# -*- coding: utf-8 -*-
"""Título en inglés de cada obra, traído de TMDB y VERIFICADO.

`title_en` no es una traducción nuestra: es el título con que la obra se
distribuye en inglés. TMDB lo publica en `title` cuando se pide `language=en-US`
y también en `alternative_titles` con el país.

Dos candados, porque el campo es fácil de ensuciar:

  · Solo se acepta si el `tmdb_id` ya viene VERIFICADO del cruce anterior
    (director + año/duración). Nada se busca por título aquí.
  · Se descarta si TMDB devuelve el mismo título que ya tenemos: significa que
    no hay título inglés registrado y estaríamos duplicando el campo. Las obras
    que YA se llaman igual en inglés —«Toy Story», «Honeyland»— no necesitan
    `title_en` y no lo llevan.
"""
import json, os, subprocess, time, unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
OUT = f'{ST}/ficma-2026-title-en.json'
KEY = os.environ['TMDB_API_KEY']


def get(path, **params):
    url = f'https://api.themoviedb.org/3{path}?api_key={KEY}&' + '&'.join(
        f'{k}={v}' for k, v in params.items())
    for _ in range(3):
        r = subprocess.run(['curl', '-s', '--max-time', '25', url], capture_output=True)
        if r.returncode == 0 and r.stdout:
            try:
                return json.loads(r.stdout)
            except Exception:
                pass
        time.sleep(0.8)
    return {}


def igual(a, b):
    n = lambda s: ''.join(c for c in unicodedata.normalize('NFD', (s or '').lower())
                          if unicodedata.category(c) != 'Mn' and c.isalnum())
    return n(a) == n(b)


def main():
    tmdb = json.load(open(f'{ST}/ficma-2026-tmdb.json', encoding='utf-8'))['verificadas']
    out, saltadas = {}, []
    for i, (titulo, v) in enumerate(sorted(tmdb.items()), 1):
        en = get(f"/movie/{v['tmdb_id']}", language='en-US').get('title') or ''
        if not en or igual(en, titulo) or igual(en, v.get('titulo_original', '')):
            saltadas.append(titulo)
            print(f'[{i:2}/{len(tmdb)}] —   {titulo[:44]:46} (ya es su título en inglés)', flush=True)
        else:
            out[titulo] = en
            print(f'[{i:2}/{len(tmdb)}] EN  {titulo[:44]:46} → {en}', flush=True)
        time.sleep(0.15)

    json.dump({'_metodo': 'TMDB language=en-US sobre tmdb_id ya verificado; se descarta '
                          'cuando coincide con el título que ya tenemos (no hay título inglés '
                          'propio y el campo duplicaría)',
               'title_en': out, '_sin_titulo_en': sorted(saltadas)},
              open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'\n{len(tmdb)} obras con ficha · con título EN propio {len(out)} · sin él {len(saltadas)}')


if __name__ == '__main__':
    main()
