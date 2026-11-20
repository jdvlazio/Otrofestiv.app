#!/usr/bin/env python3
"""alta-festival.py — deja lista la APP para un festival nuevo, desde su plan.

POR QUÉ EXISTE (20 nov 2026, lección del Under). Los datos de un festival salen
del pipeline, pero lo que la app necesita para mostrarlo se hacía a mano en seis
lugares, y cada uno aparecía recién cuando un guardián frenaba al final: la
entrada de FESTIVAL_CONFIG, el inglés y el arquetipo de cada sección, el ancla
del radar, las huellas y las fechas del afiche de portada, y CLAUDE.md.

QUÉ HACE, con el plan (`pipeline/<id>.plan.json`) como única fuente:
  1. FESTIVAL_CONFIG (src/config.js): la entrada del festival. Los días, sus
     rótulos y las fechas se DERIVAN de festivalStartStr/festivalEndStr; lo
     editorial (nombre, subtítulo, sigla) se COPIA del plan, nunca se inventa.
  2. SECTION_EN y SECTION_ARCHETYPES: cada sección del JSON publicado, con el
     `en` y el `archetype` que el plan declara en `festival.secciones`.
  3. docs/radar-ancla.json: el festival pasa a `en_app` con su id (si ya estaba
     en el radar por su issue o su nombre, se actualiza esa entrada).
  4. scripts/keyart-huellas.py, scripts/keyart-fechas.py y
     scripts/generate-claude-md.js: las tablas generadas que leen los guardianes.

QUÉ NO HACE. No decide nada editorial. Si al plan le falta el subtítulo, el
inglés de una sección o el afiche de portada, no escribe esa pieza: la lista
como PENDIENTE (el copy se aprueba con Juan). Correrlo dos veces no cambia
nada la segunda: solo agrega lo que falta.

    python3 pipeline/alta-festival.py <id>            # p. ej. under-2026
    python3 pipeline/alta-festival.py <id> --ver      # muestra lo que haría; no escribe
    python3 pipeline/alta-festival.py <id> --ensayo   # y además todos los guardianes de la
                                                      # publicación, con la lista de lo que falta
"""
import datetime, json, os, re, subprocess, sys, unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(REPO, 'src', 'config.js')
ANCLA = os.path.join(REPO, 'docs', 'radar-ancla.json')

DIAS_ES = ['LUN', 'MAR', 'MIÉ', 'JUE', 'VIE', 'SÁB', 'DOM']          # date.weekday(): lunes = 0
DIAS_EN = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
DIAS_LARGO = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto',
         'septiembre', 'octubre', 'noviembre', 'diciembre']
EDITORIALES = ('name', 'fullName', 'shortName', 'tagline', 'city', 'country', 'dates', 'dates_en')
DERIVABLES = ('festivalStartStr', 'festivalEndStr', 'timezoneOffset')


def id_app(fid):
    """El id de la app: el archivo sin el guion antes del año (under-2026 → under2026)."""
    return re.sub(r'-(\d+)$', r'\1', fid)


def _n(s):
    s = unicodedata.normalize('NFD', str(s or '')).lower()
    return ''.join(c for c in s if c.isalnum())


def _js(v):
    """Un valor de JS con comillas simples, como el resto de config.js."""
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, list):
        return '[' + ','.join(_js(x) for x in v) + ']'
    return "'" + str(v).replace('\\', '\\\\').replace("'", "\\'") + "'"


def dias(inicio, fin):
    a = datetime.date.fromisoformat(inicio[:10])
    b = datetime.date.fromisoformat(fin[:10])
    out = []
    while a <= b:
        out.append(a)
        a += datetime.timedelta(days=1)
    return out


