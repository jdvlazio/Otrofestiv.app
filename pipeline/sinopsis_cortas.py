#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sinopsis_cortas.py — la sinopsis que se lee en el celular: 350 caracteres.

Decisión de Juan (23 nov 2026): «las versiones cortas dentro de la app se ven
muchísimo mejor… es una app pequeña de bolsillo». La síntesis NO recorta: se
reescribe. El original queda entero en el almacén y nunca se edita.

Dónde vive: en la decisión `sinopsis.es` de la obra (catalogo/decisiones/),
que ya gana en todos los festivales (sinopsis_unicas.aplicar):
    valor        la síntesis
    original     el texto completo, con `original_de` (festivales que lo traen)
    sintesis     {redacta, verifica, veredicto, fecha, huella}

Quién hace qué (pipeline/SINOPSIS-CORTA.md): una persona o agente REDACTA,
OTRO distinto VERIFICA contra el original. Piloto: de 9 síntesis bien escritas,
el segundo lector encontró 2 fieles, 6 por ajustar y 1 que cambiaba quién hacía
qué. El código solo mide lo medible (`revisar`): largo, cierre, nombres y cifras
que el original no dice. `huella` ata el veredicto a ESE par de textos: si se
toca cualquiera de los dos, hay que volver a verificar.

TRINQUETE: las largas publicadas están en pipeline/sinopsis-largas.json, por
festival. El número solo baja; un festival nuevo parte de cero. Se mira en el
push (validate.py), después de sumar las obras al catálogo: antes no tienen id.

    python3 pipeline/sinopsis_cortas.py --pendientes <festival>   # JSON para redactar
    python3 pipeline/sinopsis_cortas.py --revisar <archivo>       # chequeos del código
    python3 pipeline/sinopsis_cortas.py --registrar <archivo>     # al almacén (exige veredicto «fiel»)
    python3 pipeline/sinopsis_cortas.py --congelar                # la deuda (solo si BAJÓ)
