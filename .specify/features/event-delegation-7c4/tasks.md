# Tasks — Event Delegation Wave 4: Final + listener rewrite (Fase 7c-4)

> **Scope: 18 sites finales → onclick = 0**. Fase final de event-delegation.
> Listener walking-up rewrite + 5 helpers + 6 entries + 1 fix + 2 view-helper
> refactors + promote check a FAIL.

- [ ] 1. `python3 validate.py` → 26/26 baseline + tests `node --test tests/unit/*.test.js` → 131/131. Baseline: 18 onclick occurrences.
- [ ] 2. Crear branch `refactor/event-delegation-7c4`
- [ ] 3. **Verificación PRE** — confirmar `conflict-modal` ≠ `conflict-sheet`:
      ```
      grep -nE "id=[\"']conflict-modal[\"']|id=[\"']conflict-sheet[\"']" index.html
      ```
      Si `conflict-modal` no existe como id estático (se crea dinámicamente) → OK,
      `_removeConflictModal` usa getElementById en runtime. Confirmar no colisión.
- [ ] 4. QA browser PRE: trap de errors instalado. Baseline: 18 onclick, festival cargado, console clean.
- [ ] 5. **5 helpers nuevos** después de `_activatePlanFilm`:
      ```js
      function _scrollToSuggestions() { document.querySelector('.suggestion-wrap')?.scrollIntoView({behavior:'smooth', block:'start'}); }
      function _removeConflictModal() { document.getElementById('conflict-modal')?.remove(); }
      function _scrollToTop() { window.scrollTo({top:0, behavior:'smooth'}); }
      function _searchOpenFilm(title) { searchClose(); openPelSheet(title); }
      function _searchOpenCorto(title, country, dur, section, flags) { searchClose(); openCortoSheet(title, country, dur, section, flags); }
      ```
- [ ] 6. **ACTION_REGISTRY edits** (1 fix + 6 adds):
      - **Fix** `_openCombinedFilmSheet` (Cat B): `(el) => _openCombinedFilmSheet(JSON.parse(el.dataset.film))`
      - **Add** `markWatchedFromPlan` (Cat E): `(el, e) => markWatchedFromPlan(el.dataset.title, el.dataset.day, el.dataset.time, el.dataset.venue, el.dataset.dur, e)`
      - **Add** `scrollToSuggestions`, `removeConflictModal`, `scrollToTop` (Cat D / DOM utils): `() => _scrollToSuggestions()`, etc.
      - **Add** `searchOpenFilm` (Cat B): `(el) => _searchOpenFilm(el.dataset.title)`
      - **Add** `searchOpenCorto` (Cat B): `(el) => _searchOpenCorto(el.dataset.title, el.dataset.country, el.dataset.dur, el.dataset.section, el.dataset.flags)`
      - Actualizar comentarios header: "91 entries" → "97 entries" + counts categorías
- [ ] 7. **Listener rewrite (D1, núcleo)** — reemplazar listener (L3219 aprox) por loop manual:
      ```js
      document.addEventListener('click', function(e) {
        let node = e.target;
        while (node && node !== document) {
          if (node.dataset) {
            if (node.dataset.action) {
              if (node.dataset.stop === '1') e.stopPropagation();
              const handler = ACTION_REGISTRY[node.dataset.action];
              if (handler) handler(node, e);
              return;
            }
            if (node.dataset.stop === '1') { e.stopPropagation(); return; }
          }
          node = node.parentElement;
        }
        const bg = e.target.closest('[data-close-bg]');
        if (bg && e.target === bg) {
          const closeName = 'close' + bg.dataset.closeBg;
          const closeFn = ACTION_REGISTRY[closeName];
          if (closeFn) closeFn();
        }
      });
      ```
- [ ] 8. **View-helper refactor: `emptyStateHero`** — param `ctaOnclick` → `ctaTab`, button emite `data-action="navTo" data-tab="${ctaTab}"`. Actualizar 6 callers:
      - L6820 → `'mnav-cartelera'`
      - L7722 → `'mnav-cartelera'`
      - L7724 → `'mnav-planner'`
      - L9169 → `_hasMiPlan?'mnav-miplan':'mnav-cartelera'`
      - L9193 → `'mnav-miplan'`
      - L9203 → `'mnav-seleccion'`
