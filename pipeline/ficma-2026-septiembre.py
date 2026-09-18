# -*- coding: utf-8 -*-
"""Reconstruye festivals/ficma-2026.json con la programación de SEPTIEMBRE.

FICMA 17 se aplazó por el sismo del 10 ago y volvió del 19 al 26 de SEPTIEMBRE.

DE DÓNDE SALE LA PARRILLA, Y POR QUÉ CAMBIÓ DE FUENTE. Hasta el 17 de
septiembre el festival no había publicado parrilla: se armaba post a post desde
Instagram, y así se montaron 15 funciones. El 18, a un día de abrir, puso en su
home un PDF con la programación completa —78 páginas, una por función—. Ese PDF
es ahora la fuente de la parrilla: `ficma-2026-parse.py` lo convierte en crudo.
Lo que se leyó de los posts NO se tira: sirve para dos cosas, la ficha de las
obras que el PDF no describe (el PDF no trae sinopsis) y el CRUCE — toda función
que anunciaron por Instagram tiene que estar en el PDF, y si no está, se dice.

QUÉ SE CONSERVA. El CATÁLOGO de agosto entero: póster, sinopsis, lbSlug,
género, país, año, duración, bandera. La obra es la misma; lo que cambió es
cuándo y dónde se ve.

LA FRANJA ACADÉMICA VA APARTE. El PDF no la incluye —son otras once actividades,
talleres y charlas, que el festival publica en /talleresficma17/— y por eso
sigue entrando por su propio sidecar.

Lee   festivals/staging/ficma-2026-crudo-septiembre.json  (la parrilla, del PDF)
      festivals/staging/ficma-2026-franja-web.json    (la franja académica, 11)
      festivals/staging/ficma-2026-reprogramado.json  (lo anunciado post a post)
      festivals/staging/ficma-2026-fichas-tmdb.json   (ficha de las obras nuevas)
      festivals/staging/ficma-2026-posters.json       (el afiche del festival)
      festivals/staging/ficma-2026-catalogo-agosto.json  (las 86 fichas, congeladas)
      festivals/staging/ficma-2026-venues-geo.json    (+ las sedes nuevas, abajo)
Esc.  festivals/staging/ficma-2026-build.json         (lo publica publicar.py)
"""
import glob, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
CIUDAD = 'Manizales'
DIAS = [f'2026-09-{d}' for d in range(19, 27)]

# Nombre de sección TAL CUAL lo escribe el festival en su programa (regla
# permanente). Lo nuestro es solo el emoji, el inglés y el arquetipo —que no es
# etiqueta libre: es la clave del color y hay un gate que lo exige—.
#
# Los once primeros son los mismos que ya se publicaron en agosto, con su mismo
# emoji: es la taxonomía del propio festival —«los 8 universos temáticos» más
# los estrenos—. «POP ART» cambió de forma (en agosto lo escribía «Arte Pop») y
# se escribe como lo escribe ahora.
SECCIONES = {
    'ESTRENOS NACIONALES':     ('🎬 Estrenos Nacionales', 'National Premieres', 'Competencia', 1),
    'ESTRENOS INTERNACIONALES': ('🌍 Estrenos Internacionales', 'International Premieres', 'Muestra / País', 2),
    'ESTRENOS LOCALES':        ('🏔️ Estrenos Locales', 'Local Premieres', 'Competencia', 3),
    'ARTE':                    ('🎨 Arte', 'Art', 'Perspectivas / Miradas', 4),
    'POP ART':                 ('🥫 Pop Art', 'Pop Art', 'Perspectivas / Miradas', 5),
    'CÓMIC':                   ('💥 Cómic', 'Comics', 'Perspectivas / Miradas', 6),
    'MÚSICA':                  ('🎵 Música', 'Music', 'Perspectivas / Miradas', 7),
    'ARQUITECTURA':            ('🏗️ Arquitectura', 'Architecture', 'Perspectivas / Miradas', 8),
    'ANTIGÜEDADES':            ('🕰️ Antigüedades', 'Antiques', 'Retrospectiva / Tributo', 9),
    'NUMISMÁTICA':             ('🪙 Numismática', 'Numismatics', 'Retrospectiva / Tributo', 10),
    'MEDIO AMBIENTE':          ('🌱 Medio Ambiente', 'Environment', 'Perspectivas / Miradas', 11),
    'FUNCIONES ESPECIALES':    ('✨ Funciones Especiales', 'Special Screenings', 'Especiales / Eventos', 12),
    'FIESTA DE CLAUSURA':      ('🎉 Fiesta de Clausura', 'Closing Party', 'Especiales / Eventos', 13),
    'TALLERES':                ('🛠️ Talleres', 'Workshops', 'Charlas / Industria', 14),
    'CHARLAS':                 ('💬 Charlas', 'Talks', 'Charlas / Industria', 15),
}

