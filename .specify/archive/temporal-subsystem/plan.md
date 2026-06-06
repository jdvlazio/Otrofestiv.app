# Plan técnico — Fase 3

## Restricciones de partida

### R1. Single-file en producción
Mismo invariante de Fase 1+2. Toda función nueva (o contrato nuevo) vive
en `index.html`. La descomposición física a archivos separados es Fase 8.

### R2. Worker duplication preservada
`simNow` y `festivalEnded` tienen copias en el worker template (`_venueFns`
en `_mkCalcWorker`, líneas 8296–8297) con globals de nombres distintos
(`SIM_TIME`/`FESTIVAL_END_TS`). El comentario en línea 8293 explica el
porqué. Fase 3 **NO toca** estas copias y **NO añade** `simNow`/`festivalEnded`
a `_SCHED_PURE_FNS`. La eliminación de la duplicación queda para Fase 8.

`_festDate` y `screeningPassed` ya están en `_SCHED_PURE_FNS` — se inyectan
al worker via `.toString()`. Sus contratos main-thread aplican igual al worker.

### R3. Globals como contrato implícito
Mismo modelo de Fases 1+2: documentar los globals como contrato, no cambiar
las firmas. Las firmas se vuelven puras (deps por parámetro) en Fase 5.

## Cambios en index.html

Cero cambios de firma, cero cambios de body, cero callsites tocados.
**Solo se añaden bloques de comentario** sobre cada una de las 6 funciones.

### Ubicaciones de los contratos

| Función | Línea actual | Bloque de contrato a documentar |
|---|---:|---|
| `_festDate` | 3585 | Lee `TZ_OFFSET`. Construye Date con offset explícito. Worker la inyecta vía `.toString()`. |
| `festivalEnded` | 4446 | Lee `FESTIVAL_END` (mutable). Llama `simNow()`. NO en `_SCHED_PURE_FNS` — worker tiene copia con `FESTIVAL_END_TS`. |
| `screeningPassed` | 4454 | Lee `FESTIVAL_DATES`. Llama `festivalEnded`, `_festDate`, `simNow`. Gate: si `festivalEnded()` → false. Grace de 10 min. En `_SCHED_PURE_FNS`. |
| `dayFullyPassed` | 4462 | Lee `FESTIVAL_DATES`, `FILMS`. Llama `_festDate`, `simNow`. Grace de 10 min. Main-thread only. |
| `simNow` | 4680 | Lee `_simTime` (null = real time). NO en `_SCHED_PURE_FNS` — worker tiene copia con `SIM_TIME`. |
| `simTodayStr` | 4681 | Llama `simNow()`. Retorna YYYY-MM-DD en TZ LOCAL del runtime (NO UTC — ver comentario interno actual). Main-thread only. |

## Cambios en tests/lib/load-domain.js

Extender `DEFAULT_FNS` con las 6 funciones nuevas:

```js
const DEFAULT_FNS = [
  // Fase 1
  'toMin', 'parseDur', 'effectiveDuration',
  '_resolveVenue', 'venueTravelMins', 'travelMins',
  'screensConflict',
  // Fase 2
  '_endedStats', '_classifyTodayScreenings', '_gapSuggestion', '_getFestivalPhase',
  // Fase 3 — temporal subsystem
  '_festDate', 'simNow', 'simTodayStr', 'festivalEnded', 'screeningPassed', 'dayFullyPassed',
];
```

## Tests — diseño

### Estructura

```
tests/unit/
  festDate.test.js          ← 3 casos
  simNow.test.js            ← 3 casos
  simTodayStr.test.js       ← 3 casos
  festivalEnded.test.js     ← 3 casos
  screeningPassed.test.js   ← 5 casos
  dayFullyPassed.test.js    ← 4 casos
```

Total: 21 tests nuevos. Suite combinada: 58 tests.

### Casos por función

`_festDate(dateStr, time)`:
- Basic: `_festDate('2026-06-05', '14:30')` con `TZ_OFFSET='-05:00'` → Date equivalente a UTC `2026-06-05T19:30:00Z`
- TZ_OFFSET distinto: `'-04:00'` → Date 1h antes en UTC
- Input válido pero edge: tiempo `'00:00'` con offset → medianoche local correcta

`simNow()`:
- `_simTime=null` → Date cuyo timestamp está dentro de los últimos 100 ms vs `Date.now()`
- `_simTime='2026-06-05T14:30:00'` (string ISO local) → Date para esa hora local
- `_simTime` aplicado dos veces → mismo resultado (idempotencia)

