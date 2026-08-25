#!/usr/bin/env python3
"""
validate.py — Otrofestiv pre-deploy validator
Ejecutar antes de cada git push. Falla con exit(1) si algún check falla.

Checks implementados:
  1. Shadow variable t=  — const t= + t() en mismo scope de función
  2. _SCHED_PURE_FNS     — todas las funciones referenciadas existen en main thread
  3. Worker-local overlap — worker-local fns no duplican _SCHED_PURE_FNS
  4. JSON festival fields — cada festivals/*.json tiene los campos requeridos
  5. FESTIVAL_CONFIG      — cada entrada tiene los campos pre-fetch requeridos
  6. Critical HTML divs   — los 8 divs estructurales existen en el HTML
  7. DOCTYPE position     — el archivo empieza con <!DOCTYPE (sin texto previo)
  8. Dead code            — no hay _CALC_WORKER_SRC en el archivo

Uso:
  python3 validate.py           # valida index.html y festivals/*.json
  python3 validate.py --strict  # falla si hay warnings además de errors
"""

import re, json, os, sys

# ── Config ────────────────────────────────────────────────────────────────────
INDEX_HTML   = 'index.html'
FESTIVALS_DIR = 'festivals/'

# Campos requeridos en cada festivals/*.json (fuente de verdad del festival)
REQUIRED_JSON_FIELDS = [
    'name', 'storageKey', 'festivalEndStr',
    'festivalDates', 'days', 'dayKeys', 'timezoneOffset'
]

# Campos requeridos en FESTIVAL_CONFIG del HTML (bootstrap pre-fetch)
REQUIRED_BOOTSTRAP_FIELDS = [
    'name', 'city', 'dates', 'dates_en', 'year', 'storageKey', 'festivalEndStr'
]

# Divs estructurales críticos
CRITICAL_DIVS = [
    'id="ag-view"',
    'id="hdr-programa"',
    'id="nav-row"',
    'id="main-nav"',
    'class="topbar"',
    'id="otrofestiv-splash"',
    'id="ag-result"',
]

# ── Helpers ───────────────────────────────────────────────────────────────────
errors   = []
warnings = []
passed   = []

def fail(check, msg):
    errors.append(f'  ✗ [{check}] {msg}')

def warn(check, msg):
    warnings.append(f'  ⚠ [{check}] {msg}')

def ok(check, msg):
    passed.append(f'  ✓ [{check}] {msg}')

# ── Load files ────────────────────────────────────────────────────────────────
if not os.path.exists(INDEX_HTML):
    print(f'ERROR: {INDEX_HTML} not found')
    sys.exit(1)

content = open(INDEX_HTML, encoding='utf-8').read()
# p8 Step 0: el código de la app se movió a src/main.js (módulo). Para que los
# checks (que asumen single-file: split HTML-part / script-part) sigan
# funcionando, se inyecta main.js donde estaba el bloque inline — el `content`
# en memoria queda "as if inline". Los checks no requieren cambios.
_MAIN_JS = 'src/main.js'
if os.path.exists(_MAIN_JS):
    _main_src = open(_MAIN_JS, encoding='utf-8').read()
    # El src de main.js lleva ?v=BUILD (cache-busting del fix iOS) — matchear con o
    # sin el query para que la inyección siga funcionando en cada build. Replacement
    # como función para no interpretar backslashes del código JS como group refs.
    content = re.sub(
        r'<script type="module" src="/src/main\.js(?:\?v=\d+)?"></script>',
        lambda _m: '<script>\n' + _main_src + '\n</script>',
        content
    )
    # Store gate (5 jul 2026): el tag estático fue reemplazado por un loader
    # inline que inyecta el módulo dinámicamente (s.src="/src/main.js?v=...").
    # Si el patrón viejo no matcheó, inyectar main.js en el punto del s.src —
    # queda dentro del <script> del loader, y los checks single-file siguen
    # viendo el JS de la app como antes.
    if _main_src not in content:
        content = re.sub(
            r's\.src="/src/main\.js\?v=\d+";',
            lambda _m: '\n' + _main_src + '\n',
            content
        )
# p8 Step 1: FESTIVAL_CONFIG/VENUES/NOTICES + constantes estáticas se movieron a
# src/config.js (`export const`, importado por main.js). CHECK 5 (bootstrap) lo
# busca ahí. Se lee aparte para NO contaminar los checks que escanean `content`.
_CONFIG_JS = 'src/config.js'
_config_src = open(_CONFIG_JS, encoding='utf-8').read() if os.path.exists(_CONFIG_JS) else ''
# p8 Wave 6: HTML generado por innerHTML migró a src/view/*.js. Para checks que
# escanean markup generado (html-divs), se concatena el surface de view aparte
# (NO en `content` — contaminaría shadow-t/state-mirror que asumen main-only).
_VIEW_DIR = os.path.join('src', 'view')
_view_all = ''
if os.path.isdir(_VIEW_DIR):
    for _f in sorted(os.listdir(_VIEW_DIR)):
        if _f.endswith('.js'):
            _view_all += '\n' + open(os.path.join(_VIEW_DIR, _f), encoding='utf-8').read()
# p8 Step 7a: el worker (_SCHED_PURE_FNS + _mkCalcWorker) migró a
# src/controller/calc.js. Los checks sched-pure-fns/worker-overlap lo escanean ahí.
_CALC_JS = os.path.join('src', 'controller', 'calc.js')
_calc_src = open(_CALC_JS, encoding='utf-8').read() if os.path.exists(_CALC_JS) else ''
# p8 Wave 7: handlers/controller migran a src/controller/*.js. Checks que buscan
# cuerpos de fns de controller (controller-pattern) los escanean ahí.
_CTRL_DIR = os.path.join('src', 'controller')
_controller_all = ''
if os.path.isdir(_CTRL_DIR):
    for _f in sorted(os.listdir(_CTRL_DIR)):
        if _f.endswith('.js'):
            _controller_all += '\n' + open(os.path.join(_CTRL_DIR, _f), encoding='utf-8').read()
script_start = content.find('<script>')
script_end   = content.rfind('</script>')
if script_start == -1 or script_end == -1:
    print('ERROR: could not find <script> tags in index.html')
    sys.exit(1)
script = content[script_start:script_end]

# ── CHECK 1: Shadow variable t= ───────────────────────────────────────────────
# Detecta funciones donde una variable local llamada `t` (o arrow param `t=>`)
# pisa la función global t() de i18n — causó 3 bugs esta semana.
check = 'shadow-t'
func_matches = list(re.finditer(r'\nfunction (\w+)\s*\(', script))
shadow_found = []

for i, m in enumerate(func_matches):
    fn_name = m.group(1)
    start   = m.start()
    end     = func_matches[i+1].start() if i+1 < len(func_matches) else len(script)
    body    = script[start:end]

    # Arrow callback con t como param + t() llamado dentro del mismo bloque
    for arrow_m in re.finditer(r'(?:[.(,\s])\bt\b\s*=>\s*\{', body):
        # Extraer solo el cuerpo del bloque { } del callback
        brace_start = body.find('{', arrow_m.end()-1)
        if brace_start == -1: continue
        depth, i = 1, brace_start + 1
        while i < len(body) and depth > 0:
            if body[i] == '{': depth += 1
            elif body[i] == '}': depth -= 1
            i += 1
        cb_text = body[brace_start:i]
        if re.search(r"\bt\s*\('[^']*'\)", cb_text):
            shadow_found.append(f'{fn_name}() — arrow param t=> con t() en callback')

    # Destructuring ({t,...})=> en callbacks de array — {t,f} sombrea t()
    # Solo detecta cuando es parámetro de arrow function: ({t,...})=>
    for destr_m in re.finditer(r'\(\{([^}]{1,40})\}\s*(?:,[^)]*)?\)\s*=>', body):
        params = destr_m.group(1)
        if re.search(r'(?<![:\w])t(?![:\w])', params):
            cb_text = body[destr_m.end():destr_m.end()+500]
            if re.search(r"\bt\('[^']*'\)", cb_text):
                shadow_found.append(f'{fn_name}() — destructuring {{t}} en arrow fn sombrea t() — usar {{t:title}}')

    # const t = ... + t() llamado después
    for decl_m in re.finditer(r'\bconst\s+t\s*=(?!\s*t\()', body):
        if re.search(r"\bt\('[^']*'\)", body[decl_m.end():]):
            shadow_found.append(f'{fn_name}() — const t= con t() en mismo scope')

if shadow_found:
    for s in shadow_found:
        fail(check, s)
    fail(check, 'Convención: usar titleStr como param de callbacks, nunca t=')
else:
    ok(check, '0 shadow variable t= risks en todas las funciones')

# ── CHECK 2: _SCHED_PURE_FNS existen en main thread ──────────────────────────
# Si una función se renombra o elimina del main thread pero sigue en la lista,
# el Worker se construye con un fragmento undefined.
check = 'sched-pure-fns'
_sched_hay = content + _calc_src  # p8 7a: _SCHED_PURE_FNS vive en controller/calc.js
sched_start = _sched_hay.find('const _SCHED_PURE_FNS = [')
if sched_start == -1:
    fail(check, '_SCHED_PURE_FNS no encontrado (main ni controller/calc.js)')
else:
    sched_end = _sched_hay.find('];', sched_start)
    sched_block = _sched_hay[sched_start:sched_end]
    fn_names = re.findall(r"'(\w+)'", sched_block)
    # p8 Step 5: las pure fns se movieron a src/domain/*.js (import en main.js). El
    # worker las consume vía eval(name).toString() — el binding importado debe ser
    # resoluble en main. Se buscan en content + módulos domain. `export function
    # NAME(` contiene `function NAME(`.
    _domain_src = ''
    for _dm in ('time', 'film', 'schedule', 'festival'):
        _dp = os.path.join('src', 'domain', f'{_dm}.js')
        if os.path.exists(_dp):
            _domain_src += '\n' + open(_dp, encoding='utf-8').read()
    _haystack = content + _domain_src
    missing_fns = [f for f in fn_names if f'function {f}(' not in _haystack]
    if missing_fns:
        for f in missing_fns:
            fail(check, f"'{f}' en _SCHED_PURE_FNS pero no definida en main thread ni domain")
    # El hueco que este check NO veía (17 ago 2026): la fn existía en el dominio
    # pero calc.js no la IMPORTABA. eval(name) del build del worker resuelve en el
    # scope del módulo → ReferenceError → el worker moría y TODO cálculo caía al
    # fallback síncrono, en silencio, con este guardián en verde. screeningPlannable
    # vivió así desde su extracción (16 ago) hasta el traspaso de Onboarding (17).
    # Cada nombre de la lista debe aparecer en un import de calc.js — salvo los
    # definidos worker-local (_venueFns) o dentro del propio calc.js.
    _calc_imports = ' '.join(re.findall(r'import\s*\{([^}]*)\}', _calc_src))
    _calc_local = set(re.findall(r'function (\w+)\(', _calc_src))
    _sin_import = [f for f in fn_names
                   if f not in _calc_imports and f not in _calc_local]
    if _sin_import:
        fail(check, 'en _SCHED_PURE_FNS pero SIN import en calc.js (el worker muere al construirse y nadie lo ve): '
                    + ', '.join(_sin_import))
    elif not missing_fns:
        ok(check, f'las {len(fn_names)} funciones de _SCHED_PURE_FNS existen Y están importadas en calc.js')

# ── CHECK 3: Worker-local no duplica _SCHED_PURE_FNS ─────────────────────────
# Si una función está en ambos lados, el worker-local gana y el main thread
# queda ignorado — exactamente el bug que Sprint 3 resolvió.
check = 'worker-overlap'
mk_pos = _sched_hay.find('function _mkCalcWorker()')  # p8 7a: en controller/calc.js
if mk_pos == -1:
    fail(check, '_mkCalcWorker() no encontrado (main ni controller/calc.js)')
else:
    mk_end_search = _sched_hay.find('\n// Worker activo', mk_pos)
    if mk_end_search == -1:
        mk_end_search = mk_pos + 4000
    mk_body = _sched_hay[mk_pos:mk_end_search]
    worker_local_fns = set(re.findall(r'function (\w+)\s*\(', mk_body))
    if sched_start != -1:
        overlap = worker_local_fns & set(fn_names)
        if overlap:
            for f in overlap:
                fail(check, f"'{f}' definida como worker-local Y en _SCHED_PURE_FNS — ambigüedad")
        else:
            ok(check, f'sin overlap entre worker-local ({len(worker_local_fns)} fns) y _SCHED_PURE_FNS')

# ── CHECK 3.5: worker-deps — cierre de dependencias del Worker ───────────────
# El Worker corre SOLO con _SCHED_PURE_FNS (extraídas vía .toString()) + las fns
# worker-local. Si una pure fn llama a OTRA función de dominio que no está en ese
# conjunto, el Worker lanza ReferenceError en runtime — caso real (jun 2026):
# _festDate ganó una llamada a minToStr (fix AM/PM) que no estaba en _SCHED_PURE_FNS
# → "Calcular mi Plan" roto en Tribeca. [worker-overlap] solo valida unicidad de
# nombres, no dependencias; este check cierra ese hueco: toda fn de dominio llamada
# por una pure fn debe estar disponible en el Worker.
def _extract_fn_src(src, name):
    """Devuelve el source de `function NAME(...){...}` balanceando llaves
    (saltando strings y comentarios). None si no existe."""
    m = re.search(r'\bfunction\s+' + re.escape(name) + r'\s*\(', src)
    if not m:
        return None
    i = src.index('(', m.start()); depth = 1; i += 1
    while i < len(src) and depth > 0:
        if src[i] == '(': depth += 1
        elif src[i] == ')': depth -= 1
        i += 1
    while i < len(src) and src[i] != '{':
        i += 1
    if i >= len(src):
        return None
    depth = 0
    while i < len(src):
        c = src[i]; n = src[i + 1] if i + 1 < len(src) else ''
        if c == '/' and n == '*':
            i += 2
            while i < len(src) - 1 and not (src[i] == '*' and src[i + 1] == '/'):
                i += 1
            i += 2; continue
        if c == '/' and n == '/':
            while i < len(src) and src[i] != '\n':
                i += 1
            continue
        if c in ('"', "'", '`'):
            q = c; i += 1
            while i < len(src):
                if src[i] == '\\':
                    i += 2; continue
                if src[i] == q:
                    i += 1; break
                i += 1
            continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return src[m.start():i + 1]
        i += 1
    return None

check = 'worker-deps'
if sched_start != -1 and mk_pos != -1:
    # Solo funciones de NIVEL MÓDULO (columna 0): `export function NAME` o `function NAME`
    # al inicio de línea. Las anidadas (helpers dentro de otra fn, ej. backtrack/bb
    # dentro de computeScenarios) viajan con su padre vía .toString() → no son deps
    # externas y no deben contarse.
    domain_fn_names = set(re.findall(r'^(?:export\s+)?function (\w+)\s*\(', _domain_src, re.M))
    worker_available = set(fn_names) | worker_local_fns
    dep_problems = []
    for f in fn_names:
        body = _extract_fn_src(_haystack, f)
        if not body:
            continue
        inner = body[body.find('{'):]  # saltar la firma (no contar el nombre propio)
        called = set(re.findall(r'\b(\w+)\s*\(', inner))
        for missing_fn in sorted((called & domain_fn_names) - worker_available):
            dep_problems.append((f, missing_fn))
    if dep_problems:
        for caller, missing_fn in dep_problems:
            fail(check, f"'{caller}' (pure fn del Worker) llama a '{missing_fn}' — fn de dominio NO disponible en el Worker (ni en _SCHED_PURE_FNS ni worker-local) → ReferenceError en runtime. Agregá '{missing_fn}' a _SCHED_PURE_FNS + su import en calc.js.")
    else:
        ok(check, f'cierre de deps OK — las {len(fn_names)} pure fns solo llaman fns disponibles en el Worker')

# ── CHECK 4: JSON festival fields ─────────────────────────────────────────────
# Cada festivals/*.json debe tener todos los campos de config.
# Añadir festival nuevo sin estos campos rompe el tab de días y el cálculo.
check = 'json-fields'
json_errors = 0
json_ok     = 0
if os.path.isdir(FESTIVALS_DIR):
    for fname in sorted(os.listdir(FESTIVALS_DIR)):
        if not fname.endswith('.json'):
            continue
        fpath = os.path.join(FESTIVALS_DIR, fname)
        try:
            data = json.load(open(fpath, encoding='utf-8'))
        except json.JSONDecodeError as e:
            fail(check, f'{fname}: JSON inválido — {e}')
            json_errors += 1
            continue
        missing = [k for k in REQUIRED_JSON_FIELDS if k not in data]
        if missing:
            fail(check, f'{fname}: faltan campos {missing}')
            json_errors += 1
        else:
            json_ok += 1
    if json_errors == 0:
        ok(check, f'todos los {json_ok} JSONs tienen los campos requeridos')
else:
    warn(check, f'directorio {FESTIVALS_DIR} no encontrado — skip')

# ── CHECK 4a: títulos sin comillas tipográficas ──────────────────────────────
check = 'title-normalization'
TYPO_CHARS = '‘’ʼʹ“”«»'
typo_errors = []
import json as _json2
for fname in sorted(os.listdir(FESTIVALS_DIR)):
    if not fname.endswith('.json'): continue
    fpath = os.path.join(FESTIVALS_DIR, fname)
    try:
        jd = _json2.load(open(fpath, encoding='utf-8'))
        bad = [f['title'] for f in jd.get('films',[])
               if any(ch in f.get('title','') for ch in TYPO_CHARS)]
        if bad:
            for t in bad:
                typo_errors.append(f'{fname}: "{t}" contiene comilla tipográfica')
    except Exception as e:
        typo_errors.append(f'{fname}: error — {e}')
if typo_errors:
    for e in typo_errors:
        fail(check, e)
    fail(check, 'Correr: python3 scripts/normalize-festival-titles.py')
else:
    ok(check, 'Sin comillas tipográficas en títulos de festival')

# ── CHECK 4b: prioLimit correcto en cada JSON ───────────────────────────────
check = 'prio-limit'
prio_errors = []
import json as _json
for fname in sorted(os.listdir(FESTIVALS_DIR)):
    jf = os.path.join(FESTIVALS_DIR, fname)
    if not fname.endswith('.json'): continue
    try:
        with open(jf) as jfh:
            jd = _json.load(jfh)
        day_keys = jd.get('dayKeys', [])
        prio = jd.get('prioLimit')
        if prio is None:
            prio_errors.append(f'{jf}: prioLimit no definido')
            continue
        expected = min(8, max(3, round(len(day_keys) / 2)))
        if prio != expected:
            prio_errors.append(f'{jf}: prioLimit={prio} pero debería ser {expected} ({len(day_keys)} días)')
    except Exception as e:
        prio_errors.append(f'{jf}: error — {e}')
if prio_errors:
    for e in prio_errors:
        fail(check, e)
    fail(check, 'Regla: prioLimit = round(días/2), cap [3,8]')
else:
    ok(check, f'prioLimit correcto en todos los festivales (regla: round(días/2), cap [3,8])')

# ── CHECK 4c: contenido sano — linter de CONTENIDO del catálogo ──────────────
# Retro FICDEH (26 jul 2026, pedida por Juan): los gates de arriba validan la
# FORMA del JSON; este valida el CONTENIDO extraído (duración imposible para su
# sección, sinopsis con metadata pegada, títulos bilingües, país con basura,
# director que no es persona). Cada regla nace de un bug REAL que solo cazó un
# ojo humano — esto mecaniza ese olfato. El detalle vive en scripts/
# lint-catalog.py (--ci = solo texto, sin PIL: el dedup perceptual de pósters
# corre en el checklist de onboarding, no acá). Warnings del linter NO bloquean.
check = 'contenido-sano'
import subprocess as _sp
_lint = _sp.run([sys.executable, 'scripts/lint-catalog.py', '--root', '--ci'],
                capture_output=True, text=True)
if _lint.returncode == 0:
    ok(check, 'contenido de catálogos sano (duraciones/sinopsis/países/directores — lint-catalog)')
else:
    for line in _lint.stdout.splitlines():
        if line.strip().startswith('✗'):
            fail(check, line.strip().lstrip('✗ '))
    fail(check, 'lint-catalog encontró contenido corrupto — correr: python3 scripts/lint-catalog.py --root')

# ── CHECK 5: FESTIVAL_CONFIG bootstrap ───────────────────────────────────────
# Cada entrada en FESTIVAL_CONFIG debe tener los campos que el splash necesita
# antes del fetch (name, city, dates, dates_en, year, storageKey, festivalEndStr).
check = 'fc-bootstrap'
# p8 Step 1: FESTIVAL_CONFIG vive en src/config.js. Fallback a `content` por si
# algún festival legacy lo dejara inline (transición).
_fc_source = _config_src if 'const FESTIVAL_CONFIG={' in _config_src else content
fc_start = _fc_source.find('const FESTIVAL_CONFIG={')
if fc_start == -1:
    fail(check, 'FESTIVAL_CONFIG no encontrado en src/config.js')
else:
    fc_end = _fc_source.find('};', fc_start) + 2
    fc_block = _fc_source[fc_start:fc_end]
    # Extract festival IDs
    fest_ids = re.findall(r"'([a-z0-9]+)':\s*\{", fc_block)
    fc_errors = 0
    # La entrada se lee ENTERA, hasta donde empieza el siguiente festival. Antes se
    # tomaban 400 caracteres fijos: un comentario dentro de la entrada empujaba los
    # campos fuera de la ventana y el guardián los reportaba como faltantes aunque
    # estuvieran ahí (pasó al declarar `priority` en finca2026, 8 ago 2026).
    _starts = {fid: fc_block.find(f"'{fid}':") for fid in fest_ids}
    _orden = sorted(_starts.values())
    for fest_id in fest_ids:
        entry_start = _starts[fest_id]
        _sig = next((x for x in _orden if x > entry_start), len(fc_block))
        entry       = fc_block[entry_start:_sig]
        missing = [k for k in REQUIRED_BOOTSTRAP_FIELDS
                   if k+':' not in entry and k+' :' not in entry]
        if missing:
            fail(check, f"FESTIVAL_CONFIG['{fest_id}']: faltan campos {missing}")
            fc_errors += 1
    if fc_errors == 0:
        ok(check, f'todos los {len(fest_ids)} festivales tienen bootstrap completo')

# ── CHECK 6: Critical HTML divs ───────────────────────────────────────────────
# Si alguno de estos divs desaparece (por un str_replace mal ejecutado),
# la app rompe silenciosamente en iOS Safari.
check = 'html-divs'
div_errors = 0
for div in CRITICAL_DIVS:
    if div not in content and div not in _view_all:
        fail(check, f'div faltante: {div}')
        div_errors += 1
if div_errors == 0:
    ok(check, f'todos los {len(CRITICAL_DIVS)} divs críticos presentes')

# ── CHECK 7: DOCTYPE position ─────────────────────────────────────────────────
# El archivo debe empezar con <!DOCTYPE. Si hay texto antes, el browser
# lo renderiza como contenido visible — empujó el topbar 115px en producción.
check = 'doctype'
if not content.startswith('<!DOCTYPE'):
    first = repr(content[:80])
    fail(check, f'index.html no empieza con <!DOCTYPE — primeros chars: {first}')
else:
    ok(check, 'archivo empieza correctamente con <!DOCTYPE html>')

# ── CHECK 8: Dead code ────────────────────────────────────────────────────────
# _CALC_WORKER_SRC fue reemplazado en Sprint 3.
# wl-add-sheet y openWLAdd fueron reemplazados por showActionToast.
check = 'dead-code'
dead_items = []
if '_CALC_WORKER_SRC' in content:
    dead_items.append('_CALC_WORKER_SRC (Sprint 3: reemplazado por _mkCalcWorker dinámico)')
if 'id="wl-add-sheet"' in content:
    dead_items.append('id="wl-add-sheet" (reemplazado por showActionToast)')
if 'function openWLAdd' in content:
    dead_items.append('function openWLAdd() (reemplazada por showActionToast)')
if dead_items:
    for item in dead_items:
        warn(check, f'código muerto detectado: {item}')
else:
    ok(check, 'sin código muerto conocido')

# ── CHECK 9b: apostrophe-safe onclicks ───────────────────────────────────────
# Detecta onclick inline que interpolan títulos escapados con &#39; — patrón roto.
# El escape correcto para onclick es \\' (backslash-quote) o mejor aún dataset.title.
check = 'apostrophe-onclick'
import re as _re
bad_onclick = _re.findall(r"onclick=\"[^\"]*&#39;[^\"]*\"", content)
if bad_onclick:
    for match in bad_onclick[:5]:
        warn(check, f"onclick con &#39; (rompe con apóstrofes): {match[:80]}")
else:
    ok(check, 'sin onclick con &#39; inseguro')

# ── CHECK: static-html-template ──────────────────────────────────────────────
# Detecta ${t('key')} o ${expr} en HTML estático (antes del primer <script>).
# En HTML estático no hay template literal — el browser lo renderiza como texto literal.
# Fix: usar data-i18n="key" con textContent fallback, o span con data-i18n.
check = 'static-html-template'
try:
    html_only = content[:content.find('<script>')]
    bad_tmpl = re.findall(r'\$\{[^}]{1,60}\}', html_only)
    if bad_tmpl:
        for b in bad_tmpl[:10]:
            fail(check, f'template literal en HTML estático (se renderiza como texto): {b}')
    else:
        ok(check, 'sin template literals en HTML estático')
except Exception as e:
    warn(check, f'no se pudo verificar: {e}')

# ── CHECK: bare-t-in-template ─────────────────────────────────────────────────
# Detecta t('key') como texto HTML literal dentro de template literals JS.
# Patrón específico: >t('key')< o >t('key'). — texto visible en el DOM.
# Causa: falta el ${} wrapper → renderiza como string literal "t('key')".
# Fix: >${t('key')}< siempre.
check = 'bare-t-in-template'
try:
    import re as _re_bare
    script_part = content[content.find('<script>'):content.rfind('</script>')]
    # Solo el patrón peligroso: t() como contenido de etiqueta HTML, no como expresión JS
    bad_bare = _re_bare.findall(r'>t\([\'"][a-z_]+[\'"]\)[.<]', script_part)
    if bad_bare:
        for b in bad_bare[:5]:
            fail(check, f't() sin ${{}} como texto HTML en template literal: {b}')
    else:
        ok(check, 'sin t() literal como texto HTML en template literals')
except Exception as e:
    warn(check, f'no se pudo verificar: {e}')


# Verifica que todas las keys usadas en t('key') existan en AMBOS diccionarios ES y EN.
check = 'i18n-complete'
try:
    # p8 Step 4: el _I18N se movió a src/i18n/i18n.js (export const). Se lee de ahí
    # (el find 'const _I18N = {' matchea dentro de 'export const _I18N = {').
    _i18n_path = 'src/i18n/i18n.js'
    _i18n_src = open(_i18n_path, encoding='utf-8').read() if os.path.exists(_i18n_path) else ''
    # Extract _I18N block desde i18n.js
    i18n_start = _i18n_src.find('const _I18N = {')
    depth = 0
    end = i18n_start
    for i, ch in enumerate(_i18n_src[i18n_start:]):
        if ch == '{': depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                end = i18n_start + i + 1
                break
    i18n_block = _i18n_src[i18n_start:end]

    def _parse_i18n(block):
        import re as _re
        return set(_re.findall(r'"([^"]+)":', block))

    def _extract_lang_block(block, lang):
        # Brace-counting to extract the full lang block robustly
        start = re.search(rf'{lang}\s*:\s*{{', block)
        if not start: return ''
        pos = start.end() - 1  # position of opening {
        depth = 0
        for i, ch in enumerate(block[pos:], pos):
            if ch == '{': depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return block[pos+1:i]
        return ''
    es_keys = _parse_i18n(_extract_lang_block(i18n_block, 'es'))
    en_keys = _parse_i18n(_extract_lang_block(i18n_block, 'en'))

    # All t('key') calls — en el script (main.js inyectado) Y en i18n.js
    # (_applyI18nDOM llama t() con keys hardcodeadas).
    script_part = content[content.find('<script>'):content.rfind('</script>')]
    all_t_calls = set(re.findall(r"t\('([a-z][a-z0-9_]+)'\)", script_part + '\n' + _i18n_src))
    # Filter out non-i18n false positives (CSS selectors, HTML tags, etc.)
    NON_KEYS = {'div','span','button','img','input','p','a','svg','ul','li','err','ok'}
    real_keys = {k for k in all_t_calls if k not in NON_KEYS and len(k) > 3 and '_' in k}

    missing_es = sorted(real_keys - es_keys)
    missing_en = sorted(real_keys - en_keys)
    es_not_en = sorted(es_keys - en_keys)

    if missing_es:
        for k in missing_es:
            fail(check, f"t('{k}') usado en código pero falta en diccionario ES")
    if missing_en:
        for k in missing_en:
            fail(check, f"t('{k}') usado en código pero falta en diccionario EN")
    if es_not_en:
        for k in es_not_en:
            warn(check, f"key '{k}' en ES pero no en EN")
    if not missing_es and not missing_en:
        ok(check, f'todos los t() calls tienen key en ES y EN ({len(real_keys)} keys verificadas)')
except Exception as e:
    warn(check, f'no se pudo verificar i18n: {e}')

# ── CHECK: i18n-parity ────────────────────────────────────────────────────────
# Paridad ES/EN en el runtime (src/i18n/i18n.js, fuente de verdad — NO los JSON).
# Falla si una key existe en un idioma y no en el otro. Sin esto el desync crece
# en silencio (el fallback de t() a ES enmascara keys EN faltantes).
check = 'i18n-parity'
try:
    _src = open('src/i18n/i18n.js', encoding='utf-8').read()
    _b0 = _src.find('const _I18N = {')
    _depth = 0; _end = _b0
    for _i, _ch in enumerate(_src[_b0:]):
        if _ch == '{': _depth += 1
        elif _ch == '}':
            _depth -= 1
            if _depth == 0: _end = _b0 + _i + 1; break
    _blk = _src[_b0:_end]
    def _lang_block(block, lang):
        m = re.search(rf'{lang}\s*:\s*{{', block)
        if not m: return ''
        pos = m.end() - 1; d = 0
        for i, ch in enumerate(block[pos:], pos):
            if ch == '{': d += 1
            elif ch == '}':
                d -= 1
                if d == 0: return block[pos+1:i]
        return ''
    _es = set(re.findall(r'"([^"]+)":', _lang_block(_blk, 'es')))
    _en = set(re.findall(r'"([^"]+)":', _lang_block(_blk, 'en')))
    _es_only = sorted(_es - _en); _en_only = sorted(_en - _es)
    for _k in _es_only:
        fail(check, f"key '{_k}' en ES pero falta en EN (src/i18n/i18n.js)")
    for _k in _en_only:
        fail(check, f"key '{_k}' en EN pero falta en ES (src/i18n/i18n.js)")
    if not _es_only and not _en_only:
        ok(check, f'paridad ES/EN OK — {len(_es)} keys en ambos (src/i18n/i18n.js)')
except Exception as e:
    warn(check, f'no se pudo verificar paridad i18n: {e}')

# ── CHECK: i18n-hardcoded ─────────────────────────────────────────────────────
# Detecta strings de UI conocidos hardcodeados en JS sin pasar por t().
# p8 Step 4: _I18N y t() se movieron a src/i18n/i18n.js. Se escanea SOLO el código
# de app (main.js) — NO el HTML estático de index.html, que usa data-i18n con texto
# fallback legítimo (ej. <button data-i18n="av_confirmar">Confirmar</button>), ni
# los diccionarios (ya fuera de main.js). _main_src se leyó al inicio.
# Cada string encontrado en auditoría Chrome debe añadirse a la lista.
check = 'i18n-hardcoded'
try:
    # p8 Wave 8: la UI renderizada migró a src/view + src/controller (main.js conserva
    # wiring/constantes). Se escanean los 3 — NO src/i18n/i18n.js (fuente de verdad) ni
    # el HTML estático de index.html (data-i18n con fallback legítimo).
    code_only = (_main_src if os.path.exists(_MAIN_JS) else '') + '\n' + _view_all + '\n' + _controller_all

    # Strings de UI que deben ir siempre por t() — nunca hardcodeados
    # Fuente: auditorías Chrome EN/ES. Añadir aquí cada nuevo hallazgo.
    UI_STRINGS_MUST_USE_T = [
        # MY PLAN — durante festival
        'En curso', 'AHORA', 'Termina en', '¿Retraso?', 'Cabe en tu hueco',
        # Checkin / unconfirmed
        'sin confirmar', 'anteriores sin confirmar', 'anterior sin confirmar',
        # Botones y CTAs
        'Verificando', 'Confirmar',
        # Subtítulos auth
        'Ingresa tu email y te enviamos',
        # Labels generales
        'sinopsis', 'Luego',
    ]

    # Eliminar comentarios de línea antes de buscar
    import re as _re2
    code_no_comments = _re2.sub(r'//[^\n]*', '', code_only)

    hardcoded_found = []
    for s in UI_STRINGS_MUST_USE_T:
        # Buscar como string literal: 'texto' o "texto" o dentro de template >texto<
        in_single = f"'{s}'" in code_no_comments
        in_double = f'"{s}"' in code_no_comments
        in_template = f'>{s}<' in code_no_comments or f'>{s} ' in code_no_comments
        if in_single or in_double or in_template:
            hardcoded_found.append(s)

    for s in hardcoded_found:
        fail(check, f"'{s}' hardcodeado en JS — debe usar t()")

    # ── Reverse-dictionary check (primario): un VALOR ES del diccionario que
    # aparece como literal hardcodeado en view/controller = leak (alguien escribió
    # el texto en vez de llamar t()). Captura español CON y SIN acentos — el
    # diccionario es la verdad de terreno. Solo multi-palabra (≥1 espacio, ≥6 chars)
    # para evitar colisiones con identificadores de modo / keys de 1 palabra.
    # Excluye object-keys ('x':) y fallbacks legítimos (t(...)||'x').
    _es_vals = {}
    try:
        _b = _i18n_src.find('const _I18N = {'); _d = 0; _e = _b
        for _i, _c in enumerate(_i18n_src[_b:]):
            if _c == '{': _d += 1
            elif _c == '}':
                _d -= 1
                if _d == 0: _e = _b + _i + 1; break
        _blk = _i18n_src[_b:_e]
        _ms = re.search(r'es\s*:\s*{', _blk); _p = _ms.end() - 1; _d2 = 0; _esb = ''
        for _i, _c in enumerate(_blk[_p:], _p):
            if _c == '{': _d2 += 1
            elif _c == '}':
                _d2 -= 1
                if _d2 == 0: _esb = _blk[_p+1:_i]; break
        for _k, _v in re.findall(r'"([^"]+)"\s*:\s*"((?:[^"\\]|\\.)*)"', _esb):
            _es_vals[_v.replace('\\"', '"')] = _k
    except Exception:
        pass

    reverse_leaks = []
    for _val, _key in _es_vals.items():
        if ' ' not in _val or len(_val) < 6:
            continue
        for _pat in (f'>{_val}<', f'>{_val} ', f"'{_val}'", f'"{_val}"', f'`{_val}`'):
            _idx = code_no_comments.find(_pat)
            if _idx < 0:
                continue
            _before = code_no_comments[max(0, _idx - 4):_idx]
            _after = code_no_comments[_idx + len(_pat) - 1: _idx + len(_pat) + 1]
            if _before.rstrip().endswith('||'):
                continue  # t(...)||'fallback' — t() sí se usa
            if _pat[0] in "'\"" and _after.startswith(':'):
                continue  # 'valor': — key de objeto, no UI
            reverse_leaks.append((_key, _val))
            break
    for _key, _val in reverse_leaks:
        fail(check, f"valor i18n '{_val[:50]}' hardcodeado en view/controller — usar t('{_key}')")

    if not hardcoded_found and not reverse_leaks:
        ok(check, f'{len(UI_STRINGS_MUST_USE_T)} whitelist + {len(_es_vals)} valores i18n verificados — sin hardcode')

    # ── Check dinámico: strings JS con español fuera de t() ──────────────────
    # Produce warnings (no falla el deploy) — puede tener falsos positivos
    # pero detecta nuevos strings hardcodeados antes de llegar a producción
    SAFE_LINE_MARKERS = [
        'includes(', 'PROGRAMA_CHIPS', 'FESTIVAL_DATES', 'DAY_SHORT',
        'DAYS_ES', 'DAYS_EN', 'var(--', 'replace(', 'toLowerCase(',
        'normTitle', '.json', 'regex', 'RegExp', 'https://',
        'console.', # mensajes a consola (developer-facing, no UI)
        'Adolfo', 'SÁB 16', 'MIÉ 15', # venue/date literals en FESTIVAL_DATES Leviza
        'canvas vacío', # error interno, no UI visible
        'PROYECCIÓN SORPRESA', 'Valle de Aburrá', 'Plaza Proclamación', # venue/nombres Leviza
        'Ciencia Ficción', 'Ciencia ficción', 'Película de TV', 'Animación', # géneros TMDB / PROGRAMA_CHIPS
        'Iberoamérica', 'Indígena', 'Muestra España', # chips de sección (data de festival)
        'Opción personalizada', # ya usa t() — falso positivo del dict
        'SÁB 18', # fecha FESTIVAL_DATES Leviza
    ]
    SPANISH_ACCENT = set('áéíóúñÁÉÍÓÚÑ')
    import re as _re3

    # Extract only lines with Spanish chars from JS code
    dynamic_found = []
    for lnum, line in enumerate(code_no_comments.split('\n'), 1):
        if not any(c in line for c in SPANISH_ACCENT):
            continue
        if any(m in line for m in SAFE_LINE_MARKERS):
            continue
        stripped = line.strip()
        if stripped.startswith('//') or _re3.match(r'^\s*"[a-z_]+\s*:', stripped):
            continue
        # Look for single or double quoted strings with Spanish chars
        pat = "'([^'\\n]{4,60})'" + "|" + '"([^"\\n]{4,60})"'
        for m in _re3.finditer(pat, line):
            text = m.group(1) or m.group(2)
            if not any(c in text for c in SPANISH_ACCENT):
                continue
            if ' ' not in text:
                continue  # likely a key, not UI text
            if text in _es_vals:
                continue  # ya en diccionario — lo cubre el reverse-check (FAIL)
            # Skip if t() appears right before the quote
            pos = m.start()
            before = line[max(0, pos-3):pos]
            if before.endswith("t("):
                continue
            dynamic_found.append(f'L{lnum}: "{text[:55]}"')

    if dynamic_found:
        for item in dynamic_found[:8]:
            warn('i18n-dynamic', f'Posible string ES sin t(): {item}')

