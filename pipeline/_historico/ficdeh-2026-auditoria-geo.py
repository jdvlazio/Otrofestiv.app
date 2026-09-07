# -*- coding: utf-8 -*-
"""Auditoría cruzada del geocoding de FICDEH.

No basta con que una sede tenga coordenadas: el pase v1 las tenía todas y 63
estaban mal. Aquí cada sede se resuelve DOS veces por vías independientes —
por NOMBRE (Photon, POI) y por DIRECCIÓN postal (Nominatim, vía) — y se
comparan:

  OK        ambas vías coinciden (< 600 m): dos fuentes independientes de
            acuerdo, confianza alta.
  UNA SOLA  solo una vía respondió: no hay con qué contrastar.
  DISCREPA  ambas respondieron y están lejos: una de las dos miente → a mano.

Las sedes marcadas `_prec: manual` ya se verificaron en Google Maps una a una
(dirección de la ficha == dirección del festival) y se reportan aparte.

Salida: `festivals/staging/ficdeh-2026-geo-auditoria.json` + informe por consola.
"""
import json, time, math, collections, os, importlib.util

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEO = f'{REPO}/festivals/staging/ficdeh-2026-venues-geo.json'
PROG = f'{REPO}/festivals/staging/ficdeh-2026-programacion-oficial.json'
OUT = f'{REPO}/festivals/staging/ficdeh-2026-geo-auditoria.json'
CERCA_M = 600
VENTANA = {f'2026-08-{d}' for d in range(12, 20)}

spec = importlib.util.spec_from_file_location('geo', f'{REPO}/pipeline/_historico/ficdeh-2026-geocode.py')
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)


def main():
    geo = json.load(open(GEO, encoding='utf-8'))
    prog = json.load(open(PROG, encoding='utf-8'))['funciones']
    n = collections.Counter()
    dirs = {}
    for f in prog:
        if f.get('en_app') and f['dia'] in VENTANA:
            k = f"{f['sede']} - {f['ciudad']}"
            n[k] += 1
            d = (f.get('direccion') or '').strip()
            if d and not dirs.get(k):
                dirs[k] = d

    res = {}
    stats = collections.Counter()
    for i, k in enumerate(sorted(n, key=lambda x: -n[x]), 1):
        v = geo.get(k, {})
        ciudad = v.get('city')
        if v.get('_prec') in ('manual', 'alias'):
            stats[v['_prec']] += 1
            res[k] = {'estado': v['_prec'], 'funciones': n[k]}
            continue

        por_nombre = G.photon(v.get('short', ''), ciudad); time.sleep(1.1)
        por_dir = None
        if dirs.get(k):
            d = G.normaliza_dir(dirs[k])
            if d:
                por_dir = G.nominatim(f'{d}, {ciudad}, Colombia', ciudad, exigir_dir=dirs[k])
                time.sleep(1.1)

        if por_nombre and por_dir:
            dist = G.km((por_nombre[0], por_nombre[1]), (por_dir[0], por_dir[1])) * 1000
            estado = 'OK' if dist <= CERCA_M else 'DISCREPA'
        elif por_nombre or por_dir:
            estado = 'UNA SOLA'
            dist = None
        else:
            estado = 'SIN FUENTE'
            dist = None

        stats[estado] += 1
        res[k] = {'estado': estado, 'funciones': n[k], 'usado': [v.get('lat'), v.get('lng')],
                  'prec': v.get('_prec'), 'dist_m': round(dist) if dist else None,
                  'por_nombre': por_nombre[:2] if por_nombre else None,
                  'por_direccion': por_dir[:2] if por_dir else None,
                  'direccion': dirs.get(k, '')}
        marca = {'OK': '  ', 'DISCREPA': '⚠️', 'UNA SOLA': ' ·', 'SIN FUENTE': '⚠️'}[estado]
        extra = f'{dist:6.0f} m' if dist is not None else '        '
        print(f'[{i:3}] {marca} {n[k]:3}f {estado:10} {extra}  {k[:52]}', flush=True)

    json.dump(res, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'\nRESUMEN: {dict(stats)}')
    revisar = [(k, r) for k, r in res.items() if r['estado'] in ('DISCREPA', 'SIN FUENTE')]
    if revisar:
        print(f'\nA REVISAR A MANO ({len(revisar)}), por peso:')
        for k, r in sorted(revisar, key=lambda x: -x[1]['funciones']):
            print(f"   {r['funciones']:3}f {k[:56]:57} {r.get('dist_m') or '?'} m  «{r.get('direccion','')[:34]}»")


if __name__ == '__main__':
    main()
