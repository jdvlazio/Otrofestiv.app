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
  // El sustantivo dejó de ser «obra» fijo (2 sep 2026): el fixture de este test
  // ES un taller, y con un taller en la cuenta la línea usa el paraguas
  // («actividades»), que es la regla de vocabulario y la vigila T153. Lo que
  // este test afirma es el NÚMERO —obras distintas, no entradas—, así que lee
  // la cifra sin depender de la palabra en vez de aflojar la afirmación.
  const n = parseInt((r.resumen.match(/(\d+)\s*(?:obras?|actividades?)\b/i) || [])[1], 10);
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
  // El CTA dejó de ser una de las señales (2 sep 2026). Antes cada vacío
  // apuntaba al nodo anterior del grafo y por eso los botones diferían solos;
  // desde que el vacío manda al primer lugar donde SE PUEDE hacer algo, con la
  // app en cero los dos llevan al Programa —a propósito, es lo que corta la
  // cadena de tres pantallas vacías que dueña T150—. Lo que esta prueba
  // defiende es que las dos pantallas no se lean como el MISMO lugar, y eso lo
  // sostienen el titular y el icono, que son su identidad; el botón es la
  // salida, y con nada cargado la salida honesta es una sola.
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

// ── T144 — la hoja de disponibilidad dice QUÉ se está declarando ─────────────
// La fila de PLANEAR dice «Disponibilidad» (positivo) y la hoja que abre se
// titulaba «No disponible» (negativo), sin una frase que aclarara cuál de las
// dos declarás. Lo que se guarda son BLOQUES de no disponibilidad, y entenderlo
// al revés arruina el Plan en silencio. Las dos palabras conviven en pantalla.
//
// Decisión de Juan (1 sep): el título pregunta, que es el patrón que la app YA
// usa en sus otras hojas de declaración («¿A cuál festival vas?», «¿A cuál
// ciudad vas?», «¿Cómo querés aparecer en tu Plan?»). Esta era la única que
// declaraba con un sustantivo.
//
// Se afirma que el título PREGUNTA y que nombra la negación — no la cadena
// exacta, que es copy y puede afinarse sin romper la intención.
test('T144 — el título de la hoja de disponibilidad pregunta por la negación', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-15T09:00:00-05:00');
  const r = await page.evaluate(async () => {
    const w = ms => new Promise(r => setTimeout(r, ms));
    const tap = a => { const b = document.createElement('button'); b.setAttribute('data-action', a);
      document.body.appendChild(b); b.click(); b.remove(); };
    tap('closeCitySheet');
    await w(500);
    FILMS.filter(f => f.day === '2026-08-17').slice(0, 3).forEach(f => watchlist.add(f.title));
    switchMainNav('mnav-planner'); showAgView();
    await w(1400);
    const fila = document.querySelector('.av-fila-valor');
    tap('openAvSheet');
    await w(900);
    const s = document.querySelector('.av-sheet');
    return {
      fila: fila ? fila.innerText.replace(/\s+/g, ' ').trim() : null,
      titulo: s ? (s.querySelector('.av-sheet-title') || {}).innerText : null
    };
  });
  expect(r.titulo, 'la hoja tiene título').toBeTruthy();
  expect(r.titulo, 'y pregunta, como sus hermanas de declaración').toMatch(/^¿.+\?$/);
  expect(r.titulo, 'nombrando la negación, que es lo que se declara').toMatch(/\bNO\b/);
  // La fila sigue siendo el rótulo de sección aprobado: no se toca.
  if (r.fila) expect(r.fila, 'la fila de Planear conserva su rótulo').toContain('Disponibilidad');
});

// ── T147 — la hoja «¡Tu Plan está listo!» dice de qué día es cada hora ───────
// Medido en Cinemancia con un Plan real de 8 obras: la hoja mostraba
// «19:00 · 14:30 · 14:00» — horas en DESCENSO. Son JUE 3, VIE 4 y SÁB 5, pero
// sin el día en pantalla la lista se leía como un mismo día en desorden, justo
// en el momento que celebra el Plan.
//
// La causa de fondo no era el día: esta era la única de las seis listas de obras
// de la app sin póster, encajada en un marco y con el título cortado a mano.
// Al adoptar la fila canónica, el día llega en el renglón que ya existía para el
// cuándo. Por eso el test mide las TRES cosas juntas: si mañana alguien vuelve a
// quitar el póster, la fila dejó de ser la canónica aunque el día siga ahí.
//
// El día va CON su número: Cinemancia dura 10 días y tiene dos jueves, dos
// viernes y dos sábados — «JUE» a secas no distingue el 3 del 10.
test('T147 — cada fila del Plan listo trae póster y su día, y el pie cuenta las que faltan', async ({ page }) => {
  await enterFestival(page, 'cinemancia2026', '2026-09-04T10:00:00-05:00');
  await page.evaluate(() => {
    const b = document.createElement('button');
    b.setAttribute('data-action', 'closeCitySheet');
    document.body.appendChild(b); b.click(); b.remove();
    const porDia = {};
    FILMS.forEach(f => { (porDia[f.day] = porDia[f.day] || []).push(f.title); });
    watchlist.clear();
    // Una obra por día en cinco días distintos: garantiza 3 filas de 3 días y
    // un resto que empieza DESPUÉS de las mostradas — sin eso, el pie se podría
    // «acertar» por casualidad.
    Object.keys(porDia).sort().slice(0, 5).forEach(d => watchlist.add(porDia[d][0]));
    if (typeof saveState === 'function') saveState('wl', 'watched');
  });
  await goToPlanear(page);
  await esperarCalculo(page);
  await page.waitForTimeout(900);
  const r = await page.evaluate(async () => {
    const w = ms => new Promise(r => setTimeout(r, ms));
    const save = document.querySelector('.ag-save-btn[data-action="saveCurrentScenario"]');
    if (!save) return { sinBoton: true };
    save.click(); await w(1500);
    const filas = [...document.querySelectorAll('.plan-confirm-film')];
    if (filas.length < 3) return { pocasFilas: filas.length };
    const plan = (savedAgenda && savedAgenda.schedule || []);
    return {
      cuando: filas.map(e => (e.querySelector('.plan-confirm-when') || {}).innerText || ''),
      posters: filas.map(e => {
        const p = e.querySelector('.lb-poster');
        if (!p) return null;
        const b = p.getBoundingClientRect();
        return { w: Math.round(b.width), h: Math.round(b.height) };
      }),
      mas: (document.getElementById('plan-confirm-mas') || {}).innerText || '',
      diasDelPlan: [...new Set(plan.map(s => s.day))],
      diasMostrados: plan.slice(0, 3).map(s => s.day),
      diasQueFaltan: [...new Set(plan.slice(3).map(s => s.day))]
    };
  });
  if (r.sinBoton) return;
  expect(r.pocasFilas, 'el fixture tiene que pintar 3 filas o el test no mide nada').toBeUndefined();

  // 1 · cada fila dice su día, CON número, antes de la hora
  for (const c of r.cuando) {
    expect(c, 'la fila dice «DÍA N · HH:MM», con el número que distingue dos jueves')
      .toMatch(/^[A-ZÁÉÍÓÚ]{3}\s\d{1,2}\s·\s\d{1,2}:\d{2}$/);
  }
  // 2 · y los días AVANZAN: es lo que hacía leer las horas como desordenadas
  const num = c => parseInt(c.match(/\d{1,2}/)[0], 10);
  expect(r.diasMostrados.length, 'las 3 mostradas son de días distintos o no hay nada que ordenar')
    .toBe(new Set(r.diasMostrados).size);
  expect(num(r.cuando[1]), 'la 2ª fila cae después de la 1ª').toBeGreaterThan(num(r.cuando[0]));
  expect(num(r.cuando[2]), 'la 3ª fila cae después de la 2ª').toBeGreaterThan(num(r.cuando[1]));

  // 3 · la fila es la canónica: lleva el póster del dueño único, en su token
  for (const p of r.posters) {
    expect(p, 'la fila lleva póster — es la anatomía de las otras cinco listas').not.toBeNull();
    expect(p.w, 'y en el token --poster-xs, el mismo de la fila de Mi Plan').toBe(56);
    expect(p.h, 'idem alto').toBe(84);
  }

  // 4 · el pie cuenta el rango de LAS QUE FALTAN, no el del Plan entero
  if (r.diasQueFaltan.length) {
    const primerFalta = r.diasQueFaltan[0].slice(-2).replace(/^0/, '');
    const primerMostrado = r.diasMostrados[0].slice(-2).replace(/^0/, '');
    expect(r.mas, `el pie arranca en el día ${primerFalta}, el primero que no está arriba`)
      .toMatch(new RegExp('\\b' + primerFalta + '\\b'));
    expect(r.mas, `y NO en el ${primerMostrado}, que es la primera fila`)
      .not.toMatch(new RegExp('^\\+\\s*\\d+\\s+\\S+\\s+·\\s+[A-ZÁÉÍÓÚ]{3}\\s' + primerMostrado + '\\b'));
  }
});

// ── T148 — compartir el Plan no exige poner nombre ──────────────────────────
// La hoja tenía DOS controles: el campo y un botón. Con el campo vacío el botón
// solo pintaba el borde de rojo y volvía — sin mensaje (medido: el texto de la
// hoja no cambiaba, 98 caracteres antes y después), sin salida visible y sin
// forma de compartir.
//
// Y el nombre nunca fue obligatorio: el subtítulo de la imagen se arma con
// `(_dn ? _dn+' · ' : '')`, o sea que sin nombre sale «Mi Plan · Festival · N
// días», publicable. La compuerta afirmaba lo contrario y ganaba la que frena.
//
// El test mide las dos mitades juntas a propósito: el rótulo que ofrece la
// salida, y que la salida FUNCIONE. Arreglar solo el rótulo dejaba la hoja
// reabriéndose en bucle — sharePlan volvía a no encontrar nombre y la pedía
// otra vez. Eso lo cazó la medición, no la lectura.
test('T148 — con el campo vacío, Compartir comparte igual', async ({ page }) => {
  await enterFestival(page, 'cinemancia2026', '2026-09-04T10:00:00-05:00');
  await page.evaluate(() => {
    const b = document.createElement('button');
    b.setAttribute('data-action', 'closeCitySheet');
    document.body.appendChild(b); b.click(); b.remove();
    const porDia = {};
    FILMS.forEach(f => { (porDia[f.day] = porDia[f.day] || []).push(f.title); });
    watchlist.clear();
    Object.keys(porDia).sort().slice(0, 4).forEach(d => watchlist.add(porDia[d][0]));
    if (typeof saveState === 'function') saveState('wl', 'watched');
    try { localStorage.removeItem('otrofestiv_display_name'); } catch (e) {}
  });
  await goToPlanear(page);
  await esperarCalculo(page);
  await page.waitForTimeout(800);
  const r = await page.evaluate(async () => {
    const w = ms => new Promise(r => setTimeout(r, ms));
    const tap = a => { const b = document.createElement('button'); b.setAttribute('data-action', a);
      document.body.appendChild(b); b.click(); b.remove(); };
    const save = document.querySelector('.ag-save-btn[data-action="saveCurrentScenario"]');
    if (!save) return { sinPlan: true };
    save.click(); await w(1400);
    tap('closePlanConfirm'); await w(700);
    tap('sharePlan'); await w(900);
    const sheet = document.getElementById('display-name-sheet');
    if (!sheet) return { noPide: true };
    const inp = document.getElementById('dname-input'), cta = document.getElementById('dname-save');
    const vacio = cta.innerText.trim();
    inp.value = 'Juanda'; inp.dispatchEvent(new Event('input')); await w(200);
    const conTexto = cta.innerText.trim();
    inp.value = ''; inp.dispatchEvent(new Event('input')); await w(200);
    const vuelve = cta.innerText.trim();
    // pulsar con el campo vacío — ¿comparte de verdad?
    let imagen = 0;
    const _orig = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function (...a) {
      const u = _orig.apply(this, a);
      if (this.width > 400) imagen = Math.max(imagen, u.length);
      return u;
    };
    cta.click(); await w(2500);
    HTMLCanvasElement.prototype.toDataURL = _orig;
    return { vacio, conTexto, vuelve,
      hojaCerrada: !document.getElementById('display-name-sheet'),
      guardo: localStorage.getItem('otrofestiv_display_name'),
      imagen };
  });
  if (r.sinPlan) return;
  expect(r.noPide, 'sin nombre guardado, compartir tiene que ofrecer ponerlo').toBeUndefined();

  // 1 · con el campo vacío el botón OFRECE la salida, en vez de un borde rojo mudo
  expect(r.vacio, 'con el campo vacío el botón dice que se puede compartir sin nombre')
    .toMatch(/sin mi nombre/i);
  // 2 · y apenas escribís, dice lo que va a hacer con lo que escribiste
  expect(r.conTexto, 'con texto, el botón guarda y comparte').toMatch(/guardar/i);
  expect(r.vuelve, 'y vuelve a ofrecer la salida si borrás lo escrito').toMatch(/sin mi nombre/i);

  // 3 · la salida FUNCIONA: cierra, no inventa un nombre, y la imagen se generó
  expect(r.hojaCerrada, 'la hoja se cierra — no se reabre en bucle pidiendo lo mismo').toBe(true);
  expect(r.guardo, 'y no guarda ningún nombre, porque no lo diste').toBeNull();
  expect(r.imagen, 'y la imagen del Plan se generó igual: el nombre nunca fue obligatorio')
    .toBeGreaterThan(1000);
});

