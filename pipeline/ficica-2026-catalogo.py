#!/usr/bin/env python3
"""ficica-2026-catalogo.py — la Selección Oficial del Festival Internacional de
Cortometrajes Cine a la Calle (FICICA, Barranquilla, 20–24 oct 2026).

LA FUENTE: la tabla de https://ficica.cinealacalle.org/seleccion-oficial.html
(TÍTULO · PAÍS · CATEGORÍA · DIRECTOR-A-E), guardada en
fuentes/ficica-2026/seleccion-oficial.html. La programación (día, hora, sede)
todavía dice «muy pronto»: esto es el PRE-ONBOARDING, solo el catálogo.

El sitio escribe los títulos en MAYÚSCULA SOSTENIDA: se guarda tal cual en
`titulo_tabla` y `titulo` queda en frase como PROPUESTA; el publicado se
confirma con Juan (caja-sostenida) o lo da la ficha de TMDB.

Escribe festivals/staging/ficica-2026-catalogo.json
"""
import html
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402

FUENTE = 'https://ficica.cinealacalle.org/seleccion-oficial.html'
HTML = f'{REPO}/fuentes/ficica-2026/seleccion-oficial.html'
OUT = f'{REPO}/festivals/staging/ficica-2026-catalogo.json'
CATEGORIA = {'Ficcion': 'Ficción', 'Ficccion': 'Ficción', 'Animacion': 'Animación'}


def texto(td):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', td))).strip()


def frase(t):
    t = t.lower()
    return re.sub(r'^(\W*)(\w)', lambda m: m.group(1) + m.group(2).upper(), t)


def main():
    s = io.open(HTML, encoding='utf-8').read()
    cuerpo = s[s.index('<tbody>'):s.index('</tbody>')]
    obras = []
    for tr in re.findall(r'<tr>(.*?)</tr>', cuerpo, re.S):
        tds = [texto(td) for td in re.findall(r'<td[^>]*>(.*?)</td>', tr, re.S)]
        if len(tds) != 4:
            sys.exit(f'✗ fila con {len(tds)} celdas: {tds}')
        tit, pais, cat, dire = tds
        obras.append({'titulo': frase(tit), 'titulo_tabla': tit,
                      'director': dire.rstrip(',').strip() or None,
                      'pais': pais or None, 'categoria': CATEGORIA.get(cat, cat),
                      '_src': {'url': FUENTE, 'date': '2026-10-10'}})
    json.dump({'_provenance': provenance(FUENTE, metodo='tabla HTML de la Selección Oficial'),
               'obras': obras}, io.open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'✓ {len(obras)} obras → {os.path.relpath(OUT, REPO)}')


if __name__ == '__main__':
    main()
