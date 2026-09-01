// @ts-check
// miplan.spec.js — Tab Mi Plan: agenda guardada, alternativas, sugerencias.
const { test, expect } = require('@playwright/test');
const { LEVIZA_SIMTIME, enterFestival, addToWatchlist, goToPlanear, esperarCalculo } = require('./helpers');

// T11 — Cerrar alternativas en Mi Plan cierra el panel
test('T11 — cerrar alternativas en Mi Plan cierra el panel', async ({ page }) => {
  await enterFestival(page, 'tribeca2026');
  await page.locator('.mnav-tab[data-nav="mnav-cartelera"], .main-nav-tab').first().click();
  await page.evaluate(() => { switchMainNav('mnav-miplan'); showAgView(); });
  await page.waitForSelector('#ag-view', { state: 'visible', timeout: 8000 });
  const hasPlan = await page.locator('.mplan-t1').count();
  if (hasPlan === 0) { test.skip(true, 'T11: sin plan activo, skip'); return; }
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
  // Salida MUDA: sin plan el test pasaba en verde sin ejercer una sola aserción.
  // Un test que no corre tiene que decirlo — si no, la suite miente.
  test.skip(!hasPlan, 'T26: sin plan activo en el festival de prueba');
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
  // Salida MUDA: sin botón de sugerencia no se ejercía nada y daba verde.
  test.skip(!await addBtn.count(), 'sin sugerencia disponible para agregar');
  await addBtn.click();
  await expect(page.locator('#pel-sheet.open')).toHaveCount(0, { timeout: 3000 });
});

