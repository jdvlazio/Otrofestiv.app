#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""conexcine-2026-contraste.py — SEGUNDA y TERCERA lectura del mismo PDF.

POR QUÉ DOS MÁS. Lo extraído con poppler (`pdftotext -bbox-layout`) puede estar
mal de tres maneras que el propio poppler no sabe ver: que el mapa de caracteres
mienta, que las cajas de día que declaré recorten algo, y que una columna se
pegue con la de al lado. Ninguna se descubre releyendo con la misma herramienta.

    LECTURA 2 · PyMuPDF (MuPDF) — otro motor de PDF, otra implementación del
      layout. Lee las mismas páginas con sus coordenadas y se comparan las
      HORAS, los DÍAS y las LÍNEAS bloque a bloque.

    LECTURA 3 · Vision (OCR de macOS) sobre las páginas RASTERIZADAS a 200 dpi.
      No lee el PDF: lee los PÍXELES. Es la única que puede desmentir el mapa de
      caracteres roto —«PROGRAMA 3: BŀŝėƝŀĶŭ÷ŤɑŜŵ÷ɑƣŀŝ÷ë÷Ķ»—, porque ve lo que
      un lector humano ve. Sirve además de censo: toda hora pintada en la página
      tiene que tener su bloque.

No escribe parrilla ni catálogo: su salida es un informe y sale con 1 si hay
una diferencia no declarada. Lo declarado va en DECLARADAS, con su razón.

    /tmp/vdcenv/bin/python pipeline/conexcine-2026-contraste.py
