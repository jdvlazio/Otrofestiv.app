// Unit test — screeningPlannable (dominio), el predicado POR FUNCIÓN de «puede
// entrar a tu plan» (16 ago 2026). Nació de la re-corrida del QA: el panel de
// alternativas reimplementaba 2 de los 4 chequeos y ofrecía otras ciudades
// (436/836 con filtro Bogotá) y canceladas por el sismo (118); la recuperación
// de Sugerencias se saltaba _cancelled. Cuatro reglas, un dueño.
const { test } = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

const BASE = { title: 'X', day: 'D1', time: '10:00', venue: 'Cinemateca BOG', duration: '90 min' };

function load(overrides = {}) {
  return loadDomain({
    functions: ['screeningPlannable'],
    globals: {
      // los tres colaboradores se stubean: cada uno tiene su propia suite;
      // acá se prueba la COMPOSICIÓN de las cuatro reglas, no sus internas.
      screeningPassed: () => false, isScreeningBlocked: () => false,
      PLAN_CITY_VENUES: null,
      ...overrides,
    },
  });
}

test('función normal → plannable', () => {
  const D = load();
  assert.equal(D.screeningPlannable({ ...BASE }), true);
});

test('cancelada → NO (el agujero de Sugerencias)', () => {
  const D = load();
  assert.equal(D.screeningPlannable({ ...BASE, _cancelled: true }), false);
});

test('ya pasada → NO', () => {
  const D = load({ screeningPassed: () => true });
  assert.equal(D.screeningPlannable({ ...BASE }), false);
});

test('en tu franja vetada → NO', () => {
  const D = load({ isScreeningBlocked: () => true });
  assert.equal(D.screeningPlannable({ ...BASE }), false);
});

test('otra ciudad con filtro puesto → NO (el agujero del panel)', () => {
  const D = load({ PLAN_CITY_VENUES: new Set(['Cinemateca BOG']) });
  assert.equal(D.screeningPlannable({ ...BASE, venue: 'Colombo MED' }), false);
  assert.equal(D.screeningPlannable({ ...BASE }), true);          // la de tu ciudad sí
  assert.equal(D.screeningPlannable({ ...BASE, venue: undefined }), true); // sin sede: no se ata
});

test('sin filtro de ciudad → todas las ciudades valen', () => {
  const D = load({ PLAN_CITY_VENUES: null });
  assert.equal(D.screeningPlannable({ ...BASE, venue: 'Colombo MED' }), true);
});
