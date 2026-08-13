# -*- coding: utf-8 -*-
"""Build de staging → JSON publicable `festivals/tiff-2026.json`.

Mismo criterio que el publicador de FICDEH, y por el mismo motivo: barrer todo
lo que empieza por `_` se lleva por delante datos que los gates leen AQUÍ, en
el publicado, no en el staging.

CONSERVAR `_src` (procedencia por film, la exige [sin-procedencia]) y `_nota`
(la sede a <60 m de otra, que es donde [sedes-apiladas] la busca: si se filtra,
la nota no puede existir y el aviso no hay manera de cerrarlo).
"""
import json, os, collections

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = f'{REPO}/festivals/staging/tiff-2026-build.json'
OUT = f'{REPO}/festivals/tiff-2026.json'
CONSERVAR = {'_src', '_pendiente', '_inherited', '_nota'}


def limpio(d):
    return {k: v for k, v in d.items() if not k.startswith('_') or k in CONSERVAR}


def main():
    b = json.load(open(BUILD, encoding='utf-8'))
    out = {k: v for k, v in b.items() if k not in ('films', 'venues', 'sections')}
    out['sections'] = {k: limpio(v) for k, v in b['sections'].items()}
    out['venues'] = {k: limpio(v) for k, v in b['venues'].items()}
    out['films'] = [limpio(f) for f in b['films']]

    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False,
              separators=(',', ':'))

    sin_src = [f['title'] for f in out['films'] if not f.get('_src')]
    print(f'{OUT}  {os.path.getsize(OUT)//1024} KB')
    print(f'  films {len(out["films"])} · venues {len(out["venues"])} '
          f'· secciones {len(out["sections"])}')
    print(f'  _provenance en root: {"_provenance" in out} · films sin _src: {len(sin_src)}')
    sin_geo = [k for k, v in out['venues'].items() if not v.get('lat')]
    print(f'  sedes sin coordenada: {sin_geo or "ninguna"}')


if __name__ == '__main__':
    main()
