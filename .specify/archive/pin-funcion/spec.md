# Pin de función — Spec

> Documento puro (sin código). Anclado al código real a Jun 2026 (`fix/claude-md-versioncode-doctrine`).
> Implementación: **un solo PR post-Tribeca** (3–14 jun 2026), junto al worker Android y el fix del SW reload.
> Referencias de línea: válidas a esta lectura; reconfirmar al implementar.

## 1. Qué es y por qué

El usuario compromete **una función concreta** de una película —día, hora, venue— como **restricción dura** del Plan. Distinto de priorizar (★, `prioritized`): la prioridad dice "incluí esta película si podés"; el pin dice "**esta función, yo decido**".

Diferencias con `prioritized` (que ya existe, `src/main.js:625`):
- Prioridad opera a nivel **título**; el pin opera a nivel **(título, día, hora)**.
- Una prioridad puede dropearse cuando es mutuamente incompatible (Fase 2 del solver, `incompatiblePriorities`). **Un pin nunca se dropea en silencio.**
- Jerarquía: **pin > prioridad > interés (watchlist)**. Un film puede estar en los tres a la vez.

## 2. Modelo de datos

### 2.1 Estructura de `pinned`

Decisión cerrada: `pinned: Map<normTitle(título) → {day, time}>`, estado durable de primera clase paralelo a `watchlist`/`prioritized`, declarado en `src/main.js` §5 (junto a `prioritized=new Set()`, línea ~625) y expuesto vía STATE BRIDGE como los demás globals.

- **Key:** `normTitle(título)` (`src/domain/film.js:20`), igual que `watchlist`/`prioritized` se normalizan en `loadState` (`persistence.js:51-53`).
- **Value:** `{day, time}` — el día y hora que identifican la función comprometida (`venue` se deriva; no es parte de la key porque (día,hora) ya identifica la función dentro de un título).

> ⚠️ **REVISIÓN RECOMENDADA — Map vs objeto plano** (ver §6-R1). El codebase **no persiste ningún Map**: el estado durable es `Set` (`watchlist`/`watched`/`prioritized`) u **objeto plano** (`filmRatings`, `filmDelays`, `viewmodes`, `availability`). Un objeto `{ [normTitle]: {day,time} }` (a) serializa nativo a JSON sin el baile Map↔array, (b) calza con el patrón `filmRatings`/`filmDelays`, (c) entra a `state.batchUpdate` sin handling nuevo de Map. Los lookups del solver (`pinned.has(t)`/`pinned.get(t)`) se vuelven `t in pinned`/`pinned[t]` — equivalentes. El Map solo aporta iteración ordenada, que el feature no necesita. **El resto del spec asume objeto plano**; si se mantiene Map, ajustar serialización (§2.2) y lookups.

### 2.2 Storage key y serialización

Nueva entrada en el **STORAGE ADAPTER** (`src/storage/storage.js`, entre los marcadores `START` línea 36 / `END` línea 81). El check `[storage-encapsulation]` de `validate.py` **rechaza** cualquier `localStorage.(get|set)Item` fuera de esos marcadores → debe ir adentro.

- Key: `FESTIVAL_STORAGE_KEY+'pins'` (festival-scoped, como `'wl'`/`'prio'`/`'saved'`).
- Patrón (objeto plano, espejo de `getFilmRatings`/`setFilmRatings`, líneas 47-48):
  - `getPins()` → `r?JSON.parse(r):{}` con `try/catch`→`{}` (silent-fail, igual que el resto).
  - `setPins(o)` → `JSON.stringify(o)` con `try/catch`→no-op.
- Flag de migración one-shot: `FESTIVAL_STORAGE_KEY+'pins_migrated'` (string `'1'`), también vía adapter (`getPinsMigrated`/`setPinsMigrated`) — NO inline.
- Si se mantuviera Map: serializar `[...m]` (array de entries) y rehidratar `new Map(JSON.parse(r))`.

Wrapper controller: `savePins()` en `src/controller/persistence.js` (espejo de `savePrio()`, línea 32): `storage.setPins(pinned); _cloudSave();`. Añadir `'pins'` al dispatcher `saveState`/`saveX` (líneas 40-46).

### 2.3 Migración desde savedAgenda

`savedAgenda.schedule` es un array de objetos screening con `_title`, `day`, `time`, `day_order`, `venue` (lo que produce `computeScenarios`, `schedule.js:161/250`). Es **suficiente** para derivar los pins iniciales.

