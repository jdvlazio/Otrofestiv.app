# Tasks — Festival Phase Extraction Fase 2

- [x] 1. `python3 validate.py` → 21/21 antes de tocar nada (baseline limpio)
- [x] 2. Crear branch `refactor/domain-extraction-p2`
- [x] 3. Definir `_endedStats()` con contrato (~línea 6760)
- [x] 4. Definir `_classifyTodayScreenings(screenings, nowMin)` con contrato
- [x] 5. Definir `_gapSuggestion(todayDay, gapFromMin, gapToMin)` con contrato
- [x] 6. Reescribir cuerpo de `_getFestivalPhase` como composer thin
- [x] 7. Bloque de contrato actualizado sobre `_getFestivalPhase`
- [x] 8. `tests/unit/endedStats.test.js` — 4 casos
- [x] 9. `tests/unit/classifyTodayScreenings.test.js` — 5 casos
- [x] 10. `tests/unit/gapSuggestion.test.js` — 4 casos
- [x] 11. `tests/unit/getFestivalPhase.test.js` — 6 casos
- [x] 12. Verificar `node --test tests/unit/*.test.js` corre en local — 0 fallos (37 tests totales)
- [x] 13. Verificación JS syntax (script del SCHEMA checklist)
- [x] 14. Diff review completo
- [x] 15. QA browser — las 5 fases (manipular `_simTime` para `before`/`next`/`between`/`evening`; AFF para `ended`)
- [x] 16. `python3 validate.py` → 21/21 antes del commit (sin regresión)
- [x] 17. `node scripts/bump-version.js`
- [x] 18. Commit atómico
