// Fitness function de FESTIVAL_STATE (src/state/festival-context.js) — la tabla
// declarativa de estado por-festival.
//
// POR QUÉ EXISTE: la clase de bug más cara de multi-festival es "olvidé un sitio"
// al agregar/cambiar estado por-festival (el sangrado de availability). La tabla
// centraliza la definición; este test la CONGELA como contrato: toda entrada debe
// estar en el roster de state y tener su par get/set en storage — así olvidar
// registrar un estado nuevo pasa a ser fallo de CI, no un bug en producción.

const { test, before } = require('node:test');
const assert = require('node:assert');

let FC, STATE_ROSTER, storage;
before(async () => {
  FC = await import('../../src/state/festival-context.js');
  STATE_ROSTER = (await import('../../src/state/state.js')).STATE_ROSTER;
  storage = (await import('../../src/storage/storage.js')).storage;
});

test('FESTIVAL_STATE — cada key está en el roster de state', () => {
  for (const e of FC.FESTIVAL_STATE) {
    assert.ok(STATE_ROSTER.has(e.key), `roster de state incluye '${e.key}'`);
  }
});

test('FESTIVAL_STATE — cada key tiene par get/set en storage', () => {
  for (const e of FC.FESTIVAL_STATE) {
    assert.strictEqual(typeof storage['get' + e.storage], 'function', `storage.get${e.storage}`);
    assert.strictEqual(typeof storage['set' + e.storage], 'function', `storage.set${e.storage}`);
  }
});

test('FESTIVAL_STATE — cloud null o string (columna de user_festival_state)', () => {
  for (const e of FC.FESTIVAL_STATE) {
    assert.ok(e.cloud === null || typeof e.cloud === 'string', `cloud de '${e.key}'`);
  }
});

test('deriveClear — produce TODAS las keys por-festival con vacíos correctos', () => {
  const cfg = { dayKeys: ['2026-07-13', '2026-07-14'] };
  const clear = FC.deriveClear(cfg);
  // completitud: exactamente las keys de la tabla
  assert.deepStrictEqual(
    Object.keys(clear).sort(),
    FC.FESTIVAL_STATE.map(e => e.key).sort(),
    'clear cubre exactamente FESTIVAL_STATE'
  );
  // vacíos por tipo
  assert.ok(clear.watchlist instanceof Set && clear.watchlist.size === 0, 'watchlist Set vacío');
  assert.ok(clear.watched instanceof Set && clear.watched.size === 0, 'watched Set vacío');
  assert.ok(clear.prioritized instanceof Set && clear.prioritized.size === 0, 'prioritized Set vacío');
  assert.deepStrictEqual(clear.filmRatings, {}, 'filmRatings {}');
  assert.strictEqual(clear.savedAgenda, null, 'savedAgenda null');
  assert.deepStrictEqual(clear.filmDelays, {}, 'filmDelays {}');
  assert.deepStrictEqual(clear.filmDelaysHistory, {}, 'filmDelaysHistory {}');
  assert.deepStrictEqual(clear.lastRemovedSlots, [], 'lastRemovedSlots []');
  // availability: {blocks:[]} sembrado por dayKey (NO hereda del festival anterior)
  assert.deepStrictEqual(
    clear.availability,
    { '2026-07-13': { blocks: [] }, '2026-07-14': { blocks: [] } },
    'availability sembrada por día'
  );
});

test('deriveClear — availability vacía sin dayKeys (defensivo)', () => {
  assert.deepStrictEqual(FC.deriveClear({}).availability, {}, 'sin dayKeys → {}');
  assert.deepStrictEqual(FC.deriveClear().availability, {}, 'sin cfg → {}');
});
