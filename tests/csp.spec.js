// @ts-check
// csp.spec.js — la app corre ENTERA con la CSP estricta (26 oct 2026): script-src
// sin 'unsafe-inline' ni 'unsafe-eval'. Cualquier script, handler o eval que el
// navegador bloquee dispara `securitypolicyviolation`: se juntan todos y el test
// exige cero a lo largo de un recorrido real (splash, festival, fichas, buscador,
// cálculo del plan en el worker, Mi Plan, cuenta, palmarés y diario).
const { test, expect } = require('@playwright/test');
const { enterFestival } = require('./helpers');

async function vigilar(page) {
  await page.addInitScript(() => {
    window.__csp = [];
    document.addEventListener('securitypolicyviolation', e =>
      window.__csp.push(`${e.violatedDirective} ← ${e.blockedURI || 'inline'} @${(e.sourceFile || '').split('/').pop()}:${e.lineNumber}`));
  });
}

test('CSP01 — la CSP del <meta> es la estricta', async ({ page }) => {
  await page.goto('/');
  const csp = await page.evaluate(() => document.querySelector('meta[http-equiv="Content-Security-Policy"]').content);
  const src = (csp.match(/script-src ([^;]*)/) || [])[1] || '';
  expect(src).not.toContain("'unsafe-inline'");
  expect(src).not.toContain("'unsafe-eval'");
  expect(src).toMatch(/'sha256-/);
});

test('CSP02 — recorrido completo sin una sola violación de CSP', async ({ page }) => {
  await vigilar(page);
  await enterFestival(page, 'ficdeh2026', '2026-08-11T12:00:00-05:00');
  await page.evaluate(async () => {
    const espera = ms => new Promise(r => setTimeout(r, ms));
    const vivas = [...new Set(FILMS.filter(f => f.day && f.time && !f.info && !f._cancelled).map(f => f.title))];
    // ficha
    document.querySelector('.js-open-pel, [data-action="openPeliSheet"]')?.click(); await espera(400);
    // buscador
    searchOpen(); await espera(200);
    const inp = document.getElementById('search-input'); inp.value = 'a'; inp.dispatchEvent(new Event('input', { bubbles: true })); await espera(300);
    searchClose();
    // cálculo del plan en el WORKER (antes armado con eval)
    state.set('watchlist', new Set(vivas.slice(0, 8))); cachedResult = null; runCalc(); await espera(3500);
    // cuenta
    openAuthSheet(); await espera(300); closeAuthSheet();
    // Mi Plan, diario y palmarés (por el registro de acciones: lo que usa la UI)
    switchMainNav('mnav-miplan'); await espera(500);
    ACTION_REGISTRY.openDiary(); await espera(400); ACTION_REGISTRY.closeDiary && ACTION_REGISTRY.closeDiary();
    ACTION_REGISTRY.openPalmares(); await espera(400); ACTION_REGISTRY.closePalmares && ACTION_REGISTRY.closePalmares();
  });
  const v = await page.evaluate(() => window.__csp);
  const calc = await page.evaluate(() => !!(cachedResult && cachedResult.scenarios && cachedResult.scenarios.length));
  expect(calc, 'el worker calculó').toBe(true);
  expect(v, 'violaciones de CSP').toEqual([]);
});
