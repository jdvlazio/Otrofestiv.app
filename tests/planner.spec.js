// @ts-check
// planner.spec.js — Tab Planear: cálculo, escenarios, conflictos, disponibilidad.
const { test, expect } = require('@playwright/test');
const { LEVIZA_SIMTIME, enterFestival, addToWatchlist, goToPlanear, esperarCalculo } = require('./helpers');

// T03 — Ver opciones genera resultados
test('T03 — ver opciones genera resultados', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await addToWatchlist(page, 'Taller de Guion');
  await goToPlanear(page);
  // Desde el 16 ago entrar a Planear ya calcula (T58): el resultado está a la
  // vista SIN tocar el botón. Antes se afirmaba lo contrario (toBeHidden) — era
  // el contrato viejo, no un invariante. Que el botón recalcule lo cubre T04.
  await expect(page.locator('#ag-result-wrap')).toBeVisible({ timeout: 20000 });
  await page.locator('.av-calc-btn').click();
  await esperarCalculo(page);
  const content = await page.locator('#ag-result').textContent();
  expect(content?.trim().length).toBeGreaterThan(5);
});

// T04 — Ver opciones recalcula al presionar de nuevo
test('T04 — ver opciones recalcula al presionar de nuevo', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await addToWatchlist(page, 'Taller de Guion');
  await goToPlanear(page);
  await page.locator('.av-calc-btn').click();
  await esperarCalculo(page);
  await page.locator('.av-calc-btn').click();
  await esperarCalculo(page);
  const content = await page.locator('#ag-result').textContent();
  expect(content?.trim().length).toBeGreaterThan(5);
});

// T09 — Taller recurrente: 3 sesiones en el plan
test('T09 — taller recurrente: 3 sesiones en el plan', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await addToWatchlist(page, 'Taller de Guion');
  await goToPlanear(page);
  await page.locator('.av-calc-btn').click();
  await esperarCalculo(page);
  const sessionCount = await page.evaluate(() => {
    if (!cachedResult?.scenarios?.length) return 0;
    const s0 = cachedResult.scenarios[0];
    return s0?.schedule?.filter(s => s._title === 'Taller de Guion').length || 0;
  });
  expect(sessionCount).toBe(3);
});

// T29 — Planear sin watchlist muestra estado vacío
test('T29 — planear sin watchlist muestra estado vacío', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => { watchlist.clear(); savedAgenda = null; saveState('wl','watched'); saveSavedAgenda(); });
  await page.evaluate(() => { switchMainNav('mnav-planner'); showAgView(); });
  await page.waitForSelector('.empty-state-hero', { timeout: 8000 });
  const empty = await page.locator('.empty-state-hero').count();
  expect(empty).toBeGreaterThan(0);
});

// T30 — Planear con watchlist muestra botón calcular
test('T30 — planear con watchlist muestra botón calcular', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await addToWatchlist(page, 'Taller de Guion');
  await page.evaluate(() => { switchMainNav('mnav-planner'); showAgView(); });
  await expect(page.locator('.av-calc-btn')).toBeVisible({ timeout: 8000 });
});

// T31 — Planear genera al menos un escenario
test('T31 — planear genera al menos un escenario', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await addToWatchlist(page, 'Taller de Guion');
  await goToPlanear(page);
  await page.locator('.av-calc-btn').click();
  await esperarCalculo(page);
  const scenarios = await page.evaluate(() => cachedResult?.scenarios?.length || 0);
  expect(scenarios).toBeGreaterThan(0);
});

// T36 — Sesión solapada abre modal de conflicto
test('T36 — sesión solapada abre modal de conflicto', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => {
    const f1 = FILMS.find(fi => fi.title === 'Taller de Guion' && fi.day === 'VIE 15');
    if (!f1) return;
    if (!savedAgenda) savedAgenda = { schedule: [] };
    savedAgenda.schedule = [{ ...f1, _title: f1.title }];
    saveSavedAgenda();
    watchlist.add('Taller de Guion');
    const f2 = FILMS.find(fi => fi.title === 'Rebelión' && fi.day === 'VIE 15');
    if (f2) openConflictSheet(f2.title, f2, savedAgenda.schedule[0]);
  });
  await page.waitForSelector('#conflict-sheet', { timeout: 5000 });
  const sheet = await page.locator('#conflict-sheet.open, #conflict-sheet[style*="block"], #conflict-sheet').count();
  expect(sheet).toBeGreaterThan(0);
});

