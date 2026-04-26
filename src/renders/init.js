// ══ Init — loadFestival, splash, SW, event listeners ══
// SOURCE: index.html L7690-8062



/* ── Splash de primer encuentro ──────────────────────────────────
   Solo se muestra si no hay datos previos del usuario.
   Auto-dismiss en 2.5s o al tocar.
────────────────────────────────────────────────────────────────── */
function toggleSplashDropdown(){
  const dd=document.getElementById('splash-dropdown');
  const btn=document.getElementById('splash-sel-btn');
  if(!dd||!btn) return;
  const open=dd.style.display==='none';
  dd.style.display=open?'block':'none';
  btn.classList.toggle('open',open);
}
let _splashSelectedFestId='aff2026'; // matches HTML pre-selection
function selectSplashFest(name,meta,festId){
  _splashSelectedFestId=festId||'aff2026';
  const n=document.getElementById('splash-sel-name');
  const m=document.getElementById('splash-sel-meta');
  if(n) n.textContent=name;
  if(m) m.textContent=meta;
  document.querySelectorAll('.splash-drop-item').forEach(el=>el.classList.remove('selected'));
  const active=document.querySelector('.splash-drop-item[data-fest="'+_splashSelectedFestId+'"]');
  if(active) active.classList.add('selected');
  const dd=document.getElementById('splash-dropdown');
  const btn=document.getElementById('splash-sel-btn');
  if(dd) dd.style.display='none';
  if(btn) btn.classList.remove('open');
}

