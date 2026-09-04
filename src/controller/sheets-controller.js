// ── src/controller/sheets-controller.js ───────────────────────────────────────
// p8 Step 7d-1 — Capa UI-primitiva del controller (leaf): lifecycle de sheets
// (pel/corto/conflict/prio/planConfirm/PV-rating) + rating UI + AV sheet + toast
// + utils (LB/flags/genre/metaBanners) + plan-helpers. Closure AST = 51, 0
// pulled-in. La importa handlers.js (7d-2); no llama a mutators/filters; view no
// la importa (sin ciclo). Lets de UI-state module-local; LB_SLUGS vía bridge
// (lo escribe loadFestival). Roster/viewstate vía bridge.

import { FESTIVAL_CONFIG, MAX_REMEMBERED_SLOTS, TMDB_IMG, _DEFAULT_FEST_ID } from '../config.js';
import { DAY_ABBR, DAY_NUM, ICONS, _secLabel, _sectionColor, escXML, festivalTagline, isFullDayBlocked, makeProgramPoster, makeSharedSlotSVG, parseProgramTitle, renderRatingStarsHTML } from '../view/components.js';
import { _getItemPoster, _mkCortoItemHtml, _posterStyle, _posterThumb, dayLabel, emptyState, durFmt, flagFmt, getCortoItemPoster, getFilmPoster, getFilmPosterUntitled, getPosterSrc, itemPosterParts, posterAmbient, posterParts, sala, starsText, vcfg, venueCity, venueMatches, isCitySel, ticketBadgeTarget, conflictAccount, programParts} from '../view/helpers.js';
import { closeAvSheet, closePVRating, closePrioLimit } from '../view/sheets.js';
import { showConflictModal, showToast, _toastArriba } from '../view/feedback.js';
import { renderAgenda, renderAvBlocks, renderDiaryHTML } from '../view/agenda.js';
import { runCalc } from './calc.js';
import { commitPlan, saveAV, saveLastSlot, saveRating, saveSavedAgenda } from './persistence.js';
import { _reRenderIntereses, showAgView, switchMainNav, updateAgTab } from './pipeline.js';
import { dayFullyPassed, festivalEnded, parseDur, toMin } from '../domain/time.js';
import { screeningPassed, effectiveDuration, blockDuration } from '../domain/film.js';
import { sameEntry, isScreeningBlocked, screensConflictReason, plannableScreens } from '../domain/schedule.js';
// ── Velo del sheet: SIN driver JS (29 jul 2026 — DESIGN.md §8.4.1) ───────────
// Vivía acá un driver rAF que pisaba radio+opacidad por frame. Medido en device
// con el video de Juan (7 de 7 aperturas): progresaba hasta ~68%, se congelaba
// 233ms y saltaba a full en un frame. Causa: rAF corre en el hilo principal y
// ese hilo lo bloquea el propio sheet al construirse — la animación se moría de
// hambre a mitad de camino. Ahora el velo es CSS puro (escalera de dos capas
// animadas por opacity, index.html .pel-sheet-overlay): vive en el compositor,
// que un hilo principal bloqueado no puede detener.
import { state } from '../state/state.js';
import { storage } from '../storage/storage.js';
import { t, locSynopsis } from '../i18n/i18n.js';

// ── UI-state module-local + consts privados ──────────────────────────────────
const LB_SVG=`<svg class="block-shrink" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="13" height="13"><rect width="64" height="64" rx="9" fill="#2C3440"/><circle cx="21" cy="32" r="12" fill="#00B020" opacity=".9"/><circle cx="32" cy="32" r="12" fill="#3CBEDB" opacity=".85"/><circle cx="43" cy="32" r="12" fill="#FF8000" opacity=".9"/></svg>`;
let avAddOpen={};
let _avSheetType='hours';
let _avSheetDay=null;
const _GENRE_EN = {
  'Acción':'Action','Aventura':'Adventure','Comedia':'Comedy',
  'Drama':'Drama','Documental':'Documentary','Experimental':'Experimental',
  'Romance':'Romance','Sátira':'Satire','Terror':'Horror','Thriller':'Thriller',
  'Animación':'Animation','Ciencia Ficción':'Science Fiction',
  'Fantasía':'Fantasy','Misterio':'Mystery','Musical':'Musical',
  // Nombres canónicos TMDB es-ES (también usados por festivales legacy)
  'Ciencia ficción':'Science Fiction','Música':'Music','Crimen':'Crime',
  'Historia':'History','Suspense':'Thriller','Bélica':'War','Familia':'Family',
  'Película de TV':'TV Movie','Western':'Western',
};
let _toastActionFn=null;
let _pvTitle='', _pvRating=0;
// Cola post-vista de un PROGRAMA: se califica OBRA POR OBRA (paso a paso). La Vista
// queda marcada al programa entero (una función, una asistencia); las estrellas van a
// cada película del film_list — una estrella "de paquete" no dice nada (caso real:
// Fútbol Poético = corto de 8 min + largo de 73). null = film suelto (flujo de siempre).
let _pvQueue=null, _pvQueueIdx=0, _pvRatedCount=0, _pvSection='';
let _conflictPending=null;
let _ratingTitle='';
let _currentRating=0;
const _COUNTRY_FLAGS={
  'Alemania':'🇩🇪','Argentina':'🇦🇷','Austria':'🇦🇹','Bolivia':'🇧🇴',
  'Brasil':'🇧🇷','Bélgica':'🇧🇪','Canadá':'🇨🇦','Chile':'🇨🇱',
  'Colombia':'🇨🇴','Cuba':'🇨🇺','EEUU':'🇺🇸','Estados Unidos':'🇺🇸',
  'Ecuador':'🇪🇨','Eslovaquia':'🇸🇰','España':'🇪🇸','Estonia':'🇪🇪',
  'Filipinas':'🇵🇭','Francia':'🇫🇷','Grecia':'🇬🇷','Inglaterra':'🇬🇧','Irán':'🇮🇷',
  'Italia':'🇮🇹','Kenia':'🇰🇪','México':'🇲🇽','Nicaragua':'🇳🇮','Palestina':'🇵🇸',
  'Perú':'🇵🇪','Portugal':'🇵🇹','Reino Unido':'🇬🇧','Rep. Dominicana':'🇩🇴','Rusia':'🇷🇺',
  'Suiza':'🇨🇭','Taiwán':'🇹🇼','Turquía':'🇹🇷','UK':'🇬🇧',
  'Venezuela':'🇻🇪','Vietnam':'🇻🇳',
  'United States':'🇺🇸','USA':'🇺🇸','US':'🇺🇸',
  'United Kingdom':'🇬🇧','England':'🇬🇧','Scotland':'🇬🇧','Ireland':'🇮🇪',
  'France':'🇫🇷','Germany':'🇩🇪','Italy':'🇮🇹','Spain':'🇪🇸',
  'Portugal':'🇵🇹','Belgium':'🇧🇪','Switzerland':'🇨🇭','Austria':'🇦🇹',
  'Netherlands':'🇳🇱','Sweden':'🇸🇪','Denmark':'🇩🇰','Norway':'🇳🇴',
  'Finland':'🇫🇮','Poland':'🇵🇱','Czech Republic':'🇨🇿','Hungary':'🇭🇺',
  'Romania':'🇷🇴','Greece':'🇬🇷','Turkey':'🇹🇷','Russia':'🇷🇺',
  'Ukraine':'🇺🇦','Israel':'🇮🇱','Palestine':'🇵🇸','Lebanon':'🇱🇧',
  'Iran':'🇮🇷','Iraq':'🇮🇶','Saudi Arabia':'🇸🇦','Egypt':'🇪🇬',
  'Morocco':'🇲🇦','Tunisia':'🇹🇳','Algeria':'🇩🇿','South Africa':'🇿🇦',
  'Nigeria':'🇳🇬','Kenya':'🇰🇪','Ethiopia':'🇪🇹','Ghana':'🇬🇭',
  'Senegal':'🇸🇳','Mali':'🇲🇱','Cameroon':'🇨🇲','Rwanda':'🇷🇼',
  'Democratic Republic of Congo':'🇨🇩','Congo':'🇨🇬','Ivory Coast':'🇨🇮',
  'India':'🇮🇳','Pakistan':'🇵🇰','Bangladesh':'🇧🇩','Nepal':'🇳🇵',
  'Sri Lanka':'🇱🇰','Afghanistan':'🇦🇫','Iran':'🇮🇷',
  'China':'🇨🇳','Japan':'🇯🇵','South Korea':'🇰🇷','Taiwan':'🇹🇼',
  'Thailand':'🇹🇭','Vietnam':'🇻🇳','Indonesia':'🇮🇩','Philippines':'🇵🇭',
  'Malaysia':'🇲🇾','Singapore':'🇸🇬','Myanmar':'🇲🇲',
  'Australia':'🇦🇺','New Zealand':'🇳🇿','Canada':'🇨🇦','Mexico':'🇲🇽',
  'Brazil':'🇧🇷','Argentina':'🇦🇷','Chile':'🇨🇱','Colombia':'🇨🇴',
  'Peru':'🇵🇪','Venezuela':'🇻🇪','Cuba':'🇨🇺','Haiti':'🇭🇹',
  'Dominican Republic':'🇩🇴','Puerto Rico':'🇵🇷',
  'North Macedonia':'🇲🇰','Macedonia':'🇲🇰','Serbia':'🇷🇸','Croatia':'🇭🇷',
  'Bosnia':'🇧🇦','Slovenia':'🇸🇮','Albania':'🇦🇱','Kosovo':'🇽🇰',
  'Bulgaria':'🇧🇬','Slovakia':'🇸🇰','Estonia':'🇪🇪','Latvia':'🇱🇻','Lithuania':'🇱🇹',
  'Georgia':'🇬🇪','Armenia':'🇦🇲','Azerbaijan':'🇦🇿','Kazakhstan':'🇰🇿',
  'Mongolia':'🇲🇳','Malta':'🇲🇹','Cyprus':'🇨🇾','Iceland':'🇮🇸',
  'Luxembourg':'🇱🇺','Liechtenstein':'🇱🇮','Monaco':'🇲🇨',
  'Jamaica':'🇯🇲','Trinidad and Tobago':'🇹🇹','Barbados':'🇧🇧',
  'Ecuador':'🇪🇨','Bolivia':'🇧🇴','Paraguay':'🇵🇾','Uruguay':'🇺🇾',
  'Honduras':'🇭🇳','Guatemala':'🇬🇹','El Salvador':'🇸🇻','Nicaragua':'🇳🇮',
  'Costa Rica':'🇨🇷','Panama':'🇵🇦',
  // Huecos cazados por la auditoría del 29 jul 2026: el mapa tenía los nombres
  // en inglés de estos países pero NO los castellanos, que es lo que traen los
  // JSON de festivales hispanohablantes. Cada uno era un globo en pantalla.
  'Polonia':'🇵🇱','Japón':'🇯🇵','Dinamarca':'🇩🇰','Suecia':'🇸🇪',
  'Noruega':'🇳🇴','Países Bajos':'🇳🇱','Corea del Sur':'🇰🇷','Hungría':'🇭🇺',
  'Letonia':'🇱🇻','República Checa':'🇨🇿','Rumania':'🇷🇴','Croacia':'🇭🇷',
  'Eslovenia':'🇸🇮','Luxemburgo':'🇱🇺','Islandia':'🇮🇸','Camerún':'🇨🇲',
  'Malí':'🇲🇱','Panamá':'🇵🇦','Haití':'🇭🇹','Qatar':'🇶🇦','Malasia':'🇲🇾',
  'Tailandia':'🇹🇭','Afganistán':'🇦🇫','Kazajistán':'🇰🇿','Kirguistán':'🇰🇬',
  'Marruecos':'🇲🇦','Mozambique':'🇲🇿','Sudáfrica':'🇿🇦','Somalia':'🇸🇴',
  'Vanuatu':'🇻🇺','Türkiye':'🇹🇷','Guinea-Bissau':'🇬🇼','Líbano':'🇱🇧',
  'Nueva Zelanda':'🇳🇿','Bulgaria':'🇧🇬','Serbia':'🇷🇸','Senegal':'🇸🇳',
  'Indonesia':'🇮🇩','Nigeria':'🇳🇬','Palestina':'🇵🇸','Suiza':'🇨🇭'
};
let _cortoParentHtml=null;

// _screeningRows — DUEÑO ÚNICO de la fila de función (día · hora · sede [· Añadir]),
// para la ficha de película/programa y la de corto: es la MISMA cosa en ambas, y
// tenerla duplicada FUE el bug (la ficha de corto no la pintaba nunca).
// `pairs` = [{s, owner}] — `owner` es el film que manda sobre el Plan. Para un corto
// es su PROGRAMA: agregar un corto agrega el programa completo (regla establecida) y
// addSuggestion solo entiende títulos que existen en FILMS.
// El distintivo de un pase de prensa en la fila es el MISMO icono del
// interruptor que el usuario acaba de pulsar para verlo — vocabulario ya
// aprendido, cero palabras (decisión de Juan, 24 ago: «no quiero tanto
// texto»). Inline y sin flex-shrink:0, para no repetir la cicatriz del badge
// «En tu Plan» que le robaba ancho a la sede. El texto queda en sr-only.
const _PRESS_ICO=`<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M4 22V4a1 1 0 011-1h11a1 1 0 011 1v18"/><path d="M17 8h2a1 1 0 011 1v10a2 2 0 01-2 2H4"/><line x1="7" y1="7" x2="14" y2="7"/><line x1="7" y1="11" x2="14" y2="11"/><line x1="7" y1="15" x2="11" y2="15"/></svg>`;

