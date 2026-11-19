#!/usr/bin/env python3
"""provinciadevelez-2026-catalogo.py — 9.º Festival de Cine Provincia de Vélez
(Barbosa, Santander, 1–6 dic 2026). PRE-ONBOARDING (19 nov 2026), sin publicar.

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

TRIPLE LECTURA: (1) el arreglo de landing.js, (2) OCR del sistema
(pipeline/ocr.py) de las 29 láminas de IG y de los 29 pósteres de la web,
(3) las láminas a ojo (hojas de contacto). Lo que la lámina corrige va en _corrige.

COBERTURA INVERSA: web «29 obras» = 29 en landing.js = 13 + 14 láminas de los
dos posts del 7 nov + Saint Juanito y El pescador (videoclip) del post del 9 nov
(assert abajo). El post del afiche dice «más de 35 películas»: 29 + Bélier +
Sr. Fox + Bill W. + La imaginada + las dos de Dimaté = 35.

NINGUNA fuente trae duración; año solo algunos pósteres.
Escribe festivals/staging/provinciadevelez-2026-catalogo.json
"""
import io, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import slug  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = f'{REPO}/festivals/staging/provinciadevelez-2026-catalogo.json'
FECHA = '2026-11-19'
WEB = 'https://festivaldecineprovinciadevelez.com/'
IG = 'https://www.instagram.com/p/'
SO = 'Selección oficial'   # web: «Selección oficial» / «Convocatoria Saravita para nuevos realizadores»

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
F4_IMAG = ('2026-12-04', '18:00', 'La Tante Boutique', F4[3])

