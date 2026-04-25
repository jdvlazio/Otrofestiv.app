// ══ Actions — toggleWL, search, availability, modals ══
// SOURCE: index.html L3297-3855

// ═══════════════════════════════════════════════════════════════

/* ── ACTIONS: watchlist, prioridades, vistas, retraso ───────────────── */
function toggleWL(title,e){
  if(e) e.stopPropagation();
  if(watchlist.has(title)){
    // If film is in saved agenda, ask first
    if(savedAgenda&&savedAgenda.schedule.some(s=>s._title===title)){
      showActionModal(`Quitar de Intereses`,
        `<b>${title.length>36?title.slice(0,34)+'…':title}</b> está en tu plan.<br><br>¿Quitarla también del plan guardado?`,
        'Sí, quitar de todo',()=>{
          savedAgenda.schedule=savedAgenda.schedule.filter(s=>s._title!==title);
          if(!savedAgenda.schedule.length)savedAgenda=null;
          saveSavedAgenda();
          watchlist.delete(title);watched.delete(title);prioritized.delete(title);
          saveState('wl','watched');updateCardState(title);updateAgTab();
          if(activeView==='agenda'){cachedResult=null;renderAgenda();}
        });return;
    }
    // Now safe to remove from watchlist
    watchlist.delete(title);watched.delete(title);prioritized.delete(title);
    showToast('Quitada de Intereses','info');
  }
  else{
    watchlist.add(title);watched.delete(title);
    // ── CASO 3: todas las funciones en horario no disponible ──
    const _allScreens=FILMS.filter(f=>f.title===title&&!screeningPassed(f));
    const _allBlocked=_allScreens.length>0&&_allScreens.every(s=>isScreeningBlocked(s));
    if(_allBlocked){
      const{displayTitle}=parseProgramTitle(title);
      const _short=displayTitle.length>28?displayTitle.slice(0,26)+'…':displayTitle;
      setTimeout(()=>showToast(`"${_short}" cae en horarios no disponibles — no podrá incluirse en el plan`,'warn',5000),300);
    } else if(activeMNav==='mnav-cartelera'||activeMNav==='mnav-seleccion'){
      showActionToast(`${ICONS.heartFill} En Intereses`,`${ICONS.star} Priorizar`,()=>togglePriority(title));
    } else {
      showToast(`${ICONS.heartFill} En Intereses`,'info');
    }
  }
  saveState('wl','watched');updateCardState(title);updateAgTab();
  if(activeView==='agenda'){cachedResult=null;renderAgenda();}
  else if(activeView==='day'&&activeMNav==='mnav-cartelera'){
    // Re-renderizar el grid de Programa para reflejar el cambio de ♥
    _renderProgramaContent();
  }
}
function toggleWatched(title,e){
  if(e) e.stopPropagation();
  if(watched.has(title)){
    // Quitar de vistas — si no está en Intereses, devolverla ahí
    watched.delete(title);
    if(!watchlist.has(title)) watchlist.add(title);
    saveState('wl','watched');updateCardState(title);updateAgTab();
    const listEl=document.getElementById('ag-film-list');
    if(listEl) listEl.innerHTML=renderFilmListHTML();
    if(activeView==='agenda') renderAgenda();
    showToast('Movida a pendientes','info');
  } else {
    // Confirmar antes de marcar como vista
    const short=title.length>36?title.slice(0,34)+'…':title;
    showActionModal(
      `¿Ya viste esta película?`,
      `<b>${short}</b><br><br>Se moverá a <b>Ya vistas</b> en Intereses.`,
      'Sí, ya la vi',
      ()=>{
        watched.add(title);
        saveWatched();updateCardState(title);updateAgTab();
        cachedResult=null;
        if(activeView==='agenda') renderAgenda();
        if(activeMNav==='mnav-miplan') renderAgenda();
        showToast('Movida a Ya vistas','info');
        // Los programas de cortos no tienen calificación general
        if(!FILMS.find(fi=>fi.title===title)?.is_cortos) setTimeout(()=>openRatingSheet(title),350);
      }
    );
  }
}
function updateCardState(title){
  const inWL=watchlist.has(title),inW=watched.has(title),inPrio=prioritized.has(title);
  document.querySelectorAll(`.card[data-title="${CSS.escape(title)}"]`).forEach(card=>{
    card.classList.toggle('in-wl',inWL&&!inW);
    card.classList.toggle('in-watched',inW&&!festivalEnded());
    const wlBtn=card.querySelector('.wl-btn');
    const wBtn=card.querySelector('.w-btn');
    const prioBtn=card.querySelector('.prio-btn');
    if(wlBtn){wlBtn.innerHTML=inWL?ICONS.heartFill:ICONS.heart;wlBtn.classList.toggle('wl-on',inWL);wlBtn.title=inWL?'Quitar de Intereses':'Añadir a Intereses';}
    if(wBtn){wBtn.classList.toggle('w-on',inW);wBtn.title=inW?'Marcar como pendiente':'Marcar como vista';}
    if(prioBtn){prioBtn.classList.toggle('prio-on',inPrio);prioBtn.title=inPrio?'Quitar prioridad':'Priorizar';}
  });
}

