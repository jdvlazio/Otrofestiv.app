// Unit tests for simTodayStr — extracted from index.html via load-domain.
// Contract: YYYY-MM-DD local de simNow(). Usa TZ-less _simTime para que el
// local-date sea estable entre Colombia (UTC-5), UTC (CI) y otros runners
// — un string ISO sin TZ suffix se interpreta como LOCAL del runner, y
// getFullYear/getMonth/getDate sobre esa Date devuelven los mismos componentes
// que se pasaron al string.

const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

test('_simTime null → today local YYYY-MM-DD', () => {
  const { simTodayStr } = loadDomain({ globals: { _simTime: null } });
  const d = new Date();
  const expected = d.getFullYear() + '-' +
    String(d.getMonth() + 1).padStart(2, '0') + '-' +
    String(d.getDate()).padStart(2, '0');
  assert.strictEqual(simTodayStr(), expected);
});

test('_simTime mid-day → corresponding YYYY-MM-DD', () => {
  const { simTodayStr } = loadDomain({ globals: { _simTime: '2026-06-05T14:30:00' } });
  assert.strictEqual(simTodayStr(), '2026-06-05');
});

test('_simTime right before midnight local → still same day', () => {
  const { simTodayStr } = loadDomain({ globals: { _simTime: '2026-06-05T23:59:00' } });
  assert.strictEqual(simTodayStr(), '2026-06-05');
});
