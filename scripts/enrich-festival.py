#!/usr/bin/env python3
"""
Otrofestiv — TMDB + Letterboxd Enricher
Uso: python3 scripts/enrich-festival.py festivals/<id>.json
     python3 scripts/enrich-festival.py --selftest   # valida match_ok offline

Enriquece cada film en dos fases:

  Fase 1 — TMDB (requiere TMDB_API_KEY en el entorno):
    SOLO `genre` y `year` (campos verificables, no críticos si vacíos).
    El match exige los 4 criterios del PIPELINE (docs/PIPELINE.md, Fase 3):
    título sim>0.6 + año ±1 + apellido de director + país — y rechaza en miss.
    ❌ NUNCA escribe `synopsis`/`synopsis_en`/`poster`/`director`/`country`:
       esos van de la fuente oficial del festival con verificación humana
       (gate film-por-film). Ver docs/PIPELINE.md. Lección Brujo/Tribeca 2026:
       el match "primer resultado por título" asignaba sinopsis/póster de OTRA
       película. El gate de 4 criterios + corroboración ≥2 lo previene.

  Fase 2 — Letterboxd (sin API key, vía letterboxd.com/tmdb/{id}/):
    lbSlug → slug canónico (solo para matches que pasaron el gate de Fase 1).

Comportamiento:
  - No sobreescribe campos con valor.
  - Enriquece también los items de film_list (cortos y programas combinados).
  - Films con type:'event' se saltan siempre.
  - lbSlug no resuelto queda AUSENTE del JSON (la UI oculta el link); los
    pendientes se listan solo en el log del run.
  - Los rechazos de TMDB se loguean al final para revisión manual.

Requiere: pip install requests
"""
import json, time, re, sys, os, difflib, unicodedata

# `requests` solo se necesita para la red (Fase 1/2). El gate match_ok y el
# --selftest son puros → import lazy para correrlos sin la dependencia instalada.
try:
    import requests
except ImportError:
    requests = None

# ── TMDB ──────────────────────────────────────────────────────────────────────
TMDB_KEY  = os.environ.get('TMDB_API_KEY', '')
TMDB_BASE = 'https://api.themoviedb.org/3'

def require_runtime():
    if requests is None:
        print('⚠️  Falta la dependencia `requests`: pip install requests')
        sys.exit(1)
    if not TMDB_KEY:
        print('⚠️  TMDB_API_KEY no definida. Exportala antes de correr:')
        print('   export TMDB_API_KEY=tu_key_de_tmdb')
        print('   Obtené una en: https://www.themoviedb.org/settings/api')
        sys.exit(1)

LB_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'en-US,en;q=0.9',
}

GENRE_ES = {
    'Drama': 'Drama', 'Comedy': 'Comedia', 'Thriller': 'Thriller', 'Horror': 'Terror',
    'Action': 'Acción', 'Romance': 'Romance', 'Documentary': 'Documental',
    'Animation': 'Animación', 'Science Fiction': 'Ciencia Ficción', 'Fantasy': 'Fantasía',
    'Mystery': 'Misterio', 'Crime': 'Crimen', 'History': 'Historia', 'Adventure': 'Aventura',
    'Family': 'Familia', 'Music': 'Música', 'War': 'Guerra', 'Western': 'Western', 'TV Movie': 'TV',
}

# ── Normalización + similitud (puro, sin red) ───────────────────────────────────
def _norm(s):
    s = unicodedata.normalize('NFKD', (s or '')).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()

def title_sim(a, b):
    a, b = _norm(a), _norm(b)
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()

def _surnames(name):
    """Apellido (último token) de cada director en un campo multi-director."""
    out = set()
    for part in re.split(r'[,/&]| y | and ', name or ''):
        toks = _norm(part).split()
        if toks:
            out.add(toks[-1])
    return out

