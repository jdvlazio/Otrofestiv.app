# Spec — View Purity Fase 6b (Tier 2 mixed, 11 funciones + 1 dead)

## Problema

Fase 6a completó las 6 Views Tier 1 (sub-renders pure-ish que ya retornaban
HTML sin side effects). Quedan ~30 funciones View con mezclas de pureza:

- **Group A** (4 fns): retornan HTML sin side effects, pero leen globals
  directamente. Reclasificadas durante auditoría 6b — son **Tier 1 pattern**,
  no Tier 2.
- **Group B** (7 fns): mezclan return HTML + DOM mutations (innerHTML=,
  classList, setTimeout post-render). Necesitan split en pure half + impure
  caller.
- **Group C** (1 fn): dead code orphaned, sin callsites en HEAD.

§16.5 del roadmap define Fase 6 como "View extraction". 6b cubre las
funciones Tier 2 mixed. Tier 3 (orchestrators como renderAgenda) queda
para 6c. Tier 4 (sheets/modals) queda para Fase 7 (Controllers).

## Causa raíz

Crecimiento orgánico: las funciones Tier 2 evolucionaron como "renders
chiquitos que también encajan sus mutaciones DOM aquí adentro porque el call
site solo tiene un consumidor". Esto:

- Mezcla responsabilidades dentro de la misma función
- Imposibilita pasar `state` como param (la función tiene mutación que
  asume DOM disponible)
- Bloquea el camino a Fase 7 (subscribe → render): el subscriber querría
  llamar la pure half, pero la función monolítica también hace DOM commit

## Solución — Fase 6b

Tres acciones distintas según grupo:

### Group A — Reclasificar como Tier 1 pattern (4 funciones)

Migración trivial: añadir `state` param + destructure de `state.snapshot()`
al inicio, sin split.

| Función | Líneas | State reads | Callers |
|---|---|---|---|
| `renderPrioStrip` | 20 | FILMS, PRIO_LIMIT, prioritized | 1 |
| `renderSavedAgendaHTML` | 13 | (via wrapper) | 1 |
| `renderFilmAlternatives` | 36 | FILMS, watched, savedAgenda | 2 |
| `renderFlowProgress` | 23 | savedAgenda | 3 |

### Group B — Split pure + impure caller (7 funciones)

Convención de naming (decisión E1a):

```js
// Pure half — suffix HTML, recibe state, retorna string
function renderXHTML(state, ...args) {
  const { ... } = state.snapshot();
  return `<div>...</div>`;
}

// Impure caller — mismo nombre que antes, mantiene call sites intactos
function renderX(...args) {
  document.getElementById('...').innerHTML = renderXHTML(state, ...args);
}
```

| Función actual | Pure half nueva | Líneas | Callers |
|---|---|---|---|
| `renderRatingStars` | `renderRatingStarsHTML` | 9 → 5+4 | 2 |
| `renderProgramaChips` | `renderProgramaChipsHTML` | 24 → ~18+6 | 1 |
| `renderNoticesBanner` | `renderNoticesBannerHTML` | 20 → ~14+6 | 2 |
| `_renderSplashDropdown` | `_renderSplashDropdownHTML` | 38 → ~30+8 | 4 |
| `_renderFestivalSelector` | `_renderFestivalSelectorHTML` | 41 → ~33+8 | 4 |
| `renderAvDay` | `renderAvDayHTML` | 44 → ~36+8 | 2 |
| `renderFilmListHTML` (ya `HTML`) | `renderFilmListHTML` (queda pura) + nuevo `_rerenderFilmList` impure caller | 175 → 165+10 | 2 |

**Caso especial `renderFilmListHTML`**: ya tiene suffix `HTML`. Aceptamos
asimetría:
- `renderFilmListHTML(state)` queda como la pure half (sin rename)
- `_rerenderFilmList()` nueva — impure caller con prefix `_rerender`
- 2 callers existentes migran de `renderFilmListHTML()` a la combinación
  apropiada según contexto

**Caso especial `renderFilmListHTML` setTimeout**: el `setTimeout` post-
render actualiza 3 pills (prio/int/yv counts). Movido a `_rerenderFilmList`.
La pure half NO incluye setTimeout. El caller recomputa los counts (filter
trivial sobre Sets, O(n)).

