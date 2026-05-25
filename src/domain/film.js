// ── src/domain/film.js — Fase 8 Step 5 (CABLEADO) ───────────────────────────
//
// ESTADO: importado por src/main.js (Step 5). Funciones puras de film/scoring.
//
// DEPS:
//   - domain/time: parseDur, _festDate, simNow, festivalEnded, toMin (imports ↓)
//   - config: DEFAULT_DURATION_MIN (_classifyTodayScreenings) — import directo.
//   - festival-state vía STATE BRIDGE: FESTIVAL_DATES (screeningPassed), FILMS +
//     savedAgenda (_endedStats), FILMS + watched/filmRatings (scoreFilm).
//
// WORKER: las sched pure fns tienen COPIAS en el template del calc worker; el
//   worker las consume vía eval(name).toString(). [worker-overlap] valida.

import { DEFAULT_DURATION_MIN } from "../config.js";
import { parseDur, _festDate, simNow, festivalEnded, toMin } from "./time.js";

// p8 Step 8d-1: normTitle — normaliza comillas tipográficas en títulos (punto
// único). Puro. Reubicado desde main.js; main.js lo re-importa + re-expone global
// (leído bare por controller/{persistence,handlers,overlays}.js vía globalThis).
export function normTitle(t){
  if(!t) return t;
  return t
    .replace(/[‘’ʼʹ]/g,"'")  // comillas simples tipográficas → '
    .replace(/[“”«»]/g,'"');  // comillas dobles tipográficas → "
}

// validateFilm — VALIDACIÓN DE DATOS (pura · sin side-effects · sin imports del
// bridge). Valida un film YA exploded (flat) contra dayKeys + venues del festival,
// recibidos como PARÁMETROS (no lee globalThis) → testeable en aislamiento.
// Returns { valid, drop, errors, warnings }:
//   drop=true  → film inutilizable (sin title) → el caller lo EXCLUYE de FILMS.
//   errors[]   → bugs de datos graves (day∉dayKeys, time inválido). El caller
//                CONSERVA el film pero logea error (no dropea contenido en silencio).
//   warnings[] → degradación con fallback (section/venue/duration).
//   valid = !drop && errors.length===0  (film "perfecto").
export function validateFilm(f, dayKeys, venues){
  const errors=[], warnings=[];
  // title — HARD: es la clave primaria (Sets keyed-by-title + normTitle).
  // Sin un title string no vacío, el film corrompe state → drop.
  if(!f || typeof f.title!=='string' || !f.title.trim()){
    return { valid:false, drop:true, errors:['title faltante, vacío o no-string (film inutilizable)'], warnings };
  }
  const isEvent = f.type==='event';
  // day — ERROR (keep): debe ser clave exacta de dayKeys (FESTIVAL_DATES[day] +
  // agrupación por día). day inválido → film invisible / mal-agrupado.
  if(Array.isArray(dayKeys) && dayKeys.length){
    if(f.day==null || !dayKeys.includes(f.day)){
      errors.push(`day "${f.day}" no está en dayKeys`);
    }
  }
  // time — ERROR (keep) en films no-event: toMin(falsy)→0 → se agendaría a las 00:00.
  if(!isEvent){
    if(typeof f.time!=='string' || !f.time.trim()){
      errors.push('time faltante (se agendaría a medianoche)');
    } else if(!/\d/.test(f.time)){
      errors.push(`time "${f.time}" no parece una hora válida`);
    }
  }
  // section — WARN+default '' (caller/render ya tolera con fallback).
  if(typeof f.section!=='string' || !f.section.trim()){
    warnings.push('section faltante (default "")');
  }
  // venue — WARN: si hay venues{} y no es clave exacta (igual hay fuzzy-match,
  // pero sin coords no se calcula travel → buffer de viaje perdido).
  if(f.venue && venues && typeof venues==='object' && Object.keys(venues).length && !venues[f.venue]){
    warnings.push(`venue "${f.venue}" no es clave exacta de venues{} (fuzzy-match / sin travel)`);
  }
  // duration — WARN: presente pero sin dígitos (parseDur igual defaultea seguro).
  if(f.duration!=null && !/\d/.test(String(f.duration))){
    warnings.push(`duration "${f.duration}" no numérica (usará duración por defecto)`);
  }
  return { valid: errors.length===0, drop:false, errors, warnings };
}

export function _djb2(str){
  let h=5381;
  for(let i=0;i<str.length;i++) h=(Math.imul(31,h)+str.charCodeAt(i))|0;
  return h;
}

export function _titleSeed(titles){
  return _djb2([...titles].sort().join('|'));
}

export function _mulberry32(seed){
  let s=seed|0;
  return function(){
    s=s+0x6D2B79F5|0;
    let t=Math.imul(s^s>>>15,1|s);
    t=t+Math.imul(t^t>>>7,61|t)^t;
    return((t^t>>>14)>>>0)/4294967296;
  };
}

export function shuffle(arr,rand){
  const a=[...arr];
  const r=rand||Math.random.bind(Math);
  for(let i=a.length-1;i>0;i--){const j=Math.floor(r()*(i+1));[a[i],a[j]]=[a[j],a[i]];}
  return a;
}

export function scoreFilm(title, screens, isPriority, allTitles){
  let score=0;
  // Prioridad explícita: peso máximo
  if(isPriority) score+=100;
  // Unicidad: menos funciones = más difícil de ver = mayor peso
  const n=screens.length;
  if(n===1) score+=40;
  else if(n===2) score+=20;
  else score+=5;
  // Sección única: si es la única película de su sección en la watchlist
  const mySection=screens[0]?.section||'';
  const siblingsInSection=allTitles.filter(t=>{
    if(t===title) return false;
    return FILMS.some(f=>f.title===t&&f.section===mySection);
  });
  if(siblingsInSection.length===0) score+=15;
  // Duración larga: película de >150 min es un compromiso grande, priorizar
  const dur=parseInt(screens[0]?.duration)||0;
  if(dur>150) score+=10;
  return score;
}

export function effectiveDuration(f){return parseDur(f&&f.duration)+(f&&f.has_qa?30:0);}

export function screeningPassed(s){
  if(festivalEnded()) return false; // festival terminado — todo vuelve a plena opacidad
  const dateStr=FESTIVAL_DATES[s.day];
  if(!dateStr) return false;
  const screeningTime=_festDate(dateStr,s.time);
  screeningTime.setMinutes(screeningTime.getMinutes()+10); // 10 min grace
  return simNow()>screeningTime;
}

export function _classifyTodayScreenings(screenings,nowMin){
  const done=screenings.filter(s=>{
    const dur=parseInt(s.duration)||DEFAULT_DURATION_MIN;
    return toMin(s.time)+dur<=nowMin;
  });
  const active=screenings.filter(s=>{
    const dur=parseInt(s.duration)||DEFAULT_DURATION_MIN;
    const start=toMin(s.time);
    return start<=nowMin&&start+dur>nowMin;
  });
  const future=screenings.filter(s=>toMin(s.time)>nowMin);
  return{done,active,future};
}

export function _endedStats(){
  const _isRegular=t=>{const f=FILMS.find(fi=>fi.title===t);return f&&!f.is_cortos&&f.type!=='event';};
  const totalWatched=[...watched].filter(_isRegular).length;
  const totalPlanned=savedAgenda&&savedAgenda.schedule?savedAgenda.schedule.length:0;
  const pendingRatings=[...watched].filter(t=>_isRegular(t)&&!filmRatings[t]).length;
  return{totalWatched,totalPlanned,pendingRatings};
}
