// ── src/view/helpers.js ───────────────────────────────────────────────────────
// p8 Step 6e — Shared view helpers (capa hoja de Wave 6).
// 27 funciones hoja: posters, day/venue/label utils, formato. Closure AST = 27,
// 0 deps arrastradas. Lets module-owned (DAY_SHORT/DAY_SHORT_EN/_CUSTOM_N/
// _POSTERS_N) + setters; main.js (loadFestival) los re-popula vía setters.
// _lang se lee vía STATE BRIDGE (globalThis) igual que el resto de la capa view.

import { FESTIVAL_BUFFER, FESTIVAL_QA_MIN, FESTIVAL_CONFIG, TMDB_IMG } from '../config.js';
import {
  DAY_ABBR, DAY_NUM, ICONS, _buildPosterMini, _buildPosterV16, _datoCompuesto, _fitLines, _secLabel, _seccionPartes, _sectionColor,
  makeProgramPoster, makeEventPoster, makeSorpresaPoster, makeSharedSlotSVG, escXML, _langDates, parseProgramTitle,
} from './components.js';
// _langDates se REEXPORTA: el dueño vive en components.js (helpers importa
// components — el ciclo decide dónde vive; ver el comentario del dueño).
export { _langDates };
import { toMin, minToStr, parseDur, durEstimada, simNow, simTodayStr, _festDate, _festNowMin } from '../domain/time.js';
import { blockDuration, effectiveDuration, screeningBlockEndMin, screeningQaOnly } from '../domain/film.js';
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
  // Regla de carga (Juan, 24 ago): rótulo = primera oración; la firma de
  // curaduría solo baja al pie con TÍTULO SIMPLE — con pila/compuesto cede y
  // vive en la ficha. Tres voces: sección, cuerpo, pie.
  const _partes=_seccionPartes(_secLabel(f.section||''));
  const _compuesto=/\s\+\s/.test(f.title||'');
  return _buildPosterV16({
    accent: _sectionColor(f.section||''),
    headerLabel: _partes.rotulo||'TRIBECA',
    title: f.title,
    num: null,
    dato: _datoCompuesto(f.title, f.duration), // «3 obras · 99 min» si es compuesto
    firma: _compuesto?null:_partes.firma
  });
}

