#!/usr/bin/env python3
"""narrarelfuturo-2026-posters.py — re-hostear los pósters del festival.

Lee   festivals/staging/narrarelfuturo-2026-obras.json     (42 pósters, wp-content)
      festivals/staging/narrarelfuturo-2026-talleres.json  (retrato del tallerista)
Esc.  assets/narrarelfuturo-2026/<slug>.<ext>
      festivals/staging/narrarelfuturo-2026-posters.json
        {url_remota: {'ruta': '/assets/…', 'w', 'h', 'posterSource'}}

CADA IMAGEN SE MIDE, y de la medida sale `posterSource`, con el mismo umbral que
scripts/classify-posters.py (aspecto ≥ 1.2 → 'editorial'). Este festival mezcla
las dos formas —afiches 2:3 de los cortos y stills 16:9 de los talleres y de
varios documentales—, y la forma no se puede deducir del tipo de actividad: hay
películas con still y talleres con afiche. Un still 16:9 marcado como afiche se
publica RECORTADO en un hueco 2:3; marcado editorial va enmarcado y entero.

Por qué: [poster-host] avisa que narrarelfuturo.com no está en la whitelist —
un WordPress puede bloquear el hotlink o borrar el archivo cuando pase el
festival, y el póster de la app moriría con él. Se baja UNA vez, en su forma
original (sin variantes «-1024x476»), con el slug de lib para que el nombre
sea el mismo que usaría enriquecer.py --posters.

El crudo es quien decide qué póster va (línea 'poster' de cada obra); este paso
solo le da la tabla remota→local y él la aplica. No toca ningún otro sidecar.
"""
import io, json, os, subprocess, sys, time

from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import slug, provenance

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
DEST = f'{REPO}/assets/narrarelfuturo-2026'
UA = 'Mozilla/5.0 (Macintosh) Otrofestiv/pipeline'


def fuentes():
    O = json.load(io.open(f'{ST}/narrarelfuturo-2026-obras.json', encoding='utf-8'))['obras']
    for o in O:
        if o.get('poster'):
            yield o['titulo'], o['poster']
    T = json.load(io.open(f'{ST}/narrarelfuturo-2026-talleres.json', encoding='utf-8'))
    T = T if isinstance(T, list) else T.get('talleres', T)
    for t in T:
        if t.get('imagen'):
            yield 'taller ' + t['titulo'], t['imagen']
    C = json.load(io.open(f'{ST}/narrarelfuturo-2026-charlas.json', encoding='utf-8'))
    for c in C.get('charlas') or []:
        if c.get('imagen'):
            yield 'charla ' + c['titulo'], c['imagen']


def _mide(p):
    """(w, h) si el archivo es de verdad una imagen; None si no lo es."""
    try:
        with Image.open(p) as im:
            return im.size
    except Exception:
        return None


def main():
    os.makedirs(DEST, exist_ok=True)
    # DE QUÉ URL SALIÓ CADA ARCHIVO. El nombre local se deriva del TÍTULO, así
    # que cuando la fuente cambia de imagen —pasó con los once talleres, que
    # dejaron de apuntar al og:image y pasaron al retrato del tallerista— el
    # archivo viejo seguía ahí con el nombre correcto y no se volvía a bajar:
    # el parser ya decía la verdad y las imágenes publicadas eran las anteriores.
    # Un caché que solo mira si el archivo EXISTE no sabe si es el que toca.
    previo = {}
    if os.path.exists(f'{ST}/narrarelfuturo-2026-posters.json'):
        _p = json.load(io.open(f'{ST}/narrarelfuturo-2026-posters.json', encoding='utf-8'))
        previo = {v['ruta']: u for u, v in (_p.get('posters') or {}).items()}
    mapa, bajados, fallos = {}, 0, []
    for titulo, url in fuentes():
        if url in mapa:
            continue
        ext = url.rsplit('.', 1)[-1].lower().split('?')[0]
        ext = ext if ext in ('jpg', 'jpeg', 'png', 'webp') else 'jpg'
        nombre = f'{slug(titulo)}.{ext}'
        p = f'{DEST}/{nombre}'
        ruta = f'/assets/narrarelfuturo-2026/{nombre}'
        if not os.path.exists(p) or not _mide(p) or previo.get(ruta) != url:
            r = subprocess.run(['curl', '-sL', '--max-time', '40', '-A', UA, url, '-o', p])
            time.sleep(0.2)
            bajados += 1
        # PESAR NO ES MIRAR. El retrato de «Señales Líquidas» se guardó como un
        # .jpg de 212 KB que era una PÁGINA HTML: pasaba de sobra el umbral de
        # tamaño y habría llegado a producción como imagen rota. Ahora se abre:
        # si no es una imagen, no entra en la tabla y el paso falla ruidosamente.
        wh = _mide(p)
        if not wh:
            fallos.append((titulo, url))
            if os.path.exists(p):
                os.remove(p)
            continue
        w, h = wh
        mapa[url] = {'ruta': ruta, 'w': w, 'h': h,
                     'posterSource': 'editorial' if w / h >= 1.2 else 'oficial'}
    io.open(f'{ST}/narrarelfuturo-2026-posters.json', 'w', encoding='utf-8').write(
        json.dumps({'_provenance': provenance('narrarelfuturo.com/wp-content (pósters de las fichas y retratos de talleres)',
                                              total=len(mapa)),
                    'posters': mapa}, ensure_ascii=False, indent=1) + '\n')
    _ed = sum(1 for v in mapa.values() if v['posterSource'] == 'editorial')
    print(f'── posters: {len(mapa)} re-hosteados ({bajados} bajados ahora) → assets/narrarelfuturo-2026/')
    print(f'   forma: {len(mapa) - _ed} afiche (2:3) · {_ed} still 16:9 → editorial')
    for t, u in fallos:
        print(f'  ✗ {t}: {u}')
    if fallos:
        sys.exit(1)


if __name__ == '__main__':
    main()
