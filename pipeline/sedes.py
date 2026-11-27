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
     "_deuda": {"sin_url": [sid…], "importados": [sid…]}}
El id (`s_` + 8 hex) nace una vez y NO se recalcula: si el nombre o el pin
cambian, el lugar sigue siendo el mismo (como el work_id de las obras).

QUÉ ES EL MISMO LUGAR. Mismo nombre plano a <MISMO_LUGAR_M, o dos nombres que
una persona declaró `mismo`. Dos «Parque principal» a 30 km son dos lugares.
Dos lugares a <CERCA_M con ids distintos tienen que estar declarados
`distintos` (la Capilla y el Teatro del Claustro Comfama comparten patio) o
fusionados con `--mismo`.

    python3 pipeline/sedes.py --construir                 # arma/actualiza desde los venues-geo
    python3 pipeline/sedes.py --buscar "MAMM" 6.24,-75.57
    python3 pipeline/sedes.py --encontrar "Sala del Colombo" --ciudad Medellín   # como se le dice: candidatos, sala y cuál es firme
    python3 pipeline/sedes.py --corto <sid> "MAMM" --por-que TXT                 # el nombre con que sale en la app, en todo festival
    python3 pipeline/sedes.py --institucion "Comfama" s_aaa s_bbb … [--alias "Caja de Compensación Familiar"] --por-que TXT
    python3 pipeline/sedes.py --instituciones                                    # las instituciones y sus sedes
    python3 pipeline/sedes.py --sala-igual <sid> "Lab 1" "Laboratorio 1" --por-que TXT   # dos nombres de la misma sala
    python3 pipeline/sedes.py --nombrar <sid> "el Colombo" --por-que TXT         # una forma de decirle que ningún programa trajo
    python3 pipeline/sedes.py --mismo "MAMM" "Museo de Arte Moderno de Medellín" --por-que TXT
    python3 pipeline/sedes.py --distintos "Comfama San Ignacio" "Teatro Comfama…" --por-que TXT
    python3 pipeline/sedes.py --evidencia <sid> --maps URL [--pin LAT,LNG]   # verificado en Google Maps
    python3 pipeline/sedes.py --elegir <sid> <fid>        # resuelve una divergencia con el pin de ese festival
    python3 pipeline/sedes.py --campus <sid> <metros> --por-que TXT   # campus: cada festival en su edificio
    python3 pipeline/sedes.py --pendientes                # divergencias, pares cercanos, sin evidencia
    python3 pipeline/sedes.py --resolver <fid> [--escribir] [--aceptar «cruda=s_xxx» …] [--centro LAT,LNG]
                                                          # las sedes del crudo: ya / conocida / parecida / nueva
    python3 pipeline/sedes.py --tablero                   # festivales vivos: qué falta en sus sedes
    python3 pipeline/sedes.py --completar-ciudades        # vecino del almacén (<3 km) o Nominatim reverso
    python3 pipeline/sedes.py --enlazar                   # cada pin de los venues-geo apunta a su lugar (_matriz)

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
    # festivales publicados que nunca tuvieron venues-geo (fase 5, 26 nov 2026):
    # sus pines viven en el `venues` del JSON publicado. Sin `_prec` se tratan
    # como «aproximado», el nivel más bajo: no le ganan a un pin verificado.
    con_geo = {x[0] for x in out}
    for p in sorted(glob.glob(f'{raiz}/festivals/*.json')):
        fid = os.path.basename(p)[:-5]
        if fid in con_geo:
            continue
        try:
            d = json.load(open(p, encoding='utf-8'))
        except ValueError:
            continue
        vs = d.get('venues') if isinstance(d, dict) else None
        for k, v in (vs or {}).items() if isinstance(vs, dict) else ():
            if isinstance(v, dict) and v.get('lat') is not None and (v.get('lng') if v.get('lng') is not None else v.get('lon')) is not None:
                v = dict(v, lng=v['lng'] if v.get('lng') is not None else v['lon'], _publicado=True)
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


_NO_CIUDAD = re.compile(r'universidad|sede|campus|auditorio|edificio|bloque|sala|teatro|colegio|parque|biblioteca', re.I)


def limpia_ciudad(c):
    """«Perímetro Urbano Santa Marta» (Nominatim) → «Santa Marta»."""
    c = re.sub(r'^(Perímetro Urbano|Casco Urbano|Cabecera Municipal( de)?)\s+', '', (c or '').strip(), flags=re.I)
    return None if not c or _NO_CIUDAD.search(c) else c


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
                cc = c(fid, f['venue']).setdefault('salas', {})
                cc[f['sala']] = cc.get(f['sala'], 0) + 1
    ctx['__ciudad_plan__'] = ciudad_plan
    return ctx


def _mas_comun(xs):
    xs = [x for x in xs if x]
    return max(set(xs), key=xs.count) if xs else None


def _ficha(e, g, ctx):
    """Completa el lugar con lo que saben los festivales: alias crudos, salas,
    nombre corto, ciudad, dirección. Lo que una persona ya fijó no se pisa."""
    ciudades, cortos, dirs = [], [], []
    if e.get('ciudad') and not limpia_ciudad(e['ciudad']):   # «Universidad Nacional» no es una ciudad
        del e['ciudad']
        e.pop('_ciudad_fijada', None)
    elif e.get('ciudad'):
        e['ciudad'] = limpia_ciudad(e['ciudad'])
    alias = set(e.get('alias', []))
    salas = {x: 1 for x in e.get('salas', [])}
    for v_, c_ in (e.get('salas_alias') or {}).items():
        salas[v_] = salas.get(v_, 0)
    for fid, clave, nombre, v in g:
        c = ctx.get((fid, plano(nombre))) or {}
        for cruda, sala in (c.get('crudas') or {}).items():
            alias.add(cruda)
            if sala:
                salas[sala] = salas.get(sala, 0) + 1
        for sala, n in (c.get('salas') or {}).items():
            salas[sala] = salas.get(sala, 0) + n
        pub = c.get('publicado') or {}
        sufijo = clave.split(' - ', 1)[1].strip() if ' - ' in clave else None
        if sufijo and _NO_CIUDAD.search(sufijo):   # «Auditorio 105 - Universidad Nacional»: no es ciudad
            sufijo = None
        ciudades.append(limpia_ciudad(pub.get('city')) or sufijo or (ctx.get('__ciudad_plan__') or {}).get(fid))
        cortos.append(pub.get('short'))
        dirs.append(pub.get('address') or v.get('address'))
    e['alias'] = sorted(alias - {e['nombre']})
    canon, variantes = normalizar_salas(salas, e)
    if canon:
        e['salas'] = canon
    if variantes:
        e['salas_alias'] = variantes
    else:
        e.pop('salas_alias', None)
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


