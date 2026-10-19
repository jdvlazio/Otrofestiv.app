#!/usr/bin/env python3
"""guatape-2026-crudo.py — la programación del Guatapé Film Fest 2026 → crudo.

LA FUENTE es el carrusel oficial de programación de @guatapefilmfest,
`p/Def6fhKDSQy` del 14 oct 2026: 11 láminas. La 00 es la portada, la 10 dice
«Todos los días» (ferias sin hora ni lugar) y las 01–09 son la agenda. Las nueve
de la agenda son LAS MISMAS imágenes que publicó Vivir en El Poblado el 16 oct;
se comprobó con el OCR, lámina por lámina (Jaccard 0,95–1,00). La transcripción
a ojo se hizo sobre las de VEP y por eso guarda su numeración; VEP_A_OFICIAL la
traduce.

DOS LECTURAS: la transcripción A OJO (fuentes/guatape-2026/guatape-2026-laminas-
ojos.json), verbatim y con las erratas, y el OCR de la lámina oficial. Cada hora
y cada palabra del título tienen que aparecer en SU lámina, o el paso falla.

EL CRUDO ES LA FUENTE PRINCIPAL, entera: las 54 líneas de la agenda. Lo que la
corrige —otra fuente o una decisión— es una AFIRMACIÓN en
festivals/staging/guatape-2026-afirmaciones.json (docs/FUNCION.md), no una
tabla de este script: los dos cócteles de invitados que no se publican, y lo
que el afiche de las masterclass (p/DehGQpgoAvX, 15 oct) dice distinto de la
agenda (14 oct). La duración que la lámina no da la estima el modelo.

Decisiones de Juan del 18 oct 2026 («Dale» a la propuesta):
  · las secciones sin el lema «El Reflejo del Cine» y en caja de Título;
  · los dos programas homónimos de la Competencia Nacional de Cine
    Universitario, distinguidos con «· Programa 1» y «· Programa 2».

LO QUE NO ENTRA AL CRUDO: la lámina 10, «Todos los días» (Feria Geek, Feria
Gastronómica, Festival Cervecero, exposición «La Trama que Somos»): no da hora
ni lugar, así que no es una función.
"""
import io
import json
import os
import re
import subprocess
import sys
import unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402

FID = 'guatape-2026'
POST = 'Def6fhKDSQy'
LAMINAS = f'{REPO}/fuentes/ig/{POST}'
OJOS = f'{REPO}/fuentes/{FID}/{FID}-laminas-ojos.json'
OUT = f'{REPO}/festivals/staging/guatape-2026-crudo.json'
SRC = {'url': f'https://www.instagram.com/p/{POST}/', 'date': '2026-10-14'}

# lámina de Vivir en El Poblado → lámina del carrusel oficial (por OCR)
VEP_A_OFICIAL = {1: 1, 2: 2, 3: 3, 4: 7, 5: 6, 6: 5, 7: 4, 8: 8, 9: 9}

# ── LAS SECCIONES: encabezado de la lámina → sección (decisión de Juan) ──────
SECCION = {
    'MUESTRA DE CINE COMUNITARIO COLOMBIANO': 'Muestra de Cine Comunitario Colombiano',
    'MUESTRA CINE COMUNITARIO COLOMBIANO': 'Muestra de Cine Comunitario Colombiano',
    'COMPETENCIA NACIONAL DE CINE UNIVERSITARIO': 'Competencia Nacional de Cine Universitario',
    'COMPETENCIA INTERNACIONAL DE CORTOMETRAJES': 'Competencia Internacional de Cortometrajes',
    'COMPETENCIA INTERNACIONAL DE LARGOMETRAJE': 'Competencia Internacional de Largometraje',
    'COMPETENCIA INTERNACIONAL DE LARGOMETRAJES': 'Competencia Internacional de Largometraje',
    'MUESTRA CINE COLOMBIANO': 'Muestra de Cine Colombiano',
    'MUESTRA DE CINE COLOMBIANO': 'Muestra de Cine Colombiano',
    'EL REFELJO DEL CINE RUMBO A LOS MACONDO': 'Rumbo a los Macondo',
    'El REFLEJO DEL CINE RUMBO A LOS MACONDO': 'Rumbo a los Macondo',
    'EL REFLEJO DEL CINE RUMBO A LOS MACONDO': 'Rumbo a los Macondo',
    'EL REFLEJO DEL CINE – FIACINE': 'FIACINE',
    'EL REFLEJO DEL CINE - CINEMA LUNA': 'Cinema Luna',
    'El REFLEJO DEL CINE - CINEMA LUNA': 'Cinema Luna',
    'El REFLEJO DEL CINE MUESTRA LOCAL': 'Muestra Local',
    'El REFLEJO DEL CINE TERROR': 'Terror',
    'EL REFLEJO DEL CINE': 'El Reflejo del Cine',
    'Película Inaugural': 'Película Inaugural',
}
ACTIVIDADES = 'Actividades'

