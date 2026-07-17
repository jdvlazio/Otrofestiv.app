// ── src/view/helpers.js ───────────────────────────────────────────────────────
// p8 Step 6e — Shared view helpers (capa hoja de Wave 6).
// 27 funciones hoja: posters, day/venue/label utils, formato. Closure AST = 27,
// 0 deps arrastradas. Lets module-owned (DAY_SHORT/DAY_SHORT_EN/_CUSTOM_N/
// _POSTERS_N) + setters; main.js (loadFestival) los re-popula vía setters.
// _lang se lee vía STATE BRIDGE (globalThis) igual que el resto de la capa view.

import { FESTIVAL_CONFIG, TMDB_IMG } from '../config.js';
import {
  DAY_ABBR, DAY_NUM, ICONS, _buildPosterV16, _bandTextSVG, _secLabel, _sectionColor,
  makeProgramPoster, makeEventPoster, makeSorpresaPoster, escXML,
} from './components.js';
import { toMin, parseDur, simNow, simTodayStr, _festDate } from '../domain/time.js';
import { _resolveVenue, travelMins } from '../domain/festival.js';
import { state } from '../state/state.js';
import { t } from '../i18n/i18n.js';

// ── Lets module-owned (D-7-3) — re-populados por loadFestival vía setters ──────
let DAY_SHORT={Martes:'MAR 14',    Miércoles:'MIÉ 15',    Jueves:'JUE 16',
                 Viernes:'VIE 17',   Sábado:'SÁB 18',       Domingo:'DOM 19'};
let DAY_SHORT_EN={}; // swapeado por loadFestival() — valores en inglés
let _CUSTOM_N = {};
let _POSTERS_N = {}; // re-poblado vía setPosters(POSTERS) — POSTERS vive en main.js

export { DAY_SHORT_EN };

// normKey — privado del módulo
const normKey = s => s.replace(/[\u2018\u2019\u201A\u201B\u2032\u02BC]/g, "'");
// _EN_TO_I18N — privado (usado solo por _lblLocalized)
const _EN_TO_I18N = {MON:'day_short_lun',TUE:'day_short_mar',WED:'day_short_mie',
                     THU:'day_short_jue',FRI:'day_short_vie',SAT:'day_short_sab',SUN:'day_short_dom'};

// ── Setters (main.js muta el estado de festival vía estas) ────────────────────
export function setDayShort(m){ DAY_SHORT = m; }
export function setDayShortEn(m){ DAY_SHORT_EN = m; }
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

// Variante SIN TÍTULO para el sheet expandido (regla anti-repetición de Juan:
// el póster lleva el título solo cuando nadie más lo dice; en el sheet el título
// es la cabecera). Solo re-genera los GENERATIVOS con cuerpo vacío — la banda
// (y el num/día de programa, que es identidad) se conserva. Originales y
// editoriales pasan tal cual (el editorial ya omite el scrim sin body).
// Sorpresa queda intacta ("?" es marca, no eco del título).
export function getFilmPosterUntitled(f){
  const src=getFilmPoster(f);
  if(!src||!src.startsWith('data:image/svg+xml')) return src;      // no-generativo → tal cual
  if(f.title&&f.title.toLowerCase().includes('sorpresa')) return src;
  if(f.type==='event'){const _et=f.is_awards_screening?f.title.replace(/^Award Screening:\s*/i,''):f.title;return makeEventPoster(state,_et,f.duration,f.event_kind,f.section,{untitled:true});}
  if(f.is_cortos||(f.is_programa&&f.film_list&&f.film_list.length)) return makeProgramPoster(state,f.title,f.duration,f.section,{untitled:true});
  return _buildPosterV16({
    accent: _sectionColor(f.section||''),
    headerLabel: _secLabel(f.section||'')||'TRIBECA', // mismo fallback que getFilmPoster #8
    title: '',
    num: null
  });
}

export function getCortoItemPoster(item){
  if(!item) return null;
  // Nuevo formato (Jardín 2026+): poster directo en el objeto
  if(item.poster) return (item.poster.startsWith('http')||item.poster.startsWith('/assets/'))?item.poster:TMDB_IMG+item.poster;
  return getPosterSrc(item.title,true)||null;
}

