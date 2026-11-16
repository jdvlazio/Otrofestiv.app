#!/usr/bin/env python3
"""sedes.py — el ALMACÉN de sedes: un lugar, un id, un pin con su evidencia.

POR QUÉ (16 nov 2026, Juan: «así como hay una de películas, las sedes deberían
vivir en un archivo matriz para no repetir procesos… un almacén como el de las
películas»). Cada festival tenía su `<fid>-venues-geo.json` y una sede repetida
se copiaba a mano de otro festival. Medido ese día: 319 pines de 277 lugares;
29 lugares en 2+ festivales, copias que ya no coincidían (Brisas de Mayo con
dos pines a 549 m), 18 pares a <40 m con nombres distintos («MAMM», «Cine
MAMM», «Museo de Arte Moderno de Medellín») y la procedencia en texto libre.

EL MODELO. `catalogo/sedes.json`:
    {"sedes": {"s_xxxxxxxx": {
        "nombre", "corto"?, "ciudad"?, "address"?, "salas"?: [salas conocidas],
        "alias": [grafías que son ESTE lugar, incluidas las crudas de los planes], "lat", "lng",
        "evidencia": {"nivel": maps|direccion|manual|nominatim|aproximado,
                      "url"?, "fecha"?, "fuente"},
        "festivales": [fid…]}},
     "decisiones": {"mismo": [[a, b]…], "distintos": [[a, b]…]},
     "_divergentes": {sid: [pines…]},
     "_deuda": {"sin_url": [sid…]}}
El id (`s_` + 8 hex) nace una vez y NO se recalcula: si el nombre o el pin
cambian, el lugar sigue siendo el mismo (como el work_id de las obras).

QUÉ ES EL MISMO LUGAR. Mismo nombre plano a <MISMO_LUGAR_M, o dos nombres que
una persona declaró `mismo`. Dos «Parque principal» a 30 km son dos lugares.
Dos lugares a <CERCA_M con ids distintos tienen que estar declarados
`distintos` (la Capilla y el Teatro del Claustro Comfama comparten patio) o
fusionados con `--mismo`.

    python3 pipeline/sedes.py --construir                 # arma/actualiza desde los venues-geo
    python3 pipeline/sedes.py --buscar "MAMM" 6.24,-75.57
    python3 pipeline/sedes.py --mismo "MAMM" "Museo de Arte Moderno de Medellín" --por-que TXT
    python3 pipeline/sedes.py --distintos "Comfama San Ignacio" "Teatro Comfama…" --por-que TXT
    python3 pipeline/sedes.py --evidencia <sid> --maps URL [--pin LAT,LNG]   # verificado en Google Maps
    python3 pipeline/sedes.py --elegir <sid> <fid>        # resuelve una divergencia con el pin de ese festival
    python3 pipeline/sedes.py --campus <sid> <metros> --por-que TXT   # campus: cada festival en su edificio
    python3 pipeline/sedes.py --pendientes                # divergencias, pares cercanos, sin evidencia

geocodificar.py consulta el almacén ANTES de Nominatim. Guardián: [sede-matriz].
"""
import glob, hashlib, json, math, os, re, sys, unicodedata
from datetime import date

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MISMO_LUGAR_M = 2000     # mismo nombre a menos de esto: el mismo lugar
TOLERANCIA_M = 120       # dentro de un lugar, pines a más de esto: divergencia
CERCA_M = 40             # dos lugares distintos a menos de esto: hay que declararlo
NIVELES = ('maps', 'direccion', 'manual', 'nominatim', 'aproximado')   # de más a menos fuerte
PREC_A_NIVEL = {'maps': 'maps', 'manual': 'manual', 'direccion': 'direccion', 'nominatim': 'nominatim',
                'matriz': 'manual'}


def plano(s):
    s = unicodedata.normalize('NFD', (s or '').lower()).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]', '', s)


def nombre_de(clave):
    """«Cinemateca de Bogotá - Bogotá» → «Cinemateca de Bogotá» (la ciudad la da el pin)."""
    return clave.split(' - ')[0].strip()


