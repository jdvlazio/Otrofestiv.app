// Unit tests for screeningPassed — extracted from index.html via load-domain.
// Contract: true si simNow() > _festDate(dateStr, s.time) + 10 min grace.
// Gate: si festivalEnded() → false (post-festival, nada se marca como pasado).
//
// _festDate('2026-06-05', '10:00') con TZ_OFFSET='-05:00' → 10:00 Colombia
// = 15:00 UTC. Grace de 10 min → 15:10 UTC. _simTime usa Z-suffix para que
// la comparación con screeningTime (absolute) sea TZ-independent.

const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

function load(opts) {
  return loadDomain({
    globals: {
      _simTime: opts._simTime,
      FESTIVAL_END: opts.FESTIVAL_END || new Date('2099-01-01'),
      FESTIVAL_DATES: opts.FESTIVAL_DATES || { 'MAR 21': '2026-06-05' },
      TZ_OFFSET: '-05:00',
    },
  });
}

test('festivalEnded=true → false (gate)', () => {
  const { screeningPassed } = load({
    _simTime: '2027-01-01T00:00:00Z',
    FESTIVAL_END: new Date('2026-06-14T00:00:00Z'),
  });
  assert.strictEqual(screeningPassed({ day: 'MAR 21', time: '14:00' }), false);
});

test('s.day not in FESTIVAL_DATES → false', () => {
  const { screeningPassed } = load({ _simTime: '2026-06-05T20:00:00Z' });
  assert.strictEqual(screeningPassed({ day: 'UNKNOWN_DAY', time: '10:00' }), false);
});

test('simNow > screeningTime + 10min grace → true', () => {
  // screeningTime: 10:00 Colombia = 15:00 UTC; grace → 15:10 UTC
  // simNow: 16:00 UTC → after grace → true
  const { screeningPassed } = load({ _simTime: '2026-06-05T16:00:00Z' });
  assert.strictEqual(screeningPassed({ day: 'MAR 21', time: '10:00' }), true);
});

test('simNow < screeningTime + 10min grace → false', () => {
  // screeningTime: 15:00 UTC; grace → 15:10 UTC
  // simNow: 15:05 UTC → before grace → false
  const { screeningPassed } = load({ _simTime: '2026-06-05T15:05:00Z' });
  assert.strictEqual(screeningPassed({ day: 'MAR 21', time: '10:00' }), false);
});

test('simNow exactly at screeningTime + 10min grace → false (strict >)', () => {
  // simNow exactly 15:10 UTC → not strictly greater → false
  const { screeningPassed } = load({ _simTime: '2026-06-05T15:10:00Z' });
  assert.strictEqual(screeningPassed({ day: 'MAR 21', time: '10:00' }), false);
});
