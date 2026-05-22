# Spec — Event Delegation Wave 4: Final sites + listener rewrite (Fase 7c-4)

## Problema

Tras 7c-3 quedan **18 onclick inline** (en ocurrencias) en `index.html`. Son
los casos más complejos que requieren rediseño arquitectónico o helpers
nuevos:

- IIFE inline (scroll handlers)
- Overlay close lambdas (`if(event.target===this)closeX()`)
- Pattern N (`_openCombinedFilmSheet(JSON.parse(...))` — registry bug latente)
- Pattern H (`event.stopPropagation()` solo — requiere listener rewrite)
- Conditional onclick (`${cond?fnA:fnB}`)
- DOM-direct manipulation (`.remove()`, `scrollIntoView`, `scrollTo`)
- String builders que generan onclick en runtime (`_posterThumb`, search-item)

7c-4 es la **fase final** de event-delegation. Al completarse: **onclick = 0**,
y se promueve el check `[event-delegation]` de WARNING a FAIL.

## Causa raíz

Estos 18 sitios se postergaron en 7c-1/2/3 precisamente porque requieren:
1. Cambio arquitectónico en el listener (Pattern H walking-up)
2. Helpers compuestos nuevos (DOM-direct, search builders)
3. Fixes de registry bugs latentes (Pattern N)
4. Refactor de view-helpers que generan onclick (`emptyStateHero`, `_posterThumb`)

## Solución

### A. Listener walking-up rewrite (D1 — núcleo de 7c-4)

El listener actual usa `e.target.closest('[data-action]')` que sube por el DOM
y encuentra el primer ancestor con `data-action`. Problema: un wrapper con
`data-stop="1"` (sin data-action) entre el target y un ancestor con data-action
NO bloquea ese ancestor — `closest()` lo atraviesa.

**Rewrite a loop manual:**

```js
document.addEventListener('click', function(e) {
  let node = e.target;
  while (node && node !== document) {
    if (node.dataset) {
      if (node.dataset.action) {
        if (node.dataset.stop === '1') e.stopPropagation();
        const handler = ACTION_REGISTRY[node.dataset.action];
        if (handler) handler(node, e);
        return;
      }
      if (node.dataset.stop === '1') {
        // Wrapper Pattern H: bloquea lookup de action ancestro + stop
        e.stopPropagation();
        return;
      }
    }
    node = node.parentElement;
  }
  // close-on-background-click (sin action/stop en la ascendencia)
  const bg = e.target.closest('[data-close-bg]');
  if (bg && e.target === bg) {
    const closeName = 'close' + bg.dataset.closeBg;
    const closeFn = ACTION_REGISTRY[closeName];
    if (closeFn) closeFn();
  }
});
```

**Garantía de no-regresión:**
- Comportamiento IDÉNTICO para los 125 sites con data-action (el loop encuentra
  el primer data-action subiendo, igual que `closest()`).
- Los sites P+S (data-action + data-stop en mismo elemento) ejecutan
  stopPropagation + handler igual que antes.
- La nueva rama (`data-stop="1"` sin data-action) SOLO activa para los 2
  wrappers Pattern H nuevos.
- `data-close-bg` branch intacto (overlays no tienen action/stop → loop sale →
  branch corre).

### B. Migración de 18 sites por grupo

#### Grupo 1 — Overlay close (data-close-bg, 2 sites)

```html
<!-- L2473 ANTES -->
<div class="av-sheet-overlay" id="av-sheet-overlay" ... onclick="if(event.target===this)closeAvSheet()">
<!-- DESPUÉS -->
<div class="av-sheet-overlay" id="av-sheet-overlay" ... data-close-bg="AvSheet">

<!-- L12110 ANTES -->
<div class="auth-sheet" id="auth-sheet" onclick="if(event.target===this)closeAuthSheet()">
<!-- DESPUÉS -->
<div class="auth-sheet" id="auth-sheet" data-close-bg="AuthSheet">
```

`closeAvSheet`/`closeAuthSheet` ya en registry. Infra `data-close-bg` de 7c-1.

