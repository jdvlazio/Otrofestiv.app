// QA de dominio del planeador — invariantes de computeScenarios (Planear).
//
// Decisión de Juan (5 jul 2026): Planear es EL feature de la app ("somos un
// planeador y usamos AI para sugerir, encontrar huecos y optimizar al máximo").
// computeScenarios ya tiene 7 property-tests (conflict-free, partición,
// prioridad en índice 0, determinismo). Esta suite cubre lo que faltaba —
// sobre todo la promesa central:
//
// INVARIANTE DE MAXIMALIDAD ("optimizar al máximo"):
//   En cada escenario, NINGÚN título excluido tiene una función que quepa en
//   el schedule sin conflicto. Si cabía, el planeador dejó valor en la mesa.
//
// Más: funciones pasadas jamás en el plan · multi-función elige la viable ·
// prioridades múltiples compatibles todas presentes · prioridad inviable no
// rompe · availability respetada · info:true nunca entra · estrés determinista
// (LCG, sin Math.random) con todos los invariantes por configuración.

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
        test: { venues: {
          'Sala A': { short: 'A', lat: 6.25, lng: -75.57 },
          'Sala B': { short: 'B', lat: 6.26, lng: -75.58 },
        } },
      },
      _activeFestId: 'test',
      DEFAULT_DURATION_MIN: 90,
      _simTime: opts._simTime || '2026-06-05T08:00:00Z',
      FESTIVAL_END: new Date('2099-01-01'),
      FESTIVAL_DATES: opts.FESTIVAL_DATES || { 'MAR 21': '2026-06-05', 'MAR 22': '2026-06-06' },
      TZ_OFFSET: '-05:00',
    },
  });
}

const F = (title, day, time, opts) => Object.assign(
  { title, day, time, duration: '90 min', venue: 'Sala A', section: 'S' }, opts);

// Maximalidad: para cada escenario, ningún excluido cabe sin conflicto.
function assertMaximal(api, films, scenarios, label) {
  const { screensConflict } = api;
  for (const [i, sc] of scenarios.entries()) {
    for (const exTitle of sc.excluded || []) {
      const screens = films.filter(f => f.title === exTitle && !f.info);
      for (const s of screens) {
        const fits = !sc.schedule.some(p => screensConflict(p, s));
        assert.ok(!fits,
          `${label} esc#${i}: "${exTitle}" (${s.day} ${s.time}) cabía sin conflicto y quedó excluida`);
      }
    }
  }
}

// ── LA PROMESA CENTRAL: maximalidad ──────────────────────────────────────────

test('MAXIMALIDAD: ningún excluido cabía en el plan (caso construido)', () => {
  // F1 10:00 y F2 10:30 chocan; F3 4:00 PM cabe siempre → jamás excluible.
  const films = [
    F('F1', 'MAR 21', '10:00 AM'),
    F('F2', 'MAR 21', '10:30 AM'),
    F('F3', 'MAR 21', '4:00 PM'),
  ];
  const api = loadPlanner({ FILMS: films });
  const scenarios = api.computeScenarios(['F1', 'F2', 'F3']);
  assert.ok(scenarios.length > 0);
  assertMaximal(api, films, scenarios, 'construido');
  for (const sc of scenarios) {
    assert.ok(sc.schedule.some(p => p._title === 'F3' || p.title === 'F3'),
      'F3 (sin conflictos) debe estar en TODO escenario');
  }
});