// ── Fuente ÚNICA del póster de una OBRA (corto dentro de un programa) ──────────
// MISMA decisión editorial que posterModel(f) para films: un still 16:9 con
// posterSource "editorial" SIEMPRE va dentro del marco (banda + still sin
// recortar), nunca crudo en un slot 2:3. `_isEditorialPoster` lee posterSource/
// poster/title — campos que el item también tiene — así que la decisión es la
// misma en toda superficie. Devuelve {ed, accent, src, inner} donde `inner` son
// los hijos a meter en el contenedor sizer (que aporta tamaño y, si ed, la clase
// poster-ed + --ed-accent). Ninguna superficie de cortos debe volver a construir
// el <img> del still a mano — enforced por validate.py [poster-editorial-parity].
export function itemPosterParts(item, section, imgClass, {header=false}={}){
  const src=getCortoItemPoster(item)||makeProgramPoster(state,item.title,item.duration||'',section||'');
  if(_isEditorialPoster(item)){
    // thumb pequeño → still enmarcado SIN banda de texto (precedente _posterThumb);
    // card grande (Diario) → con banda de sección, como _recapPosterCard.
    return {ed:true, accent:_sectionColor(section||''), src,
      inner:editorialFrame(header?{header:_secLabel(section||''), src, title:item.title}:{src, title:item.title})};
  }
  return {ed:false, accent:'', src,
    inner:src?`<img class="${imgClass}" src="${src}" loading="lazy" onerror="this.remove()" alt="">`:''};
}

export function _getItemPoster(item){
  if(!item) return '';
  if(item.poster) return (item.poster.startsWith('http')||item.poster.startsWith('/assets/'))?item.poster:TMDB_IMG+item.poster;
  return getPosterSrc((item.title||item),false)||'';
}

// Una URL de poster es "editorial con imagen" (landscape 16:9 que va DENTRO del
// frame editorial, no recortado) si proviene de un CDN de stills oficiales del
// festival. Añadir un CDN nuevo = UNA línea en EDITORIAL_CDN_HOSTS. Lo robusto a
// largo plazo es declarar posterSource en el JSON (gana sobre el host); ver
// _isEditorialPoster + docs/POSTERS.md §5.
const EDITORIAL_CDN_HOSTS=['cloudfront.net','supabase.co']; // Tribeca, Olhar+
export function _isEditorialImageUrl(url){
  return !!(url && EDITORIAL_CDN_HOSTS.some(h=>url.includes(h)));
}

// Detección HÍBRIDA con default fail-safe (ver docs/POSTERS.md §5):
//   1. posterSource explícito gana (editorial→sí; tmdb/custom→no).
//   2. Si hay poster TMDB validado (map _POSTERS_N) → no (portrait, no 16:9).
//   3. Si no, auto por host CDN conocido.
// Default fail-safe: lo desconocido cae a NO-editorial → posterModel lo trata
// como image. Nunca se asume editorial sin señal, así que jamás se mete a la
// fuerza un 16:9 en un marco que no le corresponde por adivinanza.
export function _isEditorialPoster(f){
  if(!f) return false;
  if(f.posterSource==='editorial') return true;
  if(f.posterSource==='tmdb'||f.posterSource==='custom') return false;
  if(_POSTERS_N&&_POSTERS_N[normKey(f.title||'')]) return false;
  return _isEditorialImageUrl(f.poster);
}

// Header del poster editorial como SVG inline. El texto SVG NO está sujeto al
// minimumFontSize del WebView de Android (que infla el texto HTML pequeño — el
// label se veía gigante en Android; iOS WKWebView no tiene ese piso). Como los
// posters generativos (_buildPosterV16), el texto va en SVG y escala con el
// viewBox igual que el cqi anterior → mismo tamaño en navegadores modernos,
// sin regresión, y robusto donde el piso de font-size rompía el HTML.
export function _edHdrSVG(label, accent){
  if(!String(label||'').trim()) return '';
  // Banda única (misma fuente que el generativo): vw=100, anclado arriba, y el
  // <svg> propio del editorial escala vía CSS (.ed-hdr-svg / --ed-hdr-ratio).
  const {text, lines, lh}=_bandTextSVG(label, accent, 100, {mode:'top'});
  const VH=+(lines*lh+4).toFixed(2);
  return `<svg class="ed-hdr-svg" viewBox="0 0 100 ${VH}" preserveAspectRatio="xMidYMid meet">${text}</svg>`;
}