Corre en `loadState` (`persistence.js:48`), **una sola vez**, guardada por el flag:
- Condición: `getPinsMigrated()!=='1'` **y** `getPins()` vacío **y** `savedAgenda?.schedule?.length`.
- Derivación: por cada entry `s` → `pins[normTitle(s._title)] = {day:s.day, time:s.time}`.
- Al terminar: `setPins(pins)` + `setPinsMigrated('1')`.
- Lugar exacto: dentro del `try` de `loadState`, **antes** del `state.batchUpdate` (líneas 63-73), agregando `pinned` al batch para que los subscribers vean el snapshot completo (atomicidad, igual que el resto). `loadState` ya está envuelto en `try/catch` silencioso (línea 78) → seguro.
- **Riesgo:** ninguno bloqueante; es lectura + un write idempotente guardado por flag. No interactúa con el heal `prioritized⊆watchlist` (línea 75), que corre después y no toca pins (los pins huérfanos son válidos por diseño, §5).

Casos borde de la derivación → §6.

## 3. Integración con el solver

### 3.1 Contrato de entrada a computeScenarios

`computeScenarios(titles)` (`schedule.js:58`) **no recibe `prioritized` como parámetro** — lo lee como global bridgeado (`prioritized.has(t)`, línea 67), igual que `watched`/`FILMS`/`availability`. `pinned` se lee **igual**, como global.

⚠️ **Worker:** `computeScenarios` corre en el Web Worker (`src/controller/calc.js`, `_mkCalcWorker`), que recibe `{titles, films, watched, prioritized, ...}` por `postMessage` e inyecta cada uno como worker-local. **`pinned` debe agregarse al payload del worker e inyectarse como worker-local**, exactamente como `prioritized`. (Las fns puras viajan por `eval(name).toString()`; si la lógica de pin agrega un helper puro nuevo, va en `_SCHED_PURE_FNS` + el import del worker — lección del hotfix `minToStr`.) **Gate Tribeca: `schedule.js` + worker NO se tocan hasta post-festival.**

### 3.2 Restricción dura en backtracking

Un pin de título T impone: (i) la función elegida para T = exactamente la pineada (día,hora); (ii) T **debe** incluirse; (iii) ninguna otra función de T es elegible.

Punto de aplicación — **`baseGroups`** (`schedule.js:65-71`), donde hoy se arma cada grupo con `screens=FILMS.filter(f=>f.title===t && !isScreeningBlocked(f) && !screeningPassed(f))`:
- Si `t` está pineado → filtrar `screens` a **solo** la función pineada (match `f.day===pin.day && f.time===pin.time`) y marcar `g.pinned=true` (flag nuevo, paralelo a `g.priority`).
- ⚠️ **`!isScreeningBlocked && !screeningPassed` dropearía una función pineada que ya pasó o quedó bloqueada por disponibilidad** → el grupo quedaría con `screens.length===0` → eliminado por el `.filter(g=>g.screens.length>0)` (línea 71) → **pin dropeado en silencio**, lo que viola la decisión cerrada. La función pineada debe **bypassear** ese filtro (un pin es elección explícita del usuario; una función pineada que ya pasó es el caso "¿La viste?" de §5, no un drop). Ver §6-R3.

`bb`/`backtrack` (`findMax` línea 101-133; `collectAt` línea 150-184): hoy un grupo prioritario igual puede saltarse en `findMax` (`if(!g.priority) bb(idx+1,chosen)`, línea 130/123). Un grupo **pinned NUNCA se salta** (eliminar la rama de skip para pinned) y su función única siempre se empuja. `is_recurring` pinned → empujar todo el bloque (líneas 116-123/166-174), como hoy.

`findMax` (línea 96) y `collectAt` (línea 146) deben tratar pinned como **always-include** (un `mustIncludePinned` siempre activo, ortogonal a `mustIncludeAll`/`enforcePriority`). El `trueMax`/`maxWithPriorities` (líneas 138-141) se calculan ya con los pins forzados.

### 3.3 Conflicto entre pins — señal y resolución

Dos pins cuyas funciones conflictúan (`screensConflict`, `schedule.js:20`) son **insatisfacibles** — señal **propia, distinta de `incompatiblePriorities`**.

