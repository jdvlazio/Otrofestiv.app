const { test } = require('@playwright/test');
const { enterFestival } = require('./helpers');
test('tocar poster en Mi Plan', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await enterFestival(page, 'cinemancia2026', '2026-09-04T15:00');
  const r = await page.evaluate(async () => {
    const b = document.createElement('button'); b.setAttribute('data-action','closeCitySheet');
    document.body.appendChild(b); b.click(); b.remove();
    await new Promise(r => setTimeout(r, 400));
    const hoy = FILMS.filter(f => !f._cancelled && f.day === '2026-09-04' && f.time);
    const el = []; const vis = new Set();
    for (const f of hoy) { if (!vis.has(f.title)) { vis.add(f.title); el.push(f); } if (el.length === 3) break; }
    state.set('savedAgenda', { schedule: el.map(f => ({ ...f, _title: f.title })), scenarioIdx: 0 });
    switchMainNav('mnav-miplan'); showAgView();
    await new Promise(r => setTimeout(r, 1200));
    // todos los pósters visibles en Mi Plan y qué llevan encima
    const posters = [...document.querySelectorAll('img.lb-poster, .mplan-row img, .dw-poster')]
      .filter(e => e.getBoundingClientRect().height > 0)
      .slice(0, 6)
      .map(e => {
        const ab = e.closest('.js-open-pel');
        const act = e.closest('[data-action]');
        const r = e.getBoundingClientRect();
        return { cls: e.className.slice(0, 22), enJsOpenPel: !!ab,
          accion: act ? act.getAttribute('data-action') : null,
          fila: !!e.closest('.mplan-row'), bloque: !!e.closest('.mplan-wk-block'),
          centro: [Math.round(r.x + r.width/2), Math.round(r.y + r.height/2)] };
      });
    return { obras: el.length, posters };
  });
  console.log('TAP ' + JSON.stringify(r, null, 1));
});
