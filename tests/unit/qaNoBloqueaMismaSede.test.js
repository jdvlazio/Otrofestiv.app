// El Q&A solo compromete el tiempo cuando salir cuesta (decisión de Juan, 30 jul 2026).
// Es OPCIONAL y sus +30 min son ESTIMACIÓN: en la MISMA sede el fin duro es el de
// las películas (blockDuration) y el Q&A queda como advertencia; con TRASLADO de
// por medio sigue contando entero (variables incontrolables — no comprometerse).
//
// El caso que lo destapó — FINCA jue 13, mismo Cine York:
//   18:00 función compartida (106+5, con Q&A) → películas 19:51, Q&A 20:21
//   20:30 Ziki → 39 min entre películas (OK) · 9 min tras el Q&A (<15 buffer)
// La app la excluía por el estimado; el festival programó para que se pudiera.

const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

const { screensConflict, screensConflictReason } = loadDomain({
  functions: ['toMin', 'parseDur', 'blockDuration', 'durationForTravel', '_resolveVenue', 'effectiveDuration',
              'venueTravelMins', 'travelMins', 'screensConflict', 'screensConflictReason', '_cityOf'],
  globals: {
    FESTIVAL_BUFFER: 15,
    FESTIVAL_TRANSPORT: 'transit',
    FESTIVAL_CONFIG: { test: { venues: {
      'Cine York': { short: 'Cine York', lat: -34.51, lng: -58.48 },
      'Cacodelphia': { short: 'Cacodelphia', lat: -34.60, lng: -58.38 },
    } } },
    _activeFestId: 'test',
    DEFAULT_DURATION_MIN: 90,
  },
});

const DAY = '2026-08-13';
// la función compartida, tal como la sella el loader (slot con Q&A)
const FUNCION = { day: DAY, time: '18:00', duration: '106 min', venue: 'Cine York',
                  has_qa: true, _slotKey: 'k', _slotDur: 111, _slotMin: 141 };

test('MISMA sede: el Q&A no bloquea — Ziki entra (el caso real)', () => {
  const ziki = { day: DAY, time: '20:30', duration: '12 min', venue: 'Cine York' };
  assert.strictEqual(screensConflict(FUNCION, ziki), false);
  assert.strictEqual(screensConflictReason(FUNCION, ziki), null);
});

test('MISMA sede: sin Q&A la regla es idéntica a la de siempre (9 min reales < buffer → conflicto)', () => {
  // función que termina de verdad a las 20:21 (sin Q&A de por medio)
  const a = { day: DAY, time: '18:00', duration: '141 min', venue: 'Cine York' };
  const b = { day: DAY, time: '20:30', duration: '12 min', venue: 'Cine York' };
  assert.strictEqual(screensConflict(a, b), true);
});

test('CON traslado: el Q&A sigue contando entero → conflicto', () => {
  // mismas horas, otra sede: 39 min entre películas pero el Q&A + viaje no caben
  const ziki = { day: DAY, time: '20:30', duration: '12 min', venue: 'Cacodelphia' };
  assert.strictEqual(screensConflict(FUNCION, ziki), true);
  const r = screensConflictReason(FUNCION, ziki);
  assert.ok(r && r.kind !== null);
});

test('simetría: el orden de los argumentos no cambia el veredicto', () => {
  const ziki = { day: DAY, time: '20:30', duration: '12 min', venue: 'Cine York' };
  assert.strictEqual(screensConflict(ziki, FUNCION), false);
});

// ── isScreeningBlocked: el bloque de disponibilidad tampoco cuenta el Q&A ──────
const { isScreeningBlocked } = loadDomain({
  functions: ['toMin', 'parseDur', 'blockDuration', 'effectiveDuration', 'isScreeningBlocked'],
  globals: {
    FESTIVAL_BUFFER: 15, DEFAULT_DURATION_MIN: 90, _activeFestId: 'test',
    FESTIVAL_CONFIG: { test: { venues: {} } },
    availability: { '2026-08-13': { blocks: [{ from: '20:00', to: '23:00' }] } },
  },
});

test('disponibilidad: el Q&A opcional NO excluye la función (películas terminan antes del bloque)', () => {
  // film 18:00+106 → 19:51; Q&A estimado hasta 20:21 pisaría el bloque de 20:00.
  // Salir del Q&A no cuesta nada → la función entra.
  const f = { day: '2026-08-13', time: '18:00', duration: '106 min', has_qa: true };
  assert.strictEqual(isScreeningBlocked(f), false);
});

test('disponibilidad: si las PELÍCULAS pisan el bloque, sigue excluida', () => {
  const f = { day: '2026-08-13', time: '19:00', duration: '106 min', has_qa: false }; // → 20:46
  assert.strictEqual(isScreeningBlocked(f), true);
});
