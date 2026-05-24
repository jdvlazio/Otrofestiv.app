// ── src/main.js — Fase 8 (módulo ES) ─────────────────────────────────────────
// Relocación de los blocks 3+4 de index.html (app + bootstrap).
// Step 0 = relocación a módulo. Steps 1-5 extraen las capas e importan los
// módulos (config ✓ Step 1 · state ✓ Step 2 · storage/i18n/domain → Steps 3-5).
// Cargado vía <script type="module" src="/src/main.js"> en index.html.
// SW: regla network-first /src/ garantiza que el deploy propaga (D-INFRA-1=B).

// ── Step 1: config.js (import directo, sin bridge — constantes estáticas) ─────
import {
  TMDB_IMG, TMDB_API_BASE, TMDB_POSTER_BASE, _POSTER_CACHE_PFX,
  FESTIVAL_BUFFER, MAX_REMEMBERED_SLOTS, DEFAULT_DURATION_MIN,
  SECTION_ORDER_LIST, FILM_CATEGORY_ORDER, FILM_CATEGORY_LABEL, SECTION_COLORS,
  NOTICES, FESTIVAL_CONFIG, VENUES, _DEFAULT_FEST_ID,
} from './config.js';

// ── Step 2: state.js (import + bridge — D-INFRA-4: mirror eliminado) ──────────
import { state } from './state/state.js';

// ── Step 3: storage.js (import — adapter de localStorage; usa el bridge para
//   FESTIVAL_STORAGE_KEY). saveX/loadState orquestadoras se quedan en main.js. ──
import { storage } from './storage/storage.js';

// ── Step 4: i18n.js (import — _I18N + t + _applyI18nDOM). _lang vive en state
//   (bridge); su init y setLang se quedan en main.js. ──────────────────────────
import { _I18N, t, _applyI18nDOM } from './i18n/i18n.js';

// ── Step 5: domain/ (funciones puras). Importan config (DEFAULT_DURATION_MIN,
//   FESTIVAL_BUFFER, FESTIVAL_CONFIG) y leen festival-state vía bridge. El worker
//   las consume vía eval(name).toString(); sus copias worker-local se quedan. ──
import { toMin, parseDur, minToStr, _festDate, simNow, simTodayStr, dayFullyPassed, festivalEnded } from './domain/time.js';
import { _djb2, _titleSeed, _mulberry32, shuffle, scoreFilm, effectiveDuration, screeningPassed, _classifyTodayScreenings, _endedStats } from './domain/film.js';
import { screensConflict, isScreeningBlocked, sortScreensByStrategy, computeScenarios } from './domain/schedule.js';
import { _resolveVenue, _gapSuggestion, _getFestivalPhase, venueTravelMins, travelMins } from './domain/festival.js';

// ── Step 6a: view/components.js — capa presentacional foundational de Wave 6
//   (posters, builders HTML puros, helpers sección/rating/festival). ──────────
import {
  ICONS, CHECK_SVG, DAY_ABBR, DAY_NUM,
  makeProgramPoster, makeEventPoster, makeSorpresaPoster, _buildPosterV16,
  _secLabel, _sectionColor, renderRatingStarsHTML, starSVG,
  _renderSplashDropdownHTML, _renderFestivalSelectorHTML, _classifyFestival,
  _sortFestivals, renderAvBlocksHTML, isFullDayBlocked, renderFlowProgress,
  buildResultHTML, parseProgramTitle,
} from './view/components.js';

// ── Step 6b: view/sheets.js (lifecycle de paneles) + view/feedback.js
//   (notificaciones: toasts/modales/sim-label). ───────────────────────────────
import {
  openAuthSheet, closeAuthSheet, closeAvSheet, openFestivalSheet,
  closeFestivalSheet, closePVRating, closePrioLimit, _showSignedInSheet,
} from './view/sheets.js';
import {
  _SIM_TOTAL, _showModal, _simFestStart, _simFestEnd,
  showToast, showActionModal, showConflictModal, updateSimLabel,
} from './view/feedback.js';

// ── Step 6c: view/programa.js — builders del programa view (notices + chips).
//   Scope STRICT; el programa render pesado va a Wave 7 (controller). ──────────
import {
  getActiveNotices, _computeProgramaChips, renderNoticesBannerHTML,
  renderProgramaChipsHTML, renderNoticesBanner,
} from './view/programa.js';

// ── Step 6h: programa.js cartelera render (render, lugar overlay). ────────────
import {
  render, lugarClose, lugarOutside,
} from './view/programa.js';

// ── Step 6g: programa.js render dispatchers (8 fns). ─────────────────────────
import {
  _renderProgramaContent, renderProgramaChips, renderPeliculaView,
} from './view/programa.js';

// ── Step 6e: view/helpers.js — shared view helpers (posters, labels, formato).
//   Lets DAY_SHORT/_EN/_CUSTOM_N/_POSTERS_N viven allá (module-owned); main.js
//   los re-popula vía setters. ──────────────────────────────────────────────
import {
  _posterStyle, getPosterSrc, getFilmPoster, getCortoItemPoster, _getItemPoster, _isEditorialPoster, _posterThumb, isNowShowing, isToday, vcfg, sala, travelWarn, mplanEndStr, mplanBlockType, dayChip, dayLabel, _lblLocalized, durFmt, flagFmt, _langDates, _mkCortoItemHtml, starsText, _dayChips, _metaBadges, _programaStack, _plistPosterHtml, DAY_SHORT_EN,
  setDayShort, setDayShortEn, setPosters, setCustomPosters,
  emptyState, emptyStateHero, DAYS,
} from './view/helpers.js';

// ── Step 6f: view/agenda.js — render de agenda+miplan (18 fns). ───────────────
import {
  renderAgenda, renderMiPlanCalendar, renderUnconfirmed, renderFilmAlternatives, renderContextualHeader, renderPrioStrip, renderFilmListHTML, renderSavedAgendaHTML, renderAvBlocks, updateCardState, updateHorarioPrioBtn, _fixStickyOffset, _scrollMiPlanToNow, _updateMiPlanBadge,
} from './view/agenda.js';

// storage (adapter de localStorage) → src/storage/storage.js (Step 3).
// Importado al top del módulo. Usa FESTIVAL_STORAGE_KEY vía el STATE BRIDGE.

// ── STATE BRIDGE START (p8 Step 2) ───────────────────────────────────
// D-INFRA-4: el mirror fue ELIMINADO (ver src/state/state.js). El container
// `state` (importado) posee _data; este bridge expone los 19 globals del roster
// como propiedades de globalThis respaldadas por state.get/set. Una dirección:
//   read  `watchlist.has(x)`  → globalThis.watchlist getter → state.get('watchlist')
//   write `watchlist = nuevo` → globalThis.watchlist setter → state.set('watchlist', …)
//                               → dispara subscribers + render pipeline (7d)
// Instalado TEMPRANO (antes de cualquier init del roster): las (ex-)decls
// `let X = init` pasaron a `X = init` bare, que rutean por aquí.
// ⚠ El bridge DEBE preceder a la primera asignación bare del roster — en módulo
//   ESM (strict), `X = v` sin declaración requiere que globalThis.X exista.
// validate.py [state-mirror]: verifica que estos 19 keys estén bridged y que
//   ningún roster key se redeclare (let/const/var) en main.js (anti-shadowing).
const _BRIDGE_KEYS = [
  'watchlist', 'watched', 'prioritized', 'filmRatings', 'filmDelays',
  'filmDelaysHistory', 'savedAgenda', 'availability', 'lastRemovedSlots',
  '_lang', '_simTime', 'FILMS', 'FESTIVAL_DATES', 'FESTIVAL_END', 'PRIO_LIMIT',
  'TZ_OFFSET', 'FESTIVAL_TRANSPORT', '_activeFestId', 'FESTIVAL_STORAGE_KEY',
];
_BRIDGE_KEYS.forEach(k => Object.defineProperty(globalThis, k, {
  get: () => state.get(k),
  set: v => state.set(k, v),
  configurable: true,
}));
// ── STATE BRIDGE END (p8 Step 2) ─────────────────────────────────────

// ── CONTROLLER LAYER START (p7c-1) ───────────────────────────────────
// Foundation del event delegation system. ACTION_REGISTRY mapea
// data-action attributes a sus handlers. Delegated listener captura
// clicks a nivel document y dispatcha.
//
// Componentes:
//   1. Composite helpers (11) — encapsulan patrones multi-statement
//      detectados durante auditoría de onclick. Usados por 7c-3
//   2. ACTION_REGISTRY (97 entries categorías A-G) — schema completo
//   3. Delegated listener + data-close-bg infra
//
// Decisión D4 (validate.py): foundation completa up-front. Composite
// helpers + entries no consumidos hasta 7c-3/4 quedan dead-loaded
// (validate check tolera composite helpers dead).

// ── 1. Composite helpers (consumed por ACTION_REGISTRY G + 7c-3/4) ──

function _scrollToAgSection(id) {
  const el = document.getElementById(id);
  if (!el) return;
  const hdr = document.getElementById('hdr-ag');
  const off = hdr ? hdr.getBoundingClientRect().bottom : 0;
  const y = el.getBoundingClientRect().top + window.scrollY - off - 8;
  window.scrollTo({top: y, behavior: 'smooth'});
}

function _setExpandedFilm(val) {
  _expandedFilm = val;
  renderAgenda();
}

function _setAvAddOpen(day, val) {
  avAddOpen[day] = val;
  renderAvDay(day);
}

function _closePelAndRemove(title) {
  closePelSheet();
  removeFromAgenda(title);
}

function _closePelAndRate(title) {
  closePelSheet();
  setTimeout(() => openRatingSheet(title), 100);
}

function _navTo(tab) {
  if (tab === 'mnav-cartelera') {
    const _ph = _getProgramaPhase();
    programaSubMode = _ph.default;
    switchMainNav(tab);
    showDayView();
  } else {
    switchMainNav(tab);
    showAgView();
  }
}

function _closeAuthAndReset() {
  closeAuthSheet();
  const step1 = document.getElementById('auth-sheet-step1');
  const step2 = document.getElementById('auth-sheet-step2');
  if (step1) step1.style.display = 'block';
  if (step2) step2.style.display = 'none';
}

function _dismissToastAction() {
  if (_toastActionFn) {
    _toastActionFn();
    _toastActionFn = null;
    showToast('', 'info', 100);
  }
}

function _toggleCtxOlder() {
  const el = document.getElementById('ctx-older');
  if (!el) return;
  el.style.display = el.style.display === 'none' ? 'block' : 'none';
}

function _toggleWatchedAndClose(title, e) {
  toggleWatched(title, e);
  closePelSheet();
}

function _toggleWLAndClose(title, e) {
  toggleWL(title, e);
  closePelSheet();
}

function _activatePlanFilm(el) {
  setActivePlanFilm(el);
  const i = parseInt(el.dataset.dayIndex, 10);
  if (!isNaN(i)) selectMiPlanDay(i);
}

function _scrollToSuggestions() {
  document.querySelector('.suggestion-wrap')?.scrollIntoView({behavior:'smooth', block:'start'});
}

function _removeConflictModal() {
  document.getElementById('conflict-modal')?.remove();
}

function _scrollToTop() {
  window.scrollTo({top:0, behavior:'smooth'});
}

function _searchOpenFilm(title) {
  searchClose();
  openPelSheet(title);
}

function _searchOpenCorto(title, country, dur, section, flags) {
  searchClose();
  openCortoSheet(title, country, dur, section, flags);
}

// ── 2. ACTION_REGISTRY — mapping data-action → handler ────────────────
// 97 entries totales en 7 categorías. Cada entry sabe cómo extraer args
// del DOM element (dataset attributes).
// Usage en HTML: el data-action attribute identifica el handler en el
// registry. Args adicionales via data-* attributes leídos por el handler.
// Si necesita stopPropagation: añadir data-stop="1" al elemento.
// Note: ACTION_REGISTRY se evalúa con tiempo de definición — las funciones
// invocadas se resuelven por nombre (late binding via global lookup).
const ACTION_REGISTRY = {
  // ── A: Action handlers (Fase 7a) + state mutators (21) ──
  toggleWL:           (el, e) => toggleWL(el.dataset.title, e),
  toggleWatched:      (el, e) => toggleWatched(el.dataset.title, e),
  togglePriority:     (el)    => togglePriority(el.dataset.title),
  togglePelPrio:      (el)    => togglePelPrio(el.dataset.title),
  togglePelWL:        (el, e) => togglePelWL(el.dataset.title, e),
  toggleFullDay:      (el)    => toggleFullDay(el.dataset.day),
  removeBlock:        (el)    => removeBlock(el.dataset.day, el.dataset.from, el.dataset.to),
  addBlock:           (el)    => addBlock(el.dataset.day),
  confirmAvBlock:     ()      => confirmAvBlock(),
  confirmReplace:     (el)    => confirmReplace(el.dataset.rmtitle, el.dataset.newtitle, el.dataset.day, el.dataset.time),
  removeFromAgenda:   (el)    => removeFromAgenda(el.dataset.title),
  setDelay:           (el)    => setDelay(el.dataset.title, el.dataset.day, el.dataset.time, +el.dataset.mins),
  clearDelay:         (el)    => clearDelay(el.dataset.title, el.dataset.day, el.dataset.time),
  undoDelay:          (el)    => undoDelay(el.dataset.title, el.dataset.day, el.dataset.time),
  checkinLaVi:        (el)    => checkinLaVi(el.dataset.title),
  checkinNoLaVi:      (el)    => checkinNoLaVi(el.dataset.title),
  savePVRating:       ()      => savePVRating(),
  setLang:            (el)    => setLang(el.dataset.code),
  forceInclude:       (el)    => forceInclude(el.dataset.title),
  _dismissNotice:     (el)    => _dismissNotice(el.dataset.title),
  swapPriority:       (el)    => swapPriority(el.dataset.rmtitle, el.dataset.addtitle),

  // ── B: Sheets open/close (26) ──
  openAvSheet:           ()      => openAvSheet(),
  openAuthSheet:         ()      => openAuthSheet(),
  openFestivalSheet:     ()      => openFestivalSheet(),
  openRatingSheet:       (el)    => openRatingSheet(el.dataset.title),
  openCortoSheetFromEl:  (el, e) => openCortoSheetFromEl(el, e),
  closePelSheet:         ()      => closePelSheet(),
  closeAuthSheet:        ()      => closeAuthSheet(),
  closeAvSheet:          ()      => closeAvSheet(),
  closeConflictSheet:    ()      => closeConflictSheet(),
  closeFestivalSheet:    ()      => closeFestivalSheet(),
  closeRatingSheet:      ()      => closeRatingSheet(),
  closePVRating:         ()      => closePVRating(),
  closePlanConfirm:      (el)    => closePlanConfirm(el.dataset.force === '1'),
  closePrioLimit:        ()      => closePrioLimit(),
  dismissSplash:         ()      => dismissSplash(),
  toggleSplashDropdown:  ()      => toggleSplashDropdown(),
  searchOpen:            ()      => searchOpen(),
  searchClose:           ()      => searchClose(),
  _togglePastFest:       (el)    => _togglePastFest(el),
  _togglePastFestRow:    (el)    => _togglePastFestRow(el.closest('.fs-festival-row'), el.dataset.fest),
  openPostViewRating:    (el)    => openPostViewRating(el.dataset.title, el.dataset.day, el.dataset.time, el.dataset.venue, el.dataset.duration),
  selectSplashFest:      (el)    => selectSplashFest(el.dataset.name, el.dataset.meta, el.dataset.fest),
  selectFromDetail:      (el)    => selectFromDetail(el),
  _openCombinedFilmSheet:(el)    => _openCombinedFilmSheet(JSON.parse(el.dataset.film)),
  searchOpenFilm:        (el)    => _searchOpenFilm(el.dataset.title),
  searchOpenCorto:       (el)    => _searchOpenCorto(el.dataset.title, el.dataset.country, el.dataset.dur, el.dataset.section, el.dataset.flags),

  // ── C: Navigation (12) ──
  switchMainNav:       (el)    => switchMainNav(el.dataset.nav),
  miPlanNav:           (el)    => miPlanNav(el.dataset.dir),
  selectMiPlanDay:     (el)    => selectMiPlanDay(+el.dataset.index),
  setProgramaMode:     (el)    => setProgramaMode(el.dataset.mode),
  setProgramaChip:     (el)    => setProgramaChip(el.dataset.chip),
  setAvType:           (el)    => setAvType(el.dataset.type),
  setInteresesView:    (el)    => setInteresesView(el.dataset.mode),
  toggleProgramaView:  ()      => toggleProgramaView(),
  lugarToggle:         ()      => lugarToggle(),
  seccionToggle:       ()      => seccionToggle(),
  selectAvDay:         (el)    => selectAvDay(el.dataset.day),
  navTo:               (el)    => _navTo(el.dataset.tab),

  // ── D: Cartelera/Programa filters + DOM utils (13) ──
  filterBySection:     (el)    => filterBySection(el.dataset.section),
  filterByVenue:       (el)    => filterByVenue(el.dataset.venue),
  _pafClearSec:        ()      => _pafClearSec(),
  _pafClearVenue:      ()      => _pafClearVenue(),
  _toggleEveningFilms: (el)    => _toggleEveningFilms(el),
  _toggleWLFromList:   (el)    => _toggleWLFromList(el.dataset.title, el),
  addSuggestion:       (el)    => addSuggestion(el.dataset.title, el.dataset.day, el.dataset.time),
  clearProgramaChip:   ()      => clearProgramaChip(),
  runCalc:             ()      => runCalc(),
  toggleArchive:       ()      => toggleArchive(),
  scrollToSuggestions: ()      => _scrollToSuggestions(),
  removeConflictModal: ()      => _removeConflictModal(),
  scrollToTop:         ()      => _scrollToTop(),

  // ── E: Mi Plan / Schedule actions (10) ──
  jumpToScenario:        (el)    => jumpToScenario(+el.dataset.index),
  saveCurrentScenario:   ()      => saveCurrentScenario(),
  removeFilmFromScenario:(el)    => removeFilmFromScenario(el.dataset.title),
  setActivePlanFilm:     (el)    => setActivePlanFilm(el),
  toggleFilmAlternatives:(el)    => toggleFilmAlternatives(el.dataset.key, el.dataset.title, el.dataset.day, el.dataset.time),
  toggleMplanProg:       (el, e) => toggleMplanProg(el, e),
  markWatchedFromPlan:   (el, e) => markWatchedFromPlan(el.dataset.title, el.dataset.day, el.dataset.time, el.dataset.venue, el.dataset.dur, e),
  sharePlan:             ()      => sharePlan(),
  exportICS:             ()      => exportICS(),
  loadFestival:          (el)    => loadFestival(el.dataset.fest),

  // ── F: Auth (4) ──
  submitAuthEmail:  ()    => submitAuthEmail(),
  submitOTP:        ()    => submitOTP(),
  deleteAccount:    ()    => deleteAccount(),
  signOutAndClose:  ()    => signOutAndClose(),

  // ── G: Composite helpers (Patrones A-J multi-statement) (11) ──
  scrollToAgSec:        (el)    => _scrollToAgSection(el.dataset.target),
  clearExpandedFilm:    ()      => _setExpandedFilm(''),
  setAvAddOpen:         (el)    => _setAvAddOpen(el.dataset.day, el.dataset.open === '1'),
  closePelAndRemove:    (el)    => _closePelAndRemove(el.dataset.title),
  closePelAndRate:      (el)    => _closePelAndRate(el.dataset.title),
  closeAuthAndReset:    ()      => _closeAuthAndReset(),
  dismissToastAction:   ()      => _dismissToastAction(),
  toggleCtxOlder:       ()      => _toggleCtxOlder(),
  toggleWatchedAndClose:(el, e) => _toggleWatchedAndClose(el.dataset.title, e),
  toggleWLAndClose:     (el, e) => _toggleWLAndClose(el.dataset.title, e),
  activatePlanFilm:     (el)    => _activatePlanFilm(el),
};

// ── 3. Delegated click listener + data-close-bg infra ────────────────
// Captura clicks a nivel document. Walking-up manual desde el target:
// el primer ancestor con data-action dispara su handler. Un wrapper con
// data-stop="1" (sin data-action) encontrado ANTES bloquea el lookup del
// action ancestro (y detiene propagation) — patrón usado por wrappers que
// solo previenen que un handler ancestro se dispare.
//
// data-stop="1": en un elemento con data-action → stopPropagation antes del
//   handler. En un wrapper sin data-action → bloquea action ancestro + stop.
// data-close-bg="X": si click directo en este elemento (no en hijo),
//   dispara close<X>() (e.g., data-close-bg="AvSheet" → closeAvSheet)
//
// Walking-up manual (no closest()) para que un wrapper data-stop pueda
// interceptar antes de alcanzar un data-action ancestro.
document.addEventListener('click', function(e) {
  let node = e.target;
  while (node && node !== document) {
    if (node.dataset) {
      if (node.dataset.action) {
        if (node.dataset.stop === '1') e.stopPropagation();
        const handler = ACTION_REGISTRY[node.dataset.action];
        if (handler) handler(node, e);
        return;
      }
      if (node.dataset.stop === '1') {
        e.stopPropagation();
        return;
      }
    }
    node = node.parentElement;
  }
  // close-on-background-click: solo si click directo en el overlay (no propagado de hijo)
  const bg = e.target.closest('[data-close-bg]');
  if (bg && e.target === bg) {
    const closeName = 'close' + bg.dataset.closeBg;
    const closeFn = ACTION_REGISTRY[closeName];
    if (closeFn) closeFn();
  }
});
// ── CONTROLLER LAYER END (p7c-1) ──────────────────────────────────────

// ── i18n — sistema de traducción ─────────────────────────────────────────
// Idioma determinado por preferencia del usuario, persistido en localStorage.
// Cambio de idioma: setLang(code) escribe localStorage y recarga la app.
// El contenido del festival (títulos, sinopsis, secciones) NO se traduce —
// se muestra en el idioma en que está escrito en el JSON del festival.
// _I18N (diccionarios es/en) → src/i18n/i18n.js (Step 4). Importado.

_lang = (()=>{
  const saved = storage.getLang();
  if(saved && _I18N[saved]) return saved;
  // Auto-detect por idioma del navegador — solo en primer uso
  const nav = (navigator.language || navigator.userLanguage || 'es').toLowerCase();
  return nav.startsWith('en') ? 'en' : 'es';
})();

// t(key, params) → src/i18n/i18n.js (Step 4). Importado.

// Controller (p7a) — VARIANT aceptada: fade animation + delayed mutate dentro
// del setTimeout. Pattern 5-pasos NO se aplica literal (mutate diferido tras
// fade-out animation). Documentada como variant en spec/plan.
function setLang(code){
  // 1. READ + 2. GUARD
  const {_lang, _activeFestId} = state.snapshot();
  if(!_I18N[code]) return;
  if(code === _lang) return;
  // Fade out content containers (UI effect inmediato)
  const _fadeEls=['programa-list','ag-view','grid'].map(id=>document.getElementById(id)).filter(Boolean);
  _fadeEls.forEach(el=>el.classList.add('lang-fade'));
  setTimeout(()=>{
    // 3. MUTATE (diferido tras fade-out)
    state.set('_lang', code);
    // 4. PERSIST
    storage.setLang(code);
    // 5. RENDER + UI EFFECTS — full DOM refresh + componentes dinámicos
    _applyI18nDOM();
    if(activeView === 'day') { typeof showDayView === 'function' && showDayView(); }
    else                     { typeof renderAgenda === 'function' && renderAgenda(); }
    _renderSplashDropdown(_splashSelectedFestId||_DEFAULT_FEST_ID);
    _renderFestivalSelector(_activeFestId);
    requestAnimationFrame(()=>{
      _fadeEls.forEach(el=>el.classList.remove('lang-fade'));
    });
  }, 200); // --tr-smooth = 200ms
}

// ── Fin i18n ──────────────────────────────────────────────────────────────

// _applyI18nDOM() → src/i18n/i18n.js (Step 4). Importado.

// ── Capgo: confirma que el bundle cargó correctamente ──────────
// Sin esta llamada, Capgo hace rollback automático a los 10s.
// El guard ?. asegura que en web (GitHub Pages) no hay error.
if(window.Capacitor?.Plugins?.CapacitorUpdater){
  window.Capacitor.Plugins.CapacitorUpdater.notifyAppReady();
}

// ═══════════════════════════════════════════════════════════════
// 1 · DATOS DEL FESTIVAL
//     FILMS, POSTERS, CUSTOM_POSTERS
// ═══════════════════════════════════════════════════════════════
FILMS=[];
let POSTERS={};
let CUSTOM_POSTERS={};

// ── Timezone helper — festival-aware date construction ────────────────────
// TZ_OFFSET se actualiza en loadFestival() desde cfg.timezoneOffset.
// Default '-05:00' = Colombia. Festivals internacionales usan su propio offset.
// Ejemplo: Tribeca NYC junio = '-04:00'
TZ_OFFSET='-05:00';
// FESTIVAL_TRANSPORT: modo de movilización del festival activo.
// Valores: 'transit' (Uber/Metro) · 'walking' (a pie) · 'mixed' (depende de la sede)
// Afecta el texto de aviso de viaje en Mi Plan. Se actualiza en loadFestival().
FESTIVAL_TRANSPORT='transit';
// _festDate(dateStr, time) → Date — construye Date con TZ_OFFSET explícito.
// Lee (contrato implícito): TZ_OFFSET (offset del festival activo, e.g. '-05:00').
// Inputs: dateStr en formato YYYY-MM-DD, time en formato HH:mm.
// Returns: Date object cuyo valor representa dateStr+time en la TZ del festival.
// En _SCHED_PURE_FNS: el worker la consume vía .toString() con la misma TZ_OFFSET inyectada.
// _festDate → src/domain/time.js (Step 5). Importado.
/* TMDB: key vacía en producción — las funciones de enriquecimiento
   degradan silenciosamente. Para enriquecer posters localmente:
   TMDB_API_KEY en scripts/enrich-festival.py (no commit al repo público).
   Rotar key en: https://www.themoviedb.org/settings/api */
const TMDB_API_KEY='';

/* ── POSTER GENERATIVO — identidad Otrofestiv para programas ──────────
   REGLA CANÓNICA — nunca romper sin justificación explícita:

   PRIORIDAD DE POSTER (en todo contexto — grilla, card, Mi Plan):
     1. Poster real (CUSTOM_POSTERS > POSTERS/TMDB)
     2. Poster generativo (solo si no hay real)
     3. Placeholder vacío (surf-2) — nunca negro

   TIPOS DE POSTER GENERATIVO — mismo _buildPosterSVG, misma plantilla:
     · Competencia cortos → header teal  · l1:'COMPETENCIA' · l2:'CORTOMETRAJES'
     · Programa cortos   → header teal  · l1:'PROGRAMA'    · l2:'CORTOMETRAJES'
     · Evento/Industry   → header ámbar · l1:'INDUSTRY'    · l2:'DAYS'

   REGLA DE DETECCIÓN:
     f.type === 'event'  → makeEventPoster()
     f.is_cortos === true → getPosterSrc(title,true) || makeProgramPoster(title,dur,section)
     resto               → getPosterSrc(title,false) || null

   ONERROR: siempre this.remove() — nunca this.style.opacity=0
   TÍTULO: limpiar prefijos redundantes en makeProgramPoster()
────────────────────────────────────────────────────────────────────── */
function _buildPosterSVG(o){
  // ── Poster generativo 120×180px — guía de diseño ────────────────────
  // Canvas: 120×180 · fondo #1E1B17
  // Header: h=38px · 1 línea y=22 centrado · 2 líneas y=15/y=27
  // Header font: 8px bold · letter-spacing 0.8 · color: ht token
  // Separador: y=38 h=1px · color: sep token
  // Inner box: x=10 y=46 w=100 h=124 rx=3 · padding lateral 10px
  // Título: adaptativo 10px(≤3L LD13) 9px(≤5L LD12) 8px(≤9L LD11)
  //   split guiones: "Investigación-Creación" → "Investigación-"+"Creación"
  //   max chars/línea: 10px→13 · 9px→15 · 8px→17
  // Duración: y=158 fijo · 8px · color: accent token
  // Footer: y=164 h=16 fondo #161310 · festival name y=175 6px color #5A4E40
  const VW=120,VH=180,HDR_H=38,BX=10,BY=46,BW=VW-20,BH=VH-56,FY=VH-16,DUR_Y=158;

  // 1. Split hyphenated compounds: "Investigación-Creación" → ["Investigación-","Creación"]
  const rawWords=(o.title||'').split(/\s+/);
  const words=[];
  rawWords.forEach(w=>{
    const parts=w.split(/-(?=\S)/);
    parts.forEach((p,i)=>words.push(i<parts.length-1?p+'-':p));
  });
  // 2. Adaptive font — try smallest MAX first, step up if lines exceed budget
  const fontConfigs=[{MAX:13,fs:10,ld:13,maxLines:3},{MAX:15,fs:9,ld:12,maxLines:5},{MAX:17,fs:8,ld:11,maxLines:9}];
  let ls=[],FS=10,LD=13;
  for(const cfg of fontConfigs){
    const raw=[];let c='';
    for(const w of words){
      if(c&&(c+' '+w).length>cfg.MAX){raw.push(c);c=w;}
      else c=c?c+' '+w:w;
    }
    if(c)raw.push(c);
    ls=[];
    raw.forEach(l=>{
      if(l.length>cfg.MAX){for(let i=0;i<l.length;i+=cfg.MAX)ls.push(l.slice(i,i+cfg.MAX));}
      else ls.push(l);
    });
    FS=cfg.fs;LD=cfg.ld;
    if(ls.length<=cfg.maxLines||cfg.fs===8)break;
  }

  // 3. Centre title block in fixed zone
  const TITLE_ZONE_TOP=54,TITLE_ZONE_BOT=o.duration?148:158;
  const tzc=Math.round((TITLE_ZONE_TOP+TITLE_ZONE_BOT)/2);
  const sY=tzc-Math.round(ls.length*LD/2)+LD-4;
  const tl=ls.map((l,i)=>`<text x="${VW/2}" y="${sY+i*LD}" text-anchor="middle" font-family="-apple-system,BlinkMacSystemFont,sans-serif" font-size="${FS}" font-weight="700" fill="#F0EBE0">${l}</text>`).join('');
  const dT=o.duration?`<text x="${VW/2}" y="${DUR_Y}" text-anchor="middle" font-family="-apple-system,BlinkMacSystemFont,sans-serif" font-size="8" font-weight="500" fill="${o.accent}">${o.duration}</text>`:'';

  // 4. Header: centre l1 vertically when l2 is absent
  const hasL2=o.l2&&o.l2.trim();
  const l1y=hasL2?15:22;
  const l2el=hasL2?`<text x="${VW/2}" y="27" text-anchor="middle" font-family="-apple-system,BlinkMacSystemFont,sans-serif" font-size="8" font-weight="700" fill="${o.ht}" letter-spacing="0.8">${o.l2}</text>`:'';

  const svg=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${VW} ${VH}">
    <rect width="${VW}" height="${VH}" fill="#1E1B17"/>
    <rect x="0" y="0" width="${VW}" height="${HDR_H}" fill="${o.hc}"/>
    <rect x="0" y="${HDR_H}" width="${VW}" height="1" fill="${o.sep}"/>
    <text x="${VW/2}" y="${l1y}" text-anchor="middle" font-family="-apple-system,BlinkMacSystemFont,sans-serif" font-size="8" font-weight="700" fill="${o.ht}" letter-spacing="0.8">${o.l1}</text>
    ${l2el}
    <rect x="${BX}" y="${BY}" width="${BW}" height="${BH}" rx="3" fill="${o.bf}" stroke="${o.bs}" stroke-width="1"/>
    ${tl}
    ${dT}
    <rect x="0" y="${FY}" width="${VW}" height="16" fill="#161310"/>
    <text x="${VW/2}" y="${VH-5}" text-anchor="middle" font-family="-apple-system,BlinkMacSystemFont,sans-serif" font-size="6" font-weight="500" fill="#5A4E40" letter-spacing="1">${o.ft}</text>
  </svg>`;

  return `data:image/svg+xml,${encodeURIComponent(svg)}`;
}

// makeProgramPoster → src/view/components.js (Step 6a). Importado.
/* ══════════════════════════════════════════════════════
   SISTEMA DE PÓSTERS — fuente unificada y normalizada
   ─────────────────────────────────────────────────────
   FUENTES (en orden de prioridad):
     1. CUSTOM_POSTERS  — URLs manuales por festival (posters de cortos individuales incluidos)
     2. POSTERS         — features: URLs completas (TMDB o CDN propio)

   NORMALIZACIÓN:
     normKey(s) → convierte apostrofes Unicode → ASCII (U+0027)
     Se aplica a AMBOS lados (claves y título buscado).
     Previene mismatch entre U+2019 (tipográfico) y U+0027 (ASCII).

   REGLA: NUNCA acceder POSTERS/CUSTOM_POSTERS directamente
   en templates — siempre usar getPosterSrc(title, isCortos).
══════════════════════════════════════════════════════ */

// Pre-normalizar claves de los tres diccionarios al cargar

// ═══════════════════════════════════════════════════════════════
// FUENTE ÚNICA DE VERDAD — getFilmPoster(f)
// ───────────────────────────────────────────────────────────────
// Recibe el objeto film completo. Devuelve siempre el poster
// correcto según el tipo. Nunca tomar esta decisión en otro lugar.
//
// TIPOS Y REGLAS:
//   f.type === 'event'   → poster ámbar generativo
//   f.is_cortos === true → poster real si existe, teal generativo si no
//   corto individual     → getPosterSrc(title, true) — busca en CUSTOM_POSTERS del festival
//   película             → poster real si existe, null si no
//
// USO: getFilmPoster(f) en TODOS los contextos — grilla, card, lista, Mi Plan
// ═══════════════════════════════════════════════════════════════
// Devuelve inline style para object-position cuando el film tiene posterPosition != 'center'
// Aplica solo a imágenes editoriales 16:9 que necesitan crop ajustado

// makeSorpresaPoster → src/view/components.js (Step 6a). Importado.

// Para cortos individuales dentro de un film_list (no tienen objeto film completo)

// Poster de film_list item de largometraje (is_programa).
// No genera placeholder — devuelve null si no hay poster real.

// ═══════════════════════════════════════════════════════════════
// 2 · SISTEMA DE ÍCONOS
//     LB_SVG (Letterboxd), ICONS (Lucide)
// ═══════════════════════════════════════════════════════════════
/* ── Letterboxd slugs — FUENTE ÚNICA: lista oficial FICCI 65 ───
   https://letterboxd.com/ficcifestival/list/ficci-65/detail/
   Extraídos directamente del DOM con Claude in Chrome.
   Sin inferencias. Sin suposiciones.
   Replicable: extraer desde la lista oficial del festival en LB.
──────────────────────────────────────────────────────────────── */
let LB_SLUGS={};
function lbUrl(title){
  // Use festival-specific slug map from active festival config
  const _cfg=FESTIVAL_CONFIG[_activeFestId]||{};
  const _slugMap=_cfg.lbSlugs||LB_SLUGS;
  const slug=_slugMap[title]||LB_SLUGS[title];
  if(!slug) return null;
  if(slug.startsWith('http')) return slug;
  return`https://letterboxd.com/film/${slug}/`;
}
// Nuevo formato: lee lbSlug directamente del objeto film si existe
function lbUrlForFilm(f){
  if(!f) return null;
  if(f.lbSlug) return f.lbSlug.startsWith('http')?f.lbSlug:`https://letterboxd.com/film/${f.lbSlug}/`;
  return lbUrl(f.title);
}
function lbLink(title,film){
  const url=film?lbUrlForFilm(film):lbUrl(title);
  if(!url) return'';
  return`<a class="c-lb pel-sheet-lb" href="${url}" target="_blank" rel="noopener">${LB_SVG}<span class="c-lb-text pel-sheet-lb-text">Letterboxd</span></a>`;
}

