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

// 18 ago (Juan): la cuenta pierde los SUMANDOS — «21:15 se entiende cuando la
// función dice 21:00», y esa hora vive ahora en la fila, no en la frase.
// Queda la CAUSA + el veredicto, con la ~ mudada al total (era de los sumandos
// que desaparecieron): sugerimos, no predecimos.
test("'ajustado' → la causa (cambio de sala) y la llegada estimada", () => {
  const h = H.conflictAccount(A, B, { kind: 'ajustado', gap: 1, bFirst: false });
  assert.match(h, /Después de.*cambiando de sala/s); // ancla temporal + causa
  assert.match(h, /~<b>17:14<\/b>/);           // 16:59 + 15, marcado como estimado
  assert.doesNotMatch(h, /15 min entre salas|→/); // sin sumandos ni flecha
  assert.doesNotMatch(h, /no te daría el tiempo|no llegás/); // sin veredicto en palabras
});

// 17 ago 2026 — la rama de viaje pasó de frase a CADENA ARITMÉTICA: el margen es
// un sumando más y el total se compara solo con la hora de inicio. Ya no hay
// verbo de llegada ni veredicto en palabras, así que la doctrina del modo se
// cumple de otra forma: lo ESTIMADO lleva `~` (Q&A, viaje) y lo que es política
// nuestra (el margen) no. Motivo del cambio: la cuenta omitía el buffer que
// screensConflict exige, y una función EXCLUIDA se explicaba con «te quedarían
// N min» — la rama de «sí llegás». Ver T73.
test("'viaje' sin Q&A → la causa y el total, con el margen ya adentro", () => {
  const h = H.conflictAccount({ ...A, time: '16:00' }, { ...B, time: '19:00' },
    { kind: 'viaje', travel: 95, gap: 91, bFirst: false });
  assert.match(h, /Después de.*con el viaje/s); // ancla temporal + causa
  assert.match(h, /~<b>19:19<\/b>/);           // 17:29 + 95 + 15, todo el margen adentro
  assert.doesNotMatch(h, /viaje ~95|margen 15 min|→|empieza/); // sin sumandos
  assert.doesNotMatch(h, /no te daría el tiempo|te quedarían/); // sin veredicto
});

test("'viaje' con Q&A → el Q&A se NOMBRA como causa y ya está sumado", () => {
  const h = H.conflictAccount({ ...A, time: '16:00', has_qa: true }, { ...B, time: '19:00' },
    { kind: 'viaje', travel: 65, gap: 91, bFirst: false });
  assert.match(h, /Después de.*Q&A y viaje/s); // ancla temporal + las dos causas
  assert.match(h, /~<b>19:19<\/b>/);       // 17:29 + 30 + 65 + 15, ya adentro
  assert.doesNotMatch(h, /Q&A ~30|\+ viaje/); // sin enumerar los sumandos
});

// Este caso —llegás antes de la hora pero sin el margen— era el que producía
// «te quedarían 6 min» sobre una función EXCLUIDA. Ahora la cadena lo muestra
// como lo que es: 19:09 contra 19:00.
test("'viaje' al filo → el total supera el inicio aunque la llegada no", () => {
  const h = H.conflictAccount({ ...A, time: '16:00' }, { ...B, time: '19:00' },
    { kind: 'viaje', travel: 85, gap: 91, bFirst: false });
  assert.match(h, /19:09/);            // 17:29 + 85 + 15 → pasa de las 19:00
  assert.doesNotMatch(h, /te quedarían/);
});

// Choque que existe SOLO por el Q&A: la alternativa va en la misma moneda (la
// hora a la que llegarías saliendo al final de la película), no en una frase.
test("qaOnly → la cadena cierra con la hora sin el Q&A", () => {
  const h = H.conflictAccount({ ...A, time: '16:00', has_qa: true }, { ...B, time: '19:00' },
    { kind: 'viaje', travel: 65, gap: 91, bFirst: false, qaOnly: true });
  assert.match(h, /sin el Q&A, .*18:49/); // 17:29 + 65 + 15, sin los 30 del Q&A
});

test("bFirst → la frase se ordena por quién termina primero", () => {
  const h = H.conflictAccount(A, { ...B, time: '13:00' },
    { kind: 'ajustado', gap: 1, bFirst: true });
  assert.match(h, /Después de.*Three black men/s); // b termina primero → abre la frase
});

test("'solape' y 'ciudad' → sin frase (título/copy propios)", () => {
  assert.equal(H.conflictAccount(A, B, { kind: 'solape' }), '');
  assert.equal(H.conflictAccount(A, B, { kind: 'ciudad', city: 'X', cityFrom: 'Y' }), '');
  assert.equal(H.conflictAccount(A, B, null), '');
});
