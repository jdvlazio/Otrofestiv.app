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
    const ids = [...document.querySelectorAll('.splash-card[data-fest]')].map(c => c.dataset.fest);
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
      dividerPresent: !!document.querySelector('.splash-rail-div'),
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
  await page.goto('/');
  await page.waitForSelector('html[data-app-ready="1"]', { state: 'attached', timeout: 15000 });
  await page.waitForSelector('.splash-card[data-fest]', { state: 'attached', timeout: 15000 });
  // Estado inicial en 2 festivales en curso: sin preselección, "Entrar" disabled.
  const before = await page.evaluate(() => ({
    on: document.querySelector('.splash-card.on')?.dataset.fest || null,
    disabled: document.getElementById('splash-enter-btn').disabled,
  }));
  // Scroll PROGRAMÁTICO (sin pointerdown/touchstart) → dispara 'scroll' pero el gate
  // no está armado → no debe seleccionar nada tras el debounce.
  const afterProgrammatic = await page.evaluate(async () => {
    const rail = document.getElementById('splash-rail');
    rail.scrollLeft = rail.scrollWidth; // centra otra card
    rail.dispatchEvent(new Event('scroll'));
    await new Promise(r => setTimeout(r, 200)); // > 90ms del debounce
    return {
      on: document.querySelector('.splash-card.on')?.dataset.fest || null,
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
      on: document.querySelector('.splash-card.on')?.dataset.fest || null,
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
