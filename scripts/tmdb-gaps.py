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
# ── GUARD DE PÓSTER (regla dura de Juan) ──────────────────────────────────────
# NO se da de alta en TMDB una obra SIN póster, ni con un póster por debajo del
# mínimo de TMDB (500px de ancho). Lección del ensayo "Al son que me toquen
# bailo" (21 jul 2026): el asset era 298px → TMDB lo rechazó por resolución, y
# quedó una ficha huérfana sin imagen. Casi TODOS nuestros pósters de films son
# ~300px (optimizados para la app móvil) → no sirven como fuente TMDB. Por eso
# el reporte separa las obras en APTAS (póster ≥500px, listas para alta) y
# BLOQUEADAS (sin póster o chico → conseguir el original en alta ANTES de crear).
# Medir es barato y evita crear basura en una base pública.
#
# Uso:
#   python3 scripts/tmdb-gaps.py festivals/tercertiempo-2026.json
#   python3 scripts/tmdb-gaps.py festivals/tercertiempo-2026.json --day 2026-07-17
#   python3 scripts/tmdb-gaps.py --all          # todos los festivales

import json, sys, glob, os, struct

MIN_POSTER_W = 500  # mínimo de TMDB para carteles (px de ancho). Por debajo → rechazo.

def _rows(films, day=None):
    for f in films:
        if day and f.get('day') != day:
            continue
        if f.get('is_cortos') and f.get('film_list'):
            for it in f['film_list']:
                yield f, it
        elif f.get('type') != 'event':
            yield f, f

def _img_dims(fp):
    """(w,h) leyendo cabeceras PNG/GIF/JPEG sin dependencias (PIL puede no estar
    en CI). None si no se puede determinar."""
    try:
        with open(fp, 'rb') as f:
            head = f.read(26)
            if head[:8] == b'\x89PNG\r\n\x1a\n':
                w, h = struct.unpack('>II', head[16:24]); return (w, h)
            if head[:6] in (b'GIF87a', b'GIF89a'):
                w, h = struct.unpack('<HH', head[6:10]); return (w, h)
            if head[:2] != b'\xff\xd8':            # no es JPEG
                return None
            f.seek(2)                              # saltar SOI, recorrer segmentos
            while True:
                b = f.read(1)
                if not b:
                    return None
                if b != b'\xff':
                    continue
                marker = f.read(1)
                while marker == b'\xff':            # relleno entre marcadores
                    marker = f.read(1)
                if not marker:
                    return None
                m = marker[0]
                # SOF0..SOF15 llevan las dimensiones; excluir DHT/JPG/DAC
                if 0xC0 <= m <= 0xCF and m not in (0xC4, 0xC8, 0xCC):
                    f.read(3)                       # longitud(2) + precisión(1)
                    h, w = struct.unpack('>HH', f.read(4)); return (w, h)
                seg = f.read(2)
                if len(seg) < 2:
                    return None
                f.seek(struct.unpack('>H', seg)[0] - 2, 1)
    except Exception:
        return None

def _poster_status(poster, repo_root):
    """Clasifica el póster para el alta. Devuelve (apto:bool, etiqueta:str)."""
    if not poster:
        return (False, '⛔ SIN PÓSTER — no dar de alta')
    if poster.startswith('http'):
        return (False, '⚠️  remoto (http) — no medible acá')
    if not poster.startswith('/assets/'):
        return (False, f'⚠️  no-asset ({poster}) — ¿ya en TMDB?')
    fp = os.path.join(repo_root, poster.lstrip('/'))
    if not os.path.exists(fp):
        return (False, f'⚠️  no encontrado en disco ({poster})')
    dims = _img_dims(fp)
    if not dims:
        return (False, f'⚠️  no se pudo medir ({poster})')
    w, h = dims
    if w < MIN_POSTER_W:
        return (False, f'⛔ CHICO {w}×{h}px (<{MIN_POSTER_W}px) — conseguir póster en alta')
    return (True, f'✅ {w}×{h}px')

def _dump_form(parent, it, poster_label):
    """Vuelca los campos de una obra APTA, listos para copy/paste al formulario."""
    ctx = (f"  (en «{parent['title']}» · {parent.get('day','?')} {parent.get('time','')})"
           if parent is not it else f"  ({it.get('day','?')} {it.get('time','')})")
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
    print(f"    Poster:       {it['poster']}  {poster_label}")

def report(path, day=None):
    d = json.load(open(path, encoding='utf-8'))
    films = d.get('films', d if isinstance(d, list) else [])
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(path)))
    total, seen = 0, set()
    aptas, bloqueadas = [], []
    for parent, it in _rows(films, day):
        key = it.get('title')
        if key in seen:
            continue
        seen.add(key); total += 1
        if it.get('lbSlug'):
            continue
        apto, label = _poster_status(it.get('poster'), repo_root)
        (aptas if apto else bloqueadas).append((parent, it, label))

    gaps = len(aptas) + len(bloqueadas)
    hdr = f"\n═══ {path}{' · ' + day if day else ''} — {gaps} sin ficha de {total} obras"
    hdr += f" · {len(aptas)} aptas · {len(bloqueadas)} bloqueadas por póster ═══"
    print(hdr)

    if aptas:
        print(f"\n──── APTAS PARA ALTA (póster ≥{MIN_POSTER_W}px) ────")
        for parent, it, label in aptas:
            _dump_form(parent, it, label)
    if bloqueadas:
        print(f"\n──── BLOQUEADAS — conseguir póster en alta ANTES de crear ────")
        for parent, it, label in bloqueadas:
            ctx = f"«{parent['title']}»" if parent is not it else (it.get('day') or '?')
            print(f"  ✗ {it['title']:45} {label}   ({ctx})")
    if not gaps:
        print("  ✓ todas las obras tienen ficha (lbSlug presente)")
    # exit-code: nº de APTAS pendientes (las bloqueadas no son accionables aún)
    return len(aptas)

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
