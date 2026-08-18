# -*- coding: utf-8 -*-
"""Build → `festivals/cineautopsia-2026.json`. Mismo criterio que los demás.

CONSERVAR `_src` (lo exige [sin-procedencia]) y `_nota`. Los campos vacíos NO
se emiten: un `poster:""` hace que la app crea que hay imagen y pinte un hueco
(lección de Cinemancia, [poster-empty-film]).
"""
import json, os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = f'{REPO}/festivals/staging/cineautopsia-2026-build.json'
OUT = f'{REPO}/festivals/cineautopsia-2026.json'
CONSERVAR = {'_src', '_pendiente', '_inherited', '_nota'}


def limpio(d):
    return {k: v for k, v in d.items()
            if (not k.startswith('_') or k in CONSERVAR)
            and v not in (None, '', [], {})}


def main():
    b = json.load(open(BUILD, encoding='utf-8'))
    out = {k: v for k, v in b.items() if k not in ('films', 'venues', 'sections')}
    out['sections'] = {k: limpio(v) for k, v in b['sections'].items()}
    out['venues'] = {k: limpio(v) for k, v in b['venues'].items()}
    out['films'] = [limpio(dict(f, film_list=[limpio(x) for x in f['film_list']])
                           if f.get('film_list') else f) for f in b['films']]
    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(f'{OUT}  {os.path.getsize(OUT)//1024} KB')
    print(f'  films {len(out["films"])} · venues {len(out["venues"])} · secciones {len(out["sections"])}')
    print(f'  films sin _src: {sum(1 for f in out["films"] if not f.get("_src"))}')


if __name__ == '__main__':
    main()
