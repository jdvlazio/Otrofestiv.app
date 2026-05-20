// Unit tests for effectiveDuration — extracted from index.html via load-domain.
// Contract: f.duration is a parseable string ("90 min", "~95 min"); has_qa
// boolean. Returns parseDur(f.duration) + 30 if has_qa. DEFAULT_DURATION_MIN
// (injected as global) is the fallback when duration is missing.

const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

const { effectiveDuration } = loadDomain({
  globals: { DEFAULT_DURATION_MIN: 90 },
});

test('parses "90 min" → 90', () => {
  assert.strictEqual(effectiveDuration({ duration: '90 min' }), 90);
});

test('adds 30 min when has_qa is true', () => {
  assert.strictEqual(effectiveDuration({ duration: '90 min', has_qa: true }), 120);
});

test('null duration falls back to DEFAULT_DURATION_MIN', () => {
  assert.strictEqual(effectiveDuration({ duration: null }), 90);
});

test('"~95 min" prefix is stripped → 95', () => {
  assert.strictEqual(effectiveDuration({ duration: '~95 min' }), 95);
});

test('null/undefined film → DEFAULT_DURATION_MIN, no Q&A bonus', () => {
  assert.strictEqual(effectiveDuration(null), 90);
  assert.strictEqual(effectiveDuration(undefined), 90);
});
