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
// p8 Step 8a: STATE BRIDGE reubicado a state/state-bridge.js (side-effect import).
// Instala el bridge en la fase de import (antes del body de main.js).
import './state/state-bridge.js';
// p8 Step 8b: TEST BRIDGE viewstate (29 lets) → state/viewstate.js (side-effect).
// Instala en import-phase → neutraliza el gotcha de eval-time writes de main.js.
import './state/viewstate.js';

// ── Step 3: storage.js (import — adapter de localStorage; usa el bridge para
//   FESTIVAL_STORAGE_KEY). saveX/loadState orquestadoras se quedan en main.js. ──
import { storage } from './storage/storage.js';
import { onDomReady } from './util/ready.js';
import { report } from './telemetry.js';

// ── Step 4: i18n.js (import — _I18N + t + _applyI18nDOM). _lang vive en state
//   (bridge); la init eval-time de _lang se queda en main.js, setLang → pipeline.js (8d-3).
import { LANGS, t, _applyI18nDOM } from './i18n/i18n.js';

// ── Step 5: domain/ (funciones puras). Importan config (DEFAULT_DURATION_MIN,
//   FESTIVAL_BUFFER, FESTIVAL_CONFIG) y leen festival-state vía bridge. El worker
//   las consume vía eval(name).toString(); sus copias worker-local se quedan. ──
import { toMin, parseDur, minToStr, _festDate, simNow, simTodayStr, dayFullyPassed, festivalEnded } from './domain/time.js';
import { _djb2, _titleSeed, _mulberry32, shuffle, scoreFilm, effectiveDuration, screeningPassed, _classifyTodayScreenings, _endedStats, normTitle } from './domain/film.js';
import { screensConflict, isScreeningBlocked, sortScreensByStrategy, computeScenarios } from './domain/schedule.js';
import { _resolveVenue, _gapSuggestion, _getFestivalPhase, venueTravelMins, travelMins } from './domain/festival.js';

