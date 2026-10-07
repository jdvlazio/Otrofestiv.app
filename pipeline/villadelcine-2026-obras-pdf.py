#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""villadelcine-2026-obras-pdf.py — las fichas del PDF, obra por obra.

QUÉ SACA. Las páginas 12–50 del programa traen una ficha por obra, agrupadas
bajo la cabecera de su programa («NUEVAS MIRADAS TRÁNSITO»), que es exactamente
el nombre con que la retícula anuncia el bloque. De cada ficha salen el título,
la dirección, la duración, el país, el género y la SINOPSIS EN ESPAÑOL —que la
web no tiene: la web las publica en inglés—.

CÓMO SE CORTA UNA FICHA. La única línea fiable es la de dirección: «Dir. X» o
«DIR. X». A partir de ella se lee hacia arriba (título y, antes, el formato:
WIP, VERTICAL, VIDEO MUSICAL, CORTOMETRAJE NACIONAL…) y hacia abajo (la línea
de metadatos y la sinopsis). Anclar en el título no funciona: unos van en
mayúsculas y otros no, y varias páginas traen dos y hasta tres obras seguidas.

LO QUE NO SE INVENTA. Una ficha sin línea de metadatos se queda sin duración y
sin país —«QUAZAR» es una de ellas—, y esos huecos los llena después el cruce
con la web o con TMDB, nunca este paso. Una obra sin «Dir.» no se publica como
obra: se anota en `sin_direccion` para mirarla.

Lee   festivals/staging/villadelcine-2026-parrilla.json  (bloque `fichas`)
Esc.  festivals/staging/villadelcine-2026-obras-pdf.json
"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import provenance

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
PAR = f'{ST}/villadelcine-2026-parrilla.json'
OUT = f'{ST}/villadelcine-2026-obras-pdf.json'

# EL CRÉDITO NO SIEMPRE SE ESCRIBE «Dir.». En la página 18 el festival acredita
# «Productora Lorena López», y cortando las fichas solo por la línea de
# dirección la obra entera —«Pros and Cons of Daydreaming», que compite en
# Mejor Cortometraje con Celular— se caía del programa sin hacer ruido: el
# informe de «páginas sin dirección» no sonó porque esa página tiene otras dos
# fichas que sí la traen, y ese informe cuenta PÁGINAS, no fichas.
#
# El censo que la encontró va por METRAJE: toda ficha imprime su duración,
# lleve o no la palabra «Dir.». 83 líneas de metraje en las páginas 12–50, y
# una sola sin crédito de dirección. Se captura el ROL además del nombre para
# no llamar director a quien el impreso no llamó así.
RE_DIR = re.compile(r'^\s*(Dir|DIR|Dirección|DIRECCIÓN|Productora|Productor)'
                    r'\.?\s*[:.]?\s*(.+)$')
# «0:17:40 | México | Ficción» o «120 minutos | Ficción / Drama»
RE_META = re.compile(r'^\s*(?:(\d{1,2}):(\d{2}):(\d{2})|(\d{1,3})\s*minutos?)\s*\|?\s*(.*)$')
RE_SOLO_DUR = re.compile(r'^\s*(\d{1,2}):(\d{2}):(\d{2})\s*$')
# El FORMATO que el festival imprime encima del título. Verbatim, tal como lo
# escribe: es su vocabulario y no se normaliza.
FORMATOS = {
    'WIP', 'VERTICAL', 'CELULAR', 'IA', 'VR', 'VIDEO MUSICAL', 'ESCOLAR',
    'INFANTIL', 'YOUNGFILM', 'APASIONADO NACIONAL', 'CORTOMETRAJE NACIONAL',
    'CORTOMETRAJE INTERNACIONAL', 'ÓPERA PRIMA NACIONAL', 'OPERA PRIMA NACIONAL',
    'ÓPERA PRIMA INTERNACIONAL', 'PODEROSAS', 'VOCES', 'PLANETA', 'RAÍCES',
    'KOREBAJU', 'BOYACÁ EN LOS CAMPOS', 'INT', 'DISCAPACIDADES',
    'WORK IN PROGRESS', 'RUMBO A LOS MACONDO',
}


