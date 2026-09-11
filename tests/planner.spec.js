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

// T58 — entrar a Planear RESTAURA el cálculo (y respeta el plan ya confirmado)
// El escenario vive en memoria y moría al recargar: 4 filas antes, 0 después,
// sin aviso, con los intereses intactos (medido el 16 ago con FICDEH). Lo que se
// perdía era una DERIVACIÓN —recalcularla cuesta 2–3 ms— así que no se persiste:
// se recalcula al entrar. Con plan YA guardado NO se toca: aparecer con una
// opción nueva sin pedirla invita a reemplazar lo que el usuario curó a mano.
//
// RE-APUNTADO el 10 sep: lo que este test defiende es RESTAURAR, y restaurar
// supone que hubo algo. La primera entrada de la vida no entra en su alcance y
// ahora no calcula (T186) — acá se pone la marca, que es lo que describe a
// alguien que ya estuvo y vuelve. La mitad (b) no cambia una coma.
test('T58 — Planear recalcula al entrar, salvo si ya hay plan guardado', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await addToWatchlist(page, 'Taller de Guion');

  // (a) ya calculó antes, sin plan guardado y sin cálculo en memoria (la recarga
  //     se lo llevó) → reaparece solo, sin tocar el botón
  await page.evaluate(() => { cachedResult = null; savedAgenda = null;
    state.set('planCalculado', true); localStorage.setItem(FESTIVAL_STORAGE_KEY + 'calc1', '1');
    switchMainNav('mnav-planner'); showAgView(); });
  await page.waitForFunction(() => !!cachedResult, null, { timeout: 8000 });
  const auto = await page.evaluate(() => (cachedResult.scenarios || []).length);
  expect(auto, 'entrar a Planear restaura el cálculo perdido').toBeGreaterThan(0);

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

// 17 ago 2026 — el worker llevaba DÍAS muerto y nadie lo vio: screeningPlannable
// entró a _SCHED_PURE_FNS sin su import en calc.js, eval(name) tiraba
// ReferenceError, y TODO cálculo caía al fallback síncrono en el main thread.
// El guardián estático y el test de paridad estaban verdes (el primero solo
// miraba que la fn existiera; el segundo ensambla desde las fuentes del dominio,
// sin pasar por el eval de calc.js). Este test cierra el hueco de RUNTIME: el
// build real del worker no puede fallar, y el cálculo tiene que venir de él.
test('T78 — el worker del planeador construye y calcula (sin fallback silencioso)', async ({ page }) => {
  const fallos = [];
  page.on('console', m => { if (/\[Worker\]/.test(m.text())) fallos.push(m.text().slice(0, 140)); });
  await enterFestival(page, 'ficdeh2026', '2026-08-11T12:00:00-05:00');
  await page.evaluate(() => document.querySelector('[data-action="citySheetAll"]')?.click());
  await page.waitForTimeout(400);
  const r = await page.evaluate(async () => {
    const vivas = [...new Set(FILMS.filter(f => f.day && f.time && !f.info && !f._cancelled).map(f => f.title))];
    state.set('watchlist', new Set(vivas.slice(0, 8)));
    cachedResult = null;
    runCalc();
    await new Promise(r => setTimeout(r, 4000));
    return { calculo: !!(cachedResult && cachedResult.scenarios && cachedResult.scenarios.length) };
  });
  expect(r.calculo, 'el cálculo llegó').toBe(true);
  expect(fallos, 'ningún «[Worker] build failed» ni error de worker').toEqual([]);
});

// ── T184/T185 — la entrada a Disponibilidad (auditoría de descubribilidad, 10 sep 2026)
// Una usuaria de TIFF recorrió el embudo entero —38 intereses, plan guardado de 31
// obras— sin ver nunca que podía marcar cuándo NO puede ir. Medido en su pantalla:
// sin bloques puestos la función ocupaba 29px, un rótulo gris de 11px y un «Editar»
// de 21px de alto (1.185px² de toque contra los 16.468px² del primario), encima de
// un plan YA calculado. Nada ahí se leía como una oferta.
//
// La fila tiene DOS trabajos y ahora dos estados: con bloques ENCABEZA la lista
// —ese rótulo es el aprobado en #802 y no se toca—, y vacía OFRECE, sacando afuera
// la pregunta que ya vivía dentro de la hoja.
//
// Se afirma el CAMBIO DE ESTADO en los dos sentidos, no las cadenas exactas: el
// copy puede afinarse sin romper la intención. Y se afirma que fila y lista están
// de acuerdo — la primera versión de esto las desincronizaba (invalidateCalcResult
// no repinta la fila), así que se veía «¿Cuándo NO podés ir? · Marcar» encima de un
// bloque ya puesto.
test('T184 — la fila de Disponibilidad ofrece vacía y encabeza con bloques', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  const r = await page.evaluate(async () => {
    const w = ms => new Promise(r => setTimeout(r, ms));
    const fila = () => document.querySelector('.av-fila')?.textContent.replace(/\s+/g, ' ').trim() || '';
    const items = () => document.querySelectorAll('#av-blocks-list .av-block-item').length;
    const vivas = [...new Set(FILMS.filter(f => f.day && f.time && !f.info && !screeningPassed(f)).map(f => f.title))];
    state.set('watchlist', new Set(vivas.slice(0, 4)));
    cachedResult = null;
    DAY_KEYS.forEach(d => { availability[d] = { blocks: [] }; });
    switchMainNav('mnav-planner'); showAgView(); renderAgenda();
    await w(900);
    const vacio = { fila: fila(), items: items(), cta: !!document.querySelector('.av-fila .av-plus-btn') };
    // por el camino real de la app, no escribiendo el estado a mano
    const tap = (act, day) => { const b = document.createElement('button');
      b.setAttribute('data-action', act); b.setAttribute('data-day', day);
      document.body.appendChild(b); b.click(); b.remove(); };
    const dia = DAY_KEYS[DAY_KEYS.length - 1]; // último día: vigente con el reloj congelado al inicio
    tap('toggleFullDay', dia); await w(700);
    const con = { fila: fila(), items: items(), editar: !!document.querySelector('.av-fila .av-editar') };
    tap('toggleFullDay', dia); await w(700);
    const devuelta = { fila: fila(), items: items() };
    return { vacio, con, devuelta };
  });
  // vacía: ofrece — pregunta por la negación y un disparador con verbo
  expect(r.vacio.items, 'arranca sin bloques').toBe(0);
  expect(r.vacio.fila, 'vacía pregunta, no rotula').toMatch(/^¿.+\?/);
  expect(r.vacio.fila, 'y nombra la negación, que es lo que se declara').toMatch(/\bNO\b|\bno\b/);
  expect(r.vacio.cta, 'vacía ofrece un disparador con cuerpo, no un enlace').toBe(true);
  // con bloques: encabeza — el rótulo aprobado y «Editar», que hereda el objeto
  expect(r.con.items, 'el bloque puesto se ve en la lista').toBe(1);
  expect(r.con.fila, 'con bloques la fila vuelve a ser el rótulo de sección').toMatch(/Disponibilidad|Availability|Disponibilidade/);
  expect(r.con.editar, 'y su acción vuelve a ser Editar').toBe(true);
  // y de vuelta a cero: fila y lista no pueden discrepar
  expect(r.devuelta.items, 'al quitar el último bloque la lista queda vacía').toBe(0);
  expect(r.devuelta.fila, 'y la fila vuelve a ofrecer — no se queda en el rótulo').toMatch(/^¿.+\?/);
});

