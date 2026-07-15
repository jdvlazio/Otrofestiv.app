// ── src/state/festival-context.js ──────────────────────────────────────────────
// FUENTE ÚNICA de "qué estado es POR-FESTIVAL".
//
// Antes, la definición vivía IMPLÍCITA en 4 listas paralelas mantenidas a mano:
// el clear de batch1 (loadFestival), el hydrate de loadState, los campos de
// _doCloudSave y las ramas de _applyCloudRow. Agregar un estado por-festival
// exigía tocar ~9 sitios y olvidar UNO producía sangrado silencioso entre
// festivales (el bug de availability). Esta tabla es la fuente declarativa: los
// consumidores se DERIVAN de ella → agregar estado por-festival = 1 entrada
// (+ 1 columna Supabase si se sincroniza).
//
// Cada entrada:
//   key       — nombre en el roster de state.js (y global bridgeado).
//   empty     — valor fresco al cambiar de festival (clear de batch1). Recibe cfg.
//   hydrate   — valor desde storage al entrar (batch2 de loadState). Lógica fina.
//   storage   — sufijo del par storage.get<X>/set<X> (fitness function).
//   cloud     — columna en user_festival_state, o null si NO se sincroniza.
//   toCloud   — state → valor de la fila (solo si cloud). Set→array, obj→identidad.
//   fromCloud — (dbVal, whole, current) → valor a aplicar, o undefined para SALTAR.
//               whole=true (Realtime, autoritativo) vs false (boot/sign-in, solo
//               campos no-vacíos, con merge para ratings/availability).
//
// Consumidores derivados: deriveClear (P1.1) · deriveHydrate (P1.2) ·
// deriveCloudSave + deriveCloudApply (P1.3). La fitness function
// (tests/unit/festivalContext.test.js) afirma completitud vs roster + storage.

import { state } from './state.js';
import { storage } from '../storage/storage.js';
import { normTitle } from '../domain/film.js';

// Helpers de (de)serialización de nube compartidos entre entradas.
const _setToCloud   = (v)=>[...v];
const _setFromCloud = (d,whole)=> (whole||d?.length) ? new Set(d||[]) : undefined;
const _id           = (v)=>v; // objetos: identidad en ambas direcciones
// Merge parcial de availability: parte del actual y pisa solo los días que trae la
// nube (las keys del actual SON los dayKeys del festival → equivale a iterar DAY_KEYS).
const _mergeAvail   = (cur,d)=>{ const o={...cur}; Object.keys(cur).forEach(k=>{ if(d[k]) o[k]=d[k]; }); return o; };

export const FESTIVAL_STATE = [
  { key:'watchlist',   empty:()=>new Set(), storage:'Watchlist',   cloud:'watchlist',
    hydrate:()=>new Set([...storage.getWatchlist()].map(normTitle)),
    toCloud:_setToCloud, fromCloud:_setFromCloud },
  { key:'watched',     empty:()=>new Set(), storage:'Watched',     cloud:'watched',
    hydrate:()=>new Set([...storage.getWatched()].map(normTitle)),
    toCloud:_setToCloud, fromCloud:_setFromCloud },
  { key:'prioritized', empty:()=>new Set(), storage:'Prioritized', cloud:'prioritized',
    hydrate:()=>new Set([...storage.getPrioritized()].map(normTitle)),
    toCloud:_setToCloud, fromCloud:_setFromCloud },
  { key:'filmRatings', empty:()=>({}),      storage:'FilmRatings', cloud:'ratings',
    hydrate:()=>({...state.get('filmRatings'), ...storage.getFilmRatings()}),
    toCloud:_id,
    // wholesale reemplaza; parcial MERGEA sobre lo actual.
    fromCloud:(d,whole,cur)=> (whole||(d&&Object.keys(d).length)) ? (whole?(d||{}):{...cur,...d}) : undefined },
  { key:'savedAgenda', empty:()=>null,      storage:'SavedAgenda', cloud:'saved_agenda',
    hydrate:()=>{
      let sa=storage.getSavedAgenda();
      if(sa && sa.schedule){
        // Normalizar venues viejos (ej: 'CC Bocagrande' → 'Plaza Bocagrande')
        sa={...sa, schedule: sa.schedule.map(s => s.venue ? {...s, venue: s.venue.replace(/CC Bocagrande/g,'Plaza Bocagrande')} : s)};
      }
      return sa;
    },
    toCloud:_id,
    fromCloud:(d,whole)=> (whole||d) ? (d||null) : undefined },
  { key:'availability', empty:(cfg)=>Object.fromEntries(((cfg&&cfg.dayKeys)||[]).map(d=>[d,{blocks:[]}])),
    storage:'Availability', cloud:'availability',
    hydrate:()=>{
      // Merge del storage sobre el seed vacío por-día (las keys del seed SON los
      // dayKeys del festival). Un día sin dato guardado conserva su {blocks:[]}.
      const seed=state.get('availability'), av=storage.getAvailability(), out={...seed};
      Object.keys(seed).forEach(d=>{ if(av[d]) out[d]=av[d]; });
      return out;
    },
    toCloud:_id,
    // wholesale reemplaza; parcial mergea por-día sobre lo actual.
    fromCloud:(d,whole,cur)=> (whole||(d&&Object.keys(d).length)) ? (whole?(d||{}):_mergeAvail(cur,d)) : undefined },
  { key:'lastRemovedSlots',  empty:()=>[], storage:'LastRemovedSlots',  cloud:null,
    hydrate:()=>storage.getLastRemovedSlots() },
  { key:'filmDelays',        empty:()=>({}), storage:'FilmDelays',       cloud:null,
    hydrate:()=>storage.getFilmDelays() },
  { key:'filmDelaysHistory', empty:()=>({}), storage:'FilmDelaysHistory', cloud:null,
    hydrate:()=>storage.getFilmDelaysHistory() },
];

