#!/usr/bin/env python3
"""Vigía de Instagram por Apify: trae SOLO los posts nuevos de las cuentas de
los festivales vivos y los deja en fuentes/ig-vigia/.

Por qué Apify: sin sesión solo leemos posts cuyo enlace ya conocemos
(ig_sin_sesion.py); para saber QUÉ publicó una cuenta hace falta listar su
perfil, y eso con la cuenta de Juan está prohibido (memoria ig-sin-sesion).
Apify lo lista desde sus servidores. Plan gratis: US$5 al mes → todo aquí
está pensado para gastar lo mínimo.

Qué cuentas y cada cuánto (tiers):
  - en camino (empieza en ≤ CAMINO días) y en curso → cada corrida
  - terminado hace ≤ TERMINADO días (palmarés tardío) → una vez al día
  - el resto no se mira.
Las cuentas salen de `instagram:` en src/config.js y, para las que no lo
traen, de pipeline/ig-vigia-cuentas.json (que también lista pre-onboardings).

Historial (~/.otrofestiv/ig-vigia-estado.json): por cuenta, la fecha del
último post visto y de la última consulta. Cada corrida pide a Apify solo lo
publicado desde la consulta anterior, y descarta lo ya visto: nada se lee
(ni se paga) dos veces.

Fallo mudo: Apify a veces marca como exitosa una corrida bloqueada. Un ítem
con `error`, o una corrida de 3+ cuentas que vuelve sin ningún ítem, se
reporta como NO_PUDE_LEER — nunca como «sin novedades».

Uso:
  python3 pipeline/ig_vigia.py            # corre y reporta JSON
  python3 pipeline/ig_vigia.py --simular  # dice qué consultaría, sin gastar
  python3 pipeline/ig_vigia.py --hoy 2026-10-21T13:00   # reloj fijo (tests)
"""
import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timedelta

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(RAIZ, 'src', 'config.js')
CUENTAS = os.path.join(RAIZ, 'pipeline', 'ig-vigia-cuentas.json')
ESTADO = os.path.expanduser('~/.otrofestiv/ig-vigia-estado.json')
SALIDA = os.path.join(RAIZ, 'fuentes', 'ig-vigia')

CAMINO = 7        # días antes del inicio en que se empieza a mirar
TERMINADO = 8     # días después del fin en que se sigue mirando (palmarés)
DIARIO_H = 20     # horas mínimas entre consultas de un festival terminado
LIMITE = 10       # posts máximos por cuenta y corrida
PRIMERA_VEZ_D = 3  # sin historial: mirar solo los últimos N días
ACTOR = 'apify~instagram-post-scraper'

_ENTRADA = re.compile(r"\n\s{2}'?([a-z0-9]+)'?\s*:\s*\{")


def festivales_config(texto):
    """id → {cuenta, inicio, fin} desde src/config.js (solo los que tienen fechas)."""
    out = {}
    pos = [(m.group(1), m.end()) for m in _ENTRADA.finditer(texto)]
    for i, (fid, ini) in enumerate(pos):
        seg = texto[ini:pos[i + 1][1] if i + 1 < len(pos) else len(texto)]
        s = re.search(r"festivalStartStr:'(\d{4}-\d\d-\d\d)", seg)
        e = re.search(r"festivalEndStr:'(\d{4}-\d\d-\d\d)", seg)
        if not (s and e):
            continue
        ig = re.search(r"instagram:'([^']+)'", seg)
        out[fid] = {'cuenta': ig.group(1) if ig else None,
                    'inicio': s.group(1), 'fin': e.group(1)}
    return out


def vigilados(config, cuentas, ahora):
    """Lista de {id, cuenta, tier} que tocan hoy. tier: 'vivo' | 'terminado'."""
    fests = dict(config)
    for fid, cta in cuentas.get('festivales', {}).items():
        if fid in fests and not fests[fid]['cuenta']:
            fests[fid]['cuenta'] = cta
    for p in cuentas.get('preonboarding', []):
        fests.setdefault(p['id'], {'cuenta': p['cuenta'], 'inicio': p['inicio'], 'fin': p['fin']})
    hoy = ahora.date()
    out = []
    for fid, f in sorted(fests.items()):
        if not f['cuenta']:
            continue
        ini = datetime.strptime(f['inicio'], '%Y-%m-%d').date()
        fin = datetime.strptime(f['fin'], '%Y-%m-%d').date()
        if ini - timedelta(days=CAMINO) <= hoy <= fin:
            out.append({'id': fid, 'cuenta': f['cuenta'], 'tier': 'vivo'})
        elif fin < hoy <= fin + timedelta(days=TERMINADO):
            out.append({'id': fid, 'cuenta': f['cuenta'], 'tier': 'terminado'})
    return out


def toca(v, estado, ahora):
    """¿Se consulta esta cuenta en esta corrida? (terminados: una vez al día)."""
    if v['tier'] == 'vivo':
        return True
    ult = estado.get(v['cuenta'], {}).get('consultado')
    return not ult or ahora - datetime.fromisoformat(ult) >= timedelta(hours=DIARIO_H)


