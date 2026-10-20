#!/usr/bin/env python3
"""festicine-antioquia-2026-catalogo.py — la selección del 27.° Festival de Cine
de Santa Fe de Antioquia (Festicine Antioquia, 4–8 dic 2026). PRE-ONBOARDING.

LA FUENTE: el post de WordPress «Caja de Pandora 2026 — Seleccionados» (25 ago
2026), bajado por wp-json a fuentes/festicine-antioquia-2026/seleccionados.json.
Es TEXTO (una tabla Título / Dirección / Categoría): se lee del HTML, no a ojo.
21 cortos colombianos. La tabla no trae país, año ni duración.

Lo que NO existe todavía (20 oct 2026, wp-json posts+pages): la selección de
Óperas Primas (solo la convocatoria, cerró el 15 jun), ninguna otra sección y la
programación (días, horas, sedes).

El script FRENA si la tabla no da 21 filas: es el número que el post declara.

Escribe festivals/staging/festicine-antioquia-2026-catalogo.json
"""
import html, io, json, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402

SRC = f'{REPO}/fuentes/festicine-antioquia-2026/seleccionados.json'
OUT = f'{REPO}/festivals/staging/festicine-antioquia-2026-catalogo.json'
URL = 'https://festicineantioquia.org/caja-de-pandora-2026-seleccionados/'
SECCION = 'Caja de Pandora'          # verbatim: «Competencia de cortometrajes Caja de Pandora»
DECLARADAS = 21


def main():
    if not os.path.exists(SRC):
        sys.exit("✗ falta la fuente: curl -sL 'https://festicineantioquia.org/wp-json/wp/v2/posts?slug="
                 "caja-de-pandora-2026-seleccionados' -o fuentes/festicine-antioquia-2026/seleccionados.json")
    post = json.load(open(SRC, encoding='utf-8'))[0]
    filas = re.findall(r'<tr[^>]*>(.*?)</tr>', post['content']['rendered'], re.S)
    obras = []
    for f in filas:
        cel = [re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', c))).strip()
               for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', f, re.S)]
        if len(cel) != 3 or cel[0] == 'Título':
            continue
        titulo, director, categoria = cel
        obras.append({'titulo': titulo, 'director': director, 'pais': 'Colombia',
                      'tipo': 'corto', 'categoria': categoria, 'seccion': SECCION,
                      '_src': {'url': URL, 'date': post['date'][:10]}})
    if len(obras) != DECLARADAS:
        sys.exit(f'✗ la tabla dio {len(obras)} filas y el post declara {DECLARADAS}')
    json.dump({'_provenance': provenance(URL, metodo='wp-json, tabla Título/Dirección/Categoría',
                                         publicado=post['date'][:10]),
               'obras': obras}, io.open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'✓ {len(obras)} obras → {os.path.relpath(OUT, REPO)}')


if __name__ == '__main__':
    main()
