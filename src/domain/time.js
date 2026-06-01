// ── src/domain/time.js — Fase 8 Step 5 (CABLEADO) ───────────────────────────
//
// ESTADO: importado por src/main.js (Step 5). Funciones puras de tiempo/fecha.
//
// DEPS:
//   - config: DEFAULT_DURATION_MIN (parseDur) — import directo.
//   - festival-state vía STATE BRIDGE (bare-global → state.get): TZ_OFFSET
//     (_festDate), _simTime (simNow), FESTIVAL_DATES + FILMS (dayFullyPassed),
//     FESTIVAL_END (festivalEnded).
//
// WORKER: las sched pure fns tienen COPIAS en el template del calc worker (Blob
//   clásico). El worker las consume vía eval(name).toString() — su source es
//   portable. Las copias worker-local (FESTIVAL_BUFFER, etc.) se mantienen en
//   main.js; [worker-overlap] valida.
import { DEFAULT_DURATION_MIN } from "../config.js";
export function toMin(t){
  if(!t) return 0;
  const isPM=/ PM$/i.test(t), isAM=/ AM$/i.test(t);
  const clean=t.replace(/ [AP]M$/i,'').trim();
  const[h,m]=(clean+':0').split(':').map(Number);
  if(isNaN(h)||isNaN(m)) return 0;
  if(isPM||isAM){
    // 12h format: 12 AM=0, 12 PM=720, 1 PM=780
    const h24=isPM?(h===12?12:h+12):(h===12?0:h);
    return h24*60+m;
  }
  return h*60+m; // 24h format
}

export function parseDur(d){const s=d!=null?String(d):'';const m=s&&s.replace('~','').match(/(\d+)/);return m?parseInt(m[1]):DEFAULT_DURATION_MIN;}

export function minToStr(m){
  const h=Math.floor(((m%1440)+1440)%1440/60),mn=((m%1440)+1440)%1440%60;
  return`${String(h).padStart(2,'0')}:${String(mn).padStart(2,'0')}`;
}

export function _festDate(dateStr,time){
  // Normaliza AM/PM→24h: Tribeca trae "8:00 PM" y la concatenación directa daría
  // Invalid Date (rompía screeningPassed/dayFullyPassed silenciosamente). Punto
  // único — cubre todos los callers; 24h y los que ya pre-convierten (share/
  // persistence) pasan sin cambio (el regex no matchea "20:00").
  const t24=/[AP]M/i.test(time)?minToStr(toMin(time)):time;
  return new Date(dateStr+'T'+t24+':00'+TZ_OFFSET);
}

export function simNow(){return _simTime?new Date(_simTime):new Date();}

export function simTodayStr(){
  // Usa fecha LOCAL (no UTC) para consistencia con getHours()/getMinutes()
  // toISOString() devuelve UTC — en Colombia (UTC-5) esto da el día siguiente
  // después de las 7 PM, causando que la línea "ahora" aparezca en el día incorrecto
  const d=simNow();
  return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');
}

export function dayFullyPassed(day){
  const dateStr=FESTIVAL_DATES[day];
  if(!dateStr) return false;
  // Day passed if last function of that day has passed
  const dayFilms=FILMS.filter(f=>f.day===day);
  if(!dayFilms.length) return false;
  const lastTime=dayFilms.reduce((max,f)=>f.time>max?f.time:max,'00:00');
  const lastScreen=_festDate(dateStr,lastTime);
  lastScreen.setMinutes(lastScreen.getMinutes()+10);
  return simNow()>lastScreen;
}

export function festivalEnded(){ return simNow()>FESTIVAL_END; }
