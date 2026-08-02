# -*- coding: utf-8 -*-
"""Ensamblador Etapa B QAFF 2026: cruza el sidecar de programación (65 eventos Boom)
con las 54 obras de Etapa A. Decisiones de Juan (2 ago): sección dueña = PRIMERA
categoría del evento; SIN prelanzamiento del 5 sep (ventana 14–20); doble ciudad
Quibdó/Bogotá con city en venues."""
import json, re, html, unicodedata, collections

REPO='/Users/Juanda/Documents/Otrofestiv-dev'
staging=json.load(open(f'{REPO}/festivals/staging/qaff-2026.json'))
side=json.load(open(f'{REPO}/festivals/staging/qaff-2026-programacion-raw.json'))

def norm(s):
    s=unicodedata.normalize('NFD',(s or '').lower()); s=''.join(c for c in s if unicodedata.category(c)!='Mn')
    return re.sub(r'[^a-z0-9]+',' ',s).strip()

def strip_html(t):
    t=re.sub(r'</p>|<br[^>]*>','\n',t or '')
    t=re.sub(r'<[^>]+>','',t)
    return html.unescape(t)

def parse_desc(desc):
    """desc → (director_line, ficha {year,country,dur}, sinopsis)"""
    lines=[re.sub(r'\s+',' ',l).strip() for l in strip_html(desc).split('\n')]
    lines=[l for l in lines if l]
    year=None; syn=[]
    for l in lines:
        m=re.search(r'/\s*((?:19|20)\d{2})\s*/', l)
        if m and not year: year=m.group(1); continue
        if es_linea_credito(l): continue
        # línea tipo "Martinique / 2022 / 10'13 Experimental"
        if re.match(r"^[A-ZÀ-Ü][\w ,.'-]+/\s*(19|20)\d{2}", l): continue
        syn.append(l)
    return year, ' '.join(syn).strip()

# La fuente pega créditos y sinopsis en la MISMA línea en algunos eventos (sin
# separador parseable). Corte quirúrgico por marcador; el chequeo residual del
# final caza casos nuevos en re-ensamblados.
def es_linea_credito(l):
    """Línea "Etiqueta: Nombre, Nombre" pura (solo nombres tras la etiqueta) → crew."""
    m=re.match(r'^([A-Z][\w /&-]{2,40}):\s*(.*)$', l)
    if not m: return False
    toks=[t for t in re.split(r'[\s,&]+', m.group(2)) if t]
    if not toks: return True
    PART={'de','De','La','la','del','Del','van','Van','Da','da','dos','Los'}
    return len(toks)<=10 and all(t[0].isupper() or t in PART for t in toks)

# Créditos PEGADOS a la sinopsis en la misma línea (sin separador): corte
# explícito por marcador de arranque de la frase. El chequeo residual del final
# caza casos nuevos en futuros re-ensamblados.
CORTE_SINOPSIS={
 "GOD'S WORK":'In a derelict',
 'THE MADMEN COACH':'In Dakar,',
 'LEER EN LAS GOTAS DE LLUVIA':'An Angolan artist',
 'SISTERS IN DESTINY:VANGELA DAVIS & GERTY ARCHIMEDE':'Two women.',
 'SURVIVING BIAFRA':'Surviving Biafra is',
 'THE CLAY VASE':'Where do we keep',
 'ALTANEGRA':'In a territory',
 'VIVA YURUMANGUI':'On the remote Pacific',
 'CAPTAIN ANTHONY':'In 1942,',
 'CAIDA LIBRE':'In a desperate attempt',
 'HACKER LEONILIA':'In the future,',
 'THE BLACK BART OF TACO KING #17':'A suave criminal',
 'MI VICHE TODO EL DIA':'In the Medio Atrato',
}
def aplicar_corte(title, syn):
    t=title.upper().strip().replace('\u2019',"'")
    m=CORTE_SINOPSIS.get(t)
    if m and m in syn:
        return syn[syn.index(m):]
    return syn

def detect_lang(t):
    es=len(re.findall(r'\b(el|la|los|las|una|con|para|donde|entre|sobre|que|del)\b', t.lower()))
    en=len(re.findall(r'\b(the|and|with|for|where|between|about|that|his|her)\b', t.lower()))
    return 'es' if es>=en else 'en'

