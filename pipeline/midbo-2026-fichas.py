#!/usr/bin/env python3
"""midbo-2026-fichas.py --bajar — baja la ficha de cada obra de midbo.co.

La programación de MIDBO vive en la ficha de cada obra (`/peliculas/<slug>/`),
no en una grilla. Este comando lee la lista de obras que bajó la API
(fuentes/midbo-2026/pelicula.json, fuente viva anterior en el plan) y baja
cada ficha a fuentes/midbo-2026/fichas/<slug>.html. Si UNA falla o no parece
la ficha, no se reemplaza ninguna: o se bajan todas o quedan las anteriores.
Deja fichas/_indice.json (slug → sha12) como el archivo que registra la bajada.
"""
import hashlib, json, os, sys, tempfile, urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = f'{REPO}/fuentes/midbo-2026'
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'


def _get(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read(), r.headers.get('Content-Type') or ''


def main():
    if '--bajar' not in sys.argv:
        sys.exit(__doc__)
    obras = json.load(open(f'{DIR}/pelicula.json', encoding='utf-8'))
    bajadas, malas = {}, []
    for o in obras:
        try:
            cuerpo, ct = _get(o['link'])
        except Exception as e:
            malas.append(f'{o["slug"]}: {e}'); continue
        # no toda ficha trae «Funciones» (hay obras sin función aún): se exige la
        # página de ESA obra, con su slug, no un 200 cualquiera
        if 'html' not in ct or len(cuerpo) < 5000 or f'/peliculas/{o["slug"]}/'.encode() not in cuerpo:
            malas.append(f'{o["slug"]}: no parece la ficha ({ct}, {len(cuerpo)} bytes)'); continue
        bajadas[o['slug']] = cuerpo
    if malas:
        sys.exit('✗ fichas: ' + '; '.join(malas[:5]) + (f' (+{len(malas)-5})' if len(malas) > 5 else ''))
    os.makedirs(f'{DIR}/fichas', exist_ok=True)
    for slug, cuerpo in bajadas.items():
        fd, tmp = tempfile.mkstemp(dir=f'{DIR}/fichas')
        with os.fdopen(fd, 'wb') as f:
            f.write(cuerpo)
        os.replace(tmp, f'{DIR}/fichas/{slug}.html')
    json.dump({s: hashlib.sha256(c).hexdigest()[:12] for s, c in sorted(bajadas.items())},
              open(f'{DIR}/fichas/_indice.json', 'w', encoding='utf-8'), indent=1)
    print(f'  {len(bajadas)} fichas')


if __name__ == '__main__':
    main()
