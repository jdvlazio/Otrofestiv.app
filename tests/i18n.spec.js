// @ts-check
// i18n.spec.js — Cambio de idioma ES ↔ EN: botones, strings críticos, persistencia.
const { test, expect } = require('@playwright/test');
const { LEVIZA_SIMTIME, enterFestival } = require('./helpers');

// Abre el dropdown de idioma (las opciones están ocultas hasta abrir el trigger).
async function openLangDropdown(page) {
  await page.locator('#lang-trigger').click();
  await expect(page.locator('#lang-btn-en')).toBeVisible({ timeout: 3000 });
}

// I01 — Selector de idioma presente; al abrir muestra opciones ES y EN
test('I01 — selector de idioma con opciones ES y EN', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await expect(page.locator('#lang-trigger')).toBeVisible({ timeout: 5000 });
  await openLangDropdown(page);
  await expect(page.locator('#lang-btn-es')).toBeVisible();
  await expect(page.locator('#lang-btn-en')).toBeVisible();
});

// I02 — Cambiar a EN activa el botón EN y desactiva ES
test('I02 — cambiar a EN activa el botón correcto', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await openLangDropdown(page);
  await page.locator('#lang-btn-en').click();
  await page.waitForFunction(() => document.getElementById('lang-btn-en')?.classList.contains('on'), { timeout: 3000 });
  const enActive = await page.locator('#lang-btn-en.on').count();
  const esActive = await page.locator('#lang-btn-es.on').count();
  expect(enActive).toBe(1);
  expect(esActive).toBe(0);
});

// I03 — En EN los tabs del nav muestran texto en inglés
test('I03 — tabs en EN muestran texto inglés', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await openLangDropdown(page);
  await page.locator('#lang-btn-en').click();
  await page.waitForFunction(() => document.getElementById('lang-btn-en')?.classList.contains('on'), { timeout: 3000 });
  const navText = await page.locator('.main-nav-tab').allTextContents();
  const joined = navText.join(' ').toUpperCase();
  // En inglés debe haber alguno de estos strings
  expect(joined).toMatch(/INTERESTS|PLANNER|MY PLAN|PROGRAM/);
});

// I04 — Volver a ES restaura strings en español
test('I04 — volver a ES restaura strings español', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await openLangDropdown(page);
  await page.locator('#lang-btn-en').click();
  await page.waitForFunction(() => document.getElementById('lang-btn-en')?.classList.contains('on'), { timeout: 3000 });
  await openLangDropdown(page);
  await page.locator('#lang-btn-es').click();
  await page.waitForFunction(() => document.getElementById('lang-btn-es')?.classList.contains('on'), { timeout: 3000 });
  const navText = await page.locator('.main-nav-tab').allTextContents();
  const joined = navText.join(' ').toUpperCase();
  expect(joined).toMatch(/INTERESES|PLANEAR|MI PLAN|PROGRAMA/);
});

// I05 — Cambio de idioma no lanza errores JS
test('I05 — cambio de idioma sin errores JS', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await openLangDropdown(page);
  await page.locator('#lang-btn-en').click();
  await page.waitForFunction(() => document.getElementById('lang-btn-en')?.classList.contains('on'), { timeout: 3000 });
  await openLangDropdown(page);
  await page.locator('#lang-btn-es').click();
  await page.waitForFunction(() => document.getElementById('lang-btn-es')?.classList.contains('on'), { timeout: 3000 });
  await page.waitForTimeout(200);
  expect(errors).toHaveLength(0);
});
