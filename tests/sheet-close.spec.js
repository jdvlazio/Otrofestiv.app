// @ts-check
// sheet-close.spec.js — GUARDIÁN: el título de la ficha nunca se pisa con la X de
// cerrar (auditoría Juan 18 jul 2026). La X (44px, esquina sup-der) es absolute y
// su caja baja hacia la 1ª línea del título; un espaciador flotante en
// .pel-sheet-title le hace sitio para que el texto envuelva alrededor. Se mide el
// TEXTO real (Range), no la caja del elemento (flex:1 siempre "solapa"). Con un
// título deliberadamente largo, la 1ª línea del texto no debe invadir la X.
const { test, expect } = require('@playwright/test');
const { LEVIZA_SIMTIME, enterFestival } = require('./helpers');

test.use({ viewport: { width: 390, height: 844 } });

test('X01 — título largo no se pisa con la X de cerrar', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  // abrir cualquier ficha de película
  await page.evaluate(() => {
    switchMainNav('mnav-cartelera'); showDayView();
    const chip = [...document.querySelectorAll('[data-day]')].find(e => e.dataset.day === 'all');
    if (chip) chip.click();
  });
  await page.waitForTimeout(400);
  await page.evaluate(() => {
    const card = [...document.querySelectorAll('.poster-card')].find(c => c.dataset.title);
    card && card.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  });
  await page.waitForTimeout(700);

  const overlap = await page.evaluate(() => {
    const t = document.querySelector('.pel-sheet-title');
    const x = document.querySelector('.pel-sheet-close');
    if (!t || !x) return null;
    // título largo deliberado
    t.childNodes[0].textContent = 'Título Larguísimo De Prueba Copa Mundial Selección Historia Deporte Memoria';
    const xr = x.getBoundingClientRect();
    const rng = document.createRange(); rng.selectNodeContents(t);
    const rects = [...rng.getClientRects()].sort((a, b) => a.top - b.top);
    const first = rects[0];
    // solape REAL del texto de la 1ª línea con la caja de la X
    const ox = Math.max(0, Math.min(xr.right, first.right) - Math.max(xr.left, first.left));
    const oy = Math.max(0, Math.min(xr.bottom, first.bottom) - Math.max(xr.top, first.top));
    return Math.round(ox * oy);
  });
  expect(overlap, 'el texto del título se pisa con la X de cerrar').not.toBeNull();
  expect(overlap, 'el texto del título se pisa con la X de cerrar').toBe(0);
});
