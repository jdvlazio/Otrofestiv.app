// ── src/domain/film.js — Fase 8 Step 5 (CABLEADO) ───────────────────────────
//
// ESTADO: importado por src/main.js (Step 5). Funciones puras de film/scoring.
//
// DEPS:
//   - domain/time: parseDur, _festDate, simNow, festivalEnded, toMin (imports ↓)
//   - festival-state vía STATE BRIDGE: FESTIVAL_DATES (screeningPassed), FILMS +
//     savedAgenda (_endedStats), FILMS + watched/filmRatings (scoreFilm).
//
// WORKER: las sched pure fns tienen COPIAS en el template del calc worker; el
//   worker las consume vía eval(name).toString(). [worker-overlap] valida.

import { FESTIVAL_QA_MIN } from "../config.js";
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
  // Catálogo de cortos SIN sesión asignada (is_cortos + unscheduled + film_list):
  // vive en buscador/Explorar sin día/hora hasta que el festival publique la
  // jornada. NO es un bug de datos → exento de los chequeos day/time.
  const isUnscheduledCatalog = !!f.is_cortos && !!f.unscheduled
    && Array.isArray(f.film_list) && f.film_list.length>0;
  // day — ERROR (keep): debe ser clave exacta de dayKeys (FESTIVAL_DATES[day] +
  // agrupación por día). day inválido → film invisible / mal-agrupado.
  if(!isUnscheduledCatalog && Array.isArray(dayKeys) && dayKeys.length){
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

// `_slotMin` (lo marca el loader en festivales con `sharedSlotIsOneScreening`):
// dos obras programadas en la MISMA función ocupan la sala por la suma de
// ambas, no por la propia. Sin esto el planificador cree que salís al terminar
// la primera y te ofrece otra función a la que no llegás.
// blockDuration — cuánto dura la FUNCIÓN a la que entra el espectador. Con
// anclaje, la suma de las obras del slot (`_slotDur`, sellado por el loader);
// sin anclaje, la duración de la obra. SIN el Q&A: quedarse es opcional, y por
// eso existe su aviso.
//
// Es la respuesta a "¿hasta qué hora estoy en la sala?" y la usan TODAS las
// superficies que miden tiempo: huecos de sugerencias, "termina en X min", "en
// curso", buffer de retrasos, fin del día. Antes cada una hacía
// parseDur(f.duration) por su cuenta y ninguna sabía de anclaje: un corto de 5
// min dentro de una función de 111 declaraba libre un hueco que no existía.
//
// El par: effectiveDuration = blockDuration + Q&A, para CONFLICTOS, donde
// quedarse al Q&A tiene que caber.
export function blockDuration(f){
  if(f&&f._slotDur) return f._slotDur;
  return parseDur(f&&f.duration);
}

export function effectiveDuration(f){
  if(f&&f._slotMin) return f._slotMin;
  return parseDur(f&&f.duration)+(f&&f.has_qa?FESTIVAL_QA_MIN:0);
}

// durationForTravel — LA DOCTRINA DEL Q&A en un solo dueño (30 jul 2026):
// el Q&A (+30 estimados) solo compromete tu tiempo cuando salir cuesta algo,
// es decir cuando hay TRASLADO a otra sede. Misma sede → el fin duro es el
// bloque (blockDuration) y el Q&A queda como advertencia, no como muro.
// Antes esta decisión vivía inline en screensConflict/Reason (_qaCuenta) y
// re-escrita a mano en la vista de delays — dos sitios que podían divergir.
export function durationForTravel(f,travel){
  return travel>0?effectiveDuration(f):blockDuration(f);
}

export function screeningPassed(s){
  if(festivalEnded()) return false; // festival terminado — todo vuelve a plena opacidad
  const dateStr=FESTIVAL_DATES[s.day];
  if(!dateStr) return false;
  const screeningTime=_festDate(dateStr,s.time);
  screeningTime.setMinutes(screeningTime.getMinutes()+10); // 10 min grace
  return simNow()>screeningTime;
}

// ── Predicados CANÓNICOS de fase de una función (fuente única) ────────────────
// "terminó" y "en curso" estaban reimplementados inline en 5 sitios (aquí,
// isNowShowing, agenda.js ×2, _updateMiPlanBadge), cada uno con parseInt y SIN
// el Q&A (+30) que el planificador sí cuenta. Todo fin de función sale de
// screeningEndMin (effectiveDuration = parseDur + Q&A). NOTA: screeningPassed
// (arriba) es OTRO concepto — "ya no llegás" (arranque+10 de gracia), no "terminó".
export function screeningEndMin(s){ return toMin(s.time)+effectiveDuration(s); }
// screeningBlockEndMin — el fin de las PELÍCULAS (sin Q&A): lo que la pantalla
// imprime como hora de salida. Es el «termina 16:59» de la cuenta del veredicto
// (conflictAccount, 15 ago 2026): el Q&A y el viaje se muestran como sumandos
// aparte, así que la frase arranca del fin duro, no del efectivo.
export function screeningBlockEndMin(s){ return toMin(s.time)+blockDuration(s); }
// screeningEndDate — el MISMO fin canónico, como instante absoluto (cruza días).
// Dueño único del filtro "esta entrada del plan ya terminó": renderUnconfirmed y
// _updateMiPlanBadge lo reconstruían por separado, y el "terminó hace X min"
// usaba OTRO fin (blockDuration) en la misma frase que el filtro (effective).
export function screeningEndDate(s){
  const dateStr=FESTIVAL_DATES[s.day];
  if(!dateStr) return null;
  const end=_festDate(dateStr,s.time);
  end.setMinutes(end.getMinutes()+effectiveDuration(s));
  return end;
}
// isShortFilm — «es un corto» como predicado de DOMINIO (≤40 min con duración
// conocida). Nació del toast del programa (15 ago 2026): la vista decidía
// cortos/obras parseando duraciones a mano, que es cómo divergen los criterios.
export function isShortFilm(f){ const d=parseDur(f&&f.duration); return d>0&&d<=40; }
export function screeningEnded(s,nowMin){ return screeningEndMin(s)<=nowMin; }
export function screeningNow(s,nowMin){ return toMin(s.time)<=nowMin&&!screeningEnded(s,nowMin); }

export function _classifyTodayScreenings(screenings,nowMin){
  const done=screenings.filter(s=>screeningEnded(s,nowMin));
  const active=screenings.filter(s=>screeningNow(s,nowMin));
  const future=screenings.filter(s=>toMin(s.time)>nowMin);
  return{done,active,future};
}

export function _endedStats(){
  // Conteo POR OBRA (modelo del Diario): un programa visto cuenta por sus
  // películas — es lo que el usuario realmente vio. Antes excluía is_cortos
  // por completo → "Viste 0" con dos programas vistos. Eventos no cuentan.
  let totalWatched=0, pendingRatings=0;
  [...watched].forEach(t=>{
    const f=FILMS.find(fi=>fi.title===t);
    if(!f||f.type==='event') return;
    if(f.is_cortos&&f.film_list&&f.film_list.length){
      totalWatched+=f.film_list.length;
      pendingRatings+=f.film_list.filter(it=>!filmRatings[it.title]).length;
    } else {
      totalWatched+=1;
      if(!filmRatings[t]) pendingRatings+=1;
    }
  });
  const totalPlanned=savedAgenda&&savedAgenda.schedule?savedAgenda.schedule.length:0;
  return{totalWatched,totalPlanned,pendingRatings};
}

// ── PREPARACIÓN DE CATÁLOGO (dueño único: loader Y tests) ─────────────────────
// Estas dos transformaciones vivían inline en loadFestival. El oráculo del
// planeador (tests/unit/plannerOracle) necesita ejercer el MISMO catálogo que
// producción — duplicarlas en el test lib habría creado la divergencia que un
// oráculo existe para impedir. Extraídas como puras; el loader las llama.

// explodeScreenings — screenings[] → un objeto plano por función.
// Compatibilidad total con el formato plano existente (day/time/venue).
export function explodeScreenings(films){
  const exploded=[];
  (films||[]).forEach(f=>{
    if(Array.isArray(f.screenings)&&f.screenings.length){
      const base=Object.assign({},f);
      delete base.screenings;
      f.screenings.forEach((s,i)=>{
        exploded.push(Object.assign({},base,{
          day:s.day||s.date,date:s.date||s.day,time:s.time,venue:s.venue||'',
          day_order:s.day_order!==undefined?s.day_order:i,
          sala:s.sala||'',
          ...(s.is_free!=null?{is_free:s.is_free}:{}), // por-función (festivales mixed)
          // El formulario es de ESA actividad, no del festival (la Master Class de
          // FICDEH se titula con su propio nombre) → viaja por función, como is_free.
          ...(s.registration_url?{registration_url:s.registration_url}:{})
        }));
      });
    } else {
      exploded.push(f);
    }
  });
  return exploded;
}

// sealSharedSlots — ANCLAJE DE FUNCIÓN (opt-in: root `sharedSlotIsOneScreening`).
// Muta los films del grupo (mismo día|hora|sede|sala) con _slotKey/_slotDur/_slotMin.
// La sala queda ocupada por la SUMA de las obras; el Q&A se cuenta UNA vez.
// Doctrina completa en docs/SCHEMA.md § Proyecciones conjuntas.
export function sealSharedSlots(films){
  const _grupos={};
  films.forEach(f=>{
    if(f.info||!f.day||!f.time||!f.venue) return;
    (_grupos[f.day+'|'+f.time+'|'+f.venue+'|'+(f.sala||'')] ||= []).push(f);
  });
  Object.entries(_grupos).forEach(([k,g])=>{
    if(g.length<2) return;
    const base=g.reduce((a,f)=>a+parseDur(f.duration),0);
    const total=base+(g.some(f=>f.has_qa)?FESTIVAL_QA_MIN:0);
    g.forEach(f=>{ f._slotKey=k; f._slotDur=base; f._slotMin=total; });
  });
  return films;
}

// _delayKey — clave del retraso reportado de una función (título|día|hora).
// Vivía en la vista (agenda.js); es identidad de dominio y la usa delayedEndMin.
export function _delayKey(s){return(s._title||s.title||'')+'|'+(s.day||'')+'|'+(s.time||'');}

// delayedEndMin — el fin de una función CON su retraso reportado (PR 3, 31 jul).
// El delay se sumaba a mano en 2 sitios de la vista — el residuo real que quedó
// del intervalo canónico descartado por el tech lead (lo demás ya tenía dueño).
//   travel === undefined → fin de BLOQUE (+delay): "¿hasta cuándo estoy en la sala?"
//   travel numérico     → doctrina del Q&A vía durationForTravel (+delay):
//                         margen real hacia OTRA función.
export function delayedEndMin(s, travel){
  const d=(typeof filmDelays!=='undefined'&&filmDelays&&filmDelays[_delayKey(s)])||0;
  return toMin(s.time)+(travel===undefined?blockDuration(s):durationForTravel(s,travel))+d;
}