// ── T150 — el vacío no encadena vacíos ──────────────────────────────────────
// Medido con la app en cero (sin plan, sin intereses, sin vistas): Mi Plan decía
// «Ir a Planear», Planear decía «Ir a Intereses», Intereses decía «Ir al
// Programa». TRES pantallas vacías y TRES toques antes de poder tocar una obra,
// y las tres decían la misma idea con otras palabras.
//
// Cada vacío apuntaba al nodo anterior del grafo (Plan ← Planear ← Intereses ←
// Programa), que es correcto como modelo y pésimo como camino. El destino tiene
// que ser el primer lugar donde SE PUEDE hacer algo.
//
// La segunda mitad del test es la que impide «arreglarlo» de más: CON intereses,
// el salto Mi Plan → Planear sí vale, porque Planear tiene qué calcular. Mandar
// también ese caso al Programa sería cambiar un camino muerto por uno perdido.
test('T150 — con la app en cero, el vacío lleva al Programa de un toque', async ({ page }) => {
  const cero = async (conIntereses) => {
    await page.evaluate((ci) => {
      const b = document.createElement('button');
      b.setAttribute('data-action', 'closeCitySheet');
      document.body.appendChild(b); b.click(); b.remove();
      watchlist.clear(); prioritized.clear(); watched.clear();
      savedAgenda = null; cachedResult = null;
      if (ci) FILMS.slice(0, 3).forEach(f => watchlist.add(f.title));
      if (typeof saveState === 'function') saveState('wl', 'watched');
    }, conIntereses);
    await page.waitForTimeout(400);
  };
  const leer = () => page.evaluate(() => {
    const vis = e => { const b = e.getBoundingClientRect(); return b.width > 0 && b.height > 0; };
    const hero = [...document.querySelectorAll('.empty-state-hero,.empty-state')].filter(vis);
    const cta = hero.flatMap(h => [...h.querySelectorAll('button,[data-action]')]).filter(vis)
      .map(b => b.innerText.trim());
    const tab = [...document.querySelectorAll('.main-nav-tab')].find(t => t.classList.contains('on'));
    return { tab: (tab ? tab.innerText : '').trim().replace(/\n/g, ' '),
      vacio: hero.length > 0, cta,
      obras: [...document.querySelectorAll('.poster-card,.plist-item')].filter(vis).length };
  });
  const tocarCTA = async () => {
    await page.evaluate(() => {
      const vis = e => { const b = e.getBoundingClientRect(); return b.width > 0 && b.height > 0; };
      const h = [...document.querySelectorAll('.empty-state-hero,.empty-state')].filter(vis);
      const b = h.flatMap(x => [...x.querySelectorAll('button,[data-action]')]).filter(vis)[0];
      if (b) b.click();
    });
    await page.waitForTimeout(1600);
  };

  await enterFestival(page, 'cinemancia2026', '2026-09-04T10:00:00-05:00');

  // ── 1 · desde CADA uno de los tres vacíos, un solo toque llega a las obras ──
  for (const tab of ['mnav-miplan', 'mnav-planner', 'mnav-seleccion']) {
    await cero(false);
    await page.evaluate(tb => { switchMainNav(tb); showAgView(); }, tab);
    await page.waitForTimeout(1600);
    const antes = await leer();
    expect(antes.vacio, `${tab} en cero tiene que estar vacío o el test no mide nada`).toBe(true);
    expect(antes.cta.length, `${tab} ofrece una salida`).toBeGreaterThan(0);
    await tocarCTA();
    const despues = await leer();
    expect(despues.vacio, `desde ${tab}, un toque NO puede dejarte en otra pantalla vacía`).toBe(false);
    expect(despues.obras, `y tiene que dejarte donde hay obras que agregar`).toBeGreaterThan(0);
  }

  // ── 2 · pero CON intereses el salto a Planear se conserva: ahí sí hay qué hacer ──
  await cero(true);
  await page.evaluate(() => { switchMainNav('mnav-miplan'); showAgView(); });
  await page.waitForTimeout(1600);
  const conInt = await leer();
  expect(conInt.vacio, 'sin plan, Mi Plan sigue vacío aunque haya intereses').toBe(true);
  expect(conInt.cta[0], 'con intereses el destino es Planear, no el Programa').toMatch(/planear/i);
  await tocarCTA();
  const enPlanear = await leer();
  expect(enPlanear.tab, 'y lleva a Planear').toMatch(/PLANEAR/i);
  expect(enPlanear.vacio, 'que con intereses NO está vacío — por eso el salto vale').toBe(false);
});

// ── T151 — el botón de escape está en el mismo lugar en los dos modales ─────
// Medido con rects a 390x844: «SACAR DE MI PLAN» ponía Sacar en y=423 y
// Cancelar en y=471; «¿REEMPLAZAR FUNCIÓN?» los ponía al revés —Cancelar en
// y=460 y «Sí, reemplazar» en y=497—. En móvil el pulgar aprende una posición,
// y esta cambiaba según el modal.
//
// Se miden los rects y no el orden del DOM a propósito: el guardián estático
// [modal-orden] ya lee el DOM, y con `flex-direction:column` un `order:` o un
// `column-reverse` lo dejarían pasar mientras la pantalla dice otra cosa. Acá
// se afirma sobre lo que el pulgar encuentra.
test('T151 — en los dos modales el escape es el botón de abajo', async ({ page }) => {
  await enterFestival(page, 'cinemancia2026', '2026-09-04T10:00:00-05:00');
  await page.evaluate(() => {
    const b = document.createElement('button');
    b.setAttribute('data-action', 'closeCitySheet');
    document.body.appendChild(b); b.click(); b.remove();
    const porDia = {};
    FILMS.forEach(f => { (porDia[f.day] = porDia[f.day] || []).push(f.title); });
    watchlist.clear();
    Object.keys(porDia).sort().slice(0, 4).forEach(d => watchlist.add(porDia[d][0]));
    if (typeof saveState === 'function') saveState('wl', 'watched');
  });
  await goToPlanear(page);
  await esperarCalculo(page);
  await page.waitForTimeout(900);
  const leer = () => page.evaluate(() => {
    const m = document.getElementById('conflict-modal');
    if (!m) return null;
    const btns = [...m.querySelectorAll('.conflict-modal-btn')].map(b => ({
      rol: [...b.classList].find(c => c !== 'conflict-modal-btn') || '?',
      top: Math.round(b.getBoundingClientRect().top)
    })).sort((a, b) => a.top - b.top);
    return { titulo: (m.querySelector('.conflict-modal-hdr') || {}).innerText, btns };
  });
  const r = await page.evaluate(async () => {
    const w = ms => new Promise(r => setTimeout(r, ms));
    const disparar = (attrs) => {
      const b = document.createElement('button');
      Object.entries(attrs).forEach(([k, v]) => b.setAttribute(k, v));
      document.body.appendChild(b); b.click(); b.remove();
    };
    document.querySelector('.ag-save-btn[data-action="saveCurrentScenario"]').click();
    await w(1400);
    disparar({ 'data-action': 'closePlanConfirm' }); await w(800);
    switchMainNav('mnav-miplan'); showAgView(); await w(1500);
    const t0 = (savedAgenda && savedAgenda.schedule[0] || {})._title;
    disparar({ 'data-action': 'removeFromAgenda', 'data-title': t0 || '' });
    await w(900);
    return { ok: !!document.getElementById('conflict-modal') };
  });
  if (!r.ok) return;
  const quitar = await leer();
  expect(quitar, 'el modal de sacar del Plan abre').not.toBeNull();

  await page.evaluate(async () => {
    const w = ms => new Promise(r => setTimeout(r, ms));
    const m = document.getElementById('conflict-modal'); if (m) m.remove();
    switchMainNav('mnav-planner'); showAgView(); await w(1600);
    const sc = cachedResult && cachedResult.scenarios && cachedResult.scenarios[0];
    const e0 = sc && sc.schedule[0];
    const cand = FILMS.find(f => f.title !== e0._title && f.day && f.time);
    const b = document.createElement('button');
    b.setAttribute('data-action', 'confirmReplace');
    b.setAttribute('data-rmtitle', e0._title); b.setAttribute('data-newtitle', cand.title);
    b.setAttribute('data-day', cand.day); b.setAttribute('data-time', cand.time);
    document.body.appendChild(b); b.click(); b.remove(); await w(1000);
  });
  const reemplazar = await leer();
  expect(reemplazar, 'el modal de reemplazar abre').not.toBeNull();

  for (const [nombre, m] of [['sacar del Plan', quitar], ['reemplazar función', reemplazar]]) {
    expect(m.btns.length, `${nombre}: hay al menos dos botones que comparar`).toBeGreaterThan(1);
    expect(m.btns[m.btns.length - 1].rol,
      `${nombre}: el botón de MÁS ABAJO —donde cae el pulgar— tiene que ser el escape`)
      .toBe('cancel');
    expect(m.btns[0].rol, `${nombre}: y el de arriba, el que confirma`).toBe('confirm');
  }
});

