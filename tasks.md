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

### Deuda pendiente — endurecer `validate.py [i18n-hardcoded]` (RESUELTA ✅ · punto 6)
~~El check quedó ciego (solo main.js + whitelist).~~ Resuelto: ver "Design system — punto 6" al final.

## Design system — font-weight/font-size raw → tokens (punto 2 de auditoría · en revisión)

Audit de `index.html` (`--w-*` 400-800, `--t-*` 8-30px). **6 reemplazos** (solo match exacto):
- `font-weight:800` → `var(--w-display)` ×3 (posters editoriales: `.ed-lbl`, `.ed-title`, `.psp-ed-hdr span`)
- `font-weight:700` → `var(--w-bold)` ×1 (`.sec-drop-hdr`)
- `font-size:9px` → `var(--t-xs)` ×1 (`.main-nav-tab .tab-badge`)
- `font-size:16px` → `var(--t-md)` ×1 (`.int-prio-btn`)

Valores idénticos → cero cambio visual (confirmado en Chrome: tokens resuelven a su valor
exacto; `.sec-drop-hdr` fw=700, `.tab-badge` fs=9px). NO reemplazados (documentado):
- `@font-face` (74-78, `font-weight` 400-800): descriptores del archivo de fuente, no uso; `var()` no aplica.
- Inputs `font-size:16px` (`.auth-email-inp`, `.sheet-input`, `.pin-display`): anti-zoom iOS (contexto especial; aunque 16px=`--t-md` exacto, tokenizar acopla el comportamiento iOS al token).
- Sin token: `32px` (×2), `28px`, `23px`.
- `font-size` en `cqi` (posters editoriales): unidades container-query, sin token.
- `#dbg-ver` (`font-size:9px` inline, debug): fuera del scope de `<style>`.
- `20px` (`--t-lg`/`--t-wordmark-d`, ambiguo): sin uso raw.

Verificado: `validate.py` 30/31 (`tasks-sync` preexistente); Playwright sin fallos reales
(T08 flaky confirmado aislado); Chrome ES/EN sin cambio visual. Bump pendiente post-sign-off.

## Design system — auditoría de `!important` (punto 3 · en revisión)

22 `!important` en `index.html`: 6 `display:none` (toggles legítimos) + 16 raw en 8 sitios
lógicos. Clasificación por especificidad (qué regla previa los obliga):

**Intencionales (override real, NO tocar):**
- `.card.selected` (border/box-shadow) — debe ganarle al `@media(hover){.card:not(.conflict):hover}` que es más específico (0,3,0 vs 0,2,0).
- `@media reduced-motion *{...}` — patrón a11y canónico; `!important` sobre `*` es obligatorio.
- `.lugar-cnt{flex:none}` — debe ganarle a `.lugar-opt span{flex:1}` (0,1,1 > 0,1,0).
- `.card.program{background}` — pisa el zebra-striping `:nth-child`; gana por orden de fuente, el `!important` lo hace robusto. **Decisión PO: se queda** (intencional, no vale el riesgo por limpieza cosmética).

**Parches superfluos REMOVIDOS (el `!important` no hacía trabajo, render idéntico):**
- `.hint.active{padding}` — `.active` ya gana por especificidad.
- `.c-lb{flex-shrink:0}` — nadie más setea flex-shrink ni shorthand.
- `.wl-btn.wl-on{opacity:1}` — el `:not(.wl-on)` lo excluye; el `:hover` setea el mismo valor.

### Deuda pendiente — `#hdr-programa`/`#hdr-ag` `position:relative!important;top:auto` (RESUELTA ✅ · punto 7)
Un-stick de headers en un `@media`. ~~Diferido a tarea aparte.~~ Resuelto: ver "Design system — punto 7" abajo.

## Design system — botones: padding/sizing raw → tokens (punto 4 · en revisión)

Audit de selectores btn/pill/chip (tokens spacing: `--sp-1`=4 … `--sp-btn`=14, `--sp-5`=24…px).