// ── FUZZY SEARCH — accent insensitive ──
function fuzzyMatch(query,title){
  const q=normalize(query),t=normalize(title);
  if(t.includes(q)) return{match:true,score:100+q.length};
  let qi=0;for(let i=0;i<t.length&&qi<q.length;i++) if(t[i]===q[qi]) qi++;
  if(qi===q.length) return{match:true,score:qi};
  return{match:false,score:0};
}
function searchFilms(query){
  if(!query||query.length<2) return[];
  const seen=new Set();
  return FILMS
    .map(f=>{
      const r1=fuzzyMatch(query,f.title);
      const r2=f.title_en?fuzzyMatch(query,f.title_en):{match:false,score:0};
      let r3={match:false,score:0};
      if(f.film_list&&f.film_list.length){
        for(const item of f.film_list){
          const r=fuzzyMatch(query,item.title);
          if(r.match&&r.score>r3.score) r3=r;
        }
      }
      return{...f,score:Math.max(r1.score,r2.score,r3.score),match:r1.match||r2.match||r3.match};
    })
    .filter(f=>f.match)
    .filter(f=>{if(seen.has(f.title)) return false;seen.add(f.title);return true;})
    .sort((a,b)=>b.score-a.score)
    .slice(0,8);
}
function onSearchInput(){
  const q=document.getElementById('ag-search-input').value.trim();
  const res=document.getElementById('ag-search-results');
  if(!q||q.length<2){res.classList.remove('open');return;}
  const films=searchFilms(q);
  if(!films.length){res.innerHTML=emptyState(ICONS.search,'Sin resultados.');res.classList.add('open');return;}
  res.innerHTML=films.map(f=>{
    const inWL=watchlist.has(f.title);
    return`<div class="ag-sr-item">
      <div>
        <div class="ag-sr-title">${f.title}</div>
        <div class="ag-sr-meta">${f.flags||''} ${f.duration||''}${f.is_cortos?' · Programa':''}${inWL?' · <span style="color:var(--orange)">${ICONS.heartFill}</span>':''}</div>
      </div>
      <button class="ag-sr-add${inWL?' added':''}" data-title="${f.title.replace(/"/g,'&quot;')}" onclick="addFromSearch(this.dataset.title)" style="display:inline-flex;align-items:center;gap:var(--sp-1)">
        ${inWL?`${ICONS.check} En Intereses`:`${ICONS.plus} Añadir`}
      </button>
    </div>`;
  }).join('');
  res.classList.add('open');
}
function addFromSearch(title){
  if(!watchlist.has(title)){watchlist.add(title);watched.delete(title);saveState('wl','watched');updateCardState(title);updateAgTab();}
  onSearchInput();
  const listEl=document.getElementById('ag-film-list');if(listEl) listEl.innerHTML=renderFilmListHTML();
}
function removeFromAgenda(title){
  if(!savedAgenda) return;
  const _s=title.length>36?title.slice(0,34)+'…':title;
  showActionModal(`Quitar del plan`,`<b>${_s}</b><br><br>Podrás restaurarla desde Sugerencias.`,'Quitar',()=>{
    const rem=savedAgenda.schedule.find(s=>s._title===title);
    if(rem){lastRemovedSlots=lastRemovedSlots.filter(r=>r._title!==rem._title);lastRemovedSlots.unshift({...rem,_isRestored:true});if(lastRemovedSlots.length>MAX_REMEMBERED_SLOTS)lastRemovedSlots.length=MAX_REMEMBERED_SLOTS;saveLastSlot();}
    savedAgenda.schedule=savedAgenda.schedule.filter(s=>s._title!==title);
    if(!savedAgenda.schedule.length)savedAgenda=null;
    saveSavedAgenda();
    // CTA B: mostrar aviso contextual post-eliminación
    _ctaRemovedVisible=true;
    if(_ctaRemovedTimer) clearTimeout(_ctaRemovedTimer);
    _ctaRemovedTimer=setTimeout(()=>{_ctaRemovedVisible=false;renderAgenda();},6000);
    renderAgenda();showToast('Quitada de Mi Plan','info');
  });
}
function addSuggestion(title,day,time){
  if(festivalEnded()) return;
  // 1. Add to watchlist if not already there
  if(!watchlist.has(title)){watchlist.add(title);watched.delete(title);saveState('wl','watched');updateCardState(title);updateAgTab();}
  // 2. Add specific screening to saved agenda
  const screen=FILMS.find(f=>f.title===title&&f.day===day&&f.time===time);
  if(screen){
    if(!savedAgenda) savedAgenda={schedule:[]};
    // Avoid duplicates
    if(!savedAgenda.schedule.some(s=>s._title===title)){
      // ── Re-validación en tiempo real ─────────────────────────────
      // getSuggestions verificó el hueco al renderizar, pero el plan
      // pudo haber cambiado desde entonces (otra sugerencia añadida
      // en la misma sesión). Revalidamos contra el estado actual.
      const realConflict=savedAgenda.schedule.find(s=>s.day===day&&screensConflict(s,screen));
      if(realConflict){
        openConflictSheet(title, screen, realConflict);
        return;
      }
      savedAgenda.schedule.push({...screen,_title:title});
      savedAgenda.schedule.sort((a,b)=>a.day_order!==b.day_order?a.day_order-b.day_order:toMin(a.time)-toMin(b.time));
      saveSavedAgenda();
      // ── Toast informativo con día y hora ─────────────────────────
      // Informa exactamente dónde quedó la película para que el
      // usuario sepa si coincide con lo que esperaba.
      const{displayTitle:dt}=parseProgramTitle(title);
      const shortT=dt.length>20?dt.slice(0,18)+'…':dt;
      const dayShort=DAY_KEYS.indexOf(day)>=0?['MAR','MIÉ','JUE','VIE','SÁB','DOM'][DAY_KEYS.indexOf(day)]:'';
      showToast(`${ICONS.calendar} ${shortT} · ${dayShort} · ${time}`,'info');
    }
  }
  // 3. Quitar de lista de restaurables
  lastRemovedSlots=lastRemovedSlots.filter(r=>r._title!==title);
  saveLastSlot();
  // 4. Saltar al día de la sugerencia en el calendario
  const jumpIdx=DAY_KEYS.indexOf(day);
  if(jumpIdx>=0) activeMiPlanDay=jumpIdx;
  // 5. Re-render
  renderAgenda();
}
function closeSearch(){setTimeout(()=>{const r=document.getElementById('ag-search-results');if(r) r.classList.remove('open');},200);}

