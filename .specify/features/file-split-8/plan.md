# Plan — File Split / ES Modules nativos (Fase 8)

## Restricciones

**R1. Relocación, no reescritura.** Fase 8 MUEVE código a módulos + añade
import/export. Cero cambios de lógica. Excepción: eliminar el mirror de globals
(D-INFRA-4) — el único cambio de "cómo se accede al estado", no de qué hace.

**R2. Functional equivalence por wave.** Tras cada wave la app se comporta
idéntico. validate + unit tests + Playwright + QA boot path verde antes de la
siguiente.

**R3. DAG acíclico es invariante.** Cada import debe resolver sin ciclo (§12
verificó el grafo). Si una wave revela un ciclo no previsto → DETENER, romper
con late-binding/inyección, re-verificar.

**R4. Coexistencia funciona.** Entre waves, inline + módulos coexisten (D8-1).
La app NO se rompe en estados intermedios.

**R5. Test infra migra incrementalmente** (D8-2). Cada wave migra sus propios
tests a import directo.

**R6. QA device (D-INFRA-3)** antes de promover a producción nativa.

**R7. Deploy especial.** El primer deploy multi-file sube `src/` + index.html
(no el drag-and-drop de 1 archivo). Coordinar con Juan.

## Fase 0 — Pre-flight (antes de Wave 1)

1. `python3 validate.py` → baseline + `node --test tests/unit/*.test.js` → 141.
2. Branch `refactor/file-split-8`.
3. **Cerrar D8-1, D8-2, D8-3** con Juan.
4. **Setup ESM en tests**: decidir `.mjs` vs `"type":"module"` en package.json.
   ⚠ `"type":"module"` afecta TODOS los `.js` del repo (scripts/, etc.) — usar
   `.mjs` para los tests o un subdirectorio con su propio package.json.
5. Convertir el `<script>` grande de index.html a `<script type="module"
   src="/src/main.js">` + crear `src/main.js` placeholder que re-importa todo
   (estrategia bridge D8-1=A).

## Waves de extracción (orden topológico §12)

Cada wave: crear módulo(s) → mover funciones → export → import deps → bridge
temporal (D8-1) → migrar tests de esa capa → validate + Playwright.

### Wave 1 — `src/config.js` (leaf)
- Mover: `FESTIVAL_CONFIG`, constantes globales, `BUILD_VERSION`, ICONS? (ICONS
  podría ser view/components — decidir). Constantes de tiempo, límites, etc.
- Export todo. Bridge: `window.FESTIVAL_CONFIG = ...` etc. para inline legacy.
- Sin tests propios (datos/constantes).

### Wave 2 — `src/domain/{schedule,time,film,festival}.js`
- Mover: las 22 fns unit-tested + 15 `_SCHED_PURE_FNS` + helpers puros.
  - `schedule.js`: computeScenarios, screensConflict, sortScreensByStrategy,
    isScreeningBlocked, scoreFilm, gapSuggestion.
  - `time.js`: festDate (_festDate), simNow, simTodayStr, parseDur (toMin),
    getFestivalPhase, dayFullyPassed, festivalEnded.
  - `film.js`: effectiveDuration, screeningPassed, classifyTodayScreenings,
    endedStats, titleSeed (_titleSeed), djb2 (_djb2), mulberry32, shuffle.
  - `festival.js`: resolveVenue (_resolveVenue).
- import: config. Export todo.
- **Migrar los 22 unit tests a import directo** (D-INFRA-5): cada test pasa de
  `loadDomain({...})` a `import { fn } from '../../src/domain/x.js'`.
- ⚠ Worker: las fns sched tienen copias worker-local en template strings (ver
  validate `[worker-overlap]`). El worker es un caso especial — el módulo
  domain debe seguir siendo consumible por el worker (que no usa ESM import).
  **Sub-decisión Wave 2**: cómo el worker accede a domain (inline copy se queda,
  o el worker importa el módulo si soporta `importScripts`/module worker).

### Wave 3 — `src/state/state.js` [elimina mirror — D-INFRA-4]
- Mover: el bloque STATE MIRROR (container completo). Export `state`.
- **Eliminar** `_MIRROR_TARGETS`/`_MIRROR_READERS` + los `let` globals. El
  container posee `_data` directamente. Los reads que hacían `watchlist`,
  `FILMS` directo ahora pasan por `state.get()` o el módulo que los expone.
- ⚠ ESTE ES EL CAMBIO MÁS DELICADO: cada lectura de un global mirror en TODO el
  código debe migrar a `state.get(k)` o destructure de `state.snapshot()`. Hay
  cientos de reads. **Sub-plan dedicado** — posiblemente el inline legacy
  mantiene un bridge `Object.defineProperty(window, 'watchlist', {get:()=>state.get('watchlist')})`
  hasta que cada capa se extraiga y migre sus reads.
- Migrar `state.test.js` a import directo (elimina sandbox de 19 globals).

### Wave 4 — `src/storage/storage.js`
- Mover: el storage block (localStorage adapter) + saveX/loadState.
- import: state, config. Export.
- Migrar `storage.test.js`.

### Wave 5 — `src/i18n/i18n.js`
- Mover: `t()`, `_applyI18nDOM`, carga de es.json/en.json. (setLang NO — es
  controller.)
- import: state, config. Export `t`, etc.

