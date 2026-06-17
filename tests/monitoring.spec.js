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

// Bloquear el Service Worker SOLO en el monitor. El SW de prod (sw.js v15) hace
// clients.navigate(client.url) en cada activate → recarga la página al instalarse.
// En el runner frío de CI esa recarga dispara un SEGUNDO cold-load (13 módulos ESM
// + JSON 452 KB) que se cuelga, y waitForSelector queda esperando "navigation to
// finish" hasta el timeout (causa raíz de los falsos positivos #133–#137). Sin SW
// el monitor hace UNA carga determinista desde red — que es justo lo que valida:
// "prod sirve una app que arranca y carga el festival". La cobertura del SW vive
// en la suite de regresión (playwright.yml), no acá.
test.use({ serviceWorkers: 'block' });

// Presupuesto ampliado vs el global (30s): el loader reintenta el fetch del
// JSON de festival hasta 3×6s (#194) ante stalls del CDN de GitHub Pages —
// peor caso ~18s ANTES de que el grid pueda renderizar. 60s da margen al cold-load
// del runner de CI (HTML + 13 módulos ESM + JSON 452 KB) bajo latencia del edge,
// sin tapar lentitud real.
test.describe.configure({ timeout: 60000 });

// Helper: entra al primer festival disponible en producción
async function enterFirstFestival(page) {
  // waitUntil:'domcontentloaded' — no esperar a TODOS los subrecursos ni al settle
  // del reload del SW (que en runner frío puede colgar el evento 'load' → "navigation
  // to finish" nunca resuelve, el fallo observado en prod). El gate real de readiness
  // es [data-app-ready], que se espera abajo.
  await page.goto('/', { waitUntil: 'domcontentloaded' });
  // Gate de readiness JS DEFINITIVO: [data-app-ready="1"] (fin del bootstrap
  // síncrono). #splash-sel-btn es estático → no es señal válida (flaky).
  await page.waitForSelector('html[data-app-ready="1"]', { state: 'attached', timeout: 15000 });
  // El selector arranca SIN festival pre-elegido (placeholder "Elegí uno"): hay que
  // elegir uno para habilitar "Entrar". Tomamos el primero disponible de forma
  // determinista (contrato: festival-agnóstico, no hardcodear IDs). Los items existen
  // en el DOM aunque el dropdown esté cerrado (render en el bootstrap).
  await page.waitForSelector('.splash-drop-item[data-fest]', { state: 'attached', timeout: 15000 });
  await page.evaluate(() => {
    const first = document.querySelector('.splash-drop-item[data-fest]');
    if (first) selectSplashFest(first.dataset.name, first.dataset.meta, first.dataset.fest);
  });
  // Esperar que el botón sea visible (la animación puede tardar hasta 1.1s)
  await page.waitForSelector('.splash-enter-btn', { state: 'visible', timeout: 10000 });
  await page.locator('.splash-enter-btn').click({ force: true });
  // 40s: 18s del peor caso de retries del loader (#194) + render, con margen para
  // el cold-load del runner bajo latencia del edge de Pages.
  await page.waitForSelector('.poster-card, .plist-item, .dtab', { timeout: 40000 });
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
  await page.goto('/', { waitUntil: 'domcontentloaded' });  // ver enterFirstFestival
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
