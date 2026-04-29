// ══ Sheets — bottom sheets, pel-sheet, rating sheet ══
// SOURCE: index.html L6568-7113

// Render inicial — construye el DOM de las 5 estrellas una sola vez
function renderRatingStars(current){
  const el=document.getElementById('rating-stars');
  if(!el) return;
  let html='';
  for(let i=1;i<=5;i++){
    const fill=current>=i?'full':current>=i-0.5?'half':'none';
    html+=`<div style="width:44px;height:44px;display:flex;align-items:center;justify-content:center">${starSVG(fill)}</div>`;
  }
  el.innerHTML=html;
}

// Update rápido durante drag — solo actualiza los atributos SVG sin recrear DOM
function updateRatingStars(current){
  const el=document.getElementById('rating-stars');
  if(!el) return;
  const wraps=el.querySelectorAll('div');
  if(wraps.length!==5){renderRatingStars(current);return;}
  for(let i=0;i<5;i++){
    const star=i+1;
    const fill=current>=star?'full':current>=star-0.5?'half':'none';
    const poly=wraps[i].querySelector('polygon');
    const defs=wraps[i].querySelector('defs');
    if(!poly) continue;
    if(fill==='none'){
      poly.setAttribute('fill','none');
      poly.setAttribute('stroke','rgba(255,255,255,.2)');
      if(defs) defs.remove();
    } else if(fill==='full'){
      if(defs) defs.remove();
      poly.setAttribute('fill','var(--amber)');
      poly.setAttribute('stroke','var(--amber)');
    } else {
      // half — recrear gradient solo cuando es necesario
      const svg=wraps[i].querySelector('svg');
      if(svg&&!defs){
        const id='rg'+i;
        svg.insertAdjacentHTML('afterbegin',
          `<defs><linearGradient id="${id}"><stop offset="50%" stop-color="var(--amber)"/><stop offset="50%" stop-color="transparent"/></linearGradient></defs>`);
        poly.setAttribute('fill',`url(#${id})`);
        poly.setAttribute('stroke','var(--amber)');
      }
    }
  }
}

let _currentRating=0;
function setRating(val){
  _currentRating=val;
  updateRatingStars(val); // rápido, sin recrear DOM
  const btn=document.getElementById('rating-action-btn');
  if(btn){
    if(val>0){btn.textContent='Guardar';btn.className='rating-action-btn save';}
    else{btn.textContent='Sin calificar';btn.className='rating-action-btn skip';}
  }
}

function _ratingFromX(el,clientX){
  const rect=el.getBoundingClientRect();
  const x=Math.max(0,Math.min(clientX-rect.left,rect.width));
  return Math.min(5,Math.max(0.5,Math.round((x/rect.width)*10)/2));
}

// Pointer Events API — unificado mouse+touch, con setPointerCapture
// para que el drag funcione correctamente en iOS dentro de transforms
function _initRatingInteraction(){
  const range=document.getElementById('rating-range');
  if(!range||range._ratingInit) return;
  range._ratingInit=true;
  range.addEventListener('input',()=>{
    setRating(parseInt(range.value)/2);
  });
}

function openRatingSheet(title){
  _ratingTitle=title;
  _pushSheetState();
  const _rs=document.getElementById('rating-sheet');
  if(_rs) _rs.scrollTop=0;
  _currentRating=filmRatings[title]||0;
  const{displayTitle}=parseProgramTitle(title);
  document.getElementById('rating-film-title').textContent=displayTitle;
  renderRatingStars(_currentRating);
  const _btn=document.getElementById('rating-action-btn');
  if(_btn){
    if(_currentRating>0){_btn.textContent='Guardar';_btn.className='rating-action-btn save';}
    else{_btn.textContent='Sin calificar';_btn.className='rating-action-btn skip';}
  }
  document.getElementById('rating-overlay').classList.add('open');
  document.getElementById('rating-sheet').classList.add('open');
  requestAnimationFrame(()=>{
    const range=document.getElementById('rating-range');
    if(range){range.value=Math.round(_currentRating*2);range._ratingInit=false;}
    _initRatingInteraction();
  });
}

