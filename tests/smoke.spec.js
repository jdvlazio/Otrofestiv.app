// @ts-check
// smoke.spec.js — Checks críticos: si alguno falla, nada más importa.
// Criterio: ¿la app carga? ¿los tabs responden? ¿hay datos de films?
const { test, expect } = require('@playwright/test');
const { LEVIZA_SIMTIME, enterFestival } = require('./helpers');

// T34 — App carga sin errores JS en consola
test('T34 — carga inicial sin errores JS', async ({ page }) => {
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  const realErrors = errors.filter(e =>
    !e.includes('extension') && !e.includes('chrome-extension') && !e.includes('sentry')
  );
  expect(realErrors).toHaveLength(0);
});

// T35 — App carga sin errores JS en Tribeca
test('T35 — carga Tribeca sin errores JS', async ({ page }) => {
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await enterFestival(page, 'tribeca2026');
  const realErrors = errors.filter(e =>
    !e.includes('extension') && !e.includes('chrome-extension') && !e.includes('sentry')
  );
  expect(realErrors).toHaveLength(0);
});

// T32 — Nav: cambio entre los 4 tabs funciona sin errores JS
test('T32 — navegar entre los 4 tabs no lanza errores', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  for (const [nav, needsAg] of [['mnav-seleccion',true],['mnav-planner',true],['mnav-miplan',false],['mnav-cartelera',false]]) {
    await page.evaluate(([n, ag]) => { switchMainNav(n); if(ag) showAgView(); }, [nav, needsAg]);
    await page.waitForTimeout(400);
  }
  expect(errors).toHaveLength(0);
});

// T38 — Festival: JSON de festival carga con films
test('T38 — JSON del festival tiene films', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  const filmCount = await page.evaluate(() => typeof FILMS !== 'undefined' ? FILMS.length : 0);
  expect(filmCount).toBeGreaterThan(0);
});

// ── T136 — sin sesión, la app no pide lo que no puede leer ───────────────────
// Cada carga de festival disparaba un 401 a screening_reports. Medido contra la
// base: el rol `anon` NO tiene GRANT de SELECT sobre esa tabla —el error es
// 42501 «permission denied for table», que es un grant faltante y no una RLS
// que filtra—, así que la petición estaba condenada antes de salir.
//
// Peor que el ruido: `const {data} = await …` descartaba el error, y supabase-js
// RESUELVE en vez de lanzar, así que un permiso denegado se veía exactamente
// igual que «no hay reportes». La feature de retraso colaborativo quedaba muda
// sin que nadie se enterara.
//
// Se cuenta el TRÁFICO REAL de la app a Supabase, no el estado interno: el
// hallazgo era una petición que sale, y eso es lo que hay que ver salir.
test('T136 — un visitante sin sesión no dispara peticiones a Supabase', async ({ page }) => {
  const aSupabase = [];
  page.on('response', r => {
    const u = r.url();
    if (u.includes('supabase.co') && u.includes('/rest/')) {
      aSupabase.push({ status: r.status(), tabla: u.includes('screening_reports') ? 'screening_reports' : u.slice(-40) });
    }
  });
  await enterFestival(page, 'cinemancia2026', '2026-09-04T10:00:00-05:00');
  await page.waitForTimeout(3000);
  const conSesion = await page.evaluate(() => !!(typeof _sbUser !== 'undefined' && _sbUser));
  expect(conSesion, 'el visitante del test no tiene sesión — es el caso del bug').toBe(false);
  expect(aSupabase, 'sin sesión no se pide nada al REST de Supabase').toEqual([]);
});