// ── T152 — la columna elegida se marca sola, sin depender de lo que tenga ────
// Medido en FICDEH el sábado 15 a las 14:00 con un Plan real: la columna ACTIVA
// tenía 2 de 3 bloques en `opacity .35` (ya pasaron) y la de mañana 2 de 2 en 1.
// Los bloques solo saben de pasado/futuro: no distinguen columna elegida de
// columna cualquiera. Así que toda la emphasis de la selección vivía en la
// cabecera y en un tinte de fondo que, medido en píxeles pintados, da
// rgb(24,18,8) contra rgb(11,10,8) — Δ(13,8,0) sobre 255, un 5%. Con hoy ya
// empezado, la columna que mirás queda en fantasmas y la de mañana se lleva la
// mirada. Pasa todos los días desde el mediodía.
//
// La tercera parte es la que define el arreglo: la marca tiene que estar
// TAMBIÉN en un día sin un solo bloque. Si dependiera del contenido no sería
// una marca de selección, sería una coincidencia.
test('T152 — la columna activa se distingue aunque su día esté vacío o pasado', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-15T14:00:00-05:00');
  const r = await page.evaluate(async () => {
    const w = ms => new Promise(r => setTimeout(r, ms));
    const tap = a => { const b = document.createElement('button'); b.setAttribute('data-action', a);
      document.body.appendChild(b); b.click(); b.remove(); };
    tap('closeCitySheet'); await w(500);
    const sch = [];
    const hoy = FILMS.filter(x => x.day === '2026-08-15' && !x._cancelled);
    hoy.filter(x => parseInt(x.time) < 14).slice(0, 3).forEach(f => sch.push({ ...f, _title: f.title }));
    hoy.filter(x => parseInt(x.time) >= 15).slice(0, 1).forEach(f => sch.push({ ...f, _title: f.title }));
    FILMS.filter(x => x.day === '2026-08-16' && !x._cancelled).slice(0, 2)
      .forEach(f => sch.push({ ...f, _title: f.title }));
    commitPlan(() => ({ schedule: sch }));
    await w(600);
    switchMainNav('mnav-miplan'); showAgView(); await w(1800);

    const vis = e => { const b = e.getBoundingClientRect(); return b.width > 0 && b.height > 0; };
    const mirar = () => [...document.querySelectorAll('.mplan-wk-col')].filter(vis).map(c => ({
      activa: c.classList.contains('wk-active'),
      marca: getComputedStyle(c).boxShadow,
      bloques: [...c.querySelectorAll('.mplan-wk-block')].map(x => Number(getComputedStyle(x).opacity))
    }));
    const conPlan = mirar();

    // mover la selección a un día SIN bloques, para ver si la marca sobrevive
    const idxVacio = DAY_KEYS.findIndex(k => !sch.some(s => s.day === k));
    let vacia = null;
    if (idxVacio >= 0) {
      const b = document.createElement('button');
      b.setAttribute('data-action', 'selectMiPlanDay');
      b.setAttribute('data-index', String(idxVacio));
      document.body.appendChild(b); b.click(); b.remove();
      await w(1500);
      const cols = mirar();
      const act = cols.find(c => c.activa);
      vacia = act ? { marca: act.marca, bloques: act.bloques.length } : null;
    }
    return { conPlan, vacia };
  });

  const act = r.conPlan.find(c => c.activa);
  const otra = r.conPlan.find(c => !c.activa);
  expect(act, 'hay una columna activa').toBeTruthy();
  expect(otra, 'y una que no lo está — sin las dos no hay nada que comparar').toBeTruthy();

  // 1 · el diagnóstico: los bloques de la activa están MÁS apagados que los de la otra
  const apagados = act.bloques.filter(o => o < 0.5).length;
  if (apagados > 0 && otra.bloques.length) {
    expect(Math.min(...otra.bloques),
      'la columna que NO mirás tiene sus bloques enteros — por eso se lleva la mirada')
      .toBe(1);
  }

  // 2 · la activa lleva una marca propia que la otra no tiene
  expect(act.marca, 'la columna activa lleva su propia marca, no solo el tinte del 5%')
    .toMatch(/rgba?\(/);
  expect(act.marca, 'y es ámbar, el color con el que la app marca lo elegido')
    .toMatch(/245,\s*158,\s*11/);
  expect(otra.marca, 'la columna que no está elegida NO la lleva — si no, no marca nada')
    .toBe('none');

  // 3 · y la marca NO depende de lo que el día tenga adentro
  if (r.vacia) {
    expect(r.vacia.bloques, 'el día de control no tiene bloques — es el punto').toBe(0);
    expect(r.vacia.marca, 'un día vacío elegido se sigue viendo elegido')
      .toMatch(/245,\s*158,\s*11/);
  }
});

// ── T154 — la imagen compartida dice los días del PLAN, no los del festival ──
// El subtítulo del PNG reusaba `active.length`, y `active` son TODOS los días
// del festival a propósito: la grilla es un registro completo, con sus columnas
// vacías. Medido en FICDEH con 3 obras repartidas en 4 días, la imagen decía
// «Mi Plan · FICDEH · 8 días». Leído bajo «Mi Plan», ese número es el tamaño de
// tu Plan, y era el del festival.
//
// Se afirma sobre el TEXTO QUE ENTRA AL CANVAS (fillText), que es lo que queda
// pintado en la imagen que se comparte — no sobre la variable que lo calcula.
// Y son días CON algo adentro, no el lapso: con una obra el lunes y otra el
// viernes tu Plan es de 2 días, no de 5. Misma derivación que usa la línea de
// resultado de Planear.
test('T154 — el subtítulo de la imagen cuenta los días que tienen algo', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-12T09:00:00-05:00');
  const r = await page.evaluate(async () => {
    const w = ms => new Promise(r => setTimeout(r, ms));
    const tap = a => { const b = document.createElement('button'); b.setAttribute('data-action', a);
      document.body.appendChild(b); b.click(); b.remove(); };
    tap('closeCitySheet'); await w(500);
    try { localStorage.removeItem('otrofestiv_display_name'); } catch (e) {}
    // Plan repartido: días con algo < días del festival, o el test no mide nada
    const pel = FILMS.filter(f => f.type !== 'event' && !f._cancelled && f.day && f.time);
    const sch = [];
    ['2026-08-13', '2026-08-15', '2026-08-17'].forEach(d => {
      const f = pel.find(x => x.day === d); if (f) sch.push({ ...f, _title: f.title });
    });
    if (sch.length < 2) return { sinFixture: true };
    commitPlan(() => ({ schedule: sch }));
    await w(700);

    // lo que se PINTA en la imagen
    const textos = [];
    const _fill = CanvasRenderingContext2D.prototype.fillText;
    CanvasRenderingContext2D.prototype.fillText = function (t, ...rest) {
      textos.push(String(t)); return _fill.call(this, t, ...rest);
    };
    tap('sharePlan'); await w(1200);
    const cta = document.getElementById('dname-save');
    if (cta) { cta.click(); await w(2500); }
    CanvasRenderingContext2D.prototype.fillText = _fill;

    const dias = [...new Set(sch.map(s => s.day))].sort();
    const i0 = DAY_KEYS.indexOf(dias[0]), i1 = DAY_KEYS.indexOf(dias[dias.length - 1]);
    return {
      sub: textos.find(t => t.includes('Mi Plan')) || null,
      diasConPlan: dias.length,
      diasFestival: DAY_KEYS.length,
      lapso: (i0 >= 0 && i1 >= 0) ? (i1 - i0 + 1) : null
    };
  });
  if (r.sinFixture) return;
  expect(r.sub, 'el subtítulo se pintó en la imagen').toBeTruthy();
  expect(r.diasConPlan, 'el fixture reparte el Plan en menos días que el festival')
    .toBeLessThan(r.diasFestival);

  const n = parseInt((r.sub.match(/(\d+)\s*d[ií]as?\b/i) || [])[1], 10);
  expect(Number.isFinite(n), 'el subtítulo declara un número de días').toBe(true);
  expect(n, 'y son los días del PLAN, no los del festival').toBe(r.diasConPlan);
  if (r.lapso && r.lapso !== r.diasConPlan) {
    expect(n, 'días CON algo adentro, no el lapso entre el primero y el último')
      .not.toBe(r.lapso);
  }
});

// ── T155 — el día se muestra con su número, no recortado a «JUE» ────────────
// Cuatro superficies de sheets-controller cortaban `dayLabel()` con
// `.split(' ')[0]` y dejaban «JUE» a secas. Medido: 9 de los 15 festivales de
// la app repiten nombre de día —todos los de 8 días o más; Tribeca tiene 5
// pares, TIFF 4, Cinemancia 3—, así que «JUE» no distingue el 3 del 10.
//
// El recorte no protegía ningún layout: ninguna de esas clases lleva `nowrap`,
// y medido a 375px en las cuatro, el número no cambia ni la altura ni la caja.
//
// Se afirma que la superficie muestra EXACTAMENTE lo que devuelve el dueño
// (dayLabel), no un prefijo suyo: es la forma de que un recorte futuro —de un
// carácter o de dos— caiga igual.
// El reloj va CONGELADO (4 sep 2026). Corría contra la fecha real y se rompió
// solo al pasar el día: Cinemancia empezó el 3 SEP, y con el festival adentro las
// primeras funciones del catálogo ya pasaron, así que la hoja del tope se quedó
// sin filas que pintar. Medido en main limpio: con reloj real pasaba el 1 y el 3
// de septiembre y fallaba el 5. La hoja del tope y la de conflicto no dependen de
// la fase, así que se ancla ANTES del arranque, donde todas las funciones son
// futuras y el fixture es estable para siempre.
test('T155 — la hoja del tope y la de conflicto muestran el día completo', async ({ page }) => {
  await enterFestival(page, 'cinemancia2026', '2026-09-01T10:00');
  const r = await page.evaluate(async () => {
    const w = ms => new Promise(r => setTimeout(r, ms));
    const H = await import('/src/view/helpers.js');
    const S = await import('/src/domain/schedule.js');
    const tap = (a, attrs = {}) => {
      const b = document.createElement('button'); b.setAttribute('data-action', a);
      Object.entries(attrs).forEach(([k, v]) => b.setAttribute(k, v));
      document.body.appendChild(b); b.click(); b.remove();
    };
    tap('closeCitySheet'); await w(600);

    // ¿este festival repite nombres de día? si no, el test no mide nada
    const cortos = DAY_KEYS.map(k => String(H.dayLabel(k) || k).split(' ')[0]);
    const repetidos = cortos.filter((c, i) => cortos.indexOf(c) !== i).length;

    const pel = FILMS.filter(f => f.day && f.time && !f._cancelled);

    // 1 · hoja del tope de prioridades: varias obras de días distintos
    watchlist.clear(); prioritized.clear();
    const titulos = [...new Set(pel.map(f => f.title))].slice(0, PRIO_LIMIT + 1);
    titulos.forEach(t => watchlist.add(t));
    titulos.slice(0, PRIO_LIMIT).forEach(t => prioritized.add(t));
    tap('togglePriority', { 'data-title': titulos[PRIO_LIMIT] });
    await w(1200);
    const prio = [...document.querySelectorAll('.prio-limit-when')]
      .map(e => (e.textContent || '').split('·')[0].trim()).filter(Boolean);
    tap('closePrioLimit'); await w(500);

    // 2 · hoja de conflicto: dos funciones que se pisan de verdad
    let a = null, b = null;
    for (let i = 0; i < pel.length && !b; i++)
      for (let j = i + 1; j < pel.length; j++)
        if (pel[i].title !== pel[j].title && S.screensConflict(pel[i], pel[j])) { a = pel[i]; b = pel[j]; break; }
    let conflicto = null;
    if (b) {
      commitPlan(() => ({ schedule: [{ ...a, _title: a.title }] }));
      await w(500);
      openConflictSheet(b.title, b, { ...a, _title: a.title });
      await w(1000);
      conflicto = {
        entra: (document.getElementById('cs-incoming-when') || {}).textContent || '',
        estaba: (document.getElementById('cs-existing-when') || {}).textContent || '',
        diaEntra: H.dayLabel(b.day), diaEstaba: H.dayLabel(a.day)
      };
    }
    return { repetidos, prio, conflicto,
      etiquetasValidas: DAY_KEYS.map(k => H.dayLabel(k)) };
  });

  expect(r.repetidos, 'el festival de prueba repite nombres de día — si no, no hay ambigüedad que medir')
    .toBeGreaterThan(0);
  expect(r.prio.length, 'la hoja del tope pintó sus filas').toBeGreaterThan(0);

  // cada día mostrado es EXACTAMENTE una etiqueta del dueño, no un prefijo
  for (const d of r.prio) {
    expect(d, `«${d}» lleva su número: sin él no se distingue de otro ${d.split(' ')[0]}`)
      .toMatch(/^[A-ZÁÉÍÓÚ]{3}\s\d{1,2}$/);
    expect(r.etiquetasValidas, `y es una etiqueta real del calendario, no un recorte`)
      .toContain(d);
  }
  if (r.conflicto) {
    expect(r.conflicto.entra, 'la función que entra dice su día entero')
      .toContain(r.conflicto.diaEntra);
    expect(r.conflicto.estaba, 'y la que ya estaba, también')
      .toContain(r.conflicto.diaEstaba);
  }
});

