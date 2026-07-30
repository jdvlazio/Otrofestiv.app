// @ts-check
// sheet.spec.js — Sheet de película + Intereses (watchlist).
const { test, expect } = require('@playwright/test');
const { LEVIZA_SIMTIME, enterFestival, addToWatchlist } = require('./helpers');

// T07 — Quitar de Intereses desde sheet cierra el sheet
test('T07 — quitar de Intereses desde sheet cierra el sheet', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await addToWatchlist(page, 'La Suprema');
  await page.evaluate(() => openPelSheet('La Suprema'));
  await page.waitForSelector('#pel-sheet.open', { timeout: 8000 });
  const wlBtn = page.locator('#pel-wl-btn');
  await expect(wlBtn).toContainText(/(intereses|interests)/i);
  await wlBtn.click();
  await expect(page.locator('#pel-sheet.open')).toHaveCount(0, { timeout: 5000 });
});

// T14 — Sheet muestra el título correcto
test('T14 — sheet muestra el título correcto', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => openPelSheet('La Suprema'));
  await page.waitForSelector('#pel-sheet.open', { timeout: 8000 });
  const title = await page.locator('.pel-sheet-title').first().textContent();
  expect(title?.trim().length).toBeGreaterThan(0);
  expect(title).toContain('Suprema');
});

// T15 — Sheet muestra funciones del título
test('T15 — sheet muestra funciones del título', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => openPelSheet('La Suprema'));
  await page.waitForSelector('#pel-sheet.open', { timeout: 8000 });
  const funciones = await page.locator('.pel-sheet-screening, .pel-sheet-screenings').count();
  expect(funciones).toBeGreaterThan(0);
});

// T16 — Sheet tiene botón de intereses
test('T16 — sheet tiene botón de intereses', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => openPelSheet('La Suprema'));
  await page.waitForSelector('#pel-sheet.open', { timeout: 8000 });
  await expect(page.locator('#pel-wl-btn')).toBeVisible();
});

// T17 — Añadir al watchlist desde sheet actualiza el estado
test('T17 — añadir al watchlist desde sheet actualiza el estado', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => { watchlist.clear(); saveState('wl','watched'); });
  await page.evaluate(() => openPelSheet('La Suprema'));
  await page.waitForSelector('#pel-sheet.open', { timeout: 8000 });
  await page.locator('#pel-wl-btn').click();
  await page.waitForFunction(() => watchlist.has('La Suprema'), { timeout: 5000 });
  const inWL = await page.evaluate(() => watchlist.has('La Suprema'));
  expect(inWL).toBe(true);
});

// T18 — Sheet se cierra con el botón X
test('T18 — sheet se cierra con el botón X', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => openPelSheet('La Suprema'));
  await page.waitForSelector('#pel-sheet.open', { timeout: 8000 });
  await page.evaluate(() => closePelSheet());
  await expect(page.locator('#pel-sheet.open')).toHaveCount(0, { timeout: 5000 });
});

// T19 — Watchlist persiste al navegar entre tabs
test('T19 — watchlist persiste al navegar entre tabs', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await addToWatchlist(page, 'La Suprema');
  await page.evaluate(() => { switchMainNav('mnav-seleccion'); showAgView(); });
  await page.waitForSelector('#ag-view', { state: 'visible', timeout: 5000 });
  await page.evaluate(() => switchMainNav('mnav-cartelera'));
  await page.waitForSelector('.poster-card, .plist-item, .dtab', { timeout: 5000 });
  const inWL = await page.evaluate(() => watchlist.has('La Suprema'));
  expect(inWL).toBe(true);
});

// T33 — Intereses muestra películas en watchlist
test('T33 — intereses muestra películas en watchlist', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await addToWatchlist(page, 'La Suprema');
  await addToWatchlist(page, 'Taller de Guion');
  await page.evaluate(() => { switchMainNav('mnav-seleccion'); showAgView(); });
  await page.waitForSelector('#ag-view', { state: 'visible', timeout: 5000 });
  const items = await page.locator('.plist-item, .poster-card, .ag-film-row, .int-item').count();
  expect(items).toBeGreaterThan(0);
});

// ─── YA VISTA + RATING ────────────────────────────────────────────────────────