// ── AVAILABILITY ──
// ─────────────────────────────────────────────────────────────────────────────
// ⚠️  FIX CRÍTICO — NO REMOVER (Apr 2026)
// DAY_KEYS debe estar declarada aquí, antes de cualquier función que la use.
// Sin esta declaración, Planear lanza "Can't find variable: DAY_KEYS" y
// la pestaña entera no renderiza.
// ─────────────────────────────────────────────────────────────────────────────
/* ══════════════════════════════════════════════════════
   SISTEMA DE FORMATO DE DÍAS — dos niveles semánticos
   ─────────────────────────────────────────────────────
   NIVEL 1 — COMPACT (apilado, 2 líneas)
     Uso: tabs, calendarios, grids de navegación
     Abrev: DAY_ABBR[key] → 'MAR'   (var(--t-xs), gray2, arriba)
     Núm:   DAY_NUM[key]  → 14      (var(--t-lg), white, abajo)
     Contextos: dtab, mplan-wk-col, av-row-lbl, mplan-nav

   NIVEL 2 — LABEL (inline, 1 línea)
     Uso: separadores de lista, etiquetas de sección
     Corto: DAY_SHORT[key] → 'MAR 14'    (.saved-day-lbl, .ag-day-name, .suggestion-day-lbl)
     Largo: DAY_LONG[key]  → 'Martes 14' (.mplan-list-hdr — header primario únicamente)

   FUENTE: todo deriva de DAYS[] (definido en el bloque de render de tabs)
══════════════════════════════════════════════════════ */
let DAY_KEYS =['Martes','Miércoles','Jueves','Viernes','Sábado','Domingo'];
let DAY_LONG ={Martes:'Martes 14', Miércoles:'Miércoles 15', Jueves:'Jueves 16',
                 Viernes:'Viernes 17', Sábado:'Sábado 18',  Domingo:'Domingo 19'};
