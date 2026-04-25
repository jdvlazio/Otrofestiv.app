// ══ Planear + Agenda — sim, flow, renderAgenda ══
// SOURCE: index.html L5668-6443

// ═══════════════════════════════════════════════════════════════
// 13 · RENDER — VISTAS PRINCIPALES
//      renderCartelera, togglePriority, showToast, renderAgenda
// ═══════════════════════════════════════════════════════════════
function togglePriority(title,cost){
  if(prioritized.has(title)){
    // Si estamos en Planear, confirmar antes de quitar
    if(activeMNav==='mnav-planner'){
      const short=title.length>40?title.slice(0,38)+'…':title;
      showActionModal(`Quitar prioridad`,
        `<b>${short}</b><br><br>Sigue en Intereses, deja de ser prioritaria.`,
        'Quitar prioridad',()=>{
          prioritized.delete(title);savePrio();updateCardState(title);updateAgTab();runCalc();
          showToast(`${ICONS.star} Prioridad quitada`,'info');
        });return;
    }
    prioritized.delete(title);
    savePrio();updateCardState(title);updateAgTab();runCalc();
    showToast(`${ICONS.star} Prioridad quitada`,'info');
  } else {
    if(prioritized.size>=PRIO_LIMIT){
      openPrioLimit(title);return;
    }
    prioritized.add(title);
    if(!watchlist.has(title)){watchlist.add(title);watched.delete(title);saveWL();saveWatched();}
    savePrio();updateCardState(title);updateAgTab();
    showToast(`${ICONS.starFill} Priorizada · ${prioritized.size}/${PRIO_LIMIT}`,'info');
    runCalc();
  }
  if(activeView==='agenda') renderAgenda();
  else if(activeView==='day') updateHorarioPrioBtn(title);
}
function showToast(msg,type='info',duration=2800){
  let t=document.getElementById('prio-toast');
  if(!t){t=document.createElement('div');t.id='prio-toast';document.body.appendChild(t);}
  t.className='prio-toast '+type;t.innerHTML=msg;t.style.opacity='1';t.style.pointerEvents='none';
  clearTimeout(t._to);t._to=setTimeout(()=>{t.style.opacity='0';},duration);
}
let _toastActionFn=null;
function showActionToast(msg,actionLabel,actionFn,duration=4000){
  _toastActionFn=actionFn;
  let t=document.getElementById('prio-toast');
  if(!t){t=document.createElement('div');t.id='prio-toast';document.body.appendChild(t);}
  t.className='prio-toast action';
  t.innerHTML=`<span>${msg}</span><button class="toast-action-btn" onclick="if(_toastActionFn){_toastActionFn();_toastActionFn=null;showToast('','info',100)}">${actionLabel}</button>`;
  t.style.opacity='1';t.style.pointerEvents='all';
  clearTimeout(t._to);t._to=setTimeout(()=>{t.style.opacity='0';t.style.pointerEvents='none';},duration);
}

// squeezeExcluded — definida en src/algo.js (fuente canónica)

/* ── POST-VIEW RATING SHEET ── */
let _pvTitle='', _pvRating=0;

function _pvStarSVG(fill){
  if(fill==='full')  return`<svg width="34" height="34" viewBox="0 0 24 24"><polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26" fill="var(--amber)" stroke="var(--amber)" stroke-width="1.5" stroke-linejoin="round"/></svg>`;
  if(fill==='half')  return`<svg width="34" height="34" viewBox="0 0 24 24"><defs><linearGradient id="pvhg"><stop offset="50%" stop-color="var(--amber)"/><stop offset="50%" stop-color="transparent"/></linearGradient></defs><polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26" fill="url(#pvhg)" stroke="var(--amber)" stroke-width="1.5" stroke-linejoin="round"/></svg>`;
  return`<svg width="34" height="34" viewBox="0 0 24 24" style="opacity:.15"><polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26" fill="none" stroke="var(--amber)" stroke-width="1.5" stroke-linejoin="round"/></svg>`;
}

function _pvRenderStars(val){
  const row=document.getElementById('pv-stars-row');
  if(!row) return;
  row.innerHTML='';
  for(let i=1;i<=5;i++){
    const fill=val>=i?'full':val>=i-.5?'half':'none';
    const div=document.createElement('div');
    div.className='pv-star';
    div.innerHTML=_pvStarSVG(fill);
    row.appendChild(div);
  }
  // Hint y botón
  const hint=document.getElementById('pv-hint');
  const btn=document.getElementById('pv-btn-save');
  if(hint) hint.textContent=val>0?`${val} de 5`:'Deslizá sobre las estrellas';
  if(hint) hint.style.color=val>0?'var(--amber)':'var(--gray)';
  if(btn)  btn.disabled=val===0;
}

