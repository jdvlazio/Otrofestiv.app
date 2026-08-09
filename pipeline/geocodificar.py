# -*- coding: utf-8 -*-
"""geocodificar.py <fest-id> --centro LAT,LNG [--radio 0.3] — sedes verificadas.

Herramienta genérica sobre el formato intermedio. Trae las DOS lecciones de
geocoding pagadas con bugs:

  · FICDEH v1 aceptaba el primer resultado de Nominatim: 63 de 120 sedes
    apiladas en 10 centroides, reportadas «OK». Aquí un resultado solo entra si
    cae en la caja de la ciudad Y comparte un token distintivo con la sede.
  · FICMA: «Fundadores» (el teatro) aterrizaba en el BARRIO Fundadores. Una
    sede fija nunca es un barrio: los resultados de clase place/boundary/
    landuse se descartan, salvo para las sedes listadas en `_barrios_ok` del
    sidecar (los puntos de un ciclo itinerante sí son barrios y canchas).

Las coordenadas con `_prec:"manual"` son verificación humana y NO SE TOCAN —
correr el geocoder dos veces pisó 40 verificaciones de Juan en FICDEH.

Lee   festivals/staging/<id>-crudo.json
Merge festivals/staging/<id>-venues-geo.json   (se crea si no existe)
"""
import json, os, re, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import cargar_crudo, norm, provenance

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
GENERICAS = {'parque', 'auditorio', 'sala', 'teatro', 'cancha', 'plaza', 'barrio',
             'universidad', 'cine', 'centro', 'cultural', 'casa', 'club', 'colegio',
             'principal', 'campus', 'de', 'la', 'el', 'los', 'las', 'del', 'san'}
UA_NOM = 'Otrofestiv/1.0 (onboarding de festival; github.com/jdvlazio)'
CLASES_LUGAR = {'place', 'boundary', 'landuse'}


def buscar(q):
    import subprocess
    url = ('https://nominatim.openstreetmap.org/search?format=json&limit=5'
           '&countrycodes=co,ar,br&q=' + q.replace(' ', '%20').replace('&', '%26'))
    r = subprocess.run(['curl', '-s', '--max-time', '25', '-A', UA_NOM, url],
                       capture_output=True)
    try:
        return json.loads(r.stdout)
    except Exception:
        return []


def main():
    if len(sys.argv) < 2 or '--centro' not in sys.argv:
        sys.exit('uso: python3 pipeline/geocodificar.py <fest-id> --centro LAT,LNG [--radio 0.3] [--ciudad "Sasaima, Cundinamarca"]')
    fid = sys.argv[1]
    lat0, lng0 = map(float, sys.argv[sys.argv.index('--centro') + 1].split(','))
    radio = float(sys.argv[sys.argv.index('--radio') + 1]) if '--radio' in sys.argv else 0.3
    ciudad = (sys.argv[sys.argv.index('--ciudad') + 1]
              if '--ciudad' in sys.argv else '')

    crudo = cargar_crudo(f'{ST}/{fid}-crudo.json')
    geo_p = f'{ST}/{fid}-venues-geo.json'
    geo = json.load(open(geo_p, encoding='utf-8')) if os.path.exists(geo_p) else {}
    barrios_ok = set(geo.get('_barrios_ok', []))

    sedes = {}
    for f in crudo['funciones']:
        s = f['sede']
        sedes.setdefault(s, {'n': 0, 'ciudad': f.get('ciudad', '')})
        sedes[s]['n'] += 1

    ok = ya = falta = 0
    for i, (s, meta) in enumerate(sorted(sedes.items()), 1):
        prev = geo.get(s, {})
        if prev.get('_prec') == 'manual':
            ya += 1; continue                      # verificación humana: intocable
        if prev.get('lat'):
            ya += 1; continue
        consulta = f'{s}, {meta["ciudad"] or ciudad}'.strip(', ')
        distintivos = set(norm(s).split()) - GENERICAS
        elegido = None
        for r in buscar(consulta):
            la, ln = float(r['lat']), float(r['lon'])
            if abs(la - lat0) > radio or abs(ln - lng0) > radio:
                continue                           # otra ciudad
            if distintivos and not (distintivos & set(norm(r.get('display_name', '')).split())):
                continue                           # nombre que no distingue nada
            if r.get('class') in CLASES_LUGAR and s not in barrios_ok:
                continue                           # una sala fija nunca es un barrio
            elegido = {'lat': round(la, 7), 'lng': round(ln, 7),
                       '_prec': 'nominatim', '_match': r['display_name'][:90]}
            break
        if elegido:
            geo[s] = {**prev, **elegido, 'n': meta['n']}
            ok += 1
            print(f'[{i:2}] OK  {s[:44]:46} {elegido["_match"][:48]}', flush=True)
        else:
            geo[s] = {**prev, 'n': meta['n'], '_prec': 'sin verificar',
                      '_nota': 'buscar a mano (sedes-html.py genera la página)'}
            falta += 1
            print(f'[{i:2}] ??  {s[:44]}', flush=True)
        time.sleep(1.1)                            # cortesía con Nominatim

    geo['_provenance'] = provenance(
        'Nominatim con verificación: caja de ciudad + token distintivo + clase '
        'de lugar (una sede fija nunca es un barrio). _prec:manual intocable.')
    json.dump(geo, open(geo_p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'\n{len(sedes)} sedes · ubicadas ahora {ok} · ya estaban {ya} · a mano {falta}')


if __name__ == '__main__':
    main()