# ── LAS PROYECCIONES: (día, hora, encabezado) → título y obras ──────────────
# El título va como lo escribe la lámina, salvo la mayúscula sostenida, que
# pasa a caja de frase («UN POETA» → «Un poeta», «CULEBRA NEGRA» → «Culebra
# negra»). Un programa de cortos que el festival no nombra se titula con su
# sección (PROTOCOLO §4: el conjunto lo nombra el festival, acá con su sección).
U = 'Competencia Nacional de Cine Universitario'
PROYECCION = {
    ('2026-10-21', '14:00', 'EL REFLEJO DEL CINE'): {'titulo': 'Allá Cartas al Corazón'},
    ('2026-10-21', '18:00', 'MUESTRA DE CINE COMUNITARIO COLOMBIANO'): {'titulo': 'Ipatu'},
    ('2026-10-21', '18:15', 'COMPETENCIA NACIONAL DE CINE UNIVERSITARIO'): {'titulo': 'La fuente'},
    ('2026-10-21', '18:00', 'COMPETENCIA INTERNACIONAL DE CORTOMETRAJES'): {
        'titulo': 'Competencia Internacional de Cortometrajes',
        'obras': [{'titulo': 'Planeta Fome', 'pais': 'Brasil'},
                  {'titulo': 'La Parada del Colectivo', 'pais': 'Argentina'},
                  {'titulo': 'Una muñeca vestida de Azul', 'pais': 'España'}]},
    ('2026-10-21', '18:00', 'Película Inaugural'): {'titulo': 'Un poeta', 'premiere': 'Película inaugural'},
    ('2026-10-22', '18:00', 'COMPETENCIA NACIONAL DE CINE UNIVERSITARIO'): {
        'titulo': f'{U} · Programa 1',
        'obras': [{'titulo': 'Hasta que amanezca', 'pais': 'Colombia'},
                  {'titulo': 'El Umbral', 'pais': 'Colombia'}]},
    ('2026-10-22', '18:30', 'EL REFELJO DEL CINE RUMBO A LOS MACONDO'): {'titulo': 'Basta Mamá'},
    ('2026-10-22', '18:00', 'MUESTRA CINE COLOMBIANO'): {'titulo': 'La Gran Hazaña'},
    ('2026-10-22', '18:30', 'EL REFLEJO DEL CINE – FIACINE'): {'titulo': 'Niño de las Brisas', 'publicar': 'Niños de Las Brisas'},
    ('2026-10-22', '18:00', 'El REFLEJO DEL CINE RUMBO A LOS MACONDO'): {'titulo': 'Horizonte'},
    ('2026-10-23', '18:00', 'COMPETENCIA NACIONAL DE CINE UNIVERSITARIO'): {
        'titulo': f'{U} · Programa 2',
        'obras': [{'titulo': 'Carola', 'pais': 'Colombia'},
                  {'titulo': 'La Ultima Palabra', 'pais': 'Colombia'}]},
    ('2026-10-23', '18:30', 'EL REFLEJO DEL CINE RUMBO A LOS MACONDO'): {'titulo': 'Culebra negra'},
    ('2026-10-23', '18:30', 'EL REFLEJO DEL CINE - CINEMA LUNA'): {'titulo': 'Leo tus Labios'},
    ('2026-10-23', '18:00', 'MUESTRA DE CINE COMUNITARIO COLOMBIANO'): {'titulo': 'Luma'},
    ('2026-10-23', '18:20', 'MUESTRA DE CINE COLOMBIANO'): {'titulo': 'Luis Antonio'},
    ('2026-10-23', '18:00', 'COMPETENCIA INTERNACIONAL DE LARGOMETRAJES'): {'titulo': 'Sobre las olas', 'pais': 'México'},
    ('2026-10-24', '18:00', 'El REFLEJO DEL CINE MUESTRA LOCAL'): {
        'titulo': 'Muestra Local',
        'obras': [{'titulo': 'El Gesto de la Muerte'}, {'titulo': 'Cosas que Pasan'},
                  {'titulo': 'El último Biscocho'}]},
    ('2026-10-24', '18:00', 'MUESTRA CINE COMUNITARIO COLOMBIANO'): {'titulo': 'Cicatrices'},
    ('2026-10-24', '18:30', 'COMPETENCIA INTERNACIONAL DE LARGOMETRAJE'): {'titulo': 'El convento', 'pais': 'España'},
    ('2026-10-24', '18:30', 'El REFLEJO DEL CINE - CINEMA LUNA'): {'titulo': 'Volar'},
    ('2026-10-24', '18:00', 'El REFLEJO DEL CINE TERROR'): {'titulo': 'La Sierra'},
    ('2026-10-25', '18:00', 'MUESTRA DE CINE COLOMBIANO'): {'titulo': 'La Gallina Saraviada'},
    ('2026-10-25', '18:20', 'MUESTRA DE CINE COLOMBIANO'): {'titulo': 'Sangre de Palermo'},
    ('2026-10-25', '18:00', 'COMPETENCIA INTERNACIONAL DE LARGOMETRAJE'): {'titulo': 'Canelones', 'pais': 'Argentina'},
}

