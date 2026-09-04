// Unit tests for dayFullyPassed — extracted from index.html via load-domain.
// Contract (2 sep 2026): true si simNow() > el FIN de la última función del día
// (inicio + blockDuration). Antes era «último inicio + 10 min de gracia» e
// ignoraba la duración: con una función de 19:00 y 95 min, a las 19:30 el día
// ya estaba «pasado» mientras la cabecera decía «En curso · Termina en 1 h 05»
// (auditoría B-4). Las canceladas no cuentan.
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
      DEFAULT_DURATION_MIN: 90,   // blockDuration cae acá cuando el film no trae duration
      FESTIVAL_QA_MIN: 30,
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

test('antes de que TERMINE la última función → false (aunque ya haya empezado)', () => {
  // Última función: 20:00 Colombia, 95 min → termina 21:35 Colombia = 02:35 UTC Jun 6.
  // simNow: 01:30 UTC Jun 6 = 20:30 Colombia → empezó hace 30 min y sigue.
  // La regla vieja (inicio + 10) ya la daba por pasada a las 20:10.
  const { dayFullyPassed } = load({
    _simTime: '2026-06-06T01:30:00Z',
    FILMS: [{ day: 'MAR 21', time: '20:00', duration: '95 min' }],
  });
  assert.strictEqual(dayFullyPassed('MAR 21'), false);
});

test('después de que TERMINE la última función → true', () => {
  // Termina 21:35 Colombia = 02:35 UTC Jun 6. simNow: 02:40 UTC → pasó.
  const { dayFullyPassed } = load({
    _simTime: '2026-06-06T02:40:00Z',
    FILMS: [{ day: 'MAR 21', time: '20:00', duration: '95 min' }],
  });
  assert.strictEqual(dayFullyPassed('MAR 21'), true);
});

test('sin duration cae al default del festival, no a cero', () => {
  // 20:00 + 90 (DEFAULT_DURATION_MIN) = 21:30 Colombia = 02:30 UTC. A las 02:00 UTC sigue.
  const { dayFullyPassed } = load({
    _simTime: '2026-06-06T02:00:00Z',
    FILMS: [{ day: 'MAR 21', time: '20:00' }],
  });
  assert.strictEqual(dayFullyPassed('MAR 21'), false);
});

test('una función CANCELADA tarde no mantiene vivo el día', () => {
  // Viva: 18:00 × 60 → termina 19:00 Colombia = 00:00 UTC Jun 6.
  // Cancelada: 22:00 × 60 → terminaría 23:00, pero no va a ocurrir.
  // simNow: 00:30 UTC Jun 6 = 19:30 Colombia → la viva terminó → el día pasó.
  const { dayFullyPassed } = load({
    _simTime: '2026-06-06T00:30:00Z',
    FILMS: [
      { day: 'MAR 21', time: '18:00', duration: '60 min' },
      { day: 'MAR 21', time: '22:00', duration: '60 min', _cancelled: true },
    ],
  });
  assert.strictEqual(dayFullyPassed('MAR 21'), true);
});
