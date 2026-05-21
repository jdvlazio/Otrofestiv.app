# Plan técnico — Fase 6a (View Purity Tier 1)

## Restricciones de partida

### R1. Single-file en producción
Las 8 funciones siguen viviendo en index.html. Split físico a `view/` queda
para Fase 8. La migración solo cambia signature + read source, no estructura
de archivos.

### R2. Behavior preservation absoluta
HTML output **byte-identical** pre/post migración. Cero diferencias en:
- Tags, attributes, classes, style
- Text content (incluso whitespace dentro de template literals)
- Orden de elementos
- IDs y data-attributes

Verificación: diff de DOM dump antes/después en escenario controlado.

### R3. Cero cambios en lecturas de Model
Las 8 Views llaman funciones Model (`screensConflict`, `screeningPassed`,
`_resolveVenue`, etc.). Estas siguen siendo refs libres — no entran en el
destructure de state. Solo state-roster globals entran.

### R4. Caller flow intacto
Las 8 Views son **sub-renders** llamadas desde orchestrators (`renderAgenda`,
`shareAsImage`). Los orchestrators siguen leyendo globals directo en 6a — se
limitan a pasar `state` como primer arg a las sub-renders.

### R5. Cero tests nuevos (low ROI — Playwright cubre)
La cobertura existente (Playwright T01-T10) cubre los renders en flujos reales.
Añadir snapshot tests para las 8 Views tiene mantenimiento alto y benefit bajo
en 6a — el cambio es sintáctico mecánico. Tests vienen en 6b/6c donde la
pureza se vuelve materialmente diferente.

### R6. Validate check warning-only
`[view-purity]` se implementa nivel WARNING en 6a. Razón: en 6a las 8 Views
deberían quedar clean; el resto de funciones (Tier 2/3/4) aún tienen DOM
mutations legítimas que no podemos prohibir todavía. El check se promote a
FAIL en Fase 7 cuando el último Controller esté migrado.

### R7. Sub-render order matters
Algunas Views llaman otras Views. Orden de migración debe respetar la cadena
de calls — la sub-View migra ANTES de la que la llama. Cadena observada:
- `renderContextualHeader` standalone (no llama otras del Tier 1)
- `renderNextStrip(schedule)` standalone
- `renderUnconfirmed(schedule)` standalone
- `renderGapOptions` standalone
- `renderMiPlanCalendar` standalone
- `_renderSavedAgendaHTML` standalone — solo llamado por `shareAsImage`
- `makeProgramPoster`, `makeEventPoster` — llamados desde `getFilmPoster`,
  `getCortoItemPoster`, otros poster builders

Conclusión: **cero dependencias entre las 8**. Pueden migrarse en cualquier
orden. Decisión: migrar en orden creciente de complejidad (lines).

## 1. Patrón de migración por función

### 1.1 Patrón canónico

```js
// ANTES
function renderX(arg1, arg2) {
  // lee globals: A, B, C
  const result = A.find(...);
  for (const item of B) { ... }
  return `<div>${C[arg1]}</div>`;
}

// DESPUÉS
function renderX(state, arg1, arg2) {
  const { A, B, C } = state.snapshot();
  const result = A.find(...);
  for (const item of B) { ... }
  return `<div>${C[arg1]}</div>`;
}
```

### 1.2 Pattern para callers (renderAgenda y similar)

```js
// renderAgenda — caller orchestrator (sigue impuro en 6a, no se toca su shape)
function renderAgenda() {
  // ... reads existentes ...
  const ctxHtml = renderContextualHeader(state);     // ← + state arg
  const stripHtml = renderNextStrip(state, schedule); // ← + state arg
  // ...
}
```

Los orchestrators **NO migran** en 6a. Solo añaden `state` al call de las
8 funciones que migran. Esto es ~10-15 sitios tocados (call sites de las 8).

### 1.3 Edge case — destructure dentro de un branch