- [ ] 9. **View-helper refactor: `_posterThumb`** — eliminar param `onclickJs` + construcción `_oc`. Signature `(f, cssClass, loading)`. Ajustar 11 callers (10 quitan arg null, verificar los que pasan `loading` en 4ta posición → 3ra). L7788: reemplazar onclickJs por wrapper js-open-pel + data-title.
- [ ] 10. **Wave 1 — Grupos 1+2+3 (9 sites)**:
      - L2473 `if(event.target===this)closeAvSheet()` → `data-close-bg="AvSheet"`
      - L12110 `if(event.target===this)closeAuthSheet()` → `data-close-bg="AuthSheet"`
      - L2570 IIFE sec-prio → `data-action="scrollToAgSec" data-target="sec-prio"`
      - L2573 IIFE sec-int → `data-action="scrollToAgSec" data-target="sec-int"`
      - L2576 IIFE sec-yv → `data-action="scrollToAgSec" data-target="sec-yv"`
      - L9700/9701/9703/9704 Pattern N → `data-action="_openCombinedFilmSheet"` (data-film ya presente)
- [ ] 11. **Wave 2 — Grupos 6+7 (4 sites)** (Grupo 5 emptyStateHero ya en paso 8):
      - L7061 conditional → `data-action="${isDone?'toggleWatched':'markWatchedFromPlan'}"`
      - L5423 → `data-action="scrollToSuggestions"`
      - L7317 → `data-action="removeConflictModal"`
      - L12155 → `data-action="scrollToTop"`
- [ ] 12. **Wave 3 — Grupo 8 search-item (1 site)** (L4466 _posterThumb ya en paso 9):
      - L11915 search-item → `data-action="${f._isCortoItem?'searchOpenCorto':'searchOpenFilm'}"` + data-* (title, y para corto: country/dur/section/flags)
- [ ] 13. **⚠ QA BLOQUEANTE — 125 sites existentes ⚠** (R3, tras listener rewrite):
      - Browser: cargar festival, enumerar data-action únicos en DOM live, verificar 0 missing del registry
      - Click-test representativo por categoría A-G
      - P+S stopPropagation: click int-prio-btn (data-stop) → pel-sheet NO abre
      - Si CUALQUIER site regresa → **DETENER**, reportar, revisar rewrite
- [ ] 14. **Wave 4 — Grupo 4 Pattern H (2 sites)** — SOLO tras QA bloqueante PASSED:
      - L5461 js-open-pel wrapper → `data-stop="1"`
      - L5464 mplan-tc → `data-stop="1"`
      - Verificar: click en wrapper bloquea selectFromDetail del mplan-row ancestro
- [ ] 15. **Promote check `[event-delegation]` a FAIL** en validate.py: si onclick remaining > 0 → FAIL (era WARNING).
- [ ] 16. `python3 validate.py` → **26/26** (onclick=0 pasa el check FAIL-level). Verificar: 0 onclick, 97 entries, 0 typos.
- [ ] 17. `node --test tests/unit/*.test.js` → **131/131**
- [ ] 18. JS syntax check vía extracción + Function constructor → **OK**
- [ ] 19. **Functional equivalence (R2')** por grupo:
      - Grupo 1: click overlay background → cierra sheet; click contenido → no cierra
      - Grupo 2: click ag-sec-pill → scroll a sección
      - Grupo 3: click psp-card → abre combined film sheet (JSON.parse OK)
      - Grupo 4: click wrapper Pattern H → no triggerea selectFromDetail
      - Grupo 5: empty-state CTA → navega al tab correcto
      - Grupo 6: saved-check → toggleWatched (done) o markWatchedFromPlan (no done)
      - Grupo 7: scroll suggestions, remove conflict-modal, back-top
      - Grupo 8: search-item → searchClose + openPel/openCorto
- [ ] 20. Playwright skip local (run en CI)
- [ ] 21. Festival switch Tribeca↔Leviza atómico
- [ ] 22. ⚠ **QA BOOT PATH OBLIGATORIO** ⚠:
      - localStorage.clear() + reload + FILMS=0 → 0 errors
      - Click delegated en: scrollToAgSec, _openCombinedFilmSheet, navTo (emptyStateHero), search-item
      - 0 errors captured
- [ ] 23. Diff review:
      - Listener rewrite (loop manual)
      - 5 helpers + 6 entries + 1 fix + 2 view-helper refactors
      - 97 entries
      - 18 sites migrados → onclick = 0
      - Check promovido a FAIL
      - Cero cambios en signatures de funciones de dominio
- [ ] 24. `python3 validate.py` → 26/26 pre-commit
- [ ] 25. `node scripts/bump-version.js`
- [ ] 26. Commit atómico (mensaje según plan.md sección "Commit message draft")
- [ ] 27. Push + PR contra `main` con título `refactor(controller): event delegation wave 4 — final + listener rewrite, onclick=0 (p7c-4)`
- [ ] 28. Monitorear CI hasta verde — Playwright T01-T10 + T32 deben pasar
- [ ] 29. Merge squash + cleanup branch
