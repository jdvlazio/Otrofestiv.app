#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""actualizar.py <fid> — re-arma UN festival desde su fuente estructurada y dice
si lo que cambió se puede publicar SOLO (docs/FUNCION.md §5.2).

POR QUÉ EXISTE (17 oct 2026). El vigía vio el 16 a las 7:00 que Fantasmagoría
movió «Critters» de las 19:00 a las 17:00 del 17; la app lo publicó el 17 a
mediodía, cuando alguien leyó el reporte. Juan: «Si el vigía lo había detectado
qué esperamos? … tengo que estar todo el día pendiente yo?». El vigía avisa; esto
ACTÚA, dentro de una frontera estrecha que acordaron senior dev y tech lead:

  · solo la fuente ESTRUCTURADA del propio festival (la base de Fantasmagoría,
    el JSON de FICICA): los pasos que declara pipeline/actualizador.json. Lo de
    una sala o de Instagram va a la cola de propuestas, nunca acá.
  · solo cambios de DÍA, HORA o SALA de funciones que ya existen; cualquier otra
    diferencia —una función nueva o que sale, otro campo, la raíz— FRENA.
  · un TOPE de funciones cambiadas por corrida: un cambio grande suele ser una
    fuente rota, no una reprogramación.
  · un INTERRUPTOR (`activo`) que lo apaga sin tocar código.
  · sin cambios no hay nada que publicar: cada deploy hace recargar a los
    teléfonos, y publicar cada hora sin motivo molesta en pleno festival.

