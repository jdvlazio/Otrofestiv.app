// ── src/controller/sheets-controller.js ───────────────────────────────────────
// p8 Step 7d-1 — Capa UI-primitiva del controller (leaf): lifecycle de sheets
// (pel/corto/conflict/prio/planConfirm/PV-rating) + rating UI + AV sheet + toast
// + utils (LB/flags/genre/metaBanners) + plan-helpers. Closure AST = 51, 0
// pulled-in. La importa handlers.js (7d-2); no llama a mutators/filters; view no
// la importa (sin ciclo). Lets de UI-state module-local; LB_SLUGS vía bridge
// (lo escribe loadFestival). Roster/viewstate vía bridge.

import { FESTIVAL_CONFIG, MAX_REMEMBERED_SLOTS, NOTICES, TMDB_IMG, _DEFAULT_FEST_ID } from '../config.js';
import { DAY_ABBR, DAY_NUM, ICONS, _secLabel, _sectionColor, isFullDayBlocked, makeProgramPoster, parseProgramTitle, renderRatingStarsHTML } from '../view/components.js';
import { _getItemPoster, _isEditorialPoster, _mkCortoItemHtml, _posterStyle, dayLabel, durFmt, flagFmt, getCortoItemPoster, getFilmPoster, getPosterSrc, sala, starsText, vcfg } from '../view/helpers.js';
import { closeAvSheet, closePVRating, closePrioLimit } from '../view/sheets.js';
import { showConflictModal, showToast } from '../view/feedback.js';
import { renderAgenda, renderAvBlocks } from '../view/agenda.js';
import { runCalc } from './calc.js';
import { saveAV, saveLastSlot, saveRating, saveSavedAgenda } from './persistence.js';
import { _reRenderIntereses, showAgView, switchMainNav, updateAgTab } from './pipeline.js';
import { dayFullyPassed, festivalEnded, parseDur, toMin } from '../domain/time.js';
import { screeningPassed } from '../domain/film.js';
import { isScreeningBlocked } from '../domain/schedule.js';
import { state } from '../state/state.js';
import { storage } from '../storage/storage.js';
import { t } from '../i18n/i18n.js';

// ── UI-state module-local + consts privados ──────────────────────────────────
const LB_SVG=`<svg class="block-shrink" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="13" height="13"><rect width="64" height="64" rx="9" fill="#2C3440"/><circle cx="21" cy="32" r="12" fill="#00B020" opacity=".9"/><circle cx="32" cy="32" r="12" fill="#3CBEDB" opacity=".85"/><circle cx="43" cy="32" r="12" fill="#FF8000" opacity=".9"/></svg>`;
let avAddOpen={};
let _avSheetType='hours';
let _avSheetDay=null;
const _GENRE_EN = {
  'Acción':'Action','Aventura':'Adventure','Comedia':'Comedy',
  'Drama':'Drama','Documental':'Documentary','Experimental':'Experimental',
  'Romance':'Romance','Sátira':'Satire','Terror':'Horror','Thriller':'Thriller',
  'Animación':'Animation','Ciencia Ficción':'Science Fiction',
  'Fantasía':'Fantasy','Misterio':'Mystery','Musical':'Musical',
};
let _toastActionFn=null;
let _pvTitle='', _pvRating=0;
let _conflictPending=null;
let _ratingTitle='';
let _currentRating=0;
const _COUNTRY_FLAGS={
  'Alemania':'🇩🇪','Argentina':'🇦🇷','Austria':'🇦🇹','Bolivia':'🇧🇴',
  'Brasil':'🇧🇷','Bélgica':'🇧🇪','Canadá':'🇨🇦','Chile':'🇨🇱',
  'Colombia':'🇨🇴','Cuba':'🇨🇺','EEUU':'🇺🇸','Estados Unidos':'🇺🇸',
  'Ecuador':'🇪🇨','Eslovaquia':'🇸🇰','España':'🇪🇸','Estonia':'🇪🇪',
  'Francia':'🇫🇷','Grecia':'🇬🇷','Inglaterra':'🇬🇧','Irán':'🇮🇷',
  'Italia':'🇮🇹','México':'🇲🇽','Nicaragua':'🇳🇮','Palestina':'🇵🇸',
  'Perú':'🇵🇪','Portugal':'🇵🇹','Reino Unido':'🇬🇧','Rep. Dominicana':'🇩🇴',
  'Suiza':'🇨🇭','Taiwán':'🇹🇼','Turquía':'🇹🇷','UK':'🇬🇧',
  'Venezuela':'🇻🇪','Vietnam':'🇻🇳',
  'United States':'🇺🇸','USA':'🇺🇸','US':'🇺🇸',
  'United Kingdom':'🇬🇧','England':'🇬🇧','Scotland':'🇬🇧','Ireland':'🇮🇪',
  'France':'🇫🇷','Germany':'🇩🇪','Italy':'🇮🇹','Spain':'🇪🇸',
  'Portugal':'🇵🇹','Belgium':'🇧🇪','Switzerland':'🇨🇭','Austria':'🇦🇹',
  'Netherlands':'🇳🇱','Sweden':'🇸🇪','Denmark':'🇩🇰','Norway':'🇳🇴',
  'Finland':'🇫🇮','Poland':'🇵🇱','Czech Republic':'🇨🇿','Hungary':'🇭🇺',
  'Romania':'🇷🇴','Greece':'🇬🇷','Turkey':'🇹🇷','Russia':'🇷🇺',
  'Ukraine':'🇺🇦','Israel':'🇮🇱','Palestine':'🇵🇸','Lebanon':'🇱🇧',
  'Iran':'🇮🇷','Iraq':'🇮🇶','Saudi Arabia':'🇸🇦','Egypt':'🇪🇬',
  'Morocco':'🇲🇦','Tunisia':'🇹🇳','Algeria':'🇩🇿','South Africa':'🇿🇦',
  'Nigeria':'🇳🇬','Kenya':'🇰🇪','Ethiopia':'🇪🇹','Ghana':'🇬🇭',
  'Senegal':'🇸🇳','Mali':'🇲🇱','Cameroon':'🇨🇲','Rwanda':'🇷🇼',
  'Democratic Republic of Congo':'🇨🇩','Congo':'🇨🇬','Ivory Coast':'🇨🇮',
  'India':'🇮🇳','Pakistan':'🇵🇰','Bangladesh':'🇧🇩','Nepal':'🇳🇵',
  'Sri Lanka':'🇱🇰','Afghanistan':'🇦🇫','Iran':'🇮🇷',
  'China':'🇨🇳','Japan':'🇯🇵','South Korea':'🇰🇷','Taiwan':'🇹🇼',
  'Thailand':'🇹🇭','Vietnam':'🇻🇳','Indonesia':'🇮🇩','Philippines':'🇵🇭',
  'Malaysia':'🇲🇾','Singapore':'🇸🇬','Myanmar':'🇲🇲',
  'Australia':'🇦🇺','New Zealand':'🇳🇿','Canada':'🇨🇦','Mexico':'🇲🇽',
  'Brazil':'🇧🇷','Argentina':'🇦🇷','Chile':'🇨🇱','Colombia':'🇨🇴',
  'Peru':'🇵🇪','Venezuela':'🇻🇪','Cuba':'🇨🇺','Haiti':'🇭🇹',
  'Dominican Republic':'🇩🇴','Puerto Rico':'🇵🇷',
  'North Macedonia':'🇲🇰','Macedonia':'🇲🇰','Serbia':'🇷🇸','Croatia':'🇭🇷',
  'Bosnia':'🇧🇦','Slovenia':'🇸🇮','Albania':'🇦🇱','Kosovo':'🇽🇰',
  'Bulgaria':'🇧🇬','Slovakia':'🇸🇰','Estonia':'🇪🇪','Latvia':'🇱🇻','Lithuania':'🇱🇹',
  'Georgia':'🇬🇪','Armenia':'🇦🇲','Azerbaijan':'🇦🇿','Kazakhstan':'🇰🇿',
  'Mongolia':'🇲🇳','Malta':'🇲🇹','Cyprus':'🇨🇾','Iceland':'🇮🇸',
  'Luxembourg':'🇱🇺','Liechtenstein':'🇱🇮','Monaco':'🇲🇨',
  'Jamaica':'🇯🇲','Trinidad and Tobago':'🇹🇹','Barbados':'🇧🇧',
  'Ecuador':'🇪🇨','Bolivia':'🇧🇴','Paraguay':'🇵🇾','Uruguay':'🇺🇾',
  'Honduras':'🇭🇳','Guatemala':'🇬🇹','El Salvador':'🇸🇻','Nicaragua':'🇳🇮',
  'Costa Rica':'🇨🇷','Panama':'🇵🇦'
};
let _cortoParentHtml=null;

