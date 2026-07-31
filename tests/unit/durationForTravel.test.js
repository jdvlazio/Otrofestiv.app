// durationForTravel — la doctrina del Q&A tiene UN dueño (domain/film.js).
// travel>0 → el Q&A compromete (effectiveDuration); misma sede → el fin duro es
// el bloque (blockDuration) y el Q&A queda como advertencia. Antes la decisión
// vivía inline en screensConflict/Reason y re-escrita en la vista de delays.
const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

const { durationForTravel } = loadDomain({
  functions: ['parseDur', 'blockDuration', 'effectiveDuration', 'durationForTravel'],
  globals: { DEFAULT_DURATION_MIN: 90 },
});

const f = { duration: '80 min', has_qa: true };
const anclada = { duration: '5 min', has_qa: false, _slotDur: 111, _slotMin: 141 };

test('con traslado el Q&A compromete: fin = effective', () => {
  assert.strictEqual(durationForTravel(f, 12), 110);   // 80 + 30
  assert.strictEqual(durationForTravel(anclada, 12), 141);
});

test('misma sede: el fin duro es el bloque, sin Q&A', () => {
  assert.strictEqual(durationForTravel(f, 0), 80);
  assert.strictEqual(durationForTravel(anclada, 0), 111);
});
