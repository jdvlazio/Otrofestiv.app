// @ts-check
// festivals.spec.js — Selector de festival, cambio de festival, validaciones cross-festival.
const { test, expect } = require('@playwright/test');
const { LEVIZA_SIMTIME, enterFestival, festivalTestIds } = require('./helpers');

// T08 — Selector-carrusel: los festivales VIGENTES (en curso/próximos) encabezan el
// riel; los pasados van tras el divisor "ANTERIORES". Invariante derivado de
// FESTIVAL_CONFIG en runtime, robusto a fechas (no hardcodea nombres).
test('T08 — selector-carrusel: vigentes encabezan, divisor separa grupos', async ({ page }) => {
  await page.goto('/');
  // Gate de readiness JS DEFINITIVO: [data-app-ready="1"] (fin del bootstrap
  // síncrono → riel poblado por _renderSplashRail) antes de leer las cards.
  await page.waitForSelector('html[data-app-ready="1"]', { state: 'attached', timeout: 15000 });
  await page.waitForSelector('.splash-card[data-fest]', { state: 'attached', timeout: 15000 });
  // TODO en UN evaluate → una sola lectura de reloj: evita el skew goto↔evaluate en
  // el borde exacto de fin de festival (ej. 19 JUL 23:00, cuando 2 vigentes pasan a
  // 'past'). Clasifica con la MISMA fn (_classifyFestival) que usó el riel.
  const r = await page.evaluate(async () => {
    const { _classifyFestival } = await import('/src/view/components.js');
    const { FESTIVAL_CONFIG } = await import('/src/config.js');
    // SCOPE #splash-rail: el sheet "cambiar festival" replica el riel (misma card,
    // clase .splash-rail) y también vive en el DOM — document-wide mezcla ambos y
    // el invariante de tiering lee las 18 cards intercaladas. Latente hasta FINCA:
    // con 0 vigentes, tieringOk era trivialmente true.
    const ids = [...document.querySelectorAll('#splash-rail .splash-card[data-fest]')].map(c => c.dataset.fest);
    const cls = ids.map(id => _classifyFestival(FESTIVAL_CONFIG[id]));
    const firstPastIdx = cls.indexOf('past');
    const lastCurrentIdx = cls.reduce((mx, c, i) => (c !== 'past' ? i : mx), -1);
    return {
      count: ids.length,
      hasCurrent: cls.some(c => c !== 'past'),
      hasPast: cls.some(c => c === 'past'),
      // invariante de tiering: ningún vigente aparece DESPUÉS de un pasado
      tieringOk: firstPastIdx === -1 || lastCurrentIdx < firstPastIdx,
      firstIsCurrent: cls[0] !== 'past',
      dividerPresent: !!document.querySelector('#splash-rail .splash-rail-div'),
      // Desde el divisor PRÓXIMOS puede haber DOS: se cuentan, no se asume uno.
      divisores: [...document.querySelectorAll('#splash-rail .splash-rail-div')].map(d => d.textContent.trim()),
      hasUpcoming: cls.some(c => c === 'upcoming'),
      hasOngoing: cls.some(c => c === 'ongoing'),
      leviza: ids.some(id => id.includes('leviza')),
    };
  });
  expect(r.count).toBeGreaterThan(1);
  expect(r.leviza).toBe(true); // leviza (pasado) presente en el riel
  expect(r.tieringOk).toBe(true); // vigentes siempre antes que pasados
  if (r.hasCurrent) expect(r.firstIsCurrent).toBe(true); // un vigente encabeza
  // El divisor "ANTERIORES" existe EXACTAMENTE cuando hay AMBOS grupos (si todos
  // los festivales ya pasaron, p.ej. tras el 19 JUL, no se emite → no falla el CI).
  expect(r.dividerPresent).toBe(r.hasCurrent && r.hasPast);
  // Un divisor SEPARA dos grupos: se emite exactamente cuando hay algo de los dos
  // lados. Colgar uno de primero descentraría el snap inicial, que es de lo que
  // depende la preselección.
  const esperados = (r.hasOngoing && r.hasUpcoming ? 1 : 0) + (r.hasCurrent && r.hasPast ? 1 : 0);
  expect(r.divisores.length, `divisores: ${JSON.stringify(r.divisores)}`).toBe(esperados);
});

// T40 — El splash entra COMPLETO sin scroll vertical en una pantalla chica
// (360×640, peor caso), y el riel horizontal alcanza la última card. El splash es
// position:fixed → si el contenido excede el alto, los actores de abajo ("Entrar")
// quedan inalcanzables. Invariante robusto (independiente del contenido): el splash
// no desborda verticalmente, y el riel scrollea en X hasta revelar la última card.
test('T40 — splash: cabe sin scroll vertical (360×640) y el riel alcanza la última card', async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 640 });
  await page.goto('/');
  await page.waitForSelector('html[data-app-ready="1"]', { state: 'attached', timeout: 15000 });
  await page.waitForSelector('.splash-card[data-fest]', { state: 'attached', timeout: 15000 });
  const geo = await page.evaluate(() => {
    const splash = document.getElementById('otrofestiv-splash');
    const rail = document.getElementById('splash-rail');
    const cards = rail.querySelectorAll('.splash-card');
    const last = cards[cards.length - 1];
    // Riel: scrollear al fondo horizontal → la última card debe quedar dentro del viewport.
    rail.scrollLeft = rail.scrollWidth;
    const rr = rail.getBoundingClientRect();
    const lr = last.getBoundingClientRect();
    return {
      // sin scroll vertical: el contenido del splash no excede su alto fijo
      noVScroll: splash.scrollHeight <= splash.clientHeight + 1,
      innerHeight: window.innerHeight,
      splashBottom: splash.getBoundingClientRect().bottom,
      lastReachable: lr.left >= rr.left - 1 && lr.right <= rr.right + 1,
    };
  });
  expect(geo.noVScroll).toBe(true);
  expect(geo.splashBottom).toBeLessThanOrEqual(geo.innerHeight + 2);
  expect(geo.lastReachable).toBe(true);
});

// T41 — Splash en LANDSCAPE de teléfono (844×390): mismo invariante que T40 pero
// en el peor caso de ALTO. El piso duro de 184px del póster empujaba "Entrar" bajo
// el fold e inalcanzable (position:fixed sin scroll). La media query (max-height:480px)
// baja el póster y comprime el padding → el splash entra completo y "Entrar" es visible.
test('T41 — splash: cabe en landscape (844×390) y "Entrar" es alcanzable', async ({ page }) => {
  await page.setViewportSize({ width: 844, height: 390 });
  // Reduced-motion → el reveal es instantáneo (sin el transitorio translateY(16px)
  // del @keyframes splashIn que infla scrollHeight mid-animación). Mide el REPOSO.
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/');
  await page.waitForSelector('html[data-app-ready="1"]', { state: 'attached', timeout: 15000 });
  await page.waitForSelector('.splash-card[data-fest]', { state: 'attached', timeout: 15000 });
  const geo = await page.evaluate(() => {
    const splash = document.getElementById('otrofestiv-splash');
    const btn = document.getElementById('splash-enter-btn');
    return {
      noVScroll: splash.scrollHeight <= splash.clientHeight + 1,
      innerHeight: window.innerHeight,
      btnBottom: btn.getBoundingClientRect().bottom,
    };
  });
  expect(geo.noVScroll).toBe(true);
  // "Entrar" completamente dentro del viewport (no bajo el fold)
  expect(geo.btnBottom).toBeLessThanOrEqual(geo.innerHeight + 1);
});

