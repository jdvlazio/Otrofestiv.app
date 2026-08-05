// ── store-gate.spec.js — matriz de UAs del STORE GATE (v4) ────────────────────
// El gate vive inline en index.html y decide app vs landing de tiendas. En
// localhost es isDev → siempre app, así que acá se sirve el index.html REAL
// bajo un dominio simulado (route-fulfill) para ejercitar el camino de prod.
//
// Historia: v2 = confirmación positiva de navegador (fail-open hacia la app,
// incidente 5 jul). v3 = jamás usar webkit.messageHandlers como señal (Firefox
// iOS es WKWebView con handlers propios — cazado por Juan; por eso acá se
// INYECTA window.webkit vía addInitScript: Playwright emula UA pero no el
// objeto webkit, la matriz v2 no lo cazó). v4 (23 jul, prep difusión
// Argentina) = in-app browsers que declaran token en el UA (Instagram/FB:
// Instagram, FBAN/FBAV/FB_IAB) → LANDING: son el funnel de difusión social y
// antes caían como WebView → veían la web app en vez de "descargá la app".
// X/Twitter iOS NO declara token → sigue cayendo como WebView (app): costo
// aceptado hasta que los wrappers nativos anuncien UA propio.

const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

const INDEX = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
const FAKE = 'https://otrofestiv.test/';

const UA = {
  igIOS: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/21F90 Instagram 334.0.0.30.109 (iPhone14,5; iOS 17_5; es_CO)',
  igAndroid: 'Mozilla/5.0 (Linux; Android 14; Pixel 8 Build/UD1A.230803; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/126.0.6478.71 Mobile Safari/537.36 Instagram 334.0.0.30.109',
  fbIOS: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/21F90 [FBAN/FBIOS;FBAV/467.0.0.28.303;FBDV/iPhone14,5]',
  wrapperIOS: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148',
  wrapperAndroid: 'Mozilla/5.0 (Linux; Android 14; Pixel 8; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/126.0.6478.71 Mobile Safari/537.36',
  safariIOS: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1',
  chromeAndroid: 'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.6478.71 Mobile Safari/537.36',
  fxIOS: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) FxiOS/127.0 Mobile/15E148 Safari/605.1.15',
  fbAndroid: 'Mozilla/5.0 (Linux; Android 14; Pixel 8 Build/UD1A.230803; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/126.0.6478.71 Mobile Safari/537.36 [FB_IAB/FB4A;FBAV/467.0.0.28.303;]',
  xAndroid: 'Mozilla/5.0 (Linux; Android 15; Pixel 8; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/126.0.6478.71 Mobile Safari/537.36 TwitterAndroid',
};

// Contexto aislado por caso: UA propio + rutas que sirven el index real y un
// version.json con el gate ENCENDIDO (como prod). main.js se sirve vacío: el
// assert de "app" es que el gate INTENTÓ bootear (inyectó el script módulo).
async function open(browser, ua, { webkitHandlers = false, versionJson = { storeGate: true, android: 1, ios: 1 } } = {}) {
  const context = await browser.newContext({ userAgent: ua, viewport: { width: 390, height: 844 } });
  const page = await context.newPage();
  if (webkitHandlers) {
    // Lección v3: los browsers de terceros en iOS SON WKWebViews con handlers.
    await page.addInitScript(() => { window.webkit = { messageHandlers: { dummy: {} } }; });
  }
  await context.route('**/*', (route) => {
    const url = route.request().url();
    if (url === FAKE || url === FAKE + 'index.html') {
      return route.fulfill({ contentType: 'text/html', body: INDEX });
    }
    if (url.includes('version.json')) {
      if (versionJson === 'FAIL') return route.fulfill({ status: 500, body: 'boom' });
      return route.fulfill({ contentType: 'application/json', body: JSON.stringify(versionJson) });
    }
    if (url.includes('main.js')) return route.fulfill({ contentType: 'text/javascript', body: '/* stub */' });
    return route.fulfill({ status: 204, body: '' });
  });
  await page.goto(FAKE);
  return { context, page };
}

async function expectLanding(page) {
  await expect(page.locator('.sg-wrap')).toBeVisible({ timeout: 5000 });
  await expect(page.locator('.sg-btn').first()).toBeVisible(); // botón de tienda
  expect(await page.locator('script[type="module"][src*="main.js"]').count()).toBe(0);
}