def entrada_config(fid, f):
    """El bloque de FESTIVAL_CONFIG, en el formato de las entradas a mano."""
    i = id_app(fid)
    ds = dias(f['festivalStartStr'], f['festivalEndStr'])
    k = [d.isoformat() for d in ds]
    fin = f['festivalEndStr'] if len(f['festivalEndStr']) > 10 else f['festivalEndStr'] + 'T23:00:00'
    lineas = [
        f"  '{i}': {{",
        f"    // Alta con pipeline/alta-festival.py ({datetime.date.today().isoformat()}): lo editorial sale de",
        f"    // pipeline/{fid}.plan.json; los días, de festivalStartStr/festivalEndStr.",
        '    ' + ','.join(f'{c}:{_js(f[c])}' for c in ('name', 'displayName', 'fullName', 'shortName') if f.get(c)) + ',',
        f"    city:{_js(f['city'])},country:{_js(f['country'])},",
        f"    dates:{_js(f['dates'])},dates_en:{_js(f['dates_en'])},year:{int(f.get('year') or ds[0].year)},"
        f"timezoneOffset:{_js(f['timezoneOffset'])},",
        f"    keyArt:'/assets/keyart/{i}.jpg',",
        f"    tagline:{_js(f['tagline'])},",
        ('    ' + (f"instagram:{_js(f['instagram'])}, " if f.get('instagram') else '')
         + f"storageKey:{_js(f.get('storageKey') or i + '_')},"
         f"festivalStartStr:{_js(f['festivalStartStr'])},festivalEndStr:{_js(fin)},"),
        '    festivalDates:{' + ','.join(f"'{x}':'{x}'" for x in k) + '},',
        '    days:[' + ','.join(f"{{k:'{d.isoformat()}',d:{d.day},lbl:'{DIAS_ES[d.weekday()]}'}}" for d in ds) + '],',
        '    dayKeys:[' + ','.join(f"'{x}'" for x in k) + '],',
        '    dayShort:{' + ','.join(f"'{d.isoformat()}':'{DIAS_ES[d.weekday()]} {d.day}'" for d in ds) + '},',
        '    dayShort_en:{' + ','.join(f"'{d.isoformat()}':'{DIAS_EN[d.weekday()]} {d.day}'" for d in ds) + '},',
        '    dayLong:{' + ','.join(f"'{d.isoformat()}':'{DIAS_LARGO[d.weekday()]} {d.day} de {MESES[d.month - 1]}'" for d in ds) + '},',
        f"    prioLimit:{int(f.get('prioLimit') or 5)},eventPosterLabel:{_js(f.get('eventPosterLabel') or ['EVENTO', ''])},",
        '    films:null,posters:null,lbSlugs:{}',
        '  },',
    ]
    return '\n'.join(lineas) + '\n'


def _bloque(src, nombre):
    """(inicio, fin) del cuerpo de `export const <nombre> = {` … `};` en config.js."""
    m = re.search(r'^export const ' + nombre + r'\s*=\s*\{\n', src, re.M)
    if not m:
        raise SystemExit(f'✗ no encontré {nombre} en src/config.js')
    fin = src.index('\n};', m.end())
    return m.end(), fin


def secciones(fid, f, src):
    """Lo que falta de SECTION_EN y SECTION_ARCHETYPES → (líneas_en, líneas_arq, pendientes)."""
    p = os.path.join(REPO, 'festivals', f'{fid}.json')
    if not os.path.exists(p):
        return [], [], [f'festivals/{fid}.json todavía no existe: correr el pipeline antes (las secciones salen de ahí)']
    etiquetas = list((json.load(open(p, encoding='utf-8')).get('sections') or {}).keys())
    plan = {_n(k): v for k, v in (f.get('secciones') or {}).items()}
    a_en, f_en = _bloque(src, 'SECTION_EN')
    a_ar, f_ar = _bloque(src, 'SECTION_ARCHETYPES')
    cuerpo_en, cuerpo_ar = src[a_en:f_en], src[a_ar:f_ar]
    en, ar, pend = [], [], []
    for et in etiquetas:
        llave = "'" + et.replace("'", "\\'") + "'"
        # la etiqueta del JSON lleva el emoji delante; el plan, el nombre a secas
        decl = plan.get(_n(re.sub(r'^\W+\s*', '', et))) or plan.get(_n(et)) or {}
        if llave + ':' not in cuerpo_en:
            if decl.get('en'):
                en.append(f'  {llave}: {_js(decl["en"])},')
            else:
                pend.append(f'sección «{et}» sin inglés: "en" en festival.secciones del plan')
        if llave + ':' not in cuerpo_ar:
            if decl.get('archetype'):
                ar.append(f'  {llave}: {_js(decl["archetype"])},')
            else:
                pend.append(f'sección «{et}» sin arquetipo: "archetype" en festival.secciones del plan')
    return en, ar, pend


def ancla(fid, f, plan):
    """La entrada del radar: (lista_nueva, qué_cambió) o (None, motivo)."""
    d = json.load(open(ANCLA, encoding='utf-8'))
    i = id_app(fid)
    fs = d['festivales']
    if any(i in (e.get('id_config') or []) for e in fs):
        return None, 'ya está'
    issue = plan.get('radar') or (plan.get('festival') or {}).get('radar')
    e = next((e for e in fs if issue and issue in (e.get('issue') or [])), None) \
        or next((e for e in fs if _n(e.get('nombre', '')).startswith(_n(f['name']))), None)
    if e is not None:
        e['estado'], e['id_config'] = 'en_app', sorted(set((e.get('id_config') or []) + [i]))
        return d, f'actualizada «{e["clave"]}» → en_app'
    base = {k: None for k in fs[0].keys()} if fs else {}
    clave = re.sub(r'[^a-z0-9]+', '-', unicodedata.normalize('NFD', f['name']).encode('ascii', 'ignore').decode().lower()).strip('-')
    ig = f.get('instagram')
    base.update({
        'clave': clave,
        'nombre': f['name'] + (f' — {f["tagline"]}' if f.get('tagline') and _n(f['tagline']) != _n(f['name']) else ''),
        'ciudad': f.get('city'), 'mes': datetime.date.fromisoformat(f['festivalStartStr'][:10]).month,
        'fechas_2026': f.get('dates'), 'ig': f'@{ig}' if ig else None,
        'estado': 'en_app', 'id_config': [i], 'issue': [issue] if issue else [],
        'fuente': [f'https://www.instagram.com/{ig}/'] if ig else [],
    })
    fs.append(base)
    return d, f'nueva entrada «{clave}»'


