#!/usr/bin/env python3
"""provinciadevelez-2026-catalogo.py — 9.º Festival de Cine Provincia de Vélez
(Barbosa y Vélez, Santander, 30 nov–6 dic 2026). PRE-ONBOARDING (19 nov; funciones al 24 nov 2026), sin publicar.

LAS FUENTES (fuentes/provinciadevelez-2026/, gitignored):
  · web/home.html + web/landing.js + web/contenido.js — festivaldecineprovinciadevelez.com
    (bajada 19 nov). landing.js trae el arreglo de la selección: 29 obras con
    título, categoría, créditos y póster (web/sel/<poster>.jpg). La home trae la
    franja infantil (Bélier mar 1, Sr. Fox jue 3) y la muestra central de Rodrigo
    Dimaté sin día ni hora.
  · ig/ — IG @9_festcineprovinciadevelez por Bright Data (sin sesión):
      DfcpGHfoWWI (7 nov, 14 láminas) + DfcqutroV1z (7 nov, 15) = selección Saravita
      DfhmCGsEZ84 (9 nov, 5) categoría videoclip · DfihtPIRt2g (9 nov) afiche
      DfxyKI-S9LA / DfzhWP2x_sy / Df2AcYNEbXC / Df4hzKXkYiP / Df7ZYXrEaXh
      (15–19 nov): las láminas con día, hora y sede de cada función.

  · (24 nov) IG Df-DlZyERf2 (8 láminas, 30 nov SENA) y DgFiVrTEbh0 (6, sáb 5 dic), Df71yg2P6hF
    (La imaginada). Facebook festivaldecinebarbosa (fb/, 18 posts de Bright Data, 5 adjuntos
    por post): mismas láminas, cortadas en 5; las completas son las de IG.

TRIPLE LECTURA: (1) el arreglo de landing.js, (2) OCR del sistema
(pipeline/ocr.py) de las 29 láminas de IG y de los 29 pósteres de la web,
(3) las láminas a ojo (hojas de contacto). Lo que la lámina corrige va en _corrige.

COBERTURA INVERSA: web «29 obras» = 29 en landing.js = 13 + 14 láminas de los
dos posts del 7 nov + Saint Juanito y El pescador (videoclip) del post del 9 nov
(assert abajo). El post del afiche dice «más de 35 películas»: 29 + Bélier +
Sr. Fox + Bill W. + La imaginada + las dos de Dimaté = 35. El 20 nov suma tres que la
web no trae: Puchucollo Alto (Saravita), Una mala chicha es un guarapo y Entre Ríos = 38.


DOS OBRAS «El pescador» (corto y videoclip, mismo equipo): el videoclip se nombra con
su categoría, «El pescador (videoclip)», para no heredar la ficha del corto (TMDB 1558138).
Las duraciones halladas fuera van en festivals/staging/<fid>-duraciones.json.
Escribe festivals/staging/provinciadevelez-2026-catalogo.json
"""
import io, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import slug  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = f'{REPO}/festivals/staging/provinciadevelez-2026-catalogo.json'
FECHA = '2026-11-25'
WEB = 'https://festivaldecineprovinciadevelez.com/'
IG = 'https://www.instagram.com/p/'
FB25 = 'https://www.facebook.com/festivaldecinebarbosa/posts/pfbid02fqEztN5KAMM1Ro3k4YYZ61BBVJwtd7myTLcnZyVFp8qtAkX3ygDGrYRBDc18297Ul'
SO = 'Selección oficial'   # web: «Selección oficial» / «Convocatoria Saravita para nuevos realizadores»

# La función del 30 nov (SENA, Vélez; IG Df-DlZyERf2) NO se monta: el afiche oficial dice
# «DEL 1 AL 6 DE DICIEMBRE» y solo van los días oficiales (Juan, 24 nov 2026). Sus obras
# quedan en el catálogo; Alto Milluni y Un diálogo conservan la del 5 dic.
F5 = ('2026-12-05', '18:00', 'Parque Emilio Ulloa',
      f'{IG}DgFiVrTEbh0/ (6 láminas, 23 nov): «PARQUE EMILIO ULLOA · SÁBADO 5 DE DICIEMBRE · DESDE LAS 6:00 DE LA '
      'TARDE» pintado en cada una; FB 23 nov, mismo post con 5 de las 6')
# Las funciones con día/hora/sede, tal cual las láminas de IG
F1 = ('2026-12-01', '18:00', 'Casa Escuela Formación Musical Leo Olarte',
      f'{IG}DfxyKI-S9LA/ + {IG}DfzhWP2x_sy/: «1 DE DICIEMBRE · CASA ESCUELA FORMACIÓN MUSICAL LEO OLARTE · '
      'AL FRENTE DE LA CANCHA DEL MARSELLA · 6:00 P.M.»; la web: «Casa de formación musical Leo el Arte, '
      'frente a la cancha del Marsella. Antes, cortos para niños.»')
