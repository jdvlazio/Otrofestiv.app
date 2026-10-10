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

import { FESTIVAL_CONFIG, DEFAULT_DURATION_MIN, FESTIVAL_BUFFER } from "../config.js";
import { toMin, simNow, simTodayStr, festivalEnded, _festNowMin, parseDur, durEstimada } from "./time.js";
import { blockDuration } from "./film.js";
import { screeningPassed, _classifyTodayScreenings, _endedStats, effectiveWatched, seCalifica, obrasDe } from "./film.js";
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

export function _gapSuggestion(todayDay,gapFromMin,gapToMin,lastDone,next){
  // MISMO criterio de alcanzabilidad que screensConflict (schedule.js): no basta
  // que quepa por tiempo — hay que poder VIAJAR desde la función anterior
  // (lastDone) y alcanzar la siguiente (next). Usa el mismo primitivo travelMins,
  // así el hueco "Cabe en tu hueco" y la lista de Sugerencias nunca divergen.
  // (lastDone/next opcionales → sin ellos se comporta como antes: solo tiempo.)
  const _reachOK=(fromVenue,toVenue,availMin)=>{
    if(!fromVenue||!toVenue) return true;
    return availMin>=Math.max(FESTIVAL_BUFFER, travelMins(fromVenue,toVenue)+FESTIVAL_BUFFER);
  };
  return FILMS.filter(f=>{
    if(f.day!==todayDay) return false;
    if(watched.has(f.title)) return false;
    if(savedAgenda.schedule.some(s=>s._title===f.title)) return false;
    if(screeningPassed(f)) return false;
    const fStart=toMin(f.time);
    // blockDuration: una obra anclada OCUPA su función entera (un corto de 5 min
    // en un bloque de 111 no "cabe" en un hueco de 30). Antes: parseInt(duration).
    const fEnd=fStart+blockDuration(f);
    if(!(fStart>=gapFromMin&&fEnd<=gapToMin+10)) return false;
    // Viaje desde la anterior y hacia la siguiente (si las hay).
    if(lastDone&&!_reachOK(lastDone.venue,f.venue,fStart-gapFromMin)) return false;
    if(next&&!_reachOK(f.venue,next.venue,gapToMin-fEnd)) return false;
    return true;
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
    .filter(s=>s.day===todayDay&&!s.info)   // una abierta no es «la próxima»: no tiene hora a la que llegar
    .sort((a,b)=>toMin(a.time)-toMin(b.time));
  if(!todayScreenings.length) return null;

  const nowMin=_festNowMin();
  const {done,active,future}=_classifyTodayScreenings(todayScreenings,nowMin);

  // EVENING: todas las funciones del día terminaron
  if(!active.length&&!future.length){
    // effectiveWatched (dueño único): igual que antes en la práctica —
    // pasada = asumida vista — pero ahora respeta el «no la vi» (notWatched).
    const _eff=effectiveWatched();
    const todayWatched=todayScreenings.filter(s=>_eff.has(s._title));
    return{phase:'evening',todayScreenings,todayWatched};
  }

  const next=active.length?active[0]:future[0];
  const nextStartMin=toMin(next.time);
  const minsUntil=Math.max(0,nextStartMin-nowMin);
  const lastDone=done[done.length-1];

  // BETWEEN: hueco > 45 min entre función terminada y la próxima
  if(lastDone&&!active.length&&minsUntil>45){
    // blockDuration: con anclaje, la última función termina cuando termina el
    // BLOQUE — con la obra corta (5 min) el hueco "libre" arrancaba a las 18:05
    // con la función viva hasta 19:51 (mismo bug que Mi Plan, 30 jul 2026).
    const lastDoneDur=blockDuration(lastDone)||DEFAULT_DURATION_MIN;
    const gapFromMin=toMin(lastDone.time)+lastDoneDur;
    const gapToMin=nextStartMin;
    return{
      phase:'between',
      next,
      lastDone,
      gapMin:gapToMin-gapFromMin,
      gapFromMin,
      gapToMin,
      gapSuggestion:_gapSuggestion(todayDay,gapFromMin,gapToMin,lastDone,next),
      minsUntil
    };
  }

  // NEXT: próxima función en ≤ 45 min, o función en curso
  return{phase:'next',next,minsUntil,isNow:active.length>0};
}

// ── festivalRecap — «Tu festival» (#1055, F1) ────────────────────────────────
// El recorrido del asistente cuando el festival terminó: cuántas vio, en cuántos
// días y sedes, cuántas horas en sala, de cuántos países, y sus tres mejores.
// Vive acá y no en film.js (como decía el diseño) porque necesita la ciudad de
// la sede (_resolveVenue + FESTIVAL_CONFIG) y film.js no puede importar de este
// módulo sin cerrar un ciclo.
//
// REGLA DE ORO: ningún número que no se pueda afirmar. Lo que no se deriva con
// certeza se devuelve null y la vista lo omite; nunca se estima.
//   · «qué viste» = effectiveWatched (dueño único); cuenta por obra como _endedStats.
//   · día/sede de cada vista: del Plan si estaba ahí; si no, de watchedMeta (lo que
//     el usuario marcó desde el botón o una ficha con una sola función). Una obra
//     vista SIN función conocida cuenta como vista pero no suma día ni sede.
//     Si alguna vista quedó sin función, dias/sedes salen null: afirmar «3 días»
//     cuando pudo haber un cuarto sería mentir.
//   · horas: solo películas (seCalifica) con duración DECLARADA; si menos del 80 %
//     la declara, null. Un programa de cortos aporta la duración del programa.
//   · países: de películas, separados por coma; distintos. Null si ninguna lo trae.
//   · top: las 3 mejor calificadas; empate → orden cronológico (día+hora), y lo
//     sin fecha al final. Solo obras con estrellas.
//   · multiciudad: ciudades distintas aparte; la vista elige cuál mostrar.
// planRecap() — la historia «Mi plan» (#1064): lo que el usuario VA a ver, con
// la misma regla que festivalRecap («lo visto y lo asistido»): el titular cuenta
// obras (obrasDe: un programa son sus cortos, un evento las que proyecta). El
// mosaico lleva las prioridades primero; «No me las pierdo» son las prioridades
// tal como están en el Plan (el programa, no sus cortos), en orden cronológico.
// Cuenta solo lo que falta: lo pasado y lo visto no entran.
// → {obras:[{title, film, prio}], n, dias, sedes, ciudades, prios:[{title, film, day, time}]}
export function planRecap(){
  // Solo lo que FALTA (auditoría UX Writer, 10 oct): «Voy a ver» es futuro, y a
  // mitad del festival el Plan entero contaba también lo ya visto. Fuera las
  // funciones a las que ya no se llega (screeningPassed) y lo marcado como visto.
  const sch=((savedAgenda&&savedAgenda.schedule)||[]).filter(s=>s&&s._title&&!screeningPassed(s)&&!watched.has(s._title));
  const _vs=(FESTIVAL_CONFIG[_activeFestId]||{}).venues||{};
  const dias=new Set(), sedes=new Set(), ciudades=new Set(), vistos=new Set();
  const obras=[], prios=[];
  sch.slice().sort((a,b)=>(a.day+a.time).localeCompare(b.day+b.time)).forEach(s=>{
    dias.add(s.day);
    if(s.venue){ const r=_resolveVenue(s.venue,_vs); sedes.add(r.short||s.venue); if(r.city) ciudades.add(r.city); }
    if(vistos.has(s._title)) return; // un taller de dos sesiones es UNA entrada
    vistos.add(s._title);
    const f=(FILMS||[]).find(x=>x.title===s._title&&x.day===s.day&&x.time===s.time)||(FILMS||[]).find(x=>x.title===s._title);
    if(!f) return;
    const prio=prioritized.has(s._title);
    if(prio) prios.push({title:s._title, film:f, day:s.day, time:s.time||''});
    obrasDe(f).forEach(it=>obras.push({title:it.title, prio, film:it===f?f:{...it,_prog:f}}));
  });
  obras.sort((a,b)=>b.prio-a.prio); // estable: dentro de cada grupo, cronológico
  return {obras, n:obras.length, dias:dias.size, sedes:sedes.size, ciudades:ciudades.size, prios};
}

export function festivalRecap(){
  const vistas=[...effectiveWatched()];
  const _byTitle=new Map();
  (FILMS||[]).forEach(f=>{ if(!_byTitle.has(f.title)) _byTitle.set(f.title,[]); _byTitle.get(f.title).push(f); });
  // Función conocida por título: el Plan manda (es la elección), luego watchedMeta.
  const _fn=new Map();
  ((savedAgenda&&savedAgenda.schedule)||[]).forEach(s=>{ if(s&&s._title&&s.day&&!_fn.has(s._title)) _fn.set(s._title,{day:s.day,time:s.time||'',venue:s.venue||''}); });
  Object.entries((typeof watchedMeta!=='undefined'&&watchedMeta)||{}).forEach(([t,m])=>{ if(m&&m.day&&!_fn.has(t)) _fn.set(t,m); });
  const _vs=(FESTIVAL_CONFIG[_activeFestId]||{}).venues||{};
  const _city=v=>v?(_resolveVenue(v,_vs).city||''):'';

  let peliculas=0, eventos=0, sinFuncion=0, conDur=0, minutos=0, basesDur=0;
  const dias=new Set(), sedes=new Set(), ciudades=new Set(), paises=new Set();
  const obras=[]; // {title, rating, day, time, poster-able film}
  vistas.forEach(t=>{
    const fs=_byTitle.get(t); if(!fs||!fs.length) return;
    const f=fs[0];
    const fn=_fn.get(t)||null;
    if(fn){ dias.add(fn.day); if(fn.venue){ sedes.add(_resolveVenue(fn.venue,_vs).short||fn.venue); const c=_city(fn.venue); if(c) ciudades.add(c); } }
    else sinFuncion++;
    // Lo asistido: el evento cuenta como actividad. Lo visto: sus obras (obrasDe),
    // que pueden ser ninguna (una charla) o las que el festival declaró adentro.
    const esEvento=!seCalifica(f);
    if(esEvento) eventos++;
    const items=obrasDe(f);
    peliculas+=items.length;
    items.forEach(it=>{
      String(it.country||(!esEvento&&it!==f?f.country:'')||'').split(/\s*[,/]\s*/).map(x=>x.trim()).filter(Boolean).forEach(c=>paises.add(c));
      const r=filmRatings[it.title]||0;
      obras.push({title:it.title, rating:r, day:fn?fn.day:'', time:fn?fn.time:'', film:it===f?f:{...it,_prog:f}});
    });
    // Horas en sala: lo que se proyectó. Obra o programa → su duración (la del
    // programa, una vez). Evento → solo la duración declarada de cada obra que
    // proyectó; la ceremonia o la charla no son «horas en sala».
    if(!esEvento){ basesDur++; if(!durEstimada(f.duration)){ conDur++; minutos+=parseDur(f.duration); } }
    else items.forEach(it=>{ basesDur++; if(!durEstimada(it.duration)){ conDur++; minutos+=parseDur(it.duration); } });
  });
  const horas=(basesDur&&conDur/basesDur>=0.8)?Math.round(minutos/60):null;
  const conEstrellas=obras.filter(o=>o.rating>0).sort((a,b)=>
    (b.rating-a.rating)||((a.day||'\uffff')<(b.day||'\uffff')?-1:(a.day||'\uffff')>(b.day||'\uffff')?1:0)||(toMin(a.time||'99:99')-toMin(b.time||'99:99')));
  return {
    peliculas, eventos, actividades:peliculas+eventos,
    dias: sinFuncion?null:dias.size,
    sedes: sinFuncion?null:sedes.size,
    ciudades: sinFuncion?null:ciudades.size,
    horas,
    paises: paises.size||null,
    top: conEstrellas.slice(0,3),
    obras,
  };
}
