// @ts-check
// literal-template.spec.js — GUARDIÁN de interpolación rota (regresión 18 jul 2026).
//
// EL BUG: al migrar SVG inline a ICONS, tres reemplazos cayeron dentro de strings
// con COMILLA SIMPLE (no template literal) → `${ICONS.chevronD}` se renderizó
// LITERAL bajo la fila de días de Mi Plan. Ni unit ni los specs de feature lo
// cazaron (nadie renderiza ese micro-elemento). validate.py no puede distinguir
// con regex el contexto backtick vs comilla. La protección correcta es de DOM:
// ninguna vista renderizada debe contener la subcadena `${` — si aparece, hay una
// interpolación de template rota. Recorre las vistas con el plan poblado, incluida
// Mi Plan con navegación de día/semana (donde vivía el bug).
const { test, expect } = require('@playwright/test');
const { LEVIZA_SIMTIME, enterFestival } = require('./helpers');

test.use({ viewport: { width: 390, height: 844 } });

test('L01 — ninguna vista renderiza ${…} literal (interpolación rota)', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  // Plan poblado: los micro-elementos (flechas de nav de Mi Plan, badges) solo
  // se renderizan con estado real — el estado vacío no ejercita el camino del bug.
  await page.evaluate(() => {
    const wl = FILMS.filter(f => !f.info && f.time).slice(0, 6);
    watchlist.clear(); wl.forEach(f => watchlist.add(f.title));
    const sched = wl.slice(0, 4).map(f => ({ _title: f.title, title: f.title, day: f.day, time: f.time, venue: f.venue, duration: f.duration, day_order: f.day_order }));
    state.set('savedAgenda', { schedule: sched });
  });

  const views = [
    { tab: 'mnav-cartelera', fn: 'showDayView' },
    { tab: 'mnav-seleccion', fn: 'showAgView' },
    { tab: 'mnav-planner', fn: 'showAgView' },
    { tab: 'mnav-miplan', fn: 'showAgView' },
  ];
  for (const v of views) {
    await page.evaluate(({ tab, fn }) => { switchMainNav(tab); window[fn] && window[fn](); }, v);
    await page.waitForTimeout(400);
    const html = await page.evaluate(() => document.body.innerHTML);
    expect(html, `\${…} literal en ${v.tab} (interpolación rota)`).not.toContain('${');
  }

  // Sub-vista TODO del Programa (otro camino de render)
  await page.evaluate(() => {
    switchMainNav('mnav-cartelera'); showDayView();
    const chip = [...document.querySelectorAll('[data-day]')].find(e => e.dataset.day === 'all');
    if (chip) chip.click();
  });
  await page.waitForTimeout(400);
  const htmlTodo = await page.evaluate(() => document.body.innerHTML);
  expect(htmlTodo, '${…} literal en cartelera TODO').not.toContain('${');
});
