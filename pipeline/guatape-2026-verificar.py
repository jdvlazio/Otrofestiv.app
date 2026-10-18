#!/usr/bin/env python3
"""guatape-2026-verificar.py — lo que se va a publicar, contra las láminas.

El crudo ya se confirma contra el OCR al armarse. Esto mira el OTRO extremo: el
BUILD —lo que llega a la app— contra la transcripción de las láminas, en las
dos direcciones, por (día, hora, sede):

  · todo ítem de la lámina está en el build, en su sede (traducida con la tabla
    del plan), salvo los que una afirmación `existe: false` saca;
  · todo lo que el build publica viene de una lámina;
  · donde una afirmación cambió la sede (el afiche de la masterclass contra la
    agenda), el build tiene la sede AFIRMADA, no la de la lámina;
  · toda sede tiene su pin puesto a mano.
"""
import collections
import importlib.util
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FID = 'guatape-2026'


def main():
    sp = importlib.util.spec_from_file_location('crudo', f'{REPO}/pipeline/{FID}-crudo.py')
    cr = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(cr)
    ojos = json.load(io.open(cr.OJOS, encoding='utf-8'))['items']
    plan = json.load(io.open(f'{REPO}/pipeline/{FID}.plan.json', encoding='utf-8'))['festival']
    build = json.load(io.open(f'{REPO}/festivals/staging/{FID}-build.json', encoding='utf-8'))
    geo = json.load(io.open(f'{REPO}/festivals/staging/{FID}-venues-geo.json', encoding='utf-8'))
    af = json.load(io.open(f'{REPO}/festivals/staging/{FID}-afirmaciones.json', encoding='utf-8'))['afirmaciones']
    ancla = lambda a: (a['ancla']['dia'], a['ancla']['hora'], a['ancla']['sede'])
    # una por afirmación: dos funciones pueden compartir ancla (el cóctel y
    # «Horizonte», jue 22 18:00 en el Muelle Corona) y la afirmación saca una sola
    fuera = collections.Counter(ancla(a) for a in af if a['casilla'] == 'existe' and a['valor'] is False)
    contra = {ancla(a): a['valor'] for a in af if a['casilla'] == 'venue'}

    def sede(lugar):
        return plan['sedes'][re.sub(r'\s+', ' ', lugar).strip(' .')][0]

    quedan = collections.Counter(fuera)

    def _quitar(k):
        if quedan[k] > 0:
            quedan[k] -= 1
            return True
        return False

    lam = collections.Counter()
    for f in ojos:
        k = (f['dia'], f['hora'], sede(f['lugar']))
        if _quitar(k):
            continue
        lam[(f['dia'], f['hora'], contra.get(k, k[2]))] += 1
    pub = collections.Counter((f['day'], f['time'], f['venue']) for f in build['films'])

    fallos = [f'en la lámina y NO en el build: {k} ×{n - pub[k]}' for k, n in lam.items() if pub[k] < n]
    fallos += [f'en el build y en NINGUNA lámina: {k} ×{n - lam[k]}' for k, n in pub.items() if lam[k] < n]
    for v, x in build['venues'].items():
        g = geo.get(v) or geo.get(v.replace(f' - {plan["city"]}', '')) or {}
        if x.get('lat') is None:
            fallos.append(f'sede {v!r} sin pin')
        elif g.get('_prec') != 'manual':
            fallos.append(f'sede {v!r}: pin sin verificar a mano ({g.get("_prec")})')
    if fallos:
        sys.exit('✗ el build no coincide con las láminas:\n  · ' + '\n  · '.join(fallos))
    print(f'✓ los {sum(lam.values())} ítems de las láminas están en el build con su día, hora y sede, '
          f'y el build no publica ninguno más · {sum(fuera.values())} fuera y {len(contra)} sede(s) por afirmación · '
          f'{len(build["venues"])} sedes con pin puesto a mano')


if __name__ == '__main__':
    main()
