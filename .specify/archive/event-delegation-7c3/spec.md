# Spec — Event Delegation Wave 3: Multi-statement + interpolations (Fase 7c-3)

## Problema

Tras 7c-2 quedan **71 onclick inline** (en ocurrencias) en `index.html`. De
ellos, **55 sitios** caen en patrones de multi-statement o interpolación pura
migrables vía el sistema `data-action` + ACTION_REGISTRY ya establecido en
7c-1/2.

Los 16 restantes (IIFE, conditional, JSON-parse, overlay-close, DOM-direct,
edge cases) quedan para **7c-4**.

Sub-tipos de complejidad en 7c-3:

1. **Single fn con interpolación**: `fn('${var1}','${var2}')` — args pasan vía
   `data-*` attributes filled at template-time
2. **Multi-statement con composite helpers existentes**: `_navTo`,
   `_closePelAndRate`, `_closePelAndRemove`, `_toggleWatchedAndClose`,
   `_toggleCtxOlder`, `_dismissToastAction`, `_closeAuthAndReset`,
   `_setAvAddOpen`, `clearExpandedFilm`
3. **Multi-statement requiriendo NUEVO helper**: `_activatePlanFilm`
4. **Signature bugs latentes**: 2 entries con args mal mapeados
   (`closePlanConfirm`, `_toggleEveningFilms`)
5. **Handler missing**: `addSuggestion` no estaba en ACTION_REGISTRY

**Pattern H (2 sitios `event.stopPropagation()` solo) DIFERIDO a 7c-4** — análisis profundo durante planificación reveló que requiere rewrite del walking-up del listener (de `closest()` a loop manual con stop detection), no "1 línea". Defer evita riesgo de regresión sobre 127+ sites delegated.

## Causa raíz

Mismo crecimiento orgánico que 7c-1/2. Los handlers multi-statement se
escribieron inline como secuencias cortas porque crear un helper para 1-3
líneas parecía exagerado. La acumulación generó:

- Patrones repetidos (`closePelSheet();setTimeout(()=>openRatingSheet(),100)`
  aparece 3 veces)
- Acoplamiento template ↔ JS difícil de testear
- Imposibilita CSP estricto (objetivo final de 7d)

Los composite helpers ya fueron definidos up-front en 7c-1 como decisión
arquitectónica (I1 del spec 7c-1). 7c-3 los **activa** consumiéndolos en los
call sites.

## Solución

### A. Listener — sin cambios

D1=B confirmado: Pattern H se difiere a 7c-4 junto con el rewrite del
walking-up. Listener intacto en 7c-3.

### B. ACTION_REGISTRY edits (4 cambios)

#### B.1 — Fix `closePlanConfirm` entry (Cat B, bug latente)

```js
// ANTES (bug — no pasa force):
closePlanConfirm:      ()      => closePlanConfirm(),

// DESPUÉS:
closePlanConfirm:      (el)    => closePlanConfirm(el.dataset.force === '1'),
```

Sitio afectado: L2710 `<button class="plan-confirm-cta" ... onclick="closePlanConfirm(true)">`. Migra como `data-action="closePlanConfirm" data-force="1"`.

#### B.2 — Fix `_toggleEveningFilms` entry (Cat D, bug latente)

```js
// ANTES (no pasa btn):
_toggleEveningFilms: ()      => _toggleEveningFilms(),

// DESPUÉS:
_toggleEveningFilms: (el)    => _toggleEveningFilms(el),
```

Sitio L7687 `<button class="link-gray-xs" onclick="_toggleEveningFilms(this)">`.

#### B.3 — Add `addSuggestion` entry (Cat D — filters/list)

```js
addSuggestion: (el) => addSuggestion(el.dataset.title, el.dataset.day, el.dataset.time),
```

Sitio L7834.

#### B.4 — Add `activatePlanFilm` entry (Cat G — composite helpers)

```js
activatePlanFilm: (el) => _activatePlanFilm(el),
```

Consume el nuevo helper (sección C).

### C. Nuevo helper compuesto `_activatePlanFilm` (Cat G)

```js
function _activatePlanFilm(el) {
  setActivePlanFilm(el);
  const i = parseInt(el.dataset.dayIndex, 10);
  if (!isNaN(i)) selectMiPlanDay(i);
}
```

