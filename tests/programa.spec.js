// @ts-check
// programa.spec.js — Tab Programa: lista, grid, filtros, posters, topbar.
const { test, expect } = require('@playwright/test');
const { LEVIZA_SIMTIME, enterFestival } = require('./helpers');

// T01 — Apóstrofe: corazón en lista agrega al watchlist
test('T01 — apóstrofe: corazón en lista agrega al watchlist', async ({ page }) => {
  await enterFestival(page, 'tribeca2026');
  await page.locator('.dtab[data-day="2026-06-06"]').click();
  await page.waitForSelector('.plist-item', { timeout: 8000 });
  const whoopi = page.locator('.plist-item[data-title*="Whoopi"]').first();
  await whoopi.scrollIntoViewIfNeeded();
  await whoopi.locator('.plist-heart').click();
  await page.waitForFunction(() => watchlist.size > 0, { timeout: 5000 });
  const inWL = await page.evaluate(() =>
    watchlist.has("Shorts: Whoopi's Wonderful World of Animation")
  );
  expect(inWL).toBe(true);
  expect(await page.locator('#pel-sheet.open').count()).toBe(0);
});

// T02 — Apóstrofe: tap en título abre sheet
test('T02 — apóstrofe: tap en título abre sheet', async ({ page }) => {
  await enterFestival(page, 'tribeca2026');
  await page.locator('.dtab[data-day="2026-06-06"]').click();
  await page.waitForSelector('.plist-item', { timeout: 8000 });
  const film = page.locator('.plist-item[data-title*="Here I"]').first();
  await film.scrollIntoViewIfNeeded();
  await film.locator('.plist-info').click();
  await page.waitForSelector('#pel-sheet.open', { timeout: 8000 });
  expect(await page.locator('#pel-sheet.open').count()).toBe(1);
});

// T05 — Corazón en lista NO abre sheet
test('T05 — corazón en lista no abre sheet', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.locator('.dtab[data-day="VIE 15"]').click();
  await page.waitForSelector('.plist-item', { timeout: 8000 });
  await page.locator('.plist-item').first().locator('.plist-heart').click();
  await page.waitForTimeout(300); // mínimo necesario: verificar ausencia de sheet
  expect(await page.locator('#pel-sheet.open').count()).toBe(0);
});

// T06 — Scroll se mantiene después de toggle corazón
test('T06 — scroll se mantiene después de toggle corazón', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.locator('.dtab[data-day="VIE 15"]').click();
  await page.waitForSelector('.plist-item', { timeout: 8000 });
  await page.evaluate(() => window.scrollTo(0, 300));
  await page.waitForTimeout(300);
  const scrollBefore = await page.evaluate(() => window.scrollY);
  const items = page.locator('.plist-item');
  const count = await items.count();
  if (count > 2) {
    await items.nth(2).locator('.plist-heart').click();
    await page.waitForTimeout(400);
    const scrollAfter = await page.evaluate(() => window.scrollY);
    expect(Math.abs(scrollAfter - scrollBefore)).toBeLessThan(150);
  }
});

// T10 — Poster editorial sin truncar en carga inicial
test('T10 — poster editorial: sección completa sin truncar', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.waitForSelector('.poster-card, .plist-item', { timeout: 8000 });
  const content = await page.content();
  expect(content).not.toMatch(/>FICC\s*</);
});

// T12 — Día específico carga en vista lista por defecto
test('T12 — día específico carga en vista lista por defecto', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.waitForSelector('.plist-item, .poster-card', { timeout: 8000 });
  const activeDay = await page.evaluate(() => activeDay);
  if (activeDay === 'all') return;
  const listItems = await page.locator('.plist-item').count();
  const gridCards = await page.locator('.poster-card').count();
  expect(listItems).toBeGreaterThan(0);
  expect(gridCards).toBe(0);
});

// T13 — Topbar fecha en una sola línea
test('T13 — topbar fecha en una sola línea', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.waitForSelector('.hdr-fest-dates', { timeout: 5000 });
  const lineCount = await page.evaluate(() => {
    const el = document.querySelector('.hdr-fest-dates');
    if (!el) return -1;
    const style = getComputedStyle(el);
    const lineHeight = parseFloat(style.lineHeight) || parseFloat(style.fontSize) * 1.2;
    return Math.round(el.scrollHeight / lineHeight);
  });
  expect(lineCount).toBe(1);
});

// T20 — TODO muestra vista grid
test('T20 — TODO muestra vista grid', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => { activeDay='all'; programaViewMode='grid'; _renderProgramaContent(); });
  await page.waitForSelector('.poster-card', { timeout: 8000 });
  const cards = await page.locator('.poster-card').count();
  expect(cards).toBeGreaterThan(0);
});

// T21 — Día específico muestra vista lista
test('T21 — día específico muestra vista lista', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  const grid = await page.locator('.poster-card').count();
  const list = await page.locator('.plist-item').count();
  expect(list).toBeGreaterThan(0);
  expect(grid).toBe(0);
});

// T22 — Toggle de vista grid/lista funciona
test('T22 — toggle grid/lista cambia el modo de vista', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => { activeDay='all'; programaViewMode='grid'; _renderProgramaContent(); });
  await page.waitForSelector('.poster-card', { timeout: 5000 });
  await page.evaluate(() => setProgramaView('list'));
  await page.waitForSelector('.plist-item', { timeout: 5000 });
  const afterToggle = await page.evaluate(() => programaViewMode);
  expect(afterToggle).toBe('list');
});

// T23 — Filtro por día muestra solo films de ese día
test('T23 — filtro por día muestra films del día correcto', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => { activeDay='VIE 15'; programaViewMode='list'; _renderProgramaContent(); });
  await page.waitForSelector('.plist-item', { timeout: 5000 });
  const wrongDay = await page.evaluate(() => {
    return Array.from(document.querySelectorAll('.plist-item')).some(el => {
      const meta = el.querySelector('.plist-meta')?.textContent || '';
      return meta.includes('JUE') || meta.includes('SÁB') || meta.includes('DOM');
    });
  });
  expect(wrongDay).toBe(false);
});

// T41 — Sección del poster no truncada en grid
test('T41 — sección del poster no truncada en grid', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => { activeDay='all'; programaViewMode='grid'; _renderProgramaContent(); });
  await page.waitForSelector('.poster-card', { timeout: 8000 });
  const content = await page.content();
  expect(content).not.toMatch(/>FICC\s*</);
  expect(content).not.toMatch(/>COMP\s*</);
});
