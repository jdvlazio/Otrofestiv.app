// ── src/view/programa.js — Fase 8 Step 6c (CABLEADO) ────────────────────────
//
// ESTADO: importado por src/main.js (Step 6c). Builders del programa view:
//   banner de avisos (notices) + chips de filtro. Scope STRICT (D-6C-2): solo
//   los builders foundational. El programa RENDER pesado (renderProgramaList,
//   renderPeliculaView, _renderProgramaContent) es controller-coupled → Wave 7.
//
// DEPS: state(state.js), i18n(t), config(NOTICES). festival/view-state via STATE
//   BRIDGE (bare-global): _activeFestId, _DEFAULT_FEST_ID, _dismissedNotices,
//   programaChip, _programaChipMatchFn (bridgeados en main.js TEST BRIDGE, D-6C-1).
//   Los handlers _dismissNotice/setProgramaChip (data-action) viven en main.js.

import { NOTICES, SECTION_ORDER_LIST, _DEFAULT_FEST_ID } from '../config.js';
import { ICONS, _secLabel, _secLabelFull, _sectionColor, escXML, makeEventPoster, makeProgramPoster, parseProgramTitle } from './components.js';
import { _dayChips, _getItemPoster, _metaBadges, _plistPosterHtml, _programaStack, dayLabel, durFmt, emptyState, getFilmPoster, isNowShowing, posterParts, sala, vcfg } from './helpers.js';
import { festivalEnded, toMin } from '../domain/time.js';
import { screeningPassed } from '../domain/film.js';
import { state } from '../state/state.js';
import { t } from '../i18n/i18n.js';

export function _computeProgramaChips(state){
  const {FILMS} = state.snapshot();
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
  return [{id:'all',label:t('chip_todo'),match:null,count:allFilms.length},...secChips];
}

export function renderProgramaChipsHTML(state){
  const chips=_computeProgramaChips(state);
  return chips.map(chip=>{
    const isOn=chip.id==='all'?programaChip==='all':
      (_programaChipMatchFn&&chip.match&&_programaChipMatchFn.toString()===chip.match.toString());
    const label=chip.id==='all'?chip.label:`${chip.label}<span class="ml-1 count-badge cb-neutral">${chip.count}</span>`;
    return`<div class="pchip${isOn?' on':''}" data-chip="${chip.id}"
         data-action="setProgramaChip" data-chip="${chip.id}">${label}</div>`;
  }).join('');
}

// _noticeKey — clave de descarte POR FESTIVAL (festId + título). Antes _dismissedNotices
// guardaba solo el título: descartar un aviso en un festival ocultaba avisos homónimos
// en otro (TT y FantasoFest la misma semana pueden compartir título de corto/programa).
// El add (_dismissNotice) y el check (getActiveNotices) usan ESTE helper → no divergen.
// Separador NUL (imposible en un festId [a-z0-9]) evita colisiones festId-titulo.
export function _noticeKey(title){ return (_activeFestId||_DEFAULT_FEST_ID)+String.fromCharCode(0)+title; }

export function getActiveNotices(){
  const festId=(_activeFestId||_DEFAULT_FEST_ID);
  const today=new Date(); today.setHours(0,0,0,0);
  return NOTICES.filter(n=>{
    if(n.festival!==festId) return false;
    if(_dismissedNotices.has(_noticeKey(n.title))) return false;
    // Banner desaparece al día siguiente de la función cancelada
    if(n.date){
      const funcDate=new Date(n.date+'T00:00:00');
      funcDate.setDate(funcDate.getDate()+1); // día siguiente
      if(today>=funcDate) return false;
    }
    return true;
  });
}

