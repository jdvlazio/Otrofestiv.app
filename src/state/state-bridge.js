// ── src/state/state-bridge.js ────────────────────────────────────────────────
// p8 Step 8a — STATE BRIDGE reubicado desde main.js (Wave 8: relocate).
//
// D-INFRA-4: el mirror fue ELIMINADO (ver src/state/state.js). El container
// `state` posee _data; este bridge expone los 19 globals del roster como
// propiedades de globalThis respaldadas por state.get/set. Una dirección:
//   read  `watchlist.has(x)`  → globalThis.watchlist getter → state.get('watchlist')
//   write `watchlist = nuevo` → globalThis.watchlist setter → state.set('watchlist', …)
//                               → dispara subscribers + render pipeline (7d)
//
// Importado (side-effect, sin bindings) TEMPRANO en main.js — el install corre
// en la fase de import, antes del body de main.js. DEBE preceder a la primera
// asignación bare del roster: en módulo ESM (strict), `X = v` sin declaración
// requiere que globalThis.X exista.
//
// validate.py [state-mirror]: verifica que estos 19 keys estén bridged (escanea
// este archivo) y que ningún roster key se redeclare en main.js (anti-shadowing).

import { state } from './state.js';

// ── STATE BRIDGE START (p8 Step 2) ───────────────────────────────────
const _BRIDGE_KEYS = [
  'watchlist', 'watched', 'prioritized', 'filmRatings', 'filmDelays',
  'filmDelaysHistory', 'savedAgenda', 'availability', 'lastRemovedSlots',
  '_lang', '_simTime', 'FILMS', 'FESTIVAL_DATES', 'FESTIVAL_END', 'PRIO_LIMIT',
  'TZ_OFFSET', 'FESTIVAL_TRANSPORT', '_activeFestId', 'FESTIVAL_STORAGE_KEY',
];
_BRIDGE_KEYS.forEach(k => Object.defineProperty(globalThis, k, {
  get: () => state.get(k),
  set: v => state.set(k, v),
  configurable: true,
}));
// ── STATE BRIDGE END (p8 Step 2) ─────────────────────────────────────
