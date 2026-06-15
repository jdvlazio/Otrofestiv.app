// ── src/controller/pipeline.js ─────────────────────────────────────────────────
// p8 Step 7c — Render pipeline / dispatchers de controller. renderActiveView rutea
// por activeMNav a los renderers de view. Importa view + domain + state + calc
// (runCalc). Cero lets unbridged (todo viewstate ya bridgeado). Sin ciclos:
// view no importa controller; calc es leaf.

import { FESTIVAL_CONFIG } from '../config.js';
import { ICONS, _secLabelFull } from '../view/components.js';
import { _renderProgramaContent, renderProgramaChips } from '../view/programa.js';
import { _fixStickyOffset, renderAgenda, renderFilmListHTML } from '../view/agenda.js';
import { runCalc } from './calc.js';
import { _renderSplashDropdown, _renderFestivalSelector } from './festival.js';
import { dayFullyPassed, festivalEnded, simNow, simTodayStr } from '../domain/time.js';
import { screeningPassed } from '../domain/film.js';
import { state } from '../state/state.js';
import { storage } from '../storage/storage.js';
import { t, _I18N, _applyI18nDOM } from '../i18n/i18n.js';

// Sentinel: toggles de prioridad NO deben nular cachedResult ni auto-recalcular
// — el resultado se preserva para detectar "stale" (prio strip Estado 3).
let _preserveResult=false;
export function _markPreserveResult(){ _preserveResult=true; }