let DAY_SHORT={Martes:'MAR 14',    Miércoles:'MIÉ 15',    Jueves:'JUE 16',
                 Viernes:'VIE 17',   Sábado:'SÁB 18',       Domingo:'DOM 19'};

/* dayChip(key) — componente apilado: ABREV arriba / NÚMERO abajo — FORMATO ÚNICO */
const dayChip = key => {
  const abr = DAY_ABBR[key] || (DAY_SHORT[key]||'').split(' ')[0] || key;
  const num = DAY_NUM[key]  || (DAY_SHORT[key]||'').split(' ')[1] || '';
  return `<span class="day-chip-abr">${abr}</span><span class="day-chip-num">${num}</span>`;
};
/* dayLabel/dayHeader — mantenidos para compatibilidad, internamente usan dayChip */
const dayLabel  = key => DAY_SHORT[key] || key;
const dayHeader = key => DAY_LONG[key]  || key;

/* ══════════════════════════════════════════════════════
   emptyState(icon, title, sub) — componente vacío unificado
   Usa siempre este helper para estados vacíos — nunca inline styles ni emojis
   icon: ICONS.* | title: string | sub: string (opcional)
══════════════════════════════════════════════════════ */
const emptyState = (icon, title, sub='') =>
  `<div class="empty-state">
    <div class="empty-state-icon">${icon}</div>
    <div class="empty-state-title">${title}</div>
    ${sub ? `<div class="empty-state-sub">${sub}</div>` : ''}
  </div>`;

// Hero: para pantallas completas vacías — Mi Plan, Intereses, Planear
// REGLA: CTA siempre con .empty-state-cta (ámbar sólido, texto negro)
const emptyStateHero = (icon, title, sub='', ctaLabel='', ctaOnclick='') =>
  `<div class="empty-state-hero">
    <div class="empty-state-icon">${icon}</div>
    <div class="empty-state-title">${title}</div>
    ${sub ? `<div class="empty-state-sub">${sub}</div>` : ''}
    ${ctaLabel ? `<button class="empty-state-cta" onclick="${ctaOnclick}">${ctaLabel}</button>` : ''}
  </div>`;
let avAddOpen={};
/* ── Sistema de modales de confirmación ── */
function showDestructiveModal(title,body,label,cb){_showModal(title,body,label,cb,'destructive');}
function showActionModal(title,body,label,cb,cancelLabel){_showModal(title,body,label,cb,'confirm',cancelLabel);}
function _showModal(title,body,label,cb,cls,cancelLabel){
  const p=document.getElementById('conflict-modal');if(p)p.remove();
  const m=document.createElement('div');m.id='conflict-modal';m.className='conflict-modal';
  m.innerHTML=`<div class="conflict-modal-box">
    <div class="conflict-modal-hdr">${title}</div>
    <div class="conflict-modal-body">${body}</div>
    <div class="conflict-modal-btns">
      <button class="conflict-modal-btn cancel" id="cm-c">${cancelLabel||'Cancelar'}</button>
      <button class="conflict-modal-btn ${cls}" id="cm-ok">${label}</button>
    </div></div>`;
  document.body.appendChild(m);
  document.getElementById('cm-c').onclick=()=>m.remove();
  document.getElementById('cm-ok').onclick=()=>{m.remove();cb();};
  m.addEventListener('click',e=>{if(e.target===m)m.remove();});
}

