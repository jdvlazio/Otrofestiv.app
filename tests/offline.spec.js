// @ts-check
// offline.spec.js — La red de seguridad del caso "avión / sótano del teatro".
// Cubre la capa menos testeada (offline). Verifica la GARANTÍA real: tras una
// visita online, el Service Worker debe permitir abrir la app SIN red y que el
// programa siga disponible desde caché. Nace del incidente del vuelo (jul 2026).
const { test, expect } = require('@playwright/test');
const { LEVIZA_SIMTIME, selectFestival, enterFestival } = require('./helpers');

const FEST = 'leviza2026';

// T46 — La app abre offline tras una visita online (shell + JSON desde caché del SW).
test('T46 — abre offline tras visita online (shell + programa desde caché)', async ({ page, context }) => {
  // 1) Visita ONLINE: puebla la caché del SW (index + módulos + JSON del festival).
  await enterFestival(page, FEST, LEVIZA_SIMTIME);

  // 2) Esperar a que el SW CONTROLE la página (el activate ya corrió, incluido su
  //    navigate) y a que el shell mínimo esté cacheado. Sin este gate, cortar la red
  //    antes de que el SW cachee daría un falso negativo.
  await page.waitForFunction(
    () => !!(navigator.serviceWorker && navigator.serviceWorker.controller),
    null, { timeout: 15000 }
  );
  await page.waitForFunction(async () => {
    const names = await caches.keys();
    for (const n of names) {
      const ks = await (await caches.open(n)).keys();
      const paths = ks.map(r => new URL(r.url).pathname);
      const hasDoc  = paths.includes('/') || paths.includes('/index.html');
      const hasMain = paths.some(p => p.startsWith('/src/main.js'));
      const hasJson = paths.some(p => p.startsWith('/festivals/'));
      if (hasDoc && hasMain && hasJson) return true;
    }
    return false;
  }, null, { timeout: 15000 });

  // 3) CORTAR la red. A partir de aquí, todo debe salir de la caché.
  await context.setOffline(true);
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));

  // 4) Recargar SIN red: el shell debe arrancar desde caché (network-first → catch → caché).
  await page.reload();
  await page.waitForSelector('html[data-app-ready="1"]', { state: 'attached', timeout: 15000 });
  await page.waitForFunction(
    () => typeof FESTIVAL_CONFIG !== 'undefined' && typeof selectSplashFest === 'function',
    null, { timeout: 15000 }
  );

  // 5) Entrar al festival OFFLINE y confirmar que el programa está (JSON desde caché).
  await selectFestival(page, FEST);
  await page.locator('.splash-enter-btn').click();
  await page.waitForSelector('.poster-card, .plist-item, .dtab', { timeout: 15000 });
  const filmCount = await page.evaluate(() => typeof FILMS !== 'undefined' ? FILMS.length : 0);

  // Restaurar la red antes del teardown (no contaminar el contexto).
  await context.setOffline(false);

  const realErrors = errors.filter(e =>
    !e.includes('extension') && !e.includes('chrome-extension') && !e.includes('sentry')
  );
  expect(realErrors, 'la app arranca offline sin errores JS').toHaveLength(0);
  expect(filmCount, 'el programa (FILMS) está disponible offline desde caché').toBeGreaterThan(0);
});
