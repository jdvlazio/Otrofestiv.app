# Tasks — Prio strip 3 estados (Planear)

Diseño aprobado por PO. Estados: 1 intención (pre-cálculo) · 2 resolución (post) · 3 stale.

- [x] 1. Validar arquitectura contra código real; resolver D1–D6
       D3 confirmado (sin modal+navegación al quitar in-strip). Sentinel para no
       nular/recalcular cachedResult en toggles de prioridad. Snapshot para stale.
- [x] 2. i18n: 7 strings (prio_corpus_pre/post, prio_in/out, prio_stale_banner/cta,
       prio_past) en src/i18n/i18n.js (es+en) + es.json + en.json + strings-reference.json.
       EN como draft pendiente aprobación final PO.
- [x] 3. CSS (index.html): .prio-corpus, .prio-chip-res(.in/.out), .resolved-out dimmed,
       .prio-chip-past-lbl, .prio-stale(+cta), #ag-result-wrap.stale — solo tokens+ICONS existentes.
- [x] 4. renderPrioStrip(state,{mode,included}): intent (quitar) / resolved / past.
       Estado 2 REDISEÑADO (overlays en póster rechazados): dos grupos "Entró"/"No
       entró" separados por .hr-bdr, cada uno con .group-label (SVG + texto). Chips
       Entró: título en var(--gray); No entró: opacity .4. Sin nada dentro del póster.
- [x] 5. renderAgenda Estado B: línea de corpus + ruteo 1/2/3 + banner stale + result-wrap .stale.
- [x] 6. calc.js: cachedResult._prioSnapshot (worker + sync); runCalc → renderAgenda
       (re-render completo del Planear, dispara Estado 2).
- [x] 7. pipeline.js: sentinel _preserveResult / _markPreserveResult en renderActiveView.
- [x] 8. handlers.js: togglePriority setea sentinel; eliminado modal+navigate (D3).
- [x] 9. validate.py — 28/29 OK (warning único = tasks-sync pre-existente).
- [x] 10. Chrome live audit ES + EN — Estados 1/2/3 + transición Recalcular.
       Estado 2 rediseñado verificado: grupos Entró/No entró, .hr-bdr, chip dimmed en
       No entró, label ok=green / fail=gray2, 0 overlays. "No entró" forzado simulando
       exclusión (data del festival no generaba conflicto real con screenings alternos).
- [x] 11. Copy EN aprobado como group-labels (In/Out) en el rediseño.
- [x] 12. bump-version + commit + PR.
