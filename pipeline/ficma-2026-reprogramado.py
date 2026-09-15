# -*- coding: utf-8 -*-
"""Las funciones de FICMA 17 REPROGRAMADO (19–26 sep), según lo publicado.

El festival no republicó una parrilla: la está soltando función por función en
Instagram y en dos páginas sueltas de su web. Esto acumula lo publicado hasta
hoy para que la reprogramación no arranque de cero cuando salga el resto.

POR QUÉ NO SE PUEDE REMAPEAR LO DE AGOSTO: se comparó obra por obra contra
`festivals/ficma-2026.json` y NO es un desplazamiento. «El hogar fue sepultado»
pasó de mar 11 · 08:00 · All Cine a sáb 19 · 19:00 · Palogrande; «Soñé su
nombre» de mié 12 · 18:00 a sáb 19 · 14:00; «El príncipe de Nanawa» de jue 13 ·
07:30 · Los Fundadores a sáb 19 · 09:00 · Banrep. Cambian día, hora Y sede, y
además hay obras que en agosto no estaban. El CATÁLOGO sí sirve entero.
"""
import json, os

IG = 'https://www.instagram.com/cinemanizales_ficma/'
WEB_E = 'https://laficma.com/estrenosficma17/'

F = [
 # (titulo, director, dia, hora, sede, seccion, fuente, nota)
 ('El príncipe de Nanawa', 'Clarisa Navas', '2026-09-19', '09:00',
  'Centro Cultural del Banco de la República', 'Función de apertura',
  IG + 'reel/DdMiQSozvGr/',
  'El festival lo llama «Función apertura». La home de laficma.com lo fechó el 16 de septiembre —miércoles, y ANTES del arranque declarado—: se registra el 19, que es el que dice el post y que sí es sábado. NO montar sin volver a mirar.'),
 ('Soñé su nombre', 'Ángela Carabalí', '2026-09-19', '14:00',
  'Teatro Los Fundadores – Sala Olimpia', 'Estrenos Cine Colombiano', WEB_E,
  'Conversatorio con su directora. Entrada libre hasta completar aforo.'),
 ('Ayuno y cenizas', 'Rodrigo Dimaté', '2026-09-19', '16:00',
  'Teatro Los Fundadores – Sala Olimpia', 'Estrenos Cine Colombiano', WEB_E,
  'Conversatorio con su director. Entrada libre hasta completar aforo.'),
 ('Que el cielo nos perdone', 'Andrés Buitrago', '2026-09-19', '19:00',
  'Casa de la Cultura de Palogrande – Calle externa', 'Cortometrajes',
  IG + 'p/DdREw9HDXz6/',
  'Estreno en Manizales, con conversatorio. MISMO pase que «El hogar fue sepultado»: misma sede, mismo día, misma hora — corto + largo.'),
 ('El hogar fue sepultado en esa tierra que nunca pudimos encontrar', 'Deimer Quintero Vertel',
  '2026-09-19', '19:00', 'Casa de la Cultura de Palogrande – Calle externa',
  'Función Inaugural', IG + 'p/DdSSPXwGle2/',
  'El festival la llama «Función Inaugural», y a «El príncipe de Nanawa» «Función apertura». Son dos cosas distintas o una errata: PREGUNTAR antes de montar.'),
 ('Semillas', 'Eliana Niño', '2026-09-19', '18:30',
  'Confa de la 50 – Auditorio Hernando Aristizábal Botero', 'Cine Colombiano',
  IG + 'p/DdRhWhrkWKe/', 'Dos pases: sábado 19 y domingo 20, misma hora y sede.'),
 ('Semillas', 'Eliana Niño', '2026-09-20', '18:30',
  'Confa de la 50 – Auditorio Hernando Aristizábal Botero', 'Cine Colombiano',
  IG + 'p/DdRhWhrkWKe/', 'Segundo pase.'),
 ('Manizales City', 'Félix R. Restrepo', '2026-09-20', '11:30',
  'Parque Ernesto Gutiérrez', 'Cine Clásico Colombiano', IG + 'reel/DdTmOB4FdTP/',
  'Documental de 1925 restaurado por la Fundación Patrimonio Fílmico Colombiano. Va dentro del Convite Solidario de Misión Comparte, por la reconstrucción tras el sismo.'),
 ('El juego de la vida', 'Mario Andrés Ruiz Zuluaga', '2026-09-22', '08:00',
  '', 'Estrenos Cine Colombiano', WEB_E,
  'Franja con colegios. SEDE SIN DECLARAR. Presencia del director.'),
]

T = [
 ('Cine en Movimiento: Plano Secuencia', 'Mauricio Casilimas', '2026-09-19', '15:00',
  'Secretaría de Cultura de Palogrande', '30 cupos'),
 ('Escribir con la cámara: del guion a la puesta en escena', 'Andrés Buitrago',
  '2026-09-22', '09:00', '', 'sede sin declarar'),
 ('Poniéndole voz a tu historia silenciada', 'Diana Arias', '2026-09-23', '14:00',
  'Hall Secretaría de la Mujer y Equidad de Género', '20 cupos'),
 ('Animación de fotografías «de cero a cien» con IA', 'Fabián Amador Salazar',
  '2026-09-24', '17:00', 'Secretaría de Cultura de Palogrande', '30 cupos'),
]