export function _posterThumb(f, cssClass, loading){
  const p = f ? getFilmPoster(f) : null;
  const _load = loading || 'lazy';

  if(!p){
    return `<div class="${cssClass}"></div>`;
  }

  if(f && _isEditorialPoster(f)){
    // Marco editorial único (thumb = banda + img, sin label). El contenedor
    // aporta tamaño (cssClass) + color (--ed-accent) + clase poster-ed.
    return `<div class="${cssClass} poster-ed" style="--ed-accent:${_sectionColor(f.section||'')}">`
      + editorialFrame({src:p, title:f.title, loading:_load})
      + `</div>`;
  }

  const _posStyle = _posterStyle(f);
  return `<img class="${cssClass}" src="${p}" loading="${_load}"${_posStyle} onerror="this.remove()" alt="">`;
}

// ── Modelo único de póster (unión discriminada) ───────────────────────────────
// Único lugar que decide "qué tipo de póster es este". Los call sites hacen
// switch sobre `kind` en vez de re-derivar flags. Ver docs/POSTERS.md.
//   image      → imagen real portrait: <img object-fit:cover>
//   editorial  → still landscape 16:9: marco editorial (banda + header + img)
//   generative → SVG generativo (el data-URI YA es un póster completo): <img>
//   empty      → sin imagen: placeholder
// `kind:'generative'` se distingue por el prefijo data-URI que producen los
// generadores; `editorial` por _isEditorialPoster (detección híbrida: posterSource
// gana, si falta auto por host). El default es seguro: lo que no es editorial ni
// generativo es image; sin src es empty — nunca se mete un 16:9 en un marco 2:3.
export function posterModel(f){
  if(!f) return {kind:'empty'};
  const src=getFilmPoster(f);
  if(!src) return {kind:'empty'};
  if(src.startsWith('data:image/svg+xml')) return {kind:'generative', src};
  if(_isEditorialPoster(f)) return {kind:'editorial', src, accent:_sectionColor(f.section||''), header:_secLabel(f.section||''), title:f.title||''};
  return {kind:'image', src, objectPosition:(f.posterPosition&&f.posterPosition!=='center')?f.posterPosition:'', title:f.title||''};
}

