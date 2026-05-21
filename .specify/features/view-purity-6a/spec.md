# Spec — View Purity Fase 6a (Tier 1 pure-ish, 8 funciones)

## Problema

Las funciones View en index.html mezclan tres responsabilidades:
1. **Read state**: leen los 19 globals del roster directamente (post-p5.5 hay
   mirror, pero el read-side aún no canaliza)
2. **Build HTML**: ensamblan strings con template literals
3. **Commit to DOM**: `document.getElementById(...).innerHTML = ...` + classList

Esto:
- Imposibilita pasar `state` por parámetro (prereq para Fase 7 subscribe→render)
- Imposibilita testear el HTML en aislamiento (cualquier render trae 200+ líneas de deps + side effects)
- Mezcla shape de Model (puro, parámetro-driven) con shape de Controller (DOM-aware)

§16.5 del roadmap define Fase 6 como "View extraction: convertir cada `renderXxx`
en función pura `(state, deps) → HTML string`". Esta spec es **6a**, sub-fase 1
de 3, cubriendo solo las funciones que **ya retornan HTML string sin side effects**.

## Causa raíz

Crecimiento orgánico: las primeras Views eran helpers chicos (`renderRatingStars`)
que mutaban DOM directo. Luego se introdujeron sub-renders (`renderNextStrip`,
`renderGapOptions`) que sí retornan HTML — pero como sub-componentes pegados a
orchestrators (`renderAgenda`) que sí mutan DOM. Resultado: la mitad de los
"renders" ya son pure-ish por accidente, sin reconocerlo en la API.

## Solución — Fase 6a

Migrar 8 funciones que **ya retornan HTML string sin side effects** a la
signature pura `(state, ...args) → HTML string`:

```js
// ANTES
function renderNextStrip(schedule) {
  // lee watched, filmDelays, FESTIVAL_DATES como globals
  return `<div>...</div>`;
}

// DESPUÉS
function renderNextStrip(state, schedule) {
  const { watched, filmDelays, FESTIVAL_DATES } = state.snapshot();
  return `<div>...</div>`;
}
```

**Cero cambios de HTML output.** Solo cambia el shape de la API (state como
primer param) y la fuente de lectura (snapshot vs global directo).

## Las 8 funciones en scope

| # | Función | Líneas | State reads | Caller(s) |
|---|---|---|---|---|
| 1 | `makeProgramPoster(title, duration, section)` | 48 | FILMS | varios (getFilmPoster) |
| 2 | `makeEventPoster(title, duration, eventKind)` | 25 | _activeFestId, _lang | varios |
| 3 | `renderNextStrip(schedule)` | 86 | watched, filmDelays, FESTIVAL_DATES | renderAgenda |
| 4 | `renderUnconfirmed(schedule)` | 52 | watched, FESTIVAL_DATES | renderAgenda |
| 5 | `renderGapOptions(gapStartMin, gapEndMin, todayKey, removedTitle)` | 40 | savedAgenda, FILMS, watched, FESTIVAL_DATES | renderAgenda (gap suggestion) |
| 6 | `_renderSavedAgendaHTML()` | 144 | savedAgenda, FILMS, watched, _activeFestId, FESTIVAL_DATES | shareAsImage (export) |
| 7 | `renderContextualHeader()` | 244 | savedAgenda, FILMS, watched, prioritized, filmRatings, filmDelays, _activeFestId, _lang | renderAgenda |
| 8 | `renderMiPlanCalendar()` | 220 | savedAgenda, FILMS, prioritized, FESTIVAL_DATES | renderAgenda |

**Total:** ~860 líneas de View afectadas.

## Lo que NO entra en Fase 6a

| Out-of-scope | Tier | Razón | Fase futura |
|---|---|---|---|
| `renderFilmListHTML` | 2 | setTimeout con mutaciones de pill counts (post-render side effect) — necesita extract pure/impure | 6b |
| `renderRatingStars` | 2 | `el.innerHTML = html` directo — body es 50% build + 50% commit | 6b |
| `renderPrioStrip`, `renderSavedAgendaHTML` (pública), `renderProgramaChips`, `renderNoticesBanner`, `renderFlowProgress`, `renderSimPanel`, `renderAvDay`, `_renderFestivalSelector`, `_renderSplashDropdown`, `renderFilmAlternatives` | 2 | Mezcla return-HTML + classList toggles | 6b |
| `renderAgenda`, `render`, `_renderProgramaContent`, `renderProgramaList`, `renderMiPlanList`, `_renderExploreLista`, `renderSbar`, `renderPeliculaView`, `renderAvBlocks`, `_renderAfterSync` | 3 | Orchestrators — set innerHTML del root + classList del UI state | 6c |
| `openPelSheet`, `openCortoSheet`, `openAvSheet`, `openConflictSheet`, `openAuthSheet`, `openRatingSheet`, `openFestivalSheet`, `openPostViewRating`, `openCortoSheetFromEl`, `showDestructiveModal`, `showActionModal`, `showConflictModal`, `showActionToast` | 4 | Sheet/modal lifecycle — UI state local + event listeners + visibility classes | 7 (Controller) |
| `makeSorpresaPoster` | — | Ya pura, cero state reads, parámetros deterministan todo. No requiere migración | — |

## API de la View pura — D1 incorporada

**Decisión D1 aprobada**: single `state` param, deps quedan como free vars resolviendo al module scope.