# ── LAS ACTIVIDADES: (día, hora, encabezado) → título, clase y descripción ───
# Título = el encabezado de la lámina (caja de Título si viene sostenido);
# event_kind = la palabra del festival en la línea de abajo; la descripción es
# esa línea, tal cual (las erratas del festival incluidas).
ACTIVIDAD = {
    ('2026-10-21', '09:00', 'Cine para reflejar territorio'): {'titulo': 'Cine para reflejar territorio', 'kind': 'taller'},
    ('2026-10-22', '14:00', 'Territorios que Filman'): {'titulo': 'Territorios que Filman', 'kind': 'encuentro'},
    ('2026-10-22', '10:30', 'El Reflejo de la Memoria'): {'titulo': 'El Reflejo de la Memoria', 'kind': 'conversatorio'},
    ('2026-10-22', '11:00', 'El Reflejo entre Regiones'): {'titulo': 'El Reflejo entre Regiones', 'kind': 'entrega'},
    ('2026-10-22', '13:00', 'Me Llamo Tierra'): {'titulo': 'Me Llamo Tierra', 'kind': 'obra de títeres'},
    ('2026-10-22', '14:00', 'El Reflejo de las Generaciones'): {'titulo': 'El Reflejo de las Generaciones', 'kind': 'taller'},
    ('2026-10-22', '14:00', 'Taller Memoria y Patrimonio Visual'): {'titulo': 'Taller Memoria y Patrimonio Visual', 'kind': 'taller'},
    ('2026-10-22', '14:00', 'El REFLEJO DE UN ACTOR'): {'titulo': 'El Reflejo de un Actor', 'kind': 'conversatorio'},
    ('2026-10-23', '09:00', 'Territorios que Filman'): {'titulo': 'Territorios que Filman', 'kind': 'encuentro'},
    ('2026-10-23', '13:00', 'Detrás del Reflejo -El Productor'): {'titulo': 'Detrás del Reflejo - El Productor', 'kind': 'conversatorio'},
    ('2026-10-23', '14:00', 'CONCEPT ART (2JORNADAS)'): {'titulo': 'Concept Art para Cine', 'kind': 'masterclass',
                                                         'inscripcion': True, 'recurrente': True,
                                                         'afiche': 'concept-art-para-cine.jpg'},
    ('2026-10-23', '14:00', 'Reflejos de un personaje'): {'titulo': 'Reflejos de un Personaje', 'kind': 'taller'},
    ('2026-10-23', '14:00', 'Taller Memoria y Patrimonio Visual'): {'titulo': 'Taller Memoria y Patrimonio Visual', 'kind': 'taller'},
    ('2026-10-23', '14:00', 'Conversatorio Actores'): {'titulo': 'Conversatorio Actores', 'kind': 'conversatorio'},
    ('2026-10-23', '14:00', 'Conversatorio Historias que se Juegan'): {'titulo': 'Conversatorio Historias que se Juegan', 'kind': 'conversatorio'},
    ('2026-10-23', '18:30', 'Historias que se Juegan'): {'titulo': 'Historias que se Juegan', 'kind': 'taller'},
    ('2026-10-23', '20:00', 'Concierto El Reflejo del Cine'): {'titulo': 'Concierto El Reflejo del Cine', 'kind': 'concierto'},
    ('2026-10-24', '10:00', 'Cine y Nuevas Narrativas'): {'titulo': 'Cine y Nuevas Narrativas', 'kind': 'masterclass',
                                                          'inscripcion': True,
                                                          'afiche': 'cine-y-nuevas-narrativas.jpg'},
    ('2026-10-24', '09:00', 'CONCEPT ART (2JORNADAS)'): {'titulo': 'Concept Art para Cine', 'kind': 'masterclass',
                                                         'inscripcion': True, 'recurrente': True,
                                                         'afiche': 'concept-art-para-cine.jpg'},
    ('2026-10-24', '13:30', 'Cine con legado Social'): {'titulo': 'Cine con Legado Social', 'kind': 'conversatorio'},
    ('2026-10-24', '14:00', 'Reflejos de un personaje'): {'titulo': 'Reflejos de un Personaje', 'kind': 'taller'},
    ('2026-10-24', '15:00', 'Reflejos Sonoros'): {'titulo': 'Reflejos Sonoros', 'kind': 'concierto'},
    ('2026-10-24', '19:30', 'Premiación Competencia y reconocimientos - El REFLEJO DEL CINE'):
        {'titulo': 'Premiación Competencia y Reconocimientos', 'kind': 'premiación'},
    ('2026-10-24', '21:00', 'Fiesta Electrónica'): {'titulo': 'Fiesta Electrónica', 'kind': 'fiesta'},
    ('2026-10-25', '11:00', 'EL REFLEJO DE LOS FESTIVALES'): {'titulo': 'El Reflejo de los Festivales', 'kind': 'conversatorio'},
    ('2026-10-25', '13:30', 'Tres miradas, un reflejo'): {'titulo': 'Tres Miradas, un Reflejo', 'kind': 'conversatorio'},
    ('2026-10-25', '14:00', 'SANGRE DE PALERMO Y SU REFLEJO'): {'titulo': 'Sangre de Palermo y su Reflejo', 'kind': 'conversatorio'},
    ('2026-10-25', '20:00', 'Clausura EL REFLEJO DEL CINE'): {'titulo': 'Clausura El Reflejo del Cine', 'kind': 'clausura'},
    # los dos cócteles: la afirmación existe:false los saca (son de invitados)
    ('2026-10-21', '20:00', 'Coctel Inaugural'): {'titulo': 'Coctel Inaugural', 'kind': 'cóctel'},
    ('2026-10-22', '18:00', 'COCTEL INVITADOS'): {'titulo': 'Coctel Invitados', 'kind': 'cóctel'},
}

