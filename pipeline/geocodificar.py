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

LA CASCADA (27 nov 2026): almacén → Google por nombre → dirección publicada →
variantes del nombre → BÚSQUEDA WEB (paso 5, obligatorio) → persona. Lo que no
ubican los pasos 1–4 queda con `_cascada` (qué dio cada paso) y `_buscar_web`:
  --pendientes                              qué falta y qué buscar
  --direccion "SEDE" "DIR" --fuente URL     la dirección hallada vuelve a Google
  --sin-resultado "SEDE" "qué y dónde"      paso 5 vacío → paso 6, a Juan
publicar.py no publica una sede sin pin verificado (ver pipeline/PROTOCOLO.md).

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


def _leer_geo(fid):
    p = f'{ST}/{fid}-venues-geo.json'
    return p, (json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {})


def pendientes(geo):
    """→ [(sede, paso, qué falta)] de las que no tienen pin verificado.
    Paso 5 = falta la búsqueda web; paso 6 = ya se buscó, va a una persona."""
    out = []
    for s, g in sorted(geo.items()):
        if s.startswith('_') or not isinstance(g, dict) or g.get('_prec') != 'sin verificar':
            continue
        out.append((s, 6 if g.get('_web') else 5, g))
    return out


def con_direccion(geo, sede, direccion, fuente, ciudad='', geocodificar=None, buscar=None):
    """La dirección que se encontró en la web (paso 5) vuelve a Google (paso 3).
    Entra solo si Google la ubica con precisión, y nunca sin su fuente. Si en
    ese punto hay un lugar con el nombre (o una variante), se toma su ficha;
    si no, el pin es la dirección misma, con el place_id de la dirección."""
    geocodificar = geocodificar or gmaps.geocodificar
    buscar = buscar or gmaps.buscar_lugar
    if not (fuente or '').startswith('http'):
        sys.exit('✗ --fuente debe ser la URL donde se publicó la dirección')
    g = geocodificar(direccion, ciudad)
    if not g or not g.get('precisa'):
        sys.exit(f'✗ Google no ubica con precisión «{direccion}»' + (f' (dio {g["direccion"]})' if g else '')
                 + ' — buscar una dirección con número (Cra. 51 #51-55)')
    c = None
    for q in [sede] + gmaps.variantes(sede):
        c, _ = gmaps.elegir(sede, buscar(q, ciudad, (g['lat'], g['lng']), 150), (g['lat'], g['lng']), 150,
                            direccion=g)
        if c:
            break
    prev = geo.get(sede) or {}
    nuevo = {k: v for k, v in prev.items() if k not in ('_todo', '_buscar_web', '_web')}
    nuevo.update({'lat': round((c or g)['lat'], 7), 'lng': round((c or g)['lng'], 7), '_prec': 'maps',
                  '_place_id': (c or g)['place_id'], 'address': direccion, '_fuente': fuente,
                  '_por': 'dirección publicada' + (f' + ficha «{c["nombre"]}»' if c else ', ubicada por Google')})
    if c:
        nuevo['_maps_url'] = c.get('url')
    geo[sede] = nuevo
    return nuevo


