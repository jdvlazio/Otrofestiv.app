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

import { NOTICES, PALMARES, SECTION_ORDER_LIST, _DEFAULT_FEST_ID } from '../config.js';
import { ICONS, _buildPosterV16, _secLabel, _secLabelFull, _sectionColor, escXML, makeEventPoster, makeProgramPoster, parseProgramTitle } from './components.js';
import { _dayChips, _getItemPoster, _metaBadges, _plistPosterHtml, _programaStack, dayLabel, durFmt, emptyState, getFilmPoster, isNowShowing, isQaOnlyNow, posterParts, sala, vcfg, venueMatches, venueCity, programParts, isCitySel, venueSelLabel,
} from './helpers.js';
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
// Un aviso por CIUDADES no tiene `title`: su clave estable es `id`. Sin esto, la
// clave sería «…\0undefined» y descartar un aviso ocultaría cualquier otro sin título.
export function _noticeKey(title){ return (_activeFestId||_DEFAULT_FEST_ID)+String.fromCharCode(0)+title; }
export function noticeId(n){ return n.id||n.title||''; }

// _noticeAfecta — ¿este aviso alcanza a ESTA función? Es el alcance del aviso, el
// mismo que sella el loader: por CIUDADES, o por título (+fecha si la trae).
function _noticeAfecta(n,f){
  if(Array.isArray(n.cities)) return n.cities.includes(vcfg(f.venue).city||'');
  return n.title===f.title&&(!n.date||n.date===f.day);
}

export function getActiveNotices(){
  const festId=(_activeFestId||_DEFAULT_FEST_ID);
  const today=new Date(); today.setHours(0,0,0,0);
  return NOTICES.filter(n=>{
    if(n.festival!==festId) return false;
    if(_dismissedNotices.has(_noticeKey(noticeId(n)))) return false;
    // Banner desaparece al día siguiente de la función cancelada
    if(n.date){
      const funcDate=new Date(n.date+'T00:00:00');
      funcDate.setDate(funcDate.getDate()+1); // día siguiente
      if(today>=funcDate) return false;
    }
    // ── Un aviso se muestra si INTERSECTA con lo que hay en pantalla ──────────
    // (regla de Juan, 12 ago 2026.) Filtrando BOGOTÁ —donde FICDEH no canceló
    // nada— el banner seguía hablando de las 4 ciudades del sismo: no es ruido,
    // se lee como que Bogotá está afectada. Es lo contrario de informar.
    // El predicado se apoya en venueMatches, el dueño único del filtro de lugar,
    // así que vale igual para 'all', para `city:` y para una SEDE concreta — y
    // generaliza al aviso de una función suelta: si filtrás una sede donde esa
    // función no va, el aviso no aparece.
    if(activeVenue!=='all'){
      const {FILMS}=state.snapshot();
      if(!FILMS.some(f=>_noticeAfecta(n,f)&&venueMatches(f.venue,activeVenue))) return false;
    }
    return true;
  });
}

