// @ts-check
// sheet.spec.js — Sheet de película + Intereses (watchlist).
const { test, expect } = require('@playwright/test');
const { LEVIZA_SIMTIME, enterFestival, addToWatchlist, reentrar } = require('./helpers');

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
  if (!title) { test.skip(true, 'AF03: sin título multi-función no-recurrente, skip'); return; }
  await page.evaluate((t) => openPelSheet(t), title);
  await page.waitForSelector('#pel-sheet.open', { timeout: 8000 });
  const nBtns = await page.locator('.pel-sheet-screening .suggestion-add').count();
  if (nBtns < 2) { test.skip(true, 'AF03: <2 funciones futuras con botón, skip'); return; }
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
  if (!withQa) { test.skip(true, 'AF10: festival sin Q&A, skip'); return; }
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

// AF12 — la ficha de un corto HEREDA el Q&A de su programa
// Antes no: la banda leía Q&A/inscripción/gratis del film, y la ficha de un corto
// no tiene film propio — solo las funciones que hereda. Son propiedades de la
// FUNCIÓN, así que ahora se derivan de ahí y sirven a las dos fichas.
test('AF12 — el corto hereda el Q&A de su programa, y nombra cuál función', async ({ page }) => {
  await enterFestival(page, 'finca2026', '2026-08-12T10:00');
  const r = await page.evaluate(() => {
    // Ecocidio está en DOS programas; le damos Q&A solo a uno
    FILMS.filter(f => f.title.startsWith('FINQUITA')).forEach(f => { f.has_qa = true; f.qa_type = 'guests'; });
    openCortoSheet('Ecocidio', '', '', '');
    return {
      pills: [...document.querySelectorAll('.aviso-pill')].map(e => e.textContent),
      qaTxt: [...document.querySelectorAll('.aviso-txt')][0].textContent,
    };
  });
  expect(r.pills[0]).toMatch(/Q&A/);
  // aplica a UNA de las dos funciones → el aviso dice a cuál (si no, mentiría)
  expect(r.qaTxt).toMatch(/\d{1,2}:\d{2}/);
});

// AF13 — GRATIS aparece en la banda AVISOS (festival mixto)
// Ya era badge en las cards del listado; faltaba en la ficha, que es donde se decide.
test('AF13 — la ficha muestra GRATIS en un festival de ticketing mixto', async ({ page }) => {
  await enterFestival(page, 'tercertiempo2026');
  const title = await page.evaluate(() => (FILMS.find(f => f.is_free === true && !f.info) || {}).title);
  if (!title) { test.skip(true, 'AF13: sin función gratuita, skip'); return; }
  await page.evaluate((t) => openPelSheet(t), title);
  await page.waitForSelector('#pel-sheet-inner .avisos-body', { timeout: 8000 });
  const pills = await page.evaluate(() => [...document.querySelectorAll('.aviso-pill')].map(e => e.textContent));
  expect(pills.some(p => /gratis|free/i.test(p))).toBe(true);
});

// AF14 — la banda AVISOS respira igual arriba y abajo, al ritmo de FUNCIÓN
// Nació con 2px arriba y 12px abajo: el bloque quedaba pegado al encabezado y
// con el aire caído. La referencia es la fila de función (padding 8px 0) — misma
// respiración vertical en las dos superficies de la ficha. (Juan, 31 jul 2026)
test('AF14 — la banda AVISOS usa el ritmo vertical de la fila de función', async ({ page }) => {
  await enterFestival(page, 'finca2026', FINCA_SIMTIME);
  await page.evaluate(() => openCortoSheet('Ecocidio', '', '', ''));
  await page.waitForSelector('#pel-sheet-inner .avisos-body', { timeout: 8000 });
  const m = await page.evaluate(() => {
    const cs = s => getComputedStyle(document.querySelector(s));
    const a = cs('.avisos-body'), f = cs('#pel-sheet-inner .pel-sheet-screening');
    return { arriba: a.paddingTop, abajo: a.paddingBottom, fila: f.paddingTop };
  });
  expect(m.arriba).toBe(m.abajo);   // mismo aire arriba y abajo
  expect(m.arriba).toBe(m.fila);    // y el mismo que la fila de función
});

