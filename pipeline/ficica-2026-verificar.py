#!/usr/bin/env python3
"""ficica-2026-verificar.py — el catálogo contra la tabla de la Selección Oficial.

Segunda lectura INDEPENDIENTE del HTML (por celdas de texto plano, sin el
lector del catálogo): toda fila de la tabla está en el catálogo con su título
y su dirección, y el catálogo no tiene obras que la tabla no tenga.
"""
import html
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
s = io.open(f'{REPO}/fuentes/ficica-2026/seleccion-oficial.html', encoding='utf-8').read()
celdas = [re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', c))).strip()
          for c in re.findall(r'<td[^>]*>(.*?)</td>', s, re.S)]
filas = {(celdas[i], celdas[i + 3].rstrip(',').strip()) for i in range(0, len(celdas), 4)}
cat = json.load(io.open(f'{REPO}/festivals/staging/ficica-2026-catalogo.json', encoding='utf-8'))['obras']
pub = {(o['titulo_tabla'], o.get('director') or '') for o in cat}
fallos = [f'en la tabla y NO en el catálogo: {t}' for t in sorted(filas - pub)] + \
         [f'en el catálogo y NO en la tabla: {t}' for t in sorted(pub - filas)]
if fallos:
    sys.exit('✗ ' + '\n✗ '.join(fallos))
print(f'✓ las {len(filas)} filas de la Selección Oficial están en el catálogo, y nada más')