def main():
    if len(sys.argv) >= 2 and ('--pendientes' in sys.argv or '--direccion' in sys.argv
                               or '--sin-resultado' in sys.argv):
        return _pasos_5_y_6(sys.argv[1])
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
        cascada = {'1 almacén': 'no está',
                   '2 Google por nombre': por,
                   '3 dirección publicada': (('ubicada con precisión' if dirg and dirg.get('precisa')
                                              else 'Google no la ubica con precisión') if _dir
                                             else 'el festival no la publicó')}
        # PASO 4: otras formas del nombre («Auditorio X - Ciudad» → «X»). Cambia
        # la consulta, no la regla: `elegir` juzga contra el nombre completo.
        if not c:
            intentos = []
            for q in gmaps.variantes(s):
                c, por_v = gmaps.elegir(s, gmaps.buscar_lugar(q, donde, (lat0, lng0), radio * 111000),
                                        (lat0, lng0), radio * 111000,
                                        barrio_ok=s in barrios_ok, direccion=dirg)
                intentos.append(f'«{q}»: {"sí" if c else por_v}')
                if c:
                    por = f'variante «{q}» + {por_v}'
                    break
            cascada['4 variantes del nombre'] = '; '.join(intentos) or 'no hay otra forma del nombre'
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
            # PASO 5, obligatorio: la búsqueda web. Queda escrita la consulta;
            # lo que se encuentre entra con --direccion, y si de verdad no hay
            # nada, --sin-resultado deja escrito qué se buscó. Solo entonces
            # (paso 6) la sede va a una persona — ver --pendientes.
            geo[s] = {**prev, 'n': meta['n'], '_prec': 'sin verificar', '_cascada': cascada,
                      '_buscar_web': gmaps.consultas_web(s, donde),
                      '_todo': prev.get('_todo')
                      or f'paso 5: buscar en la web la dirección (python3 pipeline/geocodificar.py {fid} --pendientes)'}
            falta += 1
            print(f'[{i:2}] ??  {s[:44]}', flush=True)

    geo['_provenance'] = provenance(
        'Google Maps (Places + Geocoding) con la regla fija de gmaps.elegir: nombre '
        'distintivo + ciudad + nunca un barrio + dirección publicada. _prec:manual intocable.')
    json.dump(geo, open(geo_p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'\n{len(sedes)} sedes · ubicadas ahora {ok} · ya estaban {ya} · a mano {falta}')


def _pasos_5_y_6(fid):
    a = sys.argv
    geo_p, geo = _leer_geo(fid)
    if '--direccion' in a:
        i = a.index('--direccion')
        sede, dire = a[i + 1], a[i + 2]
        if sede not in geo:
            sys.exit(f'✗ «{sede}» no está en {geo_p}')
        fuente = a[a.index('--fuente') + 1] if '--fuente' in a else ''
        ciudad = a[a.index('--ciudad') + 1] if '--ciudad' in a else sede.split(' - ')[-1] if ' - ' in sede else ''
        n = con_direccion(geo, sede, dire, fuente, ciudad)
        print(f'✓ {sede}: {n["lat"]},{n["lng"]} — {n["_por"]}')
    elif '--sin-resultado' in a:
        i = a.index('--sin-resultado')
        sede, que = a[i + 1], a[i + 2]
        if (geo.get(sede) or {}).get('_prec') != 'sin verificar':
            sys.exit(f'✗ «{sede}» no está pendiente')
        if len(que) < 40:
            sys.exit('✗ escribir QUÉ se buscó y DÓNDE (consultas, páginas, redes): es lo que verá la persona')
        geo[sede]['_web'] = (geo[sede].get('_web') or []) + [que]
        print(f'· {sede}: paso 6, a una persona, con lo que ya se buscó')
    else:
        p = pendientes(geo)
        if not p:
            print('✓ todas las sedes tienen pin verificado')
        for s, paso, g in p:
            print(f'\n{s}  — paso {paso}')
            for k, v in (g.get('_cascada') or {}).items():
                print(f'   {k}: {v}')
            if paso == 5:
                print('   5 BUSCAR EN LA WEB (alcaldía, prensa, IG/FB del lugar y del festival):')
                for q in g.get('_buscar_web') or gmaps.consultas_web(s):
                    print(f'       {q}')
                print(f'     encontrada → python3 pipeline/geocodificar.py {fid} --direccion "{s}" "DIRECCIÓN" --fuente URL')
                print(f'     de verdad nada → python3 pipeline/geocodificar.py {fid} --sin-resultado "{s}" "qué se buscó y dónde"')
            else:
                for w in g['_web']:
                    print(f'   5 ya buscado: {w}')
                print('   6 → a Juan')
        return
    json.dump(geo, open(geo_p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