export function renderNoticesBannerHTML(state){
  const active=getActiveNotices();
  if(!active.length) return '';
  return active.map(n=>{
    const label=n.type==='cancelled'?t('notice_cancelada'):t('notice_reprogramada');
    const msgCancelled=`<span>${t('plan_fecha_pendiente')}</span>`;
    const msgRescheduled=n.newDay&&n.newTime?`${t('notice_nueva_funcion')} <span class="txt-white60">${n.newDay} · ${n.newTime}${n.newVenue?' · '+n.newVenue:''}</span>`:'';
    const msg=n.type==='cancelled'?msgCancelled:msgRescheduled;
    const safeTitle=n.title.length>32?n.title.slice(0,30)+'…':n.title;
    return`<div class="notice-banner">
      <div class="notice-banner-dot"></div>
      <div class="notice-banner-body">
        <div class="notice-banner-label">${t('notice_banner_label')}</div>
        <div class="notice-banner-text"><b class="txt-white60-semi">${safeTitle}</b> · <span>${label.toLowerCase()}</span>. ${msg}</div>
      </div>
      <button class="notice-banner-close" data-action="dismissNotice" data-title="${n.title.replace(/"/g,'&quot;')}">✕</button>
    </div>`;
  }).join('');
}

export function renderNoticesBanner(){
  const el=document.getElementById('notices-banner');
  if(!el) return;
  el.innerHTML=renderNoticesBannerHTML(state);
}


// ── Step 6g: render dispatchers programa + pelicula (8 fns). ──────────────────
export function renderProgramaList(){
  const el=document.getElementById('programa-list');
  if(!el) return;
  el.scrollTop=0;// always reset before re-render
  el.innerHTML=renderProgramaListHTML(state);
}

export function renderProgramaListHTML(state){
  try{
  const {FILMS, _activeFestId, watchlist} = state.snapshot();
  let films=FILMS.filter(f=>f.day===activeDay);
  if(activeVenue!=='all') films=films.filter(f=>vcfg(f.venue).short===activeVenue);
  if(activeSec!=='all') films=films.filter(f=>f.section===activeSec);
  films.sort((a,b)=>{
    const td=toMin(a.time)-toMin(b.time);
    if(td!==0) return td;
    const cat=f=>f.type==='event'?2:f.is_cortos?1:0;
    return cat(a)-cat(b);
  });
  if(!films.length){
    return emptyState(ICONS.search, t('filter_sin_actividades'), t('empty_filtros'));
  }
  const byTime={};
  films.forEach(f=>{if(!byTime[f.time])byTime[f.time]=[];byTime[f.time].push(f);});
  return Object.entries(byTime).map(([time,fs])=>`
    <div class="plist-time-hdr">${time}</div>
    ${fs.map(f=>{
      const inWL=watchlist.has(f.title);
      const passed=screeningPassed(f);
      const isNow=isNowShowing(f);

      const _isPrograma=f.is_programa&&f.film_list&&f.film_list.length>=2;
      const{displayTitle:_rawDt}=parseProgramTitle(f.title);
      const dt=_isPrograma
        ?(_rawDt+'<span class="film-count-badge">+1</span>')
        :_rawDt;
      const vc=vcfg(f.venue);
      const src=getFilmPoster(f)||'';
      const nowBadge=isNow?`<span class="film-check-badge">${t('misc_ahora')}</span>`:'';
      const notice=NOTICES.find(n=>n.title===f.title&&n.festival===((_activeFestId||_DEFAULT_FEST_ID)));
      const noticeBadge=notice?`<span class="notice-badge">${notice.type==='cancelled'?t('notice_cancelada'):t('notice_reprog_short')}</span>`:'';
      const noticeNote=notice&&notice.type==='cancelled'?`<div class="notice-detail-amber">${t('plan_fecha_pendiente')}</div>`:
        notice&&notice.type==='rescheduled'&&notice.newTime?`<div class="notice-detail-green">${notice.newDay||''} · ${notice.newTime}${notice.newVenue?' · '+notice.newVenue:''}</div>`:'';
      const cancelStyle=notice&&notice.type==='cancelled'?'opacity:.5':'';
      const pastStyle=passed&&!isNow&&!festivalEnded()?'opacity:.45':'';
      const itemStyle=[pastStyle,cancelStyle].filter(Boolean).join(';');
      const safeT=f.title.replace(/"/g,'&quot;').replace(/'/g,"&#39;");
      const _stk=_programaStack(f);
      return`<div class="plist-item js-open-pel" style="${itemStyle}" data-title="${escXML(f.title)}">
        ${_stk||_plistPosterHtml(f,src)}
        <div class="plist-info">
          <div class="plist-title">${noticeBadge}<span class="plist-title-txt">${dt}</span>${_metaBadges(f)}${nowBadge}</div>
          <div class="plist-meta" style="${notice&&notice.type==='cancelled'?'text-decoration:line-through':''}">${vc.short}${sala(f.venue)?' · '+sala(f.venue):''}${f.duration?' · '+durFmt(f.duration):''}</div>
          ${noticeNote||`<div class="plist-sec">${_secLabelFull(f.section||'')}</div>`}
        </div>
        <div class="plist-heart${inWL?'':' empty'}" data-title="${f.title.replace(/"/g,'&quot;')}" data-action="toggleWLFromList" data-stop="1">${inWL?ICONS.heartFill:ICONS.heart}</div>
      </div>`;
    }).join('')}
  `).join('');
  }catch(e){return `<div class="pad-muted">${t('error_funciones')}</div>`;}
}

