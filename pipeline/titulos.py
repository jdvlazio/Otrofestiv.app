#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""titulos.py: de los títulos que anuncia un festival, ¿cuáles ya tenemos? (24 nov 2026)

POR QUÉ (Juan): los títulos se suman en cuanto se anuncian. La obra que ya está en
el almacén trae su ficha; solo se investiga la nueva y después falta día, hora y lugar.

  EN ALMACÉN  catalogo.reconocer la da por la misma (título y dirección)
  CANDIDATA   título igual, o uno empieza con el otro y la dirección coincide: la
              decide una persona, nunca el programa
  NUEVA       no hay nada parecido: investigar hoy

Solo lee. Uso:
    python3 pipeline/titulos.py festicine-antioquia-2026      # su <id>-catalogo.json
    python3 pipeline/titulos.py lista.json                    # [{titulo, director, anio?, duracion_min?}]
"""
import io
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
import catalogo  # noqa: E402


def _palabras(t):
    return catalogo.re.sub(r'[^a-z0-9]+', ' ', catalogo.sinacento(t or '').lower()).split()


def candidatas(obs, titulo, director):
    h, w = catalogo.huella(titulo), _palabras(titulo)
    out = []
    if not h:
        return out
    for wid, o in obs.items():
        if not o.get('presentaciones'):
            continue
        ts = [o['titulo_original']] + [a['titulo'] for a in o.get('aliases') or []]
        persona = bool(director) and catalogo.misma_persona(director, ', '.join(o.get('directores') or []))
        if any(catalogo.huella(t) == h for t in ts):
            out.append((wid, 'mismo título' + (', misma dirección' if persona else '')))
        elif persona and any(w[:len(v)] == v or v[:len(w)] == w for v in map(_palabras, ts) if v):
            out.append((wid, 'título parecido, misma dirección'))
    return out


def clasificar(obs, lista):
    """{'almacen': [(título, wid)], 'candidata': [(título, [(wid, porqué)])], 'nueva': [título]}"""
    r = {'almacen': [], 'candidata': [], 'nueva': []}
    for x in lista:
        t, d = x.get('titulo') or x.get('title'), x.get('director') or ''
        wid, _ = catalogo.reconocer(obs, t, d, x.get('anio'), x.get('duracion_min'))
        if wid:
            r['almacen'].append((t, wid))
            continue
        c = candidatas(obs, t, d)
        r['candidata' if c else 'nueva'].append((t, c) if c else t)
    return r


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    a = sys.argv[1]
    p = a if a.endswith('.json') else os.path.join(REPO, 'festivals', 'staging', f'{a}-catalogo.json')
    d = json.load(io.open(p, encoding='utf-8'))
    obs = catalogo.obras()
    r = clasificar(obs, d['obras'] if isinstance(d, dict) else d)
    print(f"EN ALMACÉN {len(r['almacen'])} · CANDIDATAS {len(r['candidata'])} · NUEVAS {len(r['nueva'])}")
    for t, w in r['almacen']:
        print(f'  ✓ {t}  {w}')
    for t, c in r['candidata']:
        for w, por in c:
            print(f"  ¿ {t}  {w} «{obs[w]['titulo_original']}» de {', '.join(obs[w].get('directores') or ['?'])} ({por})")
    for t in r['nueva']:
        print(f'  + {t}')


if __name__ == '__main__':
    main()