Si la función entera no lee algunos globals (e.g., solo los lee en un branch
poco frecuente), tentación: destructurar dentro del branch. **Anti-patrón**:

```js
// MAL — destructure adentro del if
function renderX(state) {
  if (rare_condition) {
    const { B } = state.snapshot();  // ← duplica costo de snapshot
    return ...;
  }
  return ...;
}

// BIEN — destructure al tope, lazy si justified (raro)
function renderX(state) {
  const { B } = state.snapshot();
  if (rare_condition) return ...uses B...;
  return ...;
}
```

Razón: `state.snapshot()` itera todos los 19 keys del roster. Llamarlo varias
veces es marginalmente costoso. UN snapshot al tope es claro y barato.

### 1.4 Edge case — solo se lee 1 global, pequeño

Si la función solo lee 1 global, ¿destructure o `state.get(k)` inline?

```js
// Opción A: destructure (consistente con resto)
function makeProgramPoster(state, title, duration, section) {
  const { FILMS } = state.snapshot();
  const filmSec = section || FILMS.find(f=>f.title===title)?.section || '';
  ...
}

// Opción B: state.get(k) inline (más liviano)
function makeProgramPoster(state, title, duration, section) {
  const filmSec = section || state.get('FILMS').find(f=>f.title===title)?.section || '';
  ...
}
```

**Recomendación: A (destructure)** uniforme. Razones:
- Consistencia con el resto de Views
- Más fácil de extender (añadir global = añadir al destructure)
- Sintaxis más limpia que `state.get('FILMS').find(...)`

## 2. Lista de migraciones por función

(orden de ejecución — creciente en complejidad)

### 2.1 makeEventPoster (25 líneas, reads: _activeFestId, _lang)

```js
function makeEventPoster(state, title, duration, eventKind) {
  const { _activeFestId, _lang } = state.snapshot();
  const festCfg = (FESTIVAL_CONFIG && FESTIVAL_CONFIG[_activeFestId]) || ...;
  const _kindMap = _lang === 'en' ? _kindMapEN : _kindMapES;
  // ... resto sin cambios ...
}
```

Callers: buscar `makeEventPoster(` y añadir `state,` al inicio.

### 2.2 makeProgramPoster (48 líneas, reads: FILMS)

```js
function makeProgramPoster(state, title, duration, section) {
  const { FILMS } = state.snapshot();
  const filmSec = section || (FILMS.find(f=>f.title===title)?.section) || '';
  // ... resto ...
}
```

Nota: el original usa `typeof FILMS!=='undefined'` guard — innecesario post-migración
porque state siempre tiene FILMS (puede ser `[]` pero no undefined). Mantener el
guard si afecta byte-identity del output; remover si solo es dead branch.

### 2.3 renderGapOptions (40 líneas, reads: savedAgenda, FILMS, watched, FESTIVAL_DATES)

```js
function renderGapOptions(state, gapStartMin, gapEndMin, todayKey, removedTitle) {
  const { savedAgenda, FILMS, watched, FESTIVAL_DATES } = state.snapshot();
  // ... resto ...
}
```

### 2.4 renderUnconfirmed (52 líneas, reads: watched, FESTIVAL_DATES)

```js
function renderUnconfirmed(state, schedule) {
  const { watched, FESTIVAL_DATES } = state.snapshot();
  // ... resto ...
}
```

### 2.5 renderNextStrip (86 líneas, reads: watched, filmDelays, FESTIVAL_DATES)

```js
function renderNextStrip(state, schedule) {
  const { watched, filmDelays, FESTIVAL_DATES } = state.snapshot();
  // ... resto ...
}
```

### 2.6 _renderSavedAgendaHTML (144 líneas, reads: savedAgenda, FILMS, watched, _activeFestId, FESTIVAL_DATES)

```js
function _renderSavedAgendaHTML(state) {
  const { savedAgenda, FILMS, watched, _activeFestId, FESTIVAL_DATES } = state.snapshot();
  // ... resto ...
}
```

