# Spec — Event Delegation Wave 2: Dataset reads + stopPropagation (Fase 7c-2)

## Problema

Tras 7c-1 quedan **96 onclick inline** en `index.html`. De ellos, **26 sitios**
siguen patrones simples migrables a `data-action` sin necesidad de helpers
nuevos:

- **15 sitios** con `onclick="fn(this.dataset.X[, event])"` puro
- **10 sitios** con `event.stopPropagation()` + `fn(this.dataset.X[, …])` (orden
  variable)
- **1 sitio** `onclick="selectFromDetail(this)"` cuyo registry entry tiene un
  **bug latente** (args incorrectos vs signature real)

El delegated listener añadido en 7c-1 ya soporta:
- Resolución de `data-action` → handler vía `ACTION_REGISTRY`
- Propagation gating vía atributo `data-stop="1"` (ejecuta `stopPropagation()`
  antes del handler)

Las 88 entries del registry ya leen sus args desde `el.dataset.X`. Solo falta:
1. Migrar 26 call sites
2. Renombrar 5 atributos no-canónicos a la convención (`data-title`,
   `data-section`)
3. Añadir 1 entry nueva (`_toggleWLFromList`)
4. Corregir el bug latente del entry `selectFromDetail`

## Causa raíz

Mismo crecimiento orgánico que 7c-1. Estos onclicks ya leían datos del DOM
vía `this.dataset.X` pero el nombre del atributo se inventó localmente en cada
contexto (`data-rmt`, `data-rfs`, `data-wt`, `data-prio-title`, `data-sec`)
en vez de adoptar la convención canónica (`data-title`, `data-section`).

El bug de `selectFromDetail` en el registry quedó latente porque el call site
sigue usando `onclick="selectFromDetail(this)"` (no entra al registry path).

## Solución

### A. Renombre de atributos (precondición bloqueante — CSS selector check)

Antes de cualquier rename, verificar que **ningún CSS selector** depende de
los 5 atributos a renombrar:

```bash
grep -nE '\[data-(rmt|rfs|wt|prio-title|sec)([= ]|\])' index.html
```

Si encuentra match → **detener migración**, reportar al usuario, decidir
estrategia (rename + update CSS, o aplicar Opción C fallback).

Si limpio → proceder con renames:

| Atributo actual | Atributo nuevo | Líneas | Handler |
|---|---|---|---|
| `data-rmt`       | `data-title`   | L5465, L7036 | `removeFromAgenda` |
| `data-rfs`       | `data-title`   | L7037 | `removeFilmFromScenario` |
| `data-wt`        | `data-title`   | L7787, L7803 | `toggleWatched` |
| `data-prio-title`| `data-title`   | L6784 | `togglePriority` |
| `data-sec`       | `data-section` | L9766 | `filterBySection` |

Beneficios:
- Convención uniforme: todo handler que opera sobre películas lee `data-title`
- Registry entries no cambian (siguen leyendo `dataset.title`, `dataset.section`)
- Elimina la divergencia naming que dificultaba grep

### B. Cambios al ACTION_REGISTRY

**1. Añadir nueva entry** en Categoría D (filters/list helpers):

```js
_toggleWLFromList: (el) => _toggleWLFromList(el.dataset.title, el),
```

Justificación de ubicación: contexto plist (lista de pelis), análogo a
`filterByVenue` / `filterBySection`.

**2. Fix `selectFromDetail` entry** en Categoría B:

```js
// Antes (BUG — args no coinciden con signature real):
selectFromDetail: (el) => selectFromDetail(el.dataset.title, el.dataset.day, el.dataset.time),

// Después:
selectFromDetail: (el) => selectFromDetail(el),
```

La función `selectFromDetail(el)` lee internamente `el.dataset.rkey`. El bug
era inactivo porque ningún call site usaba el registry path. Aprovechamos
7c-2 para corregirlo.

**Total entries:** 88 + 1 (`_toggleWLFromList`) = **89**

### C. Migración de 26 sites a data-action

#### Grupo P — Pure dataset reads (15 sites)

```html
<!-- ANTES -->
<button data-day="${d}" onclick="selectAvDay(this.dataset.day)">…</button>

<!-- DESPUÉS -->
<button data-day="${d}" data-action="selectAvDay">…</button>
```

15 sitios siguen este patrón (incluye los 5 con rename de atributo).

#### Grupo P+S — Dataset + stopPropagation (10 sites)

