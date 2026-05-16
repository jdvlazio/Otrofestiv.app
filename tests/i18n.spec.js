// @ts-check
// i18n.spec.js — Cambio de idioma ES ↔ EN: botones, strings críticos, persistencia.
const { test, expect } = require('@playwright/test');
const { LEVIZA_SIMTIME, enterFestival } = require('./helpers');

// I01 — Botones de idioma están presentes en el topbar
test('I01 — botones de idioma ES y EN presentes', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await expect(page.locator('#lang-btn-es')).toBeVisible({ timeout: 5000 });
  await expect(page.locator('#lang-btn-en')).toBeVisible({ timeout: 5000 });
});

// I02 — Cambiar a EN activa el botón EN y desactiva ES
test('I02 — cambiar a EN activa el botón correcto', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.locator('#lang-btn-en').click();
  await page.waitForFunction(() => document.getElementById('lang-btn-en')?.classList.contains('active'), { timeout: 3000 });
  const enActive = await page.locator('#lang-btn-en.active').count();
  const esActive = await page.locator('#lang-btn-es.active').count();
  expect(enActive).toBe(1);
  expect(esActive).toBe(0);
});

// I03 — En EN los tabs del nav muestran texto en inglés
test('I03 — tabs en EN muestran texto inglés', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.locator('#lang-btn-en').click();
  await page.waitForFunction(() => document.getElementById('lang-btn-en')?.classList.contains('active'), { timeout: 3000 });
  const navText = await page.locator('.main-nav-tab').allTextContents();
  const joined = navText.join(' ').toUpperCase();
  // En inglés debe haber alguno de estos strings
  expect(joined).toMatch(/INTERESTS|PLANNER|MY PLAN|PROGRAM/);
});

// I04 — Volver a ES restaura strings en español
test('I04 — volver a ES restaura strings español', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.locator('#lang-btn-en').click();
  await page.waitForFunction(() => document.getElementById('lang-btn-en')?.classList.contains('active'), { timeout: 3000 });
  await page.locator('#lang-btn-es').click();
  await page.waitForFunction(() => document.getElementById('lang-btn-es')?.classList.contains('active'), { timeout: 3000 });
  const navText = await page.locator('.main-nav-tab').allTextContents();
  const joined = navText.join(' ').toUpperCase();
  expect(joined).toMatch(/INTERESES|PLANEAR|MI PLAN|PROGRAMA/);
});

// I05 — Cambio de idioma no lanza errores JS
test('I05 — cambio de idioma sin errores JS', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.locator('#lang-btn-en').click();
  await page.waitForFunction(() => document.getElementById('lang-btn-en')?.classList.contains('active'), { timeout: 3000 });
  await page.locator('#lang-btn-es').click();
  await page.waitForFunction(() => document.getElementById('lang-btn-es')?.classList.contains('active'), { timeout: 3000 });
  await page.waitForTimeout(200);
  expect(errors).toHaveLength(0);
});
