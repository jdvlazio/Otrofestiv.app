#!/usr/bin/env python3
"""aleste-2026-verificar.py — segunda lectura del crudo de Al Este contra las fuentes.

Camino distinto del crudo (que se transcribió a ojo):
  · MAMM: lee la fecha y hora impresas en cada ficha HTML («19 noviembre, jueves
    - 6:30 p.m.») y las compara con la función del crudo.
  · Colombo: lee las láminas con la OCR del sistema (pipeline/ocr.py) y exige que
    «DD.11 | HH:MM» de cada función esté pintado en SU lámina.
Sale con error si algo no casa.
"""
import html, io, json, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from ocr import leer  # noqa: E402

crudo = json.load(io.open(f'{REPO}/festivals/staging/aleste-2026-crudo.json', encoding='utf-8'))['funciones']
fallos, ok = [], 0
laminas = {}
for f in crudo:
    src = f['_src']
    if 'elmamm.org' in src['url']:
        slug = src['url'].rstrip('/').rsplit('/', 1)[1]
        t = html.unescape(re.sub(r'<[^>]+>', ' ', io.open(f'{REPO}/fuentes/aleste-2026/mamm-{slug}.html', encoding='utf-8').read()))
        m = re.search(r'(\d{1,2}) noviembre, \w+ - (\d{1,2}):(\d\d) ([ap])\.m\.', t)
        if not m:
            fallos.append(f'{f["titulo"]}: la ficha del MAMM no trae fecha'); continue
        h = int(m.group(2)) % 12 + (12 if m.group(4) == 'p' else 0)
        leido = (f'2026-11-{int(m.group(1)):02d}', f'{h:02d}:{m.group(3)}')
        if leido != (f['dia'], f['hora']):
            fallos.append(f'{f["titulo"]}: MAMM dice {leido}, crudo {(f["dia"], f["hora"])}')
        else:
            ok += 1
    elif src.get('lamina'):
        post = src['url'].rstrip('/').rsplit('/', 1)[1]
        laminas.setdefault(f'{REPO}/fuentes/ig/{post}/{src["lamina"]}', []).append(f)

lec = leer(list(laminas))
for ruta, fs in laminas.items():
    txt = re.sub(r'\s+', '', ' '.join(lec.get(ruta, [])))
    for f in fs:
        clave = f'{f["dia"][-2:]}.11'
        if clave in txt and f['hora'] in txt:
            ok += 1
        else:
            fallos.append(f'{f["titulo"]}: la lámina {os.path.relpath(ruta, REPO)} no muestra {clave} {f["hora"]}')

if fallos:
    sys.exit('✗ ' + '\n✗ '.join(fallos))
print(f'✓ {ok} funciones verificadas contra MAMM y láminas (la inaugural se cruza con el pie de p/DfkttriN6pD a mano)')
