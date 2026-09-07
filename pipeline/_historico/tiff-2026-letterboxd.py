# -*- coding: utf-8 -*-
"""Catálogo de TIFF 2026 desde la lista oficial del festival en Letterboxd.

Aquí el circuito va AL REVÉS que en FICMA. Allá partíamos de un `tmdb_id` ya
verificado y le pedíamos a Letterboxd su slug; acá partimos de la lista que
publica el propio festival (`letterboxd.com/tiff_net/list/…`) y es Letterboxd
quien nos entrega el `tmdb_id` en la ficha de cada obra.

El candado anti-homónimo se mantiene, y por el mismo motivo: el id no lo
inferimos de un título, lo declara Letterboxd en su propio mapeo. Nadie adivina.
La lección de FantasoFest —«Peephole» con cinco homónimos y ninguno el nuestro—
sigue cubierta: si una ficha no trae id, se queda sin id y se reporta.

DOS COSAS QUE ESTA FUENTE **NO** ES:
1. No es la programación. Dice qué obras vienen, no cuándo ni dónde.
2. No es la sección. La lista es plana; el programme (Special Presentations,
   TIFF Docs…) solo vive en la parrilla de tiff.net.

Y una advertencia de cobertura: una lista de Letterboxd rara vez incluye los
cortos. El conteo que salga de aquí es un PISO del catálogo, nunca el total.

El HTML crudo se cachea fuera del repo (`--cache`), por la lección de las 68 MB
de `fuentes/`: material de trabajo no se commitea.
"""
import argparse, json, os, re, subprocess, sys, time, html as H

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import provenance

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
LISTA = 'https://letterboxd.com/tiff_net/list/2026-toronto-international-film-festival'
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36')


def bajar(url, destino, forzar=False):
    """Descarga cacheada. Devuelve el HTML, o '' si la petición no fue 200."""
    if os.path.exists(destino) and not forzar and os.path.getsize(destino) > 2000:
        return open(destino, encoding='utf-8', errors='replace').read()
    r = subprocess.run(['curl', '-sL', '--max-time', '40', '-A', UA, '-w', '%{http_code}',
                        url, '-o', destino], capture_output=True)
    if r.stdout.decode().strip()[-3:] != '200':
        if os.path.exists(destino):
            os.remove(destino)
        return ''
    time.sleep(0.4)
    return open(destino, encoding='utf-8', errors='replace').read()


def leer_lista(cache):
    """Recorre las páginas hasta que una no aporte obras. Sin tope adivinado."""
    obras, pag = [], 1
    vistos = set()
    while True:
        s = bajar(f'{LISTA}/page/{pag}/', f'{cache}/lista-{pag}.html')
        # data-item-slug y data-item-full-display-name viajan en el mismo <li>.
        crudas = re.findall(r'data-item-name="([^"]+)"[^>]*?data-item-slug="([^"]+)"', s)
        nuevas = [(H.unescape(n), sl) for n, sl in crudas if sl not in vistos]
        if not nuevas:
            break
        for nombre, slug in nuevas:
            vistos.add(slug)
            # El nombre trae el año entre paréntesis solo cuando Letterboxd
            # necesita desambiguar. Ausente ≠ sin año: el año real está en la ficha.
            m = re.match(r'^(.*?)\s*\((\d{4})\)$', nombre)
            obras.append({'titulo_lb': m.group(1) if m else nombre,
                          'anio_lista': int(m.group(2)) if m else None, 'lbSlug': slug})
        print(f'   lista pág. {pag}: {len(nuevas)} obras', flush=True)
        pag += 1
    return obras


def leer_ficha(slug, cache):
    s = bajar(f'https://letterboxd.com/film/{slug}/', f'{cache}/f-{slug}.html')
    if not s:
        return {'_error': 'ficha no descargable'}
    d = {}
    m = re.search(r'themoviedb\.org/(movie|tv)/(\d+)', s)
    if m:
        d['tmdb_tipo'], d['tmdb_id'] = m.group(1), int(m.group(2))
    m = re.search(r'<meta property="og:title" content="([^"]+)"', s)
    if m:
        t = H.unescape(m.group(1))
        ma = re.match(r'^(.*?)\s*\((\d{4})\)$', t)
        d['titulo'], d['anio'] = (ma.group(1), int(ma.group(2))) if ma else (t, None)
    # Los directores viven en el JSON-LD; puede haber más de uno (codirección).
    ld = re.search(r'"director":\s*\[(.*?)\]', s, re.S)
    if ld:
        d['directores'] = [H.unescape(x) for x in re.findall(r'"name":"([^"]+)"', ld.group(1))]
    m = re.search(r'(\d+)&nbsp;mins', s) or re.search(r'(\d+)\s*mins', s)
    if m:
        d['duracion'] = int(m.group(1))
    m = re.search(r'<meta name="description" content="([^"]*)"', s)
    if m:
        d['sinopsis_en'] = H.unescape(m.group(1)).strip()
    return d


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cache', required=True, help='directorio de HTML crudo, FUERA del repo')
    a = ap.parse_args()
    os.makedirs(a.cache, exist_ok=True)

    obras = leer_lista(a.cache)
    if not obras:
        sys.exit('La lista no devolvió obras. Letterboxd cambió el HTML o bloqueó.')
    print(f'── {len(obras)} obras en la lista oficial\n')

    sin_id, sin_dir = [], []
    for i, o in enumerate(obras, 1):
        o.update(leer_ficha(o['lbSlug'], a.cache))
        if not o.get('tmdb_id'):
            sin_id.append(o['titulo_lb'])
        if not o.get('directores'):
            sin_dir.append(o['titulo_lb'])
        marca = 'OK ' if o.get('tmdb_id') else '—  '
        print(f'[{i:3}/{len(obras)}] {marca}{o["titulo_lb"][:44]:46} '
              f'{o.get("tmdb_id","(sin id)")}', flush=True)

    os.makedirs(ST, exist_ok=True)
    salida = f'{ST}/tiff-2026-letterboxd.json'
    json.dump({'_provenance': provenance(LISTA, metodo='lista oficial del festival en Letterboxd'),
               '_metodo': 'Lista oficial del festival en Letterboxd. El tmdb_id lo declara '
                          'Letterboxd en cada ficha; nunca se infiere de un título. '
                          'NO contiene programación ni secciones, y probablemente omite '
                          'los cortos: este conteo es un piso del catálogo.',
               '_obras': len(obras), 'obras': obras},
              open(salida, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    print(f'\n── {salida}')
    print(f'   con tmdb_id: {len(obras)-len(sin_id)}/{len(obras)}')
    if sin_id:
        print(f'   SIN id ({len(sin_id)}): ' + ', '.join(sin_id[:8]))
    if sin_dir:
        print(f'   sin director ({len(sin_dir)}): ' + ', '.join(sin_dir[:8]))


if __name__ == '__main__':
    main()
