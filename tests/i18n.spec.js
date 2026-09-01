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

// ── I06 — al cambiar de idioma, el encabezado también cambia de fecha ────────
// El chip del encabezado se llenaba INLINE dentro de loadFestival, así que solo
// se pintaba al cargar un festival: cambiar el idioma no lo tocaba. En inglés el
// selector decía «SEP 3–12» (dates_en) y el encabezado seguía en «3–12 SEP» —la
// misma fecha en dos órdenes, a dos toques de distancia—. Es la misma trampa que
// ya tenía resuelta renderPostponedBanner, que persiste y por eso setLang la
// rehornea; el chip no estaba en esa lista.
//
// Se comparan las DOS superficies entre sí y contra el config: que el encabezado
// diga lo del idioma actual, y que en español no se haya movido.
test('I06 — el encabezado usa las fechas del idioma activo', async ({ page }) => {
  await enterFestival(page, 'cinemancia2026');
  const r = await page.evaluate(async () => {
    const w = ms => new Promise(r => setTimeout(r, ms));
    const tap = (a, ds) => { const b = document.createElement('button'); b.setAttribute('data-action', a);
      Object.keys(ds || {}).forEach(k => b.setAttribute('data-' + k, ds[k]));
      document.body.appendChild(b); b.click(); b.remove(); };
    tap('closeCitySheet');
    await w(500);
    const cfg = FESTIVAL_CONFIG[_activeFestId] || {};
    const topbar = () => { const e = document.querySelector('.hdr-fest-dates'); return e ? e.textContent.trim() : null; };
    const es = topbar();
    tap('selectLang', { code: 'en' });
    await w(1400);
    const en = topbar();
    tap('openFestivalSheet');
    await w(900);
    const info = document.querySelector('#fs-info .splash-info-dates');
    return { es, en, selectorEn: info ? info.textContent.trim() : null,
      dates: cfg.dates, datesEn: cfg.dates_en };
  });
  expect(r.datesEn, 'el festival del test declara fechas en inglés — si no, no distingue').toBeTruthy();
  expect(r.datesEn, 'y son un orden DISTINTO del español').not.toBe(r.dates);
  expect(r.es, 'en español el encabezado usa dates').toContain(r.dates);
  expect(r.en, 'en inglés pasa a dates_en').toContain(r.datesEn);
  expect(r.en, 'y deja de mostrar el orden español').not.toContain(r.dates);
  expect(r.selectorEn, 'el selector dice lo mismo que el encabezado').toContain(r.datesEn);
});