### 2.7 renderMiPlanCalendar (220 líneas, reads: savedAgenda, FILMS, prioritized, FESTIVAL_DATES)

```js
function renderMiPlanCalendar(state) {
  const { savedAgenda, FILMS, prioritized, FESTIVAL_DATES } = state.snapshot();
  // ... resto ...
}
```

### 2.8 renderContextualHeader (244 líneas, reads: 8 globals)

```js
function renderContextualHeader(state) {
  const { savedAgenda, FILMS, watched, prioritized, filmRatings,
          filmDelays, _activeFestId, _lang } = state.snapshot();
  // ... resto ...
}
```

## 3. Validate check `[view-purity]`

### 3.1 Detector

```python
check = 'view-purity'
TIER1_FNS = ['makeProgramPoster', 'makeEventPoster', 'renderNextStrip',
             'renderUnconfirmed', 'renderGapOptions', '_renderSavedAgendaHTML',
             'renderContextualHeader', 'renderMiPlanCalendar']

ROSTER = ['_activeFestId', 'FILMS', 'FESTIVAL_DATES', 'FESTIVAL_END',
          'FESTIVAL_STORAGE_KEY', 'PRIO_LIMIT', 'TZ_OFFSET', 'FESTIVAL_TRANSPORT',
          'watchlist', 'watched', 'prioritized', 'filmRatings', 'filmDelays',
          'filmDelaysHistory', 'savedAgenda', 'availability', 'lastRemovedSlots',
          '_lang', '_simTime']

# Para cada función en TIER1_FNS:
#   1. Extraer el body
#   2. Detectar si hay destructure de state.snapshot() en las primeras N líneas
#   3. Para cada global del ROSTER referenciado en el body:
#      - WARN si NO está en el destructure (lectura directa del global ≠ canalizada)
#   4. Detectar side effects:
#      - WARN si hay `.innerHTML = `, `.outerHTML = ` (fuera de strings template literal)
#      - WARN si hay `classList.(add|remove|toggle|replace)` (fuera de strings)
#      - WARN si hay `appendChild`, `insertAdjacentHTML`
#      - WARN si hay `setTimeout`, `requestAnimationFrame` (fuera de strings)
```

### 3.2 Pseudo-código del check

```python
def check_view_purity():
    # Find function ranges
    fn_ranges = {}
    for fn in TIER1_FNS:
        ln = find_function(fn)
        end = find_function_end(ln)
        fn_ranges[fn] = (ln, end)

    for fn, (ln, end) in fn_ranges.items():
        body = lines[ln:end]
        # Quita strings template literal y comments para análisis sintáctico real
        body_stripped = strip_string_literals_and_comments(body)

        # Detect destructure at top
        destructure_match = re.search(r'const\s*\{([^}]+)\}\s*=\s*state\.snapshot\(\)', body_stripped[:5])
        destructured_keys = set(parse_destructure_keys(destructure_match)) if destructure_match else set()

        # Detect roster reads NOT in destructure
        for global_name in ROSTER:
            if uses_global_in_body(global_name, body_stripped) and global_name not in destructured_keys:
                warn(check, f'{fn}: read directo de "{global_name}" — usar state.snapshot() destructure')

        # Detect side effects
        if re.search(r'\.innerHTML\s*=', body_stripped):
            warn(check, f'{fn}: innerHTML= — Tier 1 debe ser pura')
        # ... otros patterns ...
```

### 3.3 Whitelist de "side effects" aparentes pero legítimos

| Patrón | Razón |
|---|---|
| `${document.getElementById(...).style...}` dentro de template literal | Es string content de un onclick handler, no JS real |
| `setTimeout(...)` dentro de string template literal | Idem |
| Referencias a roster globals dentro de template literal | Idem |

El strip de strings/comments antes del regex evita falsos positivos.

## 4. Test strategy — cero tests nuevos en 6a

### 4.1 Cobertura existente