F2 = ('2026-12-02', '19:00', 'Grupo Central AA',
      f'{IG}Df2AcYNEbXC/: «MUESTRA ESPECIAL BARBOSA · MIÉRCOLES 2 DE DICIEMBRE · 7:00 P.M. · '
      'Carrera 7# 6-46 Sotano · Grupo Central AA»')
F3 = ('2026-12-03', '18:00', 'Casa Taller Palo de Mango',
      f'{IG}Df4hzKXkYiP/: «JUEVES 3 DE DICIEMBRE · 6 P.M. · EN CASA TALLER PALO DE MANGO · Pasos arriba del '
      'Moncada, Barrio Marsella»; la web: «Jueves 3 de diciembre · 6:00 p. m.»')
F4 = ('2026-12-04', '19:00', 'La Tante Boutique',
      f'{IG}Df7ZYXrEaXh/: láminas «VIERNES 4 DE DICIEMBRE · DESDE LAS 7:00 P. M. · La Tante · Barbosa» '
      '(la de Cicatrices: «La Tante Boutique Barbosa»); el pie: «el 04 de diciembre desde las 6.00pm … '
      'La imaginada … Seguiremos con once (11) hermosos trabajos de la selección oficial»')
F6 = ('2026-12-02', '18:00', 'Parque Central Cite',
      f'{FB25} (4 láminas, 25 nov): «CONVOCATORIA SARAVITA DOCUMENTAL · PARQUE CENTRAL CITE · MIÉRCOLES 2 DE DICIEMBRE · '
      'DESDE LAS 6:00 P.M.» pintado en cada una')
F4_IMAG = ('2026-12-04', '18:00', 'La Tante Boutique', F4[3])

