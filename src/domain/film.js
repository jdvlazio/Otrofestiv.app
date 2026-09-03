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
// isNowShowing, agenda.js ×2), cada uno con parseInt y SIN
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
// Dueño único del filtro "esta entrada del plan ya terminó": effectiveWatched y
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
// screeningQaOnly — la ventana en la que la PELÍCULA ya terminó pero la función
// sigue: los ~30 min estimados del Q&A. Dueño único de la distinción, porque la
// pantalla la necesita en dos lugares y con la misma respuesta.
//
// Por qué existe: «AHORA» y «EN CURSO» se apoyaban en el fin EFECTIVO (con Q&A),
// que es correcto para el planificador —la función te ocupa hasta el final— pero
// no para el que lee. Medido en FINCA (16 de 30 obras con Q&A): «¿Cuán profundo
// es tu amor?» empieza 19:00, la película termina 20:41 y la función 21:11; a
// las 21:00 la app decía AHORA en verde sobre una película terminada, y Mi Plan
// mostraba «Termina en 0 min» durante media hora —el rótulo contando con Q&A y
// la cuenta sin él, dos relojes en una frase—.
//
// Y hay una regla del proyecto que lo zanja: el fin de la película es DATO
// (empieza + dura); el del Q&A es ESTIMACIÓN (FESTIVAL_QA_MIN, «la UI la
// declara, nunca la afirma»). El badge más afirmativo de la app no puede
// apoyarse 30 minutos en un número estimado.
export function screeningQaOnly(s,nowMin){
  if(!s||!s.has_qa) return false;
  return screeningBlockEndMin(s)<=nowMin&&!screeningEnded(s,nowMin);
}

export function _classifyTodayScreenings(screenings,nowMin){
  const done=screenings.filter(s=>screeningEnded(s,nowMin));
  const active=screenings.filter(s=>screeningNow(s,nowMin));
  const future=screenings.filter(s=>toMin(s.time)>nowMin);
  return{done,active,future};
}

// prioLiveCount — cuántas prioridades siguen VIVAS (alguna función futura).
// El CUPO se mide sobre estas: una prioridad cuyas funciones ya pasaron no
// puede materializarse en ningún plan, y retenía el cupo igual — el auditor de
// fin de festival vio «Prioridades 2/4» con una muerta, y con 4/4 muertas el
// usuario chocaba contra la sheet del límite sin que nada le avisara antes.
// La prioridad muerta NO se borra sola (es del usuario y su lugar es la lista,
// atenuada con «Ya pasó»): solo deja de contar.
export function prioLiveCount(){
  return [...prioritized].filter(t=>FILMS.some(f=>f.title===t&&!screeningPassed(f))).length;
}

// effectiveWatched — DUEÑO ÚNICO de «qué se vio». Decisión de Juan (18 ago,
// rediseño Diario Luz): una función del Plan que ya terminó SE ASUME vista —
// el usuario no confirma; solo puede negarla («no la vi» → notWatched).
// efectivo = watched explícito ∪ asumidas del plan − notWatched.
// El precedente ya vivía en el dominio: todayWatched (festival.js) contaba
// screeningPassed como vista desde antes de esta decisión.
export function effectiveWatched(){
  const out=new Set(watched);
  if(savedAgenda&&savedAgenda.schedule){
    const now=simNow();
    savedAgenda.schedule.forEach(s=>{
      const end=screeningEndDate(s);
      if(end&&end<now&&s._title) out.add(s._title);
    });
  }
  notWatched.forEach(t=>out.delete(t));
  return out;
}

export function _endedStats(){
  // DUEÑO ÚNICO de «cuántas marcaste». Un programa visto cuenta por sus obras —
  // es lo que el usuario realmente vio. Antes excluía is_cortos por completo →
  // "Viste 0" con dos programas vistos.
  //
  // Los EVENTOS (talleres, charlas) SÍ cuentan: son lo que el Diario muestra, y
  // el chip del Diario los contaba mientras esta cuenta los descartaba — medido
  // con FICDEH (29 eventos en catálogo): 2 marcadas acá contra 3 en el chip, dos
  // números para lo mismo a dos centímetros. Por eso el titular usa el paraguas
  // ACTIVIDADES: un taller no es una obra, pero sí es una actividad ([vocab]).
  //
  // pendingRatings NO los incluye: un taller no se califica, y prometerle al
  // usuario que le falta calificar algo que no tiene estrellas sería un pendiente
  // imposible de cerrar.
  let totalWatched=0, pendingRatings=0;
  [...effectiveWatched()].forEach(t=>{
    const f=FILMS.find(fi=>fi.title===t);
    if(!f) return;
    if(f.type==='event'){ totalWatched+=1; return; }
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
    // La suma es la doctrina para OBRAS que comparten función: un corto detrás
    // de otro (FINCA). Pero un EVENTO en el bloque no es una obra más en la
    // fila: es el contenedor. FICDEH 2026 tiene cinco «Charlas que Unen» de 180
    // min que proyectan cortos adentro, y la suma le agregaba a la charla lo que
    // ya tiene dentro — «Los pliegues de la falda» (18 min) quedaba «En curso»
    // hasta las 19:32 con un bloque que termina 19:00, y el planificador
    // bloqueaba esa media hora de más (auditoría B-2, 2 sep 2026).
    // El evento es contenedor SOLO si es tan largo como lo que contiene: un
    // taller de 120 con un largo de 178 al lado (FICMA, Expoferias, sin sala) no
    // contiene nada — ahí se conserva la suma de siempre, que es lo que hoy hace
    // y que ese dato pide decidir aparte ([slots-sin-decidir]).
    const _obras=g.filter(f=>f.type!=='event').reduce((a,f)=>a+parseDur(f.duration),0);
    const _ev=g.filter(f=>f.type==='event').reduce((a,f)=>Math.max(a,parseDur(f.duration)),0);
    const base=(_ev&&_ev>=_obras)?_ev:g.reduce((a,f)=>a+parseDur(f.duration),0);
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
