"""Corta los N stills de una tira. Histograma + conjunto óptimo.

DOS IDEAS, después de que fallaran los umbrales:

1 · HISTOGRAMA EN VENTANA GRANDE, no media en ventana corta. El still que dice
    «love» —blanco puro sobre negro puro— rompía todo detector basado en
    contraste: su borde interno salta más que los bordes de verdad. Pero arriba
    y abajo de ese salto el HISTOGRAMA es el mismo (blanco y negro), así que la
    distancia entre histogramas ahí es casi cero, mientras que entre dos stills
    distintos cambia entero. La textura interna engaña al brillo; no engaña al
    reparto de colores.

2 · SE ELIGE EL CONJUNTO, NO LOS PICOS. Coger los N-1 picos más altos deja
    pasar un corte que parte un still en 274 y 696 px. Con programación
    dinámica se busca la combinación que maximiza la suma de evidencia MENOS
    una penalización por bandas de altura disparatada: un corte que crea dos
    bandas absurdas ya no compensa aunque su pico sea alto.

El número de stills lo dice el texto de la propia página, así que N es dato.
"""
from PIL import Image
import statistics, sys

BINS = 6                                  # 6×6×6 = 216 casillas de color


def _hist(im, xs, a, b, pc):
    h = [0] * (BINS ** 3)
    n = 0
    for y in range(a, b):
        for x in xs:
            r, g, bl = pc[x, y]
            h[(r * BINS // 256) * BINS * BINS + (g * BINS // 256) * BINS + (bl * BINS // 256)] += 1
            n += 1
    return [v / n for v in h] if n else h


def _d(A, B):                              # distancia L1 entre histogramas (0..2)
    return sum(abs(a - b) for a, b in zip(A, B))


def cortar(ruta, n, y0=0, alto_min=140, paso=8, V=40, lam=0.9):
    im = Image.open(ruta).convert('RGB'); w, h = im.size; pc = im.load()
    xs = list(range(0, w, paso))
    # evidencia de borde en cada fila candidata
    ev = []
    for y in range(y0 + V, h - V, 8):
        d = _d(_hist(im, xs, y - V, y, pc), _hist(im, xs, y, y + V, pc))
        ev.append((y, d))
    if not ev:
        return im, [(y0, h)]
    # candidatos: máximos locales por encima de la mediana
    med = statistics.median(d for _, d in ev)
    cand = [(y, d) for i, (y, d) in enumerate(ev)
            if d > med and d >= max(x[1] for x in ev[max(0, i-3):i+4])]
    cand = [c for c in cand if c[0] - y0 >= alto_min and h - c[0] >= alto_min]
    if len(cand) < n - 1:
        cand = sorted(ev, key=lambda t: -t[1])[:max(n * 4, 24)]
        cand = sorted(c for c in cand if c[0] - y0 >= alto_min and h - c[0] >= alto_min)
        cand = [(y, dict(ev)[y]) for y in cand] if cand and isinstance(cand[0], int) else cand
    ideal = (h - y0) / n
    # DP: dp[k][i] = mejor puntaje usando i-ésimo candidato como k-ésimo corte
    C = [y for y, _ in cand]; S = [d for _, d in cand]
    NEG = float('-inf')
    dp = [[NEG] * len(C) for _ in range(n)]
    prev = [[-1] * len(C) for _ in range(n)]
    pena = lambda alto: lam * abs(alto - ideal) / ideal
    for i, y in enumerate(C):
        dp[1][i] = S[i] - pena(y - y0)
    for k in range(2, n):
        for i, y in enumerate(C):
            for j in range(i):
                if y - C[j] < alto_min or dp[k-1][j] == NEG:
                    continue
                v = dp[k-1][j] + S[i] - pena(y - C[j])
                if v > dp[k][i]:
                    dp[k][i], prev[k][i] = v, j
    mejor, arg = NEG, -1
    for i, y in enumerate(C):
        if dp[n-1][i] == NEG:
            continue
        v = dp[n-1][i] - pena(h - y)
        if v > mejor:
            mejor, arg = v, i
    cortes, k = [], n - 1
    while arg >= 0 and k >= 1:
        cortes.append(C[arg]); arg = prev[k][arg]; k -= 1
    bs = [y0] + sorted(cortes) + [h]
    return im, [(bs[i], bs[i+1]) for i in range(len(bs)-1)]


def parte_vertical(im, a, b, umbral=0.30):
    """¿Esta banda son DOS stills lado a lado en vez de uno ancho?

    El PDF no siempre pone un still por fila: la página 13 tiene cuatro en
    rejilla 2×2, media anchura cada uno. Con el modelo de «una fila = un still»
    faltaban dos obras y el detector se inventaba cortes en otro sitio para
    cuadrar el número.

    Se compara el histograma de la mitad izquierda con el de la derecha: dos
    fotogramas distintos no comparten paleta; una foto ancha sí consigo misma.
    """
    w = im.size[0]
    xs_i = list(range(0, w // 2, 8))
    xs_d = list(range(w // 2, w, 8))
    pc = im.load()
    hi = _hist(im, xs_i, a, b, pc)
    hd = _hist(im, xs_d, a, b, pc)
    return _d(hi, hd) > umbral


if __name__ == '__main__':
    im, bs = cortar(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else 0)
    print(f'{sys.argv[1]}: {len(bs)} bandas')
    for i, (a, b) in enumerate(bs, 1):
        print(f'   {i:2}. y {a:5}–{b:5}  alto {b-a:4}')
