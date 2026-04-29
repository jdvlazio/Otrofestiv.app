// ══ Mi Plan — renders del plan, contexto, alternativas ══
// SOURCE: index.html L4358-5668

/* ── RENDER — MI PLAN / AGENDA ──────────────────────────────────────── */
function renderSavedAgendaHTML(){
  // ⚠️ FIX CRÍTICO — NO REMOVER (Apr 2026)
  // try/catch permanente: un error en renderMiPlanCalendar u otras subfunciones
  // causaba que Mi Agenda quedara en blanco sin ningún mensaje de error visible.
  // Este wrapper aísla el fallo y muestra el error en pantalla en lugar de silencio.
  try{ return _renderSavedAgendaHTML(); }
  catch(err){
    /* renderSavedAgendaHTML error — silent in production */
    return`<div style="margin:16px;padding:16px;border:1px solid var(--red);border-radius:var(--r);font-size:var(--t-sm);color:var(--red)">
      <strong>Error al cargar Mi Plan:</strong><br>
      <code style="font-size:var(--t-xs);opacity:.8">${err.message}</code>
    </div>`;
  }
}
function checkinLaVi(title){
  if(!watched.has(title)){
    watched.add(title);saveWatched();updateCardState(title);updateAgTab();
    renderAgenda();
    const s=savedAgenda&&savedAgenda.schedule.find(e=>e._title===title);
    // Los programas de cortos no tienen calificación general
  const _isCortos=FILMS.find(fi=>fi.title===title)?.is_cortos;
  if(!_isCortos) setTimeout(()=>openPostViewRating(title, s?.day, s?.time, s?.venue, s?.duration), 250);
  } else {
    renderAgenda();
  }
}
function checkinNoLaVi(title){
  _removePlanItem(title);
  renderAgenda();
}
// _SIM_START/_SIM_END derivados del festival activo — escalable
const _simCfg=()=>FESTIVAL_CONFIG[_activeFestId]||{};
const _SIM_START=new Date((()=>{const c=_simCfg();const firstDay=c.dayKeys&&c.dayKeys[0];return firstDay&&c.festivalDates&&c.festivalDates[firstDay]?c.festivalDates[firstDay]+'T09:00:00':'2026-04-14T09:00:00';})());
const _SIM_END=new Date((()=>{const c=_simCfg();return c.festivalEndStr||'2026-04-20T02:00:00';})());
const _SIM_TOTAL=(_SIM_END-_SIM_START)/60000;
function renderSimPanel(){
  const cur=_simTime?new Date(_simTime):null;
  const label=cur?cur.toLocaleString('es',{weekday:'short',day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'}):'Tiempo real';
  const pct=cur?Math.round(Math.max(0,Math.min(_SIM_TOTAL,(cur-_SIM_START)/60000))/_SIM_TOTAL*1000):0;
  return`<div class="sim-panel">
    <label>🔧 Simular</label>
    <input type="range" id="sim-slider" min="0" max="1000" value="${pct}"
      oninput="updateSimLabel(this.value)" onchange="applySimTime(this.value)">
    <span id="sim-label">${label}</span>
    <button onclick="applySimTime(null)">Real</button>
  </div>`;
}
function updateSimLabel(val){
  const d=new Date(_SIM_START.getTime()+Math.round(val/1000*_SIM_TOTAL)*60000);
  const el=document.getElementById('sim-label');
  if(el) el.textContent=d.toLocaleString('es',{weekday:'short',day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'});
}
function applySimTime(val){
  if(val===null){
    _simTime=null;
    const sl=document.getElementById('sim-slider');if(sl) sl.value=0;
    const lb=document.getElementById('sim-label');if(lb) lb.textContent='Tiempo real';
  } else {
    _simTime=new Date(_SIM_START.getTime()+Math.round(val/1000*_SIM_TOTAL)*60000).toISOString();
  }
  _expandedFilm='';
  _activeMiPlanFilm='';
  activeMiPlanDay=null;
  renderAgenda();
}
let _expandedFilm=''; // key: title+day+time — which film has alternatives open
let _activeMiPlanFilm=''; // key: title+time — highlighted from calendar click
function toggleMplanProg(btn,e){
  e.stopPropagation();
  const row=btn.closest('.mplan-row')||btn.closest('.saved-item');
  const list=row?.nextElementSibling;
  if(!list||!list.classList.contains('mplan-prog-list')) return;
  const open=list.classList.toggle('open');
  btn.innerHTML=(open?ICONS.chevronD:ICONS.chevronR)+' Programa';
}
function setActivePlanFilm(el){_activeMiPlanFilm=el.dataset.fkey||'';}
function selectFromDetail(el){
  _activeMiPlanFilm=el.dataset.rkey||'';
  // Scroll to the matching calendar block
  setTimeout(()=>{
    const block=document.querySelector(`.mplan-wk-block[data-fkey="${CSS.escape(_activeMiPlanFilm)}"]`);
    if(block) block.scrollIntoView({behavior:'smooth',block:'center'});
  },50);
  renderAgenda();
}

function renderNextStrip(schedule){
  if(!schedule||!schedule.length) return'';
  const now=simNow();
  const upcoming=schedule
    .filter(s=>!watched.has(s._title))
    .map(s=>{
      const dateStr=FESTIVAL_DATES[s.day];if(!dateStr) return null;
      const start=new Date(`${dateStr}T${s.time}:00`);
      const dur=parseDur(s.duration);
      const end=new Date(start.getTime()+dur*60000);
      return{...s,start,end,startMin:toMin(s.time),endMin:toMin(s.time)+dur};
    })
    .filter(Boolean)
    .sort((a,b)=>a.start-b.start);
  const nowMs=now.getTime();
  const nowMin=now.getHours()*60+now.getMinutes();
  const inProg=upcoming.find(s=>s.start<=now&&s.end>now);
  const next=upcoming.find(s=>s.start>now);
  const item=inProg||next;
  if(!item) return'';
  // Only show strip if within 59 min of next film (or in progress)
  if(!inProg){
    const minsAway=Math.ceil((item.start-now)/60000);
    if(minsAway>59) return'';
  }
  const{displayTitle}=parseProgramTitle(item._title||'');
  const short=displayTitle.length>30?displayTitle.slice(0,28)+'…':displayTitle;
  const vc2=vcfg(item.venue),sl=sala(item.venue);
  const _dk=_delayKey(item);
  const delayMins=filmDelays[_dk]||0;
  let label,ico;
  if(inProg){
    const effectiveEnd=new Date(item.end.getTime()+delayMins*60000);
    const leftMin=Math.round((effectiveEnd-now)/60000);
    label=delayMins>0?`En curso · +${delayMins} min retraso · termina ~${minToStr(item.endMin+delayMins)}`:`En curso · termina en ${leftMin} min`;ico=ICONS.play;
  } else {
    const mins=Math.ceil((item.start-now)/60000);
    label=mins<60?`En ${mins} min`:`En ${Math.floor(mins/60)}h${mins%60?` ${mins%60}min`:''}`;ico=ICONS.clock;
  }

  // ── Botones de retraso (solo cuando está en curso) ──
  let delayHtml='';
  if(inProg){
    const safeT=(item._title||'').replace(/'/g,"\'");
    if(delayMins>0){
      delayHtml=`<div class="delay-row">
        <span class="delay-lbl">+${delayMins} min</span>
        ${[10,15,20,30].map(m=>`<button class="delay-btn" onclick="setDelay('${safeT}','${item.day}','${item.time}',${m})" title="+${m} min">+${m}</button>`).join('')}
        <button class="delay-clear" onclick="undoDelay('${safeT}','${item.day}','${item.time}')" title="Deshacer último">${ICONS.undo}</button>
        <button class="delay-clear" onclick="clearDelay('${safeT}','${item.day}','${item.time}')" title="Quitar retraso">${ICONS.x}</button>
      </div>`;
    } else {
      delayHtml=`<div class="delay-row">
        <span class="delay-lbl">¿Retraso?</span>
        ${[10,15,20,30].map(m=>`<button class="delay-btn" onclick="setDelay('${safeT}','${item.day}','${item.time}',${m})" title="Reportar +${m} min">+${m}</button>`).join('')}
      </div>`;
    }
  }

  // ── Advertencia si el retraso come el buffer hacia la siguiente función ──
  let warnHtml='';
  if(inProg&&delayMins>0&&next&&next.day===item.day){
    const effectiveEndMin=item.endMin+delayMins;
    const travel=travelMins(item.venue,next.venue);
    const needed=effectiveEndMin+FESTIVAL_BUFFER+travel;
    const nextStart=toMin(next.time);
    const margin=nextStart-needed;
    if(margin<0){
      const{displayTitle:nt}=parseProgramTitle(next._title||'');
      const nShort=nt.length>22?nt.slice(0,20)+'…':nt;
      warnHtml=`<div class="delay-warn"><span class="delay-warn-ico">${ICONS.alert}</span><span>Con el retraso terminas ~${minToStr(effectiveEndMin)}. Solo quedan <b>${nextStart-effectiveEndMin} min</b> antes de <b>${nShort}</b>${travel>0?` (${travel} min de viaje)`:''}.</span></div>`;
    } else if(margin<15){
      const{displayTitle:nt}=parseProgramTitle(next._title||'');
      const nShort=nt.length>22?nt.slice(0,20)+'…':nt;
      warnHtml=`<div class="delay-warn warn-amber"><span class="delay-warn-ico">${ICONS.alert}</span><span>Terminas ~${minToStr(effectiveEndMin)}. Margen ajustado: <b>${margin} min</b> hasta <b>${nShort}</b>.</span></div>`;
    }
  }

  return`<div class="next-film-strip${inProg?' now':''}">
    <div class="next-film-ico">${ico}</div>
    <div class="next-film-info">
      <div class="next-film-countdown">${label}</div>
      <div class="next-film-title">${short}</div>
      <div class="next-film-venue">${ICONS.pin} ${vc2.short}${sl?' · '+sl:''}</div>
    </div>
  </div>${delayHtml}${warnHtml}`;
}

function renderUnconfirmed(schedule){
  const now=simNow();
  const past=schedule.filter(s=>{
    if(watched.has(s._title)) return false;
    const dateStr=FESTIVAL_DATES[s.day];if(!dateStr) return false;
    const end=new Date(`${dateStr}T${s.time}:00`);
    end.setMinutes(end.getMinutes()+parseDur(s.duration));
    return end<now;
  }).sort((a,b)=>{
    const da=new Date(`${FESTIVAL_DATES[a.day]}T${a.time}:00`);
    const db=new Date(`${FESTIVAL_DATES[b.day]}T${b.time}:00`);
    return db-da;
  });
  if(!past.length) return'';
  const nowMin=now.getHours()*60+now.getMinutes();
  const todayStr=simTodayStr();
  const todayKey=DAY_KEYS.find(d=>FESTIVAL_DATES[d]===todayStr);
  const latest=past[0];const older=past.slice(1);
  const{displayTitle}=parseProgramTitle(latest._title||'');
  const short=displayTitle.length>28?displayTitle.slice(0,26)+'…':displayTitle;
  const endMs=new Date(`${FESTIVAL_DATES[latest.day]}T${latest.time}:00`).getTime()+parseDur(latest.duration)*60000;
  const minsAgo=Math.round((now.getTime()-endMs)/60000);
  const timeDesc=minsAgo<120?`Terminó hace ${minsAgo} min`:`${latest.day} · ${latest.time}`;
  const safeLast=latest._title.replace(/'/g,"\'");
  const olderHtml=older.length?`
    <div id="ctx-older" style="display:none">
      ${older.map(s=>{
        const{displayTitle:dt}=parseProgramTitle(s._title||'');
        const sh=dt.length>26?dt.slice(0,24)+'…':dt;
        const st=s._title.replace(/'/g,"\'");
        return`<div class="checkin-item">
          <div class="checkin-info"><div class="checkin-title">${sh}</div><div class="checkin-time">${s.day} · ${s.time}</div></div>
          <div class="checkin-btns"><button class="checkin-btn yes" onclick="checkinLaVi('${st}')" style="display:inline-flex;align-items:center;gap:var(--sp-1)">${ICONS.check} Vista</button><button class="checkin-btn no" onclick="checkinNoLaVi('${st}')">Luego</button></div>
        </div>`;
      }).join('')}
    </div>
    <div style="padding:4px 14px 8px">
      <button style="background:none;border:none;color:var(--gray);font-size:var(--t-xs);cursor:pointer;font-family:var(--font)"
        onclick="const el=document.getElementById('ctx-older');el.style.display=el.style.display==='none'?'block':'none'">
        + ${older.length} anterior${older.length>1?'es':''} sin confirmar
      </button>
    </div>`:'';
  return`<div class="checkin-wrap">
    <div class="checkin-hdr">Funciones sin confirmar</div>
    <div class="checkin-item">
      <div class="checkin-info"><div class="checkin-title">${short}</div><div class="checkin-time">${timeDesc}</div></div>
      <div class="checkin-btns">
        <button class="checkin-btn yes" onclick="checkinLaVi('${safeLast}')" style="display:inline-flex;align-items:center;gap:var(--sp-1)">${ICONS.check} Vista</button>
        <button class="checkin-btn no" onclick="checkinNoLaVi('${safeLast}')">Luego</button>
      </div>
    </div>${olderHtml}
  </div>`;
}


// ═══════════════════════════════════════════════════════════════
// 12 · RENDER — PLANEAR
//      toggleFilmAlternatives, renderFilmAlternatives, renderGapOptions
//      toggleArchive, runCalc, saveCurrentScenario, renderAgenda
// ═══════════════════════════════════════════════════════════════
function toggleFilmAlternatives(key,title,day,time){
  if(_expandedFilm===key){_expandedFilm='';renderAgenda();return;}
  _expandedFilm=key;
  // Marcar hint como visto la primera vez que se usa
  if(!localStorage.getItem('otrofestiv_hint_cambiar')){
    localStorage.setItem('otrofestiv_hint_cambiar','1');
  }
  renderAgenda();
}

function renderFilmAlternatives(title,day,time){
  const fStart=toMin(time);
  const fFilm=FILMS.find(f=>f.title===title&&f.day===day&&f.time===time);
  const fEnd=fStart+parseDur(fFilm?.duration||'90');
  const safeT=title.replace(/'/g,"\'");

  // Plan sin la función actual — para verificar conflictos de las alternativas
  const planWithout=(savedAgenda?savedAgenda.schedule:[]).filter(s=>!(s._title===title&&s.day===day&&s.time===time));
  const plannedTitles=new Set(planWithout.map(s=>s._title));

  // Hueco disponible: desde fin de la función anterior hasta inicio de la siguiente
  const dayPlan=planWithout.filter(s=>s.day===day).sort((a,b)=>toMin(a.time)-toMin(b.time));
  const prevFilm=dayPlan.filter(s=>toMin(s.time)+parseDur(s.duration)<=fStart).slice(-1)[0];
  const nextFilm=dayPlan.filter(s=>toMin(s.time)>=fEnd)[0];
  const gapStart=prevFilm?toMin(prevFilm.time)+parseDur(prevFilm.duration)+FESTIVAL_BUFFER:0;
  const gapEnd=nextFilm?toMin(nextFilm.time)-FESTIVAL_BUFFER:25*60;

  // ── Sección 1: Otras funciones del mismo título (cambio de horario) ──
  const sameTitle=FILMS.filter(f=>{
    if(f.title!==title) return false;
    if(f.day===day&&f.time===time) return false; // es la actual
    if(screeningPassed(f)||isScreeningBlocked(f)) return false;
    // Verificar que cabe en el plan sin conflictos
    return !planWithout.some(p=>screensConflict(p,f));
  }).sort((a,b)=>a.day_order!==b.day_order?a.day_order-b.day_order:toMin(a.time)-toMin(b.time));

  // ── Sección 2: Otras películas que caben en el hueco ──
  const DAY_A={Martes:'MAR',Miércoles:'MIÉ',Jueves:'JUE',Viernes:'VIE',Sábado:'SÁB',Domingo:'DOM'};
  const others=FILMS.filter(f=>{
    if(f.day!==day) return false;
    if(f.title===title) return false;
    if(plannedTitles.has(f.title)) return false;
    if(watched.has(f.title)) return false;
    if(screeningPassed(f)||isScreeningBlocked(f)) return false;
    const fs=toMin(f.time),fe=fs+parseDur(f.duration);
    // Cabe en el hueco disponible
    if(fs<gapStart||fe>gapEnd) return false;
    // No conflictúa con ninguna función restante del plan
    return !planWithout.some(p=>screensConflict(p,f));
  }).sort((a,b)=>{
    // Watchlist primero, luego cronológico
    const aWL=watchlist.has(a.title),bWL=watchlist.has(b.title);
    if(aWL&&!bWL) return -1;
    if(!aWL&&bWL) return 1;
    return toMin(a.time)-toMin(b.time);
  });

  const mkCard=(f,isSameTitle=false)=>{
    const vc2=vcfg(f.venue);
    const{displayTitle}=parseProgramTitle(f.title);
    const short=displayTitle.length>28?displayTitle.slice(0,26)+'…':displayTitle;
    const safeTNew=f.title.replace(/'/g,"\'");
    const inWL=!isSameTitle&&watchlist.has(f.title);
    const dayLabel=isSameTitle&&f.day!==day?`<span style="color:var(--amber);font-size:var(--t-xs);font-weight:var(--w-bold)">${DAY_A[f.day]||f.day} · </span>`:'';
    return`<div class="checkin-opt" onclick="confirmReplace('${isSameTitle?'':''}${safeT}','${safeTNew}','${f.day}','${f.time}')">
      <div class="checkin-opt-info">
        <div class="checkin-opt-time">${dayLabel}${f.time} · ${f.duration}</div>
        <div class="checkin-opt-title">${short}${inWL?` <span class="wl-heart">♥</span>`:''}</div>
        <div class="checkin-opt-venue">${ICONS.pin} ${vc2.short}</div>
      </div>
      <div class="checkin-opt-add">${ICONS.plus}</div>
    </div>`;
  };

  let html='<div class="film-alts">';

  if(sameTitle.length){
    html+=`<div style="padding:6px 14px 4px;font-size:var(--t-xs);color:var(--gray);text-transform:uppercase;letter-spacing:.06em;font-weight:var(--w-bold)">Otro horario · mismo título</div>`;
    html+=sameTitle.map(f=>mkCard(f,true)).join('');
  }
  if(others.length){
    if(sameTitle.length) html+=`<div style="height:1px;background:var(--bdr-l);margin:4px 0"></div>`;
    html+=`<div style="padding:6px 14px 4px;font-size:var(--t-xs);color:var(--gray);text-transform:uppercase;letter-spacing:.06em;font-weight:var(--w-bold)">Otras opciones · este día</div>`;
    html+=others.slice(0,5).map(f=>mkCard(f,false)).join('');
  }
  if(!sameTitle.length&&!others.length){
    html+=`<div style="padding:var(--sp-btn) var(--sp-3);font-size:var(--t-sm);color:var(--gray)">No hay alternativas disponibles — revisa Sugerencias.</div>`;
  }

  html+=`<div style="padding:4px 14px 10px">
    <button class="checkin-result-btn secondary" style="width:100%;font-size:var(--t-sm)" onclick="_expandedFilm='';renderAgenda()">Cerrar</button>
  </div></div>`;
  return html;
}


function confirmReplace(removedTitle,newTitle,day,time){
  const{displayTitle:dt}=parseProgramTitle(newTitle);
  const shortNew=dt.length>22?dt.slice(0,20)+'…':dt;
  const{displayTitle:dr}=parseProgramTitle(removedTitle||'');
  const shortRem=dr.length>22?dr.slice(0,20)+'…':dr;
  const existing=document.getElementById('conflict-modal');if(existing) existing.remove();
  const modal=document.createElement('div');
  modal.id='conflict-modal';modal.className='conflict-modal';
  modal.innerHTML=`<div class="conflict-modal-box">
    <div class="conflict-modal-hdr">${removedTitle?'¿Reemplazar función?':'¿Añadir al plan?'}</div>
    <div class="conflict-modal-body">${removedTitle?`Quitar <b>${shortRem}</b> y añadir`:'Añadir'} <b>${shortNew}</b> a tu plan.</div>
    <div class="conflict-modal-btns">
      <button class="conflict-modal-btn cancel" onclick="document.getElementById('conflict-modal').remove()">Cancelar</button>
      <button class="conflict-modal-btn confirm" id="replace-ok">Sí${removedTitle?', reemplazar':', añadir'}</button>
    </div>
  </div>`;
  document.body.appendChild(modal);
  setTimeout(()=>{
    const btn=document.getElementById('replace-ok');
    if(btn) btn.onclick=()=>{
      modal.remove();
      if(removedTitle) _removePlanItem(removedTitle);
      const screen=FILMS.find(f=>f.title===newTitle&&f.day===day&&f.time===time);
      if(screen){
        if(!savedAgenda) savedAgenda={schedule:[]};
        if(!watchlist.has(newTitle)){watchlist.add(newTitle);saveWL();}
        savedAgenda.schedule=savedAgenda.schedule.filter(s=>s._title!==newTitle);
        savedAgenda.schedule.push({...screen,_title:newTitle});
        savedAgenda.schedule.sort((a,b)=>DAY_KEYS.indexOf(a.day)-DAY_KEYS.indexOf(b.day)||toMin(a.time)-toMin(b.time));
        saveSavedAgenda();
      }
      _expandedFilm='';
      showToast(removedTitle?`Reemplazada por ${shortNew}`:`${shortNew} añadida al plan`,'info');
      renderAgenda();
    };
  },50);
}

function renderGapOptions(gapStartMin,gapEndMin,todayKey,removedTitle){
  removedTitle=removedTitle||'';
  const plannedTitles=new Set(savedAgenda?savedAgenda.schedule.map(s=>s._title):[]);
  const now=simNow();const nowMin=now.getHours()*60+now.getMinutes();
  // Only apply in-progress logic if todayKey matches the actual current festival day
  const realTodayKey=DAY_KEYS.find(d=>FESTIVAL_DATES[d]===simTodayStr());
  const isLiveDay=realTodayKey===todayKey;
  const MIN_REMAINING=20;
  const safeRem=removedTitle.replace(/'/g,"\'");
  const opts=FILMS.filter(f=>{
    if(f.day!==todayKey) return false;
    if(isScreeningBlocked(f)) return false;
    if(plannedTitles.has(f.title)&&f.title!==removedTitle) return false;
    if(f.title===removedTitle) return false;
    if(watched.has(f.title)) return false;
    const fStart=toMin(f.time),fEnd=fStart+parseDur(f.duration);
    const inProgress=isLiveDay&&fStart<nowMin&&fEnd>nowMin;
    if(inProgress) return (fEnd-nowMin)>=MIN_REMAINING&&fEnd<=gapEndMin;
    return fStart>=gapStartMin&&fEnd<=gapEndMin;
  }).sort((a,b)=>{
    const aWL=watchlist.has(a.title),bWL=watchlist.has(b.title);
    if(aWL&&!bWL) return -1;
    if(!aWL&&bWL) return 1;
    const aStart=toMin(a.time),bStart=toMin(b.time);
    const aFuture=!isLiveDay||aStart>=nowMin,bFuture=!isLiveDay||bStart>=nowMin;
    if(aFuture&&!bFuture) return -1;
    if(!aFuture&&bFuture) return 1;
    if(aFuture&&bFuture) return aStart-bStart;
    return(bStart+parseDur(b.duration))-(aStart+parseDur(a.duration));
  }).slice(0,4);
  if(!opts.length) return`<div style="padding:8px 14px 4px;font-size:var(--t-sm);color:var(--gray)">No hay funciones disponibles para este hueco.</div>`;
  return opts.map(f=>{
    const vc2=vcfg(f.venue);const{displayTitle}=parseProgramTitle(f.title);
    const short=displayTitle.length>26?displayTitle.slice(0,24)+'…':displayTitle;
    const safeT=f.title.replace(/'/g,"\'");
    const fStart=toMin(f.time);const inProg=isLiveDay&&fStart<nowMin;
    const minsIn=inProg?nowMin-fStart:0;
    const badge=inProg?`<span class="badge-live">EN CURSO · entró hace ${minsIn} min</span>`:'';
    const inWL=watchlist.has(f.title);
    return`<div class="checkin-opt" onclick="confirmReplace('${safeRem}','${safeT}','${f.day}','${f.time}')">
      <div class="checkin-opt-info">${badge}<div class="checkin-opt-time">${f.time} · ${f.duration}</div><div class="checkin-opt-title">${short}${inWL?` <span class="wl-heart">♥</span>`:''}</div><div class="checkin-opt-venue">${ICONS.pin} ${vc2.short}</div></div>
      <div class="checkin-opt-add">${ICONS.plus}</div>
    </div>`;
  }).join('');
}
// ─────────────────────────────────────────────────────────────
// HEADER CONTEXTUAL DE MI PLAN
// Responde: ¿Qué hago ahora? Cambia según el momento del festival.
// ─────────────────────────────────────────────────────────────
function _getFestivalPhase(){
  const _cfg=FESTIVAL_CONFIG[_activeFestId]||{};
  const _firstDay=_cfg.dayKeys&&_cfg.dayKeys[0];
  const _firstDateStr=_firstDay&&_cfg.festivalDates&&_cfg.festivalDates[_firstDay];
  const FESTIVAL_START=new Date(_firstDateStr?_firstDateStr+'T09:00:00':'2026-04-14T09:00:00');
  const now=simNow();
  if(festivalEnded()){
    // ENDED: resumen post-festival
    const totalWatched=[...watched].length;
    const totalPlanned=savedAgenda&&savedAgenda.schedule?savedAgenda.schedule.length:0;
    // Calificaciones pendientes: programas vistos sin rating + cortos individuales sin rating
    const _cortoPendRatings=FILMS.filter(f=>f.is_cortos&&f.film_list?.length&&watched.has(f.title))
      .reduce((acc,prog)=>acc+prog.film_list.filter(c=>!filmRatings[c.title]).length,0);
    const pendingRatings=[...watched].filter(t=>{
      const f=FILMS.find(fi=>fi.title===t);
      return f&&!f.is_cortos&&!filmRatings[t]; // programas de larga duración sin rating
    }).length+_cortoPendRatings;
    return{phase:'ended',totalWatched,totalPlanned,pendingRatings};
  }
  if(!savedAgenda||!savedAgenda.schedule||!savedAgenda.schedule.length) return null;

  // BEFORE: antes de que arranque el festival
  if(now<FESTIVAL_START){
    const msDiff=FESTIVAL_START-now;
    const daysDiff=Math.ceil(msDiff/86400000);
    return{phase:'before',daysDiff};
  }

  const todayStr=simTodayStr();
  const todayDay=DAY_KEYS.find(d=>FESTIVAL_DATES[d]===todayStr);
  if(!todayDay) return null;

  const todayScreenings=savedAgenda.schedule
    .filter(s=>s.day===todayDay)
    .sort((a,b)=>toMin(a.time)-toMin(b.time));
  if(!todayScreenings.length) return null;

  const nowMin=now.getHours()*60+now.getMinutes();

  // Clasificar funciones de hoy
  const done=todayScreenings.filter(s=>{
    const dur=parseInt(s.duration)||90;
    return toMin(s.time)+dur<=nowMin;
  });
  const active=todayScreenings.filter(s=>{
    const dur=parseInt(s.duration)||90;
    const start=toMin(s.time);
    return start<=nowMin&&start+dur>nowMin;
  });
  const future=todayScreenings.filter(s=>toMin(s.time)>nowMin);

  // Todas las del día terminaron → EVENING
  if(!active.length&&!future.length){
    const todayWatched=todayScreenings.filter(s=>watched.has(s._title)||screeningPassed(s));
    return{phase:'evening',todayScreenings,todayWatched};
  }

  const next=active.length?active[0]:future[0];
  const nextStartMin=toMin(next.time);
  const minsUntil=Math.max(0,nextStartMin-nowMin);
  const lastDone=done[done.length-1];

  // BETWEEN: hay hueco de más de 45 min entre función terminada y la próxima
  if(lastDone&&!active.length&&minsUntil>45){
    const lastDoneDur=parseInt(lastDone.duration)||90;
    const gapFromMin=toMin(lastDone.time)+lastDoneDur;
    const gapToMin=nextStartMin;
    const gapMin=gapToMin-gapFromMin;
    // Buscar sugerencia que quepa en el hueco, considerando viaje desde lastDone y hacia next
    const gapCandidates=FILMS.filter(f=>{
      if(f.day!==todayDay) return false;
      if(watched.has(f.title)) return false;
      if(savedAgenda.schedule.some(s=>s._title===f.title)) return false;
      if(screeningPassed(f)||isScreeningBlocked(f)) return false;
      const fStart=toMin(f.time);
      const fEnd=fStart+(parseInt(f.duration)||90);
      // Verificar viaje desde función anterior
      const travelFrom=lastDone.venue&&f.venue?travelMins(lastDone.venue,f.venue):0;
      if(fStart<gapFromMin+travelFrom+FESTIVAL_BUFFER) return false;
      // Verificar viaje hacia función siguiente
      const travelTo=f.venue&&next.venue?travelMins(f.venue,next.venue):0;
      if(fEnd>gapToMin-travelTo-FESTIVAL_BUFFER+10) return false;
      return true;
    }).sort((a,b)=>{
      // Watchlist primero, luego score implícito por unicidad
      const aWL=watchlist.has(a.title),bWL=watchlist.has(b.title);
      if(aWL&&!bWL) return -1;
      if(!aWL&&bWL) return 1;
      return toMin(a.time)-toMin(b.time);
    });
    const gapSuggestion=gapCandidates[0]||null;
    return{phase:'between',next,lastDone,gapMin,gapFromMin,gapToMin,gapSuggestion,minsUntil};
  }

  // NEXT: próxima función en ≤ 45 min, o función en curso
  return{phase:'next',next,minsUntil,isNow:active.length>0};
}

function renderContextualHeader(){
  const ph=_getFestivalPhase();
  if(!ph) return '';
  const DAY_A={Martes:'MAR',Miércoles:'MIÉ',Jueves:'JUE',Viernes:'VIE',Sábado:'SÁB',Domingo:'DOM'};

  // ── ENDED ─────────────────────────────────────────────────
  if(ph.phase==='ended'){
    const{totalWatched,totalPlanned,pendingRatings}=ph;
    // Películas vistas con su calificación
    // Ordenar: calificadas primero (descendente), sin calificar al final
    const watchedFilms=[...watched].sort((a,b)=>((filmRatings[b]||0)-(filmRatings[a]||0))).map(t=>{
      const f=FILMS.find(fi=>fi.title===t);
      const r=filmRatings[t];
      const{displayTitle:dt}=parseProgramTitle(t);
      const src=getFilmPoster(f)||'';
      const safeT=t.replace(/'/g,"\'");
      const stars=r?starsText(r):'';
      // Posters grandes, plena opacidad — pensado para screenshot
      // Usar poster-card existente — mismo patrón que Hoy/Mañana
      return`<div class="poster-card ended-poster" onclick="openPelSheet('${safeT}')">
        ${src?`<img src="${src}" loading="lazy" style="width:100%;height:100%;object-fit:cover;display:block" onerror="this.style.opacity=0" alt="">`:``}
        <div class="ended-poster-footer">
          ${r?`<div style="font-size:var(--t-xs);color:var(--amber);letter-spacing:1px">${stars}</div>`
             :`<button class="ended-rate-btn" onclick="event.stopPropagation();openPostViewRating('${safeT}','','','','')">★</button>`}
          <div class="ended-poster-title">${dt}</div>
        </div>
      </div>`;
    }).join('');
    const subMsg=totalWatched===0
      ?'Explorá el programa del próximo festival'
      :pendingRatings>0
        ?`${pendingRatings} sin calificar`
        :'Todo calificado · ¡Gracias por estar!';
    const ratedCount=Object.keys(filmRatings).filter(t=>watched.has(t)||FILMS.some(f=>f.is_cortos&&f.film_list?.some(c=>c.title===t))).length;
    const mainTitle=totalWatched===0
      ?((FESTIVAL_CONFIG[_activeFestId]||{}).name||'El festival')+' ha terminado'
      :`Viste ${totalWatched} película${totalWatched!==1?'s':''}`;
    return`<div class="ctx-header" style="background:linear-gradient(180deg,rgba(245,158,11,.08) 0%,transparent 120%);padding-bottom:8px">
      <div class="ctx-eyebrow">
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26"/></svg>
        ${(FESTIVAL_CONFIG[_activeFestId]||{}).name||''} · ${(FESTIVAL_CONFIG[_activeFestId]||{}).dates||''}
      </div>
      <div class="ctx-main-title">${mainTitle}</div>
      <div class="ctx-sub" style="margin-bottom:${totalWatched?'12px':'0'}">${subMsg}</div>
      ${totalWatched?`<div class="poster-grid pg-miplan">${watchedFilms}</div>`:''}
    </div>`;
  }

  // ── BEFORE ─────────────────────────────────────────────────
  if(ph.phase==='before'){
    const label=ph.daysDiff===1?'mañana':`en ${ph.daysDiff} días`;
    const prios=[...prioritized]
      .map(t=>{
        const f=FILMS.filter(fi=>fi.title===t&&!screeningPassed(fi))
          .sort((a,b)=>a.day_order-b.day_order||toMin(a.time)-toMin(b.time))[0];
        return f?{t,f}:null;
      })
      .filter(Boolean)
      .slice(0,2);
    const prioHtml=prios.map(({t,f})=>{
      const{displayTitle:dt}=parseProgramTitle(t);
      const short=dt.length>18?dt.slice(0,16)+'…':dt;
      const src=getFilmPoster(f)||'';
      return`<div class="ctx-prio-chip">
        ${src?`<img class="ctx-prio-thumb" src="${src}" onerror="this.style.opacity=0" alt="">`:
              `<div class="ctx-prio-thumb"></div>`}
        <div style="flex:1;min-width:0">
          <div class="ctx-prio-name">${short}</div>
          <div class="ctx-prio-when">${DAY_A[f.day]||''} · ${f.time}</div>
        </div>
      </div>`;
    }).join('');
    return`<div class="ctx-header">
      <div class="ctx-eyebrow">
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
        ${(FESTIVAL_CONFIG[_activeFestId]||{}).name||''}
      </div>
      <div class="ctx-main-title">El festival empieza ${label}</div>
      <div class="ctx-sub">${_cfg.city||''} · ${_cfg.dates||''}</div>
      ${prioHtml?`<div class="ctx-prio-row">${prioHtml}</div>`:''}
    </div>`;
  }

  // ── NEXT ────────────────────────────────────────────────────
  if(ph.phase==='next'){
    const{next,minsUntil,isNow}=ph;
    const{displayTitle:dt}=parseProgramTitle(next._title||'');
    const vc=vcfg(next.venue);
    const src=getFilmPoster(next)||'';
    // REGLA — badge ctx-header: solo cuando aporta info específica que el eyebrow no tiene.
    //   ✅ "En X min"        — tiempo hasta inicio; eyebrow solo dice "Próxima función"
    //   ✅ "Termina en X min"— tiempo restante en curso; eyebrow solo dice "En curso"
    //   ❌ "Ahora"           — redundante con eyebrow
    //   Todo estado nuevo debe pasar este filtro antes de añadir badge.
    const _nowMin=simNow().getHours()*60+simNow().getMinutes();
    const _endMin=toMin(next.time)+parseDur(next.duration)+(filmDelays[_delayKey(next)]||0);
    const _leftMin=Math.max(0,_endMin-_nowMin);
    const badge=isNow
      ?`<span class="ctx-next-badge" style="background:var(--surf);color:var(--white-60);border:1px solid var(--bdr)">Termina en ${_leftMin} min</span>`
      :`<span class="ctx-next-badge">En ${minsUntil} min</span>`;
    const _filmObj=FILMS.find(f=>f.title===next._title);
    const _isEvent=_filmObj&&_filmObj.type==='event';
    const eyebrowLabel=isNow?'En curso':(_isEvent?'Próximo evento':'Próxima función');

    // ── Delay controls — solo cuando está en curso ──
    let delayHtml='';
    let warnHtml='';
    if(isNow){
      const safeT=(next._title||'').replace(/'/g,"\'");
      const _dk=_delayKey(next);
      const delayMins=filmDelays[_dk]||0;
      if(delayMins>0){
        delayHtml=`<div class="delay-row">
          <span class="delay-lbl">+${delayMins} min</span>
          ${[10,15,20,30].map(m=>`<button class="delay-btn" onclick="setDelay('${safeT}','${next.day}','${next.time}',${m})" title="+${m} min">+${m}</button>`).join('')}
          <button class="delay-clear" onclick="undoDelay('${safeT}','${next.day}','${next.time}')" title="Deshacer último">${ICONS.undo}</button>
          <button class="delay-clear" onclick="clearDelay('${safeT}','${next.day}','${next.time}')" title="Quitar retraso">${ICONS.x}</button>
        </div>`;
        // Warning si el retraso come el buffer
        const schedule=savedAgenda&&savedAgenda.schedule||[];
        const upcoming=schedule.filter(s=>!screeningPassed(s)&&s._title!==next._title)
          .sort((a,b)=>toMin(a.time)-toMin(b.time));
        const nextFilm=upcoming[0];
        if(nextFilm&&nextFilm.day===next.day){
          const dur=parseDur(next.duration);
          const effectiveEndMin=toMin(next.time)+dur+delayMins;
          const travel=travelMins(next.venue,nextFilm.venue);
          const margin=toMin(nextFilm.time)-(effectiveEndMin+FESTIVAL_BUFFER+travel);
          const{displayTitle:nt}=parseProgramTitle(nextFilm._title||'');
          const nShort=nt.length>22?nt.slice(0,20)+'…':nt;
          if(margin<0){
            warnHtml=`<div class="delay-warn"><span class="delay-warn-ico">${ICONS.alert}</span><span>Con el retraso terminas ~${minToStr(effectiveEndMin)}. Solo quedan <b>${toMin(nextFilm.time)-effectiveEndMin} min</b> antes de <b>${nShort}</b>${travel>0?` (${travel} min de viaje)`:''}</span></div>`;
          }else if(margin<15){
            warnHtml=`<div class="delay-warn warn-amber"><span class="delay-warn-ico">${ICONS.alert}</span><span>Terminas ~${minToStr(effectiveEndMin)}. Margen ajustado: <b>${margin} min</b> hasta <b>${nShort}</b>.</span></div>`;
          }
        }
      }else{
        delayHtml=`<div class="delay-row">
          <span class="delay-lbl">¿Retraso?</span>
          ${[10,15,20,30].map(m=>`<button class="delay-btn" onclick="setDelay('${safeT}','${next.day}','${next.time}',${m})" title="Reportar +${m} min">+${m}</button>`).join('')}
        </div>`;
      }
    }

    return`<div class="ctx-header">
      <div class="ctx-eyebrow">
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
        ${eyebrowLabel}
      </div>
      <div class="ctx-next-card" onclick="openPelSheet('${(next._title||'').replace(/'/g,"\\'")}')" style="cursor:pointer">
        ${src?`<img class="ctx-next-poster" src="${src}" onerror="this.style.opacity=0" alt="">`:
              `<div class="ctx-next-poster"></div>`}
        <div style="flex:1;min-width:0">
          <div class="ctx-next-title">${dt}</div>
          <div class="ctx-next-detail">${next.time} · ${vc.short}</div>
          ${badge}
        </div>
      </div>
      ${delayHtml}${warnHtml}
    </div>`;
  }

  // ── BETWEEN ─────────────────────────────────────────────────
  if(ph.phase==='between'){
    const{gapMin,gapFromMin,gapToMin,gapSuggestion,next}=ph;
    const h=Math.floor(gapMin/60),m=gapMin%60;
    const gapLabel=h>0?(m>0?`${h}h ${m}min`:`${h}h`):`${m} min`;
    const fromStr=`${String(Math.floor(gapFromMin/60)).padStart(2,'0')}:${String(gapFromMin%60).padStart(2,'0')}`;
    const toStr=`${String(Math.floor(gapToMin/60)).padStart(2,'0')}:${String(gapToMin%60).padStart(2,'0')}`;
    const now=simNow();
    const nowMin=now.getHours()*60+now.getMinutes();
    const fillPct=gapMin>0?Math.min(100,Math.round((nowMin-gapFromMin)/gapMin*100)):0;
    const suggest=gapSuggestion?(()=>{
      const{displayTitle:dt}=parseProgramTitle(gapSuggestion.title);
      const vc2=vcfg(gapSuggestion.venue);
      const dur=parseInt(gapSuggestion.duration)||90;
      const safeT=gapSuggestion.title.replace(/'/g,"\'");
      return`<div style="font-size:var(--t-sm);color:var(--gray);margin-bottom:var(--sp-1)">Cabe en tu hueco</div>
        <div class="ctx-suggest-card" onclick="openPelSheet('${safeT}')" style="cursor:pointer">
          <div class="ctx-suggest-badge">${gapSuggestion.time}<br>${dur}m</div>
          <div class="ctx-suggest-info">
            <div class="ctx-suggest-title">${dt.length>26?dt.slice(0,24)+'…':dt}</div>
            <div class="ctx-suggest-venue">${vc2.short}</div>
          </div>
        </div>`;
    })():`<div style="font-size:var(--t-caption);color:var(--gray)">Sin actividades disponibles en este tramo.</div>`;
    return`<div class="ctx-header">
      <div class="ctx-eyebrow ctx-eyebrow--free">
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="var(--green)" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
        Tiempo libre
      </div>
      <div class="ctx-main-title">${gapLabel} hasta tu siguiente actividad</div>
      <div class="ctx-gap-bar">
        <div class="ctx-gap-dot" style="background:var(--green)"></div>
        <div class="ctx-gap-line"><div class="ctx-gap-fill" style="width:${fillPct}%"></div></div>
        <div class="ctx-gap-dot" style="background:var(--amber)"></div>
      </div>
      <div class="ctx-gap-label-row">
        <span class="ctx-gap-label" style="color:var(--green)">${fromStr}</span>
        <span class="ctx-gap-label">${toStr} · ${(()=>{const{displayTitle:dt}=parseProgramTitle(next._title||'');return dt.length>18?dt.slice(0,16)+'…':dt;})()} </span>
      </div>
      <div style="margin-top:12px">${suggest}</div>
    </div>`;
  }

  // ── EVENING ─────────────────────────────────────────────────
  if(ph.phase==='evening'){
    const{todayScreenings}=ph;
    const pendingRating=todayScreenings.filter(s=>watched.has(s._title)&&!filmRatings[s._title]);
    const rated=todayScreenings.filter(s=>watched.has(s._title)&&filmRatings[s._title]);
    const total=todayScreenings.filter(s=>watched.has(s._title)).length;
    if(!total) return '';
    const starsStr=n=>starsText(n);
    // Posters tappables — igual que en Intereses, consistente con el resto de la app
    const filmRows=todayScreenings.filter(s=>watched.has(s._title)).map(s=>{
      const{displayTitle:dt}=parseProgramTitle(s._title||'');
      const f=FILMS.find(fi=>fi.title===s._title);
      const src=getFilmPoster(f)||'';
      const r=filmRatings[s._title];
      const safeT=(s._title||'').replace(/'/g,"\'");
      const stars=r?starsText(r):'';
      return`<div style="position:relative;flex-shrink:0;cursor:pointer" onclick="openPelSheet('${safeT}')">
        ${src
          ?`<img class="prio-chip-poster" src="${src}" onerror="this.style.opacity=0" alt="">`
          :`<div class="prio-chip-ph">🎬</div>`}
        ${r?`<div style="position:absolute;bottom:4px;left:0;right:0;text-align:center;font-size:var(--t-xs);color:var(--amber);letter-spacing:1px;text-shadow:0 1px 3px var(--overlay-85)">${stars}</div>`:''}
        ${!r?`<div style="position:absolute;bottom:4px;left:0;right:0;text-align:center">
          <button onclick="event.stopPropagation();openPostViewRating('${safeT}','${s.day||''}','${s.time||''}','${(s.venue||'').replace(/'/g,"\'")}','${s.duration||''}')" style="background:var(--overlay-70);border:1px solid var(--white-15);border-radius:var(--r-pill);color:var(--white);font-size:var(--t-xs);font-weight:var(--w-bold);font-family:var(--font);padding:2px 6px;cursor:pointer">★</button>
        </div>`:''}
      </div>`;
    }).join('');
    const dayName=DAY_A[todayScreenings[0]?.day]||'Hoy';
    return`<div class="ctx-header">
      <div class="ctx-eyebrow ctx-eyebrow--past">
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
        Tu ${dayName.toLowerCase()} en ${(FESTIVAL_CONFIG[_activeFestId]||{}).name||'el festival'}
      </div>
      <div class="ctx-main-title">${total} película${total!==1?'s':''} ${total===1?'vista':'vistas'} hoy</div>
      ${pendingRating.length?`<div class="ctx-sub" style="margin-bottom:12px">${pendingRating.length===1?'Una pendiente de calificar.':'Podés calificarlas ahora.'}</div>`:`<div style="margin-bottom:12px"></div>`}
      <div style="display:flex;gap:10px;overflow-x:auto;padding-bottom:2px">${filmRows}</div>
    </div>`;
  }

  return '';
}

function _renderSavedAgendaHTML(){
  // Post-festival: el ENDED header es el contenido completo
  if(festivalEnded()){
    const _eh=renderContextualHeader();
    return _eh?`<div class="saved-agenda">${_eh}</div>`:'';
  }
  if(!savedAgenda||!savedAgenda.schedule.length) return emptyStateHero(ICONS.calendar,'Tu plan aparecerá aquí','Añade lo que no quieres perderte y armamos tu plan.','Ir a Planear',"switchMainNav('mnav-planner');showAgView()");
  const all=savedAgenda.schedule;
  const planTitles=new Set(all.map(s=>s._title));
  const archive=all.filter(s=>screeningPassed(s)||watched.has(s._title));
  // Películas marcadas vistas FUERA del plan — en watched pero no en savedAgenda
  const watchedOutsidePlan=[...watched]
    .filter(t=>!planTitles.has(t))
    .map(t=>FILMS.find(f=>f.title===t))
    .filter(Boolean)
    .filter((f,i,arr)=>arr.findIndex(x=>x.title===f.title)===i);
  const upcoming=all.filter(s=>!screeningPassed(s)&&!watched.has(s._title));
  const futureItems=upcoming.filter(s=>!isToday(s.day));
  const byDay={};
  futureItems.forEach(s=>{if(!byDay[s.day])byDay[s.day]=[];byDay[s.day].push(s);});

  const festDays=['Martes','Miércoles','Jueves','Viernes','Sábado','Domingo'];
  const today=simTodayStr();
  const dayIdx=festDays.findIndex(d=>FESTIVAL_DATES[d]===today);
  const currentDayNum=dayIdx>=0?dayIdx+1:null;
  const viewedCount=all.filter(s=>watched.has(s._title)).length;
  const progressPct=dayIdx>=0?Math.round((dayIdx/5)*100):0;
  const _mpSwitch=`<button class="mplan-act-btn" onclick="_scrollToMplanDetail()" title="Ir al detalle del día">
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><polyline points="19 12 12 19 5 12"/></svg>
    Ver día
  </button>`;
  const progressBar=currentDayNum?`<div class="festival-progress" style="display:flex;align-items:center;gap:8px">
    <div style="flex:1">
      <div class="festival-progress-text"><span>Día <b>${currentDayNum}</b> de 6</span><span style="color:var(--amber)">${ICONS.check} ${viewedCount} ${viewedCount===1?'vista':'vistas'}</span></div>
      <div class="festival-progress-bar"><div class="festival-progress-fill" style="width:${progressPct}%"></div></div>
    </div>
  </div>`:'';
  const planActions=`<div class="mplan-act-row">
    ${_mpSwitch}
    <button class="mplan-act-btn" onclick="sharePlan()">${ICONS.share} Compartir</button>
    <button class="mplan-act-btn" onclick="exportICS()">${ICONS.calendar} Calendario</button>
  </div>`;

  const _ctxHeader=renderContextualHeader();
  const _nextStrip=''; // delay controls integrated into ctx-header
  const _unconfirmed=renderUnconfirmed(all);
  let html=`<div class="saved-agenda">
    ${_nextStrip}${_unconfirmed}${_ctxHeader}
    ${progressBar}${planActions}
`;

  // ── CTA B: post-eliminación (temporal, auto-dismiss 6s) ──
  if(_ctaRemovedVisible){
    html+=`<div class="cta-ctx cta-ctx-b" onclick="switchMainNav('mnav-planner');showAgView()">
      <div class="cta-ctx-ico" style="display:flex;align-items:center;justify-content:center">${ICONS.undo}</div>
      <div class="cta-ctx-body">
        <div class="cta-ctx-title cta-ctx-title-b">¿Quieres poner otra cosa ahí?</div>
        <div class="cta-ctx-sub">Hay sugerencias abajo que caben en ese hueco, o recalcula en Planear.</div>
      </div>
      <div class="cta-ctx-arr cta-ctx-arr-b">${ICONS.chevronR}</div>
    </div>`;
  }

  if(archive.length||watchedOutsidePlan.length){
    const totalWatched=archive.length+watchedOutsidePlan.length;
    const archByDay={};
    archive.forEach(s=>{if(!archByDay[s.day])archByDay[s.day]=[];archByDay[s.day].push(s);});
    html+=`<div class="archive-toggle" onclick="toggleArchive()">
      <span class="archive-toggle-lbl">Historial (${totalWatched})</span>
      <span id="arch-arrow">${ICONS.chevronD}</span>
    </div>
    <div class="archive-body${archiveOpen?' open':''}" id="archive-body">
      ${archive.length?DAY_KEYS.filter(d=>archByDay[d]).map(day=>`
        <div class="saved-day-lbl">${dayChip(day)}</div>
        ${archByDay[day].map(s=>{
          const vc2=vcfg(s.venue),sl=sala(s.venue);
          const _af=FILMS.find(fi=>fi.title===s._title);const _ap=_af?getFilmPoster(_af):null;
          const _safeMpT2=(s._title||"").replace(/'/g,"\'");
          const _aph=_ap?`<img class="lb-poster" src="${_ap}" loading="lazy" style="cursor:pointer" onclick="event.stopPropagation();openPelSheet('${_safeMpT2}')" onerror="this.outerHTML='<div class=lb-poster-ph>🎬</div>'" alt="">`:'<div class="lb-poster-ph">🎬</div>';
          return`<div class="saved-item done">
            ${_aph}
            <div class="saved-time">${s.time}</div>
            <div class="saved-info">
              <div class="saved-title">${s._title}</div>
              <div class="saved-venue">${ICONS.pin} ${vc2.short}${sl?' · '+sl:''}</div>
            </div>
            <button class="saved-check done" data-wt="${(s._title||'').replace(/"/g,'&quot;')}" onclick="toggleWatched(this.dataset.wt,event)" >No vista</button>
          </div>`;
        }).join('')}`).join(''):''}
      ${watchedOutsidePlan.length?`
        <div class="archive-out-lbl">Vistas fuera del Plan</div>
        ${watchedOutsidePlan.map(f=>{
          const _ap=getFilmPoster(f);
          const _aph=_ap?`<img class="lb-poster" src="${_ap}" loading="lazy" onerror="this.outerHTML='<div class=lb-poster-ph>🎬</div>'" alt="">`:'<div class="lb-poster-ph">🎬</div>';
          return`<div class="saved-item done">
            ${_aph}
            <div class="saved-time">${f.flags||'🌐'}</div>
            <div class="saved-info">
              <div class="saved-title">${f.title}</div>
              <div class="saved-venue">${ICONS.clock} ${f.duration||'—'}</div>
            </div>
            <button class="saved-check done" data-wt="${(f.title||'').replace(/"/g,'&quot;')}" onclick="toggleWatched(this.dataset.wt,event)" >No vista</button>
          </div>`;
        }).join('')}`:''}
    </div>`;
  }


  html+=renderMiPlanCalendar();

  // Sugerencias solo durante el festival
  if(!festivalEnded()){
  const suggsByDay=getSuggestions();
  const suggDays=DAY_KEYS.filter(d=>suggsByDay[d]&&suggsByDay[d].length>0);
  html+=`<div class="suggestion-wrap">
    <div class="sec-hdr" style="margin-bottom:8px">${ICONS.search} Sugerencias</div>`;
  if(suggDays.length){
    suggDays.forEach(day=>{
      html+=`<div class="suggestion-day-lbl">${dayChip(day)}</div>`;
      html+=suggsByDay[day].map(f=>{
        const vc2=vcfg(f.venue),sl=sala(f.venue);
        const _sp=getFilmPoster(f);
        const _sph=_sp?`<img class="lb-poster" src="${_sp}" loading="lazy" onerror="this.outerHTML='<div class=lb-poster-ph>🎬</div>'" alt="">`:'<div class="lb-poster-ph">🎬</div>';
        return`<div class="suggestion-item" onclick="openPelSheet('${f.title.replace(/'/g,"\\'")}')">
          ${_sph}
          <div class="suggestion-time">${f.time}</div>
          <div class="suggestion-info">
            <div class="suggestion-title">${(()=>{const{displayTitle:_dt}=parseProgramTitle(f.title);return _dt;})()}</div>
            <div class="suggestion-meta">${f.section||''}</div>
            <div class="suggestion-meta-ico">${ICONS.clock} ${f.duration}</div>
            <div class="suggestion-meta-ico">${ICONS.pin} ${vc2.short}${sl?' · '+sl:''}</div>
            ${f._travelWarn?`<div class="suggestion-travel-warn">${f._travelWarn}</div>`:''}
            ${f.gapCtx?`<div style="font-size:var(--t-xs);color:var(--gray);margin-top:2px;font-style:italic">${f.gapCtx.length>35?f.gapCtx.slice(0,33)+'…':f.gapCtx}</div>`:''}
          </div>
          <button class="suggestion-add" onclick="event.stopPropagation();addSuggestion('${f.title.replace(/'/g,"\\'")}','${f.day}','${f.time}')" style="${f._isRestored?'border-color:var(--orange);color:var(--orange);background:var(--amber-10)':''}">
            ${f._isRestored?`${ICONS.undo} Restaurar`:`${ICONS.plus} Añadir`}
          </button>
        </div>`;
      }).join('');
    });
    html+='</div>'; // close suggestion-wrap content
  } else {
    html+=emptyState(ICONS.search,'Tu plan está bien cubierto.',UI.empty.planCovered);
  }
  html+='</div>'; // close suggestion-wrap
  } // end !festivalEnded

  html+='</div>';
  return html;
}
let archiveOpen=false;
function toggleArchive(){
  archiveOpen=!archiveOpen;
  const body=document.getElementById('archive-body');
  const arrow=document.getElementById('arch-arrow');
  if(body) body.classList.toggle('open',archiveOpen);
  if(arrow){arrow.style.transform=archiveOpen?'rotate(180deg)':'rotate(0deg)';}
}








/* ── Display name — cadena de prioridad para imagen compartida ──
   1. Supabase user_metadata.display_name (cuenta / app nativa)
   2. localStorage 'otrofestiv_display_name' (web sin cuenta)
   3. Email prefix (fallback con cuenta)
   4. null (anónimo)
*/
function _getDisplayName(){
  if(_sbUser){
    const meta=_sbUser.user_metadata||{};
    if(meta.display_name) return meta.display_name;
  }
  const local=localStorage.getItem('otrofestiv_display_name');
  if(local) return local;
  if(_sbUser&&_sbUser.email) return _sbUser.email.split('@')[0];
  return null;
}
async function _saveDisplayName(name){
  const n=name.trim().slice(0,30);
  if(!n) return;
  localStorage.setItem('otrofestiv_display_name',n);
  if(_sb&&_sbUser){
    try{ await _sb.auth.updateUser({data:{display_name:n}}); }catch(e){}
  }
}


function _promptDisplayName(onSave){
  const prev=document.getElementById('display-name-sheet');if(prev)prev.remove();
  const el=document.createElement('div');
  el.id='display-name-sheet';
  el.style.cssText='position:fixed;inset:0;background:var(--overlay-70);z-index:9999;display:flex;align-items:flex-end;justify-content:center';
  el.innerHTML=`<div style="background:var(--surf-2);border-radius:var(--r-sheet) var(--r-sheet) 0 0;padding:24px 20px 40px;width:100%;max-width:480px;box-sizing:border-box">
    <div style="width:36px;height:4px;background:var(--bdr);border-radius:2px;margin:0 auto 20px"></div>
    <div style="font-size:var(--t-base);font-weight:var(--w-bold);color:var(--white);margin-bottom:6px">¿Cómo quieres aparecer en tu plan?</div>
    <div style="font-size:var(--t-sm);color:var(--gray);margin-bottom:16px">Aparecerá en la imagen cuando la compartas.</div>
    <input id="dname-input" type="text" maxlength="30" placeholder="Tu nombre" autocomplete="name"
      style="width:100%;background:var(--surf);border:1px solid var(--bdr);border-radius:var(--r-md);padding:12px 14px;font-size:var(--t-base);color:var(--white);outline:none;box-sizing:border-box;font-family:var(--font);margin-bottom:12px">
    <button id="dname-save" style="width:100%;background:var(--amber);border:none;border-radius:var(--r-md);padding:var(--sp-btn) 0;font-size:var(--t-base);font-weight:var(--w-bold);color:#000;cursor:pointer;font-family:var(--font)">Guardar y compartir</button>
  </div>`;
  document.body.appendChild(el);
  const input=document.getElementById('dname-input');
  input.focus();
  document.getElementById('dname-save').onclick=async()=>{
    const v=input.value.trim();
    if(!v){input.style.borderColor='var(--red)';return;}
    await _saveDisplayName(v);
    el.remove();
    if(onSave) onSave();
  };
  el.addEventListener('click',e=>{if(e.target===el)el.remove();});
}

/* ── SHARE/EXPORT: imagen, ICS ──────────────────────────────────────── */
async function sharePlan(){
  if(!savedAgenda||!savedAgenda.schedule||!savedAgenda.schedule.length){
    showToast('No tienes un plan guardado','warn');return;
  }
  // Pedir nombre si no existe — solo la primera vez
  if(!_getDisplayName()){
    _promptDisplayName(()=>sharePlan());
    return;
  }
  let canvas,dataUrl;
  try{
    canvas=_buildAgendaCanvas();
    dataUrl=canvas.toDataURL('image/png');
    if(!dataUrl||dataUrl==='data:,') throw new Error('canvas vacío');
  }catch(e){showToast('Error al generar imagen','err');return;}

  // Web Share API con archivo (iOS Safari 15+, Chrome Android 86+)
  if(navigator.share&&navigator.canShare){
    canvas.toBlob(async blob=>{
      if(!blob){_dlDirect(dataUrl);return;}
      const cfg=FESTIVAL_CONFIG[_activeFestId]||{};
      const fname=`otrofestiv-${(cfg.shortName||'plan').toLowerCase().replace(/\s+/g,'-')}.png`;
      const file=new File([blob],fname,{type:'image/png'});
      if(navigator.canShare({files:[file]})){
        try{
          await navigator.share({files:[file],title:`Mi Plan · ${cfg.name||'Otrofestiv'}`});
          showToast('Compartido ✓','info');
        }catch(e){if(e.name!=='AbortError') _dlDirect(dataUrl);}
      }else{_dlDirect(dataUrl);}
    },'image/png');
  }else{
    // Fallback desktop: descarga directa
    _dlDirect(dataUrl);
  }
}



/* ── SHARE/EXPORT: imagen, ICS ──────────────────────────────────────── */
function shareAsImage(){
  if(!savedAgenda||!savedAgenda.schedule||!savedAgenda.schedule.length){
    showToast('No tienes un plan guardado','warn'); return;
  }

  // ── Guardia de integridad del plan ────────────────────────────
  // Antes de generar la imagen verificamos tres condiciones:
  // 1. Que todas las películas del plan siguen en la watchlist
  // 2. Que no hay conflictos internos entre funciones del plan
  // 3. Que al menos una función no ha pasado ya
  const issues=[];

  // 1. Películas del plan ya no en watchlist
  const notInWL=savedAgenda.schedule.filter(s=>!watchlist.has(s._title));
  if(notInWL.length){
    const names=notInWL.map(s=>s._title.length>20?s._title.slice(0,18)+'…':s._title).join(', ');
    issues.push(`${notInWL.length} película${notInWL.length>1?'s':''} ya no están en Intereses: ${names}`);
  }

  // 2. Conflictos internos entre funciones del plan
  const sched=savedAgenda.schedule;
  const conflicting=[];
  for(let i=0;i<sched.length;i++){
    for(let j=i+1;j<sched.length;j++){
      if(sched[i].day===sched[j].day && screensConflict(sched[i],sched[j])){
        conflicting.push(sched[i]._title);
      }
    }
  }
  if(conflicting.length){
    const names=[...new Set(conflicting)].map(t=>t.length>20?t.slice(0,18)+'…':t).join(', ');
    issues.push(`Hay actividades con horario solapado: ${names}`);
  }

  // 3. Plan completamente pasado
  const stillActive=savedAgenda.schedule.some(s=>!screeningPassed(s));
  if(!stillActive) issues.push(UI.empty.allPassed);

  // Si hay problemas: mostrar advertencia con opción de continuar igual
  if(issues.length){
    const msg=`<b>Tu plan puede estar desactualizado</b><br><br>`
      +issues.map(i=>`• ${i}`).join('<br>')
      +`<br><br>¿Compartir la imagen de todas formas?`;
    showActionModal(
      `${ICONS.share} Compartir imagen`,
      msg,
      'Compartir igual',
      ()=>{_generateAndShare();},
      'Revisar plan primero'
    );
    return;
  }

  _generateAndShare();
}

function _generateAndShare(){
  let canvas,dataUrl;
  try{
    canvas=_buildAgendaCanvas();
    dataUrl=canvas.toDataURL('image/png');
    if(!dataUrl||dataUrl==='data:,') throw new Error('canvas vacío');
  }catch(e){
    showToast('Error al generar imagen','err'); return;
  }
  _showImageModal(dataUrl,canvas);
}

function _buildAgendaCanvas(){
  const DPR=Math.min(window.devicePixelRatio||2,3);
  const cfg=FESTIVAL_CONFIG[_activeFestId]||{};
  const festDays=cfg.days||DAY_KEYS.map(k=>({k,lbl:k.slice(0,3).toUpperCase(),d:parseInt(k.slice(-2))||''}));
  const DAYS=festDays.map(d=>d.k);
  const DS=festDays.map(d=>d.lbl);
  const DN=festDays.map(d=>String(d.d));
  const byDay={};
  DAYS.forEach(d=>{byDay[d]=[];});
  (savedAgenda.schedule||[]).forEach(s=>{if(byDay[s.day])byDay[s.day].push(s);});
  DAYS.forEach(d=>{byDay[d].sort((a,b)=>a.time.localeCompare(b.time));});
  const active=DAYS.filter(d=>byDay[d].length>0);
  const nC=active.length||1;
  const cleanDur=s=>(s.duration||'').replace(/\s*min\s*min/i,'min').trim();
  const PAD=24,HDR=72,COL_HDR=46,CW=190,CGAP=10,CARD_PAD=12,CARD_R=8,CARD_GAP=8;
  const FONT_T=12,LINE_T=16,MAX_TL=3,CARD_MIN=90;
  const cv0=document.createElement('canvas');
  const c0=cv0.getContext('2d');
  c0.font=`600 ${FONT_T}px system-ui,-apple-system,sans-serif`;
  const cHts={};
  active.forEach(day=>{
    cHts[day]=byDay[day].map(s=>{
      const tl=_measureLines(c0,s._title||'',CW-CARD_PAD*2-6,MAX_TL);
      return Math.max(CARD_PAD+18+4+tl*LINE_T+4+14+CARD_PAD,CARD_MIN);
    });
  });
  const maxColH=active.reduce((mx,day)=>{
    const h=cHts[day].reduce((s,h)=>s+h+CARD_GAP,0)-CARD_GAP;
    return Math.max(mx,h);
  },0);
  const W=PAD*2+nC*CW+(nC-1)*CGAP;
  const H=HDR+PAD+COL_HDR+CARD_GAP+maxColH+PAD*2;
  const cv=document.createElement('canvas');
  cv.width=W*DPR;cv.height=H*DPR;
  const c=cv.getContext('2d');
  c.scale(DPR,DPR);
  c.fillStyle='#0A0A0A';c.fillRect(0,0,W,H);
  // Banner: --surf-2 (#1A1A1A) — gris sobrio de la paleta
  c.fillStyle='#1A1A1A';c.fillRect(0,0,W,HDR);
  // Wordmark: "Otro" blanco + "festiv" ámbar — igual que en la app
  c.font='800 22px system-ui,-apple-system,sans-serif';
  c.textBaseline='alphabetic';
  c.fillStyle='#FFFFFF';
  const otroW=c.measureText('Otro').width;
  c.fillText('Otro',PAD,HDR/2+4);
  c.fillStyle='#D4900A';
  c.fillText('festiv',PAD+otroW,HDR/2+4);
  // Subtítulo: --gray (#888888)
  c.fillStyle='#888888';
  c.font='500 11px system-ui,-apple-system,sans-serif';
  const _dn=_getDisplayName();
  const _sub=(_dn?_dn+' · ':'')+'Mi Plan · '+(cfg.name||'Festival')+' · '+active.length+' día'+(active.length!==1?'s':'');
  c.fillText(_sub,PAD,HDR/2+20);
  active.forEach((day,ci)=>{
    const x=PAD+ci*(CW+CGAP);
    const di=DAYS.indexOf(day);
    const films=byDay[day];
    const hy=HDR+PAD;
    c.fillStyle='rgba(212,144,10,0.12)';_rr(c,x,hy,CW,COL_HDR,8);c.fill();
    c.fillStyle='rgba(212,144,10,0.5)';c.fillRect(x,hy+COL_HDR-1,CW,1);
    c.fillStyle='#D4900A';
    c.font='700 9px system-ui,-apple-system,sans-serif';
    c.textBaseline='top';c.fillText(DS[di],x+12,hy+9);
    c.fillStyle='#FFFFFF';
    c.font='700 20px system-ui,-apple-system,sans-serif';
    c.fillText(DN[di],x+12,hy+20);
    let cardY=hy+COL_HDR+CARD_GAP;
    films.forEach((s,fi)=>{
      const ch=cHts[day][fi];
      const prio=prioritized&&prioritized.has&&prioritized.has(s._title);
      const dur=cleanDur(s);
      c.fillStyle=prio?'rgba(212,144,10,0.18)':'rgba(255,255,255,0.06)';
      _rr(c,x,cardY,CW,ch,CARD_R);c.fill();
      c.fillStyle=prio?'#D4900A':'rgba(212,144,10,0.35)';
      _rr(c,x,cardY,4,ch,CARD_R);c.fill();
      const tx=x+CARD_PAD+6;let ty=cardY+CARD_PAD;
      c.fillStyle='#D4900A';
      c.font='700 14px system-ui,-apple-system,sans-serif';
      c.textBaseline='top';c.fillText(s.time,tx,ty);
      if(dur){const hw=c.measureText(s.time).width;c.fillStyle='#666';c.font='400 10px system-ui,-apple-system,sans-serif';c.fillText(' · '+dur,tx+hw,ty+2);}
      ty+=22;
      c.fillStyle='#FFF';c.font=`600 ${FONT_T}px system-ui,-apple-system,sans-serif`;
      ty=_drawWrapped(c,s._title||'',tx,ty,CW-CARD_PAD*2-6,LINE_T,MAX_TL);
      if(s.venue){const _vc=vcfg(s.venue);const _vraw=_vc.short||s.venue;const v=_vraw.length>30?_vraw.slice(0,28)+'…':_vraw;c.fillStyle='#5A5A5A';c.font='400 10px system-ui,-apple-system,sans-serif';c.textBaseline='top';c.fillText(v,tx,cardY+ch-CARD_PAD-11);}
      cardY+=ch+CARD_GAP;
    });
  });
  c.fillStyle='rgba(212,144,10,0.2)';c.fillRect(0,H-1,W,1);
  return cv;
}

function _measureLines(c,text,maxW,maxLines){
  const words=text.split(' ');let line='',lines=1;
  for(let i=0;i<words.length;i++){
    const t=line?line+' '+words[i]:words[i];
    if(c.measureText(t).width>maxW&&line){if(lines>=maxLines)return maxLines;lines++;line=words[i];}
    else{line=t;}
  }
  return lines;
}

function _drawWrapped(c,text,x,y,maxW,lh,maxLines){
  c.textBaseline='top';
  const words=text.split(' ');let line='',ln=0;
  for(let i=0;i<words.length;i++){
    const t=line?line+' '+words[i]:words[i];
    if(c.measureText(t).width>maxW&&line){
      if(ln>=maxLines-1){c.fillText(line+'…',x,y+ln*lh);return y+ln*lh+lh;}
      c.fillText(line,x,y+ln*lh);line=words[i];ln++;
    }else{line=t;}
  }
  if(line)c.fillText(line,x,y+ln*lh);
  return y+ln*lh+lh;
}

function _rr(c,x,y,w,h,r){
  r=Math.min(r,w/2,h/2);
  c.beginPath();c.moveTo(x+r,y);c.lineTo(x+w-r,y);c.quadraticCurveTo(x+w,y,x+w,y+r);
  c.lineTo(x+w,y+h-r);c.quadraticCurveTo(x+w,y+h,x+w-r,y+h);
  c.lineTo(x+r,y+h);c.quadraticCurveTo(x,y+h,x,y+h-r);
  c.lineTo(x,y+r);c.quadraticCurveTo(x,y,x+r,y);c.closePath();
}

function _showImageModal(dataUrl,canvas){
  const prev=document.getElementById('img-share-modal');if(prev)prev.remove();
  const isIOS=/iPad|iPhone|iPod/.test(navigator.userAgent);
  const ov=document.createElement('div');
  ov.id='img-share-modal';
  ov.style.cssText='position:fixed;inset:0;background:var(--overlay-92);z-index:9999;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:20px;box-sizing:border-box;gap:14px';
  const hint=document.createElement('p');
  hint.style.cssText='color:var(--gray);font-size:var(--t-caption);font-family:system-ui;text-align:center;margin:0;line-height:1.6';
  hint.textContent=isIOS?'Mantén presionada la imagen — Añadir a Fotos':'Toca Descargar para guardar';
  ov.appendChild(hint);
  const img=document.createElement('img');
  img.src=dataUrl;
  img.style.cssText='max-width:100%;max-height:62vh;border-radius:var(--r);display:block;box-shadow:0 8px 32px var(--overlay-70)';
  ov.appendChild(img);
  const row=document.createElement('div');
  row.style.cssText='display:flex;gap:10px;width:100%;max-width:320px';
  if(!isIOS){
    const btnDl=document.createElement('button');
    btnDl.textContent='⬇ Descargar';
    btnDl.style.cssText='flex:1;padding:var(--sp-btn);background:var(--amber);color:var(--black);border:none;border-radius:var(--r-md);font-size:var(--t-base);font-family:system-ui;font-weight:var(--w-bold);cursor:pointer';
    btnDl.onclick=function(){
      if(navigator.share&&navigator.canShare){
        canvas.toBlob(blob=>{
          if(!blob){_dlDirect(dataUrl);return;}
          const file=new File([blob],'otrofestiv-miplan.png',{type:'image/png'});
          if(navigator.canShare({files:[file]})){navigator.share({files:[file]}).then(()=>{ov.remove();showToast('Compartido ✓','info');}).catch(()=>_dlDirect(dataUrl));}
          else{_dlDirect(dataUrl);}
        },'image/png');
      }else{_dlDirect(dataUrl);}
    };
    row.appendChild(btnDl);
  }
  const btnX=document.createElement('button');
  btnX.textContent='Cerrar';
  btnX.style.cssText=(isIOS?'flex:1;':'')+'padding:var(--sp-btn) var(--sp-5);background:rgba(255,255,255,0.08);color:var(--gray2);border:none;border-radius:var(--r-md);font-size:var(--t-base);font-family:system-ui;cursor:pointer';
  btnX.onclick=()=>ov.remove();
  row.appendChild(btnX);
  ov.appendChild(row);
  ov.addEventListener('click',e=>{if(e.target===ov)ov.remove();});
  document.body.appendChild(ov);
}

function _dlDirect(dataUrl){
  const a=document.createElement('a');
  a.href=dataUrl;a.download='otrofestiv-miplan.png';
  a.style.cssText='position:fixed;top:-999px;left:-999px;opacity:0';
  document.body.appendChild(a);a.click();
  setTimeout(()=>{document.body.removeChild(a);showToast('Imagen guardada ✓','info');},200);
}
function exportICS(){
  if(!savedAgenda||!savedAgenda.schedule.length){showToast('No tienes un plan guardado','warn');return;}
  const pad=n=>String(n).padStart(2,'0');
  const fmt=dt=>`${dt.getFullYear()}${pad(dt.getMonth()+1)}${pad(dt.getDate())}T${pad(dt.getHours())}${pad(dt.getMinutes())}00`;
  const _icsCfg=FESTIVAL_CONFIG[_activeFestId]||{};
  const _icsId=(_icsCfg.shortName||'festival').toLowerCase().replace(/\s+/g,'');
  const lines=['BEGIN:VCALENDAR','VERSION:2.0',`PRODID:-//Otrofestiv//${_icsId}//ES`,'CALSCALE:GREGORIAN','METHOD:PUBLISH'];
  savedAgenda.schedule.forEach(s=>{
    const dateStr=FESTIVAL_DATES[s.day];if(!dateStr) return;
    const start=new Date(`${dateStr}T${s.time}:00`);
    const dur=s.duration?parseInt(s.duration):90;
    const end=new Date(start.getTime()+dur*60000);
    lines.push('BEGIN:VEVENT',
      `DTSTART:${fmt(start)}`,`DTEND:${fmt(end)}`,
      `SUMMARY:${s._title}`,
      `LOCATION:${s.venue||''}`,
      `DESCRIPTION:${_icsCfg.name||'Festival'} · ${s.section||''} · ${s.duration||''}`,
      'END:VEVENT');
  });
  lines.push('END:VCALENDAR');
  const blob=new Blob([lines.join('\r\n')],{type:'text/calendar'});
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=`otrofestiv-${_icsId}.ics`;a.click();
  showToast('Calendario exportado','info');
}
function clearSavedAgenda(){
  showDestructiveModal(`Borrar plan`,
    'Se eliminará tu plan completo. Esta acción no se puede deshacer.',
    'Borrar plan',
    ()=>{savedAgenda=null;localStorage.removeItem(`${FESTIVAL_STORAGE_KEY}saved`);renderAgenda();});
}

// ── RESULT HTML ──
let cachedResult=null;

function buildResultHTML(scenarios){
  if(!scenarios||!scenarios.length)
    return`<div class="ag-calc-prompt">No hay combinaciones posibles. Ajusta la disponibilidad o añade más títulos.</div>`;
  const{currentIdx}=cachedResult;
  const sc=scenarios[currentIdx],n=scenarios.length;
  const pending=[...watchlist].filter(t=>!watched.has(t)&&FILMS.some(f=>f.title===t&&!screeningPassed(f)));
  const total=pending.length,ok=sc.schedule.length,bad=sc.excluded.length;
  const isOptimo=currentIdx===0;

  // ── Header: Plan óptimo vs Variación ──
  const planLabel=isOptimo?`${ICONS.calendar} Plan óptimo`:`Variación ${currentIdx}`;

  // ── Navigation ──
  let navHtml='';
  if(n>1){
    const prevLabel=currentIdx<=1?`${ICONS.calendar} Plan óptimo`:`Variación ${currentIdx-1}`;
    const nextLabel=currentIdx===0?'Variación 1':`Variación ${currentIdx+1}`;
    // Dots: un botón por opción, activo destacado
    // Escalable: generado desde scenarios.length sin hardcodear
    const dots=scenarios.map((sc_,di)=>{
      const isActive=di===currentIdx;
      const isOptimoDot=di===0;
      const cls=isActive?(isOptimoDot?'ag-nav-dot active-star active':'ag-nav-dot active'):'ag-nav-dot';
      const label=isOptimoDot?'★':di.toString();
      const titleStr=isOptimoDot?'Plan óptimo':'Variación '+di;
      return`<button class="${cls}" onclick="jumpToScenario(${di})" title="${titleStr}">${label}</button>`;
    }).join('');
    navHtml=`<div class="ag-nav" style="margin-top:8px">${dots}</div>`;
  }

  const saveBtnHtml=`<button class="ag-save-btn" onclick="saveCurrentScenario()">${ICONS.calendar} Elegir este plan</button>`;
  let html=`<div class="ag-summary">
    <div class="ag-summary-title" style="font-size:${isOptimo?'var(--t-md)':'var(--t-base)'};color:${isOptimo?'var(--white)':'var(--gray)'}">${planLabel}</div>
    <div class="ag-summary-text" style="margin-top:var(--sp-1)">
      <span class="ok"><b>${ok}</b></span> de <b>${total}</b> película${total!==1?'s':''}
      ${bad?`<span class="conflict-label"> · <b>${bad}</b> fuera del plan</span>`:''}
    </div>
    ${sc.incompatiblePriorities?`<div class="ag-warn" style="margin-top:var(--sp-2)">${ICONS.alert} Las prioridades se solapan entre sí — plan calculado sin forzarlas.</div>`:''}
    ${navHtml}
  </div>
`;

  // ── Film list by day ──
  const byDay={};
  sc.schedule.forEach(s=>{if(!byDay[s.day])byDay[s.day]=[];byDay[s.day].push(s);});
  DAY_KEYS.forEach(day=>{
    const films=byDay[day];if(!films||!films.length) return;
    html+=`<div class="ag-day-label"><span class="ag-day-name">${dayChip(day)}</span><span class="ag-day-cnt">${films.length}</span></div>`;
    films.forEach((s,i)=>{
      if(i>0){const warn=travelWarn(films[i-1],s);if(warn) html+=`<div class="ag-warn">${warn}</div>`;}
      html+=mkAgendaRow(s,'scenario');
    });
  });

  // ── Películas no incluidas — bloque visual con posters ────────────
  // Regla de diseño: cada película excluida merece identidad visual,
  // no solo texto. El poster permite reconocimiento inmediato.
  // CTA claro y accionable — no texto pasivo.
  if(sc.excluded.length){
    const excPosters=sc.excluded.map(t=>{
      const{displayTitle:dt}=parseProgramTitle(t);
      const f=FILMS.find(fi=>fi.title===t);
      const poster=f?getFilmPoster(f):null;
      const short=dt.length>18?dt.slice(0,16)+'…':dt;
      const safeT=t.replace(/'/g,"\\'");
      return`<div class="ag-excl-item" onclick="openPelSheet('${safeT}')">
        ${poster
          ?`<img class="ag-excl-poster" src="${poster}" onerror="this.outerHTML='<div class=ag-excl-poster-ph></div>'" alt="">`
          :`<div class="ag-excl-poster-ph"></div>`}
        <div class="ag-excl-title">${short}</div>
      </div>`;
    }).join('');
    html+=`<div class="ag-excl-block">
      <div class="ag-excl-eyebrow">
        <span class="ag-excl-label">No incluidas</span>
        <span class="ag-excl-count">${sc.excluded.length}</span>
      </div>
      <div class="ag-excl-strip">${excPosters}</div>
    </div>`;
  }

  // ── CTA único — un patrón, sin competencia, consistente en todas las variaciones ──
  html+=`<div class="ag-summary" style="margin-top:var(--sp-4)">
    ${navHtml}
    <div style="margin-top:${navHtml?'var(--sp-3)':'0'}">${saveBtnHtml}</div>
  </div>`;
  return html;
}


