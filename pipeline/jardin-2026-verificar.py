#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""jardin-2026-verificar.py — probar que lo montado es cierto, y que sabemos
lo que NO tenemos.

Este festival se monta al revés que los demás: primero el catálogo entero (37
obras con ficha completa) y la parrilla después — a cuatro días del inicio no
existe. Así que el verificador tiene DOS trabajos y el segundo pesa más que el
primero:

  1. Que lo poco que se publica esté bien: día dentro del festival, hora, sede
     de la tabla del plan, sin salas encimadas.
  2. QUE NO SE PIERDA NADA POR EL CAMINO NI SE INVENTE NADA. Cada obra del
     catálogo está o en una función o contada con su razón; cada sede que el
     festival publicó en su mapa está en la tabla del plan y tiene coordenadas
     o un pendiente declarado; y los días sin programación del plan son
     exactamente los que el crudo deja vacíos.

El chequeo 2 es el que importa cuando llegue la parrilla: el día que salga,
estas cuentas tienen que moverse todas a la vez. Una que no se mueva es una
pieza que se quedó atrás.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import norm

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
CRUDO = f'{ST}/jardin-2026-crudo.json'
CAT = f'{ST}/jardin-2026-catalogo.json'
IG = f'{ST}/jardin-2026-ig.json'
GEO = f'{ST}/jardin-2026-venues-geo.json'
PLAN = f'{REPO}/pipeline/jardin-2026.plan.json'

DIAS = ['2026-09-24', '2026-09-25', '2026-09-26', '2026-09-27']

# SEDES SIN COORDENADA, y por qué no se inventa una. Una entrada aquí no es un
# permiso: es una pregunta abierta con fecha.
# Hoy está VACÍA —las cinco sedes tienen punto— y se queda igual: es la puerta
# por la que entraría la sede que el festival anuncie mañana sin dirección.
SIN_PUNTO_OK = {}


def mins(h):
    return int(h[:2]) * 60 + int(h[3:])


def main():
    c = json.load(open(CRUDO, encoding='utf-8'))
    cat = json.load(open(CAT, encoding='utf-8'))
    ig = json.load(open(IG, encoding='utf-8'))
    geo = json.load(open(GEO, encoding='utf-8'))
    cfg = json.load(open(PLAN, encoding='utf-8'))['festival']
    fs = c['funciones']
    fallos, avisos = [], []

    # 1 · día dentro del festival, hora, y sede de la tabla del plan
    for f in fs:
        if f['dia'] not in DIAS:
            fallos.append(f'«{f["titulo"][:40]}» cae en {f["dia"]}, fuera del festival')
        if not f.get('hora'):
            fallos.append(f'«{f["titulo"][:40]}» sin hora')
        if f.get('sede') not in cfg['sedes']:
            fallos.append(f'«{f["titulo"][:40]}»: sede «{f.get("sede")}» sin '
                          f'entrada en la tabla del plan')

    # 2 · ninguna sala usada dos veces a la vez
    for i, f in enumerate(fs):
        fin = mins(f['hora']) + (f.get('duracion_min') or 0)
        for g in fs[i + 1:]:
            if g['dia'] == f['dia'] and g['sede'] == f['sede'] and mins(g['hora']) < fin:
                fallos.append(f'{f["dia"][-2:]} «{f["titulo"][:26]}» solapa con '
                              f'«{g["titulo"][:26]}» en {f["sede"][:26]}')

    # 3 · LAS SEDES, en los dos sentidos. El festival publicó su mapa el 20 sep:
    #     ni nos podemos inventar una ni podemos perder una que él sí nombró.
    del_mapa, del_plan = set(ig['sedes']), set(cfg['sedes'])
    for s in sorted(del_mapa - del_plan):
        fallos.append(f'el mapa del festival nombra «{s}» y la tabla del plan no')
    for s in sorted(del_plan - del_mapa):
        fallos.append(f'la tabla del plan trae «{s}» y el mapa del festival no')
    for s in sorted(del_plan):
        g = geo.get(s) or {}
        if g.get('lat'):
            continue
        if s in SIN_PUNTO_OK:
            avisos.append(f'«{s}» sin coordenada — {SIN_PUNTO_OK[s]}')
        else:
            fallos.append(f'«{s}» sin coordenada y sin entrada en SIN_PUNTO_OK')

    # 4 · el catálogo entero, contado: o tiene función, o está declarado
    con_funcion = {norm(f['titulo']) for f in fs}
    declaradas = {norm(t) for v in (c.get('_sin_funcion') or {}).values()
                  for t in v['obras']}
    for o in cat['obras']:
        if norm(o['titulo']) not in con_funcion | declaradas:
            fallos.append(f'«{o["titulo"]}» está en el catálogo y no aparece ni '
                          f'en una función ni en _sin_funcion')
    for sec, v in (c.get('_sin_funcion') or {}).items():
        if not v.get('_por_que'):
            fallos.append(f'«{sec}»: {v["n"]} obras sin función y sin razón escrita')
        avisos.append(f'{v["n"]} obra(s) de «{sec}» esperando parrilla — {v["_por_que"]}')

    # 5 · los días vacíos declarados son los que de verdad están vacíos
    vacios_reales = sorted(set(DIAS) - {f['dia'] for f in fs})
    if vacios_reales != sorted(cfg.get('dias_vacios') or []):
        fallos.append(f'el plan declara dias_vacios={sorted(cfg.get("dias_vacios") or [])} '
                      f'y el crudo deja vacíos {vacios_reales}')

    # 6 · la casilla de acceso no se rellena sola
    for f in fs:
        if f.get('acceso') == 'desconocido' and cfg['acceso_por_defecto']['is_free'] is True:
            fallos.append(f'«{f["titulo"][:34]}» dice «desconocido» y el plan ya '
                          f'declara entrada libre: hay que decidir uno de los dos')

    print(f'jardin-2026: {len(fs)} función · {len(DIAS)} días · '
          f'{len(cfg["sedes"])} sedes · {len(cat["obras"])} obras en catálogo')
    for a in avisos:
        print('   · para mirar:', a)
    if fallos:
        print(f'\n✗ {len(fallos)} problema(s):')
        for f_ in fallos:
            print('   ✗', f_)
        sys.exit(1)
    print('\n✓ la función publicada tiene día, hora y sede de la tabla; las 5 sedes '
          'del mapa están en el plan; y las 37 obras del catálogo están todas '
          'contadas — con función o con su razón')


if __name__ == '__main__':
    main()
