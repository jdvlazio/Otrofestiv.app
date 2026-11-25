#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sello_funcion.py — cada función publicada la releyó otra persona, y su acceso tiene fuente.

POR QUÉ (Juan, 24 nov 2026): BOGOSHORTS se montó con 34 proyecciones de pago marcadas
gratis («sin aviso de pago = gratis» sin abrir el PDF de acreditaciones) y 3 horas mal.
Las obras tenían sello (sello_obra.py); las funciones no.

TRES CONTROLES (archivos en festivals/staging/, nunca en el JSON publicado):
  1. <id>-sellos-funcion.json  {clave: {huella, monta, verifica (distinto), contra, fecha}}.
     La huella es lo publicado de la función MÁS lo que hereda (acceso y enlace de su
     sede, del festival y de la entrada de acceso que la cubre). Cambia algo → se vuelve a leer.
  2. <id>-acceso.json  [{alcance: función|sede|festival, nombre, nivel, acceso, cita, url,
     documentos_revisados}]. `nombre`: la clave de la función, la sede exacta o el id del
     festival. `acceso`: gratis, pago, inscripción, invitación (uno o lista). «declarado»
     exige cita y url; «sin-aviso» solo puede ser gratis y exige documentos_revisados e
     inventario cerrado. Toda función futura cubierta, y lo publicado no contradice la
     entrada más específica.
  3. <id>-fuentes.json existe y no tiene nada sin revisar (fuentes_descubrir.py).

CUÁNDO FRENA: en la PRIMERA publicación (el festival no está en el índice del almacén),
por cualquiera. Ya publicado: solo avisa, y se sella después. Si el índice no se puede
leer, frena. validate.py ([sello-funcion]) no usa red: frena solo lo inválido o
contradictorio. Lo que esto NO prueba: quién leyó de verdad.

ORDEN: acceso.json → ensamblar/publicar → --lote → otro agente lee → --sellar → ensayo.

    python3 pipeline/sello_funcion.py informe <id>
    python3 pipeline/sello_funcion.py --lote <id> <archivo>     # lo no sellado, para el lector
    python3 pipeline/sello_funcion.py --sellar <lote.json>      # sella lo que tenga veredicto «fiel»