def es_formato(l):
    """La línea de formato encima del título. El PDF del 6 oct los escribe
    largos («CORTOMETRAJE APASIONADO INTERNACIONAL», «CORTOMETRAJE CON
    CELULAR», «CORTOMETRAJE REALIDAD VIRTUAL»): todos empiezan igual."""
    u = l.strip().upper()
    return u in FORMATOS or (u.startswith('CORTOMETRAJE') and u == l.strip())


def cabecera(ls, i):
    """Las líneas de título encima del «Dir.» de la línea i, de arriba abajo.

    LA PLANTILLA DEL 6 OCT para obras extranjeras: título original, debajo su
    traducción entre paréntesis y, si el original no va en alfabeto latino,
    una línea más («落⼦無悔 (LÀOZǏ WÚ HUǏ)»). Tomando solo la línea de
    encima del crédito se publicaba «(El Joven Sofiane)» como título, y el
    formato y el título de la ficha siguiente se pegaban al final de la
    sinopsis anterior."""
    out, k = [], i - 1
    while k >= 0 and not es_formato(ls[k]) and not RE_DIR.match(ls[k]):
        l = ls[k].strip()
        latino = re.sub(r'[^A-Za-zÁÉÍÓÚÑáéíóúñÜüÀ-ÿ]', '', l)
        if out and not (l.startswith('(') or not re.search(r'[a-zá-úñ]', latino)):
            break
        out.insert(0, l)
        k -= 1
        if len(out) == 3:
            break
    return out
# EL PAÍS ES UNA LISTA, NO UNA HEURÍSTICA. El comodín «varias palabras
# separadas por coma o barra» se tragaba los géneros: «Ficción / Drama /
# Comedia / Fantasia» entraba como país y la app lo iba a pintar con un globo
# terráqueo en vez de una bandera. Un país o está en la lista o no es país.
PAISES = ['colombia', 'méxico', 'mexico', 'brasil', 'brasi', 'argentina', 'chile',
          'perú', 'peru', 'ecuador', 'venezuela', 'uruguay', 'paraguay', 'bolivia',
          'guatemala', 'cuba', 'panamá', 'costa rica', 'españa', 'france', 'francia',
          'italia', 'italy', 'alemania', 'portugal', 'reino unido', 'inglaterra',
          'bélgica', 'belgium', 'holanda', 'países bajos', 'suiza', 'austria',
          'suecia', 'noruega', 'dinamarca', 'polonia', 'rusia', 'ucrania', 'grecia',
          'turquía', 'usbekistán', 'uzbekistán', 'uzbekistan', 'india', 'china',
          'japón', 'taiwán', 'taiwan', 'corea', 'irán', 'israel', 'nigeria',
          'sudáfrica', 'australia', 'canadá', 'usa', 'estados unidos', 'spain',
          'finlandia']
# Como el festival las escribe → como se escriben. Solo ortografía: no se
# cambia el país, se corrige la letra.
ERRATA_PAIS = {'brasi': 'Brasil', 'usbekistán': 'Uzbekistán', 'mexico': 'México',
               'peru': 'Perú', 'taiwan': 'Taiwán', 'uzbekistan': 'Uzbekistán',
               'france': 'Francia', 'italy': 'Italia', 'belgium': 'Bélgica',
               'spain': 'España'}


def es_pais(t):
    """Una celda de metadatos es el país si TODAS sus partes lo son: «Brasil,
    India, Italia, España» sí; «Ficción y Drama» no."""
    partes = [x.strip().lower() for x in re.split(r'[,/]| y ', t or '') if x.strip()]
    return bool(partes) and all(x in PAISES for x in partes)


def limpia_pais(t):
    partes = [x.strip() for x in re.split(r'([,/])', t or '') if x.strip()]
    return ''.join(ERRATA_PAIS.get(x.lower(), x) if x not in ',/' else x + ' '
                   for x in partes).strip()


