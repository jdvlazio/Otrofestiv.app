# Festival pre-commit checklist

> Toda revisión pre-commit de un festival nuevo debe pasar **todos** estos ítems.
> Derivado de la revisión crítica del onboarding de Olhar de Cinema 2026 y del
> historial de incidentes (Tribeca: 134 posters falsos, 107 sinopsis de films
> distintos, year corrupto en 37 films, lbSlugs inferidos incorrectos).
>
> **Pósters:** los ítems de abajo son los *gates*; la *regla* completa (prioridad,
> trim, cobertura, editorial) vive en **`docs/POSTERS.md`** (fuente única).

## Checklist bloqueante

- [ ] `node scripts/validate-festivals.js <id>` → **0 errores**
- [ ] `python3 validate.py` → **OK para push**
- [ ] **Procedencia (pipeline v2)**: `_provenance: true` en el root + `_src: {url, date}` en cada film (gate `[sin-procedencia]`). Dato sin fuente = dato no confiable.
- [ ] **`tools/audit.html?fest=<id>`** revisado: filtro "Solo problemas" en **0** o cada hallazgo justificado explícitamente ante Juan (una pasada visual cubre póster·metadata·sinopsis·procedencia·LB).
- [ ] **Chrome live audit del splash** (gate bloqueante): servir el repo (`python3 -m http.server`),
      abrir el selector y confirmar que la entrada del festival se ve **igual que un festival de referencia**
      (ej. Tribeca): nombre **sin año** + fechas en formato **MES día–día AÑO** (`JUN 4–13 2026`).
      Verificar también `synopsis` por idioma en vivo: ES→`synopsis_es`, EN→`synopsis_en`, fallback→`synopsis` (origen).
- [ ] **Posters**: 0 duplicados entre films + binding verificado por id/uuid
      (si el CDN/og:image embebe el id del film en el path, confirmar `poster.includes(filmId)`)
- [ ] **Posters TMDB** (si se enriquecen):
      - [ ] Búsqueda TMDB intentada con **título original Y `title_en`** (no descartar hasta probar ambos)
      - [ ] Solo `poster_path` (portrait 2:3) — **nunca `backdrop_path`** (landscape)
      - [ ] **Verificación visual** vía galería Chrome tab (`gallery.html` + `http.server`) — **obligatoria** antes de escribir
      - [ ] Overrides por transliteración (3/4 criterios + visual) **documentados en el PR** como `override: transliteración`
- [ ] **Posters de programas** (`is_cortos`/`is_programa`) — REGLA INAMOVIBLE:
      - [ ] El **body** es el **identificador único** del programa: el **número/código** (`PGM 05`) para numerados, el **nombre propio** para los nombrados. **Nunca** el descriptor de sección suelto.
      - [ ] El texto sale del **título original** (`f.title`), nunca de la traducción de UI (`f.section`). **No mezcla de idiomas** (un código es neutro; un nombre propio va en su idioma).
      - [ ] **`node scripts/validate-festivals.js` → 0 errores** en `[poster-editorial-unique]` (ningún par de programas con poster editorial idéntico). El check no da falsos positivos: si falla, es real.
      - [ ] Confirmar en Chrome (ES y EN) en cada sección con >1 programa.
