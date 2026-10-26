#!/usr/bin/env python3
"""funza-2026-verificar.py — el BUILD contra la agenda PDF, por DOS lecturas
que no comparten camino con la del crudo (que es la transcripción a ojo):

  B · la capa de texto del PDF (`pdftotext -raw`);
  C · el OCR del sistema sobre las páginas renderizadas (pipeline/ocr.py),
      que no lee la capa de texto sino los píxeles.

Compara TOKENS, no registros parseados: la franja horaria tal como se imprime
(«7:15 p. m. – 8:43 p. m.», sin espacios ni puntos) y el nombre de la actividad.
En las dos direcciones: toda función del build está en B y en C, y toda franja
de B está publicada o declarada como no publicable en el crudo.
La sede tiene pin verificado a mano.
"""
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from ocr import leer  # noqa: E402

FID = 'funza-2026'
PDF = f'{REPO}/fuentes/{FID}/agenda-2026.pdf'
# lo que el OCR no ve y la capa de texto sí, mirado a ojo en la página (25 oct):
# el título de esa fila está impreso; Vision lo salta
OCR_NO_LEE = {'Proyección Reflejos', 'Proyección Basta Mamá'}


def k(s):
    return re.sub(r'[\s.\-–]', '', s.lower())


paginas = []
for i in (1, 2):
    png = f'{REPO}/fuentes/{FID}/agenda-p-{i}.png'
    if not os.path.exists(png):
        subprocess.run(['pdftoppm', '-r', '200', '-png', '-f', str(i), '-l', str(i), PDF,
                        f'{REPO}/fuentes/{FID}/agenda-p'], check=True)
    paginas.append(png)
B = k(subprocess.run(['pdftotext', '-raw', PDF, '-'], capture_output=True, text=True, check=True).stdout)
C = k(' '.join(x for lin in leer(paginas).values() for x in lin))

crudo = json.load(io.open(f'{REPO}/festivals/staging/{FID}-crudo.json', encoding='utf-8'))
build = json.load(io.open(f'{REPO}/festivals/staging/{FID}-build.json', encoding='utf-8'))
afs = json.load(io.open(f'{REPO}/festivals/staging/{FID}-afirmaciones.json', encoding='utf-8'))['afirmaciones']
movida = {(a['ancla']['dia'], a['valor']): a['ancla']['hora'] for a in afs if a['casilla'] == 'time'}

por_ancla = {(f['dia'], f['hora']): f for f in crudo['funciones']}
fallos, franjas_pub = [], set()
for f in build['films']:
    hora = movida.get((f['day'], f['time']), f['time'])
    c = por_ancla.get((f['day'], hora))
    if not c:
        fallos.append(f'en el build sin fila de agenda: {f["day"]} {f["time"]} {f["title"]}')
        continue
    franja, act = c['_src']['fila'].split(' · ', 1)
    franjas_pub.add((f['day'], k(franja), k(act)))
    for nombre, txt in (('B (texto del PDF)', B), ('C (OCR)', C)):
        if k(franja) not in txt:
            fallos.append(f'{nombre}: no está la franja «{franja}» de {f["title"]}')
        if k(act) not in txt and not (nombre.startswith('C') and act in OCR_NO_LEE):
            fallos.append(f'{nombre}: no está «{act}»')
    if f.get('duration') != f'{c["duracion_min"]} min':
        fallos.append(f'duración: {f["title"]} {f.get("duration")} ≠ {c["duracion_min"]} min')

# cobertura inversa: cada franja impresa en B (horas a. m./p. m.) está publicada o declarada fuera
impresas = re.findall(r'(\d{1,2}:\d{2}[ap]m)(\d{1,2}:\d{2}[ap]?m)', B)
declaradas = len(crudo.get('_no_se_publica', []))
if len(impresas) != len(build['films']) + declaradas:
    fallos.append(f'cobertura: {len(impresas)} franjas impresas ≠ {len(build["films"])} publicadas + {declaradas} declaradas fuera')
geo = json.load(io.open(f'{REPO}/festivals/staging/{FID}-venues-geo.json', encoding='utf-8'))
for v, x in build['venues'].items():
    if x.get('lat') is None or geo.get(v.split(' - ')[0], {}).get('_prec') != 'manual':
        fallos.append(f'sede {v!r} sin pin verificado a mano')
if fallos:
    sys.exit('✗ el build no coincide con la agenda:\n  · ' + '\n  · '.join(fallos))
print(f'✓ las {len(build["films"])} funciones del build están en la capa de texto y en el OCR con su franja '
      f'y su nombre · {len(impresas)} franjas impresas = publicadas + {declaradas} declaradas fuera · '
      f'{len(build["venues"])} sede con pin a mano')