function closeRatingSheet(){
  if(_currentRating>0){
    saveRating(_ratingTitle,_currentRating);
    const _stars=starsDisplay(_currentRating,11);
    showToast(`<span style="display:inline-flex;align-items:center;gap:4px">${_stars}</span>`,'info');
  } else {
    if(filmRatings[_ratingTitle]){
      saveRating(_ratingTitle,0);
      showToast('Calificación eliminada','info');
    }
  }
  document.getElementById('rating-overlay').classList.remove('open');
  document.getElementById('rating-sheet').classList.remove('open');
  // Re-render para reflejar el nuevo rating
  const listEl=document.getElementById('ag-film-list');
  if(listEl) listEl.innerHTML=renderFilmListHTML();
  // Actualizar Mi Plan si está activo
  if(activeMNav==='mnav-miplan') renderAgenda();
  // Actualizar Intereses
  if(activeMNav==='mnav-seleccion') updateAgTab();
  // Actualizar el rating visible en el sheet si está abierto
  const _pelSheet=document.getElementById('pel-sheet');
  if(_pelSheet&&_pelSheet.classList.contains('open')){
    // Actualizar estrellas en el sheet actual (si el título coincide)
    const _rStars=_pelSheet.querySelector('.pel-sheet-rating-stars');
    if(_rStars&&_currentRating>0) _rStars.textContent=starsText(_currentRating);
  }
}

function starsText(r){
  if(!r) return '';
  const full=Math.floor(r);
  const half=(r%1)>=0.5;
  return '★'.repeat(full)+(half?'½':'');
}
function starsDisplay(rating,size){
  // size en px para display compacto
  if(!rating) return '';
  let html='';
  for(let i=1;i<=5;i++){
    const fill=rating>=i?'full':rating>=i-0.5?'half':'none';
    const s=size||10;
    const id='sd'+i+Math.random().toString(36).slice(2,5);
    const grad=fill==='half'?`<defs><linearGradient id="${id}"><stop offset="50%" stop-color="var(--amber)"/><stop offset="50%" stop-color="transparent"/></linearGradient></defs>`:'';
    const fv=fill==='none'?'none':fill==='full'?'var(--amber)':`url(#${id})`;
    const st=fill==='none'?'rgba(255,255,255,.2)':'var(--amber)';
    html+=`<svg width="${s}" height="${s}" viewBox="0 0 24 24" style="display:block;flex-shrink:0">${grad}<polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26" fill="${fv}" stroke="${st}" stroke-width="1.5" stroke-linejoin="round"/></svg>`;
  }
  return html;
}


function togglePelPrio(title){
  togglePriority(title);
  const btn=document.getElementById('pel-prio-btn')||document.getElementById('corto-prio-btn');
  if(!btn) return;
  const inPrio=prioritized.has(title);
  btn.innerHTML=(inPrio?ICONS.starFill:ICONS.star)+' '+(inPrio?'Priorizada':'Priorizar');
  btn.className='pel-sheet-action-btn'+(inPrio?' act-prio':'');
  // Priorizar auto-añade a watchlist — sincronizar el botón de Intereses
  const inWL=watchlist.has(title);
  const pelWlBtn=document.getElementById('pel-wl-btn');
  if(pelWlBtn){
    pelWlBtn.innerHTML=(inWL?ICONS.heartFill:ICONS.heart)+' '+(inWL?'En Intereses':'Intereses');
    pelWlBtn.className='pel-sheet-action-btn'+(inWL?' act-on btn-primary':'');
  }
  const cortoWlBtn=document.getElementById('corto-wl-btn');
  if(cortoWlBtn){
    cortoWlBtn.innerHTML=(inWL?ICONS.heartFill:ICONS.heart)+' '+(inWL?'En Intereses':'Intereses');
    cortoWlBtn.className='pel-sheet-action-btn'+(inWL?' act-on':'');
  }
}

