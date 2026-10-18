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


def plano(t):
    import unicodedata
    t = ''.join(c for c in unicodedata.normalize('NFD', (t or '').lower()) if unicodedata.category(c) != 'Mn')
    return re.sub(r'\W+', ' ', t).strip()


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
    # LOS CORTOS DE LOS PROGRAMAS QUE NO SON DE LA SELECCIÓN (16 oct): Retrospectiva,
    # comunitarios, Cine accesible, Concurso MINI. Se suman para que se enriquezcan
    # igual (TMDB, la cascada de lo ya publicado); vienen del sidecar de programas
    _prog = f'{REPO}/festivals/staging/ficica-2026-programas.json'
    if os.path.exists(_prog):
        _ya = {plano(o['titulo_tabla']) for o in obras} | {plano(o['titulo']) for o in obras}
        _dir = {plano(o.get('director')) for o in obras if o.get('director')}
        for p in json.load(io.open(_prog, encoding='utf-8'))['programas']:
            for c in p['cortos']:
                if plano(c['titulo']) in _ya or plano(c.get('alterno')) in _ya or (c.get('director') and plano(c['director']) in _dir):
                    continue
                _ya.add(plano(c['titulo']))
                obras.append({'titulo': frase(c['titulo']), 'titulo_tabla': c['titulo'],
                              'director': c.get('director') or None, 'pais': c.get('pais') or None,
                              'categoria': p['nombre'], 'fuera_de_seleccion': True,
                              '_src': {'url': 'https://ficica.cinealacalle.org/programas.html', 'date': '2026-10-16'}})
    json.dump({'_provenance': provenance(FUENTE, metodo='tabla HTML de la Selección Oficial'),
               'obras': obras}, io.open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'✓ {len(obras)} obras → {os.path.relpath(OUT, REPO)}')


if __name__ == '__main__':
    main()
