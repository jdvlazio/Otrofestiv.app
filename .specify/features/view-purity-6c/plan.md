# Plan técnico — Fase 6c (View Purity Tier 3)

## Restricciones de partida

### R1. Single-file en producción
Las 8 funciones siguen en index.html. Split físico a `view/` para Fase 8.

### R2. Behavior preservation absoluta
HTML output **byte-identical** pre/post. Verificación: DOM CRC dump pre/post
en escenario controlado (mismo método de 6a/6b).

### R3. Cero cambios en lecturas de Model
Las orchestrators llaman Model functions (screensConflict, screeningPassed,
_resolveVenue, parseProgramTitle, getFilmPoster, etc.). Estas siguen como
free vars — no entran en destructure de state.

### R4. Cero caller churn
Los 60+ call sites totales de Group I + Group II **no cambian**. Los impure
callers reciben sus args originales (sin agregar `state`). El acceso a state
en el impure caller es vía free var module-level.

### R5. Cero tests nuevos
Playwright T01-T10 + T32 + DOM CRC + manual QA cubren. Tier 3 orchestrators
con DOM coupling profundo no son target eficiente para unit tests.

### R6. Validate check warning-only
Sigue WARNING. Promote a FAIL en Fase 7.

### R7. **QA boot path obligatorio** (F6 aprobado)
NO es opcional. Tras migrar todas las funciones, ANTES de la verificación
final, ejecutar QA boot path:
1. `localStorage.clear()` + reload
2. Llamar `showAgView()`, `render()`, `_renderProgramaContent()` SIN
   haber llamado `loadFestival(*)` previamente
3. Verificar consola sin errors
4. Solo si paso 3 limpio → seguir con QA flow normal

Atrapa caller-missing-state bugs antes de CI (lección del bug T32 de 6b).

### R8. Orden de migración
- Group IV primero (dead remove, baseline cleanup)
- Group I segundo, en orden creciente de tamaño (26→101 lines)
- Group II último (renderAgenda + render — branchy, mayor riesgo)
- Validate extension al final
- QA boot path antes de pre-commit validate

## 1. Patrón de migración por grupo

### 1.1 Group I — Split E1a (5 funciones)

Patrón canónico:

```js
// ANTES (monolítico)
function renderX(...args) {
  // lee globals A, B, C
  const a = A.filter(...);
  // ... build HTML ...
  document.getElementById('container-x').innerHTML = html;
  // follow-ups si hay
}

// DESPUÉS
function renderXHTML(state, ...args) {  // NUEVA — pure
  const {A, B, C} = state.snapshot();
  const a = A.filter(...);
  // ... build HTML ...
  return html;
}
function renderX(...args) {  // MANTIENE nombre — impure caller
  const el = document.getElementById('container-x');
  if (!el) return;
  el.innerHTML = renderXHTML(state, ...args);  // state como free var
  // follow-ups si hay
}
```

**Caso especial `renderSbar`** (innerHTML + classList + appendChild):
- Pure half retorna HTML del contenido principal (lo que va a un container)
- Impure caller: innerHTML + classList toggle + appendChild

**Caso especial `renderPeliculaView`** (3 innerHTML — multi-container):
Investigar al implementar. Posibles patrones:
- (a) Pure half retorna 1 string con todo concatenado, impure caller hace
  una sola innerHTML al root common ancestor
- (b) Pure half retorna objeto `{cnt, grid, ...}` con 3 strings, impure caller
  hace 3 innerHTML
- (c) 2-3 pure helpers chicas (`renderPeliculaCntHTML`, `renderPeliculaGridHTML`),
  impure caller compone

Decisión al implementar — depende de cómo está estructurado el body actual.

### 1.2 Group II — State destructure only (2 funciones)

Patrón Tier 1:

```js
// ANTES
function renderAgenda(){
  const view=document.getElementById('ag-view');
  // ... branches con reads directos a savedAgenda, FILMS, watched, etc. ...
}

// DESPUÉS
function renderAgenda(){
  const {savedAgenda, FILMS, _activeFestId, watched, watchlist} = state.snapshot();
  const view=document.getElementById('ag-view');
  // ... mismo body, ahora usa destructured vars ...
}
```

