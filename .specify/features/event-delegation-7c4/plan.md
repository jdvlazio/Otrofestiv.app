# Plan — Event Delegation Wave 4: Final + listener rewrite (Fase 7c-4)

## Restricciones

**R1. Cambios quirúrgicos** — solo:
- 1 listener rewrite (walking-up loop)
- 5 helpers nuevos
- 6 entries nuevas + 1 fix + comentarios header
- 2 refactors de view-helpers (`_posterThumb`, `emptyStateHero`) + sus callers
- 18 migraciones de call site
- 1 promoción del check `[event-delegation]` a FAIL en validate.py

**R2' (functional equivalence)**. HTML cambia por design.

**R3. QA BLOQUEANTE de 125 sites** (requisito de Juan): tras el listener
rewrite, verificación de que los 125 data-action existentes (7c-1/2/3) NO
regresan. Si cualquier site regresa → DETENER, reportar, revisar el rewrite.

**R4. Coexistencia**: tras 7c-4, onclick = 0. No quedan sites inline. La
coexistencia onclick+data-action deja de aplicar (todo migrado).

**R5. Cero cambios en signatures de funciones de dominio.** Los refactors de
`_posterThumb` y `emptyStateHero` son view-helpers (no dominio). Las funciones
invocadas (openPelSheet, openCortoSheet, markWatchedFromPlan, etc.) NO se
modifican.

**R6. QA Boot Path obligatorio** post-migración.

**R7. bump-version + commit atómico** al cierre.

**R8. Check `[event-delegation]` promovido a FAIL** — el último paso de
foundation. Tras 7c-4 el gate previene regresiones de onclick inline.

## Alcance detallado

### Fase 0 — Baseline + verificación PRE

```bash
python3 validate.py        # 26/26
node --test tests/unit/*.test.js   # 131/131
grep -o 'onclick="' index.html | wc -l   # 18 baseline
```

Verificar que `conflict-modal` (Grupo 7, L7317) es distinto de `conflict-sheet`
(confirmar que `_removeConflictModal` no colisiona con `closeConflictSheet`):
```bash
grep -nE "id=[\"']conflict-modal[\"']|id=[\"']conflict-sheet[\"']" index.html
```

### Fase 1 — Helpers nuevos (5)

Insertar después de `_activatePlanFilm` (sección Composite helpers):

```js
function _scrollToSuggestions() {
  document.querySelector('.suggestion-wrap')?.scrollIntoView({behavior:'smooth', block:'start'});
}
function _removeConflictModal() {
  document.getElementById('conflict-modal')?.remove();
}
function _scrollToTop() {
  window.scrollTo({top:0, behavior:'smooth'});
}
function _searchOpenFilm(title) {
  searchClose();
  openPelSheet(title);
}
function _searchOpenCorto(title, country, dur, section, flags) {
  searchClose();
  openCortoSheet(title, country, dur, section, flags);
}
```

### Fase 2 — ACTION_REGISTRY edits (1 fix + 6 adds)

**Fix `_openCombinedFilmSheet`** (Cat B):
```js
_openCombinedFilmSheet:(el) => _openCombinedFilmSheet(JSON.parse(el.dataset.film)),
```

**Add `markWatchedFromPlan`** (Cat E — Mi Plan):
```js
markWatchedFromPlan: (el, e) => markWatchedFromPlan(el.dataset.title, el.dataset.day, el.dataset.time, el.dataset.venue, el.dataset.dur, e),
```

**Add `scrollToSuggestions`, `removeConflictModal`, `scrollToTop`** (Cat D o nueva sub-sección "DOM utils"):
```js
scrollToSuggestions: () => _scrollToSuggestions(),
removeConflictModal: () => _removeConflictModal(),
scrollToTop:         () => _scrollToTop(),
```

**Add `searchOpenFilm`, `searchOpenCorto`** (Cat B — sheets open):
```js
searchOpenFilm:  (el) => _searchOpenFilm(el.dataset.title),
searchOpenCorto: (el) => _searchOpenCorto(el.dataset.title, el.dataset.country, el.dataset.dur, el.dataset.section, el.dataset.flags),
```

Actualizar comentarios header: "91 entries" → "97 entries" + counts de categorías.

**Total post-edit:** 91 + 6 = **97 entries**.

### Fase 3 — Listener rewrite (D1, núcleo)

Reemplazar el listener (L3219-3234 aprox) por el loop manual (ver spec sección
A). **Después de esta fase**: ejecutar inmediatamente la QA bloqueante de 125
sites (Fase 6) ANTES de continuar con las migraciones de Grupo 4 (Pattern H),
para confirmar que el rewrite no regresó nada.

### Fase 4 — View-helper refactors (2)