# ── ventana y días ────────────────────────────────────────────────────────────
DAYS=[f'2026-09-{d}' for d in range(14,21)]
LBL={0:'LUN',1:'MAR',2:'MIÉ',3:'JUE',4:'VIE',5:'SÁB',6:'DOM'}
LBL_EN={0:'MON',1:'TUE',2:'WED',3:'THU',4:'FRI',5:'SAT',6:'SUN'}
import datetime
def wd(k): return datetime.date.fromisoformat(k).weekday()
MES_L='septiembre'

events=[e for e in side['events'] if e['start'][:10] in DAYS]
descartados=[e for e in side['events'] if e['start'][:10] not in DAYS]

# ── venues ────────────────────────────────────────────────────────────────────
CITY={'Biblioteca Pública Departamental Arnoldo de los Santos Palacios Mosquera':'Quibdó',
      'Cinemateca de Bogotá':'Bogotá',
      'Museo Nacional de Colombia - Auditorio':'Bogotá'}
VSHORT={'Biblioteca Pública Departamental Arnoldo de los Santos Palacios Mosquera':'Biblioteca Departamental',
        'Cinemateca de Bogotá':'Cinemateca de Bogotá',
        'Museo Nacional de Colombia - Auditorio':'Museo Nacional'}
venues={}
def venue_key(v):
    name=(v or {}).get('name','').strip()
    city=None
    for k,c in CITY.items():
        if norm(k)==norm(name) or norm(name) in norm(k) or norm(k) in norm(name): name, city = k, c; break
    if city is None: city='Quibdó'  # default; revisar
    key=f'{VSHORT.get(name,name)} - {city}'
    if key not in venues:
        venues[key]={'short':key,'lat':None,'lng':None,'city':city,
                     'address':(v or {}).get('address','') or '', '_contact':{k2:(v or {}).get(k2,'') for k2 in ('email','phone','website')}}
    return key

# ── índice de obras Etapa A ───────────────────────────────────────────────────
by_norm={norm(f['title']):f for f in staging['films']}
alias={}
for f in staging['films']:
    if f.get('title_orig'): alias[norm(f['title_orig'])]=f

ALIAS_EV={  # título del calendario → título de Etapa A (typos y traducciones de la fuente)
 'CAIDA LIBRE':'Free Fall',
 'POSESAS':'POSESAS [Possessed]',
 'FACE TO FACE -LIVE PERFORMANCE':'FACE TO FACE',
 'RELATOS DE LA GUAJIRITA':'Stories from La Guajirita',
 'THE ANCHORAGE OF TIME':'THE ANCHORAGE OF THE TIME',
 'AMAZONA COCINAS INDIGENAS DE SELVA Y RIO':'Amazonas Cocinas Indigenas de Selva y Rio',
 'SONE SU NOMRE':'Soñé su nombre',
 'SISTERS IN DESTINY:VANGELA DAVIS & GERTY ARCHIMEDE':'Sisters in Destiny: Angela Davis & Gerty Archimede',
 'LAUNDRY':'LAUNDRY (Uhlanjululo)',
}
ALIAS_N={norm(k):norm(v) for k,v in ALIAS_EV.items()}

def find_film(title):
    n=norm(title)
    n=ALIAS_N.get(n,n)
    if n in by_norm: return by_norm[n]
    if n in alias: return alias[n]
    # fuzzy: contains
    for k,f in by_norm.items():
        if (n in k or k in n) and abs(len(n)-len(k))<=6: return f
    return None

# ── secciones desde categorías ────────────────────────────────────────────────
ARCH={'PANORAMA AFRICANO':'Muestra / País','PANORAMA COLOMBIANO':'Muestra / País',
 'PANORAMA DIASPORICA':'Muestra / País','FRONTERAS LATAM':'Muestra / País',
 'IMAGINARIOS AFRODISRUPTIVO':'Perspectivas / Miradas','OTRA MIRADA':'Perspectivas / Miradas',
 'NUEVAS VOCES':'Perspectivas / Miradas','PRISMA FEMININO':'Perspectivas / Miradas',
 'ESCUELAS DE CINE':'Charlas / Industria','FUERA DE COMPETICION':'Especiales / Eventos',
 'LANZAMIENTO QAFF':'Apertura / Gala','DIALOGO IMPROBABLE':'Charlas / Industria',
 'MASTER CLASS':'Charlas / Industria','NETWORKING':'Charlas / Industria',
 'MUESTRA ARTÍSTICA':'Especiales / Eventos'}