// ── T115 — la FICHA pregunta al mismo dueño que la grilla y la lista ──────────
// Era el CUARTO sitio con el gate viejo en `is_programa`: un compuesto de cortos
// —207 de los 215 del catálogo— caía al generativo, que trae banda de sección y
// duración justo al lado del encabezado, que ya las dice. Juan: «se lee doble».
// La Escalera entra MUDA (dato vacío): la regla anti-repetición de la ficha ya
// existía para el generativo y vale igual acá.
test('T115 — un compuesto de cortos muestra la Escalera en su ficha, no el generativo', async ({ page }) => {
  await enterFestival(page, 'cinemancia2026', '2026-09-04T10:00');
  const r = await page.evaluate(() => {
    const f = FILMS.find(x => /^Oublie pas le gruau/.test(x.title));
    if (!f) return { falta: true };
    openPelSheet(f.title);
    const svg = document.querySelector('.psp-escalera svg');
    return {
      esCortos: !!f.is_cortos, tienePosterPropio: !!f.poster,
      escalera: !!svg,
      generativo: !!document.querySelector('.pel-sheet-poster'),
      stackViejo: !!document.querySelector('.pel-sheet-poster-stage'),
      obrasListadas: document.querySelectorAll('.pel-sheet-corto-item').length,
      // MUDA: sin la línea de dato, que repetiría la duración del encabezado
      textoEnElPoster: svg ? [...svg.querySelectorAll('text')].map(t => t.textContent.trim()).filter(Boolean) : null
    };
  });
  expect(r.falta).toBeFalsy();
  expect(r.esCortos).toBe(true);
  expect(r.tienePosterPropio).toBe(false);   // si lo tuviera, mandaría el oficial
  expect(r.escalera).toBe(true);
  expect(r.generativo).toBe(false);
  expect(r.stackViejo).toBe(false);
  expect(r.obrasListadas).toBe(2);           // sus obras siguen alcanzables
  expect(r.textoEnElPoster).toEqual([]);     // muda: nada que el encabezado ya diga
});

test('T115b — si el programa trae afiche oficial, la ficha lo respeta', async ({ page }) => {
  await enterFestival(page, 'cinemancia2026', '2026-09-04T10:00');
  const r = await page.evaluate(() => {
    // El caso donde la jerarquía DECIDE: afiche oficial del programa Y los
    // afiches completos de todas sus obras. Sin esta segunda condición el test
    // pasa por la razón equivocada —la Escalera no entraría igual, por falta de
    // afiches— y la mutación que quita la jerarquía lo deja verde. Pasó: hubo
    // que cazarlo mutando. En Cinemancia hay 14 compuestos así.
    const f = FILMS.find(x => x.poster && x.film_list && x.film_list.length >= 2
      && x.film_list.length <= 8
      && x.film_list.every(i => i.poster && i.posterSource !== 'editorial'));
    if (!f) return { falta: true };
    openPelSheet(f.title);
    return { titulo: f.title, oficial: f.poster, obras: f.film_list.length,
      escalera: !!document.querySelector('.psp-escalera svg'),
      muestraElOficial: !!document.querySelector('.pel-sheet-poster, .psp-editorial') };
  });
  expect(r.falta).toBeFalsy();
  expect(r.escalera).toBe(false);         // la pila nuestra NO tapa el arte del festival
  expect(r.muestraElOficial).toBe(true);
});

