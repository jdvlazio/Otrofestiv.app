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

// ── Step 4: i18n.js (import — _I18N + t + _applyI18nDOM). _lang vive en state
//   (bridge); la init eval-time de _lang se queda en main.js, setLang → pipeline.js (8d-3).
import { _I18N, t, _applyI18nDOM } from './i18n/i18n.js';

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
  _renderSplashDropdownHTML, _renderFestivalSelectorHTML, _classifyFestival,
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
  saveWL, saveWatched, saveRating, saveAV, saveSavedAgenda, savePrio, saveLastSlot, saveDelays, saveState, loadState, _cloudLoad, _sbUpdateUI, submitAuthEmail, submitOTP, deleteAccount, signOutAndClose,
} from './controller/persistence.js';

// ── Step 7c: controller/pipeline.js — render dispatchers. ────────────────────
import {
  renderActiveView, switchMainNav, showDayView, showAgView, updateAgTab, _reRenderIntereses, _rerenderFilmList, _getProgramaPhase, _updateProgramaActiveFilter, initProgramaModeBar, setLang,
} from './controller/pipeline.js';

// ── Step 7d-1: controller/sheets-controller.js — sheets+rating+AV+toast+utils. ──
import {
  openPelSheet, closePelSheet, _closeTopSheet, openCortoSheet, openCortoSheetFromEl, _openCombinedFilmSheet, _findParentProgram, openConflictSheet, closeConflictSheet, openPrioLimit, openPlanConfirm, closePlanConfirm, openPostViewRating, openRatingSheet, closeRatingSheet, openAvSheet, selectAvDay, setAvType, confirmAvBlock, renderAvDay, addBlock, removeBlock, toggleFullDay, _setAvAddOpen, showActionToast, _dismissToastAction, countryToFlags, filmDisplayTitle, _genreEN, _removePlanItem, savePVRating,
} from './controller/sheets-controller.js';

// ── Step 7d-2: controller/overlays.js — seccion/search/lugar dropdowns. ──────
import {
  seccionClose, seccionToggle, searchOpen, searchClose, searchPositionOverlay, searchQuery, lugarOpen, lugarToggle,
} from './controller/overlays.js';

// ── Step 7d-3: controller/handlers.js — mutators+filters+composites. ─────────
import {
  toggleWL, toggleWatched, togglePelPrio, togglePelWL, setDelay, undoDelay, clearDelay, removeFromAgenda, addSuggestion, checkinLaVi, checkinNoLaVi, forceInclude, togglePriority, swapPriority, markWatchedFromPlan, confirmReplace, removeFilmFromScenario, _dismissNotice, selectMiPlanDay, miPlanNav, toggleMplanProg, setActivePlanFilm, selectFromDetail, toggleFilmAlternatives, toggleArchive, _toggleEveningFilms, filterByVenue, filterByDay, filterBySection, setInteresesView, setProgramaMode, toggleProgramaView, setProgramaView, setProgramaChip, clearProgramaChip, _pafClearSec, _pafClearVenue, _toggleWLFromList, saveCurrentScenario, jumpToScenario, _scrollToAgSection, _setExpandedFilm, _closePelAndRemove, _closePelAndRate, _navTo, _closeAuthAndReset, _toggleCtxOlder, _toggleWatchedAndClose, _toggleWLAndClose, _activatePlanFilm, _scrollToSuggestions, _removeConflictModal, _scrollToTop, _searchOpenFilm, _searchOpenCorto,
} from './controller/handlers.js';

// ── Step 8d-4: controller/loader.js (loadFestival + dismissSplash) ───────────
import {
  loadFestival, dismissSplash,
} from './controller/loader.js';

// ── Step 7e: controller/festival.js ────────────────────────────────────────────
import {
  toggleSplashDropdown, _togglePastFest, _renderSplashDropdown, _togglePastFestRow, _renderFestivalSelector, selectSplashFest, _autoResolveFestivalPosters,
} from './controller/festival.js';

// ── Step 7e: controller/auth.js ────────────────────────────────────────────
import {
  _sbInit,
} from './controller/auth.js';

// ── Step 7e: controller/share.js ────────────────────────────────────────────
import {
  sharePlan, exportICS,
} from './controller/share.js';

