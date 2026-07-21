// Unit tests de zona horaria — la app ancla "ahora" y las funciones a la hora del
// FESTIVAL (cfg.timezoneOffset), no del dispositivo. Prep del festival de Argentina
// (-03:00, 21 jul 2026). _festDate es el punto único: lo reusan share, notificaciones
// (recordatorios), screeningPassed, dayFullyPassed. Si _festDate respeta el offset,
// todo lo demás hereda la corrección.

const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

function load(tz) {
  return loadDomain({
    globals: {
      TZ_OFFSET: tz,
      _simTime: undefined,
      FESTIVAL_DATES: { 'MAR 21': '2026-07-28' },
      FESTIVAL_END: new Date('2099-01-01'),
    },
  });
}

test('_festDate — Argentina (-03:00): 20:00 local = 23:00 UTC', () => {
  const { _festDate } = load('-03:00');
  assert.strictEqual(_festDate('2026-07-28', '20:00').toISOString(), '2026-07-28T23:00:00.000Z');
});

test('_festDate — Colombia (-05:00): 20:00 local = 01:00 UTC (día siguiente)', () => {
  const { _festDate } = load('-05:00');
  assert.strictEqual(_festDate('2026-07-28', '20:00').toISOString(), '2026-07-29T01:00:00.000Z');
});

test('_festDate — la MISMA hora de pared en dos zonas da instantes distintos (2h)', () => {
  const ar = load('-03:00')._festDate('2026-07-28', '20:00').getTime();
  const co = load('-05:00')._festDate('2026-07-28', '20:00').getTime();
  assert.strictEqual((co - ar) / 3600000, 2, 'Colombia va 2h detrás de Argentina');
});

test('_festDate — normaliza AM/PM (8:00 PM == 20:00) en zona Argentina', () => {
  const { _festDate } = load('-03:00');
  assert.strictEqual(
    _festDate('2026-07-28', '8:00 PM').toISOString(),
    _festDate('2026-07-28', '20:00').toISOString()
  );
});

// El recordatorio nativo es _festDate(fecha, hora) - 30min: absoluto, correcto en
// cualquier zona del usuario. Antes se construía el Date sin offset (hora del
// dispositivo). Este test fija el instante esperado para Argentina.
test('recordatorio (funcion -30min) en Argentina — instante absoluto correcto', () => {
  const { _festDate } = load('-03:00');
  const notifyMs = _festDate('2026-07-28', '20:00').getTime() - 30 * 60000;
  assert.strictEqual(new Date(notifyMs).toISOString(), '2026-07-28T22:30:00.000Z'); // 19:30 ART
});

test('simTodayStr — "hoy" es el día EN HORA DEL FESTIVAL (Argentina)', () => {
  // 2026-07-28 23:30 UTC = 20:30 en Argentina (-03:00) → hoy = 2026-07-28.
  // El mismo instante en Colombia (-05:00) = 18:30 → también 2026-07-28. Elegimos
  // un instante donde SÍ difieren: 2026-07-29 02:30 UTC = 23:30 ART (día 28) vs
  // 21:30 COT (día 28)… usamos 2026-07-29 01:30 UTC = 22:30 ART (28) / 20:30 COT (28).
  // Para separar día: 2026-07-29 02:30 UTC → ART 23:30 (28), pero UTC ya es 29.
  const { simTodayStr } = loadDomain({
    globals: {
      TZ_OFFSET: '-03:00',
      _simTime: '2026-07-29T02:30:00Z', // 23:30 del 28 en Argentina
      FESTIVAL_DATES: {},
      FESTIVAL_END: new Date('2099-01-01'),
    },
  });
  assert.strictEqual(simTodayStr(), '2026-07-28', 'sigue siendo el 28 en hora argentina, aunque UTC ya sea 29');
});
