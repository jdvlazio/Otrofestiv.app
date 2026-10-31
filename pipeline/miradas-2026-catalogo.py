#!/usr/bin/env python3
"""miradas-2026-catalogo.py — la selección de Miradas Medellín 2026 (Festival de
cine y artes audiovisuales, Medellín, 3–8 nov 2026). PRE-ONBOARDING.

LAS FUENTES: tres carruseles de @cinematecademedellin, leídos sin sesión por el
embed público (pipeline/ig_sin_sesion.py + ig.bajar_laminas → fuentes/ig/<sc>/):
  · DefnwMYDHVV (14 oct) — Largometrajes iberoamericanos: una lámina por obra con
    dirección, año, país, género, duración, idioma, sinopsis y sus funciones.
  · DeiGFLoIKqz (15 oct) — Cortometrajes iberoamericanos: igual.
  · DeX03IEDKSe (11 oct) — Cine hecho en Medellín: título + dirección, sin más.
Las iberoamericanas se leen por OCR (pipeline/ocr.py): el texto va en orden. Las
de Medellín están diagramadas en dos columnas que el OCR cruza: se TRANSCRIBEN a
ojo (HECHO_EN_MEDELLIN, abajo), lámina por lámina.

Las funciones que traen las láminas se guardan en `funciones_lamina` de cada
obra, verbatim, para el crudo que llegará con la parrilla completa.

OJO (Juan, 16 oct 2026): @cinematecademedellin publica TODA la programación de
la Cinemateca, y Miradas es UN festival dentro de ella, con sus fechas. Por eso
el script FRENA si un post no nombra a Miradas en el pie o si una función de
una lámina cae fuera del 3–8 nov: lo que no es del festival no entra.

Escribe festivals/staging/miradas-2026-catalogo.json
"""
import glob, io, json, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402
import ocr  # noqa: E402

OUT = f'{REPO}/festivals/staging/miradas-2026-catalogo.json'
POSTS = {'DefnwMYDHVV': 'Largometrajes Iberoamericanos', 'DeiGFLoIKqz': 'Cortometrajes Iberoamericanos'}
URL = 'https://www.instagram.com/p/{}/'
DIA = re.compile(r'^(Lunes|Martes|Miércoles|Jueves|Viernes|Sábado|Domingo) \d+ de noviembre')
FICHA = re.compile(r'^Dir(?:s|a|\.ª|ª)?[.:]?\s*(.+)$')

# Transcripción a ojo de DeX03IEDKSe, láminas 02–08 (16 oct 2026). La lámina dice
# «Dir.» o «Dir.ª»; se guarda el nombre tal cual lo pinta el festival.
HECHO_EN_MEDELLIN = [
    (2, 'Largometrajes', 'La pesadilla del siervo', 'Manuel Villa Machado'),
    (2, 'Largometrajes', 'Uno vuelve siempre', 'Camilo Ríos'),
    (2, 'Largometrajes', 'Chapecó, el último sobreviviente', 'Edison Vanegas Álvarez'),
    (3, 'Cortometrajes', 'Madres de nacimiento', 'Gloria Isabel Gómez Ceballos'),
    (3, 'Cortometrajes', 'Refracción', 'Isabella Palacio Mesa'),
    (3, 'Cortometrajes', 'La mona', 'Laura Gutiérrez'),
    (3, 'Cortometrajes', 'De Saúl', 'Santiago Gomxz'),
    (4, 'Cortometrajes', 'La danza de los ángeles', 'Juan Restrepo Molina'),
    (4, 'Cortometrajes', 'La escucha, la razón', 'Juan David Bolívar Araque'),
    (4, 'Cortometrajes', 'Luis Antonio', 'Juan José Arias Gil'),
    (5, 'Cortometrajes', 'Mal de tierra', 'Camila Caballero Guzmán'),
    (5, 'Cortometrajes', 'La muerte nos declaró adultos', 'Luisa María Charry Valencia'),
    (5, 'Cortometrajes', 'Kof kof', 'Juan David Cardona Arboleda'),
    (6, 'Cine Comunitario', 'Éther, somos todo', 'Fabián Cataño Torres'),
    (6, 'Cine Comunitario', 'El teléfono morado', 'Taller de Cine Corporación Mi Comuna'),
    (6, 'Cine Comunitario', 'Paralelo', 'Tania Díaz, Elsy Galeano'),
    (6, 'Cine Comunitario', 'Oro molido #2', 'Juan David Medrano'),
    # Fe de erratas del pie del post: «El proyecto "El paradero", de la selección
    # Cine comunitario, es realizado por Semillero Colectivo Cinestrato» (la
    # lámina 07 decía «Taller de Cine Corporación Mi Comuna»).
    (7, 'Cine Comunitario', 'El paradero', 'Semillero Colectivo Cinestrato'),
    (7, 'Cine Comunitario', 'Mamá Chila raíz y corazón de la comunidad', 'Dir. Colectiva'),
    (7, 'Cine Comunitario', 'Chico de barrio (videoclip animado)', 'Juan David Echavarría Urrego'),
    (8, 'Cine Expandido', 'Todas las cosas que algún día se desvanecieron', 'Carlos Eduardo Castaño Correa'),
    (8, 'Cine Expandido', 'Vórtice nebular', 'Diego Alberto Pérez Osorno'),
    (8, 'Cine Expandido', 'El sueño de Sedna', 'Felipe López'),
    (8, 'Cine Expandido', 'Sosiego al atardecer', 'Jose Luis Ruiz Peláez'),
]