function _screeningRows(pairs, opts){
  return pairs.map(({s,owner})=>{
    const dayAbb=dayLabel(s.day)||s.day;
    const vc=vcfg(s.venue),sl=sala(s.venue);
    const _festCity=(FESTIVAL_CONFIG[_activeFestId]||{}).city||'';
    // sinCiudad: la ficha ya filtró por ciudad y la nombra arriba — acá sobra.
    const _city=(opts&&opts.sinCiudad)?'':(_festCity&&vc.city&&vc.city!==_festCity?vc.city:'');
    const isPast=screeningPassed(s)&&!festivalEnded();
    // Mitad B (pin-funcion): control "Añadir esta función al Plan" por fila.
    // Recurrentes: sin control (informativo). Si esta función ya está en el
    // Plan → indicador "En tu Plan"; si no, y la función no pasó ni terminó el
    // festival → botón "Añadir" (reusa addSuggestion, que decide add vs swap).
    // "En tu plan": la fila se marca con una BARRA de acento ámbar a la izquierda
    // (.pel-sheet-screening.in-plan), no con un badge ni un check. Decisión de Juan
    // (20 jul 2026): el badge "✓ En tu Plan" era flex-shrink:0 y le robaba ancho al
    // venue → "Cinemateca de Bogotá · Sala 2" se partía en dos líneas. La barra vive
    // en el margen (::before absoluto, costo CERO de ancho) → el venue recupera TODO
    // el ancho y lee en una línea hasta 360px. El botón "Añadir" (acción) sí se queda
    // a la derecha. La etiqueta "en tu plan" queda para lectores de pantalla (.sr-only).
    let _addCtrl='', _planned=false;
    // Una función cancelada NO se puede sumar al Plan: dejarle el botón permitía
    // planificar algo que no va a ocurrir (lo tenía, era un bug funcional).
    // El estado «en tu plan» se calcula SIEMPRE — antes vivía dentro del if de
    // abajo, así que en un taller multi-día NUNCA se calculaba y sus filas no se
    // marcaban aunque el bloque estuviera en el plan.
    // No hace falta una rama especial para el bloque: como entra entero (o no
    // entra), la comparación exacta marca sus N filas igual.
    _planned=savedAgenda&&savedAgenda.schedule.some(e=>sameEntry(e,{title:owner.title,day:s.day,time:s.time,venue:s.venue}));
    // El botón POR SESIÓN, en cambio, no existe para un recurrente: su control
    // vive abajo, a nivel de bloque (ver _bloqueCtrl).
    if(!owner.is_recurring&&!s._cancelled){
      if(!_planned&&!festivalEnded()&&!screeningPassed(s)){
        _addCtrl=`<button class="suggestion-add" data-action="addSuggestion" data-title="${owner.title.replace(/"/g,'&quot;')}" data-day="${s.day}" data-time="${s.time}" data-stop="1">${ICONS.plus} ${t('plan_agendar')}</button>`;
      }
    }
    return`<div class="pel-sheet-screening${_planned?' in-plan':''}${s._cancelled?' scr-void':''}"${isPast?' style="opacity:.4"':''}>
      ${_planned?`<span class="sr-only">${t('plan_en_tu_plan')}</span>`:''}
      <span class="pelicula-day" data-day="${s.day}">${dayAbb}</span>
      <span class="pelicula-time">${s.time}</span>
      <span class="pelicula-venue" data-venue="${s.venue.replace(/"/g,'&quot;')}" data-action="openVenueSheet">${ICONS.pin} <span class="venue-text">${vc.short}${sl?' · '+sl:''}${_city?`<span class="venue-municipio">${_city}</span>`:''}</span>${s.audience==='press'?`<span class="scr-press" aria-hidden="true">${_PRESS_ICO}</span><span class="sr-only">${t('press_badge')}</span>`:''}</span>
      ${_addCtrl}
    </div>`;
  }).join('');
}

// _cortoScreeningPairs — las funciones que hereda un corto de sus programas, ya
// ordenadas futuro→pasado igual que en la ficha de película (mismo criterio, no una
// segunda regla de orden). Un bloque-catálogo sin sesión asignada no aporta ninguna.
function _cortoScreeningPairs(cortoTitle){
  const pairs=[];
  _findParentPrograms(cortoTitle).forEach(prog=>{
    FILMS.filter(g=>g.title===prog.title&&g.day&&g.time&&g.venue)
      .forEach(s=>pairs.push({s,owner:prog}));
  });
  const fut=pairs.filter(p=>!screeningPassed(p.s))
    .sort((a,b)=>a.s.day_order-b.s.day_order||toMin(a.s.time)-toMin(b.s.time));
  const past=pairs.filter(p=>screeningPassed(p.s));
  return [...fut,...past];
}