function isFullDayBlocked(day){return availability[day].blocks.some(b=>toMin(b.from)<=0&&toMin(b.to)>=toMin('23:59'));}
function checkPlanConflictsWithBlock(day, fromStr, toStr){
  if(!savedAgenda||!savedAgenda.schedule.length) return[];
  const bFrom=toMin(fromStr), bTo=toMin(toStr);
  return savedAgenda.schedule.filter(s=>{
    if(s.day!==day) return false;
    const sStart=toMin(s.time), sEnd=sStart+parseDur(s.duration);
    return sStart<bTo&&sEnd>bFrom;
  });
}
// ── CASO 2: al quitar un bloque de no disponible, ¿caben más títulos? ──
function _checkRecalcOpportunity(){
  if(!savedAgenda||!savedAgenda.schedule.length) return;
  const planTitles=new Set(savedAgenda.schedule.map(s=>s._title));
  const candidates=[...watchlist].filter(t=>!planTitles.has(t)&&!watched.has(t));
  const hasOpportunity=candidates.some(t=>{
    const screens=FILMS.filter(f=>f.title===t&&!screeningPassed(f));
    return screens.length&&screens.some(s=>!isScreeningBlocked(s));
  });
  if(hasOpportunity){
    showActionToast('Horario liberado — podrían caber más títulos','Recalcular',()=>{
      switchMainNav('mnav-planner');showAgView();setTimeout(runCalc,300);
    },5000);
  }
}

function _removePlanItem(title){
  if(!savedAgenda) return;
  const removed=savedAgenda.schedule.find(s=>s._title===title);
  if(removed){
    lastRemovedSlots=lastRemovedSlots.filter(r=>r._title!==removed._title);
    lastRemovedSlots.unshift({...removed,_isRestored:true});
    if(lastRemovedSlots.length>MAX_REMEMBERED_SLOTS) lastRemovedSlots.length=MAX_REMEMBERED_SLOTS;
    saveLastSlot();
  }
  savedAgenda.schedule=savedAgenda.schedule.filter(s=>s._title!==title);
  if(!savedAgenda.schedule.length) savedAgenda=null;
  saveSavedAgenda();
}