// T28 — Sugerencias: botón Añadir muestra toast de confirmación
test('T28 — sugerencias: añadir muestra toast', async ({ page }) => {
  await enterFestival(page, 'tribeca2026');
  await page.evaluate(() => { switchMainNav('mnav-miplan'); showAgView(); });
  await page.waitForSelector('#ag-view', { state: 'visible', timeout: 8000 });
  const addBtn = page.locator('.suggestion-add').first();
  // Salida MUDA: sin botón de sugerencia no se ejercía nada y daba verde.
  test.skip(!await addBtn.count(), 'sin sugerencia disponible para agregar');
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
  if (!ok) { test.skip(true, 'T50: sin slot compartido en el festival, skip'); return; }
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
  if (!ok) { test.skip(true, 'T51: sin slot compartido, skip'); return; }
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
  if (!ok) { test.skip(true, 'T52: sin film de prueba, skip'); return; }
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
  if (!ok) { test.skip(true, 'T53: sin film de prueba, skip'); return; }
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
    control: document.querySelector('#pel-sheet .blk-add, #pel-sheet .blk-quitar')?.textContent.trim() || '',
    // El texto VISIBLE es corto («Agendar»/«Sacar») porque el corchete ya agrupa;
    // la cuenta vive en el aria-label, que es lo único que oye quien no ve el
    // corchete. Se afirman los dos: si alguien acorta el aria «para unificar», el
    // lector de pantalla pierde el dato y este test lo dice.
    aria: document.querySelector('#pel-sheet .blk-add, #pel-sheet .blk-quitar')?.getAttribute('aria-label') || '',
    corchetes: document.querySelectorAll('#pel-sheet .blq-corchete').length,
    marcadas: document.querySelectorAll('#pel-sheet .pel-sheet-screening.in-plan').length,
    porSesion: document.querySelectorAll('#pel-sheet .pel-sheet-screening .suggestion-add').length,
  }));
  const tocar = async () => {
    await page.evaluate(() => { const b = document.querySelector('#pel-sheet .blk-add, #pel-sheet .blk-quitar'); if (b) b.click(); });
    await page.waitForTimeout(1200);
  };
  await page.evaluate(() => openPelSheet('Taller de Guion'));
  await page.waitForTimeout(1100);

  const a = await leer();
  expect(a.control, 'el botón dice lo mismo que una función suelta').toBe('Agendar');
  expect(a.aria, 'la cuenta no se pierde: viaja en el aria-label').toMatch(/3 sesiones/);
  expect(a.corchetes, 'las 3 sesiones van unidas por un corchete').toBe(1);
  expect(a.porSesion, 'ninguna sesión tiene botón propio').toBe(0);

  await tocar();
  const b = await leer();
  expect(b.enPlan, 'entran las 3 de una').toBe(3);
  expect(b.marcadas, 'el estado «en tu plan» es del bloque: todas las filas marcadas').toBe(3);
  expect(b.control).toMatch(/Sacar/);
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
  const antes = await page.evaluate(() => {
    const b = document.querySelector('#pel-sheet .blk-add, #pel-sheet .blk-quitar');
    return { txt: b?.textContent.trim() || '', aria: b?.getAttribute('aria-label') || '' };
  });
  expect(antes.txt).toBe('Agendar');
  expect(antes.aria).toMatch(/3 sesiones/);

  // con la primera sesión ya pasada: sin control de añadir
  await enterFestival(page, 'leviza2026', '2026-05-15T23:00:00-05:00');
  await page.evaluate(() => openPelSheet('Taller de Guion'));
  await page.waitForTimeout(1100);
  const despues = await page.evaluate(() => ({
    ctrl: document.querySelector('#pel-sheet .blk-add, #pel-sheet .blk-quitar')?.textContent.trim() || '',
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

// T59 — el copy del bloque: la fila dice cuál es, y el modal qué se va.
// En Mi Plan las sesiones se leían como funciones sueltas del mismo título, y
// sorprendía que quitar una las sacara todas. Además el modal prometía «lo podés
// encontrar de nuevo en Sugerencias», que dejó de ser cierto para un taller: se
// quitaron de ahí justamente para que el bloque no se rompa (T58).
test('T59 — la fila dice «Sesión 1 de N» y el modal avisa que se van todas', async ({ page }) => {
  await enterFestival(page, 'leviza2026', '2026-05-13T09:00:00-05:00');
  await page.evaluate(() => openPelSheet('Taller de Guion'));
  await page.waitForTimeout(1000);
  await page.evaluate(() => { const b = document.querySelector('#pel-sheet .blk-add, #pel-sheet .blk-quitar'); if (b) b.click(); });
  await page.waitForTimeout(1200);
  await page.evaluate(() => { try { closePelSheet(); } catch (e) {} switchMainNav('mnav-miplan'); showAgView(); });
  await page.waitForTimeout(1800);

  const fila = await page.evaluate(() => [...document.querySelectorAll('.saved-sesion')].map(e => e.textContent.trim()));
  expect(fila.length, 'la fila del taller lleva su coordenada').toBeGreaterThan(0);
  expect(fila[0]).toMatch(/Sesión \d de 3/);

  await page.evaluate(() => removeFromAgenda('Taller de Guion'));
  await page.waitForTimeout(800);
  const modal = await page.evaluate(() => {
    const c = document.querySelector('.cm-subject');
    return c ? c.parentElement.textContent.replace(/\s+/g, ' ').trim() : '';
  });
  expect(modal, 'el modal dice la consecuencia real').toMatch(/3 sesiones/);
  expect(modal, 'y ya no promete Sugerencias, donde el taller no aparece').not.toMatch(/Sugerencias/);

  // control: una película normal conserva el copy de siempre
  await page.evaluate(() => { const b = [...document.querySelectorAll('button')].find(x => /cancelar/i.test(x.textContent)); if (b) b.click(); });
  await page.waitForTimeout(400);
  const normal = await page.evaluate(() => {
    const f = FILMS.find(x => !x.info && x.day && x.time && !x.is_recurring);
    state.set('savedAgenda', { schedule: [{ _title: f.title, title: f.title, day: f.day, time: f.time,
      venue: f.venue, duration: f.duration, day_order: f.day_order }] });
    removeFromAgenda(f.title);
    const c = document.querySelector('.cm-subject');
    return c ? c.parentElement.textContent : '';
  });
  expect(normal, 'lo que no es bloque no cambia').toMatch(/Sugerencias/);
});

// T61 — el panel de alternativas respeta la ciudad y las cancelaciones
// Re-corrida del QA de ojos frescos (16 ago 2026): con filtro Bogotá el panel
// ofrecía funciones de otras ciudades (436 de 836) y canceladas por el sismo
// (118) — al agente le ofreció Pereira, ciudad cancelada, y sin decir la ciudad.
// El predicado por función ahora es screeningPlannable (dueño único).
test('T61 — las alternativas son de TU ciudad y ninguna está cancelada', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-16T09:00');
  const caso = await page.evaluate(() => {
    // elegir dinámicamente: una función de Bogotá cuyo tramo ±15 tenga vecinas
    // de OTRA ciudad o canceladas — el caso que el panel filtraba mal
    const toM = t => { const [h, m] = t.split(':'); return +h * 60 + +m; };
    const bog = f => (f.venue || '').includes('Bogotá');
    for (const base of FILMS.filter(f => f.day >= '2026-08-17' && f.time && bog(f) && !f._cancelled)) {
      const vecinasMalas = FILMS.filter(f => f.day === base.day && f.title !== base.title
        && Math.abs(toM(f.time) - toM(base.time)) <= 15 && (!bog(f) || f._cancelled));
      if (vecinasMalas.length) return { t: base.title, d: base.day, h: base.time, malas: vecinasMalas.length };
    }
    return null;
  });
  expect(caso, 'FICDEH tiene el caso (vecinas de otra ciudad o canceladas)').not.toBeNull();

  // ciudad Bogotá + la función en el plan, por los caminos reales
  await page.evaluate((c) => {
    activeVenue = 'city:Bogotá';
    addSuggestion(c.t, c.d, c.h);
  }, caso);
  await page.waitForTimeout(600);
  await page.evaluate(() => document.querySelector('[data-action="closePlanConfirm"]')?.click());
  await page.evaluate((c) => {
    switchMainNav('mnav-miplan'); showAgView();
    activeMiPlanDay = DAY_KEYS.indexOf(c.d); renderAgenda();
  }, caso);
  await page.waitForSelector('.mplan-t1', { timeout: 8000 });
  await page.evaluate(() => document.querySelector('.mplan-t1[data-action="toggleFilmAlternatives"]').click());
  await page.waitForTimeout(600);

  // Se afirma sobre la IDENTIDAD de lo ofrecido (data-attrs → catálogo), no
  // sobre el texto: las filas muestran el `short` de la sede sin la ciudad, y
  // una aserción por texto pasaba en vacío — lo destapó la mutación.
  const ofertas = await page.evaluate(() => {
    const filas = [...document.querySelectorAll('.film-alts [data-action="confirmReplace"]')];
    return filas.map(b => {
      const f = FILMS.find(x => x.title === b.dataset.newtitle && x.day === b.dataset.day && x.time === b.dataset.time
        && (x.venue || '').includes('Bogotá'))
        || FILMS.find(x => x.title === b.dataset.newtitle && x.day === b.dataset.day && x.time === b.dataset.time);
      return { titulo: b.dataset.newtitle, venue: f && f.venue, cancelada: !!(f && f._cancelled) };
    });
  });
  // puede quedar vacío (todo lo cercano era de otra ciudad) — correcto; lo que
  // NO puede pasar es una oferta de otra ciudad o una cancelada
  for (const o of ofertas) {
    expect(o.venue, `«${o.titulo}» es de tu ciudad`).toContain('Bogotá');
    expect(o.cancelada, `«${o.titulo}» no está cancelada`).toBe(false);
  }
});

// T62 — agendar una tripleta ambigua elige la función de TU ciudad
// La otra cabeza del bug de #612: aquel protegía el plan guardado del sync;
// esta protege la PUERTA DE ENTRADA. addSuggestion resolvía (título,día,hora)
// con .find() a secas y un usuario de Bogotá agendaba la de Barranquilla.
test('T62 — con filtro de ciudad, la tripleta ambigua entra por TU sede', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-15T09:00');
  const caso = await page.evaluate(() => {
    // tripleta real con dos sedes, una de ellas de Bogotá
    const k = f => f.title + '|' + f.day + '|' + f.time;
    const por = {};
    FILMS.filter(f => f.day >= '2026-08-16' && f.time && f.venue).forEach(f => (por[k(f)] = por[k(f)] || []).push(f));
    for (const grupo of Object.values(por)) {
      if (grupo.length > 1 && grupo.some(f => f.venue.includes('Bogotá')) && grupo.some(f => !f.venue.includes('Bogotá'))
          && grupo.findIndex(f => f.venue.includes('Bogotá')) > 0) // la de Bogotá NO es la primera: el caso que fallaba
        return { t: grupo[0].title, d: grupo[0].day, h: grupo[0].time };
    }
    return null;
  });
  expect(caso, 'FICDEH tiene una tripleta ambigua con Bogotá en segundo lugar').not.toBeNull();
  await page.evaluate((c) => { activeVenue = 'city:Bogotá'; addSuggestion(c.t, c.d, c.h); }, caso);
  await page.waitForTimeout(600);
  const venue = await page.evaluate((c) =>
    (savedAgenda.schedule.find(e => e._title === c.t) || {}).venue, caso);
  expect(venue, 'entró la función de tu ciudad, no la primera del catálogo').toContain('Bogotá');
});

// ── T116 — «Día libre en tu Plan» no se apelmaza contra el día ni se encaja ───
// Reportado por Juan con captura (26 ago 2026). Dos cosas, las dos medidas:
//   · el rótulo del día quedaba a 0px del aviso — .mplan-list-hdr tenía el
//     padding inferior en 0, así que «Sábado 5» se apoyaba encima de la caja.
//   · el aviso dibujaba SU PROPIA tarjeta (fondo + borde + radio) dentro de
//     .mplan-wrap, que ya es el contenedor con su borde y su radio: dos cajas
//     anidadas diciendo lo mismo. Contra la regla del 29 jul («un aviso es una
//     NOTA al margen, no una tarjeta»), de la que este selector se había
//     escapado porque [aviso-sin-caja] vigila por NOMBRE de selector.
// Queda el filete ámbar: no rodea nada, marca que el aviso es accionable.
test('T116 — el aviso de día libre respira y no se encaja en otra caja', async ({ page }) => {
  await enterFestival(page, 'cinemancia2026', '2026-09-04T10:00');
  const r = await page.evaluate(() => {
    const tap = (a, ds) => { const b = document.createElement('button'); b.setAttribute('data-action', a);
      Object.keys(ds || {}).forEach(k => b.setAttribute('data-' + k, ds[k]));
      document.body.appendChild(b); b.click(); b.remove(); };
    // un plan con algo, para estar en Mi Plan de verdad
    const f = FILMS.filter(x => x.day === '2026-09-04' && x.time)[0];
    tap('addSuggestion', { title: f.title, day: f.day, time: f.time });
    switchMainNav('mnav-miplan'); showAgView();
    // el día que reprodujo la captura: sin funciones en el plan, CON sugerencias
    const sugs = getSuggestions();
    const enPlan = new Set(((savedAgenda || {}).schedule || []).map(s => s.day));
    const i = DAY_KEYS.findIndex(d => !enPlan.has(d) && (sugs[d] || []).length > 0);
    if (i < 0) return { sinCaso: true };
    activeMiPlanDay = i; renderAgenda();

    const cta = document.querySelector('.cta-ctx-c');
    const nombre = document.querySelector('.mplan-day-name');
    if (!cta || !nombre) return { faltaAlgo: !cta ? 'aviso' : 'rótulo' };
    const cs = getComputedStyle(cta);
    // cajas que pintan entre el aviso y la vista
    let cajas = 0, p = cta;
    for (let k = 0; k < 4 && p; k++, p = p.parentElement) {
      const s = getComputedStyle(p);
      if (s.backgroundColor !== 'rgba(0, 0, 0, 0)' || parseFloat(s.borderTopWidth) > 0) cajas++;
    }
    return {
      aire: Math.round(cta.getBoundingClientRect().top - nombre.getBoundingClientRect().bottom),
      fondo: cs.backgroundColor, bordeArriba: cs.borderTopWidth, radio: cs.borderTopLeftRadius,
      fileteIzq: parseFloat(cs.borderLeftWidth), cajas
    };
  });
  expect(r.sinCaso).toBeFalsy();
  expect(r.faltaAlgo).toBeFalsy();
  expect(r.aire).toBeGreaterThanOrEqual(8);        // antes: 0
  expect(r.fondo).toBe('rgba(0, 0, 0, 0)');        // sin fondo propio
  expect(parseFloat(r.bordeArriba)).toBe(0);       // sin recuadro
  expect(parseFloat(r.radio)).toBe(0);             // ni esquinas de tarjeta
  expect(r.fileteIzq).toBeGreaterThan(0);          // pero SÍ la marca de accionable
  expect(r.cajas).toBe(1);                         // solo .mplan-wrap, el contenedor real
});

// ── P0 del recorrido de usuario (30 ago 2026) ────────────────────────────────
// Tres hallazgos que encontraron dos agentes recorriendo la app como personas,
// no como suite. Los tres verificados por mí antes de tocar nada.

// T118 — un toque en una obra no puede arrastrar obras ajenas a Intereses.
// «Más allá» (FICDEH) tiene 6 funciones en 4 ciudades con 4-6 compañeras cada
// una: el código juntaba los _slotKey de TODAS y metía la UNIÓN → 15 obras que
// el usuario nunca eligió, incluidas las de ciudades canceladas por el sismo.
// La regla correcta es la INTERSECCIÓN: las que lo acompañan en TODAS sus
// funciones. Un programa de cortos que gira entero conserva las suyas.
test('T118 — marcar una obra no mete compañeras de otras funciones', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-15T11:00');
  const r = await page.evaluate(() => {
    const tap = (a, ds) => { const b = document.createElement('button'); b.setAttribute('data-action', a);
      Object.keys(ds || {}).forEach(k => b.setAttribute('data-' + k, ds[k]));
      document.body.appendChild(b); b.click(); b.remove(); };
    const obra = FILMS.find(f => /^Más allá/.test(f.title));
    if (!obra) return { falta: true };
    const funcs = FILMS.filter(f => f.title === obra.title).length;
    tap('toggleWL', { title: obra.title });
    const tras = watchlist.size;
    // y la simetría: quitar deshace exactamente lo que agregar hizo
    tap('toggleWL', { title: obra.title });
    return { funciones: funcs, trasAgregar: tras, trasQuitar: watchlist.size };
  });
  expect(r.falta).toBeFalsy();
  expect(r.funciones).toBeGreaterThan(1);   // el caso ambiguo: varias funciones
  expect(r.trasAgregar).toBe(1);            // solo la obra tocada (antes: 16)
  expect(r.trasQuitar).toBe(0);             // agregar y quitar son inversos
});