# (id web, título, categoría web, director, país, año, lámina IG, función, _corrige)
SEL = [
    ('anima-sola', 'Anima Sola', 'Cortometraje', 'Freddy Sanchez', 'Francia', None, 'DfcqutroV1z/13', F4,
     'lámina: «LA BRIQUE FILMS PRÉSENTE · UN FILM DE FREDDY SANCHEZ»'),
    ('entre-amigos', 'Entre amigos', 'Cortometraje', 'Edward Llanos, Simón Muñoz', 'Colombia', None, 'DfcqutroV1z/02', F4,
     'lámina: «DIRECCIÓN EDWARD LLANOS Y SIMÓN MUÑOZ · SIERRA NEVADA · PALOMINO - COLOMBIA»'),
    ('escision-cigarra', 'Escisión de la cigarra', 'Cortometraje', 'Absalón Rincón Muñoz', 'Colombia', 2025, 'DfcpGHfoWWI/14', F5,
     'lámina: «GUION Y DIRECCIÓN ABSALON RINCON MUÑOZ» (OCR «MUÑO2»), «2025»; web: «PaloSeco · 2025»'),
    ('limones', 'Limones', 'Cortometraje', 'Sergio Fernández, Nicolás Duque', 'Colombia', None, 'DfcpGHfoWWI/12', F4,
     'lámina: «ESCUELA KINÉ PRESENTA · Un cortometraje de Sergio Fernández y Nicolás Duque»'),
    ('paisaje-niebla', 'Paisaje / Niebla', 'Cortometraje', 'Fabián Chávez', 'Colombia', None, 'DfcpGHfoWWI/09', F4,
     'lámina: «Un documental de Fabián Chávez · INPROFILMS · con el apoyo de IDARTES y LA SINFÓNICA DE BOGOTÁ»'),
    ('pez-azul', 'Pez azul', 'Cortometraje', 'J. Joel Gómez G.', 'Colombia', None, 'DfcpGHfoWWI/08', F6,
     'lámina: «UN CORTOMETRAJE DE JOEL GÓMEZ»; laureles de 2019'),
    ('salvemos-el-agua', 'Salvemos el agua', 'Cortometraje', None, 'Colombia', None, 'DfcpGHfoWWI/07', F3,
     'lámina: «Cortometraje realizado en el marco de un proceso de cine comunitario en Palomino, La Guajira» '
     '· Escuela Kiné · Fundación Nukuba; sin director nombrado'),
    ('cicatrices', 'Cicatrices', 'Cortometraje', 'Jhon Amado', 'Colombia', 2026, 'DfcpGHfoWWI/02', F4,
     'lámina: «DIRIGIDA POR JHON AMADO … FILIPINAS - ARAUCA 2026»; web: «Filipinas, Arauca»'),
    ('el-pescador', 'El pescador', 'Cortometraje', 'Juan Cruz', 'Puerto Rico, Colombia', None, 'DfcqutroV1z/03', F4,
     'lámina: «DIRIGIDO POR JUAN CRUZ PARA TALLER TOCA PLENA & CASA DEL SOL» (OCR «CAUZ»)'),
    ('creation-unicorn', 'Creation of a Unicorn', 'Experimental', None, None, None, 'DfcqutroV1z/09', F4,
     'lámina: solo el título; sin créditos en ninguna fuente'),
    ('titua-y-oro', 'Titua y oro', 'Documental', 'Daniela Herrera', 'Colombia', None, 'DfcqutroV1z/14', None,
     'lámina: «DIRECTED BY DANIELA HERRERA · FESTIVAL CINE PALOMINO»'),
    ('la-belleza', 'La Belleza', 'Documental', 'Nelson Silva', 'Colombia', None, 'DfcqutroV1z/12', F6,
     'lámina: «UN DOCUMENTAL DE NELSON SILVA»'),
    ('dialogo-tierra', 'Un diálogo para sanar la Tierra', 'Documental', None, 'Colombia', None, 'DfcqutroV1z/08', F5,
     'lámina: «(Incluye el visionado del documental Tanuzanamu: Principio del Equilibrio - Dir. Ati Gündiwa '
     'Villafaña Mejia)» · Palomino, La Guajira; el director de la obra no se nombra'),
    ('uma-unjirinaka', 'Uma Uñjirinaka · Alto Milluni', 'Documental', 'Left Hand Rotation', 'Bolivia', None, 'DfcqutroV1z/07', F5,
     'lámina: «Una serie documental de Left Hand Rotation · UMA UÑJIRINAKA · Alto Milluni (CUIDADORXS DEL '
     'AGUA)»; la web escribe «Unjirinaka» (sin ñ)'),
    ('nueve-jueves', 'Nueve jueves en Riachuelo', 'Documental', 'Nelson Silva', 'Colombia', None, 'DfcqutroV1z/06', F6,
     'lámina: «DIRIGIDO POR NELSON SILVA · Producción Edson Velandia»'),
    ('ecos-canaveral', 'Ecos del cañaveral', 'Documental', 'Juan Sebastián Parra', 'Colombia', None, 'DfcqutroV1z/05', None,
     'web: «Juan Sebastián Parra»; lámina: «DIRECCIÓN JUAN SEBASTIÁN PARRA»'),
    ('guali', 'Gualí', 'Documental', None, 'Colombia', 2025, 'DfcpGHfoWWI/13', None,
     'lámina: «Una producción de Los Pinos Films · 2025»; sin director nombrado'),
    ('oficios-fonce', 'Sinfonía incompleta de oficios del Fonce', 'Documental', 'Nelson Silva', 'Colombia', 2024, 'DfcpGHfoWWI/05', F6,
     'lámina: «DIRECTOR Y PRODUCTOR EJECUTIVO NELSON SILVA»; web: «Nelson Silva · 2024»'),
    ('tradicion-prohibicion', 'De la tradición a la prohibición', 'Documental', None, None, None, 'DfcpGHfoWWI/04', F2,
     'lámina: «Producción: Charles Films / Dirección General: Lente Andino Films» — productora, no persona'),
    ('dolor-vientre', 'El dolor del vientre', 'Documental', 'María Candelaria Aldana', 'Colombia', None, 'DfcpGHfoWWI/03', F5,
     'lámina: «DIRIGIDA POR: MARÍA CANDELARIA ALDANA, PRODUCIDA POR: VALENTINA SANTOS»'),
    ('llantos-monte', 'Llantos del monte', 'Videoclip', None, 'Argentina', None, 'DfcpGHfoWWI/11', F5,
     'lámina: «Oberá - Misiones - Argentina · Cine Joven Comunitario»; sin director nombrado'),
    ('coming-from-hell', 'Coming from Hell', 'Videoclip', 'Klonazepan & Mafa', None, None, 'DfcqutroV1z/10', None,
     'lámina: «KLONAZEPAN & MAFA» — artistas, no dirección'),
    ('el-pescador-clip', 'El pescador (videoclip)', 'Videoclip', 'Juan Cruz', 'Puerto Rico, Colombia', None, 'DfhmCGsEZ84/03', F1,
     f'pie de {IG}DfzhWP2x_sy/: «Dirección Juan Cruz, Puerto Rico»; lámina: «(PUERTO RICO FT COL) · TALLER TOCA PLENA x CASA DEL SOL»'),
    ('el-empiezo', 'El empiezo', 'Videoclip', None, None, None, 'DfcpGHfoWWI/06', None,
     'lámina y web: solo el título'),
    ('saint-juanito', 'Saint Juanito', 'Videoclip', 'Sebastián Tapia', 'Perú', None, 'DfhmCGsEZ84/02', F4,
     'lámina: «(PERÚ) · CHRIS ANDREE» — el artista; dirige Sebastián Tapia (créditos del video oficial, youtube QQ1G_ps-A34); el pie del 19 nov: «Chris Andree explora…»'),
    ('el-cuarto', 'El cuarto', 'Filminuto', 'María Candelaria Aldana', 'Colombia', None, 'DfcqutroV1z/04', F4,
     'lámina: «UNA PELÍCULA DE: MARÍA CANDELARIA ALDANA»'),
    ('inmortalizar', 'El arte de inmortalizar mortales', 'Filminuto', 'Javier Jiménez Corzo', 'Colombia', None, 'DfcqutroV1z/15', F5,
     'lámina: «BARICHARA EN FOTOS · Un filminuto de Javier Jiménez Corzo»'),
    ('olvidar-a-miriam', 'Olvidar a Miriam', 'Filminuto', 'Tatiana Lobera', 'Colombia', None, 'DfcpGHfoWWI/10', F4,
     'lámina: «LA PARCA FILMS PRESENTS A TATIANA LOBERA FILM»; web: «La Parca Films»'),
    ('latir-memoria', 'El latir de la memoria', 'Filminuto', 'Javier Jiménez Corzo', 'Colombia', None, 'DfcqutroV1z/11', F4,
     'lámina: «BARICHARA EN FOTOS · Un filminuto de Javier Jiménez Corzo»'),
]