_COMPUESTA = re.compile(r'^(salas|laboratorios|auditorios|aulas)\b|\d\s*(,|\sy\s)\s*\d|\d\s+y\s+\w', re.I)


def normalizar_salas(conteo, e):
    """{sala: veces} → (salas canónicas, {variante: canónica}).
      · una sala COMPUESTA («Salas 2, 3 y Capital», «Laboratorios 1 y 2») no es
        una sala: es una función que usa varias; queda fuera;
      · las variantes de una misma sala —mayúsculas, el nombre del lugar
        delante («Teatro MAMM» → «Teatro»)— se juntan en la grafía más usada."""
    lugar = {plano(n) for n in [e.get('nombre'), e.get('corto')] if n}
    grupos = {}
    for sala, n in conteo.items():
        if not sala or _COMPUESTA.search(sala):
            continue
        # el piso es un detalle de cómo llegar, no otra sala: «Salón Montreal,
        # 3.er piso» es «Salón Montreal»
        k = plano(re.sub(r',?\s*\(?\s*(\d+\.?\s*(er|do|ro|to|vo|no|mo)?\s*piso|piso\s*\d+)\s*\)?\s*$', '', sala, flags=re.I))
        for l in lugar:
            if l and k.endswith(l) and k != l:
                k = k[:-len(l)]
            if l and k.startswith(l) and k != l:
                k = k[len(l):]
        grupos.setdefault(k, []).append((n, sala))
    canon, variantes = [], {}
    for k, xs in grupos.items():
        # la más usada; a igualdad, la más corta y con mayúscula inicial
        # sin el nombre del lugar dentro ([sala-en-sede]: «Teatro», no «Teatro
        # MAMM»), luego la más usada, luego la más corta con mayúscula inicial
        con_lugar = lambda t: any(l and l in plano(t) for l in lugar)
        xs.sort(key=lambda x: (con_lugar(x[1]), -x[0], not x[1][:1].isupper(), len(x[1]), x[1]))
        c = xs[0][1]
        canon.append(c)
        for _, v in xs[1:]:
            variantes[v] = c
    return sorted(canon), dict(sorted(variantes.items()))