// T119 — la hoja del tope de prioridades tiene que ABRIR.
// Un `.map(t=>…)` pisaba la t() de i18n y la hoja moría con «t is not a
// function» antes del classList.add('open'): no abría nunca, en ningún
// festival, y el usuario se pasaba del tope porque lo que debía frenarlo se
// caía. Cubierto además por el guardián [shadow-t], restituido con territorio
// completo — se había borrado con una medición equivocada.
test('T119 — pasarse del tope de prioridades abre la hoja, no revienta', async ({ page }) => {
  const errores = [];
  page.on('pageerror', e => errores.push(String(e.message)));
  await enterFestival(page, 'cinemancia2026', '2026-09-05T11:00');
  const r = await page.evaluate(() => {
    const tap = (a, ds) => { const b = document.createElement('button'); b.setAttribute('data-action', a);
      Object.keys(ds || {}).forEach(k => b.setAttribute('data-' + k, ds[k]));
      document.body.appendChild(b); b.click(); b.remove(); };
    const tit = [...new Set(FILMS.filter(f => !f.info && f.day).map(f => f.title))].slice(0, 8);
    tit.forEach(t => tap('toggleWL', { title: t }));
    [...watchlist].slice(0, 8).forEach(t => tap('togglePriority', { title: t }));
    const sh = document.getElementById('prio-limit-sheet');
    return { abrio: !!(sh && sh.classList.contains('open')), prioridades: prioritized.size };
  });
  expect(errores, 'ninguna excepción de página').toEqual([]);
  expect(r.abrio, 'la hoja del tope abre').toBe(true);
});

// T120 — el día preseleccionado de Disponibilidad tiene que VERSE elegido.
// El chip se emitía con clase `selected` y el CSS solo pinta `.on`: se veía
// idéntico a los no elegidos, así que «Confirmar» sin tocar nada bloqueaba
// ese día en silencio.
test('T120 — el día preseleccionado de Disponibilidad se ve elegido', async ({ page }) => {
  await enterFestival(page, 'cinemancia2026', '2026-09-05T11:00');
  const r = await page.evaluate(async () => {
    const tap = (a, ds) => { const b = document.createElement('button'); b.setAttribute('data-action', a);
      Object.keys(ds || {}).forEach(k => b.setAttribute('data-' + k, ds[k]));
      document.body.appendChild(b); b.click(); b.remove(); };
    switchMainNav('mnav-planner'); showAgView();
    tap('openAvSheet', {});
    await new Promise(r => setTimeout(r, 700));
    const chips = [...document.querySelectorAll('.av-day-chip')];
    const marcados = chips.filter(c => c.classList.contains('on'));
    const fondos = [...new Set(chips.map(c => getComputedStyle(c).backgroundColor))];
    return { chips: chips.length, marcados: marcados.length, fondosDistintos: fondos.length,
      claseSelectHuerfana: chips.some(c => c.classList.contains('selected')) };
  });
  if (!r.chips) return;                       // festival sin hoja de disponibilidad
  expect(r.claseSelectHuerfana, 'no queda la clase que el CSS no pinta').toBe(false);
  expect(r.marcados, 'hay un día marcado con la clase que el CSS SÍ pinta').toBeGreaterThan(0);
  expect(r.fondosDistintos, 'el elegido se distingue de los demás').toBeGreaterThan(1);
});

