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

Lee   festivals/staging/<id>-crudo.json  +  pipeline/<id>.plan.json (festival.sedes)
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


def limpia_direccion(d):
    """La dirección colombiana, como Nominatim la entiende.

    Medido el 23 sep 2026 con las sedes de Itagüí:
      «Carrera 50 # 52-77, barrio Centro» → 5 resultados, TODOS EN BOGOTÁ
      «Carrera 50 52-77»                  → Teatro Caribe, exacto
    El «#» y el «barrio X» no son ruido inocente: desvían la búsqueda a otra
    ciudad, que es peor que no encontrar nada. También sobra lo que va entre
    paréntesis («(carrera 51 # 51-55)» ya viene suelto) y el piso.
    """
    d = re.sub(r'\(([^)]*)\)', r' \1 ', d)          # los paréntesis, planos
    d = re.sub(r'\s*#\s*', ' ', d)                  # «# 52-77» → «52-77»
    d = re.sub(r',?\s*barrio\s+[^,]+', '', d, flags=re.I)
    d = re.sub(r'^\s*(sexto|quinto|cuarto|tercer|segundo|primer)\s+piso[^,]*,?\s*',
               '', d, flags=re.I)
    return re.sub(r'\s{2,}', ' ', d).strip(' ,')



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
        for s in (plan.get('festival', {}).get('sedes') or {}):
            sedes.setdefault(s, {'n': 0, 'ciudad': ''})
        direcciones = plan.get('festival', {}).get('direcciones') or {}

    ok = ya = falta = 0
    for i, (s, meta) in enumerate(sorted(sedes.items()), 1):
        prev = geo.get(s, {})
        if prev.get('_prec') == 'manual':
            ya += 1; continue                      # verificación humana: intocable
        if prev.get('lat'):
            ya += 1; continue
        # LA DIRECCIÓN, CUANDO EL FESTIVAL LA PUBLICA (23 sep 2026). Nominatim
        # no conoce «Auditorio Juan Carlos Escobar» ni «Cineprox Mayorca», pero
        # sí conoce «carrera 51 # 51-55, Itagüí». Itagüí imprime las SIETE
        # direcciones en sus láminas y las siete caían a mano por buscar solo
        # por nombre. Se declara en el plan (`festival.direcciones`) y se usa
        # como SEGUNDA consulta: el nombre primero, porque cuando acierta es más
        # preciso que el número de la calle.
        consultas = [f'{s}, {meta["ciudad"] or ciudad}'.strip(', ')]
        _dir = (direcciones or {}).get(s)
        if _dir:
            consultas.append(f'{limpia_direccion(_dir)}, {meta["ciudad"] or ciudad}'.strip(', '))
        distintivos = set(norm(s).split()) - GENERICAS
        elegido = None
        # La consulta POR DIRECCIÓN no puede exigir las palabras del nombre: el
        # resultado de «Carrera 50 # 52-77, Itagüí» no dice «Caribe» en ninguna
        # parte, y con el filtro del nombre las siete sedes seguían cayendo a
        # mano. Lo que la valida es OTRA cosa: que la dirección sea del propio
        # festival —impresa en su lámina— y que caiga dentro del radio. Se marca
        # `_prec:'direccion'` para que se vea de dónde salió cada punto, y no se
        # confunda con la coincidencia por nombre, que es más fuerte.
        for r, por_direccion in [(x, i > 0) for i, c in enumerate(consultas)
                                 for x in buscar(c)]:
            la, ln = float(r['lat']), float(r['lon'])
            if abs(la - lat0) > radio or abs(ln - lng0) > radio:
                continue                           # otra ciudad
            if not por_direccion and distintivos and not (
                    distintivos & set(norm(r.get('display_name', '')).split())):
                continue                           # nombre que no distingue nada
            if not por_direccion and r.get('class') in CLASES_LUGAR and s not in barrios_ok:
                continue                           # una sala fija nunca es un barrio
            elegido = {'lat': round(la, 7), 'lng': round(ln, 7),
                       '_prec': 'direccion' if por_direccion else 'nominatim',
                       '_match': r['display_name'][:90]}
            break
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
                      or 'buscar a mano (sedes-html.py genera la página)'}
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
