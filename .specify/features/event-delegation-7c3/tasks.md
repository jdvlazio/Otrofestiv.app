# Tasks — Event Delegation Wave 3 (Fase 7c-3)

> **Scope: 53 sites**. D1=B confirmado — Pattern H (2 sites) diferido a 7c-4
> junto con rewrite del walking-up del listener. Listener intacto en 7c-3.

- [ ] 1. `python3 validate.py` → 26/26 baseline + tests `node --test tests/unit/*.test.js` → 131/131
- [ ] 2. Crear branch `refactor/event-delegation-7c3`
- [ ] 3. **⚠ BLOQUEANTE — PRE verification ⚠**
      ```
      grep -nE 'data-action="(closePlanConfirm|_toggleEveningFilms)"' index.html
      ```
      Si encuentra ≥1 match → **DETENER**, reportar al usuario (significa que el
      bug latente de la entry YA se está activando vía delegated path).
      Si 0 matches → GO (las entries con fix pendiente no causan harm hoy —
      fix es safe).
- [ ] 4. QA browser PRE: trap global de errors instalado. Baseline esperado:
      71 onclick occurrences (70 lines), festival cargado, console clean.
- [ ] 5. Helper nuevo `_activatePlanFilm` definido después de `_toggleWLAndClose`
      (sección "Composite helpers" en CONTROLLER LAYER):
      ```js
      function _activatePlanFilm(el) {
        setActivePlanFilm(el);
        const i = parseInt(el.dataset.dayIndex, 10);
        if (!isNaN(i)) selectMiPlanDay(i);
      }
      ```
- [ ] 6. ACTION_REGISTRY edits (4 cambios):
      - **Fix `closePlanConfirm`** (Cat B): `(el) => closePlanConfirm(el.dataset.force === '1')`
      - **Fix `_toggleEveningFilms`** (Cat D): `(el) => _toggleEveningFilms(el)`
      - **Add `addSuggestion`** en Cat D después de `_toggleWLFromList`:
        ```js
        addSuggestion: (el) => addSuggestion(el.dataset.title, el.dataset.day, el.dataset.time),
        ```
      - **Add `activatePlanFilm`** en Cat G después de `_toggleWLAndClose` entry:
        ```js
        activatePlanFilm: (el) => _activatePlanFilm(el),
        ```
      - Actualizar comentarios header: "89 entries" → "91 entries", "Cat D (9)" → "(10)", "Cat G (10)" → "(11)"
- [ ] 7. **Wave 1 — Pattern A (28 sites)** — single fn con interpolación pura:
      - L5327 `miPlanNav(-1)` → `data-action="miPlanNav" data-dir="-1"`
      - L5342 `miPlanNav(1)` → `data-action="miPlanNav" data-dir="1"`
      - L5330 `selectMiPlanDay(${vs})` → `data-action="selectMiPlanDay" data-index="${vs}"`
      - L5335 same para `${ve}`
      - L5394 same para `${i}`
      - L6117 `addBlock('${day}')` → `data-action="addBlock" data-day="${day}"`
      - L6131 `toggleFullDay('${day}')` → `data-action="toggleFullDay" data-day="${day}"`
      - L6260 same
      - L6267 `removeBlock(...)` → `data-action="removeBlock" data-day data-from data-to`
      - L6109 `removeBlock(...);event.stopPropagation()` → + `data-stop="1"`
      - L7273 `confirmReplace(...)` → `data-action="confirmReplace" data-rmtitle data-newtitle data-day data-time`
      - L7569 `setDelay(...,${m})` → `data-action="setDelay" data-title data-day data-time data-mins="${m}"`
      - L7594 same
      - L7570 `undoDelay(...)` → `data-action="undoDelay" data-title data-day data-time`
      - L7571 `clearDelay(...)` → `data-action="clearDelay" data-title data-day data-time`
      - L8329 `jumpToScenario(${di})` → `data-action="jumpToScenario" data-index="${di}"`
      - L8402 `forceInclude('${safeT}');event.stopPropagation()` → `data-action="forceInclude" data-title data-stop="1"`
      - L8762 `swapPriority(...)` → `data-action="swapPriority" data-rmtitle data-addtitle`
      - L10287 `setProgramaChip('${chip.id}')` → `data-action="setProgramaChip" data-chip="${chip.id}"`
      - L10355 `_dismissNotice('${...}')` → `data-action="_dismissNotice" data-title`
      - L10833 `selectSplashFest(...)` → `data-action="selectSplashFest" data-name data-meta data-fest`
      - L10840 `_togglePastFest(this,...)` → `data-action="_togglePastFest"` (dead args omitidos — verificado en análisis)
      - L10895 `loadFestival('${id}')` → `data-action="loadFestival" data-fest="${id}"`
      - L10909 same
      - L10913 `_togglePastFestRow(this.closest(...),'${id}')` → `data-action="_togglePastFestRow" data-fest="${id}"`
      - L7484 `event.stopPropagation();openPostViewRating('${safeT}','','','','')` → `data-action="openPostViewRating" data-title data-stop="1"` (otros atributos omitidos = undefined; función handles)
      - L7678 `event.stopPropagation();openPostViewRating(...)` con 5 args reales → `data-action="openPostViewRating" data-title data-day data-time data-venue data-duration data-stop="1"`
- [ ] 8. **Wave 2 — Pattern B+Q (5 sites)** — `_navTo` composite:
      - L2592 cartelera multi-statement → `data-action="navTo" data-tab="mnav-cartelera"`
      - L2596 → `data-action="navTo" data-tab="mnav-seleccion"`
      - L2600 → `data-action="navTo" data-tab="mnav-planner"`
      - L2604 → `data-action="navTo" data-tab="mnav-miplan"`
      - L7753 cta-ctx-b → `data-action="navTo" data-tab="mnav-planner"`