**`emptyStateHero`** (L5955): param `ctaOnclick` → `ctaTab`, button emite
`data-action="navTo" data-tab="${ctaTab}"`. Actualizar 6 callers (L6820, 7722,
7724, 9169, 9193, 9203).

**`_posterThumb`** (L4463): eliminar param `onclickJs` y la construcción de
`_oc` (L4466). Actualizar 11 callers: 10 quitan el arg `null`, 1 (L7788)
reemplaza por mecanismo js-open-pel.

### Fase 5 — Migración de 18 sites por wave

#### Wave 1 — Grupos 1+2+3 (low risk, infra/helpers existentes, 9 sites)

- Grupo 1: 2 overlays → data-close-bg
- Grupo 2: 3 IIFE → scrollToAgSec
- Grupo 3: 4 Pattern N → _openCombinedFilmSheet (fix ya en Fase 2)

#### Wave 2 — Grupos 5+6+7 (helpers/refactors nuevos, 5 sites)

- Grupo 5: emptyStateHero (cubierto en Fase 4)
- Grupo 6: conditional onclick L7061
- Grupo 7: 3 DOM-direct

#### Wave 3 — Grupo 8 (string builders, 2 sites)

- _posterThumb (cubierto en Fase 4) + L7788 caller
- search-item L11915

#### Wave 4 — Grupo 4 (Pattern H, 2 sites) — DESPUÉS de QA bloqueante

- L5461, L5464 → data-stop="1"
- Depende del listener rewrite (Fase 3) + QA bloqueante (Fase 6) PASSED

### Fase 6 — QA BLOQUEANTE: 125 sites (R3)

**Ejecutar tras Fase 3 (listener rewrite), ANTES de Wave 4.**

1. **Typo check estático**: todos los data-action en DOM resuelven a registry
2. **Browser eval**: cargar festival, enumerar data-action únicos en DOM live,
   verificar 0 missing del registry
3. **Click-test representativo por categoría (A-G)**:
   - A: toggleWL/togglePriority (P+S — verificar stopPropagation)
   - B: closePelSheet, openР ratingSheet
   - C: navTo (cartelera/seleccion)
   - D: filterByVenue/Section
   - E: jumpToScenario
   - F: submitAuthEmail (o similar)
   - G: closePelAndRate, toggleCtxOlder
4. **P+S stopPropagation**: click en int-prio-btn (data-stop) → pel-sheet NO abre
5. Si CUALQUIER site regresa → **DETENER**, reportar, revisar rewrite

Solo tras PASSED → proceder con Wave 4 (Pattern H) que valida la rama nueva.

### Fase 7 — Promote check a FAIL (D6)

Modificar validate.py: `[event-delegation]` de WARNING a FAIL si onclick > 0.

### Fase 8 — Validation gates

1. `python3 validate.py` → 26/26 (con check ya FAIL-level, onclick=0 pasa)
2. `node --test tests/unit/*.test.js` → 131/131
3. JS syntax check
4. Functional equivalence por grupo
5. **QA Boot Path obligatorio**
6. Festival switch atómico

## Validate impact post-7c-4

| Métrica | Pre-7c-4 | Post-7c-4 |
|---|---|---|
| onclick remaining | 18 | **0** |
| data-action (occurrences) | 125 | ~143 |
| data-stop="1" | 21 | ~23 |
| Registry entries | 91 | **97** |
| dead non-composite | 4 | ~0 |
| Check `[event-delegation]` nivel | WARNING | **FAIL** |

## Riesgos y mitigaciones

### R1. Listener rewrite regresión (125 sites)
- **Mitigación**: QA bloqueante Fase 6 antes de Wave 4. Comportamiento idéntico
  para data-action; nueva rama aislada.

### R2. `_posterThumb` refactor — 11 callers
- **Riesgo**: 10 callers pasan `null` como 3er arg (onclickJs). Al eliminar el
  param, el 4to arg (loading) se corre a 3ra posición. Hay que ajustar TODOS
  los callers que pasan `loading`.
- **Mitigación**: revisar cada caller. Verificar cuáles pasan `loading`
  (4to arg). Ajustar posición.

### R3. `emptyStateHero` — `_hasMiPlan` ternary (L9169)
- **Riesgo**: el caller L9169 pasa un ctaOnclick condicional
  (`_hasMiPlan?"...miplan...":"...cartelera..."`). El ctaTab debe ser
  `_hasMiPlan?'mnav-miplan':'mnav-cartelera'`.
- **Mitigación**: migración cuidadosa de ese caller.

### R4. Pattern N JSON.parse — data-film encoding
- **Riesgo**: `data-film` contiene JSON con comillas. Debe estar HTML-escaped
  correctamente (`&quot;`). Verificar que `JSON.parse(el.dataset.film)` funciona
  con el encoding actual.
