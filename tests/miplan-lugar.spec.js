// @ts-check
// miplan-lugar.spec.js — el lugar en la fila de Mi Plan abre la hoja del lugar
// (14 nov 2026, Juan): la misma que se abre desde la ficha; el resto de la fila
// sigue abriendo la ficha.
const { test, expect } = require('@playwright/test');
const { enterFestival } = require('./helpers');

test('ML1 — tocar el lugar en Mi Plan abre la hoja del lugar, no la ficha', async ({ page }) => {
  await enterFestival(page, 'fantasmagoria2026', '2026-10-14T10:00:00-05:00');
  const r = await page.evaluate(async () => {
    const w = ms => new Promise(res => setTimeout(res, ms));
    const C = await import('/src/controller/handlers.js');
    const f = FILMS.find(x => x.day && x.time && x.venue && !x.info);
    state.set('savedAgenda', { scenarioIdx: 0, schedule: [Object.assign({}, f, { _title: f.title })] });
    switchMainNav('mnav-miplan'); showAgView(); await w(600);
    C.selectMiPlanDay(DAY_KEYS.indexOf(f.day)); await w(400);
    const lugar = document.querySelector('.mplan-row .mplan-rvenue');
    lugar.click(); await w(400);
    const hoja = document.getElementById('venue-sheet').classList.contains('open');
    const nombre = document.querySelector('.venue-sheet-name')?.textContent.trim();
    const ficha = document.getElementById('pel-sheet')?.classList.contains('open') || false;
    const funciones = [...document.querySelectorAll('.venue-fn-title')].length;
    return { hoja, nombre, ficha, funciones };
  });
  expect(r.hoja, 'se abre la hoja del lugar').toBe(true);
  expect(r.nombre, 'con el nombre del lugar').toBeTruthy();
  expect(r.funciones, 'y sus funciones, la del plan incluida').toBeGreaterThan(0);
  expect(r.ficha, 'no abre la ficha debajo').toBe(false);
});
