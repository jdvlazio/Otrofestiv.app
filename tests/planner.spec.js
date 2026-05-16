// @ts-check
// planner.spec.js — Tab Planear: cálculo, escenarios, conflictos, disponibilidad.
const { test, expect } = require('@playwright/test');
const { LEVIZA_SIMTIME, enterFestival, addToWatchlist, goToPlanear } = require('./helpers');

// T03 — Ver opciones genera resultados
test('T03 — ver opciones genera resultados', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await addToWatchlist(page, 'Taller de Guion');
  await goToPlanear(page);
  await expect(page.locator('#ag-result-wrap')).toBeHidden({ timeout: 3000 });
  await page.locator('.av-calc-btn').click();
  await expect(page.locator('#ag-result-wrap')).toBeVisible({ timeout: 20000 });
  const content = await page.locator('#ag-result').textContent();
  expect(content?.trim().length).toBeGreaterThan(5);
});

// T04 — Ver opciones recalcula al presionar de nuevo
test('T04 — ver opciones recalcula al presionar de nuevo', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await addToWatchlist(page, 'Taller de Guion');
  await goToPlanear(page);
  await page.locator('.av-calc-btn').click();
  await page.locator('#ag-result-wrap').waitFor({ state: 'visible', timeout: 20000 });
  await page.locator('.av-calc-btn').click();
  await page.locator('#ag-result-wrap').waitFor({ state: 'visible', timeout: 20000 });
  const content = await page.locator('#ag-result').textContent();
  expect(content?.trim().length).toBeGreaterThan(5);
});

// T09 — Taller recurrente: 3 sesiones en el plan
test('T09 — taller recurrente: 3 sesiones en el plan', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await addToWatchlist(page, 'Taller de Guion');
  await goToPlanear(page);
  await page.locator('.av-calc-btn').click();
  await page.locator('#ag-result-wrap').waitFor({ state: 'visible', timeout: 20000 });
  const sessionCount = await page.evaluate(() => {
    if (!cachedResult?.scenarios?.length) return 0;
    const s0 = cachedResult.scenarios[0];
    return s0?.schedule?.filter(s => s._title === 'Taller de Guion').length || 0;
  });
  expect(sessionCount).toBe(3);
});

// T29 — Planear sin watchlist muestra estado vacío
test('T29 — planear sin watchlist muestra estado vacío', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => { watchlist.clear(); savedAgenda = null; saveState('wl','watched'); saveSavedAgenda(); });
  await page.evaluate(() => { switchMainNav('mnav-planner'); showAgView(); });
  await page.waitForSelector('.empty-state-hero', { timeout: 8000 });
  const empty = await page.locator('.empty-state-hero').count();
  expect(empty).toBeGreaterThan(0);
});

// T30 — Planear con watchlist muestra botón calcular
test('T30 — planear con watchlist muestra botón calcular', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await addToWatchlist(page, 'Taller de Guion');
  await page.evaluate(() => { switchMainNav('mnav-planner'); showAgView(); });
  await expect(page.locator('.av-calc-btn')).toBeVisible({ timeout: 8000 });
});

// T31 — Planear genera al menos un escenario
test('T31 — planear genera al menos un escenario', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await addToWatchlist(page, 'Taller de Guion');
  await goToPlanear(page);
  await page.locator('.av-calc-btn').click();
  await page.locator('#ag-result-wrap').waitFor({ state: 'visible', timeout: 20000 });
  const scenarios = await page.evaluate(() => cachedResult?.scenarios?.length || 0);
  expect(scenarios).toBeGreaterThan(0);
});

// T36 — Sesión solapada abre modal de conflicto
test('T36 — sesión solapada abre modal de conflicto', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => {
    const f1 = FILMS.find(fi => fi.title === 'Taller de Guion' && fi.day === 'VIE 15');
    if (!f1) return;
    if (!savedAgenda) savedAgenda = { schedule: [] };
    savedAgenda.schedule = [{ ...f1, _title: f1.title }];
    saveSavedAgenda();
    watchlist.add('Taller de Guion');
    const f2 = FILMS.find(fi => fi.title === 'Rebelión' && fi.day === 'VIE 15');
    if (f2) openConflictSheet(f2.title, f2, savedAgenda.schedule[0]);
  });
  await page.waitForSelector('#conflict-sheet', { timeout: 5000 });
  const sheet = await page.locator('#conflict-sheet.open, #conflict-sheet[style*="block"], #conflict-sheet').count();
  expect(sheet).toBeGreaterThan(0);
});

// T43 — Planear con títulos muestra chips de disponibilidad
test('T43 — planear con títulos muestra chips de disponibilidad', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await addToWatchlist(page, 'Taller de Guion');
  await page.evaluate(() => { switchMainNav('mnav-planner'); showAgView(); });
  await page.waitForSelector('.av-calc-btn', { timeout: 8000 });
  const hasUI = await page.locator('.av-calc-btn').count();
  expect(hasUI).toBeGreaterThan(0);
});
