// ── src/view/helpers.js ───────────────────────────────────────────────────────
// p8 Step 6e — Shared view helpers (capa hoja de Wave 6).
// 27 funciones hoja: posters, day/venue/label utils, formato. Closure AST = 27,
// 0 deps arrastradas. Lets module-owned (DAY_SHORT/DAY_SHORT_EN/_CUSTOM_N/
// _POSTERS_N) + setters; main.js (loadFestival) los re-popula vía setters.
// _lang se lee vía STATE BRIDGE (globalThis) igual que el resto de la capa view.

import { FESTIVAL_CONFIG, TMDB_IMG } from '../config.js';
import {
  DAY_ABBR, DAY_NUM, ICONS, _buildPosterV16, _secLabel, _sectionColor,
  makeProgramPoster, makeEventPoster, makeSorpresaPoster,
} from './components.js';
import { toMin, parseDur, simNow, simTodayStr, _festDate } from '../domain/time.js';
import { _resolveVenue, travelMins } from '../domain/festival.js';
import { state } from '../state/state.js';
import { t } from '../i18n/i18n.js';

// ── Lets module-owned (D-7-3) — re-populados por loadFestival vía setters ──────
let DAY_SHORT={Martes:'MAR 14',    Miércoles:'MIÉ 15',    Jueves:'JUE 16',
                 Viernes:'VIE 17',   Sábado:'SÁB 18',       Domingo:'DOM 19'};
let DAY_SHORT_EN={}; // swapeado por loadFestival() — valores en inglés
let DAY_SHORT_PT={}; // swapeado por loadFestival() — valores en pt-BR
let _CUSTOM_N = {};
let _POSTERS_N = {}; // re-poblado vía setPosters(POSTERS) — POSTERS vive en main.js

export { DAY_SHORT_EN, DAY_SHORT_PT };

// normKey — privado del módulo
const normKey = s => s.replace(/[\u2018\u2019\u201A\u201B\u2032\u02BC]/g, "'");
// _EN_TO_I18N — privado (usado solo por _lblLocalized)
const _EN_TO_I18N = {MON:'day_short_lun',TUE:'day_short_mar',WED:'day_short_mie',
                     THU:'day_short_jue',FRI:'day_short_vie',SAT:'day_short_sab',SUN:'day_short_dom'};

// ── Setters (main.js muta el estado de festival vía estas) ────────────────────
export function setDayShort(m){ DAY_SHORT = m; }
export function setDayShortEn(m){ DAY_SHORT_EN = m; }
export function setDayShortPt(m){ DAY_SHORT_PT = m; }
export function setPosters(p){ _POSTERS_N = Object.fromEntries(Object.entries(p||{}).map(([k,v])=>[normKey(k),v])); }
export function setCustomPosters(c){ _CUSTOM_N = Object.fromEntries(Object.entries(c||{}).map(([k,v])=>[normKey(k),v])); }

// ── 27 helpers hoja (orden original de main.js) ───────────────────────────────
export function _posterStyle(f){
  const pos=f&&f.posterPosition;
  return (pos&&pos!=='center')?` style="object-position:${pos}"`:'';
}

export function getPosterSrc(title, isCortos, section){
  const t = normKey(title);
  if(_CUSTOM_N[t]) return _CUSTOM_N[t];
  if(_POSTERS_N[t]) return (_POSTERS_N[t].startsWith('http')||_POSTERS_N[t].startsWith('/assets/'))?_POSTERS_N[t]:TMDB_IMG+_POSTERS_N[t];
  if(isCortos) return null;
  return null;
}

