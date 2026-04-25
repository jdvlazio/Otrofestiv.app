// ══ Mi Lista — renderFilmListHTML, renderPrioStrip ══
// SOURCE: index.html L4198-4358

/* ── RENDER — MI LISTA ──────────────────────────────────────────────── */
function renderFilmListHTML(){
  const prioList=[...prioritized].filter(t=>!watched.has(t));
  const nonPrioList=[...watchlist].filter(t=>!watched.has(t)&&!prioritized.has(t));
  const allPending=[...new Set([...prioList,...nonPrioList])];
  const watchedList=[...watched];

  const mkItem=(t,listMode=false)=>{
    const f=FILMS.find(fi=>fi.title===t);
    const hasFuture=FILMS.some(fi=>fi.title===t&&!screeningPassed(fi));
    const FICCI_POSTER_AG='https://ficcifestival.com/sites/default/files/2026-02/logo-ficci65_2.png';
    const posterSrc=f?(getFilmPoster(f)):null;
    const posterHtml=posterSrc?`<img class="ag-fi-poster" src="${posterSrc}" loading="eager" style="object-fit:cover" onerror="this.outerHTML='<div class=ag-fi-poster-ph>🎬</div>'" alt="">`:`<div class="ag-fi-poster-ph">🎬</div>`;
    const isPrio=prioritized.has(t);
    const safeT=t.replace(/"/g,'&quot;');
    const{displayTitle,progSuffix}=parseProgramTitle(t);
    const safeTQ=t.replace(/'/g,"\'");
    return`<div class="ag-film-item${listMode?' list-mode':''}" onclick="openPelSheet('${safeTQ}')">
      ${posterHtml}
      <div class="ag-fi-overlay"></div>
      <div class="ag-fi-actions">
        <button class="ag-fi-btn prio-fi-btn${isPrio?' prio-on':''}" data-pt="${safeT}" onclick="togglePriority(this.dataset.pt);event.stopPropagation()" style="display:inline-flex;align-items:center;gap:var(--sp-1)">${isPrio?ICONS.starFill+' Priorizada':ICONS.star+' Priorizar'}</button>
      </div>
      <div class="ag-fi-bottom">
        <div class="ag-fi-flags">${f?f.flags||'🌐':'🌐'}</div>
        <div class="ag-fi-title">${displayTitle}</div>
        ${(()=>{
          if(!f) return '';
          const filmDays=FILMS.filter(fi=>fi.title===t&&!screeningPassed(fi));
          const dayChips=[...new Set(filmDays.map(fi=>DAY_SHORT[fi.day]).filter(Boolean))].join(' · ');
          const secShort=(f.section||'').replace(/^[^\s]+ /,'');
          return dayChips?`<div class="ag-fi-days">${dayChips}${secShort?' · '+secShort:''}</div>`:'';
        })()}
        ${progSuffix?`<div style="font-size:var(--t-xs);color:var(--orange);font-weight:var(--w-bold);margin-top:1px;line-height:1">${progSuffix}</div>`:''}
      </div>
    </div>`;
  };

  let html='';
  if(!allPending.length&&!watchedList.length){
    return emptyStateHero(ICONS.heart,'Tu lista está vacía','Tu plan para el festival, sin complicaciones.','Explorar Programa',"switchMainNav('mnav-cartelera');showDayView()");
  }
  // Switch grid/lista para Intereses
  const _iSwitch=`<div class="intereses-view-switch" style="flex-shrink:0">
    <button class="intereses-view-btn${interesesViewMode==='grid'?' on':''}" id="ibtn-grid" onclick="setInteresesView('grid')">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
    </button>
    <button class="intereses-view-btn${interesesViewMode==='list'?' on':''}" id="ibtn-list" onclick="setInteresesView('list')">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="4" y1="6" x2="20" y2="6"/><line x1="4" y1="12" x2="20" y2="12"/><line x1="4" y1="18" x2="20" y2="18"/></svg>
    </button>
  </div>`;
  const _listMode=interesesViewMode==='list';
  if(prioList.length){
    html+=`<div class="intereses-mode-bar"><div class="sec-hdr">${ICONS.star} Prioridades <span class="intereses-cnt">${prioList.length}/${PRIO_LIMIT}</span></div>${_iSwitch}</div>`;
    html+=`<div class="ag-film-grid${_listMode?' list-mode':''}">${prioList.map(t=>mkItem(t,_listMode)).join('')}</div>`;
  }
  if(nonPrioList.length){
    if(prioList.length) html+=`<div class="ag-list-sep"></div>`;
    html+=`<div class="intereses-mode-bar"><div class="sec-hdr">${ICONS.heart} Intereses <span class="intereses-cnt">${nonPrioList.length}</span></div>${prioList.length?'':_iSwitch}</div>`;
    html+=`<div class="ag-film-grid${_listMode?' list-mode':''}">${nonPrioList.map(t=>mkItem(t,_listMode)).join('')}</div>`;
  }
  if(!allPending.length&&!watchedList.length){
    return`<div style="margin-top:8px;padding:var(--sp-5) var(--sp-4);border:1px solid var(--bdr-l);border-radius:var(--r);text-align:center">
      <div class="sec-hdr" style="justify-content:center;margin-bottom:var(--sp-3)">${ICONS.heart} Intereses</div>
      <div style="font-size:var(--t-base);color:var(--gray);line-height:1.6;text-align:center;max-width:240px;margin-left:auto;margin-right:auto;text-wrap:balance">
        Aún no tienes películas guardadas.<br>Usa el buscador para añadir títulos.
      </div>
    </div>`;
  }
  if(watchedList.length){
    if(allPending.length) html+=`<div class="ag-list-sep"></div>`;
    html+=`<div class="ya-vistas-bar"><div class="ya-vistas-lbl">${ICONS.check} Ya vistas</div></div>`;
    const _sortedW=[...watchedList].sort((a,b)=>(filmRatings[b]||0)-(filmRatings[a]||0));
    html+=`<div class="ag-film-grid">${_sortedW.map(t=>{
      const f=FILMS.find(fi=>fi.title===t);
      const posterSrc=f?(getFilmPoster(f)):null;
      const _yvOp=festivalEnded()?'':';opacity:.70';
      const posterHtml=posterSrc?`<img class="ag-fi-poster" src="${posterSrc}" loading="eager" style="object-fit:cover${_yvOp}" onerror="this.outerHTML='<div class=ag-fi-poster-ph>🎬</div>'" alt="">`:`<div class="ag-fi-poster-ph" style="opacity:${festivalEnded()?1:.70}">🎬</div>`;
      const safeT=t.replace(/"/g,'&quot;');
      const safeTQ2=t.replace(/'/g,"\'");
      const{displayTitle}=parseProgramTitle(t);
      const _rating=f?(filmRatings[t]||0):0;
      const _stars=_rating?`<div class="ya-vistas-stars">${starsDisplay(_rating,9)}</div>`:'';
      return`<div class="ag-film-item${festivalEnded()?'':' watched-item'}" onclick="openPelSheet('${safeTQ2}')">
        ${posterHtml}
        <div class="ag-fi-overlay"></div>
        <div class="ag-fi-bottom">
          <div class="ag-fi-flags">${f?f.flags||'🌐':'🌐'}</div>
          <div class="ag-fi-title">${displayTitle}</div>
          ${_stars}
        </div>
      </div>`;
    }).join('')}</div>`;
  }
  return html||`<div style="margin-top:8px;padding:var(--sp-5) var(--sp-4);border:1px solid var(--bdr-l);border-radius:var(--r);text-align:center">
      <div class="sec-hdr" style="justify-content:center;margin-bottom:var(--sp-3)">${ICONS.heart} Intereses</div>
      <div style="font-size:var(--t-base);color:var(--gray);line-height:1.6;text-align:center;max-width:240px;margin-left:auto;margin-right:auto;text-wrap:balance">
        Aún no tienes películas guardadas.<br>Usa el buscador para añadir títulos.
      </div>
    </div>`;
}

// ── RENDER SAVED AGENDA ──
// ── Componente unificado: fila de función en agenda ──
// mode='saved'    → ✕ quita de agenda guardada
// mode='scenario' → ✕ quita de watchlist, muestra badge de alternativas
function removeFilmFromScenario(title,e){
  if(e) e.stopPropagation();
  const short=title.length>36?title.slice(0,34)+'…':title;
  showActionModal(
    `Quitar de Intereses`,
    `<b>${short}</b><br><br>Se quitará de Intereses y las opciones se recalcularán.`,
    'Quitar',
    ()=>{
      watchlist.delete(title);
      prioritized.delete(title);
      watched.delete(title);
      saveState('wl','prio','watched');
      updateAgTab();
      showToast('Quitada de Intereses','info');
      runCalc(); // recalcula directamente, no borra la vista
    }
  );
}
function mkAgendaRow(s, mode='saved'){
  const t=s._title||'';
  const{displayTitle,progSuffix}=parseProgramTitle(t);
  const f=FILMS.find(fi=>fi.title===t);
  const _p=getFilmPoster(f);
  const _safePT=t.replace(/'/g,"\\'");
  const _ph=_p?`<img class="lb-poster" src="${_p}" loading="lazy" style="cursor:pointer" onclick="event.stopPropagation();openPelSheet('${_safePT}')" onerror="this.style.opacity=0" alt="">`:'<div class="lb-poster-ph">🎬</div>';
  const vc2=vcfg(s.venue),sl=sala(s.venue);
  const safeT=(s._title||'').replace(/"/g,'&quot;');
  const isDone=watched.has(t);
  const alts=mode==='scenario'?FILMS.filter(fi=>fi.title===t&&!isScreeningBlocked(fi)&&!screeningPassed(fi)&&!(fi.day===s.day&&fi.time===s.time)):[];
  const altBadge=alts.length?`<span class="ag-alts">${alts.length} alt.</span>`:'';
  const filmKey=(s._title||'')+(s.day||'')+(s.time||'');
  const isExpanded=_expandedFilm===filmKey;
  const actionBtn=mode==='saved'
    ?`<button class="ag-fi-btn del" data-rmt="${safeT}" onclick="removeFromAgenda(this.dataset.rmt);event.stopPropagation()" style="display:inline-flex;align-items:center;gap:var(--sp-1)">${ICONS.x} Quitar</button>`
    :`<button class="ag-fi-btn del" data-rfs="${safeT}" onclick="removeFilmFromScenario(this.dataset.rfs,event)" style="display:inline-flex;align-items:center;gap:var(--sp-1)">${ICONS.x} Quitar</button>`;
  const switchBtn=mode==='saved'&&!isDone
    ?`<button class="film-switch${isExpanded?' open':''}" onclick="toggleFilmAlternatives('${filmKey}','${safeT}','${s.day||''}','${s.time||''}');event.stopPropagation()">Cambiar</button>`
    :'';
  const altsHtml=isExpanded&&mode==='saved'?renderFilmAlternatives(t,s.day,s.time):'';
  const _progBtn=(()=>{const _mf=f;if(!_mf||!_mf.is_cortos||!_mf.film_list||!_mf.film_list.length)return'';return`<button class="mplan-prog-toggle" onclick="toggleMplanProg(this,event)" style="display:inline-flex;align-items:center;gap:var(--sp-1)">${ICONS.chevronR} Programa</button>`;})();
  const _progList=(()=>{const _mf=f;if(!_mf||!_mf.is_cortos||!_mf.film_list||!_mf.film_list.length)return'';return`<div class="mplan-prog-list">${_mf.film_list.map((item,n)=>{const _mt=getCortoItemPoster(item);const _mth=_mt?`<img src="${_mt}" class="c-film-thumb" loading="lazy" onerror="this.outerHTML='<div class=c-film-thumb-ph>🎬</div>'" alt="">`:'<div class="c-film-thumb-ph">🎬</div>';const _sc=item.title.replace(/'/g,"\'");const _sco=item.country||'';const _scd=item.duration||'';const _scf=countryToFlags(item.country||'');const _scs=f?.section||'';return`<div class="mplan-prog-item" onclick="event.stopPropagation();openCortoSheet('${_sc}','${_sco}','${_scd}','${_scs}','${_scf}')">${_mth}<div class="mplan-prog-num">${n+1}</div><div class="mplan-prog-title">${item.title}</div><div class="mplan-prog-dur">${item.duration}</div></div>`;}).join('')}</div>`;})();
  return`<div class="saved-item${isDone?' done':''}">
    ${_ph}
    <div class="saved-time">${s.time}</div>
    <div class="saved-info">
      <div class="saved-title">${displayTitle}</div>${progSuffix?`<div style="font-size:var(--t-sm);color:var(--orange);font-weight:var(--w-bold);margin-top:1px;line-height:1">${progSuffix}</div>`:''}
      <div class="saved-venue">${ICONS.pin} ${vc2.short}${sl?' · '+sl:''}${s.duration?' · '+s.duration:''}${altBadge}</div>
      ${_progBtn}
    </div>
    <button class="saved-check${isDone?' done':''}" data-title="${safeT}" data-day="${s.day||''}" data-time="${s.time||''}" data-venue="${(s.venue||'').replace(/"/g,'&quot;')}" data-dur="${s.duration||''}" onclick="${isDone?'toggleWatched(this.dataset.title,event)':'markWatchedFromPlan(this.dataset.title,this.dataset.day,this.dataset.time,this.dataset.venue,this.dataset.dur,event)'}" style="display:inline-flex;align-items:center;gap:var(--sp-1)">${isDone?'No vista':ICONS.check+' Vista'}</button>
  </div>${_progList}${altsHtml?`<div class="film-alts">${altsHtml}</div>`:''}`;
}


