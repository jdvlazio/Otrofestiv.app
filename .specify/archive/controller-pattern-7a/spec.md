# Spec — Controller Pattern Fase 7a (20 action handlers)

## Problema

Las **21 funciones** que mezclan `state.set/update/batchUpdate` con DOM
mutation o render calls SON los Controllers actuales — pero viven dispersos,
sin convención de naming/estructura, mezclando reads inline con UI state
ephemeral.

Inventario detectado:
- 21 mixed handlers (loadFestival + 20 action handlers)
- Estructura interna variable: algunos hacen reads/mutations interleaved,
  otros mezclan render calls antes de terminar mutations, otros tienen
  guard logic disperso

§16.5 del roadmap define Fase 7 como "Controller layer". El alcance total
de Fase 7 incluye:
- 7a — **Action handlers cleanup** (esta spec)
- 7b — Tier 4 sheets/modals lifecycle
- 7c — onclick inline → event delegation
- 7d — subscribe → render pipeline

## Causa raíz

Crecimiento orgánico. Cuando un nuevo botón requirió un handler, se creó
una función ad-hoc que combinaba "leer estado + cambiar estado + actualizar
UI" en cualquier orden. Sin convención. El resultado:
- Imposible hacer mass-refactor de `onclick` → event delegation (7c) sin
  primero estandarizar las funciones target
- Imposible conectar `subscribe()` → render pipeline (7d) sin saber dónde
  termina la mutation y empieza el render
- Code review difícil — cada handler tiene su propio shape

## Solución — Fase 7a

Estandarizar las **20 action handlers** (excluye `loadFestival` que ya está
bien estructurado post-5.5 con 3 batches documentados) al **Controller
pattern canónico**:

```js
function actionX(...args) {
  // 1. READ — state snapshot + UI state + args (al tope)
  const {a, b, c} = state.snapshot();

  // 2. GUARD — early returns
  if (festivalEnded()) return;
  if (!shouldProceed(args, a)) return;

  // 3. MUTATE — state.set/update/batchUpdate
  state.batchUpdate({...});

  // 4. PERSIST — explicit save calls
  saveWL();

  // 5. RENDER + UI EFFECTS — renderX, showToast, etc. (al final)
  renderAgenda();
  showToast(...);
}
```

**Cero cambios de comportamiento**. Solo reorganización: reads al top,
mutations en medio, side effects al final.

## Por qué 7a habilita 7c (onclick delegation)

**Fase 7c** migra los 142 `onclick="fn(arg1,arg2)"` inline a un sistema
de event delegation:

```html
<!-- ANTES -->
<button onclick="toggleWL('Film Title')">

<!-- DESPUÉS -->
<button data-action="toggleWL" data-title="Film Title">
```

```js
// Delegated listener
document.addEventListener('click', e => {
  const action = e.target.closest('[data-action]')?.dataset.action;
  if (!action) return;
  const handler = ACTION_REGISTRY[action];
  if (handler) handler(e.target.dataset);
});
```

Este sistema requiere que los handlers tengan **shape uniforme**:
- Acceptan args via `dataset` (object) o positional
- No leen state desde globals (deben recibirlo destructured)
- Tienen contrato claro: input → state mutation → render

**Sin 7a, el delegation de 7c sería un caos** — cada handler tiene su propia
manera de leer args, su propio orden de mutate/render, y algunos asumen
que `this` es el button (deja de funcionar con delegation).

**Con 7a completado**, 7c puede hacer mass-refactor mecánico de los 142
onclick a data-action sabiendo que los handlers tienen shape predecible.

## Las 18 action handlers activos en scope

| Función | Líneas | Naturaleza | Categoría |
|---|---|---|---|
| `toggleWL` | 53 | Watchlist toggle con confirm modal si en savedAgenda | toggle* |
| `addSuggestion` | 44 | Añadir sugerencia del Planear al watchlist | add* |
| `confirmReplace` | 38 | Confirmar reemplazo de film en savedAgenda | confirm* |
| `toggleWatched` | 33 | Watched toggle con confirm modal | toggle* |
| `togglePriority` | 30 | Priority toggle con prio limit check | toggle* |
| `confirmAvBlock` | 29 | Confirmar block availability | confirm* |
| `setLang` | 23 | Lang change con DOM re-render | set* |
| `markWatchedFromPlan` | 22 | Mark watched desde Mi Plan | toggle* |
| `addBlock` | 19 | Add availability block | add* |
| `toggleFullDay` | 16 | Toggle full-day availability | toggle* |
| `confirmConflictReplace` | 16 | Confirm conflict resolution | confirm* |
| `removeFromAgenda` | 15 | Remove film del plan con confirm | remove* |
| `setDelay` | 12 | Set film delay | set* |
| `undoDelay` | 11 | Undo delay | undo* |
| `checkinLaVi` | 11 | Quick check "la vi" | toggle* |
| `savePVRating` | 10 | Save post-view rating | set* |
| `clearDelay` | 4 | Clear film delay | clear* |
| `removeBlock` | 4 | Remove availability block | remove* |