export function getFilmPoster(f){
  if(!f) return null;
  // 1. Custom poster siempre primero
  const _cn=normKey(f.title||'');
  if(_CUSTOM_N[_cn]) return _CUSTOM_N[_cn];
  // 2. Eventos — siempre poster ámbar generativo (ignora f.poster/TMDB)
  if(f.type==='event'){const _et=f.is_awards_screening?f.title.replace(/^Award Screening:\s*/i,''):f.title;return f.poster||makeEventPoster(state,_et,f.duration,f.event_kind,f.section);}
  // 3. Proyección sorpresa
  if(f.title&&f.title.toLowerCase().includes('sorpresa')) return makeSorpresaPoster();
  // 4. Cortos
  if(f.is_cortos) return f.poster||getPosterSrc(f.title,true)||makeProgramPoster(state,f.title,f.duration,f.section);
  // 5. Programa combinado
  if(f.is_programa&&f.film_list&&f.film_list.length){
    const first=f.film_list[0];
    if(first.poster) return (first.poster.startsWith('http')||first.poster.startsWith('/assets/'))?first.poster:TMDB_IMG+first.poster;
    return getPosterSrc(first.title||first,false)||getPosterSrc(f.title,false)||makeProgramPoster(state,f.title,f.duration,f.section);
  }
  // 6. TMDB — poster real (prioridad sobre editorial cloudfront)
  const _tmdb=getPosterSrc(f.title,false);
  if(_tmdb) return _tmdb;
  // 7. f.poster directo — editorial cloudfront o formato Jardín 2026
  if(f.poster) return (f.poster.startsWith('http')||f.poster.startsWith('/assets/'))?f.poster:TMDB_IMG+f.poster;
  // 8. Poster generativo
  return _buildPosterV16({
    accent: _sectionColor(f.section||''),
    headerLabel: _secLabel(f.section||'')||'TRIBECA',
    title: f.title,
    num: null
  });
}

export function getCortoItemPoster(item){
  if(!item) return null;
  // Nuevo formato (Jardín 2026+): poster directo en el objeto
  if(item.poster) return (item.poster.startsWith('http')||item.poster.startsWith('/assets/'))?item.poster:TMDB_IMG+item.poster;
  return getPosterSrc(item.title,true)||null;
}

export function _getItemPoster(item){
  if(!item) return '';
  if(item.poster) return (item.poster.startsWith('http')||item.poster.startsWith('/assets/'))?item.poster:TMDB_IMG+item.poster;
  return getPosterSrc((item.title||item),false)||'';
}

// Una URL de poster es "editorial con imagen" (landscape 16:9 que va DENTRO del
// frame editorial, no recortado) si proviene de un CDN de stills oficiales del
// festival. Hosts conocidos: cloudfront.net (Tribeca), supabase.co (Olhar+).
export function _isEditorialImageUrl(url){
  return !!(url && (url.includes('cloudfront.net') || url.includes('supabase.co')));
}

export function _isEditorialPoster(f){
  if(!f) return false;
  if(f.posterSource==='editorial') return true;
  if(f.posterSource==='tmdb'||f.posterSource==='custom') return false;
  // Si hay poster TMDB validado, no es editorial — son formatos incompatibles (portrait vs 16:9)
  if(_POSTERS_N&&_POSTERS_N[normKey(f.title||'')]) return false;
  return _isEditorialImageUrl(f.poster);
}

export function _posterThumb(f, cssClass, loading){
  const p = f ? getFilmPoster(f) : null;
  const _load = loading || 'lazy';

  if(!p){
    return `<div class="${cssClass}"></div>`;
  }

  if(f && _isEditorialPoster(f)){
    const color = _sectionColor(f.section || '');
    // Misma estructura que .poster-card.editorial en Programa Grid:
    // band (28.89%) + div flex:1 con img cover center-top
    return `<div class="${cssClass} ${cssClass}-ed" style="background:${color}">`
      + `<div style="height:28.89%;flex-shrink:0"></div>`
      + `<div style="flex:1;overflow:hidden;min-height:0">`
      + `<img src="${p}" style="width:100%;height:100%;object-fit:cover;object-position:center top;display:block" loading="${_load}" onerror="this.remove()" alt="">`
      + `</div>`
      + `</div>`;
  }

  const _posStyle = _posterStyle(f);
  return `<img class="${cssClass}" src="${p}" loading="${_load}"${_posStyle} onerror="this.remove()" alt="">`;
}

export function isNowShowing(f){
  const dateStr=FESTIVAL_DATES[f.day];if(!dateStr) return false;
  const now=simNow();
  const start=_festDate(dateStr,f.time);
  const dur=f.duration?parseInt(f.duration):90;
  const end=new Date(start.getTime()+dur*60000);
  return now>=start&&now<=end;
}

export function isToday(day){
  const dateStr=FESTIVAL_DATES[day];
  if(!dateStr) return false;
  const today=simTodayStr();
  return dateStr===today;
}

export function vcfg(v){
  const festVenues=(FESTIVAL_CONFIG[_activeFestId]||{}).venues||{};
  return _resolveVenue(v,festVenues);
}