# (id web, título, categoría web, director, país, año, lámina IG, función, _corrige)
SEL = [
    ('anima-sola', 'Anima Sola', 'Cortometraje', 'Freddy Sanchez', 'Francia', None, 'DfcqutroV1z/13', F4,
     'lámina: «LA BRIQUE FILMS PRÉSENTE · UN FILM DE FREDDY SANCHEZ»'),
    ('entre-amigos', 'Entre amigos', 'Cortometraje', 'Edward Llanos, Simón Muñoz', 'Colombia', None, 'DfcqutroV1z/02', F4,
     'lámina: «DIRECCIÓN EDWARD LLANOS Y SIMÓN MUÑOZ · SIERRA NEVADA · PALOMINO - COLOMBIA»'),
    ('escision-cigarra', 'Escisión de la cigarra', 'Cortometraje', 'Absalón Rincón Muñoz', 'Colombia', 2025, 'DfcpGHfoWWI/14', None,
     'lámina: «GUION Y DIRECCIÓN ABSALON RINCON MUÑOZ» (OCR «MUÑO2»), «2025»; web: «PaloSeco · 2025»'),
    ('limones', 'Limones', 'Cortometraje', 'Sergio Fernández, Nicolás Duque', 'Colombia', None, 'DfcpGHfoWWI/12', F4,
     'lámina: «ESCUELA KINÉ PRESENTA · Un cortometraje de Sergio Fernández y Nicolás Duque»'),
    ('paisaje-niebla', 'Paisaje / Niebla', 'Cortometraje', 'Fabián Chávez', 'Colombia', None, 'DfcpGHfoWWI/09', F4,
     'lámina: «Un documental de Fabián Chávez · INPROFILMS · con el apoyo de IDARTES y LA SINFÓNICA DE BOGOTÁ»'),
    ('pez-azul', 'Pez azul', 'Cortometraje', 'J. Joel Gómez G.', 'Colombia', None, 'DfcpGHfoWWI/08', None,
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
    ('la-belleza', 'La Belleza', 'Documental', 'Nelson Silva', 'Colombia', None, 'DfcqutroV1z/12', None,
     'lámina: «UN DOCUMENTAL DE NELSON SILVA»'),
    ('dialogo-tierra', 'Un diálogo para sanar la Tierra', 'Documental', None, 'Colombia', None, 'DfcqutroV1z/08', None,
     'lámina: «(Incluye el visionado del documental Tanuzanamu: Principio del Equilibrio - Dir. Ati Güindiva '
     'Villafaña Mejia)» · Palomino, La Guajira; el director de la obra no se nombra'),
    ('uma-unjirinaka', 'Uma Unjirinaka · Alto Milluni', 'Documental', 'Left Hand Rotation', 'Bolivia', None, 'DfcqutroV1z/07', None,
     'lámina: «Una serie documental de Left Hand Rotation · UMA UÑJIRINAKA · Alto Milluni (CUIDADORXS DEL '
     'AGUA)»; la web escribe «Unjirinaka» (sin ñ)'),
    ('nueve-jueves', 'Nueve jueves en Riachuelo', 'Documental', 'Nelson Silva', 'Colombia', None, 'DfcqutroV1z/06', None,
     'lámina: «DIRIGIDO POR NELSON SILVA · Producción Edson Velandia»'),
    ('ecos-canaveral', 'Ecos del cañaveral', 'Documental', 'Juan Sebastián Parra', 'Colombia', None, 'DfcqutroV1z/05', None,
     'web: «Juan Sebastián Parra»; lámina: «DIRECCIÓN JUAN SEBASTIÁN PARRA»'),
    ('guali', 'Gualí', 'Documental', None, 'Colombia', 2025, 'DfcpGHfoWWI/13', None,
     'lámina: «Una producción de Los Pinos Films · 2025»; sin director nombrado'),
    ('oficios-fonce', 'Sinfonía incompleta de oficios del Fonce', 'Documental', 'Nelson Silva', 'Colombia', 2024, 'DfcpGHfoWWI/05', None,
     'lámina: «DIRECTOR Y PRODUCTOR EJECUTIVO NELSON SILVA»; web: «Nelson Silva · 2024»'),
    ('tradicion-prohibicion', 'De la tradición a la prohibición', 'Documental', None, None, None, 'DfcpGHfoWWI/04', F2,
     'lámina: «Producción: Charles Films / Dirección General: Lente Andino Films» — productora, no persona'),
    ('dolor-vientre', 'El dolor del vientre', 'Documental', 'María Candelaria Aldana', 'Colombia', None, 'DfcpGHfoWWI/03', None,
     'lámina: «DIRIGIDA POR: MARÍA CANDELARIA ALDANA, PRODUCIDA POR: VALENTINA SANTOS»'),
    ('llantos-monte', 'Llantos del monte', 'Videoclip', None, 'Argentina', None, 'DfcpGHfoWWI/11', None,
     'lámina: «Oberá - Misiones - Argentina · Cine Joven Comunitario»; sin director nombrado'),
    ('coming-from-hell', 'Coming from Hell', 'Videoclip', 'Klonazepan & Mafa', None, None, 'DfcqutroV1z/10', None,
     'lámina: «KLONAZEPAN & MAFA» — artistas, no dirección'),
    ('el-pescador-clip', 'El pescador', 'Videoclip', 'Juan Cruz', 'Puerto Rico, Colombia', None, 'DfhmCGsEZ84/03', F1,
     f'pie de {IG}DfzhWP2x_sy/: «Dirección Juan Cruz, Puerto Rico»; lámina: «(PUERTO RICO FT COL) · TALLER TOCA PLENA x CASA DEL SOL»'),
    ('el-empiezo', 'El empiezo', 'Videoclip', None, None, None, 'DfcpGHfoWWI/06', None,
     'lámina y web: solo el título'),
    ('saint-juanito', 'Saint Juanito', 'Videoclip', 'Chris Andree', 'Perú', None, 'DfhmCGsEZ84/02', F4,
     'lámina: «(PERÚ) · CHRIS ANDREE» — el artista; el pie del 19 nov: «Chris Andree explora…»'),
    ('el-cuarto', 'El cuarto', 'Filminuto', 'María Candelaria Aldana', 'Colombia', None, 'DfcqutroV1z/04', F4,
     'lámina: «UNA PELÍCULA DE: MARÍA CANDELARIA ALDANA»'),
    ('inmortalizar', 'El arte de inmortalizar mortales', 'Filminuto', 'Javier Jiménez Corzo', 'Colombia', None, 'DfcqutroV1z/15', None,
     'lámina: «BARICHARA EN FOTOS · Un filminuto de Javier Jiménez Corzo»'),
    ('olvidar-a-miriam', 'Olvidar a Miriam', 'Filminuto', 'Tatiana Lobera', 'Colombia', None, 'DfcpGHfoWWI/10', F4,
     'lámina: «LA PARCA FILMS PRESENTS A TATIANA LOBERA FILM»; web: «La Parca Films»'),
    ('latir-memoria', 'El latir de la memoria', 'Filminuto', 'Javier Jiménez Corzo', 'Colombia', None, 'DfcqutroV1z/11', F4,
     'lámina: «BARICHARA EN FOTOS · Un filminuto de Javier Jiménez Corzo»'),
]

# Sinopsis publicadas por el festival (pies de IG y web), tal cual
SINOPSIS = {
    'El pescador|Videoclip': (f'{IG}DfzhWP2x_sy/', 'Este videoclip relaciona la pesca del Caribe de Puerto Rico y '
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
    'Escisión de la cigarra': ('https://www.themoviedb.org/movie/1753860 (traducida del inglés)', 'En una vieja '
        'carpintería, Estiven se enfrenta a las almas y al eco incesante de las cigarras. Entre la vida y el limbo, su '
        'espíritu queda atrapado en un plano espiritual donde el trabajo inconcluso, la memoria y lo sobrenatural se '
        'funden en un estado de confusión.'),
    'El pescador|Cortometraje': ('https://www.themoviedb.org/movie/1558138 (traducida del inglés)', 'Un retrato '
        'íntimo del Caribe a través de la vida de quienes se dedican al mar. De la voz de un pescador puertorriqueño al '
        'vínculo entre un padre y su hijo en Colombia, la película muestra cómo la pesca une y distingue, y retrata un '
        'legado hecho de tradición, lucha y esperanza. Filmada en La Parguera (Lajas, Puerto Rico) y en Palomino '
        '(La Guajira, Colombia).'),
    'Ecos del cañaveral': ('https://www.themoviedb.org/movie/1753875 (traducida del inglés)', 'Cinco trabajadores de '
        'la caña de azúcar cuentan la historia de un oficio ancestral que se resiste al olvido y enfrenta un futuro '
        'incierto en el campo colombiano.'),
    'Nueve jueves en Riachuelo': ('festivals/cineparalapaz-2026.json (Cine para la Paz 2026)', 'Edson Velandia tiene '
        'nueve jueves y los recreos de un colegio para formar una orquesta. En Riachuelo, Santander, el primer reto es '
        'descubrir qué quiere tocar cada estudiante.'),
    'Llantos del monte': ('https://www.youtube.com/watch?v=gy-JVJUkNUY (canal Cine Tiza, 19 oct 2026)', 'Un joven '
        'camina por el monte con amigos, pero al quedarse solo, la soledad y los ruidos extraños lo llenan de terror. '
        'Luego de perder la conciencia, despierta en una habitación misteriosa donde un ser espiritual le revela '
        'realidades sobre el mundo y el desequilibrio que gobierna el universo.'),
    # Texto pintado en el afiche oficial (lámina del festival), a falta de otra sinopsis hallada
    'La Belleza': ('https://www.instagram.com/p/DfcqutroV1z/ (afiche, lámina 12)', 'Un documental dedicado a La Belleza, Santander, en su '
        'quincuagésimo aniversario de vida jurídica: un municipio de paisajes increíbles y gente tenaz, ejemplo de '
        'progreso, paz y resiliencia en la provincia veleña.'),
    'El dolor del vientre': ('https://www.instagram.com/p/DfcpGHfoWWI/ (afiche, lámina 3)', 'De amores y tambores: cuando el canto se '
        'envuelve en los vientres de quienes de luto visten, las gargantas se cierran y el silencio empieza a primar.'),
    'El arte de inmortalizar mortales': ('https://www.instagram.com/p/DfcqutroV1z/ (afiche, lámina 15)', 'Don Antonio: la memoria esculpida '
        'que da la bienvenida o el último adiós.'),
    'Titua y oro': ('https://www.instagram.com/p/DfcqutroV1z/ (afiche, lámina 14)', 'El levantamiento de un templo sagrado femenino y el '
        'regreso de un ritual antiguo musical.'),
    'Un diálogo para sanar la Tierra': ('https://www.instagram.com/p/DfcqutroV1z/ (afiche, lámina 8)', 'Entendiendo la labor de los Mamos '
        'para armonizar el universo. Incluye el visionado del documental «Tanuzanamu: Principio del equilibrio», de '
        'Ati Güindiva Villafaña Mejía.'),
    'Ayuno y cenizas': (WEB,'Lleva la tragedia de Edipo Rey a las tragedias urbanas de los jóvenes colombianos de hoy.'),
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
    ('La imaginada', 'Carolina Muñoz', 'corto', None, F4_IMAG,
     'pie Df7ZYXrEaXh: «película de 20 minutos inspirada en Barbosa, nominada a la India Catalina, que se presentó en '
     'el 2016 … presencia de la escritora y directora Carolina Muñoz»; hora del pie (6.00 pm), no de las láminas'),
    ('Tres lunas nuevas', 'Rodrigo Dimaté', 'largo', 'Muestra central', None,
     'web: «es una de las películas de la muestra central, y su director nos acompaña en el festival»; sin día ni hora'),
    ('Ayuno y cenizas', 'Rodrigo Dimaté', 'largo', 'Muestra central', None,
     'web: «también de Rodrigo Dimaté y estreno nacional, es la otra película de la muestra central»; sin día ni hora'),
]


def funcion(f):
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
        else:
            o['franja'] = 'sin día ni hora publicados (19 nov)'
        s = SINOPSIS.get(f'{tit}|{cat}') or (SINOPSIS.get(tit) if (tit, cat) != ('El pescador', 'Cortometraje') else None)
        if s:
            o['sinopsis'], o['_sinopsis_de'] = s[1], s[0]
        _a = f'assets/provinciadevelez-2026/{slug(tit)}{"-videoclip" if wid == "el-pescador-clip" else ""}.jpg'
        if os.path.exists(f'{REPO}/{_a}'):
            o['afiche'] = _a
            o['_afiche_de'] = f'lámina {IG}{lam} (afiche recortado de la lámina del festival)'
        obras.append(o)
    for tit, dire, tipo, sec, fun, ev in OTRAS:
        o = {'titulo': tit, 'director': dire, 'tipo': tipo, '_evidencia': ev,
             '_src': {'url': WEB, 'date': FECHA}}
        if sec:
            o['seccion'] = sec
        if fun:
            o['funcion'] = funcion(fun)
        else:
            o['franja'] = 'sin día ni hora publicados (19 nov)'
        if tit in SINOPSIS:
            o['sinopsis'], o['_sinopsis_de'] = SINOPSIS[tit][1], SINOPSIS[tit][0]
        _a = f'assets/provinciadevelez-2026/{slug(tit)}.jpg'
        if os.path.exists(f'{REPO}/{_a}'):
            o['afiche'] = _a
            o['_afiche_de'] = 'cartelera de la web del festival'
        obras.append(o)
    d = {'_provenance': {'fuente': f'{WEB} (landing.js: 29 obras) + IG @9_festcineprovinciadevelez (Bright Data)',
                         'capturado': FECHA,
                         'metodo': 'arreglo de landing.js + OCR del sistema (pipeline/ocr.py) de 29+29 láminas + a ojo'},
         'obras': obras}
    io.open(OUT, 'w', encoding='utf-8').write(json.dumps(d, ensure_ascii=False, indent=1) + '\n')
    print(f'{len(obras)} obras → {OUT}')


if __name__ == '__main__':
    main()