// T42b — Selección-por-scroll GATEADA por gesto: un scroll SIN pointer/touch previo
// (re-snap programático del render, focus-scroll del teclado al tabear) NO debe
// cambiar la selección; solo un arrastre real del usuario elige por scroll. Guarda
// dos bugs: auto-selección con 0 vigentes (divisor descentra → snap dispara scroll)
// y el override de la selección al navegar con teclado hacia "Entrar".
test('T42b — el scroll sin gesto de usuario no auto-selecciona (gate)', async ({ page }) => {
  // El reloj se congela: la premisa del test es "0 o 2+ festivales en curso", y eso
  // depende del CALENDARIO. El 10 ago 2026 quedó EXACTAMENTE uno en curso (FICMA
  // abrió; FICDEH y FINCA abrían el 12) → el riel pre-selecciona, "Entrar" se
  // habilita y el test caía — sin que nada de la app estuviera roto. El 13 los tres
  // corren a la vez, que es el escenario que este gate quiere vigilar.
  await page.clock.install({ time: new Date('2026-08-13T10:00:00-05:00') });
  await page.goto('/');
  await page.waitForSelector('html[data-app-ready="1"]', { state: 'attached', timeout: 15000 });
  await page.waitForSelector('.splash-card[data-fest]', { state: 'attached', timeout: 15000 });
  // Acotado a #splash-rail A PROPÓSITO: el sheet "cambiar festival" (#fs-festival-list)
  // reusa las clases .splash-card/.on, y ahí .on significa "lo que estás mirando".
  // Sin acotar, este test leía la card del SHEET y daba por buena una selección que
  // el riel nunca hizo: verde midiendo el elemento equivocado.
  const sel = () => ({
    on: document.querySelector('#splash-rail .splash-card.on')?.dataset.fest || null,
    disabled: document.getElementById('splash-enter-btn').disabled,
  });
  const before = await page.evaluate(sel);
  // La premisa, explícita: con 0 o 2+ en curso no hay preselección. Si esto falla no
  // es el gate — es que el calendario o FESTIVAL_CONFIG cambiaron y hay que mover la
  // fecha congelada de arriba.
  expect(before.on, 'premisa rota: se esperaba NINGUNA preselección (0 o 2+ en curso)').toBeNull();
  expect(before.disabled, 'premisa rota: "Entrar" debería arrancar deshabilitado').toBe(true);
  // Scroll PROGRAMÁTICO (sin pointerdown/touchstart) → dispara 'scroll' pero el gate
  // no está armado → no debe seleccionar nada tras el debounce.
  const afterProgrammatic = await page.evaluate(async () => {
    const rail = document.getElementById('splash-rail');
    rail.scrollLeft = rail.scrollWidth; // centra otra card
    rail.dispatchEvent(new Event('scroll'));
    await new Promise(r => setTimeout(r, 200)); // > 90ms del debounce
    return {
      on: document.querySelector('#splash-rail .splash-card.on')?.dataset.fest || null,
      disabled: document.getElementById('splash-enter-btn').disabled,
    };
  });
  // Ahora un ARRASTRE real (pointerdown sobre el riel → arma el gate → scroll elige).
  const afterGesture = await page.evaluate(async () => {
    const rail = document.getElementById('splash-rail');
    rail.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true }));
    rail.scrollLeft = rail.scrollWidth;
    rail.dispatchEvent(new Event('scroll'));
    await new Promise(r => setTimeout(r, 200));
    return {
      on: document.querySelector('#splash-rail .splash-card.on')?.dataset.fest || null,
      disabled: document.getElementById('splash-enter-btn').disabled,
    };
  });
  // Sin gesto: la selección no cambió (sigue sin .on, "Entrar" disabled).
  expect(afterProgrammatic.on).toBe(before.on);
  expect(afterProgrammatic.disabled).toBe(true);
  // Con gesto: sí eligió (hay .on, "Entrar" habilitado).
  expect(afterGesture.on).not.toBeNull();
  expect(afterGesture.disabled).toBe(false);
});

// T37 — Cambiar de festival actualiza el topbar
test('T37 — cambiar de festival actualiza el topbar', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  const beforeName = await page.locator('.hdr-fest-name').textContent();
  await page.evaluate(() => loadFestival('tribeca2026'));
  await page.waitForFunction(
    () => document.querySelector('.hdr-fest-name')?.textContent?.toUpperCase().includes('TRIBECA'),
    { timeout: 8000 }
  );
  const afterName = await page.locator('.hdr-fest-name').textContent();
  expect(beforeName).not.toEqual(afterName);
  expect(afterName?.toUpperCase()).toContain('TRIBECA');
});

// T39 — Todos los festivales cargan sin crash
test('T39 — todos los festivales cargan sin crash', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  const festIds = await page.evaluate(() =>
    Object.keys(FESTIVAL_CONFIG).filter(k => k !== 'default')
  );
  // El costo de este test CRECE con cada festival: los carga todos en serie.
  // Con 14 festivales y 2.2 MB de JSON tarda ~17s en local, y el presupuesto fijo
  // de 30s se agotó en CI al entrar el festival nº14 — no por un defecto suyo,
  // sino porque el techo no acompañaba al catálogo. El presupuesto se deriva del
  // número de festivales para que el próximo onboarding no vuelva a chocarlo.
  test.setTimeout(20000 + festIds.length * 5000);

  for (const id of festIds) {
    await page.evaluate((fid) => loadFestival(fid), id);
    await page.waitForFunction(() => typeof FILMS !== 'undefined' && FILMS.length > 0, { timeout: 8000 });
  }
  const realErrors = errors.filter(e => !e.includes('sentry'));
  expect(realErrors).toHaveLength(0);
});

// T42 — onclick handlers: ninguno tiene sintaxis inválida
test('T42 — onclick handlers tienen JS válido', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  const errors = [];
  page.on('pageerror', e => { if (e.message.includes('SyntaxError')) errors.push(e.message); });
  await page.waitForTimeout(200); // mínimo: colección de errores async
  expect(errors).toHaveLength(0);
});

// ─── PARAMETRIZADOS test.each ────────────────────────────────────────────────
// Mismo invariante corriendo contra TODOS los festivales con datos. 1 definición →
// N test runs. DERIVADO de config + JSON en disco (festivalTestIds) — un festival
// nuevo (septiembre) entra a la cobertura de smoke solo al agregar su config + JSON,
// sin tocar specs. Antes: hardcodeado a ['leviza2026','tribeca2026'].

const MAIN_FESTIVALS = festivalTestIds();

// P01 — Festival tiene films (parametrizado)
for (const festId of MAIN_FESTIVALS) {
  test(`P01 — ${festId}: carga con films`, async ({ page }) => {
    await enterFestival(page, festId);
    const count = await page.evaluate(() => typeof FILMS !== 'undefined' ? FILMS.length : 0);
    expect(count).toBeGreaterThan(0);
  });
}

