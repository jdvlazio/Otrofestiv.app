# Plan técnico — Fase 7a (Controller Pattern, 20 action handlers)

## Restricciones de partida

### R1. Single-file en producción
Los 20 handlers siguen en index.html. Split físico a `controller/` queda
para Fase 8.

### R2. Behavior preservation absoluta
HTML output **byte-identical** + comportamiento idéntico tras cada acción
(toggle WL/watched/prio, save delay, etc.). Verificación: DOM CRC post-acción
+ snapshot del state.

### R3. Cero cambios en signature
Los 20 handlers conservan exactamente sus parámetros y nombres. Cero caller
churn — los 142 onclick + 29 addEventListener call sites siguen invocando
las mismas funciones con los mismos args. 7c se encargará del onclick→
delegation migration aparte.

### R4. Cero tests nuevos
Misma R5 que 6a/6b/6c. Playwright + DOM CRC + manual QA + QA boot path
obligatorio.

### R5. Validate check WARNING-only
`[controller-pattern]` nivel WARNING en 7a. Promote a FAIL en 7d cuando
subscribe pipeline elimina render calls explícitos y la separación es
estricta.

### R6. **QA boot path obligatorio**
Heredado de 6c (F6 enforced). Tras migrar todos los handlers:
1. `localStorage.clear()` + reload
2. ANTES de loadFestival, invocar muestra representativa de handlers
3. Verificar console.errors === [] (cero TypeError)

### R7. Orden de migración
- Pequeños primero (4-15 líneas) — pattern emerging
- Medianos (15-30 líneas) — aplicar pattern establecido
- Grandes (30-53 líneas) — refactor con confianza ya validada

## 1. Controller pattern canónico

### 1.1 Shape de los 5 pasos

```js
function actionName(arg1, arg2, ...) {
  // ────────────────────────────────────────────────
  // 1. READ — state snapshot + UI state al top
  // ────────────────────────────────────────────────
  const {watchlist, watched, savedAgenda, ...} = state.snapshot();
  // UI state reads (out-of-roster) van también al top si se usan
  const _isPel = activeView === 'agenda';

  // ────────────────────────────────────────────────
  // 2. GUARD — early returns
  // ────────────────────────────────────────────────
  if (festivalEnded()) return;
  if (!watchlist.has(arg1)) return;

  // ────────────────────────────────────────────────
  // 3. MUTATE — state.set/update/batchUpdate
  // ────────────────────────────────────────────────
  state.batchUpdate({
    watchlist: state._delFromSet(watchlist, arg1),
    watched: state._delFromSet(watched, arg1),
  });

  // ────────────────────────────────────────────────
  // 4. PERSIST — explicit save (con cloud sync interno)
  // ────────────────────────────────────────────────
  saveWL();
  saveWatched();

  // ────────────────────────────────────────────────
  // 5. RENDER + UI EFFECTS — al final
  // ────────────────────────────────────────────────
  updateCardState(arg1);
  updateAgTab();
  renderAgenda();
  showToast('Quitado', 'info');
}
```

### 1.2 Variantes aceptadas

**Handlers sin reads de state**: pueden omitir el destructure top:
```js
function clearDelay(title, day, time) {
  const k = title + '|' + day + '|' + time;
  state.update('filmDelays', fd => state._omit(fd, k));
  saveDelays();
  renderAgenda();
}
```

**Handlers con confirm modal callback**: el callback ES el handler real
post-confirmación. El outer handler solo dispara el modal:
```js
function removeFromAgenda(title) {
  if (!savedAgenda) return;
  const _s = title.length > 36 ? title.slice(0,34)+'…' : title;
  showActionModal(t('plan_quitar_plan'), `<b>${_s}</b>...`, t('misc_quitar'),
    () => {  // ← este callback es el "real" handler
      // 1. READ, 2. GUARD, 3. MUTATE, 4. PERSIST, 5. RENDER aquí
    });
}
```

Los modal callbacks NO necesitan re-aplicar el pattern — son closures
internas. Solo el outer handler nombrado se valida por el check.

### 1.3 Anti-patrón a corregir

**Reads dispersos a través del body**:
```js
// ANTES
function toggleX(title) {
  if (watchlist.has(title)) {  // ← read inline
    // ...
    state.update('watched', s => state._delFromSet(s, title));
    if (savedAgenda) {  // ← read inline tras mutation
      // ...
    }
  }
}

// DESPUÉS
function toggleX(title) {
  const {watchlist, watched, savedAgenda} = state.snapshot();  // ← read al top
  if (watchlist.has(title)) {
    state.update('watched', s => state._delFromSet(s, title));
    if (savedAgenda) {
      // ...
    }
  }
}
```

**Render call ANTES de terminar mutations**:
```js
// ANTES — render entre mutations (rompe shape mutate→render)
state.update('watchlist', ...);
renderAgenda();  // ← side effect intermedio
state.update('watched', ...);  // ← más mutation post-render

// DESPUÉS — agrupar mutations en batchUpdate o secuencia consecutiva
state.batchUpdate({watchlist: ..., watched: ...});
renderAgenda();
```

## 2. Lista de migraciones (orden creciente de tamaño)

### 2.1 Pequeños (4-15 líneas) — 8 fns

