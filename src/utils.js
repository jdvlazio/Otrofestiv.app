// ══ Utils — festivalEnded, screeningPassed, venues, conflictos, travel ══
// SOURCE: index.html L2714-2874

function festivalEnded(){ return simNow()>FESTIVAL_END; }

// Check if a screening has passed (with 10 min grace)

// ═══════════════════════════════════════════════════════════════
// 4 · UTILIDADES
//     Funciones puras: fechas, tiempo, conflictos, normalización
// ═══════════════════════════════════════════════════════════════
function screeningPassed(s){
  if(festivalEnded()) return false; // festival terminado — todo vuelve a plena opacidad
  const dateStr=FESTIVAL_DATES[s.day];
  if(!dateStr) return false;
  const screeningTime=new Date(`${dateStr}T${s.time}:00`);
  screeningTime.setMinutes(screeningTime.getMinutes()+10); // 10 min grace
  return simNow()>screeningTime;
}
function dayFullyPassed(day){
  const dateStr=FESTIVAL_DATES[day];
  if(!dateStr) return false;
  // Day passed if last function of that day has passed
  const dayFilms=FILMS.filter(f=>f.day===day);
  if(!dayFilms.length) return false;
  const lastTime=dayFilms.reduce((max,f)=>f.time>max?f.time:max,'00:00');
  const lastScreen=new Date(`${dateStr}T${lastTime}:00`);
  lastScreen.setMinutes(lastScreen.getMinutes()+10);
  return simNow()>lastScreen;
}
function isNowShowing(f){
  const dateStr=FESTIVAL_DATES[f.day];if(!dateStr) return false;
  const now=simNow();
  const start=new Date(`${dateStr}T${f.time}:00`);
  const dur=f.duration?parseInt(f.duration):90;
  const end=new Date(start.getTime()+dur*60000);
  return now>=start&&now<=end;
}
function isToday(day){
  const dateStr=FESTIVAL_DATES[day];
  if(!dateStr) return false;
  const today=simTodayStr();
  return dateStr===today;
}

/* ── VENUES: sistema global de sedes ────────────────────────────────────
   _FEST_VENUES se carga desde festivals/*.json en loadFestival().
   Fallback estático cubre FICCI 65 y AFF 2026 (formato legado).
   Para festivales nuevos, definir venues{} en el JSON del festival.  ── */
let _FEST_VENUES = {};      // cargado dinámicamente desde el JSON del festival
let _FEST_TRANSPORT = 'transit'; // 'walking' | 'transit' — default: transit

// Fallback estático — FICCI 65 (Cartagena)
const VENUES={
  'Teatro Adolfo Mejía': {short:'Teatro Adolfo Mejía', lat:10.4238, lon:-75.5503},
  'Plaza Bocagrande':    {short:'Plaza Bocagrande',    lat:10.3987, lon:-75.5600},
  'CC Caribe Plaza':     {short:'CC Caribe Plaza',     lat:10.4071, lon:-75.5124},
  'Auditorio Nido':      {short:'Auditorio Nido',      lat:10.4250, lon:-75.5490},
  'Plaza Proclamación':  {short:'Plaza Proclamación',  lat:10.4230, lon:-75.5510},
  'C. Convenciones':     {short:'C. de Convenciones',  lat:10.4242, lon:-75.5497},
  'Unibac':              {short:'Unibac',               lat:10.4180, lon:-75.5430},
  'AECID':               {short:'AECID',                lat:10.4210, lon:-75.5470},
};

// Resolución de venue: primero _FEST_VENUES (JSON), luego VENUES (fallback)
function _resolveVenue(v){
  if(!v) return null;
  // Búsqueda exacta en venues del festival
  if(_FEST_VENUES[v]) return _FEST_VENUES[v];
  // Búsqueda parcial en venues del festival
  const fk=Object.keys(_FEST_VENUES).find(k=>v.includes(k)||k.includes(v));
  if(fk) return _FEST_VENUES[fk];
  // Fallback estático FICCI
  const sk=Object.keys(VENUES).find(k=>v.includes(k)||k.includes(v));
  if(sk) return VENUES[sk];
  return null;
}

