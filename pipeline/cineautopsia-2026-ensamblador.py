# -*- coding: utf-8 -*-
"""Fichas de la Cinemateca + TMDB → build publicable de CineAutopsia 2026.

MODELO: cada ficha de la Cinemateca es UN PROGRAMA que se vende como una
entrada, y las obras van dentro. Es el mismo modelo de los Short Cuts de TIFF
y de los programas de FICDEH: `is_cortos` + `film_list`, nunca una obra suelta
por corto.

LAS SECCIONES SON PALABRA DEL FESTIVAL, no invención nuestra: sus propios
títulos distinguen «destacados» de «panorama», y la última sesión es la
clausura. El emoji y el arquetipo son capa nuestra y los aprueba Juan.

LA SEDE SE HEREDA. «Cinemateca de Bogotá - Bogotá» ya está geocodificada y
verificada en FICDEH; volver a geocodificarla sería crear una segunda verdad
para el mismo lugar.

LO QUE ESTE FESTIVAL NO TIENE, y se declara en vez de disimularse: sinopsis
por obra (la Cinemateca solo publica la del programa) y póster por obra en 22
de 45. Es cine experimental de circuito: TMDB y Letterboxd cubren poco, y eso
no se arregla insistiendo.
"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import dias_config, provenance

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ST = f'{REPO}/festivals/staging'
TMDB_IMG = 'https://image.tmdb.org/t/p/w500'
SEDE = 'Cinemateca de Bogotá - Bogotá'

# PROPUESTA de emoji + arquetipo — pendiente de aprobación de Juan.
SECCIONES = {
    'Destacados': ('🔬', 'Competencia'),
    'Panorama':   ('🌀', 'Muestra / País'),
    'Clausura':   ('🎬', 'Clausura'),
}

PAIS_FLAG = None   # se toma la tabla de la app, dueño único


def seccion(titulo):
    t = titulo.lower()
    if 'clausura' in t or 'premiaci' in t: return 'Clausura'
    if 'destacado' in t: return 'Destacados'
    if 'panorama' in t: return 'Panorama'
    return 'Panorama'


def tabla_flags():
    js = open(f'{REPO}/src/controller/sheets-controller.js', encoding='utf-8').read()
    m = re.search(r'const _COUNTRY_FLAGS=\{(.*?)\};', js, re.S)
    return dict(re.findall(r"'([^']+)'\s*:\s*'([^']+)'", m.group(1))) if m else {}


def main():
    cin = json.load(open(f'{ST}/cineautopsia-2026-cinemateca.json', encoding='utf-8'))['programas']
    enr = {o['titulo']: o for o in
           json.load(open(f'{ST}/cineautopsia-2026-tmdb.json', encoding='utf-8'))['obras']}
    geo = json.load(open(f'{REPO}/festivals/ficdeh-2026.json', encoding='utf-8'))['venues'][SEDE]
    TAB = tabla_flags()

    def flags(p):
        out = []
        for x in re.split(r'[,/()]', p or ''):
            f = TAB.get(x.strip())
            if f and f not in out: out.append(f)
        return ''.join(out)

    dias = sorted({p['dia'] for p in cin if p.get('dia')})
    orden = {d: i for i, d in enumerate(dias)}
    films, secs_vistas = [], set()

    for p in cin:
        sec = seccion(p['programa']); secs_vistas.add(sec)
        emoji, _arq = SECCIONES[sec]
        lista = []
        for o in p['obras']:
            e = enr.get(o['titulo'], {})
            lista.append({k: v for k, v in {
                'title': o['titulo'], 'director': o['director'],
                'year': o['anio'], 'duration': f'{o["duracion_min"]} min',
                'country': o['pais'], 'flags': flags(o['pais']),
                'synopsis': e.get('sinopsis'), 'synopsis_lang': 'es' if e.get('sinopsis') else None,
                'lbSlug': e.get('lbSlug'), 'tmdb_id': e.get('tmdb_id'),
                'poster': TMDB_IMG + e['poster_tmdb'] if e.get('poster_tmdb') else None,
                'posterSource': 'tmdb' if e.get('poster_tmdb') else None,
            }.items() if v not in (None, '', [], {})})

        paises = ', '.join(dict.fromkeys(c.strip() for o in p['obras']
                                         for c in o['pais'].split(',') if c.strip()))
        films.append({k: v for k, v in {
            'title': p['programa'], 'type': 'film',
            'duration': f'{p["duracion_min"]} min' if p.get('duracion_min') else None,
            'country': paises or None, 'flags': flags(paises),
            'section': f'{emoji} {sec}',
            'synopsis': p.get('sinopsis'), 'synopsis_lang': 'es' if p.get('sinopsis') else None,
            'poster': p.get('poster'), 'posterSource': 'editorial' if p.get('poster') else None,
            'day': p.get('dia'), 'time': p.get('hora'), 'day_order': orden.get(p.get('dia')),
            'venue': SEDE, 'sala': '',
            'rating': p.get('clasificacion'), 'language': p.get('idioma'),
            'is_cortos': bool(lista), 'film_list': lista or None,
            'is_free': False, 'requires_registration': False,
            'has_qa': False,
            '_src': {'url': p['_src'], 'fuente': 'agenda de la Cinemateca de Bogotá'},
        }.items() if v not in (None, '', [], {})})

    out = {
        '_provenance': provenance('cineautopsia-2026-cinemateca + cineautopsia-2026-tmdb',
                                  metodo='programas como is_cortos+film_list; sede heredada de FICDEH'),
        'name': 'CineAutopsia',
        'fullName': 'CineAutopsia — Festival de Cine Experimental de Bogotá',
        'city': 'Bogotá', 'country': 'CO',
        'dates': f'{int(dias[0][-2:])}–{int(dias[-1][-2:])} AGO',
        'dates_en': f'AUG {int(dias[0][-2:])}–{int(dias[-1][-2:])}',
        'year': 2026, 'timezoneOffset': '-05:00',
        'storageKey': 'cineautopsia2026_',
        'festivalStartStr': f'{dias[0]}T00:00:00', 'festivalEndStr': f'{dias[-1]}T23:59:00',
        **dias_config(dias, mes_es='agosto'),
        'prioLimit': max(3, min(8, round(len(dias) / 2))),
        'sharedSlotIsOneScreening': False,
        'sections': {f'{SECCIONES[s][0]} {s}': {'en': s, 'archetype': SECCIONES[s][1],
                                                'order': i}
                     for i, s in enumerate(['Destacados', 'Panorama', 'Clausura'], 1)
                     if s in secs_vistas},
        'venues': {SEDE: geo},
        'films': films,
    }
    p = f'{ST}/cineautopsia-2026-build.json'
    json.dump(out, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    cortos = [c for f in films if f.get('film_list') for c in f['film_list']]
    print(f'── {p}')
    print(f'   programas {len(films)} · obras dentro {len(cortos)} · secciones {len(out["sections"])}')
    print(f'   días {len(dias)} ({dias[0]} → {dias[-1]}) · sede 1 · prioLimit {out["prioLimit"]}')
    print(f'   cortos con póster {sum(1 for c in cortos if c.get("poster"))}/{len(cortos)} · '
          f'lbSlug {sum(1 for c in cortos if c.get("lbSlug"))}/{len(cortos)} · '
          f'sinopsis {sum(1 for c in cortos if c.get("synopsis"))}/{len(cortos)}')


if __name__ == '__main__':
    main()