// ── T143 — con una hoja abierta, el toast no aterriza sobre sus controles ────
// El toast vive a 62px del borde inferior, encima de la barra de tabs. Las hojas
// son TODAS bottom-anchored, así que con una abierta el aviso caía justo sobre
// lo que hay que tocar: medido en la hoja de calificación, tapaba 38 de los 84px
// del área de estrellas —la mitad de abajo— y el texto «Deslizá sobre las
// estrellas» quedaba debajo. Con showActionToast (pointer-events:all) además
// INTERCEPTABA el toque, no solo lo tapaba.
//
// Se mide el SOLAPE en píxeles contra el control, que es el hallazgo, y no la
// clase CSS: una regla puede declararse y no aplicar. La segunda mitad —sin hoja
// el toast se queda abajo— impide «arreglarlo» mandándolo siempre arriba, que
// lo pondría sobre el contenido del Programa.
test('T143 — el toast se aparta de la hoja, y solo cuando hay hoja', async ({ page }) => {
  await enterFestival(page, 'cinemancia2026', '2026-09-08T20:00:00-05:00');
  const r = await page.evaluate(async () => {
    const w = ms => new Promise(r => setTimeout(r, ms));
    const tap = a => { const b = document.createElement('button'); b.setAttribute('data-action', a);
      document.body.appendChild(b); b.click(); b.remove(); };
    tap('closeCitySheet');
    await w(600);
    const F = await import('/src/view/feedback.js');
    const caja = el => { const b = el.getBoundingClientRect(); return { y: b.top, bot: b.bottom }; };
    const solape = (a, b) => Math.round(Math.max(0, Math.min(a.bot, b.bot) - Math.max(a.y, b.y)));
    // 1 · SIN hoja: el toast se queda donde siempre, abajo
    F.showToast('Movida a Ya vistas', 'info');
    await w(400);
    const t1 = document.getElementById('prio-toast');
    const sinHoja = { y: Math.round(caja(t1).y), vp: window.innerHeight };
    // 2 · CON hoja: la de calificación, por su acción real
    const obra = FILMS[0];
    tap('closePelSheet');
    const b = document.createElement('button');
    b.setAttribute('data-action', 'openPostViewRating');
    b.setAttribute('data-title', obra.title); b.setAttribute('data-day', obra.day || '');
    b.setAttribute('data-time', obra.time || ''); b.setAttribute('data-venue', obra.venue || '');
    document.body.appendChild(b); b.click(); b.remove();
    await w(1200);
    const estrellas = document.querySelector('.pv-stars-area, .rating-stars');
    if (!estrellas) return { sinEstrellas: true, sinHoja };
    F.showToast('Movida a Ya vistas', 'info');
    await w(400);
    const t2 = document.getElementById('prio-toast');
    return { sinHoja,
      conHoja: { y: Math.round(caja(t2).y), solape: solape(caja(estrellas), caja(t2)),
        altoEstrellas: Math.round(caja(estrellas).bot - caja(estrellas).y) } };
  });
  // Premisa, no escape: sin el área de estrellas no hay hoja contra la que
  // medir el toast, y eso tiene que sonar en vez de dar verde ([test-salida-muda]).
  expect(r.sinEstrellas, 'la hoja de calificación abre: es contra ella que se mide el toast')
    .toBeUndefined();
  expect(r.sinHoja.y, 'sin hoja el toast sigue abajo, encima de los tabs')
    .toBeGreaterThan(r.sinHoja.vp / 2);
  expect(r.conHoja.altoEstrellas, 'la hoja muestra su área de estrellas').toBeGreaterThan(40);
  expect(r.conHoja.solape, 'y el toast no pisa ni un píxel de ella').toBe(0);
});

