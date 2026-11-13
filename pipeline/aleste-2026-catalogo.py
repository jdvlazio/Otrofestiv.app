#!/usr/bin/env python3
"""aleste-2026-catalogo.py — las obras del 9.º Festival de Cine de Europa Central
y Oriental Al Este, sede Medellín (18–22 nov 2026). PRE-ONBOARDING (radar #1397).

Bogotá (25–29 nov, Cinemateca): IG p/DfsHqtAlpmC (13 nov), 5 funciones.

LAS FUENTES (12 nov 2026):
- MAMM: la página del ciclo «9º Festival Al Este» y la ficha de cada película
  (fuentes/aleste-2026/mamm-*.html): título, dirección, año, país, duración.
- IG @aleste.colombia, carrusel p/DfSV6Z3lpE1 (3 nov, «Programación Medellín»,
  sello «AL ESTE ESPECIAL»): La última ronda, Gioia mia, Pucallpa la Europea.
- IG p/DfYe-5Slr8E (5 nov, sello «FOKUS LAS GRIETAS EN EL MURO»): 4 clásicos
  de Wajda y Tanner en el Colombo. El pie nombra también a Václav Havel, pero
  ninguna lámina trae una obra suya: no se inventa.
- IG p/DfkttriN6pD (10 nov): el corto inaugural «Latidos».

Las láminas se leyeron a ojo y por ig-lecturas.py (Vision ×3 + tesseract).
"""
import io
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402

DESTINO = f'{REPO}/festivals/staging/aleste-2026-catalogo.json'
IG = 'https://www.instagram.com/p/'
MAMM = 'https://www.elmamm.org/producto/'
ESPECIAL, FOKUS = 'Al Este Especial', 'Fokus: Las grietas en el muro'

# título, dirección, año, país, min, sección, fuente
OBRAS = [
    ('The Souffleur', 'Gastón Solnicki', 2025, 'Argentina, Austria', 78, None, (MAMM + 'the-souffleur/', None)),
    ('Padre', 'Tereza Nvotová', 2025, 'Eslovaquia, República Checa, Polonia', 103, None, (MAMM + 'padre/', None)),
    ('1982', 'Juan Carlos García', 2025, 'Perú', 84, None, (MAMM + '1982/', None)),
    ('Londres', 'Sebastian Brameshuber', 2026, 'Austria', 122, None, (MAMM + 'londres/', None)),
    ('La última ronda en Venecia', 'Francesco Sossai', 2025, 'Italia', None, ESPECIAL, (IG + 'DfSV6Z3lpE1/', '01.jpg')),
    ('Gioia mia', 'Margherita Spampinato', 2025, 'Italia', 90, ESPECIAL, (IG + 'DfSV6Z3lpE1/', '03.jpg')),
    ('Pucallpa la Europea', 'Santi Zegarra', 2025, 'Perú', 105, ESPECIAL, (IG + 'DfSV6Z3lpE1/', '04.jpg')),
    ('Cenizas y diamantes', 'Andrzej Wajda', 1958, 'Polonia', 97, FOKUS, (IG + 'DfYe-5Slr8E/', '02.jpg')),
    ('Regreso de África', 'Alain Tanner', 1973, 'Suiza, Francia', 108, FOKUS, (IG + 'DfYe-5Slr8E/', '03.jpg')),
    ('La tierra prometida', 'Andrzej Wajda', 1974, 'Polonia', 162, FOKUS, (IG + 'DfYe-5Slr8E/', '04.jpg')),
    ('Los inocentes encantadores', 'Andrzej Wajda', 1960, 'Polonia', 83, FOKUS, (IG + 'DfYe-5Slr8E/', '05.jpg')),
    ('Latidos: el grafiti como arte, el grafiti como forma de vida', 'Juan Zapata', 2026, 'Colombia', None, None,
     (IG + 'DfkttriN6pD/', None)),
    # Bogotá, Cinemateca (IG p/DfsHqtAlpmC, 13 nov, «Programación Bogotá», leídas a ojo).
    # La lámina 1 dice «SHAME AND MONEYV»: errata, el título es «Shame and Money».
    ('Shame and Money', 'Visar Morina', 2026, 'Alemania, Kosovo, Eslovenia, Albania, Macedonia del Norte, Bélgica', 130, None,
     (IG + 'DfsHqtAlpmC/', '01.jpg')),
    ('Todas las canciones del mundo', 'Santiago Flórez Rincón', 2026, 'Colombia', 85, None, (IG + 'DfsHqtAlpmC/', '02.jpg')),
    ('Histeria', 'Mehmet Akif Büyükatalay', 2025, 'Alemania', 104, None, (IG + 'DfsHqtAlpmC/', '04.jpg')),
]


def main():
    obras = []
    for t, d, a, p, m, sec, (url, lam) in OBRAS:
        o = {'titulo': t, 'director': d, 'anio': a, 'pais': p, 'tipo': 'corto' if t.startswith('Latidos') else 'largo',
             '_src': {'url': url, 'date': '2026-11-12'}}
        if m:
            o['duracion_min'] = m
        if sec:
            o['seccion'] = sec
        if lam:
            o['_src']['lamina'] = lam
        obras.append(o)
    if len(obras) != 15:
        sys.exit(f'✗ {len(obras)} obras, se contaron 15')
    with io.open(DESTINO, 'w', encoding='utf-8') as f:
        json.dump({'_provenance': provenance(
            fuente='MAMM (ciclo 9º Festival Al Este) + IG @aleste.colombia (3, 5 y 10 nov 2026)',
            url='https://www.elmamm.org/cine/9o-festival-al-este/',
            metodo='fichas del MAMM y láminas de IG leídas a ojo y por OCR'), 'obras': obras},
            f, ensure_ascii=False, indent=1)
    print(f'✓ {len(obras)} obras → {DESTINO}')


if __name__ == '__main__':
    main()
