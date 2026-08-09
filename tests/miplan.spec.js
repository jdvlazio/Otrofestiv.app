// @ts-check
// miplan.spec.js — Tab Mi Plan: agenda guardada, alternativas, sugerencias.
const { test, expect } = require('@playwright/test');
const { LEVIZA_SIMTIME, enterFestival, addToWatchlist } = require('./helpers');

// T11 — Cerrar alternativas en Mi Plan cierra el panel
test('T11 — cerrar alternativas en Mi Plan cierra el panel', async ({ page }) => {
  await enterFestival(page, 'tribeca2026');
  await page.locator('.mnav-tab[data-nav="mnav-cartelera"], .main-nav-tab').first().click();
  await page.evaluate(() => { switchMainNav('mnav-miplan'); showAgView(); });
  await page.waitForSelector('#ag-view', { state: 'visible', timeout: 8000 });
  const hasPlan = await page.locator('.mplan-t1').count();
  if (hasPlan === 0) { console.log('T11: sin plan activo, skip'); return; }
  await page.locator('.mplan-t1').first().click();
  const altPanel = page.locator('.film-alts').first();
  await expect(altPanel).toBeVisible({ timeout: 5000 });
  await page.locator('.film-alts .checkin-result-btn.secondary').first().click();
  await expect(page.locator('.film-alts')).toHaveCount(0, { timeout: 5000 });
});

// T24 — Quitar sesión del plan la elimina
test('T24 — quitar sesión del plan la elimina', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  const result = await page.evaluate(() => {
    const f = FILMS.find(fi => fi.title === 'Taller de Guion' && fi.day === 'VIE 15');
    if (!f) return { error: 'film not found', total: FILMS.length };
    const schedule = [{ ...f, _title: f.title }];
    const after = schedule.filter(s => normTitle(s._title||'') !== normTitle('Taller de Guion'));
    return { before: schedule.length, after: after.length };
  });
  expect(result.error).toBeUndefined();
  expect(result.before).toBe(1);
  expect(result.after).toBe(0);
});

// T25 — Datos del plan disponibles para el día seleccionado
test('T25 — datos del plan disponibles para el día seleccionado', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  const result = await page.evaluate(() => {
    const f = FILMS.find(fi => fi.title === 'Taller de Guion' && fi.day === 'VIE 15');
    if (!f) return { error: 'film not found', total: FILMS.length };
    savedAgenda = { schedule: [{ ...f, _title: f.title }] };
    const dayIdx = DAY_KEYS.indexOf('VIE 15');
    const dayFilms = savedAgenda.schedule.filter(s => s.day === DAY_KEYS[dayIdx]);
    return { dayIdx, scheduleLen: savedAgenda.schedule.length, dayFilmsLen: dayFilms.length };
  });
  expect(result.error).toBeUndefined();
  expect(result.dayIdx).toBeGreaterThanOrEqual(0);
  expect(result.scheduleLen).toBe(1);
  expect(result.dayFilmsLen).toBe(1);
});

// T26 — Hora punteada abre panel de alternativas
test('T26 — hora punteada abre panel de alternativas', async ({ page }) => {
  await enterFestival(page, 'tribeca2026');
  await page.evaluate(() => { switchMainNav('mnav-miplan'); showAgView(); });
  await page.waitForSelector('#ag-view', { state: 'visible', timeout: 8000 });
  const hasPlan = await page.locator('.mplan-t1').count();
  if (!hasPlan) return;
  await page.locator('.mplan-t1').first().click();
  await expect(page.locator('.film-alts').first()).toBeVisible({ timeout: 5000 });
  expect(await page.locator('.film-alts').count()).toBeGreaterThan(0);
});

// T27 — Sugerencias: botón Añadir NO abre sheet de película
test('T27 — sugerencias: añadir no abre sheet', async ({ page }) => {
  await enterFestival(page, 'tribeca2026');
  await page.evaluate(() => { switchMainNav('mnav-miplan'); showAgView(); });
  await page.waitForSelector('#ag-view', { state: 'visible', timeout: 8000 });
  const addBtn = page.locator('.suggestion-add').first();
  if (!await addBtn.count()) return;
  await addBtn.click();
  await expect(page.locator('#pel-sheet.open')).toHaveCount(0, { timeout: 3000 });
});