// P02 — Festival carga sin errores JS (parametrizado)
for (const festId of MAIN_FESTIVALS) {
  test(`P02 — ${festId}: carga sin errores JS`, async ({ page }) => {
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    await enterFestival(page, festId);
    const critical = errors.filter(e => !e.includes('sentry') && !e.includes('clarity'));
    expect(critical).toHaveLength(0);
  });
}

// P03 — Festival: topbar muestra nombre del festival (parametrizado)
for (const festId of MAIN_FESTIVALS) {
  test(`P03 — ${festId}: topbar muestra nombre`, async ({ page }) => {
    await enterFestival(page, festId);
    await page.waitForSelector('.hdr-fest-name', { timeout: 5000 });
    const name = await page.locator('.hdr-fest-name').textContent();
    expect(name?.trim().length).toBeGreaterThan(0);
  });
}

// ── P06 — el riel nombra a los PRÓXIMOS, y eso no mueve el arranque ────────────
// En curso y por empezar viajaban en el MISMO grupo del riel, sin nada que los
// distinga: con FICMA abierto y FICDEH/FINCA a dos días, las tres cards se leían
// igual de disponibles (Juan, 9 ago 2026). El tier ya existía en _sortFestivals;
// faltaba decirlo en pantalla.
//
// Se descartó mudar los próximos a la IZQUIERDA: haría correr el tiempo de derecha
// a izquierda —al revés de como se lee una línea de tiempo— y obligaría a arrancar
// el riel DESPLAZADO. Eso último es el riesgo real: la preselección con un solo
// festival en curso depende de que la card correcta quede centrada al abrir, y hoy
// eso se cumple porque el riel arranca en scrollLeft 0. Este test fija las dos
// cosas: el orden de los grupos y que el arranque no se movió.
//
// RELOJ FIJO: _classifyFestival lee new Date() real (no _simTime), así que sin
// congelarlo el test diría cosas distintas cada día. 11 AGO 2026 es una fecha con
// al menos un festival en curso y uno por empezar; si el config cambia y deja de
// haberlos, el test lo dice y se saltea en vez de fallar por una premisa vieja.
test('P06 — el riel separa PRÓXIMOS sin mover el arranque del snap', async ({ page }) => {
  await page.clock.install({ time: new Date('2026-08-11T10:00:00-05:00') });
  await page.goto('/');
  await page.waitForSelector('html[data-app-ready="1"]', { state: 'attached', timeout: 15000 });
  await page.waitForSelector('#splash-rail .splash-card[data-fest]', { state: 'attached', timeout: 15000 });

  const r = await page.evaluate(async () => {
    const { _classifyFestival } = await import('/src/view/components.js');
    const { FESTIVAL_CONFIG } = await import('/src/config.js');
    const riel = document.getElementById('splash-rail');
    // La tira TAL CUAL se lee: cards y divisores en orden de aparición.
    const tira = [...riel.children].map(e => e.classList.contains('splash-rail-div')
      ? { div: e.textContent.trim() }
      : { cls: _classifyFestival(FESTIVAL_CONFIG[e.dataset.fest] || {}) });
    const on = document.querySelector('#splash-rail .splash-card.on');
    const btn = document.querySelector('.splash-enter-btn');
    const cr = riel.getBoundingClientRect();
    const oc = on ? on.getBoundingClientRect() : null;
    return {
      tira,
      enCurso: tira.filter(x => x.cls === 'ongoing').length,
      proximos: tira.filter(x => x.cls === 'upcoming').length,
      preseleccionado: on ? on.dataset.fest : null,
      entrarHabilitado: btn ? !btn.disabled : null,
      scrollInicial: riel.scrollLeft,
      centrado: oc ? Math.abs(((oc.left + oc.right) / 2) - ((cr.left + cr.right) / 2)) : null,
    };
  });

  if (!r.enCurso || !r.proximos) {
    test.skip(true, `P06: al 11 AGO 2026 no hay en-curso + próximos (${r.enCurso}/${r.proximos}), skip`); return; }

  // ORDEN: ningún próximo antes de un en-curso, y el divisor justo entre los grupos.
  const idxDivProx = r.tira.findIndex(x => x.div);
  const ultimoEnCurso = r.tira.reduce((mx, x, i) => (x.cls === 'ongoing' ? i : mx), -1);
  const primerProximo = r.tira.findIndex(x => x.cls === 'upcoming');
  expect(ultimoEnCurso, 'un próximo se coló antes de un festival en curso').toBeLessThan(primerProximo);
  expect(idxDivProx, 'el divisor no está entre los dos grupos').toBeGreaterThan(ultimoEnCurso);
  expect(idxDivProx, 'el divisor no está entre los dos grupos').toBeLessThan(primerProximo);

  // SNAP: con UN solo festival en curso, sigue preseleccionado y centrado desde 0.
  if (r.enCurso === 1) {
    expect(r.preseleccionado, 'se perdió la preselección del único festival en curso').toBeTruthy();
    expect(r.entrarHabilitado, '«Entrar» quedó deshabilitado con un festival preseleccionado').toBe(true);
    expect(r.scrollInicial, 'el riel ya no arranca en 0 — el divisor movió el arranque').toBe(0);
    expect(r.centrado, `la card preseleccionada quedó descentrada ${r.centrado}px`).toBeLessThanOrEqual(2);
  }
});

