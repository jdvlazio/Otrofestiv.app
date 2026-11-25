#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sello_obra.py — la sinopsis y la dirección que se publican son de ESA película, y alguien lo leyó.

POR QUÉ (Juan, 24 nov 2026: «me preocupa que sigan apareciendo sinopsis de otras
películas»): todos los guardianes miraban la FORMA. Se leyeron 1.773 obras y 31
mezclaban dos películas: «Dracula» de Radu Jude firmada por Luc Besson, «Señoritas»
de Lina Rodríguez por Fernando Méndez. Estaban bien escritas.

REGLA: cada obra con sinopsis lleva un sello. El sello dice quién la redactó, quién
la VERIFICÓ (distinto) y contra qué fuente, y guarda la huella de lo publicado:
dirección, año, español, inglés y original (el título no: cada festival imprime el
suyo). Si cambia una letra, se rompe y
no se publica hasta que alguien la vuelva a leer.

  · catalogo/sellos.json       {obra: {huella, redacta, verifica, contra, fecha}}
  · catalogo/originales.json   {obra: {texto, idioma, fuente}}: el texto tal como
    llegó. Nunca se edita; las cortas (es, en) salen de él.
  · pipeline/sello-obra-deuda.json  lo publicado sin sello el día que nació la regla,
    con su huella. Solo baja: si cambia, necesita sello.

ORDEN: publicar → catalogo_construir.py --escribir (da los ids) → otro agente lee →
--sellar → push. Fusionar dos obras es releer: el sello de la absorbida no se hereda.
Una función urgente de una obra nueva puede salir sin sinopsis y sellarse después.
Lo que esto NO prueba: quién leyó de verdad; eso es del método (SINOPSIS-CORTA.md).

Además: un mismo texto en dos obras no se publica (`gemelas` anotadas: solo bajan).

    python3 pipeline/sello_obra.py                                     # cuántas sin sello
    python3 pipeline/sello_obra.py --sellar <lote.json>                # [{work_id, redacta, verifica, contra, veredicto: "fiel"}]
    python3 pipeline/sello_obra.py --original <lote.json>              # [{work_id, texto, idioma, fuente}], una vez por obra
    python3 pipeline/sello_obra.py --congelar                          # bajar la deuda
