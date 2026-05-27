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

import { FESTIVAL_CONFIG, SECTION_COLORS, SECTION_EN } from "../config.js";
import { toMin } from "../domain/time.js";
import { t } from "../i18n/i18n.js";
import { state } from "../state/state.js";

export function makeProgramPoster(state, title, duration, section){
  const {FILMS} = state.snapshot();
  const filmSec=section||(FILMS.find(f=>f.title===title)?.section)||'';
  const sec=filmSec.toLowerCase();

  // ── Paleta de 6 colores canónicos — asignados por hash de sección ──
  // Consistente: misma sección → mismo color en cualquier festival
  const ACCENT_PALETTE=['#F59E0B','#3AAA6E','#E5A020','#E05252','#378ADD','#3A8E8E'];
  const _hash=s=>[...s].reduce((h,c)=>(Math.imul(31,h)+c.charCodeAt(0))|0,0);
  const accent=ACCENT_PALETTE[Math.abs(_hash(sec))%ACCENT_PALETTE.length];

  // Header: sección localizada vía _secLabel (lang-aware: EN→SECTION_EN,
  // ES→original sin emoji), uppercase. Así el poster editorial coincide con el
  // separador del grid en cada idioma — antes horneaba f.section crudo y se
  // quedaba en español aunque la UI estuviera en EN.
  const cleanSection=_secLabel(filmSec).toUpperCase();
  const headerLabel=cleanSection||'PROGRAMA';

  // Número — patrones: "Prog. 4", "Prog. 1 · 16mm", "Voces 2", número al final
  const numMatch=title.match(/(?:Prog\.\s*|Programa\s+)(\d+)|(?:—\s*|:\s*|Prog\.\s*)(\d+)\s*(?:·|$)|\s(\d+)\s*$/);
  const num=numMatch?(numMatch[1]||numMatch[2]||numMatch[3]):null;

  // Día — extrae nombre de día al final del título ("— Jueves" → "JUE")
  // Solo aplica cuando no hay número (los programas numerados ya tienen su diferenciador)
  const _dayNameMap={'lunes':'LUN','martes':'MAR','miércoles':'MIÉ','miercoles':'MIÉ',
    'jueves':'JUE','viernes':'VIE','sábado':'SÁB','sabado':'SÁB','domingo':'DOM'};
  const _dayMatch=!num&&title.match(/[—\-]\s*([a-záéíóúüñ]+)\s*$/i);
  const dayAbbr=_dayMatch?(_dayNameMap[_dayMatch[1].toLowerCase()]||null):null;

  // Body: siempre vacío cuando hay número (el header + número son suficientes)
  // Sin número: extraer solo la parte distintiva
  let bodyTitle='';
  if(!num){
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

  return _buildPosterV16({accent, headerLabel, title:bodyTitle, num:num||dayAbbr||null});
}

export function makeSorpresaPoster(){
  return _buildPosterV16({
    accent:'#F59E0B',
    headerLabel:'PROYECCIÓN SORPRESA',
    title:'?',
    num:null
  });
}

export function _sectionColor(sec){return SECTION_COLORS[sec]||'#2C2C2A';}

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

export function _buildPosterV16({accent, headerLabel, title, num}){
  // ── Motor de poster tipográfico v16 ──────────────────────────
  // Sistema único para eventos, programas, sorpresa.
  // Header sólido en accent (~52/180px) + body surf-2.
  // Variante A (num!=null): título arriba + número en accent abajo.
  // Variante B (num===null): título expande desde abajo.
  // ─────────────────────────────────────────────────────────────
  const VW=120,VH=180,HDR=52,PAD=8;

  function wrap(str,maxCh){
    if(!str)return[''];
    const words=str.split(' '),lines=[];let cur='';
    for(const w of words){if(cur&&(cur+' '+w).length>maxCh){lines.push(cur);cur=w;}else cur=cur?cur+' '+w:w;}
    if(cur)lines.push(cur);return lines;
  }

  // Header label
  const hLines=wrap(headerLabel||'',15);
  const hFS=6.5,hLD=9;
  const hTotalH=hLines.length*hLD;
  const hStartY=(HDR-hTotalH)/2+hFS;
  const headerText=hLines.map((l,i)=>
    `<text x="${PAD}" y="${hStartY+i*hLD}" font-family="-apple-system,BlinkMacSystemFont,sans-serif" font-size="${hFS}" font-weight="800" letter-spacing="0.7" fill="#0A0A0A">${l}</text>`
  ).join('');

  // Body
  let bodyContent='';
  // El strip de número final solo aplica en Variante A (num se muestra aparte,
  // evita duplicarlo). En Variante B el título se muestra tal cual — si no, un
  // body como "PGM 05" perdería el "05" y dejaría dos programas indistinguibles.
  const cleanTitle=(num!==null&&num!==undefined)
    ? (title||'').replace(/\s+\d+\s*$/,'').trim()
    : (title||'').trim();

  if(num!==null&&num!==undefined){
    // Variante A — número como elemento principal
    const bodyH=VH-HDR;
    const numFS=32;
    const numY=HDR+(bodyH/2)+(numFS/3); // centrado vertical en el body
    const titleText=cleanTitle
      ? (()=>{
          const tLines=wrap(cleanTitle,12);
          const tFS=11,tLD=14;
          return tLines.map((l,i)=>
            `<text x="${PAD}" y="${HDR+PAD+tFS+i*tLD}" font-family="-apple-system,BlinkMacSystemFont,sans-serif" font-size="${tFS}" font-weight="800" letter-spacing="-0.3" fill="#F0EDE8">${l}</text>`
          ).join('');
        })()
      : '';
    bodyContent=titleText+`<text x="${VW/2}" y="${numY}" font-family="-apple-system,BlinkMacSystemFont,sans-serif" font-size="${numFS}" font-weight="800" letter-spacing="-1" fill="${accent}" text-anchor="middle">${num}</text>`;
  } else {
    // Variante B — título anclado abajo
    const tLines=wrap(cleanTitle,12);
    const tFS=11,tLD=14;
    const totalH=tLines.length*tLD;
    const startY=VH-PAD-totalH+tLD;
    bodyContent=tLines.map((l,i)=>
      `<text x="${PAD}" y="${startY+i*tLD}" font-family="-apple-system,BlinkMacSystemFont,sans-serif" font-size="${tFS}" font-weight="800" letter-spacing="-0.3" fill="#F0EDE8">${l}</text>`
    ).join('');
  }

  const svg=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${VW} ${VH}">
    <rect width="${VW}" height="${VH}" fill="#1A1A1A"/>
    <rect width="${VW}" height="${HDR}" fill="${accent}"/>
    ${headerText}
    ${bodyContent}
  </svg>`;
  return `data:image/svg+xml,${encodeURIComponent(svg)}`;
}

export function makeEventPoster(state,title,duration,eventKind,section){
  const {_activeFestId, _lang} = state.snapshot();
  const festCfg=(FESTIVAL_CONFIG&&FESTIVAL_CONFIG[_activeFestId])||Object.values(FESTIVAL_CONFIG||{})[0]||{};
  const _kindMapES={
    'ponencia':     {accent:'#F59E0B', headerLabel:'PONENCIA'},
    'masterclass':  {accent:'#7F77DD', headerLabel:'MASTERCLASS'},
    'encuentro':    {accent:'#378ADD', headerLabel:'ENCUENTRO'},
    'cineconcierto':{accent:'#D85A30', headerLabel:'CINECONCIERTO'},
    'awards':       {accent:'#BA7517', headerLabel:'AWARDS SCREENINGS'},
  };
  const _kindMapEN={
    'ponencia':     {accent:'#F59E0B', headerLabel:'TALK'},
    'masterclass':  {accent:'#7F77DD', headerLabel:'MASTERCLASS'},
    'encuentro':    {accent:'#378ADD', headerLabel:'MEETING'},
    'cineconcierto':{accent:'#D85A30', headerLabel:'FILM CONCERT'},
    'awards':       {accent:'#BA7517', headerLabel:'AWARDS SCREENINGS'},
  };
  const _kindMap=_lang==='es'?_kindMapES:_kindMapEN; // PT reutiliza EN (términos internacionales)
  const kind=_kindMap[eventKind];
  if(kind) return _buildPosterV16({...kind, title, num:null});
  // Fallback — usa la sección del film si existe, sino eventPosterLabel del config
  const _secFallback=section?_secLabel(section):'';
  const lbl=_secFallback?[_secFallback]:((festCfg.eventPosterLabel)||['EVENTO','']);
  const headerLabel=lbl.filter(Boolean).join(' ');
  const _sectionAccent=section?_sectionColor(section):'#6B9BD1';
  return _buildPosterV16({accent:_sectionAccent||'#6B9BD1', headerLabel, title, num:null});
}

export const ICONS={
  star:     `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>`,
  starFill: `<svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>`,
  heart:    `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path stroke-linecap="round" stroke-linejoin="round" d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z"/></svg>`,
  heartFill:`<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path stroke-linecap="round" stroke-linejoin="round" d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z"/></svg>`,
  x:        `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>`,
  check:    `<svg class="block-shrink" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5"/></svg>`,
  undo:     `<svg class="block-shrink" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path stroke-linecap="round" stroke-linejoin="round" d="M9 15L3 9m0 0l6-6M3 9h12a6 6 0 010 12h-3"/></svg>`,
  switch:   `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path stroke-linecap="round" stroke-linejoin="round" d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5"/></svg>`,
  plus:     `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15"/></svg>`,
  clock:    `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`,
  play:     `<svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor" stroke="none"><polygon points="5 3 19 12 5 21 5 3"/></svg>`,
  calendar: `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path stroke-linecap="round" stroke-linejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5"/></svg>`,
  alert:    `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"/></svg>`,
  chevronR: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5"/></svg>`,
  chevronD: `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5"/></svg>`,
  share:    `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"/></svg>`,
  image:    `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path stroke-linecap="round" stroke-linejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z"/></svg>`,
  search:   `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z"/></svg>`,
  sparkles: `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z"/></svg>`,
  checkCircle:`<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`,
  pin:      `<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path stroke-linecap="round" stroke-linejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z"/></svg>`,
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
        <button class="av-block-rm" data-action="toggleFullDay" data-day="${day}" title="Quitar">${ICONS.x}</button>
      </div>`);
    } else {
      visible.forEach(b=>{
        items.push(`<div class="av-block-item">
          <span class="av-block-day">${lbl} ${num}</span>
          <span class="av-block-time">${b.from} – ${b.to}</span>
          <button class="av-block-rm" data-action="removeBlock" data-day="${day}" data-from="${b.from}" data-to="${b.to}" title="Quitar">${ICONS.x}</button>
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
  return`<svg class="block-shrink" width="28" height="28" viewBox="0 0 24 24">${grad}<polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26" fill="${fillVal}" stroke="${stroke}" stroke-width="1.75" stroke-linejoin="round"/></svg>`;
}

export function renderRatingStarsHTML(state, current){
  let html='';
  for(let i=1;i<=5;i++){
    const fill=current>=i?'full':current>=i-0.5?'half':'none';
    html+=`<div class="touch-44">${starSVG(fill)}</div>`;
  }
  return html;
}

export const CHECK_SVG=`<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5"/></svg>`;

export function _classifyFestival(cfg){
  const now=new Date();
  const start=cfg.festivalStartStr?new Date(cfg.festivalStartStr):null;
  const end=cfg.festivalEndStr?new Date(cfg.festivalEndStr):null;
  if(!end) return 'upcoming';          // sin fecha de cierre → tratar como próximo
  if(now>end) return 'past';           // ya terminó
  if(start&&now<start) return 'upcoming'; // aún no empieza
  return 'ongoing';                    // entre start y end → en curso
}

export function _sortFestivals(entries, activeFestId){
  const _tier=([id,cfg])=>{
    if(id===activeFestId) return 0;
    const cls=_classifyFestival(cfg);
    if(cls==='ongoing')  return 1;
    if(cls==='upcoming') return 2;
    return 3; // past
  };
  return entries.sort((a,b)=>{
    const ta=_tier(a),tb=_tier(b);
    if(ta!==tb) return ta-tb;
    // ongoing: termina antes primero
    if(ta===1) return new Date(a[1].festivalEndStr||0)-new Date(b[1].festivalEndStr||0);
    // upcoming: empieza antes primero
    if(ta===2) return new Date(a[1].festivalStartStr||'2099-01-01')-new Date(b[1].festivalStartStr||'2099-01-01');
    // past: más reciente primero
    return new Date(b[1].festivalEndStr||0)-new Date(a[1].festivalEndStr||0);
  });
}

export function _renderSplashDropdownHTML(state, activeFestId){
  const {_lang} = state.snapshot();
  const entries=_sortFestivals(Object.entries(FESTIVAL_CONFIG)
    .filter(([,cfg])=>cfg.name&&cfg.group!=='test'), activeFestId);
  const chevSvg=`<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9l6 6 6-6"/></svg>`;
  // Clasificar en tres grupos usando la fuente única de verdad
  const ongoing  = entries.filter(([,cfg])=>_classifyFestival(cfg)==='ongoing');
  const upcoming = entries.filter(([,cfg])=>_classifyFestival(cfg)==='upcoming');
  const past     = entries.filter(([,cfg])=>_classifyFestival(cfg)==='past');
  const mkItem=([id,cfg])=>{
    const isActive=id===activeFestId;
    const meta=`${cfg.city} · ${_lang==='en'&&cfg.dates_en?cfg.dates_en:cfg.dates} ${cfg.year||''}`.trim();
    return`<button class="splash-drop-item${isActive?' selected':''}" data-fest="${id}" role="option" aria-selected="${isActive}" data-action="selectSplashFest" data-name="${cfg.name}" data-meta="${meta}">
      <div><div class="splash-drop-item-name">${cfg.name}</div><div class="splash-drop-item-meta">${meta}</div></div>
    </button>`;
  };
  const mkPastItem=([id,cfg])=>{
    const meta=`${cfg.city} · ${_lang==='en'&&cfg.dates_en?cfg.dates_en:cfg.dates} ${cfg.year||''}`.trim();
    const shortLabel=(cfg.shortName||cfg.name.split(' ')[0])+' · '+cfg.year;
    return`<button class="splash-drop-item past" data-fest="${id}" role="option" aria-selected="false" data-action="togglePastFest">
      <div><div class="splash-drop-item-name">${shortLabel}</div><div class="splash-drop-item-meta">${meta}</div></div>
      <span class="past-item-chev">${chevSvg}</span>
    </button>`;
  };
  let html='';
  if(ongoing.length)  html+=`<div class="splash-drop-sep">${t('fs_en_curso')}</div>`+ongoing.map(mkItem).join('');
  if(upcoming.length) html+=`<div class="splash-drop-sep">${t('fs_proximos')}</div>`+upcoming.map(mkItem).join('');
  if(past.length)     html+=`<div class="splash-drop-sep">${t('splash_anteriores')}</div>`+past.map(mkPastItem).join('');
  return html;
}

export function _renderFestivalSelectorHTML(state, activeFestId){
  const {_lang} = state.snapshot();
  const entries=_sortFestivals(Object.entries(FESTIVAL_CONFIG)
    .filter(([,cfg])=>cfg.name&&cfg.group!=='test'), activeFestId);
  const chevSvg=`<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9l6 6 6-6"/></svg>`;
  // Clasificar en tres grupos — fuente única de verdad
  const ongoing  = entries.filter(([,cfg])=>_classifyFestival(cfg)==='ongoing');
  const upcoming = entries.filter(([,cfg])=>_classifyFestival(cfg)==='upcoming');
  const past     = entries.filter(([,cfg])=>_classifyFestival(cfg)==='past');
  function mkRow([id,cfg]){
    const isActive=id===activeFestId;
    const meta=`${cfg.city} · ${_lang==='en'&&cfg.dates_en?cfg.dates_en:cfg.dates} ${cfg.year||''}`.trim();
    const dotClass=`fs-fest-dot${isActive?' active':''}`;
    return`<div class="fs-festival-row" data-fest="${id}" data-action="loadFestival">
      <div class="${dotClass}"></div>
      <div class="fs-fest-info">
        <div class="fs-fest-name">${cfg.name}</div>
        <div class="fs-fest-meta">${meta}</div>
      </div>
      <div class="fs-fest-check" style="display:${isActive?'':'none'}">${CHECK_SVG}</div>
    </div>`;
  }
  function mkPastRow([id,cfg]){
    const meta=`${cfg.city} · ${_lang==='en'&&cfg.dates_en?cfg.dates_en:cfg.dates} ${cfg.year||''}`.trim();
    const shortLabel=(cfg.shortName||cfg.name.split(' ')[0])+' · '+cfg.year;
    return`<div class="fs-festival-row past" data-fest="${id}">
      <div class="fs-fest-dot past"></div>
      <div class="fs-fest-info" data-action="loadFestival" data-fest="${id}" style="cursor:pointer;flex:1;min-width:0">
        <div class="fs-fest-name">${shortLabel}</div>
        <div class="fs-fest-meta">${meta}</div>
      </div>
      <span class="fs-past-chev" data-action="togglePastFestRow" data-fest="${id}" style="padding:var(--sp-2);margin:-var(--sp-2);-webkit-tap-highlight-color:transparent">${chevSvg}</span>
    </div>`;
  }
  let html='';
  if(ongoing.length)  html+=`<div class="fs-section-lbl">${t('fs_en_curso')}</div>`+ongoing.map(mkRow).join('<div class="fs-divider"></div>');
  if(upcoming.length) html+=`<div class="fs-section-lbl">${t('fs_proximos')}</div>`+upcoming.map(mkRow).join('<div class="fs-divider"></div>');
  if(past.length)     html+=`<div class="fs-section-lbl">${t('splash_anteriores')}</div>`+past.map(mkPastRow).join('<div class="fs-divider"></div>');
  return html;
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