test('MAXIMALIDAD bajo estrés: 25 configuraciones aleatorias deterministas', () => {
  let seed = 7;
  const rnd = () => (seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648;
  for (let c = 0; c < 25; c++) {
    const n = 3 + Math.floor(rnd() * 3); // 3–5 títulos (bajo el cap de nodos)
    const films = [];
    for (let i = 0; i < n; i++) {
      const day = rnd() > 0.3 ? 'MAR 21' : 'MAR 22';
      const hour = 9 + Math.floor(rnd() * 10);
      const min = rnd() > 0.5 ? '00' : '30';
      const ampm = hour >= 12 ? 'PM' : 'AM';
      const h12 = hour > 12 ? hour - 12 : hour;
      films.push(F('T' + i, day, `${h12}:${min} ${ampm}`,
        { venue: rnd() > 0.5 ? 'Sala A' : 'Sala B', duration: `${60 + Math.floor(rnd() * 60)} min` }));
    }
    const api = loadPlanner({ FILMS: films });
    const titles = films.map(f => f.title);
    const scenarios = api.computeScenarios(titles);
    assert.ok(scenarios.length > 0, `config ${c}: sin escenarios`);
    for (const [i, sc] of scenarios.entries()) {
      // I1: interno sin conflictos
      for (let a = 0; a < sc.schedule.length; a++)
        for (let b = a + 1; b < sc.schedule.length; b++)
          assert.ok(!api.screensConflict(sc.schedule[a], sc.schedule[b]),
            `config ${c} esc#${i}: conflicto interno`);
      // I2: partición exacta
      const inPlan = sc.schedule.map(p => p._title || p.title);
      const both = inPlan.filter(t => (sc.excluded || []).includes(t));
      assert.strictEqual(both.length, 0, `config ${c} esc#${i}: título en plan Y excluido`);
      assert.strictEqual(new Set([...inPlan, ...(sc.excluded || [])]).size, titles.length,
        `config ${c} esc#${i}: partición no cubre la watchlist`);
    }
    // I3: maximalidad en todos los escenarios
    assertMaximal(api, films, scenarios, `config ${c}`);
  }
});

// ── El tiempo: lo pasado no se planea ────────────────────────────────────────

test('funciones pasadas JAMÁS en el plan; si hay otra futura, se usa esa', () => {
  // simTime 2026-06-05T08:00-05:00 → son las 08:00 locales del MAR 21.
  const films = [
    F('Pasada', 'MAR 21', '6:00 AM'),                      // ya pasó
    F('DosFunciones', 'MAR 21', '6:30 AM'),                // pasada…
    F('DosFunciones', 'MAR 21', '5:00 PM'),                // …y futura
  ];
  const api = loadPlanner({ FILMS: films, _simTime: '2026-06-05T13:00:00Z' });
  const scenarios = api.computeScenarios(['Pasada', 'DosFunciones']);
  for (const sc of scenarios) {
    for (const p of sc.schedule) {
      assert.notStrictEqual(p.time, '6:00 AM', 'función pasada en el plan');
      assert.notStrictEqual(p.time, '6:30 AM', 'función pasada en el plan');
    }
  }
  const best = scenarios[0];
  assert.ok(best.schedule.some(p => (p._title || p.title) === 'DosFunciones'),
    'con función futura disponible, el título entra por esa función');
});

// ── Multi-función: el planeador esquiva el conflicto usando la alternativa ───

test('título con 2 funciones (una choca, otra no) → entra por la que no choca', () => {
  const films = [
    F('Fija', 'MAR 21', '10:00 AM'),
    F('Flexible', 'MAR 21', '10:30 AM'),   // choca con Fija
    F('Flexible', 'MAR 21', '6:00 PM'),    // libre
  ];
  const api = loadPlanner({ FILMS: films });
  const scenarios = api.computeScenarios(['Fija', 'Flexible']);
  const best = scenarios[0];
  const inPlan = best.schedule.map(p => p._title || p.title);
  assert.ok(inPlan.includes('Fija') && inPlan.includes('Flexible'),
    'ambos títulos caben usando la función alternativa');
  const flex = best.schedule.find(p => (p._title || p.title) === 'Flexible');
  assert.strictEqual(flex.time, '6:00 PM');
});

// ── Prioridades ──────────────────────────────────────────────────────────────

test('prioridades múltiples compatibles → TODAS en el escenario 0', () => {
  const films = [
    F('P1', 'MAR 21', '10:00 AM'),
    F('P2', 'MAR 21', '2:00 PM'),
    F('Relleno', 'MAR 21', '10:30 AM'),   // choca con P1
  ];
  const api = loadPlanner({ FILMS: films, prioritized: new Set(['P1', 'P2']) });
  const best = api.computeScenarios(['P1', 'P2', 'Relleno'])[0];
  const inPlan = best.schedule.map(p => p._title || p.title);
  assert.ok(inPlan.includes('P1') && inPlan.includes('P2'),
    'las dos prioridades compatibles deben estar en el mejor escenario');
});

test('prioridad inviable (todas sus funciones pasadas) → excluida sin romper', () => {
  const films = [
    F('PrioMuerta', 'MAR 21', '6:00 AM'),
    F('Normal', 'MAR 21', '5:00 PM'),
  ];
  const api = loadPlanner({ FILMS: films, prioritized: new Set(['PrioMuerta']), _simTime: '2026-06-05T13:00:00Z' });
  const scenarios = api.computeScenarios(['PrioMuerta', 'Normal']);
  assert.ok(scenarios.length > 0, 'no debe romper');
  const best = scenarios[0];
  assert.ok(best.schedule.some(p => (p._title || p.title) === 'Normal'));
  assert.ok(!best.schedule.some(p => (p._title || p.title) === 'PrioMuerta'));
});

// ── Availability (ventanas del usuario) ──────────────────────────────────────

test('availability: función dentro de un bloque de NO disponibilidad → no entra al plan', () => {
  const films = [
    F('Temprano', 'MAR 21', '10:00 AM'),
    F('Tarde', 'MAR 21', '8:00 PM'),
  ];
  // Shape real (isScreeningBlocked): blocks = franjas donde el usuario NO puede.
  // Bloqueada la mañana/tarde hasta las 18:00 → solo la función de la noche cabe.
  const api = loadPlanner({ FILMS: films, availability: { 'MAR 21': { blocks: [{ from: '00:00', to: '18:00' }] } } });
  const scenarios = api.computeScenarios(['Temprano', 'Tarde']);
  for (const sc of scenarios) {
    assert.ok(!sc.schedule.some(p => p.time === '10:00 AM'),
      'función fuera de la ventana de disponibilidad en el plan');
  }
  assert.ok(scenarios[0].schedule.some(p => (p._title || p.title) === 'Tarde'));
});

// ── Eventos informativos ─────────────────────────────────────────────────────

test('info:true (drop-in) nunca entra al plan generado', () => {
  const films = [
    F('Expo', 'MAR 21', '10:00 AM', { info: true }),
    F('Peli', 'MAR 21', '2:00 PM'),
  ];
  const api = loadPlanner({ FILMS: films });
  const scenarios = api.computeScenarios(['Expo', 'Peli']);
  for (const sc of scenarios) {
    assert.ok(!sc.schedule.some(p => (p._title || p.title) === 'Expo'),
      'evento informativo dentro del plan');
  }
});
