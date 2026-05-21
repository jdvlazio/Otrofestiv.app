# Spec — View Purity Fase 6c (Tier 3 orchestrators, 7 funciones + 1 dead)

## Problema

Fase 6a completó Tier 1 (6 sub-renders pure-ish). Fase 6b completó Tier 2
(11 fns con mezcla return-HTML + side effects). Quedan los **Tier 3
orchestrators**: las funciones grandes que componen sub-renders y commitean
HTML a containers raíz de cada tab/vista.

Tras auditoría detallada, los 10 candidates iniciales se distribuyen en 4
grupos según patrón de side effects:

- **Group I (5 fns)**: orchestrators splittable — innerHTML a un container
  raíz, follow-ups uniformes. Aplica patrón E1a de Tier 2 (pure half +
  impure caller).
- **Group II (2 fns)**: branchy orchestrators con follow-ups branch-específicos.
  Split impráctico (duplicaría branching o requeriría return de tupla).
  Aplica patrón D1 (state destructure al top, sin split).
- **Group III (2 fns)**: Controllers — sin innerHTML, solo dispatch +
  classList. Skip de 6c, entran en Fase 7.
- **Group IV (1 fn)**: dead code orphaned (`renderMiPlanList`).

§16.5 del roadmap define Fase 6 como "View extraction". 6c cierra la capa
View en index.html (single-file). Fase 7 introduce Controller layer (sheets,
event handlers, subscribe→render pipeline). Fase 8 hace el file split.

## Causa raíz

Los orchestrators son **inherentemente impuros**: su responsabilidad es
coordinar una actualización del DOM consistente entre varios sub-renders.
Algunos pueden splittearse limpio (1 root container, follow-ups uniformes —
Group I); otros tienen branching con follow-ups distintos por branch
(Group II — split distorsionaría la API).

## Solución — Fase 6c

### Group I — Split E1a (5 funciones)

Mismo patrón Tier 2:

```js
function renderXHTML(state, ...args) {
  const { ... } = state.snapshot();
  return `<div>...</div>`;
}

function renderX(...args) {
  const el = document.getElementById('container-x');
  if (!el) return;
  el.innerHTML = renderXHTML(state, ...args);  // state como free var
  // follow-ups si los hay
}
```

| Función | Líneas | State reads | Callers | Notas |
|---|---|---|---|---|
| `renderAvBlocks` | 26 | availability | 6 | Simple — 1 innerHTML, sin follow-ups |
| `renderSbar` | 30 | FILMS | 2 | innerHTML + classList + appendChild — pure half cubre innerHTML; appendChild/classList quedan en impure caller |
| `renderProgramaList` | 60 | FILMS, _activeFestId, watchlist | 1 | innerHTML en programa-list |
| `_renderExploreLista` | 64 | FILMS, _activeFestId, watchlist | 1 | innerHTML en programa-list |
| `renderPeliculaView` | 101 | FILMS, watched, watchlist | 4 | 3 innerHTML — investigar al implementar si multi-container requiere helpers múltiples o tupla return |

### Group II — State destructure only (2 funciones)

Mismo patrón Tier 1 de 6a (state param o destructure al tope):

```js
function renderX() {
  const {a, b, c} = state.snapshot();
  // ... body original sin más cambios ...
  // (sigue branchy con multiple innerHTML y follow-ups)
}
```

**Cero signature change** (F3). Cero cambios en los 50+ callers totales.

| Función | Líneas | Por qué no split |
|---|---|---|
| `renderAgenda` | 78 | 3 branches main + early returns + follow-ups branch-específicos (`_scrollMiPlanToNow`, `_updateMiPlanBadge`, `renderAvBlocks`, `requestAnimationFrame(_fixStickyOffset)`, `_agHi.style.display='none'`) |
| `render` | 53 | Multi-dispatcher — 4 early returns con calls a `renderSbar`/`renderPeliculaView`/`lugarClose`. Más dispatcher que renderer |

### Group III — Skip (Controllers, Fase 7)

| Función | Naturaleza |
|---|---|
| `_renderProgramaContent` | 0 state reads, solo classList toggles + dispatch a sub-renders (renderNoticesBanner, renderPeliculaView/renderProgramaList/_renderExploreLista). Es Controller. Fase 7 |
| `_renderAfterSync` | 4 líneas, 0 state, solo dispatch. Controller mínimo |

