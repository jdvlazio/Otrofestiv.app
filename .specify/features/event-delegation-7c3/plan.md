# Plan — Event Delegation Wave 3 (Fase 7c-3)

## Restricciones

**R1. Cambios quirúrgicos** — solo:
- 1 verificación bloqueante PRE (registry path para 2 entries con fix pendiente)
- 1 nuevo helper compuesto (`_activatePlanFilm`) + 1 entry Cat G
- 2 entry fixes (`closePlanConfirm`, `_toggleEveningFilms`)
- 1 entry nueva (`addSuggestion` en Cat D)
- 53 migraciones de call site
- **Listener intacto** (D1=B: Pattern H diferido a 7c-4)

Cero cambios en signatures de funciones de dominio, validate.py, o helpers
existentes.

**R2' (functional equivalence — heredado 7c-1/2)**. HTML cambia por design.
Verificación funcional + Playwright + manual QA.

**R3. Verificación PRE bloqueante** de que las entries con fix
(`closePlanConfirm`, `_toggleEveningFilms`) no estén siendo invocadas vía
delegated path actualmente. Si lo están, escalar antes de tocar.

**R4. Coexistencia onclick + data-action.** Tras 7c-3:
- 18 sitios con onclick inline (no migrados — scope 7c-4, incluye los 2 Pattern H) siguen funcionales
- 72 + 53 = 125 sitios con data-action gestionados por delegated listener

**R5. Cero cambios en signatures de funciones de dominio.** Las funciones
invocadas NO se modifican. Los entry fixes solo cambian cómo el registry
extrae args del DOM.

**R6. QA Boot Path obligatorio** post-migración. Heredado de 6c/7a/7c-1/7c-2.

**R7. bump-version + commit atómico** al cierre.

**R8. Validate check `[event-delegation]`** sigue nivel WARNING. Promoción a
FAIL pospuesta a 7d (post-7c-4).

## Alcance detallado

### Fase 0 — Verificación PRE bloqueante (R3)

**Objetivo**: confirmar que los 2 entries con fix pendiente
(`closePlanConfirm`, `_toggleEveningFilms`) **NO** están siendo invocados via
delegated path en la versión actual.

**Comando:**
```bash
grep -nE 'data-action="(closePlanConfirm|_toggleEveningFilms)"' index.html
```

**Decisión gate:**
- 0 matches → **GO** — las entries bugueadas no causan harm hoy. Fix incluido
  en 7c-3 es safe.
- ≥1 match → **STOP** — algún call site YA usa data-action con la entry
  bugueada. Significa que el bug está activo en producción (cero arg pasado
  cuando debería ser true/btn). Escalar al usuario antes de proceder.

Razón: misma lógica que el bug latente de `selectFromDetail` en 7c-2 — fix
seguro mientras no haya consumer del path delegated.

### Fase 1 — Helper nuevo `_activatePlanFilm` (D3)

Insertar después de `_toggleWLAndClose` (L3082 aprox):

```js
function _activatePlanFilm(el) {
  setActivePlanFilm(el);
  const i = parseInt(el.dataset.dayIndex, 10);
  if (!isNaN(i)) selectMiPlanDay(i);
}
```

Convención de naming: prefijo `_` (igual que los otros 11 helpers Cat G).

### Fase 2 — ACTION_REGISTRY edits (4 cambios)

**Edit 1 — Fix `closePlanConfirm`** (Cat B):
```js
// L3131 aprox
closePlanConfirm:      (el)    => closePlanConfirm(el.dataset.force === '1'),
```

**Edit 2 — Fix `_toggleEveningFilms`** (Cat D):
```js
// L3163 aprox
_toggleEveningFilms: (el)    => _toggleEveningFilms(el),
```

**Edit 3 — Add `addSuggestion`** (Cat D):
```js
addSuggestion:       (el)    => addSuggestion(el.dataset.title, el.dataset.day, el.dataset.time),
```

**Edit 4 — Add `activatePlanFilm`** (Cat G):
```js
activatePlanFilm:    (el)    => _activatePlanFilm(el),
```

