// Unit tests for _festDate — extracted from index.html via load-domain.
// Contract: construye Date con TZ_OFFSET explícito.

const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

test('TZ_OFFSET=-05:00 → 14:30 local Colombia = 19:30 UTC', () => {
  const { _festDate } = loadDomain({ globals: { TZ_OFFSET: '-05:00' } });
  const d = _festDate('2026-06-05', '14:30');
  assert.strictEqual(d.toISOString(), '2026-06-05T19:30:00.000Z');
});

test('different offset (-04:00) shifts UTC by 1 hour', () => {
  const { _festDate } = loadDomain({ globals: { TZ_OFFSET: '-04:00' } });
  const d = _festDate('2026-06-05', '14:30');
  assert.strictEqual(d.toISOString(), '2026-06-05T18:30:00.000Z');
});

test('midnight local: time="00:00" with -05:00 → 05:00 UTC', () => {
  const { _festDate } = loadDomain({ globals: { TZ_OFFSET: '-05:00' } });
  const d = _festDate('2026-06-05', '00:00');
  assert.strictEqual(d.toISOString(), '2026-06-05T05:00:00.000Z');
});
