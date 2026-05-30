# tasks.md — estado de tareas

## Onboarding · Olhar de Cinema 2026 (`olhar-2026`)

Festival #1 onboardeado con el pipeline nuevo y el **método A2 (SPA client-rendered)**.
Curitiba, Brasil · 4–13 jun 2026 · 80 films · 58 entries (46 films + 12 programas) · 6 sedes.

### Completo ✅
- [x] Extracción A2 (80 films, loop auto-avanzante por DOM renderizado)
- [x] Posters 80/80 (og:image, binding verificado por UUID — 0 falsos)
- [x] synopsis (PT, del cuerpo) 80/80 · synopsis_en 80/80 (sitio bilingüe)
- [x] duration 80/80 · country PT→ES + flags 80/80
- [x] Funciones (day/time/venue/day_order ISO) + has_qa (film-level)
- [x] Agrupación de cortos/programas: 12 programas (11 `is_cortos` + 1 `is_programa`), 0 slots compartidos
- [x] Títulos de programa = nombres oficiales del sitio (8 PGM exactos; 3 Acessibilidade desambiguadas por familia; 1 doble construido)
- [x] Geocoding 6/6 sedes (verificado en Curitiba)
- [x] `FESTIVAL_CONFIG['olhar2026']` en `src/config.js` + config root en el JSON
- [x] `synopsis_es` 46/46 films solos (traducción PT→ES inline en chat, gate aprobado)
- [x] 5 checks de corrupción en `validate-festivals.js` (+ negative tests) · `docs/FESTIVAL-CHECKLIST.md` · `festival-template.json` reconciliado · `tools/enricher.html` actualizado
- [x] `validate-festivals.js` 0 errores · `validate.py` OK para push

### Downstream (no bloqueante) ⏳
- [ ] `genre` (0/47) — enriquecimiento TMDB estricto (year confiable → matching seguro)
- [ ] `lbSlug` — Letterboxd (método Chrome tab, verificar cada slug)
- [ ] Section emoji + orden curatorial (Fase 2/5, Content-Designer)
- [ ] `tools/enricher.html` — agregar `olhar-2026` a la lista FESTIVALS
- [ ] Posters de los 12 programas (generativo/editorial)

### Deuda de pipeline detectada
- `geocode-venues.py`: falla en nombres de sublocal (Nominatim) → necesita campo `geo_query` override.
- `festival-template.json` dice JSON={venues,films}-only, pero `validate.py` + loader exigen config en el JSON → reconciliar el template.
- `has_qa` es film-level (el loader no transporta Q&A por-función) → Olhar perdió granularidad.

## Deuda i18n — keys muertas (RESUELTA ✅)

Detectadas durante el onboarding de PT (Lote 3): `label_director`, `label_synopsis`,
`label_duracion`, `label_valoracion` existían en `_I18N` (es+en) pero ningún código
las consumía (0 usos de `t()`/`data-i18n`). **Borradas de es/en** en el PR de
limpieza tras cerrar PT. Nunca se tradujeron a PT (habría sido copy invisible).
Resultado: `_I18N` queda en 340 keys es/en/pt — paridad total, 100% pt-BR.

## Deuda i18n — `DAY_A` + header "Tu {día} en" (RESUELTA ✅)

`DAY_A` hardcodeado (4 sitios: `agenda.js` + 3× `sheets-controller.js`) eliminado y
enrutado por `dayLabel()` lang-aware con `DAY_SHORT_PT` (mapa ES→PT en `loader.js`).
Header → `t('plan_tu_dia_en',{dia})` + nombre del festival; fallback `'Hoy'` → `t('bar_hoy')`.
Bonus: `DAY_A` nunca matcheaba festivales con claves ISO → ahora funciona para todos.

## Deuda i18n — ternarios binarios ES/EN que caen a ES en PT (RESUELTA ✅)

Tres últimos leaks de hardcode/ternario que no pasaban por `t()` y caían a ES en PT,
arreglados en un PR combinado (`feat/fix-lang-ternarios`):

1. **`dayChip()`** (`helpers.js`) tenía el mismo patrón binario que tenía `dayLabel()`:
   `_ds = _lang==='en' ? DAY_SHORT_EN : DAY_SHORT` → en PT caía a `DAY_SHORT` (ES) y además
   priorizaba `DAY_ABBR[key]` (abreviatura ES del festival). Day-chips mostraban abreviatura
   ES en PT (MIÉ en vez de QUA). Fix: 3-way usando `DAY_SHORT_PT`, análogo a `dayLabel()`.