// ── T167 — quitar de Intereses tiene vuelta atrás ────────────────────────────
// Auditoría A-2 (2 sep 2026): quitar una obra que NO está en el Plan no pregunta
// —el modal es solo para lo que está en el Plan— y el toast era informativo, sin
// botón. Medido: clase «prio-toast info», 0 botones de acción. Un toque de más
// borraba la obra, sus compañeras de función y su prioridad, en silencio.
//
// Lo que se afirma: (1) el toast ofrece «Deshacer»; (2) al usarlo vuelven los
// TRES conjuntos —intereses, vista y prioridad— y también las compañeras de
// función; (3) sobrevive a una recarga, o sea que se guardó de verdad;
// (4) control: sin tocar «Deshacer», la obra sigue fuera.
test('T167 — quitar de Intereses ofrece deshacer, y el deshacer repone todo', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await enterFestival(page, 'finca2026', '2026-08-13T10:00');

  // una obra ANCLADA (con compañera de función) y fuera del Plan: es el caso
  // donde más se pierde de un toque
  const prep = await page.evaluate(async () => {
    const g = {};
    FILMS.forEach(f => { if (f._slotKey && !f._cancelled) (g[f._slotKey] ||= []).push(f); });
    // La obra tiene que estar en UNA sola función: cuando un título gira por
    // varias con distintas compañeras, la intersección es vacía a propósito
    // (regla de «la MISMA función», handlers.js) y no arrastraría a nadie.
    const unaSola = t => FILMS.filter(f => f.title === t && f._slotKey)
      .reduce((s, f) => s.add(f._slotKey), new Set()).size === 1;
    const grupo = Object.values(g).find(x => x.length >= 2 && x.every(f => unaSola(f.title)));
    if (!grupo) return null;
    const tit = grupo[0].title;
    toggleWL(tit);
    await new Promise(r => setTimeout(r, 300));
    togglePriority(tit);
    await new Promise(r => setTimeout(r, 300));
    return { tit, hermanas: grupo.slice(1).map(f => f.title),
      enWL: watchlist.has(tit), enPrio: prioritized.has(tit),
      hermanasEnWL: grupo.slice(1).filter(f => watchlist.has(f.title)).length,
      enPlan: !!(savedAgenda && savedAgenda.schedule.some(s => s._title === tit)) };
  });
  expect(prep, 'el festival tiene una función compartida de obras que no giran').not.toBeNull();
  expect(prep.hermanas.length, 'con al menos una compañera — si no, no se prueba el arrastre').toBeGreaterThanOrEqual(1);
  expect(prep.enWL, 'la obra quedó en Intereses').toBe(true);
  expect(prep.enPrio, 'y priorizada').toBe(true);
  expect(prep.hermanasEnWL, 'con sus compañeras de función').toBe(prep.hermanas.length);
  expect(prep.enPlan, 'y NO está en el Plan: por eso quitar no pregunta').toBe(false);

  // quitar → el toast tiene que ofrecer la vuelta atrás
  const tras = await page.evaluate(async (p) => {
    toggleWL(p.tit);
    await new Promise(r => setTimeout(r, 400));
    const toast = document.getElementById('prio-toast');
    const btn = toast && toast.querySelector('.toast-action-btn');
    return { enWL: watchlist.has(p.tit), enPrio: prioritized.has(p.tit),
      hermanasEnWL: p.hermanas.filter(h => watchlist.has(h)).length,
      hayBoton: !!btn, etiqueta: btn ? btn.textContent.trim() : null,
      visible: toast ? getComputedStyle(toast).opacity : null };
  }, prep);
  expect(tras.enWL, 'la obra salió de Intereses').toBe(false);
  expect(tras.hermanasEnWL, 'y sus compañeras también').toBe(0);
  expect(tras.hayBoton, 'el toast ofrece una salida, no solo avisa').toBe(true);
  expect(tras.etiqueta, 'y dice qué hace').toBe('Deshacer');
  expect(tras.visible, 'el toast está a la vista').toBe('1');

  // usarla → vuelven los tres conjuntos y las compañeras
  const undo = await page.evaluate(async (p) => {
    document.querySelector('.toast-action-btn').click();
    await new Promise(r => setTimeout(r, 500));
    return { enWL: watchlist.has(p.tit), enPrio: prioritized.has(p.tit),
      hermanasEnWL: p.hermanas.filter(h => watchlist.has(h)).length };
  }, prep);
  expect(undo.enWL, 'la obra volvió a Intereses').toBe(true);
  expect(undo.enPrio, 'con su prioridad, no solo el interés').toBe(true);
  expect(undo.hermanasEnWL, 'y sus compañeras de función volvieron con ella').toBe(prep.hermanas.length);

  // y sobrevive a una recarga: se guardó, no quedó solo en memoria.
  // La recarga borra _simTime y devuelve al selector → hay que re-entrar
  // (mismo patrón que el resto de la suite, ver `reentrar` en helpers).
  await page.reload();
  await reentrar(page, 'finca2026', '2026-08-13T10:00');
  await page.waitForTimeout(1200);
  const post = await page.evaluate(p => ({ enWL: watchlist.has(p.tit),
    enPrio: prioritized.has(p.tit),
    hermanasEnWL: p.hermanas.filter(h => watchlist.has(h)).length }), prep);
  expect(post.enWL, 'tras recargar sigue en Intereses: el deshacer persistió').toBe(true);
  expect(post.enPrio, 'y sigue priorizada').toBe(true);
  expect(post.hermanasEnWL, 'y las compañeras siguen').toBe(prep.hermanas.length);

  // control: si NO se toca «Deshacer», la obra se queda fuera
  const sinUndo = await page.evaluate(async (p) => {
    toggleWL(p.tit);
    await new Promise(r => setTimeout(r, 400));
    const t2 = document.getElementById('prio-toast');
    if (t2) { t2.style.opacity = '0'; t2.style.pointerEvents = 'none'; }  // se vence sin tocarlo
    await new Promise(r => setTimeout(r, 300));
    return { enWL: watchlist.has(p.tit), enPrio: prioritized.has(p.tit) };
  }, prep);
  expect(sinUndo.enWL, 'sin deshacer, la obra sigue fuera — el quitar no se anula solo').toBe(false);
  expect(sinUndo.enPrio, 'y sin prioridad').toBe(false);
});