export function openPelSheet(title){
  // Decodificar entidades HTML que el inline onclick puede pasar (&#39; → ')
  const _d=document.createElement('textarea');
  _d.innerHTML=title;
  title=_d.value;
  const entry=Object.values((()=>{
    const m={};
    FILMS.forEach(f=>{if(!m[f.title])m[f.title]={film:f,screenings:[]};m[f.title].screenings.push(f);});
    return m;
  })()).find(e=>e.film.title===title);
  if(!entry) return;
  const{film:f,screenings}=entry;
  const inWL=watchlist.has(f.title),inW=watched.has(f.title),inPrio=prioritized.has(f.title);
  const posterSrc=getFilmPoster(f);
  let posterHtml;
  if(f.is_programa&&f.film_list&&f.film_list.length>=2){
    const _sp1=_getItemPoster(f.film_list[0]);
    const _sp2=_getItemPoster(f.film_list[1]);
    const _fd1=JSON.stringify(f.film_list[0]).replace(/"/g,'&quot;');
    const _fd2=JSON.stringify(f.film_list[1]).replace(/"/g,'&quot;');
    const _c1=_sp1
      ?`<img class="psp-card psp-front" src="${_sp1}" loading="lazy" onerror="this.remove()" alt="" data-action="openCombinedFilmSheet" data-film="${_fd1}">`
      :`<div class="psp-card-ph" data-action="openCombinedFilmSheet" data-film="${_fd1}">🎬</div>`;
    const _c2=_sp2
      ?`<img class="psp-card psp-back" src="${_sp2}" loading="lazy" onerror="this.remove()" alt="" data-action="openCombinedFilmSheet" data-film="${_fd2}">`
      :`<div class="psp-card-ph" data-action="openCombinedFilmSheet" data-film="${_fd2}">🎬</div>`;
    posterHtml=`<div class="pel-sheet-poster-stage">${_c1}${_c2}</div>`;
  } else {
    if(_isEditorialPoster(f)){
      const _accent=_sectionColor(f.section||'');
      const _secLbl=_secLabel(f.section||'');
      posterHtml=`<div class="psp-editorial"><div class="psp-ed-hdr" style="background:${_accent}"><span>${_secLbl}</span></div><div class="psp-ed-img"><img src="${posterSrc}" loading="lazy" onerror="this.parentElement.style.display='none'" alt=""></div></div>`;
    } else {
      posterHtml=posterSrc
        ?`<img class="pel-sheet-poster"${_posterStyle(f)} src="${posterSrc}" data-title="${f.title.replace(/"/g,'&quot;')}" loading="lazy" onerror="_posterErr(this)" alt="">`
        :`<div class="pel-sheet-poster-ph">🎬</div>`;
    }
  }
  const{displayTitle}=parseProgramTitle(f.title);
  const secLabel=_secLabel(f.section);
  const totalFn=FILMS.filter(fi=>fi.title===f.title).length;
  const unica=totalFn===1;
  const DAY_ABB=['MAR','MIÉ','JUE','VIE','SÁB','DOM'];
  const future=screenings.filter(s=>!screeningPassed(s)).sort((a,b)=>a.day_order-b.day_order||toMin(a.time)-toMin(b.time));
  const past=screenings.filter(s=>screeningPassed(s));
  const allScr=[...future,...past];
  const rows=allScr.map(s=>{
    const dayAbb=dayLabel(s.day)||s.day;
    const vc=vcfg(s.venue),sl=sala(s.venue);
    const _festCity=(FESTIVAL_CONFIG[_activeFestId]||{}).city||'';
    const _city=_festCity&&vc.city&&vc.city!==_festCity?vc.city:'';
    const isPast=screeningPassed(s)&&!festivalEnded();
    return`<div class="pel-sheet-screening"${isPast?' style="opacity:.4"':''}>
      <span class="pelicula-day" data-day="${s.day}">${dayAbb}</span>
      <span class="pelicula-time">${s.time}</span>
      <span class="pelicula-venue" data-venue="${vc.short.replace(/"/g,'&quot;')}" data-action="filterByVenue">${ICONS.pin} <span class="venue-text">${vc.short}${sl?' · '+sl:''}${_city?`<span class="venue-municipio">${_city}</span>`:''}</span></span>
    </div>`;
  }).join('');
  // Lista de cortos si es programa
  let cortosHtml='';
  if(f.is_cortos&&f.film_list?.length){
    const cortoItems=f.film_list.map((item,n)=>{
      const r=filmRatings[item.title]||0;
      const ratingEl=r
        ?`<span class="corto-rating-stars">${starsText(r)}</span>`
:`<button class="corto-rate-btn" data-title="${item.title||''}" data-action="closePelAndRate" data-stop="1">★</button>`;
      return _mkCortoItemHtml(item,n,{
        cls:'pel-sheet-corto-item',
        section:f.section||'',
        ratingEl
      });
    }).join('');
    cortosHtml=`<div class="pel-sheet-divider"></div>
      <div class="pel-sheet-section-lbl">${t('label_programa')} <span class="ml-1 count-badge cb-neutral">${f.film_list.length}</span></div>
      <div class="pel-sheet-cortos-wrap">${cortoItems}</div>`;
  }
  const wlLabel=inWL?`${ICONS.heartFill} ${t('cta_en_intereses')}`:`${ICONS.heart} ${t('nav_intereses')}`;

  const _inPlan=savedAgenda&&savedAgenda.schedule.some(s=>s._title===f.title);
  const _planEntry=_inPlan?savedAgenda.schedule.find(s=>s._title===f.title):null;
  const _ps=document.getElementById('pel-sheet');
  if(_ps) _ps.scrollTop=0;
  _pushSheetState();
  // Metadata consolidada: director · género · año
  const _yr=f.year?String(f.year):'';const _gnYr=f.genre?_genreEN(f.genre)+(_yr?' · '+_yr:''):_yr;
  const _metaLine=[f.director||'',_gnYr].filter(Boolean).join(' · ');

  document.getElementById('pel-sheet-inner').innerHTML=`
    <div class="pel-sheet-header">
      ${posterHtml}
      <div class="pel-sheet-meta">
        <div class="pel-sheet-title">${(()=>{const _dt=filmDisplayTitle(f);return _dt.original?`${_dt.main}<div class="pel-sheet-original">${_dt.original}</div>`:_dt.main;})()}</div>
        ${f.type!=='event'
          ?`<div class="pel-sheet-flags-dur">${flagFmt(f.flags)||''}${f.duration?` · ${durFmt(f.duration)}`:''}</div>`
          :(f.duration?`<div class="pel-sheet-flags-dur">${durFmt(f.duration)}</div>`:'')}
        ${f.type!=='event'&&_metaLine?`<div class="pel-sheet-metaline">${_metaLine}</div>`:''}
        ${f.section?`<div class="pel-sheet-sec" data-section="${f.section.replace(/"/g,'&quot;')}" data-action="filterBySection">${secLabel} <span class="pel-sheet-sec-arrow">›</span></div>`:''}
      </div>
    </div>
    <div class="pel-sheet-divider"></div>
    <div class="pel-sheet-section-lbl">${f.type==='event'?t('label_horario'):allScr.length===1?t('label_funcion'):t('label_funciones_pl')}${totalFn>1&&f.type!=='event'?`<span class="ml-2 count-badge cb-neutral">${totalFn}</span>`:''}</div>
    ${(()=>{const _n=NOTICES.find(n=>n.title===f.title&&n.festival===(_activeFestId||_DEFAULT_FEST_ID));if(!_n)return'';const _msg=_n.type==='cancelled'?t('notice_funcion_canc'):`Reprogramada → ${_n.newDay||''} ${_n.newTime||''}${_n.newVenue?' · '+_n.newVenue:''}`;return`<div class="notice-banner-row"><span class="notice-badge">${_n.type==='cancelled'?t('notice_cancelada'):t('notice_reprog_short')}</span><span class="notice-banner-txt">${_msg}</span></div>`;})()}
    ${_metaBanners(f)}
    <div class="pel-sheet-screenings">${rows}</div>
    ${f.synopsis?`<div class="pel-sheet-divider"></div>
    <div class="pel-sheet-section-lbl">${f.type==='event'?t('label_descripcion'):t('label_sinopsis')}</div>
    <div class="pel-sheet-synopsis">${(_lang==='en'&&f.synopsis_en?f.synopsis_en:_lang==='es'&&f.synopsis_es?f.synopsis_es:f.synopsis).replace(/^⚠️\s*INGLÉS\s*[—-]\s*/,'')}</div>`:''}
    ${cortosHtml}
    ${(!f.is_cortos&&!f.is_programa&&f.type!=='event')?lbLink(f.title,f):''}
    <div class="pel-sheet-divider"></div>
    ${inW?`<div class="pel-sheet-ctas-watched">
        <button data-title="${f.title}" data-action="toggleWatchedAndClose" class="pel-sheet-action-btn act-on">${ICONS.check} ${t('cta_vista')}</button>
        ${!f.is_cortos?`<button data-title="${f.title}" data-action="closePelAndRate" class="pel-sheet-action-btn btn-secondary">${ICONS.star} ${filmRatings[f.title]?'Cambiar':t('cta_calificar')}</button>`:``}
      </div>`
    :`<div class="pel-sheet-ctas">
        <button id="pel-wl-btn" class="row-center-xs pel-sheet-action-btn${inWL?' act-on btn-primary':' btn-primary'}" data-title="${f.title}" data-action="togglePelWL">${inWL?ICONS.heartFill:ICONS.heart} ${inWL?t('cta_en_intereses'):t('cta_intereses')}</button>
        <button id="pel-prio-btn" class="row-center-xs pel-sheet-action-btn${inPrio?' act-prio':' btn-secondary'}" data-title="${f.title}" data-action="togglePelPrio">${inPrio?ICONS.starFill:ICONS.star} ${inPrio?t('cta_priorizada'):t('cta_priorizar')}</button>
        <button id="pel-vista-btn" class="row-center-xs pel-sheet-action-btn btn-tertiary" data-title="${f.title}" data-action="toggleWatched">${ICONS.check} ${f.type==='event'?t('cta_asistio'):t('cta_vista')}</button>
      </div>`}
    ${_inPlan&&activeView==='agenda'?`<button data-title="${f.title}" data-action="closePelAndRemove" class="pel-sheet-remove-plan">${ICONS.x} ${t('plan_quitar_plan')}</button>`:''}
  `;
  document.getElementById('pel-overlay').classList.add('open');
  _ps.classList.add('open');
  _ps.classList.toggle('compact', totalFn>=3);
  _pspAttach();
}

export function closePelSheet(){
  // Si hay contenido padre guardado, volvemos al programa en lugar de cerrar
  if(_cortoParentHtml){
    const inner=document.getElementById('pel-sheet-inner');
    if(inner){
      inner.innerHTML=_cortoParentHtml;
      _cortoParentHtml=null;
      const ps=document.getElementById('pel-sheet');
      if(ps) ps.scrollTop=0;
      _pspAttach();
      return;
    }
  }
  _cortoParentHtml=null;
  document.getElementById('pel-overlay').classList.remove('open');
  document.getElementById('pel-sheet').classList.remove('open');
}

export function _pspAttach(){
  const stage=document.getElementById('psp-stage');
  if(!stage||stage._pspReady) return;
  stage._pspReady=true;
  // Ambos posters abren su film — leen data-front en el momento del tap
  [0,1].forEach(i=>{
    const el=document.getElementById('psp-img-'+i);
    if(!el) return;
    el.addEventListener('click',function(e){
      e.stopPropagation();
      const front=parseInt(stage.dataset.front||'0');
      if(i!==front) return; // solo responde si es el frontal
      try{_openCombinedFilmSheet(JSON.parse(stage.dataset['film'+i]));}catch(err){console.warn('[psp] combined sheet parse failed',err);}
    });
  });
  // Swap zone — franja dedicada de 44px bajo el poster frontal
  const swapZone=document.getElementById('psp-swap-zone');
  if(swapZone) swapZone.addEventListener('click',function(e){
    e.stopPropagation();
    const cur=parseInt(stage.dataset.front||'0');
    _pspSwap(cur===0?1:0);
  });
}

export function _pspSwap(idx){
  const stage=document.getElementById('psp-stage');
  if(!stage) return;
  stage.dataset.front=idx;
  [0,1].forEach(i=>{
    const el=document.getElementById('psp-img-'+i);
    if(!el) return;
    el.classList.toggle('psp-front',i===idx);
    el.classList.toggle('psp-back',i!==idx);
  });
}

export function _pushSheetState(){
  try{history.pushState({sheet:true},'','');}catch(e){console.warn('[sheet] pushState failed',e);}
}

export function _closeTopSheet(){
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

export function openCortoSheet(title, country, duration, section, flags, director, genre, synopsis, posterOverride){
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
  const gnr=_genreEN(genre||(richItem&&richItem.genre)||'');
  const syn=synopsis||(richItem&&richItem.synopsis)||'';
  const ctry=country||(richItem&&richItem.country)||'';
  const dur=duration||(richItem&&richItem.duration)||'';
  const flgs=flags||countryToFlags(ctry)||'🌐';
  const posterUrl=posterOverride||(richItem&&getCortoItemPoster(richItem))||getPosterSrc(title,true)||null;
  const _isEd3=posterUrl&&posterUrl.includes('cloudfront.net');
  const posterHtml=_isEd3
    ?`<div class="psp-editorial"><div class="psp-ed-hdr" style="background:${_sectionColor(section||'')}"><span>${_secLabel(section||'').toUpperCase()}</span></div><div class="psp-ed-img"><img src="${posterUrl}" loading="lazy" onerror="this.parentElement.style.display='none'" alt=""></div></div>`
    :posterUrl
      ?`<img class="pel-sheet-poster" src="${posterUrl}" data-title="${(title||"").replace(/"/g,'&quot;')}" loading="lazy" onerror="_cortoSheetPosterErr(this)" alt="">`
      :`<img class="pel-sheet-poster" src="${makeProgramPoster(state,title,dur,section||'')||''}" alt="" loading="lazy">`;
  const ps=document.getElementById('pel-sheet');
  if(ps) ps.scrollTop=0;
  _pushSheetState();
  const parent=_findParentProgram(title);
  const parentTitle=parent?parent.title:null;
  const inWL=watchlist.has(parentTitle||title);
  const inPrio=prioritized.has(parentTitle||title);
  const secLabel=_secLabel(section||'');
  inner.innerHTML=`
    <div class="pel-sheet-header">
      ${posterHtml}
      <div class="pel-sheet-meta">
        <div class="pel-sheet-title">${title}</div>
        <div class="pel-sheet-flags-dur">${flgs}${dur?` · ${dur}`:''}</div>
        ${(dir||gnr)?`<div class="pel-sheet-metaline">${[dir,gnr].filter(Boolean).join(' · ')}</div>`:''}
        ${secLabel?`<div class="pel-sheet-sec">${secLabel}</div>`:''}
      </div>
    </div>
    <div class="pel-sheet-divider"></div>
    ${syn?`<div class="pel-sheet-section-lbl">${t('label_sinopsis')}</div><div class="pel-sheet-synopsis">${syn}</div><div class="pel-sheet-divider"></div>`:''}
    <a class="c-lb pel-sheet-lb" href="${lbUrl(title)||'#'}" target="_blank" rel="noopener"${!lbUrl(title)?' style="display:none"':''}>${LB_SVG}<span class="c-lb-text pel-sheet-lb-text">Letterboxd</span></a>
    <div class="pel-sheet-divider"></div>
    ${parentTitle?`<div class="meta-xs-gray">${t('meta_corto_incluye')}</div>`:''}
    <div class="flex-gap1-mt1">
      <button id="corto-wl-btn" class="row-center-xs pel-sheet-action-btn${inWL?' act-on btn-primary':' btn-primary'}" data-title="${parentTitle||title}" data-action="toggleWL">${inWL?ICONS.heartFill:ICONS.heart} ${inWL?t('cta_en_intereses'):t('cta_intereses')}</button>
      <button id="corto-prio-btn" class="row-center-xs pel-sheet-action-btn${inPrio?' act-prio':' btn-secondary'}" data-title="${parentTitle||title}" data-action="togglePelPrio">${inPrio?ICONS.starFill:ICONS.star} ${inPrio?t('cta_priorizada'):t('cta_priorizar')}</button>
      <button class="row-center-xs pel-sheet-action-btn${filmRatings[title]?' act-on':' btn-secondary'}" data-title="${title}" data-action="closePelAndRate">${ICONS.star} ${filmRatings[title]?'Cambiar':t('cta_calificar')}</button>
    </div>
  `;
  const _psReset2=document.getElementById('pel-sheet');
  if(_psReset2){_psReset2.scrollTop=0;_psReset2.classList.remove('compact');}
  document.getElementById('pel-overlay').classList.add('open');
  const _psCo=document.getElementById('pel-sheet');
  _psCo.scrollTop=0;
  _psCo.classList.add('open');
}

