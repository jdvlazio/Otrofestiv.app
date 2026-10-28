#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""corto.py <fest-id> — EL camino corto: un cambio chico llega a la app en minutos.

Para corregir horas, salas, sedes o duraciones de unas pocas funciones, después
de escribir la afirmación en festivals/staging/<id>-afirmaciones.json:

    python3 pipeline/corto.py <fest-id>            # rearma, muestra el diff y publica
    python3 pipeline/corto.py <fest-id> --probar   # rearma y muestra el diff; no publica

Qué hace, en orden (si algo falla, no sigue):
  1. corre el plan DESDE el primer paso que lee las afirmaciones (o desde
     ensamblar). No vuelve a bajar fuentes, ni a leer láminas, ni a enriquecer
     el catálogo: eso es el camino largo (correr.py), para cuando la fuente
     cambió en muchos puntos;
  2. publicar.py → festivals/<id>.json;
  3. el diff contra lo publicado, función por función. Si cambian más de
     MAX_CHICO funciones, frena: eso no es un cambio chico;
  4. publicar-datos.py: los mismos guardianes de siempre, y al almacén.
Después va el PR de datos (solo festivals/, nunca validate.py).

POR QUÉ (28 oct 2026): corregir las horas de unos talleres de Miradas terminó en
correr.py completo «por las dudas» —láminas, catálogo, TMDB— y una tarde entera.
La regla del camino corto existía desde el 21 oct, pero era una receta de cinco
comandos; esto la vuelve uno solo.
"""
import json, os, re, subprocess, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_CHICO = 30


def paso_inicial(pasos, leer=lambda ruta: open(ruta, encoding='utf-8').read()):
    """Número (1-based) del primer paso que lee las afirmaciones; si ninguno, el
    de ensamblar. None si el plan no tiene ensamblar (no hay camino corto)."""
    ens = None
    for i, p in enumerate(pasos, 1):
        m = re.search(r'pipeline/(\S+\.py)', p['cmd'])
        if not m:
            continue
        if m.group(1) == 'ensamblar.py' and ens is None:
            ens = i
        try:
            if 'afirmaciones' in leer(os.path.join(REPO, 'pipeline', m.group(1))):
                return i
        except OSError:
            pass
    return ens


def _clave(f):
    return f.get('id') or f"{f.get('title')}|{f.get('day')}|{f.get('time')}|{f.get('venue')}"


def cambios(antes, despues):
    """Funciones que entran, salen o cambian entre dos festivals/<id>.json."""
    a = {_clave(f): f for f in antes.get('films', [])}
    d = {_clave(f): f for f in despues.get('films', [])}
    out = []
    for k in sorted(set(a) | set(d)):
        if k not in a:
            out.append(('+', d[k]))
        elif k not in d:
            out.append(('−', a[k]))
        elif a[k] != d[k]:
            campos = sorted(c for c in set(a[k]) | set(d[k]) if a[k].get(c) != d[k].get(c))
            out.append(('~', d[k], campos, a[k]))
    return out


def _correr(cmd):
    print(f'\n─── {" ".join(cmd)}')
    if subprocess.run(cmd, cwd=REPO).returncode != 0:
        sys.exit(f'✗ falló: {" ".join(cmd)}')


def main():
    if len(sys.argv) < 2 or sys.argv[1].startswith('-'):
        sys.exit(__doc__.split('Qué hace')[0].strip())
    fid = sys.argv[1]
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import lib
    try:
        pasos = lib.cargar_plan(fid)['pasos']
    except (AssertionError, FileNotFoundError, KeyError) as e:
        sys.exit(f'✗ plan de {fid}: {e}')
    n = paso_inicial(pasos)
    if not n:
        sys.exit(f'✗ el plan de {fid} no tiene ensamblar.py: no hay camino corto, usá correr.py')
    print(f'═══ camino corto · {fid} · pasos {n}–{len(pasos)} de {len(pasos)} (se salta 1–{n - 1})')

    ruta = os.path.join(REPO, 'festivals', f'{fid}.json')
    antes = json.load(open(ruta, encoding='utf-8')) if os.path.exists(ruta) else {'films': []}
    _correr(['python3', 'pipeline/correr.py', fid, '--desde', str(n)])
    _correr(['python3', 'pipeline/publicar.py', fid])

    cs = cambios(antes, json.load(open(ruta, encoding='utf-8')))
    print(f'\n═══ {len(cs)} función(es) cambian:')
    for c in cs[:40]:
        f = c[1]
        linea = f"  {c[0]} {f.get('day')} {f.get('time')} · {str(f.get('title'))[:40]}"
        if c[0] == '~':
            linea += ' · ' + ', '.join(f"{k}: {c[3].get(k)!r}→{f.get(k)!r}"[:60] for k in c[2][:3])
        print(linea)
    if not cs:
        sys.exit('· nada cambió en la app: ¿la afirmación está bien escrita?')
    if len(cs) > MAX_CHICO and '--grande' not in sys.argv:
        sys.exit(f'✗ {len(cs)} funciones cambian: esto no es un cambio chico. Revisá el diff '
                 f'(o --grande si de verdad es así)')
    if '--probar' in sys.argv:
        print('\n· --probar: no se publica'); return
    _correr(['python3', 'pipeline/publicar-datos.py', fid])
    print(f'\n✓ {fid} publicado. Falta el PR de datos (solo festivals/).')


if __name__ == '__main__':
    main()