# Lo que el OCR leyó mal, mirado en la lámina (16 oct 2026)
OCR_A_OJO = {'lan de la Rosa': 'Ian de la Rosa'}


def frase(t):
    """PROPUESTA de caja (las láminas van en mayúscula sostenida); el publicado
    lo da la ficha de TMDB o se confirma con Juan (caja-sostenida)."""
    t = t.lower()
    return re.sub(r'^(\W*)(\w)', lambda m: m.group(1) + m.group(2).upper(), t)


def ibero(sc, seccion):
    fs = sorted(glob.glob(f'{REPO}/fuentes/ig/{sc}/[0-9][0-9].jpg'))
    if not fs:
        sys.exit(f'✗ faltan las láminas de {sc}: python3 -c "import ig; ig.bajar_laminas(...)"')
    obras = []
    for f, lineas in ocr.leer(fs).items():
        ls = [x.strip() for x in lineas]
        i = next((k for k, x in enumerate(ls) if FICHA.match(x)), None)
        if i is None:
            continue                       # portada, cierre o logos
        titulo = ls[i - 1]
        ficha = ls[i]
        j = i + 1
        while j < len(ls) and not ls[j][:1].islower() and '•' in ls[j]:
            ficha += ' ' + ls[j]
            j += 1
        sinopsis, funciones = [], []
        for x in ls[j:]:
            if x.startswith('Medellín') or x.startswith('Mědellín'):
                break
            if DIA.match(x) or (funciones and not x.startswith('Funciones') and not DIA.match(x) and len(x) < 40 and x[:1].islower()):
                if DIA.match(x):
                    funciones.append(x)
                else:
                    funciones[-1] += ' ' + x
            elif x.startswith('Funciones con presencia'):
                pass
            elif not funciones:
                sinopsis.append(x)
        partes = [p.strip() for p in re.split(r'\s*•\s*', FICHA.match(ficha).group(1))]
        anio = re.search(r'\b(20\d\d)\b', ficha)
        dur = re.search(r'(\d+)\s*min', ' '.join(ls[i:i + 3]))
        obras.append({'titulo': frase(titulo), 'titulo_lamina': titulo,
                      'anio': int(anio.group(1)) if anio else None,
                      'duracion_min': int(dur.group(1)) if dur else None, 'seccion': seccion, 'ficha_lamina': ficha,
                      'director': OCR_A_OJO.get(partes[0], partes[0]), 'partes': partes[1:],
                      'sinopsis_es': ' '.join(sinopsis),
                      'con_presencia': any('presencia' in x for x in ls),
                      'funciones_lamina': funciones,
                      '_src': {'url': URL.format(sc), 'lamina': int(os.path.basename(f)[:2]), 'date': '2026-10-16'}})
    return obras