export function openPelSheet(title){
  // Decodificar entidades HTML que el inline onclick puede pasar (&#39; → ')
  const _d=document.createElement('textarea');
  _d.innerHTML=title;
  title=_d.value;
  const entry=Object.values((()=>{
    const m={};
    FILMS.forEach(f=>{if(!m[f.title])m[f.title]={film:f,screenings:[]};m[f.title].screenings.push(f);});
    return m;
  })()).find(e=>e.film.title===title);
  if(!entry) return;
  const{film:f,screenings}=entry;
  const inWL=watchlist.has(f.title),inW=watched.has(f.title),inPrio=prioritized.has(f.title);
  const posterSrc=getFilmPoster(f);
  let posterHtml;
  // LA FICHA PREGUNTA AL MISMO DUEÑO que la grilla y la lista (26 ago 2026). Era
  // el CUARTO sitio con el gate viejo en `is_programa`: un compuesto de cortos
  // —207 de los 215 del catálogo— caía al generativo, que trae banda de sección
  // y duración justo al lado del encabezado, que ya las dice. Se leía doble.
  // La jerarquía la resuelve programParts: si el festival mandó afiche, no entra.
  //
  // MUDA: el `dato` se vacía. La regla anti-repetición de la ficha ya existía
  // para el generativo («el título vive en la cabecera») y vale igual acá: el
  // encabezado dice sección, duración y título, así que el póster no los repite.
  const _escF=programParts(f);
  if(_escF){
    posterHtml=`<div class="psp-escalera">${makeSharedSlotSVG({modules:_escF.modules, secLabel:_escF.secLabel, accent:_escF.accent, dato:''})}</div>`;
  } else if(f.is_programa&&f.film_list&&f.film_list.length>=2){
    const _sp1=_getItemPoster(f.film_list[0]);
    const _sp2=_getItemPoster(f.film_list[1]);
    const _fd1=JSON.stringify(f.film_list[0]).replace(/"/g,'&quot;');
    const _fd2=JSON.stringify(f.film_list[1]).replace(/"/g,'&quot;');
    const _c1=_sp1
      ?`<img class="psp-card psp-front" src="${_sp1}" loading="lazy" onerror="this.remove()" alt="" data-action="openCombinedFilmSheet" data-film="${_fd1}">`
      :`<img class="psp-card psp-front" src="${makeProgramPoster(state,f.film_list[0].title,f.film_list[0].duration||'',f.section||'')}" loading="lazy" alt="" data-action="openCombinedFilmSheet" data-film="${_fd1}">`;
    const _c2=_sp2
      ?`<img class="psp-card psp-back" src="${_sp2}" loading="lazy" onerror="this.remove()" alt="" data-action="openCombinedFilmSheet" data-film="${_fd2}">`
      :`<img class="psp-card psp-back" src="${makeProgramPoster(state,f.film_list[1].title,f.film_list[1].duration||'',f.section||'')}" loading="lazy" alt="" data-action="openCombinedFilmSheet" data-film="${_fd2}">`;
    posterHtml=`<div class="pel-sheet-poster-stage">${_c1}${_c2}</div>`;
  } else {
    const _ppF=posterParts(f,{header:true}); // decisión única (posterModel)
    if(_ppF.ed){
      posterHtml=`<div class="psp-editorial poster-ed" style="--ed-accent:${_ppF.accent}">${_ppF.inner}</div>`;
    } else {
      // Regla anti-repetición del sheet: el título vive en la cabecera → el
      // generativo se re-genera SIN cuerpo (banda/num intactos). Originales
      // pasan tal cual (getFilmPosterUntitled solo toca data-URIs generativos).
      const _sheetSrc=posterSrc?getFilmPosterUntitled(f):null;
      posterHtml=_sheetSrc
        ?`<img class="pel-sheet-poster"${_posterStyle(f)} src="${_sheetSrc}" data-title="${f.title.replace(/"/g,'&quot;')}" loading="lazy" onerror="_posterErr(this)" alt="">`
        :`<div class="pel-sheet-poster-ph" aria-hidden="true">🎬</div>`;
    }
  }
  const{displayTitle}=parseProgramTitle(f.title);
  const secLabel=_secLabel(f.section);
  // ANCLAJE: ¿esta obra comparte función con otra? (`_slotKey` lo marca el
  // loader en los festivales que declaran `sharedSlotIsOneScreening`).
  const _anclada=screenings.some(s=>s._slotKey&&FILMS.some(o=>o._slotKey===s._slotKey&&o.title!==f.title));
  // cuántas COMPAÑERAS tiene: títulos distintos que comparten su slot.
  const totalFn=FILMS.filter(fi=>fi.title===f.title).length;
  const unica=totalFn===1;
  const DAY_ABB=['MAR','MIÉ','JUE','VIE','SÁB','DOM'];
  // Solo funciones AGENDADAS (con día/hora/sede) generan fila de screening. Un
  // bloque-catálogo de cortos sin sesión asignada (is_cortos+unscheduled) no tiene
  // función → 0 filas (abajo se muestra su lista de cortos). Los films normales
  // siempre traen día/hora/sede (validateFilm lo exige) → no se filtran.
  const scheduled=screenings.filter(s=>s.day&&s.time&&s.venue);
  const future=scheduled.filter(s=>!screeningPassed(s)).sort((a,b)=>a.day_order-b.day_order||toMin(a.time)-toMin(b.time));
  const past=scheduled.filter(s=>screeningPassed(s));
  // ── La ficha HEREDA el contexto de ciudad (7 ago 2026) ────────────────────
  // Con Medellín elegido, «One in a million» mostraba sus 2 funciones y un aviso
  // de boletería que era de Bogotá: información sobre una ciudad a la que no vas,
  // y encima engañosa —en Medellín esa función es gratis—.
  // Doctrina (#504): la ciudad filtra lo que DESCUBRÍS, nunca lo que YA ELEGISTE.
  // Por eso una función que está en tu plan se muestra SIEMPRE, aunque sea de otra
  // ciudad: sin esa excepción la app te ofrecería «Agregar» algo que ya tenés.
  const _ciudadSel=isCitySel(activeVenue)?activeVenue.slice(5):'';
  const _yaElegida=sc=>savedAgenda&&savedAgenda.schedule.some(e=>sameEntry(e,{title:f.title,day:sc.day,time:sc.time,venue:sc.venue}));
  const _todas=[...future,...past];
  const allScr=_ciudadSel?_todas.filter(sc=>venueMatches(sc.venue,activeVenue)||_yaElegida(sc)):_todas;
  // Cuántas compañeras anuncia el aviso: se cuenta sobre allScr —las funciones
  // que la ficha MUESTRA (futuras, de tu ciudad)—, no sobre el histórico, y solo
  // se afirma si TODAS coinciden. «Madres de nacimiento» tiene 10 funciones con
  // 4, 5, 6 y hasta 0 compañeras: la unión da 11 y ninguna función tiene 11 —
  // decirlo sería la misma afirmación falsa que venimos borrando (medido el
  // 16 ago). Con cuentas distintas → 0 → el aviso da el vínculo sin número.
  const _ancladaN=()=>{
    const _cuentas=new Set();
    allScr.forEach(sc=>{
      if(!sc._slotKey) return;
      _cuentas.add(new Set(FILMS.filter(o=>o._slotKey===sc._slotKey&&o.title!==f.title).map(o=>o.title)).size);
    });
    _cuentas.delete(0);              // una función suelta no define el vínculo
    return _cuentas.size===1?[..._cuentas][0]:0;
  };
  const _ocultas=_todas.length-allScr.length;
  // La ciudad se dice UNA vez, en el banner de Funciones (Juan, 7 ago): repetirla
  // bajo cada sede cuando ya filtraste por ella es decir dos veces lo mismo.
  const rows=_screeningRows(allScr.map(s=>({s,owner:f})), {sinCiudad:!!_ciudadSel});
  // ── TALLER MULTI-DÍA (is_recurring): el control es del BLOQUE ─────────────
  // Un taller de varios días se toma entero: quien se inscribe va a todas las
  // sesiones. Por eso las filas quedan informativas (sin botón propio, ver
  // _screeningRows) y debajo aparece UN control que mete o saca las N de una.
  // Misma semántica que el corto, donde añadir un corto añade su programa.
  // Hasta ahora is_recurring solo APAGABA el botón por sesión y no ponía nada en
  // su lugar: el único camino al Plan era Intereses + planificador.
  let _bloqueCtrl='';
  if(f.is_recurring&&!festivalEnded()){
    const _enPlan=savedAgenda&&savedAgenda.schedule.filter(e=>e._title===f.title).length;
    // Todas las sesiones del taller, no solo las futuras: el bloque se toma ENTERO.
    const _todasSes=allScr.filter(sc=>!sc._cancelled);
    const _empezado=_todasSes.some(sc=>screeningPassed(sc));
    // El botón dice lo MISMO que una función suelta («Agregar»/«Quitar»): el texto
    // largo compensaba una agrupación que no se veía, y ahora el corchete la muestra
    // (Juan, 9 ago 2026). La cuenta viaja en el aria-label — quien no ve el corchete
    // sigue oyendo «Añadir las 2 sesiones». Cero strings nuevas: las cuatro existían.
    if(_enPlan)
      _bloqueCtrl=`<button class="suggestion-add blk-quitar" data-action="removeRecurringBlock" data-title="${f.title.replace(/"/g,'&quot;')}" data-stop="1" aria-label="${t(_enPlan===1?'bloque_quitar_1':'bloque_quitar',{n:_enPlan})}">${ICONS.x} ${t('misc_sacar')}</button>`;
    // Un taller que YA EMPEZÓ no se puede tomar entero, así que no se ofrece.
    // Sin esto se ofrecían «las sesiones que quedan», y eso rompía dos cosas: el
    // texto («Añadir las 1 sesiones», cazado con los talleres de FICMA) y el
    // invariante — verifyPlan cuenta TODAS las del catálogo, así que un plan con
    // 1 de 2 quedaba marcado como bloque-incompleto por el propio chokepoint.
    else if(_todasSes.length&&!_empezado)
      _bloqueCtrl=`<button class="suggestion-add blk-add" data-action="addRecurringBlock" data-title="${f.title.replace(/"/g,'&quot;')}" data-stop="1" aria-label="${t(_todasSes.length===1?'bloque_anadir_1':'bloque_anadir',{n:_todasSes.length})}">${ICONS.plus} ${t('plan_agendar')}</button>`;
  }
  // ── El GRUPO: corchete + eslabón + un solo control ────────────────────────
  // Las sesiones van unidas por un corchete recto con eslabón, y el control queda
  // a su derecha EN LÍNEA — la misma píldora de cualquier función suelta. Antes era
  // un botón a lo ancho DEBAJO: no se parecía a nada más en la app y obligaba a
  // explicar la agrupación con palabras. El corchete va del lado del BOTÓN (Juan,
  // 9 ago): a la izquierda corría las filas ~24px y rompía la columna que comparten
  // TODAS las filas de la app. Con una sola sesión no hay nada que unir.
  const _esGrupo=f.is_recurring&&allScr.length>1;
  const _cuerpoFn=f.is_recurring
    ?`<div class="blq${_esGrupo?' blq-multi':''}">
        <div class="blq-filas">${rows}</div>
        ${_esGrupo?`<div class="blq-corchete" aria-hidden="true"><span class="blq-c-seg"></span><span class="blq-link">${ICONS.link}</span><span class="blq-c-seg"></span></div>`:''}
        ${_bloqueCtrl?`<div class="blq-cta">${_bloqueCtrl}</div>`:''}
      </div>`
    :rows;
  // Lista de cortos si es programa
  let cortosHtml='';
  // Antes exigía is_cortos, y los programas legacy daban acceso a sus obras por
  // los afiches TOCABLES del stack. Al pasar esos a la Escalera —una sola
  // imagen— ese acceso desaparecía: la lista lo repone para todo compuesto.
  if(f.film_list?.length>=2){
    const cortoItems=f.film_list.map((item,n)=>{
      const r=filmRatings[item.title]||0;
      const ratingEl=r
        ?`<span class="corto-rating-stars">${starsText(r)}</span>`
:`<button class="corto-rate-btn" data-title="${escXML(item.title||'')}" data-action="closePelAndRate" data-stop="1">★</button>`;
      return _mkCortoItemHtml(item,n,{
        cls:'pel-sheet-corto-item',
        section:f.section||'',
        ratingEl
      });
    }).join('');
    cortosHtml=`      <div class="sec-hdr sm">${ICONS.film} <span>${t('label_programa')}</span> <span class="count-badge cb-neutral">${f.film_list.length}</span></div>
      <div class="pel-sheet-cortos-wrap">${cortoItems}</div>`;
  }
  const wlLabel=inWL?`${ICONS.heartFill} ${t('cta_en_intereses')}`:`${ICONS.heart} ${t('nav_intereses')}`;

  const _inPlan=savedAgenda&&savedAgenda.schedule.some(s=>s._title===f.title);
  const _planEntry=_inPlan?savedAgenda.schedule.find(s=>s._title===f.title):null;
  const _ps=document.getElementById('pel-sheet');
  if(_ps) _ps.scrollTop=0;
  _pushSheetState();
  // Metadata consolidada: director · género · año
  const _yr=f.year?String(f.year):'';const _gnYr=f.genre?_genreEN(f.genre)+(_yr?' · '+_yr:''):_yr;
  const _metaLine=[f.director||'',_gnYr].filter(Boolean).join(' · ');

  document.getElementById('pel-sheet-inner').innerHTML=`
    <div class="pel-sheet-header">
      ${posterHtml}
      <div class="pel-sheet-meta">
        <div class="pel-sheet-title">${(()=>{const _dt=filmDisplayTitle(f);return _dt.original?`${_dt.main}<div class="pel-sheet-original">${_dt.original}</div>`:_dt.main;})()}</div>
        ${f.type!=='event'
          ?`<div class="pel-sheet-flags-dur">${flagFmt(f.flags)||''}${f.duration?` · ${durFmt(f.duration)}`:''}</div>`
          :(f.duration?`<div class="pel-sheet-flags-dur">${durFmt(f.duration)}</div>`:'')}
        ${f.type!=='event'&&_metaLine?`<div class="pel-sheet-metaline">${_metaLine}</div>`:''}
        ${f.section?`<div class="pel-sheet-sec" data-section="${f.section.replace(/"/g,'&quot;')}" data-action="filterBySection">${secLabel} <span class="pel-sheet-sec-arrow">›</span></div>`:''}
        ${(!f.is_cortos&&!f.is_programa&&f.type!=='event')?lbLink(f.title,f):''}
      </div>
    </div>
        ${allScr.length>0?`<div class="sec-hdr sm">${ICONS.clock} <span>${f.type==='event'?t('label_horario'):allScr.length===1?t('label_funcion'):t('label_funciones_pl')}</span>${totalFn>1&&f.type!=='event'?`<span class="count-badge cb-neutral">${allScr.length}</span>`:''}${_ciudadSel?`<span class="fn-ciudad">${_ciudadSel}</span>`:''}</div>`:''}
    ${allScr.length>0?`<div class="pel-sheet-screenings">${_cuerpoFn}${_ocultas>0?`<div class="fn-otra-ciudad">${t(_ocultas===1?'fn_otra_ciudad':'fn_otras_ciudades',{n:_ocultas})}</div>`:''}</div>`:''}
    ${/* ORDEN: FUNCIÓN (solo día·hora·sede) → AVISOS → SINOPSIS. Todos los avisos
        viven en su banda, incluidos cancelada y reprogramada, que van PRIMERAS y
        en rojo: lo que invalida se lee antes de lo que matiza (DESIGN 8.4.6). La
        fila afectada lleva su propia marca (hora tachada / atenuada) — el aviso
        explica, la fila señala; ninguna de las dos hace el trabajo sola. */''}
    ${_avisosBand(f, {prog:_anclada?'obras':null, progN:_ancladaN(), scrs:allScr})}
    ${(()=>{
      const _tk=FESTIVAL_CONFIG[_activeFestId]||{};
      // ticket_url por FILM pisa al global (Tercer Tiempo 2026: cada sesión tiene
      // su checkout directo de tuboleta en el PDF oficial). Fallback: el del festival.
      const _turl=(f.ticket_url&&/^https:\/\//.test(f.ticket_url))?f.ticket_url:_tk.ticket_url;
      if(!_turl||festivalEnded()) return '';
      if(_tk.ticketing_model==='paid')
        return `<a class="pel-sheet-ticket-link" href="${_turl}" target="_blank" rel="noopener">${ICONS.ticket} ${t('ticket_comprar_paid')}</a>`;
      if(_tk.ticketing_model==='mixed'){
        // Festival mixto: ocultar solo si TODAS las funciones del film son gratuitas.
        const _allFree=screenings.length>0&&screenings.every(s=>s.is_free===true);
        if(_allFree) return '';
        // Con link directo por film, CTA directo (sin banner genérico de mixto).
        if(f.ticket_url&&_turl===f.ticket_url)
          return `<a class="pel-sheet-ticket-link" href="${_turl}" target="_blank" rel="noopener">${ICONS.ticket} ${t('ticket_comprar_paid')}</a>`;
        return `<div class="meta-banner"><div class="meta-banner-dot"></div><div><div class="meta-banner-text">${t('ticket_mixed_body')}</div><a class="pel-sheet-ticket-link" href="${_turl}" target="_blank" rel="noopener">${ICONS.ticket} ${t('ticket_mixed_link')}</a></div></div>`;
      }
      return '';
    })()}
    ${(()=>{
      // INSCRIPCIÓN — mismo patrón que el enlace de compra, tres decisiones heredadas:
      // por FUNCIÓN (no del festival: el formulario de la Master Class de FICDEH se
      // titula con el nombre de ESA actividad), validado https:// antes de pintarlo,
      // y oculto cuando el festival terminó.
      // NO se reusó ticket_url a propósito: «ticket es solo para comprar» (Juan). Un
      // formulario gratuito ahí haría que la ficha dijera «Comprá tu entrada» en una
      // actividad de entrada libre — lo contrario de lo que arregló el badge de precio.
      const _rurl=(f.registration_url&&/^https:\/\//.test(f.registration_url))?f.registration_url:'';
      if(!_rurl||festivalEnded()) return '';
      return `<a class="pel-sheet-ticket-link" href="${_rurl}" target="_blank" rel="noopener">${ICONS.clipboardList} ${t('inscripcion_link')}</a>`;
    })()}
    ${f.synopsis?`    <div class="sec-hdr sm">${ICONS.text} <span>${f.type==='event'?t('label_descripcion'):t('label_sinopsis')}</span></div>
    <div class="pel-sheet-synopsis">${locSynopsis(f).replace(/^⚠️\s*INGLÉS\s*[—-]\s*/,'')}</div>`:''}
    ${cortosHtml}
        <div class="pel-sheet-foot">
        ${inW?`<div class="pel-sheet-ctas-watched">
        <button data-title="${escXML(f.title)}" data-action="toggleWatchedAndClose" class="pel-sheet-action-btn act-on">${ICONS.eye} ${t('cta_vista')}</button>
        ${!f.is_cortos?`<button data-title="${escXML(f.title)}" data-action="closePelAndRate" class="pel-sheet-action-btn btn-secondary">${ICONS.star} ${filmRatings[f.title]?t('misc_cambiar'):t('cta_calificar')}</button>`:``}
      </div>`
    :`<div class="pel-sheet-ctas">
        <button id="pel-wl-btn" class="row-center-xs pel-sheet-action-btn${inWL?' act-on btn-primary':' btn-primary'}" data-title="${escXML(f.title)}" data-action="togglePelWL">${inWL?ICONS.heartFill:ICONS.heart} ${inWL?t('cta_en_intereses'):t('cta_intereses')}</button>
        <button id="pel-prio-btn" class="row-center-xs pel-sheet-action-btn${inPrio?' act-prio':' btn-secondary'}" data-title="${escXML(f.title)}" data-action="togglePelPrio">${inPrio?ICONS.bookmarkFill:ICONS.bookmark} ${inPrio?t('cta_priorizada'):t('cta_priorizar')}</button>
        <button id="pel-vista-btn" class="row-center-xs pel-sheet-action-btn btn-secondary" data-title="${escXML(f.title)}" data-action="toggleWatched">${ICONS.eye} ${t('cta_vista')}</button>
      </div>`}
    ${_inPlan&&activeView==='agenda'?`<button data-title="${escXML(f.title)}" data-action="closePelAndRemove" class="pel-sheet-remove-plan">${ICONS.x} ${t('plan_quitar_plan')}</button>`:''}
        </div>
  `;
  document.getElementById('pel-overlay').classList.add('open');
  _ps.classList.add('open');
  _ps.classList.toggle('compact', totalFn>=3);
  _applyAmbient(_ps, getFilmPoster(f), _sectionColor(f.section||''));
  _pspAttach();
}

// Color ambiental de la ficha: limpia el tinte anterior y aplica el del póster
// actual vía posterAmbient (único sampler). El token en dataset evita que un
// muestreo lento pinte una ficha que ya cambió (abrir A→cerrar→abrir B rápido).
function _applyAmbient(ps, src, fbHex){
  if(!ps) return;
  ps.classList.remove('amb'); ps.style.removeProperty('--amb');
  const _tok = ps.dataset.ambFor = src || fbHex || '';
  if(!_tok) return;
  posterAmbient(src, fbHex, rgb => {
    if(rgb && ps.dataset.ambFor === _tok && ps.classList.contains('open')){
      ps.style.setProperty('--amb', rgb.join(','));
      ps.classList.add('amb');
    }
  });
}

// Prewarm del ambiental: al pointerdown sobre una card ya arranca el muestreo
// (~5KB w92), unos 150–300ms antes de que el click abra la ficha — cuando el
// sheet aparece, el color suele estar en cache y el bloom entra sin espera.
document.addEventListener('pointerdown', (e) => {
  const _card = e.target && e.target.closest ? e.target.closest('.poster-card[data-title]') : null;
  if(!_card) return;
  const _f = (typeof FILMS !== 'undefined' ? FILMS : []).find(x => x.title === _card.dataset.title);
  if(_f) posterAmbient(getFilmPoster(_f), _sectionColor(_f.section || ''), () => {});
}, { passive: true });

export function closePelSheet(){
  // Si hay contenido padre guardado, volvemos al programa en lugar de cerrar
  if(_cortoParentHtml){
    const inner=document.getElementById('pel-sheet-inner');
    if(inner){
      inner.innerHTML=_cortoParentHtml;
      _cortoParentHtml=null;
      const ps=document.getElementById('pel-sheet');
      if(ps) ps.scrollTop=0;
      _pspAttach();
      return;
    }
  }
  _cortoParentHtml=null;
  document.getElementById('pel-overlay').classList.remove('open');
  document.getElementById('pel-sheet').classList.remove('open');
}

export function _pspAttach(){
  const stage=document.getElementById('psp-stage');
  if(!stage||stage._pspReady) return;
  stage._pspReady=true;
  // Ambos posters abren su film — leen data-front en el momento del tap
  [0,1].forEach(i=>{
    const el=document.getElementById('psp-img-'+i);
    if(!el) return;
    el.addEventListener('click',function(e){
      e.stopPropagation();
      const front=parseInt(stage.dataset.front||'0');
      if(i!==front) return; // solo responde si es el frontal
      try{_openCombinedFilmSheet(JSON.parse(stage.dataset['film'+i]));}catch(err){console.warn('[psp] combined sheet parse failed',err);}
    });
  });
  // Swap zone — franja dedicada de 44px bajo el poster frontal
  const swapZone=document.getElementById('psp-swap-zone');
  if(swapZone) swapZone.addEventListener('click',function(e){
    e.stopPropagation();
    const cur=parseInt(stage.dataset.front||'0');
    _pspSwap(cur===0?1:0);
  });
}

export function _pspSwap(idx){
  const stage=document.getElementById('psp-stage');
  if(!stage) return;
  stage.dataset.front=idx;
  [0,1].forEach(i=>{
    const el=document.getElementById('psp-img-'+i);
    if(!el) return;
    el.classList.toggle('psp-front',i===idx);
    el.classList.toggle('psp-back',i!==idx);
  });
}

export function _pushSheetState(){
  try{history.pushState({sheet:true},'','');}catch(e){console.warn('[sheet] pushState failed',e);}
}

// ── Venue Sheet — se abre desde el nombre de venue en el pel-sheet ──────────
// Se superpone (z-index mayor); back/overlay vuelve al pel-sheet debajo.
export function openVenueSheet(venueName){
  if(!venueName) return;
  const _d=document.createElement('textarea');_d.innerHTML=venueName;venueName=_d.value;
  const v=vcfg(venueName)||{};
  const name=v.name||venueName;
  const _festCity=(FESTIVAL_CONFIG[_activeFestId]||{}).city||'';
  const _addr=[v.address||''];
  if(v.city&&v.city!==_festCity&&!(v.address||'').includes(v.city)) _addr.push(v.city);
  const addr=_addr.filter(Boolean).join(' · ');
  const hasGeo=v.lat!=null&&v.lng!=null;
  const fns=FILMS.filter(f=>f.venue===venueName)
    .sort((a,b)=>(a.day_order-b.day_order)||(toMin(a.time)-toMin(b.time)));
  const _fnRow=f=>{
    const _inPlan=savedAgenda&&savedAgenda.schedule.some(e=>sameEntry(e,f));
    return`<div class="venue-fn-row" data-action="openPelFromVenue" data-title="${f.title.replace(/"/g,'&quot;')}">
      <span class="venue-fn-time">${f.time}</span>
      <span class="venue-fn-title">${filmDisplayTitle(f).main}</span>
      ${_inPlan?`<span class="venue-fn-badge">${ICONS.check} ${t('plan_en_tu_plan')}</span>`:''}
    </div>`;
  };
  // Agrupado por día (discrimina días: misma hora en días distintos ya no se
  // confunde). Orden cronológico por day_order; encabezado de día por grupo.
  const _byDay=[];
  fns.forEach(f=>{ let g=_byDay.find(x=>x.day===f.day); if(!g){g={day:f.day,items:[]};_byDay.push(g);} g.items.push(f); });
  const rows=fns.length
    ? _byDay.map(g=>`<div class="venue-day-hdr">${dayLabel(g.day)||g.day}</div>${g.items.map(_fnRow).join('')}`).join('')
    : emptyState(ICONS.pin, t('venue_sin_funciones'));
  const inner=document.getElementById('venue-sheet-inner');
  if(!inner) return;
  inner.innerHTML=`
    <div class="venue-sheet-name">${name}</div>
    ${addr?`<div class="venue-sheet-addr">${addr}</div>`:''}
    ${hasGeo?`<div class="venue-sheet-map">${ICONS.pin}</div>
    <button class="venue-sheet-dir" data-action="venueDirections" data-lat="${v.lat}" data-lng="${v.lng}">${ICONS.pin} ${t('venue_directions')}</button>`:''}
        <div class="sec-hdr sm">${ICONS.clock} <span>${t('label_funciones')}</span></div>
    ${rows}`;
  const vs=document.getElementById('venue-sheet');
  if(vs) vs.scrollTop=0;
  _pushSheetState();
  document.getElementById('venue-overlay').classList.add('open');
  vs.classList.add('open');
}

export function closeVenueSheet(){
  document.getElementById('venue-overlay')?.classList.remove('open');
  document.getElementById('venue-sheet')?.classList.remove('open');
}

// ── DIARIO (17 jul) — lo visto como destino propio (patrón Letterboxd/Things).
// Se abre desde el chip "N vistas" del progreso de Mi Plan. El contenido lo arma
// renderDiaryHTML (misma card del recap de Modo Recuerdo). z 8901: bajo pel-sheet,
// así tocar una card abre la película ENCIMA del Diario.
import { renderPalmaresHTML, palmaresDe } from '../view/programa.js';

export function openPalmares(){
  // Espejo de openDiary: el sheet se llena al abrirlo, no al renderizar la banda.
  const body=document.getElementById('palm-body');
  if(body) body.innerHTML=renderPalmaresHTML(_activeFestId);
  const cfg=FESTIVAL_CONFIG[_activeFestId]||{};
  const titleEl=document.getElementById('palm-title');
  if(titleEl) titleEl.textContent=cfg.name||'';
  const artEl=document.getElementById('palm-keyart');
  if(artEl){
    if(cfg.keyArt){ artEl.src=cfg.keyArt; artEl.style.visibility=''; }
    else artEl.style.visibility='hidden';
  }
  const subEl=document.getElementById('palm-sub');
  if(subEl){
    const cats=palmaresDe(_activeFestId)||[];
    const gan=cats.reduce((n,c)=>n+c.ganadoras.length,0);
    subEl.textContent=t('palm_resumen').replace('{cats}',cats.length).replace('{n}',gan);
  }
  document.getElementById('palm-overlay')?.classList.add('open');
  document.getElementById('palm-sheet')?.classList.add('open');
}

export function closePalmares(){
  document.getElementById('palm-overlay')?.classList.remove('open');
  document.getElementById('palm-sheet')?.classList.remove('open');
}

export function openDiary(){
  const body=document.getElementById('diary-body');
  if(body) body.innerHTML=renderDiaryHTML(state);
  const cfg=FESTIVAL_CONFIG[_activeFestId]||{};
  const titleEl=document.getElementById('diary-title');
  if(titleEl) titleEl.textContent=cfg.name||'';
  // La TAPA (18 ago): el afiche del festival como objeto + sus fechas. El
  // keyArt es el mismo del splash — write-once en /assets/, ya cacheado.
  const artEl=document.getElementById('diary-keyart');
  if(artEl){
    if(cfg.keyArt){ artEl.src=cfg.keyArt; artEl.style.visibility=''; }
    else artEl.style.visibility='hidden';
  }
  // El nombre completo bajo la sigla (Juan, 18 ago) — vía festivalTagline, que
  // ya es el dueño de derivarlo SIN repetir la sigla ([no-repetir-nombre]).
  const fullEl=document.getElementById('diary-full');
  if(fullEl) fullEl.textContent=festivalTagline(cfg, _lang)||'';
  const datesEl=document.getElementById('diary-dates');
  if(datesEl) datesEl.textContent=[(_lang==='en'&&cfg.dates_en)?cfg.dates_en:cfg.dates,cfg.year].filter(Boolean).join(' ');
  const countEl=document.getElementById('diary-count');
  if(countEl){
    // La cuenta viaja como count-badge (canon: nunca en palabras) — misma
    // unidad que la banda que lo abre: OBRAS (cards del muro único).
    // «Lo que viste» NO cuenta las negadas: el muro las muestra apagadas
    // (para poder revertirlas) pero no son parte de la colección.
    const n=(body?body.querySelectorAll('.dw-poster:not(.dw-off)').length:0);
    countEl.textContent=n?String(n):'';
    countEl.style.display=n?'':'none';
  }
  _pushSheetState();
  document.getElementById('diary-overlay')?.classList.add('open');
  document.getElementById('diary-sheet')?.classList.add('open');
}

export function closeDiary(){
  document.getElementById('diary-overlay')?.classList.remove('open');
  document.getElementById('diary-sheet')?.classList.remove('open');
}

// Si el Diario está abierto detrás (calificaste desde una card), repintarlo para que
// las estrellas nuevas aparezcan al volver — el sheet no participa del pipeline.
export function _refreshDiaryIfOpen(){
  const sheet=document.getElementById('diary-sheet');
  if(!sheet||!sheet.classList.contains('open')) return;
  const body=document.getElementById('diary-body');
  if(body) body.innerHTML=renderDiaryHTML(state);
}

export function _closeTopSheet(){
  // Cerrar en orden de prioridad (el más reciente primero)
  if(document.getElementById('venue-sheet')?.classList.contains('open')){closeVenueSheet();return true;}
  if(document.getElementById('pv-rating-sheet')?.classList.contains('open')){closePVRating();return true;}
  if(document.getElementById('conflict-sheet')?.classList.contains('open')){closeConflictSheet();return true;}
  if(document.getElementById('prio-limit-sheet')?.classList.contains('open')){closePrioLimit();return true;}
  if(document.getElementById('rating-overlay')?.classList.contains('open')){closeRatingSheet();return true;}
  if(document.getElementById('pel-sheet')?.classList.contains('open')){closePelSheet();return true;}
  if(document.getElementById('diary-sheet')?.classList.contains('open')){closeDiary();return true;}
  // Action modal dinámico
  const modal=document.querySelector('.conflict-modal');
  if(modal){modal.remove();return true;}
  return false;
}

export function openCortoSheet(title, country, duration, section, flags, director, genre, synopsis, posterOverride){
  const inner=document.getElementById('pel-sheet-inner');
  if(!inner) return;
  const pelSheet=document.getElementById('pel-sheet');
  if(pelSheet&&pelSheet.classList.contains('open')){
    _cortoParentHtml=inner.innerHTML;
  } else {
    _cortoParentHtml=null;
  }
  let richItem=null;
  for(const f of FILMS){
    if(f.film_list){const found=f.film_list.find(c=>c.title===title);if(found){richItem=found;break;}}
  }
  const dir=director||(richItem&&richItem.director)||'';
  const gnr=_genreEN(genre||(richItem&&richItem.genre)||'');
  const yr=(richItem&&richItem.year)?String(richItem.year):'';
  // Sinopsis localizada vía locSynopsis (mismo helper que el sheet de película),
  // no la versión truncada a 200 chars que llega por data-attr.
  const syn=richItem ? locSynopsis(richItem) : (synopsis||'');
  const ctry=country||(richItem&&richItem.country)||'';
  const dur=duration||(richItem&&richItem.duration)||'';
  // Letterboxd: el slug del corto vive en richItem.lbSlug (item de film_list),
  // NO en el mapa lbSlugs del festival → usar lbUrlForFilm(richItem). lbUrl(title)
  // (por título contra el mapa) fallaba y dejaba el enlace oculto.
  const lbHref=(richItem&&lbUrlForFilm(richItem))||lbUrl(title);
  // `flags` NO viaja en los data-attr del item (_mkCortoItemHtml no lo emite),
  // así que acá llegaba vacío y el corto caía a recalcular desde el país — y con
  // los paréntesis de coproducción de FINCA, al globo. richItem ES el item de
  // film_list: su `flags` es el dato autoritativo, igual que ya se hace con
  // duration, lbSlug y poster. Recalcular teniendo el valor es la fuente doble.
  const flgs=flags||(richItem&&richItem.flags)||countryToFlags(ctry||(richItem&&richItem.country))||'🌐';
  const posterUrl=posterOverride||(richItem&&getCortoItemPoster(richItem))||getPosterSrc(title,true)||null;
  // Editorial por posterSource (still 16:9 local del festival) O por CDN-URL. Sin
  // el chequeo de posterSource, un still local caía a <img> recortado 2:3.
  const _pp3=itemPosterParts({title, poster:posterUrl, posterSource:richItem&&richItem.posterSource}, section||'', 'pel-sheet-poster', {header:true});
  const posterHtml=_pp3.ed
    ?`<div class="psp-editorial poster-ed" style="--ed-accent:${_pp3.accent}">${_pp3.inner}</div>`
    :posterUrl
      ?`<img class="pel-sheet-poster" src="${posterUrl}" data-title="${(title||"").replace(/"/g,'&quot;')}" loading="lazy" onerror="_cortoSheetPosterErr(this)" alt="">`
      :`<img class="pel-sheet-poster" src="${makeProgramPoster(state,title,dur,section||'')||''}" alt="" loading="lazy">`;
  const ps=document.getElementById('pel-sheet');
  if(ps) ps.scrollTop=0;
  _pushSheetState();
  const parent=_findParentProgram(title);
  const parentTitle=parent?parent.title:null;
  const inWL=watchlist.has(parentTitle||title);
  const inPrio=prioritized.has(parentTitle||title);
  const secLabel=_secLabel(section||'');
  // FUNCIÓN del corto: la hereda de su(s) programa(s) — el corto no es entrada de
  // FILMS, el día/hora/sede viven en el bloque que lo proyecta. Se pinta con el MISMO
  // constructor de filas que la ficha de película (_screeningRows), no con una línea
  // de texto aparte: es el mismo concepto, un solo lenguaje visual. Encabezado
  // "Función" a secas (decisión de Juan): la fila es idéntica a la de una película y
  // el aviso inmediatamente debajo ya explica que esa función incluye el programa.
  // Sin función anunciada (bloque-catálogo sin sesión) → VACÍO EXPLÍCITO: callar
  // dejaba la ficha muda y el usuario no sabía si el dato faltaba o no existía.
  const _cortoPairs=_cortoScreeningPairs(title);
  // Rótulo NEUTRO ("FUNCIÓN"/"FUNCIONES"): el adjetivo "compartida" NO va acá —
  // sería un error de categoría (el rótulo nombra el bloque; compartida es propiedad
  // de la fila) y mentiría cuando una obra tiene dos funciones y solo una es
  // compartida. Vive en su meta-banner, con el MISMO peso visual que Q&A e
  // inscripción previa: mismo componente, punto ámbar y rótulo. El rótulo dice
  // "Compartida" a secas, sin repetir el sustantivo del bloque.
  const _cortoShared=_cortoPairs.length>0;
  // las OTRAS obras de su(s) programa(s), sin contarse a sí mismo.
  // Mismo criterio: si sus programas tienen distinto tamaño, no se afirma un número.
  const _cortoSharedN=(()=>{
    const _cuentas=new Set(_cortoPairs.map(p=>((p.owner&&p.owner.film_list)||[]).filter(it=>it.title!==title).length));
    _cuentas.delete(0);
    return _cuentas.size===1?[..._cuentas][0]:0;
  })();
  const _cortoScrLbl=_cortoPairs.length>1?t('label_funciones_pl'):t('label_funcion');
  const _cortoScrHdr=`<div class="sec-hdr sm">${ICONS.clock} <span>${_cortoScrLbl}</span>${_cortoPairs.length>1?`<span class="count-badge cb-neutral">${_cortoPairs.length}</span>`:''}</div>`;
  const _cortoScrBody=_cortoPairs.length
    ?`<div class="pel-sheet-screenings">${_screeningRows(_cortoPairs)}</div>`
    :emptyState(ICONS.clock, t('corto_sin_funcion'));
  inner.innerHTML=`
    <div class="pel-sheet-header">
      ${posterHtml}
      <div class="pel-sheet-meta">
        <div class="pel-sheet-title">${title}</div>
        <div class="pel-sheet-flags-dur">${flgs}${dur?` · ${dur}`:''}</div>
        ${(dir||gnr||yr)?`<div class="pel-sheet-metaline">${[dir,gnr,yr].filter(Boolean).join(' · ')}</div>`:''}
        ${secLabel?`<div class="pel-sheet-sec">${secLabel}</div>`:''}
        <a class="c-lb pel-sheet-lb" href="${lbHref||'#'}" target="_blank" rel="noopener"${!lbHref?' style="display:none"':''}>${LB_SVG}<span class="c-lb-text pel-sheet-lb-text">Letterboxd</span></a>
      </div>
    </div>
        ${_cortoScrHdr}${_cortoScrBody}
        ${_avisosBand(null, {prog:_cortoShared?'cortos':null, progN:_cortoSharedN, scrs:_cortoPairs.map(p=>p.s)})}
        ${syn?`<div class="sec-hdr sm">${ICONS.text} <span>${t('label_sinopsis')}</span></div><div class="pel-sheet-synopsis">${syn}</div>`:''}
    <div class="pel-sheet-foot">
    <div class="pel-sheet-ctas">
      <button id="corto-wl-btn" class="row-center-xs pel-sheet-action-btn${inWL?' act-on btn-primary':' btn-primary'}" data-title="${escXML(parentTitle||title)}" data-action="toggleWL">${inWL?ICONS.heartFill:ICONS.heart} ${inWL?t('cta_en_intereses'):t('cta_intereses')}</button>
      <button id="corto-prio-btn" class="row-center-xs pel-sheet-action-btn${inPrio?' act-prio':' btn-secondary'}" data-title="${escXML(parentTitle||title)}" data-action="togglePelPrio">${inPrio?ICONS.bookmarkFill:ICONS.bookmark} ${inPrio?t('cta_priorizada'):t('cta_priorizar')}</button>
      <button class="row-center-xs pel-sheet-action-btn${filmRatings[title]?' act-on':' btn-secondary'}" data-title="${escXML(title)}" data-action="closePelAndRate">${ICONS.star} ${filmRatings[title]?t('misc_cambiar'):t('cta_calificar')}</button>
    </div>
    </div>
  `;
  const _psReset2=document.getElementById('pel-sheet');
  if(_psReset2){_psReset2.scrollTop=0;_psReset2.classList.remove('compact');}
  document.getElementById('pel-overlay').classList.add('open');
  const _psCo=document.getElementById('pel-sheet');
  _psCo.scrollTop=0;
  _psCo.classList.add('open');
  _applyAmbient(_psCo, posterUrl, _sectionColor(section||''));
}

