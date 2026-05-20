// Unit tests for screensConflict — extracted from index.html via load-domain.
// Contract: returns true when two screenings (a, b) cannot both be attended.
// Reads FESTIVAL_BUFFER, FESTIVAL_TRANSPORT, FESTIVAL_CONFIG[_activeFestId].venues
// as globals; calls effectiveDuration (which uses DEFAULT_DURATION_MIN via parseDur).
//
// Fixture: two venues ~2.22 km apart → 15 min travel under transit speed.

const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

const { screensConflict } = loadDomain({
  globals: {
    FESTIVAL_BUFFER: 15,
    FESTIVAL_TRANSPORT: 'transit',
    FESTIVAL_CONFIG: {
      test: {
        venues: {
          'Sala A': { short: 'A', lat: 6.25, lng: -75.57 },
          'Sala B': { short: 'B', lat: 6.27, lng: -75.57 }, // 2.22 km north → 15 min travel
        },
      },
    },
    _activeFestId: 'test',
    DEFAULT_DURATION_MIN: 90,
  },
});

const sameDay = 'MAR 21';

test('different days → no conflict', () => {
  const a = { day: 'MAR 21', time: '10:00 AM', duration: '90 min', venue: 'Sala A' };
  const b = { day: 'MIÉ 22', time: '10:00 AM', duration: '90 min', venue: 'Sala A' };
  assert.strictEqual(screensConflict(a, b), false);
});

test('same day, direct overlap → conflict', () => {
  // a: 10:00–11:30, b: 11:00–12:30 → overlap
  const a = { day: sameDay, time: '10:00 AM', duration: '90 min', venue: 'Sala A' };
  const b = { day: sameDay, time: '11:00 AM', duration: '90 min', venue: 'Sala A' };
  assert.strictEqual(screensConflict(a, b), true);
});

test('same venue, gap > buffer → no conflict', () => {
  // a: 10:00–11:00, b: 11:30 → gap 30 min, minGap 15 → no conflict
  const a = { day: sameDay, time: '10:00 AM', duration: '60 min', venue: 'Sala A' };
  const b = { day: sameDay, time: '11:30 AM', duration: '60 min', venue: 'Sala A' };
  assert.strictEqual(screensConflict(a, b), false);
});

test('same venue, gap < buffer → conflict', () => {
  // a: 10:00–11:00, b: 11:10 → gap 10 min, minGap 15 → conflict
  const a = { day: sameDay, time: '10:00 AM', duration: '60 min', venue: 'Sala A' };
  const b = { day: sameDay, time: '11:10 AM', duration: '60 min', venue: 'Sala A' };
  assert.strictEqual(screensConflict(a, b), true);
});

test('distant venues, gap > buffer but < buffer+travel → conflict', () => {
  // a Sala A: 10:00–11:00, b Sala B: 11:20 → gap 20 min, travel 15 min,
  // minGap = max(15, 15+15) = 30 → conflict. (Same venue, same times: 20 ≥ 15 → no conflict.)
  const a = { day: sameDay, time: '10:00 AM', duration: '60 min', venue: 'Sala A' };
  const b = { day: sameDay, time: '11:20 AM', duration: '60 min', venue: 'Sala B' };
  assert.strictEqual(screensConflict(a, b), true);
});

test('has_qa extends a → conflict that would not exist without Q&A', () => {
  // a 10:00 + 90 min + 30 min Q&A ends 12:00. b starts 12:10 → gap 10 → conflict.
  // Without has_qa, gap would be 40 min → no conflict. Q&A is what flips it.
  const a = { day: sameDay, time: '10:00 AM', duration: '90 min', has_qa: true, venue: 'Sala A' };
  const b = { day: sameDay, time: '12:10 PM', duration: '60 min', venue: 'Sala A' };
  assert.strictEqual(screensConflict(a, b), true);
});

test('reversed argument order returns the same result (commutative)', () => {
  const a = { day: sameDay, time: '10:00 AM', duration: '90 min', venue: 'Sala A' };
  const b = { day: sameDay, time: '11:00 AM', duration: '90 min', venue: 'Sala A' };
  assert.strictEqual(screensConflict(b, a), screensConflict(a, b));
  assert.strictEqual(screensConflict(b, a), true);
});
