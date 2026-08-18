# -*- coding: utf-8 -*-
"""Ensamblador GENÉRICO: crudo (formato intermedio) + plan → build.

POR QUÉ EXISTE. Hasta el 17 ago 2026 cada festival escribía su propio
ensamblador, y ahí es donde se perdían las cosas una y otra vez: los 6 enlaces
de TuBoleta de CineAutopsia que estaban en la fuente, las 415 banderas de
FICDEH que nunca se derivaron, el `is_free: false` escrito a mano en una función
que era libre. No eran doce errores distintos: era el mismo error doce veces,
porque las reglas vivían en la cabeza de quien escribía el ensamblador de turno.

Aquí las reglas se escriben UNA vez y el festival aporta solo lo suyo, en
`pipeline/<id>.plan.json`. Lo que el festival NO puede aportar es una forma
distinta de derivar una bandera o de escribir una hora.

QUÉ ES DE CADA QUIEN:
  · del PARSER   — el crudo, en el formato intermedio (docs PROTOCOLO §4)
  · del PLAN     — identidad del festival, tabla de sedes, mapa de secciones
  · de AQUÍ      — day_order, flags, «N min», «Sede - Ciudad», acceso, cortos

    python3 pipeline/ensamblar.py <id>            # → staging/<id>-build.json
    python3 pipeline/ensamblar.py <id> --ver      # sin escribir, solo el resumen
"""
import json, os, sys, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _plan(fid):
    p = f'{REPO}/pipeline/{fid}.plan.json'
    if not os.path.exists(p):
        sys.exit(f'✗ falta {p} — el plan declara la identidad del festival y sus tablas')
    d = json.load(open(p, encoding='utf-8'))
    if 'festival' not in d:
        sys.exit(f'✗ {p} no tiene bloque "festival" — ver la cabecera de ensamblar.py')
    return d


def _seccion_de(f, cfg):
    """De qué sección es esta función. Tres vías, en orden, y todas EXPLÍCITAS:
    lo que diga el crudo · lo que el plan declare por palabra del título · el
    default del plan. Nunca se adivina: un festival que no declara sus secciones
    para el ensamblador genérico es un festival que no las ha decidido, y eso se
    decide con Juan, no en el código (docs/PROTOCOLO §4)."""
    if f.get('seccion'):
        return f['seccion']
    for palabra, sec in (cfg.get('seccion_por_titulo') or {}).items():
        if lib.norm(palabra) in lib.norm(f.get('titulo') or ''):
            return sec
    return cfg.get('seccion_default', '')


def _seccion(nombre, mapa):
    """La sección publicada = emoji + la palabra DEL FESTIVAL, verbatim. Nuestra
    capa es el emoji, el inglés y el arquetipo; el nombre no se normaliza
    (regla de Juan, 4 jul 2026)."""
    s = mapa.get(nombre)
    if not s:
        sys.exit(f'✗ sección sin declarar en el plan: «{nombre}» — el mapa de '
                 f'secciones es explícito, nunca heurístico')
    return f"{s['emoji']} {s.get('nombre', nombre)}", s

def _enriquece(dst, it):
    """Copia del enriquecido SOLO lo que la fuente del festival no trae. La
    fuente manda: su duración es la que programó, su título es el que publicó."""
    for campo, origen in (('poster', ('poster', 'poster_tmdb', 'poster_url')),
                          ('lbSlug', ('lbSlug',)), ('tmdb_id', ('tmdb_id',)),
                          ('synopsis', ('sinopsis', 'synopsis_es')),
                          ('synopsis_en', ('synopsis_en',)),
                          ('title_en', ('title_en',)), ('genre', ('genero', 'genre'))):
        if dst.get(campo):
            continue
        v = next((it[o] for o in origen if it.get(o)), None)
        if v:
            dst[campo] = v
    # TMDB devuelve `poster_path` como «/xxx.jpg» pelado. Se completa aquí, una
    # vez: dejarlo crudo obliga a cada vista a saber de dónde salió el póster, y
    # el dueño del póster es docs/POSTERS.md, no la vista.
    _p = str(dst.get('poster') or '')
    if _p.startswith('/') and not _p.startswith('/assets/'):
        dst['poster'] = 'https://image.tmdb.org/t/p/w500' + _p
        dst['posterSource'] = 'tmdb'
    elif dst.get('poster') and not dst.get('posterSource'):
        dst['posterSource'] = 'tmdb' if 'image.tmdb.org' in _p else 'oficial'
    if dst.get('synopsis') and not dst.get('synopsis_lang'):
        dst['synopsis_lang'] = 'es'
    return dst


