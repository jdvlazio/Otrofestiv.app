// expandVentanas — la actividad ABIERTA de VARIOS días (21 oct 2026, Juan).
// «Una vez en un cuerpo: Habitar la imagen» (Anibia) es UNA exposición del 22 oct
// al 13 nov, de 8:00 a 17:00. Se cargaba como 9 funciones con is_recurring y la
// ficha la pintaba como un taller de 9 sesiones. El dato trae UNA función info con
// `day` + `hasta`; la carga la abre en una copia por día del festival, cada una con
// `_ventana`, sin is_recurring y con el código una sola vez.

const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');
const { expandVentanas } = loadDomain({ functions: ['expandVentanas'] });

const DK = ['2026-10-22', '2026-10-23', '2026-10-24', '2026-11-01'];
const expo = { title: 'Expo', type: 'event', info: true, day: '2026-10-23', hasta: '2026-11-13',
  time: '08:00', duration: '540 min', id: 'f_X', is_recurring: true };

test('una copia por día del festival dentro de la ventana, con _ventana', () => {
  const r = expandVentanas([expo], DK);
  assert.deepStrictEqual(r.map(f => f.day), ['2026-10-23', '2026-10-24', '2026-11-01']);
  assert.deepStrictEqual(r.map(f => f.day_order), [1, 2, 3]);
  r.forEach(f => assert.deepStrictEqual(f._ventana, { desde: '2026-10-23', hasta: '2026-11-13' }));
});

test('sin is_recurring (no es un taller de sesiones) y el código una sola vez', () => {
  const r = expandVentanas([expo], DK);
  assert.ok(r.every(f => !f.is_recurring));
  assert.deepStrictEqual(r.map(f => f.id || null), ['f_X', null, null]);
});

test('lo que no es abierta con hasta pasa intacto', () => {
  const a = { title: 'A', day: '2026-10-22', time: '10:00' }, b = { ...expo, hasta: undefined };
  const r = expandVentanas([a, b], DK);
  assert.strictEqual(r[0], a); assert.strictEqual(r[1], b); assert.strictEqual(r.length, 2);
});

test('los dias_vacios del festival no reciben copia (Anibia: 26 y 29 oct)', () => {
  const r = expandVentanas([expo], DK, ['2026-10-24']);
  assert.deepStrictEqual(r.map(f => f.day), ['2026-10-23', '2026-11-01']);
});
