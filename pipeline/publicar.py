# -*- coding: utf-8 -*-
"""Publicador ÚNICO: build → `festivals/<id>.json`, validando al escribir.

DOS TRABAJOS, Y EL SEGUNDO ES EL QUE DUELE.

1 · APLICA EL CONTRATO. Filtra las claves privadas (conservando `_src`,
    `_pendiente`, `_inherited` y `_nota`, que la app y los guardianes SÍ leen),
    coacciona los tipos de `pipeline/contrato.json` y aborta si algo no cumple.
    Validar al escribir es más barato que validar después: el dato malo no
    llega a existir.

2 · SE NIEGA A BORRAR LO QUE YA ESTÁ EN PRODUCCIÓN. El 17 ago 2026 republiqué
    FICDEH desde su build y el validador se puso rojo: el build estaba
    ATRASADO —le faltaban las 415 banderas y 13 salas que se habían arreglado
    sobre el JSON publicado y nunca volvieron aguas arriba—. Correr su
    publicador habría borrado dos correcciones que estaban EN VIVO, en silencio.
    Ese silencio es el bug: publicar no puede ser una operación que pierda datos
    sin decirlo.

    Por eso compara con lo publicado y ABORTA si el build tiene menos. Con
    `--forzar` se publica igual, pero hay que escribirlo a mano y queda dicho.

3 · SOLO PUBLICA LO QUE CORRIÓ EL RUNNER. El build tiene que llevar el sello
    de pipeline/correr.py con el SHA del plan que hay ahora. Sin sello —una
    cadena hecha a mano— o con el sello de un plan que luego cambió, no se
    publica. Montando QAFF Bogotá (2 sep 2026) se hicieron a mano cuatro pasos
    que tenían comando y cada uno produjo el defecto que el comando evita; con
    esto, ese camino no llega a festivals/. --forzar sigue siendo el escape.

    python3 pipeline/publicar.py <id>
    python3 pipeline/publicar.py <id> --forzar   # sí, quiero perder esos datos / publicar sin sello
"""
import json, os, sys, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# `_acceso` lo LEE [boleteria-muda]: es la declaración de que fuimos a mirar
# cómo se entra y el festival no lo publica. Si el publicador lo borra, el
# guardián no lo ve y el festival vuelve a estar mudo.
CONSERVAR = {'_src', '_pendiente', '_inherited', '_nota', '_acceso'}


def _slot(f):
    """Lo que una persona necesita para NO equivocarse de puerta ni de hora."""
    return (f.get('day', ''), f.get('time', ''),
            (f.get('venue') or '').split(' - ')[0], f.get('sala', ''),
            'libre' if f.get('is_free') else 'pago')


def diff_contra_produccion(viejo, nuevo):
    """Qué cambia de lo que ya está en la calle, obra por obra.

    POR QUÉ SE IMPRIME SIEMPRE. La compuerta de pérdida de abajo cuenta CAMPOS:
    ve que no desaparezcan datos, pero no ve que una función se mueva de hora o
    de sede, que es el error que manda a alguien a la puerta equivocada. El 18
    sep 2026 tres funciones de FICMA cambiaron de hora entre dos publicaciones y
    lo único que lo mostró fue un diff que hice a mano, una vez, por casualidad.
    Lo que se revisa por casualidad no se revisa.

    No es una compuerta: es un informe. Frenar una publicación porque una hora
    cambió sería frenar justo lo que hay que publicar durante un festival. Pero
    queda escrito en el log y en la cara de quien publica."""
    def indice(films):
        ix = {}
        for f in films or []:
            ix.setdefault(norm_t(f.get('title', '')), []).append(f)
        return ix

    def norm_t(t):
        import unicodedata
        t = ''.join(c for c in unicodedata.normalize('NFD', (t or '').lower())
                    if unicodedata.category(c) != 'Mn')
        return ' '.join(t.split())

    va, vb = indice(viejo.get('films')), indice(nuevo.get('films'))
    altas = sorted(set(vb) - set(va))
    bajas = sorted(set(va) - set(vb))
    movidas = []
    for t in sorted(set(va) & set(vb)):
        sa = sorted(_slot(f) for f in va[t])
        sb = sorted(_slot(f) for f in vb[t])
        if sa != sb:
            movidas.append((vb[t][0].get('title', t), sa, sb))
    return altas, bajas, movidas