export function _renderProgramaContent(resetScroll=false){
  // resetScroll: true solo en navegación (cambio de día/filtro/vista). En re-renders
  // por estado (toggle WL/prio, sync nube) queda false → preserva el scroll del usuario.
  const grid=document.getElementById('grid');
  const lista=document.getElementById('programa-list');
  const cntEl=document.getElementById('cnt');
  if(!grid||!lista) return;
  renderNoticesBanner();
  if(activeDay==='all'){
    requestAnimationFrame(()=>{
      const _pg2=grid.querySelector('.poster-grid');
      if(_pg2) _pg2.style.opacity='1';
      lista.style.opacity='1';
    });
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
    // Día específico seleccionado
    if(programaViewMode==='grid'){
      lista.classList.remove('visible');
      grid.style.display='';
      renderPeliculaView(); // muestra grilla de posters filtrada por activeDay
    } else {
      grid.style.display='none';
      lista.classList.add('visible');
      renderProgramaList();
      if(resetScroll){
        lista.scrollTop=0;
        window.scrollTo({top:0,behavior:'instant'});
      }
    }
  }
}

export function renderProgramaChips(){
  const el=document.getElementById('programa-chips');
  if(!el) return;
  _currentChips=_computeProgramaChips(state);
  el.innerHTML=renderProgramaChipsHTML(state);
}

export function _renderExploreLista(){
  const el=document.getElementById('programa-list');
  if(!el) return;
  el.innerHTML=_renderExploreListaHTML(state);
}