// ── Step 6a: view/components.js — capa presentacional foundational de Wave 6
//   (posters, builders HTML puros, helpers sección/rating/festival). ──────────
import {
  ICONS, CHECK_SVG, DAY_ABBR, DAY_NUM,
  makeProgramPoster, makeEventPoster, makeSorpresaPoster,
  _secLabel, _sectionColor, renderRatingStarsHTML, starSVG,
  _renderFestivalSelectorHTML, _classifyFestival,
  _sortFestivals, renderAvBlocksHTML, isFullDayBlocked, renderFlowProgress,
  parseProgramTitle,
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

// ── Step 7a: controller/calc.js — orquestación del planner (worker). ─────────
import { runCalc } from './controller/calc.js';

// ── Step 7b: controller/persistence.js — saves + cloud sync + Supabase auth. ──
import {
  saveWL, saveWatched, saveRating, saveAV, saveSavedAgenda, savePrio, saveLastSlot, saveDelays, saveState, loadState, _cloudLoad, _sbUpdateUI, submitAuthEmail, submitOTP, deleteAccount, signOutAndClose, setPlanRerender,
} from './controller/persistence.js';

// ── Step 7c: controller/pipeline.js — render dispatchers. ────────────────────
import {
  renderActiveView, switchMainNav, showDayView, showAgView, updateAgTab, _reRenderIntereses, _rerenderFilmList, _getProgramaPhase, _updateProgramaActiveFilter, initProgramaModeBar, setLang,
  toggleLangDropdown, selectLang, closeLangDropdown,
} from './controller/pipeline.js';

// ── Step 7d-1: controller/sheets-controller.js — sheets+rating+AV+toast+utils. ──
import {
  openPelSheet, closePelSheet, _closeTopSheet, openCortoSheet, openCortoSheetFromEl, _openCombinedFilmSheet, _findParentProgram, openConflictSheet, closeConflictSheet, openPrioLimit, openPlanConfirm, closePlanConfirm, openPostViewRating, openRatingSheet, closeRatingSheet, openAvSheet, selectAvDay, setAvType, confirmAvBlock, renderAvDay, addBlock, removeBlock, toggleFullDay, _setAvAddOpen, showActionToast, _dismissToastAction, countryToFlags, filmDisplayTitle, _genreEN, _removePlanItem, savePVRating, pvLater, openDiary, closeDiary, openVenueSheet, closeVenueSheet,
} from './controller/sheets-controller.js';

// ── Step 7d-2: controller/overlays.js — seccion/search/lugar dropdowns. ──────
import {
  seccionClose, seccionToggle, searchOpen, searchClose, searchPositionOverlay, searchQuery, lugarOpen, lugarToggle,
} from './controller/overlays.js';

// ── Step 7d-3: controller/handlers.js — mutators+filters+composites. ─────────
import {
  toggleWL, toggleWatched, togglePelPrio, togglePelWL, setDelay, undoDelay, clearDelay, removeFromAgenda, addSuggestion, checkinLaVi, checkinNoLaVi, forceInclude, togglePriority, swapPriority, markWatchedFromPlan, confirmReplace, removeFilmFromScenario, _dismissNotice, selectMiPlanDay, miPlanNav, toggleMplanProg, setActivePlanFilm, selectFromDetail, toggleFilmAlternatives, _toggleEveningFilms, filterByVenue, filterByDay, filterBySection, setInteresesView, setProgramaMode, toggleProgramaView, setProgramaView, setProgramaChip, clearProgramaChip, _pafClearSec, _pafClearVenue, _toggleWLFromList, saveCurrentScenario, _scrollToAgSection, _setExpandedFilm, _closePelAndRemove, _closePelAndRate, _navTo, _closeAuthAndReset, _toggleCtxOlder, _toggleWatchedAndClose, _toggleWLAndClose, _activatePlanFilm, _scrollToSuggestions, _removeConflictModal, _scrollToTop, _searchOpenFilm, _searchOpenCorto,
} from './controller/handlers.js';
import { setDelaysRerender } from './controller/delays-cloud.js';
import { initWatchBridge } from './controller/watch-bridge.js';

// ── Step 8d-4: controller/loader.js (loadFestival + dismissSplash) ───────────
import {
  loadFestival, dismissSplash,
} from './controller/loader.js';

// ── Step 7e: controller/festival.js ────────────────────────────────────────────
import {
  _renderSplashRail, _togglePastFestRow, _renderFestivalSelector, selectSplashFest, _autoResolveFestivalPosters,
} from './controller/festival.js';

// ── Step 7e: controller/auth.js ────────────────────────────────────────────
import {
  _sbInit,
} from './controller/auth.js';

// ── Step 7e: controller/share.js ────────────────────────────────────────────
import {
  sharePlan, shareDiary, exportICS,
} from './controller/share.js';

// ── Step 7e: controller/poster-err.js ────────────────────────────────────────────
import {
  _posterErr, _cortoSheetPosterErr, _edPosterErr,
} from './controller/poster-err.js';

// storage (adapter de localStorage) → src/storage/storage.js (Step 3).
// Importado al top del módulo. Usa FESTIVAL_STORAGE_KEY vía el STATE BRIDGE.
// p8 Step 8a: el STATE BRIDGE vive ahora en state/state-bridge.js (import L20).

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
  confirmReplace:     (el)    => confirmReplace(el.dataset.rmtitle, el.dataset.newtitle, el.dataset.day, el.dataset.time, !!el.closest('#ag-result')),
  removeFromAgenda:   (el)    => removeFromAgenda(el.dataset.title),
  setDelay:           (el)    => setDelay(el.dataset.title, el.dataset.day, el.dataset.time, +el.dataset.mins, el.dataset.venue),
  clearDelay:         (el)    => clearDelay(el.dataset.title, el.dataset.day, el.dataset.time, el.dataset.venue),
  undoDelay:          (el)    => undoDelay(el.dataset.title, el.dataset.day, el.dataset.time, el.dataset.venue),
  checkinLaVi:        (el)    => checkinLaVi(el.dataset.title),
  checkinNoLaVi:      (el)    => checkinNoLaVi(el.dataset.title),
  savePVRating:       ()      => savePVRating(),
  setLang:            (el)    => setLang(el.dataset.code),
  toggleLangDropdown: ()      => toggleLangDropdown(),
  selectLang:         (el)    => selectLang(el),
  forceInclude:       (el)    => forceInclude(el.dataset.title),
  dismissNotice:      (el)    => _dismissNotice(el.dataset.title),
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
  pvLater:               ()      => pvLater(),
  closePlanConfirm:      (el)    => closePlanConfirm(el.dataset.force === '1'),
  closePrioLimit:        ()      => closePrioLimit(),
  dismissSplash:         ()      => dismissSplash(),
  searchOpen:            ()      => searchOpen(),
  searchClose:           ()      => searchClose(),
  togglePastFestRow:     (el)    => _togglePastFestRow(el.closest('.fs-festival-row'), el.dataset.fest),
  openPostViewRating:    (el)    => openPostViewRating(el.dataset.title, el.dataset.day, el.dataset.time, el.dataset.venue, el.dataset.duration),
  selectSplashFest:      (el)    => selectSplashFest(el.dataset.name, el.dataset.meta, el.dataset.fest),
  selectFromDetail:      (el)    => selectFromDetail(el),
  openCombinedFilmSheet: (el)    => _openCombinedFilmSheet(JSON.parse(el.dataset.film)),
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
  openVenueSheet:      (el)    => openVenueSheet(el.dataset.venue),
  closeVenueSheet:     ()      => closeVenueSheet(),
  openPelFromVenue:    (el)    => { closeVenueSheet(); openPelSheet(el.dataset.title); },
  venueDirections:     (el)    => window.open('https://maps.apple.com/?q='+el.dataset.lat+','+el.dataset.lng,'_blank'),
  pafClearSec:         ()      => _pafClearSec(),
  pafClearVenue:       ()      => _pafClearVenue(),
  toggleEveningFilms:  (el)    => _toggleEveningFilms(el),
  toggleWLFromList:    (el)    => _toggleWLFromList(el.dataset.title, el),
  addSuggestion:       (el)    => addSuggestion(el.dataset.title, el.dataset.day, el.dataset.time),
  clearProgramaChip:   ()      => clearProgramaChip(),
  runCalc:             ()      => runCalc(),
  openDiary:           ()      => openDiary(),
  closeDiary:          ()      => closeDiary(),
  shareDiary:          ()      => shareDiary(),
  scrollToSuggestions: ()      => _scrollToSuggestions(),
  removeConflictModal: ()      => _removeConflictModal(),
  scrollToTop:         ()      => _scrollToTop(),

  // ── E: Mi Plan / Schedule actions (10) ──
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
  // Fuente ÚNICA: la detección pre-paint del HTML publica window.__otfLang (lang
  // guardado → navigator.language, es/en). Acá sólo la consumimos, validada contra
  // LANGS (idiomas ACTIVOS — no contra _I18N, que conserva bloques inertes como pt
  // y reactivaría un 'pt' zombi guardado). Fallback defensivo por si el módulo
  // corre sin el inline (nunca debería): storage.getLang() → 'es'.
  const detected = (typeof window!=='undefined' && window.__otfLang) || storage.getLang();
  if(detected && LANGS.includes(detected)) return detected;
  return 'es';
})();

