// ══ State — variables, persistence, mplan calendar ══
// SOURCE: index.html L2876-3297

// ═══════════════════════════════════════════════════════════════
// 5 · ESTADO GLOBAL
//     watchlist, watched, prioritized, savedAgenda, availability
// ═══════════════════════════════════════════════════════════════
// ── STATE ──
let watchlist=new Set();
let filmRatings={}; // {title: 0.5..5} medias estrellas Letterboxd-style
let watched=new Set();
let prioritized=new Set();
let PRIO_LIMIT=5; // Updated by loadFestival per festival
/* ── Clave de almacenamiento — cambiar por edición del festival ──
   Formato: {nombre}{año}_ → prefija todas las keys de localStorage.
   Garantiza que cada edición empiece limpia sin datos residuales. */
let FESTIVAL_STORAGE_KEY='ficci65_';
// ── Reset agresivo de caché — independiente del SW ────────────────
// BUILD_VERSION: cambia en cada deploy.
// Al cargar, compara con localStorage. Si difiere → reload duro.
// sessionStorage evita loops infinitos dentro de la misma sesión.
const BUILD_VERSION='202604211937';
(function(){
  const _vk='otrofestiv_build';
  const _sk='otrofestiv_reloaded';
  const _stored=localStorage.getItem(_vk);
  const _reloaded=sessionStorage.getItem(_sk);
  // Solo recargar si el usuario ya eligió un festival (no interrumpir primera visita)
  const _splashSeen=localStorage.getItem('otrofestiv_festival');
  if(_stored && _stored!==BUILD_VERSION && !_reloaded && _splashSeen){
    sessionStorage.setItem(_sk,'1');
    localStorage.setItem(_vk,BUILD_VERSION);
    location.reload(true);
    return;
  }
  sessionStorage.removeItem(_sk);
  localStorage.setItem(_vk,BUILD_VERSION);
})();

/* ── GLOSARIO DE TÉRMINOS USER-FACING ────────────────────────────
   Validar con usuarios reales antes de cada edición del festival.
   Regla: si un asistente al festival no usaría la palabra
   naturalmente, cambiarla antes de codificarla.

   TÉRMINO          USO EN LA APP           EVITAR
   ──────────────────────────────────────────────────
   Intereses        colección personal      Mi Lista, Selección, Watchlist
   Mi Plan          agenda generada         Agenda, Calendario
   Planear          tab de generación       Algoritmo, Cálculo
   Opciones         resultados del alg.     Escenarios, Variantes
   Prioridad        ★ película destacada    Favorita, Top
   Disponibilidad   bloques de tiempo libre Horario, Agenda libre
   Añadir           acción de ♥             Guardar, Seleccionar
   Elegir           confirmar un plan       Guardar, Aceptar
   ────────────────────────────────────────────────── */
const FESTIVAL_BUFFER=15; // min entre funciones: salida sala + intro siguiente
let savedAgenda=null;
let lastRemovedSlots=[]; // tracks up to 5 recently removed films
const MAX_REMEMBERED_SLOTS=5;
let activeMiPlanDay=null;
let _ctaRemovedVisible=false; // CTA B: post-eliminación
let _ctaRemovedTimer=null;    // CTA B: timer de auto-dismiss
let filmDelays={};            // retrasos manuales: key=title|day|time, val=mins
// ── Simulation clock (dev tool) ──
let _simTime=null; // null = real time
function simNow(){return _simTime?new Date(_simTime):new Date();}
function simTodayStr(){
  // Usa fecha LOCAL (no UTC) para consistencia con getHours()/getMinutes()
  // toISOString() devuelve UTC — en Colombia (UTC-5) esto da el día siguiente
  // después de las 7 PM, causando que la línea "ahora" aparezca en el día incorrecto
  const d=simNow();
  return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');
}
let miPlanViewStart=0; // 0-4, step 1, shows 2 days
// ─────────────────────────────────────────────────────────────────────────────
// ⚠️  FIX CRÍTICO — NO REMOVER (Apr 2026)
// availability debe inicializarse aquí con los 6 días del festival.
// Sin esta inicialización, Planear lanza TypeError al acceder a
// availability[day].blocks y la pestaña no renderiza.
// ─────────────────────────────────────────────────────────────────────────────
let availability={
  'Martes':{blocks:[]},'Miércoles':{blocks:[]},'Jueves':{blocks:[]},
  'Viernes':{blocks:[]},'Sábado':{blocks:[]},'Domingo':{blocks:[]}
};