# País ES→EN — nuestro JSON guarda países en ESPAÑOL; TMDB (en-US) responde en
# inglés. Sin esta normalización, 'España' vs 'Spain' NUNCA matcheaba y el gate
# rechazaba matches perfectos (falso rechazo masivo cazado en Tercer Tiempo 2026:
# Polígono X, El Rey Puma, Mounir, El juego de su vida — título 1.00 + director
# exacto, rechazados por "país no coincide"). Claves ya normalizadas vía _norm.
CTY_ES2EN = {
    'espana': 'spain', 'italia': 'italy', 'brasil': 'brazil',
    'estados unidos': 'united states', 'francia': 'france', 'alemania': 'germany',
    'reino unido': 'united kingdom', 'japon': 'japan', 'corea del sur': 'south korea',
    'marruecos': 'morocco', 'sudafrica': 'south africa', 'suiza': 'switzerland',
    'belgica': 'belgium', 'paises bajos': 'netherlands', 'holanda': 'netherlands',
    'suecia': 'sweden', 'noruega': 'norway', 'dinamarca': 'denmark',
    'finlandia': 'finland', 'grecia': 'greece', 'turquia': 'turkey',
    'polonia': 'poland', 'rusia': 'russia', 'ucrania': 'ukraine',
    'irlanda': 'ireland', 'hungria': 'hungary', 'republica checa': 'czech republic',
    'nueva zelanda': 'new zealand', 'egipto': 'egypt', 'iran': 'iran',
    'irak': 'iraq', 'libano': 'lebanon', 'arabia saudita': 'saudi arabia',
    'catar': 'qatar', 'kenia': 'kenya', 'etiopia': 'ethiopia',
    'argelia': 'algeria', 'tunez': 'tunisia',
}

def _countries(s):
    out = set()
    for c in (_norm(x) for x in re.split(r'[,/&]', s or '')):
        if c:
            out.add(CTY_ES2EN.get(c, c))
    return out

def _country_match(fc, cc):
    """Match laxo por substring (United States ⊂ United States of America)."""
    return any(a in b or b in a for a in fc for b in cc)

# ── Gate de match — 4 criterios del PIPELINE (PURO, testeable offline) ───────────
def match_ok(film, det):
    """
    film: objeto del JSON (title, title_en, year, director, country).
    det : detalle TMDB normalizado (title, original_title, release_date,
          directors[list], countries[list]).
    Devuelve (bool, reason). Regla:
      - Título sim>0.6 OBLIGATORIO.
      - Cualquier criterio EVALUABLE (ambos lados con dato) que NO pase → rechazo.
      - Corroboración mínima: ≥2 de {año, director, país} evaluables y aprobados.
        (El título solo NUNCA alcanza — esto es lo que cazó a Brujo.)
    """
    ftitles = [film.get('title', ''), film.get('title_en', '')]
    ctitles = [det.get('title', ''), det.get('original_title', '')]
    sims = [title_sim(a, b) for a in ftitles if a for b in ctitles if b]
    tsim = max(sims) if sims else 0.0
    if tsim <= 0.6:
        return (False, f'título sim {tsim:.2f}≤0.6')

    # Director PRIMERO (el año ±2 depende de él). Apellidos por INTERSECCIÓN DE
    # TOKENS de los nombres completos, no solo el último token: 'Diego Guareño'
    # vs 'Diego Guareño Genesta' comparaba guareno↔genesta y rechazaba a la
    # misma persona (apellido compuesto — falso rechazo cazado en TT 2026).
    # Sigue exigiendo que un APELLIDO exacto de un lado aparezca como token del otro.
    fdir = _surnames(film.get('director', ''))
    cdir = {s for n in det.get('directors', []) for s in _surnames(n)}
    ftoks = {t for part in re.split(r'[,/&]| y | and ', film.get('director', '') or '') for t in _norm(part).split()}
    ctoks = {t for n in det.get('directors', []) for t in _norm(n).split()}
    dir_ev = bool(fdir and cdir)
    dir_ok = dir_ev and bool((fdir & ctoks) or (cdir & ftoks))

    # Año: ±1 normal; hasta ±2 SOLO si el director corrobora (año de festival vs
    # año de estreno TMDB difieren con frecuencia en cine de festival — caso
    # 'La herencia de Chico': mismo director exacto, TMDB 2023 vs festival 2025).
    fy = str(film.get('year') or '')[:4]
    cy = (det.get('release_date') or '')[:4]
    year_ev = fy.isdigit() and cy.isdigit()
    ydiff = abs(int(fy) - int(cy)) if year_ev else 99
    year_ok = year_ev and (ydiff <= 1 or (ydiff <= 2 and dir_ok))

    fc = _countries(film.get('country', ''))
    cc = {_norm(c) for c in det.get('countries', []) if _norm(c)}
    co_ev = bool(fc and cc)
    co_ok = co_ev and _country_match(fc, cc)

    for nm, ev, ok in (('año', year_ev, year_ok), ('director', dir_ev, dir_ok), ('país', co_ev, co_ok)):
        if ev and not ok:
            return (False, f'{nm} no coincide (título {tsim:.2f})')

    corrob = sum(1 for ev, ok in ((year_ev, year_ok), (dir_ev, dir_ok), (co_ev, co_ok)) if ev and ok)
    if corrob < 2:
        # Registro TMDB escaso (cine nicho: sin fecha ni país cargados). El caso
        # Brujo era TÍTULO SOLO; director aprobado + título casi exacto es una
        # señal de otra clase — se acepta con 1 corroborante SOLO en ese combo.
        if dir_ok and tsim >= 0.9:
            return (True, f'ok (título {tsim:.2f}, director corrobora, registro TMDB escaso)')
        return (False, f'solo {corrob} criterio(s) corroborante(s) <2 (título {tsim:.2f})')
    return (True, f'ok (título {tsim:.2f}, {corrob} corrob.)')

