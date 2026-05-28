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
      FESTIVAL_DATES: opts.FESTIVAL_DATES || { 'MAR 21': '2026-06-05' },
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

test('priorityCost>0 → index 0 always includes the prioritized film (bug #1 regression)', () => {
  // A (priorizada) solapa B y C en D1; D y E en D2 son compatibles entre sí.
  //   trueMax            = {B,C,D,E} = 4  → balanceado 2/2 (dayBalance 0) pero SIN A
  //   maxWithPriorities  = {A,D,E}   = 3  → 1/2 (dayBalance 0.5), CON A
  // Pre-fix: el sort final solo miraba dayBalance → el plan mayor sin A ganaba el
  // índice 0 ("Tu plan"), dejando la prioridad en "no incluidas". El fix antepone
  // los planes que respetan TODAS las prioridades. El índice 0 debe incluir A.
  const films = [
    { title: 'A', day: 'D1', time: '10:00 AM', duration: '180 min', venue: 'Sala A', section: 'S1' },
    { title: 'B', day: 'D1', time: '10:00 AM', duration: '60 min',  venue: 'Sala A', section: 'S2' },
    { title: 'C', day: 'D1', time: '11:30 AM', duration: '60 min',  venue: 'Sala A', section: 'S3' },
    { title: 'D', day: 'D2', time: '10:00 AM', duration: '90 min',  venue: 'Sala A', section: 'S4' },
    { title: 'E', day: 'D2', time: '2:00 PM',  duration: '90 min',  venue: 'Sala A', section: 'S5' },
  ];
  // La enumeración usa Math.random (no determinística por design): el invariante
  // debe cumplirse en TODAS las corridas.
  for (let run = 0; run < 10; run++) {
    const { computeScenarios } = loadPlanner({
      FILMS: films,
      prioritized: new Set(['A']),
      FESTIVAL_DATES: { D1: '2026-06-05', D2: '2026-06-06' },
    });
    const scenarios = computeScenarios(['A', 'B', 'C', 'D', 'E']);
    assert.ok(scenarios.length > 0, `run ${run}: expected scenarios`);
    // Precondición: el fixture realmente ejercita el bug (prioridad cuesta cardinalidad).
    assert.strictEqual(scenarios[0].priorityCost, 1, `run ${run}: expected priorityCost=1 (fixture inválido si no)`);
    const idx0 = scenarios[0].schedule.map(s => s._title);
    assert.ok(idx0.includes('A'), `run ${run}: index 0 debe incluir la priorizada A, fue [${idx0.join(',')}]`);
  }
});

test('same watchlist → deterministic output across runs (bug #2 regression)', () => {
  // A conflicta con B; C compatible con ambos. trueMax=2 → {A,C} o {B,C},
  // ambos dayBalance 0, sin prioridad. Pre-fix: shuffle usaba Math.random →
  // el índice 0 alternaba entre {A,C} y {B,C} entre corridas. Con el RNG
  // sembrado por la watchlist (_mulberry32(_titleSeed(titles))) el output es
  // estable: misma watchlist = mismo seed = mismos escenarios en el mismo orden.
  const films = [
    { title: 'A', day: 'D1', time: '10:00 AM', duration: '90 min', venue: 'Sala A', section: 'S1' },
    { title: 'B', day: 'D1', time: '10:30 AM', duration: '90 min', venue: 'Sala A', section: 'S2' }, // conflicta A
    { title: 'C', day: 'D1', time: '2:00 PM',  duration: '90 min', venue: 'Sala A', section: 'S3' }, // compatible
  ];
  const sig = () => {
    const { computeScenarios } = loadPlanner({ FILMS: films, FESTIVAL_DATES: { D1: '2026-06-05' } });
    return computeScenarios(['A', 'B', 'C'])
      .map(sc => sc.schedule.map(s => s._title).sort().join(','))
      .join(' | ');
  };
  // 8 corridas (no las 3 del spec): en estado-buggy cada corrida es ~50/50 entre
  // {A,C}/{B,C}, así que 3 corridas falsearían-pasan ~25% de las veces. Con 8 la
  // probabilidad de falso-pase del guard cae a <1%.
  const base = sig();
  assert.ok(base.length > 0, 'expected at least one scenario');
  for (let run = 2; run <= 8; run++) {
    assert.strictEqual(sig(), base, `corrida ${run} difiere de la 1: output no determinístico`);
  }
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