DIAS_FESTIVAL = range(3, 9)   # 3–8 de noviembre


def es_de_miradas(sc):
    pie = json.load(open(f'{REPO}/fuentes/ig/{sc}/post.json', encoding='utf-8')).get('pie') or ''
    if 'miradas' not in pie.lower():
        sys.exit(f'✗ {sc}: el pie no nombra a Miradas — puede ser programación regular de la Cinemateca')


# ── 23–25 oct 2026: tres carruseles más, con ficha COMPLETA y funciones ──────
# De2vCbSjAvy (23 oct) Cine Colombiano · Cortometrajes (7 obras nuevas)
# De5YY1EjVYl (25 oct) Cine Comunitario (las 7 de DeX03IEDKSe, ahora con ficha)
# De71yR-jinh (25 oct) Cine Hecho en Medellín · Cortometrajes (las 10, con ficha)
# Leídos con ig-lecturas.py (B sin corrector + C al doble; A vacío en De2v y el
# ALT no vino) y MIRADOS a ojo lámina por lámina (26 oct 2026). Se transcribe a
# ojo porque «El paradero» no lleva «Dir.» y el parser de ibero() lo saltaría.
# Tupla: (sc, lámina, título lámina, crédito, ficha, sinopsis, presencia, funciones)
LAMINAS_OCT = [
 ('De2vCbSjAvy', 1, 'El león', 'Diana Bustamante Escobar', 'Documental. Experimental • 15 min • Colombia • 2026 • Español',
  'Esta pieza documental da cuenta de cómo la muerte ha habitado paradójicamente el Auditorio León de Greiff de la Universidad Nacional, un lugar no concebido para ella.', None,
  ['Miércoles 4 de noviembre, 2:00 p. m. Teatro MAMM.', 'Viernes 6 de noviembre, 5:00 p. m. Centro Colombo Americano, Sala 2.']),
 ('De2vCbSjAvy', 2, 'Una vez en un cuerpo', 'María Cristina Pérez González', 'Animación • 10 min • Colombia • 2025 • Español',
  'Una mujer intenta reconciliarse con su hermana mientras lidia con un ser extraño en su interior. Al explorar sus experiencias a través del cuerpo, ambas enfrentan las huellas de su adolescencia y aquello que las habita.', None,
  ['Jueves 5 de noviembre, 2:00 p. m. Teatro MAMM.', 'Domingo 8 de noviembre, 4:00 p. m. Cineprox Las Américas, Sala 3.', '(Clausura) Domingo 8 de noviembre, 6:30 p.m. Parque de los Deseos, Plazoleta.']),
 ('De2vCbSjAvy', 3, 'Las formas de la magia', 'María Paula Lorgia Garnica', 'Documental • 17 min • Colombia • 2026 • Español',
  'Un año después de la muerte del mago Gustavo Lorgia, su hija explora archivos de video que revelan su trayectoria, su rol como padre y la estética televisiva de una época, convirtiendo la memoria en resistencia al olvido.', None,
  ['Miércoles 4 de noviembre, 2:00 p. m. Teatro MAMM.', 'Viernes 6 de noviembre, 5:00 p. m. Centro Colombo Americano, Sala 2.']),
 ('De2vCbSjAvy', 4, 'Emechiche, el renacimiento de los cabeciblancos', 'Juan Camilo González', 'Animación • 11 min • Colombia. Argentina • 2025',
  'En los Montes de María habita el emechiche (Saguinus oedipus), especie en peligro de extinción. Observamos sus vínculos con las crías y el entorno, explorando su supervivencia, sentimientos e instintos salvajes.', None,
  ['Miércoles 4 de noviembre, 5:00 p. m. Centro Colombo Americano, Sala 2.', 'Sábado 7 de noviembre, 7:00 p. m. Teatro MAMM.', 'Domingo 8 de noviembre, 6:30 p.m. Parque de los Deseos, Plazoleta. Clausura.']),
 ('De2vCbSjAvy', 5, 'Decaer', 'Juan Camilo González', 'Animación • 7 min • Colombia • 2026 • Español',
  'Gracias a los chinos por la pólvora, parece hecha para mí. Inventada por accidente para ahuyentar espíritus malignos, esta película viaja de China a Cartagena y culmina siglos después en Bogotá.', None,
  ['Miércoles 4 de noviembre, 2:00 p. m. Teatro MAMM.', 'Viernes 6 de noviembre, 5:00 p. m. Centro Colombo Americano, Sala 2.']),
 ('De2vCbSjAvy', 6, 'Mi viche todo el día', 'Juan Camilo Moreno', 'Documental • 26 min • Colombia • 2025 • Español',
  'En el Medio Atrato, Ana Panesso y su comunidad cultivan caña y producen viche. Entre el río y la música, Ana imagina un futuro donde esta bebida sea alimento, sustento e identidad para las familias negras.', None,
  ['Miércoles 4 de noviembre, 5:00 p. m. Centro Colombo Americano, Sala 2.', 'Sábado 7 de noviembre, 7:00 p. m. Teatro MAMM.']),
 ('De2vCbSjAvy', 7, 'Agachar el rostro', 'Camilo Medina Noy', 'Ficción • 12 min • Colombia • 2025 • Español',
  'Entre la niebla y las paredes agrietadas, un profesor vive su último día en una escuela rural que cierra por falta de estudiantes. En silencio, se despide del lugar que fue su hogar y oficio.', None,
  ['Jueves 5 de noviembre, 4:30 p. m. Teatro MAMM.', 'Sábado 7 de noviembre, 6:30 p. m. Centro Colombo Americano, Sala 2.']),
 ('De5YY1EjVYl', 1, 'Mamá Chila: raíz y corazón de la comunidad', 'Colectiva', 'Documental • 18 min • Colombia • 2025 • Español',
  'Retrato de la vida de María Lucila Pérez, Mamá Chila, una mujer del barrio Moravia dedicada al cuidado, el amor y la solidaridad. Su labor con niños, niñas y adultos mayores, covirtiéndose en un símbolo del cuidado comunitario.', None,
  ['Miércoles 28 de Octubre, 7: 00 pm, Cr 58 con Calle 83e Contiguo a la Sede de la Fundación Oasis Urbano.', 'Sábado 7 de noviembre, 1:00 p.m. Parque de los Deseos, Cinemateca Móvil.']),
 ('De5YY1EjVYl', 2, 'El paradero', 'Semillero Colectivo Cinestrato', 'Ficción. Documental • 9 min • Colombia • 2024 • Español',
  'Rolando, un habitante de calle que duerme con su perro junto a un paradero, despierta en medio de una movilización social. Marcado por un pasado violento en el campo, observa con escepticismo e ironía a sus participantes.', None,
  ['Sábado 7 de noviembre, 1:00 p.m. Parque de los Deseos, Cinemateca Móvil', 'Miércoles 4 de noviembre, 6:00 p.m. Café Pletórico, Castilla.']),
 ('De5YY1EjVYl', 3, 'Chico de barrio', 'Juan David Echavarría Urrego', 'Animación • 4 min • Colombia • 2026 • Español',
  'El videoclip animado Chico de Barrio sigue a Ragal X y Juan Niggas, artistas urbanos de comunidades excluidas que narran sus experiencias en una propuesta visual inspirada en los barrios y la identidad barrial de Medellín.', None,
  ['Miércoles 4 de Noviembre, 6:00 p.m. Teatro UVA Tricentenario.', 'Sábado 7 de noviembre, 1:00 p.m. Parque de los Deseos, Cinemateca Móvil.']),
 ('De5YY1EjVYl', 4, 'Oro molido #2', 'Juan David Medrano', 'Documental • 35 min • Colombia • 2024 • Español',
  'Oro Molido reúne cortos documentales sobre personas mayores de Santa Elena, sus historias de vida y aportes comunitarios. En primera persona, cada protagonista comparte sus sentires y formas de recordar.', None,
  ['Sábado 7 de noviembre, 1:00 p.m. Parque de los Deseos, Cinemateca Móvil.', 'Jueves 5 de noviembre, 10:00 a.m. Escuela Vereda el Placer, Corregimiento de Santa Elena.']),
 ('De5YY1EjVYl', 5, 'Éther, somos todos', 'Fabián Cataño Torres', 'Documental • 39 min • Colombia • 2024 • Español',
  'Éther, somos todo, explora la memoria y la resiliencia de la Comuna 13 a través del arte y los elementos de la naturaleza. Tierra, agua, aire y fuego representan historias de artistas que transforman el dolor en creación, memoria y esperanza.', None,
  ['Sábado 7 de noviembre, 1:00 p.m. Parque de los Deseos, Cinemateca Móvil.', 'Viernes 6 de noviembre, 7:00 p.m. Institución Educativa Pío XII.']),
 ('De5YY1EjVYl', 6, 'Paralelo', 'Escuela de Comunicación comunitaria', 'Ficción • 5 min • Colombia • 2025 • Español',
  'Entre cajas y adornos navideños, Rodrigo encuentra una foto que evoca recuerdos de familia, fútbol y música. Un balón lo devuelve al presente, donde su hija enciende velas ante un altar que honra el pasado.', None,
  ['Sábado 7 de noviembre, 1:00 p.m. Parque de los Deseos, Cinemateca Móvil', 'Viernes 6 de noviembre, 7:00 p.m. JAC Santa Cruz parte alta.']),
 ('De5YY1EjVYl', 7, 'El teléfono morado', 'Taller de Cine Corporación Mi Comuna', 'Documental • 10 min • Colombia • 2024 • Español',
  'En un entorno de apoyo femenino ante el patriarcado, Luna, una niña soñadora, halla un teléfono morado que la conecta con Nelly, una mujer de la montaña. En sus charlas, descubren su vínculo como mujeres.', None,
  ['Sábado 7 de noviembre, 1:00 p.m. Parque de los Deseos, Cinemateca Móvil.', 'Sábado 7 de noviembre, 7:00 p.m. Finca Agroturistica El Encanto de Mis Abuelos, Corregimiento de San Cristóbal, Vereda El Llano.']),
 ('De71yR-jinh', 1, 'La danza de los ángeles', 'Juan Restrepo Molina', 'Ficción. Experimental • 15 min • Colombia • 2026 • Español',
  'Un grupo de jóvenes regresan a la Tierra convertidos en ángeles invisibles para los mortales. Solo una vieja videocámara familiar logra captar el tenue rastro de su presencia.', 'Función con presencia del director',
  ['Miércoles 4 de noviembre, 2:00 p. m. Teatro MAMM.', 'Viernes 6 de noviembre, 5:00 p. m. Centro Colombo Americano, Sala 2.']),
 ('De71yR-jinh', 2, 'La escucha, la razón. Memoria de un mural', 'Juan David Bolívar Araque', 'Documental • 15 min • Colombia • 2026 • Español',
  'En el centro de Medellín, un mural inicia un viaje sonoro y humano. A través de artistas, habitantes y una Madre de La Candelaria, explora la escucha como acto de memoria, resistencia y búsqueda de la verdad.', 'Funciones con presencia del director',
  ['Miércoles 4 de noviembre, 5:00 p. m. Centro Colombo Americano, Sala 2.', 'Sábado 7 de noviembre, 7:00 p. m. Teatro MAMM.']),
 ('De71yR-jinh', 3, 'La muerte nos declaró adultos', 'Luisa María Charry Valencia', 'Documental. Experimental • 2 min • Colombia • 2026 • Español',
  'A través de mandalas fluorescentes y ecos de una voz, este viaje experimental convierte el tejido de un puente hacia la muerte en un ritual de memoria que evoca la nostalgia y abraza a quienes quedan.', 'Función con presencia de la directora',
  ['Miércoles 4 de noviembre, 2:00 p. m. Teatro MAMM.', 'Viernes 6 de noviembre, 5:00 p. m. Centro Colombo Americano, Sala 2.']),
 ('De71yR-jinh', 4, 'Madres de nacimiento', 'Gloria Isabel Gómez Ceballos', 'Documental • 8 min • Francia • 2026 • Español',
  'Imágenes y sonidos de archivo revelan cómo se ha controlado a las mujeres latinoamericanas, consideradas madres desde niñas. Una interferencia del pasado emerge para evocar la lucha, la memoria y la libertad.', 'Función con presencia del equipo',
  ['Jueves 5 de noviembre, 2:00 p. m. Teatro MAMM.', 'Domingo 8 de noviembre, 4:00 p. m. Cineprox Las Américas, Sala 3.']),
 ('De71yR-jinh', 5, 'Refracción', 'Isabella Palacio Mesa', 'Ficción • 11 min • Colombia • 2025 • Español',
  'Eloísa mantiene dos relaciones amorosas al mismo tiempo. Agobiada por el engaño, recorre en bicicleta las calles de Medellín, donde enfrenta su confusión, descubriendo, aunque no quiere reconocerse, debe encontrarse consigo misma.', 'Función con presencia de la directora',
  ['Jueves 5 de noviembre, 2:00 p. m. Teatro MAMM.', 'Domingo 8 de noviembre, 4:00 p. m. Cineprox Las Américas, Sala 2.', 'Domingo 8 de noviembre, 6:30 p. m. Parque de los Deseos, Plazoleta. Clausura.']),
 ('De71yR-jinh', 6, 'La mona', 'Laura Gutiérrez', 'Ficción • 18 min • Colombia • 2025 • Español',
  'En La Hondura, un caserío olvidado, La Mona, una paramilitar, impone el orden, pero la menstruación la obliga a guardar cama. Bajo su carácter esquivo, aflora su feminidad, revelando una sensibilidad.', 'Función con presencia de la directora',
  ['Jueves 5 de noviembre, 4:30 p. m. Teatro MAMM.', 'Sábado 7 de noviembre, 6:30 p. m. Centro Colombo Americano, Sala 2.']),
 ('De71yR-jinh', 7, 'De: Saúl', 'Santiago Gomez', 'Ficción. Experimental • 4 min • Colombia • 2026 • Español',
  'En sus sueños, Saúl ve a una pitonisa que le dice que la única manera de liberarse de su pecado es matar al pecador. Al recordar a un ser amado, su conflicto interno lo lleva a una lucha entre el perdón y la autodestrucción.', None,
  ['Jueves 5 de noviembre, 4:30 p. m. Teatro MAMM', 'Sábado 7 de noviembre, 6:30 p. m. Centro Colombo Americano, Sala 2.']),
 ('De71yR-jinh', 8, 'Kof - kof', 'Juan David Cardona Arboleda', 'Experimental • 7 min • Colombia • 2026 • Inglés',
  'Un pequeño cucarrón intenta escapar de una tela de araña que apenas comprende. Entre la calma y la agitación, se enreda, cae y vuelve a levantarse, insistiendo en moverse dentro de un espacio que parece no tener salida.', 'Funciones con presencia del director',
  ['Jueves 5 de noviembre, 4:30 p. m. Teatro MAMM.', 'Sábado 7 de noviembre, 6:30 p. m. Centro Colombo Americano, Sala 2.']),
 ('De71yR-jinh', 9, 'Luis Antonio', 'Juan José Arias Gil', 'Ficción • 12 min • Colombia • 2025 • Español',
  'Luis Antonio, un niño de ocho años, quiere aprender a montar bicicleta, pero su madre debe trabajar y lo deja al cuidado de Ofelia, su estricta vecina. Entre regaños y aburrimiento, espera junto a la ventana el regreso de su madre.', None,
  ['Viernes 6 de noviembre, 5:00 p. m. Cine en los Barrios -Estación Trece de Noviembre de la Línea M del Metrocable de Medellín.', 'Domingo 8 de noviembre, 2:00 p. m. Cinemateca Móvil.']),
 ('De71yR-jinh', 10, 'Mal de tierra', 'Camila Caballero Guzmán', 'Experimental • 10 min • Colombia • 2026 • Español',
  'Esta cinedanza explora la tensión entre las exigencias sociales y culturales del deber ser y los deseos íntimos. A través del cuerpo, revela una lucha interna y colectiva: la lucha feminista.', 'Funciones con presencia de la directora',
  ['Jueves 5 de noviembre, 2:00 p. m. Teatro MAMM.', 'Domingo 8 de noviembre, 4:00 p. m. Cineprox Las Américas, Sala 3.']),
]
SECCION_OCT = {'De2vCbSjAvy': 'Cine Colombiano · Cortometrajes', 'De5YY1EjVYl': 'Cine Comunitario',
               'De71yR-jinh': 'Cine Hecho en Medellín · Cortometrajes'}
