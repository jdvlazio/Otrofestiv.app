// @ts-check
// monitoring.spec.js — Synthetic monitoring para producción (otrofestiv.app)
//
// CONTRATO: estos tests deben pasar sin importar:
//   - qué festival esté activo
//   - en qué fecha corra
//   - cuántos festivales haya en el selector
//
// NO usan LEVIZA_SIMTIME, NO hardcodean festival IDs.
// Entran al primer festival disponible y verifican invariantes universales.

const { test, expect } = require('@playwright/test');

// Helper: entra al primer festival disponible en producción.
//
// TOLERA un reload del Service Worker mid-test. En la primera carga de un contexto
// fresco (lo que el monitor siempre usa, y lo que vive un visitante nuevo), el SW
// instala y al tomar control dispara `controllerchange` → `location.reload()`
// (main.js:1691-1700). Si ese reload cae DESPUÉS del click en "Entrar", la app
// reinicia al splash y el contenido del festival nunca aparece en esa navegación.
// Antes el helper asumía UNA sola navegación → timeout 20s ("navigation to finish")
// → falso rojo del synthetic monitor (no un break de producto; ver diagnóstico).
//
// Fix: no asumir una navegación única. Reintentar el "entrar" (re-esperar
// data-app-ready + re-click si volvimos al splash) hasta que el contenido del
// festival quede ESTABLE. El reload del SW ocurre una vez por contexto, así que el
// loop converge; el presupuesto total acota el peor caso.
async function enterFirstFestival(page) {
  await page.goto('/');
  const deadline = Date.now() + 45000;
  while (Date.now() < deadline) {
    // (re)esperar fin del bootstrap — tras un reload del SW, el nuevo bootstrap
    // vuelve a setear data-app-ready. #splash-sel-btn es estático → no es señal válida.
    await page.waitForSelector('html[data-app-ready="1"]', { state: 'attached', timeout: 15000 });
    // Si seguimos/volvimos al splash, entrar. (La animación puede tardar ~1.1s en
    // hacer visible el botón; isVisible no espera, así que damos un waitForSelector corto.)
    const enterBtn = page.locator('.splash-enter-btn');
    await page.waitForSelector('.splash-enter-btn', { state: 'visible', timeout: 10000 }).catch(() => {});
    if (await enterBtn.isVisible().catch(() => false)) {
      await enterBtn.click({ force: true }).catch(() => {});
    }
    // ¿Contenido del festival estable? Si un reload del SW cae después del click,
    // esta espera corta falla → el loop reintenta (re-espera ready + re-entra).
    try {
      await page.waitForSelector('.poster-card, .plist-item, .dtab', { state: 'visible', timeout: 6000 });
      return; // entramos y el contenido es estable
    } catch { /* probable reload del SW → reintentar */ }
  }
  // Garantía final: si de verdad no hay contenido, que el assert del test lo reporte.
  await page.waitForSelector('.poster-card, .plist-item, .dtab', { state: 'visible', timeout: 10000 });
}

// M01 — La app carga sin errores JS críticos
test('M01 — app carga sin errores JS', async ({ page }) => {
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await enterFirstFestival(page);
  const critical = errors.filter(e =>
    !e.includes('extension') &&
    !e.includes('chrome-extension') &&
    !e.includes('sentry') &&
    !e.includes('clarity')
  );
  expect(critical).toHaveLength(0);
});

// M02 — El selector de festival tiene al menos un festival
test('M02 — selector tiene al menos un festival', async ({ page }) => {
  await page.goto('/');
  // Gate de readiness JS DEFINITIVO antes de click en #splash-sel-btn (estático).
  await page.waitForSelector('html[data-app-ready="1"]', { state: 'attached', timeout: 15000 });
  await page.locator('#splash-sel-btn').click();
  await page.waitForSelector('#splash-dropdown', { state: 'visible', timeout: 15000 });
  await page.waitForSelector('.splash-drop-item[data-fest]', { state: 'visible', timeout: 15000 });
  const count = await page.locator('.splash-drop-item[data-fest]').count();
  expect(count).toBeGreaterThan(0);
});

// M03 — El festival activo tiene films
test('M03 — festival activo tiene films', async ({ page }) => {
  await enterFirstFestival(page);
  const filmCount = await page.evaluate(() =>
    typeof FILMS !== 'undefined' ? FILMS.length : 0
  );
  expect(filmCount).toBeGreaterThan(0);
});

// M04 — Los 4 tabs navegan sin errores JS
test('M04 — 4 tabs sin errores JS', async ({ page }) => {
  await enterFirstFestival(page);
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  for (const [nav, ag] of [
    ['mnav-seleccion', true],
    ['mnav-planner', true],
    ['mnav-miplan', true],
    ['mnav-cartelera', false],
  ]) {
    await page.evaluate(([n, a]) => {
      switchMainNav(n);
      if (a) showAgView();
    }, [nav, ag]);
    await page.waitForTimeout(400);
  }
  const critical = errors.filter(e => !e.includes('sentry') && !e.includes('clarity'));
  expect(critical).toHaveLength(0);
});

// M05 — El topbar muestra nombre del festival
test('M05 — topbar muestra nombre del festival', async ({ page }) => {
  await enterFirstFestival(page);
  await page.waitForSelector('.hdr-fest-name', { timeout: 5000 });
  const name = await page.locator('.hdr-fest-name').textContent();
  expect(name?.trim().length).toBeGreaterThan(0);
});
