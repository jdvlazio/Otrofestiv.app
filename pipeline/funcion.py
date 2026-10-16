#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""funcion.py — el modelo de la función: afirmaciones con fuente, una regla por
casilla, conflictos a la vista (docs/FUNCION.md). Único dueño de esas reglas:
lo llaman ensamblar.py y los verificadores; nadie las reimplementa.

    fs, registro, avisos = asignar_ids(funciones_base, registro)   # C1
    r = resolver(fs, afirmaciones, contexto)
    r.funciones   → cada casilla resuelta, con `_procedencia`
    r.conflictos  → lo que ninguna regla pudo decidir (frena el push)
    estimar_duraciones(r.funciones)   → ÚLTIMO paso, solo donde siga vacía (C2)

Cada función base trae `_ancla = (sede, día, hora)` tal como la dio la fuente
principal, y recibe un `_fid` estable. Una afirmación apunta a `funcion` (el
id) o, mientras el ancla sea única, al ancla.

Corregido tras la auditoría del 16 oct 2026 (docs/FUNCION.md §9, C1–C8).
"""
import ast
import datetime
import glob
import hashlib
import json
import os
import re
import subprocess
import unicodedata

# ── las fuentes ──────────────────────────────────────────────────────────────
TIPOS = {'festival-web', 'festival-pdf', 'festival-ig', 'festival-mensaje', 'sala', 'prensa', 'juan'}
_FESTIVAL = {'festival-web', 'festival-pdf', 'festival-ig', 'festival-mensaje'}
_FESTIVAL_ESCRITO = {'festival-web', 'festival-pdf', 'festival-mensaje'}

# ── las reglas de cada casilla (docs/FUNCION.md §4, decisión delegada 15 oct 2026)
# Rango de mayor a menor: cada nivel es un conjunto de tipos. «juan» siempre va
# primero. Dentro de un nivel gana lo PUBLICADO más reciente; empate con valores
# distintos es conflicto. Un tipo que no aparece no puede afirmar esa casilla.
_J = {'juan'}
RANGO = {
    'day':                   [_J, _FESTIVAL, {'sala'}, {'prensa'}],
    'time':                  [_J, _FESTIVAL, {'sala'}, {'prensa'}],
    'venue':                 [_J, _FESTIVAL, {'sala'}],
    'sala':                  [_J, {'sala'}, _FESTIVAL],
    'duration':              [_J, _FESTIVAL, {'sala'}],
    'entrada':               [_J, {'sala'}, _FESTIVAL, {'prensa'}],
    'ticket_url':            [_J, {'sala'}, _FESTIVAL],
    'requires_registration': [_J, _FESTIVAL, {'sala'}],
    'registration_url':      [_J, _FESTIVAL],
    'has_qa':                [_J, _FESTIVAL_ESCRITO, {'festival-ig'}, {'sala'}],
    'qa_type':               [_J, _FESTIVAL, {'sala'}],
    'film_start':            [_J, _FESTIVAL],
    'premiere':              [_J, _FESTIVAL],
    'estado':                [_J, _FESTIVAL | {'sala'}],
    'title':                 [_J, _FESTIVAL],
    'film_list':             [_J, _FESTIVAL_ESCRITO, {'festival-ig'}],
    'type':                  [_J, _FESTIVAL],
    'event_kind':            [_J, _FESTIVAL],
    'invitados':             [_J, _FESTIVAL_ESCRITO, {'festival-ig'}],
    'existe':                [_J, _FESTIVAL | {'sala'}],
}
OBLIGATORIAS = ('title', 'type', 'day', 'time', 'venue')

# C10: TODA casilla es de la FUNCIÓN —de esta proyección—. `title` es el que el
# festival le puso a la función (un programa), `duration` lo que dura esta
# función, `film_list` qué obras trae, `premiere` qué estreno es. Lo de la OBRA
# (director, año, país, sinopsis, afiche, género, ids) no es una casilla: se
# rechaza como desconocida y va por las decisiones del catálogo (catalogo.py).
NIVEL = {c: 'funcion' for c in RANGO}

# C4: el FORMATO de cada casilla. Lo que la app no puede usar no entra.
_HORA = re.compile(r'^([01]\d|2[0-3]):[0-5]\d$')
_DUR = re.compile(r'^\d+ min$')
_HTTPS = re.compile(r'^https://\S+$')


def hoy(ahora_utc=None):
    """La fecha de HOY en Colombia (UTC-5), no la de la máquina."""
    ahora_utc = ahora_utc or datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    return (ahora_utc - datetime.timedelta(hours=5)).date().isoformat()


def _dia_real(s):
    try:
        datetime.date.fromisoformat(str(s))
        return bool(re.match(r'^\d{4}-\d{2}-\d{2}$', str(s)))
    except ValueError:
        return False


FORMATO = {
    'day': _dia_real, 'time': lambda v: bool(_HORA.match(str(v))), 'film_start': lambda v: bool(_HORA.match(str(v))),
    'venue': lambda v: isinstance(v, str) and ' - ' in v, 'sala': lambda v: isinstance(v, str) and v.strip() != '',
    'duration': lambda v: isinstance(v, str) and bool(_DUR.match(v)),
    'entrada': lambda v: v in ENTRADAS, 'ticket_url': lambda v: isinstance(v, str) and bool(_HTTPS.match(v)),
    'registration_url': lambda v: isinstance(v, str) and bool(_HTTPS.match(v)),
    'requires_registration': lambda v: isinstance(v, bool), 'has_qa': lambda v: isinstance(v, bool),
    'qa_type': lambda v: v in ('team', 'guests'), 'estado': lambda v: v in ('vigente', 'cancelada', 'reprogramada'),
    'title': lambda v: isinstance(v, str) and v.strip() != '', 'type': lambda v: v in ('film', 'event'),
    'event_kind': lambda v: isinstance(v, str) and v.strip() != '', 'premiere': lambda v: isinstance(v, str) and v.strip() != '',
    'film_list': lambda v: isinstance(v, list), 'invitados': lambda v: isinstance(v, str) and v.strip() != '',
}

# LAS SEDES QUE SIEMPRE COBRAN: ahí, lo que nadie dice es «boleta», no «libre».
# Una tabla, con la fuente de cada una (docs/FUNCION.md §4).
SEDES_QUE_COBRAN = {
    'Cinemateca de Bogotá': 'cinematecadebogota.gov.co: cada función paga trae su link de TuBoleta y '
                            'lo libre lo dice («Entrada libre»); regla de Juan, MIDBO 13 oct 2026',
}

# ── la entrada: un enum que se traduce a los campos que la app lee. La
# inscripción NO es una entrada (C8): es su propia casilla, combinable con boleta
ENTRADAS = ('libre', 'boleta', 'invitacion', 'en_linea')
_CAMPOS_ENTRADA = ('is_free', 'by_invitation', 'online')


def _entrada_a_campos(v):
    return {'libre': {'is_free': True}, 'boleta': {'is_free': False},
            'invitacion': {'by_invitation': True}, 'en_linea': {'online': True}}[v]


def _entrada_de(f):
    """La entrada que ya trae una función (fuente principal), o None."""
    if f.get('by_invitation'):
        return 'invitacion'
    if f.get('online'):
        return 'en_linea'
    if f.get('is_free') is True:
        return 'libre'
    if f.get('is_free') is False or f.get('ticket_url'):
        return 'boleta'
    return None


# ── errores (nunca en silencio) ──────────────────────────────────────────────
class AfirmacionInvalida(ValueError):
    pass


class AnclaPerdida(LookupError):
    pass


class Resultado:
    def __init__(self, funciones, conflictos):
        self.funciones, self.conflictos = funciones, conflictos


def _nivel(casilla, tipo):
    for i, n in enumerate(RANGO.get(casilla, [])):
        if tipo in n:
            return i
    return None


def validar(a, fecha_hoy=None):
    """Lanza AfirmacionInvalida si la afirmación no cumple el modelo."""
    hoy_ = fecha_hoy or hoy()
    q = f"{a.get('funcion') or a.get('ancla')} · {a.get('casilla')}"
    cas = a.get('casilla')
    if cas not in RANGO:
        raise AfirmacionInvalida(f'{q}: casilla desconocida')
    an = a.get('ancla') or {}
    if not a.get('funcion'):
        if not all(an.get(k) for k in ('sede', 'dia', 'hora')):
            raise AfirmacionInvalida(f'{q}: sin `funcion` (id) ni ancla completa (sede, dia, hora)')
        if not _dia_real(an['dia']) or not _HORA.match(str(an['hora'])):
            raise AfirmacionInvalida(f'{q}: ancla con día u hora fuera de formato (AAAA-MM-DD, HH:MM)')
    fu = a.get('fuente') or {}
    if fu.get('tipo') not in TIPOS:
        raise AfirmacionInvalida(f'{q}: tipo de fuente desconocido «{fu.get("tipo")}»')
    if _nivel(cas, fu['tipo']) is None:
        raise AfirmacionInvalida(f'{q}: una fuente «{fu["tipo"]}» no puede afirmar «{cas}» (docs/FUNCION.md §4)')
    for k in ('fecha', 'publicado'):
        if k in fu and (not _dia_real(fu[k]) or fu[k] > hoy_):
            raise AfirmacionInvalida(f'{q}: fuente.{k} «{fu[k]}» no es una fecha real o es futura')
    if 'fecha' not in fu:
        raise AfirmacionInvalida(f'{q}: fuente sin fecha (AAAA-MM-DD)')
    if fu['tipo'] == 'juan':
        if not fu.get('frase'):
            raise AfirmacionInvalida(f'{q}: una decisión de Juan lleva su frase')
        if cas != 'existe' and 'contra' not in a:
            raise AfirmacionInvalida(f'{q}: una decisión de Juan lleva `contra`: el valor que pisó (C5)')
    elif not _HTTPS.match(str(fu.get('url') or '')):
        raise AfirmacionInvalida(f'{q}: fuente sin url https')
    if cas == 'existe':
        v = a.get('valor')
        if v is False:
            if not a.get('por_que'):
                raise AfirmacionInvalida(f'{q}: quitar una función lleva su por_que')
        elif not (isinstance(v, dict) and not faltan_obligatorias(v)):
            raise AfirmacionInvalida(f'{q}: agregar una función lleva sus casillas obligatorias {OBLIGATORIAS}')
        return
    if a.get('valor') is None or not FORMATO[cas](a['valor']):
        raise AfirmacionInvalida(f'{q}: «{a.get("valor")!r}» no tiene el formato de «{cas}»')


def faltan_obligatorias(f):
    return [k for k in OBLIGATORIAS if not f.get(k)]


def _orden(fu):
    """C6: se compara lo PUBLICADO; si la fuente no dice cuándo publicó, la captura."""
    return fu.get('publicado') or fu['fecha']


def _elegir(casilla, candidatos):
    """candidatos: [(valor, fuente)] → (ganador | None, conflicto | None)."""
    con_nivel = [(v, fu, _nivel(casilla, fu['tipo'])) for v, fu in candidatos]
    con_nivel = [c for c in con_nivel if c[2] is not None]
    if not con_nivel:
        return None, None
    mejor = min(c[2] for c in con_nivel)
    del_nivel = [c for c in con_nivel if c[2] == mejor]
    ultima = max(_orden(c[1]) for c in del_nivel)
    ultimos = [c for c in del_nivel if _orden(c[1]) == ultima]
    if len({json.dumps(c[0], sort_keys=True, default=str) for c in ultimos}) > 1:
        return None, {'casilla': casilla, 'opciones': [{'valor': c[0], 'fuente': c[1]} for c in ultimos]}
    return ultimos[0], None


def _mins(h):
    m = re.match(r'^(\d{1,2}):(\d{2})$', str(h or ''))
    if not m:
        raise AfirmacionInvalida(f'hora «{h}» fuera de formato')
    return int(m.group(1)) * 60 + int(m.group(2))


# ── C1: el id estable de cada función ────────────────────────────────────────
def _plano(t):
    t = unicodedata.normalize('NFD', str(t or '').lower())
    return re.sub(r'[^a-z0-9]+', ' ', ''.join(c for c in t if unicodedata.category(c) != 'Mn')).strip()


def _clave(f):
    if not f.get('_ancla'):
        raise AfirmacionInvalida(f'«{f.get("title")}»: función sin _ancla (sede, día, hora)')
    sede, dia, hora = tuple(f['_ancla'])
    return {'sede': sede, 'dia': dia, 'hora': hora, 'sala': f.get('sala') or '', 'titulo': _plano(f.get('title'))}


def _nuevo_id(c):
    return 'f_' + hashlib.sha1('|'.join(c[k] for k in ('sede', 'dia', 'hora', 'sala', 'titulo')).encode()).hexdigest()[:10]


def asignar_ids(funciones, registro):
    """Da a cada función base su `_fid` estable → (funciones, registro, avisos).

    El registro (<fest>-funciones-ids.json) guarda, por id, la clave con que se
    vio por última vez: sede, día, hora, sala y título. Se reconoce por la
    clave exacta; si no, por UNA sola candidata sin dueño en este montaje que
    coincida en (sede, título) —se movió— o en (sede, día, hora, sala) —se
    renombró—. Con más de una candidata es AMBIGUA: id nuevo y aviso, nunca se
    elige en silencio. Dos funciones base con la misma clave son un error."""
    viejas = dict((registro or {}).get('funciones') or {})
    por_clave = {tuple(v[k] for k in ('sede', 'dia', 'hora', 'sala', 'titulo')): i for i, v in viejas.items()}
    claves = [_clave(f) for f in funciones]
    if len({tuple(c.values()) for c in claves}) != len(claves):
        dup = [c for c in claves if claves.count(c) > 1][0]
        raise AfirmacionInvalida(f'dos funciones base con la misma clave {dup}')
    usados, ids, avisos = set(), [None] * len(funciones), []
    for n, (f, c) in enumerate(zip(funciones, claves)):
        i = por_clave.get(tuple(c.values()))
        if i:
            usados.add(i)
            ids[n] = i
            if viejas[i].get('ausente'):
                avisos.append(f'{i} «{f.get("title")}» {c["dia"]} {c["hora"]}: volvió a la fuente principal')
    nuevo = {}
    for n, (f, c) in enumerate(zip(funciones, claves)):
        if ids[n]:
            continue
        # una función AUSENTE no presta su id: si otra aparece con su título en otra
        # hora, es otra función (revisión del 16 oct); solo vuelve con su clave exacta
        libres = {i: v for i, v in viejas.items() if i not in usados and not v.get('ausente')}
        movida = [i for i, v in libres.items() if (v['sede'], v['titulo']) == (c['sede'], c['titulo'])]
        renombrada = [i for i, v in libres.items()
                      if (v['sede'], v['dia'], v['hora'], v['sala']) == (c['sede'], c['dia'], c['hora'], c['sala'])]
        cand = movida or renombrada
        if len(cand) == 1:
            i, v = cand[0], viejas[cand[0]]
            avisos.append(f'{i} «{f.get("title")}»: ' + (
                f'movida de {v["dia"]} {v["hora"]} {v["sala"]} a {c["dia"]} {c["hora"]} {c["sala"]}'.strip()
                if movida else f'renombrada (antes «{v["titulo"]}»)'))
            usados.add(i)
            ids[n] = i
            continue
        if len(cand) > 1:
            avisos.append(f'«{f.get("title")}» {c["dia"]} {c["hora"]}: ambigua entre {", ".join(sorted(cand))} — id nuevo')
        i = _nuevo_id(c)
        while i in viejas or i in ids:
            i = 'f_' + hashlib.sha1(i.encode()).hexdigest()[:10]
        ids[n] = i
    out = []
    for f, c, i in zip(funciones, claves, ids):
        out.append({**f, '_fid': i})
        nuevo[i] = c
    for i, v in viejas.items():
        if i not in nuevo:
            if not v.get('ausente'):
                avisos.append(f'{i} «{v["titulo"]}» {v["dia"]} {v["hora"]}: ya no está en la fuente principal')
            nuevo[i] = {**v, 'ausente': True}
    return out, {'funciones': nuevo}, avisos


# ── la resolución ────────────────────────────────────────────────────────────
def resolver(funciones, afirmaciones, contexto):
    """Las funciones base + las afirmaciones → Resultado. `contexto`:
    fuente_principal {tipo, fecha, url}, sedes_que_cobran (set de sedes),
    ticketing_model ('paid' | 'mixed' | None). No modifica sus entradas, y
    correrlo sobre su propia salida da lo mismo (idempotente)."""
    for a in afirmaciones:
        validar(a)
    principal = contexto['fuente_principal']
    malas = []
    for f in funciones:
        _clave(f)                                     # sin ancla: error claro
        for cas in ('day', 'time'):
            if f.get(cas) and not FORMATO[cas](f[cas]):
                malas.append({'funcion': f.get('_fid') or tuple(f['_ancla']), 'casilla': cas, 'tipo': 'formato-base',
                              'opciones': [{'valor': f[cas], 'fuente': principal}]})
    if any('_fid' not in f for f in funciones):
        funciones, _, _ = asignar_ids(funciones, {})
    por_id = {f['_fid']: json.loads(json.dumps(f, default=list)) for f in funciones}
    for f in por_id.values():
        f['_ancla'] = tuple(f['_ancla'])
    orden = [f['_fid'] for f in funciones]
    por_ancla = {}
    for f in funciones:
        por_ancla.setdefault(tuple(f['_ancla']), []).append(f['_fid'])
    conflictos, afs = list(malas), {}
    for a in afirmaciones:
        if a.get('funcion'):
            k = a['funcion']
        else:
            an = (a['ancla']['sede'], a['ancla']['dia'], a['ancla']['hora'])
            ids = por_ancla.get(an, [])
            if len(ids) > 1:
                raise AnclaPerdida(f'{an}: el ancla es AMBIGUA ({len(ids)} funciones) — la afirmación '
                                   f'«{a["casilla"]}» tiene que apuntar al id (`funcion`)')
            k = ids[0] if ids else ('ancla',) + an
        afs.setdefault(k, []).append(a)
    # funciones nuevas (`existe` con datos sobre un id o ancla que no está)
    for k, xs in afs.items():
        if k in por_id:
            if any(a['casilla'] == 'existe' and a['valor'] is not False for a in xs):
                raise AfirmacionInvalida(f'{k}: `existe` con datos sobre una función que ya existe '
                                         '— para corregirla, afirmá sus casillas')
            continue
        nuevas = [a for a in xs if a['casilla'] == 'existe' and a['valor'] is not False]
        if not nuevas:
            raise AnclaPerdida(f'{k}: ninguna función base con ese id o ancla '
                               f'({", ".join(sorted({a["casilla"] for a in xs}))})')
        g, c = _elegir('existe', [(a['valor'], a['fuente']) for a in nuevas])
        if c:
            conflictos.append({'funcion': k, **c})
            continue
        v = g[0]
        an = k[1:] if isinstance(k, tuple) else (v['venue'], v['day'], v['time'])
        fid = k if not isinstance(k, tuple) else _nuevo_id(
            {'sede': an[0], 'dia': an[1], 'hora': an[2], 'sala': v.get('sala') or '', 'titulo': _plano(v.get('title'))})
        por_id[k] = {**v, '_ancla': an, '_fid': fid, '_procedencia': {'existe': dict(g[1])}}
        orden.append(k)
    salida = []
    for k in orden:
        f = por_id[k]
        proc = dict(f.get('_procedencia') or {})
        # la fecha de la fuente principal es la de la función (`_src.date`); el
        # crudo regenerado no cuenta
        _s = f.get('_src') if isinstance(f.get('_src'), dict) else {}
        _d = str(_s.get('date') or '')
        fp = dict(principal, fecha=_d) if _dia_real(_d) else principal
        mias = afs.get(k, [])
        g, c = _elegir('existe', [(a['valor'] is not False, a['fuente']) for a in mias if a['casilla'] == 'existe'])
        if c:
            conflictos.append({'funcion': k, **c})
        if g and g[0] is False:
            continue
        for casilla in RANGO:
            if casilla == 'existe':
                continue
            propias = [a for a in mias if a['casilla'] == casilla]
            cand = [(a['valor'], a['fuente']) for a in propias]
            base_v = _entrada_de(f) if casilla == 'entrada' else f.get(casilla)
            previa = proc.get(casilla)
            if base_v not in (None, ''):
                # lo que ya resolvió una corrida anterior vuelve con su fuente; una
                # REGLA (supuesto, estimado) no es una fuente: se recalcula
                if previa and previa.get('tipo') in TIPOS:
                    cand.append((base_v, previa))
                elif not previa:
                    cand.append((base_v, fp))
            if not cand:
                continue
            g, c = _elegir(casilla, cand)
            if c:
                conflictos.append({'funcion': k, **c})
                continue
            if not g:
                continue
            v, fu = g[0], g[1]
            # C5: una decisión de Juan vence si lo que pisó cambió
            if fu.get('tipo') == 'juan':
                dec = next((a for a in propias if a['fuente'] is fu), None)
                otro, _ = _elegir(casilla, [x for x in cand if x[1].get('tipo') != 'juan'])
                if dec and otro and json.dumps(otro[0], default=str) != json.dumps(dec.get('contra'), default=str):
                    conflictos.append({'funcion': k, 'casilla': casilla, 'tipo': 'decision-a-revisar',
                                       'opciones': [{'valor': v, 'fuente': fu, 'contra': dec.get('contra')},
                                                    {'valor': otro[0], 'fuente': otro[1]}]})
            if casilla == 'entrada':
                for x in _CAMPOS_ENTRADA:
                    f.pop(x, None)
                f.update(_entrada_a_campos(v))
            else:
                f[casilla] = v
            proc[casilla] = {x: fu[x] for x in ('tipo', 'fecha', 'publicado', 'url', 'frase') if fu.get(x)}
        # la entrada que nadie dijo: SUPUESTO (libre, salvo sede que cobra o festival pago)
        if 'entrada' not in proc or proc['entrada'].get('tipo') == 'regla':
            sup = 'boleta' if (f['_ancla'][0].rsplit(' - ', 1)[0] in (contexto.get('sedes_que_cobran') or set())
                               or contexto.get('ticketing_model') == 'paid') else 'libre'
            for x in _CAMPOS_ENTRADA:
                f.pop(x, None)
            f.update(_entrada_a_campos(sup))
            proc['entrada'] = {'tipo': 'regla', 'marca': 'supuesto', 'valor': sup}
        # C3: una función que no es con boleta no lleva el link de compra que
        # traía la base (sí el que afirmó una fuente)
        if f.get('is_free') is not False and f.get('ticket_url') and \
                (proc.get('ticket_url') or {}).get('tipo') in (None, fp.get('tipo')) and \
                not any(a['casilla'] == 'ticket_url' for a in mias):
            f.pop('ticket_url', None)
            proc.pop('ticket_url', None)
        f['_procedencia'] = proc
        salida.append(f)
    return Resultado(salida, conflictos)


def estimar_duraciones(funciones):
    """C2: el ÚLTIMO paso, aparte del resolver y después de reponer lo publicado
    y las duraciones corregidas. Solo donde la duración siga vacía: el hueco
    hasta la siguiente función de la MISMA sede ese día (horas comparadas como
    horas), tope 90 min; 60 si es la última. Queda `marca: estimado`."""
    def m(h):
        return _mins(h) if FORMATO['time'](h or '') else None
    for f in funciones:
        if f.get('duration') or m(f.get('time')) is None:
            continue                                    # una hora mala es un conflicto del resolver, no se estima
        t = m(f['time'])
        sig = sorted(m(g['time']) for g in funciones
                     if g is not f and g.get('day') == f.get('day') and g.get('venue') == f.get('venue')
                     and m(g.get('time')) is not None and m(g['time']) > t)
        f['duration'] = f'{min(sig[0] - t, 90) if sig else 60} min'
        f.setdefault('_procedencia', {})['duration'] = {'tipo': 'regla', 'marca': 'estimado'}
    return funciones


# ── el archivo de un festival y su contexto ──────────────────────────────────
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def cargar(fid, raiz=REPO):
    """Las afirmaciones de festivals/staging/<fid>-afirmaciones.json, validadas,
    o None si el festival todavía no usa el modelo."""
    p = os.path.join(raiz, 'festivals', 'staging', f'{fid}-afirmaciones.json')
    if not os.path.exists(p):
        return None
    d = json.load(open(p, encoding='utf-8'))
    if not (d.get('_provenance') or {}).get('capturado'):
        raise AfirmacionInvalida(f'{os.path.basename(p)}: sin _provenance.capturado')
    xs = d.get('afirmaciones') or []
    for a in xs:
        validar(a)
    return xs


def contexto(crudo, plan, ticketing_model=None):
    """El contexto de resolver(). La fecha de la fuente principal sale de cada
    función (`_src.date`); la del crudo es solo el respaldo para las que no la
    traen. El tipo lo dice el plan (`festival-web` si no)."""
    pv = crudo.get('_provenance') or {}
    fecha = str(pv.get('capturado') or '')[:10]
    if not _dia_real(fecha):
        raise AfirmacionInvalida('la fuente principal (crudo._provenance) no tiene fecha de captura')
    tipo = (plan or {}).get('fuente_principal') or 'festival-web'
    if tipo not in TIPOS:
        raise AfirmacionInvalida(f'fuente principal de tipo desconocido «{tipo}»')
    return {'fuente_principal': {'tipo': tipo, 'url': pv.get('url') or '', 'fecha': fecha},
            'sedes_que_cobran': set(SEDES_QUE_COBRAN), 'ticketing_model': ticketing_model}


def ticketing_model_de(fid, config_js=None):
    """C7: el `ticketing_model` del festival ('paid' | 'mixed') o None. Con el
    repo, se lee FESTIVAL_CONFIG como DATO (node evalúa src/config.js); con un
    texto de prueba, se lee el bloque del festival hasta la clave siguiente."""
    clave = fid.replace('-', '')
    if config_js is None:
        try:
            r = subprocess.run(['node', '--input-type=module', '-e',
                            "const m = await import(process.argv[1]); const c = (m.FESTIVAL_CONFIG||{})[process.argv[2]];"
                            "process.stdout.write(JSON.stringify(c ? (c.ticketing_model || null) : '__nada__'))",
                                os.path.join(REPO, 'src', 'config.js'), clave], capture_output=True, text=True)
        except OSError as e:
            raise AfirmacionInvalida(f'no se pudo correr node para leer src/config.js: {e}')
        if r.returncode:
            raise AfirmacionInvalida(f'no se pudo leer src/config.js como dato: {r.stderr.strip()[:200]}')
        v = json.loads(r.stdout or 'null')
        if v == '__nada__':
            return None
        return v if v in ('paid', 'mixed') else None
    i = config_js.find(f"'{clave}': {{")
    if i < 0:
        return None
    m = re.compile(r"\n\s*'[a-z0-9]+':\s*\{").search(config_js, i + 1)
    bloque = config_js[i:m.start() if m else None]
    t = re.search(r"ticketing_model:\s*'(paid|mixed)'", bloque)
    return t.group(1) if t else None


def de_ancla(afirmaciones, ancla):
    return [a for a in afirmaciones if a.get('ancla') and
            (a['ancla']['sede'], a['ancla']['dia'], a['ancla']['hora']) == tuple(ancla)]


# ── C9: la deuda que solo puede bajar ────────────────────────────────────────
# Una «tabla de excepciones» es una asignación de módulo, en un script de UN
# festival (pipeline/<fest>-AAAA-*.py, no su verificador), cuyo nombre corrige
# una casilla de la función y cuyo valor es un dato (dict, lista, conjunto,
# tupla, comprensión, dict()/list()), en cualquier lugar del script. Una regex
# o un texto no son tablas; la tabla de SEDES de la fuente tampoco (es el
# mapeo normal). El nombre es la señal: una tabla nueva con otro nombre, o una
# mutación (`X['k'] = v`, `X.update(...)`), no se ve — límite declarado.
# 16 oct 2026: 98 tablas (el detector ampliado las ve; no es deuda nueva).
_NOMBRE_EXCEPCION = re.compile(
    r'^(HORA|DURACION|SALA|ACCESO|BOLETA|INICIO|DEL_IG|DEL_DOMINGO|QA|CON_QA|SIN_QA|CON_CONVERSATORIO|'
    r'INSCRIPCION|AGREGAR|FUNCIONES_|ACTUALIZACION|EXCLUIDOS|FUERA|NO_PUBLICAR|SEDE_FUERA|SOLO_EN|DISCREPA|'
    r'ERRATA|CORRECCIONES|PRESENCIA|VR_SESIONES|METROPOLIS|SEDES_PAGAS|CELDAS|OBRAS_A|DATOS_TARJETA|'
    r'SIN_HORA|ACTIVIDADES?$|TALLERES|ENTRADA|GRATIS|LIBRES|PRECIO|TICKET|BOLETERIA|REGISTRO|OVERRIDE|PARCHE|'
    r'AJUSTE|CAMBIOS|ARREGLO|EXTRA_|MANUAL|CORRECCION|SEDES?_|TITULOS?(_|$)|QUITAR)')
_DATO = (ast.Dict, ast.List, ast.Set, ast.Tuple, ast.DictComp, ast.ListComp, ast.SetComp, ast.BinOp)


def excepciones_en_scripts(raiz=REPO):
    """[(archivo, nombre)] de las tablas de excepciones en scripts de festival."""
    out = []
    for p in sorted(glob.glob(os.path.join(raiz, 'pipeline', '*.py'))):
        n = os.path.basename(p)
        if not re.match(r'^[a-z0-9]+(-[a-z0-9]+)*-(20\d\d|\d\d)-.+\.py$', n) or n.endswith('-verificar.py'):
            continue
        t = ast.parse(open(p, encoding='utf-8').read())
        # todo el árbol: también las tablas dentro de un `if` o de `main()`
        for st in ast.walk(t):
            es_dato = lambda v: isinstance(v, _DATO) or (isinstance(v, ast.Call) and isinstance(v.func, ast.Name)
                                                          and v.func.id in ('dict', 'list', 'set', 'tuple'))
            if isinstance(st, ast.Assign) and es_dato(st.value):
                out += [(n, x.id) for x in st.targets if isinstance(x, ast.Name) and _NOMBRE_EXCEPCION.match(x.id)]
            elif isinstance(st, ast.AnnAssign) and st.value is not None and es_dato(st.value) and \
                    isinstance(st.target, ast.Name) and _NOMBRE_EXCEPCION.match(st.target.id):
                out.append((n, st.target.id))
    return out


def comparar_deuda(hoy, deuda):
    """→ (nuevas, saldadas). Una nueva frena; una saldada pide bajar la deuda."""
    h, d = [tuple(x) for x in hoy], [tuple(x) for x in deuda]
    return [x for x in h if x not in d], [x for x in d if x not in h]


def sin_entrada(festival):
    """Títulos de las funciones publicadas que no dicen cómo se entra. La
    inscripción no es una entrada (C8)."""
    return [f.get('title') for f in festival.get('films') or []
            if not (f.get('is_free') in (True, False) or f.get('ticket_url') or f.get('by_invitation') or f.get('online'))]


def conflictos_abiertos(raiz=REPO):
    return sorted(os.path.basename(p)[:-len('-conflictos.json')]
                  for p in glob.glob(os.path.join(raiz, 'festivals', 'staging', '*-conflictos.json')))


DEUDA = os.path.join(REPO, 'pipeline', 'funcion-deuda.json')


# ── autoprueba: cada regla atrapa su cebo (en memoria, nunca en disco) ───────
def autoprueba():
    ciegos = []
    S, H = 'zzz', ('zzz', '2026-01-01', '10:00')
    b = {'title': 'zzz', 'type': 'film', 'day': H[1], 'time': H[2], 'venue': 'zzz - X', 'sala': 'A',
         'duration': '90 min', '_ancla': H}
    ctx = {'fuente_principal': {'tipo': 'festival-web', 'fecha': '2026-01-01', 'url': 'https://x.example'}}

    def a(cas, val, tipo='sala', fecha='2026-01-02', url='https://y.example', **kw):
        return {'ancla': {'sede': S, 'dia': H[1], 'hora': H[2]}, 'casilla': cas, 'valor': val,
                'fuente': {'tipo': tipo, 'fecha': fecha, 'url': url, 'frase': url}, **kw}
    try:
        if resolver([b], [a('sala', 'B')], ctx).funciones[0]['sala'] != 'B':
            ciegos.append('rango (sala gana la sede)')
        if resolver([b], [a('time', '11:00')], ctx).funciones[0]['time'] != '10:00':
            ciegos.append('rango (hora no la cambia la sala)')
        if not resolver([b], [a('sala', 'B'), a('sala', 'C', url='https://z.example')], ctx).conflictos:
            ciegos.append('conflicto')
        if resolver([b], [], ctx).funciones[0]['_procedencia']['entrada'].get('marca') != 'supuesto':
            ciegos.append('entrada supuesta')
        if estimar_duraciones([dict(b, duration=None)])[0].get('_procedencia', {}).get('duration', {}).get('marca') != 'estimado':
            ciegos.append('duración estimada')
        b2 = dict(b, sala='B', title='otra')
        if len(resolver([b, b2], [], ctx).funciones) != 2:
            ciegos.append('dos salas a la misma hora (C1)')
        for nombre, mala in (('ancla perdida', {**a('sala', 'B'), 'ancla': {'sede': S, 'dia': H[1], 'hora': '23:00'}}),
                             ('afirmación sin url', {**a('sala', 'B'), 'fuente': {'tipo': 'sala', 'fecha': '2026-01-02'}}),
                             ('fuente sin rango', a('sala', 'B', tipo='prensa')),
                             ('formato', a('time', '7pm', tipo='festival-ig')),
                             ('decisión sin contra', a('sala', 'B', tipo='juan'))):
            try:
                resolver([b], [mala], ctx)
                ciegos.append(nombre)
            except (AnclaPerdida, AfirmacionInvalida):
                pass
    except Exception as e:  # una autoprueba que revienta es una autoprueba ciega
        ciegos.append(f'revienta: {e}')
    return ciegos


def informe(funciones, principal):
    """C9: lo que el modelo decidió y NO viene de la fuente principal, más los
    supuestos y estimados → [{funcion, titulo, dia, hora, casilla, valor,
    tipo, fecha, fuente, marca}]."""
    filas = []
    for f in funciones:
        for cas, pr in sorted((f.get('_procedencia') or {}).items()):
            if pr.get('tipo') == principal.get('tipo') and pr.get('url') == principal.get('url') and not pr.get('marca'):
                continue
            v = _entrada_de(f) if cas == 'entrada' else f.get(cas)
            filas.append({'funcion': f.get('_fid'), 'titulo': f.get('title'), 'dia': f.get('day'), 'hora': f.get('time'),
                          'casilla': cas, 'valor': v, 'tipo': pr.get('tipo'),
                          'fecha': pr.get('publicado') or pr.get('fecha'), 'fuente': pr.get('url') or pr.get('frase'),
                          'marca': pr.get('marca')})
    return filas


def informe_texto(funciones, principal):
    filas = informe(funciones, principal)
    if not filas:
        return 'Todo viene de la fuente principal: ninguna afirmación, supuesto ni estimación.'
    out, ultimo = [], None
    for x in filas:
        if x['funcion'] != ultimo:
            out.append(f"\n{x['dia']} {x['hora']} · {x['titulo']}  ({x['funcion']})")
            ultimo = x['funcion']
        quien = x['marca'] or f"{x['tipo']} {x['fecha'] or ''}".strip()
        out.append(f"  {x['casilla']:<22} {str(x['valor'])[:50]:<52} ← {quien}" + (f"  {x['fuente']}" if x['fuente'] else ''))
    n = len({x['funcion'] for x in filas})
    return f'{len(filas)} casillas en {n} funciones no vienen de la fuente principal:' + '\n'.join(out)


def bajar_deuda():
    """Escribe la deuda medida, solo si BAJA (nunca sube: lo nuevo se arregla)."""
    d = json.load(open(DEUDA, encoding='utf-8'))
    hoy = excepciones_en_scripts()
    nuevas, _ = comparar_deuda(hoy, d['excepciones'])
    if nuevas:
        raise SystemExit(f'✗ hay tablas de excepciones NUEVAS (no se suman a la deuda: van como afirmaciones): {nuevas}')
    d['excepciones'] = [list(x) for x in hoy]
    for p in sorted(glob.glob(os.path.join(REPO, 'festivals', '*.json'))):
        fid = os.path.basename(p)[:-5]
        try:
            n = len(sin_entrada(json.load(open(p, encoding='utf-8'))))
        except Exception:
            continue
        if fid in d['sin_entrada'] and n < d['sin_entrada'][fid]:
            d['sin_entrada'][fid] = n
        d['sin_entrada'] = {k: v for k, v in d['sin_entrada'].items() if v}
    json.dump(d, open(DEUDA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'✓ deuda: {len(d["excepciones"])} tablas, {sum(d["sin_entrada"].values())} funciones sin entrada')


if __name__ == '__main__':
    import sys
    if '--bajar-deuda' in sys.argv:
        bajar_deuda()
    elif len(sys.argv) >= 3 and sys.argv[1] == 'informe':
        fid = sys.argv[2]
        b = json.load(open(os.path.join(REPO, 'festivals', 'staging', f'{fid}-build.json'), encoding='utf-8'))
        plan = json.load(open(os.path.join(REPO, 'pipeline', f'{fid}.plan.json'), encoding='utf-8'))['festival']
        crudo = json.load(open(os.path.join(REPO, plan['crudo']), encoding='utf-8'))
        print(informe_texto(b['films'], contexto(crudo, plan)['fuente_principal']))
    else:
        c = autoprueba()
        print('✗ reglas ciegas: ' + ', '.join(c) if c else '✓ cada regla de la función atrapa su cebo')
