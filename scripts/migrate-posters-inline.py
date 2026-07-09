#!/usr/bin/env python3
# ── migrate-posters-inline.py — modelo map → inline (Fase A.1 estrategia pósters)
#
# Mueve cada poster de posters{}/customPosters{} al campo `poster` del film
# correspondiente (match por normKey del título; customPosters gana sobre posters,
# como en runtime), y ELIMINA los mapas raíz. Muere el modelo dual: un film = un
# `poster`. posterSource queda intacto. getFilmPoster ya cae de #6 (map) a #7 (f.poster).
#
# Uso: python3 scripts/migrate-posters-inline.py <id|all> [--apply]  (sin flag = dry-run)

import json, glob, os, re, sys

def normk(s): return re.sub(r"[‘’‚‛′ʼ]", "'", s or "")

def titled_objects(d):
    out = []
    def w(x):
        if isinstance(x, dict):
            if x.get('title'): out.append(x)
            for v in x.values(): w(v)
        elif isinstance(x, list):
            for v in x: w(v)
    w(d); return out

def process(fp, apply):
    name = os.path.basename(fp).replace('.json', '')
    d = json.load(open(fp, encoding='utf-8'))
    posters = d.get('posters') or {}
    custom = d.get('customPosters') or {}
    if not posters and not custom:
        print(f"▶ {name}: sin map (ya inline) — nada que hacer")
        return 0, 0, 0
    # merge: posters primero, customPosters override (gana)
    merged = {}
    for k, v in posters.items(): merged[normk(k)] = ('posters', k, v)
    for k, v in custom.items():  merged[normk(k)] = ('custom', k, v)
    # índice normKey → [films con ese título]
    by_key = {}
    for f in titled_objects(d):
        by_key.setdefault(normk(f.get('title', '')), []).append(f)

    inlined = 0; conflicts = []; orphans = []
    for nk, (src, origkey, val) in merged.items():
        films = by_key.get(nk, [])
        if not films:
            orphans.append(origkey); continue
        for f in films:
            cur = (f.get('poster') or '').strip()
            if cur and cur != val:
                conflicts.append((f.get('title', ''), cur[:40], val[:40]))
            if apply:
                f['poster'] = val
            inlined += 1
    if apply:
        d.pop('posters', None); d.pop('customPosters', None)
        json.dump(d, open(fp, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

    print(f"{'█' if (conflicts or orphans) else '▶'} {name}: {len(merged)} entradas map → {inlined} inlined"
          f"  ·  conflictos={len(conflicts)}  huérfanos={len(orphans)}")
    for t, cur, new in conflicts[:6]:
        print(f"     ⚠ conflicto '{t[:36]}': tenía {cur} → gana el map {new}")
    for o in orphans[:6]:
        print(f"     ❓ huérfano (sin film): '{o[:44]}'")
    return inlined, len(conflicts), len(orphans)

def main():
    args = sys.argv[1:]; apply = '--apply' in args
    ids = [a for a in args if not a.startswith('--')]
    if not ids: print("uso: migrate-posters-inline.py <id|all> [--apply]"); sys.exit(1)
    fps = sorted(glob.glob('festivals/*.json')) if ids == ['all'] else \
          [f'festivals/{i}.json' if not i.endswith('.json') else i for i in ids]
    print(f"{'✍  APLICANDO' if apply else '👀 DRY-RUN (no escribe)'}")
    for fp in fps:
        if os.path.exists(fp): process(fp, apply)
    if not apply: print("\nDRY-RUN — nada escrito. --apply para aplicar.")

if __name__ == '__main__':
    main()
