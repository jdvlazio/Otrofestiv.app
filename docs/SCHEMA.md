# Otrofestiv — Festival Data Schema

Documento normativo. Toda discrepancia entre este archivo y el código es un bug.
Última actualización: 2026-05-07 — commit 1f6f290

---

## Estructura raíz del JSON

```json
{
  "_status": "string — descripción del estado del archivo",
  "_source": "string — URL o descripción de la fuente",
  "_extracted": "string — fecha de extracción ISO",
  "_total": "number — total de films",
  "config": null,
  "transport": "string — 'transit' | 'driving' | 'walking'",
  "venues": { ... },
  "posters": { ... },
  "customPosters": { ... },
  "lbSlugs": { ... },
  "prioLimit": 5,
  "ticket_url": "string — URL https:// de entradas (opcional)",
  "ticketing_model": "string — 'paid' | 'mixed' (obligatorio si ticket_url existe)",
  "sharedSlotIsOneScreening": "bool — opt-in: dos obras en el mismo día+hora+sala son UNA función",
  "films": [ ... ]
}
```

### Proyecciones conjuntas — los DOS modelos canónicos (doctrina, 30 jul 2026)

Los festivales juntan proyecciones, y van a seguir haciéndolo: un bloque curado
de cortos, un corto antes de un largo, dos mediometrajes en una función.
**Tenemos arquitectura para ambos casos — no se inventa un tercer modelo.**
(El precedente: para Cinemancia 2025 se ideó una «función doble» con póster
partido a la mitad. Nunca llegó al código y quedó obsoleta: sus dos slots
compartidos son exactamente los casos que estos modelos resuelven.)

| | **A · PROGRAMA** | **B · ANCLAJE** |
|---|---|---|
| Qué es | El festival curó un contenedor con nombre («…— Programa 1», «FINQUITA») | Obras independientes que comparten función, sin contenedor |
| Cómo viene | Una entrada `is_cortos` + `film_list` | N entradas normales + `sharedSlotIsOneScreening: true` en la raíz |
| Entidad en la app | El programa (las obras viven dentro; ficha propia vía `openCortoSheet`) | Cada obra (ficha y card **independientes** — nunca fusionadas) |
| Interés/Plan opera sobre | El programa completo | La obra; sus compañeras se suman/quitan en simetría |
| Aviso en ficha | `⟨PROGRAMA⟩ Verás los otros cortos` | `⟨PROGRAMA⟩ Verás las otras obras` |

**Regla de decisión en onboarding:** ¿el festival le puso NOMBRE al conjunto?
→ Programa. ¿Son obras con identidad propia que comparten horario? → Anclaje.
La duda se resuelve contra el programa oficial del festival, nunca por deducción
(guardián `[slots-sin-decidir]` obliga a decidir; ver abajo).

**Lo que la app garantiza en ambos modelos, transversal a todos los tabs** (el
dominio es el dueño; ninguna vista calcula por su cuenta):

- **Conflictos** — `screensConflict`: las obras de una función no rivalizan.
- **Duración** — el par `blockDuration` (fin del bloque, sin Q&A: «¿hasta qué
  hora estoy en la sala?») / `effectiveDuration` (bloque + Q&A: «¿cuánto ocupa
  la sala?» — conflictos), con `durationForTravel` como dueño de la doctrina del
  Q&A (compromete solo con traslado) y `screeningEndDate` como fin canónico
  absoluto («¿ya terminó?») y `delayedEndMin` (fin + retraso reportado — «termina
  en X» y el margen hacia la siguiente). Consumido por huecos de sugerencias,
  «termina en X», en-curso, buffer de retrasos, el orden del optimizador y el
  EXPORT a calendario (ICS + iOS). Guardianes: `[duracion-solo-dominio]` (fuera
  de `src/domain/` nadie parsea `duration`; única excepción: el sellador) y
  `[fin-inline-ratchet]` (la aritmética de fin inline fuera del dominio tiene
  techo — código nuevo usa los dueños).
- **Mi Plan** — la lista no mide huecos ni avisa Q&A entre obras del mismo slot;
  el calendario dibuja **un bloque por función** con todas sus obras.
- **Ficha** — hereda funciones y avisos (banda AVISOS); Q&A contado UNA vez.
- **Escritura del plan** — `commitPlan` (persistence.js) es el ÚNICO camino de
  mutación de `savedAgenda`; certifica cada escritura con `verifyPlan` (el
  mismo certificador del oráculo del planeador) — report-only en producción,
  duro en tests (`__PLAN_STRICT__`). Las 2 puertas de hidratación (loader +
  nube) normalizan vía `syncScheduleWithCatalog`. Guardián:
  `[plan-write-chokepoint]`.
