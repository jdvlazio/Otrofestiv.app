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

// Offset de TZ_OFFSET ("-04:00"/"+05:30") a minutos. Default Colombia (-05:00).
function _tzOffsetMin(off){
  const m=/^([+-])(\d{2}):(\d{2})$/.exec(off||'-05:00');
  return m?(m[1]==='-'?-1:1)*(parseInt(m[2],10)*60+parseInt(m[3],10)):-300;
}
// "Ahora" en hora LOCAL DEL FESTIVAL. El modo en-curso (now-line, contador, "en
// curso", clasificación done/active/future, "hoy") se ancla a la zona del festival
// —no a la del dispositivo— porque el horario ya está en hora del venue ("8:00 PM"
// = NYC). Se desplaza el instante por TZ_OFFSET y se leen getters UTC → reloj de
// pared del festival, sin importar dónde esté el usuario. Las comparaciones
// ABSOLUTAS (screeningPassed/festivalEnded vía _festDate+offset) ya son correctas.
export function _festNow(){ return new Date(simNow().getTime()+_tzOffsetMin(TZ_OFFSET)*60000); }
export function _festNowMin(){ const d=_festNow(); return d.getUTCHours()*60+d.getUTCMinutes(); }

export function simTodayStr(){
  // Fecha "hoy" EN HORA DEL FESTIVAL (no del dispositivo ni UTC): _festNow()+getUTC*
  // sobre el instante desplazado → día local del festival. Así "hoy" coincide con el
  // día del horario para un usuario en cualquier zona (ej: tester en Colombia durante
  // Tribeca en NYC). Antes usaba getHours/getDate locales → hasta 1 día / 1 hora off.
  const d=_festNow();
  return d.getUTCFullYear()+'-'+String(d.getUTCMonth()+1).padStart(2,'0')+'-'+String(d.getUTCDate()).padStart(2,'0');
}

export function dayFullyPassed(day){
  const dateStr=FESTIVAL_DATES[day];
  if(!dateStr) return false;
  // Day passed if last function of that day has passed
  const dayFilms=FILMS.filter(f=>f.day===day);
  // Día SIN programación: no hay "última función" que mirar → el día pasó cuando
  // terminó su FECHA. Antes devolvía false SIEMPRE, así que un día vacío nunca se
  // atenuaba (bug: MAR sin programación en TT seguía en opacidad alta) y peor: se
  // colaba como "primer día futuro" en la navegación y en la hoja de Disponibilidad.
  if(!dayFilms.length) return simNow()>_festDate(dateStr,'23:59');
  const lastTime=dayFilms.reduce((max,f)=>f.time>max?f.time:max,'00:00');
  const lastScreen=_festDate(dateStr,lastTime);
  lastScreen.setMinutes(lastScreen.getMinutes()+10);
  return simNow()>lastScreen;
}

export function festivalEnded(){ return simNow()>FESTIVAL_END; }
