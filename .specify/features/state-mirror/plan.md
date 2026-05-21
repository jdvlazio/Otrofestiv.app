# Plan técnico — Fase 5.5

## Restricciones de partida

### R1. Single-file en producción
`state` vive como `const` namespace en index.html, top del script 3,
inmediatamente después del bloque `storage`. Split físico a `model/state.js`
queda para Fase 8.

### R2. Worker intacto
Worker no usa state container — recibe slice serializado vía `postMessage`.
El template literal del worker (líneas ~8441-8443) declara `let watched=`,
`let prioritized=`, etc. dentro de un string — esos no son globals del
main thread y la whitelist del validate check los excluye.

### R3. Mirror invariant — escrituras canalizadas, lecturas no
Toda escritura pasa por `state.set`/`update`/`batchUpdate`. Lecturas siguen
yendo al global directo (`if(watchlist.has(t))`, `FILMS.map(...)`, etc.).
La invariante `state.get(k) === window[mirror(k)]` se preserva por
construcción. **Migrar readers es Fase 5.6, no 5.5.**

### R4. Behavior preservation absoluta
Cada migración semánticamente idéntica al original. Serialización JSON
preservada. Para Sets/Objects que se mutaban in-place (`.add(t)`,
`obj[k]=v`), el reemplazo immutable cambia la identidad del valor pero NO
su contenido observable. §1.6 del inventario confirma cero callsites
dependientes de identidad.

### R5. Test-first para atomicidad
Los tests de `batchUpdate` atómico son **bloqueantes** antes de migrar
`loadFestival`. Sin atomicidad probada, el swap puede corromper en
escenarios reentrantes futuros.

### R6. Paso 7 bloqueante
Tests unitarios de state (set/update/batchUpdate/subscribe/rollback) deben
correr y pasar **antes** de migrar cualquier callsite. Si la API tiene un
bug, lo encontramos en aislamiento, no a través de QA browser.

### R7. `loadFestival` migration last
Es la migración más crítica (15 globals atómicos). Se hace al final, después
de migrar mutaciones individuales y verificar que el mecanismo funciona en
casos simples.

## 1. Diseño del state namespace

### 1.1 Roster de keys → globals (mirror map)

```js
// _MIRROR_TARGETS define el setter que escribe al global. Si el global no
// puede mutarse por scope (e.g., declarado con let dentro de IIFE), se
// resuelve con un objeto adapter. En nuestro caso todos los globals son
// module-level let, así que el setter es trivial.

const _MIRROR_TARGETS = {
  // festival batch
  _activeFestId:        v => { _activeFestId = v; },
  FILMS:                v => { FILMS = v; },
  FESTIVAL_DATES:       v => { FESTIVAL_DATES = v; },
  FESTIVAL_END:         v => { FESTIVAL_END = v; },
  FESTIVAL_STORAGE_KEY: v => { FESTIVAL_STORAGE_KEY = v; },
  PRIO_LIMIT:           v => { PRIO_LIMIT = v; },
  TZ_OFFSET:            v => { TZ_OFFSET = v; },
  FESTIVAL_TRANSPORT:   v => { FESTIVAL_TRANSPORT = v; },
  // user-state
  watchlist:            v => { watchlist = v; },
  watched:              v => { watched = v; },
  prioritized:          v => { prioritized = v; },
  filmRatings:          v => { filmRatings = v; },
  filmDelays:           v => { filmDelays = v; },
  filmDelaysHistory:    v => { filmDelaysHistory = v; },
  savedAgenda:          v => { savedAgenda = v; },
  availability:         v => { availability = v; },
  lastRemovedSlots:     v => { lastRemovedSlots = v; },
  // configuración
  _lang:                v => { _lang = v; },
  _simTime:             v => { _simTime = v; },
};
```

### 1.2 Implementación de `state`

(ver §2.3 del diseño previo — incorporada literal al index.html)

### 1.3 Ubicación en index.html

- Bloque `state` va inmediatamente después del bloque `storage` (post línea
  ~2814), en el top de script 3
- Marcadores `// [STATE-START]` y `// [STATE-END]` para validate.py
- Nueva declaración `let filmDelaysHistory = {};` adyacente a `let
  filmDelays = {};` (línea 4771 aprox)

## 2. Migración de filmDelaysHistory (decisión incorporada)

### 2.1 Backward compat de storage

