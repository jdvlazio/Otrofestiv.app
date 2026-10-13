// venueMatches — el predicado ÚNICO del filtro de lugar (5 ago 2026).
// El nivel de ciudad (FICDEH: 11 ciudades / 131 sedes) necesitaba que "filtrar"
// pudiera significar una CIUDAD entera, no solo una sede. Antes cada superficie
// comparaba `vcfg(v).short===activeVenue` a mano en 8 sitios: agregar ciudad
// habría exigido tocarlos todos, y con el tiempo habrían divergido.
// Centinela: 'city:<Ciudad>'. 'all' pasa todo. Sin centinela, compara el short.
const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

const VENUES = {
  'Cinemateca de Bogotá': { short: 'Cinemateca de Bogotá', city: 'Bogotá' },
  'Cine Tonalá':          { short: 'Cine Tonalá',          city: 'Bogotá' },
  'Cinemateca de Tunja':  { short: 'Cinemateca de Tunja',  city: 'Tunja'  },
  'Sin ciudad':           { short: 'Sin ciudad' },
};
function load() {
  return loadDomain({
    functions: ['_resolveVenue', 'vcfg', '_satelites', 'filterCity', 'venueMatches', 'venueSelLabel'],
    globals: { FESTIVAL_CONFIG: { f: { venues: VENUES } }, _activeFestId: 'f',
               SEDE_SEP: String.fromCharCode(31) },
  });
}

test("'all' deja pasar todo", () => {
  const { venueMatches } = load();
  assert.strictEqual(venueMatches('Cinemateca de Bogotá', 'all'), true);
  assert.strictEqual(venueMatches('Sin ciudad', 'all'), true);
});

test('sede: compara el short (comportamiento de siempre)', () => {
  const { venueMatches } = load();
  assert.strictEqual(venueMatches('Cine Tonalá', 'Cine Tonalá'), true);
  assert.strictEqual(venueMatches('Cine Tonalá', 'Cinemateca de Tunja'), false);
});

test('ciudad: el centinela city: matchea TODAS sus sedes', () => {
  const { venueMatches } = load();
  assert.strictEqual(venueMatches('Cinemateca de Bogotá', 'city:Bogotá'), true);
  assert.strictEqual(venueMatches('Cine Tonalá', 'city:Bogotá'), true);
  assert.strictEqual(venueMatches('Cinemateca de Tunja', 'city:Bogotá'), false);
});

test('sede sin ciudad nunca entra en un filtro de ciudad', () => {
  const { venueMatches } = load();
  assert.strictEqual(venueMatches('Sin ciudad', 'city:Bogotá'), false);
});

test('venueSelLabel muestra la ciudad sin el centinela', () => {
  const { venueSelLabel } = load();
  assert.strictEqual(venueSelLabel('city:Bogotá'), 'Bogotá');
  assert.strictEqual(venueSelLabel('Cine Tonalá'), 'Cine Tonalá');
});

// ── Centinela 'sede:<Ciudad><SEP><short>' (9 ago 2026) ────────────────────────
// El short NO es único entre ciudades. En FICDEH hay dos «Cinema Local» (Bogotá y
// Cali) y dos «Alianza Francesa» (Barranquilla y Cartagena): filtrando solo por
// short, elegir la de Bogotá traía TAMBIÉN las 4 funciones de Cali, el conteo de la
// ciudad no cuadraba (135 en el nivel 1, 139 dentro) y la sede desaparecía de la
// lista de la segunda ciudad, absorbida por la primera.
//
// La clave es (ciudad, short) y NO la sede completa: dentro de una MISMA ciudad
// varias sedes comparten short a propósito — son las salas de un edificio, y quien
// elige el edificio las quiere todas. La ciudad separa; el short agrupa.
const CHOQUE = {
  'Cinema Local - Bogota': { short: 'Cinema Local', city: 'Bogota' },
  'Cinema Local - Cali':   { short: 'Cinema Local', city: 'Cali'   },
  'Cinemateca Sala 2':     { short: 'Cinemateca', city: 'Bogota' },
  'Cinemateca Sala 3':     { short: 'Cinemateca', city: 'Bogota' },
  'Sin ciudad':            { short: 'Sin ciudad' },
};
function loadChoque() {
  return loadDomain({
    functions: ['_resolveVenue', 'vcfg', '_satelites', 'filterCity', 'venueMatches', 'venueSelLabel'],
    globals: { FESTIVAL_CONFIG: { f: { venues: CHOQUE } }, _activeFestId: 'f',
               SEDE_SEP: String.fromCharCode(31) },
  });
}
// El separador se construye por CÓDIGO: un control literal en el fuente del test es
// invisible al revisar y se pierde en un copiar/pegar.
const SEP = String.fromCharCode(31);
const sede = (ciudad, short) => 'sede:' + ciudad + SEP + short;

