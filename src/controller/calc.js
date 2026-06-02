// ── src/controller/calc.js ────────────────────────────────────────────────────
// p8 Step 7a — Orquestación de cómputo del planner (Web Worker + fallback sync).
// Leaf de la capa controller: depende de domain (puras) + view (buildResultHTML/
// showToast) + config + i18n. Lee roster/viewstate (FILMS/watchlist/cachedResult/
// etc.) vía STATE BRIDGE (globalThis). _activeCalcWorker es module-local.
//
// MECANISMO WORKER: _mkCalcWorker hace _SCHED_PURE_FNS.map(name=>eval(name)...).
// eval(name) (direct eval) resuelve en el scope del módulo → las 15 fns puras
// DEBEN importarse aquí aunque el AST no las vea (están en strings de eval).

import { FESTIVAL_CONFIG } from '../config.js';
import { toMin, minToStr, parseDur, _festDate, festivalEnded } from '../domain/time.js';
import { _resolveVenue } from '../domain/festival.js';
import { effectiveDuration, screeningPassed, _djb2, _titleSeed, _mulberry32, shuffle, scoreFilm } from '../domain/film.js';
import { screensConflict, isScreeningBlocked, sortScreensByStrategy, computeScenarios } from '../domain/schedule.js';
import { renderAgenda } from '../view/agenda.js';
import { showToast } from '../view/feedback.js';
import { t } from '../i18n/i18n.js';

// ── Sprint 3: funciones puras que el Worker extrae del main thread ────────
// Al añadir o modificar una función de scheduling en el main thread,
// el Worker la recibe automáticamente. Sin copia manual, sin divergencia.
// EXCLUIDAS de extracción: simNow, festivalEnded — usan globals con nombre
// diferente en worker scope (_simTime→SIM_TIME, FESTIVAL_END→FESTIVAL_END_TS).
// Estas se proveen como worker-local en _mkCalcWorker._venueFns.
const _SCHED_PURE_FNS = [
  'toMin','minToStr','parseDur','_festDate','_resolveVenue',
  'effectiveDuration','screensConflict','screeningPassed',
  'isScreeningBlocked','_djb2','_titleSeed','_mulberry32',
  'shuffle','scoreFilm','sortScreensByStrategy','computeScenarios'
];

function _mkCalcWorker(){
  try{
    // Globals worker-local (no acceso al main thread en Worker scope)
    const _workerGlobals=`
let FILMS=[], FESTIVAL_DATES={}, availability={};
let watched=new Set(), prioritized=new Set();
let TZ_OFFSET='-05:00', FESTIVAL_END_TS=0, SIM_TIME=null;
const DEFAULT_DURATION_MIN=90;
const FESTIVAL_BUFFER=15;
let _venueCoords={};
let _transport='transit';
`;
    // Funciones de venue — usan _venueCoords/_transport (estado worker-local)
    // simNow/festivalEnded — usan SIM_TIME/FESTIVAL_END_TS (nombres worker-local)
    // Estas no se extraen del main thread via .toString() por diferencia de globals.
    const _venueFns=`
function simNow(){return SIM_TIME?new Date(SIM_TIME):new Date();}
function festivalEnded(){return simNow()>new Date(FESTIVAL_END_TS);}
function _workerFindCoords(v){
  return _resolveVenue(v,_venueCoords);
}
function venueTravelMins(v1,v2){
  const c1=_workerFindCoords(v1),c2=_workerFindCoords(v2);
  if(!c1.lat||!c1.lng||!c2.lat||!c2.lng) return 0;
  const dlat=(c1.lat-c2.lat)*111,dlon=(c1.lng-c2.lng)*111*Math.cos(c1.lat*Math.PI/180);
  const km=Math.sqrt(dlat*dlat+dlon*dlon);
  if(km<0.15) return 0;
  const spd=_transport==='walking'?4:_transport==='transit'?10:12;
  return Math.max(5,Math.round(km/spd*60/5)*5);
}
function travelMins(venueA,venueB){ return venueTravelMins(venueA,venueB); }
`;
    // Extraer funciones puras del main thread via .toString()
    // Garantía: el Worker usa EXACTAMENTE el mismo código que el main thread.
    const _pureFns=_SCHED_PURE_FNS.map(name=>{
      const fn=eval(name); // eslint-disable-line no-eval
      return (typeof fn==='function')?fn.toString():'/* MISSING: '+name+' */';
    }).join('\n');
    // Handler worker-specific
    const _handler=`
self.onmessage=function(e){
  const d=e.data;
  FILMS=d.films;
  watched=new Set(d.watched);
  prioritized=new Set(d.prioritized);
  availability=d.availability;
  FESTIVAL_DATES=d.festivalDates;
  TZ_OFFSET=d.tzOffset||'-05:00';
  FESTIVAL_END_TS=d.festivalEndTs;
  SIM_TIME=d.simTime;
  _venueCoords=d.venueCoords||{};
  _transport=d.transport||'transit';
  try{
    const scenarios=computeScenarios(d.titles);
    self.postMessage({ok:true,scenarios});
  }catch(err){
    self.postMessage({ok:false,error:err.message});
  }
};
`;
    const src=_workerGlobals+_venueFns+_pureFns+_handler;
    const blob=new Blob([src],{type:'application/javascript'});
    const url=URL.createObjectURL(blob);
    const w=new Worker(url);
    URL.revokeObjectURL(url);
    return w;
  }catch(e){console.warn('[Worker] build failed:',e);return null;}
}

