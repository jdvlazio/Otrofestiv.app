// ── src/controller/handlers.js ────────────────────────────────────────────────
// p8 Step 7d-3 — Capa orquestadora del controller (último del controller-core):
// mutators (toggleWL/setDelay/...) + filters (filterByX/setProgramaX) + composites
// (_closePelAndRemove/_navTo/...) + scenario ops. Importa overlays + sheets-
// controller + pipeline + persistence + calc + view. normTitle/selectedIdx vía
// bridge. _ctaRemovedTimer module-local; PROGRAMA_CHIPS const privado.

import { FESTIVAL_CONFIG, MAX_REMEMBERED_SLOTS } from '../config.js';
import { ICONS, parseProgramTitle } from '../view/components.js';
import { closeAuthSheet, closePrioLimit } from '../view/sheets.js';
import { showActionModal, showToast } from '../view/feedback.js';
import { _renderProgramaContent, lugarClose, render, renderNoticesBanner, _noticeKey } from '../view/programa.js';
import { renderAgenda, updateCardState, updateHorarioPrioBtn } from '../view/agenda.js';
import { runCalc } from './calc.js';
import { saveDelays, saveLastSlot, savePrio, saveSavedAgenda, saveState, saveWL, saveWatched } from './persistence.js';
import { cloudReportDelay, cloudClearDelay, cloudScreeningKey } from './delays-cloud.js';
import { _getProgramaPhase, _reRenderIntereses, _updateProgramaActiveFilter, initProgramaModeBar, showAgView, showDayView, switchMainNav, updateAgTab, _markPreserveResult } from './pipeline.js';
import { searchClose, seccionClose } from './overlays.js';
import { dayFullyPassed, festivalEnded, simTodayStr, toMin } from '../domain/time.js';
import { scoreFilm, screeningPassed } from '../domain/film.js';
import { isScreeningBlocked, screensConflict, sortScreensByStrategy } from '../domain/schedule.js';
import { state } from '../state/state.js';
import { storage } from '../storage/storage.js';
import { t } from '../i18n/i18n.js';
import { _removePlanItem, closePelSheet, openConflictSheet, openCortoSheet, openPelSheet, openPlanConfirm, openPostViewRating, openPrioLimit, openRatingSheet, showActionToast } from './sheets-controller.js';

// ── module-local + const privado ─────────────────────────────────────────────
let _ctaRemovedTimer=null;
const PROGRAMA_CHIPS=[
  {id:'all',      label:'Todo',              match:null},
  {id:'colombia', label:'🇨🇴 Colombia',     match:s=>s.includes('Colombia')},
  {id:'ibero',    label:'🌎 Iberoamérica',  match:s=>s.includes('Iberoamérica')},
  {id:'inter',    label:'🌍 Internacional',  match:s=>s.includes('Internacional')},
  {id:'spaces',   label:'⏳ (s)paces',      match:s=>s.includes('paces')},
  {id:'afro',     label:'✊ Afro',           match:s=>s.includes('Afro')},
  {id:'indigena', label:'🪶 Indígena',       match:s=>s.includes('Indígena')},
  {id:'barrios',  label:'🏆 Barrios',        match:s=>s.includes('Barrios')},
  {id:'costas',   label:'🌊 Costas',         match:s=>s.includes('Costas')},
  {id:'rivers',   label:'🎖️ Ben Rivers',    match:s=>s.includes('Rivers')},
  {id:'retro',    label:'📽️ Retrospectiva', match:s=>s.includes('Retrospectiva')},
  {id:'midnight', label:'🌙 Medianoche',    match:s=>s.includes('Medianoche')},
  {id:'españa',   label:'🇪🇸 Muestra España',  match:s=>s.includes('España')},
  {id:'suiza',    label:'🇨🇭 Muestra Suiza',   match:s=>s.includes('Suiza')},
  {id:'argentina',label:'🇦🇷 Muestra Argentina',match:s=>s.includes('Argentina')},
  {id:'brasil',   label:'🇧🇷 Casa Brasil',      match:s=>s.includes('Brasil')},
  {id:'especial', label:'⭐ Especiales',     match:s=>s.includes('Especiales')||s.includes('Animación')||s.includes('Indias')},
];

export function toggleWL(title,e){
  if(e) e.stopPropagation();
  // 1. READ
  const {FILMS, prioritized, savedAgenda, watched, watchlist} = state.snapshot();
  // 2. GUARD + 3. MUTATE — branch A: remove con modal si en savedAgenda
  if(watchlist.has(title)){
    if(savedAgenda&&savedAgenda.schedule.some(s=>s._title===title)){
      showActionModal(t('plan_quitar_intereses'),
        `<b>${title.length>36?title.slice(0,34)+'…':title}</b> ${t('plan_esta_en_tu_plan')}<br><br>${t('plan_quitar_tmb')}`,
        t('plan_quitar_confirm'),()=>{
          // Modal callback variant — transaction agrupa las 3 mutaciones (p7d)
          state.transaction(() => {
            state.update('savedAgenda', a => ({...a, schedule: a.schedule.filter(s=>s._title!==title)}));
            if(!savedAgenda.schedule.length)state.set('savedAgenda', null);
            state.batchUpdate({
              watchlist: state._delFromSet(watchlist, title),
              watched: state._delFromSet(watched, title),
              prioritized: state._delFromSet(prioritized, title),
            });
          });
          saveSavedAgenda();
          saveState('wl','watched');updateCardState(title);   // render automático vía pipeline
        });return;
    }
    // Branch B: remove directo (film NO en savedAgenda)
    state.batchUpdate({
      watchlist: state._delFromSet(watchlist, title),
      watched: state._delFromSet(watched, title),
      prioritized: state._delFromSet(prioritized, title),
    });
    showToast(t('toast_fuera_intereses'),'info');
  }
  else{
    // Branch C: add — con detección "todas funciones bloqueadas" + UI variants
    state.batchUpdate({
      watchlist: state._addToSet(watchlist, title),
      watched: state._delFromSet(watched, title),
    });
    const _allScreens=FILMS.filter(f=>f.title===title&&!screeningPassed(f));
    const _allBlocked=_allScreens.length>0&&_allScreens.every(s=>isScreeningBlocked(s));
    if(_allBlocked){
      const{displayTitle}=parseProgramTitle(title);
      const _short=displayTitle.length>28?displayTitle.slice(0,26)+'…':displayTitle;
      setTimeout(()=>showToast(`"${_short}" ${t('plan_bloqueado_disp')}`,'warn',5000),300);
    } else if(activeMNav==='mnav-cartelera'||activeMNav==='mnav-seleccion'){
      showActionToast(`${ICONS.heartFill} ${t('cta_en_intereses')}`,`${ICONS.star} ${t('cta_priorizar')}`,()=>togglePriority(title));
    } else {
      showToast(`${ICONS.heartFill} ${t('cta_en_intereses')}`,'info');
    }
  }
  // 4. PERSIST + surgical patch (branch B y C). Render automático vía pipeline.
  saveState('wl','watched');updateCardState(title);
}

