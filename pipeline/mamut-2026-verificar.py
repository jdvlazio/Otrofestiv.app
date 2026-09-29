#!/usr/bin/env python3
"""mamut-2026-verificar.py — lo que se va a publicar, contra las láminas.

El crudo ya se confirma contra la OCR al armarse. Esto mira el OTRO extremo: el
BUILD que sale del ensamblador —lo que llega a la app— contra la lectura a ojo
de las láminas de la versión corregida (p/Dd2ckXgiYW9), en las dos direcciones:

  · toda actividad de la lámina está en el build con su día, su hora, su sede y
    su sala — salvo las que Juan dejó fuera (convocatoria cerrada);
  · todo lo que el build publica viene de una lámina;
  · toda sede tiene su pin verificado a mano, o un pendiente escrito que dice
    por qué no lo tiene.

Las REGLAS de qué se excluye y cómo se unifica un título no se reescriben acá:
se importan del crudo (verificador-mismo-camino: una segunda lectura que
reimplementa el pipeline delata diferencias que no están en la fuente).
"""
import importlib.util
import io
import json
import os
import re
import sys
import unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FID = 'mamut-2026'
CIUDAD = 'Medellín'

_spec = importlib.util.spec_from_file_location('crudo', f'{REPO}/pipeline/mamut-2026-crudo.py')
crudo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(crudo)


def plano(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def main():
    ojos = json.load(io.open(f'{REPO}/fuentes/{FID}-ojos-programa.json', encoding='utf-8'))['actividades']
    build = json.load(io.open(f'{REPO}/festivals/staging/{FID}-build.json', encoding='utf-8'))
    geo = json.load(io.open(f'{REPO}/festivals/staging/{FID}-venues-geo.json', encoding='utf-8'))

    lam = {}
    for a in ojos:
        t = crudo.TITULO_UNIFICADO.get(a['titulo'], a['titulo'])
        if t in crudo.EXCLUIDOS:
            continue
        lam[(a['dia'], a['hora'], plano(t))] = (crudo.SEDES[a['sede']],
                                                a.get('sala') or crudo.SALA_DE_OTRA_FUENTE.get(t, ''))
    pub = {(f['day'], f['time'], plano(f['title'])): (f['venue'], f.get('sala') or '')
           for f in build['films']}
    fallos = []
    for k, (sede, sala) in lam.items():
        if k not in pub:
            fallos.append(f'en la lámina y NO en el build: {k[0]} {k[1]} «{k[2]}»')
            continue
        if pub[k][0] != f'{sede} - {CIUDAD}':
            fallos.append(f'{k[0]} {k[1]} «{k[2]}»: la lámina dice {sede!r}, el build {pub[k][0]!r}')
        if pub[k][1] != sala:
            fallos.append(f'{k[0]} {k[1]} «{k[2]}»: sala {sala!r} en la lámina, {pub[k][1]!r} en el build')
    for k in pub:
        if k not in lam:
            fallos.append(f'en el build y en NINGUNA lámina: {k[0]} {k[1]} «{k[2]}»')
    for t in crudo.EXCLUIDOS:
        if any(plano(f['title']) == plano(t) for f in build['films']):
            fallos.append(f'«{t}» está en el build y Juan lo dejó fuera')

    for v, x in build['venues'].items():
        g = geo.get(v.replace(f' - {CIUDAD}', ''), {})
        if x.get('lat') is None and not g.get('_todo'):
            fallos.append(f'sede {v!r} sin pin y sin pendiente escrito')
        elif x.get('lat') is not None and g.get('_prec') != 'manual':
            fallos.append(f'sede {v!r}: pin sin verificar a mano ({g.get("_prec")})')

    if fallos:
        sys.exit('✗ el build no coincide con las láminas:\n  · ' + '\n  · '.join(fallos))
    sin_pin = [v for v, x in build['venues'].items() if x.get('lat') is None]
    print(f'✓ las {len(lam)} actividades de las láminas están en el build con su día, hora, '
          f'sede y sala, y el build no publica ninguna más · {len(crudo.EXCLUIDOS)} talleres '
          f'fuera, como decidió Juan · {len(build["venues"]) - len(sin_pin)} sedes con pin '
          f'verificado a mano' + (f' · sin pin, con su porqué: {", ".join(sin_pin)}' if sin_pin else ''))


if __name__ == '__main__':
    main()
