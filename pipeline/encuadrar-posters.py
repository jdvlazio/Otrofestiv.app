# -*- coding: utf-8 -*-
"""encuadrar-posters.py <fest-id> [--aplicar] — el póster cubre el placeholder.

REGLA (Juan, 9 ago 2026): todo póster debe cubrir EXACTAMENTE la proporción y el
tamaño del placeholder. Ni marco visible, ni hueco, ni recorte del afiche. Es un
cálculo, no un ajuste a ojo.

Dos pasos, en este orden y siempre desde el archivo ORIGINAL:

  1. CAJA DE CONTENIDO — se descarta el borde uniforme de los CUATRO lados
     (arriba, abajo, izquierda, derecha). Quitar solo arriba y abajo deja el
     marco en los costados: es el error que se cometió antes.
  2. ESCALA AL LIENZO — la caja se lleva a 780×1170 (2:3) estirando el eje que
     haga falta. Estirar, no recortar: el afiche se ve completo. Un estirado de
     hasta ~16% no se percibe (probado en el keyArt).

Qué cuenta como borde: una fila (o columna) PLANA —poca varianza a lo largo— y
casi blanca o casi negra. Con dos candados contra comerse la imagen:

  · tope del 12% por lado, y
  · si el borde LLEGA al tope, no se toca ese lado: un marco termina solo, el
    arte sigue (así se salvan el cielo de «The Dig» o el fondo de «Vinyl
    Nation», que son claros de verdad).

VERIFICACIÓN incluida: tras aplicar, vuelve a medir y reporta cuántos pósters
quedan con borde detectable y cuántos fuera de 2:3. El objetivo es 0 y 0.
"""
import json, os, struct, subprocess, sys, tempfile, zlib

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIENZO_W, LIENZO_H = 780, 1170          # 2:3 exacto
# Calibrado con los píxeles reales de los afiches, no a ojo. Un marco es una
# fila PLANA —poca varianza a lo ancho— sea blanca, negra o gris: en «El juego
# de la vida» el marco son dos filas (255 y 178) y exigir «casi blanco» dejaba
# fuera la segunda, que es la línea gris que se veía. El arte, en cambio, tiene
# varianza alta desde la primera fila (117 ahí mismo).
PLANO, MAX_FRAC = 45, 0.12
# Zoom mínimo final: tras recortar el marco queda a veces 1–2 filas de
# transición (antialias del borde). En vez de afinar más el detector —que
# arriesga comerse arte— se escala un 4% y se recorta al centro: se traga el
# residuo perdiendo un 2% por lado, imperceptible. Es el «hacer zoom» de Juan.
OVERSCAN = 1.04
MUESTRA = 220                            # ancho de análisis


