#!/usr/bin/env python3
"""mamut-2026-programa-catalogo.py — las obras de la PROGRAMACIÓN de Mamut 11 → catálogo.

La Selección Oficial (16 cortos) ya tiene su catálogo en mamut-2026-catalogo.py.
La programación del 28 sep (IG p/Dd2bBTciVpN) suma OTRAS obras: la inaugural,
los clásicos restaurados, los largos invitados. Este paso las junta para
enriquecerlas ANTES de montar, con la misma cascada que cualquier catálogo
(enriquecer_catalogo.py): TMDB, Proimágenes y lo que ya publicamos.

LA FUENTE es la lectura a ojo de las láminas (fuentes/mamut-2026-ojos-programa.json).
Los créditos vienen en formatos distintos según la lámina («Luis Ospina ·
Colombia · 1999 · 110 min.», «Deimer Quintero Vertel. Colombia. 92 min.»), así
que la ficha de cada obra va en una TABLA, y el paso comprueba que CADA dato de
la tabla esté en el crédito transcrito de su lámina. Si la tabla dice algo que la
lámina no dice, falla.

Solo entran obras: los talleres, los programas sin contenido publicado
(«Programa: Santiago Herrera») y la fiesta no son obras que buscar.
"""
import io
import json
import os
import re
import sys
import unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402

FID = 'mamut-2026-programa'
OJOS = f'{REPO}/fuentes/mamut-2026-ojos-programa.json'
DESTINO = f'{REPO}/festivals/staging/{FID}-catalogo.json'

# título → (dirección, país, año, duración). None = la lámina no lo dice.
OBRAS = {
    'Soplo de vida': ('Luis Ospina', 'Colombia', 1999, 110),
    'Bombardeo a Washington': ('Luis Ospina', 'Colombia', 1972, 1),
    'El hogar fue sepultado en esa tierra que nunca pudimos encontrar':
        ('Deimer Quintero Vertel', 'Colombia', None, 92),
    'Sueño sobre un mantel vacío': ('Víctor Gaviria', 'Colombia', 1981, 10),
    'Apocalipsur': ('Javier Mejía Osorio', 'Colombia', 2007, 101),
    'Minuto fatal': ('Jairo Pinilla', 'Colombia', 1974, 38),
    'Lolita en Honda': ('Daniel Torres', 'Colombia', None, 61),
    'Frío metal': ('Clemente Castor', 'México', None, 105),
    'La memoria de las mariposas': ('Tatiana Fuentes Sadowski', 'Perú, Portugal', None, 77),
    'Manual para invocar fantasmas': ('Juliana Zuluaga', 'Colombia', None, 71),
    'Carne de tu carne': ('Carlos Mayolo', 'Colombia', None, 94),
    'Geographies of Solitude': ('Jacquelyn Mills', 'Canadá', None, 103),
    'Yo soy la muerte': ('Daniel Cortés', 'Colombia', 2026, 30),
    # sin crédito en la lámina: se busca igual, por si ya la publicamos
    'Huella mi frente': (None, None, None, None),
}


def plano(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def main():
    ojos = json.load(io.open(OJOS, encoding='utf-8'))['actividades']
    por_titulo = {}
    for a in ojos:
        por_titulo.setdefault(a['titulo'], []).append(a)
    fallos, obras = [], []
    for t, (d, pais, anio, dur) in OBRAS.items():
        if t not in por_titulo:
            fallos.append(f'«{t}» no está en la transcripción')
            continue
        cred = ' '.join(plano(a.get('credito', '')) for a in por_titulo[t])
        for v in (d, pais, anio, dur):
            if v is not None and plano(str(v)) not in cred:
                fallos.append(f'«{t}»: la tabla dice {v!r} y el crédito de la lámina no')
        o = {'titulo': t, 'seccion': 'Programación',
             '_src': {'url': 'https://www.instagram.com/p/Dd2bBTciVpN/', 'date': '2026-09-28',
                      'laminas': sorted({a['lamina'] for a in por_titulo[t]})}}
        for k, v in (('director', d), ('pais', pais), ('anio', anio), ('duracion_min', dur)):
            if v is not None:
                o[k] = v
        obras.append(o)
    if fallos:
        sys.exit('✗ la tabla no coincide con las láminas:\n  · ' + '\n  · '.join(fallos))
    json.dump({'_provenance': provenance(
        'IG @mamut_festival p/Dd2bBTciVpN (28 sep 2026), leída a ojo',
        que_aporta='las obras de la programación que no están en la Selección Oficial'),
        'obras': obras}, io.open(DESTINO, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'✓ {len(obras)} obras de la programación, cada dato confirmado en su lámina '
          f'→ {os.path.relpath(DESTINO, REPO)}')


if __name__ == '__main__':
    main()
