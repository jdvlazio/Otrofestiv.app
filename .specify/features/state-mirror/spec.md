# Spec — State Container Mirror (Fase 5.5)

## Problema

Después de Fase 5 (storage adapter), la I/O persistente está encapsulada pero
los ~19 globals mutables del runtime siguen dispersos. Cada escritura es un
sitio inline con riesgo de:

- **Drift de contratos:** un global puede mutarse sin actualizar storage
  (`saveWL()` se olvida) o viceversa
- **Mutación oculta:** `watchlist.add(t)` y `savedAgenda.schedule.push(x)`
  modifican el objeto sin que ningún listener pueda enterarse
- **Imposibilidad de Views puras:** Fase 6 necesita `(state, deps) → HTML`,
  pero no hay un `state` para pasar — hay 19 globals dispersos
- **Imposibilidad de subscribe → render loop** en Fase 7
- **Riesgo de inconsistencia en `loadFestival`:** swap secuencial de ~15
  globals; si un subscriber existe en el futuro, vería estado parcial

## Causa raíz

§16.5 define Fase 5 como **storage + state container juntos**. Lo mergeado
en Fase 5 fue solo el storage adapter. La pieza faltante (state container)
sobre ~200+ readers en un solo PR excede el blast radius que §16.8
recomienda abortar.

## Solución — Fase 5.5

Introducir un namespace `state` (const object) en index.html con API
`get`/`set`/`update`/`batchUpdate`/`subscribe`/`snapshot` que **espeja** los
globals existentes: toda escritura va a `state.set()`, que actualiza el
state interno Y el global mirror. Las **lecturas no se tocan** — siguen
yendo al global. La invariante `state.get(k) === globalMirror(k)` se
preserva por construcción.

**Cero cambios de comportamiento. Cero cambios en readers. Cero cambios en
Model contracts. Solo se canalizan escrituras.**

La migración de readers a leer de state se difiere a Fase 5.6 cuando ya
tengamos confianza en la invariante.

## State items cubiertos (19 keys)

### Festival batch (8) — swapped por `loadFestival`
| Key | Tipo | Origen |
|---|---|---|
| `_activeFestId` | string | `loadFestival(id)` |
| `FILMS` | Array | `cfg.films` |
| `FESTIVAL_DATES` | object | `cfg.festivalDates` |
| `FESTIVAL_END` | Date | `new Date(cfg.festivalEndStr)` |
| `FESTIVAL_STORAGE_KEY` | string | `cfg.storageKey` |
| `PRIO_LIMIT` | number | `cfg.prioLimit \|\| _computedPrioLimit` |
| `TZ_OFFSET` | string | `cfg.timezoneOffset` |
| `FESTIVAL_TRANSPORT` | string | `cfg.transport` |

### User-state (9) — storage-backed
| Key | Tipo | Storage key |
|---|---|---|
| `watchlist` | Set | `{festKey}wl` |
| `watched` | Set | `{festKey}watched` |
| `prioritized` | Set | `{festKey}prio` |
| `filmRatings` | object | `{festKey}ratings` |
| `filmDelays` | object | `{festKey}delays` (sin `_hist`) |
| `filmDelaysHistory` | object | NUEVO key `{festKey}delays_hist` |
| `savedAgenda` | object\|null | `{festKey}saved` |
| `availability` | object | `{festKey}av3` |
| `lastRemovedSlots` | Array | `{festKey}lastrm` |

### Configuración (2)
| Key | Tipo | Persistencia |
|---|---|---|
| `_lang` | string | `otrofestiv_lang` |
| `_simTime` | string\|null | in-memory only |

## API del namespace `state`

```js
state.get(key)               // read del state interno (sync)
state.set(key, value)        // write → state + mirror al global + notify subs
state.update(key, fn)        // azúcar: state.set(k, fn(state.get(k)))
state.batchUpdate(updates)   // atómico: aplica todo, notifica una vez por key
state.subscribe(key, cb)     // returns unsubscribe fn; cb(value, key) sync
state.snapshot()             // shallow copy del state interno (para tests/worker)
state.init(festData)         // bootstrap: hidrata desde storage + cfg activos
```

