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
