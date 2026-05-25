// ── src/state/viewstate.js ───────────────────────────────────────────────────
// p8 Step 8b — TEST BRIDGE viewstate reubicado desde main.js (Wave 8: relocate).
//
// Aloja los 29 lets NO-roster (view-state + festival-data + calc-cache + auth/
// splash/posters) que antes vivían en main.js, e instala el `_lets` bridge
// (Object.defineProperty sobre globalThis) cuyos closures cierran sobre ESTOS
// lets. main.js y los demás módulos los leen/escriben vía globalThis (bare) —
// sin cambios en consumidores.
//
// Importado (side-effect, sin bindings) TEMPRANO en main.js → el install corre
// en la fase de import, ANTES del body de main.js. Esto neutraliza el gotcha
// clase-_sbInit: toda escritura eval-time de main.js (IIFE de detección-festival
// que setea _splashSelectedFestId; loadFestival que setea POSTERS/LB_SLUGS/
// DAY_KEYS/CUSTOM_POSTERS/cachedResult) ocurre después del install.
//
// NO redeclarar estos nombres en main.js (shadowearía el bridge). validate.py
// [viewstate-shadow] lo verifica.

import { _DEFAULT_FEST_ID } from '../config.js';

// ── VIEWSTATE BRIDGE START (p8 Step 8b) ──────────────────────────────
// festival-data / calc-cache
let DAY_KEYS=['Martes','Miércoles','Jueves','Viernes','Sábado','Domingo'];
let cachedResult=null;
// view-state núcleo (tests/helpers escriben activeDay/programaViewMode vía evaluate)
let activeView='day',activeDay='Martes',activeVenue='all',activeSec='all',selectedIdx=null,activeMNav='mnav-cartelera';
let cartelaMode='pelicula';      // 'horario' | 'pelicula' (interno)
let programaSubMode='hoy';       // 'hoy' | 'manana'
let interesesViewMode='grid';    // 'grid' | 'list' para Intereses
let miPlanViewMode='calendar';   // 'calendar' | 'list' para Mi Plan
let programaViewMode='grid';     // 'grid' | 'list'
let programaChip='all';          // chip activo en Explorar
let _programaChipMatchFn=null;   // función de match activa para filtrar
let _currentChips=[];            // chips dinámicos del festival activo
let _dismissedNotices=new Set();
// agenda / miplan view-state
let _activeMiPlanFilm='';        // key: title+time — highlighted from calendar click
let _expandedFilm='';            // key: title+day+time — which film has alternatives open
let activeMiPlanDay=null;
let miPlanViewStart=0;           // 0-4, step 1, shows 2 days
let _ctaRemovedVisible=false;    // CTA B: post-eliminación
let archiveOpen=false;
// auth / splash / posters
let _sb=null, _sbUser=null;
let LB_SLUGS={};
let POSTERS={};
let CUSTOM_POSTERS={};
let _splashSelectedFestId=_DEFAULT_FEST_ID;

const _lets = {
  DAY_KEYS:           [() => DAY_KEYS,           v => { DAY_KEYS = v; }],
  cachedResult:       [() => cachedResult,       v => { cachedResult = v; }],
  activeDay:          [() => activeDay,          v => { activeDay = v; }],
  activeView:         [() => activeView,         v => { activeView = v; }],
  activeVenue:        [() => activeVenue,        v => { activeVenue = v; }],
  activeSec:          [() => activeSec,          v => { activeSec = v; }],
  selectedIdx:        [() => selectedIdx,        v => { selectedIdx = v; }],
  activeMNav:         [() => activeMNav,         v => { activeMNav = v; }],
  programaSubMode:    [() => programaSubMode,    v => { programaSubMode = v; }],
  programaViewMode:   [() => programaViewMode,   v => { programaViewMode = v; }],
  cartelaMode:        [() => cartelaMode,        v => { cartelaMode = v; }],
  interesesViewMode:  [() => interesesViewMode,  v => { interesesViewMode = v; }],
  miPlanViewMode:     [() => miPlanViewMode,     v => { miPlanViewMode = v; }],
  _sbUser:            [() => _sbUser,            v => { _sbUser = v; }],
  _sb:                [() => _sb,                v => { _sb = v; }],
  LB_SLUGS:           [() => LB_SLUGS,           v => { LB_SLUGS = v; }],
  POSTERS:            [() => POSTERS,            v => { POSTERS = v; }],
  CUSTOM_POSTERS:     [() => CUSTOM_POSTERS,     v => { CUSTOM_POSTERS = v; }],
  _splashSelectedFestId:[() => _splashSelectedFestId, v => { _splashSelectedFestId = v; }],
  programaChip:       [() => programaChip,       v => { programaChip = v; }],
  _programaChipMatchFn:[() => _programaChipMatchFn, v => { _programaChipMatchFn = v; }],
  _dismissedNotices:  [() => _dismissedNotices,  v => { _dismissedNotices = v; }],
  _currentChips:      [() => _currentChips,      v => { _currentChips = v; }],
  _activeMiPlanFilm:  [() => _activeMiPlanFilm,  v => { _activeMiPlanFilm = v; }],
  _expandedFilm:      [() => _expandedFilm,      v => { _expandedFilm = v; }],
  activeMiPlanDay:    [() => activeMiPlanDay,    v => { activeMiPlanDay = v; }],
  miPlanViewStart:    [() => miPlanViewStart,    v => { miPlanViewStart = v; }],
  _ctaRemovedVisible: [() => _ctaRemovedVisible, v => { _ctaRemovedVisible = v; }],
  archiveOpen:        [() => archiveOpen,        v => { archiveOpen = v; }],
};
for (const [k, [get, set]] of Object.entries(_lets)) {
  Object.defineProperty(globalThis, k, { get, set, configurable: true });
}
// ── VIEWSTATE BRIDGE END (p8 Step 8b) ────────────────────────────────
