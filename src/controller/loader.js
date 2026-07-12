// ── src/controller/loader.js ──────────────────────────────────────────────────────
// p8 Step 8d-4 — loadFestival + dismissSplash (festival data load + splash dismiss).
// Orquestador: carga JSON del festival → puebla roster/viewstate (vía bridge) +
// helpers (setters) → render inicial. dismissSplash llama loadFestival y revela la
// app. Sink puro (solo main.js lo importa: ACTION_REGISTRY + Object.assign + IIFE
// detección-festival). Escribe bridge globals en runtime (no eval-time).

import { FESTIVAL_CONFIG } from '../config.js';
import { DAY_ABBR, DAY_NUM, festivalShortName } from '../view/components.js';
import { DAYS, DAY_SHORT_EN, setCustomPosters, setDayShort, setDayShortEn, setPosters } from '../view/helpers.js';
import { closeFestivalSheet } from '../view/sheets.js';
import { showToast } from '../view/feedback.js';
import { _renderProgramaContent, lugarClose } from '../view/programa.js';
import { _fixStickyOffset } from '../view/agenda.js';
import { loadState, _cloudLoad, subscribePlanCloud } from './persistence.js';
import { subscribeDelaysCloud } from './delays-cloud.js';
import { _updateProgramaActiveFilter, initProgramaModeBar, showDayView, switchMainNav } from './pipeline.js';
import { seccionClose } from './overlays.js';
import { setProgramaView } from './handlers.js';
import { dayFullyPassed, simTodayStr } from '../domain/time.js';
import { normTitle, validateFilm } from '../domain/film.js';
import { state } from '../state/state.js';
import { storage } from '../storage/storage.js';
import { t } from '../i18n/i18n.js';
import { _autoResolveFestivalPosters, _renderFestivalSelector } from './festival.js';

// Fetch del JSON de festival con timeout + reintentos (AbortController).
// GitHub Pages a veces entrega los headers (200) pero el cuerpo se cuelga → el
// r.json() nunca resuelve y loadFestival queda colgado con FILMS=0: grid vacío,
// sin error ni 404 (cazado por synthetic monitoring, ~10-20% de cargas en frío).
// El timeout aborta el cuerpo colgado y reintenta. cache:'no-store' se mantiene
// (datos siempre frescos); el reintento cubre el stall transitorio del CDN.
async function _fetchFestivalJson(url, tries=3, timeoutMs=6000){
  let lastErr;
  for(let i=0;i<tries;i++){
    const ctrl=new AbortController();
    const to=setTimeout(function(){ ctrl.abort(); }, timeoutMs);
    try{
      const r=await fetch(url,{cache:'no-store',signal:ctrl.signal});
      if(!r.ok) throw new Error('HTTP '+r.status+' — '+url);
      const json=await r.json(); // bajo el mismo timeout: si el cuerpo se cuelga, aborta
      clearTimeout(to);
      return json;
    }catch(e){
      clearTimeout(to);
      lastErr=e; // reintentar salvo en el último intento
    }
  }
  throw lastErr;
}