export function openCortoSheetFromEl(el,e){
  if(e) e.stopPropagation();
  const title=decodeURIComponent(el.dataset.ct||'');
  const parent=_findParentProgram(title);
  const section=parent?.section||'';
  // data-cp: poster resuelto en render time — llega directo, sin depender de richItem lookup
  const posterOverride=decodeURIComponent(el.dataset.cp||'')||null;
  openCortoSheet(
    title,
    decodeURIComponent(el.dataset.cc||''),
    decodeURIComponent(el.dataset.cd||''),
    section,
    countryToFlags(decodeURIComponent(el.dataset.cc||'')),
    decodeURIComponent(el.dataset.cdir||''),
    decodeURIComponent(el.dataset.cg||''),
    decodeURIComponent(el.dataset.cs||''),
    posterOverride
  );
}

export function _openCombinedFilmSheet(filmData){
  const inner=document.getElementById('pel-sheet-inner');
  if(!inner) return;
  const pelSheet=document.getElementById('pel-sheet');
  if(pelSheet&&pelSheet.classList.contains('open')){
    _cortoParentHtml=inner.innerHTML;
  }
  const{title='',director='',year='',duration='',flags='🌐',country='',lbSlug='',poster:_fPoster='',posterSource:_fPS=''}=filmData;
  const posterUrl=_fPoster?((_fPoster.startsWith('http')||_fPoster.startsWith('/assets/'))?_fPoster:TMDB_IMG+_fPoster):getPosterSrc(title,false)||null;
  const _sec4=(()=>{const _p=FILMS.find(f=>f.film_list&&f.film_list.some(c=>c.title===title));return _p?.section||'';})();
  const _pp4=itemPosterParts({title, poster:posterUrl, posterSource:_fPS}, _sec4, 'pel-sheet-poster', {header:true});
  const posterHtml=_pp4.ed
    ?`<div class="psp-editorial poster-ed" style="--ed-accent:${_pp4.accent}">${_pp4.inner}</div>`
    :posterUrl
      ?`<img class="pel-sheet-poster" src="${posterUrl}" data-title="${(title||"").replace(/"/g,'&quot;')}" loading="lazy" onerror="_cortoSheetPosterErr(this)" alt="">`
      :`<div class="pel-sheet-poster-ph" aria-hidden="true">🎬</div>`;
  const metaLine=[director,year].filter(Boolean).join(' · ');
  const lbHref=lbUrlForFilm({title,lbSlug}); // guard de slugs incluido (marcador ⚠ jamás llega al href)
  const ps=document.getElementById('pel-sheet');
  if(ps) ps.scrollTop=0;
  _pushSheetState();
  inner.innerHTML=`
    <div class="pel-sheet-header">
      ${posterHtml}
      <div class="pel-sheet-meta">
        <div class="pel-sheet-title">${title}</div>
        ${(flags||duration)?`<div class="pel-sheet-flags-dur">${flags||''}${flags&&duration?' · ':''}${duration||''}</div>`:''}
        ${metaLine?`<div class="pel-sheet-metaline">${metaLine}</div>`:''}
        ${(()=>{const _parent=FILMS.find(f=>f.film_list&&f.film_list.some(c=>c.title===title));const _sec=_parent?.section;if(!_sec)return'';const _lbl=_secLabel(_sec);return`<div class="pel-sheet-sec" style="cursor:default">${_lbl}</div>`;})()}
      </div>
    </div>
        <div class="sec-hdr sm">${ICONS.text} <span>${t('label_sinopsis')}</span></div>
    <div class="pel-sheet-synopsis">${locSynopsis(filmData)}</div>
    <a class="c-lb pel-sheet-lb" href="${lbHref||'#'}" target="_blank" rel="noopener"${!lbHref?' style="display:none"':''}>${LB_SVG}<span class="c-lb-text pel-sheet-lb-text">Letterboxd</span></a>
      `;
  const _psReset=document.getElementById('pel-sheet');
  if(_psReset){_psReset.scrollTop=0;_psReset.classList.remove('compact');}
  document.getElementById('pel-overlay').classList.add('open');
  const _psC=document.getElementById('pel-sheet');
  _psC.scrollTop=0;
  _psC.classList.add('open');
  _applyAmbient(_psC, posterUrl, _sectionColor(_sec4));
}

