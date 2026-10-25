#!/usr/bin/env python3
"""cortoscali-2026-verificar.py — lo que se va a publicar, contra las láminas.

La transcripción es a ojo (staging/cortoscali-2026-ojos.json). Esto la mira por
caminos que no pasan por ella:

  · cada obra del BUILD —título y dirección— se encuentra en el texto que las
    cuatro lecturas de ig-lecturas.py sacaron de SU lámina (basta una lectura
    que la tenga entera; ninguna = fallo), y la hora y el día de la lámina
    también;
  · al revés: cada lámina de programa (02–13, 15) tiene su función en el build,
    y el build no publica nada que no venga de una lámina;
  · segunda fuente: los cuatro posts de selección (13–16 oct) deben nombrar cada
    obra del build; las direcciones que difieren se LISTAN (no fallan: el post
    de programación, del 24 oct, es el más reciente y manda);
  · la sede tiene su pin puesto a mano.
"""
import io
import json
import os
import re
import sys
import unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FID = 'cortoscali-2026'
LECT = f'{REPO}/fuentes/{FID}'
PROG, ACAD = 'De4VP9xkaMd', 'DerpBbZkeSs'
SELECCION = ['Deb8SgNkckw', 'DefFt5bmetD', 'DehIFcKEXMx', 'DekHORfGunw']
MESES = {'27': 'MARTES 27', '28': 'MIÉRCOLES 28', '29': 'JUEVES 29', '30': 'VIERNES 30'}


def n(s):
    s = ''.join(c for c in unicodedata.normalize('NFD', s or '') if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', '', s.lower())


def lecturas(sc):
    p = f'{LECT}/lect-{sc}.json'
    if not os.path.exists(p):
        sys.exit(f'✗ faltan las lecturas de {sc}: python3 pipeline/ig-lecturas.py {sc} --salida {p}')
    d = json.load(io.open(p, encoding='utf-8'))[sc]['lecturas']
    por_lamina = {}
    for lect in d.values():
        if isinstance(lect, dict):
            for lam, txt in lect.items():
                por_lamina.setdefault(lam.split('.')[0], []).append(n(txt))
    return por_lamina


def h12(h):
    a, b = map(int, h.split(':'))
    return f'{(a - 1) % 12 + 1}{b:02d}{"am" if a < 12 else "pm"}'


def main():
    build = json.load(io.open(f'{REPO}/festivals/staging/{FID}-build.json', encoding='utf-8'))
    geo = json.load(io.open(f'{REPO}/festivals/staging/{FID}-venues-geo.json', encoding='utf-8'))
    prog, acad = lecturas(PROG), lecturas(ACAD)
    sel = ''.join(t for sc in SELECCION for ts in lecturas(sc).values() for t in ts)
    fallos, avisos, vistas = [], [], set()
    corr = json.load(open(f'{REPO}/festivals/staging/{FID}-correcciones.json', encoding='utf-8')).get('direccion', {})

    def esta(textos, frag):
        return any(frag in t for t in textos)

    for f in build['films']:
        lam = (f.get('_src') or {}).get('lamina', '')
        if f.get('is_cortos'):
            textos = prog.get(lam)
            if not textos:
                fallos.append(f'{f["title"]}: lámina {lam!r} sin lecturas'); continue
            vistas.add(lam)
            if not esta(textos, n(h12(f['time']))):
                fallos.append(f'{f["title"]}: la hora {f["time"]} no está en la lámina {lam}')
            if not esta(textos, n(MESES[f['day'][-2:]])):
                fallos.append(f'{f["title"]}: el día {f["day"]} no está en la lámina {lam}')
            for o in f['film_list']:
                if not esta(textos, n(o['title'])):
                    fallos.append(f'{o["title"]}: el título no está en la lámina {lam}')
                # una dirección corregida con su porqué (-correcciones.json «direccion»)
                # se verifica por lo que DICE la lámina, no por la corrección
                _c = corr.get(o['title'])
                for d in re.split(r',\s*', _c['lamina'] if _c else o.get('director', '')):
                    if d and not esta(textos, n(d)):
                        fallos.append(f'{o["title"]}: la dirección {d!r} no está en la lámina {lam}')
                if n(o['title']) not in sel:
                    avisos.append(f'{o["title"]}: el post de selección lo titula distinto')
                for d in re.split(r',\s*', o.get('director', '')):
                    if d and n(d) not in sel:
                        avisos.append(f'{o["title"]}: el post de selección no da «{d}» como dirección')
        else:
            textos = prog.get('15', []) + [t for ts in acad.values() for t in ts]
            vistas.add('15')
            if not esta(textos, n(f['title'])):
                fallos.append(f'{f["title"]}: no está en la lámina de masterclass')
            if not esta(prog.get('15', []), n(h12(f['time']))):
                fallos.append(f'{f["title"]}: la hora {f["time"]} no está en la lámina 15')
    faltan = {f'{i:02d}' for i in list(range(2, 14)) + [15]} - vistas
    if faltan:
        fallos.append(f'láminas de programa sin función en el build: {sorted(faltan)}')
    for v, x in build['venues'].items():
        if x.get('lat') is None:
            fallos.append(f'sede {v!r} sin pin')
        elif (geo.get(v) or {}).get('_prec') != 'manual':
            fallos.append(f'sede {v!r}: pin sin verificar a mano')
    for a in avisos:
        print('  ⚠', a)
    if fallos:
        sys.exit('✗ el build no coincide con las láminas:\n  · ' + '\n  · '.join(fallos))
    n_obras = sum(len(f.get('film_list', [])) for f in build['films'])
    print(f'✓ {len(build["films"])} funciones y {n_obras} obras del build están, con día, hora, título y '
          f'dirección, en las lecturas OCR de su lámina; las 13 láminas de programa tienen su función; '
          f'{len(build["venues"])} sede con pin a mano · {len(avisos)} diferencias con los posts de selección')


if __name__ == '__main__':
    main()