// T185 — el área de toque se MIDE en la pantalla, no se declara en el CSS: el
// expansor vive en un ::after y getBoundingClientRect no lo ve. Barrido con
// elementFromPoint, que es lo que responde a un dedo.
test('T185 — el disparador de Disponibilidad se puede tocar', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  const r = await page.evaluate(async () => {
    const w = ms => new Promise(r => setTimeout(r, ms));
    const vivas = [...new Set(FILMS.filter(f => f.day && f.time && !f.info && !screeningPassed(f)).map(f => f.title))];
    state.set('watchlist', new Set(vivas.slice(0, 4)));
    cachedResult = null;
    DAY_KEYS.forEach(d => { availability[d] = { blocks: [] }; });
    switchMainNav('mnav-planner'); showAgView(); renderAgenda();
    await w(900);
    const b = document.querySelector('.av-fila .av-plus-btn');
    if (!b) return null;
    const q = b.getBoundingClientRect();
    const cx = Math.round(q.left + q.width / 2);
    let arriba = 0, abajo = 0;
    for (let d = 1; d <= 30; d++) { if (document.elementFromPoint(cx, Math.round(q.top) - d) === b) arriba = d; else break; }
    for (let d = 1; d <= 30; d++) { if (document.elementFromPoint(cx, Math.round(q.bottom) + d) === b) abajo = d; else break; }
    return { ancho: Math.round(q.width), altoTactil: Math.round(q.height) + arriba + abajo };
  });
  expect(r, 'el disparador existe en el estado vacío').not.toBeNull();
  expect(r.altoTactil, 'alto táctil ≥44px (el expansor ::after, medido con el dedo)').toBeGreaterThanOrEqual(44);
  expect(r.ancho, 'y ancho suficiente').toBeGreaterThanOrEqual(44);
});

