#!/usr/bin/env python3
"""migrar-descripcion.py — una sola vez: synopsis → description en programas y actividades.

Decisión de Juan (7 oct 2026): «sinopsis es solo para películas, descripción
para programas o actividades». La regla vive en lib.separar_descripcion, que ya
aplican el ensamblador y el publicador; esto la aplica a lo YA publicado (y a
los builds de staging, para que build y publicado hablen igual) sin re-correr
30 pipelines cuyas fuentes cambiaron.

No es un arreglo de datos: es un cambio de NOMBRE de campo. Por eso se verifica
que no cambie ni un carácter de texto —el multiconjunto de todos los textos de
sinopsis y descripción es idéntico antes y después— y que ninguna OBRA (función
simple o ítem de un programa) pierda su sinopsis. Si algo no cuadra, no escribe.

    python3 scripts/migrar-descripcion.py            # informa y escribe
    python3 scripts/migrar-descripcion.py --probar   # solo informa
"""
import collections
import glob
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, f'{REPO}/pipeline')
import lib  # noqa: E402

CAMPOS = list(lib.DESCRIPCION_DE) + list(lib.DESCRIPCION_DE.values())


def textos(films):
    c = collections.Counter()
    for f in films:
        for x in [f] + list(f.get('film_list') or []):
            for k in CAMPOS:
                if k.endswith('_lang'):
                    continue
                if x.get(k):
                    c[x[k]] += 1
    return c


def sinopsis_de_obras(films):
    return sum(1 for f in films for x in ([f] if not lib.lleva_descripcion(f) else []) + list(f.get('film_list') or [])
               if x.get('synopsis'))


def main():
    probar = '--probar' in sys.argv
    total, fallos = collections.Counter(), []
    rutas = sorted(glob.glob(f'{REPO}/festivals/*.json')) + sorted(glob.glob(f'{REPO}/festivals/staging/*-build.json'))
    escribir = []
    for p in rutas:
        try:
            d = json.load(open(p, encoding='utf-8'))
        except Exception:
            continue
        films = d.get('films')
        if not isinstance(films, list):
            continue
        antes_t, antes_o = textos(films), sinopsis_de_obras(films)
        n = sum(lib.separar_descripcion(f) for f in films)
        if not n:
            continue
        if textos(films) != antes_t:
            fallos.append(f'{os.path.relpath(p, REPO)}: cambió el texto')
        if sinopsis_de_obras(films) != antes_o:
            fallos.append(f'{os.path.relpath(p, REPO)}: una obra perdió su sinopsis')
        total[os.path.relpath(p, REPO)] = n
        escribir.append((p, d))
    for k, v in total.items():
        print(f'  {v:4} campos movidos · {k}')
    if fallos:
        sys.exit('✗ NO se escribe nada:\n  · ' + '\n  · '.join(fallos))
    print(f'✓ {sum(total.values())} campos en {len(total)} archivos; texto idéntico, ninguna obra sin su sinopsis')
    if probar:
        return
    for p, d in escribir:
        if '/staging/' in p:
            json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        else:
            # el mismo formato que escribe pipeline/publicar.py
            json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))


if __name__ == '__main__':
    main()
