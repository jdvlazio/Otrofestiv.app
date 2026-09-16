#!/usr/bin/env python3
"""narrarelfuturo-2026-posters.py — re-hostear los pósters del festival.

Lee   festivals/staging/narrarelfuturo-2026-obras.json     (42 pósters, wp-content)
      festivals/staging/narrarelfuturo-2026-talleres.json  (retrato del tallerista)
Esc.  assets/narrarelfuturo-2026/<slug>.<ext>
      festivals/staging/narrarelfuturo-2026-posters.json   {url_remota: '/assets/…'}

Por qué: [poster-host] avisa que narrarelfuturo.com no está en la whitelist —
un WordPress puede bloquear el hotlink o borrar el archivo cuando pase el
festival, y el póster de la app moriría con él. Se baja UNA vez, en su forma
original (sin variantes «-1024x476»), con el slug de lib para que el nombre
sea el mismo que usaría enriquecer.py --posters.

El crudo es quien decide qué póster va (línea 'poster' de cada obra); este paso
solo le da la tabla remota→local y él la aplica. No toca ningún otro sidecar.
"""
import io, json, os, subprocess, sys, time
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


def main():
    os.makedirs(DEST, exist_ok=True)
    mapa, bajados, fallos = {}, 0, []
    for titulo, url in fuentes():
        if url in mapa:
            continue
        ext = url.rsplit('.', 1)[-1].lower().split('?')[0]
        ext = ext if ext in ('jpg', 'jpeg', 'png', 'webp') else 'jpg'
        nombre = f'{slug(titulo)}.{ext}'
        p = f'{DEST}/{nombre}'
        if not os.path.exists(p) or os.path.getsize(p) < 5000:
            r = subprocess.run(['curl', '-sL', '--max-time', '40', '-A', UA, url, '-o', p])
            time.sleep(0.2)
            if r.returncode or not os.path.exists(p) or os.path.getsize(p) < 5000:
                fallos.append((titulo, url))
                if os.path.exists(p):
                    os.remove(p)
                continue
            bajados += 1
        mapa[url] = f'/assets/narrarelfuturo-2026/{nombre}'
    io.open(f'{ST}/narrarelfuturo-2026-posters.json', 'w', encoding='utf-8').write(
        json.dumps({'_provenance': provenance('narrarelfuturo.com/wp-content (pósters de las fichas y retratos de talleres)',
                                              total=len(mapa)),
                    'posters': mapa}, ensure_ascii=False, indent=1) + '\n')
    print(f'── posters: {len(mapa)} re-hosteados ({bajados} bajados ahora) → assets/narrarelfuturo-2026/')
    for t, u in fallos:
        print(f'  ✗ {t}: {u}')
    if fallos:
        sys.exit(1)


if __name__ == '__main__':
    main()
