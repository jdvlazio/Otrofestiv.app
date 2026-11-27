# -*- coding: utf-8 -*-
"""gmaps.py — Google Maps, la única fuente de pines del pipeline (27 nov 2026).

Por qué Google y no Nominatim/Photon: medido el 27 nov sobre 20 lugares ya
verificados en Maps, Nominatim falló en 15 de 18 (Teatro Colón a 11 km, Museo
Nacional a 4,5 km) y los pines malos de FICDEH venían justo de ahí. En
Colombia, el mapa que conoce las direcciones es Google. Decisión de Juan.

CLAVE: `GOOGLE_MAPS_API_KEY` en el entorno (proyecto `otrofestiv-maps`,
restringida a Places API (New) y Geocoding API, tope de 300 consultas/día por
API). Sin clave, todo se detiene con un mensaje claro: NUNCA se adivina un pin.

CONDICIONES DE GOOGLE (Service Specific Terms, revisadas el 27 nov 2026): las
coordenadas que da la API se guardan como mucho 30 días; el `place_id` se puede
guardar para siempre. Por eso cada lugar guarda su `place_id` y la fecha de sus
coordenadas, y `sedes.py --refrescar` las vuelve a pedir antes de que venzan.

Cuatro preguntas, un solo dueño:
    buscar_lugar(nombre, ciudad, centro, radio_m) → candidatos de Places
    detalle(place_id)                             → el lugar por su id
    geocodificar(direccion, ciudad)               → la dirección, con su precisión
    ciudad_de(lat, lng)                           → el municipio de un punto

`_http` es inyectable: las pruebas corren con respuestas grabadas, sin red.
"""
import json, os, re, sys, unicodedata, urllib.parse, urllib.request

PLACES = 'https://places.googleapis.com/v1'
GEOCODE = 'https://maps.googleapis.com/maps/api/geocode/json'
CAMPOS = 'places.id,places.displayName,places.formattedAddress,places.location,places.types,places.googleMapsUri'
# lo que no es una sede fija: una ciudad, un barrio, una región
NO_ES_SEDE = {'locality', 'sublocality', 'sublocality_level_1', 'neighborhood', 'political',
              'administrative_area_level_1', 'administrative_area_level_2', 'country', 'route'}
# precisión de Geocoding que basta para ubicar una puerta
PRECISA = {'ROOFTOP', 'RANGE_INTERPOLATED'}
GENERICAS = {'parque', 'auditorio', 'sala', 'teatro', 'cancha', 'plaza', 'barrio', 'universidad',
             'cine', 'centro', 'cultural', 'casa', 'club', 'colegio', 'principal', 'campus', 'de', 'la',
             'el', 'los', 'las', 'del', 'san', 'y', 'biblioteca', 'publica', 'museo', 'sede'}


class SinClave(SystemExit):
    pass


def clave():
    k = os.environ.get('GOOGLE_MAPS_API_KEY', '').strip()
    if not k:
        raise SinClave('✗ falta GOOGLE_MAPS_API_KEY en el entorno (ver pipeline/gmaps.py). '
                       'Sin Google no se ubica ninguna sede: nada se adivina.')
    return k


def _http(url, body=None, headers=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None,
                                 headers={'Content-Type': 'application/json', **(headers or {})})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)