export function _renderExploreListaHTML(state){
  try{
  const {FILMS, _activeFestId, watchlist} = state.snapshot();
  const titleMap={};
  FILMS.forEach(f=>{
    if(!titleMap[f.title]){titleMap[f.title]={film:f,screenings:[]};}
    else{
      const cur=titleMap[f.title].film;
      const curMin=(cur.day_order||0)*1440+toMin(cur.time||'00:00');
      const newMin=(f.day_order||0)*1440+toMin(f.time||'00:00');
      if(newMin<curMin) titleMap[f.title].film=f;
    }
    titleMap[f.title].screenings.push(f);
  });
  let entries=Object.values(titleMap);
  if(activeSec!=='all'){
    entries=entries.filter(e=>e.film.section===activeSec);
  }
  if(activeVenue!=='all'){
    entries=entries.filter(e=>e.screenings.some(s=>{
      if(s.screenings&&s.screenings.length) return s.screenings.some(sc=>vcfg(sc.venue).short===activeVenue);
      return vcfg(s.venue).short===activeVenue;
    }));
  }
  const _typeOrder=f=>f.type==='event'?2:f.is_cortos?1:0;
  entries.sort((a,b)=>{
    const do_diff=(a.film.day_order||0)-(b.film.day_order||0);
    if(do_diff!==0) return do_diff;
    const td=(a.film.time||'').localeCompare(b.film.time||'');
    if(td!==0) return td;
    return _typeOrder(a.film)-_typeOrder(b.film);
  });
  if(!entries.length) return emptyState(ICONS.search, t('filter_sin_peliculas'), t('empty_filtros'));
  return entries.map(({film:f,screenings})=>{
    const inWL=watchlist.has(f.title);
    const isEvent=f.type==='event';
    const safeT=f.title.replace(/\'/g,"\\'").replace(/"/g,'&quot;');
    const{displayTitle:dt}=parseProgramTitle(f.title);
    const src=isEvent?'':getFilmPoster(f)||'';
    const allPast=screenings.every(s=>screeningPassed(s));
    const days=[...new Set(screenings.map(s=>dayLabel(s.day)||s.day))].join(' · ');
    const daysHtml=_dayChips(screenings);
    if(isEvent) return`<div class="plist-item plist-event js-open-pel" style="${allPast?'opacity:.35':''}" data-title="${escXML(f.title)}">
      <img class="plist-poster" src="${makeEventPoster(state,dt,f.duration,f.event_kind)}" alt="${dt}" loading="lazy">
      <div class="plist-info">
        <div class="plist-title">${dt}</div>
        <div class="plist-meta">${days?`${daysHtml} · `:''}${durFmt(f.duration)}</div>
        <div class="plist-sec">${_secLabelFull(f.section||'')}</div>
      </div>
      <div class="plist-heart${inWL?'':' empty'}" data-title="${f.title.replace(/"/g,'&quot;')}" data-action="toggleWLFromList" data-stop="1">${inWL?ICONS.heartFill:ICONS.heart}</div>
    </div>`;
    const _stk2=_programaStack(f);
    return`<div class="plist-item js-open-pel${allPast?' past-card':''}" data-title="${escXML(f.title)}">
      ${_stk2||_plistPosterHtml(f,src)}
      <div class="plist-info">
        ${(()=>{const n=NOTICES.find(nx=>nx.title===f.title&&nx.festival===((_activeFestId||_DEFAULT_FEST_ID)));const nb=n?`<span class="notice-badge">${n.type==='cancelled'?t('notice_cancelada'):t('notice_reprog_short')}</span>`:'';const nn=n&&n.type==='cancelled'?`<div class="notice-detail-amber">${t('plan_fecha_pendiente')}</div>`:n&&n.type==='rescheduled'&&n.newTime?`<div class="notice-detail-green">${n.newDay||''} · ${n.newTime}${n.newVenue?' · '+n.newVenue:''}</div>`:'';return`<div class="plist-title" style="${allPast?'opacity:.5':''}">${nb}${dt}</div><div class="plist-meta" style="${n&&n.type==='cancelled'?'text-decoration:line-through':''}${allPast?';opacity:.5':''}">${daysHtml?`${daysHtml} · `:''}${durFmt(f.duration)}${_metaBadges(f)?` · ${_metaBadges(f)}`:''}</div>${nn||`<div class="plist-sec">${_secLabelFull(f.section||'')}</div>`}`;})()}
      </div>
      <div class="plist-heart${inWL?'':' empty'}" data-title="${f.title.replace(/"/g,'&quot;')}" data-action="toggleWLFromList" data-stop="1">${inWL?ICONS.heartFill:ICONS.heart}</div>
    </div>`;
  }).join('');
  }catch(e){return '';}
}

export function renderPeliculaView(){
  const grid=document.getElementById('grid');
  const cntEl=document.getElementById('cnt');
  if(!grid) return;
  cntEl.innerHTML=''; // count visible en chip y en lugar-btn — cnt-line redundante
  const {html, hasEntries} = renderPeliculaViewHTML(state);
  grid.innerHTML=html;
  if(hasEntries) requestAnimationFrame(()=>window.dispatchEvent(new Event('scroll')));// trigger lazy load
}