// ── P1 del recorrido: «el Plan miente» (30 ago 2026) ─────────────────────────
// Cuatro hallazgos donde nada se rompe: el Plan AFIRMA cosas que no son ciertas.
// Duele durante el festival, que es cuando el usuario le cree.

// T121 — el hero no puede contarle atrás a una función cancelada.
// Medido por el agente: hero «Próxima función · En 7 h · 17:00» sin marca, y la
// fila de abajo con CANCELADA. Dos vistas de la misma pantalla contradiciéndose.
test('T121 — el hero dice CANCELADA en vez de contar atrás', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-16T10:00');
  const r = await page.evaluate(async () => {
    const tap = (a, ds) => { const b = document.createElement('button'); b.setAttribute('data-action', a);
      Object.keys(ds || {}).forEach(k => b.setAttribute('data-' + k, ds[k]));
      document.body.appendChild(b); b.click(); b.remove(); };
    const f = FILMS.find(x => /verano de Jahia/i.test(x.title) && x.day === '2026-08-16');
    if (!f) return { falta: true };
    tap('addSuggestion', { title: f.title, day: f.day, time: f.time });
    FILMS.forEach(x => { if (x.title === f.title && x.day === '2026-08-16') x._cancelled = true; });
    switchMainNav('mnav-miplan'); showAgView();
    await new Promise(r => setTimeout(r, 1100));
    const hero = document.querySelector('.ctx-header');
    if (!hero) return { sinHero: true };
    const txt = hero.innerText.replace(/\s+/g, ' ').trim();
    return { txt, marca: /cancel/i.test(txt), countdown: /\bEn \d+\s*(min|h)\b/i.test(txt) };
  });
  if (r.falta || r.sinHero) return;
  expect(r.marca, 'el hero dice que está cancelada').toBe(true);
  expect(r.countdown, 'y NO cuenta atrás hacia algo que no va a pasar').toBe(false);
});

// T122 — el resumen del Plan cuenta OBRAS, no funciones.
// `sc.schedule.length` contaba entradas: un taller de 2 sesiones son 2 entradas
// de UNA obra, así que salía «3 obras · 1 quedó fuera» sobre 3 intereses (3+1=4),
// mientras el badge de Intereses —que sí cuenta obras— decía 3.
test('T122 — el resumen del Plan cuenta OBRAS, no funciones', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-15T10:00');
  // El taller entra a Intereses junto a otras dos obras: 3 intereses. Si el
  // resumen contara ENTRADAS, sus dos sesiones lo inflarían a 4.
  const listo = await page.evaluate(() => {
    const tap = (a, ds) => { const b = document.createElement('button'); b.setAttribute('data-action', a);
      Object.keys(ds || {}).forEach(k => b.setAttribute('data-' + k, ds[k]));
      document.body.appendChild(b); b.click(); b.remove(); };
    const T = 'Los frutos que dan vida: Siembra autosostenible casera';
    if (!FILMS.some(f => f.title === T)) return 0;
    tap('toggleWL', { title: T });
    const otras = [...new Set(FILMS.filter(f => f.day && f.time && f.title !== T && !f.is_recurring).map(f => f.title))].slice(0, 2);
    otras.forEach(t => tap('toggleWL', { title: t }));
    return watchlist.size;
  });
  if (!listo) return;
  await goToPlanear(page);
  await esperarCalculo(page);
  const r = await page.evaluate(() => {
    const el = document.querySelector('.dato-resultado');
    // El resumen lee del plan CALCULADO (cachedResult), no del guardado:
    // goToPlanear deja savedAgenda en null y el plan solo se guarda al «usar».
    const _sc = cachedResult && cachedResult.scenarios && cachedResult.scenarios[cachedResult.currentIdx || 0];
    const sch = (_sc && _sc.schedule) || [];
    return {
      resumen: el ? el.innerText.replace(/\s+/g, ' ').trim() : null,
      // lo que el resumen DEBE decir: obras distintas, no entradas
      obras: new Set(sch.map(s => s._title)).size,
      entradas: sch.length
    };
  });
  if (!r.resumen) return;
  const n = parseInt((r.resumen.match(/(\d+)\s*obra/i) || [])[1], 10);
  expect(Number.isFinite(n), 'el resumen declara un número de obras').toBe(true);
  expect(n, 'el resumen cuenta OBRAS distintas, no entradas').toBe(r.obras);
  if (r.entradas > r.obras) {
    expect(n, 'con un taller de 2 sesiones, obras < entradas').toBeLessThan(r.entradas);
  }
});

// T123 — apagar Prensa marca el Plan como desactualizado.
// El interruptor no estaba en planInputSignature, así que el Plan seguía
// agendado en un pase de acreditados que la app ya no listaba: la función
// desaparecía de FILMS y la entrada seguía en savedAgenda, sin aviso.
// Regla de Juan (18 ago): el Plan no se reemplaza solo — se MARCA.
test('T123 — el interruptor de Prensa es un insumo del Plan', async ({ page }) => {
  await enterFestival(page, 'tiff2026', '2026-09-14T11:00');
  // Prensa ON + un pase de acreditados en Intereses, ANTES de calcular
  const hayPrensa = await page.evaluate(() => {
    const tap = (a, ds) => { const b = document.createElement('button'); b.setAttribute('data-action', a);
      Object.keys(ds || {}).forEach(k => b.setAttribute('data-' + k, ds[k]));
      document.body.appendChild(b); b.click(); b.remove(); };
    tap('togglePressScreenings', {});
    const p = FILMS.filter(f => f.audience === 'press' || f.is_press);
    if (!p.length) return false;
    tap('toggleWL', { title: p[0].title });
    return true;
  });
  if (!hayPrensa) return;
  await goToPlanear(page);
  await esperarCalculo(page);
  const r = await page.evaluate(async () => {
    const tap = (a, ds) => { const b = document.createElement('button'); b.setAttribute('data-action', a);
      Object.keys(ds || {}).forEach(k => b.setAttribute('data-' + k, ds[k]));
      document.body.appendChild(b); b.click(); b.remove(); };
    // Se mide la CONSECUENCIA VISIBLE —el aviso de plan desactualizado—, no la
    // función interna: es lo que ve el usuario, y no obliga a exponer nada en el
    // puente de test solo para poder mirarlo.
    const antes = !!document.querySelector('.prio-stale');
    tap('togglePressScreenings', {});          // Prensa OFF, sin tocar nada más
    await new Promise(r => setTimeout(r, 1300));
    return { antes, despues: !!document.querySelector('.prio-stale') };
  });
  expect(r.antes, 'con el plan recién calculado no hay aviso').toBe(false);
  expect(r.despues, 'al apagar Prensa el Plan queda MARCADO como desactualizado').toBe(true);
});