export function openCortoSheetFromEl(el,e){
  if(e) e.stopPropagation();
  const title=decodeURIComponent(el.dataset.ct||'');
  const parent=_findParentProgram(title);
  const section=parent?.section||'';
  // data-cp: poster resuelto en render time — llega directo, sin depender de richItem lookup
  const posterOverride=decodeURIComponent(el.dataset.cp||'')||null;
  openCortoSheet(
    title,
    decodeURIComponent(el.dataset.cc||''),
    decodeURIComponent(el.dataset.cd||''),
    section,
    countryToFlags(decodeURIComponent(el.dataset.cc||'')),
    decodeURIComponent(el.dataset.cdir||''),
    decodeURIComponent(el.dataset.cg||''),
    decodeURIComponent(el.dataset.cs||''),
    posterOverride
  );
}

export function _openCombinedFilmSheet(filmData){
  const inner=document.getElementById('pel-sheet-inner');
  if(!inner) return;
  const pelSheet=document.getElementById('pel-sheet');
  if(pelSheet&&pelSheet.classList.contains('open')){
    _cortoParentHtml=inner.innerHTML;
  }
  const{title='',director='',year='',duration='',flags='🌐',country='',synopsis='',synopsis_en='',synopsis_es='',lbSlug='',poster:_fPoster=''}=filmData;
  const posterUrl=_fPoster?((_fPoster.startsWith('http')||_fPoster.startsWith('/assets/'))?_fPoster:TMDB_IMG+_fPoster):getPosterSrc(title,false)||null;
  const _isEd4=posterUrl&&posterUrl.includes('cloudfront.net');
  const _sec4=(()=>{const _p=FILMS.find(f=>f.film_list&&f.film_list.some(c=>c.title===title));return _p?.section||'';})();
  const posterHtml=_isEd4
    ?`<div class="psp-editorial"><div class="psp-ed-hdr" style="background:${_sectionColor(_sec4)}"><span>${_secLabel(_sec4).toUpperCase()}</span></div><div class="psp-ed-img"><img src="${posterUrl}" loading="lazy" onerror="this.parentElement.style.display='none'" alt=""></div></div>`
    :posterUrl
      ?`<img class="pel-sheet-poster" src="${posterUrl}" data-title="${(title||"").replace(/"/g,'&quot;')}" loading="lazy" onerror="_cortoSheetPosterErr(this)" alt="">`
      :`<div class="pel-sheet-poster-ph">🎬</div>`;
  const metaLine=[director,year].filter(Boolean).join(' · ');
  const lbHref=lbSlug?`https://letterboxd.com/film/${lbSlug}/`:lbUrl(title);
  const ps=document.getElementById('pel-sheet');
  if(ps) ps.scrollTop=0;
  _pushSheetState();
  inner.innerHTML=`
    <div class="pel-sheet-header">
      ${posterHtml}
      <div class="pel-sheet-meta">
        <div class="pel-sheet-title">${title}</div>
        ${(flags||duration)?`<div class="pel-sheet-flags-dur">${flags||''}${flags&&duration?' · ':''}${duration||''}</div>`:''}
        ${metaLine?`<div class="pel-sheet-metaline">${metaLine}</div>`:''}
        ${(()=>{const _parent=FILMS.find(f=>f.film_list&&f.film_list.some(c=>c.title===title));const _sec=_parent?.section;if(!_sec)return'';const _lbl=_secLabel(_sec);return`<div class="pel-sheet-sec" style="cursor:default">${_lbl}</div>`;})()}
      </div>
    </div>
    <div class="pel-sheet-divider"></div>
    <div class="pel-sheet-section-lbl">${t('label_sinopsis')}</div>
    <div class="pel-sheet-synopsis">${_lang==='en'&&synopsis_en?synopsis_en:_lang==='es'&&synopsis_es?synopsis_es:(synopsis||'')}</div>
    <a class="c-lb pel-sheet-lb" href="${lbHref}" target="_blank" rel="noopener">${LB_SVG}<span class="c-lb-text pel-sheet-lb-text">Letterboxd</span></a>
    <div class="pel-sheet-divider"></div>
  `;
  const _psReset=document.getElementById('pel-sheet');
  if(_psReset){_psReset.scrollTop=0;_psReset.classList.remove('compact');}
  document.getElementById('pel-overlay').classList.add('open');
  const _psC=document.getElementById('pel-sheet');
  _psC.scrollTop=0;
  _psC.classList.add('open');
}

