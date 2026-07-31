// verifyPlan — el certificador del plan (patrón certifying algorithms).
// No re-implementa las reglas: usa el screensConflict de producción como única
// fuente de factibilidad y certifica el RESULTADO. Consumidores: el oráculo del
// planeador (CI, falla duro) y el chokepoint de escritura (PR 2).
const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

function load(passed = new Set()) {
  return loadDomain({
    functions: ['toMin', 'parseDur', 'blockDuration', 'durationForTravel', 'effectiveDuration',
                '_resolveVenue', 'venueTravelMins', 'travelMins', 'screensConflict', 'verifyPlan'],
    globals: {
      DEFAULT_DURATION_MIN: 90, FESTIVAL_BUFFER: 15, FESTIVAL_TRANSPORT: 'transit',
      FESTIVAL_CONFIG: { test: { venues: { A: { short: 'A', lat: 6.2, lng: -75.5 } } } },
      _activeFestId: 'test',
      screeningPassed: s => passed.has(s._title),
    },
  });
}
const e = (t, time, extra) => Object.assign({ _title: t, title: t, day: 'D1', time, venue: 'A', duration: '90 min' }, extra);

test('plan limpio certifica ok', () => {
  const { verifyPlan } = load();
  const r = verifyPlan([e('F1', '10:00'), e('F2', '14:00')]);
  assert.strictEqual(r.ok, true);
  assert.deepStrictEqual(r.violations, []);
});

test('conflicto real se certifica como violación', () => {
  const { verifyPlan } = load();
  const r = verifyPlan([e('F1', '10:00'), e('F2', '10:30')]);
  assert.strictEqual(r.ok, false);
  assert.strictEqual(r.violations[0].kind, 'conflicto');
});

test('_squeezed es violación DELIBERADA — no genera falso rojo', () => {
  const { verifyPlan } = load();
  const r = verifyPlan([e('F1', '10:00'), e('F2', '10:30', { _squeezed: true })]);
  assert.strictEqual(r.ok, true);
});

test('cancelada y duplicado se certifican', () => {
  const { verifyPlan } = load();
  const r = verifyPlan([e('F1', '10:00', { _cancelled: true }), e('F1', '18:00')]);
  assert.deepStrictEqual(r.violations.map(v => v.kind).sort(), ['cancelada', 'duplicado']);
});

test('is_recurring repetido NO es duplicado (taller multi-día, todas las sesiones)', () => {
  const { verifyPlan } = load();
  const r = verifyPlan([
    e('Taller', '14:00', { is_recurring: true }),
    Object.assign(e('Taller', '14:00', { is_recurring: true }), { day: 'D2' }),
  ]);
  assert.strictEqual(r.ok, true);
});

test('pasada solo con checkPassed (opt-in del oráculo)', () => {
  const { verifyPlan } = load(new Set(['F1']));
  assert.strictEqual(verifyPlan([e('F1', '10:00')]).ok, true);
  assert.strictEqual(verifyPlan([e('F1', '10:00')], { checkPassed: true }).ok, false);
});
