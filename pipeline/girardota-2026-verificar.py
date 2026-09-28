#!/usr/bin/env python3
"""girardota-2026-verificar.py — lo que se va a publicar, contra las láminas.

El crudo ya se confirma contra el OCR al armarse. Esto mira el OTRO extremo: el
BUILD que sale del ensamblador —lo que llega a la app— contra la transcripción de
las láminas, en las dos direcciones:

  · toda actividad de la lámina está en el build, con su día, su hora y su lugar;
  · todo lo que el build publica viene de una lámina (nada inventado en el camino);
  · toda sede tiene su pin verificado a mano, o un pendiente escrito que dice por
    qué no lo tiene (Palmas del Llano: es un barrio, no una sede).

Es el paso que pide [plan-verificador]: el de FICMA encontró dos horas mal en
diez segundos.
"""
import io
import json
import os
import sys
import unicodedata
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FID = 'girardota-2026'
CIUDAD = 'Girardota'


def plano(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def main():
    ojos = json.load(io.open(f'{REPO}/fuentes/{FID}-ojos.json', encoding='utf-8'))['funciones']
    build = json.load(io.open(f'{REPO}/festivals/staging/{FID}-build.json', encoding='utf-8'))
    geo = json.load(io.open(f'{REPO}/festivals/staging/{FID}-venues-geo.json', encoding='utf-8'))

    lam = {(f['dia'], f['hora'], plano(f['titulo'])): f['sede'] for f in ojos}
    pub = {(f['day'], f['time'], plano(f['title'])): f['venue'] for f in build['films']}
    fallos = []
    for k, sede in lam.items():
        if k not in pub:
            fallos.append(f'en la lámina y NO en el build: {k[0]} {k[1]} «{k[2]}»')
        elif pub[k] != f'{sede} - {CIUDAD}':
            fallos.append(f'{k[0]} {k[1]} «{k[2]}»: la lámina dice {sede!r}, el build {pub[k]!r}')
    for k in pub:
        if k not in lam:
            fallos.append(f'en el build y en NINGUNA lámina: {k[0]} {k[1]} «{k[2]}»')

    for v, x in build['venues'].items():
        g = geo.get(v.replace(f' - {CIUDAD}', ''), {})
        if x.get('lat') is None and not g.get('_todo'):
            fallos.append(f'sede {v!r} sin pin y sin pendiente escrito')
        elif x.get('lat') is not None and g.get('_prec') != 'manual':
            fallos.append(f'sede {v!r}: pin sin verificar a mano ({g.get("_prec")}) — '
                          'las láminas no dan direcciones, así que todo pin se cruza contra Google')

    if fallos:
        sys.exit('✗ el build no coincide con las láminas:\n  · ' + '\n  · '.join(fallos))
    sin_pin = [v for v, x in build['venues'].items() if x.get('lat') is None]
    print(f'✓ las {len(lam)} actividades de las láminas están en el build con su día, hora y '
          f'lugar, y el build no publica ninguna más · {len(build["venues"]) - len(sin_pin)} sedes '
          f'con pin verificado a mano' + (f' · sin pin, con su porqué: {", ".join(sin_pin)}' if sin_pin else ''))


if __name__ == '__main__':
    main()
