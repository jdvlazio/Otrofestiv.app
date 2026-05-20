// Unit tests for scoreFilm — extracted from index.html via load-domain.
// Contract: heurística aditiva. 4 factores: priority, screen scarcity,
// section uniqueness, long-form duration.
//
// Base test setup: FILMS=[{title:'F1', section:'Drama'}], 1 screening en Drama,
// short duration, not priority. Cada test varía un factor para aislar el delta.

const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

function setup(opts = {}) {
  return loadDomain({
    globals: {
      FILMS: opts.FILMS || [{ title: 'F1', section: 'Drama' }],
      DEFAULT_DURATION_MIN: 90,
    },
  });
}

test('base case: 1 screening + unique section + short + no priority → 55', () => {
  const { scoreFilm } = setup();
  // 1 screening: +40, unique section: +15, short dur: 0, no prio: 0
  assert.strictEqual(
    scoreFilm('F1', [{ section: 'Drama', duration: '90 min' }], false, ['F1']),
    55
  );
});

test('isPriority=true adds +100', () => {
  const { scoreFilm } = setup();
  assert.strictEqual(
    scoreFilm('F1', [{ section: 'Drama', duration: '90 min' }], true, ['F1']),
    155 // base 55 + priority 100
  );
});

test('2 screenings → +20 (vs 1 → +40, delta -20)', () => {
  const { scoreFilm } = setup();
  // 2 screenings: +20, unique: +15, short, no prio
  assert.strictEqual(
    scoreFilm('F1', [
      { section: 'Drama', duration: '90 min' },
      { section: 'Drama', duration: '90 min' },
    ], false, ['F1']),
    35 // 0 + 20 + 15 + 0
  );
});

test('sibling film in same section → no +15 bonus', () => {
  const { scoreFilm } = setup({
    FILMS: [
      { title: 'F1', section: 'Drama' },
      { title: 'F2', section: 'Drama' }, // sibling in Drama
    ],
  });
  // 1 screen: +40, NOT unique (F2 in same section): 0, short, no prio
  assert.strictEqual(
    scoreFilm('F1', [{ section: 'Drama', duration: '90 min' }], false, ['F1', 'F2']),
    40 // 0 + 40 + 0 + 0
  );
});

test('duration > 150 min adds +10', () => {
  const { scoreFilm } = setup();
  // 1 screen: +40, unique: +15, long (180): +10, no prio
  assert.strictEqual(
    scoreFilm('F1', [{ section: 'Drama', duration: '180 min' }], false, ['F1']),
    65 // 0 + 40 + 15 + 10
  );
});
