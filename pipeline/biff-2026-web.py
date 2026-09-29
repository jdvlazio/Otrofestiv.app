#!/usr/bin/env python3
"""biff-2026-web.py — la ficha de cada película en biff.co → duración y enlaces de compra.

La web del festival publica una ficha por película (`pelicula.php?epel=…`), a la
que se llega desde las páginas de sección (`peliculas.php?ecat=…`, enlazadas
en el menú). Cada ficha trae:
  · la DURACIÓN, que se compara con la del PDF y la de TMDB (regla de Juan:
    las duraciones siempre se comparan entre fuentes). En la web «9 Temples to
    Heaven» dice 92 y el PDF 140;
  · el enlace de compra de la Cinemateca (tuboleta, por película) y la página
    de la película en Cine Colombia.

La ficha termina con «Continúa descubriendo», un carrusel de OTRAS películas con
su propio título y duración: solo se lee lo que hay ANTES de él.
"""
import html
import io
import json
import os
import re
import subprocess
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = f'{REPO}/fuentes/biff-2026/web'
BASE = 'https://biff.co/'
UA = 'Mozilla/5.0 (Macintosh) Otrofestiv'


def bajar(url, nombre):
    p = f'{D}/{nombre}'
    if not os.path.exists(p):
        r = subprocess.run(['curl', '-sL', '-A', UA, '--max-time', '40', url], capture_output=True)
        io.open(p, 'wb').write(r.stdout)
        time.sleep(0.5)
    return io.open(p, encoding='utf-8', errors='ignore').read()


def texto(h):
    t = re.sub(r'<script.*?</script>|<style.*?</style>', '', h, flags=re.S)
    return [x.strip() for x in html.unescape(re.sub(r'<[^>]+>', '\n', t)).split('\n') if x.strip()]


def main():
    os.makedirs(D, exist_ok=True)
    home = bajar(BASE, 'home.html')
    cats = sorted(set(re.findall(r'href="(?:https://biff\.co/)?(peliculas\.php\?ecat=[^"]+)"', home)))
    fichas = {}
    for i, c in enumerate(cats):
        h = bajar(BASE + html.unescape(c), f'cat-{i:02d}.html')
        for p in re.findall(r'href="(pelicula\.php\?epel=[^"]+)"', h):
            fichas.setdefault(html.unescape(p), None)
    out = []
    for i, p in enumerate(sorted(fichas)):
        h = bajar(BASE + p, f'pel-{i:03d}.html')
        cuerpo = h.split('Continúa descubriendo')[0]
        L = texto(cuerpo)
        # EL BLOQUE PRINCIPAL: sección · TÍTULO · países · «género | año | NN min.»
        # (el carrusel de «Continúa descubriendo» usa OTRO formato, y la
        # primera versión leyó ese: 0 duraciones)
        k = next((n for n, x in enumerate(L) if re.search(r'\|\s*\d{4}\s*\|\s*\d+\s*min', x)), None)
        titulo = L[k - 2] if k and k >= 2 else ''
        m = re.search(r'\|\s*(\d{4})\s*\|\s*(\d+)\s*min', L[k]) if k is not None else None
        dur = int(m.group(2)) if m else None
        links = sorted(set(re.findall(r'href="(https?://[^"]+)"', cuerpo)))
        out.append({'titulo_web': titulo, 'duracion_web': dur, 'url': BASE + p,
                    'tuboleta': next((u for u in links if 'tuboleta' in u), None),
                    'cinecolombia': next((u for u in links if 'cinecolombia.com/films' in u), None)})
    io.open(f'{REPO}/fuentes/biff-2026/web.json', 'w', encoding='utf-8').write(
        json.dumps({'_fuente': 'biff.co, una ficha por película', 'fichas': out}, ensure_ascii=False, indent=1))
    print(f'✓ {len(out)} fichas de la web · {sum(1 for o in out if o["duracion_web"])} con duración · '
          f'{sum(1 for o in out if o["tuboleta"])} con enlace de la Cinemateca · '
          f'{sum(1 for o in out if o["cinecolombia"])} con Cine Colombia')


if __name__ == '__main__':
    main()
