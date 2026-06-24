// Unit test — delayConsensusBadge (src/view/helpers.js), Fase B del retraso
// colaborativo. Guard de regresión del RENDER del badge: caza que el mapeo
// consenso→HTML, el copy i18n y las clases CSS no se rompan en un refactor
// futuro (el render full depende de datos de nube, no testeable sin red; esto
// aísla la parte determinista). Carga: import() dinámico del módulo ESM, con
// _lang seteado para t() — patrón de poster.test.js.

const { test, before } = require('node:test');
const assert = require('node:assert');

let H;
before(async () => { globalThis._lang = 'es'; H = await import('../../src/view/helpers.js'); });

test('sin consenso (null / state none) → string vacío', () => {
  assert.equal(H.delayConsensusBadge(null), '');
  assert.equal(H.delayConsensusBadge({ state: 'none', delayMin: 0, reporters: 0 }), '');
});

test('confirmed → clase confirmed + minutos + nº reporters + disclaimer', () => {
  const h = H.delayConsensusBadge({ state: 'confirmed', delayMin: 25, reporters: 2 });
  assert.match(h, /class="delay-consensus confirmed"/);
  assert.match(h, /25/);                       // minutos (mediana)
  assert.match(h, /\b2\b/);                     // nº de asistentes
  assert.match(h, /delay-consensus-src/);       // disclaimer "no oficial"
});

test('tentative → clase tentative + "sin confirmar", sin texto de confirmado', () => {
  const h = H.delayConsensusBadge({ state: 'tentative', delayMin: 15, reporters: 1 });
  assert.match(h, /class="delay-consensus tentative"/);
  assert.match(h, /sin confirmar/i);
  assert.doesNotMatch(h, /confirmed/);
});
