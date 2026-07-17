#!/usr/bin/env python3
# ── tmdb-gaps.py — reporte de huecos TMDB/Letterboxd de un festival ───────────
#
# Lista cada obra (film suelto o ítem de film_list) SIN lbSlug, con sus datos
# ya formateados para el formulario de https://www.themoviedb.org/movie/new.
# La doctrina: ninguna obra "con botón" y otra "sin botón" — la app aporta a la
# base de datos de la cinefilia (TMDB → Letterboxd) en vez de solo consumirla.
#
# La API de TMDB NO permite crear películas (limitación de plataforma, no de
# key): las fichas se crean en la web. Este reporte convierte el hueco en una
# checklist de copy/paste. Cerrado el alta, el slug se resuelve vía el redirect
# letterboxd.com/tmdb/<id> y se escribe como lbSlug en el JSON del festival.
#
# Uso:
#   python3 scripts/tmdb-gaps.py festivals/tercertiempo-2026.json
#   python3 scripts/tmdb-gaps.py festivals/tercertiempo-2026.json --day 2026-07-17
#   python3 scripts/tmdb-gaps.py --all          # los 2 festivales activos + próximos

import json, sys, glob

def _rows(films, day=None):
    for f in films:
        if day and f.get('day') != day:
            continue
        if f.get('is_cortos') and f.get('film_list'):
            for it in f['film_list']:
                yield f, it
        elif f.get('type') != 'event':
            yield f, f

def report(path, day=None):
    d = json.load(open(path, encoding='utf-8'))
    films = d.get('films', d if isinstance(d, list) else [])
    gaps, total = [], 0
    seen = set()
    for parent, it in _rows(films, day):
        key = it.get('title')
        if key in seen:
            continue
        seen.add(key)
        total += 1
        if not it.get('lbSlug'):
            gaps.append((parent, it))
    print(f"\n═══ {path}{' · ' + day if day else ''} — {len(gaps)} sin ficha de {total} obras ═══")
    for parent, it in gaps:
        ctx = f"  (en «{parent['title']}» · {parent.get('day','?')} {parent.get('time','')})" if parent is not it else f"  ({it.get('day','?')} {it.get('time','')})"
        print(f"\n✗ {it['title']}{ctx}")
        print(f"    Title:        {it.get('title_en') or it['title']}")
        if it.get('title_en') and it.get('title_en') != it['title']:
            print(f"    Translated:   {it['title']} (es)")
        print(f"    Director:     {it.get('director','—')}")
        print(f"    Year:         {it.get('year','—')}")
        print(f"    Runtime:      {it.get('duration','—')}")
        print(f"    Country:      {it.get('country','—')}")
        if it.get('genre'):
            print(f"    Genre:        {it['genre']}")
        if it.get('synopsis_en'):
            print(f"    Overview EN:  {it['synopsis_en']}")
        if it.get('synopsis'):
            print(f"    Overview ES:  {it['synopsis']}")
        if it.get('poster'):
            print(f"    Poster:       {it['poster']}")
    if not gaps:
        print("  ✓ todas las obras tienen ficha (lbSlug presente)")
    return len(gaps)

if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    day = None
    if '--day' in sys.argv:
        day = sys.argv[sys.argv.index('--day') + 1]
        args = [a for a in args if a != day]
    paths = sorted(glob.glob('festivals/*.json')) if '--all' in sys.argv else args
    if not paths:
        print(__doc__ or 'Uso: tmdb-gaps.py <festival.json> [--day YYYY-MM-DD] | --all')
        sys.exit(1)
    n = sum(report(p, day) for p in paths)
    sys.exit(0 if n == 0 else 2)