export function _findParentProgram(cortoTitle){
  return FILMS.find(f=>f.is_cortos&&f.film_list?.some(c=>c.title===cortoTitle))||null;
}

// _findParentPrograms — TODOS los programas que incluyen este corto. El singular
// devuelve solo el primero y sirve para lo 1:1 (el corazón). Para las FUNCIONES no
// alcanza: un corto se programa en dos bloques con día/hora/sede propios (Ecocidio en
// FINCA: 13 AGO Cacodelphia + 15 AGO Cine York; en Olhar, 10 cortos repiten en la
// "Sessão com Acessibilidade"). Mostrar solo el primero es PEOR que no mostrar nada:
// el usuario confía en una única función y se pierde la otra.
export function _findParentPrograms(cortoTitle){
  const out=[],seen=new Set();
  FILMS.forEach(f=>{
    if(!f.is_cortos||!f.film_list?.some(c=>c.title===cortoTitle)) return;
    if(seen.has(f.title)) return;
    seen.add(f.title); out.push(f);
  });
  return out;
}

export function openConflictSheet(incomingTitle, incomingScreen, existingEntry){
  const{displayTitle:inDT}=parseProgramTitle(incomingTitle);
  const{displayTitle:exDT}=parseProgramTitle(existingEntry._title||'');

  // Pósters
  const inF=FILMS.find(f=>f.title===incomingTitle&&f.day===incomingScreen.day&&f.time===incomingScreen.time);
  const exF=FILMS.find(f=>f.title===(existingEntry._title||''));
  const inPoster=getFilmPoster(inF)||'';
  const exPoster=getFilmPoster(exF)||'';

  const ip=document.getElementById('cs-incoming-poster');
  const ep=document.getElementById('cs-existing-poster');
  if(ip){ip.src=inPoster;ip.onerror=()=>{ip.style.opacity='0';};}
  if(ep){ep.src=exPoster;ep.onerror=()=>{ep.style.opacity='0';};}

  // Nombres y horarios
  const setEl=(id,txt)=>{const el=document.getElementById(id);if(el)el.textContent=txt;};
  setEl('cs-incoming-name', inDT);
  // El día va CON su número (2 sep 2026). `.split(' ')[0]` dejaba «JUE» a secas,
  // y 9 de los 15 festivales de la app repiten nombre de día —todos los de 8
  // días o más: Tribeca tiene 5 pares, TIFF 4, Cinemancia 3—, así que «JUE» no
  // distinguía el 3 del 10. Medido a 375px en las cuatro superficies: el número
  // no cuesta nada —misma altura, misma caja, sin desbordar ni partir línea—
  // porque ninguna de estas clases lleva `nowrap` y la caja sobraba.
  setEl('cs-incoming-when', `${dayLabel(incomingScreen.day)||''} · ${incomingScreen.time} · ${inF?.duration||''}`);
  setEl('cs-existing-name', exDT);
  const exWhen=existingEntry.day?`${dayLabel(existingEntry.day)||''} · ${existingEntry.time} · ${exF?.duration||''}`:'';
  setEl('cs-existing-when', exWhen);

  // Título del sheet: si el conflicto es por margen (salas/viaje), el título
  // ES la cuenta — «se solapan en el mismo tramo» era falso cuando las horas
  // visibles no se pisaban y el agente del QA (15 ago 2026) descartó la función
  // creyendo que la app se equivocaba. 'solape' (dato visible) y 'ciudad'
  // conservan el título genérico. conflictAccount = dueño único de la frase.
  const _titleEl=document.getElementById('conflict-title-el');
  if(_titleEl){
    const _r=screensConflictReason(incomingScreen,existingEntry);
    const _cuenta=conflictAccount(incomingScreen,existingEntry,_r);
    _titleEl.classList.toggle('cuenta',!!_cuenta);
    if(_cuenta) _titleEl.innerHTML=_cuenta;
    else _titleEl.textContent=t('conflict_titulo');
  }

  // Botón de reemplazo con nombre exacto
  // Guardar pendiente para ejecutar al confirmar
  _conflictPending={incomingTitle, incomingScreen, existingEntry};

  const btn=document.getElementById('cs-replace-btn');
  const keepBtn=document.getElementById('cs-keep-btn');
  if(btn) btn.onclick=confirmConflictReplace;
  if(keepBtn) keepBtn.onclick=closeConflictSheet;

  document.getElementById('conflict-sheet-overlay').classList.add('open');
  document.getElementById('conflict-sheet').classList.add('open');
  _pushSheetState();
}

export function closeConflictSheet(){
  _conflictPending=null;
  document.getElementById('conflict-sheet-overlay').classList.remove('open');
  document.getElementById('conflict-sheet').classList.remove('open');
}

export function confirmConflictReplace(){
  // 1. READ + 2. GUARD
  if(!_conflictPending) return;
  const{incomingTitle, incomingScreen, existingEntry}=_conflictPending;
  // 3. MUTATE — quitar la existente e insertar la nueva
  commitPlan(a=>{const b=a||{schedule:[]};return {...b,
    schedule: [
      ...b.schedule.filter(s=>!sameEntry(s,existingEntry)),
      {...incomingScreen,_title:incomingTitle}
    ].sort((x,y)=>x.day_order!==y.day_order?x.day_order-y.day_order:toMin(x.time)-toMin(y.time))
  };});
  // 4. PERSIST + 5. RENDER + UI EFFECTS
  saveSavedAgenda();
  const{displayTitle:dt}=parseProgramTitle(incomingTitle);
  closeConflictSheet();
  showToast(`${ICONS.calendar} ${t('toast_en_tu_plan',{title:dt.length>22?dt.slice(0,20)+'…':dt})}`,'info');
  renderAgenda();
}