async function expectApp(page) {
  await expect(page.locator('script[type="module"][src*="main.js"]')).toHaveCount(1, { timeout: 5000 });
  expect(await page.locator('.sg-wrap').count()).toBe(0);
}

test.describe('store gate v4 — matriz de UAs', () => {
  test('SG1 Instagram iOS (in-app, sin Safari/) → LANDING', async ({ browser }) => {
    const { context, page } = await open(browser, UA.igIOS);
    await expectLanding(page); await context.close();
  });

  test('SG2 Instagram Android (in-app, "; wv)") → LANDING', async ({ browser }) => {
    const { context, page } = await open(browser, UA.igAndroid);
    await expectLanding(page); await context.close();
  });

  test('SG3 Facebook iOS (FBAN/FBAV) → LANDING', async ({ browser }) => {
    const { context, page } = await open(browser, UA.fbIOS);
    await expectLanding(page); await context.close();
  });

  test('SG4 wrapper iOS (WKWebView sin Safari/, sin token) → APP', async ({ browser }) => {
    const { context, page } = await open(browser, UA.wrapperIOS);
    await expectApp(page); await context.close();
  });

  test('SG5 wrapper Android ("; wv)" sin token) → APP', async ({ browser }) => {
    const { context, page } = await open(browser, UA.wrapperAndroid);
    await expectApp(page); await context.close();
  });

  test('SG6 Safari iOS real → LANDING', async ({ browser }) => {
    const { context, page } = await open(browser, UA.safariIOS);
    await expectLanding(page); await context.close();
  });

  test('SG7 Chrome Android real → LANDING', async ({ browser }) => {
    const { context, page } = await open(browser, UA.chromeAndroid);
    await expectLanding(page); await context.close();
  });

  test('SG8 Firefox iOS (WKWebView de tercero CON handlers) → LANDING (lección v3)', async ({ browser }) => {
    const { context, page } = await open(browser, UA.fxIOS, { webkitHandlers: true });
    await expectLanding(page); await context.close();
  });

  test('SG9 fail-open: version.json cae, incluso con UA Instagram → APP (proteger la app > el push)', async ({ browser }) => {
    const { context, page } = await open(browser, UA.igIOS, { versionJson: 'FAIL' });
    await expectApp(page); await context.close();
  });

  test('SG10 kill-switch: storeGate=false → APP hasta en Safari real', async ({ browser }) => {
    const { context, page } = await open(browser, UA.safariIOS, { versionJson: { storeGate: false } });
    await expectApp(page); await context.close();
  });

  // INVARIANTE CENTRAL del v4 (doble revisión, revisor A): hasCapacitor gana
  // SIEMPRE — incluso con token de in-app browser en el UA, la app real jamás
  // ve la landing. Una regresión que reordene el || debe caer acá.
  test('SG11 Capacitor + UA Instagram → APP (hasCapacitor gana al token)', async ({ browser }) => {
    const context = await browser.newContext({ userAgent: UA.igIOS, viewport: { width: 390, height: 844 } });
    const page = await context.newPage();
    await page.addInitScript(() => { window.Capacitor = { isNativePlatform: () => true }; });
    await context.route('**/*', (route) => {
      const url = route.request().url();
      if (url === FAKE || url === FAKE + 'index.html') return route.fulfill({ contentType: 'text/html', body: INDEX });
      if (url.includes('version.json')) return route.fulfill({ contentType: 'application/json', body: JSON.stringify({ storeGate: true }) });
      if (url.includes('main.js')) return route.fulfill({ contentType: 'text/javascript', body: '/* stub */' });
      return route.fulfill({ status: 204, body: '' });
    });
    await page.goto(FAKE);
    await expectApp(page); await context.close();
  });

  test('SG12 Facebook Android (FB_IAB/FB4A) → LANDING', async ({ browser }) => {
    const { context, page } = await open(browser, UA.fbAndroid);
    await expectLanding(page); await context.close();
  });

  test('SG13 X/Twitter Android (TwitterAndroid) → LANDING (revisor B)', async ({ browser }) => {
    const { context, page } = await open(browser, UA.xAndroid);
    await expectLanding(page); await context.close();
  });
});