export function toggleWatched(title,e){
  title=normTitle(title);
  if(e) e.stopPropagation();
  // 1. READ
  const {FILMS, watched, watchlist} = state.snapshot();
  // 2. GUARD + 3. MUTATE — branch A: ya watched, desmarcar y devolver a Intereses
  if(watched.has(title)){
    state.batchUpdate({
      watched: state._delFromSet(watched, title),
      watchlist: state._addToSet(watchlist, title),
    });
    // 4. PERSIST + surgical (render automático vía pipeline)
    saveState('wl','watched');
    updateCardState(title);
    _reRenderIntereses();
    showToast(t('plan_vuelta_pendientes'),'info');
    return;
  }
  // Branch B: marcar como vista — modal confirm (closure variant)
  const _short=title.length>36?title.slice(0,34)+'…':title;
  showActionModal(
    t('modal_ya_viste_titulo'),
    `<b>${_short}</b><br><br>${t('modal_ya_viste_body')}`,
    t('modal_ya_viste_cta'),
    ()=>{
      state.update('watched', s => state._addToSet(s, title));
      saveWatched();updateCardState(title);
      _reRenderIntereses();
      showToast(t('toast_marcada_vista'),'info');
      const _f=FILMS.find(fi=>fi.title===title);
      if(_f?.is_cortos&&_f.film_list?.length){ closePelSheet(); setTimeout(()=>openPostViewRating(title),350); }
      else if(!_f?.is_cortos) setTimeout(()=>openRatingSheet(title),350);
    }
  );
}

export function togglePelPrio(title){
  title=normTitle(title);
  togglePriority(title);
  const btn=document.getElementById('pel-prio-btn')||document.getElementById('corto-prio-btn');
  if(!btn) return;
  const inPrio=prioritized.has(title);
  btn.innerHTML=(inPrio?ICONS.starFill:ICONS.star)+' '+(inPrio?t('cta_priorizada'):t('cta_priorizar'));
  btn.className='pel-sheet-action-btn'+(inPrio?' act-prio':' btn-secondary');
  // Priorizar auto-añade a watchlist — sincronizar el botón de Intereses
  const inWL=watchlist.has(title);
  const pelWlBtn=document.getElementById('pel-wl-btn');
  if(pelWlBtn){
    pelWlBtn.innerHTML=(inWL?ICONS.heartFill:ICONS.heart)+' '+(inWL?t('cta_en_intereses'):t('cta_intereses'));
    pelWlBtn.className='pel-sheet-action-btn'+(inWL?' act-on btn-primary':' btn-primary');
  }
  const cortoWlBtn=document.getElementById('corto-wl-btn');
  if(cortoWlBtn){
    cortoWlBtn.innerHTML=(inWL?ICONS.heartFill:ICONS.heart)+' '+(inWL?t('cta_en_intereses'):t('cta_intereses'));
    cortoWlBtn.className='pel-sheet-action-btn'+(inWL?' act-on btn-primary':' btn-primary');
  }
}

export function togglePelWL(title,e){
  title=normTitle(title);
  const wasInWL=watchlist.has(title);
  toggleWL(title,e);
  const btn=document.getElementById('pel-wl-btn');
  if(!btn) return;
  const inWL=watchlist.has(title);
  btn.innerHTML=(inWL?ICONS.heartFill:ICONS.heart)+' '+(inWL?t('cta_en_intereses'):t('cta_intereses'));
  btn.className='pel-sheet-action-btn'+(inWL?' act-on btn-primary':' btn-primary');
  if(wasInWL&&!inWL) closePelSheet(); // quitar de intereses → cerrar sheet
  if(!wasInWL&&inWL){
    showActionToast(`${ICONS.heartFill} ${t('cta_en_intereses')}`,`${ICONS.star} ${t('cta_priorizar')}`,()=>togglePriority(title));
  }
}

export function setDelay(title,day,time,addMins,venue){
  // 1. READ — state + args
  const {filmDelays, filmDelaysHistory} = state.snapshot();
  const k=title+'|'+day+'|'+time;
  const newVal=Math.max(0, (filmDelays[k]||0)+addMins);
  // 3. MUTATE
  state.batchUpdate({
    filmDelaysHistory: {...filmDelaysHistory, [k]: [...(filmDelaysHistory[k]||[]), filmDelays[k]||0]},
    filmDelays: newVal===0 ? state._omit(filmDelays, k) : {...filmDelays, [k]: newVal},
  });
  // 4. PERSIST (render automático vía pipeline)
  saveDelays();
  // 5. DUAL-WRITE colaborativo (Fase A) — reflejar mi retraso de esta función en la nube
  const sk=cloudScreeningKey(title,day,time,venue);
  if(newVal>0) cloudReportDelay(sk,newVal); else cloudClearDelay(sk);
}