// ── T171 — Avisos dice cuando la duración no está publicada ──────────────────
// Auditoría 4 sep 2026: el festival no publica la duración de algunas actividades
// (28 registros en 7 festivales). La app rellena con DEFAULT_DURATION_MIN y sobre
// ese número afirma la hora de salida y descarta obras del plan. Es un rasgo de la
// función, igual que el Q&A, y su casa es la banda de Avisos: se lee ANTES de
// decidir. (Decisión de Juan, 4 sep: acá y no en las notas del evento exportado.)
//
// Se afirma: (1) la ficha de la actividad sin duración trae la fila, con los
// minutos que la app realmente usa; (2) una obra CON duración no la trae — el
// control que impide que el aviso salga siempre y deje de querer decir algo.
test('T171 — Avisos avisa que la duración es estimada, y solo cuando lo es', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await enterFestival(page, 'cinemancia2026', '2026-09-09T15:00');

  const avisos = async (conDuracion) => page.evaluate(async (conD) => {
    const b = document.createElement('button'); b.setAttribute('data-action', 'closeCitySheet');
    document.body.appendChild(b); b.click(); b.remove();
    await new Promise(r => setTimeout(r, 300));
    const f = FILMS.find(x => !x._cancelled && x.day && x.time && (conD ? x.duration : !x.duration));
    if (!f) return null;
    if (typeof closePelSheet === 'function') closePelSheet();
    await new Promise(r => setTimeout(r, 200));
    openPelSheet(f.title);
    await new Promise(r => setTimeout(r, 1000));
    const txt = (document.getElementById('pel-sheet')?.innerText || '').replace(/\s+/g, ' ');
    return { obra: f.title.slice(0, 30), duration: f.duration || null, texto: txt.slice(0, 400) };
  }, conDuracion);

  // 1 · sin duración publicada: el aviso está, con los minutos que la app usa
  const sin = await avisos(false);
  expect(sin, 'Cinemancia tiene la actividad sin duración del censo').not.toBeNull();
  expect(sin.duration, 'y de verdad no la trae').toBeNull();
  expect(sin.texto, `«${sin.obra}»: Avisos nombra la duración`).toMatch(/DURACI[ÓO]N/i);
  expect(sin.texto, 'y dice que es una estimación').toMatch(/estimad/i);
  expect(sin.texto, 'con los minutos que la app efectivamente usa').toContain('90 min');

  // 2 · control: con duración publicada NO aparece el aviso. Sin esto, «avisar
  // siempre» pasaría el test y la fila dejaría de significar algo.
  const con = await avisos(true);
  expect(con, 'y hay obras con duración').not.toBeNull();
  expect(con.duration, 'esta sí la trae').toBeTruthy();
  expect(con.texto, `«${con.obra}» (${con.duration}) no lleva aviso de duración estimada`)
    .not.toMatch(/min estimados/i);

  // 3 · la ficha de un CORTO no tiene film propio: el aviso se deriva de las
  // funciones heredadas, no del film. Leerlo directo reventaba las 6 pruebas de
  // esa ficha con «Cannot read properties of null» — lo cazó la suite, no yo.
  const corto = await page.evaluate(async () => {
    const prog = FILMS.find(f => f.is_cortos && f.film_list && f.film_list.length);
    if (!prog) return { sinPrograma: true };
    if (typeof closePelSheet === 'function') closePelSheet();
    await new Promise(r => setTimeout(r, 200));
    const it = prog.film_list[0];
    openCortoSheet(it.title, it.country, it.duration, prog.section, it.flags, it.director, it.genre, it.synopsis);
    await new Promise(r => setTimeout(r, 900));
    const sheet = document.querySelector('#corto-sheet, #pel-sheet');
    return { abrio: !!sheet, texto: (sheet?.innerText || '').replace(/\s+/g, ' ').slice(0, 200) };
  });
  if (!corto.sinPrograma) {
    expect(corto.abrio, 'la ficha del corto abre — sin esto el caso no se prueba').toBe(true);
  }
});

