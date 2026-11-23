#!/usr/bin/env python3
"""cajica-2026-verificar.py — segunda lectura, por OTRO camino que el crudo.

El crudo convierte `const programacion` a JSON. Ésta no: busca con regex sobre
el texto plano del script cada `hora:"…",lugar:"…"` y cada `titulo:"…",duracion:"…"`
y compara TOKENS (hora 24h, sala, minutaje, cantidad) contra el build. La
discrepancia es el dato: si algo no cuadra, sale con error.
"""
import json, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
h = open(f'{REPO}/fuentes/cajica-2026/festival-de-cine-2026.html', encoding='utf-8').read()
b = json.load(open(f'{REPO}/festivals/staging/cajica-2026-build.json', encoding='utf-8'))['films']
errores = []


def h24(t):
    hh, mm, ap = re.match(r'(\d+):(\d+) ([ap])', t).groups()
    return f'{int(hh) % 12 + (12 if ap == "p" else 0):02d}:{mm}'


web = [(h24(a), l.split('— ')[-1]) for a, l in re.findall(r'hora:"([^"]+)",lugar:"([^"]+)"', h)]
# las funciones que salen de IG (no están en la web) no se comparan contra la web
pub = sorted((f['time'], f.get('sala')) for f in b if 'instagram.com' not in (f.get('_src') or {}).get('url', ''))
if sorted(web) != pub:
    errores.append(f'hora/sala: web {sorted(web)} ≠ build {pub}')
cortos = re.findall(r'\{titulo:"([^"]+)",duracion:"(\d+):(\d+) min"\}', h)
obras = [o for f in b for o in (f.get('film_list') or [])]
if len(cortos) != len(obras):
    errores.append(f'cortos: web {len(cortos)} ≠ build {len(obras)}')
for (t, m, s), o in zip(cortos, obras):
    if not t.startswith(o['title']) or int(o['duration'].split()[0]) != round(int(m) + int(s) / 60):
        errores.append(f'corto «{t}» {m}:{s} ≠ «{o["title"]}» {o["duration"]}')
for f in b:
    if f.get('requires_registration') and not f.get('registration_url', '').startswith('https://culturacajica.app/'):
        errores.append(f'«{f["title"]}» pide inscripción sin su enlace')
print(f'{len(web)} tarjetas, {len(cortos)} cortos verificados')
if errores:
    sys.exit('✗ ' + '\n✗ '.join(errores))
print('✓ build = web')
