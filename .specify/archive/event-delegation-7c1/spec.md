# Spec — Event Delegation Foundation + Trivial Migration (Fase 7c-1)

## Problema

142 `onclick="..."` inline en index.html mezclan HTML template con lógica JS.
Cada re-render de innerHTML re-parsea estos atributos. Imposibilita:

- CSP estricto (inline event handlers bloqueados con `unsafe-inline`)
- Testing aislado de handlers (no se pueden mockear dispatched events sin re-render del template)
- Event delegation moderno (handlers attached antes de que elementos existan)
- File split de Fase 8 (handlers inline atan el HTML al JS scope global)

Fase 7c migra los 142 onclick a un sistema basado en `data-action` +
delegated event listener. Esta sub-fase (7c-1) establece la **foundation**
+ migra los 55 sites más simples (trivial — `fn()` y `fn('literal')`).

## Causa raíz

Crecimiento orgánico. Cada nuevo botón se creó con `onclick="fn()"` porque
era trivial. Sin una capa "Controller / event dispatch" centralizada, las
handlers terminaron embebidos en los templates HTML.

## Solución — Fase 7c-1 foundation + trivial migration

### A. Foundation establecida en 7c-1

1. **ACTION_REGISTRY** — mapping completo de los 87 handlers (76 funciones
   originales + 11 helpers compuestos nuevos). Categorías A-G visibles via
   comentarios sección.

2. **Delegated click listener** — único, en `document`. Detecta target
   `[data-action]` (walking up DOM), llama handler del registry.

3. **`data-close-bg` infra** — pattern para overlays close-on-background-click.
   `<div class="x-overlay" data-close-bg="AvSheet">` → click directo en el
   overlay (no en hijo) dispara `closeAvSheet()`.

4. **11 helpers compuestos** — funciones nuevas para encapsular los
   patrones multi-statement detectados. NO se usan aún en 7c-1 (los
   multi-statement migran en 7c-3); se definen UP-FRONT para que sus
   ACTION_REGISTRY entries estén operativas cuando 7c-3 las consuma:
   - `_scrollToAgSection(id)`, `_setExpandedFilm(val)`, `_setAvAddOpen(day, val)`
   - `_closePelAndRemove(title)`, `_closePelAndRate(title)`
   - `_navTo(tab)`, `_closeAuthAndReset()`, `_dismissToastAction()`
   - `_toggleCtxOlder()`, `_toggleWatchedAndClose(title, e)`, `_toggleWLAndClose(title, e)`

5. **Validate check `[event-delegation]`** — tracking del % migrado.
   Detecta:
   - Cuántos onclick inline quedan (count baseline → 0 al final de 7c-4)
   - Cualquier `data-action="X"` donde X no esté en ACTION_REGISTRY (typo)
   - Cualquier ACTION_REGISTRY entry sin call site en HTML (dead entry)

### B. Trivial migration (55 sites en 7c-1)

Migrar los onclick más simples a data-action:

```html
<!-- ANTES -->
<button onclick="dismissSplash()">Empezar</button>
<button onclick="closePelSheet()">×</button>
<button onclick="switchMainNav('mnav-cartelera')">Programa</button>
<button onclick="setAvType('hours')">Horas</button>

<!-- DESPUÉS -->
<button data-action="dismissSplash">Empezar</button>
<button data-action="closePelSheet">×</button>
<button data-action="switchMainNav" data-nav="mnav-cartelera">Programa</button>
<button data-action="setAvType" data-type="hours">Horas</button>
```

**38 sites sin args + 17 sites con string-literal arg = 55 total**.

## ACTION_REGISTRY — schema completo (87 entries, 7 categorías)

### Categoría A — Action handlers (Fase 7a) + helpers (21 entries)
```js
toggleWL, toggleWatched, togglePriority, togglePelPrio, togglePelWL,
toggleFullDay, removeBlock, addBlock, confirmAvBlock, confirmReplace,
removeFromAgenda, setDelay, clearDelay, undoDelay, checkinLaVi,
checkinNoLaVi, savePVRating, setLang, forceInclude, _dismissNotice,
swapPriority
```

### Categoría B — Sheets open/close (24 entries)
```js
openAvSheet, openAuthSheet, openFestivalSheet, openRatingSheet,
openCortoSheetFromEl, closePelSheet, closeAuthSheet, closeAvSheet,
closeConflictSheet, closeFestivalSheet, closeRatingSheet, closePVRating,
closePlanConfirm, closePrioLimit, dismissSplash, toggleSplashDropdown,
searchOpen, searchClose, _togglePastFest, _togglePastFestRow,
openPostViewRating, selectSplashFest, selectFromDetail, _openCombinedFilmSheet
```

### Categoría C — Navigation (12 entries)
```js
switchMainNav, miPlanNav, selectMiPlanDay, setProgramaMode, setProgramaChip,
setAvType, setInteresesView, toggleProgramaView, lugarToggle, seccionToggle,
selectAvDay, navTo  (composite — helper _navTo)
```

### Categoría D — Cartelera/Programa filters (8 entries)
```js
filterBySection, filterByVenue, _pafClearSec, _pafClearVenue,
_toggleEveningFilms, clearProgramaChip, runCalc, toggleArchive
```

