// ══ Utils — dayFullyPassed, venues, conflicts, travel ══
// SOURCE: index.html L2711-2876

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
/* ── UTILS: tiempo, fecha, duración ─────────────────────────────────── */
function toMin(t){const[h,m]=t.split(':').map(Number);return h*60+m;}
function parseDur(d){const m=d&&d.replace('~','').match(/(\d+)/);return m?parseInt(m[1]):90;}
// Duración efectiva: parseDur + 30 min si has_qa (Q&A alarga la función)
function effectiveDuration(f){return parseDur(f&&f.duration)+(f&&f.has_qa?30:0);}
function minToStr(m){
  const h=Math.floor(((m%1440)+1440)%1440/60),mn=((m%1440)+1440)%1440%60;
  return`${String(h).padStart(2,'0')}:${String(mn).padStart(2,'0')}`;
}

/* ── CONFLICTS: detección de solapamientos entre funciones ──────────── */
function screensConflict(a,b){
  if(a.day!==b.day) return false;
  const aS=toMin(a.time), aE=aS+parseDur(a.duration);
  const bS=toMin(b.time), bE=bS+parseDur(b.duration);
  // Gap requerido: tiempo de viaje entre sedes + 5min margen (mínimo 10min)
  const travel=(a.venue&&b.venue)?travelMins(a.venue,b.venue):0;
  const minGap=Math.max(FESTIVAL_BUFFER, travel+FESTIVAL_BUFFER);
  if(aE<=bS) return (bS-aE)<minGap; // a antes que b
  if(bE<=aS) return (aS-bE)<minGap; // b antes que a
  return true; // solapamiento directo
}
function travelMins(venueA,venueB){
  // First try coordinate-based calculation (works for all festivals)
  const coordMins=venueTravelMins(venueA,venueB);
  if(coordMins>0) return coordMins;
  // Fallback: FICCI Cartagena venue groups
  const g=v=>v.includes('Bocagrande')?'bog':v.includes('Caribe Plaza')?'cp':'centro';
  const g1=g(venueA),g2=g(venueB);
  if(g1===g2) return 0;
  if((g1==='bog'&&g2==='cp')||(g1==='cp'&&g2==='bog')) return 13;
  if(g1==='centro'||g2==='centro') return g1==='cp'||g2==='cp'?16:12;
  return 0;
}
function _effectiveVenue(s){
  // Si hay un notice de cambio de sede, usa la nueva sede
  const n=NOTICES.find(nx=>nx.title===s._title&&nx.festival===(window._currentFestivalId||'aff2026')&&nx.type==='rescheduled'&&nx.newVenue);
  return n?n.newVenue:s.venue;
}
function travelWarn(s1,s2){
  if(s1.day!==s2.day) return null;
  const v1=_effectiveVenue(s1), v2=_effectiveVenue(s2);
  const travel=travelMins(v1,v2);
  if(travel===0) return null;
  const gap=toMin(s2.time)-(toMin(s1.time)+parseDur(s1.duration));
  const _tLabel=(_FEST_TRANSPORT==='walking'||(travel<=12&&_FEST_TRANSPORT==='mixed'))?UI.travel.walking:UI.travel.transit;
  if(gap<travel+10) return`▲ ~${travel} min ${_tLabel} entre sedes`;
  return null;
}

// Normalize text for accent-insensitive search
function normalize(str){
  return str.normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase();
}


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
