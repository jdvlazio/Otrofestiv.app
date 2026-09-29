#!/usr/bin/env python3
"""biff-2026-iconos.py — lo que la tabla «por días» dice con DIBUJOS, leído por píxeles.

La columna «Sección» de la tabla no tiene texto: cada celda es un COLOR (la
sección de la película) y, a veces, un ÍCONO blanco:

    ☆ estrella  → «Función con presencia del equipo de la película»
    🎟 tiquete   → «Ingreso únicamente con invitación»
    ✹ sello     → «Entrada libre»

La leyenda está al pie de cada página, con los tres íconos en negro. No son
imágenes incrustadas (pdfimages no ve ninguna): son vectores, así que se
renderiza la página (pdftoppm, 200 dpi) y se compara la silueta blanca de
cada celda contra las tres de la leyenda (IoU a 16×16).

LAS DOS COMPROBACIONES que hacen de esto una lectura y no una adivinanza:
  · el COLOR de cada celda tiene que ser el mismo para todas las funciones de
    una película, y uno solo por sección del catálogo;
  · la leyenda del programa dice «Todas las funciones del programa son de
    entrada libre» para la muestra BIFF BANG: sus 7 celdas tienen que salir
    con el sello.
"""
import io
import json
import os
import subprocess
import sys

from PIL import Image

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = f'{REPO}/fuentes/biff-2026'
PDF = f'{D}/Programacion_BIFF_12_DIGITAL.pdf'
DPI = 200
S = DPI / 72
COL = (252, 281)                 # el INTERIOR de la columna «Sección», en puntos
LEYENDA = {'equipo': (423, 430), 'invitacion': (432, 439), 'libre': (441, 448)}
LEYENDA_X = (273, 285)


def render(pag):
    p = f'{D}/pordias-{pag}.png'
    if not os.path.exists(p):
        subprocess.run(['pdftoppm', '-f', str(pag), '-l', str(pag), '-r', str(DPI), '-png',
                        PDF, f'{D}/pordias'], check=True)
    return Image.open(p).convert('RGB')


def silueta(img, oscuro, rango=None):
    """La silueta del ícono a 16×16. `rango` = (x0, x1): solo esas columnas —
    los bordes se detectan SIEMPRE sobre la celda entera (en una pieza angosta,
    el propio ícono cruza el 60% del ancho y se borraba como si fuera borde)."""
    g = img.convert('L')
    w, h = g.size
    px = g.load()
    on = lambda x, y: (px[x, y] < 110 if oscuro else px[x, y] > 225)
    # LAS LÍNEAS QUE SEPARAN LAS FILAS son blancas y cruzan la celda de lado a
    # lado: la primera versión las tomaba por el sello de «entrada libre» (69
    # funciones «libres»). Una fila de píxeles blancos a más del 60% del ancho
    # es borde, no ícono.
    bordes = {y for y in range(h) if sum(1 for x in range(w) if on(x, y)) > 0.6 * w}
    x0, x1 = rango or (0, w)
    pts = [(x, y) for y in range(h) if y not in bordes for x in range(x0, x1) if on(x, y)]
    if len(pts) < 25:
        return None
    x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts)
    y0, y1 = min(p[1] for p in pts), max(p[1] for p in pts)
    m = Image.new('L', (x1 - x0 + 1, y1 - y0 + 1), 0)
    for x, y in pts:
        m.putpixel((x - x0, y - y0), 255)
    return [1 if v > 127 else 0 for v in m.resize((16, 16)).get_flattened_data()]


def piezas(img):
    """La celda puede traer DOS íconos lado a lado (los cortos BIFF Bang del
    9, 13 y 14: equipo presente Y entrada libre). La primera versión hacía una
    sola silueta de todo lo blanco y la clasificaba como uno: se perdía el
    equipo (triple lectura, 29 sep). Se parte por columnas sin blanco, con un
    hueco mínimo de 4 px para no partir un ícono por dentro."""
    g = img.convert('L')
    w, h = g.size
    px = g.load()
    bordes = {y for y in range(h) if sum(1 for x in range(w) if px[x, y] > 225) > 0.6 * w}
    llenas = [any(px[x, y] > 225 for y in range(h) if y not in bordes) for x in range(w)]
    grupos, ini, vacio = [], None, 0
    for x, v in enumerate(llenas + [False] * 5):
        if v:
            if ini is None:
                ini = x
            vacio = 0
        elif ini is not None:
            vacio += 1
            if vacio >= 4:
                grupos.append((ini, x - vacio + 1))
                ini, vacio = None, 0
    return grupos or [(0, w)]


def iou(a, b):
    i = sum(1 for x, y in zip(a, b) if x and y)
    u = sum(1 for x, y in zip(a, b) if x or y)
    return i / u if u else 0


def main():
    filas = json.load(io.open(f'{D}/por-dias.json', encoding='utf-8'))['funciones']
    leg_img = render(44)
    plantillas = {k: silueta(leg_img.crop((int(LEYENDA_X[0] * S), int((y0 - 1) * S),
                                           int(LEYENDA_X[1] * S), int((y1 + 1) * S))), True)
                  for k, (y0, y1) in LEYENDA.items()}
    for f in filas:
        img = render(f['pag'])
        y = f['y']
        celda = img.crop((int(COL[0] * S), int((y - 1) * S), int(COL[1] * S), int((y + 8) * S)))
        # el color: la mediana de los píxeles que NO son el ícono blanco
        px = [p for p in celda.get_flattened_data() if sum(p) < 660]
        px.sort(key=sum)
        f['color'] = '#%02x%02x%02x' % px[len(px) // 2] if px else None
        leidos = []
        for rango in piezas(celda):
            s = silueta(celda, False, rango)
            if s:
                puntaje = {k: iou(s, v) for k, v in plantillas.items()}
                k = max(puntaje, key=puntaje.get)
                leidos.append(k if puntaje[k] >= 0.45 else f'?{k}:{puntaje[k]:.2f}')
        f['icono'] = '+'.join(sorted(leidos)) or None
    json.dump({'_fuente': 'PDF oficial BIFF 12, columna «Sección» de la tabla por días, por píxeles',
               'funciones': filas}, io.open(f'{D}/por-dias-iconos.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    from collections import Counter
    print('íconos:', dict(Counter(f['icono'] for f in filas)))


if __name__ == '__main__':
    main()
