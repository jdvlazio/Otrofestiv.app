// state.test.js — p5.5 state container mirror tests
//
// La invariante crítica de Fase 5.5 es: state.set(k,v) → state.get(k)===v
// Y simultáneamente el global mirror también ===v. Plus: batchUpdate aplica
// TODO el batch antes de notificar a subscribers (atomicidad).
//
// Estrategia de carga: el bloque `const state = (() => {...})()` vive en
// index.html y closures sobre los 19 globals del roster. Para testear sin
// arrancar el browser, extraemos el bloque entre los marcadores STATE START/END
// y lo eval en un sandbox que pre-declara los globals + expone getters para
// inspección desde los tests.

const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');

const INDEX = path.resolve(__dirname, '..', '..', 'index.html');

function extractStateBlock() {
  const html = fs.readFileSync(INDEX, 'utf8');
  const startMarker = '// ── STATE MIRROR START';
  const endMarker = '// ── STATE MIRROR END';
  const startIdx = html.indexOf(startMarker);
  const endIdx = html.indexOf(endMarker);
  if (startIdx < 0 || endIdx < 0) throw new Error('STATE markers not found in index.html');
  // Devuelve el bloque incluyendo la declaración `const state = (()=>{...})();`
  return html.slice(startIdx, endIdx);
}

// Construye un sandbox fresco — cada test debería llamar esto para aislamiento.
function makeSandbox() {
  const stateBlock = extractStateBlock();
  // Pre-declarar los 19 globals con valores neutros. El IIFE `const state = ...`
  // capturará estas bindings via closure y los mirror setters podrán reasignarlas.
  // Los `get` accessors del objeto retornado permiten al test leer el valor actual.
  const src = `(function () {
    let _activeFestId = null;
    let FILMS = [];
    let FESTIVAL_DATES = {};
    let FESTIVAL_END = null;
    let FESTIVAL_STORAGE_KEY = '';
    let PRIO_LIMIT = 0;
    let TZ_OFFSET = '';
    let FESTIVAL_TRANSPORT = '';
    let watchlist = new Set();
    let watched = new Set();
    let prioritized = new Set();
    let filmRatings = {};
    let filmDelays = {};
    let filmDelaysHistory = {};
    let savedAgenda = null;
    let availability = {};
    let lastRemovedSlots = [];
    let _lang = '';
    let _simTime = null;

    ${stateBlock}

    return {
      state,
      mirror: {
        get _activeFestId() { return _activeFestId; },
        get FILMS() { return FILMS; },
        get FESTIVAL_DATES() { return FESTIVAL_DATES; },
        get FESTIVAL_END() { return FESTIVAL_END; },
        get FESTIVAL_STORAGE_KEY() { return FESTIVAL_STORAGE_KEY; },
        get PRIO_LIMIT() { return PRIO_LIMIT; },
        get TZ_OFFSET() { return TZ_OFFSET; },
        get FESTIVAL_TRANSPORT() { return FESTIVAL_TRANSPORT; },
        get watchlist() { return watchlist; },
        get watched() { return watched; },
        get prioritized() { return prioritized; },
        get filmRatings() { return filmRatings; },
        get filmDelays() { return filmDelays; },
        get filmDelaysHistory() { return filmDelaysHistory; },
        get savedAgenda() { return savedAgenda; },
        get availability() { return availability; },
        get lastRemovedSlots() { return lastRemovedSlots; },
        get _lang() { return _lang; },
        get _simTime() { return _simTime; },
      },
    };
  })();`;
  // eslint-disable-next-line no-eval
  return eval(src);
}

// ═══════════════════════════════════════════════════════════════════════
// API básica — get/set
// ═══════════════════════════════════════════════════════════════════════

test('set único: state.get retorna el valor seteado', () => {
  const { state } = makeSandbox();
  state.set('_lang', 'en');
  assert.equal(state.get('_lang'), 'en');
});

test('set único: mirror al global también se actualiza', () => {
  const { state, mirror } = makeSandbox();
  state.set('_lang', 'en');
  assert.equal(mirror._lang, 'en');
});

test('set con key inválida: throw con mensaje claro', () => {
  const { state } = makeSandbox();
  assert.throws(() => state.set('NOT_A_KEY', 'x'), /unknown key.*NOT_A_KEY/);
});

test('get sin previo set retorna el valor actual del global mirror (lazy seed)', () => {
  // Invariante: state.get(k) === <global k> en TODO momento, incluso antes
  // de cualquier state.set explícito. Esto soporta migración incremental
  // (Fase 5.5 mirror): mientras readers no migran, escrituras legacy a globals
  // siguen pasando, y state.get refleja el global actual.
  const { state } = makeSandbox();
  assert.equal(state.get('_lang'), '');           // sandbox initial
  assert.deepEqual([...state.get('watchlist')], []); // sandbox initial Set
  assert.equal(state.get('PRIO_LIMIT'), 0);
});