export function sala(v){const m=v.match(/Sala\s*(\d+)/)||v.match(/Sal[oó]n\s*(\d+)/i);return m?'Sala '+m[1]:'';}

export function travelWarn(s1,s2){
  if(s1.day!==s2.day) return null;
  const travel=travelMins(s1.venue,s2.venue);
  if(travel===0) return null;
  const gap=toMin(s2.time)-(toMin(s1.time)+parseDur(s1.duration));
  if(gap<travel+10){
    const _modo=FESTIVAL_TRANSPORT==='walking'?t('warn_a_pie'):FESTIVAL_TRANSPORT==='transit'?null:t('warn_en_carro');
    return`${ICONS.alert} ~${travel} min${_modo?' '+_modo:''} ${t('warn_entre_sedes')}`;
  }
  return null;
}

export function mplanEndStr(t,d){const m=toMin(t)+d;return String(Math.floor(m/60)%24).padStart(2,'0')+':'+String(m%60).padStart(2,'0');}

export function mplanBlockType(s){
  const f=FILMS.find(fi=>fi.title===s._title);
  if(f&&f.type==='event') return'mp-event';
  if(prioritized.has(s._title)) return'mp-priority';
  if(f&&f.is_cortos) return'mp-program';
  return'mp-regular';
}

export const dayChip = key => {
  const _ds = _lang==='pt' ? DAY_SHORT_PT : _lang==='en' ? DAY_SHORT_EN : DAY_SHORT;
  // pt/en: abreviatura del set lang-específico (no DAY_ABBR, que es ES); es: DAY_ABBR.
  const abr = (_lang!=='es' ? (_ds[key]||'').split(' ')[0] : null) || DAY_ABBR[key] || (_ds[key]||'').split(' ')[0] || key;
  const num = DAY_NUM[key]  || (_ds[key]||'').split(' ')[1] || '';
  return `<span class="day-chip-abr">${abr}</span><span class="day-chip-num">${num}</span>`;
};

export const dayLabel  = key => (_lang==='pt' ? DAY_SHORT_PT : _lang==='en' ? DAY_SHORT_EN : DAY_SHORT)[key] || key;

export const _lblLocalized = lbl => {
  if(_lang==='en') return lbl;
  const key = _EN_TO_I18N[lbl];
  return key ? t(key) : lbl;
};

export const durFmt    = d   => d ? (String(d).includes('min') ? String(d) : String(d)+' min') : '';

export const flagFmt   = fl  => fl||'';

export function _langDates(cfg) {
  return (_lang==='en' && cfg && cfg.dates_en) ? cfg.dates_en : (cfg && cfg.dates)||'';
}

export function _mkCortoItemHtml(item, n, {cls='mplan-prog-item', section='', ratingEl=''}={}){
  // Mismo fallback que openCortoSheet: real → generativo. Nunca emoji.
  const thumb=getCortoItemPoster(item)||makeProgramPoster(state,item.title,item.duration||'',section);
  const thumbHtml=`<img src="${thumb}" class="c-film-thumb" loading="lazy" onerror="this.remove()" alt="">`;
  // data-* attrs — nunca interpolar strings con contenido variable en onclick
  const _dt=encodeURIComponent(item.title||'');
  const _dc=encodeURIComponent(item.country||'');
  const _dd=encodeURIComponent(item.duration||'');
  const _dir=encodeURIComponent(item.director||'');
  const _dg=encodeURIComponent(item.genre||'');
  const _ds=encodeURIComponent((item.synopsis||'').slice(0,200));
  // data-cp: poster resuelto en render time — viaja directo al sheet, sin re-lookup
  const _dp=encodeURIComponent(thumb||'');
  return`<div class="${cls}" data-ct="${_dt}" data-cc="${_dc}" data-cd="${_dd}" data-cdir="${_dir}" data-cg="${_dg}" data-cs="${_ds}" data-cp="${_dp}" data-action="openCortoSheetFromEl">
    ${thumbHtml}
    <div style="flex:1;min-width:0">
      <div class="row-baseline">
        <span class="mplan-prog-num">${n+1}</span>
        <span class="mplan-prog-title">${item.title}</span>
      </div>
      <div class="indent-nested mplan-prog-dur">${item.country?item.country+' · ':''}${durFmt(item.duration)}</div>
    </div>
    ${ratingEl}
  </div>`;
}

