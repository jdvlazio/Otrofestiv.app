#!/usr/bin/env python3
"""fecibac-2026-verificar.py — el build contra el OCR de las 4 láminas: toda hora
y todo título clave publicados tienen que estar impresos en su lámina."""
import io, json, os, re, sys, unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from ocr import leer  # noqa: E402


def p(t):
    t = ''.join(c for c in unicodedata.normalize('NFD', t.lower()) if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', '', t)


_r = {i: f'{REPO}/fuentes/fecibac-2026/programacion-{i}.jpg' for i in range(1, 5)}
_o = leer(list(_r.values()))
lam = {i: '\n'.join(_o[r]) for i, r in _r.items()}
crudo = json.load(io.open(f'{REPO}/festivals/staging/fecibac-2026-crudo.json', encoding='utf-8'))['funciones']
TOKEN = {'Entre 2 Aguas': 'entredosaguas', 'Conversatorio Entre 2 Aguas': 'entre2aguas', 'Conversatorio con Brigitte Baptiste': 'brigittebaptiste',
         'Conversatorio con Manuel Villa': 'conversatorioconmanuelvilla', 'Fiesta en el Playón': 'fiestaenelplayon',
         'La Canoa Dorada (Tanda 1)': 'canoadoradatanda1', 'La Canoa Dorada (Tanda 2)': 'canoadoradatanda2',
         'Gala de premiación La Canoa Dorada': 'galadepremiacion', '2 Taller de creación de carteles cinematográficos para niños y niñas': '2tallerdecreaciondecarteles',
         'Taller de creación de carteles cinematográficos para niños y niñas': 'tallerdecreaciondecarteles', 'Remando con Pablo y Karla': 'pabloykarla',
         'Narrativas chilapas': 'narrativaschilapas', 'Fiesta Chilapa': 'fiestachilapa'}
fallos = []
for f in crudo:
    t = p(lam[f['_src']['lamina']])
    tok = TOKEN.get(f['titulo'], p(f['titulo']))
    if tok not in t:
        fallos.append(f"lámina {f['_src']['lamina']}: «{f['titulo']}» no está en el OCR")
    h, m = map(int, f['hora'].split(':'))
    h12 = h - 12 if h > 12 else h
    if f'{h12}{m:02d}' not in re.sub(r'[^0-9]', '', lam[f['_src']['lamina']]):
        fallos.append(f"lámina {f['_src']['lamina']}: hora {f['hora']} de «{f['titulo']}» no está")
if fallos:
    sys.exit('✗ ' + '\n✗ '.join(fallos))
print(f'✓ {len(crudo)} funciones: título y hora en el OCR de su lámina')
