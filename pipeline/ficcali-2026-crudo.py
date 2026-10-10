#!/usr/bin/env python3
"""ficcali-2026-crudo.py — programación + catálogo de FICCALI 18 → crudo.

Junta las dos lecturas de ficcali.com:
  · -programacion.json: una tarjeta por función o actividad (día, hora, sede,
    título, país | duración, categoría);
  · -catalogo.json: la ficha de cada obra de la Selección (título ORIGINAL,
    dirección, país, año, duración, sinopsis, sección).

QUÉ MANDA EN QUÉ:
  · cuándo y dónde: la tarjeta;
  · qué obra es y cómo se titula: la ficha (Juan, 7 oct: el TÍTULO ORIGINAL,
    el de la ficha; el de la tarjeta, en español, queda como `titulo_es`);
  · la sección: la de la ficha, con el nombre del menú del sitio; una
    proyección sin ficha lleva la categoría que el festival le pone a su
    tarjeta («Proyecciones», «Cine sin límites»), sin inventarle otra;
  · las actividades (Académico, Conexiones) entran TODAS, con su acceso (Juan,
    7 oct).

LO QUE NO SE INVENTA:
  · las obras de un programa solo cuando la tarjeta nombra una sección o un
    grupo sin ambigüedad («PLANO SONORO: MUESTRA DE VIDEOCLIPS»); «COMPETENCIA
    CORTO NACIONAL – PROG. 1 / PROG. 2» y «Vanguardias – Prog 1 / Prog 2»
    parten una sección en dos sin decir cómo: van sin lista y se preguntan;
  · el acceso de las proyecciones: el festival no lo publica (solo el del
    lanzamiento, «entrada libre y gratuita hasta completar aforo») → DESCONOCIDO;
  · la duración de una actividad sin rango: hueco hasta la siguiente en la misma
    sede, tope 90, 60 si es la última.
"""
import io
import json
import os
import re
import sys
import unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import DESCONOCIDO, provenance  # noqa: E402

# EL GÉNERO va UNO ([genero-unico]): el primero de la ficha que esté en el
# vocabulario de la app (_GENRE_EN de sheets-controller.js); si ninguno, vacío
_SC = io.open(f'{REPO}/src/controller/sheets-controller.js', encoding='utf-8').read()
GENEROS = set(re.findall(r"'([^']+)':", _SC[_SC.index('const _GENRE_EN'):_SC.index('};', _SC.index('const _GENRE_EN'))]))

# EL ACCESO, declarado a nivel de festival: no se publica para las proyecciones
_ACCESO = {
    'estado': DESCONOCIDO,
    'revisado': '2026-10-07',
    'fuentes': ['ficcali.com/programacion-ficcali-2026/ (las 118 tarjetas)',
                'la nota oficial del lanzamiento (ficcali.com, 3 oct)'],
    '_por_que': 'Las tarjetas no dicen cómo se entra; la única afirmación del festival es la del lanzamiento '
                '(«entrada libre y gratuita hasta completar aforo», fuera del 16–25). Las actividades que piden '
                'inscripción o tienen cupo lo dicen en su tarjeta y lo llevan.'}

ST = f'{REPO}/festivals/staging'
PROG = f'{ST}/ficcali-2026-programacion.json'
CAT = f'{ST}/ficcali-2026-catalogo.json'
DESTINO = f'{ST}/ficcali-2026-crudo.json'
URL = 'https://ficcali.com/programacion-ficcali-2026/'
# LOS DÍAS DEL FESTIVAL: «se desarrollará entre el 16 al 25 de octubre» (nota
# oficial del lanzamiento). La programación trae además actividades del 3 al 15
# y una función el 27: quedan fuera, por decisión de Juan (7 oct).
DESDE, HASTA = '2026-10-16', '2026-10-25'


