# Plan — Subscribe→Render Pipeline (Fase 7d)

## Restricciones

**R1. Cambios quirúrgicos** — solo:
- `subscribeRender` + `_runRenderSubs` en state container + integración en set/batchUpdate
- `renderActiveView()` router
- Sección RENDER PIPELINE con las registraciones de los 10 core slices
- Remoción de ~60-90 render calls manuales en handlers de core slices
- 1 unit test nuevo (dedup) + tests adicionales
- Actualización del check `[controller-pattern]` + promote a FAIL

**R2. Contrato `subscribe(key,cb)` INTACTO.** `state.test.js` L176 (cb con
value,key) debe seguir verde. Por eso el canal de render es separado.

**R3. R2' functional equivalence.** Cada mutación produce el mismo render que
antes — ahora automático. Verificación funcional + dedup test + no-double-render.

**R4. Semántica síncrona preservada (D1=A).** Renders corren al final del
batch, síncronos. Código que lee DOM post-mutación sigue funcionando.

**R5. Cero cambios en signatures de funciones de dominio.** Las funciones de
render NO se modifican. Solo se cambia QUIÉN las llama (subscriber vs handler).

**R6. QA Boot Path obligatorio.**

**R7. bump-version + commit atómico.**

**R8. Check `[controller-pattern]` a FAIL** — anticipado en su comentario.

## Alcance detallado

### Fase 0 — Baseline + mapa de dependencias

```bash
python3 validate.py        # 26/26
node --test tests/unit/*.test.js   # 131/131
```

Construir el mapa preciso slice → handlers → renders examinando cada handler
de core slice. Documentar qué render bundle sigue a cada mutación (para saber
qué remover y qué registrar).

### Fase 1 — State container: subscribeRender + _runRenderSubs

Añadir al IIFE del state container (entre `subscribe` y los helpers immutable):

```js
const _renderSubs = new Map();   // Map<key, Set<renderFn>>

function _runRenderSubs(keys) {
  const fns = new Set();
  for (const k of keys) {
    const subs = _renderSubs.get(k);
    if (subs) subs.forEach(fn => fns.add(fn));
  }
  [...fns].forEach(fn => { try { fn(); } catch(e) { console.error('[render] subscriber error:', e); } });
}
```

API pública:
```js
subscribeRender(keys, renderFn) {
  for (const k of keys) {
    if (!_renderSubs.has(k)) _renderSubs.set(k, new Set());
    _renderSubs.get(k).add(renderFn);
  }
  return () => keys.forEach(k => _renderSubs.get(k)?.delete(renderFn));
},
```

Integración:
```js
// set(): tras _notify(key)
_notify(key);
_runRenderSubs([key]);

// batchUpdate(): tras el loop de _notify
if (_batchDepth === 0) {
  const toNotify = [..._dirty];
  _dirty.clear();
  for (const k of toNotify) _notify(k);
  _runRenderSubs(toNotify);   // deduped a través de todas las dirty keys
}
```

**Importante**: `_runRenderSubs` corre DESPUÉS de `_notify` (subscribers
genéricos primero, renders después) — preserva el orden y el contrato.

### Fase 2 — Unit test (dedup) — TDD antes de wiring

Extender `state.test.js` (reusa el sandbox `makeSandbox`). El sandbox debe
exponer `subscribeRender` y `batchUpdate` (ya disponibles vía el objeto state).

Tests:
1. `subscribeRender: batchUpdate 3 keys → render 1×` (núcleo)
2. `subscribeRender: set() single key → render 1×`
3. `subscribeRender: unsubscribe fn detiene render`
4. `subscribeRender: renders disjuntos (A↔2 keys, B↔1 key) en un batch → A 1×, B 1×`
5. `subscribeRender NO afecta contrato subscribe(value,key)` (regression guard)

Correr → deben pasar tras Fase 1.

### Fase 3 — renderActiveView() router

Definir en CONTROLLER LAYER o RENDER PIPELINE section:

```js
function renderActiveView() {
  if (typeof activeView !== 'undefined' && activeView === 'day') {
    if (typeof showDayView === 'function') showDayView();
    return;
  }
  if (typeof renderAgenda === 'function') renderAgenda();
}
```

