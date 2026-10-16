#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""funcion.py — el modelo de la función: afirmaciones con fuente, una regla por
casilla, conflictos a la vista (docs/FUNCION.md). Único dueño de esas reglas:
lo llaman ensamblar.py y los verificadores; nadie las reimplementa.

    r = resolver(funciones_base, afirmaciones, contexto)
    r.funciones   → las funciones con cada casilla resuelta y `_procedencia`
    r.conflictos  → lo que ninguna regla pudo decidir (frena el push)

Una función base trae `_ancla = (sede, día, hora)` tal como la dio la fuente
principal. Las afirmaciones apuntan a esa ancla, que no cambia aunque una
afirmación mueva la hora.
"""
import json
import os
import re

# ── las fuentes ──────────────────────────────────────────────────────────────
TIPOS = {'festival-web', 'festival-pdf', 'festival-ig', 'festival-mensaje', 'sala', 'prensa', 'juan'}
_FESTIVAL = {'festival-web', 'festival-pdf', 'festival-ig', 'festival-mensaje'}

# ── las reglas de cada casilla (docs/FUNCION.md §4, decisión delegada 15 oct 2026)
# Rango de mayor a menor: cada nivel es un conjunto de tipos. «juan» siempre va
# primero. Dentro de un nivel gana lo más reciente; empate con valores distintos
# es conflicto.
_J = {'juan'}
RANGO = {
    'day':              [_J, _FESTIVAL, {'sala'}, {'prensa'}],
    'time':             [_J, _FESTIVAL, {'sala'}, {'prensa'}],
    'venue':            [_J, _FESTIVAL, {'sala'}],
    'sala':             [_J, {'sala'}, _FESTIVAL],
    'duration':         [_J, _FESTIVAL, {'sala'}],
    'entrada':          [_J, {'sala'}, _FESTIVAL, {'prensa'}],
    'ticket_url':       [_J, {'sala'}, _FESTIVAL],
    'registration_url': [_J, _FESTIVAL],
    'has_qa':           [_J, {'festival-web', 'festival-pdf', 'festival-mensaje'}, {'festival-ig'}, {'sala'}],
    'qa_type':          [_J, _FESTIVAL, {'sala'}],
    'film_start':       [_J, _FESTIVAL],
    'premiere':         [_J, _FESTIVAL],
    'estado':           [_J, _FESTIVAL | {'sala'}],
    'title':            [_J, _FESTIVAL],
    'film_list':        [_J, {'festival-web', 'festival-pdf', 'festival-mensaje'}, {'festival-ig'}],
    'type':             [_J, _FESTIVAL],
    'event_kind':       [_J, _FESTIVAL],
    'invitados':        [_J, {'festival-web', 'festival-pdf', 'festival-mensaje'}, {'festival-ig'}],
    'existe':           [_J, _FESTIVAL | {'sala'}],
}
OBLIGATORIAS = ('title', 'type', 'day', 'time', 'venue')

# LAS SEDES QUE SIEMPRE COBRAN: ahí, lo que nadie dice es «boleta», no «libre».
# Una tabla, con la fuente de cada una (docs/FUNCION.md §4).
SEDES_QUE_COBRAN = {
    'Cinemateca de Bogotá': 'cinematecadebogota.gov.co: cada función paga trae su link de TuBoleta y '
                            'lo libre lo dice («Entrada libre»); regla de Juan, MIDBO 13 oct 2026',
}

# ── la entrada: un enum que se traduce a los campos que la app lee ───────────
ENTRADAS = ('libre', 'boleta', 'inscripcion', 'invitacion', 'en_linea')
_CAMPOS_ENTRADA = ('is_free', 'requires_registration', 'by_invitation', 'online')


def _entrada_a_campos(v):
    return {'libre': {'is_free': True}, 'boleta': {'is_free': False},
            'inscripcion': {'is_free': True, 'requires_registration': True},
            'invitacion': {'by_invitation': True}, 'en_linea': {'online': True}}[v]


def _entrada_de(f):
    """La entrada que ya trae una función (fuente principal), o None."""
    if f.get('by_invitation'):
        return 'invitacion'
    if f.get('online'):
        return 'en_linea'
    if f.get('requires_registration'):
        return 'inscripcion'
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


_FECHA = re.compile(r'^\d{4}-\d{2}-\d{2}$')


def validar(a):
    """Lanza AfirmacionInvalida si la afirmación no cumple el modelo."""
    q = f"{a.get('ancla')} · {a.get('casilla')}"
    if a.get('casilla') not in RANGO:
        raise AfirmacionInvalida(f'{q}: casilla desconocida')
    an = a.get('ancla') or {}
    if not all(an.get(k) for k in ('sede', 'dia', 'hora')):
        raise AfirmacionInvalida(f'{q}: ancla incompleta (sede, dia, hora)')
    fu = a.get('fuente') or {}
    if fu.get('tipo') not in TIPOS:
        raise AfirmacionInvalida(f'{q}: tipo de fuente desconocido «{fu.get("tipo")}»')
    if not _FECHA.match(str(fu.get('fecha') or '')):
        raise AfirmacionInvalida(f'{q}: fuente sin fecha (AAAA-MM-DD)')
    if fu['tipo'] == 'juan' and not fu.get('frase'):
        raise AfirmacionInvalida(f'{q}: una decisión de Juan lleva su frase')
    if fu['tipo'] != 'juan' and not str(fu.get('url') or '').startswith('http'):
        raise AfirmacionInvalida(f'{q}: fuente sin url')
    if a['casilla'] == 'entrada' and a.get('valor') not in ENTRADAS:
        raise AfirmacionInvalida(f'{q}: entrada «{a.get("valor")}» no es una de {ENTRADAS}')
    if a['casilla'] == 'existe':
        if a.get('valor') is False and not a.get('por_que'):
            raise AfirmacionInvalida(f'{q}: quitar una función lleva su por_que')
        if a.get('valor') is not False and not (isinstance(a.get('valor'), dict)
                                                and not faltan_obligatorias(a['valor'])):
            raise AfirmacionInvalida(f'{q}: agregar una función lleva sus casillas obligatorias {OBLIGATORIAS}')


def faltan_obligatorias(f):
    return [k for k in OBLIGATORIAS if not f.get(k)]


def _nivel(casilla, tipo):
    return next(i for i, n in enumerate(RANGO[casilla]) if tipo in n) \
        if any(tipo in n for n in RANGO[casilla]) else None


def _elegir(casilla, candidatos):
    """candidatos: [(valor, fuente)] → (ganador | None, conflicto | None)."""
    con_nivel = [(v, fu, _nivel(casilla, fu['tipo'])) for v, fu in candidatos]
    con_nivel = [c for c in con_nivel if c[2] is not None]
    if not con_nivel:
        return None, None
    mejor = min(c[2] for c in con_nivel)
    del_nivel = [c for c in con_nivel if c[2] == mejor]
    ultima = max(c[1]['fecha'] for c in del_nivel)
    ultimos = [c for c in del_nivel if c[1]['fecha'] == ultima]
    valores = {repr(c[0]) for c in ultimos}
    if len(valores) > 1:
        return None, {'casilla': casilla, 'opciones': [{'valor': c[0], 'fuente': c[1]} for c in ultimos]}
    return ultimos[0], None


def _mins(h):
    return int(h[:2]) * 60 + int(h[3:5])


def resolver(funciones, afirmaciones, contexto):
    """Las funciones base + las afirmaciones → Resultado. `contexto`:
    fuente_principal {tipo, fecha, url}, sedes_que_cobran (set de sedes),
    ticketing_model ('paid' | 'mixed' | None)."""
    for a in afirmaciones:
        validar(a)
    principal = contexto['fuente_principal']
    por_ancla = {tuple(f['_ancla']): dict(f) for f in funciones}
    orden = [tuple(f['_ancla']) for f in funciones]
    afs = {}
    for a in afirmaciones:
        k = (a['ancla']['sede'], a['ancla']['dia'], a['ancla']['hora'])
        afs.setdefault(k, []).append(a)
    # LAS FUNCIONES NUEVAS: una afirmación `existe` con valor que no es False y
    # ancla que no está en la base
    for k, xs in afs.items():
        if k in por_ancla:
            continue
        nuevas = [a for a in xs if a['casilla'] == 'existe' and a['valor'] is not False]
        if not nuevas:
            raise AnclaPerdida(f'{k}: ninguna función base con esa ancla '
                               f'({", ".join(sorted({a["casilla"] for a in xs}))})')
        g, _ = _elegir('existe', [(a['valor'], a['fuente']) for a in nuevas])
        if g:
            por_ancla[k] = {**g[0], '_ancla': k, '_procedencia': {'existe': dict(g[1])}}
            orden.append(k)
    salida, conflictos = [], []
    for k in orden:
        f = por_ancla[k]
        proc = dict(f.get('_procedencia') or {})
        # LA FECHA DE LA FUENTE PRINCIPAL ES LA DE LA FUNCIÓN: el crudo se regenera
        # cualquier día, pero la web se leyó cuando dice su `_src.date`. Con la
        # fecha del crudo, la web «de hoy» le ganaría la hora a un IG más nuevo
        _d = str((f.get('_src') or {}).get('date') or '') if isinstance(f.get('_src'), dict) else ''
        fp = dict(principal, fecha=_d) if _FECHA.match(_d) else principal
        mias = afs.get(k, [])
        # quitar
        g, c = _elegir('existe', [(a['valor'] is not False, a['fuente']) for a in mias if a['casilla'] == 'existe'])
        if c:
            conflictos.append({'ancla': k, **c})
        if g and g[0] is False:
            continue
        for casilla in RANGO:
            if casilla == 'existe':
                continue
            cand = [(a['valor'], a['fuente']) for a in mias if a['casilla'] == casilla]
            if casilla == 'entrada':
                base_v = _entrada_de(f)
            else:
                base_v = f.get(casilla)
            if base_v not in (None, '') and casilla not in proc:
                cand.append((base_v, fp))
            elif base_v not in (None, '') and casilla in proc:
                cand.append((base_v, proc[casilla]))
            if not cand:
                continue
            g, c = _elegir(casilla, cand)
            if c:
                conflictos.append({'ancla': k, **c})
                g = next(((v, fu) for v, fu in cand if fu is fp or fu is proc.get(casilla)), None)
                if not g:
                    continue
            v, fu = g[0], g[1]
            if casilla == 'entrada':
                for x in _CAMPOS_ENTRADA:
                    f.pop(x, None)
                f.update(_entrada_a_campos(v))
            else:
                f[casilla] = v
            proc[casilla] = {k2: fu[k2] for k2 in ('tipo', 'fecha', 'url', 'frase') if fu.get(k2)}
        # la entrada que nadie dijo: SUPUESTO (libre, salvo sede que cobra o festival pago)
        if 'entrada' not in proc:
            sup = 'boleta' if (k[0] in (contexto.get('sedes_que_cobran') or set())
                               or contexto.get('ticketing_model') == 'paid') else 'libre'
            f.update(_entrada_a_campos(sup))
            proc['entrada'] = {'tipo': 'regla', 'marca': 'supuesto', 'valor': sup}
        f['_procedencia'] = proc
        salida.append(f)
    # la duración que nadie dijo: ESTIMADA (hueco hasta la siguiente en la sede)
    for f in salida:
        if f.get('duration'):
            continue
        sig = sorted(_mins(g['time']) for g in salida
                     if g is not f and g.get('day') == f.get('day') and g.get('venue') == f.get('venue')
                     and g.get('time', '') > f.get('time', ''))
        n = min(sig[0] - _mins(f['time']), 90) if sig else 60
        f['duration'] = f'{n} min'
        f['_procedencia']['duration'] = {'tipo': 'regla', 'marca': 'estimado'}
    return Resultado(salida, conflictos)


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
    """El contexto de resolver(): la fuente principal sale de la procedencia del
    crudo (url y fecha de captura; el tipo lo dice el plan, `festival-web` si
    no), más las sedes que cobran y el modelo de boletería del festival."""
    pv = crudo.get('_provenance') or {}
    fecha = str(pv.get('capturado') or '')[:10]
    if not _FECHA.match(fecha):
        raise AfirmacionInvalida('la fuente principal (crudo._provenance) no tiene fecha de captura')
    tipo = (plan or {}).get('fuente_principal') or 'festival-web'
    if tipo not in TIPOS:
        raise AfirmacionInvalida(f'fuente principal de tipo desconocido «{tipo}»')
    return {'fuente_principal': {'tipo': tipo, 'url': pv.get('url') or '', 'fecha': fecha},
            'sedes_que_cobran': set(SEDES_QUE_COBRAN), 'ticketing_model': ticketing_model}


def de_ancla(afirmaciones, ancla):
    return [a for a in afirmaciones
            if (a['ancla']['sede'], a['ancla']['dia'], a['ancla']['hora']) == tuple(ancla)]


# ── autoprueba: cada regla atrapa su cebo (en memoria, nunca en disco) ───────
def autoprueba():
    ciegos = []
    S, H = 'zzz', ('zzz', '2026-01-01', '10:00')
    b = {'title': 'zzz', 'type': 'film', 'day': H[1], 'time': H[2], 'venue': 'zzz - X', 'sala': 'A',
         'duration': '90 min', '_ancla': H}
    ctx = {'fuente_principal': {'tipo': 'festival-web', 'fecha': '2026-01-01', 'url': 'http://x'}}

    def a(cas, val, tipo='sala', fecha='2026-01-02', url='http://y', **kw):
        return {'ancla': {'sede': S, 'dia': H[1], 'hora': H[2]}, 'casilla': cas, 'valor': val,
                'fuente': {'tipo': tipo, 'fecha': fecha, 'url': url, 'frase': url}, **kw}
    try:
        if resolver([b], [a('sala', 'B')], ctx).funciones[0]['sala'] != 'B':
            ciegos.append('rango (sala gana la sede)')
        if resolver([b], [a('time', '11:00')], ctx).funciones[0]['time'] != '10:00':
            ciegos.append('rango (hora no la cambia la sala)')
        if not resolver([b], [a('sala', 'B'), a('sala', 'C', url='http://z')], ctx).conflictos:
            ciegos.append('conflicto')
        if resolver([b], [], ctx).funciones[0]['_procedencia']['entrada'].get('marca') != 'supuesto':
            ciegos.append('entrada supuesta')
        if resolver([dict(b, duration=None)], [], ctx).funciones[0]['_procedencia']['duration'].get('marca') != 'estimado':
            ciegos.append('duración estimada')
        try:
            resolver([b], [a('sala', 'B', ancla=None)] if False else
                     [{**a('sala', 'B'), 'ancla': {'sede': S, 'dia': H[1], 'hora': '23:00'}}], ctx)
            ciegos.append('ancla perdida')
        except AnclaPerdida:
            pass
        try:
            x = a('sala', 'B')
            x['fuente'] = {'tipo': 'sala', 'fecha': '2026-01-02'}
            resolver([b], [x], ctx)
            ciegos.append('afirmación sin url')
        except AfirmacionInvalida:
            pass
    except Exception as e:  # una autoprueba que revienta es una autoprueba ciega
        ciegos.append(f'revienta: {e}')
    return ciegos