def plano(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


# LA SECCIÓN con el nombre del menú del sitio (la subpágina dice «Cortometraje
# Nacional 2026»; el menú, «Competencia Cortometraje Nacional»). ZOOM va en caja
# de título (regla de caja sostenida): es su categoría de WordPress, «Zoom».
SECCION = {
    'Largometrajes Nacionales 2026': 'Competencia Largometrajes Nacionales',
    'Largometraje Internacional 2026': 'Competencia Largometrajes Internacionales',
    'Cortometraje Nacional 2026': 'Competencia Cortometraje Nacional',
    'Cali ciudad abierta': 'Cali Ciudad Abierta',
    'Vanguardias afro e indígenas': 'Vanguardias Afro e Indígenas',
    'Plano sonoro': 'Plano Sonoro',
    'Cine sin límites': 'Cine Sin Límites',
    'Muestras de Muestras': 'Muestras de Muestras',
    'Muestra Infantil': 'Muestra Infantil',
    'ZOOM': 'Zoom',
    'Foco: Claire Simon': 'Foco Claire Simon',
    '¡Que viva la música!': '¡Que viva la música!',
    '¡Que Viva la Música!': '¡Que viva la música!',   # la subpágina del 10 oct, otra caja
}
# LA SEDE: el nombre de la tarjeta → (sede, sala). Investigada sede por sede
# (7 oct) con dos fuentes por pin; la página de sedes 2025 del festival (Wayback)
# desempató los nombres: «TEATRINO» es el del Teatro Municipal Enrique
# Buenaventura, «CCMI» es Casa Ethel, «Casa Yurtas» y «Yurtas Ulpiano Lloreda»
# son el mismo lugar. Pines y preguntas en -venues-geo.json.
# LA EDICIÓN DEL 8 OCT reescribe cinco sedes: cuatro son las mismas con otro
# nombre; «Idea Lab» es nueva y no tiene dirección en ninguna fuente, así que su
# tarjeta queda FUERA hasta que el festival la confirme (regla: ninguna sede sin pin).
SEDE_SIN_PIN = {'Idea Lab': 'sede nueva (8 oct) sin dirección pública; preguntado al festival'}
SEDES = {
    'CINEMATECA LA TERTULIA': ('Cinemateca La Tertulia', ''),
    'CINEMATECA MUSEO LA TERTULIA': ('Cinemateca La Tertulia', ''),
    'SALA MADAME BLUE': ('Madame Blue', ''),
    'CURADOR CLUB SOCIAL': ('Curador', ''),
    'Bulevar del Río': ('Bulevar del Río', ''),
    'Yurtas Ulpiano Lloreda': ('Casa Yurtas', ''),
    'Casa Yurtas': ('Casa Yurtas', ''),
    'Online': ('En línea', ''),
    'MADAME BLUE': ('Madame Blue', ''),
    'Ciudad Pacífica': ('Ciudad Pacífica', ''),
    'Sendero Comuna 8': ('Sendero del Bosque', ''),
    'Altos de Melendez': ('Alto Meléndez', ''),
    'Biblioteca la Paz': ('Biblioteca Pública La Paz', ''),
    'Biblioteca San Luis 1': ('Biblioteca Pública San Luis I', ''),
    'Teatrino Proyecto Oriente': ('Teatrino Proyecto Oriente', ''),
    'Calimateca': ('Calimateca', ''),
    'ESPECTRA': ('Espectra', ''),
    'Universidad Autónoma de Occidente': ('Universidad Autónoma de Occidente', 'Aulas 4, Torreón 1A'),
    'TEATRO LOS CRISTALES': ('Teatro al Aire Libre Los Cristales', ''),
    'CURADOR': ('Curador', ''),
    'YAWA': ('Yawa', 'Domo'),
    'Plazoleta la Maceta': ('Plazoleta La Maceta', ''),
    'Centro Cultural Brisas de Mayo': ('Centro Cultural Brisas de Mayo', ''),
    'COMFANDI': ('Centro Cultural Comfandi', ''),
    'Tecnocentro': ('Tecnocentro Cultural Somos Pacífico', ''),
    'Teatro La Unión Comuna 16 + Biblioteca la Unión': ('Teatro La Unión', ''),
    'Café Macondo': ('Café Macondo', ''),
    'BLACK GROUND': ('BlackGround', ''),
    'TEATRINO': ('Teatro Municipal Enrique Buenaventura', 'Teatrino'),
    'Cine Quanon': ('CineQuanon', ''),
    'CCMI': ('Casa Ethel', ''),
    'SENA Salomia': ('SENA Salomia', ''),
    'CINE COLOMBIA UNICENTRO': ('Cine Colombia Unicentro', ''),
    'Hotel Obelisco': ('Hotel Obelisco', ''),
    'Boulevard del Rio': ('Bulevar del Río', ''),
}
EN_LINEA = 'En línea'

# la categoría de la tarjeta, cuando la obra no tiene ficha o es una actividad
SECCION_TARJETA = {'Proyecciones': 'Proyecciones', 'Cine sin límites': 'Cine Sin Límites',
                   'Académico': 'Académico', 'Conexiones': 'Conexiones'}

# LA TARJETA en español → el título de la ficha (mirado uno por uno)
ALIAS = {
    'un calendario incompleto': 'An Incomplete Calendar',
    'construi un cohete imaginando tu llegada': 'I Built a Rocket Imagining your Arrival',
    'nuestro cuerpo': 'Notre corps',
    'escribir la vida': 'Écrire la vie: Annie Ernaux racontée par des lycéennes et des lycéens',
    'ellas guardianas de la amazonia': 'Ellas, gardiennes de l’Amazonie',
    'mukira': 'Mu-ki-ra',
    'erase una vez en harlem': 'Once Upon a Time in Harlem',   # la tarjeta traduce; la ficha, en inglés
    'ninxs': 'Niñxs',
    'seis meses en el edificio rosa': 'Seis meses en el edificio rosa con azul',
    'amelie y los secretos de lluvia': 'Amélie y los secretos de la lluvia',
    'monster inc alianza muestra de cine fantastico': 'Monsters, Inc.',
    'kiki': 'Kiki: entregas a domicilio',
    'arco': 'Arco',
    'para vivir': 'Para vivir, el implacable tiempo de Pablo Milanés',
    'album de familia': 'Álbum de familia',
}
# LOS PROGRAMAS cuya tarjeta nombra sin ambigüedad lo que proyecta. Valor: lista
# de títulos de ficha, o ('seccion', nombre) para «todas las de esa sección»,
# o ('rotulo', texto) para las fichas cuyo rótulo lo lleva (We Cam Fest).
PROGRAMA = {
    14032: ('seccion', 'Plano Sonoro'),                 # PLANO SONORO: MUESTRA DE VIDEOCLIPS
    14004: ('seccion_cortos', 'Cali Ciudad Abierta'),   # Cali, ciudad abierta (cortos)
    14495: ['Mi vecino Totoro', 'Boato', 'El viaje', 'La gran hazaña'],   # Cortos infantiles FICCALI / Mi vecino Totoro
    14496: ['Arco', 'Akababuru: Expresión de Asombro'],                     # Largo Arco + Corto Akababuru
    14042: ('rotulo', 'We Cam Fest'),                   # WE CAM FEST 3
}
# LAS TARJETAS QUE JUNTAN DOS OBRAS CON «+» y que NO están en la Selección (sin
# ficha en el catálogo): cada obra con lo que la tarjeta dice de ella; la ficha
# de TMDB se declara en -correcciones.json. Antes se publicaban como UNA obra
# («Rodilla Negra + El Coloso») y ninguna de las dos se buscaba (8 oct).
# UNA ACTIVIDAD EN LA CATEGORÍA «PROYECCIONES»: la tarjeta 14017 es un conversatorio
# (Concip y Telepacífico) y salía como película sin afiche; [proyeccion-que-es-actividad]
# lo cazó el 9 oct. Por id, porque la categoría de la tarjeta miente.
EVENTO_EN_PROYECCIONES = {14017: 'conversatorio'}
# LO QUE LA TARJETA CALLA y otra fuente dice (8 oct): «Guapi: ritmo y balsada» es
# el documental de la Expedición Guapi 1963 del Instituto Popular de Cultura
# (nexus.univalle.edu.co/index.php/nexus/article/view/13321; trasmishuellas.univalle.edu.co),
# sin director acreditado (camarógrafo Juan B. Ocampo)
# …y las proyecciones especiales cuya ficha de TMDB se declaró a mano en
# -correcciones.json: el director y el año, de esa ficha, van aquí porque el
# ensamblador los lee del crudo
DATOS_TARJETA = {14002: {'anio': 1963},
                 14040: {'director': 'Andrey Zvyagintsev', 'anio': 2026},          # Minotauro
                 14025: {'director': 'José Luis Guerín', 'anio': 2001},            # En construcción
                 14001: {'director': 'Eliza Capai', 'anio': 2026},                 # La fabulosa máquina del tiempo
                 13904: {'director': 'Eliza Capai', 'anio': 2026},
                 14038: {'director': 'José Varón', 'anio': 2025},             # El Coloso (sáb 24)
                 # LA TARJETA CALLA DIRECTOR Y AÑO y la misma obra ya está publicada,
                 # completa, en otro festival nuestro; confirmado contra la ficha
                 # TMDB (director, año y duración) el 10 oct 2026
                 14003: {'director': 'Lisandro Alonso', 'anio': 2026},       # La libertad doble (BIFF 12)
                 14018: {'director': 'Augusto Zegarra', 'anio': 2025},       # Runa Simi (AFF 2026)
                 14037: {'director': 'José Luis Guerín', 'anio': 2025},      # Historias del buen Valle (FICCI 65)
                 14049: {'director': 'José Luis Guerín', 'anio': 2025},
                 14041: {'director': 'Javier Calvo, Javier Ambrossi', 'anio': 2026},  # La bola negra (BIFF 12, TIFF)
                 14046: {'director': 'Javier Calvo, Javier Ambrossi', 'anio': 2026}}
OBRAS_TARJETA = {
    14016: [{'titulo': 'Rodilla Negra', 'pais': 'Colombia', 'director': 'Carlos Mayolo', 'anio': 1975, 'duracion_min': 14},
            {'titulo': 'El Coloso', 'pais': 'Colombia', 'director': 'José Varón', 'anio': 2025, 'duracion_min': 70}],
    # dos SERIES documentales de Telepacífico (telepacifico.com/37-novedades): la
    # función proyecta episodios; directores de la fuente, sin ficha en TMDB
    14021: [{'titulo': 'Salseando ando', 'pais': 'Colombia', 'director': 'Álvaro Varón'},
            {'titulo': 'Convergencias', 'pais': 'Colombia', 'director': 'Jorge Navas'}],
    # PROGRAMAS cuya lista no está en ficcali.com sino en la programación del
    # Teatrino publicada por El País Cali (elpais.com.co/cultura/el-teatro-
    # municipal-enrique-buenaventura-se-reactiva-con-programacion-en-su-teatrino-
    # eventos-culturales-para-octubre-0230.html). Trópico interior: muestra de
    # terror/fantástico (curaduría Melissa Saavedra y Alejandra Rocas); Anibia: la
    # muestra itinerante del festival de animación Anibia (Bogotá).
    14019: [{'titulo': '¿Por qué se esconde Drácula?', 'director': 'Camila Loboguerrero', 'anio': 1980, 'duracion_min': 11, 'pais': 'Colombia'},
            {'titulo': 'Sirenas en la niebla', 'director': 'Daniela Narváez', 'anio': 2023, 'duracion_min': 16, 'pais': 'Colombia'},
            {'titulo': 'El ocaso de las criaturas', 'director': 'Jenny David Piedrahita', 'anio': 2023, 'duracion_min': 10, 'pais': 'Colombia'},
            {'titulo': 'Estirpe', 'director': 'Ana María Ferro', 'anio': 2023, 'duracion_min': 16, 'pais': 'Colombia'},
            {'titulo': 'Mi Demonio', 'director': 'Rossana Montoya', 'anio': 2024, 'duracion_min': 17, 'pais': 'Colombia'},
            {'titulo': 'Liebres', 'director': 'Laura Carvajal', 'anio': 2024, 'duracion_min': 13, 'pais': 'Colombia'},
            {'titulo': 'Somnolítico', 'director': 'Abril Natalia Velázquez', 'anio': 2026, 'duracion_min': 13, 'pais': 'Colombia'}],
    14043: [{'titulo': t, 'pais': 'Colombia'} for t in ('Fabricia', 'Corte Eléctrico', 'Una porción por envase', 'Quimera',
                                                       'Tapir Memories', 'Caída libre', 'Pájaro Cubo', 'Susurros del mar')],
}
# LOS PROGRAMAS SIN LISTA: la tarjeta parte una sección sin decir cómo
SIN_LISTA = {13995: 'Competencia Cortometraje Nacional', 13999: 'Competencia Cortometraje Nacional',
             14033: 'Vanguardias Afro e Indígenas', 14034: 'Vanguardias Afro e Indígenas'}
# LA CAJA Y EL NOMBRE de las tarjetas que la programación imprime en mayúscula
# sostenida o repetidas (las seis «LANZAMIENTO PUBLICACIONES en alianza con
# CaliLee»: cada una lleva el título de su libro; el distintivo de la tarjeta ya
# dice «lanzamiento de libro»). Propuesta para Juan (7 oct). Por id de tarjeta.
TITULO = {
    14518: 'Encuentro local estudiantes de cine 2026: Bailar con el caos',
    14519: 'Encuentro local estudiantes de cine 2026: Bailar con el caos',
    14521: 'Desarmar la mirada. Taller de crítica para pensar el cine',
    14525: 'Desarmar la mirada. Taller de crítica para pensar el cine',
    14594: 'Desarmar la mirada. Taller de crítica para pensar el cine',
    13995: 'Competencia corto nacional – Prog. 1',
    13999: 'Competencia corto nacional – Prog. 2',
    14591: 'Taller de doblaje en el cine',
    14592: 'Master class de SAPCINE',
    14032: 'Plano sonoro: muestra de videoclips',
    14042: 'We Cam Fest 3',
    14614: 'DJ y coctel',
    13931: 'Domo Live Camoflux: Incendio Igapó',
    14006: 'Cineconcierto: Metrópolis',
    14605: 'Agujero',
    14606: 'El trabajo de la polilla en la llama',
    14607: 'Viñetaira. Historia universal de las autoras del cómic',
    14608: 'Creatividad y escritura',
    14624: 'El juego de la vida',
    14625: 'Una mirada general del proceso del Circuito Cineclubes Cali, CCINEC, 2026',
    14019: 'Trópico interior: Todos los colores de la oscuridad',   # la tarjeta no deja espacio tras «:»
}
# EL LUGAR EXACTO que dos tarjetas dan en su última línea («Lugar: …»)
SALA_TARJETA = {14624: 'Auditorio Celsia', 14625: 'Carpa de la Red de Bibliotecas Públicas de Cali'}

# EL TIPO DE ACTIVIDAD por la palabra del título (vocabulario que la app conoce)
KIND = [('master class', 'masterclass'), ('máster class', 'masterclass'), ('taller', 'taller'),
        ('panel', 'charla'), ('charla', 'charla'), ('lanzamiento', 'lanzamiento de libro'),
        ('encuentro', 'encuentro'), ('parche', 'encuentro'), ('foro', 'encuentro'),
        ('seminario', 'encuentro'), ('city tour', 'experiencia'), ('dj', 'fiesta'),
        ('cineconcierto', 'cineconcierto'), ('domo', 'experiencia'), ('muestra vr', 'experiencia')]
# proyecciones que son una EXPERIENCIA (domo inmersivo, VR, concierto)
EXPERIENCIA = {14841, 13931, 14447, 14448, 14919, 14006}


def acceso(x):
    t = ' '.join(filter(None, [x['titulo'], x.get('meta_impresa') or '']))
    if x['id'] == 13880:          # el lanzamiento (nota oficial del festival)
        return 'Entrada libre y gratuita hasta completar aforo'
    if re.search(r'inscripci[oó]n|cupo', t, re.I):
        return 'Inscripción previa' + (f' · {m.group()}' if (m := re.search(r'Cupo:\s*\d+(\s*personas)?', t)) else '')
    return DESCONOCIDO


def genero_uno(g):
    for x in re.split(r'\s*[,/]\s*|\s+y\s+', g or ''):
        x = x.strip()
        for v in (x, x[:1].upper() + x[1:].lower()):
            if v in GENEROS:
                return v
    return None


def recta(t):
    return (t or '').replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')


def _obra(o):
    return {k: v for k, v in {'titulo': recta(o['titulo']), 'director': o.get('director'), 'pais': o.get('pais'),
                                  'anio': o.get('anio'), 'duracion_min': o.get('duracion_min'),
                                  'genero': genero_uno(o.get('genero')), 'sinopsis': o.get('sinopsis')}.items() if v}


def main():
    T = json.load(io.open(PROG, encoding='utf-8'))['tarjetas']
    O = json.load(io.open(CAT, encoding='utf-8'))['obras']
    idx = {plano(o['titulo']): o for o in O}
    fallos, funciones, fuera = [], [], []


    # LA SECCIÓN DECLARADA PRIMERO (10 oct 2026): la web sumó una subpágina
    # «Primer plano» que también enlaza obras de Zoom y de Muestras de Muestras.
    # Una obra listada en varias va en la primera que el plan ya declara; una
    # sección nueva entra solo cuando Juan la declara en el plan.
    _plan_secs = set(json.load(io.open(f'{REPO}/pipeline/ficcali-2026.plan.json', encoding='utf-8'))['festival']['secciones'])

    def seccion_de(o):
        cands = [SECCION.get(x, x) for x in o['secciones']]
        return next((c for c in cands if c in _plan_secs), cands[0])

    for x in T:
        if not (DESDE <= x['dia'] <= HASTA):
            fuera.append(f'{x["dia"]} {x["titulo"][:60]}: fuera del 16–25 oficial')
            continue
        if not x.get('hora'):
            fuera.append(f'{x["dia"]} {x["titulo"]}: sin hora en la tarjeta')
            continue
        if x['sede'] in SEDE_SIN_PIN:
            fuera.append(f'tarjeta {x["id"]} · {x["dia"]} {x["titulo"][:60]}: {SEDE_SIN_PIN[x["sede"]]}')
            continue
        partes = [p.strip() for p in x['titulo'].split('|')]
        nombre, detalle = partes[0], ' | '.join(partes[1:]) or None
        if x['sede'] not in SEDES:
            fallos.append(f'tarjeta {x["id"]}: sede sin entrada en la tabla: {x["sede"]!r}')
            continue
        sede, sala = SEDES[x['sede']]
        r = {'dia': x['dia'], 'hora': x['hora'], 'sede': sede, 'sala': sala, 'sede_cruda': x['sede'],
             'acceso': acceso(x),
             '_src': {'url': URL, 'date': '2026-10-06', 'tarjeta': x['id']}}
        if sede == EN_LINEA:
            r['online'] = True
        if x.get('hasta'):
            h1, h2 = x['hora'], x['hasta']
            r['duracion_min'] = (int(h2[:2]) * 60 + int(h2[3:])) - (int(h1[:2]) * 60 + int(h1[3:]))
        # el Q&A va como MARCA: guardado como `invitados`, el ensamblador lo pega
        # a la sinopsis solo en las funciones que lo traen y la misma obra queda
        # con dos sinopsis ([programa-mismo-titulo])
        if x.get('qa'):
            r['has_qa'], r['qa_type'] = True, 'team'
        k = plano(nombre)
        o = idx.get(k) or idx.get(plano(ALIAS.get(k, '')))
        cat = x['categoria']
        es_proy = (cat in ('Proyecciones', 'Cine sin límites') or x.get('duracion_min')) and x['id'] not in EVENTO_EN_PROYECCIONES
        if x['id'] in PROGRAMA:
            p = PROGRAMA[x['id']]
            if isinstance(p, list):
                obras = [idx[plano(t)] for t in p]
            elif p[0] == 'seccion':
                obras = [o_ for o_ in O if any(SECCION.get(s, s) == p[1] for s in o_['secciones'])]
            elif p[0] == 'seccion_cortos':
                obras = [o_ for o_ in O if any(SECCION.get(s, s) == p[1] for s in o_['secciones'])
                         and (o_.get('duracion_min') or 0) < 60]
            else:
                obras = [o_ for o_ in O if p[1] in (o_.get('rotulo') or '')]
            r.update({'titulo': nombre, 'seccion': seccion_de(obras[0]) if isinstance(p, list) else
                      (p[1] if p[0] != 'rotulo' else 'Muestras de Muestras'),
                      'obras': [_obra(o_) for o_ in obras]})
            r.setdefault('duracion_min', sum(o_.get('duracion_min') or 0 for o_ in obras) or None)
        elif x['id'] in OBRAS_TARJETA:
            r.update({'titulo': nombre, 'seccion': SECCION_TARJETA.get(cat, 'Proyecciones'),
                      'obras': [dict(o_) for o_ in OBRAS_TARJETA[x['id']]]})
            r.setdefault('duracion_min', x.get('duracion_min'))
        elif x['id'] in SIN_LISTA:
            # sin lista no hay programa (un `is_cortos` vacío rompe el contrato):
            # va como función de la categoría de su tarjeta; preguntado al festival
            r.update({'titulo': nombre, 'seccion': SECCION_TARJETA.get(cat, 'Proyecciones')})
        elif o and es_proy:
            r.update(_obra(o))
            # lo que la ficha calla y la tarjeta declara (DATOS_TARJETA) se suma;
            # nunca pisa un dato de la ficha
            for k_, v_ in (DATOS_TARJETA.get(x['id']) or {}).items():
                if not r.get(k_):
                    r[k_] = v_
            r['seccion'] = seccion_de(o)
            if plano(o['titulo']) != k:
                r['titulo_es'] = nombre
            r['duracion_obra'] = o.get('duracion_min') or x.get('duracion_min')
            r['duracion_min'] = max(filter(None, [o.get('duracion_min'), x.get('duracion_min')]), default=None)
        elif es_proy and x['id'] not in EXPERIENCIA:
            r.update({'titulo': nombre, 'seccion': SECCION_TARJETA.get(cat, 'Proyecciones'),
                      **(DATOS_TARJETA.get(x['id']) or {}),
                      'pais': x.get('pais') if x.get('pais') not in ('Cali, Colombia', 'Cali') else None,
                      'duracion_min': x.get('duracion_min')})
        else:
            kind = EVENTO_EN_PROYECCIONES.get(x['id']) or next((v for w, v in KIND if w in nombre.lower()), 'evento')
            r.update({'titulo': nombre, 'tipo': 'evento', 'event_kind': kind,
                      'seccion': SECCION_TARJETA.get(cat, 'Académico' if cat not in SECCION_TARJETA else cat)})
            if detalle:
                r['sinopsis'] = detalle.rstrip('.') + '.'
            # la meta de la tarjeta, si es de ESTA actividad: una línea que se
            # repite en varias («Cali. Panel en alianza con la Academia…») es del
            # lugar o del ciclo, no de la actividad
            if x.get('meta_impresa') and x['meta_impresa'] not in ('Cali, Colombia', 'Cali, Colombia.') \
                    and sum(1 for y in T if y.get('meta_impresa') == x['meta_impresa']) == 1:
                r['invitados'] = x['meta_impresa']
        if x['id'] in TITULO:
            r['titulo'] = TITULO[x['id']]
        if x['id'] in SALA_TARJETA:
            r['sala'] = SALA_TARJETA[x['id']]
        r['titulo'] = recta(r['titulo'])
        funciones.append({k_: v for k_, v in r.items() if v not in (None, '')})

    # LA MISMA ACTIVIDAD EN VARIAS FECHAS lleva UN texto ([programa-mismo-titulo]):
    # el de su primera tarjeta; la línea de aula y cupo de cada una ya está en
    # su acceso
    primero = {}
    for f in funciones:
        if f.get('tipo') != 'evento':
            continue
        p0 = primero.setdefault(f['titulo'], f)
        if p0 is not f:
            f.pop('invitados', None)
            if p0.get('sinopsis'):
                f['sinopsis'] = p0['sinopsis']
            p0.pop('invitados', None)

    # DURACIÓN DEDUCIDA de lo que no la trae
    def mins(h):
        return int(h[:2]) * 60 + int(h[3:])
    for f in funciones:
        if f.get('duracion_min'):
            continue
        sig = sorted(mins(g['hora']) for g in funciones
                     if g['dia'] == f['dia'] and g['sede'] == f['sede'] and g.get('sala') == f.get('sala')
                     and g['hora'] > f['hora'])
        f['duracion_min'] = min(sig[0] - mins(f['hora']), 90) if sig else 60
        f['_duracion_de'] = 'el hueco hasta la siguiente en la misma sede (tope 90, 60 si es la última)'

    if len(funciones) + len(fuera) != len(T):
        fallos.append(f'{len(T)} tarjetas y {len(funciones)} funciones + {len(fuera)} fuera')
    if fallos:
        sys.exit('✗ el crudo no cuadra:\n  · ' + '\n  · '.join(fallos))
    io.open(DESTINO, 'w', encoding='utf-8').write(json.dumps({
        '_provenance': provenance('ficcali.com — Programación 2026 (WP 14870) + fichas de la Selección 2026',
                                  url=URL, metodo='tarjeta por función; obra por la ficha del catálogo'),
        '_acceso': _ACCESO, '_fuera': fuera, 'funciones': funciones}, ensure_ascii=False, indent=1))
    n_ev = sum(1 for f in funciones if f.get('tipo') == 'evento')
    print(f'✓ {len(funciones)} funciones ({n_ev} actividades, {sum(1 for f in funciones if f.get("obras"))} programas) '
          f'· {len(fuera)} fuera → {os.path.relpath(DESTINO, REPO)}')
    for z in fuera:
        print('   fuera ·', z)


if __name__ == '__main__':
    main()