"""
import hashlib
import json
import os
import sys
import unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
SELLOS = os.path.join(REPO, 'catalogo', 'sellos.json')
ORIGINALES = os.path.join(REPO, 'catalogo', 'originales.json')
DEUDA = os.path.join(REPO, 'pipeline', 'sello-obra-deuda.json')


def _leer(p):
    if not os.path.exists(p):
        return {}
    with open(p, encoding='utf-8') as fh:
        return json.load(fh)


def _escribir(p, d):
    with open(p, 'w', encoding='utf-8') as fh:
        json.dump(d, fh, ensure_ascii=False, indent=1, sort_keys=True)


def sellos():
    return _leer(SELLOS)


def originales():
    return _leer(ORIGINALES)


def _plano(x):
    return ' '.join(unicodedata.normalize('NFC', str(x)).split())


def publicadas(festivales):
    """{obra: {título, director, año, es, en}}: cada campo, los valores distintos que se publican."""
    import catalogo
    out = {}
    for _, d in sorted(festivales.items()):
        for f in (d or {}).get('films') or []:
            if not isinstance(f, dict):
                continue
            f = dict(f, film_list=[x for x in f['film_list'] if isinstance(x, dict)]) if isinstance(f.get('film_list'), list) else f
            for o in catalogo.obras_de(f):
                w = o.get('work_id')
                if not w or o.get('type') == 'event':
                    continue
                v = out.setdefault(w, {'titulo': o.get('title'), 'director': set(), 'anio': set(), 'es': set(), 'en': set()})
                for k, x in (('director', o.get('director')), ('anio', o.get('year')), ('es', o.get('synopsis_es') or o.get('synopsis')), ('en', o.get('synopsis_en'))):
                    if x not in (None, ''):
                        v[k].add(_plano(x))
                if o.get('synopsis_es') and o.get('synopsis'):      # la app cae a `synopsis` si falta la del idioma
                    v['es'].add(_plano(o['synopsis']))
    return {w: v for w, v in out.items() if v['es'] or v['en']}


def huella(v, original=None):
    """El título no entra: cada festival imprime el suyo."""
    x = [sorted(v[k]) for k in ('director', 'anio', 'es', 'en')] + [(original or {}).get('texto') or '']
    return hashlib.sha1(json.dumps(x, ensure_ascii=False).encode()).hexdigest()[:12]


def problema(s):
    """Qué le falta a un sello para valer, o None."""
    if not isinstance(s, dict):
        return 'sello ilegible'
    q = lambda k: s[k].strip().casefold() if isinstance(s.get(k), str) else ''
    if not q('redacta') or not q('verifica') or q('redacta') == q('verifica'):
        return 'sello sin segundo lector'
    if '/' not in q('contra'):
        return 'sello sin fuente (URL o ruta)'
    if q('veredicto') != 'fiel' or not q('fecha'):
        return 'sello sin veredicto o sin fecha'
    return None


def faltan(festivales, sel=None, deuda=None, orig=None, exentas=None):
    """→ [(obra, título, qué)]: sin sello válido ni anotada."""
    sel, deuda, orig = (sellos() if sel is None else sel), (_leer(DEUDA).get('obras', {}) if deuda is None else deuda), (originales() if orig is None else orig)
    sin_orig, out = set(_leer(DEUDA).get('sin_original', [])), []
    for w, v in sorted(publicadas(festivales).items()):
        if w in sel:
            q = problema(sel[w]) or ('sellada sin guardar el original' if w not in orig and w not in sin_orig and w not in (exentas or ()) else None) or (None if sel[w].get('huella') == huella(v, orig.get(w)) else 'cambió después del sello')
        else:
            q = None if deuda.get(w) == huella(v) else 'cambió y nadie la releyó' if w in deuda else 'nueva, sin sello (¿es la misma que otra?: fusionar)'
        if q:
            out.append((w, v['titulo'], q))
    return out


def gemelas(festivales, ya=None):
    """→ {'obraA+obraB'}: el mismo texto en dos obras (más de 6 palabras)."""
    import sinopsis_unicas as su
    ya = set(_leer(DEUDA).get('gemelas', [])) if ya is None else set(ya)
    vistos, out = {}, set()
    for w, v in sorted(publicadas(festivales).items()):
        for k in ('es', 'en'):
            for t in v[k]:
                p = su.plana(t)
                if len(p.split()) > 6:
                    otra = vistos.setdefault((k, p), w)
                    if otra != w:
                        out.add(f'{otra}+{w}')
    return out - ya


def autoprueba():
    """[] = la regla ve."""
    o = {'type': 'film', 'title': 'X', 'work_id': 'w_1', 'director': 'A', 'year': 2025, 'synopsis': 'Una mujer vuelve a su pueblo y encuentra un hotel.', 'synopsis_en': 'A woman.'}
    f = lambda **k: {'a': {'films': [dict(o, **k)]}}
    h = huella(publicadas(f())['w_1'])
    s = {'w_1': {'huella': h, 'redacta': 'a', 'verifica': 'b', 'contra': 'https://x', 'veredicto': 'fiel', 'fecha': '2026-11-24'}}
    mal = []
    if faltan(f(), s, {}, {}, {'w_1'}) or not faltan(f(), s, {}, {}) or faltan(f(), {}, {'w_1': h}, {}):
        mal.append('frena lo que está bien')
    for k in ({'director': 'B'}, {'year': 1999}, {'synopsis': 'Otra.'}, {'synopsis_en': 'Other.'}):
        if not faltan(f(**k), s, {}, {}, {'w_1'}) or not faltan(f(**k), {}, {'w_1': h}, {}):
            mal.append(f'no ve {k}')
    if not faltan(f(), s, {}, {'w_1': {'texto': 'otro original'}}):
        mal.append('no ve el original')
    if not all(faltan(f(), {'w_1': x}, {}, {}) for x in (dict(s['w_1'], verifica='A '), dict(s['w_1'], contra='?'), dict(s['w_1'], redacta=''), 'x')) or not faltan(f(), {}, {}, {}):
        mal.append('acepta sin segundo lector o sin sello')
    if not gemelas({'a': {'films': [o, dict(o, work_id='w_2')]}}, []):
        mal.append('no ve el mismo texto en dos obras')
    return mal


def sellar(lote, festivales=None, fecha=None):
    import datetime
    if festivales is None:
        from obra_unica import _festivales
        festivales = _festivales()
    pub, sel, orig = publicadas(festivales), sellos(), originales()
    for e in lote:
        w = e['work_id']
        if w not in pub:
            raise SystemExit(f'✗ {w} no publica sinopsis')
        s = {'huella': huella(pub[w], orig.get(w)), **{k: e.get(k) for k in ('redacta', 'verifica', 'contra', 'veredicto')},
             'fecha': fecha or datetime.date.today().isoformat()}
        if w not in orig and w not in set(_leer(DEUDA).get('sin_original', [])):
            raise SystemExit(f'✗ {w}: primero el original (--original)')
        if problema(s):
            raise SystemExit(f'✗ {w}: {problema(s)}')
        sel[w] = s
    _escribir(SELLOS, sel)
    return len(lote)


def guardar_originales(lote):
    """El texto tal como llegó. Una vez: no se reemplaza."""
    orig = originales()
    for e in lote:
        w, o = e['work_id'], {k: e.get(k) for k in ('texto', 'idioma', 'fuente')}
        if not all(o.values()):
            raise SystemExit(f'✗ {w}: el original lleva texto, idioma y fuente')
        if w in orig and orig[w] != o:
            raise SystemExit(f'✗ {w} ya tiene original; no se edita')
        orig[w] = o
    _escribir(ORIGINALES, orig)
    return len(lote)


if __name__ == '__main__':
    from obra_unica import _festivales
    a, fs = sys.argv[1:], _festivales()
    if a[:1] == ['--sellar']:
        with open(a[1], encoding='utf-8') as fh:
            print(sellar(json.load(fh), fs), 'selladas')
    elif a[:1] == ['--original']:
        with open(a[1], encoding='utf-8') as fh:
            print(guardar_originales(json.load(fh)), 'originales')
    elif a[:1] == ['--congelar']:
        if faltan(fs) or gemelas(fs):
            sys.exit('✗ la deuda solo baja; sin sello: ' + ', '.join(f'{t} ({q})' for _, t, q in faltan(fs)[:8]))
        sel, g = sellos(), gemelas(fs, [])
        obras = {w: huella(v) for w, v in publicadas(fs).items() if w not in sel}
        _escribir(DEUDA, {'_nota': 'Obras publicadas sin sello de verificación (pipeline/sello_obra.py). Solo baja.', 'obras': obras, 'gemelas': sorted(g),
                          'sin_original': sorted(set(_leer(DEUDA).get('sin_original', [])) - set(originales()))})
        print(len(obras), 'sin sello ·', len(sel), 'selladas ·', len(g), 'textos gemelos')
    else:
        n = len(publicadas(fs))
        print(n, 'obras con sinopsis ·', len(sellos()), 'selladas ·', len(_leer(DEUDA).get('obras', {})), 'en deuda')
        for x in faltan(fs):
            print(*x, sep=' · ')