```html
<!-- ANTES -->
<button data-title="${title}" onclick="togglePriority(this.dataset.title);event.stopPropagation()">…</button>

<!-- DESPUÉS -->
<button data-title="${title}" data-action="togglePriority" data-stop="1">…</button>
```

El delegated listener (L3210-3225) ya ejecuta `e.stopPropagation()` ANTES
del handler si `data-stop="1"`. Semánticamente equivalente al patrón
`event.stopPropagation();fn()` Y también al patrón `fn();event.stopPropagation()`
(la propagation post-handler ocurre cuando el inline handler retorna; el
delegated listener retorna inmediatamente tras invocar el handler — el
browser ya recibió stopPropagation antes).

#### Site #26 — `selectFromDetail`

```html
<!-- ANTES -->
<div class="mplan-row…" data-rkey="${_safeRowKey}" onclick="selectFromDetail(this)">…</div>

<!-- DESPUÉS -->
<div class="mplan-row…" data-rkey="${_safeRowKey}" data-action="selectFromDetail">…</div>
```

### D. data-stop="1" infra

Existente desde 7c-1. Aplicada a los 10 sitios P+S. Sin cambios al listener.

## Inventario de los 26 sites

### Grupo P (15 sitios)

| # | Línea | onclick actual | data-action resultante | Atributos |
|---|---|---|---|---|
| 1 | 6172 | `selectAvDay(this.dataset.day)` | `selectAvDay` | `data-day` |
| 2 | 6906 | `toggleWatched(this.dataset.title,event)` | `toggleWatched` | `data-title` |
| 3 | 7037 | `removeFilmFromScenario(this.dataset.rfs,event)` | `removeFilmFromScenario` | `data-title` (renombrado) |
| 4 | 7077 | `openCortoSheetFromEl(this,event)` | `openCortoSheetFromEl` | `data-ct/cc/cd/cdir/cg/cs/cp` (sin cambio) |
| 5 | 9725 | `filterByVenue(this.dataset.venue)` | `filterByVenue` | `data-venue` |
| 6 | 9766 | `filterBySection(this.dataset.sec)` | `filterBySection` | `data-section` (renombrado) |
| 7 | 9785 | `togglePelWL(this.dataset.title,event)` | `togglePelWL` | `data-title` |
| 8 | 9786 | `togglePelPrio(this.dataset.title)` | `togglePelPrio` | `data-title` |
| 9 | 9787 | `toggleWatched(this.dataset.title,event)` | `toggleWatched` | `data-title` |
| 10 | 10093 | `toggleWL(this.dataset.title,event)` | `toggleWL` | `data-title` |
| 11 | 10094 | `togglePelPrio(this.dataset.title)` | `togglePelPrio` | `data-title` |
| 12 | 7787 | `toggleWatched(this.dataset.wt,event)` | `toggleWatched` | `data-title` (renombrado) |
| 13 | 7803 | `toggleWatched(this.dataset.wt,event)` | `toggleWatched` | `data-title` (renombrado) |
| 14 | 7042 | `toggleMplanProg(this,event)` | `toggleMplanProg` | — |
| 15 | 5462 | `toggleMplanProg(this,event)` | `toggleMplanProg` | — |

### Grupo P+S (10 sitios)

| # | Línea | onclick actual | data-action + data-stop="1" | Atributos |
|---|---|---|---|---|
| 16 | 5465 | `removeFromAgenda(this.dataset.rmt);event.stopPropagation()` | `removeFromAgenda` | `data-title` (renombrado) |
| 17 | 7036 | `removeFromAgenda(this.dataset.rmt);event.stopPropagation()` | `removeFromAgenda` | `data-title` (renombrado) |
| 18 | 6784 | `event.stopPropagation();togglePriority(this.dataset.prioTitle)` | `togglePriority` | `data-title` (renombrado) |
| 19 | 6879 | `togglePriority(this.dataset.title);event.stopPropagation()` | `togglePriority` | `data-title` |
| 20 | 6897 | `openRatingSheet(this.dataset.title);event.stopPropagation()` | `openRatingSheet` | `data-title` |
| 21 | 10431 | `event.stopPropagation();_toggleWLFromList(this.dataset.title,this)` | `_toggleWLFromList` | `data-title` |
| 22 | 10531 | `event.stopPropagation();_toggleWLFromList(this.dataset.title,this)` | `_toggleWLFromList` | `data-title` |
| 23 | 10539 | `event.stopPropagation();_toggleWLFromList(this.dataset.title,this)` | `_toggleWLFromList` | `data-title` |
| 24 | 10651 | `event.stopPropagation();toggleWL(this.dataset.title,event)` | `toggleWL` | `data-title` |
| 25 | 10746 | `event.stopPropagation();toggleWL(this.dataset.title,event)` | `toggleWL` | `data-title` |