"""
import datetime
import hashlib
import json
import os
import sys
import time
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
STAGING = os.path.join(REPO, 'festivals', 'staging')
INDICE = 'https://eytxrvbnwzxuedbmnnqr.supabase.co/storage/v1/object/public/datos/indice.json'

ACCESO = ('is_free', 'requires_registration', 'registration_url', 'ticket_url', 'by_invitation',
          'online', 'stream_url', 'stream_platform', 'audience')
CAMPOS = ('title', 'day', 'date', 'time', 'hasta', 'film_start', 'venue', 'sala', 'info', 'unscheduled',
          'has_qa', 'qa_type') + ACCESO
DEL_FESTIVAL = ('ticket_url', 'ticketing_model', 'acceso_por_defecto')
FORMAS = ('gratis', 'pago', 'inscripción', 'invitación')


def _ruta(fid, que):
    return os.path.join(STAGING, f'{fid}-{que}.json')


def _leer(p, vacio):
    if not os.path.exists(p):
        return vacio
    with open(p, encoding='utf-8') as fh:
        return json.load(fh)


def _hoy():
    return (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=5)).date().isoformat()


def _t(x):
    return x.strip() if isinstance(x, str) else ''


def con_modelo(fid, d):
    """El festival con su `ticketing_model`: si no va en el JSON, el de FESTIVAL_CONFIG."""
    if d.get('ticketing_model'):
        return d
    import funcion
    return dict(d, ticketing_model=funcion.ticketing_model_de(fid))


def funciones(d):
    """{clave estable: función}; las de `screenings`, con lo que heredan de su obra."""
    out = {}
    for f in d.get('films') or []:
        for x in f.get('screenings') or f.get('sessions') or [None]:
            g = f if x is None else {**{k: v for k, v in f.items() if k != 'id'}, **x}
            k = base = g.get('id') or '|'.join(str(g.get(c) or '') for c in ('title', 'day', 'date', 'time', 'venue', 'sala'))
            n = 2
            while k in out:
                k, n = f'{base}#{n}', n + 1
            out[k] = g
    return out


def futura(f, hoy):
    dia = str(f.get('hasta') or f.get('day') or f.get('date') or '')
    return not (len(dia) == 10 and dia[4] == '-') or dia >= hoy     # sin fecha legible: cuenta


# ── 2. acceso ───────────────────────────────────────────────────────────────
def formas(e):
    a = e.get('acceso')
    return {a} if isinstance(a, str) else set(a) if isinstance(a, list) and all(isinstance(x, str) for x in a) else set()


def invalidas(acceso):
    """Entradas de acceso mal formadas, como texto."""
    if not isinstance(acceso, list):
        return ['el archivo de acceso no es una lista']
    mal, vistos = [], set()
    for e in acceso:
        if not isinstance(e, dict):
            mal.append(f'entrada ilegible: {e!r}'[:80])
            continue
        n = f'{e.get("alcance")} «{e.get("nombre")}»'
        a = formas(e)
        if e.get('alcance') not in ('función', 'sede', 'festival') or not _t(e.get('nombre')):
            mal.append(f'{n}: alcance o nombre inválido')
        if not a or a - set(FORMAS) or {'gratis', 'pago'} <= a:
            mal.append(f'{n}: acceso inválido ({e.get("acceso")})')
        if e.get('nivel') == 'declarado':
            if not _t(e.get('cita')) or not _t(e.get('url')).startswith('https://'):
                mal.append(f'{n}: «declarado» sin cita o sin url')
        elif e.get('nivel') == 'sin-aviso':
            docs = e.get('documentos_revisados')
            if not isinstance(docs, list) or not docs or not all(_t(x) for x in docs):
                mal.append(f'{n}: «sin-aviso» sin documentos revisados')
            if a != {'gratis'}:
                mal.append(f'{n}: «sin-aviso» solo puede ser gratis')
        else:
            mal.append(f'{n}: nivel inválido ({e.get("nivel")})')
        if (e.get('alcance'), e.get('nombre')) in vistos:
            mal.append(f'{n}: repetida')
        vistos.add((e.get('alcance'), e.get('nombre')))
    return mal


def entrada_de(clave, f, acceso):
    """La entrada más específica que cubre la función: función › sede › festival."""
    for alcance, nombre in (('función', clave), ('sede', f.get('venue')), ('festival', None)):
        for e in acceso:
            if e.get('alcance') == alcance and (nombre is None or e.get('nombre') == nombre):
                return e
    return None


def heredado(clave, f, d, acceso):
    sede = (d.get('venues') or {}).get(f.get('venue')) or {}
    e = entrada_de(clave, f, acceso) or {}
    return {'sede': {k: sede[k] for k in ACCESO if k in sede},
            'festival': {k: d[k] for k in DEL_FESTIVAL if d.get(k) is not None},
            'entrada': {k: e[k] for k in ('nivel', 'acceso', 'cita', 'url', 'documentos_revisados') if k in e}}


def publicado(f, d):
    """Cómo se entra según lo publicado (la regla de la app: funcionPaga, urlCompra)."""
    f = {**((d.get('venues') or {}).get(f.get('venue')) or {}), **{k: v for k, v in f.items() if v is not None}}
    out = set()
    if f.get('by_invitation'):
        out.add('invitación')
    elif f.get('is_free') is True:
        out.add('gratis')
    elif f.get('is_free') is False or f.get('ticket_url') or d.get('ticket_url') or d.get('ticketing_model'):
        out.add('pago')
    else:
        out.add('gratis')
    if f.get('requires_registration') or f.get('registration_url'):
        out.add('inscripción')
    return out


def contradicciones(d, acceso, hoy=None):
    out = []
    for k, f in funciones(d).items():
        e = entrada_de(k, f, acceso) if futura(f, hoy or _hoy()) else None
        if not e:
            continue
        dice, pub = formas(e), publicado(f, d)
        if any((x in dice) != (x in pub) for x in ('pago', 'invitación')) or ('inscripción' in dice and 'inscripción' not in pub):
            out.append(f'«{f.get("title")}» {k}: publica {"+".join(sorted(pub))} y su {e["alcance"]} dice {"+".join(sorted(dice))}')
    return out


def sin_cubrir(d, acceso, hoy=None):
    fs = funciones(d)
    out = [f'«{f.get("title")}» {k}: sin acceso con fuente' for k, f in fs.items() if futura(f, hoy or _hoy()) and not entrada_de(k, f, acceso)]
    # un nombre mal escrito no cubre nada y la función cae a la regla general
    hay = {'función': set(fs), 'sede': {f.get('venue') for f in fs.values()}}
    return out + [f'{e["alcance"]} «{e["nombre"]}»: no existe en el programa' for e in acceso
                  if e.get('alcance') in hay and e.get('nombre') not in hay[e['alcance']]]


# ── 3. inventario ───────────────────────────────────────────────────────────
def inventario(fid):
    p = _ruta(fid, 'fuentes')
    if not os.path.exists(p):
        return ['sin inventario de fuentes (fuentes_descubrir.py)']
    import fuentes_descubrir
    d = _leer(p, {})
    if not (d.get('_provenance') or {}).get('capturado'):
        return ['inventario sin recorrer']
    raros = [u for u, i in (d.get('items') or {}).items() if i.get('estado') not in ('usada', 'descartada', 'sin-revisar')]
    return fuentes_descubrir.problemas(d) + [f'estado desconocido: {u}' for u in raros]


# ── 1. sellos ───────────────────────────────────────────────────────────────
def huella(clave, f, d, acceso):
    x = [{k: f.get(k) for k in CAMPOS}, heredado(clave, f, d, acceso)]
    return hashlib.sha1(json.dumps(x, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:12]


def problema(s):
    """Qué le falta a un sello para valer, o None."""
    if not isinstance(s, dict):
        return 'sello ilegible'
    q = lambda k: _t(s.get(k)).casefold()
    if not q('monta') or not q('verifica') or q('monta') == q('verifica'):
        return 'sello sin segundo lector'
    if '/' not in q('contra'):
        return 'sello sin fuente (URL o ruta)'
    return None if q('huella') and q('fecha') else 'sello sin huella o sin fecha'


def faltan(d, sellos, acceso):
    """→ [(clave, función, qué)]: sin sello válido."""
    out = []
    for k, f in funciones(d).items():
        q = 'sin sello' if k not in sellos else problema(sellos[k]) or (
            None if sellos[k]['huella'] == huella(k, f, d, acceso) else 'cambió después del sello')
        if q:
            out.append((k, f, q))
    return out


def sidecars(fid):
    return _leer(_ruta(fid, 'sellos-funcion'), {}), _leer(_ruta(fid, 'acceso'), [])


def revisar(fid, d, hoy=None, modelo=True):
    """→ (inválido o contradictorio, pendiente). Sin red."""
    sellos, acceso = sidecars(fid)
    mal = invalidas(acceso)
    if mal or not isinstance(sellos, dict):
        return mal or ['el archivo de sellos no es un diccionario'], []
    mal = [f'sello {k}: {problema(s)}' for k, s in sellos.items() if problema(s)]
    if d is None:
        return mal, []
    d = con_modelo(fid, d) if modelo else d
    inv = inventario(fid)
    pend = [f'«{f.get("title")}» {k}: {q}' for k, f, q in faltan(d, sellos, acceso)] + sin_cubrir(d, acceso, hoy) + inv
    if inv and any(e['nivel'] == 'sin-aviso' for e in acceso):
        pend.append('acceso «sin-aviso» con el inventario abierto')
    return mal + contradicciones(d, acceso, hoy), pend


def en_almacen(fid, abrir=urllib.request.urlopen):
    """¿Ya está publicado? Lo dice el índice del almacén; si no se puede leer, revienta."""
    with abrir(f'{INDICE}?m={int(time.time())}', timeout=30) as r:
        fs = json.loads(r.read())['festivales']
    if not isinstance(fs, dict) or not fs:
        raise ValueError('índice vacío')
    return bool((fs.get(fid) or {}).get('archivo'))


def control(fid, d, abrir=urllib.request.urlopen, hoy=None, modelo=True):
    """Para publicar-datos.py → (frenos, avisos)."""
    try:
        ya = en_almacen(fid, abrir)
    except Exception as e:
        return [f'no se pudo leer el índice del almacén ({type(e).__name__}): no se sabe si {fid} ya está publicado'], []
    mal, pend = revisar(fid, d, hoy, modelo)
    return ([], mal + pend) if ya else (mal + pend, [])


def lote(fid, d):
    sellos, acceso = sidecars(fid)
    af = _leer(_ruta(fid, 'afirmaciones'), {}).get('afirmaciones', [])
    return {'festival': fid, 'funciones': [
        {'clave': k, 'huella': huella(k, f, d, acceso), 'que': q,
         'publicado': {c: f[c] for c in CAMPOS if c in f}, 'heredado': heredado(k, f, d, acceso),
         'fuentes': {'_src': f.get('_src'), 'afirmaciones': [a for a in af if a.get('funcion') == k]},
         'monta': '', 'verifica': '', 'contra': '', 'veredicto': ''} for k, f, q in faltan(d, sellos, acceso)]}


def sellar(lt, d, fecha=None):
    """Sella lo «fiel»; un solo error y no escribe nada. → (selladas, las que no son fieles)."""
    fid = lt['festival']
    sellos, acceso = sidecars(fid)
    fs, n, no = funciones(d), 0, []
    for e in lt['funciones']:
        k = e['clave']
        if _t(e.get('veredicto')).casefold() != 'fiel':
            no.append(k)
            continue
        s = {**{c: e.get(c) for c in ('huella', 'monta', 'verifica', 'contra')}, 'fecha': fecha or _hoy()}
        if problema(s):
            raise SystemExit(f'✗ {k}: {problema(s)}')
        if k not in fs or e['huella'] != huella(k, fs[k], d, acceso):
            raise SystemExit(f'✗ {k}: la función ya no es la que se leyó; saca otro lote')
        sellos[k] = s
        n += 1
    with open(_ruta(fid, 'sellos-funcion'), 'w', encoding='utf-8') as fh:
        json.dump(sellos, fh, ensure_ascii=False, indent=1, sort_keys=True)
    return n, no


def autoprueba():
    """[] = la regla ve."""
    f = {'id': 'f_1', 'title': 'X', 'day': '2099-01-01', 'time': '19:00', 'venue': 'S', 'is_free': True}
    d = {'films': [f]}
    pago = [{'alcance': 'sede', 'nombre': 'S', 'nivel': 'declarado', 'acceso': 'pago', 'cita': 'c', 'url': 'https://x'}]
    s = {'f_1': {'huella': huella('f_1', f, d, []), 'monta': 'a', 'verifica': 'b', 'contra': 'https://x', 'fecha': '2026-11-24'}}
    mal = []
    if faltan(d, s, []) or not faltan({'films': [dict(f, time='20:00')]}, s, []):
        mal.append('sello')
    if not faltan(d, {'f_1': dict(s['f_1'], verifica='A ')}, []):
        mal.append('mismo lector')
    if not contradicciones(d, pago) or contradicciones({'films': [dict(f, is_free=False)]}, pago) or invalidas(pago):
        mal.append('pago declarado')
    if not invalidas([dict(pago[0], nivel='sin-aviso', acceso='gratis', documentos_revisados=[])]):
        mal.append('sin-aviso sin documentos')
    return mal


def _festival(fid):
    with open(os.path.join(REPO, 'festivals', f'{fid}.json'), encoding='utf-8') as fh:
        return con_modelo(fid, json.load(fh))


def main(a):
    if a[:1] == ['informe'] and len(a) == 2:
        d = _festival(a[1])
        mal, pend = revisar(a[1], d)
        print(f'{a[1]}: {len(funciones(d))} funciones · {len(faltan(d, *sidecars(a[1])))} sin sello válido · '
              f'{len(sin_cubrir(d, sidecars(a[1])[1]))} sin acceso con fuente · {len(inventario(a[1]))} del inventario · {len(mal)} inválido(s)')
        for x in mal + pend:
            print('  ·', x)
    elif a[:1] == ['--lote'] and len(a) == 3:
        lt = lote(a[1], _festival(a[1]))
        with open(a[2], 'w', encoding='utf-8') as fh:
            json.dump(lt, fh, ensure_ascii=False, indent=1)
        print(len(lt['funciones']), 'funciones por leer →', a[2])
    elif a[:1] == ['--sellar'] and len(a) == 2:
        lt = _leer(a[1], None) or sys.exit(f'✗ no existe {a[1]}')
        n, no = sellar(lt, _festival(lt['festival']))
        print(n, 'selladas ·', len(no), 'sin veredicto «fiel»', *no[:10])
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main(sys.argv[1:])
