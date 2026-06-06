# Plan técnico — Fase 2

## Restricciones de partida

### R1. Single-file en producción
Mismo invariante de Fase 1. Toda función nueva vive en `index.html`.

### R2. Sin worker
A diferencia de Fase 1, `_getFestivalPhase` es main-thread only.
NO se añade nada a `_SCHED_PURE_FNS`.

### R3. Shape de retorno preservado byte-a-byte
`renderContextualHeader()` (único caller) hace destructuring contra todos
los campos del objeto retornado. Si cambia algún field name, rompe el
render. La descomposición es interna; el shape externo es contrato.

## Cambios en index.html

### Inserciones nuevas — orden de declaración

Function declarations son hoisted, pero por legibilidad insertamos los
helpers ANTES de `_getFestivalPhase`. Ubicación: línea ~6760, justo antes
del `function _getFestivalPhase(){`.

1. `_endedStats()` — ~5 líneas
2. `_classifyTodayScreenings(screenings, nowMin)` — ~10 líneas
3. `_gapSuggestion(todayDay, gapFromMin, gapToMin)` — ~12 líneas

Cada una precedida por bloque de contrato (4-6 líneas).

### Reescritura de `_getFestivalPhase`

El cuerpo entero (líneas 6762-6841, ~80 líneas) se reescribe como un
composer thin que delega los 3 cómputos. Aprox 25 líneas resultantes.

### Sin cambios en

- `renderContextualHeader()`
- `simNow()`, `festivalEnded()`, `simTodayStr()`, `screeningPassed()`
- Ningún otro callsite

## Tests — diseño

### Reutiliza infraestructura de Fase 1

`tests/lib/load-domain.js` ya existe y soporta inyección de globals
arbitrarios. No requiere cambios.

### Globals a inyectar para los nuevos tests

- `FILMS[]` (array de fixtures)
- `watched` (Set)
- `savedAgenda` ({schedule: [...]})
- `filmRatings` ({})
- `DAY_KEYS[]`, `FESTIVAL_DATES{}`
- `DEFAULT_DURATION_MIN: 90`
- `_simTime` (timestamp para controlar simNow)

### Casos cubiertos

`_endedStats`:
- watched vacío → 0/0/0
- 2 films watched, 1 con rating → totalWatched=2, pendingRatings=1
- savedAgenda con 3 screenings → totalPlanned=3
- Cortos y events NO cuentan en totalWatched

`_classifyTodayScreenings`:
- Array vacío → {done:[], active:[], future:[]}
- 3 screenings antes de nowMin → todas en done
- 1 en curso, 1 pasada, 1 futura → repartidas correctamente
- Edge: screening que termina exactamente en nowMin → done
- Screening sin duration → usa DEFAULT_DURATION_MIN

`_gapSuggestion`:
- Sin films del día disponibles → null
- 1 film que cabe en gap → retorna ese film
- Film ya watched → excluida
- Film en savedAgenda → excluida (no se sugiere lo ya planeado)

`_getFestivalPhase` (integración con los helpers):
- festivalEnded=true → phase:'ended' con stats correctos
- savedAgenda vacío → null
- now < FESTIVAL_START → phase:'before' con daysDiff
- Día con screenings, sin active/future → phase:'evening'
- Próxima función en ≤ 45 min → phase:'next'
- Gap > 45 min → phase:'between' con gapSuggestion

## QA browser — receta de `_simTime` por fase

`_simTime` es un `let` mutable a nivel módulo (línea 4679 en index.html).
`null` = tiempo real. Cualquier string ISO o timestamp lo sobreescribe.
`applySimTime(val)` también lo setea (vía slider math), pero para QA es
más directo asignar `_simTime` desde DevTools console.

### Pre-requisito común para `next`/`between`/`evening`/`before`

`_getFestivalPhase()` retorna `null` si `savedAgenda.schedule` está vacío.
Antes de las pruebas:

1. Selector → **Tribeca 2026**
2. Añadir 3–4 películas a watchlist en al menos 2 días distintos
   (recomendado: días 5 y 6 de junio para tener cobertura de `between` + `evening`)
3. Generar plan (Planear → Calcular) para que `savedAgenda` se popule

### Recetas por fase (DevTools Console)

```js
// Resetear a tiempo real
_simTime = null; renderAgenda();
```

**`ended`** — sin manipular `_simTime`:
- Cambiar selector a **AFF 2026** (archivado). `festivalEnded()` retorna true por tiempo real.

**`before`** — Tribeca, antes del 3 de junio:
```js
_simTime = '2026-06-01T10:00:00'; renderAgenda();
```

**`next`** — Tribeca, ~30 min antes de la próxima función planeada:
```js
// Reemplazar con un timestamp 30 min antes de un screening real del plan.
// Ejemplo: si tenés screening a las 5:00 PM el Jun 5:
_simTime = '2026-06-05T16:30:00'; renderAgenda();
```

**`between`** — Tribeca, EN un hueco > 45 min entre dos funciones planeadas:
```js
// Requiere: 2 screenings mismo día con > 45 min de gap entre fin del 1° e inicio del 2°.
// Setear _simTime DENTRO de ese gap. Ejemplo:
_simTime = '2026-06-05T17:00:00'; renderAgenda();
```

**`evening`** — Tribeca, después de la última función del día pero antes de medianoche:
```js
_simTime = '2026-06-05T23:30:00'; renderAgenda();
```

### Qué verificar en cada fase

- `before`: panel muestra "Faltan X días", X concuerda con `daysDiff`
- `next`: panel muestra próxima función + countdown coherente con `minsUntil`
- `between`: panel muestra hueco con `gapMin` correcto + sugerencia si hay una film que cabe
- `evening`: panel muestra "resumen del día" o equivalente con `todayScreenings` y `todayWatched`
- `ended`: panel muestra `totalWatched`/`totalPlanned`/`pendingRatings`

### Setup de UI sim panel (alternativa visual)

Si preferís UI en vez de console:
```js
document.body.insertAdjacentHTML('beforeend', renderSimPanel());
```
Aparece un slider al fondo de la página. 0 = inicio del festival, 1000 = fin.
`renderSimPanel()` existe pero no se invoca en ningún render path — es
herramienta dev.

## CI

Sin cambios. `node --test tests/unit/*.test.js` ya cubre los nuevos.

## Riesgos

| Riesgo | Mitigación |
|---|---|
| Shape de retorno cambia sutilmente (field name typo, orden de propiedades observable, etc.) | Tests de `_getFestivalPhase` validan el shape completo, no solo el campo `phase`. Diff manual cuidadoso del composer reescrito. |
| Helpers tienen comportamiento sutilmente distinto del código inline original | Tests por cada helper. Riesgo real está en `_classifyTodayScreenings` (los `.filter` originales tienen edge cases con `s.duration` undefined / `parseInt`). Replicar EXACTAMENTE la lógica. |
| Test del `between` phase es sensible al `_simTime` injection — fixture debe ser cuidadoso | Fixture explícito con `_simTime` que cae justo en un gap conocido. |
| QA browser con 5 fases distintas requiere manipular `_simTime` en runtime | Recetas documentadas arriba. El simTime mecanismo ya existe (`applySimTime`, slider en `renderSimPanel`). |

## Deuda futura

- `festivalEnded()`, `simNow()`, `simTodayStr()`, `screeningPassed()` — formalizar
  como subsistema temporal con tests propios. Hoy son worker-local-duplicated.
- Inline `isPastDay`/`isToday`/`isNow` en render functions — candidatos para
  Fase 3 si decidimos perseguir descomposición de render.
- `renderSimPanel()` no tiene UI entry point en la app — solo se invoca desde
  console. Considerar añadir un toggle dev oculto si el QA browser de fases se
  vuelve recurrente.
