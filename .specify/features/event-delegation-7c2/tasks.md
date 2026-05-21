# Tasks — Event Delegation Wave 2 (Fase 7c-2)

- [ ] 1. `python3 validate.py` → 26/26 baseline + tests `node --test tests/unit/*.test.js` → 131/131
- [ ] 2. Crear branch `refactor/event-delegation-7c2`
- [ ] 3. **⚠ BLOQUEANTE — CSS selector check ⚠**
      ```
      grep -nE '\[data-(rmt|rfs|wt|prio-title|sec)([= ]|\])' index.html
      ```
      Si encuentra ≥1 match → **DETENER**, reportar al usuario líneas + contextos,
      esperar decisión explícita. Si 0 matches → GO.
- [ ] 4. QA browser PRE: trap global de errors instalado. Baseline esperado:
      96 onclick, festival cargado, console clean.
- [ ] 5. ACTION_REGISTRY edits (2 ediciones):
      - **Fix `selectFromDetail` entry** (L3141 aprox): cambiar de
        `(el) => selectFromDetail(el.dataset.title, el.dataset.day, el.dataset.time)`
        a `(el) => selectFromDetail(el)`
      - **Add `_toggleWLFromList`** en Categoría D (después de `_toggleEveningFilms`):
        ```js
        _toggleWLFromList:   (el)    => _toggleWLFromList(el.dataset.title, el),
        ```
      - Actualizar comentario header del registry: "88 entries" → "89 entries"
- [ ] 6. **Wave 1 — HTML renames (7 ediciones en 6 líneas)** — estado intermedio
      inestable, NO validar hasta post-Wave 2:
      - L5465: `data-rmt="${safeT}"` → `data-title="${safeT}"`
      - L6784: `data-prio-title="..."` → `data-title="..."`
      - L7036: `data-rmt="${safeT}"` → `data-title="${safeT}"`
      - L7037: `data-rfs="${safeT}"` → `data-title="${safeT}"`
      - L7787: `data-wt="..."` → `data-title="..."`
      - L7803: `data-wt="..."` → `data-title="..."`
      - L9766: `data-sec="..."` → `data-section="..."`
- [ ] 7. **Wave 2 — Grupo P migration (15 sites)** — onclick puro → data-action:
      - L5462 `toggleMplanProg(this,event)` → `data-action="toggleMplanProg"`
      - L6172 `selectAvDay(this.dataset.day)` → `data-action="selectAvDay"`
      - L6906 `toggleWatched(this.dataset.title,event)` → `data-action="toggleWatched"`
      - L7037 `removeFilmFromScenario(this.dataset.rfs,event)` → `data-action="removeFilmFromScenario"`
        (atributo ya renombrado en Wave 1; lee `dataset.title`)
      - L7042 `toggleMplanProg(this,event)` → `data-action="toggleMplanProg"`
      - L7077 `openCortoSheetFromEl(this,event)` → `data-action="openCortoSheetFromEl"`
      - L7787 `toggleWatched(this.dataset.wt,event)` → `data-action="toggleWatched"`
      - L7803 `toggleWatched(this.dataset.wt,event)` → `data-action="toggleWatched"`
      - L9725 `filterByVenue(this.dataset.venue)` → `data-action="filterByVenue"`
      - L9766 `filterBySection(this.dataset.sec)` → `data-action="filterBySection"`
      - L9785 `togglePelWL(this.dataset.title,event)` → `data-action="togglePelWL"`
      - L9786 `togglePelPrio(this.dataset.title)` → `data-action="togglePelPrio"`
      - L9787 `toggleWatched(this.dataset.title,event)` → `data-action="toggleWatched"`
      - L10093 `toggleWL(this.dataset.title,event)` → `data-action="toggleWL"`
      - L10094 `togglePelPrio(this.dataset.title)` → `data-action="togglePelPrio"`