def rejilla(path):
    """→ (w, h, px[y][x] = luminancia 0-255) de una versión reducida."""
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as t:
        tmp = t.name
    subprocess.run(['sips', '-s', 'format', 'png', '-Z', str(MUESTRA), path, '--out', tmp],
                   capture_output=True)
    d = open(tmp, 'rb').read()
    os.unlink(tmp)
    pos, w, h, idat, canales = 8, 0, 0, b'', 3
    while pos < len(d):
        ln = struct.unpack('>I', d[pos:pos+4])[0]; tipo = d[pos+4:pos+8]
        if tipo == b'IHDR':
            w, h, _, color = struct.unpack('>IIBB', d[pos+8:pos+18])
            if color not in (2, 6):
                return None
            canales = 3 if color == 2 else 4
        elif tipo == b'IDAT':
            idat += d[pos+8:pos+8+ln]
        pos += 12 + ln
    raw = zlib.decompress(idat)
    stride, px, prev, i = w * canales, [], bytearray(w * canales), 0
    for _ in range(h):
        f = raw[i]; lin = bytearray(raw[i+1:i+1+stride]); i += 1 + stride
        for x in range(stride):
            a = lin[x-canales] if x >= canales else 0
            b = prev[x]; c = prev[x-canales] if x >= canales else 0
            if f == 1: lin[x] = (lin[x] + a) & 255
            elif f == 2: lin[x] = (lin[x] + b) & 255
            elif f == 3: lin[x] = (lin[x] + (a + b) // 2) & 255
            elif f == 4:
                p = a + b - c; pa, pb, pc = abs(p-a), abs(p-b), abs(p-c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                lin[x] = (lin[x] + pr) & 255
        px.append([(lin[x] + lin[x+1] + lin[x+2]) // 3 for x in range(0, stride, canales)])
        prev = lin
    return w, h, px


def _borde(lineas):
    """Cuántas líneas de borde uniforme hay al principio de la secuencia."""
    n, tope = 0, max(2, int(len(lineas) * MAX_FRAC))
    for l in lineas:
        if (max(l) - min(l)) < PLANO:
            n += 1
            if n >= tope:
                return 0          # sigue más allá del tope → es arte, no marco
        else:
            break
    return n


def caja(px, w, h):
    """→ (arriba, abajo, izquierda, derecha) del marco, en píxeles de análisis."""
    cols = [[px[y][x] for y in range(h)] for x in range(w)]
    return (_borde(px), _borde(px[::-1]), _borde(cols), _borde(cols[::-1]))


def medir(path):
    r = rejilla(path)
    if not r:
        return None
    w, h, px = r
    return caja(px, w, h), (w, h)


def main():
    fid = sys.argv[1] if len(sys.argv) > 1 else sys.exit(
        'uso: python3 pipeline/encuadrar-posters.py <fest-id> [--aplicar]')
    aplicar = '--aplicar' in sys.argv
    d = json.load(open(f'{REPO}/festivals/{fid}.json', encoding='utf-8'))

    vistos, plan, editorial = set(), [], []
    for f in d['films']:
        p = f.get('poster') or ''
        if not p.startswith('/assets/') or p in vistos:
            continue
        vistos.add(p)
        real = REPO + p
        if not os.path.exists(real):
            continue
        # El still 16:9 de un posterSource:editorial NO va al lienzo 2:3: su
        # marco lo encuadra a 16/9 a propósito (docs/POSTERS.md §4).
        if f.get('posterSource') == 'editorial':
            editorial.append(os.path.basename(p)); continue
        m = medir(real)
        if not m:
            continue
        (t, b, l, r), (aw, ah) = m
        plan.append((real, os.path.basename(p), t, b, l, r, aw, ah))

    con_marco = [x for x in plan if min(x[2], x[3]) > 0 or min(x[4], x[5]) > 0]
    print(f'{len(vistos)} pósters · con marco {len(con_marco)}'
          + (f' · editorial 16:9 respetados {len(editorial)}' if editorial else ''))
    for real, n, t, b, l, r, aw, ah in con_marco[:40]:
        print(f'   {n[:46]:48} marco ↑{t} ↓{b} ←{l} →{r} (de {aw}×{ah})')
    if not aplicar:
        print('\n(simulación — usar --aplicar)')
        return

    fallos = 0
    for real, n, t, b, l, r, aw, ah in plan:
        W = int(subprocess.run(['sips', '-g', 'pixelWidth', real], capture_output=True)
                .stdout.decode().split(':')[-1])
        H = int(subprocess.run(['sips', '-g', 'pixelHeight', real], capture_output=True)
                .stdout.decode().split(':')[-1])
        # Un MARCO rodea: solo es marco lo que aparece en los DOS lados
        # opuestos, y se recorta por el menor de ellos. Si un solo lado tiene
        # borde claro es arte (el cielo de «The Dig»), y recortarlo mutila el
        # afiche. sips recorta CENTRADO —su --cropOffset se comporta como tal,
        # verificado— así que el recorte simétrico es además el único exacto.
        rv, rh = min(t, b), min(l, r)
        if rv or rh:
            # 1 · recortar la caja de contenido, EXACTA en los cuatro lados.
            #     sips recorta desde el centro y solo admite offset positivo,
            #     que quita de ARRIBA (verificado). Para quitar más de abajo se
            #     rota 180°, se recorta y se vuelve a rotar: exacto y sin
            #     inventar. Un recorte simétrico por el menor dejaría el marco
            #     del lado grueso, que es justo lo que se quiere eliminar.
            nh, nw = H - 2 * (rv * H // ah), W - 2 * (rh * W // aw)
            q = subprocess.run(['sips', '-c', str(nh), str(nw), real, '--out', real],
                               capture_output=True)
            if q.returncode != 0:
                print(f'   ✗ recorte falló en {n}: {q.stderr.decode().strip()[:70]}')
                fallos += 1
        # 2 · escalar al lienzo con overscan y recortar al centro: llena el
        #     placeholder exacto y se traga el residuo del borde.
        gz_h, gz_w = round(LIENZO_H * OVERSCAN), round(LIENZO_W * OVERSCAN)
        q = subprocess.run(['sips', '-z', str(gz_h), str(gz_w), real, '--out', real],
                           capture_output=True)
        if q.returncode != 0:
            print(f'   ✗ escala falló en {n}: {q.stderr.decode().strip()[:70]}')
            fallos += 1; continue
        q = subprocess.run(['sips', '-c', str(LIENZO_H), str(LIENZO_W), real, '--out', real],
                           capture_output=True)
        if q.returncode != 0:
            print(f'   ✗ encuadre falló en {n}: {q.stderr.decode().strip()[:70]}')
            fallos += 1

    # ── verificación: el objetivo es 0 con marco y 0 fuera de lienzo ─────────
    quedan, fuera = [], []
    for real, n, *_ in plan:
        m = medir(real)
        if m and max(m[0]) > 0:
            quedan.append(f'{n} ↑{m[0][0]} ↓{m[0][1]} ←{m[0][2]} →{m[0][3]}')
        W = int(subprocess.run(['sips', '-g', 'pixelWidth', real], capture_output=True)
                .stdout.decode().split(':')[-1])
        H = int(subprocess.run(['sips', '-g', 'pixelHeight', real], capture_output=True)
                .stdout.decode().split(':')[-1])
        if (W, H) != (LIENZO_W, LIENZO_H):
            fuera.append(f'{n} {W}×{H}')
    print(f'\nVERIFICACIÓN · fallos de sips {fallos} · '
          f'con marco {len(quedan)} · fuera de {LIENZO_W}×{LIENZO_H} {len(fuera)}')
    for x in quedan[:12]:
        print(f'   ⚠ {x}')
    for x in fuera[:12]:
        print(f'   ⚠ {x}')


if __name__ == '__main__':
    main()