# ── LOS CRÉDITOS QUE LA LÁMINA NO TRAE, con su fuente ───────────────────────
# Solo los de obras SIN ficha en TMDB (las que tienen ficha van fijadas en
# -correcciones.json → fichas). Una obra sin fuente que la ligue con certeza al
# festival se queda sin crédito.
CREDITOS = {
    'Sangre de Palermo': {'director': 'Edwin Daniel Díaz, Alejandro Aguilar', 'anio': 2025, 'duracion_min': 93,
                          '_fuente': 'https://lavillaproducciones.com/la-sangre-de-palermo',
                          '_por_que': 'la productora la acredita y nombra a María Irene Toro en el reparto, la misma '
                                      'actriz que el festival anuncia para su conversatorio (p/Deenf5Tu8vO)'},
    'Leo tus Labios': {'director': 'Daniel Bautista', 'anio': 2026, 'duracion_min': 147,
                       '_fuente': 'https://www.elheraldo.co/contenidos-en-alianza/2026/04/30/leo-tus-labios-un-reencuentro-que-desafia-el-tiempo-y-pone-a-prueba-el-amor/',
                       '_por_que': 'estrenó en la Cinemateca del Caribe el 30 abr 2026; va en la sección Cinema Luna, '
                                   'aliado del festival (@cinemalunafilms en el pie de la programación)'},
    # LAS DE FICHA EN TMDB (-correcciones → fichas): TMDB verifica la dirección
    # pero no la publica —la dirección sale de la fuente—, y la lámina no la trae
    'Basta Mamá': {'director': 'Flora Martínez', '_fuente': 'https://www.themoviedb.org/movie/1627217'},
    'Horizonte': {'director': 'César Augusto Acevedo', '_fuente': 'https://www.themoviedb.org/movie/1265716'},
    'Culebra negra': {'director': 'Aurélien Vernhes-Lermusiaux', '_fuente': 'https://www.themoviedb.org/movie/1018962'},
    'Sobre las olas': {'director': 'Horacio Alcalá', '_fuente': 'https://www.themoviedb.org/movie/1478001'},
    'El convento': {'director': 'Ángel M. Chivite, Luis Galindo', '_fuente': 'https://www.themoviedb.org/movie/1361852'},
    'Canelones': {'director': 'Christian Basilis, Ana Laura Gussoni', '_fuente': 'https://www.themoviedb.org/movie/1743296'},
    'Un poeta': {'director': 'Simón Mesa Soto', '_fuente': 'https://www.themoviedb.org/movie/1465563'},
    'Niños de Las Brisas': {'director': 'Marianela Maldonado', '_fuente': 'https://www.themoviedb.org/movie/995319'},
    # LAS QUE YA PUBLICAMOS en otro festival: el director corrobora la identidad
    # para la cascada (lib.ya_publicada: con el título solo no entra). Cada una
    # dice qué la sostiene; las de la lámina con ciudad, también la ciudad.
    'La Gran Hazaña': {'director': 'Luber Yesid Zúñiga Ordóñez',
                       '_por_que': 'corto colombiano en «Muestra de Cine Colombiano»; ya circuló por 7 de nuestros '
                                   'festivales (Ficcali, FICDEH, FICICA, Ficmontañas, Popayán, SiembraFest) con ese título'},
    'Allá Cartas al Corazón': {'director': 'Montserrat Larqué',
                               '_por_que': 'mismo título que en FICPA 2026 («Allá, cartas al corazón»); ningún homónimo conocido'},
    'La Gallina Saraviada': {'director': 'Ingrid Paola Bonilla Rodríguez',
                             '_por_que': 'corto colombiano en «Muestra de Cine Colombiano»; el mismo de FICPA y SiembraFest 2026'},
    'Luis Antonio': {'director': 'Juan José Arias Gil',
                     '_por_que': 'corto colombiano en «Muestra de Cine Colombiano»; el mismo de Popayán y FICICA 2026'},
    'Volar': {'director': 'Jeiver Pinto Vargas',
              '_por_que': 'largo colombiano de Jeiver Pinto, el mismo que publicamos en Villa del Cine 2026; '
                          'va en Cinema Luna, aliado del festival'},
    'La Sierra': {'director': 'Carlos Ortiz',
                  '_fuente': 'https://www.instagram.com/p/DervW-Tifu0/',
                  '_por_que': 'la pieza del festival para la función del 24 oct en La Manuela imprime el afiche '
                              '(«Sierra – El álbum mortuorio») y «Dirrctor Carlos Ortiz»'},
}
OBRAS_CREDITOS = {
    'Planeta Fome': {'director': 'Édier William', '_fuente': 'https://www.themoviedb.org/movie/1470780'},
    # dentro de los programas: la lámina da la ciudad, que corrobora
    'Carola': {'director': 'Violeta Barrios Ramírez',
               '_por_que': 'la lámina dice «Carola - Medellín»; es el corto antioqueño de Violeta Barrios que '
                           'publicamos en Girardota y SiembraFest 2026'},
    'Hasta que amanezca': {'director': 'Sebastián Rosas Santamaría',
                           '_por_que': 'la lámina dice «Hasta que amanezca - Bogotá»; es el corto bogotano que '
                                       'publicamos en el BHFF 2026'},
}