| Función | Líneas | State reads necesarios | Acciones |
|---|---|---|---|
| `removeBlock` | 4 | (none — solo escribe) | state.update + saveAV + render |
| `clearDelay` | 4 | (none) | state.update + saveDelays + render |
| `clearSavedAgenda` | 6 | (none) | state.set + storage.remove + render |
| `applySimTime` | 12 | (none) | state.set + render |
| `setDelay` | 12 | filmDelays, filmDelaysHistory | batchUpdate + saveDelays + render |
| `undoDelay` | 11 | filmDelays, filmDelaysHistory | batchUpdate + saveDelays + render |
| `checkinLaVi` | 11 | watched | update + saveWatched + render |
| `savePVRating` | 10 | (none — solo escribe) | update + saveFilmRatings + showToast |

### 2.2 Medianos (15-30 líneas) — 8 fns

| Función | Líneas | State reads |
|---|---|---|
| `removeFromAgenda` | 15 | savedAgenda |
| `confirmConflictReplace` | 16 | savedAgenda |
| `toggleFullDay` | 16 | availability |
| `addBlock` | 19 | availability |
| `markWatchedFromPlan` | 22 | watched, watchlist |
| `setLang` | 23 | _lang |
| `confirmAvBlock` | 29 | availability |
| `togglePriority` | 30 | prioritized, watchlist, watched, PRIO_LIMIT |

### 2.3 Grandes (30-53 líneas) — 4 fns

| Función | Líneas | State reads |
|---|---|---|
| `toggleWatched` | 33 | watched, watchlist, savedAgenda |
| `confirmReplace` | 38 | savedAgenda, watchlist |
| `addSuggestion` | 44 | watchlist, prioritized, FILMS |
| `toggleWL` | 53 | watchlist, watched, prioritized, savedAgenda |

## 3. Validate check `[controller-pattern]`

### 3.1 Detección

```python
check = 'controller-pattern'
CONTROLLER_FNS = [
    # Listed in spec
]

# Para cada handler:
#   1. Encontrar primera occurrence de state.set/update/batchUpdate
#   2. Encontrar primera occurrence de renderX() o document.X mutation
#   3. WARN si hay state mutation DESPUÉS de la primera render call
#   4. WARN si hay reads del roster (savedAgenda, FILMS, etc.) DESPUÉS
#      de la primera mutation (i.e., not at top)
```

### 3.2 Whitelist

- Modal callbacks (closures dentro de showActionModal/showDestructiveModal/
  showConflictModal) NO se validan — son closures internas
- Helpers anidados (e.g., `_doAdd` dentro de addBlock) NO se validan —
  son closures, no Controllers nombrados

## 4. Test strategy

### 4.1 Cobertura existente
- Playwright T01-T10 + T32 smoke navegación
- 131 unit tests (no se tocan)
- 24 validate checks (será 25 con `[controller-pattern]`)

### 4.2 **QA Boot Path obligatorio** (heredado de 6c)

```js
localStorage.clear();
location.reload();
// Tras reload, ANTES de loadFestival:
showAgView();
render();
_renderProgramaContent();
// Invocar muestra representativa de handlers que no requieran params:
applySimTime(null);
// Verificar console errors === [], window._capturedErrs === []
```

### 4.3 QA flow normal post-implementation

- Toggle WL/watched/priority — verificar pills + cards update
- Add/remove plan → verificar Mi Plan refresh
- Set/undo delay — verificar filmDelays + filmDelaysHistory
- Add/remove availability block → renderAvBlocks update
- Change lang ES↔EN — DOM textContent update
- Apply sim time — simNow() reflect

### 4.4 DOM CRC pre/post

Containers a CRC-checkear:
- `ag-view` (renderAgenda)
- `programa-list` (renderProgramaList)
- `av-blocks-list` (renderAvBlocks)
- Estado del state.snapshot() (todos los 19 keys)

## 5. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Refactor inadvertidamente cambia el orden de side effects (e.g., showToast antes vs después de renderAgenda) | Code review + manual QA. R2 byte-identity del DOM también atrapa muchos |
| Algunos handlers tienen lógica condicional compleja que no encaja limpiamente en 5-pasos (e.g., toggleWL con confirm modal + branches) | Aceptar variantes: modal callbacks NO se re-aplican el pattern. Solo el outer handler nombrado |
| State destructure al top hace reads inútiles si el handler tiene early return temprano | Costo trivial (state.snapshot O(19)). Aceptable |
| Handlers que escriben a `_currentChips`, `_pelTitle`, etc. (UI state ephemeral out-of-roster) — siguen con writes directos | OK por ahora. UI state ephemeral entra en 7b/7d |
| `setLang` tiene mucha UI lógica (re-render full, fade, scroll preserve) — no se ajusta al pattern simple | Variante aceptada — el pattern es guideline, no contrato estricto en 7a (WARNING) |
| Modal callbacks crean "handlers anidados" que duplican lógica del outer — refactor parcial | Aceptado en 7a. Refactor adicional puede venir en 7b cuando sheets/modals tengan lifecycle propio |

## 6. Tamaño estimado

| Concepto | Líneas |
|---|---|
| 20 handlers reorganizados | ~387 LOC tocadas (cambios mecánicos) |
| Validate check `[controller-pattern]` | ~80 LOC |
| **Total** | **~470 LOC** |

Magnitud similar a 6b (~470 LOC). Single PR.

## 7. Orden de validación pre-commit

1. **QA boot path obligatorio** (paso bloqueante)
2. `python3 validate.py` → 25/25 (con `[controller-pattern]`)
3. `node --test tests/unit/*.test.js` → 131/131
4. JS syntax check
5. QA flow normal — handlers representativos
6. DOM CRC pre/post — 3 containers
7. Diff review
8. `node scripts/bump-version.js`
9. Commit + push + PR
