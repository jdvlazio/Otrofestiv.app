// Una función CANCELADA no puede entrar a un plan.
//
// El aviso se sella en el loader (f._cancelled) y el planeador tiene que
// ignorar esa función como si no existiera: proponerla sería mandar a alguien
// a una sala cerrada. Si el film NO tiene otra función, sale del plan entero.
// Esta era la única rama del camino de avisos sin test (se verificaba a mano).

const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

function loadPlanner(FILMS) {
  return loadDomain({
    globals: {
      FILMS,
      watched: new Set(), prioritized: new Set(), availability: {}, savedAgenda: null,
      FESTIVAL_BUFFER: 15, FESTIVAL_TRANSPORT: 'transit',
      FESTIVAL_CONFIG: { test: { venues: { 'Sala A': { short: 'A', lat: 6.25, lng: -75.57 } } } },
      _activeFestId: 'test', DEFAULT_DURATION_MIN: 90,
      _simTime: '2026-06-05T08:00:00Z', FESTIVAL_END: new Date('2099-01-01'),
      FESTIVAL_DATES: { 'MAR 21': '2026-06-05' }, TZ_OFFSET: '-05:00',
    },
  });
}

const scr = (title, time, extra) => Object.assign(
  { title, day: 'MAR 21', time, duration: '90 min', venue: 'Sala A', section: 'S' }, extra);

test('la función cancelada no se propone: el plan toma la otra función del film', () => {
  const { computeScenarios } = loadPlanner([
    scr('F1', '10:00 AM', { _cancelled: true }),
    scr('F1', '4:00 PM'),
  ]);
  const scenarios = computeScenarios(['F1']);
  assert.ok(scenarios.length > 0, 'debería planear con la función viva');
  scenarios.forEach(sc => sc.schedule.forEach(s => {
    assert.notStrictEqual(s.time, '10:00 AM', 'propuso la función cancelada');
  }));
});

test('si TODAS sus funciones están canceladas, el film no entra al plan', () => {
  const { computeScenarios } = loadPlanner([
    scr('F1', '10:00 AM', { _cancelled: true }),
    scr('F1', '4:00 PM', { _cancelled: true }),
    scr('F2', '2:00 PM'),
  ]);
  computeScenarios(['F1', 'F2']).forEach(sc => sc.schedule.forEach(s => {
    assert.notStrictEqual(s._title || s.title, 'F1', 'metió al plan un film sin funciones vivas');
  }));
});
