# Tasks — Subscribe→Render Pipeline (Fase 7d)

> **Scope: 10 core slices, ~60-90 render calls manuales removidos.** Conecta
> renders al subscribe existente (foundation p5.5). Canal `subscribeRender`
> separado (preserva contrato `subscribe(value,key)`). Primer unit test nuevo
> de la serie (dedup). Promote `[controller-pattern]` a FAIL.

- [ ] 1. `python3 validate.py` → 26/26 baseline + `node --test tests/unit/*.test.js` → 131/131
- [ ] 2. Crear branch `refactor/subscribe-render-7d`
- [ ] 3. **Mapa de dependencias** — examinar cada handler de core slice y
      documentar el render bundle que sigue a cada mutación. Confirmar:
      - watchlist/watched/prioritized/filmRatings → updateAgTab + renderActiveView
      - filmDelays/filmDelaysHistory/savedAgenda/lastRemovedSlots/_simTime → cache-bust + renderActiveView
      - availability → cache-bust + renderAvBlocks + runCalc (si planner)
      Ajustar las registraciones de Fase 4 si el mapa real difiere.
- [ ] 4. QA browser PRE: trap de errors + festival cargado + render counter instrumentado.
- [ ] 5. **State container: subscribeRender + _runRenderSubs** (entre `subscribe`
      y los helpers immutable):
      ```js
      const _renderSubs = new Map();
      function _runRenderSubs(keys) {
        const fns = new Set();
        for (const k of keys) { const subs = _renderSubs.get(k); if (subs) subs.forEach(fn => fns.add(fn)); }
        [...fns].forEach(fn => { try { fn(); } catch(e) { console.error('[render] subscriber error:', e); } });
      }
      // API:
      subscribeRender(keys, renderFn) {
        for (const k of keys) { if (!_renderSubs.has(k)) _renderSubs.set(k, new Set()); _renderSubs.get(k).add(renderFn); }
        return () => keys.forEach(k => _renderSubs.get(k)?.delete(renderFn));
      },
      ```
      Integrar en `set()`: tras `_notify(key)` → `_runRenderSubs([key])`.
      Integrar en `batchUpdate()`: tras el loop `_notify(k)` → `_runRenderSubs(toNotify)`.
- [ ] 6. **Unit test dedup** — extender `state.test.js` (sandbox makeSandbox):
      - `subscribeRender: batchUpdate 3 keys → render 1×` (NÚCLEO — requisito Juan)
      - `subscribeRender: set() single key → render 1×`
      - `subscribeRender: unsubscribe fn detiene render`
      - `subscribeRender: renders disjuntos en un batch → cada uno 1×`
      - `subscribeRender NO afecta contrato subscribe(value,key)` (regression guard)
      Correr → deben pasar tras paso 5.
- [ ] 7. **renderActiveView() router** (CONTROLLER LAYER o RENDER PIPELINE):
      ```js
      function renderActiveView() {
        if (typeof activeView !== 'undefined' && activeView === 'day') { if (typeof showDayView === 'function') showDayView(); return; }
        if (typeof renderAgenda === 'function') renderAgenda();
      }
      ```
      Validar contra los guards `if(activeView==='agenda')` dispersos — replicar ruteo.
- [ ] 8. **RENDER PIPELINE registrations** (sección nueva, según mapa de paso 3):
      ```js
      // ── RENDER PIPELINE (p7d) ──
      state.subscribeRender(['watchlist','watched','prioritized','filmRatings'],
        () => { updateAgTab(); renderActiveView(); });
      state.subscribeRender(['filmDelays','filmDelaysHistory','savedAgenda','lastRemovedSlots','_simTime'],
        () => { cachedResult = null; updateAgTab(); renderActiveView(); });
      state.subscribeRender(['availability'],
        () => { cachedResult = null; renderAvBlocks(); if (activeMNav === 'mnav-planner') runCalc(); });
      ```
- [ ] 9. **Wave 1 — remover render calls de handlers watchlist/watched/prioritized/filmRatings**:
      toggleWL, toggleWatched, togglePriority, togglePelWL, togglePelPrio,
      savePVRating, etc. Quitar renderAgenda/updateAgTab/runCalc/_reRenderIntereses/
      renderActiveView manuales. Mantener: mutations, saveX, updateCardState (surgical).
- [ ] 10. **Wave 2 — remover render calls de handlers schedule slices**:
      setDelay, clearDelay, undoDelay, removeFromAgenda, removeFilmFromScenario,
      addSuggestion, confirmReplace + savedAgenda mutations. Quitar cache-bust
      manual + renders (ahora en pipeline).
- [ ] 11. **Wave 3 — remover render calls de handlers availability**:
      addBlock, removeBlock, toggleFullDay, confirmAvBlock. Quitar
      renderAvBlocks/runCalc manuales.
- [ ] 12. `python3 validate.py` → verificar [controller-pattern] (aún WARNING en este punto, se actualiza en paso 13). Reformular self-induced false positives.
- [ ] 13. **Actualizar check `[controller-pattern]`** en validate.py:
      - Nuevo shape: read → guard → mutate → persist (NO render en handler)
      - Verificar que los core-slice handlers NO contengan render calls directos
      - Promote WARNING → FAIL
- [ ] 14. `python3 validate.py` → **26/26**
- [ ] 15. `node --test tests/unit/*.test.js` → **~135/135** (131 + nuevos)
- [ ] 16. JS syntax check vía extracción + Function constructor → OK
- [ ] 17. **Functional equivalence (R2')** por slice (browser):
      - watchlist: toggle corazón → agenda/intereses actualiza + tab count
      - prioritized: toggle estrella → agenda actualiza
      - filmDelays: setDelay → agenda re-renderiza con delay
      - savedAgenda: removeFromAgenda → plan actualiza
      - availability: addBlock → panel + recompute
- [ ] 18. **No double-render** — browser eval con render counter: batchUpdate
      multi-key (e.g. removeFromAgenda que toca watchlist+watched+prioritized)
      → renderActiveView ejecuta exactamente 1×, no N×.
- [ ] 19. Playwright skip local (run en CI)
- [ ] 20. Festival switch Tribeca↔Leviza atómico — subscribers sobreviven loadFestival
      (NOTA: festival load es out-of-scope, sigue render manual — verificar coexistencia)
- [ ] 21. ⚠ **QA BOOT PATH OBLIGATORIO** ⚠:
      - localStorage.clear() + reload + FILMS=0 → 0 errors
      - Mutar un slice (toggleWL) → renderActiveView dispara sin error con FILMS=0
      - 0 errors captured
- [ ] 22. Diff review:
      - subscribeRender + _runRenderSubs en state container (+ integración set/batch)
      - subscribe(value,key) genérico INTACTO (state.test.js L176 verde)
      - renderActiveView router + 3 pipeline registrations
      - ~60-90 render calls removidos de core-slice handlers
      - Surgical patches preservados
      - [controller-pattern] nuevo shape + FAIL
      - Cero cambios en signatures de funciones de render/dominio
- [ ] 23. `python3 validate.py` → 26/26 pre-commit
- [ ] 24. `node scripts/bump-version.js`
- [ ] 25. Commit atómico (mensaje según plan.md "Commit message draft")
- [ ] 26. Push + PR contra `main` con título `refactor(controller): subscribe→render pipeline (p7d)`
- [ ] 27. Monitorear CI hasta verde — Playwright T01-T10 + T32 + unit tests deben pasar
- [ ] 28. Merge squash + cleanup branch
