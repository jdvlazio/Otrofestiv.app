// ── src/view/components.js — Fase 8 Step 6a (CABLEADO) ───────────────────────
//
// ESTADO: importado por src/main.js (Step 6a). Capa presentacional foundational
//   de Wave 6: posters, builders HTML puros, helpers de seccion/rating/festival.
//   Scope por analisis de dependencias completo: clausura cerrada, CERO lets
//   mutables. Builders que leen estado mutable (notices/chips/av-day) se DIFIEREN.
//
// DEPS: config(FESTIVAL_CONFIG,SECTION_COLORS), domain/time(toMin), i18n(t);
//   festival-state via STATE BRIDGE (FILMS,_activeFestId,_lang,availability,
//   savedAgenda,DAY_KEYS). DAY_ABBR/DAY_NUM: objetos mutados por loadFestival via
//   el binding importado (mutacion de objeto, OK en ESM).

import { FESTIVAL_CONFIG, SECTION_COLORS, SECTION_EN, ARCHETYPE_COLORS, SECTION_ARCHETYPES } from "../config.js";
import { toMin } from "../domain/time.js";
import { t } from "../i18n/i18n.js";
import { state } from "../state/state.js";

export function makeProgramPoster(state, title, duration, section, opts){
  const {FILMS, _lang} = state.snapshot();
  const filmSec=section||(FILMS.find(f=>f.title===title)?.section)||'';
  const sec=filmSec.toLowerCase();

  // ── Color de sección — MISMA fuente que el marco editorial ────────────────
  // El acento del generativo debe coincidir con _sectionColor() (lo que usa el
  // marco editorial); si no, un corto CON still (verde) y otro SIN still
  // (generativo) de la MISMA sección salían de dos colores distintos —el bug de
  // "Peephole ámbar entre verdes". Fallback a la paleta por hash solo cuando la
  // sección no tiene color propio definido (evita gris para secciones nuevas).
  // El fallback por hash vivía acá y curaba solo al generativo: ahora es del dueño.
  const accent=_sectionColor(filmSec);

  // Header: sección localizada vía _secLabel (lang-aware: EN→SECTION_EN,
  // ES→original sin emoji), uppercase. Así el poster editorial coincide con el
  // separador del grid en cada idioma — antes horneaba f.section crudo y se
  // quedaba en español aunque la UI estuviera en EN.
  // Rótulo = primera oración (regla de carga, 24 ago): el programa de cortos es
  // pila por naturaleza, así que la firma de curaduría CEDE — no se pasa. Sin
  // esto, los programas de secciones curadas seguían con el rótulo completo
  // muriendo en «…» mientras los films de al lado ya lo llevaban corto: dos
  // pósters de la MISMA sección con dos rótulos distintos.
  const cleanSection=_seccionPartes(_secLabel(filmSec)).rotulo.toUpperCase();
  const headerLabel=cleanSection||t('poster_programa');

  // Número — patrones: "Prog. 4", "Prog. 1 · 16mm", "Voces 2", número al final
  const numMatch=title.match(/(?:Prog\.\s*|Programa\s+)(\d+)|(?:—\s*|:\s*|Prog\.\s*)(\d+)\s*(?:·|$)|\s(\d+)\s*$/);
  const num=numMatch?(numMatch[1]||numMatch[2]||numMatch[3]):null;

  // Día — extrae nombre de día al final del título ("— Jueves" → "JUE")
  // Solo aplica cuando no hay número (los programas numerados ya tienen su diferenciador)
  // Día: input ES desde el título del festival → índice DOW → abreviatura lang-aware
  const _dayIdx={'lunes':1,'martes':2,'miércoles':3,'miercoles':3,
    'jueves':4,'viernes':5,'sábado':6,'sabado':6,'domingo':0};
  const _DOW_ABBR={es:['DOM','LUN','MAR','MIÉ','JUE','VIE','SÁB'],
    en:['SUN','MON','TUE','WED','THU','FRI','SAT']};
  const _dayMatch=!num&&title.match(/[—\-]\s*([a-záéíóúüñ]+)\s*$/i);
  const _di=_dayMatch?_dayIdx[_dayMatch[1].toLowerCase()]:undefined;
  const dayAbbr=_di!=null?(_DOW_ABBR[_lang]||_DOW_ABBR.es)[_di]:null;

  // Body: la parte distintiva del título. Antes se vaciaba cuando había número
  // —el número era protagonista de 32px—; con §6.0 bajó a dato al pie y esa regla
  // dejaba la tarjeta MUDA: sección y un «1» chiquito (vista previa CineAutopsia,
  // 19 ago). El número ya no vacía el cuerpo: viaja al pie como lo que es.
  let bodyTitle='';
  {
    // ── REGLA INAMOVIBLE: el body = identificador único del programa ──────
    // Para programas con código "PGM N" el código ES el identificador → body.
    // Se extrae del TÍTULO (no se matchea contra la sección): idioma-agnóstico
    // y sin string-matching frágil. El descriptor del festival que sigue al
    // código (ej. "Competitiva BR/INT", "Pequenos Olhares") desaparece del body.
    //   "PGM 01 Competitiva BR/INT" → "PGM 01"   "PGM 05 Mirada Paranaense" → "PGM 05"
    // Ver docs/PIPELINE.md (posters editoriales).
    const _code=title.match(/\bPGM\s*\d+/i);
    if(_code){
      bodyTitle=_code[0].replace(/\s+/g,' ').trim().toUpperCase();
    } else {
    const secBase=filmSec.replace(/\p{Emoji}/gu,'').replace(/[^\w\sáéíóúüñÁÉÍÓÚÜÑ¿!()·\-]/gu,'').trim();
    bodyTitle=title
      .replace(/—?\s*Prog\.\s*(?:de\s+)?Cortos\s*$/i,'')
      .replace(/—?\s*Prog\.\s*Cortometrajes\s*—?\s*/i,'')
      .replace(new RegExp('^'+secBase.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'\\s*—?\\s*','i'),'')
      .replace(/^Cortos:\s*/i,'')
      .replace(/^Programa\s+/i,'')
      .replace(/^Competencia\s+/i,'')
      .trim();
    // Programas con nombre propio (sin código): quitar el nombre de sección si
    // aparece literal (el body es el identificador, nunca el descriptor de
    // sección — ya está en el header).
    if(secBase){
      const _secRe=new RegExp('\\s*[—\\-:·]?\\s*'+secBase.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'\\s*','gi');
      const _stripped=bodyTitle.replace(_secRe,' ').replace(/\s+/g,' ').trim();
      if(_stripped.length>=3) bodyTitle=_stripped;
    }
    // Descartar el body solo si NO aporta diferenciación: vacío, subcadena del
    // header, o solo símbolos.
    if(!bodyTitle||headerLabel.includes(bodyTitle.toUpperCase())||/^[^a-zA-ZáéíóúüñÁÉÍÓÚÜÑ0-9]+$/.test(bodyTitle))
      bodyTitle='';
    }
  }

  // opts.untitled (regla anti-repetición del sheet): cuerpo vacío — el título ya
  // está en la cabecera del sheet. El num/día SE CONSERVA (identidad visual).
  // El número solo va al pie si el cuerpo NO lo dice ya: «Mediometrajes del Mundo
  // Entero 1» + «1 · 102 min» repetía el dato que el título acababa de dar.
  const _numRedundante=num&&new RegExp('\\b'+num+'\\s*$').test(bodyTitle||'');
  const _dato=[(num&&!_numRedundante)?`${num}`:null, String(duration||'').trim()||null]
    .filter(Boolean).join(' · ')||dayAbbr||null;
  return _buildPosterV16({accent, headerLabel, title:(opts&&opts.untitled)?'':bodyTitle, num:null, dato:_dato});
}

export function makeSorpresaPoster(){
  return _buildPosterV16({
    accent:'#F59E0B',
    headerLabel:t('poster_sorpresa'),
    title:'?',
    num:null
  });
}

// Sección → color por ARQUETIPO (paleta unificada, POSTERS.md). El arquetipo gana;
// fallback al mapa viejo, y a gris solo si no hay nada (lo caza el gate).
// El gris #2C2C2A murió como color de sección (Juan, 19 ago): una sección sin
// arquetipo caía a un gris apagado y, como el TEXTO se pinta con ese color,
// quedaba gris sobre gris. La cura existía pero solo en el generativo; el marco
// editorial usaba _sectionColor crudo. Ahora vive en el DUEÑO, para todos.
const ACCENT_PALETTE=['#F59E0B','#3AAA6E','#E5A020','#E05252','#378ADD','#3A8E8E'];
const _secHash=s=>[...String(s)].reduce((h,c)=>(Math.imul(31,h)+c.charCodeAt(0))|0,0);
export function _sectionColor(sec){
  if(!sec) return '#F59E0B';                       // sin sección: ámbar de marca
  const arch = SECTION_ARCHETYPES[sec];
  if(arch && ARCHETYPE_COLORS[arch]) return ARCHETYPE_COLORS[arch];
  return SECTION_COLORS[sec] || ACCENT_PALETTE[Math.abs(_secHash(sec))%ACCENT_PALETTE.length];
}
// Texto legible sobre un color: negro o blanco por MÁXIMO contraste real (WCAG),
// no por umbral. Garantiza banda legible sobre cualquier color de sección.
export function _contrastText(hex){
  const c = String(hex||'').replace('#','');
  if(c.length < 6) return '#0B0A08';
  const r=parseInt(c.slice(0,2),16)/255, g=parseInt(c.slice(2,4),16)/255, b=parseInt(c.slice(4,6),16)/255;
  const L = 0.2126*r + 0.7152*g + 0.0722*b;
  return ((L+0.05)/0.05) >= (1.05/(L+0.05)) ? '#0B0A08' : '#FFFFFF';
}

