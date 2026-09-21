#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""villadelcine-2026-posters.py — el afiche que el propio festival publica.

POR QUÉ EXISTE. `enriquecer.py --posters` trae los de TMDB, y para un festival
de cortos eso cubre poquísimo: casi ninguna de estas obras tiene ficha. Pero el
festival SÍ publica un afiche por obra en su web, uno por página, y lo tenemos
extraído desde el primer día en `-obras-web.json`. Estaba ahí, con su URL, sin
usarse: 81 afiches que la app iba a dejar en blanco.

QUÉ HACE. Baja el afiche de cada obra a `assets/villadelcine-2026/<slug>.jpg` y
escribe el sidecar que el ensamblador lee. Respeta lo que TMDB ya trajo: si una
obra tiene ficha verificada, su póster manda —es el original y suele estar
mejor—; el del festival entra donde no hay otro.

NO TOCA LO YA BAJADO (write-once): los assets pasan después por
`encuadrar-posters.py`, y volver a bajarlos desharía ese trabajo.

Lee   festivals/staging/villadelcine-2026-obras-web.json
Esc.  festivals/staging/villadelcine-2026-posters.json + assets/villadelcine-2026/
"""
import json, os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import provenance, norm

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
ASSETS = f'{REPO}/assets/villadelcine-2026'
OUT = f'{ST}/villadelcine-2026-posters.json'
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120 Safari/537.36')


def _slug_afiche(t):
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', norm(t))).strip('-')[:60]


def main():
    web = json.load(open(f'{ST}/villadelcine-2026-obras-web.json',
                         encoding='utf-8'))['obras']
    enr_p = f'{ST}/villadelcine-2026-enriquecido.json'
    con_tmdb = set()
    if os.path.exists(enr_p):
        con_tmdb = {norm(o['titulo']) for o in
                    json.load(open(enr_p, encoding='utf-8')).get('obras', [])
                    if o.get('poster')}

    os.makedirs(ASSETS, exist_ok=True)
    mapa, bajados, ya, sin = {}, 0, 0, []
    for o in web:
        if not o['afiches']:
            sin.append(o['titulo'])
            continue
        if norm(o['titulo']) in con_tmdb:
            continue                       # el de TMDB manda: es el original
        url = o['afiches'][0]
        ext = '.jpg'
        dest = f'{ASSETS}/{_slug_afiche(o["titulo"])}{ext}'
        if os.path.exists(dest) and os.path.getsize(dest) > 4000:
            ya += 1
        else:
            r = subprocess.run(['curl', '-sSL', '--max-time', '45', '-A', UA,
                                '-o', dest, url], capture_output=True)
            if r.returncode or not os.path.exists(dest) or os.path.getsize(dest) < 4000:
                sin.append(f'{o["titulo"]} (no se pudo bajar)')
                if os.path.exists(dest):
                    os.remove(dest)
                continue
            # LA WEB LOS SIRVE EN WEBP aunque el enlace diga otra cosa: 61 de
            # 79 quedaron siendo webp con nombre .jpg, y `encuadrar-posters`
            # —que usa sips— no los puede reescribir. Se convierten a JPEG de
            # verdad al bajarlos, que es donde cuesta una línea y no un
            # arreglo aguas abajo.
            try:
                from PIL import Image
                im = Image.open(dest)
                if im.format != 'JPEG':
                    im.convert('RGB').save(dest, 'JPEG', quality=90)
            except Exception as e:
                sin.append(f'{o["titulo"]} (no se pudo convertir: {str(e)[:40]})')
                continue
            bajados += 1
        mapa[o['titulo']] = {'poster': f'/assets/villadelcine-2026/{os.path.basename(dest)}',
                             'posterSource': 'oficial', '_url': url}

    json.dump({'_provenance': provenance(
        'villadelcine.com — el afiche que el festival publica en la página de cada obra',
        que_aporta='el póster de las obras que no tienen ficha en TMDB, que en un '
                   'festival de cortos son casi todas',
        url='https://villadelcine.com/festival-2024-2/',
        metodo='write-once: lo ya bajado no se vuelve a pedir, porque después pasa '
               'por encuadrar-posters.py y re-bajarlo desharía el encuadre'),
        'posters': mapa}, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{len(mapa)} afiches del festival · {bajados} bajados ahora · {ya} ya estaban '
          f'· {len(con_tmdb)} los trae TMDB → {os.path.basename(OUT)}')
    if sin:
        print(f'   sin afiche ({len(sin)}): ' + ', '.join(x[:26] for x in sin[:6]))


if __name__ == '__main__':
    main()