export function undoDelay(title,day,time,venue){
  // 1. READ — state + args
  const {filmDelays, filmDelaysHistory} = state.snapshot();
  const k=title+'|'+day+'|'+time;
  // 2. GUARD — no history para esta key
  if(!filmDelaysHistory[k]||!filmDelaysHistory[k].length) return;
  const prev=filmDelaysHistory[k][filmDelaysHistory[k].length-1];
  const newHistArr=filmDelaysHistory[k].slice(0,-1);
  // 3. MUTATE
  state.batchUpdate({
    filmDelaysHistory: newHistArr.length ? {...filmDelaysHistory, [k]: newHistArr} : state._omit(filmDelaysHistory, k),
    filmDelays: prev===0 ? state._omit(filmDelays, k) : {...filmDelays, [k]: prev},
  });
  // 4. PERSIST (render automático vía pipeline)
  saveDelays();
  // 5. DUAL-WRITE colaborativo (Fase A) — reflejar el valor revertido en la nube
  const sk=cloudScreeningKey(title,day,time,venue);
  if(prev>0) cloudReportDelay(sk,prev); else cloudClearDelay(sk);
}

export function clearDelay(title,day,time,venue){
  // 1. READ — args local
  const k=title+'|'+day+'|'+time;
  // 3. MUTATE
  state.update('filmDelays', fd => state._omit(fd, k));
  // 4. PERSIST (render automático vía pipeline)
  saveDelays();
  // 5. DUAL-WRITE colaborativo (Fase A) — borrar mi reporte en la nube
  cloudClearDelay(cloudScreeningKey(title,day,time,venue));
}

export function removeFromAgenda(title){
  // 1. READ + 2. GUARD — el outer handler solo abre el modal de confirmación
  const {savedAgenda} = state.snapshot();
  if(!savedAgenda) return;
  const _s=title.length>36?title.slice(0,34)+'…':title;
  showActionModal(t('plan_quitar_plan'),`<b>${_s}</b><br><br>${t('plan_restaurar_suger')}`,t('misc_quitar'),()=>{
    // Modal callback — el handler real (variant aceptada en spec)
    const rem=savedAgenda.schedule.find(s=>s._title===title);
    if(rem){state.update('lastRemovedSlots', arr => [{...rem,_isRestored:true}, ...arr.filter(r=>r._title!==rem._title)].slice(0,MAX_REMEMBERED_SLOTS));saveLastSlot();}
    state.update('savedAgenda', a => ({...a, schedule: a.schedule.filter(s=>s._title!==title)}));
    if(!savedAgenda.schedule.length)state.set('savedAgenda', null);
    saveSavedAgenda();
    // CTA B: mostrar aviso contextual post-eliminación
    _ctaRemovedVisible=true;
    if(_ctaRemovedTimer) clearTimeout(_ctaRemovedTimer);
    _ctaRemovedTimer=setTimeout(()=>{_ctaRemovedVisible=false;renderAgenda();},6000);
    renderAgenda();showToast(t('toast_fuera_plan'),'info');
  });
}

export function addSuggestion(title,day,time){
  title=normTitle(title);
  // 1. READ
  const {FILMS, _activeFestId, savedAgenda, watchlist, watched} = state.snapshot();
  // 2. GUARD
  if(festivalEnded()) return;
  // 3. MUTATE (step 1): Add to watchlist if not already there
  if(!watchlist.has(title)){
    state.batchUpdate({
      watchlist:state._addToSet(watchlist,title),
      watched:state._delFromSet(watched,title),
    });
    saveState('wl','watched');updateCardState(title);updateAgTab();
  }
  // 3. MUTATE (step 2): Add specific screening to saved agenda
  const screen=FILMS.find(f=>f.title===title&&f.day===day&&f.time===time);
  if(screen){
    if(!savedAgenda) state.set('savedAgenda', {schedule:[]});
    // Avoid duplicates (re-read state porque pudo haber sido seteado arriba)
    const sa=state.get('savedAgenda');
    // Mitad B (pin-funcion): add / swap / no-op. El sheet de película usa esta
    // misma acción para "Añadir esta función". Si el título ya está en OTRA
    // función → swap; si ya está en ESA misma → sin acción (cae al render final).
    const existing=sa.schedule.find(s=>s._title===title);
    if(!(existing&&existing.day===day&&existing.time===time)){
      // ── Re-validación en tiempo real ─────────────────────────────
      // getSuggestions verificó el hueco al renderizar, pero el plan
      // pudo haber cambiado desde entonces (otra sugerencia añadida
      // en la misma sesión). Revalidamos contra el estado actual. En swap,
      // EXCLUIMOS la función vieja del propio título (s._title!==title) para
      // no dar un falso positivo de conflicto consigo misma.
      const realConflict=sa.schedule.find(s=>s._title!==title&&s.day===day&&screensConflict(s,screen));
      if(realConflict){
        openConflictSheet(title, screen, realConflict);
        return;
      }
      // filter(s._title!==title): no-opea en add (título ausente), quita la
      // función vieja en swap (título presente en otra función).
      state.update('savedAgenda', a => ({
        ...a,
        schedule: [...a.schedule.filter(s=>s._title!==title), {...screen,_title:title}]
          .sort((x,y)=>x.day_order!==y.day_order?x.day_order-y.day_order:toMin(x.time)-toMin(y.time))
      }));
      saveSavedAgenda();
      // 5. UI EFFECT: toast informativo con día y hora
      const{displayTitle:dt}=parseProgramTitle(title);
      const shortT=dt.length>20?dt.slice(0,18)+'…':dt;
      const _dayShortMap=(FESTIVAL_CONFIG[_activeFestId]||{}).dayShort||{};
      const dayShort=_dayShortMap[day]||day||'';
      showToast(`${ICONS.calendar} ${shortT} · ${dayShort} · ${time}`,'info');
    }
  }
  // 3. MUTATE (step 3): Quitar de lista de restaurables
  state.update('lastRemovedSlots', arr => arr.filter(r=>r._title!==title));
  // 4. PERSIST
  saveLastSlot();
  // 5. RENDER + UI EFFECTS: jump al día de la sugerencia + re-render
  const jumpIdx=DAY_KEYS.indexOf(day);
  if(jumpIdx>=0) activeMiPlanDay=jumpIdx;
  renderAgenda();
  // Mitad B: si se añadió desde el sheet de película (abierto), re-renderizarlo
  // para que la fila pase a "En tu Plan". Desde Sugerencias el sheet no está
  // abierto → el guard lo salta.
  if(document.getElementById('pel-sheet')?.classList.contains('open')) openPelSheet(title);
}

