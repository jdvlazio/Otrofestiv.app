# -*- coding: utf-8 -*-
"""Geocodifica las sedes de FICDEH a un SIDECAR persistente.

Por qué sidecar y no el build: el ensamblador regenera el build desde cero, así
que cualquier coordenada escrita ahí se pierde en la siguiente pasada (pasó el
5 ago: 136 sedes geocodificadas, borradas al re-ensamblar). El sidecar se
acumula y el ensamblador lo mergea.

Cascada por sede (la primera que VERIFIQUE, gana):
  1. Photon por NOMBRE de la sede, con sesgo al centroide de la ciudad  → `poi`
  2. Nominatim por DIRECCIÓN postal normalizada + ciudad               → `calle`
  3. Nominatim por NOMBRE + ciudad                                     → `poi`
  4. Centroide de la ciudad                                            → `ciudad`

Todo candidato se verifica: debe caer dentro de MAX_KM del centroide de su
ciudad y NO sobre él. Sin esa verificación —el modo de fallo de la v1, que
pedía limit=1 y aceptaba lo que viniera— Nominatim responde con la ciudad
entera a una dirección colombiana que no conoce, y la sede queda apilada en el
centroide marcada como OK: así terminaron 63 de 120 sedes en 10 puntos.

El script del pipeline (scripts/geocode-venues.py) devuelve 0 resultados contra
Nominatim porque no manda User-Agent — aquí se manda.
"""
import json, re, time, math, subprocess, urllib.parse, collections, os, unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEO = f'{REPO}/festivals/staging/ficdeh-2026-venues-geo.json'
PROG = f'{REPO}/festivals/staging/ficdeh-2026-programacion-oficial.json'
UA = 'Otrofestiv-pipeline/1.0 (contacto@otrofestiv.app)'
VENTANA = {f'2026-08-{d}' for d in range(12, 20)}
MAX_KM = 30          # radio máximo respecto al centroide de la ciudad
MISMO_PUNTO_M = 60   # más cerca que esto del centroide = ES el centroide

CENTROIDES = {
    'Bogotá': (4.6533817, -74.0836331), 'Medellín': (6.2697292, -75.6025622),
    'Cali': (3.4516467, -76.5319854),   'Barranquilla': (11.0101922, -74.8231794),
    'Cartagena': (10.4265566, -75.5441671), 'Pereira': (4.7854606, -75.7883220),
    'Manizales': (5.0743694, -75.5081209), 'Armenia': (4.4919865, -75.7413996),
    'Ibagué': (4.4386033, -75.2322204),  'Quibdó': (5.6912838, -76.6531337),
    'Tunja': (5.5317862, -73.3688625),
}

# Sub-salas de una sede ya ubicada: heredan su punto (OSM no indexa salas).
ALIAS = {
    'Sala 2 - Cinemateca de Bogotá - Bogotá':            'Cinemateca de Bogotá - Bogotá',
    'Laboratorio 1 y 2 - Cinemateca de Bogotá - Bogotá': 'Cinemateca de Bogotá - Bogotá',
    'Sala 2 de la Cinemateca - Bogotá':                  'Cinemateca de Bogotá - Bogotá',
    'Laboratorio 1 y 2 - Bogotá':                        'Cinemateca de Bogotá - Bogotá',
    'Auditorio C202 - UNIMINUTO - Bogotá':               'Universidad Minuto de Dios - Bogotá',
    'UNIVERSIDAD TECNOLÓGICA DE PEREIRA - BLOQUE 7A / 118 - Pereira':
        'Universidad Tecnológica de Pereira -UTP - Pereira',
    'Universidad Tecnológica de Pereira - Bloque 13, Sala Magistral 1 - Pereira':
        'Universidad Tecnológica de Pereira -UTP - Pereira',
    # misma dirección que la Cinemateca Fontanar: son el mismo CEFE
    'Biblioteca Pública CEFE Fontanar Del Río - Bogotá': 'Cinemateca Fontanar del Río - Bogotá',
}

ABREV = [(r'\bCra\.?\b|\bCr\.?\b|\bKra\.?\b', 'Carrera'), (r'\bCl\.?\b|\bCll\.?\b', 'Calle'),
         (r'\bDg\.?\b|\bDiag\.?\b', 'Diagonal'), (r'\bAv\.?\b', 'Avenida'),
         (r'\bTv\.?\b|\bTrans\.?\b', 'Transversal'), (r'\bAut\.?\b', 'Autopista')]


def http(url):
    r = subprocess.run(['curl', '-sL', '--compressed', '--max-time', '30',
                        '-H', f'User-Agent: {UA}', url], capture_output=True)
    try:
        return json.loads(r.stdout.decode('utf-8', 'ignore'))
    except Exception:
        return None


def km(a, b):
    (la1, lo1), (la2, lo2) = a, b
    p = math.pi / 180
    h = (math.sin((la2 - la1) * p / 2) ** 2 +
         math.cos(la1 * p) * math.cos(la2 * p) * math.sin((lo2 - lo1) * p / 2) ** 2)
    return 12742 * math.asin(math.sqrt(h))