/* ── BOTTOM SHEET: apertura, cierre, acciones ───────────────────────── */
function togglePelWL(title,e){
  const wasInWL=watchlist.has(title);
  toggleWL(title,e);
  const btn=document.getElementById('pel-wl-btn');
  if(!btn) return;
  const inWL=watchlist.has(title);
  btn.innerHTML=(inWL?ICONS.heartFill:ICONS.heart)+' '+(inWL?'En Intereses':'Intereses');
  btn.className='pel-sheet-action-btn'+(inWL?' act-on btn-primary':'');
  // Abrir WLAdd solo al AÑADIR — no al quitar (modal async deja wasInWL=true)
  if(!wasInWL&&inWL&&(activeMNav==='mnav-cartelera'||activeMNav==='mnav-seleccion')){
    closePelSheet();
    showActionToast(`${ICONS.heartFill} En Intereses`,`${ICONS.star} Priorizar`,()=>togglePriority(title));
  }
}
function filterByVenue(venue){
  closePelSheet();
  activeVenue=venue;activeSec='all';selectedIdx=null;
  programaSubMode='explorar';programaViewMode='grid';
  programaChip='all';_programaChipMatchFn=null;
  switchMainNav('mnav-cartelera');
  showDayView();
  // Actualizar label del dropdown de Lugar
  const lbl=document.getElementById('vdr-label');
  const btn=document.getElementById('vdr-btn');
  if(lbl) lbl.textContent=venue.length>14?venue.slice(0,12)+'…':venue;
  if(btn) btn.classList.add('active');
}

