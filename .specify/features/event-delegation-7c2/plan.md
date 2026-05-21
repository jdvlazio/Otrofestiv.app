# Plan — Event Delegation Wave 2 (Fase 7c-2)

## Restricciones

**R1. Cambios quirúrgicos** — solo:
- 1 CSS selector check (read-only, precondición)
- 5 renames de atributos en HTML
- 2 ediciones al ACTION_REGISTRY (1 add + 1 fix)
- 26 migraciones de call site (onclick → data-action)

Cero cambios en signatures de funciones, lógica de handlers, helpers existentes,
o validate.py.

**R2' (functional equivalence — heredado 7c-1).** HTML cambia por design.
Verificación funcional + Playwright + manual QA. No DOM CRC.

**R3. CSS selector check bloqueante.** Si cualquiera de los 5 atributos
(`data-rmt`, `data-rfs`, `data-wt`, `data-prio-title`, `data-sec`) aparece
como CSS selector → DETENER migración, reportar al usuario, esperar decisión.

**R4. Coexistencia onclick + data-action.** Tras 7c-2:
- 70 sitios con onclick inline (no migrados aún) siguen funcionales
- 72 sitios con data-action (46 de 7c-1 + 26 nuevos) gestionados por delegated listener
- Ambos paths coexisten sin interferencia (listener solo activa `[data-action]`)

**R5. Cero cambios en signatures.** Las 8 funciones afectadas (`selectAvDay`,
`toggleWatched`, `removeFilmFromScenario`, `openCortoSheetFromEl`,
`filterByVenue`, `filterBySection`, `togglePelWL`, `togglePelPrio`, `toggleWL`,
`toggleMplanProg`, `removeFromAgenda`, `togglePriority`, `openRatingSheet`,
`_toggleWLFromList`, `selectFromDetail`) NO se modifican.

**R6. QA Boot Path obligatorio** post-migración. Heredado de 6c/7a/7c-1.

**R7. bump-version + commit atómico** al cierre.

**R8. Validate check `[event-delegation]`** sigue nivel WARNING. No promoción a
FAIL en 7c-2 (planificada para post-7c-4).

## Alcance detallado

### Fase 0 — CSS Selector Check (precondición bloqueante)

**Comando:**
```bash
grep -nE '\[data-(rmt|rfs|wt|prio-title|sec)([= ]|\])' index.html
```

**Decisión gate:**
- 0 matches → **GO** — proceder con migración
- ≥1 match → **STOP** — detener, reportar líneas y selectors al usuario,
  esperar instrucción explícita

Razón: si CSS depende del nombre del atributo, renombrar romperá estilos
sin que validate.py lo detecte (validate solo verifica JS y DOM critical
divs).

### Fase 1 — ACTION_REGISTRY edits (2 ediciones)

**Edit 1 — Fix `selectFromDetail` entry** (Categoría B):

```js
// L3141 — ANTES (bug latente)
selectFromDetail:      (el)    => selectFromDetail(el.dataset.title, el.dataset.day, el.dataset.time),

// DESPUÉS
selectFromDetail:      (el)    => selectFromDetail(el),
```

Justificación: `function selectFromDetail(el)` (L7170) recibe el elemento y
lee `el.dataset.rkey`. Los 3 args del entry actual son ignorados. Cambio
inactivo hoy (call site usa `onclick="selectFromDetail(this)"`), activo
después de 7c-2.

**Edit 2 — Añadir `_toggleWLFromList`** en Categoría D:

```js
// Insertar en bloque D (post `_toggleEveningFilms:` L3163)
_toggleWLFromList:   (el)    => _toggleWLFromList(el.dataset.title, el),
```

Justificación: 3 call sites (L10431, L10531, L10539) en context plist. La
función espera `(title, btn)`; pasamos `(el.dataset.title, el)`.

**Total post-edit:** 89 entries (88 + 1).

### Fase 2 — HTML rename de 5 atributos

| # | Línea | ANTES (substring) | DESPUÉS |
|---|---|---|---|
| 1 | 5465 | `data-rmt="${safeT}"` | `data-title="${safeT}"` |
| 2 | 6784 | `data-prio-title="${title.replace(/"/g,'&quot;')}"` | `data-title="${title.replace(/"/g,'&quot;')}"` |
| 3 | 7036 | `data-rmt="${safeT}"` | `data-title="${safeT}"` |
| 4 | 7037 | `data-rfs="${safeT}"` | `data-title="${safeT}"` |
| 5 | 7787 | `data-wt="${(s._title||'').replace(/"/g,'&quot;')}"` | `data-title="${(s._title||'').replace(/"/g,'&quot;')}"` |
| 6 | 7803 | `data-wt="${(f.title||'').replace(/"/g,'&quot;')}"` | `data-title="${(f.title||'').replace(/"/g,'&quot;')}"` |
| 7 | 9766 | `data-sec="${f.section.replace(/"/g,'&quot;')}"` | `data-section="${f.section.replace(/"/g,'&quot;')}"` |

