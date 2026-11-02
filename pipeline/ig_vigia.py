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
reporta como NO_PUDE_LEER — nunca como «sin novedades». La cuenta que falla
se reintenta sola una vez; si sigue fallando NO se marca consultada (la
próxima corrida pide de nuevo desde la última lectura buena) y a los 3 fallos
seguidos sale en ALERTA_FALLOS_SEGUIDOS. SIN_CUENTA_IG lista los festivales
del config, vivos o a ≤45 días, que no tienen cuenta: no se están mirando.

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
CERRADOS = os.path.expanduser('~/.otrofestiv/palmares-cerrados.json')
SALIDA = os.path.join(RAIZ, 'fuentes', 'ig-vigia')

CAMINO = 7        # días antes del inicio en que se empieza a mirar
TERMINADO = 8     # días después del fin en que se sigue mirando (palmarés)
DIARIO_H = 20     # horas mínimas entre consultas de un festival terminado
LIMITE = 5        # posts máximos por cuenta y corrida (26 oct: 10→5 para no pasar el plan gratis; 3 corridas al día bastan)
PRIMERA_VEZ_D = 3  # sin historial: mirar solo los últimos N días
ACTOR = 'apify~instagram-post-scraper'
# RESPALDO (2 nov 2026): lobstr.io, plan gratis de 100 posts/mes, sin cuenta de
# Instagram (lee solo lo público). Entra cuando a Apify le queda menos de
# APIFY_PISO_USD del mes o cuando una llamada a Apify falla por HTTP (el 502
# del 2 nov tumbó la corrida entera). Devuelve hasta 10 láminas por carrusel;
# las demás se bajan por el embed como siempre.
APIFY_PISO_USD = 1.0
LOBSTR_CRAWLER = 'd25fddae52eb78eb385e60bc2adb6d1e'   # Instagram Post Scraper
LOBSTR_SQUID = 'otrofestiv-vigia'
# lobstr NO respeta `hours_back` (2 nov: con 3 h devolvió posts de hace 15 y 20 h)
# y cobra cada post devuelto: se topa por cuenta y corrida más bajo que Apify
LOBSTR_LIMITE = 2
ACTOR_FB = 'apify~facebook-posts-scraper'

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


def vigilados(config, cuentas, ahora, cerrados=()):
    """Lista de {id, cuenta, tier} que tocan hoy. tier: 'vivo' (en curso o
    empieza mañana: cada corrida) | 'camino' | 'terminado' (una vez al día)."""
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
        if ini - timedelta(days=1) <= hoy <= fin:
            out.append({'id': fid, 'cuenta': f['cuenta'], 'tier': 'vivo'})
        elif ini - timedelta(days=CAMINO) <= hoy < ini - timedelta(days=1):
            # En camino: una vez al día. Apify cobra cada consulta aunque no haya
            # posts nuevos (~US$0,003 por cuenta): mirar 3 veces al día una cuenta
            # que publica una selección por semana era casi todo el gasto (26 oct).
            out.append({'id': fid, 'cuenta': f['cuenta'], 'tier': 'camino'})
        elif fin < hoy <= fin + timedelta(days=TERMINADO) and fid not in cerrados:
            # Terminado: solo se mira por el palmarés. Si el vigía lo declaró
            # COMPLETO (todas las categorías anunciadas tienen ganadora publicada,
            # con evidencia en palmares-cerrados.json) deja de mirarse.
            out.append({'id': fid, 'cuenta': f['cuenta'], 'tier': 'terminado'})
    return out


def sin_cuenta(config, cuentas, ahora, dias=45):
    """Festivales del config vivos, terminados hace ≤TERMINADO días o que
    empiezan en ≤`dias` días SIN cuenta de IG: el vigía no los puede mirar y
    nadie se entera (25 oct: Villa de Leyva y Miradas quedaron afuera)."""
    extra = dict(cuentas.get('festivales', {}))
    extra.update({p['id']: p['url'] for p in cuentas.get('facebook', [])})
    hoy = ahora.date()
    out = []
    for fid, f in sorted(config.items()):
        if f['cuenta'] or extra.get(fid):
            continue
        ini = datetime.strptime(f['inicio'], '%Y-%m-%d').date()
        fin = datetime.strptime(f['fin'], '%Y-%m-%d').date()
        if ini - timedelta(days=dias) <= hoy <= fin + timedelta(days=TERMINADO):
            out.append(fid)
    return out


