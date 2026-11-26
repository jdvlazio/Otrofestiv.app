#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""obra_al_dia.py — lo que cada festival publica de una obra es lo que dice la obra.

POR QUÉ (revisión senior, 25 nov 2026): los festivales del legado publicaban 274 direcciones
y 100 años distintos de los de su obra en catalogo/obras, y nada lo veía. Una mutación de
prueba —el país de una obra brasileña cambiado a «Kazajistán», el afiche de una obra cambiado
por el de otra— pasó todo validate.py.

REGLA: cada presentación que no coincide con su obra se anota por identidad (festival, obra,
campo y valor publicado). Un festival que ya sale del almacén (no está en
catalogo/obra-fuente-legado.json) no tiene ninguna. En el legado, toda diferencia que no esté
anotada frena (pipeline/obra-al-dia-deuda.json, solo baja): arreglar una no deja estropear otra.

Límite: catalogo_construir.py --escribir arma la obra con lo que publica un festival cuando
nadie decidió nada (obra en un solo festival): ahí la cuenta no ve un dato falso, solo uno
que diverge. Lo que lo cierra es decidir la obra (obra_fuente.py --sembrar).

    python3 pipeline/obra_al_dia.py              # las cuentas de hoy
    python3 pipeline/obra_al_dia.py --congelar   # bajar la deuda
"""
import glob
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
DEUDA = os.path.join(REPO, 'pipeline', 'obra-al-dia-deuda.json')
CAMPOS = ('director', 'year', 'country', 'poster', 'tmdb_id', 'lbSlug')


def _norm(campo, v):
    import catalogo
    if v in (None, '', []):
        return None
    if campo == 'director':
        return tuple(sorted(catalogo.normalizar(x) if hasattr(catalogo, 'normalizar') else ' '.join(str(x).lower().split())
                            for x in (v if isinstance(v, list) else str(v).split(','))))
    if campo == 'country':
        from fichas_iso import iso
        try:
            return tuple(sorted(v if isinstance(v, list) else iso(v)))
        except ValueError:
            return ('?', str(v))
    if campo == 'poster':
        return (v.get('archivo') if isinstance(v, dict) else v)
    return str(v)


def de_la_obra(o):
    return {'director': o.get('directores'), 'year': o.get('anio'), 'country': o.get('paises'),
            'poster': o.get('afiche'), 'tmdb_id': (o.get('xref') or {}).get('tmdb'), 'lbSlug': (o.get('xref') or {}).get('letterboxd')}


def diferencias(festivales=None, obras=None):
    """→ {'festival|obra|campo|valor'} de presentaciones que publican otra cosa que su obra."""
    out = set()
    for fid, w, c, v in _recorrer(festivales, obras):
        out.add(f'{fid}|{w}|{c}|{json.dumps(v, ensure_ascii=False, sort_keys=True)}')
    return out


def cuentas(festivales=None, obras=None):
    """→ {festival: {campo: n}}."""
    out = {}
    for fid, _, c, _ in _recorrer(festivales, obras):
        out.setdefault(fid, {}).setdefault(c, 0)
        out[fid][c] += 1
    return out


def _recorrer(festivales=None, obras=None):
    import catalogo
    if festivales is None:
        from obra_unica import _festivales
        festivales = _festivales()
    if obras is None:
        obras = {}
        for p in glob.glob(os.path.join(REPO, 'catalogo', 'obras', '*.json')):
            with open(p, encoding='utf-8') as fh:
                o = json.load(fh)
            obras[o['id']] = o
    for fid, d in sorted(festivales.items()):
        for f in (d or {}).get('films') or []:
            for p in catalogo.obras_de(f):
                o = obras.get(p.get('work_id'))
                if not o:
                    continue
                ob = de_la_obra(o)
                for c in CAMPOS:
                    a = _norm(c, p.get(c))
                    if a is not None and a != _norm(c, ob[c]):
                        yield fid, p['work_id'], c, p.get(c)


def _leer():
    if not os.path.exists(DEUDA):
        return set()
    with open(DEUDA, encoding='utf-8') as fh:
        return set(json.load(fh).get('diferencias', []))


def problemas(festivales=None, obras=None, deuda=None, legado=None):
    """→ [texto] de lo que sube o de festivales del almacén que no dan cero."""
    if legado is None:
        import obra_fuente
        legado = obra_fuente.legado()
    deuda = _leer() if deuda is None else deuda
    mal = []
    for x in sorted(diferencias(festivales, obras)):
        fid, w, c, v = x.split('|', 3)
        if fid not in legado or x not in deuda:
            mal.append(f'{fid} · {w} · {c}: publica {v[:60]}, distinto de su obra')
    return mal


def autoprueba():
    """[] = la regla ve."""
    o = {'id': 'w_1', 'directores': ['Ana Pérez'], 'anio': 2020, 'paises': ['BR'], 'afiche': {'archivo': '/a.jpg'}, 'xref': {'tmdb': 7}}
    p = {'type': 'film', 'title': 'X', 'work_id': 'w_1', 'director': 'Ana Pérez', 'year': 2020, 'country': 'Brasil', 'poster': '/a.jpg', 'tmdb_id': 7}
    f = lambda **k: {'a': {'films': [dict(p, **k)]}}
    mal = []
    if problemas(f(), {'w_1': o}, {}, set()):
        mal.append('frena lo que coincide')
    for k in ({'country': 'Kazajistán'}, {'poster': '/b.jpg'}, {'director': 'Otra Persona'}, {'year': 1999}, {'tmdb_id': 8}):
        if not problemas(f(**k), {'w_1': o}, {}, set()):
            mal.append(f'no ve {k}')
    anotada = diferencias(f(year=1999), {'w_1': o})
    if problemas(f(year=1999), {'w_1': o}, anotada, {'a'}):
        mal.append('frena una diferencia anotada del legado')
    if not problemas(f(year=1999), {'w_1': o}, anotada, set()):
        mal.append('deja pasar un festival del almacén que no da cero')
    if not problemas(f(year=1998), {'w_1': o}, anotada, {'a'}):
        mal.append('deja cambiar una diferencia anotada por otra')
    return mal


if __name__ == '__main__':
    c = cuentas()
    if '--congelar' in sys.argv:
        mal = problemas() if os.path.exists(DEUDA) else []      # la primera vez se anota lo que hay
        if mal:
            sys.exit('✗ la deuda solo baja:\n  ' + '\n  '.join(mal))
        with open(DEUDA, 'w', encoding='utf-8') as fh:
            json.dump({'_nota': 'Presentaciones que publican otra cosa que su obra (pipeline/obra_al_dia.py): festival|obra|campo|valor. Solo baja.',
                       'diferencias': sorted(diferencias())}, fh, ensure_ascii=False, indent=1)
    tot = {}
    for cs in c.values():
        for k, n in cs.items():
            tot[k] = tot.get(k, 0) + n
    print(len(c), 'festivales con diferencias ·', tot)
    for x in problemas():
        print('✗', x)