// ── Builder ÚNICO del marco editorial-con-imagen ──────────────────────────────
// Sustituye las 7 copias bespoke (grid/sheet/lista/thumb/agenda). Devuelve los
// HIJOS del marco (header SVG opcional + img + cuerpo opcional); el CONTENEDOR
// aporta tamaño y color: debe llevar la clase `poster-ed` y `style="--ed-accent:…"`
// (separación de responsabilidades — el contenedor es color/tamaño, el frame es
// contenido). Patrón: `<div class="<sizer> poster-ed" style="--ed-accent:${m.accent}">
// ${editorialFrame(m)}</div>`. `title` alimenta data-title para el fallback de
// error (_edPosterErr → póster generativo de toda la pieza). Todo texto va por
// escXML/_edHdrSVG. Ver docs/POSTERS.md.
//
// Anatomía A3 (Fase C): la zona de imagen es un blur-fill de fondo + el still
// 16:9 AL RAS del banner, SIN recortar (respeta composiciones con gente a los
// lados; el cover-crop las decapitaba) + un scrim con el título opcional. El
// blur es decorativo (aria-hidden); el still lleva data-title y el onerror que
// cae a generativo. `body` con texto → scrim con título (grid); undefined/''  →
// sin scrim (thumb/lista/sheet y ended-poster, que trae su propio footer).
export function editorialFrame({header, body, src, title, loading, accent}={}){
  const _l=loading||'lazy';
  const _dt=title?` data-title="${escXML(title)}"`:'';
  const hdr=`<div class="ed-hdr">${header?_edHdrSVG(header, accent):''}</div>`;
  const _ttl=(body!=null && String(body).trim()) ? String(body) : '';
  const img=src
    ? `<div class="ed-img">`
      + `<img class="ed-blur" src="${src}" loading="${_l}" aria-hidden="true" onerror="this.remove()" alt="">`
      + `<img class="ed-still" src="${src}"${_dt} loading="${_l}" onload="this.style.opacity='1'" onerror="_edPosterErr(this)" alt="">`
      + (_ttl?`<div class="ed-scrim"><div class="ed-title">${escXML(_ttl)}</div></div>`:'')
      + `</div>`
    : `<div class="ed-img"></div>`;
  return `${hdr}${img}`;
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

// Retraso colaborativo (Fase B) — badge informativo desde el consenso derivado.
// Pure string-builder. con = {state:'none'|'tentative'|'confirmed', delayMin, reporters}.
// "Solo informa": no toca el plan. Testeado en delayConsensusBadge.test.js.
export function delayConsensusBadge(con){
  if(!con || con.state==='none') return '';
  if(con.state==='confirmed'){
    return `<div class="delay-consensus confirmed"><span class="delay-warn-ico">${ICONS.alert}</span><span>${t('delay_consensus_confirmed',{min:con.delayMin})} · ${t('delay_consensus_reporters',{n:con.reporters})}<span class="delay-consensus-src">${t('delay_consensus_src')}</span></span></div>`;
  }
  return `<div class="delay-consensus tentative"><span>${t('delay_consensus_tentative')}<span class="delay-consensus-src">${t('delay_consensus_src')}</span></span></div>`;
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
  const _ds = _lang==='en' ? DAY_SHORT_EN : DAY_SHORT;
  // en: abreviatura del set lang-específico (no DAY_ABBR, que es ES); es: DAY_ABBR.
  const abr = (_lang!=='es' ? (_ds[key]||'').split(' ')[0] : null) || DAY_ABBR[key] || (_ds[key]||'').split(' ')[0] || key;
  const num = DAY_NUM[key]  || (_ds[key]||'').split(' ')[1] || '';
  return `<span class="day-chip-abr">${abr}</span><span class="day-chip-num">${num}</span>`;
};

export const dayLabel  = key => (_lang==='en' ? DAY_SHORT_EN : DAY_SHORT)[key] || key;

// dayLabelLong — formato largo "Viernes 5" / "Friday 5" / "Sexta 5". Mismo
// patrón que Planear (buildResultHTML). Pensado para el landmark del día en
// Mi Plan, unificando la lectura entre tabs.
export const dayLabelLong = key => {
  const dow = ['day_dom','day_lun','day_mar','day_mie','day_jue','day_vie','day_sab'];
  const iso = FESTIVAL_DATES[key] || key;
  const d = new Date(iso + 'T12:00:00');
  if(isNaN(d.getTime())) return key;
  return `${t(dow[d.getDay()])} ${d.getDate()}`;
};

export const _lblLocalized = lbl => {
  if(_lang==='en') return lbl;
  const key = _EN_TO_I18N[lbl];
  return key ? t(key) : lbl;
};

export const durFmt    = d   => d ? (String(d).includes('min') ? String(d) : String(d)+' min') : '';

// _minFmt(m) — minutos (número) → "1 h 45" / "45 min". Para los detalles del conflicto
// por desplazamiento ("~1 h 45 de viaje · 1 h 05 de hueco"). durFmt formatea la duración
// de una actividad (string del JSON); esto formatea un cómputo nuestro.
export const _minFmt   = m   => {
  const _m=Math.max(0,Math.round(m||0)), h=Math.floor(_m/60), mn=_m%60;
  return h ? `${h} h${mn?' '+String(mn).padStart(2,'0'):''}` : `${mn} ${t('label_min')}`;
};

export const flagFmt   = fl  => fl||'';

export function _langDates(cfg) {
  return (_lang==='en' && cfg && cfg.dates_en) ? cfg.dates_en : (cfg && cfg.dates)||'';
}

export function _mkCortoItemHtml(item, n, {cls='mplan-prog-item', section='', ratingEl=''}={}){
  // Póster por la fuente única: en tamaño thumb el marco va SIN texto en la
  // banda (solo color de sección + still), como los thumbs editoriales de films
  // (_posterThumb). UN solo póster propio en todas las superficies.
  const _pp=itemPosterParts(item, section, 'c-film-thumb');
  const thumb=_pp.src;
  const thumbHtml=_pp.ed
    ? `<div class="c-film-thumb poster-ed" style="--ed-accent:${_pp.accent}">${_pp.inner}</div>`
    : `<img src="${thumb}" class="c-film-thumb" loading="lazy" onerror="this.remove()" alt="">`;
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
    // Marco editorial único (lista = banda + img, sin label). Contenedor
    // .plist-poster aporta tamaño; poster-ed el flex; --ed-accent el color.
    return '<div class="plist-poster poster-ed" style="--ed-accent:'+_sectionColor(f.section||'')+'">'+
      editorialFrame({src, title:f.title})+
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