Sitio único: L5385 — `mplan-wk-block` (bloque visual en calendario semanal Mi
Plan). El handler original: `setActivePlanFilm(this);selectMiPlanDay(${i});event.stopPropagation()`.

Helper sigue el patrón canónico de Cat G (todos prefijados con `_`).

### D. Migración de 55 call sites por pattern

Detalle en `plan.md` — agrupados por pattern de comportamiento:

| Pattern | Sites | Helper/Action |
|---|---|---|
| A — Single fn interp | 28 | Registry existing entries + data-* attrs |
| B — `_navTo` | 4 | navTo (Cat C) |
| Q — `_navTo` cartelera | 1 | navTo (la branch ya existe en _navTo) |
| C — `_closePelAndRate` | 3 | closePelAndRate (Cat G) |
| D — `_closePelAndRemove` | 1 | closePelAndRemove (Cat G) |
| E — `_toggleWatchedAndClose` | 1 | toggleWatchedAndClose (Cat G) |
| F — Single fn left-over | 3 | clearExpandedFilm, closePlanConfirm (fixed), _toggleEveningFilms (fixed) |
| I — Checkin interp | 4 | checkinLaVi, checkinNoLaVi (Cat A) |
| J — `_toggleCtxOlder` | 1 | toggleCtxOlder (Cat G) |
| K — `_dismissToastAction` | 1 | dismissToastAction (Cat G) |
| L — `_closeAuthAndReset` | 1 | closeAuthAndReset (Cat G) |
| M — `toggleFilmAlternatives` interp + stop | 2 | toggleFilmAlternatives (Cat E) + data-stop |
| G — `_activatePlanFilm` NEW | 1 | activatePlanFilm (Cat G new) |
| AV — `_setAvAddOpen` | 2 | setAvAddOpen (Cat G) |
| ~~H~~ — stopPropagation alone | ~~2~~ | **DIFERIDO a 7c-4** |

**Total: 53 sites**

## Inventario completo de los 55 sites

### Pattern A — Single fn con interpolación (28 sites)

| # | Línea | onclick | Atributos resultantes |
|---|---|---|---|
| 1 | 5327 | `miPlanNav(-1)` | `data-action="miPlanNav" data-dir="-1"` |
| 2 | 5342 | `miPlanNav(1)` | `data-action="miPlanNav" data-dir="1"` |
| 3 | 5330 | `selectMiPlanDay(${vs})` | `data-action="selectMiPlanDay" data-index="${vs}"` |
| 4 | 5335 | `selectMiPlanDay(${ve})` | `data-action="selectMiPlanDay" data-index="${ve}"` |
| 5 | 5394 | `selectMiPlanDay(${i})` | `data-action="selectMiPlanDay" data-index="${i}"` |
| 6 | 6117 | `addBlock('${day}')` | `data-action="addBlock" data-day="${day}"` |
| 7 | 6131 | `toggleFullDay('${day}')` | `data-action="toggleFullDay" data-day="${day}"` |
| 8 | 6260 | `toggleFullDay('${day}')` | same |
| 9 | 6267 | `removeBlock('${day}','${b.from}','${b.to}')` | `data-action="removeBlock" data-day data-from data-to` |
| 10 | 6109 | `removeBlock(...);event.stopPropagation()` | + `data-stop="1"` |
| 11 | 7273 | `confirmReplace('${safeT}','${safeTNew}','${f.day}','${f.time}')` | `data-action="confirmReplace" data-rmtitle data-newtitle data-day data-time` |
| 12 | 7569 | `setDelay('${safeT}','${next.day}','${next.time}',${m})` | `data-action="setDelay" data-title data-day data-time data-mins` |
| 13 | 7594 | `setDelay(...)` (duplicate) | same |
| 14 | 7570 | `undoDelay('${safeT}','${next.day}','${next.time}')` | `data-action="undoDelay" data-title data-day data-time` |
| 15 | 7571 | `clearDelay('${safeT}','${next.day}','${next.time}')` | `data-action="clearDelay" data-title data-day data-time` |
| 16 | 8329 | `jumpToScenario(${di})` | `data-action="jumpToScenario" data-index="${di}"` |
| 17 | 8402 | `forceInclude('${safeT}');event.stopPropagation()` | `data-action="forceInclude" data-title data-stop="1"` |
| 18 | 8762 | `swapPriority('${safeSwap}','${safeNew}')` | `data-action="swapPriority" data-rmtitle data-addtitle` |
| 19 | 10287 | `setProgramaChip('${chip.id}')` | `data-action="setProgramaChip" data-chip="${chip.id}"` |
| 20 | 10355 | `_dismissNotice('${n.title.replace(...)}')` | `data-action="_dismissNotice" data-title` |
| 21 | 10833 | `selectSplashFest('${cfg.name}','${meta}','${id}')` | `data-action="selectSplashFest" data-name data-meta data-fest` |
| 22 | 10840 | `_togglePastFest(this,'${cfg.name}','${meta}','${id}')` | `data-action="_togglePastFest"` (dead args omitidos) |
| 23 | 10895 | `loadFestival('${id}')` | `data-action="loadFestival" data-fest="${id}"` |
| 24 | 10909 | `loadFestival('${id}')` | same |
| 25 | 10913 | `_togglePastFestRow(this.closest(...),'${id}')` | `data-action="_togglePastFestRow" data-fest="${id}"` |
| 26 | 7484 | `event.stopPropagation();openPostViewRating('${safeT}','','','','')` | `data-action="openPostViewRating" data-title data-stop="1"` (atributos opcionales vacíos = `undefined` en dataset → función handles) |
| 27 | 7678 | `event.stopPropagation();openPostViewRating('${safeT}','${s.day||''}','${s.time||''}','${(s.venue||'').replace(...)}','${s.duration||''}')` | 5 data-* + data-stop |
| 28 | 7834 | `event.stopPropagation();addSuggestion('${f.title.replace(...)}','${f.day}','${f.time}')` | `data-action="addSuggestion" data-title data-day data-time data-stop="1"` |