// T124 — una función reprogramada dice A DÓNDE se movió, no solo que se movió.
// La fila mostraba «17:00 · REPROG. · hasta 18:30 · [Actualizar]»: la hora VIEJA,
// y ni el día ni la hora nuevos en ningún lado. «Actualizar» era un botón a
// ciegas — y una función que se va del domingo al miércoles a las 20:00 puede
// ser inaceptable para quien viaja. El propio módulo ya lo tenía escrito cuatro
// líneas más arriba: «una reprogramada MUEVE su día/hora: la verdad es la nueva».
test('T124 — la fila de una reprogramada revela su destino', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-16T10:00');
  const r = await page.evaluate(async () => {
    const tap = (a, ds) => { const b = document.createElement('button'); b.setAttribute('data-action', a);
      Object.keys(ds || {}).forEach(k => b.setAttribute('data-' + k, ds[k]));
      document.body.appendChild(b); b.click(); b.remove(); };
    const f = FILMS.find(x => /verano de Jahia/i.test(x.title) && x.day === '2026-08-16');
    if (!f) return { falta: true };
    tap('addSuggestion', { title: f.title, day: f.day, time: f.time });
    // el loader sella una reprogramación: _movedFrom + día/hora NUEVOS
    FILMS.forEach(x => { if (x.title === f.title && x.day === '2026-08-16') {
      x._movedFrom = { day: x.day, time: x.time }; x.day = '2026-08-19'; x.time = '20:00'; } });
    switchMainNav('mnav-miplan'); showAgView();
    await new Promise(r => setTimeout(r, 1100));
    const badge = [...document.querySelectorAll('.notice-badge')].find(b => /REPROG/i.test(b.textContent));
    if (!badge) return { sinBadge: true };
    const fila = badge.closest('.mplan-row') || badge.parentElement.parentElement;
    const txt = fila.innerText.replace(/\s+/g, ' ').trim();
    return { txt: txt.slice(0, 140), horaNueva: txt.includes('20:00'), diaNuevo: /19/.test(txt) };
  });
  if (r.falta || r.sinBadge) return;
  expect(r.horaNueva, 'la fila dice la hora NUEVA').toBe(true);
  expect(r.diaNuevo, 'y el día nuevo').toBe(true);
});

// T125 — el aviso de conflicto dice la CONSECUENCIA cuando hay un taller.
// Nombraba la única sesión que choca con la franja —correcto— pero al aceptar se
// iban las DOS, porque un bloque entra y sale entero: el usuario decidía sin
// saber qué perdía. Y le decía «Esta función» a un taller.
test('T125 — con un taller, el conflicto anuncia las sesiones que se van', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-15T10:00');
  const r = await page.evaluate(async () => {
    const tap = (a, ds) => { const b = document.createElement('button'); b.setAttribute('data-action', a);
      Object.keys(ds || {}).forEach(k => b.setAttribute('data-' + k, ds[k]));
      document.body.appendChild(b); b.click(); b.remove(); };
    const T = 'Los frutos que dan vida: Siembra autosostenible casera';
    if (!FILMS.some(f => f.title === T)) return { falta: true };
    tap('addRecurringBlock', { title: T });
    const sesiones = FILMS.filter(f => f.title === T && f.is_recurring && f.day && f.time).length;
    switchMainNav('mnav-planner'); showAgView();
    await new Promise(r => setTimeout(r, 600));
    tap('openAvSheet', {}); await new Promise(r => setTimeout(r, 700));
    tap('selectAvDay', { day: '2026-08-17' }); await new Promise(r => setTimeout(r, 400));
    tap('toggleFullDay', { day: '2026-08-17' }); await new Promise(r => setTimeout(r, 700));
    const m = document.getElementById('conflict-modal');
    if (!m) return { sinModal: true };
    const txt = m.innerText.replace(/\s+/g, ' ').trim();
    return { sesiones, txt: txt.slice(0, 170),
      diceCuantas: txt.includes(sesiones + ' sesiones'),
      leDiceFuncion: /esta funci[oó]n/i.test(txt) };
  });
  if (r.falta || r.sinModal) return;
  expect(r.sesiones, 'el taller tiene varias sesiones').toBeGreaterThan(1);
  expect(r.diceCuantas, 'el aviso dice cuántas sesiones se van').toBe(true);
  expect(r.leDiceFuncion, 'y no le dice «función» a un taller').toBe(false);
});

// ── T128 — «Agendar» en NO INCLUIDAS agenda, y no te lleva a otro lado ───────
// Medido por un recorrido de usuario: al tocar «Agendar» de una obra no incluida
// se abría TAMBIÉN su ficha, detrás del modal, y el usuario terminaba ahí en vez
// de en su Plan. El botón declara `data-stop="1"` —«yo me encargo de este
// toque»— pero el listener que abre la ficha corre en CAPTURA, o sea ANTES del
// stopPropagation de la burbuja: la declaración no podía frenarlo. Su única
// defensa era una lista de clases en la que `.excl-include-btn` no estaba.
test('T128 — tocar «Agendar» en NO INCLUIDAS no abre la ficha detrás', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-15T11:00');
  const r = await page.evaluate(async () => {
    // Caso mínimo con una obra REAL: con un título inventado openPelSheet no
    // encuentra film y sale sin abrir nada — el test pasaría con y sin el
    // arreglo. (Pasó: su primera mutación no lo tumbó.)
    const real = FILMS.find(f => f.day && f.time && !f.info);
    if (!real) return { sinObra: true };
    const fila = document.createElement('div');
    fila.className = 'int-item js-open-pel';
    fila.dataset.title = real.title;
    const btn = document.createElement('button');
    btn.className = 'excl-include-btn';
    btn.dataset.stop = '1';
    btn.textContent = 'Agendar';
    fila.appendChild(btn);
    document.body.appendChild(fila);
    const abiertoAntes = !!document.querySelector('#pel-sheet.open');
    btn.click();
    await new Promise(r => setTimeout(r, 700));
    const abiertoDespues = !!document.querySelector('#pel-sheet.open');
    fila.remove();
    const sh = document.querySelector('#pel-sheet.open'); if (sh) sh.classList.remove('open');
    return { abiertoAntes, abiertoDespues };
  });
  if (r.sinObra) return;
  expect(r.abiertoAntes, 'no había ficha abierta').toBe(false);
  expect(r.abiertoDespues, 'un control con data-stop no abre la ficha').toBe(false);
});