Cero signature change. Cero callers cambiados.

### 1.3 Group III — Skip
`_renderProgramaContent` y `_renderAfterSync` no se tocan en 6c. Migran en
Fase 7 como Controllers.

### 1.4 Group IV — Dead remove
`renderMiPlanList`:
1. Verificación git history (precedente: renderNextStrip en 6a usó `git log -S`)
2. Si confirmado dead → eliminar las 44 líneas

## 2. Lista de migraciones

(orden de ejecución — Group IV primero, Group I por tamaño creciente, Group II al final)

### 2.1 Group IV — Dead remove

#### renderMiPlanList (44 líneas)
- Verificar git history para entender contexto de orphaning
- Confirmar 0 callsites incluyendo strings en template literals
- Eliminar definición + cualquier doc comment que la mencione

### 2.2 Group I — Split (orden creciente)

#### 2.2.1 `renderAvBlocks` (26 líneas)
- Pure half `renderAvBlocksHTML(state)` → string
- Impure caller mantiene `renderAvBlocks()` + commit a `av-blocks-list`

#### 2.2.2 `renderSbar` (30 líneas)
- Pure half `renderSbarHTML(state)` → string del contenido
- Impure caller mantiene innerHTML + classList toggles + appendChild

#### 2.2.3 `renderProgramaList` (60 líneas)
- Pure half `renderProgramaListHTML(state)` → string
- Impure caller commit a `programa-list`

#### 2.2.4 `_renderExploreLista` (64 líneas)
- Pure half `_renderExploreListaHTML(state)` → string
- Impure caller commit a `programa-list` (mismo container que renderProgramaList — diferentes modos de vista)

#### 2.2.5 `renderPeliculaView` (101 líneas)
- **Investigar primero**: las 3 innerHTML van a qué containers?
- Implementar según pattern (a), (b) o (c) de §1.1
- Posiblemente `renderPeliculaViewHTML(state)` returns string OR helpers múltiples

### 2.3 Group II — State destructure only

#### 2.3.1 `render` (53 líneas)
```js
function render(){
  const {FILMS, _activeFestId, watched, watchlist} = state.snapshot();
  // ... body unchanged ...
}
```

#### 2.3.2 `renderAgenda` (78 líneas)
```js
function renderAgenda(){
  const {savedAgenda, FILMS, _activeFestId, watched, watchlist} = state.snapshot();
  // ... body unchanged ...
}
```

## 3. Validate check `[view-purity]` — extensión

### 3.1 PURE_FNS lista actualizada

```python
PURE_FNS = [
    # Tier 1 originales (Fase 6a)
    'makeProgramPoster', 'makeEventPoster',
    'renderUnconfirmed', '_renderSavedAgendaHTML',
    'renderContextualHeader', 'renderMiPlanCalendar',
    # Group A reclasificadas (Fase 6b)
    'renderSavedAgendaHTML', 'renderFlowProgress',
    'renderPrioStrip', 'renderFilmAlternatives',
    # Group B pure halves (Fase 6b)
    'renderRatingStarsHTML', 'renderNoticesBannerHTML',
    'renderProgramaChipsHTML', '_renderSplashDropdownHTML',
    '_renderFestivalSelectorHTML', 'renderAvDayHTML',
    'renderFilmListHTML',
    # Group I pure halves (Fase 6c) — NUEVAS
    'renderAvBlocksHTML', 'renderSbarHTML',
    'renderProgramaListHTML', '_renderExploreListaHTML',
    'renderPeliculaViewHTML',
]
# Total: 22 funciones puras tracked
```

### 3.2 Comentario para Group II

Añadir en validate.py:

```python
# Group II Tier 3 orchestrators (renderAgenda, render) son impuros
# legítimos — branching con follow-ups branch-específicos hace split
# impráctico. NO entran en PURE_FNS. Verificación de state destructure
# al top queda como code review (no automatizada por ahora).
```