async function loadFestival(id){
  const cfg=FESTIVAL_CONFIG[id];
  if(!cfg){console.warn('Festival desconocido:',id);return;}
  // ── Fase 1: cargar datos del festival desde JSON si no están en memoria ──
  if(!cfg.films){
    try{
      // Datos incrustados en build-time — no hay fetch, no hay 403
      const data=_FESTIVAL_DATA[id];
      if(!data) throw new Error('Festival data not embedded: '+id);
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
              day:s.day,date:s.date,time:s.time,venue:s.venue||'',
              day_order:s.day_order!==undefined?s.day_order:i,
              sala:s.sala||''
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
      // ── Carga de venues desde el JSON del festival ──
      // Si el JSON define venues{}, se usa para resolución de sedes y
      // cálculo de distancias. Reemplaza el sistema estático por festival.
      _FEST_VENUES = {};
      _FEST_TRANSPORT = data.transport||'transit'; // 'walking' | 'transit'
      if(data.venues&&typeof data.venues==='object'){
        Object.entries(data.venues).forEach(([key,v])=>{
          _FEST_VENUES[key]=Object.assign({short:key},v);
        });
      }
      cfg.films=exploded;
      cfg.posters=data.posters||{};
      cfg.customPosters=data.customPosters||{};
      cfg.lbSlugs=data.lbSlugs||{};
    }catch(e){
      console.error('Error cargando festival '+id+':',e);
      return;
    }
  }
  _activeFestId=id;
  // Swap globals
  FILMS=cfg.films;
  POSTERS=cfg.posters;
  LB_SLUGS=cfg.lbSlugs||{};
  FESTIVAL_DATES=cfg.festivalDates;
  FESTIVAL_END=new Date(cfg.festivalEndStr);
  FESTIVAL_STORAGE_KEY=cfg.storageKey;
  DAY_KEYS=cfg.dayKeys;
  DAY_SHORT=cfg.dayShort;
  DAY_LONG=cfg.dayLong;
  PRIO_LIMIT=cfg.prioLimit||5;
  // Reconstruir lookup de posters para el festival activo
  CUSTOM_POSTERS=cfg.customPosters||{};
  _CUSTOM_N=Object.fromEntries(Object.entries(CUSTOM_POSTERS).map(([k,v])=>[normKey(k),v]));
  _POSTERS_N=Object.fromEntries(Object.entries(POSTERS).map(([k,v])=>[normKey(k),v]));
  // Mutar DAYS en sitio (const) + regenerar DAY_ABBR/DAY_NUM
  DAYS.length=0;
  cfg.days.forEach(d=>DAYS.push(d));
  Object.keys(DAY_ABBR).forEach(k=>delete DAY_ABBR[k]);
  Object.keys(DAY_NUM).forEach(k=>delete DAY_NUM[k]);
  cfg.days.forEach(d=>{DAY_ABBR[d.k]=d.lbl;DAY_NUM[d.k]=d.d;});
  // Rebuild day tabs DOM
  const _dt=document.getElementById('dtabs');
  if(_dt){
    _dt.innerHTML='';
    cfg.days.forEach(day=>{
      const btn=document.createElement('button');
      btn.className='dtab';
      btn.dataset.day=day.k;
      btn.innerHTML=`<span class="dtab-date">${day.lbl}</span><span class="dtab-name">${day.d}</span>`;
      btn.onclick=()=>{
        activeDay=day.k;activeVenue='all';activeSec='all';selectedIdx=null;
        cartelaMode='horario';
        document.querySelectorAll('.dtab').forEach(t=>t.classList.toggle('on',t.dataset.day===day.k));
        _renderProgramaContent();
        if(activeMNav!=='mnav-cartelera') switchMainNav('mnav-cartelera');
      };
      _dt.appendChild(btn);
    });
  }
  // Reset app state
  activeDay=cfg.dayKeys[0];
  activeVenue='all';activeSec='all';selectedIdx=null;
  watchlist=new Set();watched=new Set();filmRatings={};savedAgenda=null;
  prioritized=new Set();lastRemovedSlots=[];filmDelays={};
  // Rebuild availability for new festival days (keep blocks if already set)
  const _newAv={};
  DAY_KEYS.forEach(d=>{_newAv[d]=availability[d]&&availability[d].blocks?availability[d]:{blocks:[]}});
  Object.keys(availability).forEach(k=>delete availability[k]);
  Object.assign(availability,_newAv);
  programaSubMode='explorar';cartelaMode='horario';
  miPlanViewStart=0;activeMiPlanDay=0;
  // Load from new storage
  loadState();
  // Filter watchlist/watched to current festival's films only (prevents cross-festival contamination)
  const _validTitles=new Set(FILMS.map(f=>f.title));
  watchlist=new Set([...watchlist].filter(t=>_validTitles.has(t)));
  watched=new Set([...watched].filter(t=>_validTitles.has(t)));
  prioritized=new Set([...prioritized].filter(t=>_validTitles.has(t)));
  // Set active day to today
  const _ts=simTodayStr();
  const _ni=DAY_KEYS.findIndex(d=>FESTIVAL_DATES[d]===_ts);
  if(_ni>=0){
    activeDay=DAY_KEYS[_ni];
    programaSubMode='hoy'; // Durante el festival → ir directo a Hoy
  }
  // Update fest-bar
  const _fn=document.querySelector('.hdr-fest-name');
  const _fd=document.querySelector('.hdr-fest-dates');
  if(_fn) _fn.textContent=cfg.name;
  if(_fd) _fd.textContent='\u00b7 '+cfg.dates;
  // Update fs-sheet active row
  document.querySelectorAll('.fs-festival-row[data-fest]').forEach(row=>{
    const isActive=row.dataset.fest===id;
    row.querySelector('.fs-fest-check').style.display=isActive?'':'none';
  });
  // Persist choice
  localStorage.setItem('otrofestiv_festival',id);
  // Render — defer un frame para evitar flash de contenido previo
  closeFestivalSheet();
  switchMainNav('mnav-cartelera');
  requestAnimationFrame(()=>showDayView());
}
function dismissSplash(){
  const s=document.getElementById('otrofestiv-splash');
  if(s){s.classList.add('fade-out');setTimeout(()=>s.remove(),520);}
  loadFestival(_splashSelectedFestId||'aff2026').catch(e=>console.error('Error init festival:',e));
}
// Inicializar Supabase al cargar la página
// Capgo OTA — notifica que la app arrancó correctamente (Cap 6)
if(window.Capacitor?.Plugins?.CapacitorUpdater){
  window.Capacitor.Plugins.CapacitorUpdater.notifyAppReady();
}
_sbInit();
(function(){
  // Detecta el festival en curso por fecha. Prioridad:
  // 1. Festival que está sucediendo hoy · 2. El próximo más cercano · 3. El más reciente
  function detectActiveFest(){
    const today=new Date();today.setHours(12,0,0,0);
    let inProgress=null,nextUp=null,nextUpStart=null,mostRecent=null,mostRecentEnd=null;
    Object.entries(FESTIVAL_CONFIG).forEach(([id,cfg])=>{
      if(!cfg.festivalDates) return;
      const dates=Object.values(cfg.festivalDates);
      const startStr=dates.reduce((a,b)=>a<b?a:b);
      const start=new Date(startStr+'T00:00:00');
      const end=new Date(cfg.festivalEndStr);
      if(today>=start&&today<=end){
        inProgress=id;
      } else if(start>today){
        if(!nextUpStart||start<nextUpStart){nextUp=id;nextUpStart=start;}
      } else {
        if(!mostRecentEnd||end>mostRecentEnd){mostRecent=id;mostRecentEnd=end;}
      }
    });
    return inProgress||nextUp||mostRecent||'aff2026';
  }
  const activeFest=detectActiveFest();
  _splashSelectedFestId=activeFest;
  const cfg=FESTIVAL_CONFIG[activeFest];
  if(cfg){
    const n=document.getElementById('splash-sel-name');
    const m=document.getElementById('splash-sel-meta');
    if(n) n.textContent=cfg.name;
    if(m) m.textContent=cfg.city+' \u00b7 '+cfg.dates+' 2026';
    document.querySelectorAll('.splash-drop-item').forEach(el=>{
      el.classList.toggle('selected',el.dataset.fest===activeFest);
    });
  }
})();

