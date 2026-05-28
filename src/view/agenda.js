// ── src/view/agenda.js ────────────────────────────────────────────────────────
// p8 Step 6f — Render de agenda + miplan (selección/planner/Mi Plan).
// 18 fns. Closure AST = 20 (incl. emptyState/emptyStateHero/DAYS → helpers.js).
// View-state lets (_activeMiPlanFilm/_expandedFilm/activeMiPlanDay/miPlanViewStart/
// _ctaRemovedVisible/archiveOpen) viven en main.js, leídos/escritos vía STATE
// BRIDGE (globalThis) — patrón 6c (D-6F-1). Roster (FILMS/watchlist/...) idem.
// runCalc NO es dep de este árbol (va a Wave 7 controller).

import {
  DEFAULT_DURATION_MIN, FESTIVAL_BUFFER, FESTIVAL_CONFIG,
} from '../config.js';
import {
  ICONS, _secLabel, _secLabelFull, _sectionColor, makeEventPoster, parseProgramTitle, renderAvBlocksHTML, renderFlowProgress,
} from './components.js';
import {
  DAYS, DAY_SHORT_EN, _dayChips, _isEditorialPoster, _langDates, _lblLocalized, _mkCortoItemHtml, _posterThumb, dayChip, dayLabel, durFmt, emptyState, emptyStateHero, flagFmt, getFilmPoster, isToday, mplanBlockType, mplanEndStr, sala, starsText, travelWarn, vcfg,
} from './helpers.js';
import {
  _festDate, festivalEnded, minToStr, parseDur, simNow, simTodayStr, toMin,
} from '../domain/time.js';
import {
  screeningPassed,
} from '../domain/film.js';
import {
  isScreeningBlocked, screensConflict,
} from '../domain/schedule.js';
import {
  _getFestivalPhase, travelMins,
} from '../domain/festival.js';
import {
  state,
} from '../state/state.js';
import {
  t,
} from '../i18n/i18n.js';

export function renderAgenda(){
  // Group II Tier 3 (p6c): 3 branches (seleccion/miplan/planner) con follow-ups
  // branch-específicos (_scrollMiPlanToNow, _updateMiPlanBadge, renderAvBlocks,
  // _agHi.style.display, requestAnimationFrame(_fixStickyOffset)). Split impráctico
  // — body se queda monolítico con state.snapshot() destructure al top.
  const {savedAgenda, FILMS, _activeFestId, watched, watchlist, prioritized} = state.snapshot();
  const view=document.getElementById('ag-view');
  if(activeMNav==='mnav-seleccion'){
    // ── Post-festival: redirigir a Mi Plan ──
    if(festivalEnded()){
      const _festName=(FESTIVAL_CONFIG[_activeFestId]||{}).name||'El festival';
      const _hasMiPlan=watched.size>0||(savedAgenda&&savedAgenda.schedule&&savedAgenda.schedule.length>0);
      const _agHi=document.getElementById('hdr-ag');if(_agHi)_agHi.style.display='none';
      requestAnimationFrame(_fixStickyOffset);
      view.innerHTML=emptyStateHero(
        ICONS.sparkles,
        `${_festName} ${t('plan_fest_terminado')}`,
        _hasMiPlan?t('plan_revisa_planeaste'):t('empty_programa'),
        _hasMiPlan?t('cta_mi_plan'):t('plan_ir_programa'),
        _hasMiPlan?'mnav-miplan':'mnav-cartelera'
      );
      return;
    }
    // ── Mi Lista: buscador + lista de películas ──
    const _progressHtml=(!savedAgenda||!savedAgenda.schedule||!savedAgenda.schedule.length)?renderFlowProgress(state,'seleccion'):'';
    view.innerHTML=`${_progressHtml}
      <div class="ag-section">
        <div id="ag-film-list">${renderFilmListHTML(state)}</div>
      </div>`;

  } else if(activeMNav==='mnav-miplan'){
    // ── Mi Plan: stepper de progreso + calendario + sugerencias ──
    const _progressHtmlPlan=(!festivalEnded()&&(!savedAgenda||!savedAgenda.schedule||!savedAgenda.schedule.length))?renderFlowProgress(state,'miplan'):'';
    view.innerHTML=_progressHtmlPlan+renderSavedAgendaHTML(state);
    _scrollMiPlanToNow();
    _updateMiPlanBadge();
  } else {
    // ── Planear: stepper de progreso + prio strip + disponibilidad + opciones ──
    if(festivalEnded()){
      // Post-festival: Planear no tiene función — redirigir a Mi Plan
      const _festNamePl=(FESTIVAL_CONFIG[_activeFestId]||{}).name||'El festival';
      const _agHpl=document.getElementById('hdr-ag');if(_agHpl)_agHpl.style.display='none';
      requestAnimationFrame(_fixStickyOffset);
      view.innerHTML=emptyStateHero(ICONS.sparkles,`${_festNamePl} ${t('plan_fest_terminado')}`,t('plan_revisa_planeaste'),t('cta_mi_plan'),'mnav-miplan');
      return;
    }
    const _progressHtml=(!savedAgenda||!savedAgenda.schedule||!savedAgenda.schedule.length)?renderFlowProgress(state,'planner'):'';
    const pending=[...watchlist].filter(titleStr=>!watched.has(titleStr)&&FILMS.some(f=>f.title===titleStr&&!screeningPassed(f)));

    // ── Estado A: sin Intereses — pantalla simple, no mostrar herramienta ──
    if(!pending.length&&!cachedResult){
      view.innerHTML=`${_progressHtml}
        <div class="ag-section">
          ${emptyStateHero(ICONS.calendar,t('plan_tu_plan_empty'),t('empty_intereses_3'),t('cta_ir_intereses'),'mnav-seleccion')}
        </div>`;
      return;
    }

    // ── Estado B: con Intereses — herramienta completa ──
    // Pre-cálculo limpio: solo stepper + Disponibilidad + botón Calcular.
    // Stale + resumen post-cálculo viven en buildResultHTML.
    const _snap=cachedResult&&cachedResult._prioSnapshot;
    const _stale=!!cachedResult&&Array.isArray(_snap)&&(_snap.length!==prioritized.size||!_snap.every(x=>prioritized.has(x)));
    const resultContent=cachedResult
      ?buildResultHTML(cachedResult.scenarios)
      :'';
    view.innerHTML=`${_progressHtml}
      <div class="ag-section">
        <div class="section-div">
          <div class="mb-2 sec-hdr">${ICONS.clock} ${t('av_disponibilidad')} <span class="sec-hdr-opt">${t('misc_opcional')}</span></div>
          <div class="txt-gray2-sm-lh">${t('av_no_incluir')}</div>
          <div id="av-blocks-list"></div>
          <button class="av-add-unavail" data-action="openAvSheet">${ICONS.plus} ${t('misc_no_disponible')}</button>
        </div>
        <div class="av-calc-wrap">
          <button class="av-calc-btn" data-action="runCalc">
            ${t('av_ver_opciones')}
          </button>
        </div>
      </div>
      <div class="amber-border-top ag-section${_stale?' stale':''}" id="ag-result-wrap"${cachedResult?'':' style="display:none"'}>
        <div class="txt-amber60 sec-hdr">${ICONS.switch} ${t('plan_opciones')}</div>
        <div id="ag-result">${resultContent}</div>
      </div>`;
    renderAvBlocks();
  }
}

