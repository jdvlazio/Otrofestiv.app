// @ts-check
// datos-fuente.spec.js — los datos de un festival salen del almacén `datos`
// (migración 0009) y, si el almacén falla, de la copia de la web de siempre.
// Juan (18 oct 2026): separar los datos del código; nunca peor que antes.
// El almacén se simula con page.route: los tests no dependen de Supabase.
const { test, expect } = require('@playwright/test');
const { enterFestival } = require('./helpers');

const ALMACEN = 'https://eytxrvbnwzxuedbmnnqr.supabase.co/storage/v1/object/public/datos/';
const ARCH = 'festivales/leviza-2026/aaaaaaaaaaaa.json';
const SIM = '2026-05-15T10:00:00-05:00';
// En el servidor de pruebas la app lee los archivos locales (datos-fuente.js);
// estos tests son los del almacén, así que lo encienden a propósito.
const ALM = { query: 'almacen=1' };

// El JSON de la web con UNA obra renombrada: así se sabe de dónde salió.
async function almacenCon(page, { indice, version }) {
  await page.route(ALMACEN + 'indice.json*', r => indice === 'falla'
    ? r.abort() : r.fulfill({ contentType: 'application/json', body: JSON.stringify(indice) }));
  await page.route(ALMACEN + ARCH + '*', async r => {
    if (version === 'falla') return r.abort();
    const web = await (await page.request.get('/festivals/leviza-2026.json')).json();
    web.films[0].title = 'DESDE EL ALMACÉN';
    return r.fulfill({ contentType: 'application/json', body: JSON.stringify(web) });
  });
}
const indiceLeviza = (extra = {}) => ({ version: 1, ...extra, festivales: { 'leviza-2026': { archivo: ARCH } } });
const titulos = page => page.evaluate(() => FILMS.map(f => f.title));
const origen = page => page.evaluate(async () => (await import('/src/controller/datos-fuente.js')).origenDatos.leviza2026);

test('DF1 — un festival que está en el índice se lee del almacén', async ({ page }) => {
  await almacenCon(page, { indice: indiceLeviza(), version: 'ok' });
  await enterFestival(page, 'leviza2026', SIM, ALM);
  expect(await titulos(page)).toContain('DESDE EL ALMACÉN');
  expect(await origen(page)).toBe('almacen');
});

test('DF2 — si el almacén falla, la copia de la web (nunca peor que antes)', async ({ page }) => {
  await almacenCon(page, { indice: indiceLeviza(), version: 'falla' });
  await enterFestival(page, 'leviza2026', SIM, ALM);
  const t = await titulos(page);
  expect(t.length, 'el festival carga igual').toBeGreaterThan(0);
  expect(t).not.toContain('DESDE EL ALMACÉN');
  expect(await origen(page)).toBe('web');
});

test('DF3 — sin índice, o con el interruptor apagado, la web', async ({ page }) => {
  await almacenCon(page, { indice: 'falla', version: 'ok' });
  await enterFestival(page, 'leviza2026', SIM, ALM);
  expect(await titulos(page)).not.toContain('DESDE EL ALMACÉN');
  expect(await origen(page)).toBe('web');
  const p2 = await page.context().newPage();
  await almacenCon(p2, { indice: indiceLeviza({ apagado: true }), version: 'ok' });
  await enterFestival(p2, 'leviza2026', SIM, ALM);
  expect(await titulos(p2)).not.toContain('DESDE EL ALMACÉN');
});

test('DF4 — un festival que NO está en el índice sigue leyendo la web', async ({ page }) => {
  await almacenCon(page, { indice: { version: 1, festivales: {} }, version: 'ok' });
  await enterFestival(page, 'leviza2026', SIM, ALM);
  expect(await titulos(page)).not.toContain('DESDE EL ALMACÉN');
  expect(await origen(page)).toBe('web');
});