// SECTION_ORDER_LIST, FILM_CATEGORY_ORDER, FILM_CATEGORY_LABEL, SECTION_COLORS
// → src/config.js (Step 1). Importados al top del módulo.
// _sectionColor → src/view/components.js (Step 6a). Importado.
// Detecta si un poster viene de una fuente editorial (imagen 16:9 del festival)
// Usa el campo explícito posterSource si existe, si no, fallback a detección por URL.
// Regla: nuevos festivales deben usar posterSource en el JSON — no depender de la URL.

// ── _posterThumb ─────────────────────────────────────────────────────────────
// FUENTE ÚNICA DE VERDAD para posters en contexto lista/thumbnail.
// Aplica tratamiento editorial (color de sección + 16:9) cuando corresponde.
// Todos los contextos (Intereses, Planear, Mi Plan, Sugerencias) deben usar
// esta función. NUNCA construir <img class="lb-poster"> directamente.
//
// cssClass: 'lb-poster' | 'int-item-poster' | 'prio-chip-poster'
// loading:   'lazy' (default) | 'eager'
// Nota (p7c-4): se eliminó el param onclickJs — los call sites que necesitan
// abrir una sheet usan el mecanismo js-open-pel (clase + data-title).

// Elimina el prefijo emoji de una sección (ej. "🎬 Competencia" → "Competencia")
// NO elimina palabras — "U.S. Narrative Competition" se mantiene intacto
// _secLabel → src/view/components.js (Step 6a). Importado.
// _buildPosterV16 → src/view/components.js (Step 6a). Importado.
// makeEventPoster → src/view/components.js (Step 6a). Importado.

// NOTICES, FESTIVAL_CONFIG → src/config.js (Step 1). Importados al top del
// módulo. Festival-data como single source en config.js; aquí solo se consumen.
// FESTIVAL_CONFIG[id]={...} (mutación de loadFestival) opera sobre el objeto
// importado — permitido en ESM (mutación ≠ reasignación del binding).

// Festival por defecto — primer festival registrado en FESTIVAL_CONFIG.
// Usado como fallback cuando localStorage está vacío o no hay festival en rango de fechas.
// Al agregar un nuevo festival como primero en el config, este fallback se actualiza solo.
// _DEFAULT_FEST_ID → src/config.js (Step 6g). Importado (deriva de FESTIVAL_CONFIG).
const _storedFestId=storage.getActiveFestId();
// Si el festival guardado ya terminó → limpiar localStorage ahora, antes de que nada más lo lea
const _storedFestCfg=_storedFestId&&FESTIVAL_CONFIG[_storedFestId];
const _storedFestEnded=_storedFestCfg&&_storedFestCfg.festivalEndStr&&new Date(_storedFestCfg.festivalEndStr)<new Date();
if(_storedFestEnded) localStorage.removeItem('otrofestiv_festival');
_activeFestId=(_storedFestId&&!_storedFestEnded)?_storedFestId:_DEFAULT_FEST_ID;

// ═══════════════════════════════════════════════════════════════
// SUPABASE — Auth + Cloud Sync
// ═══════════════════════════════════════════════════════════════
const _SB_URL='https://eytxrvbnwzxuedbmnnqr.supabase.co';
const _SB_KEY='sb_publishable_-edEGNPRmpsRy7ThJMWtdw_bs6IVZSC';
let _sb=null,_sbUser=null,_sbReady=false;

// Init — llamado una vez al arrancar
function _sbInit(){
  if(typeof supabase==='undefined'){window.addEventListener('load',_sbInit,{once:true});return;}
  try{
    _sb=supabase.createClient(_SB_URL,_SB_KEY);
    _sb.auth.onAuthStateChange(async(event,session)=>{
      _sbUser=session?.user??null;
      _sbUpdateUI();
      if(event==='SIGNED_IN'){
        await _cloudLoad();
        _renderAfterSync();
      }
      if(event==='SIGNED_OUT') _sbUpdateUI();
    });
    _sb.auth.getSession().then(({data:{session}})=>{
      _sbUser=session?.user??null;
      _sbReady=true;
      _sbUpdateUI();
    });
  }catch(e){console.warn('Supabase init error:',e);}
}

// Magic Link — envía email de acceso
async function _sbSignIn(email){
  if(!_sb) return {error:'no client'};
  const{error}=await _sb.auth.signInWithOtp({
    email,
    options:{shouldCreateUser:true}
  });
  return{error};
}

// Sign out
async function _sbSignOut(){
  if(!_sb) return;
  await _sb.auth.signOut();
  _sbUser=null;
  _sbUpdateUI();
}

// Cargar estado del usuario desde la nube
async function _cloudLoad(){
  if(!_sb||!_sbUser) return;
  try{
    const{data,error}=await _sb
      .from('user_festival_state')
      .select('*')
      .eq('user_id',_sbUser.id)
      .eq('festival_id',_activeFestId)
      .single();
    if(error||!data) return; // Sin datos en nube — conservar local
    // Aplicar datos de la nube (tienen prioridad sobre localStorage) — atómico
    const _cloudUpdates = {};
    if(data.watchlist?.length) _cloudUpdates.watchlist = new Set(data.watchlist);
    if(data.watched?.length) _cloudUpdates.watched = new Set(data.watched);
    if(data.ratings && Object.keys(data.ratings).length) _cloudUpdates.filmRatings = {...state.get('filmRatings'), ...data.ratings};
    if(data.saved_agenda) _cloudUpdates.savedAgenda = data.saved_agenda;
    if(data.prioritized?.length) _cloudUpdates.prioritized = new Set(data.prioritized);
    if(data.availability && Object.keys(data.availability).length){
      const _newAv = {...state.get('availability')};
      DAY_KEYS.forEach(d=>{ if(data.availability[d]) _newAv[d] = data.availability[d]; });
      _cloudUpdates.availability = _newAv;
    }
    if(Object.keys(_cloudUpdates).length) state.batchUpdate(_cloudUpdates);
    // Sincronizar también en local
    saveWL();saveWatched();savePrio();saveSavedAgenda();saveAV();
  }catch(e){console.warn('Cloud load error:',e);}
}

// Guardar estado en la nube (debounced 2s)
let _cloudSaveTimer=null;
function _cloudSave(){
  if(!_sb||!_sbUser) return;
  clearTimeout(_cloudSaveTimer);
  _cloudSaveTimer=setTimeout(async()=>{
    try{
      await _sb.from('user_festival_state').upsert({
        user_id:_sbUser.id,
        festival_id:_activeFestId,
        watchlist:[...watchlist],
        watched:[...watched],
        ratings:filmRatings,
        saved_agenda:savedAgenda,
        prioritized:[...prioritized],
        availability,
        updated_at:new Date().toISOString()
      },{onConflict:'user_id,festival_id'});
      _sbShowSyncDot('ok');
    }catch(e){
      console.warn('Cloud save error:',e);
      _sbShowSyncDot('err');
    }
  },2000);
}

// UI helpers
function _sbUpdateUI(){
  const btn=document.getElementById('auth-btn');
  const av=document.getElementById('auth-avatar');
  if(!btn) return;
  if(_sbUser){
    const initial=(_sbUser.email||'?')[0].toUpperCase();
    if(av) av.textContent=initial;
    btn.title=_sbUser.email;
    btn.classList.add('signed-in');
  } else {
    if(av) av.textContent='';
    btn.title=t('aria_sincronizar');
    btn.classList.remove('signed-in');
  }
}
function _sbShowSyncDot(state){
  const dot=document.getElementById('sync-dot');
  if(!dot) return;
  dot.className='sync-dot sync-'+state;
  if(state==='ok') setTimeout(()=>{dot.className='sync-dot';},3000);
}
function _renderAfterSync(){
  // Re-renderiza la vista activa después de cargar datos de la nube
  if(typeof showDayView==='function') showDayView();
  if(typeof _renderProgramaContent==='function') _renderProgramaContent();
}

// Abrir sheet de login
// openAuthSheet → src/view/sheets.js (Step 6b). Importado.
// closeAuthSheet → src/view/sheets.js (Step 6b). Importado.
async function submitAuthEmail(){
  const inp=document.getElementById('auth-email-inp');
  const btn=document.getElementById('auth-send-btn');
  const msg=document.getElementById('auth-msg');
  const email=(inp?.value||'').trim();
  if(!email||!email.includes('@')){msg.textContent=t('auth_email_hint');return;}
  btn.disabled=true;btn.textContent=t('auth_enviando');
  const{error}=await _sbSignIn(email);
  if(error){
    msg.textContent=t('toast_envio_err');
    btn.disabled=false;btn.textContent=t('auth_enviar_cod');
  } else {
    msg.textContent='';
    // Guardar email para verificación OTP
    document.getElementById('auth-otp-email').textContent=email;
    document.getElementById('auth-sheet-step1').style.display='none';
    document.getElementById('auth-sheet-step2').style.display='block';
    setTimeout(()=>document.getElementById('auth-otp-inp')?.focus(),300);
  }
}

async function submitOTP(){
  const email=document.getElementById('auth-otp-email').textContent;
  const token=(document.getElementById('auth-otp-inp')?.value||'').trim();
  const btn=document.getElementById('auth-otp-btn');
  const msg=document.getElementById('auth-otp-msg');
  if(!token||token.length<6){msg.textContent=t('auth_cod_hint');return;}
  btn.disabled=true;btn.textContent=t('auth_verificando');
  try{
    const{data,error}=await _sb.auth.verifyOtp({email,token,type:'email'});
    if(error){
      msg.textContent=t('toast_cod_mal');
      btn.disabled=false;btn.textContent=t('av_confirmar');
    } else {
      closeAuthSheet();
      // Reset steps
      document.getElementById('auth-sheet-step1').style.display='block';
      document.getElementById('auth-sheet-step2').style.display='none';
      document.getElementById('auth-otp-inp').value='';
    }
  }catch(e){
    msg.textContent=t('toast_algo_mal');
    btn.disabled=false;btn.textContent=t('av_confirmar');
  }
}
// _showSignedInSheet → src/view/sheets.js (Step 6b). Importado.
async function deleteAccount(){
  if(!_sb||!_sbUser) return;
  const btn=document.getElementById('auth-delete-btn');
  if(!btn) return;
  // Confirmación inline
  if(!btn.dataset.confirmed){
    btn.dataset.confirmed='1';
    btn.textContent=t('auth_eliminar_confirm');
    btn.style.fontWeight='var(--w-bold)';
    setTimeout(()=>{
      if(btn.dataset.confirmed){
        delete btn.dataset.confirmed;
        btn.textContent=t('auth_eliminar');
        btn.style.fontWeight='';
      }
    },4000);
    return;
  }
  // Segunda pulsación — ejecutar
  btn.disabled=true;
  btn.textContent=t('auth_eliminando');
  try{
    const{error}=await _sb.rpc('delete_user');
    if(error) throw error;
    await _sbSignOut();
    closeAuthSheet();
    showToast(t('auth_eliminar'),'✓');
  }catch(e){
    btn.disabled=false;
    btn.textContent=t('auth_eliminar');
    delete btn.dataset.confirmed;
    btn.style.fontWeight='';
    showToast('Error: '+e.message,'✗');
  }
}
async function signOutAndClose(){
  await _sbSignOut();
  closeAuthSheet();
  // Reset steps
  document.getElementById('auth-sheet-step1').style.display='block';
  document.getElementById('auth-sheet-step3').style.display='none';
}
const LB_SVG=`<svg class="block-shrink" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="13" height="13"><rect width="64" height="64" rx="9" fill="#2C3440"/><circle cx="21" cy="32" r="12" fill="#00B020" opacity=".9"/><circle cx="32" cy="32" r="12" fill="#3CBEDB" opacity=".85"/><circle cx="43" cy="32" r="12" fill="#FF8000" opacity=".9"/></svg>`;

/* ── Lucide Icons — sistema de íconos Otrofestiv ── */
// ICONS → src/view/components.js (Step 6a). Importado.

// Festival date map

// ═══════════════════════════════════════════════════════════════
// 3 · CONFIGURACIÓN
//     FESTIVAL_DATES, VENUES, PRIO_LIMIT, constantes Mi Plan
// ═══════════════════════════════════════════════════════════════
FESTIVAL_DATES={
  'Martes':'2026-04-14','Miércoles':'2026-04-15','Jueves':'2026-04-16',
  'Viernes':'2026-04-17','Sábado':'2026-04-18','Domingo':'2026-04-19'
};
// Fin del festival — última función del Domingo + margen
FESTIVAL_END=new Date('2026-04-20T02:00:00');
// festivalEnded() → boolean — true si el festival ya terminó.
// Lee (contrato implícito): FESTIVAL_END (mutable, swapeada por loadFestival).
// Llama: simNow().
// Comparación estricta (>): simNow === FESTIVAL_END retorna false.
// NO en _SCHED_PURE_FNS — el worker define su propia copia (línea ~8297) con
//   FESTIVAL_END_TS (timestamp ms) en vez de FESTIVAL_END (Date). Artefacto del
//   mecanismo .toString(); se elimina en Fase 8 del destino.
// festivalEnded → src/domain/time.js (Step 5). Importado.

// Check if a screening has passed (with 10 min grace)

// ═══════════════════════════════════════════════════════════════
// 4 · UTILIDADES
//     Funciones puras: fechas, tiempo, conflictos, normalización
// ═══════════════════════════════════════════════════════════════
// screeningPassed(s) → boolean — true si el screening ya pasó (con 10 min de grace).
// Lee (contrato implícito): FESTIVAL_DATES (mapa dayKey → ISO date).
// Llama: festivalEnded(), _festDate(), simNow().
// Gate: si festivalEnded()=true → retorna false (post-festival, todo vuelve a
//   opacidad plena; no se marca nada como "pasado").
// Grace: suma 10 min al startTime antes de comparar — un screening que arrancó
//   hace 5 min todavía cuenta como "no pasado" (el usuario aún puede llegar).
// En _SCHED_PURE_FNS: el worker la consume vía .toString().
// screeningPassed → src/domain/film.js (Step 5). Importado.
// dayFullyPassed(day) → boolean — true si la última función del día ya pasó.
// Lee (contrato implícito): FESTIVAL_DATES, FILMS.
// Llama: _festDate(), simNow().
// Computa "última función" tomando max(FILMS[].time) para films con f.day===day,
//   y aplica el mismo grace de 10 min que screeningPassed.
// Si no hay films del día (o day no existe en FESTIVAL_DATES) → retorna false.
// Main-thread only — usado en render de chips de día y línea "now" del agenda.
// dayFullyPassed → src/domain/time.js (Step 5). Importado.

// VENUES → src/config.js (Step 1). Importado al top del módulo.

/* ── VENUES: configuración, salas, tiempos de viaje ─────────────────── */
// Las coordenadas de sedes viven en festivals/*.json bajo venues{}.
// venueTravelMins() las lee directamente de FESTIVAL_CONFIG[id].venues.
// _resolveVenue — name + venues → entrada de venues{} o {short:name} (fallback).
// Pura: no lee globals. Es la única de las _SCHED_PURE_FNS que es genuinamente
//   pura — las demás leen FESTIVAL_BUFFER, FESTIVAL_TRANSPORT, etc. como contrato
//   implícito. Se inyecta al worker vía .toString(); el worker pasa _venueCoords
//   como segundo arg (mismo shape).
// Match: exacto → prefix/includes case-insensitive, longest-key-first.
//   El longest-first garantiza determinismo cuando un name matchea múltiples keys
//   (ej: "Sala A Mejorada" gana sobre "Sala A").
// _resolveVenue → src/domain/festival.js (Step 5). Importado.
// venueTravelMins → src/domain/festival.js (Step 5). Importado.

/* ── UTILS: tiempo, fecha, duración ─────────────────────────────────── */
// toMin → src/domain/time.js (Step 5). Importado.
// parseDur → src/domain/time.js (Step 5). Importado.
// effectiveDuration — duración total de una función incluyendo Q&A.
// Pura (contrato implícito): lee DEFAULT_DURATION_MIN vía parseDur. El worker
//   define la misma constante en _workerGlobals → comportamiento idéntico.
// Asume: f.duration es string parseable a int ("90 min", "~95 min");
//   f.has_qa boolean. Si has_qa, suma 30 min (Q&A extiende la función).
// effectiveDuration → src/domain/film.js (Step 5). Importado.
// minToStr → src/domain/time.js (Step 5). Importado.

/* ── CONFLICTS: detección de solapamientos entre funciones ──────────── */
// screensConflict — true si dos funciones a y b no pueden ambas asistirse.
// Pura (contrato implícito): lee FESTIVAL_BUFFER (gap mínimo entre funciones),
//   FESTIVAL_TRANSPORT y FESTIVAL_CONFIG[_activeFestId].venues vía travelMins.
//   El worker define equivalentes (FESTIVAL_BUFFER, _transport, _venueCoords)
//   en _workerGlobals → comportamiento idéntico.
// Lógica: días distintos → no conflicto. Mismo día → suman effectiveDuration
//   (Q&A incluido) y exigen gap ≥ max(FESTIVAL_BUFFER, travel+FESTIVAL_BUFFER)
//   entre el fin de una y el inicio de la otra.
// screensConflict → src/domain/schedule.js (Step 5). Importado.
// travelMins → src/domain/festival.js (Step 5). Importado.

// Normalize text for accent-insensitive search
function normalize(str){
  return str.normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase();
}
// ── normTitle ─────────────────────────────────────────────────────────────────
// Normaliza comillas tipográficas → ASCII en títulos de festival.
// U+2019 ' U+2018 ' U+201C " U+201D " → ' ' " "
// Punto único de verdad: se aplica en loadFestival sobre FILMS.
// Todo lookup derivado (watchlist, prioritized, openPelSheet) hereda
// el título normalizado sin cambios adicionales.
function normTitle(t){
  if(!t) return t;
  return t
    .replace(/[‘’ʼʹ]/g,"'")  // comillas simples tipográficas → '
    .replace(/[“”«»]/g,'"');  // comillas dobles tipográficas → "
}

// ═══════════════════════════════════════════════════════════════
// 5 · ESTADO GLOBAL
//     watchlist, watched, prioritized, savedAgenda, availability
// ═══════════════════════════════════════════════════════════════
// ── STATE ──
watchlist=new Set();
filmRatings={}; // {title: 0.5..5} medias estrellas Letterboxd-style
watched=new Set();
prioritized=new Set();
PRIO_LIMIT=5; // Updated by loadFestival per festival
/* ── Clave de almacenamiento — cambiar por edición del festival ──
   Formato: {nombre}{año}_ → prefija todas las keys de localStorage.
   Garantiza que cada edición empiece limpia sin datos residuales. */
FESTIVAL_STORAGE_KEY=(storage.getActiveFestId()||_DEFAULT_FEST_ID)+'_';

// ── Reset agresivo de caché — independiente del SW ────────────────
// BUILD_VERSION: cambia en cada deploy.
// Al cargar, compara con localStorage. Si difiere → reload duro.
// sessionStorage evita loops infinitos dentro de la misma sesión.
const BUILD_VERSION='202605241749';
(function(){
  // _vk eliminado — el build version se accede vía storage.getBuild()/setBuild()
  const _sk='otrofestiv_reloaded';
  const _stored=storage.getBuild();
  const _reloaded=sessionStorage.getItem(_sk);
  // Solo recargar si el usuario ya eligió un festival (no interrumpir primera visita)
  const _splashSeen=storage.getActiveFestId();
  if(_stored && _stored!==BUILD_VERSION && !_reloaded && _splashSeen){
    sessionStorage.setItem(_sk,'1');
    storage.setBuild(BUILD_VERSION);
    location.reload(true);
    return;
  }
  sessionStorage.removeItem(_sk);
  storage.setBuild(BUILD_VERSION);
})();

/* ── GLOSARIO DE TÉRMINOS USER-FACING ────────────────────────────
   Validar con usuarios reales antes de cada edición del festival.
   Regla: si un asistente al festival no usaría la palabra
   naturalmente, cambiarla antes de codificarla.

   TÉRMINO          USO EN LA APP           EVITAR
   ──────────────────────────────────────────────────
   Intereses        colección personal      Mi Lista, Selección, Watchlist
   Mi Plan          agenda generada         Agenda, Calendario
   Planear          tab de generación       Algoritmo, Cálculo
   Opciones         resultados del alg.     Escenarios, Variantes
   Prioridad        ★ película destacada    Favorita, Top
   Disponibilidad   bloques de tiempo libre Horario, Agenda libre
   Añadir           acción de ♥             Guardar, Seleccionar
   Elegir           confirmar un plan       Guardar, Aceptar
   ────────────────────────────────────────────────── */
// FESTIVAL_BUFFER → src/config.js (Step 1).
savedAgenda=null;
lastRemovedSlots=[]; // tracks up to 5 recently removed films
// MAX_REMEMBERED_SLOTS → src/config.js (Step 1).
let activeMiPlanDay=null;
let _ctaRemovedVisible=false; // CTA B: post-eliminación
let _ctaRemovedTimer=null;    // CTA B: timer de auto-dismiss
filmDelays={};            // retrasos manuales: key=title|day|time, val=mins
filmDelaysHistory={};     // p5.5: undo stack — key=title|day|time, val=[prev1, prev2, ...]
                              // Separado de filmDelays para inmutabilidad (era ._hist anidado pre-p5.5).
// ── Simulation clock (dev tool) ──
_simTime=null; // null = real time
// simNow() → Date — Date de "ahora" controlable para sim/QA.
// Lee (contrato implícito): _simTime (null = tiempo real; string ISO = override).
// Returns: new Date(_simTime) si _simTime es truthy, sino new Date() (tiempo real).
// NO en _SCHED_PURE_FNS — el worker define su propia copia (línea ~8296) con
//   SIM_TIME en vez de _simTime (artefacto del .toString(); resuelto en Fase 8).
// simNow → src/domain/time.js (Step 5). Importado.
// simTodayStr() → 'YYYY-MM-DD' — fecha local de simNow().
// Llama: simNow().
// Usa getFullYear/getMonth/getDate (TZ local del runtime). NO toISOString —
//   éste devuelve UTC y produciría el día siguiente después de las 7 PM en
//   Colombia (UTC-5), rompiendo la línea "ahora" en agenda y header.
// Main-thread only.
// simTodayStr → src/domain/time.js (Step 5). Importado.
let miPlanViewStart=0; // 0-4, step 1, shows 2 days
// ─────────────────────────────────────────────────────────────────────────────
// ⚠️  FIX CRÍTICO — NO REMOVER (Apr 2026)
// availability debe inicializarse aquí con los 6 días del festival.
// Sin esta inicialización, Planear lanza TypeError al acceder a
// availability[day].blocks y la pestaña no renderiza.
// ─────────────────────────────────────────────────────────────────────────────
availability={
  'Martes':{blocks:[]},'Miércoles':{blocks:[]},'Jueves':{blocks:[]},
  'Viernes':{blocks:[]},'Sábado':{blocks:[]},'Domingo':{blocks:[]}
};

// ═══════════════════════════════════════════════════════════════
// 6 · MI PLAN — HELPERS & RENDER
//     mplanPx, mplanPct, renderMiPlanCalendar, selectMiPlanDay
// ═══════════════════════════════════════════════════════════════

// REGLA: scroll a mplan-detail — mide el topbar directamente del DOM,
// no depende de --tb-total (incorrecto en mobile por incluir nav inferior).
// Usar esta función en TODOS los contextos que necesiten bajar al detalle.
function _scrollToMplanDetail(){
  const el=document.getElementById('mplan-detail');
  if(!el) return;
  const tb=document.querySelector('.topbar');
  const tbH=tb?Math.ceil(tb.getBoundingClientRect().height):86;
  window.scrollTo({top:Math.max(0,el.getBoundingClientRect().top+window.scrollY-tbH-8),behavior:'smooth'});
}

function selectMiPlanDay(idx){
  activeMiPlanDay=idx;
  if(idx<miPlanViewStart||idx>=miPlanViewStart+2) miPlanViewStart=Math.min(idx,DAY_KEYS.length-2);
  renderAgenda();
  // Scroll to detail section below calendar
  setTimeout(()=>{
    _scrollToMplanDetail();
  },80);
}
function miPlanNav(dir){
  miPlanViewStart=Math.max(0,Math.min(DAY_KEYS.length-2,miPlanViewStart+dir));
  if(activeMiPlanDay<miPlanViewStart||activeMiPlanDay>=miPlanViewStart+2) activeMiPlanDay=miPlanViewStart;
  renderAgenda();
}

// ═══════════════════════════════════════════════════════════════
// 7 · PERSISTENCIA
//     loadState, saveWL, saveWatched, saveAV, saveSavedAgenda
// ═══════════════════════════════════════════════════════════════

/* ── STATE: persistencia en localStorage ──────────────────────────────
 * loadState — hidrate del user-state desde storage en un solo state.batchUpdate.
 * Atomicidad: subscribers ven todo el snapshot post-hidrate, nunca parcial.
 * Heal (prioritized ⊆ watchlist) corre POST-batch como update separado porque
 * lee `prioritized` ya seteado; el efecto neto es 2 notifications de watchlist
 * (hidrate + heal). Aceptable — el heal es idempotente para subscribers.
 */
function loadState(){
  try{
    // Computar todos los valores hidratados (puro, sin escribir)
    const _wl = new Set([...storage.getWatchlist()].map(normTitle));
    const _wd = new Set([...storage.getWatched()].map(normTitle));
    const _pr = new Set([...storage.getPrioritized()].map(normTitle));
    const _ratings = {...state.get('filmRatings'), ...storage.getFilmRatings()};
    const _av = storage.getAvailability();
    const _newAv = {...state.get('availability')};
    DAY_KEYS.forEach(d=>{ if(_av[d]) _newAv[d]=_av[d]; });
    let _sa = storage.getSavedAgenda();
    if(_sa && _sa.schedule){
      // Normalizar venues viejos (ej: 'CC Bocagrande' → 'Plaza Bocagrande')
      _sa = {..._sa, schedule: _sa.schedule.map(s => s.venue ? {...s, venue: s.venue.replace(/CC Bocagrande/g,'Plaza Bocagrande')} : s)};
    }
    state.batchUpdate({
      watchlist: _wl,
      watched: _wd,
      prioritized: _pr,
      filmRatings: _ratings,
      availability: _newAv,
      savedAgenda: _sa,
      lastRemovedSlots: storage.getLastRemovedSlots(),
      filmDelays: storage.getFilmDelays(),
      filmDelaysHistory: storage.getFilmDelaysHistory(),
    });
    // Heal: garantiza que todo lo que está en prioritized esté en watchlist
    state.update('watchlist', s => { let n=s; prioritized.forEach(t=>{ if(!n.has(t)) n=state._addToSet(n,t); }); return n; });
    saveWL();
    const _v = storage.getViewmodes(); if(_v.miPlan) miPlanViewMode=_v.miPlan; if(_v.intereses) interesesViewMode=_v.intereses;
  }catch(e){console.warn('[loadState] failed',e);}
}
function saveWL(){ storage.setWatchlist(watchlist); _cloudSave(); }
function saveWatched(){ storage.setWatched(watched); _cloudSave(); }
function saveRating(title,rating){
  state.update('filmRatings', o => rating>0 ? {...o, [title]: rating} : state._omit(o, title));
  storage.setFilmRatings(filmRatings); _cloudSave();
}
function saveAV(){ storage.setAvailability(availability); _cloudSave(); }
function saveSavedAgenda(){ storage.setSavedAgenda(savedAgenda); _cloudSave(); _scheduleNotifications(); }

// ── Notificaciones locales — aviso 30 min antes de cada función ───────────
async function _scheduleNotifications(){
  if(!window.Capacitor?.isNativePlatform()) return;
  try{
    const {LocalNotifications}=window.Capacitor.Plugins;
    // Solicitar permiso si no se tiene
    const perm=await LocalNotifications.requestPermissions();
    if(perm.display!=='granted') return;
    // Cancelar notificaciones anteriores del plan
    await _cancelNotifications();
    if(!savedAgenda?.schedule?.length) return;
    // Convertir tiempo 12h→24h (mismo helper que exportICS)
    const pad=n=>String(n).padStart(2,'0');
    const to24h=t=>{if(!t)return'12:00';const m=t.match(/(\d+):(\d+)\s*(AM|PM)/i);if(!m)return t;let h=parseInt(m[1]),mn=m[2],ap=m[3].toUpperCase();if(ap==='PM'&&h!==12)h+=12;if(ap==='AM'&&h===12)h=0;return pad(h)+':'+mn;};
    const notifications=[];
    savedAgenda.schedule.forEach((s,i)=>{
      const dateStr=FESTIVAL_DATES[s.day];if(!dateStr) return;
      const [h,min]=to24h(s.time).split(':').map(Number);
      const tz=FESTIVAL_CONFIG[_activeFestId]?.timezoneOffset??-5;
      const start=new Date(`${dateStr}T${pad(h)}:${pad(min)}:00`);
      if(isNaN(start.getTime())) return;
      // 30 min antes
      const notify=new Date(start.getTime()-30*60000);
      if(notify<=new Date()) return; // ya pasó
      notifications.push({
        id:1000+i,
        title:'Otrofestiv',
        body:`${s._title} · ${s.venue||''} · ${s.time}`,
        schedule:{at:notify,allowWhileIdle:true},
        sound:null,extra:null
      });
    });
    if(notifications.length){
      await LocalNotifications.schedule({notifications});
    }
  }catch(e){console.warn('Notifications error:',e);}
}

async function _cancelNotifications(){
  if(!window.Capacitor?.isNativePlatform()) return;
  try{
    const {LocalNotifications}=window.Capacitor.Plugins;
    const pending=await LocalNotifications.getPending();
    const toCancel=pending.notifications.filter(n=>n.id>=1000&&n.id<2000);
    if(toCancel.length) await LocalNotifications.cancel({notifications:toCancel});
  }catch(e){}
}
function savePrio(){ storage.setPrioritized(prioritized); _cloudSave(); }
function saveLastSlot(){ storage.setLastRemovedSlots(lastRemovedSlots); }
function saveDelays(){ storage.setFilmDelays(filmDelays); storage.setFilmDelaysHistory(filmDelaysHistory); }

