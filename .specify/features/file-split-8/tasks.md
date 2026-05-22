# Tasks — File Split / ES Modules nativos (Fase 8)

> **Scope**: split de index.html (~12k líneas) en módulos ES nativos, 8 waves
> en orden topológico (DAG §12 acíclico verificado). Relocación, no reescritura
> (excepción: eliminar mirror de globals D-INFRA-4). Post-Tribeca.
>
> **Prerequisitos resueltos**: D-INFRA-1 a 5 (FASE8-INFRA §8), DAG (§12),
> D8-1 (bridge global temporal), D8-2 (test migration por wave), D8-3 (sub-split
> evaluar al llegar), worker access (decidir en Wave 2).
> **Estado**: todo cerrado. Ejecución NO arranca hasta post-Tribeca.

## Fase 0 — Pre-flight

- [ ] 1. `python3 validate.py` baseline + `node --test tests/unit/*.test.js` → 141
- [ ] 2. Crear branch `refactor/file-split-8`
- [ ] 3. D8-1/2/3 ya cerradas (ver spec). Confirmar al arrancar: bridge global
      (A), test migration por wave, sub-split evaluado al llegar.
- [ ] 4. **ESM test setup**: decidir `.mjs` vs subdirectorio con package.json
      `"type":"module"` (NO poner `"type":"module"` en el root — rompe scripts/)
- [ ] 5. Convertir `<script>` grande → `<script type="module" src="/src/main.js">`
      + `src/main.js` placeholder (estrategia bridge si D8-1=A)
- [ ] 6. QA browser PRE: trap de errors + festival cargado + baseline

## Wave 1 — `src/config.js` (leaf)
- [ ] 7. Crear `src/config.js`. Mover FESTIVAL_CONFIG, constantes, BUILD_VERSION.
      Export. Bridge `window.*` temporal (D8-1=A).
- [ ] 8. validate + Playwright verde

## Wave 2 — `src/domain/{schedule,time,film,festival}.js`
- [ ] 9. Crear `src/domain/`. Mover 22 fns unit-tested + 15 _SCHED_PURE_FNS +
      helpers puros, agrupadas por archivo (schedule/time/film/festival).
      import config. Export todo.
- [ ] 10. **Decidir worker access** (R3): module worker vs copia worker-local.
- [ ] 11. **Migrar los 22 unit tests** a import directo (D-INFRA-5):
      `loadDomain({...})` → `import { fn } from '../../src/domain/x.js'`
- [ ] 12. validate + 141 tests + Playwright verde

## Wave 3 — `src/state/state.js` [elimina mirror — D-INFRA-4]
- [ ] 13. Crear `src/state/state.js`. Mover el container (STATE MIRROR block).
      Export `state`.
- [ ] 14. **Eliminar mirror** (_MIRROR_TARGETS/_MIRROR_READERS + let globals).
      El container posee `_data`. Bridge `Object.defineProperty` temporal para
      reads legacy (`window.watchlist` → `state.get('watchlist')`), eliminado
      conforme cada capa migra sus reads. ⚠ EL CAMBIO MÁS DELICADO — sub-plan.
- [ ] 15. Migrar `state.test.js` a import directo (elimina sandbox 19 globals).
      Verificar que los tests de subscribeRender/transaction/dedup siguen verde.
- [ ] 16. validate + tests + Playwright verde

## Wave 4 — `src/storage/storage.js`
- [ ] 17. Crear `src/storage/storage.js`. Mover storage adapter + saveX/loadState.
      import state, config. Export.
- [ ] 18. Migrar `storage.test.js` a import. validate + tests + Playwright verde

## Wave 5 — `src/i18n/i18n.js`
- [ ] 19. Crear `src/i18n/i18n.js`. Mover t(), _applyI18nDOM, carga de JSONs.
      (setLang NO — es controller.) import state, config. Export.
- [ ] 20. validate + tests + Playwright verde

## Wave 6 — `src/view/{programa,agenda,miplan,sheets,components}.js`
- [ ] 21. Crear `src/view/`. Mover render* + sheets + components + surgical
      patches (updateCardState, updateAgTab, _reRenderIntereses,
      updateHorarioPrioBtn, updateRatingStars). import domain, state, i18n,
      config. Export lo que controller consume.
- [ ] 22. Sub-split por archivo según tamaño (D8-3). Mapear sub-DAG (R2).
- [ ] 23. Migrar reads de globals a state.get (Wave 3 bridge cleanup parcial).
- [ ] 24. validate + tests + Playwright verde

## Wave 7 — `src/controller/{registry,pipeline,handlers}.js`
- [ ] 25. Crear `src/controller/`. Mover handlers + ACTION_REGISTRY + listener +
      composite helpers + RENDER PIPELINE + renderActiveView + runCalc + setLang.
      import view, state, domain, storage, i18n. Export para main.
- [ ] 26. Pipeline + listener como `init*()` exports (no side effects al import — R5).
- [ ] 27. validate + tests + Playwright verde

## Wave 8 — `src/main.js` + cleanup
- [ ] 28. `src/main.js`: bootstrap (DOMContentLoaded, loadFestival inicial,
      initPipeline(), initListener(), SW register). Orden de init explícito (R4).
- [ ] 29. **Eliminar todos los bridges `window.*`** (D8-1) — todo es módulo.
- [ ] 30. index.html → shell puro (head, divs críticos, `<script type="module">`).
- [ ] 31. `sw.js`: añadir regla network-first `/src/` (D-INFRA-1=B).
- [ ] 32. `playwright.yml` paths + `src/**`; `bundle.yml` + `cp -r src/. www/src/`.

## Validación final
- [ ] 33. `python3 validate.py` (multi-file adaptado) → verde
- [ ] 34. `node --test tests/unit/*.test.js` → 141 (import directo)
- [ ] 35. JS syntax: `node --check src/**/*.js`
- [ ] 36. Functional equivalence: app idéntica (todas las vistas + flujos)
- [ ] 37. **QA Boot Path obligatorio**: localStorage.clear + reload + FILMS=0 → 0 errors
- [ ] 38. Festival switch atómico
- [ ] 39. Playwright T01-T10 + T32 verde en CI
- [ ] 40. **QA device iOS + Android (D-INFRA-3)**: app carga, OTA propaga,
      SW reload jala módulos nuevos. ⚠ BLOQUEANTE pre-prod nativo.

## Deploy + merge
- [ ] 41. Diff review completo
- [ ] 42. `node scripts/bump-version.js`
- [ ] 43. Commit(s) por wave / PR(s) — granularidad por wave (decisión con Juan)
- [ ] 44. Monitorear CI verde
- [ ] 45. **Deploy coordinado** (R7): primer deploy multi-file sube `src/` +
      index.html (no drag-and-drop de 1 archivo)
- [ ] 46. Merge + cleanup branch

> Nota: dado el tamaño, considerar PR por wave (cada uno verificable + Playwright)
> en vez de un PR gigante. El primer deploy multi-file requiere coordinación.
