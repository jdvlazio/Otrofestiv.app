#!/usr/bin/env python3
"""festicine-antioquia-2026-crudo.py — el catálogo → crudo: 79 funciones y actividades (24 nov 2026).

ACCESO: el PDF solo habla de los talleres («abierto al público general» / «con inscripción
previa», sin enlace). Ningún documento anuncia cobro → libre (docs en -acceso.json).
PRESENCIA: «Con presencia de…» = qa_type team (precedente BIFF: «con presencia del equipo»);
«Muestra especial y conversación» = Q&A.
ESTRENO: el PDF lo imprime en las dos funciones de «Ma, despierta» y «Fang i vidre»; va en
las dos, como lo dice el festival.
OBRAS que el festival proyecta dos veces: dos funciones de la misma obra.
"""
import io, json, os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance  # noqa: E402

CAT = f'{REPO}/festivals/staging/festicine-antioquia-2026-catalogo.json'
OUT = f'{REPO}/festivals/staging/festicine-antioquia-2026-crudo.json'
SEDE = {'U': ('Universidad de Antioquia Seccional Occidente', 'Auditorio'),
        'A': ('Universidad de Antioquia Seccional Occidente', 'Aula 201'),
        'M': ('Museo Juan del Corral', 'Auditorio'), 'H': ('Hotel Mariscal Robledo', 'Auditorio'),
        'C': ('Cámara de Comercio de Medellín para Antioquia', 'Auditorio'),
        'P': ('Plaza Mayor Simón Bolívar', ''),
        'K': ('Sede de empleo y emprendimiento Comfenalco Antioquia', ''),
        'E': ('Barrio La Esmeralda', ''), 'B': ('Barrio Llano de Bolívar', ''),
        'D': ('Catedral Basílica Metropolitana', '')}
KIND = {'Conversando de…': 'conversatorio', 'Tómate un café con…': 'encuentro', 'Taller': 'taller',
        'Conversando con los actores': 'conversatorio', 'Muestra cultural': 'evento'}
INSCRIPCION = 'Taller con inscripción previa'
PROGRAMA = {'Subterráneo + Pacífico': ['Subterráneo', 'Pacífico']}
# «Made to Shine» (5 min, Débora Arango, sin dirección en el PDF): con sus minutos el almacén la
# casaría con la de FICIDI (Mariana Gutiérrez, 8 min) y ninguna fuente dice que sean la misma.
TITLE_EN = {'Tres hermanas': 'Three Sisters', 'Akababuru': 'Akababuru: Expression of Astonishment',
            'Refracción': 'Refracción'}   # almacén
SIN_MIN = {'Made to Shine'}
CAMPOS = ('director', 'pais', 'anio', 'duracion_min', 'sinopsis', 'synopsis_en')


def obra(o):
    d = {'titulo': o['titulo'], **{k: o[k] for k in CAMPOS if o.get(k)}}
    if o['titulo'] in TITLE_EN:
        d['title_en'] = TITLE_EN[o['titulo']]
    if o['titulo'] in SIN_MIN:
        d.pop('duracion_min')
    g = {'Documental': 'Documental', 'Animación': 'Animación'}.get(o.get('categoria'))
    if g:
        d['genero'] = d['genre'] = g
    return d


def main():
    cat = json.load(io.open(CAT, encoding='utf-8'))
    obs = {o['titulo']: o for o in cat['obras']}
    progs = {}
    for o in cat['obras']:
        if o.get('programa'):
            progs.setdefault(o['programa'], []).append(o['titulo'])
    progs.update(PROGRAMA)
    out, usadas = [], set()
    for p in cat['parrilla']:
        assert '2026-12-04' <= p['dia'] <= '2026-12-08', 'solo días oficiales'
        sede, sala = SEDE[p['sede']]
        rot = p['rotulo']
        f = {'titulo': p['titulo'], 'dia': p['dia'], 'hora': p['hora'], 'sede': sede, 'seccion': rot,
             'acceso': 'Con inscripción previa. Entrada libre' if INSCRIPCION in p['nota'] else 'Entrada libre',
             '_src': {'url': cat['_provenance']['fuente'], 'date': '2026-11-24', 'tipo': 'festival-pdf'}}
        if sala:
            f['sala'] = sala
        if rot in KIND:
            f['event_kind'] = KIND[rot]
            if p['nota']:
                f['descripcion'] = p['nota']
        else:
            ts = progs.get(p['titulo']) or [p['titulo']]
            usadas |= set(ts)
            os_ = [obra(obs[t]) for t in ts]
            if len(os_) == 1:
                f.update({k: v for k, v in os_[0].items() if k != 'titulo'})
                if obs[ts[0]].get('premiere'):
                    f['premiere'] = obs[ts[0]]['premiere']
            else:
                f['obras'] = os_
                f['duracion_min'] = sum(obs[t]['duracion_min'] for t in ts)
            if p['nota']:
                f['has_qa'] = True
                if p['nota'] != 'conversación':
                    f['qa_type'] = 'team'
        out.append(f)
    assert usadas == set(obs), set(obs) ^ usadas     # cobertura inversa
    json.dump({'_provenance': provenance('PDF de programación vía festicine-antioquia-2026-catalogo.json'),
               'funciones': out}, io.open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{len(out)} funciones → {os.path.relpath(OUT, REPO)}')


if __name__ == '__main__':
    main()