export function renderMiPlanCalendar(state){
  const {savedAgenda, FILMS, prioritized, FESTIVAL_DATES} = state.snapshot();
  if(!savedAgenda||!savedAgenda.schedule.length) return'';
  const schedule=savedAgenda.schedule;
  const todayStr=simTodayStr();
  const nowDayIdx=DAY_KEYS.findIndex(d=>FESTIVAL_DATES[d]===todayStr);
  const nowMin=simNow().getHours()*60+simNow().getMinutes();
  if(activeMiPlanDay===null){
    const firstDayWithFilm=DAY_KEYS.findIndex(d=>schedule.some(s=>s.day===d));
    activeMiPlanDay=nowDayIdx>=0?nowDayIdx:Math.max(0,firstDayWithFilm);
    // Alinear viewport con el día activo — replicable en futuros festivales
    miPlanViewStart=Math.max(0,Math.min(activeMiPlanDay,DAY_KEYS.length-2));
  }

  // ── Layout constants ──
  const PHDR=44;   // px for sticky day header
  const PPH=window.innerWidth<=600?40:64; // mobile: 40px/hr, desktop: 64px/hr

  // REGLA: rango dinámico — calcular desde los días visibles solamente.
  // Si los días visibles están vacíos, fallback al plan completo.
  // Buffer 30min en cada extremo, snapped a hora entera.
  // Límites absolutos: nunca antes de las 9:00, nunca después de las 26:00.
  const vs=miPlanViewStart;
  const ve=vs+1;
  const _visDays=new Set([DAY_KEYS[vs],DAY_KEYS[ve]]);
  const _visSched=schedule.filter(s=>_visDays.has(s.day));
  const _src=_visSched.length?_visSched:schedule;
  const _allMins=_src.flatMap(s=>{
    const st=toMin(s.time), en=st+parseDur(s.duration);
    return[st,en];
  });
  const _minStart=Math.min(..._allMins);
  const _maxEnd=Math.max(..._allMins);
  const SH=Math.max(9, Math.floor((_minStart-30)/60));
  const EH=Math.min(26, Math.ceil((_maxEnd+30)/60));

  const TOTAL=(EH-SH)*PPH;
  function toPx(min){return(min-SH*60)/60*PPH;}

  // ── Time axis labels (every hour, on the left) ──
  const axisHtml=Array.from({length:EH-SH+1},(_,k)=>{
    const h=SH+k;
    const top=PHDR+toPx(h*60);
    const lbl=(h%24)+':00';
    return`<div class="mplan-wk-htick" style="top:${top.toFixed(0)}px">${lbl}</div>`;
  }).join('');

  // ── Navigation header ──
  // En overview: no paginador
  const lbl1=dayLabel(DAY_KEYS[vs]); // 'MIÉ 15'
  const lbl2=dayLabel(DAY_KEYS[ve]); // 'MIÉ 15'
  const isPastVs=nowDayIdx>=0&&vs<nowDayIdx;
  const isPastVe=nowDayIdx>=0&&ve<nowDayIdx;
  const navHtml=`<div class="mplan-nav">
    <div class="mplan-nav-btn-wrap">
      <button class="mplan-nav-btn" aria-label="${t('aria_dia_ant')}" data-action="miPlanNav" data-dir="-1" ${vs===0?'disabled':''}><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5"/></svg></button>
    </div>
    <div class="mplan-nav-labels">
      <div class="mplan-nav-day${isPastVs?' past':''}" data-action="selectMiPlanDay" data-index="${vs}">
        <div class="mplan-nav-day-name">${_lblLocalized((DAY_SHORT_EN[DAYS[vs].k]||DAYS[vs].lbl).split(' ')[0])}</div>
        <div class="mplan-nav-day-num${vs===activeMiPlanDay?' wk-active-num':''}">${DAYS[vs].d}</div>
        ${vs===activeMiPlanDay?'<div class="mplan-nav-day-arrow"><svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.25" stroke-linecap="round" stroke-linejoin="round"><path d="M19.5 8.25l-7.5 7.5-7.5-7.5"/></svg></div>':''}
      </div>
      <div class="mplan-nav-day${isPastVe?' past':''}" data-action="selectMiPlanDay" data-index="${ve}">
        <div class="mplan-nav-day-name">${_lblLocalized((DAY_SHORT_EN[DAYS[ve].k]||DAYS[ve].lbl).split(' ')[0])}</div>
        <div class="mplan-nav-day-num${ve===activeMiPlanDay?' wk-active-num':''}">${DAYS[ve].d}</div>
        ${ve===activeMiPlanDay?'<div class="mplan-nav-day-arrow"><svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.25" stroke-linecap="round" stroke-linejoin="round"><path d="M19.5 8.25l-7.5 7.5-7.5-7.5"/></svg></div>':''}
      </div>
    </div>
    <div class="mplan-nav-btn-wrap right">
      <button class="mplan-nav-btn" data-action="miPlanNav" data-dir="1" ${ve>=DAY_KEYS.length-1?'disabled':''}>${ICONS.chevronR}</button>
    </div>
  </div>`;

  // ── Desktop: all 6 columns; Mobile: 2 columns via nav ──
  const renderCol=(i,extraClass='')=>{
    const day=DAY_KEYS[i];
    const dayFilms=schedule.filter(s=>s.day===day).sort((a,b)=>toMin(a.time)-toMin(b.time));
    const isPastDay=nowDayIdx>=0&&i<nowDayIdx;
    const isToday=i===nowDayIdx;
    const isActive=i===activeMiPlanDay;

    // Hour grid lines
    let gridHtml='';
    for(let h=SH;h<EH;h++){
      const top=PHDR+toPx(h*60);
      gridHtml+=`<div class="mplan-wk-hline mp-major" style="top:${top.toFixed(0)}px"></div>`;
      gridHtml+=`<div class="mplan-wk-hline" style="top:${(top+PPH/2).toFixed(0)}px"></div>`;
    }

    // Now line
    let nowHtml='';
    if(isToday&&nowMin>=SH*60&&nowMin<EH*60){
      const top=PHDR+toPx(nowMin);
      nowHtml=`<div class="mplan-wk-nowline" style="top:${top.toFixed(0)}px"><div class="mplan-wk-nowdot"></div></div>`;
    }

    // Film blocks
    const blocksHtml=dayFilms.map(s=>{
      const fMin=toMin(s.time),dur=parseDur(s.duration);
      const top=PHDR+toPx(fMin);
      const blockH=Math.max(dur/60*PPH-4,20);
      const isPast=isPastDay||(isToday&&fMin+dur<nowMin);
      const isNow=isToday&&fMin<=nowMin&&fMin+dur>nowMin;
      const type=mplanBlockType(s);
      const filmKey=(s._title||'')+s.time;
      const isActive=filmKey===_activeMiPlanFilm;
      const stateClass=isPast?' mp-past':isNow?' mp-now':isActive?' mp-active':'';
      const{displayTitle}=parseProgramTitle(s._title||'');
      const isPrio=type==='mp-priority';
      const isEvent=type==='mp-event';
      const showVenue=blockH>44;
      const vc2=vcfg(s.venue);
      return`<div class="mplan-wk-block ${type}${stateClass}" style="top:${top.toFixed(0)}px;height:${blockH.toFixed(0)}px" data-fkey="${(s._title||'')}${s.time}" data-action="activatePlanFilm" data-day-index="${i}" data-stop="1" title="${(s._title||'').replace(/"/g,'&quot;')}">
        ${isPrio?`<div class="mplan-wk-badge">★</div>`:''}
        <div class="mplan-wk-time${isEvent?' mp-event-time':''}">${s.time}</div>
        <div class="mplan-wk-title${isEvent?' mp-event-title':''}">${displayTitle}</div>
        ${showVenue?`<div class="mplan-wk-venue">${ICONS.pin} ${vc2.short}</div>`:''}
      </div>`;
    }).join('');

    const colClass=['mplan-wk-col',isToday?'wk-today':'',isActive?'wk-active':'',extraClass].filter(Boolean).join(' ');
    return`<div class="${colClass}" style="height:${PHDR+TOTAL}px" data-action="selectMiPlanDay" data-index="${i}">
      <div class="mplan-wk-col-hdr">
        <div class="mplan-wk-col-day"><span class="mplan-wk-day-name">${_lblLocalized((DAY_SHORT_EN[DAYS[i].k]||DAYS[i].lbl).split(' ')[0])}</span><span class="mplan-wk-col-date${dayFilms.length?' wk-has':''}">${DAYS[i].d}</span></div>
        ${dayFilms.length?(isActive?'<div class="mplan-wk-col-arrow"><svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.25" stroke-linecap="round" stroke-linejoin="round"><path d="M19.5 8.25l-7.5 7.5-7.5-7.5"/></svg></div>':'<div class="mplan-wk-col-dot"></div>'):''}
      </div>
      ${gridHtml}${nowHtml}${blocksHtml}
    </div>`;
  };
  const desktopCols=DAY_KEYS.map((_,i)=>renderCol(i,'mplan-col-desktop')).join('');
  const mobileCols=[vs,ve].map(i=>renderCol(i,'mplan-col-mobile')).join('');
  const colsHtml=desktopCols+mobileCols;

  // ── Detail list for active day ──
  const activeKey=DAY_KEYS[activeMiPlanDay];
  const dayFilms=schedule.filter(s=>s.day===activeKey).sort((a,b)=>toMin(a.time)-toMin(b.time));
  const isPastDay=nowDayIdx>=0&&activeMiPlanDay<nowDayIdx;

  let listHtml=`<div class="mplan-list" id="mplan-detail"><div class="mplan-list-hdr">${dayChip(activeKey)}${dayFilms.length?`<span class="count-badge cb-neutral">${dayFilms.length}</span>`:''}</div>`;
  if(!dayFilms.length){
    if(!isPastDay){
      // CTA C: día futuro sin películas — invita a explorar sugerencias o recalcular
      listHtml+=`<div class="cta-ctx cta-ctx-c" data-action="scrollToSuggestions">
        <div class="cta-ctx-ico">${ICONS.calendar}</div>
        <div class="cta-ctx-body">
          <div class="cta-ctx-title cta-ctx-title-c">${t('plan_dia_libre')}</div>
          <div class="cta-ctx-sub">${t('plan_empty_dia')} ${t('plan_recalcular_suffix')}</div>
        </div>
        <div class="cta-ctx-arr cta-ctx-arr-c">${ICONS.chevronD}</div>
      </div>`;
    } else {
      listHtml+=`<div class="mplan-empty">${t('plan_nada_dia')}</div>`;
    }
  } else {
    dayFilms.forEach((s,idx)=>{
      const fMin=toMin(s.time),dur=parseDur(s.duration);
      const isPast=isPastDay||(activeMiPlanDay===nowDayIdx&&fMin+dur<nowMin);
      const isNow=activeMiPlanDay===nowDayIdx&&fMin<=nowMin&&fMin+dur>nowMin;
      const safeT=(s._title||'').replace(/"/g,'&quot;');
      if(idx>0){
        const prev=dayFilms[idx-1];
        const gap=fMin-(toMin(prev.time)+parseDur(prev.duration));
        if(gap>=0&&gap<25){
          const _isCritical=gap<=5;
          listHtml+=`<div class="mplan-warn-row" style="${_isCritical?'color:var(--red)':''}">${ICONS.alert} ${_isCritical?t('warn_sin_tiempo'):`~${gap} ${t('warn_min_hasta_sig')}`}</div>`;
        }
        if(prev.has_qa){const qaGap=gap-30;qaGap<0?listHtml+=`<div class="mplan-warn-row" style="color:var(--red)">${t('warn_qa_no_llega')}</div>`:listHtml+=`<div class="mplan-warn-row">${t('warn_qa_tiempo',{n:qaGap})}</div>`;}
        const tw=travelWarn(prev,s);
        if(tw) listHtml+=`<div class="mplan-warn-row">${tw}</div>`;
      }
      const _rowKey=(s._title||'')+s.time;
      const _safeRowKey=_rowKey.replace(/"/g,'&quot;');
      const _mf=FILMS.find(fi=>fi.title===s._title);const _mp=_mf?getFilmPoster(_mf):null;
      const _isEventRow=_mf&&_mf.type==='event';
      const _safeMpT=(s._title||"").replace(/'/g,"\\'");
      const _mphInner=_mp
          ?_posterThumb(_mf,'lb-poster')
          :_isEventRow
            ?`<img class="lb-poster" src="${makeEventPoster(state,_mf.title,_mf.duration,_mf.event_kind)}" alt="" loading="lazy" onerror="this.remove()">`
            :_posterThumb(_mf,'lb-poster');
      const _mph=`<div class="js-open-pel" data-title="${s._title||''}" style="flex-shrink:0;cursor:pointer" data-stop="1">${_mphInner}</div>`
      listHtml+=`<div class="mplan-row${_rowKey===_activeMiPlanFilm?' active':''}" style="cursor:pointer" data-rkey="${_safeRowKey}" data-action="selectFromDetail">
        ${_mph}
        <div class="mplan-tc" data-stop="1">
          <div class="mplan-t1${isPast?' mp-past':''}" ${!isPast?`data-action="toggleFilmAlternatives" data-key="${(s._title||'')+(s.day||'')+(s.time||'')}" data-title="${safeT}" data-day="${s.day||''}" data-time="${s.time||''}" data-stop="1"`:''} title="${!isPast?'Cambiar horario':''}">${s.time}</div>
          <div class="mplan-t2">${mplanEndStr(s.time,dur)}${prioritized.has(s._title)?` <span class="txt-amber60-xs">★</span>`:''}${isNow?` <span class="txt-green-semi">en curso</span>`:''}</div>
        </div>
        <div class="mplan-ri">
          <div>${(()=>{const{displayTitle:_dt,progSuffix:_ps}=parseProgramTitle(s._title||'');const _mfqa=FILMS.find(fi=>fi.title===s._title&&fi.day===s.day&&fi.time===s.time);const _qab=_mfqa?.has_qa?`<span class="meta-badge sm">Q&A</span>`:'';return`<div class="mplan-rtitle${_isEventRow?' mp-event-title':''}">${_dt}${_qab}</div>${_ps?`<div class="prog-suffix">${_ps}</div>`:''}`;})()} </div>
          <div class="mplan-rvenue${_isEventRow?' mp-event-venue':''}">${ICONS.pin} ${vcfg(s.venue).short}${sala(s.venue)?' \u00b7 '+sala(s.venue):''}</div>
          ${(()=>{const _mf=FILMS.find(fi=>fi.title===s._title&&fi.day===s.day&&fi.time===s.time);if(!_mf||!_mf.is_cortos||!_mf.film_list||!_mf.film_list.length) return'';return`<button class="row-xs mplan-prog-toggle" data-action="toggleMplanProg">${ICONS.chevronR} ${t('label_programa')}</button>`;})()}
        </div>
        <div class="col-end">
          <button class="icon-btn-circle ag-fi-btn del" data-title="${safeT}" data-action="removeFromAgenda" data-stop="1">${ICONS.x}</button>
        </div>
      </div>${_expandedFilm===(s._title||'')+(s.day||'')+(s.time||'')?`<div class="film-alts">${renderFilmAlternatives(state,s._title,s.day,s.time)}</div>`:''}${(()=>{const _mf=FILMS.find(fi=>fi.title===s._title&&fi.day===s.day&&fi.time===s.time);if(!_mf||!_mf.is_cortos||!_mf.film_list||!_mf.film_list.length) return'';return`<div class="mplan-prog-list">${_mf.film_list.map((item,n)=>_mkCortoItemHtml(item,n,{section:_mf.section||''})).join('')}</div>`;})()}`;
    });
  }
  listHtml+='</div>';

  return `<div class="mplan-wrap">
    ${navHtml}
    <div class="mplan-wk-outer" style="height:${PHDR+TOTAL}px">
      <div class="mplan-wk-inner" style="height:${PHDR+TOTAL}px">
        <div class="mplan-wk-axis" style="height:${PHDR+TOTAL}px">${axisHtml}</div>
        <div class="mplan-wk-cols">${colsHtml}</div>
      </div>
    </div>
    ${listHtml}
    ${(()=>{
      const _hintSeen=localStorage.getItem('otrofestiv_hint_cambiar');
      const _hasFuture=savedAgenda&&savedAgenda.schedule.some(s=>!screeningPassed(s));
      if(_hintSeen||!_hasFuture) return '';
      return`<div class="mplan-change-hint">${ICONS.clock} ${t('plan_hint_hora')} ${t('misc_pelicula')}</div>`;
    })()}
    <div class="mplan-bottom-actions">
      <button class="mplan-bottom-btn" data-action="sharePlan">${ICONS.share} ${t('plan_compartir')}</button>
      <button class="mplan-bottom-btn" data-action="exportICS">${ICONS.calendar} ${t('misc_calendario')}</button>
    </div>
  </div>`
}

export function renderUnconfirmed(state,schedule){
  const {watched, FESTIVAL_DATES} = state.snapshot();
  const now=simNow();
  const past=schedule.filter(s=>{
    if(watched.has(s._title)) return false;
    const dateStr=FESTIVAL_DATES[s.day];if(!dateStr) return false;
    const end=_festDate(dateStr,s.time);
    end.setMinutes(end.getMinutes()+parseDur(s.duration));
    return end<now;
  }).sort((a,b)=>{
    const da=_festDate(FESTIVAL_DATES[a.day],a.time);
    const db=_festDate(FESTIVAL_DATES[b.day],b.time);
    return db-da;
  });
  if(!past.length) return'';
  const nowMin=now.getHours()*60+now.getMinutes();
  const todayStr=simTodayStr();
  const todayKey=DAY_KEYS.find(d=>FESTIVAL_DATES[d]===todayStr);
  const latest=past[0];const older=past.slice(1);
  const{displayTitle}=parseProgramTitle(latest._title||'');
  const short=displayTitle.length>28?displayTitle.slice(0,26)+'…':displayTitle;
  const endMs=_festDate(FESTIVAL_DATES[latest.day],latest.time).getTime()+parseDur(latest.duration)*60000;
  const minsAgo=Math.round((now.getTime()-endMs)/60000);
  const timeDesc=minsAgo<120?`${t('plan_termino_hace')} ${minsAgo} min`:`${dayLabel(latest.day)} · ${latest.time}`;
  const safeLast=latest._title.replace(/'/g,"&#39;");
  const olderHtml=older.length?`
    <div id="ctx-older" style="display:none">
      ${older.map(s=>{
        const{displayTitle:dt}=parseProgramTitle(s._title||'');
        const sh=dt.length>26?dt.slice(0,24)+'…':dt;
        const st=s._title.replace(/'/g,"&#39;");
        return`<div class="checkin-item">
          <div class="checkin-info"><div class="checkin-title">${sh}</div><div class="checkin-time">${dayLabel(s.day)} · ${s.time}</div></div>
          <div class="checkin-btns"><button class="row-xs checkin-btn yes" data-action="checkinLaVi" data-title="${st}">${ICONS.check} ${t('cta_vista')}</button><button class="checkin-btn no" data-action="checkinNoLaVi" data-title="${st}">${t('misc_luego')}</button></div>
        </div>`;
      }).join('')}
    </div>
    <div class="sim-hdr-pad">
      <button class="link-gray-xs"
        data-action="toggleCtxOlder">
        + ${older.length} ${older.length>1?t('label_anteriores'):t('label_anterior')} ${t('label_sin_confirmar')}
      </button>
    </div>`:'';
  return`<div class="checkin-wrap">
    <div class="checkin-hdr">${t('label_funciones')} ${t('label_sin_confirmar')}</div>
    <div class="checkin-item">
      <div class="checkin-info"><div class="checkin-title">${short}</div><div class="checkin-time">${timeDesc}</div></div>
      <div class="checkin-btns">
        <button class="row-xs checkin-btn yes" data-action="checkinLaVi" data-title="${safeLast}">${ICONS.check} ${t('cta_vista')}</button>
        <button class="checkin-btn no" data-action="checkinNoLaVi" data-title="${safeLast}">${t('misc_luego')}</button>
      </div>
    </div>${olderHtml}
  </div>`;
}

export function renderFilmAlternatives(state,title,day,time){
  const {FILMS, watched, savedAgenda} = state.snapshot();
  const fStart=toMin(time);
  const safeT=title.replace(/'/g,"&#39;");
  const plannedTitles=new Set(savedAgenda?savedAgenda.schedule.map(s=>s._title):[]);
  // ±15 min window — direct competition in the same slot
  const WINDOW=15;
  const opts=FILMS.filter(f=>{
    if(f.day!==day) return false;
    if(f.title===title) return false;
    if(plannedTitles.has(f.title)) return false;
    if(watched.has(f.title)) return false;
    if(isScreeningBlocked(f)) return false;
    return Math.abs(toMin(f.time)-fStart)<=WINDOW;
  }).sort((a,b)=>toMin(a.time)-toMin(b.time));

  const optsHtml=opts.map(f=>{
    const vc2=vcfg(f.venue);
    const{displayTitle}=parseProgramTitle(f.title);
    const short=displayTitle.length>28?displayTitle.slice(0,26)+'…':displayTitle;
    const safeTNew=f.title.replace(/'/g,"&#39;");
    return`<div class="checkin-opt" data-action="confirmReplace" data-rmtitle="${safeT}" data-newtitle="${safeTNew}" data-day="${f.day}" data-time="${f.time}">
      <div class="checkin-opt-info">
        <div class="checkin-opt-time">${f.time} · ${durFmt(f.duration)}</div>
        <div class="checkin-opt-title">${short}</div>
        <div class="checkin-opt-venue">${ICONS.pin} ${vc2.short}</div>
      </div>
      <div class="checkin-opt-add">${ICONS.plus}</div>
    </div>`;
  }).join('');

  return`<div class="film-alts">
    ${optsHtml||`<div class="scenario-label">${t('plan_no_alts_horario')}.</div>`}
    <div class="scenario-footer">
      <button class="w-full-sm checkin-result-btn secondary" data-action="clearExpandedFilm">${t('misc_cerrar')}</button>
    </div>
  </div>`;
}

export function renderContextualHeader(state){
  const {savedAgenda, FILMS, watched, prioritized, filmRatings, filmDelays, _activeFestId, _lang} = state.snapshot();
  const ph=_getFestivalPhase();
  if(!ph) return '';
  const _dayAbbr=k=>(dayLabel(k)||k).split(' ')[0]||'';

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
      const _isEdList=_isEditorialPoster(f);
      const safeT=t.replace(/'/g,"&#39;");
      const stars=r?starsText(r):'';
      // Posters grandes, plena opacidad — pensado para screenshot
      return`<div class="poster-card ended-poster js-open-pel${_isEdList?' editorial':''}" data-title="${f.title}">
        ${_isEdList
          ?`<div class="ed-hdr" style="background:${_sectionColor(f.section||'')}"><div class="ed-lbl">${_secLabel(f.section||'')}</div></div><div class="ed-img"><img src="${src}" onerror="this.remove()" alt="" loading="lazy"></div><div class="ed-body"></div>`
          :src?`<img class="img-cover" src="${src}" loading="lazy" onerror="this.remove()" alt="">`:``}
        <div class="ended-poster-footer">
          ${r?`<div class="label-track-amber">${stars}</div>`
             :`<button class="ended-rate-btn" data-action="openPostViewRating" data-title="${safeT}" data-stop="1">★</button>`}
          <div class="ended-poster-title">${dt}</div>
        </div>
      </div>`;
    }).join('');
    const subMsg=totalWatched===0
      ?t('empty_prox_fest')
      :pendingRatings>0
        ?`${pendingRatings} ${t('plan_sin_calificar')}`
        :t('empty_todo_calif');
    const mainTitle=totalWatched===0
      ?((FESTIVAL_CONFIG[_activeFestId]||{}).name||'El festival')+` ${t('plan_fest_terminado')}`
      :`${t('plan_viste_n')} ${totalWatched} ${totalWatched!==1?(t('misc_pelicula')+'s'):t('misc_pelicula')}`;
    return`<div class="pad-sm">
      <div class="ctx-eyebrow">
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26"/></svg>
        ${(FESTIVAL_CONFIG[_activeFestId]||{}).name||''} · ${_langDates(FESTIVAL_CONFIG[_activeFestId])}
      </div>
      <div class="ctx-main-title">${mainTitle}</div>
      <div class="ctx-sub" style="margin-bottom:${totalWatched?'12px':'0'}">${subMsg}</div>
      ${totalWatched?`<div class="poster-grid pg-miplan">${watchedFilms}</div>`:''}
    </div>`;
  }

  // ── BEFORE ─────────────────────────────────────────────────
  if(ph.phase==='before'){
    const label=ph.daysDiff===1?t('misc_manana'):`${t('misc_in')} ${ph.daysDiff} ${t('misc_days')}`;
    const prios=[...prioritized]
      .map(prioTitle=>{
        const f=FILMS.filter(fi=>fi.title===prioTitle&&!screeningPassed(fi))
          .sort((a,b)=>a.day_order-b.day_order||toMin(a.time)-toMin(b.time))[0];
        return f?{t:prioTitle,f}:null;
      })
      .filter(Boolean)
      .slice(0,1);
    const prioHtml=prios.map(({t:title,f})=>{
      const{displayTitle:dt}=parseProgramTitle(title);
      const src=getFilmPoster(f)||'';
      return`<div class="ctx-prio-chip">
        ${src?`<img class="ctx-prio-thumb" src="${src}" onerror="this.remove()" alt="" loading="lazy">`:
              `<div class="ctx-prio-thumb"></div>`}
        <div style="flex:1;min-width:0">
          <div class="ctx-prio-name">${dt}</div>
          <div class="ctx-prio-when">${_dayAbbr(f.day)} · ${f.time}</div>
        </div>
      </div>`;
    }).join('');
    // Countdown line — discreta, sin repetir info del topbar
    const _daysLeft=ph.daysDiff||0;
    const _countdownLabel=_daysLeft<=0?t('plan_fest_hoy'):_daysLeft===1?t('plan_fest_manana'):`${t('plan_fest_empieza')} ${_daysLeft} ${t('misc_days')}`;
    return`<div style="text-align:center;padding:var(--sp-2) 0 var(--sp-1);color:var(--gray2);font-size:var(--t-sm)">${_countdownLabel}</div>
      ${prioHtml?`<div class="ctx-prio-row" style="margin-bottom:var(--sp-3)">${prioHtml}</div>`:''}`;
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
      ?`<span class="ctx-next-badge ending">${t('plan_termina_en')} ${_leftMin} min</span>`
      :`<span class="ctx-next-badge">${t('plan_en_min')} ${minsUntil} min</span>`;
    const _filmObj=FILMS.find(f=>f.title===next._title);
    const _isEvent=_filmObj&&_filmObj.type==='event';
    const eyebrowLabel=isNow?t('label_en_curso'):(_isEvent?t('misc_prox_evento'):t('misc_prox_funcion'));

    // ── Delay controls — solo cuando está en curso ──
    let delayHtml='';
    let warnHtml='';
    if(isNow){
      const safeT=(next._title||'').replace(/'/g,"&#39;");
      const _dk=_delayKey(next);
      const delayMins=filmDelays[_dk]||0;
      if(delayMins>0){
        delayHtml=`<div class="delay-row">
          <span class="delay-lbl">+${delayMins} min</span>
          ${[10,15,20,30].map(m=>`<button class="delay-btn" data-action="setDelay" data-title="${safeT}" data-day="${next.day}" data-time="${next.time}" data-mins="${m}" title="+${m} min">+${m}</button>`).join('')}
          <button class="delay-clear" data-action="undoDelay" data-title="${safeT}" data-day="${next.day}" data-time="${next.time}" title="${t('aria_deshacer')}">${ICONS.undo}</button>
          <button class="delay-clear" data-action="clearDelay" data-title="${safeT}" data-day="${next.day}" data-time="${next.time}" title="Quitar retraso">${ICONS.x}</button>
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
          const nShort=nt.length>26?nt.slice(0,24)+'…':nt;
          if(margin<0){
            warnHtml=`<div class="delay-warn"><span class="delay-warn-ico">${ICONS.alert}</span><span>Con el retraso terminas ~${minToStr(effectiveEndMin)}. Solo quedan <b>${toMin(nextFilm.time)-effectiveEndMin} min</b> antes de <b>${nShort}</b>${travel>0?` (${travel} min de viaje)`:''}</span></div>`;
          }else if(margin<15){
            warnHtml=`<div class="delay-warn warn-amber"><span class="delay-warn-ico">${ICONS.alert}</span><span>Terminas ~${minToStr(effectiveEndMin)}. Margen ajustado: <b>${margin} min</b> hasta <b>${nShort}</b>.</span></div>`;
          }
        }
      }else{
        delayHtml=`<div class="delay-row">
          <span class="delay-lbl">${t('plan_retraso')}</span>
          ${[10,15,20,30].map(m=>`<button class="delay-btn" data-action="setDelay" data-title="${safeT}" data-day="${next.day}" data-time="${next.time}" data-mins="${m}" title="Reportar +${m} min">+${m}</button>`).join('')}
        </div>`;
      }
    }

    return`<div class="ctx-header">
      <div class="ctx-eyebrow">
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
        ${eyebrowLabel}
      </div>
      <div class="ctx-next-row js-open-pel" data-title="${next._title||''}" style="cursor:pointer">
        ${src
          ?`<img class="ctx-next-poster" src="${src}" data-title="${(next._title||'').replace(/"/g,'&quot;')}" onerror="_posterErr(this)" alt="" loading="lazy">`
          :_isEvent
            ?makeEventPoster(state,next._title,next.duration,_filmObj?.event_kind).replace('<svg','<svg class="bg-surf-3 poster-sm ctx-next-poster"')
            :`<div class="ctx-next-poster"></div>`}
        <div style="flex:1;min-width:0">
          <div class="ctx-next-title-row">
            <div class="ctx-next-title">${dt}</div>
            ${badge}
          </div>
          <div class="ctx-next-detail">${next.time} · ${vc.short}</div>
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
      const dur=parseInt(gapSuggestion.duration)||DEFAULT_DURATION_MIN;
      const safeT=gapSuggestion.title.replace(/'/g,"&#39;");
      return`<div class="txt-gray-sm-mb1">${t('plan_cabe_hueco')}</div>
        <div class="ctx-suggest-card js-open-pel" data-title="${f.title}" style="cursor:pointer">
          <div class="ctx-suggest-badge">${gapSuggestion.time}<br>${dur}m</div>
          <div class="ctx-suggest-info">
            <div class="ctx-suggest-title">${dt.length>26?dt.slice(0,24)+'…':dt}</div>
            <div class="ctx-suggest-venue">${vc2.short}</div>
          </div>
        </div>`;
    })():`<div class="txt-caption-gray">${t('plan_sin_actividades')}</div>`;
    return`<div class="ctx-header">
      <div class="txt-green70 ctx-eyebrow">
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="var(--green)" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
        ${t('misc_tiempo_libre')}
      </div>
      <div class="ctx-main-title">${gapLabel} ${t('misc_hasta_sig')}</div>
      <div class="txt-gray-sm-vm">${fromStr} → ${toStr} · ${(()=>{const{displayTitle:dt}=parseProgramTitle(next._title||'');return dt.length>28?dt.slice(0,26)+'…':dt;})()}</div>
      <div class="mt-3">${suggest}</div>
    </div>`;
  }

  // ── EVENING ─────────────────────────────────────────────────
  if(ph.phase==='evening'){
    const{todayScreenings}=ph;
    const pendingRating=todayScreenings.filter(s=>watched.has(s._title)&&!filmRatings[s._title]);
    const rated=todayScreenings.filter(s=>watched.has(s._title)&&filmRatings[s._title]);
    const total=todayScreenings.filter(s=>watched.has(s._title)).length;
    if(!total) return '';
    // Máximo 2 posters visibles — el resto se expande con "Ver todo (N)"
    // Consistente con el sistema: link-gray-xs, misc_ver_todo existente
    const MAX_VISIBLE=2;
    const allWatched=todayScreenings.filter(s=>watched.has(s._title));
    const mkChip=s=>{
      const{displayTitle:dt}=parseProgramTitle(s._title||'');
      const f=FILMS.find(fi=>fi.title===s._title);
      const r=filmRatings[s._title];
      const safeT=(s._title||'').replace(/'/g,"&#39;");
      const stars=r?starsText(r):'';
      return`<div class="prio-chip-wrap js-open-pel" data-title="${f.title}">
        ${getFilmPoster(f)?_posterThumb(f,'prio-chip-poster'):`<div class="prio-chip-ph">🎬</div>`}
        ${r?`<div class="prio-overlay-label">${stars}</div>`:''}
        ${!r?`<div class="prio-overlay-center">
          <button class="prio-star-pill" data-action="openPostViewRating" data-title="${safeT}" data-day="${s.day||''}" data-time="${s.time||''}" data-venue="${(s.venue||'').replace(/"/g,'&quot;')}" data-duration="${s.duration||''}" data-stop="1">★</button>
        </div>`:''}
      </div>`;
    };
    const visible=allWatched.slice(0,MAX_VISIBLE).map(mkChip).join('');
    const hidden=allWatched.length>MAX_VISIBLE
      ?`<span id="eve-films-extra" style="display:none">${allWatched.slice(MAX_VISIBLE).map(mkChip).join('')}</span>`
      :'';
    const verTodas=allWatched.length>MAX_VISIBLE
      ?`<div class="sim-hdr-pad"><button class="link-gray-xs" data-action="toggleEveningFilms">${t('misc_ver_todo')} (${allWatched.length})</button></div>`
      :'';
    const dayName=(dayLabel(todayScreenings[0]?.day)||'').split(' ')[0]||t('bar_hoy');
    return`<div class="ctx-header">
      <div class="ctx-eyebrow" style="color:var(--gray)">
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path stroke-linecap="round" stroke-linejoin="round" d="M21.752 15.002A9.718 9.718 0 0118 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 003 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 009.002-5.998z"/></svg>
        ${t('plan_tu_dia_en',{dia:dayName.toLowerCase()})} ${(FESTIVAL_CONFIG[_activeFestId]||{}).name||''}
      </div>
      <div class="ctx-main-title">${total} ${t('misc_pelicula')}${total!==1?'s':''} ${total===1?t('plan_vista_hoy'):t('plan_vistas_hoy')}</div>
      ${pendingRating.length?`<div class="mb-3 ctx-sub">${pendingRating.length===1?t('plan_una_pendiente'):t('empty_calificar')}</div>`:`<div class="mb-3"></div>`}
      <div class="hscroll-strip">${filmRows}</div>
    </div>`;
  }

  return '';
}

export function renderPrioStrip(state, opts={}){
  const {FILMS, PRIO_LIMIT, prioritized} = state.snapshot();
  if(!prioritized.size) return '';
  const mode = opts.mode || 'intent';          // 'intent' (Estado 1/3) | 'resolved' (Estado 2)
  const included = opts.included;              // Set<title> de funciones en el plan (mode resolved)
  // Chip individual. rm: botón quitar (solo intent, no en .past). dim: opacity .4
  // (grupo "No entró"). grayTitle: título en var(--gray) (grupo "Entró").
  const _chip=(title,{rm=false,dim=false,grayTitle=false}={})=>{
    const f=FILMS.find(fi=>fi.title===title);
    const p=getFilmPoster(f);
    const img=p?_posterThumb(f,'prio-chip-poster'):`<div class="prio-chip-ph">${ICONS.star}</div>`;
    const{displayTitle,progSuffix}=parseProgramTitle(title);
    const short=displayTitle.length>24?displayTitle.slice(0,22)+'…':displayTitle;
    const allPast=!festivalEnded()&&!FILMS.some(f=>f.title===title&&!screeningPassed(f));
    const safeT=title.replace(/"/g,'&quot;');
    const rmBtn=(rm&&!allPast)?`<button class="prio-chip-rm" data-title="${safeT}" data-action="togglePriority" data-stop="1" title="${t('aria_quitar_prio')}">${ICONS.x}</button>`:'';
    const pastLbl=allPast?`<div class="prio-chip-past-lbl">${t('prio_past')}</div>`:'';
    const titleStyle=grayTitle?' style="color:var(--gray)"':'';
    return`<div class="prio-chip${allPast?' past':''}"${dim?' style="opacity:.4"':''}>
      ${img}${rmBtn}${pastLbl}
      <div class="prio-chip-title"${titleStyle}>${short}${progSuffix?`<span class="poster-label-amber">${progSuffix}</span>`:''}</div>
    </div>`;
  };
  // ── Estado 2: agrupado en "Entró" / "No entró" (sin overlays en el póster) ──
  if(mode==='resolved'){
    const list=[...prioritized];
    const inT=list.filter(x=>included&&included.has(x));
    const outT=list.filter(x=>!(included&&included.has(x)));
    let body='';
    if(inT.length) body+=`<div class="group-label ok">${ICONS.checkCircle} ${t('prio_in')}</div><div class="prio-strip-row">${inT.map(x=>_chip(x,{grayTitle:true})).join('')}</div>`;
    if(inT.length&&outT.length) body+=`<div class="hr-bdr"></div>`;
    if(outT.length) body+=`<div class="group-label fail">${ICONS.x} ${t('prio_out')}</div><div class="prio-strip-row">${outT.map(x=>_chip(x,{dim:true})).join('')}</div>`;
    return`<div class="prio-strip">
      <div class="sec-hdr">${ICONS.star} ${t('lbl_prioridades')}</div>
      ${body}
    </div>`;
  }
  // ── Estado 1 / 3: intención (chips con botón quitar) ──
  const chips=[...prioritized].map(x=>_chip(x,{rm:true})).join('');
  return`<div class="prio-strip">
    <div class="sec-hdr">${ICONS.star} ${t('lbl_prioridades')} <span class="ml-1 count-badge cb-amber">${prioritized.size}/${PRIO_LIMIT}</span></div>
    <div class="prio-strip-row">${chips}</div>
  </div>`;
}

export function renderFilmListHTML(state){
  const {FILMS, FESTIVAL_DATES, filmRatings, PRIO_LIMIT, prioritized, savedAgenda, watched, watchlist} = state.snapshot();
  const prioList=[...prioritized].filter(titleStr=>!watched.has(titleStr));
  const nonPrioList=[...watchlist].filter(titleStr=>!watched.has(titleStr)&&!prioritized.has(titleStr));
  const watchedList=[...watched];

  if(!prioList.length&&!nonPrioList.length&&!watchedList.length){
    return emptyStateHero(ICONS.heart,t('empty_lo_que_agg'),t('empty_intereses_2'),t('plan_ir_programa'),'mnav-cartelera');
  }

  // ── Próxima función futura de un film ──────────────────────────────────
  function _nextScreening(title){
    const future=FILMS.filter(f=>f.title===title&&!screeningPassed(f))
      .sort((a,b)=>{ const d=(a.day_order||0)-(b.day_order||0); return d||toMin(a.time)-toMin(b.time); });
    return future[0]||null;
  }

  // ── Label de día relativo: hoy→solo hora, mañana→MAÑANA, otro→label ──
  function _relDayLabel(screening){
    const todayStr=simTodayStr();
    const todayKey=DAY_KEYS.find(d=>FESTIVAL_DATES[d]===todayStr);
    const tomorrowIdx=todayKey?DAY_KEYS.indexOf(todayKey)+1:-1;
    const tomorrowKey=tomorrowIdx>0&&tomorrowIdx<DAY_KEYS.length?DAY_KEYS[tomorrowIdx]:null;
    if(screening.day===todayKey) return screening.time+(screening.venue?' · '+screening.venue:'');
    if(tomorrowKey&&screening.day===tomorrowKey) return t('bar_manana').toUpperCase()+' · '+screening.time+(screening.venue?' · '+screening.venue:'');
    return dayLabel(screening.day)+' · '+screening.time+(screening.venue?' · '+screening.venue:'');
  }

  // ── Detecta conflicto con agenda guardada ──────────────────────────────
  function _hasConflict(title){
    if(!savedAgenda?.schedule?.length) return null;
    const next=_nextScreening(title);
    if(!next) return null;
    for(const s of savedAgenda.schedule){
      const sf=FILMS.find(f=>f.title===s.filmTitle&&f.day===s.day&&f.time===s.time);
      if(sf&&screensConflict(next,sf)){
        const{displayTitle}=parseProgramTitle(sf.title);
        return displayTitle;
      }
    }
    return null;
  }

  // ── Item de lista ──────────────────────────────────────────────────────
  function _mkItem(title){
    const f=FILMS.find(fi=>fi.title===title);
    const{displayTitle,progSuffix}=parseProgramTitle(title);
    const isPrio=prioritized.has(title);
    const next=_nextScreening(title);
    const conflict=_hasConflict(title);

    const posterHtml=_posterThumb(f,'int-item-poster');
    // p8: jerarquía aprobada (mismo orden que Programa lista) — Título / Días
    // disponibles (ámbar) / Venue·Duración (gris) / Sección+flags (blanco 60%).
    const future=FILMS.filter(fi=>fi.title===title&&!screeningPassed(fi)); // días disponibles = futuras
    const daysHtml=_dayChips(future);                                       // ámbar "THU 4 · FRI 5"
    const venueStr=next?vcfg(next.venue).short:'';                          // venue de la próxima función
    const durStr=durFmt(f?.duration);                                       // solo f.duration
    const conflictHtml=conflict
      ?`<div class="int-item-conflict">
          <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"/></svg>
          ${t('conflict_con')} ${conflict}
        </div>`
      :'';
    return`<div class="int-item js-open-pel${!next?' gone':''}" style="${!next&&!festivalEnded()?'opacity:.35':''}" data-title="${title}">
      ${posterHtml}
      <div class="int-item-info">
        <div class="int-item-title">${displayTitle}${progSuffix?` <span class="txt-amber-xs">${progSuffix}</span>`:''}</div>
        ${next?`<div class="int-item-days">${daysHtml}</div>`:`<div class="int-item-gone">${t('empty_sin_funciones')}</div>`}
        <div class="int-item-meta">${venueStr}${venueStr&&durStr?' · ':''}${durStr}</div>
        <div class="int-item-sec">${_secLabelFull(f?.section||'')}</div>
        ${conflictHtml}
      </div>
      <div class="int-item-actions">
        <button class="int-prio-btn${isPrio?' on':''}" data-title="${title}" data-action="togglePriority" data-stop="1" aria-label="${t('aria_priorizar')}">★</button>
      </div>
    </div>`;
  }

  // ── Item simplificado para Ya vistas ─────────────────────────────────
  function _mkItemWatched(title){
    const f=FILMS.find(fi=>fi.title===title);
    const{displayTitle,progSuffix}=parseProgramTitle(title);

    const posterHtml=_posterThumb(f,'int-item-poster');
    const rating=filmRatings[title]||0;
    const stars=rating>0
      ?'★'.repeat(Math.floor(rating))+(rating%1?'½':'')
      :'';
    const ratingHtml=stars
      ?`<div class="int-item-rating">${stars}</div>`
      :`<div class="int-item-rating-empty" data-title="${title}" data-action="openRatingSheet" data-stop="1">${t('cta_calificar')} →</div>`;
    return`<div class="int-item js-open-pel" data-title="${title}">
      ${posterHtml}
      <div class="int-item-info">
        <div class="int-item-title">${displayTitle}${progSuffix?` <span class="txt-amber-xs">${progSuffix}</span>`:''}</div>
        <div class="int-item-sec">${_secLabelFull(f?.section||'')}</div>
        ${ratingHtml}
      </div>
      <div class="int-item-actions">
        <button class="int-seen-btn on" data-title="${title}" data-action="toggleWatched" aria-label="${t('aria_quitar_vista')}">✓</button>
      </div>
    </div>`;
  }

  // ── Ordenar cronológicamente: primero por próxima función (futuras antes que pasadas),
  // luego por day_order + time dentro del mismo grupo ────────────────────────────────
  function _chronoSort(titles){
    return [...titles].sort((a,b)=>{
      const nA=_nextScreening(a), nB=_nextScreening(b);
      // Títulos sin función futura van al final
      if(nA&&!nB) return -1;
      if(!nA&&nB) return 1;
      if(!nA&&!nB) return 0;
      // Ambos tienen función futura: ordenar por day_order luego por hora
      const dayDiff=(nA.day_order||0)-(nB.day_order||0);
      if(dayDiff!==0) return dayDiff;
      return toMin(nA.time)-toMin(nB.time);
    });
  }

  // ── Render secciones ───────────────────────────────────────────────────
  let html='';

  if(prioList.length){
    html+=`<div class="int-section-hdr">
      <span class="int-section-hdr-ico">${ICONS.star}</span>
      <span class="int-section-hdr-lbl">${t('lbl_prioridades')}</span>
      <span class="count-badge cb-amber">${prioList.length}/${PRIO_LIMIT}</span>
    </div>
    <div>${_chronoSort(prioList).map(_mkItem).join('')}</div>`;
  }

  if(nonPrioList.length){
    if(prioList.length) html+=`<div class="hr-bdr"></div>`;
    html+=`<div class="int-section-hdr">
      <span class="int-section-hdr-ico">${ICONS.heart}</span>
      <span class="int-section-hdr-lbl">${t('lbl_intereses')}</span>
      <span class="count-badge cb-neutral">${nonPrioList.length}</span>
    </div>
    <div>${_chronoSort(nonPrioList).map(_mkItem).join('')}</div>`;
  }

  if(watchedList.length){
    if(prioList.length||nonPrioList.length) html+=`<div class="hr-bdr"></div>`;
    // Ya vistas: ordenar cronológicamente por la primera función del film
    const _sortedW=[...watchedList].sort((a,b)=>{
      const fA=FILMS.filter(f=>f.title===a).sort((x,y)=>(x.day_order||0)-(y.day_order||0)||toMin(x.time)-toMin(y.time))[0];
      const fB=FILMS.filter(f=>f.title===b).sort((x,y)=>(x.day_order||0)-(y.day_order||0)||toMin(x.time)-toMin(y.time))[0];
      if(!fA&&!fB) return 0;
      if(fA&&!fB) return -1;
      if(!fA&&fB) return 1;
      const dayDiff=(fA.day_order||0)-(fB.day_order||0);
      return dayDiff||toMin(fA.time)-toMin(fB.time);
    });
    html+=`<div class="int-section-hdr">
      <span class="int-section-hdr-ico">${ICONS.check}</span>
      <span class="int-section-hdr-lbl">${t('misc_ya_vistas')}</span>
      <span class="count-badge cb-neutral">${watchedList.length}</span>
    </div>
    <div>${_sortedW.map(_mkItemWatched).join('')}</div>`;
  }

  return html;
}

export function renderSavedAgendaHTML(state){
  // ⚠️ FIX CRÍTICO — NO REMOVER (Apr 2026)
  // try/catch permanente: un error en renderMiPlanCalendar u otras subfunciones
  // causaba que Mi Agenda quedara en blanco sin ningún mensaje de error visible.
  // Este wrapper aísla el fallo y muestra el error en pantalla en lugar de silencio.
  try{ return _renderSavedAgendaHTML(state); }
  catch(err){
    /* renderSavedAgendaHTML error — silent in production */
    return`<div class="error-box">
      <strong>${t('error_cargar_miplan')}</strong><br>
      <code class="txt-xs-dim">${err.message}</code>
    </div>`;
  }
}

export function _renderSavedAgendaHTML(state){
  const {savedAgenda, FILMS, watched, _activeFestId, FESTIVAL_DATES} = state.snapshot();
  if(festivalEnded()){
    // Con películas vistas: poster grid via renderContextualHeader
    if(watched.size>0){
      const _eh=renderContextualHeader(state);
      return _eh?`<div class="saved-agenda">${_eh}</div>`:'';
    }
    // Sin películas vistas: empty state canónico
    const _festNameMp=(FESTIVAL_CONFIG[_activeFestId]||{}).name||'El festival';
    return emptyStateHero(ICONS.sparkles,`${_festNameMp} ${t('plan_fest_terminado')}`,t('empty_vistas'),t('plan_ir_programa'),'mnav-cartelera');
  }
  if(!savedAgenda||!savedAgenda.schedule.length) return emptyStateHero(ICONS.calendar,t('plan_tu_plan_empty'),t('empty_intereses'),t('cta_ir_planear'),'mnav-planner');
  const all=savedAgenda.schedule;
  const planTitles=new Set(all.map(s=>s._title));
  const archive=all.filter(s=>watched.has(s._title));
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

  const today=simTodayStr();
  const dayIdx=DAY_KEYS.findIndex(d=>FESTIVAL_DATES[d]===today);
  const currentDayNum=dayIdx>=0?dayIdx+1:null;
  const totalDays=Math.max(1,DAY_KEYS.length);
  const viewedCount=all.filter(s=>watched.has(s._title)).length;
  const progressPct=dayIdx>=0?Math.round((dayIdx/(totalDays-1))*100):0;
  const progressBar=currentDayNum?`<div class="row-sm festival-progress">
    <div style="flex:1">
      <div class="festival-progress-text"><span>${t('label_dia_prog')} <b>${currentDayNum}</b> ${t('label_de_dias')} ${totalDays}</span><span style="color:var(--amber);display:flex;align-items:center;gap:4px">${viewedCount} ${viewedCount===1?t('label_vista'):t('label_vistas')} ${ICONS.check}</span></div>
    </div>
  </div>`:'';

  const _ctxHeader=renderContextualHeader(state);
  const _nextStrip=''; // delay controls integrated into ctx-header
  const _unconfirmed=renderUnconfirmed(state,all);
  let html=`<div class="saved-agenda">
    ${_ctxHeader}
    ${progressBar}
`;

  // ── CTA B: post-eliminación (temporal, auto-dismiss 6s) ──
  if(_ctaRemovedVisible){
    html+=`<div class="cta-ctx cta-ctx-b" data-action="navTo" data-tab="mnav-planner">
      <div class="flex-center cta-ctx-ico">${ICONS.undo}</div>
      <div class="cta-ctx-body">
        <div class="cta-ctx-title cta-ctx-title-b">${t('plan_otra_cosa')}</div>
        <div class="cta-ctx-sub">Hay sugerencias abajo que caben en ese hueco, o recalcula en Planear.</div>
      </div>
      <div class="cta-ctx-arr cta-ctx-arr-b">${ICONS.chevronR}</div>
    </div>`;
  }

    html+=renderMiPlanCalendar(state);

  if(archive.length||watchedOutsidePlan.length){
    const totalWatched=archive.length+watchedOutsidePlan.length;
    const archByDay={};
    archive.forEach(s=>{if(!archByDay[s.day])archByDay[s.day]=[];archByDay[s.day].push(s);});
    html+=`<div class="archive-toggle" data-action="toggleArchive">
      <span class="archive-toggle-lbl">${ICONS.checkCircle} ${t('plan_historial')}</span>
      <span class="row-sm"><span class="count-badge cb-neutral">${totalWatched}</span><span id="arch-arrow">${ICONS.chevronD}</span></span>
    </div>
    <div class="archive-body${archiveOpen?' open':''}" id="archive-body">
      ${archive.length?DAY_KEYS.filter(d=>archByDay[d]).map(day=>`
        <div class="saved-day-lbl">${dayChip(day)}</div>
        ${archByDay[day].map(s=>{
          const vc2=vcfg(s.venue),sl=sala(s.venue);
          const _af=FILMS.find(fi=>fi.title===s._title);
          const _aph=`<div class="js-open-pel" data-title="${(s._title||'').replace(/"/g,'&quot;')}" style="cursor:pointer">${_posterThumb(_af,'lb-poster')}</div>`;
          return`<div class="saved-item done">
            ${_aph}
            <div class="saved-time">${s.time}</div>
            <div class="saved-info">
              <div class="saved-title">${s._title}</div>
              <div class="saved-venue">${ICONS.pin} ${vc2.short}${sl?' · '+sl:''}</div>
            </div>
            <button class="saved-check done" data-title="${(s._title||'').replace(/"/g,'&quot;')}" data-action="toggleWatched">${ICONS.check+' '+t('cta_vista')}</button>
          </div>`;
        }).join('')}`).join(''):''}
      ${watchedOutsidePlan.length?`
        <div class="archive-out-lbl">${t('plan_vistas_fuera')}</div>
        ${watchedOutsidePlan.map(f=>{
          const _ap=getFilmPoster(f);
          const _aphInner=_posterThumb(f,'lb-poster');
          const _aph=`<div class="js-open-pel" data-title="${f.title}" style="cursor:pointer">${_aphInner}</div>`;
          return`<div class="saved-item done">
            ${_aph}
            <div class="saved-time">${flagFmt(f.flags)||''}</div>
            <div class="saved-info">
              <div class="saved-title">${f.title}</div>
              <div class="saved-venue">${ICONS.clock} ${durFmt(f.duration)||'—'}</div>
            </div>
            <button class="saved-check done" data-title="${(f.title||'').replace(/"/g,'&quot;')}" data-action="toggleWatched" >${ICONS.check+' '+t('cta_vista')}</button>
          </div>`;
        }).join('')}`:''}
    </div>`;
  }

  // Funciones sin confirmar — después del calendario (tarea diferible)
  if(_unconfirmed) html+=_unconfirmed;

  // Sugerencias solo durante el festival
  if(!festivalEnded()){
  const suggsByDay=getSuggestions();
  const suggDays=DAY_KEYS.filter(d=>suggsByDay[d]&&suggsByDay[d].length>0);
  html+=`<div class="suggestion-wrap">
    <div class="mb-2 sec-hdr">${ICONS.sparkles} ${t('misc_sugerencias')}</div>`;
  if(suggDays.length){
    suggDays.forEach(day=>{
      html+=`<div class="suggestion-day-lbl">${dayChip(day)}</div>`;
      html+=suggsByDay[day].slice(0,4).map(f=>{
        const vc2=vcfg(f.venue),sl=sala(f.venue);
        const _sp=getFilmPoster(f);
        const _sph=_posterThumb(f,'lb-poster');
        return`<div class="suggestion-item js-open-pel" data-title="${f.title}">
          ${_sph}
          <div class="suggestion-time">${f.time}</div>
          <div class="suggestion-info">
            <div class="suggestion-title">${(()=>{const{displayTitle:_dt}=parseProgramTitle(f.title);return _dt;})()}</div>
            <div class="suggestion-sec">${_secLabelFull(f.section||'')}</div>
            <div class="suggestion-meta">${durFmt(f.duration)}${vc2.short?' · '+vc2.short+(sl?' · '+sl:''):''}</div>
          </div>
          <button class="suggestion-add" data-action="addSuggestion" data-title="${f.title.replace(/"/g,'&quot;')}" data-day="${f.day}" data-time="${f.time}" data-stop="1" style="${f._isRestored?'border-color:var(--amber);color:var(--amber);background:var(--amber-10)':''}">
            ${f._isRestored?`${ICONS.undo} Restaurar`:`${ICONS.plus} ${t('misc_anadir')}`}
          </button>
        </div>`;
      }).join('');
    });
    html+='</div>'; // close suggestion-wrap content
  } else {
    html+=emptyState(ICONS.search,t('plan_cubierto'),t('plan_cubierto_sub'));
  }
  html+='</div>'; // close suggestion-wrap
  } // end !festivalEnded

  html+='</div>';
  return html;
}

export function renderAvBlocks(){
  const el=document.getElementById('av-blocks-list');
  if(!el) return;
  el.innerHTML=renderAvBlocksHTML(state);
}

// p8 (fix urgente): buildResultHTML reubicado desde view/components.js — usa
// mkAgendaRow (local) + helpers + domain, todos ya importados aquí; cero ciclos.
export function buildResultHTML(scenarios){
  if(!scenarios||!scenarios.length)
    return`<div class="ag-calc-prompt">${t('plan_sin_combos')} ${t('plan_anadir_titulos')}</div>`;
  const{currentIdx}=cachedResult;
  const sc=scenarios[currentIdx],n=scenarios.length;
  const pending=[...watchlist].filter(t=>!watched.has(t)&&FILMS.some(f=>f.title===t&&!screeningPassed(f)));
  const total=pending.length,ok=sc.schedule.length,bad=sc.excluded.length;
  const isOptimo=currentIdx===0;
  // Stale banner (movido aquí desde pre-cálculo): se calcula a partir de cachedResult._prioSnapshot vs prioritized actual.
  const _snap=cachedResult._prioSnapshot;
  const _stale=Array.isArray(_snap)&&(_snap.length!==prioritized.size||!_snap.every(x=>prioritized.has(x)));
  const _staleBanner=_stale
    ?`<div class="prio-stale">${ICONS.star} ${t('prio_stale_banner')}<button class="prio-stale-cta" data-action="runCalc">${t('prio_stale_cta')}</button></div>`
    :'';
  // Resumen de prioridades (post-cálculo): verde si todas entraron, ámbar si parciales.
  const _included=new Set(sc.schedule.map(s=>s._title));
  const _prioCnt=[...prioritized].filter(p=>_included.has(p)).length;
  const _prioLine=prioritized.size===0?''
    :_prioCnt===prioritized.size
      ?`<div class="plan-prio-ok">✓ ${t('plan_prio_todas')}</div>`
      :`<div class="plan-prio-partial">⚠ ${t('plan_prio_parcial',{n:_prioCnt,m:prioritized.size})}</div>`;

  // ── Header: Plan óptimo vs Variación ──
  const isCustom=sc._custom===true;
  const planLabel=isOptimo?t('plan_optimo'):isCustom?t('av_opcion_pers'):'';

  // Modelo de "plan único": sin dots ni navegación entre variaciones.
  // Si existen escenarios custom (forceInclude), `cachedResult.currentIdx` puede
  // apuntar a uno; rendereamos ese. La navegación entre múltiples scenarios la
  // sacamos junto con la Phase 3 del motor.
  const saveBtnHtml=`<button class="ag-save-btn" data-action="saveCurrentScenario">${ICONS.calendar} ${t('plan_usar_plan')}</button>`;
  let html=`${_staleBanner}<div class="ag-summary">
    <div class="ag-summary-title" style="font-size:var(--t-base);color:${isOptimo?'var(--white)':'var(--gray)'}">${planLabel} · ${ok} ${t('misc_pelicula')}${ok!==1?'s':''}</div>
    ${_prioLine}
    ${bad?`<div class="tags-row ag-summary-text"><span class="txt-gray2-sm">${bad} ${t('plan_excluidos')}</span></div>`:''}
    ${bad>0&&bad>=total?`<div class="ag-excl-note txt-gray2-sm">${t('plan_contexto_max')}</div>`:''}
    ${sc.incompatiblePriorities?(()=>{
      const pairs=sc.conflictingPriorityPairs||[];
      const pairMsg=pairs.length
        ?pairs.map(([a,b])=>{const{displayTitle:da}=parseProgramTitle(a);const{displayTitle:db}=parseProgramTitle(b);return`<span class="txt-white60">${da}</span> y <span class="txt-white60">${db}</span>`;}).join(', ')
        :`algunas de tus ${t('misc_prioridades')}`;
      return`<div class="ag-excl-incompat">${pairMsg} ${t('plan_solapan')} — revisá cuál querés priorizar.</div>`;
    })():''}
  </div>
`;

  // ── Film list by day ──
  // Day landmark: nombre completo lang-aware + stats (n films · total min)
  const _dowKeys=['day_dom','day_lun','day_mar','day_mie','day_jue','day_vie','day_sab'];
  const byDay={};
  sc.schedule.forEach(s=>{if(!byDay[s.day])byDay[s.day]=[];byDay[s.day].push(s);});
  DAY_KEYS.forEach(day=>{
    const films=byDay[day];if(!films||!films.length) return;
    const _isoDate=FESTIVAL_DATES[day]||day;
    const _d=new Date(_isoDate+'T12:00:00');
    const _dayName=t(_dowKeys[_d.getDay()]);
    const _dayNum=_d.getDate();
    const _totalMin=films.reduce((acc,f)=>acc+parseDur(f.duration),0);
    const _h=Math.floor(_totalMin/60), _m=_totalMin%60;
    const _totalStr=_h?(_m?`${_h}h ${_m}min`:`${_h}h`):`${_m}min`;
    const _filmsLbl=`${films.length} ${t('misc_pelicula')}${films.length!==1?'s':''}`;
    html+=`<div class="ag-day-label"><span class="ag-day-name">${_dayName} ${_dayNum}</span><span class="ag-day-stats">${_filmsLbl} · ${_totalStr}</span></div>`;
    films.forEach((s,i)=>{
      if(i>0){const warn=travelWarn(films[i-1],s);if(warn) html+=`<div class="ag-warn">${warn}</div>`;}
      html+=mkAgendaRow(s,'scenario');
    });
  });

  // ── Películas no incluidas — lista con razón + botón Incluir ────────
  if(sc.excluded.length){
    const _excItems=sc.excluded.map(excTitle=>{
      const t_=excTitle; // alias para no pisar t() i18n
      const{displayTitle:dt}=parseProgramTitle(excTitle);
      const f=FILMS.find(fi=>fi.title===excTitle);
      const poster=f?getFilmPoster(f):null;
      const secLabel=f?_secLabel(f.section||''):'';
      const safeT=excTitle.replace(/'/g,"&#39;");
      const posterHtml=_posterThumb(f,'int-item-poster');
      // Detectar razón usando screensConflict contra el schedule activo
      const screens=FILMS.filter(fi=>fi.title===excTitle&&!screeningPassed(fi)&&!isScreeningBlocked(fi));
      let reason='',canInclude=false;
      if(!screens.length){
        reason=`<div class="excl-reason">${t('empty_sin_funciones')}</div>`;
      } else {
        // Buscar conflicto con el schedule actual
        let conflictWith=null,conflictWhen=null;
        for(const s of screens){
          for(const c of sc.schedule){
            if(screensConflict(s,c)){
              const{displayTitle:ct}=parseProgramTitle(c._title||'');
              conflictWith=ct;
              const _ds=dayLabel(c.day)||c.day||'';
              conflictWhen=_ds+(c.time?' '+c.time:'');
              break;
            }
          }
          if(conflictWith) break;
        }
        if(conflictWith){
          reason=`<div class="excl-reason conflict">Choca con ${conflictWith}${conflictWhen?' · '+conflictWhen:''}</div>`;
          canInclude=true;
        } else if(screens.length){
          reason=`<div class="excl-reason">${t('plan_choca')}</div>`;
        } else {
          reason=`<div class="excl-reason">${t('empty_sin_funciones')}</div>`;
        }
      }
      const includeBtn=canInclude
        ?`<button class="excl-include-btn" data-action="forceInclude" data-title="${safeT}" data-stop="1">+ Incluir</button>`
        :'';
      const opacity=!screens.length?'opacity:.45;':'';
      return`<div class="int-item js-open-pel" style="${opacity}" data-title="${f.title}">
        ${posterHtml}
        <div class="int-item-info">
          <div class="int-item-title">${dt}</div>
          <div class="int-item-sec">${flagFmt(f?.flags)||''}${flagFmt(f?.flags)?' ':''} ${secLabel}</div>
          ${reason}
        </div>
        ${includeBtn}
      </div>`;
    }).join('');
    html+=`<div class="pad-flush ag-excl-block">
      <div class="pad-sm ag-excl-eyebrow">
        <span class="ag-excl-label">${t('plan_no_incluidas')}</span>
        <span class="count-badge cb-neutral">${sc.excluded.length}</span>
      </div>
      ${_excItems}
    </div>`;
  }

  // ── CTA al pie — patrón UX formulario largo ──
  html+=`<div class="mt-4 ag-summary">
    ${saveBtnHtml}
  </div>`;
  return html;
}

export function mkAgendaRow(s, mode='saved'){
  const title=s._title||'';
  const{displayTitle,progSuffix}=parseProgramTitle(title);
  const f=FILMS.find(fi=>fi.title===title);
  const _p=getFilmPoster(f);
  const _safePT=title.replace(/'/g,"\\'");
  const _phInner=_posterThumb(f,'lb-poster');
  const _ph=`<div class="js-open-pel" data-title="${title}" style="flex-shrink:0;cursor:pointer">${_phInner}</div>`;
  const vc2=vcfg(s.venue),sl=sala(s.venue);
  const safeT=(s._title||'').replace(/"/g,'&quot;');
  const isDone=watched.has(title);
  // altBadge ("X alt.") eliminado del template — rediseño visual: las
  // alternativas son un affordance de interacción (PR de editabilidad),
  // no info pasiva en la venue line.
  const filmKey=(s._title||'')+(s.day||'')+(s.time||'');
  const isExpanded=_expandedFilm===filmKey;
  const actionBtn=mode==='saved'
    ?`<button class="row-xs ag-fi-btn del" data-title="${safeT}" data-action="removeFromAgenda" data-stop="1">${ICONS.x} ${t('misc_quitar')}</button>`
    :`<button class="row-xs ag-fi-btn del" data-title="${safeT}" data-action="removeFilmFromScenario">${ICONS.x} ${t('misc_quitar')}</button>`;
  const switchBtn=mode==='saved'&&!isDone
    ?`<button class="film-switch${isExpanded?' open':''}" data-action="toggleFilmAlternatives" data-key="${filmKey}" data-title="${safeT}" data-day="${s.day||''}" data-time="${s.time||''}" data-stop="1">Cambiar</button>`
    :'';
  const altsHtml=isExpanded&&mode==='saved'?renderFilmAlternatives(state,title,s.day,s.time):'';
  const _progBtn=(()=>{const _mf=f;if(!_mf||!_mf.is_cortos||!_mf.film_list||!_mf.film_list.length)return'';return`<button class="row-xs mplan-prog-toggle" data-action="toggleMplanProg">${ICONS.chevronR} ${t('label_programa')}</button>`;})();
  const _progList=(()=>{const _mf=f;if(!_mf||!_mf.is_cortos||!_mf.film_list||!_mf.film_list.length)return'';return`<div class="mplan-prog-list">${_mf.film_list.map((item,n)=>_mkCortoItemHtml(item,n,{section:_mf.section||''})).join('')}</div>`;})();
  return`<div class="saved-item${isDone?' done':''}">
    ${_ph}
    <div class="saved-time">${s.time}</div>
    <div class="saved-info">
      <div class="saved-title">${displayTitle}</div>${progSuffix?`<div class="film-sub-label">${progSuffix}</div>`:''}
      <div class="saved-venue">${ICONS.pin} ${vc2.short}${sl?' · '+sl:''}${s.duration?' · '+durFmt(s.duration):''}</div>
      ${_progBtn}
    </div>
    ${mode==='saved'?`<button class="row-xs saved-check${isDone?' done':''}" data-title="${safeT}" data-day="${s.day||''}" data-time="${s.time||''}" data-venue="${(s.venue||'').replace(/"/g,'&quot;')}" data-dur="${s.duration||''}" data-action="${isDone?'toggleWatched':'markWatchedFromPlan'}">${ICONS.check+' '+t('cta_vista')}</button>`:''}
  </div>${_progList}${altsHtml?`<div class="film-alts">${altsHtml}</div>`:''}`;
}

export function updateCardState(title){
  const inWL=watchlist.has(title),inW=watched.has(title),inPrio=prioritized.has(title);
  // .card (legacy) + .poster-card (grid) + .poster-wl-dot (grid heart button)
  document.querySelectorAll(`.poster-wl-dot`).forEach(btn=>{
    if(btn.closest('[data-title="'+CSS.escape(title)+'"]')){
      btn.innerHTML=inWL?ICONS.heartFill:ICONS.heart;
      btn.classList.toggle('wl-on',inWL);
    }
  });
  document.querySelectorAll(`.card[data-title="${CSS.escape(title)}"],.poster-card[data-title="${CSS.escape(title)}"]`).forEach(card=>{
    card.classList.toggle('in-wl',inWL&&!inW);
    card.classList.toggle('in-watched',inW&&!festivalEnded());
    const wlBtn=card.querySelector('.wl-btn');
    const wBtn=card.querySelector('.w-btn');
    const prioBtn=card.querySelector('.prio-btn');
    if(wlBtn){wlBtn.innerHTML=inWL?ICONS.heartFill:ICONS.heart;wlBtn.classList.toggle('wl-on',inWL);wlBtn.title=inWL?t('plan_quitar_intereses'):t('cta_anadir');}
    if(wBtn){wBtn.classList.toggle('w-on',inW);wBtn.title=inW?t('aria_marcar_pendiente'):t('aria_marcar_vista');}
    if(prioBtn){prioBtn.classList.toggle('prio-on',inPrio);prioBtn.title=inPrio?t('plan_quitar_prioridad'):t('cta_priorizar');}
  });
}

export function updateHorarioPrioBtn(title){
  const inPrio=prioritized.has(title);
  document.querySelectorAll('.horario-prio-btn[data-title="'+CSS.escape(title)+'"]').forEach(btn=>{
    btn.className='card-strip-btn horario-prio-btn'+(inPrio?' prio-on':'');
    btn.innerHTML=(inPrio?ICONS.starFill:ICONS.star)+' Prio.';
  });
}

export function getSuggestions(){
  if(!savedAgenda||!savedAgenda.schedule.length) return{};
  const saved=savedAgenda.schedule.filter(s=>!screeningPassed(s));
  if(!saved.length) return{};

  const savedTitles=new Set(saved.map(s=>s._title));
  const byDay={};

  // Excluir siempre: ya en agenda o ya vistas
  const hardExclude=new Set([...savedTitles,...watched]);
  // Para descubrimiento (Bloque 1): también excluir watchlist (ya las conoces)
  const seenDiscover=new Set([...hardExclude,...watchlist]);
  // Para recuperación (Bloque 2): solo excluir hardExclude
  const seenRecovery=new Set([...hardExclude]);

  // ── Slots reservados: todas las películas recientemente quitadas ──
  // Solo muestra "← Restaurar" si el slot original está libre (sin conflicto)
  // Si el slot está ocupado, la película cae a Bloque 2 para buscar slot alternativo
  const currentSaved=savedAgenda?savedAgenda.schedule:[];
  lastRemovedSlots.forEach(rs=>{
    if(savedTitles.has(rs._title)||screeningPassed(rs)) return;
    const slotFree=!currentSaved.some(s=>screensConflict(s,rs));
    if(!slotFree) return; // slot ocupado — cae a Bloque 2
    const day=rs.day;
    if(!byDay[day]) byDay[day]=[];
    byDay[day].push({...rs,gapCtx:'Restaurar al mismo horario',_isRestored:true});
    hardExclude.add(rs._title);
    seenDiscover.add(rs._title);
    seenRecovery.add(rs._title);
  });

  DAY_KEYS.forEach(day=>{
    const dayItems=saved.filter(s=>s.day===day).sort((a,b)=>toMin(a.time)-toMin(b.time));

    // Calcular huecos del día
    const slots=[];
    if(dayItems.length===0){
      // Día completamente libre — cubre hasta la 1am
      slots.push({start:0,end:25*60,ctx:t('plan_dia_libre')});
    } else {
      // Antes de la primera
      if(toMin(dayItems[0].time)>60)
        slots.push({start:0,end:toMin(dayItems[0].time)-FESTIVAL_BUFFER,ctx:`Antes de ${(dayItems[0]._title||'').split(' ').slice(0,3).join(' ')}…`});
      // Entre funciones — cualquier hueco positivo (el chequeo fStart/fEnd filtra lo imposible)
      for(let i=0;i<dayItems.length-1;i++){
        const a=dayItems[i],b=dayItems[i+1];
        const aEnd=toMin(a.time)+parseDur(a.duration)+FESTIVAL_BUFFER;
        const bStart=toMin(b.time)-FESTIVAL_BUFFER;
        if(bStart>aEnd)
          slots.push({start:aEnd,end:bStart,ctx:`Entre ${(a._title||'').split(' ').slice(0,3).join(' ')}… y ${(b._title||'').split(' ').slice(0,3).join(' ')}…`});
      }
      // Después de la última — siempre se crea, extiende hasta la 1am
      // Bug fix: el if(lastEnd<22*60) cortaba noches con película tardía (ej: 20:00+90min=22:10 → sin slot)
      const last=dayItems[dayItems.length-1];
      const lastEnd=toMin(last.time)+parseDur(last.duration)+FESTIVAL_BUFFER;
      slots.push({start:lastEnd,end:25*60,ctx:`Después de ${(last._title||'').split(' ').slice(0,3).join(' ')}…`});
    }

    // Bloque 1 — Descubrimiento: películas del festival que quepan en huecos
    // Usa screensConflict — mismo criterio que el algoritmo, incluye travel time entre venues
    if(slots.length){
      FILMS.forEach(f=>{
        if(seenDiscover.has(f.title)||screeningPassed(f)||f.day!==day||isScreeningBlocked(f)) return;
        const fStart=toMin(f.time),fEnd=fStart+parseDur(f.duration);
        // Verificar que hay un slot de tiempo (check rápido)
        const slot=slots.find(sl=>fStart>=sl.start&&fEnd<=sl.end&&fEnd-fStart>=20);
        if(!slot) return;
        // Verificar que no conflictúa con ningún item del plan activo (incluye travel time)
        const noConflict=!saved.some(s=>screensConflict(s,f));
        if(noConflict){
          seenDiscover.add(f.title);seenRecovery.add(f.title);
          if(!byDay[day]) byDay[day]=[];
          byDay[day].push({...f,gapCtx:slot.ctx});
        }
      });
    }

    // Bloque 2 — Recuperación: watchlist no en agenda
    // Usa screensConflict (±10 min) — mismo criterio que el algoritmo de planificación
    // Solo aparece si genuinamente cabe sin conflicto en el plan actual
    [...watchlist].filter(wlTitle=>!seenRecovery.has(wlTitle)).forEach(wlTitle=>{
      FILMS.filter(f=>f.title===wlTitle&&f.day===day&&!screeningPassed(f)&&!isScreeningBlocked(f)).forEach(f=>{
        if(seenRecovery.has(f.title)) return;
        const noConflict=!saved.some(s=>screensConflict(s,f));
        if(noConflict){
          seenRecovery.add(f.title);seenDiscover.add(f.title);
          if(!byDay[day]) byDay[day]=[];
          byDay[day].push({...f,gapCtx:t('misc_sugerencias_wl'),_isFromWL:true});
        }
      });
    });
  });
  // ── Ordenar cronológicamente dentro de cada día ──
  Object.keys(byDay).forEach(d=>{
    byDay[d].sort((a,b)=>{
      // 1. Restaurar siempre primero
      if(a._isRestored!==b._isRestored) return a._isRestored?-1:1;
      // 2. Watchlist antes que descubrimiento
      if(a._isFromWL!==b._isFromWL) return a._isFromWL?-1:1;
      // 3. Cronológico
      return toMin(a.time)-toMin(b.time);
    });
  });
  return byDay;
}

export function _delayKey(s){return(s._title||s.title||'')+'|'+(s.day||'')+'|'+(s.time||'');}

export function _fixStickyOffset(){
  const tb=document.querySelector('.topbar');
  if(!tb) return;
  const isMobile=window.innerWidth<768;
  const tbH=Math.ceil(tb.getBoundingClientRect().height)||(isMobile?80:86);
  const navH=44;
  const modeH=38;
  const r=document.documentElement.style;
  if(isMobile){
    // Mobile: topbar is the single sticky container (contains hdr-programa + hdr-ag).
    // tbH now includes the full chrome height — use it for --sticky-top-lista.
    r.setProperty('--sticky-top-carta',tbH+'px'); // kept for desktop-compat
    r.setProperty('--sticky-top-lista',tbH+'px');
    r.setProperty('--sticky-top-chips',tbH+'px');
    // iOS non-scrollable page fix: cuando el contenido es corto (ej. Leviza "Hoy": 5 films),
    // la página no tiene scroll y iOS coloca position:fixed;bottom:0 de forma incorrecta.
    // Garantizar que #grid siempre sea al menos tan alto como el viewport restante (+ 1px).
    r.setProperty('--min-content-h',(window.innerHeight-tbH+1)+'px');
  } else {
    r.setProperty('--tb-no-nav',tbH+'px');
    r.setProperty('--tb-total',(tbH+navH)+'px');
    r.setProperty('--sticky-top-carta',(tbH+navH)+'px');
    r.setProperty('--sticky-top-modebar',(tbH+navH+modeH)+'px');
    const hdrH=document.getElementById('hdr-programa')?.offsetHeight||(tbH+navH);
    r.setProperty('--sticky-top-chips',hdrH+'px');
  }
}

export function _scrollMiPlanToNow(){
  requestAnimationFrame(()=>{
    const outer = document.querySelector('.mplan-wk-outer');
    if(!outer) return;
    // Replicar constantes de renderMiPlanCalendar
    const PHDR = 44;
    const PPH  = window.innerWidth <= 600 ? 40 : 64;
    const todayStr = simTodayStr();
    const nowDayIdx = DAY_KEYS.findIndex(d => FESTIVAL_DATES[d] === todayStr);
    if(nowDayIdx < 0) return; // festival no en curso — no scrollear
    const nowMin = simNow().getHours() * 60 + simNow().getMinutes();
    // Calcular SH igual que renderMiPlanCalendar (usamos plan completo como fallback)
    if(!savedAgenda || !savedAgenda.schedule.length) return;
    const allMins = savedAgenda.schedule.flatMap(s => {
      const st = toMin(s.time), en = st + parseDur(s.duration);
      return [st, en];
    });
    const SH = Math.max(9, Math.floor((Math.min(...allMins) - 30) / 60));
    const nowTop = PHDR + (nowMin - SH * 60) / 60 * PPH;
    const viewH  = outer.clientHeight;
    // Centrar la nowline en el viewport, con un margen superior de 20%
    const target = nowTop - viewH * 0.30;
    outer.scrollTo({ top: Math.max(0, target), behavior: 'smooth' });
  });
}

export function _updateMiPlanBadge(){
  const badge=document.getElementById('miplan-badge');
  if(!badge) return;
  if(!savedAgenda||!savedAgenda.schedule) { badge.classList.remove('visible'); return; }
  const now=simNow();
  const count=savedAgenda.schedule.filter(s=>{
    if(watched.has(s._title)) return false;
    const dateStr=FESTIVAL_DATES[s.day]; if(!dateStr) return false;
    const end=_festDate(dateStr,s.time);
    end.setMinutes(end.getMinutes()+parseDur(s.duration));
    return end<now;
  }).length;
  if(count>0){
    badge.textContent=count>9?'9+':String(count);
    badge.classList.add('visible');
  } else {
    badge.classList.remove('visible');
  }
}