const MPLAN_START_H=10,MPLAN_END_H=24;
const MPLAN_TOTAL_MINS=(MPLAN_END_H-MPLAN_START_H)*60;
const MPLAN_PX_PER_MIN=52/60;
const MPLAN_DETAIL_H=MPLAN_TOTAL_MINS*MPLAN_PX_PER_MIN;


// ═══════════════════════════════════════════════════════════════
// 6 · MI PLAN — HELPERS & RENDER
//     mplanPx, mplanPct, renderMiPlanCalendar, selectMiPlanDay
// ═══════════════════════════════════════════════════════════════
function mplanPx(min){return(min-MPLAN_START_H*60)*MPLAN_PX_PER_MIN;}
function mplanPct(min){return((min-MPLAN_START_H*60)/MPLAN_TOTAL_MINS*100);}
function mplanEndStr(t,d){const m=toMin(t)+d;return String(Math.floor(m/60)%24).padStart(2,'0')+':'+String(m%60).padStart(2,'0');}

function mplanBlockType(s){
  if(prioritized.has(s._title)) return'mp-priority';
  const f=FILMS.find(fi=>fi.title===s._title);
  if(f&&f.is_cortos) return'mp-program';
  return'mp-regular';
}


// REGLA: scroll a mplan-detail — mide el topbar directamente del DOM,
// no depende de --tb-total (incorrecto en mobile por incluir nav inferior).
// Usar esta función en TODOS los contextos que necesiten bajar al detalle.
function _scrollToMplanDetail(){
  const el=document.getElementById('mplan-detail');
  if(!el) return;
  const tb=document.querySelector('.topbar');
  const tbH=tb?Math.ceil(tb.getBoundingClientRect().height):86;
  window.scrollTo({top:Math.max(0,el.getBoundingClientRect().top+window.scrollY-tbH-8),behavior:'smooth'});
}

function selectMiPlanDay(idx){
  activeMiPlanDay=idx;
  if(idx<miPlanViewStart||idx>=miPlanViewStart+2) miPlanViewStart=Math.min(idx,DAY_KEYS.length-2);
  renderAgenda();
  // Scroll to detail section below calendar
  setTimeout(()=>{
    _scrollToMplanDetail();
  },80);
}
function miPlanNav(dir){
  miPlanViewStart=Math.max(0,Math.min(DAY_KEYS.length-2,miPlanViewStart+dir));
  if(activeMiPlanDay<miPlanViewStart||activeMiPlanDay>=miPlanViewStart+2) activeMiPlanDay=miPlanViewStart;
  renderAgenda();
}

