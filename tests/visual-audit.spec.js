/**
 * visual-audit.spec.js — Screenshots de cada estado principal de la app.
 *
 * NO son tests de pixel-diff (frágiles entre OS). Son evidencia visual
 * automática: cada push genera screenshots que quedan como CI artifacts.
 * Juan puede revisarlos en GitHub Actions → Artifacts → visual-audit-screenshots.
 *
 * Cuándo falla: si un selector crítico no existe (la pantalla no cargó).
 * Cuándo NO falla: si algo se ve diferente visualmente — eso se audita manual.
 */
const { test, expect } = require('@playwright/test');
const { LEVIZA_SIMTIME, enterFestival } = require('./helpers');

test.describe('Visual audit — Leviza', () => {
  test.beforeEach(async ({ page }) => {
    await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  });

  test('01 — Programa JUE 14 (lista)', async ({ page }) => {
    await page.waitForSelector('.plist-item', { timeout: 8000 });
    await page.screenshot({ path: 'test-results/visual/leviza-programa-jue14.png', fullPage: false });
    const count = await page.locator('.plist-item').count();
    expect(count).toBeGreaterThan(0);
  });

  test('02 — Programa TODO (grid)', async ({ page }) => {
    await page.locator('.dtab[data-day="all"]').click();
    await page.waitForSelector('.poster-card', { timeout: 8000 });
    await page.screenshot({ path: 'test-results/visual/leviza-programa-todo.png', fullPage: false });
    const count = await page.locator('.poster-card').count();
    expect(count).toBeGreaterThan(0);
  });

  test('03 — Intereses', async ({ page }) => {
    await page.evaluate(() => switchMainNav('mnav-intereses'));
    await page.waitForTimeout(800);
    await page.screenshot({ path: 'test-results/visual/leviza-intereses.png', fullPage: false });
  });

  test('04 — Planear', async ({ page }) => {
    await page.evaluate(() => switchMainNav('mnav-planear'));
    await page.waitForTimeout(800);
    await page.screenshot({ path: 'test-results/visual/leviza-planear.png', fullPage: false });
  });

  test('05 — Mi Plan', async ({ page }) => {
    await page.evaluate(() => switchMainNav('mnav-miplan'));
    await page.waitForTimeout(800);
    await page.screenshot({ path: 'test-results/visual/leviza-miplan.png', fullPage: false });
  });

  test('06 — Topbar selector', async ({ page }) => {
    await page.waitForSelector('.hdr-fest-dates', { timeout: 5000 });
    const bar = page.locator('.hdr-fest-bar');
    await bar.screenshot({ path: 'test-results/visual/leviza-topbar.png' });
    await expect(bar).toBeVisible();
  });
});
