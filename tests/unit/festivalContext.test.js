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

let FC, STATE_ROSTER, storage, state;
before(async () => {
  FC = await import('../../src/state/festival-context.js');
  const S = await import('../../src/state/state.js');
  STATE_ROSTER = S.STATE_ROSTER;
  state = S.state;
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

// ── P1.3: nube (deriveCloudSave / deriveCloudApply) ──
// Reemplazan la cobertura live (no QA-eable sin Supabase). Congelan la lógica
// wholesale-vs-parcial de _applyCloudRow y la serialización de _doCloudSave.

test('deriveCloudSave — fila desde el state (Set→array, solo columnas cloud)', () => {
  state.set('watchlist', new Set(['A', 'B']));
  state.set('watched', new Set(['C']));
  state.set('prioritized', new Set(['A']));
  state.set('filmRatings', { A: 5 });
  state.set('savedAgenda', { schedule: [] });
  state.set('availability', { d1: { blocks: [1] } });
  const row = FC.deriveCloudSave();
  assert.deepStrictEqual([...row.watchlist].sort(), ['A', 'B'], 'watchlist Set→array');
  assert.deepStrictEqual(row.watched, ['C']);
  assert.deepStrictEqual(row.prioritized, ['A']);
  assert.deepStrictEqual(row.ratings, { A: 5 }, 'columna ratings ← filmRatings');
  assert.deepStrictEqual(row.saved_agenda, { schedule: [] }, 'columna saved_agenda');
  assert.deepStrictEqual(row.availability, { d1: { blocks: [1] } });
  // los 3 estados local-only (cloud:null) NO van a la fila
  assert.ok(!('lastRemovedSlots' in row) && !('filmDelays' in row) && !('filmDelaysHistory' in row),
    'cloud:null no se suben');
});

test('deriveCloudApply — wholesale (Realtime): reemplaza, aplica hasta vacíos', () => {
  state.set('filmRatings', { OLD: 1 });
  state.set('availability', { d1: { blocks: ['x'] }, d2: { blocks: [] } });
  const data = { watchlist: ['A'], watched: [], prioritized: ['A'], ratings: { B: 3 },
                 saved_agenda: { s: 1 }, availability: { d1: { blocks: ['new'] } } };
  const u = FC.deriveCloudApply(data, true);
  assert.deepStrictEqual([...u.watchlist], ['A'], 'watchlist array→Set');
  assert.ok(u.watched instanceof Set && u.watched.size === 0, 'watched vacío SÍ aplica (whole)');
  assert.deepStrictEqual(u.filmRatings, { B: 3 }, 'ratings REEMPLAZA (no mergea)');
  assert.deepStrictEqual(u.savedAgenda, { s: 1 });
  assert.deepStrictEqual(u.availability, { d1: { blocks: ['new'] } }, 'availability reemplaza entero');
  assert.ok(!('lastRemovedSlots' in u) && !('filmDelays' in u), 'cloud:null nunca en el apply');
});

test('deriveCloudApply — parcial (boot): solo no-vacíos + merge de ratings/availability', () => {
  state.set('filmRatings', { A: 5 });
  state.set('availability', { d1: { blocks: ['keep'] }, d2: { blocks: ['keep2'] } });
  const data = { watchlist: ['X'], watched: [], prioritized: [], ratings: { B: 3 },
                 saved_agenda: null, availability: { d2: { blocks: ['newd2'] }, d3: { blocks: ['stray'] } } };
  const u = FC.deriveCloudApply(data, false);
  assert.deepStrictEqual([...u.watchlist], ['X'], 'no-vacío → aplica');
  assert.ok(!('watched' in u), 'watched vacío → NO aplica (gate parcial)');
  assert.ok(!('prioritized' in u), 'prioritized vacío → NO aplica');
  assert.deepStrictEqual(u.filmRatings, { A: 5, B: 3 }, 'ratings MERGEA con el actual');
  assert.ok(!('savedAgenda' in u), 'saved_agenda null → NO aplica');
  // availability parcial: d1 conserva (no venía), d2 pisado, d3 IGNORADO (no es dayKey del festival)
  assert.deepStrictEqual(u.availability, { d1: { blocks: ['keep'] }, d2: { blocks: ['newd2'] } },
    'merge por-día; días fuera de los dayKeys se ignoran');
});