// ── T129 — Intereses no puede cortar el número que distingue dos programas ───
// Un recorrido de usuario agregó los 6 programas numerados de Cinemancia y
// quedaron TRES PARES de filas visualmente idénticas: `.int-item-title` era
// nowrap + ellipsis y el corte caía justo antes del dígito. Medido entonces y
// ahora: a «Competencia de cortometrajes Programa 2» le faltaban 28 px.
// Es la pantalla donde el usuario revisa lo que eligió antes de armar el Plan.
//
// Se arregla en la LISTA, no en parseProgramTitle: ese parser tiene 46 llamadas
// y extenderlo cambiaría cómo se ven 36 títulos en toda la app — un cambio
// visual que es decisión de Juan, no un arreglo de bug. Acá el nombre pasa a dos
// líneas y cabe entero. (La estructura nombre+sufijo queda puesta: si algún día
// el parser separa el número, el sufijo ya está blindado contra el recorte.)
test('T129 — los programas numerados se distinguen entre sí en Intereses', async ({ page }) => {
  await enterFestival(page, 'cinemancia2026', '2026-09-05T11:00');
  const r = await page.evaluate(async () => {
    const tap = (a, ds) => { const b = document.createElement('button'); b.setAttribute('data-action', a);
      Object.keys(ds || {}).forEach(k => b.setAttribute('data-' + k, ds[k]));
      document.body.appendChild(b); b.click(); b.remove(); };
    const nums = [...new Set(FILMS.filter(f => /Programa \d/i.test(f.title)).map(f => f.title))].slice(0, 6);
    if (nums.length < 2) return { sinCaso: true };
    nums.forEach(t => tap('toggleWL', { title: t }));
    switchMainNav('mnav-seleccion');
    if (typeof showAgView === 'function') showAgView();
    await new Promise(r => setTimeout(r, 1400));
    const filas = [...document.querySelectorAll('.int-item-name')]
      .filter(e => /Programa \d/i.test(e.innerText));
    return {
      candidatos: nums.length,
      filas: filas.length,
      // ANCHO, no alto: un recorte con ellipsis desborda en HORIZONTAL. Medir
      // scrollHeight no lo ve —y con nowrap tampoco lo ve innerText, que devuelve
      // el texto completo aunque en pantalla esté cortado—. La primera versión de
      // este test usaba las dos medidas ciegas y pasó su mutación.
      desbordanEnAncho: filas.filter(e => e.scrollWidth > e.clientWidth + 1).length,
      desbordanEnAlto: filas.filter(e => e.scrollHeight > e.clientHeight + 1).length
    };
  });
  if (r.sinCaso) return;
  expect(r.filas, 'las filas están en pantalla').toBeGreaterThan(1);
  expect(r.desbordanEnAncho, 'ningún título se corta a lo ancho (ahí muere el número)').toBe(0);
  expect(r.desbordanEnAlto, 'ni se pasa del clamp de dos líneas').toBe(0);
});

// ── T130 — con el Plan desactualizado, la única acción viva parece la acción ──
// Un recorrido de usuario midió «Recalcular» en PLANEAR: fondo gris y texto al
// 60% de blanco — la convención de deshabilitado — con `disabled:false`.
// Bajarlo a secundario cuando ya hay plan es una DECISIÓN escrita («dos primarios
// ámbar no dicen cuál es cuál»; el primario es «Usar este Plan») y se conserva.
// Lo que faltaba: con el plan DESACTUALIZADO, «Usar este Plan» se pinta disabled
// —no se guarda un plan viejo— así que el primario queda apagado Y el único botón
// vivo se veía apagado. La app avisaba «tu Plan está desactualizado» y pintaba el
// remedio como inactivo. La regla no cambia: cambia CUÁL es el primario.
//
// Se mide el GRADIENTE, no backgroundColor: --amber-cta es un linear-gradient, y
// backgroundColor devuelve transparente aunque el botón esté pintado. (Medirlo
// mal me hizo creer que la pantalla no tenía ningún primario.)
test('T130 — el primario de Planear es el botón que se puede tocar', async ({ page }) => {
  await enterFestival(page, 'cinemancia2026', '2026-09-05T11:00');
  const hay = await page.evaluate(() => {
    const tap = (a, ds) => { const b = document.createElement('button'); b.setAttribute('data-action', a);
      Object.keys(ds || {}).forEach(k => b.setAttribute('data-' + k, ds[k]));
      document.body.appendChild(b); b.click(); b.remove(); };
    const t = [...new Set(FILMS.filter(f => f.day && f.time && !f.info).map(f => f.title))].slice(0, 4);
    t.forEach(x => tap('toggleWL', { title: x }));
    return t.length;
  });
  if (!hay) return;
  await goToPlanear(page);
  await esperarCalculo(page);
  const r = await page.evaluate(async () => {
    const AMBAR = /251,\s*191,\s*36/;   // primer stop del gradiente --amber-cta
    const leer = () => {
      const calc = [...document.querySelectorAll('.av-calc-btn')].filter(b => b.offsetParent !== null)[0];
      const save = document.querySelector('.ag-save-btn[data-action="saveCurrentScenario"]');
      const g = e => e ? (getComputedStyle(e).backgroundImage || '') : '';
      return {
        calcEsPrimario: AMBAR.test(g(calc)),
        saveEsPrimario: AMBAR.test(g(save)),
        saveDisabled: save ? save.disabled : null
      };
    };
    const conPlan = leer();
    const tap = (a, ds) => { const b = document.createElement('button'); b.setAttribute('data-action', a);
      Object.keys(ds || {}).forEach(k => b.setAttribute('data-' + k, ds[k]));
      document.body.appendChild(b); b.click(); b.remove(); };
    const extra = [...new Set(FILMS.filter(f => f.day && f.time && !f.info).map(f => f.title))][8];
    if (extra) tap('toggleWL', { title: extra });
    await new Promise(r => setTimeout(r, 1300));
    return { conPlan, stale: leer(), hayAviso: !!document.querySelector('.prio-stale') };
  });
  // con plan válido: el primario es «Usar este Plan», Recalcular baja a secundario
  expect(r.conPlan.saveEsPrimario, 'con plan válido, «Usar este Plan» es el primario').toBe(true);
  expect(r.conPlan.calcEsPrimario, 'y Recalcular NO compite con él').toBe(false);
  // desactualizado: «Usar este Plan» no se puede tocar → el primario es Recalcular
  if (!r.hayAviso) return;
  expect(r.stale.saveDisabled, 'con el plan viejo no se puede guardar').toBe(true);
  expect(r.stale.calcEsPrimario, 'así que Recalcular es el primario').toBe(true);
});