// ── P07 — el selector ES el riel del splash, no una copia ─────────────────────
// `_renderFestivalSelectorHTML` delega en `_renderSplashRailHTML` y solo cambia la
// acción; el info de las dos superficies sale de `_fillFestInfo`. Por eso todo
// ajuste del splash aparece en el selector sin tocarlo — el arreglo del país de
// FINCA y el divisor PRÓXIMOS entraron en ambos sin una línea extra.
//
// Eso se sostiene mientras el selector DELEGUE. El día que alguien copie el render
// «para tocar solo el selector», nada lo detiene: las dos superficies empiezan a
// derivar y la divergencia se descubre meses después, en una captura. Ya pasó con
// el marco editorial del póster (7 copias) y con los tres radios.
//
// Este test compara los DOS markups renderizados. La única diferencia legítima es
// la acción —el splash selecciona y espera «Entrar», el selector carga directo—, y
// es lo único que se normaliza. Se entra al festival EN CURSO a propósito: así la
// card marcada `.on` es la misma en ambos (preselección en el splash, activo en el
// selector) y no hay que aflojar la comparación para que pase.
test('P07 — el markup del selector es el mismo del splash (una implementación)', async ({ page }) => {
  // Reloj fijo: 11 AGO 2026 tiene un festival en curso y dos por empezar, así que
  // la comparación ejerce las cards Y los dos divisores. Sin congelarlo, el test
  // compararía rieles distintos según el día.
  await page.clock.install({ time: new Date('2026-08-11T10:00:00-05:00') });
  await page.goto('/');
  await page.waitForSelector('html[data-app-ready="1"]', { state: 'attached', timeout: 15000 });
  await page.waitForSelector('#splash-rail .splash-card[data-fest]', { state: 'attached', timeout: 15000 });

  const enCurso = await page.evaluate(async () => {
    const { _classifyFestival } = await import('/src/view/components.js');
    const { FESTIVAL_CONFIG } = await import('/src/config.js');
    return Object.entries(FESTIVAL_CONFIG)
      .filter(([, c]) => c.name && c.group !== 'test' && _classifyFestival(c) === 'ongoing')
      .map(([id]) => id);
  });
  if (enCurso.length !== 1) {
    test.skip(true, `P07: al 11 AGO 2026 hay ${enCurso.length} festivales en curso (se necesita 1), skip`); return; }
  const fest = enCurso[0];

  const splash = await page.evaluate(() => ({
    riel: document.getElementById('splash-rail').innerHTML,
    info: (document.querySelector('#splash-info')?.textContent || '').replace(/\s+/g, ' ').trim(),
  }));

  await page.evaluate((id) => {
    const c = FESTIVAL_CONFIG[id];
    selectSplashFest(c.name, `${c.city} · ${c.dates}`, id);
  }, fest);
  await page.locator('.splash-enter-btn').click();
  await page.waitForSelector('.poster-card, .plist-item, .dtab', { timeout: 15000 });
  await page.evaluate(() => { if (typeof openFestivalSheet === 'function') openFestivalSheet(); });
  await page.waitForSelector('#fs-festival-list .splash-rail .splash-card', { timeout: 8000 });
  await page.waitForTimeout(600);

  const sel = await page.evaluate(() => ({
    riel: document.querySelector('#fs-festival-list .splash-rail').innerHTML,
    info: (document.getElementById('fs-info')?.textContent || '').replace(/\s+/g, ' ').trim(),
  }));

  // ÚNICA diferencia legítima: la acción de la card.
  const norm = h => h.replace(/data-action="[^"]*"/g, 'data-action="·"').replace(/\s+/g, ' ').trim();
  const a = norm(splash.riel), b = norm(sel.riel);
  // Se afirma el PUNTO de divergencia, no la igualdad de los dos markups enteros:
  // un `toBe` sobre 4 KB de HTML vuelca las dos cadenas completas y el fallo se
  // vuelve ilegible. Así el mensaje trae la ventana donde empiezan a diferir.
  let i = -1;
  if (a !== b) { i = 0; while (i < a.length && i < b.length && a[i] === b[i]) i++; }
  const ventana = i < 0 ? '' :
    `\n  splash  …${a.slice(Math.max(0, i - 70), i + 70)}\n  selector…${b.slice(Math.max(0, i - 70), i + 70)}`;
  expect(i, `el selector dejó de delegar en el riel del splash — hay dos implementaciones.${ventana}`).toBe(-1);
  expect(sel.info, 'el info del selector dejó de salir de _fillFestInfo').toBe(splash.info);
  expect(a).toContain('splash-rail-div'); // la comparación ejerció los divisores
});

// ── P08 — filtrar por una sede nunca cruza ciudades (invariante, no mecanismo) ─
// El bug del 9 ago no fue del filtro de ciudad: fue que la SEDE se identificaba por
// nombre corto, y el corto no es único entre ciudades. Elegir «Cinema Local» en
// Bogotá traía las 4 funciones de Cali.
//
// Este test no sabe nada de centinelas, de `short` ni de la clave (ciudad, short):
// afirma el INVARIANTE —lo que el usuario espera— así que sigue cazando la clase
// aunque mañana cambiemos por completo cómo se implementa. Es el mismo patrón que
// el oráculo del planeador: juzgar el resultado, no el camino.
//
// Corre sobre CADA festival del config: uno nuevo entra solo, y si es multiciudad
// queda cubierto desde su primer PR.
for (const festId of MAIN_FESTIVALS) {
  test(`P08 — ${festId}: una sede no arrastra funciones de otra ciudad`, async ({ page }) => {
    await enterFestival(page, festId);
    const r = await page.evaluate(async () => {
      const { venueMatches, vcfg } = await import('/src/view/helpers.js');
      const conCiudad = FILMS.filter(f => f.venue && f.day && (vcfg(f.venue).city || ''));
      const ciudades = [...new Set(conCiudad.map(f => vcfg(f.venue).city))];
      if (ciudades.length < 2) return { mono: true, ciudades: ciudades.length };
      // Se prueban TODAS las sedes visibles, no una muestra: son decenas, es barato,
      // y el caso que rompía era justo una sede puntual entre 113.
      const sedes = [...new Set(conCiudad.map(f => vcfg(f.venue).city + '\u001F' + vcfg(f.venue).short))];
      const cruces = [];
      sedes.forEach(k => {
        const [ciudad, short] = k.split('\u001F');
        const vis = FILMS.filter(f => f.venue && venueMatches(f.venue, 'sede:' + k));
        const otras = vis.filter(f => (vcfg(f.venue).city || '') !== ciudad);
        if (otras.length) cruces.push(`${short} (${ciudad}) trajo ${otras.length} de ${[...new Set(otras.map(f => vcfg(f.venue).city))].join('/')}`);
        // y la sede tiene que existir: si el filtro la deja vacía, desapareció
        if (!vis.length) cruces.push(`${short} (${ciudad}) no devuelve ninguna función`);
      });
      return { mono: false, sedes: sedes.length, ciudades: ciudades.length, cruces };
    });
    if (r.mono) { test.skip(true, `P08 ${festId}: ${r.ciudades} ciudad(es), no aplica`); return; }
    console.log(`P08 ${festId}: ${r.sedes} sedes en ${r.ciudades} ciudades`);
    expect(r.cruces, `el filtro de sede cruzó ciudades:\n  ${r.cruces.join('\n  ')}`).toEqual([]);
  });
}