// Controller (p7a)
function setDelay(title,day,time,addMins){
  // 1. READ — state + args
  const {filmDelays, filmDelaysHistory} = state.snapshot();
  const k=title+'|'+day+'|'+time;
  const newVal=Math.max(0, (filmDelays[k]||0)+addMins);
  // 3. MUTATE
  state.batchUpdate({
    filmDelaysHistory: {...filmDelaysHistory, [k]: [...(filmDelaysHistory[k]||[]), filmDelays[k]||0]},
    filmDelays: newVal===0 ? state._omit(filmDelays, k) : {...filmDelays, [k]: newVal},
  });
  // 4. PERSIST (render automático vía pipeline)
  saveDelays();
}
// Controller (p7a)
function undoDelay(title,day,time){
  // 1. READ — state + args
  const {filmDelays, filmDelaysHistory} = state.snapshot();
  const k=title+'|'+day+'|'+time;
  // 2. GUARD — no history para esta key
  if(!filmDelaysHistory[k]||!filmDelaysHistory[k].length) return;
  const prev=filmDelaysHistory[k][filmDelaysHistory[k].length-1];
  const newHistArr=filmDelaysHistory[k].slice(0,-1);
  // 3. MUTATE
  state.batchUpdate({
    filmDelaysHistory: newHistArr.length ? {...filmDelaysHistory, [k]: newHistArr} : state._omit(filmDelaysHistory, k),
    filmDelays: prev===0 ? state._omit(filmDelays, k) : {...filmDelays, [k]: prev},
  });
  // 4. PERSIST (render automático vía pipeline)
  saveDelays();
}
// Controller (p7a)
function clearDelay(title,day,time){
  // 1. READ — args local
  const k=title+'|'+day+'|'+time;
  // 3. MUTATE
  state.update('filmDelays', fd => state._omit(fd, k));
  // 4. PERSIST (render automático vía pipeline)
  saveDelays();
}
/* ── saveState — batching de localStorage ── */
function saveState(...keys){
  const all=!keys.length;
  if(all||keys.includes('wl'))      saveWL();
  if(all||keys.includes('watched')) saveWatched();
  if(all||keys.includes('prio'))    savePrio();
  if(all||keys.includes('agenda'))  saveSavedAgenda();
  if(all||keys.includes('av'))      saveAV();
  if(all||keys.includes('lastslot'))saveLastSlot();
}

function updateAgTab(){
  // Count: in watchlist, not watched, and has future screenings
  const future=[...watchlist].filter(t=>{
    if(watched.has(t)) return false;
    return FILMS.some(f=>f.title===t&&!screeningPassed(f));
  });
  const el=document.getElementById('ag-cnt');if(el) el.textContent=future.length;
  const tab=document.getElementById('agtab');if(tab) tab.classList.toggle('on',activeView==='agenda');
}

// ═══════════════════════════════════════════════════════════════
// 8 · EVENT HANDLERS — MI LISTA
//     toggleWL, toggleWatched, removeFromAgenda
// ═══════════════════════════════════════════════════════════════

/* ── ACTIONS: watchlist, prioridades, vistas, retraso ───────────────── */
// Controller (p7a) — el más branchy de los handlers. 3 branches:
//   A: remove con confirm modal (film en savedAgenda)
//   B: remove directo (film NO en savedAgenda)
//   C: add (con detección de "todas funciones bloqueadas" + UI variants)
function toggleWL(title,e){
  if(e) e.stopPropagation();
  // 1. READ
  const {FILMS, prioritized, savedAgenda, watched, watchlist} = state.snapshot();
  // 2. GUARD + 3. MUTATE — branch A: remove con modal si en savedAgenda
  if(watchlist.has(title)){
    if(savedAgenda&&savedAgenda.schedule.some(s=>s._title===title)){
      showActionModal(t('plan_quitar_intereses'),
        `<b>${title.length>36?title.slice(0,34)+'…':title}</b> ${t('plan_en_tu_plan')}<br><br>${t('plan_quitar_tmb')}`,
        t('plan_quitar_confirm'),()=>{
          // Modal callback variant — transaction agrupa las 3 mutaciones (p7d)
          state.transaction(() => {
            state.update('savedAgenda', a => ({...a, schedule: a.schedule.filter(s=>s._title!==title)}));
            if(!savedAgenda.schedule.length)state.set('savedAgenda', null);
            state.batchUpdate({
              watchlist: state._delFromSet(watchlist, title),
              watched: state._delFromSet(watched, title),
              prioritized: state._delFromSet(prioritized, title),
            });
          });
          saveSavedAgenda();
          saveState('wl','watched');updateCardState(title);   // render automático vía pipeline
        });return;
    }
    // Branch B: remove directo (film NO en savedAgenda)
    state.batchUpdate({
      watchlist: state._delFromSet(watchlist, title),
      watched: state._delFromSet(watched, title),
      prioritized: state._delFromSet(prioritized, title),
    });
    showToast('Fuera de tus intereses','info');
  }
  else{
    // Branch C: add — con detección "todas funciones bloqueadas" + UI variants
    state.batchUpdate({
      watchlist: state._addToSet(watchlist, title),
      watched: state._delFromSet(watched, title),
    });
    const _allScreens=FILMS.filter(f=>f.title===title&&!screeningPassed(f));
    const _allBlocked=_allScreens.length>0&&_allScreens.every(s=>isScreeningBlocked(s));
    if(_allBlocked){
      const{displayTitle}=parseProgramTitle(title);
      const _short=displayTitle.length>28?displayTitle.slice(0,26)+'…':displayTitle;
      setTimeout(()=>showToast(`"${_short}" ${t('plan_bloqueado_disp')}`,'warn',5000),300);
    } else if(activeMNav==='mnav-cartelera'||activeMNav==='mnav-seleccion'){
      showActionToast(`${ICONS.heartFill} ${t('cta_en_intereses')}`,`${ICONS.star} ${t('cta_priorizar')}`,()=>togglePriority(title));
    } else {
      showToast(`${ICONS.heartFill} En Intereses`,'info');
    }
  }
  // 4. PERSIST + surgical patch (branch B y C). Render automático vía pipeline.
  saveState('wl','watched');updateCardState(title);
}
// Controller (p7a) — branchy toggle con confirm modal en branch B
function toggleWatched(title,e){
  title=normTitle(title);
  if(e) e.stopPropagation();
  // 1. READ
  const {FILMS, watched, watchlist} = state.snapshot();
  // 2. GUARD + 3. MUTATE — branch A: ya watched, desmarcar y devolver a Intereses
  if(watched.has(title)){
    state.batchUpdate({
      watched: state._delFromSet(watched, title),
      watchlist: state._addToSet(watchlist, title),
    });
    // 4. PERSIST + surgical (render automático vía pipeline)
    saveState('wl','watched');
    updateCardState(title);
    _reRenderIntereses();
    showToast(t('plan_vuelta_pendientes'),'info');
    return;
  }
  // Branch B: marcar como vista — modal confirm (closure variant)
  const _short=title.length>36?title.slice(0,34)+'…':title;
  showActionModal(
    t('modal_ya_viste_titulo'),
    `<b>${_short}</b><br><br>${t('modal_ya_viste_body')}`,
    t('modal_ya_viste_cta'),
    ()=>{
      state.update('watched', s => state._addToSet(s, title));
      saveWatched();updateCardState(title);
      _reRenderIntereses();
      showToast(t('toast_marcada_vista'),'info');
      if(!FILMS.find(fi=>fi.title===title)?.is_cortos) setTimeout(()=>openRatingSheet(title),350);
    }
  );
}

// ── FUZZY SEARCH — accent insensitive ──
function fuzzyMatch(query,title){
  const q=normalize(query),t=normalize(title);
  if(t.includes(q)) return{match:true,score:100+q.length};
  let qi=0;for(let i=0;i<t.length&&qi<q.length;i++) if(t[i]===q[qi]) qi++;
  if(qi===q.length) return{match:true,score:qi};
  return{match:false,score:0};
}
// Controller (p7a) — modal callback contiene el handler real (closure variant)
function removeFromAgenda(title){
  // 1. READ + 2. GUARD — el outer handler solo abre el modal de confirmación
  const {savedAgenda} = state.snapshot();
  if(!savedAgenda) return;
  const _s=title.length>36?title.slice(0,34)+'…':title;
  showActionModal(t('plan_quitar_plan'),`<b>${_s}</b><br><br>${t('plan_restaurar_suger')}`,t('misc_quitar'),()=>{
    // Modal callback — el handler real (variant aceptada en spec)
    const rem=savedAgenda.schedule.find(s=>s._title===title);
    if(rem){state.update('lastRemovedSlots', arr => [{...rem,_isRestored:true}, ...arr.filter(r=>r._title!==rem._title)].slice(0,MAX_REMEMBERED_SLOTS));saveLastSlot();}
    state.update('savedAgenda', a => ({...a, schedule: a.schedule.filter(s=>s._title!==title)}));
    if(!savedAgenda.schedule.length)state.set('savedAgenda', null);
    saveSavedAgenda();
    // CTA B: mostrar aviso contextual post-eliminación
    _ctaRemovedVisible=true;
    if(_ctaRemovedTimer) clearTimeout(_ctaRemovedTimer);
    _ctaRemovedTimer=setTimeout(()=>{_ctaRemovedVisible=false;renderAgenda();},6000);
    renderAgenda();showToast('Fuera de tu plan','info');
  });
}
// Controller (p7a) — multi-step: add to watchlist + add to plan + cleanup
// lastRemovedSlots + jump al día. NO usa modal (excepto conflict sheet en
// rama de error). NOTE: state snapshot re-leído tras mutaciones interleaved
// porque condicionalmente openConflictSheet sale temprano y necesita state
// fresh para el branch.
function addSuggestion(title,day,time){
  title=normTitle(title);
  // 1. READ
  const {FILMS, _activeFestId, savedAgenda, watchlist, watched} = state.snapshot();
  // 2. GUARD
  if(festivalEnded()) return;
  // 3. MUTATE (step 1): Add to watchlist if not already there
  if(!watchlist.has(title)){
    state.batchUpdate({
      watchlist:state._addToSet(watchlist,title),
      watched:state._delFromSet(watched,title),
    });
    saveState('wl','watched');updateCardState(title);updateAgTab();
  }
  // 3. MUTATE (step 2): Add specific screening to saved agenda
  const screen=FILMS.find(f=>f.title===title&&f.day===day&&f.time===time);
  if(screen){
    if(!savedAgenda) state.set('savedAgenda', {schedule:[]});
    // Avoid duplicates (re-read state porque pudo haber sido seteado arriba)
    const sa=state.get('savedAgenda');
    if(!sa.schedule.some(s=>s._title===title)){
      // ── Re-validación en tiempo real ─────────────────────────────
      // getSuggestions verificó el hueco al renderizar, pero el plan
      // pudo haber cambiado desde entonces (otra sugerencia añadida
      // en la misma sesión). Revalidamos contra el estado actual.
      const realConflict=sa.schedule.find(s=>s.day===day&&screensConflict(s,screen));
      if(realConflict){
        openConflictSheet(title, screen, realConflict);
        return;
      }
      state.update('savedAgenda', a => ({
        ...a,
        schedule: [...a.schedule, {...screen,_title:title}]
          .sort((x,y)=>x.day_order!==y.day_order?x.day_order-y.day_order:toMin(x.time)-toMin(y.time))
      }));
      saveSavedAgenda();
      // 5. UI EFFECT: toast informativo con día y hora
      const{displayTitle:dt}=parseProgramTitle(title);
      const shortT=dt.length>20?dt.slice(0,18)+'…':dt;
      const _dayShortMap=(FESTIVAL_CONFIG[_activeFestId]||{}).dayShort||{};
      const dayShort=_dayShortMap[day]||day||'';
      showToast(`${ICONS.calendar} ${shortT} · ${dayShort} · ${time}`,'info');
    }
  }
  // 3. MUTATE (step 3): Quitar de lista de restaurables
  state.update('lastRemovedSlots', arr => arr.filter(r=>r._title!==title));
  // 4. PERSIST
  saveLastSlot();
  // 5. RENDER + UI EFFECTS: jump al día de la sugerencia + re-render
  const jumpIdx=DAY_KEYS.indexOf(day);
  if(jumpIdx>=0) activeMiPlanDay=jumpIdx;
  renderAgenda();
}

// ── AVAILABILITY ──
// ─────────────────────────────────────────────────────────────────────────────
// ⚠️  FIX CRÍTICO — NO REMOVER (Apr 2026)
// DAY_KEYS debe estar declarada aquí, antes de cualquier función que la use.
// Sin esta declaración, Planear lanza "Can't find variable: DAY_KEYS" y
// la pestaña entera no renderiza.
// ─────────────────────────────────────────────────────────────────────────────
/* ══════════════════════════════════════════════════════
   SISTEMA DE FORMATO DE DÍAS — dos niveles semánticos
   ─────────────────────────────────────────────────────
   NIVEL 1 — COMPACT (apilado, 2 líneas)
     Uso: tabs, calendarios, grids de navegación
     Abrev: DAY_ABBR[key] → 'MAR'   (var(--t-xs), gray2, arriba)
     Núm:   DAY_NUM[key]  → 14      (var(--t-lg), white, abajo)
     Contextos: dtab, mplan-wk-col, av-row-lbl, mplan-nav

   NIVEL 2 — LABEL (inline, 1 línea)
     Uso: separadores de lista, etiquetas de sección
     Corto: DAY_SHORT[key] → 'MAR 14'    (.saved-day-lbl, .ag-day-name, .suggestion-day-lbl)

   FUENTE: todo deriva de DAYS[] (definido en el bloque de render de tabs)
══════════════════════════════════════════════════════ */
let DAY_KEYS =['Martes','Miércoles','Jueves','Viernes','Sábado','Domingo'];

 // swapeado por loadFestival() — valores en inglés

/* dayChip(key) — componente apilado: ABREV arriba / NÚMERO abajo — FORMATO ÚNICO */

/* dayLabel/dayHeader — mantenidos para compatibilidad, internamente usan dayChip */

/* _lblLocalized: traduce abreviación de día al idioma activo.
   Resuelve el caso donde lbl viene en inglés (ej. Tribeca: 'WED')
   y el usuario está en español → debe mostrar 'MIÉ'. */

const _isoToFlag = c  => c&&c.length===2 ? String.fromCodePoint(0x1F1E6+c.toUpperCase().charCodeAt(0)-65)+String.fromCodePoint(0x1F1E6+c.toUpperCase().charCodeAt(1)-65) : '';

/* ══════════════════════════════════════════════════════
   emptyState(icon, title, sub) — componente vacío unificado
   Usa siempre este helper para estados vacíos — nunca inline styles ni emojis
   icon: ICONS.* | title: string | sub: string (opcional)
══════════════════════════════════════════════════════ */
// emptyState, emptyStateHero → src/view/helpers.js (Step 6f). Importados.
let avAddOpen={};
/* ── Sistema de modales de confirmación ── */
// showActionModal → src/view/feedback.js (Step 6b). Importado.
// _showModal → src/view/feedback.js (Step 6b). Importado.

// isFullDayBlocked → src/view/components.js (Step 6a). Importado.
function checkPlanConflictsWithBlock(day, fromStr, toStr){
  if(!savedAgenda||!savedAgenda.schedule.length) return[];
  const bFrom=toMin(fromStr), bTo=toMin(toStr);
  return savedAgenda.schedule.filter(s=>{
    if(s.day!==day) return false;
    const sStart=toMin(s.time), sEnd=sStart+parseDur(s.duration);
    return sStart<bTo&&sEnd>bFrom;
  });
}
// ── CASO 2: al quitar un bloque de no disponible, ¿caben más títulos? ──
function _checkRecalcOpportunity(){
  if(!savedAgenda||!savedAgenda.schedule.length) return;
  const planTitles=new Set(savedAgenda.schedule.map(s=>s._title));
  const candidates=[...watchlist].filter(t=>!planTitles.has(t)&&!watched.has(t));
  const hasOpportunity=candidates.some(t=>{
    const screens=FILMS.filter(f=>f.title===t&&!screeningPassed(f));
    return screens.length&&screens.some(s=>!isScreeningBlocked(s));
  });
  if(hasOpportunity){
    showActionToast(t('toast_horario_lib'),'Recalcular',()=>{
      switchMainNav('mnav-planner');showAgView();setTimeout(runCalc,300);
    },5000);
  }
}

function _removePlanItem(title){
  if(!savedAgenda) return;
  const removed=savedAgenda.schedule.find(s=>s._title===title);
  if(removed){
    state.update('lastRemovedSlots', arr => [{...removed,_isRestored:true}, ...arr.filter(r=>r._title!==removed._title)].slice(0,MAX_REMEMBERED_SLOTS));
    saveLastSlot();
  }
  state.update('savedAgenda', a => ({...a, schedule: a.schedule.filter(s=>s._title!==title)}));
  if(!savedAgenda.schedule.length) state.set('savedAgenda', null);
  saveSavedAgenda();
}