def ensamblar(fid, escribir=True):
    plan = _plan(fid)
    cfg = plan['festival']
    crudo = lib.cargar_crudo(f"{REPO}/{cfg['crudo']}")     # exige acceso declarado
    # El enriquecido se indexa POR TÍTULO NORMALIZADO. La clave vacía se
    # descarta a propósito: «月宫» normaliza a '' y una clave vacía casa con
    # cualquier cosa — así cuatro obras se robaron el mismo slug en TIFF.
    enr = {}
    if cfg.get('enriquecido') and os.path.exists(f"{REPO}/{cfg['enriquecido']}"):
        _e = json.load(open(f"{REPO}/{cfg['enriquecido']}", encoding='utf-8'))
        _lista = next((v for k, v in _e.items()
                       if isinstance(v, list) and v and isinstance(v[0], dict)), [])
        for it in _lista:
            k = lib.norm(it.get('titulo') or it.get('title') or '')
            if k:
                enr[k] = it


    geo = {}
    if cfg.get('geo') and os.path.exists(f"{REPO}/{cfg['geo']}"):
        geo = json.load(open(f"{REPO}/{cfg['geo']}", encoding='utf-8'))
        geo = geo.get('venues', geo)

    SEDES = cfg.get('sedes', {})
    SECS = cfg.get('secciones', {})
    dias = sorted({f['dia'] for f in crudo['funciones'] if f.get('dia')})
    orden = {d: i for i, d in enumerate(dias)}

    films, venues, secciones = [], {}, {}
    rep = collections.Counter()
    for f in crudo['funciones']:
        sede, sala = lib.sede_sala(f['sede'], SEDES)
        if sede not in geo and sede not in venues:
            rep['sede sin geo'] += 1
        sec_pub, sec_meta = _seccion(_seccion_de(f, cfg), SECS)
        if sec_pub not in secciones:
            secciones[sec_pub] = {'en': sec_meta['en'], 'archetype': sec_meta['archetype'],
                                  'order': len(secciones) + 1}
        obras = f.get('obras') or f.get('film_list') or []
        e = {
            'title': f['titulo'],
            'type': f.get('type') or ('event' if f.get('event_kind') else 'film'),
            'section': sec_pub,
            'director': f.get('director') or None,
            'year': f.get('anio') or None,
            'country': f.get('pais') or None,
            'flags': lib.banderas(f.get('pais') or '') or None,
            'duration': f"{f['duracion_min']} min" if f.get('duracion_min') else None,
            'language': f.get('idioma') or None,
            'rating': f.get('clasificacion') or None,
            'day': f.get('dia'), 'time': f.get('hora'), 'day_order': orden.get(f.get('dia')),
            'venue': sede, 'sala': sala or None,
            'event_kind': f.get('event_kind') or None,
            # `info`: drop-in sin hora de fin — se muestra y NO se planifica.
            'info': True if f.get('info') else None,
            'has_qa': bool(f.get('has_qa')),
            'qa_type': f.get('qa_type') or None,
            'synopsis': f.get('sinopsis') or None,
            'synopsis_lang': 'es' if f.get('sinopsis') else None,
            'poster': f.get('poster') or None,
            # El póster que publica el festival es EDITORIAL: es la pieza del
            # programa, no el afiche de una obra (docs/POSTERS.md §2).
            'posterSource': (cfg.get('posterSource_fuente', 'editorial')
                             if f.get('poster') else None),
            '_src': ({'url': f['_src'], 'fuente': crudo['_provenance'].get('fuente', '')}
                     if isinstance(f.get('_src'), str) and f['_src'].startswith('http')
                     else f.get('_src') or crudo['_provenance'].get('fuente')),
        }
        # La casilla de acceso: una sola traducción, la de lib. Si la fuente dice
        # `desconocido`, no se emite nada — y eso es distinto de no haber mirado.
        acc = (f.get('acceso') or '').strip()
        if acc and acc != lib.DESCONOCIDO:
            e.update(lib.acceso_campos(acc, f.get('ticket_url') or ''))
        elif f.get('ticket_url'):
            e['ticket_url'] = f['ticket_url']
        if obras:
            e['is_cortos'] = True
            e['film_list'] = [{k: v for k, v in {
                'title': o.get('titulo') or o.get('title'),
                'director': o.get('director'),
                'country': o.get('pais') or o.get('country'),
                'flags': lib.banderas(o.get('pais') or o.get('country') or '') or None,
                'year': o.get('anio') or o.get('year'),
                'duration': f"{o['duracion_min']} min" if o.get('duracion_min') else None,
            }.items() if v not in (None, '', [], {})} for o in obras]
            # Lo que la FUENTE ya trae sobre la obra viaja tal cual. Qué campos
            # puede llevar una obra lo decide el contrato, no una lista escrita
            # a mano aquí: la lista fija de arriba (título/director/país/año/
            # duración) se comió los tmdb_id, los pósters y las 37 sinopsis de
            # CineAutopsia — el dato estaba en el crudo y el ensamblador,
            # calladito, lo tiraba. Primero verbatim, después los alias
            # (sinopsis→synopsis), y solo al final el enriquecido: la fuente
            # del festival manda sobre nuestra tabla.
            _campos = lib.contrato()['campos']
            for item, _o in zip(e['film_list'], obras):
                for _c in _campos:
                    if _o.get(_c) and not item.get(_c):
                        item[_c] = _o[_c]
                _enriquece(item, _o)
            # Cada obra DENTRO del programa se enriquece por su cuenta: en un
            # bloque de cortos, el póster que importa es el de cada corto.
            for item in e['film_list']:
                _it = enr.get(lib.norm(item.get('title') or ''))
                if _it:
                    _enriquece(item, _it)
            # El país de un PROGRAMA es el de las obras que lo componen: no
            # existe «el país» de una sesión de siete cortos de cinco lugares.
            # Y su `year` tampoco: el año lo tiene cada obra, y poner el de la
            # sesión pinta «2025» al lado de un programa de 2026.
            # La duración de un PROGRAMA es la suma de sus obras. Lo hice a mano
            # para los 20 bloques de TIFF; vive aquí para que no haya que
            # volver a hacerlo en ningún festival. Solo si la fuente no la trae:
            # su número manda, porque incluye presentaciones y pausas.
            if not e.get('duration'):
                _mins = sum(int(_m.group(1)) for o in e['film_list']
                            if (_m := __import__('re').match(r'(\d+)', str(o.get('duration') or ''))))
                if _mins:
                    e['duration'] = f'{_mins} min'
            _paises = [p for o in e['film_list'] if (p := o.get('country'))]
            if _paises and not e.get('country'):
                # Se deduplica por PAÍS, nunca por carácter: una bandera son DOS
                # puntos de código (indicadores regionales) y deduplicar sus
                # caracteres produjo «🇺🇸🇪🇵🇱🇩» — banderas cortadas a la mitad.
                _u = list(dict.fromkeys(x.strip() for p in _paises for x in p.split(',') if x.strip()))
                e['country'] = ', '.join(_u)
                e['flags'] = ''.join(dict.fromkeys(lib.banderas(p) for p in _u))
            e.pop('year', None)
        it = enr.get(lib.norm(f['titulo']))
        if it:
            _enriquece(e, it)
        # UN PROGRAMA DE UNA SOLA OBRA NO ES UN PROGRAMA. La doctrina dice que
        # hay contenedor cuando el festival le puso NOMBRE A UN CONJUNTO
        # (docs/SCHEMA.md, modelo A). Con una sola obra no hay conjunto: lo que
        # el festival nombró es la CATEGORÍA, y la función es esa obra. Se
        # promueve: el usuario busca «Paristopia», no «Largometraje Panorama
        # Colombia», y la ficha del programa mostraba una lista de un elemento.
        if len(e.get('film_list') or []) == 1:
            _u = e['film_list'][0]
            e['title'] = _u.get('title', e['title'])
            for _c in ('director', 'year', 'poster', 'posterSource', 'lbSlug',
                       'tmdb_id', 'synopsis', 'synopsis_lang', 'synopsis_en',
                       'country', 'flags'):
                if _u.get(_c):
                    e[_c] = _u[_c]
            if _u.get('duration'):
                e['duration'] = _u['duration']
            # La sinopsis promovida se lleva su idioma: sin `synopsis_lang`
            # la vista no sabe cuál texto mostrar ([paridad-derivados]).
            if e.get('synopsis') and not e.get('synopsis_lang'):
                e['synopsis_lang'] = 'es'
            e.pop('is_cortos', None); e.pop('film_list', None)
            e['_programa_original'] = f.get('titulo')

        films.append(lib.normaliza({k: v for k, v in e.items() if v not in (None, '', [], {})}, rep))
        venues[sede] = geo.get(sede, {'short': sede.split(' - ')[0], 'city': sede.split(' - ')[-1]})

    out = {'_etapa': plan.get('_etapa', 'build generado por pipeline/ensamblar.py'),
           '_provenance': lib.provenance(crudo['_provenance'].get('fuente', ''),
                                         ensamblador='pipeline/ensamblar.py')}
    out.update({k: v for k, v in cfg.items()
                if k not in ('crudo', 'enriquecido', 'geo', 'sedes', 'secciones',
                             'seccion_default', 'seccion_por_titulo', 'mes_es',
                             'posterSource_fuente')})
    out.update(lib.dias_config(dias, cfg.get('mes_es', '')) if dias else {})
    out['sections'] = secciones
    out['venues'] = venues
    out['films'] = films

    print(f'  {fid}: {len(films)} funciones · {len(venues)} sedes · {len(secciones)} secciones '
          f'· {len(dias)} días')
    if rep:
        print('  contrato aplicado:', dict(rep))
    if escribir:
        p = f'{REPO}/festivals/staging/{fid}-build.json'
        json.dump(out, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f'  → {p}')
    return out


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    ensamblar(sys.argv[1], escribir='--ver' not in sys.argv)
