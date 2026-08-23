// metroArea — un festival cuyas ciudades son UNA sola área de traslado.
//
// La regla que esto matiza nació con FICDEH 2026, que corre en once ciudades a
// cientos de kilómetros: ahí travelMins —velocidad urbana— le pone 13 h a
// Bogotá→Ibagué, un número que no es confiable, así que la app se niega a
// estimar y dice la ciudad, que sí es un dato.
//
// Cinemancia 2026 es el caso contrario: seis municipios (Medellín, Bello,
// Itagüí, Envigado, Caldas, Copacabana) que son el Valle de Aburrá. Ir de uno a
// otro son minutos y la estimación urbana SÍ vale, así que decir «es en otra
// ciudad» informa MENOS que decir cuántos minutos faltan.
//
// Lo levantó Juan revisando el montaje: «este festival, a pesar de ser
// multiciudad, es en la misma área metropolitana».
const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

const FNS = ['screensConflict', 'screensConflictReason', 'toMin', 'parseDur',
  'effectiveDuration', 'blockDuration', 'durationForTravel', 'travelMins',
  'venueTravelMins', '_resolveVenue', '_cityOf', 'screeningEndMin'];

// Dos sedes en municipios distintos del área metropolitana, a 8 km.
const VENUES = {
  'Sala A - Medellín': { short: 'Sala A', city: 'Medellín', lat: 6.2447, lng: -75.5748 },
  'Sala B - Bello':    { short: 'Sala B', city: 'Bello',    lat: 6.3361, lng: -75.5665 },
};

// Dos funciones que CHOCAN: 90 min desde las 14:30 terminan 16:00, y la otra
// arranca a esa misma hora en otro municipio. Sin traslado ya no da.
const A = { title: 'A', day: '2026-09-04', time: '14:30', duration: '90 min', venue: 'Sala A - Medellín' };
const B = { title: 'B', day: '2026-09-04', time: '16:00', duration: '90 min', venue: 'Sala B - Bello'    };

const D = (metroArea) => loadDomain({
  functions: FNS,
  globals: {
    FESTIVAL_CONFIG: { c: { venues: VENUES, city: 'Valle de Aburrá', metroArea } },
    _activeFestId: 'c', FESTIVAL_BUFFER: 15, FESTIVAL_TRANSPORT: 'transit',
    DEFAULT_DURATION_MIN: 90,
  },
});

test('sin metroArea, la app NO estima entre ciudades — dice cuál es', () => {
  const d = D(undefined);
  assert.ok(d.screensConflict(A, B), 'las dos funciones chocan');
  const r = d.screensConflictReason(A, B);
  assert.strictEqual(r.kind, 'ciudad', 'el motivo es la ciudad, no el viaje');
  assert.strictEqual(r.cityFrom, 'Medellín');
  assert.strictEqual(r.city, 'Bello');
  assert.strictEqual(r.travel, undefined, 'y NO se compromete con minutos');
});

test('con metroArea, vuelve a estimar el viaje y da los minutos', () => {
  const d = D(true);
  assert.ok(d.screensConflict(A, B), 'el choque es el mismo: la bandera no lo crea ni lo borra');
  const r = d.screensConflictReason(A, B);
  assert.strictEqual(r.kind, 'viaje', 'ahora el motivo es el traslado');
  assert.ok(r.travel > 0, `y trae minutos concretos (${r.travel})`);
});

test('la bandera NO inventa ni borra choques — solo cambia la explicación', () => {
  // El choque lo decide screensConflict con travelMins (coordenadas), que nunca
  // miró la ciudad. Si esto se rompe, alguien metió la ciudad en el cálculo.
  assert.strictEqual(D(undefined).screensConflict(A, B), D(true).screensConflict(A, B));
});

test('metroArea solo aplica al festival que la declara', () => {
  // Mismo par de sedes, festival sin la bandera: se comporta como FICDEH.
  const d = D(false);
  assert.strictEqual(d.screensConflictReason(A, B).kind, 'ciudad');
});