export async function loadFestival(id){
  // Resetear filtros al cambiar festival
  activeVenue='all';activeSec='all';programaChip='all';_programaChipMatchFn=null;
  lugarClose();
  seccionClose();
  requestAnimationFrame(_fixStickyOffset); // recalculate after festival name changes topbar height
  // Si no está en FESTIVAL_CONFIG, intentar cargar config desde JSON
  if(!FESTIVAL_CONFIG[id]){
    FESTIVAL_CONFIG[id]={films:null,posters:null};
  }
  const cfg=FESTIVAL_CONFIG[id];
  if(!cfg){console.warn('Festival desconocido:',id);return;}
  // Guard: storageKey es crítico — sin él los datos van a localStorage con clave 'undefined'
  if(!cfg.storageKey){
    console.error(`[loadFestival] '${id}' no tiene storageKey en FESTIVAL_CONFIG — abortando.`);
    showToast(t('error_festival_nd'),'error');
    return false;
  }
  // ── Fase 1: cargar datos del festival desde JSON si no están en memoria ──
  if(!cfg.films){
    // Convierte festivalId a nombre de archivo: ficci65→ficci-65, aff2026→aff-2026
    const festFile=id.replace(/([a-zA-Z]+)(\d+)$/,'$1-$2');
    try{
      const _festUrl='festivals/'+festFile+'.json';
      const data=await _fetchFestivalJson(_festUrl).catch(e=>{
        // Banner de diagnóstico visible en pantalla
        const dbg=document.createElement('div');
        dbg.style.cssText='position:fixed;top:0;left:0;right:0;background:#c0392b;color:#fff;padding:14px 16px;z-index:99999;font-size:13px;font-family:monospace/* exception:debug-banner */;line-height:1.4';
        dbg.textContent='ERROR cargando festival: '+e.message;
        document.body.appendChild(dbg);
        throw e;
      });
      // ── Explosión de screenings[] → objetos planos por función ──
      // Si un film tiene screenings[], genera un objeto por función.
      // Compatibilidad total con el formato plano existente (day/time/venue).
      const exploded=[];
      (data.films||[]).forEach(f=>{
        if(Array.isArray(f.screenings)&&f.screenings.length){
          const base=Object.assign({},f);
          delete base.screenings;
          f.screenings.forEach((s,i)=>{
            exploded.push(Object.assign({},base,{
              day:s.day||s.date,date:s.date||s.day,time:s.time,venue:s.venue||'',
              day_order:s.day_order!==undefined?s.day_order:i,
              sala:s.sala||'',
              ...(s.is_free!=null?{is_free:s.is_free}:{}) // por-función (festivales mixed)
            }));
          });
        } else {
          exploded.push(f);
        }
      });
      // Duración automática para is_programa
      exploded.forEach(f=>{
        if(f.is_programa&&f.film_list&&f.film_list.length&&!f.duration){
          const mins=f.film_list.reduce((acc,item)=>{
            const m=parseInt((item.duration||"").replace(/[^0-9]/g,""))||0;
            return acc+m;
          },0);
          if(mins>0) f.duration=mins+" min";
        }
      });
      cfg.films=exploded; // Cacheado en sesión — evita re-fetch al volver al festival.
      // Límite recomendado: ≤5 festivales simultáneos (~80KB c/u). LRU si escala a 8+.
      cfg.posters=data.posters||{};
      cfg.customPosters=data.customPosters||{};
      cfg.lbSlugs=data.lbSlugs||{};
      // ── Sprint 2: absorber campos de config desde JSON raíz ─────────────
      // Fuente única de verdad: el JSON de cada festival contiene toda su config.
      // FESTIVAL_CONFIG en index.html solo mantiene storageKey + festivalEndStr como bootstrap.
      // Estos campos se mergean si existen en el JSON — nunca pisan storageKey.
      const _cfgFields=['name','shortName','city','dates','dates_en','year',
        'timezoneOffset','festivalDates','days','dayKeys','dayShort','dayShort_en',
        'dayLong','prioLimit','eventPosterLabel','group','ticket_url','ticketing_model'];
      _cfgFields.forEach(k=>{ if(data[k]!=null) cfg[k]=data[k]; });
      // ── LEGADO: festivales anteriores con bloque config{} en el JSON ──────
      // Festivales nuevos (desde Mujeres 2026) NO deben incluir config{} en el JSON —
      // toda la configuración va en FESTIVAL_CONFIG en index.html.
      // Este bloque existe solo para compatibilidad con festivales anteriores.
      if(data.config){
        const _knownLegacy=['ficci65','cinemancia2025'];
        if(!_knownLegacy.includes(id)){
          console.warn(`[loadFestival] '${id}' tiene bloque config{} en el JSON — los festivales nuevos deben configurarse solo en FESTIVAL_CONFIG (index.html). El bloque config{} se ignora para festivales nuevos.`);
        } else {
          Object.assign(cfg, data.config);
          // Restaurar campos críticos — Object.assign puede pisarlos si config los tiene vacíos
          cfg.films=exploded;
          cfg.lbSlugs=data.lbSlugs||cfg.lbSlugs||{};
          cfg.posters=data.posters||cfg.posters||{};
          cfg.customPosters=data.customPosters||cfg.customPosters||{};
        }
      }
      // Absorber venues desde raíz del JSON (AFF/FICCI los tienen hardcodeados; otros festivales los traen aquí)
      if(data.venues) cfg.venues=data.venues;
      if(data.transport) cfg.transport=data.transport;
    }catch(e){
      console.error('Error cargando festival '+id+':',e);
      showToast(t('toast_conexion'),'error',5000);
      return false;
    }
  }
  // Guard: dayKeys y days son requeridos — sin ellos el UI de calendario crashea
  // (movido pre-batch en p5.5 para que el fallo no deje state parcialmente swapeado)
  if(!cfg.dayKeys||!cfg.days||!cfg.days.length){
    console.error(`[loadFestival] '${id}' no tiene dayKeys/days en FESTIVAL_CONFIG.`);
    showToast(t('error_festival_nd'),'error',6000);
    return false;
  }
  // Guard: festivalDates ({dayKey:isoDate}) → FESTIVAL_DATES. Sin él screeningPassed
  // y el match de día se rompen (FESTIVAL_DATES[day]=undefined en todo).
  if(!cfg.festivalDates||typeof cfg.festivalDates!=='object'){
    console.error(`[loadFestival] '${id}' no tiene festivalDates en FESTIVAL_CONFIG.`);
    showToast(t('error_festival_nd'),'error',6000);
    return false;
  }
  // Guard: festivalEndStr → FESTIVAL_END (new Date). Inválido → Invalid Date →
  // festivalEnded() y toda la lógica temporal se rompen silenciosamente.
  if(!cfg.festivalEndStr||isNaN(new Date(cfg.festivalEndStr).getTime())){
    console.error(`[loadFestival] '${id}' no tiene festivalEndStr válido en FESTIVAL_CONFIG.`);
    showToast(t('error_festival_nd'),'error',6000);
    return false;
  }
  // ── Non-roster cfg apply (legacy) ──────────────────────────────────
  // Estos globals no están en el state roster (Fase 5.5). Siguen como
  // asignaciones directas hasta Fase 8.
  POSTERS=cfg.posters;
  LB_SLUGS=cfg.lbSlugs||{};
  DAY_KEYS=cfg.dayKeys;
  setDayShortEn(cfg.dayShort_en||cfg.dayShort);
  // Si el festival no tiene dayShort en español (ej. Tribeca: valores en inglés),
  // construirlo desde las fechas ISO usando el día de la semana.
  const _EN_TO_ES={'SUN':'DOM','MON':'LUN','TUE':'MAR','WED':'MIÉ','THU':'JUE','FRI':'VIE','SAT':'SÁB'};
  const _needsTranslation = Object.values(cfg.dayShort||{}).some(v=>
    /^(MON|TUE|WED|THU|FRI|SAT|SUN)/.test(v)
  );
  let _esShort;
  if(_needsTranslation){
    const _translated={};
    Object.entries(cfg.dayShort||{}).forEach(([k,v])=>{
      const enAbb=v.split(' ')[0];
      const num=v.split(' ')[1]||'';
      const esAbb=_EN_TO_ES[enAbb]||enAbb;
      _translated[k]=num?esAbb+' '+num:esAbb;
    });
    _esShort=_translated;
  } else {
    _esShort=cfg.dayShort||{};
  }
  setDayShort(_esShort);
  CUSTOM_POSTERS=cfg.customPosters||{};
  setCustomPosters(CUSTOM_POSTERS);
  setPosters(POSTERS);
  // Mutar DAYS en sitio (const) + regenerar DAY_ABBR/DAY_NUM
  DAYS.length=0;
  cfg.days.forEach(d=>DAYS.push(d));
  Object.keys(DAY_ABBR).forEach(k=>delete DAY_ABBR[k]);
  Object.keys(DAY_NUM).forEach(k=>delete DAY_NUM[k]);
  cfg.days.forEach(d=>{DAY_ABBR[d.k]=d.lbl;DAY_NUM[d.k]=d.d;});
  // PRIO_LIMIT computado para batch 3 (regla: round(días/2), cap [3,8]).
  // Si cfg.prioLimit no está definido, fallback conservador = 3.
  const _computedPrioLimit = Math.min(8, Math.max(3, Math.round((cfg.dayKeys||[]).length / 2)));

  // ► BATCH 1 — transition + clear ───────────────────────────────────
  // FESTIVAL_STORAGE_KEY debe estar al new fest ANTES de batch 2 (loadState
  // lee storage prefijado). FESTIVAL_END debe estar antes del day-tab DOM
  // build (dayFullyPassed lo lee). availability rebuilda con shape del nuevo
  // festival, preservando blocks de días con misma key (cross-festival continuity).
  // festivalEndStr ('…T23:59:00') se ancla a la zona del festival vía
  // cfg.timezoneOffset → FESTIVAL_END es un instante ABSOLUTO correcto desde
  // cualquier dispositivo (festivalEnded compara contra simNow absoluto). Sin
  // offset (festivales viejos sin el campo) cae a hora local — equivalente para
  // audiencia en la misma zona del festival.
  const _currAv = state.get('availability');
  const _newAvShape = {};
  cfg.dayKeys.forEach(d => {
    _newAvShape[d] = (_currAv[d] && _currAv[d].blocks) ? _currAv[d] : {blocks:[]};
  });
  state.batchUpdate({
    FESTIVAL_STORAGE_KEY: cfg.storageKey,
    FESTIVAL_END: new Date(cfg.festivalEndStr+(cfg.timezoneOffset||'')),
    watchlist: new Set(),
    watched: new Set(),
    prioritized: new Set(),
    filmRatings: {},
    savedAgenda: null,
    lastRemovedSlots: [],
    filmDelays: {},
    filmDelaysHistory: {},
    availability: _newAvShape,
  });
  // Rebuild day tabs DOM
  const _dt=document.getElementById('dtabs');
  if(_dt){
    _dt.innerHTML='';
    // ── dtab "TODO" — muestra todo el programa sin filtro de día ──
      const todoBtn=document.createElement('button');
      todoBtn.className='dtab on';
      todoBtn.dataset.day='all';
      todoBtn.style.cssText='display:flex;align-items:center;justify-content:center;padding:0 14px';
      todoBtn.innerHTML='<span data-i18n="bar_todo" style="font-size:var(--t-sm);font-weight:700;letter-spacing:.08em;text-transform:uppercase">'+t('bar_todo')+'</span>';
      todoBtn.onclick=()=>{
        activeDay='all';activeVenue='all';activeSec='all';selectedIdx=null;
        cartelaMode='horario';
        setProgramaView('grid'); // TODO → siempre Grid
        document.querySelectorAll('.dtab').forEach(t=>t.classList.toggle('on',t.dataset.day==='all'));
        _renderProgramaContent(true); // cambio de día (TODO) → scroll al tope
        _updateProgramaActiveFilter();
        if(activeMNav!=='mnav-cartelera') switchMainNav('mnav-cartelera');
      };
      // Separador visual entre TODO y días de fecha
      const todoSep=document.createElement('div');
      todoSep.style.cssText='width:1px;background:var(--bdr);margin:6px 0;flex-shrink:0';
      _dt.appendChild(todoBtn);
      _dt.appendChild(todoSep);

      cfg.days.forEach(day=>{
      const btn=document.createElement('button');
      btn.className='dtab'+(dayFullyPassed(day.k)?' past':'');
      btn.dataset.day=day.k;
      const _dtabLblES=day.lbl;
      const _dtabLblEN=(DAY_SHORT_EN[day.k]||'').split(' ')[0]||day.lbl;
      const _dtabLbl=_lang==='en'?_dtabLblEN:_dtabLblES;
      btn.dataset.lblEs=_dtabLblES;
      btn.dataset.lblEn=_dtabLblEN;
      btn.innerHTML=`<span class="dtab-date">${_dtabLbl}</span><span class="dtab-name">${day.d}</span>`;
      btn.onclick=()=>{
        activeDay=day.k;activeVenue='all';selectedIdx=null;
        setProgramaView('list'); // día específico → siempre Lista (horarios/planificación)
        document.querySelectorAll('.dtab').forEach(t=>t.classList.toggle('on',t.dataset.day===day.k));
        _renderProgramaContent(true); // cambio de día específico → scroll al tope
        _updateProgramaActiveFilter();
        if(activeMNav!=='mnav-cartelera') switchMainNav('mnav-cartelera');
      };
      _dt.appendChild(btn);
    });
  }
  // Reset UI state (non-roster, sin cambios)
  activeDay=cfg.dayKeys[0];
  activeVenue='all';activeSec='all';selectedIdx=null;
  cachedResult=null; // invalidar cache del festival anterior — evita mostrar escenarios de otro festival
  programaSubMode='hoy';cartelaMode='horario';activeDay='all';programaViewMode='grid';
  miPlanViewStart=0;activeMiPlanDay=0;

  // ► BATCH 2 — hidrate desde storage del nuevo fest ─────────────────
  // loadState() internamente hace state.batchUpdate con los 9 user-state keys
  // (watchlist/watched/prioritized/filmRatings/availability/savedAgenda/
  // lastRemovedSlots/filmDelays/filmDelaysHistory).
  loadState();

  // ► BATCH 3 — cfg-tail + filter ────────────────────────────────────
  // _newFilms y _validTitles computados local — no se leen de state.
  // Esto permite que FILMS y los user-state filtrados estén en el MISMO
  // batch atómico. Subscribers post-Fase 6 verán "festival activo y user-state
  // consistente con sus films" en una sola notificación.
  // normTitle: normaliza comillas tipográficas en títulos. Punto único.
  const _mapped = (cfg.films||[]).map(f=>({...f,title:normTitle(f.title)}));
  // ── Validación de datos (domain puro: validateFilm) — particiona drop/keep ──
  // drop (sin title) → excluido de FILMS. errors (day/time) → conservado + logeado.
  // warnings (section/venue/duration) → conservado + default. Diagnóstico agregado
  // SIEMPRE (incluso si todo OK) para no procesar datos malformados en silencio.
  const _newFilms=[]; let _dropCount=0; const _filmErrors=[], _filmWarnings=[];
  for(const f of _mapped){
    const v=validateFilm(f, cfg.dayKeys, cfg.venues);
    if(v.drop){ _dropCount++; console.error(`[loadFestival/${id}] film DROP:`, f, v.errors); continue; }
    if(v.errors.length) _filmErrors.push({title:f.title, errors:v.errors});
    if(v.warnings.length) _filmWarnings.push({title:f.title, warnings:v.warnings});
    _newFilms.push(f);
  }
  console.group(`[loadFestival] ${id} — validación de ${_mapped.length} films`);
  console.log(`OK: ${_newFilms.length-_filmErrors.length} · con errores (conservados): ${_filmErrors.length} · con warnings: ${_filmWarnings.length} · dropeados: ${_dropCount}`);
  if(_filmErrors.length) console.error('Films con errores de datos:', _filmErrors);
  if(_filmWarnings.length) console.warn('Films con warnings:', _filmWarnings);
  console.groupEnd();
  const _validTitles = new Set(_newFilms.map(f=>f.title));
  state.batchUpdate({
    _activeFestId: id,
    FILMS: _newFilms,
    FESTIVAL_DATES: cfg.festivalDates,
    PRIO_LIMIT: cfg.prioLimit || _computedPrioLimit,
    TZ_OFFSET: cfg.timezoneOffset || '-05:00',
    FESTIVAL_TRANSPORT: cfg.transport || 'transit',
    watchlist: new Set([...state.get('watchlist')].filter(t=>_validTitles.has(t))),
    watched: new Set([...state.get('watched')].filter(t=>_validTitles.has(t))),
    prioritized: new Set([...state.get('prioritized')].filter(t=>_validTitles.has(t))),
  });

  // Set active day to today
  const _ts=simTodayStr();
  const _ni=DAY_KEYS.findIndex(d=>FESTIVAL_DATES[d]===_ts);
  if(_ni>=0){
    activeDay=DAY_KEYS[_ni];
    programaSubMode='hoy'; // Durante el festival → ir directo a Hoy
  }
  // Regla global inamovible: navegación por día específico → lista por defecto
  programaViewMode=activeDay==='all'?'grid':'list';
  // Update fest-bar
  const _fn=document.querySelector('.hdr-fest-name');
  const _fd=document.querySelector('.hdr-fest-dates');
  if(_fn) _fn.textContent=festivalShortName(cfg);
  if(_fd) _fd.textContent=' · '+(_lang==='en'&&cfg.dates_en?cfg.dates_en:cfg.dates)+(cfg.year?' '+cfg.year:'');
  // Re-render festival selector con el nuevo festival activo
  _renderFestivalSelector(id);
  // Persist choice
  storage.setActiveFestId(id);
  // Avisar al reloj el festival en curso (F1.6). Inerte fuera del wrapper iOS.
  window.__otfPushWatchFestival?.();
  // Retraso colaborativo (Fase B): (re)suscribir a los reportes de este festival.
  // Fire-and-forget — no bloquea el render; el badge se pinta al llegar datos.
  subscribeDelaysCloud();
  // Render — await dos rAFs: primero renderiza, segundo confirma el paint
  closeFestivalSheet();
  switchMainNav('mnav-cartelera');
  await new Promise(resolve=>requestAnimationFrame(()=>{showDayView();requestAnimationFrame(resolve);}));
  // Posicionar la barra de días en el día activo (hoy, durante el festival).
  // El render fija activeDay + la clase .on, pero no scrollea #dtabs → sin esto
  // la barra arranca en el día 1 con el día de hoy fuera de pantalla. Corre tras
  // el doble-rAF (barra ya pintada y medible). Mismo patrón que filterByDay.
  const _dtabs=document.getElementById('dtabs');
  const _onDtab=_dtabs&&_dtabs.querySelector('.dtab.on');
  if(_dtabs&&_onDtab) _dtabs.scrollLeft=_onDtab.offsetLeft-_dtabs.offsetLeft;
  // Resolver posters via TMDB en background — no bloquea la UI
  _autoResolveFestivalPosters().catch(()=>{});
  // F0 sync multi-dispositivo: si el usuario está firmado (no anónimo), bajar el
  // plan de la nube para ESTE festival con guard (no pisa ediciones locales sin
  // subir ni datos ya frescos — ver _cloudLoad). Boot y cambio de festival pasan
  // por acá → cubre "edito en el iPhone, abro en el iPad/Watch y veo lo último".
  // Fire-and-forget; re-renderiza la vista activa al aplicar la nube.
  const _u=state.get('_sbUser');
  if(_u&&!_u.is_anonymous){
    _cloudLoad({guard:true}).then(()=>{ showDayView(); _renderProgramaContent(); }).catch(()=>{});
    // F0.5: sync EN VIVO — al cambiar el plan en otro dispositivo (o el Watch),
    // aplicar el cambio sin reabrir. Idempotente por (user, festival).
    subscribePlanCloud();
  }
}

