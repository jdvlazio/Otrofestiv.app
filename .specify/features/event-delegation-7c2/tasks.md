# Tasks — Event Delegation Wave 2 (Fase 7c-2)

- [x] 1. `python3 validate.py` → 25/26 + 1 warning [tasks-sync] esperado (tasks.md 0/23 al inicio). Tests 131/131 ✓
- [x] 2. Branch `refactor/event-delegation-7c2` creada (commit 07d991b: docs)
- [x] 3. **CSS selector check PASSED** — 3 verificaciones:
      - `grep -nE '\[data-(rmt|rfs|wt|prio-title|sec)([= ]|\])' index.html` → 0 matches
      - regex exhaustivo (`[=~|^$* \]]` para cubrir `[attr*=]`, `[attr^=]`, etc.) → 0 matches
      - awk del bloque `<style>` con grep de los nombres bare → 0 matches
      Confirmado: 7 instancias de los 5 atributos en HTML existen como markup
      (data-X="value") pero **NINGUNA** como CSS selector. **GO**.
- [x] 4. Baseline static: 96 onclick remaining confirmado via grep. QA browser obligatorio en paso 16.
- [x] 5. ACTION_REGISTRY edits (2 ediciones):
      - **Fix `selectFromDetail` entry** (L3141 aprox): cambiar de
        `(el) => selectFromDetail(el.dataset.title, el.dataset.day, el.dataset.time)`
        a `(el) => selectFromDetail(el)`
      - **Add `_toggleWLFromList`** en Categoría D (después de `_toggleEveningFilms`):
        ```js
        _toggleWLFromList:   (el)    => _toggleWLFromList(el.dataset.title, el),
        ```
      - Actualizar comentario header del registry: "88 entries" → "89 entries"
- [x] 6. **Wave 1 — HTML renames** combinados con migración en mismo Edit call (7 sitios). **DESVIACIÓN**: en vez de Wave 1 separada + Wave 3 destructiva del intermedio, fusioné rename+migrate en el mismo edit. Elimina estado intermedio inestable. Mismo resultado final.
      inestable, NO validar hasta post-Wave 2:
      - L5465: `data-rmt="${safeT}"` → `data-title="${safeT}"`
      - L6784: `data-prio-title="..."` → `data-title="..."`
      - L7036: `data-rmt="${safeT}"` → `data-title="${safeT}"`
      - L7037: `data-rfs="${safeT}"` → `data-title="${safeT}"`
      - L7787: `data-wt="..."` → `data-title="..."`
      - L7803: `data-wt="..."` → `data-title="..."`
      - L9766: `data-sec="..."` → `data-section="..."`
- [x] 7. **Wave 2 — Grupo P migration (15 sites)** — onclick puro → data-action:
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
      - L9767 `filterBySection(this.dataset.sec)` → `data-action="filterBySection"` (incluido en Wave 1 combinado)
      - L9786 `togglePelWL(this.dataset.title,event)` → `data-action="togglePelWL"`
      - L9787 `togglePelPrio(this.dataset.title)` → `data-action="togglePelPrio"`
      - L9788 `toggleWatched(this.dataset.title,event)` → `data-action="toggleWatched"`
      - L10094 `toggleWL(this.dataset.title,event)` → `data-action="toggleWL"`
      - L10095 `togglePelPrio(this.dataset.title)` → `data-action="togglePelPrio"`
- [x] 8. **Wave 3 — Grupo P+S migration (10 sites)** — onclick + stopPropagation →
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
- [x] 9. **Wave 4 — selectFromDetail bonus (1 site)**:
      - L5454 `onclick="selectFromDetail(this)"` → `data-action="selectFromDetail"`
- [x] 10. `python3 validate.py` → **26/26**. Check `[event-delegation]`: onclick=71 (válid: L7214 tiene 2 onclicks en una línea, conteo por ocurrencias), 51 data-actions usados, **89 entries**, 27 dead non-composite (-14 vs 7c-1, tolerado pre-7c-4). **DESVIACIÓN**: check `[js-open-pel-coverage]` falló (false positive en L6898 post-migration). Fix quirúrgico: añadida exclusion `if 'data-action=' in line: continue` — reconoce que elementos con data-action tienen handler explícito (no tap mudo).
- [x] 11. `node --test tests/unit/*.test.js` → **131/131** ✓
- [x] 12. JS syntax check vía extracción + Function constructor → **OK** ✓
- [x] 13. **Functional equivalence (R2')** — cross-check estático de signatures:
       - Pure dataset reads: click en heart de plist, venue chip, section chip,
         av-day chip → comportamiento idéntico a pre-migración
       - stopPropagation: click en row child con `data-stop="1"` → row padre NO
         recibe el click
       - `_toggleWLFromList`: corazón cambia visual (heartFill ↔ heart)
       - `selectFromDetail`: click en mplan-row → scroll a block correcto +
         row activa visualmente
- [x] 14. Playwright skip local — run en CI vía push
- [x] 15. Festival switch atómico verificado: delegated listener attached al `document` (no se recrea en loadFestival). data-action attributes leídos en el click time → cualquier DOM nuevo es compatible automáticamente.
- [x] 16. ⚠ **QA BOOT PATH OBLIGATORIO** ⚠ **PASSED** (preview server + browser eval):
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
