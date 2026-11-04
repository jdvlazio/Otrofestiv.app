#!/usr/bin/env python3
"""mambe-2026-verificar.py — lo que se va a publicar, contra las láminas.

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
FID = 'mambe-2026'


def main():
    sp = importlib.util.spec_from_file_location('crudo', f'{REPO}/pipeline/{FID}-crudo.py')
    cr = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(cr)
    ojos = json.load(io.open(cr.OJOS, encoding='utf-8'))['items']
    plan = json.load(io.open(f'{REPO}/pipeline/{FID}.plan.json', encoding='utf-8'))['festival']
    build = json.load(io.open(f'{REPO}/festivals/staging/{FID}-build.json', encoding='utf-8'))
    geo = json.load(io.open(f'{REPO}/festivals/staging/{FID}-venues-geo.json', encoding='utf-8'))
    ap = f'{REPO}/festivals/staging/{FID}-afirmaciones.json'
    af = json.load(io.open(ap, encoding='utf-8'))['afirmaciones'] if os.path.exists(ap) else []

    def sede(lugar):
        return plan['sedes'][lugar][0]

    # LAS LÁMINAS, y encima las afirmaciones como operaciones sobre UNA función
    # cada una (dos funciones pueden compartir ancla: el cóctel y «Horizonte»):
    # existe:false saca una, existe:{…} agrega una, venue/time mueven una.
    # lo que el crudo deja fuera a propósito (NO_SE_PUBLICA, con su porqué)
    lam = collections.Counter((f['dia'], f['hora'], sede(f['lugar'])) for f in ojos
                              if (f['dia'], f['hora'], f['encabezado']) not in cr.NO_SE_PUBLICA)
    n_ops = collections.Counter()
    for a in af:
        k = (a['ancla']['dia'], a['ancla']['hora'], a['ancla']['sede'])
        if a['casilla'] == 'existe' and a['valor'] is False:
            lam[k] -= 1
        elif a['casilla'] == 'existe':
            v = a['valor']
            lam[(v['day'], v['time'], v['venue'])] += 1
        elif a['casilla'] in ('venue', 'time'):
            lam[k] -= 1
            lam[(k[0], a['valor'], k[2]) if a['casilla'] == 'time' else (k[0], k[1], a['valor'])] += 1
        else:
            continue
        n_ops[a['casilla'] if a['casilla'] != 'existe' else ('sale' if a['valor'] is False else 'entra')] += 1
    if any(n < 0 for n in lam.values()):
        sys.exit(f'✗ una afirmación apunta a un ancla que las láminas no tienen: {[k for k, n in lam.items() if n < 0]}')
    lam = +lam
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
    print(f'✓ los {sum(lam.values())} ítems de las láminas (con sus afirmaciones) están en el build con su día, '
          f'hora y sede, y el build no publica ninguno más · afirmaciones: {dict(n_ops)} · '
          f'{len(build["venues"])} sedes con pin puesto a mano')


if __name__ == '__main__':
    main()
