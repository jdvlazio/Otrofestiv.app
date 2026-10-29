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
if fallos:
    sys.exit('✗ ' + '\n✗ '.join(fallos))
print(f'✓ las {n} obras del catálogo = las {n} imágenes de las 4 páginas, título y año')