export function renderNoticesBannerHTML(state){
  const active=getActiveNotices();
  if(!active.length) return '';
  const {_lang}=state.snapshot();
  return active.map(n=>{
    const label=n.type==='cancelled'?t('notice_cancelada'):t('notice_reprogramada');
    // Aviso CON causa (note): habla el festival, con sus palabras y su enlace. Es
    // el único sitio donde se explica el porqué — las cards solo marcan CANCELADA.
    // `note` va en ES en todos los idiomas salvo que traiga note_en (mismo criterio
    // que status.note: no traducimos palabras ajenas sin aprobación).
    if(n.note){
      const _esc=s=>String(s||'').replace(/&/g,'&amp;');
      const _txt=(_lang!=='es'&&n.note_en)||n.note;
      return`<div class="notice-banner">
      <div class="notice-banner-dot"></div>
      <div class="notice-banner-body">
        <div class="notice-banner-label">${label}</div>
        <div class="notice-banner-text">${_txt}${n.url?`<br><a class="fest-postponed-link" href="${_esc(n.url)}" target="_blank" rel="noopener">${t('notice_link')}</a>`:''}</div>
      </div>
      <button class="notice-banner-close" data-action="dismissNotice" aria-label="${t('misc_cerrar')}" data-title="${noticeId(n).replace(/"/g,'&quot;')}">✕</button>
    </div>`;
    }
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
      <button class="notice-banner-close" data-action="dismissNotice" aria-label="${t('misc_cerrar')}" data-title="${n.title.replace(/"/g,'&quot;')}">✕</button>
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

// ── vacioDelDia — dueño único del vacío de un día ────────────────────────────
// TRES vacíos, y decirlos igual es mentir (Juan 24 ago, ampliado 30 ago): sin
// filtros el día vacío es programación que no existe; con SOLO la ciudad
// —contexto, no un filtro que el usuario fue a buscar— culpar a «sección o
// sede» le manda a arreglar dos controles que nunca tocó; con sección o sede
// puestas el filtro sí esconde y el aviso es correcto.
function vacioDelDia(){
  if(activeVenue==='all'&&activeSec==='all')
    return emptyState(ICONS.calendar, t('dia_sin_funciones'), t('dia_sin_funciones_sub'));
  if(activeSec==='all'&&isCitySel(activeVenue))
    return emptyState(ICONS.calendar,
      t('dia_sin_funciones_ciudad',{city:venueSelLabel(activeVenue)}),
      t('dia_sin_funciones_ciudad_sub'));
  return emptyState(ICONS.search, t('filter_sin_actividades'), t('empty_filtros'));
}

export function renderProgramaListHTML(state){
  try{
  const {FILMS, _activeFestId, watchlist} = state.snapshot();
  let films=FILMS.filter(f=>f.day===activeDay);
  if(activeVenue!=='all') films=films.filter(f=>venueMatches(f.venue,activeVenue));
  if(activeSec!=='all') films=films.filter(f=>f.section===activeSec);
  films.sort((a,b)=>{
    const td=toMin(a.time)-toMin(b.time);
    if(td!==0) return td;
    const cat=f=>f.type==='event'?2:f.is_cortos?1:0;
    return cat(a)-cat(b);
  });
  if(!films.length) return vacioDelDia();
  const byTime={};
  films.forEach(f=>{if(!byTime[f.time])byTime[f.time]=[];byTime[f.time].push(f);});
  return Object.entries(byTime).map(([time,fs])=>`
    <div class="plist-time-hdr">${time}</div>
    ${fs.map(f=>{
      const inWL=watchlist.has(f.title);
      const passed=screeningPassed(f);
      const isNow=isNowShowing(f);
      const isQa=isNow&&isQaOnlyNow(f);

      const _isPrograma=f.is_programa&&f.film_list&&f.film_list.length>=2;
      const{displayTitle:_rawDt}=parseProgramTitle(f.title);
      const dt=_isPrograma
        ?(_rawDt+'<span class="film-count-badge">+1</span>')
        :_rawDt;
      const vc=vcfg(f.venue);
      const src=getFilmPoster(f)||'';
      // EL PUNTO DICE CUÁNDO, EL BADGE DICE QUÉ (decisión de Juan, 18 ago, vía
      // Onboarding: el badge de estado «Q&A» quedaba pegado al informativo «Q&A»
      // de _metaBadges — la fila decía lo mismo dos veces). El punto verde
      // .live-dot —el mismo que marca «en curso» en el splash— es el marcador de
      // ahora en las FILAS: tras el título si corre la película, tras el badge
      // Q&A si corre la charla. Siempre FUERA del badge. La píldora AHORA
      // sobrevive solo sobre el PÓSTER (abajo), donde un punto de 7px se pierde
      // contra el afiche. El aria-label sostiene lo que el color no comunica.
      const nowDot=isNow&&!isQa
        ?`<span class="live-dot row-dot" role="img" aria-label="${t('aria_en_curso')}"></span>`
        :'';
      const qaDot=isQa
        ?`<span class="live-dot row-dot" role="img" aria-label="${t('aria_qa_en_curso')}"></span>`
        :'';
      // El dato viene SELLADO en la función por el loader (_cancelled/_movedFrom):
      // el listado ya no busca en NOTICES. Y para una movida, la hora que muestra la
      // card ES la nueva — el detalle "pasa a…" quedó redundante y se retiró.
      const noticeBadge=f._cancelled?`<span class="notice-badge">${t('notice_cancelada')}</span>`
        :f._movedFrom?`<span class="notice-badge">${t('notice_reprog_short')}</span>`:'';
      // «Pendiente nueva fecha» SOLO si el aviso no explicó la causa (ver loader).
      const noticeNote=(f._cancelled&&!f._cancelExplained)?`<div class="notice-detail-amber">${t('plan_fecha_pendiente')}</div>`:'';
      // Cancelada salió del difuminado (Juan, 21 ago 2026): acá se apilaba con el
      // de «ya pasó» y una función caída y vieja quedaba al 22% — ilegible, y
      // diciendo dos veces lo mismo con el mismo recurso. Ahora la fila cancelada
      // se dice en gris (`.plist-item.is-cancelled`), y le siguen respondiendo el
      // badge y el tachado de la meta, que sí son señales propias suyas.
      const itemStyle=passed&&!isNow&&!festivalEnded()?'opacity:.45':'';
      const safeT=f.title.replace(/"/g,'&quot;').replace(/'/g,"&#39;");
      const _stk=_programaStack(f);
      return`<div class="plist-item js-open-pel${f._cancelled?' is-cancelled':''}" style="${itemStyle}" data-title="${escXML(f.title)}">
        ${_stk||_plistPosterHtml(f,src)}
        <div class="plist-info">
          <div class="plist-title">${noticeBadge}<span class="plist-title-txt">${dt}</span>${nowDot}${_metaBadges(f)}${qaDot}</div>
          <div class="plist-meta" style="${f._cancelled?'text-decoration:line-through':''}">${vc.short}${sala(f.venue)?' · '+sala(f.venue):''}${venueCity(f.venue)?` · <span class="plist-city">${venueCity(f.venue)}</span>`:''}${f.duration?' · '+durFmt(f.duration):''}</div>
          ${noticeNote||`<div class="plist-sec">${_secLabelFull(f.section||'')}</div>`}
        </div>
        <div class="plist-heart${inWL?'':' empty'}" data-title="${f.title.replace(/"/g,'&quot;')}" data-action="toggleWLFromList" data-stop="1">${inWL?ICONS.heartFill:ICONS.heart}</div>
      </div>`;
    }).join('')}
  `).join('');
  }catch(e){return `<div class="pad-muted">${t('error_funciones')}</div>`;}
}