# Sinopsis publicadas por el festival (pies de IG y web), tal cual
SINOPSIS = {
    'Olvidar a Miriam': (f'{IG}Df7ZYXrEaXh/', 'El minuto recorre la tristeza de la vejez y a través del tango transmite el sentimiento de una lágrima por la nostalgia.'),
    'Entre amigos': (f'{IG}Df7ZYXrEaXh/', 'Buscando escapar de la rutina de la ciudad, un grupo de jóvenes visita a una amiga que vive sola en las montañas. Rodeados por la inmensidad del paisaje y el silencio del campo, escuchan los relatos que ella conoce sobre la región.'),
    'Limones': (f'{IG}Df7ZYXrEaXh/', 'Cristian y Andrés, dos niños wayuu de nueve años, recorren las calles de Palomino vendiendo limones. Mientras trabajan, escuchan y comentan en segundo plano la desaparición de Bartolo, ocurrida durante los recientes enfrentamientos armados en la Sierra Nevada. Al caer la noche, regresan a casa y entregan el producido a su madre.'),
    'Una mala chicha es un guarapo': (f'{IG}Df-DlZyERf2/', 'A Eulalio se le presenta la tentación de vender las tierras que han pasado de generación en generación en su familia. Un poco de chicha le ayudará a tomar la mejor decisión.'),
    'Uma Uñjirinaka · Alto Milluni': (f'{IG}DgFiVrTEbh0/', 'Muestra el testimonio y lucha de las comunidades indígenas afectadas por la contaminación del agua en la cuenca Katari - Lago Titicaca en Bolivia. En Alto Milluni, cuya agua naciente es robada a diario para ser llevada a la mega-urbe El Alto, las mujeres proponen un proyecto de turismo comunitario local para la supervivencia.'),
    'Uma Uñjirinaka · Puchucollo Alto': (f'{IG}Df-DlZyERf2/', 'Muestra el testimonio y lucha de las comunidades indígenas urbanas y rurales afectadas por la contaminación del agua en la cuenca Katari - Lago Titicaca en Bolivia. En Puchukollo Alto, periferia de la mega-urbe El Alto, las familias de la comunidad defienden el acuífero allí situado contra la usurpación y contaminación de sus aguas.'),
    'El pescador (videoclip)': (f'{IG}DfzhWP2x_sy/', 'Este videoclip relaciona la pesca del Caribe de Puerto Rico y '
        'La Guajira, y persigue los pasos de Neymar, un niño de La Guajira que aprende la pesca desde temprana edad.'),
    'Salvemos el agua': (f'{IG}Df4hzKXkYiP/', 'El cortometraje propone una aventura en la que la sabiduría ancestral '
        'y la creatividad infantil se encuentran para reflexionar sobre el cuidado de los ríos, la biodiversidad y la vida.'),
    'De la tradición a la prohibición': (f'{IG}Df2AcYNEbXC/', 'Es un documental que explora la evolución de las '
        'plantas sagradas de poder desde los rituales ancestrales hasta su estigmatización y prohibición en la sociedad '
        'contemporánea. La película se sitúa en un contexto latinoamericano para cuestionar los discursos oficiales que '
        'han criminalizado estos saberes, revelando procesos de despojo cultural y ruptura de la memoria colectiva.'),
    'Saint Juanito': (f'{IG}Df7ZYXrEaXh/', 'Desde lo más profundo de la selva peruana, donde la extraordinaria belleza '
        'natural convive con duras realidades, Saint Juanito nos invita a emprender un viaje a través de las luces y '
        'sombras de nuestra Amazonía.'),
    'El latir de la memoria': (f'{IG}Df7ZYXrEaXh/', 'Después de 15 años de ausencia, el reloj de la Inmaculada vuelve '
        'a latir en Barichara.'),
    'Paisaje / Niebla': (f'{IG}Df7ZYXrEaXh/', 'Este cortometraje, grabado en el Páramo de Sumapaz, es un acercamiento '
        'poético a la vida de este territorio, que observa su inmensidad pero también su lado más oscuro: la violencia '
        'que sufrió hace años.'),
    'La imaginada': (f'{IG}Df7ZYXrEaXh/', 'A través de un diálogo íntimo entre el documental y la ficción, La imaginada '
        'recorre la memoria colectiva y los relatos orales de Barbosa, Santander, para revelar cómo sus habitantes han '
        'construido su identidad a lo largo del tiempo.'),
    'Tres lunas nuevas': (WEB, 'Cuenta cómo abrir una pequeña puerta en la juventud puede traer problemas enormes: '
        'quien siembra vientos cosecha tempestades.'),
    # Traducidas por nosotros del inglés de TMDB (única sinopsis hallada), con el contexto de la lámina
    'Escisión de la cigarra': (f'{IG}DgFiVrTEbh0/', 'Estiven, un joven aprendiz de carpintero, trabaja con dedicación en un taller donde conviven el eco de las herramientas y las advertencias de su maestro Orlando. Una noche, entre el polvo de la madera y ruidos inexplicables, un accidente lo sumerge en un tránsito incierto entre la vida y la muerte.'),
    'El pescador': ('https://www.themoviedb.org/movie/1558138 (traducida del inglés)', 'Un retrato '
        'íntimo del Caribe a través de la vida de quienes se dedican al mar. De la voz de un pescador puertorriqueño al '
        'vínculo entre un padre y su hijo en Colombia, la película muestra cómo la pesca une y distingue, y retrata un '
        'legado hecho de tradición, lucha y esperanza. Filmada en La Parguera (Lajas, Puerto Rico) y en Palomino '
        '(La Guajira, Colombia).'),
    'Ecos del cañaveral': (f'{IG}Df-DlZyERf2/', 'En el corazón del trapiche, donde el sonido de la caña molida acompaña las jornadas de trabajo, Ecos del cañaveral retrata la vida de cinco campesinos hacedores de panela que han dedicado su existencia a un oficio ancestral.'),
    'Nueve jueves en Riachuelo': ('festivals/cineparalapaz-2026.json (Cine para la Paz 2026)', 'Edson Velandia tiene '
        'nueve jueves y los recreos de un colegio para formar una orquesta. En Riachuelo, Santander, el primer reto es '
        'descubrir qué quiere tocar cada estudiante.'),
    'Llantos del monte': ('https://www.youtube.com/watch?v=gy-JVJUkNUY (canal Cine Tiza, 19 oct 2026)', 'Un joven '
        'camina por el monte con amigos, pero al quedarse solo, la soledad y los ruidos extraños lo llenan de terror. '
        'Luego de perder la conciencia, despierta en una habitación misteriosa donde un ser espiritual le revela '
        'realidades sobre el mundo y el desequilibrio que gobierna el universo.'),
    'La Belleza': (FB25, 'La historia del municipio de La Belleza, Santander, es contada por sus propias voces. Desde lo poco que se sabe de sus habitantes precolombinos, los Tisquizoques, hasta nuestros días, se revela la historia fundacional del municipio, pasando por los capítulos más aciagos y de cómo al día de hoy es un remanso de paz de exuberante belleza.'),
    'Sinfonía incompleta de oficios del Fonce': (FB25, 'En un viaje de imágenes acompasadas al ritmo de la música, nos adentramos en sitios emblemáticos pero inaccesibles de San Gil. La cámara revela el interior de las fábricas y los oficios que allí aún perviven: manos, engranajes, máquinas, instrumentos musicales y su armonía, en una sinfonía audiovisual que permite conocer estos lugares.'),
    'Pez azul': (FB25, 'Una niña emprende un viaje bastante conmovedor para sanar y para dejar ir. Su madre siempre la acompañará.'),
    'El dolor del vientre': (f'{IG}DgFiVrTEbh0/', 'Entre amores y tambores, una madre recuerda la partida de un hijo y las vivencias nostálgicas de su tambor.'),
    'El arte de inmortalizar mortales': ('https://www.instagram.com/p/DfcqutroV1z/ (afiche, lámina 15)', 'Don Antonio: la memoria esculpida '
        'que da la bienvenida o el último adiós.'),
    'Titua y oro': ('https://www.instagram.com/p/DfcqutroV1z/ (afiche, lámina 14)', 'El levantamiento de un templo sagrado femenino y el '
        'regreso de un ritual antiguo musical.'),
    'Un diálogo para sanar la Tierra': ('https://www.instagram.com/p/DfcqutroV1z/ (afiche, lámina 8)', 'Entendiendo la labor de los Mamos '
        'para armonizar el universo. Incluye el visionado del documental «Tanuzanamu: Principio del equilibrio», de '
        'Ati Gündiwa Villafaña Mejía.'),
    'Gualí': ('https://www.facebook.com/festivaldecinebarbosa (20 nov; el final del pie viene cortado)', 'En el corazón de la sabana de Bogotá, el humedal Gualí es un santuario de biodiversidad. El documental se sumerge en su riqueza natural a través de una narrativa visual poética.'),
    'Ayuno y cenizas': (WEB,'Lleva la tragedia de Edipo Rey a las tragedias urbanas de los jóvenes colombianos de hoy.'),
}