export function openPrioLimit(newTitle){
  // Eyebrow con contador
  const eyebrow=document.getElementById('prio-limit-eyebrow-txt');
  const count=document.getElementById('prio-limit-count');
  if(eyebrow) eyebrow.textContent=`${t('lbl_prioridades')} · ${PRIO_LIMIT}/${PRIO_LIMIT}`;
  if(count) count.textContent=PRIO_LIMIT;
  // i18n patches for static prio-limit elements
  const _yaTenes=document.getElementById('prio-limit-ya-tenes-txt');
  const _prioWord=document.getElementById('prio-limit-prio-word');
  const _quieres=document.getElementById('prio-limit-quieres');
  if(_yaTenes) _yaTenes.textContent=t('plan_ya_tenes_prio');
  if(_prioWord) _prioWord.textContent=t('misc_prioridades');
  if(_quieres)  _quieres.textContent=t('plan_quieres_prio');

  // Título de la nueva película
  const{displayTitle}=parseProgramTitle(newTitle);
  const newTitleEl=document.getElementById('prio-limit-new-title');
  if(newTitleEl) newTitleEl.textContent=displayTitle;

  // Lista de prioritarias actuales
  const list=document.getElementById('prio-limit-list');
  if(list){
    // `_ttl` y NO `t`: el nombre del parámetro pisaba la t() de i18n, y la llamada
    // a t('misc_cambiar') de doce líneas más abajo reventaba con «t is not a
    // function». La hoja del tope de prioridades no abría NUNCA —en todos los
    // festivales— y el usuario se pasaba del tope justo porque lo que debía
    // frenarlo se caía antes del classList.add('open'). Cubierto por [shadow-t].
    const items=[...prioritized].map(_ttl=>{
      const{displayTitle:dt}=parseProgramTitle(_ttl);
      const f=FILMS.find(fi=>fi.title===_ttl&&!screeningPassed(fi));
      // Día con número (ver cs-incoming-when): esta lista muestra hasta PRIO_LIMIT
      // obras de días distintos, y es donde dos «JUE» a secas más engañan.
      const when=f?`${dayLabel(f.day)||f.day} · ${f.time}`:'';
      const poster=getFilmPoster(f)||'';
      const safeSwap=_ttl.replace(/"/g,'&quot;').replace(/'/g,"&#39;");
      const safeNew=newTitle.replace(/"/g,'&quot;').replace(/'/g,"&#39;");
      return`<div class="prio-limit-item">
        ${poster?`<img class="prio-limit-thumb" src="${poster}" onerror="this.remove()" alt="" loading="lazy">`:'<div class="prio-limit-thumb"></div>'}
        <div class="prio-limit-info">
          <div class="prio-limit-name">${dt}</div>
          <div class="prio-limit-when">${when}</div>
        </div>
        <button class="prio-limit-swap" data-action="swapPriority" data-rmtitle="${safeSwap}" data-addtitle="${safeNew}">${t('misc_cambiar')}</button>
      </div>`;
    }).join('');
    list.innerHTML=items;
  }

  document.getElementById('prio-limit-overlay').classList.add('open');
  document.getElementById('prio-limit-sheet').classList.add('open');
}

export function openPlanConfirm(schedule){
  // Ordenar por posición en DAY_KEYS (funciona para cualquier festival)
  const sorted=[...schedule].sort((a,b)=>{
    const ai=DAY_KEYS.indexOf(a.day),bi=DAY_KEYS.indexOf(b.day);
    return (ai<0?999:ai)-(bi<0?999:bi)||a.time.localeCompare(b.time);
  });
  const total=sorted.length;
  // Dueño único del rango de días de un tramo del Plan: lo piden el subtítulo
  // (el Plan entero) y el pie (solo las que no se muestran). Eran dos fórmulas.
  const _rango=e=>{const d=[...new Set(e.map(x=>x.day))];
    return d.length?(d.length===1?dayLabel(d[0]):`${dayLabel(d[0])}–${dayLabel(d[d.length-1])}`):'';};
  const dayRange=_rango(sorted);

  // Sub: N películas · DÍAS
  const sub=document.getElementById('plan-confirm-sub');
  if(sub) sub.innerHTML=`<span class="mr-1 count-badge cb-neutral">${total}</span> · ${dayRange}`;

  // Lista — máx 3 + resumen del resto. Fila canónica (anatomía y porqué: el
  // comentario de .plan-confirm-film en index.html). El día no es un agregado:
  // es el renglón que la fila ya tiene para el cuándo, y sin él la hoja mostraba
  // «19:00 · 14:30 · 14:00» (medido en Cinemancia) — el orden es por día.
  // dayLabel COMPLETO («JUE 3»), no el «JUE» que recortan otros 4 sitios:
  // Cinemancia dura 10 días y tiene dos jueves, dos viernes y dos sábados.
  const show=sorted.slice(0,3);
  const rest=total-show.length;
  const filmsEl=document.getElementById('plan-confirm-films');
  if(filmsEl){
    filmsEl.innerHTML=show.map(s=>{
      const{displayTitle:dt}=parseProgramTitle(s._title||'');
      // La función exacta; el fallback por título deja viva la fila si el
      // catálogo cambió bajo un plan ya guardado.
      const f=FILMS.find(fi=>fi.title===s._title&&fi.day===s.day&&fi.time===s.time)
             ||FILMS.find(fi=>fi.title===s._title);
      return`<div class="plan-confirm-film">
        ${_posterThumb(f,'lb-poster')}
        <div class="plan-confirm-info">
          <div class="plan-confirm-name">${dt}</div>
          <div class="plan-confirm-when">${dayLabel(s.day)||s.day} · ${s.time}</div>
        </div>
      </div>`;
    }).join('');
  }
  // El pie cuenta el rango de LAS QUE FALTAN, no el del Plan entero: decía
  // «+ 5 más · JUE 3–VIE 11» y JUE 3 es la primera fila, ya está arriba.
  const masEl=document.getElementById('plan-confirm-mas');
  if(masEl){
    // Sin «·» propio: misc_mas ya lo trae dentro («más ·»). Lo cazó la auditoría
    // de lo pintado — la plantilla se leía bien y la pantalla decía «más · ·».
    masEl.textContent=rest>0?`+ ${rest} ${t('misc_mas')} ${_rango(sorted.slice(3))}`:'';
    masEl.style.display=rest>0?'':'none';
  }

  const _pcSheet=document.getElementById('plan-confirm-sheet');
  if(_pcSheet){ _pcSheet.style.display=''; requestAnimationFrame(()=>_pcSheet.classList.add('open')); }
  document.getElementById('plan-confirm-overlay').classList.add('open');
}

export function closePlanConfirm(goToPlan){
  document.getElementById('plan-confirm-overlay').classList.remove('open');
  const _pcSheet=document.getElementById('plan-confirm-sheet');
  if(_pcSheet){
    _pcSheet.classList.remove('open');
    setTimeout(()=>{ if(!_pcSheet.classList.contains('open')) _pcSheet.style.display='none'; },350);
  }
  if(goToPlan){
    switchMainNav('mnav-miplan');
    showAgView();
    const agView=document.getElementById('ag-view');
    if(agView) agView.scrollTop=0;
  }
}

export function openPostViewRating(title, day, time, venue, duration){
  const f=FILMS.find(fi=>fi.title===title);
  // PROGRAMA → cola paso a paso por obra. Guardar/Después operan sobre la obra visible;
  // cerrar el sheet descarta las que falten (calificar es opcional, salir siempre es libre).
  if(f&&f.is_cortos&&f.film_list&&f.film_list.length){
    _pvQueue=f.film_list; _pvQueueIdx=0; _pvRatedCount=0; _pvSection=f.section||'';
    _pushSheetState();
    _pvShowCurrent();
    return;
  }
  _pvQueue=null;
  _pvTitle=title;
  _pushSheetState();
  _pvRating=filmRatings[title]||0;

  const{displayTitle}=parseProgramTitle(title);

  // Poster
  const poster=document.getElementById('pv-poster');
  if(poster){
    const src=getFilmPoster(f)||'';
    poster.src=src;
    poster.onerror=()=>{poster.style.opacity='0';};
  }

  // Título
  const titleEl=document.getElementById('pv-film-title');
  if(titleEl) titleEl.textContent=displayTitle;

  // Contexto: día · venue · duración
  const ctx=document.getElementById('pv-context');
  if(ctx){
    const parts=[];
    if(day) parts.push(dayLabel(day)||day);   // con número (ver cs-incoming-when)
    if(venue) parts.push(venue.split('·')[0].trim().split('‒')[0].trim());
    if(duration) parts.push(duration);
    ctx.textContent=parts.join(' · ');
  }

  _pvMountAndOpen();
}

// _pvShowCurrent — pinta la obra actual de la cola en el MISMO sheet post-vista:
// su póster (real → generativo del programa), su título, y el paso "1 de 2 · dur · país".
function _pvShowCurrent(){
  const item=_pvQueue[_pvQueueIdx], total=_pvQueue.length;
  _pvTitle=item.title;
  _pvRating=filmRatings[item.title]||0;
  const poster=document.getElementById('pv-poster');
  if(poster){
    poster.style.opacity='';
    poster.src=getCortoItemPoster(item)||makeProgramPoster(state,item.title,item.duration||'',_pvSection);
    poster.onerror=()=>{poster.style.opacity='0';};
  }
  const titleEl=document.getElementById('pv-film-title');
  if(titleEl) titleEl.textContent=item.title;
  const ctx=document.getElementById('pv-context');
  if(ctx){
    const parts=[t('pv_paso',{n:_pvQueueIdx+1,total})];
    if(item.duration) parts.push(durFmt(item.duration));
    if(item.country) parts.push(item.country);
    ctx.textContent=parts.join(' · ');
  }
  _pvMountAndOpen();
}

// _pvMountAndOpen — tail compartido (film suelto y cola): estrellas + range + apertura.
function _pvMountAndOpen(){
  const range=document.getElementById('pv-range');
  if(range){
    range.value=Math.round(_pvRating*2);
    range._pvInit=false;
  }
  _pvRenderStars(_pvRating);

  // Listener del range
  requestAnimationFrame(()=>{
    const r=document.getElementById('pv-range');
    if(r&&!r._pvInit){
      r._pvInit=true;
      r.addEventListener('input',()=>{
        _pvRating=parseInt(r.value)/2;
        _pvRenderStars(_pvRating);
      });
    }
  });

  document.getElementById('pv-rating-overlay').classList.add('open');
  const _pvSheet=document.getElementById('pv-rating-sheet');
  if(_pvSheet){ _pvSheet.style.display=''; requestAnimationFrame(()=>_pvSheet.classList.add('open')); }
}

export function openRatingSheet(title){
  _ratingTitle=title;
  _pushSheetState();
  const _rs=document.getElementById('rating-sheet');
  if(_rs) _rs.scrollTop=0;
  _currentRating=filmRatings[title]||0;
  const{displayTitle}=parseProgramTitle(title);
  document.getElementById('rating-film-title').textContent=displayTitle;
  renderRatingStars(_currentRating);
  const _btn=document.getElementById('rating-action-btn');
  if(_btn){
    if(_currentRating>0){_btn.textContent=t('misc_guardar');_btn.className='rating-action-btn save';}
    else{_btn.textContent=t('misc_omitir');_btn.className='rating-action-btn skip';}
  }
  document.getElementById('rating-overlay').classList.add('open');
  document.getElementById('rating-sheet').classList.add('open');
  requestAnimationFrame(()=>{
    const range=document.getElementById('rating-range');
    if(range){range.value=Math.round(_currentRating*2);range._ratingInit=false;}
    _initRatingInteraction();
  });
}

export function closeRatingSheet(){
  if(_currentRating>0){
    saveRating(_ratingTitle,_currentRating);
    _refreshDiaryIfOpen();
    const _stars=starsDisplay(_currentRating,11);
    showToast(`<span class="row-xs">${_stars}</span>`,'info');
  } else {
    if(filmRatings[_ratingTitle]){
      saveRating(_ratingTitle,0);
      showToast(t('toast_calif_elim'),'info');
    }
  }
  document.getElementById('rating-overlay').classList.remove('open');
  document.getElementById('rating-sheet').classList.remove('open');
  // Re-render para reflejar el nuevo rating
  _reRenderIntereses();
  // Actualizar Mi Plan si está activo
  if(activeMNav==='mnav-miplan') renderAgenda();
  // Actualizar Intereses
  if(activeMNav==='mnav-seleccion') updateAgTab();
  // Actualizar el rating visible en el sheet si está abierto
  const _pelSheet=document.getElementById('pel-sheet');
  if(_pelSheet&&_pelSheet.classList.contains('open')){
    // Actualizar estrellas en el sheet actual (si el título coincide)
    const _rStars=_pelSheet.querySelector('.pel-sheet-rating-stars');
    if(_rStars&&_currentRating>0) _rStars.textContent=starsText(_currentRating);
  }
}

export function renderRatingStars(current){
  const el=document.getElementById('rating-stars');
  if(!el) return;
  el.innerHTML=renderRatingStarsHTML(state, current);
}

export function updateRatingStars(current){
  const el=document.getElementById('rating-stars');
  if(!el) return;
  const wraps=el.querySelectorAll('div');
  if(wraps.length!==5){renderRatingStars(current);return;}
  for(let i=0;i<5;i++){
    const star=i+1;
    const fill=current>=star?'full':current>=star-0.5?'half':'none';
    const poly=wraps[i].querySelector('polygon');
    const defs=wraps[i].querySelector('defs');
    if(!poly) continue;
    if(fill==='none'){
      poly.setAttribute('fill','none');
      poly.setAttribute('stroke','rgba(255,255,255,.2)');
      if(defs) defs.remove();
    } else if(fill==='full'){
      if(defs) defs.remove();
      poly.setAttribute('fill','var(--amber)');
      poly.setAttribute('stroke','var(--amber)');
    } else {
      // half — recrear gradient solo cuando es necesario
      const svg=wraps[i].querySelector('svg');
      if(svg&&!defs){
        const id='rg'+i;
        svg.insertAdjacentHTML('afterbegin',
          `<defs><linearGradient id="${id}"><stop offset="50%" stop-color="var(--amber)"/><stop offset="50%" stop-color="transparent"/></linearGradient></defs>`);
        poly.setAttribute('fill',`url(#${id})`);
        poly.setAttribute('stroke','var(--amber)');
      }
    }
  }
}

export function setRating(val){
  _currentRating=val;
  updateRatingStars(val); // rápido, sin recrear DOM
  const btn=document.getElementById('rating-action-btn');
  if(btn){
    if(val>0){btn.textContent=t('misc_guardar');btn.className='rating-action-btn save';}
    else{btn.textContent=t('misc_omitir');btn.className='rating-action-btn skip';}
  }
}

export function _initRatingInteraction(){
  const range=document.getElementById('rating-range');
  if(!range||range._ratingInit) return;
  range._ratingInit=true;
  range.addEventListener('input',()=>{
    setRating(parseInt(range.value)/2);
  });
}

export function _pvStarSVG(fill){
  if(fill==='full')  return`<svg width="34" height="34" viewBox="0 0 24 24"><polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26" fill="var(--amber)" stroke="var(--amber)" stroke-width="1.75" stroke-linejoin="round"/></svg>`;
  if(fill==='half')  return`<svg width="34" height="34" viewBox="0 0 24 24"><defs><linearGradient id="pvhg"><stop offset="50%" stop-color="var(--amber)"/><stop offset="50%" stop-color="transparent"/></linearGradient></defs><polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26" fill="url(#pvhg)" stroke="var(--amber)" stroke-width="1.75" stroke-linejoin="round"/></svg>`;
  return`<svg width="34" height="34" viewBox="0 0 24 24" style="opacity:.15"><polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26" fill="none" stroke="var(--amber)" stroke-width="1.75" stroke-linejoin="round"/></svg>`;
}

export function _pvRenderStars(val){
  const row=document.getElementById('pv-stars-row');
  if(!row) return;
  row.innerHTML='';
  for(let i=1;i<=5;i++){
    const fill=val>=i?'full':val>=i-.5?'half':'none';
    const div=document.createElement('div');
    div.className='pv-star';
    div.innerHTML=_pvStarSVG(fill);
    row.appendChild(div);
  }
  // Hint y botón
  const hint=document.getElementById('pv-hint');
  const btn=document.getElementById('pv-btn-save');
  if(hint) hint.textContent=val>0?t('pv_de_5',{val}):t('misc_deslizar');
  if(hint) hint.style.color=val>0?'var(--amber)':'var(--gray)';
  if(btn)  btn.disabled=val===0;
}

export function starsDisplay(rating,size){
  // size en px para display compacto
  if(!rating) return '';
  let html='';
  for(let i=1;i<=5;i++){
    const fill=rating>=i?'full':rating>=i-0.5?'half':'none';
    const s=size||10;
    const id='sd'+i+Math.random().toString(36).slice(2,5);
    const grad=fill==='half'?`<defs><linearGradient id="${id}"><stop offset="50%" stop-color="var(--amber)"/><stop offset="50%" stop-color="transparent"/></linearGradient></defs>`:'';
    const fv=fill==='none'?'none':fill==='full'?'var(--amber)':`url(#${id})`;
    const st=fill==='none'?'rgba(255,255,255,.2)':'var(--amber)';
    html+=`<svg class="block-shrink" width="${s}" height="${s}" viewBox="0 0 24 24">${grad}<polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26" fill="${fv}" stroke="${st}" stroke-width="1.75" stroke-linejoin="round"/></svg>`;
  }
  return html;
}

export function openAvSheet(){
  const ov=document.getElementById('av-sheet-overlay');
  if(!ov) return;
  // Seleccionar primer día no pasado
  if(!_avSheetDay||dayFullyPassed(_avSheetDay)){
    _avSheetDay=DAY_KEYS.find(d=>!dayFullyPassed(d))||DAY_KEYS[0];
  }
  // Poblar chips de días con data-day para comparación fiable
  const chipsEl=document.getElementById('av-day-chips');
  if(chipsEl){
    chipsEl.innerHTML=DAY_KEYS.map(d=>{
      const isPast=dayFullyPassed(d);
      const lbl=(DAY_ABBR&&DAY_ABBR[d])||d.slice(0,3).toUpperCase();
      const num=(DAY_NUM&&DAY_NUM[d])||'';
      // ' on', no ' selected': el CSS solo pinta .av-day-chip.on, así que el día
      // preseleccionado se veía IDÉNTICO a los no elegidos — y «Confirmar» sin
      // tocar nada bloqueaba ese día en silencio.
      const sel=_avSheetDay===d?' on':'';
      return`<button class="av-day-chip${isPast?' past':''}${sel}" data-day="${d}" data-action="selectAvDay">${lbl} ${num}</button>`;
    }).join('');
  }
  // Poblar selects de horas
  const timeOpts=['08:00','08:30','09:00','09:30','10:00','10:30','11:00','11:30','12:00','12:30','13:00','13:30','14:00','14:30','15:00','15:30','16:00','16:30','17:00','17:30','18:00','18:30','19:00','19:30','20:00','20:30','21:00','21:30','22:00','22:30','23:00'];
  const optsHtml=timeOpts.map(t=>`<option value="${t}">${t}</option>`).join('');
  const fromEl=document.getElementById('av-sheet-from');
  const toEl=document.getElementById('av-sheet-to');
  if(fromEl){fromEl.innerHTML=optsHtml;fromEl.value='09:00';}
  if(toEl){toEl.innerHTML=optsHtml;toEl.value='12:00';}
  setAvType('hours');
  ov.style.display='flex';
}

export function selectAvDay(day){
  _avSheetDay=day;
  _refreshAvDayChips();
}

export function _refreshAvDayChips(){
  document.querySelectorAll('.av-day-chip').forEach(btn=>{
    btn.classList.toggle('on', btn.dataset.day===_avSheetDay);
  });
}

export function setAvType(type){
  _avSheetType=type;
  document.getElementById('av-type-hours')?.classList.toggle('on',type==='hours');
  document.getElementById('av-type-full')?.classList.toggle('on',type==='full');
  const ts=document.getElementById('av-time-section');
  if(ts) ts.style.display=type==='hours'?'':'none';
}

export function confirmAvBlock(){
  // 1. READ + 2. GUARD
  if(!_avSheetDay) return;
  if(_avSheetType==='full'){
    // Branch A: full-day — delega a toggleFullDay
    closeAvSheet();
    if(!isFullDayBlocked(_avSheetDay)) setTimeout(()=>toggleFullDay(_avSheetDay),50);
    return;
  }
  // Branch B: range
  // 1b. READ DOM inputs
  const from=document.getElementById('av-sheet-from')?.value||'09:00';
  const to=document.getElementById('av-sheet-to')?.value||'12:00';
  // 2b. GUARD — validation con early returns
  if(from>=to){showToast(t('av_hora_invalida'),'warn');return;}
  const av=availability[_avSheetDay];
  if(av.blocks.some(b=>toMin(from)<toMin(b.to)&&toMin(to)>toMin(b.from))){
    showToast(t('av_solapa_bloque'),'warn');return;
  }
  // 3. MUTATE — diferido via conflict modal si hay conflictos
  const _conflicts=checkPlanConflictsWithBlock(_avSheetDay,from,to);
  const _doAdd=()=>{
    _conflicts.forEach(s=>_removePlanItem(s._title));
    state.update('availability', a => ({
      ...a,
      [_avSheetDay]: {...a[_avSheetDay], blocks: [...a[_avSheetDay].blocks, {from,to}].sort((x,y)=>toMin(x.from)-toMin(y.from))}
    }));
    // 4. PERSIST + 5. RENDER
    cachedResult=null;saveAV();renderAvBlocks();invalidateCalcResult();
  };
  closeAvSheet();
  if(_conflicts.length) setTimeout(()=>showConflictModal(_conflicts,_doAdd),50);
  else _doAdd();
}

export function renderAvDay(day){
  const row=document.getElementById(`av-row-${day}`);if(!row) return;
  const fullBlocked=isFullDayBlocked(day);
  const isPast=dayFullyPassed(day);
  row.className=`av-row${isPast?' av-past':''}${fullBlocked?' av-full':''}`;
  row.innerHTML=renderAvDayHTML(state, day);
  // Set default values for selects after render
  if(avAddOpen[day]){
    const sf=document.getElementById(`av-from-${day}`);
    const st=document.getElementById(`av-to-${day}`);
    if(sf) sf.value='12:00';
    if(st) st.value='14:00';
  }
}

export function renderAvDayHTML(state, day){
  const {availability} = state.snapshot();
  const fullBlocked=isFullDayBlocked(day);
  const visibleBlocks=availability[day].blocks.filter(b=>!(toMin(b.from)<=0&&toMin(b.to)>=toMin('23:59')));
  const hasAny=fullBlocked||visibleBlocks.length>0;
  const addOpen=!!avAddOpen[day];

  const pillsHtml=fullBlocked
    ?`<span class="av-pill full">${t('av_todo_el_dia')}</span>`
    :visibleBlocks.map(b=>`<span class="av-pill">${b.from}–${b.to}<button class="av-pill-rm" aria-label="${t('av_eliminar')}" data-action="removeBlock" data-day="${day}" data-from="${b.from}" data-to="${b.to}" data-stop="1">×</button></span>`).join('');

  // Inline form — always shows when addOpen, with 15-min slot dropdowns
  const timeOpts=`<option value="08:00">08:00</option><option value="08:15">08:15</option><option value="08:30">08:30</option><option value="08:45">08:45</option><option value="09:00">09:00</option><option value="09:15">09:15</option><option value="09:30">09:30</option><option value="09:45">09:45</option><option value="10:00">10:00</option><option value="10:15">10:15</option><option value="10:30">10:30</option><option value="10:45">10:45</option><option value="11:00">11:00</option><option value="11:15">11:15</option><option value="11:30">11:30</option><option value="11:45">11:45</option><option value="12:00">12:00</option><option value="12:15">12:15</option><option value="12:30">12:30</option><option value="12:45">12:45</option><option value="13:00">13:00</option><option value="13:15">13:15</option><option value="13:30">13:30</option><option value="13:45">13:45</option><option value="14:00">14:00</option><option value="14:15">14:15</option><option value="14:30">14:30</option><option value="14:45">14:45</option><option value="15:00">15:00</option><option value="15:15">15:15</option><option value="15:30">15:30</option><option value="15:45">15:45</option><option value="16:00">16:00</option><option value="16:15">16:15</option><option value="16:30">16:30</option><option value="16:45">16:45</option><option value="17:00">17:00</option><option value="17:15">17:15</option><option value="17:30">17:30</option><option value="17:45">17:45</option><option value="18:00">18:00</option><option value="18:15">18:15</option><option value="18:30">18:30</option><option value="18:45">18:45</option><option value="19:00">19:00</option><option value="19:15">19:15</option><option value="19:30">19:30</option><option value="19:45">19:45</option><option value="20:00">20:00</option><option value="20:15">20:15</option><option value="20:30">20:30</option><option value="20:45">20:45</option><option value="21:00">21:00</option><option value="21:15">21:15</option><option value="21:30">21:30</option><option value="21:45">21:45</option><option value="22:00">22:00</option><option value="22:15">22:15</option><option value="22:30">22:30</option><option value="22:45">22:45</option><option value="23:00">23:00</option><option value="23:15">23:15</option><option value="23:30">23:30</option><option value="23:45">23:45</option><option value="00:00">00:00</option><option value="00:15">00:15</option><option value="00:30">00:30</option><option value="00:45">00:45</option><option value="01:00">01:00</option>`;
  const inlineForm=addOpen?`<div class="av-inline-form">
      <select id="av-from-${day}" class="av-time-input">${timeOpts}</select>
      <span class="av-sep">–</span>
      <select id="av-to-${day}" class="av-time-input">${timeOpts}</select>
      <button class="av-add-btn" data-action="addBlock" data-day="${day}">${t('av_confirmar')}</button>
      <button class="av-plus-btn" data-action="setAvAddOpen" data-day="${day}" data-open="0">${ICONS.x}</button>
    </div>`:'';

  return `
    <div class="av-row-lbl">
      <div class="av-row-dayname">${DAY_ABBR[day]}</div>
      <div class="av-row-date${hasAny?' wk-has':''}">${DAY_NUM[day]}</div>
    </div>
    <div class="av-row-content">
      ${pillsHtml?`<div class="av-pills">${pillsHtml}</div>`:''}
      ${inlineForm}
      <div class="av-row-btns" style="margin-top:${pillsHtml||addOpen?'6px':'0'}">
        ${!fullBlocked&&!addOpen?`<button class="av-plus-btn" data-action="setAvAddOpen" data-day="${day}" data-open="1">${ICONS.plus} ${t('misc_no_disp')}</button>`:''}
        ${!addOpen?`<button class="row-xs av-full-btn${fullBlocked?' on':''}" data-action="toggleFullDay" data-day="${day}">
          ${fullBlocked?ICONS.x+' '+t('av_liberar_dia'):ICONS.plus+' '+t('av_todo_el_dia_btn')}
        </button>`:''}
      </div>
    </div>`;
}

export function addBlock(day){
  // 1. READ — DOM inputs (input state, ephemeral)
  const f=document.getElementById(`av-from-${day}`).value;
  const toVal=document.getElementById(`av-to-${day}`).value;
  // 2. GUARD — validation con early returns + toast
  if(!f||!toVal){showToast(t('av_seleccionar'),'warn');return;}
  if(toMin(f)>=toMin(toVal)){showToast(t('av_hora_invalida'),'warn');return;}
  const av=availability[day];
  if(av.blocks.some(b=>toMin(f)<toMin(b.to)&&toMin(toVal)>toMin(b.from))){showToast(t('av_solapa_bloque'),'warn');return;}
  // 3. MUTATE — diferida via conflict modal si hay conflictos
  const _blockConflicts=checkPlanConflictsWithBlock(day,f,toVal);
  const _doAdd=()=>{
    _blockConflicts.forEach(s=>_removePlanItem(s._title));
    state.update('availability', a => ({
      ...a,
      [day]: {...a[day], blocks: [...a[day].blocks, {from:f,to:toVal}].sort((x,y)=>toMin(x.from)-toMin(y.from))}
    }));
    avAddOpen[day]=false;
    // 4. PERSIST + 5. RENDER
    cachedResult=null;saveAV();renderAvBlocks();invalidateCalcResult();
  };
  if(_blockConflicts.length) setTimeout(()=>showConflictModal(_blockConflicts,_doAdd),50);
  else _doAdd();
}

export function removeBlock(day,fromVal,toVal){
  // 3. MUTATE
  state.update('availability', a => ({...a, [day]: {...a[day], blocks: a[day].blocks.filter(b=>!(b.from===fromVal&&b.to===toVal))}}));
  // 4. PERSIST + 5. RENDER + UI EFFECTS
  cachedResult=null;
  saveAV();
  renderAvBlocks();
  invalidateCalcResult();
  _checkRecalcOpportunity();
}

export function toggleFullDay(day){
  // 1. READ — UI state (isFullDayBlocked lee availability via free var)
  // 2. GUARD + 3. MUTATE — branch A: libera día
  if(isFullDayBlocked(day)){
    state.update('availability', a => ({...a, [day]: {...a[day], blocks: []}}));
    cachedResult=null;saveAV();renderAvBlocks();invalidateCalcResult();
    _checkRecalcOpportunity();
    return;
  }
  // Branch B: bloquea — con confirm modal si hay conflictos
  const _conflicts=checkPlanConflictsWithBlock(day,'00:00','23:59');
  const _doBlock=()=>{
    _conflicts.forEach(s=>_removePlanItem(s._title));
    state.update('availability', a => ({...a, [day]: {...a[day], blocks: [{from:'00:00',to:'23:59'}]}}));
    avAddOpen[day]=false;
    cachedResult=null;saveAV();renderAvBlocks();invalidateCalcResult();
  };
  if(_conflicts.length) setTimeout(()=>showConflictModal(_conflicts,_doBlock),50);
  else _doBlock();
}

export function _setAvAddOpen(day, val) {
  avAddOpen[day] = val;
  renderAvDay(day);
}

export function showActionToast(msg,actionLabel,actionFn,duration=4000){
  _toastActionFn=actionFn;
  let t=document.getElementById('prio-toast');
  if(!t){t=document.createElement('div');t.id='prio-toast';document.body.appendChild(t);}
  t.className='prio-toast action';_toastArriba(t);
  t.innerHTML=`<span>${msg}</span><button class="toast-action-btn" data-action="dismissToastAction">${actionLabel}</button>`;
  t.style.opacity='1';t.style.pointerEvents='all';
  clearTimeout(t._to);t._to=setTimeout(()=>{t.style.opacity='0';t.style.pointerEvents='none';},duration);
}

export function _dismissToastAction() {
  if (_toastActionFn) {
    _toastActionFn();
    _toastActionFn = null;
    showToast('', 'info', 100);
  }
}

export function lbUrl(title){
  // Use festival-specific slug map from active festival config
  const _cfg=FESTIVAL_CONFIG[_activeFestId]||{};
  const _slugMap=_cfg.lbSlugs||LB_SLUGS;
  const slug=_slugMap[title]||LB_SLUGS[title];
  if(!slug) return null;
  if(slug.startsWith('http')) return slug;
  return`https://letterboxd.com/film/${slug}/`;
}

export function lbUrlForFilm(f){
  if(!f) return null;
  // Guard: el pipeline marca slugs sin resolver con "⚠️ LB PENDIENTE" — un marcador
  // NUNCA es un slug (produciría un href roto). Solo se acepta un slug plausible.
  const s=f.lbSlug;
  if(s && !s.startsWith('⚠') && /^[\w:/.-]+$/.test(s)) return s.startsWith('http')?s:`https://letterboxd.com/film/${s}/`;
  return lbUrl(f.title);
}

export function lbLink(title,film){
  const url=film?lbUrlForFilm(film):lbUrl(title);
  if(!url) return'';
  return`<a class="c-lb pel-sheet-lb" href="${url}" target="_blank" rel="noopener">${LB_SVG}<span class="c-lb-text pel-sheet-lb-text">Letterboxd</span></a>`;
}

export function countryToFlags(countryStr){
  if(!countryStr) return '🌍';
  // Separadores REALES de los datos: coma ("España, Costa Rica, Francia") y barra
  // ("España/Francia"). Antes solo partía por "/" → un string con comas quedaba
  // como una sola clave inexistente y caía al globo pese a tener países mapeados
  // (bug Voces del Territorio, 18 jul). NO se parte por guion: "Guinea-Bissau" es
  // un país. Guardián [country-flags] verifica que todo país de un festival activo
  // produzca bandera. Ver docs/ICONS.md.
  // PARÉNTESIS: varios festivales marcan la coproducción entre paréntesis —
  // "España (Austria)", "República Democrática del Congo (Bélgica, Francia)"
  // (FINCA 2026), "Republic of Korea (South Korea)" (Tribeca). Sin partirlos,
  // TODO el string quedaba como una clave inexistente y caía al globo pese a
  // ser países mapeados. Mismo bug que el de las comas, otro separador.
  const parts=countryStr.split(/[,/()]/).map(s=>s.trim());
  const flags=[...new Set(parts.map(p=>_COUNTRY_FLAGS[p]||'').filter(Boolean))];
  return flags.length?flags.join(''):'🌍';
}

export function filmDisplayTitle(f) {
  // Compone las DOS reglas de título en un solo resolvedor: (1) quitar prefijo de
  // programa vía parseProgramTitle (igual que las listas — antes la ficha mostraba
  // "Cortos: X" mientras las listas mostraban "X"); (2) swap idioma EN/original.
  const _esMain = parseProgramTitle(f.title).displayTitle;
  if (_lang === 'en' && f.title_en && f.title_en !== f.title) {
    const _enMain = f.title_en.replace(/^(Shorts|Cortos|Award Screening):\s*/i, '');
    return { main: _enMain, original: _esMain };
  }
  return { main: _esMain, original: null };
}

export function _genreEN(g) {
  if (!g || _lang !== 'en') return g;
  return g.split(',').map(s => _GENRE_EN[s.trim()] || s.trim()).join(', ');
}

// _avisosBand — DUEÑO ÚNICO de la banda AVISOS, para la ficha de película y la de
// corto. Zona exclusiva de lo que MATIZA la función; lo que la INVALIDA
// (cancelada/reprogramada) se queda dentro de FUNCIÓN, pegado a la hora que niega.
//
// Por qué banda y no avisos sueltos: vivían DENTRO del bloque de FUNCIÓN y
// competían con el día, la hora y la sede — y la palabra "función" aparecía tres
// veces en cuatro líneas. La ficha ya organiza en bandas con rótulo (FUNCIÓN,
// SINOPSIS); los avisos no tenían la suya y vivían de prestado.
//
// Vocabulario, con evidencia (30 jul 2026): "función compartida" y "shared
// screening" NO existen en la industria; lo establecido es "programa" — es como
// los propios festivales llaman al contenedor en NUESTROS datos (FINCA:
// "…— Programa 1", Cinemancia: "Programa de cortos 4", Olhar: "PGM 07"). Y
// "doble" quedó descartado por falso: los slots compartidos llegan a 4 obras y
// mezclan duraciones (106min + 5min en FINCA), así que no hay "doble programa".
//
// `opts.prog`: 'cortos' (corto dentro de un bloque) | 'obras' (slot compartido) |
// null. El texto cambia; la etiqueta es la misma.
export function _avisosBand(f, opts){
  const rows=[];
  // ROJO primero: lo que INVALIDA se lee antes de lo que matiza (DESIGN 8.4.4).
  // `_cancelled` / `_movedFrom` los sella el loader; acá solo se leen.
  (opts&&opts.scrs||[]).forEach(sc=>{
    if(sc._cancelled)
      rows.push([t('badge_cancelada'), t('aviso_cancelada',{info:_coord(sc)}), 'red']);
    else if(sc._movedFrom)
      // La coordenada VIEJA va tachada: la fila de arriba ya muestra la nueva.
      rows.push([t('badge_movida'), t('aviso_movida',{info:`<s>${_coord(sc._movedFrom)}</s>`}), 'red']);
  });
  // `qa_type` distingue los DOS Q&A que el festival programa: con el equipo de
  // la película o con referentes. Rotularlos a todos "equipo" le prometía al
  // usuario un encuentro con los directores que en 7 de 16 funciones de FINCA no
  // ocurre. Sin el campo (resto de festivales) → equipo.
  // Q&A, inscripción y gratis son propiedades de la FUNCIÓN, no de la obra. Se
  // leían del film y por eso la ficha de un CORTO no mostraba el Q&A de su
  // programa: esa ficha no tiene film propio, solo las funciones que hereda.
  // Derivarlos de las funciones sirve a las dos fichas con un solo camino.
  const _src=(opts&&opts.scrs&&opts.scrs.length)?opts.scrs:(f?[f]:[]);
  const _con=k=>_src.filter(x=>x&&x[k]);
  // Si el rasgo está en ALGUNAS funciones y no en todas, el aviso nombra cuáles
  // —si no, mentiría sobre las otras—. FICDEH 2026 lo ejerce en 43 obras, y ahí
  // «sáb 15 · 19:00» no alcanza: lo que separa las dos funciones de «One in a
  // million» (gratis en Medellín, con boleta en Bogotá) es la CIUDAD. Se agrega
  // solo si ESTA obra recorre ≥2 ciudades; si no, sería ruido en cada línea.
  const _ciudades=new Set(_src.map(x=>x&&venueCity(x.venue)).filter(Boolean));
  const _conCiudad=_ciudades.size>1;
  const _cual=h=>(h.length&&h.length<_src.length)?' · '+h.map(x=>_coord(x,_conCiudad)).join(' / '):'';
  const _qa=_con('has_qa');
  if(_qa.length) rows.push(['Q&A', t(_qa[0].qa_type==='guests'?'aviso_qa_ref':'aviso_qa_equipo')+_cual(_qa)]);
  // «Va con otras 4 obras» y no «Verás las otras obras» (ronda 3 del QA, 16 ago):
  // el tiempo verbal describía la SALA —«cuando vayas verás más cosas»— y el
  // usuario lo leyó como dato de la función; por eso marcar una y que quedaran
  // dos marcadas lo tomó por sorpresa. Nombrar el VÍNCULO y su tamaño mantiene
  // el aviso donde vive (la banda de rasgos de la función) y hace que el toast
  // posterior confirme en vez de sorprender. El número es el mismo conjunto que
  // el toast llama «hermanas».
  if(opts&&opts.prog){
    const _n=opts.progN||0;
    const _k=opts.prog==='cortos'?'aviso_prog_cortos':'aviso_prog_obras';
    // 0 = las funciones no coinciden en cuántas compañeras hay → sin número.
    rows.push([t('badge_programa'), _n===0?t(_k+'_s'):_n===1?t(_k+'_1'):t(_k,{n:_n})]);
  }
  const _ins=_con('requires_registration');
  if(_ins.length) rows.push([t('badge_inscripcion'), t('aviso_inscripcion')+_cual(_ins)]);
  // Precio: la ficha dice lo MISMO que la card — ticketBadgeTarget es el dueño
  // único de qué se marca (la minoría). Si la card de una función dice CON
  // BOLETA y su ficha dijera GRATIS, se contradirían.
  const _tb=ticketBadgeTarget();
  if(_tb==='free'){
    const _g=_con('is_free');
    if(_g.length) rows.push([t('badge_gratis'), t('aviso_gratis')+_cual(_g)]);
  } else if(_tb==='paid'){
    const _p=_src.filter(x=>x&&x.is_free!==true);
    if(_p.length) rows.push([t('badge_con_boleta'), t('aviso_con_boleta')+_cual(_p)]);
  }
  if(!rows.length) return '';
  return `<div class="sec-hdr sm">${ICONS.alert} <span>${t('label_avisos')}</span></div>`
    +`<div class="avisos-body">`
    +rows.map(([b,tx,sev])=>`<span class="aviso-pill${sev==='red'?' sev-red':''}">${b}</span><span class="aviso-txt">${tx}</span>`).join('')
    +`</div>`;
}

// _coord — "jue 13 · 19:00": cómo la app nombra una función dentro de una FRASE.
// dayLabel devuelve el día en mayúsculas porque en la fila es una etiqueta; dentro
// de una oración, "JUE 13" grita. Se baja a minúsculas solo acá.
function _coord(sc, conCiudad){
  const d=sc.day?(dayLabel(sc.day)||sc.day).toLocaleLowerCase():'';
  // La ciudad va PRIMERO: es el dato más grueso. Solo cuando desambigua (ver _cual).
  const c=conCiudad?venueCity(sc.venue):'';
  return [c, d, sc.time||''].filter(Boolean).join(' · ');
}

export function _checkRecalcOpportunity(){
  if(!savedAgenda||!savedAgenda.schedule.length) return;
  const planTitles=new Set(savedAgenda.schedule.map(s=>s._title));
  const candidates=[...watchlist].filter(t=>!planTitles.has(t)&&!watched.has(t));
  const hasOpportunity=candidates.some(t=>{
    // El aviso ofrece algo para AGREGAR AL PLAN → mismo predicado que el plan
    // (si no, ofrece una oportunidad en una ciudad que el filtro descartó).
    return plannableScreens(t).length>0;
  });
  if(hasOpportunity){
    showActionToast(t('toast_horario_lib'),'Recalcular',()=>{
      switchMainNav('mnav-planner');showAgView();setTimeout(runCalc,300);
    },5000);
  }
}

export function _removePlanItem(title){
  if(!savedAgenda) return;
  const removed=savedAgenda.schedule.find(s=>s._title===title);
  if(removed){
    state.update('lastRemovedSlots', arr => [{...removed,_isRestored:true}, ...arr.filter(r=>r._title!==removed._title)].slice(0,MAX_REMEMBERED_SLOTS));
    saveLastSlot();
  }
  commitPlan(a=>{const sch=a.schedule.filter(s=>s._title!==title);return sch.length?{...a,schedule:sch}:null;});
  saveSavedAgenda();
}

export function checkPlanConflictsWithBlock(day, fromStr, toStr){
  if(!savedAgenda||!savedAgenda.schedule.length) return[];
  const bFrom=toMin(fromStr), bTo=toMin(toStr);
  return savedAgenda.schedule.filter(s=>{
    if(s.day!==day) return false;
    const sStart=toMin(s.time), sEnd=sStart+blockDuration(s); // SIN Q&A, emparejado con isScreeningBlocked (doctrina 30 jul)
    return sStart<bTo&&sEnd>bFrom;
  });
}

export function invalidateCalcResult(){
  // Called when availability changes — resets result prompt
  const _wrap=document.getElementById('ag-result-wrap');
  if(_wrap) _wrap.style.display='none';
  const res=document.getElementById('ag-result');
  if(!res){showAgView();return;}
  res.innerHTML='';
}

export function savePVRating(){
  // 1. READ — UI state ephemeral (_pvRating, _pvTitle son module-level)
  // 2. GUARD — solo guardar si rating válido
  if(_pvRating>0){
    // 3. MUTATE + 4. PERSIST — saveRating es el camino canónico: persiste Y sube a la
    // nube (_cloudSave). Antes esto escribía storage directo → las calificaciones
    // post-vista quedaban SOLO locales (no llegaban a la nube ni al Watch). Dato
    // valioso del cinéfilo: siempre sincroniza.
    saveRating(_pvTitle,_pvRating);
    if(_pvQueue){ _pvRatedCount++; }
    else{
      const stars=['','★','★★','★★★','★★★★','★★★★★'];
      showToast(stars[Math.round(_pvRating)]||t('toast_calificada'),'info');
    }
  }
  // Cola de programa: avanzar a la siguiente obra; el toast del conteo va al final.
  if(_pvQueue&&_pvQueueIdx<_pvQueue.length-1){
    _pvQueueIdx++;
    _pvShowCurrent();
    return;
  }
  _pvFinish();
  // Render automático vía pipeline (filmRatings). Si rating=0 no hay mutación →
  // no re-render (no-op visual: el prompt de calificar sigue igual).
}

// pvLater — el botón "Después". En cola: SALTA la obra actual sin calificar (quizás
// no querés calificar la 1 pero sí la 2) y avanza; en la última, cierra. Film suelto:
// cierra como siempre. La salida total sigue libre: tap afuera / back cierran todo.
export function pvLater(){
  if(_pvQueue&&_pvQueueIdx<_pvQueue.length-1){
    _pvQueueIdx++;
    _pvShowCurrent();
    return;
  }
  _pvFinish();
}

// _pvFinish — cierre de la cola (o del film suelto): toast con el conteo si se
// calificó algo ("2 películas calificadas") y reset del estado de cola.
function _pvFinish(){
  if(_pvQueue&&_pvRatedCount>0){
    showToast(_pvRatedCount===1?t('pv_calif_1'):t('pv_calif_n',{n:_pvRatedCount}),'info');
  }
  _pvQueue=null;
  closePVRating();
  _refreshDiaryIfOpen();
}
