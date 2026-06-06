# Spec — Storage Adapter (Fase 5)

## Problema

La I/O de localStorage está dispersa por ~30 callsites en index.html, mezclada
con la lógica que consume el state. Cada user-state global tiene su propia
ceremonia de (de)serialización (Sets ↔ arrays via JSON) repetida en cada read
y cada write. Resultado:

- Sin un punto único que documente "qué state persiste"
- Cualquier cambio de formato (e.g., bumpear `_av2` → `_av3`) implica tocar
  N callsites con riesgo de drift
- Futuras evoluciones (state container Fase 5.5, multi-festival isolation,
  cloud sync hooks) requieren tocar todos los consumers

## Causa raíz

La app creció orgánicamente. localStorage era trivial de usar inline.
Mientras solo había 1–2 pedazos de state persistido, la abstracción no se
justificaba. Hoy tenemos 9 user-state items × 2 ops (get/set) × ~1.5 callsites
promedio ≈ 27 sitios + 3 global keys.

## Solución — Fase 5

Crear un namespace `storage` (const object) en index.html con métodos
`getXxx`/`setXxx` para cada user-state item y cada global key. Migrar todos
los callsites de localStorage al adapter. **Cero cambios de firma en Model
functions. Cero cambios en globals. Cero cambios de comportamiento — solo
encapsulación.**

### State items cubiertos (9 user-state + 3 global)

| Item | Storage key | Tipo | (De)serialización |
|---|---|---|---|
| `watchlist` | `{festKey}wl` | Set<string> | Array ↔ Set |
| `watched` | `{festKey}watched` | Set<string> | Array ↔ Set |
| `prioritized` | `{festKey}prio` | Set<string> | Array ↔ Set |
| `filmRatings` | `{festKey}ratings` | object | identity |
| `savedAgenda` | `{festKey}saved` | object\|null | identity |
| `availability` | `{festKey}av3` | object | identity |
| `lastRemovedSlots` | `{festKey}lastslot` | array | identity |
| `filmDelays` | `{festKey}delays` | object | identity |
| viewmodes (miPlan + intereses) | `{festKey}viewmodes` | object | identity |

| Global key (NO festival prefix) | Storage key | Tipo |
|---|---|---|
| Active festival ID | `otrofestiv_festival` | string |
| Language | `otrofestiv_lang` | string |
| Build version | `otrofestiv_build` | string |

**Nota de scope** (confirmado en paso 5 al diseñar):
- `_dismissedNotices` (`let` en línea 9831) es in-memory only — NO se persiste a localStorage en el código actual. Excluido del adapter (no necesita encapsulación).
- `viewmodes` (`{miPlan, intereses}`) sí está persistido (`{festKey}viewmodes`, líneas 5030, 9583, 9634). Incluido en lugar de `_dismissedNotices`.

Otras claves de localStorage que **NO** son parte del scope (excluidas deliberadamente):
- `otrofestiv_hint_cambiar` — flag de onboarding one-shot
- `otrofestiv_display_name` — feature Supabase, scope separado
- TMDB poster cache (`orf_poster_v1_*`) — caches dinámicos, no user state
- Build version cache (manejado por SW update logic, scope separado)

### Diseño del namespace

```js
const storage = {
  getWatchlist: () => /* Set */,
  setWatchlist: (set) => /* persist */,
  getWatched: () => /* Set */,
  setWatched: (set) => /* persist */,
  // ... 18 métodos para los 9 user-state items
  getActiveFestId: () => /* string */,
  setActiveFestId: (id) => /* persist */,
  getLang: () => /* string */,
  setLang: (lang) => /* persist */,
  getBuild: () => /* string */,
  setBuild: (b) => /* persist */,
};
```

Métodos cierran sobre `localStorage` y `FESTIVAL_STORAGE_KEY` — testeable
inyectando ambos como globals vía el loader.

### Tests

Para que el loader extraiga `const storage = {...}` necesita una extensión —
nueva función `extractObject(source, name)` con brace-walking similar a
`extractFunction`. Cero impacto en tests existentes.

Tests de storage usan un mock `localStorage` (Map-backed) inyectado:
- Empty reads retornan default (empty Set / `null` / empty object)
- Roundtrip: `setX(v); assert(getX() === v)` por cada item
- Festival-prefixed keys usan `FESTIVAL_STORAGE_KEY`; global keys NO

~20 casos.

## Criterios de aceptación

- [ ] `storage` namespace definido con 24 métodos (9 user-state × 2 + 3 global × 2)
- [ ] Los ~30 callsites de `localStorage.getItem`/`setItem` migrados al adapter
- [ ] `validate.py` check nuevo: cero `localStorage\.(getItem|setItem)` fuera del bloque del storage adapter
- [ ] `tests/lib/load-domain.js` soporta `opts.objects: string[]`
- [ ] `tests/unit/storage.test.js` — ~20 casos
- [ ] 104 tests totales pasando (84 previos + 20 nuevos)
- [ ] `python3 validate.py` 22/22 (21 existentes + 1 nuevo)
- [ ] QA browser: watchlist, watched, savedAgenda, availability persisten post-reload
- [ ] Commit atómico

## Fuera de alcance

- State container con `update()`/`subscribe()` (Fase 5.5)
- Cloud save (Supabase) — sigue funcionando porque escribe vía localStorage
- Cambio de formato de claves o estructura del JSON guardado
- Migración de globals festival-scoped (FILMS, FESTIVAL_DATES, etc.) — siguen en `loadFestival`
- Worker — no usa localStorage (recibe state vía `postMessage`)
- Refactor del `_cloudSaveTimer` mechanism
