// Unit tests for the storage namespace — extracted from index.html via load-domain.
// Mock localStorage (Map-backed) inyectado vía globals. FESTIVAL_STORAGE_KEY
// también inyectado para que los métodos user-state usen un prefix predecible.

const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

function mockLocalStorage() {
  const store = new Map();
  return {
    getItem: k => store.has(k) ? store.get(k) : null,
    setItem: (k, v) => store.set(k, String(v)),
    removeItem: k => store.delete(k),
    clear: () => store.clear(),
    _store: store, // exposed para inspección directa en tests
  };
}

function setup(opts = {}) {
  const ls = mockLocalStorage();
  if (opts.preset) {
    for (const [k, v] of Object.entries(opts.preset)) {
      ls.setItem(k, v);
    }
  }
  const { storage } = loadDomain({
    functions: [],
    objects: ['storage'],
    globals: {
      localStorage: ls,
      FESTIVAL_STORAGE_KEY: opts.prefix || 'test_',
    },
  });
  return { storage, ls };
}

// ── User state — Sets (watchlist, watched, prioritized) ──

test('watchlist: empty returns new Set(), roundtrip preserves entries', () => {
  const { storage } = setup();
  assert.deepStrictEqual([...storage.getWatchlist()], []);
  storage.setWatchlist(new Set(['Film A', 'Film B']));
  assert.deepStrictEqual([...storage.getWatchlist()].sort(), ['Film A', 'Film B']);
});

test('watched: empty returns new Set(), roundtrip preserves entries', () => {
  const { storage } = setup();
  assert.deepStrictEqual([...storage.getWatched()], []);
  storage.setWatched(new Set(['Vista 1']));
  assert.deepStrictEqual([...storage.getWatched()], ['Vista 1']);
});

test('prioritized: empty returns new Set(), roundtrip preserves entries', () => {
  const { storage } = setup();
  assert.deepStrictEqual([...storage.getPrioritized()], []);
  storage.setPrioritized(new Set(['Prio 1', 'Prio 2']));
  assert.deepStrictEqual([...storage.getPrioritized()].sort(), ['Prio 1', 'Prio 2']);
});

// ── User state — Objects ──

test('filmRatings: empty returns {}, roundtrip preserves entries', () => {
  const { storage } = setup();
  assert.deepStrictEqual(storage.getFilmRatings(), {});
  storage.setFilmRatings({ 'Film A': 4.5, 'Film B': 3 });
  assert.deepStrictEqual(storage.getFilmRatings(), { 'Film A': 4.5, 'Film B': 3 });
});

test('savedAgenda: empty returns null, roundtrip preserves object', () => {
  const { storage } = setup();
  assert.strictEqual(storage.getSavedAgenda(), null);
  storage.setSavedAgenda({ schedule: [{ title: 'A', day: 'MAR 21' }] });
  assert.deepStrictEqual(storage.getSavedAgenda(), { schedule: [{ title: 'A', day: 'MAR 21' }] });
});

test('availability: empty returns {}, roundtrip preserves per-day blocks', () => {
  const { storage } = setup();
  assert.deepStrictEqual(storage.getAvailability(), {});
  const av = { 'MAR 21': { blocks: [{ from: '10:00 AM', to: '12:00 PM' }] } };
  storage.setAvailability(av);
  assert.deepStrictEqual(storage.getAvailability(), av);
});

test('filmDelays: empty returns {}, roundtrip preserves entries', () => {
  const { storage } = setup();
  assert.deepStrictEqual(storage.getFilmDelays(), {});
  storage.setFilmDelays({ 'Film A|MAR 21|10:00 AM': 15 });
  assert.deepStrictEqual(storage.getFilmDelays(), { 'Film A|MAR 21|10:00 AM': 15 });
});

test('viewmodes: empty returns {}, roundtrip preserves miPlan/intereses', () => {
  const { storage } = setup();
  assert.deepStrictEqual(storage.getViewmodes(), {});
  storage.setViewmodes({ miPlan: 'list', intereses: 'grid' });
  assert.deepStrictEqual(storage.getViewmodes(), { miPlan: 'list', intereses: 'grid' });
});

// ── User state — Array ──

test('lastRemovedSlots: empty returns [], roundtrip preserves array', () => {
  const { storage } = setup();
  assert.deepStrictEqual(storage.getLastRemovedSlots(), []);
  storage.setLastRemovedSlots([{ _title: 'A', day: 'X' }, { _title: 'B', day: 'Y' }]);
  assert.strictEqual(storage.getLastRemovedSlots().length, 2);
  assert.strictEqual(storage.getLastRemovedSlots()[0]._title, 'A');
});

test('lastRemovedSlots: normaliza non-array value a single-element array', () => {
  // Legacy data podría tener {} en vez de [{}] — el adapter normaliza.
  const { storage } = setup({ preset: { 'test_lastslot': '{"_title":"single"}' } });
  const result = storage.getLastRemovedSlots();
  assert.ok(Array.isArray(result));
  assert.strictEqual(result.length, 1);
  assert.strictEqual(result[0]._title, 'single');
});

// ── Global keys (no prefix) ──