# ── TMDB functions ─────────────────────────────────────────────────────────────
def _search(media, query):
    params = {'api_key': TMDB_KEY, 'query': query, 'language': 'en-US'}
    r = requests.get(f'{TMDB_BASE}/search/{media}', params=params, timeout=8)
    return r.json().get('results', [])

def _query_variants(title):
    """Variantes de búsqueda para títulos que la query literal no encuentra:
    comillas tipográficas/rectas fuera, y versión sin subtítulo (tras : . —)
    cuando el tramo principal es sustancial. Caso TT 2026: 'Cantos al juego de
    "Bolar"' y 'El equipo del pueblo. Un sueño, Atlante' → 0 candidatos literales."""
    out = [title]
    stripped = re.sub(r'[\"“”‘’\']', '', title).strip()
    if stripped and stripped != title:
        out.append(stripped)
    m = re.split(r'\s*[:.—–]\s+', stripped or title, maxsplit=1)
    if len(m) == 2 and len(_norm(m[0])) >= 8:
        out.append(m[0])
    return out

def candidates_for(film, max_each=3):
    """Hasta `max_each` resultados por (media × query). Título original primero,
    luego EN, luego variantes sin comillas/subtítulo (solo si lo literal dio 0)."""
    titles = []
    for k in ('title', 'title_en'):
        v = film.get(k)
        if v and v not in titles:
            titles.append(v)
    seen, out = set(), []
    def _run(queries):
        for media in ('movie', 'tv'):
            for q in queries:
                try:
                    results = _search(media, q)
                except Exception:
                    results = []
                for res in results[:max_each]:
                    key = (media, res.get('id'))
                    if key not in seen:
                        seen.add(key)
                        out.append((media, res))
    _run(titles)
    if not out:
        variants = [v for t in titles for v in _query_variants(t) if v not in titles]
        if variants:
            _run(variants)
    return out

def fetch_details(media, cid):
    """Detalle TMDB normalizado a un shape común (en-US para que país/título matcheen)."""
    params = {'api_key': TMDB_KEY, 'language': 'en-US', 'append_to_response': 'credits'}
    d = requests.get(f'{TMDB_BASE}/{media}/{cid}', params=params, timeout=8).json()
    if media == 'tv':
        directors = [p['name'] for p in d.get('created_by', [])] + \
                    [p['name'] for p in d.get('credits', {}).get('crew', []) if p.get('job') in ('Director', 'Series Director')]
        countries = [c.get('name', '') for c in d.get('production_countries', [])] + d.get('origin_country', [])
        return dict(title=d.get('name', ''), original_title=d.get('original_name', ''),
                    release_date=d.get('first_air_date', ''), genres=d.get('genres', []),
                    directors=directors, countries=countries)
    directors = [p['name'] for p in d.get('credits', {}).get('crew', []) if p.get('job') == 'Director']
    countries = [c.get('name', '') for c in d.get('production_countries', [])]
    return dict(title=d.get('title', ''), original_title=d.get('original_title', ''),
                release_date=d.get('release_date', ''), genres=d.get('genres', []),
                directors=directors, countries=countries)

def get_genres(genres):
    return ', '.join(GENRE_ES.get(g.get('name', ''), g.get('name', '')) for g in genres[:2])