### Group C — Dead code remove (1 función)

| Función | Líneas | Motivo |
|---|---|---|
| `renderSimPanel` | 12 | **0 callsites** en HEAD. Probablemente orphaned cuando el sim panel fue reescrito. No aparece en commits recientes como callee |

## API de la View pura — D1 + E1a incorporadas

**D1 (de 6a)**: single `state` param, deps quedan como free vars.

**E1a (nueva, Tier 2)**: suffix `HTML` para la pure half, nombre original
para el impure caller.

```js
// Group B canonical pattern
function renderXHTML(state, arg1, arg2) {
  const { a, b, c } = state.snapshot();
  // free vars OK: t, ICONS, helpers
  return `<div>${t('key')}</div>`;
}

function renderX(arg1, arg2) {
  // Caller — impure: knows about DOM element to mutate
  const el = document.getElementById('container-x');
  if (!el) return;
  el.innerHTML = renderXHTML(state, arg1, arg2);
}
```

## Validate check `[view-purity]` — extensión (E5)

**Cambios**:
1. Rename `TIER1_FNS` → `PURE_FNS` (refleja que el check ahora cubre
   funciones puras de múltiples tiers)
2. Añadir las 4 Group A migradas al `PURE_FNS` list
3. Añadir las 7 Group B **pure halves** (suffix HTML o equivalent) al list
4. NO añadir los impure callers (siguen con side effects legítimos)

**Total post-6b**: ~17 funciones puras tracked por el check.

**Nivel**: sigue WARNING en 6b. Promote a FAIL en Fase 7.

## Lo que NO entra en Fase 6b

| Out-of-scope | Tier | Fase futura |
|---|---|---|
| `renderAgenda`, `render`, `_renderProgramaContent`, `renderProgramaList`, `renderMiPlanList`, `_renderExploreLista`, `renderSbar`, `renderPeliculaView`, `renderAvBlocks`, `_renderAfterSync` | 3 (orchestrators) | 6c |
| `openPelSheet`, `openCortoSheet`, `openAvSheet`, `openConflictSheet`, `openAuthSheet`, `openRatingSheet`, `openFestivalSheet`, `openPostViewRating`, `openCortoSheetFromEl`, `showDestructiveModal`, `showActionModal`, `showConflictModal`, `showActionToast` | 4 (sheets/modals) | 7 (Controllers) |
| Migrar callers (orchestrators) a leer state | — | 6c/7 |

## Test strategy — D5 + E6a (cero tests nuevos)

**Decisión E6a**: confiar en Playwright T01-T10 + DOM CRC pre/post diff +
manual QA browser. Cero unit tests nuevos.

**Justificación**:
- DOM CRC pre/post sigue siendo la verificación más robusta para R2
- Pure halves de Group B son pequeñas (5-30 líneas cada una)
- Snapshot tests son brittle y mantenimiento alto
- Si surge bug en branch específico, añadir test target

**6c** (orchestrators) será donde los tests cobren más valor — Views grandes
con muchas branches.

## Definition of Done

- [ ] 4 Group A migradas como Tier 1 pattern (state param + destructure,
      sin split)
- [ ] 7 Group B split en pure half (`XHTML`) + impure caller (mantiene
      nombre original, salvo `renderFilmListHTML` → `_rerenderFilmList`)
- [ ] 1 dead remove (`renderSimPanel`, ~12 líneas)
- [ ] 23 call sites pasan `state` como primer arg (o aceptan el nuevo
      contract apropiado)
- [ ] `setTimeout` pill updates de `renderFilmListHTML` movido a
      `_rerenderFilmList`. Counts recomputados en el caller
- [ ] Validate check `[view-purity]`: rename `TIER1_FNS` → `PURE_FNS`,
      lista extendida a ~17 funciones puras
- [ ] `python3 validate.py` → 24/24 (sin warnings activas)
- [ ] `node --test tests/unit/*.test.js` → 131/131 (sin cambios)
- [ ] HTML output **byte-identical** pre/post (DOM CRC pre = post)
- [ ] QA browser: Mi Plan, Programa chips, Notices banner, Availability
      sheet, Festival selector, Splash dropdown, Rating sheet, Film list
      pills — todos renderizan igual que antes
- [ ] Playwright T01-T10 pasan (CI)