```js
// storage.getFilmDelaysHistory() lee del nuevo key. Si no existe (primera
// vez post-upgrade), intenta migrar del _hist anidado del key viejo:
getFilmDelaysHistory() {
  try {
    const r = localStorage.getItem(FESTIVAL_STORAGE_KEY + 'delays_hist');
    if (r) return JSON.parse(r);
    // Migración suave: extraer _hist del key viejo si existe
    const old = localStorage.getItem(FESTIVAL_STORAGE_KEY + 'delays');
    if (!old) return {};
    const parsed = JSON.parse(old);
    return parsed._hist || {};
  } catch(e) { return {}; }
}

setFilmDelaysHistory(h) {
  try { localStorage.setItem(FESTIVAL_STORAGE_KEY + 'delays_hist', JSON.stringify(h)); } catch(e) {}
}

// storage.getFilmDelays() actualizado para FILTRAR _hist del valor leído:
getFilmDelays() {
  try {
    const r = localStorage.getItem(FESTIVAL_STORAGE_KEY + 'delays');
    if (!r) return {};
    const parsed = JSON.parse(r);
    const { _hist, ...clean } = parsed;  // strip _hist
    return clean;
  } catch(e) { return {}; }
}
```

### 2.2 Callsite migration (filmDelays anidado, líneas 5162-5178)

```js
// ANTES:
if(!filmDelays._hist) filmDelays._hist={};
if(!filmDelays._hist[k]) filmDelays._hist[k]=[];
filmDelays._hist[k].push(filmDelays[k]||0);
const newVal=Math.max(0,(filmDelays[k]||0)+addMins);
if(newVal===0) delete filmDelays[k]; else filmDelays[k]=newVal;

// DESPUÉS:
state.batchUpdate({
  filmDelaysHistory: (() => {
    const h = state.get('filmDelaysHistory');
    return {...h, [k]: [...(h[k]||[]), filmDelays[k]||0]};
  })(),
  filmDelays: (() => {
    const fd = state.get('filmDelays');
    const newVal = Math.max(0, (fd[k]||0)+addMins);
    if (newVal === 0) { const {[k]:_, ...rest} = fd; return rest; }
    return {...fd, [k]: newVal};
  })(),
});
```

## 3. Validate.py check `[state-mirror]`

### 3.1 Detector

```python
check = 'state-mirror'

# Globals candidatos
STATE_GLOBALS = [
    '_activeFestId', 'FILMS', 'FESTIVAL_DATES', 'FESTIVAL_END',
    'FESTIVAL_STORAGE_KEY', 'PRIO_LIMIT', 'TZ_OFFSET', 'FESTIVAL_TRANSPORT',
    'watchlist', 'watched', 'prioritized', 'filmRatings', 'filmDelays',
    'filmDelaysHistory', 'savedAgenda', 'availability', 'lastRemovedSlots',
    '_lang', '_simTime',
]

# Localiza bloque state
state_start = content.find('// [STATE-START]')
state_end = content.find('// [STATE-END]')

# Whitelist de líneas permitidas fuera del bloque:
#   - declaración inicial `let X` (el roster fijo)
#   - mutaciones in-place dentro del template literal del worker (busca
#     pattern de string template `_workerGlobals = `...``)
#   - escrituras dentro del bloque state (entre STATE-START y STATE-END)

for global_name in STATE_GLOBALS:
    # Pattern detecta: <global> = , <global>.add(, <global>.delete(,
    # <global>.push(, <global>.unshift(, <global>.pop(, <global>.shift(,
    # <global>.splice(, <global>.length =, <global>[k] =, delete <global>[k]
    for match in find_writes(global_name, content):
        line_no = lineno(match)
        if state_start < match.offset < state_end:
            continue  # dentro del bloque state
        if is_initial_declaration(line_no):
            continue  # `let X = []` del roster
        if is_inside_worker_template(line_no):
            continue  # template literal `_workerGlobals = `
        fail(check, f'L{line_no}: escritura no canalizada a {global_name}')

if no_failures:
    ok(check, f'{N} escrituras a state globals canalizadas vía state.set')
```

### 3.2 Whitelist documentada

| Excepción | Líneas | Razón |
|---|---|---|
| `let X = ...` declaración inicial del roster | ~3498, 3635, 4239, 4511, 4516, 4716-19, 4724, 4765-66, 4771, 4773, 4800 | Bootstrap inevitable, una sola vez |
| Bloque `[STATE-START]..[STATE-END]` | ~2815-2980 estimado | Donde el setter mirror legítimamente escribe |
| Template literal `_workerGlobals = \`...\`` | ~8441-8448 | Strings, no globals reales |

## 4. Tests del state container

`tests/unit/state.test.js` — mock de mirror via spy, NO toca globals reales.

### 4.1 Casos críticos (bloqueantes)

