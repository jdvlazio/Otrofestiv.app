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
 # Los dos pases de «El juego de la vida» ya tienen sede: el post del 17 sep los
 # fechó los dos. La web solo traía el de colegios y sin lugar.
 ('El juego de la vida', 'Mario Andrés Ruiz Zuluaga', '2026-09-21', '18:30',
  'Auditorio Olimpia – Teatro Los Fundadores', 'Estrenos Cine Colombiano',
  IG + 'p/DdXc2wiDbNz/', 'Presencia de su director.'),
 ('El juego de la vida', 'Mario Andrés Ruiz Zuluaga', '2026-09-22', '08:00',
  'Auditorio Olga del Socorro Serna de Quintero – Fundación Batuta Caldas',
  'Estrenos Cine Colombiano', IG + 'p/DdXc2wiDbNz/',
  'Función para colegios, «¡pero todos están invitados!» — el festival la declara abierta.'),

 # LO QUE EL RADAR (#578) VENÍA DICIENDO Y EL ONBOARDING NO HABÍA LEÍDO. Las dos
 # primeras las reportó la corrida del 16 sep; las tres siguientes son posts de
 # ayer y hoy. El festival está soltando una función por post, a diario.
 ('Brigitte, Planeta B', 'Santiago Posada', '2026-09-20', '14:00',
  'Sala Olimpia – Teatro Los Fundadores', 'Cine Colombiano',
  IG + 'p/DdVLn8pFZQV/', 'Estreno en Manizales.'),
 ('Apuntes sobre anomalías y fantasmas', 'Rodrigo Dimaté', '2026-09-20', '16:00',
  'Sala Olimpia – Teatro Los Fundadores', 'Cine Colombiano',
  IG + 'p/DdUsahVGspB/',
  'Conversatorio con su director. Es una selección de CUATRO cortos de QUO CINE —el festival la anuncia como una sola obra de 72 min y así entra; los cuatro títulos no están publicados.'),
 ('Habitante', 'José Alejandro González', '2026-09-21', '08:00',
  'Auditorio Olga del Socorro Serna de Quintero – Fundación Batuta Caldas',
  'Cine Colombiano', IG + 'p/DdWiX_ukZfO/',
  'Conversatorio con el director. Función para colegios «¡pero abierta a todo el que quiera venir!».'),
 ('La luz por primera vez', 'Ibeth Johanna Rey Jerez, Frank Rodríguez Rojas',
  '2026-09-21', '15:00', 'Centro Cultural del Banco de la República',
  'Cine Colombiano', IG + 'reel/DdWtHVTzi--/',
  'Entrada libre hasta completar aforo.'),
 ('Dicen que tú y yo estamos locos', 'Juan Mauricio Piñeros', '2026-09-22', '15:00',
  'Centro Cultural del Banco de la República', 'Cine Colombiano',
  IG + 'reel/DdXvVyVDXh0/',
  'El post NO trae rótulo de sección —los demás sí, «#FICMA17 – Cine Colombiano»—: se le pone esa, que es la que llevan sus etiquetas (#CineColombiano). Único con clasificación de edad: +12.'),
]

# LA FRANJA ACADÉMICA YA NO SE TRANSCRIBE AQUÍ. Estaban estos cuatro talleres,
# leídos a ojo de /talleresficma17/ el 15 sep, con una nota pendiente: «el 11 sep
# esa página listaba seis y el 13 devolvió cuatro — volver a mirar». Hoy la lee
# `ficma-2026-franja-web.py` y son ONCE, con hora de cierre, cupo, inscripción y
# sinopsis. Dos copias del mismo hecho divergen siempre; la que se re-corre gana.

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
 'Apuntes sobre anomalías y fantasmas': {
   'anio': 2026, 'duracion_min': 72, 'pais': 'Colombia',
   'sinopsis': ('Una selección de cuatro cortos que reúne diez años de trabajo de QUO CINE '
     'en el barrio. Los rincones menos conocidos de Bogotá no son silenciosos: de las '
     'montañas, el centro y la periferia surgen las voces que dan forma a este compendio de '
     'cuatro partes: una instrucción didáctica de cómo se manejan espantos y ansiedades; el '
     'diario de un grupo de creación artística que no registró desilusiones; un relato con '
     'moraleja de la vez que un niño probó un cigarrillo; y un día y una vuelta por las calles '
     'en las que dicen que no hay que meterse. El manifiesto de QUO CINE que reúne una década '
     'en busca de fantasmas, anomalías, risas y encuentros que dejan huella.'),
   '_sinopsis_src': 'https://www.instagram.com/cinemanizales_ficma/p/DdUsahVGspB/'},
}

# Lo que el POST dice de esta edición y la ficha de agosto no traía. No es una
# obra nueva —está en el catálogo—: es un dato que solo publicó ahora.
DEL_POST = {
 'Dicen que tú y yo estamos locos': {'rating': '+12 años'},
}

