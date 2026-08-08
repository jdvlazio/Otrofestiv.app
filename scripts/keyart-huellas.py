#!/usr/bin/env python3
"""keyart-huellas.py — regenera el registro de huellas de los keyArt.

POR QUÉ EXISTE (8 ago 2026)
El Service Worker cachea `/assets/` cache-first, en un caché que sobrevive a
todos los deploys (`ASSETS_CACHE`). Un keyArt es por eso WRITE-ONCE:
sobreescribirlo in-place deja a los usuarios recurrentes viendo el afiche viejo
PARA SIEMPRE. Ni siquiera reinstalar la app alcanza — el caché del WebView
persiste.

La regla estaba escrita en tres lugares (`src/config.js`, `compose-keyart.py`,
`docs/PIPELINE.md`) y aun así el afiche de FICDEH 2026 se sobreescribió cuatro
veces con el mismo nombre. El aliado de comunicaciones en Medellín seguía viendo
el afiche anterior a cuatro días de que abriera el festival. Una regla que solo
vive en la documentación no se cumple: por eso ahora hay una huella por archivo
y el guardián `[keyart-write-once]` la verifica en cada push.

USO
    python3 scripts/keyart-huellas.py          # regenera tras publicar un -vN
    python3 scripts/keyart-huellas.py --check  # solo compara, no escribe
"""
import glob
import hashlib
import os
import sys

REG = 'assets/keyart/HUELLAS.txt'
CABECERA = """# Huella de cada keyArt PUBLICADO — no editar a mano.
#
# El Service Worker cachea /assets/ cache-first en un caché que sobrevive a todos
# los deploys, así que un keyArt es WRITE-ONCE: sobreescribirlo in-place deja a
# los usuarios recurrentes viendo el afiche viejo PARA SIEMPRE, sin arreglo desde
# la app (reinstalar tampoco basta: el caché del WebView persiste).
#
# Pasó con FICDEH 2026: el afiche se sobreescribió 4 veces con el mismo nombre y
# el aliado de comunicaciones en Medellín seguía viendo el anterior a 4 días de
# que abriera el festival.
#
# Para cambiar un afiche: `python3 scripts/compose-keyart.py <archivo>` escribe a
# -v2/-v3, se actualiza el path en src/config.js y se regenera este archivo con
# `python3 scripts/keyart-huellas.py`.
"""


def huellas():
    return {os.path.basename(f): hashlib.sha1(open(f, 'rb').read()).hexdigest()[:16]
            for f in sorted(glob.glob('assets/keyart/*.jpg'))}


def leer():
    if not os.path.exists(REG):
        return {}
    out = {}
    for ln in open(REG, encoding='utf-8'):
        ln = ln.strip()
        if ln and not ln.startswith('#'):
            h, n = ln.split(None, 1)
            out[n] = h
    return out


def main():
    solo_check = '--check' in sys.argv
    ahora, antes = huellas(), leer()
    cambiados = [n for n, h in ahora.items() if n in antes and antes[n] != h]
    if cambiados:
        print('✗ keyArt SOBREESCRITO (write-once): ' + ', '.join(cambiados))
        print('  Usá un nombre nuevo: python3 scripts/compose-keyart.py assets/keyart/<archivo>')
        if solo_check:
            return 1
    nuevos = [n for n in ahora if n not in antes]
    if solo_check:
        print(f'✓ {len(ahora)} keyArt sin cambios' if not cambiados else '')
        return 0
    open(REG, 'w', encoding='utf-8').write(
        CABECERA + '\n'.join(f'{h}  {n}' for n, h in sorted(ahora.items())) + '\n')
    print(f'✅ {len(ahora)} huellas registradas' + (f' · {len(nuevos)} nueva(s): {", ".join(nuevos)}' if nuevos else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
