#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""jardin-2026-contraste.py — las dos superficies del festival, enfrentadas.

EL FESTIVAL SE PUBLICA A SÍ MISMO DOS VECES: una página por obra en
festicinejardin.com (escrita a máquina) y una lámina por obra en Instagram
(pintada). Ninguna de las dos es un tercero: las dos son el festival. Cuando
discrepan, el dato está en disputa y hay que decirlo, no elegir en silencio.

QUÉ COMPARA
  · las 7 obras de «MUESTRA CENTRAL Parte I» contra su ficha web
  · los 22 cortos de CALEIDOSCOPIO contra la suya
  · la obra de la función inaugural contra la suya
  · COBERTURA INVERSA en los dos sentidos: nada anunciado en Instagram puede
    faltar en el catálogo, y lo que el catálogo tiene y Instagram todavía no
    anunció se cuenta y se nombra (es la Parte II que el festival prometió).

CADA DIFERENCIA ENTENDIDA VA EN UNA TABLA CON SU RAZÓN. Una que no esté en la
tabla hace fallar el paso — es la única forma de que este contraste siga
sirviendo cuando el festival publique la Parte II.

Lee   festivals/staging/jardin-2026-catalogo.json
      festivals/staging/jardin-2026-ig.json
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import norm

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
CAT = f'{ST}/jardin-2026-catalogo.json'
IG = f'{ST}/jardin-2026-ig.json'

CAMPOS = ('director', 'anio', 'pais', 'duracion_min', 'categoria')

# LA MISMA OBRA CON OTRA GRAFÍA. Mirado uno por uno — no es una regla, y una
# regla («si se parecen, son la misma») es justo lo que no queremos.
MISMO_TITULO = {
    'Jiru luiai "Algo malo"': 'Jiru iuiai "Algo malo"',
}

# DIFERENCIAS ENTENDIDAS, campo a campo. La clave es (título web, campo).
ENTENDIDAS = {
    ('Lecciones de primavera', 'director'):
        'la lámina acredita «Antonio Mariño Lizarazo» y la web «Antonio '
        'Mariño»: el mismo nombre con y sin el segundo apellido. Manda la web, '
        'que lo escribe a máquina',
    ('Madres de nacimiento', 'director'):
        'la lámina acredita «Gloria Isabel Gómez» y la web «Gloria Isabel Gómez '
        'Ceballos»: mismo nombre, un apellido de más en la web. Manda la web',
    ('Sirena mecánica', 'director'):
        'dos firmas: la lámina las pone en dos renglones y la web con «y». '
        'Misma pareja',
    ('En todo y en nada', 'director'):
        'dos firmas: la lámina las pone en dos renglones y la web con «y». '
        'Misma pareja',
    ('La creciente', 'director'):
        'la lámina de la inaugural acredita «Pablo Andrés Muñoz» y la web '
        '«Pablo Andrés Muñoz Castrillón». Manda la web',
}

# EN DISPUTA DE VERDAD: las dos superficies del festival dicen cosas distintas
# y ninguna es obviamente la buena. No se resuelve acá — se publica una, se
# declara cuál y por qué, y se pregunta al festival.
EN_DISPUTA = {
    ('La creciente', 'duracion_min'):
        ('89', 'la web dice 89 min y la lámina de la inaugural 88. Se publica '
               'la de la web, que es la ficha de la obra; la lámina es una '
               'pieza de anuncio. Preguntado al festival'),
}

# LO QUE LA WEB TIENE Y INSTAGRAM TODAVÍA NO ANUNCIÓ. No es un hallazgo: es la
# Parte II que el propio post promete («Esto es solo la Parte I»).
PARTE_II = 'la web publica su ficha desde el 15 sep; Instagram anunció la Parte I'


def acentos_iguales(a, b):
    """¿Son la misma cadena salvo tildes? El OCR de una lámina con letra fina
    se come acentos —«Somnolitico», «De: Saul»— y eso no es una discrepancia
    entre fuentes, es el límite de la lectura. La web, escrita a máquina, manda."""
    return norm(a) == norm(b)


