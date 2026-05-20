// Unit tests for _djb2 — extracted from index.html via load-domain.
// Contract: hash xor-shift de Bernstein con initial seed 5381.

const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

test('empty string returns initial seed (5381)', () => {
  const { _djb2 } = loadDomain();
  assert.strictEqual(_djb2(''), 5381);
});

test('same input produces same hash (determinism)', () => {
  const { _djb2 } = loadDomain();
  assert.strictEqual(_djb2('hello'), _djb2('hello'));
  // Different inputs should produce different hashes (no collision for short distinct strings)
  assert.notStrictEqual(_djb2('hello'), _djb2('world'));
});