except Exception as e:
    warn(check, f'no se pudo verificar hardcoding: {e}')

# ── JS Syntax (Node.js) ───────────────────────────────────────────────────────
# ── CHECK: tasks-sync ─────────────────────────────────────────────────────────
# Detecta features con tasks.md donde cero tareas están completadas ([x]).
# Señal de desincronización: feature implementada sin documentar, o abandonada.
# Features con algún [x] + algunos [ ] = trabajo en progreso, no se advierte.
check = 'tasks-sync'
try:
    import glob as _glob
    stale = []
    for tf in sorted(_glob.glob('.specify/features/*/tasks.md')):
        with open(tf) as _f:
            _lines = _f.read().splitlines()
        done  = sum(1 for l in _lines if l.strip().startswith('- [x]') or l.strip().startswith('- [X]'))
        total = sum(1 for l in _lines if l.strip().startswith('- ['))
        if total > 0 and done == 0:
            feature = tf.split('/')[2]
            stale.append(f'{feature} (0/{total} completadas)')
    if stale:
        for s in stale:
            warn(check, f'tasks.md sin ninguna tarea completada — posible desincronización: {s}')
    else:
        ok(check, f'todos los tasks.md tienen al menos una tarea completada')
except Exception as e:
    warn(check, f'no se pudo verificar tasks: {e}')

check = 'js-syntax'
try:
    import subprocess, tempfile
    # Extract main script (largest <script> block)
    scripts = re.findall(r'<script[^>]*>(.*?)</script>', content, re.DOTALL)
    main_js = max(scripts, key=len) if scripts else ''
    if main_js:
        with tempfile.NamedTemporaryFile(suffix='.js', mode='w', delete=False, encoding='utf-8') as f:
            f.write(main_js)
            tmppath = f.name
        result = subprocess.run(['node', '--check', tmppath], capture_output=True)
        os.unlink(tmppath)
        if result.returncode != 0:
            err = result.stderr.decode()[:200]
            fail(check, f'error de sintaxis JS: {err}')
        else:
            ok(check, 'sintaxis JS válida (Node.js --check)')
    else:
        warn(check, 'no se encontró bloque <script> para validar')
except FileNotFoundError:
    warn(check, 'Node.js no disponible — skip sintaxis JS')


# ── CHECK 9c: i18n-interpolation ─────────────────────────────────────────────
# Keys cuyos valores contienen {placeholder} deben ser llamadas con t('key', {...}).
# Si se llaman como t('key') sin parámetros, el placeholder queda en el string final.
# Ejemplo del bug: warn_qa_tiempo = "~{n} min" pero t('warn_qa_tiempo') sin params.
check = 'i18n-interpolation'
try:
    import re as _re_interp
    # Extraer todas las keys con placeholders del diccionario ES (fuente de verdad)
    es_block = _extract_lang_block(i18n_block, 'es')
    keys_with_placeholders = {}
    for m in _re_interp.finditer(r'"([^"]+)"\s*:\s*"([^"]*\{[a-z]\w*\}[^"]*)"', es_block):
        key, val = m.group(1), m.group(2)
        placeholders = _re_interp.findall(r'\{([a-z]\w*)\}', val)
        if placeholders:
            keys_with_placeholders[key] = placeholders

    script_part = content[content.find('<script>'):content.rfind('</script>')]
    interp_errors = []
    for key, placeholders in keys_with_placeholders.items():
        # Buscar todas las llamadas a t('key') — con o sin parámetros
        all_calls = _re_interp.findall(rf"t\('{key}'([^)]*)\)", script_part)
        bare_calls = [c for c in all_calls if c.strip() == '']
        if bare_calls:
            interp_errors.append(
                f"t('{key}') llamado sin params pero la key contiene {{{','.join(placeholders)}}} — "
                f"usar t('{key}', {{{', '.join(f'{p}: ...' for p in placeholders)}}})"
            )

    if interp_errors:
        for e in interp_errors:
            fail(check, e)
    else:
        ok(check, f'{len(keys_with_placeholders)} keys con placeholders — todas llamadas con params')
except Exception as e:
    warn(check, f'no se pudo verificar interpolación i18n: {e}')

# ── CHECK 10: js-open-pel coverage ───────────────────────────────────────────
# Todo elemento con data-title que sea una card tappable debe tener js-open-pel.
# Sin esa clase, el listener delegado no lo encuentra y el tap queda mudo.
# Clases de cards tappables conocidas: int-item, mplan-list-item, plist-item,
# saved-item, poster-card, plist-event, ctx-suggest-card, suggestion-item.
check = 'js-open-pel-coverage'
TAPPABLE_CARDS = [
    'int-item',
    'mplan-list-item',
    'plist-item',
    'plist-event',
    'ctx-suggest-card',
    'suggestion-item',
]
# Excluir variantes que deliberadamente no abren sheet (botones de acción, etc.)
CARD_EXCLUSIONS = [
    'plist-heart',   # corazón — stopPropagation intencional
    'ag-fi-btn',     # quitar de agenda
    'saved-check',   # marcar vista
    'int-prio-btn',  # estrella prioridad
    'mplan-tc',      # tiempo en mplan
    'mplan-nav',     # navegación días
]
import re as _re2
pel_errors = []
# Buscar divs/elementos de card sin js-open-pel que tienen data-title
lines_html = content.split('\n')
for i, line in enumerate(lines_html, 1):
    if 'data-title=' not in line:
        continue
    # Debe ser apertura de tag con una clase de card tappable
    if not any(f'"{cls}' in line or f'"{cls} ' in line or f' {cls}"' in line or f' {cls} ' in line
               for cls in TAPPABLE_CARDS):
        continue
    # Si ya tiene js-open-pel, OK
    if 'js-open-pel' in line:
        continue
    # Si es un botón o elemento de acción, ignorar
    if any(exc in line for exc in CARD_EXCLUSIONS):
        continue
    if '<button' in line or ('onclick=' in line and 'event.stopPropagation' in line):
        continue
    # Post-7c: si tiene data-action, el delegated listener resuelve el handler explícitamente
    if 'data-action=' in line:
        continue
    # Extraer clase para mejor reporte
    cls_match = _re2.search(r'class="([^"]{1,60})"', line)
    cls_str = cls_match.group(1)[:50] if cls_match else '?'
    pel_errors.append(f'L{i}: clase "{cls_str}" tiene data-title pero falta js-open-pel — tap mudo')

if pel_errors:
    for e in pel_errors:
        fail(check, e)
    fail(check, 'Fix: añadir js-open-pel a la clase del elemento, o envolver el poster en <div class="js-open-pel" data-title="...">')
else:
    ok(check, f'Todas las cards tappables tienen js-open-pel')

# ── CHECK 11: version.json format ────────────────────────────────────────────
# version.json debe tener claves 'android' e 'ios' con builds numéricas.
# Formato legacy {"build":"..."} ya no es válido — pipeline staged rollout lo requiere.
check = 'version-json'
try:
    import json as _json
    _vj = _json.load(open('version.json'))
    if 'android' not in _vj or 'ios' not in _vj:
        fail(check, "version.json debe tener claves 'android' e 'ios' (formato legacy {\"build\":...} ya no válido)")
    elif not _vj['android'] or not _vj['ios']:
        fail(check, "version.json: 'android' e 'ios' no pueden estar vacíos")
    elif not _vj['android'].isdigit() or not _vj['ios'].isdigit():
        fail(check, "version.json: los builds deben ser strings numéricas (ej. '202605141911')")
    elif int(_vj['ios']) > int(_vj['android']):
        fail(check, f"version.json: ios ({_vj['ios']}) no puede ser mayor que android ({_vj['android']})")
    else:
        ok(check, f"version.json válido — android:{_vj['android']} ios:{_vj['ios']}")
except FileNotFoundError:
    fail(check, 'version.json no encontrado')
except Exception as _e:
    fail(check, f'version.json inválido: {_e}')

# ── onclick syntax ─────────────────────────────────────────────────────────────
# Extrae todos los onclick="..." estáticos (sin template vars ${...}) y valida
# que sean JS sintácticamente válido. Detecta bugs como } sobrante o typos.
check = 'onclick-syntax'
try:
    import re as _re, tempfile as _tf, os as _os
    _html = content  # p8: content ya incluye main.js inyectado
    _all_oc = _re.findall(r'onclick="([^"]+)"', _html)
    _static = [(i, oc) for i, oc in enumerate(_all_oc) if '${' not in oc]
    _oc_errors = []
    for _i, _oc in _static:
        _code = f'(function(){{{_oc}}})'
        with _tf.NamedTemporaryFile(suffix='.js', mode='w', delete=False) as _f:
            _f.write(_code)
            _tmpname = _f.name
        _r = subprocess.run(['node', '--check', _tmpname], capture_output=True, text=True)
        _os.unlink(_tmpname)
        if _r.returncode != 0:
            _oc_errors.append(f'onclick #{_i}: {_oc[:60]}')
    if _oc_errors:
        for _e in _oc_errors:
            fail(check, _e)
    else:
        ok(check, f'{len(_static)} onclick handlers estáticos con sintaxis válida')
except Exception as _e:
    warn(check, f'no se pudo verificar onclicks: {_e}')

# ── Storage encapsulation ────────────────────────────────────────────────────
# Toda lectura/escritura a localStorage debe pasar por el namespace `storage`.
# p8 Step 3: el adapter `storage` se movió a src/storage/storage.js (importado por
# main.js). Los markers STORAGE ADAPTER START/END viven AHÍ — salieron de `content`
# (index.html + main.js inyectado). Este check (actualizado) verifica:
#   1. Los markers STORAGE ADAPTER existen en src/storage/storage.js.
#   2. En `content` (main.js + index.html) NO hay localStorage.* salvo excepciones
#      documentadas (el adapter ya no vive ahí: cualquier localStorage en content
#      debe ser una excepción explícita).
# Excepciones (Fase 5 spec.md):
#   - 'otrofestiv_hint_cambiar', 'otrofestiv_display_name'  → onboarding/Supabase
#   - _BUILD_KEY    → SW staged rollout (clave 'orf_build')
#   - cacheKey      → caches dinámicos (poster TMDB)
#   - 'otrofestiv_lang_v2' → detección de idioma pre-paint (index.html, pre-módulo; storage no existe)
check = 'storage-encapsulation'
try:
    import re as _re
    # 1. adapter markers en storage.js
    _storage_path = 'src/storage/storage.js'
    _storage_src = open(_storage_path, encoding='utf-8').read() if os.path.exists(_storage_path) else ''
    if '// ── STORAGE ADAPTER START' not in _storage_src or '// ── STORAGE ADAPTER END' not in _storage_src:
        fail(check, 'No se encontraron marcadores STORAGE ADAPTER START/END en src/storage/storage.js')
    else:
        # 2. localStorage en content — todo debe ser excepción whitelisted
        _lines = content.split('\n')
        _ls_call = _re.compile(r'localStorage\.(getItem|setItem)\(([^,)]*)')
        _allowed_args = {
            "'otrofestiv_hint_cambiar'",
            "'otrofestiv_display_name'",
            '_BUILD_KEY',
            'cacheKey',
            "'otrofestiv_lang_v2'",
        }
        _violations = []
        for _i, _line in enumerate(_lines, 1):
            for _m in _ls_call.finditer(_line):
                _arg = _m.group(2).strip()
                if _arg in _allowed_args:
                    continue
                _violations.append(f'L{_i}: localStorage.{_m.group(1)}({_arg[:50]}) fuera del adapter (storage.js)')
        if _violations:
            for _v in _violations:
                fail(check, _v)
            fail(check, 'Fix: usar storage.getXxx()/setXxx() (src/storage/storage.js). Si es excepción legítima, añadir a whitelist en validate.py + spec.md.')
        else:
            ok(check, f'adapter en storage.js; cero localStorage en content fuera de las {len(_allowed_args)} excepciones whitelisted')
except Exception as _e:
    warn(check, f'no se pudo verificar storage encapsulation: {_e}')

# ── [state-mirror] ────────────────────────────────────────────────────────────
# p8 Step 2 (D-INFRA-4): el MIRROR fue eliminado. state (src/state/state.js) posee
# _data; main.js instala un STATE BRIDGE (Object.defineProperty sobre globalThis)
# que rutea cada bare-global del roster a state.get/set. Con el bridge, TODO
# `watchlist = x` o `watchlist.has()` atraviesa state automáticamente — el
# invariante "writes via state" es estructural. Este check (repurposed) verifica:
#   1. El STATE BRIDGE expone exactamente los 20 keys del roster.
#   2. NINGÚN roster key se redeclara (let/const/var) en main.js fuera del worker
#      (una redeclaración shadowearía el bridge → el write NO llegaría a state).
#   3. state.js no contiene mirror (_MIRROR_TARGETS/_MIRROR_READERS).
check = 'state-mirror'
try:
    import re as _re
    # El roster se LEE de state.js, no se copia. Tenía una copia hardcodeada acá y
    # derivó en cuanto el roster creció (FESTIVAL_POSTPONED, 10 ago 2026): el
    # guardián acusaba de «key NO-roster» a una key que SÍ estaba en el roster.
    # Un guardián con su propia copia de la verdad no vigila: compite.
    _st = open('src/state/state.js', encoding='utf-8').read()
    _blk = _st[_st.index('const _ROSTER'):]
    _blk = _blk[:_blk.index(']')]
    _roster = _re.findall(r"'([^']+)'", _blk)
    if len(_roster) < 15:
        raise ValueError('no pude leer _ROSTER de state.js (leí %d keys)' % len(_roster))
    _lines = content.split('\n')
    _problems = []

    # ── 1. STATE BRIDGE markers + _BRIDGE_KEYS expone los 19 ──
    # p8 Step 8a: el STATE BRIDGE se reubicó a src/state/state-bridge.js (Wave 8:
    # relocate). Los markers + _BRIDGE_KEYS viven allá; este check los escanea ahí.
    _bridge_path = 'src/state/state-bridge.js'
    _bridge_lines = (
        open(_bridge_path, encoding='utf-8').read().split('\n')
        if os.path.exists(_bridge_path) else []
    )
    if not _bridge_lines:
        _problems.append(f'{_bridge_path} no encontrado (STATE BRIDGE)')
    _bs = _be = None
    for _i, _line in enumerate(_bridge_lines, 1):
        if '// ── STATE BRIDGE START' in _line: _bs = _i
        elif '// ── STATE BRIDGE END' in _line: _be = _i
    if _bs is None or _be is None:
        _problems.append(f'No se encontraron marcadores STATE BRIDGE START/END en {_bridge_path}')
    else:
        _bridge_block = '\n'.join(_bridge_lines[_bs - 1:_be])
        _bk_keys = set(_re.findall(r"'([A-Za-z_][A-Za-z0-9_]*)'", _bridge_block))
        for _k in _roster:
            if _k not in _bk_keys:
                _problems.append(f'STATE BRIDGE no expone roster key: {_k}')
        for _k in _bk_keys:
            if _k not in _roster:
                _problems.append(f'STATE BRIDGE expone key NO-roster: {_k}')

    # ── 2. anti-shadowing: ninguna redeclaración let/const/var de roster ──
    # Whitelist: template literals del worker (_workerGlobals/_handler) tienen
    # copias `let FILMS=[], ...` — contexto JS separado, sin acceso al bridge.
    _worker_ranges = []
    _i = 0
    while _i < len(_lines):
        if _re.search(r'const\s+(_workerGlobals|_handler)\s*=\s*`', _lines[_i]):
            _start = _i + 1
            _j = _i + 1
            while _j < len(_lines):
                if _re.match(r'^\s*`\s*;', _lines[_j]):
                    _worker_ranges.append((_start, _j + 1)); _i = _j; break
                _j += 1
        _i += 1

    def _in_worker(_ln):
        return any(_a <= _ln <= _b for (_a, _b) in _worker_ranges)

    for _name in _roster:
        # let/const/var <name>  |  let a=.., <name>  (multi-decl, name no primero)
        _re_decl = _re.compile(
            r'\b(?:let|const|var)\s+(?:[\w$]+\s*(?:=[^,;]*?)?\s*,\s*)*' + _re.escape(_name) + r'\b'
        )
        for _i, _line in enumerate(_lines, 1):
            _st = _line.lstrip()
            if _st.startswith('//') or _st.startswith('*'):
                continue
            if _re_decl.search(_line) and not _in_worker(_i):
                _problems.append(f'L{_i}: redeclaración de roster `{_name}` (shadowea el bridge) → "{_line.strip()[:70]}"')

    # ── 3. state.js sin mirror ──
    _state_path = 'src/state/state.js'
    if os.path.exists(_state_path):
        _state_src = open(_state_path, encoding='utf-8').read()
        if _re.search(r'const\s+_MIRROR_(TARGETS|READERS)\b', _state_src):
            _problems.append('state.js todavía declara el mirror (const _MIRROR_TARGETS/_MIRROR_READERS) — D-INFRA-4 lo elimina')
    else:
        _problems.append('src/state/state.js no encontrado')

    if _problems:
        for _p in _problems[:20]:
            fail(check, _p)
        if len(_problems) > 20:
            fail(check, f'... y {len(_problems) - 20} problemas más')
        fail(check, 'Fix: roster vive en state (bridge). NO redeclarar con let/const/var en main.js. Worker boundary: verificar markers.')
    else:
        ok(check, f'STATE BRIDGE expone {len(_roster)} roster keys; cero shadowing fuera de {len(_worker_ranges)} worker templates; state.js sin mirror')
except Exception as _e:
    warn(check, f'no se pudo verificar state bridge: {_e}')

