# -*- coding: utf-8 -*-
"""Segunda pasada de afiches para Cinemancia 2026: SOLO el póster, nada más.

Las 33 obras con afiche se buscaron ANTES de arreglar los emparejamientos del
catálogo. En esa tanda quedaron fuera obras que aparecieron después —«Caminito
al Cielo» y «Vampir Cuadecuc», que estaban perdidas en celdas truncadas del
PDF— y otras que simplemente no se resolvieron.

Este script NO re-enriquece. Toca un único campo, `poster_tmdb`, y solo en las
obras que hoy no tienen afiche y sí tienen tmdbId guardado. Todo lo demás
—duración, sinopsis, director, país— se queda como está: la duración acaba de
costar un arreglo de fondo (el catálogo la tomaba del contenedor) y un
re-enriquecido a ciegas la volvería a pisar.
"""
import json, os, subprocess, sys, time, urllib.parse

S = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'festivals', 'staging')
S = os.path.normpath(S)
REPO = os.path.normpath(os.path.join(S, '..', '..'))
KEY = os.environ.get('TMDB_API_KEY')


def tmdb(path, **params):
    """Se consulta con curl y no con urllib: el Python de este entorno no tiene
    el bundle de certificados y toda llamada muere en CERTIFICATE_VERIFY_FAILED.
    Es la misma razón por la que la geocodificación se hizo con curl."""
    params['api_key'] = KEY
    url = f'https://api.themoviedb.org/3{path}?' + urllib.parse.urlencode(params)
    r = subprocess.run(['curl', '-s', '--max-time', '25', url],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f'curl salió {r.returncode}')
    return json.loads(r.stdout)


def main():
    if not KEY:
        sys.exit('✗ falta TMDB_API_KEY en el entorno')

    pub = json.load(open(f'{REPO}/festivals/cinemancia-2026.json', encoding='utf-8'))
    # Universo de OBRAS: las que viven dentro de un programa y las funciones
    # simples. Un contenedor sin contenido NO es una obra — lleva el póster
    # editorial nuestro, no uno de TMDB.
    sin_afiche = set()
    for f in pub['films']:
        hijos = f.get('film_list') or []
        if hijos:
            for o in hijos:
                if not o.get('poster'):
                    sin_afiche.add(o['title'])
        elif f.get('type') != 'event' and not f.get('poster'):
            sin_afiche.add(f['title'])

    side = json.load(open(f'{S}/cinemancia-2026-tmdb.json', encoding='utf-8'))
    obras = side['obras']

    pend = [o for o in obras
            if o.get('title') in sin_afiche
            and not o.get('poster_tmdb')
            and (o.get('tmdbId') or o.get('tmdb_id'))]

    print(f'obras sin afiche: {len(sin_afiche)} · con tmdbId para consultar: {len(pend)}')
    hallados = 0
    for o in pend:
        tid = o.get('tmdbId') or o.get('tmdb_id')
        try:
            det = tmdb(f'/movie/{tid}')
        except Exception as e:
            print(f'  ✗ {o["title"][:44]:46} {e}')
            time.sleep(0.3)
            continue
        p = det.get('poster_path') or ''
        if p:
            o['poster_tmdb'] = p
            hallados += 1
            print(f'  ✓ {o["title"][:44]:46} {p}')
        else:
            print(f'  · {o["title"][:44]:46} TMDB no tiene afiche para esta ficha')
        time.sleep(0.3)

    if hallados:
        json.dump(side, open(f'{S}/cinemancia-2026-tmdb.json', 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
    print(f'\nafiches nuevos: {hallados} de {len(pend)} consultados')


if __name__ == '__main__':
    main()
