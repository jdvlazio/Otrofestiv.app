// Unit tests for isScreeningBlocked — extracted from index.html via load-domain.
// Contract: true si el screening cae dentro de un block de availability.
// Boundary: solapamiento estricto — un screening que termina exactamente
// cuando empieza el block NO se considera bloqueado.

const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

test('availability[s.day] undefined → false', () => {
  const { isScreeningBlocked } = loadDomain({
    globals: { availability: {}, DEFAULT_DURATION_MIN: 90 },
  });
  assert.strictEqual(
    isScreeningBlocked({ day: 'MAR 21', time: '10:00 AM', duration: '90 min' }),
    false
  );
});

test('block that overlaps screening → true', () => {
  // Screening 10:30 AM (630) + 90 min → ends 12:00 PM (720).
  // Block 11:00 AM (660) — 12:00 PM (720). Overlap:
  //   sStart=630 < bTo=720  ✓
  //   sEnd=720   > bFrom=660 ✓
  // → blocked.
  const { isScreeningBlocked } = loadDomain({
    globals: {
      availability: { 'MAR 21': { blocks: [{ from: '11:00 AM', to: '12:00 PM' }] } },
      DEFAULT_DURATION_MIN: 90,
    },
  });
  assert.strictEqual(
    isScreeningBlocked({ day: 'MAR 21', time: '10:30 AM', duration: '90 min' }),
    true
  );
});

test('block adjacent to screening end (boundary) → false', () => {
  // Screening 10:30 AM (630) + 90 min → ends 12:00 PM (720).
  // Block 12:00 PM (720) — 1:00 PM (780). Boundary case:
  //   sStart=630 < bTo=780  ✓
  //   sEnd=720   > bFrom=720 ✗ (strict >)
  // → NOT blocked (screening ends exactly when block starts).
  const { isScreeningBlocked } = loadDomain({
    globals: {
      availability: { 'MAR 21': { blocks: [{ from: '12:00 PM', to: '1:00 PM' }] } },
      DEFAULT_DURATION_MIN: 90,
    },
  });
  assert.strictEqual(
    isScreeningBlocked({ day: 'MAR 21', time: '10:30 AM', duration: '90 min' }),
    false
  );
});
