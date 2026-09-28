# -*- coding: utf-8 -*-
"""enriquecer_catalogo.py <sidecar> — la ficha de cada obra de un CATÁLOGO.

Hermano de `enriquecer.py` para el PRE-ONBOARDING: cuando el festival ya publicó
qué obras van pero todavía no cuándo ni dónde. `enriquecer.py` parte del crudo, y
el crudo EXIGE día, hora y sede —con razón: es el formato de una función—. Un
catálogo sin parrilla no puede cumplir ese contrato sin inventarse los tres, y
un dato inventado para pasar una compuerta es peor que no tener el dato.

No duplica la doctrina: importa `enriquecer_obra` de `enriquecer.py`, así que el
candado sigue siendo el mismo —director ✓ Y (año ±1 O duración ±3 min)— y vive
en un solo sitio.

⚠ Ese candado necesita AÑO o DURACIÓN. La obra que no trae ninguno de los dos
va por el OTRO camino que ya tenía lib.ficha_tmdb: TÍTULO IDÉNTICO + director.
Hasta el 28 sep 2026 se saltaba sin buscarla, y el camino existía sin que
nadie lo llamara: en Popayán eran 25 obras y 13 tenían ficha en TMDB con su
título original exacto y su dirección («La tinaja», «Sombras en la niebla»,
«Los Huyentes»…). El director se exige igual en los dos caminos.

Lee   festivals/staging/<lo-que-sea>.json   con obras[] de {titulo, director, …}
Esc.  festivals/staging/<lo-que-sea>-enriquecido.json
"""
import json, os, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from enriquecer import enriquecer_obra, ficha_declarada, ficha_de_tmdb
from lib import provenance, ficha_tmdb

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    if len(sys.argv) < 2:
        sys.exit('uso: TMDB_API_KEY=… python3 pipeline/enriquecer_catalogo.py <ruta-del-sidecar>')
    p = sys.argv[1]
    if not os.path.isabs(p):
        p = f'{REPO}/{p}'
    key = os.environ.get('TMDB_API_KEY') or sys.exit('falta TMDB_API_KEY')
    d = json.load(open(p, encoding='utf-8'))
    obras = d.get('obras')
    assert isinstance(obras, list) and obras, f'{p}: falta la lista obras[]'

    # El aviso que evita el diagnóstico equivocado: sin año NI duración el
    # candado no puede abrirse, y esas obras solo se encuentran con su título
    # EXACTO. Si faltan muchas, pedirle los datos al festival sigue valiendo.
    sin_datos = [o for o in obras if not (o.get('anio') or o.get('duracion_min'))]
    if sin_datos:
        print(f'⚠ {len(sin_datos)} de {len(obras)} obras sin año ni duración: solo '
              f'entran con título idéntico + director.')
    verificables = obras

    # Las fichas que declaró una persona, con su porqué — la MISMA salida que
    # enriquecer.py (Itagüí, «Inolvidable Heidi»). Faltaba acá: «La creciente»
    # (Jardín, 24 sep 2026) la dio de alta Juan en TMDB esa noche y la API
    # tarda horas en devolverla en búsquedas y créditos, así que el candado no
    # la podía ver aunque su id ya existiera. <fest>-correcciones.json, junto
    # al sidecar: el fest-id es el nombre del sidecar sin «-catalogo.json».
    _fid = os.path.basename(p).replace('-catalogo.json', '')
    corr_p = os.path.join(os.path.dirname(p), f'{_fid}-correcciones.json')
    declaradas = (json.load(open(corr_p, encoding='utf-8')).get('fichas', {})
                  if os.path.exists(corr_p) else {})
    _titulos = {o['titulo'] for o in obras}
    _huerf = [t for t in declaradas if t not in _titulos]
    if _huerf:
        sys.exit(f'ficha declarada para un título que no está en el catálogo: {_huerf}')

    ok, sin = {}, []
    for i, o in enumerate(verificables, 1):
        if o['titulo'] in declaradas:
            e = ficha_declarada(o['titulo'], declaradas[o['titulo']], key)
        elif o.get('anio') or o.get('duracion_min'):
            e = enriquecer_obra(o, key, {})
        else:
            e = None
            r = ficha_tmdb(o, key)
            if r:
                _det, e = ficha_de_tmdb(r[0]['id'], key, o['titulo'])
                e['_verificado'] = r[2]
        t = o['titulo']
        if e:
            ok[t] = e
            print(f'[{i:3}/{len(verificables)}] OK  {t[:44]:46} tmdb {e["tmdb_id"]}'
                  f'{"  lb✓" if e.get("lbSlug") else ""}', flush=True)
        else:
            sin.append(t)
            print(f'[{i:3}/{len(verificables)}] —   {t[:44]:46} sin ficha verificable', flush=True)
        time.sleep(0.2)

    dest = p.replace('.json', '-enriquecido.json')
    json.dump({'_provenance': provenance(
        'TMDB + letterboxd.com/tmdb/<id>, con el MISMO candado de enriquecer.py: '
        'director ✓ y (año ±1 o duración ±3 min). Lo que no verifica no entra.'),
        '_origen': os.path.basename(p),
        # `obras` es la LISTA que lee el ensamblador y exige cargar_plan (lib.
        # _forma_sidecar). `enriquecer.py` ya había pagado este error y lo
        # arregló escribiendo las dos formas; su hermano se quedó atrás, y el
        # síntoma es el mismo y es MUDO: el plan que declara este archivo como
        # `enriquecido` no cumple su contrato, y si el contrato no lo cazara,
        # el enriquecido se cargaría sin error y no aportaría nada. Salió a la
        # luz montando el Festival de Cine de Jardín (20 sep 2026), que empezó
        # como pre-onboarding —catálogo sin parrilla— y luego creció a festival.
        'obras': [{'titulo': t, **e} for t, e in ok.items()],
        'verificadas': ok, 'sin_ficha': sorted(sin)},
        open(dest, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'\n{len(obras)} obras ({len(sin_datos)} sin año ni duración) · con ficha {len(ok)} · sin ficha {len(sin)}')
    print(f'  con póster {sum(1 for e in ok.values() if e.get("poster_path"))} · '
          f'con lbSlug {sum(1 for e in ok.values() if e.get("lbSlug"))}')


if __name__ == '__main__':
    main()