#### Grupo 2 — IIFE scroll → `scrollToAgSec` (3 sites)

```html
<!-- L2570/2573/2576 ANTES -->
<button class="ag-sec-pill prio" id="pill-prio" onclick="(()=>{...window.scrollTo(...)})()">
<!-- DESPUÉS -->
<button class="ag-sec-pill prio" id="pill-prio" data-action="scrollToAgSec" data-target="sec-prio">
```

Helper `_scrollToAgSection` (L3013, de 7c-1) es byte-idéntico al IIFE. Entry
`scrollToAgSec` ya existe. Targets: `sec-prio`, `sec-int`, `sec-yv`.

#### Grupo 3 — Pattern N (`_openCombinedFilmSheet`, 4 sites)

**Fix registry entry:**
```js
// ANTES (bug):
_openCombinedFilmSheet:(el) => _openCombinedFilmSheet(el.dataset.title),
// DESPUÉS:
_openCombinedFilmSheet:(el) => _openCombinedFilmSheet(JSON.parse(el.dataset.film)),
```

```html
<!-- L9700/9701/9703/9704 ANTES -->
<img class="psp-card psp-front" ... onclick="_openCombinedFilmSheet(JSON.parse(this.dataset.film))" data-film="${_fd1}">
<!-- DESPUÉS -->
<img class="psp-card psp-front" ... data-action="_openCombinedFilmSheet" data-film="${_fd1}">
```

#### Grupo 4 — Pattern H (stopPropagation alone, 2 sites)

```html
<!-- L5461 ANTES -->
<div class="js-open-pel" data-title="${s._title||''}" ... onclick="event.stopPropagation()">
<!-- DESPUÉS -->
<div class="js-open-pel" data-title="${s._title||''}" ... data-stop="1">

<!-- L5464 ANTES -->
<div class="mplan-tc" onclick="event.stopPropagation()">
<!-- DESPUÉS -->
<div class="mplan-tc" data-stop="1">
```

Depende del listener rewrite (sección A).

#### Grupo 5 — emptyStateHero refactor (1 site + 6 callers)

```js
// Signature ANTES: emptyStateHero(icon, title, sub, ctaLabel, ctaOnclick, ctaSecondary)
// Signature DESPUÉS: emptyStateHero(icon, title, sub, ctaLabel, ctaTab, ctaSecondary)

// Button ANTES:
${ctaLabel ? `<button class="..." onclick="${ctaOnclick}">${ctaLabel}</button>` : ''}
// Button DESPUÉS:
${ctaLabel ? `<button class="..." data-action="navTo" data-tab="${ctaTab}">${ctaLabel}</button>` : ''}
```

6 callers actualizados (todos pasan navTo-equivalentes):
| Línea | ctaOnclick actual | ctaTab nuevo |
|---|---|---|
| 6820 | `switchMainNav('mnav-cartelera');showDayView()` | `mnav-cartelera` |
| 7722 | `switchMainNav('mnav-cartelera');showDayView()` | `mnav-cartelera` |
| 7724 | `switchMainNav('mnav-planner');showAgView()` | `mnav-planner` |
| 9169 | `_hasMiPlan?...miplan...:...cartelera...` | `_hasMiPlan?'mnav-miplan':'mnav-cartelera'` |
| 9193 | `switchMainNav('mnav-miplan');showAgView()` | `mnav-miplan` |
| 9203 | `switchMainNav('mnav-seleccion');showAgView()` | `mnav-seleccion` |

#### Grupo 6 — Conditional onclick (1 site)

```html
<!-- L7061 ANTES -->
<button class="row-xs saved-check..." data-title data-day data-time data-venue data-dur
  onclick="${isDone?'toggleWatched(this.dataset.title,event)':'markWatchedFromPlan(this.dataset.title,this.dataset.day,this.dataset.time,this.dataset.venue,this.dataset.dur,event)'}">
<!-- DESPUÉS -->
<button class="row-xs saved-check..." data-title data-day data-time data-venue data-dur
  data-action="${isDone?'toggleWatched':'markWatchedFromPlan'}">
```

