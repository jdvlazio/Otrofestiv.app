# Spec — Subsistema temporal (Fase 3)

## Problema

6 funciones temporales participan en ~107 callsites en `index.html` y son
foundational para Fases 1 y 2 (que las stub-ean en sus tests por falta
de cobertura directa):

- `_festDate(dateStr, time)` — construye Date con `TZ_OFFSET` explícito
- `simNow()` — Date controlable vía `_simTime`
- `simTodayStr()` — YYYY-MM-DD local de simNow
- `festivalEnded()` — `simNow() > FESTIVAL_END`
- `screeningPassed(s)` — con gate de festivalEnded y 10 min de grace
- `dayFullyPassed(day)` — última función del día + 10 min de grace

Sin contratos documentados ni tests propios. Cualquier cambio sutil rompe
planning, render contextual, agenda, sugerencias. Fase 2 tuvo que stub-ear
`screeningPassed` en `gapSuggestion.test.js` precisamente porque no había
forma de testearla directamente.

## Causa raíz

Crecieron orgánicamente desde el inicio del proyecto. Nunca tuvieron su
capa de tests. Tres de ellas (`_festDate`, `screeningPassed`) ya están en
`_SCHED_PURE_FNS` (worker las consume vía `.toString()`), las otras tres
(`simNow`, `festivalEnded`, `simTodayStr`) tienen estados híbridos: `simNow`
y `festivalEnded` están **duplicadas** en worker scope con globals de
nombres distintos (`SIM_TIME`/`FESTIVAL_END_TS` vs `_simTime`/`FESTIVAL_END`),
artefacto del mecanismo `.toString()`. `simTodayStr` y `dayFullyPassed` son
main-thread only.

## Solución — Fase 3

Mismo patrón que Fase 1+2: cada función recibe bloque de contrato
documentando globals leídos y supuestos, y queda cubierta con unit tests
propios. **Cero cambios de firma. Cero callsites tocados.**

La duplicación worker de `simNow`/`festivalEnded` se preserva por ahora —
es artefacto del worker actual, y queda resuelta en Fase 8 del destino
(ver `docs/ARQUITECTURA.md` sección 16). Fase 3 documenta y testea las
versiones main-thread.

## Criterios de aceptación

- [ ] Bloque de contrato sobre cada una de las 6 funciones documentando globals leídos, dependencias y supuestos
- [ ] `tests/unit/festDate.test.js` — 3 casos
- [ ] `tests/unit/simNow.test.js` — 3 casos
- [ ] `tests/unit/simTodayStr.test.js` — 3 casos
- [ ] `tests/unit/festivalEnded.test.js` — 3 casos
- [ ] `tests/unit/screeningPassed.test.js` — 5 casos (incluye gate de festivalEnded + grace de 10 min)
- [ ] `tests/unit/dayFullyPassed.test.js` — 4 casos
- [ ] `tests/lib/load-domain.js` — `DEFAULT_FNS` extendido con las 6 nuevas
- [ ] `node --test tests/unit/*.test.js` — 21 tests nuevos, 58 totales pasando
- [ ] `python3 validate.py` 21/21 sin regresiones
- [ ] QA browser: Mi Plan funciona en Tribeca (smoke test)
- [ ] QA browser: `simTodayStr()` con `_simTime` explícito retorna YYYY-MM-DD correcto
- [ ] Commit atómico

## Fuera de alcance — explícito

- Eliminar la duplicación worker de `simNow`/`festivalEnded` (Fase 8 del destino MVC)
- Mover funciones a archivos `js/` separados (Fase 8)
- Cambiar firmas para recibir state por parámetro (Fase 5)
- Refactorizar `_festDate` para no depender de `TZ_OFFSET` global (Fase 5)
- Tocar `isNowShowing` u otras funciones tiempo-adyacentes no listadas