# ── Letterboxd slug resolution ─────────────────────────────────────────────────
def get_lb_slug(tmdb_id):
    """Resuelve el slug de Letterboxd desde el TMDB ID (og:url / canonical)."""
    if not tmdb_id:
        return None
    url = f'https://letterboxd.com/tmdb/{tmdb_id}/'
    try:
        r = requests.get(url, headers=LB_HEADERS, timeout=10, allow_redirects=True)
        if r.status_code != 200:
            return None
        m = re.search(r'<meta\s+property="og:url"\s+content="https://letterboxd\.com/film/([^/"]+)/"', r.text)
        if m:
            return m.group(1)
        m = re.search(r'<link\s+rel="canonical"\s+href="https://letterboxd\.com/film/([^/"]+)/"', r.text)
        if m:
            return m.group(1)
        return None
    except Exception:
        return None

# ── Film enrichment ────────────────────────────────────────────────────────────
def enrich_film_obj(film):
    """
    Fase 1: TMDB con gate de 4 criterios.
    Devuelve dict {genre, year, _tmdb_id, _reason} del PRIMER candidato que pasa
    el gate, o {'_reason': ...} si ninguno pasa (sin _tmdb_id).
    SOLO genre/year — nunca synopsis/poster/director (van de fuente oficial).
    """
    last = 'sin candidatos'
    for media, res in candidates_for(film):
        try:
            det = fetch_details(media, res['id'])
        except Exception as e:
            last = f'error detalle ({e})'
            continue
        ok, reason = match_ok(film, det)
        if ok:
            return {
                'genre': get_genres(det.get('genres', [])),
                'year': (det.get('release_date') or '')[:4],
                '_tmdb_id': res['id'],
                '_reason': reason,
            }
        last = reason
    return {'_reason': last}

def apply_enrichment(film, data):
    """Aplica SOLO genre/year (campos aceptados de TMDB), sin sobreescribir."""
    changed = False
    for field in ('genre', 'year'):
        if not film.get(field) and data.get(field):
            film[field] = data[field]
            changed = True
    return changed

def resolve_lb(film, tmdb_id, stats):
    """Fase 2: Letterboxd. Actualiza film['lbSlug'] en el lugar SOLO si resuelve.
    Sin match NO se escribe marcador en el JSON (el "⚠️ LB PENDIENTE" viajó a
    prod en TT 2026 y habría producido hrefs rotos): el pendiente se reporta en
    el log final del run, y la UI simplemente no muestra el link."""
    if film.get('lbSlug') and film['lbSlug'] != '⚠️ LB PENDIENTE':
        return
    time.sleep(0.3)
    slug = get_lb_slug(tmdb_id)
    if slug:
        film['lbSlug'] = slug
        stats['lb'] += 1
        print(f'✓LB:{slug}', end=' ', flush=True)
    else:
        film.pop('lbSlug', None)  # limpia también marcadores heredados de runs viejos
        stats['lb_pending'] += 1
        stats.setdefault('lb_pending_titles', []).append(film.get('title', '?'))
        print('—LB', end=' ', flush=True)

def _needs_tmdb(obj):
    return not all([obj.get('genre'), obj.get('year')])

def _needs_lb(obj):
    return not obj.get('lbSlug') or obj.get('lbSlug') == '⚠️ LB PENDIENTE'

