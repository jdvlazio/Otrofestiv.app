# -*- coding: utf-8 -*-
"""Asigna el `lbSlug` de Letterboxd a cada obra y a cada corto de TIFF 2026.

POR QUÉ EXISTE
El botón de Letterboxd va en TODAS las fichas de la app, cortos incluidos. TIFF
da el catálogo y la programación, pero no el slug; Letterboxd sí, en su lista
oficial del festival. Este script los casa.

LAS DOS GRANULARIDADES
TIFF lista 244 «obras», pero 13 son PROGRAMAS que agrupan 72 cortos, y
Letterboxd lista los cortos sueltos. El universo real a casar es 231 obras
individuales + 72 cortos = 303, contra las 259 entradas de Letterboxd. Un
programa NO recibe slug: no es una obra, es un envase.

DOS TRAMPAS QUE ESTE SCRIPT YA PISÓ, Y POR ESO ESTÁN BLINDADAS

1. La normalización que se vacía. Un título en armenio, chino o japonés
   —«月宫», «咒语», «Տապակած Հավ»— queda en cadena VACÍA al pasarlo a ASCII. La
   primera versión usaba esa cadena vacía como clave de búsqueda, así que cinco
   obras distintas recibieron todas el slug de «The Age of Goodbyes». Una clave
   vacía no identifica nada: aquí se descarta antes de buscar.

2. El homónimo. En este mismo festival hay DOS cortos llamados «The End»: el de
   Pelechian (1992) y el de Niki Lindroth von Bahr (2026). Indexar por título y
   quedarse con el primero le colgaba el slug de 1992 a los dos. Por eso el
   índice guarda TODOS los candidatos de un título y, cuando hay más de uno, se
   desempata por director y año. Si el empate no se rompe, la obra se queda SIN
   slug y se reporta: es la lección de FantasoFest —«Peephole» tenía cinco
   homónimos y ninguno era el nuestro—.

Al final hay un candado explícito: ningún slug puede quedar asignado a dos
obras. Si ocurre, el script falla en vez de publicar un dato falso.
"""
import json, os, re, sys, unicodedata
from difflib import SequenceMatcher

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import provenance

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
UMBRAL = 0.90

# Títulos que ninguna similitud puede alcanzar, porque TIFF y Letterboxd usan
# nombres distintos para la misma obra: traducción, título de reestreno o
# nombre en idioma original. Cada línea se verificó comparando el DIRECTOR con
# ambas fuentes a la vista; ninguna se aceptó por parecido de título.
#   TIFF → lbSlug
ALIAS = {
    'Life of Jorge Luis Borges': 'biografia-de-jorge-luis-borges',      # Mariano Llinás
    "Ken Russell's The Devils": 'the-devils',                           # Ken Russell, 1971
    'Viva Carmen': 'love-is-a-gypsy-child-a-carmen-story',              # Sébastien Laudenbach
    '(Haboolm Ksinaalgat) Soul Catcher': 'soul-catcher-1',              # Strong + Post
    # El director coincide salvo por una tilde que TIFF perdió:
    # «Nguyễn Phan Quang Bình» (Letterboxd) vs «...Binh» (TIFF).
    'Spirit Guardians: The Last Secret of the First Emperor': 'ho-linh-trang-si-bi-an-mo-vua-inh',
}



def norm(s):
    s = unicodedata.normalize('NFKD', (s or '').lower())
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r'^(the|a|an|le|la|les|el|los|un|une)\s+', '', s)
    return re.sub(r'[^a-z0-9]+', '', s)


def mismo_director(a, b):
    """Comparación por token largo. Vacío en cualquier lado → None (no decide)."""
    ta = {t for n in (a or []) for t in norm(n and re.sub(r'(?<=.)(?=[A-Z])', ' ', n)).split() if len(t) > 3}
    ta = {t for n in (a or []) for t in re.split(r'[^a-z0-9]+', unicodedata.normalize('NFKD', n.lower())) if len(t) > 3}
    tb = {t for n in (b or []) for t in re.split(r'[^a-z0-9]+', unicodedata.normalize('NFKD', n.lower())) if len(t) > 3}
    if not ta or not tb:
        return None
    return bool(ta & tb)


def desempatar(cands, u):
    """De varios candidatos homónimos, el que concuerde en director o año."""
    if len(cands) == 1:
        return cands[0], 'unico'
    ported = [c for c in cands if mismo_director(u.get('directores'), c.get('directores')) is True]
    if len(ported) == 1:
        return ported[0], 'director'
    pool = ported or cands
    if u.get('anio'):
        pora = [c for c in pool if str(c.get('anio') or '') == str(u['anio'])]
        if len(pora) == 1:
            return pora[0], 'anio'
    return None, f'ambiguo x{len(cands)}'


