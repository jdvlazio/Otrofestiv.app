#!/usr/bin/env python3
"""bogoshorts-2026-textos.py — la descripción de las ACTIVIDADES desde el catálogo oficial.

Toma del PDF el texto en español de cada actividad, entre dos frases de arranque y
cierre copiadas del propio catálogo (si una no aparece, FRENA: el PDF cambió).
Escribe festivals/staging/bogoshorts-2026-textos.json, que lee bogoshorts-2026-crudo.py.
"""
import json, os, re, subprocess, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402
PDF = f'{REPO}/fuentes/bogoshorts-2026/catalogo2026.pdf'
URL = 'https://info.bogoshorts.com/sccs/prensa/2026/docs_2026/24BSFF_catalogo2026.pdf'
OUT = f'{REPO}/festivals/staging/bogoshorts-2026-textos.json'
TROZOS = {
    'vineta': ('¿Qué sucede cuando una historia dibujada', 'en el papel y en la pantalla.'),
    'croacia': ('¿Qué lugar ocupa el cortometraje', 'posibilidades de intercambio y colaboración.'),
    'jazz': ('Una trompeta puede cambiar', 'ninguno había imaginado por separado.'),
    'robert': ('Antes del movimiento, una línea', 'nuevas posibilidades cinematográficas.'),
    'androsfera': ('Como extensión de esta experiencia, la lectura', 'cine, performance y música.'),
    'imaginaton': ('El viernes 4 de diciembre, todos los participantes', 'experiencia de creación.'),
    'picnic': ('Bajo el cielo estrellado de la plazoleta CityU, el 10°', 'proyección multisensorial.'),
}


def main():
    t = subprocess.run(['pdftotext', PDF, '-'], capture_output=True, text=True).stdout
    t = re.sub(r'\f', '\n', t)
    t = re.sub(r'-\n(?=[a-záéíóúñ])', '', t)
    t = re.sub(r'\s+', ' ', t)
    out = {}
    for k, (a, b) in TROZOS.items():
        i = t.find(a)
        if i < 0:
            sys.exit(f'✗ {k}: el catálogo ya no trae «{a}»')
        if b:
            j = t.find(b, i)
            if j < 0 or j - i > 2500:
                sys.exit(f'✗ {k}: no encuentro el cierre «{b}»')
            out[k] = {'es': t[i:j + len(b)]}
        else:                       # hasta el primer texto en inglés
            m = re.search(r'(.*?[.)]) (?=Under the|For |The |In |Since )', t[i:i + 2000])
            out[k] = {'es': m[1]}
    json.dump({'_provenance': provenance(URL, metodo='pdftotext: texto de la actividad entre frases del propio catálogo'),
               'textos': out}, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'✓ {len(out)} textos → {os.path.relpath(OUT, REPO)}')


if __name__ == '__main__':
    main()
