# Plan técnico — Fase 5

## Restricciones de partida

### R1. Single-file en producción
Mismo invariante de Fases 1–4. `storage` vive como `const` namespace en index.html.
Split físico a `model/storage.js` queda para Fase 8 del destino MVC.

### R2. Worker intacto
Worker no usa localStorage — recibe state vía `postMessage`. Cero cambios.

### R3. Globals como source of truth
`watchlist`, `watched`, `savedAgenda`, etc. siguen siendo `let` mutables a
nivel módulo. `storage` solo encapsula la I/O. Los globals se asignan tras
`storage.getX()` y se persisten con `storage.setX(global)`. **Lecturas en
runtime siguen siendo del global, NO del storage adapter** (por performance
y para no cambiar el contrato de Model functions).

### R4. Behavior preservation absoluta
Cada migración de callsite es semánticamente idéntica al código original.
JSON serialization preservada (mismo formato byte-a-byte en localStorage).

### R5. Test infrastructure extension
`load-domain.js` gana soporte para extraer `const NAME = {...}` (~30 líneas
añadidas). Cero impacto en tests existentes.

### R6. Paso 4 bloqueante
El paso 4 (smoke test del loader con un fixture) es bloqueante. Si
`extractObject` no extrae correctamente un object simple, no se avanza al
paso 5. La extracción de `storage` depende enteramente de este mecanismo.

## Cambios en index.html

### Nueva sección — "STORAGE ADAPTER"

Ubicación: cerca de `FESTIVAL_STORAGE_KEY` (línea ~4658).

Estructura:
```
// ── STORAGE ADAPTER START ────────────────────────────
// [bloque de contrato sobre storage]
const storage = {
  // user-state, festival-prefixed
  getWatchlist: () => ...,
  setWatchlist: (set) => ...,
  ... (18 métodos)
  // global, no prefix
  getActiveFestId: () => ...,
  ... (6 métodos)
};
// ── STORAGE ADAPTER END ──────────────────────────────
```

Los marcadores `START`/`END` los usa `validate.py` para verificar que
ningún `localStorage.(get|set)Item` quede fuera del bloque.

### Migración de callsites

Inventario (a confirmar en paso 7):
- Reads: ~15 callsites de `localStorage.getItem`
- Writes: ~15 callsites de `localStorage.setItem`
- Total: ~30 callsites

Patrón típico (antes → después):

```js
// ANTES
const wl = JSON.parse(localStorage.getItem(FESTIVAL_STORAGE_KEY + 'wl') || '[]');
watchlist = new Set(wl);

// DESPUÉS
watchlist = storage.getWatchlist();
```

```js
// ANTES
localStorage.setItem(FESTIVAL_STORAGE_KEY + 'wl', JSON.stringify([...watchlist]));

// DESPUÉS
storage.setWatchlist(watchlist);
```

Migración por grupos (un task por grupo para mantener cambios reviewables):
- Set-based items: watchlist, watched, prioritized, _dismissedNotices
- Object items: savedAgenda, availability, filmRatings, filmDelays
- Array items: lastRemovedSlots
- Global keys: otrofestiv_festival, otrofestiv_lang, otrofestiv_build

## Cambios en tests/lib/load-domain.js

