#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ficidi-2026-verificar.py — el build contra el Calendario PDF, por OTRO camino.

El crudo lee el PDF con `pdftotext -layout` y un parser por bloques. Este
verificador lo lee con `pdftotext -raw` (otro orden, sin espacios fiables) y
compara FICHAS SIN ESPACIOS: para cada encabezado de día y su hora, la lista
numerada de obras, en los dos sentidos —toda obra del PDF está en esa función
del build y toda obra del build está en el PDF—. Además: cada sede con pin
manual y toda función con su casilla de acceso.
"""
import json
import os
import re
import subprocess
import sys
import unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF = f'{REPO}/fuentes/ficidi-2026/Calendario_IV_FICIDI_2026.pdf'
BUILD = f'{REPO}/festivals/staging/ficidi-2026-build.json'
GEO = f'{REPO}/festivals/staging/ficidi-2026-venues-geo.json'
DIA = {'3': '2026-11-03', '4': '2026-11-04', '5': '2026-11-05', '6': '2026-11-06', '7': '2026-11-07'}


def ficha(t):
    t = unicodedata.normalize('NFC', t).lower()
    return re.sub(r'[\s\W_]+', '', t)


def main():
    raw = subprocess.run(['pdftotext', '-raw', PDF, '-'], capture_output=True, text=True, check=True).stdout
    raw = raw[:raw.index('PARA DISFRUTAR')]
    partes = re.split(r'^(?:MARTES|MIÉRCOLES|JUEVES|VIERNES|SÁBADO) (\d) ?DE NOVIEMBRE.*$', raw, flags=re.M)
    pdf = {}
    for i in range(1, len(partes), 2):
        cuerpo = partes[i + 1]
        h = re.search(r'•\s*(\d{1,2}):(\d\d)\s*([ap])\.\s*m', cuerpo)
        hh = int(h.group(1)) % 12 + (12 if h.group(3) == 'p' else 0)
        clave = (DIA[partes[i]], f'{hh:02d}:{h.group(2)}')
        obras = [ficha(m.group(1)) for m in re.finditer(r'^\d\d (.+?) ·', cuerpo, re.M)]
        pdf[clave] = obras
    b = json.load(open(BUILD, encoding='utf-8'))
    geo = json.load(open(GEO, encoding='utf-8'))
    fallos, n = [], 0
    vistas = set()
    for f in b['films']:
        k = (f['day'], f['time'])
        vistas.add(k)
        if k not in pdf:
            fallos.append(f'{k}: función del build que el PDF no tiene')
            continue
        mia = [ficha(o['title']) for o in f.get('film_list') or []]
        n += len(mia)
        if mia != pdf[k]:
            fallos.append(f'{k}: obras distintas · solo build {sorted(set(mia) - set(pdf[k]))} · '
                          f'solo PDF {sorted(set(pdf[k]) - set(mia))}' if set(mia) != set(pdf[k])
                          else f'{k}: mismo conjunto, otro orden')
        sede = f['venue'].rsplit(' - ', 1)[0]
        if (geo.get(sede) or {}).get('_prec') != 'manual':
            fallos.append(f'{k}: sede «{sede}» sin pin manual')
        if not (f.get('is_free') or f.get('ticket_url') or f.get('requires_registration')):
            fallos.append(f'{k}: sin casilla de acceso')
    for k in set(pdf) - vistas:
        fallos.append(f'{k}: función del PDF que el build no tiene')
    if fallos:
        sys.exit('✗ verificación FICIDI:\n   ' + '\n   '.join(fallos))
    print(f'✓ {len(b["films"])} funciones y {n} obras: el build cuadra con el PDF (lectura -raw), '
          f'en los dos sentidos; toda sede con pin manual; acceso en todas')


if __name__ == '__main__':
    main()
