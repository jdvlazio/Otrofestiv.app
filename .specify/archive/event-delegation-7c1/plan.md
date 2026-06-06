# Plan técnico — Fase 7c-1 (Event Delegation Foundation + Trivial Migration)

## Restricciones de partida

### R1. Single-file en producción
ACTION_REGISTRY + helpers + delegated listener viven en index.html, en
sección "CONTROLLER LAYER" post-state namespace.

### R2' Behavior equivalence (NOT byte-identical)
A diferencia de Fases 5-7a, el HTML output CAMBIA por design (`onclick`
removido, `data-action` añadido). DOM CRC pre/post **no aplica**.

**Verificación**:
1. **Functional equivalence**: click en cada elemento migrado produce el
   mismo state change + UI update
2. **Console clean**: cero errors
3. **Playwright T01-T10 + T32**: pasan
4. **Visual diff** manual

### R3. Cero cambios en signatures de funciones
Las 76 funciones invocadas mantienen sus signatures. El ACTION_REGISTRY
mapea data-* attributes a los args correctos. NO se renombran funciones.

### R4. Coexistencia obligatoria
Durante 7c-1/2/3/4, algunos sites estarán migrados (data-action) y otros
NO (onclick inline). Ambos sistemas DEBEN funcionar simultáneamente:
- Browser ejecuta onclick="..." nativamente para sites no migrados
- Delegated listener captura clicks en sites migrados (`[data-action]`)
- Cero interferencia entre ambos

### R5. Cero tests nuevos
Misma R5 de Fase 6/7a. Playwright + manual QA + QA boot path.

### R6. **QA Boot Path obligatorio** (F6 heredado)
1. localStorage.clear() + reload
2. ANTES de loadFest, invocar handlers de Tier 3 + clicks simulados
   en elementos migrados (data-action)
3. Verificar console clean

### R7. Helpers nuevos UP-FRONT
Los 11 helpers se definen en 7c-1 (foundation) aunque solo se usen en
7c-3/7c-4. Sus ACTION_REGISTRY entries son válidas desde 7c-1.

### R8. Orden de migración dentro de 7c-1
1. Foundation primero: ACTION_REGISTRY + helpers + delegated listener
2. Validate check añadido
3. Sites migrados en waves:
   - Wave 1: 38 onclick `fn()` sin args
   - Wave 2: 17 onclick `fn('literal')` con string-literal arg

## 1. Foundation — Controller Layer

### 1.1 Ubicación en index.html

```
<script>
  // ... storage namespace (5)
  // ... state namespace (5.5)
  // ── CONTROLLER LAYER START ─────────────────────
  //   - ACTION_REGISTRY (categorías A-G)
  //   - Helpers compuestos (11)
  //   - Delegated click listener + data-close-bg infra
  // ── CONTROLLER LAYER END ───────────────────────
  // ... resto del código (renders, handlers, etc.)
</script>
```

### 1.2 ACTION_REGISTRY constant

