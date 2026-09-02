# -*- coding: utf-8 -*-
"""Doble verificación antes de dar de alta en TMDB (regla de Juan, 2 ago 2026).
Por cada obra sin lbSlug, tres sondas independientes:
  A) TMDB search/movie por título (y variantes: sin subtítulo, título_orig)
  B) TMDB search/person por cada director → su filmografía como Director
  C) Letterboxd search por título (HTML) → ¿existe ficha con ese director?
Solo las que fallan LAS TRES son candidatas legítimas a alta nueva."""
import os, re, json, time, unicodedata, difflib, urllib.parse
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import requests

K = os.environ['TMDB_API_KEY']
UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126 Safari/537.36'}

# norm() vivía aquí copiada; idéntica a lib.norm (verificado 23 ago 2026).
from lib import norm

def sim(a, b): return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()
def toks(s): return set(norm(s).split()) - {'de','la','el','los','las','del','y','of','the','a'}

def tmdb(path, **params):
    params['api_key'] = K
    for _ in range(3):
        try:
            r = requests.get(f'https://api.themoviedb.org/3{path}', params=params, timeout=25)
            if r.status_code == 200: return r.json()
        except Exception: pass
        time.sleep(1)
    return {}

def directores(mid):
    cr = tmdb(f'/movie/{mid}/credits')
    return ' '.join(c['name'] for c in cr.get('crew', []) if c['job'] == 'Director')

def sonda_titulo(title, director, year):
    """A) búsqueda por título con variantes."""
    variantes = {title}
    if ':' in title: variantes.add(title.split(':')[0].strip())
    if '[' in title: variantes.add(re.sub(r'\[.*?\]', '', title).strip())
    if '(' in title: variantes.add(re.sub(r'\(.*?\)', '', title).strip())
    for q in variantes:
        for params in ({}, {'primary_release_year': year} if year else {}):
            if params is None: continue
            res = tmdb('/search/movie', query=q, **params).get('results', [])
            for m in res[:6]:
                if max(sim(q, m.get('title','')), sim(q, m.get('original_title',''))) < 0.55: continue
                d = directores(m['id'])
                if toks(d) & toks(director):
                    return {'id': m['id'], 'title': m['title'], 'orig': m.get('original_title'),
                            'year': (m.get('release_date') or '')[:4], 'dir': d, 'via': f'titulo:{q}'}
    return None

def sonda_persona(director):
    """B) filmografía de cada director."""
    for nombre in re.split(r'[,/&]| y ', director or ''):
        nombre = nombre.strip()
        if len(nombre) < 4: continue
        res = tmdb('/search/person', query=nombre).get('results', [])
        for p in res[:3]:
            if not (toks(p['name']) & toks(nombre)): continue
            cr = tmdb(f"/person/{p['id']}/movie_credits")
            films = [m for m in cr.get('crew', []) if m['job'] == 'Director']
            if films:
                return {'persona': p['name'], 'persona_id': p['id'],
                        'films': [(m['id'], m['title'], (m.get('release_date') or '')[:4]) for m in films]}
    return None

def sonda_lb(title, director):
    """C) buscador de Letterboxd."""
    try:
        q = urllib.parse.quote(title)
        r = requests.get(f'https://letterboxd.com/search/films/{q}/', headers=UA, timeout=25)
        if r.status_code != 200: return None
        h = r.text
        cands = re.findall(r'href="(/film/[a-z0-9-]+/)"[^>]*>([^<]{2,80})<', h)
        vistos = []
        for href, txt in cands[:8]:
            if sim(title, txt) >= 0.7: vistos.append((href, txt))
        return vistos or None
    except Exception:
        return None

# Entrada y salida por argumento: la versión anterior llevaba clavada la ruta
# del staging de QAFF y el scratchpad de la sesión que la escribió, así que la
# segunda vez que se usó había que editarla. Una herramienta reutilizable no se
# edita para reutilizarla.
#
# Y recorre TAMBIÉN las obras dentro de film_list: en un festival de cortos, casi
# todo lo que falta por dar de alta vive ahí dentro, no en las funciones de
# primer nivel. Mirando solo el primer nivel, este verificador habría dicho que
# no falta nada.
if len(sys.argv) < 2:
    sys.exit('uso: verificar-antes-de-alta.py <build.json> [salida.json]')
ENTRADA = sys.argv[1]
SALIDA = sys.argv[2] if len(sys.argv) > 2 else 'altas-verificacion.json'

d = json.load(open(ENTRADA, encoding='utf-8'))
uniq = {}
for f in d['films']:
    if f.get('type') == 'event':
        continue
    for o in ([f] if not f.get('film_list') else f['film_list']):
        if o.get('title') and o.get('director'):
            uniq.setdefault(o['title'], o)
pendientes = [(t, f) for t, f in uniq.items() if not f.get('lbSlug')]
print(f'verificando {len(pendientes)} obras sin lbSlug\n')

reporte = []
for t, f in sorted(pendientes):
    dirs = f.get('director', ''); year = f.get('year', '')
    a = sonda_titulo(t, dirs, year)
    b = sonda_persona(dirs) if not a else None
    c = sonda_lb(t, dirs) if not a else None
    estado = 'EXISTE' if a else ('REVISAR' if (b or c) else 'ALTA-OK')
    reporte.append({'title': t, 'title_en': f.get('title_en'), 'director': dirs,
                    'year': year, 'country': f.get('country', ''),
                    'duration': f.get('duration', ''), 'genre': f.get('genre'),
                    'poster': f.get('poster'), 'posterSource': f.get('posterSource'),
                    'synopsis': (f.get('synopsis') or '')[:400],
                    'estado': estado, 'tmdb': a, 'persona': b, 'lb': c})
    print(f"[{estado:8}] {t[:42]:43} {dirs[:26]:27} {year}")
    if a: print(f"           -> TMDB {a['id']} '{a['title']}' ({a['year']}) dir={a['dir']} via={a['via']}")
    if b: print(f"           -> persona TMDB '{b['persona']}' dirige: {b['films'][:4]}")
    if c: print(f"           -> LB posibles: {c[:3]}")

json.dump(reporte, open(SALIDA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
from collections import Counter
print('\nRESUMEN:', dict(Counter(r['estado'] for r in reporte)))
print('->', SALIDA)
