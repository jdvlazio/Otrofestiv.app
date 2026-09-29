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
import json, os, re, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from enriquecer import enriquecer_obra, ficha_declarada, ficha_de_tmdb
from lib import (provenance, ficha_tmdb, tmdb_get, director_coincide,
                 obras_publicadas, ya_publicada)
import proimagenes
import cinecorto

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

    # LA CASCADA (28 sep 2026). Cada obra pasa por todas las fuentes, en orden,
    # hasta que una la verifica; y SIEMPRE se cruza contra lo que ya
    # publicamos. Antes una obra que TMDB tenía sin año ni duración salía «sin
    # ficha» aunque el título y el director casaran exactos, y nadie miraba
    # nuestros propios festivales: «Lolita en Honda» estaba en FICCI 65 y en
    # Cinemancia 2026, con afiche y sinopsis, y Mamut la dio por perdida.
    #   1. la ficha declarada a mano;
    #   2. TMDB con el candado: director ✓ Y (año ±1 O duración ±3);
    #   3. TMDB por título idéntico + director, cuando a cualquiera de los dos
    #      lados le faltan año y duración (lib.ficha_tmdb);
    #   4. el tmdb_id con que ya la publicamos, si TMDB confirma la dirección;
    #   5. Proimágenes, para el cine colombiano que TMDB no tiene (mismo
    #      candado de dirección que proimagenes.py);
    #   6. cinecorto.co, para el corto colombiano: año, duración y sinopsis.
    publicadas = obras_publicadas(REPO, excluir=(_fid,))
    ok, sin, por_fuente = {}, [], {}
    for i, o in enumerate(verificables, 1):
        t = o['titulo']
        pub = ya_publicada(o, publicadas)
        e, fuente = None, None
        # la fuente se anota SOLO si devolvió algo: la primera versión la ponía
        # antes de saberlo, y «Belleza letal» salía «OK tmdb» sin tmdb_id
        # porque el cruce con lo publicado le daba cuerpo después.
        if t in declaradas:
            e = ficha_declarada(t, declaradas[t], key)
            fuente = 'declarada' if e else None
        if not e and (o.get('anio') or o.get('duracion_min')):
            e = enriquecer_obra(o, key, {})
            fuente = 'tmdb' if e else None
        if not e and o.get('director'):
            r = ficha_tmdb(o, key)
            if r:
                _det, e = ficha_de_tmdb(r[0]['id'], key, t)
                e['_verificado'] = r[2]
                fuente = 'tmdb (título idéntico)'
        if not e and o.get('director'):
            for x in pub:
                if not x.get('tmdb_id'):
                    continue
                cr = tmdb_get(f"/movie/{x['tmdb_id']}/credits", key) or {}
                dirs = [c['name'] for c in cr.get('crew', []) if c.get('job') == 'Director']
                if director_coincide(o['director'], dirs):
                    _det, e = ficha_de_tmdb(x['tmdb_id'], key, t)
                    e['_verificado'] = (f'el tmdb_id con que ya la publicamos en '
                                        f'{x["festival"]}, y TMDB confirma la dirección')
                    fuente = 'tmdb (ya publicada)'
                    break
        if not e and o.get('director'):
            for idp in proimagenes.busca(t):
                h = proimagenes.ficha(idp)
                if h and director_coincide(o['director'], h['directores']):
                    e = {'_fuente': 'proimagenes', '_proimagenes_id': h['id'],
                         'pais': 'Colombia',
                         '_verificado': f'Proimágenes, director: {", ".join(h["directores"])}'}
                    if h['anio'].isdigit():
                        e['anio'] = int(h['anio'])
                    m = re.search(r'(\d{1,3})', h['duracion'])
                    if m:
                        e['duracion_min'] = int(m.group(1))
                    if h['sinopsis']:
                        e['sinopsis'] = h['sinopsis'][:1200]
                    if h['afiche']:
                        e['_afiche_proimagenes'] = h['afiche']
                    fuente = 'proimagenes'
                    break
        if not e and o.get('director'):
            c = cinecorto.ficha(t, o['director'])
            if c:
                e = {'_fuente': 'cinecorto', '_cinecorto': c['url'],
                     '_verificado': f'cinecorto.co, dirección: {c["direccion"]}'}
                for k in ('anio', 'duracion_min', 'sinopsis', 'sinopsis_en'):
                    if c.get(k):
                        e[k] = c[k]
                fuente = 'cinecorto'
        if pub:
            e = dict(e or {})
            e['_ya_publicada'] = pub
        if e and fuente:
            ok[t] = e
            por_fuente[fuente] = por_fuente.get(fuente, 0) + 1
            print(f'[{i:3}/{len(verificables)}] OK  {t[:44]:46} {fuente}'
                  f'{" " + str(e["tmdb_id"]) if e.get("tmdb_id") else ""}'
                  f'{"  · ya publicada: " + ", ".join(x["festival"] for x in pub) if pub else ""}',
                  flush=True)
        else:
            if e:           # sin ficha, pero ya la publicamos: se guarda el cruce
                ok[t] = e
            sin.append(t)
            print(f'[{i:3}/{len(verificables)}] —   {t[:44]:46} sin ficha verificable'
                  f'{"  · ya publicada: " + ", ".join(x["festival"] for x in pub) if pub else ""}',
                  flush=True)
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
        # `verificadas` son SOLO las que alguna fuente verificó; una obra sin
        # ficha que ya publicamos va en `obras` con su cruce, no acá.
        'verificadas': {t: e for t, e in ok.items() if t not in sin},
        'sin_ficha': sorted(sin)},
        open(dest, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'\n{len(obras)} obras ({len(sin_datos)} sin año ni duración) · con ficha '
          f'{len(obras) - len(sin)} · sin ficha {len(sin)}')
    print('  por fuente: ' + ' · '.join(f'{k} {v}' for k, v in sorted(por_fuente.items())))
    print(f'  ya publicadas en otro festival nuestro: '
          f'{sum(1 for e in ok.values() if e.get("_ya_publicada"))}')
    print(f'  con póster {sum(1 for e in ok.values() if e.get("poster_path"))} · '
          f'con lbSlug {sum(1 for e in ok.values() if e.get("lbSlug"))}')


if __name__ == '__main__':
    main()
