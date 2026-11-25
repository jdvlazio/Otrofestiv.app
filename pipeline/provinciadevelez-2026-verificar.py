#!/usr/bin/env python3
"""provinciadevelez-2026-verificar.py — 2.ª lectura: Vision (pipeline/ocr.py) lee día,
hora y título de cada obra en las láminas del post de su función, contra el build."""
import glob, json, os, re, sys, unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from ocr import leer  # noqa: E402

IG = f'{REPO}/fuentes/provinciadevelez-2026/ig'
# lo que la lámina imprime distinto, y la segunda lámina de la misma función
FB = 'pfbid02fqEztN5KAMM1Ro3k4YYZ61BBVJwtd7myTLcnZyVFp8qtAkX3ygDGrYRBDc18297Ul'
POSTS = {FB: ['fb-1581240617371136'], 'DfxyKI-S9LA': ['DfxyKI-S9LA', 'DfzhWP2x_sy']}
IMPRESO = {'El pescador (videoclip)': 'El pescador', 'El fantástico Sr. Fox': 'Fantastic Mr Fox'}
A_OJO = {'Saint Juanito'}   # título dibujado en el afiche (lámina 01 de Df7ZYXrEaXh)


def n(s):
    s = unicodedata.normalize('NFD', str(s)).lower()
    return ''.join(c for c in s if c.isalnum() and not unicodedata.combining(c))


b = json.load(open(f'{REPO}/festivals/staging/provinciadevelez-2026-build.json', encoding='utf-8'))['films']
err, ojo = [], []
for f in b:   # solo días oficiales: el afiche dice 1 al 6 de diciembre (Juan, 24 nov)
    if not '2026-12-01' <= f['day'] <= '2026-12-06':
        err.append(f'{f["title"]}: {f["day"]} fuera de los días oficiales')
for f in b:
    sc = f['_src']['url'].rstrip('/').split('/')[-1]
    txt = ''
    for p in POSTS.get(sc, [sc]):
        for im in sorted(glob.glob(f'{IG}/{p}/*.jpg')):
            r = leer([im])
            txt += ' ' + (r if isinstance(r, str) else json.dumps(r, ensure_ascii=False))
    t = n(txt)
    d, h = int(f['day'][-2:]), int(f['time'][:2]) - 12
    if f'{d}dediciembre' not in t and f'{d}denoviembre' not in t:
        err.append(f'{f["title"]}: el día {d} no se lee')
    if not re.search(rf'(?<!\d){h}(:00)?\s*(P\.?\s?M|DE LA TARDE)', txt, re.I):
        err.append(f'{f["title"]}: la hora {h} no se lee')
    for o in f.get('film_list') or [f]:
        i = IMPRESO.get(o['title'], o['title'])
        pal = [w for w in re.findall(r'\w+', i) if len(w) > 2]
        falta = [w for w in pal if n(w) not in t]
        if falta:
            (ojo if len(falta) < len(pal) or o['title'] in A_OJO else err).append(f'{o["title"]}: sin leer {falta}')
print(f'{len(b)} funciones, {sum(len(f.get("film_list") or [1]) for f in b)} obras')
for x in ojo:
    print('  · parcial (confirmado a ojo 24 nov):', x)
if err:
    sys.exit('✗ ' + '\n✗ '.join(err))
print('✓ build = láminas')
