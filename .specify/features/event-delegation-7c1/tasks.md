# Tasks — Event Delegation Foundation + Trivial Migration (Fase 7c-1)

- [ ] 1. `python3 validate.py` → 25/25 baseline + `node --test tests/unit/*.test.js` → 131/131
- [ ] 2. Crear branch `refactor/event-delegation-7c1`
- [ ] 3. **Verificación schema**: confirmar que las 76 funciones invocadas desde onclick existen en HEAD (cero typos en mi ACTION_REGISTRY). Audit script systemático
- [ ] 4. QA browser PRE — captura snapshots de console.errors (línea base = 0). NO captura CRC (R2' no aplica byte-identity)
- [ ] 5. **Foundation step 1**: Añadir 11 helpers compuestos. Posición: post-state namespace, sección "// ── Composite helpers (Controller layer) ──"
- [ ] 6. **Foundation step 2**: Añadir ACTION_REGISTRY constant con 87 entries (categorías A-G). Posición: justo después de los helpers compuestos
- [ ] 7. **Foundation step 3**: Añadir delegated click listener + data-close-bg infra. Posición: al final del bloque "CONTROLLER LAYER"
- [ ] 8. **Wave 1 — 38 sites sin args**: migrar `onclick="X()"` → `data-action="X"`. Mass replace mecánico con grep + sed/edit. Sites: closePelSheet, dismissSplash, openAvSheet, openFestivalSheet, runCalc, sharePlan, exportICS, etc.
- [ ] 9. **Wave 2 — 17 sites con string-literal arg**: migrar `onclick="X('value')"` → `data-action="X" data-<argname>="value"`. Sites: switchMainNav(*), setAvType(*), setProgramaMode(*), setInteresesView(*), setProgramaChip(*), setLang(*), selectAvDay(*)
- [ ] 10. Añadir check `[event-delegation]` a validate.py nivel WARNING. Reporta: onclick remaining count, typo detection (data-action no en registry), dead entry detection (con tolerancia para composite helpers up-front)
- [ ] 11. `python3 validate.py` → 26/26. Verificar `[event-delegation]` reporta números esperados (onclick remaining ≈ 87 = 142-55, used_actions ≈ 30-40)
- [ ] 12. `node --test tests/unit/*.test.js` → 131/131
- [ ] 13. JS syntax check (validate.py [js-syntax])
- [ ] 14. **Functional equivalence test (R2')**: en el browser, click manual o programático en cada uno de los 55 sites migrados. Verificar:
    - Sheets close al click "×" migrado
    - Nav tabs cambian al click migrado
    - Search open/close funcional
    - Mode/view toggles funcionales
    - Console.errors === []
- [ ] 15. Playwright local (si disponible) — re-correr smoke tests
- [ ] 16. QA festival switch Tribeca↔Leviza (verifica delegated listener funciona post-DOM-rebuild de loadFestival)
- [ ] 17. ⚠ **QA BOOT PATH OBLIGATORIO** ⚠:
    1. `localStorage.clear(); location.reload();`
    2. Tras reload, ANTES de loadFest:
        - `showAgView(); render(); _renderProgramaContent();`
        - Simular click en `[data-action="dismissSplash"]` si existe (delegated listener debe activar)
    3. Verificar console.errors === []
- [ ] 18. Diff review:
    - ACTION_REGISTRY 87 entries en categorías A-G
    - 11 helpers definidos
    - Delegated listener + data-close-bg infra presente
    - 55 sites con data-action attributes (38 + 17)
    - Validate check añadido
    - Cero cambios en signatures de las 76 funciones invocadas
- [ ] 19. `python3 validate.py` → 26/26 pre-commit
- [ ] 20. `node scripts/bump-version.js`
- [ ] 21. Commit atómico
- [ ] 22. Push + PR contra `main` con título `refactor(controller): event delegation foundation + trivial migration (p7c-1)`
- [ ] 23. Monitorear CI hasta verde — Playwright T01-T10 + T32 deben pasar
- [ ] 24. Merge squash + cleanup branch