// t(key, params) → src/i18n/i18n.js (Step 4). Importado.

// p8 Step 8d-3: setLang → controller/pipeline.js (orquestador mutate→render).
// Importado de vuelta (arriba) para ACTION_REGISTRY. La init eval-time de _lang
// (arriba) se queda en main.js (bootstrap).

// ── Fin i18n ──────────────────────────────────────────────────────────────

// _applyI18nDOM() → src/i18n/i18n.js (Step 4). Importado.

// ═══════════════════════════════════════════════════════════════
// 1 · DATOS DEL FESTIVAL
//     FILMS, POSTERS, CUSTOM_POSTERS
// ═══════════════════════════════════════════════════════════════
FILMS=[];
// p8 8b: POSTERS/CUSTOM_POSTERS → state/viewstate.js (bridge)

// ── Timezone helper — festival-aware date construction ────────────────────
// TZ_OFFSET se actualiza en loadFestival() desde cfg.timezoneOffset.
// Default '-05:00' = Colombia. Festivals internacionales usan su propio offset.
// Ejemplo: Tribeca NYC junio = '-04:00'
TZ_OFFSET='-05:00';
// FESTIVAL_TRANSPORT: modo de movilización del festival activo.
// Valores: 'transit' (Uber/Metro) · 'walking' (a pie) · 'mixed' (depende de la sede)
// Afecta el texto de aviso de viaje en Mi Plan. Se actualiza en loadFestival().
FESTIVAL_TRANSPORT='transit';
// (funciones/constantes movidas a módulos; ver imports arriba, L8-149)
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

// SUPABASE — _sb/_sbUser: backing del bridge (leídos/escritos por
// controller/{auth,persistence}.js vía globalThis). _SB_URL/_SB_KEY → auth.js.
// p8 8b: _sb/_sbUser → state/viewstate.js (bridge)

// Init — llamado una vez al arrancar

// Magic Link — envía email de acceso

// Sign out

// Cargar estado del usuario desde la nube
// _cloudSaveTimer (debounce de _cloudSave) → controller/persistence.js (Step 7b).

// UI helpers

// Abrir sheet de login
// openAuthSheet → src/view/sheets.js (Step 6b). Importado.
// closeAuthSheet → src/view/sheets.js (Step 6b). Importado.

// _showSignedInSheet → src/view/sheets.js (Step 6b). Importado.

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
// (funciones/constantes movidas a módulos; ver imports arriba, L8-149)
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
const BUILD_VERSION='202607170727';
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
   Añadir           acción de Plan (función específica)  Guardar, Seleccionar
   Interés          acción de ♥ — añadir a la colección  Favorito, Me gusta
   Elegir           confirmar un plan       Guardar, Aceptar
   ────────────────────────────────────────────────── */
// FESTIVAL_BUFFER → src/config.js (Step 1).
savedAgenda=null;
lastRemovedSlots=[]; // tracks up to 5 recently removed films
// MAX_REMEMBERED_SLOTS → src/config.js (Step 1).
// p8 8b: activeMiPlanDay/_ctaRemovedVisible → state/viewstate.js (bridge)
    // CTA B: timer de auto-dismiss
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
// p8 8b: miPlanViewStart → state/viewstate.js (bridge)
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
const _isoToFlag = c  => c&&c.length===2 ? String.fromCodePoint(0x1F1E6+c.toUpperCase().charCodeAt(0)-65)+String.fromCodePoint(0x1F1E6+c.toUpperCase().charCodeAt(1)-65) : '';

