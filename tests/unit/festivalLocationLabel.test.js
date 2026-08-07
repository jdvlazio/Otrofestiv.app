// festivalLocationLabel — la línea de UBICACIÓN del splash.
//
// Regla: la ciudad NUNCA se repite con el país. Un festival NACIONAL no tiene una
// sede única y declara el país en `city` — FICDEH 2026 son 11 ciudades, de Quibdó
// a Tunja— y la línea salía «COLOMBIA, COLOMBIA». Eso no es una ubicación: es un
// error de lectura, y en el splash, que es la primera pantalla, se nota.
const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

const PAISES = {
  CO: { es: 'Colombia', en: 'Colombia' },
  BR: { es: 'Brasil',   en: 'Brazil' },
  US: { es: 'Estados Unidos', en: 'United States' },
};
const label = (cfg, lang = 'es') => loadDomain({
  functions: ['festivalLocationLabel', 'countryName'],
  globals: { COUNTRY_NAMES: PAISES },
}).festivalLocationLabel(cfg, lang);

test('lo normal: ciudad y país, ambos', () => {
  assert.strictEqual(label({ city: 'Cartagena', country: 'CO' }), 'Cartagena, Colombia');
  assert.strictEqual(label({ city: 'Buenos Aires', country: 'AR' }), 'Buenos Aires',
    'país sin nombre en el mapa → la ciudad sola, nunca un ISO crudo');
});

test('festival nacional: la ciudad ES el país → se dice UNA vez', () => {
  assert.strictEqual(label({ city: 'Colombia', country: 'CO' }), 'Colombia');
});

test('la repetición no vuelve por el idioma ni por los acentos', () => {
  // Interfaz en inglés: city 'Brasil' y país 'Brazil' son el mismo lugar escrito
  // distinto. Comparar solo contra el nombre del idioma activo dejaría pasar
  // «Brasil, Brazil».
  assert.strictEqual(label({ city: 'Brasil', country: 'BR' }, 'en'), 'Brasil');
  assert.strictEqual(label({ city: 'brasil', country: 'BR' }), 'brasil');
  assert.strictEqual(label({ city: ' Colombia ', country: 'CO' }), 'Colombia');
});

test('sin ciudad no se inventa el país', () => {
  // Tribeca declara `city` vacío: la línea queda vacía, como hasta ahora.
  assert.strictEqual(label({ city: '', country: 'US' }), '');
  assert.strictEqual(label({ country: 'US' }), '');
  assert.strictEqual(label({}), '');
  assert.strictEqual(label(null), '');
});