```js
// ── CONTROLLER LAYER START ────────────────────────────────────────
// ACTION_REGISTRY — mapping data-action → handler para event delegation.
// Cada entry sabe cómo extraer args del DOM element (dataset attributes).
//
// 87 entries totales (76 funciones de onclick + 11 helpers compuestos):
//   A: Action handlers (Fase 7a) + state mutators
//   B: Sheets open/close lifecycle
//   C: Navigation
//   D: Cartelera/Programa filters
//   E: Mi Plan / Schedule actions
//   F: Auth flow
//   G: Composite helpers (multi-statement patterns A-J)
//
// Usage en HTML: <button data-action="X" data-arg-1="..." data-arg-N="...">
// Si necesita stopPropagation: añadir data-stop="1" al elemento.
const ACTION_REGISTRY = {
  // ── A: Action handlers (Fase 7a) + state mutators (21) ──
  toggleWL:           (el, e) => toggleWL(el.dataset.title, e),
  toggleWatched:      (el, e) => toggleWatched(el.dataset.title, e),
  togglePriority:     (el)    => togglePriority(el.dataset.title),
  togglePelPrio:      (el)    => togglePelPrio(el.dataset.title),
  togglePelWL:        (el, e) => togglePelWL(el.dataset.title, e),
  toggleFullDay:      (el)    => toggleFullDay(el.dataset.day),
  removeBlock:        (el)    => removeBlock(el.dataset.day, el.dataset.from, el.dataset.to),
  addBlock:           (el)    => addBlock(el.dataset.day),
  confirmAvBlock:     ()      => confirmAvBlock(),
  confirmReplace:     (el)    => confirmReplace(el.dataset.rmtitle, el.dataset.newtitle, el.dataset.day, el.dataset.time),
  removeFromAgenda:   (el)    => removeFromAgenda(el.dataset.title),
  setDelay:           (el)    => setDelay(el.dataset.title, el.dataset.day, el.dataset.time, +el.dataset.mins),
  clearDelay:         (el)    => clearDelay(el.dataset.title, el.dataset.day, el.dataset.time),
  undoDelay:          (el)    => undoDelay(el.dataset.title, el.dataset.day, el.dataset.time),
  checkinLaVi:        (el)    => checkinLaVi(el.dataset.title),
  checkinNoLaVi:      (el)    => checkinNoLaVi(el.dataset.title),
  savePVRating:       ()      => savePVRating(),
  setLang:            (el)    => setLang(el.dataset.code),
  forceInclude:       (el)    => forceInclude(el.dataset.title),
  _dismissNotice:     (el)    => _dismissNotice(el.dataset.title),
  swapPriority:       (el)    => swapPriority(el.dataset.rmtitle, el.dataset.addtitle),

  // ── B: Sheets open/close (24) ──
  openAvSheet:           ()      => openAvSheet(),
  openAuthSheet:         ()      => openAuthSheet(),
  openFestivalSheet:     ()      => openFestivalSheet(),
  openRatingSheet:       (el)    => openRatingSheet(el.dataset.title),
  openCortoSheetFromEl:  (el, e) => openCortoSheetFromEl(el, e),
  closePelSheet:         ()      => closePelSheet(),
  closeAuthSheet:        ()      => closeAuthSheet(),
  closeAvSheet:          ()      => closeAvSheet(),
  closeConflictSheet:    ()      => closeConflictSheet(),
  closeFestivalSheet:    ()      => closeFestivalSheet(),
  closeRatingSheet:      ()      => closeRatingSheet(),
  closePVRating:         ()      => closePVRating(),
  closePlanConfirm:      ()      => closePlanConfirm(),
  closePrioLimit:        ()      => closePrioLimit(),
  dismissSplash:         ()      => dismissSplash(),
  toggleSplashDropdown:  ()      => toggleSplashDropdown(),
  searchOpen:            ()      => searchOpen(),
  searchClose:           ()      => searchClose(),
  _togglePastFest:       (el)    => _togglePastFest(el),
  _togglePastFestRow:    (el)    => _togglePastFestRow(el.closest('.fs-festival-row'), el.dataset.fest),
  openPostViewRating:    (el)    => openPostViewRating(el.dataset.title, el.dataset.day, el.dataset.time, el.dataset.venue, el.dataset.duration),
  selectSplashFest:      (el)    => selectSplashFest(el.dataset.name, el.dataset.meta, el.dataset.fest),
  selectFromDetail:      (el)    => selectFromDetail(el.dataset.title, el.dataset.day, el.dataset.time),
  _openCombinedFilmSheet:(el)    => _openCombinedFilmSheet(el.dataset.title),

  // ── C: Navigation (12) ──
  switchMainNav:       (el)    => switchMainNav(el.dataset.nav),
  miPlanNav:           (el)    => miPlanNav(el.dataset.dir),
  selectMiPlanDay:     (el)    => selectMiPlanDay(+el.dataset.index),
  setProgramaMode:     (el)    => setProgramaMode(el.dataset.mode),
  setProgramaChip:     (el)    => setProgramaChip(el.dataset.chip),
  setAvType:           (el)    => setAvType(el.dataset.type),
  setInteresesView:    (el)    => setInteresesView(el.dataset.mode),
  toggleProgramaView:  ()      => toggleProgramaView(),
  lugarToggle:         ()      => lugarToggle(),
  seccionToggle:       ()      => seccionToggle(),
  selectAvDay:         (el)    => selectAvDay(el.dataset.day),
  navTo:               (el)    => _navTo(el.dataset.tab),

  // ── D: Cartelera/Programa filters (8) ──
  filterBySection:     (el)    => filterBySection(el.dataset.section),
  filterByVenue:       (el)    => filterByVenue(el.dataset.venue),
  _pafClearSec:        ()      => _pafClearSec(),
  _pafClearVenue:      ()      => _pafClearVenue(),
  _toggleEveningFilms: ()      => _toggleEveningFilms(),
  clearProgramaChip:   ()      => clearProgramaChip(),
  runCalc:             ()      => runCalc(),
  toggleArchive:       ()      => toggleArchive(),

  // ── E: Mi Plan / Schedule actions (9) ──
  jumpToScenario:        (el)    => jumpToScenario(+el.dataset.index),
  saveCurrentScenario:   ()      => saveCurrentScenario(),
  removeFilmFromScenario:(el)    => removeFilmFromScenario(el.dataset.title),
  setActivePlanFilm:     (el)    => setActivePlanFilm(el),
  toggleFilmAlternatives:(el)    => toggleFilmAlternatives(el.dataset.key, el.dataset.title, el.dataset.day, el.dataset.time),
  toggleMplanProg:       (el, e) => toggleMplanProg(el, e),
  sharePlan:             ()      => sharePlan(),
  exportICS:             ()      => exportICS(),
  loadFestival:          (el)    => loadFestival(el.dataset.fest),

  // ── F: Auth (4) ──
  submitAuthEmail:  ()    => submitAuthEmail(),
  submitOTP:        ()    => submitOTP(),
  deleteAccount:    ()    => deleteAccount(),
  signOutAndClose:  ()    => signOutAndClose(),

  // ── G: Composite helpers (Patrones A-J) (9) ──
  scrollToAgSec:    (el)    => _scrollToAgSection(el.dataset.target),
  clearExpandedFilm:()      => _setExpandedFilm(''),
  setAvAddOpen:     (el)    => _setAvAddOpen(el.dataset.day, el.dataset.open === '1'),
  closePelAndRemove:(el)    => _closePelAndRemove(el.dataset.title),
  closePelAndRate:  (el)    => _closePelAndRate(el.dataset.title),
  closeAuthAndReset:()      => _closeAuthAndReset(),
  dismissToastAction:()     => _dismissToastAction(),
  toggleCtxOlder:   ()      => _toggleCtxOlder(),
  toggleWatchedAndClose:(el, e) => _toggleWatchedAndClose(el.dataset.title, e),
  toggleWLAndClose: (el, e) => _toggleWLAndClose(el.dataset.title, e),
};
```

