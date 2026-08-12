// venueCity — la ciudad de una sede, SOLO cuando aporta (dueño único).
// FICDEH 2026 (11 ciudades, 387 funciones) obligó a mostrar la ciudad en las
// cards del modo por días: sin eso había que abrir cada ficha para saber si la
// función era alcanzable. Pero en un festival de UNA ciudad, repetirla en cada
// card es ruido — de ahí la regla: se muestra solo si difiere de la del festival.
const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

const VENUES = {
  'Cinemateca':  { short: 'Cinemateca',  city: 'Bogotá' },
  'Panóptico':   { short: 'Panóptico',   city: 'Ibagué' },
  'Sin ciudad':  { short: 'Sin ciudad' },
};
const load = festCity => loadDomain({
  functions: ['_resolveVenue', 'vcfg', 'venueCity', 'isCitySel', 'keepCityOnly'],
  globals: { FESTIVAL_CONFIG: { f: { venues: VENUES, city: festCity } }, _activeFestId: 'f' },
});

test('multiciudad: cada sede muestra su ciudad', () => {
  // FICDEH declara city:'Colombia' a propósito, para que ninguna sede coincida
  const { venueCity } = load('Colombia');
  assert.strictEqual(venueCity('Cinemateca'), 'Bogotá');
  assert.strictEqual(venueCity('Panóptico'), 'Ibagué');
});

test('festival de una ciudad: NO se repite en cada card', () => {
  const { venueCity } = load('Bogotá');
  assert.strictEqual(venueCity('Cinemateca'), '', 'coincide con la del festival → ruido');
  assert.strictEqual(venueCity('Panóptico'), 'Ibagué', 'la que difiere sí se muestra');
});

test('sede sin ciudad declarada → vacío, nunca "undefined"', () => {
  assert.strictEqual(load('Colombia').venueCity('Sin ciudad'), '');
  assert.strictEqual(load('Colombia').venueCity('Inexistente'), '');
});

// keepCityOnly — la ciudad es CONTEXTO, la sede un filtro momentáneo. Al cambiar
// de día o sección se limpia la sede pero se CONSERVA la ciudad: seguís ahí.
// Sin esto, en FICDEH elegir Bogotá y tocar otro día devolvía las 11 ciudades.
test('keepCityOnly: conserva la ciudad, descarta la sede', () => {
  const { keepCityOnly, isCitySel } = load('Colombia');
  assert.strictEqual(keepCityOnly('city:Bogotá'), 'city:Bogotá');
  assert.strictEqual(keepCityOnly('Cinemateca'), 'all');
  assert.strictEqual(keepCityOnly('all'), 'all');
  assert.strictEqual(isCitySel('city:X'), true);
  assert.strictEqual(isCitySel('Cinemateca'), false);
});