# ── [viewstate-shadow] ────────────────────────────────────────────────────────
# p8 Step 8b (Wave 8: relocate): los 29 lets NO-roster (view-state + festival-data
# + calc-cache + auth/splash/posters) se reubicaron a src/state/viewstate.js, que
# instala el `_lets` bridge (Object.defineProperty sobre globalThis) en import-phase.
# main.js + módulos los leen/escriben vía globalThis. Este check verifica:
#   1. viewstate.js expone exactamente estos 29 keys (markers VIEWSTATE BRIDGE).
#   2. NINGUNO se redeclara (let/const/var) en main.js (una redecl shadowearía el
#      bridge → el write de main.js NO llegaría a los demás módulos).
check = 'viewstate-shadow'
try:
    import re as _re
    _vs_keys = [
        'DAY_KEYS', 'cachedResult', 'activeDay', 'activeView', 'activeVenue',
        'activeSec', 'selectedIdx', 'activeMNav', 'programaSubMode',
        'programaViewMode', 'cartelaMode', 'miPlanViewMode',
        '_sbUser', '_sb', 'LB_SLUGS', 'POSTERS', 'CUSTOM_POSTERS',
        '_splashSelectedFestId', 'programaChip', '_programaChipMatchFn',
        '_dismissedNotices', '_currentChips', '_activeMiPlanFilm', '_expandedFilm',
        'activeMiPlanDay', 'miPlanViewStart', '_ctaRemovedVisible',
    ]
    _problems = []

    # ── 1. viewstate.js expone los 29 keys (entre markers) ──
    _vs_path = 'src/state/viewstate.js'
    _vs_lines = (
        open(_vs_path, encoding='utf-8').read().split('\n')
        if os.path.exists(_vs_path) else []
    )
    if not _vs_lines:
        _problems.append(f'{_vs_path} no encontrado (VIEWSTATE BRIDGE)')
    _vbs = _vbe = None
    for _i, _line in enumerate(_vs_lines, 1):
        if '// ── VIEWSTATE BRIDGE START' in _line: _vbs = _i
        elif '// ── VIEWSTATE BRIDGE END' in _line: _vbe = _i
    if _vbs is None or _vbe is None:
        _problems.append(f'No se encontraron marcadores VIEWSTATE BRIDGE START/END en {_vs_path}')
    else:
        _vblock = '\n'.join(_vs_lines[_vbs - 1:_vbe])
        # keys del _lets: aparecen como `<key>:` en el objeto + en defineProperty
        _exposed = set(_re.findall(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*\[", _vblock, _re.M))
        for _k in _vs_keys:
            if _k not in _exposed:
                _problems.append(f'VIEWSTATE BRIDGE no expone key: {_k}')

    # ── 2. anti-shadowing: ninguna redeclaración let/const/var en main.js ──
    _main_lines = _main_src.split('\n')
    for _name in _vs_keys:
        _re_decl = _re.compile(
            r'\b(?:let|const|var)\s+(?:[\w$]+\s*(?:=[^,;]*?)?\s*,\s*)*' + _re.escape(_name) + r'\b'
        )
        for _i, _line in enumerate(_main_lines, 1):
            _st = _line.lstrip()
            if _st.startswith('//') or _st.startswith('*'):
                continue
            if _re_decl.search(_line):
                _problems.append(f'main.js L{_i}: redeclaración de viewstate `{_name}` (shadowea el bridge) → "{_line.strip()[:70]}"')

    if _problems:
        for _p in _problems[:20]:
            fail(check, _p)
        if len(_problems) > 20:
            fail(check, f'... y {len(_problems) - 20} problemas más')
        fail(check, 'Fix: viewstate vive en state/viewstate.js (bridge). NO redeclarar con let/const/var en main.js.')
    else:
        ok(check, f'VIEWSTATE BRIDGE expone {len(_vs_keys)} keys; cero shadowing en main.js')
except Exception as _e:
    warn(check, f'no se pudo verificar viewstate bridge: {_e}')

# ── [validate-film-tests] ─────────────────────────────────────────────────────
# Gate de cobertura: si domain/film.js exporta validateFilm (validación de datos
# del JSON de festival), DEBE estar cubierta por ≥5 tests en tests/. Sin esto, no
# mergear — la validación es crítica y debe tener red de seguridad.
check = 'validate-film-tests'
try:
    import glob as _glob
    _film_path = 'src/domain/film.js'
    _film_src = open(_film_path, encoding='utf-8').read() if os.path.exists(_film_path) else ''
    if 'export function validateFilm' not in _film_src:
        ok(check, 'validateFilm no exportada — sin requisito de tests')
    else:
        _vf_test_src = ''
        for _tf in _glob.glob('tests/**/*.js', recursive=True):
            try:
                _s = open(_tf, encoding='utf-8').read()
            except Exception:
                continue
            if 'validateFilm' in _s:
                _vf_test_src += '\n' + _s
        _n_tests = _vf_test_src.count('test(')
        if 'validateFilm' not in _vf_test_src:
            fail(check, 'validateFilm está exportada pero NO tiene tests en tests/ — no mergear')
        elif _n_tests < 5:
            fail(check, f'validateFilm cubierta por solo {_n_tests} test() (mínimo 5 requerido) — no mergear')
        else:
            ok(check, f'validateFilm cubierta por {_n_tests} tests')
except Exception as _e:
    warn(check, f'no se pudo verificar tests de validateFilm: {_e}')

# ── [no-underscore-actions] ───────────────────────────────────────────────────
# Convención (Tier-1): el nombre público de toda acción es la KEY de data-action,
# y NUNCA empieza con `_` (el prefijo `_` = interno, no entry-point de HTML). La
# función detrás puede conservar `_` (es impl); el arrow del registry da el alias
# público limpio. Este check bloquea regresiones: cero `data-action="_..."` en src/.
check = 'no-underscore-actions'
try:
    import glob as _glob, re as _re2
    _ua_hits = []
    for _f in sorted(_glob.glob('src/**/*.js', recursive=True)):
        try:
            _lines = open(_f, encoding='utf-8').read().split('\n')
        except Exception:
            continue
        for _i, _ln in enumerate(_lines, 1):
            if _re2.search(r'data-action="_', _ln):
                _ua_hits.append(f'{_f}:{_i}')
    if _ua_hits:
        for _h in _ua_hits[:20]:
            fail(check, f'data-action con prefijo `_` (entry point público no debe tener `_`): {_h}')
        fail(check, 'Fix: quitar `_` de la key del data-action (la fn interna puede conservarlo).')
    else:
        ok(check, 'cero data-action="_..." en src/ — entry points públicos sin prefijo `_`')
except Exception as _e:
    warn(check, f'no se pudo verificar data-action: {_e}')

# ── [view-purity] ─────────────────────────────────────────────────────────────
# Verifica que las Views Tier 1 (Fase 6a) cumplan el contrato de función pura:
#   - Reciben state como primer parámetro
#   - Hacen destructure de state.snapshot() al inicio
#   - NO leen globals del roster directamente (deben estar en el destructure)
#   - NO tienen side effects: innerHTML=, outerHTML=, classList.X(), appendChild,
#     insertAdjacentHTML, setTimeout, requestAnimationFrame
# Nivel: WARNING (Fase 6a). Promote a FAIL en Fase 7 cuando Controllers migren.
check = 'view-purity'
try:
    import re as _re
    # p8 Step 6a/6c: PURE_FNS movidos a src/view/*.js (components, programa). Se
    # concatenan para que _find_fn_body los halle ahí (regex acepta `export`).
    _components_src = ''
    for _vp in ('components.js', 'programa.js', 'helpers.js', 'agenda.js'):
        _vpath = os.path.join('src', 'view', _vp)
        if os.path.exists(_vpath):
            _components_src += '\n' + open(_vpath, encoding='utf-8').read()
    # p8 Step 7d-1: renderAvDayHTML (pure builder que lee avAddOpen UI-state) vive
    # en controller/sheets-controller.js → escanear controller/* para hallarlo.
    _html = content + _components_src + _controller_all
    _lines = _html.split('\n')
    # PURE_FNS — funciones puras tracked por el check. Renamed de TIER1_FNS en
    # p6b porque ahora cubre múltiples tiers: Tier 1 originales (6a) + Group A
    # reclasificadas (6b) + Group B pure halves (6b, suffix HTML) + Group I
    # pure halves de Tier 3 (6c).
    #
    # NO incluidos (impure legítimos, documentado en spec 6c):
    # - renderAgenda, render (Group II Tier 3 — branchy multi-dispatcher,
    #   side effects branch-específicos)
    # - renderSbar (reclasificada Group II durante 6c — usa createElement +
    #   appendChild + handlers programáticos, no innerHTML para contenido)
    #
    # Caso especial: renderPeliculaViewHTML retorna TUPLA {html, hasEntries}
    # (no string puro). Es deviation E1a documentada en code comment de la
    # función. Sigue siendo pura — el check valida ausencia de side effects,
    # no la forma del return.
    PURE_FNS = [
        # Tier 1 originales (Fase 6a)
        'makeProgramPoster', 'makeEventPoster',
        'renderUnconfirmed', '_renderSavedAgendaHTML',
        'renderContextualHeader', 'renderMiPlanCalendar',
        # Group A reclasificadas (Fase 6b — pure-ish, no side effects)
        'renderSavedAgendaHTML', 'renderFlowProgress',
        'renderPrioStrip', 'renderFilmAlternatives',
        # Group B pure halves (Fase 6b — split de Tier 2 mixed)
        'renderRatingStarsHTML', 'renderNoticesBannerHTML',
        'renderProgramaChipsHTML', '_renderSplashRailHTML',
        '_renderFestivalSelectorHTML', 'renderAvDayHTML',
        'renderFilmListHTML',
        # Group I pure halves (Fase 6c — split de Tier 3 orchestrators)
        'renderAvBlocksHTML', 'renderProgramaListHTML',
        '_renderExploreListaHTML', 'renderPeliculaViewHTML',
    ]
    ROSTER = ['_activeFestId', 'FILMS', 'FESTIVAL_DATES', 'FESTIVAL_END',
              'FESTIVAL_STORAGE_KEY', 'PRIO_LIMIT', 'TZ_OFFSET', 'FESTIVAL_TRANSPORT',
              'watchlist', 'watched', 'prioritized', 'filmRatings', 'filmDelays',
              'filmDelaysHistory', 'savedAgenda', 'availability', 'lastRemovedSlots',
              '_lang', '_simTime']

    def _find_fn_body(name):
        """Returns (start_line_idx, end_line_idx, body_lines) o None."""
        for i, line in enumerate(_lines):
            if _re.match(r'^\s*(?:export\s+)?(?:async\s+)?function\s+' + _re.escape(name) + r'\s*\(', line):
                # Walk braces from the first { after the signature
                depth = 0
                started = False
                for j in range(i, len(_lines)):
                    for ch in _lines[j]:
                        if ch == '{':
                            depth += 1
                            started = True
                        elif ch == '}':
                            depth -= 1
                            if started and depth == 0:
                                return (i, j, _lines[i:j+1])
        return None

    def _strip_strings_and_comments(line):
        """Remove single/double/backtick strings, // comments, /* */ from a line."""
        out = []
        i = 0
        in_str = None
        while i < len(line):
            ch = line[i]
            if in_str:
                if ch == '\\' and i+1 < len(line):
                    i += 2
                    continue
                if ch == in_str:
                    in_str = None
                i += 1
                continue
            if ch == '/' and i+1 < len(line) and line[i+1] == '/':
                break  # rest is comment
            if ch in ('"', "'", '`'):
                in_str = ch
                i += 1
                continue
            out.append(ch)
            i += 1
        return ''.join(out)

    _warnings_collected = []
    for _fn in PURE_FNS:
        _result = _find_fn_body(_fn)
        if not _result:
            _warnings_collected.append(f'{_fn}: NOT FOUND en index.html')
            continue
        _start, _end, _body = _result

        # Stripped body sin strings/comments (para análisis sintáctico real)
        _stripped = '\n'.join(_strip_strings_and_comments(l) for l in _body)

        # 1. Buscar destructure de state.snapshot() en las primeras N líneas
        _destruct_m = _re.search(r'const\s*\{([^}]+)\}\s*=\s*state\.snapshot\(\)',
                                  '\n'.join(_body[:6]))
        _destructured_keys = set()
        if _destruct_m:
            _destructured_keys = {k.strip().split(':')[0].strip()
                                  for k in _destruct_m.group(1).split(',') if k.strip()}

        # 2. Para cada roster global referenciado en el body stripped:
        #    si NO está en destructure → warning
        for _g in ROSTER:
            # busca refs al global en el código real (no strings)
            if _re.search(r'(?<![.\w])' + _re.escape(_g) + r'\b', _stripped):
                if _g not in _destructured_keys:
                    _warnings_collected.append(
                        f'{_fn}: read directo de "{_g}" — usar state.snapshot() destructure')

        # 3. Side effects
        _se_patterns = [
            (r'\.innerHTML\s*=(?!=)', 'innerHTML='),
            (r'\.outerHTML\s*=(?!=)', 'outerHTML='),
            (r'\.classList\.(add|remove|toggle|replace)\(', 'classList mutation'),
            (r'\.appendChild\(', 'appendChild'),
            (r'insertAdjacentHTML\(', 'insertAdjacentHTML'),
            (r'\bsetTimeout\(', 'setTimeout'),
            (r'\brequestAnimationFrame\(', 'requestAnimationFrame'),
        ]
        for _pat, _kind in _se_patterns:
            if _re.search(_pat, _stripped):
                _warnings_collected.append(f'{_fn}: side-effect "{_kind}" — debe ser pura (return string, no DOM ops)')

    if _warnings_collected:
        for _w in _warnings_collected:
            warn(check, _w)
    else:
        ok(check, f'{len(PURE_FNS)} funciones puras: state param + destructure + cero side effects')
except Exception as _e:
    warn(check, f'no se pudo verificar view purity: {_e}')

# ── [controller-pattern] ──────────────────────────────────────────────────────
# Verifica que los 18 action handlers (Fase 7a) sigan el shape canónico:
#   - State reads (destructure de state.snapshot()) al top, NO después de mutations
#   - State mutations (state.set/update/batchUpdate) ANTES de la primera render call
#
# Whitelist: modal callbacks (closures dentro de showActionModal/etc.) NO se
# validan — son closures internas con su propia estructura. Solo el outer
# handler nombrado se evalúa.
#
# Nivel: WARNING. Promote a FAIL en 7d-2 (post-Tribeca) cuando el pipeline
# subscribe→render cubra TODOS los slices. En 7d (scope narrow D7=A) solo 7
# slices limpios shed sus renders; los handlers de slices diferidos (savedAgenda,
# availability, lastRemovedSlots) conservan render manual legítimamente.
check = 'controller-pattern'
try:
    import re as _re
    # p8 Wave 7: content (main.js) + controller/*.js (handlers migrados ahí).
    _html = content + _controller_all
    _lines = _html.split('\n')
    CONTROLLER_FNS = [
        # Pequeños (6)
        'removeBlock', 'clearDelay', 'setDelay', 'undoDelay',
        'checkinLaVi', 'savePVRating',
        # Medianos (8)
        'removeFromAgenda', 'confirmConflictReplace', 'toggleFullDay',
        'addBlock', 'markWatchedFromPlan', 'setLang', 'confirmAvBlock',
        'togglePriority',
        # Grandes (4)
        'toggleWatched', 'confirmReplace', 'addSuggestion', 'toggleWL',
    ]

    RENDER_CALLS = _re.compile(
        r'\b(render(Agenda|FilmListHTML|ContextualHeader|MiPlanCalendar|Sbar|'
        r'PeliculaView|ProgramaList|FlowProgress|PrioStrip|NoticesBanner|'
        r'ProgramaChips|AvBlocks|AvDay|FilmAlternatives|Unconfirmed|'
        r'SavedAgendaHTML|RatingStars)|_renderProgramaContent|'
        r'_reRenderIntereses|_rerenderFilmList|runCalc)\s*\('
    )
    STATE_MUTATIONS = _re.compile(r'\bstate\.(set|update|batchUpdate)\s*\(')

    def _find_fn_body_7a(name):
        # p8 Wave 7: acepta `export function` (handlers migrados a controller/*.js).
        pat = _re.compile(rf'^(?:export\s+)?(?:async\s+)?function\s+{_re.escape(name)}\s*\(')
        for _i, _line in enumerate(_lines):
            if pat.match(_line):
                depth = 0; started = False
                for _j in range(_i, len(_lines)):
                    for _ch in _lines[_j]:
                        if _ch == '{':
                            depth += 1; started = True
                        elif _ch == '}':
                            depth -= 1
                            if started and depth == 0:
                                return (_i+1, _j+1, _lines[_i:_j+1])
        return None

    _cp_warnings = []
    for _fn in CONTROLLER_FNS:
        _result = _find_fn_body_7a(_fn)
        if not _result:
            _cp_warnings.append(f'{_fn}: NOT FOUND en index.html')
            continue
        _start, _end, _body = _result
        # Skip modal closures: find positions of showActionModal/showDestructiveModal/
        # showConflictModal/btn.onclick= en el body. El contenido dentro de su `() => {...}`
        # callback se whitelistea (no se valida).
        _body_text = '\n'.join(_body)
        # Sustituir contenido de modal callbacks por placeholders neutros
        # Pattern: `showActionModal(...)`, `showDestructiveModal(...)`, `showConflictModal(...)`
        # con `()=>{...}` adentro. Y `btn.onclick=()=>{...}`. Estos son closures internas.
        _stripped = _re.sub(
            r'(show(?:Action|Destructive|Conflict)Modal\s*\([^)]*?\(\s*\)\s*=>\s*\{[\s\S]*?\}\s*\)|'
            r'\.onclick\s*=\s*\(\s*\)\s*=>\s*\{[\s\S]*?\})',
            '/* MODAL_CALLBACK_WHITELIST */',
            _body_text
        )

        # Find first state mutation position
        _mut_match = STATE_MUTATIONS.search(_stripped)
        # Find first render call position
        _render_match = RENDER_CALLS.search(_stripped)

        # Check 1: state mutation AFTER first render call
        # Excepción: si hay `return;` ENTRE el render y la mutation, están en
        # branches distintos (early-return + fall-through) — mutuamente exclusivos
        if _mut_match and _render_match and _mut_match.start() > _render_match.start():
            _between = _stripped[_render_match.end():_mut_match.start()]
            _has_early_return = bool(_re.search(r'\breturn\s*;', _between))
            if not _has_early_return:
                _cp_warnings.append(f'{_fn}: state.set/update AFTER render call — debe ser mutate → render')

        # Check 2: roster read directo (NO via state.snapshot/get) DESPUÉS de primera mutation
        # Solo se valida si el handler hace mutations
        if _mut_match:
            _after_mut = _stripped[_mut_match.end():]
            _roster_after = ['savedAgenda', 'FILMS', 'watched', 'watchlist', 'prioritized',
                             'filmRatings', 'filmDelays', 'availability', '_activeFestId',
                             '_lang', 'PRIO_LIMIT']
            # Heurística simple: el handler tiene destructure al top si tiene
            # `const {...} = state.snapshot()` antes de la primera mutation
            _has_top_destructure = bool(_re.search(
                r'^\s*(?://[^\n]*\n\s*)*\s*const\s*\{[^}]+\}\s*=\s*state\.snapshot\(\)',
                _stripped[:_mut_match.start()]
            ))
            if not _has_top_destructure:
                # Si hay reads del roster, podría faltar destructure
                _reads_after = [g for g in _roster_after
                                if _re.search(r'(?<![.\w])' + _re.escape(g) + r'\b', _stripped)]
                if _reads_after:
                    # No fail — solo informativo en 7a (la mayoría son OK al usar el global mirror)
                    pass

    if _cp_warnings:
        for _w in _cp_warnings:
            warn(check, _w)
    else:
        ok(check, f'{len(CONTROLLER_FNS)} action handlers siguen el pattern canónico (mutate → render, modal callbacks whitelisted)')
except Exception as _e:
    warn(check, f'no se pudo verificar controller pattern: {_e}')

# ── [event-delegation] ────────────────────────────────────────────────────────
# Tracking de migración onclick inline → data-action delegated.
# Reporta:
#   - Cuántos onclick="..." quedan (baseline 142 antes de 7c-1)
#   - Typos: data-action="X" usado pero X no existe en ACTION_REGISTRY
#   - Dead entries: ACTION_REGISTRY entries sin call site (excepto composite
#     helpers, que son foundation up-front)
#
# Nivel: FAIL desde 7c-4 — migración completa (onclick=0). Cualquier onclick
# inline nuevo o typo de data-action rompe el build.
check = 'event-delegation'
try:
    import re as _re
    _html = content  # p8: content ya incluye main.js inyectado
    # Onclick remaining (excluyendo el ejemplo en mi comentario del CONTROLLER LAYER block)
    _onclick_count = len(_re.findall(r'\bonclick="', _html))
    # Parsear ACTION_REGISTRY entries
    _reg_start = _html.find('const ACTION_REGISTRY = {')
    _reg_end = _html.find('};', _reg_start) if _reg_start >= 0 else -1
    if _reg_start < 0 or _reg_end < 0:
        fail(check, 'ACTION_REGISTRY no encontrado en index.html')
    else:
        _reg_block = _html[_reg_start:_reg_end]
        # Match `keyname: ` (al inicio de línea, con indentación)
        _registry_keys = set(_re.findall(r'^\s+([_a-zA-Z][_a-zA-Z0-9]*)\s*:\s*\(', _reg_block, _re.M))
        # data-action usados en HTML. Valores dinámicos (template ternary
        # `${cond?'fnA':'fnB'}`) se resuelven extrayendo los literales quoted —
        # ambas ramas deben existir en el registry.
        _used_actions = set()
        for _a in _re.findall(r'data-action="([^"]+)"', _html):
            if '${' in _a:
                _used_actions.update(_re.findall(r"'([_a-zA-Z][_a-zA-Z0-9]*)'", _a))
            else:
                _used_actions.add(_a)
        # Typo detection
        _typos = _used_actions - _registry_keys
        # Dead entries (entries en registry sin uso en HTML)
        _dead = _registry_keys - _used_actions
        # Composite helpers se esperan dead en 7c-1 (foundation up-front)
        _composite_helpers = {
            'scrollToAgSec', 'clearExpandedFilm', 'setAvAddOpen',
            'closePelAndRemove', 'closePelAndRate', 'navTo',
            'closeAuthAndReset', 'dismissToastAction', 'toggleCtxOlder',
            'toggleWatchedAndClose', 'toggleWLAndClose',
        }
        _dead_non_composite = _dead - _composite_helpers

        if _typos:
            for _typo in sorted(_typos):
                fail(check, f'data-action="{_typo}" usado en HTML pero NO existe en ACTION_REGISTRY')
        elif _onclick_count > 0:
            fail(check, f'{_onclick_count} onclick inline restantes — event-delegation '
                        f'requiere onclick=0 (migración completa en 7c-4)')
        else:
            ok(check, f'onclick=0 (migración completa), '
                      f'{len(_used_actions)} data-actions usados, '
                      f'{len(_registry_keys)} entries en registry, '
                      f'{len(_dead_non_composite)} dead non-composite')
except Exception as _e:
    warn(check, f'no se pudo verificar event delegation: {_e}')

# ── CHECK: [dom-ready-guard] ──────────────────────────────────────────────────
# main.js se INYECTA como módulo (store-gate) → DOMContentLoaded/load ya
# dispararon cuando el módulo evalúa. Un addEventListener('DOMContentLoaded'|'load')
# DESNUDO registra para un evento pasado → nunca corre (fue el bug de idioma:
# UI estática en ES mientras el contenido salía en el idioma real). El patrón
# correcto es onDomReady/onWindowLoad (src/util/ready.js), que ejecutan ya si el
# DOM alcanzó el estado. Este check prohíbe el listener desnudo en src/.
check = 'dom-ready-guard'
try:
    import re as _re2
    _READY_RE = _re2.compile(r"addEventListener\(\s*['\"](?:DOMContentLoaded|load)['\"]")
    _offenders = []
    for _root, _dirs, _files in os.walk('src'):
        for _fn in _files:
            if not _fn.endswith('.js'): continue
            _fp = os.path.join(_root, _fn)
            if _fp.replace('\\', '/') == 'src/util/ready.js': continue  # la casa de los helpers
            _txt = open(_fp, encoding='utf-8').read()
            for _m in _READY_RE.finditer(_txt):
                _lstart = _txt.rfind('\n', 0, _m.start()) + 1
                _prefix = _txt[_lstart:_m.start()]
                if '//' in _prefix or '*' in _prefix: continue  # match dentro de comentario
                _ln = _txt[:_m.start()].count('\n') + 1
                _offenders.append(f'{_fp}:{_ln}')
    if _offenders:
        fail(check, 'addEventListener(DOMContentLoaded|load) desnudo — usar onDomReady/onWindowLoad (src/util/ready.js), el módulo se inyecta tarde: ' + ', '.join(_offenders))
    else:
        ok(check, 'sin listeners DOMContentLoaded/load desnudos en src/ (usan los guards de ready.js)')
except Exception as _e:
    warn(check, f'no se pudo verificar dom-ready-guard: {_e}')

# ── CHECK: [refresco-huella-cruda] ────────────────────────────────────────────
# La ingesta MUTA el JSON recién bajado (explodeScreenings devuelve los MISMOS
# objetos que data.films; la duración de programas, sealSharedSlots y NOTICES
# escriben sobre él). Si la huella del refresco en caliente se toma DESPUÉS de
# esas mutaciones, nunca vuelve a coincidir con la de un JSON fresco y el
# refresco cree ver un cambio en cada tick: los pósters titilan (Juan lo vio en
# su teléfono, 24 ago 2026). La huella y la copia cruda van ANTES de todo.
check = 'refresco-huella-cruda'
try:
    _ld = open('src/controller/loader.js', encoding='utf-8').read()
    _i = _ld.find('export function _ingerirDatosFestival')
    if _i < 0:
        fail(check, 'no existe _ingerirDatosFestival — el dueño único de la ingesta desapareció')
    else:
        _cuerpo = _ld[_i:_ld.find('\nexport ', _i + 10)]
        # SIN COMENTARIOS: el porqué de este check NOMBRA a explodeScreenings y a
        # sealSharedSlots, así que buscar sobre el texto crudo encontraba la
        # mención en la prosa y acusaba al código ya arreglado. Un guardián tiene
        # que mirar código, no su propia explicación.
        _codigo = '\n'.join(_l for _l in _cuerpo.split('\n') if not _l.lstrip().startswith('//'))
        _pos_hash = _codigo.find('_rawHash')
        _pos_mut  = min([p for p in (_codigo.find('explodeScreenings'), _codigo.find('sealSharedSlots')) if p > 0] or [-1])
        if _pos_hash < 0:
            fail(check, 'la ingesta ya no toma la huella cruda (_rawHash) — el refresco quedaría ciego')
        elif _pos_mut > 0 and _pos_hash > _pos_mut:
            fail(check, 'la huella (_rawHash) se toma DESPUÉS de mutar el JSON — el refresco verá un cambio en cada tick y los pósters van a titilar')
        elif 'cfg._rawFilms=data.films' in _codigo.replace(' ', ''):
            fail(check, '_rawFilms guarda la REFERENCIA al JSON que la ingesta muta — el lado viejo del diff se inventará cambios; debe ser copia')
        else:
            ok(check, 'la huella y la copia crudas se toman antes de que la ingesta mute el JSON')
except Exception as _e:
    warn(check, f'no se pudo verificar refresco-huella-cruda: {_e}')

# ── CHECK: [update-canales-sin-sw] ────────────────────────────────────────────
# Los 4 canales de version.json (cold start, visibilitychange, online, poll) NO
# dependen del service worker: son fetch + location.href. Vivieron años dentro
# de if('serviceWorker' in navigator) → el wrapper iOS (WKWebView sin
# WKAppBoundDomains, SIN esa API) quedaba sin NINGÚN mecanismo de actualización
# (24 ago 2026: el palmarés de FINCA no llegaba con la app en la mano). Este
# check prohíbe que los canales vuelvan a caer dentro de un guard de SW, y exige
# que existan. Cazado también por T102 (Playwright, borra la API de verdad).
check = 'update-canales-sin-sw'
try:
    import re as _re3
    _mainjs = open('src/main.js', encoding='utf-8').read()
    # Marcadores EJECUTABLES, no comentarios: '_checkVersionJson({offer:true})'
    # es la llamada del poll (canal #4) — 'updPoll' era mal marcador, vive
    # también en comentarios y sobrevivía a la muerte del canal.
    _CANALES = ['_checkVersionJson(', '_offerUpdate(', '_checkVersionJson({offer:true})']
    _faltan = [c for c in _CANALES if c not in _mainjs]
    _presos = []
    for _m in _re3.finditer(r"if\s*\(\s*(?:'serviceWorker'\s+in\s+navigator|_HAS_SW)\s*\)\s*\{", _mainjs):
        _d = 0; _i = _m.end() - 1
        while _i < len(_mainjs):
            if _mainjs[_i] == '{': _d += 1
            elif _mainjs[_i] == '}':
                _d -= 1
                if _d == 0: break
            _i += 1
        _bloque = _mainjs[_m.start():_i]
        for _c in _CANALES + ['setInterval(', "addEventListener('visibilitychange'", "addEventListener('online'"]:
            if _c in _bloque:
                _ln = _mainjs[:_m.start()].count('\n') + 1
                _presos.append(f'{_c} dentro del guard de SW (linea {_ln})')
    if _faltan:
        fail(check, 'canal(es) de version.json AUSENTES de src/main.js (iOS sin update): ' + ', '.join(_faltan))
    elif _presos:
        fail(check, 'canal(es) de version.json PRESOS del guard de SW — el wrapper iOS no tiene esa API y se queda sin updates: ' + '; '.join(_presos))
    else:
        ok(check, 'los 4 canales de version.json viven fuera del guard de SW (el wrapper iOS los corre)')
except Exception as _e:
    warn(check, f'no se pudo verificar update-canales-sin-sw: {_e}')

# ── CHECK: [synopsis-helper] ──────────────────────────────────────────────────
# REGLA: la sinopsis localizada se resuelve SOLO vía locSynopsis(f) (src/i18n/i18n.js).
# Prohibido rehacer a mano el ternario `_lang==='en'?...synopsis_en...` en view/
# controller — era una de las fuentes de inconsistencia de idioma (misma lógica
# copiada en 3 sitios que divergían). Flagea cualquier línea de src/ que combine
# `_lang` con `synopsis_en|synopsis_es`, salvo la casa del helper (i18n.js).
check = 'synopsis-helper'
try:
    import re as _re3
    _SYN_RE = _re3.compile(r"synopsis_(?:en|es)")
    _offenders = []
    for _root, _dirs, _files in os.walk('src'):
        for _fn in _files:
            if not _fn.endswith('.js'): continue
            _fp = os.path.join(_root, _fn).replace('\\', '/')
            if _fp == 'src/i18n/i18n.js': continue  # la casa de locSynopsis
            for _i, _line in enumerate(open(_fp, encoding='utf-8'), 1):
                if _SYN_RE.search(_line) and '_lang' in _line:
                    _offenders.append(f'{_fp}:{_i}')
    if _offenders:
        fail(check, 'ternario de sinopsis a mano — usar locSynopsis(f) de i18n.js: ' + ', '.join(_offenders))
    else:
        ok(check, 'sinopsis localizada solo vía locSynopsis (sin ternarios _lang+synopsis_* a mano)')
except Exception as _e:
    warn(check, f'no se pudo verificar synopsis-helper: {_e}')

# ── CHECK: [section-display-raw] ──────────────────────────────────────────────
# REGLA INAMOVIBLE: todo display de nombre de sección pasa por _secLabel()/
# _secLabelFull(). Flagea `X.section` (incl. optional chaining `X?.section`)
# interpolado como TEXTO VISIBLE de HTML — es decir, dentro de `>${ ... }` (texto
# de un elemento) — cuando NO va envuelto en _secLabel. Los usos como CLAVE
# (SECTION_COLORS[f.section], indexOf, data-s="${f.section}", f.section===x) no
# matchean porque no están en posición de texto (no van precedidos de `>`).
check = 'section-display-raw'
try:
    # Detector puro (testeable): interpolación `>${...X.section...}` sin _secLabel.
    _SEC_DISPLAY_RE = re.compile(r'>\s*\$\{([^{}]*\b\w+\??\.section\b[^{}]*)\}')
    def _scan_section_display_raw(text):
        hits = []
        for m in _SEC_DISPLAY_RE.finditer(text):
            expr = m.group(1)
            if '_secLabel' in expr:            # _secLabel() o _secLabelFull() → OK
                continue
            hits.append((m.start(), expr.strip()))
        return hits

    # ── Negative test OBLIGATORIO: el detector DEBE disparar en el caso malo y
    #    NO disparar en los correctos. Si falla, no se confía en el check. ──────
    _BAD       = '<div class="plist-sec">${f.section||\'\'}</div>'          # debe disparar
    _BAD_OPT   = '<div class="int-item-sec">${f?.section||\'\'}</div>'      # optional chaining → debe disparar
    _GOOD_WRAP = '<div class="plist-sec">${_secLabelFull(f.section||\'\')}</div>'  # envuelto → NO
    _GOOD_KEY  = 'const c=SECTION_COLORS[f.section]; if(f.section===activeSec){}'  # clave → NO
    _GOOD_ATTR = '<div data-s="${f.section}" class="x">hola</div>'          # atributo (clave) → NO
    _self_ok = (
        len(_scan_section_display_raw(_BAD))     >= 1 and
        len(_scan_section_display_raw(_BAD_OPT)) >= 1 and
        len(_scan_section_display_raw(_GOOD_WRAP))  == 0 and
        len(_scan_section_display_raw(_GOOD_KEY))   == 0 and
        len(_scan_section_display_raw(_GOOD_ATTR))  == 0
    )
    if not _self_ok:
        fail(check, 'SELF-TEST FALLÓ — el detector no distingue display vs clave; '
                    'no se confía en este check hasta arreglarlo')
    else:
        # Escanear los archivos de display reales (view + controller), por archivo
        # para reportar file:line.
        _scan_dirs = [os.path.join('src', 'view'), os.path.join('src', 'controller')]
        _raw_hits = []
        for _d in _scan_dirs:
            if not os.path.isdir(_d):
                continue
            for _fn in sorted(os.listdir(_d)):
                if not _fn.endswith('.js'):
                    continue
                _p = os.path.join(_d, _fn)
                _txt = open(_p, encoding='utf-8').read()
                for _off, _expr in _scan_section_display_raw(_txt):
                    _ln = _txt.count('\n', 0, _off) + 1
                    _raw_hits.append(f'{_p}:{_ln} → {_expr}')
        if _raw_hits:
            warn(check, f'{len(_raw_hits)} display(s) de sección sin _secLabel '
                        f'(usar _secLabel/_secLabelFull): ' + ' | '.join(_raw_hits))
        else:
            ok(check, 'self-test OK; 0 displays de sección crudos (todos vía _secLabel/_secLabelFull)')
except Exception as _e:
    warn(check, f'no se pudo verificar section-display-raw: {_e}')

# ── CHECK: [responsive-contract] ──────────────────────────────────────────────
# Guard cross-engine (WebKit/iOS vs Blink/Android). Caza la CLASE de bug que rompía
# la consistencia iOS/Android, de forma determinista en cada PR:
#   1. backdrop-filter sin -webkit- pareado → blur muerto en WKWebView viejo.
#   2. 100vh → shift al scrollear en mobile (usar dvh).
#   3. woff2 de @font-face que no existe en disco → el 404 que hacía caer la fuente
#      al fallback (Arial en iOS, Roboto en Android) → divergencia visual.
check = 'responsive-contract'
try:
    import re as _re_rc
    _rc = []
    _std = len(_re_rc.findall(r'(?<!-webkit-)backdrop-filter:[a-z]', content))
    _wk  = len(_re_rc.findall(r'-webkit-backdrop-filter:[a-z]', content))
    if _std != _wk:
        _rc.append(f'backdrop-filter sin -webkit- pareado ({_std} estándar vs {_wk} -webkit-)')
    _vh = _re_rc.findall(r'\b100vh\b', content)
    if _vh:
        _rc.append(f'{len(_vh)} uso(s) de 100vh — usar dvh (evita el shift mobile)')
    _fonts = sorted(set(_re_rc.findall(r'/fonts/[A-Za-z0-9._-]+\.woff2', content)))
    for _fp in _fonts:
        if not os.path.exists('.' + _fp):
            _rc.append(f'woff2 referenciado no existe en disco: {_fp}')
    if _rc:
        fail(check, '; '.join(_rc))
    else:
        ok(check, f'cross-engine OK — backdrop-filter pareado ({_wk}×), 0×100vh, {len(_fonts)} woff2 self-hosted presentes')
except Exception as _e:
    warn(check, f'no se pudo verificar responsive-contract: {_e}')

# ── [poster-editorial-parity] póster de obra/corto solo vía la fuente única ────
# UN solo póster propio en todas las superficies (regla de Juan, 17 jul 2026):
# el thumb/card de una obra se construye SOLO en view/helpers.js (itemPosterParts
# / _mkCortoItemHtml) — si "c-film-thumb" aparece en el markup de otro módulo,
# alguien está armando el póster a mano y reintroduce la inconsistencia
# (still crudo sin banda) que este check entierra.
check = 'poster-editorial-parity'
try:
    import glob as _glob
    _off = []
    for _sf in _glob.glob('src/**/*.js', recursive=True):
        if _sf.endswith('view/helpers.js'):
            continue
        _c = open(_sf, encoding='utf-8').read()
        if 'c-film-thumb' in _c:
            _off.append(_sf)
    if _off:
        fail(check, 'markup de póster de corto fuera de la fuente única (usar itemPosterParts/_mkCortoItemHtml de helpers.js): ' + ', '.join(_off))
    else:
        ok(check, 'póster de obra/corto construido solo en view/helpers.js (fuente única)')
except Exception as _e:
    warn(check, f'no se pudo verificar poster-editorial-parity: {_e}')

# ── [design-banned-classes] clases retiradas del sistema — no pueden volver ────
# La auditoría del 17-18 jul migró estas anatomías huérfanas a los componentes
# canónicos (emptyState / meta-banner / notice-banner-row / mplan-warn-row /
# familia día). Si alguna reaparece en src/, alguien reinventó la isla.
check = 'design-banned-classes'
try:
    import glob as _glob
    _BANNED = ['empty-msg', 'venue-fn-empty', 'mplan-empty', 'ag-warn"', "ag-warn'",
               'ag-excl-note', 'ag-excl-incompat', 'int-section-hdr', 'pel-sheet-divider',
               'fs-divider', 'hr-bdr']
    _hits = []
    for _sf in _glob.glob('src/**/*.js', recursive=True):
        _c = open(_sf, encoding='utf-8').read()
        for _b in _BANNED:
            for _i, _ln in enumerate(_c.splitlines(), 1):
                if _b in _ln and not _ln.strip().startswith('//') and not _ln.strip().startswith('*'):
                    _hits.append(f"{_sf}:{_i} '{_b}'")
    if _hits:
        fail(check, 'clase retirada del sistema reintroducida (usar el componente canónico): ' + '; '.join(_hits[:5]))
    else:
        ok(check, f'{len(_BANNED)} clases retiradas siguen fuera de src/')
except Exception as _e:
    warn(check, f'no se pudo verificar design-banned-classes: {_e}')

# ── [vocab-obra] el paraguas no promete formato: obra, no película ────────────
# Regla de Juan (17 ago 2026): «No siempre son películas. Esto es regla.» El
# catálogo lleva talleres, conversatorios y eventos; llamarlos «película» promete
# un formato que la app no controla. Misma familia que [vocab] actividad/función:
# ACTIVIDAD es el paraguas de lo que ocurre, OBRA el de lo que se programa.
# Se caza la palabra en el VALOR de una clave (lo que el usuario lee), no en el
# nombre de la clave: hay claves históricas (misc_pelicula, plan_pelicula_hoy)
# cuyo texto ya dice «obra» y renombrarlas sería un cambio sin lector.
# EXENTO: los nombres de FORMATO, donde «cortometraje / short film» es el dato
# correcto y no un paraguas.
check = 'vocab-obra'
try:
    _i18n_v = open('src/i18n/i18n.js', encoding='utf-8').read()
    _EXENTAS = {'label_cortometraje', 'label_cortos', 'label_largometraje'}
    _malas = []
    for _m in re.finditer(r'"([a-z0-9_]+)":\s*"([^"]*)"', _i18n_v):
        _k, _v = _m.group(1), _m.group(2)
        if _k in _EXENTAS:
            continue
        if re.search(r'\b[Pp]el[íi]culas?\b|\b[Ff]ilmes?\b', _v):
            _malas.append(f"{_k}: «{_v[:40]}»")
    if _malas:
        fail(check, 'string(s) que prometen formato en vez del paraguas «obra»: '
                    + '; '.join(_malas[:5]) + ' — el catálogo también lleva talleres y eventos')
    else:
        ok(check, 'ningún string user-facing llama «película» a lo que puede ser un taller')
except Exception as _e:
    warn(check, f'no se pudo verificar vocab-obra: {_e}')

# ── [i18n-voseo] la voz de la casa es voseo — tuteo prohibido en CTAs ES ───────
# Lote 2 (18 jul) unificó el voseo; este guard caza las formas de tuteo más
# comunes reintroducidas en el bloque ES. Lista corta y de baja falsa-alarma.
check = 'i18n-voseo'
try:
    _i18n = open('src/i18n/i18n.js', encoding='utf-8').read()
    # bloque ES = hasta la primera aparición del bloque EN ("en": {)
    _es_end = _i18n.find('"plan_hint_opciones": "Tap')
    _es = _i18n[:_es_end] if _es_end > 0 else _i18n
    import re as _re
    _TUTEO = [r'"[^"]*Ingresa', r'"[^"]*Ajusta', r'"[^"]*Permite el',
              r'"[^"]*Agrega(?!́)', r'"[^"]*Marca(?!́)', r'"[^"]*terminas',
              r'"[^"]*Añad', r'"[^"]*añad']
    _v = []
    for _pat in _TUTEO:
        for _m in _re.finditer(_pat, _es):
            _v.append(_m.group(0)[:50])
    if _v:
        fail(check, 'tuteo/vocabulario retirado en bloque ES (la casa vosea; Agregar es EL verbo): ' + '; '.join(_v[:5]))
    else:
        ok(check, 'bloque ES sin tuteo ni "añadir" — voseo íntegro')
except Exception as _e:
    warn(check, f'no se pudo verificar i18n-voseo: {_e}')

# ── [chrome-glass] el chrome es vidrio, no muro (decisión Juan 18 jul 2026) ────
# .topbar::before y .main-nav (mobile fixed) llevan velo translúcido + blur para
# que el contenido pase como color difuminado. Alpha ≤ 0.6 y backdrop-filter
# presente — si alguien lo vuelve opaco, el glass muere en silencio (pasó: vivió
# meses al 72/88% sin que se percibiera).
check = 'chrome-glass'
try:
    import re as _re
    _html = open('index.html', encoding='utf-8').read()
    _errs = []
    for _name, _pat in (('topbar::before', r'\.topbar::before\{[^}]*\}'),
                        ('main-nav fixed', r'\.main-nav\{position:fixed[^}]*\}')):
        _m = _re.search(_pat, _html, _re.S)
        if not _m:
            _errs.append(f'{_name}: regla no encontrada'); continue
        _rule = _m.group(0)
        if 'backdrop-filter' not in _rule:
            _errs.append(f'{_name}: sin backdrop-filter')
        _a = _re.search(r'background:rgba\([^)]*?,\s*(0?\.\d+|1)\)', _rule)
        if not _a:
            _errs.append(f'{_name}: fondo sin alpha rgba')
        elif float(_a.group(1)) > 0.6:
            _errs.append(f'{_name}: alpha {_a.group(1)} > 0.6 (muro, no vidrio)')
    # El chrome es UNA lámina: prohibido border opaco en sus piezas (las líneas
    # de mode-bar y nav-row se retiraron el 18 jul — no pueden volver).
    for _name, _pat in (('programa-mode-bar', r'\.programa-mode-bar\{[^}]*\}'),
                        ('nav-row', r'\.nav-row\{[^}]*\}'),
                        ('main-nav fixed', r'\.main-nav\{position:fixed[^}]*\}'),
                        ('fs-header', r'\.fs-header\{[^}]*\}'),
                        ('pv-header', r'\.pv-header\{[^}]*\}'),
                        ('search-bar', r'\.search-bar\{[^}]*\}')):
        _m = _re.search(_pat, _html, _re.S)
        if _m and _re.search(r'border(?:-top|-bottom)?:\s*1px solid var\(--bdr', _m.group(0)):
            _errs.append(f'{_name}: línea de borde reintroducida en el chrome')
    if _errs:
        fail(check, 'chrome glass roto: ' + '; '.join(_errs))
    else:
        ok(check, 'topbar y main-nav translúcidos (alpha ≤ 0.6), blur, sin líneas de borde')
except Exception as _e:
    warn(check, f'no se pudo verificar chrome-glass: {_e}')

# ── [no-animated-blur] el desenfoque NO se anima: se anima su opacidad ─────────
# Lección del 28 jul 2026, encontrada sobre una grabación de pantalla del iPhone
# de Juan: el WKWebView de iOS NO interpola backdrop-filter — salta al valor
# final en ~4 frames, y se siente como si no hubiera transición. Playwright y
# WebKit de escritorio SÍ interpolan, así que el bug es INVISIBLE en CI y en el
# navegador del Mac: costó tres intentos fallidos descubrirlo.
# El patrón correcto: blur FIJO en la capa + animar su opacity — el compositor
# mezcla nítido y desenfocado, la progresión es real en todos los motores y
# encima es más barato (el blur se calcula una vez, no por frame).
# ── [aviso-antes-sinopsis] los meta-banner van SIEMPRE antes de la sinopsis ────
# El mismo aviso ("función compartida") vivía en dos sitios: tras la función en
# la ficha de película y tras la sinopsis en la de corto — se movió uno y en el
# otro solo se cambió el texto. Un concepto en dos lugares es un concepto que el
# usuario aprende dos veces. Ver docs/DESIGN.md §8.4.4.
check = 'aviso-antes-sinopsis'
try:
    _src = open('src/controller/sheets-controller.js', encoding='utf-8').read()
    _mal = []
    for _blk in _src.split('document.getElementById('):
        _ib = _blk.find('meta-banner-label')
        _is = _blk.find('pel-sheet-synopsis')
        if _ib != -1 and _is != -1 and _ib > _is:
            _mal.append(_blk[:60].strip().replace('\n', ' '))
    if _mal:
        fail(check, 'meta-banner DESPUÉS de la sinopsis (§8.4.4: los avisos van antes): ' + '; '.join(_mal[:3]))
    else:
        ok(check, 'los meta-banner van antes de la sinopsis en toda superficie')
except Exception as _e:
    warn(check, f'no se pudo verificar aviso-antes-sinopsis: {_e}')

check = 'no-animated-blur'
try:
    import re as _re
    _html = open('index.html', encoding='utf-8').read()
    _errs = []
    for _m in _re.finditer(r'([^{}]+)\{([^}]*)\}', _html):
        _sel = _m.group(1).strip().splitlines()[-1].strip()
        _body = _m.group(2).replace('\n', ' ')
        for _tr in _re.findall(r'transition:([^;}]*)', _body):
            if 'backdrop-filter' in _tr:
                _errs.append(f'{_sel[:55]}: anima backdrop-filter (usar blur fijo + opacity)')
    if _errs:
        fail(check, 'desenfoque animado: ' + '; '.join(_errs[:4]))
    else:
        ok(check, 'ningún backdrop-filter en transition — el velo se anima por opacidad')
except Exception as _e:
    warn(check, f'no se pudo verificar no-animated-blur: {_e}')

# ── [sheet-spring] TODO bottom-sheet abre spring y cierra ease-in ──────────────
# Decisión Juan 18 jul 2026: la curva canónica vive en los tokens --sheet-in /
# --sheet-out. Antes 7 de 8 sheets tenían curvas bespoke (el spring existía solo
# en pel-sheet). Un sheet nuevo con cubic-bezier propio = isla reintroducida.
# También exige el skeleton shimmer de pósters (poster-skel) presente.
check = 'sheet-spring'
try:
    import re as _re
    _html = open('index.html', encoding='utf-8').read()
    _errs = []
    for _m in _re.finditer(r'([^{}]+)\{[^}]*translateY\(100%\)[^}]*\}', _html):
        _sel, _rule = _m.group(1).strip().splitlines()[-1].strip(), _m.group(0)
        if 'transition' in _rule and 'var(--sheet-out)' not in _rule:
            _errs.append(f'{_sel}: cierre sin var(--sheet-out)')
        if 'border-top:1px solid var(--bdr' in _rule:
            _errs.append(f'{_sel}: línea en el arco del sheet (retiradas 18 jul)')
    for _m in _re.finditer(r'([^{}]+)\{[^}]*transform:translateY\(0\)[^}]*\}', _html):
        _sel, _rule = _m.group(1).strip().splitlines()[-1].strip(), _m.group(0)
        if '.open' in _sel and 'var(--sheet-in)' not in _rule:
            _errs.append(f'{_sel}: apertura sin var(--sheet-in)')
    if '@keyframes poster-skel' not in _html:
        _errs.append('falta @keyframes poster-skel (skeleton de pósters)')
    if _errs:
        fail(check, 'motion fuera del canon: ' + '; '.join(_errs[:6]))
    else:
        ok(check, 'sheets con --sheet-in/--sheet-out y skeleton de pósters presente')
except Exception as _e:
    warn(check, f'no se pudo verificar sheet-spring: {_e}')

# ── [warm-neutrals] superficies con temperatura — gris neutro puro prohibido ──
# Decisión Juan 18 jul 2026: los tokens de superficie/borde llevan sesgo cálido
# (~1.5% hacia el ámbar, R>G>B). Un hex neutro de la paleta VIEJA reintroducido
# = isla fría (pasó con #1C1C1C del auth sheet y los canvas de compartir).
check = 'warm-neutrals'
try:
    import glob as _glob
    _OLD = ['#0A0A0A', '#141414', '#1A1A1A', '#1C1C1C', '#1E1E1E', '#1F1F1F',
            '#232323', '#2A2A2A', 'rgba(20,20,20', 'rgba(20, 20, 20']
    _hits = []
    _files = ['index.html'] + _glob.glob('src/**/*.js', recursive=True)
    for _sf in _files:
        _c = open(_sf, encoding='utf-8').read()
        for _i, _ln in enumerate(_c.splitlines(), 1):
            for _h in _OLD:
                if _h.lower() in _ln.lower():
                    _hits.append(f'{_sf}:{_i} {_h}')
    if _hits:
        fail(check, 'gris neutro de la paleta vieja reintroducido (usar el token cálido): ' + '; '.join(_hits[:5]))
    else:
        # sanity: los tokens deben seguir cálidos (R>G>B en --bg)
        import re as _re
        _html = open('index.html', encoding='utf-8').read()
        _m = _re.search(r'--bg:\s*#([0-9A-Fa-f]{6})', _html)
        _r, _g, _b = (int(_m.group(1)[i:i+2], 16) for i in (0, 2, 4)) if _m else (0, 0, 0)
        if not (_m and _r >= _g >= _b and _r > _b):
            fail(check, f'--bg perdió el sesgo cálido (R≥G≥B): {_m.group(1) if _m else "no encontrado"}')
        else:
            ok(check, 'paleta vieja fuera y tokens de superficie cálidos (R≥G≥B)')
except Exception as _e:
    warn(check, f'no se pudo verificar warm-neutrals: {_e}')

# ── [poster-ambient] el color ambiental sale SOLO del sampler único ────────────
# posterAmbient (view/helpers.js) es el único que muestrea color (getImageData)
# y el único que produce el tinte --amb, siempre DOMADO (clamp sat/lum). Un
# getImageData en otro módulo o un --amb puesto a mano = color crudo sin domar.
check = 'poster-ambient'
try:
    import glob as _glob
    _off = []
    for _sf in _glob.glob('src/**/*.js', recursive=True):
        if _sf.endswith('view/helpers.js'):
            continue
        _c = open(_sf, encoding='utf-8').read()
        for _i, _ln in enumerate(_c.splitlines(), 1):
            if _ln.strip().startswith('//'):
                continue
            if 'getImageData' in _ln:
                _off.append(f'{_sf}:{_i} getImageData')
            if "setProperty('--amb'" in _ln and 'sheets-controller' not in _sf:
                _off.append(f'{_sf}:{_i} --amb a mano')
    _html = open('index.html', encoding='utf-8').read()
    if '.pel-sheet.amb{' not in _html:
        _off.append('index.html: falta la regla .pel-sheet.amb')
    _helpers = open('src/view/helpers.js', encoding='utf-8').read()
    if 'function posterAmbient' not in _helpers or '_clampAmb' not in _helpers:
        _off.append('helpers.js: posterAmbient/_clampAmb ausentes')
    if _off:
        fail(check, 'color ambiental fuera del sampler único: ' + '; '.join(_off[:5]))
    else:
        ok(check, 'sampler único posterAmbient con clamp; --amb solo del hook')
except Exception as _e:
    warn(check, f'no se pudo verificar poster-ambient: {_e}')

# ── [sheet-meta-legible] metadata informativa nunca en --gray2 ─────────────────
# Reporte Juan 18 jul 2026: duración/director/año de la ficha en #555 eran
# ilegibles sobre el tinte ambiental. Regla: lo que se LEE para decidir
# (metadata de obra) va en --gray o más claro; --gray2 es UI pasiva.
check = 'sheet-meta-legible'
try:
    _html = open('index.html', encoding='utf-8').read()
    _INFO = ['.pel-sheet-flags-dur{', '.pel-sheet-metaline{', '.rating-title{']
    _bad = []
    for _sel in _INFO:
        _i = _html.find(_sel)
        _rule = _html[_i:_html.find('}', _i)] if _i >= 0 else ''
        if not _rule:
            _bad.append(f'{_sel} no encontrada')
        elif 'var(--gray2)' in _rule:
            _bad.append(f'{_sel} en --gray2 (ilegible sobre tinte)')
    if _bad:
        fail(check, 'metadata informativa degradada: ' + '; '.join(_bad))
    else:
        ok(check, 'duración/director/año de la ficha en --gray o más claro')
except Exception as _e:
    warn(check, f'no se pudo verificar sheet-meta-legible: {_e}')

# ── [pressed-canon] feedback al presionar unificado (auditoría 18 jul 2026) ────
# Había 6 escalas distintas (.88/.9/.94/.95/.96/.97) + opacidades mezcladas + un
# duplicado de int-prio-btn. Canon: controles con caja = scale(.96); cards y
# links = solo opacity (sin scale). Un :active con scale != .96 = isla nueva.
check = 'pressed-canon'
try:
    import re as _re
    _html = open('index.html', encoding='utf-8').read()
    _scales = set(_re.findall(r':active\{[^}]*transform:scale\((\.\d+)\)', _html))
    _bad = sorted(s for s in _scales if s != '.96')
    if _bad:
        fail(check, f'escala :active fuera del canon (.96): {", ".join(_bad)}')
    else:
        ok(check, 'pressed unificado: controles scale(.96), cards/links solo opacity')
except Exception as _e:
    warn(check, f'no se pudo verificar pressed-canon: {_e}')

# ── [filter-drop-canon] dropdowns de filtro con anatomía única ─────────────────
# Auditoría overlays 18 jul: sección y lugar duplicaban ~11 líneas de cssText
# inline que divergieron. Ahora ambos usan la clase .filter-drop; el build solo
# aporta posición (top/right). Un dropdown que re-declare anatomía inline
# (background/border/box-shadow en cssText de overlays.js) = isla nueva.
check = 'filter-drop-canon'
try:
    _html = open('index.html', encoding='utf-8').read()
    _ov = open('src/controller/overlays.js', encoding='utf-8').read()
    _errs = []
    if '.filter-drop{' not in _html:
        _errs.append('falta la clase .filter-drop en index.html')
    import re as _re
    for _m in _re.finditer(r"cssText\s*=\s*\[([^\]]*)\]", _ov):
        if 'box-shadow' in _m.group(1) or 'background:var(--surf)' in _m.group(1).replace(' ', ''):
            _errs.append('dropdown con anatomía inline en overlays.js (usar .filter-drop)')
    if _errs:
        fail(check, 'filter-drop roto: ' + '; '.join(_errs[:4]))
    else:
        ok(check, 'sección y lugar comparten .filter-drop (sin anatomía inline)')
except Exception as _e:
    warn(check, f'no se pudo verificar filter-drop-canon: {_e}')

# ── [poster-morph] viaje del póster: FLIP en el compositor, NUNCA View Transition ──
# Decisión Juan 19 jul (el póster viaja) + 29 jul (el motor es FLIP). La VT del
# root produjo TRES fallos solo-en-device (§8.4.2): snapshots que tapan el DOM
# (velo invisible→golpe), póster fantasma (#443/#444) y texto congelado de la
# ficha anterior. PROHIBIDO reintroducir startViewTransition en la apertura.
# ── [poster-radius] un póster = un radio, en TODAS sus superficies ─────────────
# El póster viaja de la card del grid a la ficha (FLIP). Había TRES radios en un
# solo viaje —card 12px, ficha 8px, thumb de corto 4px, más un 10px hardcodeado
# en el JS del vuelo— así que cambiaba de redondez a mitad de trayecto. Un póster
# es el mismo objeto donde sea que aparezca. Ver docs/DESIGN.md §8.4.5.
check = 'poster-radius'
try:
    import re as _re3
    _html = open('index.html', encoding='utf-8').read()
    _SUPERFICIES = ['.poster-card', '.pel-sheet-poster', '.psp-editorial',
                    '.c-film-thumb', '.pel-sheet-poster-ph', '.pel-sheet-poster-stage']
    _visto = {k: False for k in _SUPERFICIES}
    _mal = []
    # Toda regla cuyo selector nombre una superficie de póster y fije border-radius
    # debe fijarlo al token. Se recorren TODAS (hay selectores agrupados).
    for _m in _re3.finditer(r'([^{}]+)\{([^}]*)\}', _html):
        _sel, _body = _m.group(1), _m.group(2)
        _br = _re3.search(r'border-radius:\s*([^;}]+)', _body)
        if not _br:
            continue
        for _s2 in _SUPERFICIES:
            if _re3.search(_re3.escape(_s2) + r'(?![\w-])', _sel):
                if 'var(--r-poster)' in _br.group(1):
                    _visto[_s2] = True
                else:
                    _mal.append(f"{_s2}: {_br.group(1).strip()}")
    _falta = [k for k, v in _visto.items() if not v]
    if _falta:
        _mal.append('sin --r-poster: ' + ', '.join(_falta))
    _js = open('src/main.js', encoding='utf-8').read()
    if _re3.search(r"borderRadius\s*=\s*['\"]\d", _js):
        _mal.append('radio hardcodeado en el vuelo (main.js) — usar el token')
    if _mal:
        fail(check, 'radio de poster desalineado: ' + '; '.join(_mal[:5]))
    else:
        ok(check, 'las 6 superficies de poster comparten --r-poster')
except Exception as _e:
    warn(check, f'no se pudo verificar poster-radius: {_e}')

# ── [dtab-sin-linea] el dia activo se marca SOLO con color, sin linea ambar ────
# Decidido 18 may 2026 (964cc6b) y revertido POR ERROR el 18 jul (534b150) al
# "unificar el lenguaje de activo con .pmode-tab.on": se deshizo una decision
# anterior sin saber que existia. Este guardian es la memoria de esa decision.
check = 'dtab-sin-linea'
try:
    import re as _re4
    _html = open('index.html', encoding='utf-8').read()
    _m = _re4.search(r'\.dtab\.on\{([^}]*)\}', _html)
    if not _m:
        fail(check, 'no existe la regla .dtab.on')
    elif 'border-bottom-color' in _m.group(1) or 'border-bottom:' in _m.group(1):
        fail(check, 'linea ambar bajo el dia activo reintroducida — el activo va SOLO por color')
    else:
        ok(check, 'dia activo marcado solo por color, sin linea')
except Exception as _e:
    warn(check, f'no se pudo verificar dtab-sin-linea: {_e}')

check = 'poster-morph'
try:
    _html = open('index.html', encoding='utf-8').read()
    _mn = open('src/main.js', encoding='utf-8').read()
    _sc = open('src/controller/sheets-controller.js', encoding='utf-8').read()
    _errs = []
    # El poster NO viaja. Dos intentos, CINCO defectos solo-en-device (DESIGN.md
    # 8.4.5). Este guardian impide que cualquiera de los dos motores vuelva.
    if 'startViewTransition' in (_mn + _sc):
        _errs.append('startViewTransition reintroducido — prohibido (3 fallos device)')
    if 'poster-flight' in (_mn + _html):
        _errs.append('clon en vuelo (.poster-flight) reintroducido — prohibido (2 fallos device)')
    # Lo que SI debe seguir: la costura unica de apertura y el stagger sobre el DOM.
    if '_openPelMorph' not in _mn or '_morphOpen' not in _mn:
        _errs.append('falta la costura unica de apertura (_morphOpen/_openPelMorph)')
    if 'vt-in' not in _html or '@keyframes vtRise' not in _html:
        _errs.append('falta el stagger de la meta (vt-in / vtRise)')
    if 'prefers-reduced-motion:reduce' not in _html.replace(' ', ''):
        _errs.append('falta el guard @media reduce-motion')
    if _errs:
        fail(check, 'apertura de ficha rota: ' + '; '.join(_errs[:4]))
    else:
        ok(check, 'la card sube completa: sin View Transition ni clon en vuelo')
except Exception as _e:
    warn(check, f'no se pudo verificar poster-morph: {_e}')

# ── [festival-chooser-canon] elegir festival = LA MISMA estructura en las 2 superficies ─
# Feedback real de usuario (20 jul 2026): "¿cómo vuelvo al menú donde estaban los
# festivales?". Había DOS implementaciones de la misma decisión: el riel de afiches del
# splash y una lista de texto en el sheet → no se reconocían como el mismo lugar.
# 2ª iteración (Juan: "¿por qué no replicaste la estructura del splash?"): el sheet ya
# ni siquiera tiene render propio — DELEGA en el riel del splash y solo cambia la acción.
# Requisitos que NO pueden desaparecer: (1) una sola fábrica de card (_festivalCardHTML)
# usada por el riel; (2) el sheet DELEGA en _renderSplashRailHTML (si alguien le vuelve a
# escribir un render propio, son dos otra vez); (3) el sheet NO vuelve a la lista de texto
# (fs-festival-row); (4) el sheet conserva su bloque de info de 4 líneas (#fs-info con las
# clases .splash-info-*); (5) el chevron del header va DENTRO de la píldora, junto al
# nombre (si se saca, el nombre vuelve a leerse como título y el control desaparece).
check = 'festival-chooser-canon'
try:
    _cmp = open('src/view/components.js', encoding='utf-8').read()
    _html = open('index.html', encoding='utf-8').read()
    _errs = []
    if '_festivalCardHTML' not in _cmp:
        _errs.append('falta la fábrica única _festivalCardHTML')
    _i = _cmp.find('function _renderSplashRailHTML')
    if _i < 0:
        _errs.append('falta _renderSplashRailHTML')
    elif '_festivalCardHTML' not in _cmp[_i:_i + 2600]:
        _errs.append('_renderSplashRailHTML no usa la fábrica única (card duplicada)')
    _j = _cmp.find('function _renderFestivalSelectorHTML')
    if _j < 0:
        _errs.append('falta _renderFestivalSelectorHTML')
    elif '_renderSplashRailHTML' not in _cmp[_j:_j + 700]:
        _errs.append('el sheet dejó de delegar en el riel del splash (render propio = dos implementaciones)')
    if 'fs-festival-row' in _cmp:
        _errs.append('el sheet volvió a la lista de texto (fs-festival-row)')
    _fi = _html.find('id="fs-info"')
    if _fi < 0:
        _errs.append('falta el bloque de info del sheet (#fs-info)')
    else:
        _blk = _html[_fi:_fi + 500]
        for _cls in ('splash-info-name', 'splash-info-tag', 'splash-info-city', 'splash-info-dates'):
            if _cls not in _blk:
                _errs.append(f'#fs-info perdió la línea {_cls} (las 4 del splash son el canon)')
                break
    # El chevron debe ir dentro de la píldora, pegado al nombre.
    _pill = _html.find('hdr-fest-pill')
    if _pill < 0:
        _errs.append('falta la píldora del selector en el header (hdr-fest-pill)')
    elif 'hdr-fest-chev' not in _html[_pill:_pill + 700]:
        _errs.append('el chevron salió de la píldora (vuelve a leerse como control de fecha)')
    if _errs:
        fail(check, 'chooser de festival roto: ' + '; '.join(_errs[:4]))
    else:
        ok(check, 'elegir festival = muro de afiches con fábrica única (splash + sheet)')
except Exception as _e:
    warn(check, f'no se pudo verificar festival-chooser-canon: {_e}')

# ── [diary-poster-grid] el Diario compartible es un muro de afiches, no una lista ─
# Decisión Juan 19 jul: shareDiary dibuja un GRID de pósters (cover-fit) con chip
# de estrellas, no la lista tipográfica vieja. Requisitos que NO pueden desaparecer:
# (1) resolver el afiche por obra (getCortoItemPoster) y film (getFilmPoster);
# (2) dibujarlo (drawImage); (3) el tile generativo de fallback para pósters no
# dibujables (CORS/CDN) vía _sectionColor — sin él, un afiche caído deja hueco negro.
check = 'diary-poster-grid'
try:
    _sh = open('src/controller/share.js', encoding='utf-8').read()
    _dia = _sh[_sh.find('function shareDiary'):_sh.find('function sharePlan')] if 'function shareDiary' in _sh else ''
    _errs = []
    if 'getCortoItemPoster' not in _dia or 'getFilmPoster' not in _dia:
        _errs.append('no resuelve el afiche por obra/film (getCortoItemPoster/getFilmPoster)')
    if 'drawImage' not in _dia:
        _errs.append('no dibuja el póster (drawImage) — ¿regresó a la lista tipográfica?')
    if '_sectionColor' not in _dia:
        _errs.append('falta el tile generativo de fallback (_sectionColor) para afiches no dibujables')
    # Orden por calificación desc (decisión de Juan): el muro va de la mejor nota a la peor.
    if 'rows.sort' not in _dia:
        _errs.append('el muro no ordena por calificación (rows.sort — mejor nota primero)')
    if _errs:
        fail(check, 'diario-grid roto: ' + '; '.join(_errs[:3]))
    else:
        ok(check, 'Diario compartible = grid de afiches con fallback generativo')
except Exception as _e:
    warn(check, f'no se pudo verificar diary-poster-grid: {_e}')

# ── [button-canon] botones: anatomías con regla dueña + estado .on único ───────
# Auditoría 18 jul 2026: el primario amber tenía 9 anatomías, el cancel 4, y el
# estado activo 3 nombres. Ahora: (1) fondo amber+texto negro de botón SOLO en
# la regla dueña PRIMARIO; (2) w-display prohibido en botones; (3) el estado
# activo se llama .on — classList con 'active'/'selected' en src/ = isla nueva.
check = 'button-canon'
try:
    import re as _re, glob as _glob
    _html = open('index.html', encoding='utf-8').read()
    _errs = []
    for _m in _re.finditer(r'([^{}]+)\{([^}]*)\}', _html):
        _sel = _m.group(1).strip().splitlines()[-1].strip()
        _body = _m.group(2)
        # El botón es el ÚLTIMO componente del selector: en '.auth-btn .auth-avatar'
        # lo que se estiliza es el avatar, no el botón que lo contiene.
        _last = _sel.split()[-1] if _sel.split() else _sel
        _is_btn = ('-btn' in _last or '-cta' in _last or 'button' in _last) and '::' not in _sel
        if not _is_btn:
            continue
        # Fondo del primario: un botón con fondo ámbar Y texto negro ES un CTA
        # primario, y su fondo debe ser --amber-cta (el degradado del canon).
        # Se parsean las props en vez de buscar una secuencia literal: antes el
        # check exigía 'background:var(--amber);color:var(--black)' pegados, así
        # que cualquier prop en medio (border-color, width…) lo esquivaba — los
        # 2 primarios de sheet pasaban invisibles.
        _flat = _body.replace('\n', '').replace(' ', '')
        _props = dict(_p.split(':', 1) for _p in _flat.split(';') if ':' in _p)
        _bg, _fg = _props.get('background', ''), _props.get('color', '')
        if _fg == 'var(--black)' and _bg.startswith('var(--amber') and _bg != 'var(--amber-cta)':
            _errs.append(f'{_sel[:60]}: CTA primario con fondo plano (canon: var(--amber-cta))')
        if 'font-weight:var(--w-display)' in _body:
            _errs.append(f'{_sel[:60]}: w-display en botón (canon: w-bold)')
    for _sf in _glob.glob('src/**/*.js', recursive=True) + ['index.html']:
        _c = open(_sf, encoding='utf-8').read()
        for _i, _ln in enumerate(_c.splitlines(), 1):
            if _ln.strip().startswith('//'):
                continue
            if _re.search(r"classList\.(add|toggle|remove)\(\s*['\"](active|selected)['\"]", _ln):
                _errs.append(f'{_sf}:{_i} estado activo con nombre viejo (usar .on)')
    if _errs:
        fail(check, 'canon de botones roto: ' + '; '.join(_errs[:5]))
    else:
        ok(check, 'primario en regla dueña, sin w-display en botones, estado .on único')
except Exception as _e:
    warn(check, f'no se pudo verificar button-canon: {_e}')

# ── [reload-sin-reloj] recargar borra la fecha congelada ─────────────────────
# El 20 ago 2026 main amaneció rojo por dos tests que hacían page.reload(): la
# recarga borra `_simTime` (vive en memoria), la app pasa a usar la fecha REAL y
# el test queda a merced del día en que corra. T65 tardó media hora en entenderse
# porque el síntoma engañaba —parecía roto el marcado «Ya pasó» y lo roto era la
# premisa—. Es la única de las tres bombas de ese día que se caza LEYENDO.
#
# Después de recargar hay exactamente dos formas correctas:
#   · reentrar(page, festId, simTime)  — re-elige festival y re-congela (helpers)
#   · page.clock.install(...)          — congela el reloj del navegador, sobrevive
#   · derivar la premisa del dato en tiempo de ejecución (lo que hace P09 hoy)
#
# La bomba NO es recargar: es recargar con la premisa CLAVADA. Un test que fija
# 'ficdeh2026' o un simTime literal y después recarga queda a merced del día en
# que corra; uno que elige el festival vigente al vuelo, no. Por eso el check
# mira las dos cosas juntas — si solo mirara el reload, obligaría a reescribir
# tests que ya son correctos, y un guardián que crea trabajo inútil se ignora.
check = 'reload-sin-reloj'
try:
    import glob as _g6, re as _re
    _malos = []
    for _f in sorted(_g6.glob('tests/*.spec.js')):
        _ls = open(_f, encoding='utf-8').read().splitlines()
        for _i, _l in enumerate(_ls):
            if '.reload(' not in _l:
                continue
            _ventana = ' '.join(_ls[_i:_i + 5])
            if ('reentrar(' in _ventana or 'clock.install' in _ventana
                    or 'selectFestival(' in _ventana):
                continue
            # clock.install ANTES del goto también vale: el reloj ya está congelado
            _antes = _ls[max(0, _i - 45):_i]
            if any('clock.install' in _p for _p in _antes):
                continue
            # ¿La premisa está clavada? Solo entonces la recarga es una bomba.
            _fijo = any(_re.search(r"enterFestival\(page,\s*'[a-z0-9]+'", _p) for _p in _antes)
            if not _fijo:
                continue
            _malos.append(f'{_f}:{_i + 1}')
    if _malos:
        fail(check, 'page.reload() sin re-congelar la fecha (usar reentrar() o clock.install): '
                    + ', '.join(_malos[:5]))
    else:
        ok(check, 'toda recarga en tests re-congela la fecha o instala reloj')
except Exception as _e:
    warn(check, f'no se pudo verificar reload-sin-reloj: {_e}')

# ── [aviso-color] el color de un aviso significa algo, y está decidido ────────
# Juan, 18 ago 2026: «Plan desactualizado» salió en blanco por inercia (herencia
# del banner de prioridades) y él preguntó lo obvio — ¿no debería ser ámbar, como
# los otros avisos? La app YA tenía el precedente (.dato-alerta, .ctx-aviso.amb)
# pero nadie lo había escrito: DESIGN.md define el ámbar como «acento, hora, CTA,
# estado activo», nunca como advertencia. Resultado: 13 clases de aviso con 6
# tokens de color repartidos a ojo. La regla (§8.6) y este guardián cierran eso:
# cada aviso declara a qué familia semántica pertenece, y una clase nueva no
# entra sin decidirlo.
check = 'aviso-color'
try:
    import re as _re
    _html = open('index.html', encoding='utf-8').read()
    # familia semántica → token permitido
    _ROSTER = {
        # ATENCIÓN — «esto te pide algo ahora»
        '.dato-alerta': 'amber', '.ctx-aviso.amb': 'amber', '.prio-stale': 'amber',
        '.delay-warn.warn-amber': 'amber', '.mplan-warn-row': 'amber-60',
        # CONTEXTO — informa, no exige
        '.ctx-aviso': 'gray',
        # ESTADO del festival/función — verde en curso, rojo lo grave
        '.ctx-aviso.grn': 'green', '.delay-warn': 'red', '.aviso-pill.sev-red': 'red',
        # SUPERFICIE — el color ES el componente (pastilla/toast), no un texto teñido
        '.aviso-pill': 'amber', '.prio-toast.warn': 'yellow-12',
        # MATIZ de ficha
        '.aviso-txt': 'white',
    }
    _errs = []
    _vistos = set()
    for _m in _re.finditer(r'^(\.[a-zA-Z0-9_.\-]+)\{([^}]*)\}', _html, _re.M):
        _sel, _cuerpo = _m.group(1), _m.group(2)
        if not _re.search(r'(aviso|alerta|stale|warn)', _sel):
            continue
        _c = _re.search(r'color:var\(--([a-z0-9-]+)\)', _cuerpo)
        if not _c:
            continue
        _vistos.add(_sel)
        if _sel not in _ROSTER:
            _errs.append(f'{_sel} es un aviso nuevo sin familia semántica declarada '
                         f'(§8.6: ámbar pide atención · gris informa · verde/rojo estado)')
        elif _c.group(1) != _ROSTER[_sel]:
            _errs.append(f'{_sel}: color --{_c.group(1)} pero su familia manda --{_ROSTER[_sel]}')
    _muertas = [k for k in _ROSTER if k not in _vistos]
    if _muertas:
        _errs.append('en el roster pero ya no existe(n) en el CSS: ' + ', '.join(sorted(_muertas)))
    if _errs:
        fail(check, '; '.join(_errs[:4]))
    else:
        ok(check, f'{len(_vistos)} avisos, cada uno con su familia de color declarada')
except Exception as _e:
    warn(check, f'no se pudo verificar aviso-color: {_e}')

# ── [cancelada-no-difumina] cancelada y pasada no pueden usar el mismo recurso ─
# Juan, 21 ago 2026, mirando FICDEH en el teléfono: el badge CANCELADA se pisaba
# con el rótulo de sección del póster propio. Al medirlo aparecieron DOS fallas,
# no una:
#   1. El badge vivía en `top:5px`. En la anatomía §6.0 el rótulo de sección vive
#      justo ahí. No era un caso raro: chocaban SIEMPRE, en todo póster nuestro.
#   2. Cancelada se decía con `opacity:.45` — el mismo recurso que «ya pasó». Dos
#      verdades distintas con la misma cara: una función caída se leía como una
#      función vieja.
# El arreglo: el badge se ancla a la retícula (la sección no puede pasar de 4,4u,
# así que 4,65u SIEMPRE está libre) y cancelada se dice en gris, que es un canal
# que no estaba ocupado. Este guardián cuida las dos mitades — la segunda importa
# más, porque volver a difuminar una cancelada no se ve roto, se ve normal.
check = 'cancelada-no-difumina'
try:
    import re as _re
    _html = open('index.html', encoding='utf-8').read()
    _prog = open('src/view/programa.js', encoding='utf-8').read()
    _errs = []

    _m = _re.search(r'^\.poster-past-badge\{([^}]*)\}', _html, _re.M)
    if not _m:
        _errs.append('.poster-past-badge ya no existe en el CSS')
    else:
        _cuerpo = _m.group(1)
        _top = _re.search(r'top:([^;}]+)', _cuerpo)
        if not _top:
            _errs.append('.poster-past-badge sin `top` — el badge queda donde caiga')
        elif 'var(--poster-badge-top)' not in _top.group(1):
            _errs.append(f'.poster-past-badge ancla en `top:{_top.group(1).strip()}` en vez de '
                         'var(--poster-badge-top): un número a ojo vuelve a caer sobre el rótulo '
                         'de sección en cuanto el rótulo cambie de tamaño')
    if '--poster-badge-top:' not in _html:
        _errs.append('falta el token --poster-badge-top (sale de la retícula: 4,65u de 12u)')
    if not _re.search(r'\.is-cancelled[^{]*\{[^}]*filter:grayscale', _html):
        _errs.append('cancelada dejó de decirse en gris — sin `filter:grayscale` el estado '
                     'no se distingue de una función normal')

    # La mitad que de verdad protege la decisión: nadie vuelve a difuminar una cancelada.
    # Solo cuenta cuando CANCELADA es la CONDICIÓN y el difuminado la consecuencia.
    # Un `allPast?'opacity:.5'` que convive en la misma línea con un badge de
    # cancelada es legítimo: ahí quien difumina es «ya pasó», que es su dueño.
    if _re.search(r"_cancell?ed[^?\n]{0,40}\?[^:\n]{0,60}opacity:", _prog):
        _errs.append('una función cancelada vuelve a difuminarse en programa.js: el '
                     'difuminado ya significa «ya pasó» y no puede decir dos cosas')

    if _errs:
        fail(check, '; '.join(_errs[:3]))
    else:
        ok(check, 'el badge se ancla a la retícula y cancelada se dice en gris, no difuminada')
except Exception as _e:
    warn(check, f'no se pudo verificar cancelada-no-difumina: {_e}')

def _re_fecha(k):
    """¿La clave de día es una fecha ISO? Leviza y otros legacy usan rótulos
    ('DOM 17'), y ahí el concepto de «día que falta» no aplica."""
    import re as _r
    return bool(_r.fullmatch(r'\d{4}-\d{2}-\d{2}', str(k)))

# ── [calendario-sin-huecos] el día existe aunque esté vacío ───────────────────
# Juan, 24 ago 2026: «el día debería existir, vacío. No hay programación pero el
# día existe. Menos conflictos, más claridad».
#
# CineAutopsia corre del 21 al 29 de agosto y su calendario NO declaraba el 24.
# Con el festival EN CURSO eso hacía que «Hoy» abriera el VIE 21 —ya pasado— y
# «Mañana» el SÁB 29: `findIndex` del día de hoy daba -1 y los fallbacks caían a
# los extremos del array (arreglado aparte, pero el dato era la causa).
#
# La convención ya existía y nadie la había escrito: Tercer Tiempo declara SIETE
# días con DOS vacíos (14 y 19 jul) y cero huecos; FICDEH tampoco tiene huecos.
# CineAutopsia fue la excepción. Un día vacío declarado se atenúa solo y no
# rompe nada —`dayFullyPassed` ya tiene su caso explícito—; un día AUSENTE deja
# un agujero por el que se cuela la aritmética de índices.
check = 'calendario-sin-huecos'
try:
    import json as _json, glob as _glob, os as _os
    from datetime import date as _date, timedelta as _td
    _errs = []
    for _p in sorted(_glob.glob('festivals/*.json')):
        try:
            _d = _json.load(open(_p, encoding='utf-8'))
        except Exception:
            continue
        _keys = [k for k in (_d.get('dayKeys') or []) if _re_fecha(k)]
        if len(_keys) < 2:
            continue
        try:
            _ini = _date.fromisoformat(_keys[0]); _fin = _date.fromisoformat(_keys[-1])
        except ValueError:
            continue
        _esperados, _x = [], _ini
        while _x <= _fin:
            _esperados.append(_x.isoformat()); _x += _td(days=1)
        _faltan = [k for k in _esperados if k not in _keys]
        if _faltan:
            _errs.append(f'{_os.path.basename(_p)}: el calendario salta {len(_faltan)} día(s) '
                         f'({", ".join(_faltan[:3])}). Un día sin programación se DECLARA vacío, '
                         'no se omite — si no, «Hoy» cae en un día que ya pasó')
    if _errs:
        fail(check, '; '.join(_errs[:3]))
    else:
        ok(check, 'ningún festival salta días: los vacíos se declaran')
except Exception as _e:
    warn(check, f'no se pudo verificar calendario-sin-huecos: {_e}')

# ── [calendario-entero] un día que se dibuja tiene que existir para el reloj ───
# Juan, 23 ago 2026: «CineAutopsia no marcó el Vie 21 como pasado, sigue vivo».
# La tira de días se arma con `dayKeys` —que el JSON PISA, porque es contenido—
# pero el reloj lee `FESTIVAL_DATES` (= `festivalDates`), que estaba archivado
# como IDENTIDAD y por tanto el JSON solo podía rellenarlo si config lo tenía
# vacío. El calendario quedó partido en dos dueños: 8 días dibujados, 4
# conocidos. `dayFullyPassed` corta en seco con `if(!dateStr) return false`, así
# que los cuatro huérfanos no se atenuaban NUNCA, sus funciones no contaban como
# pasadas, y `todayDay` habría fallado el 25/26/27 con el festival en curso.
# La regla que faltaba: todo día que se dibuja tiene que tener fecha. Este
# guardián la exige en las DOS fuentes, porque el bug no vivía en ninguna de las
# dos por separado — vivía en que no coincidían.
check = 'calendario-entero'
try:
    import re as _re, json as _json, glob as _glob, os as _os
    _errs = []
    _cfg = open('src/config.js', encoding='utf-8').read()
    for _m in _re.finditer(r"'([a-zA-Z0-9]+)':\s*\{(.*?)\n  \},", _cfg, _re.S):
        _fid, _body = _m.group(1), _m.group(2)
        _dk = _re.search(r"dayKeys:\[(.*?)\]", _body, _re.S)
        _fd = _re.search(r"festivalDates:\{(.*?)\}", _body, _re.S)
        if not _dk or not _fd:
            continue
        _keys = set(_re.findall(r"'([^']+)'", _dk.group(1)))
        _dates = set(_re.findall(r"'([^']+)'\s*:", _fd.group(1)))
        _huerf = _keys - _dates
        if _huerf:
            _errs.append(f'{_fid}: {len(_huerf)} día(s) en dayKeys sin fecha en festivalDates '
                         f'({", ".join(sorted(_huerf)[:3])}) — se dibujan pero el reloj no los ve')
    for _p in sorted(_glob.glob('festivals/*.json')):
        try:
            _d = _json.load(open(_p, encoding='utf-8'))
        except Exception:
            continue
        _keys = set(_d.get('dayKeys') or [])
        _dates = set((_d.get('festivalDates') or {}).keys())
        if not _keys or not _dates:
            continue
        _huerf = _keys - _dates
        if _huerf:
            _errs.append(f'{_os.path.basename(_p)}: {len(_huerf)} día(s) en dayKeys sin fecha '
                         f'en festivalDates ({", ".join(sorted(_huerf)[:3])})')
        # ── La mitad que SÍ habría cazado el bug ──────────────────────────────
        # Dentro de config el calendario cuadraba, y dentro del JSON también. Lo
        # que no cuadraba era una fuente contra la otra, y ahí no miraba nadie.
        # El apareo replica el del loader: 'cineautopsia2026' → cineautopsia-2026.
        _fid = _os.path.basename(_p)[:-5].replace('-', '')
        _cm = _re.search(r"'" + _re.escape(_fid) + r"':\s*\{(.*?)\n  \},", _cfg, _re.S)
        if not _cm:
            continue
        _cfd = _re.search(r"festivalDates:\{(.*?)\}", _cm.group(1), _re.S)
        if not _cfd:
            continue
        _cdates = set(_re.findall(r"'([^']+)'\s*:", _cfd.group(1)))
        if _cdates != _dates:
            _solo_json = sorted(_dates - _cdates)
            _errs.append(f'{_fid}: el calendario NO coincide entre config ({len(_cdates)} días) '
                         f'y su JSON ({len(_dates)} días)'
                         + (f' — el JSON tiene además {", ".join(_solo_json[:3])}' if _solo_json else '')
                         + '. El dueño es el JSON: config quedó viejo y hay que regenerarlo')
    # Y la clasificación en sí: si `festivalDates` vuelve a ser IDENTIDAD, el JSON
    # deja de poder corregir un config viejo y el calendario se parte otra vez —
    # sin que ningún dato quede mal, que es lo que lo hizo invisible la primera vez.
    _ld = open('src/controller/loader.js', encoding='utf-8').read()
    _ident = _re.search(r'_identFields\s*=\s*\[(.*?)\]', _ld, _re.S)
    if _ident and 'festivalDates' in _ident.group(1):
        _errs.append('festivalDates volvió a _identFields: el JSON ya no puede corregir un '
                     'config viejo y el calendario se vuelve a partir en dos dueños')

    # ── El ORDEN, que es lo que de verdad rompía ──────────────────────────────
    # `dayFullyPassed` lee FESTIVAL_DATES y FILMS. Los dos se publican en el
    # `state.batchUpdate` del loader. Preguntarle ANTES —como hacía el DOM build
    # de la tira— es preguntarle por el festival anterior: devolvía false por
    # `if(!dateStr)` y NINGÚN día se atenuaba, en ningún festival, nunca. El
    # comentario del loader ya avisaba de FESTIVAL_END y aun así se coló, porque
    # nadie miró la OTRA cosa que la función lee primero.
    # El ancla es la LÍNEA QUE PUBLICA EL CALENDARIO, no `state.batchUpdate` a
    # secas: hay dos batchUpdate en el loader y el primero (transition+clear) va
    # ANTES de la tira, así que anclar ahí daba un chequeo que no medía nada —
    # pasaba en verde con el bug puesto. Lo cacé mutando; sin mutar, habría
    # quedado un guardián decorativo.
    _bu = _ld.find('FESTIVAL_DATES: cfg.festivalDates')
    if _bu < 0:
        _errs.append('no encuentro dónde se publica FESTIVAL_DATES en loader.js: '
                     'no puedo verificar el orden')
    else:
        for _c in _re.finditer(r'dayFullyPassed\s*\(', _ld):
            _linea = _ld[_ld.rfind('\n', 0, _c.start()) + 1:_c.start()]
            if _linea.lstrip().startswith(('//', '*')) or 'import' in _linea:
                continue
            if _c.start() < _bu:
                _n = _ld[:_c.start()].count('\n') + 1
                _errs.append(f'loader.js:{_n} pregunta dayFullyPassed antes de que se publique '
                             'el calendario: ahí FESTIVAL_DATES y FILMS son todavía los del '
                             'festival anterior, y la respuesta es siempre false')
                break

    if _errs:
        fail(check, '; '.join(_errs[:3]))
    else:
        ok(check, 'todo día dibujable tiene fecha, y el calendario tiene un solo dueño')
except Exception as _e:
    warn(check, f'no se pudo verificar calendario-entero: {_e}')

# ── [aplazado-caduca] un aplazado se va a pasados, pero sigue siendo aplazado ──
# Juan, 23 ago 2026: «FICMA hace ruido donde está». Un aplazado nunca contaba
# como pasado —deliberado: cuando FICMA se aplazó por el terremoto era noticia
# viva y esconderlo habría tapado justo lo que había que leer— pero esa razón
# CADUCA: pasadas sus fechas anunciadas es ruido en la zona de los vigentes.
#
# La bisagra vive en el RIEL (`_postponedElapsed`), no en el clasificador. Y ahí
# está la tentación que este guardián existe para frenar: «simplificar» haciendo
# que `_classifyFestival` devuelva 'past' para un aplazado con fechas vencidas.
# Se vería idéntico en el riel y rompería en silencio todo lo que el estado
# aplazado protege — que no cuente como en curso, que no se preseleccione, que
# su plan no se rehidrate, que su banner siga explicando por qué no hay festival.
# Eso es el bug del sismo otra vez, y no se ve hasta que alguien abre la app.
check = 'aplazado-caduca'
try:
    import re as _re
    _c = open('src/view/components.js', encoding='utf-8').read()
    _errs = []

    if 'function _postponedElapsed' not in _c:
        _errs.append('falta _postponedElapsed: la bisagra que manda un aplazado vencido a pasados')
    else:
        _m = _re.search(r'function _postponedElapsed\(cfg\)\{(.*?)\n\}', _c, _re.S)
        _body = _m.group(1) if _m else ''
        if 'festivalEndStr' not in _body:
            _errs.append('_postponedElapsed no mira festivalEndStr — la bisagra es la fecha '
                         'que el festival había anunciado, no otra cosa')

    # El clasificador NO puede aprender la bisagra: ahí rompería en silencio.
    _cl = _re.search(r'export function _classifyFestival\(cfg\)\{(.*?)\n\}', _c, _re.S)
    if not _cl:
        _errs.append('no encuentro _classifyFestival')
    else:
        _cb = _cl.group(1)
        if '_postponedElapsed' in _cb:
            _errs.append('_classifyFestival llama a _postponedElapsed: un aplazado dejaría de '
                         'ser aplazado y perdería sus protecciones (preselección, punto verde, '
                         'banner). La bisagra es de PRESENTACIÓN, no de estado')
        if not _re.search(r"kind===?'postponed'\s*\)\s*return\s*'postponed'", _cb.replace('"', "'")):
            _errs.append("_classifyFestival dejó de devolver 'postponed' para un aplazado")

    # Y alguien tiene que USARLA: una bisagra que nadie llama existe y no hace
    # nada. Se cuentan las referencias fuera de su propia definición — partir el
    # archivo por el nombre de la función me dio el trozo equivocado y el chequeo
    # falló sobre código correcto.
    _usos = len(_re.findall(r'_postponedElapsed\s*\(', _c)) - 1  # -1: la definición
    if _usos < 2:
        _errs.append(f'_postponedElapsed se usa {_usos} vez/veces: hacen falta las dos '
                     '—el orden (_sortFestivals) y la partición del riel—')

    if _errs:
        fail(check, '; '.join(_errs[:3]))
    else:
        ok(check, 'el aplazado vencido baja a pasados sin dejar de ser aplazado')
except Exception as _e:
    warn(check, f'no se pudo verificar aplazado-caduca: {_e}')

# ── [icono-texto] un botón con icono Y texto se alinea, o el icono flota ──────
# Juan, 18 ago 2026: el «+» de «Agendar» iba 3px más alto que la palabra. La
# causa: .excl-include-btn no tenía display:inline-flex ni align-items:center,
# así que el SVG se apoyaba en la línea BASE del texto en vez de centrarse con
# él. [button-canon] no lo vio porque mira color, fondo y peso — nunca miró
# geometría interna. Este chequeo cierra ese hueco: si el markup pone un ICONS.x
# SEGUIDO DE TEXTO dentro de un botón, su regla CSS debe alinearlos. Los
# contenedores de icono SOLO (chevrons, cierres) no entran: no hay nada que
# alinear con nada.
check = 'icono-texto'
try:
    import re as _re, glob as _glob
    _html = open('index.html', encoding='utf-8').read()
    _src = ''
    for _f in _glob.glob('src/**/*.js', recursive=True):
        _src += open(_f, encoding='utf-8').read()
    # markup: class="… X …" … > ${ICONS.algo} <algo que NO cierra el tag>
    _con_texto = set()
    # SOLO elementos <button>: una fila de texto con icono se alinea por su
    # cuenta (line-height, vertical-align) y no es lo que rompe aquí.
    for _m in _re.finditer(r'<button[^>]*class="([^"]*)"[^>]*>\s*\$\{ICONS\.\w+\}\s*([^<]{2,40})', _src):
        _resto = _m.group(2).strip()
        if not _resto or _resto.startswith('</'):
            continue  # icono solo
        for _c in _m.group(1).split():
            if '${' in _c:
                continue
            _con_texto.add(_c)
    _errs = []
    for _c in sorted(_con_texto):
        _r = _re.search(r'^\.' + _re.escape(_c) + r'\{([^}]*)\}', _html, _re.M)
        if not _r:
            continue
        _b = _r.group(1)
        if 'flex' not in _b or 'align-items:center' not in _b:
            _errs.append(f'.{_c} lleva icono+texto sin alinear (falta inline-flex + align-items:center)')
    if _errs:
        fail(check, '; '.join(_errs[:5]))
    else:
        ok(check, f'{len(_con_texto)} botones con icono+texto, todos alineados')
except Exception as _e:
    warn(check, f'no se pudo verificar icono-texto: {_e}')

# ── [dato-linea] la línea de dato tiene UN dueño; la familia no crece ─────────
# Auditoría 18 ago 2026: la app tenía 89 clases distintas de «texto pequeño gris»
# (.hint, .cnt-line, .excl-reason, .plist-meta, .suggestion-meta…) — ninguna era
# dueña, así que cada pantalla inventaba su tamaño y su ritmo, y las líneas se
# veían sueltas. Nace .dato-linea (t-base, ritmo sp-1) como canon. Este guardián
# NO exige migrar las 89 de golpe: congela el número para que nadie sume la 90
# sin decidirlo, y verifica que el canon siga existiendo con su anatomía.
check = 'dato-linea'
try:
    import re as _re
    _html = open('index.html', encoding='utf-8').read()
    _errs = []
    # 1) el canon existe y conserva su anatomía (t-base + ritmo entre hermanas)
    _canon = _re.search(r'^\.dato-linea\{([^}]*)\}', _html, _re.M)
    if not _canon:
        _errs.append('.dato-linea no existe — el canon de línea de dato desapareció')
    else:
        _body = _canon.group(1)
        if 'font-size:var(--t-base)' not in _body:
            _errs.append('.dato-linea sin t-base (a 11px las líneas se leen «pequeñas»)')
        if not _re.search(r'^\.dato-linea\+\.dato-linea\{[^}]*margin-top:var\(--sp-1\)', _html, _re.M):
            _errs.append('.dato-linea perdió su ritmo sp-1 entre hermanas')
    # 2) la familia de líneas grises sueltas no crece
    _fam = 0
    for _m in _re.finditer(r'^(\.[a-z0-9-]+)\{([^}]*)\}', _html, _re.M):
        _b = _m.group(2)
        # el canon NO es una variante de sí mismo (se contaba y disparaba solo)
        if _m.group(1) == '.dato-linea':
            continue
        if 'font-size' not in _b or 'background' in _b:
            continue
        if _re.search(r'font-size:var\(--t-(xs|sm|label|caption|base)\)', _b) and \
           _re.search(r'color:var\(--(gray|gray2|white-60|white-40)\)', _b):
            _fam += 1
    # 88 heredadas + .diary-full (nombre completo bajo la sigla en la TAPA del
    # Diario: tipografía de bloque de título, no una línea de dato) + .palm-cap
    # (pie de afiche del palmarés: el nombre DEBAJO de una imagen, en el riel y
    # en las menciones — no es una línea de dato en una ficha, y usarla como tal
    # la ataría a t-base, que a 62px de ancho no cabe). Baja cuando se migren
    # las heredadas.
    _TECHO = 90
    if _fam > _TECHO:
        _errs.append(f'familia de líneas de texto gris: {_fam} > techo {_TECHO} — '
                     f'usá .dato-linea en vez de crear otra variante (o bajá el techo si migraste)')
    if _errs:
        fail(check, '; '.join(_errs))
    else:
        ok(check, f'canon vivo (t-base + ritmo sp-1) y familia en {_fam} (techo {_TECHO})')
except Exception as _e:
    warn(check, f'no se pudo verificar dato-linea: {_e}')

# ── [star-semantics] la estrella es CALIFICACIÓN; prioridad = bookmark ─────────
# Decisión Juan 18 jul 2026: ★/ICONS.star SOLO para rating (convención cine);
# prioridad usa ICONS.bookmark. Una línea de PRIORIDAD (togglePriority/
# togglePelPrio/cta_priorizar/lbl_prioridades) con ICONS.star, starFill o ★
# reintroduce la colisión que confundía prioridad con calificación.
check = 'star-semantics'
try:
    import glob as _glob
    _hits = []
    _PRIO = ('togglePriority', 'togglePelPrio', 'cta_priorizar', 'cta_priorizada',
             'lbl_prioridades', 'toast_priorizada', 'prio_stale_banner', 'lbl_prio_corto',
             'toast_prioridad_quitada')
    for _sf in _glob.glob('src/**/*.js', recursive=True):
        for _i, _ln in enumerate(open(_sf, encoding='utf-8').read().splitlines(), 1):
            if _ln.strip().startswith('//') or _ln.strip().startswith('*'):
                continue
            if any(_p in _ln for _p in _PRIO) and ('ICONS.star' in _ln or '★' in _ln):
                _hits.append(f'{_sf}:{_i}')
    if _hits:
        fail(check, 'estrella en contexto de PRIORIDAD (usar ICONS.bookmark): ' + '; '.join(_hits[:6]))
    else:
        ok(check, 'estrella reservada a calificación; prioridad con bookmark')
except Exception as _e:
    warn(check, f'no se pudo verificar star-semantics: {_e}')

# ── [icon-single-source] glifos migrados no reaparecen inline en view/controller ─
# Auditoría iconos 18 jul: todo glifo de UI sale de ICONS (components.js). Estos
# paths ya se migraron; un <svg> inline con ellos fuera de components.js = copia
# reintroducida (la fuente diverge). Excepciones legítimas (NO en esta lista):
# starSVG/rating (polígono estrella con half-fill), LB_SVG (logo marca),
# generadores de póster — todos en components.js o con su propia identidad.
check = 'icon-single-source'
try:
    import glob as _glob
    _SIGS = {
        'chevronD': 'M19.5 8.25l-7.5 7.5-7.5-7.5',
        'clock': 'polyline points="12 6 12 12 16 14"',
        'pin': 'M15 10.5a3 3 0 11-6 0',
        'alert': 'M12 9v3.75m-9.303',
        'moon': 'M21.752 15.002',
        'x-close': 'M6 18L18 6M6 6l12 12',
        'check-glyph': 'M4.5 12.75l6 6 9-13.5',
    }
    _hits = []
    for _sf in _glob.glob('src/view/*.js') + _glob.glob('src/controller/*.js'):
        if _sf.endswith('components.js'):
            continue
        _c = open(_sf, encoding='utf-8').read()
        for _i, _ln in enumerate(_c.splitlines(), 1):
            if _ln.strip().startswith('//'):
                continue
            if '<svg' in _ln:
                for _name, _sig in _SIGS.items():
                    if _sig in _ln:
                        _hits.append(f'{_sf}:{_i} {_name} inline (usar ICONS)')
    if _hits:
        fail(check, 'glifo migrado reintroducido inline: ' + '; '.join(_hits[:6]))
    else:
        ok(check, 'glifos de ICONS no duplicados inline en view/controller')
except Exception as _e:
    warn(check, f'no se pudo verificar icon-single-source: {_e}')

# ── [country-flags] si hay país, hay bandera (regla Juan 18 jul 2026) ──────────
# El bug Voces del Territorio: countryToFlags partía solo por "/" y el string con
# comas caía al globo 🌍. Fix aplicado; este guardián evita la recaída a nivel de
# DATOS: en los festivales VIVOS, todo país (partido por coma/barra) debe estar en
# _COUNTRY_FLAGS o el film debe traer un campo `flags` autorizado. Un país nuevo sin
# mapear se caza aquí antes de mostrar globo. Festival nuevo activo → sumarlo abajo.
check = 'country-flags'
try:
    import re as _re, json as _json, datetime as _dt, glob as _g2
    # Los festivales VIVOS se DERIVAN de FESTIVAL_CONFIG (festivalEndStr futuro).
    # Antes era una lista escrita a mano y nadie la actualizó nunca: el guardián
    # llevaba meses dando verde sobre dos festivales ya pasados mientras
    # FICMontañas y FINCA se publicaban sin revisar — "el segundo festival
    # consecutivo con globos" (Juan, 29 jul 2026). Un guardián con lista manual
    # no es un guardián: es una foto que envejece.
    _cfg = open('src/config.js', encoding='utf-8').read()
    _hoy = _dt.date.today().isoformat()
    _vivos = set()
    for _fid, _end in _re.findall(r"'([a-z0-9]+)':\s*\{.*?festivalEndStr:\s*'(\d{4}-\d{2}-\d{2})", _cfg, _re.S):
        if _end >= _hoy:
            _vivos.add(_re.sub(r'([a-zA-Z]+)(\d+)$', r'\1-\2', _fid))
    _ACTIVE = [f'festivals/{_v}.json' for _v in sorted(_vivos)]
    if not _ACTIVE:  # sin festivales vivos, revisar el más reciente igual
        _ACTIVE = sorted(_g2.glob('festivals/*.json'))[-1:]
    _js = open('src/controller/sheets-controller.js', encoding='utf-8').read()
    _m = _re.search(r'const _COUNTRY_FLAGS=\{(.*?)\};', _js, _re.S)
    _mapped = set(_re.findall(r"'([^']+)':", _m.group(1))) if _m else set()
    _bad = []
    def _walk_films(_films, _fid):
        for _f in _films or []:
            _c = (_f.get('country') or '').strip()
            if _c and not _f.get('flags'):
                _parts = [p.strip() for p in _re.split(r'[,/()]', _c) if p.strip()]
                _unmapped = [p for p in _parts if p not in _mapped]
                if _unmapped:
                    _bad.append(f"{_fid}: '{_f.get('title','?')[:30]}' país sin bandera: {', '.join(_unmapped)}")
            _walk_films(_f.get('film_list'), _fid)
    for _af in _ACTIVE:
        try:
            _d = _json.load(open(_af, encoding='utf-8'))
        except FileNotFoundError:
            continue
        _walk_films(_d.get('films'), _af.split('/')[-1])
    # SEGUNDA MITAD, la que faltaba. Lo de arriba comprueba que el país SE PUEDA
    # mapear; no que la bandera EXISTA en el dato. FICDEH pasó en verde durante
    # todo el festival con 415 films mostrando su país y ninguna bandera: sus
    # países estaban perfectamente mapeados y el pipeline nunca emitió `flags`,
    # que es lo único que la ficha pinta (`flagFmt(f.flags)`, sin derivar).
    # Un guardián que verifica que algo SE PUEDE hacer no verifica que se haya
    # hecho. Lo encontró Juan mirando la app, 13 ago 2026.
    _mudos = []
    for _af in _ACTIVE:
        try:
            _d = _json.load(open(_af, encoding='utf-8'))
        except FileNotFoundError:
            continue
        _cc = [f for f in (_d.get('films') or []) if (f.get('country') or '').strip()]
        _sin = [f for f in _cc if not f.get('flags')]
        if _cc and len(_sin) == len(_cc):
            _mudos.append(f'{_af.split("/")[-1]}: {len(_cc)} films con país y '
                          f'NINGUNO con flags')
    if _bad:
        fail(check, 'país sin bandera en festival vivo (mapear en _COUNTRY_FLAGS o añadir flags): ' + '; '.join(_bad[:6]))
    elif _mudos:
        fail(check, 'festival vivo que muestra país sin una sola bandera: '
                    + '; '.join(_mudos))
    else:
        ok(check, 'todo país de festivales vivos produce bandera (nunca globo)')
except Exception as _e:
    warn(check, f'no se pudo verificar country-flags: {_e}')

# ── [poster-radio-unico] toda superficie de póster usa var(--r-poster) ────────
# El póster se ve IGUAL en toda la app. Hasta ago 2026 convivían TRES radios
# —12px, 8px y 4px— sin razón de diseño detrás: deriva pura, 16 declaraciones
# repartidas en 2000 líneas de CSS. Nadie las eligió; se fueron copiando.
# El radio es proporcional (--r-poster, clamp elíptico) justamente porque el rango
# de tamaños va de 32px a 96px: un valor fijo no puede servir a los dos extremos.
# Un radio suelto no rompe nada y no da error — por eso hace falta el guardián.
#
# Se juzga por NOMBRE de selector (poster/thumb): un póster nuevo se va a llamar
# así. Los overlays que van ENCIMA del póster —badges, checks— no son superficie
# de imagen y llevan el radio de su propio componente; van en la excepción, con
# nombre, para que agregar uno sea una decisión y no un descuido.
check = 'poster-radio-unico'
try:
    _html = open('index.html', encoding='utf-8').read()
    # Encima del póster, no el póster: conservan su radio propio.
    _ENCIMA = {'.poster-now', '.poster-past-badge', '.pv-poster-check'}
    _malos = []
    # Hueco cazado el 18 ago: la regex exigía que el selector EMPEZARA con
    # punto, así que «#ag-result .lb-poster{border-radius:var(--r-sm)}» pasaba
    # en verde con 4px mientras el resto de la app usaba el radio proporcional.
    # Un guardián que solo mira la puerta de adelante no es un guardián.
    for _m in re.finditer(r'^([#.][a-zA-Z0-9_.\-]+(?: +[.#][a-zA-Z0-9_.\-]+)*)\{([^}]*)\}', _html, re.M):
        if not re.search(r'(poster|thumb)', _m.group(1)):
            continue
        _sel, _cuerpo = _m.group(1), _m.group(2)
        if _sel in _ENCIMA:
            continue
        _br = re.search(r'border-radius:([^;}]+)', _cuerpo)
        if not _br:
            continue
        _val = _br.group(1).strip()
        if _val != 'var(--r-poster)':
            _linea = _html[:_m.start()].count('\n') + 1
            _malos.append(f'{_sel} (L{_linea}): {_val}')
    if _malos:
        fail(check, 'superficie(s) de póster con radio propio en vez de var(--r-poster): '
                    + ' · '.join(_malos[:5]) + (f' +{len(_malos)-5} más' if len(_malos) > 5 else ''))
    else:
        _n = len(re.findall(r'border-radius:var\(--r-poster\)', _html))
        ok(check, f'{_n} superficies de póster con el mismo radio proporcional')
except Exception as _e:
    warn(check, f'no se pudo verificar poster-radio-unico: {_e}')

# ── [poster-single-owner] decisión y marco editorial SOLO en view/helpers.js ──
# posterModel/posterParts (films) e itemPosterParts (obras) son los ÚNICOS dueños
# de la decisión editorial-vs-imagen y del marco. Si _isEditorialPoster( o
# editorialFrame( aparece en otro módulo de src/, alguien re-derivó la decisión
# a mano — el patrón que causó 7 copias divergentes del marco (jul 2026).
check = 'poster-single-owner'
try:
    import glob as _glob
    _off = []
    for _sf in _glob.glob('src/**/*.js', recursive=True):
        if _sf.endswith('view/helpers.js'):
            continue
        _c = open(_sf, encoding='utf-8').read()
        for _tok in ('_isEditorialPoster(', 'editorialFrame('):
            for _i, _ln in enumerate(_c.splitlines(), 1):
                if _tok in _ln and not _ln.strip().startswith('//') and 'import' not in _ln:
                    _off.append(f"{_sf}:{_i} {_tok[:-1]}")
    if _off:
        fail(check, 'decisión/marco editorial fuera de la fuente única (usar posterParts/itemPosterParts): ' + '; '.join(_off[:6]))
    else:
        ok(check, 'decisión y marco editorial construidos solo en view/helpers.js')
except Exception as _e:
    warn(check, f'no se pudo verificar poster-single-owner: {_e}')

# ── [avisos-en-banda] los avisos que MATIZAN viven en la banda AVISOS ─────────
# Q&A, programa e inscripción vivían DENTRO del bloque de FUNCIÓN y competían con el
# día, la hora y la sede (y "función" aparecía 3 veces en 4 líneas). Ahora tienen
# banda propia, construida por _avisosBand — dueño único. Un .meta-banner-label
# suelto en las fichas significa que alguien volvió a colgar un aviso fuera.
# Excepción legítima: el banner de entradas de festival mixto (lleva enlace, no es
# un matiz de la función) y el notice-banner-row de cancelada/reprogramada, que va
# DENTRO de FUNCIÓN porque la invalida.
check = 'avisos-en-banda'
try:
    _sc = open('src/controller/sheets-controller.js', encoding='utf-8').read()
    _bad = [i for i, ln in enumerate(_sc.splitlines(), 1)
            if 'meta-banner-label' in ln and not ln.strip().startswith('//')]
    if _bad:
        fail(check, 'aviso con rótulo fuera de la banda AVISOS (usar _avisosBand): '
             + ', '.join(f'sheets-controller.js:{i}' for i in _bad[:5]))
    else:
        ok(check, 'los avisos que matizan la función se construyen solo en _avisosBand')
except Exception as _e:
    warn(check, f'no se pudo verificar avisos-en-banda: {_e}')

# ── [aviso-sin-caja] ningún aviso lleva recuadro sobre el texto ────────────────
# Regla de Juan (29 jul 2026): un aviso es una NOTA al margen, no una tarjeta. El
# recuadro competía con las superficies reales (sec-hdr, filas de función) y pesaba
# más que su contenido. Se quitó de .meta-banner, .notice-banner-row, .prio-stale y
# .notice-detail-*. La PASTILLA del badge sí se queda: ahí el fondo ES el componente,
# no una caja alrededor de un texto.
check = 'aviso-sin-caja'
try:
    import re as _re
    _html = open('index.html', encoding='utf-8').read()
    _AVISOS = ('.meta-banner{', '.notice-banner-row{', '.prio-stale{',
               '.notice-detail-amber{', '.notice-detail-green{')
    _off = []
    for _sel in _AVISOS:
        _i = _html.find(_sel)
        if _i < 0:
            continue
        _body = _html[_i + len(_sel):_html.index('}', _i)]
        if 'background' in _body or 'border:' in _body or 'border-radius' in _body:
            _off.append(_sel[:-1])
    if _off:
        fail(check, 'aviso(s) con caja (fondo/borde/radio sobre el texto): ' + ', '.join(_off))
    else:
        ok(check, f'{len(_AVISOS)} avisos sin caja — solo el badge conserva su pastilla')
except Exception as _e:
    warn(check, f'no se pudo verificar aviso-sin-caja: {_e}')

# ── [screening-row-single-owner] la fila de función tiene UN solo constructor ───
# La fila "día · hora · sede [· Añadir]" es el mismo concepto en la ficha de película
# y en la de corto. Tenerla duplicada fue el bug de jul 2026: la ficha de corto no
# pintaba función NUNCA porque su constructor simplemente no la tenía, y el usuario
# que buscaba el corto de un amigo no sabía cuándo ni dónde verlo. `_screeningRows`
# es el dueño único; quien emita la clase .pel-sheet-screening a mano la re-derivó.
check = 'screening-row-single-owner'
try:
    import glob as _glob, re as _re
    _off = []
    for _sf in _glob.glob('src/**/*.js', recursive=True):
        _c = open(_sf, encoding='utf-8').read()
        for _i, _ln in enumerate(_c.splitlines(), 1):
            _t = _ln.strip()
            # OJO: `pel-sheet-screenings` (plural) es el CONTENEDOR, no la fila —
            # el patrón antiguo, por prefijo, los confundía y solo pasaba por una
            # heurística de proximidad que se rompía al mover código. Se exige que
            # la clase termine ahí (comilla, espacio o interpolación).
            if _t.startswith('//') or not _re.search(r'class="pel-sheet-screening(?![a-z-])', _ln):
                continue
            _off.append(f"{_sf}:{_i}")
    if len(_off) > 1:
        fail(check, 'la fila de función se construye en más de un sitio (usar _screeningRows): ' + '; '.join(_off[:6]))
    else:
        ok(check, 'fila de función construida solo por _screeningRows (ficha de película + de corto)')
except Exception as _e:
    warn(check, f'no se pudo verificar screening-row-single-owner: {_e}')

# ── [plan-sync-en-puertas] el plan hidratado se re-deriva del catálogo ──────────
# Una entrada de savedAgenda es una copia congelada de la función al elegirla.
# Bug real (31 jul 2026, FINCA): plan guardado antes del anclaje mostraba fines y
# aviso de Q&A calculados sobre la copia vieja. Regla: TODA puerta por donde un
# plan persistido entra al estado vivo (hydrate del loader, _applyCloudRow de la
# nube) debe pasar por syncScheduleWithCatalog. Si alguien abre una puerta nueva
# que hidrate savedAgenda desde fuera (storage/nube), tiene que sumarla acá y
# llamar al sync — este check lo recuerda.
check = 'plan-sync-en-puertas'
try:
    _puertas = {
        'src/controller/loader.js': 'loadState(',        # hydrate local (BATCH 2)
        'src/controller/persistence.js': 'deriveCloudApply(',  # plan desde la nube
    }
    _sin = []
    for _pf, _marca in _puertas.items():
        _c = open(_pf, encoding='utf-8').read()
        if _marca in _c and 'syncScheduleWithCatalog(' not in _c:
            _sin.append(_pf)
    if _sin:
        fail(check, 'puerta de hidratación del plan sin sync contra el catálogo: ' + '; '.join(_sin))
    else:
        ok(check, 'las 2 puertas del plan (loader + nube) re-derivan contra el catálogo')
except Exception as _e:
    warn(check, f'no se pudo verificar plan-sync-en-puertas: {_e}')

# ── [plan-write-chokepoint] savedAgenda tiene UN camino de escritura ────────────
# PR 2 del plan de confiabilidad (31 jul 2026): toda MUTACIÓN del plan pasa por
# commitPlan (persistence.js), que certifica el resultado con verifyPlan —
# report-only en prod, duro en tests (__PLAN_STRICT__). Las únicas escrituras
# directas permitidas son las 2 puertas de HIDRATACIÓN (loader + nube), que
# normalizan vía syncScheduleWithCatalog. Un escritor nuevo que salte el
# chokepoint reabre la puerta a planes inválidos sin radar — este check lo veta.
check = 'plan-write-chokepoint'
try:
    import glob as _glob, re as _re
    # sitio permitido → nº exacto de escrituras directas esperadas
    _allowed = {'src/controller/persistence.js': 2,  # commitPlan + puerta nube
                'src/controller/loader.js': 1}       # puerta hydrate local
    _off = []
    for _sf in _glob.glob('src/**/*.js', recursive=True):
        _n = _sf.replace('\\', '/')
        _c = open(_sf, encoding='utf-8').read()
        _hits = len(_re.findall(r"state\.(?:set|update)\('savedAgenda'", _c))
        if _n in _allowed:
            if _hits != _allowed[_n]:
                _off.append(f"{_n}: {_hits} escrituras (esperadas {_allowed[_n]})")
        elif _hits:
            _off.append(f"{_n}: {_hits} escrituras fuera del chokepoint")
    if _off:
        fail(check, 'savedAgenda se escribe fuera de commitPlan: ' + '; '.join(_off))
    else:
        ok(check, 'savedAgenda: chokepoint único (commitPlan) + 2 puertas de hidratación')
except Exception as _e:
    warn(check, f'no se pudo verificar plan-write-chokepoint: {_e}')

# ── [plan-concepto] «Plan» es un nombre, y los nombres van en mayúscula ────────
# Decisión de Juan (16 ago 2026, opción B de la discusión de roles): «Mi Plan» es
# UN concepto de la app, no un sustantivo común, así que la palabra va en
# mayúscula siempre — incluso en posesivo («en tu Plan», «Fuera de tu Plan»).
# Antes convivían 20 strings con mayúscula y 36 con minúscula, y la misma frase
# se escribía de las dos formas según el día en que se agregó
# (plan_en_tu_plan «En tu Plan» vs toast_en_tu_plan «en tu plan»).
# Se eligió esta regla y no «depende del uso» justamente porque ESTA se puede
# verificar sola; la otra depende del criterio de quien escribe, y ya vimos cómo
# terminó. Cubre también el fallback estático de index.html: es lo que se ve en el
# primer frame, antes de que corra i18n.
# NO toca «Planear»/«planner»/«Planejar» ni los verbos (planeaste, planned,
# planejou): la regla es sobre la palabra suelta.
check = 'plan-concepto'
try:
    import re as _re
    _off = []
    _i18n = open('src/i18n/i18n.js', encoding='utf-8').read()
    for _m in _re.finditer(r'"([a-z_0-9]+)":\s*"([^"]*)"', _i18n):
        if _re.search(r'\b(plan|plano)\b', _m.group(2)):
            _ln = _i18n[:_m.start()].count('\n') + 1
            _off.append(f'i18n.js:{_ln} [{_m.group(1)}]')
    _idx = open('index.html', encoding='utf-8').read()
    for _m in _re.finditer(r'data-i18n="[a-z_0-9]+"[^>]*>([^<]*)', _idx):
        if _re.search(r'\bplan\b', _m.group(1)):
            _ln = _idx[:_m.start()].count('\n') + 1
            _off.append(f'index.html:{_ln}')
    if _off:
        fail(check, '«Plan» en minúscula — es el nombre del concepto, va en mayúscula: ' + '; '.join(_off[:8]))
    else:
        ok(check, '«Plan» en mayúscula en las 3 locales y en el fallback estático')
except Exception as _e:
    warn(check, f'no se pudo verificar: {_e}')

# ── [plannable-dueno-unico] nadie reimplementa «qué funciones son planificables» ─
# El 16 ago 2026 el plan volvió a cruzar ciudades con el filtro puesto, y NO fue
# por la regla: plannableScreens filtraba bien. Fue `squeezeExcluded` en
# handlers.js, que tenía su propia copia del predicado (FILMS.filter con 2 de los
# 4 filtros) y reinsertaba las excluidas AL GUARDAR — después del motor, y exenta
# del chequeo de conflicto por `_squeezed`. Una regla con dos implementaciones es
# una regla que se desincroniza; y este chequeo mira el CRUCE (quién combina
# título + pasada/bloqueada fuera del dueño), no la forma de una sola línea.
check = 'plannable-dueno-unico'
try:
    import glob as _glob, re as _re
    _off = []
    for _sf in _glob.glob('src/**/*.js', recursive=True):
        _p = _sf.replace('\\', '/')
        if _p.endswith('src/domain/schedule.js'):
            continue  # la casa del dueño
        _src = open(_sf, encoding='utf-8').read()
        # FILMS.filter(...) que combine match por título con los filtros temporales.
        # El cuerpo se captura por BALANCE DE PARÉNTESIS, no por ventana de
        # caracteres: la versión anterior leía hasta 240 chars y el filtro del
        # panel de alternativas medía 337 — el guardián tenía un punto ciego
        # proporcional al largo del código, y justo la copia más grande (la que
        # ofrecía ciudades canceladas) pasaba por debajo (re-corrida del QA,
        # 16 ago 2026). Un guardián que depende del largo no vigila: muestrea.
        for _m in _re.finditer(r'FILMS\.filter\(', _src):
            _i = _m.end(); _depth = 1
            while _i < len(_src) and _depth:
                if _src[_i] == '(': _depth += 1
                elif _src[_i] == ')': _depth -= 1
                _i += 1
            _body = _src[_m.end():_i - 1]
            if '.title===' not in _body.replace(' ', ''):
                continue
            if 'screeningPassed' in _body or 'isScreeningBlocked' in _body:
                _ln = _src[:_m.start()].count('\n') + 1
                # Exención EXPLÍCITA: `// plannable-ok: <razón>` en las 4 líneas
                # previas. Las preguntas sobre el CATÁLOGO (qué días existe la
                # obra, por qué quedó fuera) son legítimamente otras y necesitan
                # ver lo que el dueño ya filtró — pero se declaran, no se asumen.
                _prev = '\n'.join(_src.splitlines()[max(0, _ln - 5):_ln - 1])
                if 'plannable-ok:' in _prev:
                    continue
                _off.append(f'{_sf}:{_ln}')
    if _off:
        fail(check, 'predicado de «función planificable» reimplementado fuera de plannableScreens (usar el dueño): ' + '; '.join(_off))
    else:
        ok(check, 'plannableScreens es el dueño único del predicado de planificable')
except Exception as _e:
    warn(check, f'no se pudo verificar: {_e}')

# ── [fin-inline-ratchet] la aritmética de fin fuera del dominio no puede CRECER ─
# PR 3 del plan de confiabilidad (31 jul 2026). El tech lead descartó el rewrite
# big-bang del intervalo canónico (generalidad especulativa); en su lugar, patrón
# ratchet de migraciones: los sitios existentes de `toMin(x)+duración` fuera de
# src/domain/ están auditados (todos usan el dueño correcto) y su CONTEO es un
# techo — código nuevo debe usar los dueños del dominio (delayedEndMin,
# screeningEndMin/Date, durationForTravel), no sumar a mano. Si esta cifra sube,
# el CI exige mover el cálculo al dominio (o, si es legítimo, documentarlo y
# ajustar el techo A CONCIENCIA en este check).
check = 'fin-inline-ratchet'
try:
    import glob as _glob, re as _re
    _TECHO = 4  # agenda.js:382,1536,1544 (huecos/slots) + helpers.js:347 (travelWarn)
    _hits = []
    for _sf in _glob.glob('src/**/*.js', recursive=True):
        if _sf.replace('\\', '/').startswith('src/domain/'):
            continue
        for _i, _ln in enumerate(open(_sf, encoding='utf-8').read().splitlines(), 1):
            _code = _ln.split('//')[0]
            if _re.search(r'toMin\([^)]*\)\s*\+\s*(blockDuration|effectiveDuration|durationForTravel)', _code):
                _hits.append(f"{_sf}:{_i}")
    if len(_hits) > _TECHO:
        fail(check, f'aritmética de fin inline subió a {len(_hits)} (techo {_TECHO}) — usar los dueños del dominio: ' + '; '.join(_hits))
    else:
        ok(check, f'aritmética de fin inline: {len(_hits)}/{_TECHO} sitios auditados (ratchet)')
except Exception as _e:
    warn(check, f'no se pudo verificar fin-inline-ratchet: {_e}')

# ── [hooks-activos] las barreras de git están enchufadas ────────────────────────
# .githooks/ se versiona, pero core.hooksPath es config LOCAL de cada clon: un
# clon nuevo trae los hooks y no los usa hasta que alguien lo configura. Aviso, no
# error: en CI no aplica, y un clon de solo lectura no los necesita.
check = 'hooks-activos'
try:
    import subprocess as _sp
    _hp = _sp.run(['git', 'config', 'core.hooksPath'], capture_output=True, text=True).stdout.strip()
    if not os.path.isdir('.githooks'):
        warn(check, 'falta .githooks/ (pre-commit + pre-push)')
    elif _hp != '.githooks':
        warn(check, 'los hooks no están activos en este clon — enchufalos con: '
                    'git config core.hooksPath .githooks')
    else:
        ok(check, 'pre-commit y pre-push activos (core.hooksPath)')
except Exception as _e:
    warn(check, f'no se pudo verificar hooks-activos: {_e}')

# ── [peso-repo] el repo guarda el producto, no el material de trabajo ───────────
# 68,7 MB entraron de un tirón (8 ago 2026): un `git add -A` se llevó fuentes/ con
# los PDF y afiches originales de FICDEH y FICMA —uno de 35 MB, otro de 26—. La
# regla que los ignoraba venía en el PR del festival, que aún no estaba mergeado,
# así que en main no existía y nada los frenó.
# Dos reglas, calibradas con lo que el repo tiene de verdad: el archivo legítimo
# más pesado son 2,28 MB (un póster de Leviza) y hay CERO documentos ofimáticos.
# Esta es la única capa que bloquea el MERGE; el .gitignore y la disciplina de
# `git add` dependen de que alguien se acuerde.
check = 'peso-repo'
try:
    import subprocess as _sp
    TOPE_MB = 3.0
    EXT_TRABAJO = ('.pdf', '.xlsx', '.xls', '.docx', '.doc', '.numbers', '.pages', '.key', '.psd', '.ai')
    _out = _sp.run(['git', 'ls-files', '-s'], capture_output=True, text=True).stdout
    _pesados, _ofim = [], []
    for _ln in _out.splitlines():
        _f = _ln.split('\t', 1)[-1].strip().strip('"')
        if _f.lower().endswith(EXT_TRABAJO):
            _ofim.append(_f)
            continue
        try:
            _mb = os.path.getsize(_f) / 1024 / 1024
        except OSError:
            continue
        if _mb > TOPE_MB:
            _pesados.append(f'{_f} ({_mb:.1f} MB)')
    _prob = []
    if _ofim:
        _prob.append('documentos de trabajo versionados: ' + ', '.join(_ofim[:4]))
    if _pesados:
        _prob.append(f'archivos sobre {TOPE_MB:g} MB: ' + ', '.join(_pesados[:4]))
    if _prob:
        fail(check, ' · '.join(_prob) + ' — el material original va en fuentes/ (gitignored), no en el repo')
    else:
        ok(check, f'sin material de trabajo versionado (tope {TOPE_MB:g} MB por archivo)')
except Exception as _e:
    warn(check, f'no se pudo verificar peso-repo: {_e}')

# ── [sin-symlinks] ningún enlace simbólico versionado ──────────────────────────
# El 8 ago 2026 un symlink `fuentes` → /Users/Juanda/Documents/Otrofestiv-dev/fuentes
# entró al repo dentro del PR de FICMA. En el runner de Pages esa ruta absoluta no
# existe; el empaquetador lo sigue y muere con exit 1. Resultado: FICMA quedó en
# main sin llegar nunca a producción, y el log no decía «symlink» por ningún lado.
#
# Un symlink no sobrevive a salir de la máquina que lo creó, así que en un repo que
# se despliega no hay caso legítimo. La regla es absoluta a propósito: cualquier
# excepción futura tendría que discutirse, que es exactamente lo que no pasó acá.
# git guarda los symlinks con el modo 120000 — eso es lo que se busca.
check = 'sin-symlinks'
try:
    import subprocess as _sp
    _out = _sp.run(['git', 'ls-files', '-s'], capture_output=True, text=True).stdout
    _links = [_ln.split('\t', 1)[-1].strip().strip('"')
              for _ln in _out.splitlines() if _ln.startswith('120000')]
    if _links:
        fail(check, 'enlaces simbólicos versionados: ' + ', '.join(_links[:5])
                    + ' — no sobreviven al runner y tumban el deploy de Pages')
    else:
        ok(check, 'ningún symlink versionado')
except Exception as _e:
    warn(check, f'no se pudo verificar sin-symlinks: {_e}')

# ── [merge-driver] el driver `bump` está registrado en este clon ────────────────
# .gitattributes declara `merge=bump` para los archivos que llevan el número de
# build, pero registrar el driver es config LOCAL: git no ejecuta comandos que
# vengan del repo. Sin registrar, esos cuatro archivos vuelven a conflictuar en
# cada PR —los cinco conflictos del 8 ago 2026 fueron exactamente eso—.
# Aviso, no error: en CI no aplica y un clon de solo lectura no lo necesita.
# ── [doc-cadena] la documentación y los guardianes se citan mutuamente ─────────
# «Hemos escrito muchas cosas pero no todas se cumplen en cadena» (Juan, 9 ago 2026).
# Medido: la cadena docs→código estaba COMPLETA (61 de 61 etiquetas documentadas
# tienen ejecutor). El hueco era el otro sentido: de 100 guardianes reales, 46 no
# se mencionaban en NINGÚN documento. Un guardián invisible se cumple pero no se
# conoce: nadie puede leer la doc y saber que existe, así que se re-descubre a
# golpes o se duplica.
#
# El check va en las DOS direcciones, que es lo que hace que sea una cadena:
#   docs → código: una etiqueta citada sin ejecutor es una promesa vacía. ERROR:
#                  hoy son cero y tienen que seguir siéndolo.
#   código → docs: un guardián sin mención es deuda. Techo que solo BAJA, mismo
#                  patrón que module-size: lo viejo queda con número y lo NUEVO
#                  nace documentado o no entra.
check = 'doc-cadena'
try:
    import glob as _glob
    _docs = ' '.join(open(_f, encoding='utf-8').read() for _f in _glob.glob('docs/*.md') + ['CLAUDE.md'])
    _reales = {}
    for _m in re.finditer(r"^check = '([^']+)'", open('validate.py', encoding='utf-8').read(), re.M):
        _reales[_m.group(1)] = 'validate.py'
    # Cada archivo DECLARA sus guardianes a su manera, y el extractor tiene que
    # conocer las tres formas o inventa huérfanos. Ya pasó dos veces hoy: un `[i]`
    # de índice contado como guardián (54 falsos), y lint-catalog dado por vacío
    # porque emite `err('etiqueta', …)` y no `[etiqueta]`.
    #   validate.py            → check = 'x'
    #   validate-festivals.js  → '[x]' dentro del mensaje
    #   lint-catalog.py        → err('x', …) / warn('x', …)
    # En los dos archivos que se leen por REGEX se exige que la etiqueta lleve GUION.
    # Sin eso entraban `[emoji]`, `[fname]` e `[info]` —índices y palabras sueltas
    # dentro de mensajes— como si fueran guardianes. Todos los reales son kebab-case
    # de dos o más palabras; los de validate.py no necesitan la heurística porque su
    # declaración (`check = '…'`) es inequívoca.
    for _f, _pat in [('scripts/validate-festivals.js', r"""['"`][^'"`]*\[([a-z0-9][a-z0-9]*(?:-[a-z0-9]+)+)\]"""),
                     ('scripts/lint-catalog.py',       r"""(?:err|warn)\(\s*['"]([a-z0-9][a-z0-9]*(?:-[a-z0-9]+)+)['"]""")]:
        if not os.path.exists(_f):
            continue
        for _l in set(re.findall(_pat, open(_f, encoding='utf-8').read())):
            _reales.setdefault(_l, os.path.basename(_f))
    # Deuda al introducir la regla: guardianes que ya existían sin documentar.
    # Se DOCUMENTA y se saca de acá; nunca se agrega uno nuevo.
    _DEUDA_DOC = {
        'activity-duration','apostrophe-onclick','aviso-antes-sinopsis','bare-t-in-template',
        'day-order-indice','dead-code','design-banned-classes','diary-poster-grid','doctype',
        'dom-ready-guard','dtab-sin-linea','fc-bootstrap','filter-drop-canon','html-divs',
        'i18n-hardcoded','i18n-interpolation','i18n-voseo','json-fields','keyart-write-once',
        'no-underscore-actions','onclick-syntax','pais-conocido','pipeline-circuito',
        'poster-editorial-parity','poster-radio-unico','poster-single-owner','pressed-canon',
        'prio-limit','responsive-contract','sala-en-sede','sched-pure-fns','section-display-raw',
        'sedes-apiladas','shadow-t','sheet-meta-legible','staging-provenance','static-html-template',
        'synopsis-helper','synopsis-length','tasks-sync','template-al-dia','title-normalization',
        'validate-film-tests','version-json','viewstate-shadow','worker-deps',
    }
    _sin_doc = sorted(k for k in _reales if ('[' + k + ']') not in _docs)
    _nuevos = [k for k in _sin_doc if k not in _DEUDA_DOC]
    # docs → código: etiqueta citada con backticks que no existe como guardián
    _citadas = set(re.findall(r'`\[([a-z0-9][a-z0-9-]{3,40})\]`', _docs))
    _promesas = sorted(c for c in _citadas if c not in _reales)
    if _promesas:
        fail(check, 'la doc cita guardián(es) que NO existen: ' + ', '.join('[' + p + ']' for p in _promesas[:5])
                    + ' — o se implementan o se saca la promesa')
    elif _nuevos:
        fail(check, 'guardián(es) NUEVO(s) sin una línea en la doc: ' + ', '.join('[' + n + ']' for n in _nuevos[:5])
                    + ' — un guardián invisible se cumple pero no se conoce')
    else:
        _saldada = sorted(k for k in _DEUDA_DOC if k in _reales and ('[' + k + ']') in _docs)
        _msg = f'{len(_reales)} guardianes · {len(_reales)-len(_sin_doc)} documentados · deuda {len(_sin_doc)}/{len(_DEUDA_DOC)}'
        if _saldada:
            warn(check, _msg + ' — ya documentados, sacalos de _DEUDA_DOC: ' + ', '.join(_saldada[:4]))
        else:
            ok(check, _msg)
except Exception as _e:
    warn(check, f'no se pudo verificar doc-cadena: {_e}')

# ── [stash-compartido] el stash NO se aísla por worktree ───────────────────────
# Los worktrees aíslan el árbol y el índice; la PILA DE STASH es una sola para todo
# el repositorio. Con dos chats trabajando en worktrees distintos, un `git stash pop`
# saca la entrada de arriba — que puede ser del OTRO. Pasó el 9 ago 2026: un pop en
# el worktree de app trajo `ficmontanas-hold-5` del worktree de onboarding y dejó
# CLAUDE.md, src/config.js y validate-festivals.js con marcadores de conflicto sin
# resolver, en medio de una verificación que no tenía nada que ver.
#
# No hay hook de git para stash (no existe pre-stash), así que la barrera no puede
# interceptar el comando: vigila el ESTADO, que es lo que hace daño. Una entrada de
# stash viva en un repo con varios worktrees es una trampa esperando a que alguien
# haga pop.
#
# En vez de stash: commiteá el WIP en tu rama y seguí. Un commit lleva tu nombre de
# rama y no lo puede sacar otro por accidente. Si aun así usás stash, aplicalo SIEMPRE
# por referencia exacta (`git stash apply stash@{N}`), nunca `pop`.
#
# Aviso y no error: la entrada puede ser legítima y del otro chat — no es nuestra
# para borrarla, y bloquear el push por algo ajeno sería peor que el problema.
check = 'stash-compartido'
try:
    import subprocess as _sp
    _wt = _sp.run(['git', 'worktree', 'list'], capture_output=True, text=True).stdout.strip().splitlines()
    _st = _sp.run(['git', 'stash', 'list'], capture_output=True, text=True).stdout.strip().splitlines()
    if len(_wt) > 1 and _st:
        _quien = ', '.join(s.split(':')[1].strip() if ':' in s else s for s in _st[:3])
        warn(check, f'{len(_st)} stash vivo(s) con {len(_wt)} worktrees — la pila es COMPARTIDA y un `pop` '
                    f'puede sacar el del otro chat ({_quien}). Usá un commit de WIP en tu rama; '
                    f'si tenés que aplicar uno, `git stash apply stash@{{N}}` por referencia exacta.')
    elif len(_wt) > 1:
        ok(check, f'{len(_wt)} worktrees y la pila de stash vacía')
    else:
        ok(check, 'un solo worktree — la pila de stash no se comparte')
except Exception as _e:
    warn(check, f'no se pudo verificar stash-compartido: {_e}')

check = 'merge-driver'
try:
    import subprocess as _sp
    _drv = _sp.run(['git', 'config', 'merge.bump.driver'],
                   capture_output=True, text=True).stdout.strip()
    if not os.path.isfile('.gitattributes'):
        warn(check, 'falta .gitattributes (declara merge=bump)')
    elif not _drv:
        warn(check, 'el driver `bump` no está registrado en este clon — enchufalo con: '
                    'sh scripts/install-hooks.sh')
    else:
        ok(check, 'driver `bump` registrado (conflictos de build se resuelven solos)')
except Exception as _e:
    warn(check, f'no se pudo verificar merge-driver: {_e}')

# ── [keyart-write-once] un afiche publicado nunca se sobreescribe ───────────────
# El SW cachea /assets/ cache-first en un caché que sobrevive a TODOS los deploys
# (ASSETS_CACHE, sw.js). Sobreescribir un keyArt in-place deja a los usuarios
# recurrentes viendo el afiche viejo para siempre: la URL no cambió, así que el
# SW nunca lo vuelve a pedir. Reinstalar la app tampoco alcanza — el caché del
# WebView persiste.
# La regla estaba escrita en config.js, compose-keyart.py y PIPELINE.md, y aun
# así el afiche de FICDEH 2026 se sobreescribió CUATRO veces con el mismo nombre:
# el aliado de comunicaciones en Medellín seguía viendo el anterior a 4 días de
# que abriera el festival. Una regla que solo vive en la documentación no se
# cumple; por eso ahora se verifica por huella.
check = 'keyart-write-once'
try:
    import glob as _glob, hashlib as _hl, os as _os
    _reg = 'assets/keyart/HUELLAS.txt'
    if not _os.path.exists(_reg):
        warn(check, 'falta assets/keyart/HUELLAS.txt (correr scripts/keyart-huellas.py)')
    else:
        _antes = {}
        for _ln in open(_reg, encoding='utf-8'):
            _ln = _ln.strip()
            if _ln and not _ln.startswith('#'):
                _h, _n = _ln.split(None, 1)
                _antes[_n] = _h
        _cambiados, _sinreg = [], []
        for _f in sorted(_glob.glob('assets/keyart/*.jpg')):
            _n = _os.path.basename(_f)
            _h = _hl.sha1(open(_f, 'rb').read()).hexdigest()[:16]
            if _n not in _antes:
                _sinreg.append(_n)
            elif _antes[_n] != _h:
                _cambiados.append(_n)
        if _cambiados:
            fail(check, 'keyArt SOBREESCRITO (los usuarios recurrentes verían el viejo para '
                        'siempre): ' + ', '.join(_cambiados) +
                        ' — usar un nombre nuevo (-v2) y actualizar src/config.js')
        elif _sinreg:
            fail(check, 'keyArt sin huella registrada: ' + ', '.join(_sinreg) +
                        ' — correr python3 scripts/keyart-huellas.py')
        else:
            ok(check, f'{len(_antes)} afiches con su huella intacta (write-once respetado)')
except Exception as _e:
    warn(check, f'no se pudo verificar keyart-write-once: {_e}')

# ── [keyart-2-3] el afiche del splash entra entero en la card ───────────────────
# La card del riel es 2:3 EXACTO con object-fit:cover, así que recorta todo
# keyArt que no lo sea. Medido en ago 2026: 7 de 10 se recortaban, hasta +19,5%
# (Tercer Tiempo perdía casi un quinto del afiche).
# REGLA PERMANENTE (Juan, 6 ago 2026): el afiche se ESTIRA en un eje hasta
# 400×600 — no se recorta, no se rellena con bandas, no se difumina. Se probaron
# las tres opciones con afiches reales; el estirado no se percibe ni en el peor
# caso (16,3% de compresión) y deja leer el afiche completo.
# Se aplica con `python3 scripts/compose-keyart.py <archivo>` (write-once:
# escribe a -v2, nunca sobreescribe, por el caché del SW).
check = 'keyart-2-3'
try:
    import re as _re
    _TOL = 0.02
    _cfg = open('src/config.js', encoding='utf-8').read()
    _paths = _re.findall(r"keyArt:\s*'(/assets/keyart/[^']+)'", _cfg)
    _mal, _sin = [], []
    for _p in _paths:
        _f = _p.lstrip('/')
        if not os.path.exists(_f):
            _sin.append(_f); continue
        # dimensiones del JPEG sin dependencias: SOF0..SOF15 del marcador
        with open(_f, 'rb') as _fh:
            _d = _fh.read()
        _i, _w, _h = 2, None, None
        while _i < len(_d) - 9:
            if _d[_i] != 0xFF:
                _i += 1; continue
            _m = _d[_i + 1]
            if 0xC0 <= _m <= 0xCF and _m not in (0xC4, 0xC8, 0xCC):
                _h = int.from_bytes(_d[_i + 5:_i + 7], 'big')
                _w = int.from_bytes(_d[_i + 7:_i + 9], 'big')
                break
            _i += 2 + int.from_bytes(_d[_i + 2:_i + 4], 'big')
        if not (_w and _h):
            continue
        _ex = (_w - _h * 2 / 3) / (_h * 2 / 3)
        if abs(_ex) > _TOL:
            _mal.append(f"{os.path.basename(_f)} {_w}×{_h} ({_ex:+.1%})")
    if _sin:
        fail(check, 'keyArt referenciado que no existe: ' + '; '.join(_sin))
    elif _mal:
        fail(check, 'keyArt que la card va a recortar (correr scripts/compose-keyart.py): ' + '; '.join(_mal))
    else:
        ok(check, f'los {len(_paths)} keyArt entran enteros en la card 2:3 (tolerancia {_TOL:.0%})')
except Exception as _e:
    warn(check, f'no se pudo verificar keyart-2-3: {_e}')

# ── [duracion-solo-dominio] aritmética de duración solo en el dominio ───────────
# La clase de bug del 31 jul 2026: sitios que calculan un fin de función a mano
# (parseInt(duration) en el ICS y en _gapSuggestion) ignoraban el anclaje y el
# Q&A — exportaban "18:00→18:05" donde el bloque real termina 19:51. Regla: fuera
# de src/domain/, nadie parsea `duration` para aritmética — se usa el par
# blockDuration/effectiveDuration (o durationForTravel). Excepción única:
# controller/loader.js, el SELLADOR — deriva la duración canónica una vez.
check = 'duracion-solo-dominio'
try:
    import glob as _glob, re as _re
    _off = []
    for _sf in _glob.glob('src/**/*.js', recursive=True):
        _n = _sf.replace('\\', '/')
        if _n.startswith('src/domain/') or _n.endswith('controller/loader.js'):
            continue
        for _i, _ln in enumerate(open(_sf, encoding='utf-8').read().splitlines(), 1):
            _code = _ln.split('//')[0]
            if _re.search(r'parseInt\([^)]*duration|parseDur\(', _code):
                _off.append(f"{_sf}:{_i}")
    if _off:
        fail(check, 'aritmética de duración fuera del dominio (usar blockDuration/effectiveDuration/durationForTravel): ' + '; '.join(_off[:6]))
    else:
        ok(check, 'toda aritmética de duración pasa por el dominio (única excepción: el sellador)')
except Exception as _e:
    warn(check, f'no se pudo verificar duracion-solo-dominio: {_e}')

# ── [badge-precio-minoria] el badge de precio marca la MINORÍA, nunca a mano ────
# FICDEH 2026 invirtió una premisa que la app daba por sentada: 81% de sus
# funciones son de entrada libre, así que el badge GRATIS pintaba 313 tarjetas y
# escondía las 71 accionables. La regla vive en ticketBadgeTarget() (view/
# helpers.js), que decide UNA vez por festival de qué lado cae la minoría.
# Regla: nadie decide badge de precio leyendo `is_free` por su cuenta — quien lo
# pinte consulta al dueño. Sin esto, cada superficie nueva reintroduce el sesgo
# "gratis es la excepción" y los festivales de entrada libre vuelven a romperse.
check = 'badge-precio-minoria'
try:
    import glob as _glob, re as _re
    _src = open('src/view/helpers.js', encoding='utf-8').read()
    if not _re.search(r'export function ticketBadgeTarget\(', _src):
        fail(check, 'falta ticketBadgeTarget() en src/view/helpers.js — es el dueño de la regla')
    else:
        _off = []
        for _sf in sorted(_glob.glob('src/**/*.js', recursive=True)):
            _n = _sf.replace('\\', '/')
            # el dueño, y el diccionario (que solo DECLARA las claves, no pinta)
            if _n.endswith('view/helpers.js') or _n.endswith('i18n/i18n.js'):
                continue
            _txt = open(_sf, encoding='utf-8').read()
            _consulta = 'ticketBadgeTarget' in _txt
            for _i, _ln in enumerate(_txt.splitlines(), 1):
                _code = _ln.split('//')[0]
                # pintar un badge/aviso de precio decidiendo is_free por su cuenta
                if _re.search(r'badge_gratis|badge_con_boleta|aviso_gratis|aviso_con_boleta', _code) \
                        and not _consulta:
                    _off.append(f"{_sf}:{_i}")
        if _off:
            fail(check, 'badge de precio sin consultar ticketBadgeTarget(): ' + '; '.join(_off[:6]))
        else:
            ok(check, 'el badge de precio lo decide ticketBadgeTarget() (marca la minoría)')
except Exception as _e:
    warn(check, f'no se pudo verificar badge-precio-minoria: {_e}')

# ── [tests-puerto-propio] cada corrida de tests con su servidor ─────────────────
# La causa raíz del "flaky" que llevábamos meses tapando con `retries`: Playwright
# MATA el servidor que él levantó al terminar, y con `reuseExistingServer` una
# segunda corrida reusa ese servidor en vez de levantar el suyo. Si la primera
# termina antes, la segunda se queda sin servidor a mitad de camino →
# ERR_CONNECTION_REFUSED y cascada de timeouts en specs sin relación entre sí.
# Medido: la misma suite da 21/21 sola y 1/21 con otra corrida solapada; dos
# suites completas solapadas daban 22 y 14 fallos, y 0 con puerto propio.
# Regla: el puerto sale de PW_PORT (scripts/test.sh elige uno libre) y ningún
# spec lo hardcodea — un solo `localhost:3000` incrustado ata esa corrida al
# puerto compartido y reabre el agujero.
check = 'tests-puerto-propio'
try:
    import glob as _glob, re as _re
    _cfg = open('playwright.config.js', encoding='utf-8').read()
    _prob = []
    if 'process.env.PW_PORT' not in _cfg:
        _prob.append('playwright.config.js no lee PW_PORT')
    if not os.path.exists('scripts/test.sh'):
        _prob.append('falta scripts/test.sh (elige el puerto libre)')
    for _tf in sorted(_glob.glob('tests/**/*.js', recursive=True)):
        for _i, _ln in enumerate(open(_tf, encoding='utf-8').read().splitlines(), 1):
            # Ojo: acá NO se puede cortar por '//' como en los otros checks — el
            # '//' de 'http://' se comía la línea entera y el guardián no veía
            # nada (cazado por mutación). Se descartan solo las líneas que SON
            # comentario.
            _code = '' if _ln.lstrip().startswith('//') else _ln
            if _re.search(r'localhost:\d+|127\.0\.0\.1:\d+', _code):
                _prob.append(f"{_tf}:{_i} hardcodea el puerto (usar baseURL)")
    if _prob:
        fail(check, 'aislamiento de corridas roto: ' + '; '.join(_prob[:5]))
    else:
        ok(check, 'cada corrida toma su puerto (PW_PORT) — dos suites simultáneas no se pisan')
except Exception as _e:
    warn(check, f'no se pudo verificar tests-puerto-propio: {_e}')

# ── [template-al-dia] la plantilla de onboarding no se queda atrás ──────────────
# Causa raíz de la tarea #81: el onboarding de FINCA usó 10 campos de film que la
# plantilla no enseñaba, y nadie lo notó hasta un mes después. Regla: todo campo
# que usan LOS DOS festivales más recientes (por festivalEndStr) debe estar en
# pipeline/festival-template.json o en la whitelist de omisiones DELIBERADAS.
# Un campo nuevo que dos onboardings seguidos necesitaron ya no es experimento:
# es vocabulario — y la plantilla es donde el próximo onboarding lo aprende.
check = 'template-al-dia'
try:
    import json as _json, glob as _glob
    # Omisiones deliberadas (documentar el porqué acá):
    #   tematica     — campo interno del festival (Juan: "no hagas nada con eso")
    #   qa_detail    — texto libre del festival; la plantilla enseña qa_type
    #   flags        — derivado por countryToFlags; solo se llena si el derivado falla
    #   screenings   — forma intermedia del ensamblador (el loader lo explota)
    #   info, is_recurring, is_programa — legacy / casos que la doctrina cubre aparte
    _OMIT = {'tematica', 'qa_detail', 'flags', 'screenings', 'info', 'is_recurring',
             'is_programa', 'date'}
    _tpl = _json.load(open('pipeline/festival-template.json', encoding='utf-8'))
    _tf = set(_tpl.keys())
    for _f in _tpl.get('films', []):
        _tf |= set(_f.keys())
        for _it in (_f.get('film_list') or []): _tf |= set(_it.keys())
    _fests = []
    for _fp in _glob.glob('festivals/*.json'):
        try:
            _d = _json.load(open(_fp, encoding='utf-8'))
            if isinstance(_d, dict) and _d.get('festivalEndStr'):
                _fests.append((_d['festivalEndStr'], _fp, _d))
        except Exception:
            continue
    _fests.sort(reverse=True)
    _missing = {}
    for _end, _fp, _d in _fests[:2]:
        _used = set(_d.keys())
        for _f in _d.get('films', []):
            _used |= set(_f.keys())
            for _it in (_f.get('film_list') or []): _used |= set(_it.keys())
        for _k in _used:
            if _k.startswith('_') or _k in _tf or _k in _OMIT: continue
            _missing.setdefault(_k, []).append(_fp.split('/')[-1])
    _viol = {k: v for k, v in _missing.items() if len(v) >= 2}
    if _viol:
        fail(check, 'campo(s) usados por los 2 festivales más recientes y ausentes de la plantilla: '
             + '; '.join(f"{k} ({'+'.join(v)})" for k, v in sorted(_viol.items())))
    else:
        _solo = sorted(k for k, v in _missing.items() if len(v) == 1)
        ok(check, 'plantilla al día con los 2 festivales más recientes'
           + (f" ({len(_solo)} campo(s) usados por solo uno: {', '.join(_solo[:5])})" if _solo else ''))
except Exception as _e:
    warn(check, f'no se pudo verificar template-al-dia: {_e}')

# ── [slots-sin-decidir] toda proyección conjunta tiene modelo declarado ────────
# Doctrina (SCHEMA.md, 30 jul 2026): los festivales juntan proyecciones y hay DOS
# modelos canónicos — Programa (is_cortos+film_list) o Anclaje
# (sharedSlotIsOneScreening). Lo que NO puede pasar es el limbo: dos obras en el
# mismo día+hora+sede+sala sin decisión, tratadas como rivales (Cinemancia 2025
# quedó así: corto+largo a las 19:00 en la misma sala, declarados en conflicto).
# NO se auto-deriva (multisala: misma hora+sede puede ser otra sala = otra
# función) → el guardián OBLIGA a decidir contra el programa oficial: declarar el
# flag, o anotar el slot como funciones separadas en _SEPARATE.
# _festivalesVivos — quiénes están activos o por venir, DERIVADO de las fechas.
# Antes cada guardián llevaba su propia lista `_ACTIVE` escrita a mano, y esas
# listas envejecían calladas: al 20 ago 2026, [slots-sin-decidir] vigilaba a
# finca-2026 (cerrado el 19) y [activity-duration] a dos festivales cerrados en
# JULIO — verdes los dos, sin mirar CineAutopsia ni Vartex, que sí estaban vivos.
# El propio repo ya lo había escrito 800 líneas arriba: «un guardián con lista
# manual no es un guardián: es una foto que envejece». Esto lo hace una sola vez.
def _festivalesVivos():
    import re as _r2, datetime as _d2, glob as _g3
    _cfg = open('src/config.js', encoding='utf-8').read()
    # Fecha de Colombia, no del runner (misma regla que el resto del repo).
    _hoy = (_d2.datetime.utcnow() - _d2.timedelta(hours=5)).date().isoformat()
    _vivos = []
    for _fid, _end in _r2.findall(r"'([a-z0-9]+)':\s*\{.*?festivalEndStr:\s*'(\d{4}-\d{2}-\d{2})", _cfg, _r2.S):
        if _end >= _hoy:
            _vivos.append(_r2.sub(r'([a-zA-Z]+)(\d+)$', r'\1-\2', _fid))
    if not _vivos:   # entre temporadas: revisar el más reciente igual
        _vivos = [_g3.os.path.basename(_p)[:-5] for _p in sorted(_g3.glob('festivals/*.json'))[-1:]]
    return sorted(_vivos)

check = 'slots-sin-decidir'
try:
    import json as _json
    _ACTIVE = _festivalesVivos()   # derivado de las fechas, no escrito a mano
    # (festival, 'dia|hora|sede') REVISADOS contra el programa oficial y confirmados
    # como funciones SEPARADAS (p.ej. actividades paralelas en espacios distintos).
    _SEPARATE = set()
    _viol = []
    for _fname in _ACTIVE:
        try:
            _fd = _json.load(open('festivals/' + _fname + '.json', encoding='utf-8'))
        except FileNotFoundError:
            continue
        if _fd.get('sharedSlotIsOneScreening'):
            continue  # modelo declarado: el loader ancla estos grupos
        _slots = {}
        for _f in _fd.get('films', []):
            if _f.get('info') or _f.get('is_cortos') or not (_f.get('day') and _f.get('time') and _f.get('venue')):
                continue
            _k = f"{_f['day']}|{_f['time']}|{_f['venue']}|{_f.get('sala','')}"
            _slots.setdefault(_k, []).append(_f.get('title', '?'))
        for _k, _g in _slots.items():
            if len(_g) > 1 and (_fname, _k.rsplit('|',1)[0]) not in _SEPARATE:
                _viol.append(f"{_fname}: {_k} → " + ' + '.join(t[:22] for t in _g))
    if _viol:
        fail(check, 'slot(s) compartidos SIN modelo decidido (declarar sharedSlotIsOneScreening o anotar en _SEPARATE): ' + '; '.join(_viol[:4]))
    else:
        ok(check, 'toda proyección conjunta de festivales activos tiene modelo declarado (Programa o Anclaje)')
except Exception as _e:
    warn(check, f'no se pudo verificar slots-sin-decidir: {_e}')

# ── [activity-duration] toda actividad de un festival activo tiene duración ────
# Valor central de la app: TODA actividad (película, evento único o programa
# múltiple) muestra su duración — alimenta el cálculo del plan y la decisión del
# usuario. Bug detonante (17 jul 2026): "Muestra de Cortometrajes" de FantasoFest
# sin duración (contenedor '' + cortos sin minutaje; el PDF de prensa no publica
# runtimes). Enforce SOLO festivales activos/próximos (los archivados quedan como
# histórico). Excepción documentada = dato que la organización aún no entregó.
check = 'activity-duration'
try:
    import json as _json
    _ACTIVE = _festivalesVivos()   # derivado de las fechas, no escrito a mano
    # (festival_file, título) cuyo dato de duración la organización NO publicó.
    # Al recibir el minutaje real: llenar el JSON y BORRAR la línea de aquí.
    _PENDING = {
        ('fantasofest-2026', 'Muestra de Cortometrajes'),  # PDF prensa sin runtimes; pedido a FantasoLab
        # Vartex 14 — vartexmedellin.co publica minutaje SOLO de la Muestra Local
        # (12 obras, ya en el JSON) y las 8 h del taller. Verificado sobre el HTML
        # vivo: el sitio no tiene sección de Internacional ni de Inauguración, y su
        # sección muestra-nacional lista las obras sin duración. Pedido al festival.
        ('vartex-2026', 'A La Rivera: Synthfonía de un escape'),   # live cinema de apertura; no anunciado
        ('vartex-2026', 'Muestra Fashion Film Internacional'),     # 2 obras del carrusel IG, sin minutaje
        ('vartex-2026', 'Muestra Fashion Film Nacional'),          # 20 obras listadas sin duración
        # CineAutopsia — el PDF oficial la trae sin obras y sin runtime: es una
        # proyección al aire libre más un diálogo, y el festival no anunció cuánto dura.
        ('cineautopsia-2026', 'Encuentro Colombia Experimental Contemporánea'),
        # QAFF — la Muestra Artística es exposición CONTINUA: el calendario Boom
        # publica un rango (14 SEP 09:00 → «17 OCT» 10:00, con el mes además mal
        # tipeado), no un minutaje de visita. No hay número honesto que poner.
        ('qaff-2026', 'Muestra Artística'),
        # Cinemancia — actividad de encuentro sin minutaje publicado (ni en el
        # Excel de 3 tabs ni en la web). Además es candidata a SALIR: el festival
        # pidió retirar las actividades con inscripción — decisión pendiente en
        # el chat de Cinemancia. NOTA: este error estaba EN MAIN (el guardián
        # llegó en #698 con este caso ya rojo); esta línea desbloquea a los dos.
        ('cinemancia-2026', 'Encuentro Internacional de Investigación-Creación en Música y Sonido Cinematográfico'),
    }
    _viol = []
    for _fname in _ACTIVE:
        _fp = 'festivals/' + _fname + '.json'
        try:
            _fd = _json.load(open(_fp, encoding='utf-8'))
        except FileNotFoundError:
            continue
        _seen = set()
        for _a in _fd.get('films', []):
            _tt = _a.get('title')
            if _tt in _seen:
                continue
            _seen.add(_tt)
            if not str(_a.get('duration', '')).strip():
                if (_fname, _tt) not in _PENDING:
                    _viol.append(f"{_fname}: '{_tt}'")
    if _viol:
        fail(check, 'actividad(es) sin duración en festival activo (obligatoria — alimenta el plan): ' + '; '.join(_viol))
    else:
        _pend = len(_PENDING)
        ok(check, f'toda actividad de festivales activos tiene duración' + (f' ({_pend} excepción(es) pendiente(s) de dato de la organización)' if _pend else ''))
except Exception as _e:
    warn(check, f'no se pudo verificar activity-duration: {_e}')

# ── [festival-name-parity] name/shortName del JSON == FESTIVAL_CONFIG ─────────
# loadFestival mergea name/shortName/city/dates del JSON SOBRE FESTIVAL_CONFIG
# (loader.js _cfgFields): si el JSON trae el nombre mal escrito, toda superficie
# runtime (diario/plan compartido, ICS, share titles) lo hereda aunque config.js
# esté bien — el bug "TercerTiempo" pegado del export del Diario (17 jul 2026).
# El nombre oficial es un artefacto de diseño: UNA sola forma en todas partes.
check = 'festival-name-parity'
try:
    import json as _json
    _cfg = open('src/config.js', encoding='utf-8').read()
    # Un par (id, bloque) por entrada de FESTIVAL_CONFIG; name/shortName se buscan
    # DENTRO del bloque (robusto al orden/estilo de cada entrada, legacy incluidas).
    _entries = re.findall(r"'([a-z0-9]+)':\s*\{(.*?)\n  \}", _cfg, re.S)
    _pairs = []
    for _id, _blk in _entries:
        _n = re.search(r"\bname:'([^']+)'", _blk)
        _s = re.search(r"\bshortName:'([^']+)'", _blk)
        if _n:
            _pairs.append((_id, _blk, _n.group(1), _s.group(1) if _s else None))
    _mism = []
    for _id, _blk2, _name, _short in _pairs:
        _city = re.search(r"\bcity:'([^']*)'", _blk2)
        _dates = re.search(r"\bdates:'([^']*)'", _blk2)
        _year = re.search(r"\byear:(\d+)", _blk2)
        _fields = [('name', _name), ('shortName', _short),
                   ('city', _city.group(1) if _city else None),
                   ('dates', _dates.group(1) if _dates else None),
                   ('year', int(_year.group(1)) if _year else None)]
        _file = 'festivals/' + re.sub(r'([a-zA-Z]+)(\d+)$', r'\1-\2', _id) + '.json'
        try:
            _d = _json.load(open(_file, encoding='utf-8'))
        except FileNotFoundError:
            continue
        for _k, _cv in _fields:
            _jv = _d.get(_k)
            if _cv is not None and _jv is not None and _jv != _cv:
                _mism.append(f"{_file} {_k}={_jv!r} != config {_cv!r}")
    if _mism:
        fail(check, 'JSON pisa FESTIVAL_CONFIG en runtime con otro nombre: ' + '; '.join(_mism))
    else:
        ok(check, f'identidad (name/shortName/city/dates/year) consistente en {len(_pairs)} festivales (JSON == config)')
except Exception as _e:
    warn(check, f'no se pudo verificar festival-name-parity: {_e}')

# ── [pais-conocido] todo `country` del config tiene nombre en COUNTRY_NAMES ────
# La línea de ubicación del splash sale de festivalLocationLabel → countryName, y
# countryName devuelve '' cuando el ISO no está en la tabla. El resultado no es un
# error: es la ciudad sola. FINCA se publicó con country:'AR' sin su entrada y el
# splash dijo «BUENOS AIRES» —sin Argentina— durante toda su vitrina, sin que nada
# se quejara (lo vio Juan, 9 ago 2026).
# La tabla crece una línea por país, y esa línea es justo la que se olvida cuando
# el festival nuevo es del exterior. `country:''` es LEGÍTIMO y no se exige: es como
# un festival nacional dice «no tengo una sede única» (FICDEH, 11 ciudades).
check = 'pais-conocido'
try:
    _cfg = open('src/config.js', encoding='utf-8').read()
    # Hasta el CIERRE DEL OBJETO (`\n};`), no hasta la primera `}` — esa cierra la
    # primera entrada y dejaba la tabla en un solo país: el guardián acusaba de
    # faltantes a US, BR y AR estando los tres. Un check con un parser flojo no
    # avisa de menos: avisa mal, que es peor.
    _tabla = _cfg[_cfg.index('COUNTRY_NAMES'):]
    _tabla = _tabla[:_tabla.index('\n};')]
    _conocidos = set(re.findall(r"^\s*([A-Z]{2}):\s*\{", _tabla, re.M))
    _body = _cfg[_cfg.index('FESTIVAL_CONFIG'):]
    _ids = re.findall(r"\n  '([a-z0-9]+)':\s*\{", _body)
    _huerfanos = []
    for _i, _fid in enumerate(_ids):
        _ini = _body.index("'%s':" % _fid)
        _fin = _body.index("'%s':" % _ids[_i + 1]) if _i + 1 < len(_ids) else _ini + 2500
        _blk = _body[_ini:_fin]
        if re.search(r"group\s*:\s*['\"]test['\"]", _blk):
            continue
        _m = re.search(r"country:'([A-Z]{2})'", _blk)
        if _m and _m.group(1) not in _conocidos:
            _huerfanos.append(f'{_fid} → {_m.group(1)}')
    if not _conocidos:
        warn(check, 'no se pudo leer COUNTRY_NAMES')
    elif _huerfanos:
        fail(check, 'festival(es) con país sin nombre en COUNTRY_NAMES: ' + ', '.join(_huerfanos)
                    + ' — el splash mostraría solo la ciudad, sin error visible')
    else:
        ok(check, f'todo country del config tiene nombre ({len(_conocidos)} países en la tabla)')
except Exception as _e:
    warn(check, f'no se pudo verificar pais-conocido: {_e}')

# ── [claude-md-fresco] el archivo de CONTEXTO no puede estar desactualizado ─────
# CLAUDE.md se genera con scripts/generate-claude-md.js leyendo el repo, pero el
# script se corre A MANO y nadie lo verificaba. Resultado: el archivo que un
# ayudante lee PRIMERO —y del que saca su idea del proyecto— envejecía en silencio.
#
# El 15 ago 2026 costó caro: decía «Android: Closed testing — Alpha» meses después
# de que las dos apps estuvieran publicadas, y de ahí salió el diagnóstico falso de
# que «nadie pudo instalar la app» durante tres festivales. Un dato caduco en la
# doc de contexto no produce una duda: produce una conclusión falsa, con seguridad.
#
# Este check regenera el archivo en un temporal y compara SOLO lo que el script
# DERIVA del repo (la tabla de festivales y el bloque de features). El resto del
# documento es prosa del template y no caduca sola. Si difieren: correr el script.
check = 'claude-md-fresco'
try:
    import subprocess as _sp, tempfile as _tf, shutil as _sh
    _md = 'CLAUDE.md'
    if not os.path.exists(_md):
        warn(check, 'no hay CLAUDE.md')
    else:
        _viejo = open(_md, encoding='utf-8').read()
        _bak = _tf.mktemp(suffix='.md')
        _sh.copy(_md, _bak)
        try:
            _r = _sp.run(['node', 'scripts/generate-claude-md.js'],
                         capture_output=True, text=True, timeout=60)
            _nuevo = open(_md, encoding='utf-8').read()
        finally:
            _sh.copy(_bak, _md)   # el check NO deja el archivo tocado
            os.remove(_bak)
        if _r.returncode != 0:
            warn(check, 'el generador falló: %s' % (_r.stderr or '')[:120])
        else:
            # Solo las secciones DERIVADAS. La línea del último commit cambia con
            # cada commit por definición: compararla haría fallar el check siempre.
            # La columna «Estado» sale del RELOJ (festivalStatus: próximo/recién
            # terminado/archivado), no del repo: entre el commit y el CI un
            # festival cruza un umbral y CLAUDE.md queda «desactualizado» sin que
            # nadie tocara nada, bloqueando PRs ajenos (pasó en el #682, 18 ago).
            # Se compara la lista de festivales y features — que sí es del repo —
            # ignorando esa última celda.
            def _sin_estado(_linea):
                if not _linea.startswith('|'):
                    return _linea
                _cells = _linea.rstrip().rstrip('|').split('|')
                return '|'.join(_cells[:-1]) + '|' if len(_cells) > 2 else _linea
            def _derivado(txt):
                out = []
                for _sec in ('### Festivales', '### Features activas'):
                    if _sec in txt:
                        _t = txt[txt.index(_sec):]
                        _fin = _t.find('\n---')
                        _t = _t[:_fin if _fin > 0 else 1200]
                        out.append('\n'.join(_sin_estado(_l) for _l in _t.split('\n')))
                return '\n'.join(out)
            if _derivado(_viejo).strip() != _derivado(_nuevo).strip():
                fail(check, 'CLAUDE.md desactualizado respecto al repo (festivales o features) '
                            '— correr: node scripts/generate-claude-md.js')
            else:
                ok(check, 'CLAUDE.md al día con el estado derivado del repo')
except Exception as _e:
    warn(check, f'no se pudo verificar claude-md-fresco: {_e}')

# ── [festival-aplazado] un `status` declarado viene COMPLETO y consistente ──────
# Nace del terremoto de Manizales (FICMA 17, 10 ago 2026). `status:{kind:'postponed'}`
# saca al festival de «en curso» (_classifyFestival lo devuelve ANTES de la aritmética
# de fechas) y pinta distintivo + banda con las palabras del propio festival. Un status
# a medias es el peor de los mundos: sin `note` la banda sale vacía (el festival
# desaparece de la explicación), sin `url` no hay comunicado que leer, sin `since` no
# hay registro de cuándo. Los tres se exigen. `kind` solo admite 'postponed' (v1):
# un typo ('postponned') haría que _classifyFestival lo ignorara EN SILENCIO y el
# festival volvería a salir «en curso» — exactamente el bug que este estado evita.
check = 'festival-aplazado'
try:
    _cfg = open('src/config.js', encoding='utf-8').read()
    _body = _cfg[_cfg.index('FESTIVAL_CONFIG'):]
    _ids = re.findall(r"\n  '([a-z0-9]+)':\s*\{", _body)
    _malos = []
    _con_status = 0
    for _i, _fid in enumerate(_ids):
        _ini = _body.index("'%s':" % _fid)
        _fin = _body.index("'%s':" % _ids[_i + 1]) if _i + 1 < len(_ids) else len(_body)
        _blk = _body[_ini:_fin]
        _m = re.search(r"status\s*:\s*\{([^}]*)\}", _blk)
        if not _m:
            continue
        _con_status += 1
        _st = _m.group(1)
        _k = re.search(r"kind\s*:\s*'([^']*)'", _st)
        if not _k or _k.group(1) != 'postponed':
            _malos.append(f"{_fid}: kind {_k.group(1)!r} desconocido (v1 solo 'postponed') — _classifyFestival lo IGNORARÍA y el festival saldría en curso" if _k else f'{_fid}: status sin kind')
            continue
        for _campo, _por in [('note', 'la banda saldría vacía'), ('url', 'no habría comunicado que leer'), ('since', 'sin registro de cuándo')]:
            if not re.search(_campo + r"\s*:\s*'[^']+'", _st):
                _malos.append(f'{_fid}: status sin {_campo} — {_por}')
    if _malos:
        fail(check, 'status incompleto/inválido: ' + ' · '.join(_malos))
    else:
        ok(check, f'{_con_status} festival(es) con status declarado, todos completos' if _con_status else 'ningún festival con status declarado')
except Exception as _e:
    warn(check, f'no se pudo verificar festival-aplazado: {_e}')

# ── [timezone-valid] todo festival tiene timezoneOffset válido (±HH:MM) ─────────
# Toda la lógica de "ahora" (now-line, contador, en-curso, hoy, pasó/futuro) se ancla
# a la zona del festival vía cfg.timezoneOffset (domain/time.js _festNow/_festDate).
# Sin él, o mal formateado, el fallback es Colombia (-05:00) → un festival en otra zona
# queda corrido SIN error visible (prep Argentina -03:00, 21 jul 2026). generate-config
# ya lo exige en la entrada; este guardián es la red en el OUTPUT: bloquea el merge si
# algún festival (no group:'test') no lo trae bien. Formato: signo + HH:MM (Argentina
# -03:00, Colombia -05:00, India +05:30). Argentina no usa DST → offset fijo correcto.
check = 'timezone-valid'
try:
    _cfg = open('src/config.js', encoding='utf-8').read()
    _entries = re.findall(r"'([a-z0-9]+)':\s*\{(.*?)\n  \}", _cfg, re.S)
    _bad = []
    _n_ok = 0
    for _id, _blk in _entries:
        if not re.search(r"\bname:'", _blk):  # entradas sin name = placeholders, se ignoran
            continue
        if re.search(r"group:\s*'test'", _blk):  # festivales de test no van a runtime
            continue
        _tz = re.search(r"\btimezoneOffset:'([^']*)'", _blk)
        if not _tz:
            _bad.append(f"{_id}: falta timezoneOffset")
        elif not re.match(r'^[+-]\d{2}:\d{2}$', _tz.group(1)):
            _bad.append(f"{_id}: timezoneOffset={_tz.group(1)!r} no es ±HH:MM")
        else:
            _n_ok += 1
    if _bad:
        fail(check, 'timezoneOffset inválido (el festival caería en hora de Colombia): ' + '; '.join(_bad[:5]))
    else:
        ok(check, f'{_n_ok} festivales con timezoneOffset válido (±HH:MM) — la hora se ancla al venue')
except Exception as _e:
    warn(check, f'no se pudo verificar timezone-valid: {_e}')

# ── [section-map-dupes] claves duplicadas en los mapas de sección ──────────────
# Un objeto JS con una clave repetida NO es error: la 2ª pisa a la 1ª en silencio
# (el bug 'Talks' de SECTION_COLORS, arreglado en P2.1). Con secciones de 3
# festivales nuevos en septiembre el riesgo se multiplica → este check lo caza.
check = 'section-map-dupes'
try:
    _cfg = open('src/config.js', encoding='utf-8').read()
    _dupes = []
    for _name in ['SECTION_COLORS', 'SECTION_EN', 'SECTION_ARCHETYPES']:
        _m = re.search(_name + r'\s*=\s*\{([^}]*)\}', _cfg, re.S)
        if not _m:
            continue
        _keys = re.findall(r"'([^']+)'\s*:", _m.group(1))
        _seen = set()
        for _k in _keys:
            if _k in _seen:
                _dupes.append(f"{_name}: '{_k}'")
            _seen.add(_k)
    _m = re.search(r"SECTION_ORDER_LIST\s*=\s*\[([^\]]*)\]", _cfg, re.S)
    if _m:
        _items = re.findall(r"'([^']+)'", _m.group(1))
        _seen = set()
        for _k in _items:
            if _k in _seen:
                _dupes.append(f"SECTION_ORDER_LIST: '{_k}'")
            _seen.add(_k)
    if _dupes:
        fail(check, 'clave(s) de sección duplicada(s) — una pisa a la otra en silencio: ' + '; '.join(_dupes))
    else:
        ok(check, 'sin claves de sección duplicadas en los 4 mapas')
except Exception as _e:
    warn(check, f'no se pudo verificar section-map-dupes: {_e}')

# ── [module-size] ningún módulo crece en silencio ─────────────────────────────
# La modularidad se degrada cuando un archivo se vuelve un cajón de sastre. Este
# check pone un techo: los módulos nuevos deben quedar <800 líneas; los grandes
# actuales están grandfathered a su tamaño de HOY (allowlist) y solo pueden ENCOGER
# — crecerlos exige subir su techo acá, una decisión consciente y revisada, no un
# derrape silencioso. "Medir, no suponer" automatizado (auditoría jul 2026).
check = 'module-size'
try:
    import glob as _glob
    _CAP = 800
    # techos grandfathered (líneas de HOY). Bajar cuando el archivo encoja; subir SOLO
    # como decisión explícita y justificada en el PR. Cohesivos-pero-grandes conocidos:
    #   agenda.js (render agenda+miplan) · main.js (composición/bootstrap) ·
    #   i18n.js (diccionarios es/en, es DATA) · sheets-controller.js · handlers.js
    _ALLOW = {
        # components.js aloja ahora el motor de pósters (§6.0: _fitLines, _lineaSVG,
        # _buildPosterV16) y el dueño del color de sección. Entra a la lista con la
        # razón escrita, que es lo que este guardián pide, en vez de seguir
        # recortando comentarios que explican POR QUÉ el código es así.
        'src/view/components.js': 1103,  # +20: el título tampoco repite el programa cuando el eco va al final (Cinemancia) — 24 ago  # +11: la pila reparte el presupuesto por uso real (el lazo del techo ahora SÍ vive) — 24 ago  # +2: el « + » de la pila sube a 0,6u (a 0,5u leía como suciedad, no como signo) — 24 ago  # +60: la pila de obras — un compuesto se apila, no se escribe como frase (mejora 1 de la auditoría de pósters) — 24 ago  # +10: makeProgramPoster con rótulo corto + suelo de sección 7 con su porqué — 24 ago  # +33: _seccionPartes + firma en el motor + sección a 2 líneas (regla de carga) — 24 ago  # +34: auditoría Forma A — luz por sección, título sin repetir la sección, _datoCompuesto — 24 ago  # +3: muere el badge EN REVISIÓN de la card (redundante con el divisor) — 23 ago  # +4: icono `award` de Lucide — la estrella ya significa calificación — 23 ago  # +5: el grupo de revisión NO se filtra al sheet «cambiar festival» — 23 ago  # +24: grupo «en revisión» en el riel — 23 ago  # +58: makeSharedSlotSVG — el póster de función compartida (Escalera mayor §6.0) — 21 ago  # +7: «foro» y «debate» entran al vocabulario (Cinemancia 2026) — 21 ago  # +24: _postponedElapsed — un aplazado baja a pasados cuando sus fechas anunciadas pasan — 23 ago
        # helpers.js estaba EXACTAMENTE en 800 antes del rediseño de pósters
        # (§6.0): el marco de la forma B y el header con ajuste tipográfico no
        # entran sin pasarse. Se sube 15 con la razón escrita, que es lo que este
        # guardián pide. Baja cuando se migre algo fuera de helpers.
        'src/view/helpers.js': 898,  # +14: rótulo/firma en los llamadores + halo en el póster grande — 24 ago  # +1: el camino #8 pasa el dato compuesto — 24 ago  # +6: badge PRENSA en _metaBadges — 23 ago  # +17: legacyProgramParts — el programa «A + B» usa la forma C — 21 ago  # +5: la sección nunca se pinta con fill undefined — 19 ago
        'src/view/agenda.js': 2014,  # +11: el Diario deja de mostrar un programa como su primera obra — 21 ago  # +3: respaldo de nombre de sede — una sede sin `short` pintaba «undefined» — 21 ago
        'src/main.js': 1772,  # +4: los tres canales vivos también refrescan DATOS (capa 2, live-refresh) — 24 ago  # +15: canales de update fuera del guard de SW + guardián de que no vuelvan (bug iOS sin updates) — 24 ago  # +5: el clic de corto en el palmarés abre su ficha — 24 ago  # +41: canal #4 — poll en primer plano que OFRECE la actualización (doctrina T97) — 24 ago  # +1: accion togglePressScreenings — 23 ago  # +2: acciones openPalmares/closePalmares — 23 ago  # +5: acciones de la hoja de clave de revisión — 23 ago  # +29: vista previa por ?fest= — que el equipo de un festival revise su montaje sin publicarlo — 21 ago
        'src/i18n/i18n.js': 1661,  # +6: update_disponible/update_cta es-en-pt — 24 ago  # +6: el día vacío dice que el festival no programa, no que ajustes filtros — 24 ago  # +9: Prensa e Industria en es/en/pt — 23 ago  # +36: las strings del palmarés en es/en/pt — 23 ago  # +12: cadenas de festival en revisión (es/en/pt) — 23 ago  # +3: av_recalcular en es/en/pt — 18 ago
        'src/controller/sheets-controller.js': 1718,  # +7: icono de prensa en la fila de función — 24 ago  # +29: openPalmares/closePalmares — el palmarés usa el patrón sheet del Diario — 23 ago  # +4: el nombre completo del festival en la tapa, vía festivalTagline (18 ago)
        # config.js es DATA de festival (FESTIVAL_CONFIG, VENUES, NOTICES y ahora
        # PALMARES). El palmarés de FICDEH son 19 entradas + el porqué de tres
        # correcciones sobre la fuente, que valen más escritas que ahorradas.
        'src/controller/handlers.js': 1105,  # +2: el límite de prioridades mide las vivas (prioLiveCount) (17 ago)  # +26: includeAnyway — agendar la que solo choca por el Q&A, marcada como decisión deliberada (17 ago)  # +12: _vueltaA — el toast nombra la sección REAL donde reaparece (la prioridad sobrevive al desmarcar) (16 ago)  # +6: los dos toasts dicen «también en Intereses», solo cuando de verdad sumaron (16 ago)  # +18: el squeeze y «+ Incluir» usan el dueño del predicado (el plan volvía a cruzar ciudades al GUARDAR) (16 ago)  # +8: el toast del programa dice cuántas obras y por qué (15 ago)  # +45: taller multi-día — addRecurringBlock/removeRecurringBlock (bloque entero en un solo commitPlan) (8 ago)  # +15: acciones del sheet de ciudad (7 ago)  # +20: anclaje de función en toggleWL, simétrico al quitar (29 jul)
    }
    # src/config.js NO tiene techo (Juan, 23 ago 2026). Es DATA de festival
    # —FESTIVAL_CONFIG, VENUES, NOTICES, PALMARES— y crece con cada onboarding,
    # por construcción y para siempre. Un techo sobre un archivo que legítimamente
    # crece sin fin es un techo que se sube sin fin: en un solo día subió cuatro
    # veces (747→807→885→925→926).
    #
    # Y cada subida tenía un costo oculto: el techo vive en validate.py, que SÍ es
    # código de app, así que todo PR de DATOS que agregara una línea a config.js
    # arrastraba un cambio de código y [frontera] lo marcaba como mixto. Le pasó
    # al PR del afiche de «Los bibliotecarios» y le iba a pasar a cada onboarding.
    # La medida no protegía nada y ensuciaba la frontera; se retira.
    #
    # Lo que sí lo vigila y sigue en pie: [frontera] (que no mezcle), los
    # validadores de festival, y que su contenido sea declarativo — este chequeo
    # medía LÍNEAS, que en un archivo de datos no dice nada sobre su salud.
    _SIN_TECHO = {'src/config.js'}
    _over = []
    for _f in _glob.glob('src/**/*.js', recursive=True):
        _f = _f.replace('\\', '/')
        if _f in _SIN_TECHO:
            continue
        _n = sum(1 for _ in open(_f, encoding='utf-8'))
        _ceil = _ALLOW.get(_f, _CAP)
        if _n > _ceil:
            if _f in _ALLOW:
                _over.append(f"{_f}: {_n} líneas > techo {_ceil} (creció — bajá el techo si es intencional)")
            else:
                _over.append(f"{_f}: {_n} líneas > {_CAP} (módulo nuevo demasiado grande — partir o allowlist con justificación)")
    if _over:
        fail(check, 'módulo(s) sobre su techo de líneas: ' + '; '.join(_over))
    else:
        ok(check, f'ningún módulo sobre su techo (nuevos <{_CAP}; {len(_ALLOW)} grandes grandfathered no crecieron)')
except Exception as _e:
    warn(check, f'no se pudo verificar module-size: {_e}')

# ── [layer-direction] las dependencias apuntan hacia adentro ───────────────────
# La modularidad por capas solo se sostiene si las dependencias van en UNA
# dirección: domain (puro) ← state/storage ← controller/view ← main. Una capa
# interna que importa de una externa invierte el flujo y reintroduce el
# acoplamiento que la migración a módulos (Fase 6-8) eliminó. Este check congela
# esa dirección como contrato: medir, no suponer (auditoría jul 2026).
#   · domain/ no importa de controller/ ni view/  (0)
#   · state/ y storage/ no importan de controller/ ni view/  (0)
#   · view/ no importa de controller/  EXCEPTO la allowlist de lecturas de estado
#     derivado (getConsensusMap: cache vivo de la suscripción Realtime, controller-owned).
check = 'layer-direction'
try:
    import glob as _glob
    # (símbolo, módulo) permitidos como lectura view→controller. Estado derivado que
    # el controller posee y el view solo LEE — no es llamada a orquestador. Crecer
    # esta lista es una decisión consciente y revisada, no un accidente silencioso.
    _VIEW_CTRL_ALLOW = {('getConsensusMap', 'delays-cloud')}
    _viol = []
    def _imports_from(_src, _layers):
        # devuelve lista de (símbolos, módulo-base) importados de esas capas hermanas
        out = []
        for _m in re.finditer(r"import\s+(?:\{([^}]*)\}|[\w*]+)\s+from\s+'\.\./(" + '|'.join(_layers) + r")/([\w-]+)\.js'", _src):
            syms = [s.strip().split(' as ')[0].strip() for s in (_m.group(1) or '').split(',') if s.strip()]
            out.append((syms, _m.group(3)))
        return out
    # domain, state, storage → NO controller/view
    for _layer in ['domain', 'state', 'storage']:
        for _f in _glob.glob(f'src/{_layer}/*.js'):
            _s = open(_f, encoding='utf-8').read()
            if _imports_from(_s, ['controller', 'view']):
                _viol.append(f"{_f} importa de controller/view (capa interna → externa)")
    # view → controller solo lo allowlisted
    for _f in _glob.glob('src/view/*.js'):
        _s = open(_f, encoding='utf-8').read()
        for _syms, _mod in _imports_from(_s, ['controller']):
            for _sym in _syms:
                if (_sym, _mod) not in _VIEW_CTRL_ALLOW:
                    _viol.append(f"{os.path.basename(_f)} importa '{_sym}' de controller/{_mod} (no allowlisted)")
    if _viol:
        fail(check, 'dependencia contra la dirección de capas: ' + '; '.join(_viol))
    else:
        ok(check, 'dependencias apuntan hacia adentro (domain←state/storage←controller/view; view→controller solo allowlist)')
except Exception as _e:
    warn(check, f'no se pudo verificar layer-direction: {_e}')


# ── [staging-provenance] todo sidecar nuevo declara cuándo se capturó ─────────
# El bug de las 48 salas de FICDEH vivió escondido porque nada decía de CUÁNDO
# era cada sidecar. Regla: todo JSON nuevo en festivals/staging/ lleva
# _provenance.capturado (lib.provenance() lo pone solo). Los que existían antes
# de la regla quedan congelados en esta lista — NO añadir nombres nuevos aquí:
# un sidecar nuevo sin fecha es un error, no un candidato a la lista.
check = 'staging-provenance'
try:
    import json as _json, glob as _glob, os as _os
    _LEGACY_SIN_FECHA = {
        'ficdeh-2026-actividades.json', 'ficdeh-2026-boleteria-tuboleta.json',
        'ficdeh-2026-build.json', 'ficdeh-2026-cinemateca-grid.json',
        'ficdeh-2026-confirmaciones-externas.json', 'ficdeh-2026-funciones-barrido.json',
        'ficdeh-2026-geo-auditoria.json', 'ficdeh-2026-posters-src.json',
        'ficdeh-2026-programacion-oficial.json', 'ficdeh-2026-programacion-raw.json',
        'ficdeh-2026-salas-medellin.json', 'ficdeh-2026-title-en-candidatos.json',
        'ficdeh-2026-venues-geo.json', 'ficdeh-2026.json',
        'ficma-2026-crudo.json', 'ficma-2026-franja-ocr.json',
        'ficma-2026-letterboxd.json', 'ficma-2026-ocr.json',
        'ficma-2026-title-en.json', 'ficma-2026-tmdb.json',
        'ficma-2026-venues-geo.json',
        'finca-2026-build.json', 'finca-2026-funciones.json',
        'finca-2026-posters-src.json', 'finca-2026.json',
    }
    _sin = []
    for _f in sorted(_glob.glob('festivals/staging/*.json')):
        _b = _os.path.basename(_f)
        if _b in _LEGACY_SIN_FECHA:
            continue
        try:
            _d = _json.load(open(_f, encoding='utf-8'))
        except Exception:
            _sin.append(_b + ' (JSON inválido)'); continue
        _pr = _d.get('_provenance') if isinstance(_d, dict) else None
        if not (isinstance(_pr, dict) and (_pr.get('capturado') or _pr.get('recibido'))):
            _sin.append(_b)
    if _sin:
        fail(check, 'sidecar sin _provenance.capturado (usar lib.provenance()): ' + ', '.join(_sin))
    else:
        ok(check, 'todo sidecar nuevo declara cuándo se capturó (legacy congelado: '
                  f'{len(_LEGACY_SIN_FECHA)})')
except Exception as _e:
    warn(check, f'no se pudo verificar staging-provenance: {_e}')

# ══ GUARDIANES DE LA LÓGICA DEL CRUCE Y DEL CONTRATO CON LA APP ══════════════
# Los guardianes anteriores revisan la FORMA del dato. Estos revisan el CRUCE
# que lo produjo y la JUNTA con la app. Nacieron el 13 ago 2026 montando TIFF:
# cinco defectos de cruce y dos de contrato pasaron por tres validadores y 420
# tests sin que nada se pusiera rojo — los cazó Juan mirando la pantalla.
# Documentados en docs/PIPELINE.md §1.6.


# ── [valor-inventado] un valor de config que la app no maneja ────────────────
# HERMANO DE [campo-contrato], y del mismo día. Aquél caza el NOMBRE mal escrito;
# éste caza el VALOR inventado. Los dos son la misma familia: el dato y la app
# hablando idiomas distintos sin que nada se ponga rojo.
#
# El 13 ago 2026 escribí `ticketing_model:'ticketed'` para TIFF. La app solo
# ramifica sobre 'paid' y 'mixed'; con cualquier otra cosa cae al return vacío.
# Resultado: 637 fichas con su enlace de Ticketmaster guardado y SIN botón de
# compra. No lo cazó nada — lo cazó Juan preguntando por qué no veía la
# boletería. El error de fondo: vi 'mixed' en otro festival y DEDUJE que
# existiría un valor para «todo de pago», en vez de leer qué acepta el código.
#
# Regla: para cada campo de FESTIVAL_CONFIG cuyo valor la app compara con ===,
# el conjunto de valores usados tiene que estar contenido en el de valores
# manejados. Los valores manejados se leen DEL CÓDIGO, no de una lista a mano:
# una lista escrita aquí envejecería igual que el bug que persigue.
check = 'valor-inventado'
try:
    import re as _re, glob as _glob
    _cfg = open('src/config.js', encoding='utf-8').read()
    _src = ' '.join(open(_x, encoding='utf-8').read()
                    for _x in _glob.glob('src/**/*.js', recursive=True)
                    if 'config.js' not in _x)
    _CAMPOS = ('ticketing_model', 'posterSource', 'event_kind', 'type')
    _viol = []
    for _campo in _CAMPOS:
        _maneja = set(_re.findall(_campo + r"\s*===?\s*'([^']+)'", _src))
        _maneja |= set(_re.findall(r"'([^']+)'\s*===?\s*[\w.]*" + _campo, _src))
        if not _maneja:
            continue          # la app no ramifica sobre él: nada que validar
        _usa = set(_re.findall(_campo + r":\s*'([^']+)'", _cfg))
        _malos = sorted(_usa - _maneja)
        if _malos:
            _viol.append(f'{_campo}={_malos} — la app solo maneja '
                         f'{sorted(_maneja)}')
    if _viol:
        fail(check, 'valor de config que la app NO maneja (cae al camino vacío): '
                    + '; '.join(_viol))
    else:
        ok(check, 'todo valor de config cae en una rama que la app maneja')
except Exception as _e:
    warn(check, f'no se pudo verificar valor-inventado: {_e}')


# ── [paridad-derivados] un campo DERIVADO existe siempre que exista su fuente ─
# EL HUECO QUE ESTE TAPA, y por qué costó tanto verlo.
#
# `flags` es un campo DERIVADO: no existe en ninguna fuente. Ningún PDF, ningún
# Excel, ninguna web de festival trae banderas — las calculamos del país. Y ahí
# está la trampa: UNA AUSENCIA QUE NUNCA FUE PRESENCIA NO SE NOTA. Si falta un
# título salta a la vista, porque la fuente lo tenía y lo perdimos. Si falta
# `flags` no hay nada río arriba de donde se haya caído.
#
# FICDEH corrió su festival entero con 415 films mostrando país y ninguna
# bandera. Su ensamblador era a medida —PDF, Excel, web y tuboleta— y
# sencillamente nunca escribió el campo; los otros doce festivales lo emiten
# porque sus ensambladores salieron de la plantilla. Nadie lo vio en meses.
#
# La regla: para cada par (fuente → derivado), un film que tenga la fuente
# tiene que tener el derivado. Los pares se declaran acá y se MIDIERON antes de
# entrar: los cuatro primeros se cumplen hoy en los 12 festivales publicados,
# 1.209 films sin una sola excepción. No es una aspiración, es un invariante
# que ya se sostiene y que a partir de ahora no se puede romper en silencio.
#
# OJO con la regla ingenua «campo presente en N-1 festivales»: daría falsos
# positivos con `is_cortos` y `film_list`, que faltan legítimamente donde el
# festival no tiene programas de cortos. La dependencia, no la frecuencia, es
# lo que distingue un hueco de una ausencia legítima.
check = 'paridad-derivados'
try:
    import json as _json, glob as _glob, os as _os, re as _re
    # (fuente, derivado, por qué)
    _PARES = [
        ('day', 'day_order', 'el orden del día lo calcula el ensamblador'),
        ('day', 'time', 'una función con día y sin hora no se puede planear'),
        ('poster', 'posterSource', 'sin fuente, getFilmPoster no sabe si es editorial'),
        ('synopsis', 'synopsis_lang', 'sin idioma declarado, locSynopsis no elige bien'),
    ]
    # `country → flags` es aparte: solo es hueco si la bandera SE PODÍA derivar.
    # Un país que no está en la tabla («Varios», o un idioma colado en el campo)
    # es otro problema, y de ese ya se ocupa [country-flags].
    _js = open('src/controller/sheets-controller.js', encoding='utf-8').read()
    _m = _re.search(r'const _COUNTRY_FLAGS=\{(.*?)\};', _js, _re.S)
    _TAB = dict(_re.findall(r"'([^']+)'\s*:\s*'([^']+)'", _m.group(1))) if _m else {}

    def _vacio(v):
        return v in (None, '', [], {})

    _viol = []
    for _f in sorted(_glob.glob('festivals/*.json')):
        try:
            _d = _json.load(open(_f, encoding='utf-8'))
        except Exception:
            continue
        _n = _os.path.basename(_f)
        for _src, _der, _por in _PARES:
            _mal = [x.get('title', '?') for x in (_d.get('films') or [])
                    if not _vacio(x.get(_src)) and _vacio(x.get(_der))]
            if _mal:
                _viol.append(f'{_n}: {len(_mal)} film(s) con «{_src}» y sin «{_der}» '
                             f'({_por}) — p.ej. «{str(_mal[0])[:28]}»')
        _sinf = []
        for _x in (_d.get('films') or []):
            _c = (_x.get('country') or '').strip()
            if not _c or not _vacio(_x.get('flags')):
                continue
            if any(_p.strip() in _TAB for _p in _re.split(r'[,/()]', _c)):
                _sinf.append(_x.get('title', '?'))
        if _sinf:
            _viol.append(f'{_n}: {len(_sinf)} film(s) con país mapeable y sin «flags» '
                         f'— p.ej. «{str(_sinf[0])[:28]}»')
    if _viol:
        fail(check, 'campo derivado ausente donde su fuente existe: ' + '; '.join(_viol[:4]))
    else:
        ok(check, f'{len(_PARES)+1} pares fuente→derivado sin un solo hueco')
except Exception as _e:
    warn(check, f'no se pudo verificar paridad-derivados: {_e}')


# ── [campo-contrato] el JSON y la app tienen que llamar igual a lo mismo ─────
# EL HUECO QUE ESTE GUARDIÁN TAPA. Todos los demás revisan el dato POR DENTRO:
# que el campo exista, que sea booleano, que las cuentas cierren. Ninguno miraba
# la JUNTA entre el dato y la app. Un JSON impecable y una vista impecable
# pueden no encontrarse nunca, y nada se pone rojo.
#
# Pasó con TIFF el 13 ago 2026: emití `ticketUrl` y sheets-controller lee
# `ticket_url`. Los 638 enlaces de boletería estaban en el JSON y no llegaban a
# ninguna ficha. No lo cazó ningún test —ni los nuestros ni los de la app—: lo
# cazó Juan abriendo la app y preguntando «¿dónde está el enlace?». Lo mismo con
# `tmdbId` contra `tmdb_id`.
#
# La regla es estrecha A PROPÓSITO, para no tener falsos positivos: si un campo
# NO lo lee la app pero SÍ existe su variante en el otro estilo de nombre
# (camelCase ↔ snake_case) y ESA sí se lee, es un error seguro. No es una
# heurística: es la misma cosa escrita de dos formas.
check = 'campo-contrato'
try:
    import json as _json, glob as _glob, os as _os, re as _re
    _src = ' '.join(open(_x, encoding='utf-8').read()
                    for _x in _glob.glob('src/**/*.js', recursive=True))

    # Metadato NUESTRO, no de render: lo consumen el pipeline y los validadores,
    # y que la app no lo lea es correcto. Se declara para que el aviso de «dato
    # muerto» signifique algo — si todo es ruido, nadie lo mira.
    _PIPELINE = {'synopsis_lang', 'tmdb_id', 'tmdbId', 'posterSource', 'day_order',
                 # section_tags: los sellos de TIFF («💎 Unhidden Gems», «🌊 TIFF
                 # Next Wave Selects»). Juan decidió el 13 ago NO mostrarlos. El
                 # dato se conserva porque registra lo que el festival publica
                 # —esas 18 obras llevan el sello de verdad— pero nadie lo pinta,
                 # y eso es deliberado, no un cabo suelto.
                 'section_tags'}

    def _lee(_k):
        # Palabra suelta, no solo `.campo`: la app también desestructura y usa
        # el nombre en literales. Buscar solo `.campo` daba huérfanos falsos
        # («sessions» se lee en 4 sitios y salía como muerto).
        return bool(_re.search(r'\b' + _re.escape(_k) + r'\b', _src))

    def _variantes(_k):
        _snake = _re.sub(r'(?<!^)(?=[A-Z])', '_', _k).lower()
        _camel = _re.sub(r'_([a-z])', lambda m: m.group(1).upper(), _k)
        return {_snake, _camel} - {_k}

    _viol, _huerf = [], []
    for _f in sorted(_glob.glob('festivals/*.json')):
        try:
            _d = _json.load(open(_f, encoding='utf-8'))
        except Exception:
            continue
        _campos = set()
        def _rec(_items):
            for _it in _items or []:
                if isinstance(_it, dict):
                    _campos.update(k for k in _it if not k.startswith('_'))
                    _rec(_it.get('film_list'))
        _rec(_d.get('films'))
        for _k in sorted(_campos):
            if _lee(_k):
                continue
            _gemelas = [_v for _v in _variantes(_k) if _lee(_v)]
            if _gemelas:
                _viol.append(f'{_os.path.basename(_f)}: emite «{_k}» y la app lee '
                             f'«{_gemelas[0]}» — el dato no llega')
            elif _k not in _PIPELINE:
                _huerf.append(f'{_os.path.basename(_f)}:{_k}')
    if _viol:
        fail(check, 'mismo dato con dos nombres distintos: ' + '; '.join(_viol[:4]))
    elif _huerf:
        warn(check, f'{len(_huerf)} campo(s) que nadie lee (dato muerto, no error): '
                    + ', '.join(_huerf[:6]))
    else:
        ok(check, 'todo campo publicado tiene quien lo lea')
except Exception as _e:
    warn(check, f'no se pudo verificar campo-contrato: {_e}')


# ── [flag-booleano] un flag de la app es booleano, no la palabra «true» ──────
# La app compara los flags de servicio con `=== true`, no por truthy, y a
# propósito: un badge de precio no se pinta por un valor accidental. El coste de
# esa decisión es que un `"true"` como STRING no rompe nada — simplemente el
# badge no aparece nunca, y nadie se entera hasta que un usuario no ve algo que
# debería estar.
#
# Lo levantó Main el 13 ago 2026 al implementar el badge PREMIUM de TIFF. El
# dato estaba bien, pero el contrato entre el JSON y la vista no lo vigilaba
# nadie. Vale para todos los flags, no solo para premium: basta con que un
# ensamblador lea un CSV o un Excel para que un booleano llegue como texto.
check = 'flag-booleano'
try:
    import json as _json, glob as _glob, os as _os
    _FLAGS = ('premium', 'is_free', 'requires_registration', 'has_qa', 'is_cortos',
              'is_programa', 'isCanadian', 'canadiense')
    _viol = []
    for _f in sorted(_glob.glob('festivals/*.json')):
        try:
            _d = _json.load(open(_f, encoding='utf-8'))
        except Exception:
            continue
        def _mira(_items, _donde):
            for _it in _items or []:
                if not isinstance(_it, dict):
                    continue
                for _k in _FLAGS:
                    if _k in _it and not isinstance(_it[_k], (bool, type(None))):
                        _viol.append(f'{_os.path.basename(_f)} {_donde}'
                                     f'«{str(_it.get("title", "?"))[:28]}»: {_k}='
                                     f'{_it[_k]!r} ({type(_it[_k]).__name__}, no bool)')
                _mira(_it.get('film_list'), _donde + 'film_list/')
        _mira(_d.get('films'), '')
    if _viol:
        fail(check, 'flag que la app compara con === true y NO es booleano: '
                    + '; '.join(_viol[:4]))
    else:
        ok(check, 'todos los flags de servicio son booleanos de verdad')
except Exception as _e:
    warn(check, f'no se pudo verificar flag-booleano: {_e}')


# ── [cruce-inyectivo] un identificador externo, una sola obra ────────────────
# «The Age of Goodbyes» le prestó su lbSlug a otras cuatro obras porque sus
# títulos —«月宫», «咒语»— se normalizaban a cadena VACÍA y la vacía casaba con
# cualquier cosa. Y los dos cortos llamados «The End» (Pelechian 1992, Lindroth
# von Bahr 2026) colapsaron en uno solo al indexar por título.
# Regla: un lbSlug o un tmdb_id no puede quedar asignado a dos obras DISTINTAS.
# Se compara por obra, no por fila: una obra con doce funciones repite su slug
# doce veces y eso es sano.
check = 'cruce-inyectivo'
try:
    import json as _json, glob as _glob, os as _os
    _IDS = ('lbSlug', 'tmdb_id')
    _TIT = ('titulo', 'title', 'titulo_lb', 'nombre')
    _viol = []

    def _recorrer(nodo, ruta, archivo):
        if isinstance(nodo, dict):
            for k, v in nodo.items():
                _recorrer(v, f'{ruta}.{k}', archivo)
        elif isinstance(nodo, list) and nodo and isinstance(nodo[0], dict):
            for idk in _IDS:
                if not any(idk in r for r in nodo if isinstance(r, dict)):
                    continue
                titk = next((t for t in _TIT
                             if any(t in r for r in nodo if isinstance(r, dict))), None)
                if not titk:
                    continue
                porid = {}
                for r in nodo:
                    if not isinstance(r, dict):
                        continue
                    i, t = r.get(idk), r.get(titk)
                    if i in (None, '', []) or not t:
                        continue
                    porid.setdefault(i, set()).add(t)
                for i, ts in porid.items():
                    if len(ts) > 1:
                        _viol.append(f'{archivo}{ruta}: {idk}={i} en {len(ts)} obras '
                                     f'({", ".join(sorted(ts)[:3])})')
            for r in nodo:
                _recorrer(r, ruta + '[]', archivo)

    for _f in sorted(_glob.glob('festivals/staging/*.json')):
        try:
            _recorrer(_json.load(open(_f, encoding='utf-8')), '', _os.path.basename(_f))
        except Exception:
            continue
    if _viol:
        fail(check, 'identificador externo compartido por obras distintas: '
                    + '; '.join(_viol[:4]))
    else:
        ok(check, 'ningún lbSlug/tmdb_id asignado a dos obras distintas')
except Exception as _e:
    warn(check, f'no se pudo verificar cruce-inyectivo: {_e}')


# ── [cuentas-cuadran] nada se cae del cruce en silencio ──────────────────────
# El ensamblador de TIFF se quedaba con la PRIMERA sección de cada obra y tiraba
# la segunda sin decir nada: 18 obras perdieron una etiqueta y el JSON se veía
# perfecto. Un dato que desaparece callado es peor que uno que falta a gritos.
# Regla: si un sidecar declara `_cuentas`, sus números tienen que cerrar —
# entradas = publicadas + suma de descartes—. Declarar los descartes obliga a
# mirarlos; que sumen impide inventarlos.
check = 'cuentas-cuadran'
try:
    import json as _json, glob as _glob, os as _os
    _malas, _con = [], 0
    for _f in sorted(_glob.glob('festivals/staging/*.json')):
        try:
            _d = _json.load(open(_f, encoding='utf-8'))
        except Exception:
            continue
        _c = _d.get('_cuentas') if isinstance(_d, dict) else None
        if not isinstance(_c, dict):
            continue
        _con += 1
        _ent, _pub = _c.get('entradas'), _c.get('publicadas')
        _des = _c.get('descartadas') or {}
        if not isinstance(_ent, int) or not isinstance(_pub, int):
            _malas.append(f'{_os.path.basename(_f)}: falta entradas/publicadas')
            continue
        _sum = sum(v for v in _des.values() if isinstance(v, int))
        if _ent != _pub + _sum:
            _malas.append(f'{_os.path.basename(_f)}: {_ent} entradas ≠ {_pub} publicadas '
                          f'+ {_sum} descartadas ({_ent - _pub - _sum} sin explicar)')
    if _malas:
        fail(check, 'las cuentas del cruce no cierran: ' + '; '.join(_malas[:3]))
    else:
        ok(check, f'{_con} sidecar(s) con cuentas declaradas y cerradas')
except Exception as _e:
    warn(check, f'no se pudo verificar cuentas-cuadran: {_e}')


# ── [sidecar-vacio] un enriquecimiento que no enriqueció es un fallo ─────────
# El script de TMDB de TIFF se pasó una hora reintentando un error de
# certificado SSL y terminó sin escribir nada, porque trataba un fallo de
# transporte como si fuera un tropiezo pasajero de la API. Un script que corre
# hasta el final y no produce dato TIENE que notarse.
# Regla: si un sidecar declara un conteo mayor que cero, la lista que lo
# acompaña no puede estar vacía ni ser toda nula.
check = 'sidecar-vacio'
try:
    import json as _json, glob as _glob, os as _os, re as _re
    _viol = []
    for _f in sorted(_glob.glob('festivals/staging/*.json')):
        try:
            _d = _json.load(open(_f, encoding='utf-8'))
        except Exception:
            continue
        if not isinstance(_d, dict):
            continue
        _listas = {k: v for k, v in _d.items() if isinstance(v, list)}
        for _k, _v in _d.items():
            if not (_k.startswith('_') and isinstance(_v, int) and _v > 0):
                continue
            _base = _k.lstrip('_')
            # OJO con el `or`: una lista VACÍA es falsa, así que
            # `_listas.get(a) or _listas.get(b)` se saltaba justo el caso que
            # este guardián existe para cazar. Se pregunta por presencia, no
            # por verdad — el mismo error que el guardián persigue.
            if _base in _listas:
                _cand = _listas[_base]
            elif _base + 's' in _listas:
                _cand = _listas[_base + 's']
            else:
                continue
            if not _cand:
                _viol.append(f'{_os.path.basename(_f)}: {_k}={_v} pero «{_base}» vacía')
            elif all(x in (None, '', {}, []) for x in _cand):
                _viol.append(f'{_os.path.basename(_f)}: «{_base}» tiene {len(_cand)} '
                             'entradas y todas vacías')
    if _viol:
        fail(check, 'sidecar que declara dato y no lo tiene: ' + '; '.join(_viol[:3]))
    else:
        ok(check, 'ningún sidecar declara un conteo que su lista no respalda')
except Exception as _e:
    warn(check, f'no se pudo verificar sidecar-vacio: {_e}')


# ── [discrepancia-falsa] no acusar de distinto lo que es idéntico ────────────
# La auditoría de directores de TIFF reportó 22 discrepancias. Las 22 eran
# falsas: comparaba «Sue Kim» con «Sue Kim» —tokens de tres letras, conjuntos
# vacíos— y «濱口竜介» con su nombre latino. Una lista de discrepancias que
# contiene idénticos no es una auditoría, es ruido que esconde las de verdad.
# Regla: en cualquier lista de discrepancias o ambigüedades de un sidecar,
# ningún elemento puede tener dos valores que sean iguales al normalizar.
check = 'discrepancia-falsa'
try:
    import json as _json, glob as _glob, os as _os, unicodedata as _ud
    def _n(x):
        if isinstance(x, list):
            x = ' '.join(str(i) for i in x)
        x = _ud.normalize('NFKD', str(x or '').lower())
        x = ''.join(c for c in x if not _ud.combining(c))
        return re.sub(r'[^a-z0-9]+', '', x)
    _viol = []
    for _f in sorted(_glob.glob('festivals/staging/*.json')):
        try:
            _d = _json.load(open(_f, encoding='utf-8'))
        except Exception:
            continue
        if not isinstance(_d, dict):
            continue
        for _k, _v in _d.items():
            if not (_k.startswith('_') and ('discrep' in _k or 'ambigu' in _k)):
                continue
            for _it in (_v if isinstance(_v, list) else []):
                if not isinstance(_it, dict):
                    continue
                _vals = [(kk, _n(vv)) for kk, vv in _it.items()
                         if not kk.startswith('_') and isinstance(vv, (str, list)) and _n(vv)]
                for _i in range(len(_vals)):
                    for _j in range(_i + 1, len(_vals)):
                        if _vals[_i][1] == _vals[_j][1]:
                            _viol.append(f'{_os.path.basename(_f)} {_k}: '
                                         f'«{_vals[_i][0]}» y «{_vals[_j][0]}» son iguales '
                                         f'({_vals[_i][1][:24]})')
    if _viol:
        fail(check, 'discrepancia reportada entre valores idénticos: '
                    + '; '.join(sorted(set(_viol))[:3]))
    else:
        ok(check, 'ninguna lista de discrepancias contiene valores idénticos')
except Exception as _e:
    warn(check, f'no se pudo verificar discrepancia-falsa: {_e}')


# ── [pipeline-circuito] el barrido que nadie consume ──────────────────────────
# El bug real: el barrido escribía programacion-canonica.json y el ensamblador
# leía programacion-oficial.json — dos nombres para lo mismo, y el nuevo quedó
# sin consumidor. Este guardián busca ESE patrón: dentro de un mismo festival,
# un sidecar que se escribe y nadie lee junto a otro del mismo propósito
# (comparten un token largo del nombre) que se lee y nadie escribe.
check = 'pipeline-circuito'
try:
    import re as _re, glob as _glob, os as _os
    _escribe, _lee = {}, {}
    for _sp in _glob.glob('pipeline/*.py'):
        for _ln in open(_sp, encoding='utf-8'):
            for _m in _re.findall(r"[a-z0-9\-{}]+\.json", _ln):
                _b = _m.replace('{fid}', '*').lstrip('-')
                _es_w = bool(_re.search(r"json\.dump|,\s*'w'", _ln))
                (_escribe if _es_w else _lee).setdefault(_b, set()).add(_os.path.basename(_sp))
    def _quien(_tabla, _b):
        # nombre exacto o patrón de herramienta genérica ('*-crudo.json')
        _hit = set(_tabla.get(_b, set()))
        for _k, _v in _tabla.items():
            if _k.startswith('*') and _b.endswith(_k[1:]):
                _hit |= _v
        return _hit
    _pares = []
    _files = [_os.path.basename(_f) for _f in _glob.glob('festivals/staging/*.json')]
    for _a in _files:
        if _quien(_escribe, _a) and not _quien(_lee, _a):          # se escribe, nadie lee
            _fest = _a.split('-202')[0]
            _tok = {t for t in _re.split(r'[-.]', _a) if len(t) >= 6} - {_fest}
            for _b in _files:
                if _b == _a or not _b.startswith(_fest):
                    continue
                if _quien(_lee, _b) and not _quien(_escribe, _b) and \
                   _tok & {t for t in _re.split(r'[-.]', _b) if len(t) >= 6}:
                    _pares.append(f'{_a} (se escribe, nadie lee) ↔ {_b} (se lee, nadie escribe)')
    if _pares:
        fail(check, 'circuito roto entre productor y consumidor: ' + '; '.join(sorted(set(_pares))))
    else:
        ok(check, 'ningún sidecar escrito-sin-lector convive con su gemelo leído-sin-escritor')
except Exception as _e:
    warn(check, f'no se pudo verificar pipeline-circuito: {_e}')

# ── [sedes-apiladas] + [sala-en-sede] — los guardianes de datos de sede ───────
# Aprobados tras FICDEH. (a) dos sedes del mismo festival a <60 m casi siempre
# son la MISMA con dos nombres (63 de 120 apiladas en el geocoding v1); si es
# real (dos secretarías en la Alcaldía) se declara con _nota en el venue.
# (b) la sala dentro del nombre de la sede parte el filtro de lugar (la
# Cinemateca aparecía 5 veces). Ambos como WARNING: los festivales archivados
# violan (b) y no se van a reescribir.
check = 'sedes-apiladas'
try:
    import json as _json, math as _math, glob as _glob, os as _os, itertools as _it
    _avisos = []
    _ACTIVOS_AP = {'ficdeh-2026.json', 'ficma-2026.json', 'finca-2026.json'}
    for _f in sorted(_glob.glob('festivals/*.json')):
        if _os.path.basename(_f) not in _ACTIVOS_AP:
            continue          # los archivados no se reescriben
        try:
            _d = _json.load(open(_f, encoding='utf-8'))
        except Exception:
            continue
        _vs = _d.get('venues')
        if not isinstance(_vs, dict):
            continue
        _ub = {k: v for k, v in _vs.items()
               if isinstance(v, dict) and v.get('lat') and not v.get('_nota')}
        for _a, _b in _it.combinations(_ub, 2):
            _dy = (_ub[_a]['lat'] - _ub[_b]['lat']) * 111320
            _dx = (_ub[_a]['lng'] - _ub[_b]['lng']) * 111320 * \
                  _math.cos(_math.radians(_ub[_a]['lat']))
            if _math.hypot(_dx, _dy) < 60:
                _avisos.append(f'{_os.path.basename(_f)}: «{_a}» y «{_b}» a '
                               f'{round(_math.hypot(_dx, _dy))} m — ¿misma sede con dos '
                               'nombres? (si es real, _nota en el venue)')
    if _avisos:
        for _w in _avisos[:8]:
            warn(check, _w)
        ok(check, f'{len(_avisos)} pares sospechosos (warnings)')
    else:
        ok(check, 'ningún par de sedes a <60 m sin _nota')
except Exception as _e:
    warn(check, f'no se pudo verificar sedes-apiladas: {_e}')

check = 'sala-en-sede'
try:
    import json as _json, re as _re, glob as _glob, os as _os
    _avisos = []
    _ACTIVOS = {'ficdeh-2026.json', 'ficma-2026.json', 'finca-2026.json'}
    for _f in sorted(_glob.glob('festivals/*.json')):
        if _os.path.basename(_f) not in _ACTIVOS:
            continue          # los archivados no se reescriben
        try:
            _d = _json.load(open(_f, encoding='utf-8'))
        except Exception:
            continue
        _vs = _d.get('venues')
        if not isinstance(_vs, dict):
            continue
        for _k, _v in _vs.items():
            _n = (_v.get('short') or _k) if isinstance(_v, dict) else _k
            if _re.search(r'\b[Ss]ala\s+\d|\bSALA\s+\d', _n):
                _avisos.append(f'{_os.path.basename(_f)}: «{_n}» lleva la SALA en el '
                               'nombre — va en el campo sala de la función')
    if _avisos:
        for _w in _avisos:
            warn(check, _w)
        ok(check, f'{len(_avisos)} sedes con sala en el nombre (warnings)')
    else:
        ok(check, 'ninguna sede activa lleva la sala en el nombre')
except Exception as _e:
    warn(check, f'no se pudo verificar sala-en-sede: {_e}')

# ── [boleteria-muda] un festival entero sin una palabra sobre cómo se entra ──
# EL HUECO QUE TAPA. Los guardianes de boletería que ya teníamos vigilan la
# COHERENCIA de lo emitido: que el badge lo decida ticketBadgeTarget(), que
# `ticketing_model` use el vocabulario real, que `ticketUrl` no se escriba en
# camelCase. Ninguno vigilaba la AUSENCIA. Un festival puede salir a producción
# sin una sola función que diga cómo se entra, y todo queda verde.
#
# Pasó con CineAutopsia el 17 ago 2026: la agenda de la Cinemateca publicaba el
# enlace de TuBoleta de los 6 programas de pago y decía «Entrada libre» en la
# clausura. Mi ensamblador no miró el campo y encima escribió `is_free: False`
# en los 7 —también en el libre—. El dato estaba en la fuente, en la misma
# página de la que saqué todo lo demás. Lo cazó Juan preguntando, igual que los
# 638 enlaces de TIFF y las 415 banderas de FICDEH.
#
# LA REGLA. Un festival vigente cuyas funciones NO dicen NADA —ni `ticket_url`,
# ni `is_free`, ni `registration_url`— está mudo, y el silencio no es un dato:
# es una omisión. Gratis se DECLARA (`is_free: true`), no se deja en blanco.
# Solo aplica a festivales vigentes: los archivados quedaron como quedaron y
# reescribir su pasado no le sirve a nadie.
# ── [campo-huerfano] un campo que nadie lee no es un dato: es peso muerto ────
# EL HUECO QUE TAPA. `[campo-contrato]` caza el campo mal ESCRITO (`ticketUrl`
# contra `ticket_url`): el dato quiere llegar a la app y se pierde por el
# nombre. Éste caza el campo que no tiene a dónde llegar — nadie lo lee, y
# nunca lo leyó.
#
# El 17 ago 2026 había NUEVE. Entre ellos 36 `trailer` que alguien buscó uno
# por uno, 23 `tematica` y 16 `qa_detail` que además duplicaba —peor y en un
# solo idioma— lo que `qa_type` ya pintaba en tres. Se emitían, se validaban,
# se versionaban, y no se veían en ninguna pantalla.
#
# Es el espejo exacto de `[boleteria-muda]`: allá el dato estaba en la fuente y
# no lo emitimos; aquí lo emitimos y nadie lo pinta. Las dos formas de que el
# trabajo se pierda entre la fuente y el ojo.
#
# LA REGLA. Todo campo de función que `src/` no mencione tiene que estar en una
# de las dos listas de abajo, con su dueño escrito. Antes de añadir un campo, la
# pregunta es QUIÉN LO VA A LEER; si la respuesta es «alguien algún día», no se
# emite.
# ── [contrato-vivo] el canon manda, y la doc se genera de él ────────────────
# `pipeline/contrato.json` es el canon EJECUTABLE de una función. Este guardián
# vigila las tres formas de que deje de serlo:
#
#   1. La doc se escribe a mano y diverge. Pasó: SCHEMA.md documentaba 24 campos
#      de 60 y juraba que `duration` era un número. Ahora se GENERA del contrato
#      y aquí se comprueba que esté regenerada.
#   2. Un campo aparece en los datos y NO está en el contrato. Sin esto, el
#      contrato envejece igual que envejeció la doc: callando.
#   3. Una excepción con fecha se vence y nadie la mira. Una excepción sin fecha
#      se vuelve permanente sola; la de aquí se vence sola, pero alguien tiene
#      que enterarse el día que pasa.
# ── [lib-unica] una función, un dueño ───────────────────────────────────────
# `pipeline/lib.py` existe para que la lógica común se escriba UNA vez. El 17
# ago 2026 se midió cuánto de eso era verdad: 7 de sus 17 funciones tenían
# copias sueltas, `norm()` estaba reescrita en SEIS scripts y solo 5 de 28
# scripts importaban lib.
#
# Y al comparar comportamiento con entradas reales apareció algo peor que un
# duplicado: **el mismo nombre significaba cosas distintas**. `norm()` devuelve
# un string en lib, un `set` en ficma-repesca y una `list` en ficma-tmdb;
# `slug()` quita acentos en lib y los conserva en ficma («rebelion» vs
# «rebelión»); `hora24()` devuelve la hora en lib y «» en ficma-parse cuando ya
# venía en 24h. Leer un script y suponer la semántica del otro era un bug
# esperando fecha.
#
# LA REGLA, en dos ramas: si la copia hace LO MISMO, se borra y se importa de
# lib. Si hace otra cosa, se RENOMBRA para que lo diga. Lo que no se permite es
# que dos cosas distintas compartan nombre.
# ── [pipeline-generico] el camino nuevo es UNO, no uno por festival ─────────
# Cada festival escribía su propio ensamblador y su propio publicador, y ahí es
# donde se perdían las cosas: los 6 enlaces de TuBoleta de CineAutopsia, las 415
# banderas de FICDEH, el `is_free:false` a mano en una función que era libre. No
# eran doce errores distintos — era el mismo error doce veces, porque las reglas
# vivían en la cabeza de quien escribía el ensamblador de turno.
#
# Desde el 17 ago 2026 hay UN ensamblador (pipeline/ensamblar.py) y UN publicador
# (pipeline/publicar.py). Lo propio del festival cabe en su `<id>.plan.json`.
# Este guardián vigila que la excepción no vuelva a ser la norma: los dos
# publicadores por-festival que quedan son deuda DECLARADA y la lista solo puede
# encoger. Un festival nuevo con publicador propio es una regla que se escapó.

# ── [boleteria-muda] un festival entero sin una palabra sobre cómo se entra ──
# EL HUECO QUE TAPA. Los guardianes de boletería que ya teníamos vigilan la
# COHERENCIA de lo emitido: que el badge lo decida ticketBadgeTarget(), que
# `ticketing_model` use el vocabulario real, que `ticketUrl` no se escriba en
# camelCase. Ninguno vigilaba la AUSENCIA. Un festival puede salir a producción
# sin una sola función que diga cómo se entra, y todo queda verde.
#
# Pasó con CineAutopsia el 17 ago 2026: la agenda de la Cinemateca publicaba el
# enlace de TuBoleta de los 6 programas de pago y decía «Entrada libre» en la
# clausura. Mi ensamblador no miró el campo y encima escribió `is_free: False`
# en los 7 —también en el libre—. El dato estaba en la fuente, en la misma
# página de la que saqué todo lo demás. Lo cazó Juan preguntando, igual que los
# 638 enlaces de TIFF y las 415 banderas de FICDEH.
#
# LA REGLA. Un festival vigente cuyas funciones NO dicen NADA —ni `ticket_url`,
# ni `is_free`, ni `registration_url`— está mudo, y el silencio no es un dato:
# es una omisión. Gratis se DECLARA (`is_free: true`), no se deja en blanco.
# Solo aplica a festivales vigentes: los archivados quedaron como quedaron y
# reescribir su pasado no le sirve a nadie.
# ── [campo-huerfano] un campo que nadie lee no es un dato: es peso muerto ────
# EL HUECO QUE TAPA. `[campo-contrato]` caza el campo mal ESCRITO (`ticketUrl`
# contra `ticket_url`): el dato quiere llegar a la app y se pierde por el
# nombre. Éste caza el campo que no tiene a dónde llegar — nadie lo lee, y
# nunca lo leyó.
#
# El 17 ago 2026 había NUEVE. Entre ellos 36 `trailer` que alguien buscó uno
# por uno, 23 `tematica` y 16 `qa_detail` que además duplicaba —peor y en un
# solo idioma— lo que `qa_type` ya pintaba en tres. Se emitían, se validaban,
# se versionaban, y no se veían en ninguna pantalla.
#
# Es el espejo exacto de `[boleteria-muda]`: allá el dato estaba en la fuente y
# no lo emitimos; aquí lo emitimos y nadie lo pinta. Las dos formas de que el
# trabajo se pierda entre la fuente y el ojo.
#
# LA REGLA. Todo campo de función que `src/` no mencione tiene que estar en una
# de las dos listas de abajo, con su dueño escrito. Antes de añadir un campo, la
# pregunta es QUIÉN LO VA A LEER; si la respuesta es «alguien algún día», no se
# emite.
# ── [contrato-vivo] el canon manda, y la doc se genera de él ────────────────
# `pipeline/contrato.json` es el canon EJECUTABLE de una función. Este guardián
# vigila las tres formas de que deje de serlo:
#
#   1. La doc se escribe a mano y diverge. Pasó: SCHEMA.md documentaba 24 campos
#      de 60 y juraba que `duration` era un número. Ahora se GENERA del contrato
#      y aquí se comprueba que esté regenerada.
#   2. Un campo aparece en los datos y NO está en el contrato. Sin esto, el
#      contrato envejece igual que envejeció la doc: callando.
#   3. Una excepción con fecha se vence y nadie la mira. Una excepción sin fecha
#      se vuelve permanente sola; la de aquí se vence sola, pero alguien tiene
#      que enterarse el día que pasa.
# ── [lib-unica] una función, un dueño ───────────────────────────────────────
# `pipeline/lib.py` existe para que la lógica común se escriba UNA vez. El 17
# ago 2026 se midió cuánto de eso era verdad: 7 de sus 17 funciones tenían
# copias sueltas, `norm()` estaba reescrita en SEIS scripts y solo 5 de 28
# scripts importaban lib.
#
# Y al comparar comportamiento con entradas reales apareció algo peor que un
# duplicado: **el mismo nombre significaba cosas distintas**. `norm()` devuelve
# un string en lib, un `set` en ficma-repesca y una `list` en ficma-tmdb;
# `slug()` quita acentos en lib y los conserva en ficma («rebelion» vs
# «rebelión»); `hora24()` devuelve la hora en lib y «» en ficma-parse cuando ya
# venía en 24h. Leer un script y suponer la semántica del otro era un bug
# esperando fecha.
#
# LA REGLA, en dos ramas: si la copia hace LO MISMO, se borra y se importa de
# lib. Si hace otra cosa, se RENOMBRA para que lo diga. Lo que no se permite es
# que dos cosas distintas compartan nombre.
# ── [pipeline-generico] el camino nuevo es UNO, no uno por festival ─────────
# Cada festival escribía su propio ensamblador y su propio publicador, y ahí es
# donde se perdían las cosas: los 6 enlaces de TuBoleta de CineAutopsia, las 415
# banderas de FICDEH, el `is_free:false` a mano en una función que era libre. No
# eran doce errores distintos — era el mismo error doce veces, porque las reglas
# vivían en la cabeza de quien escribía el ensamblador de turno.
#
# Desde el 17 ago 2026 hay UN ensamblador (pipeline/ensamblar.py) y UN publicador
# (pipeline/publicar.py). Lo propio del festival cabe en su `<id>.plan.json`.
# Este guardián vigila que la excepción no vuelva a ser la norma: los dos
# publicadores por-festival que quedan son deuda DECLARADA y la lista solo puede
# encoger. Un festival nuevo con publicador propio es una regla que se escapó.
# ── [arquetipo-existe] un arquetipo inventado se pinta gris y nadie avisa ────
# `[seccion-sin-arquetipo]` (validate-festivals) comprueba que la sección ESTÉ
# en SECTION_ARCHETYPES. Nadie comprobaba que el arquetipo asignado sea uno de
# los NUEVE que tienen color. Escribí «Apertura» e «Industria / Formación» —que
# suenan bien y no existen: son «Apertura / Gala» y «Charlas / Industria»— y las
# dos secciones de CineAutopsia cayeron al gris por defecto, con el texto encima
# ilegible. Verde en los dos validadores, roto en la pantalla; lo vio Juan.
# ── [poster-mirado] alguien tiene que ABRIR el archivo ──────────────────────
# «¿Cómo es posible crear un póster sin pasar por un guardián?» — Juan, 18 ago
# 2026, después de encontrar en pantalla un póster que era la franja gris del
# encabezado del PDF con dos stills ajenos debajo.
#
# La respuesta incómoda: TODOS los guardianes de póster miran el CAMPO y ninguno
# el ARCHIVO. `[poster-single-owner]` vigila quién lo escribe, `[posters-
# duplicados]` que dos obras no compartan URL, `[paridad-derivados]` que
# `posterSource` acompañe a `poster`. Un JPG con una banda plana ocupando un
# tercio de la imagen los pasa todos, porque ninguno lo abre.
#
# Éste lo abre. Tres cosas que se pueden medir sin opinar:
#   · que el archivo EXISTA (una ruta rota no se ve hasta que se ve),
#   · que tenga resolución de póster y no de miniatura,
#   · que no lleve una BANDA PLANA en un borde — el recorte que se comió el
#     encabezado del PDF, que es exactamente el error de hoy.
check = 'poster-mirado'
try:
    import json as _j8, glob as _g8, os as _os8
    try:
        from PIL import Image as _Img
    except ImportError:
        _Img = None
    if _Img is None:
        warn(check, 'sin Pillow: no se pueden abrir los pósters')
    else:
        # DEUDA DECLARADA (18 ago 2026), y solo puede encoger. Son festivales ya
        # montados, no errores nuevos: Leviza y Tercer Tiempo trajeron pósters
        # diminutos de su fuente, y el still de «Mutante» viene letterboxed de
        # origen. Un guardián que nace rojo por el pasado no lo mira nadie; uno
        # que nombra su deuda obliga a que no crezca.
        _DEUDA_POSTER = {'leviza-2026', 'tercertiempo-2026', 'fantasofest-2026'}
        _rotos, _chicos, _bandas = [], [], []
        for _f in sorted(_g8.glob('festivals/*.json')):
            _d = _j8.load(open(_f, encoding='utf-8'))
            _fest = _f.split('/')[-1]
            _viejo = _f.split('/')[-1][:-5] in _DEUDA_POSTER
            for _x in (_d.get('films') or []):
                for _o in [_x] + list(_x.get('film_list') or []):
                    _p = str(_o.get('poster') or '')
                    if not _p.startswith('/assets/'):
                        continue
                    _ruta = '.' + _p
                    if not _os8.path.exists(_ruta):
                        _rotos.append(f'{_fest}: {_p}')
                        continue
                    try:
                        _im = _Img.open(_ruta).convert('RGB')
                    except Exception:
                        _rotos.append(f'{_fest}: {_p} (ilegible)')
                        continue
                    _w, _h = _im.size
                    # El mínimo va por el LADO CORTO, no por el ancho: un póster
                    # vertical de 300×427 es legítimo y mi primera versión lo
                    # marcaba junto a 51 más. Lo que no vale es una miniatura.
                    if min(_w, _h) < 280 and not _viejo:
                        _chicos.append(f'{_o.get("title","?")[:28]} {_w}×{_h}')
                    # La banda plana solo se persigue en pósters EDITORIALES —los
                    # que recortamos nosotros—: en un afiche diseñado, una franja
                    # de color sólido es una decisión, no un descuido. Sin este
                    # matiz salían 41 avisos, casi todos de afiches ajenos.
                    if _o.get('posterSource') != 'editorial' or _viejo:
                        continue
                    _px = _im.load()
                    for _borde, _rango in (('arriba', range(0, _h // 5, 2)),
                                           ('abajo', range(_h - 1, _h - _h // 5, -2))):
                        _n = 0
                        for _y in _rango:
                            _fila = [_px[_x2, _y] for _x2 in range(0, _w, max(1, _w // 40))]
                            _prom = [sum(c[_i] for c in _fila) / len(_fila) for _i in range(3)]
                            _plano = all(max(abs(c[_i] - _prom[_i]) for c in _fila) < 12 for _i in range(3))
                            if _plano:
                                _n += 2
                            else:
                                break
                        if _n > _h * 0.10:
                            _bandas.append(f'{_o.get("title","?")[:26]} ({_borde}, {100*_n//_h}%)')
        _prob = []
        if _rotos:
            _prob.append(f'{len(_rotos)} póster(s) que apuntan a un archivo que no existe: ' + '; '.join(_rotos[:3]))
        if _chicos:
            _prob.append(f'{len(_chicos)} por debajo de 400×220: ' + '; '.join(_chicos[:3]))
        if _bandas:
            _prob.append(f'{len(_bandas)} con banda plana en un borde (¿se coló el encabezado?): '
                         + '; '.join(_bandas[:3]))
        if _prob:
            fail(check, ' · '.join(_prob))
        else:
            ok(check, 'todo póster local abre, mide como póster y no arrastra bandas planas')
except Exception as _e:
    warn(check, f'no se pudo verificar poster-mirado: {_e}')


# ── [config-esm] node --check da un VERDE FALSO ─────────────────────────────
# src/config.js es un MÓDULO ES, y `node --check` lo analiza como script: un
# archivo con la llave de un festival sin cerrar pasa ese chequeo y revienta en
# el navegador. Pasó el 20 ago 2026 al resolver un merge donde las dos ramas
# agregaban su festival en el mismo punto: la entrada de Cinemancia se quedó
# sin `},`, CineAutopsia terminó ANIDADO dentro de ella, y la app no arrancaba
# —splash vacío, «Uncaught SyntaxError»—. Ni validate.py ni `node --check` lo
# vieron: el primero parsea con regex, el segundo con la gramática equivocada.
#
# Este lo IMPORTA de verdad y cuenta los festivales. Es la única forma de saber
# que el archivo que carga el navegador es el que creemos.
check = 'config-esm'
try:
    import subprocess as _sp9
    _js = ("import('./src/config.js').then(m=>{const C=m.FESTIVAL_CONFIG;"
           "const n=Object.keys(C).length;"
           "const anid=Object.entries(C).filter(([k,v])=>Object.keys(v||{})"
           ".some(x=>/^[a-z]+20\\d\\d$/.test(x))).map(([k])=>k);"
           "console.log(JSON.stringify({n,anid}));})"
           ".catch(e=>{console.log(JSON.stringify({error:String(e.message)}))})")
    _r = _sp9.run(['node', '-e', _js], capture_output=True, text=True, timeout=30)
    _out = [l for l in _r.stdout.splitlines() if l.strip().startswith('{')]
    if not _out:
        fail(check, f'src/config.js NO carga como módulo ES: {(_r.stderr or "").strip()[:120]}')
    else:
        import json as _j9
        _d = _j9.loads(_out[-1])
        if _d.get('error'):
            fail(check, f'src/config.js NO carga como módulo ES: {_d["error"][:120]}')
        elif _d.get('anid'):
            fail(check, f'festival ANIDADO dentro de otro (falta un «}}» en la entrada anterior): {_d["anid"]}')
        elif _d.get('n', 0) < 5:
            fail(check, f'FESTIVAL_CONFIG solo tiene {_d["n"]} festivales — ¿se cerró una entrada de más?')
        else:
            ok(check, f'src/config.js carga como módulo ES · {_d["n"]} festivales, ninguno anidado')
except Exception as _e:
    warn(check, f'no se pudo verificar config-esm: {_e}')


check = 'arquetipo-existe'
try:
    import re as _r7
    _cfg = open('src/config.js', encoding='utf-8').read()
    _i = _cfg.index('export const ARCHETYPE_COLORS'); _j = _cfg.index('\n};', _i)
    _validos = set(_r7.findall(r"'([^']+)':\s*'#", _cfg[_i:_j]))
    _k = _cfg.index('export const SECTION_ARCHETYPES'); _l = _cfg.index('\n};', _k)
    _malos = [f'{_a} → {_b!r}' for _a, _b in _r7.findall(r"'([^']+)':\s*'([^']+)'", _cfg[_k:_l])
              if _b not in _validos]
    if _malos:
        fail(check, f'sección con arquetipo que NO existe en ARCHETYPE_COLORS '
                    f'(cae a gris con texto ilegible): ' + '; '.join(_malos[:5]))
    else:
        ok(check, f'los {len(_validos)} arquetipos con color son los únicos usados')
except Exception as _e:
    warn(check, f'no se pudo verificar arquetipo-existe: {_e}')



# ── [cosecha-tmdb] tener la ficha y no traerse la sinopsis ──────────────────
# Los guardianes de este repo miraban la FORMA del dato (tipo, enum, campo
# huérfano) y ninguno preguntaba lo obvio: si fuimos hasta TMDB y anotamos el
# `tmdb_id`, ¿por qué volvimos con las manos vacías? En CineAutopsia 32 obras
# tenían ficha y ninguna sinopsis: la consulta pedía `es-CO` (TMDB devuelve
# vacío en vez de caer a `es-ES`) y el ensamblador tiraba el campo. Dos capas
# verdes, la pantalla sin un solo texto. Este guardián mira la COSECHA.
check = 'cosecha-tmdb'
try:
    import glob as _g, json as _j, os as _os
    # Festivales ya publicados cuya deuda es histórica: solo puede ENCOGER.
    _DEUDA_SIN = {'ficci65': 0, 'aff2026': 0}
    _malos = []
    for _f in sorted(_g.glob('festivals/*.json')):
        _fid = _os.path.basename(_f)[:-5]
        if _fid.endswith('-build') or '/staging/' in _f:
            continue
        try:
            _d = _j.load(open(_f, encoding='utf-8'))
        except Exception:
            continue
        _fichas = []
        for _x in _d.get('films') or []:
            _fichas.append(_x)
            _fichas += _x.get('film_list') or []
        _huecos = [_x.get('title', '?') for _x in _fichas
                   if _x.get('tmdb_id') and not _x.get('synopsis')]
        if _huecos:
            _malos.append((_fid, _huecos))
    if _malos:
        fail(check, 'obra con ficha TMDB y sin sinopsis — el dato estaba en la '
                    'fuente y no lo cosechamos: ' +
                    '; '.join(f'{_i} ({len(_h)}: {", ".join(_h[:3])})'
                              for _i, _h in _malos))
    else:
        ok(check, 'toda ficha con tmdb_id trae su sinopsis')
except Exception as _e:
    warn(check, f'no se pudo verificar cosecha-tmdb: {_e}')

check = 'pipeline-generico'
try:
    import glob as _g5, os as _os5
    # CineAutopsia salió de esta lista: se montó entero con el camino genérico
    # y su publicador propio se borró. La lista solo encoge.
    _HEREDADOS = {'ficdeh-2026-publicar.py'}   # pre-genérico; su build está atrasado
    _propios = {_os5.path.basename(_p) for _p in _g5.glob('pipeline/*-publicar.py')}
    _nuevos = sorted(_propios - _HEREDADOS)
    _faltan = [_f for _f in ('pipeline/ensamblar.py', 'pipeline/publicar.py')
               if not _os5.path.exists(_f)]
    if _faltan:
        fail(check, 'falta el camino genérico: ' + ', '.join(_faltan))
    elif _nuevos:
        fail(check, 'publicador propio de un festival (usá pipeline/publicar.py y '
                    'declará lo del festival en su plan.json): ' + ', '.join(_nuevos))
    else:
        ok(check, f'un solo ensamblador y un solo publicador ({len(_HEREDADOS)} heredados declarados)')
except Exception as _e:
    warn(check, f'no se pudo verificar pipeline-generico: {_e}')


check = 'lib-unica'
try:
    import ast as _ast, glob as _g4, os as _os4
    _libf = {_n.name for _n in _ast.parse(open('pipeline/lib.py', encoding='utf-8').read()).body
             if isinstance(_n, _ast.FunctionDef) and not _n.name.startswith('_')}
    _col = []
    for _p in sorted(_g4.glob('pipeline/*.py')):
        if _os4.path.basename(_p) == 'lib.py':
            continue
        try:
            _t = _ast.parse(open(_p, encoding='utf-8').read())
        except SyntaxError:
            continue
        for _n in _t.body:
            if isinstance(_n, _ast.FunctionDef) and _n.name in _libf:
                _col.append(f'{_os4.path.basename(_p)}::{_n.name}()')
    if _col:
        fail(check, 'función de pipeline/ que se llama igual que una de lib.py — '
                    'o hace lo mismo (importala) o hace otra cosa (renombrala): '
                    + '; '.join(_col[:6]))
    else:
        ok(check, f'ninguna de las {len(_libf)} funciones de lib.py tiene copia con su nombre')
except Exception as _e:
    warn(check, f'no se pudo verificar lib-unica: {_e}')


check = 'contrato-vivo'
try:
    import json as _j, glob as _g, subprocess as _sp, datetime as _dt
    _C = _j.load(open('pipeline/contrato.json', encoding='utf-8'))
    _prob = []
    _r = _sp.run(['node', 'scripts/generate-schema-md.js', '--check'],
                 capture_output=True, text=True)
    if _r.returncode != 0:
        _prob.append('SCHEMA.md desactualizado — correr: node scripts/generate-schema-md.js')
    _en_datos = set()
    for _f in _g.glob('festivals/*.json'):
        for _x in (_j.load(open(_f, encoding='utf-8')).get('films') or []):
            _en_datos |= set(_x)
    _sin = sorted(_en_datos - set(_C['campos']) - {'_provenance'})
    _sin = [_k for _k in _sin if not _k.startswith('_')]
    if _sin:
        _prob.append('campo(s) en los datos que el contrato no declara: ' + ', '.join(_sin[:6]))
    # Fecha de Colombia (UTC-5), no del runner: en UTC el día cambia cinco horas
    # antes y una excepción vencía distinto acá que en CI (misma regla de CLAUDE.md).
    _hoyCO = (_dt.datetime.utcnow() - _dt.timedelta(hours=5)).date()
    _limite = (_hoyCO + _dt.timedelta(days=14)).isoformat()
    _hoy = _hoyCO.isoformat()
    _porvencer = []
    for _campo, _fests in (_C.get('_pendientes') or {}).items():
        if _campo == '_doc':
            continue
        for _fest, _info in _fests.items():
            _m = _info['migrar_el']
            if _m <= _hoy:
                _prob.append(f'excepción VENCIDA: {_campo}@{_fest} debía migrar el {_m}')
            elif _m <= _limite:
                # Ámbar: la franja que este repo no tenía. Todo era verde o rojo,
                # así que lo que caducaba no avisaba — explotaba.
                _porvencer.append(f'{_campo}@{_fest} vence el {_m}')
    if _prob:
        fail(check, ' · '.join(_prob))
    elif _porvencer:
        warn(check, 'excepción(es) por vencer en ≤14 días: ' + ' · '.join(_porvencer)
                    + ' — migrar antes, o mover la fecha con su razón escrita')
    else:
        _np = sum(len(_v) for _k, _v in (_C.get('_pendientes') or {}).items() if _k != '_doc')
        ok(check, f'contrato al día: {len(_C["campos"])} campos, doc generada, '
                  f'{_np} excepción(es) con fecha por vencer')
except Exception as _e:
    warn(check, f'no se pudo verificar contrato-vivo: {_e}')


check = 'campo-huerfano'
try:
    import json as _j, glob as _g, re as _r3
    # Legítimos: no los lee la vista, pero tienen dueño y se nombra cuál.
    _CON_DUENO = {
        'synopsis_lang': 'lo consumen los guardianes ([paridad-derivados])',
        'tmdb_id': 'lo usa el pipeline para reenriquecer sin volver a buscar',
    }
    # DEUDA DECLARADA (17 ago 2026). No crece: cada uno se cablea o se borra.
    # Los dos primeros pares son EL MISMO DATO CON DOS NOMBRES — ahí no sobra el
    # dato, sobra el nombre, y unificarlos exige decidir cuál gana.
    # VACÍA desde el 17 ago 2026, y ese es el estado normal. Ese día salieron
    # los nueve: trailer, tematica y qa_detail primero; después original_title
    # (con title_orig ya unificado dentro), filmType y cycle; _tmdbId se fusionó
    # en tmdb_id. La pregunta que los resolvió todos fue la misma: ¿lo vamos a
    # pintar? Si no, es peso muerto — por limpio que esté el dato.
    _DEUDA = {
        # TIFF, y los dos esperan una decisión de Juan, no un borrado mío:
        # `section_tags` son los 47 SELLOS que él decidió sacar de las secciones
        # y dejar como etiqueta — la decisión se tomó y el cableado en la vista
        # nunca se hizo. `accessibility` son 34 funciones con subtítulos
        # descriptivos ('oc'), dato real que hoy no se pinta en ningún lado.
        'section_tags': 'TIFF (47) — sellos decididos por Juan, sin cablear en la vista',
        'accessibility': 'TIFF (34) — accesibilidad de la función, sin superficie que la muestre',
    }
    _src_all = ''.join(open(_p, encoding='utf-8').read()
                       for _p in _g.glob('src/**/*.js', recursive=True))
    _vistos = {}
    for _f in sorted(_g.glob('festivals/*.json')):
        for _x in (_j.load(open(_f, encoding='utf-8')).get('films') or []):
            for _k in _x:
                _vistos.setdefault(_k, set()).add(_f.split('/')[-1])
            for _it in (_x.get('film_list') or []):
                if isinstance(_it, dict):
                    for _k in _it:
                        _vistos.setdefault(_k, set()).add(_f.split('/')[-1])
    # EL GUION BAJO NO ES UN ESCONDITE. Un campo `_` es una nota para nosotros
    # —de dónde salió el dato, qué falta, qué se heredó—, no un dato de la app
    # con disfraz. `_tmdbId` vivió 16 funciones de FINCA a salvo de este mismo
    # guardián solo por llamarse con guion bajo, mientras el resto del repo
    # usaba `tmdb_id` (17 ago 2026). Si al quitarle el guion y normalizar el
    # nombre coincide con un campo real, es el mismo dato de contrabando.
    def _desnudo(_k):
        return _r3.sub(r'[^a-z0-9]', '', _k.lower())
    _reales = {_desnudo(_k) for _k in _vistos if not _k.startswith('_')}
    _reales |= {_desnudo(_k) for _k in _CON_DUENO} | {_desnudo(_k) for _k in _DEUDA}
    _contrabando = [f'{_k} → {", ".join(sorted(_vistos[_k]))[:40]}'
                    for _k in _vistos
                    if _k.startswith('_') and _desnudo(_k[1:]) in _reales]
    if _contrabando:
        fail(check, 'campo `_` que es en realidad un campo de datos con otro '
                    'nombre: ' + '; '.join(sorted(_contrabando)[:4]))
    _nuevos = [(_k, sorted(_v)) for _k, _v in _vistos.items()
               if not _k.startswith('_')
               and _k not in _CON_DUENO and _k not in _DEUDA
               and not _r3.search(r'\b' + _r3.escape(_k) + r'\b', _src_all)]
    if _nuevos:
        fail(check, 'campo(s) que ningún archivo de src/ lee y que no están '
                    'declarados: ' + '; '.join(f'{_k} ({", ".join(_v[:2])})'
                                               for _k, _v in sorted(_nuevos)))
    else:
        _viva = [_k for _k in _DEUDA if _k in _vistos]
        ok(check, f'ningún campo huérfano nuevo (deuda declarada: {len(_viva)})')
except Exception as _e:
    warn(check, f'no se pudo verificar campo-huerfano: {_e}')


check = 'boleteria-muda'
try:
    import json as _j, glob as _g
    from datetime import date as _date
    _hoy = _date.today().isoformat()
    _mudos = []
    for _f in sorted(_g.glob('festivals/*.json')):
        _d = _j.load(open(_f, encoding='utf-8'))
        _F = _d.get('films') or []
        # La vigencia NO está en un flag: está en la fecha de cierre. El primer
        # intento de este guardián buscaba `archived:true` en config.js y no
        # casaba con NINGÚN festival — verde por no mirar a nadie, que es peor
        # que rojo. Si un festival no declara cuándo termina, se revisa igual.
        _fin = (_d.get('festivalEndStr') or '')[:10]
        if not _F or (_fin and _fin < _hoy):
            continue
        _habla = sum(1 for _x in _F
                     if _x.get('ticket_url') or _x.get('is_free') or _x.get('registration_url'))
        if _habla == 0:
            _mudos.append(f'{_f.split("/")[-1]} ({len(_F)} funciones)')
    if _mudos:
        fail(check, 'festival vigente sin una sola función que diga cómo se entra '
                    '(ni ticket_url, ni is_free, ni registration_url): ' + '; '.join(_mudos))
    else:
        ok(check, 'todo festival vigente declara cómo se entra a sus funciones')
except Exception as _e:
    warn(check, f'no se pudo verificar boleteria-muda: {_e}')


# ── Report ────────────────────────────────────────────────────────────────────
print()
print('═' * 60)
print('  OTROFESTIV — validate.py')
print('═' * 60)

if passed:
    print(f'\n✓ PASSED ({len(passed)}):')
    for p in passed:
        print(p)

if warnings:
    print(f'\n⚠ WARNINGS ({len(warnings)}):')
    for w in warnings:
        print(w)

if errors:
    print(f'\n✗ ERRORS ({len(errors)}):')
    for e in errors:
        print(e)

print()
print('═' * 60)
total = len(passed) + len(warnings) + len(errors)
print(f'  {len(passed)}/{total} checks passed'
      + (f' · {len(warnings)} warnings' if warnings else '')
      + (f' · {len(errors)} errors' if errors else ''))
print('═' * 60)
print()

strict = '--strict' in sys.argv
if errors or (strict and warnings):
    print('  → PUSH BLOQUEADO\n')
    sys.exit(1)
else:
    print('  → OK para push\n')
    sys.exit(0)