export function starsText(r){
  if(!r) return '';
  const full=Math.floor(r);
  const half=(r%1)>=0.5;
  return '★'.repeat(full)+(half?'½':'');
}

export function _dayChips(screenings){
  const seen=new Set();
  return screenings
    .map(s=>s.day)
    .filter(d=>{if(seen.has(d))return false;seen.add(d);return true;})
    .map(d=>`<span class="pelicula-day" data-day="${d}">${dayLabel(d)}</span>`)
    .join('<span style="color:var(--gray2)"> · </span>');
}

export function _metaBadges(f){
  let b='';
  if(f.has_qa) b+=`<span class="meta-badge">Q&A</span>`;
  if(f.requires_registration) b+=`<span class="meta-badge">${t('badge_inscripcion')}</span>`;
  // Festival mixto: marcar función gratuita (discrimina — solo las gratis, no todas).
  if((FESTIVAL_CONFIG[_activeFestId]||{}).ticketing_model==='mixed'&&f.is_free===true)
    b+=`<span class="meta-badge">${t('badge_gratis')}</span>`;
  return b;
}

export function _programaStack(f){
  if(!f.is_programa||!f.film_list||f.film_list.length<2) return null;
  const p1=_getItemPoster(f.film_list[0]);
  const p2=_getItemPoster(f.film_list[1]);
  const imgB=p2?`<img class="ps-back" src="${p2}" loading="lazy" onerror="this.remove()" alt="">`:"<div class='ps-back'></div>";
  const imgF=p1?`<img class="ps-front" src="${p1}" loading="lazy" onerror="this.remove()" alt="">`:"<div class='ps-front'></div>";
  return`<div class="plist-poster-stack">${imgB}${imgF}</div>`;
}

export function _plistPosterHtml(f, src){
  if(_isEditorialPoster(f)){
    var _accent=_sectionColor(f.section||'');
    var _imgSection=src
      ?'<div style="flex:1;overflow:hidden;min-height:0"><img src="'+src+'" loading="lazy" onerror="this.remove()" alt="" style="width:100%;height:100%;object-fit:cover;object-position:center top;display:block"></div>'
      :'<div style="flex:1;background:#1A1A1A"></div>';
    return '<div class="plist-poster" style="background:'+_accent+';display:flex;flex-direction:column;overflow:hidden">'+
      '<div style="height:28.89%;flex-shrink:0"></div>'+
      _imgSection+
    '</div>';
  }
  return src?'<div class="plist-poster"><img src="'+src+'" loading="lazy" onerror="this.remove()" alt="" style="width:100%;height:100%;object-fit:cover;border-radius:var(--r-sm)"></div>':'<div class="plist-poster"></div>';
}

// ── Step 6f addendum: shared leaves (emptyState/emptyStateHero/DAYS) ───────────
// Compartidas por agenda/programa/cartelera. Templates puros (params only).
export const emptyState = (icon, title, sub='') =>
  `<div class="empty-state">
    <div class="empty-state-icon">${icon}</div>
    <div class="empty-state-title">${title}</div>
    ${sub ? `<div class="empty-state-sub">${sub}</div>` : ''}
  </div>`;

// Hero: para pantallas completas vacías — Mi Plan, Intereses, Planear
// REGLA: CTA primario → .empty-state-cta (ámbar sólido, texto negro). Secundario → pasar ctaSecondary=true
export const emptyStateHero = (icon, title, sub='', ctaLabel='', ctaTab='', ctaSecondary=false) =>
  `<div class="empty-state-hero">
    <div class="empty-state-icon">${icon}</div>
    <div class="empty-state-title">${title}</div>
    ${sub ? `<div class="empty-state-sub">${sub}</div>` : ''}
    ${ctaLabel ? `<button class="${ctaSecondary?'empty-state-cta-sec':'empty-state-cta'}" data-action="navTo" data-tab="${ctaTab}">${ctaLabel}</button>` : ''}
  </div>`;

// DAYS — array de días del festival activo. Mutado IN-PLACE por loadFestival
// (main.js): DAYS.length=0; cfg.days.forEach(d=>DAYS.push(d)). El binding
// importado refleja la mutación (mismo objeto array). No reasignar.
export const DAYS=[];
