// ══ Programa — mplan-list, programa chips, grid, render() ══
// SOURCE: index.html L7113-7690

function renderMiPlanList(schedule){
  try{
  // Vista lista compacta — mismo patrón que Hoy/Mañana en Programa
  const upcoming=schedule
    .filter(s=>!watched.has(s._title))
    .sort((a,b)=>{
      const da=new Date(`${FESTIVAL_DATES[a.day]}T${a.time}:00`);
      const db=new Date(`${FESTIVAL_DATES[b.day]}T${b.time}:00`);
      return da-db;
    });
  if(!upcoming.length) return '<div style="padding:var(--sp-5) var(--sp-4);text-align:center;color:var(--gray);font-size:var(--t-base)">Sin actividades pendientes</div>';
  
  // Agrupar por día
  const byDay={};
  upcoming.forEach(s=>{if(!byDay[s.day])byDay[s.day]=[];byDay[s.day].push(s);});
  
  return`<div class="mplan-list-view">${
    DAY_KEYS.filter(d=>byDay[d]).map(day=>`
      <div class="mplan-list-day">${day}</div>
      ${byDay[day].map(s=>{
        const{displayTitle:dt}=parseProgramTitle(s._title||'');
        const vc=vcfg(s.venue);
        const src=getFilmPoster(FILMS.find(fi=>fi.title===s._title&&fi.day===s.day))||'';
        const safeT=(s._title||'').replace(/'/g,"\'");
        const isW=watched.has(s._title);
        const isPassed=screeningPassed(s);
        return`<div class="mplan-list-item${isPassed?' past-card':''}" onclick="openPelSheet('${safeT}')">
          ${src
            ?`<img class="mplan-list-poster" src="${src}" loading="lazy" onerror="this.style.opacity=0" alt="" style="${isPassed?'opacity:.4':''}">`
            :`<div class="mplan-list-poster"></div>`}
          <div class="mplan-list-info">
            <div class="mplan-list-title" style="${isPassed?'opacity:.5':''}">${dt}</div>
            <div class="mplan-list-meta">${s.time} · ${vc.short}${FILMS.find(fi=>fi.title===s._title)?.is_cortos?' · Cortos':''}</div>
          </div>
          ${isW?`<div class="mplan-list-check">✓</div>`:''}
        </div>`;
      }).join('')}
    `).join('')
  }</div>`;
  }catch(e){return '<div style="padding:16px;color:var(--gray);font-size:var(--t-base)">Error al cargar lista</div>';}
}
function setInteresesView(mode){
  interesesViewMode=mode;
  document.getElementById('ibtn-grid')?.classList.toggle('on',mode==='grid');
  document.getElementById('ibtn-list')?.classList.toggle('on',mode==='list');
  try{const _v=JSON.parse(localStorage.getItem(`${FESTIVAL_STORAGE_KEY}viewmodes`)||'{}');_v.intereses=mode;localStorage.setItem(`${FESTIVAL_STORAGE_KEY}viewmodes`,JSON.stringify(_v));}catch(e){}
  // Re-renderizar sección activa
  const grids=document.querySelectorAll('.ag-film-grid');
  const items=document.querySelectorAll('.ag-film-item:not(.watched-item)');
  grids.forEach(g=>g.classList.toggle('list-mode',mode==='list'));
  items.forEach(el=>el.classList.toggle('list-mode',mode==='list'));
}

function _getProgramaPhase(){
  // Retorna qué tabs deben ser visibles y cuál es el default
  if(festivalEnded()) return {tabs:['explorar'],default:'explorar'};
  const now=simNow();
  // Fecha de inicio dinámica — primer día del festival activo
  const firstDayKey=DAY_KEYS[0];
  const firstDayDate=FESTIVAL_DATES[firstDayKey];
  const FEST_START=firstDayDate?new Date(firstDayDate+'T09:00:00'):new Date('2099-01-01');
  if(now<FEST_START) return {tabs:['explorar'],default:'explorar'};
  const todayStr=simTodayStr();
  const lastDayKey=DAY_KEYS[DAY_KEYS.length-1];
  const isLastDay=todayStr===FESTIVAL_DATES[lastDayKey];
  const tabs=isLastDay?['explorar','hoy']:['explorar','hoy','manana'];
  return{tabs,default:'hoy'};
}

function initProgramaModeBar(){
  const phase=_getProgramaPhase();
  // Mostrar/ocultar tabs según fase
  ['explorar','hoy','manana'].forEach(m=>{
    const el=document.getElementById('pmode-'+m);
    if(!el) return;
    el.style.display=phase.tabs.includes(m)?'':'none';
  });
  // Si el sub-modo actual no está disponible, resetear al default
  if(!phase.tabs.includes(programaSubMode)){
    programaSubMode=phase.default;
  }
  // Actualizar tab activo
  ['explorar','hoy','manana'].forEach(m=>{
    const el=document.getElementById('pmode-'+m);
    if(el) el.classList.toggle('on',m===programaSubMode);
  });
  // Mostrar/ocultar chips
  const chipsEl=document.getElementById('programa-chips');
  if(chipsEl){
    chipsEl.classList.toggle('hidden',programaSubMode!=='explorar');
    if(programaSubMode==='explorar') renderProgramaChips();
  }
  // Mostrar/ocultar nav-row (días) y filter-row según modo
  const navRow=document.getElementById('nav-row');
  const filterRow=document.getElementById('filter-row');
  // nav-row: hidden in Explorar (accessed via Place filter), visible in Hoy/Mañana
  if(programaSubMode==='explorar'){
    if(navRow) navRow.classList.add('hidden');
    if(filterRow) filterRow.classList.add('hidden');
  } else {
    if(navRow) navRow.classList.remove('hidden');
    if(filterRow) filterRow.classList.add('hidden');
    document.querySelectorAll('.dtab').forEach(t=>t.classList.toggle('on',t.dataset.day===activeDay));
  }
  // tag dismissible
  _updateProgramaActiveFilter();
}

function setProgramaMode(mode){
  programaSubMode=mode;
  // Reset filtros al cambiar modo
  activeSec='all';activeVenue='all';selectedIdx=null;
  programaChip='all';_programaChipMatchFn=null;
  clearCartaSearch();
  // Set active day for hoy/mañana modes
  const _pts=simTodayStr();
  const _pti=DAY_KEYS.findIndex(d=>FESTIVAL_DATES[d]===_pts);
  if(mode==='hoy'){
    activeDay=_pti>=0?DAY_KEYS[_pti]:DAY_KEYS[0];
  } else if(mode==='manana'){
    activeDay=_pti>=0&&_pti<DAY_KEYS.length-1?DAY_KEYS[_pti+1]:DAY_KEYS[DAY_KEYS.length-1];
  }
  _updateProgramaActiveFilter();
  initProgramaModeBar();
  _renderProgramaContent();
}

function setProgramaView(view){
  programaViewMode=view;
  document.getElementById('pmode-grid').classList.toggle('on',view==='grid');
  document.getElementById('pmode-list').classList.toggle('on',view==='list');
  _renderProgramaContent();
}

function setProgramaChip(chipId){
  programaChip=chipId;
  // Actualizar chips visuales
  document.querySelectorAll('.pchip').forEach(el=>{
    el.classList.toggle('on',el.dataset.chip===chipId);
  });
  // Guardar la función de match — soporta múltiples secciones
  const chip=(_currentChips.length?_currentChips:PROGRAMA_CHIPS).find(c=>c.id===chipId);
  if(chip&&chip.match){
    _programaChipMatchFn=chip.match;
    activeSec='_chip_'; // señal de que el filtro lo maneja el chip
  } else {
    _programaChipMatchFn=null;
    activeSec='all';
  }
  _updateProgramaActiveFilter();
  _renderProgramaContent();
}

function clearProgramaChip(){
  _programaChipMatchFn=null;
  activeVenue='all';
  // Resetear label del venue dropdown
  const vl=document.getElementById('vdr-label');if(vl) vl.textContent='Lugar';
  const vb=document.getElementById('vdr-btn');if(vb) vb.classList.remove('active');
  setProgramaChip('all');
}

function toggleProgramaFilter(){
  const btn=document.getElementById('pmode-filter-btn');
  const filterRow=document.getElementById('filter-row');
  if(!filterRow) return;
  const visible=filterRow.classList.contains('hidden');
  filterRow.classList.toggle('hidden',!visible);
  if(btn) btn.classList.toggle('active',visible);
  if(visible){renderVbar();renderSbar();}
}

function _updateProgramaActiveFilter(){
  const af=document.getElementById('programa-active-filter');
  const tagText=document.getElementById('paf-tag-text');
  const countEl=document.getElementById('paf-count');
  if(!af) return;
  const chip=(_currentChips.length?_currentChips:PROGRAMA_CHIPS).find(c=>c.id===programaChip);
  const hasChip=programaChip!=='all'&&chip;
  const hasVenue=activeVenue!=='all';

  if(hasChip||hasVenue){
    // Construir el label del tag — chip + venue si ambos activos
    let parts=[];
    if(hasChip) parts.push(chip.label);
    if(hasVenue) parts.push('📍 '+activeVenue);
    tagText.textContent=parts.join(' · ');
    // Contar películas que cumplen ambos filtros
    const titleMap={};
    FILMS.forEach(f=>{if(!titleMap[f.title])titleMap[f.title]={film:f,screenings:[]};titleMap[f.title].screenings.push(f);});
    const count=Object.values(titleMap).filter(({film:f,screenings})=>{
      const secOk=hasChip?(chip.match&&chip.match(f.section||'')):true;
      const venueOk=hasVenue?screenings.some(s=>vcfg(s.venue).short===activeVenue):true;
      return secOk&&venueOk;
    }).length;
    countEl.textContent=count+' película'+(count!==1?'s':'');
    af.classList.add('visible');
  } else {
    af.classList.remove('visible');
  }
}

function renderProgramaChips(){
  const el=document.getElementById('programa-chips');
  if(!el) return;
  // Derivar chips dinámicamente desde secciones del festival activo
  const titleSet={};
  FILMS.forEach(f=>{if(!titleSet[f.title])titleSet[f.title]=f;});
  const allFilms=Object.values(titleSet);
  const secMap={};
  allFilms.forEach(f=>{const s=f.section||'';if(s) secMap[s]=(secMap[s]||0)+1;});
  const secChips=Object.entries(secMap)
    .sort((a,b)=>b[1]-a[1])
    .map(([sec,cnt])=>({
      id:'sec_'+sec.replace(/[^a-zA-Z0-9]/g,'_').slice(0,30),
      label:sec, match:s=>s===sec, count:cnt
    }));
  const chips=[{id:'all',label:'Todo',match:null,count:allFilms.length},...secChips];
  _currentChips=chips;
  el.innerHTML=chips.map(chip=>{
    const isOn=chip.id==='all'?programaChip==='all':
      (_programaChipMatchFn&&chip.match&&_programaChipMatchFn.toString()===chip.match.toString());
    const label=chip.id==='all'?chip.label:`${chip.label}<span style="font-size:var(--t-xs);opacity:.6;margin-left:3px">${chip.count}</span>`;
    return`<div class="pchip${isOn?' on':''}" data-chip="${chip.id}"
         onclick="setProgramaChip('${chip.id}')">${label}</div>`;
  }).join('');
}

// ── Badges de metadata: Q&A e Inscripción previa ────────────────────────
function _metaBadges(f){
  let b='';
  if(f.has_qa) b+=`<span class="meta-badge">${UI.badge.qa}</span>`;
  if(f.requires_registration) b+=`<span class="meta-badge">${UI.badge.inscription}</span>`;
  return b;
}
function _metaBanners(f){
  let b='';
  if(f.has_qa) b+=`<div class="meta-banner"><div class="meta-banner-dot"></div><div><div class="meta-banner-label">Q&A · EQUIPO PRESENTE</div><div class="meta-banner-text">La función puede extenderse <span>· +30 min estimados</span></div></div></div>`;
  if(f.requires_registration) b+=`<div class="meta-banner"><div class="meta-banner-dot"></div><div><div class="meta-banner-label">INSCRIPCIÓN PREVIA</div><div class="meta-banner-text">Requiere registro antes del evento</div></div></div>`;
  return b;
}

// ── Stack poster para programas combinados ───────────────────────────────
function _programaStack(f){
  if(!f.is_programa||!f.film_list||f.film_list.length<2) return null;
  const p1=getPosterSrc(f.film_list[0].title||f.film_list[0],false)||"";
  const p2=getPosterSrc(f.film_list[1].title||f.film_list[1],false)||"";
  const imgB=p2?`<img class="ps-back" src="${p2}" loading="lazy" onerror="this.remove()" alt="">`:"<div class='ps-back'></div>";
  const imgF=p1?`<img class="ps-front" src="${p1}" loading="lazy" onerror="this.remove()" alt="">`:"<div class='ps-front'></div>";
  return`<div class="plist-poster-stack">${imgB}${imgF}</div>`;
}

// ── Notices: banner de funciones canceladas/reprogramadas ────────────────
let _dismissedNotices=new Set();
function getActiveNotices(){
  const festId=window._currentFestivalId||'aff2026';
  const today=new Date(); today.setHours(0,0,0,0);
  return NOTICES.filter(n=>{
    if(n.festival!==festId) return false;
    if(_dismissedNotices.has(n.title)) return false;
    // Banner desaparece al día siguiente de la función cancelada
    if(n.date){
      const funcDate=new Date(n.date+'T00:00:00');
      funcDate.setDate(funcDate.getDate()+1); // día siguiente
      if(today>=funcDate) return false;
    }
    return true;
  });
}
function renderNoticesBanner(){
  const el=document.getElementById('notices-banner');
  if(!el) return;
  const active=getActiveNotices();
  if(!active.length){el.innerHTML='';return;}
  el.innerHTML=active.map(n=>{
    const label=n.type==='cancelled'?UI.badge.cancelled:UI.badge.rescheduled;
    const detailCancelled=`<div class="notice-banner-detail">Pendiente nueva fecha.</div>`;
    const detailVenue=n.newVenue?`<div class="notice-banner-detail">${n.newVenue}</div>`:'';
    const detailWhen=n.newDay&&n.newTime?`<div class="notice-banner-detail">${n.newDay} · ${n.newTime}</div>`:'';
    const detail=n.type==='cancelled'?detailCancelled:(detailWhen+detailVenue);
    const safeTitle=n.title.length>32?n.title.slice(0,30)+'…':n.title;
    return`<div class="notice-banner">
      <div class="notice-banner-dot"></div>
      <div class="notice-banner-body">
        <div class="notice-banner-label">AVISO DEL FESTIVAL</div>
        <div class="notice-banner-text"><b>${safeTitle}</b> <span class="notice-banner-status">${label.toLowerCase()}</span></div>
        ${detail}
      </div>
      <button class="notice-banner-close" onclick="_dismissNotice('${n.title.replace(/'/g,"\\'")}')">${ICONS.x}</button>
    </div>`;
  }).join('');
}
function _dismissNotice(title){
  _dismissedNotices.add(title);
  renderNoticesBanner();
}
function renderProgramaList(){
  try{
  // Vista lista cronológica para Hoy/Mañana
  const el=document.getElementById('programa-list');
  if(!el) return;
  el.scrollTop=0;// always reset before re-render
  let films=FILMS.filter(f=>f.day===activeDay);
  if(activeVenue!=='all') films=films.filter(f=>vcfg(f.venue).short===activeVenue);
  if(activeSec!=='all') films=films.filter(f=>f.section===activeSec);
  // Sort: by time (primary), then Movies→Cortos→Events within same time
  films.sort((a,b)=>{
    const td=toMin(a.time)-toMin(b.time);
    if(td!==0) return td;
    const cat=f=>f.type==='event'?2:f.is_cortos?1:0;
    return cat(a)-cat(b);
  });
  if(!films.length){
    el.innerHTML=`<div style="text-align:center;padding:var(--sp-6) var(--sp-5);color:var(--gray);font-size:var(--t-base)">Sin actividades para este filtro</div>`;
    return;
  }
  // Agrupar por hora
  const byTime={};
  films.forEach(f=>{if(!byTime[f.time])byTime[f.time]=[];byTime[f.time].push(f);});
  el.innerHTML=Object.entries(byTime).map(([time,fs])=>`
    <div class="plist-time-hdr">${time}</div>
    ${fs.map(f=>{
      const inWL=watchlist.has(f.title);
      const passed=screeningPassed(f);
      const isNow=isNowShowing(f);
      const safeT=f.title.replace(/'/g,"\'");
      const{displayTitle:dt}=parseProgramTitle(f.title);
      const notice=NOTICES.find(n=>n.title===f.title&&n.festival===(window._currentFestivalId||'aff2026'));
      const _effVenue=notice&&notice.newVenue?notice.newVenue:f.venue;
      const vc=vcfg(_effVenue);
      const src=getFilmPoster(f)||'';
      const nowBadge=isNow?`<span style="font-size:var(--t-xs);font-weight:var(--w-display);color:var(--green);background:var(--green-10);border:1px solid var(--green-30);border-radius:var(--r);padding:2px 6px;margin-left:4px">AHORA</span>`:'';
      const noticeBadge=notice?`<span class="notice-badge">${notice.type==='cancelled'?UI.badge.cancelled:UI.badge.rescheduled}</span>`:'';
      const noticeNote=notice&&notice.type==='cancelled'?`<div class="notice-note notice-note--warn">Pendiente nueva fecha</div>`:
        notice&&notice.type==='rescheduled'&&notice.newTime?`<div class="notice-note notice-note--ok">${notice.newDay||''} · ${notice.newTime}${notice.newVenue?' · '+notice.newVenue:''}</div>`:'';
      const cancelStyle=notice&&notice.type==='cancelled'?'opacity:.5':'';
      const pastStyle=passed&&!isNow&&!festivalEnded()?'opacity:.45':'';
      const itemStyle=[pastStyle,cancelStyle].filter(Boolean).join(';');
      const _stk=_programaStack(f);
      return`<div class="plist-item" style="${itemStyle}" onclick="openPelSheet('${safeT}')">
        ${_stk||(src?`<img class="plist-poster" src="${src}" loading="lazy" onerror="this.style.opacity=0" alt="">`:`<div class="plist-poster"></div>`)}
        <div class="plist-info">
          <div class="plist-title">${noticeBadge}${_metaBadges(f)}${dt}${nowBadge}</div>
          <div class="plist-meta" style="${notice&&notice.type==='cancelled'?'text-decoration:line-through':''}">${vc.short}${sala(_effVenue)?' · '+sala(_effVenue):''} · ${f.duration||'~90 min'}</div>
          ${noticeNote||`<div class="plist-sec">${f.section||''}</div>`}
        </div>
        <div class="plist-heart${inWL?'':' empty'}" onclick="event.stopPropagation();_toggleWLFromList('${safeT}',this)">${inWL?ICONS.heartFill:ICONS.heart}</div>
      </div>`;
    }).join('')}
  `).join('');
  }catch(e){return '<div style="padding:16px;color:var(--gray);font-size:var(--t-base)">Error al cargar funciones</div>';}
}
function _renderProgramaContent(){
  const grid=document.getElementById('grid');
  const lista=document.getElementById('programa-list');
  const cntEl=document.getElementById('cnt');
  if(!grid||!lista) return;
  renderNoticesBanner();
  if(programaSubMode==='explorar'){
    if(programaViewMode==='grid'){
      lista.classList.remove('visible');
      grid.style.display='';
      renderPeliculaView();
    } else {
      grid.style.display='none';
      lista.classList.add('visible');
      _renderExploreLista();
    }
  } else {
    // Hoy / Mañana
    if(programaViewMode==='grid'){
      lista.classList.remove('visible');
      grid.style.display='';
      render(); // usa el modo horario existente
    } else {
      grid.style.display='none';
      lista.classList.add('visible');
      renderProgramaList();
      // Reset scroll: prevent page jumping to bottom after day-tab navigation
      lista.scrollTop=0;
      window.scrollTo({top:0,behavior:'instant'});
    }
  }
}

function _renderExploreLista(){
  try{
  // Vista lista del catálogo completo (Explorar en modo lista)
  const el=document.getElementById('programa-list');
  if(!el) return;
  const titleMap={};
  FILMS.forEach(f=>{if(!titleMap[f.title])titleMap[f.title]={film:f,screenings:[]};titleMap[f.title].screenings.push(f);});
  let entries=Object.values(titleMap);
  if(activeSec==='_chip_'&&_programaChipMatchFn){
    entries=entries.filter(e=>_programaChipMatchFn(e.film.section||''));
  } else if(activeSec!=='all'){
    entries=entries.filter(e=>e.film.section===activeSec);
  }
  if(activeVenue!=='all'){
    entries=entries.filter(e=>e.screenings.some(s=>vcfg(s.venue).short===activeVenue));
  }
  // Sort: Movies → Cortos → Industry (category), within each: day_order → time
  const _typeOrder=f=>f.type==='event'?2:f.is_cortos?1:0;
  entries.sort((a,b)=>{
    const to=_typeOrder(a.film)-_typeOrder(b.film);
    if(to!==0) return to;
    const do_diff=(a.film.day_order||0)-(b.film.day_order||0);
    if(do_diff!==0) return do_diff;
    return (a.film.time||'').localeCompare(b.film.time||'');
  });
  if(!entries.length){el.innerHTML=`<div style="text-align:center;padding:var(--sp-6) var(--sp-5);color:var(--gray);font-size:var(--t-base)">Sin películas para este filtro</div>`;return;}
  el.innerHTML=entries.map(({film:f,screenings})=>{
    const inWL=watchlist.has(f.title);
    const isEvent=f.type==='event';
    const safeT=f.title.replace(/\'/g,"\\'");
    const{displayTitle:dt}=parseProgramTitle(f.title);
    const src=isEvent?'':getFilmPoster(f)||'';
    const allPast=screenings.every(s=>screeningPassed(s));
    const days=[...new Set(screenings.map(s=>DAY_SHORT[s.day]||s.day))].join(' · ');
    if(isEvent) return`<div class="plist-item plist-event" style="${allPast?'opacity:.35':''}" onclick="openPelSheet('${safeT}')">
      <img class="plist-poster" src="${makeEventPoster(dt,f.duration)}" alt="${dt}">
      <div class="plist-info">
        <div class="plist-title plist-title--past">${dt}</div>
        <div class="plist-meta">${f.duration||''} · ${days}</div>
        <div class="plist-sec">${f.section||''}</div>
      </div>
    </div>`;
    const _stk2=_programaStack(f);
    return`<div class="plist-item${allPast?' past-card':''}" onclick="openPelSheet('${safeT}')">
      ${_stk2||(src?`<img class="plist-poster" src="${src}" loading="lazy" onerror="this.style.opacity=0" alt="${dt}" style="${allPast&&!festivalEnded()?'opacity:.45':''}">` :`<div class="plist-poster"></div>`)}
      <div class="plist-info">
        ${(()=>{const n=NOTICES.find(nx=>nx.title===f.title&&nx.festival===(window._currentFestivalId||'aff2026'));const nb=n?`<span class="notice-badge">${n.type==='cancelled'?UI.badge.cancelled:UI.badge.rescheduled}</span>`:'';const nn=n&&n.type==='cancelled'?`<div style="font-size:var(--t-xs);color:var(--amber);margin-top:2px;font-weight:var(--w-semi)">Pendiente nueva fecha</div>`:n&&n.type==='rescheduled'&&(n.newTime||n.newVenue)?`<div style="font-size:var(--t-xs);color:var(--green);margin-top:2px;font-weight:var(--w-semi)">${n.newVenue&&!n.newTime?n.newVenue:`${n.newDay||''} · ${n.newTime}${n.newVenue?' · '+n.newVenue:''}`}</div>`:'';return`<div class="plist-title" style="${allPast?'opacity:.5':''}">${nb}${dt}</div><div class="plist-meta" style="${n&&n.type==='cancelled'?'text-decoration:line-through':''}">${f.duration||'~90 min'} · ${days}</div>${nn||`<div class="plist-sec">${f.section||''}</div>`}`;})()}
      </div>
      <div class="plist-heart${inWL?'':' empty'}" onclick="event.stopPropagation();_toggleWLFromList('${safeT}',this)">${inWL?ICONS.heartFill:ICONS.heart}</div>
    </div>`;
  }).join('');
  }catch(e){return;}
}
function _toggleWLFromList(title,btn){
  // Wrapper para el ♥ en la lista de Programa — usa el toggleWL existente
  const wasIn=watchlist.has(title);
  toggleWL(title,{stopPropagation:()=>{}});
  // Actualizar el botón visualmente después del toggle
  setTimeout(()=>{
    const isIn=watchlist.has(title);
    if(btn){
      btn.innerHTML=isIn?ICONS.heartFill:ICONS.heart;
      btn.classList.toggle('empty',!isIn);
    }
  },50);
}

function setCartelaMode(mode){
  // Mantenida por compatibilidad — el nuevo sistema usa programaSubMode
  cartelaMode=mode;
  expandedPelicula='';
}




function renderPeliculaView(){
  const grid=document.getElementById('grid');
  const cntEl=document.getElementById('cnt');
  if(!grid) return;

  // Agrupar por título único
  const titleMap={};
  FILMS.forEach(f=>{
    if(!titleMap[f.title]) titleMap[f.title]={film:f,screenings:[]};
    titleMap[f.title].screenings.push(f);
  });

  // Aplicar filtro de sección (chip o dropdown)
  let entries=Object.values(titleMap);
  if(activeSec==='_chip_'&&_programaChipMatchFn){
    entries=entries.filter(e=>_programaChipMatchFn(e.film.section||''));
  } else if(activeSec!=='all'){
    entries=entries.filter(e=>e.film.section===activeSec);
  }
  // Aplicar filtro de venue — incluir film si alguna función es en ese lugar
  if(activeVenue!=='all'){
    entries=entries.filter(e=>e.screenings.some(s=>vcfg(s.venue).short===activeVenue));
  }

  // Sort: Movies → Cortos → Industry (category order)
  // Within each category: chronological (day_order → time)
  const _typeOrd2=f=>f.type==='event'?2:f.is_cortos?1:0;
  entries.sort((a,b)=>{
    const to=_typeOrd2(a.film)-_typeOrd2(b.film);
    if(to!==0) return to;
    // Within same category: chronological
    const do_diff=(a.film.day_order||0)-(b.film.day_order||0);
    if(do_diff!==0) return do_diff;
    return (a.film.time||'').localeCompare(b.film.time||'');
  });

  cntEl.innerHTML=(activeSec!=='all'||programaChip!=='all')?`<b>${entries.length}</b> película${entries.length!==1?'s':''}`:'';

  const DAY_ABB=['MAR','MIÉ','JUE','VIE','SÁB','DOM'];

  grid.innerHTML=`<div class="poster-grid">${entries.map(({film:f,screenings})=>{
    const inWL=watchlist.has(f.title);
    const inW=watched.has(f.title);
    const allPast=screenings.every(s=>screeningPassed(s));
    const posterSrc=getFilmPoster(f);
    const safeT=f.title.replace(/'/g,"\'");
    const{displayTitle}=parseProgramTitle(f.title);
    const progBadge='';//REMOVED: no count badge
    const _ended=festivalEnded();
    const posterImg=posterSrc
      ?`<img src="${posterSrc}" loading="lazy" style="width:100%;height:100%;object-fit:cover${allPast&&!_ended?';opacity:.45':''};display:block" onerror="this.remove()" alt="">`
      :``;
    return`<div class="poster-card${inWL&&!inW?' in-wl':''}${inW&&!_ended?' in-watched':''}" data-title="${f.title.replace(/"/g,'&quot;')}" onclick="openPelSheet('${safeT}')">
      ${posterImg}
      ${progBadge}
      ${inWL?`<div class="poster-wl-dot">${ICONS.heartFill}</div>`:''}
    </div>`;
  }).join('')}</div>`;
  requestAnimationFrame(()=>window.dispatchEvent(new Event('scroll')));// trigger lazy load
}