New entry: `markWatchedFromPlan: (el,e) => markWatchedFromPlan(el.dataset.title, el.dataset.day, el.dataset.time, el.dataset.venue, el.dataset.dur, e)`.

#### Grupo 7 — DOM-direct (3 new helpers)

```js
function _scrollToSuggestions() {
  document.querySelector('.suggestion-wrap')?.scrollIntoView({behavior:'smooth', block:'start'});
}
function _removeConflictModal() {
  document.getElementById('conflict-modal')?.remove();
}
function _scrollToTop() {
  window.scrollTo({top:0, behavior:'smooth'});
}
```

| Línea | onclick | data-action |
|---|---|---|
| 5423 | `document.querySelector('.suggestion-wrap')?.scrollIntoView(...)` | `scrollToSuggestions` |
| 7317 | `document.getElementById('conflict-modal').remove()` | `removeConflictModal` |
| 12155 | `window.scrollTo({top:0,behavior:'smooth'})` | `scrollToTop` |

#### Grupo 8 — String builders (2 new helpers + 1 refactor)

**`_posterThumb` refactor (D3 Opción A):** eliminar param `onclickJs`. El único
consumer L7788 pasa `openPelSheet('${title}')` → reemplazar por el mecanismo
`js-open-pel` (clase + `data-title`) que ya maneja el capture listener.

```js
// _posterThumb signature ANTES: _posterThumb(f, cssClass, onclickJs, loading)
// DESPUÉS: _posterThumb(f, cssClass, loading)
// Se elimina la construcción de _oc (L4466).
```

10 de 11 callers pasan `null` (no afectados). L7788 caller:
```js
// ANTES: _posterThumb(_af,'lb-poster',`openPelSheet('${_safeMpT2}')`)
// DESPUÉS: _posterThumb(_af,'lb-poster') + wrapper con clase js-open-pel + data-title
```

**search-item (L11915) — 2 helpers nuevos:**
```js
function _searchOpenFilm(title) {
  searchClose();
  openPelSheet(title);
}
function _searchOpenCorto(title, country, dur, section, flags) {
  searchClose();
  openCortoSheet(title, country, dur, section, flags);
}
```

```js
// search-item ANTES (onclick string builder):
const onclick = f._isCortoItem ? `searchClose();openCortoSheet(...)` : `searchClose();openPelSheet(...)`;
return '<div class="search-item" onclick="'+onclick+'">'...
// DESPUÉS:
// data-action + data-* attributes; conditional action name
```

### C. Promote check `[event-delegation]` a FAIL (D6)

Al cerrar 7c-4 → onclick = 0. Promover el check de WARNING a FAIL:
- Si `onclick=` remaining > 0 (excluyendo whitelist explícita) → FAIL
- Typo detection (data-action sin entry) → FAIL
- Dead entry detection → sigue informativo (tolerado para composite helpers)

## Inventario completo (18 sites)

| # | Línea | Grupo | onclick actual | Destino |
|---|---|---|---|---|
| 1 | 2473 | 1 | overlay closeAvSheet | `data-close-bg="AvSheet"` |
| 2 | 12110 | 1 | overlay closeAuthSheet | `data-close-bg="AuthSheet"` |
| 3 | 2570 | 2 | IIFE scroll sec-prio | `scrollToAgSec` + `data-target="sec-prio"` |
| 4 | 2573 | 2 | IIFE scroll sec-int | `scrollToAgSec` + `data-target="sec-int"` |
| 5 | 2576 | 2 | IIFE scroll sec-yv | `scrollToAgSec` + `data-target="sec-yv"` |
| 6 | 9700 | 3 | Pattern N psp-front | `_openCombinedFilmSheet` (fix entry) |
| 7 | 9701 | 3 | Pattern N psp-front-ph | `_openCombinedFilmSheet` |
| 8 | 9703 | 3 | Pattern N psp-back | `_openCombinedFilmSheet` |
| 9 | 9704 | 3 | Pattern N psp-back-ph | `_openCombinedFilmSheet` |
| 10 | 5461 | 4 | Pattern H js-open-pel wrapper | `data-stop="1"` |
| 11 | 5464 | 4 | Pattern H mplan-tc | `data-stop="1"` |
| 12 | 5960 | 5 | emptyStateHero ctaOnclick | `navTo` + `data-tab` (refactor) |
| 13 | 7061 | 6 | conditional toggleWatched/markWatchedFromPlan | conditional `data-action` |
| 14 | 5423 | 7 | scrollIntoView suggestions | `scrollToSuggestions` |
| 15 | 7317 | 7 | conflict-modal .remove() | `removeConflictModal` |
| 16 | 12155 | 7 | back-top scrollTo | `scrollToTop` |
| 17 | 4466 | 8 | _posterThumb onclickJs builder | refactor (drop param) |
| 18 | 11915 | 8 | search-item onclick builder | `searchOpenFilm`/`searchOpenCorto` |

