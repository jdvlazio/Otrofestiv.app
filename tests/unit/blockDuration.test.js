// Unit tests for blockDuration — la duración de la FUNCIÓN a la que entra el
// espectador. Con anclaje (dos obras en un mismo slot) es la suma de las obras,
// que el loader sella en `_slotDur`; sin anclaje, la duración de la obra.
// SIN el Q&A: quedarse es opcional, y por eso existe su aviso. El par es
// effectiveDuration = blockDuration + Q&A, que es la que usan los conflictos.
//
// De dónde sale: ocho superficies calculaban el fin de la función con
// parseDur(f.duration) por su cuenta y ninguna sabía de anclaje. Un corto de
// 5 min dentro de una función de 111 declaraba libre un hueco inexistente y se
// marcaba "terminado" mientras la función seguía. (30 jul 2026)

const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

const { blockDuration, effectiveDuration } = loadDomain({
  globals: { DEFAULT_DURATION_MIN: 90 },
});

test('sin anclaje → la duración de la obra', () => {
  assert.strictEqual(blockDuration({ duration: '90 min' }), 90);
});

test('sin anclaje NO suma el Q&A (eso es effectiveDuration)', () => {
  assert.strictEqual(blockDuration({ duration: '90 min', has_qa: true }), 90);
  assert.strictEqual(effectiveDuration({ duration: '90 min', has_qa: true }), 120);
});

test('con anclaje → la suma del slot, no la obra', () => {
  // el caso real de FINCA: Propiedad privada (106) + Mi casa es su casa (5)
  const corto = { duration: '5 min', _slotDur: 111, _slotMin: 141, has_qa: false };
  assert.strictEqual(blockDuration(corto), 111);
});

test('con anclaje, el Q&A queda fuera del bloque pero dentro de effectiveDuration', () => {
  const largo = { duration: '106 min', _slotDur: 111, _slotMin: 141, has_qa: true };
  assert.strictEqual(blockDuration(largo), 111);
  assert.strictEqual(effectiveDuration(largo), 141);
});

test('sin duración → cae al default', () => {
  assert.strictEqual(blockDuration({}), 90);
});
