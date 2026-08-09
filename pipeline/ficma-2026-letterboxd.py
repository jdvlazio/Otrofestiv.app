# -*- coding: utf-8 -*-
"""`lbSlug` de cada obra, resuelto por el mapeo TMDB→Letterboxd. Sin adivinar.

Letterboxd bloquea el scraping de búsqueda (403), y por eso hasta ahora los
slugs se buscaban a mano. Pero publica un atajo, `letterboxd.com/tmdb/<id>/`,
que redirige (302) a la ficha del film que ELLOS tienen mapeado a ese id de
TMDB. Eso cambia la naturaleza del dato: el slug deja de ser una inferencia
nuestra sobre el título y pasa a ser la respuesta de Letterboxd.

El candado sigue siendo el mismo de siempre: solo se consultan `tmdb_id` que ya
pasaron la verificación (director + año/duración). Si el id es el correcto, el
slug también lo es; si nunca hubo id verificado, aquí no se inventa uno.

Un 404 significa que Letterboxd no tiene ese film mapeado, y eso es un estado
honesto: la ficha se queda sin botón. Nunca se cuelga un homónimo — la lección
de FantasoFest, donde «Peephole» tenía cinco homónimos y ninguno era el nuestro.
"""
import json, os, re, subprocess, time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
OUT = f'{ST}/ficma-2026-letterboxd.json'
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')


def resolver(tmdb_id):
    """→ (slug, código http). Solo mira la redirección, no descarga la ficha."""
    r = subprocess.run(
        ['curl', '-s', '-o', '/dev/null', '-w', '%{http_code} %{redirect_url}',
         '--max-time', '25', '-A', UA, f'https://letterboxd.com/tmdb/{tmdb_id}/'],
        capture_output=True)
    partes = r.stdout.decode().split()
    codigo = partes[0] if partes else '000'
    url = partes[1] if len(partes) > 1 else ''
    m = re.match(r'https://letterboxd\.com/film/([^/]+)/?$', url)
    return (m.group(1) if m else ''), codigo


def main():
    tmdb = json.load(open(f'{ST}/ficma-2026-tmdb.json', encoding='utf-8'))['verificadas']
    extra = {'Punto de Fuga': 1525164}      # id verificado a mano contra el afiche
    ids = {t: v['tmdb_id'] for t, v in tmdb.items()} | extra

    out, sin = {}, []
    for i, (titulo, tid) in enumerate(sorted(ids.items()), 1):
        slug, codigo = resolver(tid)
        if slug:
            out[titulo] = slug
            print(f'[{i:2}/{len(ids)}] OK  {titulo[:42]:44} → {slug}', flush=True)
        else:
            sin.append({'titulo': titulo, 'tmdb_id': tid, 'http': codigo})
            print(f'[{i:2}/{len(ids)}] —   {titulo[:42]:44} (http {codigo}: no mapeado)', flush=True)
        time.sleep(0.4)

    json.dump({'_metodo': 'letterboxd.com/tmdb/<id> → 302 a la ficha. El slug lo da '
                          'Letterboxd desde su propio mapeo; nosotros solo aportamos un '
                          'tmdb_id ya verificado (director + año/duración). Sin match '
                          '→ sin lbSlug, nunca un homónimo.',
               'lbSlug': out, 'sin_mapeo': sin},
              open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'\n{len(ids)} obras con ficha TMDB · con slug {len(out)} · sin mapeo {len(sin)}')


if __name__ == '__main__':
    main()