function filterBySection(section){
  // Navegar a Programa · Explorar con esa sección activa
  closePelSheet();
  activeSec=section;activeVenue='all';selectedIdx=null;
  programaSubMode='explorar';programaViewMode='grid';
  // Buscar chip que corresponda a esta sección y activar filtro
  const matchedChip=PROGRAMA_CHIPS.find(ch=>ch.match&&ch.match(section));
  programaChip=matchedChip?matchedChip.id:'all';
  _programaChipMatchFn=matchedChip?.match||null;
  if(matchedChip) activeSec='_chip_';
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

// ═══════════════════════════════════════════════════════════════
// ═══════════════════════════════════════════════════════════════
// CARD TEMPLATE CANÓNICO — 4 tipos, misma shell, contenido variable
// ───────────────────────────────────────────────────────────────
// DISEÑO VISUAL (aplica a todos los tipos):
//   Labels:    lowercase · letter-spacing .12em · color gray · .pel-sheet-section-lbl
//   Dividers:  1px · var(--bdr) · margin 20px · .pel-sheet-divider
//   Metadata:  director · género · año en una línea · .pel-sheet-metaline
//   CTAs:      primario=ámbar (.btn-primary) · secundario=borde · terciario=sin borde (.btn-tertiary)
//
// TIPO 1: PELÍCULA (!f.is_cortos, f.type !== 'event')
//   Header: poster + flags + título + duración + director·género·año + sección
//   Body:   label función/funciones + filas día·hora·venue·única-función
//           label sinopsis + texto + Letterboxd (link discreto)
//   CTAs:   Intereses (ámbar si activo) · Priorizar · Vista (terciario)
//
// TIPO 2: PROGRAMA DE CORTOS (f.is_cortos === true)
//   Header: igual TIPO 1 + "N cortos"
//   Body:   igual TIPO 1 + lista desplegable de cortos individuales
//   CTAs:   Intereses · Priorizar · Vista
//   → Cada corto abre openCortoSheet() → TIPO 3
//
// TIPO 3: CORTO INDIVIDUAL (openCortoSheet)
//   Header: poster + flags + título + duración + director·género + sección
//   Body:   label sinopsis + texto + Letterboxd
//   CTAs:   Intereses · Priorizar · Calificar
//   REGLA:  Intereses/Priorizar empaquetan al PROGRAMA PADRE (_findParentProgram)
//
// TIPO 4: EVENTO / TALLER / CONFERENCIA (f.type === 'event')
//   Header: poster + título + duración + sección (sin flags)
//   Body:   label horario + filas día·hora·venue
//           label descripción + texto (sin Letterboxd)
//   CTAs:   Intereses · Priorizar · Asistí (terciario)
//
// REGLA GLOBAL: campo nuevo → definir aquí primero, nunca ad-hoc en el template.
// ═══════════════════════════════════════════════════════════════
function openPelSheet(title){
  const entry=Object.values((()=>{
    const m={};
    FILMS.forEach(f=>{if(!m[f.title])m[f.title]={film:f,screenings:[]};m[f.title].screenings.push(f);});
    return m;
  })()).find(e=>e.film.title===title);
  if(!entry) return;
  const{film:f,screenings}=entry;
  const inWL=watchlist.has(f.title),inW=watched.has(f.title),inPrio=prioritized.has(f.title);
  const posterSrc=getFilmPoster(f);
  const posterHtml=posterSrc
    ?`<img class="pel-sheet-poster" src="${posterSrc}" loading="lazy" onerror="this.outerHTML='<div class=pel-sheet-poster-ph>🎬</div>'" alt="">`
    :`<div class="pel-sheet-poster-ph">🎬</div>`;
  const{displayTitle}=parseProgramTitle(f.title);
  const secLabel=f.section?f.section.replace(/^[^ ]+ /,''):'';
  const totalFn=FILMS.filter(fi=>fi.title===f.title).length;
  const unica=totalFn===1;
  const DAY_ABB=['MAR','MIÉ','JUE','VIE','SÁB','DOM'];
  const future=screenings.filter(s=>!screeningPassed(s)).sort((a,b)=>a.day_order-b.day_order||toMin(a.time)-toMin(b.time));
  const past=screenings.filter(s=>screeningPassed(s));
  const allScr=[...future,...past];
  const safeT=f.title.replace(/'/g,"\'");
  const _hasPlan=savedAgenda&&savedAgenda.schedule.length>0;
  const _inPlan=savedAgenda&&savedAgenda.schedule.some(s=>s._title===f.title);
  const rows=allScr.map(s=>{
    const dayAbb=DAY_SHORT[s.day]||DAY_ABB[DAY_KEYS.indexOf(s.day)]||s.day.slice(0,3).toUpperCase();
    const vc=vcfg(s.venue),sl=sala(s.venue);
    const isPast=screeningPassed(s)&&!festivalEnded();
    const safeDay=s.day.replace(/'/g,"\'");
    const _showAdd=_hasPlan&&!_inPlan&&!isPast;
    return`<div class="pel-sheet-screening"${isPast?' style="opacity:.4"':''}>
      <span class="pelicula-day">${dayAbb}</span>
      <span class="pelicula-time">${s.time}</span>
      <span class="pelicula-venue" data-venue="${vc.short.replace(/"/g,'&quot;')}" onclick="filterByVenue(this.dataset.venue)">${ICONS.pin} ${vc.short}${sl?' · '+sl:''}  <span style="opacity:.4;font-size:var(--t-xs)">›</span></span>
      ${_showAdd?`<button class="pel-sheet-add-plan" onclick="event.stopPropagation();if(addSuggestion('${safeT}','${safeDay}','${s.time}')==='added')closePelSheet()" title="Añadir a mi plan">${ICONS.plus}</button>`:''}
    </div>`;
  }).join('');
  // Lista de cortos si es programa
  let cortosHtml='';
  if(f.is_cortos&&f.film_list?.length){
    const cortoItems=f.film_list.map((item,n)=>{
      const thumb=getCortoItemPoster(item);
      const thumbHtml=thumb?`<img src="${thumb}" loading="lazy" class="lb-poster" onerror="this.remove()" alt="">`:`<div class="lb-poster-ph">🎬</div>`;
      const r=filmRatings[item.title]||0;
      const safeCorto=item.title.replace(/'/g,"\'");
      const safeCountry=(item.country||'').replace(/'/g,"\'");
      const safeDur=(item.duration||'').replace(/'/g,"\'");
      // Usar banderas reales del corto individual, no las del programa
      const _cortoFlags=countryToFlags(item.country||'');
      const safeFlags=_cortoFlags.replace(/'/g,"\'");
      const safeSec=(f.section||'').replace(/'/g,"\'");
      const ratingEl=r
        ?`<span class="corto-rating-stars">${starsText(r)}</span>`
        :`<button class="corto-rate-btn" onclick="event.stopPropagation();closePelSheet();setTimeout(()=>openRatingSheet('${safeCorto}'),100)">★</button>`;
      const _sd=(item.director||'').replace(/['"]/g,'');
      const _sg=(item.genre||'').replace(/['"]/g,'');
      const _ss=(item.synopsis||'').replace(/['"]/g,'');
      return`<div class="pel-sheet-corto-item" onclick="openCortoSheet('${safeCorto}','${safeCountry}','${safeDur}','${safeSec}','${safeFlags}','${_sd}','${_sg}','${_ss.slice(0,150)}')">
        ${thumbHtml}
        <div style="flex:1;min-width:0">
          <div style="font-size:var(--t-caption);font-weight:var(--w-semi);color:var(--white);line-height:1.3;margin-bottom:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${item.title}</div>
          <div style="font-size:var(--t-sm);color:var(--gray2)">${item.country||''} · ${item.duration}</div>
        </div>
        ${ratingEl}
      </div>`;
    }).join('');
    cortosHtml=`<div class="pel-sheet-divider"></div>
      <div class="pel-sheet-section-lbl">Programa · ${f.film_list.length} cortos</div>
      <div class="pel-sheet-cortos-wrap">${cortoItems}</div>`;
  }
  const wlLabel=inWL?`${ICONS.heartFill} En Intereses`:`${ICONS.heart} Intereses`;
  const _planEntry=_inPlan?savedAgenda.schedule.find(s=>s._title===f.title):null;
  const _ps=document.getElementById('pel-sheet');
  if(_ps) _ps.scrollTop=0;
  _pushSheetState();
  // Metadata consolidada: director · género · año
  const _metaLine=[f.director?`${f.director}`:'',f.genre?(f.genre+(f.year?' · '+f.year:'')):'',(!f.director&&!f.genre&&f.year)?f.year:''].filter(Boolean).join(' · ');

  document.getElementById('pel-sheet-inner').innerHTML=`
    <div class="pel-sheet-header">
      ${posterHtml}
      <div class="pel-sheet-meta">
        <div class="pel-sheet-title">${displayTitle}</div>
        <div class="pel-sheet-flags">${f.flags||'🌐'}</div>
        <div class="pel-sheet-dur">${ICONS.clock} ${f.duration}</div>
        ${_metaLine?`<div class="pel-sheet-metaline">${_metaLine}</div>`:''}
        ${f.section?`<div class="pel-sheet-sec" data-sec="${f.section.replace(/"/g,'&quot;')}" onclick="filterBySection(this.dataset.sec)">${secLabel} <span class="pel-sheet-sec-arrow">›</span></div>`:''}
        ${f.is_cortos&&f.film_list?.length?`<div class="pel-sheet-cortos-count">${f.film_list.length} corto${f.film_list.length!==1?'s':''}</div>`:''}
      </div>
    </div>
    <div class="pel-sheet-divider"></div>
    <div class="pel-sheet-section-lbl${allScr.length===1&&f.type!=='event'?' pel-sheet-section-lbl--urgent':''}">${f.type==='event'?'horario':allScr.length===1?'única función':'funciones'}</div>
    ${(()=>{const _n=NOTICES.find(n=>n.title===f.title&&n.festival===(_activeFestId||'aff2026'));if(!_n)return'';const _msg=_n.type==='cancelled'?'Función cancelada · Pendiente nueva fecha':_n.newVenue&&!_n.newTime?`Nueva sede: ${_n.newVenue}`:`Reprogramada → ${_n.newDay||''} ${_n.newTime||''}${_n.newVenue?' · '+_n.newVenue:''}`;return`<div style="display:flex;align-items:center;gap:var(--sp-2);padding:var(--sp-2) var(--sp-3);background:var(--amber-08);border-radius:var(--r-sm);margin-bottom:var(--sp-2)"><span class="notice-badge">${_n.type==='cancelled'?UI.badge.cancelled:UI.badge.rescheduled}</span><span style="font-size:var(--t-sm);color:var(--amber-60)">${_msg}</span></div>`;})()}
    ${_metaBanners(f)}
    <div class="pel-sheet-screenings">${rows}</div>
    <div class="pel-sheet-divider"></div>
    <div class="pel-sheet-section-lbl">${f.type==='event'?'descripción':'sinopsis'}</div>
    <div class="pel-sheet-synopsis">${f.synopsis||'Sinopsis disponible próximamente.'}</div>
    ${cortosHtml}
    ${(!f.is_cortos&&f.type!=='event')?`<a class="c-lb pel-sheet-lb" href="${lbUrl(f.title)}" target="_blank" rel="noopener">${LB_SVG}<span class="c-lb-text pel-sheet-lb-text">Letterboxd</span></a>`:''}
    <div class="pel-sheet-divider"></div>
    ${inW?`<div class="pel-sheet-ctas-watched">
        <button onclick="toggleWatched('${safeT}',event);closePelSheet()" class="pel-sheet-action-btn act-on">${ICONS.check} Ya vista</button>
        ${!f.is_cortos?`<button onclick="closePelSheet();setTimeout(()=>openRatingSheet('${safeT}'),100)" class="pel-sheet-action-btn">${ICONS.star} ${filmRatings['${safeT}']?'Cambiar':'Calificar'}</button>`:``}
      </div>`
    :`<div class="pel-sheet-ctas">
        <button id="pel-wl-btn" class="pel-sheet-action-btn${inWL?' act-on btn-primary':''}" onclick="togglePelWL('${safeT}',event)" style="display:inline-flex;align-items:center;justify-content:center;gap:var(--sp-1)">${inWL?ICONS.heartFill:ICONS.heart} ${inWL?'En Intereses':'Intereses'}</button>
        <button id="pel-prio-btn" class="pel-sheet-action-btn${inPrio?' act-prio':''}" onclick="togglePelPrio('${safeT}')" style="display:inline-flex;align-items:center;justify-content:center;gap:var(--sp-1)">${inPrio?ICONS.starFill:ICONS.star} ${inPrio?'Priorizada':'Priorizar'}</button>
        <button id="pel-vista-btn" class="pel-sheet-action-btn btn-tertiary" onclick="toggleWatched('${safeT}',event)" style="display:inline-flex;align-items:center;justify-content:center;gap:var(--sp-1)">${ICONS.check} ${f.type==='event'?'Asistí':'Vista'}</button>
      </div>`}
    ${_inPlan&&activeView==='agenda'?`<button onclick="closePelSheet();removeFromAgenda('${safeT}')" class="pel-sheet-remove-plan">${ICONS.x} Quitar del plan</button>`:''}
  `;
  document.getElementById('pel-overlay').classList.add('open');
  document.getElementById('pel-sheet').classList.add('open');
}
function closePelSheet(){
  // Si hay contenido padre guardado, volvemos al programa en lugar de cerrar
  if(_cortoParentHtml){
    const inner=document.getElementById('pel-sheet-inner');
    if(inner){
      inner.innerHTML=_cortoParentHtml;
      _cortoParentHtml=null;
      const ps=document.getElementById('pel-sheet');
      if(ps) ps.scrollTop=0;
      return;
    }
  }
  _cortoParentHtml=null;
  document.getElementById('pel-overlay').classList.remove('open');
  document.getElementById('pel-sheet').classList.remove('open');
}
// History API — cerrar cualquier sheet/overlay con botón back del browser
function _closeTopSheet(){
  // Cerrar en orden de prioridad (el más reciente primero)
  if(document.getElementById('pv-rating-sheet')?.classList.contains('open')){closePVRating();return true;}
  if(document.getElementById('conflict-sheet')?.classList.contains('open')){closeConflictSheet();return true;}
  if(document.getElementById('prio-limit-sheet')?.classList.contains('open')){closePrioLimit();return true;}
  if(document.getElementById('rating-overlay')?.classList.contains('open')){closeRatingSheet();return true;}
  if(document.getElementById('pel-sheet')?.classList.contains('open')){closePelSheet();return true;}
  // Action modal dinámico
  const modal=document.querySelector('.conflict-modal');
  if(modal){modal.remove();return true;}
  return false;
}
window.addEventListener('popstate',function(e){
  if(!_closeTopSheet()){
    // Ningún sheet abierto — dejar que el browser navegue normalmente
  }
});
function _pushSheetState(){
  try{history.pushState({sheet:true},'','');}catch(e){}
}
// ESC cierra el sheet activo (útil en desktop/tablet)
document.addEventListener('keydown',function(e){
  if(e.key==='Escape') _closeTopSheet();
});
(function(){
  let _startY=0,_dragging=false;
  document.addEventListener('DOMContentLoaded',()=>{});
  // Swipe-down en el topbar para cerrar el sheet
  function _initSheetSwipe(){
    const topbar=document.querySelector('.pel-sheet-topbar');
    if(!topbar||topbar._swipeInit) return;
    topbar._swipeInit=true;
    topbar.addEventListener('touchstart',e=>{
      _startY=e.touches[0].clientY;_dragging=true;
    },{passive:true});
    topbar.addEventListener('touchmove',e=>{
      if(!_dragging) return;
      const sheet=document.getElementById('pel-sheet');
      const dy=e.touches[0].clientY-_startY;
      if(dy>0) sheet.style.transform=`translateY(${dy}px)`;
    },{passive:true});
    topbar.addEventListener('touchend',e=>{
      if(!_dragging) return;
      _dragging=false;
      const sheet=document.getElementById('pel-sheet');
      const dy=e.changedTouches[0].clientY-_startY;
      sheet.style.transform='';
      if(dy>80) closePelSheet();
    },{passive:true});
  }
  // Inicializar cuando se abre el sheet
  const _origOpen=window.openPelSheet;
  window.openPelSheet=function(title){
    if(_origOpen) _origOpen(title);
    setTimeout(_initSheetSwipe,50);
  };
})();

// ─────────────────────────────────────────────────────────────────
// PROGRAMA — EXPLORAR / HOY / MAÑANA
// ─────────────────────────────────────────────────────────────────

// ─────────────────────────────────────────────────────────────
// MAPPER PAÍS → BANDERA para cortos individuales
// ─────────────────────────────────────────────────────────────
const _COUNTRY_FLAGS={
  'Alemania':'🇩🇪','Argentina':'🇦🇷','Austria':'🇦🇹','Bolivia':'🇧🇴',
  'Brasil':'🇧🇷','Bélgica':'🇧🇪','Canadá':'🇨🇦','Chile':'🇨🇱',
  'Colombia':'🇨🇴','Cuba':'🇨🇺','EEUU':'🇺🇸','Estados Unidos':'🇺🇸',
  'Ecuador':'🇪🇨','Eslovaquia':'🇸🇰','España':'🇪🇸','Estonia':'🇪🇪',
  'Francia':'🇫🇷','Grecia':'🇬🇷','Inglaterra':'🇬🇧','Irán':'🇮🇷',
  'Italia':'🇮🇹','México':'🇲🇽','Nicaragua':'🇳🇮','Palestina':'🇵🇸',
  'Perú':'🇵🇪','Portugal':'🇵🇹','Reino Unido':'🇬🇧','Rep. Dominicana':'🇩🇴',
  'Suiza':'🇨🇭','Taiwán':'🇹🇼','Turquía':'🇹🇷','UK':'🇬🇧',
  'Venezuela':'🇻🇪','Vietnam':'🇻🇳'
};
function countryToFlags(countryStr){
  if(!countryStr) return '🌍';
  const parts=countryStr.split('/').map(s=>s.trim());
  const flags=parts.map(p=>_COUNTRY_FLAGS[p]||'').filter(Boolean);
  return flags.length?flags.join(''):'🌍';
}
// ─────────────────────────────────────────────────────────────
// SHEET INDIVIDUAL DE CORTOMETRAJE
// Trata cada corto como película — poster, info, rating, Letterboxd
// ─────────────────────────────────────────────────────────────
let _cortoParentHtml=null; // guarda el HTML del programa padre

// Encuentra el programa padre de un corto individual
function _findParentProgram(cortoTitle){
  return FILMS.find(f=>f.is_cortos&&f.film_list?.some(c=>c.title===cortoTitle))||null;
}

// openCortoSheet — card unificada con openPelSheet
// Intereses/Priorizar empaquetan al programa padre completo
function openCortoSheet(title, country, duration, section, flags, director, genre, synopsis){
  const inner=document.getElementById('pel-sheet-inner');
  if(!inner) return;
  const pelSheet=document.getElementById('pel-sheet');
  if(pelSheet&&pelSheet.classList.contains('open')){
    _cortoParentHtml=inner.innerHTML;
  } else {
    _cortoParentHtml=null;
  }
  let richItem=null;
  for(const f of FILMS){
    if(f.film_list){const found=f.film_list.find(c=>c.title===title);if(found){richItem=found;break;}}
  }
  const dir=director||(richItem&&richItem.director)||'';
  const gnr=genre||(richItem&&richItem.genre)||'';
  const syn=synopsis||(richItem&&richItem.synopsis)||'';
  const ctry=country||(richItem&&richItem.country)||'';
  const dur=duration||(richItem&&richItem.duration)||'';
  const flgs=flags||countryToFlags(ctry)||'🌐';
  const posterUrl=getPosterSrc(title,true)||null;
  const posterHtml=posterUrl
    ?`<img class="pel-sheet-poster" src="${posterUrl}" loading="lazy" onerror="this.outerHTML='<div class=pel-sheet-poster-ph>🎬</div>'" alt="">`
    :`<div class="pel-sheet-poster-ph">🎬</div>`;
  const ps=document.getElementById('pel-sheet');
  if(ps) ps.scrollTop=0;
  _pushSheetState();
  const safeTitle=title.replace(/'/g,"\\'");
  // Intereses y Priorizar actúan sobre el programa padre
  const parent=_findParentProgram(title);
  const parentTitle=parent?parent.title:null;
  const safeParent=parentTitle?parentTitle.replace(/'/g,"\\'"):safeTitle;
  const inWL=watchlist.has(parentTitle||title);
  const inPrio=prioritized.has(parentTitle||title);
  const secLabel=section?section.replace(/^[^ ]+ /,'').trim():'';
  inner.innerHTML=`
    <div class="pel-sheet-header">
      ${posterHtml}
      <div class="pel-sheet-meta">
        <div class="pel-sheet-title">${title}</div>
        <div class="pel-sheet-flags">${flgs}</div>
        ${dur?`<div class="pel-sheet-dur">${ICONS.clock} ${dur}</div>`:''}
        ${(dir||gnr)?`<div class="pel-sheet-metaline">${[dir,gnr].filter(Boolean).join(' · ')}</div>`:''}
        ${secLabel?`<div class="pel-sheet-sec">${secLabel}</div>`:''}
      </div>
    </div>
    <div class="pel-sheet-divider"></div>
    ${syn?`<div class="pel-sheet-section-lbl">Sinopsis</div><div class="pel-sheet-synopsis">${syn}</div><div class="pel-sheet-divider" style="margin-top:16px"></div>`:''}
    <a class="c-lb" href="${lbUrl(title)}" target="_blank" rel="noopener" style="display:inline-flex;margin-bottom:2px">${LB_SVG}<span class="c-lb-text">Letterboxd</span></a>
    <div class="pel-sheet-divider" style="margin-top:16px"></div>
    ${parentTitle?`<div style="font-size:var(--t-xs);color:var(--gray);margin-bottom:8px">Al agregar un corto se incluye el programa completo</div>`:''}
    <div style="display:flex;gap:var(--sp-1);margin-top:4px">
      <button id="corto-wl-btn" class="pel-sheet-action-btn${inWL?' act-on':''}" onclick="toggleWL('${safeParent}',event)" style="display:inline-flex;align-items:center;justify-content:center;gap:var(--sp-1)">${inWL?ICONS.heartFill:ICONS.heart} ${inWL?'En Intereses':'Intereses'}</button>
      <button id="corto-prio-btn" class="pel-sheet-action-btn${inPrio?' act-prio':''}" onclick="togglePelPrio('${safeParent}')" style="display:inline-flex;align-items:center;justify-content:center;gap:var(--sp-1)">${inPrio?ICONS.starFill:ICONS.star} ${inPrio?'Priorizada':'Priorizar'}</button>
      <button class="pel-sheet-action-btn${filmRatings[title]?' act-on':''}" onclick="closePelSheet();setTimeout(()=>openRatingSheet('${safeTitle}'),100)" style="display:inline-flex;align-items:center;justify-content:center;gap:var(--sp-1)">${ICONS.star} ${filmRatings[title]?'Cambiar':'Calificar'}</button>
    </div>
  `;
  document.getElementById('pel-overlay').classList.add('open');
  document.getElementById('pel-sheet').classList.add('open');
}

function setMiPlanView(mode){
  miPlanViewMode=mode;
  try{const _v=JSON.parse(localStorage.getItem(`${FESTIVAL_STORAGE_KEY}viewmodes`)||'{}');_v.miPlan=mode;localStorage.setItem(`${FESTIVAL_STORAGE_KEY}viewmodes`,JSON.stringify(_v));}catch(e){}
  renderAgenda();
}