| Test | Verifica |
|---|---|
| `set` único → mirror llamado + subscribers notificados sync | path estándar |
| `set` con key sin subs → mirror llamado, no notify | sin error en absent subs |
| `update` → fn recibe valor actual, retorno se setea | composición |
| `batchUpdate({k1,k2,k3})` → 3 mirrors llamados ANTES de cualquier notify | atomicidad core |
| Subscriber A en batchUpdate ve k2 y k3 ya aplicados (no solo k1) | atomicidad post-batch |
| Subscriber A llama `state.set('k4',v)` → k4 se notifica DESPUÉS de los del batch | reentrada limpia |
| Subscriber A llama `state.batchUpdate({k4,k5})` → k4,k5 notifican tras el batch padre | reentrada nested |
| `_MIRROR_TARGETS[k]` throws → snapshot pre-batch restaurado, no notify, error re-lanzado | rollback |
| batchUpdate vacío `{}` → no-op total | edge |
| batchUpdate con clave duplicada (vía función computada que actualiza dos veces) → último gana, 1 notify | dedup |
| `subscribe` retorna unsubscribe fn → llamarla remueve el cb | API contract |
| `unsubscribe` desde dentro de notify → no rompe la iteración del set | snapshot del Set durante notify |
| `snapshot()` shallow → copiar mutación local no afecta state interno | aislamiento |

### 4.2 Tests del mirror invariant (integración con globals)

Tests separados que SÍ tocan globals (vía `loadDomain` con mock globals
inyectados):
- Después de `state.set('watchlist', s)`, el global `watchlist === s`
- Después de `state.batchUpdate({watchlist, watched, prioritized})`, los tres
  globals reflejan los nuevos valores
- Roundtrip: `state.set('_lang', 'en')` → `_lang === 'en'`

### 4.3 Tests de filmDelaysHistory migration

- Storage con key viejo `delays={k1:5, _hist:{k1:[0,3]}}` → `getFilmDelays()`
  retorna `{k1:5}` (sin _hist); `getFilmDelaysHistory()` retorna `{k1:[0,3]}`
- Storage con key nuevo `delays_hist={k1:[0,3]}` → toma ese, ignora `_hist`
  del viejo
- Storage sin ninguno → ambos retornan `{}`

## 5. Migración por categoría — orden de pasos

### Categoría A — Reasignaciones simples (las más seguras)
- `_lang = code` → `state.set('_lang', code)`
- `_simTime = null|new Date(...)` → `state.set('_simTime', ...)`
- `savedAgenda = {schedule:_squeezed}` → `state.set('savedAgenda', ...)`

### Categoría B — Sets (21 sitios)
Patrones reemplazo:
```js
// .add(t) sin guard
watchlist.add(t)
→ state.update('watchlist', s => new Set([...s, t]))

// .delete(t)
watchlist.delete(t)
→ state.update('watchlist', s => { const n = new Set(s); n.delete(t); return n; })

// .add(t) con guard
if(!watchlist.has(t)) watchlist.add(t)
→ state.update('watchlist', s => s.has(t) ? s : new Set([...s, t]))

// Pares/triples
watchlist.delete(t); watched.delete(t); prioritized.delete(t);
→ state.batchUpdate({
    watchlist: deleteFrom(state.get('watchlist'), t),
    watched: deleteFrom(state.get('watched'), t),
    prioritized: deleteFrom(state.get('prioritized'), t),
  });
```

Helper en el bloque state:
```js
const _addToSet = (s, t) => s.has(t) ? s : new Set([...s, t]);
const _delFromSet = (s, t) => { const n = new Set(s); n.delete(t); return n; };
```

### Categoría C — Objects (filmRatings, savedAgenda, availability, filmDelays)
```js
// obj[k] = v
filmRatings[title] = rating
→ state.update('filmRatings', o => ({...o, [title]: rating}))

// delete obj[k]
delete filmRatings[title]
→ state.update('filmRatings', o => { const {[title]:_, ...rest} = o; return rest; })

// obj.path = newArr (reassignment de prop anidada)
savedAgenda.schedule = savedAgenda.schedule.filter(...)
→ state.update('savedAgenda', a => ({...a, schedule: a.schedule.filter(...)}))

// obj.path.push(x)
savedAgenda.schedule.push(obj)
→ state.update('savedAgenda', a => ({...a, schedule: [...a.schedule, obj]}))

// availability[d].blocks = [...]
availability[day].blocks = []
→ state.update('availability', a => ({...a, [day]: {...a[day], blocks: []}}))
```

### Categoría D — Array `lastRemovedSlots`
```js
lastRemovedSlots = lastRemovedSlots.filter(...);
lastRemovedSlots.unshift(obj);
if(lastRemovedSlots.length > MAX) lastRemovedSlots.length = MAX;
→ state.update('lastRemovedSlots', arr => {
    const filtered = arr.filter(...);
    filtered.unshift(obj);
    return filtered.slice(0, MAX_REMEMBERED_SLOTS);
  });
```

