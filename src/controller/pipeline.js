// ── src/controller/pipeline.js ─────────────────────────────────────────────────
// p8 Step 7c — Render pipeline / dispatchers de controller. renderActiveView rutea
// por activeMNav a los renderers de view. Importa view + domain + state + calc
// (runCalc). Cero lets unbridged (todo viewstate ya bridgeado). Sin ciclos:
// view no importa controller; calc es leaf.

import { FESTIVAL_CONFIG } from '../config.js';
import { ICONS } from '../view/components.js';
import { _renderProgramaContent, renderProgramaChips } from '../view/programa.js';
import { _fixStickyOffset, renderAgenda, renderFilmListHTML } from '../view/agenda.js';
import { runCalc } from './calc.js';
import { dayFullyPassed, festivalEnded, simNow, simTodayStr } from '../domain/time.js';
import { screeningPassed } from '../domain/film.js';
import { state } from '../state/state.js';
import { t } from '../i18n/i18n.js';

export function renderActiveView(){
  cachedResult = null;                        // state cambió → cache de schedule stale
  if(activeView==='day' && activeMNav==='mnav-cartelera'){
    const pelOpen = document.getElementById('pel-sheet')?.classList.contains('open');
    if(!pelOpen){ const sy=window.scrollY; _renderProgramaContent(); window.scrollTo(0,sy); }
    return;
  }
  if(activeMNav==='mnav-planner'){ runCalc(); return; }  // recompute scenarios + render
  renderAgenda();                             // rutea internamente seleccion/miplan
}

export function switchMainNav(id){
  if(id==='mnav-miplan') activeMiPlanDay=null; // recalcula día actual al entrar
  activeMNav=id;
  document.querySelectorAll('.main-nav-tab').forEach(t=>t.classList.remove('on'));
  const el=document.getElementById(id);if(el) el.classList.add('on');
  // nav-row solo visible en tab Programa
  const navRow=document.getElementById('nav-row');
  if(navRow) navRow.classList.toggle('hidden', id!=='mnav-cartelera');
}

export function showDayView(){
  activeView='day';
  switchMainNav('mnav-cartelera');
  // Mostrar buscador y mode bar
  document.getElementById('hdr-ag')?.style.setProperty('display','none');
  const modeBar=document.getElementById('programa-mode-bar');
  if(modeBar){
    modeBar.style.removeProperty('display');// removeProperty is more reliable than =""
    modeBar.setAttribute('data-sdv',Date.now());// tag for debugging
  }
  // Ocultar toggle legacy
  const toggle=document.getElementById('carta-mode-toggle');if(toggle) toggle.style.display='none';
  document.getElementById('filter-bars').style.display='';
  ['hint','cnt','grid','cartelera-stepper'].forEach(id=>{const el=document.getElementById(id);if(el) el.style.display='';});
  const _av=document.getElementById('ag-view');
  _av.classList.remove('visible');
  _av.style.display='none';
  document.getElementById('agtab').classList.remove('on');
  // Inicializar el sistema de modos
  initProgramaModeBar();
  _renderProgramaContent();
  requestAnimationFrame(_fixStickyOffset); // actualiza altura del chrome-blur
}

export function showAgView(){
  activeView='agenda';
  const _toggle=document.getElementById('carta-mode-toggle');if(_toggle) _toggle.style.display='none';
  const _mbar=document.getElementById('programa-mode-bar');if(_mbar) _mbar.style.display='none';
  const _chips=document.getElementById('programa-chips');if(_chips) _chips.classList.add('hidden');
  const _paf=document.getElementById('programa-active-filter');if(_paf) _paf.classList.remove('visible');
  const _lista=document.getElementById('programa-list');if(_lista) _lista.classList.remove('visible');
  const _agH=document.getElementById('hdr-ag');
  if(_agH){
    _agH.style.display='';
    // ag-toggle-bar eliminado de Intereses (solo en Explorar)
  }
  document.getElementById('filter-bars').style.display='none';
  ['hint','cnt','grid','cartelera-stepper'].forEach(id=>{const el=document.getElementById(id);if(el) el.style.display='none';});
  const _av=document.getElementById('ag-view');
  _av.style.display='';
  _av.classList.add('visible');
  // Trigger lazy image loading for newly visible content
  requestAnimationFrame(()=>window.dispatchEvent(new Event('scroll')));
  _av.scrollTop=0;
  document.getElementById('agtab').classList.add('on');
  document.querySelectorAll('.dtab').forEach(t=>t.classList.remove('on'));
  renderAgenda();
  requestAnimationFrame(_fixStickyOffset); // actualiza altura del chrome-blur
}

export function updateAgTab(){
  // Count: in watchlist, not watched, and has future screenings
  const future=[...watchlist].filter(t=>{
    if(watched.has(t)) return false;
    return FILMS.some(f=>f.title===t&&!screeningPassed(f));
  });
  const el=document.getElementById('ag-cnt');if(el) el.textContent=future.length;
  const tab=document.getElementById('agtab');if(tab) tab.classList.toggle('on',activeView==='agenda');
}