**Aplicado (3, match exacto):**
- `.suggestion-add` — `min-width:76px` → `fit-content` (debloat aprobado por PO; el `76px` inflaba el botón) **+** `padding:4px var(--sp-2)` → `padding:var(--sp-1) var(--sp-2)` (4px=`--sp-1`). Chrome: width 76px→54px (al contenido), padding intacto.
- `.seccion-btn` · `.lugar-btn` — `padding:4px 0` → `padding:var(--sp-1) 0` (4px=`--sp-1`, valor idéntico, cero cambio). Encontrados en el barrido (no estaban en los candidatos originales).

**No reemplazados (motivo):**
- Sin token: `10px` (`.conflict-modal-btn.cancel`, `.conflict-btn-cancel`), `2px` (`.prio-pill`, `.ended-rate-btn`, `.corto-rate-btn`), `3px`/`6px` (`.paf-pill` asimétrico, `.ended-rate-btn`), `9px` (`.delay-btn`).
- **Heights** (`28/30/32/34/36/38/44px`, etc.): `--sp-*` es escala de **espaciado**, no de dimensión; usar un spacing token como `height` acopla semánticas distintas → no se tokeniza.
- **Gaps** `1px`/`3px`/`5px`: sin token.
- `.prio-chip-rm` (`top/right:4px; width/height:18px`): posicionamiento absoluto de control → legítimo (no es escala de spacing).
- `#rating-stars{padding:4px 0}`: fuera de scope (no es btn/pill/chip).

### Decisión pendiente — shorthands mixtos con UN valor on-scale
`.delay-btn` (`4px 9px`), `.mplan-bottom-btn` (`4px 10px`), `.pel-sheet-action-btn[.btn-*]`
(`11/13px 4px`), `.corto-rate-btn` (`2px 8px`): tienen un eje con token exacto (4px/8px) y el
otro off-scale. Tokenizar deja un shorthand token+raw (`var(--sp-1) 9px`). **Hay precedente
en el código** (`.prio-pill`, `.ag-fi-btn`, `.btn-tertiary` ya mezclan), así que es defensible,
pero expande más allá de los candidatos nombrados.
**DECISIÓN (Senior Dev + PO):** NO por ahora. El precedente de mezcla existía antes de que
hubiera regla → no es razón para expandirlo. Si en algún momento se crean tokens de sizing
vertical (`--sp-btn-v` o similar), se hace el barrido completo. Hasta entonces queda como
**deuda conocida documentada**, no follow-up inmediato.

## Design system — dead-CSS removal (punto 5 · en revisión · sign-off visual pendiente)

Eliminación de CSS muerto heredado del refactor MVC por capas (Wave 6-7).

**Enfoque (corregido tras incidente de integridad):**
1. **Set autoritativo dead-safe** = clases definidas en el CSS cuyo token NO aparece con
   límites estrictos `(?<![\w-])X(?![\w-])` en NINGÚN `src/*.js`/`.html` ni en el markup
   (post-`</style>`). Captura `class="..."`, `classList`, `closest/querySelector`, **y clases
   pasadas como argumento a helpers** (`_posterThumb(f,'int-item-poster')`) — esto último era
   el punto ciego del set-diff original. Resultado: **244 dead-safe** de 912 definidas.
2. **Procesador per-part**: por cada regla, elimina solo los selectores-coma cuyos
   required-classes ∈ dead_safe (ese selector no matchea nada); conserva miembros vivos; quita
   la regla entera solo si TODOS sus selectores mueren. Preserva comentarios (enmascarados),
   respeta `@media`/`:not()`/`[attr]`. **Seguro por construcción**: nunca quita estilo de un
   elemento vivo. → **329 reglas removidas, 12 selectores recortados** (miembros vivos intactos).