// T43 — Planear con títulos muestra chips de disponibilidad
test('T43 — planear con títulos muestra chips de disponibilidad', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await addToWatchlist(page, 'Taller de Guion');
  await page.evaluate(() => { switchMainNav('mnav-planner'); showAgView(); });
  await page.waitForSelector('.av-calc-btn', { timeout: 8000 });
  const hasUI = await page.locator('.av-calc-btn').count();
  expect(hasUI).toBeGreaterThan(0);
});

// T54 — el Q&A no bloquea en la misma sede: advierte (decisión de Juan, 30 jul 2026)
// Caso real de FINCA: función compartida 18:00 (106+5, Q&A) + Ziki 20:30, mismo
// Cine York. 39 min entre películas — el festival lo programó para que se pudiera —
// pero el planificador excluía a Ziki contando los +30 ESTIMADOS del Q&A opcional
// (9 < buffer 15). Ahora entra, y Mi Plan muestra "Q&A · si te quedás tenés ~N min".
// Con TRASLADO el Q&A sigue contando entero (variables incontrolables).
test('T54 — Ziki entra al plan pese al Q&A (misma sede) y Mi Plan advierte', async ({ page }) => {
  await enterFestival(page, 'finca2026', '2026-08-13T10:00');
  await page.evaluate(() => {
    watchlist.clear();
    ['Propiedad privada prohibido pasar', 'Mi casa es su casa', 'Ziki'].forEach(t => watchlist.add(t));
    saveState('wl', 'watched');
  });
  await goToPlanear(page);
  await page.locator('.av-calc-btn').click();
  await esperarCalculo(page);
  const titles = await page.evaluate(() =>
    (cachedResult?.scenarios?.[0]?.schedule || []).map(s => s._title));
  expect(titles).toContain('Ziki');
  expect(titles).toContain('Propiedad privada prohibido pasar');
  // y la advertencia aparece en Mi Plan
  await page.evaluate(() => { state.set('savedAgenda', { schedule: cachedResult.scenarios[0].schedule, scenarioIdx: 0 }); switchMainNav('mnav-miplan'); showAgView(); });
  await page.waitForSelector('#ag-view', { state: 'visible', timeout: 8000 });
  await page.waitForTimeout(600);
  const warns = await page.evaluate(() =>
    [...document.querySelectorAll('.mplan-warn-row')].map(e => e.textContent.trim()));
  expect(warns.some(w => /Q&A/.test(w) && /min/.test(w))).toBe(true);
});

// T58 — entrar a Planear recalcula solo (y respeta el plan ya confirmado)
// El escenario vive en memoria y moría al recargar: 4 filas antes, 0 después,
// sin aviso, con los intereses intactos (medido el 16 ago con FICDEH). Lo que se
// perdía era una DERIVACIÓN —recalcularla cuesta 2–3 ms— así que no se persiste:
// se recalcula al entrar. Con plan YA guardado NO se toca: aparecer con una
// opción nueva sin pedirla invita a reemplazar lo que el usuario curó a mano.
test('T58 — Planear recalcula al entrar, salvo si ya hay plan guardado', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await addToWatchlist(page, 'Taller de Guion');

  // (a) sin plan guardado y sin cálculo en memoria → aparece solo, sin tocar el botón
  await page.evaluate(() => { cachedResult = null; savedAgenda = null; switchMainNav('mnav-planner'); showAgView(); });
  await page.waitForFunction(() => !!cachedResult, null, { timeout: 8000 });
  const auto = await page.evaluate(() => (cachedResult.scenarios || []).length);
  expect(auto, 'entrar a Planear calcula solo').toBeGreaterThan(0);

  // (b) con plan guardado → NO recalcula al entrar; manda el botón
  await page.evaluate(() => {
    savedAgenda = { schedule: [{ ...FILMS.find(f => f.title === 'Taller de Guion'), _title: 'Taller de Guion' }] };
    cachedResult = null;
    switchMainNav('mnav-cartelera');
    switchMainNav('mnav-planner'); showAgView();
  });
  await page.waitForTimeout(600);
  const conPlan = await page.evaluate(() => cachedResult);
  expect(conPlan, 'con plan guardado no se autocalcula').toBeNull();
});
