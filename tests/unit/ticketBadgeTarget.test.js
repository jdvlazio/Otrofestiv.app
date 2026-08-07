// ticketBadgeTarget — qué badge de precio VALE LA PENA pintar en este festival.
//
// La app nació asumiendo que el cine se paga: por eso marcaba GRATIS, la
// excepción informativa. FICDEH 2026 invirtió la premisa — 313 de sus 384
// funciones son de entrada libre (81%). Marcar GRATIS ahí pinta 313 badges que
// no dicen nada y esconde las 71 que sí exigen una acción del asistente.
//
// La regla: el badge señala la MINORÍA. Si la mayoría es gratis → se marca
// CON BOLETA; si no → se sigue marcando GRATIS, exactamente como siempre.
// Umbral 50% (empate → 'paid', porque la duda se resuelve del lado de avisar
// que hay que pagar). Es un umbral explicable en una frase, a propósito.
//
// Solo aplica a `ticketing_model:'mixed'`. Un festival todo-pago o todo-libre
// ya se resuelve con su modelo declarado y no necesita badges por función.
const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

// n funciones reales, de las cuales `libres` con is_free. Se cuelan un `info`
// (evento sin función) y una función sin hora: no son funciones, no cuentan.
const films = (n, libres) => [
  { info: true, is_free: true },
  { day: '2026-08-14', is_free: true },
  ...Array.from({ length: n }, (_, i) => ({
    day: '2026-08-14', time: '18:00', is_free: i < libres,
  })),
];

const target = (modelo, n, libres) => loadDomain({
  functions: ['ticketBadgeTarget'],
  globals: {
    FESTIVAL_CONFIG: { f: { ticketing_model: modelo } },
    _activeFestId: 'f',
    FILMS: films(n, libres),
    // memo por festival: cada loadDomain trae el suyo, en blanco
    _tbCache: { id: null, val: null },
  },
}).ticketBadgeTarget();

test('mayoría gratis (FICDEH: 81%) → se marca la minoría CON BOLETA', () => {
  assert.strictEqual(target('mixed', 384, 313), 'paid');
});

test('gratis excepcional (Tercer Tiempo: 6%) → sigue marcándose GRATIS', () => {
  assert.strictEqual(target('mixed', 15, 1), 'free');
});

test('empate exacto → CON BOLETA (la duda avisa que hay que pagar)', () => {
  assert.strictEqual(target('mixed', 10, 5), 'paid');
});

test('sin funciones todavía → ningún badge (no se inventa una mayoría)', () => {
  assert.strictEqual(target('mixed', 0, 0), null);
});

test('festival no mixto → ningún badge por función', () => {
  assert.strictEqual(target('paid', 10, 9), null);
  assert.strictEqual(target(undefined, 10, 9), null);
});
