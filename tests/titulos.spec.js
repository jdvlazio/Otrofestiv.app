// @ts-check
// titulos.spec.js — títulos anteriores de una obra renombrada.
// Spec propio porque necesita interceptar el JSON del festival, y el service
// worker lo serviría por fuera de page.route: aquí se bloquea.
const { test, expect } = require('@playwright/test');
const { reentrar } = require('./helpers');

test.use({ serviceWorkers: 'block' });

// T-REN — lo guardado bajo el título viejo de una obra renombrada sobrevive
// (7 oct 2026, Juan: «sin avisar, es lo justo»). Caso real: Villa del Cine
// renombró «Tránsito» → «Tránsitos» (PR #1021). Antes, publicarCatalogo filtraba
// el Interés contra los títulos vigentes y lo BORRABA. Se simula el dato que
// Onboarding pondrá en el JSON (`titulos_anteriores`) interceptando la respuesta.
test('T-REN — Interés, prioridad y calificación pasan del título viejo al nuevo', async ({ page }) => {
  await page.route('**/festivals/villadelcine-2026.json*', async route => {
    const res = await route.fetch();
    const d = await res.json();
    d.films.forEach(f => { if (f.title === 'Tránsitos') f.titulos_anteriores = ['Tránsito']; });
    await route.fulfill({ response: res, json: d });
  });
  await page.goto('/?simTime=' + encodeURIComponent('2026-10-14T10:00:00-05:00'));
  await page.evaluate(() => {
    const k = 'villadelcine2026_';
    localStorage.setItem(k + 'wl', JSON.stringify(['Tránsito', 'Amor a primera vista']));
    localStorage.setItem(k + 'prio', JSON.stringify(['Tránsito']));
    localStorage.setItem(k + 'ratings', JSON.stringify({ 'Tránsito': 4 }));
  });
  await page.reload();
  await reentrar(page, 'villadelcine2026', '2026-10-14T10:00:00-05:00');
  const r = await page.evaluate(() => ({
    wl: [...watchlist].sort(), prio: [...prioritized], rating: filmRatings['Tránsitos'],
    guardado: JSON.parse(localStorage.getItem('villadelcine2026_wl') || '[]').sort(),
  }));
  expect(r.wl, 'el Interés pasó al título nuevo y el resto quedó igual').toEqual(['Amor a primera vista', 'Tránsitos']);
  expect(r.prio, 'la prioridad también').toEqual(['Tránsitos']);
  expect(r.rating, 'y la calificación').toBe(4);
  expect(r.guardado, 'y quedó guardado en el teléfono').toEqual(['Amor a primera vista', 'Tránsitos']);
});
