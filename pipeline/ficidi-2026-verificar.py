#!/usr/bin/env python3
"""ficidi-2026-verificar.py — lo declarado del pre-onboarding contra el catálogo.

Toda sinopsis y todo año o duración declarados son de una obra del catálogo
de la Selección Oficial, y cada dato trae la URL de donde salió (o dice que
es traducción nuestra y de qué fuente).
"""
import io
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
cat = {o['titulo'] for o in json.load(io.open(f'{ST}/ficidi-2026-catalogo.json', encoding='utf-8'))['obras']}
sin = json.load(io.open(f'{ST}/ficidi-2026-sinopsis.json', encoding='utf-8'))['sinopsis']
dat = json.load(io.open(f'{ST}/ficidi-2026-datos.json', encoding='utf-8'))['datos']
fallos = [f'sinopsis de una obra que no está en el catálogo: {t}' for t in sin if t not in cat]
fallos += [f'sinopsis sin fuente: {t}' for t, v in sin.items() if 'http' not in v.get('fuente', '')]
fallos += [f'dato de una obra que no está en el catálogo: {t}' for t in dat if t not in cat]
for t, v in dat.items():
    for k in ('anio', 'duracion_min'):
        if k in v and not str(v.get(f'{k.split("_")[0]}_url', '')).startswith('http'):
            fallos.append(f'{t}: {k} sin URL')
if fallos:
    sys.exit('✗ ' + '\n✗ '.join(fallos))
print(f'✓ {len(sin)} sinopsis y {len(dat)} fichas de datos, todas de obras del catálogo y con su fuente')