- [ ] 9. **Wave 3 — Patterns C+D+E+J+K+L (8 sites)** — composite helpers existentes:
      - L9736 closePelAndRate + stop → `data-action="closePelAndRate" data-title data-stop="1"`
      - L9783 closePelAndRate → `data-action="closePelAndRate" data-title`
      - L10096 closePelAndRate → same
      - L9790 closePelAndRemove → `data-action="closePelAndRemove" data-title`
      - L9782 toggleWatchedAndClose → `data-action="toggleWatchedAndClose" data-title`
      - L7220 toggleCtxOlder → `data-action="toggleCtxOlder"`
      - L8485 dismissToastAction → `data-action="dismissToastAction"`
      - L12118 closeAuthAndReset → `data-action="closeAuthAndReset"`
- [ ] 10. **Wave 4 — Patterns F+I (7 sites)** — incluye activación de los 2 entry fixes:
      - L2710 `closePlanConfirm(true)` → `data-action="closePlanConfirm" data-force="1"` (activa fix B.1)
      - L7286 `_expandedFilm='';renderAgenda()` → `data-action="clearExpandedFilm"`
      - L7687 `_toggleEveningFilms(this)` → `data-action="_toggleEveningFilms"` (activa fix B.2)
      - L7214 (2 onclicks): `checkinLaVi('${st}')` → `data-action="checkinLaVi" data-title="${st}"` y `checkinNoLaVi('${st}')` → `data-action="checkinNoLaVi" data-title="${st}"`
      - L7229 → `data-action="checkinLaVi" data-title`
      - L7230 → `data-action="checkinNoLaVi" data-title`
- [ ] 11. **Wave 5 — Patterns M+AV (4 sites)** — args + setAvAddOpen:
      - L5457 `toggleFilmAlternatives(...);event.stopPropagation()` → `data-action="toggleFilmAlternatives" data-key data-title data-day data-time data-stop="1"`
      - L7040 same → same
      - L6118 `avAddOpen[day]=false;renderAvDay(day)` → `data-action="setAvAddOpen" data-day data-open="0"`
      - L6130 `avAddOpen[day]=true;renderAvDay(day)` → `data-action="setAvAddOpen" data-day data-open="1"`
- [ ] 12. **Wave 6 — Pattern G (1 site)** — `_activatePlanFilm` NEW helper:
      - L5385 `setActivePlanFilm(this);selectMiPlanDay(${i});event.stopPropagation()` →
        `data-action="activatePlanFilm" data-day-index="${i}" data-stop="1"`
- [ ] 13. **Wave 7 — Pattern A #28 addSuggestion (1 site)** — entry nueva ya en paso 6:
      - L7834 `event.stopPropagation();addSuggestion(...)` → `data-action="addSuggestion" data-title data-day data-time data-stop="1"`
- [ ] 14. `python3 validate.py` → **26/26**. Check `[event-delegation]`: onclick remaining ≈ 16, registry **91**, data-actions usados ≈ 106, dead non-composite ≈ 3.
      Reformular self-induced false positives si surgen.
- [ ] 15. `node --test tests/unit/*.test.js` → **131/131**
- [ ] 16. JS syntax check vía extracción + Function constructor → **OK**
- [ ] 17. **Functional equivalence (R2')** — verificación por pattern:
      - Pattern A: smoke test de delete-block (removeBlock), set-delay,
        navigate-day, jump-scenario, dismissNotice, selectSplashFest, loadFestival
      - Pattern B+Q: switch-tab a cartelera (verificar `_navTo` cartelera branch
        iguala secuencia original byte por byte), seleccion, planner, miplan
      - Pattern C+D+E: open pel-sheet, click "Calificar" → cierra sheet + abre rating;
        click "Quitar plan" → cierra + remove; click "Marcar vista" → toggle + close
      - Pattern G: click mplan-wk-block → activatePlanFilm (set + selectDay) sin
        que parent fire
      - Pattern AV: toggle av-add-open ambas direcciones
- [ ] 18. Playwright skip local (run en CI vía push)
- [ ] 19. Festival switch Tribeca↔Leviza atómico
- [ ] 20. ⚠ **QA BOOT PATH OBLIGATORIO** ⚠:
       - localStorage.clear() + reload + FILMS=0 → 0 errors
       - Click delegated en al menos: navTo, closePelAndRate, addSuggestion,
         activatePlanFilm, closePlanConfirm (fix activado)
       - 0 errors captured
- [ ] 21. Diff review:
       - 1 helper nuevo (`_activatePlanFilm`)
       - 4 ediciones al ACTION_REGISTRY (2 fixes + 2 adds)
       - 91 entries totales
       - 53 sites con `data-action` attributes (28 + 5 + 8 + 7 + 4 + 1 + 1)
       - Sin cambios al listener (D1=B defer Pattern H)
       - Cero cambios en signatures de las 18+ funciones invocadas
       - Cero cambios en validate.py (a menos que false positive emerja)
- [ ] 22. `python3 validate.py` → 26/26 pre-commit
- [ ] 23. `node scripts/bump-version.js`
- [ ] 24. Commit atómico (mensaje según plan.md sección "Commit message draft")
- [ ] 25. Push + PR contra `main` con título
       `refactor(controller): event delegation wave 3 — multi-statement + interpolations (p7c-3)`
- [ ] 26. Monitorear CI hasta verde — Playwright T01-T10 + T32 deben pasar
- [ ] 27. Merge squash + cleanup branch
