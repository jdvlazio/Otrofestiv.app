#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""obra_unica.py — el guardián: lo publicado de una obra ES lo decidido, en todos los festivales.

POR QUÉ (24 nov 2026, revisión senior): tras unificar sinopsis, afiche, director,
año, país y género, NADA impedía que volvieran a divergir: se mutaron seis campos a
mano en festivals/ y ningún chequeo reaccionó. Dos reglas, sobre lo publicado:
  · con decisión en el almacén: todo festival que publica el dato publica ESE;
  · sin decisión: todos los que lo publican coinciden. Si no, hay que decidir.
Vacío no es divergencia (es herencia, [dato-que-no-viaja]). La duración no entra:
es de la copia de cada festival.

    python3 pipeline/obra_unica.py [<festival>]          # lo que diverge
    python3 pipeline/obra_unica.py --decidir <work_id> <campo> <valor> --motivo "…" --quien "…"
        campo: directores («A, B») · anio · paises («CO,FR») · generos · sinopsis.en · sinopsis.es · afiche
    y después: ficha_unica.py / sinopsis_unicas.py / afiches_unicos.py --aplicar --escribir,
    y catalogo_construir.py --escribir
La decisión guarda en `antes` qué publicaba cada festival.
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))

CAMPO = {'director': 'directores', 'year': 'anio', 'country': 'paises', 'genre': 'generos',
         'synopsis': 'sinopsis.es', 'synopsis_en': 'sinopsis.en', 'poster': 'afiche'}
# Divergencias conocidas y explicadas, con fecha. Se quitan al resolverse: el
# guardián también falla si una excepción ya no hace falta.
EXCEPCIONES = {
    'w_R4PS7MYC5SKG': '«The End» une dos obras de TIFF (Pelechian y Lindroth von Bahr); la rama data/bogoshorts-2026 las separa (24 nov 2026)',
}


def elegidos(decs):
    """{work_id: {campo publicado: valor}} — lo que dicen las decisiones vigentes."""
    import afiches_unicos
    import ficha_unica
    out = ficha_unica.elegidos(decs)
    for w, e in afiches_unicos.elegidos(decs).items():
        out.setdefault(w, {})['poster'] = e['valor']['archivo']
    for x in decs:
        if x['campo'] == 'sinopsis.es':
            out.setdefault(x['work_id'], {})['synopsis'] = x['valor']
    return out


def publicado(festivales):
    """{work_id: {campo: {valor: [festivales]}}} con el título al lado."""
    import catalogo
    vals, tit = {}, {}
    for fid, d in sorted(festivales.items()):
        for f in (d or {}).get('films', []):
            for o in catalogo.obras_de(f):
                w = o.get('work_id')
                if not w:
                    continue
                tit.setdefault(w, o.get('title'))
                for k in CAMPO:
                    if o.get(k) not in (None, ''):
                        fs = vals.setdefault(w, {}).setdefault(k, {}).setdefault(str(o[k]), [])
                        if fid not in fs:
                            fs.append(fid)
    return vals, tit


def divergencias(festivales, decs, excepciones=None):
    """→ [(work_id, título, campo, elegido|None, {valor: [festivales]})]. Sin excepciones."""
    exc = EXCEPCIONES if excepciones is None else excepciones
    vals, tit = publicado(festivales)
    eleg, out = elegidos(decs), []
    for w, campos in sorted(vals.items()):
        if w in exc:
            continue
        for k, v in campos.items():
            if k in eleg.get(w, {}):
                malos = {x: f for x, f in v.items() if x != str(eleg[w][k])}
                if malos:
                    out.append((w, tit[w], k, eleg[w][k], malos))
            elif len(v) > 1:
                out.append((w, tit[w], k, None, v))
    return out


def excepciones_de_mas(festivales, decs):
    """Excepciones que ya no ocultan nada: hay que borrarlas."""
    vivas = {x[0] for x in divergencias(festivales, decs, {})}
    return [w for w in EXCEPCIONES if w not in vivas]