def limpio(d):
    return {k: v for k, v in d.items() if not k.startswith('_') or k in CONSERVAR}


def _cobertura(films):
    """Cuántas funciones traen cada campo. La unidad de la comparación: si un
    campo baja, alguien perdió datos entre una publicación y la siguiente."""
    c = collections.Counter()
    for f in films:
        for k, v in f.items():
            if v not in (None, '', [], {}):
                c[k] += 1
    return c


def publicar(fid, forzar=False):
    build = f'{REPO}/festivals/staging/{fid}-build.json'
    out_p = f'{REPO}/festivals/{fid}.json'
    if not os.path.exists(build):
        sys.exit(f'✗ falta {build} — correr antes pipeline/ensamblar.py {fid}')
    b = json.load(open(build, encoding='utf-8'))

    # ── ¿este build lo produjo el runner, con este plan? ────────────────────
    ok_sello, motivo = lib.sello_valido(fid, b)
    if not ok_sello and not forzar:
        sys.exit(f'✗ NO se publica {fid}: {motivo}.\n'
                 f'  El camino es: python3 pipeline/correr.py {fid}\n'
                 f'  (o --forzar, a mano, si de verdad querés publicar un build sin correr)')
    if not ok_sello:
        print(f'⚠ --forzar: se publica SIN sello del runner — {motivo}')
    else:
        print(f'  sello: {motivo}')

    rep = collections.Counter()
    out = {k: v for k, v in b.items() if k not in ('films', 'venues', 'sections')}
    out = limpio(out)
    out['_provenance'] = b.get('_provenance', {})
    out['sections'] = {k: limpio(v) for k, v in (b.get('sections') or {}).items()}
    out['venues'] = {k: limpio(v) for k, v in (b.get('venues') or {}).items()}
    out['films'] = [lib.normaliza(limpio(f), rep) for f in b['films']]
    for f in out['films']:
        for it in (f.get('film_list') or []):
            if isinstance(it, dict):
                lib.normaliza(it, rep)

    # ── el contrato, ANTES de escribir ──────────────────────────────────────
    fallos = []
    C = lib.contrato()['campos']
    for f in out['films']:
        for k, spec in C.items():
            v = f.get(k)
            if spec.get('obligatorio') and not f.get('unscheduled') and v in (None, ''):
                fallos.append(f"«{f.get('title','?')}»: falta {k}")
            if v in (None, '', [], {}):
                continue
            if spec.get('formato'):
                import re as _re
                if not _re.search(spec['formato'], str(v)):
                    fallos.append(f"«{f.get('title','?')}»: {k}={v!r} no cumple {spec['formato']}")
            if spec.get('enum') and v not in spec['enum']:
                fallos.append(f"«{f.get('title','?')}»: {k}={v!r} fuera de {spec['enum']}")
    if fallos:
        print(f'✗ {len(fallos)} incumplimiento(s) del contrato — NO se publica:')
        for x in fallos[:8]:
            print('   ', x)
        sys.exit(1)

    # ── ¿esta publicación PIERDE datos? ─────────────────────────────────────
    if os.path.exists(out_p):
        viejo = json.load(open(out_p, encoding='utf-8'))
        _alt, _baj, _mov = diff_contra_produccion(viejo, out)
        if _alt or _baj or _mov:
            print(f'· cambios contra lo publicado: +{len(_alt)} obra(s), '
                  f'-{len(_baj)}, {len(_mov)} movida(s)')
            for _t, _sa, _sb in _mov[:10]:
                for _a, _b in zip(_sa + [None] * len(_sb), _sb + [None] * len(_sa)):
                    if _a != _b:
                        _f = lambda x: ('—' if x is None else
                                        f'{x[0][-2:]}·{x[1]}·{x[2][:22]}'
                                        + (f'·{x[3]}' if x[3] else '') +
                                        ('' if x[4] == 'libre' else '·PAGO'))
                        print(f'    ~ {_t[:40]:42} {_f(_a)}  →  {_f(_b)}')
            for _t in _baj[:6]:
                print(f'    - {_t[:60]}')
            for _t in _alt[:6]:
                print(f'    + {_t[:60]}')
            if len(_alt) > 6 or len(_baj) > 6 or len(_mov) > 10:
                print('    … (recortado)')
        # La cobertura se compara sobre las funciones que NO se movieron: una
        # función trasladada (título en `_mov`) cambia de sede y con ella pierde
        # o gana los campos que son de la sede (sala, dirección). Eso no es
        # perder datos: es la corrección misma. Lo que sí es pérdida es que una
        # función quieta amanezca sin un campo que ayer tenía.
        _movidos = {t for t, _a, _b in _mov}
        _quietas = lambda fs: [f for f in fs if f.get('title') not in _movidos]
        ca, cb = _cobertura(_quietas(viejo.get('films') or [])), _cobertura(_quietas(out['films']))
        perdidos = {k: (ca[k], cb[k]) for k in ca if cb[k] < ca[k]}
        menos_films = len(viejo.get('films') or []) - len(out['films'])
        # UNA SEDE QUE SE VACIÓ NO ES UNA SEDE PERDIDA (19 sep 2026). «Poniéndole
        # voz…» se movió de la Secretaría de la Mujer a Palogrande porque el
        # festival lo corrigió en IG y en el formulario; la Secretaría quedó sin
        # funciones y salió del build, y esta compuerta lo leyó como pérdida.
        # Contar sedes no distingue «se cayó una sede» de «se trasladó su única
        # función». La regla: una sede que desaparece es TRASLADO si todas las
        # obras que tenía siguen publicadas (en otra sede); es pérdida si con
        # ella se fue alguna obra.
        _titulos_nuevos = {f.get('title') for f in out['films']}
        _sedes_idas = set(viejo.get('venues') or {}) - set(out['venues'])
        _trasladadas = {v for v in _sedes_idas if all(
            f.get('title') in _titulos_nuevos
            for f in (viejo.get('films') or []) if f.get('venue') == v)}
        for v in sorted(_trasladadas):
            print(f'    · sede vaciada, no perdida: {v[:50]} (sus obras siguen, en otra sede)')
        menos_sedes = len(_sedes_idas - _trasladadas) - max(0, len(out['venues']) - len(viejo.get('venues') or {}))
        if (perdidos or menos_films > 0 or menos_sedes > 0) and not forzar:
            print(f'✗ publicar {fid} PERDERÍA datos que ya están en producción:')
            if menos_films > 0:
                print(f'    funciones: {len(viejo["films"])} → {len(out["films"])}')
            if menos_sedes > 0:
                print(f'    sedes: {len(viejo["venues"])} → {len(out["venues"])}')
            for k, (a, bb) in sorted(perdidos.items(), key=lambda x: x[1][0] - x[1][1], reverse=True)[:8]:
                print(f'    {k}: {a} → {bb}')
            print('  El build está ATRASADO respecto a producción: alguien arregló el JSON\n'
                  '  publicado y no volvió aguas arriba. Arreglá el build, o --forzar si de\n'
                  '  verdad querés perder eso.')
            sys.exit(1)
        if perdidos and forzar:
            print('⚠ --forzar: se publican MENOS datos de los que había:', dict(perdidos))

    json.dump(out, open(out_p, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    kb = os.path.getsize(out_p) // 1024
    print(f'✓ {out_p}  {kb} KB · {len(out["films"])} funciones · {len(out["venues"])} sedes')
    if rep:
        print('  contrato aplicado:', dict(rep))
    sin_src = sum(1 for f in out['films'] if not f.get('_src'))
    print(f'  films sin _src: {sin_src}')
    return out


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    publicar(sys.argv[1], forzar='--forzar' in sys.argv)
