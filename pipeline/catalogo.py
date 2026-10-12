#!/usr/bin/env python3
"""catalogo.py — el catálogo único de obras: lectura, huella e invariantes.

Diseño en docs/CATALOGO-OBRAS.md (aprobado por Juan, 12 oct 2026). Este módulo
es la FASE 0: no construye el catálogo ni toca el pipeline; define cómo se lee,
cómo se reconoce una obra (huella) y los cinco invariantes que validate.py
vigila. Mientras catalogo/obras/ esté vacío, los guardianes pasan sin más; con
`autoprueba()` se demuestra que cada uno atrapa su caso roto (un guardián que
nunca falló no es de fiar).

    catalogo/obras/<id>.json     una obra por archivo
    catalogo/decisiones.json     decisiones humanas (prioridad máxima)
    catalogo/fusiones.json       ids absorbidos → superviviente (nunca se borra)
    catalogo/procedencia/<id>.json  de dónde salió cada campo
"""
import glob
import io
import json
import os
import re
import secrets
import time

from lib import sinacento

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(REPO, 'catalogo')
_B32 = '0123456789ABCDEFGHJKMNPQRSTVWXYZ'          # Crockford: sin I, L, O, U
ID = re.compile(r'^w_[0-9A-HJKMNP-TV-Z]{12}$')
_ARTICULOS = {'el', 'la', 'los', 'las', 'lo', 'un', 'una', 'the', 'a', 'an', 'o', 'os', 'as', 'le', 'les', 'il', 'der', 'die', 'das'}


# ── identidad ────────────────────────────────────────────────────────────────
def nuevo_id():
    """Opaco y ordenable por fecha (ULID recortado): 6 caracteres de tiempo + 6 al
    azar. Nunca se deriva del título: un título cambia, el id no."""
    t, s = int(time.time() * 1000), ''
    for _ in range(6):
        s = _B32[t % 32] + s
        t //= 32
    return 'w_' + s + ''.join(secrets.choice(_B32) for _ in range(6))


def huella(titulo):
    """La clave de CANDIDATURA de OpenRefine (fingerprint): minúsculas, sin
    tildes, sin puntuación, sin artículo inicial, tokens únicos y ordenados.
    Sirve para proponer coincidencias, NUNCA como identidad."""
    t = re.sub(r'[^a-z0-9 ]+', ' ', sinacento(titulo or '').lower())   # sinacento devuelve MAYÚSCULAS
    toks = t.split()
    # el artículo al principio («La niña santa») o al final, como lo catalogan
    # los archivos («Niña santa, La»)
    if len(toks) > 1 and toks[0] in _ARTICULOS:
        toks = toks[1:]
    if len(toks) > 1 and toks[-1] in _ARTICULOS:
        toks = toks[:-1]
    return ' '.join(sorted(set(toks)))


def apellido(director):
    """El apellido del primer director, para bloquear la comparación."""
    primero = re.split(r',| y | & |/', director or '')[0].strip()
    partes = sinacento(primero).lower().split()
    return partes[-1] if partes else ''


# ── lectura ──────────────────────────────────────────────────────────────────
def obras(raiz=DIR):
    out = {}
    for p in sorted(glob.glob(os.path.join(raiz, 'obras', '*.json'))):
        o = json.load(io.open(p, encoding='utf-8'))
        out[o.get('id') or os.path.basename(p)[:-5]] = dict(o, _archivo=os.path.basename(p))
    return out


def _lista(raiz, nombre):
    p = os.path.join(raiz, nombre)
    return json.load(io.open(p, encoding='utf-8')) if os.path.exists(p) else []


def decisiones(raiz=DIR):
    return _lista(raiz, 'decisiones.json')


def fusiones(raiz=DIR):
    return _lista(raiz, 'fusiones.json')


def redirige(work_id, fus):
    """El id vigente de una obra, siguiendo las fusiones (una cadena A→B→C)."""
    m, vistos = {f['absorbido']: f['superviviente'] for f in fus}, set()
    while work_id in m and work_id not in vistos:
        vistos.add(work_id)
        work_id = m[work_id]
    return work_id


def indice(obs):
    """(festival, huella) → work_ids, y tmdb → work_ids: para resolver miles de
    presentaciones sin recalcular la huella de cada obra cada vez."""
    por_h, por_t = {}, {}
    for wid, o in obs.items():
        hs = {huella(o['titulo_original'])} | {huella(a['titulo']) for a in o.get('aliases') or []}
        for fid in o.get('presentaciones') or []:
            for h in hs:
                por_h.setdefault((fid, h), set()).add(wid)
        t = (o.get('xref') or {}).get('tmdb')
        if t:
            por_t.setdefault(t, set()).add(wid)
    return por_h, por_t


