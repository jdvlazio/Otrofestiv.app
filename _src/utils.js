// ══ Utils — festivalEnded, screeningPassed, venues, conflictos, travel ══
// SOURCE: index.html L2714-2874

/* ── UTILS: tiempo, fecha, duración ─────────────────────────────────── */
function toMin(t){const[h,m]=t.split(':').map(Number);return h*60+m;}
function parseDur(d){const m=d&&d.replace('~','').match(/(\d+)/);return m?parseInt(m[1]):90;}
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
  const travel=(a.venue&&b.venue)?travelMins(a.venue,b.venue):0;
  const minGap=Math.max(FESTIVAL_BUFFER, travel+FESTIVAL_BUFFER);
  if(aE<=bS) return (bS-aE)<minGap;
  if(bE<=aS) return (aS-bE)<minGap;
  return true;
}
function travelMins(venueA,venueB){
  const coordMins=venueTravelMins(venueA,venueB);
  if(coordMins>0) return coordMins;
  const g=v=>v.includes('Bocagrande')?'bog':v.includes('Caribe Plaza')?'cp':'centro';
  const g1=g(venueA),g2=g(venueB);
  if(g1===g2) return 0;
  if((g1==='bog'&&g2==='cp')||(g1==='cp'&&g2==='bog')) return 13;
  if(g1==='centro'||g2==='centro') return g1==='cp'||g2==='cp'?16:12;
  return 0;
}
function isScreeningBlocked(s){
  const av=availability[s.day];if(!av) return false;
  const sStart=toMin(s.time),sEnd=sStart+parseDur(s.duration);
  return av.blocks.some(b=>sStart<toMin(b.to)&&sEnd>toMin(b.from));
}



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
// _FEST_VENUES y _FEST_TRANSPORT declarados en config.js

// Fallback estático — FICCI 65 (Cartagena)

// ════ algo.js ════
// ══════════════════════════════════════════════════════════════════
// ALGORITMO DE PLANIFICACIÓN — exhaustive max + MRV + backtracking
// Dependencias: FILMS, watchlist, prioritized, availability,
//               screensConflict(), screeningPassed(), isScreeningBlocked(),
//               parseDur(), toMin(), FESTIVAL_BUFFER
// ══════════════════════════════════════════════════════════════════


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