# El título de DeX03IEDKSe (11 oct) que la lámina dedicada del 25 oct reescribe.
# Va a `titulos_anteriores`: el título de la lámina dedicada manda.
RENOMBRA_OCT = {'De Saúl': 'De: Saúl', 'Kof kof': 'Kof - kof', 'Éther, somos todo': 'Éther, somos todos',
                'La escucha, la razón': 'La escucha, la razón. Memoria de un mural',
                'Mamá Chila raíz y corazón de la comunidad': 'Mamá Chila: raíz y corazón de la comunidad',
                'Chico de barrio (videoclip animado)': 'Chico de barrio'}


def oct_laminas(obras):
    """Funde LAMINAS_OCT en el catálogo: completa las de DeX03IEDKSe, agrega las nuevas."""
    idx = {o['titulo']: o for o in obras}
    for sc, lam, tit, cred, ficha, sinop, pres, funcs in LAMINAS_OCT:
        es_de_miradas(sc)
        dentro = [f for f in funcs if (m := re.search(r'(\d+) de [Nn]oviembre', f)) and int(m.group(1)) in DIAS_FESTIVAL]
        fuera = [f for f in funcs if f not in dentro]
        viejo = next((k for k, v in RENOMBRA_OCT.items() if v == tit), None)
        o = idx.get(tit) or idx.get(viejo)
        if o is None:
            o = {'titulo': tit, 'director': cred}
            obras.append(o)
        if viejo and o['titulo'] == viejo:
            o['titulo'] = tit
            o['titulos_anteriores'] = [viejo]
        anio = re.search(r'\b(20\d\d)\b', ficha)
        dur = re.search(r'(\d+) min', ficha)
        o.update({'seccion': SECCION_OCT[sc], 'ficha_lamina': ('Dir. ' if sc != 'De5YY1EjVYl' or lam != 2 else '') + cred + ' • ' + ficha,
                  'anio': int(anio.group(1)) if anio else None, 'duracion_min': int(dur.group(1)),
                  'sinopsis_es': sinop, 'con_presencia': bool(pres), 'presencia_lamina': pres,
                  'funciones_lamina': dentro,
                  '_src': {'url': URL.format(sc), 'lamina': lam, 'date': '2026-10-26'}})
        if fuera:
            o['funciones_fuera_de_ventana'] = fuera   # solo días oficiales: se guardan, no se montan
    return obras


