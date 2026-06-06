// ESLint flat config — gate de no-undef para src/ (módulos ESM del app).
// Objetivo acotado: cazar referencias a variables NO declaradas (ej. el `f`
// suelto que crasheó My Plan) estáticamente, en todos los paths, en cada PR.
// NO habilita el set "recommended" (sería ruido en un código grande existente):
// solo no-undef. Los globals del STATE/VIEWSTATE BRIDGE se declaran acá para
// que no den falsos positivos (en ESM los `import` se resuelven solos).
const globals = require('globals');

// Bridge globals (bare en el código, respaldados por globalThis getters/setters).
// Fuente: src/state/state-bridge.js (_BRIDGE_KEYS) + src/state/viewstate.js (_lets).
// Si se agrega/quita un bridge key allá, actualizar acá.
const BRIDGE = {};
[
  // STATE BRIDGE (19)
  'watchlist','watched','prioritized','filmRatings','filmDelays','filmDelaysHistory',
  'savedAgenda','availability','lastRemovedSlots','_lang','_simTime','FILMS',
  'FESTIVAL_DATES','FESTIVAL_END','PRIO_LIMIT','TZ_OFFSET','FESTIVAL_TRANSPORT',
  '_activeFestId','FESTIVAL_STORAGE_KEY',
  // VIEWSTATE BRIDGE (29)
  'DAY_KEYS','cachedResult','activeView','activeDay','activeVenue','activeSec',
  'selectedIdx','activeMNav','programaSubMode','programaViewMode','cartelaMode',
  'interesesViewMode','miPlanViewMode','_sbUser','_sb','LB_SLUGS','POSTERS',
  'CUSTOM_POSTERS','_splashSelectedFestId','programaChip','_programaChipMatchFn',
  '_dismissedNotices','_currentChips','_activeMiPlanFilm','_expandedFilm',
  'activeMiPlanDay','miPlanViewStart','_ctaRemovedVisible','archiveOpen',
].forEach(k => { BRIDGE[k] = 'writable'; });

module.exports = [
  {
    files: ['src/**/*.js'],
    // Solo corremos no-undef. Los `eslint-disable ... no-eval` legítimos del código
    // (ej. calc.js: eval() para serializar pure-fns al worker) quedarían marcados
    // como "unused" bajo este set mínimo — se preserva la anotación y se silencia.
    linterOptions: { reportUnusedDisableDirectives: 'off' },
    languageOptions: {
      ecmaVersion: 2023,
      sourceType: 'module',
      globals: {
        ...globals.browser, ...globals.worker, ...BRIDGE,
        // expuestas en globalThis (main.js Object.assign) y usadas bare cross-módulo
        normTitle: 'readonly',
        // librería UMD cargada por <script> CDN en index.html
        supabase: 'readonly',
      },
    },
    rules: {
      'no-undef': 'error',
    },
  },
];
