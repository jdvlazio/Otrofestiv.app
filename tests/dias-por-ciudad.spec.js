// @ts-check
// dias-por-ciudad.spec.js — la tira de días muestra solo los días de la ciudad
// elegida (19 nov 2026, Juan). Al Este no es simultáneo: Medellín 18–22 nov y
// Bogotá 25–29. Elegida una ciudad, los días de la otra se ocultan y el día
// activo nunca queda en un día oculto. Dueños: diasDeCiudad (helpers.js) y
// _syncDiasCiudad/_hoyManana (pipeline.js).
const { test, expect } = require('@playwright/test');
const { enterFestival } = require('./helpers');

const MED = ['2026-11-18', '2026-11-19', '2026-11-20', '2026-11-21', '2026-11-22'];
const BOG = ['2026-11-25', '2026-11-26', '2026-11-27', '2026-11-28', '2026-11-29'];

// Estado de la tira: días visibles, día activo y si su pestaña se ve.
const tira = () => {
  const tabs = [...document.querySelectorAll('#dtabs .dtab')].filter(t => t.dataset.day !== 'all');
  const visibles = tabs.filter(t => getComputedStyle(t).display !== 'none').map(t => t.dataset.day);
  const on = document.querySelector('#dtabs .dtab.on');
  return { visibles, activeDay, onVisible: !!on && getComputedStyle(on).display !== 'none' };
};

test('DC1 — elegir ciudad oculta los días de la otra; «Todas» los muestra', async ({ page }) => {
  await enterFestival(page, 'aleste2026', '2026-11-19T10:00:00-05:00');
  const r = await page.evaluate(async ({ tiraSrc }) => {
    const w = ms => new Promise(res => setTimeout(res, ms));
    const tira = eval(tiraSrc);
    const C = await import('/src/controller/handlers.js');
    C.citySheetPick('Medellín'); await w(300);
    const med = tira();
    C.citySheetPick('Bogotá'); await w(300);
    const bog = tira();
    C.citySheetAll(); await w(300);
    const todas = tira();
    return { med, bog, todas };
  }, { tiraSrc: tira.toString() });
  expect(r.med.visibles, 'Medellín: solo sus días').toEqual(MED);
  expect(r.bog.visibles, 'Bogotá: solo sus días').toEqual(BOG);
  expect(r.todas.visibles, 'Todas: los doce').toHaveLength(12);
  for (const k of ['med', 'bog', 'todas']) {
    expect(r[k].activeDay === 'all' || r[k].onVisible, `${k}: el día activo está a la vista`).toBe(true);
  }
  // El 19 con Bogotá elegida: Bogotá no empezó → su primer día, el 25.
  expect(r.bog.activeDay, 'Bogotá antes de empezar → su primer día').toBe('2026-11-25');
});

test('DC2 — elegir una ciudad que ya terminó con el día de hoy puesto lleva a «Todo»', async ({ page }) => {
  await enterFestival(page, 'aleste2026', '2026-11-26T10:00:00-05:00');
  const r = await page.evaluate(async ({ tiraSrc }) => {
    const w = ms => new Promise(res => setTimeout(res, ms));
    const tira = eval(tiraSrc);
    const C = await import('/src/controller/handlers.js');
    C.filterByDay('2026-11-26'); await w(300);   // hoy, día de Bogotá
    C.citySheetPick('Medellín'); await w(300);    // la hoja de ciudad, con hoy ya puesto
    return tira();
  }, { tiraSrc: tira.toString() });
  expect(r.activeDay, 'Medellín terminó el 22 → «Todo», no un día vacío').toBe('all');
  expect(r.visibles).toEqual(MED);
});

test('DC3 — «Mañana» en el último día de la ciudad no salta a un día ajeno', async ({ page }) => {
  await enterFestival(page, 'aleste2026', '2026-11-22T10:00:00-05:00');
  const r = await page.evaluate(async ({ tiraSrc }) => {
    const w = ms => new Promise(res => setTimeout(res, ms));
    const tira = eval(tiraSrc);
    const C = await import('/src/controller/handlers.js');
    C.citySheetPick('Medellín'); await w(300);
    C.setProgramaMode('manana'); await w(300);
    const pill = document.getElementById('pmode-manana');
    return { ...tira(), pillOn: !!pill && pill.classList.contains('on') };
  }, { tiraSrc: tira.toString() });
  expect(MED, '«Mañana» queda dentro de Medellín').toContain(r.activeDay);
  expect(r.onVisible, 'y su pestaña se ve').toBe(true);
});