def main():
    for sc in [*POSTS, 'DeX03IEDKSe']:
        es_de_miradas(sc)
    obras = []
    for sc, sec in POSTS.items():
        obras += ibero(sc, sec)
    fuera = [(o['titulo'], f) for o in obras for f in o['funciones_lamina']
             if int(re.search(r'(\d+) de noviembre', f).group(1)) not in DIAS_FESTIVAL]
    if fuera:
        sys.exit(f'✗ funciones fuera del 3–8 nov (¿programación regular de la Cinemateca?): {fuera}')
    for lam, sec, tit, dire in HECHO_EN_MEDELLIN:
        obras.append({'titulo': tit, 'seccion': 'Cine Hecho en Medellín · ' + sec, 'director': dire,
                      '_src': {'url': URL.format('DeX03IEDKSe'), 'lamina': lam, 'date': '2026-10-16'}})
    obras = oct_laminas(obras)
    json.dump({'_provenance': provenance('@cinematecademedellin (6 carruseles, embed sin sesión)',
                                         metodo='OCR de láminas (iberoamericanas) + transcripción a ojo (Hecho en Medellín)'),
               'obras': obras}, io.open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'✓ {len(obras)} obras → {os.path.relpath(OUT, REPO)}')


if __name__ == '__main__':
    main()