# LAS CUATRO PÁGINAS SIN «Dir.». No son obras en competencia: son un tributo,
# dos reconocimientos y dos talleres infantiles, y por eso el festival no les
# imprime dirección. Se declaran con lo que dice su página —no se fuerzan por
# el parser ni se dejan caer— y salen marcadas como actividad.
IRREGULARES = [
    # PDF del 6 oct (14–17 oct): las páginas se corrieron y aparecieron dos más.
    # «Aquileo Venganza» tiene ahora su ficha CON dirección (p17, la exhibición)
    # y aparte el TRIBUTO (p15), que es una actividad.
    # el título va con «TRIBUTO»: con «AQUILEO VENGANZA» a secas colisionaba con
    # la ficha de la película (p17) y el crudo le daba a la obra el texto del tributo
    {'pagina': 15, 'titulo': 'TRIBUTO A AQUILEO VENGANZA', 'linea': 'AQUILEO VENGANZA',
     'credito': 'Ciro Durán y Joyce Ventura',
     'rol': 'tributo', 'nota': 'TRIBUTO al legado de Ciro Durán y a la labor de Joyce '
            'Ventura; con la exposición fotográfica «Memorias de Aquileo Venganza»'},
    {'pagina': 16, 'titulo': 'PATRIMONIO FÍLMICO COLOMBIANO', 'credito': '',
     'rol': 'reconocimiento', 'nota': 'POR SUS 40 AÑOS'},
    {'pagina': 16, 'titulo': 'HÉROES DE LA MONTAÑA', 'credito': '',
     'rol': 'reconocimiento', 'nota': 'EL TERRITORIO QUE SOMOS'},
    {'pagina': 16, 'titulo': 'MABEL VELOSA', 'credito': '',
     'rol': 'reconocimiento', 'nota': 'CAMINOS DEL TIEMPO'},
    {'pagina': 55, 'titulo': 'CIANOTIPIA', 'credito': 'Isabella Bobadilla Monsalve',
     'rol': 'tallerista',
     'nota': 'Taller de experimentación y fotografía analógica'},
    {'pagina': 55, 'titulo': 'FARMEANDO EL TUNJO: CREACIÓN CINEMATOGRÁFICA CON '
                             'INTELIGENCIA ARTIFICIAL', 'linea': 'FARMEANDO EL TUNJO',
     'credito': 'Jimena Guerrero, Vanessa Vega y PiPo Aranguren',
     'rol': 'talleristas', 'nota': 'taller de creación cinematográfica con inteligencia artificial'},
    # EL FÓSIL MÁGICO YA TIENE FICHA (6 oct). En septiembre estaba solo en la
    # retícula y Juan lo dejó fuera por eso; ahora la p55 trae crédito, formato
    # y sinopsis. Es una OBRA (no lleva `es_actividad`): un cortometraje de
    # estudiantes con Q&A. El crédito se escribe como en la RETÍCULA
    # («Sáchica, Boyacá»): la ficha dice «Sáchicha», y su propia sinopsis
    # escribe «Sáchica».
    {'pagina': 55, 'titulo': 'EL FÓSIL MÁGICO', 'linea': 'COMIENZOS | EL FÓSIL MÁGICO: Cortometraje',
     'credito': 'Estudiantes IE Nueva Generación (Sáchica, Boyacá)', 'rol': 'realizadores',
     'nota': 'COMIENZOS · EXHIBICIÓN + Q&A; la ficha escribe «Sáchicha»',
     'obra': {'seccion': 'Programación Infantil', 'programa': 'COMIENZOS', 'formato': 'Cortometraje'}},
]


def tramo(ls, irr, pagina):
    """El párrafo de UNA ficha irregular: desde su título hasta la siguiente.

    En las páginas con dos o tres (p16, p55) tomar todas las líneas largas
    de la página le pegaba a Cianotipia la sinopsis de Farmeando."""
    propios = [x.get('linea', x['titulo']).upper() for x in IRREGULARES if x['pagina'] == pagina]
    cab = irr.get('linea', irr['titulo']).upper()
    i = next((k for k, l in enumerate(ls) if l.upper() == cab), None)
    if i is None:
        sys.exit(f'✗ p{pagina}: no aparece el título «{cab}» de la ficha irregular')
    out = []
    for l in ls[i + 1:]:
        if l.upper() in propios:
            break
        if not out:
            if len(l) > 60:
                out.append(l)
        elif re.search(r'[a-zá-ú]', l) and '|' not in l:
            out.append(l)
        else:
            break
    if not out:
        sys.exit(f'✗ p{pagina} «{cab}»: la ficha irregular no tiene párrafo')
    return ' '.join(out)
