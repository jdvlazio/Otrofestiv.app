#!/usr/bin/env python3
"""Bandeja del vigía: todo post de IG que se lee termina decidido y, si trae
dato, aplicado (16 nov 2026).

Por qué existe: el vigía bajaba y REPORTABA posts, pero nada obligaba a que un
post leído llegara a la app. El palmarés de Villa de Leyva (DfzcCpZm2Uq) quedó
reportado como «APLICAR» y nadie lo aplicó.

Ciclo de un post:
  pendiente  → lo mete ig_vigia.py al traerlo
  decidido   → `--decidir <sc> palmares|programacion --evidencia "lámina N dice…"`
  aplicado   → `--aplicado <sc> --pr <n>`
  sin_dato   → `--decidir <sc> sin_dato --evidencia … --por-que …` (termina ahí)

Cierre de festival: cuando sale de la ventana (fin + TERMINADO días),
`--cierre <fid> palmares_cargado|no_compite|sin_palmares_publicado --evidencia …`.

`--guardian` sale con código 1 si algo quedó colgado (ver `problemas`).
La bandeja vive fuera del repo: ~/.otrofestiv/bandeja.json, o $OTROFESTIV_BANDEJA.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta

RUTA = os.environ.get('OTROFESTIV_BANDEJA') or os.path.expanduser('~/.otrofestiv/bandeja.json')
TERMINADO = 8      # mismo valor que ig_vigia.TERMINADO: no todo festival compite
PLAZO_H = 4        # horas que un post puede quedar pendiente o decidido sin aplicar
CON_DATO = ('palmares', 'programacion')
DECISIONES = CON_DATO + ('sin_dato',)
CIERRES = ('palmares_cargado', 'no_compite', 'sin_palmares_publicado')


def _iso(d):
    return d.isoformat(timespec='seconds')


def cargar(ruta):
    if os.path.exists(ruta):
        with open(ruta) as f:
            b = json.load(f)
    else:
        b = {}
    b.setdefault('posts', {})
    b.setdefault('festivales', {})
    return b


def guardar(ruta, b):
    os.makedirs(os.path.dirname(os.path.abspath(ruta)), exist_ok=True)
    tmp = ruta + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(b, f, ensure_ascii=False, indent=1)
    os.replace(tmp, ruta)


def ingresar(ruta, fid, fin, item, ahora):
    """Mete un post traído por ig_vigia.py. Idempotente: un post ya en la
    bandeja no vuelve a «pendiente»; si es colaborativo suma el festival."""
    b = cargar(ruta)
    sc = item['shortCode']
    p = b['posts'].get(sc)
    if p is None:
        b['posts'][sc] = {
            'festival': fid, 'festivales': [fid], 'shortCode': sc,
            'url': f'https://www.instagram.com/p/{sc}/',
            'timestamp': item.get('timestamp'),
            'laminas': len(item.get('childPosts') or item.get('images') or []) or 1,
            'estado': 'pendiente', 'ingreso': _iso(ahora)}
    elif fid not in p['festivales']:
        p['festivales'].append(fid)
    if fid and fin:
        b['festivales'].setdefault(fid, {})['fin'] = fin
    guardar(ruta, b)
    return b['posts'][sc]


def decidir(b, sc, decision, evidencia, por_que, ahora):
    if sc not in b['posts']:
        raise ValueError(f'{sc} no está en la bandeja')
    if decision not in DECISIONES:
        raise ValueError(f'decisión inválida: {decision} (una de {", ".join(DECISIONES)})')
    if not (evidencia or '').strip():
        raise ValueError('--evidencia es obligatoria: qué dice la lámina («lámina N dice…»)')
    if decision == 'sin_dato' and not (por_que or '').strip():
        raise ValueError('sin_dato exige --por-que')
    p = b['posts'][sc]
    p.update({'estado': 'sin_dato' if decision == 'sin_dato' else 'decidido',
              'decision': decision, 'evidencia': evidencia.strip(), 'decidido': _iso(ahora)})
    if por_que:
        p['por_que'] = por_que.strip()
    return p


def aplicado(b, sc, pr, ahora):
    p = b['posts'].get(sc)
    if p is None:
        raise ValueError(f'{sc} no está en la bandeja')
    if p.get('decision') not in CON_DATO:
        raise ValueError(f'{sc} no está decidido como palmares/programacion (está «{p["estado"]}»)')
    if not pr:
        raise ValueError('--pr es obligatorio')
    p.update({'estado': 'aplicado', 'pr': int(pr), 'aplicado': _iso(ahora)})
    return p


def cierre(b, fid, motivo, evidencia, ahora):
    if motivo not in CIERRES:
        raise ValueError(f'cierre inválido: {motivo} (uno de {", ".join(CIERRES)})')
    if not (evidencia or '').strip():
        raise ValueError('--evidencia es obligatoria para el cierre')
    f = b['festivales'].setdefault(fid, {})
    f['cierre'] = {'motivo': motivo, 'evidencia': evidencia.strip(), 'fecha': _iso(ahora)}
    return f


def problemas(b, ahora):
    """Lista de textos: todo lo que deja al guardián en rojo."""
    out = []
    limite = timedelta(hours=PLAZO_H)
    for sc, p in sorted(b['posts'].items()):
        tag = f"{sc} ({p.get('festival')})"
        if p['estado'] == 'pendiente':
            if ahora - datetime.fromisoformat(p['ingreso']) > limite:
                out.append(f'PENDIENTE >{PLAZO_H} h: {tag} {p["url"]}')
            continue
        if not (p.get('evidencia') or '').strip():
            out.append(f'DECISIÓN SIN EVIDENCIA: {tag}')
        if p['estado'] == 'sin_dato' and not (p.get('por_que') or '').strip():
            out.append(f'SIN_DATO SIN POR QUÉ: {tag}')
        if p['estado'] == 'decidido' and ahora - datetime.fromisoformat(p['decidido']) > limite:
            out.append(f'DECIDIDO {p["decision"]} SIN APLICAR >{PLAZO_H} h: {tag} {p["url"]}')
    hoy = ahora.date()
    for fid, f in sorted(b['festivales'].items()):
        fin = f.get('fin')
        if not fin or f.get('cierre'):
            continue
        if hoy > datetime.strptime(fin, '%Y-%m-%d').date() + timedelta(days=TERMINADO):
            out.append(f'SIN CIERRE: {fid} salió de la ventana (fin {fin} + {TERMINADO} d) — '
                       f'--cierre {fid} {"|".join(CIERRES)} --evidencia …')
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--bandeja', default=RUTA)
    ap.add_argument('--hoy', help='ISO, para pruebas')
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--pendientes', action='store_true')
    g.add_argument('--decidir', nargs=2, metavar=('SHORTCODE', 'DECISION'))
    g.add_argument('--aplicado', metavar='SHORTCODE')
    g.add_argument('--cierre', nargs=2, metavar=('FID', 'MOTIVO'))
    g.add_argument('--guardian', action='store_true')
    ap.add_argument('--evidencia')
    ap.add_argument('--por-que', dest='por_que')
    ap.add_argument('--pr')
    a = ap.parse_args(argv)
    ahora = datetime.fromisoformat(a.hoy) if a.hoy else datetime.now()
    b = cargar(a.bandeja)
    try:
        if a.pendientes:
            res = [p for p in b['posts'].values() if p['estado'] in ('pendiente', 'decidido')]
            print(json.dumps(res, ensure_ascii=False, indent=1))
            return 0
        if a.guardian:
            mal = problemas(b, ahora)
            for m in mal:
                print('✗', m)
            if mal:
                print(f'Guardián de la bandeja: {len(mal)} pendiente(s).', file=sys.stderr)
                return 1
            print('✓ bandeja al día')
            return 0
        if a.decidir:
            r = decidir(b, a.decidir[0], a.decidir[1], a.evidencia, a.por_que, ahora)
        elif a.aplicado:
            r = aplicado(b, a.aplicado, a.pr, ahora)
        else:
            r = cierre(b, a.cierre[0], a.cierre[1], a.evidencia, ahora)
    except ValueError as e:
        print(f'✗ {e}', file=sys.stderr)
        return 2
    guardar(a.bandeja, b)
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