function openPostViewRating(title, day, time, venue, duration){
  _pvTitle=title;
  _pushSheetState();
  _pvRating=filmRatings[title]||0;

  const{displayTitle}=parseProgramTitle(title);
  const f=FILMS.find(fi=>fi.title===title);
  const DAY_A={Martes:'MAR',Miércoles:'MIÉ',Jueves:'JUE',Viernes:'VIE',Sábado:'SÁB',Domingo:'DOM'};

  // Poster
  const poster=document.getElementById('pv-poster');
  if(poster){
    const src=getFilmPoster(f)||'';
    poster.src=src;
    poster.onerror=()=>{poster.style.opacity='0';};
  }

  // Título
  const titleEl=document.getElementById('pv-film-title');
  if(titleEl) titleEl.textContent=displayTitle;

  // Contexto: día · venue · duración
  const ctx=document.getElementById('pv-context');
  if(ctx){
    const parts=[];
    if(day) parts.push(DAY_A[day]||day);
    if(venue) parts.push(venue.split('·')[0].trim().split('‒')[0].trim());
    if(duration) parts.push(duration);
    ctx.textContent=parts.join(' · ');
  }

  // Estrellas y rango
  const range=document.getElementById('pv-range');
  if(range){
    range.value=Math.round(_pvRating*2);
    range._pvInit=false;
  }
  _pvRenderStars(_pvRating);

  // Listener del range
  requestAnimationFrame(()=>{
    const r=document.getElementById('pv-range');
    if(r&&!r._pvInit){
      r._pvInit=true;
      r.addEventListener('input',()=>{
        _pvRating=parseInt(r.value)/2;
        _pvRenderStars(_pvRating);
      });
    }
  });

  document.getElementById('pv-rating-overlay').classList.add('open');
  const _pvSheet=document.getElementById('pv-rating-sheet');
  if(_pvSheet){ _pvSheet.style.display=''; requestAnimationFrame(()=>_pvSheet.classList.add('open')); }
}

function savePVRating(){
  if(_pvRating>0){
    filmRatings[_pvTitle]=_pvRating;
    localStorage.setItem(`${FESTIVAL_STORAGE_KEY}ratings`,JSON.stringify(filmRatings));
    const stars=['','★','★★','★★★','★★★★','★★★★★'];
    showToast(stars[Math.round(_pvRating)]||'★ Calificada','info');
  }
  closePVRating();
}

function closePVRating(){
  const overlay=document.getElementById('pv-rating-overlay');
  const sheet=document.getElementById('pv-rating-sheet');
  if(overlay) overlay.classList.remove('open');
  if(sheet){
    sheet.classList.remove('open');
    setTimeout(()=>{ if(!sheet.classList.contains('open')) sheet.style.display='none'; },350);
  }
}

function markWatchedFromPlan(title, day, time, venue, duration, e){
  if(e) e.stopPropagation();
  if(watched.has(title)){
    // Ya está vista — desmarcar
    watched.delete(title);
    if(!watchlist.has(title)) watchlist.add(title);
    saveState('wl','watched');
    updateCardState(title);
    updateAgTab();
    showToast('Movida a pendientes','info');
    return;
  }
  // Marcar como vista y abrir sheet de calificación
  watched.add(title);
  saveWatched();
  updateCardState(title);
  updateAgTab();
  renderAgenda();
  // Cortos: sin calificación general
  if(!FILMS.find(fi=>fi.title===title)?.is_cortos) setTimeout(()=>openPostViewRating(title, day, time, venue, duration), 250);
}

/* ── CONFLICT SHEET ── */
let _conflictPending=null; // {title, day, time, screen, existingTitle}

function openConflictSheet(incomingTitle, incomingScreen, existingEntry){
  const{displayTitle:inDT}=parseProgramTitle(incomingTitle);
  const{displayTitle:exDT}=parseProgramTitle(existingEntry._title||'');
  const DAY_A={Martes:'MAR',Miércoles:'MIÉ',Jueves:'JUE',Viernes:'VIE',Sábado:'SÁB',Domingo:'DOM'};

  // Pósters
  const inF=FILMS.find(f=>f.title===incomingTitle&&f.day===incomingScreen.day&&f.time===incomingScreen.time);
  const exF=FILMS.find(f=>f.title===(existingEntry._title||''));
  const inPoster=getFilmPoster(inF)||'';
  const exPoster=getFilmPoster(exF)||'';

  const ip=document.getElementById('cs-incoming-poster');
  const ep=document.getElementById('cs-existing-poster');
  if(ip){ip.src=inPoster;ip.onerror=()=>{ip.style.opacity='0';};}
  if(ep){ep.src=exPoster;ep.onerror=()=>{ep.style.opacity='0';};}

  // Nombres y horarios
  const setEl=(id,txt)=>{const el=document.getElementById(id);if(el)el.textContent=txt;};
  setEl('cs-incoming-name', inDT);
  setEl('cs-incoming-when', `${DAY_A[incomingScreen.day]||''} · ${incomingScreen.time} · ${inF?.duration||''}`);
  setEl('cs-existing-name', exDT);
  const exWhen=existingEntry.day?`${DAY_A[existingEntry.day]||''} · ${existingEntry.time} · ${exF?.duration||''}`:'';
  setEl('cs-existing-when', exWhen);

  // Botón de reemplazo con nombre exacto
  const btn=document.getElementById('cs-replace-btn');
  const shortEx=exDT.length>24?exDT.slice(0,22)+'…':exDT;
  if(btn) btn.textContent=`Añadir y quitar ${shortEx}`;

  // Guardar pendiente para ejecutar al confirmar
  _conflictPending={incomingTitle, incomingScreen, existingEntry};

  document.getElementById('conflict-sheet-overlay').classList.add('open');
  document.getElementById('conflict-sheet').classList.add('open');
  _pushSheetState();

  // Acción del botón
  if(btn) btn.onclick=confirmConflictReplace;
}