def desde(cuentas, estado, ahora):
    """Fecha mínima a pedir: la consulta anterior más vieja entre las cuentas
    (menos 1 h de margen). Lo publicado antes ya se vio; lo repetido en el
    margen lo descarta `clasificar` por la fecha del último post visto."""
    fechas = []
    for c in cuentas:
        u = estado.get(c, {}).get('consultado')
        fechas.append(datetime.fromisoformat(u) - timedelta(hours=1) if u
                      else ahora - timedelta(days=PRIMERA_VEZ_D))
    return min(fechas).strftime('%Y-%m-%dT%H:%M:%S')


def clasificar(items, cuentas, estado):
    """Separa por cuenta los posts nuevos y detecta las cuentas que no se leyeron."""
    nuevos = {c: [] for c in cuentas}
    errores = {}
    for it in items:
        if it.get('error'):
            c = (it.get('username') or it.get('inputUrl') or '').rstrip('/').split('/')[-1]
            errores[c] = it.get('errorDescription') or it.get('error')
            continue
        c = it.get('ownerUsername')
        if c not in nuevos:
            # Post colaborativo: lo publica otra cuenta CON el festival como
            # coautor (25 oct: la cancelación de «Las pesadillas del siervo»
            # en Ficcali salió así y el vigía la descartó). Cuenta como del
            # festival. Solo etiquetado (sin coautoría) sigue descartado.
            coautores = {x.get('username') for x in it.get('coauthorProducers') or []}
            c = next((x for x in cuentas if x in coautores), None)
            if not c:
                continue
        ult = estado.get(c, {}).get('ultimo_post')
        ts = (it.get('timestamp') or '').replace('Z', '').split('.')[0]
        if ult and ts <= ult:
            continue
        nuevos[c].append(it)
    sin_leer = {c: str(errores[c]) for c in cuentas if c in errores}
    if not items and len(cuentas) >= 3:
        # ninguna de varias cuentas publicó nada: más probable un bloqueo mudo
        sin_leer['*'] = f'Apify devolvió 0 ítems para {len(cuentas)} cuentas'
    return nuevos, sin_leer


def apify(cuentas, desde_iso, token):
    cuerpo = json.dumps({'username': cuentas, 'resultsLimit': LIMITE,
                         'onlyPostsNewerThan': desde_iso, 'skipPinnedPosts': True}).encode()
    url = (f'https://api.apify.com/v2/acts/{ACTOR}/run-sync-get-dataset-items'
           f'?token={token}&timeout=280')
    req = urllib.request.Request(url, cuerpo, {'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--simular', action='store_true')
    ap.add_argument('--hoy')
    a = ap.parse_args()
    ahora = datetime.fromisoformat(a.hoy) if a.hoy else datetime.now()
    estado = json.load(open(ESTADO)) if os.path.exists(ESTADO) else {}
    vig = vigilados(festivales_config(open(CONFIG).read()), json.load(open(CUENTAS)), ahora)
    ahora_toca = [v for v in vig if toca(v, estado, ahora)]
    cuentas = sorted({v['cuenta'] for v in ahora_toca})
    informe = {'hora': ahora.isoformat(timespec='minutes'),
               'consultadas': [f"{v['id']} @{v['cuenta']} ({v['tier']})" for v in ahora_toca],
               'saltadas_hoy_ya_vistas': [v['id'] for v in vig if v not in ahora_toca]}
    if not cuentas:
        print(json.dumps(informe, ensure_ascii=False, indent=1))
        return
    d = desde(cuentas, estado, ahora)
    informe['desde'] = d
    if a.simular:
        print(json.dumps(informe, ensure_ascii=False, indent=1))
        return
    token = os.environ.get('APIFY_TOKEN')
    if not token:
        sys.exit('Falta APIFY_TOKEN (hacer `source ~/.zshrc`).')
    items = apify(cuentas, d, token)
    nuevos, sin_leer = clasificar(items, cuentas, estado)
    os.makedirs(SALIDA, exist_ok=True)
    informe['nuevos'] = []
    for c in cuentas:
        e = estado.setdefault(c, {})
        e['consultado'] = ahora.isoformat(timespec='seconds')
        for it in sorted(nuevos[c], key=lambda x: x.get('timestamp', '')):
            ts = it['timestamp'].replace('Z', '').split('.')[0]
            json.dump(it, open(os.path.join(SALIDA, f"{it['shortCode']}.json"), 'w'), ensure_ascii=False)
            e['ultimo_post'] = max(e.get('ultimo_post', ''), ts)
            informe['nuevos'].append({'cuenta': c, 'fecha': ts, 'post': f"https://www.instagram.com/p/{it['shortCode']}/",
                                      'laminas': len(it.get('childPosts') or it.get('images') or []) or 1,
                                      'texto': (it.get('caption') or '')[:300]})
    informe['NO_PUDE_LEER'] = sin_leer
    os.makedirs(os.path.dirname(ESTADO), exist_ok=True)
    json.dump(estado, open(ESTADO, 'w'), ensure_ascii=False, indent=1)
    print(json.dumps(informe, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
