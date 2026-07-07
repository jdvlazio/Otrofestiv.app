// QA — _shouldApplyRealtimeRow: la decisión del sync del plan EN VIVO (F0.5).
//
// Contexto (7 jul 2026): el plan ya sube a Supabase, pero el otro dispositivo solo
// bajaba al REABRIR (boot-load) → inútil para festival en tiempo real / Apple Watch.
// F0.5 se suscribe a user_festival_state por Realtime y aplica la fila entrante. Esta
// decisión pura protege contra:
//   - el ECO de la propia escritura (rowUpdatedAt <= localSyncedAt) → no re-aplicar;
//   - filas viejas (mismo criterio de timestamp);
//   - pisar una edición local sin subir (dirty) → la nuestra gana y se sube.
//
// _shouldApplyRealtimeRow es pura y sin deps → se extrae directo de persistence.js
// (como _cloudGuardSkip) y se evalúa en aislamiento. Teeth por mutación abajo.

const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const { extractFunction } = require('../lib/load-domain.js');

const SRC = fs.readFileSync(
  path.resolve(__dirname, '..', '..', 'src', 'controller', 'persistence.js'), 'utf8');
const fnSrc = extractFunction(SRC, '_shouldApplyRealtimeRow');
assert.ok(fnSrc, '_shouldApplyRealtimeRow no encontrada en persistence.js');
// eslint-disable-next-line no-eval
const _shouldApplyRealtimeRow = eval('(' + fnSrc + ')');

const T1 = '2026-07-07T10:00:00.000Z'; // más viejo
const T2 = '2026-07-07T12:00:00.000Z'; // más nuevo

// ── Aplicar: el otro dispositivo escribió algo MÁS NUEVO que lo nuestro ───────
test('otro dispositivo, fila más nueva, sin dirty → APLICAR', () => {
  assert.strictEqual(
    _shouldApplyRealtimeRow({ rowUpdatedAt: T2, localSyncedAt: T1, dirty: false }), true);
});

test('primer evento sin localSyncedAt previo (null) → APLICAR', () => {
  assert.strictEqual(
    _shouldApplyRealtimeRow({ rowUpdatedAt: T2, localSyncedAt: null, dirty: false }), true);
});

// ── Eco de la propia escritura: rowUpdatedAt == localSyncedAt → NO aplicar ────
test('eco propio (rowUpdatedAt == localSyncedAt) → NO aplicar', () => {
  assert.strictEqual(
    _shouldApplyRealtimeRow({ rowUpdatedAt: T2, localSyncedAt: T2, dirty: false }), false);
});

// ── Fila vieja: rowUpdatedAt < localSyncedAt → NO aplicar ─────────────────────
test('fila más vieja que lo local sincronizado → NO aplicar', () => {
  assert.strictEqual(
    _shouldApplyRealtimeRow({ rowUpdatedAt: T1, localSyncedAt: T2, dirty: false }), false);
});

// ── Edición local pendiente (dirty) → NO pisar, aunque la fila sea más nueva ──
test('dirty (edición local sin subir) → NO aplicar aunque la nube sea más nueva', () => {
  assert.strictEqual(
    _shouldApplyRealtimeRow({ rowUpdatedAt: T2, localSyncedAt: T1, dirty: true }), false);
});

// ── Sin timestamp entrante → NO aplicar (defensivo) ──────────────────────────
test('rowUpdatedAt ausente → NO aplicar', () => {
  assert.strictEqual(
    _shouldApplyRealtimeRow({ rowUpdatedAt: null, localSyncedAt: T1, dirty: false }), false);
});

// ── Teeth por mutación — cada guard debe matar al menos un caso ───────────────
// Si alguien borra `if(dirty) return false;` → el caso dirty pasaría a true (rompe).
// Si borra el check de timestamp → el eco propio pasaría a true (rompe).
// Si borra `if(!rowUpdatedAt) return false;` → null pasaría el <= y devolvería true.
test('matriz completa de teeth', () => {
  const M = _shouldApplyRealtimeRow;
  // dirty domina sobre "más nuevo"
  assert.strictEqual(M({ rowUpdatedAt: T2, localSyncedAt: T1, dirty: true }), false);
  // timestamp domina el eco
  assert.strictEqual(M({ rowUpdatedAt: T1, localSyncedAt: T1, dirty: false }), false);
  // camino feliz sigue vivo
  assert.strictEqual(M({ rowUpdatedAt: T2, localSyncedAt: T1, dirty: false }), true);
});