Verificar contra el comportamiento de los guards `if(activeView==='agenda')`
dispersos — el router debe replicar la lógica de ruteo existente.

### Fase 4 — RENDER PIPELINE registrations

Nueva sección (post-CONTROLLER LAYER o al final del setup). Registrar los 10
core slices según el mapa de Fase 0. Estructura tentativa (afinar con mapa):

```js
// ── RENDER PIPELINE (p7d) ──────────────────────────────────────────
// Conecta state slices → renders. Reemplaza las llamadas manuales de
// render en los handlers. Deduped vía subscribeRender.

// Slices de interés/vista (sin afectar schedule cache)
state.subscribeRender(
  ['watchlist','watched','prioritized','filmRatings'],
  () => { updateAgTab(); renderActiveView(); }
);
// Slices que afectan el cómputo de horario → invalidan cache
state.subscribeRender(
  ['filmDelays','filmDelaysHistory','savedAgenda','lastRemovedSlots','_simTime'],
  () => { cachedResult = null; updateAgTab(); renderActiveView(); }
);
// Availability → panel propio + recompute si planner
state.subscribeRender(
  ['availability'],
  () => { cachedResult = null; renderAvBlocks(); if (activeMNav === 'mnav-planner') runCalc(); }
);
```

⚠ El mapa exacto (qué renders por slice) se valida en Fase 0 contra los
handlers reales. Ajustar antes de remover los manuales.

### Fase 5 — Remover render calls manuales (waves por slice)

Para cada core slice, quitar de sus handlers las llamadas que ahora hace el
pipeline. Mantener: state mutations, persist (saveX), surgical patches.

#### Wave 1 — watchlist/watched/prioritized/filmRatings handlers
toggleWL, toggleWatched, togglePriority, togglePelWL, togglePelPrio,
savePVRating, _reRenderIntereses callers, etc.

#### Wave 2 — schedule slices handlers
setDelay, clearDelay, undoDelay, removeFromAgenda, removeFilmFromScenario,
addSuggestion, confirmReplace, savedAgenda mutations.

#### Wave 3 — availability handlers
addBlock, removeBlock, toggleFullDay, confirmAvBlock.

⚠ Riesgo: algunos handlers tienen renders CONDICIONALES
(`if(activeView==='agenda') renderAgenda()`). El pipeline + renderActiveView
maneja esto. Verificar cada remoción contra el comportamiento esperado.

### Fase 6 — Actualizar check [controller-pattern]

Nuevo shape canónico: read → guard → mutate → persist (NO render). El check:
- Verifica que los handlers de core slices NO contengan render calls directos
  (render ahora automático)
- Mantiene: state reads al top, mutations antes de cualquier efecto
- Promote a FAIL

Ajustar `RENDER_CALLS` logic: en vez de "mutate antes de render", verificar
"NO render en el handler" para los core slices.

### Fase 7 — Validation gates

1. `python3 validate.py` → 26/26
2. `node --test tests/unit/*.test.js` → ~135/135
3. JS syntax check
4. Functional equivalence por slice
5. **No double-render** (browser eval render counter)
6. **QA Boot Path obligatorio**
7. Festival switch atómico

## Validate impact post-7d

| Métrica | Pre-7d | Post-7d |
|---|---|---|
| Render calls manuales | ~128 | ~40-60 (surgical + out-of-scope) |
| subscribeRender registrations | 0 | 3 (10 slices) |
| cachedResult=null disperso | 11 sites | centralizado en pipeline |
| Unit tests | 131 | ~135 |
| Check `[controller-pattern]` | WARNING | FAIL (nuevo shape) |

## Riesgos y mitigaciones

### R1. Double-render (regresión de perf)
- **Riesgo**: si un handler deja un render manual Y el pipeline también
  registra → doble render.
- **Mitigación**: Fase 5 remueve los manuales sistemáticamente. Fase 7
  verifica con render counter en browser.

### R2. Render faltante (under-render)
- **Riesgo**: remover un render manual que el pipeline NO cubre → UI no
  actualiza.
- **Mitigación**: el mapa de Fase 0 mapea cada render a su slice. Functional
  equivalence por slice verifica.

