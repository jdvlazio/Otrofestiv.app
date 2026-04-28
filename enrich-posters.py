#!/usr/bin/env python3
"""
Otrofestiv — Enriquecedor de posters desde TMDB
================================================
Uso: python3 enrich-posters.py festivals/nombre-festival.json

Reutilizable para cualquier festival. Lee el JSON, busca posters en TMDB
y actualiza el campo "posters" con las URLs encontradas.

SISTEMA DE BÚSQUEDA (6 estrategias en cascada):
  1. title + year, es-MX
  2. title + year, en-US
  3. title_en + year, en-US
  4. title (sin año), es-MX
  5. title_en (sin año), en-US
  6. title_en + year, búsqueda en TV (para documentales)

CONFIANZA: verifica coincidencia de año ±2 y similitud de título
para evitar falsos positivos. Umbral mínimo de 15 puntos.

REGLAS:
  - Salta eventos (type='event') y programas de cortos (is_cortos=True)
  - No sobreescribe posters existentes (customPosters tienen prioridad)
  - Reporta cobertura final y lista los no encontrados con sugerencias

PARA FESTIVALES FUTUROS:
  Añadir title_en en el JSON mejora drásticamente el match.
  Películas en idiomas no latinos: title_en es OBLIGATORIO.
"""

import json, sys, time, urllib.request, urllib.parse, re

TMDB_KEY = '38f24e78b2f13970af3430eb0732f0ac'
TMDB_BASE = 'https://api.themoviedb.org/3'
TMDB_IMG  = 'https://image.tmdb.org/t/p/w342'
DELAY     = 0.25

def normalize(s):
    return re.sub(r'[^a-z0-9]', '', str(s).lower())

def year_close(found, target, tol=2):
    if not target or not found:
        return True
    try:
        return abs(int(found) - int(target)) <= tol
    except:
        return True

def confidence(result, title, year):
    score = 0
    ft = result.get('title') or result.get('name', '')
    fy = (result.get('release_date') or result.get('first_air_date') or '')[:4]
    if normalize(ft) == normalize(title):    score += 40
    elif normalize(title) in normalize(ft) or normalize(ft) in normalize(title): score += 20
    if year and fy == str(year):             score += 30
    elif year_close(fy, year, 2):            score += 10
    if result.get('poster_path'):            score += 10
    if result.get('popularity', 0) > 5:     score += 5
    return score

def tmdb_search(query, year=None, lang='es-MX', media='movie'):
    q = urllib.parse.quote(query)
    url = f'{TMDB_BASE}/search/{media}?api_key={TMDB_KEY}&query={q}&language={lang}'
    if year:
        url += f'&year={year}' if media == 'movie' else f'&first_air_date_year={year}'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Otrofestiv/1.0'})
        return json.loads(urllib.request.urlopen(req, timeout=8).read()).get('results', [])
    except:
        return []

def get_poster(title, title_en=None, year=None):
    candidates = []
    strategies = [
        (title,    year, 'es-MX', 'movie'),
        (title,    year, 'en-US', 'movie'),
        (title,    None, 'es-MX', 'movie'),
    ]
    if title_en and normalize(title_en) != normalize(title):
        strategies += [
            (title_en, year, 'en-US', 'movie'),
            (title_en, None, 'en-US', 'movie'),
        ]
    strategies.append((title_en or title, year, 'en-US', 'tv'))

    for query, yr, lang, media in strategies:
        results = tmdb_search(query, yr, lang, media)
        time.sleep(DELAY)
        for r in results:
            if not r.get('poster_path'): continue
            candidates.append((confidence(r, query, year), r, media))
        if candidates and max(c[0] for c in candidates) >= 70:
            break

    if not candidates: return None, None, None
    best_score, best, _ = max(candidates, key=lambda x: x[0])
    if best_score < 15:  return None, None, None

    ft = best.get('title') or best.get('name', '')
    fy = (best.get('release_date') or best.get('first_air_date') or '')[:4]
    return TMDB_IMG + best['poster_path'], ft, fy

def main(filepath):
    print(f"\n{'═'*52}")
    print(f"  Otrofestiv — Enriquecedor de posters TMDB")
    print(f"{'═'*52}")

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    films   = data.get('films', [])
    posters = data.get('posters', {})
    custom  = data.get('customPosters', {})

    seen, unique = set(), []
    for f in films:
        if f.get('is_cortos') or f.get('type') == 'event' or f.get('is_programa'): continue
        if f['title'] not in seen:
            seen.add(f['title']); unique.append(f)

    already = sum(1 for f in unique if f['title'] in posters or f['title'] in custom)
    print(f"\n  Festival : {data.get('config',{}).get('name', filepath)}")
    print(f"  Películas: {len(unique)} únicas | {already} con poster | {len(unique)-already} a buscar")
    print(f"{'─'*52}\n")

    updated, not_found = 0, []
    for film in unique:
        title, title_en, year = film.get('title',''), film.get('title_en') or '', film.get('year')
        if title in custom or title in posters: continue
        url, ft, fy = get_poster(title, title_en, year)
        if url:
            posters[title] = url; updated += 1
            note = f" → '{ft}' {fy}" if ft and normalize(ft) != normalize(title) else (f" ({fy})" if fy and str(fy) != str(year or '') else '')
            print(f"  ✓  {title[:46]}{note}")
        else:
            not_found.append(film); print(f"  ✗  {title[:46]}")

    data['posters'] = posters
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    total   = len(unique)
    covered = sum(1 for f in unique if f['title'] in posters or f['title'] in custom)
    print(f"\n{'─'*52}")
    print(f"  Nuevos    : {updated}")
    print(f"  Cobertura : {covered}/{total} ({100*covered//total if total else 0}%)")
    print(f"  Archivo   : {filepath}")
    if not_found:
        print(f"\n  Sin poster — añadir manualmente o mejorar title_en:")
        for f in not_found:
            en = f' (en: {f["title_en"]})' if f.get('title_en') and f['title_en'] != f['title'] else ''
            print(f"    · {f['title'][:50]}{en}")
    print(f"\n{'═'*52}\n")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python3 enrich-posters.py festivals/nombre-festival.json")
        sys.exit(1)
    main(sys.argv[1])