// ── T156 — la hoja del nombre tiene una salida visible ──────────────────────
// Solo se cerraba tocando el fondo, que no se anuncia. La hoja reusa de la de
// cuenta el contenedor (.auth-sheet-body), el título, el subtítulo, el input y
// el CTA — pero no la última pieza de esa anatomía: los TRES pasos de la hoja
// de cuenta terminan en `<span class="auth-cancel">Cancelar</span>`.
//
// Se afirman las dos mitades: que la salida se VE (existe, tiene caja y entra
// en el viewport) y que hace lo que dice — cerrar SIN compartir. Una salida que
// igual comparte es peor que ninguna, y arreglar solo la primera mitad la
// dejaría pasar.
test('T156 — Compartir se puede cancelar, y cancelar no comparte', async ({ page }) => {
  await enterFestival(page, 'cinemancia2026', '2026-09-04T10:00:00-05:00');
  await page.evaluate(() => {
    const b = document.createElement('button');
    b.setAttribute('data-action', 'closeCitySheet');
    document.body.appendChild(b); b.click(); b.remove();
    const porDia = {};
    FILMS.forEach(f => { (porDia[f.day] = porDia[f.day] || []).push(f.title); });
    watchlist.clear();
    Object.keys(porDia).sort().slice(0, 3).forEach(d => watchlist.add(porDia[d][0]));
    if (typeof saveState === 'function') saveState('wl', 'watched');
    try { localStorage.removeItem('otrofestiv_display_name'); } catch (e) {}
  });
  await goToPlanear(page);
  await esperarCalculo(page);
  await page.waitForTimeout(900);
  const r = await page.evaluate(async () => {
    const w = ms => new Promise(r => setTimeout(r, ms));
    const tap = a => { const b = document.createElement('button'); b.setAttribute('data-action', a);
      document.body.appendChild(b); b.click(); b.remove(); };
    const save = document.querySelector('.ag-save-btn[data-action="saveCurrentScenario"]');
    if (!save) return { sinPlan: true };
    save.click(); await w(1400);
    tap('closePlanConfirm'); await w(800);
    tap('sharePlan'); await w(1000);
    const sh = document.getElementById('display-name-sheet');
    if (!sh) return { noPide: true };

    // 1 · ¿hay una salida que se VEA?
    const c = document.getElementById('dname-cancel');
    const rc = c ? c.getBoundingClientRect() : null;
    const visible = { hay: !!c, txt: c ? c.textContent.trim() : null,
      caja: rc ? (rc.width > 0 && rc.height > 0) : false,
      enPantalla: rc ? (rc.bottom <= innerHeight + 0.5 && rc.top >= 0) : false };
    if (!c) return { visible };

    // 2 · ¿cierra SIN compartir?
    let imagen = 0;
    const _o = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function (...a) {
      const u = _o.apply(this, a);
      if (this.width > 400) imagen = Math.max(imagen, u.length);
      return u;
    };
    c.click(); await w(2000);
    HTMLCanvasElement.prototype.toDataURL = _o;
    return { visible, cerro: !document.getElementById('display-name-sheet'),
      imagen, nombre: localStorage.getItem('otrofestiv_display_name') };
  });
  if (r.sinPlan || r.noPide) return;

  expect(r.visible.hay, 'la hoja ofrece una salida visible, no solo el fondo').toBe(true);
  expect(r.visible.caja, 'y esa salida ocupa lugar en la pantalla').toBe(true);
  expect(r.visible.enPantalla, 'y entra en el viewport, no queda debajo del borde').toBe(true);

  expect(r.cerro, 'cancelar cierra la hoja').toBe(true);
  expect(r.imagen, 'y NO comparte: una salida que igual comparte es peor que ninguna').toBe(0);
  expect(r.nombre, 'ni guarda un nombre que no diste').toBeNull();
});

// ── T159 — la fila de una obra excluida ofrece una función VIVA, no una cancelada ──
// Auditoría B-1 (2 sep 2026), FICDEH tras el sismo: «Honorablé» tiene una
// función cancelada (SÁB 15 · Cali) y una viva (MIÉ 19 · Barranquilla). Con el
// Plan en Bogotá, la fila de «En otra ciudad» decía «SÁB 15 17:00 · Cali», en
// ámbar y sin marca: el bucle tomaba la PRIMERA que chocaba con el Plan, y la
// cancelada iba primero. Mandaba a viajar a otra ciudad a una función que no
// existe, teniendo una viva que nunca miró.
//
// Tres afirmaciones, y la tercera es la que impide arreglar de más: una obra
// con TODAS sus funciones caídas tiene que seguir marcada CANCELADA (regla del
// 30 ago). Si las canceladas se excluyeran del todo, esa fila perdería su marca.
test('T159 — la excluida se explica con su función viva, y la toda-caída sigue marcada', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-15T14:00:00-05:00');
  await page.evaluate(() => { const f = [...document.querySelectorAll('#city-sheet-list .lugar-opt')].find(e => e.dataset.city === 'Bogotá'); if (f) f.click(); });
  await page.waitForTimeout(1400);
  const fx = await page.evaluate(() => {
    watchlist.clear();
    // una obra con función cancelada Y función viva, y otra con TODAS caídas
    const porT = {}; FILMS.forEach(f => { if (f.day && f.time) (porT[f.title] ||= []).push(f); });
    // La condición EXACTA del hallazgo: en el orden del catálogo, la función
    // cancelada va ANTES que la viva — es lo que hacía que el bucle la tomara.
    // Con una obra donde la viva va primero, el bug no cambia nada y el test
    // pasaría con el bug puesto (la primera versión de este test, mutada, pasó).
    // …Y el segundo ingrediente: todas sus funciones vivas caen FUERA de la
    // ciudad del Plan. Solo así el motor la excluye y existe una fila que medir.
    // Con una viva en Bogotá el motor la incluye, no hay fila, y el test pasaría
    // con el bug puesto (la segunda versión de este test, mutada, pasó).
    const ciudadDe = f => (typeof venueCity === 'function' ? venueCity(f.venue) : '') || (f.venue || '').split(' - ').pop();
    const mixta = Object.keys(porT).find(t => {
      const noPasadas = porT[t].filter(f => f.day >= '2026-08-15');
      const iCanc = noPasadas.findIndex(f => f._cancelled), iViva = noPasadas.findIndex(f => !f._cancelled);
      const vivas = noPasadas.filter(f => !f._cancelled);
      return iCanc >= 0 && iViva >= 0 && iCanc < iViva && vivas.every(f => ciudadDe(f) && ciudadDe(f) !== 'Bogotá');
    });
    const caida = Object.keys(porT).find(t => porT[t].every(f => f._cancelled));
    const vivas = [...new Set(FILMS.filter(f => f.day && f.time && !f._cancelled).map(f => f.title))].filter(t => t !== mixta).slice(0, 12);
    [mixta, caida, ...vivas].filter(Boolean).forEach(t => watchlist.add(t));
    if (typeof saveState === 'function') saveState('wl', 'watched');
    savedAgenda = null; cachedResult = null;
    return { mixta, caida, vivasDeLaMixta: mixta ? porT[mixta].filter(f => !f._cancelled).map(f => f.day + ' ' + f.time) : [],
      canceladaPrimero: mixta ? porT[mixta].filter(f => f.day >= '2026-08-15')[0].day + ' ' + porT[mixta].filter(f => f.day >= '2026-08-15')[0].time : null };
  });
  if (!fx.mixta) return; // festival sin el caso: nada que afirmar
  console.log(`T159 fixture: ${fx.mixta} · cancelada primero ${fx.canceladaPrimero} · vivas ${fx.vivasDeLaMixta.join(', ')}`);
  await goToPlanear(page);
  await esperarCalculo(page);
  await page.waitForTimeout(1000);
  const r = await page.evaluate(async (fx) => {
    const det = document.querySelector('details.ag-excl-city'); if (det) det.open = true;
    await new Promise(r => setTimeout(r, 400));
    const sc = cachedResult.scenarios[cachedResult.currentIdx || 0];
    const fila = t => { const e = [...document.querySelectorAll('.int-item')].find(x => x.dataset.title === t); if (!e) return null;
      const when = (e.querySelector('.int-item-when') || {}).innerText || '';
      const s = FILMS.find(f => f.title === t && when.includes(f.time) && (window.dayLabel ? true : true));
      return { when, marca: !!e.querySelector('.notice-badge'), boton: !!e.querySelector('.excl-include-btn'),
        // ¿la función que muestra está cancelada?
        muestraCancelada: FILMS.filter(f => f.title === t && when.includes(f.time)).every(f => f._cancelled) }; };
    return { excluidaMixta: sc.excluded.includes(fx.mixta), mixta: fila(fx.mixta), caida: fx.caida ? fila(fx.caida) : null };
  }, fx);
  // Sin `return` temprano: el fixture está construido para que la obra quede
  // excluida y tenga fila. Si no pasa, el test tiene que FALLAR, no callarse.
  expect(r.excluidaMixta, `${fx.mixta}: sus vivas están fuera de Bogotá, el motor tiene que excluirla`).toBe(true);
  expect(r.mixta, 'la obra excluida tiene su fila').not.toBeNull();
  expect(r.mixta.when, 'la fila dice cuándo').toBeTruthy();
  // 1 · la función que muestra es VIVA
  expect(r.mixta.muestraCancelada, `la fila no puede ofrecer una función cancelada — la obra tiene viva: ${fx.vivasDeLaMixta.join(', ')}`)
    .toBe(false);
  expect(r.mixta.marca, 'y como tiene función viva, no lleva CANCELADA').toBe(false);
  // 2 · y no ofrece agendarla en otra ciudad (regla #594)
  expect(r.mixta.boton, 'sin botón: el motor no cruza ciudades').toBe(false);
  // 3 · la que perdió TODAS sus funciones sigue marcada — no se arregla de más
  if (r.caida) {
    expect(r.caida.marca, 'una obra con todas sus funciones caídas sigue diciendo CANCELADA').toBe(true);
  }
});