/* ══════════════════════════════════════════════════════
   emptyState(icon, title, sub) — componente vacío unificado
   Usa siempre este helper para estados vacíos — nunca inline styles ni emojis
   icon: ICONS.* | title: string | sub: string (opcional)
══════════════════════════════════════════════════════ */
// emptyState, emptyStateHero → src/view/helpers.js (Step 6f). Importados.

/* ── Sistema de modales de confirmación ── */
// showActionModal → src/view/feedback.js (Step 6b). Importado.
// _showModal → src/view/feedback.js (Step 6b). Importado.

// isFullDayBlocked → src/view/components.js (Step 6a). Importado.

// ── CASO 2: al quitar un bloque de no disponible, ¿caben más títulos? ──

// ═══════════════════════════════════════════════════════════════
// 9 · DISPONIBILIDAD
//     showConflictModal, toggleFullDay, addBlock, renderAvDay
// ═══════════════════════════════════════════════════════════════
// showConflictModal → src/view/feedback.js (Step 6b). Importado.
// Controller (p7a) — branchy: si día ya bloqueado, libera; si no, bloquea con conflict modal opcional

// Controller (p7a) — lee 2 inputs DOM, valida, muta con conflict check

// Controller (p7a) — action handler standardizado: mutate → persist → render

// Pure half (p6b) — innerHTML del row del día. NO incluye className ni post-
// render defaults (esos quedan en el impure caller porque son DOM ops).

// Impure caller (p6b) — className + innerHTML + post-render select defaults

/* ── DISPONIBILIDAD — nueva UI ──────────────────────────────────── */

// closeAvSheet → src/view/sheets.js (Step 6b). Importado.

// Controller (p7a) — branchy: full-day usa toggleFullDay, range crea block con conflict check

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

// filmDisplayTitle(f) — patrón Letterboxd
// EN: title_en como principal, title como original (solo si difieren)
// ES: title siempre, sin secundario
// _langDates(cfg) — devuelve fechas en el idioma activo

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

// Impure caller (p6b) — commit a DOM + update pill counts post-render.
// renderFilmListHTML mantuvo su nombre original (ya tenía suffix HTML) como
// la pure half. _rerenderFilmList es el nuevo impure caller. Asimetría
// documentada en plan §1.2.

// ── RENDER SAVED AGENDA ──
// ── Componente unificado: fila de función en agenda ──
// mode='saved'    → ✕ quita de agenda guardada
// mode='scenario' → ✕ quita de watchlist, muestra badge de alternativas

/* ── RENDER — MI PLAN / AGENDA ──────────────────────────────────────── */
// ── _mkCortoItemHtml ───────────────────────────────────────────────────────
// Fuente única de verdad para el item de corto en lista.
// Usado en: pel-sheet (cortos list), Mi Plan (mplan-prog-list x2).
// opts.cls      → clase CSS del row (default: 'mplan-prog-item')
// opts.section  → sección del programa padre — para poster generativo con color correcto
// opts.ratingEl → HTML del botón de calificación (opcional)

// Wrapper — lee data-* y llama openCortoSheet. Evita interpolación de apóstrofes en onclick.

// Controller (p7a) — branchy: si NO está watched, marca + post-view rating modal

// Sim panel dates derive from active festival — never hardcoded
// _simFestStart → src/view/feedback.js (Step 6b). Importado.
// _simFestEnd → src/view/feedback.js (Step 6b). Importado.
// _SIM_TOTAL → src/view/feedback.js (Step 6b). Importado.
// updateSimLabel → src/view/feedback.js (Step 6b). Importado.
// p8 8b: _expandedFilm/_activeMiPlanFilm → state/viewstate.js (bridge)

// ═══════════════════════════════════════════════════════════════
// 12 · RENDER — PLANEAR
//      toggleFilmAlternatives, renderFilmAlternatives
//      toggleArchive, runCalc, saveCurrentScenario, renderAgenda
// ═══════════════════════════════════════════════════════════════

// Controller (p7a) — modal builder + handler closure variant. Modal es custom
// (no showActionModal) por requirements de styling. El handler real vive en
// el `btn.onclick` closure adentro del setTimeout.

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

// (archiveOpen retirado 17 jul — el Historial colapsable fue reemplazado por el Diario)

/* ── Display name — cadena de prioridad para imagen compartida ──
   1. Supabase user_metadata.display_name (cuenta / app nativa)
   2. localStorage 'otrofestiv_display_name' (web sin cuenta)
   3. Email prefix (fallback con cuenta)
   4. null (anónimo)
*/

