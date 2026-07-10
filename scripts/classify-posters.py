#!/usr/bin/env python3
# ── classify-posters.py — clasifica posters por ASPECTO REAL (F: estrategia editorial)
#
# Descarga cada poster, mide su aspecto y escribe `posterSource` en el film:
#   landscape (≥1.2) → 'editorial'   (marco editorial-con-imagen)
#   portrait          → 'tmdb'|'custom'
# Caza rotos (403/404) al montar, no en producción. Reemplaza la detección
# frágil por-host: el runtime ya honra posterSource primero (POSTERS.md §5).
#
# Uso:
#   python3 scripts/classify-posters.py <id|all> [--apply]
#   (sin --apply = DRY-RUN: reporta qué cambiaría, NO escribe)

import json, glob, os, re, sys, ssl, io, urllib.request
from urllib.parse import urlparse
from PIL import Image

ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
PROD = "https://otrofestiv.app"
TMDB_HOSTS = ("image.tmdb.org",)

def norm_key(s): return re.sub(r"[‘’‚‛′ʼ]", "'", s or "")

# Objetos "film-ish": film de nivel superior, corto dentro de film_list, programa.
# Amplio (antes solo time/day) para que el map matchee cortos anidados también.
_FILMISH = ('time', 'day', 'duration', 'director', 'poster', 'type',
            'film_list', 'is_cortos', 'is_programa', 'screenings')
def films_of(d):
    out = []
    def w(x):
        if isinstance(x, dict):
            if x.get('title') and any(k in x for k in _FILMISH): out.append(x)
            for v in x.values(): w(v)
        elif isinstance(x, list):
            for v in x: w(v)
    w(d); return out

def resolve_url(p):
    if not p: return None
    if p.startswith('http'): return p
    if p.startswith('/assets/'):
        # Local primero (onboarding: el asset existe en el repo antes del deploy —
        # medir contra PROD daba ROTO 404; hallazgo del test pipeline v2).
        local = p.lstrip('/')
        if os.path.exists(local): return 'file://' + os.path.abspath(local)
        return PROD + p
    # path TMDB (/xxx.jpg) → no hace falta medir, es portrait por construcción
    return None

def is_tmdb(p):
    if not p: return False
    if p.startswith('http'): return urlparse(p).netloc in TMDB_HOSTS
    return bool(re.match(r'^/[A-Za-z0-9]+\.(jpg|png|jpeg)$', p))  # path TMDB

_cache = {}
def measure(url):
    if url in _cache: return _cache[url]
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        data = urllib.request.urlopen(req, timeout=15, context=ctx).read()
        im = Image.open(io.BytesIO(data)); w, h = im.size
        r = ('editorial' if (w / h) >= 1.2 else 'portrait', round(w / h, 2))
    except Exception as e:
        r = ('BROKEN', str(e)[:40])
    _cache[url] = r; return r

def classify_film(f, poster):
    """Devuelve (posterSource|None, nota). poster = el string de poster a usar."""
    if not poster or not poster.strip():
        return (None, None)
    if is_tmdb(poster):
        return ('tmdb', 'tmdb→portrait')
    url = resolve_url(poster)
    if not url:
        return ('custom', 'path no-medible→custom')
    kind, val = measure(url)
    if kind == 'BROKEN':
        # No dejar el poster sin posterSource (lo exige el gate). Adivina por host;
        # se reporta ROTO igual → Fase A.2 lo re-hostea (y ahí se re-mide).
        host = urlparse(poster).netloc if poster.startswith('http') else ''
        guess = 'editorial' if any(host.endswith(e) for e in ('cloudfront.net', 'supabase.co')) else 'custom'
        return (guess, f'ROTO {val}')
    if kind == 'editorial':
        return ('editorial', f'landscape r={val}')
    return ('custom', f'portrait r={val}')

def process(fp, apply):
    name = os.path.basename(fp).replace('.json', '')
    d = json.load(open(fp, encoding='utf-8'))
    posters_map = {}
    if isinstance(d, dict):
        posters_map = {**(d.get('posters') or {}), **(d.get('customPosters') or {})}
    films = films_of(d)
    by_key = {}
    for f in films: by_key.setdefault(norm_key(f.get('title', '')), f)

    changes = []; broken = []; counts = {'editorial': 0, 'tmdb': 0, 'custom': 0, 'skip': 0}
    handled = set()
    # 1) inline
    for f in films:
        p = f.get('poster')
        if not p or not p.strip():
            counts['skip'] += 1; continue
        src, note = classify_film(f, p)
        if src is None:
            counts['skip'] += 1; continue
        if note and 'ROTO' in note:
            broken.append((f.get('title', ''), note))   # reportar, pero igual setear posterSource
        counts[src] += 1
        handled.add(id(f))
        if f.get('posterSource') != src:
            changes.append((f.get('title', ''), f.get('posterSource'), src, note))
            if apply: f['posterSource'] = src
    # 2) map (posters/customPosters) → adjuntar al film por título
    for k, v in posters_map.items():
        f = by_key.get(norm_key(k))
        if f is None or id(f) in handled: continue
        src, note = classify_film(f, v)
        if src is None:
            broken.append((k, note)); continue
        counts[src] += 1
        if f.get('posterSource') != src:
            changes.append((k, f.get('posterSource'), src, note + ' (map)'))
            if apply: f['posterSource'] = src

    if apply and changes:
        json.dump(d, open(fp, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

    print(f"\n{'█' if broken else '▶'} {name}  editorial={counts['editorial']} tmdb={counts['tmdb']} custom={counts['custom']}  cambios={len(changes)}")
    ed = [c for c in changes if c[2] == 'editorial']
    if ed:
        print(f"   → {len(ed)} NUEVOS editoriales (landscape mal-clasificados hoy):")
        for t, old, new, note in ed[:12]: print(f"      · {t[:44]:46s} [{note}]")
        if len(ed) > 12: print(f"      … +{len(ed)-12} más")
    if broken:
        print(f"   ⚠ {len(broken)} ROTOS (re-hostear):")
        for t, note in broken: print(f"      · {t[:44]:46s} {note}")
    return counts, changes, broken

def main():
    args = sys.argv[1:]
    apply = '--apply' in args
    ids = [a for a in args if not a.startswith('--')]
    if not ids:
        print("uso: classify-posters.py <id|all> [--apply]"); sys.exit(1)
    if ids == ['all']:
        fps = sorted(glob.glob('festivals/*.json'))
    else:
        fps = [f'festivals/{i}.json' if not i.endswith('.json') else i for i in ids]
    print(f"{'✍  APLICANDO' if apply else '👀 DRY-RUN (no escribe)'}  ·  {len(fps)} festival(es)")
    tb = 0
    for fp in fps:
        if not os.path.exists(fp): print(f"  ✗ no existe: {fp}"); continue
        _, _, broken = process(fp, apply)
        tb += len(broken)
    print(f"\n{'═'*50}\nTotal rotos a re-hostear: {tb}")
    if not apply:
        print("DRY-RUN — nada escrito. Agregá --apply para aplicar.")

if __name__ == '__main__':
    main()