- **Playwright T01-T10**: cubren los flujos visuales:
  - T01 Mi Plan vacío
  - T02 Mi Plan con schedule
  - T03 Programa list view
  - T04 Programa grid view
  - T05 Pelicula sheet
  - T06 Corto sheet
  - T07 Lang switch
  - T08 Festival switch
  - T09 Availability sheet
  - T10 Share export
- **131 unit tests** (Model + state container) — no cambian
- **23 validate checks** + 1 nuevo `[view-purity]` = 24

### 4.2 Manual QA browser

Post-migración, abrir local server y verificar visualmente:
- Mi Plan tab con savedAgenda (probar renderAgenda → llama renderContextualHeader, renderNextStrip, renderUnconfirmed, renderMiPlanCalendar, renderGapOptions)
- shareAsImage (probar _renderSavedAgendaHTML)
- Cards de program/event (probar makeProgramPoster, makeEventPoster)

### 4.3 Diff de HTML output

Para alta confianza en R2 (byte-identical):

```js
// Pre-migración: dump innerHTML de cada View root
const before = {
  ctx: document.querySelector('[data-ctx]')?.innerHTML,
  strip: document.querySelector('[data-strip]')?.innerHTML,
  unconfirmed: document.querySelector('[data-unconfirmed]')?.innerHTML,
  // ...
};
// guardar JSON

// Post-migración: dump idéntico, comparar JSON.stringify
```

Esto se hace en QA browser paso. No automated.

## 5. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Olvidé un global en el destructure → ReferenceError o lectura del global directo | Validate check `[view-purity]` lo detecta (WARN). Lee build sin error pero alerta |
| Función migrada pero un caller no se actualizó → `state` es undefined → crash | Buscar todos los call sites antes de mergear. Grep por nombre función + verificar primer arg es state |
| `state.snapshot()` costoso si se llama N veces en hot path | El snapshot solo se llama 1 vez al tope (por R8). N ~10 keys, costo despreciable |
| HTML output difiere por orden de propiedades en destructure | Destructure order no afecta el HTML — solo afecta el binding. R2 robusto |
| Template literals con `${...}` que referencian globals al string-content | Esos son contenido de string, no eval. No afectan el HTML real |
| Función llama un Model function que internamente lee globals (no del roster) | OK — Model functions ya tienen contratos puros desde Fases 1-4 |
| QA browser detecta visual regression sutil (color, spacing) | Diff de DOM dump localiza el sitio. Si pasa al merge, Playwright T01-T10 cubre el resto |

## 6. Tamaño estimado

| Concepto | Líneas |
|---|---|
| 8 functions migradas (signature + destructure top) | ~50 líneas tocadas (en 8 funciones de 860 líneas totales — la mayoría del body queda intacto) |
| Callers actualizados (renderAgenda, shareAsImage, getFilmPoster, etc) | ~15 sitios x 1 línea = 15 líneas |
| Validate check `[view-purity]` | ~60 líneas |
| **Total nuevo + modificado** | **~125 líneas** |

Pequeño y bien-bounded. Single PR.

## 7. Orden de validación pre-commit

1. `python3 validate.py` → 24/24 (incluye `[view-purity]` nuevo nivel WARN, 0 warnings activas tras migración)
2. `node --test tests/unit/*.test.js` → 131/131 (sin cambios — no se añadieron tests)
3. JS syntax check (validate.py [js-syntax])
4. QA browser:
   - Pre: dump DOM innerHTML de los containers afectados
   - Migrar
   - Post: dump idéntico, diff debe ser vacío
   - Mi Plan tab (con un schedule existente — la sesión QA de p5.5 dejó uno)
   - Festival switch (verificar makeProgramPoster/makeEventPoster aún funcionan)
   - shareAsImage (verificar _renderSavedAgendaHTML)
5. Diff review: cero cambios en HTML output, solo destructure añadido + signature change
6. `node scripts/bump-version.js`
7. Commit + push + PR
