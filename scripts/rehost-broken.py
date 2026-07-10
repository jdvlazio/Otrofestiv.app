#!/usr/bin/env python3
# ── rehost-broken.py — Fase A.2 (quirúrgico): solo toca posters ROTOS.
#
# Prueba por URL (no por título → no toca el film equivocado) cada poster http
# no-tmdb. Actúa por status:
#   404/410/gone → strip poster + posterSource → el film cae a generativo (fallback diseñado)
#   403          → reintenta con Referer (anti-hotlink). Si vive → baja a /assets/<fest>/<slug>.<ext>
#                  y reescribe poster. Si sigue muerto → strip.
#   2xx          → VIVO → no se toca (las frágiles-pero-vivas NO son de esta fase)
#
# Uso: python3 scripts/rehost-broken.py <id|all> [--apply]   (sin flag = dry-run)

import json, glob, os, re, sys, ssl, io, urllib.request
from urllib.parse import urlparse
from PIL import Image

ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15'
TMDB_HOSTS = ('image.tmdb.org',)

def is_local_or_tmdb(p):
    if not p: return True
    if p.startswith('/'): return True                      # /assets/ o path tmdb
    if p.startswith('http'): return urlparse(p).netloc in TMDB_HOSTS
    return True

def titled_objects(d):
    out = []
    def w(x):
        if isinstance(x, dict):
            if x.get('title'): out.append(x)
            for v in x.values(): w(v)
        elif isinstance(x, list):
            for v in x: w(v)
    w(d); return out

def slugify(s):
    s = re.sub(r"[‘’‚‛′ʼ]", "'", s or '').lower()
    s = re.sub(r"[áàä]", 'a', s); s = re.sub(r"[éèë]", 'e', s)
    s = re.sub(r"[íìï]", 'i', s); s = re.sub(r"[óòö]", 'o', s)
    s = re.sub(r"[úùü]", 'u', s); s = re.sub(r"ñ", 'n', s)
    s = re.sub(r"[^a-z0-9]+", '-', s).strip('-')
    return s[:60] or 'poster'

def probe(url, referer=None):
    """(status:int|'ERR', bytes|None). HEAD primero; si baja, hace GET (para 403 recuperable)."""
    headers = {'User-Agent': UA}
    if referer: headers['Referer'] = referer
    try:
        req = urllib.request.Request(url, headers=headers, method='HEAD')
        r = urllib.request.urlopen(req, timeout=15, context=ctx)
        return (r.status, None)
    except urllib.error.HTTPError as e:
        return (e.code, None)
    except Exception:
        return ('ERR', None)

def fetch(url, referer=None):
    headers = {'User-Agent': UA}
    if referer: headers['Referer'] = referer
    try:
        req = urllib.request.Request(url, headers=headers)
        data = urllib.request.urlopen(req, timeout=20, context=ctx).read()
        Image.open(io.BytesIO(data)).verify()              # que sea imagen real
        return data
    except Exception:
        return None

def ext_of(url, data=None):
    m = re.search(r'\.(jpe?g|png|webp)(\?|$)', url, re.I)
    if m: return m.group(1).lower().replace('jpeg', 'jpg')
    if data:
        try: return {'JPEG':'jpg','PNG':'png','WEBP':'webp'}.get(Image.open(io.BytesIO(data)).format, 'jpg')
        except Exception: pass
    return 'jpg'

def process(fp, apply):
    name = os.path.basename(fp).replace('.json', '')
    d = json.load(open(fp, encoding='utf-8'))
    films = titled_objects(d)
    stripped = []; rehosted = []; alive = 0; touched_urls = {}
    for f in films:
        p = (f.get('poster') or '').strip()
        if is_local_or_tmdb(p): continue
        if p in touched_urls:                              # misma URL en varios films
            act = touched_urls[p]
        else:
            host_root = f"{urlparse(p).scheme}://{urlparse(p).netloc}/"
            st, _ = probe(p)
            if isinstance(st, int) and 200 <= st < 300:
                act = ('alive', None)
            elif st == 403:
                data = fetch(p, referer=host_root)
                if data:
                    ext = ext_of(p, data)
                    rel = f"/assets/{name}/{slugify(f.get('title',''))}.{ext}"
                    act = ('rehost', (rel, data))
                else:
                    act = ('strip', None)
            else:                                          # 404/410/ERR → muerto
                act = ('strip', None)
            touched_urls[p] = act
        kind, payload = act
        if kind == 'alive':
            alive += 1
        elif kind == 'rehost':
            rel, data = payload
            rehosted.append((f.get('title',''), rel))
            if apply:
                os.makedirs(os.path.dirname('.'+rel), exist_ok=True)
                open('.'+rel, 'wb').write(data)
                f['poster'] = rel                          # posterSource se re-mide luego (classify)
        elif kind == 'strip':
            stripped.append((f.get('title',''), p[:48]))
            if apply:
                f.pop('poster', None); f.pop('posterSource', None)
    if apply and (stripped or rehosted):
        json.dump(d, open(fp, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

    flag = '█' if (stripped or rehosted) else '▶'
    print(f"{flag} {name}: vivas={alive}  re-host={len(rehosted)}  strip={len(stripped)}")
    for t, rel in rehosted: print(f"   ✓ RE-HOST '{t[:40]}' → {rel}")
    for t, u in stripped:   print(f"   ✗ STRIP  '{t[:40]}' (muerto) — cae a generativo")
    return len(rehosted), len(stripped)

def main():
    args = sys.argv[1:]; apply = '--apply' in args
    ids = [a for a in args if not a.startswith('--')]
    if not ids: print("uso: rehost-broken.py <id|all> [--apply]"); sys.exit(1)
    fps = sorted(glob.glob('festivals/*.json')) if ids == ['all'] else \
          [f'festivals/{i}.json' if not i.endswith('.json') else i for i in ids]
    print(f"{'✍  APLICANDO' if apply else '👀 DRY-RUN (no escribe)'}")
    tr = ts = 0
    for fp in fps:
        if os.path.exists(fp):
            r, s = process(fp, apply); tr += r; ts += s
    print(f"\n{'═'*50}\nRe-hosteadas: {tr}  ·  Stripped→generativo: {ts}")
    if not apply: print("DRY-RUN — nada escrito. --apply para aplicar.")

if __name__ == '__main__':
    main()
