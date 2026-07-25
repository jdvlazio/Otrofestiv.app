#!/usr/bin/env python3
# ── optimize-posters.py — pósters al peso justo para la app ───────────────────
#
# Cada onboarding baja pósters de tamaños dispares (FICDEH: 474–1857px, 8MB).
# La app los muestra a ≤400px; servir originales es ancho de banda regalado.
#
# POLÍTICA (nace de FICDEH, 26 jul 2026): redimensionar a MAX_W=500px de ancho.
# 500 no es casual: es el MÍNIMO de TMDB para carteles → el mismo archivo queda
# liviano para la app Y sigue siendo apto para las altas TMDB (gate de
# tmdb-gaps.py). Si alguna vez se necesita el original en alta, se re-baja de la
# fuente: el onboarding debe commitear el sidecar de URLs fuente (ver FICDEH:
# festivals/staging/ficdeh-2026-posters-src.json).
#
# Seguro por diseño: nunca AGRANDA (un póster de 474px se queda como está),
# nunca toca PNG con transparencia, y con --dry-run solo reporta.
#
# Uso:
#   python3 scripts/optimize-posters.py assets/ficdeh/            # in place
#   python3 scripts/optimize-posters.py assets/ficdeh/ --dry-run  # solo reporte
#   python3 scripts/optimize-posters.py foto.jpg otra.jpg --max-width 800

import sys, os, glob

MAX_W, QUALITY = 500, 82

def main():
    from PIL import Image
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    dry = '--dry-run' in sys.argv
    if '--max-width' in sys.argv:
        globals()['MAX_W'] = int(sys.argv[sys.argv.index('--max-width') + 1])
    files = []
    for a in args:
        if os.path.isdir(a):
            files += sorted(glob.glob(os.path.join(a, '*.jpg'))) \
                   + sorted(glob.glob(os.path.join(a, '*.jpeg'))) \
                   + sorted(glob.glob(os.path.join(a, '*.png')))
        else:
            files.append(a)
    if not files:
        print('Uso: optimize-posters.py <dir|archivos…> [--max-width N] [--dry-run]')
        sys.exit(1)

    antes = despues = tocados = saltados = 0
    for fp in files:
        size0 = os.path.getsize(fp)
        antes += size0
        im = Image.open(fp)
        if im.mode in ('RGBA', 'P') and fp.lower().endswith('.png'):
            saltados += 1; despues += size0
            continue                      # transparencia: no convertir a ciegas
        w, h = im.size
        if w <= MAX_W and size0 < 120_000:
            saltados += 1; despues += size0
            continue                      # ya está bien — jamás agrandar
        nw = min(w, MAX_W)
        nh = round(h * nw / w)
        out = im.convert('RGB').resize((nw, nh), Image.LANCZOS)
        if dry:
            print(f'  {os.path.basename(fp):46} {w}x{h} {size0//1024}KB → {nw}x{nh}')
            despues += size0
            continue
        tmp = fp + '.opt'
        out.save(tmp, 'JPEG', quality=QUALITY, optimize=True, progressive=True)
        if os.path.getsize(tmp) < size0:   # reemplazar SOLO si de verdad mejora
            os.replace(tmp, fp); tocados += 1
        else:
            os.remove(tmp); saltados += 1
        despues += os.path.getsize(fp)
    print(f'\noptimize-posters: {tocados} optimizados · {saltados} ya al peso '
          f'· {antes/1e6:.1f}MB → {despues/1e6:.1f}MB '
          f'({100 - despues * 100 // max(antes, 1)}% menos)')

if __name__ == '__main__':
    main()
