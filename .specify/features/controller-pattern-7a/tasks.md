# Tasks — Controller Pattern Fase 7a (20 action handlers)

- [ ] 1. `python3 validate.py` → 24/24 baseline + `node --test tests/unit/*.test.js` → 131/131
- [ ] 2. Crear branch `refactor/controller-pattern-7a`
- [ ] 3. Re-verificar inventario: 20 handlers (excluye loadFestival) en HEAD, líneas y state reads exactos
- [ ] 4. QA browser PRE — dump CRC de 3 containers (ag-view, programa-list, av-blocks-list)
- [ ] 5. **Pequeños (4-15 líneas, 8 fns)**: `removeBlock`, `clearDelay`, `clearSavedAgenda`, `applySimTime`, `setDelay`, `undoDelay`, `checkinLaVi`, `savePVRating`. Aplicar pattern: read top → guard → mutate → persist → render
- [ ] 6. **Medianos (15-30 líneas, 8 fns)**: `removeFromAgenda`, `confirmConflictReplace`, `toggleFullDay`, `addBlock`, `markWatchedFromPlan`, `setLang`, `confirmAvBlock`, `togglePriority`. Modal callbacks NO se re-aplican pattern (closures internas)
- [ ] 7. **Grandes (30-53 líneas, 4 fns)**: `toggleWatched`, `confirmReplace`, `addSuggestion`, `toggleWL`. Estos tienen branching complejo — aplicar pattern donde se ajuste, documentar variantes en code comment
- [ ] 8. Añadir check `[controller-pattern]` a validate.py nivel WARNING. Verifica:
    - State reads (destructure) deben estar al top, NO después de mutations
    - State mutations deben estar ANTES de render/DOM calls
    - Whitelist: modal callbacks + helpers anidados (closures)
- [ ] 9. `python3 validate.py` → 25/25, 0 warnings activas para los 20 handlers
- [ ] 10. `node --test tests/unit/*.test.js` → 131/131
- [ ] 11. JS syntax check
- [ ] 12. QA browser POST — CRC pre/post match exact en 3 containers
- [ ] 13. QA browser — flow representativo:
    - Toggle WL en card → ver pill update
    - Toggle watched → ver pill update
    - Toggle priority → ver star + prio strip
    - Add availability block → renderAvBlocks update
    - Set/undo delay en Mi Plan → filmDelays update + history
    - Change lang ES↔EN → DOM text update
    - Apply sim time → simNow change visible
- [ ] 14. QA browser — festival switch Tribeca↔Leviza (verifica handlers no rompen post-state-swap)
- [ ] 15. Diff review — cada handler con pattern 5-pasos aplicado, modal callbacks intactos, signatures sin cambio
- [ ] 16. ⚠ **QA BOOT PATH OBLIGATORIO** ⚠ (F6 heredado de 6c):
    1. `localStorage.clear(); location.reload();`
    2. Tras reload, en consola: invocar handlers SIN loadFest previo
       (al menos `applySimTime(null)` + `showAgView()` + `render()`)
    3. Verificar console.errors === [] y window._capturedErrs === []
    4. Solo si paso 3 limpio → pasar a paso 17
- [ ] 17. `python3 validate.py` → 25/25 pre-commit
- [ ] 18. `node scripts/bump-version.js`
- [ ] 19. Commit atómico
- [ ] 20. Push + PR contra `main` con título `refactor(controller): 7a — 20 action handlers al pattern canónico`
- [ ] 21. Monitorear CI hasta verde — Playwright T01-T10 + T32 deben pasar
- [ ] 22. Merge squash + cleanup branch
