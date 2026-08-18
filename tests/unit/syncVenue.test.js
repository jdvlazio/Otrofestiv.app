// Unit test — syncScheduleWithCatalog respeta la SEDE (re-corrida del QA de
// ojos frescos, 16 ago 2026). FICDEH programa el mismo título el mismo día a
// la misma hora en ciudades distintas (13 tripletas medidas): matchear solo
// por título+día+hora devolvía la PRIMERA del catálogo y el plan guardado en
// Bogotá amanecía en Barranquilla tras recargar. La identidad de una función
// incluye su sede; sin match exacto la entrada queda INTACTA (camino
// reprogramada/cancelada de los avisos — nunca un swap mudo).
const { test } = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

const CAT = [
  { title: 'Notas', day: 'D1', time: '19:00', venue: 'Caribe BAQ', duration: '80 min', _slotDur: 90 },
  { title: 'Notas', day: 'D1', time: '19:00', venue: 'Cinemateca BOG', duration: '80 min', _slotDur: 95 },
];

function load() {
  return loadDomain({ functions: ['syncScheduleWithCatalog'], globals: {} });
}

test('misma tripleta en dos sedes → conserva LA SEDE elegida, no la primera del catálogo', () => {
  const D = load();
  const out = D.syncScheduleWithCatalog(
    [{ _title: 'Notas', day: 'D1', time: '19:00', venue: 'Cinemateca BOG' }], CAT);
  assert.equal(out[0].venue, 'Cinemateca BOG');
  assert.equal(out[0]._slotDur, 95);           // heredó el anclaje de SU función
});

test('la sede elegida ya no existe → entrada INTACTA (avisos deciden, no un swap)', () => {
  const D = load();
  const e = { _title: 'Notas', day: 'D1', time: '19:00', venue: 'Sala que cerró' };
  const out = D.syncScheduleWithCatalog([e], CAT);
  assert.deepEqual(out[0], e);                  // ni Caribe ni Cinemateca: intacta
});

test('entrada vieja SIN sede → sigue matcheando por título+día+hora', () => {
  const D = load();
  const out = D.syncScheduleWithCatalog([{ _title: 'Notas', day: 'D1', time: '19:00' }], CAT);
  assert.equal(out[0].title, 'Notas');          // hereda del catálogo como antes
});
