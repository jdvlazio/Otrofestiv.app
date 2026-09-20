#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""conexcine-2026-crudo.py — las 13 funciones del 3° CONEXCINE.

JUNTA TRES FUENTES, cada una con lo que sabe:

  · la PARRILLA del PDF (p2) — día, hora de inicio y de fin, y las líneas que
    el festival imprime en cada bloque. Es la única fuente con horarios.
  · el CATÁLOGO del PDF (p3) — qué cortos lleva cada programa, su departamento,
    y la duración de los tres largos.
  · INSTAGRAM — el DIRECTOR de cada corto, que el PDF no publica en ninguna
    parte, leído de las láminas del carrusel de Selección Oficial.

CÓMO SE EMPAREJA UN BLOQUE CON SU PROGRAMA. El bloque imprime «PROGRAMA 2:
Entre el mar y la luna» y el catálogo titula igual: el emparejamiento es por
ese rótulo, normalizado. Un bloque que nombre un programa que el catálogo no
tiene es un FALLO, no un bloque vacío — el PDF se contradiría a sí mismo.

LA SEDE. El PDF solo nombra una, y solo para el conversatorio. La de todo lo
demás la dice el festival en Instagram (cuatro posts, dos cuentas): Biblioteca
Pública Julio Pérez Ferrero. Va como defecto DECLARADO en el plan, no como
conjetura de este script.

