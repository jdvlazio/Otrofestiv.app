// Unit tests for simTodayStr — extracted from index.html via load-domain.
// Contract (TZ-anchored): YYYY-MM-DD del día EN HORA DEL FESTIVAL (TZ_OFFSET),
// no del dispositivo. simTodayStr usa _festNow() = simNow() desplazado por
// TZ_OFFSET, leído con getUTC* → el día local del festival, idéntico en cualquier
// runner. Tests usan _simTime con sufijo de TZ (instante absoluto) + TZ_OFFSET
// explícito → deterministas e independientes del TZ del runner (Colombia/UTC/CI).

const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

test('hora del festival, no del runner: NYC jun7 19:30 EDT → 2026-06-07', () => {
  const { simTodayStr } = loadDomain({ globals: { _simTime: '2026-06-07T19:30:00-04:00', TZ_OFFSET: '-04:00' } });
  assert.strictEqual(simTodayStr(), '2026-06-07');
});

test('borde de medianoche: NYC jun8 00:30 EDT → 2026-06-08 (no jun7 del dispositivo)', () => {
  // Un dispositivo en Colombia (UTC-5) marcaría jun7 23:30 → día equivocado; anclado al
  // festival (-04:00) el día correcto es jun8. Este es el bug que el fix corrige.
  const { simTodayStr } = loadDomain({ globals: { _simTime: '2026-06-08T00:30:00-04:00', TZ_OFFSET: '-04:00' } });
  assert.strictEqual(simTodayStr(), '2026-06-08');
});

test('festival en Colombia (-05:00): instante absoluto → día en hora del festival', () => {
  const { simTodayStr } = loadDomain({ globals: { _simTime: '2026-05-14T12:00:00-05:00', TZ_OFFSET: '-05:00' } });
  assert.strictEqual(simTodayStr(), '2026-05-14');
});

test('mismo instante absoluto → mismo día festival sin importar TZ_OFFSET del runner', () => {
  // 2026-06-07T23:30:00Z = NYC 19:30 EDT. Con TZ_OFFSET=-04:00 → jun7.
  const { simTodayStr } = loadDomain({ globals: { _simTime: '2026-06-07T23:30:00Z', TZ_OFFSET: '-04:00' } });
  assert.strictEqual(simTodayStr(), '2026-06-07');
});