// ── T132 — al final del día, Mi Plan cierra el día ───────────────────────────
// El plan se cumplió y no se marcó nada a mano: la pantalla arrancaba directo
// en «Mi Plan · Día 5 de 8» con las filas atenuadas, sin tarjeta de cierre.
// Causa: dos dueños de «qué se vio» en el mismo camino — la fase resolvía
// todayWatched con effectiveWatched (una función que TERMINÓ se asume vista) y
// la tarjeta recontaba con el set explícito `watched`, que estaba vacío.
// Se mide el DOM pintado, que es donde el usuario ve —o no ve— la tarjeta.
test('T132 — con el plan cumplido, la tarjeta de cierre del día aparece', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-16T22:45:00-05:00');
  const r = await page.evaluate(async () => {
    const w = ms => new Promise(r => setTimeout(r, ms));
    const hoy = FILMS.filter(f => f.day === '2026-08-16' && f.time < '17:00').slice(0, 2);
    commitPlan(() => ({ schedule: hoy.map(f => ({ ...f, _title: f.title })) }));
    await w(400);
    switchMainNav('mnav-miplan'); showAgView();
    await w(1400);
    const ph = typeof _getFestivalPhase === 'function' ? _getFestivalPhase() : null;
    const h = document.querySelector('.ctx-main-title');
    return {
      fase: ph ? ph.phase : '?',
      planeadas: hoy.length,
      marcadasAMano: watched.size,
      hayTarjeta: !!document.querySelector('.ctx-header'),
      titular: h ? h.innerText.replace(/\s+/g, ' ').trim() : null
    };
  });
  expect(r.planeadas, 'el día tenía dos funciones planeadas').toBe(2);
  expect(r.fase, 'y todas terminaron: es el cierre del día').toBe('evening');
  expect(r.marcadasAMano, 'sin marcar ninguna a mano — es el caso del bug').toBe(0);
  expect(r.hayTarjeta, 'la tarjeta de cierre del día aparece igual').toBe(true);
  expect(r.titular, 'y cuenta las dos').toMatch(/^2 /);
});

// ── T132b — un taller cuenta, pero no se le dice obra ────────────────────────
// «actividad» es el paraguas y un taller no es una obra ([vocab]): con un
// evento en la cuenta el titular usa el paraguas, igual que _endedStats.
// La hora va anclada a -05:00: sin zona, `new Date()` la parsea en la del host
// y el runner de CI (UTC) leía las 18:50 de Colombia, con el taller de las
// 17:00 todavía en curso — otra fase, sin tarjeta que medir.
test('T132b — con un taller en el día, el titular usa el paraguas', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-13T23:50:00-05:00');
  const r = await page.evaluate(async () => {
    const w = ms => new Promise(r => setTimeout(r, ms));
    const dia = '2026-08-13';
    const ev = FILMS.find(f => f.type === 'event' && f.day === dia);
    const obra = FILMS.find(f => f.day === dia && f.type !== 'event');
    const sel = [ev, obra].filter(Boolean);
    commitPlan(() => ({ schedule: sel.map(f => ({ ...f, _title: f.title })) }));
    await w(400);
    switchMainNav('mnav-miplan'); showAgView();
    await w(1400);
    const h = document.querySelector('.ctx-main-title');
    return { conEvento: sel.some(f => f.type === 'event'), n: sel.length,
      titular: h ? h.innerText.replace(/\s+/g, ' ').trim() : null };
  });
  if (!r.conEvento) return; // festival sin eventos ese día: nada que afirmar
  expect(r.titular, 'la tarjeta se pintó').not.toBe(null);
  expect(r.titular, 'un taller no se cuenta como obra').not.toMatch(/obras?\b/);
  expect(r.titular, 'se cuenta como actividad').toMatch(/actividades?\b/);
});

// ── T134 — PLANEAR y MI PLAN no se presentan como el mismo lugar ─────────────
// Con la app recién abierta y nada agregado, los pasos 2 y 3 del stepper
// mostraban el MISMO titular («Tu Plan aparece aquí.») y el MISMO icono, con
// CTA en direcciones contrarias. Además la frase era falsa en PLANEAR: ahí el
// Plan se ARMA, aparece en MI PLAN. Se comparan las dos pantallas entre sí
// —titular e icono—, que es la magnitud del hallazgo: no que cada una diga algo
// razonable, sino que no digan lo mismo.
test('T134 — los vacíos de PLANEAR y MI PLAN se distinguen', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-15T09:00:00-05:00');
  const r = await page.evaluate(async () => {
    const w = ms => new Promise(r => setTimeout(r, ms));
    const leer = async nav => {
      switchMainNav(nav);
      try { showAgView(); } catch (e) {}
      await w(1500);
      const es = [...document.querySelectorAll('.empty-state-hero')].filter(e => e.offsetParent !== null)[0];
      if (!es) return null;
      const ic = es.querySelector('.empty-state-icon svg');
      return {
        titulo: (es.querySelector('.empty-state-title') || {}).innerText,
        cta: (es.querySelector('.empty-state-cta,.empty-state-cta-sec') || {}).innerText,
        icono: ic ? [...ic.querySelectorAll('path,circle,rect,line,polyline')]
          .map(e => e.getAttribute('d') || e.tagName).join('~') : null
      };
    };
    return { wl: watchlist.size, planear: await leer('mnav-planner'), miplan: await leer('mnav-miplan') };
  });
  expect(r.wl, 'app sin intereses — es el estado del hallazgo').toBe(0);
  expect(r.planear, 'PLANEAR muestra su vacío').not.toBe(null);
  expect(r.miplan, 'MI PLAN muestra su vacío').not.toBe(null);
  expect(r.planear.cta, 'y los CTA siguen apuntando a pasos distintos').not.toBe(r.miplan.cta);
  expect(r.planear.titulo, 'los titulares no pueden ser el mismo').not.toBe(r.miplan.titulo);
  expect(r.planear.icono, 'ni el icono').not.toBe(r.miplan.icono);
});

// ── T137 — la hora tachada de una función caída se lee ───────────────────────
// La línea de una entrada cancelada lleva TRES cosas: el badge CANCELADA (77px),
// la hora tachada y «Buscar reemplazo» (111px). `.mplan-t2` era flex SIN
// flex-wrap, así que iban a la fuerza en una sola línea de 230px y el que cedía
// era el texto: «hasta 17:05» quedaba en 23px de ancho y 22 de alto — once
// caracteres partidos en dos líneas tachadas, una encima de la otra. Ilegible
// justo cuando el usuario necesita entender qué pasó con su función.
//
// Se mide la CAJA del texto: que no desborde y que ocupe una sola línea. Es la
// magnitud del diagnóstico — el bug era una caja demasiado chica para su
// contenido, no una regla CSS ausente.
test('T137 — «hasta HH:MM» de una función cancelada entra en una línea', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-12T09:00:00-05:00');
  const r = await page.evaluate(async () => {
    const w = ms => new Promise(r => setTimeout(r, ms));
    const tap = a => { const b = document.createElement('button'); b.setAttribute('data-action', a);
      document.body.appendChild(b); b.click(); b.remove(); };
    tap('closeCitySheet');
    await w(500);
    // FICDEH trae cancelaciones REALES (el sismo de agosto: Quibdó, Cali,
    // Pereira, Manizales), así que el estado no se fabrica.
    const canc = FILMS.filter(f => f._cancelled && f.day === '2026-08-12').slice(0, 2);
    if (!canc.length) return { sinCanceladas: true };
    commitPlan(() => ({ schedule: canc.map(f => ({ ...f, _title: f.title })) }));
    await w(500);
    switchMainNav('mnav-miplan'); showAgView();
    await w(1600);
    const span = [...document.querySelectorAll('.mplan-t2 .mp-void-t')]
      .filter(e => e.getBoundingClientRect().width > 0)[0];
    if (!span) return { sinHora: true };
    const b = span.getBoundingClientRect();
    const cs = getComputedStyle(span);
    const titulo = document.querySelector('.mplan-t1');
    // El botón «Buscar reemplazo» es el tercer inquilino de la línea: sin
    // flex-wrap no baja, se sale de su fila por la derecha (medido: 352 contra
    // 323). El nowrap del texto solo NO lo evita — cada declaración hace un
    // trabajo distinto, así que las dos se afirman.
    const fila = span.closest('.mplan-t2');
    const btn = fila && fila.querySelector('.mplan-fix');
    const fb = fila.getBoundingClientRect();
    const bb = btn && btn.getBoundingClientRect();
    return {
      txt: span.innerText.replace(/\s+/g, ' ').trim(),
      ancho: Math.round(b.width), alto: Math.round(b.height),
      fontSize: parseFloat(cs.fontSize),
      desborda: span.scrollWidth > Math.ceil(b.width) + 1 || span.scrollHeight > Math.ceil(b.height) + 1,
      wsTitulo: titulo ? getComputedStyle(titulo).whiteSpace : null,
      hayBoton: !!btn,
      botonSeSale: bb ? Math.round(bb.right) > Math.round(fb.right) + 1 : null
    };
  });
  if (r.sinCanceladas || r.sinHora) return;
  expect(r.txt, 'la fila muestra la hora hasta la que iba').toMatch(/\d{1,2}:\d{2}/);
  expect(r.desborda, 'el texto no se sale de su caja').toBe(false);
  expect(r.alto, 'y entra en UNA línea (dos serían ~2× el tamaño de fuente)')
    .toBeLessThan(r.fontSize * 2);
  // El nowrap va acotado al span: si se filtrara a .mplan-t1, el título de la
  // obra dejaría de envolver y se saldría de la fila.
  expect(r.wsTitulo, 'el título de la obra sigue envolviendo').toBe('normal');
  if (r.hayBoton) {
    expect(r.botonSeSale, '«Buscar reemplazo» baja de línea en vez de salirse de la fila').toBe(false);
  }
});

