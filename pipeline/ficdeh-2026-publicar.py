# -*- coding: utf-8 -*-
"""Build de staging → JSON publicable `festivals/ficdeh-2026.json`.

Existe como script y no como una línea suelta porque el filtrado de claves
privadas es donde se pierden datos en silencio: barrer todo lo que empieza por
`_` se lleva por delante `_src`, y el gate `[sin-procedencia]` exige uno por
film («dato sin fuente = dato no confiable», docs/FESTIVAL-CHECKLIST.md).

CONSERVAR: `_src` (procedencia, obligatoria) · `_pendiente` (marca de dato que
la fuente no publica) · `_inherited` (procedencia por campo) · `_nota` (sede a
<60 m de otra ya revisada a mano: el guardián [sedes-apiladas] la lee AQUÍ, en
el publicado, así que si se filtra la nota no puede existir y el aviso no hay
manera de cerrarlo).
DESCARTAR: notas de trabajo del ensamblador — el ingreso crudo ya está
derivado a is_free/requires_registration, y las marcas de geocoding viven en
su sidecar.
"""
import json, os, collections

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = f'{REPO}/festivals/staging/ficdeh-2026-build.json'
OUT = f'{REPO}/festivals/ficdeh-2026.json'

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
    priv = collections.Counter(k for f in out['films'] for k in f if k.startswith('_'))
    print(f'{OUT}  {os.path.getsize(OUT)//1024} KB')
    print(f'  films {len(out["films"])} · venues {len(out["venues"])} · secciones {len(out["sections"])}')
    print(f'  _provenance en root: {"_provenance" in out} · films sin _src: {len(sin_src)}')
    print(f'  claves privadas conservadas: {dict(priv)}')
    if sin_src:
        print('  ⚠️ SIN PROCEDENCIA:', sin_src[:5])


if __name__ == '__main__':
    main()
