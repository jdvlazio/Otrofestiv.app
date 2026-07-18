// Unit tests for _endedStats — extracted from index.html via load-domain.
// Contract (modelo por-obra del Diario, 17 jul 2026): un programa visto cuenta
// por sus OBRAS (film_list) en totalWatched/pendingRatings; films regulares
// cuentan 1; eventos (type==='event') no cuentan.

const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

function load(opts) {
  return loadDomain({
    globals: {
      FILMS: opts.FILMS || [],
      watched: opts.watched || new Set(),
      savedAgenda: opts.savedAgenda ?? null,
      filmRatings: opts.filmRatings || {},
    },
  });
}

test('empty watched and no agenda → 0/0/0', () => {
  const { _endedStats } = load({});
  assert.deepStrictEqual(
    _endedStats(),
    { totalWatched: 0, totalPlanned: 0, pendingRatings: 0 }
  );
});

test('2 regular films watched, 1 rated → totalWatched=2, pendingRatings=1', () => {
  const { _endedStats } = load({
    FILMS: [{ title: 'F1' }, { title: 'F2' }],
    watched: new Set(['F1', 'F2']),
    filmRatings: { F1: 5 },
  });
  assert.deepStrictEqual(
    _endedStats(),
    { totalWatched: 2, totalPlanned: 0, pendingRatings: 1 }
  );
});

test('savedAgenda with 3 screenings → totalPlanned=3', () => {
  const { _endedStats } = load({
    savedAgenda: { schedule: [{}, {}, {}] },
  });
  assert.deepStrictEqual(
    _endedStats(),
    { totalWatched: 0, totalPlanned: 3, pendingRatings: 0 }
  );
});

test('programa cuenta por sus OBRAS; eventos excluidos (modelo Diario)', () => {
  const { _endedStats } = load({
    FILMS: [
      { title: 'Regular', is_cortos: false, type: 'film' },
      { title: 'Cortos Program', is_cortos: true, film_list: [
        { title: 'Obra A' }, { title: 'Obra B' }, { title: 'Obra C' },
      ] },
      { title: 'Workshop', type: 'event' },
    ],
    watched: new Set(['Regular', 'Cortos Program', 'Workshop']),
    filmRatings: { 'Obra A': 5 },
  });
  // Regular (sin calificar) = 1/1 · programa = 3 obras, 1 calificada → 3/2 · evento = 0
  assert.deepStrictEqual(
    _endedStats(),
    { totalWatched: 4, totalPlanned: 0, pendingRatings: 3 }
  );
});