# LA MUESTRA QUE NO TIENE «Dir.» PERO SÍ METRAJE (PDF del 6 oct, p18): «NUEVA
# OLA ROLA», del Festival de Cine Eureka, «MUESTRA + Q&A», 53 min. Su línea de
# metadatos se lee igual que la de una obra.
SIN_DIRECCION = {'NUEVA OLA ROLA': ('Festival de Cine Eureka', 'muestra')}


# Palabras que NO se capitalizan dentro de un título en español, y siglas que
# SÍ van enteras en mayúscula. Ver `a_titulo`.
# LA CAJA DE LOS TÍTULOS QUE LA WEB NO TRAE, escrita a mano. Se respeta la
# ortografía del festival; lo único que cambia es la mayúscula sostenida de la
# plantilla del PDF.
CAJA = {
    'UN POETA': 'Un poeta',
    'LLUEVE SOBRE BABEL': 'Llueve sobre Babel',
    'AQUILEO VENGANZA': 'Aquileo Venganza',
    'FUNDACIÓN PATRIMONIO FILMICO': 'Fundación Patrimonio Fílmico',
    'MABEL VELOSA': 'Mabel Velosa',
    'MI TESORO': 'Mi tesoro',
    'LA ÚLTIMA HISTORIA': 'La última historia',
    'LE JEUNE SOFIANE': 'Le jeune Sofiane',
    'CIANOTIPIA': 'Cianotipia',
    'BEHIND THE DOOR': 'Behind the Door',
    'CON LA MANO ARRIBA': 'Con la mano arriba',
    'AMOR A PRIMERA VISTA': 'Amor a primera vista',
    'SABOR A MI (ACÚSTICO / BOLERO JAZZ)': 'Sabor a mí (acústico / bolero jazz)',
    'MOMENTOS EN MOVIMIENTO. PRIMEROS PASOS DEL BALLET EN COLOMBIA.':
        'Momentos en movimiento. Primeros pasos del ballet en Colombia',
    'KOREBAJU PAI REKOCHO': 'Korebaju Pai Rekocho',
    'CUADRILEROS ORGULLO Y LEGADO': 'Cuadrileros, orgullo y legado',
    'THE GUANENTÁ SYMPHONY': 'The Guanentá Symphony',
    'FARMEANDO EL TUNJO: CREACIÓN CINEMATOGRÁFICA CON INTELIGENCIA ARTIFICIAL':
        'Farmeando el Tunjo: creación cinematográfica con inteligencia artificial',
}

# UN TÍTULO PEGADO A SU CATEGORÍA. La plantilla del PDF imprime la categoría
# del premio en una línea encima del título («ESCOLAR», «YOUNGFILM»). En la
# página 45 esa línea y la del título salen a la misma altura y pdftotext las
# entrega juntas: «INTFINAL ACT». No se de-pega con una regla —ninguna sabe
# dónde acaba la categoría y empieza el nombre, y hay títulos que empiezan por
# «INT»—, así que va declarado, con la web del festival como testigo: la ficha
# de la obra en villadelcine.com se llama «Final Act».
PEGADOS = {'INTFINAL ACT': ('Final Act', 'la categoría INT pegada al título, p45')}

MINUS = {'a', 'al', 'ante', 'con', 'contra', 'de', 'del', 'desde', 'e', 'el', 'en',
         'entre', 'hacia', 'hasta', 'la', 'las', 'lo', 'los', 'más', 'ni', 'o', 'para',
         'por', 'que', 'se', 'según', 'si', 'sin', 'sobre', 'su', 'sus', 'tras', 'un',
         'una', 'unos', 'unas', 'y', 'the', 'of', 'and', 'in', 'on', 'to', 'for', 'a'}
