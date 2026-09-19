#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""villadelcine-2026-contraste.py — el mismo PDF leído por OTRO motor, y comparado.

POR QUÉ (19 sep 2026). `villadelcine-2026-programa-pdf.py` saca la parrilla con
poppler (`pdftotext -bbox-layout`) para el texto y con PIL —segmentando los
píxeles de la página renderizada— para los rectángulos de las celdas. Los dos
chequeos que ya existen, el verificador y la cobertura, comprueban que ESA
lectura sea coherente consigo misma. Ninguno la compara con nada de afuera, y
una lectura puede ser perfectamente coherente y estar mal: el error de la hora
de fin —una fila corrida en los 53 bloques— pasó los dos.

QUÉ HACE. Vuelve a extraer el PDF con **PyMuPDF (MuPDF)**, que no comparte una
línea de código con poppler ni con PIL, y por los dos lados donde puede
equivocarse el original:

  · EL TEXTO, con sus cajas, de `page.get_text("dict")`.
  · LOS RECTÁNGULOS DE LAS CELDAS, de `page.get_drawings()` — que son los
    VECTORES que el PDF dibuja, no una interpretación de los píxeles. Es el
    contraste que de verdad importa: si MuPDF lee el mismo rectángulo que PIL
    adivinó en la imagen, las horas están bien por dos caminos.

Y COMPARA, bloque a bloque, contra `villadelcine-2026-parrilla.json`: día,
hora, hora de fin, sede y texto. Lo que no coincida se imprime; si algo no
coincide, sale con 1.

NECESITA PyMuPDF, que no está en el sistema y no tiene por qué estarlo —es
para contrastar, no para producir—:

    python3 -m venv /tmp/vdcenv && /tmp/vdcenv/bin/pip install pymupdf
    /tmp/vdcenv/bin/python pipeline/villadelcine-2026-contraste.py
