const { test } = require('@playwright/test');
const { enterFestival } = require('./helpers');
test('tocar de verdad', async ({ page }) => {
  const errs = []; page.on('pageerror', e => errs.push(e.message.slice(0, 90)));
  await page.setViewportSize({ width: 390, height: 844 });
  await enterFestival(page, 'cinemancia2026', '2026-09-04T15:00');
  await page.evaluate(async () => {
    const b = document.createElement('button'); b.setAttribute('data-action','closeCitySheet');
    document.body.appendChild(b); b.click(); b.remove();
    await new Promise(r => setTimeout(r, 400));
    const hoy = FILMS.filter(f => !f._cancelled && f.day === '2026-09-04' && f.time);
    const el = []; const vis = new Set();
    for (const f of hoy) { if (!vis.has(f.title)) { vis.add(f.title); el.push(f); } if (el.length === 3) break; }
    state.set('savedAgenda', { schedule: el.map(f => ({ ...f, _title: f.title })), scenarioIdx: 0 });
    switchMainNav('mnav-miplan'); showAgView();
    await new Promise(r => setTimeout(r, 1200));
  });
  const antes = await page.evaluate(() => {
    const p = document.querySelector('.mplan-row .js-open-pel');
    return { hay: !!p, titulo: p ? p.dataset.title : null, sheet: !!document.querySelector('#pel-sheet.open') };
  });
  // tocar el póster de la primera fila, como el usuario
  const loc = page.locator('.mplan-row .js-open-pel').first();
  await loc.scrollIntoViewIfNeeded();
  await loc.click({ timeout: 5000 }).catch(e => errs.push('CLICK ' + e.message.slice(0, 60)));
  await page.waitForTimeout(1500);
  const despues = await page.evaluate(() => ({
    sheetAbierta: !!document.querySelector('#pel-sheet.open'),
    tituloSheet: document.querySelector('#pel-sheet .pel-sheet-title')?.textContent?.trim().slice(0, 30) || null,
    filaActiva: !!document.querySelector('.mplan-row.active') }));
  console.log('TAP2 ' + JSON.stringify({ antes, despues, errs: errs.slice(0, 3) }));
});
