#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""ficma-2026-programa-pdf.py — el PDF de programación de septiembre, a OCR.

QUÉ ES. El 18 de septiembre —a un día de abrir— el festival puso en su home un
botón «DESCARGAR PROGRAMACIÓN» que baja un PDF de Google Drive: 78 páginas, una
por función, en formato de post de Instagram. Es la PRIMERA parrilla completa de
la reprogramación; hasta ayer había que armarla post a post.

NO TIENE TEXTO. Lo hizo el «Image Conversion Plug-in» de Acrobat: cada página es
una imagen. `pdftotext` devuelve cero caracteres. Se rasteriza con pdftoppm y se
lee con Vision (macOS), el mismo motor del PDF de agosto.

CON CAJAS, y eso no es un lujo. La plantilla es rígida —póster a la izquierda,
columna de datos a la derecha— y `ficma-2026-parse.py` usa la POSICIÓN de cada
línea para saber qué campo es: sin las cajas, las críticas impresas en el afiche
entran como si fueran el país. Por eso el OCR es el de `ficma-2026-ocr.swift` y
no el genérico de `ocr.py`, que devuelve solo texto.

EL PDF NO SE COMMITEA (24 MB, y `fuentes/` está fuera del repo). Lo que se
versiona es su OCR, que es lo que el parser lee y lo que hace la cadena
re-corrible sin volver a pedirle nada a Drive.

Lee   https://drive.google.com/file/d/<ID>  (el que enlaza laficma.com)
Esc.  festivals/staging/ficma-2026-ocr-septiembre.json
"""
import json, os, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import provenance

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
CACHE = f'{REPO}/fuentes/ficma-2026/programa-septiembre'
SWIFT = f'{REPO}/pipeline/ficma-2026-ocr.swift'
OUT = f'{ST}/ficma-2026-ocr-septiembre.json'

# El id del archivo en Drive, tal como lo enlaza el botón «DESCARGAR
# PROGRAMACIÓN» de laficma.com. Si el festival sube una versión nueva, cambia el
# id: por eso va acá, a la vista, y no escondido en una URL armada.
DRIVE_ID = '1X2Nq3D5K7NaMjXwkROlN1JfYKbGJ__2Z'
DPI = 150   # 1080×1350 en pantalla → suficiente para Vision, y no infla el disco


def baja_pdf():
    p = f'{CACHE}/programacion-ficma17.pdf'
    if not os.path.exists(p) or os.path.getsize(p) < 100000:
        os.makedirs(CACHE, exist_ok=True)
        subprocess.run(['curl', '-sSL', '--retry', '3', '-o', p,
                        f'https://drive.google.com/uc?export=download&id={DRIVE_ID}'],
                       check=True)
    with open(p, 'rb') as f:
        if f.read(5) != b'%PDF-':
            sys.exit(f'{p} no es un PDF — ¿Drive devolvió una página de aviso?')
    return p


def paginas(pdf):
    d = f'{CACHE}/pag'
    if not os.path.isdir(d) or not os.listdir(d):
        os.makedirs(d, exist_ok=True)
        subprocess.run(['pdftoppm', '-r', str(DPI), '-jpeg', '-jpegopt',
                        'quality=85', pdf, f'{d}/p'], check=True)
    return sorted(f'{d}/{x}' for x in os.listdir(d) if x.endswith('.jpg'))


def main():
    pdf = baja_pdf()
    imgs = paginas(pdf)
    if not imgs:
        sys.exit('pdftoppm no dejó ninguna página')
    r = subprocess.run(['swift', SWIFT] + imgs, capture_output=True, text=True)
    if r.returncode or not r.stdout.strip():
        sys.exit(f'el OCR falló ({r.returncode}): {(r.stderr or "")[:200]}')
    lineas = json.loads(r.stdout)

    json.dump({'_provenance': provenance(
        f'PROGRAMACIÓN FICMA 17 (PDF de {len(imgs)} páginas) — botón «DESCARGAR '
        f'PROGRAMACIÓN» de laficma.com, alojado en Google Drive ({DRIVE_ID})',
        que_aporta='la parrilla COMPLETA de la reprogramación: día, hora, sede, '
                   'sección, título, dirección, país, duración, año y el sello de '
                   '«presencia del director» de cada función',
        metodo=f'el PDF es imagen pura (Acrobat Image Conversion): pdftoppm a {DPI} '
               f'dpi + Vision con cajas, porque el parser distingue los campos por '
               f'su POSICIÓN en la plantilla'),
        **lineas},
        open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
    print(f'{len(imgs)} páginas · {sum(len(v) for v in lineas.values())} líneas → '
          f'{os.path.basename(OUT)}')


if __name__ == '__main__':
    main()
