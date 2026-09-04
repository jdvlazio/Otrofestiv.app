// ── src/controller/pipeline.js ─────────────────────────────────────────────────
// p8 Step 7c — Render pipeline / dispatchers de controller. renderActiveView rutea
// por activeMNav a los renderers de view. Importa view + domain + state + calc
// (runCalc). Cero lets unbridged (todo viewstate ya bridgeado). Sin ciclos:
// view no importa controller; calc es leaf.

import { FESTIVAL_CONFIG } from '../config.js';
import { ICONS, _secLabelFull } from '../view/components.js';
import { venueSelLabel } from '../view/helpers.js';
import { _renderProgramaContent, renderProgramaChips, scrollDtabsToActive } from '../view/programa.js';
import { _fixStickyOffset, renderAgenda, renderFilmListHTML } from '../view/agenda.js';
import { runCalc } from './calc.js';
import { _renderSplashRail, _renderFestivalSelector, renderPostponedBanner, renderFestBar } from './festival.js';
import { dayFullyPassed, festivalEnded, simNow, simTodayStr } from '../domain/time.js';
import { screeningPassed } from '../domain/film.js';
import { state } from '../state/state.js';
import { storage } from '../storage/storage.js';
import { t, LANGS, _applyI18nDOM } from '../i18n/i18n.js';

export function renderActiveView(){
  // El resultado ya NO se anula en cada cambio (Juan, 18 ago): «que el Plan que
  // estás mirando nunca cambie solo». Antes, cambiar un interés lo destruía y
  // recalculaba en silencio, mientras cambiar una prioridad lo conservaba y
  // avisaba — dos gestos vecinos, leyes opuestas. Ahora se conserva siempre y la
  // vista compara la firma de insumos (planInputSignature) para decir si quedó
  // desactualizado. Recalcular es del usuario.
  if(activeView==='day' && activeMNav==='mnav-cartelera'){
    const pelOpen = document.getElementById('pel-sheet')?.classList.contains('open');
    if(!pelOpen) _renderProgramaContent(); // re-render por estado → resetScroll=false preserva scroll
    return;
  }
  if(activeMNav==='mnav-planner'){
    // MISMO gate que el auto-cálculo de showAgView: si no queda nada
    // planificable, runCalc solo produce una cáscara de cero escenarios que
    // pisa la pantalla «Nada por planear» con un «Sin combinaciones» que culpa
    // al armado cuando la verdad es temporal. Sin material, se re-rutea a
    // showAgView, que ya distingue las tres situaciones del vacío.
    const _p=[...watchlist].some(t=>!watched.has(t)&&FILMS.some(f=>f.title===t&&!screeningPassed(f)));
    // Con un resultado en pantalla NO se recalcula solo: se re-renderiza y la
    // firma de insumos lo marcará desactualizado si algo cambió. Sin resultado,
    // el primer cálculo sí es automático: no hay ningún Plan que arruinar.
    if(_p&&!cachedResult) runCalc(); else showAgView();
    return;
  }
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
  requestAnimationFrame(()=>{
    _fixStickyOffset(); // actualiza altura del chrome-blur
    // ENTRAR a Programa reposiciona la barra de días: hoy y mañana a la vista
    // (Juan, 18 ago). Antes solo corría al CARGAR el festival, así que volver
    // desde otra pestaña dejaba la barra donde el usuario la hubiera empujado.
    scrollDtabsToActive();
  });
}

export function showAgView(){
  activeView='agenda';
  const _toggle=document.getElementById('carta-mode-toggle');if(_toggle) _toggle.style.display='none';
  const _mbar=document.getElementById('programa-mode-bar');if(_mbar) _mbar.style.display='none';
  const _chips=document.getElementById('programa-chips');if(_chips) _chips.classList.add('hidden');
  const _paf=document.getElementById('programa-active-filter');if(_paf) _paf.classList.remove('visible');
  const _lista=document.getElementById('programa-list');if(_lista) _lista.classList.remove('visible');
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
  // Al ENTRAR a Planear sin resultado en memoria, calcular solo.
  //
  // El escenario vive en memoria (viewstate) y muere al recargar: medido el
  // 16 ago con FICDEH — 4 filas antes, 0 después, sin aviso, mientras los
  // intereses seguían intactos. Lo que se perdía no era el trabajo del usuario
  // sino una DERIVACIÓN de ese trabajo, y recalcularla cuesta 2–3 ms (medido con
  // 8 y con 20 intereses). Por eso NO se persiste: guardar la derivación sería
  // una segunda verdad que además se pone rancia sola (una función se cancela,
  // cambia el filtro de ciudad) y te mostraría un plan que ya no es cierto.
  //
  // Con plan YA guardado no se toca nada: aparecer con una opción nueva sin
  // pedirla invita a reemplazar lo que el usuario curó a mano. Ahí manda el botón.
  if(activeMNav==='mnav-planner'&&!cachedResult&&!festivalEnded()){
    const _sa=savedAgenda&&savedAgenda.schedule&&savedAgenda.schedule.length;
    // MISMO criterio que `pending` en la vista (agenda.js): interés sin ver Y
    // con alguna función futura. Contar solo «sin ver» calculaba con una lista
    // agotada, dejaba un cachedResult de cero escenarios y esa cáscara pisaba
    // la pantalla «Nada por planear» — el usuario veía «Sin combinaciones»
    // culpando al armado cuando la verdad era temporal (todo lo suyo ya pasó).
    const _hayIntereses=[...watchlist].some(t=>!watched.has(t)&&FILMS.some(f=>f.title===t&&!screeningPassed(f)));
    if(!_sa&&_hayIntereses) runCalc();
  }
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
  // Prensa e Industria entra acá porque su botón es solo un icono: la barra a
  // 390px no admite una cuarta etiqueta, así que la palabra la pone la píldora.
  // Y sirve de recordatorio: el usuario está viendo pases a los que el público
  // general no entra, y puede apagarlo desde la misma × que los otros filtros.
  const hasPress=!!showPress;
  if(!hasSec&&!hasVenue&&!hasPress){af.classList.remove('visible');return;}
  let pills='';
  if(hasPress){
    pills+='<div class="paf-pill" data-action="togglePressScreenings">'+t('paf_prensa')+'<span class="paf-pill-x">×</span></div>';
  }
  if(hasSec){
    const lbl=_seccionPillLabel(activeSec);
    pills+='<div class="paf-pill" data-action="pafClearSec">'+lbl+'<span class="paf-pill-x">×</span></div>';
  }
  if(hasVenue){
    pills+='<div class="paf-pill" data-action="pafClearVenue">'+ICONS.pin+' '+venueSelLabel(activeVenue)+'<span class="paf-pill-x">×</span></div>';
  }
  af.innerHTML=pills;
  af.classList.add('visible');
}

