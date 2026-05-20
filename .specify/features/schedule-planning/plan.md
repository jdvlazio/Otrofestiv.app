# Plan técnico — Fase 4

## Restricciones de partida

### R1. Single-file en producción
Mismo invariante de Fases 1–3. La descomposición física a archivos
separados es Fase 8 del destino.

### R2. Worker preservado
Las 8 funciones ya están en `_SCHED_PURE_FNS` (línea 8234) — el worker
las consume vía `.toString()`. **No tocar firmas, no tocar cuerpos** —
cualquier cambio sutil afecta el worker. Fase 4 añade solo comentarios
de contrato sobre las definiciones main-thread.

### R3. Globals como contrato implícito
Mismo modelo. Tests inyectan los globals vía `loadDomain({ globals: ... })`.

### R4. Property tests para `computeScenarios`
Por la no-determinismo intencional del algoritmo (random restarts en las
3 fases de generación), los tests validan **invariantes** que cualquier
output válido cumple:
- Cada escenario es internally conflict-free
- `excluded ∩ included = ∅` y `excluded ∪ included = pending`
- `scenario.schedule.length ≤ trueMax`
- Cuando todas las películas son compatibles, todas aparecen en cada escenario
- Empty pending → `[]`

Tests con fixtures pequeñas (3–5 films) para mantener velocidad y reducir
chance de hit del `MAX_NODES_PER_CALL=80000` cap.

### R5. Determinismo donde aplica
`_djb2`, `_titleSeed`, `_mulberry32` SÍ son determinísticas. Tests exactos.
`shuffle` con `rand` proporcionado SÍ es determinística. Tests exactos.

## Cambios en index.html

Cero cambios de firma, cero cambios de cuerpo, cero callsites tocados.
**Solo bloques de comentario** sobre cada una de las 8 funciones.

### Ubicaciones de los contratos

| Función | Línea actual | Bloque de contrato a documentar |
|---|---:|---|
| `isScreeningBlocked` | 5668 | Lee `availability` global. Llama `toMin`, `parseDur`. Solapamiento estricto (`sStart < bTo && sEnd > bFrom`). |
| `_djb2` | 5676 | Pura. Hash determinístico (5381 seed, `Math.imul(31, h) + charCode` step). |
| `_titleSeed` | 5681 | Pura. Hace `[...titles].sort().join('|')` — order-independent sobre el set. Llama `_djb2`. |
| `_mulberry32` | 5684 | Pura. Closure factory: retorna una función PRNG. Output en `[0, 1)`. Mismo seed → misma secuencia infinita. |
| `shuffle` | 5693 | Pura cuando `rand` se proporciona; impure con `Math.random` por default. Fisher-Yates. NO muta input (clona con `[...arr]`). |
| `scoreFilm` | 5702 | Lee `FILMS` global (para chequeo de section uniqueness). Heurística de 4 factores aditivos. |
| `sortScreensByStrategy` | 5728 | Llama `screensConflict`, `toMin`, `parseDur`. NO muta input (clona con `[...screens]`). Interval scheduling. |
| `computeScenarios` | 5750 | Lee `watched`, `prioritized`, `FILMS`, indirecto `savedAgenda`, `availability`. Algoritmo: MRV + branch-and-bound con `MAX_NODES_PER_CALL=80000`. NO determinístico por design. Documentar el FIX CRÍTICO de Apr 2026 sobre el cap. |

## Cambios en tests/lib/load-domain.js

Extender `DEFAULT_FNS` con las 8 funciones nuevas:

```js
const DEFAULT_FNS = [
  // Fase 1, 2, 3 (already present)
  ...
  // Fase 4 — schedule planning
  'isScreeningBlocked', '_djb2', '_titleSeed', '_mulberry32',
  'shuffle', 'scoreFilm', 'sortScreensByStrategy', 'computeScenarios',
];
```

## Tests — diseño

### Estructura

```
tests/unit/
  isScreeningBlocked.test.js   ← 3 casos
  djb2.test.js                 ← 2 casos
  titleSeed.test.js            ← 2 casos
  mulberry32.test.js           ← 2 casos
  shuffle.test.js              ← 3 casos
  scoreFilm.test.js            ← 5 casos
  sortScreensByStrategy.test.js ← 4 casos
  computeScenarios.test.js     ← 5 property tests
```

Total: 26 tests nuevos. Suite combinada: 84 tests.

### Casos por función

`isScreeningBlocked(s)`:
- `availability[s.day]` undefined → false
- Block que solapa con screening → true
- Block adyacente sin overlap → false

`_djb2(str)`:
- String vacío → returns 5381 (initial seed)
- Mismo input → mismo hash (determinismo)

`_titleSeed(titles)`:
- Order-independent: `_titleSeed(['B','A']) === _titleSeed(['A','B'])`
- Mismo array → mismo seed

`_mulberry32(seed)`:
- Mismo seed → mismas dos primeras llamadas
- Output siempre en `[0, 1)` para 10 llamadas

`shuffle(arr, rand)`:
- Length preservada
- Con `rand` que retorna 0 siempre → no swap (output = input)
- Sin `rand` → output es array no-vacío del mismo length (no exact match)