// DF6 — en el servidor de pruebas, sin ?almacen=1, se lee el archivo LOCAL aunque
// el almacén lo tenga: es lo que se va a publicar y lo que los tests tienen que ver
// (19 oct 2026: publicar-datos y el CI de datos probaban la versión ya publicada).
test('DF6 — en el servidor de pruebas manda el archivo local', async ({ page }) => {
  await almacenCon(page, { indice: indiceLeviza(), version: 'ok' });
  await enterFestival(page, 'leviza2026', SIM);
  expect(await titulos(page)).not.toContain('DESDE EL ALMACÉN');
  expect(await origen(page)).toBe('web');
});

// ── Etapa 2·B1 (19 oct 2026): la FICHA del festival viene en el índice ─────────
// La portada sale con la última ficha guardada y se re-dibuja si el índice trae
// otra. Es lo que permite cambiar un afiche o una fecha sin publicar la app.
const KEYART = ALMACEN + 'keyart/aaaaaaaaaaaa.jpg';
async function indiceConFicha(page, ficha) {
  await page.route(ALMACEN + 'indice.json*', r => r.fulfill({ contentType: 'application/json',
    body: JSON.stringify({ version: 1, festivales: { 'leviza-2026': { archivo: ARCH, ficha } } }) }));
  await page.route(KEYART + '*', async r => r.fulfill({ contentType: 'image/jpeg',
    body: (await page.request.get('/assets/keyart/leviza2026.jpg')).body() }));
}
const cardLeviza = page => page.locator('#splash-rail .splash-card[data-fest="leviza2026"]');

test('DF7 — una ficha nueva en el índice cambia la portada sin publicar la app', async ({ page }) => {
  await indiceConFicha(page, { city: 'Ciudad Prueba', keyArt: KEYART });
  await page.goto('/?almacen=1&simTime=' + encodeURIComponent(SIM));
  await page.waitForSelector('html[data-app-ready="1"]', { state: 'attached', timeout: 15000 });
  await expect(cardLeviza(page)).toHaveAttribute('data-meta', /Ciudad Prueba/, { timeout: 10000 });
  await expect(cardLeviza(page).locator('img')).toHaveAttribute('src', KEYART);
  // y queda guardada para el próximo arranque
  const guardada = await page.evaluate(() => JSON.parse(localStorage.getItem('otf_fichas_v1') || '{}'));
  expect(guardada.leviza2026 && guardada.leviza2026.city).toBe('Ciudad Prueba');
});

test('DF8 — el próximo arranque sale YA con la ficha guardada, aunque no haya red', async ({ page }) => {
  await page.addInitScript(([k]) => {
    if (!localStorage.getItem(k)) localStorage.setItem(k, JSON.stringify({ leviza2026: { city: 'Guardada' } }));
  }, ['otf_fichas_v1']);
  await page.route(ALMACEN + '**', r => r.abort());   // sin almacén: solo lo guardado
  await page.goto('/?almacen=1&simTime=' + encodeURIComponent(SIM));
  await page.waitForSelector('html[data-app-ready="1"]', { state: 'attached', timeout: 15000 });
  await expect(cardLeviza(page)).toHaveAttribute('data-meta', /Guardada/);
});

test('DF9 — almacén apagado: la portada vuelve a la copia de la app', async ({ page }) => {
  await page.route(ALMACEN + 'indice.json*', r => r.fulfill({ contentType: 'application/json',
    body: JSON.stringify({ version: 1, apagado: true, festivales: { 'leviza-2026': { archivo: ARCH, ficha: { city: 'NO' } } } }) }));
  await page.goto('/?almacen=1&simTime=' + encodeURIComponent(SIM));
  await page.waitForSelector('html[data-app-ready="1"]', { state: 'attached', timeout: 15000 });
  await page.waitForTimeout(1500);
  await expect(cardLeviza(page)).not.toHaveAttribute('data-meta', /NO ·/);
  expect(await page.evaluate(() => localStorage.getItem('otf_fichas_v1'))).toBe('{}');
});