// V01 — Click en "Seen" abre modal de confirmación (verificado en browser)
// Flujo real: pel-vista-btn → modal pv-rating-sheet "Have you seen this film?"
test('V01 — botón Seen abre modal de confirmación', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => openPelSheet('La Suprema'));
  await page.waitForSelector('#pel-sheet.open', { timeout: 8000 });
  const vistaBtn = page.locator('#pel-vista-btn');
  await expect(vistaBtn).toBeVisible({ timeout: 5000 });
  await vistaBtn.click();
  // showActionModal → crea #conflict-modal en el DOM
  await page.waitForSelector('#conflict-modal', { timeout: 5000 });
  expect(await page.locator('#conflict-modal').count()).toBe(1);
});

// V02 — Rating sheet abre correctamente
// openRatingSheet directo — el botón en sheet usa setTimeout que complica el selector
test('V02 — rating sheet abre correctamente', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => openRatingSheet('La Suprema'));
  await page.waitForSelector('#rating-sheet.open', { timeout: 5000 });
  expect(await page.locator('#rating-sheet.open').count()).toBe(1);
});

// V03 — Rating sheet se cierra quitando clase .open
// closeRatingSheet usa classList.remove('open'), no display:none
test('V03 — rating sheet se cierra con omitir', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => openRatingSheet('La Suprema'));
  await page.waitForSelector('#rating-sheet.open', { timeout: 5000 });
  await page.locator('#rating-action-btn').click();
  await page.waitForSelector('#rating-sheet:not(.open)', { timeout: 5000 });
  expect(await page.locator('#rating-sheet.open').count()).toBe(0);
});

// V04 — Rating sheet muestra estrellas correctamente
// Testea DOM observable: las estrellas están presentes en el rating sheet
test('V04 — rating sheet muestra estrellas', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => openRatingSheet('La Suprema'));
  await page.waitForSelector('#rating-sheet.open', { timeout: 5000 });
  // El rating-film-title debe mostrar el nombre de la película
  const filmTitle = await page.locator('#rating-film-title').textContent();
  expect(filmTitle).toContain('Suprema');
  // El área de estrellas debe estar presente
  await expect(page.locator('.rating-stars')).toBeVisible({ timeout: 3000 });
});

// ─── AÑADIR FUNCIÓN AL PLAN DESDE EL SHEET (Mitad B · pin-funcion) ─────────────

const TRIBECA_SIMTIME = '2026-06-03T09:00:00-05:00';

// Helper: primer título con ≥minN funciones futuras NO recurrentes.
async function _titleWithFutureScreenings(page, minN) {
  return page.evaluate((minN) => {
    const byTitle = {};
    FILMS.forEach(f => { (byTitle[f.title] = byTitle[f.title] || []).push(f); });
    let best = null, bestN = 0;
    for (const [t, scr] of Object.entries(byTitle)) {
      if (scr[0].is_recurring) continue;            // recurrentes: sin botón por fila
      if (scr.length >= minN && scr.length > bestN) { best = t; bestN = scr.length; }
    }
    return best;                                     // el de MÁS funciones (≥minN)
  }, minN);
}

// AF01 — Añadir función desde el sheet crea entrada en el Plan (sin plan previo)
test('AF01 — añadir función desde el sheet crea entrada en el Plan', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => { state.set('savedAgenda', null); });
  const title = await _titleWithFutureScreenings(page, 1);
  expect(title).toBeTruthy();
  await page.evaluate((t) => openPelSheet(t), title);
  await page.waitForSelector('#pel-sheet.open', { timeout: 8000 });
  await page.waitForSelector('.pel-sheet-screening .suggestion-add', { state: 'visible', timeout: 5000 });
  await page.locator('.pel-sheet-screening .suggestion-add').first().click();
  await page.waitForFunction(() => savedAgenda && savedAgenda.schedule.length === 1, { timeout: 5000 });
  const len = await page.evaluate(() => savedAgenda.schedule.length);
  expect(len).toBe(1);
});

// AF02 — La función añadida muestra el indicador "En tu Plan"
test('AF02 — la función añadida muestra "En tu Plan"', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => { state.set('savedAgenda', null); });
  const title = await _titleWithFutureScreenings(page, 1);
  expect(title).toBeTruthy();
  await page.evaluate((t) => openPelSheet(t), title);
  await page.waitForSelector('#pel-sheet.open', { timeout: 8000 });
  await page.locator('.pel-sheet-screening .suggestion-add').first().click();
  // Tras añadir, la fila planeada muestra el check "en tu plan" (izquierda del día).
  await expect(page.locator('.pel-sheet-screening.in-plan')).toHaveCount(1, { timeout: 5000 });
});

