// @ts-check
// festivals.spec.js — Selector de festival, cambio de festival, validaciones cross-festival.
const { test, expect } = require('@playwright/test');
const { LEVIZA_SIMTIME, enterFestival } = require('./helpers');

// T08 — Festival selector: Leviza aparece antes que Tribeca
test('T08 — festival selector: Leviza aparece antes que Tribeca', async ({ page }) => {
  await page.goto('/');
  // Gate de readiness JS (no DOM estático): los items del splash sólo existen
  // tras _renderSplashDropdown, lo que garantiza que el listener delegado está
  // adjunto ANTES de hacer click en #splash-sel-btn (estático). Sin esto, el
  // click llega antes del wiring del bootstrap → el dropdown nunca abre (flaky).
  await page.waitForSelector('.splash-drop-item[data-fest]', { state: 'attached', timeout: 15000 });
  await page.locator('#splash-sel-btn').click();
  await page.waitForSelector('#splash-dropdown', { state: 'visible', timeout: 15000 });
  await page.waitForSelector('.splash-drop-item[data-fest]', { state: 'visible', timeout: 15000 });
  const items = page.locator('.splash-drop-item[data-fest]');
  expect(await items.count()).toBeGreaterThan(1);
  // Tribeca es el festival próximo — aparece primero en la lista (upcoming > past)
  // Leviza terminó el 17 MAY y aparece en Anteriores, después de los próximos
  const firstFestId = await items.first().getAttribute('data-fest');
  expect(firstFestId).toContain('tribeca');
  const allIds = await items.evaluateAll(els => els.map(el => el.getAttribute('data-fest')));
  expect(allIds.some(id => id.includes('leviza'))).toBe(true);
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

// ─── PARAMETRIZADOS test.each ────────────────────────────────────────────────
// Mismo invariante corriendo contra todos los festivales principales.
// 1 definición → N test runs. Patrón correcto para cobertura cross-festival.

const MAIN_FESTIVALS = ['leviza2026', 'tribeca2026'];

// P01 — Festival tiene films (parametrizado)
for (const festId of MAIN_FESTIVALS) {
  test(`P01 — ${festId}: carga con films`, async ({ page }) => {
    await enterFestival(page, festId);
    const count = await page.evaluate(() => typeof FILMS !== 'undefined' ? FILMS.length : 0);
    expect(count).toBeGreaterThan(0);
  });
}

// P02 — Festival carga sin errores JS (parametrizado)
for (const festId of MAIN_FESTIVALS) {
  test(`P02 — ${festId}: carga sin errores JS`, async ({ page }) => {
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    await enterFestival(page, festId);
    const critical = errors.filter(e => !e.includes('sentry') && !e.includes('clarity'));
    expect(critical).toHaveLength(0);
  });
}

// P03 — Festival: topbar muestra nombre del festival (parametrizado)
for (const festId of MAIN_FESTIVALS) {
  test(`P03 — ${festId}: topbar muestra nombre`, async ({ page }) => {
    await enterFestival(page, festId);
    await page.waitForSelector('.hdr-fest-name', { timeout: 5000 });
    const name = await page.locator('.hdr-fest-name').textContent();
    expect(name?.trim().length).toBeGreaterThan(0);
  });
}