function renderMiPlanCalendar(){
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

  // REGLA: rango dinámico — calcular desde las funciones reales del plan.
  // Buffer de 45min antes del inicio y después del final, snapped a hora entera.
  // Límites absolutos: nunca antes de las 8:00, nunca después de las 26:00.
  const _allMins=schedule.flatMap(s=>{
    const st=toMin(s.time), en=st+parseDur(s.duration);
    return[st,en];
  });
  const _minStart=Math.min(..._allMins);
  const _maxEnd=Math.max(..._allMins);
  const SH=Math.max(8, Math.floor((_minStart-30)/60));
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
  const vs=miPlanViewStart;
  const ve=vs+1; // show days vs and ve (2 days)
  // En overview: no paginador
  const lbl1=dayLabel(DAY_KEYS[vs]); // 'MIÉ 15'
  const lbl2=dayLabel(DAY_KEYS[ve]); // 'MIÉ 15'
  const isPastVs=nowDayIdx>=0&&vs<nowDayIdx;
  const isPastVe=nowDayIdx>=0&&ve<nowDayIdx;
  const navHtml=`<div class="mplan-nav">
    <div class="mplan-nav-btn-wrap">
      <button class="mplan-nav-btn" aria-label="Día anterior" onclick="miPlanNav(-1)" ${vs===0?'disabled':''}>◀</button>
    </div>
    <div class="mplan-nav-labels">
      <div class="mplan-nav-day${isPastVs?' past':''}" onclick="selectMiPlanDay(${vs})">
        <div class="mplan-nav-day-name">${DAYS[vs].lbl}</div>
        <div class="mplan-nav-day-num${vs===activeMiPlanDay?' wk-active-num':''}">${DAYS[vs].d}</div>
      </div>
      <div class="mplan-nav-day${isPastVe?' past':''}" onclick="selectMiPlanDay(${ve})">
        <div class="mplan-nav-day-name">${DAYS[ve].lbl}</div>
        <div class="mplan-nav-day-num${ve===activeMiPlanDay?' wk-active-num':''}">${DAYS[ve].d}</div>
      </div>
    </div>
    <div class="mplan-nav-btn-wrap right">
      <button class="mplan-nav-btn" onclick="miPlanNav(1)" ${ve>=DAY_KEYS.length-1?'disabled':''}>${ICONS.chevronR}</button>
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
      const showVenue=blockH>44;
      const vc2=vcfg(s.venue);
      return`<div class="mplan-wk-block ${type}${stateClass}" style="top:${top.toFixed(0)}px;height:${blockH.toFixed(0)}px" data-fkey="${(s._title||'')}${s.time}" onclick="setActivePlanFilm(this);selectMiPlanDay(${i});event.stopPropagation()" title="${(s._title||'').replace(/"/g,'&quot;')}">
        ${isPrio?`<div class="mplan-wk-badge">${ICONS.star}</div>`:''}
        <div class="mplan-wk-time">${s.time}</div>
        <div class="mplan-wk-title">${displayTitle}</div>
        ${showVenue?`<div class="mplan-wk-venue">${ICONS.pin} ${vc2.short}</div>`:''}
      </div>`;
    }).join('');

    const colClass=['mplan-wk-col',isToday?'wk-today':'',isActive?'wk-active':'',extraClass].filter(Boolean).join(' ');
    return`<div class="${colClass}" style="height:${PHDR+TOTAL}px" onclick="selectMiPlanDay(${i})">
      <div class="mplan-wk-col-hdr">
        <div class="mplan-wk-col-day"><span class="mplan-wk-day-name">${DAYS[i].lbl}</span><span class="mplan-wk-col-date${dayFilms.length?' wk-has':''}">${DAYS[i].d}</span></div>
        ${dayFilms.length?'<div class="mplan-wk-col-dot"></div>':''}
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

  let listHtml=`<div class="mplan-list" id="mplan-detail"><div class="mplan-list-hdr">${dayChip(activeKey)}</div>`;
  if(!dayFilms.length){
    if(!isPastDay){
      // CTA C: día futuro sin películas — invita a explorar sugerencias o recalcular
      listHtml+=`<div class="cta-ctx cta-ctx-c" onclick="document.querySelector('.suggestion-wrap')?.scrollIntoView({behavior:'smooth',block:'start'})">
        <div class="cta-ctx-ico">${ICONS.calendar}</div>
        <div class="cta-ctx-body">
          <div class="cta-ctx-title cta-ctx-title-c">Día libre en tu plan</div>
          <div class="cta-ctx-sub">No hay funciones para este día. Añade desde Sugerencias abajo, o recalcula en Planear.</div>
        </div>
        <div class="cta-ctx-arr cta-ctx-arr-c">${ICONS.chevronD}</div>
      </div>`;
    } else {
      listHtml+=`<div class="mplan-empty">Nada en tu plan este día</div>`;
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
        if(gap>=0&&gap<25) listHtml+=`<div class="mplan-warn-row">\u25b2 ~${gap} min hasta la siguiente</div>`;
        if(prev.has_qa){const qaGap=gap-30;qaGap<0?listHtml+=`<div class="mplan-warn-row" style="color:var(--red)">Q&A · si te quedas no llegas a la siguiente</div>`:listHtml+=`<div class="mplan-warn-row" style="color:var(--amber)">Q&A · si te quedas tienes ~${qaGap} min</div>`;}
        const tw=travelWarn(prev,s);
        if(tw) listHtml+=`<div class="mplan-warn-row">${tw}</div>`;
      }
      const _rowKey=(s._title||'')+s.time;
      const _safeRowKey=_rowKey.replace(/"/g,'&quot;');
      const _mf=FILMS.find(fi=>fi.title===s._title);const _mp=_mf?getFilmPoster(_mf):null;
      const _safeMpT=(s._title||"").replace(/'/g,"\'");
      const _mph=_mp?`<img class="lb-poster" src="${_mp}" loading="lazy" style="cursor:pointer" onclick="event.stopPropagation();openPelSheet('${_safeMpT}')" onerror="this.outerHTML='<div class=lb-poster-ph>🎬</div>'" alt="">`:'<div class="lb-poster-ph">🎬</div>';
      listHtml+=`<div class="mplan-row${_rowKey===_activeMiPlanFilm?' active':''}" style="cursor:pointer" data-rkey="${_safeRowKey}" onclick="selectFromDetail(this)">
        ${_mph}
        <div class="mplan-tc" onclick="event.stopPropagation()">
          <div class="mplan-t1${isPast?' mp-past':''}" ${!isPast?`onclick="toggleFilmAlternatives('${(s._title||'')+(s.day||'')+(s.time||'')}','${safeT}','${s.day||''}','${s.time||''}');event.stopPropagation()"`:''} title="${!isPast?'Cambiar horario':''}">${s.time}</div>
          <div class="mplan-t2">${mplanEndStr(s.time,dur)}${isNow?` <span style="color:var(--green);font-weight:var(--w-semi)">en curso</span>`:''}</div>
        </div>
        <div class="mplan-ri">
          <div>${(()=>{const{displayTitle:_dt,progSuffix:_ps}=parseProgramTitle(s._title||'');const _mfqa=FILMS.find(fi=>fi.title===s._title&&fi.day===s.day&&fi.time===s.time);const _qab=_mfqa?.has_qa?`<span class="meta-badge" style="font-size:8px;padding:1px 4px;margin-right:4px">${UI.badge.qa}</span>`:'';return`<div class="mplan-rtitle">${prioritized.has(s._title)?`<span style="color:var(--orange);margin-right:4px">${ICONS.starFill}</span>`:''} ${_qab}${_dt}</div>${_ps?`<div style="font-size:var(--t-sm);color:var(--orange);font-weight:var(--w-bold);line-height:1;margin-top:2px">${_ps}</div>`:''}`;})()} </div>
          <div class="mplan-rvenue">${ICONS.pin} ${vcfg(s.venue).short}${sala(s.venue)?' \u00b7 '+sala(s.venue):''}</div>
          ${(()=>{const _mf=FILMS.find(fi=>fi.title===s._title&&fi.day===s.day&&fi.time===s.time);if(!_mf||!_mf.is_cortos||!_mf.film_list||!_mf.film_list.length) return'';return`<button class="mplan-prog-toggle" onclick="toggleMplanProg(this,event)" style="display:inline-flex;align-items:center;gap:var(--sp-1)">${ICONS.chevronR} Programa</button>`;})()}
        </div>
        <div style="display:flex;flex-direction:column;align-items:flex-end;justify-content:center;flex-shrink:0">
          <button class="ag-fi-btn del" data-rmt="${safeT}" onclick="removeFromAgenda(this.dataset.rmt);event.stopPropagation()" style="display:inline-flex;align-items:center;justify-content:center;width:30px;height:30px;padding:0">${ICONS.x}</button>
        </div>
      </div>${_expandedFilm===(s._title||'')+(s.day||'')+(s.time||'')?`<div class="film-alts">${renderFilmAlternatives(s._title,s.day,s.time)}</div>`:''}${(()=>{const _mf=FILMS.find(fi=>fi.title===s._title&&fi.day===s.day&&fi.time===s.time);if(!_mf||!_mf.is_cortos||!_mf.film_list||!_mf.film_list.length) return'';return`<div class="mplan-prog-list">${_mf.film_list.map((item,n)=>{const _mt=getCortoItemPoster(item);const _mth=_mt?`<img src="${_mt}" class="c-film-thumb" loading="lazy" onerror="this.outerHTML='<div class=c-film-thumb-ph>🎬</div>'" alt="">`:'<div class="c-film-thumb-ph">🎬</div>';const _sc2=item.title.replace(/'/g,"\'");const _sco2=(item.country||"").replace(/'/g,"\'");const _scd2=(item.duration||"");const _scf2=countryToFlags(item.country||"");const _scs2=(_mf.section||"").replace(/'/g,"\'");return`<div class="mplan-prog-item" onclick="event.stopPropagation();openCortoSheet('${_sc2}','${_sco2}','${_scd2}','${_scs2}','${_scf2}')">${_mth}<div class="mplan-prog-num">${n+1}</div><div class="mplan-prog-title">${item.title}</div><div class="mplan-prog-dur">${item.duration}</div></div>`;}).join('')}</div>`;})()}`;
    });
  }
  listHtml+='</div>';

  return `<div class="mplan-wrap">
    ${navHtml}
    <div class="mplan-wk-outer">
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
      return`<div class="mplan-change-hint">${ICONS.clock} Toca la hora para cambiar la película</div>`;
    })()}
  </div>`
}


// ═══════════════════════════════════════════════════════════════
// 7 · PERSISTENCIA
//     loadState, saveWL, saveWatched, saveAV, saveSavedAgenda
// ═══════════════════════════════════════════════════════════════

/* ── STATE: persistencia en localStorage ────────────────────────────── */
function loadState(){
  try{
    const wl=localStorage.getItem(`${FESTIVAL_STORAGE_KEY}wl`); if(wl) watchlist=new Set(JSON.parse(wl));
    const wt=localStorage.getItem(`${FESTIVAL_STORAGE_KEY}watched`); if(wt) watched=new Set(JSON.parse(wt));
    const _rt=localStorage.getItem(`${FESTIVAL_STORAGE_KEY}ratings`); if(_rt) try{Object.assign(filmRatings,JSON.parse(_rt));}catch(e){}
    const av=localStorage.getItem(`${FESTIVAL_STORAGE_KEY}av3`); if(av){const p=JSON.parse(av);DAY_KEYS.forEach(d=>{if(p[d]) availability[d]=p[d];});}
    const sa=localStorage.getItem(`${FESTIVAL_STORAGE_KEY}saved`); if(sa) savedAgenda=JSON.parse(sa);
    // Normalizar venues viejos (ej: 'CC Bocagrande' → 'Plaza Bocagrande')
    if(savedAgenda&&savedAgenda.schedule){
      savedAgenda.schedule.forEach(s=>{
        if(s.venue) s.venue=s.venue.replace(/CC Bocagrande/g,'Plaza Bocagrande');
      });
    }
    const pr=localStorage.getItem(`${FESTIVAL_STORAGE_KEY}prio`); if(pr) prioritized=new Set(JSON.parse(pr));
    // Heal: garantiza que todo lo que está en prioritized esté en watchlist
    prioritized.forEach(t=>{if(!watchlist.has(t)){watchlist.add(t);}});
    saveWL();
    // Restore reserved slot — persists across refresh, button shows "＋ Añadir" (not "← Restaurar")
    const rs=localStorage.getItem(`${FESTIVAL_STORAGE_KEY}lastslot`);if(rs){try{const p=JSON.parse(rs);lastRemovedSlots=Array.isArray(p)?p:(p?[p]:[]);}catch(e){}}
    const fd=localStorage.getItem(`${FESTIVAL_STORAGE_KEY}delays`);if(fd){try{filmDelays=JSON.parse(fd);}catch(e){}}
    const _vm=localStorage.getItem(`${FESTIVAL_STORAGE_KEY}viewmodes`);if(_vm){try{const _v=JSON.parse(_vm);if(_v.miPlan)miPlanViewMode=_v.miPlan;if(_v.intereses)interesesViewMode=_v.intereses;}catch(e){}}
  }catch(e){}
}
function saveWL(){try{localStorage.setItem(`${FESTIVAL_STORAGE_KEY}wl`,JSON.stringify([...watchlist]));}catch(e){}_cloudSave();}
function saveWatched(){try{localStorage.setItem(`${FESTIVAL_STORAGE_KEY}watched`,JSON.stringify([...watched]));}catch(e){}_cloudSave();}
function saveRating(title,rating){
  if(rating>0) filmRatings[title]=rating; else delete filmRatings[title];
  try{localStorage.setItem(`${FESTIVAL_STORAGE_KEY}ratings`,JSON.stringify(filmRatings));}catch(e){}_cloudSave();
}
function saveAV(){try{localStorage.setItem(`${FESTIVAL_STORAGE_KEY}av3`,JSON.stringify(availability));}catch(e){}_cloudSave();}
function saveSavedAgenda(){try{localStorage.setItem(`${FESTIVAL_STORAGE_KEY}saved`,JSON.stringify(savedAgenda));}catch(e){}_cloudSave();}
function savePrio(){try{localStorage.setItem(`${FESTIVAL_STORAGE_KEY}prio`,JSON.stringify([...prioritized]));}catch(e){}_cloudSave();}
function saveLastSlot(){try{localStorage.setItem(`${FESTIVAL_STORAGE_KEY}lastslot`,JSON.stringify(lastRemovedSlots));}catch(e){}}
function saveDelays(){try{localStorage.setItem(`${FESTIVAL_STORAGE_KEY}delays`,JSON.stringify(filmDelays));}catch(e){}}
function _delayKey(s){return(s._title||s.title||'')+'|'+(s.day||'')+'|'+(s.time||'');}
function setDelay(title,day,time,addMins){
  const k=title+'|'+day+'|'+time;
  if(!filmDelays._hist) filmDelays._hist={};
  if(!filmDelays._hist[k]) filmDelays._hist[k]=[];
  filmDelays._hist[k].push(filmDelays[k]||0); // guardar valor anterior
  const newVal=Math.max(0,(filmDelays[k]||0)+addMins);
  if(newVal===0) delete filmDelays[k]; else filmDelays[k]=newVal;
  saveDelays();renderAgenda();
}
function undoDelay(title,day,time){
  const k=title+'|'+day+'|'+time;
  if(!filmDelays._hist||!filmDelays._hist[k]||!filmDelays._hist[k].length) return;
  const prev=filmDelays._hist[k].pop();
  if(prev===0) delete filmDelays[k]; else filmDelays[k]=prev;
  saveDelays();renderAgenda();
}
function clearDelay(title,day,time){
  const k=title+'|'+day+'|'+time;
  delete filmDelays[k];
  saveDelays();renderAgenda();
}
/* ── saveState — batching de localStorage ── */
function saveState(...keys){
  const all=!keys.length;
  if(all||keys.includes('wl'))      saveWL();
  if(all||keys.includes('watched')) saveWatched();
  if(all||keys.includes('prio'))    savePrio();
  if(all||keys.includes('agenda'))  saveSavedAgenda();
  if(all||keys.includes('av'))      saveAV();
  if(all||keys.includes('lastslot'))saveLastSlot();
}


function updateAgTab(){
  // Count: in watchlist, not watched, and has future screenings
  const future=[...watchlist].filter(t=>{
    if(watched.has(t)) return false;
    return FILMS.some(f=>f.title===t&&!screeningPassed(f));
  });
  const el=document.getElementById('ag-cnt');if(el) el.textContent=future.length;
  const tab=document.getElementById('agtab');if(tab) tab.classList.toggle('on',activeView==='agenda');
}


// ═══════════════════════════════════════════════════════════════
// 8 · EVENT HANDLERS — MI LISTA
//     toggleWL, toggleWatched, addFromSearch, removeFromAgenda