# EL RÓTULO DE SECCIÓN TRAE ADORNOS, Y NO TODOS SON SECCIÓN. El festival escribe
# «ESTRENOS NACIONALES EN ALIANZA CON CINEMA LUNA» o «ESTRENOS NACIONALES -
# ESTRENO LOCAL FUNCION DE CLAUSURA». Si cada combinación fuera una sección
# habría 22 para 70 funciones y la pantalla dejaría de servir para filtrar.
# La SECCIÓN es lo que queda al quitar estos adornos; el adorno se guarda, no se
# tira: la alianza va a `_nota` y el rótulo de inaugural/clausura a `premiere`,
# que es el campo del contrato para «texto libre del festival».
ALIANZA = re.compile(r'\s+EN\s+(?:ALIANZA|ASOCIACI[OÓ]N)\s+CON\s+(.+)$')
HITO = re.compile(r'\s*[-–]?\s*(FUNCI[OÓ]N\s+INAUGURAL|FUNCI[OÓ]N\s+DE\s+CLAUSURA)\s*')
MATIZ = re.compile(r'\s*[-–]\s*(CORTO\s+LOCAL|ESTRENO\s+LOCAL|MUSICALIZADA\s+EN\s+VIVO)\s*')


def parte_seccion(rotulo):
    """«ESTRENOS NACIONALES - ESTRENO LOCAL FUNCION DE CLAUSURA» →
    ('ESTRENOS NACIONALES', {'premiere': 'Función de clausura', ...})."""
    s, extra = rotulo.strip(), {}
    m = ALIANZA.search(s)
    if m:
        extra['alianza'] = m.group(1).strip().title()
        s = s[:m.start()]
    m = HITO.search(s)
    if m:
        extra['premiere'] = m.group(1).capitalize().replace('Funcion', 'Función')
        s = (s[:m.start()] + ' ' + s[m.end():]).strip()
    for m in MATIZ.finditer(s):
        extra.setdefault('matices', []).append(m.group(1).capitalize())
    s = MATIZ.sub(' ', s).strip(' -–')
    # «FUNCIÓN ESPECIAL» y «FUNCIONES ESPECIALES» son la misma sección escrita en
    # singular y en plural según le cupo al diseñador en la lámina.
    if s.startswith('FUNCI') and 'ESPECIAL' in s:
        s = 'FUNCIONES ESPECIALES'
    return re.sub(r'\s{2,}', ' ', s), extra


