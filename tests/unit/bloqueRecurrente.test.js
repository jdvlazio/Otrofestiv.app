// EL INVARIANTE del taller multi-día: en el plan están TODAS sus sesiones, o ninguna.
//
// Un taller de varios días se toma entero — quien se inscribe va a todas las
// sesiones. Un plan con «1 de 2» no es medio taller: es un plan que miente sobre
// un compromiso que el usuario nunca tomó.
//
// verifyPlan NO podía cazarlo, y ese era el hueco real (más que el botón): su
// chequeo de duplicado trata las repeticiones del título como legítimas, que es
// justo el permiso que otorga `is_recurring`. Y el schedule por sí solo no sabe
// cuántas sesiones tiene el taller — eso vive en el catálogo.
const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

const D = () => loadDomain({ functions: ['verifyPlan', 'screensConflict', 'screeningPassed', 'sameEntry',
  'toMin', 'parseDur', 'effectiveDuration', 'blockDuration', 'durationForTravel', 'travelMins',
  'venueTravelMins', '_resolveVenue', 'screeningEndMin', 'screeningEndDate', '_cityOf'],
  globals: { FESTIVAL_CONFIG: { f: { venues: {} } }, _activeFestId: 'f',
             FESTIVAL_BUFFER: 15, FESTIVAL_TRANSPORT: 'driving', SIM_TIME: null } });

const ses = (day, time) => ({ _title: 'Taller de Guion', title: 'Taller de Guion',
  day, time, venue: 'Sala', duration: '120 min', day_order: Number(day.slice(-2)), is_recurring: true });
// el taller tiene TRES sesiones en el catálogo
const CATALOGO = [ses('2026-05-14', '10:00 AM'), ses('2026-05-15', '10:00 AM'), ses('2026-05-17', '10:00 AM')];

test('las 3 sesiones en el plan → válido (y NO es duplicado)', () => {
  const r = D().verifyPlan(CATALOGO, { catalog: CATALOGO });
  assert.strictEqual(r.ok, true, JSON.stringify(r.violations));
});

test('1 de 3 → bloque incompleto', () => {
  const r = D().verifyPlan([CATALOGO[0]], { catalog: CATALOGO });
  const v = r.violations.find(x => x.kind === 'bloque-incompleto');
  assert.ok(v, 'debe detectarlo: ' + JSON.stringify(r.violations));
  assert.strictEqual(v.tiene, 1);
  assert.strictEqual(v.necesita, 3);
});

test('ninguna sesión → válido: no tomarlo es una opción legítima', () => {
  const r = D().verifyPlan([], { catalog: CATALOGO });
  assert.strictEqual(r.ok, true);
});

test('sin catálogo no se verifica — las llamadas viejas no cambian', () => {
  const r = D().verifyPlan([CATALOGO[0]]);
  assert.ok(!r.violations.some(x => x.kind === 'bloque-incompleto'));
});

test('una obra normal en DOS funciones ya NO es duplicado (doctrina 26 ago)', () => {
  // Antes, repetir el título bastaba para ser duplicado, e is_recurring era el
  // permiso que salvaba a los talleres. Ese permiso ya no hace falta: `duplicado`
  // es por identidad de entrada, y dos funciones distintas son dos entradas.
  const normal = { _title: 'Bojayá', title: 'Bojayá', day: '2026-05-14', time: '10:00 AM',
                   venue: 'Sala', duration: '90 min', day_order: 14 };
  const r = D().verifyPlan([normal, { ...normal, day: '2026-05-15', day_order: 15 }], { catalog: [] });
  assert.ok(!r.violations.some(x => x.kind === 'duplicado'));
});

test('la MISMA función repetida sigue siendo duplicado, con o sin is_recurring', () => {
  const normal = { _title: 'Bojayá', title: 'Bojayá', day: '2026-05-14', time: '10:00 AM',
                   venue: 'Sala', duration: '90 min', day_order: 14 };
  const r = D().verifyPlan([normal, { ...normal }], { catalog: [] });
  assert.ok(r.violations.some(x => x.kind === 'duplicado'));
  // el permiso viejo de is_recurring ya no puede tapar una entrada repetida
  const t = { ...normal, is_recurring: true };
  const r2 = D().verifyPlan([t, { ...t }], { catalog: [] });
  assert.ok(r2.violations.some(x => x.kind === 'duplicado'));
});