// ── T138 — el aviso del hueco se apaga cuando el hueco se tapa ───────────────
// Sacás algo del Plan → «¿Querés poner otra cosa ahí?». Lo volvés a poner → el
// aviso SEGUÍA, señalando un hueco que ya no existe. Se iba a los 6 s por un
// setTimeout: un temporizador no es un estado, se apaga por reloj y no porque
// el motivo haya desaparecido.
//
// Ahora el aviso se DERIVA del plan: si lo último que se sacó volvió —lo decide
// sameEntry, dueño único de la identidad de una entrada— no hay hueco del que
// hablar. El test recorre los tres momentos, porque el del medio es el que
// impide «arreglarlo» no mostrando nunca el aviso.
test('T138 — al volver a poner lo que sacaste, el aviso del hueco desaparece', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-15T09:00:00-05:00');
  const r = await page.evaluate(async () => {
    const w = ms => new Promise(r => setTimeout(r, ms));
    const tap = a => { const b = document.createElement('button'); b.setAttribute('data-action', a);
      document.body.appendChild(b); b.click(); b.remove(); };
    tap('closeCitySheet');
    await w(500);
    const hoy = FILMS.filter(f => f.day === '2026-08-15').slice(0, 3);
    if (hoy.length < 3) return { pocasFunciones: true };
    hoy.forEach(f => watchlist.add(f.title));
    commitPlan(() => ({ schedule: hoy.map(f => ({ ...f, _title: f.title })) }));
    await w(400);
    switchMainNav('mnav-miplan'); showAgView();
    await w(1500);
    const aviso = () => !!document.querySelector('.cta-ctx-b');
    const antes = aviso();
    // Sacar por el camino real: el modal pide confirmar.
    removeFromAgenda(hoy[0].title);
    await w(600);
    const conf = [...document.querySelectorAll('button')].find(b => /Sacar/i.test(b.innerText));
    if (conf) conf.click();
    await w(1400);
    const conHueco = aviso();
    // Volver a ponerla por el chokepoint, donde terminan TODOS los caminos que
    // la devuelven (Restaurar en Sugerencias, deshacer, agendar de nuevo).
    commitPlan(a => ({ ...a, schedule: [...a.schedule, { ...hoy[0], _title: hoy[0].title }] }));
    saveSavedAgenda(); renderAgenda();
    await w(1200);
    return { antes, conHueco, tapado: aviso(),
      volvio: (savedAgenda && savedAgenda.schedule || []).some(s => s._title === hoy[0].title) };
  });
  if (r.pocasFunciones) return;
  expect(r.antes, 'sin haber sacado nada no hay aviso de hueco').toBe(false);
  expect(r.conHueco, 'al sacar algo, el aviso aparece — si no, el test no prueba nada').toBe(true);
  expect(r.volvio, 'la entrada volvió al Plan').toBe(true);
  expect(r.tapado, 'y con el hueco tapado el aviso ya no habla de él').toBe(false);
});

// ── T139 — las dos cifras de Planear no se leen como la misma ────────────────
// Planear muestra dos números a ~113 px uno de otro, y usaban la MISMA clave
// «N obras»: arriba lo que vas a planear, abajo lo que entró («5 obras · 5 días
// · 1 quedó fuera»). Con los números iguales se leen como el mismo dato; con
// distintos, como una contradicción. Y el de arriba no tenía rótulo: colgaba de
// «Disponibilidad · Editar», así que se leía como parte de la disponibilidad.
//
// Se comparan los dos TEXTOS entre sí —que es el hallazgo— y no cada uno contra
// una cadena fija: lo que no puede volver a pasar es que empiecen igual.
test('T139 — la cifra de «por planear» no se confunde con la del resultado', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-15T09:00:00-05:00');
  await page.evaluate(async () => {
    const b = document.createElement('button');
    b.setAttribute('data-action', 'closeCitySheet');
    document.body.appendChild(b); b.click(); b.remove();
    FILMS.filter(f => f.day === '2026-08-17').slice(0, 5).forEach(f => watchlist.add(f.title));
    if (typeof saveState === 'function') saveState();
  });
  await goToPlanear(page);
  await esperarCalculo(page);
  await page.waitForTimeout(1200);
  const r = await page.evaluate(() => {
    const txt = el => el ? el.innerText.replace(/\s+/g, ' ').trim() : null;
    const pre = document.querySelector('.pre-resumen .dato-linea');
    const res = document.querySelector('.dato-resultado');
    return { pre: txt(pre), res: txt(res),
      separacion: (pre && res)
        ? Math.round(res.getBoundingClientRect().top - pre.getBoundingClientRect().top) : null };
  });
  if (!r.pre || !r.res) return;            // sin cálculo en pantalla no hay dos cifras
  expect(r.separacion, 'las dos cifras conviven en la misma pantalla').toBeLessThan(400);
  expect(r.pre, 'la de arriba dice de qué conjunto habla').toMatch(/planear|schedule|planejar/i);
  expect(r.pre, 'y no es el mismo texto que la de abajo').not.toBe(r.res);
  // El hallazgo era que ambas ARRANCABAN igual («5 obras…»): comparar los textos
  // completos no alcanza, porque diferían en el sufijo y aun así se confundían.
  const prefijo = s => s.split('·')[0].trim();
  expect(prefijo(r.pre), 'ni empieza igual que ella').not.toBe(prefijo(r.res));
});
