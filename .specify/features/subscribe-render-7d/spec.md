# Spec — Subscribe→Render Pipeline (Fase 7d)

## Problema

~128 call sites imperativos de render en `index.html`. Cada handler, tras
mutar el state, llama manualmente a las funciones de render que dependen de esa
mutación:

```js
function togglePriority(title){
  state.update('prioritized', ...);   // mutate
  savePrio();                         // persist
  updateCardState(title);            // surgical patch
  updateAgTab();                     // tab count
  runCalc();                         // recompute
  renderAgenda();                    // full render — MANUAL
}
```

Problemas:
- **Acoplamiento**: el handler debe saber QUÉ renderizar tras cada mutación.
  Olvidar un render = bug "no se actualizó la UI".
- **Duplicación**: el mismo bundle de renders se repite en decenas de handlers.
- **Dispersión del cache-bust**: `cachedResult=null` aparece en 11 sites,
  acoplado manualmente a los renders de schedule.
- **Bloquea Fase 8**: para mover renders a `view/` necesitamos saber qué
  dispara cada render — el subscribe lo hace explícito.

## Hallazgo: la foundation ya existe (p5.5)

El state container ya tiene subscribe completo + batch coalescing:

```js
subscribe(key, cb)        // retorna unsubscribe
_notify(key)              // cb(value, key)
_subs = Map<key, Set<cb>>
// batchUpdate: _dirty acumula keys, _notify cada una 1× al final
```

**Pero ningún render está conectado.** 7d cablea renders al subscribe y
remueve las llamadas manuales. Es cableado + decoupling, no infraestructura
nueva.

## Restricción crítica: contrato del subscribe genérico

`state.test.js` L176 testea: `subscribe: cb se invoca síncronamente con
(value, key)`. Este contrato NO se puede romper. Por eso 7d introduce un
**canal separado** para renders en vez de reusar `subscribe`.

## Solución

### A. Canal `subscribeRender` (D1 — dedup)

Nuevo canal en el state container, distinto del `subscribe` genérico:

```js
// Registro: una render fn contra MÚLTIPLES keys. Deduped, arg-less.
const _renderSubs = new Map();   // Map<key, Set<renderFn>>

subscribeRender(keys, renderFn) {
  for (const k of keys) {
    if (!_renderSubs.has(k)) _renderSubs.set(k, new Set());
    _renderSubs.get(k).add(renderFn);
  }
  return () => keys.forEach(k => _renderSubs.get(k)?.delete(renderFn));
}

// Dedup: colecta render fns de todas las keys afectadas, ejecuta 1× cada una.
function _runRenderSubs(keys) {
  const fns = new Set();
  for (const k of keys) {
    const subs = _renderSubs.get(k);
    if (subs) subs.forEach(fn => fns.add(fn));
  }
  [...fns].forEach(fn => { try { fn(); } catch(e) { console.error('[render] subscriber error:', e); } });
}
```

Integración:
- `set(key, value)`: tras `_notify(key)` → `_runRenderSubs([key])`.
- `batchUpdate(updates)`: tras el loop de `_notify(k)` → `_runRenderSubs(toNotify)`
  (deduped a través de TODAS las dirty keys).

**Garantía dedup**: `batchUpdate({watchlist, watched, prioritized})` donde las
3 keys mapean a `renderActiveView` → `renderActiveView` ejecuta **exactamente
1 vez** (Set dedup de function refs).

**Semántica síncrona preservada** (D1=A): los renders corren síncronamente al
final del batch — DOM listo tras la mutación, igual que hoy. Cero cambio de
timing.

### B. Router `renderActiveView()` (D3 — A-lite)

Despacha al render correcto según la vista activa:

```js
function renderActiveView() {
  if (activeView === 'day') { showDayView(); return; }
  // activeView === 'agenda' → depende del mnav
  renderAgenda();  // renderAgenda ya rutea internamente por activeMNav
}
```

Los subscribers llaman `renderActiveView` en vez de un render específico —
elimina los renders de vistas ocultas sin dirty-tracking explícito (re-render
on view-switch ya existe vía los handlers de navegación).

### C. Registraciones del pipeline (sección RENDER PIPELINE)

Mapa de los 10 core slices → renders, con cache-bust centralizado (D5):

```js
// User-state slices que afectan la vista activa
state.subscribeRender(
  ['watchlist','watched','prioritized','filmRatings'],
  () => { updateAgTab(); renderActiveView(); }
);
// Schedule-affecting: invalidan cache antes de renderizar (D5)
state.subscribeRender(
  ['filmDelays','filmDelaysHistory','savedAgenda','lastRemovedSlots','_simTime'],
  () => { cachedResult = null; renderActiveView(); }
);
// Availability: panel propio + recompute
state.subscribeRender(
  ['availability'],
  () => { cachedResult = null; renderAvBlocks(); if (activeMNav === 'mnav-planner') runCalc(); }
);
```

(Las registraciones exactas se afinan en plan.md según el mapa de dependencias.)

### D. Surgical patches fuera del pipeline (D2 — A)

`updateCardState(title)` necesita el `title` arg → no encaja en el canal
arg-less. Se mantiene como llamada explícita donde se necesita patch puntual
(toggle de corazón sin re-render de grid). Igual `updateSimLabel(val)`,
`updateRatingStars(current)`, `updateHorarioPrioBtn(title)`.

### E. Remover llamadas manuales de render (D4 — A, core slices)

