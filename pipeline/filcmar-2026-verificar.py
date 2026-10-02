#!/usr/bin/env python3
"""filcmar-2026-verificar.py — lo que se va a publicar, contra las láminas.

El crudo ya se confirma contra la OCR al armarse. Esto mira el OTRO extremo: el
BUILD que sale del ensamblador contra la lectura a ojo de las láminas
(p/Dd-Wc29Dhkd), en las dos direcciones:

  · toda actividad y toda obra de la lámina está en el build con su día, su
    hora, su sede y su sala — salvo lo que Juan dejó fuera;
  · todo lo que el build publica viene de una lámina;
  · toda obra de un programa está dentro de su programa;
  · toda sede tiene su pin verificado a mano.

Las REGLAS (qué se excluye, qué título se publica, qué sede y sala) se importan
del crudo (verificador-mismo-camino).
"""
import importlib.util
import io
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FID = 'filcmar-2026'
CIUDAD = 'Marinilla'

_spec = importlib.util.spec_from_file_location('crudo', f'{REPO}/pipeline/filcmar-2026-crudo.py')
crudo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(crudo)
plano = crudo.plano


def main():
    ojos = json.load(io.open(crudo.OJOS, encoding='utf-8'))['actividades']
    build = json.load(io.open(f'{REPO}/festivals/staging/{FID}-build.json', encoding='utf-8'))
    geo = json.load(io.open(f'{REPO}/festivals/staging/{FID}-venues-geo.json', encoding='utf-8'))

    lam, programas = {}, {}
    for a in ojos:
        t = a.get('titulo')
        if t in crudo.EXCLUIDOS:
            continue
        sede, sala = crudo.SEDES[a['sede']]
        lugar = (f'{sede} - {CIUDAD}', sala or '')
        if a.get('cortos') or (t or '').startswith('Cortoconcierto'):
            lam[(a['dia'], a['hora'], plano(t))] = lugar
            programas[(a['dia'], a['hora'], plano(t))] = sorted(
                plano(x) for x in (a.get('cortos') or [o['titulo'] for o in a['obras']]))
            continue
        if t in crudo.ACTIVIDAD:
            lam[(a['dia'], a['hora'], plano(crudo.TITULO.get(t, t)))] = lugar
        for o in a.get('obras', []):
            lam[(a['dia'], a['hora'], plano(o['titulo']))] = lugar
    pub = {(f['day'], f['time'], plano(f['title'])): f for f in build['films']}

    fallos = []
    for k, (sede, sala) in lam.items():
        f = pub.get(k)
        if not f:
            fallos.append(f'en la lámina y NO en el build: {k[0]} {k[1]} «{k[2]}»')
            continue
        if f['venue'] != sede:
            fallos.append(f'{k[0]} {k[1]} «{k[2]}»: la lámina dice {sede!r}, el build {f["venue"]!r}')
        if (f.get('sala') or '') != sala:
            fallos.append(f'{k[0]} {k[1]} «{k[2]}»: sala {sala!r} en la lámina, {f.get("sala")!r} en el build')
    for k in pub:
        if k not in lam:
            fallos.append(f'en el build y en NINGUNA lámina: {k[0]} {k[1]} «{k[2]}»')
    for k, titulos in programas.items():
        f = pub.get(k)
        if f and sorted(plano(o['title']) for o in f.get('film_list', [])) != titulos:
            fallos.append(f'{k[0]} {k[1]} «{k[2]}»: las obras del programa no son las de la lámina')
    for t in crudo.EXCLUIDOS:
        if any(plano(f['title']) == plano(t) for f in build['films']):
            fallos.append(f'«{t}» está en el build y Juan lo dejó fuera')
    for v, x in build['venues'].items():
        g = geo.get(v.replace(f' - {CIUDAD}', ''), {})
        if x.get('lat') is None:
            fallos.append(f'sede {v!r} sin pin')
        elif g.get('_prec') != 'manual':
            fallos.append(f'sede {v!r}: pin sin verificar a mano ({g.get("_prec")})')

    if fallos:
        sys.exit('✗ el build no coincide con las láminas:\n  · ' + '\n  · '.join(fallos))
    print(f'✓ las {len(lam)} funciones de las láminas están en el build con su día, hora, sede y '
          f'sala, y el build no publica ninguna más · {len(programas)} programas con sus obras · '
          f'{len(crudo.EXCLUIDOS)} fuera, como decidió Juan · {len(build["venues"])} sedes con pin a mano')


if __name__ == '__main__':
    main()