def normaliza_dir(d):
    """'Cra. 6 Nº 23-58, piso 3, barrio X' → 'Carrera 6 23-58'."""
    d = re.sub(r'\(.*?\)', ' ', d or '')
    d = re.split(r',|\bpiso\b|\blocal\b|\bbarrio\b|\bfrente\b|\bsobre\b', d, flags=re.I)[0]
    for pat, rep in ABREV:
        d = re.sub(pat, rep, d, flags=re.I)
    d = d.replace('#', ' ').replace('Nº', ' ').replace('N°', ' ')
    return re.sub(r'\s+', ' ', d).strip()


def valida(lat, lng, ciudad):
    """Un candidato solo vale si cae DENTRO de la ciudad y NO es su centroide."""
    c = CENTROIDES.get(ciudad)
    if not c:
        return False
    d = km((lat, lng), c)
    return d * 1000 > MISMO_PUNTO_M and d < MAX_KM


# Palabras que casi toda sede comparte: no distinguen una de otra. Photon hace
# match difuso, así que sin este filtro "Casa de la Juventud Chapinero" cae en
# la Casa de la Juventud de Mártires, y "Casa de la Juventud Antonio Nariño" en
# la Casa de Nariño. Un POI falso es peor que el centroide honesto: manda al
# usuario a caminar al lugar equivocado con plena confianza.
GENERICAS = {
    'casa', 'juventud', 'biblioteca', 'publica', 'centro', 'cultural', 'comunitario',
    'comunitaria', 'sala', 'auditorio', 'teatro', 'universidad', 'fundacion', 'cine',
    'cineclub', 'club', 'museo', 'parque', 'colegio', 'institucion', 'educativa',
    'plaza', 'plazoleta', 'comercial', 'principal', 'salon', 'bloque', 'piso',
    'de', 'del', 'la', 'el', 'los', 'las', 'y', 'en', 'para', 'sede', 'arte',
    'nacional', 'departamental', 'deptal', 'municipal', 'distrital', 'festival',
    # la ciudad va en toda consulta: coincide siempre y no distingue nada
    'bogota', 'medellin', 'cali', 'barranquilla', 'cartagena', 'pereira',
    'manizales', 'armenia', 'ibague', 'quibdo', 'tunja', 'colombia',
}