def obra_de(obs, fid, titulo, tmdb=None, ix=None):
    """El work_id de una obra de un festival: la que lo lista en sus
    presentaciones y cuyo título (original o alias) tiene la misma huella; o la
    que lleva su tmdb. Ninguna o más de una → None (no se adivina)."""
    por_h, por_t = ix or indice(obs)
    hits = por_h.get((fid, huella(titulo))) or (por_t.get(tmdb) if tmdb else None) or set()
    return next(iter(hits)) if len(hits) == 1 else None


def reconocer(obs, titulo, director='', anio=None, duracion=None, excluir=None):
    """Una obra que llega de un festival NUEVO → (work_id, 'coincide') o (None, None).
    Las mismas reglas que el constructor (§4.1): misma huella de título (original
    o alias) Y mismo apellido de director Y año ±1; o, si a un lado le falta
    director, la huella corroborada por año ±1 o duración ±3. Más de una obra
    posible = no se adivina. `excluir` deja fuera un festival (para probar
    contra lo publicado sin verse a sí mismo)."""
    h, ap = huella(titulo), apellido(director)
    if not h:
        return None, None
    hits = set()
    for wid, o in obs.items():
        pres = [p for p in o.get('presentaciones') or [] if p != excluir]
        if not pres:
            continue
        if h not in {huella(o['titulo_original'])} | {huella(a['titulo']) for a in o.get('aliases') or []}:
            continue
        a_ok = anio is None or o.get('anio') is None or abs(anio - o['anio']) <= 1
        aps = {apellido(d) for d in o.get('directores') or []}
        if ap and aps - {''}:
            if ap in aps and a_ok:
                hits.add(wid)
        elif (anio and o.get('anio') and abs(anio - o['anio']) <= 1) or \
                (duracion and any(v.get('duracion_min') and abs(v['duracion_min'] - duracion) <= 3
                                  for v in o.get('versiones') or [])):
            hits.add(wid)
    return (hits.pop(), 'coincide') if len(hits) == 1 else (None, None)


def enlazar(d, fid, obs, ix=None):
    """Pone `work_id` a cada obra del festival (también las de un programa de
    cortos; las actividades no). Devuelve los títulos que no resolvieron: obras
    nuevas que el catálogo todavía no tiene (catalogo_construir.py --escribir)."""
    ix = ix or indice(obs)
    faltan = []
    for f in d.get('films', []):
        if f.get('type') == 'event':
            continue
        for o in (f.get('film_list') or [f]):
            if o.get('type') == 'event' or not o.get('title'):
                continue
            w = obra_de(obs, fid, o['title'], o.get('tmdb_id'), ix)
            if w:
                o['work_id'] = w
            else:
                o.pop('work_id', None)
                faltan.append(o['title'])
    return faltan


# ── los cinco invariantes (funciones puras: datos → lista de problemas) ───────
def xref_repetido(obs):
    """Un tmdb / imdb / wikidata pertenece a UNA obra (regla distinct values de
    Wikidata). Dos obras con el mismo es un duplicado sin fusionar."""
    visto, prob = {}, []
    for wid, o in obs.items():
        for k, v in (o.get('xref') or {}).items():
            if v in (None, ''):
                continue
            clave = (k, v)
            if clave in visto:
                prob.append(f'{k}={v} en {visto[clave]} y en {wid}')
            visto[clave] = wid
    return prob


def duracion_en_obra(obs):
    """La duración es de la VERSIÓN, no de la obra (EN 15907 la saca del Work a
    propósito): una obra con duración suelta elige un número «verdadero» que no
    existe —Llueve sobre Babel: 111, 113 y 120 min en cuatro festivales—."""
    return [f'{wid}: «{k}» en la obra (va en versiones[])' for wid, o in obs.items()
            for k in ('duracion_min', 'duration', 'duracion', 'runtime') if k in o]