// ── Step 7e: controller/poster-err.js ────────────────────────────────────────────
import {
  _posterErr, _cortoSheetPosterErr,
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
  closePlanConfirm:      (el)    => closePlanConfirm(el.dataset.force === '1'),
  closePrioLimit:        ()      => closePrioLimit(),
  dismissSplash:         ()      => dismissSplash(),
  toggleSplashDropdown:  ()      => toggleSplashDropdown(),
  searchOpen:            ()      => searchOpen(),
  searchClose:           ()      => searchClose(),
  togglePastFest:        (el)    => _togglePastFest(el),
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
  pafClearSec:         ()      => _pafClearSec(),
  pafClearVenue:       ()      => _pafClearVenue(),
  toggleEveningFilms:  (el)    => _toggleEveningFilms(el),
  toggleWLFromList:    (el)    => _toggleWLFromList(el.dataset.title, el),
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

// p8 Step 8d-3: setLang → controller/pipeline.js (orquestador mutate→render).
// Importado de vuelta (arriba) para ACTION_REGISTRY. La init eval-time de _lang
// (arriba) se queda en main.js (bootstrap).

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
// _festDate(dateStr, time) → Date — construye Date con TZ_OFFSET explícito.
// Lee (contrato implícito): TZ_OFFSET (offset del festival activo, e.g. '-05:00').
// Inputs: dateStr en formato YYYY-MM-DD, time en formato HH:mm.
// Returns: Date object cuyo valor representa dateStr+time en la TZ del festival.
// En _SCHED_PURE_FNS: el worker la consume vía .toString() con la misma TZ_OFFSET inyectada.
// _festDate → src/domain/time.js (Step 5). Importado.
// p8 (fix): TMDB_API_KEY se movió a config.js (export const), importado por
// controller/festival.js + poster-err.js como binding real. Antes era un const
// module-local aquí que esos módulos leían como global fantasma (undefined en
// globalThis → ReferenceError, enmascarado sólo por el .catch del auto-resolve).

/* ── POSTER GENERATIVO — identidad Otrofestiv (regla canónica) ────────
   PRIORIDAD DE POSTER (en todo contexto — grilla, card, Mi Plan):
     1. Poster real (CUSTOM_POSTERS > POSTERS/TMDB)
     2. Poster generativo (solo si no hay real)
     3. Placeholder vacío (surf-2) — nunca negro
   REGLA DE DETECCIÓN:
     f.type === 'event'  → makeEventPoster()
     f.is_cortos === true → getPosterSrc(title,true) || makeProgramPoster(title,dur,section)
     resto               → getPosterSrc(title,false) || null
   ONERROR: siempre this.remove() — nunca this.style.opacity=0
   p8 Step 8d-2: el builder generativo vive en view/components.js
   (_buildPosterV16 + make*Poster). El antiguo _buildPosterSVG de main.js
   era dead code (cero callers) → eliminado.
────────────────────────────────────────────────────────────────────── */

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
// p8 8b: LB_SLUGS → state/viewstate.js (bridge)

// Nuevo formato: lee lbSlug directamente del objeto film si existe

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

// p8 Step 8d-1: normTitle → domain/film.js (puro). Importado + re-expuesto global
// (Object.assign) para los lectores bare (controller/{persistence,handlers,overlays}).

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
const BUILD_VERSION='202605251543';
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

// ═══════════════════════════════════════════════════════════════
// 6 · MI PLAN — HELPERS & RENDER
//     mplanPx, mplanPct, renderMiPlanCalendar, selectMiPlanDay
// ═══════════════════════════════════════════════════════════════

// REGLA: scroll a mplan-detail — mide el topbar directamente del DOM,
// no depende de --tb-total (incorrecto en mobile por incluir nav inferior).
// Usar esta función en TODOS los contextos que necesiten bajar al detalle.

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

// ── Notificaciones locales — aviso 30 min antes de cada función ───────────

// Controller (p7a)

// Controller (p7a)

// Controller (p7a)

/* ── saveState — batching de localStorage ── */

// ═══════════════════════════════════════════════════════════════
// 8 · EVENT HANDLERS — MI LISTA
//     toggleWL, toggleWatched, removeFromAgenda
// ═══════════════════════════════════════════════════════════════

/* ── ACTIONS: watchlist, prioridades, vistas, retraso ───────────────── */
// Controller (p7a) — el más branchy de los handlers. 3 branches:
//   A: remove con confirm modal (film en savedAgenda)
//   B: remove directo (film NO en savedAgenda)
//   C: add (con detección de "todas funciones bloqueadas" + UI variants)

// Controller (p7a) — branchy toggle con confirm modal en branch B

// ── FUZZY SEARCH — accent insensitive ──

// Controller (p7a) — modal callback contiene el handler real (closure variant)

// Controller (p7a) — multi-step: add to watchlist + add to plan + cleanup
// lastRemovedSlots + jump al día. NO usa modal (excepto conflict sheet en
// rama de error). NOTE: state snapshot re-leído tras mutaciones interleaved
// porque condicionalmente openConflictSheet sale temprano y necesita state
// fresh para el branch.

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
// p8 8b: DAY_KEYS → state/viewstate.js (bridge)

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

// p8 8b: archiveOpen → state/viewstate.js (bridge)

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

// Pure half (p6b) — HTML del dropdown list
// _renderSplashDropdownHTML → src/view/components.js (Step 6a). Importado.
// Impure caller (p6b) — DOM mutations en 3 elementos del splash

// Toggle colapso/expansión de festival pasado en el sheet in-app.
// Idéntico en comportamiento a _togglePastFest del splash.
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

// p8 Step 7e: _sbInit() DESPUÉS del TEST BRIDGE. _sbInit vive en controller/auth.js
// y escribe _sb/_sbUser como globales bridgeados (bare assignment en módulo strict).
// El defineProperty(globalThis,'_sb') del bridge debe existir antes, o el assignment
// lanza ReferenceError (silenciado por el try/catch interno) y _sb queda null.
_sbInit();

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

