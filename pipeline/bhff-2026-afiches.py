#!/usr/bin/env python3
"""bhff-2026-afiches.py — el afiche original de cada corto, recortado de su lámina.

Cada lámina de la Selección 2026 (bogotahorrorfilmfest.com/seleccion-2026/) es
un cuadrado de 2160 px con el AFICHE ORIGINAL de la obra al centro, dentro de un
marco blanco, y el título y la dirección pintados debajo. Lo que se publica es
solo lo de adentro del marco: el afiche, sin la lámina.

EL RECORTE se mide, no se pone a ojo, y DESDE AFUERA: el fondo de la lámina
(foto en rojo) nunca es blanco, y el afiche puede serlo —«Los Lobo» es casi
todo blanco; «ANAX» y «Ruth» tienen letras y figuras blancas—. Así que desde
cada lado de la lámina se camina hacia el centro hasta el primer píxel casi
blanco (el borde EXTERIOR del marco), sobre varias líneas, y el grosor del marco
se toma de los lados donde termina limpio (el mismo para los cuatro: es un
paspartú). Candados:
  · el marco tiene que aparecer en los CUATRO lados, igual en todas las líneas;
  · el afiche resultante es vertical (alto > ancho);
  · si algo no cuadra, la obra queda sin afiche y se dice cuál.

Escribe festivals/staging/bhff-2026-afiches.json (título publicado → archivo),
que enriquecer.py usa SOLO donde TMDB y lo ya publicado no tienen afiche.
"""
import io
import json
import os
import re
import sys
import unicodedata

from PIL import Image

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = f'{REPO}/fuentes/bhff-2026'
OJOS = f'{DIR}/ojos-seleccion.json'
CRUDO = f'{REPO}/festivals/staging/bhff-2026-crudo.json'
DESTINO = f'{REPO}/festivals/staging/bhff-2026-afiches.json'
SALIDA = f'{DIR}/afiches'
BLANCO = 225
# los largos no están en la Selección del sitio: su lámina (mismo formato) es la del
# carrusel «Selección oficial — Largometraje nacional» de IG (p/DcxA28kjgVo, sin sesión)
LAMINAS_IG = {'Parapeto': 'fuentes/ig/DcxA28kjgVo/2.jpg'}


def plano(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def blanco(px):
    return min(px[:3]) >= BLANCO


def exterior(im, lineas, eje, sentido):
    """El borde exterior del marco y su grosor, sobre cada línea (lineas = coordenadas del otro eje)."""
    w, h = im.size
    n = w if eje == 'x' else h
    out = []
    for c in lineas:
        rango = range(n) if sentido > 0 else range(n - 1, -1, -1)
        borde = grosor = None
        for k in rango:
            px = im.getpixel((k, c) if eje == 'x' else (c, k))
            if borde is None:
                if blanco(px):
                    borde, grosor = k, 1
            elif blanco(px):
                grosor += 1
            else:
                break
        out.append((borde, grosor))
    return out


def a_lo_largo(im, x, y0, dy):
    """Sobre la barra vertical del marco (columna x), desde y0 hacia dy mientras sea blanco → el último y blanco."""
    y = y0
    while 0 <= y + dy < im.size[1] and blanco(im.getpixel((x, y + dy))):
        y += dy
    return y


def recortar(ruta):
    im = Image.open(ruta).convert('RGB')
    w, h = im.size
    ys = [int(h * f) for f in (0.30, 0.40, 0.50)]
    lados = {'l': exterior(im, ys, 'x', 1), 'r': exterior(im, ys, 'x', -1)}
    for k, v in lados.items():
        bs = [b for b, _ in v]
        if None in bs or max(bs) - min(bs) > 2:
            return None, f'el marco no aparece parejo en el lado {k}: {bs}'
    # el grosor del paspartú: el más fino medido (un afiche blanco junto al
    # marco lo «engorda»; nada lo adelgaza)
    g = min(gr for v in lados.values() for _, gr in v)
    if not 3 <= g <= 60:
        return None, f'grosor de marco raro: {g} px'
    lo = min(b for b, _ in lados['l'])
    ro = max(b for b, _ in lados['r'])
    # arriba y abajo NO se buscan desde el borde de la lámina: ahí están la
    # cabecera y el título, en blanco. Se recorre cada barra vertical del marco
    # hasta donde deja de ser blanca: eso es el alto del marco
    xl, xr = lo + g // 2, ro - g // 2
    tops = [a_lo_largo(im, xl, ys[1], -1), a_lo_largo(im, xr, ys[1], -1)]
    bots = [a_lo_largo(im, xl, ys[1], 1), a_lo_largo(im, xr, ys[1], 1)]
    if max(tops) - min(tops) > 2 or max(bots) - min(bots) > 2:
        return None, f'las dos barras del marco no miden lo mismo: arriba {tops}, abajo {bots}'
    l, r = lo + g, ro - g + 1
    t, b = max(tops) + g, min(bots) - g + 1
    if not (b - t > r - l > 0):
        return None, f'el recorte no es un afiche vertical ({r - l}×{b - t})'
    return im.crop((l, t, r, b)), f'{r - l}×{b - t}, marco {g} px'


def main():
    ojos = json.load(io.open(OJOS, encoding='utf-8'))['laminas']
    lam = {plano(t): f for f, _, t, *_ in ojos}
    titulos = []
    for f in json.load(io.open(CRUDO, encoding='utf-8'))['funciones']:
        for o in f.get('obras') or [f]:
            if plano(o['titulo']) in lam and o['titulo'] not in titulos:
                titulos.append(o['titulo'])
    os.makedirs(SALIDA, exist_ok=True)
    afiches, sin = {}, []
    for t in titulos + list(LAMINAS_IG):
        f = os.path.basename(LAMINAS_IG[t]) if t in LAMINAS_IG else lam[plano(t)]
        im, que = recortar(f'{REPO}/{LAMINAS_IG[t]}' if t in LAMINAS_IG else f'{DIR}/laminas/{f}')
        if im is None:
            sin.append(f'{t} ({f}): {que}')
            continue
        dest = f'{SALIDA}/{"ig-DcxA28kjgVo-" if t in LAMINAS_IG else ""}{os.path.splitext(f)[0]}.jpg'
        im.save(dest, quality=92)
        afiches[t] = {'archivo': os.path.relpath(dest, REPO),
                      'fuente': (f'IG @bogotahorrorfest p/DcxA28kjgVo, lámina {f}: el afiche, ' if t in LAMINAS_IG else
                                 f'bogotahorrorfilmfest.com, Selección 2026: el afiche de la lámina {f}, ')
                                + 
                                f'recortado por dentro del marco ({que})'}
    io.open(DESTINO, 'w', encoding='utf-8').write(json.dumps({
        '_provenance': {'fuente': 'bogotahorrorfilmfest.com, Selección 2026 (láminas de festivalData)',
                        'capturado': '2026-10-07', 'regla': 'solo donde TMDB y lo ya publicado no tienen afiche',
                        'genera': 'pipeline/bhff-2026-afiches.py'},
        'afiches': dict(sorted(afiches.items()))}, ensure_ascii=False, indent=1) + '\n')
    print(f'✓ {len(afiches)} afiches recortados de sus láminas · {len(sin)} sin → {os.path.relpath(DESTINO, REPO)}')
    for x in sin:
        print('   sin ·', x)
    if sin:
        sys.exit(1)


if __name__ == '__main__':
    main()