def _tok(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return [t for t in re.findall(r'[a-z0-9]+', s) if len(t) > 2]


def nombre_coincide(pedido, hallado):
    """El POI hallado debe compartir tokens DISTINTIVOS con el pedido.

    Con dos o más tokens propios se exigen dos coincidencias: uno solo deja
    pasar «Casa de la Juventud Antonio Nariño» → «Casa de Nariño».
    """
    a, b = _tok(pedido), _tok(hallado)
    propios = {t for t in a if t not in GENERICAS}
    if not propios:
        return len(set(a) & set(b)) >= 2   # sin tokens propios: exigir 2 comunes
    # Las siglas (UTP, EAM, MAMB) rara vez están en OSM: si hay tokens largos,
    # no cuentan para el umbral — si no, «… de Pereira -UTP» exigiría dos
    # aciertos y rechazaría su propio match bueno.
    largos = {t for t in propios if len(t) > 4}
    if largos:
        propios = largos
    hits = sum(1 for t in propios if t in b)
    return hits >= (2 if len(propios) >= 2 else 1)


def direccion_coincide(pedida, hallada):
    """Verifica un resultado de dirección.

    OSM suele devolver la VÍA sin placa («Calle 65, Palogrande») — eso es
    precisión de cuadra y vale. Lo que no vale es otra vía: basta comparar el
    primer número, el de la vía. Si no hay número que comparar, se cae al
    match por nombre contra la sede o contra la dirección cruda (que a veces
    nombra el sitio: «Centro Comercial El Caraño Calle 30»).
    """
    via = re.findall(r'\d+[a-zA-Z]?', normaliza_dir(pedida))
    if via and via[0].lower() in {t.lower() for t in re.findall(r'\d+[a-zA-Z]?', hallada)}:
        return True
    return nombre_coincide(pedida, hallada)


def photon(nombre, ciudad):
    c = CENTROIDES[ciudad]
    r = http(f'https://photon.komoot.io/api/?limit=5&lat={c[0]}&lon={c[1]}&q=' +
             urllib.parse.quote(f'{nombre} {ciudad}'))
    for f in (r or {}).get('features', []):
        lon, lat = f['geometry']['coordinates']
        hallado = f['properties'].get('name', '')
        if valida(lat, lon, ciudad) and nombre_coincide(nombre, hallado):
            return lat, lon, hallado
    return None


def nominatim(q, ciudad, exigir_nombre=None, exigir_dir=None):
    r = http('https://nominatim.openstreetmap.org/search?format=json&limit=5&countrycodes=co&q=' +
             urllib.parse.quote(q))
    for x in (r or []):
        lat, lon = float(x['lat']), float(x['lon'])
        etq = x.get('display_name', '')[:70]
        if not valida(lat, lon, ciudad):
            continue
        if exigir_nombre and not nombre_coincide(exigir_nombre, etq):
            continue
        if exigir_dir and not direccion_coincide(exigir_dir, etq):
            continue
        return lat, lon, etq
    return None


def photon_dir(direccion, ciudad):
    """Segundo intento por dirección: Photon cubre direcciones colombianas que
    Nominatim no tiene, pero hace match difuso — de ahí la verificación."""
    c = CENTROIDES[ciudad]
    d = normaliza_dir(direccion)
    if not d:
        return None
    r = http(f'https://photon.komoot.io/api/?limit=5&lat={c[0]}&lon={c[1]}&q=' +
             urllib.parse.quote(f'{d} {ciudad}'))
    for f in (r or {}).get('features', []):
        lon, lat = f['geometry']['coordinates']
        p = f['properties']
        etq = ' '.join(x for x in (p.get('name'), p.get('street'), p.get('housenumber')) if x)
        if valida(lat, lon, ciudad) and direccion_coincide(direccion, etq):
            return lat, lon, etq
    return None


def main():
    prog = json.load(open(PROG, encoding='utf-8'))['funciones']
    geo = json.load(open(GEO, encoding='utf-8')) if os.path.exists(GEO) else {}

    n = collections.Counter()
    info = {}
    for f in prog:
        if not (f.get('en_app') and f['dia'] in VENTANA):
            continue
        k = f"{f['sede']} - {f['ciudad']}"
        n[k] += 1
        d = (f.get('direccion') or '').strip()
        if k not in info or (d and not info[k]['dir']):
            info[k] = {'sede': f['sede'], 'ciudad': f['ciudad'], 'dir': d}

    orden = sorted(info, key=lambda k: -n[k])
    print(f'{len(orden)} sedes con funciones en la ventana 12–19 AGO\n', flush=True)
    stats = collections.Counter()

    for i, k in enumerate(orden, 1):
        v = info[k]
        ciudad = v['ciudad']
        if ciudad not in CENTROIDES:
            print(f'[{i:3}] ⚠️  ciudad desconocida: {ciudad} ({k})', flush=True)
            continue

        r = photon(v['sede'], ciudad); prec = 'poi'; time.sleep(1.1)
        if not r and v['dir']:
            d = normaliza_dir(v['dir'])
            if d:
                r = nominatim(f'{d}, {ciudad}, Colombia', ciudad, exigir_dir=v['dir'])
                prec = 'calle'; time.sleep(1.1)
        if not r:
            r = nominatim(f"{v['sede']}, {ciudad}, Colombia", ciudad, exigir_nombre=v['sede'])
            prec = 'poi'; time.sleep(1.1)
        if not r and v['dir']:
            r = photon_dir(v['dir'], ciudad); prec = 'calle'; time.sleep(1.1)

        if r:
            lat, lng, etq = r
            geo[k] = {'lat': lat, 'lng': lng, 'city': ciudad, 'short': v['sede'],
                      'address': v['dir'], '_prec': prec, '_match': etq}
            stats[prec] += 1
            print(f'[{i:3}] {n[k]:3}f {prec:6} {k[:50]:51} → {lat:.5f},{lng:.5f}  {etq[:38]}', flush=True)
        else:
            c = CENTROIDES[ciudad]
            geo[k] = {'lat': c[0], 'lng': c[1], 'city': ciudad, 'short': v['sede'],
                      'address': v['dir'], '_prec': 'ciudad',
                      '_geo': 'CENTROIDE de ciudad — sede no hallada, revisar antes de publicar'}
            stats['ciudad'] += 1
            print(f'[{i:3}] {n[k]:3}f ⚠️CIUD {k[:50]:51} sin resolver', flush=True)

        if i % 10 == 0:
            json.dump(geo, open(GEO, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    # Sub-salas: no son sedes distintas, son salas dentro de una ya ubicada.
    # OSM no las conoce, así que heredan el punto de su sede madre.
    for k, madre in ALIAS.items():
        src = geo.get(madre, {})
        if k in geo and src.get('lat') and src.get('_prec') in ('poi', 'calle'):
            geo[k] = {**geo[k], 'lat': src['lat'], 'lng': src['lng'],
                      '_prec': 'alias', '_match': f'hereda de «{madre}»'}
            geo[k].pop('_geo', None)
            stats['ciudad'] -= 1
            stats['alias'] += 1
            print(f'      alias  {k[:50]:51} ← {madre[:38]}', flush=True)

    json.dump(geo, open(GEO, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'\nRESUMEN: {dict(stats)}\nsidecar: {len(geo)} sedes', flush=True)
    faltan = [k for k in orden if geo.get(k, {}).get('_prec') == 'ciudad']
    if faltan:
        print(f'\n⚠️ {len(faltan)} sedes sin resolver (centroide) — revisar a mano:')
        for k in sorted(faltan, key=lambda x: -n[x]):
            print(f'   {n[k]:3}f {k}')


if __name__ == '__main__':
    main()