export function _findParentProgram(cortoTitle){
  return FILMS.find(f=>f.is_cortos&&f.film_list?.some(c=>c.title===cortoTitle))||null;
}

export function openConflictSheet(incomingTitle, incomingScreen, existingEntry){
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
  // Guardar pendiente para ejecutar al confirmar
  _conflictPending={incomingTitle, incomingScreen, existingEntry};

  const btn=document.getElementById('cs-replace-btn');
  const keepBtn=document.getElementById('cs-keep-btn');
  if(btn) btn.onclick=confirmConflictReplace;
  if(keepBtn) keepBtn.onclick=closeConflictSheet;

  document.getElementById('conflict-sheet-overlay').classList.add('open');
  document.getElementById('conflict-sheet').classList.add('open');
  _pushSheetState();
}

export function closeConflictSheet(){
  _conflictPending=null;
  document.getElementById('conflict-sheet-overlay').classList.remove('open');
  document.getElementById('conflict-sheet').classList.remove('open');
}

export function confirmConflictReplace(){
  // 1. READ + 2. GUARD
  if(!_conflictPending) return;
  const{incomingTitle, incomingScreen, existingEntry}=_conflictPending;
  // 3. MUTATE — quitar la existente e insertar la nueva
  state.update('savedAgenda', a => ({
    ...a,
    schedule: [
      ...a.schedule.filter(s=>!(s._title===existingEntry._title&&s.day===existingEntry.day&&s.time===existingEntry.time)),
      {...incomingScreen,_title:incomingTitle}
    ].sort((x,y)=>x.day_order!==y.day_order?x.day_order-y.day_order:toMin(x.time)-toMin(y.time))
  }));
  // 4. PERSIST + 5. RENDER + UI EFFECTS
  saveSavedAgenda();
  const{displayTitle:dt}=parseProgramTitle(incomingTitle);
  closeConflictSheet();
  showToast(`${ICONS.calendar} ${dt.length>22?dt.slice(0,20)+'…':dt} en tu plan`,'info');
  renderAgenda();
}

