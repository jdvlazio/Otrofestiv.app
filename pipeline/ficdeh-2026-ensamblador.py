# -*- coding: utf-8 -*-
"""Ensamblador Etapa B de FICDEH 2026.

Entradas:
  · festivals/staging/ficdeh-2026.json                     → catálogo (94 obras)
  · festivals/staging/ficdeh-2026-programacion-oficial.json → 433 funciones (424 en_app)
Salida:
  · festivals/staging/ficdeh-2026-build.json               → festival completo

Decisiones aplicadas (Juan): entran 18 charlas + 9 talleres abiertos; fuera
industria y sedes en el extranjero. Multi-ciudad: cada venue lleva `city`.
"""
import json, re, unicodedata, collections, datetime, os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAT  = json.load(open(f'{REPO}/festivals/staging/ficdeh-2026.json', encoding='utf-8'))
PROG = json.load(open(f'{REPO}/festivals/staging/ficdeh-2026-programacion-oficial.json', encoding='utf-8'))

def norm(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()

# ── catálogo indexado ────────────────────────────────────────────────────────
by_title = {f['title']: f for f in CAT['films']}

# ── funciones que entran ─────────────────────────────────────────────────────
# Ventana OFICIAL del festival (decisión de Juan, 5 ago): 12–19 AGO. Las
# funciones del 10, 11, 20 y 24 son actividades alternativas fuera de programa.
VENTANA = {f'2026-08-{d}' for d in range(12, 20)}
funcs = [f for f in PROG['funciones'] if f.get('en_app') and f['dia'] in VENTANA]
fuera = [f for f in PROG['funciones'] if f.get('en_app') and f['dia'] not in VENTANA]
dias  = sorted({f['dia'] for f in funcs})

LBL    = ['LUN','MAR','MIÉ','JUE','VIE','SÁB','DOM']
LBL_EN = ['MON','TUE','WED','THU','FRI','SAT','SUN']
NOM    = ['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo']
def wd(k): return datetime.date.fromisoformat(k).weekday()
def dnum(k): return int(k[-2:])

# ── venues: clave "Sede - Ciudad" ────────────────────────────────────────────
# Las coordenadas viven en un SIDECAR (ficdeh-2026-venues-geo.json) y se
# mergean aquí: este script regenera el build desde cero, así que escribirlas
# en el build las perdería en la siguiente pasada (pasó el 5 ago).
GEO_PATH = f'{REPO}/festivals/staging/ficdeh-2026-venues-geo.json'
GEO = json.load(open(GEO_PATH, encoding='utf-8')) if os.path.exists(GEO_PATH) else {}
# Sinopsis, póster y si pide inscripción de cada actividad (de /charlas/<slug>
# y /talleres/<slug>). El póster vive en /uploads/obras/ del sitio del festival.
ACT_PATH = f'{REPO}/festivals/staging/ficdeh-2026-actividades.json'
ACT = json.load(open(ACT_PATH, encoding='utf-8')) if os.path.exists(ACT_PATH) else {}
# Detalle de cada ficha de charla/taller: DURACIÓN (del rango «Hora : 9:00 a.m.
# - 12:00 M.») e INSCRIPCIÓN leída del campo. Solo 4 de 42 fichas publican el
# rango, y una de ellas —Pintando realidades, 90 min— demuestra que la duración
# NO es uniforme: por eso el dato real gana y los 180 min quedan de respaldo.
DET_PATH = f'{REPO}/festivals/staging/ficdeh-2026-actividades-detalle.json'
DET = (json.load(open(DET_PATH, encoding='utf-8'))['actividades']
       if os.path.exists(DET_PATH) else {})


def _slug(t):
    t = unicodedata.normalize('NFD', (t or '').lower())
    t = ''.join(c for c in t if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', '-', t).strip('-')


def detalle(titulo):
    """La ficha se busca por slug: el sidecar viene indexado por la url."""
    sl = _slug(titulo)
    if sl in DET:
        return DET[sl]
    return next((v for k, v in DET.items()
                 if k.startswith(sl[:34]) or sl.startswith(k[:34])), {})


def _poster_local(url):
    """El sitio del festival sirve sus pósters en /uploads/obras/…; esa ruta en
    nuestra app es un 404 y la card sale con el icono de imagen rota (lo vimos
    en «Pintando realidades»). Los archivos se bajan a assets/ficdeh/ y aquí se
    reescribe la ruta."""
    if url.startswith('/uploads/'):
        return '/assets/ficdeh/' + url.rsplit('/', 1)[-1]
    return url
# La programación escribe la SALA dentro del nombre de la sede («Sala 2 -
# Cinemateca de Bogotá»), así que un mismo lugar entra al catálogo como varias
# sedes distintas: la Cinemateca aparecía 5 veces, y en el filtro por sede se
# leían como 5 lugares. La sala no es una sede: es un dato de la función, y el
# schema ya tiene campo para ella (`sala`, que el dominio usa en la clave de
# anclaje día|hora|sede|sala). Tabla explícita —no heurística sobre el guion,
# que partiría nombres legítimos como «La Trocha - Casa de la Paz».
SEDE_SALA = {
    'Sala 2 - Cinemateca de Bogotá':            ('Cinemateca de Bogotá', 'Sala 2'),
    'Sala 2 de la Cinemateca':                  ('Cinemateca de Bogotá', 'Sala 2'),
    'Laboratorio 1 y 2 - Cinemateca de Bogotá': ('Cinemateca de Bogotá', 'Laboratorio 1 y 2'),
    'Laboratorio 1 y 2':                        ('Cinemateca de Bogotá', 'Laboratorio 1 y 2'),
    'Auditorio C202 - UNIMINUTO':               ('Universidad Minuto de Dios', 'Auditorio C202'),
    'UNIVERSIDAD TECNOLÓGICA DE PEREIRA - BLOQUE 7A / 118':
        ('Universidad Tecnológica de Pereira -UTP', 'Bloque 7A / 118'),
    'Universidad Tecnológica de Pereira - Bloque 13, Sala Magistral 1':
        ('Universidad Tecnológica de Pereira -UTP', 'Bloque 13, Sala Magistral 1'),
    'Centro Cultural - Sala Audiovisual de Cali':
        ('Centro Cultural de Cali', 'Sala Audiovisual'),
    # «Cinemateca» a secas: la fuente repite 3 funciones de la Cinemateca de
    # Bogotá con este nombre, misma sala y hora, pero con la dirección de la
    # Cinemateca del Museo La Tertulia (que es de Cali) y sin tipo de ingreso.
    # Se unifica y el dedup posterior se queda con la entrada completa.
    'Cinemateca': ('Cinemateca de Bogotá', ''),
    # La web escribe «La Trocha, La Casa de la Paz» y el resto del festival
    # «La Trocha - Casa de la Paz»: la misma sede, dos grafías, dos pins a 0 m.
    # Lo cazó [sedes-apiladas] en su primera corrida (9 ago) — el duplicado
    # entró el 8 ago con las funciones nuevas de «Lo que sentimos».
    'La Trocha, La Casa de la Paz': ('La Trocha - Casa de la Paz', ''),
}


# La guía en PDF de Medellín es la única fuente que dice en qué sala del Colombo
# Americano va cada función — y proyecta en SALA 1 y SALA 2 el mismo día, así que
# sin este dato el anclaje día|hora|sede junta funciones que son paralelas.
SALAS_PATH = f'{REPO}/festivals/staging/ficdeh-2026-salas-medellin.json'
SALAS = (json.load(open(SALAS_PATH, encoding='utf-8'))['salas']
         if os.path.exists(SALAS_PATH) else {})


def _norm(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def sede_sala(f):
    """→ (sede, sala). Manda la guía en PDF; luego la sala explícita de la
    programación; por último la que venía metida en el nombre de la sede."""
    sede, sala = SEDE_SALA.get(f['sede'], (f['sede'], ''))
    del_pdf = SALAS.get(f"{f['dia']}|{f['hora']}|{_norm(f['sede'])}")
    return sede, (del_pdf or f.get('sala') or sala or '')


venues = {}
def venue_key(f):
    sede, _ = sede_sala(f)
    key = f'{sede} - {f["ciudad"]}'
    if key not in venues:
        g = GEO.get(key, {})
        venues[key] = {'short': sede, 'lat': g.get('lat'), 'lng': g.get('lng'),
                       'city': f['ciudad'], 'address': f.get('direccion','') or ''}
        if g.get('_geo'): venues[key]['_geo'] = g['_geo']
        # _nota: sedes que caen a <60 m de otra y que ya se revisaron a mano
        # (el guardián [sedes-apiladas] la exige para no volver a preguntar).
        # Vive en el sidecar, no en el publicado: si no se propagara aquí, el
        # próximo ensamblado la borraría.
        if g.get('_nota'): venues[key]['_nota'] = g['_nota']
    return key

# ── secciones de actividades (nombres del festival, regla "tal cual") ────────
# Nombres ES verbatim del festival (regla «secciones tal cual»); emoji y EN son
# nuestra capa, aprobados por Juan el 5 ago 2026.
#   💬 y no 🎤: el micrófono chocaba con el 🎙️ de Cortometraje Documental
#   Nacional — dos micrófonos casi idénticos a tamaño de riel.
#   «Workshops» y no «Training»: son talleres (animación 2D, pintura, actuación,
#   «Taller de Herramientas»), y es el término que busca el público de festival.
# Talleres que ocurren en VARIAS sesiones y se toman completos. Se declara a
# mano y no por «tiene más de una función»: una charla que se repite en dos
# ciudades también tendría varias, pero ahí sí son alternativas.
RECURRENTES = {
    'Los frutos que dan vida: Siembra autosostenible casera',   # 16 y 17 AGO, Aguas Fieras
}

SEC_ACT = {
  'charla': ('💬 Charlas que Unen', 'Talks That Unite', 'Charlas / Industria', 11),
  'taller': ('🛠️ Formación',        'Workshops',        'Charlas / Industria', 12),
}

sections = dict(CAT.get('sections') or {})
for k,(nombre,en,arch,order) in SEC_ACT.items():
    if nombre not in sections:
        sections[nombre] = {'oficial': nombre.split(' ',1)[1], 'en': en,
                            'archetype': arch, 'color': '#639922', 'order': order}

# ── ensamblado ───────────────────────────────────────────────────────────────
films_out, sin_ficha = [], collections.Counter()
for f in sorted(funcs, key=lambda x: (x['dia'], x['hora'], x['ciudad'])):
    base = {'day': f['dia'], 'time': f['hora'], 'venue': venue_key(f),
            'day_order': dias.index(f['dia']),
            'has_qa': False, 'is_cortos': False, 'film_list': None,
            **({'sala': sede_sala(f)[1]} if sede_sala(f)[1] else {}),
            # is_free/requires_registration salen del 'tipo de ingreso' que
            # publica cada función en la programación oficial.
            'is_free': f.get('ingreso','').strip().lower().startswith('entrada libre') or not f.get('ingreso'),
            'requires_registration': 'inscrip' in f.get('ingreso','').lower(),
            '_ingreso': f.get('ingreso',''),
            '_src': {'programacion_oficial': f['titulo_programacion']}}
    # El póster que publica la programación oficial es el mismo /uploads/obras/
    # del festival; solo se usa si la obra del catálogo no trae uno propio.
    if f['tipo'] in ('film','film_invitada'):
        obra = by_title.get(f['obra_catalogo']) if f['obra_catalogo'] else by_title.get(f['titulo_programacion'])
        if not obra:
            sin_ficha[f['titulo_programacion']] += 1
            continue
        e = {k: v for k, v in obra.items() if not k.startswith('_')}
        e.update(base); e['type'] = 'film'
        if not e.get('poster') and f.get('poster_url'):
            e['poster'] = _poster_local(f['poster_url']); e['posterSource'] = 'custom'
        e['_src'] = {**obra.get('_src', {}), **base['_src']}
    else:
        a = ACT.get(f['titulo_programacion'], {})
        # Duración de las actividades: ninguna fuente la publica por actividad,
        # y sin ella el dominio aplica DEFAULT_DURATION_MIN (90 min), que para un
        # taller de media tarde se queda corto. La guía en PDF de Medellín es la
        # única que da un rango real —«1:00 PM - 4:00 PM» en Los frutos que dan
        # vida—, así que los TALLERES toman esas 3 horas y las charlas se quedan
        # en los 90 min por defecto hasta que el festival confirme (Juan, 6 ago).
        # Duraciones oficiales que el festival confirmó para Medellín (6 ago):
        # Charlas que Unen 2:00–5:00 PM y talleres 1:00–4:00 PM, ambas 3 horas.
        # Sin este dato el dominio aplicaba 90 min por defecto y el plan cabía
        # cosas imposibles detrás de una charla.
        _d = detalle(f['titulo_programacion'])
        # Duraciones que solo constan en el póster oficial (Medellín, 7 ago).
        _DUR_POSTER = {'¿Cómo filmar un país en guerra?': 120,   # 4:30–6:30 PM
                       'Los frutos que dan vida: Siembra autosostenible casera': 180}  # 1–4 PM
        if f['titulo_programacion'] in _DUR_POSTER:
            _d = {**_d, 'duracion_min': _DUR_POSTER[f['titulo_programacion']]}
        # 180 min es lo que el festival confirmó para Medellín (charlas 2–5 PM,
        # talleres 1–4 PM); solo se usa cuando la ficha no publica su rango.
        _dur = f"{_d['duracion_min']} min" if _d.get('duracion_min') else '180 min'
        e = {'title': f['titulo_programacion'], 'type': 'event',
             'section': SEC_ACT[f['tipo']][0], 'duration': _dur,
             'synopsis': a.get('synopsis',''), 'synopsis_lang': 'es',
             'poster': _poster_local(a.get('poster','')), 'posterSource': 'custom' if a.get('poster') else '',
             'event_kind': 'ponencia' if f['tipo']=='charla' else 'masterclass'}
        e.update(base)
        if a.get('requires_registration') or _d.get('requires_registration'):
            e['requires_registration'] = True
        # El formulario de inscripción va en la FUNCIÓN (docs/SCHEMA.md §Ticketing),
        # no en la raíz: cada actividad tiene el SUYO —cada form se titula con el
        # nombre de su actividad—, así que ninguno es reutilizable. Los 6 que el
        # festival publica salen del bio oficial (linkship.cc/ficdeh); el sidecar
        # guarda de dónde vino cada uno en `_registration_url_src`.
        _ru = a.get('registration_url') or ''
        if _ru.startswith('https://'):
            e['registration_url'] = _ru
        # is_recurring — un taller de varias sesiones es UN bloque, no varias
        # opciones: quien se inscribe va a todas. Con esto la ficha ofrece un
        # solo «Añadir las N sesiones» en vez de un botón por sesión, y el plan
        # las mete todas o ninguna (schedule.js §is_recurring). La fuente lo
        # confirma sola: hay UN formulario de inscripción para las dos fechas.
        # Precedente: los talleres de Leviza 2026.
        if f['titulo_programacion'] in RECURRENTES:
            e['is_recurring'] = True
        if not e['synopsis']: e['_pendiente'] = 'sin sinopsis en la ficha del festival'
    films_out.append(e)

# ── slots compartidos: mismo día+hora+sede ───────────────────────────────────
slots = collections.Counter((e['day'], e['time'], e['venue']) for e in films_out)
compartidos = {k: v for k, v in slots.items() if v > 1}

# Pósters genéricos de sección: el sitio publica UNA «Portada_Charla» que sirve
# a las 18 charlas por igual. Repetido 18 veces en la grilla es peor que nada —
# para eso está el póster editorial por tipo (eventPosterLabel). Se detecta por
# repetición, no por lista negra, para que el próximo genérico también caiga.
# Se cuentan TÍTULOS distintos, no funciones: una actividad que se repite varios
# días (Los frutos que dan vida, 16 y 17 AGO) usa su póster dos veces sin que
# eso lo haga genérico. Contando funciones se le borraba el póster propio.
_uso = collections.Counter()
for _p, _t in {(e.get('poster'), e.get('title')) for e in films_out
               if e.get('type') == 'event' and e.get('poster')}:
    _uso[_p] += 1
_generico = {p for p, n in _uso.items() if n > 1}
for e in films_out:
    if e.get('poster') in _generico:
        e['poster'] = ''
        e['posterSource'] = ''
        e['_poster_descartado'] = 'genérico de sección (compartido por varias actividades)'
if _generico:
    print(f'  pósters genéricos descartados: {len(_generico)} → ' +
          ', '.join(f'{p.split("/")[-1]} (×{_uso[p]})' for p in _generico))

# Un poster vacío debe ser AUSENCIA de campo, no string vacío: el gate
# [poster-empty-film] lo rechaza y el fallback editorial necesita que falte.
for e in films_out:
    for k in ('poster', 'posterSource', 'lbSlug'):
        if k in e and not (e[k] or '').strip():
            del e[k]

# Dedup: la misma obra, el mismo día, a la misma hora y en la misma sala es UNA
# función, por más que la fuente la liste dos veces con dos grafías de la sede.
# Sin esto la app pinta dos proyecciones simultáneas de la misma película. Gana
# la entrada con más datos (la que trae tipo de ingreso).
_vistas, _dedup, _fuera = {}, [], []
for e in films_out:
    k = (e.get('day'), e.get('time'), e.get('venue'), e.get('sala', ''), e.get('title'))
    if None in k[:3]:
        _dedup.append(e)
        continue
    prev = _vistas.get(k)
    if prev is None:
        _vistas[k] = len(_dedup)
        _dedup.append(e)
    elif len((e.get('_ingreso') or '').strip()) > len((_dedup[prev].get('_ingreso') or '').strip()):
        _fuera.append(_dedup[prev]['title'])
        _dedup[prev] = e            # la nueva trae ingreso y la vieja no
    else:
        _fuera.append(e['title'])
if _fuera:
    print(f'  dedup: {len(_fuera)} funciones repetidas por grafía de sede → {sorted(set(_fuera))}')
films_out = _dedup

# Segunda pasada, SIN la sala en la clave: al corregir horarios con la guía en
# PDF, una función puede caer sobre otra idéntica que solo se diferencia en que
# una trae sala y la otra no. Gana la que tiene sala, que es la del PDF.
_v2, _out2, _fuera2 = {}, [], []
for e in films_out:
    k = (e.get('day'), e.get('time'), e.get('venue'), e.get('title'))
    if None in k[:3] or not e.get('title'):
        _out2.append(e); continue
    prev = _v2.get(k)
    if prev is None:
        _v2[k] = len(_out2); _out2.append(e)
    elif e.get('sala') and not _out2[prev].get('sala'):
        _fuera2.append(e['title']); _out2[prev] = e
    else:
        _fuera2.append(e['title'])
if _fuera2:
    print(f'  dedup (sin sala): {len(_fuera2)} → {sorted(set(_fuera2))}')
films_out = _out2

# ticket_url — solo la Cinemateca de Bogotá vende online, y el enlace no está
# ni en el sitio de FICDEH («Boletería en taquilla» a secas) ni en las fichas
# ni en la agenda de la Cinemateca: vive únicamente en su checkout de tuboleta,
# y solo se ve con JS (curl no lo alcanza). Cada boleta es de una FUNCIÓN, así
# que el enlace se reparte a todas las obras del slot.
TB_PATH = f'{REPO}/festivals/staging/ficdeh-2026-boleteria-tuboleta.json'
TB = json.load(open(TB_PATH, encoding='utf-8')) if os.path.exists(TB_PATH) else {'funciones': []}
TB_URL = 'https://cinemateca.checkout.tuboleta.com/selection/event/date?productId='


def _tit(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def _misma_sala(e, t):
    """La boleta es de UNA sala. Sin este filtro, un taller gratis en el
    Laboratorio hereda el enlace de compra de la película que va a esa misma
    hora en Sala Capital."""
    s = (e.get('sala') or '').strip()
    return not s or _tit(s) == _tit(t['sala'])


_tb_ok = _tb_no = 0
for t in TB['funciones']:
    slot = [e for e in films_out
            if e.get('day') == t['dia'] and e.get('time') == t['hora']
            and (e.get('venue') or '').startswith('Cinemateca de Bogotá')
            and _misma_sala(e, t)]
    if not slot:
        # la hora de tuboleta no cuadra con la del festival: se busca la obra
        # por título dentro del día (pasa con Desierto verde, ver más abajo)
        slot = [e for e in films_out
                if e.get('day') == t['dia'] and (e.get('venue') or '').startswith('Cinemateca de Bogotá')
                and _tit(e.get('title')) == _tit(t['titulo'])]
    if slot:
        for e in slot:
            e['ticket_url'] = TB_URL + t['productId']
        _tb_ok += 1
    else:
        _tb_no += 1
        print(f"  ⚠️ boleta sin función: {t['dia']} {t['hora']} «{t['titulo']}»")
print(f'  ticket_url: {_tb_ok}/{len(TB["funciones"])} boletas cruzadas → '
      f'{sum(1 for e in films_out if e.get("ticket_url"))} funciones con enlace de compra')

# has_qa — solo donde hay confirmación externa verificable. El sitio del
# festival no lo publica y las fichas de la Cinemateca tampoco (su menú incluye
# «Conversatorios y charlas», que aparece en las 30 páginas y NO es señal de
# nada). Hoy: la inauguración de Bogotá, confirmada por el afiche de @ficdeh.
# has_qa suma 30' a la ocupación de sala (effectiveDuration) → toca conflictos.
CONF_PATH = f'{REPO}/festivals/staging/ficdeh-2026-confirmaciones-externas.json'
CONF = json.load(open(CONF_PATH, encoding='utf-8')) if os.path.exists(CONF_PATH) else {}
for _i in CONF.get('inauguraciones', []):
    if not _i.get('has_qa'):
        continue
    # La inauguración es UNA función concreta: hay que casar también la ciudad y
    # la hora. Sin eso, el Q&A de Bogotá se coló en la función de Quibdó, que
    # ese mismo día proyecta la misma película.
    _ciudad = {k: v.get('city') for k, v in venues.items()}
    _hit = [e for e in films_out
            if e['day'] == _i['dia'] and e.get('title') == _i.get('pelicula')
            and _ciudad.get(e['venue']) == _i.get('ciudad')
            and (not _i.get('hora_evento') or e['time'] == _i['hora_evento'])]
    for e in _hit:
        e['has_qa'] = True
        e['_qa_detalle'] = _i.get('qa_detalle', '')
        e['_src']['qa'] = 'confirmaciones-externas (afiche @ficdeh)'
        if _i.get('ingreso') and not (e.get('_ingreso') or '').strip():
            e['_ingreso'] = _i['ingreso']
            e['is_free'] = _i['ingreso'].strip().lower().startswith('entrada libre')
    print(f"  has_qa · {_i['ciudad']} {_i['dia']} «{_i.get('pelicula')}» → {len(_hit)} función(es)")

# Una función no puede tener dos regímenes de entrada: cuando la fuente declara
# el ingreso en una obra del slot y lo deja vacío en la otra (pasa cuando
# escribió la misma sala de dos formas), el dato bueno se propaga al grupo.
_slots = collections.defaultdict(list)
for e in films_out:
    if e.get('day') and e.get('time') and e.get('venue'):
        _slots[(e['day'], e['time'], e['venue'], e.get('sala', ''))].append(e)
for _k, _g in _slots.items():
    if len(_g) < 2:
        continue
    _ing = next((e['_ingreso'] for e in _g if (e.get('_ingreso') or '').strip()), '')
    if not _ing:
        continue
    for e in _g:
        if not (e.get('_ingreso') or '').strip():
            e['_ingreso'] = _ing
            e['is_free'] = _ing.strip().lower().startswith('entrada libre')
            e['requires_registration'] = 'inscrip' in _ing.lower()

out = {
  # El marcador dice en qué punto está el festival, y se actualiza cuando el
  # punto cambia — si no, miente. Este decía «staging, sin publicar: faltan
  # geocoding, sinopsis de actividades, pase de secciones y checklist» con el
  # festival ya en producción, las 114 sedes ubicadas, las 29 actividades con
  # sinopsis y las 12 secciones con inglés y arquetipo. Lo único abierto es el
  # gate humano, que es de Juan y nadie más puede dar por hecho.
  '_etapa': 'PUBLICADA en producción (8 ago 2026). Pendiente solo el gate humano: '
            'la revisión film-por-film en tools/audit.html?fest=ficdeh-2026.',
  '_provenance': {
    'catalogo': 'festivals/staging/ficdeh-2026.json — 94 obras (91 + 3 invitadas)',
    'programacion': 'festivals/staging/ficdeh-2026-programacion-oficial.json — sitio nuevo Next.js, 433 funciones, 424 en_app',
    'alcance': PROG['_provenance'].get('decision_actividades',''),
  },
  # El nombre debe ser IDÉNTICO al de FESTIVAL_CONFIG: el JSON lo pisa en
  # runtime y el guardián [festival-name-parity] exige paridad. La edición
  # («13°») vive en `year`, no en el nombre del selector.
  'name': 'FICDEH', 'shortName': 'FICDEH',
  'fullName': 'Festival Internacional de Cine por los Derechos Humanos',
  # '11 ciudades' NO coincide con la city de ninguna sede → el badge
  # `venue-municipio` (multiciudad, introducido con Cinemancia) se muestra en
  # TODAS las funciones, que es lo que queremos en un festival de 11 ciudades.
  'city': 'Colombia', 'country': 'CO',
  'dates': f'{dnum(dias[0])}–{dnum(dias[-1])} AGO', 'dates_en': f'AUG {dnum(dias[0])}–{dnum(dias[-1])}',
  'year': 2026, 'timezoneOffset': '-05:00', 'storageKey': 'ficdeh2026_',
  'festivalStartStr': f'{dias[0]}T00:00:00', 'festivalEndStr': f'{dias[-1]}T23:59:00',
  'festivalDates': {d: d for d in dias},
  'days': [{'k': d, 'd': dnum(d), 'lbl': LBL[wd(d)]} for d in dias],
  'dayKeys': dias,
  'dayShort':    {d: f'{LBL[wd(d)]} {dnum(d)}'    for d in dias},
  'dayShort_en': {d: f'{LBL_EN[wd(d)]} {dnum(d)}' for d in dias},
  'dayLong':     {d: f'{NOM[wd(d)]} {dnum(d)} de agosto' for d in dias},
  'prioLimit': max(3, min(8, round(len(dias)/2))),
  # Los 52 slots compartidos son UNA función: programas de cortos (hasta 6) o
  # corto+largo. Verificado uno a uno; las sedes son de sala única salvo la
  # Cinemateca, que escalona horarios (nunca dos títulos a la misma hora).
  'sharedSlotIsOneScreening': True,
  # ticketing_model NO va aquí: el validador exige ticket_url en el root si el
  # JSON lo declara, y FICDEH no tiene boletería única (solo la Cinemateca vende
  # online, sede por sede). Vive en FESTIVAL_CONFIG, que es de donde lo leen el
  # badge de gratis (view/helpers.js) y el filtro de funciones gratuitas.
  'sections': sections,
  'venues': venues,
  'films': films_out,
}
json.dump(out, open(f'{REPO}/festivals/staging/ficdeh-2026-build.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)

print(f'fuera de la ventana oficial (12-19 AGO): {len(fuera)} → ' + str(sorted({x["dia"] for x in fuera})))
print(f'funciones ensambladas: {len(films_out)}  (cine {sum(1 for e in films_out if e["type"]=="film")} · actividades {sum(1 for e in films_out if e["type"]=="event")})')
print(f'días: {len(dias)} ({dias[0]} → {dias[-1]})  · prioLimit {out["prioLimit"]}')
print(f'sedes con coordenada: {sum(1 for v in venues.values() if v.get("lat"))}/{len(venues)}')
print(f'sedes: {len(venues)} · ciudades: {len({v["city"] for v in venues.values()})}')
print(f'obras únicas programadas: {len({e["title"] for e in films_out if e["type"]=="film"})}/{len(CAT["films"])}')
if sin_ficha: print('SIN FICHA EN EL CATÁLOGO:', dict(sin_ficha))
print(f'slots compartidos (mismo día+hora+sede): {len(compartidos)}')
for k, v in sorted(compartidos.items())[:12]:
    print(f'   {k[0]} {k[1]} · {k[2][:52]} → {v} obras')
