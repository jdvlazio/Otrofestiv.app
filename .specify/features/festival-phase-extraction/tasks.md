# Tasks — Festival Phase Extraction Fase 2

- [ ] 1. `python3 validate.py` → 21/21 antes de tocar nada (baseline limpio)
- [ ] 2. Crear branch `refactor/domain-extraction-p2`
- [ ] 3. Definir `_endedStats()` con contrato (~línea 6760)
- [ ] 4. Definir `_classifyTodayScreenings(screenings, nowMin)` con contrato
- [ ] 5. Definir `_gapSuggestion(todayDay, gapFromMin, gapToMin)` con contrato
- [ ] 6. Reescribir cuerpo de `_getFestivalPhase` como composer thin
- [ ] 7. Bloque de contrato actualizado sobre `_getFestivalPhase`
- [ ] 8. `tests/unit/endedStats.test.js` — 4 casos
- [ ] 9. `tests/unit/classifyTodayScreenings.test.js` — 5 casos
- [ ] 10. `tests/unit/gapSuggestion.test.js` — 4 casos
- [ ] 11. `tests/unit/getFestivalPhase.test.js` — 6 casos
- [ ] 12. Verificar `node --test tests/unit/*.test.js` corre en local — 0 fallos (37 tests totales)
- [ ] 13. Verificación JS syntax (script del SCHEMA checklist)
- [ ] 14. Diff review completo
- [ ] 15. QA browser — las 5 fases (manipular `_simTime` para `before`/`next`/`between`/`evening`; AFF para `ended`)
- [ ] 16. `python3 validate.py` → 21/21 antes del commit (sin regresión)
- [ ] 17. `node scripts/bump-version.js`
- [ ] 18. Commit atómico