### Pattern B — `_navTo` composite (4 sites)

| # | Línea | onclick | Atributos |
|---|---|---|---|
| 29 | 2596 | `switchMainNav('mnav-seleccion');showAgView()` | `data-action="navTo" data-tab="mnav-seleccion"` |
| 30 | 2600 | `switchMainNav('mnav-planner');showAgView()` | `data-action="navTo" data-tab="mnav-planner"` |
| 31 | 2604 | `switchMainNav('mnav-miplan');showAgView()` | `data-action="navTo" data-tab="mnav-miplan"` |
| 32 | 7753 | `switchMainNav('mnav-planner');showAgView()` | `data-action="navTo" data-tab="mnav-planner"` (cta-ctx-b) |

### Pattern Q — `_navTo` cartelera branch (1 site)

| # | Línea | onclick | Atributos |
|---|---|---|---|
| 33 | 2592 | `{const _ph=_getProgramaPhase();programaSubMode=_ph.default;switchMainNav('mnav-cartelera');showDayView();}` | `data-action="navTo" data-tab="mnav-cartelera"` (la branch cartelera del helper `_navTo` ya hace exactamente esto) |

### Pattern C — `_closePelAndRate` (3 sites)

| # | Línea | onclick | Atributos |
|---|---|---|---|
| 34 | 9736 | `event.stopPropagation();closePelSheet();setTimeout(()=>openRatingSheet(this.dataset.title),100)` | `data-action="closePelAndRate" data-title data-stop="1"` |
| 35 | 9783 | `closePelSheet();setTimeout(()=>openRatingSheet(this.dataset.title),100)` | `data-action="closePelAndRate" data-title` |
| 36 | 10096 | `closePelSheet();setTimeout(()=>openRatingSheet(this.dataset.title),100)` | same |

### Pattern D — `_closePelAndRemove` (1 site)

| # | Línea | onclick | Atributos |
|---|---|---|---|
| 37 | 9790 | `closePelSheet();removeFromAgenda(this.dataset.title)` | `data-action="closePelAndRemove" data-title` |

### Pattern E — `_toggleWatchedAndClose` (1 site)

| # | Línea | onclick | Atributos |
|---|---|---|---|
| 38 | 9782 | `toggleWatched(this.dataset.title,event);closePelSheet()` | `data-action="toggleWatchedAndClose" data-title` |

### Pattern J — `_toggleCtxOlder` (1 site)