# LA PIEZA PROPIA DE CADA ACTIVIDAD (19 oct 2026, Juan: «le da más identidad al
# festival»). El festival publicó un arte por taller y por conversatorio en tres
# carruseles de @guatapefilmfest: DemHnuhINOv (talleres), DenbqwCDTjY y
# DepGT_4oHSu (conversatorios). Se miraron una por una; van al lienzo 2:3 con el
# recorte de siempre (decisión de Juan: A, aunque se pierda texto a los lados).
PIEZAS = {
    'Cine para reflejar territorio': 'cine-para-reflejar-territorio.jpg',        # DemHnuhINOv/1
    'El Reflejo de las Generaciones': 'el-reflejo-de-las-generaciones.jpg',      # DemHnuhINOv/2
    'Taller Memoria y Patrimonio Visual': 'taller-memoria-y-patrimonio-visual.jpg',  # DemHnuhINOv/3
    'Historias que se Juegan': 'historias-que-se-juegan.jpg',                    # DemHnuhINOv/4
    'Reflejos de un Personaje': 'reflejos-de-un-personaje.jpg',                  # DemHnuhINOv/5
    'El Reflejo de un Actor': 'el-reflejo-de-un-actor.jpg',                      # DenbqwCDTjY/2
    'Detrás del Reflejo - El Productor': 'detras-del-reflejo-el-productor.jpg',  # DenbqwCDTjY/3
    'Conversatorio Actores': 'conversatorio-actores.jpg',                        # DenbqwCDTjY/4
    'Conversatorio Historias que se Juegan': 'conversatorio-historias-que-se-juegan.jpg',  # DenbqwCDTjY/5
    'Cine con Legado Social': 'cine-con-legado-social.jpg',                      # DepGT_4oHSu/1
    'Tres Miradas, un Reflejo': 'tres-miradas-un-reflejo.jpg',                   # DepGT_4oHSu/2
    'El Reflejo de los Festivales': 'el-reflejo-de-los-festivales.jpg',          # DepGT_4oHSu/3
    'Sangre de Palermo y su Reflejo': 'sangre-de-palermo-y-su-reflejo.jpg',      # DepGT_4oHSu/4
}

