#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ficica-2026-programas.py — los cortos de cada programa de FICICA 2026 → sidecar.

LA FUENTE: https://ficica.cinealacalle.org/programas.html, guardada en
fuentes/ficica-2026/programas.html (16 oct 2026). Webflow, como la Programación
General: un bloque <script type="application/json"> con `programas` (20), cada
uno con `funciones` (dia, hora, sede, sala, acceso) y `cortos` (titulo en
MAYÚSCULA SOSTENIDA, alterno, pais, genero, director). El 15 oct decía «muy
pronto»; el 16 ya lista 162 cortos.

Escribe festivals/staging/ficica-2026-programas.json — lo lee ficica-2026-crudo.py,
que es el único que escribe el crudo. El programa se identifica por sus
FUNCIONES (día, hora, sede), no por su nombre.
"""
import io, json, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402

URL = 'https://ficica.cinealacalle.org/programas.html'
FUENTE = f'{REPO}/fuentes/ficica-2026/programas.html'
DESTINO = f'{REPO}/festivals/staging/ficica-2026-programas.json'


def main():
    s = io.open(FUENTE, encoding='utf-8').read()
    bl = re.findall(r'<script type="application/json"[^>]*>(.*?)</script>', s, re.S)
    if len(bl) != 1:
        sys.exit(f'✗ {os.path.relpath(FUENTE, REPO)}: {len(bl)} bloques JSON (se esperaba 1)')
    P = json.loads(bl[0])['programas']
    out = []
    for p in P:
        if not p.get('funciones'):
            sys.exit(f'✗ programa sin funciones: {p.get("nombre")}')
        out.append({'nombre': p['nombre'], 'numero': p.get('numero') or None,
                    'funciones': [(f['dia'], f['hora'], f['sede']) for f in p['funciones']],
                    'cortos': [{k: c.get(k) for k in ('titulo', 'alterno', 'pais', 'genero', 'director') if c.get(k)}
                               for c in p.get('cortos') or []]})
    json.dump({'_provenance': provenance(URL, metodo='JSON embebido de la página Programas'),
               'programas': out}, io.open(DESTINO, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'✓ {len(out)} programas · {sum(len(p["cortos"]) for p in out)} cortos → {os.path.relpath(DESTINO, REPO)}')


if __name__ == '__main__':
    main()
