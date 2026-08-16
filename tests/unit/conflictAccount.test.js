// Unit test — conflictAccount (src/view/helpers.js), la cuenta del veredicto
// (QA de ojos frescos, 15 ago 2026). Guard de: (1) los números salen de las
// MISMAS reglas que screensConflict (blockDuration, Q&A solo con traslado,
// buffer), (2) la doctrina del modo — fines de película en indicativo,
// llegada/margen en condicional («llegarías», «no te daría», «te quedarían»),
// (3) solo habla en 'ajustado'/'viaje' — 'solape' y 'ciudad' devuelven ''.
// Carga: import ESM directo con _lang seteado (patrón delayConsensusBadge).

const { test, before } = require('node:test');
const assert = require('node:assert');

let H;
before(async () => { globalThis._lang = 'es'; globalThis.FILMS = []; H = await import('../../src/view/helpers.js'); });

const A = { title: 'Por una gota de leche', time: '15:30', duration: '89 min' }; // termina 16:59
const B = { title: 'Three black men', time: '17:00', duration: '80 min' };

test("'ajustado' → fin + buffer + llegada + inicio, veredicto en condicional", () => {
  const h = H.conflictAccount(A, B, { kind: 'ajustado', gap: 1, bFirst: false });
  assert.match(h, /16:59/);            // fin de película (dato)
  assert.match(h, /15 min entre salas/); // FESTIVAL_BUFFER visible
  assert.match(h, /17:14/);            // 16:59 + 15
  assert.match(h, /17:00/);            // inicio de la otra
  assert.match(h, /no te daría el tiempo/); // condicional, nunca «no llegás»
  assert.doesNotMatch(h, /no llegás/);
});

test("'viaje' sin Q&A → llegada estimada en condicional («llegarías»)", () => {
  const h = H.conflictAccount({ ...A, time: '16:00' }, { ...B, time: '19:00' },
    { kind: 'viaje', travel: 95, gap: 91, bFirst: false });
  assert.match(h, /17:29/);      // 16:00 + 89 min
  assert.match(h, /llegarías/);  // estimación → condicional
  assert.match(h, /19:04/);      // 17:29 + 95
  assert.match(h, /no te daría el tiempo/); // 19:04 > 19:00
});

test("'viaje' con Q&A → el Q&A se muestra como sumando aparte", () => {
  const h = H.conflictAccount({ ...A, time: '16:00', has_qa: true }, { ...B, time: '19:00' },
    { kind: 'viaje', travel: 65, gap: 91, bFirst: false });
  assert.match(h, /Q&A ~30 min/);
  assert.match(h, /17:59/);      // 17:29 + 30
  assert.match(h, /19:04/);      // 17:59 + 65
});

test("'viaje' que sí alcanza pero al filo → dice los minutos, no sentencia", () => {
  const h = H.conflictAccount({ ...A, time: '16:00' }, { ...B, time: '19:00' },
    { kind: 'viaje', travel: 85, gap: 91, bFirst: false });
  assert.match(h, /18:54/);            // llegada 17:29 + 85
  assert.match(h, /te quedarían 6 min/); // margen mostrado, en condicional
  assert.doesNotMatch(h, /no te daría/);
});

test("bFirst → la frase se ordena por quién termina primero", () => {
  const h = H.conflictAccount(A, { ...B, time: '13:00' },
    { kind: 'ajustado', gap: 1, bFirst: true });
  assert.match(h, /Three black men.*termina/); // b termina primero → abre la frase
});

test("'solape' y 'ciudad' → sin frase (título/copy propios)", () => {
  assert.equal(H.conflictAccount(A, B, { kind: 'solape' }), '');
  assert.equal(H.conflictAccount(A, B, { kind: 'ciudad', city: 'X', cityFrom: 'Y' }), '');
  assert.equal(H.conflictAccount(A, B, null), '');
});
