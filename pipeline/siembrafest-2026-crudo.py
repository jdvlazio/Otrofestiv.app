# -*- coding: utf-8 -*-
"""Los crudos de los dos municipios → el crudo canónico.

SiembraFest 11 corre en Villeta (9–17) y Sasaima (14–18) con programaciones
SEPARADAS: de las 28 obras de Sasaima, ninguna se repite en Villeta. Cada
municipio tiene su PDF, su generador y su verificación; este paso solo los junta,
sin decidir nada, para que el ensamblador siga leyendo un único `-crudo.json`.

    python3 pipeline/siembrafest-2026-crudo.py
"""
import json, os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from lib import provenance                                          # noqa: E402

ST = f'{REPO}/festivals/staging'
PARTES = [('Villeta', f'{ST}/siembrafest-2026-villeta-crudo.json'),
          ('Sasaima', f'{ST}/siembrafest-2026-sasaima-crudo.json')]
SALIDA = f'{ST}/siembrafest-2026-crudo.json'

if __name__ == '__main__':
    funcs, resumen = [], []
    for ciudad, p in PARTES:
        if not os.path.exists(p):
            sys.exit(f'  ✗ falta {p} — corré primero el generador de {ciudad}')
        d = json.load(open(p, encoding='utf-8'))
        fs = d['funciones']
        funcs += fs
        resumen.append(f'{ciudad}: {len(fs)} funciones, '
                       f'{len({f["sede"] for f in fs})} sedes')
        print(f'  {ciudad:<8} {len(fs):>3} funciones · '
              f'{len({o["titulo"] for f in fs for o in f.get("obras") or []}):>3} obras')
    funcs.sort(key=lambda x: (x['dia'], x['hora'], x['sede']))
    # una sede en dos municipios sería un error de transcripción, no un dato
    sedes = {}
    for f in funcs:
        sedes.setdefault(f['sede'], set()).add(f['_src'])
    json.dump({'_provenance': provenance(
                 'PDF oficial de cada municipio — ' + ' · '.join(c for c, _ in PARTES),
                 metodo='unión de los crudos por municipio; cada uno verifica su propio PDF',
                 partes=' · '.join(resumen)),
               'funciones': funcs}, open(SALIDA, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(f'  → {len(funcs)} funciones · {len(sedes)} sedes · {SALIDA}')
