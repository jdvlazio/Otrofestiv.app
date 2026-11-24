#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ficha_unica.py — UN director, UN año y UN país por obra en todos los festivales.

POR QUÉ EXISTE (24 nov 2026, Juan): son de la obra, como el afiche
(afiches_unicos.py) y la sinopsis (sinopsis_unicas.py). Ese día diferían entre
festivales 129 obras en director, 54 en año y 78 en país: grafías («Garcia JC»),
nombres a medias, coproducciones incompletas, países en inglés. Lo elegido vive
en catalogo/decisiones.json (`directores`, `anio`, `paises`). La duración NO:
es de la copia que proyecta cada festival.

También el GÉNERO (`generos`) y la SINOPSIS EN INGLÉS (`sinopsis.en`), desde el
mismo día. El género publicado va en español (la app lo traduce): TIFF lo
traía en inglés, y así se leía en la app en español.

Solo reemplaza un dato publicado; donde no hay dato no lo pone (eso es herencia).

    python3 pipeline/ficha_unica.py --aplicar [<festival>] [--escribir]
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))


GENEROS = {'Documentary': 'Documental', 'documental': 'Documental', 'documentales': 'Documental', 'History': 'Historia',
           'Comedy': 'Comedia', 'Science Fiction': 'Ciencia ficción', 'Ciencia Ficción': 'Ciencia ficción', 'Crime': 'Crimen',
           'Action': 'Acción', 'Horror': 'Terror', 'War': 'Bélica', 'Music': 'Música', 'Animation': 'Animación',
           'Mystery': 'Misterio', 'ficción': 'Ficción', 'Thiller': 'Thriller', 'Familiar': 'Familia'}


def elegidos(decs):
    """{work_id: {campo publicado: valor}} de las decisiones de ficha."""
    from herencia import _pais_es
    eleg = {}
    for x in decs:
        if x['campo'] == 'directores':
            eleg.setdefault(x['work_id'], {})['director'] = ', '.join(x['valor'])
        elif x['campo'] == 'anio':
            eleg.setdefault(x['work_id'], {})['year'] = x['valor']
        elif x['campo'] == 'paises' and _pais_es(x['valor']):
            eleg.setdefault(x['work_id'], {})['country'] = _pais_es(x['valor'])
        elif x['campo'] == 'generos' and x['valor']:
            eleg.setdefault(x['work_id'], {})['genre'] = x['valor'][0]
        elif x['campo'] == 'sinopsis.en' and x['valor']:
            eleg.setdefault(x['work_id'], {})['synopsis_en'] = x['valor']
    return eleg


def aplicar(d, decs=None):
    """Lo elegido, en el JSON del festival `d` (en el lugar). La usan publicar.py y
    --aplicar. → [(título, campo, antes, después)]"""
    import catalogo
    from lib import banderas
    if decs is None:
        decs = catalogo.decisiones()
    eleg = elegidos(decs)
    out = []
    for f in d.get('films', []):
        for o in (f.get('film_list') or [f]):
            if o.get('type') == 'event':
                continue
            g = o.get('genre')
            if g in GENEROS:
                o['genre'] = GENEROS[g]
                out.append((o.get('title'), 'genre', g, o['genre']))
            for k, v in eleg.get(o.get('work_id'), {}).items():
                if o.get(k) in (None, '') or str(o[k]) == str(v):
                    continue
                out.append((o.get('title'), k, o[k], v))
                o[k] = str(v) if isinstance(o[k], str) else v
                if k == 'country' and banderas(v):
                    o['flags'] = banderas(v)
    return out


if __name__ == '__main__':
    if '--aplicar' not in sys.argv:
        sys.exit(__doc__)
    import glob
    import json
    from sinopsis_unicas import _guardar
    solo = next((a for a in sys.argv[1:] if not a.startswith('--')), None)
    tot = 0
    for p in sorted(glob.glob(f'{REPO}/festivals/*.json')):
        if solo and os.path.basename(p) != f'{solo}.json':
            continue
        d = json.load(open(p, encoding='utf-8'))
        c = aplicar(d) if isinstance(d, dict) else []
        if c:
            print(f'{os.path.basename(p)[:-5]:22} {len(c)}')
            tot += len(c)
            if '--escribir' in sys.argv:
                _guardar(p, d)
    print(tot, 'datos' + ('' if '--escribir' in sys.argv else ' (solo muestra; --escribir para guardarlo)'))
