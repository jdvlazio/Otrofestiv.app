# Festival pre-commit checklist

> Toda revisión pre-commit de un festival nuevo debe pasar **todos** estos ítems.
> Derivado de la revisión crítica del onboarding de Olhar de Cinema 2026 y del
> historial de incidentes (Tribeca: 134 posters falsos, 107 sinopsis de films
> distintos, year corrupto en 37 films, lbSlugs inferidos incorrectos).

## Checklist bloqueante

- [ ] `node scripts/validate-festivals.js <id>` → **0 errores**
- [ ] `python3 validate.py` → **OK para push**
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
- [ ] **Posters de programas** (`is_cortos`/`is_programa`): ninguno muestra el nombre de la sección en el body — verificar visualmente en Chrome para **cada sección con más de un programa** (que no queden dos posters idénticos). `makeProgramPoster` lo limpia automáticamente, pero confirmar en vivo.
- [ ] **Year**: 0 outliers no explicados (los clásicos/retro conservan su año original; los contemporáneos ≤ año_festival + 1)
- [ ] **0 sinopsis duplicadas** entre films (synopsis y synopsis_en)
- [ ] **Slots compartidos**: todos los (day, time, venue) con ≥2 films declarados `is_cortos:true` o `is_programa:true`
- [ ] **Config en el JSON**: `dayKeys`, `days`, `festivalDates`, `timezoneOffset`, `prioLimit`, `name`, `storageKey`, `festivalEndStr`
- [ ] **Entrada en `src/config.js`** (`FESTIVAL_CONFIG`) creada (id sin guion: `[a-z0-9]+`)
- [ ] **Secciones**: emoji único por sección + orden curatorial definido
- [ ] **`synopsis_es`** presente para todos los films solos
- [ ] **`synopsis_lang`** declarado en cada film
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
| `[year-sospechoso]` | WARNING | year > festival+1 sin ser clásico/retro |
| `[slot-sin-agrupar]` | WARNING | programa de cortos sin modelar |
| `[sinopsis-truncada]` | WARNING | huella de og:description truncada (200 chars, trampa A2) |

## Deuda downstream aceptable

Estos campos **pueden quedar para después del primer commit** sin bloquear el merge:

- **`genre`** — enriquecimiento TMDB estricto (los 4 criterios; year debe estar verificado antes).
- **`lbSlug`** — Letterboxd (método Chrome tab, verificar cada slug individualmente; nunca inferir del título).
- **Section emoji final** — la asignación curatorial de emoji + orden puede afinarse post-commit (Content-Designer).
- **Posters de programas** (`is_cortos`/`is_programa`) — poster generativo/editorial.

> Regla: la deuda aceptable es la que NO afecta integridad de datos ni rompe el
> planner. Posters/sinopsis/year/slots NO son deuda aceptable — son bloqueantes.
