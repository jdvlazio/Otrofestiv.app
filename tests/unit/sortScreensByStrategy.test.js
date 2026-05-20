// Unit tests for sortScreensByStrategy — extracted from index.html via load-domain.
// Contract: interval scheduling. Criterio: 1) fewest-conflicts contra
// screenings de otros grupos primero; 2) tiebreak por earliest-finish-time.

const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

function setup() {
  return loadDomain({
    globals: {
      FESTIVAL_BUFFER: 15,
      FESTIVAL_TRANSPORT: 'transit',
      FESTIVAL_CONFIG: {
        test: { venues: { 'Sala A': { short: 'A', lat: 6.25, lng: -75.57 } } },
      },
      _activeFestId: 'test',
      DEFAULT_DURATION_MIN: 90,
    },
  });
}

test('screen with fewer conflicts comes first', () => {
  const { sortScreensByStrategy } = setup();
  // a: 10:00 AM, 90 min, same venue as x and y (overlapping times → conflicts with both)
  // b: 2:00 PM, 90 min, separate from x and y (zero conflicts)
  const a = { day: 'D', time: '10:00 AM', duration: '90 min', venue: 'Sala A' };
  const b = { day: 'D', time: '2:00 PM', duration: '90 min', venue: 'Sala A' };
  const x = { day: 'D', time: '10:30 AM', duration: '90 min', venue: 'Sala A' };
  const y = { day: 'D', time: '11:00 AM', duration: '90 min', venue: 'Sala A' };
  const result = sortScreensByStrategy([a, b], [{ screens: [x, y] }]);
  // a conflicts with both x and y; b conflicts with neither → b first.
  assert.strictEqual(result[0], b);
  assert.strictEqual(result[1], a);
});

test('tiebreak: same conflict count, earlier finish wins (EFT)', () => {
  const { sortScreensByStrategy } = setup();
  // a: 10:00 AM, 60 min → ends 11:00 AM
  // b: 10:00 AM, 90 min → ends 11:30 AM
  // No other groups → both 0 conflicts → tiebreak by EFT → a first.
  const a = { day: 'D', time: '10:00 AM', duration: '60 min', venue: 'Sala A' };
  const b = { day: 'D', time: '10:00 AM', duration: '90 min', venue: 'Sala A' };
  const result = sortScreensByStrategy([b, a], []); // input b before a
  assert.strictEqual(result[0], a);
  assert.strictEqual(result[1], b);
});

test('single screen returned unchanged', () => {
  const { sortScreensByStrategy } = setup();
  const a = { day: 'D', time: '10:00 AM', duration: '90 min', venue: 'Sala A' };
  const result = sortScreensByStrategy([a], []);
  assert.strictEqual(result.length, 1);
  assert.strictEqual(result[0], a);
});

test('idempotency: sorting twice produces same result', () => {
  const { sortScreensByStrategy } = setup();
  const a = { day: 'D', time: '10:00 AM', duration: '60 min', venue: 'Sala A' };
  const b = { day: 'D', time: '2:00 PM', duration: '90 min', venue: 'Sala A' };
  const x = { day: 'D', time: '10:30 AM', duration: '90 min', venue: 'Sala A' };
  const r1 = sortScreensByStrategy([a, b], [{ screens: [x] }]);
  const r2 = sortScreensByStrategy(r1, [{ screens: [x] }]);
  assert.deepStrictEqual(r1, r2);
});