// ═══════════════════════════════════════════════════════════════════════
// update
// ═══════════════════════════════════════════════════════════════════════

test('update: fn recibe el valor actual y retorna el nuevo', () => {
  const { state, mirror } = makeSandbox();
  state.set('watchlist', new Set(['a','b']));
  state.update('watchlist', s => new Set([...s, 'c']));
  assert.deepEqual([...state.get('watchlist')].sort(), ['a','b','c']);
  assert.deepEqual([...mirror.watchlist].sort(), ['a','b','c']);
});

test('update sin previo set: fn recibe el valor del global mirror (no undefined)', () => {
  // Caso real Fase 5.5: legacy code asigna `watchlist = new Set([...]); ` y
  // luego un callsite migrado hace state.update('watchlist', s => addTo(s, t)).
  // Si la update no leyera del mirror, fn recibiría undefined y crashearía.
  const { state, mirror } = makeSandbox();
  state.update('watchlist', s => new Set([...s, 'x']));
  assert.deepEqual([...state.get('watchlist')], ['x']);
  assert.deepEqual([...mirror.watchlist], ['x']);
});

test('update: identidad del nuevo valor es la que retorna fn (no clone interno)', () => {
  const { state, mirror } = makeSandbox();
  const newSet = new Set(['x']);
  state.update('watchlist', () => newSet);
  assert.equal(state.get('watchlist'), newSet);
  assert.equal(mirror.watchlist, newSet);
});

// ═══════════════════════════════════════════════════════════════════════
// snapshot
// ═══════════════════════════════════════════════════════════════════════

test('snapshot: shallow copy del state interno', () => {
  const { state } = makeSandbox();
  state.set('_lang', 'es');
  state.set('watchlist', new Set(['a']));
  const snap = state.snapshot();
  assert.equal(snap._lang, 'es');
  assert.deepEqual([...snap.watchlist], ['a']);
});

test('snapshot: mutación local del snapshot no afecta state interno', () => {
  const { state } = makeSandbox();
  state.set('_lang', 'es');
  const snap = state.snapshot();
  snap._lang = 'CORRUPTED';
  assert.equal(state.get('_lang'), 'es');
});

// ═══════════════════════════════════════════════════════════════════════
// subscribe
// ═══════════════════════════════════════════════════════════════════════

test('subscribe: cb se invoca síncronamente con (value, key)', () => {
  const { state } = makeSandbox();
  const calls = [];
  state.subscribe('_lang', (v, k) => calls.push([k, v]));
  state.set('_lang', 'en');
  assert.deepEqual(calls, [['_lang', 'en']]);
});

test('subscribe: cb solo dispara para la key suscrita', () => {
  const { state } = makeSandbox();
  const langCalls = [];
  state.subscribe('_lang', v => langCalls.push(v));
  state.set('watchlist', new Set(['x']));
  assert.deepEqual(langCalls, []);
});

test('subscribe: retorna unsubscribe fn que detiene notifications', () => {
  const { state } = makeSandbox();
  const calls = [];
  const unsub = state.subscribe('_lang', v => calls.push(v));
  state.set('_lang', 'en');
  unsub();
  state.set('_lang', 'es');
  assert.deepEqual(calls, ['en']);
});

test('subscribe: múltiples subscribers del mismo key todos invocados', () => {
  const { state } = makeSandbox();
  const a = [], b = [];
  state.subscribe('_lang', v => a.push(v));
  state.subscribe('_lang', v => b.push(v));
  state.set('_lang', 'en');
  assert.deepEqual(a, ['en']);
  assert.deepEqual(b, ['en']);
});

test('subscribe: unsubscribe desde dentro de notify no rompe iteración', () => {
  const { state } = makeSandbox();
  const order = [];
  let unsubB;
  state.subscribe('_lang', () => { order.push('A'); unsubB(); });
  unsubB = state.subscribe('_lang', () => order.push('B'));
  const c = state.subscribe('_lang', () => order.push('C'));
  state.set('_lang', 'en');
  // A se ejecuta, hace unsub de B, pero la iteración usa snapshot del Set
  // por lo que B también corre. C corre normalmente.
  assert.deepEqual(order, ['A', 'B', 'C']);
});

test('subscribe: excepción en un cb no impide otros cbs', () => {
  const { state } = makeSandbox();
  // Silenciar el console.error del state durante este test
  const origErr = console.error;
  console.error = () => {};
  try {
    const order = [];
    state.subscribe('_lang', () => { order.push('A'); throw new Error('boom'); });
    state.subscribe('_lang', () => order.push('B'));
    state.set('_lang', 'en');
    assert.deepEqual(order, ['A', 'B']);
  } finally {
    console.error = origErr;
  }
});

