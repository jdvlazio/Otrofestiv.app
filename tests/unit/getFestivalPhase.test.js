// Integration tests for _getFestivalPhase — composer que delega a _endedStats,
// _classifyTodayScreenings y _gapSuggestion. Verifica que cada una de las 5
// fases retorna el shape correcto + los 3 puntos de `null`.
//
// Stub strategy: festivalEnded, simNow, simTodayStr, screeningPassed se
// inyectan como stubs para controlar las branches deterministicamente.

const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

function load(opts = {}) {
  return loadDomain({
    globals: {
      FILMS: opts.FILMS || [],
      watched: opts.watched || new Set(),
      savedAgenda: opts.savedAgenda ?? null,
      filmRatings: opts.filmRatings || {},
      DAY_KEYS: opts.DAY_KEYS || [],
      FESTIVAL_DATES: opts.FESTIVAL_DATES || {},
      DEFAULT_DURATION_MIN: 90,
      festivalEnded: opts.festivalEnded || (() => false),
      simNow: opts.simNow || (() => new Date()),
      simTodayStr: opts.simTodayStr || (() => ''),
      screeningPassed: opts.screeningPassed || (() => false),
    },
  });
}

test('festivalEnded=true → phase:"ended" con stats correctos', () => {
  const { _getFestivalPhase } = load({
    festivalEnded: () => true,
    FILMS: [{ title: 'F1' }, { title: 'F2' }],
    watched: new Set(['F1', 'F2']),
    filmRatings: { F1: 5 },
    savedAgenda: { schedule: [{}, {}] },
  });
  const r = _getFestivalPhase();
  assert.deepStrictEqual(r, {
    phase: 'ended',
    totalWatched: 2,
    totalPlanned: 2,
    pendingRatings: 1,
  });
});

test('savedAgenda vacío o ausente → null', () => {
  // No agenda
  assert.strictEqual(load({ savedAgenda: null })._getFestivalPhase(), null);
  // Agenda con schedule vacío
  assert.strictEqual(
    load({ savedAgenda: { schedule: [] } })._getFestivalPhase(),
    null
  );
});

test('now < FESTIVAL_START → phase:"before" con daysDiff', () => {
  // FESTIVAL_DATES[DAY_KEYS[0]] = '2026-06-03' → FESTIVAL_START = 2026-06-03T00:00:00
  // simNow = 2026-06-01T10:00:00 → 38 horas antes → ceil(38/24) = 2 días
  const { _getFestivalPhase } = load({
    savedAgenda: { schedule: [{ day: 'MAR 21', time: '10:00 AM' }] },
    DAY_KEYS: ['MAR 21'],
    FESTIVAL_DATES: { 'MAR 21': '2026-06-03' },
    simNow: () => new Date('2026-06-01T10:00:00'),
  });
  const r = _getFestivalPhase();
  assert.strictEqual(r.phase, 'before');
  assert.strictEqual(r.daysDiff, 2);
});

test('día con screenings todas pasadas → phase:"evening"', () => {
  // simNow=20:00 → todas las screenings del día (9am, 11am) ya terminaron.
  // todayWatched=[] porque watched está vacío y screeningPassed stubbed a false.
  const todayKey = 'MAR 21', today = '2026-06-03';
  const { _getFestivalPhase } = load({
    savedAgenda: {
      schedule: [
        { _title: 'F1', day: todayKey, time: '9:00 AM', duration: '60 min' },
        { _title: 'F2', day: todayKey, time: '11:00 AM', duration: '90 min' },
      ],
    },
    DAY_KEYS: [todayKey],
    FESTIVAL_DATES: { [todayKey]: today },
    simNow: () => new Date(`${today}T20:00:00`),
    simTodayStr: () => today,
  });
  const r = _getFestivalPhase();
  assert.strictEqual(r.phase, 'evening');
  assert.strictEqual(r.todayScreenings.length, 2);
  assert.deepStrictEqual(r.todayWatched, []);
});

test('próxima función en ≤ 45 min → phase:"next"', () => {
  // simNow=18:30 (1110 min), screening planeado a 19:00 (1140) → minsUntil=30
  const todayKey = 'MAR 21', today = '2026-06-03';
  const f1 = { _title: 'F1', day: todayKey, time: '7:00 PM', duration: '90 min' };
  const { _getFestivalPhase } = load({
    savedAgenda: { schedule: [f1] },
    DAY_KEYS: [todayKey],
    FESTIVAL_DATES: { [todayKey]: today },
    simNow: () => new Date(`${today}T18:30:00`),
    simTodayStr: () => today,
  });
  const r = _getFestivalPhase();
  assert.strictEqual(r.phase, 'next');
  assert.strictEqual(r.minsUntil, 30);
  assert.strictEqual(r.isNow, false);
  assert.strictEqual(r.next._title, 'F1');
});

test('gap > 45 min entre función pasada y próxima → phase:"between" con gapSuggestion', () => {
  // f1 (10:00-11:00) y f2 (15:00-16:30) planeadas. Now = 12:30. Gap: 11:00-15:00 = 240 min.
  // Sugerencia: film del día 12:00-13:00 que cabe en el gap.
  const todayKey = 'MAR 21', today = '2026-06-03';
  const f1 = { _title: 'F1', day: todayKey, time: '10:00 AM', duration: '60 min' };
  const f2 = { _title: 'F2', day: todayKey, time: '3:00 PM', duration: '90 min' };
  const suggestion = { title: 'Sugg', day: todayKey, time: '12:00 PM', duration: '60 min' };
  const { _getFestivalPhase } = load({
    FILMS: [suggestion],
    savedAgenda: { schedule: [f1, f2] },
    DAY_KEYS: [todayKey],
    FESTIVAL_DATES: { [todayKey]: today },
    simNow: () => new Date(`${today}T12:30:00`),
    simTodayStr: () => today,
  });
  const r = _getFestivalPhase();
  assert.strictEqual(r.phase, 'between');
  assert.strictEqual(r.gapMin, 240);
  assert.strictEqual(r.gapFromMin, 660);
  assert.strictEqual(r.gapToMin, 900);
  assert.strictEqual(r.minsUntil, 150);
  assert.strictEqual(r.next._title, 'F2');
  assert.strictEqual(r.lastDone._title, 'F1');
  assert.strictEqual(r.gapSuggestion, suggestion);
});