- **Mitigación**: el atributo data-film YA existe y se usaba con el mismo
  JSON.parse en el onclick original. Mismo encoding. Browser eval verifica.

### R5. search-item — openCortoSheet args
- **Riesgo**: `openCortoSheet(title, country, dur, section, flags, ...)` toma 9
  params; el onclick original pasa 5. Verificar que los 4 restantes son
  opcionales (default).
- **Mitigación**: verificar function signature en exec. El onclick original ya
  pasaba solo 5 → comportamiento idéntico.

### R6. conflict-modal vs conflict-sheet
- **Riesgo**: confusión de nombres. `_removeConflictModal` opera sobre
  `conflict-modal` (creado dinámicamente), distinto de `conflict-sheet`.
- **Mitigación**: verificación PRE en Fase 0.

## Helpers nuevos

**5**: `_scrollToSuggestions`, `_removeConflictModal`, `_scrollToTop`,
`_searchOpenFilm`, `_searchOpenCorto`.

## Tests

**Cero tests nuevos.** Mismo principio. R2' + Playwright + manual QA.

## Backwards compat

Tras 7c-4, onclick = 0 — no más coexistencia. Todo migrado.

## Commit message draft

```
refactor(controller): 7c-4 — final 18 sites + listener rewrite, onclick=0 (p7c-4)

Fase final de event-delegation. onclick inline: 18 → 0.

Listener walking-up rewrite (D1):
- closest('[data-action]') → loop manual con stop detection
- Wrapper data-stop="1" sin data-action bloquea lookup de action ancestro
- Comportamiento idéntico para los 125 sites con data-action (verificado QA bloqueante)

ACTION_REGISTRY (91 → 97 entries):
- Fix _openCombinedFilmSheet: JSON.parse(el.dataset.film)
- Add markWatchedFromPlan, scrollToSuggestions, removeConflictModal,
  scrollToTop, searchOpenFilm, searchOpenCorto

5 helpers nuevos: _scrollToSuggestions, _removeConflictModal, _scrollToTop,
_searchOpenFilm, _searchOpenCorto.

View-helper refactors:
- emptyStateHero: ctaOnclick → ctaTab (data-action="navTo") + 6 callers
- _posterThumb: drop onclickJs param + L7788 caller usa js-open-pel

Migrations (18 sites):
- Grupo 1: 2 overlays → data-close-bg (AvSheet, AuthSheet)
- Grupo 2: 3 IIFE → scrollToAgSec (helper existente)
- Grupo 3: 4 Pattern N → _openCombinedFilmSheet (fix entry)
- Grupo 4: 2 Pattern H → data-stop="1" (listener rewrite)
- Grupo 5: 1 emptyStateHero refactor
- Grupo 6: 1 conditional onclick → markWatchedFromPlan
- Grupo 7: 3 DOM-direct → helpers nuevos
- Grupo 8: 2 string builders → search helpers + _posterThumb refactor

Validate:
- onclick remaining: 18 → 0
- registry: 91 → 97
- Check [event-delegation] PROMOVIDO a FAIL (gate activado)
- 26/26 checks

QA bloqueante 125 sites PASSED. QA Boot Path PASSED. Tests 131/131. JS syntax OK.

Cierra Fase 7c (event-delegation): 142 onclick → 0 en 4 sub-fases.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

## Dependencias entre artefactos

```
Fase 0 (Baseline + PRE verification conflict-modal)
  ↓
Fase 1 (5 helpers nuevos)
  ↓
Fase 2 (ACTION_REGISTRY 1 fix + 6 adds)
  ↓
Fase 3 (Listener rewrite) ──────┐
  ↓                              │
Fase 4 (view-helper refactors)   │
  ↓                              │
Wave 1 (Grupos 1+2+3 — 9 sites)  │
  ↓                              │
Wave 2 (Grupos 5+6+7 — 5 sites)  │
  ↓                              │
Wave 3 (Grupo 8 — 2 sites)       │
  ↓                              │
Fase 6 (QA BLOQUEANTE 125 sites) ←┘ [debe pasar antes de Wave 4]
  ↓ [bloqueante]
Wave 4 (Grupo 4 Pattern H — 2 sites)
  ↓
Fase 7 (Promote check a FAIL)
  ↓
Fase 8 (Validation gates)
  ↓
Commit + Push + PR
```

Nota: el QA bloqueante (Fase 6) corre tras el listener rewrite + las waves
no-Pattern-H, porque verifica que el rewrite no regresó los 125 sites antes de
añadir los 2 wrappers Pattern H que dependen de la rama nueva del listener.
