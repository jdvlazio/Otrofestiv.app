// Unit tests del onboarding: generate-config.js EXIGE --tz (±HH:MM). Antes tenía
// default '-05:00' → olvidar --tz metía un festival fuera de Colombia en hora de
// Bogotá, corriendo todo el programa sin error (prep Argentina, 21 jul 2026). El
// script solo imprime a stdout (no escribe archivos) → seguro correrlo en test.

const test = require('node:test');
const assert = require('node:assert');
const { spawnSync } = require('node:child_process');
const path = require('node:path');

const SCRIPT = path.join(__dirname, '../../scripts/generate-config.js');
const BASE = [
  '--id', 'argentina2026', '--name', 'Festival de Cine Argentina',
  '--fullname', 'Festival Internacional de Cine de Argentina', '--short', 'ARG',
  '--city', 'Buenos Aires', '--start', '2026-07-28', '--days', '5',
  '--storage', 'argentina2026_',
];

function run(extra) {
  return spawnSync('node', [SCRIPT, ...BASE, ...extra], { encoding: 'utf8' });
}

test('sin --tz → error (exit 1) que lo nombra', () => {
  const r = run([]);
  assert.strictEqual(r.status, 1, 'debe salir con código 1');
  assert.match(r.stderr, /--tz/, 'el error menciona --tz');
});

test('--tz con formato inválido → error (exit 1)', () => {
  const r = run(['--tz', 'GMT-3']);
  assert.strictEqual(r.status, 1, 'formato malo debe fallar');
  assert.match(r.stderr, /HH:MM|±/, 'el error explica el formato');
});

test('--tz -03:00 válido → OK (exit 0) y escribe el offset de Argentina', () => {
  const r = run(['--tz', '-03:00']);
  assert.strictEqual(r.status, 0, 'con --tz válido debe generar');
  assert.match(r.stdout, /timezoneOffset:'-03:00'/, 'el bloque lleva el offset de Argentina');
});