// T28 — Sugerencias: botón Añadir muestra toast de confirmación
test('T28 — sugerencias: añadir muestra toast', async ({ page }) => {
  await enterFestival(page, 'tribeca2026');
  await page.evaluate(() => { switchMainNav('mnav-miplan'); showAgView(); });
  await page.waitForSelector('#ag-view', { state: 'visible', timeout: 8000 });
  const addBtn = page.locator('.suggestion-add').first();
  if (!await addBtn.count()) return;
  await addBtn.click();
  await page.waitForSelector('.toast, .toast-msg, #toast', { timeout: 5000 });
  const toast = await page.locator('.toast, .toast-msg, #toast').count();
  expect(toast).toBeGreaterThan(0);
});

// T40 — Mi Plan vacío muestra estado vacío
test('T40 — mi plan vacío muestra estado vacío', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => {
    savedAgenda = null;
    saveSavedAgenda();
    switchMainNav('mnav-miplan');
    showAgView();
    renderAgenda();
  });
  await page.waitForSelector('.empty-state-hero, .cta-ctx', { timeout: 8000 });
  const empty = await page.locator('.empty-state-hero, .cta-ctx').count();
  expect(empty).toBeGreaterThan(0);
});

// T44 — Flujo completo: Tribeca filtro día + intereses + plan + mi plan
test('T44 — flujo completo: Tribeca filtro día + intereses + plan + mi plan', async ({ page }) => {
  await enterFestival(page, 'tribeca2026');
  await page.locator('.dtab[data-day="2026-06-04"]').click();
  await page.waitForSelector('.plist-item', { timeout: 8000 });
  await page.locator('.plist-item').first().locator('.plist-heart').click();
  await page.waitForFunction(() => watchlist.size > 0, { timeout: 5000 });
  const inWL = await page.evaluate(() => watchlist.size > 0);
  expect(inWL).toBe(true);
  await page.locator('#mnav-seleccion').click();
  await page.waitForSelector('#ag-view', { state: 'visible', timeout: 5000 });
  const wlItems = await page.locator('.ag-item, .wl-item, .plist-item').count();
  expect(wlItems).toBeGreaterThan(0);
  await page.locator('#mnav-planner').click();
  const calcBtn = page.locator('.av-calc-btn');
  if (await calcBtn.count() > 0) {
    await calcBtn.click();
    await page.waitForTimeout(500); // mínimo: cálculo async
  }
  await page.locator('#mnav-miplan').click();
  await page.waitForSelector('#ag-view', { state: 'visible', timeout: 5000 });
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.waitForTimeout(200); // mínimo: colección de errores async
  expect(errors).toHaveLength(0);
});

// ─── Anclaje de función en Mi Plan (bug de producción, 30 jul 2026) ───────────
// Dos obras del MISMO slot son UNA función. Mi Plan las trataba como funciones
// rivales: avisaba "Q&A · si te quedás no llegás a la siguiente" entre ellas —la
// siguiente ERA la misma función— y mostraba el fin de cada obra por separado, así
// que un corto de 5 min decía que salías 18:05 cuando la función terminaba 19:51.
test('T50 — dos obras del mismo slot no generan aviso entre ellas y comparten fin', async ({ page }) => {
  await enterFestival(page, 'finca2026', '2026-08-13T10:00');
  const ok = await page.evaluate(() => {
    const slot = FILMS.find(f => f._slotKey && f.title.startsWith('Propiedad'));
    if (!slot) return false;
    const miembros = FILMS.filter(f => f._slotKey === slot._slotKey);
    if (miembros.length < 2) return false;
    state.set('savedAgenda', { schedule: miembros.map(f => ({ ...f, _title: f.title })), scenarioIdx: 0 });
    return true;
  });
  if (!ok) { console.log('T50: sin slot compartido en el festival, skip'); return; }
  await page.evaluate(() => { switchMainNav('mnav-miplan'); showAgView(); });
  await page.waitForSelector('#ag-view', { state: 'visible', timeout: 8000 });
  await page.waitForTimeout(600);
  const d = await page.evaluate(() => ({
    rows: document.querySelectorAll('.mplan-row').length,
    warns: [...document.querySelectorAll('.mplan-warn-row')].map(e => e.textContent.trim()),
    fines: [...document.querySelectorAll('.mplan-row .mplan-t2')].map(e => (e.textContent.match(/\d{1,2}:\d{2}/) || [''])[0]),
  }));
  // las dos filas existen (si no, el resto no probaría nada)
  expect(d.rows).toBe(2);
  // ningún aviso entre ellas
  expect(d.warns).toHaveLength(0);
  // y las dos terminan a la MISMA hora: es una sola función
  expect(new Set(d.fines).size).toBe(1);
});

