#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""heredar.py <fest-id> [--escribir] — lo que el catálogo ya sabe, sobre el
JSON PUBLICADO de un festival que no tiene pipeline (15 oct 2026).

POR QUÉ. Los festivales montados a mano antes de la v2 (FICMontañas, Cinemancia
2025…) no tienen `correr.py`: no se pueden re-armar, así que la herencia del
catálogo (enriquecer.py) nunca les llega. El guardián [dato-que-no-viaja] los
mide —FICMontañas: 88 datos que otro festival nuestro ya publicó— y nada los
saldaba. Las REGLAS son las de enriquecer.py, no una copia: las dos llaman a
herencia.valor().

QUÉ HACE. Por cada presentación con `work_id` (obra suelta o dentro de un
programa) llena SOLO lo vacío —lo publicado manda— con el valor único del
catálogo, y anota de dónde vino en `_src.heredado`. Sin --escribir solo muestra
el diff campo por campo; con --escribir lo guarda. Después: correr
`python3 pipeline/catalogo.py --medir` para bajar el techo del festival.

    python3 pipeline/heredar.py ficmontanas-2026
    python3 pipeline/heredar.py ficmontanas-2026 --escribir
    python3 pipeline/heredar.py ficci-65 --sin=poster   # un campo que no se hereda

`--sin` deja afuera los campos que la hoja de contacto rechazó (Trizas en FICCI:
el afiche de TMDB es un rostro sin título ni créditos, no un afiche).

Para festivales CON pipeline no se usa: se re-arman (correr.py), que hereda en
su paso de enriquecido y no se pierde en el próximo montaje.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import catalogo  # noqa: E402
import herencia  # noqa: E402

REPO = herencia.REPO


def _vacio(o, pub):
    if pub == 'poster':
        # un fotograma (editorial) cuenta como vacío para el guardián, pero no
        # se pisa: lo que se publicó se cambia con criterio, no por herencia
        return not o.get('poster')
    return not str(o.get(pub) or '').strip()


def heredar(d, fid, obs, key=None, sin=()):
    """Llena `d` en el lugar. Devuelve [(título, campo, valor, de)]."""
    cambios = []
    for f in d.get('films', []):
        if f.get('type') == 'event':
            continue
        for o in (f.get('film_list') or [f]):
            w = obs.get(o.get('work_id') or '')
            if not w or o.get('type') == 'event':
                continue
            de = f'catálogo {w["id"]} ({", ".join(w.get("presentaciones") or [])})'
            for campo, pub in herencia.CAMPOS.items():
                if pub in sin or not _vacio(o, pub):
                    continue
                if campo == 'synopsis_es' and (o.get('synopsis') or '').strip():
                    continue
                v = herencia.valor(w, campo, fid, o.get('title') or '', o.get('tmdb_id'), key,
                                   obra={'director': o.get('director'), 'anio': o.get('year')})
                if not v:
                    continue
                o[pub] = f'{v} min' if pub == 'duration' else v
                if campo == 'synopsis_es':
                    o['synopsis_lang'] = 'es'
                if campo == 'poster':
                    o['posterSource'] = herencia.poster_source(w, v)
                src = o.get('_src') if isinstance(o.get('_src'), dict) else (
                    {'fuente': o['_src']} if o.get('_src') else {})
                src.setdefault('heredado', {})[pub] = de
                o['_src'] = src
                cambios.append((o.get('title'), pub, v, de))
    return cambios


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args:
        sys.exit(__doc__)
    fid = args[0]
    p = os.path.join(REPO, 'festivals', f'{fid}.json')
    if not os.path.exists(p):
        sys.exit(f'✗ no existe {os.path.relpath(p, REPO)}')
    if os.path.exists(os.path.join(REPO, 'pipeline', f'{fid}.plan.json')):
        sys.exit(f'✗ {fid} tiene pipeline: re-armalo con correr.py (hereda en el enriquecido '
                 'y no se pierde en el próximo montaje)')
    d = json.load(open(p, encoding='utf-8'))
    sin = {c for a in sys.argv if a.startswith('--sin=') for c in a[6:].split(',') if c}
    cambios = heredar(d, fid, catalogo.obras(), os.environ.get('TMDB_API_KEY'), sin)
    for t, c, v, de in cambios:
        print(f'  «{t}» · {c} ← {str(v)[:70]}{"…" if len(str(v)) > 70 else ""}   [{de}]')
    print(f'{"✓" if cambios else "·"} {fid}: {len(cambios)} dato(s) heredado(s)')
    if cambios and '--escribir' in sys.argv:
        # LA FORMA DEL ARCHIVO SE RESPETA: unos festivales están en una línea y
        # otros indentados (Olhar, Leviza). Reescribirlos compactos hacía un diff
        # de miles de líneas que tapaba los pocos datos heredados
        crudo = open(p, encoding='utf-8').read()
        if '\n' in crudo.strip():
            sangria = len(crudo.split('\n')[1]) - len(crudo.split('\n')[1].lstrip(' '))
            txt = json.dumps(d, ensure_ascii=False, indent=sangria or 1)
        else:
            txt = json.dumps(d, ensure_ascii=False, separators=(',', ':'))
        open(p, 'w', encoding='utf-8').write(txt + ('\n' if crudo.endswith('\n') else ''))
        print(f'  escrito {os.path.relpath(p, REPO)} — ahora: python3 pipeline/catalogo.py --medir')
    elif cambios:
        print('  (solo muestra; --escribir para guardarlo)')


if __name__ == '__main__':
    main()
