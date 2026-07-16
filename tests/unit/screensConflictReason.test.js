// Unit tests for screensConflictReason — el MOTIVO del conflicto (domain/schedule.js).
//
// POR QUÉ EXISTE: "Choca con X" era el mismo mensaje para dos problemas distintos
// (horas que se pisan vs. sedes lejos) → el usuario buscaba un solape inexistente.
// Estos tests congelan la distinción que alimenta la convención 🕐 reloj / 🗺️ ruta.
//
// Contrato: null si no hay conflicto (delega en screensConflict, no duplica la regla).
//   solape   → las horas se pisan (DATO).
//   viaje    → no se pisan, sedes distintas, hueco < viaje+buffer (ESTIMACIÓN).
//   ajustado → misma sede, hueco < buffer (sin viaje de por medio).

const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

const { screensConflictReason } = loadDomain({
  functions: ['toMin', 'parseDur', '_resolveVenue', 'effectiveDuration', 'venueTravelMins',
              'travelMins', 'screensConflict', 'screensConflictReason'],
  globals: {
    FESTIVAL_BUFFER: 15,
    FESTIVAL_TRANSPORT: 'transit',
    FESTIVAL_CONFIG: {
      test: {
        venues: {
          // Sedes REALES de TT — el caso que reportó Juan (17,6 km → 105 min en transit)
          'Cinemateca Sala 2': { short: 'Cinemateca', lat: 4.6032463, lng: -74.06758 },
          'CEFE Fontanar del Río': { short: 'Fontanar', lat: 4.754983, lng: -74.1126869 },
        },
      },
    },
    _activeFestId: 'test',
    DEFAULT_DURATION_MIN: 90,
  },
});

const DAY = '2026-07-17';

test('sin conflicto → null', () => {
  // Misma sede, 3 h de hueco → entra de sobra.
  const a = { day: DAY, time: '13:00', duration: '115 min', venue: 'Cinemateca Sala 2' };
  const b = { day: DAY, time: '18:00', duration: '100 min', venue: 'Cinemateca Sala 2' };
  assert.strictEqual(screensConflictReason(a, b), null);
});

test('las horas se pisan → solape (sin minutos: es un dato, no una estimación)', () => {
  const a = { day: DAY, time: '13:00', duration: '115 min', venue: 'Cinemateca Sala 2' };
  const b = { day: DAY, time: '14:00', duration: '100 min', venue: 'Cinemateca Sala 2' };
  assert.deepStrictEqual(screensConflictReason(a, b), { kind: 'solape' });
});

test('CASO REAL TT — Contra Todo → Raíces del juego: viaje, NO solape', () => {
  // Contra Todo 13:00–14:55 (Cinemateca) · Raíces 16:00 (Fontanar): 65 min de hueco,
  // 17,6 km de por medio → ~105 min de viaje. No se pisan, pero no da el tiempo.
  const contraTodo = { day: DAY, time: '13:00', duration: '115 min', venue: 'Cinemateca Sala 2' };
  const raices     = { day: DAY, time: '16:00', duration: '105 min', venue: 'CEFE Fontanar del Río' };
  const r = screensConflictReason(raices, contraTodo);
  assert.strictEqual(r.kind, 'viaje', 'es desplazamiento, no solape');
  assert.strictEqual(r.gap, 65, 'hueco real entre 14:55 y 16:00');
  assert.strictEqual(r.travel, 105, '17,6 km a 10 km/h (transit) → 105 min');
  assert.strictEqual(r.bFirst, true, 'Contra Todo es el anterior → copy "desde"');
});

test('dirección inversa → bFirst false (copy "hasta")', () => {
  const contraTodo = { day: DAY, time: '13:00', duration: '115 min', venue: 'Cinemateca Sala 2' };
  const raices     = { day: DAY, time: '16:00', duration: '105 min', venue: 'CEFE Fontanar del Río' };
  const r = screensConflictReason(contraTodo, raices); // ahora el "otro" es el posterior
  assert.strictEqual(r.kind, 'viaje');
  assert.strictEqual(r.bFirst, false, 'Raíces es el posterior → copy "hasta"');
});

test('misma sede, hueco menor al buffer → ajustado (sin viaje)', () => {
  // 13:00–14:55 y 15:00 en la MISMA sede: 5 min de hueco < 15 de buffer.
  const a = { day: DAY, time: '13:00', duration: '115 min', venue: 'Cinemateca Sala 2' };
  const b = { day: DAY, time: '15:00', duration: '90 min', venue: 'Cinemateca Sala 2' };
  const r = screensConflictReason(b, a);
  assert.strictEqual(r.kind, 'ajustado', 'misma sede → no es problema de viaje');
  assert.strictEqual(r.gap, 5);
  assert.strictEqual(r.travel, undefined, 'ajustado no reporta viaje');
});

test('días distintos → null (delega en screensConflict)', () => {
  const a = { day: DAY, time: '13:00', duration: '115 min', venue: 'Cinemateca Sala 2' };
  const b = { day: '2026-07-18', time: '13:30', duration: '90 min', venue: 'CEFE Fontanar del Río' };
  assert.strictEqual(screensConflictReason(a, b), null);
});