# LA SINOPSIS EN INGLÉS, donde TMDB no la tiene. La app tiene modo en inglés y
# una obra sin sinopsis EN se queda muda ahí. Estas cuatro son traducción de lo
# que publica el FESTIVAL en español —su texto, no el de TMDB—, hecha acá y no
# por una API: es el método del pipeline desde que se retiró translate-synopsis.
SINOPSIS_EN = {
 'El hogar fue sepultado en esa tierra que nunca pudimos encontrar':
   ('“Those devils took everything from me, those devils took everything from me, '
    'those devils took everything from me”: this mantra of dispossession keeps '
    'resurfacing in the family, like a verdict. They long to meet their disappeared '
    'loved ones again, to play once more among plantain groves and fantastical beings, '
    'and… the house… the house wants to be a home again. Through home movies, collective '
    'archives, family images and a spectral, mystical presence, the film inhabits the '
    'dreams and the nightmares left by the traces of a vanished love. The gunfire seems '
    'to have stopped; the war feels distant now, but it left behind a deep grief and the '
    'promise of return. Friends, family, home and territory come back, summoned by this '
    'choral account. The past is a ghost, and this film speculates on a paradise and a '
    'hell that can no longer be touched, hoping to inhabit this new place and conjure an '
    'embrace inside it.'),
 'Que el cielo nos perdone':
   ('Colombia, 1951. In the thick of La Violencia, the period of brutal political war '
    'between Liberals and Conservatives, two chulavitas —hired killers on the government’s '
    'payroll— stalk a priest through the dark, waiting for him to lead them to the cabin in '
    'the woods where their next victims are hiding. But the horror they find there is a '
    'thousand times worse than the pain they meant to inflict.'),
 'Apuntes sobre anomalías y fantasmas':
   ('A selection of four shorts gathering ten years of QUO CINE’s work in the neighbourhood. '
    'Bogotá’s lesser-known corners are not silent: from the mountains, the centre and the '
    'outskirts come the voices that shape this four-part compendium — a how-to on handling '
    'spooks and anxieties; the diary of an art collective that never recorded a '
    'disappointment; a cautionary tale about the time a boy tried a cigarette; and a day out '
    'on the streets people say you should stay away from. QUO CINE’s manifesto: a decade '
    'spent looking for ghosts, anomalies, laughter and encounters that leave a mark.'),
 'Dicen que tú y yo estamos locos':
   ('The Luis Ángel Arango Public Library is the largest in Colombia and one of the most '
    'important in Latin America. This landmark of Bogotá life outgrows its traditional '
    'mission to become a stage for many lives: people who find in its reading rooms a '
    'refuge, a pause, or a way out of the reality waiting beyond its doors. The film '
    'gathers the stories of some of these “locos” — the word other readers, and even the '
    'city itself, tend to use for them.'),
}

fun = [{'titulo': t, 'director': d, 'dia': dia, 'hora': h, 'sede': s,
        'seccion': sec, 'acceso': 'Entrada libre',
        '_src': {'url': u, 'date': '2026-09-17'}, '_nota': n}
       for t, d, dia, h, s, sec, u, n in F]
for x in fun:
    if x['titulo'] in FICHA_NUEVA:
        x.update(FICHA_NUEVA[x['titulo']])
    if x['titulo'] in DEL_POST:
        x.update(DEL_POST[x['titulo']])
    if x['titulo'] in SINOPSIS_EN:
        x['sinopsis_en'] = SINOPSIS_EN[x['titulo']]

out = {
 '_provenance': {
   'fuente': 'laficma.com (/estrenosficma17/ y /talleresficma17/) + Instagram @cinemanizales_ficma, post a post',
   'capturado': '2026-09-17',
   'metodo': 'La web NO tiene parrilla: su menú solo ofrece ESTRENOS y TALLERES. El resto sale de los posts, que desde el 14 sep ya traen la función entera (día · hora · sede · acceso). Los pies se leyeron EN EL NAVEGADOR, con sesión: el endpoint de embed dejó de devolver el pie y da falso vacío.',
   'alcance': f'{len(F)} funciones publicadas. El festival declara «más de 60 proyecciones»: falta la inmensa mayoría. La franja académica va aparte, en ficma-2026-franja-web.json.'},
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
   'La página de talleres se volvió a leer el 17 sep, ya con parser: son ONCE actividades (ficma-2026-franja-web.json). El taller de Franco Lolli sigue anunciado en el párrafo de entrada y NO tiene ficha: preguntar si se cayó.',
   'Proimágenes (ntd=1320) sigue publicando las fechas de agosto.'],
 'funciones': fun}

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = REPO + '/festivals/staging/ficma-2026-reprogramado.json'
json.dump(out, open(D, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'{len(F)} funciones · días {sorted(set(x["dia"] for x in fun))}')