/* ── SHARE/EXPORT: imagen, ICS ──────────────────────────────────────── */

/* ── SHARE/EXPORT: imagen, ICS ──────────────────────────────────────── */

// ── RESULT HTML ──
// p8 8b: cachedResult → state/viewstate.js (bridge)

// ── forceInclude — crea variante custom con la película forzada ──────

// buildResultHTML → src/view/components.js (Step 6a). Importado.

// ═══════════════════════════════════════════════════════════════
// 13 · RENDER — VISTAS PRINCIPALES
//      renderCartelera, togglePriority, showToast, renderAgenda
// ═══════════════════════════════════════════════════════════════
// Controller (p7a) — branchy: prioritize/unprioritize con prio limit + modal confirm en Planear

// showToast → src/view/feedback.js (Step 6b). Importado.

// ── POST-SELECTION SQUEEZE ──
// Tras elegir una opción, intenta insertar películas excluidas de la watchlist
// que quepan en los huecos reales del plan elegido (usando screensConflict ±10 min).
// Puede superar trueMax porque ese era el máximo dentro del árbol explorado,
// no el máximo real del calendario.

/* ── POST-VIEW RATING SHEET ── */

// Controller (p7a)

// closePVRating → src/view/sheets.js (Step 6b). Importado.

// Controller (p7a) — branchy toggle desde Mi Plan

/* ── CONFLICT SHEET ── */
 // {title, day, time, screen, existingTitle}

// Controller (p7a) — handler del btn de "Reemplazar" en conflict sheet

// closePrioLimit → src/view/sheets.js (Step 6b). Importado.

// runCalc + worker → src/controller/calc.js (Step 7a). Importado.

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

// ── CALENDAR VIEW ──
// p8 8b: view-state (activeView/activeDay/activeVenue/activeSec/selectedIdx/
// activeMNav/cartelaMode/programaSubMode/interesesViewMode/miPlanViewMode/
// programaViewMode/programaChip/_programaChipMatchFn/_currentChips) →
// state/viewstate.js (bridge). main.js los lee/escribe vía globalThis.

// Definición de chips de categoría — agrupan las secciones reales de FICCI

let expandedPelicula=''; // título expandido en vista Por Película

/* ── BÚSQUEDA EN CARTELERA ── */
// ── BÚSQUEDA GLOBAL ────────────────────────────────────────────────────────

/* ── NAV: navegación principal entre tabs ────────────────────────────── */

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

// starSVG → src/view/components.js (Step 6a). Importado.

// Pure half (p6b): construye el HTML de 5 estrellas según el rating actual.
// state param incluido por uniformidad — esta vista no lee state, todo viene
// del parámetro `current`.
// renderRatingStarsHTML → src/view/components.js (Step 6a). Importado.
// Impure caller (p6b): commit a DOM

// Update rápido durante drag — solo actualiza los atributos SVG sin recrear DOM

// Pointer Events API — unificado mouse+touch, con setPointerCapture
// para que el drag funcione correctamente en iOS dentro de transforms

/* ── BOTTOM SHEET: apertura, cierre, acciones ───────────────────────── */

// _dayChips — renderiza días únicos de un film como spans tappables (filtran por día)

// ── pelicula-day tap → filterByDay ──────────────────────────
document.addEventListener('click', function(e){
  const day=e.target.closest('.pelicula-day');
  if(day&&day.dataset.day) filterByDay(day.dataset.day);
});

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

// History API — cerrar cualquier sheet/overlay con botón back del browser

window.addEventListener('popstate',function(e){
  if(!_closeTopSheet()){
    // Ningún sheet abierto — dejar que el browser navegue normalmente
  }
});

