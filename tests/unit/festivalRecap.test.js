// festivalRecap — «Tu festival» (#1055, F1). Regla de oro: ningún número que no
// se pueda afirmar. Casos del criterio de aceptación: 0 vistas; solo eventos;
// programa de cortos; duración faltante (<80 % → sin horas); multiciudad; empate
// en el top 3; y vista sin función conocida → días/sedes null.
const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

const VENUES = { 'Cinemateca': { short: 'Cinemateca', city: 'Bogotá' }, 'Colombo': { short: 'Colombo', city: 'Bogotá' },
  'Teatro Cali': { short: 'Teatro Cali', city: 'Cali' } };
const PELI = (title, extra = {}) => ({ title, day: '2026-10-09', time: '18:00', venue: 'Cinemateca', duration: '90 min', country: 'Colombia', ...extra });
const FILMS = [
  PELI('A'), PELI('B', { day: '2026-10-10', venue: 'Colombo', country: 'Francia, Alemania', duration: '120 min' }),
  PELI('C', { day: '2026-10-11', venue: 'Teatro Cali', time: '16:00' }),
  { title: 'Taller', type: 'event', day: '2026-10-10', time: '10:00', venue: 'Colombo' },
  { title: 'Programa 1', is_cortos: true, day: '2026-10-11', time: '20:00', venue: 'Cinemateca', duration: '60 min',
    film_list: [{ title: 'c1', country: 'Perú' }, { title: 'c2', country: 'Chile' }] },
];
function load(o = {}) {
  return loadDomain({ globals: {
    FILMS: o.FILMS || FILMS, watched: o.watched || new Set(), notWatched: new Set(),
    savedAgenda: o.savedAgenda ?? null, watchedMeta: o.watchedMeta || {}, filmRatings: o.filmRatings || {},
    FESTIVAL_CONFIG: { f: { venues: VENUES } }, _activeFestId: 'f', _simTime: null, FESTIVAL_DATES: {}, TZ_OFFSET: '-05:00',
  } });
}
const meta = (...ts) => Object.fromEntries(ts.map(t => { const f = FILMS.find(x => x.title === t); return [t, { day: f.day, time: f.time, venue: f.venue }]; }));

test('0 vistas → todo en cero y nada afirmado', () => {
  const r = load().festivalRecap();
  assert.deepStrictEqual([r.actividades, r.dias, r.sedes, r.horas, r.paises, r.top], [0, 0, 0, null, null, []]);
});

test('solo eventos: cuentan como actividades, sin horas ni países ni estrellas', () => {
  const r = load({ watched: new Set(['Taller']), watchedMeta: meta('Taller') }).festivalRecap();
  assert.strictEqual(r.eventos, 1); assert.strictEqual(r.peliculas, 0);
  assert.strictEqual(r.dias, 1); assert.strictEqual(r.sedes, 1);
  assert.strictEqual(r.horas, null); assert.strictEqual(r.paises, null); assert.deepStrictEqual(r.top, []);
});

test('programa de cortos: cuenta por obra, la duración es del programa, países de cada corto', () => {
  const r = load({ watched: new Set(['Programa 1']), watchedMeta: meta('Programa 1'), filmRatings: { c2: 5 } }).festivalRecap();
  assert.strictEqual(r.peliculas, 2);
  assert.strictEqual(r.horas, 1);
  assert.strictEqual(r.paises, 2);
  assert.deepStrictEqual(r.top.map(o => o.title), ['c2']);
});

test('duración faltante en más del 20 % → sin horas (no se estima)', () => {
  const sinDur = FILMS.map(f => f.title === 'B' ? { ...f, duration: undefined } : f);
  const r = load({ FILMS: sinDur, watched: new Set(['A', 'B']), watchedMeta: meta('A', 'B') }).festivalRecap();
  assert.strictEqual(r.horas, null, '1 de 2 sin duración = 50 %');
  const r2 = load({ watched: new Set(['A', 'B']), watchedMeta: meta('A', 'B') }).festivalRecap();
  assert.strictEqual(r2.horas, 4, '90 + 120 = 210 min ≈ 4 h, redondeado');
});

test('vista sin función conocida: cuenta, pero días y sedes no se afirman', () => {
  const r = load({ watched: new Set(['A', 'B']), watchedMeta: meta('A') }).festivalRecap();
  assert.strictEqual(r.peliculas, 2);
  assert.strictEqual(r.dias, null); assert.strictEqual(r.sedes, null);
});

test('el Plan manda sobre la meta, y multiciudad cuenta ciudades aparte', () => {
  const sa = { schedule: [{ _title: 'C', day: '2026-10-11', time: '16:00', venue: 'Teatro Cali' }] };
  const r = load({ watched: new Set(['A', 'C']), savedAgenda: sa, watchedMeta: meta('A') }).festivalRecap();
  assert.strictEqual(r.dias, 2); assert.strictEqual(r.sedes, 2); assert.strictEqual(r.ciudades, 2);
  assert.strictEqual(r.paises, 1);
});

test('top 3: por estrellas; empate → orden cronológico; sin estrellas no entra', () => {
  const r = load({ watched: new Set(['A', 'B', 'C', 'Programa 1']), watchedMeta: meta('A', 'B', 'C', 'Programa 1'),
    filmRatings: { A: 4, B: 5, C: 4, c1: 0 } }).festivalRecap();
  assert.deepStrictEqual(r.top.map(o => o.title), ['B', 'A', 'C'], 'B(5) primero; A y C empatan a 4 y gana la más temprana');
});