test('sede: NO cruza ciudades aunque el short coincida', () => {
  const { venueMatches } = loadChoque();
  assert.strictEqual(venueMatches('Cinema Local - Bogota', sede('Bogota', 'Cinema Local')), true);
  assert.strictEqual(venueMatches('Cinema Local - Cali', sede('Bogota', 'Cinema Local')), false,
    'la sede de Cali se coló en el filtro de Bogota — es el bug de FICDEH');
  assert.strictEqual(venueMatches('Cinema Local - Cali', sede('Cali', 'Cinema Local')), true);
  assert.strictEqual(venueMatches('Cinema Local - Bogota', sede('Cali', 'Cinema Local')), false);
});

test('sede: agrupa las SALAS de un mismo edificio dentro de su ciudad', () => {
  const { venueMatches } = loadChoque();
  const sel = sede('Bogota', 'Cinemateca');
  assert.strictEqual(venueMatches('Cinemateca Sala 2', sel), true);
  assert.strictEqual(venueMatches('Cinemateca Sala 3', sel), true,
    'las salas del mismo edificio se separaron — quien elige el edificio las quiere todas');
});

test('sede: una sede sin ciudad se selecciona con ciudad vacia', () => {
  const { venueMatches } = loadChoque();
  assert.strictEqual(venueMatches('Sin ciudad', sede('', 'Sin ciudad')), true);
  assert.strictEqual(venueMatches('Cinema Local - Cali', sede('', 'Cinema Local')), false);
});

test('el short pelado (legado) sigue resolviendo — no rompe estado en vuelo', () => {
  const { venueMatches } = loadChoque();
  assert.strictEqual(venueMatches('Cinema Local - Bogota', 'Cinema Local'), true);
  assert.strictEqual(venueMatches('Cinema Local - Cali', 'Cinema Local'), true);
});

test('venueSelLabel muestra la sede, no el centinela', () => {
  const { venueSelLabel } = loadChoque();
  assert.strictEqual(venueSelLabel(sede('Bogota', 'Cinema Local')), 'Cinema Local');
  assert.strictEqual(venueSelLabel('city:Bogota'), 'Bogota');
  assert.strictEqual(venueSelLabel('Cine Tonala'), 'Cine Tonala');
});

// ── Municipios satélite (13 oct 2026, FICPA) ──────────────────────────────────
// 1 sola función y < 50 km de la ciudad principal → se integra a ella para
// filtrar y agrupar. Datos con la forma real de FICPA (Pasto + 3 municipios a
// 16–18 km con 1 función cada uno) y un control lejano tipo FICDEH.
function loadSat(films, venues) {
  return loadDomain({
    functions: ['_resolveVenue', 'vcfg', '_satelites', 'filterCity', 'venueMatches', 'festivalCities'],
    globals: { FESTIVAL_CONFIG: { p: { venues } }, _activeFestId: 'p', FILMS: films,
               SEDE_SEP: String.fromCharCode(31) },
  });
}
const PV = {
  'Teatro Pasto':  { short: 'Teatro Pasto', city: 'Pasto',     lat: 1.2136, lng: -77.2811 },
  'Parque Chacha': { short: 'Parque Chacha', city: 'Chachagüí', lat: 1.3570, lng: -77.2830 },
  'Teatro Lejos':  { short: 'Teatro Lejos', city: 'Cali',      lat: 3.4516, lng: -76.5320 },
};
const fn = (venue, n) => Array.from({ length: n }, (_, i) => ({ title: venue + i, venue, day: '2026-10-14' }));

test('satélite: municipio con 1 función a 16 km se integra a la principal', () => {
  const { festivalCities, filterCity, venueMatches } = loadSat([...fn('Teatro Pasto', 48), ...fn('Parque Chacha', 1)], PV);
  assert.deepStrictEqual(festivalCities([...fn('Teatro Pasto', 48), ...fn('Parque Chacha', 1)]).map(c => c.name), ['Pasto']);
  assert.strictEqual(filterCity('Parque Chacha'), 'Pasto');
  assert.strictEqual(venueMatches('Parque Chacha', 'city:Pasto'), true);
});

test('satélite: con 2 funciones sigue siendo ciudad aparte (Cinemancia)', () => {
  const films = [...fn('Teatro Pasto', 48), ...fn('Parque Chacha', 2)];
  const { festivalCities } = loadSat(films, PV);
  assert.deepStrictEqual(festivalCities(films).map(c => c.name), ['Pasto', 'Chachagüí']);
});

test('satélite: lejos (≥ 50 km) sigue siendo ciudad aparte aunque tenga 1 función', () => {
  const films = [...fn('Teatro Pasto', 48), ...fn('Teatro Lejos', 1)];
  const { festivalCities, filterCity } = loadSat(films, PV);
  assert.deepStrictEqual(festivalCities(films).map(c => c.name), ['Pasto', 'Cali']);
  assert.strictEqual(filterCity('Teatro Lejos'), 'Cali');
});
