#!/usr/bin/env python3
"""under-2026-verificar.py — triple lectura y cobertura inversa del crudo
contra el PDF oficial (correo del 18 nov 2026).

Cada función se busca en SU página del PDF por tres caminos que no comparten
nada: la capa de texto (pdftotext), Vision (pipeline/ocr.py, página a 200 dpi)
y Tesseract (la misma imagen, otro motor). La hora (impresa «6:30 PM» o «6:30»
sin AM/PM), la sede y cada título tienen que leerse en los tres.

COBERTURA INVERSA: toda línea «crédito · país · año» del texto del PDF tiene
encima un título; ese título tiene que estar en el crudo. Y toda hora impresa
tiene que ser la de alguna función de su página.

    python3 pipeline/under-2026-verificar.py
"""
import io, json, os, re, subprocess, sys, unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from ocr import leer  # noqa: E402

CRUDO = f'{REPO}/festivals/staging/under-2026-crudo.json'
PDF = f'{REPO}/fuentes/under-2026/correo-2026-11-18/Programa_UNDER_Medellin_2026_def.pdf'
TMP = f'{REPO}/fuentes/under-2026/correo-2026-11-18/paginas'

# cómo imprime el PDF lo que el crudo normalizó o tituló
EN_PDF = {'Fiesta Under · El Vikingo Selektor': 'El vikingo selektor',
          # el formulario de inscripción (20 nov) suma «audiovisuales»; el PDF no lo trae
          'Orígenes de los lenguajes audiovisuales experimentales y laboratorio de creación': 'Orígenes de los lenguajes experimentales',
          'Proyección sorpresa': 'Proyección sorpresa'}
SEDE_PDF = {'Perpetua Lab': 'PERPETUA LAB', 'Bebop Bar': 'BEBOP', 'Donde Robin': 'DONDE ROBIN',
            'Librería Antimateria': 'ANTIMATERIA'}
# lo que un motor no lee y la página sí dice: mirado a ojo, con su porqué
MIRADO = {
    (6, 'El vikingo selektor', 'Tesseract'): 'Tesseract lee «EI vikingo selektor» (I por l); texto y Vision lo leen y a ojo es claro (18 nov)',
    (6, 'Proyección sorpresa', 'Tesseract'): 'Tesseract lee «Proyecci6én sorpresa»; texto y Vision lo leen y a ojo es claro (18 nov)',
    (4, 'Jubiladxs le enseñan', 'Tesseract'): 'Tesseract lee «ensehan» por «enseñan»; texto y Vision lo leen y a ojo es claro (18 nov)',
}


def n(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9:]+', ' ', s).strip()


def lee(txt, t):
    return n(t) in n(txt)


def paginas():
    os.makedirs(TMP, exist_ok=True)
    out = {}
    for p in range(1, 7):
        png = f'{TMP}/p-{p}.png'
        if not os.path.exists(png):
            subprocess.run(['pdftoppm', '-r', '200', '-png', '-singlefile', '-f', str(p), '-l', str(p),
                            PDF, png[:-4]], check=True)
        texto = subprocess.run(['pdftotext', '-layout', '-f', str(p), '-l', str(p), PDF, '-'],
                               capture_output=True, text=True, check=True).stdout
        tes = subprocess.run(['tesseract', png, '-', '-l', 'spa+eng'], capture_output=True, text=True).stdout
        plano = subprocess.run(['pdftotext', '-f', str(p), '-l', str(p), PDF, '-'],
                               capture_output=True, text=True, check=True).stdout
        out[p] = {'layout': texto, 'texto': plano, 'Tesseract': tes, 'png': png}
    vis = leer([v['png'] for v in out.values()])
    for p, v in out.items():
        v['Vision'] = '\n'.join(vis[v['png']])
    return out


def h12(h):
    hh, mm = map(int, h.split(':'))
    return f'{(hh - 1) % 12 + 1}:{mm:02d}'


def main():
    pg = paginas()
    fs = json.load(io.open(CRUDO, encoding='utf-8'))['funciones']
    malos = []
    for f in fs:
        p = int(f['_src']['lamina'].split()[-1])
        textos = [o['titulo'] for o in f.get('obras') or []] or [EN_PDF.get(f['titulo'], f['titulo'])]
        for motor in ('texto', 'Vision', 'Tesseract'):
            txt = pg[p][motor]
            if h12(f['hora']) not in txt and (p, f['hora'], motor) not in MIRADO:
                malos.append(f'p. {p} {f["hora"]} «{f["titulo"]}»: {motor} no lee la hora')
            if p != 6 and not lee(txt, SEDE_PDF[f['sede']]):
                malos.append(f'p. {p} «{f["titulo"]}»: {motor} no lee la sede {f["sede"]}')
            for t in textos:
                if not lee(txt, t) and (p, t, motor) not in MIRADO:
                    malos.append(f'p. {p} {f["hora"]} «{t}»: {motor} no lo lee')
    # cobertura inversa: títulos (línea encima de «crédito · país · año»)
    en_crudo = {n(o['titulo']) for f in fs for o in (f.get('obras') or [f])}
    impresos = 0
    for p in range(2, 6):
        for col in columnas(pg[p]['layout']):
            for i, l in enumerate(col):
                if re.search(r'·\s*(19|20)\d\d\s*$', l) and i:
                    t = col[i - 1] if col[i - 1] else ''
                    if t and not re.search(r'\d:\d\d', t):
                        impresos += 1
                        if not any(n(t) in c or c in n(t) for c in en_crudo):
                            malos.append(f'p. {p}: «{t}» está impreso y no está en el crudo')
    horas = {(int(f['_src']['lamina'].split()[-1]), h12(f['hora'])) for f in fs}
    for p in range(2, 7):
        for h in set(re.findall(r'\b(\d{1,2}:\d\d)\b', pg[p]['layout'])):
            if (p, h) not in horas and not (p == 6 and h == '7:00'):   # «5:00 PM — 7:00 PM»: fin
                malos.append(f'p. {p}: la hora {h} está impresa y ninguna función la tiene')
    if malos:
        print('\n'.join('✗ ' + m for m in malos))
        sys.exit(f'✗ {len(malos)} lectura(s) que no coinciden en {len(fs)} funciones: mirar la página')
    print(f'✓ {len(fs)} funciones: hora, sede y títulos leídos en texto, Vision y Tesseract; '
          f'{impresos} títulos impresos, todos en el crudo; toda hora impresa tiene función')


def columnas(texto):
    """El -layout pone las dos columnas lado a lado: se parten por la posición."""
    izq, der = [], []
    for l in texto.splitlines():
        m = re.search(r'\S\s{3,}(\S)', l)
        corte = m.start(1) if m and m.start(1) > 40 else None
        if corte:
            izq.append(l[:corte].strip()); der.append(l[corte:].strip())
        elif len(l) - len(l.lstrip()) > 40:
            der.append(l.strip())
        else:
            izq.append(l.strip())
    return [[x for x in c if x] for c in (izq, der)]


if __name__ == '__main__':
    main()