### Group IV — Dead remove (1 función)

| Función | Líneas | Motivo |
|---|---|---|
| `renderMiPlanList` | 44 | 0 callsites en HEAD. Verificación git history antes de remover (paso bloqueante en tasks) |

## Decisiones de diseño incorporadas (F1-F7)

| # | Decisión | Aplicación en 6c |
|---|---|---|
| F1 | Split E1a para Group I | ✓ 5 funciones, 5 pure halves nuevas con suffix `HTML` |
| F2 | Group II destructure-only, no split | ✓ renderAgenda + render |
| F3 | Impure callers usan state como free var | ✓ Cero signature change, cero caller churn |
| F4 | PURE_FNS extiende a ~22 fns | ✓ +5 Group I pure halves |
| F5 | Group II NO en PURE_FNS (impure legítimo) | ✓ Documentado |
| F6 | QA boot path **obligatorio** (mandatory step) | ✓ Paso 23 en tasks.md — atrapa caller-missing-state bugs antes de CI |
| F7 | renderMiPlanList dead remove | ✓ Con verificación git history previa |

## Validate check `[view-purity]` — extensión

Añadir 5 pure halves nuevas a `PURE_FNS`:
- `renderAvBlocksHTML`
- `renderSbarHTML`
- `renderProgramaListHTML`
- `_renderExploreListaHTML`
- `renderPeliculaViewHTML` (o helpers múltiples si multi-container; ajustar al implementar)

**Total post-6c**: 22 funciones puras tracked (17 pre-6c + 5 nuevas).

**Nivel**: sigue WARNING en 6c. Promote a FAIL en Fase 7.

**Group II** (`renderAgenda`, `render`) NO entran en PURE_FNS — son impure
legítimos. Documentado en `validate.py` con comentario.

## Lo que NO entra en Fase 6c

| Out-of-scope | Razón | Fase futura |
|---|---|---|
| Tier 4 sheets/modals (13 fns) | UI lifecycle, no Views | 7 (Controllers) |
| `_renderProgramaContent`, `_renderAfterSync` | Controllers ya, sin state reads | 7 |
| Migrar callers para recibir state como param | Caller churn prohibitivo (60+ sites) y bajo valor | Fase 8 (file split) si necesario |
| Eliminar el mirror global (5.5) | Mirror sigue siendo backward compat hasta que todo reader migre | Fase 8 |

## QA boot path — obligatorio (F6)

**Background**: el bug de Fase 6b (CI atrapó `renderFilmListHTML()` sin state)
reveló que mi QA local con `loadFestival(tribeca2026)` pre-cargado oculta
bugs de boot path. Cuando el smoke test `T32 — navegar entre 4 tabs` corre
post-boot SIN haber llamado loadFestival, los call sites no migrados fallan.

**Paso obligatorio en tasks.md** (no opcional):

```
QA boot path:
1. Cleanup browser state: localStorage.clear() + reload
2. ANTES de loadFestival(*), llamar a:
   - showAgView()
   - render()
   - _renderProgramaContent()
3. Verificar consola sin errors
4. Solo si paso 3 limpio → seguir con QA flow normal (loadFestival, switches, etc.)
```

Atrapa caller-missing-state bugs antes de CI.

## Definition of Done

- [ ] 5 Group I split en pure half (`<X>HTML`) + impure caller
- [ ] 2 Group II con `state.snapshot()` destructure al top, sin signature change
- [ ] 1 dead remove (`renderMiPlanList`) con verificación git history previa
- [ ] 0 callers actualizados (impure callers acceden state como free var)
- [ ] Validate check `[view-purity]`: `PURE_FNS` extendido a 22 funciones
- [ ] `python3 validate.py` → 24/24
- [ ] `node --test tests/unit/*.test.js` → 131/131
- [ ] HTML output **byte-identical** pre/post (DOM CRC match)
- [ ] **QA boot path obligatorio**: cleanup + reload + invocar Tier 3 fns
      ANTES de loadFestival → cero errors
- [ ] QA flow normal — Mi Plan, Programa list/grid, Pelicula view, Sbar,
      Availability sheet
- [ ] Playwright T01-T10 + T32 (smoke navegación tabs) verde en CI
