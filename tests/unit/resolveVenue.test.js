// Unit tests for _resolveVenue — extracted from index.html via load-domain.
// Contract: name + venues → venue object or {short: name} fallback.
// Pure: no globals read. Match order: exact → case-sensitive startsWith/includes
// → case-insensitive startsWith/includes, longest key first.

const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

const { _resolveVenue } = loadDomain();

test('exact match returns the venue object', () => {
  const venues = { 'Sala A': { short: 'A', lat: 1, lng: 2 } };
  assert.deepStrictEqual(_resolveVenue('Sala A', venues), { short: 'A', lat: 1, lng: 2 });
});

test('matches by case-sensitive prefix', () => {
  // Canonical example: "CC Caribe Plaza — Sala 2" resolves to "CC Caribe Plaza".
  const venues = { 'CC Caribe Plaza': { short: 'CC' } };
  assert.deepStrictEqual(
    _resolveVenue('CC Caribe Plaza — Sala 2', venues),
    { short: 'CC' }
  );
});

test('matches by case-insensitive substring (includes branch)', () => {
  // Key has different casing AND is not a prefix of name — exercises the
  // `nl.includes(kLower)` branch specifically (not startsWith, not exact).
  const venues = { 'Cinema Central': { short: 'CC' } };
  assert.deepStrictEqual(
    _resolveVenue('sala vip — Cinema central', venues),
    { short: 'CC' }
  );
});

test('longest matching key wins when multiple keys would match', () => {
  // Both "Sala A" and "Sala A Mejorada" are prefixes of the input. The
  // longest-first sort guarantees "Sala A Mejorada" wins → determinism.
  const venues = {
    'Sala A': { short: 'short-A' },
    'Sala A Mejorada': { short: 'long-A' },
  };
  assert.deepStrictEqual(
    _resolveVenue('Sala A Mejorada — Centro', venues),
    { short: 'long-A' }
  );
});

test('empty venues object returns {short: name} fallback', () => {
  assert.deepStrictEqual(_resolveVenue('Sala A', {}), { short: 'Sala A' });
});

test('empty name returns {short: ""} regardless of venues', () => {
  assert.deepStrictEqual(
    _resolveVenue('', { 'Sala A': { short: 'A' } }),
    { short: '' }
  );
});
