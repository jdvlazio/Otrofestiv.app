# -*- coding: utf-8 -*-
"""Ensambla FICMA 17 → festivals/ficma-2026.json

Junta las tres fuentes que produjeron los pasos anteriores:

  · ficma-2026-crudo.json    — el PDF, leído con OCR (Vision) y parseado. Manda
                               sobre programación: día, hora, sede, sala, sección,
                               título, director, país, duración, año y Q&A.
  · ficma-2026-tmdb.json     — enriquecimiento VERIFICADO (director + año/duración).
                               Aporta póster, sinopsis y géneros. No manda sobre
                               ningún dato que el PDF publique: si el festival dice
                               86 min, van 86 aunque TMDB diga 88.
  · ficma-2026-venues-geo.json — coordenadas. Las `_prec: manual` son de Juan
                               contra Google Maps y no se tocan.

El PDF es la autoridad porque es el programa del festival; TMDB es una fuente de
ficha, no de programación. Esa jerarquía evita que un dato de catálogo mueva una
función, que es como se rompió Medellín en FICDEH.
"""
import json, os, re, shutil, unicodedata, collections, datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
OUT = f'{REPO}/festivals/ficma-2026.json'
CIUDAD = 'Manizales'

# ── secciones ────────────────────────────────────────────────────────────────
# El NOMBRE va tal cual lo escribe el festival (regla permanente de onboarding),
# con UNA excepción decidida por Juan el 8 ago: «EN ALIANZA CON EL FESTIVAL DE
# DERECHOS HUMANOS» se acorta a «En alianza con el FICDEH» — el nombre completo
# desborda el chip de sección y FICDEH es como se conoce al festival aliado.
# lo único nuestro son el emoji, el inglés y el arquetipo. El PDF las imprime en
# versalitas — eso es tipografía, no el nombre, así que van en capitalización
# normal. FICMA no programa por competencias sino por TEMAS de coleccionismo y
# ciudad, y los emojis siguen esa lógica.
SECCIONES = {
# El arquetipo NO es una etiqueta libre: es la clave del color (ARCHETYPE_COLORS,
# 9 valores cerrados) y un gate lo exige. Las dos secciones de estrenos son la
# cabecera del festival y llevan colores distintos entre sí; las temáticas
# comparten «Perspectivas», salvo las dos que miran al pasado —antigüedades y
# numismática—, que van con el color de retrospectiva.
    'ESTRENOS NACIONALES':        ('🎬 Estrenos Nacionales', 'National Premieres', 'Competencia', 1),
    'ESTRENOS INTERNACIONALES':   ('🌍 Estrenos Internacionales', 'International Premieres', 'Muestra / País', 2),
    'EN ALIANZA CON EL FESTIVAL DE DERECHOS HUMANOS':
        ('🕊️ En alianza con el FICDEH',
         'In Partnership with FICDEH', 'Especiales / Eventos', 3),
    'ARTE':                       ('🎨 Arte', 'Art', 'Perspectivas / Miradas', 4),
    'ARTE POP':                   ('🥫 Arte Pop', 'Pop Art', 'Perspectivas / Miradas', 5),
    'CÓMIC':                      ('💥 Cómic', 'Comics', 'Perspectivas / Miradas', 6),
    'MÚSICA':                     ('🎵 Música', 'Music', 'Perspectivas / Miradas', 7),
    'ARQUITECTURA':               ('🏗️ Arquitectura', 'Architecture', 'Perspectivas / Miradas', 8),
    'ANTIGÜEDADES':               ('🕰️ Antigüedades', 'Antiques', 'Retrospectiva / Tributo', 9),
    'NUMISMÁTICA':                ('🪙 Numismática', 'Numismatics', 'Retrospectiva / Tributo', 10),
    'MEDIO AMBIENTE':             ('🌱 Medio Ambiente', 'Environment', 'Perspectivas / Miradas', 11),
    'RED DE MUSEOS':              ('🏛️ Red de Museos', 'Museum Network', 'Especiales / Eventos', 12),
    # Franja Académica — el festival la divide en dos y así se respeta. Mismos
    # emojis que en FICDEH para lo mismo, para que se lea igual entre festivales.
    'TALLERES':                   ('🛠️ Talleres', 'Workshops', 'Charlas / Industria', 13),
    'CHARLAS':                    ('💬 Charlas', 'Talks', 'Charlas / Industria', 14),
}

