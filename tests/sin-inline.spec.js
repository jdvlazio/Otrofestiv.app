// @ts-check
// sin-inline.spec.js — los handlers que vivían en el HTML (on*="…") pasaron a
// listeners delegados (src/controller/sin-inline.js, 26 oct 2026) para que la CSP
// pueda dejar 'unsafe-inline'. Estos tests ejercen los tres atributos nuevos.
const { test, expect } = require('@playwright/test');
const { LEVIZA_SIMTIME, enterFestival } = require('./helpers');

test('SI01 — data-enter: Enter en el campo dispara la acción del registro', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => {
    const i = document.createElement('input'); i.id = 'si01'; i.dataset.enter = 'openAuthSheet';
    document.body.appendChild(i);
  });
  await page.locator('#si01').press('Enter');
  await expect(page.locator('#auth-sheet.open')).toHaveCount(1, { timeout: 5000 });
});

test('SI02 — Enter en la clave de revisión ya no tira ReferenceError', async ({ page }) => {
  // Antes: onkeydown llamaba a un submitReviewKey GLOBAL que no existía.
  const errores = [];
  page.on('pageerror', e => errores.push(e.message));
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => { const s = document.getElementById('review-sheet'); if (s) { s.style.display = 'block'; s.classList.add('open'); } });
  await page.locator('#review-key-inp').press('Enter');
  await page.waitForTimeout(300);
  expect(errores).toEqual([]);
});

test('SI03 — data-err="ocultar": la imagen que no carga se oculta', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => {
    const im = document.createElement('img'); im.id = 'si03'; im.dataset.err = 'ocultar';
    im.src = '/assets/no-existe-' + Date.now() + '.jpg'; document.body.appendChild(im);
  });
  await expect.poll(() => page.evaluate(() => document.getElementById('si03').style.visibility), { timeout: 5000 }).toBe('hidden');
});

test('SI04 — data-buscar: escribir en el buscador busca', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => searchOpen());
  await page.locator('#search-input').fill('a');
  await expect.poll(() => page.locator('#search-results').innerHTML().then(h => h.length), { timeout: 5000 }).toBeGreaterThan(0);
});
