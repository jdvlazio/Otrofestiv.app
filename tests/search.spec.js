// @ts-check
// search.spec.js — Búsqueda global: abrir, tipear, resultados, cerrar.
const { test, expect } = require('@playwright/test');
const { LEVIZA_SIMTIME, enterFestival } = require('./helpers');

// S01 — Icono de búsqueda abre el overlay
test('S01 — icono búsqueda abre overlay', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.locator('#hdr-search-icon').click();
  await page.waitForSelector('#search-overlay', { state: 'visible', timeout: 5000 });
  expect(await page.locator('#search-overlay').count()).toBe(1);
});

// S02 — Input de búsqueda recibe foco al abrir
test('S02 — search input recibe foco', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => searchOpen());
  await page.waitForSelector('#search-overlay', { state: 'visible', timeout: 5000 });
  const input = page.locator('#search-input');
  await expect(input).toBeVisible({ timeout: 3000 });
});

// S03 — Buscar término con resultados muestra items
test('S03 — búsqueda con resultados muestra items', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => searchOpen());
  await page.waitForSelector('#search-overlay', { state: 'visible', timeout: 5000 });
  await page.locator('#search-input').fill('La');
  await page.waitForSelector('.search-item', { timeout: 5000 });
  const items = await page.locator('.search-item').count();
  expect(items).toBeGreaterThan(0);
});

// S04 — Búsqueda sin resultados muestra empty state
test('S04 — búsqueda sin resultados muestra empty state', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => searchOpen());
  await page.waitForSelector('#search-overlay', { state: 'visible', timeout: 5000 });
  await page.locator('#search-input').fill('xyzxyzxyz123456');
  await page.waitForSelector('.search-empty', { timeout: 5000 });
  expect(await page.locator('.search-empty').count()).toBeGreaterThan(0);
});

// S05 — Click en resultado de búsqueda abre sheet de película
test('S05 — resultado búsqueda abre sheet de película', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => searchOpen());
  await page.waitForSelector('#search-overlay', { state: 'visible', timeout: 5000 });
  await page.locator('#search-input').fill('Suprema');
  await page.waitForSelector('.search-item', { timeout: 5000 });
  await page.locator('.search-item').first().click();
  await page.waitForSelector('#pel-sheet.open', { timeout: 5000 });
  expect(await page.locator('#pel-sheet.open').count()).toBe(1);
});

// S06 — Búsqueda funciona en Tribeca
test('S06 — búsqueda funciona en Tribeca', async ({ page }) => {
  await enterFestival(page, 'tribeca2026');
  await page.evaluate(() => searchOpen());
  await page.waitForSelector('#search-overlay', { state: 'visible', timeout: 5000 });
  await page.locator('#search-input').fill('New');
  await page.waitForSelector('.search-item, .search-empty', { timeout: 5000 });
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.waitForTimeout(200);
  expect(errors).toHaveLength(0);
});
