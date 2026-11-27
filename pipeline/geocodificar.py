# -*- coding: utf-8 -*-
"""geocodificar.py <fest-id> --centro LAT,LNG [--radio 0.3] — sedes verificadas.

Herramienta genérica sobre el formato intermedio. Desde el 27 nov 2026 la única
fuente es GOOGLE MAPS (`pipeline/gmaps.py`): Nominatim y Photon salieron del
pipeline — medidos sobre lugares ya verificados, Nominatim falló en 15 de 18 y
los pines malos de FICDEH venían de ahí. Sin `GOOGLE_MAPS_API_KEY` se detiene.

Un pin entra solo si cumple la regla fija de `gmaps.elegir` (nombre distintivo
+ ciudad + nunca un barrio + a <150 m de la dirección publicada, si la hay).
Lo que no la cumple queda `_prec:"sin verificar"` con el porqué en `_todo`:
NUNCA se adivina. Medida el 27 nov sobre 40 lugares verificados: 32 bien, 0
mal, 8 a revisión. Cada pin guarda `_place_id` (Google deja guardarlo para
siempre) y `_maps_url`; las coordenadas vencen a los 30 días y las renueva
`sedes.py --refrescar`.

Una sede que ya está en la MATRIZ (catalogo/sedes.json, pipeline/sedes.py)
entra con su pin, `_prec:"matriz"`, antes de preguntarle a Google.

Las coordenadas con `_prec:"manual"` son verificación humana y NO SE TOCAN —
correr el geocoder dos veces pisó 40 verificaciones de Juan en FICDEH.

Lee   festivals/staging/<id>-crudo.json  +  pipeline/<id>.plan.json (festival.sedes)
Merge festivals/staging/<id>-venues-geo.json   (se crea si no existe)
"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import cargar_crudo, provenance
import gmaps

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'


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

    # LAS SEDES SON LAS DEL PLAN, NO SOLO LAS QUE YA TIENEN FUNCIÓN. La tabla
    # canónica del plan es donde el festival declara sus sedes; derivarlas del
    # crudo daba por inexistente la que todavía no tiene programación.
    #
    # Pasó con el Festival de Cine de Jardín (20 sep 2026): publicó el MAPA de
    # sus cinco sedes —con dos reubicadas por el sismo del 10 de agosto— cuatro
    # días antes de empezar y sin parrilla. El crudo tenía una sola función, así
    # que el geocoder ubicaba una sede de cinco y las otras cuatro quedaban sin
    # coordenadas hasta que saliera la programación, que es justo cuando ya no
    # hay tiempo. El dato estaba publicado; lo que faltaba era leerlo de donde
    # se declara.
    #
    # Se lee el plan A PELO y no con `cargar_plan()`: el contrato exige que el
    # sidecar `geo` ya exista, y el sidecar `geo` es justo lo que este paso
    # escribe. Una herramienta no puede pedir como requisito su propia salida.
    # El contrato lo hacen cumplir `correr.py` y `ensamblar.py`, que van después.
    plan_p = f'{REPO}/pipeline/{fid}.plan.json'
    direcciones = {}
    if os.path.exists(plan_p):
        plan = json.load(open(plan_p, encoding='utf-8'))
        _sp = plan.get('festival', {}).get('sedes') or {}
        for s in _sp:
            # la grafía cruda del impreso NO es una sede nueva cuando su sede
            # canónica (`sedes` como mapa crudo → [sede, sala]) ya tiene pin:
            # en Villa del Cine entraba «sin verificar» en cada corrida
            v = _sp[s] if isinstance(_sp, dict) else None
            if isinstance(v, list) and v and v[0] in geo:
                continue
            sedes.setdefault(s, {'n': 0, 'ciudad': ''})
        direcciones = plan.get('festival', {}).get('direcciones') or {}

    ok = ya = falta = 0
    for i, (s, meta) in enumerate(sorted(sedes.items()), 1):
        prev = geo.get(s, {})
        if prev.get('_prec') == 'manual':
            ya += 1; continue                      # verificación humana: intocable
        if prev.get('lat'):
            ya += 1; continue
        # LA MATRIZ DE SEDES PRIMERO (16 nov 2026, catalogo/sedes.json): una
        # sede que ya ubicamos en otro festival entra con ESE pin verificado, no
        # se vuelve a buscar ni se copia a mano. Solo las nuevas van a Google.
        import sedes as _matriz
        hit = _matriz.buscar(s, (lat0, lng0), radio_m=radio * 111000)
        if hit:
            geo[s] = {**prev, **hit, 'n': meta['n']}
            ok += 1
            print(f'[{i:2}] MZ  {s[:44]:46} {hit["_matriz"]}', flush=True)
            continue
        # GOOGLE (27 nov 2026): Places por nombre y ciudad, sesgado al centro;
        # la dirección del festival (`festival.direcciones` del plan), si la
        # hay, se ubica con Geocoding y el lugar debe caer a <150 m de ella.
        donde = meta['ciudad'] or ciudad
        _dir = (direcciones or {}).get(s)
        dirg = gmaps.geocodificar(_dir, donde) if _dir else None
        cands = gmaps.buscar_lugar(s, donde, (lat0, lng0), radio * 111000)
        c, por = gmaps.elegir(s, cands, (lat0, lng0), radio * 111000,
                              barrio_ok=s in barrios_ok, direccion=dirg)
        elegido = c and {'lat': round(c['lat'], 7), 'lng': round(c['lng'], 7), '_prec': 'maps',
                         '_place_id': c['place_id'], '_maps_url': c['url'],
                         '_match': f'{c["nombre"]} — {c["direccion"]}'[:90], '_por': por}
        if elegido:
            geo[s] = {**prev, **elegido, 'n': meta['n']}
            ok += 1
            print(f'[{i:2}] OK  {s[:44]:46} {elegido["_match"][:48]}', flush=True)
        else:
            # `_todo`, NO `_nota`: son dos cosas distintas y llamarlas igual
            # costó caro. Esto es un PENDIENTE de trabajo y se queda en el
            # sidecar. `_nota` significa otra cosa —«esta sede se revisó a mano
            # y es real»— y el guardián [sedes-apiladas] la lee en el JSON
            # publicado para dar por cerrado el aviso. Con el mismo nombre, un
            # pendiente silenciaba el aviso de una sede sin revisar.
            #
            # Y el `_todo` QUE YA ESTUVIERA ESCRITO no se pisa. El genérico es
            # un recordatorio; el que escribe una persona dice qué se buscó,
            # dónde y por qué no apareció —«no existe en OSM, ni en la web de
            # la alcaldía; es sede nueva de esta edición»—. Pisarlo en cada
            # corrida borra el trabajo de averiguarlo y obliga a repetirlo, que
            # es justo lo que un pipeline re-corrible no puede hacer.
            geo[s] = {**prev, 'n': meta['n'], '_prec': 'sin verificar',
                      '_todo': prev.get('_todo')
                      or f'revisar en Google Maps: {por}'}
            falta += 1
            print(f'[{i:2}] ??  {s[:44]}', flush=True)

    geo['_provenance'] = provenance(
        'Google Maps (Places + Geocoding) con la regla fija de gmaps.elegir: nombre '
        'distintivo + ciudad + nunca un barrio + dirección publicada. _prec:manual intocable.')
    json.dump(geo, open(geo_p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'\n{len(sedes)} sedes · ubicadas ahora {ok} · ya estaban {ya} · a mano {falta}')


if __name__ == '__main__':
    main()