// AF03 — Añadir otra función del mismo título hace swap (no duplica)
test('AF03 — añadir otra función del mismo título hace swap', async ({ page }) => {
  await enterFestival(page, 'tribeca2026', TRIBECA_SIMTIME);
  await page.evaluate(() => { state.set('savedAgenda', null); });
  const title = await _titleWithFutureScreenings(page, 2);
  if (!title) { console.log('AF03: sin título multi-función no-recurrente, skip'); return; }
  await page.evaluate((t) => openPelSheet(t), title);
  await page.waitForSelector('#pel-sheet.open', { timeout: 8000 });
  const nBtns = await page.locator('.pel-sheet-screening .suggestion-add').count();
  if (nBtns < 2) { console.log('AF03: <2 funciones futuras con botón, skip'); return; }
  await page.locator('.pel-sheet-screening .suggestion-add').first().click();
  // El sheet se re-renderiza: la función añadida pasa a "en tu plan" (check izq).
  await page.waitForSelector('.pel-sheet-screening.in-plan', { timeout: 5000 });
  // Queda ≥1 .suggestion-add (otra función) → clic = swap, no duplicado.
  await page.locator('.pel-sheet-screening .suggestion-add').first().click();
  await page.waitForTimeout(400);
  const len = await page.evaluate(() => savedAgenda.schedule.length);
  expect(len).toBe(1);
});

// ─── Función heredada en la ficha de corto (bug jul 2026) ──────────────────────
// Un corto no es entrada de FILMS: su dia/hora/sede viven en el programa que lo
// proyecta. La ficha de corto los ignoraba y quedaba MUDA — se veia el corto pero
// nunca cuando ni donde. Estos tests exigen la fila; sin ellos el bug vuelve.

const FINCA_SIMTIME = '2026-08-14T15:00';

// AF04 — la ficha de un corto muestra la función de su programa
test('AF04 — la ficha de un corto muestra la función heredada', async ({ page }) => {
  await enterFestival(page, 'finca2026', FINCA_SIMTIME);
  await page.evaluate(() => openCortoSheet('Cuidemos el planeta', '', '', ''));
  await page.waitForSelector('#pel-sheet.open', { timeout: 8000 });
  const row = page.locator('#pel-sheet-inner .pel-sheet-screening').first();
  await expect(row).toBeVisible({ timeout: 5000 });
  // Los tres datos, no solo la fila: dia, hora y sede.
  await expect(row.locator('.pelicula-day')).not.toBeEmpty();
  await expect(row.locator('.pelicula-time')).toContainText(/\d{1,2}:\d{2}/);
  await expect(row.locator('.pelicula-venue')).not.toBeEmpty();
});

// AF05 — un corto en DOS programas muestra sus DOS funciones, y "Añadir" apunta
// al programa (no al corto): addSuggestion solo entiende titulos de FILMS.
test('AF05 — corto en dos programas muestra ambas funciones y añade el programa', async ({ page }) => {
  // simTime al ARRANQUE del festival: las dos funciones de Ecocidio (13 y 15 AGO)
  // quedan en futuro, asi que ambas filas llevan boton. Con el reloj en el 14 la del
  // 13 ya paso y no lleva control — correcto, pero no es lo que este test mide.
  await enterFestival(page, 'finca2026', '2026-08-12T10:00');
  await page.evaluate(() => { state.set('savedAgenda', null); });
  await page.evaluate(() => openCortoSheet('Ecocidio', '', '', ''));
  await page.waitForSelector('#pel-sheet.open', { timeout: 8000 });
  await expect(page.locator('#pel-sheet-inner .pel-sheet-screening')).toHaveCount(2, { timeout: 5000 });
  const owners = await page.evaluate(() =>
    [...document.querySelectorAll('#pel-sheet-inner .suggestion-add')].map(b => ({
      title: b.dataset.title, day: b.dataset.day, time: b.dataset.time })));
  expect(owners.length).toBe(2);
  // Cada owner existe en FILMS con ESA funcion → addSuggestion puede resolverlo.
  const resolvable = await page.evaluate((os) =>
    os.every(o => FILMS.some(f => f.title === o.title && f.day === o.day && f.time === o.time)), owners);
  expect(resolvable).toBe(true);
  // Y ninguno es el titulo del corto.
  expect(owners.some(o => o.title === 'Ecocidio')).toBe(false);
});