TITULO={'PANORAMA AFRICANO':'Panorama Africano','PANORAMA COLOMBIANO':'Panorama Colombiano',
 'PANORAMA DIASPORICA':'Panorama Diaspórica','FRONTERAS LATAM':'Fronteras Latam',
 'IMAGINARIOS AFRODISRUPTIVO':'Imaginarios Afrodisruptivos','OTRA MIRADA':'Otra Mirada',
 'NUEVAS VOCES':'Nuevas Voces','PRISMA FEMININO':'Prisma Femenino',
 'ESCUELAS DE CINE':'Escuelas de Cine','FUERA DE COMPETICION':'Miradas Especiales',
 'LANZAMIENTO QAFF':'Lanzamiento','DIALOGO IMPROBABLE':'Diálogo Improbable',
 'MASTER CLASS':'Master Class','NETWORKING':'Networking','MUESTRA ARTÍSTICA':'Muestra Artística'}
secciones_usadas={}
ACT_CATS={'LANZAMIENTO QAFF','DIALOGO IMPROBABLE','MASTER CLASS','NETWORKING','MUESTRA ARTÍSTICA'}
def section_of(ev):
    cats=ev.get('categories') or []
    if not cats: return None
    # una categoría de actividad manda sobre las secciones de película
    c=next((x for x in cats if x['name'] in ACT_CATS), cats[0])
    if 'MUESTRA ART' in ev['title'].upper():
        c={'name':'MUESTRA ARTÍSTICA','color':'#467808','order_index':90}
    name=TITULO.get(c['name'], c['name'].title())
    if name not in secciones_usadas:
        secciones_usadas[name]={'oficial':name,'en':'','archetype':ARCH.get(c['name'],''),
                                'color':c['color'],'order':c.get('order_index',99),
                                '_todas_las_obras_multi':True}
    return name