# Sede del programa → (clave canónica de venues, sala). La tabla es EXPLÍCITA,
# nunca heurística sobre el guion: es la lección más cara de FICDEH. Lo que no
# está acá entra tal cual, que es lo correcto para un parque o un barrio.
SEDES = {
    # El mismo edificio, escrito de tres formas en el mismo PDF.
    'Casa de la Cultura Palogrande': ('Casa de la Cultura de Palogrande', ''),
    'Calle externa - Casa de la Cultura Palogrande':
        ('Casa de la Cultura de Palogrande', 'Calle externa'),
    'Secretaría de Cultura de Palogrande': ('Casa de la Cultura de Palogrande', ''),
    'Biblioteca Pública Satélite Palogrande': ('Casa de la Cultura de Palogrande', ''),
    'Secretaria de Cultura de Palogrande': ('Casa de la Cultura de Palogrande', ''),
    # El Centro Cultural del Banco de la República (Cra. 23 #23-06) y el Centro
    # Cultural Universitario Rogelio Salmona (Cra. 28D, dentro de la Universidad
    # de Caldas) son dos edificios distintos, a 3 km. Los dos son de Salmona y
    # por eso se confunden; verificado en Google Maps el 18 sep.
    'Auditorio Rogelio Salmona': ('Centro Cultural Rogelio Salmona', 'Auditorio'),
    'Oculo Rogelio Salmona': ('Centro Cultural Rogelio Salmona', 'Óculo'),
    'Rogelio Salmona': ('Centro Cultural Rogelio Salmona', ''),
    'Banco de la República': ('Centro Cultural del Banco de la República', ''),
    # La Cámara de Comercio tiene UN auditorio, el Carlos E. Pinzón. Dos láminas
    # lo nombran y una no; son la misma sala y se unifican —dos sedes con el
    # mismo `short` y distinta sala serían dos sitios (docs/SCHEMA.md)—.
    'Auditorio Carlos E. Pinzón - Cámara de Comercio de Manizales por Caldas':
        ('Cámara de Comercio de Manizales por Caldas', 'Auditorio Carlos E. Pinzón'),
    'Cámara de Comercio de Manizales por Caldas':
        ('Cámara de Comercio de Manizales por Caldas', 'Auditorio Carlos E. Pinzón'),
    'Auditorio Olga del Socorro Serna de Quintero - Fundación Batuta Caldas':
        ('Fundación Batuta Caldas', 'Auditorio Olga del Socorro Serna de Quintero'),
    'Sala Roberto Vélez Correa - Universidad de Caldas':
        ('Universidad de Caldas', 'Sala Roberto Vélez Correa'),
    'Auditorio Roberto Vélez Correa - Universidad de Caldas':
        ('Universidad de Caldas', 'Auditorio Roberto Vélez Correa'),
    'Cine al Cable - Campus El Cable UNAL, aula 007':
        ('Universidad Nacional · El Cable', 'Aula 007'),
    # EL ALIADO NO ES LA SEDE. «Confa - Cinema Luna» y «Fama - Cinespiral» traen
    # detrás del guion a quien co-presenta, no un salón: el propio rótulo de
    # sección dice «EN ALIANZA CON CINEMA LUNA». El lugar al que se va es Confa
    # y Fama.
    'Confa - Cinema Luna': ('Confa', ''),
    'Fama - Cinespiral': ('Fama', ''),
    'Parque Ernesto Gutierrez': ('Parque Ernesto Gutiérrez', ''),
    'Universidad Autónoma - Aula Torreón F-101':
        ('Universidad Autónoma', 'Aula Torreón F-101'),
    'Hall Secretaría de la Mujer y Equidad de Género':
        ('Secretaría de la Mujer y Equidad de Género', 'Hall'),
    'Secretaría de la Mujer y Equidad de Género':
        ('Secretaría de la Mujer y Equidad de Género', 'Hall'),
    'Teatro Los Fundadores – Sala Olimpia': ('Teatro los Fundadores', 'Sala Olimpia'),
    'Auditorio Olimpia - Teatro Los Fundadores': ('Teatro los Fundadores', 'Sala Olimpia'),
    'Auditorio Olimpia – Teatro Los Fundadores': ('Teatro los Fundadores', 'Sala Olimpia'),
    'Sala Olimpia – Teatro Los Fundadores': ('Teatro los Fundadores', 'Sala Olimpia'),
    'Confa de la 50 – Auditorio Hernando Aristizábal Botero':
        ('Confa', 'Auditorio Hernando Aristizábal Botero'),
    'Zoom': ('Zoom', ''),
    'Charla transmitida por zoom': ('Zoom', ''),
}

# La sede que no es un lugar: «Zoom» no tiene coordenadas y no debe tenerlas.
# `city` va vacío A PROPÓSITO —una transmisión no está en Manizales— y el filtro
# por ciudad sigue plano porque las demás sedes sí la declaran.
SIN_LUGAR = {'Zoom': {'city': '', '_nota': 'transmisión por Zoom; el festival no '
                                           'publica más lugar que la plataforma'}}

