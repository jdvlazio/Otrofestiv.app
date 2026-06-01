// ── src/domain/festival.js — Fase 8 Step 5 (CABLEADO) ───────────────────────
//
// ESTADO: importado por src/main.js (Step 5). Venue travel + festival phase.
//
// DEPS:
//   - domain/time: toMin, simNow, simTodayStr, festivalEnded (imports ↓)
//   - domain/film: screeningPassed, _classifyTodayScreenings, _endedStats (↓)
//   - config: FESTIVAL_CONFIG (venueTravelMins), DEFAULT_DURATION_MIN
//     (_gapSuggestion, _getFestivalPhase) — import directo.
//   - festival-state vía STATE BRIDGE: _activeFestId + FESTIVAL_TRANSPORT
//     (venueTravelMins), FILMS, savedAgenda, watched, FESTIVAL_DATES, DAY_KEYS.
//
// NOTA DAG: _getFestivalPhase + _gapSuggestion se ubican aquí (no en time.js)
//   para romper el micro-ciclo time↔schedule. festival → time + film + config;
//   schedule → festival (travelMins). Acíclico.
//
// WORKER: venueTravelMins/travelMins tienen COPIAS worker-local (leen
//   _venueCoords/_transport). Las sched pure fns se consumen vía
//   eval(name).toString(). [worker-overlap] valida.

import { FESTIVAL_CONFIG, DEFAULT_DURATION_MIN } from "../config.js";
import { toMin, simNow, simTodayStr, festivalEnded, _festNowMin } from "./time.js";
import { screeningPassed, _classifyTodayScreenings, _endedStats } from "./film.js";
export function _resolveVenue(name,venues){
  if(!name) return{short:''};
  if(!venues) return{short:name};
  if(venues[name]) return venues[name];
  const sorted=Object.keys(venues).sort((a,b)=>b.length-a.length);
  const nl=name.toLowerCase();
  const k=sorted.find(k=>name.startsWith(k)||name.includes(k)||nl.startsWith(k.toLowerCase())||nl.includes(k.toLowerCase()));
  return k?venues[k]:{short:name};
}

// venueTravelMins/travelMins (main-thread): tiempo de viaje entre sedes vía
// coords del festival activo. Leen FESTIVAL_CONFIG (config) + _activeFestId /
// FESTIVAL_TRANSPORT (bridge). El worker mantiene SUS copias (lee _venueCoords/
// _transport worker-local). screensConflict (schedule.js) importa travelMins.
export function venueTravelMins(v1,v2){
  // Data-driven: uses coords from active festival's venues JSON
  const festVenues=(FESTIVAL_CONFIG[_activeFestId]||{}).venues||{};
  const c1=_resolveVenue(v1,festVenues),c2=_resolveVenue(v2,festVenues);
  const lat1=c1.lat,lng1=c1.lng??c1.lon,lat2=c2.lat,lng2=c2.lng??c2.lon;
  if(!lat1||!lng1||!lat2||!lng2) return 0;
  const dlat=(lat1-lat2)*111,dlon=(lng1-lng2)*111*Math.cos(lat1*Math.PI/180);
  const km=Math.sqrt(dlat*dlat+dlon*dlon);
  if(km<0.15) return 0;
  // Velocidad efectiva por modo de transporte (km/h, incluye overhead puerta-a-puerta)
  const spd=FESTIVAL_TRANSPORT==='walking'?4:FESTIVAL_TRANSPORT==='transit'?10:12;
  return Math.max(5,Math.round(km/spd*60/5)*5);
}
export function travelMins(venueA,venueB){
  // Coordinate-based — all festivals provide venues with lat+lng
  return venueTravelMins(venueA,venueB);
}

export function _gapSuggestion(todayDay,gapFromMin,gapToMin){
  return FILMS.filter(f=>{
    if(f.day!==todayDay) return false;
    if(watched.has(f.title)) return false;
    if(savedAgenda.schedule.some(s=>s._title===f.title)) return false;
    if(screeningPassed(f)) return false;
    const fStart=toMin(f.time);
    const fEnd=fStart+(parseInt(f.duration)||DEFAULT_DURATION_MIN);
    return fStart>=gapFromMin&&fEnd<=gapToMin+10;
  })[0]||null;
}

export function _getFestivalPhase(){
  if(festivalEnded()) return{phase:'ended',..._endedStats()};
  if(!savedAgenda||!savedAgenda.schedule||!savedAgenda.schedule.length) return null;

  const now=simNow();
  const _fsDStr=DAY_KEYS[0]?FESTIVAL_DATES[DAY_KEYS[0]]||'':'';
  const FESTIVAL_START=_fsDStr?new Date(_fsDStr+'T00:00:00'+(TZ_OFFSET||'')):new Date(0);
  if(now<FESTIVAL_START) return{phase:'before',daysDiff:Math.ceil((FESTIVAL_START-now)/86400000)};

  const todayStr=simTodayStr();
  const todayDay=DAY_KEYS.find(d=>FESTIVAL_DATES[d]===todayStr);
  if(!todayDay) return null;
  const todayScreenings=savedAgenda.schedule
    .filter(s=>s.day===todayDay)
    .sort((a,b)=>toMin(a.time)-toMin(b.time));
  if(!todayScreenings.length) return null;

  const nowMin=_festNowMin();
  const {done,active,future}=_classifyTodayScreenings(todayScreenings,nowMin);

  // EVENING: todas las funciones del día terminaron
  if(!active.length&&!future.length){
    const todayWatched=todayScreenings.filter(s=>watched.has(s._title)||screeningPassed(s));
    return{phase:'evening',todayScreenings,todayWatched};
  }

  const next=active.length?active[0]:future[0];
  const nextStartMin=toMin(next.time);
  const minsUntil=Math.max(0,nextStartMin-nowMin);
  const lastDone=done[done.length-1];

  // BETWEEN: hueco > 45 min entre función terminada y la próxima
  if(lastDone&&!active.length&&minsUntil>45){
    const lastDoneDur=parseInt(lastDone.duration)||DEFAULT_DURATION_MIN;
    const gapFromMin=toMin(lastDone.time)+lastDoneDur;
    const gapToMin=nextStartMin;
    return{
      phase:'between',
      next,
      lastDone,
      gapMin:gapToMin-gapFromMin,
      gapFromMin,
      gapToMin,
      gapSuggestion:_gapSuggestion(todayDay,gapFromMin,gapToMin),
      minsUntil
    };
  }

  // NEXT: próxima función en ≤ 45 min, o función en curso
  return{phase:'next',next,minsUntil,isNow:active.length>0};
}