## Decisiones de diseño incorporadas

| # | Decisión | Aplicación en 7c-4 |
|---|---|---|
| D1 | Listener walking-up rewrite | Loop manual; QA bloqueante de 125 sites |
| D2 | emptyStateHero ctaOnclick→ctaTab | Refactor view-helper + 6 callers |
| D3 | _posterThumb onclickJs | **Opción A** — eliminar param, js-open-pel en L7788 |
| D4 | search-item builders | 2 helpers `_searchOpenFilm`/`_searchOpenCorto` |
| D5 | 5 helpers + 6 entries + 1 fix + 2 refactors | Registry 91 → 97 |
| D6 | Promote check a FAIL | Al cierre de 7c-4 (onclick=0) |

## ACTION_REGISTRY post-7c-4 (97 entries)

| Tipo | Items |
|---|---|
| New helpers (5) | `_scrollToSuggestions`, `_removeConflictModal`, `_scrollToTop`, `_searchOpenFilm`, `_searchOpenCorto` |
| New entries (6) | markWatchedFromPlan, scrollToSuggestions, removeConflictModal, scrollToTop, searchOpenFilm, searchOpenCorto |
| Fixed entries (1) | `_openCombinedFilmSheet` (JSON.parse) |
| Refactors (2) | `_posterThumb` (drop onclickJs), `emptyStateHero` (ctaOnclick→ctaTab) |

## R2' (functional equivalence)

Mismo enfoque. Verificación:

1. **Functional equivalence** por grupo
2. **QA BLOQUEANTE — 125 sites existentes** (D1 requisito): tras el listener
   rewrite, verificar que los 125 data-action sites de 7c-1/2/3 siguen
   dispatcheando correctamente. Incluye:
   - Todos los data-action únicos en DOM live resuelven a registry (0 typos)
   - Click-test representativo por categoría (A-G)
   - P+S sites (data-action + data-stop) siguen stopPropagation correcto
   - Los 2 wrappers Pattern H nuevos bloquean el ancestor
3. **Console clean**: 0 errors
4. **Playwright T01-T10 + T32** verde en CI
5. **QA Boot Path obligatorio**

## Lo que NO entra en 7c-4

Nada de event-delegation queda pendiente — 7c-4 es la fase final. Tras 7c-4:
onclick = 0, check promovido a FAIL.

## Definition of Done

- [ ] Listener rewrite a walking-up loop
- [ ] **QA BLOQUEANTE**: 125 sites existentes verificados post-rewrite (0
      regresión) + 2 Pattern H wrappers bloquean ancestor
- [ ] 5 helpers nuevos definidos
- [ ] ACTION_REGISTRY **97 entries** (6 new + 1 fix + existing)
- [ ] `_posterThumb` refactor (drop onclickJs) + L7788 caller
- [ ] `emptyStateHero` refactor (ctaOnclick→ctaTab) + 6 callers
- [ ] **18 sites migrados** → onclick = 0
- [ ] Check `[event-delegation]` promovido a FAIL
- [ ] `python3 validate.py` → 26/26
- [ ] `node --test tests/unit/*.test.js` → 131/131
- [ ] JS syntax check OK
- [ ] Functional equivalence R2' por grupo
- [ ] Playwright T01-T10 + T32 verde en CI
- [ ] QA Boot Path obligatorio → 0 errors
