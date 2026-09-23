// @ts-check
// i18n-boot.spec.js — Coherencia de idioma AL ARRANQUE (regresión del store-gate).
//
// EL BUG (reportado por Juan): iPhone en EN, primer uso → la UI ESTÁTICA del HTML
// (tabs del nav, bandera del toggle) se queda en ES hardcodeado mientras el
// contenido dinámico (días, secciones) sale en EN = MEZCLA. Causa: main.js se
// inyecta como módulo (store-gate) → el listener DOMContentLoaded que aplicaba el
// i18n registraba para un evento YA disparado y nunca corría. Fix: onDomReady()
// en main.js (src/util/ready.js).
//
// GUARDIÁN PRINCIPAL DE LA REGRESIÓN: el check estructural [dom-ready-guard] en
// validate.py — prohíbe `addEventListener('DOMContentLoaded'|'load')` desnudo en
// src/ (determinista, en cada commit). Es más fuerte que este test: el bug de
// TIMING solo se manifiesta bajo WebKit (motor de iOS), y ahí `enterFestival` es
// flaky por cold-context; en Chromium el listener alcanza a correr y enmascara el
// timing. Verificado MANUALMENTE que sin el fix, bajo WebKit el nav sale
// "PROGRAMA/INTERESES/PLANEAR/MI PLAN" con locale EN.
//
// Estos tests (Chromium) validan el INVARIANTE de coherencia: sin tocar el
// selector, la UI estática coincide con el idioma detectado — y atrapan otras
// regresiones (una traducción faltante, la bandera desincronizada).
const { test, expect } = require('@playwright/test');
const { LEVIZA_SIMTIME, enterFestival } = require('./helpers');

test.describe('coherencia al arranque (locale EN)', () => {
  test.use({ locale: 'en-US' });
  test('I06 — arranque EN: nav + bandera en EN sin toggle (cero mezcla)', async ({ page }) => {
    await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);  // NO se toca el selector de idioma
    await expect(page.locator('#lbl-nav-miplan')).toContainText(/my plan/i); // EN presente
    await expect(page.locator('#lang-trigger-code')).toHaveText('EN');       // código coincide
    await expect(page.locator('#lang-btn-en.on')).toHaveCount(1);          // botón activo EN
    const nav = (await page.locator('.main-nav-tab').allTextContents()).join(' ').toUpperCase();
    expect(nav).not.toContain('MI PLAN');   // sin ES mezclado
  });
});

test.describe('coherencia al arranque (locale ES)', () => {
  test.use({ locale: 'es-CO' });
  test('I07 — arranque ES: nav + bandera en ES sin toggle', async ({ page }) => {
    await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
    await expect(page.locator('#lbl-nav-miplan')).toContainText(/mi plan/i);
    await expect(page.locator('#lang-trigger-code')).toHaveText('ES');
    // Sin banderas (22 sep 2026, Juan): una bandera nombra un país, no un idioma.
    // Se vigila el selector ENTERO, trigger y opciones: cero indicadores regionales.
    const toggle = await page.locator('#lang-toggle').textContent();
    expect(toggle, `el selector de idioma no lleva banderas (tiene: ${toggle.trim()})`).not.toMatch(/[\u{1F1E6}-\u{1F1FF}]/u);
    expect(toggle.replace(/\s+/g, ' ').trim(), 'códigos y nombres, en ese orden').toMatch(/ES.*ES\s*Español.*EN\s*English/);
    // Y en el HTML SERVIDO, no solo en el DOM: el boot sincroniza el trigger con la
    // opción activa, así que una bandera dejada en el markup se «cura» sola y el DOM
    // no la delata (mutación cazada al escribir esto).
    const html = await (await page.request.get('/')).text();
    const markup = html.slice(html.indexOf('id="lang-toggle"'), html.indexOf('id="auth-btn"'));
    expect(markup, 'el markup del selector tampoco lleva banderas').not.toMatch(/[\u{1F1E6}-\u{1F1FF}]/u);
    const nav = (await page.locator('.main-nav-tab').allTextContents()).join(' ').toUpperCase();
    expect(nav).not.toContain('MY PLAN');
  });
});