**Garantía de atomicidad de `batchUpdate`** (formal — ver `plan.md` §4):
1. Todas las claves se aplican a state + mirror **antes** de notificar
2. Cada clave dirty notifica exactamente una vez
3. Subscribers ven estado post-batch completo, nunca parcial
4. Reentrada de `set/update/batchUpdate` desde subscriber soportada
5. Excepción durante el batch → rollback completo + re-throw

## Invariante (enforced por validate.py)

```
∀k ∈ STATE_KEYS:  state.get(k) === mirror(k)
```

Donde `mirror(k)` es el global `let` correspondiente. La invariante se
preserva por construcción: toda escritura pasa por `state.set` que actualiza
ambos en orden estricto (state interno primero, mirror después, notify al
final).

Validate.py detecta cualquier `let X = ...` reasignación a un global state
fuera del bloque `state` namespace.

## Lo que NO entra en Fase 5.5

| Out-of-scope | Razón | Fase futura |
|---|---|---|
| Migrar **readers** a `state.get()` | Bulk del trabajo (~200+ sitios). 5.5 sólo prepara la abstracción | 5.6 |
| Convertir Model functions a recibir state por parámetro | Requiere readers migrados primero | 6 |
| Conectar `subscribe()` al render loop | Views aún no son puras | 6/7 |
| UI state (`activeDay`, `programaSubMode`, `programaViewMode`, `interesesViewMode`, `miPlanViewMode`, `programaChip`, `cartelaMode`, `activeVenue`, `selectedIdx`, `activeMNav`, `miPlanViewStart`, `activeMiPlanDay`, `_avSheetDay`, etc.) | Ephemeral UI; no requiere persistencia ni atomicidad | 6/7 |
| Worker boundary change | Worker recibe slice serializado; no toca state container | 8 |
| Eliminar globals mirror | Mirror es lo que da backward compat sin tocar readers | 5.6 (deprecate), 8 (elimina) |
| Move state to file | Single-file invariant hasta Fase 8 | 8 |

## Decisiones de diseño incorporadas

1. **`filmDelays._hist` separado como key independiente `filmDelaysHistory`**
   en state + nuevo storage key `{festKey}delays_hist`. Razón: anidamiento
   profundo dentro de `filmDelays` rompía pureza; separar simplifica
   immutable updates de 4 líneas a 1
2. **UI state fuera de scope.** Sólo persistent + festival-swap state entra
3. **`PRIO_LIMIT` y `FESTIVAL_TRANSPORT` IN.** Aunque son swap-once,
   incluirlos en batchUpdate mantiene atomicidad del swap completo
4. **Validate whitelist:** declaraciones iniciales (`let X = []` en el
   roster fijo), reasignaciones dentro del bloque `state` namespace, y el
   template literal del worker boundary (líneas ~8441-8443)

## Definition of Done

- [ ] Namespace `state` implementado en index.html con marcadores START/END
- [ ] 19 keys del roster espejadas con setters mirror
- [ ] Todas las escrituras inline (`global = v`, `set.add(x)`, `obj[k]=v`,
      `arr.push(x)`, `arr.length=N`) migradas a `state.set/update`
- [ ] `loadFestival` usa `state.batchUpdate` para el swap atómico
- [ ] Nuevo key `filmDelaysHistory` con storage adapter + migración del
      `_hist` anidado (con backward-compat read del `_hist` viejo)
- [ ] Tests unitarios cubren atomicidad de `batchUpdate`, rollback,
      reentrada, subscribe/unsubscribe
- [ ] Validate.py check `[state-mirror]` activo (23/23)
- [ ] QA browser: watchlist toggle, festival switch, lang change, sim time,
      undo de filmDelays — todo funciona igual que antes
- [ ] `node --test tests/unit/*.test.js` 100% pass
- [ ] Diff review: cero cambios de comportamiento, sólo canalizar escrituras
