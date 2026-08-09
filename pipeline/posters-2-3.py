# -*- coding: utf-8 -*-
"""posters-2-3.py <fest-id> [--aplicar] — los pósters al 2:3 exacto, ESTIRANDO.

Regla de Juan, la misma que ya rige el afiche del splash (scripts/compose-
keyart.py): cuando una imagen no es 2:3 se ESTIRA en un eje hasta serlo. No se
recorta, no se rellena con bandas, no se difumina.

Por qué importa en los pósters: las cards y la ficha son 2:3 con
`object-fit:cover`, así que todo póster que no lo sea pierde contenido por el
lado largo — y en los bordes de algunas superficies deja hueco. Estirar un 3–5%
no se percibe (probado con afiches reales en el keyArt) y garantiza que se vea
el afiche COMPLETO en cualquier superficie.

Sin umbral: se estira siempre que el desvío pase de 0,5%. Una regla simple que
no hay que recordar cuándo aplicar.

Usa sips (macOS): `-z alto ancho` reescala sin conservar proporción, que es
exactamente lo que se quiere aquí.
"""
import json, os, struct, subprocess, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOL = 0.005


def dim(p):
    d = open(p, 'rb').read(); i = 2
    while i < len(d):
        if d[i] != 0xFF:
            i += 1; continue
        m = d[i+1]
        if m in (0xC0, 0xC1, 0xC2, 0xC3):
            h, w = struct.unpack('>HH', d[i+5:i+9]); return w, h
        if m == 0xD8 or 0xD0 <= m <= 0xD7:
            i += 2; continue
        i += 2 + struct.unpack('>H', d[i+2:i+4])[0]
    return None


def main():
    fid = sys.argv[1] if len(sys.argv) > 1 else sys.exit(
        'uso: python3 pipeline/posters-2-3.py <fest-id> [--aplicar]')
    aplicar = '--aplicar' in sys.argv
    d = json.load(open(f'{REPO}/festivals/{fid}.json', encoding='utf-8'))
    vistos, tocados, saltados = set(), [], []
    for f in d['films']:
        p = f.get('poster') or ''
        if not p.startswith('/assets/') or p in vistos:
            continue
        vistos.add(p)
        real = REPO + p
        if not os.path.exists(real):
            continue
        # El still 16:9 de un `posterSource:editorial` NO va a 2:3: su marco lo
        # enmarca a 16/9 a propósito (docs/POSTERS.md §4). Estirarlo sería
        # deformar una imagen que la app ya sabe encuadrar.
        if f.get('posterSource') == 'editorial':
            saltados.append(os.path.basename(p)); continue
        wh = dim(real)
        if not wh:
            continue
        w, h = wh
        if abs(w / h - 2 / 3) <= TOL:
            continue
        nuevo_h = round(w * 3 / 2)
        tocados.append((os.path.basename(p), f'{w}×{h} (r={w/h:.3f}) → {w}×{nuevo_h}'))
        if aplicar:
            r = subprocess.run(['sips', '-z', str(nuevo_h), str(w), real, '--out', real],
                               capture_output=True)
            if r.returncode != 0:
                print(f'   ✗ sips falló en {os.path.basename(p)}: '
                      f'{r.stderr.decode().strip()[:80]}')
    print(f'{len(vistos)} pósters · fuera de 2:3 {len(tocados)}'
          + (f' · editorial 16:9 respetados {len(saltados)}' if saltados else '')
          + ('  (APLICADO)' if aplicar else '  (simulación — usar --aplicar)'))
    for n, msg in tocados:
        print(f'   {n[:52]:54} {msg}')


if __name__ == '__main__':
    main()