# Sinopsis en inglés: traducción nuestra de la española publicada (24 nov 2026)
SINOPSIS_EN = {
    "Nueve jueves en Riachuelo": "Edson Velandia has nine Thursdays and a school’s recess breaks to form an orchestra. In Riachuelo, Santander, the first challenge is discovering what each student wants to play.",
    "Sinfonía incompleta de oficios del Fonce": "On a journey of images set to the rhythm of music, we enter emblematic but inaccessible places in San Gil. The camera reveals the inside of the factories and the trades that still survive there: hands, gears, machines, musical instruments and their harmony, in an audiovisual symphony that lets us get to know these places.",
    "Pez azul": "A girl sets out on a quite moving journey to heal and to let go. Her mother will always be with her.",
    "La Belleza": "The story of the municipality of La Belleza, Santander, is told by its own voices. From the little that is known of its pre-Columbian inhabitants, the Tisquizoques, to the present day, its founding history is revealed, through its darkest chapters and on to how today it is an exuberantly beautiful haven of peace.",
    "De la tradición a la prohibición": "A documentary exploring the evolution of sacred plants of power, from ancestral rituals to their stigmatization and prohibition. In a Latin American context, it questions the official narratives that have criminalized this knowledge and reveals processes of cultural dispossession and the rupture of collective memory.",
    "El arte de inmortalizar mortales": "Don Antonio: the sculpted memory that bids welcome or the last farewell.",
    "El dolor del vientre": "Amid loves and drums, a mother remembers a son's departure and the nostalgic moments lived with his drum.",
    "El latir de la memoria": "After 15 years of absence, the Inmaculada clock beats again in Barichara.",
    "El pescador (videoclip)": "This music video links fishing in the Caribbean of Puerto Rico and La Guajira, following Neymar, a boy from La Guajira who learns to fish from an early age.",
    "Entre amigos": "Seeking to escape the routine of the city, a group of young people visit a friend who lives alone in the mountains. Surrounded by the vastness of the landscape and the silence of the countryside, they listen to the stories she knows about the region.",
    "Gualí": "In the heart of the Bogotá savanna, the Gualí wetland is a sanctuary of biodiversity. The documentary immerses itself in its natural wealth through a poetic visual narrative.",
    "La imaginada": "Through an intimate dialogue between documentary and fiction, La imaginada travels through the collective memory and oral stories of Barbosa, Santander, to reveal how its inhabitants have built their identity over time.",
    "Limones": "Cristian and Andrés, two nine-year-old Wayuu boys, roam the streets of Palomino selling limes. As they work, they hear and comment on, in the background, the disappearance of Bartolo, which occurred during the recent armed clashes in the Sierra Nevada. At nightfall, they return home and hand over their earnings to their mother.",
    "Llantos del monte": "A young man walks through the woods with friends, but when he is left alone, solitude and strange noises fill him with terror. After losing consciousness, he wakes in a mysterious room where a spiritual being reveals to him realities about the world and the imbalance that governs the universe.",
    "Olvidar a Miriam": "This one-minute film travels through the sadness of old age and, through tango, conveys the feeling of a tear shed out of nostalgia.",
    "Paisaje / Niebla": "This short film, shot in the Sumapaz páramo, is a poetic approach to life in this territory, looking at its vastness but also its darkest side: the violence it suffered years ago.",
    "Saint Juanito": "From the depths of the Peruvian jungle, where extraordinary natural beauty coexists with harsh realities, Saint Juanito invites us on a journey through the lights and shadows of our Amazon.",
    "Salvemos el agua": "The short film offers an adventure in which ancestral wisdom and children's creativity come together to reflect on caring for rivers, biodiversity and life.",
    "Uma Uñjirinaka · Alto Milluni": "It shows the testimony and struggle of the Indigenous communities affected by water pollution in the Katari - Lake Titicaca basin in Bolivia. In Alto Milluni, whose spring water is stolen daily to be taken to the megacity of El Alto, the women propose a local community tourism project in order to survive.",
    "Uma Uñjirinaka · Puchucollo Alto": "It shows the testimony and struggle of the urban and rural Indigenous communities affected by water pollution in the Katari - Lake Titicaca basin in Bolivia. In Puchukollo Alto, on the outskirts of the megacity of El Alto, the families of the community defend the aquifer located there against the seizure and pollution of its waters.",
    "Un diálogo para sanar la Tierra": "Understanding the Mamos' work to harmonize the universe. Includes a screening of the documentary “Tanuzanamu: Principio del equilibrio”, by Ati Gündiwa Villafaña Mejía.",
    "Una mala chicha es un guarapo": "Eulalio is tempted to sell the land that has been in his family for generations. A little chicha will help him make the best decision.",
}