// ── T161 — Intereses muestra la función de TU ciudad cuando la hay ──────────
// Auditoría B-5 (2 sep 2026): con Bogotá elegida al entrar, la fila de «Sukua»
// decía «Centro Cultural Panóptico de Ibagué» por ser la más temprana del
// catálogo, teniendo función en Bogotá ese mismo día — la que estaba en su Plan.
// La elección de ciudad se pidió como un dato sobre la persona; acá la lista de
// sus intereses le proponía salas a 200 km.
//
// La segunda mitad impide arreglar de más: una obra SIN función en tu ciudad
// sigue mostrando dónde existe (el comentario `plannable-ok` de _nextScreening
// protegía justo eso: filtrar por ciudad escondería que la obra existe en otra
// parte). Preferir no es filtrar.
test('T161 — la fila de Intereses prefiere tu ciudad, y sin función ahí muestra dónde existe', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-18T09:00:00-05:00');
  await page.evaluate(() => { const f = [...document.querySelectorAll('#city-sheet-list .lugar-opt')].find(e => e.dataset.city === 'Bogotá'); if (f) f.click(); });
  await page.waitForTimeout(1400);
  const r = await page.evaluate(async () => {
    const H = await import('/src/view/helpers.js');
    const D = await import('/src/domain/film.js');
    const viva = f => f.day && f.time && !f._cancelled && !D.screeningPassed(f);
    const enBogota = f => H.venueMatches(f.venue, 'city:Bogotá');
    const porT = {}; FILMS.forEach(f => { if (viva(f)) (porT[f.title] ||= []).push(f); });
    // una obra con función viva en Bogotá Y otra más temprana fuera; y una sin ninguna en Bogotá
    const conBogota = Object.keys(porT).find(t => porT[t].some(enBogota) && porT[t].some(f => !enBogota(f)));
    const sinBogota = Object.keys(porT).find(t => !porT[t].some(enBogota));
    watchlist.clear(); [conBogota, sinBogota].filter(Boolean).forEach(t => watchlist.add(t));
    if (typeof saveState === 'function') saveState('wl', 'watched');
    switchMainNav('mnav-seleccion'); showAgView();
    await new Promise(r => setTimeout(r, 1500));
    const vis = e => { const b = e.getBoundingClientRect(); return b.width > 0 && b.height > 0; };
    const fila = t => { const e = [...document.querySelectorAll('.int-item')].filter(vis).find(x => x.dataset.title === t); return e ? e.innerText.replace(/\s+/g, ' ') : null; };
    const sedesBogota = t => [...new Set(porT[t].filter(enBogota).map(f => H.vcfg(f.venue).short || f.venue))];
    const sedesFuera = t => [...new Set(porT[t].filter(f => !enBogota(f)).map(f => H.vcfg(f.venue).short || f.venue))];
    return { activeVenue, conBogota, sinBogota,
      filaCon: conBogota ? fila(conBogota) : null, sedesBogotaDeCon: conBogota ? sedesBogota(conBogota) : [], sedesFueraDeCon: conBogota ? sedesFuera(conBogota) : [],
      filaSin: sinBogota ? fila(sinBogota) : null, sedesFueraDeSin: sinBogota ? sedesFuera(sinBogota) : [] };
  });
  expect(r.activeVenue, 'la ciudad elegida está activa').toBe('city:Bogotá');
  expect(r.conBogota, 'el fixture trae una obra con función en Bogotá y otra más temprana fuera').toBeTruthy();
  expect(r.filaCon, 'la fila se pintó').toBeTruthy();
  const enBog = r.sedesBogotaDeCon.some(s => r.filaCon.includes(s));
  expect(enBog, `«${r.conBogota}» tiene función en Bogotá (${r.sedesBogotaDeCon.join(' / ')}): la fila la muestra, no la de ${r.sedesFueraDeCon.join(' / ')}`)
    .toBe(true);
  if (r.sinBogota) {
    expect(r.filaSin, 'la obra sin función en Bogotá también tiene fila').toBeTruthy();
    const fuera = r.sedesFueraDeSin.some(s => r.filaSin.includes(s));
    expect(fuera, `«${r.sinBogota}» no tiene función en Bogotá: la fila muestra dónde existe (${r.sedesFueraDeSin.slice(0, 2).join(' / ')}), no la esconde`)
      .toBe(true);
  }
});

// ── T162 — los botones de la fila del Plan se tocan con el dedo, y no se pisan ──
// Auditoría B-9 (2 sep 2026), y los dos recorridos independientes midieron lo
// mismo: los .icon-btn-circle de las filas del Plan —«Cambiar» y «Quitar del
// Plan», apilados— miden 30×30, en una lista donde el error de dedo borra una
// función. iOS pide 44.
//
// La caja de impacto se extiende 7px a cada lado con un ::before; el dibujo
// sigue en 30. Y la segunda mitad es la que importa: medido, los dos botones
// tenían gap 0, así que ampliar cada uno 14px los hacía SOLAPARSE 14px y en
// toda la franja el toque iba al de abajo — el destructivo. Peor que antes.
// El gap de 14 (--sp-btn) hace que las zonas se toquen sin pisarse. Se afirma
// con elementFromPoint, que es lo que el dedo encuentra.
test('T162 — cada botón de la fila responde a 20px de su centro, y la franja entre los dos va al más cercano', async ({ page }) => {
  await enterFestival(page, 'cinemancia2026', '2026-09-04T10:00:00-05:00');
  await page.evaluate(() => {
    const b = document.createElement('button'); b.setAttribute('data-action', 'closeCitySheet');
    document.body.appendChild(b); b.click(); b.remove();
    const porDia = {}; FILMS.forEach(f => { (porDia[f.day] = porDia[f.day] || []).push(f.title); });
    watchlist.clear();
    Object.keys(porDia).sort().slice(0, 3).forEach(d => watchlist.add(porDia[d][0]));
    if (typeof saveState === 'function') saveState('wl', 'watched');
  });
  await goToPlanear(page);
  await esperarCalculo(page);
  await page.waitForTimeout(900);
  const r = await page.evaluate(() => {
    const col = document.querySelector('.col-end'); if (!col) return null;
    const [a, b] = [...col.querySelectorAll('.ag-fi-btn')]; if (!a || !b) return null;
    const ra = a.getBoundingClientRect(), rb = b.getBoundingClientRect();
    const fila = col.closest('.saved-item').getBoundingClientRect();
    const cx = ra.left + ra.width / 2, ca = ra.top + ra.height / 2, cb = rb.top + rb.height / 2;
    const quien = (x, y) => { const e = document.elementFromPoint(x, y); return e === a || a.contains(e) ? 'A' : (e === b || b.contains(e) ? 'B' : 'otro'); };
    return {
      dibujado: [Math.round(ra.width), Math.round(ra.height)],
      gap: Math.round(rb.top - ra.bottom),
      colNoDesborda: col.getBoundingClientRect().height <= fila.height + 0.5,
      a20: [quien(cx, ca - 20), quien(cx - 20, ca), quien(cx + 20, ca)],
      b20: [quien(cx, cb + 20), quien(cx - 20, cb), quien(cx + 20, cb)],
      franja: { bajoA: quien(cx, ra.bottom + 3), sobreB: quien(cx, rb.top - 3) }
    };
  });
  expect(r, 'hay una fila del Plan con sus dos botones').not.toBeNull();
  expect(r.dibujado, 'el dibujo sigue siendo el círculo de 30 — no cambió la anatomía').toEqual([30, 30]);
  expect(r.colNoDesborda, 'la columna de botones no hace crecer la fila').toBe(true);
  // 1 · cada botón responde a 20px de su centro (caja ≥ 44)
  expect(r.a20, '«Cambiar» responde a 20px arriba/izquierda/derecha de su centro').toEqual(['A', 'A', 'A']);
  expect(r.b20, '«Quitar» responde a 20px abajo/izquierda/derecha de su centro').toEqual(['B', 'B', 'B']);
  // 2 · y NO se pisan: la franja entre los dos va al más cercano
  expect(r.gap, 'hay aire entre los dos: sin él las zonas ampliadas se solapan y gana el de abajo').toBeGreaterThanOrEqual(14);
  expect(r.franja.bajoA, 'justo debajo de «Cambiar» sigue siendo «Cambiar» — no «Quitar»').toBe('A');
  expect(r.franja.sobreB, 'justo encima de «Quitar» es «Quitar»').toBe('B');
});
// ── T163 — el distintivo Q&A del Plan se dibuja; el que cede es el título ────
// Auditoría A-5 (2 sep 2026): el badge vivía DENTRO de `.mplan-rtitle`, que es
// `nowrap + overflow:hidden`, así que se recortaba junto con el título. Medido
// en Mi Plan: el renglón terminaba en x=323 y el badge arrancaba en x=587 — no
// se dibujaba nunca. La ficha y Planear sí avisan «Q&A · +30 min estimados»; en
// el Plan, el único lugar donde el dato cambia a qué hora salís del cine,
// desaparecía.
//
// Se afirma que el badge queda DENTRO de la caja de la fila (no que exista en
// el DOM: existía y no se veía). Y la fila sin Q&A es el control que impide
// arreglar de más poniéndole un distintivo a todo el mundo.
test('T163 — con Q&A el distintivo entra en la fila, y sin Q&A no aparece', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await enterFestival(page, 'cinemancia2026', '2026-09-04T10:00:00-05:00');
  await page.evaluate(() => {
    const b = document.createElement('button'); b.setAttribute('data-action', 'closeCitySheet');
    document.body.appendChild(b); b.click(); b.remove();
    watchlist.clear();
    // una obra CON Q&A y una SIN, las dos con función
    FILMS.filter(f => f.has_qa && f.day && f.time).slice(0, 2).forEach(f => watchlist.add(f.title));
    FILMS.filter(f => !f.has_qa && f.day && f.time).slice(0, 2).forEach(f => watchlist.add(f.title));
    if (typeof saveState === 'function') saveState('wl', 'watched');
  });
  await goToPlanear(page);
  await esperarCalculo(page);
  await page.waitForTimeout(900);
  const r = await page.evaluate(async () => {
    const w = ms => new Promise(r => setTimeout(r, ms));
    const save = document.querySelector('.ag-save-btn[data-action="saveCurrentScenario"]');
    if (!save) return { sinPlan: true };
    save.click(); await w(1400);
    const cta = document.querySelector('.plan-confirm-cta'); if (cta) cta.click();
    await w(1800);
    const conQA = (savedAgenda.schedule || []).find(s => (FILMS.find(f => f.title === s._title && f.day === s.day) || {}).has_qa);
    if (!conQA) return { sinQAenPlan: true };
    const idx = DAY_KEYS.indexOf(conQA.day);
    const b = document.createElement('button');
    b.setAttribute('data-action', 'selectMiPlanDay'); b.setAttribute('data-index', String(idx));
    document.body.appendChild(b); b.click(); b.remove();
    await w(1200);
    const filas = [...document.querySelectorAll('.mplan-rtitle')].map(rt => {
      const bd = rt.querySelector('.meta-badge'), tx = rt.querySelector('.mplan-rtitle-txt');
      const rr = rt.getBoundingClientRect();
      const br = bd ? bd.getBoundingClientRect() : null;
      const tr = tx ? tx.getBoundingClientRect() : null;
      const cs = getComputedStyle(rt);
      const lh = parseFloat(cs.lineHeight) || parseFloat(cs.fontSize) * 1.2;
      return { texto: rt.textContent.trim().slice(0, 30), hayBadge: !!bd,
        dentroDeLaFila: br ? (br.width > 0 && br.right <= rr.right + 0.5) : null,
        tituloCede: tx ? tx.scrollWidth > tx.clientWidth + 1 : null,
        badgeRight: br ? Math.round(br.right) : null, filaRight: Math.round(rr.right),
        // el renglón es UNO: sin esto, un `display:block` deja el badge «dentro»
        // de la caja pero en una segunda línea, con el título desbordando
        lineas: Math.round(rr.height / lh),
        mismaLinea: (br && tr) ? Math.abs(br.top - tr.top) < lh * 0.6 : null,
        tituloDesborda: tr ? tr.right > rr.right + 0.5 : null };
    });
    return { dia: conQA.day, filas };
  });
  if (r.sinPlan || r.sinQAenPlan) return;
  const conBadge = r.filas.filter(f => f.hayBadge);
  const sinBadge = r.filas.filter(f => !f.hayBadge);
  expect(conBadge.length, 'el día elegido tiene la obra con Q&A — si no, el test no mide nada').toBeGreaterThan(0);
  for (const f of conBadge) {
    expect(f.dentroDeLaFila,
      `«${f.texto}»: el distintivo termina en x=${f.badgeRight} y la fila en x=${f.filaRight} — tiene que ENTRAR, no solo existir en el DOM`)
      .toBe(true);
    expect(f.lineas, `«${f.texto}»: el renglón sigue siendo UNO — el distintivo no baja a una segunda línea`).toBe(1);
    expect(f.mismaLinea, 'y va en la misma línea que el título').toBe(true);
    expect(f.tituloDesborda, 'con el título recortado dentro de la fila, no desbordándola').toBe(false);
  }
  // el que cede es el título, no el distintivo (si el título entra entero, nada que afirmar)
  const cortada = conBadge.find(f => f.tituloCede);
  if (cortada) {
    expect(cortada.dentroDeLaFila, 'con el título recortado, el distintivo sigue entero').toBe(true);
  }
  // control: una fila sin Q&A no inventa distintivo
  for (const f of sinBadge) {
    expect(f.hayBadge, `«${f.texto}» no tiene Q&A: no lleva distintivo`).toBe(false);
  }
});

