# Plan técnico — Fase 6b (View Purity Tier 2)

## Restricciones de partida

### R1. Single-file en producción
Las 11 funciones siguen en index.html. Split físico a `view/` queda para
Fase 8. La migración cambia signature + read source + introduce nuevas
funciones pure-half adyacentes; no estructura de archivos.

### R2. Behavior preservation absoluta
HTML output **byte-identical** pre/post. Cero diferencias en:
- Tags, attributes, classes, style, IDs
- Text content (incluso whitespace)
- Orden de elementos

Verificación: DOM CRC dump pre/post en escenario controlado (mismo flujo
que 6a).

### R3. Cero cambios en lecturas de Model
Las funciones llaman Model functions (`screensConflict`, `screeningPassed`,
`_resolveVenue`, `parseProgramTitle`, etc.). Estas siguen como free var
refs — no entran en `state.snapshot()` destructure.

### R4. Caller flow intacto
Los **call sites** de las 11 funciones no rename. Para Group A y para los
impure callers de Group B, los call sites siguen invocando con el mismo
nombre que antes.

Para las pure halves nuevas de Group B (`XHTML`), son funciones nuevas —
solo se llaman desde sus respectivos impure callers.

### R5. Cero tests nuevos (mismo que 6a — R5)
Playwright T01-T10 + DOM CRC + manual QA cubren. Snapshot tests son brittle
para este tier. 6c será donde añadir tests targeted.

### R6. Validate check warning-only
Sigue WARNING. Promote a FAIL en Fase 7.

### R7. Orden de migración respeta dependencias

- Group A primero (más simple, menor blast radius)
- Group B segundo, ordenado por tamaño creciente
- Group C dead-remove al final (cleanup)

Cero dependencias entre las 11 funciones — pueden migrarse en cualquier
orden, pero el orden creciente es el camino seguro.

## 1. Patrón de migración por grupo

### 1.1 Group A — Tier 1 pattern (4 funciones)

Idéntico al patrón de Fase 6a:

```js
// ANTES
function renderPrioStrip() {
  // lee FILMS, PRIO_LIMIT, prioritized como globals
  return `<div>...</div>`;
}

// DESPUÉS
function renderPrioStrip(state) {
  const { FILMS, PRIO_LIMIT, prioritized } = state.snapshot();
  return `<div>...</div>`;
}
```

Callers actualizados para pasar `state`.

### 1.2 Group B — Pure + impure caller split (7 funciones)

Patrón canónico (E1a):

```js
// ANTES (monolítico)
function renderProgramaChips() {
  // ... build HTML ...
  document.getElementById('chips-container').innerHTML = html;
}

// DESPUÉS
function renderProgramaChipsHTML(state) {  // ← NUEVA, pure
  const { ... } = state.snapshot();
  // ... build HTML ...
  return html;
}
function renderProgramaChips() {  // ← MANTIENE nombre, impure caller
  const el = document.getElementById('chips-container');
  if (!el) return;
  el.innerHTML = renderProgramaChipsHTML(state);
}
```

**Caso especial `renderFilmListHTML`** (ya tiene HTML suffix):

```js
// ANTES (175 líneas, retorna HTML + setTimeout post-render mutations)
function renderFilmListHTML() {
  // ... 165 líneas de build HTML ...
  setTimeout(() => {
    // updates pill-prio-cnt, pill-int-cnt, pill-yv-cnt + visibility
  }, 0);
  return html;
}

// DESPUÉS
function renderFilmListHTML(state) {  // ← MANTIENE nombre, ahora PURE
  const { ... } = state.snapshot();
  // ... 165 líneas de build HTML ... (sin setTimeout)
  return html;
}
function _rerenderFilmList() {  // ← NUEVO impure caller
  const lel = document.getElementById('ag-film-list');
  if (!lel) return;
  lel.innerHTML = renderFilmListHTML(state);
  // Recompute pill counts (filter sobre Sets, O(n) trivial)
  const { watchlist, watched, prioritized } = state.snapshot();
  const prioList = [...prioritized];
  const nonPrioList = [...watchlist].filter(t => !prioritized.has(t));
  const watchedList = [...watched];
  // setTimeout: update pills + visibility
  setTimeout(() => {
    const _pp = document.getElementById('pill-prio-cnt');
    if (_pp) _pp.textContent = prioList.length ? `${prioList.length}/${PRIO_LIMIT}` : '—';
    // ... etc
  }, 0);
}
```

Callers actuales:
- `lel.innerHTML = renderFilmListHTML();` (L6490) → reemplazar por
  `_rerenderFilmList()` (que internamente hace lo mismo + setTimeout)
- `<div id="ag-film-list">${renderFilmListHTML()}</div>` (L8832) →
  reemplazar por `renderFilmListHTML(state)` (pure, dentro de template
  literal sigue retornando string)

### 1.3 Group C — Dead remove

`renderSimPanel` (L6818-6829): eliminar las 12 líneas. Cero callsites.

## 2. Lista de migraciones por función

(orden de ejecución — Group A primero, luego Group B por tamaño creciente)