export function _reRenderIntereses(){
  _rerenderFilmList();
}

export function _rerenderFilmList(){
  const lel=document.getElementById('ag-film-list');
  if(!lel) return;
  lel.innerHTML=renderFilmListHTML(state);
  // Recompute pill counts — filter sobre Sets, O(n) trivial. Mismo cálculo
  // que la pure half hace; se duplica para mantener purity de renderFilmListHTML.
  const {prioritized, watched, watchlist, PRIO_LIMIT} = state.snapshot();
  const prioList=[...prioritized].filter(titleStr=>!watched.has(titleStr));
  const nonPrioList=[...watchlist].filter(titleStr=>!watched.has(titleStr)&&!prioritized.has(titleStr));
  const watchedList=[...watched];
  setTimeout(()=>{
    const _pp=document.getElementById('pill-prio-cnt');if(_pp) _pp.textContent=prioList.length?`${prioList.length}/${PRIO_LIMIT}`:'—';
    const _pi=document.getElementById('pill-int-cnt');if(_pi) _pi.textContent=nonPrioList.length?String(nonPrioList.length):'—';
    const _py=document.getElementById('pill-yv-cnt');if(_py) _py.textContent=watchedList.length?String(watchedList.length):'—';
    document.getElementById('pill-prio')?.style.setProperty('display',prioList.length?'inline-flex':'none');
    document.getElementById('pill-int')?.style.setProperty('display',nonPrioList.length?'inline-flex':'none');
    document.getElementById('pill-yv')?.style.setProperty('display',watchedList.length?'inline-flex':'none');
  },0);
}

export function _getProgramaPhase(){
  // Retorna qué tabs deben ser visibles y cuál es el default
  // Explorar eliminado — dtab TODO cubre ese caso
  if(festivalEnded()) return {tabs:[],default:'hoy'};
  const now=simNow();
  const firstDayKey=DAY_KEYS[0];
  const firstDayDate=FESTIVAL_DATES[firstDayKey];
   const _tzOff=(FESTIVAL_CONFIG[_activeFestId]||{}).timezoneOffset||'-05:00';
   const FEST_START=firstDayDate?new Date(firstDayDate+'T09:00:00'+_tzOff):new Date('2099-01-01');
  if(now<FEST_START) return {tabs:[],default:'hoy'};
  const todayStr=simTodayStr();
  const lastDayKey=DAY_KEYS[DAY_KEYS.length-1];
  const isLastDay=todayStr===FESTIVAL_DATES[lastDayKey];
  const tabs=isLastDay?['hoy']:['hoy','manana'];
  return{tabs,default:'hoy'};
}

export function _seccionPillLabel(sec){
  // Pill: nombre completo tal como viene en el JSON — ya incluye emoji
  if(!sec||sec==='all') return sec;
  return sec;
}

export function _updateProgramaActiveFilter(){
  const af=document.getElementById('programa-active-filter');
  if(!af) return;
  const hasSec=activeSec!=='all';
  const hasVenue=activeVenue!=='all';
  if(!hasSec&&!hasVenue){af.classList.remove('visible');return;}
  let pills='';
  if(hasSec){
    const lbl=_seccionPillLabel(activeSec);
    pills+='<div class="paf-pill" data-action="_pafClearSec">'+lbl+'<span class="paf-pill-x">×</span></div>';
  }
  if(hasVenue){
    pills+='<div class="paf-pill" data-action="_pafClearVenue">'+ICONS.pin+' '+activeVenue+'<span class="paf-pill-x">×</span></div>';
  }
  af.innerHTML=pills;
  af.classList.add('visible');
}

export function initProgramaModeBar(){
  const phase=_getProgramaPhase();
  // Mostrar/ocultar tabs según fase
  ['hoy','manana'].forEach(m=>{
    const el=document.getElementById('pmode-'+m);
    if(!el) return;
    el.style.display=phase.tabs.includes(m)?'':'none';
  });
  // Si el sub-modo actual no está disponible, resetear al default
  if(!phase.tabs.includes(programaSubMode)){
    programaSubMode=phase.default;
  }
  // Actualizar tab activo
  ['hoy','manana'].forEach(m=>{
    const el=document.getElementById('pmode-'+m);
    if(el) el.classList.toggle('on',m===programaSubMode);
  });
  // Mostrar/ocultar chips
  const chipsEl=document.getElementById('programa-chips');
  if(chipsEl){
    chipsEl.classList.toggle('hidden',activeDay!=='all');
    if(activeDay==='all') renderProgramaChips();
  }
  // nav-row siempre visible en Programa — dtabs son la navegación temporal
  const navRow=document.getElementById('nav-row');
  if(navRow) navRow.classList.remove('hidden');
  document.querySelectorAll('.dtab').forEach(t=>{
    t.classList.toggle('on', activeDay==='all' ? t.dataset.day==='all' : t.dataset.day===activeDay);
    t.classList.toggle('past', t.dataset.day!=='all' && dayFullyPassed(t.dataset.day));
  });
  // tag dismissible
  _updateProgramaActiveFilter();
}