def decision_pisada(obs, decs):
    """Ningún valor de la obra contradice una decisión humana vigente. Es la
    cicatriz «arreglo aguas abajo se pierde»: una regeneración no la deshace."""
    reemplazadas = {d.get('reemplaza') for d in decs if d.get('reemplaza') is not None}
    prob = []
    for i, d in enumerate(decs):
        if i in reemplazadas or d['campo'] in ('no-es', 'no-alta-tmdb') or 'valor' not in d:
            continue
        o = obs.get(d['work_id'])
        if o is None:
            prob.append(f'decisión {i}: la obra {d["work_id"]} no existe')
            continue
        actual = o
        for parte in d['campo'].split('.'):
            actual = actual.get(parte) if isinstance(actual, dict) else None
        if actual != d['valor']:
            prob.append(f'{d["work_id"]}.{d["campo"]}: la obra dice {actual!r}, la decisión del {d["fecha"]} dice {d["valor"]!r}')
    return prob


def presentacion_sin_obra(festivales, obs, fus, exigir=False):
    """Toda obra de un festival apunta a una obra vigente del catálogo
    (`work_id`), directo o por fusión. Hasta la fase 3 el campo no existe en los
    festivales: `exigir=False` solo revisa los que YA lo llevan."""
    prob = []
    for fid, d in festivales.items():
        for f in d.get('films', []):
            for o in (f.get('film_list') or [f]):
                if o.get('type') == 'event' or f.get('type') == 'event':
                    continue
                w = o.get('work_id')
                if w is None:
                    if exigir:
                        prob.append(f'{fid}: «{o.get("title")}» sin work_id')
                    continue
                if redirige(w, fus) not in obs:
                    prob.append(f'{fid}: «{o.get("title")}» apunta a {w}, que no existe')
    return prob


def candidatos_abiertos(raiz=DIR):
    """Un onboarding no publica con pares de obras sin resolver: un candidato es
    una pregunta para Juan, no una respuesta."""
    return [f'{c.get("a")} ~ {c.get("b")}: {c.get("por_que", "")}'
            for c in _lista(raiz, 'candidatos.json') if not c.get('resuelto')]


def ids_validos(obs):
    return [f'{wid}: id con forma inválida' for wid in obs if not ID.match(wid)] + \
           [f'{o["_archivo"]}: el archivo no se llama como su id' for wid, o in obs.items()
            if o.get('_archivo') and o['_archivo'] != f'{wid}.json']


# ── autoprueba: cada invariante atrapa su caso roto ──────────────────────────
def autoprueba():
    """Cebos en memoria (prefijo zzz, nunca en disco: un cebo en disco pisó un
    crudo real una vez). Devuelve la lista de invariantes CIEGOS: vacía = sanos."""
    a, b = 'w_000000ZZZ001', 'w_000000ZZZ002'
    sana = {a: {'id': a, 'titulo_original': 'zzz', 'directores': ['zzz'], 'xref': {'tmdb': 1}}}
    ciegos = []
    if xref_repetido(sana) or not xref_repetido({**sana, b: {'id': b, 'xref': {'tmdb': 1}}}):
        ciegos.append('xref_repetido')
    if duracion_en_obra(sana) or not duracion_en_obra({a: {**sana[a], 'duracion_min': 90}}):
        ciegos.append('duracion_en_obra')
    dec = [{'work_id': a, 'campo': 'xref.tmdb', 'valor': 1, 'motivo': 'zzz', 'fecha': '2026-10-12'}]
    if decision_pisada(sana, dec) or not decision_pisada(sana, [dict(dec[0], valor=2)]):
        ciegos.append('decision_pisada')
    fest_ok = {'zzz-2026': {'films': [{'title': 'zzz', 'work_id': a}]}}
    fest_mal = {'zzz-2026': {'films': [{'title': 'zzz', 'work_id': b}]}}
    fus = [{'absorbido': b, 'superviviente': a, 'fecha': '2026-10-12', 'motivo': 'zzz'}]
    if presentacion_sin_obra(fest_ok, sana, []) or not presentacion_sin_obra(fest_mal, sana, []) \
            or presentacion_sin_obra(fest_mal, sana, fus):
        ciegos.append('presentacion_sin_obra')
    if ids_validos(sana) or not ids_validos({'zzz': {}}):
        ciegos.append('ids_validos')
    if huella('La niña santa') != huella('Niña Santa, La') or huella('Rose') == huella('Rosa'):
        ciegos.append('huella')
    if not ID.match(nuevo_id()):
        ciegos.append('nuevo_id')
    return ciegos


if __name__ == '__main__':
    c = autoprueba()
    print('✗ invariantes ciegos: ' + ', '.join(c) if c else '✓ los invariantes del catálogo atrapan sus cebos')