- [ ] 8. **Wave 3 — Grupo P+S migration (10 sites)** — onclick + stopPropagation →
      `data-action` + `data-stop="1"`:
      - L5465 `removeFromAgenda(this.dataset.rmt);event.stopPropagation()` →
        `data-action="removeFromAgenda" data-stop="1"`
      - L6784 `event.stopPropagation();togglePriority(this.dataset.prioTitle)` →
        `data-action="togglePriority" data-stop="1"`
      - L6879 `togglePriority(this.dataset.title);event.stopPropagation()` →
        `data-action="togglePriority" data-stop="1"`
      - L6897 `openRatingSheet(this.dataset.title);event.stopPropagation()` →
        `data-action="openRatingSheet" data-stop="1"`
      - L7036 `removeFromAgenda(this.dataset.rmt);event.stopPropagation()` →
        `data-action="removeFromAgenda" data-stop="1"`
      - L10431 `event.stopPropagation();_toggleWLFromList(this.dataset.title,this)` →
        `data-action="_toggleWLFromList" data-stop="1"`
      - L10531 `event.stopPropagation();_toggleWLFromList(this.dataset.title,this)` →
        `data-action="_toggleWLFromList" data-stop="1"`
      - L10539 `event.stopPropagation();_toggleWLFromList(this.dataset.title,this)` →
        `data-action="_toggleWLFromList" data-stop="1"`
      - L10651 `event.stopPropagation();toggleWL(this.dataset.title,event)` →
        `data-action="toggleWL" data-stop="1"`
      - L10746 `event.stopPropagation();toggleWL(this.dataset.title,event)` →
        `data-action="toggleWL" data-stop="1"`
- [ ] 9. **Wave 4 — selectFromDetail bonus (1 site)**:
      - L5453 `onclick="selectFromDetail(this)"` → `data-action="selectFromDetail"`
- [ ] 10. `python3 validate.py` → **26/26**. Verificar reporte del check
       `[event-delegation]`: onclick remaining ≈ 70, registry 89 entries,
       data-actions usados ≈ 45, dead non-composite ≈ 31.
       Si false positive de mis propios comentarios (`data-action="X"` literal,
       `onclick="X"` literal) → reformular.
- [ ] 11. `node --test tests/unit/*.test.js` → **131/131**
- [ ] 12. JS syntax check: `node --check index.html 2>&1` → OK (esperar el
       warning estándar de top-level await en módulo HTML — no error)
- [ ] 13. **Functional equivalence (R2')** — verificación por categorías:
       - Pure dataset reads: click en heart de plist, venue chip, section chip,
         av-day chip → comportamiento idéntico a pre-migración
       - stopPropagation: click en row child con `data-stop="1"` → row padre NO
         recibe el click
       - `_toggleWLFromList`: corazón cambia visual (heartFill ↔ heart)
       - `selectFromDetail`: click en mplan-row → scroll a block correcto +
         row activa visualmente
- [ ] 14. Playwright skip local (run en CI vía push)
- [ ] 15. Festival switch Tribeca↔Leviza atómico — delegated listener funciona
       post-loadFestival DOM rebuild para los 26 nuevos sites
- [ ] 16. ⚠ **QA BOOT PATH OBLIGATORIO** ⚠:
       - localStorage.clear() + reload
       - showAgView() / render() / _renderProgramaContent() con FILMS=0
       - Click simulado en al menos 1 de cada categoría P/P+S/selectFromDetail
         (e.g., `[data-action="toggleWatched"]`, `[data-action="togglePriority"][data-stop="1"]`,
         `[data-action="selectFromDetail"]`)
       - **0 errors captured**
- [ ] 17. Diff review:
       - 5 atributos renombrados (7 ediciones en HTML)
       - ACTION_REGISTRY 89 entries (88 + `_toggleWLFromList`); `selectFromDetail`
         entry corregido
       - 26 sites con `data-action` attributes
       - 10 sites con `data-stop="1"` añadido
       - Cero cambios en signatures de las 14 funciones invocadas
       - Cero cambios en validate.py
- [ ] 18. `python3 validate.py` → 26/26 pre-commit
- [ ] 19. `node scripts/bump-version.js`
- [ ] 20. Commit atómico (mensaje según plan.md sección "Commit message draft")
- [ ] 21. Push + PR contra `main` con título
       `refactor(controller): event delegation wave 2 — dataset + stopPropagation (p7c-2)`
- [ ] 22. Monitorear CI hasta verde — Playwright T01-T10 + T32 deben pasar
- [ ] 23. Merge squash + cleanup branch