`scoreFilm(title, screens, isPriority, allTitles)`:
- `isPriority=true` agrega 100
- `screens.length === 1` agrega 40
- `screens.length === 2` agrega 20
- Única en su sección (no hay siblings en `allTitles` con misma sección) agrega 15
- Duración del primer screening > 150 agrega 10

`sortScreensByStrategy(screens, allGroups)`:
- Screen con menos conflictos viene primero
- Con tie en conflictos, screen que termina antes viene primero (EFT)
- Screen sola: ordenamiento trivial sin throw
- Idempotencia: ordenar dos veces el mismo array da el mismo resultado

`computeScenarios(titles)` — property tests:
1. Empty pending (todas en `watched`) → returns `[]`
2. Para cada escenario en output: ningún par de screenings cumple `screensConflict()`
3. Para cada escenario: `scenario.schedule.length <= scenario.trueMax`
4. Para cada escenario: `excluded ∩ included(_title from schedule) = ∅` y union = `titles`
5. Watchlist sin conflictos posibles → todas las películas en cada escenario

### Globals inyectados (helper común)

```js
function loadPlanner(opts = {}) {
  return loadDomain({
    globals: {
      FILMS: opts.FILMS || [],
      watched: opts.watched || new Set(),
      prioritized: opts.prioritized || new Set(),
      availability: opts.availability || {},
      savedAgenda: opts.savedAgenda || null,
      FESTIVAL_BUFFER: 15,
      FESTIVAL_TRANSPORT: 'transit',
      FESTIVAL_CONFIG: opts.FESTIVAL_CONFIG || { test: { venues: {} } },
      _activeFestId: 'test',
      DEFAULT_DURATION_MIN: 90,
      // Stub time funcs — los tests no necesitan tiempo real
      _simTime: opts._simTime || null,
      FESTIVAL_END: opts.FESTIVAL_END || new Date('2099-01-01'),
    },
  });
}
```

## QA browser

### Receta para paso 23 (smoke)

1. `python3 -m http.server 3000` → abrir `127.0.0.1:3000` en mobile viewport
2. Selector → **Tribeca 2026**
3. Añadir 5–6 películas a watchlist (al menos 2 con conflicto de horario)
4. Ir a tab **Planear** → click "Calcular"
5. Verificar:
   - El panel renderiza entre 1 y 8 escenarios
   - Cada escenario tiene su día/hora visible
   - No hay error en Console

### Receta para paso 24 (verificación específica)

En DevTools Console:
```js
// Obtener los escenarios calculados (cache en _planScenarios o similar)
const scenarios = _planScenarios || [];
console.log('Total scenarios:', scenarios.length);

// Verificar invariant: cada escenario es internally conflict-free
const violations = [];
scenarios.forEach((sc, i) => {
  const schedule = sc.schedule;
  for (let a = 0; a < schedule.length; a++) {
    for (let b = a + 1; b < schedule.length; b++) {
      if (screensConflict(schedule[a], schedule[b])) {
        violations.push({ scenario: i, a: schedule[a]._title, b: schedule[b]._title });
      }
    }
  }
});
console.log('Conflict violations:', violations.length);
console.assert(violations.length === 0, 'Expected zero conflicts within each scenario');
```

Output esperado: `Conflict violations: 0`.

## CI

Sin cambios — `node --test tests/unit/*.test.js` ya cubre los nuevos archivos automáticamente.

## Riesgos

| Riesgo | Mitigación |
|---|---|
| `computeScenarios` no-determinístico → tests inestables | Property tests sobre invariantes, no sobre outputs específicos. Pasan en cualquier corrida válida. |
| `MAX_NODES_PER_CALL=80000` se hitea con fixtures grandes | Fixtures de 3–5 films máximo en tests. |
| `loadPlanner` helper acumula muchos globals — frágil si alguno se renombra | Helper centralizado en un solo lugar; si un global se renombra, un solo punto a actualizar. |
| Property test "cada escenario conflict-free" tarda mucho con muchos escenarios | Fixtures pequeñas garantizan ≤ 8 escenarios × ≤ 5 films cada uno → 28 pares max por escenario × 8 = 224 chequeos. Negligible. |
| Worker rompe porque alguna función cambia | Cero cambios de cuerpo o firma — solo comentarios. Worker tiene cero exposure. |

## Deuda futura

- **`getSuggestions()`** (línea 5940, ~70 líneas) — main-thread only, no está en
  `_SCHED_PURE_FNS`. Adjacente al subsistema de planning pero su rol es distinto
  (recuperación y descubrimiento POST-agenda guardada). Candidata para una fase
  4.5 con su propio spec/tests si se valida que es high-leverage. Lee globals:
  `savedAgenda`, `watched`, `watchlist`, `lastRemovedSlots`, `DAY_KEYS`,
  `FILMS`, `FESTIVAL_BUFFER`.
- **Closures internas de `computeScenarios`** (`findMax`, `collectAt`,
  `dayBalance`) — son local scope. Promoverlas a top-level cambiaría el
  contrato del worker (más funciones a serializar). Considerar en Fase 8 cuando
  se elimine la serialización `.toString()`.
- **Forzar determinismo en `computeScenarios`** usando `_titleSeed(titles)` +
  `_mulberry32` en lugar de `Math.random`. Cambio de UX (los usuarios verían
  siempre los mismos escenarios con la misma watchlist). Decisión de producto,
  no de refactor.
