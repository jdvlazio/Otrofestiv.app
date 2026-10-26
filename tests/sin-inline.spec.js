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

// ── Paso 2/4: los on*= de las strings HTML de src/ ───────────────────────────
async function _img(page, attrs, suelta) {
  return page.evaluate(({ attrs, suelta }) => new Promise(res => {
    const box = document.createElement('div');
    box.innerHTML = `<img id="si-img" ${attrs}>`;
    const im = box.firstChild;
    // suelta: la imagen termina (falla/carga) ANTES de entrar al documento
    if (suelta) { const fin = () => { document.body.appendChild(box); res(); };
      im.addEventListener('error', fin); im.addEventListener('load', fin); }
    else { document.body.appendChild(box); res(); }
  }), { attrs, suelta });
}
const ROTA = () => `src="/assets/no-existe-${Date.now()}.jpg"`;
const SANA = 'src="/icon-192.png"';

for (const suelta of [false, true]) {
  const tag = suelta ? ' (falla antes de entrar al documento)' : '';
  test(`SI05 — data-err="quitar" saca la imagen rota${tag}`, async ({ page }) => {
    await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
    await _img(page, `data-err="quitar" ${ROTA()}`, suelta);
    await expect(page.locator('#si-img')).toHaveCount(0, { timeout: 5000 });
  });
  test(`SI06 — data-load="mostrar" la muestra al cargar${tag}`, async ({ page }) => {
    await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
    await _img(page, `data-load="mostrar" style="opacity:0" ${SANA}`, suelta);
    await expect.poll(() => page.evaluate(() => document.getElementById('si-img').style.opacity), { timeout: 5000 }).toBe('1');
  });
}

test('SI07 — data-err="poster": el afiche roto cae al generativo UNA vez', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  const titulo = await page.evaluate(() => FILMS.find(f => f.title).title);
  await _img(page, `data-err="poster" data-title="${titulo.replace(/"/g, '&quot;')}" ${ROTA()}`, false);
  await expect.poll(() => page.evaluate(() => document.getElementById('si-img').getAttribute('src')), { timeout: 5000 }).toMatch(/^data:/);
  expect(await page.evaluate(() => document.getElementById('si-img').dataset.err)).toBeUndefined();
});
