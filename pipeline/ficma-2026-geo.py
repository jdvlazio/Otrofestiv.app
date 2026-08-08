# -*- coding: utf-8 -*-
"""Geocodifica las sedes de FICMA — verificando el resultado, no aceptándolo.

La lección de FICDEH: la v1 tomaba el primer resultado de Nominatim y reportó
«120 sedes OK» cuando 63 estaban apiladas en 10 centroides. Un número que no
medía nada. Aquí un resultado solo se acepta si:

  · cae dentro de Manizales (caja geográfica), y
  · su nombre comparte un token DISTINTIVO con el que buscamos — «parque»,
    «auditorio» o «manizales» no distinguen nada y no cuentan.

Lo que no pasa el filtro sale marcado `_prec: 'sin verificar'` para buscarlo a
mano en Google Maps. Preferible un hueco declarado a un punto inventado.
"""
import json, os, re, subprocess, time, unicodedata

S = os.path.dirname(os.path.abspath(__file__))
# Caja de Manizales con margen: fuera de aquí, el resultado es de otra ciudad.
CAJA = (4.95, 5.15, -75.60, -75.40)          # lat_min, lat_max, lng_min, lng_max
GENERICAS = {'parque', 'auditorio', 'sala', 'teatro', 'cancha', 'plaza', 'barrio',
             'universidad', 'cine', 'centro', 'manizales', 'caldas', 'colombia',
             'principal', 'campus', 'de', 'la', 'el', 'los', 'las', 'del'}
UA = 'Otrofestiv/1.0 (onboarding de festival; contacto via github.com/jdvlazio)'


def norm(s):
    s = ''.join(c for c in unicodedata.normalize('NFD', (s or '').lower())
                if unicodedata.category(c) != 'Mn')
    return set(re.sub(r'[^a-z0-9 ]', ' ', s).split())


def buscar(q):
    url = ('https://nominatim.openstreetmap.org/search?format=json&limit=5&countrycodes=co&q='
           + q.replace(' ', '%20').replace('&', '%26'))
    r = subprocess.run(['curl', '-s', '--max-time', '25', '-A', UA, url], capture_output=True)
    try:
        return json.loads(r.stdout)
    except Exception:
        return []


def main():
    sedes = json.load(open(f'{S}/ficma-sedes.json', encoding='utf-8'))
    out = {}
    for i, (clave, s) in enumerate(sorted(sedes.items()), 1):
        consulta = s.get('consulta') or f"{clave}, Manizales, Caldas"
        distintivos = norm(clave) - GENERICAS
        # Qué CLASE de lugar esperamos. Sin esto, «Fundadores» (el teatro)
        # aterrizaba en el barrio Fundadores: mismo nombre, cosa distinta. Los
        # puntos de los ciclos itinerantes sí son barrios, parques y canchas.
        itinerante = bool(s.get('ciclo'))
        CLASES_LUGAR = {'place', 'boundary', 'landuse'}
        elegido = None
        for r in buscar(consulta):
            lat, lng = float(r['lat']), float(r['lon'])
            if not (CAJA[0] <= lat <= CAJA[1] and CAJA[2] <= lng <= CAJA[3]):
                continue
            if distintivos and not (distintivos & norm(r.get('display_name', ''))):
                continue
            # Una sala fija NUNCA es un barrio: «Fundadores» (el teatro) caía en
            # el barrio Fundadores. Los puntos de los ciclos, en cambio, valen de
            # las dos formas — «Cine al barrio - Samaria» es un barrio y «Cine al
            # aire libre - Rogelio Salmona» es un centro cultural.
            if not itinerante and r.get('class') in CLASES_LUGAR:
                continue
            elegido = {'lat': round(lat, 7), 'lng': round(lng, 7),
                       '_prec': 'nominatim', '_match': r['display_name'][:90]}
            break
        out[clave] = {**s, **(elegido or {'_prec': 'sin verificar',
                                          '_nota': 'buscar a mano en Google Maps'})}
        print(f"[{i:2}/{len(sedes)}] {'OK  ' if elegido else '??  '}{clave[:44]:46}"
              f"{elegido['_match'][:52] if elegido else ''}", flush=True)
        time.sleep(1.1)          # cortesía con Nominatim

    json.dump(out, open(f'{S}/ficma-venues-geo.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    n = sum(1 for v in out.values() if v['_prec'] == 'nominatim')
    print(f'\n{len(out)} sedes · ubicadas {n} · sin verificar {len(out) - n}')


if __name__ == '__main__':
    main()
