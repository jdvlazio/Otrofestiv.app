# Spec — Extracción de capa de dominio (Fase 1)

## Problema

La lógica de dominio (detección de conflictos, duración efectiva, resolución
de venues) vive dentro de funciones que mezclan responsabilidades:

1. `screensConflict(a, b)` y `effectiveDuration(f)` están en `index.html`
   junto al render. Hoy se les llama "puras" en `_SCHED_PURE_FNS` (línea 8234,
   inyección al Web Worker vía `.toString()`), pero leen globales
   (`FESTIVAL_BUFFER`, `FESTIVAL_TRANSPORT`, `FESTIVAL_CONFIG[_activeFestId]`).
   No están testeadas. Cualquier cambio a `screensConflict` riesga ~15
   callsites (planeación, sugerencias, gap-detection) y al worker.

2. La función `_resolveVenue` que la doc de ARQUITECTURA describe (sección
   14.3 — exacta → prefix → fallback) NO existe como función nombrada.
   La misma lógica está duplicada inline en tres lugares:
   - `venueTravelMins()` — index.html:4502 (main)
   - `vcfg()` — index.html:4523 (main)
   - `_workerFindCoords()` — index.html:8257 (worker)

   Tres copias = tres futuros de drift silencioso.

## Causa raíz

La app nació single-file con un único contrato implícito: "las funciones
puras viven juntas y comparten globals del festival activo". El Web Worker
materializa este contrato (serializa funciones vía `.toString()` e inyecta
sus propios globals al worker), pero la abstracción se quedó a medias:
el código nunca distinguió "función pura" de "función que lee globals
pero no escribe".

## Solución — Fase 1

Esta fase NO cambia firmas ni reordena callsites. Hace tres cosas:

### 1. Crear `_resolveVenue(name, venues)` como función nombrada

Firma:
- `name`: string del campo `film.venue`
- `venues`: objeto `{ "Nombre - Ciudad": {short, lat, lng, ...} }`
- Retorna: el objeto venue, o `{ short: name }` como fallback

Vive cerca de `venueTravelMins` en main thread. Se añade a `_SCHED_PURE_FNS`
para inyección al worker (el worker tiene su propio `_venueCoords`, que
sustituye al parámetro `venues`).

### 2. Reemplazar las 3 copias inline por llamada a `_resolveVenue`

- `venueTravelMins` (main): el bloque `findCoords` interno → `_resolveVenue(v, festVenues)`
- `vcfg` (main): el bloque de búsqueda exacta+prefix → `_resolveVenue(v, festVenues)`
- `_workerFindCoords` (worker): el cuerpo entero → `_resolveVenue(v, _venueCoords)`

Comportamiento idéntico, una sola fuente de verdad.

### 3. Documentar el contrato de pureza y cubrir las tres funciones con tests

Las firmas de `screensConflict`, `effectiveDuration` y `_resolveVenue`
no cambian. Lo que cambia es que:
- Se añade un bloque de comentario sobre cada función nombrando sus globals
  como contrato (qué leen, por qué, qué se asume).
- Se crean tests unitarios en `tests/unit/*.test.js` (Node + node:test/assert,
  cero dependencias). Los tests cargan `index.html`, extraen las
  funciones por nombre, y las evalúan en un sandbox que controla los globals.

## Criterios de aceptación

- [ ] `_resolveVenue(name, venues)` definida en index.html, cerca de venueTravelMins
- [ ] `_resolveVenue` añadida a `_SCHED_PURE_FNS`
- [ ] `venueTravelMins`, `vcfg`, `_workerFindCoords` usan `_resolveVenue` — cero lógica inline duplicada
- [ ] Cada función pura tiene comentario que documenta sus globals como contrato
- [ ] `tests/unit/effectiveDuration.test.js` — casos: sin has_qa, con has_qa, duración nula, duración con "~"
- [ ] `tests/unit/screensConflict.test.js` — casos: días distintos, solapamiento directo, gap insuficiente por buffer, gap insuficiente por travel, Q&A extiende ventana, mismo venue
- [ ] `tests/unit/resolveVenue.test.js` — casos: match exacto, match por prefix, match por substring case-insensitive, fallback con short=name, venues vacío
- [ ] `tests/lib/load-domain.js` — loader que extrae funciones de index.html
- [ ] CI corre `node --test tests/unit/` (paso nuevo en bump-and-validate.yml)
- [ ] `python3 validate.py` 12/12 sin regresiones
- [ ] Playwright T01–T10 sin regresiones
- [ ] QA browser:
    - [ ] Sheet de film muestra venue short correcto (FICCI, Tribeca, Leviza)
    - [ ] Conflicto de horario se detecta en escenarios conocidos
    - [ ] Worker procesa schedule sin error (Planear renderiza)
- [ ] Commit atómico con mensaje siguiendo convención del repo

## Fuera de alcance — explícito

- Cambiar firma de `screensConflict` o `effectiveDuration` para recibir
  globals por parámetro (pureza real) — fase 2 o decisión separada
- Sacar funciones de `index.html` a archivos `js/*.js` separados — rompe
  invariante single-file, requiere su propia spec
- Refactor de la lógica de fase de festival, gap detection, schedule planning
- Reescribir el Web Worker
- Tocar render functions
- Migrar inline onclick handlers (deuda registrada en ARCH)
