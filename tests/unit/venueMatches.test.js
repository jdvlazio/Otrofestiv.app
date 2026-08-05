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
    functions: ['_resolveVenue', 'vcfg', 'venueMatches', 'venueSelLabel'],
    globals: { FESTIVAL_CONFIG: { f: { venues: VENUES } }, _activeFestId: 'f' },
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