// ═══════════════════════════════════════════════════════════════
// 9 · DISPONIBILIDAD
//     showConflictModal, toggleFullDay, addBlock, renderAvDay
// ═══════════════════════════════════════════════════════════════
function showConflictModal(conflicts, onConfirm){
  const existing=document.getElementById('conflict-modal');if(existing) existing.remove();
  const names=conflicts.map(s=>{
    const{displayTitle}=parseProgramTitle(s._title||'');
    return`<b>${s.time} ${displayTitle.length>30?displayTitle.slice(0,28)+'…':displayTitle}</b>`;
  }).join('<br>');
  const modal=document.createElement('div');
  modal.id='conflict-modal';modal.className='conflict-modal';
  modal.innerHTML=`<div class="conflict-modal-box">
    <div class="conflict-modal-hdr">Conflicto con tu plan</div>
    <div class="conflict-modal-body">
      Este horario choca con:<br>${names}<br><br>
      ¿Continuar y quitar ${conflicts.length===1?'esta actividad':'estas actividades'} del plan?
    </div>
    <div class="conflict-modal-btns">
      <button class="conflict-modal-btn cancel" id="conflict-cancel">Cancelar</button>
      <button class="conflict-modal-btn confirm" id="conflict-ok">Quitar y continuar</button>
    </div>
  </div>`;
  document.body.appendChild(modal);
  document.getElementById('conflict-cancel').onclick=()=>modal.remove();
  document.getElementById('conflict-ok').onclick=()=>{
    modal.remove();
    onConfirm();
  };
}
function toggleFullDay(day){
  if(isFullDayBlocked(day)){
    availability[day].blocks=[];
    cachedResult=null;saveAV();renderAvBlocks();invalidateCalcResult();
    _checkRecalcOpportunity();
    return;
  }
  const _conflicts=checkPlanConflictsWithBlock(day,'00:00','23:59');
  const _doBlock=()=>{
    _conflicts.forEach(s=>_removePlanItem(s._title));
    availability[day].blocks=[{from:'00:00',to:'23:59'}];avAddOpen[day]=false;
    cachedResult=null;saveAV();renderAvBlocks();invalidateCalcResult();
  };
  if(_conflicts.length) setTimeout(()=>showConflictModal(_conflicts,_doBlock),50);
  else _doBlock();
}
function addBlock(day){
  const f=document.getElementById(`av-from-${day}`).value;
  const t=document.getElementById(`av-to-${day}`).value;
  if(!f||!t){showToast('Selecciona hora de inicio y fin','warn');return;}
  if(toMin(f)>=toMin(t)){showToast('La hora de inicio debe ser menor que la de fin','warn');return;}
  const av=availability[day];
  if(av.blocks.some(b=>toMin(f)<toMin(b.to)&&toMin(t)>toMin(b.from))){showToast('Este horario coincide con otro bloque','warn');return;}
  const _blockConflicts=checkPlanConflictsWithBlock(day,f,t);
  const _doAdd=()=>{
    _blockConflicts.forEach(s=>_removePlanItem(s._title));
    av.blocks.push({from:f,to:t});av.blocks.sort((a,b)=>toMin(a.from)-toMin(b.from));
    avAddOpen[day]=false;
    cachedResult=null;saveAV();renderAvBlocks();invalidateCalcResult();
  };
  if(_blockConflicts.length) setTimeout(()=>showConflictModal(_blockConflicts,_doAdd),50);
  else _doAdd();
}
function removeBlock(day,fromVal,toVal){
  availability[day].blocks=availability[day].blocks.filter(b=>!(b.from===fromVal&&b.to===toVal));
  cachedResult=null;saveAV();renderAvBlocks();invalidateCalcResult();
  _checkRecalcOpportunity();
}
function renderAvDay(day){
  const row=document.getElementById(`av-row-${day}`);if(!row) return;
  const fullBlocked=isFullDayBlocked(day);
  const visibleBlocks=availability[day].blocks.filter(b=>!(toMin(b.from)<=0&&toMin(b.to)>=toMin('23:59')));
  const hasAny=fullBlocked||visibleBlocks.length>0;
  const addOpen=!!avAddOpen[day];

  const pillsHtml=fullBlocked
    ?`<span class="av-pill full">Todo el día</span>`
    :visibleBlocks.map(b=>`<span class="av-pill">${b.from}–${b.to}<button class="av-pill-rm" aria-label="Eliminar bloque" onclick="removeBlock('${day}','${b.from}','${b.to}');event.stopPropagation()">×</button></span>`).join('');

  // Inline form — always shows when addOpen, with 15-min slot dropdowns
  const timeOpts=`<option value="08:00">08:00</option><option value="08:15">08:15</option><option value="08:30">08:30</option><option value="08:45">08:45</option><option value="09:00">09:00</option><option value="09:15">09:15</option><option value="09:30">09:30</option><option value="09:45">09:45</option><option value="10:00">10:00</option><option value="10:15">10:15</option><option value="10:30">10:30</option><option value="10:45">10:45</option><option value="11:00">11:00</option><option value="11:15">11:15</option><option value="11:30">11:30</option><option value="11:45">11:45</option><option value="12:00">12:00</option><option value="12:15">12:15</option><option value="12:30">12:30</option><option value="12:45">12:45</option><option value="13:00">13:00</option><option value="13:15">13:15</option><option value="13:30">13:30</option><option value="13:45">13:45</option><option value="14:00">14:00</option><option value="14:15">14:15</option><option value="14:30">14:30</option><option value="14:45">14:45</option><option value="15:00">15:00</option><option value="15:15">15:15</option><option value="15:30">15:30</option><option value="15:45">15:45</option><option value="16:00">16:00</option><option value="16:15">16:15</option><option value="16:30">16:30</option><option value="16:45">16:45</option><option value="17:00">17:00</option><option value="17:15">17:15</option><option value="17:30">17:30</option><option value="17:45">17:45</option><option value="18:00">18:00</option><option value="18:15">18:15</option><option value="18:30">18:30</option><option value="18:45">18:45</option><option value="19:00">19:00</option><option value="19:15">19:15</option><option value="19:30">19:30</option><option value="19:45">19:45</option><option value="20:00">20:00</option><option value="20:15">20:15</option><option value="20:30">20:30</option><option value="20:45">20:45</option><option value="21:00">21:00</option><option value="21:15">21:15</option><option value="21:30">21:30</option><option value="21:45">21:45</option><option value="22:00">22:00</option><option value="22:15">22:15</option><option value="22:30">22:30</option><option value="22:45">22:45</option><option value="23:00">23:00</option><option value="23:15">23:15</option><option value="23:30">23:30</option><option value="23:45">23:45</option><option value="00:00">00:00</option><option value="00:15">00:15</option><option value="00:30">00:30</option><option value="00:45">00:45</option><option value="01:00">01:00</option>`;
  const inlineForm=addOpen?`<div class="av-inline-form">
      <select id="av-from-${day}" class="av-time-input">${timeOpts}</select>
      <span class="av-sep">–</span>
      <select id="av-to-${day}" class="av-time-input">${timeOpts}</select>
      <button class="av-add-btn" onclick="addBlock('${day}')">Confirmar</button>
      <button class="av-plus-btn" onclick="avAddOpen['${day}']=false;renderAvDay('${day}')">${ICONS.x}</button>
    </div>`:'';

  const isPast=dayFullyPassed(day);row.className=`av-row${isPast?' av-past':''}${fullBlocked?' av-full':''}`;
  row.innerHTML=`
    <div class="av-row-lbl">
      <div class="av-row-dayname">${DAY_ABBR[day]}</div>
      <div class="av-row-date${hasAny?' wk-has':''}">${DAY_NUM[day]}</div>
    </div>
    <div class="av-row-content">
      ${pillsHtml?`<div class="av-pills">${pillsHtml}</div>`:''}
      ${inlineForm}
      <div class="av-row-btns" style="margin-top:${pillsHtml||addOpen?'6px':'0'}">
        ${!fullBlocked&&!addOpen?`<button class="av-plus-btn" onclick="avAddOpen['${day}']=true;renderAvDay('${day}')">${ICONS.plus} No disponible</button>`:''}
        ${!addOpen?`<button class="av-full-btn${fullBlocked?' active':''}" onclick="toggleFullDay('${day}')" style="display:inline-flex;align-items:center;gap:var(--sp-1)">
          ${fullBlocked?ICONS.x+' Liberar día':ICONS.plus+' Todo el día'}
        </button>`:''}
      </div>
    </div>`;
  // Set default values for selects after render
  if(addOpen){
    const sf=document.getElementById(`av-from-${day}`);
    const st=document.getElementById(`av-to-${day}`);
    if(sf) sf.value='12:00';
    if(st) st.value='14:00';
  }
}