def _aplicar_salas(e, sid, dec):
    """Las salas que una persona juntó (--sala-igual) siguen juntas al reconstruir:
    «Lab 1» y «Laboratorio 1» no las une la normalización, que solo ve grafías."""
    for s_, var, can, *_ in dec.get('sala_igual') or []:
        if s_ != sid:
            continue
        salas = set(e.get('salas', []))
        if var in salas or var in (e.get('salas_alias') or {}) or can in salas:
            salas.discard(var)
            salas.add(can)
            e['salas'] = sorted(salas)
            va = e.setdefault('salas_alias', {})
            va[var] = can
            for k, v in list(va.items()):
                if v == var:
                    va[k] = can
            e['salas_alias'] = dict(sorted(va.items()))


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
    # UN PIN YA ENLAZADO (`_matriz`) VA CON SU LUGAR, esté donde esté (16 nov):
    # cuando Maps movió «Antimateria» 6,4 km, el pin viejo del festival quedó
    # lejos y la reconstrucción armaba un lugar duplicado. El enlace manda
    # sobre la distancia; solo los pines sin enlace se agrupan por nombre.
    enlazados, sueltos = {}, []
    for x in pines(raiz):
        sid0 = x[3].get('_matriz')
        while sid0 in redir:
            sid0 = redir[sid0]
        if sid0 and sid0 in viejas:
            enlazados.setdefault(sid0, []).append(x)
        else:
            sueltos.append(x)
    grupos = [(s0, g0) for s0, g0 in enlazados.items()] + [(None, g0) for g0 in agrupar(sueltos, dec)]
    for fijo, g in grupos:
        alias = {x[2] for x in g} | {x[1] for x in g}
        planos = {plano(a) for a in alias}
        pt0 = (g[0][3]['lat'], g[0][3]['lng'])
        # ¿es un lugar que ya tiene id? por alias y cercanía
        if fijo:   # el lugar del enlace; su pin (quizá corregido en Maps) es el que cuenta
            pt0 = (viejas[fijo]['lat'], viejas[fijo]['lng'])
            planos |= {plano(a) for a in [viejas[fijo]['nombre']] + viejas[fijo].get('alias', [])}
        canon = _uf_mismo(dec)
        cplanos = {canon(p_) for p_ in planos}
        hits = sorted(s for s, e in viejas.items() if s not in sedes and s not in redir and
                      cplanos & {canon(plano(a)) for a in [e['nombre']] + e.get('alias', [])} and
                      metros(pt0, (e['lat'], e['lng'])) < MISMO_LUGAR_M)
        if fijo and fijo not in hits:
            hits.append(fijo)
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
                 'evidencia': {'nivel': nivel_de(base[3].get('_prec')), 'fuente': f'{base[0]}.json (publicado)' if base[3].get('_publicado') else f'{base[0]}-venues-geo.json'}}
            if base[3].get('address'):
                e['address'] = base[3]['address']
        e['alias'] = sorted((set(e.get('alias', [])) | alias) - {e['nombre']})
        e['festivales'] = sorted(set(e.get('festivales', [])) | {x[0] for x in g})
        _ficha(e, g, ctx)
        _aplicar_salas(e, sid, dec)
        tol = e.get('campus', {}).get('radio_m', TOLERANCIA_M)
        lejos = [x for x in g if metros((e['lat'], e['lng']), (x[3]['lat'], x[3]['lng'])) > tol]
        # un pin verificado en Maps (o elegido a mano) MANDA: los que se apartan
        # son el error del festival, no una duda del almacén
        if lejos and not e.get('_elegido_de') and (e.get('evidencia') or {}).get('nivel') != 'maps':
            div[sid] = [{'fid': x[0], 'clave': x[1], 'lat': x[3]['lat'], 'lng': x[3]['lng'],
                         'nivel': nivel_de(x[3].get('_prec')),
                         'a_m': round(metros((e['lat'], e['lng']), (x[3]['lat'], x[3]['lng'])))} for x in g]
        sedes[sid] = e
    # FUSIÓN TARDÍA: dos lugares ya armados que una persona declaró `mismo` y que
    # quedan a <MISMO_LUGAR_M se juntan aquí (el orden de los grupos no decide)
    canon = _uf_mismo(dec)
    ids = sorted(sedes, key=lambda h: (bool(sedes[h].get('_elegido_de')) is False,
                                        NIVELES.index((sedes[h].get('evidencia') or {}).get('nivel', 'aproximado')), h))
    for i, a_ in enumerate(ids):
        if a_ not in sedes:
            continue
        ca = {canon(plano(n)) for n in [sedes[a_]['nombre']] + sedes[a_].get('alias', [])}
        for b_ in ids[i + 1:]:
            if b_ not in sedes:
                continue
            eb = sedes[b_]
            if ca & {canon(plano(n)) for n in [eb['nombre']] + eb.get('alias', [])} and \
                    metros((sedes[a_]['lat'], sedes[a_]['lng']), (eb['lat'], eb['lng'])) < MISMO_LUGAR_M:
                ea = sedes[a_]
                ea['alias'] = sorted((set(ea.get('alias', [])) | set(eb.get('alias', [])) | {eb['nombre']}) - {ea['nombre']})
                ea['festivales'] = sorted(set(ea['festivales']) | set(eb['festivales']))
                for k in ('salas',):
                    if eb.get(k):
                        ea[k] = sorted(set(ea.get(k, [])) | set(eb[k]))
                if eb.get('institucion') and not ea.get('institucion'):
                    ea['institucion'] = eb['institucion']
                redir[b_] = a_
                div.pop(b_, None)
                del sedes[b_]
                ca |= {canon(plano(n)) for n in [eb['nombre']] + eb.get('alias', [])}
    # lugares del almacén que ningún festival usa hoy se conservan (son datos)
    for s, e in viejas.items():
        if s not in redir:
            sedes.setdefault(s, e)
    # LA CIUDAD SE COMPRUEBA CON EL MAPA (16 nov): un festival de varias ciudades
    # (MIDBO, Bogotá) le prestaba «Bogotá» a la Universidad de Antioquia. Un
    # lugar a >40 km de la mediana de su ciudad no es de esa ciudad: se le quita
    # y queda para revisar.
    med = lambda xs: sorted(xs)[len(xs) // 2]
    por_ciudad = {}
    for e in sedes.values():
        if e.get('ciudad'):
            por_ciudad.setdefault(e['ciudad'], []).append((e['lat'], e['lng']))
    centros = {c: (med([p[0] for p in ps]), med([p[1] for p in ps])) for c, ps in por_ciudad.items() if len(ps) >= 3}
    for e in sedes.values():
        c = e.get('ciudad')
        if c in centros and metros(centros[c], (e['lat'], e['lng'])) > 40000 and not e.get('_ciudad_fijada'):
            e['_ciudad_dudosa'] = c
            del e['ciudad']
    deuda = previa.get('_deuda') or {'sin_url': sorted(s for s, e in sedes.items()
                                                       if not (e.get('evidencia') or {}).get('url'))}
    deuda['sin_url'] = sorted(s for s in deuda.get('sin_url', []) if s in sedes and s not in redir and
                              not (sedes[s].get('evidencia') or {}).get('url'))
    # `importados`: los lugares de los 16 festivales publicados que nunca
    # tuvieron venues-geo (fase 5, 26 nov 2026). Deuda aparte de la vieja,
    # con su propio número; como la otra, solo baja.
    deuda['importados'] = sorted({redir.get(s, s) for s in deuda.get('importados', [])} & set(sedes) - set(deuda['sin_url'])
                                 - {s for s in sedes if (sedes[s].get('evidencia') or {}).get('url')})
    d = {'_provenance': {'fuente': 'festivals/staging/*-venues-geo.json + decisiones humanas',
                         'construido_por': 'pipeline/sedes.py --construir',
                         'regla': f'mismo lugar: mismo nombre (o declarado) a <{MISMO_LUGAR_M} m; '
                                  f'divergencia: pines a >{TOLERANCIA_M} m; cerca: lugares a <{CERCA_M} m sin declarar'},
         'instituciones': dict(sorted((previa.get('instituciones') or {}).items())),
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
    d = m.get('_deuda') or {}
    deuda = set(d.get('sin_url') or []) | set(d.get('importados') or [])
    return sorted(s for s, e in (m.get('sedes') or {}).items()
                  if not (e.get('evidencia') or {}).get('url') and s not in deuda)


# ── enlazar: el festival apunta al lugar (PR C, 16 nov 2026) ─────────────────
def lugar(sid, raiz=REPO, _m=None):
    """El lugar de un id, siguiendo las redirecciones de --mismo. None si no existe."""
    m = _m or leer(raiz)
    red = m.get('redirecciones') or {}
    for _ in range(10):
        if sid in red:
            sid = red[sid]
    return (m.get('sedes') or {}).get(sid)


def enlazar(raiz=REPO):
    """Pone `_matriz: s_xxx` en cada pin de los venues-geo que el almacén
    conoce. Desde ahí el pin y la dirección los da el almacén (ensamblar.py):
    corregir un lugar una vez lo corrige en todos los festivales que se vuelvan
    a armar. → {fid: n enlazados}"""
    m = leer(raiz)
    S = m.get('sedes') or {}
    idx = {}
    for sid, e in S.items():
        for nom in [e['nombre']] + e.get('alias', []):
            for fid in e['festivales']:
                idx.setdefault((fid, nom), sid)
    out = {}
    for p in sorted(glob.glob(f'{raiz}/festivals/staging/*-venues-geo.json')):
        fid = os.path.basename(p)[:-len('-venues-geo.json')]
        g = json.load(open(p, encoding='utf-8'))
        n = 0
        for k, v in g.items():
            if not isinstance(v, dict) or v.get('lat') is None:
                continue
            sid = idx.get((fid, k)) or idx.get((fid, nombre_de(k)))
            if sid and v.get('_matriz') != sid:
                v['_matriz'] = sid
                n += 1
        if n:
            json.dump(g, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
            out[fid] = n
    return out


def sin_enlace(raiz=REPO):
    """Pines de festivales VIVOS sin `_matriz` válido: [(fid, clave)]."""
    m = leer(raiz)
    out = []
    for fid, k, nombre, v in pines(raiz):
        if vivo(fid, raiz) and not (v.get('_matriz') and lugar(v['_matriz'], _m=m)):
            out.append((fid, k))
    return out


# ── completar la ciudad (16 nov 2026, Juan: «añadir ciudad») ────────────────
def _reverso(lat, lng):
    """Nominatim reverso → municipio. Con la cortesía de 1 consulta/s."""
    import subprocess, time
    url = f'https://nominatim.openstreetmap.org/reverse?format=json&zoom=10&lat={lat}&lon={lng}&accept-language=es'
    r = subprocess.run(['curl', '-s', '--max-time', '25', '-A', 'Otrofestiv/1.0 (sedes; github.com/jdvlazio)', url],
                       capture_output=True)
    time.sleep(1.1)
    try:
        a = json.loads(r.stdout).get('address') or {}
    except ValueError:
        return None
    return a.get('city') or a.get('town') or a.get('municipality') or a.get('village') or a.get('county')   # en Colombia el municipio rural sale como «county»


def completar_ciudades(raiz=REPO, reverso=_reverso):
    """La ciudad de los lugares que no la tienen (o la tenían dudosa): primero
    el lugar del almacén más cercano con ciudad, si está a <3 km; si no,
    Nominatim reverso. Queda fijada, con su fuente. → [(nombre, ciudad, fuente)]"""
    m = leer(raiz)
    S = m.get('sedes') or {}
    con = [(e['lat'], e['lng'], e['ciudad']) for e in S.values() if e.get('ciudad')]
    out = []
    for sid, e in S.items():
        if e.get('ciudad'):
            continue
        cerca = sorted((metros((e['lat'], e['lng']), (a, b)), c) for a, b, c in con)
        if cerca and cerca[0][0] < 3000:
            ciudad, fuente = cerca[0][1], f'lugar vecino del almacén a {round(cerca[0][0])} m'
        else:
            ciudad, fuente = limpia_ciudad(reverso(e['lat'], e['lng'])), 'Nominatim reverso'
        if ciudad:
            e.update(ciudad=ciudad, _ciudad_fijada=fuente)
            e.pop('_ciudad_dudosa', None)
            out.append((e['nombre'], ciudad, fuente))
    _escribir(m, raiz)
    construir(raiz)
    return out


# ── resolver las sedes de un festival en un paso (PR B, 16 nov 2026) ─────────
def _centro(fid, raiz):
    """Dónde está el festival: sus pines ya puestos, o los lugares del almacén
    de su ciudad (la del plan). None si no hay cómo saberlo."""
    gp = f'{raiz}/festivals/staging/{fid}-venues-geo.json'
    pts = []
    if os.path.exists(gp):
        pts = [(v['lat'], v['lng']) for v in json.load(open(gp, encoding='utf-8')).values()
               if isinstance(v, dict) and v.get('lat') is not None]
    if not pts:
        pp = f'{raiz}/pipeline/{fid}.plan.json'
        ciudad = ((json.load(open(pp, encoding='utf-8')).get('festival') or {}).get('city') or '') if os.path.exists(pp) else ''
        pts = [(e['lat'], e['lng']) for e in (leer(raiz).get('sedes') or {}).values()
               if e.get('ciudad') and plano(e['ciudad']) == plano(ciudad)]
    if not pts:
        return None
    # la MEDIANA, no el promedio: un solo pin mal puesto (o un lugar con la
    # ciudad mal cosechada) corría el centro de Bogotá 50 km al norte
    med = lambda xs: sorted(xs)[len(xs) // 2]
    return (med([p[0] for p in pts]), med([p[1] for p in pts]))


def _parecidos(cruda, centro, raiz, radio_m=30000, n=3):
    """Lugares del almacén con nombre parecido (no igual): por palabras en común
    y por similitud de letras, dentro del radio."""
    import difflib
    stop = {'de', 'del', 'la', 'el', 'los', 'las', 'y', 'sala', 'sede', 'centro', 'teatro', 'auditorio'}
    pal = lambda t: {w for w in re.findall(r'[a-z0-9]+', unicodedata.normalize('NFD', t.lower()).encode('ascii', 'ignore').decode()) if w not in stop and len(w) > 2}
    pc = pal(cruda)
    out = []
    for sid, e in (leer(raiz).get('sedes') or {}).items():
        if centro and metros(centro, (e['lat'], e['lng'])) > radio_m:
            continue
        best = 0
        for nom in [e['nombre']] + e.get('alias', []):
            pn = pal(nombre_de(nom))
            jac = len(pc & pn) / len(pc | pn) if pc | pn else 0
            rat = difflib.SequenceMatcher(None, plano(cruda), plano(nombre_de(nom))).ratio()
            best = max(best, jac, rat - 0.15)
        if best >= 0.5:
            out.append((round(best, 2), sid, e))
    return sorted(out, key=lambda x: -x[0])[:n]


def _con_sala(cruda, centro, raiz, radio_m=30000):
    """«Cinemateca Sala 2» → (sid, 'Sala 2') si el lugar conoce esa sala."""
    pc = plano(cruda)
    for sid, e in (leer(raiz).get('sedes') or {}).items():
        if centro and metros(centro, (e['lat'], e['lng'])) > radio_m:
            continue
        noms = [e['nombre'], e.get('corto') or ''] + e.get('alias', [])
        if e.get('ciudad'):   # «Cinemateca de Bogotá» → «Cinemateca» + «Sala Capital»
            noms += [re.sub(rf'\s+de\s+{re.escape(e["ciudad"])}$', '', n, flags=re.I) for n in noms if n]
        for nom in noms:
            pn = plano(nombre_de(nom))
            if pn and pc.startswith(pn):
                resto = pc[len(pn):]
                sala = next((sa for sa in e.get('salas', []) if plano(sa) == resto), None)
                if not sala:   # una variante conocida resuelve a la sala canónica
                    sala = next((c_ for v_, c_ in (e.get('salas_alias') or {}).items() if plano(v_) == resto), None)
                if sala:
                    return sid, sala
    return None


_VACIAS = {'de', 'del', 'la', 'el', 'los', 'las', 'y', 'en', 'sala', 'sede', 'centro'}


def _pal(s):
    return re.findall(r'[a-z0-9]+', unicodedata.normalize('NFD', (s or '').lower()).encode('ascii', 'ignore').decode())


def _sin(pal, tramo):
    """`pal` sin el tramo contiguo `tramo`; None si no lo trae."""
    n = len(tramo)
    for i in range(len(pal) - n + 1):
        if n and pal[i:i + n] == tramo:
            return pal[:i] + pal[i + n:]
    return None


def _id_inst(nombre):
    return 'i_' + hashlib.sha1(plano(nombre).encode()).hexdigest()[:8]


def institucion(nombre, sids, por_que, alias=(), raiz=REPO):
    """Varias sedes de una misma institución (fase 3, 26 nov 2026): Comfama tiene nueve,
    la Tadeo cuatro edificios, la Cinemateca de Bogotá dos sedes. La institución no es un
    lugar —no tiene pin—: agrupa lugares para encontrarlos y, después, para mostrarlos juntos.
    Una sede está en una sola institución; cambiarla de una a otra se hace a propósito."""
    if not (por_que or '').strip():
        sys.exit('--institucion necesita --por-que')
    nombre = (nombre or '').strip()
    if not _pal(nombre) or not sids:
        sys.exit('--institucion: faltan el nombre o las sedes')
    m = leer(raiz)
    I = m.setdefault('instituciones', {})
    iid = next((i for i, x in I.items() if plano(nombre) in {plano(n) for n in [x['nombre']] + x.get('alias', [])}), None) or _id_inst(nombre)
    for sid in sids:
        e = (m.get('sedes') or {}).get(sid)
        if not e:
            sys.exit(f'--institucion: {sid} no existe')
        if e.get('institucion') and e['institucion'] != iid:
            sys.exit(f"--institucion: {sid} {e['nombre']} ya es de {I.get(e['institucion'], {}).get('nombre', e['institucion'])}")
    x = I.setdefault(iid, {'nombre': nombre, 'alias': []})
    x['alias'] = sorted((set(x.get('alias', [])) | {a.strip() for a in alias if a.strip()}) - {x['nombre']})
    x.setdefault('decisiones', []).append({'sedes': sorted(sids), 'por_que': por_que.strip(), 'fecha': date.today().isoformat()})
    for sid in sids:
        m['sedes'][sid]['institucion'] = iid
    _escribir(m, raiz)
    return iid


def sedes_de(iid, raiz=REPO, _m=None):
    m = _m or leer(raiz)
    return sorted(s for s, e in (m.get('sedes') or {}).items() if e.get('institucion') == iid)


def sala_igual(sid, variante, canonica, por_que, raiz=REPO):
    """Dos nombres de la MISMA sala que la normalización no junta («Lab 1» / «Laboratorio 1»)."""
    if not (por_que or '').strip():
        sys.exit('--sala-igual necesita --por-que')
    m = leer(raiz)
    e = (m.get('sedes') or {}).get(sid)
    if not e:
        sys.exit(f'--sala-igual: {sid} no existe')
    conocidas = set(e.get('salas', [])) | set(e.get('salas_alias') or {})
    for s_ in (variante, canonica):
        if s_ not in conocidas:
            sys.exit(f'--sala-igual: «{s_}» no es una sala de {e["nombre"]}')
    if variante == canonica:
        sys.exit('--sala-igual: son la misma grafía')
    dec = m.setdefault('decisiones', {}).setdefault('sala_igual', [])
    if not any(x[:3] == [sid, variante, canonica] for x in dec):
        dec.append([sid, variante, canonica, por_que.strip()])
    _aplicar_salas(e, sid, m['decisiones'])
    _escribir(m, raiz)
    return e


def huerfanas(raiz=REPO):
    """Sedes que apuntan a una institución que no existe."""
    m = leer(raiz)
    I = m.get('instituciones') or {}
    return sorted(s for s, e in (m.get('sedes') or {}).items() if e.get('institucion') and e['institucion'] not in I)


def encontrar(texto, ciudad=None, centro=None, radio_m=30000, raiz=REPO, n=6):
    """Cómo se le dice a un lugar → los lugares del almacén que pueden ser, del más al menos firme.

    «Colombo», «el Colombo Americano», «Sala del Colombo», «Colombo Americano sala 2», «la Tadeo»:
    nadie escribe el nombre oficial. Niveles:
      igual      — es el nombre o una variante guardada (lo que ya hacía --buscar);
      sin ciudad — igual, quitando la ciudad («Cinemateca» en Bogotá);
      contenida  — todas sus palabras de peso están en un nombre del lugar («Tadeo»);
      parecida   — se parece por palabras o por letras: es una pista, no un hallazgo.
    Si el texto trae una sala que el lugar conoce, sale aparte en `sala`.
    `firme` solo cuando no hay otro candidato del mismo peso: «Cinemateca» en Bogotá
    devuelve la de Bogotá, la de Fontanar y la Sala Gaitán, y ninguna es firme.
    Se acota con `ciudad` (nombre) o con `centro` + `radio_m`."""
    S = leer(raiz).get('sedes') or {}
    pq = _pal(nombre_de(texto))
    out = []
    for sid, e in S.items():
        if ciudad and plano(e.get('ciudad')) != plano(ciudad):
            continue
        if centro and metros(centro, (e['lat'], e['lng'])) > radio_m:
            continue
        de_ciudad = set(_pal(e.get('ciudad')))
        peso = lambda ps: {w for w in ps if w not in _VACIAS and w not in de_ciudad and (len(w) > 2 or w.isdigit())}
        noms = [x for x in [e['nombre'], e.get('corto')] + e.get('alias', []) if x]
        salas = [(sa, sa) for sa in e.get('salas', [])] + list((e.get('salas_alias') or {}).items())
        mejor = None
        for escrita, sala in [(None, None)] + salas:
            resto = pq if escrita is None else _sin(pq, _pal(escrita))
            if resto is None or (escrita is not None and not peso(resto)):
                continue
            for nom in noms:
                pn = _pal(nombre_de(nom))
                a, b = peso(resto), peso(pn)
                if ''.join(resto) == ''.join(pn):
                    c = (1.0, 'igual')
                elif a and a == b:
                    c = (0.9, 'sin ciudad')
                elif a and a <= b and (len(a) > 1 or len(next(iter(a))) >= 4):
                    c = (0.8, 'contenida')
                else:
                    continue
                if not mejor or (c[0], bool(sala)) > (mejor[0], bool(mejor[2])):
                    mejor = (c[0], c[1], sala, nom)
        if mejor:
            out.append({'sid': sid, 'nombre': e['nombre'], 'ciudad': e.get('ciudad'), 'puntaje': mejor[0], 'nivel': mejor[1],
                        'por': mejor[3], **({'sala': mejor[2]} if mejor[2] else {})})
    I = leer(raiz).get('instituciones') or {}
    for iid, ins in I.items():
        nomi = [ins['nombre']] + ins.get('alias', [])
        a = {w for w in pq if w not in _VACIAS and (len(w) > 2 or w.isdigit())}
        if not a or not any(a <= {w for w in _pal(n) if w not in _VACIAS} or ''.join(pq) == ''.join(_pal(n)) for n in nomi):
            continue
        for sid in sedes_de(iid, raiz):
            e = S[sid]
            if (ciudad and plano(e.get('ciudad')) != plano(ciudad)) or (centro and metros(centro, (e['lat'], e['lng'])) > radio_m):
                continue
            hay = next((x for x in out if x['sid'] == sid), None)
            if hay and hay['puntaje'] >= 0.85:
                continue
            if hay:
                out.remove(hay)
            out.append({'sid': sid, 'nombre': e['nombre'], 'ciudad': e.get('ciudad'), 'puntaje': 0.85,
                        'nivel': 'institución', 'por': ins['nombre']})
    for x in out:
        if S[x['sid']].get('institucion') in I:
            x['institucion'] = I[S[x['sid']]['institucion']]['nombre']
    vistos = {x['sid'] for x in out}
    centro_p = centro
    for p, sid, e in _parecidos(texto, centro_p, raiz, radio_m, n=n):
        if sid in vistos or (ciudad and plano(e.get('ciudad')) != plano(ciudad)):
            continue
        out.append({'sid': sid, 'nombre': e['nombre'], 'ciudad': e.get('ciudad'), 'puntaje': round(min(p, 1) * 0.7, 2),
                    'nivel': 'parecida', 'por': e['nombre']})
    out.sort(key=lambda x: (-x['puntaje'], -len(S[x['sid']].get('festivales', [])), x['nombre']))
    for i, x in enumerate(out):
        x['firme'] = i == 0 and x['nivel'] != 'parecida' and not any(y['puntaje'] >= x['puntaje'] for y in out[1:])
    return out[:n]


def nombrar(sid, texto, por_que, raiz=REPO):
    """Una forma de decirle al lugar que ningún programa trajo todavía («el Colombo», «la Tadeo»).
    Queda como variante: desde ahí --buscar y --resolver la reconocen sin preguntar."""
    if not (por_que or '').strip():
        sys.exit('--nombrar necesita --por-que')
    m = leer(raiz)
    e = (m.get('sedes') or {}).get(sid)
    if not e:
        sys.exit(f'--nombrar: {sid} no existe')
    texto = texto.strip()
    if not _pal(texto):
        sys.exit('--nombrar: falta el texto')
    otro = [f"{s} {o['nombre']}" for s, o in m['sedes'].items() if s != sid
            and metros((e['lat'], e['lng']), (o['lat'], o['lng'])) <= 30000
            and plano(nombre_de(texto)) in {plano(nombre_de(x)) for x in [o['nombre']] + o.get('alias', [])}]
    if otro:
        sys.exit(f'--nombrar: «{texto}» ya nombra a otro lugar cercano: {", ".join(otro)}')
    if plano(texto) != plano(e['nombre']) and texto not in e.get('alias', []):
        e['alias'] = sorted(set(e.get('alias', [])) | {texto})
    dec = m.setdefault('decisiones', {}).setdefault('nombrado', [])
    if not any(x[:2] == [sid, texto] for x in dec):
        dec.append([sid, texto, por_que.strip()])
    _escribir(m, raiz)
    return e['alias']


def fijar_corto(sid, corto, por_que, raiz=REPO, fecha=None):
    """El nombre con que el lugar sale en la app, decidido por una persona (fase 2, 26 nov 2026).
    El MAMM salía «MAMM», «Cine MAMM» o «Museo de Arte Moderno de Medellín» según el festival.
    Desde aquí ensamblar.py publica este nombre en todo festival que se arme; los otros
    quedan como variantes para que la búsqueda los siga encontrando."""
    if not (por_que or '').strip():
        sys.exit('--corto necesita --por-que')
    corto = (corto or '').strip()
    if not corto:
        sys.exit('--corto: falta el nombre')
    m = leer(raiz)
    e = (m.get('sedes') or {}).get(sid)
    if not e:
        sys.exit(f'--corto: {sid} no existe')
    viejo = e.get('corto')
    if viejo and viejo != corto and viejo != e['nombre']:
        e['alias'] = sorted(set(e.get('alias', [])) | {viejo})
    e['alias'] = sorted(set(e.get('alias', [])) - {corto})
    e['corto'] = corto
    e['corto_decidido'] = {'por_que': por_que.strip(), 'fecha': fecha or date.today().isoformat()}
    _escribir(m, raiz)
    return e


def cortos_distintos(raiz=REPO, solo_vivos=True):
    """Venues publicados con otro nombre que el decidido para su lugar: [(fid, clave, publicado, decidido)]."""
    S_ = leer(raiz).get('sedes') or {}
    out = []
    for p in sorted(glob.glob(f'{raiz}/festivals/staging/*-venues-geo.json')):
        fid = os.path.basename(p)[:-len('-venues-geo.json')]
        pj = f'{raiz}/festivals/{fid}.json'
        if (solo_vivos and not vivo(fid, raiz)) or not os.path.exists(pj):
            continue
        g = json.load(open(p, encoding='utf-8'))
        ven = (json.load(open(pj, encoding='utf-8')) or {}).get('venues') or {}
        for k, v in ven.items():
            x = g.get(k) or g.get(nombre_de(k)) or {}
            e = S_.get(x.get('_matriz') or '')
            if e and e.get('corto_decidido') and isinstance(v, dict) and v.get('short') != e['corto']:
                out.append((fid, k, v.get('short'), e['corto']))
    return out


def resolver(fid, raiz=REPO, escribir=False, aceptar=None, centro=None):
    """Las sedes del crudo de un festival, una por una:
      ya        — el plan ya la mapea y su pin está;
      conocida  — el almacén la tiene (nombre, alias o «lugar + sala»);
      parecida  — candidatos para confirmar con --aceptar «cruda=s_xxx»;
      nueva     — no está: buscar en Maps (enlace listo).
    Con `escribir`, las conocidas y las aceptadas entran al plan
    (festival.sedes: cruda → [«Nombre - Ciudad», sala]) y al venues-geo, con el
    pin del almacén. → {estado: [(cruda, detalle)]}"""
    aceptar = dict(aceptar or {})
    crudo = json.load(open(f'{raiz}/festivals/staging/{fid}-crudo.json', encoding='utf-8'))
    pp = f'{raiz}/pipeline/{fid}.plan.json'
    plan = json.load(open(pp, encoding='utf-8'))
    F = plan.setdefault('festival', {})
    tabla = F.setdefault('sedes', {})
    gp = f'{raiz}/festivals/staging/{fid}-venues-geo.json'
    geo = json.load(open(gp, encoding='utf-8')) if os.path.exists(gp) else {}
    centro = centro or _centro(fid, raiz)
    S = leer(raiz).get('sedes') or {}
    crudas = sorted({f['sede'] for f in crudo.get('funciones', []) if f.get('sede')})
    out = {'ya': [], 'conocida': [], 'parecida': [], 'nueva': []}
    for cr in crudas:
        canon = (tabla.get(cr) or [cr])[0]
        if (geo.get(canon) or {}).get('lat') is not None:
            out['ya'].append((cr, canon))
            continue
        sala, sid = '', None
        if cr in aceptar:
            sid = aceptar[cr]
            if sid not in S:
                sys.exit(f'--aceptar: {sid} no existe')
            sala = next((x.get('sala', '') for x in encontrar(cr, centro=centro, raiz=raiz, n=99) if x['sid'] == sid), '')
        else:
            hit = buscar(cr, centro, raiz=raiz) if centro else None
            if hit:
                sid = hit['_matriz']
            else:
                cs = _con_sala(cr, centro, raiz)
                if cs:
                    sid, sala = cs
        if not sid:
            par = encontrar(cr, centro=centro, raiz=raiz)
            if par:
                out['parecida'].append((cr, [(x['puntaje'], x['sid'], x['nombre'] + (f" / {x['sala']}" if x.get('sala') else ''), x['ciudad'],
                                              round(metros(centro, (S[x['sid']]['lat'], S[x['sid']]['lng']))) if centro else None)
                                             for x in par]))
            else:
                ciudad = F.get('city') or ''
                q = re.sub(r'\s+', '+', f'{cr} {ciudad}'.strip())
                out['nueva'].append((cr, f'https://www.google.com/maps/search/{q}'))
            continue
        e = S[sid]
        nuevo = f'{e["nombre"]} - {e["ciudad"]}' if e.get('ciudad') else e['nombre']
        out['conocida'].append((cr, f'{nuevo}{" / " + sala if sala else ""} ({sid})'))
        if escribir:
            tabla[cr] = [nuevo, sala]
            g = {'lat': e['lat'], 'lng': e['lng'], '_prec': 'matriz', '_matriz': sid,
                 '_match': f'almacén de sedes ({(e.get("evidencia") or {}).get("nivel")})'}
            for k in ('address',):
                if e.get(k):
                    g[k] = e[k]
            geo[nuevo] = {**geo.get(nuevo, {}), **g}
    if escribir and out['conocida']:
        json.dump(plan, open(pp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        json.dump(geo, open(gp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return out


def tablero(raiz=REPO):
    """Lo que falta en las sedes de los festivales VIVOS: sedes del crudo sin
    pin, pines sin verificar o aproximados, lugares sin enlace de Maps."""
    S = leer(raiz).get('sedes') or {}
    filas = []
    for p in sorted(glob.glob(f'{raiz}/pipeline/*.plan.json')):
        fid = os.path.basename(p)[:-len('.plan.json')]
        if not vivo(fid, raiz) or not os.path.exists(f'{raiz}/festivals/staging/{fid}-crudo.json'):
            continue
        r = resolver(fid, raiz)
        gp = f'{raiz}/festivals/staging/{fid}-venues-geo.json'
        geo = json.load(open(gp, encoding='utf-8')) if os.path.exists(gp) else {}
        flojos = [k for k, v in geo.items() if isinstance(v, dict) and
                  (v.get('_prec') in ('sin verificar', 'nominatim', 'aproximado') or v.get('_todo'))]
        sin_maps = sorted({e['nombre'] for e in S.values() if fid in e['festivales']
                           and not (e.get('evidencia') or {}).get('url')})
        filas.append((fid, r, flojos, sin_maps))
    return filas


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
    elif '--encontrar' in a:
        ciu = _arg('--ciudad') if '--ciudad' in a else None
        c = tuple(map(float, _arg('--centro').split(','))) if '--centro' in a else None
        r = encontrar(_arg('--encontrar'), ciudad=ciu, centro=c)
        for x in r:
            print(f"  {'FIRME ' if x['firme'] else '      '}{x['sid']}  {x['nombre']} ({x['ciudad'] or '?'})"
                  f"{' · de ' + x['institucion'] if x.get('institucion') else ''}"
                  f"{' · sala: ' + x['sala'] if x.get('sala') else ''} · {x['nivel']} por «{x['por']}»")
        print(f'{len(r)} candidatos' + ('' if any(x['firme'] for x in r) else ' · ninguno firme: elegir a mano') if r else 'no está en el almacén')
    elif '--institucion' in a:
        i = a.index('--institucion')
        nom = a[i + 1]
        sids = [x for x in a[i + 2:] if re.fullmatch(r's_[0-9a-f]{8}', x)]
        al = [a[j + 1] for j, x in enumerate(a) if x == '--alias' and j + 1 < len(a)]
        iid = institucion(nom, sids, pq, al)
        print(f'✓ {iid} {nom}: ' + ', '.join(leer()['sedes'][s]['nombre'] for s in sedes_de(iid)))
    elif '--instituciones' in a:
        m = leer()
        for iid, x in (m.get('instituciones') or {}).items():
            print(f"{iid}  {x['nombre']}" + (f" (también: {', '.join(x['alias'])})" if x.get('alias') else ''))
            for s in sedes_de(iid, _m=m):
                print(f"    {s}  {m['sedes'][s]['nombre']} ({m['sedes'][s].get('ciudad') or '?'})")
    elif '--sala-igual' in a:
        sid, v, c = _arg('--sala-igual', 3)
        print('✓ salas:', ', '.join(sala_igual(sid, v, c, pq)['salas']))
    elif '--corto' in a:
        sid, txt = _arg('--corto', 2)
        print(f"✓ {sid} sale como «{fijar_corto(sid, txt, pq)['corto']}»")
    elif '--nombrar' in a:
        sid, txt = _arg('--nombrar', 2)
        print('✓ variantes:', ', '.join(nombrar(sid, txt, pq)))
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
    elif '--resolver' in a:
        fid = _arg('--resolver')
        acept = dict(x.split('=', 1) for x in a[a.index('--aceptar') + 1:] if '=' in x) if '--aceptar' in a else {}
        c = tuple(map(float, _arg('--centro').split(','))) if '--centro' in a else None
        r = resolver(fid, escribir='--escribir' in a, aceptar=acept, centro=c)
        for cr, x in r['ya']:
            print(f'  ya        {cr}')
        for cr, x in r['conocida']:
            print(f'  CONOCIDA  {cr}  →  {x}')
        for cr, cs in r['parecida']:
            print(f'  ¿PARECIDA? {cr}')
            for p, sid, nom, ciu, d in cs:
                print(f'              {sid}  {nom} ({ciu or "?"}) · similitud {p}{f" · a {d} m" if d is not None else ""}')
        for cr, url in r['nueva']:
            print(f'  NUEVA     {cr}  →  buscar en Maps: {url}')
        print(f"{len(r['ya'])} ya · {len(r['conocida'])} conocidas{' (escritas)' if '--escribir' in a else ' (--escribir para aplicarlas)'}"
              f" · {len(r['parecida'])} para confirmar (--aceptar «cruda=s_xxx») · {len(r['nueva'])} nuevas")
    elif '--enlazar' in a:
        r = enlazar()
        print(f'✓ {sum(r.values())} pines enlazados en {len(r)} festivales' if r else '✓ todo enlazado')
    elif '--completar-ciudades' in a:
        for n, c, f in completar_ciudades():
            print(f'  {n:50} → {c}  ({f})')
        print(f'sin ciudad: {sum(1 for e in leer()["sedes"].values() if not e.get("ciudad"))}')
    elif '--tablero' in a:
        for fid, r, flojos, sin_maps in tablero():
            pend = len(r['conocida']) + len(r['parecida']) + len(r['nueva'])
            print(f'{fid:28} sin pin {pend:>2} (conocidas {len(r["conocida"])}, parecidas {len(r["parecida"])}, nuevas {len(r["nueva"])})'
                  f' · pines flojos {len(flojos):>2} · lugares sin Maps {len(sin_maps):>2}')
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