export function checkinLaVi(title){
  // 1. READ — state al top
  const {FILMS, savedAgenda, watched} = state.snapshot();
  // 2. GUARD — si ya está watched, solo re-renderea (no-op del estado: sin
  // mutación el pipeline no dispara, así que el render queda explícito)
  if(watched.has(title)){
    renderAgenda();
    return;
  }
  // 3. MUTATE
  state.update('watched', s => state._addToSet(s, title));
  // 4. PERSIST + surgical (render automático vía pipeline)
  saveWatched();
  updateCardState(title);
  // Post-view rating SIEMPRE — openPostViewRating rutea: programa (is_cortos con
  // film_list) → cola obra por obra; film suelto → flujo de siempre. El skip viejo
  // "cortos sin calificación general" era del modelo paquete y dejaba la cola
  // INALCANZABLE (bug cazado por Juan en TT: Refugio en la Cancha sin preguntar).
  const s=savedAgenda&&savedAgenda.schedule.find(e=>e._title===title);
  setTimeout(()=>openPostViewRating(title, s?.day, s?.time, s?.venue, s?.duration), 250);
}

export function checkinNoLaVi(title){
  _removePlanItem(title);
  renderAgenda();
}

export function forceInclude(title){
  // El botón "+ Incluir" en la sección No Incluidas solo se renderiza cuando
  // hay un conflicto con el schedule actual (ver agenda.js: canInclude=true
  // sii conflictWith != null). Reusamos el modal de confirmReplace con
  // isScenario=true: muta cachedResult, no toca savedAgenda. El commit ocurre
  // solo con "Usar este Plan".
  //
  // IMPORTANTE: matchear el mismo loop que la vista usa para detectar
  // conflictWith (agenda.js _excItems) — sin sortScreensByStrategy — para que
  // el (screening del excluido, conflicto) que muestra el modal coincida con
  // el que dice la razón en la UI ("Choca con X · DÍA HORA").
  if(festivalEnded()){showToast(t('notice_fest_term'),'info');return;}
  if(!cachedResult||!cachedResult.scenarios.length) return;
  const sc=cachedResult.scenarios[cachedResult.currentIdx||0];
  const screens=FILMS.filter(f=>f.title===title&&!screeningPassed(f)&&!isScreeningBlocked(f));
  if(!screens.length){showToast(t('plan_sin_horario'),'info');return;}
  // Buscar el primer (screening del excluido, conflicto en schedule) y delegar.
  for(const s of screens){
    for(const c of sc.schedule){
      if(screensConflict(s,c)){
        confirmReplace(c._title, title, s.day, s.time, true);
        return;
      }
    }
  }
  // Edge case: ninguna función conflictúa. El planner debería haberla
  // incluido — pero por consistencia mostramos toast en lugar de fallar
  // silenciosamente.
  showToast(t('plan_sin_horario'),'info');
}

export function togglePriority(title,cost){
  // 1. READ
  const {prioritized, watchlist, watched, PRIO_LIMIT} = state.snapshot();
  // 2. GUARD + 3. MUTATE — branch A: unprioritize
  if(prioritized.has(title)){
    // D3: quitar in-strip se queda en el tab actual (sin modal ni navegación) — el
    // toast alcanza. Preservar el resultado del Planear → detección de estado stale.
    _markPreserveResult();
    state.update('prioritized', s=>state._delFromSet(s,title));
    // 4. PERSIST + surgical (render automático vía pipeline)
    savePrio();updateCardState(title);
    showToast(`${ICONS.star} ${t('toast_prioridad_quitada')}`,'info');
  } else {
    // Branch B: prioritize (con limit check)
    if(prioritized.size>=PRIO_LIMIT){
      openPrioLimit(title);return;
    }
    _markPreserveResult();
    const _addWL=!watchlist.has(title);
    state.transaction(() => {
      state.update('prioritized', s=>state._addToSet(s,title));
      if(_addWL) state.batchUpdate({watchlist:state._addToSet(watchlist,title), watched:state._delFromSet(watched,title)});
    });
    savePrio();if(_addWL){saveWL();saveWatched();}updateCardState(title);
    showToast(`${ICONS.starFill} ${t('cta_priorizada')} · ${prioritized.size+1}/${PRIO_LIMIT}`,'info');
  }
  if(activeView==='day') updateHorarioPrioBtn(title);   // surgical: botón prio del pel-sheet
}