# El horario que imprime la lámina con un «Pm» que no corresponde («9:00 - 12:00
# Pm» es de mañana: lo dice su propio afiche, «9:00 a.m. – 12:00 m.»; «11:00 Pm»
# del día 25 va antes del conversatorio de las 13:30 en la misma lámina).
# La transcripción ya los pasó a 24 h así; acá queda escrito el porqué.

ACCESO = 'Entrada libre'
_ACCESO = {
    'estado': ACCESO,
    'revisado': '2026-10-18',
    'fuentes': ['las 11 láminas del carrusel oficial (instagram.com/p/Def6fhKDSQy/)',
                'los afiches de las masterclass (instagram.com/p/DehGQpgoAvX/)',
                '12 posts de @guatapefilmfest leídos sin sesión el 17 oct'],
    '_por_que': 'Ninguna fuente anuncia boletería; regla de Juan: sin aviso de pago es gratis. '
                'Las dos masterclass piden inscripción por QR («cupos limitados»).',
}


def plano(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def ocr(n):
    r = subprocess.run(['swift', f'{REPO}/pipeline/ocr.swift', f'{LAMINAS}/{n:02d}.jpg'],
                       capture_output=True, text=True)
    if r.returncode:
        sys.exit(f'✗ el OCR de la lámina {n:02d} falló: {r.stderr[:200]}')
    return plano(' '.join(json.loads(r.stdout)['lineas']))


def hora12(h):
    a, b = map(int, h.split(':'))
    a = a - 12 if a > 12 else a
    return {f'{a} {b:02d}', f'{a:02d} {b:02d}'}


def mins(h):
    a, b = h.split(':')
    return int(a) * 60 + int(b)


def limpia(s):
    s = re.sub(r'\s+', ' ', (s or '').replace('|', '.')).strip(' .')
    return re.sub(r'\s*\.\s*', '. ', s).strip() + '.' if s else ''


def main():
    ojos = json.load(io.open(OJOS, encoding='utf-8'))['items']
    texto = {n: ocr(VEP_A_OFICIAL[n]) for n in VEP_A_OFICIAL}
    fallos, funciones, vistos = [], [], set()
    for f in ojos:
        k = (f['dia'], f['hora'], f['encabezado'])
        if k in vistos:
            fallos.append(f'clave repetida en la transcripción: {k}')
        vistos.add(k)
        t = texto[f['lamina']]
        w = set(t.split())
        if not any(h in t for h in hora12(f['hora'])):
            fallos.append(f'{k}: el OCR no encuentra la hora en la lámina oficial {VEP_A_OFICIAL[f["lamina"]]:02d}')
        p, a = PROYECCION.get(k), ACTIVIDAD.get(k)
        if bool(p) == bool(a):
            fallos.append(f'{k}: sin clasificar (ni PROYECCION ni ACTIVIDAD), o en las dos')
            continue
        base = {'dia': f['dia'], 'hora': f['hora'], 'sede': re.sub(r'\s+', ' ', f['lugar']).strip(' .'),
                'acceso': ACCESO, '_src': dict(SRC, lamina=VEP_A_OFICIAL[f['lamina']])}
        if p:
            # el título de una obra (o de las obras de un programa) tiene que estar en su lámina
            for tit in [o['titulo'] for o in p.get('obras', [])] or [p['titulo']]:
                faltan = [x for x in plano(tit).split() if len(x) >= 4 and x not in w]
                if faltan:
                    fallos.append(f'«{tit}»: el OCR no encuentra {faltan} en la lámina oficial')
            reg = {**base, 'titulo': p.get('publicar') or p['titulo'], 'seccion': SECCION[f['encabezado']]}
            if p.get('publicar'):
                reg['_titulo_lamina'] = p['titulo']
            for c in ('premiere', 'pais'):
                if p.get(c):
                    reg[c] = p[c]
            for c, v in CREDITOS.get(reg['titulo'], {}).items():
                reg[c if not c.startswith('_') else '_creditos' + c] = v
            if p.get('obras'):
                reg['obras'] = [{**o, **{c if not c.startswith('_') else '_creditos' + c: v
                                         for c, v in OBRAS_CREDITOS.get(o['titulo'], {}).items()}}
                                for o in p['obras']]
        else:
            faltan = [x for x in plano(f['encabezado']).split() if len(x) >= 4 and x not in w]
            if faltan:
                fallos.append(f'«{f["encabezado"]}»: el OCR no encuentra {faltan} en la lámina oficial')
            reg = {**base, 'titulo': a['titulo'], 'tipo': 'evento', 'event_kind': a['kind'],
                   'seccion': ACTIVIDADES}
            if f.get('fin'):
                reg['duracion_min'] = mins(f['fin']) - mins(f['hora'])
            if a.get('inscripcion'):
                reg['acceso'] = 'Entrada libre con inscripción previa'
            if a.get('recurrente'):
                reg['is_recurring'] = True
            if a.get('afiche') or PIEZAS.get(a['titulo']):
                a = {**a, 'afiche': a.get('afiche') or PIEZAS[a['titulo']]}
                # la pieza propia de la actividad, que el festival mandó por mensaje
                # (19 oct 2026): el afiche OFICIAL, no una tarjeta nuestra
                reg['poster'] = f'/assets/guatape-2026/{a["afiche"]}'
                reg['posterSource'] = 'oficial'
            if f.get('linea'):
                reg['sinopsis'] = limpia(f['linea'])
        funciones.append(reg)
    sin_usar = (set(PROYECCION) | set(ACTIVIDAD)) - vistos
    if sin_usar:
        fallos.append(f'entradas de las tablas que ninguna lámina tiene: {sorted(sin_usar)}')
    if fallos:
        sys.exit('✗ la transcripción, el OCR y las tablas no coinciden:\n  · ' + '\n  · '.join(fallos))

    funciones.sort(key=lambda f: (f['dia'], f['hora'], f['sede'], f['titulo']))
    io.open(OUT, 'w', encoding='utf-8').write(json.dumps({
        '_provenance': provenance(
            'Instagram @guatapefilmfest — el carrusel oficial de programación (11 láminas)',
            que_aporta='la programación entera: día, hora, lugar, sección y actividad',
            url=SRC['url'],
            metodo='transcripción a ojo lámina por lámina, confirmada hora por hora y título por '
                   'título con el OCR de la lámina oficial'),
        '_acceso': _ACCESO,
        'funciones': funciones}, ensure_ascii=False, indent=1) + '\n')
    n_ev = sum(1 for f in funciones if f.get('tipo') == 'evento')
    print(f'✓ {len(funciones)} ({len(funciones) - n_ev} proyecciones + {n_ev} actividades) · '
          f'{len({f["sede"] for f in funciones})} lugares · OCR de acuerdo → '
          f'{os.path.relpath(OUT, REPO)}')


if __name__ == '__main__':
    main()