// ═══════════════════════════════════════════════════════════════
// 9 · DISPONIBILIDAD
//     showConflictModal, toggleFullDay, addBlock, renderAvDay
// ═══════════════════════════════════════════════════════════════
// showConflictModal → src/view/feedback.js (Step 6b). Importado.
// Controller (p7a) — branchy: si día ya bloqueado, libera; si no, bloquea con conflict modal opcional
function toggleFullDay(day){
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
// Controller (p7a) — lee 2 inputs DOM, valida, muta con conflict check
function addBlock(day){
  // 1. READ — DOM inputs (input state, ephemeral)
  const f=document.getElementById(`av-from-${day}`).value;
  const toVal=document.getElementById(`av-to-${day}`).value;
  // 2. GUARD — validation con early returns + toast
  if(!f||!toVal){showToast(t('av_seleccionar'),'warn');return;}
  if(toMin(f)>=toMin(toVal)){showToast(t('av_hora_invalida'),'warn');return;}
  const av=availability[day];
  if(av.blocks.some(b=>toMin(f)<toMin(b.to)&&toMin(toVal)>toMin(b.from))){showToast('Este horario coincide con otro bloque','warn');return;}
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
// Controller (p7a) — action handler standardizado: mutate → persist → render
function removeBlock(day,fromVal,toVal){
  // 3. MUTATE
  state.update('availability', a => ({...a, [day]: {...a[day], blocks: a[day].blocks.filter(b=>!(b.from===fromVal&&b.to===toVal))}}));
  // 4. PERSIST + 5. RENDER + UI EFFECTS
  cachedResult=null;
  saveAV();
  renderAvBlocks();
  invalidateCalcResult();
  _checkRecalcOpportunity();
}
// Pure half (p6b) — innerHTML del row del día. NO incluye className ni post-
// render defaults (esos quedan en el impure caller porque son DOM ops).
function renderAvDayHTML(state, day){
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
        ${!addOpen?`<button class="row-xs av-full-btn${fullBlocked?' active':''}" data-action="toggleFullDay" data-day="${day}">
          ${fullBlocked?ICONS.x+' '+t('av_liberar_dia'):ICONS.plus+' '+t('av_todo_el_dia_btn')}
        </button>`:''}
      </div>
    </div>`;
}
// Impure caller (p6b) — className + innerHTML + post-render select defaults
function renderAvDay(day){
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

/* ── DISPONIBILIDAD — nueva UI ──────────────────────────────────── */
let _avSheetType='hours';
let _avSheetDay=null;

function openAvSheet(){
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
      const sel=_avSheetDay===d?' selected':'';
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

// closeAvSheet → src/view/sheets.js (Step 6b). Importado.

function selectAvDay(day){
  _avSheetDay=day;
  _refreshAvDayChips();
}

function _refreshAvDayChips(){
  document.querySelectorAll('.av-day-chip').forEach(btn=>{
    btn.classList.toggle('selected', btn.dataset.day===_avSheetDay);
  });
}

function setAvType(type){
  _avSheetType=type;
  document.getElementById('av-type-hours')?.classList.toggle('selected',type==='hours');
  document.getElementById('av-type-full')?.classList.toggle('selected',type==='full');
  const ts=document.getElementById('av-time-section');
  if(ts) ts.style.display=type==='hours'?'':'none';
}

// Controller (p7a) — branchy: full-day usa toggleFullDay, range crea block con conflict check
function confirmAvBlock(){
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
    showToast('Este horario coincide con otro bloque','warn');return;
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

// Pure half (p6c)
// renderAvBlocksHTML → src/view/components.js (Step 6a). Importado.
// Impure caller (p6c)

// isScreeningBlocked(s) → boolean — true si el screening cae dentro de un block de availability del usuario.
// Lee (contrato implícito): availability (mapa dayKey → {blocks:[{from,to}]}).
// Llama: toMin (para s.time, b.from, b.to), parseDur (para s.duration).
// Solapamiento estricto: sStart<bTo && sEnd>bFrom — un screening que termina
//   exactamente cuando empieza el block NO se considera bloqueado (boundary OK).
// En _SCHED_PURE_FNS: el worker la consume vía .toString() con su propio availability.
// isScreeningBlocked → src/domain/schedule.js (Step 5). Importado.

// ── ALGORITHM — exhaustive max + MRV + random restarts ──
// _djb2 / _titleSeed / _mulberry32 — RNG determinista.
// Puras. Producen un seed reproducible a partir de un set de strings y un
// PRNG con esa semilla. _djb2: hash xor-shift de Bernstein (seed 5381).
// _titleSeed: ordena titles[] (set semantics) y hashea con _djb2 → seed
// order-independent. _mulberry32: closure factory que retorna un PRNG con
// output en [0, 1). Mismo seed → misma secuencia infinita.
// En _SCHED_PURE_FNS: el worker las consume vía .toString().
// NOTA: computeScenarios NO usa estos helpers — usa Math.random directo en
// sus shuffles internos, por design (random restarts dan diversidad). Para
// forzar reproducibilidad: shuffle(arr, _mulberry32(_titleSeed(titles))).
// _djb2 → src/domain/film.js (Step 5). Importado.
// _titleSeed → src/domain/film.js (Step 5). Importado.
// _mulberry32 → src/domain/film.js (Step 5). Importado.
// shuffle(arr, rand) → array — Fisher-Yates.
// Pura cuando se pasa `rand`. Impure con Math.random (default).
// NO muta input — clona con [...arr] y retorna el clon.
// `rand` debe retornar valor en [0, 1) (compatible con _mulberry32).
// En _SCHED_PURE_FNS: el worker la consume vía .toString().
// shuffle → src/domain/film.js (Step 5). Importado.

// ── Mejora 1: Scoring por película ──
// Pondera cuánto vale incluir una película según rareza, sección y duración
// scoreFilm(title, screens, isPriority, allTitles) → number — heurística aditiva.
// Lee (contrato implícito): FILMS (para chequear section uniqueness).
// 4 factores: isPriority +100, scarcity (+40 si 1 screening, +20 si 2, +5 si más),
//   section uniqueness +15 (única película de su sección en allTitles),
//   long-form +10 (duración del primer screening > 150 min).
// Usada por computeScenarios para el MRV ordering.
// En _SCHED_PURE_FNS: el worker la consume vía .toString().
// scoreFilm → src/domain/film.js (Step 5). Importado.

// ── Mejora 2: Interval Scheduling — ordenar funciones por conflictos mínimos + fin temprano ──
// Para cada película con múltiples funciones, prioriza la que:
// 1. Conflicta con menos otras funciones de la watchlist (menos bloqueos)
// 2. Termina más temprano (earliest-finish-time: principio clásico de interval scheduling)
// sortScreensByStrategy(screens, allGroups) → array — interval scheduling con tiebreak.
// Llama: screensConflict (con sus deps), toMin, parseDur.
// NO muta input — clona con [...screens].
// Criterio: 1) fewest-conflicts contra screenings de OTROS grupos primero;
//   2) tiebreak por earliest-finish-time.
// En _SCHED_PURE_FNS: el worker la consume vía .toString().
// sortScreensByStrategy → src/domain/schedule.js (Step 5). Importado.

// ═══════════════════════════════════════════════════════════════
// 10 · LÓGICA DE NEGOCIO
//      computeScenarios (MRV+backtracking), getSuggestions
// ═══════════════════════════════════════════════════════════════

/* ── ALGO: backtracking MRV + escenarios óptimos ────────────────────── */
// computeScenarios(titles) → Scenario[] — corazón del Planner.
// Lee (contrato implícito): watched, prioritized, FILMS, availability
//   (vía isScreeningBlocked), savedAgenda (indirecto vía screeningPassed).
// Llama: isScreeningBlocked, screeningPassed, scoreFilm, sortScreensByStrategy,
//   screensConflict, shuffle.
// Algoritmo: MRV (Most Restricted Variable) ordering + branch-and-bound con
//   cap MAX_NODES_PER_CALL=80000 (FIX CRÍTICO Apr 2026 — sin el cap, el JS
//   engine de mobile cortaba la recursión antes que desktop → outputs
//   inconsistentes entre dispositivos).
// 3 fases de generación: (1) escenarios CON prioridades, (2) fallback si las
//   prioridades conflictan todas entre sí, (3) llenar slots restantes con
//   escenarios sin prioridad para diversidad.
// Retorna hasta 8 escenarios ordenados por dayBalance (menor desviación
//   estándar de películas por día primero).
// NO determinístico: usa shuffle(arr) sin rand → Math.random en cada restart.
//   Por design — random restarts dan diversidad. Para reproducibilidad ver
//   contrato de _mulberry32 / _titleSeed.
// En _SCHED_PURE_FNS: el worker la consume vía .toString().
// computeScenarios → src/domain/schedule.js (Step 5). Importado.

// ── SUGGESTIONS after saved agenda ──

// ── RENDER FILM LIST ──
// Utility: extraer displayTitle y progSuffix de cualquier título de programa
// parseProgramTitle → src/view/components.js (Step 6b). Importado.

// _genreEN(g) — traduce género al idioma activo
// Opera sobre strings compuestos: "Comedia, Drama" → "Comedy, Drama"
const _GENRE_EN = {
  'Acción':'Action','Aventura':'Adventure','Comedia':'Comedy',
  'Drama':'Drama','Documental':'Documentary','Experimental':'Experimental',
  'Romance':'Romance','Sátira':'Satire','Terror':'Horror','Thriller':'Thriller',
  'Animación':'Animation','Ciencia Ficción':'Science Fiction',
  'Fantasía':'Fantasy','Misterio':'Mystery','Musical':'Musical',
};
function _genreEN(g) {
  if (!g || _lang !== 'en') return g;
  return g.split(',').map(s => _GENRE_EN[s.trim()] || s.trim()).join(', ');
}

// filmDisplayTitle(f) — patrón Letterboxd
// EN: title_en como principal, title como original (solo si difieren)
// ES: title siempre, sin secundario
// _langDates(cfg) — devuelve fechas en el idioma activo

function filmDisplayTitle(f) {
  if (_lang === 'en' && f.title_en && f.title_en !== f.title) {
    return { main: f.title_en, original: f.title };
  }
  return { main: f.title, original: null };
}

// ═══════════════════════════════════════════════════════════════
// 11 · RENDER — MI AGENDA
//      renderPrioStrip, renderFilmListHTML, renderSavedAgendaHTML
//      renderUnconfirmed
// ═══════════════════════════════════════════════════════════════

/* ── RENDER — MI LISTA ──────────────────────────────────────────────── */

// ── Intereses — collapse/expand secciones ────────────────────────────────
// section headers — sin toggle, siempre visibles

// Preserva el estado colapsado al re-renderizar la lista de Intereses.
// Post-p6b: delega en _rerenderFilmList que también actualiza pill counts.
function _reRenderIntereses(){
  _rerenderFilmList();
}

// Impure caller (p6b) — commit a DOM + update pill counts post-render.
// renderFilmListHTML mantuvo su nombre original (ya tenía suffix HTML) como
// la pure half. _rerenderFilmList es el nuevo impure caller. Asimetría
// documentada en plan §1.2.
function _rerenderFilmList(){
  const lel=document.getElementById('ag-film-list');
  if(!lel) return;
  lel.innerHTML=renderFilmListHTML(state);
  // Recompute pill counts — filter sobre Sets, O(n) trivial. Mismo cálculo
  // que la pure half hace; se duplica para mantener purity de renderFilmListHTML.
  const {prioritized, watched, watchlist, PRIO_LIMIT} = state.snapshot();
  const prioList=[...prioritized].filter(titleStr=>!watched.has(titleStr));
  const nonPrioList=[...watchlist].filter(titleStr=>!watched.has(titleStr)&&!prioritized.has(titleStr));
  const watchedList=[...watched];
  setTimeout(()=>{
    const _pp=document.getElementById('pill-prio-cnt');if(_pp) _pp.textContent=prioList.length?`${prioList.length}/${PRIO_LIMIT}`:'—';
    const _pi=document.getElementById('pill-int-cnt');if(_pi) _pi.textContent=nonPrioList.length?String(nonPrioList.length):'—';
    const _py=document.getElementById('pill-yv-cnt');if(_py) _py.textContent=watchedList.length?String(watchedList.length):'—';
    document.getElementById('pill-prio')?.style.setProperty('display',prioList.length?'inline-flex':'none');
    document.getElementById('pill-int')?.style.setProperty('display',nonPrioList.length?'inline-flex':'none');
    document.getElementById('pill-yv')?.style.setProperty('display',watchedList.length?'inline-flex':'none');
  },0);
}

// ── RENDER SAVED AGENDA ──
// ── Componente unificado: fila de función en agenda ──
// mode='saved'    → ✕ quita de agenda guardada
// mode='scenario' → ✕ quita de watchlist, muestra badge de alternativas
function removeFilmFromScenario(title,e){
  if(e) e.stopPropagation();
  const short=title.length>36?title.slice(0,34)+'…':title;
  showActionModal(
    t('plan_quitar_intereses'),
    `<b>${short}</b><br><br>${t('plan_se_quitara')}.`,
    t('misc_quitar'),
    ()=>{
      state.batchUpdate({
        watchlist: state._delFromSet(state.get('watchlist'), title),
        prioritized: state._delFromSet(state.get('prioritized'), title),
        watched: state._delFromSet(state.get('watched'), title),
      });
      saveState('wl','prio','watched');
      updateAgTab();
      showToast('Fuera de tus intereses','info');
      runCalc(); // recalcula directamente, no borra la vista
    }
  );
}

/* ── RENDER — MI PLAN / AGENDA ──────────────────────────────────────── */
// ── _mkCortoItemHtml ───────────────────────────────────────────────────────
// Fuente única de verdad para el item de corto en lista.
// Usado en: pel-sheet (cortos list), Mi Plan (mplan-prog-list x2).
// opts.cls      → clase CSS del row (default: 'mplan-prog-item')
// opts.section  → sección del programa padre — para poster generativo con color correcto
// opts.ratingEl → HTML del botón de calificación (opcional)

// Wrapper — lee data-* y llama openCortoSheet. Evita interpolación de apóstrofes en onclick.
function openCortoSheetFromEl(el,e){
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

// Controller (p7a) — branchy: si NO está watched, marca + post-view rating modal
function checkinLaVi(title){
  // 1. READ — state al top
  const {FILMS, savedAgenda, watched} = state.snapshot();
  // 2. GUARD — si ya está watched, solo re-renderea (no-op del estado: sin
  // mutación el pipeline no dispara, así que el render queda explícito)
  if(watched.has(title)){
    renderAgenda();
    return;
  }
  // 3. MUTATE
  state.update('watched', s => state._addToSet(s, title));
  // 4. PERSIST + surgical (render automático vía pipeline)
  saveWatched();
  updateCardState(title);
  // Post-view rating modal (sólo para films, no cortos)
  const s=savedAgenda&&savedAgenda.schedule.find(e=>e._title===title);
  const _isCortos=FILMS.find(fi=>fi.title===title)?.is_cortos;
  if(!_isCortos) setTimeout(()=>openPostViewRating(title, s?.day, s?.time, s?.venue, s?.duration), 250);
}
function checkinNoLaVi(title){
  _removePlanItem(title);
  renderAgenda();
}
// Sim panel dates derive from active festival — never hardcoded
// _simFestStart → src/view/feedback.js (Step 6b). Importado.
// _simFestEnd → src/view/feedback.js (Step 6b). Importado.
// _SIM_TOTAL → src/view/feedback.js (Step 6b). Importado.
// updateSimLabel → src/view/feedback.js (Step 6b). Importado.
let _expandedFilm=''; // key: title+day+time — which film has alternatives open
let _activeMiPlanFilm=''; // key: title+time — highlighted from calendar click
function toggleMplanProg(btn,e){
  e.stopPropagation();
  const row=btn.closest('.mplan-row')||btn.closest('.saved-item');
  const list=row?.nextElementSibling;
  if(!list||!list.classList.contains('mplan-prog-list')) return;
  const open=list.classList.toggle('open');
  btn.innerHTML=(open?ICONS.chevronD:ICONS.chevronR)+' '+t('label_programa');
}
function setActivePlanFilm(el){_activeMiPlanFilm=el.dataset.fkey||'';}
function selectFromDetail(el){
  _activeMiPlanFilm=el.dataset.rkey||'';
  // Scroll to the matching calendar block
  setTimeout(()=>{
    const block=document.querySelector(`.mplan-wk-block[data-fkey="${CSS.escape(_activeMiPlanFilm)}"]`);
    if(block) block.scrollIntoView({behavior:'smooth',block:'center'});
  },50);
  renderAgenda();
}

// ═══════════════════════════════════════════════════════════════
// 12 · RENDER — PLANEAR
//      toggleFilmAlternatives, renderFilmAlternatives
//      toggleArchive, runCalc, saveCurrentScenario, renderAgenda
// ═══════════════════════════════════════════════════════════════
function toggleFilmAlternatives(key,title,day,time){
  if(_expandedFilm===key){_expandedFilm='';renderAgenda();return;}
  _expandedFilm=key;
  // Marcar hint como visto la primera vez que se usa
  if(!localStorage.getItem('otrofestiv_hint_cambiar')){
    localStorage.setItem('otrofestiv_hint_cambiar','1');
  }
  renderAgenda();
}

// Controller (p7a) — modal builder + handler closure variant. Modal es custom
// (no showActionModal) por requirements de styling. El handler real vive en
// el `btn.onclick` closure adentro del setTimeout.
function confirmReplace(removedTitle,newTitle,day,time){
  // 1. READ — args + state (snapshot del state se hace dentro del closure
  // porque el handler se ejecuta tras el user click, no inmediato)
  const{displayTitle:dt}=parseProgramTitle(newTitle);
  const shortNew=dt.length>22?dt.slice(0,20)+'…':dt;
  const{displayTitle:dr}=parseProgramTitle(removedTitle||'');
  const shortRem=dr.length>22?dr.slice(0,20)+'…':dr;
  const existing=document.getElementById('conflict-modal');if(existing) existing.remove();
  const modal=document.createElement('div');
  modal.id='conflict-modal';modal.className='conflict-modal';
  modal.innerHTML=`<div class="conflict-modal-box">
    <div class="conflict-modal-hdr">${removedTitle?t('plan_reemplazar_funcion'):t('plan_anadir_plan')}</div>
    <div class="conflict-modal-body">${removedTitle?`${t('misc_quitar')} <b>${shortRem}</b> y ${t('misc_anadir')}`:`${t('misc_anadir')}`} <b>${shortNew}</b> al plan.</div>
    <div class="conflict-modal-btns">
      <button class="conflict-modal-btn cancel" data-action="removeConflictModal">${t('search_cancelar')}</button>
      <button class="conflict-modal-btn confirm" id="replace-ok">${t('misc_si')}${removedTitle?', '+t('misc_si_reemplazar').split(', ')[1]:', '+t('misc_si_anadir').split(', ')[1]}</button>
    </div>
  </div>`;
  document.body.appendChild(modal);
  setTimeout(()=>{
    const btn=document.getElementById('replace-ok');
    if(btn) btn.onclick=()=>{
      // Handler real — fresh snapshot al ejecutarse (post user-click)
      const {FILMS, savedAgenda, watchlist} = state.snapshot();
      modal.remove();
      if(removedTitle) _removePlanItem(removedTitle);
      const screen=FILMS.find(f=>f.title===newTitle&&f.day===day&&f.time===time);
      if(screen){
        if(!savedAgenda) state.set('savedAgenda', {schedule:[]});
        if(!watchlist.has(newTitle)){state.update('watchlist', s=>state._addToSet(s,newTitle));saveWL();}
        state.update('savedAgenda', a => ({
          ...a,
          schedule: [...a.schedule.filter(s=>s._title!==newTitle), {...screen,_title:newTitle}]
            .sort((x,y)=>DAY_KEYS.indexOf(x.day)-DAY_KEYS.indexOf(y.day)||toMin(x.time)-toMin(y.time))
        }));
        saveSavedAgenda();
      }
      _expandedFilm='';
      showToast(removedTitle?`${t('plan_reemplazada_por')} ${shortNew}`:`${shortNew} ${t('plan_anadida_al_plan')}`,'info');
      renderAgenda();
    };
  },50);
}

// ─────────────────────────────────────────────────────────────
// HEADER CONTEXTUAL DE MI PLAN
// Responde: ¿Qué hago ahora? Cambia según el momento del festival.
// ─────────────────────────────────────────────────────────────
// DEFAULT_DURATION_MIN → src/config.js (Step 1). (El worker mantiene su propia
// copia en _workerGlobals — contexto JS separado, sin acceso a imports.)

// _endedStats — stats post-festival para la rama `ended` de _getFestivalPhase.
// Pura (contrato implícito): lee FILMS, watched, savedAgenda, filmRatings.
//   Cuenta solo películas regulares (excluye is_cortos y type==='event'):
//   los cortos son contenedores y los eventos no tienen rating mechanism.
// Returns: { totalWatched, totalPlanned, pendingRatings }.
// _endedStats → src/domain/film.js (Step 5). Importado.

// _classifyTodayScreenings(screenings, nowMin) → {done, active, future}.
// Particiona funciones de hoy por su relación con nowMin (minutos del día).
// Pura (contrato implícito): lee DEFAULT_DURATION_MIN. Usa parseInt(s.duration),
//   NO parseDur — para fidelidad byte-a-byte con el código inline original
//   (tilde-prefixed durations caen al fallback de DEFAULT_DURATION_MIN).
// _classifyTodayScreenings → src/domain/film.js (Step 5). Importado.

// _gapSuggestion(todayDay, gapFromMin, gapToMin) → Film | null.
// Busca una film del día que quepa en el hueco entre dos funciones planeadas.
// Lee: FILMS, watched, savedAgenda, DEFAULT_DURATION_MIN. Llama: screeningPassed, toMin.
// Excluye films de otro día, ya watched, ya en savedAgenda, o screeningPassed=true.
// Slack +10 min en gapToMin: la film puede terminar hasta 10 min después del
//   cierre nominal del hueco (margen práctico).
// _gapSuggestion → src/domain/festival.js (Step 5). Importado.

// _getFestivalPhase — devuelve {phase, ...derived} o `null`.
// Composer thin: delega a _endedStats (post-festival), _classifyTodayScreenings
//   (partición temporal del día), _gapSuggestion (sugerencia para hueco).
// Lee (contrato implícito): FILMS, watched, savedAgenda, filmRatings, DAY_KEYS,
//   FESTIVAL_DATES; usa simNow, simTodayStr, festivalEnded, screeningPassed.
// 5 fases posibles: ended | before | evening | between | next.
// `null`: sin agenda, sin día actual en DAY_KEYS, o sin screenings hoy.
// Caller único: renderContextualHeader().
// _getFestivalPhase → src/domain/festival.js (Step 5). Importado.

let archiveOpen=false;
function toggleArchive(){
  archiveOpen=!archiveOpen;
  const body=document.getElementById('archive-body');
  const arrow=document.getElementById('arch-arrow');
  if(body) body.classList.toggle('open',archiveOpen);
  if(arrow){arrow.style.transform=archiveOpen?'rotate(180deg)':'rotate(0deg)';}
}

/* ── Display name — cadena de prioridad para imagen compartida ──
   1. Supabase user_metadata.display_name (cuenta / app nativa)
   2. localStorage 'otrofestiv_display_name' (web sin cuenta)
   3. Email prefix (fallback con cuenta)
   4. null (anónimo)
*/
function _getDisplayName(){
  if(_sbUser){
    const meta=_sbUser.user_metadata||{};
    if(meta.display_name) return meta.display_name;
  }
  const local=localStorage.getItem('otrofestiv_display_name');
  if(local) return local;
  if(_sbUser&&_sbUser.email) return _sbUser.email.split('@')[0];
  return null;
}
async function _saveDisplayName(name){
  const n=name.trim().slice(0,30);
  if(!n) return;
  localStorage.setItem('otrofestiv_display_name',n);
  if(_sb&&_sbUser){
    try{ await _sb.auth.updateUser({data:{display_name:n}}); }catch(e){console.warn('[auth] updateUser failed',e);}
  }
}

function _promptDisplayName(onSave){
  const prev=document.getElementById('display-name-sheet');if(prev)prev.remove();
  const el=document.createElement('div');
  el.id='display-name-sheet';
  el.style.cssText='position:fixed;inset:0;background:var(--overlay-70);z-index:9999;display:flex;align-items:flex-end;justify-content:center';
  el.innerHTML=`<div class="auth-sheet-body">
    <div class="sheet-handle-bar"></div>
    <div class="sheet-title">${t('export_como_aparecer')}</div>
    <div class="sheet-subtitle">${t('export_aparecera')}</div>
    <input class="sheet-input" id="dname-input" type="text" maxlength="30" placeholder="${t('auth_nombre')}" autocomplete="name">
    <button class="sheet-cta" id="dname-save">${t('export_guardar_compartir')}</button>
  </div>`;
  document.body.appendChild(el);
  const input=document.getElementById('dname-input');
  input.focus();
  document.getElementById('dname-save').onclick=async()=>{
    const v=input.value.trim();
    if(!v){input.style.borderColor='var(--red)';return;}
    await _saveDisplayName(v);
    el.remove();
    if(onSave) onSave();
  };
  el.addEventListener('click',e=>{if(e.target===el)el.remove();});
}

/* ── SHARE/EXPORT: imagen, ICS ──────────────────────────────────────── */
async function sharePlan(){
  if(!savedAgenda||!savedAgenda.schedule||!savedAgenda.schedule.length){
    showToast(t('plan_sin_plan'),'warn');return;
  }
  // Pedir nombre si no existe — solo la primera vez
  if(!_getDisplayName()){
    _promptDisplayName(()=>sharePlan());
    return;
  }
  let canvas,dataUrl;
  try{
    canvas=_buildAgendaCanvas();
    dataUrl=canvas.toDataURL('image/png');
    if(!dataUrl||dataUrl==='data:,') throw new Error('canvas vacío');
  }catch(e){showToast('Error al generar imagen','err');return;}

  // Web Share API con archivo (iOS Safari 15+, Chrome Android 86+)
  if(navigator.share&&navigator.canShare){
    canvas.toBlob(async blob=>{
      if(!blob){_dlDirect(dataUrl);return;}
      const cfg=FESTIVAL_CONFIG[_activeFestId]||{};
      const fname=`otrofestiv-${(cfg.shortName||'plan').toLowerCase().replace(/\s+/g,'-')}.png`;
      const file=new File([blob],fname,{type:'image/png'});
      if(navigator.canShare({files:[file]})){
        try{
          await navigator.share({files:[file],title:`Mi Plan · ${cfg.name||'Otrofestiv'}`});
          showToast('Compartido ✓','info');
        }catch(e){if(e.name!=='AbortError') _dlDirect(dataUrl);}
      }else{_dlDirect(dataUrl);}
    },'image/png');
  }else{
    // Fallback desktop: descarga directa
    _dlDirect(dataUrl);
  }
}

/* ── SHARE/EXPORT: imagen, ICS ──────────────────────────────────────── */
function shareAsImage(){
  if(!savedAgenda||!savedAgenda.schedule||!savedAgenda.schedule.length){
    showToast(t('plan_sin_plan'),'warn'); return;
  }

  // ── Guardia de integridad del plan ────────────────────────────
  // Antes de generar la imagen verificamos tres condiciones:
  // 1. Que todas las películas del plan siguen en la watchlist
  // 2. Que no hay conflictos internos entre funciones del plan
  // 3. Que al menos una función no ha pasado ya
  const issues=[];

  // 1. Películas del plan ya no en watchlist
  const notInWL=savedAgenda.schedule.filter(s=>!watchlist.has(s._title));
  if(notInWL.length){
    const names=notInWL.map(s=>s._title.length>20?s._title.slice(0,18)+'…':s._title).join(', ');
    issues.push(`${notInWL.length} película${notInWL.length>1?'s':''} ${t('plan_no_intereses')}: ${names}`);
  }

  // 2. Conflictos internos entre funciones del plan
  const sched=savedAgenda.schedule;
  const conflicting=[];
  for(let i=0;i<sched.length;i++){
    for(let j=i+1;j<sched.length;j++){
      if(sched[i].day===sched[j].day && screensConflict(sched[i],sched[j])){
        conflicting.push(sched[i]._title);
      }
    }
  }
  if(conflicting.length){
    const names=[...new Set(conflicting)].map(t=>t.length>20?t.slice(0,18)+'…':t).join(', ');
    issues.push(`Hay actividades con horario solapado: ${names}`);
  }

  // 3. Plan completamente pasado
  const stillActive=savedAgenda.schedule.some(s=>!screeningPassed(s));
  if(!stillActive) issues.push('Todas las actividades de tu plan ya pasaron');

  // Si hay problemas: mostrar advertencia con opción de continuar igual
  if(issues.length){
    const msg=`<b>${t('plan_desactualizado')}</b><br><br>`
      +issues.map(i=>`• ${i}`).join('<br>')
      +`<br><br>¿Compartir la imagen de todas formas?`;
    showActionModal(
      `${ICONS.share} Compartir imagen`,
      msg,
      'Compartir igual',
      ()=>{_generateAndShare();},
      'Revisar plan primero'
    );
    return;
  }

  _generateAndShare();
}

function _generateAndShare(){
  let canvas,dataUrl;
  try{
    canvas=_buildAgendaCanvas();
    dataUrl=canvas.toDataURL('image/png');
    if(!dataUrl||dataUrl==='data:,') throw new Error('canvas vacío');
  }catch(e){
    showToast('Error al generar imagen','err'); return;
  }
  _showImageModal(dataUrl,canvas);
}

function _buildAgendaCanvas(){
  const cfg=FESTIVAL_CONFIG[_activeFestId]||{};
  const festDays=cfg.days||DAY_KEYS.map(k=>({k,lbl:k.slice(0,3).toUpperCase(),d:parseInt(k.slice(-2))||''}));
  const DAYS=festDays.map(d=>d.k);
  const DS=festDays.map(d=>d.lbl);
  const DN=festDays.map(d=>String(d.d));
  const byDay={};
  DAYS.forEach(d=>{byDay[d]=[];});
  (savedAgenda.schedule||[]).forEach(s=>{if(byDay[s.day])byDay[s.day].push(s);});
  DAYS.forEach(d=>{byDay[d].sort((a,b)=>a.time.localeCompare(b.time));});
  const active=DAYS; // Todos los días del festival — registro completo independiente del plan
  const nC=active.length||1;
  // DPR adaptativo: iOS limita canvas a ~4096px por dimensión — calcular tras conocer nC
  const _W_RAW=48+nC*200-10; // PAD*2 + nC*CW + (nC-1)*CGAP
  const DPR=Math.max(1,Math.min(window.devicePixelRatio||2,3,Math.floor(4096/_W_RAW)));
  const cleanDur=s=>String(s.duration||'').replace(/\s*min\s*min/i,'min').trim();
  const PAD=24,HDR=72,COL_HDR=46,CW=190,CGAP=10,CARD_PAD=12,CARD_R=8,CARD_GAP=8;
  const FONT_T=12,LINE_T=16,MAX_TL=3,CARD_MIN=90;
  const cv0=document.createElement('canvas');
  const c0=cv0.getContext('2d');
  c0.font=`600 ${FONT_T}px system-ui,-apple-system,sans-serif`;
  const cHts={};
  active.forEach(day=>{
    cHts[day]=byDay[day].map(s=>{
      const tl=_measureLines(c0,s._title||'',CW-CARD_PAD*2-6,MAX_TL);
      return Math.max(CARD_PAD+18+4+tl*LINE_T+4+14+CARD_PAD,CARD_MIN);
    });
  });
  const maxColH=active.reduce((mx,day)=>{
    const h=cHts[day].reduce((s,h)=>s+h+CARD_GAP,0)-CARD_GAP;
    return Math.max(mx,h);
  },0);
  const W=PAD*2+nC*CW+(nC-1)*CGAP;
  const H=HDR+PAD+COL_HDR+CARD_GAP+Math.max(0,maxColH)+PAD*2;
  const cv=document.createElement('canvas');
  cv.width=W*DPR;cv.height=H*DPR;
  const c=cv.getContext('2d');
  c.scale(DPR,DPR);
  c.fillStyle='#0A0A0A';c.fillRect(0,0,W,H);
  // Banner: --surf-2 (#1A1A1A) — gris sobrio de la paleta
  c.fillStyle='#1A1A1A';c.fillRect(0,0,W,HDR);
  // Wordmark: "Otro" blanco + "festiv" ámbar — igual que en la app
  c.font='800 22px system-ui,-apple-system,sans-serif';
  c.textBaseline='alphabetic';
  c.fillStyle='#FFFFFF';
  const otroW=c.measureText('Otro').width;
  c.fillText('Otro',PAD,HDR/2+4);
  c.fillStyle='#D4900A';
  c.fillText('festiv',PAD+otroW,HDR/2+4);
  // Subtítulo: --gray (#888888)
  c.fillStyle='#888888';
  c.font='500 11px system-ui,-apple-system,sans-serif';
  const _dn=_getDisplayName();
  const _sub=(_dn?_dn+' · ':'')+'Mi Plan · '+(cfg.name||'Festival')+' · '+active.length+' día'+(active.length!==1?'s':'');
  c.fillText(_sub,PAD,HDR/2+20);
  active.forEach((day,ci)=>{
    const x=PAD+ci*(CW+CGAP);
    const di=DAYS.indexOf(day);
    const films=byDay[day];
    const hy=HDR+PAD;
    c.fillStyle='rgba(212,144,10,0.12)';_rr(c,x,hy,CW,COL_HDR,8);c.fill();
    c.fillStyle='rgba(212,144,10,0.5)';c.fillRect(x,hy+COL_HDR-1,CW,1);
    c.fillStyle='#D4900A';
    c.font='700 9px system-ui,-apple-system,sans-serif';
    c.textBaseline='top';c.fillText(DS[di],x+12,hy+9);
    c.fillStyle='#FFFFFF';
    c.font='700 20px system-ui,-apple-system,sans-serif';
    c.fillText(DN[di],x+12,hy+20);
    let cardY=hy+COL_HDR+CARD_GAP;
    films.forEach((s,fi)=>{
      const ch=cHts[day][fi];
      const prio=prioritized&&prioritized.has&&prioritized.has(s._title);
      const dur=cleanDur(s);
      c.fillStyle=prio?'rgba(212,144,10,0.18)':'rgba(255,255,255,0.06)';
      _rr(c,x,cardY,CW,ch,CARD_R);c.fill();
      c.fillStyle=prio?'#D4900A':'rgba(212,144,10,0.35)';
      _rr(c,x,cardY,4,ch,CARD_R);c.fill();
      const tx=x+CARD_PAD+6;let ty=cardY+CARD_PAD;
      c.fillStyle='#D4900A';
      c.font='700 14px system-ui,-apple-system,sans-serif';
      c.textBaseline='top';c.fillText(s.time,tx,ty);
      if(dur){const hw=c.measureText(s.time).width;c.fillStyle='#666';c.font='400 10px system-ui,-apple-system,sans-serif';c.fillText(' · '+dur,tx+hw,ty+2);}
      ty+=22;
      c.fillStyle='#FFF';c.font=`600 ${FONT_T}px system-ui,-apple-system,sans-serif`;
      ty=_drawWrapped(c,s._title||'',tx,ty,CW-CARD_PAD*2-6,LINE_T,MAX_TL);
      if(s.venue){const _vc=vcfg(s.venue);const _vraw=_vc.short||s.venue;const v=_vraw.length>30?_vraw.slice(0,28)+'…':_vraw;c.fillStyle='#5A5A5A';c.font='400 10px system-ui,-apple-system,sans-serif';c.textBaseline='top';c.fillText(v,tx,cardY+ch-CARD_PAD-11);}
      cardY+=ch+CARD_GAP;
    });
  });
  c.fillStyle='rgba(212,144,10,0.2)';c.fillRect(0,H-1,W,1);
  return cv;
}

function _measureLines(c,text,maxW,maxLines){
  const words=text.split(' ');let line='',lines=1;
  for(let i=0;i<words.length;i++){
    const t=line?line+' '+words[i]:words[i];
    if(c.measureText(t).width>maxW&&line){if(lines>=maxLines)return maxLines;lines++;line=words[i];}
    else{line=t;}
  }
  return lines;
}

function _drawWrapped(c,text,x,y,maxW,lh,maxLines){
  c.textBaseline='top';
  const words=text.split(' ');let line='',ln=0;
  for(let i=0;i<words.length;i++){
    const t=line?line+' '+words[i]:words[i];
    if(c.measureText(t).width>maxW&&line){
      if(ln>=maxLines-1){c.fillText(line+'…',x,y+ln*lh);return y+ln*lh+lh;}
      c.fillText(line,x,y+ln*lh);line=words[i];ln++;
    }else{line=t;}
  }
  if(line)c.fillText(line,x,y+ln*lh);
  return y+ln*lh+lh;
}

function _rr(c,x,y,w,h,r){
  r=Math.min(r,w/2,h/2);
  c.beginPath();c.moveTo(x+r,y);c.lineTo(x+w-r,y);c.quadraticCurveTo(x+w,y,x+w,y+r);
  c.lineTo(x+w,y+h-r);c.quadraticCurveTo(x+w,y+h,x+w-r,y+h);
  c.lineTo(x+r,y+h);c.quadraticCurveTo(x,y+h,x,y+h-r);
  c.lineTo(x,y+r);c.quadraticCurveTo(x,y,x+r,y);c.closePath();
}

function _showImageModal(dataUrl,canvas){
  const prev=document.getElementById('img-share-modal');if(prev)prev.remove();
  const isIOS=/iPad|iPhone|iPod/.test(navigator.userAgent);
  const ov=document.createElement('div');
  ov.id='img-share-modal';
  ov.style.cssText='position:fixed;inset:0;background:var(--overlay-92);z-index:9999;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:20px;box-sizing:border-box;gap:var(--sp-btn)';
  const hint=document.createElement('p');
  hint.style.cssText='color:var(--gray);font-size:var(--t-caption);font-family:system-ui;text-align:center;margin:0;line-height:1.6';
  hint.textContent=isIOS?t('misc_mantener'):t('misc_descargar_guardar');
  ov.appendChild(hint);
  const img=document.createElement('img');
  img.src=dataUrl;
  img.style.cssText='max-width:100%;max-height:62vh;border-radius:var(--r);display:block;box-shadow:0 8px 32px var(--overlay-70)';
  ov.appendChild(img);
  const row=document.createElement('div');
  row.style.cssText='display:flex;gap:10px;width:100%;max-width:320px';
  if(!isIOS){
    const btnDl=document.createElement('button');
    btnDl.textContent='⬇ Descargar';
    btnDl.style.cssText='flex:1;padding:var(--sp-btn);background:var(--amber);color:var(--black);border:none;border-radius:var(--r-md);font-size:var(--t-base);font-family:system-ui;font-weight:var(--w-bold);cursor:pointer';
    btnDl.onclick=function(){
      if(navigator.share&&navigator.canShare){
        canvas.toBlob(blob=>{
          if(!blob){_dlDirect(dataUrl);return;}
          const file=new File([blob],'otrofestiv-miplan.png',{type:'image/png'});
          if(navigator.canShare({files:[file]})){navigator.share({files:[file]}).then(()=>{ov.remove();showToast('Compartido ✓','info');}).catch(()=>_dlDirect(dataUrl));}
          else{_dlDirect(dataUrl);}
        },'image/png');
      }else{_dlDirect(dataUrl);}
    };
    row.appendChild(btnDl);
  }
  const btnX=document.createElement('button');
  btnX.textContent=t('misc_cerrar');
  btnX.style.cssText=(isIOS?'flex:1;':'')+'padding:var(--sp-btn) var(--sp-5);background:rgba(255,255,255,0.08);color:var(--gray2);border:none;border-radius:var(--r-md);font-size:var(--t-base);font-family:system-ui;cursor:pointer';
  btnX.onclick=()=>ov.remove();
  row.appendChild(btnX);
  ov.appendChild(row);
  ov.addEventListener('click',e=>{if(e.target===ov)ov.remove();});
  document.body.appendChild(ov);
}

function _dlDirect(dataUrl){
  const a=document.createElement('a');
  a.href=dataUrl;a.download='otrofestiv-miplan.png';
  a.style.cssText='position:fixed;top:-999px;left:-999px;opacity:0';
  document.body.appendChild(a);a.click();
  setTimeout(()=>{document.body.removeChild(a);showToast('Imagen guardada ✓','info');},200);
}
async function exportICS(){
  if(!savedAgenda||!savedAgenda.schedule.length){showToast(t('plan_sin_plan'),'warn');return;}
  const pad=n=>String(n).padStart(2,'0');
  const fmt=dt=>`${dt.getFullYear()}${pad(dt.getMonth()+1)}${pad(dt.getDate())}T${pad(dt.getHours())}${pad(dt.getMinutes())}00`;
  // Convierte tiempo 12h (8:00 PM) → 24h (20:00) para _festDate
  const to24h=t=>{if(!t)return'12:00';const m=t.match(/(\d+):(\d+)\s*(AM|PM)/i);if(!m)return t;let h=parseInt(m[1]),mn=m[2],ap=m[3].toUpperCase();if(ap==='PM'&&h!==12)h+=12;if(ap==='AM'&&h===12)h=0;return pad(h)+':'+mn;};
  const _icsCfg=FESTIVAL_CONFIG[_activeFestId]||{};
  const _icsId=(_icsCfg.shortName||'festival').toLowerCase().replace(/\s+/g,'');
  const lines=['BEGIN:VCALENDAR','VERSION:2.0',`PRODID:-//Otrofestiv//${_icsId}//ES`,'CALSCALE:GREGORIAN','METHOD:PUBLISH'];
  savedAgenda.schedule.forEach(s=>{
    const dateStr=FESTIVAL_DATES[s.day];if(!dateStr) return;
    const start=_festDate(dateStr,to24h(s.time));
    if(isNaN(start.getTime())) return; // skip si fecha inválida
    const dur=s.duration?parseInt(String(s.duration)):90;
    const end=new Date(start.getTime()+(isNaN(dur)?90:dur)*60000);
    const clean=str=>(str||'').replace(/[\r\n,;\\]/g,' ').trim();
    lines.push('BEGIN:VEVENT',
      `DTSTART:${fmt(start)}`,`DTEND:${fmt(end)}`,
      `SUMMARY:${clean(s._title)}`,
      `LOCATION:${clean(s.venue)}`,
      `DESCRIPTION:${clean(_icsCfg.name||'Festival')} - ${clean(s.section)} - ${clean(s.duration)}`,
      `UID:otrofestiv-${_icsId}-${s._title?.replace(/\s/g,'')}-${fmt(start)}@otrofestiv.app`,
      'END:VEVENT');
  });
  lines.push('END:VCALENDAR');
  const icsText=lines.join('\r\n');
  const fileName=`otrofestiv-${_icsId}.ics`;
  // Capacitor nativo: Filesystem + Share para invocar Calendar.app
  if(window.Capacitor?.isNativePlatform()){
    const b64=btoa(unescape(encodeURIComponent(icsText)));
    try{
      const {Filesystem,Share}=window.Capacitor.Plugins;
      const result=await Filesystem.writeFile({
        path:fileName,
        data:b64,
        directory:'CACHE'
      });
      await Share.share({
        title:'Otrofestiv — Mi Plan',
        files:[result.uri]
      });
    }catch(e){
      console.error('ICS share error:',e);
      showToast('No se pudo abrir Calendario','warn');
    }
  } else {
    const blob=new Blob([icsText],{type:'text/calendar;charset=utf-8'});
    const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=fileName;a.click();
  }
  showToast(t('misc_calendario_listo'),'info');
}
// ── RESULT HTML ──
let cachedResult=null;

// ── forceInclude — crea variante custom con la película forzada ──────
function forceInclude(title){
  if(festivalEnded()){showToast(t('notice_fest_term'),'info');return;}
  if(!cachedResult||!cachedResult.scenarios.length) return;
  const sc=cachedResult.scenarios[cachedResult.currentIdx];

  // Intentar encajar la película en el schedule actual
  const newSchedule=squeezeExcluded(sc.schedule,[title]);
  const included=newSchedule.find(s=>s._title===title&&s._squeezed);

  if(!included){
    showToast(t('plan_sin_horario'),'info');
    return;
  }

  // Construir nuevo escenario custom
  const includedTitles=new Set(newSchedule.map(s=>s._title));
  const pending=[...watchlist].filter(t=>!watched.has(t));
  const newScenario={
    schedule:newSchedule,
    excluded:pending.filter(t=>!includedTitles.has(t)),
    _custom:true,
    incompatiblePriorities:sc.incompatiblePriorities,
    trueMax:sc.trueMax,
    maxWithPriorities:sc.maxWithPriorities,
    priorityCost:sc.priorityCost,
    dayBalance:sc.dayBalance
  };

  // Deduplicar — si ya existe un escenario idéntico, saltar a él
  const newKey=newSchedule.map(s=>(s._title||'')+'@'+s.day+s.time).sort().join('|');
  const existingIdx=cachedResult.scenarios.findIndex(s=>{
    const k=s.schedule.map(x=>(x._title||'')+'@'+x.day+x.time).sort().join('|');
    return k===newKey;
  });

  if(existingIdx>-1){
    cachedResult.currentIdx=existingIdx;
    showToast('Escenario ya existente','info');
  } else {
    cachedResult.scenarios.push(newScenario);
    cachedResult.currentIdx=cachedResult.scenarios.length-1;
  }
  renderAgenda();
}

// buildResultHTML → src/view/components.js (Step 6a). Importado.

// ═══════════════════════════════════════════════════════════════
// 13 · RENDER — VISTAS PRINCIPALES
//      renderCartelera, togglePriority, showToast, renderAgenda
// ═══════════════════════════════════════════════════════════════
// Controller (p7a) — branchy: prioritize/unprioritize con prio limit + modal confirm en Planear
function togglePriority(title,cost){
  // 1. READ
  const {prioritized, watchlist, watched, PRIO_LIMIT} = state.snapshot();
  // 2. GUARD + 3. MUTATE — branch A: unprioritize
  if(prioritized.has(title)){
    // Si estamos en Planear, confirmar antes de quitar (modal callback variant)
    if(activeMNav==='mnav-planner'){
      const short=title.length>40?title.slice(0,38)+'…':title;
      showActionModal(t('plan_quitar_prioridad'),
        `<b>${short}</b><br><br>${t('plan_sigue_intereses')}`,
        t('plan_quitar_prioridad'),()=>{
          state.update('prioritized', s=>state._delFromSet(s,title));savePrio();updateCardState(title);
          showToast(`${ICONS.star} ${t('toast_prioridad_quitada')}`,'info');
          switchMainNav('mnav-seleccion');showAgView();   // render automático vía pipeline + nav
        });return;
    }
    state.update('prioritized', s=>state._delFromSet(s,title));
    // 4. PERSIST + surgical (render automático vía pipeline)
    savePrio();updateCardState(title);
    showToast(`${ICONS.star} ${t('toast_prioridad_quitada')}`,'info');
  } else {
    // Branch B: prioritize (con limit check)
    if(prioritized.size>=PRIO_LIMIT){
      openPrioLimit(title);return;
    }
    const _addWL=!watchlist.has(title);
    state.transaction(() => {
      state.update('prioritized', s=>state._addToSet(s,title));
      if(_addWL) state.batchUpdate({watchlist:state._addToSet(watchlist,title), watched:state._delFromSet(watched,title)});
    });
    savePrio();if(_addWL){saveWL();saveWatched();}updateCardState(title);
    showToast(`${ICONS.starFill} ${t('cta_priorizada')} · ${prioritized.size+1}/${PRIO_LIMIT}`,'info');
  }
  if(activeView==='day') updateHorarioPrioBtn(title);   // surgical: botón prio del pel-sheet
}
// showToast → src/view/feedback.js (Step 6b). Importado.
let _toastActionFn=null;
function showActionToast(msg,actionLabel,actionFn,duration=4000){
  _toastActionFn=actionFn;
  let t=document.getElementById('prio-toast');
  if(!t){t=document.createElement('div');t.id='prio-toast';document.body.appendChild(t);}
  t.className='prio-toast action';
  t.innerHTML=`<span>${msg}</span><button class="toast-action-btn" data-action="dismissToastAction">${actionLabel}</button>`;
  t.style.opacity='1';t.style.pointerEvents='all';
  clearTimeout(t._to);t._to=setTimeout(()=>{t.style.opacity='0';t.style.pointerEvents='none';},duration);
}

// ── POST-SELECTION SQUEEZE ──
// Tras elegir una opción, intenta insertar películas excluidas de la watchlist
// que quepan en los huecos reales del plan elegido (usando screensConflict ±10 min).
// Puede superar trueMax porque ese era el máximo dentro del árbol explorado,
// no el máximo real del calendario.
function squeezeExcluded(schedule, excludedTitles){
  const result=[...schedule];
  // Ordenar excluidas por score descendente — misma lógica que el algoritmo
  const scored=excludedTitles.map(t=>{
    const screens=FILMS.filter(f=>f.title===t&&!screeningPassed(f)&&!isScreeningBlocked(f));
    return{title:t,screens,score:scoreFilm(t,screens,prioritized.has(t),[...watchlist])};
  }).filter(g=>g.screens.length>0).sort((a,b)=>b.score-a.score);

  scored.forEach(({title,screens})=>{
    // Ordenar funciones por estrategia — menos conflictos + fin temprano
    const sorted=sortScreensByStrategy(screens,[...scored]);
    for(const s of sorted){
      if(!result.some(c=>screensConflict(c,s))){
        result.push({...s,_title:title,_squeezed:true});
        break; // encontró slot, pasar al siguiente título
      }
    }
  });
  return result;
}

/* ── POST-VIEW RATING SHEET ── */
let _pvTitle='', _pvRating=0;

function _pvStarSVG(fill){
  if(fill==='full')  return`<svg width="34" height="34" viewBox="0 0 24 24"><polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26" fill="var(--amber)" stroke="var(--amber)" stroke-width="1.75" stroke-linejoin="round"/></svg>`;
  if(fill==='half')  return`<svg width="34" height="34" viewBox="0 0 24 24"><defs><linearGradient id="pvhg"><stop offset="50%" stop-color="var(--amber)"/><stop offset="50%" stop-color="transparent"/></linearGradient></defs><polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26" fill="url(#pvhg)" stroke="var(--amber)" stroke-width="1.5" stroke-linejoin="round"/></svg>`;
  return`<svg width="34" height="34" viewBox="0 0 24 24" style="opacity:.15"><polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26" fill="none" stroke="var(--amber)" stroke-width="1.75" stroke-linejoin="round"/></svg>`;
}

function _pvRenderStars(val){
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
  if(hint) hint.textContent=val>0?`${val} de 5`:t('misc_deslizar');
  if(hint) hint.style.color=val>0?'var(--amber)':'var(--gray)';
  if(btn)  btn.disabled=val===0;
}

function openPostViewRating(title, day, time, venue, duration){
  _pvTitle=title;
  _pushSheetState();
  _pvRating=filmRatings[title]||0;

  const{displayTitle}=parseProgramTitle(title);
  const f=FILMS.find(fi=>fi.title===title);
  const DAY_A={Martes:'MAR',Miércoles:'MIÉ',Jueves:'JUE',Viernes:'VIE',Sábado:'SÁB',Domingo:'DOM'};

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
    if(day) parts.push(DAY_A[day]||day);
    if(venue) parts.push(venue.split('·')[0].trim().split('‒')[0].trim());
    if(duration) parts.push(duration);
    ctx.textContent=parts.join(' · ');
  }

  // Estrellas y rango
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

// Controller (p7a)
function savePVRating(){
  // 1. READ — UI state ephemeral (_pvRating, _pvTitle son module-level)
  // 2. GUARD — solo guardar si rating válido
  if(_pvRating>0){
    // 3. MUTATE
    state.update('filmRatings', o => ({...o, [_pvTitle]: _pvRating}));
    // 4. PERSIST
    storage.setFilmRatings(filmRatings);
    // 5. RENDER + UI EFFECTS — toast
    const stars=['','★','★★','★★★','★★★★','★★★★★'];
    showToast(stars[Math.round(_pvRating)]||'★ Calificada','info');
  }
  closePVRating();
  // Render automático vía pipeline (filmRatings). Si rating=0 no hay mutación →
  // no re-render (no-op visual: el prompt de calificar sigue igual).
}

// closePVRating → src/view/sheets.js (Step 6b). Importado.

// Controller (p7a) — branchy toggle desde Mi Plan
function markWatchedFromPlan(title, day, time, venue, duration, e){
  if(e) e.stopPropagation();
  // 1. READ
  const {FILMS, watched, watchlist} = state.snapshot();
  // 2. GUARD + 3. MUTATE — branch A: desmarcar (ya watched)
  if(watched.has(title)){
    state.batchUpdate({
      watched: state._delFromSet(watched, title),
      watchlist: watchlist.has(title) ? watchlist : state._addToSet(watchlist, title),
    });
    // 4. PERSIST + surgical (render automático vía pipeline)
    saveState('wl','watched');
    updateCardState(title);
    showToast(t('plan_vuelta_pendientes'),'info');
    return;
  }
  // Branch B: marcar como vista + post-view rating modal
  // 3. MUTATE
  state.update('watched', s=>state._addToSet(s, title));
  // 4. PERSIST + surgical (render automático vía pipeline)
  saveWatched();
  updateCardState(title);
  // Cortos: sin calificación general
  if(!FILMS.find(fi=>fi.title===title)?.is_cortos) setTimeout(()=>openPostViewRating(title, day, time, venue, duration), 250);
}

/* ── CONFLICT SHEET ── */
let _conflictPending=null; // {title, day, time, screen, existingTitle}

function openConflictSheet(incomingTitle, incomingScreen, existingEntry){
  const{displayTitle:inDT}=parseProgramTitle(incomingTitle);
  const{displayTitle:exDT}=parseProgramTitle(existingEntry._title||'');
  const DAY_A={Martes:'MAR',Miércoles:'MIÉ',Jueves:'JUE',Viernes:'VIE',Sábado:'SÁB',Domingo:'DOM'};

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
  setEl('cs-incoming-when', `${DAY_A[incomingScreen.day]||''} · ${incomingScreen.time} · ${inF?.duration||''}`);
  setEl('cs-existing-name', exDT);
  const exWhen=existingEntry.day?`${DAY_A[existingEntry.day]||''} · ${existingEntry.time} · ${exF?.duration||''}`:'';
  setEl('cs-existing-when', exWhen);

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

// Controller (p7a) — handler del btn de "Reemplazar" en conflict sheet
function confirmConflictReplace(){
  // 1. READ + 2. GUARD
  if(!_conflictPending) return;
  const{incomingTitle, incomingScreen, existingEntry}=_conflictPending;
  // 3. MUTATE — quitar la existente e insertar la nueva
  state.update('savedAgenda', a => ({
    ...a,
    schedule: [
      ...a.schedule.filter(s=>!(s._title===existingEntry._title&&s.day===existingEntry.day&&s.time===existingEntry.time)),
      {...incomingScreen,_title:incomingTitle}
    ].sort((x,y)=>x.day_order!==y.day_order?x.day_order-y.day_order:toMin(x.time)-toMin(y.time))
  }));
  // 4. PERSIST + 5. RENDER + UI EFFECTS
  saveSavedAgenda();
  const{displayTitle:dt}=parseProgramTitle(incomingTitle);
  closeConflictSheet();
  showToast(`${ICONS.calendar} ${dt.length>22?dt.slice(0,20)+'…':dt} en tu plan`,'info');
  renderAgenda();
}

function closeConflictSheet(){
  _conflictPending=null;
  document.getElementById('conflict-sheet-overlay').classList.remove('open');
  document.getElementById('conflict-sheet').classList.remove('open');
}

function openPrioLimit(newTitle){
  // Eyebrow con contador
  const eyebrow=document.getElementById('prio-limit-eyebrow-txt');
  const count=document.getElementById('prio-limit-count');
  if(eyebrow) eyebrow.textContent=`Prioridades · ${PRIO_LIMIT}/${PRIO_LIMIT}`;
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
    const DAY_A={Martes:'MAR',Miércoles:'MIÉ',Jueves:'JUE',Viernes:'VIE',Sábado:'SÁB',Domingo:'DOM'};
    const items=[...prioritized].map(t=>{
      const{displayTitle:dt}=parseProgramTitle(t);
      const f=FILMS.find(fi=>fi.title===t&&!screeningPassed(fi));
      const when=f?`${DAY_A[f.day]||f.day} · ${f.time}`:'';
      const poster=getFilmPoster(f)||'';
      const safeSwap=t.replace(/'/g,"&#39;");
      const safeNew=newTitle.replace(/'/g,"&#39;");
      return`<div class="prio-limit-item">
        ${poster?`<img class="prio-limit-thumb" src="${poster}" onerror="this.remove()" alt="" loading="lazy">`:'<div class="prio-limit-thumb"></div>'}
        <div class="prio-limit-info">
          <div class="prio-limit-name">${dt}</div>
          <div class="prio-limit-when">${when}</div>
        </div>
        <button class="prio-limit-swap" data-action="swapPriority" data-rmtitle="${safeSwap}" data-addtitle="${safeNew}">Cambiar</button>
      </div>`;
    }).join('');
    list.innerHTML=items;
  }

  document.getElementById('prio-limit-overlay').classList.add('open');
  document.getElementById('prio-limit-sheet').classList.add('open');
}

// closePrioLimit → src/view/sheets.js (Step 6b). Importado.

function swapPriority(removeTitle, addTitle){
  state.update('prioritized', s => state._addToSet(state._delFromSet(s, removeTitle), addTitle));
  savePrio();
  updateCardState(removeTitle);
  updateCardState(addTitle);
  updateAgTab();
  closePrioLimit();
  const{displayTitle}=parseProgramTitle(addTitle);
  showToast(`${ICONS.starFill} ${displayTitle} priorizada`,'info');
}

function openPlanConfirm(schedule){
  // Ordenar por posición en DAY_KEYS (funciona para cualquier festival)
  const sorted=[...schedule].sort((a,b)=>{
    const ai=DAY_KEYS.indexOf(a.day),bi=DAY_KEYS.indexOf(b.day);
    return (ai<0?999:ai)-(bi<0?999:bi)||a.time.localeCompare(b.time);
  });
  const total=sorted.length;
  const days=[...new Set(sorted.map(s=>s.day))];
  const dayRange=days.length===1?dayLabel(days[0]):`${dayLabel(days[0])}–${dayLabel(days[days.length-1])}`;

  // Sub: N películas · DÍAS
  const sub=document.getElementById('plan-confirm-sub');
  if(sub) sub.innerHTML=`<span class="mr-1 count-badge cb-neutral">${total}</span> · ${dayRange}`;

  // Lista — máx 3 + resumen del resto
  const show=sorted.slice(0,3);
  const rest=total-show.length;
  const filmsEl=document.getElementById('plan-confirm-films');
  if(filmsEl){
    filmsEl.innerHTML=show.map(s=>{
      const{displayTitle:dt}=parseProgramTitle(s._title||'');
      const short=dt.length>28?dt.slice(0,26)+'…':dt;
      return`<div class="plan-confirm-film">
        <div class="plan-confirm-dot"></div>
        <div class="plan-confirm-time">${s.time}</div>
        <div class="plan-confirm-name">${short}</div>
      </div>`;
    }).join('')+(rest>0?`<div class="plan-confirm-film" style="color:var(--gray)"><div class="bg-gray plan-confirm-dot"></div><div class="plan-confirm-name">+ ${rest} ${t('misc_mas')} ${dayRange}</div></div>`:'');
  }

  const _pcSheet=document.getElementById('plan-confirm-sheet');
  if(_pcSheet){ _pcSheet.style.display=''; requestAnimationFrame(()=>_pcSheet.classList.add('open')); }
  document.getElementById('plan-confirm-overlay').classList.add('open');
}

function closePlanConfirm(goToPlan){
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

function saveCurrentScenario(){
  if(!cachedResult||!cachedResult.scenarios.length) return;
  const _doSave=()=>{
    const _sc=cachedResult.scenarios[cachedResult.currentIdx];
    const _squeezed=squeezeExcluded(_sc.schedule,_sc.excluded||[]);
    state.set('savedAgenda', {schedule:_squeezed});
    saveSavedAgenda();
    openPlanConfirm(_squeezed);
  };
  // Si ya hay un plan guardado, pedir confirmación antes de reemplazarlo
  if(savedAgenda&&savedAgenda.schedule&&savedAgenda.schedule.length){
    const n=savedAgenda.schedule.length;
    showActionModal(
      `${ICONS.calendar} ${t('plan_reemplazar_plan')}`,
      `${t('notice_ya_tenes')} un plan con <b>${n} película${n!==1?'s':''}</b>.<br><br>${t('plan_reemplazar')}.`,
      t('misc_si_reemplazar'),
      _doSave,
      'Conservar mi plan actual'
    );
  } else {
    _doSave();
  }
}
function invalidateCalcResult(){
  // Called when availability changes — resets result prompt
  const _wrap=document.getElementById('ag-result-wrap');
  if(_wrap) _wrap.style.display='none';
  const res=document.getElementById('ag-result');
  if(!res){showAgView();return;}
  res.innerHTML='';
}

// ── Sprint 3: funciones puras que el Worker extrae del main thread ────────
// Al añadir o modificar una función de scheduling en el main thread,
// el Worker la recibe automáticamente. Sin copia manual, sin divergencia.
// EXCLUIDAS de extracción: simNow, festivalEnded — usan globals con nombre
// diferente en worker scope (_simTime→SIM_TIME, FESTIVAL_END→FESTIVAL_END_TS).
// Estas se proveen como worker-local en _mkCalcWorker._venueFns.
const _SCHED_PURE_FNS = [
  'toMin','parseDur','_festDate','_resolveVenue',
  'effectiveDuration','screensConflict','screeningPassed',
  'isScreeningBlocked','_djb2','_titleSeed','_mulberry32',
  'shuffle','scoreFilm','sortScreensByStrategy','computeScenarios'
];

function _mkCalcWorker(){
  try{
    // Globals worker-local (no acceso al main thread en Worker scope)
    const _workerGlobals=`
let FILMS=[], FESTIVAL_DATES={}, availability={};
let watched=new Set(), prioritized=new Set();
let TZ_OFFSET='-05:00', FESTIVAL_END_TS=0, SIM_TIME=null;
const DEFAULT_DURATION_MIN=90;
const FESTIVAL_BUFFER=15;
let _venueCoords={};
let _transport='transit';
`;
    // Funciones de venue — usan _venueCoords/_transport (estado worker-local)
    // simNow/festivalEnded — usan SIM_TIME/FESTIVAL_END_TS (nombres worker-local)
    // Estas no se extraen del main thread via .toString() por diferencia de globals.
    const _venueFns=`
function simNow(){return SIM_TIME?new Date(SIM_TIME):new Date();}
function festivalEnded(){return simNow()>new Date(FESTIVAL_END_TS);}
function _workerFindCoords(v){
  return _resolveVenue(v,_venueCoords);
}
function venueTravelMins(v1,v2){
  const c1=_workerFindCoords(v1),c2=_workerFindCoords(v2);
  if(!c1.lat||!c1.lng||!c2.lat||!c2.lng) return 0;
  const dlat=(c1.lat-c2.lat)*111,dlon=(c1.lng-c2.lng)*111*Math.cos(c1.lat*Math.PI/180);
  const km=Math.sqrt(dlat*dlat+dlon*dlon);
  if(km<0.15) return 0;
  const spd=_transport==='walking'?4:_transport==='transit'?10:12;
  return Math.max(5,Math.round(km/spd*60/5)*5);
}
function travelMins(venueA,venueB){ return venueTravelMins(venueA,venueB); }
`;
    // Extraer funciones puras del main thread via .toString()
    // Garantía: el Worker usa EXACTAMENTE el mismo código que el main thread.
    const _pureFns=_SCHED_PURE_FNS.map(name=>{
      const fn=eval(name); // eslint-disable-line no-eval
      return (typeof fn==='function')?fn.toString():'/* MISSING: '+name+' */';
    }).join('\n');
    // Handler worker-specific
    const _handler=`
self.onmessage=function(e){
  const d=e.data;
  FILMS=d.films;
  watched=new Set(d.watched);
  prioritized=new Set(d.prioritized);
  availability=d.availability;
  FESTIVAL_DATES=d.festivalDates;
  TZ_OFFSET=d.tzOffset||'-05:00';
  FESTIVAL_END_TS=d.festivalEndTs;
  SIM_TIME=d.simTime;
  _venueCoords=d.venueCoords||{};
  _transport=d.transport||'transit';
  try{
    const scenarios=computeScenarios(d.titles);
    self.postMessage({ok:true,scenarios});
  }catch(err){
    self.postMessage({ok:false,error:err.message});
  }
};
`;
    const src=_workerGlobals+_venueFns+_pureFns+_handler;
    const blob=new Blob([src],{type:'application/javascript'});
    const url=URL.createObjectURL(blob);
    const w=new Worker(url);
    URL.revokeObjectURL(url);
    return w;
  }catch(e){console.warn('[Worker] build failed:',e);return null;}
}

// Worker activo — referencia para cancelar si el tab va a background
let _activeCalcWorker=null;

// iOS: si el tab va a background con Worker corriendo, limpiar estado
document.addEventListener('visibilitychange',function(){
  if(document.hidden&&_activeCalcWorker){
    _activeCalcWorker.terminate();
    _activeCalcWorker=null;
    const btn=document.querySelector('.av-calc-btn');
    if(btn){btn.disabled=false;btn.textContent=t('av_ver_opciones');}
  }
});

function runCalc(){
  if(festivalEnded()){showToast(t('notice_fest_term'),'info');return;}
  // Cancelar Worker previo si existe
  if(_activeCalcWorker){_activeCalcWorker.terminate();_activeCalcWorker=null;}
  cachedResult=null;
  const btn=document.querySelector('.av-calc-btn');
  const res=document.getElementById('ag-result');
  if(btn){btn.disabled=true;btn.textContent=t('plan_calculando');}
  if(res) res.innerHTML=`<div class="ag-calc-prompt" style="opacity:.6">${t('plan_calculando_ops')}</div>`;

  // Build venue coords for Worker
  const _vcoords={};
  const _vcfg=(FESTIVAL_CONFIG[_activeFestId]||{}).venues||{};
  Object.entries(_vcfg).forEach(([k,v])=>{if(v.lat&&v.lng) _vcoords[k]={lat:v.lat,lng:v.lng};});

  const worker=_mkCalcWorker();
  if(worker){
    _activeCalcWorker=worker;
    // Watchdog: 15s timeout — previene Worker colgado en mobile
    const watchdog=setTimeout(()=>{
      if(_activeCalcWorker===worker){
        worker.terminate();
        _activeCalcWorker=null;
        console.warn('[Worker] timeout — falling back to main thread');
        _runCalcSync(btn,res);
      }
    },15000);
    // Web Worker path — non-blocking
    worker.onmessage=function(e){
      clearTimeout(watchdog);
      _activeCalcWorker=null;
      worker.terminate();
      if(btn){btn.disabled=false;btn.textContent=t('av_ver_opciones');}
      if(e.data.ok){
        const scenarios=e.data.scenarios;
        cachedResult={scenarios,currentIdx:0,_algorithmCount:scenarios.length};
        const _w1=document.getElementById('ag-result-wrap');if(_w1)_w1.style.display='';
        if(res) res.innerHTML=buildResultHTML(scenarios);
      }else{
        if(res) res.innerHTML=`<div class="ag-calc-prompt" style="color:var(--red)"><strong>${t('error_calcular')}</strong><br><code class="txt-xs">${e.data.error}</code></div>`;
      }
    };
    worker.onerror=function(err){
      clearTimeout(watchdog);
      _activeCalcWorker=null;
      worker.terminate();
      console.warn('[Worker] error, falling back to main thread',err);
      _runCalcSync(btn,res);
    };
    worker.postMessage({
      titles:[...watchlist],
      films:FILMS,
      watched:[...watched],
      prioritized:[...prioritized],
      availability,
      festivalDates:FESTIVAL_DATES,
      tzOffset:TZ_OFFSET,
      festivalEndTs:FESTIVAL_END.getTime(),
      simTime:_simTime,
      venueCoords:_vcoords,
      transport:FESTIVAL_TRANSPORT
    });
  }else{
    // Fallback: main thread con setTimeout
    setTimeout(()=>_runCalcSync(btn,res),80);
  }
}

function _runCalcSync(btn,res){
  try{
    const scenarios=computeScenarios([...watchlist]);
    cachedResult={scenarios,currentIdx:0,_algorithmCount:scenarios.length};
    const _w2=document.getElementById('ag-result-wrap');if(_w2)_w2.style.display='';
    if(res) res.innerHTML=buildResultHTML(scenarios);
  }catch(err){
    if(res) res.innerHTML=`<div class="ag-calc-prompt" style="color:var(--red)"><strong>${t('error_calcular')}</strong><br><code class="txt-xs">${err.message}</code></div>`;
  }finally{
    if(btn){btn.disabled=false;btn.textContent=t('av_ver_opciones');}
  }
}

function jumpToScenario(idx){
  if(!cachedResult) return;
  cachedResult.currentIdx=Math.max(0,Math.min(cachedResult.scenarios.length-1,idx));
  renderAgenda();
}

// renderFlowProgress → src/view/components.js (Step 6a). Importado.
// _scrollMiPlanToNow — auto-scroll del calendario de Mi Plan al tiempo actual.
// Se llama después del render, usa requestAnimationFrame para esperar el paint.
// Solo actúa cuando el festival está en curso (nowDayIdx >= 0).
// Centra la nowline verticalmente en el viewport del contenedor.

// _updateMiPlanBadge — muestra el número de funciones sin confirmar
// en el tab de Mi Plan. Ámbar, no rojo — es una tarea diferible, no un error.
// Se llama al final de renderAgenda() y cuando cambia watched.
// _toggleEveningFilms — muestra/oculta posters adicionales en EVENING.
// Sin CSS nuevo — usa hscroll-strip existente y link-gray-xs.
function _toggleEveningFilms(btn){
  const extra=document.getElementById('eve-films-extra');
  if(!extra) return;
  const open=extra.style.display!=='none';
  extra.style.display=open?'none':'contents';
  btn.style.display='none'; // ocultar el botón al expandir — ya no hace falta
}

// ── CALENDAR VIEW ──
let activeView='day',activeDay='Martes',activeVenue='all',activeSec='all',selectedIdx=null,activeMNav='mnav-cartelera';
let cartelaMode='pelicula'; // 'horario' | 'pelicula' (interno)
let programaSubMode='hoy'; // 'hoy' | 'manana' (explorar eliminado — activeDay==='all' lo reemplaza)
let interesesViewMode='grid';   // 'grid' | 'list' para Intereses
let miPlanViewMode='calendar';  // 'calendar' | 'list' para Mi Plan
let programaViewMode='grid';    // 'grid' | 'list'
let programaChip='all';         // chip activo en Explorar
let _programaChipMatchFn=null;  // función de match activa para filtrar
let _currentChips=[];           // chips dinámicos del festival activo

// Definición de chips de categoría — agrupan las secciones reales de FICCI
const PROGRAMA_CHIPS=[
  {id:'all',      label:'Todo',              match:null},
  {id:'colombia', label:'🇨🇴 Colombia',     match:s=>s.includes('Colombia')},
  {id:'ibero',    label:'🌎 Iberoamérica',  match:s=>s.includes('Iberoamérica')},
  {id:'inter',    label:'🌍 Internacional',  match:s=>s.includes('Internacional')},
  {id:'spaces',   label:'⏳ (s)paces',      match:s=>s.includes('paces')},
  {id:'afro',     label:'✊ Afro',           match:s=>s.includes('Afro')},
  {id:'indigena', label:'🪶 Indígena',       match:s=>s.includes('Indígena')},
  {id:'barrios',  label:'🏆 Barrios',        match:s=>s.includes('Barrios')},
  {id:'costas',   label:'🌊 Costas',         match:s=>s.includes('Costas')},
  {id:'rivers',   label:'🎖️ Ben Rivers',    match:s=>s.includes('Rivers')},
  {id:'retro',    label:'📽️ Retrospectiva', match:s=>s.includes('Retrospectiva')},
  {id:'midnight', label:'🌙 Medianoche',    match:s=>s.includes('Medianoche')},
  {id:'españa',   label:'🇪🇸 Muestra España',  match:s=>s.includes('España')},
  {id:'suiza',    label:'🇨🇭 Muestra Suiza',   match:s=>s.includes('Suiza')},
  {id:'argentina',label:'🇦🇷 Muestra Argentina',match:s=>s.includes('Argentina')},
  {id:'brasil',   label:'🇧🇷 Casa Brasil',      match:s=>s.includes('Brasil')},
  {id:'especial', label:'⭐ Especiales',     match:s=>s.includes('Especiales')||s.includes('Animación')||s.includes('Indias')},
];
let expandedPelicula=''; // título expandido en vista Por Película

/* ── BÚSQUEDA EN CARTELERA ── */
// ── BÚSQUEDA GLOBAL ────────────────────────────────────────────────────────

/* ── NAV: navegación principal entre tabs ────────────────────────────── */
function switchMainNav(id){
  if(id==='mnav-miplan') activeMiPlanDay=null; // recalcula día actual al entrar
  activeMNav=id;
  document.querySelectorAll('.main-nav-tab').forEach(t=>t.classList.remove('on'));
  const el=document.getElementById(id);if(el) el.classList.add('on');
  // nav-row solo visible en tab Programa
  const navRow=document.getElementById('nav-row');
  if(navRow) navRow.classList.toggle('hidden', id!=='mnav-cartelera');
}
function showDayView(){
  activeView='day';
  switchMainNav('mnav-cartelera');
  // Mostrar buscador y mode bar
  document.getElementById('hdr-ag')?.style.setProperty('display','none');
  const modeBar=document.getElementById('programa-mode-bar');
  if(modeBar){
    modeBar.style.removeProperty('display');// removeProperty is more reliable than =""
    modeBar.setAttribute('data-sdv',Date.now());// tag for debugging
  }
  // Ocultar toggle legacy
  const toggle=document.getElementById('carta-mode-toggle');if(toggle) toggle.style.display='none';
  document.getElementById('filter-bars').style.display='';
  ['hint','cnt','grid','cartelera-stepper'].forEach(id=>{const el=document.getElementById(id);if(el) el.style.display='';});
  const _av=document.getElementById('ag-view');
  _av.classList.remove('visible');
  _av.style.display='none';
  document.getElementById('agtab').classList.remove('on');
  // Inicializar el sistema de modos
  initProgramaModeBar();
  _renderProgramaContent();
  requestAnimationFrame(_fixStickyOffset); // actualiza altura del chrome-blur
}
function showAgView(){
  activeView='agenda';
  const _toggle=document.getElementById('carta-mode-toggle');if(_toggle) _toggle.style.display='none';
  const _mbar=document.getElementById('programa-mode-bar');if(_mbar) _mbar.style.display='none';
  const _chips=document.getElementById('programa-chips');if(_chips) _chips.classList.add('hidden');
  const _paf=document.getElementById('programa-active-filter');if(_paf) _paf.classList.remove('visible');
  const _lista=document.getElementById('programa-list');if(_lista) _lista.classList.remove('visible');
  const _agH=document.getElementById('hdr-ag');
  if(_agH){
    _agH.style.display='';
    // ag-toggle-bar eliminado de Intereses (solo en Explorar)
  }
  document.getElementById('filter-bars').style.display='none';
  ['hint','cnt','grid','cartelera-stepper'].forEach(id=>{const el=document.getElementById(id);if(el) el.style.display='none';});
  const _av=document.getElementById('ag-view');
  _av.style.display='';
  _av.classList.add('visible');
  // Trigger lazy image loading for newly visible content
  requestAnimationFrame(()=>window.dispatchEvent(new Event('scroll')));
  _av.scrollTop=0;
  document.getElementById('agtab').classList.add('on');
  document.querySelectorAll('.dtab').forEach(t=>t.classList.remove('on'));
  renderAgenda();
  requestAnimationFrame(_fixStickyOffset); // actualiza altura del chrome-blur
}

const dtabs=document.getElementById('dtabs');
// DAYS → src/view/helpers.js (Step 6f). Importado; mutado in-place por loadFestival.
// DAY_ABBR → src/view/components.js (Step 6a). Importado.
// DAY_NUM → src/view/components.js (Step 6a). Importado.

// Auto-posicionar en el primer día vigente al cargar
// Los días pasados siguen accesibles con scroll hacia la izquierda
(()=>{
  const firstFuture=DAY_KEYS.find(d=>!dayFullyPassed(d));
  if(firstFuture&&dayFullyPassed(activeDay)){
    activeDay=firstFuture;
    dtabs.querySelectorAll('.dtab').forEach(t=>t.classList.toggle('on',t.dataset.day===firstFuture));
  }
  requestAnimationFrame(()=>{
    const activeBtn=dtabs.querySelector('.dtab.on');
    if(activeBtn) dtabs.scrollLeft=activeBtn.offsetLeft-dtabs.offsetLeft;
  });
})();

/* ── RENDER — CARTELERA: filtros, grid horario, grid película ────────── */

/* ── RATING SHEET ── */
let _ratingTitle='';

// starSVG → src/view/components.js (Step 6a). Importado.

// Pure half (p6b): construye el HTML de 5 estrellas según el rating actual.
// state param incluido por uniformidad — esta vista no lee state, todo viene
// del parámetro `current`.
// renderRatingStarsHTML → src/view/components.js (Step 6a). Importado.
// Impure caller (p6b): commit a DOM
function renderRatingStars(current){
  const el=document.getElementById('rating-stars');
  if(!el) return;
  el.innerHTML=renderRatingStarsHTML(state, current);
}

// Update rápido durante drag — solo actualiza los atributos SVG sin recrear DOM
function updateRatingStars(current){
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

let _currentRating=0;
function setRating(val){
  _currentRating=val;
  updateRatingStars(val); // rápido, sin recrear DOM
  const btn=document.getElementById('rating-action-btn');
  if(btn){
    if(val>0){btn.textContent=t('misc_guardar');btn.className='rating-action-btn save';}
    else{btn.textContent=t('misc_omitir');btn.className='rating-action-btn skip';}
  }
}

// Pointer Events API — unificado mouse+touch, con setPointerCapture
// para que el drag funcione correctamente en iOS dentro de transforms
function _initRatingInteraction(){
  const range=document.getElementById('rating-range');
  if(!range||range._ratingInit) return;
  range._ratingInit=true;
  range.addEventListener('input',()=>{
    setRating(parseInt(range.value)/2);
  });
}

function openRatingSheet(title){
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

function closeRatingSheet(){
  if(_currentRating>0){
    saveRating(_ratingTitle,_currentRating);
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

function starsDisplay(rating,size){
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

function togglePelPrio(title){
  title=normTitle(title);
  togglePriority(title);
  const btn=document.getElementById('pel-prio-btn')||document.getElementById('corto-prio-btn');
  if(!btn) return;
  const inPrio=prioritized.has(title);
  btn.innerHTML=(inPrio?ICONS.starFill:ICONS.star)+' '+(inPrio?t('cta_priorizada'):t('cta_priorizar'));
  btn.className='pel-sheet-action-btn'+(inPrio?' act-prio':' btn-secondary');
  // Priorizar auto-añade a watchlist — sincronizar el botón de Intereses
  const inWL=watchlist.has(title);
  const pelWlBtn=document.getElementById('pel-wl-btn');
  if(pelWlBtn){
    pelWlBtn.innerHTML=(inWL?ICONS.heartFill:ICONS.heart)+' '+(inWL?t('cta_en_intereses'):t('cta_intereses'));
    pelWlBtn.className='pel-sheet-action-btn'+(inWL?' act-on btn-primary':' btn-primary');
  }
  const cortoWlBtn=document.getElementById('corto-wl-btn');
  if(cortoWlBtn){
    cortoWlBtn.innerHTML=(inWL?ICONS.heartFill:ICONS.heart)+' '+(inWL?t('cta_en_intereses'):t('cta_intereses'));
    cortoWlBtn.className='pel-sheet-action-btn'+(inWL?' act-on btn-primary':' btn-primary');
  }
}

/* ── BOTTOM SHEET: apertura, cierre, acciones ───────────────────────── */
function togglePelWL(title,e){
  title=normTitle(title);
  const wasInWL=watchlist.has(title);
  toggleWL(title,e);
  const btn=document.getElementById('pel-wl-btn');
  if(!btn) return;
  const inWL=watchlist.has(title);
  btn.innerHTML=(inWL?ICONS.heartFill:ICONS.heart)+' '+(inWL?t('cta_en_intereses'):t('cta_intereses'));
  btn.className='pel-sheet-action-btn'+(inWL?' act-on btn-primary':' btn-primary');
  if(wasInWL&&!inWL) closePelSheet(); // quitar de intereses → cerrar sheet
  if(!wasInWL&&inWL){
    showActionToast(`${ICONS.heartFill} ${t('cta_en_intereses')}`,`${ICONS.star} ${t('cta_priorizar')}`,()=>togglePriority(title));
  }
}
// _dayChips — renderiza días únicos de un film como spans tappables (filtran por día)

function filterByVenue(venue){
  closePelSheet();
  activeVenue=venue;activeSec='all';selectedIdx=null;
  programaSubMode='hoy';
  programaChip='all';_programaChipMatchFn=null;
  // Si el día activo ya pasó, ir al primer día vigente
  if(dayFullyPassed(activeDay)){
    const _ff=DAY_KEYS.find(d=>!dayFullyPassed(d));
    if(_ff) activeDay=_ff;
  }
  // Regla global: navegación por día → lista por defecto
  programaViewMode=activeDay==='all'?'grid':'list';
  switchMainNav('mnav-cartelera');
  showDayView();
  // Actualizar label del filtro Lugar
  lugarClose();
}

function filterByDay(day){
  closePelSheet();
  activeDay=day;activeVenue='all';selectedIdx=null;
  cartelaMode='horario';
  document.querySelectorAll('.dtab').forEach(t=>t.classList.toggle('on',t.dataset.day===day));
  requestAnimationFrame(()=>{
    const activeBtn=document.querySelector('.dtab.on');
    if(activeBtn){const dt=document.getElementById('dtabs');if(dt)dt.scrollLeft=activeBtn.offsetLeft-dt.offsetLeft;}
  });
  switchMainNav('mnav-cartelera');
  _renderProgramaContent();
  _updateProgramaActiveFilter();
}

// ── pelicula-day tap → filterByDay ──────────────────────────
document.addEventListener('click', function(e){
  const day=e.target.closest('.pelicula-day');
  if(day&&day.dataset.day) filterByDay(day.dataset.day);
});

function filterBySection(section){
  // Navegar a Programa · Explorar con esa sección activa
  closePelSheet();
  activeSec=section;activeVenue='all';selectedIdx=null;
  programaSubMode='hoy';
  programaChip='all';
  _programaChipMatchFn=null;
  // Si el día activo ya pasó, ir al primer día vigente
  if(dayFullyPassed(activeDay)){
    const _ff=DAY_KEYS.find(d=>!dayFullyPassed(d));
    if(_ff) activeDay=_ff;
  }
  // Regla global: navegación por día → lista por defecto
  programaViewMode=activeDay==='all'?'grid':'list';
  switchMainNav('mnav-cartelera');
  showDayView();
  // Actualizar chips visualmente después del render
  setTimeout(()=>{
    document.querySelectorAll('.pchip').forEach(el=>{
      el.classList.toggle('on',el.dataset.chip===programaChip);
    });
    _updateProgramaActiveFilter();
  },50);
}

// ═══════════════════════════════════════════════════════════════
// ═══════════════════════════════════════════════════════════════
// CARD TEMPLATE CANÓNICO — 4 tipos, misma shell, contenido variable
// ───────────────────────────────────────────────────────────────
// DISEÑO VISUAL (aplica a todos los tipos):
//   Labels:    lowercase · letter-spacing .12em · color gray · .pel-sheet-section-lbl
//   Dividers:  1px · var(--bdr) · margin 20px · .pel-sheet-divider
//   Metadata:  director · género · año en una línea · .pel-sheet-metaline
//   CTAs:      primario=ámbar (.btn-primary) · secundario=borde · terciario=sin borde (.btn-tertiary)
//
// TIPO 1: PELÍCULA (!f.is_cortos, f.type !== 'event')
//   Header: poster + flags + título + duración + director·género·año + sección
//   Body:   label función/funciones + filas día·hora·venue·única-función
//           label sinopsis + texto + Letterboxd (link discreto)
//   CTAs:   Intereses (ámbar si activo) · Priorizar · Vista (terciario)
//
// TIPO 2: PROGRAMA DE CORTOS (f.is_cortos === true)
//   Header: igual TIPO 1 + "N cortos"
//   Body:   igual TIPO 1 + lista desplegable de cortos individuales
//   CTAs:   Intereses · Priorizar · Vista
//   → Cada corto abre openCortoSheet() → TIPO 3
//
// TIPO 3: CORTO INDIVIDUAL (openCortoSheet)
//   Header: poster + flags + título + duración + director·género + sección
//   Body:   label sinopsis + texto + Letterboxd
//   CTAs:   Intereses · Priorizar · Calificar
//   REGLA:  Intereses/Priorizar empaquetan al PROGRAMA PADRE (_findParentProgram)
//
// TIPO 4: EVENTO / TALLER / CONFERENCIA (f.type === 'event')
//   Header: poster + título + duración + sección (sin flags)
//   Body:   label horario + filas día·hora·venue
//           label descripción + texto (sin Letterboxd)
//   CTAs:   Intereses · Priorizar · Asistí (terciario)
//
// REGLA GLOBAL: campo nuevo → definir aquí primero, nunca ad-hoc en el template.
// ═══════════════════════════════════════════════════════════════
function openPelSheet(title){
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
  if(f.is_programa&&f.film_list&&f.film_list.length>=2){
    const _sp1=_getItemPoster(f.film_list[0]);
    const _sp2=_getItemPoster(f.film_list[1]);
    const _fd1=JSON.stringify(f.film_list[0]).replace(/"/g,'&quot;');
    const _fd2=JSON.stringify(f.film_list[1]).replace(/"/g,'&quot;');
    const _c1=_sp1
      ?`<img class="psp-card psp-front" src="${_sp1}" loading="lazy" onerror="this.remove()" alt="" data-action="_openCombinedFilmSheet" data-film="${_fd1}">`
      :`<div class="psp-card-ph" data-action="_openCombinedFilmSheet" data-film="${_fd1}">🎬</div>`;
    const _c2=_sp2
      ?`<img class="psp-card psp-back" src="${_sp2}" loading="lazy" onerror="this.remove()" alt="" data-action="_openCombinedFilmSheet" data-film="${_fd2}">`
      :`<div class="psp-card-ph" data-action="_openCombinedFilmSheet" data-film="${_fd2}">🎬</div>`;
    posterHtml=`<div class="pel-sheet-poster-stage">${_c1}${_c2}</div>`;
  } else {
    if(_isEditorialPoster(f)){
      const _accent=_sectionColor(f.section||'');
      const _secLbl=_secLabel(f.section||'');
      posterHtml=`<div class="psp-editorial"><div class="psp-ed-hdr" style="background:${_accent}"><span>${_secLbl}</span></div><div class="psp-ed-img"><img src="${posterSrc}" loading="lazy" onerror="this.parentElement.style.display='none'" alt=""></div></div>`;
    } else {
      posterHtml=posterSrc
        ?`<img class="pel-sheet-poster"${_posterStyle(f)} src="${posterSrc}" data-title="${f.title.replace(/"/g,'&quot;')}" loading="lazy" onerror="_posterErr(this)" alt="">`
        :`<div class="pel-sheet-poster-ph">🎬</div>`;
    }
  }
  const{displayTitle}=parseProgramTitle(f.title);
  const secLabel=_secLabel(f.section);
  const totalFn=FILMS.filter(fi=>fi.title===f.title).length;
  const unica=totalFn===1;
  const DAY_ABB=['MAR','MIÉ','JUE','VIE','SÁB','DOM'];
  const future=screenings.filter(s=>!screeningPassed(s)).sort((a,b)=>a.day_order-b.day_order||toMin(a.time)-toMin(b.time));
  const past=screenings.filter(s=>screeningPassed(s));
  const allScr=[...future,...past];
  const rows=allScr.map(s=>{
    const dayAbb=dayLabel(s.day)||s.day;
    const vc=vcfg(s.venue),sl=sala(s.venue);
    const _festCity=(FESTIVAL_CONFIG[_activeFestId]||{}).city||'';
    const _city=_festCity&&vc.city&&vc.city!==_festCity?vc.city:'';
    const isPast=screeningPassed(s)&&!festivalEnded();
    return`<div class="pel-sheet-screening"${isPast?' style="opacity:.4"':''}>
      <span class="pelicula-day" data-day="${s.day}">${dayAbb}</span>
      <span class="pelicula-time">${s.time}</span>
      <span class="pelicula-venue" data-venue="${vc.short.replace(/"/g,'&quot;')}" data-action="filterByVenue">${ICONS.pin} <span class="venue-text">${vc.short}${sl?' · '+sl:''}${_city?`<span class="venue-municipio">${_city}</span>`:''}</span></span>
    </div>`;
  }).join('');
  // Lista de cortos si es programa
  let cortosHtml='';
  if(f.is_cortos&&f.film_list?.length){
    const cortoItems=f.film_list.map((item,n)=>{
      const r=filmRatings[item.title]||0;
      const ratingEl=r
        ?`<span class="corto-rating-stars">${starsText(r)}</span>`
:`<button class="corto-rate-btn" data-title="${item.title||''}" data-action="closePelAndRate" data-stop="1">★</button>`;
      return _mkCortoItemHtml(item,n,{
        cls:'pel-sheet-corto-item',
        section:f.section||'',
        ratingEl
      });
    }).join('');
    cortosHtml=`<div class="pel-sheet-divider"></div>
      <div class="pel-sheet-section-lbl">${t('label_programa')} <span class="ml-1 count-badge cb-neutral">${f.film_list.length}</span></div>
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
      </div>
    </div>
    <div class="pel-sheet-divider"></div>
    <div class="pel-sheet-section-lbl">${f.type==='event'?t('label_horario'):allScr.length===1?t('label_funcion'):t('label_funciones_pl')}${totalFn>1&&f.type!=='event'?`<span class="ml-2 count-badge cb-neutral">${totalFn}</span>`:''}</div>
    ${(()=>{const _n=NOTICES.find(n=>n.title===f.title&&n.festival===(_activeFestId||_DEFAULT_FEST_ID));if(!_n)return'';const _msg=_n.type==='cancelled'?t('notice_funcion_canc'):`Reprogramada → ${_n.newDay||''} ${_n.newTime||''}${_n.newVenue?' · '+_n.newVenue:''}`;return`<div class="notice-banner-row"><span class="notice-badge">${_n.type==='cancelled'?t('notice_cancelada'):t('notice_reprog_short')}</span><span class="notice-banner-txt">${_msg}</span></div>`;})()}
    ${_metaBanners(f)}
    <div class="pel-sheet-screenings">${rows}</div>
    ${f.synopsis?`<div class="pel-sheet-divider"></div>
    <div class="pel-sheet-section-lbl">${f.type==='event'?t('label_descripcion'):t('label_sinopsis')}</div>
    <div class="pel-sheet-synopsis">${(_lang==='en'&&f.synopsis_en?f.synopsis_en:f.synopsis).replace(/^⚠️\s*INGLÉS\s*[—-]\s*/,'')}</div>`:''}
    ${cortosHtml}
    ${(!f.is_cortos&&!f.is_programa&&f.type!=='event')?lbLink(f.title,f):''}
    <div class="pel-sheet-divider"></div>
    ${inW?`<div class="pel-sheet-ctas-watched">
        <button data-title="${f.title}" data-action="toggleWatchedAndClose" class="pel-sheet-action-btn act-on">${ICONS.check} ${t('cta_vista')}</button>
        ${!f.is_cortos?`<button data-title="${f.title}" data-action="closePelAndRate" class="pel-sheet-action-btn btn-secondary">${ICONS.star} ${filmRatings[f.title]?'Cambiar':t('cta_calificar')}</button>`:``}
      </div>`
    :`<div class="pel-sheet-ctas">
        <button id="pel-wl-btn" class="row-center-xs pel-sheet-action-btn${inWL?' act-on btn-primary':' btn-primary'}" data-title="${f.title}" data-action="togglePelWL">${inWL?ICONS.heartFill:ICONS.heart} ${inWL?t('cta_en_intereses'):t('cta_intereses')}</button>
        <button id="pel-prio-btn" class="row-center-xs pel-sheet-action-btn${inPrio?' act-prio':' btn-secondary'}" data-title="${f.title}" data-action="togglePelPrio">${inPrio?ICONS.starFill:ICONS.star} ${inPrio?t('cta_priorizada'):t('cta_priorizar')}</button>
        <button id="pel-vista-btn" class="row-center-xs pel-sheet-action-btn btn-tertiary" data-title="${f.title}" data-action="toggleWatched">${ICONS.check} ${f.type==='event'?t('cta_asistio'):t('cta_vista')}</button>
      </div>`}
    ${_inPlan&&activeView==='agenda'?`<button data-title="${f.title}" data-action="closePelAndRemove" class="pel-sheet-remove-plan">${ICONS.x} ${t('plan_quitar_plan')}</button>`:''}
  `;
  document.getElementById('pel-overlay').classList.add('open');
  _ps.classList.add('open');
  _ps.classList.toggle('compact', totalFn>=3);
  _pspAttach();
}
function _pspAttach(){
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
function _pspSwap(idx){
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
function closePelSheet(){
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
// History API — cerrar cualquier sheet/overlay con botón back del browser
function _closeTopSheet(){
  // Cerrar en orden de prioridad (el más reciente primero)
  if(document.getElementById('pv-rating-sheet')?.classList.contains('open')){closePVRating();return true;}
  if(document.getElementById('conflict-sheet')?.classList.contains('open')){closeConflictSheet();return true;}
  if(document.getElementById('prio-limit-sheet')?.classList.contains('open')){closePrioLimit();return true;}
  if(document.getElementById('rating-overlay')?.classList.contains('open')){closeRatingSheet();return true;}
  if(document.getElementById('pel-sheet')?.classList.contains('open')){closePelSheet();return true;}
  // Action modal dinámico
  const modal=document.querySelector('.conflict-modal');
  if(modal){modal.remove();return true;}
  return false;
}
window.addEventListener('popstate',function(e){
  if(!_closeTopSheet()){
    // Ningún sheet abierto — dejar que el browser navegue normalmente
  }
});
function _pushSheetState(){
  try{history.pushState({sheet:true},'','');}catch(e){console.warn('[sheet] pushState failed',e);}
}
// ESC cierra el sheet activo (útil en desktop/tablet)
document.addEventListener('keydown',function(e){
  if(e.key==='Escape') _closeTopSheet();
});
(function(){
  let _startY=0,_dragging=false;
  document.addEventListener('DOMContentLoaded',()=>{
  _applyI18nDOM();
});
// ── Event delegation para js-open-pel → openPelSheet ──────────────────────
// capture:true garantiza que el evento llega antes del stopPropagation
// de _posterThumb. data-title contiene el título sin encoding.
document.addEventListener('click',function(e){
  if(e.target.closest('.plist-heart')) return; // heart toggle — no abrir sheet
  if(e.target.closest('.suggestion-add')) return; // botón Añadir — no abrir sheet
  if(e.target.closest('.int-prio-btn')) return; // estrella priorizar — no abrir sheet
  if(e.target.closest('.int-seen-btn')) return; // ya vista — no abrir sheet
  if(e.target.closest('.prio-chip-rm')) return; // quitar prioridad — no abrir sheet
  const el=e.target.closest('.js-open-pel');
  if(el) openPelSheet(el.dataset.title||'');
},true);
  // Swipe-down en el topbar para cerrar el sheet
  function _initSheetSwipe(){
    const topbar=document.querySelector('.pel-sheet-topbar');
    if(!topbar||topbar._swipeInit) return;
    topbar._swipeInit=true;
    topbar.addEventListener('touchstart',e=>{
      _startY=e.touches[0].clientY;_dragging=true;
    },{passive:true});
    topbar.addEventListener('touchmove',e=>{
      if(!_dragging) return;
      const sheet=document.getElementById('pel-sheet');
      const dy=e.touches[0].clientY-_startY;
      if(dy>0) sheet.style.transform=`translateY(${dy}px)`;
    },{passive:true});
    topbar.addEventListener('touchend',e=>{
      if(!_dragging) return;
      _dragging=false;
      const sheet=document.getElementById('pel-sheet');
      const dy=e.changedTouches[0].clientY-_startY;
      sheet.style.transform='';
      if(dy>80) closePelSheet();
    },{passive:true});
  }
  // Inicializar cuando se abre el sheet
  const _origOpen=window.openPelSheet;
  window.openPelSheet=function(title){
    if(_origOpen) _origOpen(title);
    setTimeout(_initSheetSwipe,50);
  };
})();

// ─────────────────────────────────────────────────────────────────
// PROGRAMA — EXPLORAR / HOY / MAÑANA
// ─────────────────────────────────────────────────────────────────

// ─────────────────────────────────────────────────────────────
// MAPPER PAÍS → BANDERA para cortos individuales
// ─────────────────────────────────────────────────────────────
const _COUNTRY_FLAGS={
  'Alemania':'🇩🇪','Argentina':'🇦🇷','Austria':'🇦🇹','Bolivia':'🇧🇴',
  'Brasil':'🇧🇷','Bélgica':'🇧🇪','Canadá':'🇨🇦','Chile':'🇨🇱',
  'Colombia':'🇨🇴','Cuba':'🇨🇺','EEUU':'🇺🇸','Estados Unidos':'🇺🇸',
  'Ecuador':'🇪🇨','Eslovaquia':'🇸🇰','España':'🇪🇸','Estonia':'🇪🇪',
  'Francia':'🇫🇷','Grecia':'🇬🇷','Inglaterra':'🇬🇧','Irán':'🇮🇷',
  'Italia':'🇮🇹','México':'🇲🇽','Nicaragua':'🇳🇮','Palestina':'🇵🇸',
  'Perú':'🇵🇪','Portugal':'🇵🇹','Reino Unido':'🇬🇧','Rep. Dominicana':'🇩🇴',
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
  'Costa Rica':'🇨🇷','Panama':'🇵🇦'
};
function countryToFlags(countryStr){
  if(!countryStr) return '🌍';
  const parts=countryStr.split('/').map(s=>s.trim());
  const flags=parts.map(p=>_COUNTRY_FLAGS[p]||'').filter(Boolean);
  return flags.length?flags.join(''):'🌍';
}
// ─────────────────────────────────────────────────────────────
// SHEET INDIVIDUAL DE CORTOMETRAJE
// Trata cada corto como película — poster, info, rating, Letterboxd
// ─────────────────────────────────────────────────────────────
let _cortoParentHtml=null; // guarda el HTML del programa padre

// Encuentra el programa padre de un corto individual
function _findParentProgram(cortoTitle){
  return FILMS.find(f=>f.is_cortos&&f.film_list?.some(c=>c.title===cortoTitle))||null;
}

// openCortoSheet — card unificada con openPelSheet
// Intereses/Priorizar empaquetan al programa padre completo

// ═══════════════════════════════════════════════════════════════════
// _openCombinedFilmSheet — film individual dentro de un programa combinado
// ───────────────────────────────────────────────────────────────────
// Usa el skeleton exacto de openPelSheet. Omite sección de funciones
// y CTAs — la planificación pertenece al programa padre.
// Template: cualquier festival con is_programa + film_list enriquecido.
// ═══════════════════════════════════════════════════════════════════
function _openCombinedFilmSheet(filmData){
  const inner=document.getElementById('pel-sheet-inner');
  if(!inner) return;
  const pelSheet=document.getElementById('pel-sheet');
  if(pelSheet&&pelSheet.classList.contains('open')){
    _cortoParentHtml=inner.innerHTML;
  }
  const{title='',director='',year='',duration='',flags='🌐',country='',synopsis='',synopsis_en='',lbSlug='',poster:_fPoster=''}=filmData;
  const posterUrl=_fPoster?((_fPoster.startsWith('http')||_fPoster.startsWith('/assets/'))?_fPoster:TMDB_IMG+_fPoster):getPosterSrc(title,false)||null;
  const _isEd4=posterUrl&&posterUrl.includes('cloudfront.net');
  const _sec4=(()=>{const _p=FILMS.find(f=>f.film_list&&f.film_list.some(c=>c.title===title));return _p?.section||'';})();
  const posterHtml=_isEd4
    ?`<div class="psp-editorial"><div class="psp-ed-hdr" style="background:${_sectionColor(_sec4)}"><span>${_secLabel(_sec4).toUpperCase()}</span></div><div class="psp-ed-img"><img src="${posterUrl}" loading="lazy" onerror="this.parentElement.style.display='none'" alt=""></div></div>`
    :posterUrl
      ?`<img class="pel-sheet-poster" src="${posterUrl}" data-title="${(title||"").replace(/"/g,'&quot;')}" loading="lazy" onerror="_cortoSheetPosterErr(this)" alt="">`
      :`<div class="pel-sheet-poster-ph">🎬</div>`;
  const metaLine=[director,year].filter(Boolean).join(' · ');
  const lbHref=lbSlug?`https://letterboxd.com/film/${lbSlug}/`:lbUrl(title);
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
    <div class="pel-sheet-divider"></div>
    <div class="pel-sheet-section-lbl">${t('label_sinopsis')}</div>
    <div class="pel-sheet-synopsis">${_lang==='en'&&synopsis_en?synopsis_en:(synopsis||'')}</div>
    <a class="c-lb pel-sheet-lb" href="${lbHref}" target="_blank" rel="noopener">${LB_SVG}<span class="c-lb-text pel-sheet-lb-text">Letterboxd</span></a>
    <div class="pel-sheet-divider"></div>
  `;
  const _psReset=document.getElementById('pel-sheet');
  if(_psReset){_psReset.scrollTop=0;_psReset.classList.remove('compact');}
  document.getElementById('pel-overlay').classList.add('open');
  const _psC=document.getElementById('pel-sheet');
  _psC.scrollTop=0;
  _psC.classList.add('open');
}

function openCortoSheet(title, country, duration, section, flags, director, genre, synopsis, posterOverride){
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
  const syn=synopsis||(richItem&&richItem.synopsis)||'';
  const ctry=country||(richItem&&richItem.country)||'';
  const dur=duration||(richItem&&richItem.duration)||'';
  const flgs=flags||countryToFlags(ctry)||'🌐';
  const posterUrl=posterOverride||(richItem&&getCortoItemPoster(richItem))||getPosterSrc(title,true)||null;
  const _isEd3=posterUrl&&posterUrl.includes('cloudfront.net');
  const posterHtml=_isEd3
    ?`<div class="psp-editorial"><div class="psp-ed-hdr" style="background:${_sectionColor(section||'')}"><span>${_secLabel(section||'').toUpperCase()}</span></div><div class="psp-ed-img"><img src="${posterUrl}" loading="lazy" onerror="this.parentElement.style.display='none'" alt=""></div></div>`
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
  inner.innerHTML=`
    <div class="pel-sheet-header">
      ${posterHtml}
      <div class="pel-sheet-meta">
        <div class="pel-sheet-title">${title}</div>
        <div class="pel-sheet-flags-dur">${flgs}${dur?` · ${dur}`:''}</div>
        ${(dir||gnr)?`<div class="pel-sheet-metaline">${[dir,gnr].filter(Boolean).join(' · ')}</div>`:''}
        ${secLabel?`<div class="pel-sheet-sec">${secLabel}</div>`:''}
      </div>
    </div>
    <div class="pel-sheet-divider"></div>
    ${syn?`<div class="pel-sheet-section-lbl">${t('label_sinopsis')}</div><div class="pel-sheet-synopsis">${syn}</div><div class="pel-sheet-divider"></div>`:''}
    <a class="c-lb pel-sheet-lb" href="${lbUrl(title)||'#'}" target="_blank" rel="noopener"${!lbUrl(title)?' style="display:none"':''}>${LB_SVG}<span class="c-lb-text pel-sheet-lb-text">Letterboxd</span></a>
    <div class="pel-sheet-divider"></div>
    ${parentTitle?`<div class="meta-xs-gray">${t('meta_corto_incluye')}</div>`:''}
    <div class="flex-gap1-mt1">
      <button id="corto-wl-btn" class="row-center-xs pel-sheet-action-btn${inWL?' act-on btn-primary':' btn-primary'}" data-title="${parentTitle||title}" data-action="toggleWL">${inWL?ICONS.heartFill:ICONS.heart} ${inWL?t('cta_en_intereses'):t('cta_intereses')}</button>
      <button id="corto-prio-btn" class="row-center-xs pel-sheet-action-btn${inPrio?' act-prio':' btn-secondary'}" data-title="${parentTitle||title}" data-action="togglePelPrio">${inPrio?ICONS.starFill:ICONS.star} ${inPrio?t('cta_priorizada'):t('cta_priorizar')}</button>
      <button class="row-center-xs pel-sheet-action-btn${filmRatings[title]?' act-on':' btn-secondary'}" data-title="${title}" data-action="closePelAndRate">${ICONS.star} ${filmRatings[title]?'Cambiar':t('cta_calificar')}</button>
    </div>
  `;
  const _psReset2=document.getElementById('pel-sheet');
  if(_psReset2){_psReset2.scrollTop=0;_psReset2.classList.remove('compact');}
  document.getElementById('pel-overlay').classList.add('open');
  const _psCo=document.getElementById('pel-sheet');
  _psCo.scrollTop=0;
  _psCo.classList.add('open');
}

function setMiPlanView(mode){
  miPlanViewMode=mode;
  const _v = storage.getViewmodes(); _v.miPlan = mode; storage.setViewmodes(_v);
  renderAgenda();
}

function setInteresesView(mode){
  interesesViewMode=mode;
  const _v = storage.getViewmodes(); _v.intereses = mode; storage.setViewmodes(_v);
  document.getElementById('ibtn-grid')?.classList.toggle('on',mode==='grid');
  document.getElementById('ibtn-list')?.classList.toggle('on',mode==='list');
  const el=document.getElementById('ag-film-list');
  _reRenderIntereses();
}

function _getProgramaPhase(){
  // Retorna qué tabs deben ser visibles y cuál es el default
  // Explorar eliminado — dtab TODO cubre ese caso
  if(festivalEnded()) return {tabs:[],default:'hoy'};
  const now=simNow();
  const firstDayKey=DAY_KEYS[0];
  const firstDayDate=FESTIVAL_DATES[firstDayKey];
   const _tzOff=(FESTIVAL_CONFIG[_activeFestId]||{}).timezoneOffset||'-05:00';
   const FEST_START=firstDayDate?new Date(firstDayDate+'T09:00:00'+_tzOff):new Date('2099-01-01');
  if(now<FEST_START) return {tabs:[],default:'hoy'};
  const todayStr=simTodayStr();
  const lastDayKey=DAY_KEYS[DAY_KEYS.length-1];
  const isLastDay=todayStr===FESTIVAL_DATES[lastDayKey];
  const tabs=isLastDay?['hoy']:['hoy','manana'];
  return{tabs,default:'hoy'};
}

function initProgramaModeBar(){
  const phase=_getProgramaPhase();
  // Mostrar/ocultar tabs según fase
  ['hoy','manana'].forEach(m=>{
    const el=document.getElementById('pmode-'+m);
    if(!el) return;
    el.style.display=phase.tabs.includes(m)?'':'none';
  });
  // Si el sub-modo actual no está disponible, resetear al default
  if(!phase.tabs.includes(programaSubMode)){
    programaSubMode=phase.default;
  }
  // Actualizar tab activo
  ['hoy','manana'].forEach(m=>{
    const el=document.getElementById('pmode-'+m);
    if(el) el.classList.toggle('on',m===programaSubMode);
  });
  // Mostrar/ocultar chips
  const chipsEl=document.getElementById('programa-chips');
  if(chipsEl){
    chipsEl.classList.toggle('hidden',activeDay!=='all');
    if(activeDay==='all') renderProgramaChips();
  }
  // nav-row siempre visible en Programa — dtabs son la navegación temporal
  const navRow=document.getElementById('nav-row');
  if(navRow) navRow.classList.remove('hidden');
  document.querySelectorAll('.dtab').forEach(t=>{
    t.classList.toggle('on', activeDay==='all' ? t.dataset.day==='all' : t.dataset.day===activeDay);
    t.classList.toggle('past', t.dataset.day!=='all' && dayFullyPassed(t.dataset.day));
  });
  // tag dismissible
  _updateProgramaActiveFilter();
}

function setProgramaMode(mode){
  programaSubMode=mode;
  // Reset filtros al cambiar modo y cerrar dropdowns
  activeSec='all';activeVenue='all';selectedIdx=null;
  programaChip='all';_programaChipMatchFn=null;
  lugarClose();seccionClose();
  // Set active day for hoy/mañana modes
  const _pts=simTodayStr();
  const _pti=DAY_KEYS.findIndex(d=>FESTIVAL_DATES[d]===_pts);
  if(mode==='hoy'){
    activeDay=_pti>=0?DAY_KEYS[_pti]:DAY_KEYS[0];
  } else if(mode==='manana'){
    activeDay=_pti>=0&&_pti<DAY_KEYS.length-1?DAY_KEYS[_pti+1]:DAY_KEYS[DAY_KEYS.length-1];
  }
  // filter-row visibility handled by initProgramaModeBar() below
  // filter updates handled by lugarOpen()
  _updateProgramaActiveFilter();
  initProgramaModeBar();
  _renderProgramaContent();
}

function toggleProgramaView(){
  setProgramaView(programaViewMode==='grid'?'list':'grid');
}
function setProgramaView(view){
  programaViewMode=view;
  document.getElementById('pmode-grid').classList.toggle('on',view==='grid');
  document.getElementById('pmode-list').classList.toggle('on',view==='list');
  // Sync single toggle icon
  const icoG=document.getElementById('view-toggle-ico-grid');
  const icoL=document.getElementById('view-toggle-ico-list');
  if(icoG) icoG.style.display=view==='grid'?'':'none';
  if(icoL) icoL.style.display=view==='list'?'':'none';
  _renderProgramaContent();
}

function setProgramaChip(chipId){
  // Toggle: tap active chip → deselect back to 'all'
  if(chipId!=='all'&&chipId===programaChip) chipId='all';
  programaChip=chipId;
  // Actualizar chips visuales
  document.querySelectorAll('.pchip').forEach(el=>{
    el.classList.toggle('on',el.dataset.chip===chipId);
  });
  // Guardar la función de match — soporta múltiples secciones
  const chip=(_currentChips.length?_currentChips:PROGRAMA_CHIPS).find(c=>c.id===chipId);
  // Chips ocultos — activeSec siempre directo
  _programaChipMatchFn=null;
  activeSec='all';
  _updateProgramaActiveFilter();
  _renderProgramaContent();
}

function clearProgramaChip(){
  _programaChipMatchFn=null;
  activeVenue='all';
  lugarClose();
  setProgramaChip('all');
}

function _pafClearSec(){
  activeSec='all';seccionClose();_updateProgramaActiveFilter();
  if(activeMNav==='mnav-cartelera')_renderProgramaContent();else render();
}
function _pafClearVenue(){
  activeVenue='all';lugarClose();_updateProgramaActiveFilter();
  if(activeMNav==='mnav-cartelera')_renderProgramaContent();else render();
}
function _updateProgramaActiveFilter(){
  const af=document.getElementById('programa-active-filter');
  if(!af) return;
  const hasSec=activeSec!=='all';
  const hasVenue=activeVenue!=='all';
  if(!hasSec&&!hasVenue){af.classList.remove('visible');return;}
  let pills='';
  if(hasSec){
    const lbl=_seccionPillLabel(activeSec);
    pills+='<div class="paf-pill" data-action="_pafClearSec">'+lbl+'<span class="paf-pill-x">×</span></div>';
  }
  if(hasVenue){
    pills+='<div class="paf-pill" data-action="_pafClearVenue">'+ICONS.pin+' '+activeVenue+'<span class="paf-pill-x">×</span></div>';
  }
  af.innerHTML=pills;
  af.classList.add('visible');
}

// Helper compartido entre la pure half (renderProgramaChipsHTML) y el impure
// caller (renderProgramaChips, que muta _currentChips). Extraído para evitar
// duplicar el cómputo o mezclar la mutación al state UI ephemeral con la pureza.
// _computeProgramaChips → src/view/programa.js (Step 6c). Importado.
// Pure half (p6b) — returns HTML string
// renderProgramaChipsHTML → src/view/programa.js (Step 6c). Importado.
// Impure caller (p6b) — muta _currentChips (UI state ephemeral, out-of-roster) + DOM

// ── Badges de metadata: Q&A e Inscripción previa ────────────────────────

function _metaBanners(f){
  let b='';
  if(f.has_qa) b+=`<div class="meta-banner"><div class="meta-banner-dot"></div><div><div class="meta-banner-label">${t('meta_qa_label')}</div><div class="meta-banner-text">${t('notice_extension')} <span>${t('meta_qa_time')}</span></div></div></div>`;
  if(f.requires_registration) b+=`<div class="meta-banner"><div class="meta-banner-dot"></div><div><div class="meta-banner-label">${t('badge_inscripcion_prev')}</div><div class="meta-banner-text">${t('meta_registro_text')}</div></div></div>`;
  return b;
}

// ── Stack poster para programas combinados ───────────────────────────────

// ── Notices: banner de funciones canceladas/reprogramadas ────────────────
let _dismissedNotices=new Set();
// getActiveNotices → src/view/programa.js (Step 6c). Importado.
// Pure half (p6b)
// renderNoticesBannerHTML → src/view/programa.js (Step 6c). Importado.
// Impure caller (p6b)
// renderNoticesBanner → src/view/programa.js (Step 6c). Importado.
function _dismissNotice(title){
  _dismissedNotices.add(title);
  renderNoticesBanner();
}

// Pure half (p6c)

// Impure caller (p6c) — scrollTop reset + innerHTML

// Pure half (p6c)

// Impure caller (p6c)

function _toggleWLFromList(title,btn){
  // Wrapper para el ♥ en la lista de Programa — usa el toggleWL existente
  const wasIn=watchlist.has(title);
  toggleWL(title,{stopPropagation:()=>{}});
  // Actualizar el botón visualmente después del toggle
  // Spring pop al agregar
  if(!wasIn){
    btn.style.transform='scale(1.25)';
    setTimeout(()=>btn.style.transform='',200);
  }
  setTimeout(()=>{
    const isIn=watchlist.has(title);
    if(btn){
      btn.innerHTML=isIn?ICONS.heartFill:ICONS.heart;
      btn.classList.toggle('empty',!isIn);
    }
  },50);
}

// Pure half (p6c) — DESVIACIÓN del patrón E1a: retorna tupla {html, hasEntries}
// en lugar de string puro. Razón: el original tiene side effect branch-específico
// (requestAnimationFrame(scroll) solo si entries.length > 0) — la impure caller
// necesita saber qué branch se tomó para preservar R2 byte-identity. Alternativa
// "siempre disparar rAF" cambiaría comportamiento observable (scroll event extra
// en empty state). Documentada como deviation en spec/plan/tasks de 6c.

// Impure caller (p6c) — 2 containers (cnt + grid) + rAF branch-específico

// renderActiveView (p7d) — router del pipeline subscribe→render.
// Llamado por los subscribers del RENDER PIPELINE tras una mutación de state.
// Encapsula la matriz (activeView × activeMNav) + cache-bust + scroll/pel-guard
// + runCalc-planner que antes estaba duplicada en ~20 handlers.
// NO se llama desde navegación (esa usa render/renderAgenda directo).
function renderActiveView(){
  cachedResult = null;                        // state cambió → cache de schedule stale
  if(activeView==='day' && activeMNav==='mnav-cartelera'){
    const pelOpen = document.getElementById('pel-sheet')?.classList.contains('open');
    if(!pelOpen){ const sy=window.scrollY; _renderProgramaContent(); window.scrollTo(0,sy); }
    return;
  }
  if(activeMNav==='mnav-planner'){ runCalc(); return; }  // recompute scenarios + render
  renderAgenda();                             // rutea internamente seleccion/miplan
}

// ── RENDER PIPELINE (p7d) ─────────────────────────────────────────────
// Conecta state slices → renders vía subscribeRender (deduped). Reemplaza las
// llamadas manuales de render en los handlers de los core slices. El cache-bust
// (cachedResult=null) vive en renderActiveView — centralizado.
//
// SCOPE (D7=A): solo los 7 slices "limpios" cuyo render-after-mutation es
// uniforme (re-render de vista activa). Los slices con semántica invalidate-no-
// recompute (savedAgenda, lastRemovedSlots, availability) se DEFIEREN a 7d-2
// post-Tribeca — sus handlers mantienen render manual (coexistencia, patrón
// establecido desde 5.6).
//
// CRÍTICO: los 7 slices usan la MISMA referencia de callback (_pipelineRenderMain).
// El dedup de _runRenderSubs colapsa por function ref — una transaction que toca
// varios de estos slices dispara el render 1× solo si comparten la misma fn.
const _pipelineRenderMain = () => { updateAgTab(); renderActiveView(); };
state.subscribeRender(
  ['watchlist', 'watched', 'prioritized', 'filmRatings',
   'filmDelays', 'filmDelaysHistory', '_simTime'],
  _pipelineRenderMain
);

/* ── Splash de primer encuentro ──────────────────────────────────
   Solo se muestra si no hay datos previos del usuario.
   Auto-dismiss en 2.5s o al tocar.
────────────────────────────────────────────────────────────────── */
function toggleSplashDropdown(){
  const dd=document.getElementById('splash-dropdown');
  const btn=document.getElementById('splash-sel-btn');
  if(!dd||!btn) return;
  const open=dd.style.display==='none';
  dd.style.display=open?'block':'none';
  btn.classList.toggle('open',open);
}

// ── Genera el splash dropdown y el festival selector desde FESTIVAL_CONFIG ──
// Agregar un festival = una entrada en FESTIVAL_CONFIG. Nada más que tocar.
// CHECK_SVG → src/view/components.js (Step 6a). Importado.
// _classifyFestival — fuente única de verdad para el estado temporal de un festival.
// Usada en splash, sheet, y cualquier contexto futuro.
// Retorna: 'ongoing' | 'upcoming' | 'past'
// _classifyFestival → src/view/components.js (Step 6a). Importado.

// _sortFestivals → src/view/components.js (Step 6a). Importado.
// Toggle colapso/expansión de festival pasado en el dropdown del splash.
// Al expandir muestra metadata completa y hace el item seleccionable.
// Al colapsar vuelve al estado condensado.
function _togglePastFest(btn, name, meta, id){
  // Toggle colapso/expansión — siempre. Nunca selecciona.
  const isOpen=btn.classList.contains('past-open');
  btn.classList.toggle('past-open', !isOpen);
  btn.setAttribute('aria-selected', isOpen ? 'false' : 'true');
}

// Pure half (p6b) — HTML del dropdown list
// _renderSplashDropdownHTML → src/view/components.js (Step 6a). Importado.
// Impure caller (p6b) — DOM mutations en 3 elementos del splash
function _renderSplashDropdown(activeFestId){
  const dd=document.getElementById('splash-dropdown');
  if(!dd) return;
  dd.innerHTML=_renderSplashDropdownHTML(state, activeFestId);
  // Update selected button meta with language-aware dates
  const _activeCfg=FESTIVAL_CONFIG[activeFestId];
  const _selMeta=document.getElementById('splash-sel-meta');
  const _selName=document.getElementById('splash-sel-name');
  if(_activeCfg && _selMeta){
    _selMeta.textContent=`${_activeCfg.city} · ${_langDates(_activeCfg)} ${_activeCfg.year||''}`.trim();
  }
  if(_activeCfg && _selName) _selName.textContent=_activeCfg.name;
}

// Toggle colapso/expansión de festival pasado en el sheet in-app.
// Idéntico en comportamiento a _togglePastFest del splash.
// Primer tap: expande mostrando metadata completa.
// Segundo tap: selecciona el festival vía loadFestival.
function _togglePastFestRow(row, id){
  // Toggle colapso/expansión — siempre. Nunca carga el festival.
  const isOpen=row.classList.contains('past-open');
  if(!isOpen){
    // Colapsar cualquier otro abierto antes de expandir
    document.querySelectorAll('.fs-festival-row.past.past-open')
      .forEach(el=>el.classList.remove('past-open'));
  }
  row.classList.toggle('past-open', !isOpen);
}

// Pure half (p6b) — HTML del festival selector list
// _renderFestivalSelectorHTML → src/view/components.js (Step 6a). Importado.
// Impure caller (p6b) — DOM mutation. Preserva el doble innerHTML= pre-existente
// (bug benign — escribe el mismo valor dos veces, sin efecto observable)
function _renderFestivalSelector(activeFestId){
  const container=document.getElementById('fs-festival-list');
  if(!container) return;
  const html=_renderFestivalSelectorHTML(state, activeFestId);
  container.innerHTML=html;
  container.innerHTML=html;
}
// ─────────────────────────────────────────────────────────────────────────────

let _splashSelectedFestId=_DEFAULT_FEST_ID;
function selectSplashFest(name,meta,festId){
  _splashSelectedFestId=festId||_DEFAULT_FEST_ID;
  const n=document.getElementById('splash-sel-name');
  const m=document.getElementById('splash-sel-meta');
  if(n) n.textContent=name;
  if(m) m.textContent=meta;
  document.querySelectorAll('.splash-drop-item').forEach(el=>el.classList.remove('selected'));
  const active=document.querySelector('.splash-drop-item[data-fest="'+_splashSelectedFestId+'"]');
  if(active) active.classList.add('selected');
  const dd=document.getElementById('splash-dropdown');
  const btn=document.getElementById('splash-sel-btn');
  if(dd) dd.style.display='none';
  if(btn) btn.classList.remove('open');
}

// ═══════════════════════════════════════════════════════════════════
// AUTO-RESOLVE POSTERS — lbSlug → TMDB search → poster correcto
// Corre en background después de cargar cada festival.
// Usa localStorage como caché para evitar llamadas TMDB repetidas.
// Sobreescribe entradas en POSTERS (no en CUSTOM_POSTERS).
// ═══════════════════════════════════════════════════════════════════
async function _autoResolveFestivalPosters(){
  if(!LB_SLUGS||!TMDB_API_KEY) return;
  const seen=new Set();
  const candidates=[];
  for(const f of FILMS){
    if(seen.has(f.title)) continue;
    if(f.type==='event'||f.is_cortos) continue;
    if(!LB_SLUGS[f.title]) continue;
    if(CUSTOM_POSTERS&&CUSTOM_POSTERS[f.title]) continue; // customPosters tienen prioridad
    seen.add(f.title);
    candidates.push(f);
  }
  if(!candidates.length) return;
  let updated=0;
  for(const film of candidates){
    const slug=LB_SLUGS[film.title];
    const cacheKey=_POSTER_CACHE_PFX+slug;
    let posterPath=null;
    try{posterPath=localStorage.getItem(cacheKey);}catch(e){}
    if(!posterPath){
      try{
        const q=encodeURIComponent(film.title_en||film.title);
        const yr=film.year?'&year='+film.year:'';
        const url=TMDB_API_BASE+'/search/movie?api_key='+TMDB_API_KEY+'&query='+q+yr+'&language=en-US';
        const resp=await fetch(url);
        if(!resp.ok) continue;
        const data=await resp.json();
        posterPath=data.results?.[0]?.poster_path||null;
        if(posterPath){try{localStorage.setItem(cacheKey,posterPath);}catch(e){}}
      }catch(e){continue;}
      await new Promise(r=>setTimeout(r,120)); // rate limit ~8 req/s
    }
    if(posterPath){
      const fullUrl=TMDB_POSTER_BASE+posterPath;
      if(POSTERS[film.title]!==fullUrl){POSTERS[film.title]=fullUrl;updated++;}
    }
  }
  if(updated>0){
    setPosters(POSTERS);
    requestAnimationFrame(()=>{try{render();}catch(e){console.warn('[render] rAF render failed',e);}});
  }
}
/**
 * loadFestival(id) — switch al festival `id`. Post-p5.5: el swap del state
 * roster (15 keys: 7 cfg + 8 user-state, sin `_activeFestId` que cierra
 * el switch) se hace en 3 batches atómicos por dependencias direccionales:
 *
 *   ► BATCH 1 — transition + clear:
 *     FESTIVAL_STORAGE_KEY (new), FESTIVAL_END (new),
 *     watchlist=∅, watched=∅, prioritized=∅, filmRatings=∅, savedAgenda=null,
 *     lastRemovedSlots=[], filmDelays=∅, filmDelaysHistory=∅,
 *     availability=<new shape, blocks preservados>
 *
 *   ► BATCH 2 — hidrate (loadState):
 *     watchlist/watched/prioritized/filmRatings/availability/savedAgenda/
 *     lastRemovedSlots/filmDelays/filmDelaysHistory desde storage del NUEVO fest
 *
 *   ► BATCH 3 — cfg-tail + filter:
 *     _activeFestId, FILMS, FESTIVAL_DATES, PRIO_LIMIT, TZ_OFFSET, FESTIVAL_TRANSPORT,
 *     watchlist/watched/prioritized (filtered por _validTitles)
 *
 * Por qué 3 batches y no 1:
 *   - Batch 2 (loadState) lee `storage.getX()` que prefija con FESTIVAL_STORAGE_KEY
 *     → FESTIVAL_STORAGE_KEY debe estar al nuevo fest ANTES de batch 2 → batch 1
 *   - El day-tab DOM build (entre batches 1 y 2) llama `dayFullyPassed()` que lee
 *     FESTIVAL_END → debe estar al nuevo fest ANTES del DOM build → batch 1
 *   - `_validTitles` para el filter se computa local de `_newFilms` (no del global
 *     FILMS), permitiendo que FILMS y user-state filtered convivan en batch 3.
 *
 * Atomicidad entre batches: garantizada por JS single-thread — entre el `return`
 * de batch N y el inicio de batch N+1 no corre código del event loop (loadState
 * es sync, day-tab DOM build es sync). Subscribers (futuros, post-Fase 6) verán
 * 3 snapshots discretos: post-transition, post-hidrate, post-final. Cada snapshot
 * es internamente consistente.
 */
async function loadFestival(id){
  // Resetear filtros al cambiar festival
  activeVenue='all';activeSec='all';programaChip='all';_programaChipMatchFn=null;
  lugarClose();
  seccionClose();
  requestAnimationFrame(_fixStickyOffset); // recalculate after festival name changes topbar height
  // Si no está en FESTIVAL_CONFIG, intentar cargar config desde JSON
  if(!FESTIVAL_CONFIG[id]){
    FESTIVAL_CONFIG[id]={films:null,posters:null};
  }
  const cfg=FESTIVAL_CONFIG[id];
  if(!cfg){console.warn('Festival desconocido:',id);return;}
  // Guard: storageKey es crítico — sin él los datos van a localStorage con clave 'undefined'
  if(!cfg.storageKey){
    console.error(`[loadFestival] '${id}' no tiene storageKey en FESTIVAL_CONFIG — abortando.`);
    showToast(t('error_festival_nd'),'error');
    return false;
  }
  // ── Fase 1: cargar datos del festival desde JSON si no están en memoria ──
  if(!cfg.films){
    // Convierte festivalId a nombre de archivo: ficci65→ficci-65, aff2026→aff-2026
    const festFile=id.replace(/([a-zA-Z]+)(\d+)$/,'$1-$2');
    try{
      const _festUrl='festivals/'+festFile+'.json';
      const data=await fetch(_festUrl,{cache:'no-store'}).then(r=>{
        if(!r.ok)throw new Error('HTTP '+r.status+' — '+_festUrl);
        return r.json();
      }).catch(e=>{
        // Banner de diagnóstico visible en pantalla
        const dbg=document.createElement('div');
        dbg.style.cssText='position:fixed;top:0;left:0;right:0;background:#c0392b;color:#fff;padding:14px 16px;z-index:99999;font-size:13px;font-family:monospace/* exception:debug-banner */;line-height:1.4';
        dbg.textContent='ERROR cargando festival: '+e.message;
        document.body.appendChild(dbg);
        throw e;
      });
      // ── Explosión de screenings[] → objetos planos por función ──
      // Si un film tiene screenings[], genera un objeto por función.
      // Compatibilidad total con el formato plano existente (day/time/venue).
      const exploded=[];
      (data.films||[]).forEach(f=>{
        if(Array.isArray(f.screenings)&&f.screenings.length){
          const base=Object.assign({},f);
          delete base.screenings;
          f.screenings.forEach((s,i)=>{
            exploded.push(Object.assign({},base,{
              day:s.day||s.date,date:s.date||s.day,time:s.time,venue:s.venue||'',
              day_order:s.day_order!==undefined?s.day_order:i,
              sala:s.sala||''
            }));
          });
        } else {
          exploded.push(f);
        }
      });
      // Duración automática para is_programa
      exploded.forEach(f=>{
        if(f.is_programa&&f.film_list&&f.film_list.length&&!f.duration){
          const mins=f.film_list.reduce((acc,item)=>{
            const m=parseInt((item.duration||"").replace(/[^0-9]/g,""))||0;
            return acc+m;
          },0);
          if(mins>0) f.duration=mins+" min";
        }
      });
      cfg.films=exploded; // Cacheado en sesión — evita re-fetch al volver al festival.
      // Límite recomendado: ≤5 festivales simultáneos (~80KB c/u). LRU si escala a 8+.
      cfg.posters=data.posters||{};
      cfg.customPosters=data.customPosters||{};
      cfg.lbSlugs=data.lbSlugs||{};
      // ── Sprint 2: absorber campos de config desde JSON raíz ─────────────
      // Fuente única de verdad: el JSON de cada festival contiene toda su config.
      // FESTIVAL_CONFIG en index.html solo mantiene storageKey + festivalEndStr como bootstrap.
      // Estos campos se mergean si existen en el JSON — nunca pisan storageKey.
      const _cfgFields=['name','shortName','city','dates','dates_en','year',
        'timezoneOffset','festivalDates','days','dayKeys','dayShort','dayShort_en',
        'dayLong','prioLimit','eventPosterLabel','group'];
      _cfgFields.forEach(k=>{ if(data[k]!=null) cfg[k]=data[k]; });
      // ── LEGADO: festivales anteriores con bloque config{} en el JSON ──────
      // Festivales nuevos (desde Mujeres 2026) NO deben incluir config{} en el JSON —
      // toda la configuración va en FESTIVAL_CONFIG en index.html.
      // Este bloque existe solo para compatibilidad con festivales anteriores.
      if(data.config){
        const _knownLegacy=['ficci65','cinemancia2025'];
        if(!_knownLegacy.includes(id)){
          console.warn(`[loadFestival] '${id}' tiene bloque config{} en el JSON — los festivales nuevos deben configurarse solo en FESTIVAL_CONFIG (index.html). El bloque config{} se ignora para festivales nuevos.`);
        } else {
          Object.assign(cfg, data.config);
          // Restaurar campos críticos — Object.assign puede pisarlos si config los tiene vacíos
          cfg.films=exploded;
          cfg.lbSlugs=data.lbSlugs||cfg.lbSlugs||{};
          cfg.posters=data.posters||cfg.posters||{};
          cfg.customPosters=data.customPosters||cfg.customPosters||{};
        }
      }
      // Absorber venues desde raíz del JSON (AFF/FICCI los tienen hardcodeados; otros festivales los traen aquí)
      if(data.venues) cfg.venues=data.venues;
      if(data.transport) cfg.transport=data.transport;
    }catch(e){
      console.error('Error cargando festival '+id+':',e);
      showToast(t('toast_conexion'),'error',5000);
      return false;
    }
  }
  // Guard: dayKeys y days son requeridos — sin ellos el UI de calendario crashea
  // (movido pre-batch en p5.5 para que el fallo no deje state parcialmente swapeado)
  if(!cfg.dayKeys||!cfg.days||!cfg.days.length){
    console.error(`[loadFestival] '${id}' no tiene dayKeys/days en FESTIVAL_CONFIG.`);
    showToast(t('error_festival_nd'),'error',6000);
    return false;
  }
  // ── Non-roster cfg apply (legacy) ──────────────────────────────────
  // Estos globals no están en el state roster (Fase 5.5). Siguen como
  // asignaciones directas hasta Fase 8.
  POSTERS=cfg.posters;
  LB_SLUGS=cfg.lbSlugs||{};
  DAY_KEYS=cfg.dayKeys;
  setDayShortEn(cfg.dayShort_en||cfg.dayShort);
  // Si el festival no tiene dayShort en español (ej. Tribeca: valores en inglés),
  // construirlo desde las fechas ISO usando el día de la semana.
  const _EN_TO_ES={'SUN':'DOM','MON':'LUN','TUE':'MAR','WED':'MIÉ','THU':'JUE','FRI':'VIE','SAT':'SÁB'};
  const _needsTranslation = Object.values(cfg.dayShort||{}).some(v=>
    /^(MON|TUE|WED|THU|FRI|SAT|SUN)/.test(v)
  );
  if(_needsTranslation){
    const _translated={};
    Object.entries(cfg.dayShort||{}).forEach(([k,v])=>{
      const enAbb=v.split(' ')[0];
      const num=v.split(' ')[1]||'';
      const esAbb=_EN_TO_ES[enAbb]||enAbb;
      _translated[k]=num?esAbb+' '+num:esAbb;
    });
    setDayShort(_translated);
  } else {
    setDayShort(cfg.dayShort);
  }
  CUSTOM_POSTERS=cfg.customPosters||{};
  setCustomPosters(CUSTOM_POSTERS);
  setPosters(POSTERS);
  // Mutar DAYS en sitio (const) + regenerar DAY_ABBR/DAY_NUM
  DAYS.length=0;
  cfg.days.forEach(d=>DAYS.push(d));
  Object.keys(DAY_ABBR).forEach(k=>delete DAY_ABBR[k]);
  Object.keys(DAY_NUM).forEach(k=>delete DAY_NUM[k]);
  cfg.days.forEach(d=>{DAY_ABBR[d.k]=d.lbl;DAY_NUM[d.k]=d.d;});
  // PRIO_LIMIT computado para batch 3 (regla: round(días/2), cap [3,8]).
  // Si cfg.prioLimit no está definido, fallback conservador = 3.
  const _computedPrioLimit = Math.min(8, Math.max(3, Math.round((cfg.dayKeys||[]).length / 2)));

  // ► BATCH 1 — transition + clear ───────────────────────────────────
  // FESTIVAL_STORAGE_KEY debe estar al new fest ANTES de batch 2 (loadState
  // lee storage prefijado). FESTIVAL_END debe estar antes del day-tab DOM
  // build (dayFullyPassed lo lee). availability rebuilda con shape del nuevo
  // festival, preservando blocks de días con misma key (cross-festival continuity).
  // ⚠️  festivalEndStr se parsea como hora LOCAL del dispositivo (sin sufijo UTC).
  // Festivales colombianos con audiencia local: correcto (todos en UTC-5).
  // Para festivales en otra zona, usar festivalEndStr con offset explícito.
  const _currAv = state.get('availability');
  const _newAvShape = {};
  cfg.dayKeys.forEach(d => {
    _newAvShape[d] = (_currAv[d] && _currAv[d].blocks) ? _currAv[d] : {blocks:[]};
  });
  state.batchUpdate({
    FESTIVAL_STORAGE_KEY: cfg.storageKey,
    FESTIVAL_END: new Date(cfg.festivalEndStr),
    watchlist: new Set(),
    watched: new Set(),
    prioritized: new Set(),
    filmRatings: {},
    savedAgenda: null,
    lastRemovedSlots: [],
    filmDelays: {},
    filmDelaysHistory: {},
    availability: _newAvShape,
  });
  // Rebuild day tabs DOM
  const _dt=document.getElementById('dtabs');
  if(_dt){
    _dt.innerHTML='';
    // ── dtab "TODO" — muestra todo el programa sin filtro de día ──
      const todoBtn=document.createElement('button');
      todoBtn.className='dtab on';
      todoBtn.dataset.day='all';
      todoBtn.style.cssText='display:flex;align-items:center;justify-content:center;padding:0 14px';
      todoBtn.innerHTML='<span style="font-size:var(--t-sm);font-weight:700;letter-spacing:.08em;text-transform:uppercase">'+t('bar_todo')+'</span>';
      todoBtn.onclick=()=>{
        activeDay='all';activeVenue='all';activeSec='all';selectedIdx=null;
        cartelaMode='horario';
        setProgramaView('grid'); // TODO → siempre Grid
        document.querySelectorAll('.dtab').forEach(t=>t.classList.toggle('on',t.dataset.day==='all'));
        _renderProgramaContent();
        _updateProgramaActiveFilter();
        if(activeMNav!=='mnav-cartelera') switchMainNav('mnav-cartelera');
      };
      // Separador visual entre TODO y días de fecha
      const todoSep=document.createElement('div');
      todoSep.style.cssText='width:1px;background:var(--bdr);margin:6px 0;flex-shrink:0';
      _dt.appendChild(todoBtn);
      _dt.appendChild(todoSep);

      cfg.days.forEach(day=>{
      const btn=document.createElement('button');
      btn.className='dtab'+(dayFullyPassed(day.k)?' past':'');
      btn.dataset.day=day.k;
      const _dtabLblES=day.lbl;
      const _dtabLblEN=(DAY_SHORT_EN[day.k]||'').split(' ')[0]||day.lbl;
      const _dtabLbl=_lang==='en'?_dtabLblEN:_dtabLblES;
      btn.dataset.lblEs=_dtabLblES;
      btn.dataset.lblEn=_dtabLblEN;
      btn.innerHTML=`<span class="dtab-date">${_dtabLbl}</span><span class="dtab-name">${day.d}</span>`;
      btn.onclick=()=>{
        activeDay=day.k;activeVenue='all';selectedIdx=null;
        setProgramaView('list'); // día específico → siempre Lista (horarios/planificación)
        document.querySelectorAll('.dtab').forEach(t=>t.classList.toggle('on',t.dataset.day===day.k));
        _renderProgramaContent();
        _updateProgramaActiveFilter();
        if(activeMNav!=='mnav-cartelera') switchMainNav('mnav-cartelera');
      };
      _dt.appendChild(btn);
    });
  }
  // Reset UI state (non-roster, sin cambios)
  activeDay=cfg.dayKeys[0];
  activeVenue='all';activeSec='all';selectedIdx=null;
  cachedResult=null; // invalidar cache del festival anterior — evita mostrar escenarios de otro festival
  programaSubMode='hoy';cartelaMode='horario';activeDay='all';programaViewMode='grid';
  miPlanViewStart=0;activeMiPlanDay=0;

  // ► BATCH 2 — hidrate desde storage del nuevo fest ─────────────────
  // loadState() internamente hace state.batchUpdate con los 9 user-state keys
  // (watchlist/watched/prioritized/filmRatings/availability/savedAgenda/
  // lastRemovedSlots/filmDelays/filmDelaysHistory).
  loadState();

  // ► BATCH 3 — cfg-tail + filter ────────────────────────────────────
  // _newFilms y _validTitles computados local — no se leen de state.
  // Esto permite que FILMS y los user-state filtrados estén en el MISMO
  // batch atómico. Subscribers post-Fase 6 verán "festival activo y user-state
  // consistente con sus films" en una sola notificación.
  // normTitle: normaliza comillas tipográficas en títulos. Punto único.
  const _newFilms = (cfg.films||[]).map(f=>({...f,title:normTitle(f.title)}));
  const _validTitles = new Set(_newFilms.map(f=>f.title));
  state.batchUpdate({
    _activeFestId: id,
    FILMS: _newFilms,
    FESTIVAL_DATES: cfg.festivalDates,
    PRIO_LIMIT: cfg.prioLimit || _computedPrioLimit,
    TZ_OFFSET: cfg.timezoneOffset || '-05:00',
    FESTIVAL_TRANSPORT: cfg.transport || 'transit',
    watchlist: new Set([...state.get('watchlist')].filter(t=>_validTitles.has(t))),
    watched: new Set([...state.get('watched')].filter(t=>_validTitles.has(t))),
    prioritized: new Set([...state.get('prioritized')].filter(t=>_validTitles.has(t))),
  });

  // Set active day to today
  const _ts=simTodayStr();
  const _ni=DAY_KEYS.findIndex(d=>FESTIVAL_DATES[d]===_ts);
  if(_ni>=0){
    activeDay=DAY_KEYS[_ni];
    programaSubMode='hoy'; // Durante el festival → ir directo a Hoy
  }
  // Regla global inamovible: navegación por día específico → lista por defecto
  programaViewMode=activeDay==='all'?'grid':'list';
  // Update fest-bar
  const _fn=document.querySelector('.hdr-fest-name');
  const _fd=document.querySelector('.hdr-fest-dates');
  if(_fn) _fn.textContent=cfg.name;
  if(_fd) _fd.textContent=' · '+(_lang==='en'&&cfg.dates_en?cfg.dates_en:cfg.dates);
  // Re-render festival selector con el nuevo festival activo
  _renderFestivalSelector(id);
  // Persist choice
  storage.setActiveFestId(id);
  // Render — await dos rAFs: primero renderiza, segundo confirma el paint
  closeFestivalSheet();
  switchMainNav('mnav-cartelera');
  await new Promise(resolve=>requestAnimationFrame(()=>{showDayView();requestAnimationFrame(resolve);}));
  // Resolver posters via TMDB en background — no bloquea la UI
  _autoResolveFestivalPosters().catch(()=>{});
}
function dismissSplash(){
  const s=document.getElementById('otrofestiv-splash');
  const btn=document.querySelector('.splash-enter-btn');
  if(btn) btn.classList.add('loading');
  loadFestival(_splashSelectedFestId)
    .then(ok=>{
      if(ok===false){
        if(btn) btn.classList.remove('loading'); // reset spinner — el error ya se mostró con toast
        return;
      }
      // 150ms para que el compositor de iOS se asiente antes de revelar
      setTimeout(()=>{
        if(s){s.classList.add('fade-out');setTimeout(()=>{s.remove();// FIX iOS compositor (especialmente Leviza/festival activo):
          // initProgramaModeBar() corrió bajo el splash → reflowó el topbar →
          // compositor cacheó nav en posición incorrecta. Re-ejecutar DESPUÉS de
          // quitar el splash fuerza el reflow en viewport abierto → posición correcta.
          // Luego translateY(0)→'' en doble rAF hace flush definitivo del compositor.
          (function(){
            if(typeof initProgramaModeBar==='function') initProgramaModeBar();
            if(typeof _fixStickyOffset==='function') _fixStickyOffset();
            const _nav=document.getElementById('main-nav');
            if(!_nav) return;
            _nav.style.transform='translateY(0)';
            requestAnimationFrame(function(){
              requestAnimationFrame(function(){
                _nav.style.transform='';
              });
            });
          })();},680);}
        if(btn) btn.classList.remove('loading');
      },150);
    })
    .catch(e=>{
      console.error('Error init festival:',e);
      if(btn) btn.classList.remove('loading');
    });
}
// Inicializar Supabase al cargar la página
// Capgo OTA — notifica que la app arrancó correctamente (Cap 6)
// Sin esta llamada, el updater hace rollback automático al bundle anterior.
if(window.Capacitor?.Plugins?.CapacitorUpdater){
  const _cu=window.Capacitor.Plugins.CapacitorUpdater;
  _cu.notifyAppReady();
  // Auto-update: revisa update.json y descarga bundle nuevo si hay versión distinta
  (async()=>{
    try{
      const res=await fetch('/update.json',{cache:'no-store'});
      const data=await res.json();
      const current=await _cu.current();
      const currentVer=current?.bundle?.version||'';
      if(data.version&&data.url&&data.version!==currentVer){
        const bundle=await _cu.download({url:data.url,version:data.version});
        await _cu.next(bundle);
        // El bundle nuevo se aplica en el próximo lanzamiento de la app
        console.log('[Capgo] Bundle nuevo descargado:',data.version);
      }
    }catch(e){
      // Silencioso — no interrumpir la app si falla la actualización
    }
  })();
}
_sbInit();
(function(){
  // Detecta el festival en curso por fecha. Prioridad:
  // 1. Festival que está sucediendo hoy · 2. El próximo más cercano · 3. El más reciente
  function detectActiveFest(){
    const today=new Date();today.setHours(12,0,0,0);
    let inProgress=null,nextUp=null,nextUpStart=null,mostRecent=null,mostRecentEnd=null;
    Object.entries(FESTIVAL_CONFIG).forEach(([id,cfg])=>{
      if(!cfg.festivalStartStr||!cfg.festivalEndStr) return;
      const start=new Date(cfg.festivalStartStr);
      const end=new Date(cfg.festivalEndStr);
      if(today>=start&&today<=end){
        inProgress=id;
      } else if(start>today){
        if(!nextUpStart||start<nextUpStart){nextUp=id;nextUpStart=start;}
      } else {
        if(!mostRecentEnd||end>mostRecentEnd){mostRecent=id;mostRecentEnd=end;}
      }
    });
    return inProgress||nextUp||mostRecent||_DEFAULT_FEST_ID;
  }
  const activeFest=detectActiveFest();
  _splashSelectedFestId=activeFest;
  // Render dinámico — agregar festival = solo FESTIVAL_CONFIG, nada más
  _renderSplashDropdown(activeFest);
  // Splash entrada — Web Animations API (fiable en WKWebView/Capacitor)
  // Doble rAF garantiza que el compositor iOS procese el estado opacity:0 antes de animar
  requestAnimationFrame(()=>requestAnimationFrame(()=>{
    const _sp=document.getElementById('otrofestiv-splash');
    if(!_sp||_sp.classList.contains('fade-out')) return;
    const _prefersReduced=window.matchMedia('(prefers-reduced-motion:reduce)').matches;
    const _ease='cubic-bezier(.22,1,.36,1)';
    const _animUp=(el,delay)=>{
      if(!el) return;
      if(_prefersReduced){el.style.opacity='1';return;}
      el.style.opacity='0'; // set initial state via JS — no via CSS
      el.animate(
        [{opacity:0,transform:'translateY(14px)'},{opacity:1,transform:'none'}],
        {duration:600,delay,fill:'forwards',easing:_ease}
      );
    };
    const _animFade=(el,delay)=>{
      if(!el) return;
      if(_prefersReduced){el.style.opacity='1';return;}
      el.style.opacity='0'; // set initial state via JS — no via CSS
      el.animate(
        [{opacity:0},{opacity:1}],
        {duration:550,delay,fill:'forwards',easing:'ease'}
      );
    };
    _animUp(_sp.querySelector('.splash-wordmark'),150);
    _animFade(_sp.querySelector('.splash-tagline'),650);
    _animUp(_sp.querySelector('.splash-action'),1050);
  }));
  _renderFestivalSelector(activeFest);
  const cfg=FESTIVAL_CONFIG[activeFest];
  if(cfg){
    const n=document.getElementById('splash-sel-name');
    const m=document.getElementById('splash-sel-meta');
    if(n) n.textContent=cfg.name;
    if(m) m.textContent=`${cfg.city} · ${_langDates(cfg)}${cfg.year?' '+cfg.year:''}`.trimEnd();
  }
})();

// ── Init: el splash siempre se muestra ─────────────────────────────
// El festival pre-seleccionado es el que está en curso por fecha.
// loadFestival() se llama desde dismissSplash() cuando el usuario pulsa "Entrar".
/* ── Tap-to-reveal en Intereses mobile ──────────────────────────
   Toca el poster → revela botones (ag-active).
   Toca fuera o toca un botón → cierra. */
document.addEventListener('click', function(e){
  const item = e.target.closest('.ag-film-item');
  const activeItems = document.querySelectorAll('.ag-film-item.ag-active');
  if(item){
    const isActive = item.classList.contains('ag-active');
    activeItems.forEach(el => el.classList.remove('ag-active'));
    if(!isActive && !e.target.closest('.ag-fi-btn')){
      item.classList.add('ag-active');
    }
  } else {
    activeItems.forEach(el => el.classList.remove('ag-active'));
  }
});

// (Relocado en p8 Step 6g: instalado ANTES del bootstrap eval-time para que
//  fns de view movidas que leen viewstate vía bridge en el render inicial no
//  fallen — causa raíz de 6d. El bloque referencia solo bindings hoisted/lazy.)
// ── TEST BRIDGE START (p8 Step 0) ────────────────────────────────────────────
// En el classic <script>, los const/let/function top-level vivían en el global
// lexical scope (visibles a page.evaluate de Playwright + otros scripts). Al
// modularizar quedan module-scoped. Este bloque re-expone en globalThis los
// símbolos NO-roster que la suite Playwright accede (read/write), backed por los
// module bindings.
// p8 Step 2: los 12 slices del roster (FILMS, watchlist, watched, prioritized,
// filmRatings, savedAgenda, availability, _simTime, FESTIVAL_DATES, FESTIVAL_END,
// _activeFestId, PRIO_LIMIT) se MOVIERON al STATE BRIDGE real (arriba, backed por
// state). Aquí quedan solo los NO administrados por state: view-state, DAY_KEYS,
// cachedResult, auth/splash.
(() => {
  const _lets = {
    DAY_KEYS:       [() => DAY_KEYS,       v => { DAY_KEYS = v; }],
    cachedResult:   [() => cachedResult,   v => { cachedResult = v; }],
    // view-state (los tests/helpers escriben activeDay + programaViewMode vía
    // page.evaluate; en classic eran global-lexical, ahora module-scoped).
    activeDay:        [() => activeDay,        v => { activeDay = v; }],
    activeView:       [() => activeView,       v => { activeView = v; }],
    activeVenue:      [() => activeVenue,      v => { activeVenue = v; }],
    activeSec:        [() => activeSec,        v => { activeSec = v; }],
    // p8 Step 6h: selectedIdx (hermano viewstate) — leído por render (view/
    // programa.js), escrito por filterByVenue/Day/Section + nav (handlers en main.js).
    selectedIdx:      [() => selectedIdx,      v => { selectedIdx = v; }],
    activeMNav:       [() => activeMNav,       v => { activeMNav = v; }],
    programaSubMode:  [() => programaSubMode,  v => { programaSubMode = v; }],
    programaViewMode: [() => programaViewMode, v => { programaViewMode = v; }],
    cartelaMode:      [() => cartelaMode,      v => { cartelaMode = v; }],
    interesesViewMode:[() => interesesViewMode,v => { interesesViewMode = v; }],
    miPlanViewMode:   [() => miPlanViewMode,   v => { miPlanViewMode = v; }],
    // auth/splash state que los tests leen/escriben (deleteAccount guard, splash sel)
    _sbUser:              [() => _sbUser,              v => { _sbUser = v; }],
    _splashSelectedFestId:[() => _splashSelectedFestId, v => { _splashSelectedFestId = v; }],
    // p8 Step 6c (D-6C-1): view-state de programa, bridgeado para view/programa.js.
    // Los lets viven en main.js (escritos por setProgramaChip/_dismissNotice).
    programaChip:         [() => programaChip,         v => { programaChip = v; }],
    _programaChipMatchFn: [() => _programaChipMatchFn,  v => { _programaChipMatchFn = v; }],
    _dismissedNotices:    [() => _dismissedNotices,     v => { _dismissedNotices = v; }],
    // p8 Step 6g (D-6G): _currentChips escrito por renderProgramaChips (view/
    // programa.js) y leído por setProgramaChip (handler en main.js).
    _currentChips:        [() => _currentChips,        v => { _currentChips = v; }],
    // p8 Step 6f (D-6F-1): view-state de agenda/miplan, bridgeado para view/agenda.js.
    // Los lets viven en main.js (escritos por handlers: setActivePlanFilm,
    // selectFromDetail, _setExpandedFilm, toggleFilmAlternatives, selectMiPlanDay,
    // miPlanNav, jumpToScenario, switchMainNav, toggleArchive, loadFestival).
    _activeMiPlanFilm:    [() => _activeMiPlanFilm,    v => { _activeMiPlanFilm = v; }],
    _expandedFilm:        [() => _expandedFilm,        v => { _expandedFilm = v; }],
    activeMiPlanDay:      [() => activeMiPlanDay,      v => { activeMiPlanDay = v; }],
    miPlanViewStart:      [() => miPlanViewStart,      v => { miPlanViewStart = v; }],
    _ctaRemovedVisible:   [() => _ctaRemovedVisible,   v => { _ctaRemovedVisible = v; }],
    archiveOpen:          [() => archiveOpen,          v => { archiveOpen = v; }],
  };
  for (const [k, [get, set]] of Object.entries(_lets)) {
    Object.defineProperty(globalThis, k, { get, set, configurable: true });
  }
  for (const [k, val] of Object.entries({ state, FESTIVAL_CONFIG, ACTION_REGISTRY })) {
    Object.defineProperty(globalThis, k, { get: () => val, configurable: true });
  }
  // Funciones invocadas desde:
  //  (a) handlers inline on* en HTML generado (onerror=_posterErr/_cortoSheetPosterErr)
  //      — corren en GLOBAL scope, no module scope → DEBEN estar en globalThis
  //      (correctness de producción, no solo tests; onerror no se migró en 7c).
  //  (b) page.evaluate de la suite Playwright.
  Object.assign(globalThis, {
    // (a) inline on* handlers — producción
    //     en HTML generado (main.js innerHTML): onerror=_posterErr/_cortoSheetPosterErr
    //     en markup estático (index.html): oninput/onkeyup/onkeydown=searchQuery,
    //     onkeydown=submitAuthEmail/submitOTP (#search-input, #auth-email-inp, #auth-otp-inp)
    _posterErr, _cortoSheetPosterErr,
    searchQuery, submitAuthEmail, submitOTP,
    // (b) page.evaluate — tests
    _renderProgramaContent, closeAuthSheet, closePelSheet, loadFestival, normTitle,
    openAuthSheet, openPelSheet, openRatingSheet, openCortoSheet, renderAgenda,
    render, saveSavedAgenda, saveState, savePrio, saveWL, saveWatched, searchOpen,
    searchClose, selectSplashFest, dismissSplash, showAgView, showDayView,
    simNow, simTodayStr, switchMainNav, runCalc, _getFestivalPhase,
    toggleWL, togglePriority, addBlock,
    setProgramaView, openConflictSheet, deleteAccount,
  });
})();
// ── TEST BRIDGE END (p8 Step 0) ──────────────────────────────────────────────

/* ── Re-render automático cada 60s ───────────────────────────
   Actualiza estados temporales (AHORA, Ya pasó, días pasados)
   sin depender de que el usuario navegue entre tabs.
   Solo re-renderiza si Planear o Cartelera están visibles.
   Replicable en cualquier festival futuro sin cambios.
────────────────────────────────────────────────────────────── */
// Sincronizar el primer tick con el siguiente minuto del reloj del sistema
// Así el contador avanza exactamente cuando cambia el minuto — no con retraso
function _startTickLoop(){
  setInterval(function(){
    // Planear
    if(activeMNav==='mnav-planner' && activeView==='agenda'){
      renderAgenda();
    }
    // Cartelera
    if(activeView==='day'){
      render();
    }
    // Mi Plan — contador de minutos next-film-strip
    if(activeMNav==='mnav-miplan' && activeView==='agenda'){
      renderAgenda();
    }
    updateAgTab();
  }, 60000);
}
// Esperar al próximo minuto exacto antes de iniciar el loop
const _msToNextMin=(60-new Date().getSeconds())*1000;
setTimeout(function(){ _startTickLoop(); }, _msToNextMin);
// Mientras tanto, tick inmediato para estado inicial correcto
updateAgTab();

// ── Reactivar al volver al primer plano ──────────────────────
// iOS/Android suspenden setInterval cuando la app va a background.
// visibilitychange fuerza re-render inmediato al volver,
// sin esperar al próximo tick del loop.
// ── Back-to-top: solo visible cuando hay scroll ──────────────────
(function(){
  const btn=document.getElementById('back-top');
  if(!btn) return;
  const onScroll=()=>{ btn.classList.toggle('visible', window.scrollY > 200); };
  window.addEventListener('scroll',onScroll,{passive:true});
})();
document.addEventListener('visibilitychange', function(){
  if(document.visibilityState!=='visible') return;
  // Al volver al primer plano: si hay función en los próximos 30min → Mi Plan
  if(_checkNavigateToMiPlan()&&activeMNav!=='mnav-miplan'){
    switchMainNav('mnav-miplan');
    showAgView();
  } else {
    if(activeMNav==='mnav-miplan'&&activeView==='agenda') renderAgenda();
    else if(activeMNav==='mnav-planner'&&activeView==='agenda') renderAgenda();
    else if(activeView==='day') render();
  }
  updateAgTab();
}); // visibilitychange

// html2canvas eliminado — Canvas API puro
// lugar click-outside handled by lugarOutside()
updateAgTab();render();

// ── p8: marcador de readiness ────────────────────────────────────────────────
// Bootstrap síncrono completo: módulo evaluado, STATE/TEST BRIDGE + listener
// delegado instalados, render inicial hecho. Los tests esperan
// [data-app-ready="1"] para sincronizar contra JS-ready (no DOM estático),
// cerrando races de interacción-antes-de-bootstrap (ej. flaky #splash-dropdown).
document.documentElement.dataset.appReady = '1';

// ── Auto-navegar a Mi Plan si hay función próxima ──────────────
// Si el usuario tiene un plan guardado y hay una función
// empezando en los próximos 30 minutos, aterrizamos en Mi Plan.
// También se revisa al volver de background (visibilitychange).
function _checkNavigateToMiPlan(){
  if(festivalEnded()) return false;
  if(!savedAgenda||!savedAgenda.schedule||!savedAgenda.schedule.length) return false;
  const now=simNow();
  const WINDOW_MS=30*60*1000; // 30 minutos
  const upcoming=savedAgenda.schedule.find(s=>{
    const dateStr=FESTIVAL_DATES[s.day];
    if(!dateStr) return false;
    const start=_festDate(dateStr,s.time);
    const diff=start-now;
    return diff>=0 && diff<=WINDOW_MS; // empieza en los próximos 30min
  });
  return !!upcoming;
}

// Al arrancar — navegar a Mi Plan si hay agenda activa
setTimeout(()=>{
  if(_checkNavigateToMiPlan()){
    switchMainNav('mnav-miplan');
    showAgView();
  }
}, 400);

// openFestivalSheet → src/view/sheets.js (Step 6b). Importado.
// closeFestivalSheet → src/view/sheets.js (Step 6b). Importado.

/* ── _fixStickyOffset: correct sticky positions for desktop gap ─────────
   Measures actual topbar height so #hdr-programa sticks precisely.
   Runs synchronously + on resize. Desktop only (mobile uses CSS 47px). */

// Run after layout is complete (fonts + CSS painted)
requestAnimationFrame(()=>requestAnimationFrame(_fixStickyOffset));
window.addEventListener('resize',function(){requestAnimationFrame(_fixStickyOffset);});
if('serviceWorker' in navigator){
  navigator.serviceWorker.register('/sw.js').catch(function(){});

  // ── Plataforma y build tracking ───────────────────────────────────────
  var _isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) ||
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  var _BUILD_KEY = 'orf_build';
  var _reloading  = false; // guard: evita double-reload si dos canales disparan a la vez

  // ── Canal Android/Desktop: controllerchange ───────────────────────────
  // hadController previene el double-reload en primera instalación
  // (sin SW previo, controller es null → ese controllerchange se ignora)
  // iOS excluido: WKWebView puede terminar el proceso SW entre sesiones,
  // haciendo que controllerchange se dispare sin haber actualización real.
  if(!_isIOS){
    var _hadController = !!navigator.serviceWorker.controller;
    navigator.serviceWorker.addEventListener('controllerchange', function(){
      if(_hadController && !_reloading){
        _reloading = true;
        location.reload();
      }
      _hadController = true;
    });
  }

  // ── Función de check compartida por cold-start y visibilitychange ─────
  // Extrae la lógica para reutilizarla en ambos triggers sin duplicar código.
  function _checkVersionJson(){
    fetch('/version.json', {cache:'no-store'})
      .then(function(r){ return r.json(); })
      .then(function(v){
        var serverBuild = v[_isIOS ? 'ios' : 'android'] || '';
        var localBuild  = localStorage.getItem(_BUILD_KEY) || '';
        if(serverBuild){
          if(serverBuild !== localBuild && !_reloading){
            // Versión distinta (incluye primera instalación con localBuild vacío):
            // guardar primero para evitar loop, luego recargar solo si había versión previa
            var wasFirstInstall = !localBuild;
            localStorage.setItem(_BUILD_KEY, serverBuild);
            if(!wasFirstInstall){
              // Update real: recargar para tomar la nueva versión
              _reloading = true;
              location.reload();
            }
            // En primera instalación: el SW ya tomó control (skipWaiting+claim),
            // el próximo visibilitychange o cold-start traerá contenido fresco.
          }
          // misma versión: no hacer nada
        }
      })
      .catch(function(){});
  }

  // ── Canal version.json #1: cold start ─────────────────────────────────
  // Corre al abrir la app desde cero.
  // Permite staged rollout: android e ios con builds independientes en version.json.
  _checkVersionJson();

  // ── Canal version.json #2 + SW re-check: visibilitychange ────────────
  // Corre cuando el usuario vuelve la app desde background.
  // En mobile, el JS no recarga al volver del background — sin este listener,
  // un usuario que deja la app abierta horas (o días) nunca detecta updates.
  // Patrón usado por Slack, Discord, Notion para actualizaciones en WebView.
  // registration.update() fuerza re-verificación de sw.js contra el servidor —
  // el browser solo hace este check en register() (al cargar), no al volver de bg.
  // Si hay nuevo sw.js → instala → skipWaiting → controllerchange → reload.
  document.addEventListener('visibilitychange', function(){
    if(document.visibilityState === 'visible' && !_reloading){
      _checkVersionJson();
      // Forzar re-check del SW contra el servidor (gap documentado en web.dev/MDN)
      navigator.serviceWorker.ready.then(function(reg){ reg.update(); }).catch(function(){});
    }
  });
}

// ── FILTRO LUGAR — implementación desde cero ─────────────────────────────
// 40 líneas. Un dropdown simple. Sin dependencias externas.

function lugarOpen(){
  const btn = document.getElementById('lugar-btn');
  const r = btn.getBoundingClientRect();

  // Build dropdown
  const drop = document.createElement('div');
  drop.id = 'lugar-drop';
  drop.style.cssText = [
    'position:fixed',
    'top:'+(r.bottom+4)+'px',
    'right:'+(window.innerWidth-r.right)+'px',
    'min-width:200px',
    'max-width:min(280px,90vw)',
    'max-height:50vh',
    'overflow-y:auto',
    '-webkit-overflow-scrolling:touch',
    'overscroll-behavior:contain',
    'background:var(--surf)',
    'border:1px solid var(--bdr)',
    'border-radius:var(--r)',
    'box-shadow:0 8px 24px rgba(0,0,0,.55)',
    'z-index:9999',
    'animation:lugarFadeIn .12s ease'
  ].join(';');

  // Collect unique venues from FILMS
  // Embedded screenings[] format (Tribeca): expand all screenings, dedupe by title.
  // Flat format (FICCI/AFF): one row per screening, use f.venue directly.
  const venueMap = {};
  const _vSeen = new Set();
  (activeDay==='all'?FILMS:FILMS.filter(f=>f.day===activeDay))
    .forEach(f=>{
      if(f.screenings&&f.screenings.length){
        if(_vSeen.has(f.title)) return;
        _vSeen.add(f.title);
        const rel=activeDay==='all'?f.screenings:f.screenings.filter(s=>s.date===activeDay||s.day===activeDay);
        rel.forEach(s=>{
          const cfg=vcfg(s.venue);const short=cfg.short||s.venue;
          if(!short) return;
          if(!venueMap[short]) venueMap[short]={label:short,count:0,city:cfg.city||''};
          venueMap[short].count++;
        });
      } else {
        const cfg=vcfg(f.venue);const short=cfg.short||f.venue;
        if(!short) return;
        if(!venueMap[short]) venueMap[short]={label:short,count:0,city:cfg.city||''};
        venueMap[short].count++;
      }
    });

  const venues = Object.values(venueMap).sort((a,b)=>b.count-a.count);
  const total = venues.reduce((s,v)=>s+v.count,0);

  // Render options
  const opts = [{label:t('filter_todos_lugares'), count:total, short:'all'}, ...venues.map(v=>({...v,short:v.label}))];
  drop.innerHTML = opts.map(v=>{
    const isActive = (v.short==='all' && activeVenue==='all') || (activeVenue===v.short);
    return '<div class="lugar-opt'+(isActive?' on':'')+'" data-v="'+v.short+'">'
      +(v.short!=='all'?'<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path stroke-linecap="round" stroke-linejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z"/></svg>':'')
      +'<span>'+v.label+'</span>'
      +'<span class="lugar-cnt">'+v.count+'</span>'
      +'</div>';
  }).join('');

  drop.addEventListener('click', e=>{
    const opt = e.target.closest('.lugar-opt');
    if(!opt) return;
    const v = opt.dataset.v;
    activeVenue = (v==='all'||v===activeVenue)?'all':v;
    lugarClose();
    _updateProgramaActiveFilter();
    if(activeMNav==='mnav-cartelera') _renderProgramaContent(); else render();
  });

  document.body.appendChild(drop);
  btn.classList.add('active');

  // Close on outside click
  setTimeout(()=>{
    document.addEventListener('click', lugarOutside);
  }, 0);
  // Close on scroll — dropdown is fixed, button moves with sticky bar
  window.addEventListener('scroll', lugarClose, {passive:true, once:true});
}

function lugarToggle(){
  if(document.getElementById('seccion-drop')) seccionClose();
  if(document.getElementById('lugar-drop')) lugarClose();
  else lugarOpen();
}

// ── BUSCADOR — sistema completo ───────────────────────────────────────────
// Overlay position:fixed. Se posiciona debajo del topbar.
// El teclado ajusta la altura via visualViewport.

function searchPositionOverlay(){
  const overlay = document.getElementById('search-overlay');
  const results = document.getElementById('search-results');
  if(!overlay || overlay.style.display==='none') return;
  // Overlay: desde topbar hasta el borde inferior de la pantalla (bottom:0)
  // El teclado es UI del sistema — siempre por encima, no interfiere con el overlay
  const tb = document.querySelector('.topbar');
  const top = tb ? Math.ceil(tb.getBoundingClientRect().bottom) : 88;
  overlay.style.top = top + 'px';
  overlay.style.bottom = '0';
  overlay.style.height = 'auto';
  // Padding-bottom en resultados = altura del teclado para que nada quede oculto
  if(results){
    const vv = window.visualViewport;
    const kbH = vv ? Math.max(0, window.innerHeight - vv.height - (vv.offsetTop||0)) : 0;
    results.style.paddingBottom = (kbH + 16) + 'px';
  }
}

function searchOpen(){
  const overlay = document.getElementById('search-overlay');
  const inp = document.getElementById('search-input');
  if(!overlay) return;
  window.scrollTo({top:0, behavior:'instant'});
  // Posicionar ANTES de mostrar para evitar flash sin top
  const tb = document.querySelector('.topbar');
  const top = tb ? Math.ceil(tb.getBoundingClientRect().bottom) : 88;
  overlay.style.top = top + 'px';
  overlay.style.bottom = '0';
  overlay.style.display = 'flex';
  requestAnimationFrame(()=>{
    overlay.style.opacity = '1';
    searchPositionOverlay();
    if(inp){
      inp.focus();
      // Si hay texto previo, disparar búsqueda inmediatamente
      if(inp.value.trim()) searchQuery();
    }
  });
}

function searchClose(){
  const overlay = document.getElementById('search-overlay');
  const inp = document.getElementById('search-input');
  const results = document.getElementById('search-results');
  if(overlay){
    overlay.style.opacity = '0';
    setTimeout(()=>{ overlay.style.display = 'none'; }, 150);
  }
  if(inp){ inp.value = ''; inp.blur(); }
  if(results) results.innerHTML = '';
}

function _searchAll(q){
  // Motor único: fuzzyMatch scoring en títulos + cortos individuales.
  // Reemplaza los tres motores paralelos anteriores.
  if(!q) return[];
  const ql=q.toLowerCase();
  const seen=new Set();
  const results=[];

  // 1. Programas y películas (deduplicados por título)
  const titleMap={};
  FILMS.forEach(f=>{if(!titleMap[f.title]) titleMap[f.title]=f;});
  Object.values(titleMap).forEach(f=>{
    const r1=fuzzyMatch(q,f.title);
    const r2=f.title_en?fuzzyMatch(q,f.title_en):{match:false,score:0};
    const secScore=(f.section||'').toLowerCase().includes(ql)?0.3:0;
    const cntScore=(f.country||'').toLowerCase().includes(ql)?0.2:0;
    const score=Math.max(r1.score,r2.score)+secScore+cntScore;
    if((r1.match||r2.match||secScore||cntScore)&&!seen.has(f.title)){
      seen.add(f.title);
      results.push({...f,_score:score});
    }
  });

  // 2. Cortos individuales dentro de film_list
  FILMS.filter(f=>f.is_cortos&&f.film_list?.length).forEach(prog=>{
    prog.film_list.forEach(item=>{
      const r=fuzzyMatch(q,item.title);
      if(r.match&&!seen.has(item.title)){
        seen.add(item.title);
        results.push({_isCortoItem:true,_prog:prog,_score:r.score,
          title:item.title,country:item.country,duration:item.duration,
          flags:countryToFlags(item.country||''),section:prog.section,is_cortos:false});
      }
    });
  });

  return results.sort((a,b)=>b._score-a._score).slice(0,10);
}

function searchQuery(){
  const inp = document.getElementById('search-input');
  const results = document.getElementById('search-results');
  if(!inp || !results) return;
  const q = inp.value.trim();

  if(!q){ results.innerHTML = ''; return; }

  const matches = _searchAll(q);

  if(!matches.length){
    results.innerHTML = `<div class="search-empty">${emptyState(ICONS.search,t('search_sin_res_para')+' \u201c'+q+'\u201d')}</div>`;
    return;
  }

  const hasCortos=matches.some(f=>f._isCortoItem);
  const hasFilms=matches.some(f=>!f._isCortoItem);
  const hdr=hasFilms&&hasCortos?t('search_resultados')||'Resultados':hasCortos?t('label_cortos')||'Cortometrajes':t('planear_peliculas');
  results.innerHTML = `<div class="search-section-hdr">${hdr}</div>`
    + matches.map(f=>{
      const{displayTitle,progSuffix}=parseProgramTitle(f.title);
      const poster=getFilmPoster(f)||'';
      const _dur=f.duration!=null?String(f.duration):'';
      const meta=f._isCortoItem
        ?'Cortometraje'+(f._prog?' · '+parseProgramTitle(f._prog.title).displayTitle:'')
        :(_dur?_dur+' min':'')+(f.section?' · '+f.section.replace(/^[^ ]+ /,''):'');
      const _q=s=>String(s).replace(/"/g,'&quot;');
      const _siAttrs=f._isCortoItem
        ?`data-action="searchOpenCorto" data-title="${_q(f.title)}" data-country="${_q(f.country||'')}" data-dur="${_q(_dur)}" data-section="${_q(f.section||'')}" data-flags="${_q(f.flags||'🌍')}"`
        :`data-action="searchOpenFilm" data-title="${_q(f.title)}"`;
      return '<div class="search-item" '+_siAttrs+'>'
        +(poster?'<img class="search-item-poster" src="'+poster+'" onerror="this.remove()" alt="" loading="lazy">'
                :'<div class="search-item-poster"></div>')
        +'<div class="search-item-info">'
        +'<div class="search-item-title">'+displayTitle
        +(progSuffix?'<span class="txt-amber-sm"> '+progSuffix+'</span>':'')
        +'</div>'
        +'<div class="search-item-meta">'+meta+'</div>'
        +'</div>'
        +'<div class="search-item-arrow">›</div>'
        +'</div>';
    }).join('');
}

// Reposition when keyboard appears/disappears
if(window.visualViewport){
  window.visualViewport.addEventListener('resize', searchPositionOverlay);
}

// ── FILTRO SECCIÓN ────────────────────────────────────────────────────────
// Mismo patrón que lugarOpen/Close/Outside/Toggle.
// activeSec: 'all' | nombre exacto de sección (f.section)

function _seccionLabel(sec){
  // Botón mode bar: solo el emoji que ya viene en el nombre de sección
  // Las secciones tienen formato "🏆 Nombre" en todos los festivales
  if(!sec||sec==='all') return t('label_seccion');
  return sec.match(/^\S+/)?.[0] || sec.slice(0,4);
}
function _seccionPillLabel(sec){
  // Pill: nombre completo tal como viene en el JSON — ya incluye emoji
  if(!sec||sec==='all') return sec;
  return sec;
}

function seccionOpen(){
  const btn = document.getElementById('seccion-btn');
  const r = btn.getBoundingClientRect();
  const drop = document.createElement('div');
  drop.id = 'seccion-drop';
  drop.style.cssText = [
    'position:fixed','top:'+(r.bottom+4)+'px',
    'right:'+(window.innerWidth-r.right)+'px',
    'min-width:200px','max-width:min(300px,90vw)','max-height:55vh',
    'overflow-y:auto','background:var(--surf)','border:1px solid var(--bdr)',
    'border-radius:var(--r)','box-shadow:0 8px 24px rgba(0,0,0,.55)',
    'z-index:9999','animation:lugarFadeIn .12s ease'
  ].join(';');

  const baseFilms = activeDay==='all' ? FILMS : FILMS.filter(f=>f.day===activeDay);
  const films = activeVenue!=='all' ? baseFilms.filter(f=>vcfg(f.venue).short===activeVenue) : baseFilms;

  const secMap={}, secCatMap={}, titleSet={};
  films.forEach(f=>{
    if(!titleSet[f.title]){
      titleSet[f.title]=true;
      const s=f.section||'';
      if(s){ secMap[s]=(secMap[s]||0)+1; if(f.filmCategory) secCatMap[s]=f.filmCategory; }
    }
  });
  const total=Object.keys(titleSet).length;

  const _opt=(s,cnt,isActive)=>'<div class="lugar-opt'+(isActive?' on':'')+'" data-s="'+s.replace(/"/g,'&quot;')+'">'
    +'<span>'+s+'</span><span class="lugar-cnt">'+cnt+'</span>'+(isActive?'<span class="txt-amber-ml">✓</span>':'')+'</div>';

  let html='<div class="lugar-opt'+(activeSec==='all'?' on':'')+'" data-s="all">'
    +'<span>'+t('filter_todo_programa')+'</span><span class="lugar-cnt">'+total+'</span>'
    +'</div>';

  const hasCategories=Object.keys(secCatMap).length>0;
  const orderedSecs=Object.keys(secMap).sort((a,b)=>{
    const ia=SECTION_ORDER_LIST.indexOf(a),ib=SECTION_ORDER_LIST.indexOf(b);
    return (ia<0?999:ia)-(ib<0?999:ib);
  });

  if(hasCategories){
    const groups={};
    orderedSecs.forEach(s=>{ const cat=secCatMap[s]||''; if(cat){if(!groups[cat])groups[cat]=[];groups[cat].push(s);} });
    const uncategorized=orderedSecs.filter(s=>!secCatMap[s]);
    FILM_CATEGORY_ORDER.forEach(cat=>{
      if(!groups[cat]) return;
      html+='<div class="sec-drop-hdr">'+(FILM_CATEGORY_LABEL[cat]||cat)+'</div>';
      groups[cat].forEach(s=>{ html+=_opt(s,secMap[s],activeSec===s); });
    });
    uncategorized.forEach(s=>{ html+=_opt(s,secMap[s],activeSec===s); });
  } else {
    orderedSecs.forEach(s=>{ html+=_opt(s,secMap[s],activeSec===s); });
  }

  drop.innerHTML=html;
  drop.addEventListener('click',e=>{
    const opt=e.target.closest('.lugar-opt');
    if(!opt) return;
    const s=opt.dataset.s;
    activeSec=(s==='all'||s===activeSec)?'all':s;
    _programaChipMatchFn=null; programaChip='all';
    seccionClose(); _updateProgramaActiveFilter();
    if(activeMNav==='mnav-cartelera') _renderProgramaContent(); else render();
  });
  document.body.appendChild(drop);
  btn.classList.add('active');
  setTimeout(()=>{ document.addEventListener('click',seccionOutside); },0);
}
function seccionOutside(e){
  const drop = document.getElementById('seccion-drop');
  const btn = document.getElementById('seccion-btn');
  if(drop && !drop.contains(e.target) && e.target!==btn && !btn?.contains(e.target)){
    seccionClose();
  }
}

function seccionClose(){
  const drop = document.getElementById('seccion-drop');
  if(drop) drop.remove();
  document.removeEventListener('click', seccionOutside);
  const btn = document.getElementById('seccion-btn');
  if(btn) btn.classList.toggle('active', activeSec!=='all');
  const lbl = document.getElementById('seccion-lbl');
  if(lbl) lbl.textContent = _seccionLabel(activeSec);
}

function seccionToggle(){
  if(document.getElementById('lugar-drop')) lugarClose();
  if(document.getElementById('seccion-drop')) seccionClose();
  else seccionOpen();
}

// ── Poster error handler — una función, un comportamiento ────────────────
// Llamado desde onerror en cualquier img de poster.
// data-title en el img → busca el film → muestra generativo.
// Si no hay generativo → fondo surf-2 (nunca negro).
// ── Poster error handler ─────────────────────────────────────────────────
// Cuando una URL de poster falla (hotlink, 404, timeout):
// 1. Muestra generativo inmediatamente (no queda en negro)
// 2. Busca en TMDB por título para conseguir poster real (async)
// 3. Si TMDB responde, reemplaza el generativo con el poster real
// 4. Cachea el resultado en localStorage para no repetir la búsqueda

function _posterGenFallback(img, f){
  if(!f){ img.style.display='none'; return; }
  let gen;
  if(f.title&&f.title.toLowerCase().includes('sorpresa')) gen=makeSorpresaPoster();
  else if(f.type==='event') gen=makeEventPoster(state,f.title,f.duration,f.event_kind);
  else if(f.is_cortos) gen=makeProgramPoster(state,f.title,f.duration,f.section);
  else gen=_buildPosterV16({
    accent: _sectionColor(f.section||''),
    headerLabel: _secLabel(f.section||'')||'FESTIVAL',
    title: f.title,
    num: null
  });
  if(gen) img.src=gen; else img.style.display='none';
}

function _posterErr(img){
  img.onerror=null;
  const title=img.dataset.title||'';
  const f=title?FILMS.find(fi=>fi.title===title):null;
  if(!f){img.style.display='none';return;}

  // Check localStorage cache first
  const cacheKey=_POSTER_CACHE_PFX+'err_'+title;
  const cached=localStorage.getItem(cacheKey);
  if(cached){img.src=cached;return;}

  // Show generative immediately
  _posterGenFallback(img,f);

  // Search TMDB async for real poster (only if key available — not in production bundle)
  if(!TMDB_API_KEY) return;
  const query=encodeURIComponent(f.title_en||f.title);
  const yearParam=f.year?'&year='+f.year:'';
  fetch(`${TMDB_API_BASE}/search/movie?api_key=${TMDB_API_KEY}&query=${query}${yearParam}&language=es`)
    .then(r=>r.json())
    .then(data=>{
      const path=data.results?.[0]?.poster_path;
      if(path&&img.isConnected){
        const url=TMDB_IMG+path;
        img.src=url;
        try{localStorage.setItem(cacheKey,url);}catch(e){}
      }
    })
    .catch(()=>{});
}
// Fallback para poster en openCortoSheet: los cortos no están en FILMS top-level,
// por lo que _posterErr no puede encontrarlos y los oculta. Esto muestra el placeholder.
function _cortoSheetPosterErr(img){
  img.onerror=null;
  const ph=document.createElement('div');
  ph.className='pel-sheet-poster-ph';
  ph.textContent='🎬';
  img.parentNode?.replaceChild(ph,img);
}

