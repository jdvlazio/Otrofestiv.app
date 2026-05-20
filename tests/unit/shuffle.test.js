// Unit tests for shuffle — extracted from index.html via load-domain.
// Contract: Fisher-Yates. NO muta input — clona con [...arr] y retorna el clon.
// Pura cuando se pasa `rand`. Impure con Math.random (default).

const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

test('preserves length', () => {
  const { shuffle } = loadDomain();
  assert.strictEqual(shuffle([1, 2, 3, 4, 5]).length, 5);
});

test('with seeded rand produces deterministic output (same seed → same shuffle)', () => {
  const { shuffle, _mulberry32 } = loadDomain();
  const a = shuffle([1, 2, 3, 4, 5], _mulberry32(42));
  const b = shuffle([1, 2, 3, 4, 5], _mulberry32(42));
  assert.deepStrictEqual(a, b);
});

test('does not mutate input array', () => {
  const { shuffle } = loadDomain();
  const input = [1, 2, 3, 4, 5];
  const before = [...input];
  shuffle(input);
  assert.deepStrictEqual(input, before);
});