// ESC cierra el sheet activo (útil en desktop/tablet)
document.addEventListener('keydown',function(e){
  if(e.key==='Escape') _closeTopSheet();
});
(function(){
  let _startY=0,_dragging=false;
  // BUG DE TIMING (store-gate): main.js se inyecta como <script type=module>
  // dinámico (bootApp en index.html) → NO bloquea DOMContentLoaded, que ya
  // disparó cuando este módulo evalúa. Un listener 'DOMContentLoaded' aquí
  // registra para un evento pasado y NUNCA corre → la UI estática (tabs, bandera
  // del toggle) se queda en el HTML hardcodeado (ES) mientras el contenido
  // dinámico sale en el idioma real → MEZCLA. onDomReady ejecuta ya si el DOM
  // está listo. NUNCA usar addEventListener('DOMContentLoaded') desnudo en src/
  // (lo prohíbe validate.py [dom-ready-guard]).
  onDomReady(()=>{
    _applyI18nDOM(); // incluye la bandera del trigger (absorbió _syncLangTrigger)
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

// ─────────────────────────────────────────────────────────────
// SHEET INDIVIDUAL DE CORTOMETRAJE
// Trata cada corto como película — poster, info, rating, Letterboxd
// ─────────────────────────────────────────────────────────────
 // guarda el HTML del programa padre

// Encuentra el programa padre de un corto individual

// openCortoSheet — card unificada con openPelSheet
// Intereses/Priorizar empaquetan al programa padre completo

// ═══════════════════════════════════════════════════════════════════
// _openCombinedFilmSheet — film individual dentro de un programa combinado
// ───────────────────────────────────────────────────────────────────
// Usa el skeleton exacto de openPelSheet. Omite sección de funciones
// y CTAs — la planificación pertenece al programa padre.
// Template: cualquier festival con is_programa + film_list enriquecido.
// ═══════════════════════════════════════════════════════════════════

// Helper compartido entre la pure half (renderProgramaChipsHTML) y el impure
// caller (renderProgramaChips, que muta _currentChips). Extraído para evitar
// duplicar el cómputo o mezclar la mutación al state UI ephemeral con la pureza.
// _computeProgramaChips → src/view/programa.js (Step 6c). Importado.
// Pure half (p6b) — returns HTML string
// renderProgramaChipsHTML → src/view/programa.js (Step 6c). Importado.
// Impure caller (p6b) — muta _currentChips (UI state ephemeral, out-of-roster) + DOM

// ── Badges de metadata: Q&A e Inscripción previa ────────────────────────

// ── Stack poster para programas combinados ───────────────────────────────

// ── Notices: banner de funciones canceladas/reprogramadas ────────────────
// p8 8b: _dismissedNotices → state/viewstate.js (bridge)
// getActiveNotices → src/view/programa.js (Step 6c). Importado.
// Pure half (p6b)
// renderNoticesBannerHTML → src/view/programa.js (Step 6c). Importado.
// Impure caller (p6b)
// renderNoticesBanner → src/view/programa.js (Step 6c). Importado.

// Pure half (p6c)

// Impure caller (p6c) — scrollTop reset + innerHTML

// Pure half (p6c)

// Impure caller (p6c)

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

// ── Genera el splash rail y el festival selector desde FESTIVAL_CONFIG ──
// Agregar un festival = una entrada en FESTIVAL_CONFIG. Nada más que tocar.
// CHECK_SVG → src/view/components.js (Step 6a). Importado.
// _classifyFestival — fuente única de verdad para el estado temporal de un festival.
// Usada en splash, sheet, y cualquier contexto futuro.
// Retorna: 'ongoing' | 'upcoming' | 'past'
// _classifyFestival → src/view/components.js (Step 6a). Importado.

// _sortFestivals → src/view/components.js (Step 6a). Importado.

// _renderSplashRailHTML → src/view/components.js. Caller impuro _renderSplashRail
// (DOM: puebla #splash-rail + info) → src/controller/festival.js.

// Toggle colapso/expansión de festival pasado en el sheet in-app.
// Primer tap: expande mostrando metadata completa.
// Segundo tap: selecciona el festival vía loadFestival.

// Pure half (p6b) — HTML del festival selector list
// _renderFestivalSelectorHTML → src/view/components.js (Step 6a). Importado.
// Impure caller (p6b) — DOM mutation. Preserva el doble innerHTML= pre-existente
// (bug benign — escribe el mismo valor dos veces, sin efecto observable)

// ─────────────────────────────────────────────────────────────────────────────

// p8 8b: _splashSelectedFestId → state/viewstate.js (bridge)

// ═══════════════════════════════════════════════════════════════════
// AUTO-RESOLVE POSTERS — lbSlug → TMDB search → poster correcto
// Corre en background después de cargar cada festival.
// Usa localStorage como caché para evitar llamadas TMDB repetidas.
// Sobreescribe entradas en POSTERS (no en CUSTOM_POSTERS).
// ═══════════════════════════════════════════════════════════════════

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
  // Regla del selector (decisión Juan, 5 jul 2026):
  //   · EXACTAMENTE 1 festival en curso → se pre-selecciona SOLO: barra con el
  //     nombre, "Entrar" habilitado, cero interacción necesaria.
  //   · 0 o 2+ en curso → acordeón cerrado (.compact): barra mínima solo con el
  //     chevron, el usuario elige. (Reemplaza la regla anterior "el usuario
  //     elige siempre".)
  // Se decide ANTES del reveal (splash aún invisible) → sin flash ni brinco.
  const _ongoingIds=Object.entries(FESTIVAL_CONFIG)
    .filter(([,c])=>_classifyFestival(c)==='ongoing').map(([id])=>id);
  if(_ongoingIds.length===1){
    // Preselección automática: card .on + "Entrar" habilitado, cero interacción.
    _renderSplashRail(_ongoingIds[0]);
    selectSplashFest(null,null,_ongoingIds[0]);
  } else {
    // 0 o 2+ en curso → el usuario elige. El riel arranca centrado en el primer
    // festival y el info lo muestra como PREVIEW; ninguna card .on, "Entrar"
    // disabled hasta un tap (regla 5 jul preservada).
    _splashSelectedFestId=null;
    _renderSplashRail(null);
  }
  // Splash entrada: la animación es 100% CSS (@keyframes en index.html). El
  // contenido es visible por default y JS NO toca opacity → imposible que quede
  // atascado invisible en WKWebView (Bug 1 se resuelve en la capa CSS).
  _renderFestivalSelector(activeFest);
  // El selector del splash NO se rellena — queda el placeholder del markup
  // (data-i18n="splash_elegi"). "Entrar" arranca disabled hasta que se elige.
  // Revelar el splash recién cuando el selector YA tiene el festival correcto:
  // el cambio placeholder→activo ocurre tras opacity:0 (invisible). Doble rAF
  // asegura que el contenido poblado se commitee antes de animar la entrada.
  const _spEl=document.getElementById('otrofestiv-splash');
  if(_spEl){
    requestAnimationFrame(function(){requestAnimationFrame(function(){
      _spEl.classList.add('splash-anim-in');
      // Hard-floor anti-invisible (lección del subsistema splash): la entrada anima
      // opacity con fill:both → bajo throttle del timeline (doc oculto) se quedaría
      // en from{opacity:0}. Tras la ventana total (último delay 1400 + 600 dur = 2000,
      // +200 margen) quitar la animación → cae a la regla estática .splash-anim-in →
      // opacity:1. En foreground la animación ya terminó: no-op (mismos valores). Es
      // relativo al inicio real de la animación (este rAF) → nunca corta el fade.
      setTimeout(function(){
        ['.splash-wordmark','.splash-action','.splash-tagline'].forEach(function(s){
          var el=_spEl.querySelector(s); if(el) el.style.animation='none';
        });
      },2200);
    });});
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
  // p8 Step 8b: el bloque `_lets` (29 viewstate/festival-data/auth) se reubicó a
  // state/viewstate.js (side-effect import, instala en import-phase). Aquí queda
  // solo la exposición de {state, FESTIVAL_CONFIG, ACTION_REGISTRY} + las fns
  // (inline on* de producción + page.evaluate de tests) → 8c.
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
    _posterErr, _cortoSheetPosterErr, _edPosterErr,
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

// p8 Step 7e: _sbInit() DESPUÉS del TEST BRIDGE. _sbInit vive en controller/auth.js
// y escribe _sb/_sbUser como globales bridgeados (bare assignment en módulo strict).
// El defineProperty(globalThis,'_sb') del bridge debe existir antes, o el assignment
// lanza ReferenceError (silenciado por el try/catch interno) y _sb queda null.
_sbInit();
// F1.0 Apple Watch: listener del handoff de identidad (no-op fuera de la app iOS
// con el plugin WatchBridge). Después de _sbInit — usa _sb/_sbUser bridgeados.
initWatchBridge();

/* ── Re-render automático cada 60s ───────────────────────────
   Actualiza estados temporales (AHORA, Ya pasó, días pasados)
   sin depender de que el usuario navegue entre tabs.
   Solo re-renderiza si Planear o Cartelera están visibles.
   Replicable en cualquier festival futuro sin cambios.
────────────────────────────────────────────────────────────── */
// Sincronizar el primer tick con el siguiente minuto del reloj del sistema
// Así el contador avanza exactamente cuando cambia el minuto — no con retraso
// _tickRender — repinta la vista ACTIVA (liviano: sin invalidar cachés ni recomputar
// el planner). Rutea por activeMNav, NO por conjunciones estrechas de (mnav && view):
// el bug del contador congelado ("4h 39min" quieto por horas, cazado por Juan en TT)
// era esta clase — cualquier combinación de estado fuera de las 3 contempladas dejaba
// los headers sensibles al tiempo (TIEMPO LIBRE, AHORA, Ya pasó) sin repintar jamás.
// renderAgenda() rutea internamente seleccion/miplan/planner.
function _tickRender(){
  try{
    if(activeMNav==='mnav-cartelera'){
      if(activeView==='day') render();
    }else{
      renderAgenda();
    }
    updateAgTab();
  }catch(e){ report(e,'tickRender'); }
}
function _startTickLoop(){
  setInterval(_tickRender, 60000);
}
// Esperar al próximo minuto exacto antes de iniciar el loop
const _msToNextMin=(60-new Date().getSeconds())*1000;
setTimeout(function(){ _startTickLoop(); }, _msToNextMin);
// Mientras tanto, tick inmediato para estado inicial correcto
updateAgTab();

// Retraso colaborativo (Fase B): al llegar un cambio por Realtime, repintar Mi Plan
// (donde vive el badge). Targeted — solo si esa vista está activa.
setDelaysRerender(function(){
  if(activeMNav==='mnav-miplan' && activeView==='agenda') renderAgenda();
});

// Sync del plan EN VIVO (F0.5): al llegar un cambio de OTRO dispositivo por Realtime,
// repintar la vista ACTIVA sin navegar. renderActiveView() rutea internamente
// (cartelera/seleccion/miplan/planner) — NO usar showDayView, que fuerza el tab
// Programa y hace "brincar" de vista al recibir un cambio.
setPlanRerender(function(){
  renderActiveView();
});

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
  // Al volver al primer plano: si hay función en los próximos 30min → Mi Plan.
  // try/catch: si el check lanza, el refresh de abajo DEBE correr igual — un throw
  // acá dejaba la vista congelada con datos de hace horas (contador de TIEMPO LIBRE).
  try{
    if(_checkNavigateToMiPlan()&&activeMNav!=='mnav-miplan'){
      switchMainNav('mnav-miplan');
      showAgView();
      updateAgTab();
      return;
    }
  }catch(e){ report(e,'visNavigate'); }
  // Repintar la vista activa SEA CUAL SEA (iOS suspende el setInterval en background;
  // al volver, el usuario no debe ver tiempos viejos ni por un segundo).
  _tickRender();
}); // visibilitychange
// pageshow — cinturón para el wrapper iOS/WKWebView: al restaurar desde bfcache o al
// resumir la app, visibilitychange puede no disparar; pageshow sí. Refresh idempotente.
window.addEventListener('pageshow', function(){ _tickRender(); });

// html2canvas eliminado — Canvas API puro
// lugar click-outside handled by lugarOutside()
updateAgTab();render();

// ── p8: marcador de readiness ────────────────────────────────────────────────
// Bootstrap síncrono completo: módulo evaluado, STATE/TEST BRIDGE + listener
// delegado instalados, render inicial hecho. Los tests esperan
// [data-app-ready="1"] para sincronizar contra JS-ready (no DOM estático),
// cerrando races de interacción-antes-de-bootstrap (ej. flaky #splash-dropdown).
document.documentElement.dataset.appReady = '1';

// iOS nativo (Capacitor): ocultar el splash nativo recién cuando la app ya pintó
// (oscura) → evita el flash blanco de la WebView durante la carga remota de
// server.url. requestAnimationFrame asegura un frame pintado antes de ocultar.
// ⚠ REQUIERE launchAutoHide:false en capacitor.config.json (plugins.SplashScreen);
// si no, el splash nativo ya se auto-ocultó y este hide() es no-op. Guard ?. →
// inofensivo en web/PWA o si el plugin @capacitor/splash-screen no está instalado.
requestAnimationFrame(() => window.Capacitor?.Plugins?.SplashScreen?.hide?.());

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
        if(!serverBuild) return;
        // Comparar contra BUILD_VERSION (horneado en el bundle que REALMENTE está
        // corriendo) — único indicador confiable de qué código se cargó. NO contra
        // localStorage, que solo refleja "vi este version.json", no "cargué este JS".
        if(serverBuild === BUILD_VERSION){
          // El bundle cargado ya es el del servidor → recién ahora marcar como
          // actualizado. (Antes se escribía ANTES de recargar → en iOS el reload
          // servía el bundle viejo desde caché y el marcador quedaba "actualizado"
          // para siempre, deshabilitando el trigger.)
          if(localStorage.getItem(_BUILD_KEY) !== serverBuild){
            localStorage.setItem(_BUILD_KEY, serverBuild);
          }
          return;
        }
        // serverBuild !== BUILD_VERSION → hay un bundle nuevo que todavía no cargó.
        // Recargar con cache-busting REAL del documento (?v=serverBuild) para
        // bypassear la caché HTTP de WKWebView que causaba el stuck en iOS.
        // Guard de loop: si ya estamos en ?v=serverBuild, no re-navegar (el
        // sub-recurso pudo quedar en caché) — se reintenta en el próximo cold-start.
        if(!_reloading && location.href.indexOf('v=' + serverBuild) === -1){
          _reloading = true;
          location.href = location.href.split('?')[0].split('#')[0] + '?v=' + serverBuild;
        }
        // NO se escribe orf_build aquí: el bundle nuevo aún no cargó.
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

// ── BUSCADOR — sistema completo ───────────────────────────────────────────
// Overlay position:fixed. Se posiciona debajo del topbar.
// El teclado ajusta la altura via visualViewport.

// Reposition when keyboard appears/disappears
if(window.visualViewport){
  window.visualViewport.addEventListener('resize', searchPositionOverlay);
}

// ── FILTRO SECCIÓN ────────────────────────────────────────────────────────
// Mismo patrón que lugarOpen/Close/Outside/Toggle.
// activeSec: 'all' | nombre exacto de sección (f.section)

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

// Fallback para poster en openCortoSheet: los cortos no están en FILMS top-level,
// por lo que _posterErr no puede encontrarlos y los oculta. Esto muestra el placeholder.

