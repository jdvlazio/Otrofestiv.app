// planCiudad.test.js — el planificador NO cruza ciudades (QA de ojos frescos,
// 15 ago 2026): con filtro Bogotá, «Calcular mi Plan» armaba el domingo en
// Medellín y el lunes en Ibagué sin avisar. La restricción vive en UN punto
// (plannableScreens lee PLAN_CITY_VENUES) y las sugerencias comparten predicado.
const { test } = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

const F = (t, day, time, venue) => ({ title: t, day, time, venue, duration: '90 min' });
const FILMS = [
  F('Peli A', 'D1', '10:00', 'Cinemateca BOG'),
  F('Peli A', 'D1', '14:00', 'Colombo MED'),     // la misma obra, otra ciudad
  F('Peli B', 'D1', '16:00', 'Colombo MED'),      // solo en la otra ciudad
];

function load(planVenues) {
  return loadDomain({
    functions: ['plannableScreens'],
    globals: {
      FILMS,
      DEFAULT_DURATION_MIN: 90,
      DAY_KEYS: ['D1'],
      availability: {},
      FESTIVAL_DATES: { D1: '2099-01-01' },   // futuro: nada ha pasado
      TZ_OFFSET: '-05:00',
      _simTime: null,
      isScreeningBlocked: () => false,
      screeningPassed: () => false,
      PLAN_CITY_VENUES: planVenues,           // null = sin restricción
    },
  });
}

test('sin filtro: todas las funciones de la obra son plannables', () => {
  const d = load(null);
  assert.strictEqual(d.plannableScreens('Peli A').length, 2);
  assert.strictEqual(d.plannableScreens('Peli B').length, 1);
});

test('con filtro de ciudad: SOLO las funciones de esa ciudad', () => {
  const d = load(new Set(['Cinemateca BOG']));
  const a = d.plannableScreens('Peli A');
  assert.strictEqual(a.length, 1, 'Peli A: solo la función de Bogotá');
  assert.strictEqual(a[0].venue, 'Cinemateca BOG');
  // El caso que dolió: una obra que SOLO existe fuera del filtro no entra al
  // plan — antes entraba y el plan te mandaba a Medellín sin avisar.
  assert.strictEqual(d.plannableScreens('Peli B').length, 0);
});

test('una función SIN venue nunca queda atrapada por el filtro', () => {
  const d = load(new Set(['Cinemateca BOG']));
  const films2 = FILMS.concat([{ title: 'Peli C', day: 'D1', time: '18:00', duration: '60 min' }]);
  const d2 = loadDomain({
    functions: ['plannableScreens'],
    globals: { FILMS: films2, DEFAULT_DURATION_MIN: 90, DAY_KEYS: ['D1'], availability: {},
      FESTIVAL_DATES: { D1: '2099-01-01' }, TZ_OFFSET: '-05:00', _simTime: null,
      isScreeningBlocked: () => false, screeningPassed: () => false,
      PLAN_CITY_VENUES: new Set(['Cinemateca BOG']) },
  });
  assert.strictEqual(d2.plannableScreens('Peli C').length, 1, 'sin venue → no se filtra');
  void d;
});

// ── verifyPlan: la RED, no solo el camino feliz ─────────────────────────────
// El 16 ago 2026 el plan volvió a cruzar ciudades pese a que plannableScreens
// filtraba bien: `squeezeExcluded` reinsertaba las excluidas al GUARDAR, con su
// propia copia del predicado, y verifyPlan no miraba la ciudad. Estos dos tests
// cubren la red: quien sea que inserte, el verificador lo caza.
function loadVerify(planVenues) {
  return loadDomain({
    functions: ['verifyPlan', 'screensConflict', 'screeningPassed', 'toMin', 'parseDur', 'blockDuration', 'effectiveDuration', 'durationForTravel'],
    globals: {
      FILMS, DEFAULT_DURATION_MIN: 90, DAY_KEYS: ['D1'],
      FESTIVAL_DATES: { D1: '2099-01-01' }, TZ_OFFSET: '-05:00', _simTime: null,
      FESTIVAL_BUFFER: 15, FESTIVAL_CONFIG: {}, _activeFestId: 'x',
      availability: {}, travelMins: () => 0, festivalEnded: () => false,
      PLAN_CITY_VENUES: planVenues,
    },
  });
}

test('verifyPlan: una función de otra ciudad es violación «ciudad-fuera»', () => {
  const D = loadVerify(new Set(['Cinemateca BOG']));
  const r = D.verifyPlan([
    { _title: 'Peli A', day: 'D1', time: '10:00', venue: 'Cinemateca BOG', duration: '90 min' },
    { _title: 'Peli B', day: 'D1', time: '16:00', venue: 'Colombo MED', duration: '90 min', _squeezed: true },
  ]);
  assert.equal(r.ok, false);
  const ciudad = r.violations.filter(v => v.kind === 'ciudad-fuera');
  assert.equal(ciudad.length, 1);                 // solo la de la otra ciudad
  assert.equal(ciudad[0].title, 'Peli B');
  assert.equal(ciudad[0].venue, 'Colombo MED');   // _squeezed NO la exime
});

test('verifyPlan: sin restricción de ciudad no inventa violaciones', () => {
  const D = loadVerify(null);
  const r = D.verifyPlan([
    { _title: 'Peli A', day: 'D1', time: '10:00', venue: 'Cinemateca BOG', duration: '90 min' },
    { _title: 'Peli B', day: 'D1', time: '16:00', venue: 'Colombo MED', duration: '90 min' },
  ]);
  assert.equal(r.violations.filter(v => v.kind === 'ciudad-fuera').length, 0);
});