// ── SG14/SG15 — el badge de App Store NAVEGA en el webview (2 ago 2026) ───────
// Bug de campaña FINCA: en el in-app browser de Instagram el tap al badge de
// Apple "no hacía nada". Los webviews de IG/FB BLOQUEAN el handoff del
// universal link apps.apple.com a la app de App Store (la navegación se
// cancela en silencio). Workaround estándar de la industria (Branch/AppsFlyer):
// en iOS el href usa itms-apps:// — el esquema sí pasa al sistema, y en Safari
// normal también abre App Store directo. Android/desktop conservan https
// (la página web, que resuelve desde #496 con storefront + slug).
test.describe('store gate v4 — badge de App Store por plataforma', () => {
  // v2 (2 ago): IG bloquea TAMBIÉN itms-apps (confirmado en el teléfono de Juan)
  // → en in-app browsers el badge va a /get/, que redirige y tiene el rescate.
  test('SG14 Instagram iOS → badge Apple hacia /get/ (funnel con rescate)', async ({ browser }) => {
    const { context, page } = await open(browser, UA.igIOS);
    await page.waitForSelector('.sg-btn', { timeout: 8000 });
    const hrefs = await page.evaluate(() => [...document.querySelectorAll('.sg-btn')].map(a => a.getAttribute('href')));
    expect(hrefs.some(h => h === '/get/')).toBe(true);
    await context.close();
  });
  test('SG14b Safari iOS (fuera de webview) → badge Apple directo con itms-apps://', async ({ browser }) => {
    const { context, page } = await open(browser, UA.safariIOS);
    await page.waitForSelector('.sg-btn', { timeout: 8000 });
    const hrefs = await page.evaluate(() => [...document.querySelectorAll('.sg-btn')].map(a => a.getAttribute('href')));
    expect(hrefs.some(h => h.startsWith('itms-apps://apps.apple.com/co/app/otrofestiv/id6769367002'))).toBe(true);
    await context.close();
  });
  // SG16 — el RESCATE de /get: si el webview frena el redirect (acá: 204 = la
  // navegación no ocurre), a los 1.6s aparece el rescate con reintento itms-apps
  // + instrucción del menú ···. Es la red del funnel de campaña (IG stories/bio).
  test('SG16 /get en IG iOS con redirect bloqueado → muestra el rescate', async ({ browser }) => {
    const GET = fs.readFileSync(path.join(__dirname, '..', 'get', 'index.html'), 'utf8');
    const context = await browser.newContext({ userAgent: UA.igIOS, viewport: { width: 390, height: 844 }, locale: 'es-CO' });
    const page = await context.newPage();
    await context.route('**/*', (route) => {
      const url = route.request().url();
      if (url.startsWith(FAKE + 'get')) return route.fulfill({ contentType: 'text/html', body: GET });
      if (url.includes('apps.apple.com')) return route.fulfill({ status: 204, body: '' }); // el webview "se traga" la navegación
      return route.fulfill({ status: 204, body: '' });
    });
    // waitUntil commit: el location.replace inline aborta el 'load' del goto
    // (la navegación al store devuelve 204 y la página original sigue viva).
    await page.goto(FAKE + 'get/', { waitUntil: 'commit' });
    await page.waitForSelector('#rescate', { state: 'visible', timeout: 5000 });
    const r = await page.evaluate(() => ({
      titulo: document.getElementById('r-t').textContent,
      btn: document.getElementById('r-btn').getAttribute('href'),
      alt: document.getElementById('r-alt').style.display !== 'none',
    }));
    expect(r.titulo).toContain('Instagram');
    expect(r.btn.startsWith('itms-apps://apps.apple.com/co/app/otrofestiv/')).toBe(true);
    expect(r.alt).toBe(true); // la instrucción del ··· SÍ se muestra en webview
    await context.close();
  });
  test('SG15 Instagram Android → badge Apple https (página web) + Play intacto', async ({ browser }) => {
    const { context, page } = await open(browser, UA.igAndroid);
    await page.waitForSelector('.sg-btn', { timeout: 8000 });
    const hrefs = await page.evaluate(() => [...document.querySelectorAll('.sg-btn')].map(a => a.getAttribute('href')));
    expect(hrefs.some(h => h.startsWith('https://apps.apple.com/co/app/otrofestiv/id6769367002'))).toBe(true);
    expect(hrefs.some(h => h.includes('play.google.com/store/apps/details'))).toBe(true);
    await context.close();
  });
});
