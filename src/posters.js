// ══ Posters — generativos SVG, TMDB, getFilmPoster ══
// Nota: SHORT_IMGS, normKey, etc. declarados en config.js

function _buildPosterSVG(o){
  // Unified 120×180 poster layout for events and cortos programs.
  // Identical internal distribution — only colors and header labels differ.
  const VW=120,VH=180;
  // ── HEADER: 38px, 2 text lines centred mathematically ──────────────
  // Midpoint of baselines = (y1+y2)/2 = header_center (38/2=19).
  // y1=14, y2=24 → midpoint=19. Both lines 10px apart (8px font + 2px leading).
  const HDR_H=38,HDR_Y1=15,HDR_Y2=27; // Centrado exacto: bloque 20px centrado en 38px → aire=9px arriba y abajo
  // ── INNER BOX ──────────────────────────────────────────────────────
  const BX=10,BY=46,BW=VW-20,BH=VH-56;
  // ── FOOTER ─────────────────────────────────────────────────────────
  const FY=VH-16;

  // Wrap body title into lines of ≤13 chars
  const MAX=13,LD=13;
  const ws=(o.title||'').split(/\s+/);
  const ls=[];let c='';
  for(const w of ws){
    if(c&&(c+' '+w).length>MAX){ls.push(c);c=w;}
    else c=c?c+' '+w:w;
  }
  if(c) ls.push(c);

  // Centre title+duration block inside inner box
  const dH=o.duration?19:0;
  const bH=ls.length*LD+dH;
  // ZONAS FIJAS — el layout no cambia con el contenido
  // Duración: siempre en Y=158 (fija, nunca se mueve)
  // Título: centrado en zona 54-148, ajustado por número de líneas
  const DUR_Y=158;
  const TITLE_ZONE_TOP=54,TITLE_ZONE_BOT=o.duration?148:158;
  const titleZoneCenter=Math.round((TITLE_ZONE_TOP+TITLE_ZONE_BOT)/2);
  const titleBlockH=ls.length*LD;
  const sY=titleZoneCenter-Math.round(titleBlockH/2)+LD-4;

  const tl=ls.map((l,i)=>`<text x="${VW/2}" y="${sY+i*LD}" text-anchor="middle" font-family="-apple-system,BlinkMacSystemFont,sans-serif" font-size="10" font-weight="700" fill="#F0EBE0">${l}</text>`).join('');
  const dT=o.duration?`<text x="${VW/2}" y="${DUR_Y}" text-anchor="middle" font-family="-apple-system,BlinkMacSystemFont,sans-serif" font-size="8" font-weight="500" fill="${o.accent}">${o.duration}</text>`:'';

  const svg=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${VW} ${VH}">
    <rect width="${VW}" height="${VH}" fill="#1E1B17"/>
    <rect x="0" y="0" width="${VW}" height="${HDR_H}" fill="${o.hc}"/>
    <rect x="0" y="${HDR_H}" width="${VW}" height="1" fill="${o.sep}"/>
    <text x="${VW/2}" y="${HDR_Y1}" text-anchor="middle" font-family="-apple-system,BlinkMacSystemFont,sans-serif" font-size="8" font-weight="700" fill="${o.ht}" letter-spacing="0.8">${o.l1}</text>
    <text x="${VW/2}" y="${HDR_Y2}" text-anchor="middle" font-family="-apple-system,BlinkMacSystemFont,sans-serif" font-size="8" font-weight="700" fill="${o.ht}" letter-spacing="0.8">${o.l2}</text>
    <rect x="${BX}" y="${BY}" width="${BW}" height="${BH}" rx="3" fill="${o.bf}" stroke="${o.bs}" stroke-width="1"/>
    ${tl}
    ${dT}
    <rect x="0" y="${FY}" width="${VW}" height="16" fill="#161310"/>
    <text x="${VW/2}" y="${VH-5}" text-anchor="middle" font-family="-apple-system,BlinkMacSystemFont,sans-serif" font-size="6" font-weight="500" fill="#5A4E40" letter-spacing="1">${o.ft}</text>
  </svg>`;

  return `data:image/svg+xml,${encodeURIComponent(svg)}`;
}
function makeProgramPoster(title, duration, section){
  // Limpiar prefijos redundantes del título
  let t=title;
  t=t.replace(/^Cortos:\s*/i,'');
  t=t.replace(/^Prog\.\s*de\s*Cortos\s*[—-]\s*/i,'');
  t=t.replace(/^Programa\s*de\s*Cortos\s*[—-]\s*/i,'');

  const festName=((FESTIVAL_CONFIG&&FESTIVAL_CONFIG[_activeFestId])||Object.values(FESTIVAL_CONFIG||{})[0]||{}).shortName||'FESTIVAL';

  // Auto-lookup sección si no se pasa
  const sec=(section||(FILMS.find(f=>f.title===title)?.section)||'').toLowerCase();
  const isComp=sec.includes('comp')||sec.includes('competencia');

  const l1=isComp?'COMPETENCIA':'PROGRAMA';
  const l2='CORTOMETRAJES';

  return _buildPosterSVG({
    hc:'#3A8E8E',sep:'#1C5A5A',ht:'#051A1A',
    l1,l2,
    bf:'#0D2222',bs:'#1C4444',
    accent:'#4ABABA',
    title:t,duration:duration||null,
    ft:festName
  });
}
/* ══════════════════════════════════════════════════════
   SISTEMA DE PÓSTERS — fuente unificada y normalizada
   ─────────────────────────────────────────────────────
   FUENTES (en orden de prioridad):
     1. CUSTOM_POSTERS  — URLs manuales (Maspalomas, AnyMart…)
     2. SHORT_IMGS      — cortos: URLs directas TMDB/FICCI
     3. POSTERS         — features: URLs completas (TMDB o CDN propio)

   NORMALIZACIÓN:
     normKey(s) → convierte apostrofes Unicode → ASCII (U+0027)
     Se aplica a AMBOS lados (claves y título buscado).
     Previene mismatch entre U+2019 (tipográfico) y U+0027 (ASCII).

   REGLA: NUNCA acceder SHORT_IMGS/POSTERS/CUSTOM_POSTERS directamente
   en templates — siempre usar getPosterSrc(title, isCortos).
══════════════════════════════════════════════════════ */
function lbUrl(title){
  // Use festival-specific slug map from active festival config
  const _cfg=FESTIVAL_CONFIG[_activeFestId]||{};
  const _slugMap=_cfg.lbSlugs||LB_SLUGS;
  const slug=_slugMap[title]||LB_SLUGS[title];
  if(!slug) return`https://letterboxd.com/search/films/${encodeURIComponent(title)}/`;
  if(slug.startsWith('http')) return slug;
  return`https://letterboxd.com/film/${slug}/`;
}

function makeEventPoster(title,duration){
  const festName=((FESTIVAL_CONFIG&&FESTIVAL_CONFIG[_activeFestId])||Object.values(FESTIVAL_CONFIG||{})[0]||{}).shortName||'FESTIVAL';
  return _buildPosterSVG({
    hc:'#C8963E',sep:'#8A6228',ht:'#1A1410',
    l1:'INDUSTRY',l2:'DAYS',
    bf:'#252017',bs:'#3A3228',
    accent:'#C8963E',
    title,duration,
    ft:festName
  });
}

/* ══════════════════════════════════════════════════════════════
   MULTI-FESTIVAL — AFF 2026 data + config
══════════════════════════════════════════════════════════════ */
// ── Avisos de festival: funciones canceladas o reprogramadas ──────────────
// type: 'cancelled' | 'rescheduled'
// date: 'YYYY-MM-DD' de la función original — el banner desaparece al día siguiente
// Para 'rescheduled': añadir newDay, newTime, newVenue