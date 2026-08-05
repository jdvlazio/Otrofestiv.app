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
  const items = page.locator('.plist-item');
  const count = await items.count();
  if (count > 2) {
    // Centrar el item objetivo en el viewport — lo deja despejado del header
    // sticky para que el click de Playwright no dispare auto-scroll de actionability.
    await page.evaluate(() => document.querySelectorAll('.plist-item')[2].scrollIntoView({ block: 'center' }));
    await page.waitForTimeout(300);
    const scrollBefore = await page.evaluate(() => window.scrollY);
    await items.nth(2).locator('.plist-heart').click();
    await page.waitForTimeout(400);
    const scrollAfter = await page.evaluate(() => window.scrollY);
    expect(Math.abs(scrollAfter - scrollBefore)).toBeLessThan(50); // scroll preservado tras toggle
  }
});

// T45 — Scroll-preservation: re-render por estado preserva scroll; cambio de día resetea
test('T45 — scroll: toggle preserva posición, cambio de día resetea al tope', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.locator('.dtab[data-day="VIE 15"]').click();
  await page.waitForSelector('.plist-item', { timeout: 8000 });

  // (A) Toggle de watchlist (re-render por estado) NO debe mover el scroll
  await page.evaluate(() => window.scrollTo(0, 250));
  await page.waitForTimeout(200);
  const before = await page.evaluate(() => window.scrollY);
  await page.locator('.plist-item').nth(2).locator('.plist-heart').click();
  await page.waitForFunction(() => watchlist.size > 0, { timeout: 5000 });
  await page.waitForTimeout(300);
  const afterToggle = await page.evaluate(() => window.scrollY);
  expect(Math.abs(afterToggle - before)).toBeLessThan(20); // scroll preservado

  // (B) Cambiar de día (navegación) SÍ resetea al tope
  const otherDay = await page.evaluate(() =>
    [...document.querySelectorAll('.dtab[data-day]')]
      .map(t => t.dataset.day)
      .find(d => d !== 'all' && d !== 'VIE 15') || null
  );
  expect(otherDay).toBeTruthy();
  await page.locator(`.dtab[data-day="${otherDay}"]`).click();
  await page.waitForTimeout(400);
  const afterDayChange = await page.evaluate(() => window.scrollY);
  expect(afterDayChange).toBe(0); // scroll reseteado en cambio de día
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
  test.setTimeout(40000);
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  const activeDay = await page.evaluate(() => activeDay);
  if (activeDay === 'all') return;
  // Esperar a que .plist-item sea visible y .poster-card desaparezca del DOM visible
  await page.waitForSelector('.plist-item', { timeout: 8000 });
  await page.waitForFunction(() => {
    const cards = document.querySelectorAll('.poster-card');
    return Array.from(cards).every(c => getComputedStyle(c).display === 'none' || !c.offsetParent);
  }, { timeout: 8000 }).catch(() => {});
  const listItems = await page.locator('.plist-item:visible').count();
  const gridCards = await page.locator('.poster-card:visible').count();
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
  test.setTimeout(40000);
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.waitForSelector('.plist-item', { timeout: 8000 });
  await page.waitForFunction(() => {
    const cards = document.querySelectorAll('.poster-card');
    return Array.from(cards).every(c => getComputedStyle(c).display === 'none' || !c.offsetParent);
  }, { timeout: 8000 }).catch(() => {});
  const grid = await page.locator('.poster-card:visible').count();
  const list = await page.locator('.plist-item:visible').count();
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

// ── T46/T47 — filtro de lugar con NIVEL DE CIUDAD (5 ago 2026) ────────────────
// FICDEH 2026: 11 ciudades, 131 sedes, 416 funciones — la lista plana eran 12,5
// pantallas de scroll y el usuario de Tunja tenía que recorrer las de Bogotá.
// Anatomía aprobada por Juan: nivel 1 = ciudades (caben sin scroll), nivel 2 =
// "‹ Ciudades" + la ciudad (filtra entera) + sus sedes. SOLO en multiciudad:
// con una sola ciudad el filtro queda EXACTO como siempre (T47 lo congela).
test('T46 — multiciudad: el filtro abre por ciudad y se puede filtrar la ciudad entera', async ({ page }) => {
  await enterFestival(page, 'cinemancia2025');
  await page.evaluate(() => switchMainNav('mnav-cartelera'));
  await page.waitForTimeout(300);
  await page.evaluate(() => document.getElementById('lugar-btn').click());
  await page.waitForSelector('#lugar-drop', { timeout: 5000 });

  const n1 = await page.evaluate(() => [...document.querySelectorAll('#lugar-drop .lugar-opt')].map(o => o.dataset.v));
  expect(n1[0]).toBe('all');
  expect(n1.filter(v => v.startsWith('drill:')).length).toBeGreaterThanOrEqual(2); // ciudades, no sedes
  expect(n1.some(v => v === 'Colombo Americano')).toBe(false);                     // las sedes NO están en el nivel 1

  // entrar a una ciudad → "‹ Ciudades" + la ciudad + sus sedes
  await page.evaluate(() => document.querySelector('#lugar-drop [data-v="drill:Medellín"]').click());
  await page.waitForTimeout(200);
  const n2 = await page.evaluate(() => [...document.querySelectorAll('#lugar-drop .lugar-opt')].map(o => o.dataset.v));
  expect(n2[0]).toBe('back');
  expect(n2[1]).toBe('city:Medellín');
  expect(n2.length).toBeGreaterThan(2);
  // el drill NO cierra el dropdown (regresión: el repintado dejaba huérfano el
  // e.target y lugarOutside lo cerraba — por eso stopPropagation)
  expect(await page.evaluate(() => !!document.getElementById('lugar-drop'))).toBe(true);

  // volver
  await page.evaluate(() => document.querySelector('#lugar-drop [data-v="back"]').click());
  await page.waitForTimeout(200);
  expect(await page.evaluate(() => document.querySelector('#lugar-drop .lugar-opt').dataset.v)).toBe('all');

  // filtrar la ciudad entera
  await page.evaluate(() => document.querySelector('#lugar-drop [data-v="drill:Medellín"]').click());
  await page.waitForTimeout(200);
  await page.evaluate(() => document.querySelector('#lugar-drop [data-v="city:Medellín"]').click());
  await page.waitForTimeout(700);
  const tras = await page.evaluate(() => ({
    sel: activeVenue,
    pill: document.querySelector('.paf-pill')?.innerText.replace(/\s+/g, ' ').trim(),
    items: document.querySelectorAll('.poster-card, .plist-item').length,
  }));
  expect(tras.sel).toBe('city:Medellín');
  expect(tras.pill).toContain('Medellín');
  expect(tras.pill).not.toContain('city:');   // el centinela no se filtra a la UI
  expect(tras.items).toBeGreaterThan(0);
});

test('T47 — festival de una ciudad: el filtro sigue plano, sin nivel de ciudad', async ({ page }) => {
  await enterFestival(page, 'finca2026', '2026-08-13T10:00');
  await page.evaluate(() => switchMainNav('mnav-cartelera'));
  await page.waitForTimeout(300);
  await page.evaluate(() => document.getElementById('lugar-btn').click());
  await page.waitForSelector('#lugar-drop', { timeout: 5000 });
  const v = await page.evaluate(() => [...document.querySelectorAll('#lugar-drop .lugar-opt')].map(o => o.dataset.v));
  expect(v[0]).toBe('all');
  expect(v.some(x => x.startsWith('drill:'))).toBe(false);
  expect(v.some(x => x.startsWith('city:'))).toBe(false);
  expect(v.length).toBeGreaterThan(1);        // y sigue listando sus sedes
});

// ── T48 — los paneles de filtro nunca se salen del viewport ───────────────────
// Bug real (FICDEH, 6 ago 2026): el panel se anclaba al borde derecho de su
// botón sin tope. Con el botón "Sección" terminando en x=274 de 375 y el panel
// en su ancho máximo (300px), el borde izquierdo caía en -26px: se leía "odo el
// programa" sin la T y los emojis de sección salían partidos. No lo introdujo
// FICDEH — le pasa a cualquier festival cuyo panel llegue a 300px.
test('T48 — los paneles de Sección y Lugar caben en pantalla (375px, el peor caso)', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 844 });
  await enterFestival(page, 'tribeca2026');
  await page.evaluate(() => switchMainNav('mnav-cartelera'));
  await page.waitForTimeout(300);
  for (const [btn, drop] of [['seccion-btn', 'seccion-drop'], ['lugar-btn', 'lugar-drop']]) {
    await page.evaluate(id => document.getElementById(id).click(), btn);
    await page.waitForSelector(`#${drop}`, { timeout: 5000 });
    const box = await page.evaluate(id => {
      const r = document.getElementById(id).getBoundingClientRect();
      return { left: Math.round(r.left), right: Math.round(r.right), w: Math.round(r.width) };
    }, drop);
    expect(box.left, `${drop} se sale por la izquierda`).toBeGreaterThanOrEqual(0);
    expect(box.right, `${drop} se sale por la derecha`).toBeLessThanOrEqual(375);
    await page.evaluate(id => document.getElementById(id)?.remove(), drop);
  }
});