// AF06 — sin función anunciada, vacío EXPLÍCITO (no silencio)
test('AF06 — corto sin función anunciada muestra vacío explícito', async ({ page }) => {
  await enterFestival(page, 'finca2026', FINCA_SIMTIME);
  await page.evaluate(() => openCortoSheet('Corto Inexistente QA', '', '', ''));
  await page.waitForSelector('#pel-sheet.open', { timeout: 8000 });
  await expect(page.locator('#pel-sheet-inner .pel-sheet-screening')).toHaveCount(0);
  await expect(page.locator('#pel-sheet-inner')).toContainText(/sin función anunciada|no screening announced/i, { timeout: 5000 });
});

// ─── Banda AVISOS (30 jul 2026) ────────────────────────────────────────────────
// Los avisos que MATIZAN la función (Q&A, programa, inscripción) viven en su
// propia banda, no dentro del bloque de FUNCIÓN. AF09 exige que existan; AF10 es
// el invariante de alineación: todos los textos comparten columna (grid), que es
// lo que se rompe si alguien vuelve a anchos fijos.

// AF09 — la ficha de un corto muestra el aviso PROGRAMA en la banda AVISOS
test('AF09 — banda AVISOS con el aviso de programa en la ficha de corto', async ({ page }) => {
  await enterFestival(page, 'finca2026', FINCA_SIMTIME);
  await page.evaluate(() => openCortoSheet('Ecocidio', '', '', ''));
  await page.waitForSelector('#pel-sheet.open', { timeout: 8000 });
  await expect(page.locator('#pel-sheet-inner .avisos-body')).toHaveCount(1, { timeout: 5000 });
  await expect(page.locator('#pel-sheet-inner .aviso-pill').first()).toHaveText(/programa|programme/i);
  // y NO quedan avisos con rótulo fuera de la banda
  await expect(page.locator('#pel-sheet-inner .meta-banner-label')).toHaveCount(0);
});

// AF10 — invariante de alineación: pastillas al riel del día, textos en una columna
test('AF10 — los avisos comparten columna y arrancan en el riel del día', async ({ page }) => {
  await enterFestival(page, 'finca2026', FINCA_SIMTIME);
  const withQa = await page.evaluate(() => (FILMS.find(f => f.has_qa) || {}).title);
  if (!withQa) { console.log('AF10: festival sin Q&A, skip'); return; }
  await page.evaluate((t) => openPelSheet(t), withQa);
  await page.waitForSelector('#pel-sheet-inner .avisos-body', { timeout: 8000 });
  const m = await page.evaluate(() => {
    const L = e => Math.round(e.getBoundingClientRect().left);
    return {
      pills: [...document.querySelectorAll('.aviso-pill')].map(L),
      txts: [...document.querySelectorAll('.aviso-txt')].map(L),
      dia: L(document.querySelector('.pelicula-day')),
    };
  });
  expect(m.pills.length).toBeGreaterThan(0);
  // pastillas en el mismo riel que el día de la fila de función
  m.pills.forEach(x => expect(x).toBe(m.dia));
  // todos los textos en la MISMA columna (lo garantiza el grid, no un px fijo)
  expect(new Set(m.txts).size).toBe(1);
});

// AF11 — el diálogo de confirmación tiene UN solo riel izquierdo
// Tenía tres (36, 52 y 60) y el rótulo, sin padding, quedaba cortado por la
// esquina redondeada de la caja. El padding vive ahora en la caja: todo alinea.
test('AF11 — el diálogo de confirmación alinea todo a un solo riel', async ({ page }) => {
  await enterFestival(page, 'finca2026', FINCA_SIMTIME);
  const title = await page.evaluate(() => (FILMS.find(f => !f.is_cortos && !f.info) || {}).title);
  await page.evaluate((t) => openPelSheet(t), title);
  await page.waitForSelector('#pel-vista-btn', { timeout: 8000 });
  await page.locator('#pel-vista-btn').click();
  await page.waitForSelector('#conflict-modal .conflict-modal-box', { timeout: 5000 });
  const m = await page.evaluate(() => {
    const L = s => Math.round(document.querySelector(s).getBoundingClientRect().left);
    const box = document.querySelector('.conflict-modal-box').getBoundingClientRect();
    return {
      lefts: ['.conflict-modal-hdr', '.conflict-modal-body', '.conflict-modal-btn.confirm', '.conflict-modal-btn.cancel'].map(L),
      hdrDentro: Math.round(document.querySelector('.conflict-modal-hdr').getBoundingClientRect().top - box.top),
    };
  });
  // un solo borde izquierdo para rótulo, cuerpo y los dos botones
  expect(new Set(m.lefts).size).toBe(1);
  // y el rótulo no toca el borde de la caja (antes: 1px → lo cortaba el radio)
  expect(m.hdrDentro).toBeGreaterThanOrEqual(12);
});