Salida: festivals/staging/conexcine-2026-crudo.json
"""
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import provenance, norm

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
PAR = f'{ST}/conexcine-2026-parrilla.json'
CAT = f'{ST}/conexcine-2026-catalogo.json'
IG = f'{ST}/conexcine-2026-ig.json'
OUT = f'{ST}/conexcine-2026-crudo.json'
PLAN = f'{REPO}/pipeline/conexcine-2026.plan.json'

SEDE_DEFECTO = 'Biblioteca Pública Julio Pérez Ferrero'

# QUÉ ES CADA BLOQUE QUE NO ES UNA PROYECCIÓN DE COMPETENCIA. El patrón se
# busca en las líneas del bloque; el título es VERBATIM del festival y el
# `event_kind` es el vocabulario de la app.
ACTIVIDAD = [
    (r'conversatorio', 'Conversatorio sobre formulación de proyectos para '
                       'convocatorias, mercados y festivales',
     'Conversatorios', 'charla'),
    (r'exposicion proyectarte', 'Exposición Proyectarte',
     'Actividades Culturales', 'experiencia'),
    (r'ceremonia de clausura', 'Ceremonia de Clausura',
     'Actividades Culturales', 'clausura'),
]

# LOS TRES LARGOS, por la línea con que el bloque los nombra.
# Los patrones se escriben COMO QUEDAN TRAS norm(): sin tildes y sin guiones.
# «mu-ki-ra» no casaba nunca contra el texto normalizado «mu ki ra», y el
# bloque del sábado se caía a «sin clasificar» — que es exactamente lo que el
# aviso tiene que hacer cuando un patrón mío está mal escrito.
LARGOS = {
    'el juego de la vida': 'El Juego de la Vida',
    'adios al amigo': 'Adiós al Amigo',
    'mu ki ra': 'MU-KI-RA',
}


def poster_local(titulo):
    """El póster de TMDB, SERVIDO POR NOSOTROS. `enriquecer.py --posters` ya lo
    bajó a assets/ con el slug del título; publicando en su lugar la URL remota
    de image.tmdb.org el archivo se queda en el repo sin que nada lo nombre
    —un huérfano que el CI caza— y además se salta `encuadrar-posters.py`, que
    solo recorta archivos locales. FICMA publica así sus 67."""
    from lib import slug
    f = f'{REPO}/assets/conexcine-2026/{slug(titulo)}.jpg'
    if os.path.exists(f) and os.path.getsize(f) > 5000:
        return f'/assets/conexcine-2026/{slug(titulo)}.jpg'
    return ''




def main():
    par = json.load(open(PAR, encoding='utf-8'))
    cat = json.load(open(CAT, encoding='utf-8'))
    plan = json.load(open(PLAN, encoding='utf-8'))['festival']
    ig = json.load(open(IG, encoding='utf-8'))['obras'] if os.path.exists(IG) else []

    # el director, por título, desde Instagram
    dires = {norm(o['titulo']): o['director'] for o in ig if o.get('director')}
    # LA FICHA DE TMDB, para los cortos que la tienen. La trae un paso propio y
    # no `enriquecer.py`: el candado genérico exige año o duración y el PDF de
    # este festival no publica ninguno de los dos, así que no podía abrirse ni
    # con la obra delante. El de `lib.ficha_tmdb` decide por título idéntico +
    # director, que es el caso de un festival de cortos.
    ft = {}
    ft_p = f'{ST}/conexcine-2026-fichas-tmdb.json'
    if os.path.exists(ft_p):
        for t, e in json.load(open(ft_p, encoding='utf-8'))['fichas'].items():
            ft[norm(t)] = e
    CAMPOS = ('tmdb_id', 'anio', 'duracion_min', 'genero', 'sinopsis',
              'sinopsis_en', 'title_en', 'pais', 'poster', 'posterSource', 'lbSlug')
    # las obras de cada programa, y las de cada sección suelta
    porprog, porsec = {}, {}
    for o in cat['obras']:
        if o.get('programa'):
            porprog.setdefault(norm(o['programa']), []).append(o)
        else:
            porsec.setdefault(norm(o['seccion']), []).append(o)
    largos = {norm(l['titulo']): l for l in cat['largos']}

    def obra(o):
        d = dires.get(norm(o['titulo']), '')
        f = ft.get(norm(o['titulo']), {})
        return {'titulo': o['titulo'], **({'director': d} if d else {}),
                'pais': o.get('pais') or 'Colombia',
                '_departamento': o.get('departamento', ''),
                **{k: f[k] for k in CAMPOS if f.get(k)},
                '_src': o['_src']}

    funciones, avisos = [], []
    for b in sorted(par['bloques'], key=lambda b: (b['dia'], b['hora'])):
        txt = ' '.join(b['lineas'])
        n = norm(txt)
        reg = {'dia': b['dia'], 'hora': b['hora'], 'sede': SEDE_DEFECTO,
               'duracion_min': b['duracion_min'],
               'is_free': plan['acceso_por_defecto']['is_free'],
               'acceso': 'Entrada libre',
               '_jornada': b.get('jornada', ''),
               '_src': {'url': ('https://drive.google.com/file/d/'
                                '1x0l0MwffrReBexjv_d312trbZvZ5JP5p/view'),
                        'date': '2026-09-19'}}

        # ¿una actividad?
        act = next((a for a in ACTIVIDAD if re.search(a[0], n)), None)
        if act:
            _, titulo, seccion, kind = act
            reg.update({'titulo': titulo, 'seccion': seccion,
                        'tipo': 'evento', 'event_kind': kind})
            # la ÚNICA sede que el PDF nombra, y solo para este bloque
            if 'torre del reloj' in n:
                reg['sede'] = 'Auditorio TORRE DEL RELOJ'
            funciones.append(reg)
            continue

        # ¿uno de los tres largos?
        lg = next((v for k, v in LARGOS.items() if re.search(k, n)), None)
        if lg:
            l = largos[norm(lg)]
            # EL DIRECTOR DEL LARGO LO IMPRIME EL BLOQUE, y solo ahí: el
            # carrusel de Instagram lista los CORTOS de la Selección Oficial,
            # no los tres largos de Proyecciones Especiales. Buscándolo solo en
            # IG, las tres películas salían sin dirección y el enricher no
            # podía abrir su candado —que exige director— así que las tres se
            # quedaban sin ficha y sin póster, y el gate de pósters bloqueaba.
            dir_pdf = next((re.sub(r'^Dir\.?\s*', '', x).strip()
                            for x in b['lineas']
                            if re.match(r'^Dir\.?\s', x.strip())), '')
            # LA DURACIÓN REAL MANDA (regla de Juan). El bloque del jueves mide
            # 180 min y la película 95: se publica la casilla porque el bloque
            # incluye «Presentaciones Culturales», pero la de la OBRA queda
            # aparte para verificarla contra TMDB.
            reg.update({'titulo': lg, 'seccion': 'Proyecciones Especiales',
                        'pais': 'Colombia', 'duracion_obra': l['duracion_min'],
                        'director': dires.get(norm(lg)) or dir_pdf,
                        **({'poster': poster_local(lg), 'posterSource': 'tmdb'}
                           if poster_local(lg) else {})})
            if not reg['director']:
                reg.pop('director')
            funciones.append(reg)
            continue

        # ¿un programa de cortos?
        prog = next((k for k in porprog if k and k in n), '')
        if prog:
            obras = porprog[prog]
            reg.update({'titulo': obras[0]['programa'],
                        'seccion': obras[0]['seccion'], 'is_cortos': True,
                        'obras': [obra(o) for o in obras]})
            funciones.append(reg)
            continue

        # ¿la inauguración, que proyecta la competencia En(Foco) entera?
        if 'en foco' in n or 'enfoco' in n:
            obras = porsec.get(norm('Competencia En(Foco) Santanderes'), [])
            reg.update({'titulo': 'Inauguración 3° CONEXCINE',
                        'seccion': 'Competencia En(Foco) Santanderes',
                        'tipo': 'evento', 'event_kind': 'apertura',
                        'is_cortos': True,
                        'obras': [obra(o) for o in obras]})
            funciones.append(reg)
            continue

        avisos.append(f'{b["dia"][-2:]} {b["hora"]} sin clasificar: «{txt[:60]}»')

    # UNA ACTIVIDAD NO LLEVA FICHA DE OBRA. Va al final a propósito: puesto
    # antes, las ramas de arriba volvían a ponerle los campos.
    for f in funciones:
        if f.get('tipo') == 'evento' and not f.get('is_cortos'):
            for k in ('pais', 'director', 'duracion_obra'):
                f.pop(k, None)

    json.dump({'_provenance': provenance(
        'Programación Oficial CONEXCINE 2026 (PDF, páginas 2 y 3) + las láminas '
        'de «Selección Oficial» en Instagram',
        que_aporta='13 funciones con día, hora y sede; los cortos de cada '
                   'programa con su departamento; y el director de cada obra',
        url='https://www.fedecajas.com/conexcine/',
        metodo='el PDF leído tres veces con herramientas distintas (poppler, '
               'MuPDF y el OCR del sistema sobre los píxeles) y cruzado contra '
               'Instagram, que es la que aporta los directores'),
        'funciones': funciones, 'avisos': avisos},
        open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    cortos = sum(len(f.get('obras') or []) for f in funciones)
    ev = sum(1 for f in funciones if f.get('tipo') == 'evento')
    con_dir = sum(1 for f in funciones for o in (f.get('obras') or [])
                  if o.get('director'))
    print(f'{len(funciones)} funciones · {ev} actividades · {cortos} cortos '
          f'({con_dir} con director) → {OUT.split("/")[-1]}')
    for f in funciones:
        print(f'  {f["dia"][-2:]} {f["hora"]} {f["duracion_min"]:>4}m  '
              f'{f["titulo"][:44]:46} {f["sede"][:22]}')
    for a in avisos:
        print('   ·', a)
    if avisos:
        sys.exit(1)


if __name__ == '__main__':
    main()