def alta(fid, escribir=True):
    pp = os.path.join(REPO, 'pipeline', f'{fid}.plan.json')
    if not os.path.exists(pp):
        raise SystemExit(f'✗ no existe pipeline/{fid}.plan.json')
    plan = json.load(open(pp, encoding='utf-8'))
    f = plan.get('festival') or {}
    i = id_app(fid)
    hecho, pend = [], []

    faltan = [c for c in EDITORIALES + DERIVABLES if not str(f.get(c) or '').strip()]
    if faltan:
        pend.append('al plan le falta en "festival": ' + ', '.join(faltan)
                    + ' (lo editorial se decide con Juan; nada se inventa)')
    avisos = []
    if not f.get('instagram'):
        # no frena: la app funciona sin él, pero el vigía de IG lo usa para seguir
        # los cambios de programación
        avisos.append('el plan no trae "instagram": sin él, el vigía no sigue sus cambios')
    if not os.path.exists(os.path.join(REPO, 'assets', 'keyart', f'{i}.jpg')):
        pend.append(f'falta el afiche de portada: assets/keyart/{i}.jpg')

    src = open(CONFIG, encoding='utf-8').read()
    # 1. FESTIVAL_CONFIG
    if re.search(r"^\s{2}'" + re.escape(i) + r"'\s*:", src, re.M):
        hecho.append(f'FESTIVAL_CONFIG: {i} ya está')
    elif faltan:
        pend.append(f'FESTIVAL_CONFIG: no se escribe {i} hasta completar el plan')
    else:
        a, _ = _bloque(src, 'FESTIVAL_CONFIG')
        src = src[:a] + entrada_config(fid, f) + src[a:]
        hecho.append(f'FESTIVAL_CONFIG: {i} agregado')
    # 2. secciones
    en, ar, p_sec = secciones(fid, f, src)
    pend += p_sec
    nota = f"  // {f.get('name') or i} ({datetime.date.today().isoformat()}, alta-festival.py): del plan\n"
    if en:
        a, _ = _bloque(src, 'SECTION_EN')
        src = src[:a] + nota + '\n'.join(en) + '\n' + src[a:]
        hecho.append(f'SECTION_EN: {len(en)} sección(es)')
    if ar:
        a, _ = _bloque(src, 'SECTION_ARCHETYPES')
        src = src[:a] + nota + '\n'.join(ar) + '\n' + src[a:]
        hecho.append(f'SECTION_ARCHETYPES: {len(ar)} sección(es)')
    if not en and not ar and not p_sec:
        hecho.append('secciones: todas con inglés y arquetipo')
    cambio_config = src != open(CONFIG, encoding='utf-8').read()
    # 3. radar
    nuevo_ancla, que = (None, 'sin plan completo') if faltan else ancla(fid, f, plan)
    hecho.append(f'radar-ancla: {que}')

    if escribir:
        if cambio_config:
            open(CONFIG, 'w', encoding='utf-8').write(src)
        if nuevo_ancla is not None:
            json.dump(nuevo_ancla, open(ANCLA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
            open(ANCLA, 'a', encoding='utf-8').write('\n')
        # 4. las tablas generadas que leen los guardianes (solo con config y afiche)
        if not faltan and os.path.exists(os.path.join(REPO, 'assets', 'keyart', f'{i}.jpg')):
            for nombre, cmd in (('huellas del afiche', ['python3', 'scripts/keyart-huellas.py']),
                                ('fechas del afiche', ['python3', 'scripts/keyart-fechas.py']),
                                ('CLAUDE.md', ['node', 'scripts/generate-claude-md.js'])):
                r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=600)
                if r.returncode == 0:
                    hecho.append(f'{nombre}: regenerado')
                else:
                    pend.append(f'{nombre}: {" ".join(cmd)} falló — {(r.stderr or r.stdout).strip()[-160:]}')
    return hecho, pend, avisos


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if len(args) != 1:
        sys.exit(__doc__)
    fid = args[0]
    hecho, pend, avisos = alta(fid, escribir='--ver' not in sys.argv)
    print(f'ALTA de {fid}' + (' (--ver: no se escribe nada)' if '--ver' in sys.argv else ''))
    for x in hecho:
        print('  ✓', x)
    for x in avisos:
        print('  ⚠', x)
    for x in pend:
        print('  ✗', x)
    if '--ensayo' in sys.argv:
        print()
        r = subprocess.run(['python3', 'pipeline/publicar-datos.py', fid, '--ensayo'], cwd=REPO)
        sys.exit(1 if (pend or r.returncode) else 0)
    sys.exit(1 if pend else 0)