// ── REGLA INAMOVIBLE DE ARQUITECTURA ─────────────────────────────────────────
// Todo display de nombre de sección DEBE pasar por _secLabel() (o _secLabelFull()
// si se necesita preservar el emoji). NUNCA usar `f.section` directamente en
// templates o componentes visuales — quedaría en español aunque la UI esté en EN.
// `f.section` crudo es SOLO para lógica/clave: SECTION_ORDER_LIST.indexOf(),
// SECTION_COLORS[], data-s=, comparaciones de filtro. El check validate.py
// [section-display-raw] enforcea esta regla.
// ─────────────────────────────────────────────────────────────────────────────
// Etiqueta de sección SIN emoji, localizada. En EN devuelve SECTION_EN[sec] si
// existe (display-only; la clave de orden/color/filtro sigue siendo `sec`); si no,
// cae al string ES con el emoji líder removido. `_lang` vía STATE BRIDGE (como el
// resto de la capa view) → cero cambios en los call sites.
export function _secLabel(sec){
  if(!sec) return '';
  const {_lang} = state.snapshot();
  if(_lang==='en' && SECTION_EN[sec]) return SECTION_EN[sec];
  const first=sec.split(' ')[0];
  const isEmoji=/^\p{Emoji}/u.test(first)&&!/^[A-Za-z0-9.]/u.test(first);
  return isEmoji?sec.slice(first.length).trim():sec;
}

// Igual que _secLabel pero PRESERVANDO el emoji líder (para listas que hoy
// muestran `f.section` crudo, p.ej. plist-sec / dropdown de filtro). En ES
// reproduce el string original; en EN devuelve "<emoji> <label EN>".
export function _secLabelFull(sec){
  if(!sec) return '';
  const first=sec.split(' ')[0];
  const isEmoji=/^\p{Emoji}/u.test(first)&&!/^[A-Za-z0-9.]/u.test(first);
  const label=_secLabel(sec);
  return isEmoji?`${first} ${label}`:label;
}

// Escape XML único para todo texto que va dentro de un <text> de SVG data-URI
// (pósters generativos). Sin esto, un '&' (ej. "Apertura & Galas" / "Reunions &
// Retrospectives") o '<'/'>' rompe el XML y el SVG no decodifica (naturalWidth 0).
// Lo reusa _edHdrSVG (helpers.js). Cubierto por tests/unit/poster.test.js.
export function escXML(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}

// ── Banda de sección: FUENTE ÚNICA del texto (Fase B) ─────────────────────────
// Editorial (_edHdrSVG, vw=100) y generativo (_buildPosterV16, vw=120) comparten
// ESTE builder: wrap, auto-contraste, escape XML, peso y métricas viven acá una
// sola vez. Antes eran dos implementaciones casi-idénticas que divergían (padding
// 2 vs 8, wrap 14 vs 15, spacing 0.5 vs 0.7) — esa duplicación ERA la inconsistencia.
// Las métricas son ratio de `vw` calibrado para que a vw=120 dé EXACTO lo del
// generativo (FS 6.5, LH 9, padX 8, ls 0.7) → el generativo no cambia y el
// editorial adopta el mismo look. Devuelve {text,lines,lh,fs}: `text` = los <text>;
// el caller compone el <svg> (y, en generativo, el <rect> de banda).
//   mode 'center' → centrado vertical en una banda de alto `bandH` (generativo).
//   mode 'top'    → anclado arriba, para el <svg> propio del editorial.
// wrap a 15ch mantiene la línea más ancha ≤15; secciones que superan 2 líneas
// exigen `sectionShort` (gate [seccion-larga]).
// _BAND_FS/_LH/_PADX/_LS murieron con la banda-losa (§6.0): el tamaño ya no es
// un ratio fijo del ancho. _BAND_MAXCH sigue vivo como default de _bandWrap.
const _BAND_MAXCH=16;

// ── Regla de lecturabilidad del corte de línea (regla de Juan) ────────────────
// Cada línea debe tener sentido por sí sola y NINGUNA línea (salvo la última)
// termina en palabra débil: conjunción, preposición o artículo. Esas arrastran
// a la línea siguiente junto al sustantivo que introducen. Ej.:
//   "Competencia De Cortometrajes" → [Competencia / De Cortometrajes]  (no "…De /")
//   "Tributo Ben Rivers"           → [Tributo / Ben Rivers]            (nombre junto)
//   "¿Qué es la ficción?"          → [¿Qué es / la ficción?]          (no "…la /")
// Acentos normalizados (según→segun, qué→que) para el match; "que" NO es débil
// (interrogativo/relativo válido a fin de línea). Reemplaza el corte greedy que
// partía donde cayera. Elige el corte con menos líneas, sin débiles al final y
// más balanceado (búsqueda exhaustiva — las etiquetas tienen pocas palabras).
const _BAND_WEAK=new Set(['el','la','lo','los','las','un','una','unos','unas','y','e','o','u','ni',
  'de','del','al','a','ante','bajo','con','contra','desde','en','entre','hacia','hasta','para','por',
  'segun','sin','sobre','tras','the','an','of','and','or','nor','to','in','on','at','for','with','by','from','into','over','under']);
export function _bandWrap(s, maxCh=_BAND_MAXCH){
  const words=s.split(/\s+/), n=words.length;
  if(n<=1) return words;
  const norm=w=>w.toLowerCase().replace(/[^\p{L}]/gu,'').normalize('NFD').replace(/[̀-ͯ]/g,'');
  // débil = conjunción/preposición/artículo O un guión separador suelto (–—-):
  // ninguno puede colgar al final de línea; bindean hacia el sustantivo que sigue.
  const isWeak=w=>/^[·–—-]+$/.test(w)||_BAND_WEAK.has(norm(w));
  if(n>13){ // guard: partición exhaustiva sólo para etiquetas normales
    const L=[]; let cur=''; for(const w of words){ if(cur&&(cur+' '+w).length>maxCh){L.push(cur);cur=w;} else cur=cur?cur+' '+w:w; } if(cur)L.push(cur); return L;
  }
  let best=null;
  for(let mask=0; mask<(1<<(n-1)); mask++){
    const lines=[]; let cur=[words[0]];
    for(let i=1;i<n;i++){ if(mask&(1<<(i-1))){lines.push(cur);cur=[words[i]];} else cur.push(words[i]); }
    lines.push(cur);
    const lens=lines.map(l=>l.join(' ').length);
    let overflow=0, weak=0;
    for(const L of lens) if(L>maxCh) overflow+=L-maxCh;
    for(let i=0;i<lines.length-1;i++) if(isWeak(lines[i][lines[i].length-1])) weak++;
    const imbal=Math.max(...lens)-Math.min(...lens);
    // débil (regla dura) pesa más que una línea extra; overflow evita reventar el ancho.
    const score=lines.length*1000 + weak*1500 + overflow*400 + imbal;
    if(!best || score<best.score) best={score, texts:lines.map(l=>l.join(' '))};
  }
  return best.texts;
}

// ── Motor de ajuste tipográfico (POSTERS.md §6.0) ────────────────────────────
// La tipografía se ajusta AL ESPACIO, no a una constante: antes _BAND_FS daba
// 4,55px en la tarjeta real, igual para «FICCIÓN» que para un nombre de 43
// caracteres. Se calcula en el viewBox (determinista, sin tocar el DOM) con un
// estimador de ancho por carácter; como es aproximado, el test mide el tamaño
// REAL en la tarjeta de 84px — ahí se ve si el estimador miente.
const _CHW_UPPER={'I':.30,'J':.45,'L':.55,'M':.92,'W':.92,'1':.42,' ':.26,'·':.32,'-':.35,'–':.5,'.':.28,',':.28,':':.28,'&':.75,'Í':.30,'Ó':.7,'Á':.68,'É':.62,'Ú':.7,'Ñ':.72};
const _CHW_LOWER={'i':.28,'j':.28,'l':.28,'t':.35,'f':.34,'r':.4,'m':.86,'w':.72,' ':.26,'·':.32,'-':.35,'.':.26,',':.26,'I':.3,'M':.9,'W':.9};
function _emWidth(str, upper){
  // 0.66 medido con getBBox sobre el <text> YA RENDERIZADO (no con canvas: ahí
  // el bold sintetizado mide de menos y el primer intento subestimaba hasta un
  // 19% — «CHARLA» real da 0.739 em/char y se salía de la tarjeta).
  const T=upper?_CHW_UPPER:_CHW_LOWER, def=upper?.66:.55;
  let w=0;
  for(const ch of String(str)) w += T[ch] !== undefined ? T[ch] : (upper ? def : (ch===ch.toUpperCase()&&ch!==ch.toLowerCase() ? .68 : def));
  return w;
}
// Devuelve {lines, fs, lh} con el MAYOR tamaño que entra en la caja. El corte de
// línea lo sigue decidiendo _bandWrap (regla de Juan: ninguna línea, salvo la
// última, termina en palabra débil) — acá solo se le dice cuántos caracteres
// caben a ese tamaño, y después se verifica el ancho REAL de cada línea.
// _lineaSVG — una línea que NO puede cruzar la línea de margen. Cuando el corte
// no logra evitarlo —la regla de Juan prohíbe dejar «de» al final, así que «DE
// CORTOMETRAJES» viaja pegado— se fija el ancho con textLength y el navegador
// condensa unos puntos. Solo se activa ahí; el resto se dibuja sin tocar.
export function _lineaSVG(txt, {x, y, fs, ls, fill, boxW, upper}){
  const est=(_emWidth(txt,upper)*fs+txt.length*ls)*1.12;
  const tope=boxW*0.98;
  const ajuste=est>tope?` textLength="${(+tope).toFixed(2)}" lengthAdjust="spacingAndGlyphs"`:'';
  return `<text x="${+x.toFixed(2)}" y="${+y.toFixed(2)}" font-family="-apple-system,BlinkMacSystemFont,sans-serif" font-size="${+fs.toFixed(2)}" font-weight="800" letter-spacing="${+ls.toFixed(2)}" fill="${fill}"${ajuste}>${escXML(txt)}</text>`;
}