- **Plan guardado** — `syncScheduleWithCatalog` (31 jul 2026): una entrada de
  `savedAgenda` guarda la ELECCIÓN (título+día+hora); todo lo demás se re-deriva
  de la función viva en cada hidratación (loader y nube). Un plan guardado antes
  de un cambio de catálogo nunca vuelve a mentir. Sin match exacto la entrada
  queda intacta — territorio del camino de avisos. Guardián:
  `[plan-sync-en-puertas]`.

### Festivales MULTICIUDAD — `city` por sede

Cada entrada de `venues` puede declarar `city`. Con eso la app hace dos cosas,
ambas automáticas (sin flags ni cambios de pipeline):

- **Display** — badge `venue-municipio` bajo el nombre de la sede y ciudad en la
  dirección de su ficha, cuando difiere de `FESTIVAL_CONFIG[id].city`
  (Cinemancia 2025, 10 municipios del Valle de Aburrá).
- **Filtro de lugar con nivel de ciudad** (5 ago 2026) — cuando hay **≥2
  ciudades distintas y no vacías** entre las sedes visibles, el dropdown pasa a
  dos niveles: ciudades (con su conteo) → «‹ Ciudades» + la ciudad (filtra
  entera) + sus sedes. Con una sola ciudad el filtro queda plano, idéntico a
  siempre. Motivo: FICDEH 2026 tiene 131 sedes en 11 ciudades — la lista plana
  eran 12,5 pantallas de scroll en 390×844.
  El predicado es `venueMatches(venue, sel)` (`view/helpers.js`), dueño único:
  `sel` es `'all'`, un short de sede, o el centinela `'city:<Ciudad>'`.
  **Ojo con el borde**: FINCA declara `city` en 1 de 6 sedes — por eso la regla
  exige DOS ciudades distintas, no «¿hay city?».

### `sharedSlotIsOneScreening` — anclaje de función (opt-in, 29 jul 2026)

Algunos festivales programan **dos obras en una misma función**: un corto o
mediometraje y después un largo, mismo día, hora y sala, con una sola cabecera
de horario en su programa. Con este flag en `true`, el loader detecta esos
grupos (`día|hora|sede|sala`) y marca cada obra con `_slotKey`, `_slotDur`
(suma de las obras — el fin del bloque) y `_slotMin` (con el Q&A — conflictos), y
el dominio entonces:

- **no las declara en conflicto entre sí** — con una entrada se ven las dos;
- **ocupa la sala por la SUMA de ambas** (+30 del Q&A **una sola vez**: es una
  charla al final de la función, no una por obra). Sin esto el planificador cree
  que salís al terminar la primera y te ofrece otra función a la que no llegás.

Además, la función es **una unidad en las dos direcciones**: agregar una obra
anclada suma sus compañeras a Intereses y quitarla las quita —incluido su lugar
en el plan guardado—. La ficha lo anuncia con `meta_funcion_incluye`.

> La simetría no es cosmética. Con el quitar individual, quien agregaba una obra
> y se arrepentía quedaba con la compañera en Intereses —que nunca eligió— y con
> la franja igual reservada. Con un corto el problema no existe porque su botón
> opera sobre el programa: ahí hay una sola entidad. Acá hay dos que deben
> comportarse como una.

> ⚠️ **Es opt-in a propósito, no se puede derivar.** En sedes multisala (Tribeca:
> «AMC 19th St. East 6», «Village East by Angelika») misma hora y sede es **otra
> sala = otra función**, y anclarlas sería un error. Solo lo declara el festival
> cuyo programa lo confirma. FINCA 2026 es el primero: 6 casos, verificados uno
> a uno contra su documento día por día.

**Nota formato:** Los festivales desde Jardín 2026 no incluyen `config{}` en el JSON — la configuración vive en `FESTIVAL_CONFIG` de `index.html`. Los festivales legacy (FICCI 65, Cinemancia 2025) sí incluyen `config{}`.

