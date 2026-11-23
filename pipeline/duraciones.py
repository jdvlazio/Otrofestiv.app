# -*- coding: utf-8 -*-
"""duraciones.py — la duración de una OBRA no puede contradecir a TMDB en silencio.

POR QUÉ EXISTE (20 nov 2026). En Funza, «Basta Mamá» salió con 125 min y dura
77 (TMDB 1627217, Letterboxd). La agenda del festival daba el BLOQUE de 6:30 a
8:35 p. m. —película más conversatorio, «Horario sujeto a duración oficial de la
película»— y el crudo lo tomó como duración de la obra. El ensamblador SÍ lo
notó: dejó «125 min en el festival, 77 en TMDB» en `_avisos_duracion` del build.
Nadie lo leyó. El mismo fallo mudo de las sinopsis. Juan: «no debe volver a
ocurrir».

Una duración inflada no es un detalle: el plan reserva esa franja, esconde
choques reales y descarta funciones que sí cabían.

LA REGLA. Toda obra con ficha de TMDB cuya duración difiera del runtime de TMDB
en más de 5 min y más del 10 % queda pendiente hasta que alguien la mire:
  · se corrige (era la franja, o un error de la fuente), o
  · se declara en festivals/staging/<id>-correcciones.json, con su porqué:
        "duracion_distinta": {"<título>": {"_por_que": "corte de festival de 92 min (web del festival)"}}
La duración del festival sigue mandando (regla del 29 sep 2026): este dueño no
cambia ningún número, solo obliga a mirar.

DE DÓNDE SALE EL RUNTIME. Del enriquecido del festival
(festivals/staging/<id>-enriquecido.json, `duracion_tmdb`): sin red, el mismo
dato con el que se armó el build. Una obra sin ficha o sin runtime no se mide.

Lo consultan publicar.py (frena al publicar) y validate.py [duracion-vs-tmdb]
(vigila lo publicado de los festivales vivos).

    python3 pipeline/duraciones.py <id>     # las diferencias de un festival
"""
import json, os, re, sys, unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _n(s):
    s = unicodedata.normalize('NFD', str(s or '')).lower()
    return ''.join(c for c in s if c.isalnum())


def minutos(v):
    m = re.match(r'\s*(\d+)', str(v or ''))
    return int(m.group(1)) if m else None


def fuera_de_margen(dur, runtime):
    """Más de 5 min Y más del 10 %: un corte de festival de 3 min no es un error;
    una franja de 125 contra una obra de 77, sí."""
    return abs(dur - runtime) > max(5, 0.1 * runtime)


def runtimes(fid, raiz=REPO):
    """{título normalizado: runtime de TMDB} del enriquecido del festival."""
    p = os.path.join(raiz, 'festivals', 'staging', f'{fid}-enriquecido.json')
    if not os.path.exists(p):
        return {}
    d = json.load(open(p, encoding='utf-8'))
    out = {}
    for t, e in (d.get('verificadas') or {}).items():
        if isinstance(e, dict) and e.get('tmdb_id') and (e.get('duracion_tmdb') or 0) > 0:
            out[_n(t)] = int(e['duracion_tmdb'])
    for e in d.get('obras') or []:
        t = e.get('titulo')
        if t and e.get('tmdb_id') and (e.get('duracion_tmdb') or 0) > 0:
            out.setdefault(_n(t), int(e['duracion_tmdb']))
    return out


def declaradas(fid, raiz=REPO):
    """`duracion_distinta` con porqué → ({título normalizado}, [mal declaradas])."""
    p = os.path.join(raiz, 'festivals', 'staging', f'{fid}-correcciones.json')
    if not os.path.exists(p):
        return set(), []
    ok, mal = set(), []
    for t, v in ((json.load(open(p, encoding='utf-8')) or {}).get('duracion_distinta') or {}).items():
        if isinstance(v, dict) and str(v.get('_por_que') or '').strip():
            ok.add(_n(t))
        else:
            mal.append(f'{fid}: duracion_distinta «{t[:40]}» sin _por_que')
    return ok, mal


def distintas(fid, films, raiz=REPO):
    """Obras cuya duración contradice a TMDB y nadie declaró → [{titulo, dur, tmdb, programa}]."""
    rt = runtimes(fid, raiz)
    if not rt:
        return []
    dec, _ = declaradas(fid, raiz)
    out, vistas = [], set()
    for f in films or []:
        if f.get('event_kind') or f.get('type') == 'event':
            continue
        inner = [o for o in (f.get('film_list') or []) if isinstance(o, dict)]
        for o in (inner or [f]):
            t = o.get('title')
            if not t or _n(t) in vistas or _n(t) in dec:
                continue
            d, r = minutos(o.get('duration')), rt.get(_n(t))
            if d and r and fuera_de_margen(d, r):
                vistas.add(_n(t))
                out.append({'titulo': t, 'dur': d, 'tmdb': r,
                            'programa': f.get('title') if inner else None})
    return out


def linea(x):
    prog = f' (en «{x["programa"][:30]}»)' if x.get('programa') else ''
    pista = ' (¿la franja con conversatorio?)' if x['dur'] > x['tmdb'] else ''
    return (f'«{x["titulo"][:50]}»{prog}: {x["dur"]} min publicado, {x["tmdb"]} en TMDB{pista} — '
            f'corregir, o declarar `duracion_distinta` con su porqué')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    fid = sys.argv[1]
    p = os.path.join(REPO, 'festivals', f'{fid}.json')
    if not os.path.exists(p):
        sys.exit(f'✗ no existe {p} (usar el nombre del archivo: funza-2026)')
    xs = distintas(fid, json.load(open(p, encoding='utf-8'))['films'])
    for x in xs:
        print('·', linea(x))
    print(f'{len(xs)} diferencia(s) sin declarar')
