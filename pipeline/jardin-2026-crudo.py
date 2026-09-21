#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""jardin-2026-crudo.py — lo que el 11° Festival de Cine de Jardín SÍ fechó.

A CUATRO DÍAS DEL FESTIVAL HAY UNA SOLA FUNCIÓN CON DÍA, HORA Y SEDE: la
inaugural. El catálogo tiene 37 obras con ficha completa desde el 15 de
septiembre y ninguna otra tiene cuándo ni dónde. Este paso NO rellena ese hueco:
publica la que existe y deja las otras 36 contadas, con su razón, en
`_sin_funcion`. Sin día, hora y sede no se publica una función — la regla es
vieja y es de las que no se negocian.

DE DÓNDE SALE CADA CAMPO. Del catálogo de la web sale la ficha de la obra
(país, idioma, género, duración, sinopsis, año, dirección), porque está escrita
a máquina por el festival. De la lámina de Instagram salen el día, la hora, la
sede y el «Estreno mundial» — que la web no publica en ninguna parte. Donde las
dos hablan y no coinciden manda la web, y la discrepancia va declarada en
`jardin-2026-contraste.py`, no resuelta en silencio aquí.

LA CASILLA DE ACCESO LA DECIDIÓ JUAN, y por eso la palabra la pone el PLAN y no
este script. Ninguna fuente del festival dice en esta edición si se entra
gratis: lo dice un tercero en Instagram y lo decía la página de la primera
edición, de 2016. Juan lo zanjó el 20 sep —«Entrada libre, siempre. A todas las
funciones»— y en `acceso_por_defecto._por_que` queda escrito que la decisión es
suya, no un dato que hayamos leído. Si el festival lo desmiente se cambia allí,
en un sitio, y se re-corre.

Lee   festivals/staging/jardin-2026-catalogo.json
      festivals/staging/jardin-2026-ig.json
      festivals/staging/jardin-2026-posters.json
Esc.  festivals/staging/jardin-2026-crudo.json
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import norm, provenance

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
PLAN = f'{REPO}/pipeline/jardin-2026.plan.json'
CAT = f'{ST}/jardin-2026-catalogo.json'
IG = f'{ST}/jardin-2026-ig.json'
POS = f'{ST}/jardin-2026-posters.json'
OUT = f'{ST}/jardin-2026-crudo.json'

# La ficha de la obra, de la web al formato intermedio. Solo renombra: si un
# campo hubiera que TRADUCIRLO, no iría aquí — iría discutido y declarado.
DE_LA_WEB = {'pais': 'pais', 'idioma': 'idioma', 'genero': 'genero',
             'duracion_min': 'duracion_min', 'sinopsis': 'sinopsis',
             'anio': 'anio', 'director': 'director', 'clasificacion': 'rating'}

# POR QUÉ CADA GRUPO DE OBRAS SE QUEDA FUERA. La clave es la sección tal como
# la escribe el catálogo; un grupo sin entrada hace fallar el paso.
SIN_FUNCION_OK = {
    'Muestra Central': 'el festival publicó su ficha el 15 sep y no ha '
                       'publicado en qué día, a qué hora ni en qué sede se '
                       'proyectan. Solo la inaugural tiene función.',
    'CALEIDOSCOPIO': 'los 22 cortos de la competencia nacional están '
                     'anunciados desde el 2 y el 4 de septiembre, y el propio '
                     'festival dice que se exhiben — pero no ha publicado las '
                     'sesiones. Sin día, hora y sede no hay función.',
}


def genero_de(w):
    """El género de un corto de CALEIDOSCOPIO.

    La ficha de un largo imprime «Género: Documental / musical / ambiental». La
    de un corto no tiene esa línea: imprime la palabra suelta —«Documental»,
    «Ficción», «Experimental»— justo bajo el título, en el mismo sitio de la
    maqueta, y el raspador la guarda como `categoria` porque además es el eje
    por el que el festival parte la competencia. Es la misma palabra del mismo
    festival en el mismo lugar: se publica como género. No se traduce ni se
    completa — un corto sin esa línea se queda sin género."""
    if not w.get('genero') and w.get('categoria'):
        return {'genero': w['categoria']}
    return {}


def poster_de(w, pos):
    """El afiche YA BAJADO por `jardin-2026-posters.py`, servido por nosotros.

    Nunca la URL remota: un archivo en assets/ que ningún JSON nombra es un
    huérfano que el CI caza, y publicar la URL de image.tmdb.org además se
    salta el encuadre, que solo trabaja sobre archivos locales. Es la lección
    que costó los 16 pósters sueltos de Villa del Cine."""
    e = pos.get(norm(w['titulo']))
    return {'poster': e['poster'], 'posterSource': e['posterSource']} if e else {}


