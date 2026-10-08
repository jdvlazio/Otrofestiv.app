#!/usr/bin/env python3
"""bhff-2026-catalogo.py — la Selección del 8° Bogotá Horror Film Festival, desde sus láminas.

LA FUENTE es bogotahorrorfilmfest.com/seleccion-2026/: la página arma la
selección con JavaScript (`festivalData` en el HTML) y cada obra es una LÁMINA —
el afiche con TÍTULO / DIRECCIÓN / PAÍS pintados debajo—, en cuatro categorías:
Cortometraje Animado, Internacional, Nacional I y Nacional II (las demás «están
vacías por ahora», dice su propio comentario).

LECTURA a ojo de las 39 láminas (fuentes/bhff-2026/ojos-seleccion.json),
confirmada por la OCR del sistema: toda palabra de 4+ letras del título y de la
dirección tiene que estar en SU lámina, y cada lámina del sitio tiene que estar
transcrita (cobertura en los dos sentidos).

Las nacionales no imprimen país: la categoría es «Cortometraje Nacional» de un
festival colombiano → Colombia, declarado como deducción de la categoría.
"""
import io
import json
import os
import re
import sys
import unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402
from ocr import leer  # noqa: E402

DIR = f'{REPO}/fuentes/bhff-2026'
OJOS = f'{DIR}/ojos-seleccion.json'
SITIO = f'{DIR}/seleccion-afiches.json'
DESTINO = f'{REPO}/festivals/staging/bhff-2026-catalogo.json'
URL = 'https://bogotahorrorfilmfest.com/seleccion-2026/'
CATEGORIA = {'corto-animado': 'Cortometraje Animado', 'corto-internacional': 'Cortometraje Internacional',
             'corto-nacional-1': 'Cortometraje Nacional', 'corto-nacional-2': 'Cortometraje Nacional'}


def plano(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def main():
    ojos = json.load(io.open(OJOS, encoding='utf-8'))['laminas']
    sitio = json.load(io.open(SITIO, encoding='utf-8'))
    del_sitio = {os.path.basename(u): k for k, v in sitio.items() for u in v['imgs']}
    rutas = [f'{DIR}/laminas/{f}' for f, *_ in ojos]
    ocr = leer(rutas)
    fallos = []
    vistas = {f for f, *_ in ojos}
    for f in del_sitio.keys() - vistas:
        fallos.append(f'lámina del sitio sin transcribir: {f}')
    for f in vistas - del_sitio.keys():
        fallos.append(f'transcrita y no está en el sitio: {f}')
    obras = []
    for f, cat, titulo, director, pais in ojos:
        if del_sitio.get(f) != cat:
            fallos.append(f'{f}: transcrita como {cat}, en el sitio es {del_sitio.get(f)}')
        w = set(plano(' '.join(ocr.get(f'{DIR}/laminas/{f}', []))).split())
        for x in plano(titulo + ' ' + director).split():
            if len(x) >= 4 and x not in w:
                fallos.append(f'{f}: la OCR no encuentra «{x}» de «{titulo}» / «{director}»')
        o = {'titulo': titulo, 'director': director, 'categoria': CATEGORIA[cat],
             '_src': {'url': URL, 'lamina': f, 'date': '2026-10-07'}}
        if pais:
            o['pais'] = pais
        elif cat.startswith('corto-nacional'):
            o['pais'] = 'Colombia'
            o['_pais_fuente'] = 'categoría «Cortometraje Nacional» de un festival colombiano (la lámina no imprime país)'
        obras.append(o)
    if fallos:
        sys.exit('✗ la transcripción y las láminas no coinciden:\n  · ' + '\n  · '.join(fallos))
    io.open(DESTINO, 'w', encoding='utf-8').write(json.dumps({
        '_provenance': provenance('bogotahorrorfilmfest.com, Selección 2026 (láminas de festivalData)', url=URL,
                                  metodo='lectura a ojo de las 39 láminas, confirmada por la OCR del sistema'),
        'obras': obras}, ensure_ascii=False, indent=1))
    print(f'✓ {len(obras)} obras de la selección → {os.path.relpath(DESTINO, REPO)}')


if __name__ == '__main__':
    main()