2. **dtab labels** (`loader.js`): el build del dtab era binario (`_dtabLbl=_lang==='en'?...`)
   y el fallback legado de `_applyI18nDOM` (`i18n.js`) solo leía `lblEn`/`lblEs`. Fix:
   `_dtabLblPT` + `dataset.lblPt` + ramas PT en ambos sitios.
3. **`_kindMap`** (`components.js`): `_lang==='en'?_kindMapEN:_kindMapES` → PT caía a ES.
   Fix: `_lang==='es'?_kindMapES:_kindMapEN` (PT reutiliza EN, términos internacionales).

> El leak del **countdown** (`misc_days`) se arregló en el PR del countdown (#116) y el del
> header + `DAY_A` en el refactor `dayLabel()` (#117).

## Auditoría de Planear — hallazgos

Auditoría formal de `computeScenarios` + `screensConflict` (el feature core, nunca
revisado antes). 3 bugs principales + secundarios.

### Bug #1 — el índice 0 ("Tu plan") podía omitir una prioridad (RESUELTA ✅ · PR #122)
Cuando `priorityCost>0`, el sort final ordenaba solo por `dayBalance` → un plan de
Fase 3 de mayor cardinalidad **sin** la película priorizada podía ganar el índice 0.
Fix: el sort antepone los planes que respetan TODAS las prioridades schedulables;
empate → `dayBalance`. Test red-green permanente en `computeScenarios.test.js`.
Bonus: label `plan_optimo` Óptimo/Best/Melhor → **Tu plan/Your plan/Seu plano**.

### Bug #2 — output no determinístico (RESUELTA ✅ · PR #123)
`computeScenarios` llamaba `shuffle(baseGroups)` sin seed → `Math.random` → misma
watchlist daba "Tu plan" distinto entre recálculos. Fix: `_mulberry32(_titleSeed(titles))`
sembrado por la watchlist (el RNG ya existía en `film.js`, no estaba cableado). Test
red-green (8 corridas). Bonus: worker y fallback sync ahora dan output idéntico.

### Bug #3 — cruce de medianoche en `screensConflict` (DIFERIDA · deuda latente)
**Defecto real confirmado** (repro): `screensConflict` da falso-negativo cuando dos
funciones se solapan cruzando medianoche. Dos manifestaciones:
- `if(a.day!==b.day) return false` corta el caso distinto-día (peli D1 23:30→01:30 D2
  vs peli D2 00:30).
- `toMin` topea en 24h sin wrap → mismo-día con time after-midnight mal comparado.

**NO alcanzable en datos actuales:** Tribeca función más tardía 9:15 PM, Olhar 21:15;
0 funciones cruzan medianoche, 0 funciones 00:00–05:00. Bug latente, no observable.

**Decisión (aprobada):** diferir. Modificar `screensConflict` —la función de mayor
blast-radius del planner— para un caso que no ocurre tiene riesgo > beneficio.

**Fix candidato (cuando algún festival lo requiera):** tiempo absoluto
`day_order*1440 + toMin(time)` en vez de `toMin` + el short-circuit por día.
Verificado: `day_order` es índice de día global (Tribeca/Olhar) e idéntico al código
actual para todo dato sin cruce. **Precondición/riesgo:** depende de que cada screening
tenga `day_order` global; si falta, el loader cae a índice de screening (no global) →
posible falso conflicto cross-day. Alternativa robusta: pasar el orden de días
(`DAY_KEYS`/`FESTIVAL_DATES`) a `screensConflict` (cambia firma + template del worker).
Cualquiera de los dos exige test red-green con fixture de cruce de medianoche.

### Secundarios (no bloqueantes, sin PR)
- **`scoreFilm` — NO es código muerto (auditoría corregida):** revisado en cadena
  completa, `scoreFilm` está vivo en dos consumidores reales: (1) `squeezeExcluded`
  (`handlers.js:748`) ordena por score qué excluidas meter en los huecos — usado en
  `saveCurrentScenario` (al guardar "Tu plan") y en `forceInclude` (botón "+ Incluir"),
  ambos user-facing; (2) `mrvGroups` (`schedule.js`) como heurística de traversal de
  `findMax` bajo el cap de 80k nodos. Lo único cierto del hallazgo original: score **no
  desempata** en la *selección* del plan mostrado (eso lo hacen cardinalidad + `dayBalance`
  + prioridad). Opcional marginal: sumarlo como último tiebreaker del sort. No se tocó.
- **`MAX_NODES_PER_CALL=80000`:** "Tu plan" es best-effort (no óptimo garantizado) para
  watchlists densas — el branch-and-bound corta a 80k nodos. Aceptable, pero el label no
  refleja el caso cap.
- **Divergencia main/worker en venue/time fns (DIFERIDA · deuda estructural):**
  `venueTravelMins`/`travelMins`/`simNow`/`festivalEnded`/`_workerFindCoords` están
  reescritas a mano en el template string del Worker (`calc.js` `_venueFns`) en vez de
  extraerse por `.toString()` como las `_SCHED_PURE_FNS`. Drift concreta ya presente:
  `festival.js` usa `c1.lng??c1.lon` (fallback `lon`) y el coord-builder (`calc.js:128`)
  `if(v.lat&&v.lng)` + la copia del worker leen solo `.lng` → un venue con `lon` daría
  travel en main y 0 en worker.
  **NO alcanzable hoy:** los 15 venues (Tribeca 9 + Olhar 6) usan `lng`, ninguno sin
  coords → worker y main dan travel idéntico.
  **`[worker-overlap]` NO lo cubre:** solo verifica que ninguna fn worker-local esté
  también en `_SCHED_PURE_FNS` (ambigüedad de nombre), no que las copias coincidan en
  contenido. La drift es invisible al validador.
  **Decisión (impacto 0):** diferir. Dos fixes candidatos cuando aplique:
  (a) *minimal* — normalizar `lon→lng` en el coord-builder (`{lat,lng:v.lng??v.lon}`) +
  el `??lon` en la copia del worker. ~2 líneas, cero riesgo, cierra la drift concreta;
  no resuelve la duplicación. (b) *estructural* — unificar `venueTravelMins` para que lea
  una global `_venueCoords` que main y worker pueblen igual, moverla a `_SCHED_PURE_FNS`
  (fuente única vía `.toString()`), sacarla del template del worker. Resuelve la
  duplicación pero toca el path de travel (alto blast-radius) + la bridge + el validador.
  Obstáculo de test: la copia del worker vive en un Blob string → no hay red-green limpio
  en Node; habría que testear el boundary (coord-builder) por separado.

## Design system — opacidad: feedback/estado, no jerarquía (en revisión · sign-off visual pendiente)

`.icon-btn-circle` (botones Cambiar/Quitar en Planear, Quitar en Mi Plan) llevaba
`opacity:.5` en reposo apilado sobre `color:var(--white-60)` → ícono efectivo a ~0.3 de
alfa, se leía como deshabilitado. Único outlier real de una auditoría de `opacity` en el
CSS inline (`index.html` raíz; `www/` lo genera el CI). Fix: quitar `opacity:.5` de la
regla — la jerarquía secundaria ya la expresa el token de color sólido. El feedback de
toque queda intacto (`.ag-fi-btn:active{opacity:.6;transform:scale(.95)}`). NO se tocaron
indicadores de affordance dentro de un target mayor (`.paf-pill-x`, `.hdr-fest-chev`,
`.pel-sheet-sec-arrow`), placeholders, estados de contenido (`past`/`watched`/`conflict`),
overlays ni inputs invisibles. Referencia canónica: `.int-prio-btn` (estrella de
Prioridades). Decisión documentada en `constitution.md` → "Opacidad: feedback y estado,
no jerarquía". Check nuevo en `validate.py` diferido (decisión de tooling aparte).

**Follow-up — unificar el control Quitar (rojo en ambos contextos):** durante el audit
visual se detectó un 2º caso en reposo: `#ag-result .col-end .ag-fi-btn.del` (Planear)
llevaba `opacity:.7` (viola el principio) apilado sobre `color:var(--red)` (deliberado, ver
comentario en CSS). Además había inconsistencia entre pantallas: Planear Quitar = rojo,
Mi Plan Quitar = neutro white-60. Como la app es mobile-only (sin hover), la señal
destructiva tiene que vivir en reposo → el rojo es correcto. Fix: regla global
`.ag-fi-btn.del{color:var(--red)}` (rojo en reposo en Planear y Mi Plan), se elimina el
override `#ag-result .col-end` con su `opacity:.7`. Resultado: Quitar rojo sólido
`opacity:1` y consistente entre pantallas; Cambiar sigue neutro. Principle-compliant
(jerarquía/estado por color, no por opacity).

## Design system — colores hex raw → tokens (punto 1 de auditoría · en revisión)

Audit de `index.html`: 48 ocurrencias de hex; mapeadas a `{hex → token → uso}`. **18
reemplazos** aplicados (solo match exacto + contexto de uso CSS):
- `#000` → `var(--black)` ×12 (color/border-top-color de CTAs amber + spinner + html bg)
- `#0A0A0A` → `var(--bg)` ×4 (texto oscuro en badges/posters editoriales)
- `#F0EDE8` → `var(--white)` ×1 (ed-title)
- `#1A1A1A` → `var(--surf-2)` ×1 (psp-editorial bg)

Valores idénticos (cero cambio visual; confirmado en Chrome: tokens resuelven a su hex
exacto). NO tocados (documentado): inline `<html style>` y `<meta theme-color>` (pre-CSS /
no-CSS, var() no disponible); `#e05` (#ee0055, sin token ≠ `--red`); `#1C1C1C` (sin token);
`var(--surf-3,#1A1A1A)` (fallback explícito); `stroke="#fff"`/`stroke="#3AAA6E"` en SVG
(atributo de presentación — var() no resuelve ahí); `rgba(0,0,0,.25)`. `#141414`/`#1E1E1E`
tienen tokens ambiguos (2 c/u) pero solo aparecen en definiciones, sin uso raw.

Verificado: `validate.py` 30/31 (`tasks-sync` preexistente); Playwright sin fallos reales
(T06 flaky confirmado aislado); Chrome ES/EN sin cambio visual. Bump pendiente post-sign-off.

## Barrido i18n — eliminar mezcla de idiomas (en revisión · sign-off visual pendiente)

Auditoría profunda (5 agentes en paralelo) de leaks i18n en todos los estados del
festival (pre/durante/post/global). Causa raíz: el check `[i18n-hardcoded]` de
`validate.py` solo escanea `main.js` (casi vacío tras el refactor por capas) contra una
whitelist de 13 strings → nunca miró los módulos `src/view/*` ni `src/controller/*` donde
vive el UI. Pasaban ~55 leaks. El diccionario `i18n.js` en sí estaba limpio (paridad
es/en/pt perfecta); todos los leaks eran literales hardcodeados o concatenación (pegar un
`t()` con texto ES fijo, lo que producía "You already have un plan con N películas" en EN).

Corregido en 8 lotes (commit por lote), **55 keys nuevas** en es/en/pt (i18n.js: 345→400),
copy aprobado por Juan:
- **A `share.js`** (15): flujo compartir/exportar completo a t().
- **B `handlers.js`** (8): toasts + modal Reemplazar plan + `confirmReplace` (quitado el hack `.split(', ')[1]`).
- **C `sheets-controller.js`** (5): Cambiar/reprogramada/prioridades/rating.
- **D `agenda.js`** (11): Mi Plan durante festival (retraso, en curso), sugerencias, fallback "El festival" post-festival, pluralización (`misc_peliculas`).
- **E `programa.js`+`components.js`** (4): chip "Todo", banner aviso, filtros, "Quitar".
- **F `index.html`** (6): píldoras/conflicto vía `data-i18n` + wiring por ID (aria Cuenta).
- **G `overlays.js`+`persistence.js`** (3): "Cortometraje" + toasts (+ fix args `✓`/`✗` mal usados como tipo).
- **H pósters SVG** (3): PROGRAMA/EVENTO/PROYECCIÓN SORPRESA + abreviaturas de día lang-aware.

Decisiones: términos universales (min/h/Q&A/vs) y meta/OG/SEO estático se dejan (no son
leaks de runtime); endónimos del selector se quedan en su idioma.

### Deuda pendiente — endurecer `validate.py [i18n-hardcoded]`
El check quedó ciego (solo main.js + whitelist). Pendiente (decisión de tooling aparte):
escanear `src/view/*` + `src/controller/*` y detectar concatenación `t()`+literal y
literales de UI ES/EN, para que estos leaks no reaparezcan en silencio.
