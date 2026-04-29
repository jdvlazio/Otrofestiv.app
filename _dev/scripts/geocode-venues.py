#!/usr/bin/env python3
"""
Otrofestiv — Geocodificador de venues via Nominatim/OpenStreetMap
=================================================================
Uso: python3 geocode-venues.py festivals/cinemancia-2025.json

Obtiene coordenadas verificadas (lat/lng) para cada venue de un festival
usando la API pública de Nominatim (OpenStreetMap). Sin API key. Gratuito.

PROCESO:
  1. Lee el JSON del festival
  2. Para cada venue sin coordenadas, busca en Nominatim
  3. Muestra resultado para verificación manual
  4. Actualiza el JSON con las coordenadas encontradas

PARA FESTIVALES FUTUROS:
  Añadir en el JSON antes de correr el script:
  "venues": {
    "Nombre del venue": {
      "short": "Nombre corto",
      "city": "Ciudad",
      "address": "Dirección completa"  ← ayuda al geocodificador
    }
  }

VERIFICACIÓN:
  El script muestra la dirección OSM encontrada para cada venue.
  Verificar que el nombre/barrio coincide antes de confirmar.
  Si la coordinada es incorrecta, editar manualmente en el JSON.

POLÍTICA DE USO NOMINATIM:
  - Máximo 1 request/segundo (el script respeta esto)
  - User-Agent identificado como Otrofestiv
  - No usar en producción con más de 100 venues/hora
"""

import json, sys, time, urllib.request, urllib.parse

NOMINATIM = 'https://nominatim.openstreetmap.org/search'
DELAY = 1.1  # segundos entre requests (política Nominatim: max 1/sec)

def geocode(query, country_code='co'):
    """Busca coordenadas en Nominatim para una query."""
    params = urllib.parse.urlencode({
        'q': query,
        'format': 'json',
        'limit': 1,
        'countrycodes': country_code,
        'accept-language': 'es'
    })
    url = f'{NOMINATIM}?{params}'
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Otrofestiv/1.0 (festival planning app)',
        'Accept-Language': 'es'
    })
    try:
        data = json.loads(urllib.request.urlopen(req, timeout=10).read())
        if data:
            return {
                'lat': float(data[0]['lat']),
                'lng': float(data[0]['lon']),
                '_osm_display': data[0]['display_name'][:80]
            }
    except Exception as e:
        print(f"    Error: {e}")
    return None

def build_query(venue_name, venue_cfg, festival_city):
    """
    Construye la query de búsqueda en orden de precisión:
    1. Nombre + dirección + ciudad (más preciso)
    2. Nombre + ciudad
    3. Ciudad sola (fallback para venues pequeños)
    """
    city = venue_cfg.get('city') or festival_city or ''
    address = venue_cfg.get('address', '')
    
    if address:
        return f"{venue_name}, {address}, {city}, Colombia"
    return f"{venue_name}, {city}, Colombia"

def main(filepath):
    print(f"\n{'═'*60}")
    print(f"  Otrofestiv — Geocodificador de venues (Nominatim/OSM)")
    print(f"{'═'*60}")

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    cfg = data.get('config', {})
    festival_name = cfg.get('name', filepath)
    festival_city = cfg.get('city', '')
    venues = data.get('venues', {})

    if not venues:
        print("\n  ⚠ No hay venues en el JSON. Añadir sección 'venues' primero.")
        print("  Ver FESTIVAL_GUIDE.md para el formato.")
        sys.exit(1)

    # Filtrar venues sin coordenadas
    to_geocode = {k: v for k, v in venues.items() if 'lat' not in v or 'lng' not in v}
    
    print(f"\n  Festival  : {festival_name}")
    print(f"  Venues    : {len(venues)} total | {len(to_geocode)} sin coordenadas")
    print(f"  Fuente    : Nominatim / OpenStreetMap")
    print(f"{'─'*60}\n")

    if not to_geocode:
        print("  ✓ Todos los venues ya tienen coordenadas.")
        sys.exit(0)

    found, not_found, manual_needed = 0, [], []

    for name, venue_cfg in to_geocode.items():
        query = build_query(name, venue_cfg, festival_city)
        result = geocode(query)
        time.sleep(DELAY)

        if result:
            venues[name].update({'lat': result['lat'], 'lng': result['lng']})
            found += 1
            print(f"  ✓ {name[:40]}")
            print(f"      OSM: {result['_osm_display']}")
            print(f"      Coords: {result['lat']:.5f}, {result['lng']:.5f}")
        else:
            # Retry con query más simple (solo nombre + ciudad)
            city = venue_cfg.get('city', festival_city)
            simple_query = f"{name}, {city}, Colombia"
            result2 = geocode(simple_query)
            time.sleep(DELAY)

            if result2:
                venues[name].update({'lat': result2['lat'], 'lng': result2['lng']})
                found += 1
                print(f"  ✓ {name[:40]} (query simple)")
                print(f"      OSM: {result2['_osm_display']}")
            else:
                not_found.append(name)
                print(f"  ✗ {name[:40]} — no encontrado")
                manual_needed.append(name)

    # Guardar
    data['venues'] = venues
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n{'─'*60}")
    print(f"  Encontrados  : {found}/{len(to_geocode)}")
    print(f"  No encontrados: {len(not_found)}")
    print(f"  Guardado en  : {filepath}")

    if manual_needed:
        print(f"\n  Añadir manualmente en 'venues' del JSON:")
        for name in manual_needed:
            city = venues[name].get('city', festival_city)
            print(f"    → Buscar en maps.google.com: \"{name}, {city}\"")
            print(f"       Añadir: \"lat\": X.XXXXX, \"lng\": -XX.XXXXX")

    print(f"\n  ⚠ Verificar coordenadas visualmente en OSM:")
    print(f"    https://www.openstreetmap.org/#map=15/LAT/LNG")
    print(f"\n{'═'*60}\n")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        print("Uso: python3 geocode-venues.py festivals/cinemancia-2025.json")
        sys.exit(1)
    main(sys.argv[1])