// Worker activo — referencia para cancelar si el tab va a background
let _activeCalcWorker=null;

// iOS: si el tab va a background con Worker corriendo, limpiar estado
document.addEventListener('visibilitychange',function(){
  if(document.hidden&&_activeCalcWorker){
    _activeCalcWorker.terminate();
    _activeCalcWorker=null;
    const btn=document.querySelector('.av-calc-btn');
    if(btn){btn.disabled=false;btn.textContent=t('av_ver_opciones');}
  }
});

export function runCalc(){
  if(festivalEnded()){showToast(t('notice_fest_term'),'info');return;}
  // Cancelar Worker previo si existe
  if(_activeCalcWorker){_activeCalcWorker.terminate();_activeCalcWorker=null;}
  cachedResult=null;
  const btn=document.querySelector('.av-calc-btn');
  const res=document.getElementById('ag-result');
  if(btn){btn.disabled=true;btn.textContent=t('plan_calculando');}
  if(res) res.innerHTML=`<div class="ag-calc-prompt" style="opacity:.6">${t('plan_calculando_ops')}</div>`;

  // Build venue coords for Worker
  const _vcoords={};
  const _vcfg=(FESTIVAL_CONFIG[_activeFestId]||{}).venues||{};
  Object.entries(_vcfg).forEach(([k,v])=>{if(v.lat&&v.lng) _vcoords[k]={lat:v.lat,lng:v.lng};});

  const worker=_mkCalcWorker();
  if(worker){
    _activeCalcWorker=worker;
    const _prioSnap=[...prioritized]; // snapshot de prioridades al momento del cálculo (detección stale)
    // Watchdog: 15s timeout — previene Worker colgado en mobile
    const watchdog=setTimeout(()=>{
      if(_activeCalcWorker===worker){
        worker.terminate();
        _activeCalcWorker=null;
        console.warn('[Worker] timeout — falling back to main thread');
        _runCalcSync(btn,res);
      }
    },15000);
    // Web Worker path — non-blocking
    worker.onmessage=function(e){
      clearTimeout(watchdog);
      _activeCalcWorker=null;
      worker.terminate();
      if(btn){btn.disabled=false;btn.textContent=t('av_ver_opciones');}
      if(e.data.ok){
        const scenarios=e.data.scenarios;
        cachedResult={scenarios,currentIdx:0,_algorithmCount:scenarios.length,_prioSnapshot:_prioSnap};
        renderAgenda(); // re-render Planear → Estado 2 (corpus muta + strip resuelto + resultado)
      }else{
        if(res) res.innerHTML=`<div class="ag-calc-prompt" style="color:var(--red)"><strong>${t('error_calcular')}</strong><br><code class="txt-xs">${e.data.error}</code></div>`;
      }
    };
    worker.onerror=function(err){
      clearTimeout(watchdog);
      _activeCalcWorker=null;
      worker.terminate();
      console.warn('[Worker] error, falling back to main thread',err);
      _runCalcSync(btn,res);
    };
    worker.postMessage({
      titles:[...watchlist],
      films:FILMS,
      watched:[...watched],
      prioritized:[...prioritized],
      availability,
      festivalDates:FESTIVAL_DATES,
      tzOffset:TZ_OFFSET,
      festivalEndTs:FESTIVAL_END.getTime(),
      simTime:_simTime,
      venueCoords:_vcoords,
      transport:FESTIVAL_TRANSPORT
    });
  }else{
    // Fallback: main thread con setTimeout
    setTimeout(()=>_runCalcSync(btn,res),80);
  }
}

function _runCalcSync(btn,res){
  try{
    const scenarios=computeScenarios([...watchlist]);
    cachedResult={scenarios,currentIdx:0,_algorithmCount:scenarios.length,_prioSnapshot:[...prioritized]};
    renderAgenda(); // re-render Planear → Estado 2 (corpus muta + strip resuelto + resultado)
  }catch(err){
    if(res) res.innerHTML=`<div class="ag-calc-prompt" style="color:var(--red)"><strong>${t('error_calcular')}</strong><br><code class="txt-xs">${err.message}</code></div>`;
  }finally{
    if(btn){btn.disabled=false;btn.textContent=t('av_ver_opciones');}
  }
}
