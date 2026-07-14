// ── src/state/festival-context.js ──────────────────────────────────────────────
// FUENTE ÚNICA de "qué estado es POR-FESTIVAL".
//
// Antes, la definición vivía IMPLÍCITA en 4 listas paralelas mantenidas a mano:
// el clear de batch1 (loadFestival), el hydrate de loadState, los campos de
// _doCloudSave y las ramas de _applyCloudRow. Agregar un estado por-festival
// exigía tocar ~9 sitios y olvidar UNO producía sangrado silencioso entre
// festivales (el bug de availability). Esta tabla es la fuente declarativa: los
// consumidores se DERIVAN de ella → agregar estado por-festival = 1 entrada.
//
// Cada entrada:
//   key      — nombre en el roster de state.js (y global bridgeado).
//   empty    — valor fresco al cambiar de festival (clear de batch1). Recibe cfg
//              (availability necesita dayKeys para sembrar {blocks:[]} por día).
//   hydrate  — valor desde storage al entrar al festival (batch2 de loadState).
//              Captura la lógica fina de cada key: normTitle en los Sets, merge de
//              ratings, merge por-día de availability, normalización de venues.
//   storage  — sufijo del par storage.get<X>/set<X> (usado por la fitness function).
//   cloud    — columna en user_festival_state, o null si NO se sincroniza.
//
// [P1.1] deriveClear (batch1) · [P1.2] deriveHydrate (loadState). La nube
// (_doCloudSave/_applyCloudRow) migra en P1.3 vía el campo `cloud`.
// La fitness function (tests/unit/festivalContext.test.js) afirma completitud vs
// el roster + storage → olvidar un sitio pasa a ser fallo de CI.

import { state } from './state.js';
import { storage } from '../storage/storage.js';
import { normTitle } from '../domain/film.js';

export const FESTIVAL_STATE = [
  { key:'watchlist',   empty:()=>new Set(), storage:'Watchlist',   cloud:'watchlist',
    hydrate:()=>new Set([...storage.getWatchlist()].map(normTitle)) },
  { key:'watched',     empty:()=>new Set(), storage:'Watched',     cloud:'watched',
    hydrate:()=>new Set([...storage.getWatched()].map(normTitle)) },
  { key:'prioritized', empty:()=>new Set(), storage:'Prioritized', cloud:'prioritized',
    hydrate:()=>new Set([...storage.getPrioritized()].map(normTitle)) },
  { key:'filmRatings', empty:()=>({}),      storage:'FilmRatings', cloud:'ratings',
    // merge sobre el valor en memoria (tras el clear es {} → equivale a storage).
    hydrate:()=>({...state.get('filmRatings'), ...storage.getFilmRatings()}) },
  { key:'savedAgenda', empty:()=>null,      storage:'SavedAgenda', cloud:'saved_agenda',
    hydrate:()=>{
      let sa=storage.getSavedAgenda();
      if(sa && sa.schedule){
        // Normalizar venues viejos (ej: 'CC Bocagrande' → 'Plaza Bocagrande')
        sa={...sa, schedule: sa.schedule.map(s => s.venue ? {...s, venue: s.venue.replace(/CC Bocagrande/g,'Plaza Bocagrande')} : s)};
      }
      return sa;
    } },
  { key:'availability', empty:(cfg)=>Object.fromEntries(((cfg&&cfg.dayKeys)||[]).map(d=>[d,{blocks:[]}])),
    storage:'Availability', cloud:'availability',
    hydrate:()=>{
      // Merge del storage sobre el seed vacío por-día (las keys del seed SON los
      // dayKeys del festival). Un día sin dato guardado conserva su {blocks:[]}.
      const seed=state.get('availability'), av=storage.getAvailability(), out={...seed};
      Object.keys(seed).forEach(d=>{ if(av[d]) out[d]=av[d]; });
      return out;
    } },
  { key:'lastRemovedSlots',  empty:()=>[], storage:'LastRemovedSlots',  cloud:null,
    hydrate:()=>storage.getLastRemovedSlots() },
  { key:'filmDelays',        empty:()=>({}), storage:'FilmDelays',       cloud:null,
    hydrate:()=>storage.getFilmDelays() },
  { key:'filmDelaysHistory', empty:()=>({}), storage:'FilmDelaysHistory', cloud:null,
    hydrate:()=>storage.getFilmDelaysHistory() },
];

// deriveClear(cfg) — objeto de vacíos por-festival para el batch1 de loadFestival.
// Agregar una entrada a FESTIVAL_STATE la auto-incluye → imposible olvidar el
// reset de un estado nuevo al cambiar de festival (por construcción).
export function deriveClear(cfg){
  const out={};
  for(const e of FESTIVAL_STATE) out[e.key]=e.empty(cfg);
  return out;
}

// deriveHydrate() — objeto hidratado desde el storage del festival activo, para el
// batch2 de loadState. Cada valor se COMPUTA leyendo storage (puro, sin escribir);
// loadState hace el batchUpdate atómico. Lee state.get() del seed donde aplica
// (ratings/availability) — mismo timing que el código manual previo.
export function deriveHydrate(){
  const out={};
  for(const e of FESTIVAL_STATE) out[e.key]=e.hydrate();
  return out;
}
