// Unit tests for _gapSuggestion — extracted from index.html.
// Contract: busca una film del día que quepa en el hueco entre dos funciones
// planeadas. Excluye films de otro día, ya watched, ya en savedAgenda, o con
// `screeningPassed=true`. Slack +10 min en gapToMin.
//
// `screeningPassed` se stubea a () => false en estos tests — no es el
// comportamiento bajo prueba aquí (queda implícitamente cubierto por la
// integración a través de _getFestivalPhase tests).

const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

function load(opts) {
  return loadDomain({
    globals: {
      FILMS: opts.FILMS || [],
      watched: opts.watched || new Set(),
      savedAgenda: opts.savedAgenda || { schedule: [] },
      DEFAULT_DURATION_MIN: 90,
      screeningPassed: () => false,
    },
  });
}

test('no films match todayDay → null', () => {
  const { _gapSuggestion } = load({
    FILMS: [
      { title: 'F1', day: 'OTHER DAY', time: '10:30 AM', duration: '60 min' },
    ],
  });
  assert.strictEqual(_gapSuggestion('MAR 21', 600, 720), null);
});

test('one film fits in the gap → returns that film', () => {
  // gap: 600 (10:00 AM) → 720 (12:00 PM), +10 slack on end.
  // f1: starts 630 (10:30 AM), 60 min → ends 690. Fits.
  const f1 = { title: 'F1', day: 'MAR 21', time: '10:30 AM', duration: '60 min' };
  const { _gapSuggestion } = load({ FILMS: [f1] });
  assert.strictEqual(_gapSuggestion('MAR 21', 600, 720), f1);
});

test('film already watched → excluded → null', () => {
  const f1 = { title: 'F1', day: 'MAR 21', time: '10:30 AM', duration: '60 min' };
  const { _gapSuggestion } = load({
    FILMS: [f1],
    watched: new Set(['F1']),
  });
  assert.strictEqual(_gapSuggestion('MAR 21', 600, 720), null);
});

test('film already in savedAgenda → excluded → null', () => {
  // savedAgenda entries usan `_title`, no `title` — replicado del código original.
  const f1 = { title: 'F1', day: 'MAR 21', time: '10:30 AM', duration: '60 min' };
  const { _gapSuggestion } = load({
    FILMS: [f1],
    savedAgenda: { schedule: [{ _title: 'F1' }] },
  });
  assert.strictEqual(_gapSuggestion('MAR 21', 600, 720), null);
});