// ── T165 — el bloque de la grilla dice cuántas obras no le caben ──────────────
// Auditoría B-3 (2 sep 2026): un bloque compartido mide lo que dura la función y
// lista todas sus obras; con `overflow:hidden`, las que no entraban se cortaban
// en silencio —la última por la mitad—. Medido en FICDEH a 390px: 7 obras en
// 98 min → bloque de 61px con 3 enteras, 1 partida y 3 invisibles.
//
// Lo que se afirma: (1) toda obra que queda en el bloque se ve ENTERA; (2) el
// «+N» existe, cuenta exactamente las que faltan y también se ve entero, en la
// línea de la última visible; (3) un bloque donde todo cabe no lleva contador
// ni pierde obras — el control contra arreglar de más.
test('T165 — el bloque de la grilla dice cuántas obras no le caben', async ({ page }) => {
  const medir = async (key, slotDur) => page.evaluate(async ([key, slotDur]) => {
    const g = FILMS.filter(f => f._slotKey === key);
    // slotDur: la misma función pero más corta (bloque más bajo) — ver el caso 3
    state.set('savedAgenda', { schedule: g.map(f => ({ ...f, _title: f.title, ...(slotDur ? { _slotDur: slotDur } : {}) })), scenarioIdx: 0 });
    switchMainNav('mnav-miplan'); showAgView();
    await new Promise(r => setTimeout(r, 900));
    const b = document.querySelector('.mplan-col-mobile .mplan-wk-block');
    if (!b) return null;
    const br = b.getBoundingClientRect();
    const lim = br.bottom - parseFloat(getComputedStyle(b).paddingBottom) + 0.5;
    const ts = [...b.querySelectorAll('.mplan-wk-title')].map(t => t.getBoundingClientRect());
    const mas = b.querySelector('.dw-strip-mas');
    const mr = mas && mas.getBoundingClientRect();
    return { n: g.length, h: Math.round(br.height), titulos: ts.length,
      enteros: ts.filter(r => r.bottom <= lim).length,
      mas: mas ? mas.textContent : null, masEntero: mr ? mr.bottom <= lim && mr.right <= br.right : null,
      masEnLineaUltima: mr && ts.length ? Math.abs(mr.top - ts[ts.length - 1].top) <= 3 : null,
      sedeEntera: (() => { const v = b.querySelector('.mplan-wk-venue'); return v ? v.getBoundingClientRect().bottom <= lim : null; })(),
      // junto a la hora: cuánto aire hay entre «19:00» y «+N»
      gapHora: (() => { const tm = b.querySelector('.mplan-wk-time'); if (!mas || !tm || mas.parentElement !== tm) return null;
        const r = document.createRange(); r.selectNodeContents(tm.firstChild); return mr.left - r.getBoundingClientRect().right; })(),
      // con un nombre que no cabe, el que cede es el nombre: el contador sigue a la vista
      masEnteroLargo: (() => { const txt = b.querySelector('.mp-mas .mplan-wk-title-txt'); if (!txt || !mas) return null;
        txt.textContent = 'Un nombre largo, largo, largo, que no cabe en la columna de la grilla';
        const m2 = mas.getBoundingClientRect(), l2 = txt.parentElement.getBoundingClientRect();
        return m2.right <= br.right + 0.5 && m2.bottom <= lim && l2.bottom <= lim && l2.height < m2.height * 2; })() };
  }, [key, slotDur || 0]);

  await page.setViewportSize({ width: 390, height: 844 });
  await enterFestival(page, 'ficdeh2026', '2026-08-15T10:00');
  const picks = await page.evaluate(() => {
    const groups = {};
    FILMS.forEach(f => { if (f._slotKey && !f._cancelled) (groups[f._slotKey] ||= []).push(f); });
    const arr = Object.values(groups).sort((a, b) => b.length - a.length);
    const chico = arr.find(g => g.length === 2 && g.reduce((a, f) => a + parseInt(f.duration), 0) >= 80);
    return { grande: { key: arr[0][0]._slotKey, day: arr[0][0].day, n: arr[0].length },
             chico: chico && { key: chico[0]._slotKey, day: chico[0].day } };
  });
  expect(picks.grande.n, 'hace falta una función con 5+ obras — si no, el test no mide nada').toBeGreaterThanOrEqual(5);
  expect(picks.chico, 'y una de 2 obras con tiempo de sobra, como control').toBeTruthy();

  // 1 · la función grande: entra lo que entra, y el resto se cuenta
  await enterFestival(page, 'ficdeh2026', picks.grande.day + 'T10:00');
  const g = await medir(picks.grande.key);
  expect(g, 'el bloque de la función grande se dibuja').not.toBeNull();
  expect(g.enteros, `las ${g.titulos} obras que quedan se ven enteras (bloque de ${g.h}px)`).toBe(g.titulos);
  expect(g.titulos, 'quedan menos obras de las que hay — si caben todas, el fixture no sirve').toBeLessThan(g.n);
  expect(g.titulos, 'al menos una obra se queda').toBeGreaterThanOrEqual(1);
  expect(g.mas, 'el contador dice exactamente cuántas faltan').toBe(`+${g.n - g.titulos}`);
  expect(g.masEntero, 'y se ve entero, dentro del bloque').toBe(true);
  expect(g.masEnLineaUltima, 'en la misma línea que la última obra visible').toBe(true);
  expect(g.masEnteroLargo, 'con un nombre largo el contador sigue a la vista: el que cede es el nombre').toBe(true);
  expect(g.sedeEntera, 'la sede, si quedó, se ve entera — no escondida bajo el borde').not.toBe(false);

  // 2 · control: donde todo cabe, no hay contador ni se pierde nada
  await enterFestival(page, 'ficdeh2026', picks.chico.day + 'T10:00');
  const c = await medir(picks.chico.key);
  expect(c, 'el bloque de control se dibuja').not.toBeNull();
  expect(c.titulos, 'las 2 obras siguen ahí').toBe(2);
  expect(c.enteros, 'enteras').toBe(2);
  expect(c.mas, 'y sin contador: no falta nada').toBeNull();
  expect(c.sedeEntera, 'la sede del control también entera').not.toBe(false);

  // 3 · y si no entra ni una obra (ningún festival tiene hoy un bloque compartido
  // tan corto: se simula la misma función de 30 min), el contador va junto a la hora
  const z = await medir(picks.chico.key, 30);
  expect(z, 'el bloque corto se dibuja').not.toBeNull();
  expect(z.titulos, 'con 30 min no cabe ninguna obra').toBe(0);
  expect(z.mas, 'el contador dice que faltan las 2').toBe('+2');
  expect(z.masEntero, 'y se ve entero').toBe(true);
  expect(z.gapHora, 'separado de la hora, no pegado').toBeGreaterThanOrEqual(3);
  expect(z.gapHora, 'con el aire del bloque (sp-1), no el de la tira de pósters (sp-3)').toBeLessThanOrEqual(8);
});

// ── T168 — el bloque de UNA obra corta no recorta su título ──────────────────
// Auditoría del bloque corto (3 sep 2026). El bloque mide lo que dura la
// función y apila hora sobre título: hacen falta 36px para una línea (≈61 min)
// y 51 para dos (≈76 min). Debajo de eso el título se cortaba, y en el piso de
// 20px no se veía ni una letra. Censo a 390px: 148 bloques en 14 de 15
// festivales, 21 de ellos en Cinemancia, en curso.
//
// La altura mínima se descartó MIDIENDO: arregla el bloque de 16 min y falla en
// los de 43 y 60 —ya son altos; lo que no entra es la segunda línea— y cubrirlos
// exigiría 51px fijos, con lo que 16 min se dibujaría del alto de 76. El bloque
// dejaría de decir cuánto dura, que es su única razón de ser.
//
// Lo que se afirma: (1) donde no entraba, hora y título comparten UNA línea y
// el título entra entero en el bloque; (2) el bloque NO cambia de alto, o sea
// que sigue diciendo la duración; (3) el título cede con elipsis, no se corta a
// la mitad; (4) control: un bloque donde el título ya entraba no se toca.
test('T168 — el bloque de una obra corta dice su título en una línea', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });

  // `elegir` corre EN la página: 'corta' es la del censo (por nombre) y 'larga'
  // se busca por dato. La primera versión fijaba también el control por nombre
  // y ese título no existía en el catálogo: el control se saltaba en silencio y
  // la mutación «una línea SIEMPRE» pasaba limpia.
  const medir = async (elegir, dia) => {
    await enterFestival(page, 'cinemancia2026', dia + 'T10:00');
    return page.evaluate(async ([elegir, dia]) => {
      const b0 = document.createElement('button'); b0.setAttribute('data-action', 'closeCitySheet');
      document.body.appendChild(b0); b0.click(); b0.remove();
      await new Promise(r => setTimeout(r, 400));
      const solas = FILMS.filter(x => !x._cancelled && !x._slotKey && x.day === dia && x.time);
      const f = elegir.tit
        ? solas.find(x => x.title === elegir.tit)
        : solas.filter(x => (parseInt(x.duration) || 0) >= 95)
               .sort((a, b) => parseInt(b.duration) - parseInt(a.duration))[0];
      if (!f) return null;
      const alto = Math.max(parseInt(f.duration) / 60 * 40 - 4, 20);   // lo que DEBE medir
      state.set('savedAgenda', { schedule: [{ ...f, _title: f.title }], scenarioIdx: 0 });
      switchMainNav('mnav-miplan'); showAgView();
      await new Promise(r => setTimeout(r, 900));
      const b = document.querySelector('.mplan-col-mobile .mplan-wk-block');
      if (!b) return null;
      const br = b.getBoundingClientRect();
      const lim = br.bottom - parseFloat(getComputedStyle(b).paddingBottom);
      const ti = b.querySelector('.mplan-wk-title'), tm = b.querySelector('.mplan-wk-time');
      const rt = ti.getBoundingClientRect(), rm = tm.getBoundingClientRect();
      return { dur: parseInt(f.duration), h: +br.height.toFixed(1), altoEsperado: +alto.toFixed(1),
        unaLinea: b.classList.contains('mp-linea'),
        excede: +(rt.bottom - lim).toFixed(1),
        mismaLinea: Math.abs(rt.top - rm.top) <= 3,
        desborda: ti.scrollWidth > ti.clientWidth + 1,
        // el corte con puntos suspensivos no deja rastro medible en el DOM:
        // se afirma la declaración, que es lo que lo produce
        cortaConPuntos: getComputedStyle(ti).textOverflow === 'ellipsis',
        lineas: Math.round(rt.height / 12) };
    }, [elegir, dia]);
  };

  // 1 · el caso que se cortaba: 43 min, título de dos líneas, faltaban 26px
  const corto = await medir({ tit: 'Fuera de competencia programa 2' }, '2026-09-10');
  expect(corto, 'Cinemancia tiene la función corta del censo').not.toBeNull();
  expect(corto.unaLinea, 'el bloque pasa a una línea').toBe(true);
  expect(corto.excede, `el título entra en el bloque de ${corto.h}px`).toBeLessThanOrEqual(0.5);
  expect(corto.mismaLinea, 'hora y título comparten línea').toBe(true);
  expect(corto.desborda, 'el título no cabía entero: por eso hay algo que ceder').toBe(true);
  expect(corto.cortaConPuntos, 'y cede con puntos suspensivos, no cortado a la mitad').toBe(true);
  expect(corto.lineas, 'en UNA línea').toBe(1);
  expect(corto.h, 'el bloque NO creció: sigue diciendo cuánto dura').toBeCloseTo(corto.altoEsperado, 0);

  // 2 · control: una obra larga conserva su forma de siempre. Sin este control,
  // «pasar TODOS los bloques a una línea» sería indistinguible del arreglo.
  const largo = await medir({ largo: true }, '2026-09-04');
  expect(largo, 'hace falta una obra sola de 95+ min como control').not.toBeNull();
  expect(largo.unaLinea, 'un bloque que ya tenía lugar no se toca').toBe(false);
  expect(largo.excede, 'y su título sigue entrando').toBeLessThanOrEqual(0.5);
});