def main():
    ofi = json.load(open(f'{ST}/tiff-2026-oficial.json', encoding='utf-8'))['obras']
    cor = json.load(open(f'{ST}/tiff-2026-cortos.json', encoding='utf-8'))['programas']
    lb = json.load(open(f'{ST}/tiff-2026-tmdb.json', encoding='utf-8'))['obras']

    idx = {}
    for x in lb:
        for t in (x.get('titulo_lb'), x.get('titulo'), x.get('titulo_original')):
            k = norm(t)
            if not k:          # trampa 1: una clave vacía no identifica nada
                continue
            idx.setdefault(k, [])
            if x not in idx[k]:
                idx[k].append(x)

    programas = {p['slug'] for p in cor}
    universo = ([{'tipo': 'obra', 'clave': o['slug'], 'titulo': o['titulo'], 'alt': None,
                  'directores': o.get('directores'), 'anio': None}
                 for o in ofi if o['slug'] not in programas] +
                [{'tipo': 'corto', 'clave': c['id'], 'titulo': c['titulo'],
                  'alt': c.get('tituloAlt'), 'directores': c.get('directores'),
                  'anio': c.get('anio'), 'programa': p['slug']}
                 for p in cor for c in p['cortos']])

    por_slug = {x['lbSlug']: x for x in lb}
    res, difusos, ambiguos, sin = [], [], [], []
    for u in universo:
        if u['titulo'] in ALIAS:
            x = por_slug[ALIAS[u['titulo']]]
            res.append(dict(u, lbSlug=x['lbSlug'], tmdb_id=x.get('tmdb_id'),
                            _match='alias/verificado por director'))
            continue
        cands = idx.get(norm(u['titulo'])) or (idx.get(norm(u['alt'])) if u['alt'] else None)
        modo = 'exacto'
        if not cands:
            mejor, punt = None, 0.0
            for k, xs in idx.items():
                p = SequenceMatcher(None, norm(u['titulo']), k).ratio()
                if p > punt:
                    mejor, punt = xs, p
            if punt >= UMBRAL:
                cands, modo = mejor, f'difuso {punt:.2f}'
        if not cands:
            sin.append(u)
            continue
        cand, via = desempatar(cands, u)
        if not cand:
            ambiguos.append({'tiff': u['titulo'], 'candidatos': [c['lbSlug'] for c in cands],
                             'motivo': via})
            sin.append(u)
            continue
        res.append(dict(u, lbSlug=cand['lbSlug'], tmdb_id=cand.get('tmdb_id'),
                        _match=f'{modo}/{via}'))
        if modo != 'exacto':
            difusos.append({'tiff': u['titulo'], 'letterboxd': cand['titulo_lb'],
                            'lbSlug': cand['lbSlug'], 'modo': modo})

    # Candado: un slug, una obra. Sin esto se publica un dato falso en silencio.
    vistos = {}
    choques = []
    for r in res:
        if r['lbSlug'] in vistos:
            choques.append((r['lbSlug'], vistos[r['lbSlug']], r['titulo']))
        vistos[r['lbSlug']] = r['titulo']
    if choques:
        for s, a, b in choques:
            print(f'  CHOQUE {s}: «{a}» y «{b}»')
        sys.exit(f'{len(choques)} slug(s) asignados a más de una obra. Abortado.')

    usados = {r['lbSlug'] for r in res}
    huerfanos = [x['titulo_lb'] for x in lb if x['lbSlug'] not in usados]
    salida = f'{ST}/tiff-2026-lbslug.json'
    json.dump({'_provenance': provenance('cruce tiff-2026-oficial + tiff-2026-cortos + tiff-2026-tmdb',
                                         metodo=f'titulo exacto, luego original, luego similitud >= {UMBRAL}; '
                                                'homonimos desempatados por director y anio'),
               '_universo': len(universo), '_con_slug': len(res),
               '_difusos': difusos, '_ambiguos': ambiguos,
               '_sin_slug': [u['titulo'] for u in sin],
               '_letterboxd_sin_usar': huerfanos,
               'obras': res}, open(salida, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    print(f'── universo {len(universo)} · con lbSlug {len(res)} · sin slug {len(sin)}')
    print(f'   difusos {len(difusos)} · ambiguos {len(ambiguos)} · '
          f'Letterboxd sin usar {len(huerfanos)}')
    for a in ambiguos:
        print(f'   ? {a["tiff"][:38]:40} {a["candidatos"]} ({a["motivo"]})')
    print(f'── {salida}')


if __name__ == '__main__':
    main()