### 1.3 Helpers compuestos (11)

```js
// ── Composite helpers (consumed por ACTION_REGISTRY G + 7c-3/4 sites) ──

function _scrollToAgSection(id) {
  const el = document.getElementById(id);
  if (!el) return;
  const hdr = document.getElementById('hdr-ag');
  const off = hdr ? hdr.getBoundingClientRect().bottom : 0;
  const y = el.getBoundingClientRect().top + window.scrollY - off - 8;
  window.scrollTo({top: y, behavior: 'smooth'});
}

function _setExpandedFilm(val) {
  _expandedFilm = val;
  renderAgenda();
}

function _setAvAddOpen(day, val) {
  avAddOpen[day] = val;
  renderAvDay(day);
}

function _closePelAndRemove(title) {
  closePelSheet();
  removeFromAgenda(title);
}

function _closePelAndRate(title) {
  closePelSheet();
  setTimeout(() => openRatingSheet(title), 100);
}

function _navTo(tab) {
  if (tab === 'mnav-cartelera') {
    const _ph = _getProgramaPhase();
    programaSubMode = _ph.default;
    switchMainNav(tab);
    showDayView();
  } else {
    switchMainNav(tab);
    showAgView();
  }
}

function _closeAuthAndReset() {
  closeAuthSheet();
  const step1 = document.getElementById('auth-sheet-step1');
  const step2 = document.getElementById('auth-sheet-step2');
  if (step1) step1.style.display = 'block';
  if (step2) step2.style.display = 'none';
}

function _dismissToastAction() {
  if (_toastActionFn) {
    _toastActionFn();
    _toastActionFn = null;
    showToast('', 'info', 100);
  }
}

function _toggleCtxOlder() {
  const el = document.getElementById('ctx-older');
  if (!el) return;
  el.style.display = el.style.display === 'none' ? 'block' : 'none';
}

function _toggleWatchedAndClose(title, e) {
  toggleWatched(title, e);
  closePelSheet();
}

function _toggleWLAndClose(title, e) {
  toggleWL(title, e);
  closePelSheet();
}
```

