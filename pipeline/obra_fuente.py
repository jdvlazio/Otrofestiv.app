#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""obra_fuente.py — la obra es la fuente; el festival solo pone la función y el lugar.

Juan, 24 nov 2026 (paso 7 de docs/OBRA.md): «una película es el insumo principal; el
festival lo que agrega es la función y en dónde». Cada festival guardaba su copia de
dirección, año, país, género, sinopsis, afiche y enlaces, y las copias se separaban.

En un festival NUEVO esos datos no son suyos: salen de catalogo/decisiones/. El
JSON que lee la app se sigue publicando completo (instaladas y sin conexión), pero se
ARMA: `componer(desnudar(d))`. Guardián [obra-fuente]:
  · todo dato de obra publicado tiene su decisión y es ese;
  · armar el festival desde función + almacén da, campo por campo, lo publicado.
Los festivales anteriores están en catalogo/obra-fuente-legado.json: la lista solo baja.

    python3 pipeline/obra_fuente.py <festival>                        # qué falta
    python3 pipeline/obra_fuente.py <festival> --sembrar --quien X    # lo publicado de sus obras sin decisión pasa al almacén
    python3 pipeline/obra_fuente.py <festival> --aplicar              # el almacén, en lo publicado
Orden: publicar → catalogo_construir.py --escribir → --sembrar → catalogo_construir.py
--escribir → sello_obra.py (original y sello) → push.
"""
import copy
import datetime
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
LEGADO = os.path.join(REPO, 'catalogo', 'obra-fuente-legado.json')
CAMPOS = ('director', 'year', 'country', 'genre', 'synopsis', 'synopsis_en', 'poster', 'tmdb_id', 'lbSlug')
# lo que se deriva de esos: se arma con ellos y no se guarda aparte
DERIVADOS = ('flags', 'synopsis_lang', 'posterSource', 'synopsis_es')
# los que ya existían el 24 nov 2026: en el legado no puede entrar ninguno más
LEGADO_MAX = frozenset('aff-2026 aleste-2026 anibia-2026 bhff-2026 biff-2026 cajica-2026 cineautopsia-2026 cinemancia-2025 cinemancia-2026 cineparalapaz-2026 cinetoro-2026 cortoscali-2026 cuaff-2026 fantasmagoria-2026 fantasofest-2026 fecibac-2026 festicinerio-2026 ficcali-2026 ficci-65 ficdeh-2026 ficfusa-2026 ficica-2026 ficidi-2026 ficma-2026 ficmontanas-2026 ficpa-2026 filcmar-2026 finca-2026 funza-2026 girardota-2026 guatape-2026 itagui-2026 jardin-2026 leviza-2026 mambe-2026 mamut-2026 midbo-2026 miradas-2026 mubibogota-2026 narrarelfuturo-2026 olhar-2026 popayan-2026 provinciadevelez-2026 qaff-2026 semanacine-2026 siembrafest-2026 tercertiempo-2026 tiff-2026 tribeca-2026 under-2026 vartex-2026 villadelcine-2026 villadeleyvaiff-2026'.split())


def legado():
    with open(LEGADO, encoding='utf-8') as fh:
        return set(json.load(fh))


def enrolado(fid):
    return fid not in legado()


def _obras(d):
    import catalogo
    for f in (d or {}).get('films') or []:
        if isinstance(f, dict):
            for o in catalogo.obras_de(f):
                if isinstance(o, dict) and o.get('work_id') and o.get('type') != 'event':
                    yield o


def elegidos(decs):
    """{obra: {campo publicado: valor}}, y la fuente del afiche."""
    import afiches_unicos
    import obra_unica
    out = obra_unica.elegidos(decs)
    # un fotograma remoto DESCARTADO («esa imagen no es afiche») no se pone nunca; uno ELEGIDO al sembrar, sí
    for d in decs:
        if d['campo'] == 'afiche' and (d['valor']['veredicto'] != 'fotograma' or d['valor']['archivo'].startswith('/assets/') or d['valor'].get('elegido')):
            out.setdefault(d['work_id'], {}).update(poster=d['valor']['archivo'], posterSource=afiches_unicos.fuente(d))
    return out


def desnudar(d):
    """El festival sin nada que sea de la obra: función y lugar."""
    d = copy.deepcopy(d)
    for o in _obras(d):
        for k in CAMPOS + DERIVADOS:
            o.pop(k, None)
    return d


def componer(d, decs=None):
    """Lo decidido de cada obra, puesto en `d` (en el lugar). → [(título, campo, antes, después)]"""
    import catalogo
    from lib import banderas
    eleg, out = elegidos(catalogo.decisiones() if decs is None else decs), []
    for o in _obras(d):
        for k, v in eleg.get(o['work_id'], {}).items():
            if k not in CAMPOS or o.get(k) == v:
                continue
            if v in (None, ''):
                if o.get(k) not in (None, ''):
                    out.append((o.get('title'), k, o.get(k), v))
                o.pop(k, None)
                if k == 'synopsis':
                    o.pop('synopsis_lang', None)
                    o.pop('synopsis_es', None)
                continue
            out.append((o.get('title'), k, o.get(k), v))
            if k == 'poster' and o.get('poster'):
                o.pop('posterPosition', None)          # era el encuadre de la imagen anterior
            o[k] = v
        e = eleg.get(o['work_id'], {})
        if e.get('country'):
            o['flags'] = banderas(e['country'])
            if not o['flags']:
                o.pop('flags')
        if e.get('synopsis'):
            o['synopsis_lang'] = 'es'
            o.pop('synopsis_es', None)
        if e.get('poster'):
            o['posterSource'] = e['posterSource']
    return out


def problemas(fid, d, decs=None):
    """→ [(título, campo, qué)] de un festival enrolado."""
    import catalogo
    decs = catalogo.decisiones() if decs is None else decs
    eleg, out = elegidos(decs), []
    for o in _obras(d):
        e = eleg.get(o['work_id'], {})
        for k in CAMPOS:
            p, v = o.get(k), e.get(k)
            if p not in (None, '') and k not in e:
                out.append((o.get('title'), k, 'publicado sin decisión en el almacén'))
            elif v not in (None, '') and str(p) != str(v):
                out.append((o.get('title'), k, f'publica {str(p)[:40]!r}; el almacén dice {str(v)[:40]!r}'))
            elif k in e and v in (None, '') and p not in (None, ''):
                out.append((o.get('title'), k, 'el almacén dice que no tiene'))
        for k in o:
            if (k.startswith('synopsis') or (k.startswith('poster') and k != 'posterPosition')) and k not in CAMPOS + DERIVADOS or (k == 'synopsis_es' and o[k]):
                out.append((o.get('title'), k, 'dato de obra fuera de los campos conocidos'))
    for f in d.get('films') or []:
        if f.get('type') == 'event' and f.get('work_id'):
            out.append((f.get('title'), 'type', 'una obra publicada como evento'))
        if f.get('film_list') and f.get('type') != 'event':      # el programa no repite lo de sus obras
            out += [(f.get('title'), k, 'dato de obra puesto en el programa') for k in ('director', 'year', 'synopsis', 'synopsis_en', 'tmdb_id', 'lbSlug') if f.get(k)]
            ps = {p.strip() for o in f['film_list'] for p in (o.get('country') or '').split(',') if p.strip()}
            if f.get('country') and {p.strip() for p in f['country'].split(',')} != ps:
                out.append((f.get('title'), 'country', 'los países del programa no son los de sus obras'))
    if not out:                                        # armado de cero, campo por campo
        armado = desnudar(d)
        componer(armado, decs)
        for a, b in zip(_obras(armado), _obras(d)):
            for k in set(a) | set(b):
                if a.get(k) != b.get(k) and not (a.get(k) in (None, '') and b.get(k) in (None, '')):
                    out.append((b.get('title'), k, f'armado da {str(a.get(k))[:40]!r} y se publica {str(b.get(k))[:40]!r}'))
    return out


def sembrar(fid, d, decs, quien, fecha=None, festivales=None):
    """Alta: lo que publica una obra SIN decisión pasa a ser del almacén. Si ya hay una, o
    otro festival publica otra cosa, no se adivina: se dice cuál y se decide."""
    import obra_unica
    from fichas_iso import iso
    vals = obra_unica.publicado({**(festivales or {}), fid: d})[0]
    fecha, ya = fecha or datetime.date.today().isoformat(), {(x['work_id'], x['campo']): x for x in decs}
    eleg, nuevas, mal, hechas = elegidos(decs), [], [], set()
    for o in _obras(d):
        w = o['work_id']
        conv = {'director': lambda x: [y.strip() for y in x.split(',') if y.strip()], 'year': int, 'country': iso, 'genre': lambda x: [x], 'synopsis': str, 'synopsis_en': str,
                'tmdb_id': int, 'lbSlug': str,
                'poster': lambda x: {'archivo': x, 'veredicto': {'custom': 'oficial-festival', 'editorial': 'fotograma'}.get(o.get('posterSource'), 'oficial'),
                                     **({'fuente': 'tmdb'} if o.get('posterSource') == 'tmdb' else {'elegido': True} if o.get('posterSource') == 'editorial' else {})}}
        for k, v in conv.items():
            c, p = obra_unica.CAMPO[k], (o.get('synopsis_es') or o.get(k)) if k == 'synopsis' else o.get(k)
            if p in (None, '') or (w, c) in hechas:
                continue
            t = f'«{o.get("title")}» {k}'
            if (w, c) in ya:
                if eleg.get(w, {}).get(k) in (None, ''):
                    mal.append(f'{t}: hay una decisión que no da valor ({str(ya[w, c]["valor"])[:50]}) — decidir de nuevo')
                continue
            otros = {x: fs for x, fs in vals.get(w, {}).get(k, {}).items() if x != str(p)}
            if otros:
                mal.append(f'{t}: otro festival publica {str(list(otros))[:80]} — obra_unica.py --decidir')
                continue
            if k == 'synopsis' and (o.get('synopsis_lang') or 'es') != 'es':
                mal.append(f'{t}: la sinopsis no está en español')
                continue
            try:
                valor = v(p)
            except ValueError as e:
                mal.append(f'{t}: {e}')
                continue
            nuevas.append({'work_id': w, 'campo': c, 'valor': valor, 'motivo': f'alta desde {fid}', 'fecha': fecha, 'quien': quien, 'sembrada': True,
                           'antes': {f: x for x, fs in vals.get(w, {}).get(k, {}).items() for f in fs}})
            hechas.add((w, c))
    if mal:
        raise SystemExit(f'✗ {len(mal)} sin sembrar, no se guardó nada:\n  ' + '\n  '.join(mal))
    decs += nuevas
    return len(nuevas)


def autoprueba():
    """[] = la regla ve."""
    o = {'type': 'film', 'title': 'X', 'work_id': 'w_1', 'director': 'A B', 'year': 2025, 'country': 'Colombia', 'flags': '🇨🇴', 'synopsis': 'Una.', 'synopsis_lang': 'es',
         'synopsis_en': 'A.', 'day': 'VIE 1', 'venue': 'v', 'duration': '9 min', 'poster': '/assets/x.jpg', 'posterSource': 'oficial'}
    d, decs, mal = {'films': [o]}, [], []
    sembrar('f', d, decs, 'x')
    if problemas('f', d, decs):
        mal.append(f'frena lo que está bien: {problemas("f", d, decs)[:2]}')
    for k, v in (('director', 'Otro'), ('year', 1999), ('synopsis', 'Otra.'), ('synopsis_en', ''), ('poster', '/assets/y.jpg'), ('genre', 'Drama'), ('flags', '🇫🇷'), ('posterSource', 'tmdb'), ('synopsis_lang', 'en')):
        if not problemas('f', {'films': [dict(o, **{k: v})]}, decs):
            mal.append(f'no ve {k}')
    if problemas('f', {'films': [dict(o, venue='otra', day='SÁB 2', duration='10 min')]}, decs):
        mal.append('la función y el lugar no son de la obra')
    if not problemas('f', {'films': [{'title': 'P', 'type': 'film', 'country': 'Chile', 'film_list': [dict(o)]}]}, decs) or not problemas('f', {'films': [dict(o, synopsis_pt='x')]}, decs) or not problemas('f', {'films': [dict(o, type='event')]}, decs):
        mal.append('no ve el programa, el evento o un campo nuevo')
    if set(desnudar(d)['films'][0]) & set(CAMPOS + DERIVADOS):
        mal.append('desnudar deja datos de la obra')
    return mal


if __name__ == '__main__':
    from obra_unica import _festivales
    import catalogo
    a, fs = sys.argv[1:], _festivales()
    if not a or a[0] not in fs:
        sys.exit(__doc__)
    fid, d = a[0], fs[a[0]]
    if '--sembrar' in a:
        if '--quien' not in a:
            sys.exit('✗ falta --quien')
        decs = catalogo.decisiones()
        n = sembrar(fid, d, decs, a[a.index('--quien') + 1], festivales=fs)
        catalogo.escribir_decisiones(decs)
        print(n, 'decisiones')
    elif '--aplicar' in a:
        from sinopsis_unicas import _guardar
        n = componer(d)
        _guardar(os.path.join(REPO, 'festivals', fid + '.json'), d)
        print(len(n), 'datos')
    mal = problemas(fid, fs[fid])
    for x in mal:
        print(*x, sep=' · ')
    print('enrolado' if enrolado(fid) else 'en el legado')
    sys.exit(1 if mal and enrolado(fid) else 0)