// scrollDtabsToActive — DUEÑO ÚNICO del scroll de la barra de días. Regla de
// Juan (18 ago): al abrir Programa, HOY y MAÑANA se ven sin navegar — el día
// siguiente no puede vivir escondido en la navegación. La fórmula vieja
// (activo pegado al borde izquierdo) vivía copiada en 3 sitios y con festivales
// largos dejaba mañana fuera de cuadro: medido en AFF (10 días) — hoy visible,
// mañana cortado; en Tribeca (12 días) ninguno de los dos.
export function scrollDtabsToActive(){
  const dt=document.getElementById('dtabs');
  if(!dt) return;
  const on=dt.querySelector('.dtab.on');
  if(!on) return;
  const tabs=[...dt.querySelectorAll('.dtab')];
  const next=tabs[tabs.indexOf(on)+1]||null;
  // El objetivo es el PAR (hoy + mañana); sin mañana (último día), solo hoy.
  const left=on.offsetLeft-dt.offsetLeft;
  const right=((next||on).offsetLeft-dt.offsetLeft)+(next||on).offsetWidth;
  const max=Math.max(0,dt.scrollWidth-dt.clientWidth);
  // Si el par no cabe entero, manda HOY (el día siguiente asoma lo que pueda).
  const target=(right-left>dt.clientWidth)?left:Math.min(left,Math.max(0,right-dt.clientWidth));
  dt.scrollLeft=Math.max(0,Math.min(max,target));
}