SIGLAS = {'IA', 'VR', 'WIP', 'USA', 'UBPD', 'AI', 'DASC', 'ENACC', 'TV', 'II', 'III'}


def a_titulo(t, natural=None):
    """«AMOR A PRIMERA VISTA» → «Amor a primera vista».

    El PDF imprime TODOS los títulos en mayúscula sostenida. Eso es una
    decisión tipográfica de la plantilla, no el nombre de la obra, y publicarlo
    así se lee a gritos (además de romper el gate de la app).

    PRIMERO, LA WEB DEL PROPIO FESTIVAL: publica los mismos títulos en caja
    natural, así que si la obra está allí se usa SU escritura y no la nuestra.
    Es la diferencia entre respetar cómo lo escribe el festival y adivinarlo:
    ninguna regla automática sabe que en «Sierra: el álbum mortuorio» la sierra
    va en mayúscula y el álbum no.

    SOLO SI NO ESTÁ EN LA WEB se busca en CAJA, que es una lista escrita a
    mano. NO se aplica una regla automática: probé con caja de oración y
    «LLUEVE SOBRE BABEL» quedó «Llueve sobre babel». Ninguna regla sabe que
    Babel es un nombre propio y el álbum no, así que las pocas que la web no
    trae se escriben una por una, mirando la obra.
    """
    # CAJA va PRIMERO: «BEHIND THE DOOR» y «AMOR A PRIMERA VISTA» están en
    # mayúscula sostenida también en la web, así que preferir la web sin más
    # las dejaba gritando. La lista escrita a mano es una decisión tomada
    # mirando la obra y gana sobre las dos fuentes.
    if t.strip() in PEGADOS:
        return PEGADOS[t.strip()][0]
    if t.strip() in CAJA:
        return CAJA[t.strip()]
    return natural or t


def _sinacento(x):
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFD', x or '')
                   if unicodedata.category(c) != 'Mn').lower()


def parte_cabecera(cab):
    """«NUEVAS MIRADAS TRÁNSITO» → (sección, programa). Las secciones son las
    once que aprobó Juan; lo que sobra del nombre es el programa."""
    SECC = ['NARRATIVAS DIVERGENTES', 'PROGRAMACIÓN INFANTIL', 'LENGUAJES EMERGENTES',
            'NUEVAS MIRADAS', 'RUMBO A LOS MACONDO', 'EXHIBICIÓN ESPECIAL',
            'EVENTOS ESPECIALES', 'TERRITORIOS', 'INDUSTRIA', 'RUTA ACADÉMICA',
            'COMUNICACIONES']
    c = re.sub(r'\s+', ' ', cab).strip()
    # EL PDF DEL 6 OCT pega a la cabecera el día y la franja de la función
    # («16 TARDE LENGUAJES EMERGENTES VIERNES DESTELLOS», «15 y 16 SEÑALES
    # JUEVES, VIERNES»): se quitan, que el programa es el nombre de la retícula
    c = re.sub(r'\b(\d{1,2}|y|MAÑANA|TARDE|NOCHE|LUNES|MARTES|MIÉRCOLES|JUEVES|VIERNES|'
               r'SÁBADO|DOMINGO)\b,?', ' ', c)
    c = re.sub(r'\s+', ' ', c).strip(' ,')
    for s in SECC:
        if c.upper().startswith(s):
            return s.title().replace('Rumbo A Los Macondo', 'Rumbo a los Macondo'), \
                   c[len(s):].strip()
    return '', c