## 4. Test strategy

### 4.1 Cobertura existente (sin cambios)
- Playwright T01-T10 + T32 smoke navegación
- 131 unit tests
- 24 validate checks

### 4.2 **QA boot path obligatorio** (paso bloqueante)

Pre-implementation:
- DOM CRC baseline PRE (mismo método 6a/6b)

Post-implementation, ANTES del pre-commit validate:

```js
// Browser console:
localStorage.clear();
location.reload();
// Tras reload, antes de splash:
showAgView();
render();
_renderProgramaContent();
// Verificar window.onerror = null + console limpia
```

Si CUALQUIERA de las 3 funciones throwes → fail. Atrapa caller-missing-state
de Tier 3 orchestrators o sus sub-renders. Bug equivalente a T32 de 6b.

### 4.3 QA flow normal post-boot

- loadFestival(tribeca2026)
- Mi Plan tab → verifica renderAgenda branches (seleccion/miplan/planner)
- Programa tab → verifica render, renderPeliculaView, renderProgramaList,
  _renderExploreLista, renderSbar
- Availability sheet → verifica renderAvBlocks

### 4.4 DOM CRC pre/post

Containers a CRC-checkear (basado en 6b baseline + nuevos):
- `ag-view` (renderAgenda output)
- `programa-list` (renderProgramaList, _renderExploreLista)
- `grid` (render + renderPeliculaView)
- `cnt` (renderSbar / renderPeliculaView)
- `av-blocks-list` (renderAvBlocks)

## 5. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| `renderPeliculaView` con 3 innerHTML — pattern de split a decidir al implementar | Investigar body al ejecutar paso 2.2.5. Si multi-container, evaluar (a)/(b)/(c) según fits |
| `renderSbar` con appendChild — DOM tree construction, no solo innerHTML | Pure half cubre solo el contenido principal (string). Impure caller hace appendChild + classList |
| `renderAgenda` y `render` siguen impuros — el dev futuro puede asumir que son testeables | Documentar en spec + comentario en validate.py PURE_FNS |
| Boot path bug equivalente a T32 6b oculto en Group I caller migration | F6 QA boot path obligatorio lo atrapa pre-CI |
| `renderMiPlanList` dead remove — callsite escondido en string template | Grep exhaustivo + verificación git history antes de remover |
| Multi-orchestrator coordination — `_renderProgramaContent` llama `renderPeliculaView`/`renderProgramaList`/`_renderExploreLista`. Si la impure caller de éstos pasa state vía free var, el dispatch desde _renderProgramaContent debería funcionar igual | Sin cambios en _renderProgramaContent. Test: clickear chip/day cambiar entre views — Playwright cubre |
| State destructure al top en renderAgenda agrega 5 reads que el body posiblemente no usa en todos los branches | Costo trivial — state.snapshot() es O(n=19). Aceptable. R2 byte-identity preservada |
| renderPeliculaView signature `()` actual — si cambia a `(state)` algunos callers (4) deben actualizarse | Mantener `()` signature, acceder state como free var (F3) |

## 6. Tamaño estimado

| Concepto | Líneas |
|---|---|
| Group I split (5 fns) — extracción pure + impure caller | ~300 reorganizadas |
| Group II destructure-only (2 fns) — añadir destructure al top | ~10 líneas añadidas |
| Group IV dead remove (renderMiPlanList) | -44 |
| Validate check ext (PURE_FNS +5) | +5 |
| **Total** | **~270 líneas reorganizadas net** |

Magnitud similar a 6b (~470 LOC).

## 7. Orden de validación pre-commit

1. **QA boot path obligatorio** (paso 23 en tasks)
2. `python3 validate.py` → 24/24 (sin warnings)
3. `node --test tests/unit/*.test.js` → 131/131
4. JS syntax (validate.py `[js-syntax]`)
5. QA flow normal — Mi Plan, Programa, Availability sheet
6. DOM CRC pre/post — 5 containers byte-identical
7. Diff review
8. `node scripts/bump-version.js`
9. Commit + push + PR
