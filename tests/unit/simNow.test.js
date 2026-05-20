// Unit tests for simNow — extracted from index.html via load-domain.
// Contract: Date de "ahora" controlable vía _simTime (null = tiempo real).

const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

test('_simTime null → returns Date close to Date.now()', () => {
  const { simNow } = loadDomain({ globals: { _simTime: null } });
  const before = Date.now();
  const result = simNow().getTime();
  const after = Date.now();
  assert.ok(result >= before && result <= after,
    `simNow() should be in [${before}, ${after}], got ${result}`);
});

test('_simTime as Z-suffixed ISO → returns Date for that absolute time', () => {
  const { simNow } = loadDomain({ globals: { _simTime: '2026-06-05T14:30:00Z' } });
  assert.strictEqual(simNow().toISOString(), '2026-06-05T14:30:00.000Z');
});

test('idempotency: two calls with same _simTime produce equal timestamps', () => {
  const { simNow } = loadDomain({ globals: { _simTime: '2026-06-05T14:30:00Z' } });
  assert.strictEqual(simNow().getTime(), simNow().getTime());
});
