# -*- coding: utf-8 -*-
"""Auditoría independiente: el JSON publicado contra las DOS fuentes oficiales.
No re-usa el código que construyó el JSON — lo compara contra el PDF y la hoja."""
import json,re,unicodedata,collections,sys
def n(s):
    s=unicodedata.normalize('NFD',s or '').encode('ascii','ignore').decode().lower()
    return re.sub(r'[^a-z0-9]','',s)
J=json.load(open('festivals/cinemancia-2026.json'))
PAR=json.load(open('festivals/staging/cinemancia-2026-programacion-oficial.json'))['funciones']
HOJA=json.load(open('festivals/staging/cinemancia-2026-programas-oficial.json'))
fallos=[]
def check(nombre, ok, detalle=''):
    print(f"  {'✓' if ok else '✗'} {nombre}" + (f' — {detalle}' if detalle else ''))
    if not ok: fallos.append(nombre)

print('═══ 1 · CADA FUNCIÓN DE LA PARRILLA ESTÁ EN EL JSON ═══')
pub={(f['day'],f['time'][:5],n(f.get('venue'))) for f in J['films']}
falt=[p for p in PAR if not any(d==p['dia'] and h==p['hora'] and (n(p['sede'])[:14] in v or v[:14] in n(p['sede'])) for d,h,v in pub)]
check('las 86 funciones de la parrilla están publicadas', not falt, f'faltan {len(falt)}: {[(f["dia"],f["hora"]) for f in falt][:4]}')
check('el JSON no inventa funciones', len(J['films'])==len(PAR), f'{len(J["films"])} publicadas vs {len(PAR)} en la parrilla')

print('\n═══ 2 · DÍA, HORA Y SEDE COINCIDEN UNO A UNO ═══')
mal=[]
for p in PAR:
    m=[f for f in J['films'] if f['day']==p['dia'] and f['time'][:5]==p['hora'] and (n(p['sede'])[:14] in n(f.get('venue')) or n(f.get('venue'))[:14] in n(p['sede']))]
    if len(m)!=1: mal.append((p['dia'],p['hora'],p['sede'][:24],len(m)))
check('cada función de la parrilla casa con exactamente UNA publicada', not mal, f'{len(mal)} anomalías: {mal[:3]}')

print('\n═══ 3 · LOS PROGRAMAS LLEVAN LAS OBRAS QUE DIJO EL FESTIVAL ═══')
for p in HOJA['programas']:
    esperadas=[o['titulo'] for o in p['obras']]
    for x in p['pases']:
        m=[f for f in J['films'] if f['day']==x['dia'] and f['time'][:5]==x['hora']
           and (n(x['sede'])[:14] in n(f.get('venue')) or n(f.get('venue'))[:14] in n(x['sede']))]
        if not m: check(f'{p["programa"][:30]} {x["dia"]} {x["hora"]}', False, 'función no encontrada'); continue
        got=[o['title'] for o in (m[0].get('film_list') or [])]
        ok = [n(t) for t in got]==[n(t) for t in esperadas]
        check(f'{p["programa"][:34]} · {x["dia"]} {x["hora"]}', ok,
              '' if ok else f'esperadas {len(esperadas)} / publicadas {len(got)}')

print('\n═══ 4 · NINGUNA OBRA APARECE DOS VECES EN LA MISMA FUNCIÓN ═══')
dup=[(f['title'],t) for f in J['films'] for t,c in collections.Counter(n(o['title']) for o in (f.get('film_list') or [])).items() if c>1]
check('sin obras repetidas dentro de una función', not dup, str(dup[:3]))

print('\n═══ 5 · ACCESO SEGÚN LA NOTA OFICIAL ═══')
PAGAS=('cineprox','cinemamm')
malacc=[]
for f in J['films']:
    v=n(f.get('venue'))
    paga=any(x in v for x in PAGAS)
    if paga and f.get('is_free'): malacc.append((f['title'][:24],f.get('venue')[:22],'marcada gratis y cobra'))
    if not paga and not f.get('is_free') and not f.get('requires_registration'): malacc.append((f['title'][:24],f.get('venue')[:22],'ni gratis ni inscripción'))
check('Cineprox y MAMM no figuran como gratis', not malacc, f'{len(malacc)}: {malacc[:3]}')

print('\n═══ 6 · SEDES Y COORDENADAS ═══')
ven=J.get('venues') or {}
sin=[k for k,v in ven.items() if not v.get('lat')]
check('toda sede publicada tiene dirección', all(v.get('address') for v in ven.values()), f'sin address: {[k for k,v in ven.items() if not v.get("address")]}')
check('toda sede tiene coordenadas', not sin, f'sin lat/lng: {sin}')

print('\n═══ 7 · FECHAS DENTRO DE LA VENTANA DEL FESTIVAL ═══')
dias=sorted({f['day'] for f in J['films']})
check('todas las funciones caen entre el 3 y el 12 de septiembre',
      dias[0]=='2026-09-03' and dias[-1]=='2026-09-12', f'{dias[0]} … {dias[-1]} ({len(dias)} días)')

print('\n═══ 8 · SINOPSIS ═══')
# Una FUNCIÓN que agrupa obras no tiene sinopsis propia: la tienen sus obras.
obras=[o for f in J['films'] for o in ([f] if not f.get('film_list') else []) + list(f.get('film_list') or []) if o.get('title')]
sin_s={o['title'] for o in obras if not o.get('synopsis')}
ACT=('Foro de la','Seminario','Debate','Conversaciones','Encuentro','Programa','Foco','Retrospectiva','Competencia','Fuera de competencia','Alquimia de la luz','Itinerarios de una tradici')
obras_sin=[t for t in sin_s if not any(a in t for a in ACT)]
check('toda OBRA tiene sinopsis (los programas y actividades no cuentan)', not obras_sin, str(sorted(obras_sin)[:5]))

print('\n' + '═'*54)
print(f'  {"TODO EN VERDE" if not fallos else str(len(fallos))+" COMPROBACIONES FALLAN"}')
print('═'*54)
sys.exit(1 if fallos else 0)
