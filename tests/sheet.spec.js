// @ts-check
// sheet.spec.js — Sheet de película + Intereses (watchlist).
const { test, expect } = require('@playwright/test');
const { LEVIZA_SIMTIME, enterFestival, addToWatchlist } = require('./helpers');

// T07 — Quitar de Intereses desde sheet cierra el sheet
test('T07 — quitar de Intereses desde sheet cierra el sheet', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await addToWatchlist(page, 'La Suprema');
  await page.evaluate(() => openPelSheet('La Suprema'));
  await page.waitForSelector('#pel-sheet.open', { timeout: 8000 });
  const wlBtn = page.locator('#pel-wl-btn');
  await expect(wlBtn).toContainText(/(intereses|interests)/i);
  await wlBtn.click();
  await expect(page.locator('#pel-sheet.open')).toHaveCount(0, { timeout: 5000 });
});

// T14 — Sheet muestra el título correcto
test('T14 — sheet muestra el título correcto', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => openPelSheet('La Suprema'));
  await page.waitForSelector('#pel-sheet.open', { timeout: 8000 });
  const title = await page.locator('.pel-sheet-title').first().textContent();
  expect(title?.trim().length).toBeGreaterThan(0);
  expect(title).toContain('Suprema');
});

// T15 — Sheet muestra funciones del título
test('T15 — sheet muestra funciones del título', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => openPelSheet('La Suprema'));
  await page.waitForSelector('#pel-sheet.open', { timeout: 8000 });
  const funciones = await page.locator('.pel-sheet-screening, .pel-sheet-screenings').count();
  expect(funciones).toBeGreaterThan(0);
});

// T16 — Sheet tiene botón de intereses
test('T16 — sheet tiene botón de intereses', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => openPelSheet('La Suprema'));
  await page.waitForSelector('#pel-sheet.open', { timeout: 8000 });
  await expect(page.locator('#pel-wl-btn')).toBeVisible();
});

// T17 — Añadir al watchlist desde sheet actualiza el estado
test('T17 — añadir al watchlist desde sheet actualiza el estado', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => { watchlist.clear(); saveState('wl','watched'); });
  await page.evaluate(() => openPelSheet('La Suprema'));
  await page.waitForSelector('#pel-sheet.open', { timeout: 8000 });
  await page.locator('#pel-wl-btn').click();
  await page.waitForFunction(() => watchlist.has('La Suprema'), { timeout: 5000 });
  const inWL = await page.evaluate(() => watchlist.has('La Suprema'));
  expect(inWL).toBe(true);
});

// T18 — Sheet se cierra con el botón X
test('T18 — sheet se cierra con el botón X', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => openPelSheet('La Suprema'));
  await page.waitForSelector('#pel-sheet.open', { timeout: 8000 });
  await page.evaluate(() => closePelSheet());
  await expect(page.locator('#pel-sheet.open')).toHaveCount(0, { timeout: 5000 });
});

// T19 — Watchlist persiste al navegar entre tabs
test('T19 — watchlist persiste al navegar entre tabs', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await addToWatchlist(page, 'La Suprema');
  await page.evaluate(() => { switchMainNav('mnav-seleccion'); showAgView(); });
  await page.waitForSelector('#ag-view', { state: 'visible', timeout: 5000 });
  await page.evaluate(() => switchMainNav('mnav-cartelera'));
  await page.waitForSelector('.poster-card, .plist-item, .dtab', { timeout: 5000 });
  const inWL = await page.evaluate(() => watchlist.has('La Suprema'));
  expect(inWL).toBe(true);
});

// T33 — Intereses muestra películas en watchlist
test('T33 — intereses muestra películas en watchlist', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await addToWatchlist(page, 'La Suprema');
  await addToWatchlist(page, 'Taller de Guion');
  await page.evaluate(() => { switchMainNav('mnav-seleccion'); showAgView(); });
  await page.waitForSelector('#ag-view', { state: 'visible', timeout: 5000 });
  const items = await page.locator('.plist-item, .poster-card, .ag-film-row, .int-item').count();
  expect(items).toBeGreaterThan(0);
});

// ─── YA VISTA + RATING ────────────────────────────────────────────────────────

// V01 — Botón Vista en sheet cierra el sheet (comportamiento DOM observable)
// toggleWatched está en closure — testeamos efecto visible: sheet se cierra tras marcar vista
test('V01 — botón Vista en sheet cierra el sheet', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => openPelSheet('La Suprema'));
  await page.waitForSelector('#pel-sheet.open', { timeout: 8000 });
  // #pel-vista-btn aparece cuando la película NO está en watched aún
  const vistaBtn = page.locator('#pel-vista-btn');
  await expect(vistaBtn).toBeVisible({ timeout: 5000 });
  await vistaBtn.click();
  await page.waitForTimeout(300); // animación de cierre
  await expect(page.locator('#pel-sheet.open')).toHaveCount(0, { timeout: 5000 });
});

// V02 — Rating sheet abre correctamente
// openRatingSheet directo — el botón en sheet usa setTimeout que complica el selector
test('V02 — rating sheet abre correctamente', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => openRatingSheet('La Suprema'));
  await page.waitForSelector('#rating-sheet.open', { timeout: 5000 });
  expect(await page.locator('#rating-sheet.open').count()).toBe(1);
});

// V03 — Rating sheet se cierra quitando clase .open
// closeRatingSheet usa classList.remove('open'), no display:none
test('V03 — rating sheet se cierra con omitir', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => openRatingSheet('La Suprema'));
  await page.waitForSelector('#rating-sheet.open', { timeout: 5000 });
  await page.locator('#rating-action-btn').click();
  await page.waitForSelector('#rating-sheet:not(.open)', { timeout: 5000 });
  expect(await page.locator('#rating-sheet.open').count()).toBe(0);
});

// V04 — Rating sheet muestra estrellas correctamente
// Testea DOM observable: las estrellas están presentes en el rating sheet
test('V04 — rating sheet muestra estrellas', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => openRatingSheet('La Suprema'));
  await page.waitForSelector('#rating-sheet.open', { timeout: 5000 });
  // El rating-film-title debe mostrar el nombre de la película
  const filmTitle = await page.locator('#rating-film-title').textContent();
  expect(filmTitle).toContain('Suprema');
  // El área de estrellas debe estar presente
  await expect(page.locator('#rating-stars-wrap')).toBeVisible({ timeout: 3000 });
});