// T51 — el calendario dibuja UN bloque por función, con todas sus obras dentro
// Antes pintaba un bloque por obra: dos encimados arrancando a la misma hora, uno
// de 106 min y otro de 5 min montado encima. La función se dibuja completa.
test('T51 — el calendario dibuja un solo bloque para la función compartida', async ({ page }) => {
  await enterFestival(page, 'finca2026', '2026-08-13T10:00');
  const ok = await page.evaluate(() => {
    const slot = FILMS.find(f => f._slotKey && f.title.startsWith('Propiedad'));
    if (!slot) return false;
    const miembros = FILMS.filter(f => f._slotKey === slot._slotKey);
    if (miembros.length < 2) return false;
    state.set('savedAgenda', { schedule: miembros.map(f => ({ ...f, _title: f.title })), scenarioIdx: 0 });
    return true;
  });
  if (!ok) { console.log('T51: sin slot compartido, skip'); return; }
  await page.evaluate(() => { switchMainNav('mnav-miplan'); showAgView(); });
  await page.waitForSelector('#ag-view', { state: 'visible', timeout: 8000 });
  await page.waitForTimeout(600);
  const d = await page.evaluate(() => {
    const bs = [...document.querySelectorAll('.mplan-col-mobile .mplan-wk-block')];
    return { bloques: bs.length, titulos: bs.length ? bs[0].querySelectorAll('.mplan-wk-title').length : 0 };
  });
  expect(d.bloques).toBe(1);      // una función, un bloque
  expect(d.titulos).toBe(2);      // con TODAS sus obras listadas
});

// T52 — la entrada afectada por un aviso tiene SALIDA, no solo marca
// El badge dice QUÉ pasó; el botón dice QUÉ HAGO. Reprogramada → se muda a la
// hora nueva (reusa addSuggestion, que revalida conflictos). Cancelada → se
// quita y lleva a Sugerencias con el hueco libre. Nada se mueve ni se borra solo.
test('T52 — Actualizar muda la entrada a la función nueva', async ({ page }) => {
  await enterFestival(page, 'finca2026', '2026-08-13T10:00');
  const ok = await page.evaluate(() => {
    // se simula el aviso sobre el DATO, igual que lo haría el loader desde NOTICES
    const f = FILMS.find(fi => fi.title === 'Ziki');
    if (!f) return false;
    f._movedFrom = { day: f.day, time: f.time, venue: f.venue };
    f.day = '2026-08-14'; f.time = '21:00'; f.day_order = 2;
    state.set('savedAgenda', { schedule: [{ ...f, _title: f.title,
      day: f._movedFrom.day, time: f._movedFrom.time, venue: f._movedFrom.venue }], scenarioIdx: 0 });
    return true;
  });
  if (!ok) { console.log('T52: sin film de prueba, skip'); return; }
  await page.evaluate(() => { switchMainNav('mnav-miplan'); showAgView(); });
  await page.waitForSelector('#ag-view', { state: 'visible', timeout: 8000 });
  await page.waitForTimeout(600);
  const btn = page.locator('.mplan-fix').first();
  await expect(btn).toBeVisible({ timeout: 5000 });
  await btn.click();
  await page.waitForTimeout(700);
  const entry = await page.evaluate(() => savedAgenda.schedule.find(s => s._title === 'Ziki') || {});
  expect(entry.day).toBe('2026-08-14');
  expect(entry.time).toBe('21:00');
});

