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
  // los campos REALES apuntan a la acción correcta (un typo en index.html pasaría)
  const enter = await page.evaluate(() => ['auth-email-inp', 'auth-otp-inp', 'review-key-inp']
    .map(id => document.getElementById(id).dataset.enter));
  expect(enter).toEqual(['submitAuthEmail', 'submitOTP', 'submitReviewKey']);
});

test('SI02 — Enter en la clave de revisión valida como el botón', async ({ page }) => {
  // Antes: onkeydown llamaba a un submitReviewKey GLOBAL que no existía
  // (ReferenceError) y Enter no hacía nada. Ahora: clave mala → mensaje; buena → entra.
  const errores = [];
  page.on('pageerror', e => errores.push(e.message));
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(async () => {
    const { FESTIVAL_CONFIG } = await import('/src/config.js');
    FESTIVAL_CONFIG.leviza2026.review = { key: 'clave-si02' };
    const { openReviewSheet } = await import('/src/view/sheets.js');
    openReviewSheet('leviza2026');
  });
  await expect(page.locator('#review-sheet.open')).toHaveCount(1, { timeout: 5000 });
  await page.locator('#review-key-inp').fill('mala');
  await page.locator('#review-key-inp').press('Enter');
  await expect(page.locator('#review-msg')).not.toHaveText('', { timeout: 5000 });
  await page.locator('#review-key-inp').fill('clave-si02');
  await page.locator('#review-key-inp').press('Enter');
  await expect(page.locator('#review-sheet.open')).toHaveCount(0, { timeout: 5000 });
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
  // searchOpen busca sola en su rAF si el campo ya tiene texto: esperar a que abra
  // del todo, o el test mide esa búsqueda y no la del listener (auditoría, 26 oct)
  await page.waitForFunction(() => document.getElementById('search-overlay').style.opacity === '1');
  await page.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))));
  const antes = await page.locator('#search-results').innerHTML();
  await page.locator('#search-input').pressSequentially('a');
  await expect.poll(() => page.locator('#search-results').innerHTML(), { timeout: 5000 }).not.toBe(antes);
});