7 ediciones de atributo en 6 líneas (L7036 + L7037 son el mismo template,
ambos renombres en líneas separadas).

⚠ **Nota L6784**: el `togglePriority` de ese sitio originalmente pasaba
`this.dataset.prioTitle` — el rename del atributo a `data-title` Y el migration
del call site a `data-action="togglePriority"` quedan acoplados. Si solo
renombras el atributo sin migrar el call site, el onclick inline rompería
(`this.dataset.prioTitle` quedaría undefined). **Orden importante: rename Y
migrate en el MISMO commit / wave.**

### Fase 3 — Wave plan (4 waves)

#### Wave 1 — HTML renames (atomic, 7 ediciones)

Renames de los 5 atributos en 6 líneas. Después de este wave, el onclick
inline de cada uno ROMPERÍA si quedara solo (porque lee `this.dataset.rmt`
pero el atributo es ahora `data-title`). Por eso debe ir junto con Wave 2.

**Estado intermedio inestable** — no validar entre Wave 1 y Wave 2.

#### Wave 2 — Grupo P migration (15 sites)

Cada call site:
```html
<!-- ANTES -->
<X data-Y="..." onclick="fn(this.dataset.Y[, event])">

<!-- DESPUÉS -->
<X data-Y="..." data-action="fn">
```

Aplicar mass-replace site por site (no regex global — los args entre paréntesis
varían).

#### Wave 3 — Grupo P+S migration (10 sites)

Cada call site:
```html
<!-- ANTES (orden A) -->
<X data-Y="..." onclick="fn(this.dataset.Y[, event]);event.stopPropagation()">

<!-- ANTES (orden B) -->
<X data-Y="..." onclick="event.stopPropagation();fn(this.dataset.Y[, args])">

<!-- DESPUÉS -->
<X data-Y="..." data-action="fn" data-stop="1">
```

Ambos órdenes (`;event.stopPropagation()` y `event.stopPropagation();...`)
mapean al mismo resultado migrado.

#### Wave 4 — selectFromDetail bonus (1 site)

```html
<!-- L5453 ANTES -->
<div class="mplan-row..." data-rkey="${_safeRowKey}" onclick="selectFromDetail(this)">

<!-- DESPUÉS -->
<div class="mplan-row..." data-rkey="${_safeRowKey}" data-action="selectFromDetail">
```

### Fase 4 — Validation gates

Post-Wave 4:

1. `python3 validate.py` → 26/26
2. `node --test tests/unit/*.test.js` → 131/131
3. JS syntax check (`node --check`)
4. Functional equivalence smoke test
5. QA Boot Path obligatorio
6. Festival switch atómico (Tribeca↔Leviza) — verifica listener post-DOM rebuild

## Validate impact post-7c-2

| Métrica | Pre-7c-2 | Post-7c-2 |
|---|---|---|
| onclick remaining | 96 | 70 |
| data-actions únicos usados | 36 | ~45 |
| Registry entries | 88 | 89 |
| Dead non-composite | 41 | ~31 (10 menos) |
| Check `[event-delegation]` nivel | WARNING | WARNING (sin cambio) |

## Riesgos y mitigaciones

### R1. CSS selector breakage (D1 Opción A)
- **Riesgo**: si CSS usa `[data-rmt]` etc, rename rompe estilo.
- **Mitigación**: CSS check bloqueante en Fase 0. Si match, escalar al usuario.

### R2. Estado intermedio inestable Wave 1↔2
- **Riesgo**: si validate falla entre waves, branch queda con HTML roto.
- **Mitigación**: ejecutar Wave 1 y Wave 2 secuencialmente sin validate entre
  ambos. Validate solo post-Wave 4.

### R3. `data-stop="1"` semantic con orden `fn();stopPropagation()`
- **Riesgo**: el patrón "primero fn luego stopPropagation" inline ejecuta el
  handler y LUEGO detiene propagation. El listener delegado con `data-stop="1"`
  detiene propagation ANTES del handler.