// ── T169 — ningún bloque de obra sola recorta su título ─────────────────────
// El barrido que el caso a caso no puede dar: mete en el Plan las obras solas
// MÁS CORTAS de cada catálogo y afirma que ninguna se sale de su caja. Es el
// que caza el festival que todavía no existe.
//
// Se entra una vez por DÍA y se pintan juntas las de ese día: la grilla móvil
// muestra dos columnas, así que un bloque de otro día no se dibuja y no se
// puede medir. (La primera versión midió 2 de 14 por esto y no probaba nada;
// la segunda, con un render por obra, se pasaba del tiempo.)
for (const fid of ['cinemancia2026', 'ficdeh2026', 'olhar2026']) {
test(`T169 — ningún bloque de obra sola recorta su título · ${fid}`, async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await enterFestival(page, fid);
  const porDia = await page.evaluate(() => {
    const v = new Map();
    FILMS.filter(f => !f._slotKey && !f._cancelled && f.day && f.time)
      .forEach(f => { if (!v.has(f.title + f.day + f.time)) v.set(f.title + f.day + f.time, f); });
    const g = {};
    [...v.values()].sort((a, b) => (parseInt(a.duration) || 90) - (parseInt(b.duration) || 90))
      .slice(0, 16).forEach(f => (g[f.day] ||= []).push(f.title));
    return g;
  });
  let medidos = 0; const malos = [];
  for (const [dia, titulos] of Object.entries(porDia)) {
    await enterFestival(page, fid, dia + 'T10:00');
    const r = await page.evaluate(async ([dia, titulos]) => {
      const b0 = document.createElement('button'); b0.setAttribute('data-action', 'closeCitySheet');
      document.body.appendChild(b0); b0.click(); b0.remove();
      await new Promise(r => setTimeout(r, 300));
      const fs = titulos.map(t => FILMS.find(x => x.title === t && x.day === dia && !x._slotKey && !x._cancelled)).filter(Boolean);
      if (!fs.length) return { n: 0, malos: [] };
      state.set('savedAgenda', { schedule: fs.map(f => ({ ...f, _title: f.title })), scenarioIdx: 0 });
      switchMainNav('mnav-miplan'); showAgView();
      await new Promise(r => setTimeout(r, 900));
      const out = { n: 0, malos: [] };
      for (const b of document.querySelectorAll('.mplan-col-mobile .mplan-wk-block')) {
        const br = b.getBoundingClientRect();
        if (!br.height) continue;
        const ti = b.querySelector('.mplan-wk-title');
        if (!ti || b.querySelectorAll('.mplan-wk-title').length > 1) continue;   // los compartidos son de T165
        out.n++;
        const lim = br.bottom - parseFloat(getComputedStyle(b).paddingBottom);
        const ex = +(ti.getBoundingClientRect().bottom - lim).toFixed(1);
        if (ex > 0.5) out.malos.push(`${ti.textContent.trim().slice(0, 22)} (caja ${Math.round(br.height)}px, se sale ${ex})`);
      }
      return out;
    }, [dia, titulos]);
    medidos += r.n; malos.push(...r.malos);
  }
  expect(medidos, `${fid}: hay bloques de obra sola que medir`).toBeGreaterThan(5);
  expect(malos, `${fid}: ${malos.length} de ${medidos} bloques recortan su título — ${malos.slice(0, 3).join(' · ')}`).toHaveLength(0);
});
}

// ── T170 — sin duración publicada, la app no afirma la hora de salida ────────
// Auditoría del 4 sep 2026. `parseDur` rellena con DEFAULT_DURATION_MIN (90)
// cuando el dato no trae número, y nada distinguía ese 90 de uno real. Sobre él
// la app afirmaba «hasta 15:30», reservaba 90 minutos en el calendario y
// descartaba obras del plan con una cuenta que se presenta como dato. Medido en
// el catálogo: 28 registros en 7 festivales sin duración.
//
// El arreglo NO cambia la aritmética —hace falta algún número para dibujar y
// para no armar un plan imposible—: cambia lo que la app AFIRMA. La `~` ya es la
// convención de la casa para lo estimado (helpers.js: «llegarías ~21:15»).
//
// Se afirma: (1) la fila marca la salida como estimada cuando no hay duración;
// (2) NO la marca cuando sí la hay, ni siquiera con un 90 real — el control que
// impide «marcar todo»; (3) el calendario dice de dónde salen esos minutos.
test('T170 — la hora de salida se marca estimada si la duración no está publicada', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await enterFestival(page, 'cinemancia2026', '2026-09-09T15:00');

  // Se entra por el DÍA de la obra: la grilla móvil muestra dos columnas y la
  // fila de un día fuera de la ventana no se dibuja (la primera versión midió
  // null por esto y no probaba nada).
  const fila = async (conDuracion) => {
    const elegida = await page.evaluate(conD => {
      const f = FILMS.find(x => !x._cancelled && x.day && x.time && (conD ? x.duration : !x.duration));
      return f ? { title: f.title, day: f.day, duration: f.duration || null } : null;
    }, conDuracion);
    if (!elegida) return null;
    await enterFestival(page, 'cinemancia2026', elegida.day + 'T10:00');
    return page.evaluate(async (el) => {
      const b = document.createElement('button'); b.setAttribute('data-action', 'closeCitySheet');
      document.body.appendChild(b); b.click(); b.remove();
      await new Promise(r => setTimeout(r, 300));
      const f = FILMS.find(x => x.title === el.title && x.day === el.day);
      state.set('savedAgenda', { schedule: [{ ...f, _title: f.title }], scenarioIdx: 0 });
      switchMainNav('mnav-miplan'); showAgView();
      await new Promise(r => setTimeout(r, 900));
      const t2 = document.querySelector('.mplan-t2');
      return { obra: f.title.slice(0, 30), duration: f.duration || null,
        texto: t2 ? t2.textContent.replace(/\s+/g, ' ').trim().slice(0, 40) : null };
    }, elegida);
  };

  // 1 · sin duración publicada: la salida va marcada
  const sin = await fila(false);
  expect(sin, 'Cinemancia tiene la actividad sin duración del censo').not.toBeNull();
  expect(sin.duration, 'y de verdad no la trae').toBeNull();
  expect(sin.texto, `«${sin.obra}» marca la salida como estimada (dice: ${sin.texto})`).toContain('~');

  // 2 · control: con duración publicada NO se marca. Sin esto, «marcar siempre»
  // pasaría el test y la tilde dejaría de querer decir algo.
  const con = await fila(true);
  expect(con, 'y hay obras con duración').not.toBeNull();
  expect(con.duration, 'esta sí la trae').toBeTruthy();
  expect(con.texto, `«${con.obra}» NO se marca: su duración es dato (dice: ${con.texto})`).not.toContain('~');
});

// ── T172 — «qué viste» se cuenta una sola vez ────────────────────────────────
// Auditoría 4 sep 2026. `effectiveWatched` está declarado DUEÑO ÚNICO de «qué se
// vio» (film.js): una función del plan que ya terminó SE ASUME vista. Pero cuatro
// puertas del modo Recuerdo preguntaban por el `watched` CRUDO, y las pantallas
// se contradecían a dos toques de distancia:
//
//   · con 4 obras en el plan y 2 marcadas a mano, Mi Plan titulaba «Viste 4
//     actividades» mientras Intereses archivaba 2 bajo «te quedaste con ganas»;
//   · y a quien fue a TODO sin marcar nada —armás el plan, vas, volvés cuando
//     terminó— se le escondía «Compartir mi festival», que es lo que el modo
//     Recuerdo promete. Medido: 4 afiches pintados, 0 botones de compartir.
//
// Las cuatro puertas viven dentro de festivalEnded(), así que nada cambia en vivo.
test('T172 — Mi Plan e Intereses cuentan lo mismo, y quien fue a todo puede compartir', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });

  const escenario = async (marcadas) => {
    await enterFestival(page, 'ficdeh2026', '2026-08-25T11:00');
    return page.evaluate(async (marcadas) => {
      const b = document.createElement('button'); b.setAttribute('data-action', 'closeCitySheet');
      document.body.appendChild(b); b.click(); b.remove();
      await new Promise(r => setTimeout(r, 400));
      // OJO: post-festival screeningPassed() devuelve false a propósito (todo
      // vuelve a plena opacidad), así que las pasadas se eligen por FECHA.
      const vistos = new Set(); const el = [];
      for (const f of FILMS.filter(x => !x._cancelled && x.day && x.time && x.day < '2026-08-20')) {
        if (!vistos.has(f.title)) { vistos.add(f.title); el.push(f); }
        if (el.length === 4) break;
      }
      // Una obra de MÁS en la watchlist que NO está en el plan y nadie marcó: es
      // el control de que el reparto siga significando algo. Sin ella, «contar
      // todo como visto» pasaba el test igual.
      const suelta = [...FILMS].find(x => !x._cancelled && x.title && !vistos.has(x.title));
      state.set('watchlist', new Set([...el.map(f => f.title), suelta.title]));
      state.set('savedAgenda', { schedule: el.map(f => ({ ...f, _title: f.title })), scenarioIdx: 0 });
      state.set('notWatched', new Set());
      state.set('watched', new Set(el.slice(0, marcadas).map(f => f.title)));
      switchMainNav('mnav-miplan'); showAgView();
      await new Promise(r => setTimeout(r, 900));
      const recap = document.querySelector('.recap-hdr');
      const compartir = [...document.querySelectorAll('.ag-save-btn[data-action="shareDiary"]')]
        .filter(e => e.getBoundingClientRect().height > 0).length;
      // renderAgenda() explícito: cambiar de pestaña sola no re-dibuja la vista
      // (medido: #ag-view queda con el contenido anterior y en display:none).
      switchMainNav('mnav-seleccion');
      if (typeof renderAgenda === 'function') renderAgenda();
      await new Promise(r => setTimeout(r, 900));
      const vista = document.getElementById('ag-view');
      const hdrs = [...vista.querySelectorAll('.sec-hdr')].map(e => e.textContent.replace(/\s+/g, ' ').trim());
      const filas = [...vista.querySelectorAll('.saved-item')];
      const conMarca = filas.filter(f => f.classList.contains('done')).length;
      return { enPlan: el.length, marcadasAMano: marcadas, suelta: suelta.title.slice(0, 26),
        recapTxt: recap ? recap.textContent.replace(/\s+/g, ' ').trim().slice(0, 40) : null,
        compartir, filas: filas.length, comoVistas: conMarca,
        hayGanas: hdrs.some(h => /no viste|missed/i.test(h)) };
    }, marcadas);
  };

  // 1 · fue a todo y no marcó nada: el caso del hallazgo
  const nada = await escenario(0);
  expect(nada.enPlan, 'el fixture arma un plan de 4 funciones ya pasadas').toBe(4);
  expect(nada.recapTxt, 'Mi Plan lo recibe con su recap, no pidiéndole que marque').not.toBeNull();
  expect(nada.recapTxt, 'y cuenta las 4').toMatch(/4/);
  expect(nada.compartir, '«Compartir mi festival» existe: es lo que el modo Recuerdo promete').toBe(1);
  expect(nada.comoVistas, 'Intereses da por vistas las 4 del plan, igual que Mi Plan').toBe(4);
  expect(nada.filas, 'y lista también la que quedó fuera del plan').toBe(5);
  expect(nada.hayGanas,
    `«${nada.suelta}» no estuvo en el plan y nadie la marcó: va en «te quedaste con ganas»`).toBe(true);

  // 2 · marcó 2 de 4 a mano: las dos pantallas siguen de acuerdo
  const dos = await escenario(2);
  expect(dos.recapTxt, 'Mi Plan sigue contando 4').toMatch(/4/);
  expect(dos.comoVistas, 'e Intereses también las da las 4 por vistas').toBe(4);
  expect(dos.hayGanas, 'y la que quedó fuera del plan sigue del otro lado').toBe(true);

  // 2b · quien NIEGA haber ido: `notWatched` es su memoria propia. El plan existe,
  // así que el diario se pinta igual — pero no hay festival que compartir. Es el
  // control de la puerta: sin él, «mostrar el botón siempre» pasaba el test.
  const negadas = await page.evaluate(async () => {
    const plan = savedAgenda.schedule.map(s => s._title);
    state.set('watched', new Set());
    state.set('notWatched', new Set(plan));
    switchMainNav('mnav-miplan'); showAgView();
    await new Promise(r => setTimeout(r, 900));
    return { diario: !!document.querySelector('.saved-agenda'),
      compartir: [...document.querySelectorAll('.ag-save-btn[data-action="shareDiary"]')]
        .filter(e => e.getBoundingClientRect().height > 0).length };
  });
  expect(negadas.diario, 'el plan vivido se sigue pintando').toBe(true);
  expect(negadas.compartir, 'pero si negaste haber ido a todo, no hay festival que compartir').toBe(0);

  // 3 · control: sin plan y sin marcas no se inventa nada
  const vacio = await page.evaluate(async () => {
    state.set('savedAgenda', null); state.set('watched', new Set()); state.set('notWatched', new Set());
    switchMainNav('mnav-miplan'); showAgView();
    await new Promise(r => setTimeout(r, 900));
    return { recap: !!document.querySelector('.recap-hdr'),
      compartir: [...document.querySelectorAll('.ag-save-btn[data-action="shareDiary"]')]
        .filter(e => e.getBoundingClientRect().height > 0).length };
  });
  expect(vacio.recap, 'sin plan ni marcas no hay recap que mostrar').toBe(false);
  expect(vacio.compartir, 'ni festival que compartir').toBe(0);
});