export function _fitLines(str, {boxW, boxH, maxLines, fsMax, fsMin, lhRatio=1.16, lsEm=0, upper=false}){
  const s=String(str||'').trim();
  if(!s) return {lines:[], fs:0, lh:0};
  for(let fs=fsMax; fs>=fsMin; fs-=0.25){
    const perChar=fs*lsEm;
    const maxCh=Math.max(4, Math.floor(boxW/(fs*(upper?.66:.55)+perChar)));
    const L=_bandWrap(s, maxCh);
    if(L.length>maxLines) continue;
    const lh=fs*lhRatio;
    if(L.length*lh>boxH) continue;
    // 8% de resguardo (Juan, 19 ago: «los textos llegan demasiado al borde»). El
    // estimador es aproximado y el margen de 0,75u es una regla de retícula, no
    // una sugerencia: el test mide el bbox REAL de cada línea y exige que ninguna
    // cruce la línea de margen. Pasarse se VE; quedarse corto, no.
    // El estimador es aproximado y su error NO es simétrico: quedarse corto se ve
    // (texto tocando el borde), sobrar no. Por eso se mide con un factor de
    // seguridad —el peor caso observado, «CHARLA», mide 1,12× el promedio— y la
    // caja se respeta al 98%. El test mide el bbox REAL contra la línea de margen.
    if(L.some(l=>(_emWidth(l,upper)*fs+l.length*perChar)*1.12>boxW*0.98)) continue;
    return {lines:L, fs:+fs.toFixed(2), lh:+lh.toFixed(2)};
  }
  // Suelo: no cabe ni al mínimo → se recorta a maxLines con elipsis. El ancho no
  // se re-verifica acá A PROPÓSITO: quien garantiza el margen es _lineaSVG (una
  // sola vez, para todas las líneas). Un segundo cinturón acá era redundante —
  // ninguna mutación podía matarlo, que es la señal de que no defendía nada.
  const lh=fsMin*lhRatio;
  const L=_bandWrap(s, Math.max(4, Math.floor(boxW/(fsMin*(upper?.66:.55)))));
  const K=L.slice(0,maxLines);
  if(L.length>maxLines) K[maxLines-1]=K[maxLines-1].replace(/[\s.,;:–—-]+$/,'')+'…';
  return {lines:K, fs:fsMin, lh:+lh.toFixed(2)};
}

// _datoCompuesto — el pie de un programa dice cuántas obras trae.
// Juan, 24 ago 2026: un compuesto de tres obras decía «99 min», el mismo pie que
// una obra sola. La Forma C ya lo resolvió («2 obras · 77 min»); esto se lo da a
// la Forma A. El conteo sale del « + » CON espacios — el separador que usan los
// títulos compuestos reales (Cinemancia: 14 de 32)— para no confundir un «+»
// interno de un nombre. «obras» va en crudo como en la Forma C (mismo dueño de
// vocabulario; si algún día se localiza, se localizan juntos).
export function _datoCompuesto(title, duration){
  const _partes=String(title||'').split(/\s\+\s/);
  if(_partes.length<2) return duration||'';
  return `${_partes.length} obras${duration?` · ${duration}`:''}`;
}

// _seccionPartes — separa el rótulo de la FIRMA en una sección curada.
// Cinemancia escribe la curaduría dentro del nombre de sección: «La primavera
// llega para los que esperan. El cine de José Luis Torres Leiva». En el póster,
// ese rótulo moría en 84px justo donde va el autor («…EL CINE DE JOSÉ…»).
//
// La firma se reconoce ESTRICTA, no por cualquier punto: solo si tras la primera
// oración viene «Curaduría…» / «El cine de…» (o su inglés) o un nombre propio
// corto (≤4 palabras, todas capitalizadas — «Sergio Navarro»). Sin eso, el punto
// es parte del nombre y NO se parte: «Programa 1. El espesor de las formas» es
// un solo rótulo, no un rótulo con firma — partirlo por el punto a secas habría
// convertido «El espesor de las formas» en curador.
export function _seccionPartes(label){
  const _l=String(label||'').trim();
  const _i=_l.indexOf('. ');
  if(_i<0) return {rotulo:_l, firma:null};
  const _rot=_l.slice(0,_i), _resto=_l.slice(_i+2).trim();
  const _esFirma=/^(curadur[ií]a|curated|el cine de|the cinema of|o cinema de)/i.test(_resto)
    || (_resto.split(/\s+/).length<=4 && _resto.split(/\s+/).every(w=>/^[A-ZÁÉÍÓÚÑÜ]/.test(w)));
  return _esFirma ? {rotulo:_rot, firma:_resto} : {rotulo:_l, firma:null};
}