| # | Línea | onclick | Atributos |
|---|---|---|---|
| 39 | 7220 | `const el=document.getElementById('ctx-older');el.style.display=...` | `data-action="toggleCtxOlder"` |

### Pattern K — `_dismissToastAction` (1 site)

| # | Línea | onclick | Atributos |
|---|---|---|---|
| 40 | 8485 | `if(_toastActionFn){_toastActionFn();_toastActionFn=null;showToast('','info',100)}` | `data-action="dismissToastAction"` |

### Pattern L — `_closeAuthAndReset` (1 site)

| # | Línea | onclick | Atributos |
|---|---|---|---|
| 41 | 12118 | `closeAuthSheet();...display='block';...display='none'` | `data-action="closeAuthAndReset"` |

### Pattern F — Single fn left-over (3 sites con 2 entry fixes)

| # | Línea | onclick | Atributos | Entry fix? |
|---|---|---|---|---|
| 42 | 2710 | `closePlanConfirm(true)` | `data-action="closePlanConfirm" data-force="1"` | **B.1 fix** |
| 43 | 7286 | `_expandedFilm='';renderAgenda()` | `data-action="clearExpandedFilm"` | ✓ existing |
| 44 | 7687 | `_toggleEveningFilms(this)` | `data-action="_toggleEveningFilms"` | **B.2 fix** |

### Pattern I — Checkin interpolation (4 sites)

| # | Línea | onclick | Atributos |
|---|---|---|---|
| 45 | 7214a | `checkinLaVi('${st}')` | `data-action="checkinLaVi" data-title="${st}"` |
| 46 | 7214b | `checkinNoLaVi('${st}')` | `data-action="checkinNoLaVi" data-title="${st}"` |
| 47 | 7229 | `checkinLaVi('${safeLast}')` | `data-action="checkinLaVi" data-title` |
| 48 | 7230 | `checkinNoLaVi('${safeLast}')` | `data-action="checkinNoLaVi" data-title` |

### Pattern M — `toggleFilmAlternatives` + stop (2 sites)

| # | Línea | onclick | Atributos |
|---|---|---|---|
| 49 | 5457 | `toggleFilmAlternatives('${...}','${safeT}','${s.day||''}','${s.time||''}');event.stopPropagation()` | `data-action="toggleFilmAlternatives" data-key data-title data-day data-time data-stop="1"` |
| 50 | 7040 | same shape | same |

### Pattern G — `_activatePlanFilm` NEW helper (1 site)

| # | Línea | onclick | Atributos |
|---|---|---|---|
| 51 | 5385 | `setActivePlanFilm(this);selectMiPlanDay(${i});event.stopPropagation()` | `data-action="activatePlanFilm" data-day-index="${i}" data-stop="1"` |

### Pattern AV — `_setAvAddOpen` (2 sites)

| # | Línea | onclick | Atributos |
|---|---|---|---|
| 52 | 6118 | `avAddOpen['${day}']=false;renderAvDay('${day}')` | `data-action="setAvAddOpen" data-day data-open="0"` |
| 53 | 6130 | `avAddOpen['${day}']=true;renderAvDay('${day}')` | `data-action="setAvAddOpen" data-day data-open="1"` |

### Pattern H — DIFERIDO a 7c-4

L5453 (`js-open-pel` wrapper) y L5456 (`mplan-tc` cell) requieren rewrite del
walking-up del listener (riesgo sobre 127+ sites). Diferido a 7c-4 junto con
otros edge cases que requieren rediseño arquitectónico.

**Total 7c-3: 53 sites**

## Sub-fases siguientes (no en 7c-3)

| Sub-fase | Scope | Sites |
|---|---|---|
| **7c-4** | IIFE, conditional, JSON-parse, overlay-close, DOM-direct, edge cases | 16 |
| **7d/8** | Promote check `[event-delegation]` a FAIL | — |

## Decisiones de diseño incorporadas