export function swapPriority(removeTitle, addTitle){
  state.update('prioritized', s => state._addToSet(state._delFromSet(s, removeTitle), addTitle));
  savePrio();
  updateCardState(removeTitle);
  updateCardState(addTitle);
  updateAgTab();
  closePrioLimit();
  const{displayTitle}=parseProgramTitle(addTitle);
  showToast(`${ICONS.starFill} ${t('toast_priorizada',{title:displayTitle})}`,'info');
}

export function markWatchedFromPlan(title, day, time, venue, duration, e){
  if(e) e.stopPropagation();
  // 1. READ
  const {FILMS, watched, watchlist} = state.snapshot();
  // 2. GUARD + 3. MUTATE — branch A: desmarcar (ya watched)
  if(watched.has(title)){
    state.batchUpdate({
      watched: state._delFromSet(watched, title),
      watchlist: watchlist.has(title) ? watchlist : state._addToSet(watchlist, title),
    });
    // 4. PERSIST + surgical (render automático vía pipeline)
    saveState('wl','watched');
    updateCardState(title);
    showToast(t('plan_vuelta_pendientes'),'info');
    return;
  }
  // Branch B: marcar como vista + post-view rating modal
  // 3. MUTATE
  state.update('watched', s=>state._addToSet(s, title));
  // 4. PERSIST + surgical (render automático vía pipeline)
  saveWatched();
  updateCardState(title);
  // Post-view rating SIEMPRE (programa → cola obra por obra; ver checkinLaVi).
  setTimeout(()=>openPostViewRating(title, day, time, venue, duration), 250);
}

export function confirmReplace(removedTitle,newTitle,day,time,isScenario){
  // 1. READ — args + state (snapshot del state se hace dentro del closure
  // porque el handler se ejecuta tras el user click, no inmediato)
  const{displayTitle:dt}=parseProgramTitle(newTitle);
  const shortNew=dt.length>22?dt.slice(0,20)+'…':dt;
  const{displayTitle:dr}=parseProgramTitle(removedTitle||'');
  const shortRem=dr.length>22?dr.slice(0,20)+'…':dr;
  const existing=document.getElementById('conflict-modal');if(existing) existing.remove();
  const modal=document.createElement('div');
  modal.id='conflict-modal';modal.className='conflict-modal';
  modal.innerHTML=`<div class="conflict-modal-box">
    <div class="conflict-modal-hdr">${removedTitle?t('plan_reemplazar_funcion'):t('plan_anadir_plan')}</div>
    <div class="conflict-modal-body">${removedTitle?t('plan_reemplazar_funcion_body',{old:`<b>${shortRem}</b>`,new:`<b>${shortNew}</b>`}):t('plan_anadir_plan_body',{new:`<b>${shortNew}</b>`})}</div>
    <div class="conflict-modal-btns">
      <button class="conflict-modal-btn cancel" data-action="removeConflictModal">${t('search_cancelar')}</button>
      <button class="conflict-modal-btn confirm" id="replace-ok">${removedTitle?t('misc_si_reemplazar'):t('misc_si_anadir')}</button>
    </div>
  </div>`;
  document.body.appendChild(modal);
  setTimeout(()=>{
    const btn=document.getElementById('replace-ok');
    if(btn) btn.onclick=()=>{
      // Handler real — fresh snapshot al ejecutarse (post user-click)
      const {FILMS, savedAgenda, watchlist} = state.snapshot();
      modal.remove();
      const screen=FILMS.find(f=>f.title===newTitle&&f.day===day&&f.time===time);
      if(!screen){
        _expandedFilm='';
        renderAgenda();
        return;
      }
      if(isScenario){
        // Planear = espacio de exploración: muta SOLO cachedResult, no toca
        // savedAgenda ni watchlist. El commit ocurre al tocar "Usar este Plan".
        if(cachedResult&&cachedResult.scenarios&&cachedResult.scenarios.length){
          const idx=cachedResult.currentIdx||0;
          const sc=cachedResult.scenarios[idx];
          let newSchedule=sc.schedule;
          if(removedTitle) newSchedule=newSchedule.filter(s=>s._title!==removedTitle);
          // Quitar cualquier screening conflictiva con la nueva.
          newSchedule=newSchedule.filter(s=>!screensConflict(s,screen)&&s._title!==newTitle);
          newSchedule=[...newSchedule,{...screen,_title:newTitle}]
            .sort((x,y)=>DAY_KEYS.indexOf(x.day)-DAY_KEYS.indexOf(y.day)||toMin(x.time)-toMin(y.time));
          let newExcluded=(sc.excluded||[]).filter(t=>t!==newTitle);
          if(removedTitle&&!newSchedule.some(s=>s._title===removedTitle)&&watchlist.has(removedTitle)&&!newExcluded.includes(removedTitle)){
            newExcluded.push(removedTitle);
          }
          cachedResult.scenarios[idx]={...sc,schedule:newSchedule,excluded:newExcluded};
          cachedResult._prioSnapshot=[...state.get('prioritized')];
        }
      } else {
        // Mi Plan (saved): comportamiento histórico — escribe a savedAgenda.
        if(removedTitle) _removePlanItem(removedTitle);
        if(!savedAgenda) state.set('savedAgenda', {schedule:[]});
        if(!watchlist.has(newTitle)){state.update('watchlist', s=>state._addToSet(s,newTitle));saveWL();}
        state.update('savedAgenda', a => ({
          ...a,
          schedule: [...a.schedule.filter(s=>s._title!==newTitle), {...screen,_title:newTitle}]
            .sort((x,y)=>DAY_KEYS.indexOf(x.day)-DAY_KEYS.indexOf(y.day)||toMin(x.time)-toMin(y.time))
        }));
        saveSavedAgenda();
      }
      _expandedFilm='';
      showToast(removedTitle?`${t('plan_reemplazada_por')} ${shortNew}`:`${shortNew} ${t('plan_anadida_al_plan')}`,'info');
      renderAgenda();
    };
  },50);
}