# Las dos obras que en agosto NO estaban. La sinopsis es la que publica el
# propio festival —fuente más fuerte que TMDB para una obra de 2026 que casi no
# tiene ficha—; el resto del dato sale del mismo post o página.
FICHA_NUEVA = {
 'Ayuno y cenizas': {
   'anio': 2026, 'duracion_min': 100, 'pais': 'Colombia',
   'sinopsis': ('En medio de las montañas de Bogotá, un grupo aficionado de teatro hace '
     'ensayos y lleva a escena la más famosa de todas las obras, Edipo Rey. Sus integrantes '
     'son músicos, actores, artistas de barrio y, algunos de ellos, consumidores de bazuco. '
     'Los testimonios sobre la droga, la familia y el barrio —voces, manos y rostros, a veces '
     'distantes y a veces frágiles—, contrastan con la atmósfera de tambores y luces '
     'incandescentes de la creación teatral. En las lomas de la ciudad, Edipo Rey no es una '
     'obra antigua, es una pregunta sobre el destino, sobre la posibilidad de tomar el rumbo '
     'de la propia vida.'),
   '_sinopsis_src': 'https://laficma.com/estrenosficma17/'},
 'Semillas': {
   'anio': 2026, 'duracion_min': 100, 'pais': 'Colombia',
   'sinopsis': ('Shaira, una niña llanera, sueña con participar en un festival del colegio. '
     'Pero un día su caballo desaparece. En un atardecer llanero, su abuelo le cuenta que el '
     'cielo atrapa a los animales y forma sus figuras en las nubes, y que solo cuando vuelva a '
     'llover regresarán al pueblo. Decidida, Shaira emprende la búsqueda de una semilla '
     'especial capaz de hacer llover de nuevo y traer de vuelta a su caballo, Semillas.'),
   '_sinopsis_src': 'https://www.instagram.com/cinemanizales_ficma/p/DdRhWhrkWKe/'},
}

fun = [{'titulo': t, 'director': d, 'dia': dia, 'hora': h, 'sede': s,
        'seccion': sec, 'acceso': 'Entrada libre',
        '_src': {'url': u, 'date': '2026-09-15'}, '_nota': n}
       for t, d, dia, h, s, sec, u, n in F]
for x in fun:
    if x['titulo'] in FICHA_NUEVA:
        x.update(FICHA_NUEVA[x['titulo']])
fun += [{'titulo': t, 'tallerista': d, 'dia': dia, 'hora': h, 'sede': s,
         'tipo': 'taller', 'acceso': 'Entrada libre', '_cupos': c,
         '_src': {'url': 'https://laficma.com/talleresficma17/', 'date': '2026-09-15'}}
        for t, d, dia, h, s, c in T]

out = {
 '_provenance': {
   'fuente': 'laficma.com (/estrenosficma17/ y /talleresficma17/) + Instagram @cinemanizales_ficma, post a post',
   'capturado': '2026-09-15',
   'metodo': 'La web NO tiene parrilla: su menú solo ofrece ESTRENOS y TALLERES. El resto sale de los posts, que desde el 14 sep ya traen la función entera (día · hora · sede · acceso). Los pies se leyeron por embed, completos.',
   'alcance': f'{len(F)} funciones y {len(T)} talleres publicados. El festival declara «más de 60 proyecciones»: falta la inmensa mayoría.'},
 '_festival': {
   'nombre': 'FICMA — Feria Internacional de Cine de Manizales', 'edicion': 17,
   'titulo_edicion': 'El jardín de las cosas perdidas',
   'ciudad': 'Manizales', 'fechas': '19–26 de septiembre de 2026',
   'reprogramado_desde': '10–17 de agosto de 2026, aplazado por el sismo del 10 ago',
   'acceso': 'Todas las actividades son de acceso libre (declarado en laficma.com)',
   'web': 'https://laficma.com/', 'ig': IG, 'radar': '#578'},
 '_por_que_no_se_remapea': (
   'Comparado obra por obra contra festivals/ficma-2026.json: cambian día, hora Y '
   'sede, y hay obras nuevas. NO es un desplazamiento del calendario de agosto. '
   'El catálogo (póster, sinopsis, lbSlug de las 90 funciones) sí se reutiliza entero.'),
 '_abierto': [
   'DOS «aperturas»: «Función apertura» (El príncipe de Nanawa, sáb 19 · 09:00) y «Función Inaugural» (El hogar fue sepultado, sáb 19 · 19:00). Preguntar cuál es cuál.',
   'La home de laficma.com fecha El príncipe de Nanawa el 16 de septiembre; el post dice sábado 19. El 16 es miércoles y cae antes del arranque. Sin resolver.',
   'El 11 sep la página de talleres listaba SEIS (con Franco Lolli e Isabella Vega) y el 13 devolvió cuatro. No se afirma que se cayeran: puede ser lectura incompleta. Volver a mirar esa página.',
   'Proimágenes (ntd=1320) sigue publicando las fechas de agosto.'],
 'funciones': fun}

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = REPO + '/festivals/staging/ficma-2026-reprogramado.json'
json.dump(out, open(D, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'{len(F)} funciones + {len(T)} talleres · días {sorted(set(x["dia"] for x in fun))}')