/* ── DISPONIBILIDAD — nueva UI ──────────────────────────────────── */
let _avSheetType='hours';
let _avSheetDay=null;

function openAvSheet(){
  const ov=document.getElementById('av-sheet-overlay');
  if(!ov) return;
  // Seleccionar primer día no pasado
  if(!_avSheetDay||dayFullyPassed(_avSheetDay)){
    _avSheetDay=DAY_KEYS.find(d=>!dayFullyPassed(d))||DAY_KEYS[0];
  }
  // Poblar chips de días con data-day para comparación fiable
  const chipsEl=document.getElementById('av-day-chips');
  if(chipsEl){
    chipsEl.innerHTML=DAY_KEYS.map(d=>{
      const isPast=dayFullyPassed(d);
      const lbl=(DAY_ABBR&&DAY_ABBR[d])||d.slice(0,3).toUpperCase();
      const num=(DAY_NUM&&DAY_NUM[d])||'';
      const sel=_avSheetDay===d?' selected':'';
      return`<button class="av-day-chip${isPast?' past':''}${sel}" data-day="${d}" onclick="selectAvDay(this.dataset.day)">${lbl} ${num}</button>`;
    }).join('');
  }
  // Poblar selects de horas
  const timeOpts=['08:00','08:30','09:00','09:30','10:00','10:30','11:00','11:30','12:00','12:30','13:00','13:30','14:00','14:30','15:00','15:30','16:00','16:30','17:00','17:30','18:00','18:30','19:00','19:30','20:00','20:30','21:00','21:30','22:00','22:30','23:00'];
  const optsHtml=timeOpts.map(t=>`<option value="${t}">${t}</option>`).join('');
  const fromEl=document.getElementById('av-sheet-from');
  const toEl=document.getElementById('av-sheet-to');
  if(fromEl){fromEl.innerHTML=optsHtml;fromEl.value='09:00';}
  if(toEl){toEl.innerHTML=optsHtml;toEl.value='12:00';}
  setAvType('hours');
  ov.style.display='flex';
}