# ── Main ───────────────────────────────────────────────────────────────────────
def enrich_festival(path):
    require_runtime()
    with open(path, encoding='utf-8') as f:
        data = json.load(f)

    films = data['films']
    stats = {'tmdb': 0, 'lb': 0, 'lb_pending': 0, 'not_found': 0, 'skipped': 0, 'considered': 0}
    rejects = []

    def do_tmdb(obj, label):
        stats['considered'] += 1
        try:
            found = enrich_film_obj(obj)
        except Exception as e:
            stats['not_found'] += 1
            rejects.append((label, f'excepción ({e})'))
            print('✗TMDB', end=' ', flush=True)
            return obj.get('_last_tmdb_id')
        if found.get('_tmdb_id'):
            apply_enrichment(obj, found)
            stats['tmdb'] += 1
            print(f'✓TMDB:{found.get("year","—")}·{found.get("genre","—")[:18]}', end=' ', flush=True)
            return found['_tmdb_id']
        stats['not_found'] += 1
        rejects.append((label, found.get('_reason', 'sin match')))
        print('✗TMDB', end=' ', flush=True)
        return None

    for i, film in enumerate(films):
        if film.get('type') == 'event':
            stats['skipped'] += 1
            continue

        title = film.get('title', '')
        needs_tmdb = _needs_tmdb(film)
        needs_lb = _needs_lb(film)
        list_items = [it for it in film.get('film_list', []) if _needs_tmdb(it) or _needs_lb(it)]

        if not needs_tmdb and not needs_lb and not list_items:
            stats['skipped'] += 1
            continue

        print(f'[{i+1}/{len(films)}] {title[:48]}', end=' ', flush=True)
        tmdb_id = None

        if needs_tmdb:
            tmdb_id = do_tmdb(film, title)
        elif needs_lb:
            # Ya tiene genre/year pero falta LB: buscar el ID con el gate igual
            found = enrich_film_obj(film)
            tmdb_id = found.get('_tmdb_id')

        if needs_lb:
            resolve_lb(film, tmdb_id, stats)

        for item in film.get('film_list', []):
            if not (_needs_tmdb(item) or _needs_lb(item)):
                continue
            it_id = None
            if _needs_tmdb(item):
                it_id = do_tmdb(item, f'  {item.get("title","")} (en {title})')
            elif _needs_lb(item):
                found = enrich_film_obj(item)
                it_id = found.get('_tmdb_id')
            if _needs_lb(item):
                resolve_lb(item, it_id, stats)
            time.sleep(0.2)

        print()
        time.sleep(0.25)

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f'\n{"─"*55}')
    print(f'✓ TMDB: {stats["tmdb"]}  |  ✓ LB: {stats["lb"]}  |  ⚠️ LB pendiente: {stats["lb_pending"]}  |  ✗ Sin match: {stats["not_found"]}  |  — Saltados: {stats["skipped"]}')

    # Sanidad del match rate (docs/PIPELINE.md: >60% permisivo, <20% revisar búsqueda)
    if stats['considered']:
        rate = stats['tmdb'] / stats['considered']
        if rate > 0.6:
            print(f'⚠️  match rate {rate:.0%} (>60%) — el algoritmo puede estar permisivo, revisar.')
        elif rate < 0.2:
            print(f'⚠️  match rate {rate:.0%} (<20%) — revisar búsqueda o datos de entrada.')

    if rejects:
        print(f'\nRechazos TMDB — revisar manualmente (NO se asignó ningún dato):')
        for label, reason in rejects:
            print(f'  · {label}: {reason}')

    if stats.get('lb_pending_titles'):
        print(f'\nFilms sin slug LB (no se escribe marcador en el JSON — completar a mano si existen):')
        for t in stats['lb_pending_titles']:
            print(f'  · {t}')
    print(f'\nJSON guardado: {path}')

