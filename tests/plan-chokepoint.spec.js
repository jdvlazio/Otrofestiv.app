// @ts-check
// plan-chokepoint.spec.js — commitPlan: el único camino de mutación del plan.
//
// PR 2 del plan de confiabilidad: toda escritura de savedAgenda pasa por
// commitPlan, que certifica con verifyPlan (el mismo del oráculo). Doctrina de
// severidad: en producción REPORTA y deja pasar (un plan raro no brickea al
// usuario); con __PLAN_STRICT__ (tests) TIRA — un flujo que produce un plan
// inválido es un bug que el CI tiene que ver. El guardián
// [plan-write-chokepoint] veta escritores nuevos fuera del chokepoint.
const { test, expect } = require('@playwright/test');
const { enterFestival, addToWatchlist, goToPlanear, esperarCalculo } = require('./helpers');

test('CH01 — strict: un plan con conflicto real NO puede commitearse', async ({ page }) => {
  await enterFestival(page, 'finca2026', '2026-08-12T10:00');
  const r = await page.evaluate(() => {
    globalThis.__PLAN_STRICT__ = true;
    const f = d => FILMS.find(fi => fi.title === 'Toroboro: el nombre de las plantas' && fi.day === d) ||
                   FILMS.filter(fi => !fi.info && fi.day)[d === 0 ? 0 : 1];
    // dos funciones del MISMO día y hora en sedes distintas = conflicto seguro
    const a = FILMS.find(fi => !fi.info && fi.day && fi.time);
    const b = { ...a, title: 'OTRA', venue: Object.keys(FESTIVAL_CONFIG[_activeFestId].venues || {})[1] || a.venue };
    try {
      commitPlan(() => ({ schedule: [{ ...a, _title: a.title }, { ...b, _title: 'OTRA' }] }));
      return { threw: false, plan: !!savedAgenda };
    } catch (e) {
      return { threw: true, msg: String(e.message).slice(0, 60), plan: savedAgenda };
    } finally { delete globalThis.__PLAN_STRICT__; }
  });
  expect(r.threw).toBe(true);
  expect(r.msg).toContain('plan inválido');
  expect(r.plan).toBe(null); // el estado NO se tocó
});

test('CH02 — prod: el mismo commit inválido pasa con reporte, sin brickear', async ({ page }) => {
  await enterFestival(page, 'finca2026', '2026-08-12T10:00');
  const r = await page.evaluate(() => {
    const reported = [];
    const _sentry = window.Sentry;
    window.Sentry = { captureException: (e) => reported.push(String(e.message)) };
    const a = FILMS.find(fi => !fi.info && fi.day && fi.time);
    const b = { ...a, title: 'OTRA' };
    commitPlan(() => ({ schedule: [{ ...a, _title: a.title }, { ...b, _title: 'OTRA' }] }));
    window.Sentry = _sentry;
    return { escrito: savedAgenda.schedule.length, reportes: reported.filter(m => m.includes('plan inválido')).length };
  });
  expect(r.escrito).toBe(2);        // el dato manda — no se pierde nada
  expect(r.reportes).toBe(1);       // y el radar avisó
});

test('CH03 — strict: los flujos REALES de la app commitean limpio de punta a punta', async ({ page }) => {
  await enterFestival(page, 'finca2026', '2026-08-12T10:00');
  await page.evaluate(() => { globalThis.__PLAN_STRICT__ = true; });
  // planear → usar plan → añadir sugerencia → quitar: todos pasan por commitPlan
  await addToWatchlist(page, 'Ziki');
  await page.evaluate(() => { watchlist.add('Yurlu'); saveState('wl', 'watched'); });
  await goToPlanear(page);
  await page.locator('.av-calc-btn').click();
  await esperarCalculo(page);
  const ok = await page.evaluate(() => {
    const sc = cachedResult && cachedResult.scenarios && cachedResult.scenarios[0];
    if (!sc) return false;
    commitPlan(() => ({ schedule: sc.schedule, scenarioIdx: 0 }));
    // añadir por el handler real (pasa por commitPlan, strict activo)
    const extra = FILMS.find(f => f.title === 'Toroboro: el nombre de las plantas');
    if (extra) addSuggestion(extra.title, extra.day, extra.time);
    switchMainNav('mnav-miplan'); showAgView();
    const idx = DAY_KEYS.indexOf('2026-08-13'); if (idx >= 0) { activeMiPlanDay = idx; renderAgenda(); }
    return true;
  });
  expect(ok).toBe(true);
  // quitar por la UI REAL: botón de la fila → modal → confirmar (→ _dropFromPlan → commitPlan)
  // click() nativo del DOM: dispara el listener delegado real (algo intercepta el
  // hit-test de Playwright en este layout — el evento y el handler son los mismos)
  await page.waitForSelector('.ag-fi-btn.del', { state: 'attached', timeout: 8000 });
  await page.evaluate(() => { document.querySelector('.ag-fi-btn.del').click(); });
  await page.waitForSelector('#cm-ok', { timeout: 5000 });
  await page.evaluate(() => { document.getElementById('cm-ok').click(); });
  await page.waitForTimeout(400);
  const r = await page.evaluate(() => ({ n: (savedAgenda && savedAgenda.schedule.length) || 0, strict: !!globalThis.__PLAN_STRICT__ }));
  expect(r.strict).toBe(true);          // strict estuvo activo durante TODO el flujo
  expect(r.n).toBeGreaterThan(0);       // y ninguna mutación real lo hizo tirar
});