def autoprueba():
    """Cada campo, alterado en memoria, tiene que verse: con decisión y sin ella. [] = ve todo."""
    base = {'title': 'X', 'type': 'film', 'work_id': 'w_1', 'director': 'A', 'year': 2025, 'country': 'Colombia', 'genre': 'Drama',
            'synopsis': 's', 'synopsis_en': 'e', 'poster': '/assets/a/x.jpg'}
    decs = [{'work_id': 'w_1', 'campo': 'directores', 'valor': ['A']}, {'work_id': 'w_1', 'campo': 'anio', 'valor': 2025},
            {'work_id': 'w_1', 'campo': 'paises', 'valor': ['CO']}, {'work_id': 'w_1', 'campo': 'generos', 'valor': ['Drama']},
            {'work_id': 'w_1', 'campo': 'sinopsis.es', 'valor': 's'}, {'work_id': 'w_1', 'campo': 'sinopsis.en', 'valor': 'e'},
            {'work_id': 'w_1', 'campo': 'afiche', 'valor': {'archivo': '/assets/a/x.jpg', 'veredicto': 'oficial'}}]
    ciego = []
    for k in CAMPO:
        for ds, que in ((decs, 'decidido'), ([], 'sin decidir')):
            otro = dict(base, **{k: 1999 if k == 'year' else 'otro'})
            fs = lambda b: {'f-1': {'films': [dict(base)]}, 'f-2': {'films': [{'title': 'P', 'type': 'film', 'film_list': [b]}]}}
            if [x[2] for x in divergencias(fs(otro), ds, {})] != [k] or divergencias(fs(dict(base)), ds, {}):
                ciego.append(f'{k} ({que})')
    return ciego


def _festivales():
    import glob
    import json
    return {os.path.basename(p)[:-5]: json.load(open(p, encoding='utf-8')) for p in glob.glob(f'{REPO}/festivals/*.json')}


def texto(x):
    w, t, k, e, v = x
    return f'«{t}» {w} {CAMPO[k]}' + (f' (decidido: {str(e)[:60]})' if e is not None else ' (sin decidir)') + ': ' + \
        ' | '.join(f'{str(a)[:60]} [{", ".join(f[:4])}]' for a, f in v.items())


def decidir(decs, vals, w, campo, valor, motivo, quien, fecha):
    """Agrega (o cambia) la decisión, guardando en `antes` qué publicaba cada festival."""
    pub = next((k for k, c in CAMPO.items() if c == campo), None)
    if not pub:
        raise SystemExit(f'✗ campo desconocido: {campo}')
    v = {'directores': lambda s: [x.strip() for x in s.split(',')], 'paises': lambda s: [x.strip().upper() for x in s.split(',')],
         'anio': int, 'generos': lambda s: [s]}.get(campo, lambda s: s)(valor)
    if campo == 'afiche':
        v = {'archivo': valor, 'veredicto': 'oficial'}
    if campo == 'paises':
        from herencia import _pais_es
        if not _pais_es(v):
            raise SystemExit(f'✗ código de país desconocido en {v}')
    antes = {f: a for a, fs in vals.get(w, {}).get(pub, {}).items() for f in fs}
    if not antes:
        raise SystemExit(f'✗ {w} no publica {pub} en ningún festival')
    d = next((x for x in decs if x['work_id'] == w and x['campo'] == campo), None)
    if d is None:
        d = {'work_id': w, 'campo': campo}
        decs.append(d)
    if 'original' in d:
        raise SystemExit('✗ esa sinopsis tiene síntesis verificada: se cambia con sinopsis_cortas.py')
    d.update(valor=v, motivo=motivo, fecha=fecha, quien=quien, antes={**antes, **(d.get('antes') or {})})
    if campo == 'afiche':
        d['a_mano'] = True
        d['vistas'] = sorted(set(d.get('vistas') or []) | set(antes.values()) - {valor})
    if campo == 'sinopsis.es':
        import sinopsis_unicas
        d['vistas'] = sorted(set(d.get('vistas') or []) | {sinopsis_unicas.huella(s) for s in antes.values()})
    return d


if __name__ == '__main__':
    import json
    import datetime
    import catalogo
    a = sys.argv[1:]
    fs, decs = _festivales(), catalogo.decisiones()
    if a[:1] == ['--decidir']:
        arg = lambda n: a[a.index(n) + 1] if n in a else sys.exit(f'✗ falta {n}')
        d = decidir(decs, publicado(fs)[0], a[1], a[2], a[3], arg('--motivo'), arg('--quien'), datetime.date.today().isoformat())
        with open(os.path.join(catalogo.DIR, 'decisiones.json'), 'w', encoding='utf-8') as fh:
            fh.write(json.dumps(decs, ensure_ascii=False, indent=1))
        print('✓', json.dumps(d, ensure_ascii=False))
    else:
        xs = [x for x in divergencias(fs, decs) if not a or any(a[0] in f for f in x[4].values())]
        print('\n'.join(texto(x) for x in xs) or '✓ lo publicado es lo decidido')
        sys.exit(1 if xs else 0)
