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
}


def sede_sala(f):
    """→ (sede, sala). La sala explícita de la fuente gana sobre la del nombre."""
    sede, sala = SEDE_SALA.get(f['sede'], (f['sede'], ''))
    return sede, (f.get('sala') or sala or '')


venues = {}
def venue_key(f):
    sede, _ = sede_sala(f)
    key = f'{sede} - {f["ciudad"]}'
    if key not in venues:
        g = GEO.get(key, {})
        venues[key] = {'short': sede, 'lat': g.get('lat'), 'lng': g.get('lng'),
                       'city': f['ciudad'], 'address': f.get('direccion','') or ''}
        if g.get('_geo'): venues[key]['_geo'] = g['_geo']
    return key

# ── secciones de actividades (nombres del festival, regla "tal cual") ────────
# Nombres ES verbatim del festival (regla «secciones tal cual»); emoji y EN son
# nuestra capa, aprobados por Juan el 5 ago 2026.
#   💬 y no 🎤: el micrófono chocaba con el 🎙️ de Cortometraje Documental
#   Nacional — dos micrófonos casi idénticos a tamaño de riel.
#   «Workshops» y no «Training»: son talleres (animación 2D, pintura, actuación,
#   «Taller de Herramientas»), y es el término que busca el público de festival.
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
            e['poster'] = f['poster_url']; e['posterSource'] = 'custom'
        e['_src'] = {**obra.get('_src', {}), **base['_src']}
    else:
        a = ACT.get(f['titulo_programacion'], {})
        e = {'title': f['titulo_programacion'], 'type': 'event',
             'section': SEC_ACT[f['tipo']][0], 'duration': '',
             'synopsis': a.get('synopsis',''), 'synopsis_lang': 'es',
             'poster': a.get('poster',''), 'posterSource': 'custom' if a.get('poster') else '',
             'event_kind': 'ponencia' if f['tipo']=='charla' else 'masterclass'}
        e.update(base)
        if a.get('requires_registration'): e['requires_registration'] = True
        if not e['synopsis']: e['_pendiente'] = 'sin sinopsis en la ficha del festival'
    films_out.append(e)

# ── slots compartidos: mismo día+hora+sede ───────────────────────────────────
slots = collections.Counter((e['day'], e['time'], e['venue']) for e in films_out)
compartidos = {k: v for k, v in slots.items() if v > 1}

# Pósters genéricos de sección: el sitio publica UNA «Portada_Charla» que sirve
# a las 18 charlas por igual. Repetido 18 veces en la grilla es peor que nada —
# para eso está el póster editorial por tipo (eventPosterLabel). Se detecta por
# repetición, no por lista negra, para que el próximo genérico también caiga.
_uso = collections.Counter(e.get('poster') for e in films_out
                           if e.get('type') == 'event' and e.get('poster'))
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
    _hit = [e for e in films_out
            if e['day'] == _i['dia'] and e.get('title') == _i.get('pelicula')]
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
  '_etapa': 'B-ensamblada (staging, sin publicar): faltan geocoding, sinopsis de actividades, pase de secciones nuevas y checklist',
  '_provenance': {
    'catalogo': 'festivals/staging/ficdeh-2026.json — 94 obras (91 + 3 invitadas)',
    'programacion': 'festivals/staging/ficdeh-2026-programacion-oficial.json — sitio nuevo Next.js, 433 funciones, 424 en_app',
    'alcance': PROG['_provenance'].get('decision_actividades',''),
  },
  'name': '13° FICDEH', 'shortName': 'FICDEH',
  'fullName': 'Festival Internacional de Cine por los Derechos Humanos',
  # '11 ciudades' NO coincide con la city de ninguna sede → el badge
  # `venue-municipio` (multiciudad, introducido con Cinemancia) se muestra en
  # TODAS las funciones, que es lo que queremos en un festival de 11 ciudades.
  'city': '11 ciudades', 'country': 'CO',
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
  # sin ticketing_model: exige ticket_url y no hay una URL única — la boletería
  # la vende cada sede (la Cinemateca por tuboleta). is_free por función ya lo dice.
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
