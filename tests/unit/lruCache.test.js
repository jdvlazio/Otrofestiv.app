// Unit test — _lruTouch (src/controller/loader.js), la decisión PURA del LRU del
// cache de festivales en memoria.
//
// POR QUÉ EXISTE: sin cota, un usuario que recorre muchos festivales en una sesión
// acumula ~80KB de JSON por festival sin límite. El LRU mantiene hasta CAP cacheados
// y evicta el menos-usado, sin evictar el activo. Este test congela esa lógica.

const { test, before } = require('node:test');
const assert = require('node:assert');

let lruTouch;
before(async () => { lruTouch = (await import('../../src/lru.js')).lruTouch; });

test('_lruTouch — mueve id a MRU (final) sin duplicar', () => {
  const r = lruTouch(['a', 'b', 'c'], 'b', 8);
  assert.deepStrictEqual(r.order, ['a', 'c', 'b'], 'b va al final (MRU)');
  assert.deepStrictEqual(r.evict, [], 'bajo el cap → nada se evicta');
});

test('_lruTouch — id nuevo se agrega al final', () => {
  const r = lruTouch(['a', 'b'], 'c', 8);
  assert.deepStrictEqual(r.order, ['a', 'b', 'c']);
  assert.deepStrictEqual(r.evict, []);
});

test('_lruTouch — al exceder el cap evicta el MENOS usado (LRU)', () => {
  const order = ['f1', 'f2', 'f3']; // cap 3, lleno
  const r = lruTouch(order, 'f4', 3); // entra f4
  assert.deepStrictEqual(r.evict, ['f1'], 'evicta el más viejo');
  assert.deepStrictEqual(r.order, ['f2', 'f3', 'f4'], 'quedan los 3 más recientes');
});

test('_lruTouch — el id recién tocado NUNCA se evicta', () => {
  // tocar un id que ya está y está lleno: no debe evictarlo a sí mismo
  const r = lruTouch(['a', 'b', 'c'], 'a', 3);
  assert.deepStrictEqual(r.order, ['b', 'c', 'a'], 'a a MRU');
  assert.deepStrictEqual(r.evict, [], 'no excede el cap → nada evicta');
  // y con cap 1: tocar 'b' evicta todo lo demás, nunca 'b'
  const r2 = lruTouch(['a', 'x', 'y'], 'b', 1);
  assert.ok(!r2.evict.includes('b'), 'b (activo) nunca evictado');
  assert.deepStrictEqual(r2.order, ['b'], 'queda solo el activo');
});

test('_lruTouch — evicta múltiples si el orden venía sobre el cap', () => {
  const r = lruTouch(['a', 'b', 'c', 'd'], 'e', 3); // 5 → cap 3 → evict 2
  assert.deepStrictEqual(r.evict, ['a', 'b']);
  assert.deepStrictEqual(r.order, ['c', 'd', 'e']);
});