# Sedes que el sidecar de agosto no tenía, ubicadas en Google Maps — cada una
# con ficha propia (/place/), no con el centro de un resultado de búsqueda. Para
# sedes de ciudades colombianas Maps manda sobre Nominatim, y la DIRECCIÓN vale
# más que el pin: es lo que se copia a un mapa para llegar.
GEO_NUEVAS = {
    'Centro Cultural del Banco de la República': {
        'lat': 5.0669375, 'lng': -75.5168125, '_prec': 'maps',
        'address': 'Cra. 23 #23-06',
        '_nota': 'ficha propia en Google Maps; dentro está la Biblioteca Luis Ángel Arango'},
    'Centro Cultural Rogelio Salmona': {
        'lat': 5.0546875, 'lng': -75.4915625, '_prec': 'maps',
        'address': 'Cra. 28D entre Cl. 66 y 67',
        '_nota': 'ficha «Centro Cultural Universitario Rogelio Salmona», dentro de la Universidad de Caldas. NO es el Centro Cultural del Banco de la República, que también es obra de Salmona y está a 3 km.'},
    'Casa de la Cultura de Palogrande': {
        'lat': 5.0575195, 'lng': -75.484585, '_prec': 'maps',
        'address': 'Cl 64A #20a-31',
        '_nota': 'ficha «Casa de la cultura - Palogrande». El festival la nombra también «Secretaría de Cultura de Palogrande» y «Biblioteca Pública Satélite Palogrande»: es el mismo edificio —la alcaldía lo inauguró como «Casa de la Cultura y Biblioteca Pública Satélite de Palogrande»— y se unifican.'},
    'Confa': {
        'lat': 5.0625092, 'lng': -75.4989887, '_prec': 'maps',
        '_nota': 'ficha «Confa», Cra 25 Calle 50 esquina. El auditorio Hernando Aristizábal Botero está dentro.'},
    'Fundación Batuta Caldas': {
        'lat': 5.0508125, 'lng': -75.4828125, '_prec': 'maps',
        'address': 'Cra. 22 #70b-31',
        '_nota': 'ficha «Fundación Batuta Caldas - Sede Principal». El auditorio Olga del Socorro Serna de Quintero está dentro.'},
    'Cámara de Comercio de Manizales por Caldas': {
        'lat': 5.0670625, 'lng': -75.5144375, '_prec': 'maps',
        'address': 'Cra. 23 #26-60'},
    'Fama': {
        'lat': 5.0483125, 'lng': -75.4831875, '_prec': 'maps',
        'address': 'Av. Santander #72-118, piso 2',
        '_nota': 'ficha «FAMA», barrio Milán. El festival lo escribe también «Fama - Cinespiral»: Cinespiral es quien co-presenta, no el lugar.'},
    # Las de exteriores y barrios las ubica Nominatim, que para un parque o un
    # monumento es tan bueno como Maps —y para un barrio entero, el punto es
    # aproximado por definición—.
    'Centro Colombo Americano': {
        'lat': 5.058704, 'lng': -75.489655, '_prec': 'nominatim',
        'address': 'Calle 62, La Estrella'},
    'Bajo Tablazo': {'lat': 5.029143, 'lng': -75.53819, '_prec': 'nominatim',
                     '_nota': 'vereda del corredor agroturístico; el punto es el del sector'},
    'Monumento a los Colonizadores': {
        'lat': 5.076985, 'lng': -75.52781, '_prec': 'nominatim',
        'address': 'Avenida 12 de Octubre, Chipre'},
    'Parque de la Mujer': {'lat': 5.065194, 'lng': -75.499274, '_prec': 'nominatim'},
    'San José': {'lat': 5.072105, 'lng': -75.514901, '_prec': 'nominatim',
                 '_nota': 'el barrio, no una dirección: es cine al aire libre'},
    'Barrio La Estrella': {'lat': 5.0773125, 'lng': -75.4873125, '_prec': 'manual',
                           '_nota': 'la misma coordenada que usó la edición de agosto'},
    # SIN COORDENADA, y dicho: para el Seminario Redentorista Maps da la
    # dirección pero no una ficha con punto, y los dos últimos son canchas de
    # barrio que ningún servicio ubica. La DIRECCIÓN sirve más que un pin
    # inventado a 300 m.
    'Auditorio Redentoristas': {
        'address': 'Cra. 19 #61, Colegio Seminario Redentorista',
        '_nota': 'sin coordenada verificada: Maps tiene la ficha del colegio pero sin punto propio para el auditorio'},
}

# Conversatorio o presencia del director. El PDF lo trae impreso —«PRESENCIA DEL
# DIRECTOR» en la esquina— y el parser lo saca como has_qa; esto solo añade los
# que anunciaron los posts y el PDF no marca.
CON_QA = {'Soñé su nombre', 'Ayuno y cenizas', 'Que el cielo nos perdone',
          'El hogar fue sepultado en esa tierra que nunca pudimos encontrar',
          'Apuntes sobre anomalías y fantasmas', 'Habitante'}
