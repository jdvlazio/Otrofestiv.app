#!/usr/bin/env python3
"""medellinhorror-2026-verificar.py — el crudo contra sus fuentes, releídas aparte.

  · Los largos: fecha y hora impresas en la pág. 4 de la revista (capa de texto) y
    leídas otra vez con OCR sobre la lámina (pags/hi-04.jpg).
  · Los pases de cortos: cada entrada de la agenda de Comic Con (HTML capturado el
    25 nov). COBERTURA INVERSA: toda entrada "Medellín Horror" tiene función.
  · Los 13 cortos: cada título en la página de selección de la web, y trece pósteres.

    python3 pipeline/medellinhorror-2026-verificar.py
"""
import glob, html, io, json, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import norm  # noqa: E402
from ocr import leer  # noqa: E402

F = f'{REPO}/fuentes/medellinhorror-2026'


def lee(p):
    return io.open(p, encoding='utf-8', errors='ignore').read()


def h12(h):
    hh, mm = map(int, h.split(':'))
    return f'{(hh - 1) % 12 + 1}:{mm:02d}{"AM" if hh < 12 else "PM"}'


def main():
    fs = json.load(io.open(f'{REPO}/festivals/staging/medellinhorror-2026-crudo.json', encoding='utf-8'))['funciones']
    malos = []
    lamina = f'{F}/pags/hi-04.jpg'
    textos = {'texto': lee(f'{F}/revista-01.txt'), 'OCR': ' '.join(leer([lamina])[lamina])}
    rx = r'(\d+)\s*DE\s*NOV\s*(\d+:\d\d)\s*([AP]M)'
    largos = {(int(f['dia'][8:]), h12(f['hora'])) for f in fs if f.get('seccion') == 'Largometrajes'}
    for motor, t in textos.items():
        vistos = {(int(d), h + a) for d, h, a in re.findall(rx, t.upper())}
        if vistos != largos:
            malos.append(f'pág. 4 ({motor}): {sorted(vistos)} ≠ crudo {sorted(largos)}')
    agenda = set()
    for p in glob.glob(f'{F}/25nov/cc*.html'):
        for li in re.findall(r'<li>(.*?)</li>', lee(p), re.S):
            t = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', li)))
            m = re.search(r'(\d+) noviembre \| (\d+):(\d\d) ([AP])M - .*Medellín Horror.*Lugar: (Salón [\w ]+?)\s*$', t)
            if m:
                h = int(m[2]) % 12 + (12 if m[4] == 'P' else 0)
                # ":31" es la franja siguiente a la de ":30": se publica en punto
                agenda.add((int(m[1]), f'{h:02d}:{int(m[3]) // 10 * 10:02d}', m[5]))
    crudo = {(int(f['dia'][8:]), f['hora'], f['sala']) for f in fs if f['_src']['tipo'] == 'sala-agenda'}
    if agenda != crudo:
        malos.append(f'agenda Comic Con {sorted(agenda)} ≠ crudo {sorted(crudo)}')
    web = norm(html.unescape(lee(f'{F}/25nov/seleccion-2026.html')))
    cortos = [o['titulo'] for f in fs for o in f.get('obras') or []]
    for t in cortos:
        if norm(t.split(' / ')[-1]) not in web:
            malos.append(f'"{t}" no está en la selección de la web')
    n = len(glob.glob(f'{F}/web/*.webp'))
    if len(cortos) != n:
        malos.append(f'{len(cortos)} cortos en el crudo, {n} pósteres en la web')
    if malos:
        sys.exit('\n'.join('✗ ' + m for m in malos))
    print(f'✓ {len(largos)} largos (texto y OCR), {len(crudo)} pases (agenda) y {len(cortos)} cortos (web)')


if __name__ == '__main__':
    main()