- **Análisis**: el handler en sí no propaga el evento — la propagation sucede
  cuando el inline handler retorna (a través del bubble phase). El listener
  delegado intercepta en bubble phase también; al llamar stopPropagation
  ANTES del handler, evita que ancestros reciban el evento — exactamente el
  efecto deseado por el patrón inline. Semánticamente equivalente.
- **Verificación**: QA browser — click en cada P+S site y confirmar que
  ancestros NO reciben el click (e.g., row con onclick no se dispara cuando
  el botón child con stopPropagation se clickea).

### R4. `_toggleWLFromList` con `this` second arg
- **Riesgo**: la función espera `(title, btn)` donde `btn` debe ser el elemento
  visual del corazón. El listener pasa `e.target.closest('[data-action]')`.
- **Análisis**: en los 3 call sites (L10431/10531/10539), el elemento con
  data-action ES el corazón (`<div class="plist-heart">`). Si el click es
  directo sobre el div, `e.target === el === btn`. Si hay un child (no es
  el caso aquí), `e.target.closest('[data-action]')` sigue devolviendo el div.
- **Verificación**: QA browser — toggle WL desde plist y confirmar que el icon
  cambia (la función actualiza `btn.innerHTML`).

### R5. `openCortoSheetFromEl(this, event)` con dataset complejo
- **Riesgo**: la función lee `data-ct/cc/cd/cdir/cg/cs/cp` del elemento. Registry
  entry pasa `(el, e)`.
- **Análisis**: function signature `openCortoSheetFromEl(el, e)`. Sin cambios
  necesarios. Funciona idéntico.

### R6. `selectFromDetail` activation
- **Riesgo**: el fix activa el path registry para selectFromDetail. Si la
  función tiene side effects que dependen del onclick context (raro pero
  posible), el delegated path puede diferir.
- **Análisis**: function signature `selectFromDetail(el)`. No usa `this`, no
  depende de `event`. Cero side effects context-dependent. Cambio seguro.

## Helpers nuevos

**Cero.** Toda la migración usa entries existentes o el nuevo entry
`_toggleWLFromList`.

## Tests

**Cero tests nuevos.** Heredado de 7c-1 (I7): R2 byte-identical NO aplica.
Verificación = functional equivalence + Playwright + manual QA.

## Backwards compat

Mismo principio 7c-1 (I5): coexistencia onclick + data-action. Los 70 onclick
no migrados aún siguen ejecutándose normalmente. El delegated listener solo
activa elementos con `data-action`.

## Validate check `[event-delegation]`

Sin cambios estructurales. Sigue WARNING. Reporta automáticamente:
- onclick remaining count (de 96 → 70)
- typos `data-action="X"` sin entry en registry
- dead entries non-composite (de 41 → ~31)

## Commit message draft

```
refactor(controller): 7c-2 — event delegation wave 2: 26 sites + 5 attribute renames

CSS selector check PASSED — los 5 atributos (data-rmt/rfs/wt/prio-title/sec)
no se usan como CSS selectors.

ACTION_REGISTRY edits:
- Fix selectFromDetail entry: (el) => selectFromDetail(el) (era bug latente)
- Add _toggleWLFromList en Categoría D (filters/list helpers)
- Total entries: 88 → 89

HTML attribute renames (uniformidad data-title / data-section):
- data-rmt → data-title (L5465, L7036)
- data-rfs → data-title (L7037)
- data-wt → data-title (L7787, L7803)
- data-prio-title → data-title (L6784)
- data-sec → data-section (L9766)

Migrations (26 sites):
- Wave 2: Grupo P — 15 pure dataset reads (onclick → data-action)
- Wave 3: Grupo P+S — 10 dataset + stopPropagation (gain data-stop="1")
- Wave 4: selectFromDetail bonus (L5453) — aprovecha fix del entry

Validate:
- onclick remaining: 96 → 70
- data-actions usados: 36 → ~45
- dead non-composite: 41 → ~31
- 26/26 checks (sin cambios al check [event-delegation])

QA Boot Path PASSED. Tests 131/131. JS syntax OK.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

## Dependencias entre artefactos

```
Fase 0 (CSS check)
  ↓ [bloqueante]
Fase 1 (ACTION_REGISTRY edits — 2)
  ↓
Fase 2 (HTML renames — 7 ediciones)
  ↓ [estado intermedio inestable]
Fase 3 Wave 2 (Grupo P — 15)
  ↓
Fase 3 Wave 3 (Grupo P+S — 10)
  ↓
Fase 3 Wave 4 (selectFromDetail — 1)
  ↓
Fase 4 (Validate gates — 6 checks)
  ↓
Commit + Push + PR
```
