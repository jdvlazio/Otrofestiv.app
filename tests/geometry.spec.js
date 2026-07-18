// @ts-check
// geometry.spec.js — GUARDIÁN de geometría entre tabs (decisión Juan, 17 jul 2026):
// "distancias diferentes entre el topbar y lo demás en cada tab" es la clase de
// inconsistencia que este spec entierra. Regla: el PRIMER contenido de cada tab
// arranca a la MISMA distancia del chrome superior (tolerancia ±4px por
// subpíxeles/bordes). Si un tab introduce un espaciador fantasma, esto lo caza
// con número y elemento culpable.
const { test, expect } = require('@playwright/test');
const { enterFestival } = require('./helpers');

// Mide: bottom del chrome superior visible y top del primer elemento de
// contenido visible (>4px de alto) del view activo. Devuelve el gap y quién es.
async function measureGap(page) {
  return page.evaluate(() => {
    const vis = (e) => {
      if (!e) return false;
      const cs = getComputedStyle(e);
      if (cs.display === 'none' || cs.visibility === 'hidden') return false;
      const r = e.getBoundingClientRect();
      return r.height > 4 && r.width > 0;
    };
    // Chrome superior: topbar + barras sticky visibles que cuelgan de él
    const chrome = ['.topbar', '#programa-mode-bar', '#hdr-programa', '#hdr-ag', '.day-tabs']
      .flatMap(s => [...document.querySelectorAll(s)])
      .filter(vis);
    const chromeBottom = Math.max(...chrome.map(e => e.getBoundingClientRect().bottom), 0);
    // Primer contenido visible bajo el chrome (excluye style/script/overlays fijos)
    const roots = ['#ag-view', '#grid', '#programa-list', 'main', 'body'];
    let first = null;
    for (const rs of roots) {
      const root = document.querySelector(rs);
      if (!root || !vis(root)) continue;
      const walk = [...root.querySelectorAll('*')].filter(e => {
        if (!vis(e)) return false;
        const cs = getComputedStyle(e);
        if (cs.position === 'fixed') return false;
        const r = e.getBoundingClientRect();
        return r.top >= chromeBottom - 2 && r.top < chromeBottom + 400;
      });
      if (walk.length) { first = walk.sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top)[0]; break; }
    }
    if (!first) return { gap: null, el: null, chromeBottom };
    return {
      gap: Math.round(first.getBoundingClientRect().top - chromeBottom),
      el: (first.id ? '#' + first.id : '') + '.' + (first.className || '').toString().split(' ').slice(0, 2).join('.'),
      chromeBottom: Math.round(chromeBottom),
    };
  });
}

// FIXME(18 jul): activar tras calibrar la línea base con el dispositivo real de
// Juan (CI midió 56px uniforme en 3 tabs + cartelera 66→corregida a 56; el
// teléfono mostraba otra distribución — sospecha: SW con CSS viejo). Al activar:
// quitar .fixme y este comentario.
test.fixme('G01 — el primer contenido de cada tab arranca a la misma distancia del chrome', async ({ page }) => {
  await enterFestival(page, 'tribeca2026');
  // Estado POBLADO (el de la queja real): watchlist + plan guardado — los tabs
  // vacíos centran un hero y no miden lo mismo que la vida real.
  await page.evaluate(() => {
    const wl = FILMS.filter(f => !f.info && f.time).slice(0, 6);
    watchlist.clear(); wl.forEach(f => watchlist.add(f.title));
    const sched = wl.slice(0, 4).map(f => ({ _title: f.title, title: f.title, day: f.day, time: f.time, venue: f.venue, duration: f.duration, day_order: f.day_order }));
    state.set('savedAgenda', { schedule: sched });
  });
  const tabs = ['mnav-cartelera', 'mnav-seleccion', 'mnav-planner', 'mnav-miplan'];
  const gaps = {};
  for (const tab of tabs) {
    await page.evaluate((t) => { switchMainNav(t); (t === 'mnav-cartelera' ? showDayView : showAgView)(); }, tab);
    await page.waitForTimeout(400);
    gaps[tab] = await measureGap(page);
  }
  console.log('G01 gaps:', JSON.stringify(gaps));
  const values = Object.values(gaps).map(g => g.gap).filter(g => g !== null);
  expect(values.length).toBe(4);
  const min = Math.min(...values), max = Math.max(...values);
  expect(max - min, `gaps desiguales entre tabs: ${JSON.stringify(gaps)}`).toBeLessThanOrEqual(4);
});
