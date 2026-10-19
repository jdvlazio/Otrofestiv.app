// fichas.test.js — la ficha del festival publicada aparte (Etapa 2·B1, 19 oct 2026).
// src/fichas.js decide qué campos puede tocar una ficha del almacén y cómo se
// aplican sobre la copia que trae la app. Lo crítico: nunca `storageKey` (es la
// llave de lo guardado por cada usuario) y nunca un festival a medias.
const test = require('node:test');
const assert = require('node:assert');

let F;
test.before(async () => { F = await import('../../src/fichas.js'); });

const base = () => ({ bhff2026: { name: 'BHFF', city: 'Bogotá', dates: '22–31 OCT', storageKey: 'bhff2026_',
  keyArt: '/assets/keyart/bhff2026-v1.jpg', films: [1], festivalEndStr: '2026-10-31T23:59:00' } });

test('FI1 — pisa los campos de ficha y avisa cuáles cambiaron', () => {
  const c = base();
  const ids = F.aplicarFichas(c, { bhff2026: { keyArt: 'https://x/keyart/abc.jpg', dates: '22–31 OCT' } });
  assert.deepStrictEqual(ids, ['bhff2026']);
  assert.strictEqual(c.bhff2026.keyArt, 'https://x/keyart/abc.jpg');
  assert.deepStrictEqual(c.bhff2026.films, [1], 'lo que no es ficha no se toca');
});

test('FI2 — sin cambios reales no reporta nada (la portada no se re-dibuja de gusto)', () => {
  const c = base();
  assert.deepStrictEqual(F.aplicarFichas(c, { bhff2026: { name: 'BHFF', city: 'Bogotá' } }), []);
});

test('FI3 — storageKey y campos ajenos NUNCA se aplican', () => {
  const c = base();
  F.aplicarFichas(c, { bhff2026: { storageKey: 'otro_', films: [], dayKeys: ['x'] } });
  assert.strictEqual(c.bhff2026.storageKey, 'bhff2026_');
  assert.deepStrictEqual(c.bhff2026.films, [1]);
  assert.strictEqual(c.bhff2026.dayKeys, undefined);
  assert.ok(!F.CAMPOS_FICHA.includes('storageKey'));
});

test('FI4 — un festival nuevo entra solo con lo mínimo, y con su propia llave', () => {
  const c = base();
  const minimo = { name: 'Nuevo', city: 'Cali', dates: '1–5 NOV', festivalStartStr: '2026-11-01T00:00:00', festivalEndStr: '2026-11-05T23:00:00' };
  F.aplicarFichas(c, { nuevo2026: { name: 'Nuevo', city: 'Cali' } });
  assert.strictEqual(c.nuevo2026, undefined, 'a medias no entra');
  assert.deepStrictEqual(F.aplicarFichas(c, { nuevo2026: minimo }), ['nuevo2026']);
  assert.strictEqual(c.nuevo2026.storageKey, 'nuevo2026_');
  assert.strictEqual(c.nuevo2026.films, null);
});

test('FI5 — el índice: id de la app desde el archivo, y apagado no trae fichas', () => {
  const ix = { festivales: { 'bhff-2026': { archivo: 'a', ficha: { name: 'B' } }, 'ficci-65': { archivo: 'b' } } };
  assert.deepStrictEqual(F.fichasDelIndice(ix), { bhff2026: { name: 'B' } });
  assert.deepStrictEqual(F.fichasDelIndice({ ...ix, apagado: true }), {});
  assert.deepStrictEqual(F.fichasDelIndice(null), {});
});

test('FI6 — un id raro no se cuela como festival', () => {
  const c = base();
  F.aplicarFichas(c, { '__proto__': { name: 'x' }, 'Mal-Id': { name: 'y', city: 'c', dates: 'd', festivalStartStr: 's', festivalEndStr: 'e' } });
  assert.strictEqual(Object.keys(c).length, 1);
});