SIN_QA_EN = {('El Juego de la Vida', '2026-09-22')}

DURACION_POR_DEFECTO = {'taller': 180, 'charla': 90}

# LAS CINCO PÁGINAS DE MAQUETA CENTRADA NO SON TODAS LO MISMO. Dos son cine
# —muestras de cortos, que se ven sentado y a una hora— y tres no: un concierto,
# una noche de vinilos y la fiesta de clausura. Se declara una por una porque la
# maqueta dice «esto no es una ficha de película», no dice qué es.
#
# `info` marca lo que NO se planifica: a una fiesta se entra y se sale, y el
# planificador no debe reservarle un bloque (docs/SCHEMA.md). El concierto sí
# tiene hora de inicio y se planifica.
#
# Las dos muestras de cortos no traen duración en el programa —son compilados y
# el festival no dice de cuánto—. La duración es OBLIGATORIA en un festival
# activo porque alimenta el plan, y el contrato admite estimarla; se estiman en
# 90 min, que es lo que dura una muestra de cortos, y queda dicho que es
# estimación nuestra y no dato del festival.
ACTIVIDADES = {
    'Cortos Colombia de película': {
        'tipo': 'pelicula', 'duracion_min': 90,
        '_nota': 'Duración estimada: el programa no la publica'},
    'Muestra de Cortometrajes: Realizadores locales y Eje Cafetero': {
        'tipo': 'pelicula', 'duracion_min': 90,
        '_nota': 'Duración estimada: el programa no la publica'},
    'Concierto Sinfónico': {'tipo': 'evento', 'event_kind': 'experiencia',
                            'duracion_min': 90},
    'Noche de Vinilos': {'tipo': 'evento', 'event_kind': 'experiencia', 'info': True},
    'Sonora Vol. 4': {'tipo': 'evento', 'event_kind': 'experiencia', 'info': True},
}
norm = lib.norm


def franja(path):
    """El sidecar de la franja académica → funciones del formato de este build."""
    d = json.load(open(path, encoding='utf-8'))
    src = d['_provenance']
    out = []
    for a in d['actividades']:
        gente = a.get('tallerista') or a.get('invitados') or ''
        if a.get('modera'):
            gente = f"{gente}, modera {a['modera']}".strip(', ')
        f = {'titulo': a['titulo'], 'director': gente,
             'dia': a['dia'], 'hora': a['hora'], 'sede': a['sede_cruda'], 'sala': '',
             'tipo': a['tipo'],
             'seccion': 'TALLERES' if a['tipo'] == 'taller' else 'CHARLAS',
             'duracion_min': a.get('duracion_min') or DURACION_POR_DEFECTO[a['tipo']],
             'sinopsis': a.get('sinopsis', ''), '_cupos': a.get('cupos'),
             '_src': {'url': src['fuente'].split(' ')[0], 'date': src['capturado']}}
        for c in ('requires_registration', 'registration_url', 'is_free'):
            if a.get(c):
                f[c] = a[c]
        out.append(f)
    return out


def parrilla(path):
    """El crudo del PDF → funciones del formato de este build."""
    d = json.load(open(path, encoding='utf-8'))
    src = d.get('_provenance') or {}
    out = []
    for f in d['funciones']:
        sec, extra = parte_seccion(f['seccion'])
        g = {'titulo': f['titulo'], 'director': f.get('director', ''),
             'dia': f['dia'], 'hora': f['hora'],
             'sede': f['sede'], 'sala': f.get('sala', ''),
             'ciclo': f.get('ciclo', ''), 'seccion': sec,
             'pais': f.get('pais', ''), 'anio': f.get('anio'),
             'duracion_min': f.get('duracion_min'),
             'has_qa': f.get('has_qa', False), 'costo': f.get('costo', ''),
             '_seccion_cruda': f['seccion'], '_pagina': f['pagina'],
             '_src': {'url': 'https://laficma.com/ (PROGRAMACIÓN FICMA 17.pdf)',
                      'date': src.get('capturado', '2026-09-18')}}
        # Las cinco páginas de maqueta centrada no son obra: son actividad —un
        # concierto, una noche de vinilos, dos muestras, la fiesta de clausura—.
        if f.get('maqueta') == 'centrada':
            decl = ACTIVIDADES.get(f['titulo'])
            if not decl:
                sys.exit(f"actividad de maqueta centrada sin declarar: «{f['titulo']}» "
                         f"— decí en ACTIVIDADES si es cine o es evento")
            g.update({k: v for k, v in decl.items() if k != '_nota'})
            if decl.get('_nota'):
                g['_nota'] = ' · '.join(x for x in (g.get('_nota'), decl['_nota']) if x)
        g.update({k: v for k, v in extra.items() if k in ('premiere',)})
        notas = []
        if extra.get('alianza'):
            notas.append(f"En alianza con {extra['alianza']}")
        notas += extra.get('matices', [])
        if notas:
            g['_nota'] = ' · '.join(notas)
        out.append(g)
    return out