# ── ensamblar funciones ───────────────────────────────────────────────────────
out_films=[]; sin_match=[]; enriquecidas=0
ACTIVIDAD=re.compile(r'master ?class|networking|dialogo|diálogo|lanzamiento|apertura|clausura|muestra art|ceremonia|conversatorio|taller|panel', re.I)
for ev in sorted(events, key=lambda e:e['start']):
    day=ev['start'][:10]; time=ev['start'][11:16]
    dur_min=None
    try:
        t0=datetime.datetime.fromisoformat(ev['start']); t1=datetime.datetime.fromisoformat(ev['end'])
        dur_min=int((t1-t0).total_seconds()//60)
    except: pass
    vk=venue_key(ev.get('venue'))
    sec=section_of(ev)
    film=find_film(ev['title'])
    imgs=[]
    try: imgs=json.loads(ev.get('image') or '[]')
    except: pass
    year_desc, syn_desc = parse_desc(ev.get('desc',''))
    syn_desc=aplicar_corte(ev['title'], syn_desc)
    base={'day':day,'time':time,'venue':vk,'day_order':DAYS.index(day),
          'has_qa':False,'is_cortos':False,'film_list':None,
          'requires_registration':True,'is_free':True,
          '_src':{'boom_event_id':ev['id'],'stills':imgs[:3]}}
    if film is not None:
        entry=dict(film)  # copia de la ficha de Etapa A
        entry.pop('_out_of_competition', None)
        entry.update(base)
        entry['type']='film'
        if sec: entry['section']=sec
        # enriquecer ficha madre (año/sinopsis) si faltaba
        marks=film.get('_inherited',{})
        if year_desc and not film.get('year'):
            film['year']=year_desc; entry['year']=year_desc; marks['year']='qaff-event-desc';
        if syn_desc and not film.get('synopsis'):
            lang=detect_lang(syn_desc)
            film['synopsis']=syn_desc; film['synopsis_lang']=lang
            entry['synopsis']=syn_desc; entry['synopsis_lang']=lang
            marks['synopsis']='qaff-event-desc'
        if marks: film['_inherited']=marks; entry['_inherited']=marks
        film['_programada']=True
        out_films.append(entry)
    else:
        kind='event' if ACTIVIDAD.search(ev['title']) or (sec and secciones_usadas[sec]['archetype'] in ('Charlas / Industria','Especiales / Eventos','Apertura / Gala')) else 'film'
        entry={'title':ev['title'].strip(),'type':kind,
               'duration':f'{dur_min} min' if dur_min else '',
               'synopsis':syn_desc,'synopsis_lang':detect_lang(syn_desc) if syn_desc else 'es',
               'section':sec or '','year':year_desc or ''}
        entry.update(base)
        if kind=='event': entry['event_kind']=''
        out_films.append(entry)
        sin_match.append((ev['title'], kind, day, time))

# obras de Etapa A sin función
sin_funcion=[f['title'] for f in staging['films'] if not f.get('_programada')]
for f in staging['films']: f.pop('_programada', None)

# ── chequeo de slots compartidos (mismo día+hora+sede) ────────────────────────
slots=collections.Counter((e['day'],e['time'],e['venue']) for e in out_films)
compartidos=[k for k,c in slots.items() if c>1]

# ── armar JSON final de staging ───────────────────────────────────────────────
final={
 '_etapa':'B-ensamblada (staged, sin publicar — falta pase de secciones/emoji, geocoding y verificación humana)',
 '_provenance':{
   'fuente':'Etapa A (selection-2026) + programación Boom published_calendar (sidecar qaff-2026-programacion-raw.json), 2 ago 2026',
   'verificacion':'Cruce título-normalizado eventos↔obras; sección dueña = 1ª categoría del evento (decisión Juan 2 ago); sin prelanzamiento 5 sep (decisión Juan); doble ciudad con city en venues (decisión Juan)',
   'decisiones_pendientes':'emojis/EN de secciones; 19-20 sep incluidos (funciones de cierre reales); geocoding; verificar URL de Registrarse por evento',
 },
 'name':'QAFF 2026','shortName':'QAFF','city':'Quibdó y Bogotá','country':'CO',
 'dates':'14–20 SEP','dates_en':'SEP 14–20','year':2026,'timezoneOffset':'-05:00',
 'storageKey':'qaff2026_',
 'festivalStartStr':'2026-09-14T00:00:00','festivalEndStr':'2026-09-20T23:59:00',
 'festivalDates':{k:k for k in DAYS},
 'days':[{'k':k,'d':int(k[-2:]),'lbl':LBL[wd(k)]} for k in DAYS],
 'dayKeys':DAYS,
 'dayShort':{k:f'{LBL[wd(k)]} {int(k[-2:])}' for k in DAYS},
 'dayShort_en':{k:f'{LBL_EN[wd(k)]} {int(k[-2:])}' for k in DAYS},
 'dayLong':{k:f"{['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo'][wd(k)]} {int(k[-2:])} de {MES_L}" for k in DAYS},
 'prioLimit':4,
 'sharedSlotIsOneScreening':False,
 'sections':secciones_usadas,
 'venues':venues,
 'films':out_films,
 '_obras_sin_funcion':sin_funcion,
}
json.dump(final, open(f'{REPO}/festivals/staging/qaff-2026.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)

print(f'funciones: {len(out_films)} ({sum(1 for f in out_films if f.get("type")=="film")} film / {sum(1 for f in out_films if f.get("type")=="event")} event)')
print(f'eventos descartados (fuera de ventana): {[(e["start"][:10],e["title"][:40]) for e in descartados]}')
print(f'enriquecidas con año/sinopsis del desc: ver marcas')
print(f'sin match con Etapa A ({len(sin_match)}):')
for t,k,d,h in sin_match: print(f'  [{k}] {d} {h} · {t[:60]}')
print(f'obras de Etapa A SIN función ({len(sin_funcion)}): {sin_funcion}')
print(f'slots compartidos: {compartidos if compartidos else "ninguno"}')
print('venues:', list(venues))
print('secciones usadas:', list(secciones_usadas))