```js
// Nueva función ~30 líneas
function extractObject(source, name) {
  const re = new RegExp(`\\bconst\\s+${name}\\s*=\\s*\\{`);
  // Walk braces desde el opening { skipping strings y comments
  // Return `const NAME = { ... };`
}

// Nueva opción en loadDomain
function loadDomain(opts = {}) {
  const objects = opts.objects || [];
  // Extract both functions and objects
  // Include objects in returnObj
}
```

## Tests — diseño

`tests/unit/storage.test.js`:

```js
function mockLocalStorage() {
  const store = new Map();
  return {
    getItem: k => store.has(k) ? store.get(k) : null,
    setItem: (k, v) => store.set(k, String(v)),
    removeItem: k => store.delete(k),
    clear: () => store.clear(),
  };
}

const ls = mockLocalStorage();
const { storage } = loadDomain({
  objects: ['storage'],
  globals: { localStorage: ls, FESTIVAL_STORAGE_KEY: 'test_' },
});
```

Casos cubiertos (~20):
- `getWatchlist()` empty → `Set()` vacío
- `setWatchlist(Set)` + `getWatchlist()` roundtrip
- (similar para watched, prioritized, dismissedNotices)
- `getSavedAgenda()` empty → `null`
- `setSavedAgenda({schedule:[]})` + `getSavedAgenda()` roundtrip
- (similar para availability, filmRatings, filmDelays)
- `getLastRemovedSlots()` empty → `[]`
- `getActiveFestId()` empty → `null`
- Festival-prefixed keys vs global keys: verificar que el prefix se aplica solo a user-state

## Cambios en validate.py

Nuevo check `[storage-encapsulation]`:
```python
# Permitir localStorage.(get|set)Item solo entre los marcadores
# // ── STORAGE ADAPTER START y // ── STORAGE ADAPTER END
# Cualquier callsite fuera de ese rango es un error.
```

Implementación: grep + line range matching. ~20 líneas en validate.py.

## QA browser receta

1. Tribeca activo
2. Añadir 3 películas a watchlist → reload → verify watchlist preserved (3 películas)
3. Marcar 1 como watched → reload → verify watched (1) y watchlist (3) preserved
4. Calcular plan → reload → verify savedAgenda preserved
5. Setear availability block (Mar 21, 10:00–12:00) → reload → verify block preserved
6. Cambiar idioma a EN → reload → verify lang=EN
7. Cambiar festival a AFF → reload → verify activeFestId=aff2026

Cualquier item que NO persista post-reload indica regresión en la migración.

## CI

Sin cambios al workflow `bump-and-validate.yml`. `validate.py` ya corre ahí
y picará el nuevo check `[storage-encapsulation]`.

## Riesgos

| Riesgo | Mitigación |
|---|---|
| Set→Array→Set serialización pierde datos en edge cases | Sets actuales contienen solo strings. Tests cubren explicit. |
| Migración callsite-por-callsite es error-prone (forgotten one) | Validate.py check rechaza cualquier `localStorage.*` fuera del bloque del adapter |
| Cloud save (`_cloudSaveTimer`) depende del formato de localStorage | Storage adapter preserva formato byte-a-byte. Cloud save sigue trabajando contra los mismos keys con los mismos valores. |
| Migración rompe ordering de inicialización (e.g., bootstrap lee storage antes de que loadFestival arme FESTIVAL_STORAGE_KEY) | Mantener el orden actual de inicialización. Si la lectura inicial es problemática, agregar guards `storage.getX()` con default null si FESTIVAL_STORAGE_KEY no está set. |
| Loader no extrae objetos correctamente | Paso 4 es bloqueante — smoke test con fixture antes de implementar storage |
| Worker rompe | Worker no toca localStorage. Cero exposure. |
| Globals como source-of-truth se desincronizan si un callsite olvida `storage.setX(global)` después de mutar el global | R3 explícita; migración por grupos permite revisar set/get juntos; QA browser de roundtrip captura desincronización |

## Deuda futura

- **Fase 5.5 (state container)**: storage adapter es prereq. Con localStorage
  encapsulado, el state container puede tener hooks `state.subscribe(persist)`
  que invocan los `storage.setX` automáticamente.
- **Cloud sync abstraction**: `storage.setWatched(set)` podría también marcar
  el `_cloudSaveTimer`. Hoy esa coordinación está en cada callsite.
- **Migración de claves**: `_av2 → _av3` ya pasó (sufrido). Con storage
  adapter, futuras migraciones son 1 línea en el adapter + script de
  migración corriendo en bootstrap.
- **Quota handling**: localStorage puede tirar `QuotaExceededError`. Hoy
  los callsites no lo manejan. Storage adapter podría agregar un try/catch
  + toast de error.
