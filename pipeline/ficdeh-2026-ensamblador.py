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
funcs = [f for f in PROG['funciones'] if f.get('en_app')]
dias  = sorted({f['dia'] for f in funcs})

LBL    = ['LUN','MAR','MIÉ','JUE','VIE','SÁB','DOM']
LBL_EN = ['MON','TUE','WED','THU','FRI','SAT','SUN']
NOM    = ['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo']
def wd(k): return datetime.date.fromisoformat(k).weekday()
def dnum(k): return int(k[-2:])

# ── venues: clave "Sede - Ciudad" ────────────────────────────────────────────
venues = {}
def venue_key(f):
    key = f"{f['sede']} - {f['ciudad']}"
    if key not in venues:
        venues[key] = {'short': f['sede'], 'lat': None, 'lng': None,
                       'city': f['ciudad'], 'address': f.get('direccion','') or ''}
    return key

# ── secciones de actividades (nombres del festival, regla "tal cual") ────────
SEC_ACT = {
  'charla': ('🎤 Charlas que Unen', 'Talks That Unite', 'Charlas / Industria', 11),
  'taller': ('🛠️ Formación',        'Training',          'Charlas / Industria', 12),
}

sections = dict(CAT.get('sections') or {})
for k,(nombre,en,arch,order) in SEC_ACT.items():
    if nombre not in sections:
        sections[nombre] = {'oficial': nombre.split(' ',1)[1], 'en': en,
                            'archetype': arch, 'color': '#639922', 'order': order,
                            '_pendiente_aprobacion': 'emoji y traducción propuestos, sin aprobar'}

# ── ensamblado ───────────────────────────────────────────────────────────────
films_out, sin_ficha = [], collections.Counter()
for f in sorted(funcs, key=lambda x: (x['dia'], x['hora'], x['ciudad'])):
    base = {'day': f['dia'], 'time': f['hora'], 'venue': venue_key(f),
            'day_order': dias.index(f['dia']),
            'has_qa': False, 'is_cortos': False, 'film_list': None,
            'is_free': True, 'requires_registration': False,
            '_src': {'programacion_oficial': f['titulo_programacion']}}
    if f['tipo'] in ('film','film_invitada'):
        obra = by_title.get(f['obra_catalogo']) if f['obra_catalogo'] else by_title.get(f['titulo_programacion'])
        if not obra:
            sin_ficha[f['titulo_programacion']] += 1
            continue
        e = {k: v for k, v in obra.items() if not k.startswith('_')}
        e.update(base); e['type'] = 'film'
        e['_src'] = {**obra.get('_src', {}), **base['_src']}
    else:
        e = {'title': f['titulo_programacion'], 'type': 'event',
             'section': SEC_ACT[f['tipo']][0], 'duration': '',
             'synopsis': '', 'synopsis_lang': 'es',
             'event_kind': 'ponencia' if f['tipo']=='charla' else 'masterclass'}
        e.update(base)
        e['_pendiente'] = 'sinopsis y duración — recuperar de /charlas/<slug> o /talleres/<slug>'
    films_out.append(e)

# ── slots compartidos: mismo día+hora+sede ───────────────────────────────────
slots = collections.Counter((e['day'], e['time'], e['venue']) for e in films_out)
compartidos = {k: v for k, v in slots.items() if v > 1}

out = {
  '_etapa': 'B-ensamblada (staging, sin publicar): faltan geocoding, sinopsis de actividades, pase de secciones nuevas y checklist',
  '_provenance': {
    'catalogo': 'festivals/staging/ficdeh-2026.json — 94 obras (91 + 3 invitadas)',
    'programacion': 'festivals/staging/ficdeh-2026-programacion-oficial.json — sitio nuevo Next.js, 433 funciones, 424 en_app',
    'alcance': PROG['_provenance'].get('decision_actividades',''),
  },
  'name': '13° FICDEH', 'shortName': 'FICDEH',
  'fullName': 'Festival Internacional de Cine por los Derechos Humanos',
  'city': 'Bogotá y 10 ciudades', 'country': 'CO',
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
  'ticketing_model': 'mixed',
  'sections': sections,
  'venues': venues,
  'films': films_out,
}
json.dump(out, open(f'{REPO}/festivals/staging/ficdeh-2026-build.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)

print(f'funciones ensambladas: {len(films_out)}  (cine {sum(1 for e in films_out if e["type"]=="film")} · actividades {sum(1 for e in films_out if e["type"]=="event")})')
print(f'días: {len(dias)} ({dias[0]} → {dias[-1]})  · prioLimit {out["prioLimit"]}')
print(f'sedes: {len(venues)} · ciudades: {len({v["city"] for v in venues.values()})}')
print(f'obras únicas programadas: {len({e["title"] for e in films_out if e["type"]=="film"})}/{len(CAT["films"])}')
if sin_ficha: print('SIN FICHA EN EL CATÁLOGO:', dict(sin_ficha))
print(f'slots compartidos (mismo día+hora+sede): {len(compartidos)}')
for k, v in sorted(compartidos.items())[:12]:
    print(f'   {k[0]} {k[1]} · {k[2][:52]} → {v} obras')
