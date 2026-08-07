#!/usr/bin/env python3
# ── tmdb-precheck.py — ¿esta obra YA existe en TMDB? ─────────────────────────
#
# Se corre ANTES de abrir un alta. Crear un duplicado en una base pública es el
# error más caro del pipeline: ensucia TMDB, ensucia Letterboxd y solo se limpia
# con un reporte manual que otro humano tiene que moderar.
#
# ── POR QUÉ EXISTE (lección del 27 jul 2026) ─────────────────────────────────
# Creé «In four stops» (1738831) sin ver que ya estaba como «Четыре остановки»
# (1645816): misma directora, 19 min, Rusia, 2026. Dos guardas habían fallado:
#
#   1. La búsqueda por TÍTULO no la vio porque TMDB la tiene en cirílico y el
#      festival la lista con su título internacional. Buscar el título que uno
#      conoce nunca alcanza: hay que buscar por PERSONA, que es language-neutral.
#   2. La búsqueda por DIRECTORA sí la habría visto — el crédito estaba ahí —
#      pero mi chequeo capturaba las excepciones de red y devolvía {} en
#      silencio, así que un fallo de API se veía EXACTO IGUAL que un "no existe".
#
# De ahí las dos reglas de este script:
#   · buscar por título Y por créditos de cada director (no solo por título);
#   · **fallar ruidosamente**: si una llamada revienta, sale con código 3 y lo
#     dice. Silencio nunca significa "verificado".
#
# Uso:
#   python3 scripts/tmdb-precheck.py festivals/staging/ficdeh-2026.json
#   python3 scripts/tmdb-precheck.py <festival.json> --title "Solo esta"
#
# Códigos de salida: 0 = ninguna existe · 2 = hay candidatas · 3 = chequeo roto

import json, os, sys, re, time, subprocess, urllib.parse

KEY = os.environ.get('TMDB_API_KEY')
API = 'https://api.themoviedb.org/3/'
FALLOS = []          # errores de red/API: se reportan, NO se silencian
AÑO_TOL = 3          # holgura de año para dar por candidata una coincidencia


def api(path, **q):
    """Llamada a TMDB. Un fallo se ANOTA y se propaga — nunca se convierte en
    un resultado vacío, que sería indistinguible de 'no existe'.

    Va por `curl` y no por urllib a propósito: el Python de este Mac no trae
    bundle de CA, así que urllib revienta con CERTIFICATE_VERIFY_FAILED en cada
    llamada. Ese fue el fallo que dejó pasar el duplicado de «In four stops» —
    con captura silenciosa de excepciones, 51 llamadas rotas se veían como
    51 películas inexistentes."""
    q['api_key'] = KEY
    url = API + path + '?' + urllib.parse.urlencode(q)
    for intento in range(3):
        try:
            r = subprocess.run(['curl', '-sS', '--fail', '--max-time', '25', url],
                               capture_output=True, text=True)
            if r.returncode == 0:
                return json.loads(r.stdout)
            err = (r.stderr or f'curl exit {r.returncode}').strip()
        except Exception as e:
            err = str(e)
        if intento == 2:
            FALLOS.append(f'{path} :: {err}')
            return None
        time.sleep(1.5 * (intento + 1))


def norm(s):
    return ''.join(c for c in (s or '').lower() if c.isalnum())


def año(x):
    m = re.match(r'(\d{4})', (x or ''))
    return int(m.group(1)) if m else 0


def por_titulo(f):
    """Coincidencia exacta de título (o título original) con año compatible."""
    hits = []
    yr = año(str(f.get('year') or ''))
    for q in filter(None, [f.get('title'), f.get('title_en')]):
        for media in ('movie', 'tv'):
            r = api(f'search/{media}', query=q)
            if r is None:
                continue
            for x in r.get('results', [])[:8]:
                nm = x.get('title') or x.get('name')
                ori = x.get('original_title') or x.get('original_name')
                dt = año(x.get('release_date') or x.get('first_air_date'))
                if norm(nm) == norm(q) or norm(ori) == norm(q):
                    if not yr or not dt or abs(dt - yr) <= AÑO_TOL:
                        hits.append((media, x['id'], nm, ori, dt, 'título'))
    return hits


def por_director(f):
    """La red que atrapa los títulos en otro alfabeto: los créditos de la
    persona son independientes del idioma del título."""
    hits = []
    yr = año(str(f.get('year') or ''))
    dirs = [d.strip() for d in re.split(r',| y ', f.get('director') or '') if d.strip()]
    for nombre in dirs[:3]:
        r = api('search/person', query=nombre)
        if r is None:
            continue
        for p in r.get('results', [])[:2]:
            if norm(p['name']) != norm(nombre):
                continue
            cr = api(f"person/{p['id']}/movie_credits")
            if cr is None:
                continue
            for c in cr.get('crew', []):
                if c.get('job') != 'Director':
                    continue
                dt = año(c.get('release_date'))
                if not yr or not dt or abs(dt - yr) <= AÑO_TOL:
                    hits.append(('movie', c['id'], c.get('title'), c.get('original_title'), dt,
                                 f'director «{p["name"]}»'))
    return hits


def main():
    if not KEY:
        print('✗ falta $TMDB_API_KEY'); sys.exit(3)
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    solo = None
    if '--title' in sys.argv:
        solo = sys.argv[sys.argv.index('--title') + 1]
        args = [a for a in args if a != solo]
    if not args:
        print(__doc__ or 'Uso: tmdb-precheck.py <festival.json> [--title "X"]'); sys.exit(3)

    d = json.load(open(args[0], encoding='utf-8'))
    films = [f for f in d.get('films', []) if not f.get('lbSlug')]
    if solo:
        films = [f for f in films if f.get('title') == solo]

    candidatas = 0
    print(f'\n═══ precheck TMDB — {len(films)} obra(s) sin ficha ═══\n')
    for f in films:
        hits = {h[:2]: h for h in (por_titulo(f) + por_director(f))}.values()
        if hits:
            candidatas += 1
            print(f'⚠️  {f["title"]} ({f.get("year")}) — {f.get("director")}')
            for m, i, nm, ori, dt, via in hits:
                print(f'      ya existiría → {m} {i} · {nm} · orig «{ori}» · {dt}   [vía {via}]')
        else:
            print(f'·   {f["title"]}')
        time.sleep(0.12)

    if FALLOS:
        print(f'\n✗ EL CHEQUEO ESTÁ ROTO — {len(FALLOS)} llamada(s) fallaron; el resultado NO es confiable:')
        for x in FALLOS[:10]:
            print('   ', x)
        sys.exit(3)

    print(f'\n{candidatas} candidata(s) a duplicado de {len(films)}')
    sys.exit(2 if candidatas else 0)


if __name__ == '__main__':
    main()