### Wave 6 — `src/view/{programa,agenda,miplan,sheets,components}.js`
- Mover: render* (renderAgenda, _renderProgramaContent, renderMiPlanCalendar,
  renderPelicula*, etc.), sheets (open/close), components (emptyState,
  _posterThumb, showToast, ICONS), surgical patches (updateCardState,
  updateAgTab, _reRenderIntereses, updateHorarioPrioBtn, updateRatingStars).
- import: domain, state, i18n, config. Export lo que controller consume.
- ⚠ El más grande (la mayoría del bloque L2754–11697). Sub-split por archivo
  según tamaño (D8-3).

### Wave 7 — `src/controller/{registry,pipeline,handlers}.js`
- Mover: handlers (toggleWL, …), ACTION_REGISTRY + delegated listener,
  composite helpers, RENDER PIPELINE (subscribeRender), renderActiveView,
  runCalc, setLang.
- import: view, state, domain, storage, i18n. Export lo que main necesita.
- Sub-orden interno: handlers → renderActiveView → registry → pipeline.

### Wave 8 — `src/main.js` + cleanup
- Bootstrap: DOMContentLoaded, loadFestival inicial, init del SW.
- **Eliminar todos los bridges `window.*`** (D8-1) — ya todo es módulo.
- index.html queda como shell puro.
- `sw.js`: añadir regla network-first `/src/`.
- `playwright.yml` + `bundle.yml`: añadir `src/`.

## Validación post-cada-wave

```
python3 validate.py            # adaptado a multi-file
node --test tests/unit/*.test.js   # migrados a import
# Playwright (CI o local)
# QA boot path manual
```

## validate.py — adaptación a multi-file (durante las waves)

Los checks que leen `index.html` single-file migran a leer `src/**/*.js` cuando
su capa se extrae:
- `[state-mirror]` → `src/state/state.js` (o se retira si el mirror se elimina)
- `[controller-pattern]`, `[event-delegation]` → `src/controller/*.js`
- `[view-purity]` → `src/domain/*.js` (las puras) + `src/view/*.js`
- `[storage-encapsulation]` → `src/storage/*.js`
- `[js-syntax]` → `node --check src/**/*.js` por archivo
- `[js-open-pel-coverage]`, i18n checks → buscar en `src/` + index.html shell

**Estrategia**: durante la transición, los checks leen `index.html` + `src/**`
concatenados (cubre el estado mixto de las waves intermedias). Al final, solo
`src/**` + el shell de index.html.

## Riesgos y mitigaciones

### R1. El mirror de globals (Wave 3) — el más delicado
- Cientos de reads de `watchlist`/`FILMS`/etc. directo en el código.
- Mitigación: bridge `Object.defineProperty` temporal que redirige los globals
  a `state.get()`, eliminado conforme cada capa migra sus reads. NO eliminar
  los globals de golpe.

### R2. Ciclos no previstos
- El DAG (§12) es a nivel de capa. Sub-módulos (view/programa vs view/agenda)
  podrían tener micro-ciclos.
- Mitigación: al sub-splittear view/controller, mapear el sub-DAG. Romper con
  re-export desde un index del paquete o late-binding.

### R3. Worker + domain (Wave 2)
- El worker usa copias inline de las sched fns (no ESM). Si domain se modulariza,
  el worker no puede `import` (a menos que sea module worker).
- Mitigación: evaluar module worker (`new Worker(url, {type:'module'})`) — o
  mantener la copia worker-local como hoy (el validate `[worker-overlap]` ya la
  gestiona). Decisión en Wave 2.

### R4. Orden de ejecución top-level (módulos vs script)
- En un script clásico, el orden top-level es lineal. En módulos, los imports
  se resuelven primero (hoisting de imports), luego el body. Código que dependía
  del orden de ejecución inline podría romperse.
- Mitigación: el bootstrap explícito en main.js (Wave 8) controla el orden de
  init. Los módulos solo definen (no ejecutan side effects al import, salvo el
  pipeline registrations y el listener — esos van en main o en un init()).

### R5. Pipeline registrations + listener (side effects al cargar)
- La RENDER PIPELINE (subscribeRender) y el delegated listener corren al
  cargar. En módulos, deben ejecutarse en orden tras definir todo.
- Mitigación: exportar funciones `initPipeline()` / `initListener()` llamadas
  desde main.js bootstrap, no side effects al import.

## Tests

Migración incremental a import directo (D-INFRA-5). Los 141 tests existentes se
preservan, solo cambia CÓMO cargan el código (import vs extracción). Posibles
tests nuevos para el bootstrap (main.js).

## Commit strategy

Una rama `refactor/file-split-8` con commits por wave (8+ commits). PR único al
final, O PRs por wave si se prefiere granularidad. **Decisión con Juan**: dado
el tamaño, PRs por wave (cada uno verificable + Playwright) reduce el riesgo de
un PR gigante. Pero el primer deploy multi-file requiere coordinación (R7).

## Dependencias entre artefactos

```
Fase 0 (pre-flight: D8-1/2/3 + ESM test setup + main.js placeholder)
  ↓
Wave 1 (config) → Wave 2 (domain) → Wave 3 (state, elimina mirror) →
Wave 4 (storage) → Wave 5 (i18n) → Wave 6 (view) → Wave 7 (controller) →
Wave 8 (main + cleanup bridges + sw.js + CI)
  ↓
QA device (D-INFRA-3)
  ↓
Deploy coordinado (R7)
```