# Fuera de la selección: (título, director, tipo, rótulo del festival, función, evidencia)
OTRAS = [
    ('La familia Bélier', 'Éric Lartigau', 'largo', 'Franja infantil', F1,
     'web «Franja infantil» + lámina «MUESTRA ESPECIAL · FRANJA INFANTIL»'),
    ('El fantástico Sr. Fox', 'Wes Anderson', 'largo', 'Franja infantil', F3,
     'web «Franja infantil · Wes Anderson · stop motion» + lámina «MUESTRA ESPECIAL · FRANJA PARA NIÑOS»'),
    ('My Name Is Bill W.', 'Daniel Petrie', 'largo', 'Muestra especial', F2,
     'lámina «MUESTRA ESPECIAL BARBOSA»; el afiche dice «My Name is Bill W.» (James Woods, JoBeth Williams, '
     'James Garner); el pie del 17 nov la presenta como «La caída»'),
    ('La imaginada', 'Carolina Muñoz', 'corto', 'Muestra especial', F4_IMAG,
     'pie Df7ZYXrEaXh: «película de 20 minutos inspirada en Barbosa, nominada a la India Catalina, que se presentó en '
     'el 2016 … presencia de la escritora y directora Carolina Muñoz»; lámina Df71yg2P6hF (y FB 19 nov): «MUESTRA ESPECIAL LA IMAGINADA 2016 – 2026 · DIRECTORA CAROLINA MUÑOZ · VIERNES 4 DE DICIEMBRE · DESDE LAS 6:00 P. M. · LA TANTE · BARBOSA»'),
    ('Uma Uñjirinaka · Puchucollo Alto', 'Left Hand Rotation', 'corto', SO, None,
     'lámina Df-DlZyERf2/02: «CONVOCATORIA SARAVITA · DOCUMENTAL · Una serie documental de Left Hand Rotation · UMA '
     'UÑJIRINAKA · Puchucollo Alto (CUIDADORXS DEL AGUA) · SELECCIÓN OFICIAL 2026»; no está en las 29 de la web; '
     'el pie escribe «Puchukollo Alto»'),
    ('Una mala chicha es un guarapo', 'Wilson Beltrán, Wilson Valderrama', 'corto', 'Muestra especial', None,
     'lámina Df-DlZyERf2/04: «MUESTRA ESPECIAL · EL ARTE COMO RESISTENCIA Y SALVACIÓN · Un Film De Cine Club Barbosa & '
     'Celuloide · Realizado Por Wilson Beltran, Wilson Valderrama»'),
    ('Entre Ríos. Todos somos hermanos', None, 'corto', 'Muestra especial', None,
     'lámina Df-DlZyERf2/08: «MUESTRA ESPECIAL · EL ARTE COMO RESISTENCIA Y SALVACIÓN · Entre Ríos · Todos somos '
     'hermanos»; sin créditos; tipo supuesto por la portada (documental y cortometraje), sin duración'),
    ('Tres lunas nuevas', 'Rodrigo Dimaté', 'largo', 'Muestra central', ('2026-12-05', '20:00', 'Parque Emilio Ulloa', 'correo del festival a hola@otrofestiv.app, 27 nov 2026 (4 láminas)'),
     'web: «es una de las películas de la muestra central, y su director nos acompaña en el festival»; sin día ni hora'),
    ('Ayuno y cenizas', 'Rodrigo Dimaté', 'largo', 'Muestra central', ('2026-12-06', '20:00', 'Estación del Tren', 'correo del festival a hola@otrofestiv.app, 27 nov 2026 (4 láminas)'),
     'web: «también de Rodrigo Dimaté y estreno nacional, es la otra película de la muestra central»; sin día ni hora'),
]


