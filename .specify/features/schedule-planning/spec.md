# Spec — Subsistema de schedule planning (Fase 4)

## Problema

8 funciones forman el subsistema algorítmico del planner — son la última
pieza grande de la capa Model sin contratos ni tests:

- `isScreeningBlocked(s)` — filtro de availability blocks del usuario
- `_djb2(str)`, `_titleSeed(titles)`, `_mulberry32(seed)` — utilities de RNG determinista
- `shuffle(arr, rand)` — Fisher-Yates con rand opcional
- `scoreFilm(title, screens, isPriority, allTitles)` — heurística de scoring por película
- `sortScreensByStrategy(screens, allGroups)` — interval scheduling (menos conflictos + EFT)
- `computeScenarios(titles)` — ~190 líneas, MRV + branch-and-bound, 3 fases de generación, retorna hasta 8 escenarios

`computeScenarios` consume todos los demás. Es el corazón del Planner —
cualquier regresión aquí rompe la experiencia central del producto. Hoy:
sin tests, sin contratos, validado solo via QA visual.

## Causa raíz

Crecieron junto con el algoritmo. El comment de "FIX CRÍTICO — NO REMOVER
(Apr 2026)" sobre `MAX_NODES_PER_CALL` es evidencia de que ha habido
regresiones graves en el pasado (desktop vs mobile producían outputs
distintos). Tests propios habrían atrapado eso antes de que llegara a
producción.

## Hallazgo crítico — `computeScenarios` NO es determinístico

El algoritmo usa `shuffle(baseGroups)` SIN pasar `rand` en sus 3 fases de
generación de escenarios → cae a `Math.random` por default → mismo input
produce outputs distintos entre runs. Esto es **intencional** (UX: random
restarts dan diversidad de escenarios).

La infraestructura para determinismo existe (`_titleSeed` + `_mulberry32`
+ `shuffle` con `rand` opcional), pero NO se usa en `computeScenarios`
por design.

**Implicación**: tests de `computeScenarios` son **property-based**
(invariantes que todo output válido cumple) — no exact-match.

## Solución — Fase 4

Mismo patrón que Fase 1–3 para los 7 helpers (contratos + tests exactos).
Para `computeScenarios`: contrato detallado + 5 property tests sobre
invariantes algorítmicas.

### Funciones cubiertas

1. `isScreeningBlocked(s)` — 3 casos
2. `_djb2(str)` — 2 casos (determinismo de hash)
3. `_titleSeed(titles)` — 2 casos (order-independence vía sort)
4. `_mulberry32(seed)` — 2 casos (mismo seed → misma secuencia, output en `[0, 1)`)
5. `shuffle(arr, rand)` — 3 casos (length preservada, con seeded rand determinista)
6. `scoreFilm(title, screens, isPriority, allTitles)` — 5 casos (priority +100, single +40, dos +20, sola en sección +15, dur >150 +10)
7. `sortScreensByStrategy(screens, allGroups)` — 4 casos (menos conflictos primero, EFT tiebreak)
8. `computeScenarios(titles)` — 5 property tests sobre invariantes

## Criterios de aceptación

- [ ] Bloque de contrato sobre cada una de las 8 funciones
- [ ] `tests/unit/isScreeningBlocked.test.js` — 3 casos
- [ ] `tests/unit/djb2.test.js` — 2 casos
- [ ] `tests/unit/titleSeed.test.js` — 2 casos
- [ ] `tests/unit/mulberry32.test.js` — 2 casos
- [ ] `tests/unit/shuffle.test.js` — 3 casos
- [ ] `tests/unit/scoreFilm.test.js` — 5 casos
- [ ] `tests/unit/sortScreensByStrategy.test.js` — 4 casos
- [ ] `tests/unit/computeScenarios.test.js` — 5 property tests
- [ ] `tests/lib/load-domain.js` — `DEFAULT_FNS` extendido con las 8 nuevas
- [ ] `node --test tests/unit/*.test.js` — 26 tests nuevos, 84 totales
- [ ] `python3 validate.py` 21/21 sin regresiones
- [ ] QA browser: Planear genera escenarios coherentes en Tribeca con watchlist real
- [ ] QA browser específico: verificar conflict-free invariant en console sobre escenarios reales
- [ ] Commit atómico

## Fuera de alcance — explícito

- Forzar determinismo en `computeScenarios` (cambia UX de random restarts, fuera de scope)
- `getSuggestions()` (~70 líneas adyacentes a partir de línea 5940) — main-thread only, no en `_SCHED_PURE_FNS`. Registrada como deuda en plan.md.
- Refactorizar las closures internas de `computeScenarios` (`findMax`, `collectAt`, `dayBalance`) — son local scope, no son funciones top-level. Mover a top-level cambia el contrato del worker.
- Cambiar firmas para recibir state por parámetro (Fase 5)
- Mover funciones a archivos `js/` separados (Fase 8)