```js
function renderX(state, ...otherArgs) {
  const { a, b, c } = state.snapshot();
  // free refs OK: t, ICONS, parseProgramTitle, screeningPassed, etc.
  return `<div>${t('key')} ${ICONS.star}</div>`;
}
```

Justificación:
- `t`, `ICONS`, Model functions ya son module-level constants efectivamente puras
- Pasar 5+ deps explícitos infla call sites sin ganancia de testabilidad (Model ya testeado en Fases 1-4)
- En Fase 8 (file split), los `deps` se convierten en `import` — no es trabajo perdido

## Callers — D2 + D4 incorporadas

**Decisión D2**: caller dedicado `_rerenderX()`.
**Decisión D4**: `renderX` queda como la pura; el caller `_rerenderX()` es el side-effect.

Pero en Fase 6a, las 8 funciones son **sub-renders** llamadas desde otros renders, NO desde call sites raíz. Sus callers actuales son:
- `renderAgenda` → llama renderNextStrip, renderUnconfirmed, renderContextualHeader, renderMiPlanCalendar, renderGapOptions
- `shareAsImage` → llama `_renderSavedAgendaHTML`
- `getFilmPoster` → llama makeProgramPoster, makeEventPoster

Por tanto en 6a NO se introducen `_rerenderX` callers. Los callers actuales
(`renderAgenda`, `shareAsImage`, etc.) reciben el state como argument:

```js
// Caller actual (sigue siendo impuro en 6a — Fase 6c)
function renderAgenda() {
  // ...existing read pattern, no cambios...
  const ctxHtml = renderContextualHeader(state);     // ← cambia
  const stripHtml = renderNextStrip(state, schedule); // ← cambia
  // ...
  document.getElementById('ag-view').innerHTML = ctxHtml + stripHtml + ...;
}
```

Los `_rerenderX` para los orchestrators aparecen en Fase 6c.

## Decisiones de testing — D5 incorporada

**D5**: no snapshots. Tests target a branches críticos + Playwright.

Para Fase 6a específicamente:
- **NO se añaden unit tests nuevos** para los 8 functions. Razón: cada función es 50-244 líneas con deps a 10+ helpers (ICONS, t, parseProgramTitle, screeningPassed, _resolveVenue, …). Extraer con `loadDomain` requiere armar fixtures gigantes. ROI bajo para 6a (migración mecánica).
- **Playwright T01-T10** debe pasar post-migración. Cubre los flujos donde estas Views renderizan.
- **QA browser manual**: verificar renderAgenda visual idéntico pre/post.
- **Diff de HTML output**: snapshot DOM antes y después de migración, comparar.

Tests más profundos vienen en Fase 6b/6c donde la pureza se vuelve más clara.

## Validate check `[view-purity]` — D6 incorporada

**D6**: warning, no fail, en Fase 6a. Promote a fail en Fase 7.

Implementación:
```python
check = 'view-purity'
TIER1_FNS = ['makeProgramPoster', 'makeEventPoster', 'renderNextStrip',
             'renderUnconfirmed', 'renderGapOptions', '_renderSavedAgendaHTML',
             'renderContextualHeader', 'renderMiPlanCalendar']

# Para cada función Tier 1, inspeccionar el body:
#   - WARN si hay innerHTML/outerHTML = ...
#   - WARN si hay classList.X(...)
#   - WARN si hay appendChild/insertAdjacent
#   - WARN si hay setTimeout/requestAnimationFrame (excluyendo strings)
#   - WARN si hay document.X (excluyendo strings de onclick="..." dentro de
#     template literals)
#   - WARN si hay lectura DIRECTA de cualquier global del roster fuera de
#     un destructure de state.snapshot()
```

Whitelist:
- Refs dentro de template literals backtick (string content)
- `document.X` dentro de strings (onclick handlers)
- El bloque `state.snapshot()` destructure al inicio de función

## Decisiones de diseño incorporadas (resumen)

| # | Decisión | Aplicación en 6a |
|---|---|---|
| D1 | Signature: single `state` param, deps como free vars | ✓ todas las 8 functions |
| D2 | Caller dedicado `_rerenderX` | ⚠ no aplica — las 8 son sub-renders, no orchestrators |
| D3 | `t()` aceptado como localmente puro | ✓ se queda como free var |
| D4 | Nombrado: `renderX` = pure, `_rerenderX` = caller | ⚠ las 8 ya tienen el nombre pure (renderX); zero rename |
| D5 | No snapshots, sí tests por branch crítico | ✓ pero en 6a: **cero tests nuevos** (low ROI) — Playwright cubre |
| D6 | `[view-purity]` como WARNING en 6a | ✓ check implementado nivel warn |
| D7 | 3 sub-PRs (6a → 6b → 6c) | ✓ esta spec cubre solo 6a |

## Definition of Done

- [ ] 8 funciones migradas a signature `(state, ...args)` con destructure de `state.snapshot()` al inicio
- [ ] HTML output **byte-identical** pre/post migración (verificable con diff de DOM dump)
- [ ] Callers actualizados para pasar `state` como primer arg (`renderAgenda`, `shareAsImage`, callers de poster makers)
- [ ] Validate check `[view-purity]` implementado nivel WARNING. 0 warnings para las 8 funciones tras migración
- [ ] `python3 validate.py` → 24/24 (23 previos + 1 nuevo, sin warnings nuevas)
- [ ] `node --test tests/unit/*.test.js` → 131/131 (sin cambios)
- [ ] Playwright T01-T10 pasan (regresión visual)
- [ ] QA browser manual: renderAgenda, shareAsImage, posters de programa/event todos renderizan igual que antes
