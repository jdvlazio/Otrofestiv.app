#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""conexcine-2026-verificar.py — probar que lo montado es cierto.

No relee el PDF: eso lo hacen `-programa-pdf`, `-contraste` (MuPDF + OCR) e
`-ig-contraste`. Este paso mira el CRUDO ya armado y comprueba las cosas que
solo se ven cuando las piezas están juntas —que ninguna sala se use dos veces
a la vez, que ninguna función se quede sin sede, que todo lo que el catálogo
lista acabe en alguna función—. El verificador de FICMA encontró dos horas mal
en diez segundos; el de Villa del Cine, un bloque que no cabía en su casilla.

Lo que está entendido va en una tabla DECLARADA, con su razón. Un hallazgo sin
entrada hace fallar el paso: es la única forma de que siga sirviendo mañana.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import norm

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
CRUDO = f'{ST}/conexcine-2026-crudo.json'
CAT = f'{ST}/conexcine-2026-catalogo.json'
PAR = f'{ST}/conexcine-2026-parrilla.json'
PLAN = f'{REPO}/pipeline/conexcine-2026.plan.json'

DIAS = {'2026-09-23', '2026-09-24', '2026-09-25', '2026-09-26'}

# SOLAPES ENTENDIDOS. El PDF los dibuja a propósito.
SOLAPE_OK = {
    ('2026-09-26', 'Exposición Proyectarte', 'Ceremonia de Clausura'):
        'la exposición está «disponible durante todo el festival»: se recorre, '
        'no se asiste, y el propio PDF la cruza con la clausura',
}

# OBRAS DEL CATÁLOGO QUE NO VAN EN NINGUNA FUNCIÓN, y por qué.
SIN_FUNCION_OK = {
    'Competencia Virtual': 'ocho cortos en el YouTube de FEDECAJAS para el '
                           'Premio del Público, sin día, hora ni sede',
}


def mins(h):
    return int(h[:2]) * 60 + int(h[3:])


def main():
    c = json.load(open(CRUDO, encoding='utf-8'))['funciones']
    cat = json.load(open(CAT, encoding='utf-8'))
    par = json.load(open(PAR, encoding='utf-8'))
    plan = json.load(open(PLAN, encoding='utf-8'))['festival']
    fallos, avisos = [], []

    # 1 · toda función con día conocido, hora y SEDE
    for f in c:
        if f['dia'] not in DIAS:
            fallos.append(f'«{f["titulo"][:40]}» cae en {f["dia"]}, fuera del festival')
        if not f.get('sede'):
            fallos.append(f'«{f["titulo"][:40]}» sin sede')
        elif f['sede'] not in plan['sedes']:
            fallos.append(f'«{f["titulo"][:40]}»: sede «{f["sede"]}» sin tabla en el plan')
        if not f.get('hora'):
            fallos.append(f'«{f["titulo"][:40]}» sin hora')

    # 2 · los cuatro días tienen programación
    vacios = DIAS - {f['dia'] for f in c}
    if vacios:
        fallos.append(f'días del festival sin ninguna función: {sorted(vacios)}')

    # 3 · ningún bloque del PDF se perdió por el camino
    if len(c) != len(par['bloques']):
        fallos.append(f'la parrilla trae {len(par["bloques"])} bloques y el crudo '
                      f'publica {len(c)}')

    # 4 · ninguna sala usada dos veces a la vez
    for i, f in enumerate(c):
        fin = mins(f['hora']) + f['duracion_min']
        for g in c[i + 1:]:
            if g['dia'] != f['dia'] or g['sede'] != f['sede']:
                continue
            if mins(g['hora']) < fin:
                k = (f['dia'], f['titulo'], g['titulo'])
                sol = fin - mins(g['hora'])
                if k in SOLAPE_OK:
                    avisos.append(f'{f["dia"][-2:]} «{f["titulo"][:26]}» solapa '
                                  f'{sol} min con «{g["titulo"][:26]}» — {SOLAPE_OK[k]}')
                else:
                    fallos.append(f'{f["dia"][-2:]} «{f["titulo"][:30]}» ({f["hora"]}'
                                  f'+{f["duracion_min"]}m) solapa {sol} min con '
                                  f'«{g["titulo"][:30]}» ({g["hora"]}) en {f["sede"][:24]}')

    # 5 · TODO lo que el catálogo lista acaba en una función
    en_funcion = {norm(o['titulo']) for f in c for o in (f.get('obras') or [])}
    en_funcion |= {norm(f['titulo']) for f in c}
    huerfanas = {}
    for o in cat['obras']:
        if norm(o['titulo']) in en_funcion:
            continue
        huerfanas.setdefault(o['seccion'], []).append(o['titulo'])
    for sec, ts in huerfanas.items():
        if sec in SIN_FUNCION_OK:
            avisos.append(f'{len(ts)} obra(s) de «{sec}» sin función — {SIN_FUNCION_OK[sec]}')
        else:
            fallos.append(f'{len(ts)} obra(s) de «{sec}» que el catálogo lista y '
                          f'ninguna función proyecta: {ts[:6]}')

    # 6 · un largo nunca se publica más corto de lo que dura
    for f in c:
        d = f.get('duracion_obra')
        if d and d > f['duracion_min']:
            fallos.append(f'«{f["titulo"][:34]}» dura {d} min y su función mide '
                          f'{f["duracion_min"]}: se publicaría más corta de lo que es')

    # 7 · toda actividad con su vocabulario, y ninguna con ficha de obra
    for f in c:
        if f.get('tipo') == 'evento':
            if not f.get('event_kind'):
                fallos.append(f'actividad «{f["titulo"][:34]}» sin event_kind')
            if not f.get('is_cortos') and any(f.get(k) for k in ('pais', 'director')):
                fallos.append(f'actividad «{f["titulo"][:34]}» con ficha de obra')

    print(f'conexcine-2026: {len(c)} funciones · {len(DIAS)} días · '
          f'{len(plan["sedes"])} sedes')
    for a in avisos:
        print('   · para mirar:', a)
    if fallos:
        print(f'\n✗ {len(fallos)} problema(s):')
        for f_ in fallos:
            print('   ✗', f_)
        sys.exit(1)
    print('\n✓ cada función con día, hora y sede; sin solapes no declarados; y todo '
          'lo que el catálogo lista tiene dónde verse')


if __name__ == '__main__':
    main()