### 1.4 Delegated click listener + `data-close-bg` infra

```js
// ── Delegated click listener — captura cualquier click con data-action ──
//
// Patron data-stop="1": llama event.stopPropagation() ANTES del handler
// Patron data-close-bg="X": si click directo en este elemento (no en hijo),
//   dispara closeXSheet(). Para overlays click-to-close.
document.addEventListener('click', function(e) {
  const target = e.target.closest('[data-action]');
  if (target) {
    if (target.dataset.stop === '1') e.stopPropagation();
    const handler = ACTION_REGISTRY[target.dataset.action];
    if (handler) handler(target, e);
    return;
  }
  // close-on-background-click: solo si click directo en el overlay
  const bg = e.target.closest('[data-close-bg]');
  if (bg && e.target === bg) {
    const closeName = 'close' + bg.dataset.closeBg;
    const closeFn = ACTION_REGISTRY[closeName];
    if (closeFn) closeFn();
  }
});
// ── CONTROLLER LAYER END ──────────────────────────────────────────
```

## 2. Trivial migration (55 sites)

### 2.1 Wave 1 — 38 sites `fn()` sin args

Patrón mechanico: `onclick="X()"` → `data-action="X"`.

Sites afectados (sample — verificación exhaustiva en paso 3):
- `closePelSheet()`, `closeAuthSheet()` × varios
- `dismissSplash()`, `toggleSplashDropdown()`
- `openAvSheet()`, `openFestivalSheet()`, `searchOpen()`, `searchClose()`
- `confirmAvBlock()`, `savePVRating()`
- `clearProgramaChip()`, `_pafClearSec()`, `_pafClearVenue()`, `_toggleEveningFilms()`
- `lugarToggle()`, `seccionToggle()`, `toggleProgramaView()`
- `runCalc()`, `saveCurrentScenario()`, `toggleArchive()`
- `sharePlan()`, `exportICS()`
- `submitAuthEmail()`, `submitOTP()`, `deleteAccount()`, `signOutAndClose()`
- `closePVRating()`, `closePlanConfirm()`, `closePrioLimit()`

### 2.2 Wave 2 — 17 sites `fn('literal')` con string-literal arg

Patrón: `onclick="X('value')"` → `data-action="X" data-<argname>="value"`.

Sites afectados:
- `switchMainNav('mnav-cartelera')` × 4 → `data-action="switchMainNav" data-nav="mnav-cartelera"`
- `setAvType('hours')`, `setAvType('full')` → `data-action="setAvType" data-type="hours"`
- `setProgramaMode('hoy')`, `setProgramaMode('manana')` → `data-mode="hoy"`
- `setInteresesView('grid')`, `setInteresesView('list')` → `data-mode="grid"`
- `setProgramaChip('all')` → `data-chip="all"`
- `setLang('es')`, `setLang('en')` → `data-code="es"`
- `selectAvDay('Martes')` × 6 → `data-day="Martes"`

## 3. Validate check `[event-delegation]`

```python
check = 'event-delegation'

# Count onclick remaining
onclick_count = content.count('onclick="')

# Detect typos: any data-action="X" must exist in ACTION_REGISTRY
# Parse ACTION_REGISTRY block from index.html
registry_block = content[content.find('const ACTION_REGISTRY'):content.find('};', content.find('const ACTION_REGISTRY')) + 2]
registry_keys = re.findall(r'^\s+([_a-zA-Z][_a-zA-Z0-9]*):\s*\(', registry_block, re.M)

# Find all data-action values used in HTML
used_actions = set(re.findall(r'data-action="([^"]+)"', content))

# Typo detection
typos = used_actions - set(registry_keys)
if typos:
    for typo in typos:
        warn(check, f'data-action="{typo}" usado en HTML pero NO existe en ACTION_REGISTRY')

# Dead entry detection (in 7c-1 esperable que muchos sean dead — solo 55 sites migrados)
dead = set(registry_keys) - used_actions
# Solo flag los helpers nuevos (composite) si están dead — los registry entries
# de funciones existentes pueden estar dead porque sus sites no se han migrado aún
composite_helpers = {'scrollToAgSec', 'clearExpandedFilm', 'setAvAddOpen',
                     'closePelAndRemove', 'closePelAndRate', 'navTo',
                     'closeAuthAndReset', 'dismissToastAction',
                     'toggleCtxOlder', 'toggleWatchedAndClose', 'toggleWLAndClose'}
dead_composites_in_7c1 = dead & composite_helpers  # esperado dead en 7c-1
# No flag — son helpers up-front

# Reporting
ok(check, f'Migration progress: onclick={onclick_count} remaining, '
          f'{len(used_actions)} unique data-actions used, '
          f'{len(registry_keys)} entries in ACTION_REGISTRY, '
          f'{len(dead - composite_helpers)} non-helper dead entries')
```