export function removeFilmFromScenario(title,e){
  if(e) e.stopPropagation();
  const short=title.length>36?title.slice(0,34)+'…':title;
  showActionModal(
    t('plan_quitar_intereses'),
    `<b>${short}</b><br><br>${t('plan_se_quitara')}.`,
    t('misc_quitar'),
    ()=>{
      state.batchUpdate({
        watchlist: state._delFromSet(state.get('watchlist'), title),
        prioritized: state._delFromSet(state.get('prioritized'), title),
        watched: state._delFromSet(state.get('watched'), title),
      });
      saveState('wl','prio','watched');
      updateAgTab();
      showToast(t('toast_fuera_intereses'),'info');
      // Mutación local del cachedResult (evita rerun del worker ~1-2s):
      // 1) quitar el título del schedule, 2) sacarlo de excluded, 3) re-squeeze
      // las restantes en el slot liberado, 4) re-renderizar. Sin spinner.
      if(cachedResult&&cachedResult.scenarios&&cachedResult.scenarios.length){
        const idx=cachedResult.currentIdx||0;
        const sc=cachedResult.scenarios[idx];
        const filtered=sc.schedule.filter(s=>s._title!==title);
        const excludedLeft=(sc.excluded||[]).filter(t=>t!==title);
        const newSchedule=squeezeExcluded(filtered,excludedLeft);
        const inSched=new Set(newSchedule.map(s=>s._title));
        cachedResult.scenarios[idx]={
          ...sc,
          schedule:newSchedule,
          excluded:excludedLeft.filter(t=>!inSched.has(t))
        };
        // Snapshot de prioridades para el flag stale.
        cachedResult._prioSnapshot=[...state.get('prioritized')];
        renderAgenda();
      } else {
        runCalc();
      }
    }
  );
}

export function _dismissNotice(title){
  _dismissedNotices.add(_noticeKey(title)); // clave POR FESTIVAL (no oculta homónimos de otro)
  renderNoticesBanner();
}

export function selectMiPlanDay(idx){
  activeMiPlanDay=idx;
  // Clamp a [0, len-2] para que vs+1 (la 2ª columna de la nav) nunca desborde.
  if(idx<miPlanViewStart||idx>=miPlanViewStart+2) miPlanViewStart=Math.max(0,Math.min(idx,DAY_KEYS.length-2));
  renderAgenda();
  // Scroll to detail section below calendar
  setTimeout(()=>{
    _scrollToMplanDetail();
  },80);
}

export function miPlanNav(dir){
  // dir llega como string desde data-dir ("-1"/"1"). Coercionar a número: sin
  // esto, `miPlanViewStart + "-1"` concatena strings → "N-1" → NaN → DAYS[NaN]
  // crashea Mi Plan al navegar al día anterior.
  const _d=Number(dir)||0;
  const _cur=Number.isFinite(miPlanViewStart)?miPlanViewStart:0;
  miPlanViewStart=Math.max(0,Math.min(DAY_KEYS.length-2,_cur+_d));
  if(activeMiPlanDay<miPlanViewStart||activeMiPlanDay>=miPlanViewStart+2) activeMiPlanDay=miPlanViewStart;
  renderAgenda();
}

export function toggleMplanProg(btn,e){
  e.stopPropagation();
  const row=btn.closest('.mplan-row')||btn.closest('.saved-item');
  const list=row?.nextElementSibling;
  if(!list||!list.classList.contains('mplan-prog-list')) return;
  const open=list.classList.toggle('open');
  btn.innerHTML=(open?ICONS.chevronD:ICONS.chevronR)+' '+t('label_programa');
}

export function setActivePlanFilm(el){_activeMiPlanFilm=el.dataset.fkey||'';}

export function selectFromDetail(el){
  _activeMiPlanFilm=el.dataset.rkey||'';
  // Scroll to the matching calendar block
  setTimeout(()=>{
    const block=document.querySelector(`.mplan-wk-block[data-fkey="${CSS.escape(_activeMiPlanFilm)}"]`);
    if(block) block.scrollIntoView({behavior:'smooth',block:'center'});
  },50);
  renderAgenda();
}

export function toggleFilmAlternatives(key,title,day,time){
  if(_expandedFilm===key){_expandedFilm='';renderAgenda();return;}
  _expandedFilm=key;
  // Marcar hint como visto la primera vez que se usa
  if(!localStorage.getItem('otrofestiv_hint_cambiar')){
    localStorage.setItem('otrofestiv_hint_cambiar','1');
  }
  renderAgenda();
}

export function _toggleEveningFilms(btn){
  const extra=document.getElementById('eve-films-extra');
  if(!extra) return;
  const open=extra.style.display!=='none';
  extra.style.display=open?'none':'contents';
  btn.style.display='none'; // ocultar el botón al expandir — ya no hace falta
}

export function filterByVenue(venue){
  closePelSheet();
  activeVenue=venue;activeSec='all';selectedIdx=null;
  programaSubMode='hoy';
  programaChip='all';_programaChipMatchFn=null;
  // Si el día activo ya pasó, ir al primer día vigente
  if(dayFullyPassed(activeDay)){
    const _ff=DAY_KEYS.find(d=>!dayFullyPassed(d));
    if(_ff) activeDay=_ff;
  }
  // Regla global: navegación por día → lista por defecto
  programaViewMode=activeDay==='all'?'grid':'list';
  switchMainNav('mnav-cartelera');
  showDayView();
  // Actualizar label del filtro Lugar
  lugarClose();
}