Salidas: 0 sin cambios (todo queda como estaba) · 10 cambios publicables
(el resumen queda en <scratch>/actualizar-<fid>.json para el PR) · 2 frenado
(todo queda como estaba; el porqué en el mismo archivo) · 1 error.
La tarea programada hace lo demás: validadores, PR, CI, merge, y confirmar que
la hora nueva está en otrofestiv.app.
"""
import json, os, subprocess, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(REPO, 'pipeline', 'actualizador.json')
PERMITIDOS = ('day', 'time', 'sala')
INTERNOS = ('_src', 'day_order', '_procedencia')
RAIZ_INTERNA = ('films', 'sections', '_provenance')


def puede(cfg, fid):
    """None si puede actuar sobre fid; si no, el porqué."""
    if not cfg.get('activo'):
        return 'el actualizador está apagado (pipeline/actualizador.json: activo=false)'
    if fid not in (cfg.get('festivales') or {}):
        return f'{fid} no está habilitado en pipeline/actualizador.json'
    return None


def _mins(f):
    h, m = (f.get('time') or '00:00').split(':')[:2]
    return (f.get('day') or '', int(h) * 60 + int(m))


def comparar(viejo, nuevo, tope):
    """→ (cambios, frenos). Las funciones se emparejan por obra + sede; dentro de
    eso, por día y hora exactos, y lo que queda, en orden."""
    frenos = []
    for k in sorted(set(viejo) | set(nuevo)):
        if k not in RAIZ_INTERNA and viejo.get(k) != nuevo.get(k):
            frenos.append(f'cambió «{k}» en la raíz del festival')
    grupos = {}
    for lado, films in (('a', viejo.get('films') or []), ('b', nuevo.get('films') or [])):
        for f in films:
            grupos.setdefault((f.get('title'), f.get('venue')), {'a': [], 'b': []})[lado].append(f)
    cambios = []
    for (tit, ven), g in sorted(grupos.items(), key=lambda x: str(x[0])):
        a = sorted(g['a'], key=_mins)
        b = sorted(g['b'], key=_mins)
        exactos = [(x, y) for x in a for y in b if _mins(x) == _mins(y)]
        usados_a, usados_b, pares = set(), set(), []
        for x, y in exactos:
            if id(x) not in usados_a and id(y) not in usados_b:
                usados_a.add(id(x)); usados_b.add(id(y)); pares.append((x, y))
        resto_a = [x for x in a if id(x) not in usados_a]
        resto_b = [y for y in b if id(y) not in usados_b]
        if len(resto_a) != len(resto_b):
            if len(resto_b) > len(resto_a):
                frenos.append(f'función nueva: «{tit}» en {ven}')
            else:
                frenos.append(f'función que sale: «{tit}» en {ven}')
            continue
        pares += list(zip(resto_a, resto_b))
        for x, y in pares:
            for c in sorted(set(x) | set(y)):
                if c in INTERNOS or x.get(c) == y.get(c):
                    continue
                if c in PERMITIDOS:
                    cambios.append({'title': tit, 'campo': c, 'antes': x.get(c), 'ahora': y.get(c),
                                    'day': x.get('day')})
                else:
                    frenos.append(f'«{tit}» ({x.get("day")} {x.get("time")}): cambió «{c}», que el actualizador no publica solo')
    n = len({(c['title'], c['day']) for c in cambios})
    if n > tope:
        frenos.append(f'{n} funciones cambian: más que el tope ({tope}); ¿fuente rota?')
    return cambios, frenos


def _git(*a):
    return subprocess.run(['git', '-C', REPO, *a], capture_output=True, text=True)


def main():
    fid = sys.argv[1] if len(sys.argv) > 1 else sys.exit(__doc__)
    cfg = json.load(open(CONFIG, encoding='utf-8'))
    por_que = puede(cfg, fid)
    salida = os.path.join(os.environ.get('ACTUALIZAR_SALIDA', REPO), f'actualizar-{fid}.json')
    if por_que:
        print(f'· {por_que}')
        return 0
    if _git('status', '--porcelain').stdout.strip():
        sys.exit('✗ la copia de trabajo no está limpia: el actualizador trabaja solo en su propia copia')
    pub = f'festivals/{fid}.json'
    viejo = json.loads(_git('show', f'HEAD:{pub}').stdout)
    for cmd in cfg['festivales'][fid].get('antes') or []:   # bajar la fuente
        r = subprocess.run(cmd, shell=True, cwd=REPO, capture_output=True, text=True)
        if r.returncode:
            _git('checkout', '--', '.')
            json.dump({'estado': 'frenado', 'frenos': [f'falló «{cmd}»'], 'salida': (r.stdout + r.stderr)[-1500:]},
                      open(salida, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
            print(f'✗ {fid}: falló «{cmd}» — frenado')
            return 2
    for n in cfg['festivales'][fid]['pasos']:
        r = subprocess.run([sys.executable, 'pipeline/correr.py', fid, '--paso', str(n)], cwd=REPO,
                           capture_output=True, text=True)
        if r.returncode:
            _git('checkout', '--', '.')
            json.dump({'estado': 'frenado', 'frenos': [f'el paso {n} falló'], 'salida': r.stdout[-1500:]},
                      open(salida, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
            print(f'✗ {fid}: el paso {n} falló — frenado (detalle en {salida})')
            return 2
    r = subprocess.run([sys.executable, 'pipeline/publicar.py', fid], cwd=REPO, capture_output=True, text=True)
    if r.returncode:
        _git('checkout', '--', '.')
        json.dump({'estado': 'frenado', 'frenos': ['publicar.py no aceptó el build'], 'salida': r.stdout[-1500:]},
                  open(salida, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f'✗ {fid}: publicar.py no aceptó el build — frenado')
        return 2
    nuevo = json.load(open(os.path.join(REPO, pub), encoding='utf-8'))
    cambios, frenos = comparar(viejo, nuevo, cfg.get('tope', 5))
    if frenos or not cambios:
        _git('checkout', '--', '.')
        _git('clean', '-fdq', 'festivals/staging')
    if frenos:
        json.dump({'estado': 'frenado', 'frenos': frenos, 'cambios': cambios},
                  open(salida, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f'✗ {fid}: frenado —\n  · ' + '\n  · '.join(frenos))
        return 2
    if not cambios:
        print(f'✓ {fid}: sin cambios')
        return 0
    json.dump({'estado': 'publicable', 'cambios': cambios}, open(salida, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(f'✓ {fid}: {len(cambios)} cambio(s) publicable(s):')
    for c in cambios:
        print(f"  · «{c['title']}» {c['day']}: {c['campo']} {c['antes']} → {c['ahora']}")
    return 10


if __name__ == '__main__':
    sys.exit(main())