3. Cleanup de artefactos: `@media` vacíos eliminados, runs de líneas en blanco colapsados.
4. **Gate de integridad** (la red que faltaba): `net-removed ∩ used == 0`. Verificado.

**Conservador a propósito:** clases muertas pero referenciadas defensivamente (`querySelector('.card,.poster-card')`)
o mencionadas en comentarios (`card`, `selected`, `conflict`, `program`) quedan como token
"usado" → se **conservan** (se deja algo de CSS muerto antes que arriesgar regresión).

**Comentarios huérfanos:** NO se tocan (no son CSS muerto; distinguir header-de-sección de
header-padre no es automatizable con seguridad → fuera de scope quirúrgico).

### Incidente de integridad (detectado y revertido antes de cualquier push)
Un primer intento por lotes usó un `dead_all.txt` mal generado (el set de "usados" no barría
`src/*.js` correctamente) + un error manual mío (quitar `ag-fi-btn` vivo como colateral de
grupos multi-clase en el lote ag-*). Resultado: **31 clases vivas borradas** (regresiones
confirmadas: `ag-fi-btn` feedback/touch-action, `int-item-poster`, `sync-dot`, `count-badge.cb-*`,
estados `wl-on`/`w-on`/`prio-on`, etc.). El safety-net de entonces (brace-balance + validate.py)
solo cubría **sintaxis**, no **liveness** → pasó silencioso. **Recuperación:** reset a base +
re-ejecución con el enfoque autoritativo de arriba + gate de integridad. Lección incorporada:
toda remoción de CSS exige un gate de liveness, no solo de sintaxis.

**Verificación:** brace-balance 0 · 0 malformados · validate.py 30/31 · Playwright 68 passed
(16 flaky conocidos, pasan en retry) · smoke visual Chrome EN+ES en las 4 tabs (Programa,
Intereses, Planear, Mi Plan) + ficha + estados WL/prio/`in-wl`/`count-badge`/timeline `mplan-wk-*`.

## Design system — endurecer validate.py [i18n-hardcoded] (punto 6 · en revisión · sign-off pendiente)

**Gap raíz:** el check `[i18n-hardcoded]` solo escaneaba `main.js` (la UI migró a `src/view/`
+ `src/controller/` en el refactor MVC) contra una whitelist de 13 strings + un heurístico
solo-acentos. Por eso pasaron ~55 leaks en #152.

**Fix (3 partes):**
1. **Scope ampliado:** el check ahora escanea `_view_all` + `_controller_all` + `_main_src`
   (NO `i18n.js` = fuente de verdad, NO el HTML estático = `data-i18n` con fallback legítimo).
2. **Reverse-dictionary check (NUEVO, primario, FAIL):** un VALOR ES del diccionario que
   aparece como literal hardcodeado = leak. Captura español CON y SIN acentos (el diccionario
   es la verdad de terreno — esto es lo que habría cazado #152). Solo multi-palabra (≥1 espacio,
   ≥6 chars); excluye object-keys (`'x':`) y fallbacks (`t()||'x'`). **0 falsos positivos empíricos.**
3. **Heurístico de acentos (WARN):** ahora sobre view+controller, con `SAFE_MARKERS` ampliado
   (géneros TMDB, chips de sección, `console.`) + skip de valores ya en diccionario (los cubre
   el reverse-check). Caza español NUEVO aún no en el diccionario.

**Leak real detectado y corregido** (lo encontró el reverse-check durante el audit): modal de
conflicto en `src/view/feedback.js` tenía 2 strings ES hardcodeadas mientras el resto del modal
usaba `t()`. Copy aprobado por Content Designer:
- `conflict_plan_titulo` — ES "Conflicto con tu plan" · EN "Conflicts with your plan" · PT "Conflito com seu plano"
- `conflict_choca_intro` — ES "Esta función choca con:" · EN "This screening conflicts with:" · PT "Esta sessão conflita com:"
  (terminología "función" por consistencia con el resto de la app)