Los handlers de los 10 core slices shed sus render calls manuales (~60-90
calls). Quedan: read → guard → mutate → persist. El render es automático.

```js
// ANTES
function togglePriority(title){
  state.update('prioritized', ...);
  savePrio(); updateCardState(title); updateAgTab(); runCalc(); renderAgenda();
}
// DESPUÉS
function togglePriority(title){
  state.update('prioritized', ...);   // auto-dispara renderActiveView vía subscribeRender
  savePrio();
  updateCardState(title);            // surgical patch (D2) — se mantiene
}
```

### F. Actualizar check `[controller-pattern]` + promote a FAIL

El check actual valida "mutate → render". Tras 7d los handlers ya no llaman
render. El check evoluciona al nuevo shape canónico:
- read (snapshot al top) → guard → mutate → persist
- **NO render calls** en el handler (render es automático)

Y se promueve de WARNING a FAIL (anticipado en el comentario del check).

## Scope (D4 — foundation + core slices)

### Core slices (10) — IN

| Slice | Renders (vía pipeline) |
|---|---|
| watchlist | updateAgTab + renderActiveView |
| watched | updateAgTab + renderActiveView |
| prioritized | updateAgTab + renderActiveView |
| filmRatings | updateAgTab + renderActiveView |
| filmDelays | cache-bust + renderActiveView |
| filmDelaysHistory | cache-bust + renderActiveView |
| savedAgenda | cache-bust + renderActiveView |
| lastRemovedSlots | cache-bust + renderActiveView |
| _simTime | cache-bust + renderActiveView |
| availability | cache-bust + renderAvBlocks + runCalc (si planner) |

### Out-of-scope (orquestación especial)

| Slice | Razón | Fase |
|---|---|---|
| `_lang` | Full DOM refresh especial (_applyI18nDOM + selectores + fade) | 7d-2 o defer |
| `_activeFestId`, `FILMS`, `FESTIVAL_*` | Festival load — orquestación async compleja | 7d-2 o defer |
| Surgical patches (updateCardState, etc.) | Necesitan args (D2=A) | — |

## Unit test obligatorio (requisito de Juan)

`tests/unit/` extiende `state.test.js` (reusa el sandbox extractStateBlock) o
nuevo archivo `renderScheduler.test.js`. Test central:

```js
test('subscribeRender: batchUpdate de 3 keys → render ejecutado exactamente 1 vez', () => {
  const { state } = makeSandbox();
  let count = 0;
  state.subscribeRender(['watchlist','watched','prioritized'], () => count++);
  state.batchUpdate({
    watchlist:   new Set(['a']),
    watched:     new Set(['b']),
    prioritized: new Set(['c']),
  });
  assert.strictEqual(count, 1);  // dedup: 3 keys → 1 render
});
```

Tests adicionales:
- `set()` single key con subscribeRender → render fires 1×
- `subscribeRender` retorna unsubscribe fn funcional
- batch con renders disjuntos (2 keys → render A, 1 key → render B) → A 1×, B 1×
- subscribeRender NO interfiere con el contrato `subscribe(value, key)` existente

Test count: 131 → ~135-136.

## Decisiones de diseño incorporadas

| # | Decisión | Aplicación |
|---|---|---|
| D1 | Render scheduler | Canal `subscribeRender` deduped, **síncrono** (sin cambio de timing) |
| D2 | Surgical patches | Fuera del pipeline (updateCardState etc. siguen explícitos) |
| D3 | View-awareness | `renderActiveView()` router (A-lite, sin dirty-tracking) |
| D4 | Scope | Foundation + 10 core slices (~60-90 render calls removidos) |
| D5 | Cache invalidation | Centralizada en subscribers de schedule-keys |

## R2' (functional equivalence)

El comportamiento observable NO cambia: cada mutación produce el mismo render
que antes, ahora automático. Verificación:
1. **Functional equivalence** por slice: mutar cada slice produce el mismo
   UI update que antes
2. **Dedup unit test** PASSED
3. **No double-render**: verificar (browser eval con render counter) que
   batchUpdate multi-key no re-renderiza N×
4. **Console clean**: 0 errors
5. **Playwright T01-T10 + T32** verde
6. **QA Boot Path obligatorio**

## Definition of Done

- [ ] `subscribeRender(keys, fn)` + `_runRenderSubs(keys)` en state container
- [ ] `set()` y `batchUpdate()` integran `_runRenderSubs` (deduped en batch)
- [ ] `subscribe(key, cb)` genérico INTACTO — `state.test.js` L176 sigue verde
- [ ] **Unit test dedup**: batchUpdate 3 keys → render 1× (+ tests adicionales)
- [ ] `renderActiveView()` router definido
- [ ] Pipeline registrations para los 10 core slices (cache-bust centralizado)
- [ ] ~60-90 render calls manuales removidos de los handlers de core slices
- [ ] Surgical patches (updateCardState etc.) preservados
- [ ] Check `[controller-pattern]` actualizado al nuevo shape + promovido a FAIL
- [ ] `python3 validate.py` → 26/26
- [ ] `node --test tests/unit/*.test.js` → ~135/135 (131 + nuevos)
- [ ] JS syntax check OK
- [ ] **Functional equivalence R2'** por slice
- [ ] **No double-render** verificado (render counter)
- [ ] Playwright T01-T10 + T32 verde
- [ ] **QA Boot Path obligatorio** → 0 errors
