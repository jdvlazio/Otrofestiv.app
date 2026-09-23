#!/usr/bin/env python3
"""itagui-2026-verificar.py — el crudo armado, contra la fuente independiente.

Las láminas de Instagram y el PDF oficial de institutoitagui.gov.co son la MISMA
programación publicada por dos caminos. El PDF trae TEXTO, así que no comparte
ni motor de OCR ni parser con la parrilla: es la única lectura de verdad
independiente que tenemos, y por eso es la que manda acá.

Falla si:
  · una función no tiene día, hora o sede;
  · una sede no está en la tabla del plan;
  · un título parseado no aparece en el PDF.
"""
import json
import os
import re
import subprocess
import sys
import unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CRUDO = f'{REPO}/festivals/staging/itagui-2026-crudo.json'
PDF = f'{REPO}/fuentes/itagui-2026/programacion.pdf'
PLAN = f'{REPO}/pipeline/itagui-2026.plan.json'


def clave(x):
    x = ''.join(c for c in unicodedata.normalize('NFD', str(x or ''))
                if unicodedata.category(c) != 'Mn').lower()
    return re.sub(r'[^a-z0-9]+', ' ', x).strip()


def main():
    d = json.load(open(CRUDO, encoding='utf-8'))
    plan = json.load(open(PLAN, encoding='utf-8'))
    sedes = set(plan['festival']['sedes'])
    fallos = []

    for i, f in enumerate(d['funciones']):
        for campo in ('dia', 'hora', 'sede', 'titulo'):
            if not f.get(campo):
                fallos.append(f'funciones[{i}] sin {campo}')
        if f.get('sede') and f['sede'] not in sedes:
            fallos.append(f'sede fuera de la tabla del plan: {f["sede"]!r}')

    if not os.path.exists(PDF):
        fallos.append(f'falta el PDF oficial en {PDF} — sin él no hay lectura '
                      f'independiente que cruzar')
    else:
        txt = clave(subprocess.run(['pdftotext', '-layout', PDF, '-'],
                                   capture_output=True, text=True).stdout)
        # los títulos que PARTIMOS a mano no se buscan enteros: en el PDF están
        # con su cola, que es justo lo que les quitamos.
        for f in d['funciones']:
            t = clave(f['titulo'])[:26]
            if t and t not in txt:
                fallos.append(f'«{f["titulo"][:46]}» no aparece en el PDF oficial')

    if fallos:
        print('\n'.join(f'   ✗ {x}' for x in fallos), file=sys.stderr)
        sys.exit(f'\n✗ {len(fallos)} fallo(s) de verificación')
    print(f'✓ {len(d["funciones"])} funciones · día, hora y sede en todas · las '
          f'{len(sedes)} sedes en la tabla · los {len(d["funciones"])} títulos '
          f'en el PDF oficial')


if __name__ == '__main__':
    main()
