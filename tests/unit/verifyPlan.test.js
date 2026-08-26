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
                '_resolveVenue', 'venueTravelMins', 'travelMins', 'screensConflict', 'verifyPlan',
                'sameEntry'],
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

test('cancelada se certifica (y el título repetido en OTRA función, no)', () => {
  const { verifyPlan } = load();
  // Doctrina 26 ago 2026: `duplicado` es por IDENTIDAD DE ENTRADA, no por título.
  // La misma obra en dos funciones distintas es un plan legítimo — el usuario
  // puede pedirlo. Acá la única violación es la cancelada.
  const r = verifyPlan([e('F1', '10:00', { _cancelled: true }), e('F1', '18:00')]);
  assert.deepStrictEqual(r.violations.map(v => v.kind).sort(), ['cancelada']);
});

test('la MISMA función dos veces SÍ es duplicado (corrupción real)', () => {
  const { verifyPlan } = load();
  const r = verifyPlan([e('F1', '10:00'), e('F1', '10:00')]);
  const dup = r.violations.filter(v => v.kind === 'duplicado');
  assert.strictEqual(dup.length, 1, 'una sola violación, sin eco de conflicto-consigo-misma');
  assert.strictEqual(dup[0].day, 'D1');
  assert.strictEqual(dup[0].time, '10:00');
  // y NO se reporta además como conflicto: el eco enmascaraba el hallazgo real
  assert.ok(!r.violations.some(v => v.kind === 'conflicto'));
});

test('misma obra, mismo día y hora, SEDES distintas → conflicto, no duplicado', () => {
  const { verifyPlan } = load();
  // No es la misma entrada (la sede es parte de la identidad desde #751): es un
  // imposible físico, y el kind correcto lo dice.
  const r = verifyPlan([e('F1', '10:00'), e('F1', '10:00', { venue: 'B' })]);
  assert.ok(!r.violations.some(v => v.kind === 'duplicado'));
  assert.ok(r.violations.some(v => v.kind === 'conflicto'));
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