def main():
    d = json.load(open(PAR, encoding='utf-8'))
    # los mismos títulos, como los escribe la web del festival
    natural = {}
    web_p = f'{ST}/villadelcine-2026-obras-web.json'
    if os.path.exists(web_p):
        for o in json.load(open(web_p, encoding='utf-8'))['obras']:
            natural[re.sub(r'[^a-z0-9]+', '', _sinacento(o['titulo']))] = o['titulo']
            # desde el 6 oct la web escribe «FAR (LEJOS)», «Final Act (Acto
            # Final)»: el original, sin la traducción, es la otra llave
            _orig = re.sub(r'\s*\([^)]*\)?\s*$', '', o['titulo']).strip()
            if _orig and _orig != o['titulo']:
                natural.setdefault(re.sub(r'[^a-z0-9]+', '', _sinacento(_orig)), _orig)
    obras, sin_dir = [], []

    SEM = {'MIÉRCOLES': '14', 'JUEVES': '15', 'VIERNES': '16', 'SÁBADO': '17'}
    for f in d['fichas']:
        seccion, programa = parte_cabecera(f['cabecera'])
        # el DÍA que la cabecera de la ficha imprime («15 y 16 … JUEVES, VIERNES»)
        dia_ficha = ','.join(sorted({SEM[w] for w in SEM if w in f['cabecera'].upper()}))
        ls = [x.strip() for x in f['texto'].split('\n') if x.strip()]
        idx = [i for i, l in enumerate(ls) if RE_DIR.match(l)]
        cabs = [cabecera(ls, i) for i in idx]
        for n, i in enumerate(idx):
            _m = RE_DIR.match(ls[i])
            rol, director = _m.group(1), _m.group(2).strip()
            # LA LÍNEA DE CRÉDITO CON LOS METADATOS PEGADOS. La plantilla los
            # pone en renglones distintos, salvo en «SIERRA: EL ÁLBUM
            # MORTUORIO», donde el PDF imprime «Dir. Carlos Ortiz Alarcón
            # 1:30:00 | Colombia» de corrido. Quedándose con todo lo que sigue
            # a «Dir.» se publicaba un director llamado «Carlos Ortiz Alarcón
            # 1:30:00 | Colombia» y se perdían LOS DOS datos: los 90 minutos y
            # el país. Se corta por el metraje, que es lo único que no puede
            # ser parte de un nombre.
            _meta = re.search(r'\s+(\d{1,2}:\d{2}:\d{2}.*)$', director)
            cola = ''
            if _meta:
                director, cola = director[:_meta.start()].strip(), _meta.group(1)
            cab = cabs[n]
            traduccion = next((c[1:-1].strip() for c in cab
                               if c.startswith('(') and c.endswith(')')), '')
            # el título es la primera línea en alfabeto latino; la otra, si la
            # hay, se guarda aparte (en el texto del PDF el orden varía)
            _lat = lambda c: len(re.findall(r'[A-Za-zÀ-ÿ]', c)) > len(c) / 2
            noparen = [c for c in cab if not (c.startswith('(') and c.endswith(')'))]
            # la MÁS CERCANA al crédito: encima puede quedar un rótulo
            principal = next((c for c in reversed(noparen) if _lat(c)), noparen[-1] if noparen else '')
            otras = [c for c in noparen if c != principal and not _lat(c)]
            crudo_t = re.sub(r'\s*—$', '', principal)
            titulo = a_titulo(crudo_t, natural.get(
                re.sub(r'[^a-z0-9]+', '', _sinacento(crudo_t))))
            formato = ''
            arriba = i - len(cab) - 1
            if arriba >= 0 and es_formato(ls[arriba]):
                formato = ls[arriba].strip()
            # hacia abajo: metadatos (si los hay) y sinopsis hasta la cabecera
            # de la ficha siguiente (y su formato, si lo trae)
            fin = len(ls)
            if n + 1 < len(idx):
                fin = idx[n + 1] - len(cabs[n + 1])
                if fin - 1 > i and es_formato(ls[fin - 1]):
                    fin -= 1
            cuerpo = ls[i + 1:fin]
            # LA PLANTILLA DEL 6 OCT: entre «DIR.» y los metadatos van el FORMATO
            # («ÓPERA PRIMA NACIONAL») y «Selección Oficial en Competencia»
            while cuerpo and (cuerpo[0].strip().upper() in FORMATOS or
                              cuerpo[0].strip().upper() in ('CORTOMETRAJE',) or
                              cuerpo[0].startswith('Selección Oficial')):
                if not formato and cuerpo[0].strip().upper() in FORMATOS:
                    formato = cuerpo[0].strip()
                cuerpo = cuerpo[1:]
            # lo que venía pegado al crédito se lee como si fuera su renglón
            if cola:
                cuerpo = [cola] + cuerpo
            dur_min, pais, genero = None, '', ''
            if cuerpo:
                m = RE_META.match(cuerpo[0])
                solo = RE_SOLO_DUR.match(cuerpo[0])
                if m and (m.group(1) or m.group(4)):
                    if m.group(1):
                        dur_min = int(m.group(1)) * 60 + int(m.group(2)) + \
                                  (1 if int(m.group(3)) >= 30 else 0)
                    else:
                        dur_min = int(m.group(4))
                    resto = [x.strip() for x in (m.group(5) or '').split('|') if x.strip()]
                    for r in resto:
                        if not pais and es_pais(r):
                            pais = limpia_pais(r)
                        elif not genero:
                            genero = r
                    cuerpo = cuerpo[1:]
                elif solo:
                    dur_min = int(solo.group(1)) * 60 + int(solo.group(2)) + \
                              (1 if int(solo.group(3)) >= 30 else 0)
                    cuerpo = cuerpo[1:]
                # LOS WORK IN PROGRESS DEL 6 OCT: «Colombia | Ciencia Ficción», sin
                # metraje (el PDF de septiembre ponía 0:05:00). Sin este caso la
                # línea se iba al comienzo de la sinopsis de las cinco de GÉNESIS.
                elif ' | ' in cuerpo[0] and es_pais(cuerpo[0].split('|')[0].strip()):
                    partes = [x.strip() for x in cuerpo[0].split('|') if x.strip()]
                    pais, genero = limpia_pais(partes[0]), ' | '.join(partes[1:])
                    cuerpo = cuerpo[1:]
            obras.append({
                'titulo': titulo, 'director': director,
                **({'_titulo_traducido': traduccion} if traduccion else {}),
                **({'_titulo_otro_alfabeto': otras[0]} if otras else {}),
                # QUIÉN ES ESA PERSONA, con la palabra del impreso. El PDF la
                # acredita como «Productora» y la ficha de la obra en la propia
                # web del festival la lista bajo «Director»: son dos fuentes del
                # mismo festival diciendo cosas distintas, así que se publica lo
                # que dice la página de la obra y queda anotado de dónde sale la
                # diferencia, en vez de escoger en silencio.
                **({'rol_credito': rol.lower(),
                    '_nota': f'el PDF la acredita «{rol} {director}»; la ficha de '
                             'la obra en villadelcine.com la lista como Director'}
                   if rol.lower().startswith('productor') else {}),
                'seccion': seccion, 'programa': programa, 'dia_ficha': dia_ficha,
                **({'formato': formato} if formato else {}),
                'duracion_min': dur_min, 'pais': pais, 'genero': genero,
                # el rótulo de la ficha SIGUIENTE («WORK IN PROGRESS», en
                # GÉNESIS) va en mayúscula entre dos fichas y se quedaba pegado
                'sinopsis': re.sub(r'\s+WORK IN PROGRESS$', '', ' '.join(cuerpo).strip()),
                'pagina': f['pagina'],
                '_src': {'url': 'https://villadelcine.com/ (PROGRAMACIÓN 2026.pdf) '
                                f'p{f["pagina"]}', 'date': '2026-10-06'},
            })
        for irr in [x for x in IRREGULARES if x['pagina'] == f['pagina']]:
            obras.append({
                'titulo': a_titulo(irr['titulo']), 'director': irr['credito'],
                'seccion': seccion, 'programa': programa,
                'rol_credito': irr['rol'], '_nota': irr['nota'],
                **({'es_actividad': True} if 'obra' not in irr else irr['obra']),
                'duracion_min': None, 'pais': '', 'genero': '',
                'sinopsis': tramo(ls, irr, f['pagina']),
                'pagina': f['pagina'],
                '_src': {'url': 'https://villadelcine.com/ (PROGRAMACIÓN 2026.pdf) '
                                f'p{f["pagina"]}', 'date': '2026-10-06'},
            })
        for k, (cred, rol) in SIN_DIRECCION.items():
            if k in ls:
                j0 = ls.index(k)
                meta = next((x for x in ls[j0:j0 + 4] if RE_META.match(x) and RE_META.match(x).group(1)), '')
                m = RE_META.match(meta)
                dur = (int(m.group(1)) * 60 + int(m.group(2)) + (1 if int(m.group(3)) >= 30 else 0)) if m else None
                resto = [x.strip() for x in (m.group(5) if m else '').split('|') if x.strip()]
                fin2 = next((n2 for n2 in range(ls.index(meta) + 1, len(ls)) if ls[n2].isupper()), len(ls)) if meta else j0 + 1
                obras.append({'titulo': a_titulo(k), 'director': cred, 'rol_credito': rol,
                              '_nota': 'sin «Dir.»: la presenta el ' + cred, 'seccion': seccion, 'programa': programa,
                              'duracion_min': dur, 'pais': limpia_pais(resto[0]) if resto and es_pais(resto[0]) else '',
                              'genero': resto[1] if len(resto) > 1 else '',
                              'sinopsis': ' '.join(ls[ls.index(meta) + 1:fin2]).strip() if meta else '',
                              'pagina': f['pagina'],
                              '_src': {'url': 'https://villadelcine.com/ (PROGRAMACIÓN 2026.pdf) '
                                              f'p{f["pagina"]}', 'date': '2026-10-06'}})
        if not idx and not any(x['pagina'] == f['pagina'] for x in IRREGULARES):
            sin_dir.append({'pagina': f['pagina'], 'cabecera': f['cabecera'],
                            'texto': f['texto'][:180]})

    json.dump({'_provenance': provenance(
        'PROGRAMACIÓN «Caminos del tiempo» 2026, páginas 12–50: una ficha por obra',
        que_aporta='título, dirección, duración, país, género y la SINOPSIS EN '
                   'ESPAÑOL, además del programa al que pertenece cada obra',
        url='https://villadelcine.com/wp-content/uploads/2026/10/'
            'Programacion-caminos-del-tiempo-2026.pdf',
        metodo='cada ficha se corta por su línea de dirección, que es la única '
               'constante: el título va en mayúsculas o no según la página, y hay '
               'páginas con dos y tres obras'),
        'obras': obras, 'sin_direccion': sin_dir},
        open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    # EL CENSO QUE FALTABA. `sin_direccion` cuenta PÁGINAS sin ninguna línea de
    # crédito, y por eso se calló con la página 18: tenía otras dos fichas que
    # sí la traían. Toda ficha imprime su metraje, con crédito o sin él, así
    # que se cuentan las líneas de metraje y se comparan con lo extraído.
    metrajes = sum(1 for f in d['fichas']
                   for l in f['texto'].split('\n') if RE_SOLO_DUR.match(l.strip())
                   or (RE_META.match(l.strip()) and RE_META.match(l.strip()).group(1)))
    cubiertas = sum(1 for o in obras if o['duracion_min'])
    if metrajes > cubiertas:
        print(f'✗ {metrajes} líneas de metraje en las fichas y solo {cubiertas} '
              f'obras con duración: hay una ficha que no se está cortando')
        sys.exit(1)

    con_dur = sum(1 for o in obras if o['duracion_min'])
    con_sin = sum(1 for o in obras if o['sinopsis'])
    progs = {(o['seccion'], o['programa']) for o in obras}
    print(f'{len(obras)} obras · {con_dur} con duración · {con_sin} con sinopsis · '
          f'{len(progs)} programas → {os.path.basename(OUT)}')
    for s, p in sorted(progs):
        n = sum(1 for o in obras if (o['seccion'], o['programa']) == (s, p))
        print(f'   {n:>3}  {s or "—":24} {p}')
    if sin_dir:
        print(f'⚠ {len(sin_dir)} página(s) de ficha sin ninguna línea «Dir.»: '
              + ', '.join(f'p{x["pagina"]} ({x["cabecera"][:28]})' for x in sin_dir))


if __name__ == '__main__':
    main()