// AP01 — festival APLAZADO (status:{kind:'postponed'}): se VE pero no invita a ir.
// Nace del terremoto de Manizales (FICMA 17, 10 ago 2026): las fechas decían «en
// curso» mientras el festival anunciaba que no habría festival. El estado DECLARADO
// le gana a la aritmética de fechas en _classifyFestival (dueño único) y de ahí caen
// preselección, punto verde, AHORA y la apertura en «hoy». La banda lleva las
// palabras del PROPIO festival (note, verbatim). Reloj congelado en pleno rango de
// fechas del festival: el caso más hostil (sin status diría ongoing).
test('AP01 — aplazado: distintivo + banda + sin AHORA + sin «hoy»', async ({ page }) => {
  await page.clock.install({ time: new Date('2026-08-13T15:30:00-05:00') });
  await page.goto('/');
  await page.waitForSelector('html[data-app-ready="1"]', { state: 'attached', timeout: 15000 });
  await page.waitForSelector('.splash-card[data-fest]', { state: 'attached', timeout: 15000 });
  // Declarar el estado en runtime sobre FICMA (en el dato real hoy: group:'test').
  const rail = await page.evaluate(async () => {
    const { FESTIVAL_CONFIG } = await import('/src/config.js');
    const cfg = FESTIVAL_CONFIG['ficma2026'];
    delete cfg.group;
    cfg.status = { kind: 'postponed', since: '2026-08-10', note: 'Hoy, primero, la vida. Estaremos anunciando nuevas fechas y actividades.', note_en: 'Today, life comes first. We will be announcing new dates and activities.', url: 'https://www.instagram.com/p/Db35wc_zR5h/' };
    const { _classifyFestival, _renderSplashRailHTML } = await import('/src/view/components.js');
    const { state } = await import('/src/state/state.js');
    const html = _renderSplashRailHTML(state, null);
    // Orden en el riel: la card aplazada va DESPUÉS de los próximos y ANTES de ANTERIORES.
    // El divisor se busca POR SU RÓTULO, no por la clase. El riel emite DOS divisores
    // con la misma clase —«Próximos» y «Anteriores»— y buscar el primero daba con el
    // que no era en cuanto existía algún festival próximo: al publicar CineAutopsia
    // (21–29 AGO, próximo el 13 de agosto que congela este test) apareció el divisor
    // «Próximos» delante de FICMA y el test señaló una regresión que no ocurrió.
    const { t } = await import('/src/i18n/i18n.js');
    const iFicma = html.indexOf('data-fest="ficma2026"');
    const iAnteriores = html.indexOf(`<span class="srd-lbl">${t('splash_anteriores')}</span>`);
    return { cls: _classifyFestival(cfg), badge: html.includes('splash-card-badge'),
             postponedClass: /splash-card[^"]*postponed/.test(html),
             ficmaAntesDeAnteriores: iFicma >= 0 && iAnteriores > iFicma };
  });
  // Con fechas «en curso», el estado declarado gana.
  expect(rail.cls).toBe('postponed');
  expect(rail.badge).toBe(true);
  expect(rail.postponedClass).toBe(true);
  expect(rail.ficmaAntesDeAnteriores).toBe(true);
  // NO REPETIR (regla de Juan): la card ya lleva el distintivo APLAZADO — la línea
  // de fechas del info dice solo «FECHAS POR ANUNCIAR», sin repetir el estado.
  const infoFechas = await page.evaluate(async () => {
    const { FESTIVAL_CONFIG } = await import('/src/config.js');
    const c = FESTIVAL_CONFIG['ficma2026'];
    selectSplashFest(c.name, `${c.city} · ${c.dates}`, 'ficma2026');
    return document.querySelector('#otrofestiv-splash .splash-info-dates')?.textContent || '';
  });
  expect(infoFechas).toBe('FECHAS POR ANUNCIAR');
  // Entrar al festival aplazado: banda con las palabras del festival, sin AHORA,
  // y la vista NO aterriza en «hoy» (se abre como festival futuro: grilla TODO).
  await page.evaluate(() => { const c = FESTIVAL_CONFIG['ficma2026']; selectSplashFest(c.name, `${c.city} · ${c.dates}`, 'ficma2026'); });
  await page.locator('.splash-enter-btn').click();
  await page.waitForSelector('#fest-postponed-banner', { timeout: 15000 });
  const dentro = await page.evaluate(async () => {
    // AHORA se mide DIRECTO en el dueño (isNowShowing), no contando chips en el
    // DOM: a la hora congelada puede no haber ninguna función viva en la vista y
    // el conteo daría 0 con o sin el gate — un assert que no discrimina. Se
    // fabrica una función que SÍ estaría viva ahora (13 ago, 15:00, 120 min):
    // sin el gate devolvería true; con el festival aplazado debe ser false.
    const { isNowShowing } = await import('/src/view/helpers.js');
    return {
      banda: document.getElementById('fest-postponed-banner')?.textContent || '',
      link: document.querySelector('.fest-postponed-link')?.href || '',
      ahoraViva: isNowShowing({ day: '2026-08-13', time: '15:00', duration: '120 min' }),
      ahoraChips: document.querySelectorAll('.poster-now, .film-check-badge').length,
      activeDay: globalThis.activeDay,
    };
  });
  expect(dentro.banda).toContain('Hoy, primero, la vida.');
  expect(dentro.banda).toContain('APLAZADO');
  expect(dentro.link).toContain('instagram.com');
  expect(dentro.ahoraViva).toBe(false); // el dueño del AHORA obedece al estado
  expect(dentro.ahoraChips).toBe(0);    // y ningún chip llegó al DOM
  expect(dentro.activeDay).toBe('all'); // no aterriza en «hoy»
  // Las fechas viejas NO se prometen en NINGUNA superficie (dueño único _langDates,
  // 10 ago): el header interno decía «· 10–17 AGO 2026» junto al selector.
  const hdrFechas = await page.evaluate(() => document.querySelector('.hdr-fest-dates')?.textContent || '');
  expect(hdrFechas).toContain('FECHAS POR ANUNCIAR');
  expect(hdrFechas).not.toContain('AGO');
  expect(hdrFechas).not.toContain('2026'); // el año sobra bajo status
  // EN: la banda se REHORNEA al cambiar idioma (setLang no pasa por loadFestival —
  // el bug del idioma horneado, cazado en QA visual). Con note_en presente la cita
  // sale traducida; al volver a ES, el verbatim del festival.
  await page.evaluate(async () => { const m = await import('/src/controller/pipeline.js'); m.setLang('en'); });
  await page.waitForTimeout(500); // setLang difiere el render 200ms (fade)
  const bandaEN = await page.evaluate(() => document.getElementById('fest-postponed-banner')?.textContent || '');
  expect(bandaEN).toContain('POSTPONED');
  expect(bandaEN).toContain('Today, life comes first.');
  // Fallback: sin note_en, el EN muestra el ES INTACTO — nunca se traduce en runtime.
  const bandaSinNoteEn = await page.evaluate(async () => {
    const { FESTIVAL_CONFIG } = await import('/src/config.js');
    delete FESTIVAL_CONFIG['ficma2026'].status.note_en;
    const m = await import('/src/controller/festival.js');
    m.renderPostponedBanner(FESTIVAL_CONFIG['ficma2026']);
    return document.getElementById('fest-postponed-banner')?.textContent || '';
  });
  expect(bandaSinNoteEn).toContain('Hoy, primero, la vida.');
});

// AP02 — Mi Plan de un festival APLAZADO: el plan se ve, con el aviso, y NUNCA
// entra en Modo Recuerdo. El reloj se congela DESPUÉS de las fechas viejas (18 ago,
// FICMA cerraba el 17): sin el estado, festivalEnded() —pura aritmética contra
// FESTIVAL_END— daba el festival por terminado y la app pedía «Marcá lo que viste y
// calificálo» sobre ocho días que no ocurrieron. Nadie habría desplegado nada: el
// bug llegaba solo, con el calendario.
test('AP02 — aplazado: Mi Plan avisa y no entra en Modo Recuerdo', async ({ page }) => {
  await page.clock.install({ time: new Date('2026-08-18T12:00:00-05:00') });
  await page.goto('/');
  await page.waitForSelector('html[data-app-ready="1"]', { state: 'attached', timeout: 15000 });
  await page.waitForSelector('#splash-rail .splash-card[data-fest="ficma2026"]', { timeout: 15000 });
  await page.evaluate(() => { const c = FESTIVAL_CONFIG['ficma2026']; selectSplashFest(c.name, `${c.city} · ${c.dates}`, 'ficma2026'); });
  await page.locator('.splash-enter-btn').click();
  await page.waitForSelector('.poster-card, .plist-item', { timeout: 15000 });
  const r = await page.evaluate(async () => {
    const { festivalEnded } = await import('/src/domain/time.js');
    // Guardar un plan real: se toma una función del catálogo tal cual la arma la app.
    const { state } = await import('/src/state/state.js');
    const f = state.snapshot().FILMS.find(x => x.day && x.time && !x.info);
    toggleWL(f.title);
    // `_title` (no `title`): es la forma REAL de un ítem del plan — la que arma
    // commitPlan en handlers.js. Con `title` el render de Mi Plan lanza y cae en su
    // caja de error, que es exactamente lo que este test debe distinguir de un plan
    // sano (me pasó al escribirlo).
    state.set('savedAgenda', { schedule: [{ ...f, _title: f.title }] });
    // showAgView (no solo switchMainNav): es lo que hace visible Mi Plan — con
    // switchMainNav sola el usuario sigue viendo el Programa (me pasó en la captura).
    switchMainNav('mnav-miplan');
    showAgView();
    await new Promise(res => requestAnimationFrame(res));
    const v = document.getElementById('ag-view');
    return {
      ended: festivalEnded(),
      // UNA sola banda visible en la pantalla: la del header sigue ahí en Mi Plan.
      // Al escribir esto agregué una segunda dentro de #ag-view y quedaron dos
      // avisos idénticos, uno encima del otro.
      bandas: [...document.querySelectorAll('.fest-postponed-banner')]
        .filter(el => el.getBoundingClientRect().height > 0).length,
      aviso: !!document.querySelector('#hdr-programa .fest-postponed-banner'),
      avisoTexto: document.querySelector('.fest-postponed-banner')?.textContent || '',
      // Modo Recuerdo pide calificar lo vivido — no debe aparecer.
      recuerdo: /Marcá lo que viste|Tu festival/i.test(v.innerText || ''),
      // El plan sigue ahí: el dato no se toca. Se exige el título Y la ausencia de
      // la caja de error del render (renderSavedAgendaHTML atrapa sus fallos y
      // muestra .error-box en vez de reventar — un plan roto se vería «vacío»).
      tituloEnPlan: (v.innerText || '').includes(f.title.slice(0, 18)),
      errorBox: !!v.querySelector('.error-box'),
    };
  });
  expect(r.ended).toBe(false);        // un aplazado NO terminó: no ocurrió
  expect(r.recuerdo).toBe(false);     // nada que recordar
  expect(r.aviso).toBe(true);         // pero sí una explicación
  expect(r.bandas).toBe(1);           // UNA, no dos
  expect(r.avisoTexto).toContain('APLAZADO');
  expect(r.errorBox).toBe(false);     // el plan RINDE (no la caja de error)
  expect(r.tituloEnPlan).toBe(true);  // y el plan intacto, no un hueco
});

// AP03 — aviso con alcance por CIUDAD (sismo del 11 ago 2026: FICDEH canceló
// Quibdó, Cali, Pereira y Manizales y siguió en las otras 7). Verifica las cuatro
// piezas: el sellado alcanza SOLO esas ciudades, hay UN banner y no 88, el banner
// habla con las palabras del festival + enlace, y la card NO promete «nueva fecha»
// —copy escrito para REPROGRAMADA, que en una cancelación por tragedia miente—.
test('AP03 — cancelación por ciudad: sella, un solo banner, sin fecha prometida', async ({ page }) => {
  await page.clock.install({ time: new Date('2026-08-13T10:00:00-05:00') });
  await page.goto('/');
  await page.waitForSelector('html[data-app-ready="1"]', { state: 'attached', timeout: 15000 });
  await page.waitForSelector('.splash-card[data-fest="ficdeh2026"]', { timeout: 15000 });
  const CIUDADES = ['Quibdó', 'Cali', 'Pereira', 'Manizales'];
  const r = await page.evaluate(async (CIUDADES) => {
    const { NOTICES, FESTIVAL_CONFIG } = await import('/src/config.js');
    // Solo si NO está ya: desde el 12 ago el aviso real vive en config.js, y
    // empujar una copia daba DOS banners para un mismo hecho — el test se caía
    // por su propio fixture. Así vigila el MECANISMO (alcance por ciudad, un
    // banner, sin promesa de fecha) y no depende de que este festival concreto
    // siga teniendo su aviso: cuando FICDEH termine y se retire, el test crea
    // el suyo y sigue valiendo.
    if (!NOTICES.some(n => n.id === 'ficdeh-sismo-ciudades')) NOTICES.push({
      festival: 'ficdeh2026', type: 'cancelled', cities: CIUDADES,
      id: 'ficdeh-sismo-ciudades',
      note: 'FICDEH canceló su programación en <b>Quibdó, Cali, Pereira y Manizales</b> por el sismo. Sigue activa en las demás ciudades.',
      note_en: 'FICDEH canceled its programming in Quibdó, Cali, Pereira and Manizales due to the earthquake. It remains active in all other cities.',
      url: 'https://www.instagram.com/p/Db6xcU2FGb6/',
    });
    const c = FESTIVAL_CONFIG['ficdeh2026'];
    selectSplashFest(c.name, `${c.city} · ${c.dates}`, 'ficdeh2026');
    return true;
  }, CIUDADES);
  await page.locator('.splash-enter-btn').click();
  await page.waitForSelector('.poster-card, .plist-item', { timeout: 20000 });
  const m = await page.evaluate(async (CIUDADES) => {
    const { state } = await import('/src/state/state.js');
    const { FILMS } = state.snapshot();
    const { vcfg } = await import('/src/view/helpers.js');
    const city = f => (vcfg(f.venue) || {}).city || '';
    const enCiudades = FILMS.filter(f => CIUDADES.includes(city(f)));
    const fuera = FILMS.filter(f => f.day && f.time && !CIUDADES.includes(city(f)));
    return {
      selladasDentro: enCiudades.filter(f => f._cancelled).length,
      totalDentro: enCiudades.length,
      // Ni una sola función de las OTRAS ciudades puede quedar sellada.
      selladasFuera: fuera.filter(f => f._cancelled).length,
      explicadas: enCiudades.filter(f => f._cancelExplained).length,
      banners: document.querySelectorAll('.notice-banner').length,
      bannerTexto: document.querySelector('.notice-banner')?.textContent || '',
      enlace: document.querySelector('.notice-banner a')?.href || '',
      // La promesa falsa no puede aparecer en ninguna card.
      promesaFecha: [...document.querySelectorAll('.notice-detail-amber')].filter(e => /Pendiente nueva fecha/i.test(e.textContent)).length,
    };
  }, CIUDADES);
  expect(m.totalDentro).toBeGreaterThan(50);          // el caso real: 88 funciones
  expect(m.selladasDentro).toBe(m.totalDentro);        // TODAS las de esas ciudades
  expect(m.selladasFuera).toBe(0);                     // y NINGUNA de las otras
  expect(m.explicadas).toBe(m.totalDentro);
  expect(m.banners).toBe(1);                           // UN banner, no 88
  expect(m.bannerTexto).toContain('por el sismo');
  expect(m.enlace).toContain('instagram.com');
  expect(m.promesaFecha).toBe(0);                      // no se promete fecha
  // Una cancelada no ofrece SERVICIOS: ni boleta, ni inscripción, ni Q&A. Visto en
  // producción el día que FICDEH abrió: la card de Quibdó decía «CANCELADA» y al
  // lado «CON BOLETA» — le ofrecía entrada a una función suspendida por el sismo.
  const servicios = await page.evaluate(async () => {
    const { state } = await import('/src/state/state.js');
    const { _metaBadges } = await import('/src/view/helpers.js');
    const canc = state.snapshot().FILMS.filter(f => f._cancelled);
    return { total: canc.length, conBadge: canc.filter(f => _metaBadges(f) !== '').length,
             enPantalla: [...document.querySelectorAll('.plist-item, .poster-card')]
               .filter(el => /CANCELADA/i.test(el.textContent) && /CON BOLETA|INSCRIPCIÓN|Q&A/i.test(el.textContent)).length };
  });
  expect(servicios.total).toBeGreaterThan(50);
  expect(servicios.conBadge).toBe(0);      // el dueño (_metaBadges) no los emite
  expect(servicios.enPantalla).toBe(0);    // y ninguna card los muestra
});

// AP04 — la marca de CANCELADA solo cuando es verdad para TODA la obra (regla de
// Juan, 11 ago 2026). Tras el sismo, de las 116 obras de FICDEH: 10 quedaron sin
// ninguna función viva, 39 son PARCIALES («La gran hazaña»: 4 canceladas, 12
// activas). Marcar las 39 sería falso y empujaría a descartar películas que SÍ se
// pueden ver. Y en Modo Recuerdo la cancelada aparece —borrarla sería otra forma
// de mentir— pero sin ofrecer «Vista»: no se califica lo que no ocurrió.
test('AP04 — cancelada por obra: marca solo las totales, y el Diario no ofrece Vista', async ({ page }) => {
  await page.clock.install({ time: new Date('2026-08-14T10:00:00-05:00') });
  await page.goto('/');
  await page.waitForSelector('html[data-app-ready="1"]', { state: 'attached', timeout: 15000 });
  await page.waitForSelector('.splash-card[data-fest="ficdeh2026"]', { timeout: 15000 });
  await page.evaluate(() => { const c = FESTIVAL_CONFIG['ficdeh2026']; selectSplashFest(c.name, `${c.city} · ${c.dates}`, 'ficdeh2026'); });
  await page.locator('.splash-enter-btn').click();
  await page.waitForFunction(() => document.querySelectorAll('.poster-card, .plist-item').length > 0, null, { timeout: 20000 });
  const g = await page.evaluate(() => {
    const porObra = {};
    FILMS.forEach(f => { (porObra[f.title] = porObra[f.title] || []).push(f); });
    const obras = Object.entries(porObra);
    const totales = obras.filter(([, fs]) => fs.every(x => x._cancelled));
    const parciales = obras.filter(([, fs]) => fs.some(x => x._cancelled) && !fs.every(x => x._cancelled));
    const marcadas = [...document.querySelectorAll('.poster-card')]
      .filter(c => /CANCELADA/i.test(c.textContent)).map(c => c.dataset.title);
    return {
      obras: obras.length, totales: totales.map(([t]) => t), parciales: parciales.length,
      marcadasEnTodo: marcadas.length,
      // Ni una parcial puede aparecer marcada.
      parcialMarcada: parciales.filter(([t]) => marcadas.includes(t)).length,
      totalSinMarca: totales.filter(([t]) => !marcadas.includes(t)).length,
    };
  });
  expect(g.totales.length).toBeGreaterThan(0);   // el caso real: 10
  expect(g.parciales).toBeGreaterThan(20);       // el caso real: 39
  expect(g.parcialMarcada).toBe(0);              // NINGUNA parcial marcada
  expect(g.totalSinMarca).toBe(0);               // TODAS las totales, marcadas
  // ── Modo Recuerdo: aparece, marcada, y SIN botón «Vista» ──
  const d = await page.evaluate(async (titulo) => {
    const { state } = await import('/src/state/state.js');
    toggleWL(titulo);
    const viva = state.snapshot().FILMS.find(f => !f._cancelled && f.day && f.time);
    toggleWL(viva.title);
    globalThis._simTime = '2026-08-21T12:00';   // festival TERMINADO → Modo Recuerdo
    switchMainNav('mnav-seleccion'); showAgView();
    await new Promise(r => requestAnimationFrame(r));
    const v = document.getElementById('ag-view');
    const fila = [...v.querySelectorAll('.saved-item')].find(e => e.textContent.includes(titulo.slice(0, 20)));
    const filaViva = [...v.querySelectorAll('.saved-item')].find(e => e.textContent.includes(viva.title.slice(0, 20)));
    return {
      apareceCancelada: !!fila,
      marcada: !!fila && /CANCELADA/i.test(fila.textContent),
      ofreceVista: !!fila && !!fila.querySelector('[data-action="toggleWatched"]'),
      vivaOfreceVista: !!filaViva && !!filaViva.querySelector('[data-action="toggleWatched"]'),
    };
  }, g.totales[0]);
  expect(d.apareceCancelada).toBe(true);   // no se borra: sería otra forma de mentir
  expect(d.marcada).toBe(true);
  expect(d.ofreceVista).toBe(false);       // no se califica lo que no ocurrió
  expect(d.vivaOfreceVista).toBe(true);    // y la que sí ocurrió, sigue calificable
});

// AP05 — badge PREMIUM: la función cuesta más y hay que decirlo. TIFF marca 61 de
// sus 638 funciones (galas del Roy Thomson, Princess of Wales, Royal Alexandra y
// dos sedes más), y 55 OBRAS tienen funciones premium y normales a la vez: sin el
// badge, alguien planea su día, va a comprar y se encuentra otro precio — y lo
// habría llevado ahí la app. Se prueba en el DUEÑO (_metaBadges), que es donde
// vive la regla, y con el caso de orden que importa: una cancelada no anuncia que
// es cara. Hoy no hay ninguna premium cancelada en TIFF; el orden vale para
// cuando la haya.
test('AP05 — PREMIUM se anuncia, salvo si la función está cancelada', async ({ page }) => {
  await page.goto('/');
  await page.waitForSelector('html[data-app-ready="1"]', { state: 'attached', timeout: 15000 });
  const r = await page.evaluate(async () => {
    const { _metaBadges } = await import('/src/view/helpers.js');
    const txt = o => _metaBadges(o).replace(/<[^>]*>/g, '·');
    return {
      premium:            txt({ premium: true }),
      normal:             txt({ premium: false }),
      sinCampo:           txt({}),
      premiumCancelada:   txt({ premium: true, _cancelled: true }),
      premiumConQA:       txt({ premium: true, has_qa: true }),
      // `premium: 'true'` (string) NO cuenta: el dato es booleano y un truthy
      // accidental no debe pintar un badge de precio.
      premiumString:      txt({ premium: 'true' }),
    };
  });
  expect(r.premium).toContain('PREMIUM');
  expect(r.normal).not.toContain('PREMIUM');
  expect(r.sinCampo).not.toContain('PREMIUM');
  // El badge de ESTADO manda sobre los de SERVICIO: si no va a ocurrir, no hay
  // nada que ofrecer — ni siquiera decir que era cara.
  expect(r.premiumCancelada).toBe('');
  // Convive con los demás, y va PRIMERO: es lo único que cambia el precio.
  expect(r.premiumConQA).toContain('PREMIUM');
  expect(r.premiumConQA).toContain('Q&A');
  expect(r.premiumConQA.indexOf('PREMIUM')).toBeLessThan(r.premiumConQA.indexOf('Q&A'));
  expect(r.premiumString).not.toContain('PREMIUM');
});

// PC01 — el plan NO cruza ciudades (QA de ojos frescos, 15 ago 2026). El caso
// real: filtro Bogotá en FICDEH, watchlist con obras que existen en Bogotá Y en
// otras ciudades, «Calcular mi Plan» → el plan ponía al usuario en Medellín el
// domingo y en Ibagué el lunes, sin ciudad visible en las filas. Ahora: con
// filtro de ciudad, CADA función del plan y CADA sugerencia es de esa ciudad.
test('PC01 — con filtro Bogotá, el plan y las sugerencias no salen de Bogotá', async ({ page }) => {
  test.setTimeout(90000);
  await page.clock.install({ time: new Date('2026-08-15T09:00:00-05:00') });
  await page.goto('/');
  await page.waitForSelector('html[data-app-ready="1"]', { state: 'attached', timeout: 15000 });
  await page.waitForSelector('.splash-card[data-fest="ficdeh2026"]', { timeout: 15000 });
  await page.evaluate(() => { const c = FESTIVAL_CONFIG['ficdeh2026']; selectSplashFest(c.name, `${c.city} · ${c.dates}`, 'ficdeh2026'); });
  await page.locator('.splash-enter-btn').click();
  await page.waitForFunction(() => document.querySelectorAll('.poster-card, .plist-item').length > 0, null, { timeout: 20000 });
  await page.waitForTimeout(600);
  const r = await page.evaluate(async () => {
    const { state } = await import('/src/state/state.js');
    const { vcfg } = await import('/src/view/helpers.js');
    const { computeScenarios } = await import('/src/domain/schedule.js');
    const { _planCityVenues } = await import('/src/controller/calc.js');
    const { getSuggestions } = await import('/src/view/agenda.js');
    const city = f => (vcfg(f.venue) || {}).city || '';
    const { FILMS } = state.snapshot();
    // Watchlist como la del agente: obras con función en Bogotá Y en otras ciudades.
    const mixtas = [...new Set(FILMS.filter(f => city(f) === 'Bogotá' && f.day >= '2026-08-16')
      .map(f => f.title))].filter(t => FILMS.some(f => f.title === t && city(f) && city(f) !== 'Bogotá')).slice(0, 6);
    mixtas.forEach(t => toggleWL(t));
    // Filtro de ciudad ACTIVO — el camino real lo setea el dropdown; acá el estado.
    globalThis.activeVenue = 'city:Bogotá';
    globalThis.PLAN_CITY_VENUES = _planCityVenues();
    const scenarios = computeScenarios([...state.snapshot().watchlist]);
    const funciones = scenarios.flatMap(sc => sc.schedule || sc.items || sc);
    const ciudades = [...new Set(funciones.map(f => city(f.venue ? f : f)).filter(Boolean))];
    // Y las sugerencias sobre un plan guardado en Bogotá:
    const bog = FILMS.find(f => city(f) === 'Bogotá' && f.day === '2026-08-16' && f.time);
    state.set('savedAgenda', { schedule: [{ ...bog, _title: bog.title }] });
    const sug = getSuggestions();
    const sugCiudades = [...new Set(Object.values(sug).flat().map(s => city(s)).filter(Boolean))];
    return { mixtas: mixtas.length, escenarios: scenarios.length, funciones: funciones.length,
             ciudadesEnPlan: ciudades, ciudadesEnSugerencias: sugCiudades };
  });
  expect(r.mixtas).toBeGreaterThan(2);            // el caso existe de verdad
  expect(r.escenarios).toBeGreaterThan(0);        // el plan se calcula
  expect(r.funciones).toBeGreaterThan(0);
  expect(r.ciudadesEnPlan).toEqual(['Bogotá']);   // NI UNA función de otra ciudad
  expect(r.ciudadesEnSugerencias.every(c => c === 'Bogotá')).toBe(true);
});

// Ronda 3 (FINCA): con 3 festivales en curso el splash pedía elegir CADA vez —
// el auditor elegía FICDEH, recargaba y volvía al punto cero. La regla del 5 jul
// (0 o 2+ en curso → el usuario elige) decide la PRIMERA visita; no dice nada
// sobre recordar lo ya elegido. La memoria persiste en el dispositivo y caduca
// sola: si el festival recordado terminó, se vuelve a preguntar.
test('P09 — el splash recuerda el festival elegido, y lo olvida cuando terminó', async ({ page }) => {
  const estado = () => page.evaluate(() => ({
    on: document.querySelector('.splash-card.on')?.dataset.fest || null,
    entrar: document.getElementById('splash-enter-btn')?.disabled ? 'disabled' : 'habilitado',
    guardado: localStorage.getItem('otrofestiv_festival'),
  }));

  // El festival se elige EN TIEMPO DE EJECUCIÓN, no a mano. Antes era
  // 'ficdeh2026' fijo, y el test caducó solo cuando FICDEH terminó (19 AGO
  // 2026): la app olvida a propósito los festivales terminados —es justo lo
  // que la segunda mitad de este test comprueba— así que el propio caso se
  // contradecía. Se necesita uno VIGENTE, y cuál sea depende del día.
  await page.goto('/');
  await page.waitForSelector('html[data-app-ready="1"]', { state: 'attached', timeout: 15000 });
  const elegido = await page.evaluate(() => {
    const vivos = Object.entries(FESTIVAL_CONFIG).filter(([, c]) =>
      c.name && c.group !== 'test' && c.festivalEndStr && new Date(c.festivalEndStr) > new Date());
    return vivos.length ? vivos[0][0] : null;
  });
  expect(elegido, 'hace falta al menos un festival vigente para este caso').not.toBeNull();

  await enterFestival(page, elegido);
  expect((await estado()).guardado, 'entrar guarda la elección').toBe(elegido);

  // El splash SIGUE apareciendo — solo llega con la elección puesta.
  await page.reload();
  await page.waitForSelector('.splash-card');
  await page.waitForTimeout(800);
  const vuelta = await estado();
  expect(await page.locator('#otrofestiv-splash').isVisible(), 'el splash no se salta').toBe(true);
  expect(vuelta.on, 'preselecciona lo recordado').toBe(elegido);
  expect(vuelta.entrar, 'y «Entrar» queda habilitado').toBe('habilitado');

  // Caduca sola: un festival ya terminado no se preselecciona ni sobrevive.
  await page.evaluate(() => localStorage.setItem('otrofestiv_festival', 'ficci65'));
  await page.reload();
  await page.waitForSelector('.splash-card');
  await page.waitForTimeout(800);
  const caducado = await estado();
  // Lo invariante es que el terminado NO sobrevive: ni queda seleccionado ni
  // queda en memoria. Antes se comprobaba «Entrar» disabled, y eso solo vale
  // cuando NO hay exactamente un festival en curso: si lo hay, al olvidar el
  // viejo entra la OTRA regla —preselección automática del único vigente— y
  // «Entrar» queda habilitado con razón. Son dos reglas distintas y cada una
  // tiene su caso; mezclarlas hacía que este fallara según el día.
  expect(caducado.on, 'el terminado no queda seleccionado').not.toBe('ficci65');
  expect(caducado.guardado, 'y la memoria se limpia sola').toBeNull();
});
