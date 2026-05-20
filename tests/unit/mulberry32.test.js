// Unit tests for _mulberry32 — extracted from index.html via load-domain.
// Contract: PRNG factory. Mismo seed → misma secuencia. Output en [0, 1).

const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

test('same seed produces same sequence', () => {
  const { _mulberry32 } = loadDomain();
  const a = _mulberry32(42);
  const b = _mulberry32(42);
  for (let i = 0; i < 5; i++) {
    assert.strictEqual(a(), b(), `value ${i} should match between sequences`);
  }
});

test('output always in [0, 1) for 10 calls', () => {
  const { _mulberry32 } = loadDomain();
  const rng = _mulberry32(123);
  for (let i = 0; i < 10; i++) {
    const v = rng();
    assert.ok(v >= 0 && v < 1, `value ${v} not in [0, 1)`);
  }
});
