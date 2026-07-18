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
    'id="hdr-ag"',
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
    else:
        ok(check, f'todas las {len(fn_names)} funciones de _SCHED_PURE_FNS existen (main + domain)')

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
    for fest_id in fest_ids:
        entry_start = fc_block.find(f"'{fest_id}':")
        entry       = fc_block[entry_start:entry_start+400]
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
#   1. El STATE BRIDGE expone exactamente los 19 keys del roster.
#   2. NINGÚN roster key se redeclara (let/const/var) en main.js fuera del worker
#      (una redeclaración shadowearía el bridge → el write NO llegaría a state).
#   3. state.js no contiene mirror (_MIRROR_TARGETS/_MIRROR_READERS).
check = 'state-mirror'
try:
    import re as _re
    _roster = [
        '_activeFestId', 'FILMS', 'FESTIVAL_DATES', 'FESTIVAL_END',
        'FESTIVAL_STORAGE_KEY', 'PRIO_LIMIT', 'TZ_OFFSET', 'FESTIVAL_TRANSPORT',
        'watchlist', 'watched', 'prioritized', 'filmRatings', 'filmDelays',
        'filmDelaysHistory', 'savedAgenda', 'availability', 'lastRemovedSlots',
        '_lang', '_simTime',
    ]
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
        'programaViewMode', 'cartelaMode', 'interesesViewMode', 'miPlanViewMode',
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
                        ('hdr-ag', r'#hdr-ag\{[^}]*\}'),
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
    _INFO = ['.pel-sheet-flags-dur{', '.pel-sheet-metaline{']
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
        _is_btn = ('-btn' in _sel or '-cta' in _sel or 'button' in _sel) and '::' not in _sel
        if not _is_btn:
            continue
        if 'background:var(--amber);color:var(--black)' in _body.replace('\n', '').replace(' ', '') and '.splash-enter-btn' not in _sel:
            _errs.append(f'{_sel[:60]}: primario amber fuera de la regla dueña')
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
    _ACTIVE = ['tercertiempo-2026', 'fantasofest-2026']   # activos/próximos hoy
    # (festival_file, título) cuyo dato de duración la organización NO publicó.
    # Al recibir el minutaje real: llenar el JSON y BORRAR la línea de aquí.
    _PENDING = {
        ('fantasofest-2026', 'Muestra de Cortometrajes'),  # PDF prensa sin runtimes; pedido a FantasoLab
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
        'src/view/agenda.js': 1622,
        'src/main.js': 1551,
        'src/i18n/i18n.js': 1405,  # +5: aria_dia_sig ×3 locales (a11y iconos, 18 jul)
        'src/controller/sheets-controller.js': 1350,  # +25: hook _applyAmbient + prewarm pointerdown (color ambiental, 18 jul 2026)
        'src/controller/handlers.js': 915,
    }
    _over = []
    for _f in _glob.glob('src/**/*.js', recursive=True):
        _f = _f.replace('\\', '/')
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
