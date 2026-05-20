// Unit tests for festivalEnded — extracted from index.html via load-domain.
// Contract: simNow() > FESTIVAL_END (strict). Z-suffixed timestamps para
// que la comparación sea TZ-independent entre runners.

const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

test('_simTime before FESTIVAL_END → false', () => {
  const { festivalEnded } = loadDomain({
    globals: {
      _simTime: '2026-06-05T14:00:00Z',
      FESTIVAL_END: new Date('2026-06-14T00:00:00Z'),
    },
  });
  assert.strictEqual(festivalEnded(), false);
});

test('_simTime after FESTIVAL_END → true', () => {
  const { festivalEnded } = loadDomain({
    globals: {
      _simTime: '2026-06-20T10:00:00Z',
      FESTIVAL_END: new Date('2026-06-14T00:00:00Z'),
    },
  });
  assert.strictEqual(festivalEnded(), true);
});

test('_simTime exactly FESTIVAL_END → false (strict >)', () => {
  const ts = '2026-06-14T00:00:00Z';
  const { festivalEnded } = loadDomain({
    globals: { _simTime: ts, FESTIVAL_END: new Date(ts) },
  });
  assert.strictEqual(festivalEnded(), false);
});