### Categoría E — Mi Plan / Schedule (9 entries)
```js
jumpToScenario, saveCurrentScenario, removeFilmFromScenario,
setActivePlanFilm, toggleFilmAlternatives, toggleMplanProg,
sharePlan, exportICS, loadFestival
```

### Categoría F — Auth (4 entries)
```js
submitAuthEmail, submitOTP, deleteAccount, signOutAndClose
```

### Categoría G — Composite helpers nuevos (9 entries, +`navTo` ya en C)
```js
scrollToAgSec, clearExpandedFilm, setAvAddOpen, closePelAndRemove,
closePelAndRate, closeAuthAndReset, dismissToastAction, toggleCtxOlder,
toggleWatchedAndClose
```

**Total: 87 entries** (76 funciones de onclick + 11 helpers nuevos, con
`navTo` contado una vez).

## Sub-fases siguientes (no en 7c-1)

| Sub-fase | Scope | Sites |
|---|---|---|
| **7c-2** | `fn(this.dataset.X)` + wrapped `stopPropagation` | ~27 |
| **7c-3** | Multi-statement (Patrones A-J) + interpolations | ~42 |
| **7c-4** | IIFE + conditional + edge cases | ~18 |

## Decisiones de diseño incorporadas

| # | Decisión | Aplicación en 7c-1 |
|---|---|---|
| Scope | Opción A — sub-fases por complejidad | ✓ 7c-1 es foundation + trivial |
| I1 | Multi-statement onclick | Helpers definidos pero NO usados en 7c-1 (migración en 7c-3) |
| I2 | IIFE scroll handlers | Helper `_scrollToAgSection` definido. Uso en 7c-4 |
| I3 | Interpolation args | Defer a 7c-3 (con multi-statement) |
| I4 | ACTION_REGISTRY location | **Categoría A-G** visibles via comentarios. Ubicación: post-state namespace, sección dedicada "CONTROLLER LAYER" |
| I5 | Backwards compat | ✓ Coexistencia onclick + data-action funciona porque delegated listener solo activa elementos con `data-action` |
| I6 | Validate check | `[event-delegation]` WARNING — tracking + typo detection + dead entry detection |
| I7 | Test strategy | Cero tests nuevos. **R2 BYTE-IDENTICAL NO APLICA** (el DOM cambia attributes). Verificación = functional equivalence + Playwright + manual QA |
| Helpers nuevos | 11 helpers up-front | ✓ Todos definidos en 7c-1 |
| `data-close-bg` | Infra del listener | ✓ |
| `_plistPosterHtml` signature | Defer a 7c-4 (edge case) | ✓ |

## R2 ajustado para 7c (no byte-identical)

Antes (Fases 5-7a): HTML output **byte-identical** pre/post. Verificación
via DOM CRC.

Para 7c: el HTML output CAMBIA por design — `onclick="X"` → `data-action="Y"`.
Los `outerHTML` de los elementos migrados difieren.

**Nueva verificación (R2'):**
1. **Functional equivalence**: cada elemento migrado, al hacer click,
   produce el mismo state change + UI update que antes
2. **Console clean**: cero errors en consola al interactuar
3. **Playwright T01-T10 + T32**: pasan (cubren los flujos críticos)
4. **Visual diff** (manual): inspección visual de cada tab/sheet — todo
   renderiza igual

## Lo que NO entra en Fase 7c-1

| Out-of-scope | Razón | Fase |
|---|---|---|
| Migrar `fn(this.dataset.X)` y wrapped | Complejidad media | 7c-2 |
| Multi-statement (38 sites) | Patrones A-J necesitan helpers + cada uno verificado | 7c-3 |
| IIFE inline (3 sites) | Extracción a `_scrollToAgSection` (helper ya definido en 7c-1) | 7c-4 |
| Conditional onclick | Lógica dinámica | 7c-4 |
| `_plistPosterHtml` signature change | Refactor de signature change cascading | 7c-4 |
| Promote `[event-delegation]` a FAIL | Cuando 7c-4 termine | 7d/8 |

## Definition of Done

- [ ] ACTION_REGISTRY constant con 87 entries (categorías A-G), ubicado
      en sección "CONTROLLER LAYER" post-state namespace
- [ ] 11 helpers nuevos definidos con bodies funcionales
- [ ] Delegated click listener en `document` con `data-close-bg` infra
- [ ] 55 sites migrados (38 no-arg + 17 string-literal)
- [ ] Validate check `[event-delegation]` añadido nivel WARNING. Reporta:
      onclick remaining count + typos + dead entries
- [ ] `python3 validate.py` → 26/26 (25 previos + 1 nuevo)
- [ ] `node --test tests/unit/*.test.js` → 131/131
- [ ] **Functional equivalence** (R2'): click en cada uno de los 55 sites
      migrados produce el mismo comportamiento que antes
- [ ] Playwright T01-T10 + T32 verde en CI
- [ ] **QA Boot Path obligatorio** (de 6c/7a): localStorage.clear() +
      reload + invocar fns sin loadFest → 0 errors
- [ ] Coexistencia funciona — los 87 sites NO migrados aún (onclick inline)
      siguen ejecutándose normalmente