// T53 — la hora tachada NO arrastra al badge ni al botón
// `text-decoration` de un ancestro se PROPAGA al dibujar y no se puede cancelar
// desde un hijo: con la regla en la fila quedaban tachados los tres.
test('T53 — el tachado de la hora no alcanza al badge ni a la salida', async ({ page }) => {
  await enterFestival(page, 'finca2026', '2026-08-13T10:00');
  const ok = await page.evaluate(() => {
    const f = FILMS.find(fi => fi.title === 'Yurlu');
    if (!f) return false;
    f._cancelled = true;
    state.set('savedAgenda', { schedule: [{ ...f, _title: f.title }], scenarioIdx: 0 });
    return true;
  });
  if (!ok) { console.log('T53: sin film de prueba, skip'); return; }
  await page.evaluate(() => { switchMainNav('mnav-miplan'); showAgView(); });
  await page.waitForSelector('.mplan-fix', { timeout: 8000 });
  const deco = await page.evaluate(() => {
    const g = s => { const e = document.querySelector(s); return e ? getComputedStyle(e).textDecorationLine : null; };
    return { hora: g('.mp-void-t'), badge: g('.mplan-t2 .notice-badge'), boton: g('.mplan-fix') };
  });
  expect(deco.hora).toBe('line-through');
  expect(deco.badge).toBe('none');
  expect(deco.boton).toBe('none');
});

// ── T56 — el taller multi-día entra y sale ENTERO ────────────────────────────
// Un taller de varios días se toma completo: quien se inscribe va a todas las
// sesiones. Hasta ahora `is_recurring` solo APAGABA el botón por sesión y no
// ponía nada en su lugar — el único camino al Plan era Intereses + planificador.
//
// La regla dura: si una sola sesión no cabe, no entra NINGUNA. Un plan con «1 de
// 2» no es medio taller, es un plan que miente sobre un compromiso que nadie
// tomó. Y verifyPlan no puede cazarlo por su cuenta: para él las repeticiones
// del título son legítimas, que es justo el permiso que da is_recurring.
test('T56 — el taller multi-día entra y sale entero, y no entra a medias', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  const leer = () => page.evaluate(() => ({
    enPlan: ((savedAgenda && savedAgenda.schedule) || []).filter(e => e._title === 'Taller de Guion').length,
    control: document.querySelector('#pel-sheet .pel-sheet-bloque .suggestion-add')?.textContent.trim() || '',
    marcadas: document.querySelectorAll('#pel-sheet .pel-sheet-screening.in-plan').length,
    porSesion: document.querySelectorAll('#pel-sheet .pel-sheet-screening .suggestion-add').length,
  }));
  const tocar = async () => {
    await page.evaluate(() => { const b = document.querySelector('#pel-sheet .pel-sheet-bloque .suggestion-add'); if (b) b.click(); });
    await page.waitForTimeout(1200);
  };
  await page.evaluate(() => openPelSheet('Taller de Guion'));
  await page.waitForTimeout(1100);

  const a = await leer();
  expect(a.control, 'el control es del bloque y dice cuántas son').toMatch(/3 sesiones/);
  expect(a.porSesion, 'ninguna sesión tiene botón propio').toBe(0);

  await tocar();
  const b = await leer();
  expect(b.enPlan, 'entran las 3 de una').toBe(3);
  expect(b.marcadas, 'el estado «en tu plan» es del bloque: todas las filas marcadas').toBe(3);
  expect(b.control).toMatch(/Quitar/);
  // el plan resultante es válido: 3 veces el mismo título NO es duplicado
  const cert = await page.evaluate(() => verifyPlan(savedAgenda.schedule, { catalog: FILMS }));
  expect(cert.ok, JSON.stringify(cert.violations)).toBe(true);

  await tocar();
  expect((await leer()).enPlan, 'quitar saca todas').toBe(0);

  // TODO O NADA: con la 2ª sesión ocupada, no entra ninguna — ni la 1ª, que cabía
  await page.evaluate(() => {
    const ses = FILMS.filter(f => f.title === 'Taller de Guion' && f.day && f.time).sort((x, y) => x.day_order - y.day_order);
    const s1 = ses[1];
    state.set('savedAgenda', { schedule: [{ _title: 'Rival', title: 'Rival', day: s1.day,
      time: s1.time, venue: s1.venue, duration: '120 min', day_order: s1.day_order }] });
    openPelSheet('Taller de Guion');
  });
  await page.waitForTimeout(1100);
  await tocar();
  const c = await leer();
  expect(c.enPlan, 'si una sesión no cabe, no entra ninguna').toBe(0);
  expect(await page.evaluate(() => savedAgenda.schedule.some(e => e._title === 'Rival')),
    'y no se saca nada del plan sin permiso').toBe(true);
});