function render(){
  if(activeView==='agenda') return;
  // Si estamos en Cartelera con el nuevo sistema, _renderProgramaContent lo maneja
  if(activeView==='day'&&document.getElementById('programa-mode-bar')?.style.display!=='none'){
    if(programaSubMode==='explorar'){renderSbar();renderPeliculaView();return;}
    // Hoy/Mañana — forzar cartelaMode horario para que render() use la vista por día
    cartelaMode='horario';
  }
  if(cartelaMode==='pelicula'){renderSbar();renderPeliculaView();return;}
  renderVbar();renderSbar();
  let films=FILMS.filter(f=>f.day===activeDay);
  if(activeVenue!=='all') films=films.filter(f=>vcfg(f.venue).short===activeVenue);
  if(activeSec!=='all') films=films.filter(f=>f.section===activeSec);
  const cntEl=document.getElementById('cnt');
  if(activeVenue!=='all'||activeSec!=='all'){
    cntEl.innerHTML=`<b>${films.length}</b> actividad${films.length!==1?'es':''}`;
  } else {
    cntEl.innerHTML='';
  }
  const grid=document.getElementById('grid');
  if(!films.length){grid.innerHTML=emptyState(ICONS.search,UI.empty.noResults,'Ajusta los filtros de sección o sede.');return;}
  // ── Vista horario: poster-grid 3 col + overlay de hora ──
  grid.innerHTML='<div class="poster-grid">'+films.map((f,i)=>{
    const FICCI_POSTER='https://ficcifestival.com/sites/default/files/2026-02/logo-ficci65_2.png';
    const isProg=f.is_cortos;
    const isEvent=f.type==='event';
    const passed=screeningPassed(f);
    const inWL=watchlist.has(f.title),inW=watched.has(f.title);
    const isNow=isNowShowing(f);
    const safeT=f.title.replace(/'/g,"\'");
    const posterSrc=getFilmPoster(f);
    const posterImg=posterSrc
      ?`<img src="${posterSrc}" loading="lazy" style="width:100%;height:100%;object-fit:cover;display:block" onerror="this.style.opacity=0" alt="">`
      :``;
    const progBadge='';//REMOVED
    const nowBadge=isNow?`<div class="poster-now">AHORA</div>`:'';
    const _notice=NOTICES.find(n=>n.title===f.title&&n.festival===(_activeFestId||'aff2026'));
    const pastBadge=_notice?`<div class="poster-notice-badge">${_notice.type==='cancelled'?UI.badge.cancelled:UI.badge.rescheduled}</div>`:'';

    const _fe=festivalEnded();
return`<div class="poster-card${inWL&&!inW?' in-wl':''}${inW&&!_fe?' in-watched':''}${passed&&!_fe?' past-card':''}" onclick="openPelSheet('${safeT}')">
      ${posterImg}
      <div class="poster-time">${f.time}</div>
      ${nowBadge||pastBadge||progBadge}
      ${inWL?`<div class="poster-wl-dot">${ICONS.heartFill}</div>`:''}
    </div>`;
  }).join('')+'</div>';


  // ── Cartelera: micro-CTA only (step bar removed from PROGRAMA context)
  // Flow progress bar belongs in INTERESES/PLANEAR/MI PLAN tabs, not in PROGRAMA.
  if(activeView==='day'){
    const _cStepper=document.getElementById('cartelera-stepper');
    const _cCta=document.getElementById('cartelera-cta');
    if(_cStepper) _cStepper.style.display='none';// always hidden in day/hora view
    if(_cCta)_cCta.style.display=(!festivalEnded()&&watchlist.size===0)?'':'none';
  }
}
