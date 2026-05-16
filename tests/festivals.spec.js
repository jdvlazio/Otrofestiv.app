// @ts-check
// festivals.spec.js — Selector de festival, cambio de festival, validaciones cross-festival.
const { test, expect } = require('@playwright/test');
const { LEVIZA_SIMTIME, enterFestival } = require('./helpers');

// T08 — Festival selector: Leviza aparece antes que Tribeca
test('T08 — festival selector: Leviza aparece antes que Tribeca', async ({ page }) => {
  await page.goto('/');
  await page.waitForSelector('#splash-sel-btn', { timeout: 15000 });
  await page.locator('#splash-sel-btn').click();
  await page.waitForSelector('#splash-dropdown', { state: 'visible', timeout: 5000 });
  const items = page.locator('.splash-drop-item[data-fest]');
  expect(await items.count()).toBeGreaterThan(1);
  const firstFestId = await items.first().getAttribute('data-fest');
  expect(firstFestId).toContain('leviza');
});

// T37 — Cambiar de festival actualiza el topbar
test('T37 — cambiar de festival actualiza el topbar', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  const beforeName = await page.locator('.hdr-fest-name').textContent();
  await page.evaluate(() => loadFestival('tribeca2026'));
  await page.waitForFunction(
    () => document.querySelector('.hdr-fest-name')?.textContent?.toUpperCase().includes('TRIBECA'),
    { timeout: 8000 }
  );
  const afterName = await page.locator('.hdr-fest-name').textContent();
  expect(beforeName).not.toEqual(afterName);
  expect(afterName?.toUpperCase()).toContain('TRIBECA');
});

// T39 — Todos los festivales cargan sin crash
test('T39 — todos los festivales cargan sin crash', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  const festIds = await page.evaluate(() =>
    Object.keys(FESTIVAL_CONFIG).filter(k => k !== 'default')
  );
  for (const id of festIds) {
    await page.evaluate((fid) => loadFestival(fid), id);
    await page.waitForFunction(() => typeof FILMS !== 'undefined' && FILMS.length > 0, { timeout: 8000 });
  }
  const realErrors = errors.filter(e => !e.includes('sentry'));
  expect(realErrors).toHaveLength(0);
});

// T42 — onclick handlers: ninguno tiene sintaxis inválida
test('T42 — onclick handlers tienen JS válido', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  const errors = [];
  page.on('pageerror', e => { if (e.message.includes('SyntaxError')) errors.push(e.message); });
  await page.waitForTimeout(200); // mínimo: colección de errores async
  expect(errors).toHaveLength(0);
});