- Detección: bloque paralelo al de `conflictingPriorityPairs` (`schedule.js:239-248`), recorriendo los grupos `pinned` y comparando sus funciones únicas con `screensConflict`.
- Contrato de retorno (`schedule.js:250-262`): agregar `conflictingPins: [[titleA,titleB],...]` y `unsatisfiablePins: boolean`. Cuando hay conflicto de pins, **no se genera ningún escenario que viole un pin** (el solver no degrada el pin como sí degrada la prioridad en Fase 2).
- Propagación al caller: `runCalc` (`controller/calc.js`) recibe el resultado del worker; si `unsatisfiablePins`, el controller muestra el modal de resolución **"Mantener {A}" / "Mantener {B}"** (i18n §4.3). Al elegir, se borra el pin del otro título (`savePins()`) y se re-corre.

## 4. UI — pel-sheet

### 4.1 Zona de pins (sección Funciones)

La sección "Funciones" se renderiza en `openPelSheet` (`src/controller/sheets-controller.js:91`):
- Label: línea 191 (`label_funcion`/`label_funciones_pl`/`label_horario`).
- Filas: template `rows` (líneas 137-148), insertado en `<div class="pel-sheet-screenings">${rows}</div>` (línea 194).
- Cada fila hoy (`.pel-sheet-screening`, líneas 143-147) tiene 3 spans: `.pelicula-day` (`data-day`), `.pelicula-time`, `.pelicula-venue` (`data-action="filterByVenue"`). Tiene en scope `s.day`, `s.time`, `s.venue`.

**El botón de pin va como 4º hijo dentro de `.pel-sheet-screening`**, por fila (no es un CTA full-width). Hoy **no existe** ningún control accionable por fila en esa zona (las filas son display + el venue filtra), así que es un control nuevo.

- Componente: **botón inline pequeño** (NO `pel-sheet-action-btn`, que es CTA full-width de los líneas 214-222). Clase nueva sugerida `pel-sheet-pin-btn` (+ modificador `act-on` cuando esa fila es la pineada, reusando el patrón de estado activo de `pel-prio-btn`/`act-prio`, línea 220). Tokens de spacing/tipografía vía `var(--)` (regla de arquitectura; cero raw).
- `data-action="togglePin"` con `data-title`, `data-day`, `data-time`. **Sin onclick inline** — el check `[event-delegation]` exige `onclick=0`; el handler se registra en el registry (controller/handlers.js + el registro de acciones) como las 98 entradas actuales.
- Accesible desde las 4 tabs: `openPelSheet` es la **misma** sheet universal abierta desde cualquier tab → no requiere variación por tab.
- No colisiona con `closePelAndRemove`/`confirmReplace`/`toggleFilmAlternatives` (flows de Mi Plan): el botón vive en las filas de Funciones, separado de los CTAs inferiores (218-222) y del `pel-sheet-remove-plan` (línea 223). Esos flows se conservan intactos.
- Icono: **Lucide** (regla: solo Lucide). ⚠️ `ICONS.pin` ya se usa para el **venue** (línea 146, pin de ubicación) → el botón de fijar necesita **otro** icono Lucide para no confundir (candidatos: `pin`/`anchor`/`bookmark`/`lock`). **[PENDIENTE DECISIÓN: icono Lucide del pin de función].**

### 4.2 Estados del botón por fila

| Contexto | Fila no pineada | Fila pineada |
|---|---|---|
| Sin Plan aún (`!savedAgenda`) | "Fijar" | "Fijada" (`act-on`) |
| Con Plan (`savedAgenda` existe) | "Agregar" → el pin entra **directo, sin regenerar** | "Fijada" (`act-on`) |

- Solo **una** fila por título puede estar "Fijada" (pin = una función). **[PENDIENTE DECISIÓN: clic en otra fila cuando ya hay una pineada → ¿mueve el pin en silencio o confirma el cambio?]**
- "Agregar" con Plan ya armado: el pin entra a `savedAgenda` directamente (mutación de `savedAgenda` + `saveSavedAgenda`), **sin** re-llamar `computeScenarios`. Es un flujo de mutación de agenda, no del solver. **[PENDIENTE DECISIÓN: si "Agregar" introduce un conflicto con una función ya en el Plan, ¿se resuelve con el modal de §3.3 o con `confirmReplace` existente?]**

### 4.3 Verbos y i18n keys necesarias

Fuente de verdad: `src/i18n/i18n.js` (bloque `_I18N`, **es+en**). `validate.py [i18n-complete]` exige es+en completos. PT-BR se difiere (decisión cerrada) — no bloquea spec.