// Escalas de tiempo por modo de transporte
// walking: festival compacto (pueblo, campus) — todo a pie
// transit: festival en ciudad — Uber/Metro entre sedes
// mixed:   híbrido — a pie si < 1km, en carro si > 1km (ej: Cartagena)
const _TRAVEL_SCALE = {
  walking: [{d:0.10,t:0},{d:0.35,t:5},{d:0.8,t:10},{d:1.5,t:20},{d:3.0,t:35},{d:Infinity,t:50}],
  transit: [{d:0.15,t:0},{d:0.40,t:8},{d:1.0,t:12},{d:2.5,t:18},{d:5.0,t:25},{d:Infinity,t:35}],
  mixed:   [{d:0.10,t:0},{d:0.35,t:5},{d:0.8,t:10},{d:1.0,t:12},{d:2.5,t:18},{d:5.0,t:25},{d:Infinity,t:35}],
};
function venueTravelMins(v1,v2){
  const c1=_resolveVenue(v1), c2=_resolveVenue(v2);
  if(!c1?.lat||!c2?.lat) return 0;
  const dlat=(c1.lat-c2.lat)*111;
  const dlon=(c1.lon-c2.lon)*111*Math.cos(c1.lat*Math.PI/180);
  const km=Math.sqrt(dlat*dlat+dlon*dlon);
  const scale=_TRAVEL_SCALE[_FEST_TRANSPORT]||_TRAVEL_SCALE.transit;
  const tier=scale.find(s=>km<=s.d);
  return tier?tier.t:35;
}

function vcfg(v){
  if(!v) return {short:''};
  const r=_resolveVenue(v);
  if(r) return r;
  return {short:v.split(' · ')[0].trim()};
}
function sala(v){const m=v.match(/Sala\s*(\d+)/)||v.match(/Sal[oó]n\s*(\d+)/i);return m?'Sala '+m[1]:'';}

// ════ algo.js ════
// ══════════════════════════════════════════════════════════════════
// ALGORITMO DE PLANIFICACIÓN — exhaustive max + MRV + backtracking
// Dependencias: FILMS, watchlist, prioritized, availability,
//               screensConflict(), screeningPassed(), isScreeningBlocked(),
//               parseDur(), toMin(), FESTIVAL_BUFFER
// ══════════════════════════════════════════════════════════════════

// ── ALGORITHM — exhaustive max + MRV + random restarts ──
function shuffle(arr){
  const a=[...arr];
  for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]];}
  return a;
}

// ── Mejora 1: Scoring por película ──
// Pondera cuánto vale incluir una película según rareza, sección y duración
function scoreFilm(title, screens, isPriority, allTitles){
  let score=0;
  // Prioridad explícita: peso máximo
  if(isPriority) score+=100;
  // Unicidad: menos funciones = más difícil de ver = mayor peso
  const n=screens.length;
  if(n===1) score+=40;
  else if(n===2) score+=20;
  else score+=5;
  // Sección única: si es la única película de su sección en la watchlist
  const mySection=screens[0]?.section||'';
  const siblingsInSection=allTitles.filter(t=>{
    if(t===title) return false;
    return FILMS.some(f=>f.title===t&&f.section===mySection);
  });
  if(siblingsInSection.length===0) score+=15;
  // Duración larga: película de >150 min es un compromiso grande, priorizar
  const dur=parseInt(screens[0]?.duration)||0;
  if(dur>150) score+=10;
  return score;
}

// ── Mejora 2: Interval Scheduling — ordenar funciones por conflictos mínimos + fin temprano ──
// Para cada película con múltiples funciones, prioriza la que:
// 1. Conflicta con menos otras funciones de la watchlist (menos bloqueos)
// 2. Termina más temprano (earliest-finish-time: principio clásico de interval scheduling)
function sortScreensByStrategy(screens, allGroups){
  // Precalcular todas las funciones de todas las otras películas
  const allOtherScreenings=allGroups.flatMap(g=>g.screens);
  return [...screens].sort((a,b)=>{
    // Contar cuántas funciones ajenas conflictan con cada opción
    const conflA=allOtherScreenings.filter(s=>s!==a&&screensConflict(a,s)).length;
    const conflB=allOtherScreenings.filter(s=>s!==b&&screensConflict(b,s)).length;
    if(conflA!==conflB) return conflA-conflB; // menos conflictos primero
    // Si empatan, earliest finish time (termina antes = deja más espacio)
    const endA=toMin(a.time)+parseDur(a.duration);
    const endB=toMin(b.time)+parseDur(b.duration);
    return endA-endB;
  });
}


function _effectiveVenue(s){
  const n=NOTICES.find(nx=>nx.title===s._title&&nx.festival===(window._currentFestivalId||'aff2026')&&nx.type==='rescheduled'&&nx.newVenue);
  return n?n.newVenue:s.venue;
}
function travelWarn(s1,s2){
  if(s1.day!==s2.day) return null;
  const v1=_effectiveVenue(s1), v2=_effectiveVenue(s2);
  const travel=travelMins(v1,v2);
  if(travel===0) return null;
  const _tLabel=(_FEST_TRANSPORT==='walking'||(travel<=12&&_FEST_TRANSPORT==='mixed'))?UI.travel.walking:UI.travel.transit;
  const gap=toMin(s2.time)-(toMin(s1.time)+parseDur(s1.duration));
  if(gap<travel+10) return`\u25b2 ~${travel} min ${_tLabel} entre sedes`;
  return null;
}