**Decisión sobre check `[dead-css]`:** NO se añade (over-engineering — el CSS muerto es
inofensivo, alto riesgo de FP por construcción dinámica de clases). El gate de liveness de #157
se preserva como herramienta puntual de refactor, no como check de CI.

**Verificación:** node --check (i18n.js + feedback.js) · validate.py 30/31 (`[i18n-hardcoded]`:
13 whitelist + 378 valores i18n verificados, sin hardcode · paridad 402 keys ES/EN) ·
Playwright 68 passed · modal renderizado vía import dinámico con copy correcto (DOM-verificado ES).

### Deuda relacionada (no en scope) — `[i18n-complete]` también solo mira main.js+i18n.js
`t('key')` usados en `src/view`/`src/controller` no se validan contra el diccionario. Un
`t('typo_key')` en un módulo no se detectaría. Mismo patrón de fix (ampliar scope al corpus)
si se quiere cerrar — follow-up menor.

## Design system — quitar !important sticky #hdr-programa/#hdr-ag (punto 7 · en revisión · sign-off pendiente)

Cierra la deuda diferida del punto 3. Los headers tenían `position:relative!important;top:auto!important`
en `@media(max-width:768px)` para des-stickearse (mobile: `.topbar` es el único sticky).

**Veredicto del audit: `!important` superfluo (3 pruebas convergentes):**
1. **Orden de fuente ya gana** — base (`#hdr-*{position:sticky}`) y el bloque mobile tienen idéntica
   especificidad de ID (1,0,0); el `@media` no añade peso; el bloque va después en el source → gana
   sin `!important`. Los dos `@media` (max-768 / min-768) son mutuamente excluyentes.
2. **Gemelo desktop** — el bloque `@media(min-width:768px)` hace el mismo un-stick
   (`position:relative;top:auto`) sobre los mismos IDs, contra la misma base, **sin `!important`**, y funciona.
3. **Sin inline que vencer** — `_fixStickyOffset` solo setea variables CSS en `:root`; el único inline
   en esos headers es `display:none`. No hay selector más específico que reponga `sticky`.

**Fix:** quitar los 4 `!important` (2 en `#hdr-programa`, 2 en `#hdr-ag`) → idéntico al gemelo desktop.
Cero cambios a padding/background/border.

**Verificación (sticky es load-bearing):** brace-balance 0 · validate.py 30/31 · `getComputedStyle` en
**2 breakpoints** — mobile 375: `.topbar` sticky, headers `relative` ✓ · desktop 1280: `.topbar` +
`.programa-mode-bar` sticky, headers `relative` ✓ · scroll-test mobile: chrome pegado en top:0 sin gap.

## fix(splash): animación de entrada no revela en WKWebView (Capacitor) — RESUELTO

**Síntoma:** en la app nativa (Capacitor/WKWebView) el splash se veía en blanco/vacío "sin
animación"; en Chrome/Safari (web) funcionaba. El resto de la app (OTA incluido) funcionaba bien.

**Causa raíz:** la entrada del splash (`src/main.js`) hacía `el.style.opacity='0'` inline y luego
`el.animate([0→1], {fill:'forwards'})`. La visibilidad final dependía 100% de que `fill:'forwards'`
persistiera. **WebKit no persiste `fill:'forwards'` de forma fiable sobre un `opacity:0` inline**
(+ posible throttling de rAF/animaciones mientras la vista está tras el launch-screen nativo) →
wordmark + tagline + selector + botón Entrar quedaban atascados en `opacity:0` → splash vacío.
Blink (Chrome) sí persiste → por eso web funcionaba. El resto de la app no usa este patrón.

**Fix:** `_reveal()` robusto — la visibilidad ya NO depende de `fill:'forwards'`:
- `onfinish` + `oncancel` fijan el estado visible al terminar la animación.
- `setTimeout(delay+duration+400)` como red de seguridad si WKWebView throttlea y onfinish no dispara.
- guards: `prefers-reduced-motion` o `el.animate` ausente/lanza → mostrar directo.
Cuando la animación funciona, la entrada es idéntica; peor caso pasa de "invisible" a "sin animación".

