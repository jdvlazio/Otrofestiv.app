// ── src/domain/festival.js — Fase 8 Wave 2 (PREP, NO CABLEADO) ──────────────────
//
// ⚠ ESTADO: módulo de preparación. NO importado por index.html. Cero impacto
//   runtime/deploy/SW. Wiring real en Wave 2 post-Tribeca.
// ⚠ FUENTE DE VERDAD: index.html hasta el wiring. Copia fiel (byte-faithful,
//   generada vía extractFunction). Si cambia en index.html antes del wiring,
//   re-generar.
//
// DEPS EXTERNAS (a inyectar/importar en el wiring — NO resueltas aquí):
//   - domain/time: toMin, simNow, simTodayStr, festivalEnded (imports ↓)
//   - domain/film: screeningPassed, _classifyTodayScreenings (imports ↓)
//   - config: DEFAULT_DURATION_MIN (_gapSuggestion, _getFestivalPhase)
//   - festival-state: FILMS, savedAgenda, watched, FESTIVAL_DATES, DAY_KEYS
//
// NOTA DAG: _getFestivalPhase + _gapSuggestion se ubican aquí (no en time.js
//   como sugería §13) para ROMPER el micro-ciclo time↔schedule detectado en
//   pre-flight. Aquí: festival → time + film (sólo hacia abajo, acíclico).
//
// WORKER: las sched pure fns tienen COPIAS en el template string del calc
//   worker (Blob worker clásico, index.html L~8950). El worker NO puede
//   `import`. Al cablear: decidir module worker vs mantener la copia
//   worker-local (status quo, validado por [worker-overlap]). Mientras, este
//   módulo y la copia worker DEBEN mantenerse sincronizados.

import { toMin, simNow, simTodayStr, festivalEnded } from "./time.js";
import { screeningPassed, _classifyTodayScreenings } from "./film.js";
export function _resolveVenue(name,venues){
  if(!name) return{short:''};
  if(!venues) return{short:name};
  if(venues[name]) return venues[name];
  const sorted=Object.keys(venues).sort((a,b)=>b.length-a.length);
  const nl=name.toLowerCase();
  const k=sorted.find(k=>name.startsWith(k)||name.includes(k)||nl.startsWith(k.toLowerCase())||nl.includes(k.toLowerCase()));
  return k?venues[k]:{short:name};
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
  const FESTIVAL_START=_fsDStr?new Date(_fsDStr+'T00:00:00'):new Date(0);
  if(now<FESTIVAL_START) return{phase:'before',daysDiff:Math.ceil((FESTIVAL_START-now)/86400000)};

  const todayStr=simTodayStr();
  const todayDay=DAY_KEYS.find(d=>FESTIVAL_DATES[d]===todayStr);
  if(!todayDay) return null;
  const todayScreenings=savedAgenda.schedule
    .filter(s=>s.day===todayDay)
    .sort((a,b)=>toMin(a.time)-toMin(b.time));
  if(!todayScreenings.length) return null;

  const nowMin=now.getHours()*60+now.getMinutes();
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
