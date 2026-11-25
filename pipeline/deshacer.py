#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""deshacer.py — una decisión del almacén se puede echar atrás (paso 8 de docs/OBRA.md).

obra_unica.decidir guarda en `anteriores` cada valor que reemplaza. Deshacer vuelve al
último; si la decisión es la primera, la quita y devuelve a cada festival lo que
publicaba (`antes`). El sello de la obra se rompe: alguien tiene que volver a leerla.

    python3 pipeline/deshacer.py <work_id> <campo>               # muestra qué haría
    python3 pipeline/deshacer.py <work_id> <campo> --escribir
Después: ficha_unica / sinopsis_unicas / afiches_unicos --aplicar --escribir,
catalogo_construir.py --escribir y releer la obra (sello_obra.py).
"""
import copy
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
GUARDA = ('valor', 'motivo', 'fecha', 'quien', 'fuente', 'a_mano', 'vistas')


def recordar(d):
    """Antes de cambiar una decisión, guarda la que había."""
    if 'valor' in d:
        d.setdefault('anteriores', []).append({k: copy.deepcopy(d[k]) for k in GUARDA if k in d})


def deshacer(decs, festivales, w, campo):
    """→ (qué pasó, {festival}). Cambia `decs` y, si hace falta, `festivales` en el lugar."""
    import obra_unica
    d = next((x for x in reversed(decs) if x['work_id'] == w and x['campo'] == campo), None)
    if d is None:
        raise SystemExit(f'✗ {w} no tiene decisión de {campo}')
    if 'original' in d:
        raise SystemExit('✗ es una síntesis verificada: se cambia con sinopsis_cortas.py')
    if d.get('anteriores'):
        viejo = d['anteriores'].pop()
        for k in GUARDA:
            d.pop(k, None)
        d.update(viejo)
        if not d['anteriores']:
            del d['anteriores']
        return f'vuelve a {str(viejo["valor"])[:80]!r}', set()
    k, antes = next((p for p, c in obra_unica.CAMPO.items() if c == campo), None), d.get('antes') or {}
    no = ('es el alta de la obra: no hay nada antes; se decide otra cosa con obra_unica.py --decidir' if d.get('sembrada') else
          'no se guardó qué había antes' if k is None or not antes else
          'un afiche se decide de nuevo con obra_unica.py --decidir … --veredicto (no se guardó qué clase de imagen era)' if campo == 'afiche' else
          f'un festival publicaba varios: {[v for v in antes.values() if isinstance(v, list)]}; decidir cuál' if any(isinstance(v, list) for v in antes.values()) else None)
    i = next(n for n, x in enumerate(decs) if x is d)
    if any(x.get('reemplaza') == i for x in decs):
        no = no or 'otra decisión la reemplaza'
    import obra_fuente
    if any(obra_fuente.enrolado(f) for f in antes) or any(obra_fuente.enrolado(f) and any(o['work_id'] == w for o in obra_fuente._obras(x)) for f, x in festivales.items()):
        no = no or 'la publica un festival que se arma desde el almacén: sin decisión quedaría sin dueño'
    if no:
        raise SystemExit('✗ no se deshace: ' + no)
    tipo = int if k in ('year', 'tmdb_id') else str
    del decs[i]
    for x in decs:                                     # `reemplaza` es una posición
        if isinstance(x.get('reemplaza'), int) and x['reemplaza'] > i:
            x['reemplaza'] -= 1
    from lib import banderas
    import catalogo
    tocados = set()
    for fid, v in antes.items():
        for f in (festivales.get(fid) or {}).get('films') or []:
            for o in catalogo.obras_de(f):
                if o.get('work_id') == w:
                    o[k] = tipo(v)
                    if k == 'country' and banderas(v):
                        o['flags'] = banderas(v)
                    tocados.add(fid)
    return f'se quita la decisión; vuelve lo de {", ".join(sorted(tocados))}', tocados


if __name__ == '__main__':
    import catalogo
    import obra_unica
    from sinopsis_unicas import _guardar
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    if len(a) != 2:
        sys.exit(__doc__)
    decs, fs = catalogo.decisiones(), obra_unica._festivales()
    que, tocados = deshacer(decs, fs, *a)
    print(que)
    if '--escribir' in sys.argv:
        catalogo.escribir_decisiones(decs)
        for fid in tocados:
            _guardar(os.path.join(REPO, 'festivals', fid + '.json'), fs[fid])
    else:
        print('(solo muestra; --escribir para guardarlo)')
