// @ts-check
// smoke.spec.js — Checks críticos: si alguno falla, nada más importa.
// Criterio: ¿la app carga? ¿los tabs responden? ¿hay datos de films?
const { test, expect } = require('@playwright/test');
const { LEVIZA_SIMTIME, enterFestival } = require('./helpers');

// T34 — App carga sin errores JS en consola
test('T34 — carga inicial sin errores JS', async ({ page }) => {
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  const realErrors = errors.filter(e =>
    !e.includes('extension') && !e.includes('chrome-extension') && !e.includes('sentry')
  );
  expect(realErrors).toHaveLength(0);
});

// T35 — App carga sin errores JS en Tribeca
test('T35 — carga Tribeca sin errores JS', async ({ page }) => {
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await enterFestival(page, 'tribeca2026');
  const realErrors = errors.filter(e =>
    !e.includes('extension') && !e.includes('chrome-extension') && !e.includes('sentry')
  );
  expect(realErrors).toHaveLength(0);
});

// T32 — Nav: cambio entre los 4 tabs funciona sin errores JS
test('T32 — navegar entre los 4 tabs no lanza errores', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  for (const [nav, needsAg] of [['mnav-seleccion',true],['mnav-planner',true],['mnav-miplan',false],['mnav-cartelera',false]]) {
    await page.evaluate(([n, ag]) => { switchMainNav(n); if(ag) showAgView(); }, [nav, needsAg]);
    await page.waitForTimeout(400);
  }
  expect(errors).toHaveLength(0);
});

// T38 — Festival: JSON de festival carga con films
test('T38 — JSON del festival tiene films', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  const filmCount = await page.evaluate(() => typeof FILMS !== 'undefined' ? FILMS.length : 0);
  expect(filmCount).toBeGreaterThan(0);
});