`simTodayStr()`:
- `_simTime=null` → match con today local YYYY-MM-DD
- `_simTime='2026-06-05T14:30:00'` → `'2026-06-05'`
- `_simTime='2026-06-05T23:59:00'` (right before midnight local) → `'2026-06-05'`

`festivalEnded()`:
- `_simTime` antes de `FESTIVAL_END` → false
- `_simTime` después de `FESTIVAL_END` → true
- `_simTime === FESTIVAL_END` → false (`>` strict)

`screeningPassed(s)`:
- `festivalEnded()=true` → false (gate, sin importar la hora del screening)
- `s.day` no está en `FESTIVAL_DATES` → false
- `simNow > screeningTime + 10min grace` → true
- `simNow < screeningTime + 10min grace` → false
- `simNow === screeningTime + 10min grace` → false (`>` strict)

`dayFullyPassed(day)`:
- `day` no está en `FESTIVAL_DATES` → false
- No hay films de ese día en `FILMS` → false
- `simNow < lastFilm.time + 10min` → false
- `simNow > lastFilm.time + 10min` → true

### Globals inyectados en cada test

- `_festDate.test.js`: `TZ_OFFSET`
- `simNow.test.js`: `_simTime`
- `simTodayStr.test.js`: `_simTime`
- `festivalEnded.test.js`: `_simTime`, `FESTIVAL_END`
- `screeningPassed.test.js`: `_simTime`, `FESTIVAL_END`, `FESTIVAL_DATES`, `TZ_OFFSET`
- `dayFullyPassed.test.js`: `_simTime`, `FESTIVAL_DATES`, `FILMS`, `TZ_OFFSET`

Las dependencias function-to-function (e.g., `screeningPassed` llama `_festDate`)
se resuelven via hoisting en la IIFE del loader, igual que en Fase 2.

## QA browser — receta

### Smoke test general
1. `python3 -m http.server 3000` → abrir `localhost:3000` en mobile viewport
2. Selector → Tribeca 2026
3. Verificar: Console sin errores nuevos, tabs Mi Plan/Programa/Planear cargan

### Verificación específica de `simTodayStr` con `_simTime` explícito
En DevTools Console:
```js
// Caso 1: tiempo real
_simTime = null;
console.log(simTodayStr());  // → YYYY-MM-DD de hoy local

// Caso 2: simTime en mitad del día
_simTime = '2026-06-05T14:30:00';
console.log(simTodayStr());  // → '2026-06-05'

// Caso 3: simTime cerca de medianoche local
_simTime = '2026-06-05T23:59:00';
console.log(simTodayStr());  // → '2026-06-05' (no salta a 06-06)

// Reset
_simTime = null;
```

## CI

Sin cambios — `node --test tests/unit/*.test.js` ya cubre los nuevos
archivos automáticamente.

## Riesgos

| Riesgo | Mitigación |
|---|---|
| `simTodayStr` usa Date.getFullYear/getMonth/getDate (local del runner). En CI (UTC) podría dar resultado distinto que en local del dev (UTC-5). | Tests usan strings ISO **sin TZ suffix** (e.g., `'2026-06-05T14:30:00'`). Interpretación local consistente en ambos runners porque el string no especifica TZ. Verificado en Fase 2 con resultados estables. |
| `_festDate` depende de TZ_OFFSET global. Tests inyectan TZ_OFFSET explícito. | Cada test usa `globals: { TZ_OFFSET: '-05:00' }` para reproducibilidad. |
| `screeningPassed` tiene gate de `festivalEnded`. Mockear ese gate requiere setear correctamente FESTIVAL_END. | Tests setean `FESTIVAL_END` futuro para no disparar el gate, y separadamente testean el caso `festivalEnded=true`. |
| Worker rompe porque cambia comportamiento de `_festDate` o `screeningPassed` | Cero cambios de body — solo comentarios. Worker tiene cero exposure de cambio. |
| Smoke test en QA browser no detecta regresión sutil | Verificación explícita de `simTodayStr` con `_simTime` añadida como tarea separada. |

## Deuda futura

- **Fase 5 (state container)**: las 6 funciones cambian firma para recibir
  state slice por parámetro. Globals desaparecen como contrato implícito.
- **Fase 8 (file split)**: `simNow` y `festivalEnded` dejan de duplicarse —
  el worker importa directamente del archivo `model/time.js`.
- Considerar también `isNowShowing(f)` (línea ~4473) — adyacente al subsistema
  temporal, fuera de alcance de esta fase. Candidata para Fase 3.5 o
  añadir a Fase 4 (schedule planning) si la dependencia natural lo justifica.