### 2.1 Group A (4 funciones)

#### 2.1.1 `renderSavedAgendaHTML` (13 líneas, wrapper)

```js
function renderSavedAgendaHTML(state) {
  try { return _renderSavedAgendaHTML(state); }
  catch (err) { ... }
}
```

Caller único: L8838 `view.innerHTML=_progressHtmlPlan+renderSavedAgendaHTML();`
→ `view.innerHTML=_progressHtmlPlan+renderSavedAgendaHTML(state);`

#### 2.1.2 `renderFlowProgress` (23 líneas)

```js
function renderFlowProgress(activeTab) {
  // ANTES: lee savedAgenda como global
  // DESPUÉS:
  const { savedAgenda } = state.snapshot();
  // ... resto ...
}
```

Wait — `renderFlowProgress(activeTab)` ya recibe `activeTab` como param.
Nueva signature: `renderFlowProgress(state, activeTab)`. 3 callers actualizan.

#### 2.1.3 `renderPrioStrip` (20 líneas)

```js
function renderPrioStrip(state) {
  const { FILMS, PRIO_LIMIT, prioritized } = state.snapshot();
  // ... resto ...
}
```

1 caller actualiza.

#### 2.1.4 `renderFilmAlternatives` (36 líneas)

```js
function renderFilmAlternatives(state, title, day, time) {
  const { FILMS, watched, savedAgenda } = state.snapshot();
  // ... resto ...
}
```

2 callers actualizan.

### 2.2 Group B (7 funciones, orden creciente)

#### 2.2.1 `renderRatingStars` (9 → 5+4 líneas)

```js
function renderRatingStarsHTML(state, current) {
  let html = '';
  for (let i = 1; i <= 5; i++) {
    const fill = current >= i ? 'full' : current >= i - 0.5 ? 'half' : 'none';
    html += `<div class="touch-44">${starSVG(fill)}</div>`;
  }
  return html;
}
function renderRatingStars(current) {
  const el = document.getElementById('rating-stars');
  if (!el) return;
  el.innerHTML = renderRatingStarsHTML(state, current);
}
```

Nota: la pure half NO lee state — solo recibe `current` como param. El
state se incluye en signature por consistencia + futuro-proofing (Fase 7
quizás use state.subscribe para re-renderear). Si parece overkill, dejarlo
sin state en signature.

**Decisión interna**: incluir `state` en signature para uniformidad. Cero
costo runtime.

#### 2.2.2 `renderNoticesBanner` (20 → ~14+6 líneas)

```js
function renderNoticesBannerHTML(state, [params si los hay]) {
  // ... pure build HTML ...
  return html;
}
function renderNoticesBanner() {
  const el = document.getElementById('notices-banner');
  if (!el) return;
  el.innerHTML = renderNoticesBannerHTML(state);
}
```

2 callers (L10053, L10134): siguen invocando `renderNoticesBanner()` sin
cambio.

#### 2.2.3 `renderProgramaChips` (24 → ~18+6 líneas)

Similar pattern. 1 caller.

#### 2.2.4 `_renderSplashDropdown` (38 → ~30+8 líneas)

```js
function _renderSplashDropdownHTML(state, activeFestId) {
  // ... pure ...
}
function _renderSplashDropdown(activeFestId) {
  // ... DOM mutation ...
}
```

4 callers.

#### 2.2.5 `_renderFestivalSelector` (41 → ~33+8 líneas)

Igual patrón. 4 callers.

#### 2.2.6 `renderAvDay` (44 → ~36+8 líneas)

```js
function renderAvDayHTML(state, day, [otros params si los hay]) {
  const { availability, ... } = state.snapshot();
  // ... build HTML para el row del día ...
  return html;
}
function renderAvDay(day) {
  const row = document.getElementById(`av-row-${day}`);
  if (!row) return;
  row.innerHTML = renderAvDayHTML(state, day);
}
```

2 callers (ambos en onclick handlers dentro de template literals): siguen
invocando `renderAvDay('dia-key')`.

#### 2.2.7 `renderFilmListHTML` (175 → 165+10 líneas)

Ver §1.2 caso especial. Pure half mantiene nombre. Nuevo impure caller
`_rerenderFilmList()` con setTimeout movido.

2 callers — uno migra a `_rerenderFilmList()`, el otro queda como
`renderFilmListHTML(state)` (dentro de template literal).

### 2.3 Group C — Dead remove

```js
// ANTES
function renderSimPanel() {
  // ... 12 líneas ...
}

// DESPUÉS
// (función eliminada)
```

## 3. Validate check `[view-purity]` — extensión

### 3.1 Cambios al check existente