_LAM = 'afiche recortado de la lámina del festival'
LAMINA_DE = {'La imaginada': f'lámina {IG}Df71yg2P6hF ({_LAM})',
             'Uma Uñjirinaka · Puchucollo Alto': f'lámina {IG}Df-DlZyERf2/02 ({_LAM})',
             'Una mala chicha es un guarapo': f'lámina {IG}Df-DlZyERf2/04 ({_LAM})'}


def funcion(f):
    if f and isinstance(f[0], tuple):
        f = f[0]
    return None if not f else {'fecha': f[0], 'hora': f[1], 'sede': f[2], '_evidencia': f[3]}


def main():
    assert len(SEL) == 29, 'la web dice 29 obras'
    assert sum(1 for s in SEL if s[6].startswith('DfcpGHfoWWI')) == 13
    assert sum(1 for s in SEL if s[6].startswith('DfcqutroV1z')) == 14
    assert sum(1 for s in SEL if s[7] is F4) == 11, 'el pie del 19 nov: «once (11) trabajos»'
    obras = []
    for wid, tit, cat, dire, pais, anio, lam, fun, cor in SEL:
        o = {'titulo': tit, 'director': dire, 'pais': pais, 'anio': anio, 'tipo': 'corto',
             'seccion': SO, 'categoria': cat,
             'imagen_web': f'fuentes/provinciadevelez-2026/web/sel/{wid}.jpg',
             'lamina_ig': f'fuentes/provinciadevelez-2026/ig/{lam}.jpg',
             '_corrige': cor,
             '_src': {'url': WEB, 'ig': IG + lam.split('/')[0] + '/', 'date': FECHA}}
        o = {k: v for k, v in o.items() if v is not None}
        if fun:
            o['funcion'] = funcion(fun)
            if isinstance(fun[0], tuple):
                o['funciones'] = [funcion(x) for x in fun]
        else:
            o['franja'] = 'sin función en los días oficiales (1–6 dic)'
        s = SINOPSIS.get(tit)
        if s:
            o['sinopsis'], o['_sinopsis_de'] = s[1], s[0]
        _a = f'assets/provinciadevelez-2026/{"clip-el-pescador" if wid == "el-pescador-clip" else slug(tit)}.jpg'
        if os.path.exists(f'{REPO}/{_a}'):
            o['afiche'] = _a
            o['_afiche_de'] = f'lámina {IG}{lam} (afiche recortado de la lámina del festival)'
        obras.append(o)
    for tit, dire, tipo, sec, fun, ev in OTRAS:
        o = {'titulo': tit, 'director': dire, 'tipo': tipo, '_evidencia': ev,
             '_src': {'url': WEB, 'date': FECHA}}
        if tit.startswith('Uma '):
            o['pais'], o['categoria'] = 'Bolivia', 'Documental'
        if o['director'] is None:
            del o['director']
        if tit in ('La imaginada', 'Una mala chicha es un guarapo'):
            o['pais'] = 'Colombia'   # «hecha en Barbosa por una barboseña» (web); Cine Club Barbosa (lámina)
        if sec:
            o['seccion'] = sec
        if fun:
            o['funcion'] = funcion(fun)
        else:
            o['franja'] = 'sin función en los días oficiales (1–6 dic)'
        if tit in SINOPSIS:
            o['sinopsis'], o['_sinopsis_de'] = SINOPSIS[tit][1], SINOPSIS[tit][0]
        _a = f'assets/provinciadevelez-2026/{slug(tit)}.jpg'
        if os.path.exists(f'{REPO}/{_a}'):
            o['afiche'] = _a
            o['_afiche_de'] = LAMINA_DE.get(tit, 'cartelera de la web del festival')
        obras.append(o)
    for o in obras:
        if o['titulo'] in SINOPSIS_EN:
            o['synopsis_en'] = SINOPSIS_EN[o['titulo']]
    d = {'_provenance': {'fuente': f'{WEB} (landing.js: 29 obras) + IG @9_festcineprovinciadevelez (Bright Data)',
                         'capturado': FECHA,
                         'metodo': 'arreglo de landing.js + OCR del sistema (pipeline/ocr.py) de 29+29 láminas + a ojo'},
         'obras': obras}
    io.open(OUT, 'w', encoding='utf-8').write(json.dumps(d, ensure_ascii=False, indent=1) + '\n')
    print(f'{len(obras)} obras → {OUT}')


if __name__ == '__main__':
    main()
