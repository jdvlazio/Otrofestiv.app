#!/usr/bin/env python3
"""sedes.py — la MATRIZ de sedes: un pin por lugar, para todos los festivales.

POR QUÉ (16 nov 2026, Juan: «así como hay una de películas, las sedes deberían
vivir en un archivo matriz para no repetir procesos»). Cada festival tenía su
`<fid>-venues-geo.json` y una sede repetida se copiaba a mano de otro festival.
Medido ese día: 319 pines de 277 lugares; 29 lugares en 2+ festivales (la
Cinemateca de Bogotá 6 veces, el Colombo Americano 5, Fontanar 4) y en varios
las copias ya no coincidían: la Jorge Tadeo con 3 pines, Brisas de Mayo con
dos a 500 m.

EL MODELO. `catalogo/sedes.json`:
    {"sedes": {"<id>": {"nombre", "lat", "lng", "address"?, "_prec", "fuente",
                        "festivales": [fid…], "nombres": [grafías vistas]}},
     "_divergentes": {"<id>": [{"fid", "lat", "lng"}…]}}
Un LUGAR es un nombre (plano) + dónde está: dos «Parque principal» a 30 km
son dos lugares (homónimos de pueblos distintos), no un error. Se agrupan los
pines del mismo nombre que caen a menos de MISMO_LUGAR_M; si dentro de un
grupo hay pines a más de TOLERANCIA_M, el lugar queda en `_divergentes` hasta
que una persona elija el bueno (`--elegir`).

    python3 pipeline/sedes.py --construir            # arma la matriz desde los venues-geo
    python3 pipeline/sedes.py --buscar "Cinemateca de Bogotá" 4.61,-74.07
    python3 pipeline/sedes.py --elegir <id> <fid>    # resuelve una divergencia con el pin de ese festival
    python3 pipeline/sedes.py --divergentes          # qué falta resolver

La consulta la usa geocodificar.py ANTES de Nominatim: una sede conocida entra
con el pin ya verificado (`_prec: matriz`). El guardián [sede-matriz] de
validate.py frena un pin de festival que se aparta de su lugar en la matriz.
"""
import glob, json, math, os, re, sys, unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
MATRIZ = f'{REPO}/catalogo/sedes.json'
MISMO_LUGAR_M = 2000     # mismo nombre a menos de esto: el mismo lugar (o el mismo pueblo)
TOLERANCIA_M = 120       # dentro de un lugar, pines a más de esto: divergencia
PREC_ORDEN = ('manual', 'direccion', 'nominatim', 'matriz')   # la verificación más fuerte gana


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


def _rango(prec):
    return PREC_ORDEN.index(prec) if prec in PREC_ORDEN else len(PREC_ORDEN)


def agrupar(ps):
    """Por nombre plano, grupos de pines a menos de MISMO_LUGAR_M entre sí."""
    por_nombre = {}
    for x in ps:
        por_nombre.setdefault(plano(x[2]), []).append(x)
    grupos = []
    for n, xs in sorted(por_nombre.items()):
        gs = []
        for x in xs:
            pt = (x[3]['lat'], x[3]['lng'])
            g = next((g for g in gs if any(metros(pt, (y[3]['lat'], y[3]['lng'])) < MISMO_LUGAR_M for y in g)), None)
            (g.append(x) if g is not None else gs.append([x]))
        grupos += [(n, g) for g in gs]
    return grupos