### R3. renderActiveView ruteo incorrecto
- **Riesgo**: el router no replica exactamente los guards
  `if(activeView===...)` dispersos.
- **Mitigación**: Fase 3 valida el router contra la lógica existente. QA
  browser navega entre vistas tras mutaciones.

### R4. Orden subscriber genérico vs render
- **Riesgo**: si algún subscriber genérico (no-render) depende de correr
  ANTES/DESPUÉS del render.
- **Mitigación**: hoy no hay subscribers genéricos de render wired. `_notify`
  corre antes de `_runRenderSubs` — orden determinista.

### R5. Timing del cache-bust
- **Riesgo**: cachedResult debe ser null ANTES de renderActiveView (que lee el
  cache). El subscriber hace `cachedResult=null; renderActiveView()` — orden
  correcto dentro del mismo callback.
- **Mitigación**: el cache-bust y el render viven en el mismo subscriber fn,
  orden garantizado.

### R6. batchUpdate anidado
- **Riesgo**: `_batchDepth` maneja anidamiento. `_runRenderSubs` solo corre
  cuando `_batchDepth===0`.
- **Mitigación**: integrar `_runRenderSubs` en el mismo guard
  `if(_batchDepth===0)` que ya existe.

## Helpers nuevos

**1**: `renderActiveView()` (router).

## Tests

**~4-5 tests nuevos** (dedup + variantes). Primer test nuevo de la serie —
justificado: el scheduler dedup es lógica pura testeable.

## Backwards compat

El comportamiento observable es idéntico. Los renders ocurren igual, ahora
disparados por el pipeline. Los slices out-of-scope (_lang, festival load)
siguen con render manual — coexisten sin conflicto.

## Commit message draft

```
refactor(controller): 7d — subscribe→render pipeline (10 core slices)

Conecta los renders al mecanismo subscribe del state container (foundation
p5.5, antes sin usar para render). Los handlers shed sus render calls manuales.

State container:
- Nuevo canal subscribeRender(keys, fn) — deduped, arg-less, separado del
  subscribe(key,cb) genérico (cuyo contrato value,key queda intacto).
- _runRenderSubs(keys): colecta render fns de las keys afectadas, dedup vía
  Set, ejecuta 1× cada una. Síncrono (sin cambio de timing).
- Integrado en set() y batchUpdate() (deduped a través de dirty keys).

renderActiveView() router: despacha showDayView/renderAgenda según activeView.

RENDER PIPELINE: 3 registrations cubren 10 core slices (watchlist, watched,
prioritized, filmRatings, filmDelays, filmDelaysHistory, savedAgenda,
lastRemovedSlots, _simTime, availability). cachedResult bust centralizado
(antes disperso en 11 sites).

Removidos ~60-90 render calls manuales de los handlers de core slices.
Surgical patches (updateCardState etc.) preservados (necesitan args).

Unit tests (+5): dedup batchUpdate 3 keys → render 1×, single set, unsubscribe,
renders disjuntos, regression guard del contrato subscribe.

Check [controller-pattern]: actualizado al nuevo shape (mutate→persist, NO
render) + promovido a FAIL.

Out-of-scope (7d-2/defer): _lang full refresh, festival load orchestration.

Validate 26/26. Tests ~135/135. QA Boot Path PASSED. No double-render verificado.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

## Dependencias entre artefactos

```
Fase 0 (Baseline + mapa de dependencias slice→render)
  ↓
Fase 1 (subscribeRender + _runRenderSubs en state container)
  ↓
Fase 2 (Unit test dedup — debe pasar tras Fase 1)
  ↓
Fase 3 (renderActiveView router)
  ↓
Fase 4 (RENDER PIPELINE registrations)
  ↓
Fase 5 (Remover render calls manuales — waves 1-3 por slice)
  ↓
Fase 6 (Actualizar [controller-pattern] + promote FAIL)
  ↓
Fase 7 (Validation gates + no-double-render + QA Boot Path)
  ↓
Commit + Push + PR
```

Nota: Fase 2 (test) va inmediatamente tras Fase 1 (TDD) — el dedup se verifica
en aislamiento antes de cablear los renders reales en Fase 4-5.