**Total ~373 líneas activas** a reorganizar.

## Dead removes incluidos en 7a (-18 líneas)

| Función | Líneas | Motivo |
|---|---|---|
| `clearSavedAgenda` | 6 | Orphaned por commit `7219918` ("refactor: Mi Plan sin segunda barra — Borrar eliminado"). El botón onclick fue removido pero la función quedó |
| `applySimTime` | 12 | Orphaned por commit de Fase 6c (`5574800` — view-purity Tier 3). Los callers vivían dentro de `renderSimPanel` que fue removido como dead code en 6c. Cleanup follow-up |

Precedent: 6a (renderNextStrip + renderGapOptions), 6b (renderSimPanel),
6c (renderMiPlanList). Total dead removed acumulado tras 7a: 6 funciones.

## Excluida del scope

| Función | Razón |
|---|---|
| `loadFestival` (277 líneas) | Ya state-aware via 3 batches atómicos de 5.5. Estructura distinta de las 20 — orchestrator de festival switch, no action handler |

## Decisiones de diseño incorporadas (G1-G3 + Tooling)

| # | Decisión | Aplicación en 7a |
|---|---|---|
| G1 | Orden 7a→7b→7c→7d | ✓ 7a foundational (esta spec) |
| G2 | Solo spec 7a ahora | ✓ 7b/7c/7d se spec después de 7a merged |
| G3 | Excluir loadFestival | ✓ 20 fns (era 21) |
| Tooling | Cero tests nuevos | ✓ Playwright + DOM CRC + manual QA + QA boot path |
| Tooling | Validate check `[controller-pattern]` WARNING | ✓ Verifica shape de los 20 handlers |

## Validate check `[controller-pattern]` (WARNING en 7a)

Implementación:
```python
check = 'controller-pattern'
CONTROLLER_FNS = [
    'toggleWL', 'addSuggestion', 'confirmReplace', 'toggleWatched',
    'togglePriority', 'confirmAvBlock', 'setLang', 'markWatchedFromPlan',
    'addBlock', 'toggleFullDay', 'confirmConflictReplace', 'removeFromAgenda',
    'setDelay', 'undoDelay', 'checkinLaVi', 'savePVRating',
    'clearDelay', 'removeBlock',
]  # 18 handlers activos (clearSavedAgenda + applySimTime dead-removed)

# Para cada handler:
#   1. Verificar que tenga state.snapshot() destructure en las primeras
#      6 líneas (después del comentario header si lo hay) — opcional si
#      el handler no lee estado del roster
#   2. Verificar que NO haya state.set/update/batchUpdate DESPUÉS de
#      renderX() o document.X — el orden debe ser mutate → render
```

**Nivel**: WARNING en 7a. Promote a FAIL en 7d cuando subscribe pipeline
elimina los render calls explícitos y la separación es estricta.

## Lo que NO entra en Fase 7a

| Out-of-scope | Razón | Fase futura |
|---|---|---|
| `loadFestival` cleanup adicional | Ya bien estructurado post-5.5 | — |
| Tier 4 sheets/modals (13 fns) | Requiere lifecycle separado | 7b |
| onclick inline → event delegation | Requiere data-action attribute migration en templates | 7c |
| `state.subscribe()` connection | Architectural change separado | 7d |
| Migrar onclick callers de las 20 fns | El refactor 7a no cambia signatures — callers intactos | 7c |
| Cambio en `addEventListener` patterns existentes (29 sitios) | Listeners actuales OK por ahora | 7c |

## Definition of Done

- [ ] 20 action handlers reorganizadas al Controller pattern canónico
      (read → guard → mutate → persist → render)
- [ ] `state.snapshot()` destructure al top en cada handler que lea state
      del roster (algunos handlers solo escriben y no necesitan reads)
- [ ] Cero cambios en signature de las 20 fns (callers intactos)
- [ ] Validate check `[controller-pattern]` añadido nivel WARNING
- [ ] `python3 validate.py` → 25/25 (24 previos + 1 nuevo)
- [ ] `node --test tests/unit/*.test.js` → 131/131 (sin cambios)
- [ ] HTML output **byte-identical** pre/post (DOM CRC match)
- [ ] **QA Boot Path obligatorio** (de 6c): localStorage.clear() + reload
      + invocar handlers SIN loadFest previo → cero errors
- [ ] QA flow normal — togglar watchlist, add/remove plan, set delay,
      change lang, festival switch
- [ ] Playwright T01-T10 + T32 verde en CI
- [ ] **Habilita Fase 7c** — los 142 onclick handlers ahora tienen targets
      con shape uniforme listos para `data-action` migration
