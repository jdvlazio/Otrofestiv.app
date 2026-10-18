#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ficcali-2026-ig.py — las obras de los programas que la web no lista, desde el
Instagram del festival (@festivaldecinecali) → sidecar.

LA FUENTE (17 oct 2026): el post DenDhbtmnyO, leído sin sesión por el embed
(pipeline/ig_sin_sesion.py → fuentes/ig/DenDhbtmnyO/post.json). Su pie lista los
dos programas de «Vanguardias Afro e Indígenas», cada corto con «Título | Dir.
Nombre». La web publica los programas sin sus obras.

Escribe festivals/staging/ficcali-2026-ig.json — lo lee ficcali-2026-crudo.py
(el único que escribe el crudo). El programa se identifica por su NÚMERO
(«Programa 1»), que es como lo titula la web («– Prog 1»).
"""
import io, json, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402

SC = 'DenDhbtmnyO'
URL = f'https://www.instagram.com/p/{SC}/'
POST = f'{REPO}/fuentes/ig/{SC}/post.json'
DESTINO = f'{REPO}/festivals/staging/ficcali-2026-ig.json'


def main():
    if not os.path.exists(POST):
        sys.exit(f'✗ falta {os.path.relpath(POST, REPO)}: python3 pipeline/ig_sin_sesion.py {SC}')
    pie = json.load(io.open(POST, encoding='utf-8'))['pie']
    progs, actual = {}, None
    for l in pie.split('\n'):
        l = l.strip()
        m = re.match(r'Programa (\d+)\b', l)
        if m:
            actual = progs.setdefault(int(m.group(1)), [])
            continue
        m = re.match(r'(.+?)\s*[|l]\s*Dir\.\s*(.+?)(?:\s*\|.*)?$', l)
        if actual is not None and m:
            actual.append({'titulo': m.group(1).strip(), 'director': m.group(2).strip()})
        elif actual is not None and l and not m:
            actual = None if not l.startswith(('Programa',)) else actual
    if sorted(progs) != [1, 2] or any(len(v) != 7 for v in progs.values()):
        sys.exit(f'✗ el pie no dio 2 programas de 7 obras: { {k: len(v) for k, v in progs.items()} }')
    json.dump({'_provenance': provenance(URL, metodo='pie del post (embed sin sesión)'),
               'vanguardias': {str(k): v for k, v in progs.items()}},
              io.open(DESTINO, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'✓ Vanguardias: {", ".join(f"Prog {k} ({len(v)})" for k, v in sorted(progs.items()))} → {os.path.relpath(DESTINO, REPO)}')


if __name__ == '__main__':
    main()
