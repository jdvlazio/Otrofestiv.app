#!/usr/bin/env python3
"""festicine-antioquia-2026-verificar.py — la lectura ciega (otro agente, sin ver el
repo) y el OCR del PDF contra el build: día, hora, sede, sala, título y minutos."""
import io, json, os, re, sys, unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from ocr import leer  # noqa: E402

FID = 'festicine-antioquia-2026'
SRC = f'{REPO}/fuentes/{FID}'
CLAVE = {'Universidad de Antioquia': 'Universidad', 'Museo Juan': 'Museo', 'Hotel Mariscal': 'Mariscal',
         'Cámara de Comercio': 'Cámara', 'Plaza Mayor': 'Plaza Mayor', 'Sede de empleo': 'Comfenalco',
         'Barrio La Esmeralda': 'Esmeralda', 'Barrio Llano': 'Llano', 'Catedral': 'Catedral'}
# lo que el verificador corrige del impreso, con porqué en -duraciones y -correcciones
MIN_IMPRESO = {'Toni Erdmann': 182, 'Die Odyssee': 122, 'Almanya – Willkommen in Deutschland': 116, 'Aunque seamos islas': 69}


def n(s):
    s = unicodedata.normalize('NFD', str(s)).lower()
    return ''.join(c for c in s if c.isalnum() and not unicodedata.combining(c))


b = json.load(io.open(f'{REPO}/festivals/staging/{FID}-build.json', encoding='utf-8'))['films']
ciega = json.load(io.open(f'{SRC}/lectura-2.json', encoding='utf-8'))
ocr = ' '.join(x if isinstance(x, str) else json.dumps(x, ensure_ascii=False)
               for x in [leer([f'{SRC}/pdf/p-1.png']), leer([f'{SRC}/pdf/p-2.png'])])
o_n = n(ocr)
err, aviso, libres = [], [], list(ciega)
for f in b:
    if not '2026-12-04' <= f['day'] <= '2026-12-08':
        err.append(f'{f["title"]}: fuera de los días oficiales')
    kw = next(v for k, v in CLAVE.items() if f['venue'].startswith(k))
    cand = [c for c in libres if c['dia'] == f['day'] and c['hora'] == f['time'] and kw in c['lugar']
            and (('Aula 201' in c['lugar']) == (f.get('sala') == 'Aula 201'))]
    if len(cand) != 1:
        err.append(f'{f["day"]} {f["time"]} {f["title"]}: {len(cand)} filas en la lectura ciega')
        continue
    c = cand[0]
    libres.remove(c)
    todo = n(' '.join(c['lineas']) + c['rotulo'] + c['lugar'] + ' '.join(o['titulo'] for o in c['obras']))
    for o in f.get('film_list') or [f]:
        pal = [n(w) for w in re.findall(r'\w+', o['title']) if len(w) > 3]
        if [w for w in pal if w not in todo]:
            err.append(f'{f["day"]} {f["time"]} {o["title"]}: no está así en la lectura ciega')
        if [w for w in pal if w not in o_n]:
            aviso.append(f'{o["title"]}: OCR no lee {[w for w in pal if w not in o_n]}')
        x = next((q for q in c['obras'] if n(q['titulo']) == n(o['title'])), None)
        if x and x.get('min') and o.get('duration') and int(re.sub(r'\D', '', str(x['min']))) != int(o['duration'].split()[0]):
            if MIN_IMPRESO.get(o['title']) != int(re.sub(r'\D', '', str(x['min']))):
                err.append(f'{o["title"]}: {o["duration"]} ≠ {x["min"]}')
for c in libres:
    err.append(f'en el PDF y no en el build: {c["dia"]} {c["hora"]} {c["lineas"][:1]}')
print(f'{len(b)} funciones contra {len(ciega)} filas')
for x in sorted(set(aviso)):
    print('  · OCR parcial (visto a ojo):', x)
if err:
    sys.exit('✗ ' + '\n✗ '.join(err))
print('✓ build = PDF')
