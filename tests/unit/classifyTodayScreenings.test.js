// Unit tests for _classifyTodayScreenings — extracted from index.html.
// Contract: particiona funciones del día en done / active / future según
// su relación con nowMin (minutos del día). Lee DEFAULT_DURATION_MIN como
// fallback para screenings sin duration (o con duration no parseable por
// parseInt — ver nota del contrato).

const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

const { _classifyTodayScreenings } = loadDomain({
  globals: { DEFAULT_DURATION_MIN: 90 },
});

test('empty array → empty done/active/future', () => {
  assert.deepStrictEqual(
    _classifyTodayScreenings([], 600),
    { done: [], active: [], future: [] }
  );
});

test('all 3 screenings already past → all done', () => {
  const screenings = [
    { time: '9:00 AM', duration: '60 min' },   // 540–600
    { time: '10:00 AM', duration: '60 min' },  // 600–660
    { time: '11:00 AM', duration: '60 min' },  // 660–720
  ];
  const r = _classifyTodayScreenings(screenings, 800); // 1:20 PM in min
  assert.strictEqual(r.done.length, 3);
  assert.strictEqual(r.active.length, 0);
  assert.strictEqual(r.future.length, 0);
});

test('mix of done/active/future correctly partitioned', () => {
  const screenings = [
    { time: '9:00 AM', duration: '60 min' },    // 540–600  done at 700
    { time: '10:30 AM', duration: '90 min' },   // 630–720  active at 700
    { time: '1:00 PM', duration: '90 min' },    // 780–870  future at 700
  ];
  const r = _classifyTodayScreenings(screenings, 700); // 11:40 AM
  assert.strictEqual(r.done.length, 1);
  assert.strictEqual(r.active.length, 1);
  assert.strictEqual(r.future.length, 1);
  assert.strictEqual(r.done[0].time, '9:00 AM');
  assert.strictEqual(r.active[0].time, '10:30 AM');
  assert.strictEqual(r.future[0].time, '1:00 PM');
});

test('screening ending exactly at nowMin → done (not active)', () => {
  // 10:00 AM (600) + 90 min = ends at 690 (11:30 AM). nowMin = 690.
  // done check:   600+90<=690 → 690<=690 → true → done.
  // active check: 600<=690 && 690>690 → false → not active.
  const screenings = [{ time: '10:00 AM', duration: '90 min' }];
  const r = _classifyTodayScreenings(screenings, 690);
  assert.strictEqual(r.done.length, 1);
  assert.strictEqual(r.active.length, 0);
  assert.strictEqual(r.future.length, 0);
});

test('screening with undefined duration falls back to DEFAULT_DURATION_MIN', () => {
  // No `duration` field → parseInt(undefined) = NaN → falls back to 90.
  // 10:00 (600) + default 90 = 690. nowMin=650 → active (600<=650 && 690>650).
  const screenings = [{ time: '10:00 AM' }];
  const r = _classifyTodayScreenings(screenings, 650);
  assert.strictEqual(r.active.length, 1, 'should be active using DEFAULT_DURATION_MIN fallback');
  assert.strictEqual(r.done.length, 0);
  assert.strictEqual(r.future.length, 0);
});
