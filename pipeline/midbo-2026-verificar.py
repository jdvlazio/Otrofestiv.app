#!/usr/bin/env python3
"""midbo-2026-verificar.py — lo que se va a publicar, contra las fichas de midbo.co.

Por el MISMO camino del crudo (se importan su lector y sus tablas): toda función
de cada ficha que cae en la ventana oficial y no se declaró fuera está en el
build —en su día y su hora, sola o dentro de su programa—; todo lo que el build
publica a una hora tiene una ficha a esa hora (o una sesión del seminario); y
toda sede tiene su pin verificado a mano.
"""
import html
import importlib.util
import io
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FID = 'midbo-2026'
_spec = importlib.util.spec_from_file_location('crudo', f'{REPO}/pipeline/midbo-2026-crudo.py')
crudo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(crudo)
plano = crudo.plano


def main():
    obras = json.load(io.open(f'{crudo.DIR}/pelicula-1.json', encoding='utf-8')) + \
        json.load(io.open(f'{crudo.DIR}/pelicula-2.json', encoding='utf-8'))
    build = json.load(io.open(f'{REPO}/festivals/staging/{FID}-build.json', encoding='utf-8'))
    geo = json.load(io.open(f'{REPO}/festivals/staging/{FID}-venues-geo.json', encoding='utf-8'))
    pub = {}
    for f in build['films']:
        nombres = {plano(f['title'])} | {plano(o['title']) for o in f.get('film_list') or []}
        pub.setdefault(f['day'], []).append((f['time'], nombres))
    fallos, n, horas = [], 0, set()
    for o in obras:
        t = html.unescape(o['title']['rendered']).strip().replace('’', "'").replace('‘', "'")
        p = f'{crudo.DIR}/fichas/{o["slug"]}.html'
        for f in crudo.ficha(crudo.lineas(p), crudo.bloques(p))['funciones']:
            if not (crudo.DESDE <= f['dia'] <= crudo.HASTA) or f['lugar'] in crudo.SEDE_FUERA:
                continue
            n += 1
            horas.add((f['dia'], f['hora']))
            # dentro de un programa la obra puede tener SU hora (arranca al
            # terminar la anterior): basta con que esté ese día en un bloque que
            # empieza a su hora o antes
            if not any(plano(t) in nom and h <= f['hora'] for h, nom in pub.get(f['dia'], [])):
                fallos.append(f'en la ficha y NO en el build: {f["dia"]} {f["hora"]} «{t[:60]}»')
    sem, _ = crudo.seminario()
    horas |= {(s['dia'], s['hora']) for s in sem}
    for d, lst in pub.items():
        for h, nom in lst:
            if (d, h) not in horas:
                fallos.append(f'en el build a una hora que ninguna ficha tiene: {d} {h} {sorted(nom)[:1]}')
    for v, x in build['venues'].items():
        g = geo.get(x.get('short') or v.split(' - ')[0], {})
        if x.get('lat') is None:
            fallos.append(f'sede {v!r} sin pin')
        elif g.get('_prec') != 'manual':
            fallos.append(f'sede {v!r}: pin sin verificar a mano ({g.get("_prec")})')
    if fallos:
        sys.exit('✗ el build no coincide con las fichas:\n  · ' + '\n  · '.join(fallos))
    print(f'✓ las {n} funciones de las fichas están en el build y el build no publica ninguna hora '
          f'sin ficha o sesión · {len(build["venues"])} sedes con pin a mano')


if __name__ == '__main__':
    main()
