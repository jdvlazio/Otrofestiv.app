# -*- coding: utf-8 -*-
"""Las obras del catálogo que NO existen en TMDB, listas para darlas de alta.

Sin ficha en TMDB no hay Letterboxd —Letterboxd se alimenta de TMDB—, así que
estas 43 obras no pueden ganar `lbSlug` ni sinopsis por barrido: hay que crearlas
a mano (pipeline/PROTOCOLO.md, fase 3b). Este paso deja la lista con todo lo que
el formulario de alta pide, para no volver a reunirlo obra por obra.

El año y el director salen de las cápsulas de Instagram del propio festival —cada
carrusel de sección lista sus obras como «• Título (año) — Dir. Nombre»—, que es
más de lo que trae su web. Donde su Instagram y su web no coinciden en el
director van los dos: es una discrepancia suya, no nuestra, y quien dé el alta
tiene que verla antes de elegir.

    python3 pipeline/siembrafest-2026-altas.py
"""
import json, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import norm, provenance                                    # noqa: E402
from ig_carrusel import laminas as _carrusel                        # noqa: E402
import importlib.util as _iu                                        # noqa: E402
_s = _iu.spec_from_file_location('_l', f'{REPO}/pipeline/siembrafest-2026-laminas.py')
_l = _iu.module_from_spec(_s); _s.loader.exec_module(_l)

CAT = f'{REPO}/festivals/staging/siembrafest-2026.json'
SALIDA = f'{REPO}/festivals/staging/siembrafest-2026-altas-candidatas.json'

# «• Título (2025) — Dir. Nombre» — el guion puede ser raya o medio raya
FICHA = re.compile(r'^[•\-•]\s*(.+?)\s*\((\d{4})\)\s*[—–-]\s*Dir\.\s*(.+?)\s*$')


def del_instagram():
    """Título → (año, director) leído de las cápsulas de los nueve carruseles."""
    out = {}
    for sc in _l.POSTS.values():
        for linea in _carrusel(sc)['caption'].split('\n'):
            m = FICHA.match(linea.strip())
            if m:
                out[norm(m.group(1))] = (int(m.group(2)), m.group(3))
    return out


if __name__ == '__main__':
    cat = json.load(open(CAT, encoding='utf-8'))['films']
    ig = del_instagram()
    obras = []
    for f in cat:
        if (f.get('_src') or {}).get('tmdb_id') or f.get('lbSlug'):
            continue                                  # esa ya tiene ficha
        anio, director = ig.get(norm(f['title']), (None, None))
        web = f.get('director')
        obras.append({
            'title': f['title'],
            'director': director or web,
            # solo cuando su IG y su web no dicen lo mismo: quien dé el alta elige
            'director_web': web if director and norm(director) != norm(web or '') else None,
            'year': anio or f.get('year'),
            'duration': f.get('duration'),
            'country': f.get('country'),
            'synopsis': f.get('synopsis') or None,
            'synopsis_lang': f.get('synopsis_lang') or None,
            'section': f.get('section'),
        })
    json.dump({'_provenance': provenance(
        'catálogo de la Selección Oficial + cápsulas «Presentamos <sección>» de '
        'instagram.com/siembrafest',
        metodo='obras sin ficha en TMDB tras DOS barridos: el de agosto por título, y el '
               'del 5 sep con el año y el director que el festival publica en sus '
               'cápsulas. 26 de las 43 dan CERO resultados en TMDB — no es un problema '
               'de desambiguación, no existen',
        para='darlas de alta en TMDB (pipeline/PROTOCOLO.md, fase 3b) y de ahí sacar el '
             'botón de Letterboxd. Sin alta no hay lbSlug: Letterboxd se alimenta de TMDB',
        ojo='verificar con las 3 sondas de siempre (título, filmografía del director, '
            'Letterboxd) antes de crear cada ficha'),
        'obras': obras}, open(SALIDA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    con_disc = sum(1 for o in obras if o['director_web'])
    print(f'  {len(obras)} obras sin ficha en TMDB → {SALIDA}')
    print(f'  con año y director de Instagram: {sum(1 for o in obras if o["director"])}')
    print(f'  con el director en disputa entre su IG y su web: {con_disc}')