def main():
    cat = json.load(open(CAT, encoding='utf-8'))
    ig = json.load(open(IG, encoding='utf-8'))
    web = {norm(o['titulo']): o for o in cat['obras']}
    solo_ig = set(cat.get('_solo_en_instagram') or [])

    fallos, entendidas, disputas, ocr, iguales = [], [], [], [], 0
    anunciadas = set()

    def contrasta(o, que):
        nonlocal iguales
        t = MISMO_TITULO.get(o['titulo'], o['titulo'])
        w = web.get(norm(t))
        if not w:
            fallos.append(f'{que}: «{o["titulo"]}» está anunciada en Instagram y '
                          f'no tiene ficha en el catálogo de la web')
            return
        anunciadas.add(norm(t))
        for c in CAMPOS:
            a, b = o.get(c), w.get(c)
            if a in (None, '') or b in (None, ''):
                continue
            if str(a) == str(b):
                iguales += 1
                continue
            k = (w['titulo'], c)
            if isinstance(a, str) and isinstance(b, str) and acentos_iguales(a, b):
                ocr.append(f'«{w["titulo"]}» {c}: «{a}» / «{b}» — solo tildes')
            elif k in EN_DISPUTA:
                gana, por_que = EN_DISPUTA[k]
                if str(b) != gana and str(a) != gana:
                    fallos.append(f'{k}: se declara que gana «{gana}» y ninguna '
                                  f'fuente lo dice ya (IG «{a}», web «{b}»)')
                disputas.append(f'«{w["titulo"]}» {c}: IG «{a}» · web «{b}» → '
                                f'se publica {gana}. {por_que}')
            elif k in ENTENDIDAS:
                entendidas.append(f'«{w["titulo"]}» {c}: IG «{a}» · web «{b}» — '
                                  f'{ENTENDIDAS[k]}')
            else:
                fallos.append(f'{que}: «{w["titulo"]}» campo {c} — Instagram dice '
                              f'«{a}» y la web «{b}». Sin entrada en la tabla.')

    for o in ig['muestra_central']:
        contrasta(o, 'muestra')
    for o in ig['caleidoscopio']:
        contrasta(o, 'caleidoscopio')
    for f in ig['funciones']:
        contrasta({**f, 'duracion_min': f.get('duracion_obra')}, 'función')

    # cobertura inversa ← : lo que el catálogo tiene y Instagram no ha anunciado
    pendientes = {}
    for k, w in web.items():
        if k in anunciadas or w['titulo'] in solo_ig:
            continue
        pendientes.setdefault(w['seccion'], []).append(w['titulo'])

    # y →: nada del catálogo puede haber salido SOLO de Instagram sin declararlo
    for t in solo_ig:
        if norm(t) not in web:
            fallos.append(f'«{t}» está declarada como solo-Instagram y no está '
                          f'en el catálogo')

    print(f'jardin-2026 · contraste web ↔ Instagram\n'
          f'  {len(ig["muestra_central"])} obras de la Muestra Central · '
          f'{len(ig["caleidoscopio"])} cortos · {len(ig["funciones"])} función\n'
          f'  {iguales} campos idénticos en las dos superficies')
    if ocr:
        print(f'\n{len(ocr)} diferencia(s) de tilde (la web manda, escribe a máquina):')
        for x in ocr:
            print('   ·', x)
    if entendidas:
        print(f'\n{len(entendidas)} diferencia(s) entendida(s):')
        for x in entendidas:
            print('   ·', x)
    if disputas:
        print(f'\n{len(disputas)} DATO(S) EN DISPUTA entre dos superficies del '
              f'propio festival:')
        for x in disputas:
            print('   ⚠', x)
    for sec, ts in sorted(pendientes.items()):
        print(f'\n{len(ts)} obra(s) de «{sec}» con ficha en la web y sin anunciar '
              f'en Instagram — {PARTE_II}:')
        for t in sorted(ts):
            print('   ·', t)
    if fallos:
        print(f'\n✗ {len(fallos)} problema(s):')
        for f_ in fallos:
            print('   ✗', f_)
        sys.exit(1)
    print('\n✓ las dos superficies del festival dicen lo mismo, salvo lo declarado')


if __name__ == '__main__':
    main()