**Total post-edit:** 89 + 2 (addSuggestion, activatePlanFilm) = **91 entries**.

Actualizar comentarios header del registry:
- "89 entries categorías A-G" → "91 entries categorías A-G"
- "// ── D: Cartelera/Programa filters (9) ──" → "(10)" — añade addSuggestion
- "// ── G: Composite helpers (Patrones A-J multi-statement) (10) ──" → "(11)"

### Fase 3 — Migración de 53 sites por wave

Las waves se organizan por **paridad de riesgo** (low → high):

#### Wave 1 — Pattern A (interpolación pura, 28 sites)

Estructura uniforme. Cada uno: añadir `data-X` attributes + `data-action` +
opcional `data-stop="1"`. Sin helpers nuevos, sin entry fixes.

Sitios listados en spec.md sección "Pattern A". Migración en bloque
manual (cada sitio único — interpolaciones específicas por contexto).

#### Wave 2 — Patterns B + Q (navTo composite, 5 sites)

Todos los main-nav-tab + cta-ctx-b. Helper `_navTo` ya existe.

#### Wave 3 — Patterns C+D+E+J+K+L (composite helpers existentes, 8 sites)

`closePelAndRate`, `closePelAndRemove`, `toggleWatchedAndClose`,
`toggleCtxOlder`, `dismissToastAction`, `closeAuthAndReset`.

#### Wave 4 — Patterns F + I (sites individuales + checkin, 7 sites)

Incluye los **2 entry fixes** (Edit 1, Edit 2 de Fase 3) — el fix y la
migración del call site deben ir juntos (atomicity).

#### Wave 5 — Patterns M + AV (con args + setAvAddOpen, 4 sites)

`toggleFilmAlternatives` x2 y `setAvAddOpen` x2.

#### Wave 6 — Pattern G NEW helper (1 site)

`_activatePlanFilm` + entry + L5385.

#### Wave 7 — Pattern A #28 `addSuggestion` (1 site)

L7834. Entry nueva (Edit 3 de Fase 2) + migración del call site.

### Fase 4 — Validation gates

Post-Wave 7:

1. `python3 validate.py` → 26/26
2. `node --test tests/unit/*.test.js` → 131/131
3. JS syntax check
4. Functional equivalence — verificación por pattern
5. **QA Boot Path obligatorio**
6. Festival switch atómico

## Validate impact post-7c-3

| Métrica | Pre-7c-3 | Post-7c-3 |
|---|---|---|
| onclick remaining (occurrences) | 71 | 18 |
| onclick remaining (lines) | 70 | ~17 |
| data-action total | 72 | 125 |
| data-stop="1" | 12 | ~23 |
| Registry entries | 89 | 91 |
| Dead non-composite | 27 | ~3 |
| Check `[event-delegation]` nivel | WARNING | WARNING (sin cambio) |

## Riesgos y mitigaciones

### R1. Pattern Q — `_navTo` cartelera branch divergence

El helper `_navTo` (L3042-3052) tiene:
```js
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
```

L2592 original: `{const _ph=_getProgramaPhase();programaSubMode=_ph.default;switchMainNav('mnav-cartelera');showDayView();}`

**Risk**: si la secuencia difiere (e.g., orden de calls), comportamiento cambia.
**Mitigación**: inspección manual byte-level del helper vs el onclick original
en Wave 2. Si difiere, escalar.

### R2. Pattern F #42 — `closePlanConfirm(true)` semantics

Función signature: `closePlanConfirm(force)`. `force=true` actualmente sucede
solo en este 1 sitio (L2710 — botón "Ver Mi Plan").

**Risk**: si la función tiene side effects diferentes con `force=true` vs
`force=false`, el comportamiento del botón debe permanecer idéntico.
**Mitigación**: verificar function body en Wave 4. La migración pasa
`data-force="1"`. Sin atributo o `data-force="0"`, fallback a `force=false`.

### R3. Pattern H deferred → 7c-4