**Descartado en el diagnóstico:** prefers-reduced-motion (su rama hace visible, no invisible),
ausencia de `el.animate` (presente en iOS 13.4+), y auto-dismiss del splash en Capacitor (no existe).

**Verificación:** node --check · validate.py 30/31 · Playwright 69 passed (0 fail) · smoke web:
los 3 bloques del splash llegan a `opacity:1, transform:none` (path onfinish confirmado en navegador).
Confirmación final pendiente en iPhone (build/OTA + Web Inspector).

## fix(splash): blanco + brinco de idioma en WKWebView — fix integral (2 bugs, mismo origen)

Ambos bugs son de "primer paint antes de que JS inicialice" en la app nativa (Capacitor/WKWebView).
Web (Chrome/Safari) no los exhibía.

**Bug 1 — splash invisible.** La entrada hacía `el.style.opacity='0'` inline + `el.animate(…,{fill:'forwards'})`,
gated tras doble-rAF. Si el timeline de la animación está throttled (vista tras el launch-screen nativo)
o WebKit no persiste `fill:'forwards'`, los elementos quedaban atascados en `opacity:0` → splash vacío.
PR #162 (onfinish/oncancel/setTimeout) no bastó: el fallback vivía DENTRO del rAF throttleable.
**Fix:** entrada 100% CSS y **opacity NUNCA se anima** — `.splash-*{opacity:1}` fijo, la animación CSS
mueve SOLO `transform` (slide-up). Peor caso: contenido visible sin deslizarse. JS ya no toca opacity.
(Iteración cazada en smoke web: un primer intento animaba opacity con `fill-mode:both` y seguía
quedando en 0 bajo throttle → se quitó opacity de la animación.)

**Bug 2 — brinco de idioma.** El parche inline pre-paint solo cubría `localStorage==='en'` → en install
fresca con sistema en EN/PT (sin lang guardado) mostraba ES hardcodeado y luego saltaba al idioma del
sistema. **Fix:** el parche inline ahora replica la detección de main.js (`lang guardado OR
navigator.language → es/en/pt`) con el copy exacto del diccionario (incl. PT) → primer paint ya correcto.

**Diagnóstico temporal incluido (quitar tras confirmar en iPhone):** console.logs `[splash i18n] lang=…`,
`[splash] init · _lang=… · build=…`, `[splash] opacity tras paint → …`.

**Verificación:** node --check · validate.py 30/31 · Playwright 72 passed · smoke web: opacity de los 3
bloques = 1 (visible) bajo throttle headless + parche EN aplicado al primer paint. Confirmación final en iPhone (OTA + Web Inspector).

## Subsistema splash iOS — CERRADO ✅ (flash blanco + brinco de idioma)

El "flash blanco al abrir" tenía **3 capas** de primer-paint, cada una en un lugar distinto.
Resueltas las tres:

| Capa | Qué | Dónde se arregló |
|---|---|---|
| **1 · Launch screen nativo** | iOS pintaba blanco por default (`UILaunchScreen_Generation=YES` → vacío) | **Proyecto iOS** (SwiftUI iCloud): `UILaunchScreen` dict con `UIColorName=LaunchBackground` (#0A0A0A), **sin logo** (evita doble-marca ícono→wordmark); `Generation=NO` en pbxproj. |
| **2 · Fondo del WKWebView** | el WebView nace **opaco y blanco**, visible mientras carga otrofestiv.app | **Proyecto iOS** `ContentView.swift`: `isOpaque=false` + `backgroundColor`/`scrollView.backgroundColor`=#0A0A0A + capa SwiftUI oscura detrás. (Se quitó el `alpha:0`/reveal-on-didFinish: hacía que la animación de entrada corriera oculta → "sin animar". Ahora el contenido pinta directo sobre fondo oscuro → animación siempre visible, sin depender de la red.) |
| **3 · Primer paint del HTML** | splash web invisible (opacity:0 + WAAPI `fill:forwards` no persiste en WKWebView) + brinco de idioma ES→sistema | **Repo web** (PR #163): entrada 100% CSS animando **solo `transform`** (opacity:1 fijo → nunca invisible); parche inline pre-paint con detección `navigator.language` (es/en/pt) → idioma correcto al primer frame. |

**Resultado:** cadena 100% oscura — launch screen → WKWebView → splash web — con la animación de entrada (slide-up) visible. Cero blanco, cero brinco de idioma.

### ⚠️ Nota crítica — el proyecto iOS real es el SwiftUI de iCloud, NO el Capacitor
- **Real / activo:** `/Users/Juanda/Library/Mobile Documents/com~apple~CloudDocs/Otrofestiv/10_iOS/Otrofestiv/` — app **SwiftUI** (`OtrofestivApp.swift` + `ContentView.swift` con `WKWebView` que carga `https://otrofestiv.app` fresco cada launch). **Aquí van los fixes nativos + el rebuild de Xcode.** Las capas 1 y 2 viven aquí (gitignored-friendly: el proyecto es su propio repo git).
- **Abandonado:** `/Users/Juanda/Otrofestiv.app/` (Capacitor + @capgo, May 19). Un fix temprano del LaunchScreen.storyboard fue a parar aquí por error — inofensivo, no se compila. **No usar.**
- Como el SwiftUI carga producción directo (no @capgo), **los fixes web (capa 3) llegan vía producción en el próximo cold-launch — sin OTA.** El launch screen + WKWebView (capas 1-2) requieren **rebuild de Xcode** (no OTA).

**Diagnóstico:** los `console.log` temporales `[splash …]` se quitaron tras confirmar en iPhone (este PR).

## fix(splash): entrada escalonada + gate del selector (sin brinco de festival)

**Brinco:** `splash-sel-name`/`splash-sel-meta` traen placeholder estático en el HTML y main.js
los sobrescribe con el festival activo (síncrono, FESTIVAL_CONFIG estático) → el cambio era visible.

**Fix (gate por clase):** los 3 bloques (wordmark/action/tagline) arrancan `opacity:0`. main.js
puebla el selector y RECIÉN ahí (doble rAF) agrega `.splash-anim-in` al `#otrofestiv-splash` → el
cambio placeholder→activo ocurre tras opacity:0 (invisible). Fallback inline (1.5s) por si main.js
no corre. Entrada escalonada: wordmark 0ms · selector 250ms · tagline 500ms (slide-up 500ms, ease
cubic-bezier(.22,1,.36,1)).

**Decisión de robustez (clave):** la OPACITY se revela con **regla estática** disparada por la clase
(instantánea, jamás animada); la animación CSS mueve **solo `transform`**. Razón: animar opacity con
`fill:both` la deja en 0 si el timeline se throttlea (verificado en smoke: con `visibilityState:hidden`
la versión con opacity animada quedaba en 0; la estática da opacity:1 siempre). Trade-off: la aparición
es instantánea + slide escalonado, no un fade gradual de opacity — pero **nunca invisible** (la lección
del subsistema splash). reduce-motion: estado final visible, sin animar.

**Verificación:** node --check · validate.py 30/31 · Playwright 69 passed · smoke web: los 3 bloques
llegan a `opacity:1` AUN con `visibilityState:hidden` (throttle) · selector muestra "Tribeca Festival"
(no placeholder) en estado visible.

## fix(splash): fade+slide juntos + delays largos (0/700/1400) con hard-floor anti-invisible

**Ajuste 1 — delays:** wordmark 0ms · selector 700ms · tagline 1400ms, 600ms c/u (~2s total).
**Ajuste 2 — opacity + transform animan JUNTOS** (`@keyframes splashIn{0%{opacity:0;translateY(16px)} 100%{opacity:1;none}}`).

**Veredicto técnico (clave):** animar opacity en `@keyframes` CSS NO es throttle-safe — el throttle es
del document timeline (pausa CSS Animations Y WAAPI por igual bajo visibilityState:hidden). Mientras
cualquier fase de la animación aplica (active o fill) PISA la regla de reposo `opacity:1` (origen CSS
Animations > author normal). Ningún fill-mode lo salva: `both/backwards` → from{0} durante el delay;
`forwards/none` → flash + atasco en la fase activa. Verificado esta sesión (la versión opacity-both dio 0).

**Solución (CSS cosmético + hard-floor JS):** el `@keyframes` hace el fade+slide; una regla estática
`.splash-anim-in{opacity:1}` es el reposo visible; un hard-floor JS (main.js, relativo al inicio real
de la animación: último delay 1400 + 600 dur + 200 margen = 2200ms) hace `style.animation='none'` →
la animación deja de aplicar → cae a la regla estática → opacity:1 garantizado. El visual NUNCA depende
de JS (distinto del fiasco WAAPI). En foreground el doc nunca throttlea → el fade siempre se ve; el floor
es no-op (mismos valores). El fallback inline (main.js no corre) trae su propio hard-floor → ningún
camino deja opacity en 0.

**Verificación:** node --check · validate.py 30/31 · Playwright 73 passed · smoke determinístico bajo
visibilityState:hidden: CSSOM confirma keyframe opacity 0→1 + transform juntos y timings 0/700/1400ms;
step1 (animación throttled) → opacity:0, step2 (floor) → opacity:1. Selector = Tribeca (sin brinco).

## fix(during-festival #1): anclar "ahora" del modo en-curso a la zona del festival

**Bug:** la lógica minuto-del-día (now-line, contador, "en curso", clasificación done/active/future,
fases next/between/evening, "hoy") usaba `now.getHours()` LOCAL DEL DISPOSITIVO, mientras el horario
está en hora del venue (toMin("8:00 PM")=1200, NYC). Para un tester fuera de NYC los dos marcos no
coinciden → error continuo = delta TZ (Bogotá 60min, UTC 240min). Demostrado: función en curso se
mostraba como "en 30 min, isNow=false".

**Decisión de producto:** anclar el tiempo del modo en-curso a la ZONA DEL FESTIVAL (lugar físico),
no al dispositivo. Un festival es ligado a un lugar; el programa oficial está en hora del venue;
asistir es físico. El horario ya se muestra en hora-festival → "ahora" debe estar en el mismo marco.
Estándar de apps de eventos. Correcto para asistente en NYC y espectador remoto por igual.

**Fix:** time.js: `_festNow()`/`_festNowMin()` desplazan simNow() por TZ_OFFSET y leen getters UTC →
reloj de pared del festival; `simTodayStr()` reescrito igual. festival.js: nowMin→`_festNowMin()`,
FESTIVAL_START con offset. agenda.js: 5 sitios minuto-del-día → `_festNowMin()`. loader.js:
FESTIVAL_END anclado con cfg.timezoneOffset. Comparaciones ABSOLUTAS (screeningPassed/festivalEnded)
no se tocan (ya correctas vía _festDate+offset).

**Evidencia:** Playwright fresh-import bajo 3 timezones (NY/Bogotá/UTC) al mismo instante NYC jun7
19:30: festNowMin=1170 + simToday=2026-06-07 + isNowPlaying=true IDÉNTICOS en las 3 (device-local
daba 1170/1110/1410). EN/PT/ES: Programa en-curso renderiza traducido (Today/Hoje, Tomorrow/Amanhã),
sin keys crudas ni errores JS. node --check x4 · validate 30/31 · regression 72 passed.

Nota: independiente de #2 (AM/PM); ambos tocan time.js (funciones distintas) → mergear #2 luego #1.