**Ticketing (campos opcionales del root):**
- `ticket_url` — URL `https://` de la página oficial de entradas. Si existe, el sheet de función muestra un bloque con link (oculto cuando `festivalEnded()`). Ausencia de `ticket_url` = festival gratuito (no muestra nada).
- `ticketing_model` — `"paid"` (todo pago, ej. Tribeca → link "Comprá tu entrada →") o `"mixed"` (pago + gratis, ej. Olhar → meta-banner "Funciones pagas y gratuitas"). **Obligatorio si `ticket_url` existe.**
- En festivales `"mixed"`, marcar funciones gratuitas con `is_free: true` por screening (ver Screenings). El card muestra badge "GRATIS"; el sheet oculta el bloque solo si **todas** las funciones del film son gratuitas.
- Ambos campos se absorben vía el whitelist `_cfgFields` en `loader.js` — un campo root nuevo que no esté ahí se descarta en silencio.

---

## Venues

```json
"venues": {
  "Nombre completo del venue": {
    "short": "Nombre corto para el card (≤ 20 chars)",
    "address": "Dirección completa",
    "room": "Sala 3 — opcional, solo sedes MULTISALA (ver abajo)",
    "lat": 0.0,
    "lng": 0.0
  }
}
```

**Reglas:**
- La clave ES el nombre completo — sin abreviaciones
- `short` es lo que ve el usuario en el card
- Coordenadas requeridas para la vista de mapa
- Los nombres de venue en `film.venue` y `film.screenings[].venue` deben ser claves exactas de este objeto

#### Sedes MULTISALA — una sala, una sede

Un complejo con varias salas (Colombo Americano 1/2/3, Cinemateca de Bogotá,
Plaza Bocagrande 1–5 en FICCI 65) se monta como **una entrada de `venues` por
sala**: clave propia, **mismo `short`** (el edificio) y **las mismas
coordenadas**. Con eso, y sin nada más:

- son **funciones distintas** y nunca se funden;
- dos a la misma hora **entran en conflicto** (no podés estar en dos salas);
- encadenar una tras otra **no cuesta viaje** (0 min, mismas coordenadas);
- el **filtro de Lugar las agrupa por edificio** — elegir «Cinemateca» trae sus
  tres salas, que es lo que uno quiere.

> Ojo: por eso `sharedSlotIsOneScreening` es **opt-in**. En una sede multisala,
> misma hora + misma sede es **otra sala = otra función**, y anclarlas sería un
> error.

**`room` — cómo se llama la sala.** Opcional. Si no se declara, la app la deduce
del nombre de la sede, pero **solo entiende salas numeradas** (`Sala 3`,
`Salón 1`). Una sala con nombre propio —«Sala Capital» de la Cinemateca— se
pierde: el asistente llega al edificio sin saber a cuál entrar. Se declara ahí.

Dueño único: `sala(venue)` (`view/helpers.js`) — declarado gana sobre deducido —
y `venueLabel(venue)` arma el «Edificio · Sala» que se exporta al calendario.

**Regla de onboarding:** si dos sedes comparten `short`, cada una necesita su
sala. Si no la tienen, no son salas: son la misma sede escrita de dos formas
(FICCI 65 tiene cuatro de esos duplicados: `AECID`/`aecid`,
`Auditorio Nido`/`Auditorio nido`…) y hay que fusionarlas.

---

## Films

```json
{
  "title": "string — requerido",
  "slug": "string — requerido para Tribeca/festivales con URL propia",
  "section": "string — requerido",
  "type": "string — 'film' | 'event' | 'short'",
  "filmType": "string — descripción textual del tipo (de la fuente)",
  "director": "string",
  "duration": "number — minutos",
  "country": "string",
  "language": "string",
  "premiere": "string — 'World Premiere' | 'International Premiere' | ...",
  "synopsis": "string",
  "poster": "string — URL completa (https://...), path de assets (/assets/<id>/x.png) o path TMDB (/x.jpg). Prioridad, cobertura y reglas: docs/POSTERS.md",
  "posterPosition": "string — 'center' | 'top' | 'bottom' (default: 'center')",
  "genre": "string",
  "year": "number",
  "flags": "string — emojis de banderas de países",
  "day": "string — KEY del dayKeys del festival (REQUERIDO para filtrado)",
  "date": "string — ISO date '2026-06-03' (requerido si screenings[] existe)",
  "time": "string — '10:30 AM' formato 12h",
  "venue": "string — debe ser clave exacta de venues{}",
  "info": "boolean — opcional, SOLO type:event — evento informativo (ver abajo)",
  "screenings": [ ... ]
}
```

### Campo `info` — eventos informativos (no planificables)

`info: true` (solo en `type:'event'`) marca un evento **drop-in / sin hora fija**
cuya duración no es controlable: exposiciones, visitas guiadas, recorridos,
fiestas, conciertos, performances, presentaciones virtuales.