function confirmConflictReplace(){
  if(!_conflictPending) return;
  const{incomingTitle, incomingScreen, existingEntry}=_conflictPending;
  // Quitar la existente e insertar la nueva
  savedAgenda.schedule=savedAgenda.schedule.filter(s=>!(s._title===existingEntry._title&&s.day===existingEntry.day&&s.time===existingEntry.time));
  savedAgenda.schedule.push({...incomingScreen,_title:incomingTitle});
  savedAgenda.schedule.sort((a,b)=>a.day_order!==b.day_order?a.day_order-b.day_order:toMin(a.time)-toMin(b.time));
  saveSavedAgenda();
  const{displayTitle:dt}=parseProgramTitle(incomingTitle);
  closeConflictSheet();
  showToast(`${ICONS.calendar} ${dt.length>22?dt.slice(0,20)+'…':dt} en tu plan`,'info');
  renderAgenda();
}

function closeConflictSheet(){
  _conflictPending=null;
  document.getElementById('conflict-sheet-overlay').classList.remove('open');
  document.getElementById('conflict-sheet').classList.remove('open');
}

function openPrioLimit(newTitle){
  // Eyebrow con contador
  const eyebrow=document.getElementById('prio-limit-eyebrow-txt');
  const count=document.getElementById('prio-limit-count');
  if(eyebrow) eyebrow.textContent=`Prioridades · ${PRIO_LIMIT}/${PRIO_LIMIT}`;
  if(count) count.textContent=PRIO_LIMIT;

  // Título de la nueva película
  const{displayTitle}=parseProgramTitle(newTitle);
  const newTitleEl=document.getElementById('prio-limit-new-title');
  if(newTitleEl) newTitleEl.textContent=displayTitle;

  // Lista de prioritarias actuales
  const list=document.getElementById('prio-limit-list');
  if(list){
    const DAY_A={Martes:'MAR',Miércoles:'MIÉ',Jueves:'JUE',Viernes:'VIE',Sábado:'SÁB',Domingo:'DOM'};
    const items=[...prioritized].map(t=>{
      const{displayTitle:dt}=parseProgramTitle(t);
      const f=FILMS.find(fi=>fi.title===t&&!screeningPassed(fi));
      const when=f?`${DAY_A[f.day]||f.day} · ${f.time}`:'';
      const poster=getFilmPoster(f)||'';
      const safeSwap=t.replace(/'/g,"\'");
      const safeNew=newTitle.replace(/'/g,"\'");
      return`<div class="prio-limit-item">
        ${poster?`<img class="prio-limit-thumb" src="${poster}" onerror="this.style.opacity=0" alt="">`:'<div class="prio-limit-thumb"></div>'}
        <div class="prio-limit-info">
          <div class="prio-limit-name">${dt}</div>
          <div class="prio-limit-when">${when}</div>
        </div>
        <button class="prio-limit-swap" onclick="swapPriority('${safeSwap}','${safeNew}')">Cambiar</button>
      </div>`;
    }).join('');
    list.innerHTML=items;
  }

  document.getElementById('prio-limit-overlay').classList.add('open');
  document.getElementById('prio-limit-sheet').classList.add('open');
}

function closePrioLimit(){
  document.getElementById('prio-limit-overlay').classList.remove('open');
  document.getElementById('prio-limit-sheet').classList.remove('open');
}

function swapPriority(removeTitle, addTitle){
  prioritized.delete(removeTitle);
  prioritized.add(addTitle);
  savePrio();
  updateCardState(removeTitle);
  updateCardState(addTitle);
  updateAgTab();
  closePrioLimit();
  const{displayTitle}=parseProgramTitle(addTitle);
  showToast(`${ICONS.starFill} ${displayTitle} priorizada`,'info');
}

function openPlanConfirm(schedule){
  // Ordenar por posición en DAY_KEYS (funciona para cualquier festival)
  const sorted=[...schedule].sort((a,b)=>{
    const ai=DAY_KEYS.indexOf(a.day),bi=DAY_KEYS.indexOf(b.day);
    return (ai<0?999:ai)-(bi<0?999:bi)||a.time.localeCompare(b.time);
  });
  const total=sorted.length;
  const days=[...new Set(sorted.map(s=>s.day))];
  // Usar DAY_SHORT para mostrar "MAR 21" en lugar de solo "MAR"
  const dayLabel=d=>DAY_SHORT[d]||DAY_ABBR[d]||d.slice(0,3).toUpperCase();
  const dayRange=days.length===1?dayLabel(days[0]):`${dayLabel(days[0])}–${dayLabel(days[days.length-1])}`;

  // Sub: N películas · DÍAS
  const sub=document.getElementById('plan-confirm-sub');
  if(sub) sub.textContent=`${total} película${total!==1?'s':''} · ${dayRange}`;

  // Lista — máx 3 + resumen del resto
  const show=sorted.slice(0,3);
  const rest=total-show.length;
  const filmsEl=document.getElementById('plan-confirm-films');
  if(filmsEl){
    filmsEl.innerHTML=show.map(s=>{
      const{displayTitle:dt}=parseProgramTitle(s._title||'');
      const short=dt.length>28?dt.slice(0,26)+'…':dt;
      return`<div class="plan-confirm-film">
        <div class="plan-confirm-dot"></div>
        <div class="plan-confirm-time">${s.time}</div>
        <div class="plan-confirm-name">${short}</div>
      </div>`;
    }).join('')+(rest>0?`<div class="plan-confirm-film" style="color:var(--gray)"><div class="plan-confirm-dot" style="background:var(--gray)"></div><div class="plan-confirm-name">+ ${rest} más · ${dayRange}</div></div>`:'');
  }

  const _pcSheet=document.getElementById('plan-confirm-sheet');
  if(_pcSheet){ _pcSheet.style.display=''; requestAnimationFrame(()=>_pcSheet.classList.add('open')); }
  document.getElementById('plan-confirm-overlay').classList.add('open');
}

function closePlanConfirm(goToPlan){
  document.getElementById('plan-confirm-overlay').classList.remove('open');
  const _pcSheet=document.getElementById('plan-confirm-sheet');
  if(_pcSheet){
    _pcSheet.classList.remove('open');
    setTimeout(()=>{ if(!_pcSheet.classList.contains('open')) _pcSheet.style.display='none'; },350);
  }
  if(goToPlan){
    switchMainNav('mnav-miplan');
    showAgView();
    const agView=document.getElementById('ag-view');
    if(agView) agView.scrollTop=0;
  }
}

function saveCurrentScenario(){
  if(!cachedResult||!cachedResult.scenarios.length) return;
  const _doSave=()=>{
    const _sc=cachedResult.scenarios[cachedResult.currentIdx];
    const _squeezed=squeezeExcluded(_sc.schedule,_sc.excluded||[]);
    savedAgenda={schedule:_squeezed};
    saveSavedAgenda();
    openPlanConfirm(_squeezed);
  };
  // Si ya hay un plan guardado, pedir confirmación antes de reemplazarlo
  if(savedAgenda&&savedAgenda.schedule&&savedAgenda.schedule.length){
    const n=savedAgenda.schedule.length;
    showActionModal(
      `${ICONS.calendar} Reemplazar plan`,
      `Ya tienes un plan con <b>${n} película${n!==1?'s':''}</b>.<br><br>¿Reemplazarlo con esta nueva opción? Tu plan actual se perderá.`,
      'Sí, reemplazar',
      _doSave,
      'Conservar mi plan actual'
    );
  } else {
    _doSave();
  }
}
function invalidateCalcResult(){
  // Called when availability changes — resets result prompt
  if(!document.getElementById('ag-result')) return;
  const res=document.getElementById('ag-result');
  const pending=[...watchlist].filter(t=>!watched.has(t)&&FILMS.some(f=>f.title===t&&!screeningPassed(f)));
  res.innerHTML=pending.length
    ?`<div class="ag-calc-prompt">Toca <strong>Calcular opciones</strong> para ver tu plan.</div>`
    :`<div class="ag-calc-prompt">Añade lo que no quieres perderte en <strong>Intereses</strong>.</div>`;
}
function runCalc(){
  if(festivalEnded()){showToast('El festival ya terminó','info');return;}
  cachedResult=null;
  const btn=document.querySelector('.av-calc-btn');
  const res=document.getElementById('ag-result');
  // ── Loading state: mostrar siempre aunque el resultado sea idéntico ──
  if(btn){btn.disabled=true;btn.textContent='Calculando…';}
  if(res) res.innerHTML=`<div class="ag-calc-prompt" style="opacity:.6">◌ Calculando opciones…</div>`;
  // Defer computation to allow browser to paint loading state first
  setTimeout(()=>{
    try{
      const scenarios=computeScenarios([...watchlist]);
      // _algorithmCount: cuántos escenarios generó el algoritmo (sin personalizados).
      // Escalable: cualquier escenario con índice >= _algorithmCount es personalizado.
      // Al recalcular, este valor se resetea y los dots vuelven a reflejar solo el algoritmo.
      cachedResult={scenarios,currentIdx:0,_algorithmCount:scenarios.length};
      if(res) res.innerHTML=buildResultHTML(scenarios);
    }catch(err){
      if(res){const _em=document.createElement('div');_em.className='ag-calc-prompt ag-calc-error';_em.innerHTML=`<strong>Error al calcular:</strong><br>`;const _code=document.createElement('code');_code.textContent=err.message;_em.appendChild(_code);res.innerHTML='';res.appendChild(_em);}
      /* runCalc error — silent in production */
    }finally{
      if(btn){btn.disabled=false;btn.textContent='Calcular opciones';}
    }
  },80);
}

function jumpToScenario(idx){
  if(!cachedResult) return;
  cachedResult.currentIdx=Math.max(0,Math.min(cachedResult.scenarios.length-1,idx));
  renderAgenda();
}


function renderFlowProgress(activeTab){
  // activeTab: qué tab está activo ahora ('cartelera'|'seleccion'|'planner'|'miplan')
  // Paso activo = tab actual. ✓ solo cuando hay plan guardado.
  // Escalable: misma lógica para cualquier festival.
  const hasPlan=savedAgenda&&savedAgenda.schedule&&savedAgenda.schedule.length>0;
  const tabStep={'cartelera':0,'seleccion':1,'planner':2,'miplan':3};
  const currentStep=tabStep[activeTab]||1;

  const mkStep=(n,label)=>{
    const isDone=hasPlan&&n<3;  // ✓ solo cuando plan guardado
    const isActive=n===currentStep;
    const cls=`flow-step${isDone?' done':isActive?' active':''}`;
    const dotContent=isDone?'✓':n.toString();
    return`<div class="${cls}"><div class="flow-step-dot">${dotContent}</div><span>${label}</span></div>`;
  };

  return`<div class="flow-progress">
    ${mkStep(1,'Intereses')}
    <div class="flow-step-sep"></div>
    ${mkStep(2,'Planear')}
    <div class="flow-step-sep"></div>
    ${mkStep(3,'Mi Plan')}
  </div>`;
}
function renderAgenda(){
  const view=document.getElementById('ag-view');
  if(activeMNav==='mnav-seleccion'){
    // ── Mi Lista: buscador + lista de películas ──
    const _progressHtml=(!festivalEnded()&&(!savedAgenda||!savedAgenda.schedule||!savedAgenda.schedule.length))?renderFlowProgress('seleccion'):'';
    view.innerHTML=`${_progressHtml}
      <div class="ag-section">
        <div class="ag-search-wrap">
          <div class="ag-search-field">
            <span class="ag-search-ico"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg></span>
            <input type="text" id="ag-search-input" class="ag-search"
              placeholder="Buscar y añadir a Intereses…"
              oninput="onSearchInput()" onblur="closeSearch()" autocomplete="off" autocapitalize="off">
          </div>
          <div id="ag-search-results" class="ag-search-results"></div>
        </div>
        <div id="ag-film-list">${renderFilmListHTML()}</div>

      </div>`;
  } else if(activeMNav==='mnav-miplan'){
    // ── Mi Plan: stepper de progreso + calendario + sugerencias ──
    const _progressHtmlPlan=(!festivalEnded()&&(!savedAgenda||!savedAgenda.schedule||!savedAgenda.schedule.length))?renderFlowProgress('miplan'):'';
    view.innerHTML=_progressHtmlPlan+renderSavedAgendaHTML();
  } else {
    // ── Planear: stepper de progreso + prio strip + disponibilidad + opciones ──
    if(festivalEnded()){
      // Post-festival: Planear no tiene función — redirigir a Mi Plan
      view.innerHTML=`<div style="text-align:center;padding:48px 24px">
        <div style="font-size:var(--t-display);margin-bottom:16px">🎬</div>
        <div style="font-weight:var(--w-bold);color:var(--white);font-size:var(--t-lg);margin-bottom:8px">${(FESTIVAL_CONFIG[_activeFestId]||{}).name||'El festival'} ha terminado</div>
        <div style="font-size:var(--t-sm);color:var(--gray);line-height:1.6;margin-bottom:24px;max-width:260px;margin-left:auto;margin-right:auto">
          El festival ya concluyó. Revisá las películas que viste en Mi Plan.
        </div>
        <button onclick="switchMainNav('mnav-miplan');showAgView()" class="av-calc-btn" style="margin-top:0">
          Ver Mi Plan
        </button>
      </div>`;
      return;
    }
    const _progressHtml=(!savedAgenda||!savedAgenda.schedule||!savedAgenda.schedule.length)?renderFlowProgress('planner'):'';
    const pending=[...watchlist].filter(t=>!watched.has(t)&&FILMS.some(f=>f.title===t&&!screeningPassed(f)&&!isScreeningBlocked(f)));

    // ── Estado A: sin Intereses — pantalla simple, no mostrar herramienta ──
    if(!pending.length&&!cachedResult){
      view.innerHTML=`${_progressHtml}
        <div class="ag-section">
          <div class="ag-search-wrap">
            <div class="ag-search-field">
              <span class="ag-search-ico"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg></span>
              <input type="text" id="ag-search-input" class="ag-search"
                placeholder="Buscar y añadir a Intereses…"
                oninput="onSearchInput()" onblur="closeSearch()" autocomplete="off" autocapitalize="off">
            </div>
            <div id="ag-search-results" class="ag-search-results"></div>
          </div>
          ${emptyStateHero(ICONS.calendar,'Primero, elige tus títulos','Añade lo que no quieres perderte. Cuando tengas tu lista, armamos tu plan.','Ir a Intereses',"switchMainNav('mnav-seleccion');showAgView()")}
        </div>`;
      return;
    }

    // ── Estado B: con Intereses — herramienta completa ──
    const resultContent=cachedResult
      ?buildResultHTML(cachedResult.scenarios)
      :`<div class="ag-calc-prompt">Toca <strong>Calcular opciones</strong> para ver tu plan.</div>`;
    view.innerHTML=`${_progressHtml}
      <div class="ag-section">
        <div class="ag-search-wrap">
          <div class="ag-search-field">
            <span class="ag-search-ico"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg></span>
            <input type="text" id="ag-search-input" class="ag-search"
              placeholder="Buscar y añadir a Intereses…"
              oninput="onSearchInput()" onblur="closeSearch()" autocomplete="off" autocapitalize="off">
          </div>
          <div id="ag-search-results" class="ag-search-results"></div>
        </div>
        ${renderPrioStrip()}
        <button class="av-calc-btn" onclick="runCalc()">
          Calcular opciones
        </button>
        <div style="margin-top:var(--sp-5);border-top:1px solid var(--bdr-l);padding-top:var(--sp-4)">
          <div class="sec-hdr" style="margin-bottom:var(--sp-2)">${ICONS.clock} Disponibilidad <span class="sec-hdr-opt">opcional</span></div>
          <div style="font-size:var(--t-sm);color:var(--gray2);margin-bottom:var(--sp-3);line-height:1.5">Tu plan no incluirá funciones en estos horarios.</div>
          <div id="av-blocks-list"></div>
          <button class="av-add-unavail" onclick="openAvSheet()">${ICONS.plus} No disponible</button>
        </div>
      </div>
      <div class="ag-section">
        <div class="sec-hdr">${ICONS.switch} Opciones</div>
        <div id="ag-result">${resultContent}</div>
      </div>`;
    renderAvBlocks();
  }
}

// ── CALENDAR VIEW ──
let activeView='day',activeDay='Martes',activeVenue='all',activeSec='all',selectedIdx=null,activeMNav='mnav-cartelera';
let cartelaMode='pelicula'; // 'horario' | 'pelicula' (interno)
let programaSubMode='explorar'; // 'explorar' | 'hoy' | 'manana'
let interesesViewMode='grid';   // 'grid' | 'list' para Intereses
let miPlanViewMode='calendar';  // 'calendar' | 'list' para Mi Plan
let programaViewMode='grid';    // 'grid' | 'list'
let programaChip='all';         // chip activo en Explorar
let _programaChipMatchFn=null;  // función de match activa para filtrar
let _currentChips=[];           // chips dinámicos del festival activo

// Definición de chips de categoría — agrupan las secciones reales de FICCI
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
let expandedPelicula=''; // título expandido en vista Por Película

/* ── BÚSQUEDA EN CARTELERA ── */
function onCartaSearch(){
  const inp=document.getElementById('carta-search-input');
  const res=document.getElementById('carta-search-results');
  const clr=document.getElementById('carta-search-clear');
  if(!inp||!res) return;
  const q=inp.value.trim().toLowerCase();
  if(clr) clr.classList.toggle('visible', q.length>0);
  if(!q){res.classList.remove('open');res.innerHTML='';return;}

  // Buscar en títulos únicos (programas + cortos individuales en film_list)
  const titleMap={};
  FILMS.forEach(f=>{if(!titleMap[f.title]) titleMap[f.title]=f;});
  const progMatches=Object.values(titleMap).filter(f=>{
    const{displayTitle}=parseProgramTitle(f.title);
    const secShort=(f.section||'').replace(/^[^ ]+ /,'').toLowerCase();
    return displayTitle.toLowerCase().includes(q)
      ||f.title.toLowerCase().includes(q)
      ||secShort.includes(q)
      ||(f.country||'').toLowerCase().includes(q);
  });
  // Buscar también en cortos individuales dentro de film_list
  const cortoMatches=[];
  FILMS.filter(f=>f.is_cortos&&f.film_list?.length).forEach(prog=>{
    prog.film_list.forEach(item=>{
      if(item.title.toLowerCase().includes(q)){
        // Crear pseudo-entrada para el corto individual
        cortoMatches.push({
          _isCortoItem:true, _prog:prog,
          title:item.title, country:item.country, duration:item.duration,
          flags:countryToFlags(item.country||''), section:prog.section,
          is_cortos:false
        });
      }
    });
  });
  // Combinar — programas primero, cortos individuales después
  const allMatches=[...progMatches,...cortoMatches];
  const seen=new Set();
  const matches=allMatches.filter(f=>{if(seen.has(f.title))return false;seen.add(f.title);return true;}).slice(0,10);

  if(!matches.length){
    res.innerHTML='<div style="padding:var(--sp-btn);text-align:center;color:var(--gray);font-size:var(--t-base)">Sin resultados</div>';
    res.classList.add('open');
    return;
  }

  res.innerHTML=matches.map(f=>{
    const{displayTitle,progSuffix}=parseProgramTitle(f.title);
    const poster=getFilmPoster(f)||'';
    const safeT=f.title.replace(/'/g,"\'");
    const safeC=(f.country||'').replace(/'/g,"\'");
    const safeD=(f.duration||'').replace(/'/g,"\'");
    const safeS=(f.section||'').replace(/'/g,"\'");
    const safeF=(f.flags||'🌍').replace(/'/g,"\'");
    const inWL=watchlist.has(f.title);
    const onclick=f._isCortoItem?`clearCartaSearch();openCortoSheet('${safeT}','${safeC}','${safeD}','${safeS}','${safeF}')`:`clearCartaSearch();openPelSheet('${safeT}')`;
    return`<div class="carta-sr-item" onclick="${onclick}">
      ${poster?`<img class="carta-sr-poster" src="${poster}" onerror="this.style.opacity=0" alt="">`:'<div class="carta-sr-poster"></div>'}
      <div class="carta-sr-info">
        <div class="carta-sr-title">${displayTitle}${progSuffix?` <span class="prog-suffix">${progSuffix}</span>`:''}</div>
        <div class="carta-sr-meta">${f._isCortoItem
          ?`Cortometraje${f._prog?` · ${parseProgramTitle(f._prog.title).displayTitle}`:''}`
          :`${f.duration||''}${f.section?' · '+f.section.replace(/^[^ ]+ /,''):''}`
        }${inWL?' · <span class="wl-heart">♥</span>':''}</div>
      </div>
    </div>`;
  }).join('');
  res.classList.add('open');
}

function clearCartaSearch(){
  const inp=document.getElementById('carta-search-input');
  const res=document.getElementById('carta-search-results');
  const clr=document.getElementById('carta-search-clear');
  if(inp) inp.value='';
  if(res){res.classList.remove('open');res.innerHTML='';}
  if(clr) clr.classList.remove('visible');
}

// Cerrar al tocar fuera
document.addEventListener('click',e=>{
  const wrap=document.getElementById('carta-search-wrap');
  if(wrap&&!wrap.contains(e.target)) clearCartaSearch();
});

/* ── NAV: navegación principal entre tabs ────────────────────────────── */
function switchMainNav(id){
  if(id==='mnav-miplan') activeMiPlanDay=null; // recalcula día actual al entrar
  activeMNav=id;
  document.querySelectorAll('.main-nav-tab').forEach(t=>t.classList.remove('on'));
  const el=document.getElementById(id);if(el) el.classList.add('on');
}
function showDayView(){
  activeView='day';
  switchMainNav('mnav-cartelera');
  // Mostrar buscador y mode bar
  const _csw2=document.getElementById('carta-search-wrap');if(_csw2) _csw2.style.display='';
  const modeBar=document.getElementById('programa-mode-bar');
  if(modeBar){
    modeBar.style.removeProperty('display');// removeProperty is more reliable than =""
    modeBar.setAttribute('data-sdv',Date.now());// tag for debugging
  }
  // Ocultar toggle legacy
  const toggle=document.getElementById('carta-mode-toggle');if(toggle) toggle.style.display='none';
  // Ocultar filter-row hasta que se pida con "Filtrar"
  document.getElementById('filter-row').classList.add('hidden');
  document.getElementById('filter-bars').style.display='';
  ['hint','cnt','grid','cartelera-stepper','cartelera-cta'].forEach(id=>{const el=document.getElementById(id);if(el) el.style.display='';});
  const _av=document.getElementById('ag-view');
  _av.classList.remove('visible');
  _av.style.display='none';
  document.getElementById('agtab').classList.remove('on');
  // Inicializar el sistema de modos
  initProgramaModeBar();
  _renderProgramaContent();
}
function showAgView(){
  activeView='agenda';
  const _toggle=document.getElementById('carta-mode-toggle');if(_toggle) _toggle.style.display='none';
  const _mbar=document.getElementById('programa-mode-bar');if(_mbar) _mbar.style.display='none';
  const _chips=document.getElementById('programa-chips');if(_chips) _chips.classList.add('hidden');
  const _paf=document.getElementById('programa-active-filter');if(_paf) _paf.classList.remove('visible');
  const _lista=document.getElementById('programa-list');if(_lista) _lista.classList.remove('visible');
  const _csw=document.getElementById('carta-search-wrap');if(_csw) _csw.style.display='none';
  document.getElementById('nav-row').classList.add('hidden');
  document.getElementById('filter-row').classList.add('hidden');
  document.getElementById('filter-bars').style.display='none';
  ['hint','cnt','grid','cartelera-stepper','cartelera-cta'].forEach(id=>{const el=document.getElementById(id);if(el) el.style.display='none';});
  const _av=document.getElementById('ag-view');
  _av.style.display='';
  _av.classList.add('visible');
  // Trigger lazy image loading for newly visible content
  requestAnimationFrame(()=>window.dispatchEvent(new Event('scroll')));
  _av.scrollTop=0;
  document.getElementById('agtab').classList.add('on');
  document.querySelectorAll('.dtab').forEach(t=>t.classList.remove('on'));
  renderAgenda();
}

const dtabs=document.getElementById('dtabs');
const DAYS=[{k:'Martes',d:14,lbl:'MAR'},{k:'Miércoles',d:15,lbl:'MIÉ'},{k:'Jueves',d:16,lbl:'JUE'},{k:'Viernes',d:17,lbl:'VIE'},{k:'Sábado',d:18,lbl:'SÁB'},{k:'Domingo',d:19,lbl:'DOM'}];
const DAY_ABBR=Object.fromEntries(DAYS.map(d=>[d.k,d.lbl])); // {Martes:'MAR',...}
const DAY_NUM =Object.fromEntries(DAYS.map(d=>[d.k,d.d]));  // {Martes:14,...}
DAYS.forEach(day=>{
  const cnt=FILMS.filter(f=>f.day===day.k).length;
  const btn=document.createElement('button');
  btn.className='dtab'+(day.k===activeDay?' on':'')+(dayFullyPassed(day.k)?' past':'');
  btn.dataset.day=day.k;
  btn.innerHTML=`<span class="dtab-date">${day.lbl}</span><span class="dtab-name">${day.d}</span>`;
  btn.onclick=()=>{
    activeDay=day.k;activeVenue='all';activeSec='all';selectedIdx=null;
    cartelaMode='horario';
    document.querySelectorAll('.dtab').forEach(t=>t.classList.toggle('on',t.dataset.day===day.k));
    _renderProgramaContent();
    if(activeMNav!=='mnav-cartelera') switchMainNav('mnav-cartelera');
  };
  dtabs.appendChild(btn);
});

// Auto-posicionar en el primer día vigente al cargar
// Los días pasados siguen accesibles con scroll hacia la izquierda
(()=>{
  const firstFuture=DAY_KEYS.find(d=>!dayFullyPassed(d));
  if(firstFuture&&dayFullyPassed(activeDay)){
    activeDay=firstFuture;
    dtabs.querySelectorAll('.dtab').forEach(t=>t.classList.toggle('on',t.dataset.day===firstFuture));
  }
  requestAnimationFrame(()=>{
    const activeBtn=dtabs.querySelector('.dtab.on');
    if(activeBtn) dtabs.scrollLeft=activeBtn.offsetLeft-dtabs.offsetLeft;
  });
})();


function toggleDropdown(id){
  const panel=document.getElementById(id+'-panel');
  const arrow=document.getElementById(id+'-arrow');
  const isOpen=panel.classList.contains('open');
  closeDropdowns();
  if(!isOpen){panel.classList.add('open');if(arrow) arrow.classList.add('open');}
}
function closeDropdowns(){
  document.querySelectorAll('.fdr-panel').forEach(p=>p.classList.remove('open'));
  document.querySelectorAll('.fdr-arrow').forEach(a=>a.classList.remove('open'));
}

