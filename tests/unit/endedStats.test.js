// Unit tests for _endedStats — extracted from index.html via load-domain.
// Contract: stats post-festival sobre `watched` y `savedAgenda`.
// Solo películas regulares cuentan en totalWatched/pendingRatings
// (excluye is_cortos y type==='event').

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

test('cortos and events excluded from totalWatched/pendingRatings', () => {
  const { _endedStats } = load({
    FILMS: [
      { title: 'Regular', is_cortos: false, type: 'film' },
      { title: 'Cortos Program', is_cortos: true },
      { title: 'Workshop', type: 'event' },
    ],
    watched: new Set(['Regular', 'Cortos Program', 'Workshop']),
  });
  assert.deepStrictEqual(
    _endedStats(),
    { totalWatched: 1, totalPlanned: 0, pendingRatings: 1 }
  );
});
