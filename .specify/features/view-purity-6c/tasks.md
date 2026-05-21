# Tasks — View Purity Fase 6c (Tier 3, 7 fns + 1 dead)

- [ ] 1. `python3 validate.py` → 24/24 baseline + `node --test tests/unit/*.test.js` → 131/131
- [ ] 2. Crear branch `refactor/view-purity-6c`
- [ ] 3. Re-verificar inventario contra HEAD: 5 Group I + 2 Group II + 2 Group III skip + 1 Group IV dead. Confirmar state reads exactos
- [ ] 4. QA browser PRE — dump CRC de 5 containers: ag-view, programa-list, grid, cnt, av-blocks-list
- [ ] 5. **Group IV**: verificar git history de `renderMiPlanList` (`git log -S` + grep en strings), confirmar dead, eliminar (-44 líneas)
- [ ] 6. **Group I.1**: `renderAvBlocks` (26 líneas) → split `renderAvBlocksHTML(state)` + impure caller (commit a av-blocks-list)
- [ ] 7. **Group I.2**: `renderSbar` (30 líneas) → split. Pure half retorna HTML del contenido; impure caller maneja innerHTML + classList + appendChild
- [ ] 8. **Group I.3**: `renderProgramaList` (60 líneas) → split, impure caller commit a programa-list
- [ ] 9. **Group I.4**: `_renderExploreLista` (64 líneas) → split, impure caller commit a programa-list (mismo container que renderProgramaList — modes distintos)
- [ ] 10. **Group I.5**: `renderPeliculaView` (101 líneas) → investigar las 3 innerHTML al implementar. Decidir pattern (a)/(b)/(c) según multi-container layout. Split según fits
- [ ] 11. **Group II.1**: `render` (53 líneas) → state.snapshot() destructure al top con `{FILMS, _activeFestId, watched, watchlist}`. Sin signature change, sin split. Body sin más cambios
- [ ] 12. **Group II.2**: `renderAgenda` (78 líneas) → state.snapshot() destructure al top con `{savedAgenda, FILMS, _activeFestId, watched, watchlist}`. Sin signature change, sin split. Body sin más cambios
- [ ] 13. Validate check `[view-purity]`: añadir 5 pure halves nuevas a `PURE_FNS` (renderAvBlocksHTML, renderSbarHTML, renderProgramaListHTML, _renderExploreListaHTML, renderPeliculaViewHTML — o variantes según paso 10). Añadir comentario "Group II Tier 3 son impuros legítimos — NO en PURE_FNS"
- [ ] 14. `python3 validate.py` → 24/24, 0 warnings activas para las 22 funciones puras tracked
- [ ] 15. `node --test tests/unit/*.test.js` — 131/131
- [ ] 16. JS syntax check (validate.py [js-syntax])
- [ ] 17. QA browser POST normal — CRC pre/post match exact en 5 containers (byte-identical R2)
- [ ] 18. QA browser — flow normal: Mi Plan tab (renderAgenda branches), Programa tab (render, renderPeliculaView, renderProgramaList, _renderExploreLista, renderSbar), Availability sheet (renderAvBlocks)
- [ ] 19. QA browser — festival switch Tribeca↔Leviza (verifica orchestrators reactúan al state swap atómico de 5.5)
- [ ] 20. QA browser — toggle watchlist/watched (verifica `render`, `renderAgenda`, `_reRenderIntereses` chain re-renderean correctamente con state actualizado)
- [ ] 21. Diff review — Group I: pure halves bien extractas + impure callers solo side effects. Group II: solo destructure al top. Group IV: solo delete
- [ ] 22. ⚠ **QA BOOT PATH OBLIGATORIO** ⚠ (F6 — paso bloqueante):
    1. En Chrome: `localStorage.clear(); location.reload();`
    2. Esperar a que cargue (splash o initial state)
    3. ANTES de seleccionar festival, en console: ejecutar `showAgView(); render(); _renderProgramaContent();`
    4. Verificar console.errors === [] (cero TypeError, cero "Cannot read properties of undefined")
    5. Solo si paso 4 limpio → pasar a paso 23. Si fail → reabrir migrations missing state arg
- [ ] 23. `python3 validate.py` → 24/24 pre-commit
- [ ] 24. `node scripts/bump-version.js`
- [ ] 25. Commit atómico
- [ ] 26. Push + PR contra `main` con título `refactor(view): purity Tier 3 — 5 split + 2 destructure + 1 dead (p6c)`
- [ ] 27. Monitorear CI hasta verde — Playwright T01-T10 + T32 deben pasar
- [ ] 28. Merge squash + cleanup branch
