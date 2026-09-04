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
// film.js importa de este módulo y este módulo importa de film.js: es un ciclo
// ESM deliberado y seguro — ninguno usa al otro en la evaluación del módulo,
// solo dentro de funciones, así que los enlaces vivos ya están inicializados
// cuando se llaman. La alternativa era duplicar la regla del fin de bloque
// acá, y un segundo dueño de «¿hasta qué hora estoy en la sala?» es justo lo
// que blockDuration vino a matar.
import { blockDuration } from "./film.js";
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
  // El día pasó cuando TERMINÓ su última función, no cuando empezó (auditoría
  // B-4, 2 sep 2026): con «El juego de la vida» a las 19:00 y 95 min, a las
  // 19:30 el LUN 17 salía `past` a opacity .35 —contraste 2,04:1 sobre el día
  // que estabas viviendo— mientras la cabecera de la MISMA pantalla decía «En
  // curso · Termina en 1 h 05». La regla vieja tomaba la última hora de INICIO
  // más 10 minutos fijos: ignoraba la duración. Diecisiete sitios cuelgan de
  // esta función (tabs de día, «primer día futuro», Disponibilidad,
  // sugerencias): se corrige acá y se corrigen todos.
  // Las canceladas no cuentan: una función que no va a ocurrir no mantiene
  // vivo el día. Y sin gracia de 10 min: el fin del bloque ya es el fin.
  const dayFilms=FILMS.filter(f=>f.day===day&&!f._cancelled);
  // Día SIN programación (o toda caída): no hay última función que mirar → el
  // día pasó cuando terminó su FECHA. Antes devolvía false SIEMPRE, así que un
  // día vacío nunca se atenuaba y se colaba como «primer día futuro».
  if(!dayFilms.length) return simNow()>_festDate(dateStr,'23:59');
  // Fecha por función (no minutos del día): una función que cruza medianoche
  // termina al día siguiente y la aritmética en minutos la daría por acabada.
  const lastEnd=dayFilms.reduce((max,f)=>{
    if(!f.time) return max;
    const d=_festDate(dateStr,f.time);
    d.setMinutes(d.getMinutes()+blockDuration(f));
    return d>max?d:max;
  },new Date(0));
  return simNow()>lastEnd;
}

// Un festival APLAZADO no terminó: NO ocurrió. Sin esto, la aritmética contra
// FESTIVAL_END lo daba por terminado al pasar sus fechas viejas (FICMA: 18 ago) y
// toda la app entraba en Modo Recuerdo —«Tu festival», «Marcá lo que viste y
// calificálo»— para ocho días que no existieron. Es el mismo patrón que
// _classifyFestival: el estado DECLARADO le gana a la fecha. 27 call sites cuelgan
// de esta función; corregir acá los corrige todos.
// `typeof` y no la referencia directa: este global viaja por el STATE BRIDGE y hay
// contextos que no lo declaran (el sandbox de los unit tests inyecta solo los
// globals que cada test pide — sin el guard, 72 tests morían con ReferenceError).
// Mismo motivo por el que simNow/festivalEnded están excluidas del worker.
export function festivalEnded(){
  const _post=typeof FESTIVAL_POSTPONED!=='undefined'&&FESTIVAL_POSTPONED;
  return !_post && simNow()>FESTIVAL_END;
}