export function filterByDay(day){
  closePelSheet();
  activeDay=day;activeVenue='all';selectedIdx=null;
  cartelaMode='horario';
  document.querySelectorAll('.dtab').forEach(t=>t.classList.toggle('on',t.dataset.day===day));
  requestAnimationFrame(()=>{
    const activeBtn=document.querySelector('.dtab.on');
    if(activeBtn){const dt=document.getElementById('dtabs');if(dt)dt.scrollLeft=activeBtn.offsetLeft-dt.offsetLeft;}
  });
  switchMainNav('mnav-cartelera');
  _renderProgramaContent(true); // cambio de día → scroll al tope
  _updateProgramaActiveFilter();
}

export function filterBySection(section){
  // Navegar a Programa · Explorar con esa sección activa
  closePelSheet();
  activeSec=section;activeVenue='all';selectedIdx=null;
  programaSubMode='hoy';
  programaChip='all';
  _programaChipMatchFn=null;
  // Si el día activo ya pasó, ir al primer día vigente
  if(dayFullyPassed(activeDay)){
    const _ff=DAY_KEYS.find(d=>!dayFullyPassed(d));
    if(_ff) activeDay=_ff;
  }
  // Regla global: navegación por día → lista por defecto
  programaViewMode=activeDay==='all'?'grid':'list';
  switchMainNav('mnav-cartelera');
  showDayView();
  // Actualizar chips visualmente después del render
  setTimeout(()=>{
    document.querySelectorAll('.pchip').forEach(el=>{
      el.classList.toggle('on',el.dataset.chip===programaChip);
    });
    _updateProgramaActiveFilter();
  },50);
}

export function setInteresesView(mode){
  interesesViewMode=mode;
  const _v = storage.getViewmodes(); _v.intereses = mode; storage.setViewmodes(_v);
  document.getElementById('ibtn-grid')?.classList.toggle('on',mode==='grid');
  document.getElementById('ibtn-list')?.classList.toggle('on',mode==='list');
  const el=document.getElementById('ag-film-list');
  _reRenderIntereses();
}

export function setProgramaMode(mode){
  programaSubMode=mode;
  // Reset filtros al cambiar modo y cerrar dropdowns
  activeSec='all';activeVenue='all';selectedIdx=null;
  programaChip='all';_programaChipMatchFn=null;
  lugarClose();seccionClose();
  // Set active day for hoy/mañana modes
  const _pts=simTodayStr();
  const _pti=DAY_KEYS.findIndex(d=>FESTIVAL_DATES[d]===_pts);
  if(mode==='hoy'){
    activeDay=_pti>=0?DAY_KEYS[_pti]:DAY_KEYS[0];
  } else if(mode==='manana'){
    activeDay=_pti>=0&&_pti<DAY_KEYS.length-1?DAY_KEYS[_pti+1]:DAY_KEYS[DAY_KEYS.length-1];
  }
  // filter-row visibility handled by initProgramaModeBar() below
  // filter updates handled by lugarOpen()
  _updateProgramaActiveFilter();
  initProgramaModeBar();
  _renderProgramaContent(true); // cambio de modo (hoy/mañana) → scroll al tope
}

export function toggleProgramaView(){
  setProgramaView(programaViewMode==='grid'?'list':'grid');
}

export function setProgramaView(view){
  programaViewMode=view;
  document.getElementById('pmode-grid').classList.toggle('on',view==='grid');
  document.getElementById('pmode-list').classList.toggle('on',view==='list');
  // Sync single toggle icon
  const icoG=document.getElementById('view-toggle-ico-grid');
  const icoL=document.getElementById('view-toggle-ico-list');
  if(icoG) icoG.style.display=view==='grid'?'':'none';
  if(icoL) icoL.style.display=view==='list'?'':'none';
  _renderProgramaContent(true); // toggle grid/list → scroll al tope
}

export function setProgramaChip(chipId){
  // Toggle: tap active chip → deselect back to 'all'
  if(chipId!=='all'&&chipId===programaChip) chipId='all';
  programaChip=chipId;
  // Actualizar chips visuales
  document.querySelectorAll('.pchip').forEach(el=>{
    el.classList.toggle('on',el.dataset.chip===chipId);
  });
  // Guardar la función de match — soporta múltiples secciones
  const chip=(_currentChips.length?_currentChips:PROGRAMA_CHIPS).find(c=>c.id===chipId);
  // Chips ocultos — activeSec siempre directo
  _programaChipMatchFn=null;
  activeSec='all';
  _updateProgramaActiveFilter();
  _renderProgramaContent(true); // filtro chip → scroll al tope
}

export function clearProgramaChip(){
  _programaChipMatchFn=null;
  activeVenue='all';
  lugarClose();
  setProgramaChip('all');
}

export function _pafClearSec(){
  activeSec='all';seccionClose();_updateProgramaActiveFilter();
  if(activeMNav==='mnav-cartelera')_renderProgramaContent(true);else render(); // limpiar filtro sección → scroll al tope
}

export function _pafClearVenue(){
  activeVenue='all';lugarClose();_updateProgramaActiveFilter();
  if(activeMNav==='mnav-cartelera')_renderProgramaContent(true);else render(); // limpiar filtro lugar → scroll al tope
}

export function _toggleWLFromList(title,btn){
  // Wrapper para el ♥ en la lista de Programa — usa el toggleWL existente
  const wasIn=watchlist.has(title);
  toggleWL(title,{stopPropagation:()=>{}});
  // Actualizar el botón visualmente después del toggle
  // Spring pop al agregar
  if(!wasIn){
    btn.style.transform='scale(1.25)';
    setTimeout(()=>btn.style.transform='',200);
  }
  setTimeout(()=>{
    const isIn=watchlist.has(title);
    if(btn){
      btn.innerHTML=isIn?ICONS.heartFill:ICONS.heart;
      btn.classList.toggle('empty',!isIn);
    }
  },50);
}