def construir(raiz=REPO):
    previa = leer(raiz)
    sedes, div = {}, {}
    for n, g in agrupar(pines(raiz)):
        g.sort(key=lambda x: (_rango(x[3].get('_prec')), x[0]))
        base = g[0]
        lat0, lng0 = base[3]['lat'], base[3]['lng']
        sid = f'{n}@{round(lat0, 2)},{round(lng0, 2)}'
        # una divergencia ya resuelta a mano manda (--elegir); si no, la más verificada
        elegido = (previa.get('sedes') or {}).get(sid, {})
        if elegido.get('_elegido_de'):
            lat0, lng0 = elegido['lat'], elegido['lng']
        e = {'nombre': base[2], 'lat': lat0, 'lng': lng0, '_prec': base[3].get('_prec') or 'sin dato',
             'fuente': f'{base[0]}-venues-geo.json', 'festivales': sorted({x[0] for x in g}),
             'nombres': sorted({x[1] for x in g})}
        if base[3].get('address'):
            e['address'] = base[3]['address']
        if elegido.get('_elegido_de'):
            e.update(_elegido_de=elegido['_elegido_de'], fuente=elegido['fuente'], _prec=elegido['_prec'])
        lejos = [x for x in g if metros((lat0, lng0), (x[3]['lat'], x[3]['lng'])) > TOLERANCIA_M]
        if lejos and not elegido.get('_elegido_de'):
            div[sid] = [{'fid': x[0], 'clave': x[1], 'lat': x[3]['lat'], 'lng': x[3]['lng'],
                         '_prec': x[3].get('_prec'),
                         'a_m': round(metros((lat0, lng0), (x[3]['lat'], x[3]['lng'])))} for x in g]
        sedes[sid] = e
    d = {'_provenance': {'fuente': 'festivals/staging/*-venues-geo.json', 'construido_por': 'pipeline/sedes.py --construir',
                         'regla': f'mismo nombre a <{MISMO_LUGAR_M} m = un lugar; pines a >{TOLERANCIA_M} m dentro de un lugar = divergencia'},
         'sedes': sedes, '_divergentes': div}
    json.dump(d, open(f'{raiz}/catalogo/sedes.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return d


def leer(raiz=REPO):
    p = f'{raiz}/catalogo/sedes.json'
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {}


def buscar(nombre, centro, radio_m=30000, raiz=REPO):
    """El lugar de la matriz con ese nombre más cercano a `centro` (lat, lng),
    dentro de `radio_m`. None si no hay, o si ese lugar está en divergencia
    (un pin dudoso no se reparte a otro festival)."""
    m = leer(raiz)
    n = plano(nombre_de(nombre))
    cands = [(metros(centro, (e['lat'], e['lng'])), sid, e) for sid, e in (m.get('sedes') or {}).items()
             if plano(e['nombre']) == n or n in {plano(nombre_de(k)) for k in e.get('nombres', [])}]
    cands = [c for c in cands if c[0] <= radio_m]
    if not cands:
        return None
    _, sid, e = min(cands, key=lambda c: c[0])
    if sid in (m.get('_divergentes') or {}):
        return None
    return {'lat': e['lat'], 'lng': e['lng'], '_prec': 'matriz', '_matriz': sid,
            '_match': f'matriz de sedes ({e["_prec"]}, de {e["fuente"]})',
            **({'address': e['address']} if e.get('address') else {})}


def elegir(sid, fid, raiz=REPO):
    m = leer(raiz)
    xs = (m.get('_divergentes') or {}).get(sid)
    if not xs:
        sys.exit(f'{sid} no está en divergencia')
    x = next((x for x in xs if x['fid'] == fid), None)
    if not x:
        sys.exit(f'{fid} no tiene pin para {sid}: {[y["fid"] for y in xs]}')
    m['sedes'][sid].update(lat=x['lat'], lng=x['lng'], _prec=x.get('_prec') or 'manual',
                           fuente=f'{fid}-venues-geo.json', _elegido_de=fid)
    json.dump(m, open(f'{raiz}/catalogo/sedes.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    construir(raiz)


def apartados(raiz=REPO):
    """Pines de festival que se apartan de su lugar resuelto en la matriz:
    [(fid, clave, sid, metros)]. Los lugares en divergencia no se miden: ya
    están en la lista de pendientes."""
    m = leer(raiz)
    S, D = m.get('sedes') or {}, m.get('_divergentes') or {}
    out = []
    for fid, k, nombre, v in pines(raiz):
        n = plano(nombre)
        for sid, e in S.items():
            if sid in D or plano(e['nombre']) != n:
                continue
            d = metros((e['lat'], e['lng']), (v['lat'], v['lng']))
            if d < MISMO_LUGAR_M and d > TOLERANCIA_M:
                out.append((fid, k, sid, round(d)))
    return out


def main():
    a = sys.argv
    if '--construir' in a:
        d = construir()
        print(f'✓ {len(d["sedes"])} lugares en catalogo/sedes.json · {len(d["_divergentes"])} con pines divergentes')
    elif '--buscar' in a:
        i = a.index('--buscar')
        print(json.dumps(buscar(a[i + 1], tuple(map(float, a[i + 2].split(',')))), ensure_ascii=False, indent=1))
    elif '--elegir' in a:
        i = a.index('--elegir')
        elegir(a[i + 1], a[i + 2])
        print(f'✓ {a[i + 1]}: pin de {a[i + 2]}')
    elif '--divergentes' in a:
        for sid, xs in (leer().get('_divergentes') or {}).items():
            print(sid)
            for x in xs:
                print(f'   {x["fid"]:28} {x["lat"]:.6f},{x["lng"]:.6f}  {x.get("_prec") or "":12} a {x["a_m"]} m')
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