export function _renderProgramaContent(resetScroll=false){
  // resetScroll: true solo en navegación (cambio de día/filtro/vista). En re-renders
  // por estado (toggle WL/prio, sync nube) queda false → preserva el scroll del usuario.
  const grid=document.getElementById('grid');
  const lista=document.getElementById('programa-list');
  const cntEl=document.getElementById('cnt');
  if(!grid||!lista) return;
  renderNoticesBanner();
  // ── El palmarés vive en PROGRAMA, encima de la cartelera ────────────────
  // Acá y no en Mi Plan: Mi Plan es TUYO —lo que planeaste, lo que viste— y el
  // palmarés es del FESTIVAL. Juan pidió que lo viera cualquiera que abra el
  // festival, haya usado o no la app, y a Mi Plan solo entra quien tiene algo
  // suyo adentro. En PROGRAMA cae todo el mundo.
  // Solo con el festival terminado: mientras corre, la cartelera es la noticia.
  // Solo en TODO: un día concreto es una pregunta de horarios, no de premios.
  const _palm=document.getElementById('palmares-slot');
  if(_palm){
    const _hay=festivalEnded()&&activeDay==='all'&&palmaresDe(state.get('_activeFestId'));
    _palm.innerHTML=_hay?renderPalmaresBandHTML(state.get('_activeFestId')):'';
  }
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
      if(s.screenings&&s.screenings.length) return s.screenings.some(sc=>venueMatches(sc.venue,activeVenue));
      return venueMatches(s.venue,activeVenue);
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
        ${(()=>{const nb=f._cancelled?`<span class="notice-badge">${t('notice_cancelada')}</span>`:f._movedFrom?`<span class="notice-badge">${t('notice_reprog_short')}</span>`:'';const nn=(f._cancelled&&!f._cancelExplained)?`<div class="notice-detail-amber">${t('plan_fecha_pendiente')}</div>`:'';const n=f._cancelled?{type:'cancelled'}:null;return`<div class="plist-title" style="${allPast?'opacity:.5':''}">${nb}${dt}</div><div class="plist-meta" style="${n&&n.type==='cancelled'?'text-decoration:line-through':''}${allPast?';opacity:.5':''}">${daysHtml?`${daysHtml} · `:''}${durFmt(f.duration)}${_metaBadges(f)?` · ${_metaBadges(f)}`:''}</div>${nn||`<div class="plist-sec">${_secLabelFull(f.section||'')}</div>`}`;})()}
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
  // El REPRESENTANTE de cada obra —el que fija su posición en el grid— es su
  // función más temprana, pero IGNORANDO los pases de prensa. Sin esto, activar
  // Prensa e Industria reordenaba el catálogo sin añadirle una sola tarjeta:
  // ninguna obra existe solo en prensa (las 226 tienen función pública), y los
  // pases son mucho más tempranos que las funciones públicas —en TIFF prensa
  // arranca con 61 el 10 SEP contra 14 públicas—, así que el pase pasaba a ser
  // el más temprano y la obra saltaba de sitio. Mismas tarjetas, otro orden:
  // confuso justo cuando el usuario busca ver QUÉ SE AÑADIÓ. Lo levantó Juan.
  //
  // El grid es un catálogo de OBRAS; el interruptor filtra FUNCIONES. Que la
  // obra se ancle a su función pública mantiene el catálogo quieto, y las
  // funciones añadidas se ven donde son la unidad: la vista Lista.
  const _rank=f=>(f.audience==='press'?1:0);   // público primero, siempre
  const _min=f=>(f.day_order||0)*1440+toMin(f.time||'00:00');
  _dayFilms.forEach(f=>{
    if(!titleMap[f.title]){titleMap[f.title]={film:f,screenings:[]};}
    else{
      const cur=titleMap[f.title].film;
      // Una pública SIEMPRE gana a un pase de prensa; entre iguales, la más
      // temprana. Si la obra solo tuviera pases (hoy no pasa en TIFF), el
      // primero que llegue sigue siendo su representante y nada se rompe.
      const dr=_rank(f)-_rank(cur);
      if(dr<0||(dr===0&&_min(f)<_min(cur))) titleMap[f.title].film=f;
    }
    titleMap[f.title].screenings.push(f);
  });
  let entries=Object.values(titleMap);
  if(activeSec!=='all'){
    entries=entries.filter(e=>e.film.section===activeSec);
  }
  if(activeVenue!=='all'){
    entries=entries.filter(e=>e.screenings.some(s=>{
      if(s.screenings&&s.screenings.length) return s.screenings.some(sc=>venueMatches(sc.venue,activeVenue));
      return venueMatches(s.venue,activeVenue);
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
    // La marca aparece SOLO cuando es verdad para TODA la obra (regla de Juan,
    // 11 ago 2026). En FICDEH tras el sismo: de 116 obras, 10 quedaron sin ninguna
    // función viva y 39 son PARCIALES —«La gran hazaña» tiene 4 canceladas y 12
    // activas—. Marcar las 39 sería falso y empujaría a descartar películas que sí
    // se pueden ver; su cancelación se ve donde el usuario decide a qué ir: la
    // ficha y la vista por día. Aquí la card es la OBRA, no la función.
    const allCancelled=screenings.length>0&&screenings.every(s=>s._cancelled);
    const posterSrc=getFilmPoster(f);
    const safeT=f.title.replace(/"/g,'&quot;').replace(/'/g,"&#39;");
    const{displayTitle}=parseProgramTitle(f.title);
    const progBadge='';//REMOVED: no count badge
    const _ended=festivalEnded();
    // LA ESCALERA — 2-3 obras, todas con afiche REAL (POSTERS.md, Juan 21 ago).
    // Se pregunta ANTES que nada: es la decisión de más alto rango para una
    // función que agrupa obras, y su modelo ya sabe decir que no. Devuelve null
    // si falta un afiche, si alguno es un still nuestro (Forma B) o si son 4+;
    // ahí siguen mandando los caminos de siempre y no se toca nada.
    //
    // Lo que gana el grid: las funciones de cortos de 2-3 obras caían al
    // generativo con los dos afiches guardados (31 en el catálogo), y los
    // programas legacy mostraban `poster-card-stack`, dos mitades a 50/50 que
    // recortan cada afiche a una tira y le parten la tipografía. La Escalera
    // los muestra ENTEROS y solapados.
    const _esc=programParts(f);
    const _isPrograma=!_esc&&f.is_programa&&f.film_list&&f.film_list.length>=2;
    let posterImg,_cardBg='',_edAccent='';
    if(_esc){
      // El SVG va INLINE, no como src de un <img>: sus módulos son <image href>
      // remotos y un SVG dentro de <img> no carga recursos externos — saldría en
      // negro. Es el mismo camino que ya usa el Diario (`.dw-svg`).
      posterImg=`<div class="img-cover poster-esc">${_esc.svg}</div>`;
    } else if(_isPrograma){
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
      // El difuminado dice UNA sola cosa: «ya pasó». Cancelada salió de acá
      // (Juan, 21 ago 2026) y se dice en gris — ver `.poster-card.is-cancelled`
      // en index.html. Con las dos verdades compartiendo opacidad, una función
      // caída se leía como una función vieja.
      const _opacity=(allPast&&!_ended)?';opacity:.45':'';
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
    const cancBadge=allCancelled?`<div class="badge-past poster-past-badge">${t('notice_cancelada')}</div>`:'';
    return _sep+`<div class="bg-surf-2 poster-card js-open-pel${allCancelled?' is-cancelled':''}${inWL&&!inW?' in-wl':''}${inW&&!_ended?' in-watched':''}${_edAccent?' poster-ed':''}" data-title="${escXML(f.title)}"${_edAccent?` style="--ed-accent:${_edAccent}"`:(_isPrograma?'':_cardBg)}>
      ${posterImg}
      ${cancBadge}
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
  if(activeVenue!=='all') films=films.filter(f=>venueMatches(f.venue,activeVenue));
  if(activeSec!=='all') films=films.filter(f=>f.section===activeSec);
  films.sort((a,b)=>toMin(a.time)-toMin(b.time));
  const cntEl=document.getElementById('cnt');
  cntEl.innerHTML=''; // count eliminado — redundante con lugar-btn y chips
  const grid=document.getElementById('grid');
  if(!films.length){grid.innerHTML=vacioDelDia();return;}
  // ── Vista horario: poster-grid 3 col + overlay de hora ──
  grid.innerHTML='<div class="poster-grid">'+films.map((f,i)=>{
    const isProg=f.is_cortos;
    const isEvent=f.type==='event';
    const passed=screeningPassed(f);
    const inWL=watchlist.has(f.title),inW=watched.has(f.title);
    const isNow=isNowShowing(f);
    const isQa=isNow&&isQaOnlyNow(f);
    const safeT=f.title.replace(/"/g,'&quot;').replace(/'/g,"&#39;");
    const posterSrc=getFilmPoster(f);
    const _cardBg2='';
    const posterImg=posterSrc
      ?`<img class="img-cover" src="${posterSrc}" loading="lazy" data-title="${f.title.replace(/"/g,'&quot;')}" onerror="_posterErr(this)" alt="">`
      :``;
    const progBadge='';//REMOVED
    const nowBadge=isNow
      ?`<div class="poster-now${isQa?' qa-only':''}">${isQa?t('label_qa_ahora'):t('misc_ahora')}</div>`
      :'';
    const pastBadge=f._cancelled?`<div class="badge-past poster-past-badge">${t('notice_cancelada')}</div>`
      :f._movedFrom?`<div class="badge-past poster-past-badge">${t('notice_reprog_short')}</div>`:'';

    const _fe=festivalEnded();
// Cancelada le GANA a pasada (Juan, 21 ago 2026): si la función no va a
    // ocurrir, que además su hora haya quedado atrás es lo de menos. Sin este
    // `&&!f._cancelled` la tarjeta llevaba las dos marcas y el difuminado de
    // «ya fue» se comía el gris de «se canceló».
return`<div class="poster-card js-open-pel${f._cancelled?' is-cancelled':''}${inWL&&!inW?' in-wl':''}${inW&&!_fe?' in-watched':''}${passed&&!_fe&&!f._cancelled?' past-card':''}" data-title="${escXML(f.title)}"${_cardBg2}>
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


// ── PALMARÉS ────────────────────────────────────────────────────────────────
// Superficie del FESTIVAL, no del usuario (decisión de Juan, 23 ago 2026): la ve
// cualquiera que abra el festival terminado, haya usado o no la app. Lo personal
// —cuántas ganadoras viste, tu calificación sobre el afiche— se SUMA encima
// cuando hay diario, y su ausencia no deja hueco.
//
// Todo lleva afiche, menciones incluidas. Una premiada que no está en el
// catálogo NO se dibuja como una casilla vacía: nace con su afiche propio
// (Forma A, POSTERS.md §6.0), que es la respuesta que la app ya da a cualquier
// obra sin póster. Así el palmarés no hereda los huecos del catálogo.
export function palmaresDe(festId){
  const rows=PALMARES.filter(p=>p.fest===festId);
  if(!rows.length) return null;
  const cats=[];
  rows.forEach(r=>{
    let c=cats.find(x=>x.categoria===r.categoria);
    if(!c){ c={categoria:r.categoria, ganadoras:[], menciones:[]}; cats.push(c); }
    (r.nivel==='ganadora'?c.ganadoras:c.menciones).push(r);
  });
  return cats;
}

// Una premiada se busca en el catálogo ENTERO: primero como obra de nivel
// superior y, si no, DENTRO de los programas de cortos. Un corto premiado tiene
// su propia ficha (openCortoSheet) igual que cualquier obra — no hay razón para
// que el palmarés lo trate distinto por venir envuelto en un programa. Lo
// levantó Juan el 24 ago: «para eso existe la ficha independiente por película o
// cortometraje, sin discriminación». Antes devolvíamos null y caían a Forma A,
// que es el respaldo para lo que NO tenemos, no para lo que sí.
export function _palmBuscar(titulo){
  if(!titulo) return null;
  const {FILMS}=state.snapshot();
  const f=FILMS.find(x=>x.title===titulo);
  if(f) return {tipo:'film', film:f};
  for(const p of FILMS){
    const c=(p.film_list||[]).find(x=>x&&x.title===titulo);
    if(c) return {tipo:'corto', corto:c, programa:p};
  }
  return null;
}

function _palmPoster(entry, accent, tira){
  const {watched, filmRatings}=state.snapshot();
  const _h=entry.obra?_palmBuscar(entry.obra):null;
  const f=_h?(_h.tipo==='film'?_h.film:_h.corto):null;
  // Prioridad: afiche de la obra en el catálogo → afiche propio de la entrada del
  // palmarés (una premiada que no tenemos pero cuyo póster oficial sí existe) →
  // Forma A. La Forma A es el último recurso, no el primero.
  const src=(_h?(_h.tipo==='film'?getFilmPoster(_h.film):_getItemPoster(_h.corto)):null)||entry.poster||null;
  // Sin obra en el catálogo → afiche propio. El rótulo dice QUÉ es, no de qué
  // sección: «PROYECTO» para lo de ImpulsoLab, la categoría para una obra.
  const inner=src
    ? `<img class="img-cover" src="${src}" loading="lazy" onerror="_posterErr(this)" alt="">`
    // SIN rótulo de sección. A 76px —y peor a 52— el rótulo de la Forma A no
    // informa: ocupa media tarjeta y compite con el título. Acá además sería
    // redundante, porque la categoría ya está escrita ARRIBA de la fila, a dos
    // centímetros. Queda el filete de color y la luz: el afiche se lee como
    // pieza nuestra sin gritar de qué sección es.
    : `<img class="img-cover" src="${_buildPosterV16({accent, headerLabel:'', title:entry.titulo, num:null, dato:''})}" alt="">`;
  const vista=entry.obra&&watched.has(entry.obra);
  const r=vista?(filmRatings[entry.obra]||0):0;
  const estrellas=r?`<div class="palm-seen">${'★'.repeat(Math.floor(r))}${r%1>=0.5?'½':''}</div>`:'';
  // Sin marca «afiche nuestro» (Juan, 24 ago 2026). Nació cuando toda premiada
  // sin ficha caía en Forma A y eran varias; hoy queda UNA —«Eliza», un proyecto
  // de ImpulsoLab que no tiene afiche en ninguna parte— y no hay original con el
  // que confundirla. Protegía de una confusión que ya no existe, y tapaba el
  // afiche.
  // La marca va SOLO en la ganadora: lo que no la lleva es mención. Un signo en
  // vez de dieciséis rótulos —ocho «Ganadora» y ocho «Menciones»—, que era lo
  // que Juan llamó repetitivo. Anclada con --poster-badge-top, el token que
  // salió del bug del badge de cancelada: arriba chocaría con el rótulo de la
  // Forma A, y ese error ya lo cometí hoy dos veces.
  // Sin medalla sobre el afiche (Juan, 23 ago 2026): tapaba el dibujo —caía sobre
  // una cara en «El verano de Jahia» y sobre el título en «Hija del volcán»— y
  // marcaba lo que ya era obvio. Lo ambiguo no era cuál gana, sino qué son las
  // pequeñas de la derecha; eso lo dice ahora el divisor.
  const laurel='';
  return `<div class="palm-po">${inner}${laurel}${estrellas}</div>`;
}

export function renderPalmaresBandHTML(festId){
  // REPLEGADO, como el Diario (Juan, 23 ago 2026): la primera versión desplegaba
  // el palmarés entero encima de la cartelera y había que navegar media pantalla
  // para llegar al programa. La banda + la tira ocupan ~110px y cuentan lo mismo:
  // que hay palmarés, cuántas ganadoras, y con qué cara. El detalle vive en su
  // sheet, que es el patrón que la app ya enseñó con el Diario.
  const cats=palmaresDe(festId);
  if(!cats) return '';
  const gan=cats.flatMap(c=>c.ganadoras);
  const MAX=6;
  const tira=gan.slice(0,MAX).map((g,i)=>{
    const acc=_sectionColor(g.categoria);
    return `<div class="palm-strip-p" style="${i?'margin-left:-20px;':''}z-index:${MAX-i}">${_palmPoster(g,acc,true)}</div>`;
  }).join('');
  const resto=gan.length>MAX?`<span class="dw-strip-mas">+${gan.length-MAX}</span>`:'';
  return `<div class="palm-wrap">
    <div class="sec-hdr palm-band" data-action="openPalmares">${ICONS.award} <span>${t('palm_eyebrow')}</span> <span class="count-badge cb-neutral">${gan.length}</span><span class="hdr-end">${ICONS.chevronR}</span></div>
    <div class="palm-strip" data-action="openPalmares">${tira}${resto}</div>
  </div>`;
}

export function renderPalmaresHTML(festId){
  const cats=palmaresDe(festId);
  if(!cats) return '';
  const {watched}=state.snapshot();
  const gan=cats.flatMap(c=>c.ganadoras);
  const vistas=gan.filter(g=>g.obra&&watched.has(g.obra)).length;
  const cruce=vistas
    ? `<div class="palm-cruce dato-linea">${t('palm_viste').replace('{n}',`<b>${vistas}</b>`).replace('{tot}',`<b>${gan.length}</b>`)}</div>`
    : '';
  // UNA fila por categoría: la ganadora grande a la izquierda, las menciones
  // pequeñas a la derecha. El chip «Ganadora» y el rótulo «Menciones de honor»
  // se retiraron (Juan, 23 ago 2026): repetían dieciséis veces —ocho y ocho— una
  // estructura que es siempre la misma, y el tamaño ya la dice. Se explica UNA
  // vez en la cabecera del sheet. De paso la altura por categoría cae a la mitad,
  // que era la otra queja: demasiado scroll.
  const secs=cats.map(c=>{
    const acc=_sectionColor(c.categoria);
    // `_palmAbrir` decide la ficha: la de película o la del CORTO. Antes esto
    // era `js-open-pel` a secas y un corto premiado no tenía a dónde llevar.
    // Qué ficha abre cada premiada: la de película, o la del CORTO si viene
    // dentro de un programa. Un corto premiado tiene ficha propia igual que
    // cualquier obra (openCortoSheet) — el palmarés no lo trata distinto por
    // venir envuelto. Sin obra en el catálogo, la tarjeta no es clicable.
    const _clic=x=>{
      const h=x.obra?_palmBuscar(x.obra):null;
      if(!h) return '';
      const cls=h.tipo==='corto'?'js-open-corto':'js-open-pel';
      return ` ${cls}" data-title="${escXML(x.obra)}`;
    };
    const g=c.ganadoras.map(x=>`
      <div class="palm-g${_clic(x)}">
        ${_palmPoster(x,acc)}
        <div class="palm-wtx">
          ${x.premio?`<div class="palm-premio">${escXML(x.premio)}</div>`:''}
          <div class="palm-wt">${escXML(x.titulo)}</div>
          <div class="palm-wm dato-linea">${escXML(x.autoria||'')}</div></div>
      </div>`).join('');
    const m=c.menciones.map(x=>`
      <div class="palm-m${_clic(x)}" title="${escXML((x.premio?x.premio+' · ':'')+x.titulo)}">${_palmPoster(x,acc,true)}</div>`).join('');
    return `<section class="palm-sec">
      <div class="palm-cat" style="--c:${acc}"><span></span>${escXML(c.categoria)}</div>
      ${g}${c.menciones.length?`<div class="palm-row palm-mrow2"><span class="splash-rail-div palm-div-v" aria-hidden="true"><span class="srd-bar"></span><span class="srd-lbl">${t('palm_mencion_corto')}</span><span class="srd-bar"></span></span><div class="palm-ms">${m}</div></div>`:''}</section>`;
  }).join('');
  return cruce+secs;
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
  if(activeVenue!=='all') dayF=dayF.filter(f=>venueMatches(f.venue,activeVenue));
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
