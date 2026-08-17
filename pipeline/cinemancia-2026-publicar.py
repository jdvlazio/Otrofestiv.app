# -*- coding: utf-8 -*-
"""Build de staging → JSON publicable `festivals/cinemancia-2026.json`.

Mismo criterio que los publicadores de FICDEH y TIFF, y por el mismo motivo:
barrer todo lo que empieza por `_` se lleva por delante datos que los gates
leen AQUÍ, en el publicado, no en el staging.

CONSERVAR `_src` (procedencia por film, la exige [sin-procedencia]) y `_nota`
(la sede a <60 m de otra, que es donde [sedes-apiladas] la busca).

Y una corrección de nombre al pasar: el build emite `tmdbId` en camelCase, pero
el resto del proyecto usa `tmdb_id`. No es cosmético — el guardián
[campo-contrato] (17 ago 2026) existe justo por esto: en TIFF emití `ticketUrl`
donde la app lee `ticket_url` y 638 enlaces de boletería quedaron invisibles.
Aquí `tmdb_id` no lo lee la vista, pero que dos festivales llamen distinto al
mismo dato es la grieta por la que se cuela el siguiente error.
"""
import json, os, collections

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = f'{REPO}/festivals/staging/cinemancia-2026-build.json'
OUT = f'{REPO}/festivals/cinemancia-2026.json'
CONSERVAR = {'_src', '_pendiente', '_inherited', '_nota'}
RENOMBRA = {'tmdbId': 'tmdb_id'}
# Un campo VACÍO no es «sin dato»: es una promesa rota. `poster:""` hace que la
# app crea que hay imagen y pinte un hueco, y por eso [poster-empty-film] lo
# bloquea salvo en programas de cortos (POSTERS.md §6). Once obras de Cinemancia
# —cortos experimentales y de archivo— no tienen afiche en TMDB ni en ninguna
# fuente: el estado honesto es SIN CAMPO, no con el campo en blanco.
VACIABLES = {'poster', 'posterSource', 'lbSlug', 'synopsis_en', 'title_en'}


def limpio(d):
    out = {}
    for k, v in d.items():
        if k.startswith('_') and k not in CONSERVAR:
            continue
        if k in VACIABLES and (v is None or (isinstance(v, str) and not v.strip())):
            continue                      # el campo se OMITE, no se emite vacío
        out[RENOMBRA.get(k, k)] = v
    return out


def main():
    b = json.load(open(BUILD, encoding='utf-8'))
    out = {k: v for k, v in b.items() if k not in ('films', 'venues', 'sections', 'id')}
    out['sections'] = {k: limpio(v) for k, v in b['sections'].items()}
    out['venues'] = {k: limpio(v) for k, v in b['venues'].items()}
    out['films'] = [limpio(dict(f, film_list=[limpio(x) for x in f['film_list']])
                           if f.get('film_list') else f) for f in b['films']]

    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False,
              separators=(',', ':'))

    sin_src = [f['title'] for f in out['films'] if not f.get('_src')]
    print(f'{OUT}  {os.path.getsize(OUT)//1024} KB')
    print(f'  films {len(out["films"])} · venues {len(out["venues"])} '
          f'· secciones {len(out["sections"])}')
    print(f'  _provenance en root: {"_provenance" in out} · films sin _src: {len(sin_src)}')
    print(f'  sedes sin coordenada: '
          f'{[k for k, v in out["venues"].items() if not v.get("lat")] or "ninguna"}')
    print(f'  tmdbId residual: {sum(1 for f in out["films"] if "tmdbId" in f)}')


if __name__ == '__main__':
    main()