- **Aparece en el programa** como cualquier evento, pero **NO entra al plan ni a
  conflictos:** `screensConflict` lo ignora y `computeScenarios` lo excluye del
  plan generado (ambos en `domain/schedule.js`, guard aditivo por `f.info`).
- **El default es planificar.** La app es un **planificador**, no un tablón
  informativo — `info` es la **excepción mínima**. Un evento con hora fija
  (masterclass, conversatorio, panel, gala, bloque de cortos) NO lleva `info`:
  lleva `duration` (estimada si hace falta) y SÍ se planifica.
- Regla de clasificación al montar: *¿el asistente "reserva" ese horario?* Sí →
  `duration` (planificable). No (entra/sale cuando quiere) → `info: true`.
- `info` se propaga a los screenings exploded vía el `Object.assign` del loader.

### Bloques de cortos: `is_cortos` + `film_list` (+ `unscheduled`)

Un **bloque de cortos** agrupa varios cortometrajes que se proyectan juntos:

```jsonc
{ "title": "Cortometraje Documental", "section": "📽️ Cortometrajes",
  "type": "event", "is_cortos": true, "flags": "<derivado>",
  "film_list": [ { "title": "Madres de nacimiento", "director": "...",
                   "country": "Colombia/Francia", "genre": "Documental",
                   "duration": "18 min" }, ... ] }
```

- `is_cortos: true` **requiere** `film_list` no vacío (guard bloqueante en
  `validate-festivals.js` — un bloque vacío invisibiliza cortos que sí están).
- Cada item del `film_list` es **buscable como card propia** (`_searchAll` los
  indexa; `_searchOpenCorto` abre su detalle). `flags` del bloque se **deriva**
  de los países del `film_list`. Póster por item vía `getCortoItemPoster` (sin
  póster → fallback editorial). Sinopsis = pase de Content Design aparte.

**`unscheduled: true`** — catálogo de cortos **sin sesión asignada todavía**: el
corto está EN el festival pero el festival aún no publicó en qué jornada va. Vive
en **buscador + Explorar**, NO bajo un día concreto. Es la única excepción a la
regla day/time de abajo: `is_cortos + unscheduled + film_list` **no exige
`day`/`time`/`venue`** (exento en `validate-festivals.js` y en `validateFilm`).
Cuando el festival publique la programación, se le asigna `day`/`time`/`venue` y
deja de ser `unscheduled`. **Regla de criterio:** un corto sin horario se monta
igual (catálogo) — nunca se "pausa" fuera del JSON.

### Campo `day` — regla crítica

`day` debe ser una clave exacta de `FESTIVAL_CONFIG[id].dayKeys`.

- **Formato legacy** (FICCI, AFF): `day` = key legible, e.g. `"MAR 21"`, `"VIE 24"`
- **Formato ISO** (Tribeca, Jardín): `day` = ISO date, e.g. `"2026-06-03"`

Cuando el film tiene `screenings[]`, el campo `day` del film raíz se toma del primer screening.

**El validator falla si `day` no está en `dayKeys`.**

---

## Screenings (array por función)

Usado cuando un film tiene múltiples funciones en días/horarios/venues distintos.

```json
"screenings": [
  {
    "date": "string — ISO date '2026-06-03' (requerido)",
    "day": "string — KEY del dayKeys (opcional, se deriva de date si falta)",
    "time": "string — '10:30 AM'",
    "venue": "string — clave exacta de venues{}",
    "is_free": "boolean — opcional, solo festivales 'mixed': marca función gratuita"
  }
]
```

`is_free` se absorbe en la explosión de screenings (whitelist en `loader.js`). Solo aplica a festivales con `ticketing_model: "mixed"`.

**Regla de explosión:** el sistema convierte `screenings[]` en objetos film planos usando:
```javascript
day: s.day || s.date   // ← CRÍTICO: siempre usar ambos por compatibilidad
date: s.date || s.day
```

**Si solo existe `date` (sin `day`), el sistema lo normaliza automáticamente.**
El validator debe advertir si ninguno de los dos existe.

---

## FESTIVAL_CONFIG en index.html

Campos requeridos por festival:

```javascript
{
  name: 'Nombre común/marca',   // display = 1ª palabra + ' · ' + year (festivalLabel)
  fullName: 'Nombre oficial completo',  // OBLIGATORIO — verificado en fuente; visible al expandir el selector
  shortName: 'ABREVIACIÓN',     // deprecado para display
  city: 'Ciudad',
  dates: 'FEB 3–14',        // ES
  dates_en: 'FEB 3–14',     // EN
  year: 2026,
  timezoneOffset: '-05:00',  // OBLIGATORIO, ±HH:MM (validado por [timezone-valid]).
                             // Es la zona del VENUE — ancla "ahora"/contador/pasó-futuro
                             // a la hora del festival, no del dispositivo. Argentina -03:00,
                             // Colombia -05:00, NYC -04:00. Sin él (o mal), el festival cae
                             // en hora de Bogotá corrido, sin error visible → el guardián lo
                             // bloquea. generate-config exige --tz.
  storageKey: 'id_',
  festivalEndStr: '2026-02-14T23:59:00',
  festivalDates: { dayKey: isoDate },
  days: [{ k: dayKey, d: dayNumber, lbl: 'LUN' }],
  dayKeys: ['key1', 'key2', ...],
  dayShort: { dayKey: 'LUN 3' },
  dayShort_en: { dayKey: 'MON 3' },
  dayLong: { dayKey: 'Lunes 3 de febrero' },
  eventPosterLabel: ['LABEL1', 'LABEL2'],
  films: null,
  posters: null,
  lbSlugs: {}
}
```

**`dayKeys` deben coincidir exactamente con los valores de `film.day` en el JSON.**

---

## i18n — Reglas

- Toda string visible al usuario debe usar `t('key')`
- **Prohibido:** strings hardcodeadas en ES o EN dentro de templates HTML en `index.html`
- Excepción: nombres propios, nombres de festival, títulos de film
- Toda clave nueva debe añadirse a AMBOS archivos (`es.json` y `en.json`) en el mismo commit
- El validator compara keys de `en.json` vs `es.json` — deben ser idénticas

---

## Pre-push checklist (obligatorio para cambios en index.html)

```
[ ] node scripts/validate-festivals.js → 0 errores
[ ] VERIFICACIÓN DE SINTAXIS JS (obligatorio, <1 segundo):
    node -e "const h=require('fs').readFileSync('index.html','utf8');[...h.matchAll(/<script>([\s\S]*?)<\/script>/g)].forEach((m,i)=>{try{new Function(m[1]);console.log('Script',i,'OK')}catch(e){console.error('Script',i,'ERROR:',e.message);process.exit(1)}})"
[ ] Diff review completo — no solo el fragmento modificado
[ ] Smoke test en browser:
    [ ] Splash carga con festival correcto como default
    [ ] Grilla Programa muestra films y posters
    [ ] Sheet de un film: día visible (no UNDEFINED), venue, hora
    [ ] Tab Intereses: carga sin error de consola
    [ ] Consola: 0 errores nuevos
[ ] str_replace verificado: leer las líneas modificadas con sed antes de commitear
```

---

## Regla de onboarding de festival nuevo

**Esta regla es la más importante del documento.**

Cuando se monta un festival nuevo, el trabajo es:

1. Copiar la estructura de datos del festival más reciente
2. Replicar exactamente el mismo pipeline: extracción → enrichment → FESTIVAL_CONFIG
3. No modificar ningún componente visual existente
4. No proponer mejoras visuales durante el onboarding
5. Si el festival nuevo tiene algo que los anteriores no tienen (ej: imagen editorial 16:9), se para, se hace un mockup, se presenta, se espera aprobación explícita antes de tocar código

**Lo que no es aceptable:**
- Modificar `makeFilmPlaceholder`, `makeEventPoster`, `makeProgramPoster`, `_buildPosterV16` durante el onboarding de un festival
- Añadir componentes visuales (badges, overlays, nuevos tipos de card) sin aprobación
- Cambiar proporciones, colores o tipografía de componentes existentes
- "Mejorar" algo que no se pidió mejorar

**La pregunta antes de cada cambio:**
¿Me pidieron esto explícitamente? Si la respuesta no es "sí", no se hace.



### Arquitectura

**ARCH-R1 — Una función, una definición en el scope del main thread.**
Las funciones duplicadas en `index.html` son del Web Worker (scope separado, legítimo). No eliminar.

**ARCH-R2 — Detección de poster editorial.**
Usar `_isEditorialPoster(f)` en todo el código. Esta función lee `f.posterSource` primero.
Nuevos festivales **deberían** incluir `posterSource: 'editorial'` cuando la imagen es editorial.
Estado real y deuda (hoy la detección operativa es por host vía `_isEditorialImageUrl`; `posterSource` está sin adoptar): ver `docs/POSTERS.md §5`.

