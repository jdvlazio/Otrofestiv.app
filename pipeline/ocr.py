# -*- coding: utf-8 -*-
"""ocr.py — el texto PINTADO de una imagen, cacheado.

POR QUÉ. En Instagram —la fuente donde más festivales publican su programación
antes que en su web— el dato no está en el pie: está DENTRO de la imagen. Una
lámina de carrusel trae título, dirección, país, año, sede, hora y a veces el
conversatorio, todo pintado. Mirarlas a ojo no escala (42 en #NarrarElFuturo) y
la que no se mira es justo la que falta.

CÓMO. El OCR del sistema (Vision, macOS), que no hay que instalar y lee español.
Se cachea por hash del archivo: una lámina se lee UNA vez aunque el parser se
re-corra veinte veces, que es lo que hace re-corrible un pipeline.

Uso:
    from ocr import leer
    leer(['a.jpg', 'b.jpg'])    # → {'a.jpg': ['línea', …], …}
"""
import hashlib, io, json, os, subprocess, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SWIFT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ocr.swift')
CACHE = f'{REPO}/fuentes/_ocr'


def _huella(p):
    h = hashlib.sha1()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(65536), b''):
            h.update(b)
    return h.hexdigest()[:16]


def leer(rutas, forzar=False):
    """{ruta: [líneas]} — el texto de cada imagen, leyendo solo lo que falte."""
    out, pendientes = {}, []
    os.makedirs(CACHE, exist_ok=True)
    for p in rutas:
        if not os.path.exists(p):
            continue
        c = f'{CACHE}/{_huella(p)}.json'
        if os.path.exists(c) and not forzar:
            out[p] = json.load(io.open(c, encoding='utf-8'))['lineas']
        else:
            pendientes.append((p, c))
    if pendientes:
        # una sola invocación: `swift` compila en cada llamada
        r = subprocess.run([ 'swift', SWIFT] + [p for p, _ in pendientes],
                           capture_output=True, text=True)
        leidas = {}
        for linea in (r.stdout or '').splitlines():
            if linea.startswith('{'):
                d = json.loads(linea)
                leidas[d['ruta']] = d['lineas']
        for p, c in pendientes:
            lin = leidas.get(p, [])
            io.open(c, 'w', encoding='utf-8').write(
                json.dumps({'origen': p, 'lineas': lin}, ensure_ascii=False, indent=1) + '\n')
            out[p] = lin
        if not leidas and r.returncode:
            print(f'⚠ ocr: swift falló ({r.returncode}) — {(r.stderr or "")[:120]}', file=sys.stderr)
    return out


if __name__ == '__main__':
    for p, lin in leer(sys.argv[1:]).items():
        print(f'── {os.path.basename(p)}')
        for x in lin:
            print('   ', x)