def _plano(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    return ' '.join(re.sub(r'[^a-z0-9 ]', ' ', ''.join(c for c in s if unicodedata.category(c) != 'Mn')).split())


def distintivas(nombre):
    """Las palabras del nombre que distinguen el lugar («Tertulia», no «Museo»)."""
    return set(_plano(nombre).split()) - GENERICAS


def metros(a, b):
    import math
    dy = (a[0] - b[0]) * 111320
    dx = (a[1] - b[1]) * 111320 * math.cos(math.radians(a[0]))
    return math.hypot(dx, dy)


def _lugar(p):
    loc = p.get('location') or {}
    return {'place_id': p.get('id'), 'nombre': (p.get('displayName') or {}).get('text', ''),
            'direccion': p.get('formattedAddress', ''), 'lat': loc.get('latitude'),
            'lng': loc.get('longitude'), 'tipos': p.get('types') or [], 'url': p.get('googleMapsUri', '')}


def buscar_lugar(nombre, ciudad='', centro=None, radio_m=30000, http=None):
    """Places Text Search, sesgado a la ciudad del festival. → [lugar…]"""
    body = {'textQuery': ', '.join(x for x in (nombre, ciudad) if x), 'languageCode': 'es',
            'regionCode': 'CO', 'pageSize': 5}
    if centro:
        body['locationBias'] = {'circle': {'center': {'latitude': centro[0], 'longitude': centro[1]},
                                           'radius': min(float(radio_m), 50000.0)}}
    r = (http or _http)(f'{PLACES}/places:searchText', body,
                        {'X-Goog-Api-Key': clave(), 'X-Goog-FieldMask': CAMPOS})
    return [_lugar(p) for p in r.get('places') or []]


def detalle(place_id, http=None):
    """El lugar por su id: lo que usa el refresco de coordenadas (30 días)."""
    r = (http or _http)(f'{PLACES}/places/{urllib.parse.quote(place_id)}', None,
                        {'X-Goog-Api-Key': clave(),
                         'X-Goog-FieldMask': 'id,displayName,formattedAddress,location,types,googleMapsUri'})
    return _lugar(r)


def geocodificar(direccion, ciudad='', http=None):
    """La dirección → {lat, lng, precisa, parcial, direccion} o None."""
    q = urllib.parse.urlencode({'address': ', '.join(x for x in (direccion, ciudad) if x),
                                'components': 'country:CO', 'language': 'es', 'key': clave()})
    r = (http or _http)(f'{GEOCODE}?{q}')
    if r.get('status') != 'OK' or not r.get('results'):
        return None
    x = r['results'][0]
    g = x['geometry']
    return {'lat': g['location']['lat'], 'lng': g['location']['lng'],
            'precisa': g.get('location_type') in PRECISA and not x.get('partial_match'),
            'direccion': x.get('formatted_address', ''), 'place_id': x.get('place_id')}


def ciudad_de(lat, lng, http=None):
    """El municipio de un punto (Geocoding inverso)."""
    q = urllib.parse.urlencode({'latlng': f'{lat},{lng}', 'language': 'es',
                                'result_type': 'locality|administrative_area_level_2', 'key': clave()})
    r = (http or _http)(f'{GEOCODE}?{q}')
    for x in r.get('results') or []:
        for c in x.get('address_components') or []:
            if {'locality', 'administrative_area_level_2'} & set(c.get('types') or []):
                return c.get('long_name')
    return None


def elegir(nombre, candidatos, centro=None, radio_m=30000, barrio_ok=False, direccion=None):
    """La regla fija para aceptar un pin SIN persona (aprobada por Juan, 27 nov):
      · el nombre en Google comparte una palabra distintiva con el nuestro;
      · cae dentro del radio de la ciudad;
      · una sede fija nunca es una ciudad, un barrio ni una calle;
      · si el festival publicó dirección y Google la ubica con precisión, el
        lugar queda a <150 m de ella.
    → (lugar, motivo) o (None, por qué no)."""
    dist = distintivas(nombre)
    motivos = []
    for c in candidatos:
        if c['lat'] is None:
            continue
        if centro and metros(centro, (c['lat'], c['lng'])) > radio_m:
            motivos.append(f'«{c["nombre"]}» fuera de la ciudad'); continue
        if dist and not dist & distintivas(c['nombre']):
            motivos.append(f'«{c["nombre"]}» no comparte nombre'); continue
        if not barrio_ok and set(c['tipos']) <= NO_ES_SEDE | {'point_of_interest', 'establishment'} \
                and set(c['tipos']) & NO_ES_SEDE:
            motivos.append(f'«{c["nombre"]}» es un barrio o una ciudad'); continue
        if direccion and direccion.get('precisa'):
            d = metros((direccion['lat'], direccion['lng']), (c['lat'], c['lng']))
            if d > 150:
                motivos.append(f'«{c["nombre"]}» a {round(d)} m de la dirección publicada'); continue
        return c, 'nombre + ciudad' + (' + dirección' if direccion and direccion.get('precisa') else '')
    return None, '; '.join(motivos) or 'Google no devolvió candidatos'
