# Pin de función específica — Análisis arquitectónico verificado

> **Estado:** análisis para revisión humana (Juan). NO implementado, NO commiteado.
> Generado contra el código en `main` tras el hotfix del planner. Baseline: `validate.py` 31/32 (1 warning pre-existente `file-split-8`).
> Verificado por lectura directa del código + 3 barridos read-only. Las líneas son del estado actual de `main`.

---

## 0. Resumen ejecutivo

- Los **8 hallazgos** de la sesión previa son **correctos**, con **2 correcciones de ubicación** (hallazgo 6: `toggleFilmAlternatives` vive en `handlers.js:567`, no en `agenda.js`; hallazgo 4: el reemplazo total está en `handlers.js:760`).
- La **hipótesis del pin como estado durable de primera clase es arquitectónicamente sólida y, además, elegante**: un pin mapea 1:1 a "colapsar las funciones candidatas de ese título a UNA + marcarlo como obligatorio", lo que **reusa toda la maquinaria del solver** (branch-and-bound, `screensConflict`, day-balance) sin reescribirla. De paso **arregla la fragilidad** de las ediciones manuales (que hoy se destruyen al regenerar).
- **Recomendación:** Enfoque A (pin como estado + restricción de entrada al solver), con la afordancia de pin **en la lista `Funciones` del sheet** (hallazgo 7) — lo que **esquiva por completo la colisión de gesto** de Mi Plan (decisión abierta #1).
- **Lo que la sesión pasó por alto** (sección 5): pin de título **fuera de watchlist** debe unirse al input del solver (no solo filtrar `titles`); el pin necesita una señal de inconsatisfacibilidad **distinta** de `incompatiblePriorities` (una prioridad se puede dropear, un pin NO); interacción del pin con `is_recurring`, con el filtro `screeningPassed`/`isScreeningBlocked` del solver, con `lastRemovedSlots`, y la **migración** de ediciones manuales existentes.

---

## 1. Tabla de verificación de los 8 hallazgos

| # | Hallazgo | Veredicto | Evidencia (file:line) |
|---|---|---|---|
| 1 | Modelo: cada unidad tiene `screenings:[{date,time,venue,day_order}]`; el loader **explota** a objetos planos por función; cortos individuales (`film_list`) **no** tienen función propia → heredan la del programa padre → **no pineables solos** | **CONFIRMADO** | `src/controller/loader.js:61-80` (explosión: `f.screenings.forEach(...exploded.push)`; `day:s.day||s.date`). `film_list` items: 0 con `screenings` propios (ver §2). |
| 2 | Solver `computeScenarios(titles)`: branch-and-bound que **maximiza nº de películas**, `prioritized` como must-include, balancea por día, determinístico (RNG sembrado), reporta `conflictingPriorityPairs`/`incompatiblePriorities`. **No** hay concepto de "pin" | **CONFIRMADO** | `src/domain/schedule.js:58-263`. baseGroups `:65-71` (`screens=FILMS.filter(title && !blocked && !passed)`); seed `:62` (`_mulberry32(_titleSeed(titles))`); must-include `:106-111` (`groups.every(g=>!g.priority||chosenTitles.has(g.title))`); **selección de 1 función por título** `:124-132` (`for(const s of g.screens){...}`); return fields `:250-262`. |
| 3 | Worker: fns puras de `schedule.js` se **copian** al worker vía `eval(name).toString()`; cubierto por `[worker-overlap]` + `[worker-deps]` | **CONFIRMADO** | `src/controller/calc.js:26-31` (`_SCHED_PURE_FNS`), `:67-70` (`eval(name).toString()`). Validadores: `validate.py` `[worker-overlap]:198`, `[worker-deps]` (añadido en el hotfix, valida cierre de dependencias). **Cualquier cambio al solver vive en 2 lugares** (schedule.js + la lista de extracción). |
| 4 | Dos espacios: PLANEAR=`cachedResult` (sandbox), MI PLAN=`savedAgenda` (comprometido). Commit `saveCurrentScenario()` hace `state.set('savedAgenda',{schedule})` = **reemplazo total** (`plan_reemplazar_plan`) → **regenerar destruye ediciones manuales** | **CONFIRMADO** (línea corregida) | `src/controller/handlers.js:755` (`saveCurrentScenario`), **reemplazo total `:760`** (`state.set('savedAgenda', {schedule:_squeezed})`), confirm `plan_reemplazar_plan` `:768`. Trace en §6. |
| 5 | Ediciones manuales escriben en `savedAgenda` y son frágiles; `addSuggestion` ya hace "agregar función específica"; modal de conflicto es **elección del usuario** (`misc_si_anadir`/`misc_si_reemplazar`), no auto-resuelve | **CONFIRMADO** | `handlers.js:233` (`addSuggestion`: WL + conflicto vía `openConflictSheet` `:260` + `state.update('savedAgenda',...)` MERGE + `saveSavedAgenda`), `:409` (`confirmReplace`), `:213` (`removeFromAgenda`). Modal user-choice en `sheets-controller.js` (`openConflictSheet`/`confirmConflictReplace`). |
| 6 | "Tocar la hora" en Mi Plan muestra **otras películas** ±15 min (no otras funciones de la misma peli) → `confirmReplace`; tooltip `tooltip_cambiar_horario` **mal etiquetado** | **CONFIRMADO + CORRECCIÓN** | El spec decía `agenda.js`; **`toggleFilmAlternatives` está en `handlers.js:567`**. `renderFilmAlternatives` sí en `agenda.js:427`; ventana `WINDOW=15` `:433`; filtra `f.title!==title` (otras pelis) → `data-action="confirmReplace"`. Tooltip `tooltip_cambiar_horario` en `agenda.js:332` (dice "cambiar horario" pero cambia la **película**). |
| 7 | Sheet compartida (`openPelSheet`/`openCortoSheet`/`_openCombinedFilmSheet`); la lista `Funciones` (hora+sede) es el punto de entrada natural del pin | **CONFIRMADO** | `src/controller/sheets-controller.js`: `openPelSheet` (~`:91`), filas de función `:136-148` (`.pel-sheet-screening` con `.pelicula-day`/`.pelicula-time`/`.pelicula-venue`), label `label_funcion(es)` (~`:191`). Cada fila ya tiene `${ICONS.pin}` → punto de anclaje del botón pin. |
| 8 | Persistencia por-festival (`storage.js`); roster de estado (`state.js`); fases `festivalEnded()`/`screeningPassed`/`_festNowMin` | **CONFIRMADO** | `state.js` `_ROSTER:19-25` incluye `watchlist,prioritized,savedAgenda,lastRemovedSlots,...`. Claves prefijadas en `storage.js` (`{key}_saved`,`_prio`,`_wl`,`_lastslot`). `time.js`: `festivalEnded`, `_festNow`/`_festNowMin:59-60`, `screeningPassed` (`film.js`). |

---

## 2. Datos por festival activo (dentro de fechas)

Fuente: `festivals/*.json`. "Unidad" = entrada en `films[]` (lo que el solver ve como título único, antes de explotar). "% ≥2 funciones" = unidades pineables donde elegir función **importa**.

| Festival | Unidades | % con ≥2 funciones | Distribución (nº fn → unidades) | Tipos | Cortos en `film_list` con función propia |
|---|---|---|---|---|---|
| **Tribeca 2026** (jun 3–14) | **204** | **69%** (140/204) | 1:64 · 2:15 · 3:117 · 4:8 | regular 149 · is_cortos 16 · is_programa 0 · event 41 | **0 / 91** → heredan |
| **Olhar 2026** (jun 4–13) | **58** | **93%** (54/58) | 1:4 · 2:44 · 3:9 · 4:1 | regular 46 · is_cortos 11 · is_programa 1 · event 0 | **0 / 44** → heredan |

**Lecturas de producto:**
- En **ambos** festivales, la **mayoría** de unidades tienen ≥2 funciones (69% / 93%) → elegir función específica es relevante para casi todo el catálogo, no un caso de borde.
- Las **64 unidades de 1 sola función en Tribeca** (incluye los 41 eventos: inaugural, awards, talks) son el caso (b) del producto: "comprometer una peli con una sola función / fuera de intereses". El pin debe funcionar igual con 1 función.
- **Confirmado el hallazgo 1:** 0/91 (Tribeca) y 0/44 (Olhar) cortos en `film_list` tienen `screenings` propios → el corto individual **no es pineable solo**; lo pineable es el **programa** (`is_cortos`/`is_programa`), la película y el evento.

---

## 3. Hipótesis a evaluar — por qué el "pin como restricción de entrada al solver" encaja

El solver ya hace exactamente la mitad del trabajo: por cada título arma `g.screens` (sus funciones disponibles) y el branch-and-bound **elige UNA** (`schedule.js:124-132`). `prioritized` lo fuerza a **must-include** (`:106-111`).

Un **pin `{título→{day,time}}`** = dos cosas que el solver ya sabe expresar:
1. **Colapsar** `g.screens` de ese título a **la única función pinneada** (en vez de todas sus funciones).
2. **Must-include reforzado**: como `priority`, pero el solver **no puede dropearlo** (una prioridad sí se dropea cuando es incompatible → `priorityCost`; un pin **no**).

Esto significa que el pin **reusa** branch-and-bound, `screensConflict`, day-balance, determinismo — sin reescribir el solver. Y como es **input upstream** de `computeScenarios`, **sobrevive la regeneración** (cada recálculo lo respeta) y **sobrevive el commit** (el escenario ya viene con el pin colocado). Eso valida los 3 puntos de la hipótesis (i, ii, iii) y, como subproducto, mata la fragilidad del §6.

---

## 4. Enfoques de solución

### Enfoque A — Pin como estado durable de primera clase, restricción de entrada al solver ✅ RECOMENDADO

**Modelo.** Nueva clave de estado `pinned` (objeto `{título → {day,time}}`), paralela a `watchlist`/`prioritized`, persistida por-festival (`{key}_pinned`).

**Solver (`schedule.js:computeScenarios`).**
- El conjunto de títulos pasa a ser `union(titles, Object.keys(pinned))` → permite pin de pelis **fuera de watchlist** (caso b).
- En `baseGroups`: si `pinned[t]`, `screens = screens.filter(s => s.day===pin.day && s.time===pin.time)` (colapsa a 1) y se marca `pinned:true`.
- En el terminal de `bb`/`findMax` (`:106-111`): extender `mustIncludeAll` para exigir también los pinneados; añadir una rama que detecte **pin insatisfacible** (un pin que ningún escenario puede incluir por choque pin-pin) y reportarla **separada** de `incompatiblePriorities`.
- Pin de función ya pasada/bloqueada: ver §5 (no filtrarla silenciosamente).

**Reframe de las ediciones manuales** (arregla la fragilidad): `addSuggestion`/`confirmReplace`/`removeFromAgenda` pasan a **escribir/borrar `pinned`** (no `savedAgenda` directo). El commit (`saveCurrentScenario`) sigue siendo reemplazo total **pero ahora es seguro**, porque el escenario regenerado ya respeta los pins.

**Afordancia:** botón pin en cada fila de la lista `Funciones` del sheet (hallazgo 7) — ver decisión #1 opción C.

**Archivos afectados:** `src/domain/schedule.js` (solver + worker-copy via `_SCHED_PURE_FNS` — **2 lugares**, `calc.js:26-31` + el postMessage `:164-176` debe sumar `pinned`, y el handler del worker `:73-91` desempaquetar `pinned=...`); `src/state/state.js` (roster + getter/setter); `src/storage/storage.js` (`get/setPinned`); `src/controller/handlers.js` (reframe de las 3 ops + nuevo `togglePin`); `src/controller/sheets-controller.js` (botón pin en filas + estado "En Mi Plan"); `src/view/agenda.js` (render del pin en Mi Plan/Planear); `src/i18n/i18n.js` (copy ES+EN). `tests/lib/load-domain.js` (`pinned` global + DEFAULT_FNS si surge helper nuevo).

**Riesgo:** **MEDIO-ALTO.** Toca el solver (el componente que ya rompió producción 2 veces vía la duplicación worker). El `[worker-deps]` recién añadido cubre dependencias faltantes, pero **no** detecta divergencia semántica entre las dos copias del solver — disciplina manual. La señal "pin insatisfacible" es lógica nueva en branch-and-bound (cuidado con el cap `MAX_NODES_PER_CALL=80000`).

**Impacto en tests:** `tests/unit/computeScenarios.test.js` — `loadPlanner()` suma `pinned`; +3-5 tests nuevos ("pin incluido en todos los escenarios", "pin colapsa a 1 función", "pin-pin insatisfacible → señal", "pin fuera de watchlist se incluye"). Las 7 invariantes actuales (conflict-free, ≤trueMax, partición, determinismo, prioridad-en-índice-0) **deben seguir pasando** sin cambio. Playwright `planner.spec.js` T03/T31 y `miplan.spec.js` T27/T44 necesitan setup de pin. Contrato del worker postMessage gana `pinned` → tocar el path async + el fallback sync `_runCalcSync`.

---

### Enfoque B — Pin solo como flag en `savedAgenda` (`_pinned:true`), preservado en el commit (sin tocar el solver)

**Modelo.** No hay estado nuevo. Cada item de `savedAgenda.schedule` puede tener `_pinned:true`. El solver **no cambia**. `saveCurrentScenario` deja de ser reemplazo total: **mergea** los items pinneados del `savedAgenda` viejo sobre el escenario regenerado.

**Archivos afectados:** solo `handlers.js` (`saveCurrentScenario` merge en vez de `:760`), `agenda.js` (render del flag), i18n. **No toca solver ni worker.**

**Riesgo:** **BAJO en blast-radius, ALTO en correctitud.** El escenario se computa **sin saber de los pins** → el solver puede elegir, para OTRA peli, una función que choca con el pin que vas a injertar después → el "merge" produce **planes con conflictos que el solver creía válidos** (justo la fragilidad que queremos matar, movida de lugar). No maneja pin de pelis fuera de watchlist (el solver no las ve). El plan ya no es óptimo respecto a los pins.

**Impacto en tests:** mínimo en unit (solver intacto); pero requiere tests de integración nuevos para el merge y sus conflictos. Es la opción que **menos rompe** y la que **peor resuelve** el problema.

---

### Enfoque C — Pin como estado + el solver **pre-siembra** `chosen[]` (lock pinneados, optimiza el resto)

Variante de A: en vez de colapsar `g.screens`, el branch-and-bound **arranca con los pins ya colocados en `chosen`** y optimiza alrededor. Mecánicamente equivalente a A (un pin = función fija que no se reordena), pero la implementación toca el núcleo de `bb()` en vez de la construcción de `baseGroups`.

**Tradeoff vs A:** misma potencia, **peor relación riesgo/beneficio** — modificar el cuerpo recursivo de `bb()` (con su cap de nodos y la rama `is_recurring`) es más delicado que filtrar `g.screens` en `baseGroups`. **A logra lo mismo con un cambio más localizado.** C solo conviene si A resultara insuficiente para algún caso de prioridad+pin combinados.

---

## 5. Decisiones abiertas — opciones con tradeoffs

### #1 — Colisión de gesto en Mi Plan
- **(A) Una hoja al tocar la hora, dos secciones** ("cambiar función de esta peli" + el `confirmReplace` actual). *Tradeoff:* concentra todo en un gesto, pero mezcla dos acciones distintas (cambiar función propia vs reemplazar peli) en un sheet → carga cognitiva; toca `renderFilmAlternatives` (agenda.js:427).
- **(B) Gestos separados** (hora=función propia, título/póster=reemplazar peli). *Tradeoff:* semánticamente limpio y arregla el tooltip mal etiquetado (hallazgo 6), pero re-mapea un gesto que los usuarios ya conocen.
- **(C) El pin vive en la lista `Funciones` del sheet (hallazgo 7), NO en el tap de la hora** ✅ *— lo que la sesión no consideró.* El tap de la hora **conserva** su significado actual ("cambiar película", vía `confirmReplace`), y "elegir/comprometer una función específica" sucede donde ves **todas** las funciones: el sheet. *Tradeoff:* cero colisión de gesto, cero re-mapeo, reusa el punto de entrada natural; el único costo es que pinear desde Mi Plan requiere abrir el sheet (1 tap extra) — aceptable. **Recomendado.** Toca `sheets-controller.js` (botón en filas), no `renderFilmAlternatives`.
- **Conservar `confirmReplace`** en las 3 opciones (es el "reemplazar peli del slot", ortogonal al pin).

### #2 — Dónde vive el pin
- **Estado durable de primera clase `pinned`** (Enfoque A) ✅ — sobrevive regenerar/commit por ser input upstream; paralelo a `watchlist`/`prioritized`; encaja en el roster (`state.js:19-25`) y en `storage.js`.
- **Flag en `savedAgenda`** (Enfoque B) — más simple, pero el solver no lo ve → correctitud débil.
- **En `cachedResult`** — descartado: es sandbox efímero, no persiste, se pierde al recalcular.

### #3 — Conflictos (validado contra `screensConflict`/`FESTIVAL_BUFFER`)
`screensConflict(a,b)` (schedule.js) es **binario**: devuelve `true` si hay solape directo **o** si `gap < minGap` donde `minGap = max(FESTIVAL_BUFFER, travel+FESTIVAL_BUFFER)`. Implicaciones:
- **Resoluble** (la otra unidad tiene alternativas) → reflow silencioso: el solver elige otra función de la otra peli. **Coherente** — es lo que `bb()` ya hace.
- **Irreducible** (pin vs pin sin alternativas) → el usuario elige, nunca auto-resolver. **Requiere lógica nueva**: la señal debe ser **distinta** de `incompatiblePriorities` (una prioridad se dropea; un pin no). Copy acordado: `{a} y {b}: mismo día, misma hora. Solo podés ver una.` + `Mantener {a}`/`Mantener {b}`.
- **Apretado pero posible** (gap ≥ travel+buffer) → **`screensConflict` ya lo considera NO-conflicto** (cabe). El "warning de conexión apretada" sería un **umbral suave nuevo** (p.ej. gap ≥ travel pero < travel+buffer+margen). Existe ya `travelWarn` (helpers.js) como afordancia de aviso de viaje → **reusarla** en vez de inventar otra. *Decisión:* el pin se mantiene + warning vía `travelWarn`.

### #4 — Pin huérfano durante festival (función futura comprometida que pasa sin verse)
- **Mantener** → el plan conserva historia, pero `screeningPassed` la atenúa; coherente con el resto.
- **Autolimpiar** → riesgo de borrar algo que el usuario sí vio.
- **Preguntar "¿la viste?"** → mejor UX pero requiere disparador (al reabrir post-función) y copy nuevo.
- *Subtleza crítica (lo que la sesión no vio):* `baseGroups` filtra `!screeningPassed(f)` (`schedule.js:66`). Un pin a una función que ya pasó **desaparecería del solver** → el pin se perdería **silenciosamente** en vez de mostrarse como huérfano. La implementación debe **excluir los pins de ese filtro** (o manejarlos antes) para que la decisión #4 sea siquiera posible. *Recomendación:* mantener + marcar `_isPast` (no preguntar pre-festival; "¿la viste?" solo durante festival, reusando `screeningPassed`/`_festNowMin`).

### #5 — Afordancia "agregar a este día" en Mi Plan
- **(A) Botón en la cabecera del día** — descubrible, consistente con el landmark de día que ya agrupa items (DESIGN.md `--plan-saved`). *Tradeoff:* abre un picker/sheet de qué agregar.
- **(B) Tocar hueco vacío del calendario** — natural en vista calendario (`renderMiPlanCalendar`), pero menos descubrible y el "hueco" no siempre es obvio en lista. *Recomendación:* (A) botón en cabecera de día → abre buscador filtrado por ese día → pin. Más barato y descubrible; reusa el patrón de sugerencias.

---

## 6. Trace: regenerar destruye ediciones manuales (evidencia del §4)

1. Usuario edita Mi Plan: `addSuggestion('F1','jun 7','8:00 PM')` → `state.update('savedAgenda', a=>({...a, schedule:[...a.schedule, {...screen,_title:'F1'}]}))` + `saveSavedAgenda()` (`handlers.js:233-268`). `savedAgenda` ahora contiene F1 manual.
2. Usuario va a PLANEAR y recalcula: `runCalc()` → worker → `computeScenarios([...watchlist])` → `cachedResult={scenarios,...}` (`calc.js:185-187`). **`cachedResult` se computa solo desde `watchlist`; nunca lee `savedAgenda`.** Si F1 no estaba en watchlist (o el solver eligió otra función de F1), la edición manual **no está** en `cachedResult`.
3. Usuario confirma: `saveCurrentScenario()` → **`state.set('savedAgenda', {schedule:_squeezed})`** (`handlers.js:760`) = **reemplazo total** con el escenario regenerado.
4. **Resultado:** la edición del paso 1 se pierde (estaba en el `savedAgenda` viejo, no en `cachedResult`). Confirm previo `plan_reemplazar_plan` (`:768`) advierte "reemplazar", pero el usuario no espera perder ediciones puntuales.

**Con Enfoque A esto desaparece:** el paso 1 escribe `pinned`; el paso 2 incluye `pinned` en el input del solver → F1 viene en `_squeezed`; el paso 3 ya no destruye nada.

---

## 7. Superficie de tests afectada

- **`tests/unit/computeScenarios.test.js`** (CRÍTICO): 7 invariantes (conflict-free, `len≤trueMax`, partición incluidos/excluidos, determinismo 8 corridas, "prioridad siempre en índice 0", "todos compatibles→todos incluidos"). Setup `loadPlanner()` inyecta `FILMS/watched/prioritized/savedAgenda/_simTime/...` vía `loadDomain`. Enfoque A: sumar `pinned` al setup + tests nuevos; las 7 deben seguir verdes.
- **`tests/lib/load-domain.js`**: `DEFAULT_FNS` (29 fns) + inyección de globals. Si el solver lee `pinned` directo (no vía helper) → solo sumar el global; si surge un helper (`_isPinned`) → sumarlo a `DEFAULT_FNS` **y** (recordatorio del hotfix) a `_SCHED_PURE_FNS` del worker.
- **Unit que asume shape de `savedAgenda`**: `gapSuggestion.test.js` (`{schedule:[{_title}]}`), `storage.test.js` (`setSavedAgenda`), `state.test.js` (snapshot/update). Si el pin agrega `_pinned` por item (Enfoque B) → tocar estos.
- **Playwright**: `planner.spec.js` T03/T04/T09/T31/T36/T43 (corren `runCalc`/conflicto, festival Leviza); `miplan.spec.js` T11/T24/T25/T26/T27/T28/T40/T44 (savedAgenda, addSuggestion, Tribeca/Leviza). T36 ("sesión solapada abre modal de conflicto") y T27/T44 son los que más se rozan con el pin.
- **Contrato worker**: `calc.js:164-176` postMessage (`titles/films/watched/prioritized/availability/festivalDates/tzOffset/festivalEndTs/simTime/venueCoords/transport`). Enfoque A suma `pinned`. Cubierto implícitamente por los specs que llaman `runCalc`.

---

## 8. Interacción con `lastRemovedSlots` (restaurables)

`lastRemovedSlots` es una pila FIFO (máx `MAX_REMEMBERED_SLOTS`=5) de funciones quitadas del plan, persistida (`{key}_lastslot`). `removeFromAgenda` (`handlers.js:213`) la prepende con `_isRestored:true`; `addSuggestion` (`:278`) la limpia al re-agregar; la UI ofrece "← Restaurar" en Sugerencias si el slot original sigue libre (`agenda.js:~1313`).

**Conflicto de diseño que la sesión no resolvió:** con Enfoque A, "quitar del plan" pasa a ser "des-pinear". ¿Quitar un pin lo manda a `lastRemovedSlots` (restaurable) o solo borra el pin? ¿Restaurar un slot re-crea un pin? Hay **dos mecanismos de restauración solapados** (lastRemovedSlots vs re-pin). *Recomendación:* unificar — al des-pinear, guardar el `{day,time}` en `lastRemovedSlots`; "Restaurar" = re-pin. Evita dos verdades.

---

## 9. Recomendación

**Enfoque A** (pin como estado durable + restricción de entrada al solver) **con afordancia en la lista `Funciones` del sheet** (decisión #1-C). Razones:
1. Es la única opción que resuelve **los tres** casos de producto (elegir entre varias, comprometer con 1 sola función, comprometer fuera de intereses) **y** arregla la fragilidad de raíz.
2. **Reusa el solver** en lugar de reescribirlo: pin = colapsar `g.screens` a 1 + must-include. Cambio localizado en `baseGroups`, no en `bb()`.
3. **Esquiva la colisión de gesto** (#1-C) → cero re-mapeo de gestos conocidos, arregla el tooltip mal etiquetado de paso.
4. Encaja en la arquitectura objetivo (ARQUITECTURA §16): `pinned` es otro estado en el roster; el reframe de las ops manuales empuja hacia "Controllers explícitos".

**Condiciones para proceder (gates):**
- Resolver primero las 4 subtilezas de §5 (#3 señal pin≠prioridad, #4 filtro `screeningPassed`, fuera-de-watchlist, `is_recurring`) y la migración (§10) — son requisitos, no detalles.
- **No** abordar durante la ventana de testing de Tribeca (toca el solver, que ya rompió producción 2×). Es trabajo **post-festival**.
- Implementar tras los gates con: cambio en `schedule.js` + worker en el **mismo PR** (los `[worker-overlap]`/`[worker-deps]` lo exigen), tests unitarios nuevos antes del wiring de UI, y un PR separado para la UI/copy.

---

## 10. Lo que la sesión de diseño pasó por alto

1. **Pin fuera de watchlist no entra al solver** tal cual. `computeScenarios` solo recorre `pending=titles.filter(!watched)` y `baseGroups` sobre eso. Un pin a una peli no-interesada (caso b explícito del producto) **no aparecería** salvo que se **una** `pinned` al conjunto de títulos. Es un requisito del solver, no un detalle de UI.
2. **El pin necesita una señal de inconsatisfacibilidad propia.** `incompatiblePriorities`/`conflictingPriorityPairs` modelan prioridades que **se pueden dropear** (`priorityCost`). Un pin **no se dropea**: si dos pins chocan sin alternativa, el solver no puede satisfacer ambos → hay que **forzar la elección del usuario** con una señal distinta. Reusar el campo de prioridades sería incorrecto.
3. **El filtro `screeningPassed`/`isScreeningBlocked` del solver (`schedule.js:66`) borraría el pin huérfano en silencio** — haciendo imposible la decisión #4. Hay que exceptuar los pins de ese filtro.
4. **Interacción con `is_recurring`** (talleres que incluyen TODAS las sesiones, `schedule.js:99,116-123`): pinear UNA sesión de un recurrente es contradictorio con "incluir todas". Definir: el pin de un recurrente o no se permite, o lo degrada a no-recurrente para ese caso.
5. **Migración / back-compat.** Usuarios actuales tienen `savedAgenda` con ediciones manuales y **cero pins**. Al primer recálculo post-feature, esas ediciones se perderían igual salvo que se **migren a pins** en el load (derivar `pinned` del `savedAgenda` existente). Sin esto, el feature **introduce** la pérdida que pretende arreglar para los datos viejos.
6. **Doble mecanismo de restauración** (`lastRemovedSlots` vs re-pin) — §8.
7. **Colisión de gesto evitable** (#1-C): la sesión planteó A/B sobre el tap de la hora; la opción más limpia es no tocar ese gesto y poner el pin en el sheet.
8. **Costo de duplicación del worker**: cualquier cambio al solver es **doble** (schedule.js + extracción en calc.js). El `[worker-deps]` añadido cubre dependencias faltantes pero **no** divergencia semántica entre copias — el feature hereda esa deuda hasta la Fase 8 (worker desde import directo).

---

*Fin del análisis. No se modificó código, datos ni config. Archivo para revisión de Juan.*
