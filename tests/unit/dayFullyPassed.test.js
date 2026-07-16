// Unit tests for dayFullyPassed — extracted from index.html via load-domain.
// Contract: true si simNow() > lastFilm.time del día + 10 min grace.
// Falsa si el day no existe en FESTIVAL_DATES.
// Día SIN films: no hay última función que mirar → pasó cuando terminó su FECHA
// (23:59 del día). El contrato viejo ("sin films → false" SIEMPRE) era un bug: un día
// vacío nunca se atenuaba y se colaba como "primer día futuro" en la navegación.
//
// Para evitar el comportamiento lex de Array.reduce sobre f.time strings
// (e.g., "9:00 AM" > "10:00 AM" lex pero no chronologically), los tests
// usan un único film por día — el reduce queda trivial.

const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

function load(opts) {
  return loadDomain({
    globals: {
      _simTime: opts._simTime,
      FESTIVAL_END: new Date('2099-01-01'),
      FESTIVAL_DATES: opts.FESTIVAL_DATES || { 'MAR 21': '2026-06-05' },
      FILMS: opts.FILMS || [],
      TZ_OFFSET: '-05:00',
    },
  });
}

test('day not in FESTIVAL_DATES → false', () => {
  const { dayFullyPassed } = load({
    _simTime: '2026-06-05T23:00:00Z',
    FILMS: [{ day: 'MAR 21', time: '20:00' }],
  });
  assert.strictEqual(dayFullyPassed('UNKNOWN_DAY'), false);
});

test('día SIN films, la fecha aún no termina → false', () => {
  // simNow: 23:00 UTC Jun 5 = 18:00 Colombia del MISMO día → el día no terminó.
  const { dayFullyPassed } = load({
    _simTime: '2026-06-05T23:00:00Z',
    FILMS: [],
  });
  assert.strictEqual(dayFullyPassed('MAR 21'), false);
});

test('día SIN films, la fecha YA pasó → true (bug: día vacío nunca se atenuaba)', () => {
  // El día 2026-06-05 termina 23:59 Colombia = 04:59 UTC Jun 6.
  // simNow: 06:00 UTC Jun 6 → la fecha ya terminó → pasó, aunque no tuviera programación.
  const { dayFullyPassed } = load({
    _simTime: '2026-06-06T06:00:00Z',
    FILMS: [],
  });
  assert.strictEqual(dayFullyPassed('MAR 21'), true);
});

test('simNow before last film + 10min grace → false', () => {
  // Last film: 20:00 Colombia = 01:00 UTC next day; grace → 01:10 UTC Jun 6
  // simNow: 00:00 UTC Jun 6 → before grace → false
  const { dayFullyPassed } = load({
    _simTime: '2026-06-06T00:00:00Z',
    FILMS: [{ day: 'MAR 21', time: '20:00' }],
  });
  assert.strictEqual(dayFullyPassed('MAR 21'), false);
});

test('simNow after last film + 10min grace → true', () => {
  // Last film: 20:00 Colombia = 01:00 UTC next day; grace → 01:10 UTC Jun 6
  // simNow: 02:00 UTC Jun 6 → after grace → true
  const { dayFullyPassed } = load({
    _simTime: '2026-06-06T02:00:00Z',
    FILMS: [{ day: 'MAR 21', time: '20:00' }],
  });
  assert.strictEqual(dayFullyPassed('MAR 21'), true);
});