BANDERAS = {
    'colombia': '🇨🇴', 'argentina': '🇦🇷', 'brasil': '🇧🇷', 'chile': '🇨🇱', 'mexico': '🇲🇽',
    'peru': '🇵🇪', 'panama': '🇵🇦', 'espana': '🇪🇸', 'francia': '🇫🇷', 'italia': '🇮🇹',
    'alemania': '🇩🇪', 'reino unido': '🇬🇧', 'estados unidos': '🇺🇸', 'canada': '🇨🇦',
    'japon': '🇯🇵', 'china': '🇨🇳', 'iran': '🇮🇷', 'india': '🇮🇳', 'rusia': '🇷🇺',
    'polonia': '🇵🇱', 'dinamarca': '🇩🇰', 'suecia': '🇸🇪', 'noruega': '🇳🇴', 'irlanda': '🇮🇪',
    'belgica': '🇧🇪', 'paises bajos': '🇳🇱', 'portugal': '🇵🇹', 'suiza': '🇨🇭',
    'macedonia del norte': '🇲🇰', 'nueva zelanda': '🇳🇿', 'australia': '🇦🇺',
    'grecia': '🇬🇷', 'turquia': '🇹🇷', 'austria': '🇦🇹', 'luxemburgo': '🇱🇺',
}
DIA_ES = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
DIA_AB = ['LUN', 'MAR', 'MIÉ', 'JUE', 'VIE', 'SÁB', 'DOM']
DIA_EN = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']


# ── correcciones y material que el PDF no da ─────────────────────────────────
# Títulos que el OCR o el propio programa escriben mal. Se corrigen contra el
# AFICHE OFICIAL, que es la fuente más fuerte sobre cómo se llama una obra.
TITULO_OFICIAL = {
    # El programa dice «AA95»; el afiche dice «AA 965» — es el vuelo 965 de
    # American Airlines, el que cayó en el Valle en 1995. Al OCR se le fue un dígito.
    'AA95 un rescate imposible': 'AA965 un rescate imposible',
    # El afiche dice «Puntos de fuga» (plural) y da el internacional. Con el
    # título correcto la película SÍ aparece en TMDB (id 1525164).
    'Punto de Fuga': 'Puntos de fuga',
}
TITULO_EN_MANUAL = {'Punto de Fuga': 'Vanishing Points'}   # del afiche oficial

# EXCEPCIÓN a «el PDF manda»: duraciones donde el programa se equivocó y Juan
# resolvió a favor de la oficial (8 ago). Va como tabla y no como «si TMDB
# difiere, gana TMDB»: esa regla automática movería 30 funciones sin que nadie
# lo decida, y en un festival la duración programada suele ser la buena.
DURACION_OFICIAL = {
    'Punto de Fuga': 72,     # el programa dice 90; TMDB y la distribución, 72
}
TMDB_MANUAL = {'Punto de Fuga': 1525164}