export function saveCurrentScenario(){
  if(!cachedResult||!cachedResult.scenarios.length) return;
  const _doSave=()=>{
    const _sc=cachedResult.scenarios[cachedResult.currentIdx];
    const _squeezed=squeezeExcluded(_sc.schedule,_sc.excluded||[]);
    // Preservar el PASADO del plan actual — recalcular es solo para los días que
    // aún no llegan (el algoritmo ya excluye funciones pasadas). Sin esto, "Usar
    // este plan" a mitad de festival amputaba los días cumplidos (y su marca de
    // Vista/calificación en el contexto del plan). Dedup por función exacta.
    const _past=(savedAgenda&&savedAgenda.schedule||[]).filter(s=>screeningPassed(s));
    const _key=s=>`${s._title}|${s.day}|${s.time}`;
    const _fresh=new Set(_squeezed.map(_key));
    const _merged=[..._past.filter(s=>!_fresh.has(_key(s))),..._squeezed];
    state.set('savedAgenda', {schedule:_merged});
    saveSavedAgenda();
    openPlanConfirm(_merged);
  };
  // Si ya hay un plan FUTURO guardado, pedir confirmación (el pasado se conserva).
  const _futureN=(savedAgenda&&savedAgenda.schedule||[]).filter(s=>!screeningPassed(s)).length;
  if(_futureN){
    const n=_futureN;
    showActionModal(
      `${ICONS.calendar} ${t('plan_reemplazar_plan')}`,
      `${t('plan_ya_tenes_n',{count:`<b>${n} ${n!==1?t('misc_peliculas'):t('misc_pelicula')}</b>`})}<br><br>${t('plan_reemplazar')}.`,
      t('misc_si_reemplazar'),
      _doSave,
      t('plan_conservar_actual')
    );
  } else {
    _doSave();
  }
}

export function squeezeExcluded(schedule, excludedTitles){
  const result=[...schedule];
  // Ordenar excluidas por score descendente — misma lógica que el algoritmo
  const scored=excludedTitles.map(t=>{
    const screens=FILMS.filter(f=>f.title===t&&!screeningPassed(f)&&!isScreeningBlocked(f));
    return{title:t,screens,score:scoreFilm(t,screens,prioritized.has(t),[...watchlist])};
  }).filter(g=>g.screens.length>0).sort((a,b)=>b.score-a.score);

  scored.forEach(({title,screens})=>{
    // Ordenar funciones por estrategia — menos conflictos + fin temprano
    const sorted=sortScreensByStrategy(screens,[...scored]);
    for(const s of sorted){
      if(!result.some(c=>screensConflict(c,s))){
        result.push({...s,_title:title,_squeezed:true});
        break; // encontró slot, pasar al siguiente título
      }
    }
  });
  return result;
}

export function _scrollToAgSection(id) {
  const el = document.getElementById(id);
  if (!el) return;
  const hdr = document.getElementById('hdr-ag');
  const off = hdr ? hdr.getBoundingClientRect().bottom : 0;
  const y = el.getBoundingClientRect().top + window.scrollY - off - 8;
  window.scrollTo({top: y, behavior: 'smooth'});
}

export function _setExpandedFilm(val) {
  _expandedFilm = val;
  renderAgenda();
}

export function _closePelAndRemove(title) {
  closePelSheet();
  removeFromAgenda(title);
}

export function _closePelAndRate(title) {
  closePelSheet();
  setTimeout(() => openRatingSheet(title), 100);
}

export function _navTo(tab) {
  if (tab === 'mnav-cartelera') {
    const _ph = _getProgramaPhase();
    programaSubMode = _ph.default;
    switchMainNav(tab);
    showDayView();
  } else {
    switchMainNav(tab);
    showAgView();
  }
}

export function _closeAuthAndReset() {
  closeAuthSheet();
  const step1 = document.getElementById('auth-sheet-step1');
  const step2 = document.getElementById('auth-sheet-step2');
  if (step1) step1.style.display = 'block';
  if (step2) step2.style.display = 'none';
}

export function _toggleCtxOlder() {
  const el = document.getElementById('ctx-older');
  if (!el) return;
  el.style.display = el.style.display === 'none' ? 'block' : 'none';
}

export function _toggleWatchedAndClose(title, e) {
  toggleWatched(title, e);
  closePelSheet();
}

export function _toggleWLAndClose(title, e) {
  toggleWL(title, e);
  closePelSheet();
}

export function _activatePlanFilm(el) {
  setActivePlanFilm(el);
  const i = parseInt(el.dataset.dayIndex, 10);
  if (!isNaN(i)) selectMiPlanDay(i);
}

export function _scrollToSuggestions() {
  document.querySelector('.suggestion-wrap')?.scrollIntoView({behavior:'smooth', block:'start'});
}

export function _removeConflictModal() {
  document.getElementById('conflict-modal')?.remove();
}

export function _scrollToTop() {
  window.scrollTo({top:0, behavior:'smooth'});
}

export function _searchOpenFilm(title) {
  searchClose();
  openPelSheet(title);
}

export function _searchOpenCorto(title, country, dur, section, flags) {
  searchClose();
  openCortoSheet(title, country, dur, section, flags);
}

export function _scrollToMplanDetail(){
  const el=document.getElementById('mplan-detail');
  if(!el) return;
  const tb=document.querySelector('.topbar');
  const tbH=tb?Math.ceil(tb.getBoundingClientRect().height):86;
  window.scrollTo({top:Math.max(0,el.getBoundingClientRect().top+window.scrollY-tbH-8),behavior:'smooth'});
}