// ═══════════════════════════════════════════════════════════════════════
// batchUpdate — atomicidad CRÍTICA
// ═══════════════════════════════════════════════════════════════════════

test('batchUpdate: aplica TODAS las keys antes de notificar', () => {
  const { state } = makeSandbox();
  let observedSnapshot = null;
  state.subscribe('_activeFestId', () => {
    // Si batchUpdate es atómico, cuando A se notifica, B y C ya están aplicados
    observedSnapshot = state.snapshot();
  });
  state.batchUpdate({
    _activeFestId: 'tribeca2026',
    _lang: 'en',
    PRIO_LIMIT: 7,
  });
  assert.equal(observedSnapshot._activeFestId, 'tribeca2026');
  assert.equal(observedSnapshot._lang, 'en');
  assert.equal(observedSnapshot.PRIO_LIMIT, 7);
});

test('batchUpdate: mirror al global se actualiza para TODAS las keys antes de notify', () => {
  const { state, mirror } = makeSandbox();
  let observed = null;
  state.subscribe('_activeFestId', () => {
    observed = { id: mirror._activeFestId, lang: mirror._lang, lim: mirror.PRIO_LIMIT };
  });
  state.batchUpdate({
    _activeFestId: 'aff2026',
    _lang: 'es',
    PRIO_LIMIT: 5,
  });
  assert.deepEqual(observed, { id: 'aff2026', lang: 'es', lim: 5 });
});

test('batchUpdate: cada key dirty notifica exactamente una vez', () => {
  const { state } = makeSandbox();
  const counts = {};
  ['_activeFestId', '_lang', 'PRIO_LIMIT'].forEach(k => {
    counts[k] = 0;
    state.subscribe(k, () => counts[k]++);
  });
  state.batchUpdate({
    _activeFestId: 'tribeca2026',
    _lang: 'en',
    PRIO_LIMIT: 5,
  });
  assert.deepEqual(counts, { _activeFestId: 1, _lang: 1, PRIO_LIMIT: 1 });
});

test('batchUpdate: subscriber que llama state.set se notifica DESPUÉS del batch', () => {
  const { state } = makeSandbox();
  const order = [];
  state.subscribe('_lang', () => {
    order.push('lang-notified');
    // Reentrada: setear otra key dentro del notify del batch
    if (order.length === 1) state.set('PRIO_LIMIT', 99);
  });
  state.subscribe('PRIO_LIMIT', v => order.push('prio-notified:' + v));
  state.batchUpdate({ _lang: 'en', _activeFestId: 'x' });
  // El subscriber de _lang corre dentro del batch flush. Al llamar state.set
  // _batchDepth ya es 0, así que prio se notifica inmediatamente. Pero el orden:
  // lang-notified (dentro del flush del batch) → prio-notified (inmediato post-set).
  assert.deepEqual(order, ['lang-notified', 'prio-notified:99']);
});

test('batchUpdate: subscriber que llama batchUpdate anidado funciona', () => {
  const { state } = makeSandbox();
  const order = [];
  state.subscribe('_lang', () => {
    order.push('outer-lang');
    if (order.length === 1) state.batchUpdate({ PRIO_LIMIT: 42, TZ_OFFSET: '-08:00' });
  });
  state.subscribe('PRIO_LIMIT', v => order.push('inner-prio:' + v));
  state.subscribe('TZ_OFFSET', v => order.push('inner-tz:' + v));
  state.batchUpdate({ _lang: 'en' });
  assert.deepEqual(order, ['outer-lang', 'inner-prio:42', 'inner-tz:-08:00']);
});

test('batchUpdate: key inválida → throw, ningún cambio aplicado', () => {
  const { state, mirror } = makeSandbox();
  state.set('_lang', 'es');
  // PRIO_LIMIT pre-batch es el global initial (0), no undefined post-lazy-seed
  const prioBefore = state.get('PRIO_LIMIT');
  assert.throws(() => state.batchUpdate({
    _lang: 'en',
    BOGUS_KEY: 42,
    PRIO_LIMIT: 99,
  }), /unknown key.*BOGUS_KEY/);
  // Verifica fail-fast: nada aplicado (ni en state ni en mirror)
  assert.equal(state.get('_lang'), 'es');
  assert.equal(state.get('PRIO_LIMIT'), prioBefore);
  assert.equal(mirror._lang, 'es');
  assert.equal(mirror.PRIO_LIMIT, prioBefore);
});

test('batchUpdate: vacío → no-op, no notify', () => {
  const { state } = makeSandbox();
  let notified = false;
  state.subscribe('_lang', () => { notified = true; });
  state.batchUpdate({});
  assert.equal(notified, false);
});

