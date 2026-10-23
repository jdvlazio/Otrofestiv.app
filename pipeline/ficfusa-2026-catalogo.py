#!/usr/bin/env python3
"""ficfusa-2026-catalogo.py — la Selección Oficial de FICFUSA 2026 (13.ª versión,
11–16 nov 2026, Fusagasugá). PRE-ONBOARDING, radar #1032.

LA FUENTE: el post «Selección oficial FICFUSA 2026» (wp-json posts/9882,
publicado 21 oct 2026). Declara 62 obras (42 en competencia, 20 en muestras),
pero al 22 oct solo publica UNA sección, «Hecho por Colombianas»
(cortometrajes dirigidos por mujeres), con 3 tarjetas. El resto no está en el
HTML, ni en wp-json (media del 21 oct = esas 3), ni en Instagram
(@ficfusa_festival por Apify: último post de la selección, ninguno).

El dato está PINTADO en las tarjetas: se lee con pipeline/ocr.py y se cruza con
la transcripción a ojo (OJOS). El script FRENA si una tarjeta no trae el
director, el año o la duración transcritos: la lectura a ojo no se cree sin la
del OCR.

Escribe festivals/staging/ficfusa-2026-catalogo.json
"""
import io, json, os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402
from ocr import leer  # noqa: E402

SRC = f'{REPO}/fuentes/ficfusa-2026'
OUT = f'{REPO}/festivals/staging/ficfusa-2026-catalogo.json'
URL = 'https://ficfusa.com/seleccion-oficial-ficfusa-2026/'
UP = 'https://ficfusa.com/wp-content/uploads/2026/10/'

# Transcrito a ojo de cada tarjeta (22 oct). El OCR leyó «materidad»: manda la lámina.
OJOS = [
    ('seleccion-oficial-hecho-por-colombianas-ficfusa-desaprender-la-maternidad.webp',
     dict(titulo='Desaprender la maternidad', director='Juliana Erazo Gómez', anio=2025,
          pais='Colombia, Países bajos', duracion_min=11, genero='Animación', _dur='10:45')),
    ('akababuru-expresion-de-asombro-ficfusa.webp',
     dict(titulo='Akababuru: expresión de asombro', director='Irati Dojura Landa Yagarí', anio=2025,
          pais='Colombia', duracion_min=14, genero='Fantasía', _dur='13:32')),
    ('nina-chilapa-ficfusa-seleccion-oficial-hecho-por-colombianas.webp',
     dict(titulo='Niña chilapa', director='Juana Lotero López', anio=2025,
          pais='Colombia', duracion_min=17, genero='Documental', _dur='17')),
    # 22 oct 22:54–23:02: la página suma tres (media 9908–9910).
    ('seleccion-oficial-ficfusa-una-vez-en-un-cuerpo.webp',
     dict(titulo='Una vez en un cuerpo', director='María Cristina Pérez', anio=2025,
          pais='Colombia, Estados Unidos', duracion_min=11, genero='Animación', _dur='10:20', _fecha='2026-10-22')),
    ('chaika-seleccion-oficial-ficfusa.webp',
     dict(titulo='Chaika', director='Ingrid Paola Bonilla Rodríguez', anio=2025,
          pais='Colombia', duracion_min=15, genero='Ciencia ficción', _dur='14:40', _fecha='2026-10-22')),
    ('salsa-ficfusa-seleccion-oficial.webp',
     dict(titulo='Salsa', director='Antonina Kerguelén Román', anio=2024,
          pais='Colombia', duracion_min=14, genero='Ficción', _dur='14', _fecha='2026-10-22')),
]
SECCION = 'Hecho por Colombianas'   # verbatim: «CORTOMETRAJES DIRIGIDOS POR MUJERES · HECHO POR COLOMBIANAS»


def main():
    rutas = [f'{SRC}/{a}' for a, _ in OJOS]
    falta = [r for r in rutas if not os.path.exists(r)]
    if falta:
        sys.exit('✗ faltan las tarjetas: curl -sL ' + UP + '<archivo> -o fuentes/ficfusa-2026/<archivo>\n  ' + '\n  '.join(falta))
    ocr = leer(rutas)
    obras = []
    for (arch, o), r in zip(OJOS, rutas):
        txt = ' '.join(ocr[r])
        for tok in (o['director'], str(o['anio']), o['_dur'] + ' min'):
            if tok not in txt:
                sys.exit(f'✗ {arch}: el OCR no corrobora «{tok}»')
        o = dict(o); o.pop('_dur'); fecha = o.pop('_fecha', '2026-10-21')
        obras.append({**o, 'tipo': 'corto', 'seccion': SECCION,
                      '_src': {'url': URL, 'tarjeta': UP + arch, 'date': fecha}})
    json.dump({'_provenance': provenance(URL, metodo='wp-json posts/9882 + tarjetas leídas con ocr.py y a ojo',
                                         publicado='2026-10-21'),
               '_nota': 'el post declara 62 obras (42 en competencia, 20 en muestras); al 22 oct 23:02 solo publica estas 6',
               'obras': obras}, io.open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'✓ {len(obras)} obras → {os.path.relpath(OUT, REPO)}')


if __name__ == '__main__':
    main()