// ── T174 — la prioridad se retira con el planeador ───────────────────────────
// Auditoría 4 sep 2026: con el festival terminado, la ficha seguía ofreciendo
// «Priorizar» y, con el cupo lleno, abría una hoja de canje de 575px —el 68% de
// la pantalla— pidiendo cambiar una prioridad por otra. En la misma sesión,
// Planear ya decía «El planeador descansa hasta el próximo festival».
//
// Las prioridades no tienen otro consumidor que el planeador: ofrecerlas cuando
// se retiró es ofrecer una acción sin consecuencia. Se retiran con él. Las que
// ya existían siguen visibles (la marca ámbar del bloque en Mi Plan): lo que se
// va es la posibilidad de negociar un cupo que no alimenta a nadie.
//
// Nota de lo medido, sin tocar: el cupo se calcula con `prioLiveCount`, que llama
// a `screeningPassed`, y ESE devuelve false post-festival a propósito («todo
// vuelve a plena opacidad»). O sea que después del cierre el cupo cuenta TODAS
// como vivas y se llena. No se corrige acá porque, sin el botón, ningún camino lo
// consulta y ninguna superficie post-festival muestra el contador (verificado en
// las cuatro pestañas).
test('T174 — un festival terminado no ofrece priorizar', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });

  const ficha = async (sim) => {
    await enterFestival(page, 'ficdeh2026', sim);
    return page.evaluate(async () => {
      // se cierran las hojas que pudo dejar abiertas la medición anterior: sin
      // esto, la hoja de canje del caso «en curso» seguía en pantalla y el caso
      // «terminado» la contaba como suya.
      const b = document.createElement('button'); b.setAttribute('data-action', 'closeCitySheet');
      document.body.appendChild(b); b.click(); b.remove();
      // la hoja de canje del caso anterior se cierra a mano: sin esto seguía en
      // pantalla y el caso «terminado» la contaba como suya.
      document.getElementById('prio-limit-sheet')?.classList.remove('open');
      await new Promise(r => setTimeout(r, 500));
      const t = [...new Set(FILMS.filter(f => !f._cancelled && f.title).map(f => f.title))].slice(0, PRIO_LIMIT + 1);
      state.set('watchlist', new Set(t));
      state.set('prioritized', new Set(t.slice(0, PRIO_LIMIT)));   // cupo LLENO
      state.set('watched', new Set());
      if (typeof closePelSheet === 'function') closePelSheet();
      await new Promise(r => setTimeout(r, 200));
      openPelSheet(t[PRIO_LIMIT]);                                  // una que NO está priorizada
      await new Promise(r => setTimeout(r, 1000));
      const btn = [...document.querySelectorAll('[data-action="togglePelPrio"]')]
        .filter(e => e.getBoundingClientRect().height > 0);
      // si el botón existe, se toca: es lo que abría la hoja de canje
      if (btn.length) { btn[0].click(); await new Promise(r => setTimeout(r, 900)); }
      // el nodo de la hoja existe SIEMPRE y tiene caja aunque esté cerrada: lo que
      // dice si está abierta es la clase `.open`, que es la que conmuta el código.
      // Medirlo por el rect daba «abierta» en los dos casos y el test no probaba nada.
      const hoja = document.querySelector('#prio-limit-sheet');
      const abierta = !!(hoja && hoja.classList.contains('open'));
      const hr = hoja ? hoja.getBoundingClientRect() : null;
      return { obra: t[PRIO_LIMIT].slice(0, 26), limite: PRIO_LIMIT,
        ofreceBoton: btn.length, etiqueta: btn.length ? btn[0].textContent.trim().slice(0, 18) : null,
        hojaDeCanje: abierta, altoHoja: abierta && hr ? Math.round(hr.height) : 0,
        // qué botones quedan, POR NOMBRE: contar no alcanza —borrar otro botón
        // bajaba los dos lados por igual y la mutación pasaba limpia—.
        botones: ['pel-wl-btn', 'pel-prio-btn', 'pel-vista-btn']
          .filter(id => { const e = document.getElementById(id); return e && e.getBoundingClientRect().height > 0; }) };
    });
  };

  // 1 · control primero: EN CURSO el botón está y el cupo se defiende. Va antes a
  // propósito — si la ficha no abriera, el caso de abajo pasaría solo.
  const vivo = await ficha('2026-08-15T11:00');
  expect(vivo.ofreceBoton, 'con el festival en curso la ficha ofrece priorizar').toBeGreaterThan(0);
  expect(vivo.botones, 'y la fila viva tiene sus tres botones').toEqual(['pel-wl-btn', 'pel-prio-btn', 'pel-vista-btn']);
  expect(vivo.hojaDeCanje, 'y con el cupo lleno abre la hoja de canje, como está diseñada').toBe(true);
  expect(vivo.altoHoja, 'que ocupa media pantalla').toBeGreaterThan(300);

  // 2 · el hallazgo: TERMINADO no ofrece la acción, y por lo tanto no hay canje
  const cerrado = await ficha('2026-08-25T11:00');
  expect(cerrado.ofreceBoton, 'terminado, la ficha ya no ofrece priorizar').toBe(0);
  expect(cerrado.hojaDeCanje, 'y no hay cupo que negociar').toBe(false);
  // «no se retiró de más», por nombre: se va el de priorizar y SOLO ese.
  expect(cerrado.botones, `los botones que quedan (viva: ${vivo.botones.join(', ')})`)
    .toEqual(vivo.botones.filter(b => b !== 'pel-prio-btn'));
});