export function dismissSplash(){
  // Sin festival elegido no hay a dónde entrar. El botón "Entrar" está disabled
  // hasta que se elige (selectSplashFest lo habilita); guard defensivo por si
  // el click llega igual.
  if(!_splashSelectedFestId) return;
  const s=document.getElementById('otrofestiv-splash');
  const btn=document.querySelector('.splash-enter-btn');
  if(btn) btn.classList.add('loading');
  loadFestival(_splashSelectedFestId)
    .then(ok=>{
      if(ok===false){
        if(btn) btn.classList.remove('loading'); // reset spinner — el error ya se mostró con toast
        return;
      }
      // 150ms para que el compositor de iOS se asiente antes de revelar
      setTimeout(()=>{
        if(s){s.classList.add('fade-out');setTimeout(()=>{s.remove();// FIX iOS compositor (especialmente Leviza/festival activo):
          // initProgramaModeBar() corrió bajo el splash → reflowó el topbar →
          // compositor cacheó nav en posición incorrecta. Re-ejecutar DESPUÉS de
          // quitar el splash fuerza el reflow en viewport abierto → posición correcta.
          // Luego translateY(0)→'' en doble rAF hace flush definitivo del compositor.
          (function(){
            if(typeof initProgramaModeBar==='function') initProgramaModeBar();
            if(typeof _fixStickyOffset==='function') _fixStickyOffset();
            const _nav=document.getElementById('main-nav');
            if(!_nav) return;
            _nav.style.transform='translateY(0)';
            requestAnimationFrame(function(){
              requestAnimationFrame(function(){
                _nav.style.transform='';
              });
            });
          })();},680);}
        if(btn) btn.classList.remove('loading');
      },150);
    })
    .catch(e=>{
      console.error('Error init festival:',e);
      if(btn) btn.classList.remove('loading');
    });
}
