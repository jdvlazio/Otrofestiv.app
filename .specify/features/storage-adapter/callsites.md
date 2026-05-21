# Inventario de callsites — Storage Adapter Fase 5

> Mapa de trabajo para la migración (pasos 8–11). Cada callsite con su línea
> exacta y la transformación esperada. Las líneas ~4674–4709 son la
> implementación del propio adapter (NO migrar).

## Resumen

| Grupo | Items | Reads | Writes | Total callsites | Task |
|---|---|---:|---:|---:|---|
| A. Set-based | watchlist, watched, prioritized | 3 | 3 | 6 | Paso 8 |
| B. Object items | filmRatings, savedAgenda, availability, filmDelays, viewmodes | 5 | 5 + 2 extras | 12 | Paso 9 |
| C. Array items | lastRemovedSlots | 1 | 1 | 2 | Paso 10 |
| D. Global keys | otrofestiv_festival, otrofestiv_lang, otrofestiv_build | 6 | 4 | 10 | Paso 11 |
| **TOTAL a migrar** | | **15** | **15** | **30** | |
| **Excluido del scope** | | | | 10 | (no migrate) |

## Grupo A — Set-based items (paso 8)

### watchlist (`{festKey}wl`)

**Read** (1 callsite):
- Línea 5066:
  ```js
  const wl=localStorage.getItem(`${FESTIVAL_STORAGE_KEY}wl`); if(wl) watchlist=new Set(JSON.parse(wl).map(normTitle));
  ```
  → `watchlist = new Set([...storage.getWatchlist()].map(normTitle));`

**Write** (1 callsite):
- Línea 5087:
  ```js
  function saveWL(){try{localStorage.setItem(`${FESTIVAL_STORAGE_KEY}wl`,JSON.stringify([...watchlist]));}catch(e){}_cloudSave();}
  ```
  → `function saveWL(){ storage.setWatchlist(watchlist); _cloudSave(); }`

### watched (`{festKey}watched`)

**Read** (1): línea 5067 — patrón idéntico a watchlist.
**Write** (1): línea 5088 — `function saveWatched()`.

### prioritized (`{festKey}prio`)

**Read** (1): línea 5077 — patrón idéntico a watchlist.
**Write** (1): línea 5143 — `function savePrio()`.

## Grupo B — Object items (paso 9)

### filmRatings (`{festKey}ratings`)

**Read** (1):
- Línea 5068:
  ```js
  const _rt=localStorage.getItem(`${FESTIVAL_STORAGE_KEY}ratings`); if(_rt) try{Object.assign(filmRatings,JSON.parse(_rt));}catch(e){console.warn('[loadState] ratings parse failed',e);}
  ```
  → `Object.assign(filmRatings, storage.getFilmRatings());` — MERGE semantics preservado.

**Write** (2 callsites — uno es duplicado inline):
- Línea 5091: dentro de `function saveRatings()`:
  ```js
  try{localStorage.setItem(`${FESTIVAL_STORAGE_KEY}ratings`,JSON.stringify(filmRatings));}catch(e){}_cloudSave();
  ```
  → `storage.setFilmRatings(filmRatings); _cloudSave();`
- Línea 8163: write inline duplicado (fuera de saveRatings):
  ```js
  localStorage.setItem(`${FESTIVAL_STORAGE_KEY}ratings`,JSON.stringify(filmRatings));
  ```
  → `storage.setFilmRatings(filmRatings);`

### savedAgenda (`{festKey}saved`)

**Read** (1): línea 5070 — `if(sa) savedAgenda=JSON.parse(sa);` → `savedAgenda = storage.getSavedAgenda();`
**Write** (1): línea 5094 — `function saveSavedAgenda()`.

### availability (`{festKey}av3`)

**Read** (1):
- Línea 5069:
  ```js
  const av=localStorage.getItem(`${FESTIVAL_STORAGE_KEY}av3`); if(av){const p=JSON.parse(av);DAY_KEYS.forEach(d=>{if(p[d]) availability[d]=p[d];});}
  ```
  **⚠ Cuidado**: merge per-day, NO reasign del objeto entero.
  → `const _p = storage.getAvailability(); DAY_KEYS.forEach(d=>{ if(_p[d]) availability[d]=_p[d]; });`

**Write** (1): línea 5093 — `function saveAV()`.

### filmDelays (`{festKey}delays`)

**Read** (1): línea 5083 → `filmDelays = storage.getFilmDelays();` o `Object.assign(filmDelays, storage.getFilmDelays())` según semantics deseado.
**Write** (1): línea 5145 — `function saveDelays()`.

### viewmodes (`{festKey}viewmodes`)

**Read** (1):
- Línea 5084 — lee y aplica a los 2 globals `miPlanViewMode` e `interesesViewMode`:
  ```js
  const _vm=localStorage.getItem(`${FESTIVAL_STORAGE_KEY}viewmodes`);if(_vm){try{const _v=JSON.parse(_vm);if(_v.miPlan)miPlanViewMode=_v.miPlan;if(_v.intereses)interesesViewMode=_v.intereses;}catch(e){console.warn('[loadState] viewmodes parse failed',e);}}
  ```
  → `const _v = storage.getViewmodes(); if(_v.miPlan) miPlanViewMode=_v.miPlan; if(_v.intereses) interesesViewMode=_v.intereses;`

