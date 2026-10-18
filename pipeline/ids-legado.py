#!/usr/bin/env python3
"""La pasada de legado del id estable (docs/FUNCION.md §11.2 y §11.6 paso 4).

Da `id` a las funciones de los festivales YA publicados sin rearmarlos
(rearmar traería cambios del pipeline que nadie revisó) y congela su registro
festivals/staging/<fid>-funciones-ids.json. Rearmar después conserva cada id
(la clave es la misma que usa el ensamblador).

Dos caminos, por el mismo invariante de publicar-datos.py:
  · build — si publicar.py hoy reproduce lo publicado byte a byte, el id va
    al build y publicar.py lo propaga (las correcciones siguen pasando por ahí);
  · publicado — si no, el id va directo al JSON publicado, en su mismo formato.
En los dos, lo único que cambia en lo publicado es `id`: si cambia otra cosa, FRENA.

    python3 pipeline/ids-legado.py <fid> [<fid>...]
    python3 pipeline/ids-legado.py --todos
    python3 pipeline/ids-legado.py --todos --ver     # solo dice qué haría
"""
import glob, json, os, subprocess, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
import funcion  # noqa: E402
import lib      # noqa: E402


def _sin_id(d):
    return [{k: v for k, v in f.items() if k != 'id'} for f in d.get('films') or []]


def _publicar_reproduce(fid, pub_p):
    """¿publicar.py, sobre el build de hoy, da exactamente lo publicado? No deja rastro."""
    if not os.path.exists(f'{REPO}/pipeline/{fid}.plan.json') or not os.path.exists(f'{REPO}/festivals/staging/{fid}-build.json'):
        return False
    antes = open(pub_p, 'rb').read()
    estado = subprocess.run(['git', 'status', '--porcelain'], cwd=REPO, capture_output=True, text=True).stdout
    r = subprocess.run(['python3', 'pipeline/publicar.py', fid], cwd=REPO, capture_output=True, text=True)
    igual = r.returncode == 0 and open(pub_p, 'rb').read() == antes
    open(pub_p, 'wb').write(antes)
    if subprocess.run(['git', 'status', '--porcelain'], cwd=REPO, capture_output=True, text=True).stdout != estado:
        sys.exit(f'✗ {fid}: publicar.py tocó otros archivos al probar — revisar a mano')
    return igual


def pasar(fid, ver=False):
    pub_p = f'{REPO}/festivals/{fid}.json'
    reg_p = f'{REPO}/festivals/staging/{fid}-funciones-ids.json'
    raw = open(pub_p, encoding='utf-8').read()
    d = json.loads(raw)
    if os.path.exists(reg_p):
        return f'· {fid}: ya tiene registro, no se toca'
    camino = 'build' if _publicar_reproduce(fid, pub_p) else 'publicado'
    if ver:
        return f'· {fid}: iría por el camino «{camino}»'
    if camino == 'build':
        b_p = f'{REPO}/festivals/staging/{fid}-build.json'
        b_raw = open(b_p, encoding='utf-8').read()
        b = json.loads(b_raw)
        b['films'], reg = funcion.ids_para_publicado(b['films'], {})
        open(b_p, 'w', encoding='utf-8').write(funcion.volcar_como(b_raw, b))
        r = subprocess.run(['python3', 'pipeline/publicar.py', fid], cwd=REPO, capture_output=True, text=True)
        if r.returncode:
            sys.exit(f'✗ {fid}: publicar.py falló tras agregar ids:\n{r.stdout[-800:]}{r.stderr[-800:]}')
    else:
        d2 = dict(d)
        d2['films'], reg = funcion.ids_para_publicado(d['films'], {})
        open(pub_p, 'w', encoding='utf-8').write(funcion.volcar_como(raw, d2))
    nuevo = json.load(open(pub_p, encoding='utf-8'))
    if {k: v for k, v in nuevo.items() if k != 'films'} != {k: v for k, v in d.items() if k != 'films'} \
            or _sin_id(nuevo) != _sin_id(d):
        sys.exit(f'✗ {fid}: lo publicado cambió en algo más que `id` — revisar a mano')
    json.dump({'_provenance': lib.provenance('ids-legado.py: ids estables congelados desde lo publicado (docs/FUNCION.md §11.2)'),
               **reg}, open(reg_p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    con = sum(1 for f in nuevo['films'] if f.get('id'))
    return f'✓ {fid}: {con}/{len(nuevo["films"])} funciones con id (camino «{camino}»)'


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if '--todos' in sys.argv:
        args = sorted(os.path.basename(p)[:-5] for p in glob.glob(f'{REPO}/festivals/*.json'))
    if not args:
        sys.exit(__doc__)
    for fid in args:
        print(pasar(fid, ver='--ver' in sys.argv))