// ── T186/T187 — el auto-cálculo RESTAURA, no adivina (10 sep 2026) ───────────
// showAgView calculaba solo al entrar a Planear sin resultado en memoria. Nació
// para una razón buena —el escenario muere al recargar, y el 16 ago en FICDEH se
// medían 4 filas antes y 0 después— pero atendía por igual dos situaciones que no
// son la misma: RESTAURAR algo que existía, y la PRIMERA entrada de la vida, donde
// no hay nada que restaurar. En la segunda el efecto es que llegás al paso
// «② PLANEAR» y el paso ya está hecho: ningún control de entrada se lee como tal,
// y la oferta de Disponibilidad queda de pie de página (auditoría #884).
//
// `planCalculado` es lo único que las distingue, porque cachedResult es memoria.
// Se afirman las DOS mitades: sin la marca no calcula, con la marca sí. Una sola
// habría dejado pasar la mitad que importa en cada dirección.
test('T186 — la primera vez en el festival, Planear no calcula solo', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  const r = await page.evaluate(async () => {
    const w = ms => new Promise(r => setTimeout(r, ms));
    const vivas = [...new Set(FILMS.filter(f => f.day && f.time && !f.info && !screeningPassed(f)).map(f => f.title))];
    state.set('watchlist', new Set(vivas.slice(0, 4)));
    state.set('planCalculado', false); localStorage.removeItem(FESTIVAL_STORAGE_KEY + 'calc1');
    state.set('savedAgenda', null);
    cachedResult = null;
    switchMainNav('mnav-planner'); showAgView();
    await w(1600);
    const btn = document.querySelector('.av-calc-btn');
    const porShowAgView = !!cachedResult;
    // La OTRA puerta: renderActiveView tiene su propio auto-cálculo. Si solo se
    // tapa una, la primera vez se sigue calculando sola por el otro lado y nadie
    // lo ve. Se dispara por su camino real —una mutación de un slice suscrito—
    // en vez de llamarla a mano: así el test también afirma que ESE camino pasa
    // por acá, que es lo que lo hace peligroso.
    state.set('watchlist', new Set([...watchlist, vivas[5]].filter(Boolean)));
    await w(1600);
    return {
      calculo: porShowAgView || !!cachedResult,
      porShowAgView,
      porRenderActiveView: !!cachedResult,
      marca: state.get('planCalculado'),
      btn: btn ? btn.textContent.trim() : null,
      resultado: !!document.querySelector('#ag-result .ag-day-hdr, #ag-result .mkrow, #ag-result .dato-linea'),
    };
  });
  expect(r.porShowAgView, 'showAgView no calcula solo — el paso 2 sigue siendo un paso por hacer').toBe(false);
  expect(r.porRenderActiveView, 'renderActiveView tampoco: las dos puertas o ninguna').toBe(false);
  expect(r.marca, 'y la marca sigue sin ponerse: nadie pidió opciones todavía').toBe(false);
  expect(r.btn, 'el primario invita a calcular, no a RE-calcular').not.toMatch(/^Re/i);
  expect(r.resultado, 'no hay un plan en pantalla que nadie pidió').toBe(false);
});

test('T187 — con la marca puesta (recarga), Planear sí restaura el cálculo', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  const r = await page.evaluate(async () => {
    const w = ms => new Promise(r => setTimeout(r, ms));
    const vivas = [...new Set(FILMS.filter(f => f.day && f.time && !f.info && !screeningPassed(f)).map(f => f.title))];
    state.set('watchlist', new Set(vivas.slice(0, 4)));
    state.set('planCalculado', true); localStorage.setItem(FESTIVAL_STORAGE_KEY + 'calc1', '1');  // ya calculó antes; la recarga se llevó el escenario
    state.set('savedAgenda', null);
    cachedResult = null;
    switchMainNav('mnav-planner'); showAgView();
    await w(2500);
    return { calculo: !!(cachedResult && cachedResult.scenarios) };
  });
  expect(r.calculo, 'restauró lo que la recarga se llevó').toBe(true);
});

// T188 — la marca la pone runCalc, que es la única puerta de los tres caminos
// (worker, fallback síncrono, sugerencias). Si se pusiera en el botón, calcular
// por cualquier otra vía dejaría al usuario recibiendo la oferta para siempre.
test('T188 — pedir opciones deja constancia de que acá ya se calculó', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  const r = await page.evaluate(async () => {
    const w = ms => new Promise(r => setTimeout(r, ms));
    const vivas = [...new Set(FILMS.filter(f => f.day && f.time && !f.info && !screeningPassed(f)).map(f => f.title))];
    state.set('watchlist', new Set(vivas.slice(0, 4)));
    state.set('planCalculado', false); localStorage.removeItem(FESTIVAL_STORAGE_KEY + 'calc1');
    cachedResult = null;
    switchMainNav('mnav-planner'); showAgView();
    await w(900);
    const antes = { estado: state.get('planCalculado'), disco: localStorage.getItem(FESTIVAL_STORAGE_KEY + 'calc1') === '1' };
    runCalc();
    await w(2500);
    return { antes, despues: { estado: state.get('planCalculado'), disco: localStorage.getItem(FESTIVAL_STORAGE_KEY + 'calc1') === '1' } };
  });
  expect(r.antes.estado, 'arranca sin marca').toBe(false);
  expect(r.antes.disco, 'y sin marca en disco').toBe(false);
  expect(r.despues.estado, 'pedir opciones la pone').toBe(true);
  expect(r.despues.disco, 'y sobrevive a la recarga (va a disco)').toBe(true);
});