// deriveClear(cfg) — vacíos por-festival para el batch1 de loadFestival. Agregar
// una entrada la auto-incluye → imposible olvidar el reset (por construcción).
export function deriveClear(cfg){
  const out={};
  for(const e of FESTIVAL_STATE) out[e.key]=e.empty(cfg);
  return out;
}

// deriveHydrate() — objeto hidratado desde el storage del festival activo (batch2
// de loadState). Cada valor se computa leyendo storage (puro, sin escribir).
export function deriveHydrate(){
  const out={};
  for(const e of FESTIVAL_STATE) out[e.key]=e.hydrate();
  return out;
}

// deriveCloudSave() — los campos de la fila user_festival_state desde el state
// ACTIVO (solo entradas con cloud). Set→array vía toCloud. Puro; el caller le
// suma user_id/festival_id/updated_at.
export function deriveCloudSave(){
  const row={};
  for(const e of FESTIVAL_STATE) if(e.cloud) row[e.cloud]=e.toCloud(state.get(e.key));
  return row;
}

// deriveCloudMerge(local, remote, dirtyKeys) — la fila A SUBIR que preserva escrituras
// CONCURRENTES a campos distintos. Sin timestamps por-campo en Supabase, un upsert de
// la fila entera es last-write-wins: si el iPhone bloquea availability y el iPad agrega
// a watchlist casi a la vez, el segundo upsert pisaba el campo del primero con su copia
// vieja (edición perdida). Aquí, antes de subir se relee la fila remota y se mergea POR
// CAMPO: un campo que este dispositivo editó (su state key está en dirtyKeys) sube el
// valor LOCAL (la intención del usuario); un campo NO tocado localmente conserva el valor
// REMOTO (no lo pisa con una copia vieja → la edición del otro dispositivo sobrevive).
//   remote=null (fila inexistente, o el fetch de merge falló) → todo local (degrada al
//   comportamiento previo: nunca se pierde la edición local por un fallo de red).
//   Merge a nivel de CAMPO, no de elemento: no resucita ítems borrados (a diferencia de
//   una unión de Sets) — un borrado local marca el campo dirty → sube el Set local ya
//   sin el ítem. Residual conocido: dos dispositivos editando EL MISMO campo en la misma
//   ventana de debounce siguen siendo last-write-wins (necesitaría timestamps por-campo).
//   Puro y testeable sin Supabase (tests/unit/festivalContext.test.js).
export function deriveCloudMerge(local, remote, dirtyKeys){
  if(!remote) return local;
  const out={};
  for(const e of FESTIVAL_STATE){
    if(!e.cloud) continue;
    const col=e.cloud, r=remote[col];
    out[col] = dirtyKeys.has(e.key) ? local[col]
             : (r!==undefined && r!==null) ? r : local[col];
  }
  return out;
}

// deriveCloudApply(data, whole) — el objeto de state.batchUpdate al aplicar una
// fila de la nube. whole=true (Realtime, autoritativo) vs false (boot/sign-in:
// solo campos no-vacíos, con merge para ratings/availability). Puro (lee state.get
// para los merges parciales; no escribe — el caller batchUpdatea + persiste).
export function deriveCloudApply(data, whole){
  const u={};
  for(const e of FESTIVAL_STATE){
    if(!e.cloud) continue;
    const v=e.fromCloud(data[e.cloud], whole, state.get(e.key));
    if(v!==undefined) u[e.key]=v;
  }
  return u;
}