export function openPrioLimit(newTitle){
  // Eyebrow con contador
  const eyebrow=document.getElementById('prio-limit-eyebrow-txt');
  const count=document.getElementById('prio-limit-count');
  if(eyebrow) eyebrow.textContent=`Prioridades · ${PRIO_LIMIT}/${PRIO_LIMIT}`;
  if(count) count.textContent=PRIO_LIMIT;
  // i18n patches for static prio-limit elements
  const _yaTenes=document.getElementById('prio-limit-ya-tenes-txt');
  const _prioWord=document.getElementById('prio-limit-prio-word');
  const _quieres=document.getElementById('prio-limit-quieres');
  if(_yaTenes) _yaTenes.textContent=t('plan_ya_tenes_prio');
  if(_prioWord) _prioWord.textContent=t('misc_prioridades');
  if(_quieres)  _quieres.textContent=t('plan_quieres_prio');

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
      const safeSwap=t.replace(/'/g,"&#39;");
      const safeNew=newTitle.replace(/'/g,"&#39;");
      return`<div class="prio-limit-item">
        ${poster?`<img class="prio-limit-thumb" src="${poster}" onerror="this.remove()" alt="" loading="lazy">`:'<div class="prio-limit-thumb"></div>'}
        <div class="prio-limit-info">
          <div class="prio-limit-name">${dt}</div>
          <div class="prio-limit-when">${when}</div>
        </div>
        <button class="prio-limit-swap" data-action="swapPriority" data-rmtitle="${safeSwap}" data-addtitle="${safeNew}">Cambiar</button>
      </div>`;
    }).join('');
    list.innerHTML=items;
  }

  document.getElementById('prio-limit-overlay').classList.add('open');
  document.getElementById('prio-limit-sheet').classList.add('open');
}

export function openPlanConfirm(schedule){
  // Ordenar por posición en DAY_KEYS (funciona para cualquier festival)
  const sorted=[...schedule].sort((a,b)=>{
    const ai=DAY_KEYS.indexOf(a.day),bi=DAY_KEYS.indexOf(b.day);
    return (ai<0?999:ai)-(bi<0?999:bi)||a.time.localeCompare(b.time);
  });
  const total=sorted.length;
  const days=[...new Set(sorted.map(s=>s.day))];
  const dayRange=days.length===1?dayLabel(days[0]):`${dayLabel(days[0])}–${dayLabel(days[days.length-1])}`;

  // Sub: N películas · DÍAS
  const sub=document.getElementById('plan-confirm-sub');
  if(sub) sub.innerHTML=`<span class="mr-1 count-badge cb-neutral">${total}</span> · ${dayRange}`;

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
    }).join('')+(rest>0?`<div class="plan-confirm-film" style="color:var(--gray)"><div class="bg-gray plan-confirm-dot"></div><div class="plan-confirm-name">+ ${rest} ${t('misc_mas')} ${dayRange}</div></div>`:'');
  }

  const _pcSheet=document.getElementById('plan-confirm-sheet');
  if(_pcSheet){ _pcSheet.style.display=''; requestAnimationFrame(()=>_pcSheet.classList.add('open')); }
  document.getElementById('plan-confirm-overlay').classList.add('open');
}

