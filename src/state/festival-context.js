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
//   key     — nombre en el roster de state.js (y global bridgeado).
//   empty   — valor fresco al cambiar de festival (clear de batch1). Recibe cfg
//             (availability necesita dayKeys para sembrar {blocks:[]} por día).
//   storage — sufijo del par storage.get<X>/set<X> (hidratación/persistencia).
//   cloud   — nombre de la columna en user_festival_state, o null si NO se sincroniza.
//
// [P1.1] Hoy se DERIVA el clear de batch1 (deriveClear). El hydrate y la nube
// migran en pasos siguientes (siguen manuales por ahora, pero ya declarados acá).
// La fitness function (tests/unit/festivalContext.test.js) afirma que la tabla
// está completa vs el roster + storage → olvidar un sitio pasa a ser fallo de CI.

export const FESTIVAL_STATE = [
  { key:'watchlist',         empty:()=>new Set(), storage:'Watchlist',         cloud:'watchlist'    },
  { key:'watched',           empty:()=>new Set(), storage:'Watched',           cloud:'watched'      },
  { key:'prioritized',       empty:()=>new Set(), storage:'Prioritized',       cloud:'prioritized'  },
  { key:'filmRatings',       empty:()=>({}),      storage:'FilmRatings',       cloud:'ratings'      },
  { key:'savedAgenda',       empty:()=>null,      storage:'SavedAgenda',       cloud:'saved_agenda' },
  { key:'availability',      empty:(cfg)=>Object.fromEntries(((cfg&&cfg.dayKeys)||[]).map(d=>[d,{blocks:[]}])),
                             storage:'Availability',      cloud:'availability'  },
  { key:'lastRemovedSlots',  empty:()=>[],        storage:'LastRemovedSlots',  cloud:null           },
  { key:'filmDelays',        empty:()=>({}),      storage:'FilmDelays',        cloud:null           },
  { key:'filmDelaysHistory', empty:()=>({}),      storage:'FilmDelaysHistory', cloud:null           },
];

// deriveClear(cfg) — objeto de vacíos por-festival para el batch1 de loadFestival.
// Agregar una entrada a FESTIVAL_STATE la auto-incluye en el clear → imposible
// olvidar el reset de un estado nuevo al cambiar de festival (por construcción).
export function deriveClear(cfg){
  const out={};
  for(const e of FESTIVAL_STATE) out[e.key]=e.empty(cfg);
  return out;
}
