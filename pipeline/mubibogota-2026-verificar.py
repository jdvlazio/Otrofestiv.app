#!/usr/bin/env python3
"""mubibogota-2026-verificar.py — el build contra la página, por OTRA lectura.

El crudo lee el __NUXT_DATA__; esto lee el TEXTO VISIBLE de la misma página
guardada (la que ve una persona): para cada tarjeta, el título en mayúsculas y,
unas líneas después, «oct NN» y la hora. Toda función del build tiene que estar
ahí con su día y su hora, y toda tarjeta con hora tiene que estar en el build.
La sede tiene pin verificado a mano.
"""
import html
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FID = 'mubibogota-2026'
s = io.open(f'{REPO}/fuentes/{FID}/bogota.html', encoding='utf-8').read()
t = html.unescape(re.sub(r'<[^>]+>', '\n', re.sub(r'<script.*?</script>|<style.*?</style>', '', s, flags=re.S)))
L = [x.strip() for x in t.split('\n') if x.strip()]


def hora_tarjeta(h):
    m = re.match(r'(\d{1,2}):(\d{2})\s*([ap]m)?', h.lower().replace(' ', ''))
    hh, mm, ap = int(m.group(1)), m.group(2), m.group(3)
    if ap == 'pm' and hh < 12:
        hh += 12
    return f'{hh:02d}:{mm}'


web = set()
for i, x in enumerate(L):
    m = re.fullmatch(r'oct (\d{2})', x.lower())
    # un rango («oct 24» / «- oct 25» / «1:00 pm»): la hora viene una línea después
    k = i + 2 if i + 2 < len(L) and re.fullmatch(r'-\s*oct \d{2}', L[i + 1].lower()) else i + 1
    if m and k < len(L) and re.match(r'\d{1,2}:\d{2}', L[k]):
        # el título es la última línea en mayúsculas antes del crédito/fecha
        tit = next(L[j] for j in (i - 1, i - 2) if L[j].isupper() and L[j] not in ('GRATIS',))
        web.add((f'2026-10-{m.group(1)}', hora_tarjeta(L[k]), tit))
        if L[i - 1].isupper() and L[i - 2].isupper() and not L[i - 2].startswith(('ESTRENO', 'Q&A', 'EPÍLOGO')):
            web.add((f'2026-10-{m.group(1)}', hora_tarjeta(L[k]), L[i - 2]))
build = json.load(io.open(f'{REPO}/festivals/staging/{FID}-build.json', encoding='utf-8'))
crudo = json.load(io.open(f'{REPO}/festivals/staging/{FID}-crudo.json', encoding='utf-8'))
# sin distinguir mayúsculas: ensamblar pone en Título los programas
# (caja.titulo, 15 oct) y el título del build deja de ser idéntico al del crudo
fuente = {f['titulo'].lower(): f['titulo_fuente'] for f in crudo['funciones']}
pub = {(f['day'], f['time'], fuente.get(f['title'].lower(), f['title'])) for f in build['films']}
fallos = [f'en el build y NO en la página: {x}' for x in sorted(pub - web)]
# cobertura inversa: toda tarjeta con hora está publicada (una lectura puede
# dar dos candidatos de título para la misma tarjeta; basta con uno)
por_hora = {}
for d, h, tit in web:
    por_hora.setdefault((d, h), set()).add(tit)
for (d, h), tits in sorted(por_hora.items()):
    if not any((d, h, x) in pub for x in tits):
        fallos.append(f'en la página y NO en el build: {d} {h} {sorted(tits)}')
geo = json.load(io.open(f'{REPO}/festivals/staging/{FID}-venues-geo.json', encoding='utf-8'))
for v, x in build['venues'].items():
    if x.get('lat') is None or geo.get(v.split(' - ')[0], {}).get('_prec') != 'manual':
        fallos.append(f'sede {v!r} sin pin verificado a mano')
if fallos:
    sys.exit('✗ el build no coincide con la página:\n  · ' + '\n  · '.join(fallos))
print(f'✓ las {len(pub)} funciones del build están en la página con su día y su hora, '
      f'y toda tarjeta con hora está en el build · {len(build["venues"])} sede con pin a mano')