export function closePlanConfirm(goToPlan){
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

export function openPostViewRating(title, day, time, venue, duration){
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

export function openRatingSheet(title){
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
    if(_currentRating>0){_btn.textContent=t('misc_guardar');_btn.className='rating-action-btn save';}
    else{_btn.textContent=t('misc_omitir');_btn.className='rating-action-btn skip';}
  }
  document.getElementById('rating-overlay').classList.add('open');
  document.getElementById('rating-sheet').classList.add('open');
  requestAnimationFrame(()=>{
    const range=document.getElementById('rating-range');
    if(range){range.value=Math.round(_currentRating*2);range._ratingInit=false;}
    _initRatingInteraction();
  });
}

export function closeRatingSheet(){
  if(_currentRating>0){
    saveRating(_ratingTitle,_currentRating);
    const _stars=starsDisplay(_currentRating,11);
    showToast(`<span class="row-xs">${_stars}</span>`,'info');
  } else {
    if(filmRatings[_ratingTitle]){
      saveRating(_ratingTitle,0);
      showToast(t('toast_calif_elim'),'info');
    }
  }
  document.getElementById('rating-overlay').classList.remove('open');
  document.getElementById('rating-sheet').classList.remove('open');
  // Re-render para reflejar el nuevo rating
  _reRenderIntereses();
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

export function renderRatingStars(current){
  const el=document.getElementById('rating-stars');
  if(!el) return;
  el.innerHTML=renderRatingStarsHTML(state, current);
}

export function updateRatingStars(current){
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

export function setRating(val){
  _currentRating=val;
  updateRatingStars(val); // rápido, sin recrear DOM
  const btn=document.getElementById('rating-action-btn');
  if(btn){
    if(val>0){btn.textContent=t('misc_guardar');btn.className='rating-action-btn save';}
    else{btn.textContent=t('misc_omitir');btn.className='rating-action-btn skip';}
  }
}

export function _initRatingInteraction(){
  const range=document.getElementById('rating-range');
  if(!range||range._ratingInit) return;
  range._ratingInit=true;
  range.addEventListener('input',()=>{
    setRating(parseInt(range.value)/2);
  });
}

export function _pvStarSVG(fill){
  if(fill==='full')  return`<svg width="34" height="34" viewBox="0 0 24 24"><polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26" fill="var(--amber)" stroke="var(--amber)" stroke-width="1.75" stroke-linejoin="round"/></svg>`;
  if(fill==='half')  return`<svg width="34" height="34" viewBox="0 0 24 24"><defs><linearGradient id="pvhg"><stop offset="50%" stop-color="var(--amber)"/><stop offset="50%" stop-color="transparent"/></linearGradient></defs><polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26" fill="url(#pvhg)" stroke="var(--amber)" stroke-width="1.5" stroke-linejoin="round"/></svg>`;
  return`<svg width="34" height="34" viewBox="0 0 24 24" style="opacity:.15"><polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26" fill="none" stroke="var(--amber)" stroke-width="1.75" stroke-linejoin="round"/></svg>`;
}

export function _pvRenderStars(val){
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
  if(hint) hint.textContent=val>0?`${val} de 5`:t('misc_deslizar');
  if(hint) hint.style.color=val>0?'var(--amber)':'var(--gray)';
  if(btn)  btn.disabled=val===0;
}

export function starsDisplay(rating,size){
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
    html+=`<svg class="block-shrink" width="${s}" height="${s}" viewBox="0 0 24 24">${grad}<polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26" fill="${fv}" stroke="${st}" stroke-width="1.75" stroke-linejoin="round"/></svg>`;
  }
  return html;
}

export function openAvSheet(){
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
      return`<button class="av-day-chip${isPast?' past':''}${sel}" data-day="${d}" data-action="selectAvDay">${lbl} ${num}</button>`;
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

export function selectAvDay(day){
  _avSheetDay=day;
  _refreshAvDayChips();
}

export function _refreshAvDayChips(){
  document.querySelectorAll('.av-day-chip').forEach(btn=>{
    btn.classList.toggle('selected', btn.dataset.day===_avSheetDay);
  });
}

export function setAvType(type){
  _avSheetType=type;
  document.getElementById('av-type-hours')?.classList.toggle('selected',type==='hours');
  document.getElementById('av-type-full')?.classList.toggle('selected',type==='full');
  const ts=document.getElementById('av-time-section');
  if(ts) ts.style.display=type==='hours'?'':'none';
}

export function confirmAvBlock(){
  // 1. READ + 2. GUARD
  if(!_avSheetDay) return;
  if(_avSheetType==='full'){
    // Branch A: full-day — delega a toggleFullDay
    closeAvSheet();
    if(!isFullDayBlocked(_avSheetDay)) setTimeout(()=>toggleFullDay(_avSheetDay),50);
    return;
  }
  // Branch B: range
  // 1b. READ DOM inputs
  const from=document.getElementById('av-sheet-from')?.value||'09:00';
  const to=document.getElementById('av-sheet-to')?.value||'12:00';
  // 2b. GUARD — validation con early returns
  if(from>=to){showToast(t('av_hora_invalida'),'warn');return;}
  const av=availability[_avSheetDay];
  if(av.blocks.some(b=>toMin(from)<toMin(b.to)&&toMin(to)>toMin(b.from))){
    showToast('Este horario coincide con otro bloque','warn');return;
  }
  // 3. MUTATE — diferido via conflict modal si hay conflictos
  const _conflicts=checkPlanConflictsWithBlock(_avSheetDay,from,to);
  const _doAdd=()=>{
    _conflicts.forEach(s=>_removePlanItem(s._title));
    state.update('availability', a => ({
      ...a,
      [_avSheetDay]: {...a[_avSheetDay], blocks: [...a[_avSheetDay].blocks, {from,to}].sort((x,y)=>toMin(x.from)-toMin(y.from))}
    }));
    // 4. PERSIST + 5. RENDER
    cachedResult=null;saveAV();renderAvBlocks();invalidateCalcResult();
  };
  closeAvSheet();
  if(_conflicts.length) setTimeout(()=>showConflictModal(_conflicts,_doAdd),50);
  else _doAdd();
}

export function renderAvDay(day){
  const row=document.getElementById(`av-row-${day}`);if(!row) return;
  const fullBlocked=isFullDayBlocked(day);
  const isPast=dayFullyPassed(day);
  row.className=`av-row${isPast?' av-past':''}${fullBlocked?' av-full':''}`;
  row.innerHTML=renderAvDayHTML(state, day);
  // Set default values for selects after render
  if(avAddOpen[day]){
    const sf=document.getElementById(`av-from-${day}`);
    const st=document.getElementById(`av-to-${day}`);
    if(sf) sf.value='12:00';
    if(st) st.value='14:00';
  }
}

export function renderAvDayHTML(state, day){
  const {availability} = state.snapshot();
  const fullBlocked=isFullDayBlocked(day);
  const visibleBlocks=availability[day].blocks.filter(b=>!(toMin(b.from)<=0&&toMin(b.to)>=toMin('23:59')));
  const hasAny=fullBlocked||visibleBlocks.length>0;
  const addOpen=!!avAddOpen[day];

  const pillsHtml=fullBlocked
    ?`<span class="av-pill full">${t('av_todo_el_dia')}</span>`
    :visibleBlocks.map(b=>`<span class="av-pill">${b.from}–${b.to}<button class="av-pill-rm" aria-label="${t('av_eliminar')}" data-action="removeBlock" data-day="${day}" data-from="${b.from}" data-to="${b.to}" data-stop="1">×</button></span>`).join('');

  // Inline form — always shows when addOpen, with 15-min slot dropdowns
  const timeOpts=`<option value="08:00">08:00</option><option value="08:15">08:15</option><option value="08:30">08:30</option><option value="08:45">08:45</option><option value="09:00">09:00</option><option value="09:15">09:15</option><option value="09:30">09:30</option><option value="09:45">09:45</option><option value="10:00">10:00</option><option value="10:15">10:15</option><option value="10:30">10:30</option><option value="10:45">10:45</option><option value="11:00">11:00</option><option value="11:15">11:15</option><option value="11:30">11:30</option><option value="11:45">11:45</option><option value="12:00">12:00</option><option value="12:15">12:15</option><option value="12:30">12:30</option><option value="12:45">12:45</option><option value="13:00">13:00</option><option value="13:15">13:15</option><option value="13:30">13:30</option><option value="13:45">13:45</option><option value="14:00">14:00</option><option value="14:15">14:15</option><option value="14:30">14:30</option><option value="14:45">14:45</option><option value="15:00">15:00</option><option value="15:15">15:15</option><option value="15:30">15:30</option><option value="15:45">15:45</option><option value="16:00">16:00</option><option value="16:15">16:15</option><option value="16:30">16:30</option><option value="16:45">16:45</option><option value="17:00">17:00</option><option value="17:15">17:15</option><option value="17:30">17:30</option><option value="17:45">17:45</option><option value="18:00">18:00</option><option value="18:15">18:15</option><option value="18:30">18:30</option><option value="18:45">18:45</option><option value="19:00">19:00</option><option value="19:15">19:15</option><option value="19:30">19:30</option><option value="19:45">19:45</option><option value="20:00">20:00</option><option value="20:15">20:15</option><option value="20:30">20:30</option><option value="20:45">20:45</option><option value="21:00">21:00</option><option value="21:15">21:15</option><option value="21:30">21:30</option><option value="21:45">21:45</option><option value="22:00">22:00</option><option value="22:15">22:15</option><option value="22:30">22:30</option><option value="22:45">22:45</option><option value="23:00">23:00</option><option value="23:15">23:15</option><option value="23:30">23:30</option><option value="23:45">23:45</option><option value="00:00">00:00</option><option value="00:15">00:15</option><option value="00:30">00:30</option><option value="00:45">00:45</option><option value="01:00">01:00</option>`;
  const inlineForm=addOpen?`<div class="av-inline-form">
      <select id="av-from-${day}" class="av-time-input">${timeOpts}</select>
      <span class="av-sep">–</span>
      <select id="av-to-${day}" class="av-time-input">${timeOpts}</select>
      <button class="av-add-btn" data-action="addBlock" data-day="${day}">${t('av_confirmar')}</button>
      <button class="av-plus-btn" data-action="setAvAddOpen" data-day="${day}" data-open="0">${ICONS.x}</button>
    </div>`:'';

  return `
    <div class="av-row-lbl">
      <div class="av-row-dayname">${DAY_ABBR[day]}</div>
      <div class="av-row-date${hasAny?' wk-has':''}">${DAY_NUM[day]}</div>
    </div>
    <div class="av-row-content">
      ${pillsHtml?`<div class="av-pills">${pillsHtml}</div>`:''}
      ${inlineForm}
      <div class="av-row-btns" style="margin-top:${pillsHtml||addOpen?'6px':'0'}">
        ${!fullBlocked&&!addOpen?`<button class="av-plus-btn" data-action="setAvAddOpen" data-day="${day}" data-open="1">${ICONS.plus} ${t('misc_no_disp')}</button>`:''}
        ${!addOpen?`<button class="row-xs av-full-btn${fullBlocked?' active':''}" data-action="toggleFullDay" data-day="${day}">
          ${fullBlocked?ICONS.x+' '+t('av_liberar_dia'):ICONS.plus+' '+t('av_todo_el_dia_btn')}
        </button>`:''}
      </div>
    </div>`;
}

export function addBlock(day){
  // 1. READ — DOM inputs (input state, ephemeral)
  const f=document.getElementById(`av-from-${day}`).value;
  const toVal=document.getElementById(`av-to-${day}`).value;
  // 2. GUARD — validation con early returns + toast
  if(!f||!toVal){showToast(t('av_seleccionar'),'warn');return;}
  if(toMin(f)>=toMin(toVal)){showToast(t('av_hora_invalida'),'warn');return;}
  const av=availability[day];
  if(av.blocks.some(b=>toMin(f)<toMin(b.to)&&toMin(toVal)>toMin(b.from))){showToast('Este horario coincide con otro bloque','warn');return;}
  // 3. MUTATE — diferida via conflict modal si hay conflictos
  const _blockConflicts=checkPlanConflictsWithBlock(day,f,toVal);
  const _doAdd=()=>{
    _blockConflicts.forEach(s=>_removePlanItem(s._title));
    state.update('availability', a => ({
      ...a,
      [day]: {...a[day], blocks: [...a[day].blocks, {from:f,to:toVal}].sort((x,y)=>toMin(x.from)-toMin(y.from))}
    }));
    avAddOpen[day]=false;
    // 4. PERSIST + 5. RENDER
    cachedResult=null;saveAV();renderAvBlocks();invalidateCalcResult();
  };
  if(_blockConflicts.length) setTimeout(()=>showConflictModal(_blockConflicts,_doAdd),50);
  else _doAdd();
}

export function removeBlock(day,fromVal,toVal){
  // 3. MUTATE
  state.update('availability', a => ({...a, [day]: {...a[day], blocks: a[day].blocks.filter(b=>!(b.from===fromVal&&b.to===toVal))}}));
  // 4. PERSIST + 5. RENDER + UI EFFECTS
  cachedResult=null;
  saveAV();
  renderAvBlocks();
  invalidateCalcResult();
  _checkRecalcOpportunity();
}

export function toggleFullDay(day){
  // 1. READ — UI state (isFullDayBlocked lee availability via free var)
  // 2. GUARD + 3. MUTATE — branch A: libera día
  if(isFullDayBlocked(day)){
    state.update('availability', a => ({...a, [day]: {...a[day], blocks: []}}));
    cachedResult=null;saveAV();renderAvBlocks();invalidateCalcResult();
    _checkRecalcOpportunity();
    return;
  }
  // Branch B: bloquea — con confirm modal si hay conflictos
  const _conflicts=checkPlanConflictsWithBlock(day,'00:00','23:59');
  const _doBlock=()=>{
    _conflicts.forEach(s=>_removePlanItem(s._title));
    state.update('availability', a => ({...a, [day]: {...a[day], blocks: [{from:'00:00',to:'23:59'}]}}));
    avAddOpen[day]=false;
    cachedResult=null;saveAV();renderAvBlocks();invalidateCalcResult();
  };
  if(_conflicts.length) setTimeout(()=>showConflictModal(_conflicts,_doBlock),50);
  else _doBlock();
}

export function _setAvAddOpen(day, val) {
  avAddOpen[day] = val;
  renderAvDay(day);
}

export function showActionToast(msg,actionLabel,actionFn,duration=4000){
  _toastActionFn=actionFn;
  let t=document.getElementById('prio-toast');
  if(!t){t=document.createElement('div');t.id='prio-toast';document.body.appendChild(t);}
  t.className='prio-toast action';
  t.innerHTML=`<span>${msg}</span><button class="toast-action-btn" data-action="dismissToastAction">${actionLabel}</button>`;
  t.style.opacity='1';t.style.pointerEvents='all';
  clearTimeout(t._to);t._to=setTimeout(()=>{t.style.opacity='0';t.style.pointerEvents='none';},duration);
}

export function _dismissToastAction() {
  if (_toastActionFn) {
    _toastActionFn();
    _toastActionFn = null;
    showToast('', 'info', 100);
  }
}

export function lbUrl(title){
  // Use festival-specific slug map from active festival config
  const _cfg=FESTIVAL_CONFIG[_activeFestId]||{};
  const _slugMap=_cfg.lbSlugs||LB_SLUGS;
  const slug=_slugMap[title]||LB_SLUGS[title];
  if(!slug) return null;
  if(slug.startsWith('http')) return slug;
  return`https://letterboxd.com/film/${slug}/`;
}

export function lbUrlForFilm(f){
  if(!f) return null;
  if(f.lbSlug) return f.lbSlug.startsWith('http')?f.lbSlug:`https://letterboxd.com/film/${f.lbSlug}/`;
  return lbUrl(f.title);
}

export function lbLink(title,film){
  const url=film?lbUrlForFilm(film):lbUrl(title);
  if(!url) return'';
  return`<a class="c-lb pel-sheet-lb" href="${url}" target="_blank" rel="noopener">${LB_SVG}<span class="c-lb-text pel-sheet-lb-text">Letterboxd</span></a>`;
}

export function countryToFlags(countryStr){
  if(!countryStr) return '🌍';
  const parts=countryStr.split('/').map(s=>s.trim());
  const flags=parts.map(p=>_COUNTRY_FLAGS[p]||'').filter(Boolean);
  return flags.length?flags.join(''):'🌍';
}

export function filmDisplayTitle(f) {
  if (_lang === 'en' && f.title_en && f.title_en !== f.title) {
    return { main: f.title_en, original: f.title };
  }
  return { main: f.title, original: null };
}

export function _genreEN(g) {
  if (!g || _lang !== 'en') return g;
  return g.split(',').map(s => _GENRE_EN[s.trim()] || s.trim()).join(', ');
}

export function _metaBanners(f){
  let b='';
  if(f.has_qa) b+=`<div class="meta-banner"><div class="meta-banner-dot"></div><div><div class="meta-banner-label">${t('meta_qa_label')}</div><div class="meta-banner-text">${t('notice_extension')} <span>${t('meta_qa_time')}</span></div></div></div>`;
  if(f.requires_registration) b+=`<div class="meta-banner"><div class="meta-banner-dot"></div><div><div class="meta-banner-label">${t('badge_inscripcion_prev')}</div><div class="meta-banner-text">${t('meta_registro_text')}</div></div></div>`;
  return b;
}

export function _checkRecalcOpportunity(){
  if(!savedAgenda||!savedAgenda.schedule.length) return;
  const planTitles=new Set(savedAgenda.schedule.map(s=>s._title));
  const candidates=[...watchlist].filter(t=>!planTitles.has(t)&&!watched.has(t));
  const hasOpportunity=candidates.some(t=>{
    const screens=FILMS.filter(f=>f.title===t&&!screeningPassed(f));
    return screens.length&&screens.some(s=>!isScreeningBlocked(s));
  });
  if(hasOpportunity){
    showActionToast(t('toast_horario_lib'),'Recalcular',()=>{
      switchMainNav('mnav-planner');showAgView();setTimeout(runCalc,300);
    },5000);
  }
}

export function _removePlanItem(title){
  if(!savedAgenda) return;
  const removed=savedAgenda.schedule.find(s=>s._title===title);
  if(removed){
    state.update('lastRemovedSlots', arr => [{...removed,_isRestored:true}, ...arr.filter(r=>r._title!==removed._title)].slice(0,MAX_REMEMBERED_SLOTS));
    saveLastSlot();
  }
  state.update('savedAgenda', a => ({...a, schedule: a.schedule.filter(s=>s._title!==title)}));
  if(!savedAgenda.schedule.length) state.set('savedAgenda', null);
  saveSavedAgenda();
}

export function checkPlanConflictsWithBlock(day, fromStr, toStr){
  if(!savedAgenda||!savedAgenda.schedule.length) return[];
  const bFrom=toMin(fromStr), bTo=toMin(toStr);
  return savedAgenda.schedule.filter(s=>{
    if(s.day!==day) return false;
    const sStart=toMin(s.time), sEnd=sStart+parseDur(s.duration);
    return sStart<bTo&&sEnd>bFrom;
  });
}

export function invalidateCalcResult(){
  // Called when availability changes — resets result prompt
  const _wrap=document.getElementById('ag-result-wrap');
  if(_wrap) _wrap.style.display='none';
  const res=document.getElementById('ag-result');
  if(!res){showAgView();return;}
  res.innerHTML='';
}

export function savePVRating(){
  // 1. READ — UI state ephemeral (_pvRating, _pvTitle son module-level)
  // 2. GUARD — solo guardar si rating válido
  if(_pvRating>0){
    // 3. MUTATE
    state.update('filmRatings', o => ({...o, [_pvTitle]: _pvRating}));
    // 4. PERSIST
    storage.setFilmRatings(filmRatings);
    // 5. RENDER + UI EFFECTS — toast
    const stars=['','★','★★','★★★','★★★★','★★★★★'];
    showToast(stars[Math.round(_pvRating)]||'★ Calificada','info');
  }
  closePVRating();
  // Render automático vía pipeline (filmRatings). Si rating=0 no hay mutación →
  // no re-render (no-op visual: el prompt de calificar sigue igual).
}