// _syncPmodeTabs — la píldora Hoy/Mañana ESPEJA a su chip de día (16 ago 2026,
// hallazgo de la ronda 3 + observación de Juan). La píldora es doble: BOTÓN
// (el atajo que salta al día) e INDICADOR — y la mitad de indicador mentía por
// omisión: pintada desde programaSubMode, quedaba subrayada mostrando MAR 18,
// y nunca se atenuaba cuando su día ya no tenía nada. Ahora las dos dimensiones
// se derivan de lo mismo que el chip: activa si su día ES el día activo,
// opaca si su día está agotado (dayFullyPassed, el mismo dueño del .past del
// chip). El destino de cada píldora se calcula con las MISMAS fórmulas del
// atajo (setProgramaMode) para que indicador y botón nunca diverjan.
export function _syncPmodeTabs(){
  const _pts=simTodayStr();
  const _pti=DAY_KEYS.findIndex(d=>FESTIVAL_DATES[d]===_pts);
  const _keys={
    hoy: _pti>=0?DAY_KEYS[_pti]:DAY_KEYS[0],
    manana: _pti>=0&&_pti<DAY_KEYS.length-1?DAY_KEYS[_pti+1]:DAY_KEYS[DAY_KEYS.length-1],
  };
  ['hoy','manana'].forEach(m=>{
    const el=document.getElementById('pmode-'+m);
    if(!el) return;
    el.classList.toggle('on', activeDay===_keys[m]);
    el.classList.toggle('past', dayFullyPassed(_keys[m]));
  });
  // Y los chips se refrescan con el MISMO cálculo: al cruzar la medianoche o
  // agotarse el día, píldora y chip tienen que atenuarse JUNTOS (Juan, 16 ago).
  // Sin esto la píldora quedaba opaca y su chip brillante — la discrepancia
  // inversa a la que veníamos a arreglar, y la cazó el test.
  document.querySelectorAll('.dtab').forEach(t=>{
    if(t.dataset.day&&t.dataset.day!=='all') t.classList.toggle('past', dayFullyPassed(t.dataset.day));
  });
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
  // Tab activo/atenuado: derivado del día, no de programaSubMode (el espejo).
  _syncPmodeTabs();
  // Mostrar/ocultar chips
  const chipsEl=document.getElementById('programa-chips');
  if(chipsEl){
    chipsEl.classList.toggle('hidden',activeDay!=='all');
    if(activeDay==='all') renderProgramaChips();
  }
  // nav-row visible SOLO en Programa — misma condición que switchMainNav. El
  // remove('hidden') incondicional asumía que esta función solo corre en
  // Programa, pero el fix del compositor de iOS (loader.js) la re-ejecuta
  // ~830ms después de entrar al festival, y si para entonces estás en Mi Plan
  // (el salto automático del boot, o un toque rápido) la barra de días se
  // colaba en el tab equivocado. Cazado por Juan en producción, 18 ago 2026.
  const navRow=document.getElementById('nav-row');
  if(navRow) navRow.classList.toggle('hidden', activeMNav!=='mnav-cartelera');
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
  if(!LANGS.includes(code)) return; // solo idiomas ACTIVOS (no todo bloque de _I18N)
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
    // Re-renderiza el riel del splash con el idioma nuevo (divisor "Anteriores" +
    // fechas del info localizadas). Preserva la selección (_splashSelectedFestId).
    _renderSplashRail(_splashSelectedFestId);
    _renderFestivalSelector(_activeFestId);
    // Banda APLAZADO: persistente → no pasa por loadFestival; se rehornea acá con
    // la etiqueta/enlace del idioma nuevo (la cita del festival queda en ES).
    renderPostponedBanner(FESTIVAL_CONFIG[_activeFestId]);
    // El chip del encabezado tampoco pasa por loadFestival al cambiar idioma:
    // sin esto quedaba con las fechas en el orden del idioma anterior.
    renderFestBar(FESTIVAL_CONFIG[_activeFestId]);
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

// _syncLangTrigger fue absorbido por _applyI18nDOM (i18n.js): la bandera del
// trigger se sincroniza en el mismo pase que marca .active — una función menos
// que acordarse de llamar en el boot.
