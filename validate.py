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
sched_start = content.find('const _SCHED_PURE_FNS = [')
if sched_start == -1:
    fail(check, '_SCHED_PURE_FNS no encontrado en index.html')
else:
    sched_end = content.find('];', sched_start)
    sched_block = content[sched_start:sched_end]
    fn_names = re.findall(r"'(\w+)'", sched_block)
    missing_fns = [f for f in fn_names if f'function {f}(' not in content]
    if missing_fns:
        for f in missing_fns:
            fail(check, f"'{f}' en _SCHED_PURE_FNS pero no definida en main thread")
    else:
        ok(check, f'todas las {len(fn_names)} funciones de _SCHED_PURE_FNS existen en main')

# ── CHECK 3: Worker-local no duplica _SCHED_PURE_FNS ─────────────────────────
# Si una función está en ambos lados, el worker-local gana y el main thread
# queda ignorado — exactamente el bug que Sprint 3 resolvió.
check = 'worker-overlap'
mk_pos = content.find('function _mkCalcWorker()')
if mk_pos == -1:
    fail(check, '_mkCalcWorker() no encontrado en index.html')
else:
    mk_end_search = content.find('\n// Worker activo', mk_pos)
    if mk_end_search == -1:
        mk_end_search = mk_pos + 4000
    mk_body = content[mk_pos:mk_end_search]
    worker_local_fns = set(re.findall(r'function (\w+)\s*\(', mk_body))
    if sched_start != -1:
        overlap = worker_local_fns & set(fn_names)
        if overlap:
            for f in overlap:
                fail(check, f"'{f}' definida como worker-local Y en _SCHED_PURE_FNS — ambigüedad")
        else:
            ok(check, f'sin overlap entre worker-local ({len(worker_local_fns)} fns) y _SCHED_PURE_FNS')

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
fc_start = content.find('const FESTIVAL_CONFIG={')
if fc_start == -1:
    fail(check, 'FESTIVAL_CONFIG no encontrado en index.html')
else:
    fc_end = content.find('};', fc_start) + 2
    fc_block = content[fc_start:fc_end]
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
    if div not in content:
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
    # Extract _I18N block
    i18n_start = content.find('const _I18N = {')
    depth = 0
    end = i18n_start
    for i, ch in enumerate(content[i18n_start:]):
        if ch == '{': depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                end = i18n_start + i + 1
                break
    i18n_block = content[i18n_start:end]

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

    # All t('key') calls in the script
    script_part = content[content.find('<script>'):content.rfind('</script>')]
    all_t_calls = set(re.findall(r"t\('([a-z][a-z0-9_]+)'\)", script_part))
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

# ── CHECK: i18n-hardcoded ─────────────────────────────────────────────────────
# Detecta strings de UI conocidos hardcodeados en JS sin pasar por t().
# La búsqueda excluye la zona de los diccionarios i18n (antes de "function t(key")
# para evitar falsos positivos — esos strings aparecen legítimamente en los dicts.
# Cada string encontrado en auditoría Chrome debe añadirse aquí.
check = 'i18n-hardcoded'
try:
    script_full = content[content.find('<script>'):content.rfind('</script>')]
    # Boundary: todo DESPUÉS de la definición de t() es código de app
    t_fn_idx = script_full.find('function t(key')
    code_only = script_full[t_fn_idx:] if t_fn_idx > 0 else script_full

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

    if hardcoded_found:
        for s in hardcoded_found:
            fail(check, f"'{s}' hardcodeado en JS — debe usar t()")
    else:
        ok(check, f'{len(UI_STRINGS_MUST_USE_T)} strings de UI verificados — ninguno hardcodeado')

    # ── Check dinámico: strings JS con español fuera de t() ──────────────────
    # Produce warnings (no falla el deploy) — puede tener falsos positivos
    # pero detecta nuevos strings hardcodeados antes de llegar a producción
    SAFE_LINE_MARKERS = [
        'includes(', 'PROGRAMA_CHIPS', 'FESTIVAL_DATES', 'DAY_SHORT',
        'DAYS_ES', 'DAYS_EN', 'var(--', 'replace(', 'toLowerCase(',
        'normTitle', '.json', 'regex', 'RegExp', 'https://',
        'Adolfo', 'SÁB 16', 'MIÉ 15', # venue/date literals en FESTIVAL_DATES Leviza
        'canvas vacío', # error interno, no UI visible
        'PROYECCIÓN SORPRESA', 'Valle de Aburrá', 'Plaza Proclamación', # venue/nombres Leviza
        'Ciencia Ficción', 'Animación', # géneros PROGRAMA_CHIPS FICCI
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
    if '<button' in line or 'onclick=' in line and 'event.stopPropagation' in line:
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
    _html = open('index.html').read()
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