- [ ] **`posterSource` clasificado**: `python3 scripts/classify-posters.py <id> --apply` corrido tras cargar los pósters — todo póster inline lleva `posterSource` (gate `[poster-source]`) y el modelo map NO existe (gate `[poster-map-legacy]`). Adquisición/anatomía/reglas → **`docs/POSTERS.md`** (no re-decidir acá).
- [ ] **Secciones nuevas registradas en `src/config.js`**: emoji único + `SECTION_EN` + arquetipo en `SECTION_ARCHETYPES` (gate `[seccion-sin-arquetipo]` — sin arquetipo la banda cae a gris ilegible).
- [ ] **Verificar en Chrome** que los cortos en `film_list` muestran imagen en el sheet del programa (portrait o editorial-con-imagen para landscapes). `poster: ""` exclusivo de programas; el landscape no se vacía — regla completa en `docs/POSTERS.md`.
- [ ] **Year**: 0 outliers no explicados (los clásicos/retro conservan su año original; los contemporáneos ≤ año_festival + 1)
- [ ] **0 sinopsis duplicadas** entre films (synopsis y synopsis_en)
- [ ] **Slots compartidos**: todos los (day, time, venue) con ≥2 films declarados `is_cortos:true` o `is_programa:true`
- [ ] **Config en el JSON**: `dayKeys`, `days`, `festivalDates`, `timezoneOffset`, `prioLimit`, `name`, `storageKey`, `festivalEndStr`
- [ ] **`timezoneOffset` = zona del VENUE** (±HH:MM). `generate-config.js` lo exige vía `--tz` y el guardián `[timezone-valid]` bloquea el merge si falta o está mal. Ej.: Argentina `-03:00`, Colombia `-05:00`, NYC `-04:00`. Sin él, el festival cae en hora de Bogotá corrido, sin error visible.
- [ ] **Entrada en `src/config.js`** (`FESTIVAL_CONFIG`) creada (id sin guion: `[a-z0-9]+`)
- [ ] **`fullName`** (nombre oficial completo, **verificado en la fuente oficial del festival**) presente en la entrada de `FESTIVAL_CONFIG` — se muestra al expandir el selector. `generate-config.js` lo exige vía `--fullname`.
- [ ] **Secciones**: emoji único por sección + orden curatorial definido
- [ ] **Programa cruzado contra la fuente oficial de convocatoria** (PDF/comunicado): coincide el conteo de films/funciones; **weekday↔fecha validado contra el año**; funciones fuera de la ventana = bandera roja (contenido reciclado de edición pasada — lección FantasoFest 2026)
- [ ] **Secciones = nombres OFICIALES** de la fuente (jamás etiquetas propias tipo "Selección Oficial" — lección TT 2026, PR #295)
- [ ] **Imágenes de cada ficha inventariadas** (afiche oficial de sesión = póster de bloque; no leer solo texto — lección TT 2026, PR #297)
- [ ] **Póster corresponde a ESE film** cuando el director tiene varias obras (buscar el asset por título; `AFICHE-Lqv`≠La Virgen — lección FantasoFest)
- [ ] **`title_en` = título internacional OFICIAL** verificado (LB/circuito), NUNCA traducido; sin oficial → sin `title_en`. (`synopsis_en` sí se traduce si no hay oficial.)
- [ ] **Funciones no confirmadas por la fuente operativa** marcadas `_pendiente` (no modelar lo anunciado sin ficha/boleta)
- [ ] **`ticket_url` por film** si el material oficial trae link de compra por sesión
- [ ] **`synopsis_es`** presente para todos los films solos
- [ ] **`synopsis_lang`** declarado en cada film
- [ ] **Localización de contenido** (traducción del contenido del festival, no de UI):
      - [ ] **Chrome live audit en EN** — verificar que **secciones, país y sinopsis** no quedan en el idioma de origen.
      - [ ] **`validate-festivals.js [i18n-content-coverage]`** pasa sin warnings inesperados antes del merge (films sin `synopsis_es`/`synopsis_en`/`title_en`, secciones sin `section_en`).
- [ ] **Títulos de programas** son nombres editoriales reales del sitio
      (no artefactos del proceso como "PGM 01" sin contexto, ni placeholders)
- [ ] **Venues con `lat`/`lng`** (geocoding corrido y verificado contra el mapa)
- [ ] **`tools/enricher.html`** actualizado con el festival (lista FESTIVALS)
- [ ] **`tasks.md`** actualizado con estado y deuda downstream
- [ ] `node scripts/bump-version.js` corrido
- [ ] **CI verde** antes del merge (validate-festivals + validate.py + Playwright)

## Checks automáticos de corrupción (en validate-festivals.js)

Estos labels, si aparecen, bloquean o advierten — no ignorarlos:

| Label | Nivel | Qué detecta |
|---|---|---|
| `[posters-duplicados]` | ERROR | dos films con la misma URL de poster |
| `[sinopsis-duplicada]` | ERROR | cross-contaminación de synopsis/synopsis_en |
| `[poster-map-legacy]` | ERROR | `posters{}`/`customPosters{}` a nivel raíz (modelo muerto jul 2026) |
| `[poster-source]` | ERROR | póster inline sin `posterSource` (correr classify-posters) |
| `[seccion-sin-arquetipo]` | ERROR | sección sin entrada en `SECTION_ARCHETYPES` (banda gris ilegible) |
| `[sin-procedencia]` | ERROR | film sin `_src:{url,date}` en festival con `_provenance:true` (pipeline v2) |
| `[poster-host]` | WARNING | póster en host fuera de whitelist (re-hostear en `/assets/`) |
| `[year-sospechoso]` | WARNING | year > festival+1 sin ser clásico/retro |
| `[slot-sin-agrupar]` | WARNING | programa de cortos sin modelar |
| `[sinopsis-truncada]` | WARNING | huella de og:description truncada (200 chars, trampa A2) |

## Deuda downstream aceptable

Estos campos **pueden quedar para después del primer commit** sin bloquear el merge:

- **`genre` + `lbSlug`** — `enrich-festival.py` (gate v2 con `--selftest`; year verificado antes). El slug sale del TMDB id que pasó el gate; verificación final = GET a la página LB (200 + director coincide). Rechazos con título ~1.0 se auditan (rechazo ≠ ausencia); método Chrome tab solo como rescate para films fuera de TMDB.
- **Section emoji final** — la asignación curatorial de emoji + orden puede afinarse post-commit (Content-Designer).
- **Posters de programas** (`is_cortos`/`is_programa`) — poster generativo/editorial.

> Regla: la deuda aceptable es la que NO afecta integridad de datos ni rompe el
> planner. Posters/sinopsis/year/slots NO son deuda aceptable — son bloqueantes.
