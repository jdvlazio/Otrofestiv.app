#!/usr/bin/env python3
"""Posts de Instagram de una cuenta, desde la memoria del vigía: Apify solo
para lo que falta.

Por qué existe: el vigía (ig_vigia.py) guarda cada post que lee en
fuentes/ig-vigia/<shortCode>.json y nunca pide dos veces lo mismo. Pero los
agentes de onboarding llamaban a Apify por su cuenta y volvían a bajar posts
ya guardados: del 21 al 25 oct 2026 eso fue más de la mitad del gasto (US$3
de los US$5 del mes). Toda lectura de IG de un festival pasa por aquí.

Uso:
  python3 pipeline/ig_posts.py <cuenta> [--desde 2026-10-01] [--traer]
    sin --traer: solo la memoria (gratis).
    con --traer: si la cuenta no se consultó en las últimas 6 h, pide a Apify
                 SOLO lo publicado desde la última consulta (o desde --desde si
                 nunca se consultó), lo guarda en la memoria y actualiza el
                 historial del vigía.
Imprime JSON: [{shortCode, fecha, url, laminas, texto, archivo}] del más viejo
al más nuevo. Incluye los posts colaborativos (cuenta como coautora).
"""
import argparse
import glob
import json
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ig_vigia as v  # noqa: E402

FRESCO_H = 6


def de_la_cuenta(it, cuenta):
    if it.get('ownerUsername') == cuenta:
        return True
    return cuenta in {x.get('username') for x in it.get('coauthorProducers') or []}


def en_memoria(cuenta, desde=None):
    out = []
    for p in glob.glob(os.path.join(v.SALIDA, '*.json')):
        if os.path.basename(p).startswith('fb-'):
            continue
        try:
            it = json.load(open(p))
        except (OSError, ValueError):
            continue
        if not de_la_cuenta(it, cuenta):
            continue
        ts = (it.get('timestamp') or '').replace('Z', '').split('.')[0]
        if desde and ts < desde:
            continue
        out.append({'shortCode': it.get('shortCode'), 'fecha': ts,
                    'url': f"https://www.instagram.com/p/{it.get('shortCode')}/",
                    'laminas': len(it.get('childPosts') or it.get('images') or []) or 1,
                    'texto': (it.get('caption') or '')[:300], 'archivo': p})
    return sorted(out, key=lambda x: x['fecha'])


def traer(cuenta, desde, ahora):
    estado = json.load(open(v.ESTADO)) if os.path.exists(v.ESTADO) else {}
    e = estado.get(cuenta, {})
    if e.get('consultado') and ahora - datetime.fromisoformat(e['consultado']) < timedelta(hours=FRESCO_H):
        return 'fresco'
    token = os.environ.get('APIFY_TOKEN')
    if not token:
        sys.exit('Falta APIFY_TOKEN (hacer `source ~/.zshrc`).')
    d = v.desde([cuenta], estado, ahora) if e.get('consultado') else (desde or v.desde([cuenta], estado, ahora))
    nuevos, sin_leer = v.clasificar(v.apify([cuenta], d, token), [cuenta], estado)
    if sin_leer:
        return f'no pude leer: {sin_leer}'
    os.makedirs(v.SALIDA, exist_ok=True)
    e = estado.setdefault(cuenta, {})
    for it in nuevos[cuenta]:
        ts = it['timestamp'].replace('Z', '').split('.')[0]
        json.dump(it, open(os.path.join(v.SALIDA, f"{it['shortCode']}.json"), 'w'), ensure_ascii=False)
        e['ultimo_post'] = max(e.get('ultimo_post', ''), ts)
    e['consultado'] = ahora.isoformat(timespec='seconds')
    json.dump(estado, open(v.ESTADO, 'w'), ensure_ascii=False, indent=1)
    return f'{len(nuevos[cuenta])} nuevos desde {d}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cuenta')
    ap.add_argument('--desde')
    ap.add_argument('--traer', action='store_true')
    a = ap.parse_args()
    cuenta = a.cuenta.lstrip('@')
    if a.traer:
        print('# apify:', traer(cuenta, a.desde, datetime.now()), file=sys.stderr)
    print(json.dumps(en_memoria(cuenta, a.desde), ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