// ── Init: el splash siempre se muestra ─────────────────────────────
// El festival pre-seleccionado es el que está en curso por fecha.
// loadFestival() se llama desde dismissSplash() cuando el usuario pulsa "Entrar".
/* ── Tap-to-reveal en Intereses mobile ──────────────────────────
   Toca el poster → revela botones (ag-active).
   Toca fuera o toca un botón → cierra. */
document.addEventListener('click', function(e){
  const item = e.target.closest('.ag-film-item');
  const activeItems = document.querySelectorAll('.ag-film-item.ag-active');
  if(item){
    const isActive = item.classList.contains('ag-active');
    activeItems.forEach(el => el.classList.remove('ag-active'));
    if(!isActive && !e.target.closest('.ag-fi-btn')){
      item.classList.add('ag-active');
    }
  } else {
    activeItems.forEach(el => el.classList.remove('ag-active'));
  }
});

/* ── Re-render automático cada 60s ───────────────────────────
   Actualiza estados temporales (AHORA, Ya pasó, días pasados)
   sin depender de que el usuario navegue entre tabs.
   Solo re-renderiza si Planear o Cartelera están visibles.
   Replicable en cualquier festival futuro sin cambios.
────────────────────────────────────────────────────────────── */
// Sincronizar el primer tick con el siguiente minuto del reloj del sistema
// Así el contador avanza exactamente cuando cambia el minuto — no con retraso
function _startTickLoop(){
  setInterval(function(){
    // Planear
    if(activeMNav==='mnav-planner' && activeView==='agenda'){
      renderAgenda();
    }
    // Cartelera
    if(activeView==='day'){
      render();
    }
    // Mi Plan — contador de minutos next-film-strip
    if(activeMNav==='mnav-miplan' && activeView==='agenda'){
      renderAgenda();
    }
    updateAgTab();
  }, 60000);
}
// Esperar al próximo minuto exacto antes de iniciar el loop
const _msToNextMin=(60-new Date().getSeconds())*1000;
setTimeout(function(){ _startTickLoop(); _startTickLoop.call(); }, _msToNextMin);
// Mientras tanto, tick inmediato para estado inicial correcto
updateAgTab();