Después: catalogo_construir.py --escribir y sinopsis_unicas.py --aplicar <festival> --escribir
"""
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sinopsis
import sinopsis_unicas as su

MAX = 350
DEUDA = os.path.join(su.REPO, 'pipeline', 'sinopsis-largas.json')
_CIERRE = re.compile(r'[.!?…][»”"\')]*$|[»”"]\.?$')
_NUM = {'dos': 2, 'tres': 3, 'cuatro': 4, 'cinco': 5, 'seis': 6, 'siete': 7, 'ocho': 8, 'nueve': 9, 'diez': 10,
        'once': 11, 'doce': 12, 'trece': 13, 'catorce': 14, 'quince': 15, 'veinte': 20, 'treinta': 30,
        'cuarenta': 40, 'cincuenta': 50, 'sesenta': 60, 'setenta': 70, 'ochenta': 80, 'noventa': 90, 'cien': 100}


def cierra(s):
    return bool(_CIERRE.search((s or '').strip()))


def huella(original, corta):
    return hashlib.sha1(f'{original}\0{corta}'.encode()).hexdigest()[:12]


def _cifras(s):
    p = su.plana(s).split()
    return {int(x) for x in p if x.isdigit()} | {_NUM[x] for x in p if x in _NUM}


def revisar(original, corta, titulo=''):
    """Lo que el código puede medir. [] = nada que objetar (NO prueba fidelidad)."""
    out = []
    o, c = (original or '').strip(), (corta or '').strip()
    if len(c) > MAX:
        out.append(f'{len(c)} caracteres (máximo {MAX})')
    if len(c) >= len(o):
        out.append('no es más corta que el original')
    if not cierra(c):
        out.append('no cierra la frase')
    if not cierra(o):
        out.append('el ORIGINAL está cortado: recuperarlo antes')
    out += su.defectos(c)
    base = set(su.plana(o + ' ' + titulo).split())
    # un nombre propio es una mayúscula que no abre frase; y toda palabra del nombre debe estar en el original
    for m in re.finditer(r'(?<![.!?…:»”"«“¿¡] )(?<![«“"¿¡])(?<!^)\b[A-ZÁÉÍÓÚÑ][\wáéíóúñ’\'-]*', c):
        if any(w not in base for w in su.plana(m.group()).split()):
            out.append(f'nombre que el original no trae: {m.group()}')
    for n in sorted(_cifras(c) - _cifras(o + ' ' + titulo)):
        out.append(f'cifra que el original no trae: {n}')
    if re.search(r'\s{2,}', c):
        out.append('doble espacio')
    return out


def invalidas(decs):
    """Síntesis del almacén sin verificar, vencidas o fuera de regla → [mensaje]."""
    out = []
    for d in decs:
        if d.get('campo') != 'sinopsis.es' or 'original' not in d:
            continue
        s, t = d.get('sintesis') or {}, d.get('titulo') or d['work_id']
        mal = revisar(d['original'], d['valor'], d.get('titulo') or '')
        perm = s.get('permitido') or {}
        mal = [m for m in mal if not str(perm.get(m) or '').strip()]
        if s.get('veredicto') != 'fiel':
            mal.append('sin veredicto «fiel»')
        if not s.get('redacta') or not s.get('verifica') or s['redacta'] == s['verifica']:
            mal.append('quien verifica no puede ser quien redacta')
        if s.get('huella') != huella(d['original'], d['valor']):
            mal.append('el texto cambió después de verificarlo')
        if mal:
            out.append(f'«{t}»: ' + ', '.join(mal))
    return out


def largas(films):
    return [o for o, _ in sinopsis.obras(films) if len(sinopsis._es(o)) > MAX]


def deuda():
    if not os.path.exists(DEUDA):
        return {}
    return {k: v for k, v in json.load(open(DEUDA, encoding='utf-8')).items() if not k.startswith('_')}


def excedidos():
    """Festivales con más largas que su deuda → [(festival, n, techo, [títulos])]."""
    t = deuda()
    return [(f, len(x), t.get(f, 0), [o['title'] for o in x]) for f, films in sinopsis._publicados()
            for x in [largas(films)] if len(x) > t.get(f, 0)]


def pendientes(fid):
    films = dict(sinopsis._publicados())[fid]
    return [{'work_id': o.get('work_id'), 'titulo': o['title'], 'original': sinopsis._es(o), 'corta': '',
             'original_cortado': not cierra(sinopsis._es(o))} for o in largas(films)]


def registrar(xs, fecha):
    """xs: [{work_id, titulo, original, corta, redacta, verifica, veredicto}] → n. Todo o nada."""
    cat = su._almacen()
    decs = cat.decisiones()
    por = {d['work_id']: d for d in decs if d['campo'] == 'sinopsis.es'}
    vistos = {}
    for f, films in sinopsis._publicados():
        for o, _ in sinopsis.obras(films):
            if o.get('work_id') and sinopsis._es(o):
                vistos.setdefault(o['work_id'], {}).setdefault(sinopsis._es(o), []).append(f)
    for x in xs:
        if not x.get('work_id'):
            raise SystemExit(f'✗ «{x["titulo"]}» no tiene obra en el catálogo')
        d = por.get(x['work_id'])
        if d is None:
            d = {'work_id': x['work_id'], 'campo': 'sinopsis.es', 'motivo': 'síntesis de la sinopsis (sinopsis_cortas.py)',
                 'fecha': fecha, 'quien': 'Juan'}
            decs.append(d)
        # el original es el que está en uso; resintetizar no lo pisa
        actual = d.get('original') or d.get('valor') or x['original']
        if actual != x['original']:
            raise SystemExit(f'✗ «{x["titulo"]}»: el original del archivo no es el del almacén')
        d['vistas'] = sorted(set(d.get('vistas') or []) | {su.huella(s) for s in vistos.get(x['work_id'], {})} | {su.huella(x['original'])})
        d.setdefault('original_de', sorted(vistos.get(x['work_id'], {}).get(x['original'], [])))
        d.update(titulo=x['titulo'], valor=x['corta'].strip(), original=x['original'],
                 sintesis={'redacta': x.get('redacta'), 'verifica': x.get('verifica'), 'veredicto': x.get('veredicto'),
                           'fecha': fecha, 'huella': huella(x['original'], x['corta'].strip()),
                           **({'permitido': x['permitido']} if x.get('permitido') else {})})
    ids = {x['work_id'] for x in xs}
    mal = invalidas([d for d in decs if d['work_id'] in ids])
    if mal:
        raise SystemExit('✗ no se registra nada:\n  ' + '\n  '.join(mal))
    cat.escribir_decisiones(decs)
    return len(xs)


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[:1] == ['--congelar']:
        n = {f: len(largas(x)) for f, x in sinopsis._publicados() if largas(x)}
        sube = {k: v for k, v in n.items() if os.path.exists(DEUDA) and v > deuda().get(k, 0)}
        if sube:
            sys.exit(f'✗ la deuda solo baja; subió en: {sube}')
        json.dump({'_nota': f'Sinopsis publicadas de más de {MAX} caracteres, por festival. Solo baja (pipeline/sinopsis_cortas.py).', **n},
                  open(DEUDA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, sort_keys=True)
        print(sum(n.values()), 'largas en', len(n), 'festivales')
    elif len(a) == 2 and a[0] == '--pendientes':
        print(json.dumps(pendientes(a[1]), ensure_ascii=False, indent=1))
    elif len(a) == 2 and a[0] == '--revisar':
        mal = 0
        for x in json.load(open(a[1], encoding='utf-8')):
            m = revisar(x['original'], x['corta'], x['titulo'])
            mal += bool(m)
            print('✗' if m else '✓', f'{len(x["original"])}→{len(x["corta"])}', x['titulo'], '· '.join(m))
        sys.exit(1 if mal else 0)
    elif len(a) == 2 and a[0] == '--registrar':
        import datetime
        print(registrar(json.load(open(a[1], encoding='utf-8')), datetime.date.today().isoformat()), 'síntesis registradas')
    else:
        sys.exit(__doc__)