**Promote a FAIL en 7c-4** cuando onclick_count === 0.

## 4. Test strategy

### 4.1 R2' Functional equivalence

Click cada uno de los 55 sites migrados → verificar comportamiento idéntico:
- Buttons sin args: comportamiento click → mismo state/UI change
- Buttons con string literal: arg correcto pasado al handler

### 4.2 QA Boot Path obligatorio (heredado de 6c/7a)

```
1. localStorage.clear() + reload
2. ANTES de loadFest:
   - showAgView(); render(); _renderProgramaContent();
   - Simular click en algunos elementos migrados (e.g., dismissSplash)
3. Verificar console.errors === []
```

### 4.3 QA flow normal

- Sheets open/close: click "×" cierra sheet correctamente
- Nav: click tabs cambia view
- Search: open/close funcional
- Sub-modal closes

### 4.4 Playwright

T01-T10 + T32 cubren los flujos principales. No se añaden nuevos.

## 5. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Typo en data-action attribute (typo no atrapado por validate hasta correr) | Validate check `[event-delegation]` detecta data-action no-en-registry |
| Coexistencia onclick + delegated listener: ambos disparan handler doble | Imposible por design — onclick activa antes de bubble al document. Si el elemento tiene AMBOS, el data-action pierde (browser ejecuta onclick directo y no propaga). Verificar que NO existan ambos en el mismo elemento |
| Helper compuesto sin call site en 7c-1 (dead until 7c-3) | Aceptado — son foundation. Validate check tolera composite helpers dead |
| `_togglePastFestRow` requiere `el.closest('.fs-festival-row')` en lugar del `el` directo (signature de el original era `_togglePastFestRow(this.closest('.fs-festival-row'),'${id}')`) | Documentado en registry entry. Argument extraction lo handlea |
| Algunos sites tienen `data-X` attributes pre-existentes (`data-title`, `data-fest`) que ya se leían desde onclick. Tras migración, el handler los lee del dataset igual | OK — los data-* attributes coexisten con data-action |
| Splash overlay tiene multiples onclick: `dismissSplash`, `selectSplashFest`. Cada uno migra a su propio data-action | OK — split por target element |
| Algunos onclick complejos NO entran en 7c-1 (Wave 1/2) pero su FUNCIÓN está en el registry. ej. `closePelSheet` se invoca también desde multi-statement `closePelSheet();removeFromAgenda(...)`. El multi-statement migra en 7c-3 | OK — registry entry funciona desde 7c-1 |

## 6. Tamaño estimado

| Concepto | Líneas |
|---|---|
| ACTION_REGISTRY (87 entries + comentarios) | ~120 |
| 11 helpers compuestos | ~80 |
| Delegated listener + data-close-bg infra | ~25 |
| Validate check `[event-delegation]` | ~50 |
| 55 sites migrados en HTML (mass replace) | ~55 líneas tocadas |
| **Total** | **~330 LOC** |

Magnitud similar a 6b/6c. Single PR.

## 7. Orden de validación pre-commit

1. **QA Boot Path obligatorio** (R6)
2. `python3 validate.py` → 26/26 (con nuevo `[event-delegation]`)
3. `node --test tests/unit/*.test.js` → 131/131
4. JS syntax (validate.py `[js-syntax]`)
5. **Functional equivalence** (R2') — click manual en 55 sites migrados
6. Playwright T01-T10 + T32 verde en CI
7. Diff review
8. `node scripts/bump-version.js`
9. Commit + push + PR
