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
SECCION = 'Hecho por Colombianas'   # verbatim: «CORTOMETRAJES DIRIGIDOS POR MUJERES · HECHO POR COLOMBIANAS»
# Mismo molde: el antetítulo describe, el título grande es el nombre → en Título.
REGION = 'Un Relato Hecho Región'  # verbatim: «CORTOMETRAJES NACIONALES · Un relato hecho región»

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
    # 23 oct 20:58–21:30: la página suma siete más a «Hecho por Colombianas» (media 9913–9922).
    ('seleccion-ficfusa-pudor-ante-el-asalto-de-los-ojos-furtivos.webp',
     dict(titulo='Pudor ante el asalto de los ojos furtivos', director='Laura María Rodríguez', anio=2025,
          pais='Colombia', duracion_min=9, genero='Animación', _dur='8:35', _fecha='2026-10-23')),
    ('sinfonia-del-viaje-a-la-luna-ficfusa.webp',
     dict(titulo='Sinfonía del viaje a la luna', director='Sandra Reyes Sotomayor', anio=2026,
          pais='Colombia', duracion_min=10, genero='Animación', _dur='9:24', _fecha='2026-10-23')),
    ('seleccion-oficial-ficfusa-kanekalon.webp',
     dict(titulo='Kanekalon', director='Sara J. Asprilla', anio=2025,
          pais='Colombia', duracion_min=13, genero='Ficción', _dur='12:30', _fecha='2026-10-23')),
    ('la-mona-seleccion-oficial-ficfusa-2026.webp',
     dict(titulo='La mona', director='Laura Gutiérrez Ardila', anio=2025,
          pais='Colombia', duracion_min=19, genero='Ficción, Wéstern', _dur='18:18', _fecha='2026-10-23')),
    ('seleccion-ficfusa-entrelazadas.jpg',
     dict(titulo='Entrelazadas', director='Alejandra Morales García', anio=2024,
          pais='Colombia', duracion_min=15, genero='Animación, Híbrido', _dur='14:36', _fecha='2026-10-23')),
    ('seleccion-oficial-ficfusa-madres-de-nacimiento.webp',
     dict(titulo='Madres de nacimiento', director='Gloria Isabel Gómez Ceballos', anio=2025,
          pais='Francia', duracion_min=9, genero='Documental, Experimental', _dur='8:08', _fecha='2026-10-23')),
    ('seleccion-oficial-ficfusa-chicha-la-chicharra.webp',
     dict(titulo='Chicha la chicharra', director='Sofía Alejandra Uzcátegui León', anio=2025,
          pais='Colombia', duracion_min=10, genero='Animación', _dur='10', _fecha='2026-10-23')),
    # 23 oct 22:21–22:55: sección nueva «CORTOMETRAJES NACIONALES · Un relato hecho región» (media 9927–9933).
    ('seleccion-oficial-ficfusa-tuktu-padre-maiz.webp',
     dict(titulo='Tuktu padre maíz', director='Mauricio Prieto', anio=2025,
          pais='Colombia', duracion_min=14, genero='Animación', _dur='13:45', _fecha='2026-10-23', _sec=REGION)),
    ('seleccion-oficial-ficfusa-como-el-agua-la-piedra-y-la-espuma.webp',
     dict(titulo='Como el agua, la piedra y la espuma', director='Diana Marcela Moreno', anio=2024,
          pais='Colombia', duracion_min=26, genero='Documental', _dur='25:01', _fecha='2026-10-23', _sec=REGION)),
    ('seleccion-oficial-ficfusa-la-gran-hazana.webp',
     dict(titulo='La gran hazaña', director='Luber Yesid Zúñiga Ordóñez', anio=2024,
          pais='Colombia', duracion_min=15, genero='Drama, Aventura', _dur='14:56', _fecha='2026-10-23', _sec=REGION)),
    ('seleccion-oficial-ficfusa-bajo-el-ultimo-aliento.webp',
     dict(titulo='Bajo el último aliento', director='Pedro Valencia', anio=2024,
          pais='Colombia', duracion_min=6, genero='Drama, Experimental', _dur='5:15', _fecha='2026-10-23', _sec=REGION)),
]



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
        o = dict(o); o.pop('_dur'); fecha = o.pop('_fecha', '2026-10-21'); sec = o.pop('_sec', SECCION)
        obras.append({**o, 'tipo': 'corto', 'seccion': sec,
                      '_src': {'url': URL, 'tarjeta': UP + arch, 'date': fecha}})
    json.dump({'_provenance': provenance(URL, metodo='wp-json posts/9882 + tarjetas leídas con ocr.py y a ojo',
                                         publicado='2026-10-21'),
               '_nota': 'el post declara 62 obras (42 en competencia, 20 en muestras); al 23 oct 22:55 publica estas 17 en dos secciones',
               'obras': obras}, io.open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'✓ {len(obras)} obras → {os.path.relpath(OUT, REPO)}')


if __name__ == '__main__':
    main()
