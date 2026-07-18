// @ts-check
// geometry.spec.js — GUARDIÁN de geometría entre tabs (decisión Juan, 17 jul 2026):
// "distancias diferentes entre el topbar y lo demás en cada tab" es la clase de
// inconsistencia que este spec entierra. Regla: el PRIMER contenido de cada tab
// arranca a la MISMA distancia del chrome superior (tolerancia ±4px por
// subpíxeles/bordes). Si un tab introduce un espaciador fantasma, esto lo caza
// con número y elemento culpable.
const { test, expect } = require('@playwright/test');

// MÓVIL explícito: el proyecto chromium hereda devices['Desktop Chrome'] (1280px)
// y ahí la nav vive EN FLUJO bajo el chrome — todo gap medido en desktop es de
// otro layout. La queja y la regla son del teléfono.
test.use({ viewport: { width: 390, height: 844 } });
const { enterFestival, LEVIZA_SIMTIME } = require('./helpers');

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
    // Cadena de contribuciones: padding/margin top de first y sus ancestros
    const chain = [];
    let n = first;
    while (n && n !== document.body) {
      const cs = getComputedStyle(n);
      const mt = parseFloat(cs.marginTop) || 0, pt = parseFloat(cs.paddingTop) || 0;
      if (mt || pt) chain.push(`${n.id ? '#' + n.id : '.' + (n.className||'').toString().split(' ')[0]}:m${mt}/p${pt}`);
      n = n.parentElement;
    }
    return {
      gap: Math.round(first.getBoundingClientRect().top - chromeBottom),
      el: (first.id ? '#' + first.id : '') + '.' + (first.className || '').toString().split(' ').slice(0, 2).join('.'),
      chromeBottom: Math.round(chromeBottom),
      chain,
      between: [...document.querySelectorAll('body *')].filter(e => {
        const r = e.getBoundingClientRect(); const cs = getComputedStyle(e);
        return cs.position !== 'fixed' && r.height > 0 && r.top >= chromeBottom - 2 && r.bottom <= first.getBoundingClientRect().top + 2 && r.height >= 8;
      }).slice(0, 6).map(e => `${e.id ? '#' + e.id : '.' + (e.className||'').toString().split(' ')[0]}:h${Math.round(e.getBoundingClientRect().height)}`),
    };
  });
}

test('G01 — el primer contenido de cada tab arranca a la misma distancia del chrome', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME); // festival EN CURSO → Planear poblado (pending>0)
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
    await page.waitForTimeout(500);
    gaps[tab] = await measureGap(page);
    // anti-flake: un re-intento si el primer render aún no asentó
    if (gaps[tab].gap === null || gaps[tab].gap > 2) { await page.waitForTimeout(500); gaps[tab] = await measureGap(page); }
  }
  console.log('G01 gaps:', JSON.stringify(gaps));
  const values = Object.values(gaps).map(g => g.gap).filter(g => g !== null);
  expect(values.length).toBe(4);
  const min = Math.min(...values), max = Math.max(...values);
  // FLUSH (regla Juan 17 jul): cada tab arranca PEGADO al chrome — sin espacio.
  expect(max, `algún tab no arranca pegado al chrome: ${JSON.stringify(gaps)}`).toBeLessThanOrEqual(2);
  expect(max - min, `gaps desiguales entre tabs: ${JSON.stringify(gaps)}`).toBeLessThanOrEqual(2);
});