L5453 (`js-open-pel` wrapper) y L5456 (`mplan-tc` cell). Análisis profundo
durante planificación reveló que el rewrite del walking-up del listener
(de `closest()` a loop manual con stop detection) es necesario para que
el wrapper bloquee correctamente el `data-action` ancestor.

**Decisión D1=B**: defer a 7c-4 junto con otros edge cases que requieren
rediseño arquitectónico del listener. Listener intacto en 7c-3 → cero riesgo
de regresión sobre los 125 sites delegated post-7c-3.

### R4. Pattern N defer impact

Los 4 sitios `_openCombinedFilmSheet(JSON.parse(this.dataset.film))` quedan
con onclick inline post-7c-3. El registry entry actual está bugueada (lee
`dataset.title` pero función espera objeto). Mientras los call sites usen
onclick inline, el bug NO se activa. Confirmado seguro.

### R5. Coexistencia 18 onclicks remanentes con 125 data-actions

Todos los onclicks remanentes (7c-4 scope, incluye Pattern H) son patrones que
no interfieren con event-delegation (overlay close lambdas, IIFE en buttons
sin parent delegated, etc.). Verificar caso por caso en 7c-4.

## Helpers nuevos

**1**: `_activatePlanFilm` (Cat G, post-7c-1 helpers).

## Tests

**Cero tests nuevos.** Mismo principio que 7c-1/2. Verificación = R2' +
Playwright + manual QA.

## Backwards compat

Mismo principio. Los 16 onclicks remanentes siguen ejecutándose normalmente.

## Validate check `[event-delegation]`

Sin cambios estructurales. Tras 7c-3:
- onclick=18, data-actions=125, registry=91, dead=~3.

## Commit message draft

```
refactor(controller): 7c-3 — multi-statement + interpolations (53 sites)

Verificación PRE bloqueante PASSED: closePlanConfirm y _toggleEveningFilms
NO están siendo invocados via delegated path actualmente — fixes son safe.

ACTION_REGISTRY edits:
- Fix closePlanConfirm: (el) => closePlanConfirm(el.dataset.force === '1')
- Fix _toggleEveningFilms: (el) => _toggleEveningFilms(el)
- Add addSuggestion en Cat D
- Add activatePlanFilm en Cat G
- Total entries: 89 → 91

Nuevo helper: _activatePlanFilm en Cat G.

Migrations (53 sites):
- Wave 1: Pattern A — 28 sites con interpolación pura (single fn)
- Wave 2: Pattern B+Q — 5 sites con _navTo composite
- Wave 3: Pattern C+D+E+J+K+L — 8 sites con composite helpers existentes
- Wave 4: Pattern F+I — 7 sites (3 individuales + 4 checkin) con 2 entry fixes
- Wave 5: Pattern M+AV — 4 sites (toggleFilmAlternatives, setAvAddOpen)
- Wave 6: Pattern G — 1 site _activatePlanFilm
- Wave 7: Pattern A#28 — 1 site addSuggestion

D1=B: Pattern H (2 sites stopPropagation alone) diferido a 7c-4 junto con
rewrite del walking-up del listener. Listener intacto en 7c-3.

Validate:
- onclick remaining: 71 → 18
- data-actions usados: 51 → ~104
- 26/26 checks (sin cambios estructurales al check [event-delegation])

QA Boot Path PASSED. Tests 131/131. JS syntax OK.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

## Dependencias entre artefactos

```
Fase 0 (Verificación PRE bloqueante)
  ↓ [bloqueante]
Fase 1 (Helper _activatePlanFilm)
  ↓
Fase 2 (ACTION_REGISTRY 4 edits)
  ↓
Wave 1 (Pattern A — 28)
  ↓
Wave 2 (Pattern B+Q — 5)
  ↓
Wave 3 (Pattern C+D+E+J+K+L — 8)
  ↓
Wave 4 (Pattern F+I — 7, incluye fix activations)
  ↓
Wave 5 (Pattern M+AV — 4)
  ↓
Wave 6 (Pattern G — 1 with new helper)
  ↓
Wave 7 (addSuggestion — 1 with new entry)
  ↓
Fase 4 (Validation gates — 6 checks)
  ↓
Commit + Push + PR
```