**ARCH-R3 — Constantes de módulo, no locales.**
`SECTION_COLORS`, `SECTION_ORDER_LIST`, `_sectionColor()`, `_secLabel()`, `_isEditorialPoster()` viven al nivel de módulo, antes de `_buildPosterV16`. No redefinir dentro de funciones.

**ARCH-R4 — Cero `console.log` en producción.**
Usar `if(DEBUG)console.log(...)` o eliminarlo. El flag `DEBUG` se activa solo en desarrollo.

---

### Componentes

**COMP-R1 — Sheet compacto con 3+ funciones.**
`openPelSheet` añade clase `.compact` cuando `totalFn >= 3`. El CSS reduce el poster de 96→72px.
Regla: el CTA primario debe ser visible sin scroll en el primer viewport.

**COMP-R2 — `_secLabel(sec)` en todos los contextos.**
Nunca usar `.replace(/^\S+ /, '')` ni `.replace(/^[^ ]+ /, '')` para limpiar nombres de sección.
Usar `_secLabel(sec)` — solo elimina prefijo emoji, preserva palabras como "U.S.", "Free", "Escape".

**COMP-R3 — Scroll en sheets.**
Toda función que abre el sheet hace `document.getElementById('pel-sheet').scrollTop = 0`.
Toda función que abre el sheet añade `-webkit-overflow-scrolling: touch` al contenedor.

---

### Visual

**VIS-R1 — Tres tipos de card, tratamiento visual distinto:**
1. TMDB: imagen pura 2:3, sin intervención, sin sólido de sección.
2. Editorial (cloudfront): sólido de sección 52px + imagen 16:9 + título anclado abajo.
3. Generativo (sin imagen): sólido de sección 52px + caja oscura + título. Sin texto "NO POSTER".

**VIS-R2 — `makeFilmPlaceholder` siempre recibe `section`.**
Firma: `makeFilmPlaceholder(title, director, year, section)`.
El header usa `_sectionColor(section)`. Si no hay `section`, color fallback `#2C2C2A`.

**VIS-R3 — Grilla con affordance de scroll.**
`poster-grid` tiene `padding-right: 20px` para que la cuarta columna asome.

---

### Copy e i18n

**COPY-R1 — El campo `synopsis` en el JSON no contiene metadatos de proceso.**
Nunca guardar `⚠️ INGLÉS —` u otros prefijos en el dato. El dato es el dato.

**COPY-R2 — Toda string visible al usuario pasa por `t()`.**
Sin excepciones en templates. Incluye: Q&A labels, registro, premieres, empty states.

**COPY-R3 — `premiere` se muestra tal cual, sin `.toUpperCase()`.**
El valor en el JSON ya viene en el case correcto desde la fuente.

**COPY-R4 — Paridad ES/EN obligatoria.**
Toda key nueva se añade a `es.json` Y `en.json` en el mismo commit.
El validator (RULE 9) bloquea el push si hay desalineación.

---

### Mobile

**MOB-R1 — `-webkit-overflow-scrolling: touch` en todo scroll container.**
`.pel-sheet`, `.prio-strip-row`, `.hscroll-strip`, `.mplan-wk-outer`, `.ag-excl-strip`.

**MOB-R2 — Tap targets mínimo 44px.**
Botones de acción: `min-height: 44px`. Si el visual es más pequeño, usar `padding` para expandir el área táctil sin cambiar el tamaño visual.

---

### Deuda técnica registrada (no bloqueante)

- 13 inline onclick handlers con >40 chars — deben migrar a funciones nombradas
- FICCI/AFF/Cinemancia tienen `config{}` en el JSON (formato legacy) — no afecta runtime
- Cinemancia2025 en FESTIVAL_CONFIG falta `dayShort`/`dayShort_en`/`dayLong`
- Detección por URL en `_isEditorialPoster` como fallback — migrar a `posterSource` en todos los festivales



| Error | Causa | Fix |
|---|---|---|
| `SyntaxError: Unexpected token '?'` | `str_replace` eliminó código adyacente | Verificar diff post-reemplazo |
| `renderSbar is not defined` | Función eliminada en refactor, llamada no eliminada | Inventario de funciones antes de borrar |
| `UNDEFINED` en día del sheet | `s.day` undefined en screenings con formato ISO | `s.day \|\| s.date` en la explosión |
| Strings hardcodeadas ES en festival EN | Templates con strings literales en vez de `t()` | Toda string de UI pasa por `t()` |
