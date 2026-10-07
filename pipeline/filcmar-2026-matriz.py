#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""filcmar-2026-matriz.py — la «Matriz información curaduría» que mandó el festival.

EL 6 OCT EL EQUIPO DE FILCMAR NOS MANDÓ SU HOJA DE CURADURÍA (Google Sheets,
cuatro pestañas: Universitaria, Latinoamericana, Cinescuela y Viejos secretos
del nuevo Oeste). Trae por obra lo que las láminas de IG no daban: SINOPSIS,
el afiche (un enlace a su Drive) y el crédito completo.

QUÉ HACE ESTE PASO, y qué NO:
  · lee las cuatro pestañas exportadas a CSV y los enlaces de la columna
    PÓSTERS (el CSV los pierde; salen de la vista HTML de la hoja);
  · escribe un sidecar por título. El crudo toma la SINOPSIS (la fuente del
    festival manda) y declara el AFICHE en filcmar-2026-afiches.json, que
    enriquecer.py usa solo donde TMDB y lo ya publicado no tienen uno.

Lee   fuentes/filcmar-2026/matriz/gid-*.csv, posters-links.json, posters/
Esc.  festivals/staging/filcmar-2026-matriz.json
"""
import csv
import io
import json
import os
import re
import sys
import unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
M = f'{REPO}/fuentes/filcmar-2026/matriz'
OUT = f'{REPO}/festivals/staging/filcmar-2026-matriz.json'
HOJA = 'https://docs.google.com/spreadsheets/d/1NVyy-_n4dtptNdhtSNfrcw3UQ59ZDKXAv8hSvKc-evk/htmlview'
PESTANAS = {'0': 'Universitaria', '1846105446': 'Latinoamericana',
            '481110431': 'Cinescuela', '47146740': 'Viejos secretos del nuevo Oeste'}



def plano(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def slug_hoja(s):
    """El nombre con que se bajaron los afiches de la hoja (no es lib.slug)."""
    return plano(s).replace(' ', '-')[:60]


def minutos(s):
    """«15:00» (mm:ss, Universitaria), «81 min» o «70» → minutos."""
    s = (s or '').strip().lower()
    m = re.match(r'^(\d+):(\d\d)(?::(\d\d))?$', s)
    if m:
        a, b, c = m.groups()
        return int(a) * 60 + int(b) if c else int(a) + (1 if int(b) >= 30 else 0)
    m = re.match(r'^(\d+)', s)
    return int(m.group(1)) if m else None


def main():
    enlaces = json.load(io.open(f'{M}/posters-links.json', encoding='utf-8'))
    archivos = {f.rsplit('.', 1)[0]: f for f in os.listdir(f'{M}/posters')}
    obras, sin = {}, []
    for gid, pestana in PESTANAS.items():
        filas = list(csv.reader(io.open(f'{M}/gid-{gid}.csv', encoding='utf-8')))
        cab = filas[0]

        def col(r, nombre):
            return next((r[i].strip() for i, c in enumerate(cab)
                         if c.strip().upper().startswith(nombre) and i < len(r)), '')
        links = {plano(x['titulo']): x['poster_links'] for x in enlaces.get(gid, [])}
        for r in filas[1:]:
            t = col(r, 'NOMBRE')
            if not t:
                continue
            k = plano(t)
            d = {'titulo_matriz': t, 'pestana': pestana,
                 '_src': {'url': HOJA + f'#gid={gid}', 'date': '2026-10-06'}}
            # «¸» (cedilla suelta, U+00B8) por coma en la de Aquileo Venganza: es
            # un error de tecleo de la hoja, no de redacción
            sin_ = re.sub(r'\s+', ' ', col(r, 'SINOPSIS')).replace('\u00b8', ',').strip()
            if sin_:
                d['sinopsis'] = sin_
            if col(r, 'AÑO')[:4].isdigit():
                d['anio'] = int(col(r, 'AÑO')[:4])
            if minutos(col(r, 'DURACI')):
                d['duracion_min'] = minutos(col(r, 'DURACI'))
            d['credito'] = col(r, 'DIRECCI')
            # EL AFICHE se anota, no se copia: el crudo lo declara en
            # filcmar-2026-afiches.json y enriquecer.py lo usa SOLO donde TMDB y
            # lo ya publicado no tienen uno (la cascada de la casa)
            f = archivos.get(slug_hoja(t))
            if f and links.get(k):
                d['afiche'] = {'archivo': f'fuentes/filcmar-2026/matriz/posters/{f}',
                               'fuente': f'matriz de curaduría de FILCMAR (6 oct), Drive: {links[k][0]}'}
            else:
                sin.append(t)
            obras[k] = d
    json.dump({'_provenance': {
        'fuente': 'Matriz información curaduría — hoja de Google que mandó el equipo de FILCMAR',
        'url': HOJA, 'capturado': '2026-10-06',
        'metodo': 'CSV por pestaña + enlaces de la vista HTML; afiches bajados de su Drive',
        'uso': 'el crudo completa con esto lo que falta; no pisa lo publicado'},
        'obras': obras}, io.open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{len(obras)} obras · {sum(1 for o in obras.values() if o.get("sinopsis"))} con sinopsis · '
          f'{sum(1 for o in obras.values() if o.get("afiche"))} con afiche → {os.path.relpath(OUT, REPO)}')
    if sin:
        print('  sin afiche:', ', '.join(sin))


if __name__ == '__main__':
    main()
