// Unit tests for _titleSeed — extracted from index.html via load-domain.
// Contract: hash determinístico order-independent sobre el set de titles.

const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

test('order-independent: ["B","A"] same seed as ["A","B"]', () => {
  const { _titleSeed } = loadDomain();
  assert.strictEqual(_titleSeed(['B', 'A']), _titleSeed(['A', 'B']));
});

test('same titles produce same seed (determinism)', () => {
  const { _titleSeed } = loadDomain();
  const titles = ['Belén', 'Tár', 'Aftersun'];
  assert.strictEqual(_titleSeed(titles), _titleSeed(titles));
  // Different set produces different seed
  assert.notStrictEqual(_titleSeed(titles), _titleSeed(['Otra', 'Película']));
});