### Categoría E — `loadFestival` (último, más crítico)
Reemplazar el swap secuencial (líneas 10649-10782) por dos batchUpdates:
1. Clear + cfg-derived values (atómico)
2. Hidrate desde storage (en `loadState`, ya como batchUpdate)

## 6. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Mirror setter no actualiza el global por scope incorrecto | Cada setter es una assignment al `let` declarado en el mismo módulo. Test unitario verifica que tras `state.set`, el global cambió |
| `state.update` con función impura (modifica el valor anterior in-place y lo retorna) | El helper retornado por `update` debe ser puro. Code review focused. Tests cubren mutación accidental |
| `filmDelaysHistory` migration: usuario con `_hist` viejo en storage → leído correctamente UNA VEZ; al siguiente save sólo el key nuevo se persiste | Ya cubierto por `getFilmDelaysHistory()` fallback + `getFilmDelays()` strip de `_hist` |
| `loadFestival` batchUpdate dispara un subscriber que re-llama `loadFestival` | No habrá subscribers conectados en 5.5 (Fase 6+). Riesgo nulo en 5.5. Test exhaustivo cuando aparezcan |
| El template literal del worker contiene `let watched=new Set()` que el validate puede detectar como write inicial | El whitelist detecta string templates por contexto sintáctico (regex sobre líneas que están dentro de un literal `_workerGlobals = \``) |
| Bootstrap order: `state` namespace referencia setter de `filmDelaysHistory` pero el `let filmDelaysHistory` se declara después en el flujo del script | Mover la declaración `let filmDelaysHistory={};` antes del bloque state (línea ~2810, justo antes de `[STATE-START]`), junto al resto del roster que ya viene declarado |
| `state.set` antes de `state.init` (durante bootstrap muy temprano) → mirror al global escribe pero global aún no fue declarado | El bloque state declara `let filmDelaysHistory` ANTES del namespace. Los otros globals ya están declarados en el código existente al momento de cargar el bloque state |

## 7. Tamaño estimado

| Concepto | Líneas |
|---|---|
| `state` namespace (incluyendo `_MIRROR_TARGETS` + helpers) | ~150 |
| Test file `tests/unit/state.test.js` | ~250 |
| Validate check `[state-mirror]` | ~50 |
| `storage.{get,set}FilmDelaysHistory` + ajuste `getFilmDelays` | ~25 |
| `let filmDelaysHistory = {}` (nueva declaración) | 1 |
| Callsites migrados (escrituras): 21 sets + ~17 objects + 3 arrays + ~10 reasignaciones + 1 loadFestival | ~180 líneas tocadas (mayormente puntuales) |
| **Total nuevo + modificado** | **~650 líneas** |

Validar contra §16.8 limit (>200 líneas tocadas → split). Estamos por encima.
**Mitigación:** plan/tasks lo dividen lógicamente en categorías commit-able
si Juan prefiere mergear por etapas (ver §8).

## 8. Estrategia de PR

Opciones:

**A. Single PR (recomendada).** Igual que Fase 5, atómico. Diff es grande
pero localizado en patches puntuales. Tests cubren atomicidad. QA exhaustivo
post-merge.

**B. Split en 2 PRs.**
- PR-1: namespace `state` + tests + validate check + `filmDelaysHistory`
  storage adapter (sin migrar callsites). Validate check pasa con el
  bloque vacío.
- PR-2: migración de todos los callsites. Validate check ahora exige cero
  escrituras fuera del bloque.

A es más simple y refleja el flujo de Fase 5. B reduce blast radius por PR
pero introduce un commit intermedio donde `state` existe pero nadie lo usa.

**Default propuesto: A.**

## 9. Orden de validación pre-commit

1. `python3 validate.py` → 23/23 (incluye `[state-mirror]`)
2. `node --test tests/unit/*.test.js` → 100% pass (espera ~130 tests post-fase)
3. JS syntax check (extracción de 3 scripts via SCHEMA checklist)
4. QA browser:
   - Watchlist add/remove → persiste post-reload
   - Festival switch (Tribeca → AFF si disponible, o doble switch a Tribeca) → todo el state cambia atómicamente
   - Cambio de idioma → persiste
   - Sim time → afecta `simNow`
   - filmDelays: marcar retraso → undo → state restaurado (filmDelaysHistory funciona)
5. Diff review: cero cambios de comportamiento, solo escrituras canalizadas
6. `node scripts/bump-version.js`
7. Commit + push + PR
