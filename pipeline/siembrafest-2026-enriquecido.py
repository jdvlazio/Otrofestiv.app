# -*- coding: utf-8 -*-
"""El catálogo de la selección oficial → sidecar de enriquecimiento.

El catálogo (festivals/staging/siembrafest-2026.json, 84 obras de la selección
oficial) tiene forma de festival: `films[]`. El ensamblador genérico lee un
enriquecido con forma `{obras:[…]}` —y lib.cargar_plan() ya lo exige, porque un
sidecar con otra forma se carga sin error y no enriquece nada—. Esto lo traduce.

Aporta lo que el programa impreso NO trae: sinopsis, póster, país, género y
lbSlug. La jerarquía va declarada en siembrafest-2026-villeta.py.

Del póster hay dos fuentes y un orden entre ellas: el original de TMDB que trae
el catálogo, y —solo donde no hay original— la lámina que el festival publicó
en Instagram (siembrafest-2026-laminas.py). Nunca al revés.
"""
import json, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance                                          # noqa: E402
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
import importlib.util as _iu
_s = _iu.spec_from_file_location('_v', f'{REPO}/pipeline/siembrafest-2026-villeta.py')
_v = _iu.module_from_spec(_s); _s.loader.exec_module(_v)

# El vocabulario de género de la app (_GENRE_EN en sheets-controller.js) más
# «Ficción», que no está en el mapa pero lleva 110 obras en el repo.
GENEROS = {'accion', 'aventura', 'comedia', 'drama', 'documental', 'experimental',
           'romance', 'satira', 'terror', 'thriller', 'animacion', 'cienciaficcion',
           'fantasia', 'misterio', 'musical', 'musica', 'crimen', 'historia',
           'suspense', 'belica', 'familia', 'western', 'ficcion'}


def _genero(g):
    """UNO, el primero de la fuente que sea un género de verdad. El catálogo trae
    descripciones («Social, war, peace, religión») que no son géneros: la app las
    pintaría enteras en la ficha y no sabría traducirlas."""
    from lib import norm
    for x in re.split(r'[,/]| y ', g or ''):
        if norm(x.strip()) in GENEROS:
            return x.strip()
    return None


# La película invitada NO está en el catálogo —ese es la Selección Oficial— y
# tampoco tiene lámina: la serie de carruseles solo cubre la Selección. Viene del
# programa impreso y se enriquece a mano, contra TMDB.
INVITADA = {
    'titulo': 'Andariega',
    '_director_catalogo': 'Raúl Soto Rodríguez',   # = @raulsotorodriguez, el del festival
    'anio': 2025, 'pais': 'Colombia', 'genero': 'Documental',
    'poster_tmdb': '/uA5PZ9RBb23ESi1RVmnCosygXE0.jpg',
    'tmdb_id': 1456127,
    'lbSlug': 'nomad-spirit',                 # letterboxd.com/tmdb/1456127/ → 302
    # La ficha de TMDB tiene el overview en inglés y vacío en español; la frase
    # en español es la del propio festival, en su post de apertura.
    'sinopsis': 'Acompaña a una joven madre campesina en los caminos del trabajo '
                'rural y la cosecha de café.',
    'synopsis_en': 'Each year, 26-year-old María Yessenia Herrera, best known as '
                   '“Chena”, joins the traveling diaspora of peasants who move '
                   'around Colombia working as hand-picking coffee harvesters.',
}

CAT = f'{REPO}/festivals/staging/siembrafest-2026.json'
LAM = f'{REPO}/festivals/staging/siembrafest-2026-laminas.json'
OUT = f'{REPO}/festivals/staging/siembrafest-2026-enriquecido.json'

if __name__ == '__main__':
    cat = json.load(open(CAT, encoding='utf-8'))
    lam = {o['titulo']: o for o in json.load(open(LAM, encoding='utf-8'))['obras']} \
        if os.path.exists(LAM) else {}
    # el título con que lo llama el PROGRAMA, cuando el catálogo lo escribe de otra forma
    inverso = {v: k for k, v in _v.ALIAS_CATALOGO.items()}
    obras = []
    for f in cat['films']:
        o = {'titulo': inverso.get(f['title'], f['title'])}
        for src, dst in (('director', '_director_catalogo'), ('country', 'pais'),
                         ('genre', 'genero'), ('synopsis', 'sinopsis'),
                         ('synopsis_en', 'synopsis_en'), ('poster', 'poster'),
                         ('posterSource', 'posterSource'), ('lbSlug', 'lbSlug')):
            v = _genero(f[src]) if src == 'genre' else f.get(src)
            if v:
                o[dst] = v
        if not o.get('poster') and f['title'] in lam:
            o['poster'] = lam[f['title']]['poster']
            o['posterSource'] = lam[f['title']]['posterSource']
        if f['title'] in inverso:
            o['_titulo_catalogo'] = f['title']
        obras.append(o)
    obras.append(dict(INVITADA))
    json.dump({'_provenance': provenance(
                 'selección oficial publicada por el festival — siembrafest.com/seleccion-sf-2026/',
                 metodo='traducción del catálogo (films[]) al sidecar de enriquecimiento '
                        '({obras:[…]}), que es la forma que lee el ensamblador'),
               'obras': obras}, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{len(obras)} obras → {OUT}')