export function renderPeliculaViewHTML(state){
  const {FILMS, watched, watchlist} = state.snapshot();
  const _dayFilms = activeDay==='all' ? FILMS : FILMS.filter(f=>f.day===activeDay);
  const titleMap={};
  _dayFilms.forEach(f=>{
    if(!titleMap[f.title]){titleMap[f.title]={film:f,screenings:[]};}
    else{
      const cur=titleMap[f.title].film;
      const curMin=(cur.day_order||0)*1440+toMin(cur.time||'00:00');
      const newMin=(f.day_order||0)*1440+toMin(f.time||'00:00');
      if(newMin<curMin) titleMap[f.title].film=f;
    }
    titleMap[f.title].screenings.push(f);
  });
  let entries=Object.values(titleMap);
  if(activeSec!=='all'){
    entries=entries.filter(e=>e.film.section===activeSec);
  }
  if(activeVenue!=='all'){
    entries=entries.filter(e=>e.screenings.some(s=>{
      if(s.screenings&&s.screenings.length) return s.screenings.some(sc=>vcfg(sc.venue).short===activeVenue);
      return vcfg(s.venue).short===activeVenue;
    }));
  }
  const _unknownSecMap=(()=>{const m={};let i=SECTION_ORDER_LIST.length;FILMS.forEach(f=>{if(f.section&&SECTION_ORDER_LIST.indexOf(f.section)<0&&!(f.section in m))m[f.section]=i++;});return m;})();
  const _secIdx=f=>{const i=SECTION_ORDER_LIST.indexOf(f.section??'');return i>=0?i:(_unknownSecMap[f.section??'']??99999);};
  entries.sort((a,b)=>{
    const so=_secIdx(a.film)-_secIdx(b.film);
    if(so!==0) return so;
    const da=DAY_KEYS.indexOf(a.film.day),db=DAY_KEYS.indexOf(b.film.day);
    if(da!==db) return da-db;
    const do_diff=(a.film.day_order||0)-(b.film.day_order||0);
    if(do_diff!==0) return do_diff;
    return toMin(a.film.time||'00:00')-toMin(b.film.time||'00:00');
  });
  if(!entries.length){
    return {html: emptyState(ICONS.search, t('filter_sin_peliculas'), t('empty_filtros')), hasEntries: false};
  }
  let _prevSec=null;
  const html=`<div class="poster-grid">${entries.map(({film:f,screenings})=>{
    const inWL=watchlist.has(f.title);
    const inW=watched.has(f.title);
    const allPast=screenings.every(s=>screeningPassed(s));
    const posterSrc=getFilmPoster(f);
    const safeT=f.title.replace(/"/g,'&quot;').replace(/'/g,"&#39;");
    const{displayTitle}=parseProgramTitle(f.title);
    const progBadge='';//REMOVED: no count badge
    const _ended=festivalEnded();
    const _isPrograma=f.is_programa&&f.film_list&&f.film_list.length>=2;
    let posterImg,_cardBg='',_edAccent='';
    if(_isPrograma){
      const _p1=_getItemPoster(f.film_list[0]);
      const _p2=_getItemPoster(f.film_list[1]);
      if(!_p1&&!_p2){
        // Ningún item del programa tiene poster real → poster editorial del
        // programa (evita el stack de divs vacíos / card en blanco)
        posterImg=`<img src="${getFilmPoster(f)||''}" loading="lazy" data-title="${f.title.replace(/"/g,'&quot;')}" style="width:100%;height:100%;object-fit:cover;display:block;opacity:0;transition:opacity 250ms ease" onload="this.style.opacity='1'" onerror="_posterErr(this)" alt="">`;
      } else {
        // Fallback unificado (como el sheet): item sin póster → generativo, no hueco.
        const _gen=()=>makeProgramPoster(state,f.title,f.duration||'',f.section||'');
        const _ib=`<img class="pcs-back" src="${_p2||_gen()}" loading="lazy" onerror="this.remove()" alt="">`;
        const _if=`<img class="pcs-front" src="${_p1||_gen()}" loading="lazy" onerror="this.remove()" alt="">`;
        posterImg=`<div class="poster-card-stack">${_ib}${_if}</div>`;
      }
    } else {
      _cardBg='';
      _cardBg='';
      const _opacity=allPast&&!_ended?';opacity:.45':'';
      const _edSecLbl=_secLabel(f.section||'');
      const _edBodyTitle=(()=>{const pfx=_edSecLbl+' - ';if(displayTitle.startsWith(pfx))return displayTitle.slice(pfx.length);const sPfx='Storytellers - ';if(displayTitle.startsWith(sPfx))return displayTitle.slice(sPfx.length);return displayTitle;})();
      const _pp=posterParts(f,{header:true,body:_edBodyTitle}); // decisión única (posterModel)
      if(_pp.ed){
        _edAccent=_pp.accent;
        posterImg=_pp.inner;
      } else {
        posterImg=posterSrc
          ?`<img src="${posterSrc}" loading="lazy" data-title="${f.title.replace(/"/g,'&quot;')}" style="width:100%;height:100%;object-fit:cover${_opacity};display:block;opacity:0;transition:opacity 250ms ease" onload="this.style.opacity='1'" onerror="_posterErr(this)" alt="">`
          :``;
      }
    }
    const _sep=activeDay==='all'&&f.section&&f.section!==_prevSec?`<div class="sec-hdr sm poster-grid-sep">${_secLabelFull(f.section||'')}</div>`:'';_prevSec=f.section||_prevSec;
    return _sep+`<div class="bg-surf-2 poster-card js-open-pel${inWL&&!inW?' in-wl':''}${inW&&!_ended?' in-watched':''}${_edAccent?' poster-ed':''}" data-title="${escXML(f.title)}"${_edAccent?` style="--ed-accent:${_edAccent}"`:(_isPrograma?'':_cardBg)}>
      ${posterImg}
      ${progBadge}
      ${inWL?`<button class="poster-wl-dot wl-on" data-title="${f.title.replace(/"/g,'&quot;')}" data-action="toggleWL" data-stop="1" aria-label="${t('misc_interes_label')}">${ICONS.heartFill}</button>`:''}
    </div>`
  }).join('')}</div>`;
  return {html, hasEntries: true};
}


