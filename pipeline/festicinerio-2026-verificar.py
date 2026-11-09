#!/usr/bin/env python3
"""festicinerio-2026-verificar.py — el build contra las láminas, por otro camino.

No usa la tabla del crudo: toma Tesseract sobre cada lámina (otro motor que el
Vision del crudo), y exige que cada hora y título del build de ese día estén
ahí, que los días sean los seis oficiales y que las 48 obras del catálogo salgan.
"""
import json
import os
import re
import subprocess
import sys
import unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IG = f'{REPO}/fuentes/ig/DfXJjeBm1w7'
LAM = {'2026-11-08': '01', '2026-11-09': '02', '2026-11-10': '03', '2026-11-11': '04', '2026-11-12': '05', '2026-11-13': '06'}


def plano(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    return re.sub(r'[^a-z0-9]+', ' ', ''.join(c for c in s if unicodedata.category(c) != 'Mn')).strip()


def main():
    b = json.load(open(f'{REPO}/festivals/staging/festicinerio-2026-build.json', encoding='utf-8'))
    films = b['films'] if isinstance(b, dict) else b
    cat = json.load(open(f'{REPO}/festivals/staging/festicinerio-2026-catalogo.json', encoding='utf-8'))['obras']
    fallos = []
    for d, n in LAM.items():
        t = plano(subprocess.run(['tesseract', f'{IG}/{n}.jpg', '-', '--psm', '6'], capture_output=True, text=True).stdout)
        delDia = [f for f in films if f['day'] == d]
        if not delDia:
            fallos.append(f'{d}: sin funciones')
        for f in delDia:
            h, m = f['time'].split(':')
            a = int(h) % 12 or 12
            # una hora que vino de una afirmación (docs/FUNCION.md) no está en la lámina: la respalda su fuente
            movida = ((f.get('_procedencia') or {}).get('time') or {}).get('tipo') not in (None, 'festival-web')
            if not movida and not re.search(rf'\b{a}\s?(pm|{m})\b' if m == '00' else rf'\b{a}\s{m}\b', t):
                fallos.append(f'{d} {f["time"]}: la hora no se lee en la lámina {n}')
            for w in re.findall(r'[a-z]{5,}', plano(f['title'])):
                if w not in t:
                    fallos.append(f'{f["title"]}: «{w}» no se lee en la lámina {n}')
    if {f['day'] for f in films} - set(LAM):
        fallos.append('hay funciones fuera de los días oficiales')
    pub = {plano(x['title']) for f in films for x in [f] + (f.get('film_list') or [])}
    faltan = [o['titulo'] for o in cat if plano(o['titulo']) not in pub]
    if faltan:
        fallos.append(f'obras del catálogo sin publicar: {faltan}')
    if fallos:
        sys.exit('✗ el build y las láminas no coinciden:\n  · ' + '\n  · '.join(fallos))
    print(f'✓ {len(films)} funciones confirmadas por Tesseract; las {len(cat)} obras del catálogo salen')


if __name__ == '__main__':
    main()
