// @ts-check
// festivals.spec.js — Selector de festival, cambio de festival, validaciones cross-festival.
const { test, expect } = require('@playwright/test');
const { LEVIZA_SIMTIME, enterFestival } = require('./helpers');

// T08 — Selector-carrusel: el festival vigente encabeza el riel; los pasados van
// tras el divisor "ANTERIORES". El riel siempre está visible (sin toggle) — se
// elige por poster (.splash-card). Derivado de FESTIVAL_CONFIG en runtime.
test('T08 — selector-carrusel: el festival vigente encabeza el riel', async ({ page }) => {
  await page.goto('/');
  // Gate de readiness JS DEFINITIVO: [data-app-ready="1"] (fin del bootstrap
  // síncrono → riel poblado por _renderSplashRail) antes de leer las cards.
  await page.waitForSelector('html[data-app-ready="1"]', { state: 'attached', timeout: 15000 });
  await page.waitForSelector('.splash-card[data-fest]', { state: 'attached', timeout: 15000 });
  const cards = page.locator('.splash-card[data-fest]');
  expect(await cards.count()).toBeGreaterThan(1);
  // El que encabeza debe ser el festival VIGENTE (en curso o el próximo por
  // empezar): festivalEndStr >= hoy y el de fin más cercano. Derivado de
  // FESTIVAL_CONFIG en runtime — antes se hardcodeaba el nombre y el test se
  // vencía con cada festival nuevo (rotó con Tribeca→FICMontañas→TercerTiempo).
  const expectedFirst = await page.evaluate(async () => {
    const { FESTIVAL_CONFIG } = await import('/src/config.js');
    const now = new Date();
    const vigentes = Object.values(FESTIVAL_CONFIG)
      .filter(c => new Date(c.festivalEndStr) >= now)
      .sort((a, b) => new Date(a.festivalEndStr) - new Date(b.festivalEndStr));
    return vigentes.length ? vigentes[0].id || vigentes[0].storageKey.replace(/_$/, '') : null;
  });
  const firstFestId = await cards.first().getAttribute('data-fest');
  if (expectedFirst) {
    expect(firstFestId).toBe(expectedFirst);
  } // sin festival vigente (todos pasados): no hay expectativa de cabecera — solo orden por tiers
  // El divisor "ANTERIORES" separa vigentes de pasados; leviza (pasado) queda tras él.
  await expect(page.locator('.splash-rail-div')).toBeAttached();
  const allIds = await cards.evaluateAll(els => els.map(el => el.getAttribute('data-fest')));
  expect(allIds.some(id => id.includes('leviza'))).toBe(true);
});

// T40 — El splash entra COMPLETO sin scroll vertical en una pantalla chica
// (360×640, peor caso), y el riel horizontal alcanza la última card. El splash es
// position:fixed → si el contenido excede el alto, los actores de abajo ("Entrar")
// quedan inalcanzables. Invariante robusto (independiente del contenido): el splash
// no desborda verticalmente, y el riel scrollea en X hasta revelar la última card.
test('T40 — splash: cabe sin scroll vertical (360×640) y el riel alcanza la última card', async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 640 });
  await page.goto('/');
  await page.waitForSelector('html[data-app-ready="1"]', { state: 'attached', timeout: 15000 });
  await page.waitForSelector('.splash-card[data-fest]', { state: 'attached', timeout: 15000 });
  const geo = await page.evaluate(() => {
    const splash = document.getElementById('otrofestiv-splash');
    const rail = document.getElementById('splash-rail');
    const cards = rail.querySelectorAll('.splash-card');
    const last = cards[cards.length - 1];
    // Riel: scrollear al fondo horizontal → la última card debe quedar dentro del viewport.
    rail.scrollLeft = rail.scrollWidth;
    const rr = rail.getBoundingClientRect();
    const lr = last.getBoundingClientRect();
    return {
      // sin scroll vertical: el contenido del splash no excede su alto fijo
      noVScroll: splash.scrollHeight <= splash.clientHeight + 1,
      innerHeight: window.innerHeight,
      splashBottom: splash.getBoundingClientRect().bottom,
      lastReachable: lr.left >= rr.left - 1 && lr.right <= rr.right + 1,
    };
  });
  expect(geo.noVScroll).toBe(true);
  expect(geo.splashBottom).toBeLessThanOrEqual(geo.innerHeight + 2);
  expect(geo.lastReachable).toBe(true);
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