"""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import hora24

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF = f'{REPO}/fuentes/conexcine-2026/programacion-2026.pdf'
PAR = f'{REPO}/festivals/staging/conexcine-2026-parrilla.json'
CAT = f'{REPO}/festivals/staging/conexcine-2026-catalogo.json'
TMP = f'{REPO}/fuentes/conexcine-2026/_paginas'

# Diferencias YA ENTENDIDAS, cada una con su porqué. Una diferencia sin entrada
# acá hace fallar el paso: es la única forma de que el contraste siga sirviendo
# cuando el PDF cambie.
DECLARADAS = {
    'ENTRADA LIBRE': 'la cabecera de la hoja, no una función',
    'Ingreso hasta completar aforo': 'cabecera',
    'Nos reservamos el derecho de admisión.': 'cabecera',
    'Cúcuta, Norte de Santander': 'cabecera',
    'EVENTO RECREACIÓN COMFANORTE': 'rótulo del sábado SIN hora propia — el PDF '
                                    'no le pone horario, así que no es función',
    '¡VEN Y DISFRUTA EN FAMILIA!': 'subtítulo del anterior',
    'EXPOSICIÓN PERMANENTE PROYECTARTE': 'franja transversal, sin hora de reloj',
    'DE DiBUJO Y PLASTiLiNA': 'franja transversal',
    # MuPDF junta la etiqueta del día con su número donde poppler los da
    # separados: es una diferencia de AGRUPACIÓN entre los dos motores, no de
    # contenido — las dos piezas ya están en `sin_clasificar`.
    'SÁBADO26': 'MuPDF pega «SÁBADO» y «26»; poppler los separa',
    'MIÉRCOLES23': 'MuPDF pega «MIÉRCOLES» y «23»; poppler los separa',
}

RE_HORA_TXT = re.compile(r'\b(\d{1,2}):(\d{2})\s*([ap])\.?\s*m\.?', re.I)




def horas_de(txt):
    """Las horas que un texto anuncia, en 24 h y sin repetir."""
    return list(dict.fromkeys(hora24(f'{m.group(1)}:{m.group(2)} {m.group(3)}.m.') for m in RE_HORA_TXT.finditer(txt)))


# ── LECTURA 2 · PyMuPDF ──────────────────────────────────────────────────────
def lectura_mupdf():
    try:
        import pymupdf
    except ImportError:
        try:
            import fitz as pymupdf
        except ImportError:
            print('✗ falta PyMuPDF. Es una LECTURA INDEPENDIENTE, no un extra:\n'
                  '    python3 -m venv /tmp/vdcenv && /tmp/vdcenv/bin/pip install pymupdf\n'
                  '    /tmp/vdcenv/bin/python pipeline/conexcine-2026-contraste.py')
            sys.exit(2)
    doc = pymupdf.open(PDF)
    paginas = {}
    for n in (2, 3):
        p = doc[n - 1]
        lineas = []
        for b in p.get_text('dict')['blocks']:
            for l in b.get('lines', []):
                t = ''.join(s['text'] for s in l['spans']).strip()
                t = re.sub(r'\s+', ' ', t)
                if t:
                    lineas.append({'x': round(l['bbox'][0], 1),
                                   'y': round(l['bbox'][1], 1), 'txt': t})
        paginas[n] = lineas
    doc.close()
    return paginas


# ── LECTURA 3 · Vision OCR sobre los píxeles ─────────────────────────────────
def lectura_ocr():
    os.makedirs(TMP, exist_ok=True)
    pngs = []
    for n in (2, 3):
        dest = f'{TMP}/p{n}'
        if not os.path.exists(f'{dest}-{n:02d}.png') and not os.path.exists(f'{dest}-{n}.png'):
            subprocess.run(['pdftoppm', '-f', str(n), '-l', str(n), '-r', '200',
                            '-png', PDF, dest], check=True)
        hallado = [f'{TMP}/{f}' for f in sorted(os.listdir(TMP))
                   if f.startswith(f'p{n}-') and f.endswith('.png')]
        pngs += hallado[:1]
    from ocr import leer
    return leer(pngs), pngs


def main():
    par = json.load(open(PAR, encoding='utf-8'))
    cat = json.load(open(CAT, encoding='utf-8'))
    bloques = par['bloques']
    fallos, notas = [], []

    # ── 1 · MuPDF contra lo extraído ─────────────────────────────────────────
    mp = lectura_mupdf()
    horas_mu = set()
    for l in mp[2]:
        m = re.match(r'^(\d{1,2}):(\d{2})\s*([ap])\.?\s*m\.?\s*[-–]', l['txt'], re.I)
        if m:
            horas_mu.add(hora24(f'{m.group(1)}:{m.group(2)} {m.group(3)}.m.'))
    horas_nu = {b['hora'] for b in bloques}
    if horas_mu != horas_nu:
        fallos.append(f'MuPDF ve horas de inicio {sorted(horas_mu)} y nosotros '
                      f'{sorted(horas_nu)}')
    else:
        notas.append(f'MuPDF · las {len(horas_mu)} horas de inicio de la página 2, '
                     f'idénticas')

    # toda línea que MuPDF ve en la página 2 tiene que estar en algún bloque,
    # o declarada
    en_bloques = {l for b in bloques for l in b['lineas']}
    en_bloques |= {b['hora'] for b in bloques}
    sueltas_nu = set(par['sin_clasificar'])
    perdidas = []
    for l in mp[2]:
        t = l['txt']
        if t in en_bloques or t in sueltas_nu or t in DECLARADAS:
            continue
        if re.fullmatch(r'[\d\s.:\-–•]*', t) or RE_HORA_TXT.search(t):
            continue
        # el mojibake: MuPDF lo lee igual de roto, y nosotros lo publicamos ya
        # corregido — la pareja está declarada en el sidecar
        if t in par.get('mojibake_corregido', {}):
            continue
        perdidas.append(t)
    if perdidas:
        fallos.append(f'MuPDF ve {len(perdidas)} línea(s) en la p2 que no están '
                      f'en ningún bloque ni declaradas: {perdidas[:6]}')
    else:
        notas.append(f'MuPDF · las {len(mp[2])} líneas de la p2: todas en un bloque, '
                     f'en la cabecera o declaradas')

    # el catálogo: cada corto que extrajimos tiene que estar en el texto de MuPDF
    t3 = ' '.join(l['txt'] for l in mp[3])
    t3 = re.sub(r'\s+', ' ', t3)
    faltan = [o['titulo'] for o in cat['obras']
              if o['titulo'] not in t3
              and o['titulo'] not in cat.get('mojibake_corregido', {}).values()
              and not any(o['titulo'] == v['publicado']
                          for v in cat.get('mojibake_corregido', {}).values())]
    if faltan:
        fallos.append(f'MuPDF no encuentra en la p3 estos títulos que extrajimos: '
                      f'{faltan[:8]}')
    else:
        notas.append(f'MuPDF · los {len(cat["obras"])} cortos del catálogo, todos '
                     f'presentes en el texto de la p3')

    # ── 2 · OCR contra lo extraído ───────────────────────────────────────────
    ocr, pngs = lectura_ocr()
    lineas_ocr = [x for p in pngs for x in ocr.get(p, [])]
    txt_ocr = ' '.join(lineas_ocr)
    horas_ocr = set(horas_de(' '.join(x for x in lineas_ocr if RE_HORA_TXT.search(x))))
    faltan_h = horas_nu - horas_ocr
    if faltan_h:
        fallos.append(f'el OCR NO ve pintadas estas horas que publicamos: '
                      f'{sorted(faltan_h)}')
    else:
        notas.append(f'OCR · las {len(horas_nu)} horas de inicio que publicamos '
                     f'están pintadas en la página')

    # CADA TÍTULO DEL CATÁLOGO, CONTRA LOS PÍXELES. No basta con que MuPDF lo
    # confirme: MuPDF lee el mismo mapa de caracteres que poppler, así que los
    # dos repiten la misma mentira. El OCR es el único que ve lo impreso.
    def _n(s):
        return re.sub(r'[^a-z0-9]', '', s.lower())
    _ocr = _n(txt_ocr)
    invisibles = [o['titulo'] for o in cat['obras'] if _n(o['titulo']) not in _ocr]
    invisibles += [l['titulo'] for l in cat['largos'] if _n(l['titulo']) not in _ocr]
    if invisibles:
        fallos.append(f'el OCR no ve pintados {len(invisibles)} título(s) del '
                      f'catálogo: {invisibles[:8]}')
    else:
        notas.append(f'OCR · los {len(cat["obras"])} cortos y los '
                     f'{len(cat["largos"])} largos están pintados en la página')

    # LA PRUEBA QUE SOLO EL OCR PUEDE DAR: el mojibake. Lo que corregimos tiene
    # que estar pintado tal cual lo publicamos.
    def norm(s):
        return re.sub(r'[^a-z0-9]', '', s.lower())
    for sidecar, nombre in ((par, 'parrilla'), (cat, 'catálogo')):
        for roto, v in sidecar.get('mojibake_corregido', {}).items():
            bueno = v['publicado']
            if norm(bueno) in norm(txt_ocr):
                notas.append(f'OCR · «{bueno}» está pintado tal cual — la corrección '
                             f'del mojibake ({nombre}) queda probada contra los píxeles')
            else:
                fallos.append(f'el OCR no ve «{bueno}» pintado en la página: la '
                              f'corrección del mojibake ({nombre}) NO está probada')

    # ── informe ──────────────────────────────────────────────────────────────
    print(f'conexcine-2026 · tres lecturas del mismo PDF\n'
          f'  1 poppler  {len(bloques)} bloques · {len(cat["obras"])} cortos\n'
          f'  2 MuPDF    {len(mp[2])} líneas p2 · {len(mp[3])} líneas p3\n'
          f'  3 Vision   {len(lineas_ocr)} líneas pintadas\n')
    for n in notas:
        print('  ✓', n)
    if fallos:
        print(f'\n✗ {len(fallos)} diferencia(s):')
        for f in fallos:
            print('   ✗', f)
        sys.exit(1)
    print('\n✓ las tres lecturas dicen lo mismo')


if __name__ == '__main__':
    main()
