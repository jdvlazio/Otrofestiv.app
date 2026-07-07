// QA — _cloudGuardSkip: la decisión del boot-load multi-dispositivo (F0).
//
// Contexto (7 jul 2026, prerrequisito Apple Watch F0): el plan del usuario ya
// sincroniza a Supabase (user_festival_state). El gap era que un usuario firmado
// que REABRE la app no bajaba la nube (solo al firmar) → multi-dispositivo
// stale. El fix hace _cloudLoad({guard:true}) en cada loadFestival, con esta
// decisión pura protegiendo contra pisar datos:
//   - ediciones locales sin subir (dirty) no se pisan;
//   - datos locales ya frescos (cloud <= local synced) no se re-bajan.
//   - sign-in (guard=false) siempre aplica la nube (restaurar cuenta).
//
// _cloudGuardSkip es pura y sin deps → se extrae directo de persistence.js
// (como workerParity extrae de calc.js) y se evalúa en aislamiento.

const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const { extractFunction } = require('../lib/load-domain.js');

const SRC = fs.readFileSync(
  path.resolve(__dirname, '..', '..', 'src', 'controller', 'persistence.js'), 'utf8');
const fnSrc = extractFunction(SRC, '_cloudGuardSkip');
assert.ok(fnSrc, '_cloudGuardSkip no encontrada en persistence.js');
// eslint-disable-next-line no-eval
const _cloudGuardSkip = eval('(' + fnSrc + ')');

const T1 = '2026-07-05T10:00:00.000Z'; // más viejo
const T2 = '2026-07-05T12:00:00.000Z'; // más nuevo

// ── Sign-in (guard=false): la nube SIEMPRE gana ──────────────────────────────

test('sign-in (guard=false) nunca skip, aunque haya dirty o local fresco', () => {
  assert.strictEqual(_cloudGuardSkip({guard:false, dirty:true, cloudUpdatedAt:T1, localSyncedAt:T2}), false);
  assert.strictEqual(_cloudGuardSkip({guard:false, dirty:false, cloudUpdatedAt:T1, localSyncedAt:T2}), false);
});

// ── Boot (guard=true): protege datos locales ─────────────────────────────────

test('boot + ediciones locales sin subir (dirty) → SKIP (no pisar)', () => {
  assert.strictEqual(_cloudGuardSkip({guard:true, dirty:true, cloudUpdatedAt:T2, localSyncedAt:T1}), true);
});

test('boot + local ya al día (cloud == local synced) → SKIP', () => {
  assert.strictEqual(_cloudGuardSkip({guard:true, dirty:false, cloudUpdatedAt:T1, localSyncedAt:T1}), true);
});

test('boot + local más adelante que la nube → SKIP', () => {
  assert.strictEqual(_cloudGuardSkip({guard:true, dirty:false, cloudUpdatedAt:T1, localSyncedAt:T2}), true);
});

test('MULTI-DISPOSITIVO: boot + nube más nueva que local → APLICAR (no skip)', () => {
  // El caso que motiva F0: otro dispositivo cambió el plan; este está atrás.
  assert.strictEqual(_cloudGuardSkip({guard:true, dirty:false, cloudUpdatedAt:T2, localSyncedAt:T1}), false);
});

test('boot + primera vez (sin localSyncedAt) + no dirty → APLICAR', () => {
  assert.strictEqual(_cloudGuardSkip({guard:true, dirty:false, cloudUpdatedAt:T2, localSyncedAt:null}), false);
});

test('precedencia: dirty gana sobre timestamps (aunque la nube sea más nueva)', () => {
  // Ediciones locales sin subir NUNCA se pisan, ni por una nube más reciente.
  assert.strictEqual(_cloudGuardSkip({guard:true, dirty:true, cloudUpdatedAt:T2, localSyncedAt:T1}), true);
});

test('boot + nube sin updated_at (dato viejo) + no dirty + no local ts → APLICAR', () => {
  assert.strictEqual(_cloudGuardSkip({guard:true, dirty:false, cloudUpdatedAt:null, localSyncedAt:null}), false);
});