function closeAvSheet(){
  const ov=document.getElementById('av-sheet-overlay');
  if(ov) ov.style.display='none';
}

function selectAvDay(day){
  _avSheetDay=day;
  _refreshAvDayChips();
}

function _refreshAvDayChips(){
  document.querySelectorAll('.av-day-chip').forEach(btn=>{
    btn.classList.toggle('selected', btn.dataset.day===_avSheetDay);
  });
}

function setAvType(type){
  _avSheetType=type;
  document.getElementById('av-type-hours')?.classList.toggle('selected',type==='hours');
  document.getElementById('av-type-full')?.classList.toggle('selected',type==='full');
  const ts=document.getElementById('av-time-section');
  if(ts) ts.style.display=type==='hours'?'':'none';
}

function confirmAvBlock(){
  if(!_avSheetDay) return;
  if(_avSheetType==='full'){
    // toggleFullDay ya maneja conflictos internamente
    closeAvSheet();
    if(!isFullDayBlocked(_avSheetDay)) setTimeout(()=>toggleFullDay(_avSheetDay),50);
  } else {
    const from=document.getElementById('av-sheet-from')?.value||'09:00';
    const to=document.getElementById('av-sheet-to')?.value||'12:00';
    if(from>=to){showToast('La hora de inicio debe ser menor que la de fin','warn');return;}
    // Verificar solapamiento con bloques existentes (no solo igualdad exacta)
    const av=availability[_avSheetDay];
    if(av.blocks.some(b=>toMin(from)<toMin(b.to)&&toMin(to)>toMin(b.from))){
      showToast('Este horario coincide con un bloque existente','warn');return;
    }
    // ── CASO 1: detectar conflictos con el plan antes de confirmar ──
    const _conflicts=checkPlanConflictsWithBlock(_avSheetDay,from,to);
    const _doAdd=()=>{
      _conflicts.forEach(s=>_removePlanItem(s._title));
      av.blocks.push({from,to});
      av.blocks.sort((a,b)=>toMin(a.from)-toMin(b.from)); // mantener orden cronológico
      cachedResult=null;saveAV();renderAvBlocks();invalidateCalcResult();
    };
    closeAvSheet();
    if(_conflicts.length) setTimeout(()=>showConflictModal(_conflicts,_doAdd),50);
    else _doAdd();
  }
}

function renderAvBlocks(){
  const el=document.getElementById('av-blocks-list');
  if(!el) return;
  const items=[];
  DAY_KEYS.forEach(day=>{
    const lbl=(DAY_ABBR&&DAY_ABBR[day])||day.slice(0,3).toUpperCase();
    const num=(DAY_NUM&&DAY_NUM[day])||'';
    const fullBlocked=isFullDayBlocked(day);
    const visible=availability[day]?.blocks.filter(b=>!(toMin(b.from)<=0&&toMin(b.to)>=toMin('23:59')))||[];
    if(fullBlocked){
      items.push(`<div class="av-block-item is-full">
        <span class="av-block-day">${lbl} ${num}</span>
        <span class="av-block-time">Todo el día</span>
        <button class="av-block-rm" onclick="toggleFullDay('${day}')" title="Quitar">${ICONS.x}</button>
      </div>`);
    } else {
      visible.forEach(b=>{
        items.push(`<div class="av-block-item">
          <span class="av-block-day">${lbl} ${num}</span>
          <span class="av-block-time">${b.from} – ${b.to}</span>
          <button class="av-block-rm" onclick="removeBlock('${day}','${b.from}','${b.to}')" title="Quitar">${ICONS.x}</button>
        </div>`);
      });
    }
  });
  el.innerHTML=items.length?`<div class="av-block-list">${items.join('')}</div>`:'';
}

function isScreeningBlocked(s){
  const av=availability[s.day];if(!av) return false;
  const sStart=toMin(s.time),sEnd=sStart+parseDur(s.duration);
  // Chequeo de solapamiento completo: excluye funciones que ocurran durante el bloque
  return av.blocks.some(b=>sStart<toMin(b.to)&&sEnd>toMin(b.from));
}