"""
import json, os, re, sys, unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF = f'{REPO}/fuentes/villadelcine-2026/programacion-2026.pdf'
PAR = f'{REPO}/festivals/staging/villadelcine-2026-parrilla.json'
PAGS = list(range(2, 12))

try:
    import pymupdf
except ImportError:
    sys.exit(__doc__.split('NECESITA')[1])

# «12:00 m» es el mediodía y no lleva a/p. Sin este caso al contraste le faltaba
# una fila entera, y la primera diferencia que encontró —tres bloques corridos
# quince minutos— era suya y no del dato. Un contraste también se verifica.
RE_HORA = re.compile(r'^(\d{1,2}):(\d{2})\s*([ap0o])?\.?\s*m\.?$', re.I)
# MuPDF agrupa las líneas distinto que poppler: el día puede venir «23
# MIÉRCOLES» o suelto («26» por un lado y «SÁBADO» por otro). Se ancla al
# número, que es lo único estable, y a que vive en la banda de cielo.
RE_DIA = re.compile(r'^(\d{1,2})(\s+[A-ZÁÉÍÓÚ/ ]+)?$')
Y_CIELO = 65          # por encima de esto va la cabecera de marca, no la tabla
MARCA = re.compile(r'^(12|FESTIVAL|VILLA|DEL CINE|Septiembre|Lugar|Hora|caminos|del|'
                   r'tiempo|MAÑANA|TARDE|NOCHE|TARDE/NOCHE|LUNES|MARTES|MIÉRCOLES|'
                   r'JUEVES|VIERNES|SÁBADO|DOMINGO)$', re.I)


def norm(s):
    s = ''.join(c for c in unicodedata.normalize('NFD', s or '')
                if unicodedata.category(c) != 'Mn').lower()
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def hora24(t, ap_previo=''):
    m = RE_HORA.match(t.strip())
    if not m:
        return ''
    # OJO con `ap not in 'ap'`: la cadena vacía está contenida en cualquier
    # cadena, así que esa prueba da False para el mediodía y lo dejaba sin
    # marca —«12:00 m» salía como 00:00—. Se compara contra una lista.
    ap = (m.group(3) or '').lower()
    if ap not in ('a', 'p'):
        ap = 'p' if m.group(1) == '12' else (ap_previo or 'p')
    return f'{int(m.group(1)) % 12 + (12 if ap == "p" else 0):02d}:{m.group(2)}'


def lineas_mupdf(page):
    """[(x0, y0, x1, y1, texto)] — una entrada por línea, como las ve MuPDF."""
    out = []
    for b in page.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            t = ''.join(s['text'] for s in l['spans']).strip()
            t = re.sub(r'\s+', ' ', t)
            if t:
                x0, y0, x1, y1 = l['bbox']
                out.append((x0, y0, x1, y1, t))
    return out


def celdas_mupdf(page, y_min):
    """Los rectángulos RELLENOS de la página: las celdas, en vectores.

    Se descarta lo que no es una celda: lo que no tiene relleno, la banda de
    cielo de la cabecera (por altura), las líneas (muy finas) y los rellenos
    sin tono, que son la retícula y no contenido.
    """
    out = []
    for d in page.get_drawings():
        f = d.get('fill')
        if not f or d.get('type') not in ('f', 'fs'):
            continue
        r = d['rect']
        if r.y0 < y_min or r.width < 24 or r.height < 8:
            continue
        if max(f) - min(f) <= 0.05:        # gris o blanco: retícula, no celda
            continue
        out.append((round(r.x0, 1), round(r.y0, 1), round(r.x1, 1), round(r.y1, 1)))
    # dos rectángulos superpuestos son el mismo relleno partido
    out.sort()
    fus, cambio = list(out), True
    while cambio:
        cambio = False
        for i in range(len(fus)):
            for j in range(i + 1, len(fus)):
                a, b = fus[i], fus[j]
                an, al = min(a[2], b[2]) - max(a[0], b[0]), min(a[3], b[3]) - max(a[1], b[1])
                menor = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))
                if an > 0 and al > 0 and an * al > 0.25 * menor:
                    fus[i] = (min(a[0], b[0]), min(a[1], b[1]),
                              max(a[2], b[2]), max(a[3], b[3]))
                    del fus[j]
                    cambio = True
                    break
            if cambio:
                break
    return fus


def main():
    doc = pymupdf.open(PDF)
    nuestros = json.load(open(PAR, encoding='utf-8'))['bloques']
    suyos, dif = [], []

    for pag in PAGS:
        page = doc[pag - 1]
        ls = lineas_mupdf(page)
        horas, ap = [], ''
        for x0, y0, x1, y1, t in sorted(ls, key=lambda l: l[1]):
            h = hora24(t, ap)
            if h:
                horas.append(((y0 + y1) / 2, h))
                ap = 'a' if h < '12:00' else 'p'
        if not horas:
            dif.append(f'p{pag}: MuPDF no encontró ninguna fila de hora')
            continue
        horas.sort()
        dia = next((f'2026-09-{int(RE_DIA.match(t).group(1)):02d}'
                    for x0, y0, x1, y1, t in ls
                    if y1 < Y_CIELO and x0 > 440 and RE_DIA.match(t)), '')
        # columnas: la cabecera, arriba de la primera hora
        cab = [l for l in ls if Y_CIELO < l[3] < horas[0][0] - 8 and l[0] > 88
               and not MARCA.match(l[4]) and not RE_DIA.match(l[4]) and not hora24(l[4])]
        cols = []
        for x0, y0, x1, y1, t in sorted(cab, key=lambda l: (l[0], l[1])):
            for c in cols:
                if min(x1, c['x1']) - max(x0, c['x0']) > 0.4 * min(x1 - x0, c['x1'] - c['x0']):
                    c['partes'].append((y0, t))
                    c['x0'], c['x1'] = min(c['x0'], x0), max(c['x1'], x1)
                    break
            else:
                cols.append({'x0': x0, 'x1': x1, 'partes': [(y0, t)]})
        cols = [{'x0': c['x0'], 'x1': c['x1'],
                 'nombre': ' '.join(t for _, t in sorted(c['partes']))} for c in cols]

        LINEA = 6.4
        filas = [(c - LINEA, h) for c, h in horas]
        rot = lambda y: min(filas, key=lambda f: abs(f[0] - y))[1]
        for x0, y0, x1, y1 in celdas_mupdf(page, horas[0][0] - 10):
            cx = (x0 + x1) / 2
            sede = next((c['nombre'] for c in cols if c['x0'] - 14 <= cx <= c['x1'] + 14), '')
            if not sede:
                continue
            dentro = [t for lx0, ly0, lx1, ly1, t in ls
                      if x0 - 3 <= (lx0 + lx1) / 2 <= x1 + 3
                      and y0 - 5 <= (ly0 + ly1) / 2 <= y1 + 7
                      and not MARCA.match(t) and not hora24(t) and not RE_DIA.match(t)]
            suyos.append({'dia': dia, 'pagina': pag, 'sede': sede,
                          'hora': rot(y0), 'hasta': rot(y1), 'lineas': dentro})

    # ── la comparación ──────────────────────────────────────────────────────
    def clave(b):
        return (b['dia'], b['sede'], b['hora'])

    mios = {clave(b): b for b in nuestros}
    otros = {clave(b): b for b in suyos if b['lineas']}
    print(f'poppler+PIL: {len(nuestros)} bloques · MuPDF (vectores): {len(otros)} bloques')

    for k in sorted(set(mios) | set(otros)):
        a, b = mios.get(k), otros.get(k)
        if not b:
            # un bloque que unimos entre páginas no tiene pareja exacta: MuPDF
            # ve los dos trozos por separado, que es lo que el PDF dibuja.
            if a.get('_partido') or a.get('_empieza_antes'):
                continue
            if any(norm(' '.join(a['lineas'])) == norm(' '.join(o['lineas']))
                   for o in suyos):
                continue
            dif.append(f'solo en la nuestra: {k[0][-2:]} {k[2]} {k[1][:26]} '
                       f'«{" ".join(a["lineas"])[:34]}»')
        elif not a:
            if any(norm(' '.join(b['lineas'])) == norm(' '.join(m['lineas']))
                   or (m.get('_partido') or m.get('_empieza_antes'))
                   and norm(' '.join(b['lineas'])) in norm(' '.join(m['lineas']))
                   for m in nuestros):
                continue
            dif.append(f'solo en MuPDF:     {k[0][-2:]} {k[2]} {k[1][:26]} '
                       f'«{" ".join(b["lineas"])[:34]}»')
        else:
            if a['hasta'] != b['hasta'] and not a.get('_partido') \
                    and not a.get('_empieza_antes'):
                dif.append(f'hora de fin distinta: {k[0][-2:]} {k[2]} {k[1][:22]} — '
                           f'nuestra {a["hasta"]}, MuPDF {b["hasta"]}')
            if a.get('_partido') or a.get('_empieza_antes'):
                continue
            if norm(' '.join(a['lineas'])) != norm(' '.join(b['lineas'])):
                dif.append(f'texto distinto: {k[0][-2:]} {k[2]} {k[1][:20]}\n'
                           f'       nuestra: {" / ".join(a["lineas"])[:70]}\n'
                           f'       MuPDF  : {" / ".join(b["lineas"])[:70]}')

    if dif:
        print(f'\n✗ {len(dif)} diferencia(s) entre los dos motores:')
        for x in dif:
            print('   ✗', x)
        sys.exit(1)
    print('\n✓ los dos motores leen la misma parrilla: día, hora, fin, sede y texto')


if __name__ == '__main__':
    main()
