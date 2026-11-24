#!/usr/bin/env python3
"""ficfusa-2026-crudo.py — la programación de FICFUSA 2026 (11–16 nov, Fusagasugá) → crudo.

LA FUENTE es festivals/staging/ficfusa-2026-programacion-oficial.json: la
transcripción, entrada por entrada y con su `fuente`, de la web /programacion/ y
de los posts de IG del festival (un post por día: 6, 7, 8 y 10 nov; el del día
11, Dfma5V8EbTn, confirma el 11). El catálogo del pre-onboarding da director y
país de cada obra.

DECISIONES (11 nov 2026):
- El post más reciente manda (corregido en la transcripción, con su fuente):
  «El reto del audio inmersivo» a las 11:00 y «El espejo de la vida» a las 14:00.
- Sin sede no se publica: los dos talleres que la fuente deja «Por definir»
  van a `_fuera`.
- Sección = el formato que nombra el festival (Proyección, Proyección y
  conversatorio, Charla, Taller, Evento), tal cual.
- Duración = de la hora de inicio a la de fin que da la fuente.
- Faltan el 15 y el 16 nov: el festival no los ha publicado.
"""
import io
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import norm, provenance  # noqa: E402

PROG = f'{REPO}/festivals/staging/ficfusa-2026-programacion-oficial.json'
CATALOGO = f'{REPO}/festivals/staging/ficfusa-2026-catalogo.json'
OUT = f'{REPO}/festivals/staging/ficfusa-2026-crudo.json'

# formato de la fuente → (sección, event_kind; None = proyección)
FORMATO = {'Charla': ('Charla', 'charla'), 'Taller': ('Taller', 'taller'),
           'Taller - Laboratorio': ('Taller', 'taller'), 'Evento': ('Evento', 'evento')}
# Programas de varias obras: el nombre que les da la fuente (campo `nombre` de la
# transcripción, con su porqué), o el título que trae, o sus obras unidas con «y».
GENERICOS = {'Proyecciones', 'Proyección', 'Proyección y conversatorio'}
KIND = {'Masterclass: Actuación del subtexto y el lenguaje no verbal': 'masterclass',
        '¡Fiesta de los 13 años del FICFUSA!': 'fiesta',
        'Laboratorio Visual Experimental VIDEOFRAGMENTOS': 'taller'}


def y_lista(ts):
    return ts[0] if len(ts) == 1 else ', '.join(ts[:-1]) + ' y ' + ts[-1]


def mins(h):
    return int(h[:2]) * 60 + int(h[3:])


def seccion(f):
    if f['titulo'] in KIND:
        return {'masterclass': 'Taller', 'fiesta': 'Evento', 'taller': 'Taller'}[KIND[f['titulo']]], KIND[f['titulo']]
    if f.get('formato') in FORMATO:
        return FORMATO[f['formato']]
    if f['titulo'].startswith('Película de apertura'):
        return 'Película de apertura', None
    fmt = f.get('formato') or f['titulo']
    return ('Proyección y conversatorio' if 'onversatorio' in fmt or f.get('invitados') else 'Proyección'), None


def main():
    prog = json.load(io.open(PROG, encoding='utf-8'))
    cat = {norm(o['titulo']): o for o in json.load(io.open(CATALOGO, encoding='utf-8'))['obras']}
    funcs, fuera = [], []
    for f in prog['funciones']:
        if f['sede'] == 'Por definir':
            fuera.append({'titulo': f['titulo'], 'dia': f['fecha'], 'hora': f['hora'],
                          '_por_que': 'la fuente no da sede; sin sede no se publica', 'fuente': f.get('fuente')})
            continue
        hora, fin = f['hora'], f.get('fin')
        sec, kind = seccion(f)
        g = {'titulo': f['titulo'], 'dia': f['fecha'], 'hora': hora, 'sede': f['sede'], 'sala': '',
             'acceso': f.get('acceso') or 'Entrada gratuita', 'seccion': sec,
             '_src': {'url': (f.get('fuente') or prog['_provenance']['fuente']).split(' ')[0],
                      'nota': f.get('fuente') or 'web /programacion/', 'date': '2026-11-11'}}
        if fin and mins(fin) > mins(hora):
            g['duracion_min'] = mins(fin) - mins(hora)
            g['_duracion_de'] = f.get('_duracion_por_que') or 'de la hora de inicio a la de fin de la fuente'
        if f.get('invitados'):
            g['invitados'] = f['invitados']
        if sec == 'Proyección y conversatorio' or (sec == 'Película de apertura' and 'onversatorio' in f.get('invitados', '')):
            # la apertura también trae conversatorio (lámina del 13 nov, vigía 11 nov).
            # el PDF del 11 nov dice «proyección y conversatorio»: has_qa (regla del 1 nov).
            # La app le suma FESTIVAL_QA_MIN (30) a has_qa; si la franja ya lo incluye, se resta.
            g['has_qa'] = True
            if g.get('duracion_min', 0) > 30:
                g['duracion_min'] -= 30
                g['_duracion_de'] += ' (menos los 30 min del conversatorio, que la app suma por has_qa)'
        if kind:
            g.update(tipo='evento', event_kind=kind)
        obras = []
        for t in f.get('obras') or []:
            o = cat.get(norm(t))
            obras.append({k: o[k] for k in ('titulo', 'director', 'pais') if o.get(k)} if o else {'titulo': t})
        if obras and len(obras) > 1:
            g['titulo'] = f.get('nombre') or (f['titulo'] if f['titulo'] not in GENERICOS else None) or y_lista([o['titulo'] for o in obras])
        if len(obras) == 1 and not kind:
            g['titulo'] = obras[0]['titulo']
            g.update({k: v for k, v in obras[0].items() if k != 'titulo'})
        elif obras:
            g['obras'] = obras
        funcs.append(g)
    io.open(OUT, 'w', encoding='utf-8').write(json.dumps({
        '_provenance': provenance('FICFUSA: web /programacion/ + posts de IG del 6, 7, 8, 10 y 11 nov 2026',
                                  que_aporta='día, hora, sede y obras del 11 al 14 nov',
                                  metodo='la transcripción de ficfusa-2026-programacion-oficial.json'),
        '_acceso': {'estado': 'Entrada gratuita', 'revisado': '2026-11-11',
                    '_por_que': 'la programación es gratuita (nota de prensa DflgSQ8FDce); la fiesta del 14 pide aporte'},
        '_fuera': fuera, 'funciones': funcs}, ensure_ascii=False, indent=1) + '\n')
    print(f'✓ {len(funcs)} funciones ({len(fuera)} fuera) → {os.path.relpath(OUT, REPO)}')


if __name__ == '__main__':
    main()
