// Property tests for computeScenarios — extracted from index.html via load-domain.
// Contract: NO determinístico por design (random restarts en cada fase). Los
// tests validan invariantes que cualquier output válido cumple, no outputs
// específicos.
//
// Fixtures pequeñas (3 films máx) para mantener velocidad y reducir chance
// de hit del MAX_NODES_PER_CALL=80000 cap.

const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

function loadPlanner(opts = {}) {
  return loadDomain({
    globals: {
      FILMS: opts.FILMS || [],
      watched: opts.watched || new Set(),
      prioritized: opts.prioritized || new Set(),
      availability: opts.availability || {},
      savedAgenda: opts.savedAgenda || null,
      FESTIVAL_BUFFER: 15,
      FESTIVAL_TRANSPORT: 'transit',
      FESTIVAL_CONFIG: {
        test: { venues: { 'Sala A': { short: 'A', lat: 6.25, lng: -75.57 } } },
      },
      _activeFestId: 'test',
      DEFAULT_DURATION_MIN: 90,
      _simTime: '2026-06-05T08:00:00Z',
      FESTIVAL_END: new Date('2099-01-01'),
      FESTIVAL_DATES: { 'MAR 21': '2026-06-05' },
      TZ_OFFSET: '-05:00',
    },
  });
}

test('empty pending (all watched) → returns []', () => {
  const films = [
    { title: 'F1', day: 'MAR 21', time: '10:00 AM', duration: '90 min', venue: 'Sala A', section: 'S' },
    { title: 'F2', day: 'MAR 21', time: '2:00 PM', duration: '90 min', venue: 'Sala A', section: 'S' },
  ];
  const { computeScenarios } = loadPlanner({
    FILMS: films,
    watched: new Set(['F1', 'F2']),
  });
  assert.deepStrictEqual(computeScenarios(['F1', 'F2']), []);
});

test('each scenario is internally conflict-free', () => {
  // 3 films: F1+F2 conflict (close times same venue), F3 separate
  const films = [
    { title: 'F1', day: 'MAR 21', time: '10:00 AM', duration: '90 min', venue: 'Sala A', section: 'S' },
    { title: 'F2', day: 'MAR 21', time: '10:30 AM', duration: '90 min', venue: 'Sala A', section: 'S' },
    { title: 'F3', day: 'MAR 21', time: '2:00 PM', duration: '90 min', venue: 'Sala A', section: 'S' },
  ];
  const { computeScenarios, screensConflict } = loadPlanner({ FILMS: films });
  const scenarios = computeScenarios(['F1', 'F2', 'F3']);
  assert.ok(scenarios.length > 0, 'expected at least one scenario');
  scenarios.forEach((sc, idx) => {
    const schedule = sc.schedule;
    for (let i = 0; i < schedule.length; i++) {
      for (let j = i + 1; j < schedule.length; j++) {
        assert.strictEqual(
          screensConflict(schedule[i], schedule[j]),
          false,
          `scenario[${idx}] has conflicting pair: ${schedule[i]._title} vs ${schedule[j]._title}`
        );
      }
    }
  });
});

test('scenario.schedule.length <= scenario.trueMax', () => {
  const films = [
    { title: 'F1', day: 'MAR 21', time: '10:00 AM', duration: '90 min', venue: 'Sala A', section: 'S' },
    { title: 'F2', day: 'MAR 21', time: '2:00 PM', duration: '90 min', venue: 'Sala A', section: 'S' },
  ];
  const { computeScenarios } = loadPlanner({ FILMS: films });
  const scenarios = computeScenarios(['F1', 'F2']);
  scenarios.forEach((sc, idx) => {
    assert.ok(
      sc.schedule.length <= sc.trueMax,
      `scenario[${idx}] schedule.length=${sc.schedule.length} > trueMax=${sc.trueMax}`
    );
  });
});

test('excluded and included partition the watchlist (∩=∅, ∪=titles)', () => {
  const films = [
    { title: 'F1', day: 'MAR 21', time: '10:00 AM', duration: '90 min', venue: 'Sala A', section: 'S' },
    { title: 'F2', day: 'MAR 21', time: '10:30 AM', duration: '90 min', venue: 'Sala A', section: 'S' },
    { title: 'F3', day: 'MAR 21', time: '2:00 PM', duration: '90 min', venue: 'Sala A', section: 'S' },
  ];
  const titles = ['F1', 'F2', 'F3'];
  const { computeScenarios } = loadPlanner({ FILMS: films });
  const scenarios = computeScenarios(titles);
  scenarios.forEach((sc, idx) => {
    const included = new Set(sc.schedule.map(s => s._title));
    const excluded = new Set(sc.excluded);
    // Intersection empty
    for (const t of included) {
      assert.strictEqual(excluded.has(t), false, `scenario[${idx}] has ${t} in both included and excluded`);
    }
    // Union = titles
    const union = [...new Set([...included, ...excluded])].sort();
    assert.deepStrictEqual(union, [...titles].sort(), `scenario[${idx}] union does not match titles`);
  });
});

test('all films compatible → each scenario includes all of them', () => {
  // 3 films separated by hours, same venue → zero conflicts
  const films = [
    { title: 'F1', day: 'MAR 21', time: '10:00 AM', duration: '90 min', venue: 'Sala A', section: 'S' },
    { title: 'F2', day: 'MAR 21', time: '2:00 PM', duration: '90 min', venue: 'Sala A', section: 'S' },
    { title: 'F3', day: 'MAR 21', time: '6:00 PM', duration: '90 min', venue: 'Sala A', section: 'S' },
  ];
  const { computeScenarios } = loadPlanner({ FILMS: films });
  const scenarios = computeScenarios(['F1', 'F2', 'F3']);
  assert.ok(scenarios.length > 0, 'expected at least one scenario');
  scenarios.forEach((sc, idx) => {
    assert.strictEqual(sc.schedule.length, 3, `scenario[${idx}] should include all 3 films, got ${sc.schedule.length}`);
  });
});