Keys nuevas (es / en):
- `cta_fijar` → "Fijar" / "Pin"
- `cta_fijada` → "Fijada" / "Pinned"
- `cta_agregar` → "Agregar" / "Add"
- `pin_orphan_ask` → "¿La viste?" / "Did you watch it?" (§5)
- `pin_conflict_keep` → "Mantener {title}" / "Keep {title}" (§3.3, con placeholder `{title}` → check `[i18n-interpolation]`)
- `pin_conflict_title` / `pin_conflict_body` → encabezado/cuerpo del modal de conflicto. **[PENDIENTE COPY: discusión semántica con Juan como Content Designer, regla del proyecto.]**

## 5. Pin huérfano

Un pin cuyo título ya **no está en watchlist** (fue removido) **persiste** en `pinned` — no pasa por `screeningPassed` ni se borra automáticamente (decisión cerrada). El pin es input durable, no derivado de la watchlist.

- Detección: título en `pinned` pero no en `watchlist`.
- UX: al detectarlo, mostrar **"¿La viste?"** (`pin_orphan_ask`) para limpiar el pin. **[PENDIENTE DECISIÓN: dónde se muestra — ¿en Mi Plan, en Intereses, en un sweep al abrir la app? El código actual no tiene un punto de "revisión de huérfanos"; hay que definir el host UI.]**
- Una función pineada que **ya pasó** (`screeningPassed`, `film.js:126`) es un caso de huérfano-temporal equivalente: el pin no se dropea; se ofrece "¿La viste?". (Conecta con el bypass del filtro en §3.2.)

## 6. Casos borde y restricciones

**Edge de migración / modelo:**
- **`is_recurring`:** el plan empuja **todos** los slots del bloque (mismo `_title`, varios día/hora — `schedule.js:119/169`). El value `{day,time}` **no puede representar un bloque recurrente** de N slots. Decisión cerrada: "pinear el bloque completo". → Necesita variante de representación (p. ej. `{recurring:true}` o pin-por-título-solo para recurrentes). **[REVISIÓN — R2 abajo.]**
- **`is_programa`/`is_cortos`:** una función de programa/cortos es un único screening con un (día,hora) → `{day,time}` lo representa bien. Corto individual dentro del programa: NO pineable (hereda la función del bloque) — el sheet del corto no ofrece pin.
- **`type==='event'`:** `validateFilm` (`film.js:43,52`) permite eventos sin `time`. Un evento pineado sin hora → `{day, time:''}`. **[PENDIENTE: confirmar que los eventos del festival activo tienen `time`; si no, el match (día,hora) del solver necesita tolerar `time` vacío.]**
- **Film ya visto (`watched`):** `computeScenarios` excluye watched (`pending=titles.filter(t=>!watched.has(t))`, `schedule.js:63`) → un pin de un título watched es inerte para el solver. La migración puede pinearlo igual (inofensivo) o saltarlo. **[PENDIENTE DECISIÓN menor: migrar pins de títulos ya watched o no.]**
- **Título en `savedAgenda` pero ya no en `FILMS`** (cambió la data del festival): el pin persiste como huérfano (§5); su (día,hora) puede no existir más.

**Restricciones de arquitectura:**
- normTitle obligatorio en la key (comillas tipográficas), igual que wl/prio.
- Worker: `pinned` al payload; helpers nuevos a `_SCHED_PURE_FNS`.
- Sin `localStorage` fuera del adapter; sin `onclick` inline; tokens `var(--)`; iconos Lucide.

### Decisiones cerradas que, visto el código real, conviene revisar

- **R1 — `pinned` como objeto plano en vez de Map.** Argumento: cero Map en el estado persistido actual; objeto calza con `filmRatings`/`filmDelays`, serializa nativo, entra a `state.batchUpdate` sin handling nuevo. Map solo da orden, que no se usa. *(No resuelvo; reporto.)*
- **R2 — el value `{day,time}` no expresa un bloque `is_recurring`.** La decisión "pinear el bloque completo" choca con un value de una sola (día,hora). Necesita variante. *(No resuelvo; reporto.)*
- **R3 — el filtro `!screeningPassed && !isScreeningBlocked` de `baseGroups` dropea pins en silencio.** Viola "un pin nunca se dropea en silencio". La función pineada debe bypassear ese filtro. *(No resuelvo; reporto.)*
- **R4 — cloud sync.** `prioritized`/`watchlist`/etc. sincronizan a Supabase `user_festival_state` (`persistence.js:86-95`, columnas explícitas). `pinned` **no tiene columna** → quedaría **local-only** salvo que se agregue `pinned` a la tabla + a `_cloudSave`/`_cloudLoad`. Las decisiones cerradas no mencionan cloud. **[DECISIÓN NECESARIA: pins local-only vs sincronizados.]**

