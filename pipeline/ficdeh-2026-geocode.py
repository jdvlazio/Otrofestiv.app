# -*- coding: utf-8 -*-
"""Geocodifica las sedes de FICDEH a un SIDECAR persistente.

Por qué sidecar y no el build: el ensamblador regenera el build desde cero, así
que cualquier coordenada escrita ahí se pierde en la siguiente pasada (pasó el
5 ago: 136 sedes geocodificadas, borradas al re-ensamblar). El sidecar se
acumula y el ensamblador lo mergea.

El script del pipeline (scripts/geocode-venues.py) devuelve 0 resultados contra
Nominatim porque no manda User-Agent — aquí se manda.
"""
import json, time, subprocess, urllib.parse, os
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = f'{REPO}/festivals/staging/ficdeh-2026-build.json'
CACHE = f'{REPO}/festivals/staging/ficdeh-2026-venues-geo.json'
UA = 'Otrofestiv-pipeline/1.0 (contacto@otrofestiv.app)'

geo = json.load(open(CACHE, encoding='utf-8')) if os.path.exists(CACHE) else {}
venues = json.load(open(BUILD, encoding='utf-8'))['venues']

def q(s):
    u = 'https://nominatim.openstreetmap.org/search?format=json&limit=1&countrycodes=co&q=' + urllib.parse.quote(s)
    r = subprocess.run(['curl','-s','--max-time','25','-A',UA,u], capture_output=True)
    try:
        j = json.loads(r.stdout.decode('utf-8','ignore'))
        if j: return {'lat': float(j[0]['lat']), 'lng': float(j[0]['lon']),
                      '_osm': j[0].get('display_name','')[:70]}
    except Exception: pass
    return None

nuevas = exact = aprox = 0
for k, v in venues.items():
    if k in geo: continue
    city, addr = v['city'], (v.get('address') or '').strip()
    r = None
    if addr: r = q(f'{addr}, {city}, Colombia'); time.sleep(1.1)
    if not r: r = q(f"{v['short']}, {city}, Colombia"); time.sleep(1.1)
    if r: exact += 1
    else:
        r = q(f'{city}, Colombia'); time.sleep(1.1)
        if r: r['_geo'] = 'CENTROIDE de ciudad — sede no hallada en OSM, revisar antes de publicar'; aprox += 1
    if r: geo[k] = r; nuevas += 1
    print(f'{len(geo):3}/{len(venues)} {k[:60]:62} {"OK" if r and not r.get("_geo") else ("APROX" if r else "FAIL")}', flush=True)
    if nuevas % 10 == 0: json.dump(geo, open(CACHE,'w',encoding='utf-8'), ensure_ascii=False, indent=1)

json.dump(geo, open(CACHE,'w',encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'\nsidecar: {len(geo)} sedes · nuevas {nuevas} (exactas {exact} · centroide {aprox})')