def main():
    cat = json.load(open(CAT, encoding='utf-8'))
    ig = json.load(open(IG, encoding='utf-8'))
    pos = {}
    if os.path.exists(POS):
        pos = {norm(x['title']): x
               for x in json.load(open(POS, encoding='utf-8'))['films']}
    acc = json.load(open(PLAN, encoding='utf-8'))['festival']['acceso_por_defecto']
    palabra = 'Entrada libre' if acc.get('is_free') is True else str(acc.get('is_free'))
    web = {norm(o['titulo']): o for o in cat['obras']}

    funciones, usadas = [], set()
    for f in ig['funciones']:
        w = web.get(norm(f['titulo']))
        if not w:
            sys.exit(f'✗ «{f["titulo"]}» tiene función y no tiene ficha en el '
                     f'catálogo. Mirar antes de publicarla a medias.')
        usadas.add(norm(f['titulo']))
        reg = {'titulo': w['titulo'], 'dia': f['dia'], 'hora': f['hora'],
               'sede': f['sede'], 'seccion': w['seccion'],
               'acceso': palabra,
               '_src': {'url': f'https://www.instagram.com/festicinejardin/',
                        'date': '2026-09-20'}}
        for orig, dest in DE_LA_WEB.items():
            if w.get(orig):
                reg[dest] = w[orig]
        reg.update(genero_de(w))
        reg.update(poster_de(w, pos))
        # LO QUE SOLO DICE LA LÁMINA. «Estreno mundial» es palabra del festival
        # y va verbatim en `premiere`, que es el campo del contrato para eso.
        if f.get('_estreno'):
            reg['premiere'] = 'Estreno mundial'
        # la duración de la función es la de la obra: no hay bloque que la
        # envuelva, es una proyección y ya.
        reg['duracion_min'] = w.get('duracion_min') or f.get('duracion_obra')
        if f.get('event_kind') == 'apertura':
            reg['_apertura'] = ('la lámina 1 la rotula «ACTO INAUGURAL». Se '
                                'publica en su sección de catálogo, «Muestra '
                                'Central», que es donde el festival la ficha.')
        funciones.append(reg)

    sin, fallos = {}, []
    for o in cat['obras']:
        if norm(o['titulo']) in usadas:
            continue
        sin.setdefault(o['seccion'], []).append(o['titulo'])
    for sec in sin:
        if sec not in SIN_FUNCION_OK:
            fallos.append(f'{len(sin[sec])} obra(s) de «{sec}» sin función y sin '
                          f'entrada en SIN_FUNCION_OK')

    json.dump({'_provenance': provenance(
        'festicinejardin.com (la ficha de cada obra) + las láminas de Instagram '
        'de @festicinejardin (día, hora, sede y el estreno)',
        que_aporta='la única función que el festival ha fechado, con la ficha '
                   'completa de su obra',
        url='https://festicinejardin.com/',
        metodo='las dos superficies del festival, contrastadas campo a campo en '
               'jardin-2026-contraste.py. Donde discrepan manda la web, que '
               'está escrita a máquina, y la discrepancia queda declarada',
        alcance=f'{len(funciones)} función de las {len(cat["obras"])} obras del '
                f'catálogo — el resto no tiene día, hora ni sede'),
        'funciones': funciones,
        '_sin_funcion': {sec: {'n': len(ts), '_por_que': SIN_FUNCION_OK.get(sec, ''),
                               'obras': sorted(ts)}
                         for sec, ts in sorted(sin.items())},
        '_sedes_publicadas_sin_funcion': [
            s for s in ig['sedes'] if s not in {f['sede'] for f in funciones}]},
        open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    print(f'{len(funciones)} función · {sum(len(v) for v in sin.values())} obras '
          f'del catálogo esperando parrilla → {OUT.split("/")[-1]}')
    for f in funciones:
        print(f'  {f["dia"][-2:]} {f["hora"]} {f["duracion_min"]:>4}m  '
              f'{f["titulo"][:40]:42} {f["sede"]}')
    for sec, ts in sorted(sin.items()):
        print(f'  · {len(ts):2} de «{sec}» sin función')
    if fallos:
        print(f'\n✗ {len(fallos)} problema(s):')
        for x in fallos:
            print('   ✗', x)
        sys.exit(1)


if __name__ == '__main__':
    main()