def metros(a, b):
    la1, ln1, la2, ln2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((ln2 - ln1) / 2) ** 2
    return 6371000 * 2 * math.asin(math.sqrt(h))


def _ruta(raiz):
    return f'{raiz}/catalogo/sedes.json'


def leer(raiz=REPO):
    p = _ruta(raiz)
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {}


def _escribir(d, raiz):
    json.dump(d, open(_ruta(raiz), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def nivel_de(prec):
    p = (prec or '').lower()
    return PREC_A_NIVEL.get(p, 'aproximado')


def pines(raiz=REPO):
    """Todos los pines de los venues-geo: [(fid, clave, nombre, entrada)]."""
    out = []
    for p in sorted(glob.glob(f'{raiz}/festivals/staging/*-venues-geo.json')):
        fid = os.path.basename(p)[:-len('-venues-geo.json')]
        for k, v in json.load(open(p, encoding='utf-8')).items():
            if isinstance(v, dict) and v.get('lat') is not None and v.get('lng') is not None \
                    and v.get('_prec') != 'sin verificar':
                out.append((fid, k, nombre_de(k), v))
    return out


def _uf_mismo(decisiones):
    """Nombres planos declarados el mismo lugar → su representante."""
    padre = {}

    def raiz(x):
        while padre.get(x, x) != x:
            x = padre[x]
        return x
    for a, b, *_ in decisiones.get('mismo') or []:
        ra, rb = raiz(plano(a)), raiz(plano(b))
        if ra != rb:
            padre[rb] = ra
    return raiz


def agrupar(ps, decisiones):
    """Grupos de pines que son el mismo lugar: mismo nombre (o declarado
    `mismo`) y a <MISMO_LUGAR_M de algún otro pin del grupo."""
    canon = _uf_mismo(decisiones)
    por_nombre = {}
    for x in ps:
        por_nombre.setdefault(canon(plano(x[2])), []).append(x)
    grupos = []
    for n, xs in sorted(por_nombre.items()):
        gs = []
        for x in xs:
            pt = (x[3]['lat'], x[3]['lng'])
            g = next((g for g in gs if any(metros(pt, (y[3]['lat'], y[3]['lng'])) < MISMO_LUGAR_M for y in g)), None)
            (g.append(x) if g is not None else gs.append([x]))
        grupos += gs
    return grupos


def _nuevo_id(nombre, lat, lng, usados):
    base = f'{plano(nombre)}|{lat:.4f}|{lng:.4f}'
    for i in range(100):
        sid = 's_' + hashlib.sha1(f'{base}|{i}'.encode()).hexdigest()[:8]
        if sid not in usados:
            return sid
    raise RuntimeError('sin id libre')


def _contexto(raiz):
    """Lo que los festivales ya saben de cada pin, además del pin, por
    (fid, nombre plano): {'crudas': {grafía→sala}, 'publicado': venue de la app,
    'salas': {salas de sus funciones}, 'ciudad_plan': ciudad única del plan}.
    Las grafías crudas vienen del mapa `festival.sedes` del plan (349 el 16 nov:
    «Cinemateca Sala 2» → [«Cinemateca de Bogotá - Bogotá», «Sala 2»]); el
    nombre corto, la ciudad y la dirección, del JSON publicado; las salas, de
    las funciones publicadas."""
    ctx = {}

    def c(fid, clave):
        return ctx.setdefault((fid, plano(nombre_de(clave))), {})
    ciudad_plan = {}
    for p in glob.glob(f'{raiz}/pipeline/*.plan.json'):
        fid = os.path.basename(p)[:-len('.plan.json')]
        F = json.load(open(p, encoding='utf-8')).get('festival') or {}
        cp = (F.get('city') or '').strip()
        if cp and not re.search(r'\sy\s|,|/', cp):
            ciudad_plan[fid] = cp
        sp = F.get('sedes')
        if isinstance(sp, dict):
            for cruda, v in sp.items():
                if isinstance(v, list) and v:
                    c(fid, v[0]).setdefault('crudas', {})[cruda] = (v[1] if len(v) > 1 else '') or ''
    for p in glob.glob(f'{raiz}/festivals/*.json'):
        fid = os.path.basename(p)[:-5]
        try:
            d = json.load(open(p, encoding='utf-8'))
        except ValueError:
            continue
        vs = d.get('venues') if isinstance(d, dict) else None
        if isinstance(vs, dict):
            for k, v in vs.items():
                if isinstance(v, dict):
                    c(fid, k)['publicado'] = v
        for f in (d.get('films') or []) if isinstance(d, dict) else []:
            if isinstance(f, dict) and f.get('venue') and f.get('sala'):
                c(fid, f['venue']).setdefault('salas', set()).add(f['sala'])
    for (fid, n), x in ctx.items():
        if fid in ciudad_plan:
            x['ciudad_plan'] = ciudad_plan[fid]
    return ctx


def _mas_comun(xs):
    xs = [x for x in xs if x]
    return max(set(xs), key=xs.count) if xs else None


def _ficha(e, g, ctx):
    """Completa el lugar con lo que saben los festivales: alias crudos, salas,
    nombre corto, ciudad, dirección. Lo que una persona ya fijó no se pisa."""
    ciudades, cortos, dirs = [], [], []
    alias, salas = set(e.get('alias', [])), set(e.get('salas', []))
    for fid, clave, nombre, v in g:
        c = ctx.get((fid, plano(nombre))) or {}
        for cruda, sala in (c.get('crudas') or {}).items():
            alias.add(cruda)
            if sala:
                salas.add(sala)
        salas |= c.get('salas') or set()
        pub = c.get('publicado') or {}
        sufijo = clave.split(' - ', 1)[1].strip() if ' - ' in clave else None
        ciudades.append(pub.get('city') or sufijo or c.get('ciudad_plan'))
        cortos.append(pub.get('short'))
        dirs.append(pub.get('address') or v.get('address'))
    e['alias'] = sorted(alias - {e['nombre']})
    if salas:
        e['salas'] = sorted(salas)
    ciudades = [x for x in ciudades if x and plano(x) != plano(e['nombre'])]
    for campo, xs in (('ciudad', ciudades), ('corto', cortos), ('address', dirs)):
        if not e.get(campo):
            x = _mas_comun(xs)
            if x:
                e[campo] = x
    ciudades = [x for x in ciudades if x and plano(x) != plano(e['nombre'])]
    distintas = sorted(set(ciudades))
    if len(distintas) > 1:
        e['_ciudades_vistas'] = distintas
    else:
        e.pop('_ciudades_vistas', None)
    return e


def construir(raiz=REPO):
    """Arma/actualiza el almacén desde los venues-geo. Lo que ya está —id,
    evidencia, divergencia elegida— se conserva: el almacén es la fuente, los
    venues-geo solo aportan festivales y grafías nuevas."""
    previa = leer(raiz)
    viejas = previa.get('sedes') or {}
    dec = previa.get('decisiones') or {'mismo': [], 'distintos': []}
    redir = dict(previa.get('redirecciones') or {})
    sedes, div, usados = {}, {}, set(viejas) | set(redir)
    ctx = _contexto(raiz)
    for g in agrupar(pines(raiz), dec):
        alias = {x[2] for x in g} | {x[1] for x in g}
        planos = {plano(a) for a in alias}
        pt0 = (g[0][3]['lat'], g[0][3]['lng'])
        # ¿es un lugar que ya tiene id? por alias y cercanía
        hits = sorted(s for s, e in viejas.items() if s not in sedes and s not in redir and
                      planos & {plano(a) for a in [e['nombre']] + e.get('alias', [])} and
                      metros(pt0, (e['lat'], e['lng'])) < MISMO_LUGAR_M)
        # dos ids viejos que ahora son el mismo lugar (--mismo): sobrevive uno,
        # el otro redirige — el id no se pierde, como en el almacén de obras
        sid = hits[0] if hits else None
        if sid:
            hits.sort(key=lambda h: (bool(viejas[h].get('_elegido_de')) is False,
                                     NIVELES.index((viejas[h].get('evidencia') or {}).get('nivel', 'aproximado')), h))
            sid = hits[0]
            for h in hits[1:]:
                redir[h] = sid
        g.sort(key=lambda x: (NIVELES.index(nivel_de(x[3].get('_prec'))), x[0]))
        base = g[0]
        if sid:
            e = dict(viejas[sid])
        else:
            sid = _nuevo_id(base[2], base[3]['lat'], base[3]['lng'], usados)
            usados.add(sid)
            e = {'nombre': base[2], 'lat': base[3]['lat'], 'lng': base[3]['lng'],
                 'evidencia': {'nivel': nivel_de(base[3].get('_prec')), 'fuente': f'{base[0]}-venues-geo.json'}}
            if base[3].get('address'):
                e['address'] = base[3]['address']
        e['alias'] = sorted((set(e.get('alias', [])) | alias) - {e['nombre']})
        e['festivales'] = sorted(set(e.get('festivales', [])) | {x[0] for x in g})
        _ficha(e, g, ctx)
        tol = e.get('campus', {}).get('radio_m', TOLERANCIA_M)
        lejos = [x for x in g if metros((e['lat'], e['lng']), (x[3]['lat'], x[3]['lng'])) > tol]
        # un pin verificado en Maps (o elegido a mano) MANDA: los que se apartan
        # son el error del festival, no una duda del almacén
        if lejos and not e.get('_elegido_de') and (e.get('evidencia') or {}).get('nivel') != 'maps':
            div[sid] = [{'fid': x[0], 'clave': x[1], 'lat': x[3]['lat'], 'lng': x[3]['lng'],
                         'nivel': nivel_de(x[3].get('_prec')),
                         'a_m': round(metros((e['lat'], e['lng']), (x[3]['lat'], x[3]['lng'])))} for x in g]
        sedes[sid] = e
    # lugares del almacén que ningún festival usa hoy se conservan (son datos)
    for s, e in viejas.items():
        if s not in redir:
            sedes.setdefault(s, e)
    deuda = previa.get('_deuda') or {'sin_url': sorted(s for s, e in sedes.items()
                                                       if not (e.get('evidencia') or {}).get('url'))}
    deuda['sin_url'] = sorted(s for s in deuda.get('sin_url', []) if s in sedes and s not in redir and
                              not (sedes[s].get('evidencia') or {}).get('url'))
    d = {'_provenance': {'fuente': 'festivals/staging/*-venues-geo.json + decisiones humanas',
                         'construido_por': 'pipeline/sedes.py --construir',
                         'regla': f'mismo lugar: mismo nombre (o declarado) a <{MISMO_LUGAR_M} m; '
                                  f'divergencia: pines a >{TOLERANCIA_M} m; cerca: lugares a <{CERCA_M} m sin declarar'},
         'sedes': dict(sorted(sedes.items())), 'redirecciones': dict(sorted(redir.items())), 'decisiones': dec, '_divergentes': div, '_deuda': deuda}
    _escribir(d, raiz)
    return d


def _sid_de(nombre, raiz, centro=None):
    m = leer(raiz)
    n = plano(nombre_de(nombre))
    cs = [(s, e) for s, e in (m.get('sedes') or {}).items()
          if n in {plano(a) for a in [e['nombre']] + e.get('alias', [])} or n == plano(s)]
    if centro:
        cs.sort(key=lambda c: metros(centro, (c[1]['lat'], c[1]['lng'])))
    return cs[0][0] if cs else None


def buscar(nombre, centro, radio_m=30000, raiz=REPO):
    """El lugar del almacén con ese nombre o alias más cercano a `centro`,
    dentro de `radio_m`. None si no hay, o si está en divergencia."""
    m = leer(raiz)
    n = plano(nombre_de(nombre))
    cands = [(metros(centro, (e['lat'], e['lng'])), sid, e) for sid, e in (m.get('sedes') or {}).items()
             if n in {plano(nombre_de(a)) for a in [e['nombre']] + e.get('alias', [])}]
    cands = [c for c in cands if c[0] <= radio_m]
    if not cands:
        return None
    _, sid, e = min(cands, key=lambda c: c[0])
    if sid in (m.get('_divergentes') or {}):
        return None
    ev = e.get('evidencia') or {}
    return {'lat': e['lat'], 'lng': e['lng'], '_prec': 'matriz', '_matriz': sid,
            '_match': f'almacén de sedes: {e["nombre"]} ({ev.get("nivel")})',
            **{k: e[k] for k in ('address', 'ciudad', 'corto', 'salas') if e.get(k)}}


def declarar(tipo, a, b, por_que, raiz=REPO):
    if not (por_que or '').strip():
        sys.exit(f'--{tipo} necesita --por-que')
    m = leer(raiz)
    dec = m.setdefault('decisiones', {'mismo': [], 'distintos': []})
    par = sorted([a, b])
    if not any(sorted(x[:2]) == par for x in dec.setdefault(tipo, [])):
        dec[tipo].append(par + [por_que])
    _escribir(m, raiz)
    construir(raiz)


def poner_evidencia(sid, url, pin=None, raiz=REPO):
    if not re.match(r'https://(www\.)?(google\.[a-z.]+/maps|maps\.app\.goo\.gl|goo\.gl/maps)', url or ''):
        sys.exit('la evidencia es un enlace de Google Maps')
    m = leer(raiz)
    e = m['sedes'].get(sid) or sys.exit(f'{sid} no existe')
    if pin:
        e['lat'], e['lng'] = pin
    e['evidencia'] = {'nivel': 'maps', 'url': url, 'fecha': date.today().isoformat(),
                      'fuente': 'verificado en Google Maps'}
    if sid in (m.get('_divergentes') or {}):
        e['_elegido_de'] = 'maps'
    _escribir(m, raiz)
    construir(raiz)


def marcar_campus(sid, radio_m, por_que, raiz=REPO):
    """Un CAMPUS (universidad, claustro, parque con varias salas): cada
    festival pone el pin en SU edificio y está bien. El lugar tolera pines
    dentro de `radio_m` (16 nov: U. Central, Sala Fundadores vs. Auditorio
    Caldas a 221 m; Jorge Tadeo, Posgrados vs. Salón Oval a 159 m)."""
    if not (por_que or '').strip():
        sys.exit('--campus necesita --por-que')
    if not 120 < radio_m <= 600:
        sys.exit('un campus tolera entre 120 y 600 m; más que eso no es un lugar')
    m = leer(raiz)
    e = m['sedes'].get(sid) or sys.exit(f'{sid} no existe')
    e['campus'] = {'radio_m': radio_m, 'por_que': por_que}
    _escribir(m, raiz)
    construir(raiz)


def elegir(sid, fid, raiz=REPO):
    m = leer(raiz)
    xs = (m.get('_divergentes') or {}).get(sid) or sys.exit(f'{sid} no está en divergencia')
    x = next((x for x in xs if x['fid'] == fid), None) or sys.exit(f'{fid} no tiene pin para {sid}')
    m['sedes'][sid].update(lat=x['lat'], lng=x['lng'], _elegido_de=fid)
    m['sedes'][sid]['evidencia'] = {'nivel': x['nivel'], 'fuente': f'{fid}-venues-geo.json (elegido)'}
    _escribir(m, raiz)
    construir(raiz)


def cercanos(raiz=REPO):
    """Pares de lugares a <CERCA_M sin decisión: [(d, sid_a, sid_b)]."""
    m = leer(raiz)
    S = m.get('sedes') or {}
    dist = {frozenset(map(plano, x[:2])) for x in (m.get('decisiones') or {}).get('distintos') or []}
    ks = sorted(S.items())
    out = []
    for i, (a, x) in enumerate(ks):
        na = {plano(n) for n in [x['nombre']] + x.get('alias', [])}
        for b, y in ks[i + 1:]:
            d = metros((x['lat'], x['lng']), (y['lat'], y['lng']))
            if d >= CERCA_M:
                continue
            nb = {plano(n) for n in [y['nombre']] + y.get('alias', [])}
            if any(frozenset((p, q)) in dist for p in na for q in nb):
                continue
            out.append((round(d), a, b))
    return out


def vivo(fid, raiz=REPO):
    """¿El festival no ha terminado? Por `festivalEndStr` de su plan. Sin plan
    (los viejos sin pipeline) o ya terminado: no se reescribe, no se mide."""
    p = f'{raiz}/pipeline/{fid}.plan.json'
    if not os.path.exists(p):
        return False
    fin = ((json.load(open(p, encoding='utf-8')).get('festival') or {}).get('festivalEndStr') or '')[:10]
    return bool(fin) and fin >= date.today().isoformat()


def apartados(raiz=REPO, solo_vivos=True):
    """Pines de festival que se apartan de su lugar resuelto: [(fid, clave, sid, m)].
    Solo festivales vivos: un archivado con un pin viejo no se reescribe (la
    matriz ya tiene el bueno y lo da al próximo que lo pida)."""
    m = leer(raiz)
    S, D = m.get('sedes') or {}, m.get('_divergentes') or {}
    out = []
    for fid, k, nombre, v in pines(raiz):
        if solo_vivos and not vivo(fid, raiz):
            continue
        n = plano(nombre)
        for sid, e in S.items():
            if sid in D or n not in {plano(nombre_de(a)) for a in [e['nombre']] + e.get('alias', [])}:
                continue
            d = metros((e['lat'], e['lng']), (v['lat'], v['lng']))
            if e.get('campus', {}).get('radio_m', TOLERANCIA_M) < d < MISMO_LUGAR_M:
                out.append((fid, k, sid, round(d)))
    return out


def sin_evidencia_nueva(raiz=REPO):
    """Lugares sin enlace de Maps que NO están en la deuda congelada."""
    m = leer(raiz)
    deuda = set((m.get('_deuda') or {}).get('sin_url') or [])
    return sorted(s for s, e in (m.get('sedes') or {}).items()
                  if not (e.get('evidencia') or {}).get('url') and s not in deuda)


def _arg(flag, n=1):
    i = sys.argv.index(flag)
    v = sys.argv[i + 1:i + 1 + n]
    if len(v) < n:
        sys.exit(f'{flag}: faltan argumentos')
    return v if n > 1 else v[0]


def main():
    a = sys.argv
    pq = _arg('--por-que') if '--por-que' in a else ''
    if '--construir' in a:
        d = construir()
        print(f'✓ {len(d["sedes"])} lugares · {len(d["_divergentes"])} divergentes · '
              f'{len(cercanos())} pares cercanos sin decidir · {len(d["_deuda"]["sin_url"])} sin enlace de Maps (deuda)')
    elif '--buscar' in a:
        n, c = _arg('--buscar', 2)
        print(json.dumps(buscar(n, tuple(map(float, c.split(',')))), ensure_ascii=False, indent=1))
    elif '--mismo' in a:
        declarar('mismo', *_arg('--mismo', 2), pq)
        print('✓ declarados el mismo lugar')
    elif '--distintos' in a:
        declarar('distintos', *_arg('--distintos', 2), pq)
        print('✓ declarados lugares distintos')
    elif '--evidencia' in a:
        pin = tuple(map(float, _arg('--pin').split(','))) if '--pin' in a else None
        poner_evidencia(_arg('--evidencia'), _arg('--maps'), pin)
        print('✓ evidencia de Maps')
    elif '--campus' in a:
        sid, r = _arg('--campus', 2)
        marcar_campus(sid, int(r), pq)
        print('✓ campus')
    elif '--elegir' in a:
        elegir(*_arg('--elegir', 2))
        print('✓ divergencia resuelta')
    elif '--pendientes' in a:
        m = leer()
        for sid, xs in (m.get('_divergentes') or {}).items():
            print(f'DIVERGENTE {sid} {m["sedes"][sid]["nombre"]}')
            for x in xs:
                print(f'   {x["fid"]:28} {x["lat"]:.6f},{x["lng"]:.6f}  {x["nivel"]:10} a {x["a_m"]} m')
        for d, s1, s2 in cercanos():
            print(f'CERCA {d:>3} m  {m["sedes"][s1]["nombre"]}  ↔  {m["sedes"][s2]["nombre"]}')
        print(f'sin enlace de Maps: {len((m.get("_deuda") or {}).get("sin_url") or [])} en deuda, '
              f'{len(sin_evidencia_nueva())} nuevos')
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