```python
# ANTES (post-6a):
TIER1_FNS = ['makeProgramPoster', 'makeEventPoster', 'renderUnconfirmed',
             '_renderSavedAgendaHTML', 'renderContextualHeader',
             'renderMiPlanCalendar']

# DESPUÉS (post-6b):
PURE_FNS = [
    # Tier 1 originales (Fase 6a)
    'makeProgramPoster', 'makeEventPoster', 'renderUnconfirmed',
    '_renderSavedAgendaHTML', 'renderContextualHeader',
    'renderMiPlanCalendar',
    # Group A reclasificados (Fase 6b)
    'renderSavedAgendaHTML', 'renderFlowProgress', 'renderPrioStrip',
    'renderFilmAlternatives',
    # Group B pure halves (Fase 6b)
    'renderRatingStarsHTML', 'renderNoticesBannerHTML',
    'renderProgramaChipsHTML', '_renderSplashDropdownHTML',
    '_renderFestivalSelectorHTML', 'renderAvDayHTML',
    'renderFilmListHTML',  # ya pura post-6b
]
# Total: 17 funciones puras tracked
```

El rename `TIER1_FNS` → `PURE_FNS` es global en validate.py:
- Variable declaration
- Loop usage
- Mensaje del ok() report

### 3.2 La logic del check no cambia

Sigue detectando los mismos 7 patrones (read directo del roster, innerHTML=,
outerHTML=, classList, appendChild, insertAdjacent, setTimeout/rAF).

Whitelist sigue: destructure de `state.snapshot()` en primeras 6 líneas.

## 4. Test strategy (cero tests nuevos — R5)

### 4.1 Cobertura existente

- Playwright T01-T10 (CI)
- 131 unit tests (Model + state)
- 24 validate checks (post-6a, será 24 post-6b también)

### 4.2 Manual QA browser

Post-migración, verificar visualmente:
- Mi Plan tab (renderPrioStrip, renderFilmListHTML pills, renderFlowProgress,
  renderFilmAlternatives, renderSavedAgendaHTML wrapper)
- Programa tab (renderProgramaChips, renderNoticesBanner)
- Festival selector (_renderFestivalSelector, en topbar)
- Splash overlay (_renderSplashDropdown — solo si el primer init)
- Availability sheet (renderAvDay)
- Rating sheet (renderRatingStars)

### 4.3 DOM CRC pre/post diff

Mismo método que 6a:
- Capturar CRC de containers afectados PRE
- Aplicar migraciones
- Re-capturar POST
- Verificar match exacto

Containers a CRC-checkear:
- `ag-view` (Mi Plan)
- `programa-list` (Programa)
- `av-row-*` para algún day (Availability)
- Output de `_renderFestivalSelectorHTML(state, activeFestId)` directo
- Output de `renderRatingStarsHTML(state, 3)` directo (con stars)

## 5. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| `renderFilmListHTML` setTimeout depends on derived counts — al separar a `_rerenderFilmList`, recomputamos counts pueden divergir si state cambia mid-setTimeout | El setTimeout(0) corre en next tick. Entre el `renderFilmListHTML` call y el setTimeout fire, JS es single-threaded — no hay race. State no cambia |
| `renderAvDay` mutates `av-row-${day}` específico. El callback en onclick lee `av-from-${day}` y `av-to-${day}` inputs después | Pure half retorna HTML completo del row. Impure caller hace `row.innerHTML = ...`. Los inputs siguen leyéndose por el handler `addBlock(day)` separado |
| Group A `renderSavedAgendaHTML` ya pasaba state vía free var a `_renderSavedAgendaHTML(state)`. Ahora signature explícita | Caller único actualiza: L8838 |
| Pure half de Group B no lee state en algunos casos (renderRatingStars) | Mantener `state` en signature por uniformidad + futuro-proofing |
| Validate check rename `TIER1_FNS` → `PURE_FNS` puede romper si hay otros usos | Solo se usa dentro del bloque `[view-purity]` — find/replace local |
| HTML output difiere por orden de propiedades | Destructure order no afecta HTML output. R2 robusto |
| Callers en template literals (`${render...()}`) — pasar state desde adentro de un template | OK — `state` es module-level const, accesible como free var desde cualquier scope |

## 6. Tamaño estimado

| Concepto | Líneas |
|---|---|
| Group A (4 fns) — añadir state + destructure | ~20 líneas tocadas |
| Group B (7 fns) — split en pure + impure caller | ~370 líneas reorganizadas (extracción) + ~50 líneas nuevas para impure callers |
| Group C dead remove (renderSimPanel) | -12 líneas |
| Callers actualizados (23 sitios) | ~25 líneas |
| Validate check rename + extend (PURE_FNS list) | ~15 líneas |
| **Total** | **~470 líneas tocadas** (similar magnitud a 6a) |

Single PR.

## 7. Orden de validación pre-commit

1. `python3 validate.py` → 24/24 (sin warnings — pure halves nuevas en
   `PURE_FNS` list pasan el check)
2. `node --test tests/unit/*.test.js` → 131/131 (sin cambios)
3. JS syntax (validate.py `[js-syntax]`)
4. QA browser:
   - PRE: dump CRC de containers
   - Migrar
   - POST: dump CRC, debe match exacto
   - Verificar visualmente cada tab/sheet afectado
5. Diff review: pure halves extractas correctamente, impure callers
   contienen solo DOM mutation, cero state reads directos
6. `node scripts/bump-version.js`
7. Commit + push + PR