// ── LA MINI para superficies de 56px (mejora 1, auditoría Apple Music) ──────
// Espeja las decisiones de getFilmPoster y solo sustituye los caminos que
// terminarían en la Forma A generativa: custom/evento/sorpresa/TMDB/editorial
// pasan tal cual (la sorpresa conserva su «?», que es marca). El chip de la
// lista y el thumb de cortos muestran el título AL LADO, así que acá el
// generativo responde con UNA voz: ordinal de serie o la marca de la obra
// (_buildPosterMini). El GRID no pasa por acá — queda tipográfico puro
// (decisión de Juan, 25 ago: la marca en grande era «demasiado ruidosa»).
export function getFilmPosterMini(f){
  const src=getFilmPoster(f);
  if(!src||!String(src).startsWith('data:image/svg')) return src;   // póster real
  if(f&&f.type==='event') return src;                                // evento: ámbar propio
  if(f&&f.title&&f.title.toLowerCase().includes('sorpresa')) return src; // la «?» es marca
  return _buildPosterMini({
    accent:_sectionColor(f&&f.section||''),
    title:f&&f.title||'',
    esPrograma:!!(f&&(f.is_cortos||f.is_programa)),
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
    headerLabel: _seccionPartes(_secLabel(f.section||'')).rotulo||'TRIBECA', // mismo rótulo que #8
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
  // Sin póster propio: la CARD grande (header) conserva el generativo entero;
  // el thumb de 56px recibe la mini — la marca de la obra, su título va al lado.
  const src=getCortoItemPoster(item)
    ||(header?makeProgramPoster(state,item.title,item.duration||'',section||'')
             :_buildPosterMini({accent:_sectionColor(section||''), title:item.title, esPrograma:false}));
  if(_isEditorialPoster(item)){
    // thumb pequeño → still enmarcado SIN banda de texto (precedente _posterThumb);
    // card grande (Diario) → con banda de sección, como _recapPosterCard.
    // Filete de la MINIATURA en ámbar de marca, no en color de sección (Juan, 19
    // ago): los cortos de un programa comparten sección, así que ese color no
    // informa —y sin arquetipo cae al gris #2C2C2A, la barra gris repetida que
    // él vio—. En la TAPA (header) se conserva: ahí sí orienta al scrollear.
    return {ed:true, accent:header?_sectionColor(section||''):'var(--amber)', src,
      inner:editorialFrame(header?{header:_secLabel(section||''), src, title:item.title}:{src, title:item.title})};
  }
  return {ed:false, accent:'', src,
    inner:src?`<img class="${imgClass}" src="${src}" loading="lazy" onerror="this.remove()" alt="">`:''};
}

// ── posterAmbient — color ambiental del póster (decisión Juan 18 jul 2026) ────
// ÚNICO sampler de color de la app (guardián [poster-ambient]: getImageData
// prohibido fuera de este módulo). Extrae el color dominante VIBRANTE del póster
// (bucket cuantizado con mejor saturación×√frecuencia, ignorando casi-negros y
// casi-blancos) y lo DOMA a la paleta: saturación tope .55, luminancia .30–.42 —
// nunca un neón, nunca compite con el ámbar. CORS sin permiso (CDNs ajenos, ej.
// Tribeca) → fallback al acento de sección, mismo clamp. cb recibe [r,g,b] o
// null (sin src ni fallback). Cache por src — un póster se muestrea una vez.
const _ambCache=new Map();
function _hexToRgb(h){const c=String(h||'').replace('#','');return c.length>=6?[parseInt(c.slice(0,2),16),parseInt(c.slice(2,4),16),parseInt(c.slice(4,6),16)]:null;}
function _clampAmb(r,g,b){
  r/=255;g/=255;b/=255;
  const mx=Math.max(r,g,b),mn=Math.min(r,g,b);let h=0,s=0;const l=(mx+mn)/2;
  if(mx!==mn){const d=mx-mn;s=l>.5?d/(2-mx-mn):d/(mx+mn);
    h=mx===r?((g-b)/d+(g<b?6:0)):mx===g?((b-r)/d+2):((r-g)/d+4);h/=6;}
  s=Math.min(s,.55);const l2=Math.max(.30,Math.min(l,.42));
  const q=l2<.5?l2*(1+s):l2+s-l2*s,p=2*l2-q;
  const f=t=>{t=(t%1+1)%1;return t<1/6?p+(q-p)*6*t:t<1/2?q:t<2/3?p+(q-p)*(2/3-t)*6:p;};
  return [f(h+1/3),f(h),f(h-1/3)].map(x=>Math.round(x*255));
}
export function posterAmbient(src,fallbackHex,cb){
  const _fb=()=>{const rgb=_hexToRgb(fallbackHex);cb(rgb?_clampAmb(...rgb):null);};
  if(!src||src.startsWith('data:')){_fb();return;}
  if(_ambCache.has(src)){const v=_ambCache.get(src);v?cb(v):_fb();return;}
  // Safari iOS sirve del caché HTTP la entrada SIN CORS que dejó el <img> de la
  // ficha → el pedido crossOrigin falla y caía al fallback (bug MU-KI-RA ciruela,
  // 18 jul). URL distinta = entrada de caché propia: TMDB baja a w92 (~5KB, de
  // sobra para 24×24); otros dominios llevan query param. Same-origin no taintea.
  let _src=src;
  if(/^https?:/.test(src)&&!src.startsWith(location.origin)){
    _src=src.includes('image.tmdb.org/t/p/w')?src.replace(/\/t\/p\/w\d+/,'/t/p/w92')
        :src+(src.includes('?')?'&':'?')+'amb=1';
  }
  const img=new Image();img.crossOrigin='anonymous';
  img.onload=()=>{try{
    const N=24,c=document.createElement('canvas');c.width=N;c.height=N;
    const x=c.getContext('2d');x.drawImage(img,0,0,N,N);
    const d=x.getImageData(0,0,N,N).data;const buckets=new Map();
    for(let i=0;i<d.length;i+=4){const k=(d[i]>>5)+'.'+(d[i+1]>>5)+'.'+(d[i+2]>>5);buckets.set(k,(buckets.get(k)||0)+1);}
    let best=null;
    for(const[k,n]of buckets){const[qr,qg,qb]=k.split('.').map(v=>v*32+16);
      const mx=Math.max(qr,qg,qb)/255,mn=Math.min(qr,qg,qb)/255,l=(mx+mn)/2;
      if(l<.08||l>.92)continue;
      const s=mx===mn?0:(l>.5?(mx-mn)/(2-mx-mn):(mx-mn)/(mx+mn));
      // Puntaje por ÁREA (s×n, decisión Juan 18 jul): gana el color que domina
      // el póster, no un acento chico ultra-saturado (con √n, las letras magenta
      // de MU-KI-RA le ganaban a la selva). Piso de saturación .12: dominante
      // casi-gris → mejor el acento de sección que un tinte barro.
      const score=s*n;
      if(!best||score>best[0])best=[score,qr,qg,qb,s];}
    const rgb=(best&&best[4]>=.12)?_clampAmb(best[1],best[2],best[3]):null;
    _ambCache.set(src,rgb);rgb?cb(rgb):_fb();
  }catch(e){_ambCache.set(src,null);_fb();}};
  img.onerror=()=>{_ambCache.set(src,null);_fb();};
  img.src=_src;
}

// ── posterParts — puente RENDER de posterModel (films) ────────────────────────
// posterModel(f) es LA decisión (kind/src/accent); posterParts la vuelve HTML de
// la rama editorial. Análogo de itemPosterParts para films: toda superficie que
// pinte un film editorial DEBE pasar por aquí — nadie re-deriva _isEditorialPoster
// ni llama editorialFrame directo (guardián [poster-single-owner]). La rama
// `image`/`generative` conserva su <img> por superficie (clases/transiciones
// propias) usando .src — la DECISIÓN ya viene tomada.
// ── slotPosterParts — la DECISIÓN del póster de función compartida ───────────
// Dueño del modelo (como posterParts): clasifica cada obra del slot y decide si
// la función tiene póster propio. Reglas de la revisión exhaustiva (21 ago):
//   · SOLO Tipo 2 (slot anclado) de 2-3 obras — con 4+ no hay tarjeta (mostrar
//     3 de 6 sería curaduría nuestra sobre curaduría ajena).
//   · La Escalera existe SOLO COMPLETA (Juan, 21 ago): 2-3 obras y TODOS los
//     afiches reales (!_isEditorialPoster). Un still va dentro del marco
//     editorial —ya es un póster propio— y no puede ser módulo; y el «módulo
//     mudo» que probamos para los incompletos se leía como sombra sucia y la
//     tarjeta se hacía pasar por la única obra visible. Falta un afiche → null:
//     cada obra conserva su card, como hoy. Nada se inventa.
//   · Delantero = primera obra en orden de catálogo (regla neutra).
// El dibujo lo hace components.makeSharedSlotSVG — acá solo el modelo.
// programParts — el póster de una función que agrupa 2-3 obras, sea programa
// legacy («A + B», is_programa) o de cortos (is_cortos, como se modelan hoy).
// Arregla una mentira vieja: getFilmPoster (camino 5) devuelve el afiche de la
// PRIMERA obra, así que «Esperando abril + Los bandidos del hotel azul» se
// mostraba como si fuera «Esperando abril» sola. Con la Escalera dice la verdad.
// Antes se llamaba legacyProgramParts y solo miraba is_programa: las 31
// funciones de cortos de 2-3 obras caían al generativo teniendo los afiches.
// Devuelve null si no califica (afiche incompleto, still, 4+) → camino viejo.
export function programParts(f){
  if(!f||!(f.is_programa||f.is_cortos)||!Array.isArray(f.film_list)) return null;
  // EL AFICHE DEL FESTIVAL MANDA (regla de Juan, 26 ago 2026). La Escalera es un
  // póster NUESTRO: solo tiene sentido cuando el festival no mandó uno para la
  // función. Si el programa trae el suyo —«Competencia de cortos Programa 1»,
  // las secciones de Cinemancia, los programas de CineAutopsia— ese gana, y la
  // pila no se dibuja. Medido antes de la regla: de 59 compuestos que dibujaban
  // Escalera, 19 tapaban el afiche oficial (Cinemancia y Leviza, publicados).
  // El orden es jerarquía, no preferencia: oficial del programa → Escalera con
  // los afiches oficiales de TODAS sus obras → generativo nuestro.
  if(f.poster) return null;
  return slotPosterParts(f.film_list.map(it=>({
    title:it.title, poster:it.poster, posterSource:it.posterSource,
    duration:it.duration||f.duration, section:f.section,
  })));
}

export function slotPosterParts(members){
  // Tope 8 (prototipo aprobado, 25 ago): la Escalera escala a cualquier N porque
  // el paso es fracción de la lámina — ver makeSharedSlotSVG. Con 9+ la lámina
  // baja del 23% y a 56px queda en textura, así que ahí sí cae a la forma vieja.
  if(!Array.isArray(members)||members.length<2||members.length>8) return null;
  const clasif=members.map(f=>{
    const src=getPosterSrc(f.title,true)||f.poster||null;
    const real=!!src&&!_isEditorialPoster(f);
    return {f, src:real?src:null};
  });
  if(clasif.some(c=>!c.src)) return null;   // solo completa: falta un afiche → sin tarjeta
  const reales=clasif;
  // atrás→delante: el 1º del catálogo queda delante
  const modules=[...reales.slice(1).reverse().map(c=>c.src), reales[0].src];
  const lider=reales[0].f;
  const dur=blockDuration(lider);
  const dato=`${members.length} ${t('misc_peliculas')}${dur?` · ${dur} min`:''}`;
  return {modules, secLabel:_secLabel(lider.section||''), accent:_sectionColor(lider.section||''), dato,
    svg:makeSharedSlotSVG({modules, secLabel:_secLabel(lider.section||''), accent:_sectionColor(lider.section||''), dato})};
}

export function posterParts(f,{header=false,body='',loading}={}){
  const m=posterModel(f);
  if(m.kind!=='editorial') return m;                       // {kind,src,...} decidido
  return {...m, ed:true,
    inner:editorialFrame({header:header?m.header:undefined, body, src:m.src, title:m.title, loading, accent:m.accent, firma:body?m.firma:undefined})};
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
  // Sin accent el <text> salía con fill="undefined" y el navegador lo pintaba
  // NEGRO: la sección quedaba invisible sobre el fondo oscuro (lo vio Juan en la
  // tarjeta de ENCUENTRO). El filete no lo delataba porque toma su color del CSS
  // (--ed-accent), no de este argumento. Ahora el color siempre existe.
  const _fill=String(accent||'').trim()||'var(--amber)';
  // Mismo motor que la forma A (_fitLines), vw=100. Con imagen la sección baja a
  // 2 líneas: la imagen carga el peso (§6.0). Caja = 8u menos margen de 0,75u.
  const U=100/8, M=0.75*U, CW=100-2*M;
  const fit=_fitLines(String(label).toUpperCase(),
    {boxW:CW, boxH:2.4*U, maxLines:2, fsMax:2.4*U/1.16, fsMin:5, lhRatio:1.16, lsEm:0.02, upper:true});
  const round=n=>+n.toFixed(2);
  const VH=+(fit.lines.length*fit.lh+fit.fs*0.3).toFixed(2);
  const text=fit.lines.map((l,i)=>
    `<text x="${round(M)}" y="${round(fit.fs+i*fit.lh)}" font-family="-apple-system,BlinkMacSystemFont,sans-serif" font-size="${round(fit.fs)}" font-weight="800" letter-spacing="${round(fit.fs*0.02)}" fill="${_fill}">${escXML(l)}</text>`
  ).join('');
  return `<svg class="ed-hdr-svg" viewBox="0 0 100 ${VH}" preserveAspectRatio="xMinYMin meet">${text}</svg>`;
}

// ── hayEvento — dueño único del sustantivo que nombra un conjunto ───────────
// «actividad» es el PARAGUAS y un taller no es una obra (regla de vocabulario de
// Juan): el sustantivo se elige por el contenido, no por la pantalla. «obras» si
// TODAS son proyecciones; «actividades» si alguna no lo es.
//
// Vivía inline en el titular de Mi Plan y lo vigilaba T132b, pero las dos líneas
// de Planear —«N obras por planear» y «N obras · N días»— se habían quedado
// afuera: medido en FICDEH con «Los frutos que dan vida» (taller de 2 sesiones)
// más una película, decían «2 obras» sobre 1 película y 1 taller. El número
// estaba bien; el sustantivo no. Con tres copias del predicado, la próxima
// pantalla iba a quedarse afuera igual.
export function hayEvento(entradas, films){
  return (entradas||[]).some(e=>{
    const _t=typeof e==='string'?e:(e&&(e._title||e.title));
    return ((films||[]).find(f=>f.title===_t)||{}).type==='event';
  });
}

export function _posterThumb(f, cssClass, loading){
  const p = f ? getFilmPoster(f) : null;
  const _load = loading || 'lazy';

  if(!p){
    return `<div class="${cssClass}"></div>`;
  }

  const _pp=posterParts(f,{loading:_load});
  if(_pp.ed){
    // Marco editorial único (thumb = banda + img, sin label) vía posterParts.
    return `<div class="${cssClass} poster-ed" style="--ed-accent:${_pp.accent}">${_pp.inner}</div>`;
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
  if(_isEditorialPoster(f)) return {kind:'editorial', src, accent:_sectionColor(f.section||''), header:_seccionPartes(_secLabel(f.section||'')).rotulo, firma:(/\s\+\s/.test(f.title||'')?null:_seccionPartes(_secLabel(f.section||'')).firma), title:f.title||''};
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

export function editorialFrame({header, body, src, title, loading, accent, dato, firma}={}){
  // Forma B (§6.0) = forma A + UN campo 16:9 constante (8u×4,5u en y=3,5u). Sin
  // blur ni banda de color; la geometría vive en el CSS de .poster-ed, en %.
  const _l=loading||'lazy';
  const _dt=title?` data-title="${escXML(title)}"`:'';
  const _ttl=(body!=null && String(body).trim()) ? String(body) : '';
  const _dato=(dato!=null && String(dato).trim()) ? String(dato) : '';
  const img=src
    ? `<img class="ed-still" src="${src}"${_dt} loading="${_l}" onload="this.style.opacity='1'" onerror="_edPosterErr(this)" alt="">`
    : '';
  // MINIATURA = sin sección ni título (el corto dentro de un programa). Ahí el
  // campo se centra y el pie se llena con la propia obra desenfocada (Juan, 19
  // ago: «se ven muy vacías»). No es el blur que mató §6.0 —aquel iba DETRÁS del
  // still, a sangre, y ensuciaba el negro—: este está contenido bajo el campo y
  // se apaga con máscara antes del borde. En el póster grande no aplica: ahí el
  // vacío no existe, lo llenan el título y el dato.
  const _mini=!header&&!_ttl;
  // El halo llena el vacío TAMBIÉN en el póster grande (Juan, 24 ago 2026: «esa
  // línea negra debajo del still genera distancia y ruido»). Medido en la app:
  // el still termina en 66,67% y el título arranca en 86,4% — 23,6px de negro
  // muerto en una card de 120. La premisa que lo excluía («en el póster grande
  // el vacío no existe, lo llenan el título y el dato») era falsa en pantalla.
  // Mismo mecanismo que la miniatura —contenido, con máscara— pero anclado al
  // borde del campo grande (66,67%, clase ed-halo-full) para no dejar costura.
  const halo=(src)?`<div class="ed-halo${_mini?'':' ed-halo-full'}"><img src="${src}" loading="${_l}" aria-hidden="true" onerror="this.remove()" alt=""></div>`:'';
  return `<div class="ed-fil"></div>`
    + `<div class="ed-hdr">${header?_edHdrSVG(header, accent):''}</div>`
    + halo
    + `<div class="ed-img${_mini?' ed-img-mid':''}">${img}</div>`
    + `<div class="ed-foot">`
      + (_ttl?`<div class="ed-title">${escXML(_ttl)}</div>`:'')
      + ((firma&&_ttl)?`<div class="ed-firma">${escXML(firma)}</div>`:'')
      + (_dato?`<div class="ed-dato">${escXML(_dato)}</div>`:'')
    + `</div>`;
}

export function isNowShowing(f){
  // Festival aplazado: NADA está «AHORA» — el chip verde es una invitación a ir,
  // y un aplazado no invita. El reloj diría otra cosa (las fechas viejas siguen
  // en el dato, a propósito); el estado declarado gana.
  const _cfg=FESTIVAL_CONFIG[state.snapshot()._activeFestId];
  if(_cfg&&_cfg.status&&_cfg.status.kind==='postponed') return false;
  const dateStr=FESTIVAL_DATES[f.day];if(!dateStr) return false;
  const now=simNow();
  const start=_festDate(dateStr,f.time);
  // effectiveDuration (Q&A incluido) — mismo fin de función que el planificador.
  const end=new Date(start.getTime()+effectiveDuration(f)*60000);
  return now>=start&&now<=end;
}

// isQaOnlyNow — «la película ya terminó, queda el Q&A». Mismo encuadre que
// isNowShowing (aplazado, fecha del festival, reloj simulado) pero delegando el
// veredicto en el dominio: screeningQaOnly es el dueño único de la ventana.
export function isQaOnlyNow(f){
  if(!isNowShowing(f)) return false;
  return screeningQaOnly(f,_festNowMin());
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

// venueMatches — EL predicado del filtro de lugar (dueño único, 5 ago 2026).
// `sel` es 'all', un short de sede, o el centinela 'city:<Ciudad>' (filtro de
// ciudad entera — festivales multiciudad, FICDEH/Cinemancia). Antes cada
// superficie comparaba `vcfg(v).short===activeVenue` a mano en 8 sitios; el
// nivel de ciudad habría exigido tocarlos todos y en el tiempo habrían
// divergido. Consumido por programa.js (grid/lista/horario) y overlays.js.
// SEDE_SEP — separador del centinela 'sede:<ciudad><SEP><short>'. Se usa un
// carácter de control (U+001F, unit separator) y no un '|' o un '·' porque el
// delimitador NO puede aparecer nunca dentro de un nombre de ciudad o de sede.
// Se escribe como ESCAPE, nunca como carácter literal: un control invisible en el
// fuente se pierde en un copiar/pegar y no se ve al revisar un diff.
export const SEDE_SEP='\u001F';

// venueMatches — DUEÑO ÚNICO del predicado «esta función pasa el filtro de lugar».
// Tres formas de selección:
//   'all'                       → todo
//   'city:<Ciudad>'             → la ciudad entera
//   'sede:<Ciudad><SEP><short>' → una sede DE esa ciudad
//   '<short>'                   → legado: sede por nombre corto, sin ciudad
//
// Por qué la sede lleva la ciudad adentro (9 ago 2026): el nombre corto NO es
// único cuando el festival recorre varias ciudades. En FICDEH hay dos «Cinema
// Local» (Bogotá y Cali) y dos «Alianza Francesa» (Barranquilla y Cartagena);
// filtrando solo por short, elegir la de Bogotá traía también las 4 funciones de
// Cali, el conteo de la ciudad no cuadraba (135 arriba, 139 adentro) y la sede
// DESAPARECÍA de la lista de la segunda ciudad, absorbida por la primera.
//
// Y por qué la clave es (ciudad, short) y no la sede completa: dentro de UNA
// ciudad, varias sedes comparten short a PROPÓSITO — son las salas de un mismo
// edificio (Cinemateca Sala 2/3/Capital → «Cinemateca de Bogotá»; las 5 de Plaza
// Bocagrande). Ahí agrupar es lo correcto: quien elige el edificio quiere todas
// sus salas. La ciudad separa; el short agrupa.
export function venueMatches(v, sel){
  if(sel==='all') return true;
  if(sel&&sel.startsWith('city:')) return (vcfg(v).city||'')===sel.slice(5);
  if(sel&&sel.startsWith('sede:')){
    const i=sel.indexOf(SEDE_SEP);
    if(i<0) return vcfg(v).short===sel.slice(5);
    const ciudad=sel.slice(5,i), short=sel.slice(i+1);
    const c=vcfg(v);
    return c.short===short && (c.city||'')===ciudad;
  }
  return vcfg(v).short===sel;
}

// venueSelLabel — cómo se MUESTRA la selección del filtro (pill de filtros
// activos): la ciudad sin el centinela, o el short tal cual.
export function venueSelLabel(sel){
  if(sel&&sel.startsWith('city:')) return sel.slice(5);
  if(sel&&sel.startsWith('sede:')){
    // La pill muestra el NOMBRE de la sede; la ciudad viaja en el centinela para
    // desambiguar, no para leerse (ya está dicha en el propio filtro de ciudad).
    const i=sel.indexOf(SEDE_SEP);
    return i<0?sel.slice(5):sel.slice(i+1);
  }
  return sel;
}

// isCitySel / keepCityOnly — la CIUDAD es contexto, la SEDE es un filtro momentáneo.
// Al cambiar de día o de sección se limpia la sede (el viernes esa sala quizá no
// proyecta) pero se CONSERVA la ciudad: seguís en la misma ciudad. Sin esto, en
// FICDEH elegir Bogotá y tocar otro día te devolvía las 11 ciudades.
export function isCitySel(sel){ return !!(sel&&sel.startsWith('city:')); }

// venueCity(v) — la ciudad de una sede, SOLO cuando aporta (dueño único).
// Devuelve '' si la sede no declara ciudad o si es la misma del festival: en un
// festival de una ciudad, repetirla en cada card sería ruido. En FICDEH (11
// ciudades, `city:'Colombia'` en config a propósito) ninguna coincide → todas la
// muestran. Mismo criterio que ya usaban las fichas para el badge
// `venue-municipio`; acá pasa a ser el dueño de esa decisión.
// festivalCities(films) — DUEÑO ÚNICO de "las ciudades de este festival".
// Devuelve [{name, count, days:[dayKeys...]}] ordenado por cantidad de funciones.
// Lo consumen el nivel de ciudades del filtro de Lugar y el sheet de bienvenida
// multiciudad: sin un dueño, dos listas de ciudades que pueden divergir.
//
// `days` sale de las FUNCIONES, no de la config: en un festival ITINERANTE
// (Tercer Tiempo: DeKalb → Bogotá → CDMX en fechas distintas) cada ciudad tiene
// su propia ventana, y derivarla del dato es lo que permite soportarlos sin
// campos nuevos en el JSON. En uno simultáneo (FICDEH) todas coinciden.
export function festivalCities(films){
  const map={};
  (films||[]).forEach(f=>{
    if(f.info||!f.venue||!f.day) return;
    const c=vcfg(f.venue).city;
    if(!c) return;
    (map[c] ||= {name:c,count:0,vivas:0,days:new Set()});
    map[c].count++;
    if(!f._cancelled) map[c].vivas++;
    map[c].days.add(f.day);
  });
  // `cancelled` sale de ACÁ y no de un predicado al lado (2 sep 2026): esta
  // función ya recorre todas las funciones y ya es el dueño único que comparten
  // la hoja de apertura («¿A cuál ciudad vas?») y el nivel de ciudades del filtro
  // de Lugar. Con dos derivaciones, una superficie podía decir CANCELADA y la
  // otra ofrecer la misma ciudad como si nada.
  // Medido en FICDEH tras el sismo: Pereira 0/29, Manizales 0/26, Cali 0/17 y
  // Quibdó 0/16 — cuatro de once, ofrecidas con la misma tipografía que las vivas.
  return Object.values(map)
    .map(c=>({...c, days:[...c.days].sort(), cancelled:c.vivas===0}))
    .sort((a,b)=>b.count-a.count);
}

export function venueCity(v){
  const festCity=(FESTIVAL_CONFIG[_activeFestId]||{}).city||'';
  const c=vcfg(v).city||'';
  return (c&&c!==festCity)?c:'';
}
export function keepCityOnly(sel){ return isCitySel(sel)?sel:'all'; }

// sala(v) — la sala dentro del edificio, DECLARADA o, en su defecto, deducida.
//
// El modelo de multisala es: cada sala es una SEDE con clave propia, mismo
// `short` (el edificio) y las mismas coordenadas. Eso ya hace lo importante —dos
// funciones simultáneas en salas distintas son funciones distintas y entran en
// conflicto, encadenarlas no cuesta viaje, y el filtro las agrupa por edificio—.
// Lo que faltaba era DECIRLE al asistente a qué sala entrar.
//
// Hasta ahora la sala se adivinaba con un regex sobre el nombre de la sede, y el
// regex solo entiende NÚMEROS: «Cinemateca Sala Capital» (Tercer Tiempo y
// FantasoFest, ambos publicados) se perdía — llegabas al edificio sin saber la
// sala. Por eso el dato pasa a poder DECLARARSE: `room` en la entrada de venues.
//
// El regex se conserva como respaldo, no por nostalgia: los festivales ya
// montados (FICCI 65 con 9 sedes-sala, Cinemancia, Tercer Tiempo) traen la sala
// dentro del nombre y seguirían funcionando sin re-onboardearlos.
export function sala(v){
  const _room=(vcfg(v)||{}).room;
  if(_room) return String(_room).trim();
  const s=String(v||'');
  const m=s.match(/Sala\s*(\d+)/)||s.match(/Sal[oó]n\s*(\d+)/i);
  return m?'Sala '+(m[1]||m[2]):'';
}

// venueLabel(v) — el nombre COMPLETO de dónde ocurre una función: edificio + sala.
// Dueño único de esa concatenación.
//
// Nació de una incoherencia real entre las dos vías de exportar al calendario: el
// ICS mandaba `LOCATION` con la clave cruda de la sede —que lleva la sala— y el
// puente nativo de iOS mandaba solo el `short` —que la pierde—. Mismo plan, mismo
// usuario, y a qué sala entrar dependía del teléfono. Ahora ambas piden acá.
// Frente a la clave cruda tiene además la ventaja de ser legible: «UNIBAC · Sala 1»
// en vez de «Salón 1 ‒ Miguel Sebastián Guerrero, unibac».
export function venueLabel(v){
  const nombre=(vcfg(v)||{}).short||String(v||'');
  const _sala=sala(v);
  return _sala?`${nombre} · ${_sala}`:nombre;
}

// planCityVenues — el SET de sedes que el plan puede usar, derivado del filtro
// de lugar activo reducido a ciudad. Dueño único (16 ago 2026): vivía en
// controller/calc.js y solo se publicaba al CALCULAR, así que quien armaba su
// plan a mano (addSuggestion, sin pasar por Planear) tenía screeningPlannable
// sin restricción de ciudad — lo destapó el test de mutación de T61. Vive en
// helpers porque lo consumen la vista (alternativas, sugerencias) y el
// controller (runCalc, squeeze), y controller→view ya es dirección permitida.
export function planCityVenues(){
  const _sel=keepCityOnly(typeof activeVenue!=='undefined'?activeVenue:'all');
  if(_sel==='all') return null;
  const _vs=(FESTIVAL_CONFIG[_activeFestId]||{}).venues||{};
  return new Set(Object.keys(_vs).filter(v=>venueMatches(v,_sel)));
}

// planInputSignature — DUEÑO ÚNICO de «con qué se calculó este Plan» (Juan, 18
// ago: el Plan que estás mirando nunca cambia solo). Cubre todo lo que consume el
// planificador; la ciudad va reducida con keepCityOnly — una sede concreta no
// restringe el plan y marcarla desactualizada sería una falsa alarma.
export function planInputSignature(){
  const _int=[...watchlist].filter(t=>!watched.has(t)).sort().join('|');
  const _pri=[...prioritized].sort().join('|');
  const _av=Object.keys(availability||{}).sort()
    .map(d=>`${d}:${(availability[d]&&availability[d].blocks||[]).map(b=>`${b.from}-${b.to}`).sort().join(',')}`)
    .filter(x=>!x.endsWith(':'))
    .join(';');
  const _ciudad=keepCityOnly(typeof activeVenue!=='undefined'?activeVenue:'all');
  // El interruptor de PRENSA es un insumo del plan (30 ago 2026). Faltaba, y por
  // eso apagarlo dejaba el Plan agendado en un pase de acreditados que la app
  // misma ya no listaba: la función desaparecía de FILMS y la entrada seguía en
  // savedAgenda, sin aviso. Con el interruptor dentro de la firma, el Plan queda
  // marcado como desactualizado y el usuario decide cuándo recalcular — que es la
  // regla de Juan del 18 ago: «el Plan en pantalla no se reemplaza solo».
  const _prensa=(typeof showPress!=='undefined'&&showPress)?'P':'-';
  return `${_int}#${_pri}#${_av}#${_ciudad}#${_prensa}`;
}

export function travelWarn(s1,s2){
  if(s1.day!==s2.day) return null;
  const travel=travelMins(s1.venue,s2.venue);
  if(travel===0) return null;
  // effectiveDuration (incluye Q&A +30) — MISMO fin de función que screensConflict.
  const gap=toMin(s2.time)-(toMin(s1.time)+effectiveDuration(s1));
  if(gap<travel+10){
    const _modo=FESTIVAL_TRANSPORT==='walking'?t('warn_a_pie'):FESTIVAL_TRANSPORT==='transit'?null:t('warn_en_carro');
    return`${ICONS.alert} ~${travel} min${_modo?' '+_modo:''} ${t('warn_entre_sedes')}`;
  }
  return null;
}


// conflictAccount(a,b,r) — LA CUENTA del veredicto, en un solo dueño.
// r = screensConflictReason(a,b). Solo arma frase para 'ajustado' y 'viaje':
// son los veredictos cuyo número era irreconstruible en pantalla (QA de ojos
// frescos, 15 ago 2026 — un agente descartó una función creyendo que la app
// se equivocaba: los datos visibles no se solapaban; el margen de sala sí).
// 'solape' es un dato visible y 'ciudad' tiene su propia frase (el sujeto es
// el PLAN, no la película).
// Doctrina (Juan, 15 ago): la cuenta se MUESTRA, el veredicto se SUGIERE.
// Los fines de película son dato (indicativo); llegada y margen son estimación
// (condicional: «llegarías», «no te daría el tiempo», «te quedarían N min»).
// Mismos números que la regla (blockDuration / Q&A solo con traslado / buffer):
// no recalcula la decisión, la explica.
export function conflictAccount(a,b,r){
  if(!r||(r.kind!=='viaje'&&r.kind!=='ajustado')) return '';
  // f1 = la que termina primero; f2 = aquella a la que el tiempo no daría.
  const [f1,f2]=r.bFirst?[b,a]:[a,b];
  const t1=parseProgramTitle(f1._title||f1.title||'').displayTitle;
  const t2=parseProgramTitle(f2._title||f2.title||'').displayTitle;
  // fin de película: dato… salvo cuando la duración no está publicada, y entonces
  // sale de rellenar el hueco con DEFAULT_DURATION_MIN. La doctrina de acá abajo
  // dice que la `~` marca lo estimado: si el fin lo es, se marca igual que el
  // viaje y el Q&A. Si no, la cuenta que descarta una obra se apoya en un número
  // inventado y lo presenta como hecho.
  const end=screeningBlockEndMin(f1);
  const _endEst=durEstimada(f1.duration);
  const _end=x=>(_endEst?'~':'')+minToStr(x);
  const start=toMin(f2.time);
  const _b=x=>`<b>${x}</b>`;
  if(r.kind==='ajustado'){
    // misma sede: el Q&A no compromete (doctrina 30 jul) — cuenta con el buffer
    return t('cuenta_salas',{t1:`<i>${t1}</i>`,end:_b(_end(end)),buffer:FESTIVAL_BUFFER,
      arr:_b(minToStr(end+FESTIVAL_BUFFER)),t2:`<i>${t2}</i>`,start:_b(minToStr(start))});
  }
  // viaje: con traslado el Q&A sí cuenta (durationForTravel) — se muestra aparte.
  // La cadena SUMA el margen en vez de enunciarlo aparte: así el total es
  // directamente comparable con la hora de inicio y la conclusión se lee sola
  // (21:15 contra 21:00), sin una frase de veredicto que pueda contradecir a la
  // decisión — que fue el bug original. Antes la cuenta omitía el margen que
  // screensConflict exige, y una función EXCLUIDA se explicaba con la rama de
  // «sí llegás»: 53 de los 275 choques de viaje de FICDEH (medido 17 ago).
  // La `~` marca lo ESTIMADO (Q&A, viaje); el margen va sin tilde porque es una
  // política nuestra, no una estimación.
  const qaEnd=end+(f1.has_qa?FESTIVAL_QA_MIN:0);
  const total=qaEnd+r.travel+FESTIVAL_BUFFER;
  const base=t(f1.has_qa?'cuenta_viaje_qa':'cuenta_viaje',
    {t1:`<i>${t1}</i>`,end:_b(_end(end)),qa:FESTIVAL_QA_MIN,
     // travel en minutos PELADOS: la cadena declara la unidad una sola vez, al
     // final («margen 15 min»). Con _minFmt salía «viaje ~10 min + margen 15 min».
     travel:r.travel,buffer:FESTIVAL_BUFFER,
     total:_b(minToStr(total)),start:_b(minToStr(start))});
  // Cuando el choque existe SOLO por el Q&A, la alternativa va en la MISMA
  // moneda: la hora a la que llegarías saliendo al final de la película. Un
  // número en vez de una recomendación — el usuario compara y decide.
  const _qa=r.qaOnly?t('cuenta_qa_opcional',{sinQa:_b(minToStr(end+r.travel+FESTIVAL_BUFFER))}):'';
  return `${base}${_qa}`;
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

export function mplanEndStr(t,d){return minToStr(toMin(t)+d);} // delega en la fuente única min→HH:MM

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

// ticketBadgeTarget() — QUÉ marca el badge de precio en este festival (dueño único).
//   'free' → badge GRATIS en las gratuitas · 'paid' → badge CON BOLETA en las de
//   pago · null → el festival no es 'mixed', no hay badge.
//
// REGLA (Juan, 6 ago 2026): **el badge marca siempre la MINORÍA.** Un badge que
// pinta la mayoría de las tarjetas no discrimina: informa cero y ensucia.
// Hasta FICDEH lo gratuito era la excepción en todos los festivales (0% en
// nueve, 6% en Tercer Tiempo) y marcar las gratis alcanzaba. FICDEH 2026
// invierte la premisa: 81% gratis (313 de 384) — el badge pintaba 313 tarjetas y
// escondía lo único accionable, las 71 que cuestan plata.
// EMPATE EXACTO → 'paid': con 50/50 ninguna es minoría, y desempata lo
// accionable (hay que sacar boleta) sobre lo que no exige nada.
// Umbral 50% y no uno más alto: es "la minoría" literal, se explica en una línea
// y no deja zona gris marcando mayorías.
//
// Memoizado por festival: la proporción se recorre UNA vez, no por card.
let _tbCache={id:null,val:null};
export function ticketBadgeTarget(){
  const id=_activeFestId;
  if(_tbCache.id===id) return _tbCache.val;
  const cfg=FESTIVAL_CONFIG[id]||{};
  let val=null;
  if(cfg.ticketing_model==='mixed'){
    const reales=(FILMS||[]).filter(f=>!f.info&&f.day&&f.time);
    // Sin funciones cargadas no hay mayoría que leer: se devuelve null SIN
    // memoizar, o una consulta anterior a la carga congelaría el festival
    // entero sin badges.
    if(!reales.length) return null;
    const libres=reales.filter(f=>f.is_free===true).length;
    val=(libres*2>=reales.length)?'paid':'free';
  }
  _tbCache={id,val};
  return val;
}

export function _metaBadges(f){
  // Una función CANCELADA no tiene Q&A, ni inscripción, ni boleta. Sin esto la
  // card de Quibdó decía «CANCELADA» y al lado «CON BOLETA» el día que FICDEH
  // abrió: le ofrecía comprar entrada a una función que el festival ya suspendió
  // por el sismo (visto en producción, 11 ago 2026). El badge de estado manda
  // sobre los de servicio: si no va a ocurrir, no hay nada que ofrecer.
  if(f&&f._cancelled) return '';
  let b='';
  // PRENSA — va PRIMERO, antes incluso que premium, porque no describe la
  // función sino QUIÉN puede entrar: es un pase de acreditados. Solo se ve
  // cuando el usuario activó el filtro de Prensa e Industria — apagado, la
  // función ni siquiera está en FILMS —, así que el badge es el recordatorio
  // de que esta fila no es para el público general.
  if(f.audience==='press') b+=`<span class="meta-badge">${t('press_badge')}</span>`;
  // PREMIUM — la función cuesta más que el resto. Va PRIMERO entre los de
  // servicio porque es lo único que cambia el precio: los demás dicen qué te dan,
  // éste dice cuánto te cuesta. En TIFF son 61 de 638 funciones (las galas del
  // Roy Thomson, el Princess of Wales, el Royal Alexandra y dos sedes más), y lo
  // crítico es que 55 obras tienen funciones premium y normales A LA VEZ: sin el
  // badge, alguien planea su día, va a comprar y se encuentra otro precio — y lo
  // habría llevado ahí la app. Palabra del propio festival, la misma que verá en
  // Ticketmaster; no se traduce (mismo criterio que Q&A).
  if(f.premium===true) b+=`<span class="meta-badge">${t('badge_premium')}</span>`;
  if(f.has_qa) b+=`<span class="meta-badge">Q&A</span>`;
  if(f.requires_registration) b+=`<span class="meta-badge">${t('badge_inscripcion')}</span>`;
  // Festival mixto: el badge marca la MINORÍA (ver ticketBadgeTarget).
  const _tb=ticketBadgeTarget();
  if(_tb==='free'&&f.is_free===true) b+=`<span class="meta-badge">${t('badge_gratis')}</span>`;
  else if(_tb==='paid'&&f.is_free!==true) b+=`<span class="meta-badge">${t('badge_con_boleta')}</span>`;
  return b;
}

// _programaStack — el chip de 56px de la LISTA para una función compuesta.
//
// Era el TERCER dibujante de «afiches apilados», junto a la Escalera del grid y
// el generativo: dos imágenes a 50/50, y con el gate puesto en `is_programa`.
// Ese gate lo dejaba fuera de casi todo: de los 215 compuestos del catálogo,
// 207 son `is_cortos` y solo 8 son `is_programa` — disparaba en el 3,7%. El
// grid ya había corregido exactamente esto (ver programParts, «antes se
// llamaba legacyProgramParts y solo miraba is_programa») y la lista se quedó
// atrás: la misma obra se veía apilada en grilla y generativa en lista.
//
// Ahora la lista PREGUNTA AL MISMO DUEÑO que el grid (programParts) y dibuja la
// misma Escalera. Un compuesto se ve igual en las dos vistas y quedan dos
// dibujantes en vez de tres. El stack de dos imágenes se conserva solo como
// respaldo para los que no califican (afiche incompleto, still, 9+ obras).
export function _programaStack(f){
  if(!f||!f.film_list||f.film_list.length<2) return null;
  const _pp=programParts(f);
  if(_pp&&_pp.svg) return`<div class="plist-poster">${_pp.svg}</div>`;
  if(!f.is_programa) return null;
  const p1=_getItemPoster(f.film_list[0]);
  const p2=_getItemPoster(f.film_list[1]);
  // Fallback unificado (como el stack del sheet): item sin póster → la MINI del
  // programa (mejora 1 — el stack vive en el chip de 56px de la lista), nunca
  // un hueco vacío ni el póster entero ilegible.
  const _gen=()=>getFilmPosterMini(f);
  const imgB=`<img class="ps-back" src="${p2||_gen()}" loading="lazy" onerror="this.remove()" alt="">`;
  const imgF=`<img class="ps-front" src="${p1||_gen()}" loading="lazy" onerror="this.remove()" alt="">`;
  return`<div class="plist-poster-stack">${imgB}${imgF}</div>`;
}

export function _plistPosterHtml(f, src){
  // Chip de 56px: el generativo entero era ruido ilegible que repetía la fila
  // (mejora 1) → la mini. Los pósters reales y la sorpresa pasan tal cual.
  if(src&&String(src).startsWith('data:image/svg')) src=getFilmPosterMini(f);
  const _pp=posterParts(f);
  if(_pp.ed){
    // Marco editorial único (lista = banda + img, sin label) vía posterParts.
    return '<div class="plist-poster poster-ed" style="--ed-accent:'+_pp.accent+'">'+_pp.inner+'</div>';
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
