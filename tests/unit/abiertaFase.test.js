// Unit tests for abiertaFase — la FASE de una actividad ABIERTA (info:true,
// drop-in con ventana) respecto a un instante: 'antes' | 'abierta' | 'despues'.
//
// De dónde sale (7 sep 2026): la maratón fotográfica de SiembraFest, abierta de
// 8:00 a 18:00. Con «600 min» la tarjeta prometía diez horas de compromiso; sin
// duración la app la daba por pasada a las 8:10 y le inventaba «~90 min». La
// ventana es dato; lo que cambia es cómo se dice, y eso se decide por fase.

const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

const { abiertaFase } = loadDomain({
  globals: {
    TZ_OFFSET: '-05:00',        // _festDate ancla la hora al huso del festival
    DEFAULT_DURATION_MIN: 90,
    FESTIVAL_QA_MIN: 30,
    FESTIVAL_DATES: { '2026-09-13': '2026-09-13' },
  },
});

// La app fija el festival en Colombia (-05:00): 08:00 local = 13:00Z.
const at = h => new Date(`2026-09-13T${h}:00-05:00`);
const maraton = { info: true, day: '2026-09-13', time: '08:00', duration: '600 min' };

test('antes de la ventana → antes', () => {
  assert.strictEqual(abiertaFase(maraton, at('07:30')), 'antes');
});

test('dentro de la ventana → abierta, en los dos extremos', () => {
  assert.strictEqual(abiertaFase(maraton, at('08:00')), 'abierta');
  assert.strictEqual(abiertaFase(maraton, at('11:00')), 'abierta');
  assert.strictEqual(abiertaFase(maraton, at('18:00')), 'abierta');
});

test('pasada la ventana → despues', () => {
  assert.strictEqual(abiertaFase(maraton, at('18:01')), 'despues');
});

test('una función normal (sin info) no tiene fase de abierta', () => {
  assert.strictEqual(abiertaFase({ ...maraton, info: false }, at('11:00')), '');
  assert.strictEqual(abiertaFase(null, at('11:00')), '');
});

test('sin día conocido o sin hora → vacío, nunca una fase inventada', () => {
  assert.strictEqual(abiertaFase({ ...maraton, day: '2026-09-99' }, at('11:00')), '');
  assert.strictEqual(abiertaFase({ ...maraton, time: '' }, at('11:00')), '');
});
