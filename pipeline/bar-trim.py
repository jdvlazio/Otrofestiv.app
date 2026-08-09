# -*- coding: utf-8 -*-
"""bar-trim.py <fest-id> [--aplicar] — el recorte obligatorio de POSTERS.md §3.

Los afiches llegan «dentro de un diseño»: márgenes blancos del festival, barras
negras de centrado, marcos. La doctrina (docs/POSTERS.md §3) manda recortarlos
antes de hospedarlos — «como si fuera el original» — y el paso se venía haciendo
a ojo, festival por festival. En FICMA no se hizo: cuatro pósters entraron con
marco blanco de 12–18 px arriba y abajo, visible en la card.

Detecta bordes uniformes CLAROS (>235) y OSCUROS (<20) — un trim que solo quita
blanco deja barras negras (caso Chiribiquete, FICMontañas) — y solo recorta lo
que es de verdad un borde: filas planas (poca varianza a lo ancho) y hasta un
25% de la imagen por lado. Sin --aplicar solo informa.

Usa sips (macOS) para leer y recortar: nada que instalar.
"""
import json, os, re, subprocess, sys, tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Un MARCO es fino: 12–18 px sobre 1115 (~1,5%). Un área grande y clara es ARTE
# —el cielo de «The Dig», el fondo de «Vinyl Nation»— y recortarla arruina el
# afiche. De ahí el tope del 5% por lado: la diferencia entre quitar un borde y
# comerse la imagen. PLANO 40 y no 12 porque un margen impreso tiene textura.
CLARO, OSCURO, PLANO, MAX_FRAC = 235, 20, 40, 0.05


def pixels(path):
    """→ (w, h, filas) con filas[y] = lista de (r,g,b) muestreados a lo ancho.
    Se pasa por PNG chico: basta para detectar bordes, y evita dependencias."""
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as t:
        tmp = t.name
    subprocess.run(['sips', '-s', 'format', 'png', '-Z', '400', path, '--out', tmp],
                   capture_output=True)
    import zlib, struct
    d = open(tmp, 'rb').read()
    os.unlink(tmp)
    pos, w, h, idat, bits = 8, 0, 0, b'', 8
    while pos < len(d):
        ln = struct.unpack('>I', d[pos:pos+4])[0]; tipo = d[pos+4:pos+8]
        if tipo == b'IHDR':
            w, h, bits, color = struct.unpack('>IIBB', d[pos+8:pos+18])
            if color != 2 and color != 6:
                return None
            canales = 3 if color == 2 else 4
        elif tipo == b'IDAT':
            idat += d[pos+8:pos+8+ln]
        pos += 12 + ln
    raw = zlib.decompress(idat)
    stride = w * canales
    filas, prev = [], bytearray(stride)
    i = 0
    for y in range(h):
        f = raw[i]; linea = bytearray(raw[i+1:i+1+stride]); i += 1 + stride
        for x in range(stride):                       # des-filtrado PNG
            a = linea[x-canales] if x >= canales else 0
            b = prev[x]; c = prev[x-canales] if x >= canales else 0
            if f == 1: linea[x] = (linea[x] + a) & 255
            elif f == 2: linea[x] = (linea[x] + b) & 255
            elif f == 3: linea[x] = (linea[x] + (a + b) // 2) & 255
            elif f == 4:
                p = a + b - c; pa, pb, pc = abs(p-a), abs(p-b), abs(p-c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                linea[x] = (linea[x] + pr) & 255
        filas.append([(linea[x], linea[x+1], linea[x+2])
                      for x in range(0, stride, canales * max(1, w // 60))])
        prev = linea
    return w, h, filas


def borde(filas, desde_arriba=True):
    """Cuántas filas de borde uniforme (claras u oscuras) hay por ese lado."""
    orden = filas if desde_arriba else filas[::-1]
    n, tope = 0, max(2, int(len(filas) * MAX_FRAC))
    for f in orden:
        lum = [sum(p) / 3 for p in f]
        media = sum(lum) / len(lum)
        plano = (max(lum) - min(lum)) < PLANO
        if plano and (media > CLARO or media < OSCURO):
            n += 1
            if n >= tope:
                # La zona clara SIGUE más allá del tope: no es un marco, es arte
                # —el cielo de «The Dig», el fondo de «Vinyl Nation»—. Un marco
                # TERMINA solo; el arte continúa. Se devuelve 0: no se toca.
                return 0
        else:
            break
    return n


def main():
    fid = sys.argv[1] if len(sys.argv) > 1 else sys.exit('uso: bar-trim.py <fest-id> [--aplicar]')
    aplicar = '--aplicar' in sys.argv
    d = json.load(open(f'{REPO}/festivals/{fid}.json', encoding='utf-8'))
    vistos, tocados = set(), []
    for f in d['films']:
        p = f.get('poster') or ''
        # el prefijo sale del dato, no del id: FICMA usa /assets/ficma/ con
        # fest-id «ficma-2026», y suponerlo daba 0 pósters en silencio.
        if not p.startswith('/assets/') or p in vistos:
            continue
        vistos.add(p)
        real = REPO + p
        if not os.path.exists(real):
            continue
        px = pixels(real)
        if not px:
            continue
        w, h, filas = px
        t, b = borde(filas, True), borde(filas, False)
        if min(t, b) < 2:                   # el marco debe estar en AMBOS lados
            continue
        # escalar al tamaño original y recortar
        W = int(subprocess.run(['sips', '-g', 'pixelWidth', real], capture_output=True)
                .stdout.decode().split(':')[-1])
        H = int(subprocess.run(['sips', '-g', 'pixelHeight', real], capture_output=True)
                .stdout.decode().split(':')[-1])
        rt, rb = round(t * H / h), round(b * H / h)
        # Se recorta lo MISMO por los dos lados, usando el menor. sips recorta
        # desde el centro y no acepta offset negativo —lo lee como bandera y
        # aborta—, así que un marco asimétrico fallaba en silencio (habitante:
        # 14 arriba, 17 abajo → offset −1 → sips error → póster sin tocar).
        # Simétrico es además más seguro: nunca se come imagen, y deja como
        # mucho unos pocos px de marco en el lado más grueso.
        rt = rb = min(rt, rb)
        nuevo_h = H - rt - rb
        tocados.append((os.path.basename(p), f'{H}px → {nuevo_h}px (arriba {rt}, abajo {rb})'))
        if aplicar:
            r = subprocess.run(['sips', '-c', str(nuevo_h), str(W), real, '--out', real],
                               capture_output=True)
            if r.returncode != 0:                     # nunca más en silencio
                print(f'   ✗ sips falló en {os.path.basename(p)}: '
                      f'{r.stderr.decode().strip()[:80]}')
    print(f'{len(vistos)} pósters propios · con marco {len(tocados)}'
          + ('  (APLICADO)' if aplicar else '  (simulación — usar --aplicar)'))
    for n, msg in tocados:
        print(f'   {n[:54]:56} {msg}')


if __name__ == '__main__':
    main()