# Pósters que no salieron de TMDB. `editorial` marca un still 16:9: la app lo
# enmarca sin recortarlo en vez de forzarlo dentro de un slot 2:3
# (_isEditorialPoster → posterModel). `custom` es un cartel vertical oficial.
POSTER_OFICIAL = {
    'AA95 un rescate imposible':            ('aa965-un-rescate-imposible.jpg', 'custom'),
    'Cuando la palabra se hace búsqueda: El eco de sus voces':
        ('cuando-la-palabra-se-hace-b-squeda-el-eco-de-sus-voces.jpg', 'custom'),
    'Punto de Fuga':                        ('puntos-de-fuga.jpg', 'custom'),
    'Cómo limpiar un espejo':               ('c-mo-limpiar-un-espejo.jpg', 'editorial'),
    # Heredados de FICDEH: son las MISMAS obras de la sección en alianza, con
    # póster y sinopsis oficiales que el festival aliado ya nos dio.
    'Desierto verde':                       ('desierto-verde.jpg', 'custom'),
    'Notas sobre un destierro':             ('notas-sobre-un-destierro.jpg', 'custom'),
}
HEREDA_SINOPSIS_FICDEH = ('Desierto verde', 'Notas sobre un destierro')

# Sinopsis de PRIMERA FUENTE para obras que el PDF no describe y TMDB no tiene.
# La regla (docs/PIPELINE.md) es que la sinopsis salga de quien hizo o distribuye
# la película, y que se verifique contra tres anclas: director, país y duración.
# La ES es traducción nuestra de la oficial en inglés — el camino documentado
# cuando solo existe en un idioma.
SINOPSIS_PRIMERA_FUENTE = {
    'Punto de Fuga': {
        'es': 'A lo largo de más de setenta años, dos mujeres cuentan cómo fue crecer en '
              'Colombia y emigrar a Canadá. Atravesado por momentos clave de la historia '
              'colombiana, «Puntos de fuga» es un ensayo fílmico sobre el enredo entre la '
              'historia oficial y las historias personales, y sobre lo complejo de la '
              'identidad diaspórica.',
        'en': 'Spanning over 70 years, two women recount their experiences growing up in '
              'Colombia and immigrating to Canada. Intersecting with key moments in '
              'Colombian history, Vanishing Points is an essay film that reflects on the '
              'entanglements between official histories and personal stories, and the '
              'complexities of diasporic identity.',
        '_src': 'rayonverde.com/puntos-de-fuga — la distribuidora de la película. '
                'Verificado contra las tres anclas: Lina Rodríguez ✓, Colombia/Canadá ✓, '
                '72 min ✓ (la misma duración que corrige el dato del programa).',
    },
    # OJO al buscar material de esta: su director tiene OTRA película sobre el
    # mismo accidente, la ficción «Rescate en el Valle» (2023). Una búsqueda
    # devuelve esa sinopsis y encaja lo suficiente como para colarse. Esta es el
    # documental de 2026, y la sinopsis vino del festival.
    'AA95 un rescate imposible': {
        'es': 'En diciembre de 1995, un Boeing 757 de American Airlines se estrelló en los '
              'cerros de Buga, dejando 156 muertos y apenas cinco sobrevivientes. Perdidos '
              'entre la niebla y la montaña, esperaron durante horas un rescate para el que '
              'Colombia no estaba preparada.\n\nAños después, comenzaron a surgir '
              'testimonios desconocidos sobre los heroicos esfuerzos de rescatistas y '
              'médicos anónimos que arriesgaron sus propias vidas para salvar a los '
              'sobrevivientes.\n\nA través de entrevistas exclusivas y relatos inéditos, '
              'este documental reconstruye una tragedia olvidada y revela la extraordinaria '
              'historia humana que nació en medio del desastre.',
        'genero': 'Documental',   # «este documental», lo dice el propio texto
        '_src': 'material oficial del festival (8 ago 2026). Solo en español.',
    },
    'Que el cielo nos perdone': {
        'es': 'Colombia, 1951: En medio de La Violencia, el período de brutal guerra '
              'política entre liberales y conservadores, un par de chulavitas —asesinos a '
              'sueldo pagados por el gobierno— acechan a un sacerdote en la oscuridad de la '
              'noche, esperando que los conduzca a la cabaña en el bosque en donde se '
              'esconden sus próximas víctimas. Pero el horror que encontrarán allí es mil '
              'veces peor que el dolor que pensaban infligir.',
        'genero': 'Terror',       # la ficha oficial: Ficción / Terror / Suspenso
        'title_en': 'May heaven forgive us',
        '_src': 'material oficial del festival (8 ago 2026). La ficha da 16 min y el '
                'programa 17: se conservan los 17 del programa, que es la duración con la '
                'que el festival armó el horario.',
    },
    'Cómo limpiar un espejo': {
        'es': 'Días antes de mudarse a Bogotá, Tomás enfrenta la culpa de haber traicionado '
              'a su mejor amigo, al ver cómo su propia situación se refleja en las acciones '
              'de su madre.',
        'en': 'Days before moving to Bogotá, Tomás confronts the guilt of betraying his best '
              'friend, noticing how his own situation is reflected in his mother\u2019s actions.',
        'genero': 'Drama',
        '_src': 'material oficial del festival (8 ago 2026), en español e inglés. La ficha '
                'lo clasifica como DRAMA/FICCIÓN.',
    },
    'Cuando la palabra se hace búsqueda: El eco de sus voces': {
        'es': 'En Colombia, la búsqueda de las personas desaparecidas ha abierto caminos '
              'inesperados de encuentro entre quienes sufren su ausencia y quienes guardan '
              'información clave sobre su paradero. Este largometraje documental revela el '
              'papel fundamental de los aportantes de información, en las voces de quienes '
              'participaron directa e indirectamente en las hostilidades y que, desde el '
              'compromiso, han decidido sumarse al proceso humanitario de la búsqueda '
              'liderado por la Unidad de Búsqueda de Personas dadas por Desaparecidas '
              '(UBPD).\n\nA través de historias íntimas y encuentros improbables entre '
              'víctimas y antiguos actores del conflicto, la película expone cómo la verdad '
              'compartida —desde un enfoque extrajudicial, confidencial y humanitario— se '
              'convierte en una herramienta para aliviar el dolor de las familias y '
              'dignificar la memoria de quienes desaparecieron.',
        'genero': 'Documental',   # lo dice el propio texto: «este largometraje documental»
        '_src': 'material oficial del festival (8 ago 2026). Solo en español.',
    },
}


