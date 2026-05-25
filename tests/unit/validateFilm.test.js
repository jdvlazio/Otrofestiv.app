// Unit tests for validateFilm (domain/film.js) — validación de datos pura.
// Contract: validateFilm(f, dayKeys, venues) → { valid, drop, errors[], warnings[] }.
//   drop=true → sin title (inutilizable). errors → day∉dayKeys / time inválido (keep).
//   warnings → section/venue/duration (keep + default). valid = !drop && !errors.

const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

// validateFilm es pura (solo usa sus args) → se extrae sola, sin globals.
const { validateFilm } = loadDomain({ functions: ['validateFilm'] });

const DAYS = ['2026-06-03', '2026-06-04'];
const VENUES = { 'BMCC': { short: 'BMCC' } };

test('film completo y válido → valid, sin drop/errors/warnings', () => {
  const r = validateFilm({ title: 'A', day: '2026-06-03', time: '10:30 AM', section: 'Gala', venue: 'BMCC', duration: '90 min' }, DAYS, VENUES);
  assert.strictEqual(r.valid, true);
  assert.strictEqual(r.drop, false);
  assert.deepStrictEqual(r.errors, []);
  assert.deepStrictEqual(r.warnings, []);
});

test('sin title → drop=true, valid=false', () => {
  const r = validateFilm({ day: '2026-06-03', time: '10:30 AM' }, DAYS, VENUES);
  assert.strictEqual(r.drop, true);
  assert.strictEqual(r.valid, false);
  assert.ok(r.errors.length > 0);
});

test('title vacío/whitespace/no-string → drop', () => {
  assert.strictEqual(validateFilm({ title: '   ' }, DAYS, VENUES).drop, true);
  assert.strictEqual(validateFilm({ title: 42 }, DAYS, VENUES).drop, true);
  assert.strictEqual(validateFilm(null, DAYS, VENUES).drop, true);
});

test('day fuera de dayKeys → error, NO drop (se conserva)', () => {
  const r = validateFilm({ title: 'A', day: '2026-12-31', time: '10:30 AM', section: 'X' }, DAYS, VENUES);
  assert.strictEqual(r.drop, false);
  assert.strictEqual(r.valid, false);
  assert.ok(r.errors.some(e => e.includes('day')));
});

test('time faltante en film no-event → error (medianoche)', () => {
  const r = validateFilm({ title: 'A', day: '2026-06-03', section: 'X' }, DAYS, VENUES);
  assert.ok(r.errors.some(e => e.includes('time')));
  assert.strictEqual(r.drop, false);
});

test('event sin time → NO genera error de time', () => {
  const r = validateFilm({ title: 'E', type: 'event', day: '2026-06-03', section: 'X' }, DAYS, VENUES);
  assert.ok(!r.errors.some(e => e.includes('time')));
});

test('section faltante → warning, sigue válido (no error)', () => {
  const r = validateFilm({ title: 'A', day: '2026-06-03', time: '10:30 AM' }, DAYS, VENUES);
  assert.strictEqual(r.valid, true);
  assert.ok(r.warnings.some(w => w.includes('section')));
});

test('venue inexistente en venues{} → warning (se conserva)', () => {
  const r = validateFilm({ title: 'A', day: '2026-06-03', time: '10:30 AM', section: 'X', venue: 'Desconocido' }, DAYS, VENUES);
  assert.ok(r.warnings.some(w => w.includes('venue')));
  assert.strictEqual(r.valid, true);
});

test('duration no-numérica → warning (parseDur defaultea igual)', () => {
  const r = validateFilm({ title: 'A', day: '2026-06-03', time: '10:30 AM', section: 'X', duration: 'dos horas' }, DAYS, VENUES);
  assert.ok(r.warnings.some(w => w.includes('duration')));
  assert.strictEqual(r.valid, true);
});