| # | Decisión | Aplicación en 7c-3 |
|---|---|---|
| D1 | Pattern H (stopPropagation alone) | **Opción B (re-decidida)** — defer a 7c-4 con rewrite arquitectónico del walking-up. Listener intacto en 7c-3. |
| D2 | Signature fixes en ACTION_REGISTRY | **2 fixes**: closePlanConfirm, _toggleEveningFilms. (`_togglePastFest` verificado: dead args, no requiere fix) |
| D3 | Pattern G helper nuevo | **`_activatePlanFilm`** + entry `activatePlanFilm` en Cat G |
| D4 | `addSuggestion` entry | **Añadir** en Cat D (filters/list helpers) |
| D5 | js-open-pel coexistence | Consecuencia de D1=A — wrapper divs siguen funcionando |
| D6 | Pattern N (_openCombinedFilmSheet) | **Defer a 7c-4** (JSON.parse + signature change merece análisis dedicado) |
| Inherited 7c-1 | Composite helpers up-front | ✓ Activados los que tenían consumer en 7c-3 |
| Inherited 7c-2 | data-stop="1" infra | ✓ Reusada + extendida (D1) |

## R2' (functional equivalence — heredado 7c-1/2)

Mismo enfoque. HTML output cambia por design (onclick → data-action + data-*).
Verificación:

1. **Functional equivalence** por pattern: cada categoría verificada via QA boot
   path o browser eval
2. **Console clean**: 0 errors al interactuar con cualquiera de los 55 sites
3. **Playwright T01-T10 + T32** verde en CI
4. **Risk pattern Q (cartelera tab)**: el helper `_navTo` debe replicar
   exactamente la secuencia `_getProgramaPhase + programaSubMode = default +
   switchMainNav + showDayView`. Verificar diff de comportamiento via inspección
   del helper.
5. **Risk pattern H (wrapper div)**: verificar que clicks en
   `mplan-tc` y `js-open-pel` wrappers no triggerean handlers ancestros
   (selectFromDetail / openPelSheet).

## Lo que NO entra en Fase 7c-3

| Out-of-scope | Razón | Fase |
|---|---|---|
| IIFE scroll (L2570/2573/2576) | Helper `_scrollToAgSection` existe pero scope IIFE | 7c-4 |
| Overlay close (L2473, L12102) | Migración a `data-close-bg` | 7c-4 |
| Conditional onclick (L7053) | `${isDone?fnA:fnB}` lógica dinámica | 7c-4 |
| Dynamic `${ctaOnclick}` (L5952) | Substitución de string en template | 7c-4 |
| JSON-parse Pattern N (L9692/93/95/96) | Args parsed-from-dataset, bug latente registry | 7c-4 |
| DOM-direct `.remove()` (L7309) | Necesita nuevo helper o anti-pattern review | 7c-4 |
| scrollIntoView ad-hoc (L5415) | Necesita nuevo helper | 7c-4 |
| Back-to-top (L12147) | Singleton edge case | 7c-4 |
| JS-gen onclick strings (L4458, L11907) | No son call sites, son template literals en JS | 7d/8 (cleanup) |
| Promote `[event-delegation]` a FAIL | Post-7c-4 | 7d/8 |

## Definition of Done

- [ ] **Verificación bloqueante PRE**: confirmar que las 2 entries a fixear
      (`closePlanConfirm`, `_toggleEveningFilms`) **NO están siendo invocadas
      via delegated path actualmente** (call sites tienen onclick inline, no
      data-action). Si lo están, escalar antes de modificar.
- [ ] Listener intacto (D1=B, Pattern H diferido a 7c-4)
- [ ] ACTION_REGISTRY tiene **91 entries**:
      - `closePlanConfirm` fixed
      - `_toggleEveningFilms` fixed
      - `addSuggestion` añadida en Cat D
      - `activatePlanFilm` añadida en Cat G
- [ ] Helper `_activatePlanFilm` definido
- [ ] **53 sites migrados** (28 A + 4 B + 1 Q + 3 C + 1 D + 1 E + 1 J + 1 K +
      1 L + 3 F + 4 I + 2 M + 1 G + 2 AV)
- [ ] `python3 validate.py` → **26/26**
- [ ] `node --test tests/unit/*.test.js` → 131/131
- [ ] JS syntax check OK
- [ ] **Functional equivalence R2'** por pattern (especialmente Q y H)
- [ ] Playwright T01-T10 + T32 verde en CI
- [ ] **QA Boot Path obligatorio**: 0 errors
- [ ] Coexistencia funciona — los 16 sites NO migrados aún (7c-4) siguen
      ejecutándose normalmente
