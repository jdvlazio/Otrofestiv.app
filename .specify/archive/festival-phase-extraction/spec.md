# Spec — Extracción de fase de festival (Fase 2)

## Problema

`_getFestivalPhase()` (index.html:6762, ~80 líneas) es una función god que
mezcla tres concerns en un solo árbol de decisión:

1. **Detección de fase**: en qué de las 5 fases estamos (ended / before /
   evening / between / next).
2. **Cómputo de stats derivados**: para `ended`, calcula `totalWatched`,
   `totalPlanned`, `pendingRatings` inline. Para `between`, filtra `FILMS`
   buscando una sugerencia de gap inline.
3. **Filtrado y clasificación**: para `next` / `between` / `evening`,
   parte el array de funciones de hoy en `done` / `active` / `future`.

Cada uno de esos concerns requiere conocer ~3-5 globals distintos. La
función completa lee ~10 globals (`FILMS`, `watched`, `savedAgenda`,
`filmRatings`, `DAY_KEYS`, `FESTIVAL_DATES`, `DEFAULT_DURATION_MIN`, `_simTime`,
indirectos: `simNow`, `festivalEnded`, `simTodayStr`, `screeningPassed`).

Está sin tests. Cualquier cambio a una de las 5 ramas requiere QA manual de
las 5 fases porque no hay forma de aislar el cambio.

## Causa raíz

La función creció orgánicamente añadiendo casos. Empezó probablemente como
"si terminó, muestra resumen; si no, muestra próxima función" — y se fueron
añadiendo `before`, `evening`, `between` con sus respectivas derivaciones de
datos inline. Ningún paso pidió descomponer.

## Solución — Fase 2

Descomponer `_getFestivalPhase()` en una orquestación delgada que llama a
tres helpers, manteniendo el shape de retorno byte-idéntico.

### 1. `_endedStats()` — stats post-festival
Firma: `() => { totalWatched, totalPlanned, pendingRatings }`
Extrae el bloque inline del branch `ended`.
Lee: `FILMS`, `watched`, `savedAgenda`, `filmRatings`.

### 2. `_classifyTodayScreenings(screenings, nowMin)` — partición temporal
Firma: `(screenings[], nowMin) => { done[], active[], future[] }`
Extrae los 3 `.filter()` que clasifican las funciones del día.
Pura modulo `parseDur` / `DEFAULT_DURATION_MIN`.

### 3. `_gapSuggestion(todayDay, gapFromMin, gapToMin)` — sugerencia para hueco
Firma: `(todayDay, gapFromMin, gapToMin) => Film | null`
Extrae el `FILMS.filter(...)[0]` inline del branch `between`.
Lee: `FILMS`, `watched`, `savedAgenda`. Llama: `screeningPassed`.

### 4. `_getFestivalPhase()` queda como thin composer
Mismo shape de retorno. Llama a los 3 helpers. Aprox 25 líneas en lugar de 80.

### 5. Contratos documentados
Cada helper + `_getFestivalPhase` con bloque de comentario nombrando globals
y supuestos, igual que Fase 1.

### 6. Tests
- `tests/unit/endedStats.test.js` — 4 casos
- `tests/unit/classifyTodayScreenings.test.js` — 5 casos
- `tests/unit/gapSuggestion.test.js` — 4 casos
- `tests/unit/getFestivalPhase.test.js` — 6 casos (uno por fase + null cases)

Total: 19 tests adicionales sobre los 18 de Fase 1.

## Criterios de aceptación

- [ ] `_endedStats`, `_classifyTodayScreenings`, `_gapSuggestion` extraídas
- [ ] `_getFestivalPhase` reescrita como composer thin (≤30 líneas)
- [ ] Shape de retorno byte-idéntico al actual (verificable por inspección
      manual + tests de regresión)
- [ ] Cada nueva función con bloque de contrato
- [ ] 19 tests unitarios pasando
- [ ] `python3 validate.py` 21/21 sin regresiones
- [ ] Playwright T01–T10 sin regresiones
- [ ] QA browser exhaustivo (las 5 fases):
    - [ ] `before` — usar Tribeca con `_simTime` previo al 3 de junio
    - [ ] `next` — Tribeca con `_simTime` ~30 min antes de un screening
    - [ ] `between` — Tribeca con `_simTime` en gap > 45 min
    - [ ] `evening` — Tribeca con `_simTime` post-última-función del día
    - [ ] `ended` — AFF 2026 archivado (festivalEnded = true)

## Fuera de alcance

- Tocar `festivalEnded()`, `simNow()`, `screeningPassed()`, `simTodayStr()`
  (utilities de tiempo — son su propia fase futura si vale la pena)
- Cambiar firma de `renderContextualHeader()`
- Refactorizar los inline `isPastDay` / `isToday` / `isNow` en render functions
- Worker — fase de festival es main-thread only, no requiere `_SCHED_PURE_FNS`
- Añadir `_getFestivalPhase` a `_SCHED_PURE_FNS` (innecesario)