def paginas_fb(cuentas, ahora):
    """Páginas de Facebook a mirar hoy (festivales que no usan IG: Funza, 25 oct).
    En ig-vigia-cuentas.json: "facebook": [{"id","url","inicio","fin"}]. Mismos
    tiers que IG (en camino / en curso / terminado ≤8 días)."""
    hoy = ahora.date()
    out = []
    for p in cuentas.get('facebook', []):
        ini = datetime.strptime(p['inicio'], '%Y-%m-%d').date()
        fin = datetime.strptime(p['fin'], '%Y-%m-%d').date()
        if ini - timedelta(days=CAMINO) <= hoy <= fin + timedelta(days=TERMINADO):
            out.append(p)
    return out


def apify_fb(urls, desde_iso, token):
    cuerpo = json.dumps({'startUrls': [{'url': u} for u in urls], 'resultsLimit': LIMITE,
                         'onlyPostsNewerThan': desde_iso}).encode()
    url = (f'https://api.apify.com/v2/acts/{ACTOR_FB}/run-sync-get-dataset-items'
           f'?token={token}&timeout=280')
    req = urllib.request.Request(url, cuerpo, {'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)


def clasificar_fb(items, paginas, estado):
    """Agrupa por página los posts nuevos (por inputUrl/facebookUrl) y marca las que fallaron."""
    norm = lambda u: (u or '').rstrip('/').lower()
    por_url = {norm(p['url']): p['id'] for p in paginas}
    nuevos = {p['id']: [] for p in paginas}
    sin_leer = {}
    for it in items:
        pid = por_url.get(norm(it.get('inputUrl'))) or por_url.get(norm(it.get('facebookUrl')))
        if it.get('error') == 'no_items':
            continue  # sin posts nuevos desde la fecha: no es un fallo
        if it.get('error'):
            sin_leer[pid or '*'] = str(it.get('errorDescription') or it.get('error'))
            continue
        if not pid:
            continue
        ult = estado.get('fb:' + pid, {}).get('ultimo_post')
        ts = (it.get('time') or '').replace('Z', '').split('.')[0][:19]
        if ult and ts <= ult:
            continue
        nuevos[pid].append(it)
    return nuevos, sin_leer


def toca(v, estado, ahora):
    """¿Se consulta esta cuenta en esta corrida? (camino y terminados: una vez al día)."""
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


def apify_por_cuenta(cuentas, estado, ahora, token):
    """Una llamada por cuenta, cada una desde SU última consulta (26 oct). Con
    una sola llamada desde la fecha más vieja del grupo, Apify devolvía —y
    cobraba— posts de las cuentas recientes que ya teníamos. Apify cobra por
    ítem devuelto, no por llamada: partirlas no cuesta más. En paralelo."""
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=5) as ex:
        lotes = ex.map(lambda c: apify([c], desde([c], estado, ahora), token), cuentas)
    return [it for lote in lotes for it in lote]


def clasificar(items, cuentas, estado):
    """Separa por cuenta los posts nuevos y detecta las cuentas que no se leyeron."""
    nuevos = {c: [] for c in cuentas}
    errores = {}
    for it in items:
        if it.get('error') == 'no_items':
            continue  # «Empty or private data»: no hay posts nuevos desde la fecha pedida, NO es un bloqueo (25 oct: FICPA «fallaba» a diario por no publicar)
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
    """Un error HTTP de Apify (502, 429…) ya no tumba la corrida (2 nov): vuelve
    como ítem de error por cuenta, que `clasificar` manda a NO_PUDE_LEER y el
    respaldo de lobstr reintenta."""
    try:
        return _apify(cuentas, desde_iso, token)
    except Exception as ex:  # noqa: BLE001 — urllib, timeout, JSON roto: todo es «no se leyó»
        return [{'error': 'http', 'errorDescription': f'Apify: {ex}', 'username': c} for c in cuentas]


def _apify(cuentas, desde_iso, token):
    cuerpo = json.dumps({'username': cuentas, 'resultsLimit': LIMITE,
                         'onlyPostsNewerThan': desde_iso, 'skipPinnedPosts': True}).encode()
    url = (f'https://api.apify.com/v2/acts/{ACTOR}/run-sync-get-dataset-items'
           f'?token={token}&timeout=280')
    req = urllib.request.Request(url, cuerpo, {'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)


def vigilar_fb(cuentas_json, estado, ahora, token, informe):
    paginas = paginas_fb(cuentas_json, ahora)
    informe['facebook_consultadas'] = [f"{p['id']} {p['url']}" for p in paginas]
    informe['nuevos_facebook'] = []
    if not paginas:
        return
    claves = ['fb:' + p['id'] for p in paginas]
    d = desde(claves, estado, ahora)
    try:
        items = apify_fb([p['url'] for p in paginas], d, token)
    except Exception as e:  # una falla de FB no tumba la corrida de IG
        for p in paginas:
            informe['NO_PUDE_LEER']['fb:' + p['id']] = f'Apify FB: {e}'
        return
    nuevos, sin_leer = clasificar_fb(items, paginas, estado)
    for p in paginas:
        k = 'fb:' + p['id']
        e = estado.setdefault(k, {})
        if p['id'] in sin_leer or '*' in sin_leer:
            informe['NO_PUDE_LEER'][k] = sin_leer.get(p['id']) or sin_leer.get('*')
            e['fallos'] = e.get('fallos', 0) + 1
            continue
        e['fallos'] = 0
        e['consultado'] = ahora.isoformat(timespec='seconds')
        for it in sorted(nuevos[p['id']], key=lambda x: x.get('time', '')):
            ts = (it.get('time') or '').replace('Z', '').split('.')[0][:19]
            json.dump(it, open(os.path.join(SALIDA, f"fb-{it.get('postId')}.json"), 'w'), ensure_ascii=False)
            e['ultimo_post'] = max(e.get('ultimo_post', ''), ts)
            informe['nuevos_facebook'].append({'festival': p['id'], 'fecha': ts, 'post': it.get('url'),
                                               'imagenes': len(it.get('media') or []),
                                               'texto': (it.get('text') or '')[:300]})


def apify_saldo(token):
    """USD que le quedan a Apify en el mes, o None si no se pudo saber."""
    try:
        with urllib.request.urlopen(f'https://api.apify.com/v2/users/me/limits?token={token}', timeout=30) as r:
            d = json.load(r)['data']
        return d['limits']['maxMonthlyUsageUsd'] - d['current']['monthlyUsageUsd']
    except Exception:  # noqa: BLE001
        return None


def _lobstr(metodo, ruta, clave, cuerpo=None):
    req = urllib.request.Request(f'https://api.lobstr.io/v1/{ruta}', method=metodo,
                                 data=json.dumps(cuerpo).encode() if cuerpo is not None else None,
                                 headers={'Authorization': f'Token {clave}', 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def lobstr_a_apify(x):
    """Un resultado de lobstr con la forma de un ítem de Apify: así `clasificar`,
    el informe y ig_posts.py lo leen sin saber de dónde vino."""
    hijos = [x[f'child_post_{i}'] for i in range(1, 11) if isinstance(x.get(f'child_post_{i}'), dict)]
    ts = x.get('timestamp_datetime') or ''
    return {'shortCode': x.get('shortcode'), 'url': x.get('url'), 'timestamp': ts,
            'ownerUsername': x.get('owner_username'), 'caption': x.get('caption') or '',
            'coauthorProducers': [{'username': c.get('username')} for c in x.get('coauthors') or []],
            'displayUrl': x.get('display_url'), 'type': x.get('media_type'),
            'childPosts': [{'displayUrl': h.get('display_url')} for h in hijos],
            '_via': 'lobstr'}


def lobstr_por_cuentas(cuentas, desde_iso, clave, ahora, espera=5, intentos=60):
    """Una corrida de lobstr para estas cuentas, desde `desde_iso`. Reusa un
    solo squid (lo vacía y le pone las tareas de hoy). Cobra 1 crédito por post
    devuelto; `max_results` lo topa. Un fallo devuelve ítems de error, como Apify."""
    import time
    try:
        sq = next((q for q in _lobstr('GET', 'squids?limit=100', clave).get('data', [])
                   if q.get('name') == LOBSTR_SQUID), None)
        if not sq:
            sq = _lobstr('POST', 'squids', clave, {'crawler': LOBSTR_CRAWLER, 'name': LOBSTR_SQUID})
        horas = max(1, int((ahora - datetime.fromisoformat(desde_iso)).total_seconds() // 3600) + 1)
        _lobstr('POST', f"squids/{sq['id']}/empty", clave, {'type': 'url'})
        _lobstr('POST', f"squids/{sq['id']}", clave, {'params': {
            'hours_back': horas, 'max_results': LOBSTR_LIMITE, 'enrich_comments': False, 'skip_pinned_posts': True}})
        _lobstr('POST', 'tasks', clave, {'squid': sq['id'], 'tasks': [{'url': c} for c in cuentas]})
        run = _lobstr('POST', 'runs', clave, {'squid': sq['id']})
        for _ in range(intentos):
            time.sleep(espera)
            # GET runs/<id> no trae `is_done` (solo la lista de corridas): se mira
            # `ended_at`/`status` (2 nov: la corrida terminó en 5 s y se esperó 6 min)
            g = _lobstr('GET', f"runs/{run['id']}", clave)
            if g.get('is_done') or g.get('ended_at') or g.get('status') in ('done', 'error', 'aborted'):
                break
        else:
            raise TimeoutError('la corrida de lobstr no terminó')
        res, pag = [], 1
        while True:
            r = _lobstr('GET', f"results?squid={sq['id']}&run={run['id']}&page={pag}&page_size=100", clave)
            res += r.get('data', [])
            if not r.get('next'):
                break
            pag += 1
        return [lobstr_a_apify(x) for x in res]
    except Exception as ex:  # noqa: BLE001
        return [{'error': 'http', 'errorDescription': f'lobstr: {ex}', 'username': c} for c in cuentas]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--simular', action='store_true')
    ap.add_argument('--hoy')
    a = ap.parse_args()
    ahora = datetime.fromisoformat(a.hoy) if a.hoy else datetime.now()
    estado = json.load(open(ESTADO)) if os.path.exists(ESTADO) else {}
    cerrados = json.load(open(CERRADOS)) if os.path.exists(CERRADOS) else {}
    vig = vigilados(festivales_config(open(CONFIG).read()), json.load(open(CUENTAS)), ahora, cerrados)
    ahora_toca = [v for v in vig if toca(v, estado, ahora)]
    faltan = sin_cuenta(festivales_config(open(CONFIG).read()), json.load(open(CUENTAS)), ahora)
    cuentas = sorted({v['cuenta'] for v in ahora_toca})
    informe = {'hora': ahora.isoformat(timespec='minutes'),
               'consultadas': [f"{v['id']} @{v['cuenta']} ({v['tier']})" for v in ahora_toca],
               'saltadas_hoy_ya_vistas': [v['id'] for v in vig if v not in ahora_toca],
               'SIN_CUENTA_IG': faltan}
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
    clave_lobstr = os.environ.get('LOBSTR_API_KEY')
    saldo = apify_saldo(token)
    informe['apify_saldo_usd'] = None if saldo is None else round(saldo, 2)
    if saldo is not None and saldo < APIFY_PISO_USD and clave_lobstr:
        # sin saldo en Apify: todo va por lobstr (no se gasta lo que queda)
        informe['via'] = 'lobstr (Apify bajo el piso)'
        items = lobstr_por_cuentas(cuentas, d, clave_lobstr, ahora)
    else:
        informe['via'] = 'apify'
        items = apify_por_cuenta(cuentas, estado, ahora, token)
    nuevos, sin_leer = clasificar(items, cuentas, estado)
    # Reintento: Apify devuelve «Empty or private data» por rachas; una cuenta
    # sola, en una segunda llamada, suele pasar.
    reintentar = [c for c in sin_leer if c != '*']
    if reintentar:
        # el reintento va por lobstr si hay clave (2 nov): si Apify falló por
        # HTTP, pedirle otra vez lo mismo suele fallar igual
        otra = (lambda cs: lobstr_por_cuentas(cs, desde(cs, estado, ahora), clave_lobstr, ahora)) if clave_lobstr \
            else (lambda cs: apify_por_cuenta(cs, estado, ahora, token))
        n2, s2 = clasificar(otra(reintentar), reintentar, estado)
        for c in reintentar:
            if c not in s2:
                nuevos[c] = n2[c]
                del sin_leer[c]
    os.makedirs(SALIDA, exist_ok=True)
    informe['nuevos'] = []
    informe['ALERTA_FALLOS_SEGUIDOS'] = {}
    for c in cuentas:
        e = estado.setdefault(c, {})
        if c in sin_leer or '*' in sin_leer:
            # NO se marca consultada: la próxima corrida vuelve a pedir desde
            # la última lectura buena y no se pierde lo publicado en el hueco.
            e['fallos'] = e.get('fallos', 0) + 1
            if e['fallos'] >= 3:
                informe['ALERTA_FALLOS_SEGUIDOS'][c] = e['fallos']
            continue
        e['fallos'] = 0
        e['consultado'] = ahora.isoformat(timespec='seconds')
        for it in sorted(nuevos[c], key=lambda x: x.get('timestamp', '')):
            ts = it['timestamp'].replace('Z', '').split('.')[0]
            json.dump(it, open(os.path.join(SALIDA, f"{it['shortCode']}.json"), 'w'), ensure_ascii=False)
            e['ultimo_post'] = max(e.get('ultimo_post', ''), ts)
            informe['nuevos'].append({'cuenta': c, 'fecha': ts, 'post': f"https://www.instagram.com/p/{it['shortCode']}/",
                                      'laminas': len(it.get('childPosts') or it.get('images') or []) or 1,
                                      'texto': (it.get('caption') or '')[:300]})
    informe['NO_PUDE_LEER'] = sin_leer
    vigilar_fb(json.load(open(CUENTAS)), estado, ahora, token, informe)
    os.makedirs(os.path.dirname(ESTADO), exist_ok=True)
    json.dump(estado, open(ESTADO, 'w'), ensure_ascii=False, indent=1)
    print(json.dumps(informe, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
