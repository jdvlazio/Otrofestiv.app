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

16 nov 2026 — LA WEB OFICIAL (alestfestival.com/programa2026, 40 fichas; la
lee aleste-2026-programa.py → festivals/staging/aleste-2026-programa.json):
suma las obras que faltaban (Bogotá) y da la SECCIÓN oficial de todas. Las
secciones de antes («Al Este en el MAMM / en la Cinemateca») eran nuestras,
por sede: la regla es la sección del festival, tal cual. Los dos bloques de
«Competencia Hecho en Colombia» son una sección; el bloque es la función.
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

DESTINO = f'{REPO}/festivals/staging/aleste-2026-catalogo.json'
IG = 'https://www.instagram.com/p/'
MAMM = 'https://www.elmamm.org/producto/'
ESPECIAL, FOKUS = 'Al Este Especial', 'Fokus: Las grietas en el muro'
WEB = 'https://www.alestfestival.com/programa2026'
PROGRAMA = f'{REPO}/festivals/staging/aleste-2026-programa.json'

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
    ('Latido. El grafiti como arte, el grafiti como forma de vida.', 'Juan Zapata', 2026, 'Colombia', None, None,
     (IG + 'DfkttriN6pD/', None)),
    # Bogotá, Cinemateca (IG p/DfsHqtAlpmC, 13 nov, «Programación Bogotá», leídas a ojo).
    # La lámina 1 dice «SHAME AND MONEYV»: errata, el título es «Shame and Money».
    ('Shame and Money', 'Visar Morina', 2026, 'Alemania, Kosovo, Eslovenia, Albania, Macedonia del Norte, Bélgica', 130, None,
     (IG + 'DfsHqtAlpmC/', '01.jpg')),
    ('Todas las canciones del mundo', 'Santiago Flórez Rincón', 2026, 'Colombia', 85, None, (IG + 'DfsHqtAlpmC/', '02.jpg')),
    ('Histeria', 'Mehmet Akif Büyükatalay', 2025, 'Alemania', 104, None, (IG + 'DfsHqtAlpmC/', '04.jpg')),
]


def seccion_web(sec):
    return re.sub(r'\s*[-–]\s*Bloque \d+$', '', sec)


def plano(t):
    return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFD', t.lower()).encode('ascii', 'ignore').decode())


def main():
    web = {plano(o['titulo']): o for o in json.load(io.open(PROGRAMA, encoding='utf-8'))['obras']}
    obras = []
    for t, d, a, p, m, sec, (url, lam) in OBRAS:
        o = {'titulo': t, 'director': d, 'anio': a, 'pais': p, 'tipo': 'corto' if t.startswith('Latido') else 'largo',
             '_src': {'url': url, 'date': '2026-11-12'}}
        if t == 'Latido. El grafiti como arte, el grafiti como forma de vida.':
            o['titulos_anteriores'] = ['Latidos: el grafiti como arte, el grafiti como forma de vida']
        if m:
            o['duracion_min'] = m
        if sec:
            o['seccion'] = sec
        if lam:
            o['_src']['lamina'] = lam
        w = web.pop(plano(t), None)
        if w:
            o['seccion'] = seccion_web(w['seccion'])
        obras.append(o)
    for w in web.values():                     # las que solo trae la web (16 nov)
        o = {'titulo': w['titulo'], 'pais': w['pais'], 'duracion_min': w['duracion_min'],
             'seccion': seccion_web(w['seccion']),
             'tipo': 'corto' if w['duracion_min'] < 60 else 'largo',
             '_src': {'url': f'{WEB}/{w["pagina"]}', 'date': '2026-11-16'}}
        if w['director']:
            o['director'] = w['director']
        if w['anio']:
            o['anio'] = w['anio']
        if w['titulo_original'] and w['titulo_original'] not in (w['titulo'], 'Varios'):
            o['titulo_original'] = w['titulo_original']
        obras.append(o)
    # Las que la web no trae: Cinemateca (fichas 4080 y 4087) y catálogo PDF (23 nov)
    for t, d, a, m, n, s in (('Futuros luminosos', 'Ismael García Ramírez', 2026, 25, 4080,
                                'En un lugar extraño y oscuro, un grupo variopinto de jóvenes imagina su futuro.'),
                          ('Transversal30FF', 'Sergio Mejía', 2025, 6, 4087,
                                'La trama sigue en tono de comedia dramática a dos amigos que, en medio de una mudanza, intentan encontrar la dirección del nuevo apartamento de uno de ellos, pero terminan completamente perdidos en la urbe.')):
        obras.append({'titulo': t, 'director': d, 'anio': a, 'pais': 'Colombia', 'duracion_min': m, 'tipo': 'corto',
                      'seccion': 'Competencia Hecho en Colombia', 'sinopsis': s,
                      '_src': {'url': f'https://cinematecadebogota.gov.co/node/peliculas/{n}?sede=11', 'date': '2026-11-23'}})
    if len(obras) != 43:
        sys.exit(f'✗ {len(obras)} obras, se contaron 43 (15 de MAMM/IG + 26 de la web + 2 de la sala)')
    with io.open(DESTINO, 'w', encoding='utf-8') as f:
        json.dump({'_provenance': provenance(
            fuente='MAMM (ciclo 9º Festival Al Este) + IG @aleste.colombia (3, 5 y 10 nov 2026)',
            url='https://www.elmamm.org/cine/9o-festival-al-este/',
            metodo='fichas del MAMM y láminas de IG leídas a ojo y por OCR'), 'obras': obras},
            f, ensure_ascii=False, indent=1)
    print(f'✓ {len(obras)} obras → {DESTINO}')


if __name__ == '__main__':
    main()
