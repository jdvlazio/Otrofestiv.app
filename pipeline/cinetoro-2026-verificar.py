#!/usr/bin/env python3
"""cinetoro-2026-verificar.py — el catálogo contra una SEGUNDA lectura de la web.

Independiente del lector del catálogo: no lee el texto de los bloques sino los
NOMBRES DE ARCHIVO de las imágenes que subió el festival a uploads/2026/10
(«Titulo-Director-Lugar-Año-1024x1024.png»). En las dos direcciones, por página:
toda imagen tiene su obra (título al inicio del nombre, y el año si lo trae), y
toda obra su imagen. Las discrepancias que el festival escribió distinto en la
imagen y en el texto están declaradas abajo con su porqué; cualquier otra frena.
"""
import io, json, os, re, sys, unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def plano(t):
    t = ''.join(c for c in unicodedata.normalize('NFD', t.lower()) if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', '-', t).strip('-')


# imagen → título del catálogo, cuando la imagen lo escribe distinto
ALIAS = {'la-gargante-del-diablo': 'La garganta del diablo',   # errata en el nombre de la imagen
         'haswe-clouds': 'ḤAŚWƐ: Clouds Seen from a Distance Before the Sea Wind Comes'}
cat = json.load(io.open(f'{REPO}/festivals/staging/cinetoro-2026-catalogo.json', encoding='utf-8'))['obras']
fallos, n = [], 0
for url in sorted({o['_src']['url'] for o in cat}):
    slug = url.rstrip('/').rsplit('/', 1)[1]
    s = io.open(f'{REPO}/fuentes/cinetoro-2026/{slug}.html', encoding='utf-8').read()
    imgs = list(dict.fromkeys(re.findall(r'uploads/2026/10/([^"\s]+?)(?:-\d+x\d+)?\.png', s)))
    obras = [o for o in cat if o['_src']['url'] == url]
    libres = list(obras)
    for im in imgs:
        p = plano(im)
        o = next((o for o in libres if p.startswith(plano(o['titulo']))
                  or any(p.startswith(a) and o['titulo'] == t for a, t in ALIAS.items())), None)
        if not o:
            fallos.append(f'{slug}: imagen sin obra: {im}')
            continue
        libres.remove(o)
        anio = re.search(r'-(20\d\d)(?:-\d)?$', p)
        if anio and int(anio.group(1)) != o['anio']:
            fallos.append(f'{o["titulo"]}: año {o["anio"]} y la imagen dice {anio.group(1)}')
        n += 1
    fallos += [f'{slug}: obra sin imagen: {o["titulo"]}' for o in libres]
print(f'✓ las {n} obras del catálogo = las {n} imágenes de las 4 páginas, título y año')

# ── EL BUILD CONTRA LA PARRILLA (31 oct 2026) ────────────────────────────────
# Otra lectura, sin el parser del crudo: del HTML crudo de la parrilla se sacan
# TOKENS (día dd/mm, hora hh:mm) con un regex sobre el texto plano, y se exige,
# en los dos sentidos, que cada función del build esté en la parrilla y que
# cada par día+hora de los días incluidos esté en el build (salvo lo de _fuera).
_b = f'{REPO}/festivals/staging/cinetoro-2026-build.json'
if os.path.exists(_b):
    build = json.load(io.open(_b, encoding='utf-8'))['films']
    raw = io.open(f'{REPO}/fuentes/cinetoro-2026/programacion-2026-2.html', encoding='utf-8').read()
    txt = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', raw))
    pares = set()
    for m in re.finditer(r'Fecha:(.*?)Lugar:(.*?)Hora:\s*(\D{0,30}\d{2}:\d{2})', txt):
        dias = re.findall(r'(\d{1,2})\s*/\s*(\d{2})\s*/\s*2026', m.group(1))
        h = re.search(r'\d{2}:\d{2}', m.group(3)).group()
        for d, mes in dias:
            pares.add((f'2026-{mes}-{int(d):02d}', h))
    en_build = {(f['day'], f['time']) for f in build}
    multi = {('2026-11-13', '15:00'), ('2026-11-14', '09:00')}   # 2.ª sesión del taller de archivo: «Viernes de 15:00…; Sábado de 09:00…»
    fuera_b = sorted(x for x in en_build - pares - multi)
    oficiales = {x for x in pares if '2026-11-10' <= x[0] <= '2026-11-15' or x[0] == '2026-11-07'}
    # el laboratorio (11–14) y los talleres de Cali (9–11) caen en esas fechas y están fuera a propósito
    # el Laboratorio (11–14 nov, 09:00) y los talleres de Cali/Univalle (9–11 nov,
    # 09:00) caen en estas fechas y están fuera a propósito (crudo `_fuera`)
    excluidos = {(f'2026-11-{d}', '09:00') for d in ('10', '11', '12', '13', '14')}
    # el regex lee la PRIMERA hora del bloque del taller de archivo («Viernes de
    # 15:00…; Sábado de 09:00…») para los dos días: el sábado 15:00 no existe
    excluidos.add(('2026-11-14', '15:00'))
    fuera_p = sorted(oficiales - en_build - excluidos)
    if fuera_b:
        fallos.append(f'funciones del build sin par día/hora en la parrilla: {fuera_b}')
    if fuera_p:
        fallos.append(f'pares día/hora de la parrilla que no están en el build: {fuera_p}')
    # cada obra de un programa del build, nombrada en programas-2 (título o dirección)
    rp = plano(re.sub(r'<[^>]+>', ' ', io.open(f'{REPO}/fuentes/cinetoro-2026/programas-2.html', encoding='utf-8').read()))
    nob = 0
    for f in build:
        for o in f.get('film_list') or []:
            nob += 1
            if plano(o['title'])[:18] not in rp and plano((o.get('director') or 'x').split(',')[0])[:12] not in rp:
                fallos.append(f'{f["title"]}: «{o["title"]}» no aparece en programas-2')
    # cada sede con pin
    geo = json.load(io.open(f'{REPO}/festivals/staging/cinetoro-2026-venues-geo.json', encoding='utf-8'))
    for v in sorted({f['venue'] for f in build}):
        if not (geo.get(v) or {}).get('lat'):
            fallos.append(f'sede sin pin: {v}')
    print(f'✓ build: {len(build)} funciones contra la parrilla, {nob} obras de programa contra programas-2, sedes con pin')
if fallos:
    sys.exit('✗ ' + '\n✗ '.join(fallos))