// ── Reactivar al volver al primer plano ──────────────────────
// iOS/Android suspenden setInterval cuando la app va a background.
// visibilitychange fuerza re-render inmediato al volver,
// sin esperar al próximo tick del loop.
// ── Bienvenida primer uso ────────────────────────────────────────
// Escalable: FESTIVAL_STORAGE_KEY cambia por edición → siempre nuevo
function showWelcomeIfNeeded(){
  const key=FESTIVAL_STORAGE_KEY+'welcome_seen';
  if(localStorage.getItem(key)) return;
  const el=document.getElementById('welcome-overlay');
  if(el) el.style.display='flex';
}
function dismissWelcome(){
  localStorage.setItem(FESTIVAL_STORAGE_KEY+'welcome_seen','1');
  const el=document.getElementById('welcome-overlay');
  if(el){ el.style.opacity='0';el.style.transition='opacity .25s';
    setTimeout(()=>el.style.display='none',260); }
}
// Mostrar después de que el estado cargue
setTimeout(showWelcomeIfNeeded, 400);

// ── Back-to-top: solo visible cuando hay scroll ──────────────────
(function(){
  const btn=document.getElementById('back-top');
  if(!btn) return;
  const onScroll=()=>{ btn.classList.toggle('visible', window.scrollY > 200); };
  window.addEventListener('scroll',onScroll,{passive:true});
})();
document.addEventListener('visibilitychange', function(){
  if(document.visibilityState!=='visible') return;
  // Al volver al primer plano: si hay función en los próximos 30min → Mi Plan
  if(_checkNavigateToMiPlan()&&activeMNav!=='mnav-miplan'){
    switchMainNav('mnav-miplan');
    showAgView();
  } else {
    if(activeMNav==='mnav-miplan'&&activeView==='agenda') renderAgenda();
    else if(activeMNav==='mnav-planner'&&activeView==='agenda') renderAgenda();
    else if(activeView==='day') render();
  }
  updateAgTab();
}); // visibilitychange

// html2canvas eliminado — Canvas API puro
document.addEventListener('click',e=>{if(!e.target.closest('.fdr-wrap')) closeDropdowns();});
updateAgTab();render();

// ── Auto-navegar a Mi Plan si hay función próxima ──────────────
// Si el usuario tiene un plan guardado y hay una función
// empezando en los próximos 30 minutos, aterrizamos en Mi Plan.
// También se revisa al volver de background (visibilitychange).
function _checkNavigateToMiPlan(){
  if(festivalEnded()) return false;
  if(!savedAgenda||!savedAgenda.schedule||!savedAgenda.schedule.length) return false;
  const now=simNow();
  const WINDOW_MS=30*60*1000; // 30 minutos
  const upcoming=savedAgenda.schedule.find(s=>{
    const dateStr=FESTIVAL_DATES[s.day];
    if(!dateStr) return false;
    const start=new Date(`${dateStr}T${s.time}:00`);
    const diff=start-now;
    return diff>=0 && diff<=WINDOW_MS; // empieza en los próximos 30min
  });
  return !!upcoming;
}

// Al arrancar — solo si no estamos en primer uso (welcome overlay visible)
setTimeout(()=>{
  if(_checkNavigateToMiPlan()){
    switchMainNav('mnav-miplan');
    showAgView();
  }
}, 600); // después del welcome check (400ms) y del render inicial

function openFestivalSheet(){
  const ov=document.getElementById('fs-overlay');
  const sh=document.getElementById('fs-sheet');
  if(ov) ov.classList.add('open');
  if(sh) sh.classList.add('open');
}
function closeFestivalSheet(){
  const ov=document.getElementById('fs-overlay');
  const sh=document.getElementById('fs-sheet');
  if(ov) ov.classList.remove('open');
  if(sh) sh.classList.remove('open');
}

/* ── _fixStickyOffset: correct sticky positions for desktop gap ─────────
   Measures actual topbar height so #hdr-programa sticks precisely.
   Runs synchronously + on resize. Desktop only (mobile uses CSS 47px). */
function _fixStickyOffset(){
  const tb=document.querySelector('.topbar');
  if(!tb||window.innerWidth<768) return;
  const h=Math.ceil(tb.getBoundingClientRect().height)||130;
  const r=document.documentElement.style;
  r.setProperty('--tb-total',h+'px');
  r.setProperty('--sticky-top-carta',h+'px');
  r.setProperty('--sticky-top-modebar',(h+44)+'px');
  r.setProperty('--sticky-top-chips',(h+44+42)+'px');
}
_fixStickyOffset();
window.addEventListener('resize',function(){requestAnimationFrame(_fixStickyOffset);});