def sinacento(s):
    return ''.join(c for c in unicodedata.normalize('NFD', (s or '').lower())
                   if unicodedata.category(c) != 'Mn').strip()


def banderas(pais):
    out = [BANDERAS[k] for p in re.split(r'[,/]| y ', pais or '')
           if (k := sinacento(p)) in BANDERAS]
    return ''.join(dict.fromkeys(out))


def slug(t):
    return ''.join(c if c.isalnum() else '-' for c in t.lower()).strip('-')[:60]


def main():
    crudo = json.load(open(f'{ST}/ficma-2026-crudo.json', encoding='utf-8'))
    tmdb = json.load(open(f'{ST}/ficma-2026-tmdb.json', encoding='utf-8'))['verificadas']
    title_en = json.load(open(f'{ST}/ficma-2026-title-en.json', encoding='utf-8'))['title_en']
    lb = json.load(open(f'{ST}/ficma-2026-letterboxd.json', encoding='utf-8'))['lbSlug']
    geo = json.load(open(f'{ST}/ficma-2026-venues-geo.json', encoding='utf-8'))
    funcs = crudo['funciones']

    # ── Franja Académica ─────────────────────────────────────────────────────
    # 12 actividades de un PDF aparte. Se convierten al mismo shape que una
    # función de película para que el resto del ensamblador no las distinga: una
    # actividad de varios días produce una entrada POR DÍA, y el bloque se marca
    # con is_recurring (el plan las toma todas o ninguna).
    franja = json.load(open(f'{ST}/ficma-2026-franja.json', encoding='utf-8'))['actividades']
    for a in franja:
        for dia in a['dias']:
            funcs.append({
                'pagina': a['pagina'], 'dia': dia, 'hora': a['hora'],
                'sede': a['sede'], 'sala': a.get('sala', ''), 'ciclo': '',
                'seccion': 'TALLERES' if a['tipo'] == 'taller' else 'CHARLAS',
                'titulo': a['titulo'],
                # En una charla el «director» es quien la dicta: invitados y
                # moderación. Es lo que la ficha muestra bajo el título.
                'director': a['tallerista'] or ', '.join(
                    x for x in (a['invitados'], a['modera'] and f'modera {a["modera"]}') if x),
                'pais': '', 'anio': None,
                # Sin rango horario publicado (las charlas) no se inventa: 90 min
                # es el DEFAULT_DURATION_MIN del dominio y queda explícito aquí.
                'duracion_min': a['duracion_min'] or 90,
                'has_qa': False,
                '_franja': a,
            })

    dias = sorted({f['dia'] for f in funcs})
    fecha = lambda d: datetime.date.fromisoformat(d)

    # ── venues ───────────────────────────────────────────────────────────────
    # La clave lleva la ciudad como en el resto de festivales, aunque FICMA sea
    # de una sola: es el formato que el loader y las fichas esperan.
    venues, sin_ubicar = {}, []
    for f in funcs:
        k = f'{f["sede"]} - {CIUDAD}'
        if k in venues:
            continue
        g = geo.get(f['sede'], {})
        if not g.get('lat'):
            sin_ubicar.append(f['sede'])
        venues[k] = {'short': f['sede'], 'lat': g.get('lat'), 'lng': g.get('lng'),
                     'city': CIUDAD, 'address': ''}
        if g.get('_prec'):
            venues[k]['_prec'] = g['_prec']

    # ── films ────────────────────────────────────────────────────────────────
    # Sinopsis oficiales del catálogo de FICDEH para las obras compartidas.
    ficdeh = {x['title']: x for x in json.load(
        open(f'{REPO}/festivals/ficdeh-2026.json', encoding='utf-8'))['films']}

    films, sin_tmdb = [], []
    for f in funcs:
        t = tmdb.get(f['titulo'], {})
        if not t:
            sin_tmdb.append(f['titulo'])
        sec = SECCIONES.get(f['seccion'])
        if not sec:
            raise SystemExit(f'sección sin declarar: «{f["seccion"]}» (pág {f["pagina"]})')
        _fa = f.get('_franja')
        e = {
            'title': TITULO_OFICIAL.get(f['titulo'], f['titulo']),
            'director': f['director'],
            'year': str(f['anio']),
            # La duración es la del PDF, SIEMPRE: es la que el festival programó.
            # TMDB difiere hasta en 3 min y mover eso corre el fin de la función.
            'duration': f'{DURACION_OFICIAL.get(f["titulo"], f["duracion_min"])} min',
            'country': f['pais'],
            'flags': banderas(f['pais']),
            'section': sec[0],
            'day': f['dia'],
            'time': f['hora'],
            'venue': f'{f["sede"]} - {CIUDAD}',
            'has_qa': f['has_qa'],
            '_src': 'FICMA 17 - PROGRAMACIÓN.pdf (OCR) · ' + f['pagina'],
        }
        if _fa:
            # Actividad, no película: sin país ni año, con tipo de evento.
            e['type'] = 'event'
            e['event_kind'] = 'taller' if _fa['tipo'] == 'taller' else 'ponencia'
            for k in ('country', 'flags', 'year'):
                e.pop(k, None)
            if _fa['requires_registration']:
                e['requires_registration'] = True
            if _fa.get('registration_url'):
                e['registration_url'] = _fa['registration_url']
            if _fa.get('synopsis'):
                e['synopsis'], e['synopsis_lang'] = _fa['synopsis'], 'es'
            if _fa['is_recurring']:
                e['is_recurring'] = True
            if _fa.get('cupos'):
                e['_cupos'] = _fa['cupos']
            e['_src'] = 'FICMA 17 - FRANJA ACADÉMICA.pdf (OCR) · ' + _fa['pagina']
        if f.get('sala'):
            e['sala'] = f['sala']
        if f.get('ciclo'):
            # El ciclo es la marca del festival («Cine al barrio»), no la sede.
            e['cycle'] = f['ciclo']
        if t:
            e['tmdb_id'] = t['tmdb_id']
            if (g := (t.get('generos') or [''])[0]):
                e['genre'] = g
            # Nunca poster:'' — el gate [poster-empty-film] lo bloquea y con razón:
            # un string vacío es un póster roto, la ausencia es un dato honesto.
            if t.get('poster_path'):
                e['poster'] = f'/assets/ficma/{slug(f["titulo"])}.jpg'
                e['posterSource'] = 'tmdb'
            if t.get('synopsis_es'):
                e['synopsis'], e['synopsis_lang'] = t['synopsis_es'], 'es'
            elif t.get('synopsis_en'):
                e['synopsis'], e['synopsis_lang'] = t['synopsis_en'], 'en'
            if t.get('synopsis_en'):
                e['synopsis_en'] = t['synopsis_en']
            if t.get('titulo_original') and t['titulo_original'] != f['titulo']:
                e['original_title'] = t['titulo_original']
        # title_en: el título con que la obra se distribuye en inglés, traído de
        # TMDB sobre un tmdb_id ya verificado (pipeline/ficma-2026-title-en.py).
        # Las que ya se llaman igual en inglés no lo llevan.
        # lbSlug: lo resuelve Letterboxd desde su mapeo con el tmdb_id verificado
        # (pipeline/ficma-2026-letterboxd.py). Sin mapeo → sin botón, nunca un homónimo.
        if f['titulo'] in lb:
            e['lbSlug'] = lb[f['titulo']]
        _en = ((_sf or {}).get('title_en') if (_sf := SINOPSIS_PRIMERA_FUENTE.get(f['titulo'])) else None) \
              or TITULO_EN_MANUAL.get(f['titulo']) or title_en.get(f['titulo'])
        if _en:
            e['title_en'] = _en
        if f['titulo'] in TMDB_MANUAL:
            e['tmdb_id'] = TMDB_MANUAL[f['titulo']]
        if f['titulo'] in POSTER_OFICIAL:
            arch, tipo = POSTER_OFICIAL[f['titulo']]
            e['poster'], e['posterSource'] = f'/assets/ficma/{arch}', tipo
        if f['titulo'] in HEREDA_SINOPSIS_FICDEH and not e.get('synopsis'):
            src = ficdeh.get(f['titulo'], {})
            if src.get('synopsis'):
                e['synopsis'] = src['synopsis']
                e['synopsis_lang'] = src.get('synopsis_lang', 'es')
                e['_inherited'] = 'sinopsis y póster del catálogo de FICDEH (misma obra)'
                if src.get('synopsis_en'):
                    e['synopsis_en'] = src['synopsis_en']
        _sf = SINOPSIS_PRIMERA_FUENTE.get(f['titulo'])
        if _sf and not e.get('synopsis'):
            e['synopsis'], e['synopsis_lang'] = _sf['es'], 'es'
            if _sf.get('en'):
                e['synopsis_en'] = _sf['en']
            if _sf.get('genero') and not e.get('genre'):
                e['genre'] = _sf['genero']
            e['_src_synopsis'] = _sf['_src']
        if not e.get('synopsis'):
            e['_pendiente'] = 'sin sinopsis'
        films.append(e)

    films.sort(key=lambda x: (x['day'], x['time'], x['title']))
    # day_order — el ÍNDICE DEL DÍA dentro de dayKeys, no la posición de la
    # función dentro del día. Lo tenía como contador correlativo y por eso en la
    # ficha de un taller multi-día el SÁB 15 salía antes que el VIE 14: la
    # primera sesión del sábado llevaba 0 y la segunda del viernes 1.
    # Guardián: [day-order-indice] en validate-festivals.js.
    for x in films:
        x['day_order'] = dias.index(x['day'])

    d = {
        '_provenance': {
            'programacion': 'FICMA 17 - PROGRAMACIÓN.pdf — 87 páginas de imagen (son los posts de '
                            'Instagram exportados desde un iPhone), leídas con OCR de Vision y '
                            'parseadas por la plantilla fija: una página, una función.',
            'catalogo': 'TMDB, emparejado con VERIFICACIÓN: director + (año ±1 o duración ±3 min). '
                        'Lo que no verifica no se acepta.',
            'sedes': 'Nominatim con verificación de tipo de lugar; las marcadas _prec:manual las '
                     'ubicó Juan en Google Maps y mandan sobre las automáticas.',
            'acceso': 'Entrada libre a todo el festival (confirmado por Juan, 8 ago 2026).',
        },
        'name': 'FICMA', 'shortName': 'FICMA',
        'fullName': 'Feria Internacional de Cine de Manizales',
        'city': CIUDAD, 'country': 'CO',
        'dates': '10–17 AGO', 'dates_en': 'AUG 10–17', 'year': 2026,
        'timezoneOffset': '-05:00', 'storageKey': 'ficma2026_',
        'festivalStartStr': f'{dias[0]}T00:00:00', 'festivalEndStr': f'{dias[-1]}T23:59:00',
        'festivalDates': {x: x for x in dias},
        'days': [{'k': x, 'd': fecha(x).day, 'lbl': DIA_AB[fecha(x).weekday()]} for x in dias],
        'dayKeys': dias,
        'dayShort': {x: f'{DIA_AB[fecha(x).weekday()]} {fecha(x).day}' for x in dias},
        'dayShort_en': {x: f'{DIA_EN[fecha(x).weekday()]} {fecha(x).day}' for x in dias},
        'dayLong': {x: f'{DIA_ES[fecha(x).weekday()]} {fecha(x).day} de agosto' for x in dias},
        'prioLimit': 4,
        # Tres funciones del festival juntan un corto y un largo bajo una sola
        # cabecera de horario. Confirmado con Juan (8 ago). El flag es de raíz:
        # también alcanza al bloque del jueves 13, que espera confirmación del
        # festival — y si resultara ser dos funciones distintas, se corrige el
        # dato, no el modelo.
        'sharedSlotIsOneScreening': True,
        'sections': {v[0]: {'en': v[1], 'archetype': v[2], 'order': v[3]}
                     for v in sorted(SECCIONES.values(), key=lambda x: x[3])},
        'venues': venues,
        'films': films,
    }
    json.dump(d, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    print(f'{OUT}  {os.path.getsize(OUT)//1024} KB')
    print(f'  films {len(films)} · obras {len({x["title"] for x in films})} · '
          f'venues {len(venues)} · secciones {len(SECCIONES)} · días {len(dias)}')
    print(f'  con póster {sum(1 for x in films if x.get("poster"))} · '
          f'con sinopsis {sum(1 for x in films if x.get("synopsis"))} · '
          f'con Q&A {sum(1 for x in films if x["has_qa"])}')
    print(f'  sin ubicar {sorted(set(sin_ubicar))}')
    print(f'  con título EN {sum(1 for x in films if x.get("title_en"))} · '
          f'con Letterboxd {sum(1 for x in films if x.get("lbSlug"))}')
    print(f'  sin ficha TMDB {len(set(sin_tmdb))}: {sorted(set(sin_tmdb))}')
    slots = [k for k, n in collections.Counter(
        (x['day'], x['time'], x['venue'], x.get('sala', '')) for x in films).items() if n > 1]
    print(f'  slots compartidos {len(slots)}')


if __name__ == '__main__':
    main()