## 7. Lo que NO cambia (gate Tribeca)

- `src/domain/schedule.js` y su **worker** (`src/controller/calc.js`): **NO se tocan durante Tribeca** (3–14 jun 2026).
- Flujos de Mi Plan existentes: `confirmReplace`, `toggleFilmAlternatives`, `closePelAndRemove`/`pel-sheet-remove-plan` — intactos.
- `prioritized` y su semántica (★) — el pin es paralelo, no lo reemplaza.
- El SW / cache-busting (su fix es otro track).
- Este `spec.md` SÍ se puede commitear ahora (documento puro).

## 8. Pasos de implementación (post-Tribeca)

> Todo en **un PR**, junto al worker Android y el fix del SW reload. Validar con `python3 validate.py` + `node --test tests/unit/*.test.js` antes de proponer commit; `node scripts/bump-version.js` antes de push.

### 8.1 Estado y migración
- `src/main.js` §5 (~625): declarar `pinned` (objeto plano per R1, o Map) + exponerlo en el STATE BRIDGE.
- `src/controller/persistence.js`: en `loadState` (48-79), derivar pins de `savedAgenda` one-shot (guardado por flag), agregar `pinned` al `state.batchUpdate` (63-73).

### 8.2 Storage adapter
- `src/storage/storage.js` (entre marcadores 36-81): `getPins/setPins` (key `…'pins'`) + `getPinsMigrated/setPinsMigrated` (`…'pins_migrated'`).
- `persistence.js`: `savePins()` (espejo de `savePrio`, 32) + `'pins'` en `saveX` (40-46). Si se sincroniza (R4): columna `pinned` en `_cloudSave`/`_cloudLoad` (86-95 / 116-127).

### 8.3 Solver  *(gate: post-Tribeca)*
- `schedule.js` `computeScenarios`: `baseGroups` (65-71) filtra a la función pineada + `g.pinned` + bypass del filtro passed/blocked (R3); `findMax`/`bb` (96-136) y `collectAt`/`backtrack` (146-186) tratan pinned como always-include (sin rama de skip); `conflictingPins`+`unsatisfiablePins` en el retorno (239-262).
- `controller/calc.js`: `pinned` al payload del worker + worker-local; `runCalc` propaga `unsatisfiablePins` al modal.

### 8.4 UI
- `sheets-controller.js` `openPelSheet`: botón `togglePin` por fila dentro de `.pel-sheet-screening` (137-148) con `data-title/day/time`; estados Fijar/Fijada/Agregar (§4.2); clase `pel-sheet-pin-btn` + `act-on`.
- `controller/handlers.js` + registry: handler `togglePin` (+ resolución de conflicto, + "Agregar sin regenerar").
- Modal de conflicto de pins (§3.3) y host UI de huérfanos (§5).
- CSS: `.pel-sheet-pin-btn` con tokens `var(--)`; ícono Lucide elegido.

### 8.5 i18n
- `src/i18n/i18n.js` `_I18N`: `cta_fijar`, `cta_fijada`, `cta_agregar`, `pin_orphan_ask`, `pin_conflict_keep`, `pin_conflict_title/body` (es+en). Copy de modal: discusión con Juan. PT-BR posterior.

### 8.6 Tests
- Unit (`tests/unit/`, vía `tests/lib/load-domain.js`): `computeScenarios` con pins — pin forzado siempre incluido; pin que dropea por passed (R3); conflicto de pins → `unsatisfiablePins`+`conflictingPins`; pin + prioridad simultáneos; `is_recurring` pineado (R2). Actualizar `DEFAULT_FNS` si la firma/deps de `computeScenarios` cambia.
- Migración: derivar pins de un `savedAgenda` mock (incluye recurring, programa, event sin time, watched).
- `validate.py`: `[storage-encapsulation]`, `[event-delegation]`, `[i18n-complete]`, `[i18n-interpolation]`, `[worker-overlap]`/`[worker-deps]` deben pasar.