# ── Self-test offline (sin red, sin API key) ────────────────────────────────────
def selftest():
    cases = [
        # (nombre, film, det, esperado)
        ('Brujo — match equivocado (año+dir+país no coinciden)',
         {'title': 'Brujo', 'year': '2025', 'director': 'Juan Zuleta', 'country': 'Colombia'},
         {'title': 'Brujo', 'original_title': 'Brujo', 'release_date': '2008-01-01',
          'directors': ['Guillermo Gómez-Peña'], 'countries': ['Mexico']},
         False),
        ('Dante — match válido (año+dir+país coinciden)',
         {'title': 'Dante', 'year': '2026', 'director': 'Hugo Ruíz', 'country': 'Spain'},
         {'title': 'Dante', 'original_title': 'Dante', 'release_date': '2026-05-01',
          'directors': ['Hugo Ruíz'], 'countries': ['Spain']},
         True),
        ('Título-solo — sin corroboración (rechaza)',
         {'title': 'Unidentified', 'year': '', 'director': '', 'country': ''},
         {'title': 'Unidentified', 'original_title': 'Unidentified', 'release_date': '2021-01-01',
          'directors': ['Some One'], 'countries': ['United States of America']},
         False),
        ('Año ausente pero dir+país corroboran (acepta)',
         {'title': 'Pale Sun', 'director': 'Adrian Moyse Dullin', 'country': 'France'},
         {'title': 'Pale Sun', 'original_title': 'Soleil Pâle', 'release_date': '',
          'directors': ['Adrian Moyse Dullin'], 'countries': ['France']},
         True),
        ('País laxo: United States ⊂ United States of America (acepta)',
         {'title': 'Listen', 'year': '2026', 'director': 'Jane Doe', 'country': 'United States'},
         {'title': 'Listen', 'original_title': 'Listen', 'release_date': '2026-01-01',
          'directors': ['Jane Doe'], 'countries': ['United States of America']},
         True),
        # ── Fixtures REALES de Tercer Tiempo 2026 (auditoría 12 jul) ──────────
        ('TT/Polígono X — país ES vs EN: España↔Spain (acepta)',
         {'title': 'Polígono X', 'year': '2025', 'director': 'Néstor López', 'country': 'España'},
         {'title': 'Polígono X', 'original_title': 'Polígono X', 'release_date': '2025-11-28',
          'directors': ['Néstor López'], 'countries': ['Spain']},
         True),
        ('TT/El fin de los tiempos — apellido compuesto: Guareño↔Guareño Genesta (acepta)',
         {'title': 'El fin de los tiempos', 'year': '2025', 'director': 'Diego Guareño', 'country': 'México'},
         {'title': 'The End of Times', 'original_title': 'El Fin de los Tiempos', 'release_date': '2025-10-10',
          'directors': ['Diego Guareño Genesta'], 'countries': ['Mexico']},
         True),
        ('TT/Con un pie en la gloria — registro TMDB escaso, dir+título 1.0 (acepta)',
         {'title': 'Con un pie en la gloria', 'year': '2025', 'director': 'Eduardo Esparza', 'country': 'México'},
         {'title': 'Con un pie en la gloria', 'original_title': 'Con un pie en la gloria', 'release_date': '',
          'directors': ['José Eduardo Esparza'], 'countries': []},
         True),
        ('TT/La herencia de Chico — año festival vs estreno ±2 con dir exacto (acepta)',
         {'title': 'La herencia de Chico', 'year': '2025', 'director': 'Jefferson Rodrigues', 'country': 'Brasil'},
         {'title': 'A Herança de Chico', 'original_title': 'A Herança de Chico', 'release_date': '2023-05-01',
          'directors': ['Jefferson Rodrigues'], 'countries': []},
         True),
        ('TT/Pambelé — telenovela 2017 homónima, sin dir/país (rechaza)',
         {'title': 'Pambelé', 'year': '2024', 'director': 'Augusto Pinilla', 'country': 'España, Colombia'},
         {'title': 'Pambelé', 'original_title': 'Pambelé', 'release_date': '2017-07-10',
          'directors': [], 'countries': []},
         False),
        ('TT/Grand Slam — film homónimo 1978 de otro director (rechaza)',
         {'title': 'Grand slam', 'year': '2023', 'director': 'Galar Egüén', 'country': 'España'},
         {'title': 'Grand Slam', 'original_title': 'Grand Slam', 'release_date': '1978-03-17',
          'directors': ['John Hefin'], 'countries': ['United Kingdom']},
         False),
        ('TT/Al son que me toquen bailo — homónima colombiana 2019 de otro dir (rechaza)',
         {'title': 'Al son que me toquen bailo', 'year': '2024', 'director': 'Deyaneira González', 'country': 'Puerto Rico'},
         {'title': 'Al son que me toquen bailo', 'original_title': 'Al son que me toquen bailo', 'release_date': '2019-12-25',
          'directors': ['Juan Carlos Mazo'], 'countries': ['Colombia']},
         False),
        ('TT/El documental del 10 — mismo título, director distinto (rechaza)',
         {'title': 'El documental del 10', 'year': '2025', 'director': 'Damian Originario', 'country': 'Argentina'},
         {'title': 'El documental del 10', 'original_title': 'El documental del 10', 'release_date': '2024-10-08',
          'directors': ['Lucas Costa'], 'countries': []},
         False),
        ('Anti-Brujo sigue: título 1.0 solo, registro escaso SIN director nuestro (rechaza)',
         {'title': 'Unidentified', 'year': '', 'director': '', 'country': ''},
         {'title': 'Unidentified', 'original_title': 'Unidentified', 'release_date': '',
          'directors': ['Some One'], 'countries': []},
         False),
    ]
    ok = True
    for name, film, det, expected in cases:
        got, reason = match_ok(film, det)
        status = '✓' if got == expected else '✗ FALLO'
        if got != expected:
            ok = False
        print(f'  {status}  {name}\n        → {got} ({reason})')
    print('\n' + ('PASS — match_ok OK' if ok else 'FAIL — revisar match_ok'))
    sys.exit(0 if ok else 1)

if __name__ == '__main__':
    if len(sys.argv) >= 2 and sys.argv[1] == '--selftest':
        selftest()
    if len(sys.argv) < 2 or sys.argv[1] in ('-h', '--help'):
        print('Uso: python3 scripts/enrich-festival.py festivals/<id>.json')
        print('     python3 scripts/enrich-festival.py --selftest')
        sys.exit(0 if (len(sys.argv) >= 2 and sys.argv[1] in ('-h', '--help')) else 1)
    enrich_festival(sys.argv[1])