export function _buildPosterV16({accent, headerLabel, title, num, dato, firma}){
  // ── Póster nuestro — anatomía aprobada (POSTERS.md §6.0, Juan 18 ago 2026) ──
  // Retícula: u = ancho/8 → 8u × 12u. Margen 0,75u. Filete de sección de 0,25u a
  // sangre. Sección arriba, título anclado abajo, dato al pie, luz abajo a la
  // derecha. La tipografía se ajusta al espacio (_fitLines), no a una constante.
  //
  // Lo que murió acá: la banda de color como losa (el color de sección pasó al
  // filete y a la propia tipografía), el chevron (a 84px era suciedad) y el
  // número gigante — que era un DATO y ahora vive como tal, en el pie.
  //
  // La LUZ hereda el acento de sección (Juan, 24 ago 2026 — auditoría con
  // Cinemancia): era ámbar fija en los 32 generativos del festival y una pared
  // de Forma A se veía monótona. Con la luz en el color de sección, Competencia
  // se distingue de Iluminaciones de un golpe de vista, sin tocar la retícula.
  // Es la doctrina de color ambiental, aplicada al generativo.
  const VW=120, VH=180, U=VW/8;              // 15
  const M=0.75*U, CW=VW-2*M;                 // margen 11.25 · caja de contenido 97.5
  const esc=escXML;
  const round=n=>+n.toFixed(2);
  const FONT='-apple-system,BlinkMacSystemFont,sans-serif';

  // Sección — la mayor que quepa en 6,5u × 3,4u, máx 3 líneas
  // Tope de 15px en la tarjeta de 84 (decisión de Juan, 18 ago) = 21,43 en el
  // viewBox: «la mayor que quepa» sin techo llevaba «CHARLA» a 17,9px, más grande
  // que el título de la obra. El techo mantiene la jerarquía: la sección orienta,
  // el título es el protagonista.
  // EL TÍTULO NO REPITE LA SECCIÓN (Juan: «una regla que he repetido mil veces
  // y nunca la aplican» — 24 ago 2026). Si el título arranca con el nombre del
  // rótulo («Competencia de cortometrajes Programa 1» bajo COMPETENCIA DE
  // CORTOMETRAJES), el prefijo se recorta y queda «Programa 1», grande y limpio:
  // la sección ya lo dijo arriba. Comparación sin acentos/case; solo prefijo
  // EXACTO — nada de adivinar coincidencias parciales. Si el recorte deja vacío,
  // se conserva el título original.
  const _norm=x=>String(x||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().trim();
  {
    const _nt=_norm(title), _nh=_norm(headerLabel);
    if(_nh&&_nt.startsWith(_nh)){
      const _resto=String(title).trim().slice(String(headerLabel).trim().length).replace(/^[\s·:—-]+/,'');
      if(_resto) title=_resto;
    }
  }
  const SEC_FS_MAX=15*VW/84;
  // REGLA DE CARGA (Juan, 24 ago 2026): el póster habla con TRES voces —
  // sección ≤2 líneas, cuerpo, pie de UNA línea. La sección bajó de 4 líneas a
  // 2: con 4, los rótulos curados se comían medio póster y aun así morían en
  // «…»; la primera oración (via _seccionPartes, en los llamadores) cabe en 2.
  const sec=_fitLines(String(headerLabel||'').toUpperCase(),
    {boxW:CW, boxH:3.4*U, maxLines:2, fsMax:Math.min(SEC_FS_MAX, 3.4*U/1.16), fsMin:7, lhRatio:1.16, lsEm:0.02, upper:true});
  // fsMin bajó de 9 a 7 CON el techo de 2 líneas (24 ago): a fsMin 9, «LA
  // PRIMAVERA LLEGA PARA LOS QUE ESPERAN» necesitaba 3 líneas y el motor
  // recortaba con «…» — y recortar una sección está prohibido (§6.0). A 7
  // (≈4,9px en la card de 84) el rótulo entero cabe en dos líneas. Preferimos
  // pequeño y completo a grande y mutilado.
  const secY=1*U+sec.fs;                     // primera línea base a 1u
  const secText=sec.lines.map((l,i)=>_lineaSVG(l,
    {x:M, y:secY+i*sec.lh, fs:sec.fs, ls:sec.fs*0.02, fill:accent, boxW:CW, upper:true})).join('');

  // Dato al pie (5% del ancho, gris). El `num` de los programas —«PGM 05», «MAR
  // 18»— ES un dato: deja de ser un número de 32px en el centro.
  //
  // Y si no hay título, el dato PASA AL LUGAR DEL TÍTULO: sin eso, los programas
  // con `untitled` quedaban con la sección y nada más.
  const _tituloVacio=!String(title||'').trim();
  const _datoCrudo=String(dato||num||'').trim();
  const datoStr=_tituloVacio?'':_datoCrudo;
  const datoFS=VW*0.05;
  // La línea base va ARRIBA del margen por el descendente (~0,22em): apoyarla
  // justo en 11,25u metía las colas de la «g» y la «p» fuera de la retícula.
  const datoY=VH-M-datoFS*0.30;
  const datoText=datoStr
    ? _lineaSVG(datoStr, {x:M, y:datoY, fs:datoFS, ls:datoFS*0.02, fill:'#888', boxW:CW, upper:false})
    : '';
  // FIRMA de curaduría — línea propia en itálica sobre el dato, a 1,5·fs. Solo
  // llega cuando el llamador la permite (título simple: la regla de carga manda
  // que con pila de obras la firma CEDE y vive en la ficha, no en el póster).
  const _firmaStr=String(firma||'').trim();
  const firmaY=_firmaStr?(datoStr?datoY-datoFS*1.5:datoY):null;
  const firmaText=_firmaStr
    ? `<text x="${M}" y="${round(firmaY)}" font-family="${FONT}" font-size="${datoFS}" font-style="italic" font-weight="600" fill="#888">${escXML(_firmaStr)}</text>`
    : '';

  // Título — anclado abajo, sobre el dato (y sobre la firma si la hay)
  const tTop=_firmaStr?firmaY-datoFS*1.6:(datoStr?datoY-datoFS*1.6:datoY);
  const _titulo=_tituloVacio?_datoCrudo:String(title||'').trim();
  const _obras=_titulo.split(/\s\+\s/).map(x=>x.trim()).filter(Boolean);

  // ── LA PILA (Juan, 24 ago 2026) ───────────────────────────────────────────
  // «El + no es un título: es una pila de obras». Un compuesto llegaba como una
  // frase y el motor lo partía donde caía: «La tempestá + No contéis con los
  // dedos + Vampir Cuadecuc» rompía a mitad de un nombre y moría en elipsis.
  // El cartel de un programa doble nunca tipografía así: apila las obras.
  //
  // Retícula (medida con Juan sobre grid y rulers, no a ojo):
  //  · todas las obras al MISMO cuerpo — hermanas iguales: el menor de los
  //    ajustes individuales. Una obra corta no puede gritar más que su vecina.
  //  · 1u exacto entre bloques; el «+» vive EN ese gap, a 0,5u, al margen
  //    izquierdo como todo el sistema, en el color de la sección.
  //  · la pila crece hacia arriba desde la misma base que el título de §6.0 —
  //    no inventa anclas nuevas.
  //  · FRONTERA 2–3 obras, la misma de la forma C. Con 4+ el cuerpo caería a un
  //    tamaño ilegible: se conserva la forma de siempre y el pie ya dice
  //    «4 obras» (_datoCompuesto), que es la información que salva el caso.
  const _esPila=_obras.length>=2&&_obras.length<=3;
  let ttlText, ttl;
  if(_esPila){
    const GAP=U;
    const PILA_FS_MAX=16;                    // tope de cuerpo de la pila (Juan)
    // TECHO REAL, MEDIDO: la pila no vive en la caja de 2,4u del título — crece
    // hacia arriba por aire vacío (la Forma A no tiene campo de imagen). Su
    // único límite por arriba es el bloque de sección YA AJUSTADO, no una
    // constante inventada: fondo de la sección + 0,5u de aire para descendentes.
    const _techo=secY+(sec.lines.length-1)*sec.lh+0.5*U;
    const _presupuesto=tTop-_techo;
    // El techo NO se vigila con un lazo que encoge después: se le entrega al
    // motor como la caja de cada obra. Cada una recibe su parte del presupuesto
    // (descontados los gaps) y _fitLines ya no puede devolver algo que no quepa.
    // Un lazo correctivo aparte era código muerto — _fitLines lo adelantaba
    // siempre — y un guardián que nunca dispara no es de fiar.
    const _boxCada=(_presupuesto-GAP*(_obras.length-1))/_obras.length;
    const _ajusta=(fsMax)=>_obras.map(o=>_fitLines(o,
      {boxW:CW, boxH:_boxCada, maxLines:2, fsMax, fsMin:9, lhRatio:1.2, lsEm:-0.02, upper:false}));
    // Cuerpo común = el MENOR de los ajustes individuales: mandan las anchas.
    // Con el menor, el re-ajuste de cada obra devuelve exactamente ese cuerpo —
    // por eso ninguna línea necesita condensarse (textLength) al dibujarse.
    const _fs=Math.min(PILA_FS_MAX, ...(_ajusta(PILA_FS_MAX).map(f=>f.fs)));
    const _re=_ajusta(_fs), _lh=_fs*1.2;
    const _alto=_re.reduce((a,f)=>a+f.lines.length*_lh,0)+GAP*(_obras.length-1);
    let _y=tTop-_alto;                                     // crece hacia arriba
    const _partes=[];
    _re.forEach((f,i)=>{
      f.lines.forEach(l=>{ _y+=_lh;
        _partes.push(_lineaSVG(l,{x:M, y:_y, fs:_fs, ls:_fs*-0.02, fill:'#F0EDE8', boxW:CW, upper:false})); });
      if(i<_re.length-1){
        // el «+» centrado en el gap: 0,5u, apoyado en su tercio para ópticamente
        // caer en el medio del aire, no en su borde superior.
        const _fsMas=0.5*U;
        _partes.push(`<text x="${round(M)}" y="${round(_y+GAP*0.5+_fsMas*0.35)}" font-family="${FONT}" font-size="${round(_fsMas)}" font-weight="800" fill="${accent}">+</text>`);
        _y+=GAP;
      }
    });
    ttlText=_partes.join('');
    ttl={fs:_fs, lines:_re.flatMap(f=>f.lines)};
  } else {
    ttl=_fitLines(_titulo,
      {boxW:CW, boxH:2.4*U, maxLines:4, fsMax:2.4*U/1.2, fsMin:12, lhRatio:1.2, lsEm:-0.02, upper:false});
    // fsMin=12 (≈8,4px en tarjeta) es SUELO DE LEGIBILIDAD: por debajo se recorta
    // con elipsis en vez de encoger hasta lo ilegible. La sección usa un suelo más
    // bajo a propósito — recortar el nombre del festival está prohibido.
    const tStartY=tTop-(ttl.lines.length-1)*ttl.lh;
    ttlText=ttl.lines.map((l,i)=>_lineaSVG(l,
      {x:M, y:tStartY+i*ttl.lh, fs:ttl.fs, ls:ttl.fs*-0.02, fill:'#F0EDE8', boxW:CW, upper:false})).join('');
  }

  const svg=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${VW} ${VH}">
    <defs><radialGradient id="lz" cx="1" cy="1" r="1">
      <stop offset="0" stop-color="${accent}" stop-opacity=".28"/>
      <stop offset="1" stop-color="${accent}" stop-opacity="0"/>
    </radialGradient></defs>
    <rect width="${VW}" height="${VH}" fill="#0B0A08"/>
    <rect x="${round(VW*0.45)}" y="${round(VH*0.55)}" width="${round(VW*0.55)}" height="${round(VH*0.45)}" fill="url(#lz)"/>
    <rect width="${VW}" height="${round(0.25*U)}" fill="${accent}"/>
    ${secText}
    ${ttlText}
    ${firmaText}${datoText}
  </svg>`;
  return `data:image/svg+xml,${encodeURIComponent(svg)}`;
}

// ── Póster de FUNCIÓN COMPARTIDA (Tipo 2) — «Escalera mayor», §6.0 ──────────
// Aprobado por Juan (21 ago 2026) tras revisión exhaustiva. Reglas de frontera:
// SOLO funciones compartidas (anclaje) de 2-3 obras con ≥1 afiche real; los
// PROGRAMAS (Tipo 3) jamás usan esta forma — sus obras suelen tener stills, y un
// still se dibuja dentro del marco editorial, que ya es un póster propio: sería
// un póster propio dentro de otro. SIN TÍTULO interno («en una película con
// póster nunca vemos títulos»): la identidad nominal vive en lista/ficha/plan,
// y en las superficies mudas queda a un tap, igual que cualquier obra.
// Este builder SOLO dibuja: la decisión de qué es módulo real y qué es mudo la
// toma helpers (slotPosterParts), dueño del modelo de póster.
// Devuelve MARKUP SVG INLINE, no data-uri: contiene <image> y un SVG dentro de
// <img> tiene prohibido cargar recursos — los afiches saldrían rotos.
export function makeSharedSlotSVG({modules, secLabel, accent, dato}){
  const U=15, VW=120, VH=180, M=11.25, CW=VW-2*M, NEGRO='#0B0A08', HAIR='#26231F';
  const r=n=>+n.toFixed(2);
  const mod=(ux,uy,uw,src,i)=>{
    const x=ux*U,y=uy*U,w=uw*U,h=uw*1.5*U,rx=w*0.13;
    const id=`ssp${i}`;
    return `<clipPath id="${id}"><rect x="${r(x)}" y="${r(y)}" width="${r(w)}" height="${r(h)}" rx="${r(rx)}"/></clipPath>`
      +`<rect x="${r(x)}" y="${r(y)}" width="${r(w)}" height="${r(h)}" rx="${r(rx)}" fill="${NEGRO}" stroke="${HAIR}" stroke-width="0.5"/>`
      +`<image href="${escXML(src)}" x="${r(x)}" y="${r(y)}" width="${r(w)}" height="${r(h)}" preserveAspectRatio="xMidYMid meet" clip-path="url(#${id})"/>`;
  };
  const sombra=(ux,uy,uw)=>`<rect x="${r(ux*U+2.85)}" y="${r(uy*U-2.85)}" width="${r(uw*U)}" height="${r(uw*1.5*U)}" rx="${r(uw*U*0.13)}" fill="#000" opacity=".5"/>`;
  // Geometrías aprobadas (en u, pasos de 0,25u). modules viene atrás→delante,
  // con los mudos SIEMPRE atrás. El delantero es la primera obra con afiche.
  // El «módulo mudo» murió (Juan, 21 ago): la Escalera existe solo completa,
  // así que acá solo llegan afiches reales.
  const n=modules.length;
  let comp='';
  if(n===2){
    const [atras,frente]=modules;
    comp = mod(0.75,3,4.5,atras,0) + sombra(2.75,3.75,4.5) + mod(2.75,3.75,4.5,frente,1);
  } else {
    const pos=[[0.75,3],[2,3.75],[3.25,4.5]]; // atrás→delante, módulos 4u
    comp = modules.map((src,i)=>
      (i===n-1?sombra(pos[i][0],pos[i][1],4):'')+mod(pos[i][0],pos[i][1],4,src,i)).join('');
  }
  const SEC_FS_MAX=15*VW/84;
  const sec=_fitLines(String(secLabel||'').toUpperCase(),
    {boxW:CW, boxH:1.9*U, maxLines:2, fsMax:Math.min(SEC_FS_MAX, 1.9*U/1.16), fsMin:9, lhRatio:1.16, lsEm:0.02, upper:true});
  const secTxt=sec.lines.map((l,i)=>_lineaSVG(l,{x:M,y:1*U+sec.fs+i*sec.lh,fs:sec.fs,ls:sec.fs*0.02,fill:accent,boxW:CW,upper:true})).join('');
  const datoFS=VW*0.05, datoY=VH-M-datoFS*0.30;
  const datoTxt=dato?_lineaSVG(dato,{x:M,y:datoY,fs:datoFS,ls:datoFS*0.02,fill:'#888',boxW:CW,upper:false}):'';
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${VW} ${VH}">`
    +`<defs><radialGradient id="ssp-luz" cx="1" cy="1" r="1"><stop offset="0" stop-color="#F59E0B" stop-opacity=".28"/><stop offset="1" stop-color="#F59E0B" stop-opacity="0"/></radialGradient>`
    +`</defs>`
    +`<rect width="${VW}" height="${VH}" fill="${NEGRO}"/>`
    +`<rect x="54" y="99" width="66" height="81" fill="url(#ssp-luz)"/>`
    +comp
    +`<rect width="${VW}" height="3.75" fill="${accent}"/>`
    +secTxt+datoTxt+`</svg>`;
}

export function makeEventPoster(state,title,duration,eventKind,section,opts){
  const {_activeFestId, _lang} = state.snapshot();
  const festCfg=(FESTIVAL_CONFIG&&FESTIVAL_CONFIG[_activeFestId])||Object.values(FESTIVAL_CONFIG||{})[0]||{};
  // 'charla' — la palabra que usan los festivales. FICDEH («💬 Charlas que Unen»,
  // 18 actividades) y FICMA («💬 Charlas», 6) mostraban PONENCIA, que no aparece en
  // ninguna de sus fuentes: la Franja Académica de FICMA dice TALLERES y CHARLAS.
  // «Ponencia» la pusimos nosotros (Juan, 10 ago 2026 — con FICMA ya en curso).
  // 'ponencia' SE QUEDA: es vocabulario válido para un festival que sí la use, y
  // sacarla rompería el dato actual mientras se migra. Primero el mapa, después el
  // dato: event_kind solo alimenta makeEventPoster, y agenda.js (×2) y programa.js
  // lo llaman SIN sección, así que un 'charla' sin entrada caería al genérico
  // EVENTO en Mi Plan y en la agenda — peor que el PONENCIA de hoy.
  const _kindMapES={
    'ponencia':     {accent:'#F59E0B', headerLabel:'PONENCIA'},
    'charla':       {accent:'#F59E0B', headerLabel:'CHARLA'},
    // 'taller' ya estaba EN EL DATO (FICMA, 8 actividades) sin entrada en el mapa:
    // esas cards mostraban el genérico EVENTO. Es la otra mitad del vocabulario de
    // la Franja Académica —«TALLERES y CHARLAS»— y no necesita migración.
    // Accent ámbar como charla/ponencia: las tres son la franja académica. Si Juan
    // prefiere distinguirlas, es cambiar este color y nada más.
    'taller':       {accent:'#F59E0B', headerLabel:'TALLER'},
    // «seminario» llegó con VARTEX 14: es la misma franja académica que taller
    // y charla, y sin entrada aquí su card mostraba el genérico EVENTO.
    'seminario':    {accent:'#F59E0B', headerLabel:'SEMINARIO'},
    // «foro» y «debate» llegaron con Cinemancia 2026: su Foro de la Crítica son
    // cuatro sesiones y el debate «Todos los planos del mundo» una. Mismo ámbar
    // de la franja académica; sin entrada aquí su card mostraba EVENTO genérico.
    'foro':         {accent:'#F59E0B', headerLabel:'FORO'},
    'debate':       {accent:'#F59E0B', headerLabel:'DEBATE'},
    'masterclass':  {accent:'#7F77DD', headerLabel:'MASTERCLASS'},
    'encuentro':    {accent:'#378ADD', headerLabel:'ENCUENTRO'},
    'cineconcierto':{accent:'#D85A30', headerLabel:'CINECONCIERTO'},
    // «live cinema» llegó con VARTEX 14: actuación audiovisual en vivo, prima
    // del cineconcierto. Se conserva la palabra del festival, no se traduce a
    // «cineconcierto», que es de otros festivales.
    'live cinema':  {accent:'#D85A30', headerLabel:'LIVE CINEMA'},
    'awards':       {accent:'#BA7517', headerLabel:'AWARDS SCREENINGS'},
  };
  const _kindMapEN={
    'ponencia':     {accent:'#F59E0B', headerLabel:'TALK'},
    'charla':       {accent:'#F59E0B', headerLabel:'TALK'},
    'taller':       {accent:'#F59E0B', headerLabel:'WORKSHOP'},
    'seminario':    {accent:'#F59E0B', headerLabel:'SEMINAR'},
    'foro':         {accent:'#F59E0B', headerLabel:'FORUM'},
    'debate':       {accent:'#F59E0B', headerLabel:'DEBATE'},
    'masterclass':  {accent:'#7F77DD', headerLabel:'MASTERCLASS'},
    'encuentro':    {accent:'#378ADD', headerLabel:'MEETING'},
    'cineconcierto':{accent:'#D85A30', headerLabel:'FILM CONCERT'},
    'live cinema':  {accent:'#D85A30', headerLabel:'LIVE CINEMA'},
    'awards':       {accent:'#BA7517', headerLabel:'AWARDS SCREENINGS'},
  };
  const _kindMap=_lang==='es'?_kindMapES:_kindMapEN; // PT reutiliza EN (términos internacionales)
  // opts.untitled (regla anti-repetición del sheet): cuerpo vacío — el título ya
  // está en la cabecera del sheet. La banda de kind/sección se conserva.
  const _bodyTitle=(opts&&opts.untitled)?'':title;
  const kind=_kindMap[eventKind];
  if(kind) return _buildPosterV16({...kind, title:_bodyTitle, num:null});
  // Fallback — usa la sección del film si existe, sino eventPosterLabel del config
  const _secFallback=section?_secLabel(section):'';
  const lbl=_secFallback?[_secFallback]:((festCfg.eventPosterLabel)||[t('poster_evento'),'']);
  const headerLabel=lbl.filter(Boolean).join(' ');
  const _sectionAccent=section?_sectionColor(section):'#6B9BD1';
  return _buildPosterV16({accent:_sectionAccent||'#6B9BD1', headerLabel, title:_bodyTitle, num:null});
}

export const ICONS={
  ticket:   `<svg aria-hidden="true" focusable="false" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M2 9a3 3 0 0 1 0 6v2a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-2a3 3 0 0 1 0-6V7a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2Z"/><path d="M13 5v14"/></svg>`,
  // clipboard-list — el enlace de inscripción. Icono PROPIO y no uno prestado:
  // los candidatos obvios ya significan otra cosa en la app (bookmark=Priorizar,
  // calendar=Mi Plan, plus=«+ Agregar», check=visto) y reusarlos diría dos cosas
  // con el mismo símbolo. Es literalmente a dónde lleva: un formulario.
  clipboardList: `<svg aria-hidden="true" focusable="false" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><rect width="8" height="4" x="8" y="2" rx="1" ry="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><path d="M12 11h4"/><path d="M12 16h4"/><path d="M8 11h.01"/><path d="M8 16h.01"/></svg>`,
  // link — Lucide «link-2»: dos eslabones unidos por una barra RECTA. Marca el
  // corchete del taller multi-día («estas sesiones son una sola cosa»). Se eligió
  // link-2 sobre link porque su barra horizontal continúa la línea del corchete;
  // el link clásico es diagonal y pelea con la geometría. 12px: es una marca
  // sobre una línea de 1.5px, no un icono de acción.
  link: `<svg aria-hidden="true" focusable="false" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 17H7A5 5 0 0 1 7 7h2"/><path d="M15 7h2a5 5 0 1 1 0 10h-2"/><line x1="8" y1="12" x2="16" y2="12"/></svg>`,
  // Lucide `award` — la medalla. La app solo tenía star/starFill, y la estrella
  // YA significa calificación: usarla para «premio» hacía decir dos cosas con el
  // mismo signo. Es el único icono nuevo que pide el palmarés.
  award: `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="6"/><path d="M15.477 12.89 17 22l-5-3-5 3 1.523-9.11"/></svg>`,
  star:     `<svg aria-hidden="true" focusable="false" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>`,
  starFill: `<svg aria-hidden="true" focusable="false" width="13" height="13" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>`,
  heart:    `<svg aria-hidden="true" focusable="false" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path stroke-linecap="round" stroke-linejoin="round" d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z"/></svg>`,
  heartFill:`<svg aria-hidden="true" focusable="false" width="14" height="14" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path stroke-linecap="round" stroke-linejoin="round" d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z"/></svg>`,
  x:        `<svg aria-hidden="true" focusable="false" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>`,
  check:    `<svg aria-hidden="true" focusable="false" class="block-shrink" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5"/></svg>`,
  undo:     `<svg aria-hidden="true" focusable="false" class="block-shrink" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path stroke-linecap="round" stroke-linejoin="round" d="M9 15L3 9m0 0l6-6M3 9h12a6 6 0 010 12h-3"/></svg>`,
  switch:   `<svg aria-hidden="true" focusable="false" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path stroke-linecap="round" stroke-linejoin="round" d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5"/></svg>`,
  plus:     `<svg aria-hidden="true" focusable="false" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15"/></svg>`,
  text:     `<svg aria-hidden="true" focusable="false" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M15 12H3"/><path d="M17 18H3"/><path d="M21 6H3"/></svg>`,
  // book-open (Lucide) — el DIARIO. `history` (reloj con flecha de rebobinar) es
  // el símbolo de restaurar/deshacer, no el de un cuaderno: se leía como una
  // acción sobre el pasado, no como un lugar donde queda escrito lo que viste.
  bookOpen: `<svg aria-hidden="true" focusable="false" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M12 7v14"/><path d="M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z"/></svg>`,
  eye: `<svg aria-hidden="true" focusable="false" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0"/><circle cx="12" cy="12" r="3"/></svg>`,
  eyeOff: `<svg aria-hidden="true" focusable="false" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M10.733 5.076a10.744 10.744 0 0 1 11.205 6.575 1 1 0 0 1 0 .696 10.747 10.747 0 0 1-1.444 2.49"/><path d="M14.084 14.158a3 3 0 0 1-4.242-4.242"/><path d="M17.479 17.499a10.75 10.75 0 0 1-15.417-5.151 1 1 0 0 1 0-.696 10.75 10.75 0 0 1 4.446-5.143"/><path d="m2 2 20 20"/></svg>`,
  history:  `<svg aria-hidden="true" focusable="false" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l4 2"/></svg>`,
  film:     `<svg aria-hidden="true" focusable="false" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M7 3v18"/><path d="M17 3v18"/><path d="M3 7.5h4"/><path d="M3 12h18"/><path d="M3 16.5h4"/><path d="M17 7.5h4"/><path d="M17 16.5h4"/></svg>`,
  clock:    `<svg aria-hidden="true" focusable="false" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`,
  // route (Lucide) — convención del conflicto por DESPLAZAMIENTO, par del clock
  // (que marca el solape de horario). Ver screensConflictReason en domain/schedule.
  route:    `<svg aria-hidden="true" focusable="false" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="6" cy="19" r="3"/><path d="M9 19h8.5a3.5 3.5 0 0 0 0-7h-11a3.5 3.5 0 0 1 0-7H15"/><circle cx="18" cy="5" r="3"/></svg>`,
  play:     `<svg aria-hidden="true" focusable="false" width="13" height="13" viewBox="0 0 24 24" fill="currentColor" stroke="none"><polygon points="5 3 19 12 5 21 5 3"/></svg>`,
  calendar: `<svg aria-hidden="true" focusable="false" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path stroke-linecap="round" stroke-linejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5"/></svg>`,
  calendarPlus: `<svg aria-hidden="true" focusable="false" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path stroke-linecap="round" stroke-linejoin="round" d="M8 2v4M16 2v4M21 13V6a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h8M3 10h18M16 19h6M19 16v6"/></svg>`,
  alert:    `<svg aria-hidden="true" focusable="false" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"/></svg>`,
  chevronR: `<svg aria-hidden="true" focusable="false" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5"/></svg>`,
  chevronD: `<svg aria-hidden="true" focusable="false" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5"/></svg>`,
  share:    `<svg aria-hidden="true" focusable="false" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"/></svg>`,
  image:    `<svg aria-hidden="true" focusable="false" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path stroke-linecap="round" stroke-linejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z"/></svg>`,
  search:   `<svg aria-hidden="true" focusable="false" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z"/></svg>`,
  sparkles: `<svg aria-hidden="true" focusable="false" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z"/></svg>`,
  checkCircle:`<svg aria-hidden="true" focusable="false" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`,
  pin:      `<svg aria-hidden="true" focusable="false" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path stroke-linecap="round" stroke-linejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z"/></svg>`,
  // bookmark/bookmarkFill (Lucide) — PRIORIDAD (18 jul 2026). Decisión: la estrella
  // se reserva a CALIFICACIÓN (convención universal del cine); prioridad = marcador
  // ("marcado para no perdérmelo"). Ver leyenda de vocabulario en main.js.
  bookmark:    `<svg aria-hidden="true" focusable="false" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2Z"/></svg>`,
  bookmarkFill:`<svg aria-hidden="true" focusable="false" width="13" height="13" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2Z"/></svg>`,
  // chevronL — par de chevronR (navegación de día); antes era SVG inline suelto.
  chevronL: `<svg aria-hidden="true" focusable="false" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5"/></svg>`,
  // moon — "tu día terminó" (fase evening del día). Antes SVG inline en agenda.
  moon: `<svg aria-hidden="true" focusable="false" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path stroke-linecap="round" stroke-linejoin="round" d="M21.752 15.002A9.718 9.718 0 0118 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 003 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 009.002-5.998z"/></svg>`,
};

export function isFullDayBlocked(day){return availability[day].blocks.some(b=>toMin(b.from)<=0&&toMin(b.to)>=toMin('23:59'));}

export function renderAvBlocksHTML(state){
  const {availability} = state.snapshot();
  const items=[];
  DAY_KEYS.forEach(day=>{
    const lbl=(DAY_ABBR&&DAY_ABBR[day])||day.slice(0,3).toUpperCase();
    const num=(DAY_NUM&&DAY_NUM[day])||'';
    const fullBlocked=isFullDayBlocked(day);
    const visible=availability[day]?.blocks.filter(b=>!(toMin(b.from)<=0&&toMin(b.to)>=toMin('23:59')))||[];
    if(fullBlocked){
      items.push(`<div class="av-block-item is-full">
        <span class="av-block-day">${lbl} ${num}</span>
        <span class="av-block-time">${t('av_todo_el_dia')}</span>
        <button class="av-block-rm" data-action="toggleFullDay" data-day="${day}" title="${t('misc_quitar')}">${ICONS.x}</button>
      </div>`);
    } else {
      visible.forEach(b=>{
        items.push(`<div class="av-block-item">
          <span class="av-block-day">${lbl} ${num}</span>
          <span class="av-block-time">${b.from} – ${b.to}</span>
          <button class="av-block-rm" data-action="removeBlock" data-day="${day}" data-from="${b.from}" data-to="${b.to}" title="${t('misc_quitar')}">${ICONS.x}</button>
        </div>`);
      });
    }
  });
  return items.length?`<div class="av-block-list">${items.join('')}</div>`:'';
}

// p8 (fix urgente): buildResultHTML reubicado a view/agenda.js — usaba helpers +
// mkAgendaRow + domain (capas superiores) → pertenece a agenda; evita ciclos.

export function renderFlowProgress(state,activeTab){
  // activeTab: qué tab está activo ahora ('cartelera'|'seleccion'|'planner'|'miplan')
  // Paso activo = tab actual. ✓ solo cuando hay plan guardado.
  // Escalable: misma lógica para cualquier festival.
  const {savedAgenda} = state.snapshot();
  const hasPlan=savedAgenda&&savedAgenda.schedule&&savedAgenda.schedule.length>0;
  const tabStep={'cartelera':0,'seleccion':1,'planner':2,'miplan':3};
  const currentStep=tabStep[activeTab]||1;

  const mkStep=(n,label)=>{
    const isDone=hasPlan&&n<3;  // ✓ solo cuando plan guardado
    const isActive=n===currentStep;
    const cls=`flow-step${isDone?' done':isActive?' active':''}`;
    const dotContent=isDone?'✓':n.toString();
    return`<div class="${cls}"><div class="flow-step-dot">${dotContent}</div><span>${label}</span></div>`;
  };

  return`<div class="flow-progress">
    ${mkStep(1,t('nav_intereses'))}
    <div class="flow-step-sep"></div>
    ${mkStep(2,t('nav_planear'))}
    <div class="flow-step-sep"></div>
    ${mkStep(3,t('nav_miplan'))}
  </div>`;
}

export const DAY_ABBR={};

export const DAY_NUM ={};

export function starSVG(fill){
  // fill: 'none' | 'half' | 'full'
  const id='rs'+Math.random().toString(36).slice(2,6);
  const grad=fill==='half'
    ?`<defs><linearGradient id="${id}"><stop offset="50%" stop-color="var(--amber)"/><stop offset="50%" stop-color="transparent"/></linearGradient></defs>`
    :'';
  const fillVal=fill==='none'?'none':fill==='full'?'var(--amber)':`url(#${id})`;
  const stroke=fill==='none'?'var(--gray)':'var(--amber)';
  return`<svg aria-hidden="true" focusable="false" class="block-shrink" width="28" height="28" viewBox="0 0 24 24">${grad}<polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26" fill="${fillVal}" stroke="${stroke}" stroke-width="1.75" stroke-linejoin="round"/></svg>`;
}

export function renderRatingStarsHTML(state, current){
  let html='';
  for(let i=1;i<=5;i++){
    const fill=current>=i?'full':current>=i-0.5?'half':'none';
    html+=`<div class="touch-44">${starSVG(fill)}</div>`;
  }
  return html;
}


// _langDates — DUEÑO ÚNICO de «las fechas del festival como texto». Vivía en
// helpers.js con un solo consumidor mientras el header interno, la card del riel
// y la imagen de «Compartir mi festival» repetían el ternario por su cuenta — y
// cuando FICMA se aplazó, tres superficies siguieron prometiendo «10–17 AGO»
// (la del share, HORNEADA en un PNG que la gente manda por WhatsApp y no se
// corrige con un deploy; hallazgo de Onboarding, 10 ago 2026). Un festival
// aplazado no tiene fechas: tiene un estado. Se muda ACÁ porque helpers importa
// components (ciclo); helpers lo re-exporta para sus consumidores.
// `lang` opcional: default al estado global, pero quien ya tiene el idioma en la
// mano (la card del riel lo recibe de su render) lo pasa explícito — el unit test
// del riel cazó que ignorarlo rompía el contrato de _renderSplashRailHTML(state).
// postponedBannerHTML — markup ÚNICO del aviso de festival aplazado. Dos hosts lo
// pintan: el header del Programa (renderPostponedBanner) y Mi Plan (renderAgenda).
// Las palabras son del FESTIVAL (note verbatim; note_en traducción aprobada por
// Juan). Sin botón de cerrar: es contexto, no notificación.
export function postponedBannerHTML(cfg,{id=''}={}){
  if(!cfg||!cfg.status||cfg.status.kind!=='postponed') return '';
  const {_lang}=state.snapshot();
  const _esc=s=>String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;');
  const note=(_lang!=='es'&&cfg.status.note_en)||cfg.status.note;
  return`<div class="fest-postponed-banner"${id?` id="${id}"`:''}>
    <div class="notice-banner-dot"></div>
    <div class="notice-banner-body">
      <div class="notice-banner-label">${t('fest_postponed_label')}</div>
      <div class="notice-banner-text">${_esc(note)}${cfg.status.url?`<br><a class="fest-postponed-link" href="${_esc(cfg.status.url)}" target="_blank" rel="noopener">${t('fest_postponed_link')}</a>`:''}</div>
    </div>
  </div>`;
}

export function _langDates(cfg,lang){
  if(cfg&&cfg.status&&cfg.status.kind==='postponed') return t('fest_postponed_dates');
  const _l=lang||state.snapshot()._lang;
  return (_l==='en'&&cfg&&cfg.dates_en)?cfg.dates_en:(cfg&&cfg.dates)||'';
}

export function _classifyFestival(cfg){
  // APLAZADO — estado DECLARADO (cfg.status), no derivado: le gana a la aritmética
  // de fechas. Nace del terremoto de Manizales (FICMA 17, 10 ago 2026): sus fechas
  // decían «en curso» mientras el festival anunciaba que no habría festival. Un
  // aplazado jamás cuenta como ongoing (preselección, punto verde, rehidratación
  // del plan) ni como past (sigue siendo noticia viva). Reversión: fechas nuevas
  // + borrar `status` — sin re-onboarding. Guardián: [festival-aplazado].
  if(cfg.status&&cfg.status.kind==='postponed') return 'postponed';
  const now=new Date();
  const start=cfg.festivalStartStr?new Date(cfg.festivalStartStr):null;
  const end=cfg.festivalEndStr?new Date(cfg.festivalEndStr):null;
  if(!end) return 'upcoming';          // sin fecha de cierre → tratar como próximo
  if(now>end) return 'past';           // ya terminó
  if(start&&now<start) return 'upcoming'; // aún no empieza
  return 'ongoing';                    // entre start y end → en curso
}

// ¿Un aplazado ya dejó de ser noticia? (Juan, 23 ago 2026)
//
// `_classifyFestival` nunca devuelve 'past' para un aplazado, y eso fue
// deliberado: FICMA se aplazó por el terremoto el 10 de agosto, y mandarlo al
// fondo del riel habría escondido justo lo que la gente necesitaba leer.
//
// Pero esa razón CADUCA. Pasadas sus fechas anunciadas, el aplazado deja de ser
// noticia y pasa a ser ruido en la zona de los vigentes — que es como Juan lo
// encontró seis días después del 17. La bisagra es la fecha de cierre que el
// festival había anunciado: antes es noticia viva, después es historia.
//
// Vive SOLO en el orden y la partición del riel. La clasificación no se toca:
// un aplazado sigue sin contar como en curso, sin preselección, y con su banner
// explicando por qué está donde está. Guardián: [aplazado-caduca].
export function _postponedElapsed(cfg){
  if(!cfg||!cfg.status||cfg.status.kind!=='postponed') return false;
  if(!cfg.festivalEndStr) return false;   // sin fecha declarada no hay bisagra
  return new Date()>new Date(cfg.festivalEndStr);
}

export function _sortFestivals(entries, activeFestId){
  const _tier=([id,cfg])=>{
    if(id===activeFestId) return 0;
    const cls=_classifyFestival(cfg);
    if(cls==='ongoing')  return 1;
    if(cls==='upcoming') return 2;
    if(cls==='postponed') return _postponedElapsed(cfg)?4:3; // vigente sin invitación… hasta que sus fechas pasan
    return 4; // past
  };
  // PRIORIDAD EDITORIAL — desempata DENTRO del tier, antes que la fecha.
  // Nace de FINCA vs FICDEH (8 ago 2026): mismas fechas exactas, y quién salía
  // primero lo decidía un accidente de datos —30 minutos de diferencia en
  // festivalEndStr—. Con una alianza oficial y otra parcial, esa decisión es
  // editorial y tiene que estar declarada, no emerger del ruido.
  // Sin `priority` en el config, todo se comporta como antes.
  const _prio=([,cfg])=>(cfg.priority??99);
  return entries.sort((a,b)=>{
    const ta=_tier(a),tb=_tier(b);
    if(ta!==tb) return ta-tb;
    const pa=_prio(a),pb=_prio(b);
    if(pa!==pb) return pa-pb;
    // ongoing: termina antes primero
    if(ta===1) return new Date(a[1].festivalEndStr||0)-new Date(b[1].festivalEndStr||0);
    // upcoming (y aplazados entre sí): empieza antes primero
    if(ta===2||ta===3) return new Date(a[1].festivalStartStr||'2099-01-01')-new Date(b[1].festivalStartStr||'2099-01-01');
    // past: más reciente primero
    return new Date(b[1].festivalEndStr||0)-new Date(a[1].festivalEndStr||0);
  });
}

// Etiqueta unificada de festival para selector + header. Primera palabra del
// `name` (case correcto: siglas en MAYÚS, marcas en Title Case) + año. UNA fuente
// de verdad → activos, anteriores, header y botón cerrado muestran lo MISMO.
// Reemplaza el uso de `shortName` (que estaba en MAYÚSCULA, inconsistente con la
// primera-palabra Title Case de otros). El año va en el título (es fundamental);
// el subtítulo queda solo ciudad · fechas.
// festivalShortName — la etiqueta compacta de la marca (splash, topbar, selector).
// Heurístico: primer token del name (FICCI 65→FICCI, Tribeca Festival→Tribeca,
// FantasoFest→FantasoFest). Para marcas multi-palabra que el primer token parte
// mal (Tercer Tiempo Fest), el config pone un `displayName` explícito. NO confundir
// con `shortName` (slug MAYÚSCULA para nombres de archivo en share.js).
export function festivalShortName(cfg){ return cfg.displayName || (cfg.name||'').split(' ')[0]; }
export function festivalLabel(cfg){ const n=festivalShortName(cfg); return cfg.year?`${n} · ${cfg.year}`:n; }

// festivalSeasonYear — el año "vigente" que ancla el header del selector UNA sola
// vez (minimalismo: no repetir 2026 en cada fila). Es el año más reciente entre
// los festivales vigentes (en curso + próximos); si todo es pasado, el más reciente
// del conjunto. Las filas cuyo año difiera de este SÍ muestran el suyo (desambiguar).
export function festivalSeasonYear(){
  const entries=Object.entries(FESTIVAL_CONFIG).filter(([,c])=>c.name&&c.group!=='test');
  const vigentes=entries.filter(([,c])=>_classifyFestival(c)!=='past');
  const pool=vigentes.length?vigentes:entries;
  return pool.reduce((mx,[,c])=>(c.year>mx?c.year:mx),0)||null;
}

// festivalTagline — el descriptor del festival para la 2ª línea del selector-splash,
// DERIVADO de `fullName` (fuente única; sin campo aparte que mantener). Reglas,
// verificadas contra los 9 festivales reales (unit test splashTagline):
//   1. `tagline` explícito en config → gana (escape hatch para casos raros). Puede
//      ser string, o un objeto {es,en} para taglines localizados (Tribeca: descriptor
//      ES + nombre original EN). El lang cae a 'es' si no se pasa o no hay variante.
//   2. fullName vacío, o fullName === name → '' (el nombre ya lo dice: Tribeca).
//   3. fullName con separador em/en-dash → el descriptor es la parte tras el dash
//      (FantasoFest — Muestra… → "Muestra…"; Olhar de Cinema – Festival… → "Festival…").
//   4. Sin dash → quitar el shortName del inicio o fin (Leviza al final, Cinemancia
//      al inicio). Si el shortName no aparece → fullName tal cual (FICCI, AFF).
export function festivalTagline(cfg, lang='es'){
  if(cfg.tagline!==undefined){
    const tg=cfg.tagline;
    return (tg && typeof tg==='object') ? (tg[lang] ?? tg.es ?? '') : tg;
  }
  const full=(cfg.fullName||'').trim(), name=(cfg.name||'').trim();
  if(!full || full===name) return '';
  const parts=full.split(/\s*[—–]\s*/);
  if(parts.length===2) return parts[1].trim();
  const sh=festivalShortName(cfg).replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
  return full.replace(new RegExp('^'+sh+'\\b[\\s,:–—-]*','i'),'')
             .replace(new RegExp('[\\s,:–—-]*\\b'+sh+'$','i'),'').trim() || full;
}

// _renderSplashRailHTML — carrusel de afiches del selector-splash (reemplaza el
// dropdown vertical). VIGENTES (en curso + próximos, brillo pleno) → divisor
// "ANTERIORES" → PASADOS (atenuados). Cada card lleva data-name/data-meta para
// preservar la firma de selectSplashFest(name,meta,festId).
// Sin afiche (keyArt) → fallback tipográfico con el shortName.
// ORDEN ESTABLE: _sortFestivals recibe null — el tier 0 "seleccionado primero"
// era semántica del dropdown; en un carrusel posicional, reordenar en un
// re-render (p.ej. setLang) teletransporta las cards y desalinea el centro del
// scroll con la selección (bug cazado en QA: la card centrada dejaba de ser la
// .on → el próximo gesto de scroll pisaba la selección). activeFestId aquí solo
// marca .on/aria-selected.
// _festivalCardHTML — FUENTE ÚNICA de la card-afiche de festival. La usan las DOS
// superficies donde se elige festival: el riel del splash y el sheet "cambiar
// festival". Rediseño 20 jul 2026 (feedback real de usuario: "¿cómo vuelvo al menú
// donde estaban los festivales?"): el sheet era una lista de texto con miniaturas de
// 27px y no se reconocía como el mismo lugar que el muro de afiches de la entrada.
// Mismo vocabulario visual en ambas → reconocimiento inmediato.
// `action` es lo ÚNICO que difiere por superficie: en el splash SELECCIONA (el
// usuario confirma con "Entrar"); en el sheet CARGA directo (no hay confirmación).
// keyArtPos → custom property --kap (no inline style raw: ARQUITECTURA §10.3);
// onerror=this.remove() degrada al template negro si el afiche 404ea (§10.2).
function _festivalCardHTML([id,cfg], {isPast, isActive, action, lang, review}){
  const meta=`${cfg.city} · ${_langDates(cfg,lang)}`;
  const label=festivalLabel(cfg);
  const art=cfg.keyArt
    ? `<img class="splash-card-art" src="${cfg.keyArt}" alt="" loading="lazy" onerror="this.remove()"${cfg.keyArtPos?` style="--kap:${cfg.keyArtPos}"`:''}>`
    : `<span class="splash-card-fb">${festivalShortName(cfg)}</span>`;
  // Distintivo APLAZADO sobre el afiche — fuente única: sale en el riel del splash
  // Y en el sheet «cambiar festival» sin tocar cada superficie.
  const _postponed=_classifyFestival(cfg)==='postponed';
  // Sin badge para revisión (Juan, 23 ago 2026): las cards en revisión viven
  // DESPUÉS del divisor «EN REVISIÓN» del riel, así que el badge decía lo que la
  // pantalla ya dice al lado. El de APLAZADO se queda: su grupo no tiene divisor
  // propio y el badge es la única señal en la card.
  const badge=_postponed?`<span class="splash-card-badge">${t('fest_postponed_label')}</span>`:'';
  return`<button class="splash-card${isPast?' past':''}${isActive?' on':''}${_postponed?' postponed':''}${review?' review':''}" data-fest="${id}" role="option" aria-selected="${isActive}" data-action="${action}" data-name="${label}" data-meta="${meta}"><span class="splash-card-tpl">${art}</span>${badge}</button>`;
}

// `action` parametriza la superficie (20 jul 2026): el splash SELECCIONA (confirma
// con "Entrar"); el sheet "cambiar festival" CARGA directo. Todo lo demás —orden,
// partición vigentes/pasados, divisor "ANTERIORES"— es idéntico, así que el riel es
// UNO SOLO y no dos implementaciones que se desincronizan.
// _enRevision — ¿este festival está en revisión del propio festival, y todavía?
// Vive en el riel pero SOLO dentro de la app: en un navegador el store gate ya
// mandó al usuario a las tiendas, así que web y app se ven distinto a propósito.
// `until` la apaga sola: un permiso temporal que hay que acordarse de revocar
// es, en la práctica, un permiso permanente.
export function _enRevision(cfg){
  const r=cfg&&cfg.review;
  if(!r||!r.key) return false;
  if(r.until&&new Date()>new Date(r.until+'T23:59:59')) return false;
  return globalThis.__otfIsApp===true||globalThis.__otfIsDev===true;
}

export function _renderSplashRailHTML(state, activeFestId, action='selectSplashFest', conRevision=true){
  const {_lang} = state.snapshot();
  const _todos=Object.entries(FESTIVAL_CONFIG).filter(([,cfg])=>cfg.name);
  const entries=_sortFestivals(_todos.filter(([,cfg])=>cfg.group!=='test'), null);
  // Los de revisión salen aparte: group:'test' los mantiene fuera de todo lo
  // demás —validadores, sheet de festivales, preselección— y esto los devuelve
  // solo acá, al final del riel.
  // SOLO en el splash. El sheet «cambiar festival» reutiliza este mismo riel
  // pero con action='loadFestival', que entra DIRECTO — sin pasar por
  // dismissSplash, que es donde vive la clave. Con la card ahí, el festival en
  // revisión quedaba abierto a un toque, sin clave: la puerta con llave al lado
  // de una ventana abierta.
  const revision=conRevision?_todos.filter(([,cfg])=>cfg.group==='test'&&_enRevision(cfg)):[];
  // «pasado» para el RIEL incluye al aplazado cuyas fechas ya pasaron — ver
  // _postponedElapsed. La clasificación sigue diciendo 'postponed'; lo que
  // cambia es dónde se dibuja.
  const _esPasado=cfg=>_classifyFestival(cfg)==='past'||_postponedElapsed(cfg);
  const current = entries.filter(([,cfg])=>!_esPasado(cfg));
  const past    = entries.filter(([,cfg])=>_esPasado(cfg));
  // isPast se pasa desde la partición (una sola clasificación por festival) — no
  // re-clasificar dentro de mkCard: evita que la card caiga en un grupo y se pinte
  // con la clase del otro en un boundary de fecha.
  const mkCard=(e,isPast)=>_festivalCardHTML(e,{isPast,isActive:e[0]===activeFestId,action,lang:_lang});
  // El año de temporada NO se muestra cuando todos los festivales comparten año (hoy,
  // todos 2026 → repetirlo no suma; minimalismo). El único lugar donde aparece es la
  // FECHA del info, y solo si el año de ESE festival DIFIERE de la temporada
  // (festivalSeasonYear) — ver _fillSplashInfo. A FUTURO, cuando el riel mezcle años,
  // acá cabría un divisor de año (mismo patrón que "ANTERIORES", agrupando por año).
  // Un divisor SEPARA dos grupos: se emite solo si hay algo de los dos lados. Colgar
  // uno de primero descentra el snap inicial y rompe la auto-selección.
  const div=lbl=>`<span class="splash-rail-div" aria-hidden="true"><span class="srd-bar"></span><span class="srd-lbl">${lbl}</span><span class="srd-bar"></span></span>`;
  const ongoing =current.filter(([,cfg])=>_classifyFestival(cfg)==='ongoing');
  const upcoming=current.filter(([,cfg])=>_classifyFestival(cfg)!=='ongoing');
  // "PRÓXIMOS" — en curso y por empezar viajaban en el MISMO grupo, sin nada que los
  // distinga: con FICMA abierto y FICDEH/FINCA a dos días, las tres cards se leían
  // igual de disponibles. El tier ya existía en _sortFestivals; lo que faltaba era
  // decirlo en pantalla. Misma tira y misma dirección: los próximos NO se mudan a la
  // izquierda —eso haría correr el tiempo de derecha a izquierda y obligaría a
  // arrancar el riel desplazado, que es de lo que depende la preselección—.
  // Aplazados: dentro de los vigentes (siguen siendo noticia, no historia) pero
  // FUERA del grupo «Próximos» — un aplazado no es un próximo: no tiene fecha. Van
  // al final del grupo vigente, con su distintivo como única etiqueta.
  const _upc=upcoming.filter(([,cfg])=>_classifyFestival(cfg)!=='postponed');
  const _post=upcoming.filter(([,cfg])=>_classifyFestival(cfg)==='postponed');
  let html=ongoing.map(e=>mkCard(e,false)).join('');
  if(ongoing.length && _upc.length) html+=div(t('fs_proximos'));
  html+=_upc.map(e=>mkCard(e,false)).join('');
  html+=_post.map(e=>mkCard(e,false)).join('');
  if(current.length && past.length) html+=div(t('splash_anteriores'));
  html+=past.map(e=>mkCard(e,true)).join('');
  // Al FINAL de todo y con divisor propio: no compite con los vigentes ni se
  // confunde con un pasado. Un divisor separa dos grupos, así que solo se emite
  // si hay algo antes.
  if(revision.length){
    if(entries.length) html+=div(t('splash_en_revision'));
    html+=revision.map(e=>_festivalCardHTML(e,{isPast:false,isActive:e[0]===activeFestId,action,lang:_lang,review:true})).join('');
  }
  return html;
}

// _renderFestivalSelectorHTML — el chooser del sheet ES el riel del splash.
// Rediseño 20 jul 2026 (2ª iteración, feedback de Juan: "¿por qué no replicaste la
// estructura del splash?"). La 1ª iteración inventó una estructura propia —tres
// encabezados de grupo (EN CURSO/PRÓXIMOS/ANTERIORES) y un rótulo por card— cuando
// el riel del splash YA resolvía lo mismo mejor: una sola tira con divisor vertical
// "ANTERIORES", y el bloque .splash-info de 4 líneas (nombre / descriptor / CIUDAD
// con punto verde si está en curso / FECHAS) que se actualiza al desplazar.
// Ahora NO hay dos implementaciones: esta delega en el riel único y solo cambia la
// acción (cargar directo en vez de seleccionar+"Entrar"). El info lo puebla
// _renderFestivalSelector (controller/festival.js) reusando _fillFestInfo.
export function _renderFestivalSelectorHTML(state, activeFestId){
  return _renderSplashRailHTML(state, activeFestId, 'loadFestival', false);
}

// p8 Step 6b (D-6B-2): util de título compartida (usada por feedback/programa/agenda).
export function parseProgramTitle(t){
  let displayTitle=t, progSuffix='';
  const f=FILMS.find(fi=>fi.title===t);
  if(f?.is_awards_screening){
    displayTitle=t.replace(/^Award Screening:\s*/i,'');
  } else if(f?.is_cortos){
    // "Cortos: Familia 12+" → displayTitle="Familia 12+"
    if(t.match(/^Cortos:\s*/i)){
      displayTitle=t.replace(/^Cortos:\s*/i,'');
    } else if(t.match(/^Shorts:\s*/i)){
      displayTitle=t.replace(/^Shorts:\s*/i,'');
    } else if(t.startsWith('Prog.')){
      const m=t.match(/^(Prog\.[^—–]+)\s*[—–]\s*(.+)$/);
      if(m){displayTitle=m[2].trim();progSuffix=m[1].trim();}
    } else {
      const m=t.match(/^(.+?)\s*[—–]\s*(Prog\..*)$/);
      if(m){displayTitle=m[1];progSuffix=m[2];}
    }
    if(progSuffix&&!/\d/.test(progSuffix)) progSuffix='';
  }
  return{displayTitle,progSuffix};
}