// T57 — un taller que YA EMPEZÓ no se ofrece. Cazado con los datos reales de
// FICMA 17: su taller de 2 días mostraba «Añadir las 1 sesiones» —mal escrito y,
// peor, incoherente—: se ofrecían «las sesiones que quedan», pero verifyPlan
// cuenta TODAS las del catálogo, así que ese plan de 1 de 2 lo marcaba el propio
// chokepoint como bloque-incompleto. Un taller se toma entero; si su primera
// sesión pasó, ya no se puede.
test('T57 — un taller ya empezado no se ofrece', async ({ page }) => {
  // víspera: se ofrece completo
  await enterFestival(page, 'leviza2026', '2026-05-13T09:00:00-05:00');
  await page.evaluate(() => openPelSheet('Taller de Guion'));
  await page.waitForTimeout(1100);
  const antes = await page.evaluate(() =>
    document.querySelector('#pel-sheet .pel-sheet-bloque .suggestion-add')?.textContent.trim() || '');
  expect(antes).toMatch(/3 sesiones/);

  // con la primera sesión ya pasada: sin control de añadir
  await enterFestival(page, 'leviza2026', '2026-05-15T23:00:00-05:00');
  await page.evaluate(() => openPelSheet('Taller de Guion'));
  await page.waitForTimeout(1100);
  const despues = await page.evaluate(() => ({
    ctrl: document.querySelector('#pel-sheet .pel-sheet-bloque .suggestion-add')?.textContent.trim() || '',
    filas: document.querySelectorAll('#pel-sheet .pel-sheet-screening').length,
  }));
  expect(despues.ctrl, 'no se ofrece un taller que ya empezó').toBe('');
  expect(despues.filas, 'las sesiones siguen listándose, informativas').toBeGreaterThan(0);
});

// T58 — un taller multi-día no aparece en Sugerencias.
// Era el único camino que quedaba para romper el bloque: el botón de la
// sugerencia llama a addSuggestion, que añade UNA función — y eso deja el bloque
// a medias, justo lo que prohíbe el invariante. (Quitar, en cambio, nunca lo
// rompió: tanto Mi Plan como Planear filtran por TÍTULO, así que sacan las N.)
test('T58 — el taller multi-día no se ofrece como sugerencia', async ({ page }) => {
  await enterFestival(page, 'leviza2026', '2026-05-13T09:00:00-05:00');
  const r = await page.evaluate(() => {
    const rec = FILMS.filter(f => f.is_recurring && f.day && f.time);
    const tallerTitulo = rec[0].title;
    // plan mínimo para que el motor de sugerencias corra, + el taller en Intereses
    const suelta = FILMS.find(f => !f.info && f.day && f.time && !f.is_recurring);
    state.set('savedAgenda', { schedule: [{ _title: suelta.title, title: suelta.title, day: suelta.day,
      time: suelta.time, venue: suelta.venue, duration: suelta.duration, day_order: suelta.day_order }] });
    watchlist.clear(); watchlist.add(tallerTitulo);
    switchMainNav('mnav-miplan'); showAgView();
    return { tallerTitulo, sesiones: rec.length };
  });
  await page.waitForTimeout(1200);
  const ofrecido = await page.evaluate((t) =>
    [...document.querySelectorAll('[data-action="addSuggestion"]')].some(b => b.dataset.title === t),
  r.tallerTitulo);
  expect(ofrecido, 'una sesión suelta del bloque no puede ofrecerse: addSuggestion añade una sola').toBe(false);
});