**Write** (2 callsites — patrón read-modify-write combo):
- Línea 9637 (saveMiPlanViewmode):
  ```js
  try{const _v=JSON.parse(localStorage.getItem(`${FESTIVAL_STORAGE_KEY}viewmodes`)||'{}');_v.miPlan=mode;localStorage.setItem(`${FESTIVAL_STORAGE_KEY}viewmodes`,JSON.stringify(_v));}catch(e){}
  ```
  → `const _v = storage.getViewmodes(); _v.miPlan = mode; storage.setViewmodes(_v);`
- Línea 9688 (saveInteresesViewmode): patrón idéntico con `_v.intereses=mode`.

## Grupo C — Array items (paso 10)

### lastRemovedSlots (`{festKey}lastslot`)

**Read** (1):
- Línea 5082 — defensiva por si valor no es array:
  ```js
  const rs=localStorage.getItem(`${FESTIVAL_STORAGE_KEY}lastslot`);if(rs){try{const p=JSON.parse(rs);lastRemovedSlots=Array.isArray(p)?p:(p?[p]:[]);}catch(e){console.warn('[loadState] lastslot parse failed',e);}}
  ```
  → `lastRemovedSlots = storage.getLastRemovedSlots();` — el adapter ya hace la normalización defensive.

**Write** (1): línea 5144 — `function saveLastSlot()`.

## Grupo D — Global keys (paso 11)

### otrofestiv_festival

**Read** (3 callsites):
- Línea 4168 — `const _storedFestId=localStorage.getItem('otrofestiv_festival');` ⚠ **BOOTSTRAP — ver nota abajo**
- Línea 4658 — `let FESTIVAL_STORAGE_KEY=(localStorage.getItem('otrofestiv_festival')||_DEFAULT_FEST_ID)+'_';` ⚠ **BOOTSTRAP**
- Línea 4724 — `const _splashSeen=localStorage.getItem('otrofestiv_festival');` (después del storage block, OK)

**Write** (1): línea 10778 — `localStorage.setItem('otrofestiv_festival',id);` → `storage.setActiveFestId(id);`

### otrofestiv_lang

**Read** (2): líneas 2456, 3433.
**Write** (1): línea 3454.

### otrofestiv_build

**Read** (1): línea 4721 — via `_vk='otrofestiv_build'` variable.
**Write** (2): líneas 4727, 4732 — mismo IIFE de cache reset.

## ⚠ Constraint estructural — bootstrap reads

Las líneas **4168 y 4658** leen `otrofestiv_festival` ANTES del storage block
(que está actualmente en líneas 4659–4710). Estas son lecturas de bootstrap
necesarias para inicializar `_activeFestId` y `FESTIVAL_STORAGE_KEY`.

**Acción requerida en paso 11**: **mover el storage block** desde su ubicación
actual (línea 4659) hacia ANTES de la línea 4162 (después de `FESTIVAL_CONFIG`
const, antes del cálculo de `_DEFAULT_FEST_ID` / `_storedFestId`).

Por qué es seguro:
- Los métodos del storage adapter cierran sobre `localStorage` (built-in,
  siempre disponible) y `FESTIVAL_STORAGE_KEY` (late binding via closure).
- Los user-state methods NO se llaman hasta `loadState()` en línea 5066+,
  bien después de la inicialización de `FESTIVAL_STORAGE_KEY` (línea 4658).
- Los global-key methods (getActiveFestId, getLang, getBuild) NO dependen de
  `FESTIVAL_STORAGE_KEY` — pueden usarse inmediatamente tras la declaración.

## Excluido del scope (NO migrate)

| Callsite | Línea(s) | Razón |
|---|---:|---|
| `otrofestiv_hint_cambiar` | 5045, 6774, 6775 | Onboarding flag — scope separado |
| `otrofestiv_display_name` | 7434, 7442 | Supabase user feature — scope separado |
| TMDB poster cache (`cacheKey`) | 10509, 10519 | Cache dinámico con keys derivados |
| Otra caché (`cacheKey`) | 11545, 11562 | Cache dinámico (TBD origen) |
| `_BUILD_KEY` (SW update) | 11098, 11104 | SW update logic — scope separado |

**Total excluido: 10 callsites.** El check `[storage-encapsulation]` en
validate.py debe whitelisteár estas líneas o sus patrones específicos
(por ejemplo: keys que NO empiezan con `otrofestiv_` ni `${FESTIVAL_STORAGE_KEY}`).

## Total para migración

- **30 callsites a migrar** (15 reads + 15 writes) distribuidos en 4 grupos
- **10 callsites excluidos** del scope, documentados arriba
- **1 cambio estructural**: mover storage block antes de línea 4162 (parte del paso 11)