// ── Step 6h: render dispatcher cartelera/horario + sub-nav + lugar overlay. ───
export function render(){
  // Group II Tier 3 (p6c): branchy multi-dispatcher con 4 early returns.
  // Split impráctico — body se queda monolítico con state.snapshot() destructure.
  const {FILMS, _activeFestId, watched, watchlist} = state.snapshot();
  if(activeView==='agenda') return;
  // Si estamos en Cartelera con el nuevo sistema, _renderProgramaContent lo maneja
  if(activeView==='day'&&document.getElementById('programa-mode-bar')?.style.display!=='none'){
    if(activeDay==='all'){renderSbar();renderPeliculaView();return;}
    // Hoy/Mañana — forzar cartelaMode horario para que render() use la vista por día
    cartelaMode='horario';
  }
  if(cartelaMode==='pelicula'){renderSbar();renderPeliculaView();return;}
  lugarClose(); // refresh label if open
  let films=FILMS.filter(f=>f.day===activeDay);
  if(activeVenue!=='all') films=films.filter(f=>vcfg(f.venue).short===activeVenue);
  if(activeSec!=='all') films=films.filter(f=>f.section===activeSec);
  films.sort((a,b)=>toMin(a.time)-toMin(b.time));
  const cntEl=document.getElementById('cnt');
  cntEl.innerHTML=''; // count eliminado — redundante con lugar-btn y chips
  const grid=document.getElementById('grid');
  if(!films.length){grid.innerHTML=emptyState(ICONS.search,t('filter_sin_actividades'),t('empty_filtros'));return;}
  // ── Vista horario: poster-grid 3 col + overlay de hora ──
  grid.innerHTML='<div class="poster-grid">'+films.map((f,i)=>{
    const isProg=f.is_cortos;
    const isEvent=f.type==='event';
    const passed=screeningPassed(f);
    const inWL=watchlist.has(f.title),inW=watched.has(f.title);
    const isNow=isNowShowing(f);
    const safeT=f.title.replace(/"/g,'&quot;').replace(/'/g,"&#39;");
    const posterSrc=getFilmPoster(f);
    const _cardBg2='';
    const posterImg=posterSrc
      ?`<img class="img-cover" src="${posterSrc}" loading="lazy" data-title="${f.title.replace(/"/g,'&quot;')}" onerror="_posterErr(this)" alt="">`
      :``;
    const progBadge='';//REMOVED
    const nowBadge=isNow?`<div class="poster-now">${t('misc_ahora')}</div>`:'';
    const _notice=NOTICES.find(n=>n.title===f.title&&n.festival===(_activeFestId||_DEFAULT_FEST_ID));
    const pastBadge=_notice?`<div class="badge-past poster-past-badge">${_notice.type==='cancelled'?t('notice_cancelada'):t('notice_reprog_short')}</div>`:'';

    const _fe=festivalEnded();
return`<div class="poster-card js-open-pel${inWL&&!inW?' in-wl':''}${inW&&!_fe?' in-watched':''}${passed&&!_fe?' past-card':''}" data-title="${escXML(f.title)}"${_cardBg2}>
      ${posterImg}
      <div class="poster-time">${f.time}</div>
      ${nowBadge||pastBadge||progBadge}
      ${inWL?`<button class="poster-wl-dot wl-on" data-title="${f.title.replace(/"/g,'&quot;')}" data-action="toggleWL" data-stop="1" aria-label="${t('misc_interes_label')}">${ICONS.heartFill}</button>`:''}
    </div>`;
  }).join('')+'</div>';

  // ── Cartelera: micro-CTA only (step bar removed from PROGRAMA context)
  // Flow progress bar belongs in INTERESES/PLANEAR/MI PLAN tabs, not in PROGRAMA.
  if(activeView==='day'){
    const _cStepper=document.getElementById('cartelera-stepper');
    const _cCta=document.getElementById('cartelera-cta');
    if(_cStepper) _cStepper.style.display='none';// always hidden in day/hora view
  }
}

export function renderSbar(){
  // Reclasificada Group II durante 6c: no usa innerHTML para contenido —
  // crea botones con createElement + appendChild + handlers programáticos
  // (.onclick = fn). Split E1a no aplica sin cambiar byte-identity del DOM.
  const {FILMS} = state.snapshot();
  const panel=document.getElementById('sdr-panel');
  const trigBtn=document.getElementById('sdr-btn');
  const lbl=document.getElementById('sdr-label');
  if(!panel) return;
  panel.innerHTML='';
  const isExplorar=activeDay==='all';
  let dayF=isExplorar?FILMS:FILMS.filter(f=>f.day===activeDay);
  if(activeVenue!=='all') dayF=dayF.filter(f=>vcfg(f.venue).short===activeVenue);
  const secs=[...new Set(dayF.map(f=>f.section))].sort((a,b)=>{
    const ia=SECTION_ORDER_LIST.indexOf(a),ib=SECTION_ORDER_LIST.indexOf(b);
    if(ia>=0&&ib>=0) return ia-ib;
    if(ia>=0) return -1;
    if(ib>=0) return 1;
    return a.localeCompare(b);
  });
  if(lbl){const _al=_secLabelFull(activeSec);lbl.textContent=activeSec==='all'||activeSec==='_chip_'?t('bar_seccion'):(_al.length>18?_al.slice(0,16)+'…':_al);}
  if(trigBtn) trigBtn.classList.toggle('on',activeSec!=='all'&&activeSec!=='_chip_');
  const mkOpt=(html,isOn,cb)=>{
    const b=document.createElement('button');
    b.className='fdr-opt'+(isOn?' on':'');
    b.innerHTML=html;
    b.onclick=e=>{e.stopPropagation();cb();};
    panel.appendChild(b);
  };
  mkOpt(`${t('sbar_todas_categorias')} <span class="fdr-cnt">${dayF.length}</span>`,activeSec==='all',()=>{activeSec='all';selectedIdx=null;render();});
  secs.forEach(sec=>{
    const cnt=dayF.filter(f=>f.section===sec).length;
    mkOpt(`${_secLabelFull(sec)} <span class="fdr-cnt">${cnt}</span>`,activeSec===sec,()=>{activeSec=activeSec===sec?'all':sec;selectedIdx=null;render();});
  });
}

export function lugarClose(){
  const drop = document.getElementById('lugar-drop');
  if(drop) drop.remove();
  document.removeEventListener('click', lugarOutside);
  window.removeEventListener('scroll', lugarClose);
  const btn = document.getElementById('lugar-btn');
  if(btn) btn.classList.toggle('on', activeVenue!=='all');
  const lbl = document.getElementById('lugar-lbl');
  if(lbl) lbl.textContent = t('bar_lugar');
}

export function lugarOutside(e){
  const drop = document.getElementById('lugar-drop');
  const btn = document.getElementById('lugar-btn');
  if(drop && !drop.contains(e.target) && e.target!==btn && !btn?.contains(e.target)){
    lugarClose();
  }
}
