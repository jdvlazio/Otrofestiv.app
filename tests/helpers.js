// @ts-check
// ─────────────────────────────────────────────────────────────────────────────
// helpers.js — Shared utilities for Otrofestiv test suite
// Fuente única de verdad para helpers, constantes y fixtures reutilizables.
// ─────────────────────────────────────────────────────────────────────────────

const LEVIZA_SIMTIME = '2026-05-14T00:00:00-05:00';

async function selectFestival(page, festId) {
  // Selección DETERMINISTA vía selectSplashFest (no via gesto de scroll del riel).
  // Este es un helper de SETUP — su objetivo es entrar al festival, no probar la
  // UI del selector-carrusel (eso lo cubre festivals.spec.js con click real sobre
  // .splash-card). Ir directo a selectSplashFest elimina la race del scroll-snap.
  await page.evaluate((id) => {
    const cfg = FESTIVAL_CONFIG[id] || {};
    const meta = `${cfg.city} · ${cfg.dates} ${cfg.year || ''}`.trim();
    selectSplashFest(cfg.name, meta, id);
  }, festId);
  await page.waitForTimeout(100);
}

async function enterFestival(page, festId, simTime) {
  await page.goto('/');
  // Gate de readiness JS DEFINITIVO: el marcador [data-app-ready="1"] se setea al
  // FINAL del bootstrap síncrono (main.js) — módulo evaluado, STATE/TEST BRIDGE
  // instalado (FESTIVAL_CONFIG/selectSplashFest expuestos en globalThis), listener
  // delegado adjunto, render inicial hecho. El proxy anterior (.splash-card
  // attached) se renderiza ANTES del bridge → bajo runners lentos de CI, evaluate
  // veía "FESTIVAL_CONFIG is not defined". appReady cierra esa ventana de forma
  // garantizada.
  await page.waitForSelector('html[data-app-ready="1"]', { state: 'attached', timeout: 15000 });

  // Gate extra para WebKit (motor de iOS, más lento en arrancar que Blink): el
  // marcador data-app-ready se setea al cerrar el bootstrap síncrono, pero bajo
  // WebKit el TEST BRIDGE (FESTIVAL_CONFIG/selectSplashFest en globalThis) puede
  // aún no estar visible para el primer evaluate → "FESTIVAL_CONFIG is not
  // defined". Esperar a que ambos símbolos existan cierra esa ventana sin un
  // timeout fijo (probado: elimina el race bajo el proyecto ios-mobile).
  await page.waitForFunction(
    () => typeof FESTIVAL_CONFIG !== 'undefined' && typeof selectSplashFest === 'function',
    null,
    { timeout: 15000 }
  );

  // Selección determinista del festival objetivo (independiente de la preselección
  // del riel: con 1 solo festival en curso viene preseleccionado, con 0/2+ no).
  await selectFestival(page, festId);

  await page.locator('.splash-enter-btn').click();
  await page.waitForSelector('.poster-card, .plist-item, .dtab', { timeout: 15000 });

  if (simTime) {
    await page.evaluate((t) => {
      _simTime = t;
      const ts = simTodayStr();
      const ni = DAY_KEYS.findIndex(d => FESTIVAL_DATES[d] === ts);
      if (ni >= 0) {
        activeDay = DAY_KEYS[ni];
        programaViewMode = 'list';
      } else {
        activeDay = 'all';
        programaViewMode = 'grid';
      }
      _renderProgramaContent && _renderProgramaContent();
    }, simTime);
  }
}

async function freezeSimTime(page, isoStr) {
  await page.evaluate((t) => { _simTime = t; }, isoStr);
}

async function addToWatchlist(page, title) {
  await page.evaluate((t) => {
    watchlist.clear();
    watchlist.add(t);
    if (typeof saveState === 'function') saveState('wl', 'watched');
  }, title);
}

async function goToPlanear(page) {
  await page.evaluate(() => {
    cachedResult = null;
    savedAgenda = null;
    switchMainNav('mnav-planner');
    showAgView();
  });
  await page.waitForSelector('.av-calc-btn', { timeout: 8000 });
}

module.exports = { LEVIZA_SIMTIME, enterFestival, freezeSimTime, addToWatchlist, goToPlanear };