def main():
    fun = parrilla(f'{ST}/ficma-2026-crudo-septiembre.json')
    fun += franja(f'{ST}/ficma-2026-franja-web.json')
    # La foto CONGELADA, no el JSON publicado: publicar encoge ese archivo y
    # leerlo aquí haría que el segundo regenerado saliera sin catálogo.
    cat = json.load(open(f'{ST}/ficma-2026-catalogo-agosto.json', encoding='utf-8'))['obras']
    geo = json.load(open(f'{ST}/ficma-2026-venues-geo.json', encoding='utf-8'))
    extra_ficha = json.load(open(f'{ST}/ficma-2026-fichas-tmdb.json',
                                encoding='utf-8'))['fichas']
    for t, f in json.load(open(f'{ST}/ficma-2026-posters.json',
                               encoding='utf-8'))['fichas'].items():
        extra_ficha.setdefault(t, {}).update(f)
    # Lo anunciado post a post: hoy ya no es la parrilla, pero es la única
    # fuente con SINOPSIS de las obras que agosto no tenía.
    posts = json.load(open(f'{ST}/ficma-2026-reprogramado.json', encoding='utf-8'))

    ficha, ajenas = {}, {}
    for t, o in cat.items():
        ficha.setdefault(norm(t), o)
    for otro in sorted(glob.glob(f'{REPO}/festivals/*.json')):
        if otro.endswith('ficma-2026.json'):
            continue
        try:
            d = json.load(open(otro, encoding='utf-8'))
        except Exception:
            continue
        for x in (d.get('films') or []):
            for o in [x] + list(x.get('film_list') or []):
                if o and o.get('title') and o.get('director'):
                    ajenas.setdefault(norm(o['title']), (os.path.basename(otro), o))

    def apellidos(d):
        return {w for w in norm(d).replace(',', ' ').split() if len(w) > 3}

    def heredar(titulo, director):
        k = norm(titulo)
        if k in ficha:
            return ficha[k], 'ficma-2026 (agosto)'
        if k in ajenas:
            fn, o = ajenas[k]
            if apellidos(director) & apellidos(o.get('director')):
                return o, fn
        return None, ''

    # Lo que solo publicaron los posts: sinopsis, año, país, duración y rating.
    del_post = {}
    for p in posts['funciones']:
        e = {k: p[k] for k in ('sinopsis', 'sinopsis_en', 'anio', 'pais',
                               'duracion_min', 'rating') if p.get(k)}
        if e:
            del_post.setdefault(norm(p['titulo']), e)

    films, venues, sin_ficha, avisos = [], {}, [], []
    for fn in fun:
        if not fn['sede']:
            # Una actividad sin lugar no se puede planear, y una sede inventada
            # es peor. No entra, y queda dicho.
            avisos.append(f"«{fn['titulo']}» ({fn['dia'][-2:]}·{fn['hora']}) "
                          f"SIN SEDE declarada: no se publica")
            continue
        es_evento = fn.get('tipo') in ('taller', 'charla', 'evento')
        sec = SECCIONES.get(fn['seccion'])
        if not sec:
            sys.exit(f"sección sin mapear: «{fn['seccion']}» "
                     f"({fn['titulo']}) — añadila a SECCIONES, no la dejes caer")
        clave_sede, sala = lib.sede_sala(fn['sede'], SEDES)
        sala = fn.get('sala') or sala
        k = f'{clave_sede} - {CIUDAD}'
        if k not in venues:
            # GEO_NUEVAS pisa al sidecar de agosto: es lo verificado en Maps
            # hoy, y hay entradas viejas que existen con la coordenada en nulo
            # —«San José», «Cancha la Isla»—. Sin esta precedencia, una entrada
            # vacía gana por el solo hecho de existir.
            g = {**(geo.get(clave_sede) or {}), **(GEO_NUEVAS.get(clave_sede) or {})}
            venues[k] = {'short': clave_sede, 'lat': g.get('lat'), 'lng': g.get('lng'),
                         'city': CIUDAD, 'address': g.get('address', '')}
            for c in ('_prec', '_nota'):
                if g.get(c):
                    venues[k][c] = g[c]
            if clave_sede in SIN_LUGAR:
                venues[k].update(SIN_LUGAR[clave_sede])
            if not g.get('lat'):
                avisos.append(f'sede sin coordenadas: {clave_sede}')

        base, de_donde = heredar(fn['titulo'], fn.get('director', ''))
        if base is None and not es_evento:
            sin_ficha.append(fn['titulo'])
        b = dict(base or {})
        for campo, valor in (extra_ficha.get(fn['titulo']) or {}).items():
            if not campo.startswith('_') and not b.get(campo):
                b[campo] = valor
        # el post manda sobre la ficha vieja solo donde la vieja calla
        for k_, k2 in (('sinopsis', 'synopsis'), ('sinopsis_en', 'synopsis_en')):
            v = (del_post.get(norm(fn['titulo'])) or {}).get(k_)
            if v and not b.get(k2):
                b[k2], b['synopsis_lang'] = v, 'es' if k2 == 'synopsis' else b.get('synopsis_lang')
        # …y el PROGRAMA manda sobre todos: es el dato de ESTA edición
        if fn.get('anio'):
            b['year'] = fn['anio']
        if fn.get('pais'):
            b['country'] = fn['pais']
            b['flags'] = lib.banderas(fn['pais'])
        if fn.get('duracion_min'):
            b['duration'] = f"{fn['duracion_min']} min"
        if fn.get('sinopsis'):
            b['synopsis'], b['synopsis_lang'] = fn['sinopsis'], 'es'

        libre = not fn.get('costo')
        item = {
            'title': fn['titulo'],
            'director': fn.get('director') or '',
            'year': b.get('year'), 'duration': b.get('duration'),
            'country': b.get('country', ''), 'flags': b.get('flags', ''),
            'section': sec[0], 'day': fn['dia'], 'time': fn['hora'],
            'day_order': DIAS.index(fn['dia']),
            'venue': k,
            'has_qa': bool(fn.get('has_qa') or fn['titulo'] in CON_QA)
                      and (fn['titulo'], fn['dia']) not in SIN_QA_EN,
            # «Todas las actividades son de acceso libre», dicho por el festival
            # en su web — pero su propio programa cobra dos: la noche de vinilos
            # y la fiesta de clausura. Manda el programa.
            'is_free': libre,
            '_src': f"{fn['_src']['url']} ({fn['_src']['date']})",
        }
        if not libre:
            item['_nota'] = ' · '.join(x for x in (fn.get('_nota'),
                                                   f"Costo: {fn['costo']}") if x)
        elif fn.get('_nota'):
            item['_nota'] = fn['_nota']
        if fn.get('premiere'):
            item['premiere'] = fn['premiere']
        if fn.get('ciclo'):
            item['_nota'] = ' · '.join(x for x in (item.get('_nota'), fn['ciclo']) if x)
        if de_donde and de_donde != 'ficma-2026 (agosto)':
            item['_ficha_heredada_de'] = de_donde
        if sala:
            item['sala'] = sala
        for campo in ('tmdb_id', 'genre', 'poster', 'posterSource', 'synopsis',
                      'synopsis_en', 'synopsis_lang', 'lbSlug', 'title_en', 'rating'):
            if b.get(campo):
                item[campo] = b[campo]
        if (del_post.get(norm(fn['titulo'])) or {}).get('rating') and not item.get('rating'):
            item['rating'] = del_post[norm(fn['titulo'])]['rating']
        if es_evento:
            item['type'] = 'event'
            item['event_kind'] = fn.get('event_kind') or {
                'taller': 'taller', 'charla': 'ponencia'}[fn['tipo']]
            item['duration'] = item['duration'] or (
                f"{fn['duracion_min']} min" if fn.get('duracion_min') else
                f"{DURACION_POR_DEFECTO[fn['tipo']]} min" if fn.get('tipo') in
                DURACION_POR_DEFECTO else '120 min')
            if fn.get('info'):
                item['info'] = True
            for c in ('requires_registration', 'registration_url'):
                if fn.get(c):
                    item[c] = fn[c]
            if fn.get('_cupos'):
                item['_cupos'] = fn['_cupos']
        films.append(item)

    # ── EL CRUCE: lo que anunció Instagram tiene que estar en el PDF ──────────
    en_pdf = {(norm(f['title']), f['day'], f['time']) for f in films}
    por_obra = {}
    for f in films:
        por_obra.setdefault(norm(f['title']), []).append((f['day'], f['time']))
    for p in posts['funciones']:
        if (norm(p['titulo']), p['dia'], p['hora']) in en_pdf:
            continue
        donde = por_obra.get(norm(p['titulo']))
        avisos.append(
            f"«{p['titulo']}» se anunció {p['dia'][-2:]}·{p['hora']} y el programa "
            + (f"la pone {'; '.join(d[-2:] + '·' + h for d, h in donde)}"
               if donde else 'NO la trae'))

    films.sort(key=lambda f: (f['day'], f['time'], f['title']))
    secs = {v[0]: {'en': v[1], 'archetype': v[2], 'order': v[3]}
            for k, v in SECCIONES.items()
            if any(f['section'] == v[0] for f in films)}

    out = {
        '_provenance': {
            'programacion': 'PROGRAMACIÓN FICMA 17.pdf (78 páginas, una por función), '
                            'publicado en laficma.com el 18 sep 2026 — la primera parrilla '
                            'completa de la reprogramación',
            'franja': 'laficma.com/talleresficma17/ — 11 actividades académicas, aparte del PDF',
            'catalogo': 'heredado de la edición de agosto + TMDB para las obras nuevas',
            'sedes': 'las de agosto + las nuevas ubicadas en Google Maps',
            'acceso': 'libre salvo dos actividades que el propio programa cobra '
                      '(noche de vinilos y fiesta de clausura)',
            'capturado': '2026-09-18',
            'reprogramacion': 'aplazado el 10 ago por el sismo de Manizales; vuelve 19–26 SEP',
        },
        'name': 'FICMA', 'shortName': 'FICMA',
        'fullName': 'Feria Internacional de Cine de Manizales',
        'city': CIUDAD, 'country': 'CO',
        'dates': '19–26 SEP', 'dates_en': 'SEP 19–26', 'year': 2026,
        'timezoneOffset': '-05:00', 'storageKey': 'ficma2026_',
        'festivalStartStr': f'{DIAS[0]}T00:00:00', 'festivalEndStr': f'{DIAS[-1]}T23:59:00',
        'prioLimit': 4,
        # Dos actividades se pagan; el resto es libre. No es 'free'.
        'ticketing_model': 'mixed',
        # Los tres cortos locales del viernes 25 a las 19:00 en Redentoristas son
        # UNA función de clausura, no tres que compiten: el programa les da la
        # misma sede, la misma hora y el mismo rótulo. Es el único slot
        # compartido de toda la parrilla.
        'sharedSlotIsOneScreening': True,
        **lib.dias_config(DIAS, 'septiembre'),
        'sections': secs, 'venues': venues, 'films': films,
    }
    json.dump(out, open(f'{ST}/ficma-2026-build.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    dias_con = sorted({f['day'] for f in films})
    print(f'{len(films)} funciones · {len(venues)} sedes · {len(secs)} secciones')
    print(f'días declarados {len(DIAS)} ({DIAS[0]}…{DIAS[-1]}) · con función {len(dias_con)}: '
          + ', '.join(d[-2:] for d in dias_con))
    print(f'con póster {sum(1 for f in films if f.get("poster"))} · '
          f'con sinopsis {sum(1 for f in films if f.get("synopsis"))} · '
          f'con lbSlug {sum(1 for f in films if f.get("lbSlug"))}')
    sin_poster = sorted({f['title'] for f in films if not f.get('poster')})
    if sin_poster:
        print(f'sin afiche ({len(sin_poster)}):')
        for s in sin_poster:
            print('   ·', s)
    if avisos:
        print(f'avisos ({len(avisos)}):')
        for a in dict.fromkeys(avisos):
            print('   ⚠', a)


if __name__ == '__main__':
    main()