export function renderActiveView(){
  if(_preserveResult){
    _preserveResult=false;                    // consumir flag
    // No nular cachedResult, no auto-runCalc: preservar para detección stale.
    if(activeView==='day' && activeMNav==='mnav-cartelera'){
      const pelOpen = document.getElementById('pel-sheet')?.classList.contains('open');
      if(!pelOpen) _renderProgramaContent();
      return;
    }
    renderAgenda();                           // planner → Estado 1/3; seleccion/miplan
    return;
  }
  cachedResult = null;                        // state cambió → cache de schedule stale
  if(activeView==='day' && activeMNav==='mnav-cartelera'){
    const pelOpen = document.getElementById('pel-sheet')?.classList.contains('open');
    if(!pelOpen) _renderProgramaContent(); // re-render por estado → resetScroll=false preserva scroll
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
  _renderProgramaContent(true); // entrar a vista día → scroll al tope
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
  // Pill: emoji + label localizado (EN→SECTION_EN, ES→original con emoji).
  if(!sec||sec==='all') return sec;
  return _secLabelFull(sec);
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
    pills+='<div class="paf-pill" data-action="pafClearSec">'+lbl+'<span class="paf-pill-x">×</span></div>';
  }
  if(hasVenue){
    pills+='<div class="paf-pill" data-action="pafClearVenue">'+ICONS.pin+' '+activeVenue+'<span class="paf-pill-x">×</span></div>';
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

// p8 Step 8d-3: setLang reubicado desde main.js. Orquestador mutate→render del
// cambio de idioma. Lee activeView/_splashSelectedFestId/_activeFestId vía bridge
// (globalThis). main.js lo importa de vuelta para ACTION_REGISTRY (data-action).
export function setLang(code){
  // 1. READ + 2. GUARD
  const {_lang, _activeFestId} = state.snapshot();
  if(!_I18N[code]) return;
  if(code === _lang) return;
  // Fade out content containers (UI effect inmediato)
  const _fadeEls=['programa-list','ag-view','grid'].map(id=>document.getElementById(id)).filter(Boolean);
  _fadeEls.forEach(el=>el.classList.add('lang-fade'));
  setTimeout(()=>{
    // 3. MUTATE (diferido tras fade-out)
    state.set('_lang', code);
    // 4. PERSIST
    storage.setLang(code);
    // 5. RENDER + UI EFFECTS — full DOM refresh + componentes dinámicos
    _applyI18nDOM();
    if(activeView === 'day') { typeof showDayView === 'function' && showDayView(); }
    else                     { typeof renderAgenda === 'function' && renderAgenda(); }
    // Sin festival elegido (placeholder) → null: re-renderiza el dropdown con las
    // secciones en el nuevo idioma pero NO rellena el selector (el placeholder
    // "Elegí uno" lo re-traduce _applyI18nDOM). Con festival elegido → localiza fechas.
    _renderSplashDropdown(_splashSelectedFestId);
    _renderFestivalSelector(_activeFestId);
    requestAnimationFrame(()=>{
      _fadeEls.forEach(el=>el.classList.remove('lang-fade'));
    });
  }, 200); // --tr-smooth = 200ms
}

// ── Lang toggle dropdown ──────────────────────────────────────────────────
// Shell de UI sobre setLang: abre/cierra el desplegable y delega el cambio de
// idioma en setLang(). No modifica setLang ni _applyI18nDOM. El highlight de
// la opción activa lo mantiene _applyI18nDOM (toggle .active en #lang-btn-es/en).
export function toggleLangDropdown(){
  const tog=document.getElementById('lang-toggle');
  const trg=document.getElementById('lang-trigger');
  const dd=document.getElementById('lang-dropdown');
  if(!tog||!trg||!dd) return;
  const open=!tog.classList.contains('open');
  if(!open){ closeLangDropdown(); return; }
  tog.classList.add('open');
  trg.setAttribute('aria-expanded', 'true');
  // El topbar (position:sticky; z-index:200) crea un stacking context que atrapa
  // al dropdown — su z-index:201 es local y la barra de filtros (z-index:201 a
  // nivel root) pinta encima. Para escapar: mover el dropdown al <body> y
  // posicionarlo fixed bajo el trigger — mismo patrón que seccion-drop/lugar-drop.
  const r=trg.getBoundingClientRect();
  dd.style.position='fixed';
  dd.style.top=(r.bottom+4)+'px';
  dd.style.right=(window.innerWidth-r.right)+'px';
  dd.style.zIndex='9999';
  dd.style.display='block'; // el selector CSS .lang-toggle.open ya no aplica en <body>
  document.body.appendChild(dd);
  setTimeout(()=>{ document.addEventListener('click', langOutside); }, 0);
}

export function closeLangDropdown(){
  const tog=document.getElementById('lang-toggle');
  const trg=document.getElementById('lang-trigger');
  const dd=document.getElementById('lang-dropdown');
  if(tog) tog.classList.remove('open');
  if(trg) trg.setAttribute('aria-expanded', 'false');
  if(dd && tog){
    dd.removeAttribute('style');   // limpia position/top/right/zIndex/display inline
    tog.appendChild(dd);            // re-parent dentro del toggle (vuelve a display:none por CSS)
  }
  document.removeEventListener('click', langOutside);
}

export function langOutside(e){
  // El dropdown vive en <body> mientras está abierto, no dentro de .lang-toggle:
  // chequear contra el dropdown y el trigger directamente.
  const dd=document.getElementById('lang-dropdown');
  const trg=document.getElementById('lang-trigger');
  if(dd && !dd.contains(e.target) && trg && !trg.contains(e.target)) closeLangDropdown();
}

export function selectLang(el){
  const code=el && el.dataset ? el.dataset.code : null;
  if(!code) return;
  // Reflejar la bandera en el trigger cerrado (inmediato, sin depender de _applyI18nDOM)
  const flag=el.querySelector('.lang-opt-flag');
  const trgFlag=document.getElementById('lang-trigger-flag');
  if(flag && trgFlag) trgFlag.textContent=flag.textContent;
  closeLangDropdown();
  setLang(code);
}

// Inicializa la bandera del trigger desde la opción activa (marcada por
// _applyI18nDOM en boot). Llamado una vez en el bootstrap.
export function _syncLangTrigger(){
  const active=document.querySelector('#lang-dropdown .lang-opt.active .lang-opt-flag');
  const trgFlag=document.getElementById('lang-trigger-flag');
  if(active && trgFlag) trgFlag.textContent=active.textContent;
}
