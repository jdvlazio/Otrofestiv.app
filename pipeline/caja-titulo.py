#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""caja-titulo.py [<fest-id> …] [--escribir] — programas y secciones en Título
sobre lo YA publicado (regla de Juan, 15 oct 2026; reglas en pipeline/caja.py).

Lo que se publique de acá en adelante ya sale en Título (ensamblar.py); esto es
para lo que está en producción. Por cada festival:
  · el título de cada programa (nunca el de una obra ni una unión «A + B»), con
    `titulos_anteriores` para que la app mueva lo que el usuario guardó bajo el
    nombre viejo (domain/titulos.js) — y, si el festival tiene pipeline, el
    renombre queda en su sidecar <fid>-titulos-anteriores.json, o el próximo
    montaje lo perdería;
  · la sección de cada función y obra, y las llaves de `sections`;
  · las llaves de esa sección en src/config.js (SECTION_ARCHETYPES y la
    traducción), por llave exacta entre comillas, nunca por texto suelto.
Sin --escribir solo muestra. Sin festivales, todos.
"""
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import caja  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _escribir_json(p, d):
    crudo = open(p, encoding='utf-8').read()
    if '\n' in crudo.strip():
        l2 = crudo.split('\n')[1]
        txt = json.dumps(d, ensure_ascii=False, indent=(len(l2) - len(l2.lstrip(' '))) or 1)
    else:
        txt = json.dumps(d, ensure_ascii=False, separators=(',', ':'))
    open(p, 'w', encoding='utf-8').write(txt + ('\n' if crudo.endswith('\n') else ''))


def aplicar(d, fid):
    """Renombra en `d`. Devuelve ({viejo: nuevo} de programas, {viejo: nuevo} de secciones)."""
    progs, secs = {}, {}
    for f in d.get('films') or []:
        if caja.es_programa(f):
            n = caja.titulo(f['title'])
            if n != f['title']:
                progs[f['title']] = n
                f['titulos_anteriores'] = sorted(set(f.get('titulos_anteriores') or []) | {f['title']})
                f['title'] = n
        for o in [f] + (f.get('film_list') or []):
            s = o.get('section')
            if s and caja.seccion(s) != s:
                secs[s] = caja.seccion(s)
                o['section'] = secs[s]
    if isinstance(d.get('sections'), dict):
        secs.update({k: caja.seccion(k) for k in d['sections'] if caja.seccion(k) != k})
        d['sections'] = {caja.seccion(k): v for k, v in d['sections'].items()}
    return progs, secs


def main():
    escribir = '--escribir' in sys.argv
    fids = [a for a in sys.argv[1:] if not a.startswith('--')] or \
        [os.path.basename(p)[:-5] for p in sorted(glob.glob(f'{REPO}/festivals/*.json'))]
    cfg_p = f'{REPO}/src/config.js'
    cfg = open(cfg_p, encoding='utf-8').read()
    total = 0
    for fid in fids:
        if fid in caja.OTRO_IDIOMA:
            continue
        p = f'{REPO}/festivals/{fid}.json'
        try:
            d = json.load(open(p, encoding='utf-8'))
        except Exception:
            continue
        progs, secs = aplicar(d, fid)
        if not progs and not secs:
            continue
        total += len(progs) + len(secs)
        print(f'{fid}: {len(progs)} programa(s), {len(secs)} sección(es)')
        for a, b in list(progs.items()) + list(secs.items()):
            print(f'   {a}  →  {b}')
        for a, b in secs.items():
            cfg = cfg.replace(f"'{a}':", f"'{b}':")
        if escribir:
            _escribir_json(p, d)
            if progs and os.path.exists(f'{REPO}/pipeline/{fid}.plan.json'):
                sp = f'{REPO}/festivals/staging/{fid}-titulos-anteriores.json'
                sd = json.load(open(sp, encoding='utf-8')) if os.path.exists(sp) else {
                    '_provenance': {'fuente': 'caja-titulo.py: programas en Título (regla de Juan)',
                                    'capturado': '2026-10-15'}, 'renombres': []}
                ya = {(r['antes'], r['ahora']) for r in sd['renombres']}
                sd['renombres'] += [{'antes': a, 'ahora': b, 'por_que': 'programa en Título (regla de Juan, 15 oct 2026)'}
                                    for a, b in progs.items() if (a, b) not in ya]
                json.dump(sd, open(sp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
                open(sp, 'a', encoding='utf-8').write('\n')
    if escribir and total:
        open(cfg_p, 'w', encoding='utf-8').write(cfg)
    print(f'{"✓" if total else "·"} {total} cambio(s)' + ('' if escribir else ' (solo muestra; --escribir para guardarlo)'))


if __name__ == '__main__':
    main()
