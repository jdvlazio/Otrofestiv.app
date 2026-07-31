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
# ── GUARD DE PROPORCIÓN (lección de la tanda FICDEH, 25 jul 2026) ─────────────
# TMDB también rechaza por "aspect ratio", y ese rechazo llega DESPUÉS de haber
# creado la ficha y abierto el formulario de subida — es decir, cuando el error
# ya cuesta caro. Evidencia medida contra el uploader real: 0.700 (700×1000) fue
# aceptado en 6 carteles; 0.725 (1857×2560, el original de Amalgama) fue
# rechazado, y solo pasó tras un recorte centrado a 0.700. Por eso se valida el
# ancho Y la proporción antes de tocar la web: fuera de rango la obra queda
# BLOQUEADA con la instrucción de recorte, no "apta con sorpresa".
#
# Uso:
#   python3 scripts/tmdb-gaps.py festivals/tercertiempo-2026.json
#   python3 scripts/tmdb-gaps.py festivals/tercertiempo-2026.json --day 2026-07-17
#   python3 scripts/tmdb-gaps.py --all          # todos los festivales

import json, sys, glob, os, struct

MIN_POSTER_W = 500  # mínimo de TMDB para carteles (px de ancho). Por debajo → rechazo.
RATIO_OK = (0.66, 0.71)  # rango de w/h que el uploader acepta (medido, ver cabecera)
RATIO_TARGET = 0.70      # a esto se recorta lo que queda fuera de rango

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

def _src_sidecar(path):
    """Sidecar `<festival>-posters-src.json` (URL + dims del póster ORIGINAL de la
    fuente). Existe porque el asset del repo está optimizado para la app (~500px)
    y NO es la copia que se sube: a TMDB va el original en alta. Devuelve {} si
    el festival no tiene sidecar."""
    base = os.path.splitext(path)[0]
    # También en staging/: el sidecar no puede vivir en festivals/ porque el
    # validador trata todo *.json de ahí como un festival (FINCA, 29 jul 2026).
    d, n = os.path.split(base)
    for cand in (base + '-posters-src.json',
                 os.path.join(d, 'staging', n + '-posters-src.json')):
        if os.path.exists(cand):
            try:
                return json.load(open(cand, encoding='utf-8'))
            except Exception:
                return {}
    return {}

def _src_entry(poster, sidecar):
    """Entrada del sidecar para este póster (clave = nombre de archivo sin extensión)."""
    if not poster or not sidecar:
        return None
    key = os.path.splitext(os.path.basename(poster))[0]
    return sidecar.get(key)

def _poster_status(poster, repo_root, src=None):
    """Clasifica el póster para el alta. Devuelve (apto:bool, etiqueta:str).
    Si hay original en el sidecar se juzga ESE, que es el archivo que se sube."""
    if src and src.get('w') and src.get('h'):
        w, h = src['w'], src['h']
        ok, label = _dims_verdict(w, h)
        return (ok, label + ' (original de la fuente)')
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
    return _dims_verdict(*dims)

def _dims_verdict(w, h):
    """Veredicto del uploader de TMDB para unas dimensiones: ancho mínimo Y
    proporción dentro de rango. Ambas se comprueban ANTES de crear la ficha."""
    if w < MIN_POSTER_W:
        return (False, f'⛔ CHICO {w}×{h}px (<{MIN_POSTER_W}px) — conseguir póster en alta')
    ratio = w / h
    if not (RATIO_OK[0] <= ratio <= RATIO_OK[1]):
        crop_w, crop_h = int(h * RATIO_TARGET), h
        if crop_w > w:                       # más alto que ancho: recortar arriba/abajo
            crop_w, crop_h = w, int(w / RATIO_TARGET)
        return (False, f'⛔ PROPORCIÓN {ratio:.3f} (fuera de {RATIO_OK[0]}–{RATIO_OK[1]}) '
                       f'— recorte centrado a {crop_w}×{crop_h}px antes de subir')
    return (True, f'✅ {w}×{h}px · ratio {ratio:.3f}')

def _dump_form(parent, it, poster_label, src=None):
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
    if src and src.get('src'):
        print(f"    Subir:        {src['src']}")

def report(path, day=None):
    d = json.load(open(path, encoding='utf-8'))
    films = d.get('films', d if isinstance(d, list) else [])
    # raíz del repo = subir hasta encontrar assets/ (soporta festivals/ Y
    # festivals/staging/ — el pre-onboarding vive un nivel más adentro)
    repo_root = os.path.dirname(os.path.abspath(path))
    while repo_root != '/' and not os.path.isdir(os.path.join(repo_root, 'assets')):
        repo_root = os.path.dirname(repo_root)
    sidecar = _src_sidecar(path)
    total, seen = 0, set()
    aptas, bloqueadas = [], []
    for parent, it in _rows(films, day):
        key = it.get('title')
        if key in seen:
            continue
        seen.add(key); total += 1
        if it.get('lbSlug'):
            continue
        src = _src_entry(it.get('poster'), sidecar)
        apto, label = _poster_status(it.get('poster'), repo_root, src)
        (aptas if apto else bloqueadas).append((parent, it, label, src))

    gaps = len(aptas) + len(bloqueadas)
    hdr = f"\n═══ {path}{' · ' + day if day else ''} — {gaps} sin ficha de {total} obras"
    hdr += f" · {len(aptas)} aptas · {len(bloqueadas)} bloqueadas por póster ═══"
    print(hdr)

    if aptas:
        print(f"\n──── APTAS PARA ALTA (≥{MIN_POSTER_W}px · ratio {RATIO_OK[0]}–{RATIO_OK[1]}) ────")
        for parent, it, label, src in aptas:
            _dump_form(parent, it, label, src)
    if bloqueadas:
        print(f"\n──── BLOQUEADAS — arreglar el póster ANTES de crear la ficha ────")
        for parent, it, label, src in bloqueadas:
            ctx = f"«{parent['title']}»" if parent is not it else (it.get('day') or '?')
            print(f"  ✗ {it['title']:45} {label}   ({ctx})")
            if src and src.get('src'):
                print(f"      original: {src['src']}")
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