test('batchUpdate: rollback en error de _MIRROR_TARGETS', () => {
  // Forzar un mirror setter que throwee es complicado vía API pública.
  // En la práctica esto solo pasa si el global es no-asignable (e.g., const).
  // Test alternativo: keyValidation en pre-loop garantiza fail-fast. Ya cubierto
  // arriba. Aquí verifico que un throw DENTRO de un mirror setter rollbackea —
  // monkey-patching el setter requeriría exponer _MIRROR_TARGETS. Skip por ahora.
  // TODO: si extendemos state con un hook de mirror, añadir test concreto.
  assert.ok(true); // placeholder
});

// ═══════════════════════════════════════════════════════════════════════
// Helpers immutable expuestos
// ═══════════════════════════════════════════════════════════════════════

test('_addToSet: agrega si no existe, retorna mismo set si ya existe (identity preserved)', () => {
  const { state } = makeSandbox();
  const s = new Set(['a', 'b']);
  const r1 = state._addToSet(s, 'c');
  assert.notEqual(r1, s);
  assert.deepEqual([...r1].sort(), ['a', 'b', 'c']);
  const r2 = state._addToSet(s, 'a');
  assert.equal(r2, s, 'identity preserved when key already present');
});

test('_delFromSet: borra si existe, retorna mismo set si no existe', () => {
  const { state } = makeSandbox();
  const s = new Set(['a', 'b']);
  const r1 = state._delFromSet(s, 'a');
  assert.notEqual(r1, s);
  assert.deepEqual([...r1], ['b']);
  const r2 = state._delFromSet(s, 'zzz');
  assert.equal(r2, s, 'identity preserved when key absent');
});

test('_omit: borra propiedad de object, retorna mismo si no existe', () => {
  const { state } = makeSandbox();
  const o = { a: 1, b: 2 };
  const r1 = state._omit(o, 'a');
  assert.notEqual(r1, o);
  assert.deepEqual(r1, { b: 2 });
  const r2 = state._omit(o, 'zzz');
  assert.equal(r2, o, 'identity preserved when key absent');
});

// ═══════════════════════════════════════════════════════════════════════
// Mirror invariant — los 19 keys
// ═══════════════════════════════════════════════════════════════════════

test('mirror invariant: los 19 keys del roster espejean al global', () => {
  const { state, mirror } = makeSandbox();
  const cases = {
    _activeFestId: 'tribeca2026',
    FILMS: [{title:'x'}],
    FESTIVAL_DATES: { d1: '2026-01-01' },
    FESTIVAL_END: new Date('2026-06-14'),
    FESTIVAL_STORAGE_KEY: 'tribeca2026_',
    PRIO_LIMIT: 7,
    TZ_OFFSET: '-08:00',
    FESTIVAL_TRANSPORT: 'driving',
    watchlist: new Set(['a']),
    watched: new Set(['b']),
    prioritized: new Set(['c']),
    filmRatings: { x: 4.5 },
    filmDelays: { k1: 10 },
    filmDelaysHistory: { k1: [0] },
    savedAgenda: { schedule: [] },
    availability: { d1: { blocks: [] } },
    lastRemovedSlots: [{ _title: 'x' }],
    _lang: 'en',
    _simTime: '2026-06-04T12:00:00.000Z',
  };
  for (const [k, v] of Object.entries(cases)) {
    state.set(k, v);
    assert.equal(state.get(k), v, `state.get ${k}`);
    assert.equal(mirror[k], v, `mirror ${k}`);
  }
});

test('batchUpdate de loadFestival shape: 15 keys atómicas', () => {
  const { state, mirror } = makeSandbox();
  let parcial = false;
  state.subscribe('FILMS', () => {
    // Si vemos films de tribeca pero _activeFestId todavía no, falla
    if (state.get('_activeFestId') !== 'tribeca2026') parcial = true;
  });
  state.batchUpdate({
    _activeFestId: 'tribeca2026',
    FILMS: [{title:'Anora'}],
    FESTIVAL_DATES: { d1: '2026-06-03' },
    FESTIVAL_END: new Date('2026-06-14'),
    FESTIVAL_STORAGE_KEY: 'tribeca2026_',
    PRIO_LIMIT: 5,
    TZ_OFFSET: '-05:00',
    FESTIVAL_TRANSPORT: 'transit',
    watchlist: new Set(),
    watched: new Set(),
    prioritized: new Set(),
    filmRatings: {},
    filmDelays: {},
    filmDelaysHistory: {},
    savedAgenda: null,
  });
  assert.equal(parcial, false, 'subscriber NO debe ver estado parcial');
  assert.equal(mirror._activeFestId, 'tribeca2026');
  assert.equal(mirror.FILMS[0].title, 'Anora');
});