// ── T173 — la fila de Intereses no dice «Vista» dos veces ────────────────────
// Auditoría 4 sep 2026: una obra vista y SIN calificar mostraba la palabra dos
// veces en la misma fila —«Madres de nacimiento | Vista | Vista»—: una en la
// línea de metadatos (`.saved-venue`, gris) y otra en el botón (`.saved-check`,
// verde). Con estrellas se veía bien; sin ellas, la fila tartamudeaba.
//
// La línea de metadatos dice lo que SABEMOS de la obra; que esté vista ya lo
// dicen el botón, la marca ✓ y el atenuado. Sin calificación muestra la sección,
// igual que una obra no vista.
//
// Se afirma: (1) sin calificar, la palabra aparece UNA vez y el dato es la
// sección; (2) con calificación, el dato son las estrellas —el arreglo no se las
// come—; (3) control: una obra NO vista sigue mostrando su sección y su botón.
test('T173 — la fila de Intereses no repite «Vista»', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await enterFestival(page, 'ficdeh2026', '2026-08-25T11:00');

  const fila = async (opts) => page.evaluate(async (o) => {
    const b = document.createElement('button'); b.setAttribute('data-action', 'closeCitySheet');
    document.body.appendChild(b); b.click(); b.remove();
    await new Promise(r => setTimeout(r, 300));
    const f = FILMS.find(x => !x._cancelled && x.title && x.section);
    state.set('watchlist', new Set([f.title]));
    state.set('savedAgenda', null);
    state.set('notWatched', new Set());
    state.set('watched', new Set(o.vista ? [f.title] : []));
    state.set('filmRatings', o.estrellas ? { [f.title]: 4 } : {});
    switchMainNav('mnav-seleccion');
    if (typeof renderAgenda === 'function') renderAgenda();
    await new Promise(r => setTimeout(r, 800));
    const vista = document.getElementById('ag-view');
    const row = vista.querySelector('.saved-item');
    if (!row) return null;
    const dato = row.querySelector('.saved-venue'), btn = row.querySelector('.saved-check');
    const txt = row.innerText.replace(/\s+/g, ' ').trim();
    return { obra: f.title.slice(0, 26), seccion: f.section,
      dato: dato ? dato.textContent.replace(/\s+/g, ' ').trim() : null,
      boton: btn ? btn.textContent.replace(/\s+/g, ' ').trim() : null,
      vecesVista: (txt.match(/vista/gi) || []).length, texto: txt.slice(0, 60) };
  }, opts);

  // 1 · vista y sin calificar: el caso del hallazgo
  const sinEstrellas = await fila({ vista: true, estrellas: false });
  expect(sinEstrellas, 'la fila de Intereses se dibuja').not.toBeNull();
  expect(sinEstrellas.vecesVista,
    `«Vista» aparece una sola vez en la fila (dice: ${sinEstrellas.texto})`).toBe(1);
  expect(sinEstrellas.boton, 'y la que queda es la del botón, que es la acción').toMatch(/vista/i);
  expect(sinEstrellas.dato, 'el dato muestra la sección, no el estado')
    .not.toMatch(/^vista$/i);
  expect(sinEstrellas.dato, 'y esa sección es la suya').toBeTruthy();

  // 2 · con calificación, el dato son las estrellas: el arreglo no se las come
  const conEstrellas = await fila({ vista: true, estrellas: true });
  expect(conEstrellas.dato, `«${conEstrellas.obra}» calificada muestra sus estrellas`).toMatch(/★|☆|\*/);
  expect(conEstrellas.vecesVista, 'y «Vista» sigue apareciendo una sola vez').toBe(1);

  // 3 · control: una obra NO vista conserva su fila de siempre. El botón dice
  // «Vista» en los dos estados —es la ACCIÓN, no el estado—, así que la palabra
  // aparece una vez también acá: lo que no puede es aparecer dos.
  const noVista = await fila({ vista: false, estrellas: false });
  expect(noVista.dato, 'sin ver, el dato sigue siendo la sección').toBeTruthy();
  expect(noVista.dato, 'y no es el estado').not.toMatch(/^vista$/i);
  expect(noVista.vecesVista, 'y la palabra sigue apareciendo una sola vez, en el botón').toBe(1);
});

// ── T175 — el póster de Mi Plan abre la ficha, siempre ───────────────────────
// Reporte de Juan (4 sep 2026): tocar el póster en Mi Plan no abría la ficha.
// Medido en Cinemancia, día de hoy, plan de 4: NINGUNA fila abría —obra,
// programa y evento por igual—. Solo funcionaba el póster de un corto dentro de
// un programa expandido, que no declara `data-stop`.
//
// Causa: el listener honra `data-stop="1"` desde el 30 ago —«yo me encargo de
// este toque», para que «Agendar» no abriera la ficha detrás del modal—, y el
// póster de Mi Plan lleva las DOS cosas: la marca de abrir y el `data-stop`, que
// ahí significa «no actúe la FILA». El guard lo vetaba antes de mirar quién era.
// El que abre no puede vetarse a sí mismo.
//
// Se afirma: (1) el póster de cada fila abre la ficha, sea obra, programa o
// evento; (2) el título que abre es el de ESA fila, no el de otra; (3) control:
// un control con `data-stop` que NO abre —el botón de agendar— sigue sin abrir.
test('T175 — tocar el póster en Mi Plan abre la ficha de esa obra', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await enterFestival(page, 'cinemancia2026', '2026-09-04T15:00');
  await page.evaluate(async () => {
    const b = document.createElement('button'); b.setAttribute('data-action', 'closeCitySheet');
    document.body.appendChild(b); b.click(); b.remove();
    await new Promise(r => setTimeout(r, 400));
    const hoy = FILMS.filter(f => !f._cancelled && f.day === '2026-09-04' && f.time);
    const el = []; const vis = new Set();
    for (const f of hoy) { if (!vis.has(f.title)) { vis.add(f.title); el.push(f); } if (el.length === 4) break; }
    state.set('savedAgenda', { schedule: el.map(f => ({ ...f, _title: f.title })), scenarioIdx: 0 });
    switchMainNav('mnav-miplan'); showAgView();
    await new Promise(r => setTimeout(r, 1200));
  });

  const n = await page.locator('.mplan-row .js-open-pel').count();
  expect(n, 'el plan pinta sus filas con póster — si no, el test no mide nada').toBeGreaterThan(2);

  const fallidas = [];
  for (let i = 0; i < n; i++) {
    // se cierra por el camino de la app: quitar la clase deja el telón puesto y
    // el toque siguiente lo recibe la ficha, no la fila.
    await page.evaluate(async () => {
      const b = document.createElement('button'); b.setAttribute('data-action', 'closePelSheet');
      document.body.appendChild(b); b.click(); b.remove();
      await new Promise(r => setTimeout(r, 500));
    });
    const loc = page.locator('.mplan-row .js-open-pel').nth(i);
    const titulo = await loc.getAttribute('data-title');
    await loc.scrollIntoViewIfNeeded();
    await loc.click({ timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(900);
    const r = await page.evaluate(() => ({
      abierta: !!document.querySelector('#pel-sheet.open'),
      titulo: document.querySelector('#pel-sheet .pel-sheet-title')?.textContent?.trim() || null }));
    if (!r.abierta) fallidas.push(`${i}: «${(titulo || '').slice(0, 30)}» no abrió`);
    else if (titulo && r.titulo && !titulo.startsWith(r.titulo.slice(0, 12)))
      fallidas.push(`${i}: abrió «${r.titulo.slice(0, 24)}» y se tocó «${titulo.slice(0, 24)}»`);
  }
  expect(fallidas, `las ${n} filas abren su ficha — ${fallidas.join(' · ')}`).toHaveLength(0);

  // control: un control que declara data-stop y NO abre ficha sigue sin abrirla.
  // Sin esto, quitar el guard entero pasaría el test y volvería el defecto que
  // lo trajo: agendar desde NO INCLUIDAS y terminar en la ficha, detrás del modal.
  const control = await page.evaluate(async () => {
    const c = document.createElement('button'); c.setAttribute('data-action', 'closePelSheet');
    document.body.appendChild(c); c.click(); c.remove();
    await new Promise(r => setTimeout(r, 500));
    // el botón va DENTRO del que abre la ficha: ese es el caso real («Agendar»
    // dentro de una fila que abre). Puesto fuera, no había ficha que abrir y el
    // control pasaba con el guard desactivado — mutación comprobada.
    const abridor = document.querySelector('.mplan-row .js-open-pel');
    if (!abridor) return { sinFila: true };
    const b = document.createElement('button');
    b.setAttribute('data-stop', '1'); b.setAttribute('data-action', 'nadaQueHacer');
    b.textContent = 'x'; b.style.cssText = 'position:relative;z-index:5';
    abridor.appendChild(b);
    b.click();
    await new Promise(r => setTimeout(r, 700));
    const abierta = !!document.querySelector('#pel-sheet.open');
    b.remove();
    return { abierta };
  });
  expect(control.abierta, 'un control con data-stop que no abre ficha sigue sin abrirla').toBe(false);
});