test('activeFestId: empty returns null, roundtrip works, NO prefix', () => {
  const { storage, ls } = setup();
  assert.strictEqual(storage.getActiveFestId(), null);
  storage.setActiveFestId('tribeca2026');
  assert.strictEqual(storage.getActiveFestId(), 'tribeca2026');
  // Verificar que NO usa FESTIVAL_STORAGE_KEY como prefix
  assert.strictEqual(ls.getItem('otrofestiv_festival'), 'tribeca2026');
  assert.strictEqual(ls.getItem('test_otrofestiv_festival'), null);
});

test('lang: empty returns null, roundtrip works', () => {
  const { storage } = setup();
  assert.strictEqual(storage.getLang(), null);
  storage.setLang('en');
  assert.strictEqual(storage.getLang(), 'en');
});

test('build: empty returns null, roundtrip works', () => {
  const { storage } = setup();
  assert.strictEqual(storage.getBuild(), null);
  storage.setBuild('202605201951');
  assert.strictEqual(storage.getBuild(), '202605201951');
});

// ── Prefix vs no-prefix ──

test('user-state keys SI usan FESTIVAL_STORAGE_KEY como prefix', () => {
  const { storage, ls } = setup({ prefix: 'tribeca2026_' });
  storage.setWatchlist(new Set(['Film X']));
  assert.strictEqual(ls.getItem('tribeca2026_wl'), JSON.stringify(['Film X']));
  // No debe haber otro key sin prefix
  assert.strictEqual(ls.getItem('wl'), null);
});

test('global keys NO toman FESTIVAL_STORAGE_KEY como prefix', () => {
  const { storage, ls } = setup({ prefix: 'tribeca2026_' });
  storage.setActiveFestId('aff2026');
  storage.setLang('es');
  storage.setBuild('xyz');
  assert.strictEqual(ls.getItem('otrofestiv_festival'), 'aff2026');
  assert.strictEqual(ls.getItem('otrofestiv_lang'), 'es');
  assert.strictEqual(ls.getItem('otrofestiv_build'), 'xyz');
  // Y no aparecen con prefix
  assert.strictEqual(ls.getItem('tribeca2026_otrofestiv_festival'), null);
});

// ── Robustness — parse failures + writes silent-fail ──

test('parse failure en JSON corrupto retorna default vacío', () => {
  const { storage } = setup({ preset: {
    'test_wl': 'not-json',
    'test_saved': '{broken',
    'test_ratings': '[]invalid',
  }});
  assert.deepStrictEqual([...storage.getWatchlist()], []);
  assert.strictEqual(storage.getSavedAgenda(), null);
  assert.deepStrictEqual(storage.getFilmRatings(), {});
});

test('write failure silent-fail (mock throw)', () => {
  const ls = mockLocalStorage();
  // Override setItem para simular QuotaExceededError
  ls.setItem = () => { throw new Error('QuotaExceededError'); };
  const { storage } = loadDomain({
    functions: [],
    objects: ['storage'],
    globals: { localStorage: ls, FESTIVAL_STORAGE_KEY: 'test_' },
  });
  // No debe throw — el adapter cathchea silenciosamente
  assert.doesNotThrow(() => storage.setWatchlist(new Set(['A'])));
  assert.doesNotThrow(() => storage.setLang('en'));
});

// ── Cambios de FESTIVAL_STORAGE_KEY ──

test('cambio de prefix produce reads aislados entre festivales (simulación de switch)', () => {
  const ls = mockLocalStorage();
  // Festival A: watchlist con 2 entradas
  const { storage: storageA } = loadDomain({
    functions: [],
    objects: ['storage'],
    globals: { localStorage: ls, FESTIVAL_STORAGE_KEY: 'festA_' },
  });
  storageA.setWatchlist(new Set(['A1', 'A2']));

  // Festival B (mismo localStorage): watchlist con otras entradas
  const { storage: storageB } = loadDomain({
    functions: [],
    objects: ['storage'],
    globals: { localStorage: ls, FESTIVAL_STORAGE_KEY: 'festB_' },
  });
  storageB.setWatchlist(new Set(['B1']));

  // Cada festival ve solo lo suyo
  assert.deepStrictEqual([...storageA.getWatchlist()].sort(), ['A1', 'A2']);
  assert.deepStrictEqual([...storageB.getWatchlist()], ['B1']);
  // Keys en raw localStorage están separados por prefix
  assert.strictEqual(ls.getItem('festA_wl'), JSON.stringify(['A1', 'A2']));
  assert.strictEqual(ls.getItem('festB_wl'), JSON.stringify(['B1']));
});

// ── Set serialization round-trip ──

test('Sets se serializan como arrays y se deserializan como Sets', () => {
  const { storage, ls } = setup();
  storage.setWatched(new Set(['F1', 'F2', 'F3']));
  // En storage está como JSON array
  const raw = JSON.parse(ls.getItem('test_watched'));
  assert.ok(Array.isArray(raw));
  assert.strictEqual(raw.length, 3);
  // Al leer, vuelve a ser Set
  const restored = storage.getWatched();
  assert.ok(restored instanceof Set);
  assert.strictEqual(restored.size, 3);
});
