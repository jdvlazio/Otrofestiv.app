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
      notWatched: opts.notWatched || new Set(),
      _simTime: opts._simTime ?? null,
      FESTIVAL_DATES: opts.FESTIVAL_DATES || {},
      TZ_OFFSET: opts.TZ_OFFSET ?? '-05:00',
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

// Los eventos SÍ cuentan desde el 17 ago 2026: son lo que el Diario muestra, y
// el chip del Diario ya los contaba mientras esta cuenta los descartaba — dos
// números para lo mismo (medido con FICDEH: 2 contra 3). Calificar sigue siendo
// solo de lo calificable: un taller no tiene estrellas.
test('programa cuenta por sus OBRAS; el evento suma pero no se califica', () => {
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
  // Regular (sin calificar) = 1/1 · programa = 3 obras, 1 calificada → 3/2 ·
  // evento = 1 visto, 0 pendientes de calificar
  assert.deepStrictEqual(
    _endedStats(),
    { totalWatched: 5, totalPlanned: 0, pendingRatings: 3 }
  );
});

// ── Vista ASUMIDA (Diario Luz, 18 ago): una función del plan que YA terminó
// cuenta como vista sin marcarla; notWatched la excluye; una futura no cuenta. ──
const _FILMS_ASUM = [
  { title: 'Pasada', duration: '60 min' },
  { title: 'Futura', duration: '60 min' },
];
const _AGENDA_ASUM = { schedule: [
  { _title: 'Pasada', day: 'VIE 15', time: '10:00', duration: '60 min' },
  { _title: 'Futura', day: 'VIE 15', time: '20:00', duration: '60 min' },
] };
const _ASUM_OPTS = {
  FILMS: _FILMS_ASUM, savedAgenda: _AGENDA_ASUM,
  FESTIVAL_DATES: { 'VIE 15': '2026-08-15' },
  _simTime: '2026-08-15T15:00:00-05:00',
};

test('vista asumida: la pasada del plan cuenta sin marcarla; la futura no', () => {
  const { _endedStats } = load(_ASUM_OPTS);
  assert.strictEqual(_endedStats().totalWatched, 1);
});

test('notWatched niega la asunción: «no la vi» no cuenta', () => {
  const { _endedStats } = load({ ..._ASUM_OPTS, notWatched: new Set(['Pasada']) });
  assert.strictEqual(_endedStats().totalWatched, 0);
});

test('effectiveWatched = explícito ∪ asumido − negado', () => {
  const { effectiveWatched } = load({ ..._ASUM_OPTS, watched: new Set(['Futura']) });
  assert.deepStrictEqual([...effectiveWatched()].sort(), ['Futura', 'Pasada']);
});

