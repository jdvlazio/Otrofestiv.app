// syncScheduleWithCatalog — el plan guarda la elección, el catálogo manda el resto.
//
// Bug real (31 jul 2026, FINCA): un plan guardado ANTES del anclaje de función
// conservaba la copia congelada (sin _slotDur, con duración vieja) y Mi Plan
// calculaba fines y el aviso de Q&A sobre esa mentira: "18:05 de fin" y
// "~115 min" donde el catálogo vivo dice "19:51" y "~9 min". La corrección es
// estructural: al hidratar (loader / nube) cada entrada se re-deriva de su
// función viva y SOLO sobreviven los campos propios de la entrada.

const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

// sameEntry es el dueño único de la identidad de entrada; syncScheduleWithCatalog
// la consume, así que el harness tiene que cargar las dos.
const { syncScheduleWithCatalog } = loadDomain({ functions: ['sameEntry', 'syncScheduleWithCatalog'], globals: {} });

const CATALOGO = [
  { title: 'Propiedad privada', day: 'D1', time: '18:00', venue: 'York', duration: '106 min',
    has_qa: true, _slotKey: 'D1|18:00|York|', _slotDur: 111, _slotMin: 141 },
  { title: 'Mi casa', day: 'D1', time: '18:00', venue: 'York', duration: '5 min',
    _slotKey: 'D1|18:00|York|', _slotDur: 111, _slotMin: 141 },
  { title: 'Ziki', day: 'D1', time: '20:30', venue: 'York', duration: '12 min',
    _slotKey: 'D1|20:30|York|', _slotDur: 91, _slotMin: 121 },
];

test('la entrada congelada se re-deriva de la función viva (el bug de la captura)', () => {
  const viejo = [
    { _title: 'Propiedad privada', title: 'Propiedad privada', day: 'D1', time: '18:00', venue: 'York', duration: '106 min', has_qa: true },
    { _title: 'Mi casa', title: 'Mi casa', day: 'D1', time: '18:00', venue: 'York', duration: '5 min' },
  ];
  const out = syncScheduleWithCatalog(viejo, CATALOGO);
  assert.strictEqual(out[0]._slotDur, 111, 'la entrada sin anclaje debe heredar el _slotDur vivo');
  assert.strictEqual(out[1]._slotDur, 111);
  assert.strictEqual(out[0]._title, 'Propiedad privada');
});

test('una corrección de duración del festival llega al plan', () => {
  const out = syncScheduleWithCatalog(
    [{ _title: 'Ziki', title: 'Ziki', day: 'D1', time: '20:30', venue: 'York', duration: '2 min' }],
    CATALOGO);
  assert.strictEqual(out[0].duration, '12 min');
});

test('sin match exacto (título+día+hora) la entrada queda INTACTA — es territorio de avisos', () => {
  const e = { _title: 'Ziki', title: 'Ziki', day: 'D1', time: '19:00', venue: 'York', duration: '2 min' };
  const out = syncScheduleWithCatalog([e], CATALOGO);
  assert.deepStrictEqual(out[0], e);
});

test('los campos propios de la entrada sobreviven; los congelados no', () => {
  const out = syncScheduleWithCatalog(
    [{ _title: 'Ziki', title: 'Ziki', day: 'D1', time: '20:30', _squeezed: true, _basuraVieja: 1 }],
    CATALOGO);
  assert.strictEqual(out[0]._squeezed, true);
  assert.strictEqual(out[0]._basuraVieja, undefined, 'la copia vieja no debe dejar residuos');
});

test('idempotente: dos corridas = una', () => {
  const una = syncScheduleWithCatalog(
    [{ _title: 'Ziki', title: 'Ziki', day: 'D1', time: '20:30', duration: '2 min' }], CATALOGO);
  assert.deepStrictEqual(syncScheduleWithCatalog(una, CATALOGO), una);
});

test('plan vacío o null pasa de largo', () => {
  assert.strictEqual(syncScheduleWithCatalog(null, CATALOGO), null);
  assert.deepStrictEqual(syncScheduleWithCatalog([], CATALOGO), []);
});
