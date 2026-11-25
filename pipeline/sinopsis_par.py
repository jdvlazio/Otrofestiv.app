#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sinopsis_par.py — la sinopsis se lee en español Y en inglés.

Juan, 24 nov 2026: «me molestaba mucho cuando no aparecía en español porque se
tenía en inglés y no había traducción». Ese día: 1.651 obras con las dos, 480
sin inglés, 77 sin español.

REGLA: si una obra publica sinopsis en un idioma, la publica en el otro, en cada
festival. Sin ninguna no incumple (no hay de dónde traducir;
que no se pierdan lo mira [sinopsis-cobertura]). Deuda por obra y
festival en sinopsis-par-deuda.json: solo baja; un festival nuevo parte de cero.

    python3 pipeline/sinopsis_par.py [<festival>]    # qué falta
    python3 pipeline/sinopsis_par.py --congelar      # bajar la deuda
"""
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
DEUDA = os.path.join(REPO, 'pipeline', 'sinopsis-par-deuda.json')


def _hay(v):
    return isinstance(v, str) and bool(v.strip())


def falta(o):
    """Idiomas que le faltan a una obra publicada: [] | ['en'] | ['es'] | ['es', 'en']."""
    s, lang = o.get('synopsis'), o.get('synopsis_lang')
    lang = lang.lower() if isinstance(lang, str) and lang else 'es'
    es = o.get('synopsis_es') if _hay(o.get('synopsis_es')) else s if lang == 'es' else None
    en = o.get('synopsis_en') if _hay(o.get('synopsis_en')) else s if lang == 'en' else None
    if not (_hay(es) or _hay(en) or _hay(s)):
        return []
    if _hay(es) and _hay(en) and es.strip() == en.strip():     # la misma copiada no es una traducción
        return ['en']
    return [k for k, v in (('es', es), ('en', en)) if not _hay(v)]


def _plano(t):
    import unicodedata
    t = unicodedata.normalize('NFD', str(t or '').lower())
    return ' '.join(''.join(c if c.isalnum() else ' ' for c in t if unicodedata.category(c) != 'Mn').split())


def faltan(d):
    """{'obra:idioma': título} de un festival."""
    import catalogo
    out = {}
    for f in (d or {}).get('films') or []:
        if not isinstance(f, dict):
            continue                                   # ilegible: lo dice [ficha-obra]
        f = dict(f, film_list=[x for x in f['film_list'] if isinstance(x, dict)]) if isinstance(f.get('film_list'), list) else f
        for o in catalogo.obras_de(f):
            if o.get('type') != 'event':
                for q in falta(o):
                    out[f"{o.get('work_id') or '?' + _plano(o.get('title'))}:{q}"] = o.get('title')
    return out


def _sin_anotar(d, ya):
    """Lo que falta y no está anotado. Una obra fusionada vale por su id de hoy, y una
    función nueva aún sin enlazar, por el título de una anotada del mismo festival."""
    import catalogo
    fus = catalogo.fusiones()
    hoy = faltan(d)
    ya = {f"{catalogo.redirige(k.rsplit(':', 1)[0], fus)}:{k.rsplit(':', 1)[1]}" for k in ya}
    ya |= {f"?{_plano(t)}:{k.rsplit(':', 1)[1]}" for k, t in hoy.items() if k in ya}
    return {k: t for k, t in hoy.items() if k not in ya}, ya


def deuda():
    if not os.path.exists(DEUDA):
        return {}
    return {k: v for k, v in json.load(open(DEUDA, encoding='utf-8')).items() if not k.startswith('_')}


def excedidos(festivales, techo=None):
    """→ [(festival, [títulos (idioma)])]: lo que falta y no estaba anotado."""
    techo, out = deuda() if techo is None else techo, []
    for fid, d in sorted(festivales.items()):
        n = [f"{t} ({k.rsplit(':', 1)[1]})" for k, t in _sin_anotar(d, techo.get(fid, []))[0].items()]
        if n:
            out.append((fid, sorted(n)))
    return out


def holgura(festivales, techo=None):
    techo, out = deuda() if techo is None else techo, []
    for fid, ks in sorted(techo.items()):
        s = {k for k in _sin_anotar(festivales.get(fid), ks)[1] if not k.startswith('?')} - set(faltan(festivales.get(fid)))
        if s:
            out.append(f'{fid} {len(s)}')
    return out


def autoprueba():
    """[] = la regla ve."""
    mal = []
    for o, q in (({'synopsis': 'Una mujer.'}, ['en']), ({'synopsis': 'A woman.', 'synopsis_lang': 'EN'}, ['es']), ({'synopsis_en': 'A woman.'}, ['es']),
                 ({'synopsis': 'Uma mulher.', 'synopsis_lang': 'pt', 'synopsis_en': 'A woman.'}, ['es']), ({'synopsis': 'Uma.', 'synopsis_lang': 'pt'}, ['es', 'en']),
                 ({'synopsis': 'Una.', 'synopsis_en': '  '}, ['en']), ({'synopsis': 'Una.', 'synopsis_en': 'Una.'}, ['en']), ({'synopsis': 'Una.', 'synopsis_en': 'A.'}, []), ({}, [])):
        if falta(o) != q:
            mal.append(f'{o} → {falta(o)}')
    if not excedidos({'nuevo': {'films': [{'type': 'film', 'title': 'X', 'synopsis': 'Una.'}]}}, {}):
        mal.append('un festival nuevo no parte de cero')
    return mal


if __name__ == '__main__':
    from obra_unica import _festivales
    a, fs = sys.argv[1:], _festivales()
    if a[:1] == ['--congelar']:
        if os.path.exists(DEUDA) and excedidos(fs):
            sys.exit('✗ la deuda solo baja; subió en: ' + ', '.join(f'{f}: {x[:2]}' for f, x in excedidos(fs)[:8]))
        ahora = {f: sorted(faltan(d)) for f, d in sorted(fs.items()) if faltan(d)}
        with open(DEUDA, 'w', encoding='utf-8') as fh:
            json.dump({'_nota': 'Obras con sinopsis en un solo idioma (pipeline/sinopsis_par.py). Solo baja.', **ahora}, fh, ensure_ascii=False, indent=1, sort_keys=True)
        print(sum(map(len, ahora.values())), 'huecos en', len(ahora), 'festivales')
    else:
        for f, d in sorted(fs.items()):
            x = faltan(d)
            if x and (not a or f == a[0]):
                print(f, len(x), (': ' + ' · '.join(f"{t} ({k.rsplit(':', 1)[1]})" for k, t in x.items())) if a else '')
