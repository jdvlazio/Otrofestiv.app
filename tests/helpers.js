// @ts-check
// ─────────────────────────────────────────────────────────────────────────────
// helpers.js — Shared utilities for Otrofestiv test suite
// Fuente única de verdad para helpers, constantes y fixtures reutilizables.
// ─────────────────────────────────────────────────────────────────────────────

const LEVIZA_SIMTIME = '2026-05-14T00:00:00-05:00';

async function selectFestival(page, festId) {
  await page.locator('#splash-sel-btn').click();
  await page.waitForSelector('#splash-dropdown', { state: 'visible', timeout: 5000 });
  // Si el item está en "Anteriores" puede estar colapsado — expandirlo primero
  const item = page.locator(`.splash-drop-item[data-fest="${festId}"]`);
  const isPast = await item.evaluate(el => el.classList.contains('past')).catch(() => false);
  if (isPast) {
    await item.click(); // primer click expande el past-item
    await page.waitForTimeout(200);
    // segundo click confirma la selección (si _togglePastFest requiere doble acción)
    // o bien usamos evaluate para forzar la selección directamente
    await page.evaluate((id) => {
      const cfg = FESTIVAL_CONFIG[id] || {};
      const meta = `${cfg.city} · ${cfg.dates} ${cfg.year||''}`.trim();
      selectSplashFest(cfg.name, meta, id);
    }, festId);
  } else {
    await item.click();
  }
  await page.waitForTimeout(300);
}

async function enterFestival(page, festId, simTime) {
  await page.goto('/');
  await page.waitForSelector('#splash-sel-btn', { timeout: 15000 });

  const selName = await page.locator('#splash-sel-name').textContent().catch(() => '');
  if (!selName.toLowerCase().includes(festId.replace(/\d+/g, '').toLowerCase())) {
    await selectFestival(page, festId);
  }

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