// ── T176 — la banda no le pone precio a una función cancelada ────────────────
// Auditoría 4 sep 2026, FICDEH: la ficha de «Bojayá, la verdad desde adentro»
// listaba 7 funciones CANCELADA y, tres renglones más abajo, decía CON BOLETA
// nombrando funciones que están en esa misma lista. La misma tarjeta se
// desmentía sola.
//
// Una función cancelada no tiene precio: no va a ocurrir. Y lo que invalida se
// lee ANTES que lo que matiza (DESIGN 8.4.6), así que el precio se dice de las
// VIVAS. Si TODAS están canceladas no se dice nada de precio: el aviso de
// cancelada ya lo dijo todo.
//
// Se afirma: (1) ninguna función nombrada en el aviso de precio aparece también
// en el de cancelada; (2) el aviso de precio SIGUE estando cuando hay funciones
// vivas —el control: callarlo del todo también quitaría la contradicción, y sería
// peor—; (3) el aviso de cancelada sigue nombrando las suyas.
test('T176 — el precio se dice de las funciones vivas, no de las canceladas', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await enterFestival(page, 'ficdeh2026', '2026-08-15T11:00');
  const r = await page.evaluate(async () => {
    const b = document.createElement('button'); b.setAttribute('data-action', 'closeCitySheet');
    document.body.appendChild(b); b.click(); b.remove();
    await new Promise(r => setTimeout(r, 500));
    // una obra con funciones canceladas Y vivas: es donde la contradicción vive
    const porTitulo = {};
    FILMS.forEach(f => { if (f.title) (porTitulo[f.title] ||= []).push(f); });
    // La obra se elige por DATO y de forma determinista: la que MÁS funciones de
    // pago canceladas tiene. `_cual` solo nombra cuando el rasgo está en algunas y
    // no en todas, así que hace falta un subconjunto propio de pago que además
    // contenga canceladas. Las dos primeras versiones elegían «la primera que
    // cumple» y caían en una obra cuyo aviso nombraba una función VIVA: no había
    // contradicción que medir y el test pasaba con el código viejo.
    const tit = Object.keys(porTitulo)
      .filter(t => {
        const fs = porTitulo[t]; const pago = fs.filter(f => f.is_free !== true);
        return pago.length > 0 && pago.length < fs.length && pago.some(f => f._cancelled);
      })
      .sort((a, b) => porTitulo[b].filter(f => f.is_free !== true && f._cancelled).length
                    - porTitulo[a].filter(f => f.is_free !== true && f._cancelled).length)[0];
    if (!tit) return { sinCaso: true };
    if (typeof closePelSheet === 'function') closePelSheet();
    await new Promise(r => setTimeout(r, 200));
    openPelSheet(tit);
    await new Promise(r => setTimeout(r, 1100));
    const cuerpo = document.querySelector('#pel-sheet .avisos-body');
    if (!cuerpo) return { sinBanda: true, tit };
    // cada aviso es un par pill + texto
    const pills = [...cuerpo.querySelectorAll('.aviso-pill')].map(e => e.textContent.trim());
    const txts = [...cuerpo.querySelectorAll('.aviso-txt')].map(e => e.textContent.replace(/\s+/g, ' ').trim());
    // los días llevan tilde («mié», «sáb»): `\w` no los toma.
    const horas = s => [...s.matchAll(/([^\s·]{3})\s+(\d{1,2})\s*·\s*(\d{1,2}:\d{2})/g)].map(m => `${m[1]} ${m[2]} ${m[3]}`);
    // TODAS las filas de cancelada, no la primera: esta obra tiene siete, y
    // mirando una sola el solapamiento se escapaba.
    const iPrecio = pills.findIndex(p => /boleta|gratis/i.test(p));
    const _hc = pills.map((p, i) => /cancel/i.test(p) ? horas(txts[i] || '') : []).flat();
    const fs = porTitulo[tit];
    return { tit: tit.slice(0, 30), pills,
      canceladas: fs.filter(f => f._cancelled).length, vivas: fs.filter(f => !f._cancelled).length,
      horasCanceladas: _hc,
      horasPrecio: iPrecio >= 0 ? horas(txts[iPrecio]) : [],
      textoPrecio: iPrecio >= 0 ? (txts[iPrecio] || '').slice(0, 90) : null,
      hayPrecio: iPrecio >= 0, hayCancelada: _hc.length > 0 };
  });

  expect(r.sinCaso, 'FICDEH tiene una obra con funciones canceladas y vivas').toBeUndefined();
  expect(r.sinBanda, `«${r.tit}» muestra su banda de avisos`).toBeUndefined();
  expect(r.canceladas, 'y de verdad tiene canceladas').toBeGreaterThan(0);
  expect(r.vivas, 'y también vivas').toBeGreaterThan(0);

  // 1 · ninguna función nombrada en el precio está entre las canceladas
  const solapan = r.horasPrecio.filter(h => r.horasCanceladas.includes(h));
  expect(solapan,
    `el aviso de precio no nombra funciones canceladas — dice «${r.textoPrecio}» y las canceladas son [${r.horasCanceladas.join(', ')}]`)
    .toHaveLength(0);

  // 2 · control: el aviso de precio sigue estando. Callarlo del todo también
  // quitaría la contradicción, y sería peor: el usuario dejaría de saber si paga.
  expect(r.hayPrecio, `la banda sigue diciendo el precio (avisos: ${r.pills.join(' / ')})`).toBe(true);

  // 3 · y el aviso de cancelada sigue nombrando las suyas
  expect(r.hayCancelada, 'y sigue avisando de las canceladas, nombrando sus funciones').toBe(true);
});
