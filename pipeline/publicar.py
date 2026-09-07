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
        ca, cb = _cobertura(viejo.get('films') or []), _cobertura(out['films'])
        perdidos = {k: (ca[k], cb[k]) for k in ca if cb[k] < ca[k]}
        menos_films = len(viejo.get('films') or []) - len(out['films'])
        menos_sedes = len(viejo.get('venues') or {}) - len(out['venues'])
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