### Site #26 — Fix bonus

| # | Línea | onclick actual | data-action resultante |
|---|---|---|---|
| 26 | 5453 | `selectFromDetail(this)` | `selectFromDetail` |

## Sub-fases siguientes (no en 7c-2)

| Sub-fase | Scope | Sites |
|---|---|---|
| **7c-3** | Multi-statement (Patrones A-J) + interpolations | ~42 |
| **7c-4** | IIFE + conditional + overlay close + edge cases | ~18 |

## Decisiones de diseño incorporadas

| # | Decisión | Aplicación en 7c-2 |
|---|---|---|
| D1 | Atributos no-canónicos | **Opción A**: renombrar 5 atributos (`data-rmt/rfs/wt/prio-title/sec`) → canónicos (`data-title`, `data-section`). Precondición CSS check bloqueante. |
| D2 | `_toggleWLFromList` location | **Categoría D** (filters/list helpers) — análogo a filterByVenue/Section |
| D3 | `selectFromDetail` entry bug | **Fix incluido**: registry entry → `(el) => selectFromDetail(el)` |
| D4 | Nombre del flag | **`data-stop="1"`** mantenido (ya documentado en listener) |
| D5 | Site count | **26** sites (25 trivial + 1 selectFromDetail bonus) |
| D6 | Validate check ajustes | Sin cambios estructurales — sigue WARNING |
| Inherited 7c-1 | Coexistencia onclick + data-action | ✓ Mantenida (70 sites no migrados siguen funcionales) |

## R2' (functional equivalence — heredado de 7c-1)

Mismo enfoque que 7c-1. HTML output CAMBIA por design (onclick → data-action +
opcional data-stop). Verificación:

1. **Functional equivalence**: cada uno de los 26 elementos migrados, al hacer
   click, produce el mismo state change + UI update que antes
2. **Console clean**: cero errors en consola al interactuar
3. **Playwright T01-T10 + T32**: pasan (cubren los flujos críticos)
4. **Visual diff** (manual): inspección visual de cada tab/sheet
5. **CSS regression check** (precondición): verificar atributos no usados como
   selector — si lo son, detener y reportar

## Lo que NO entra en Fase 7c-2

| Out-of-scope | Razón | Fase |
|---|---|---|
| Multi-statement (~40 sites) | Patrones A-J necesitan helpers de 7c-1 | 7c-3 |
| Interpolation pura `onclick="fn('${var}')"` | Args dinámicos del template | 7c-3 |
| IIFE inline (3-4 sites) | Helper `_scrollToAgSection` ya definido | 7c-4 |
| Conditional onclick (L7052) | Lógica dinámica entre 2 handlers | 7c-4 |
| Overlay close lambdas (L2473, L12101) | Migración a `data-close-bg` | 7c-4 |
| Back-to-top anchor (L12146) | scrollTo({top:0}) — edge | 7c-4 |
| Promote `[event-delegation]` a FAIL | Cuando 7c-4 termine | 7d/8 |

## Definition of Done

- [ ] **CSS selector check** PASS (los 5 atributos no usados como selectors) o
      decisión explícita del usuario sobre cómo proceder
- [ ] 5 atributos renombrados en HTML (`data-rmt/rfs/wt/prio-title/sec`)
- [ ] ACTION_REGISTRY tiene **89 entries**:
      - `_toggleWLFromList` añadido en Categoría D
      - `selectFromDetail` corregido a `(el) => selectFromDetail(el)`
- [ ] **26 sites migrados** (15 Grupo P + 10 Grupo P+S + 1 selectFromDetail)
- [ ] `python3 validate.py` → **26/26**
- [ ] `node --test tests/unit/*.test.js` → 131/131
- [ ] JS syntax check OK
- [ ] **Functional equivalence R2'**: click en cada uno de los 26 sites migrados
      produce el mismo comportamiento que antes
- [ ] Playwright T01-T10 + T32 verde en CI
- [ ] **QA Boot Path obligatorio**: localStorage.clear() + reload + invocar
      handlers sin loadFest → 0 errors
- [ ] Coexistencia funciona — los 70 sites NO migrados aún (onclick inline)
      siguen ejecutándose normalmente
