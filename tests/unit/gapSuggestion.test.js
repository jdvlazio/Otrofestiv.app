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

// ── Alcanzabilidad (mismo criterio que screensConflict) — bug 17 jul 2026 ──────
// Dos sedes lejanas: cabe por TIEMPO pero NO por VIAJE. El "Cabe en tu hueco" no
// puede sugerir algo que no alcanzás a llegar desde la función anterior.
function loadWithVenues(opts) {
  return loadDomain({
    globals: {
      FILMS: opts.FILMS,
      watched: new Set(),
      savedAgenda: { schedule: [] },
      DEFAULT_DURATION_MIN: 90,
      FESTIVAL_BUFFER: 15,
      screeningPassed: () => false,
      _activeFestId: 'F',
      FESTIVAL_TRANSPORT: null, // → 12 km/h (auto)
      FESTIVAL_CONFIG: { F: { venues: {
        A: { lat: 4.6032463, lng: -74.06758, short: 'A' },   // Cinemateca
        B: { lat: 4.754983,  lng: -74.1126869, short: 'B' },  // CEFE (~17.5 km ≈ 90 min)
      } } },
    },
  });
}

test('cabe por tiempo pero el viaje no alcanza → excluido', () => {
  // lastDone en A termina a las 895 (14:55). Candidato en B empieza 960 (16:00) →
  // hueco de viaje 65 min < travel(90)+buffer(15)=105 → NO se puede sugerir.
  const f = { title: 'CORTOS', day: 'D', time: '16:00', duration: '105 min', venue: 'B' };
  const { _gapSuggestion } = loadWithVenues({ FILMS: [f] });
  const gap = _gapSuggestion('D', 895, 1200, { venue: 'A' }, { venue: 'A', time: '20:00' });
  assert.strictEqual(gap, null);
});

test('mismo hueco con margen de viaje suficiente → se sugiere', () => {
  // Candidato en B empieza 1050 (17:30): hueco de viaje 155 min ≥ 105 → OK.
  const f = { title: 'CORTOS', day: 'D', time: '17:30', duration: '60 min', venue: 'B' };
  const { _gapSuggestion } = loadWithVenues({ FILMS: [f] });
  const gap = _gapSuggestion('D', 895, 1300, { venue: 'A' }, { venue: 'A', time: '21:40' });
  assert.strictEqual(gap && gap.title, 'CORTOS');
});
