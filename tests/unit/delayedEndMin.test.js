// delayedEndMin — el fin de una función CON su retraso reportado (dueño único).
// El delay se sumaba a mano en 2 sitios de la vista de "en curso" (Mi Plan):
// el "termina en X min" y el warning de margen hacia la siguiente función.
const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

function load(delays = {}) {
  return loadDomain({
    functions: ['toMin', 'parseDur', 'blockDuration', 'effectiveDuration', 'durationForTravel', '_delayKey', 'delayedEndMin'],
    globals: { DEFAULT_DURATION_MIN: 90, filmDelays: delays },
  });
}
const f = { _title: 'F1', day: 'D1', time: '18:00', duration: '80 min', has_qa: true };

test('sin travel: fin de bloque + delay (sin Q&A)', () => {
  const { delayedEndMin } = load({ 'F1|D1|18:00': 20 });
  assert.strictEqual(delayedEndMin(f), 18 * 60 + 80 + 20);
});

test('con travel: doctrina del Q&A + delay', () => {
  const { delayedEndMin } = load({ 'F1|D1|18:00': 20 });
  assert.strictEqual(delayedEndMin(f, 12), 18 * 60 + 80 + 30 + 20);
  assert.strictEqual(delayedEndMin(f, 0), 18 * 60 + 80 + 20); // misma sede: sin Q&A
});

test('sin delay reportado: igual al fin canónico', () => {
  const { delayedEndMin } = load();
  assert.strictEqual(delayedEndMin(f), 18 * 60 + 80);
});

test('anclaje: el delay se suma al fin del BLOQUE, no al de la obra', () => {
  const anclada = { _title: 'C', day: 'D1', time: '18:00', duration: '5 min', _slotDur: 111, _slotMin: 141 };
  const { delayedEndMin } = load({ 'C|D1|18:00': 10 });
  assert.strictEqual(delayedEndMin(anclada), 18 * 60 + 111 + 10);
});
