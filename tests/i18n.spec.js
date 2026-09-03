// @ts-check
// i18n.spec.js — Cambio de idioma ES ↔ EN: botones, strings críticos, persistencia.
const { test, expect } = require('@playwright/test');
const { LEVIZA_SIMTIME, enterFestival } = require('./helpers');

// Abre el dropdown de idioma (las opciones están ocultas hasta abrir el trigger).
async function openLangDropdown(page) {
  await page.locator('#lang-trigger').click();
  await expect(page.locator('#lang-btn-en')).toBeVisible({ timeout: 3000 });
}

// I01 — Selector de idioma presente; al abrir muestra opciones ES y EN
test('I01 — selector de idioma con opciones ES y EN', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await expect(page.locator('#lang-trigger')).toBeVisible({ timeout: 5000 });
  await openLangDropdown(page);
  await expect(page.locator('#lang-btn-es')).toBeVisible();
  await expect(page.locator('#lang-btn-en')).toBeVisible();
});

// I02 — Cambiar a EN activa el botón EN y desactiva ES
test('I02 — cambiar a EN activa el botón correcto', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await openLangDropdown(page);
  await page.locator('#lang-btn-en').click();
  await page.waitForFunction(() => document.getElementById('lang-btn-en')?.classList.contains('on'), { timeout: 3000 });
  const enActive = await page.locator('#lang-btn-en.on').count();
  const esActive = await page.locator('#lang-btn-es.on').count();
  expect(enActive).toBe(1);
  expect(esActive).toBe(0);
});

// I03 — En EN los tabs del nav muestran texto en inglés
test('I03 — tabs en EN muestran texto inglés', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await openLangDropdown(page);
  await page.locator('#lang-btn-en').click();
  await page.waitForFunction(() => document.getElementById('lang-btn-en')?.classList.contains('on'), { timeout: 3000 });
  const navText = await page.locator('.main-nav-tab').allTextContents();
  const joined = navText.join(' ').toUpperCase();
  // En inglés debe haber alguno de estos strings
  expect(joined).toMatch(/INTERESTS|PLANNER|MY PLAN|PROGRAM/);
});

// I04 — Volver a ES restaura strings en español
test('I04 — volver a ES restaura strings español', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await openLangDropdown(page);
  await page.locator('#lang-btn-en').click();
  await page.waitForFunction(() => document.getElementById('lang-btn-en')?.classList.contains('on'), { timeout: 3000 });
  await openLangDropdown(page);
  await page.locator('#lang-btn-es').click();
  await page.waitForFunction(() => document.getElementById('lang-btn-es')?.classList.contains('on'), { timeout: 3000 });
  const navText = await page.locator('.main-nav-tab').allTextContents();
  const joined = navText.join(' ').toUpperCase();
  expect(joined).toMatch(/INTERESES|PLANEAR|MI PLAN|PROGRAMA/);
});

// I05 — Cambio de idioma no lanza errores JS
test('I05 — cambio de idioma sin errores JS', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await openLangDropdown(page);
  await page.locator('#lang-btn-en').click();
  await page.waitForFunction(() => document.getElementById('lang-btn-en')?.classList.contains('on'), { timeout: 3000 });
  await openLangDropdown(page);
  await page.locator('#lang-btn-es').click();
  await page.waitForFunction(() => document.getElementById('lang-btn-es')?.classList.contains('on'), { timeout: 3000 });
  await page.waitForTimeout(200);
  expect(errors).toHaveLength(0);
});

// ── I06 — al cambiar de idioma, el encabezado también cambia de fecha ────────
// El chip del encabezado se llenaba INLINE dentro de loadFestival, así que solo
// se pintaba al cargar un festival: cambiar el idioma no lo tocaba. En inglés el
// selector decía «SEP 3–12» (dates_en) y el encabezado seguía en «3–12 SEP» —la
// misma fecha en dos órdenes, a dos toques de distancia—. Es la misma trampa que
// ya tenía resuelta renderPostponedBanner, que persiste y por eso setLang la
// rehornea; el chip no estaba en esa lista.
//
// Se comparan las DOS superficies entre sí y contra el config: que el encabezado
// diga lo del idioma actual, y que en español no se haya movido.
test('I06 — el encabezado usa las fechas del idioma activo', async ({ page }) => {
  await enterFestival(page, 'cinemancia2026');
  const r = await page.evaluate(async () => {
    const w = ms => new Promise(r => setTimeout(r, ms));
    const tap = (a, ds) => { const b = document.createElement('button'); b.setAttribute('data-action', a);
      Object.keys(ds || {}).forEach(k => b.setAttribute('data-' + k, ds[k]));
      document.body.appendChild(b); b.click(); b.remove(); };
    tap('closeCitySheet');
    await w(500);
    const cfg = FESTIVAL_CONFIG[_activeFestId] || {};
    const topbar = () => { const e = document.querySelector('.hdr-fest-dates'); return e ? e.textContent.trim() : null; };
    const es = topbar();
    tap('selectLang', { code: 'en' });
    await w(1400);
    const en = topbar();
    tap('openFestivalSheet');
    await w(900);
    const info = document.querySelector('#fs-info .splash-info-dates');
    return { es, en, selectorEn: info ? info.textContent.trim() : null,
      dates: cfg.dates, datesEn: cfg.dates_en };
  });
  expect(r.datesEn, 'el festival del test declara fechas en inglés — si no, no distingue').toBeTruthy();
  expect(r.datesEn, 'y son un orden DISTINTO del español').not.toBe(r.dates);
  expect(r.es, 'en español el encabezado usa dates').toContain(r.dates);
  expect(r.en, 'en inglés pasa a dates_en').toContain(r.datesEn);
  expect(r.en, 'y deja de mostrar el orden español').not.toContain(r.dates);
  expect(r.selectorEn, 'el selector dice lo mismo que el encabezado').toContain(r.datesEn);
});

// ── I07 — en inglés, el cromo no habla español ──────────────────────────────
// Las cards de programa compuesto decían «2 obras · 93 min» en inglés: once
// ocurrencias en la grilla. El sustantivo estaba PEGADO en dos sitios
// (_datoCompuesto y slotPosterParts), no salía de t(), y ningún guardián podía
// verlo:
//
// LÍMITE MEDIDO (3 sep 2026): de esos dos sitios, este test solo ejercita
// `slotPosterParts`. Marqué los dos con centinelas y barrí los quince
// festivales en grilla con TODO: `slotPosterParts` pinta 11 ocurrencias en
// Cinemancia y `_datoCompuesto` pinta CERO en todos. Su mutación (devolverle el
// literal español) no hace fallar nada. No es que el test mire mal: es que hoy
// ningún catálogo llega a esa rama del póster. Queda dicho para que nadie lea
// «cubre los dos» donde el dato dice que cubre uno.
// [i18n-complete] comprueba que las CLAVES existan en los dos idiomas
// —un literal no es una clave— y literal-template.spec.js vigila `${` roto.
//
// Este cubre el hueco por el lado del DOM. Busca NUESTRO vocabulario con su
// cuenta delante («N obras», «N actividades»…), que es cromo y nunca contenido:
// los títulos y las secciones del festival NO se traducen por diseño, así que un
// «no hay palabras en español» a secas daría falsos positivos con «Proyecciones
// Especiales». El número delante es lo que distingue una cosa de la otra.
test('I07 — en inglés ninguna cuenta usa el sustantivo en español', async ({ page }) => {
  await enterFestival(page, 'cinemancia2026');
  const r = await page.evaluate(async () => {
    const w = ms => new Promise(r => setTimeout(r, ms));
    const tap = (a, ds) => { const b = document.createElement('button'); b.setAttribute('data-action', a);
      Object.keys(ds || {}).forEach(k => b.setAttribute('data-' + k, ds[k]));
      document.body.appendChild(b); b.click(); b.remove(); };
    tap('closeCitySheet');
    await w(500);
    switchMainNav('mnav-cartelera');
    await w(1400);
    // La GRILLA, explícitamente (3 sep 2026): «N obras» es el dato de la tarjeta
    // de programa compuesto, y esas tarjetas son de la grilla. enterFestival deja
    // la vista según la FASE del festival —con Cinemancia en curso pasa a lista y
    // al día de hoy—, así que el día que el festival arrancó este test se quedó
    // sin nada que medir y su propia guarda lo dijo: «en español SÍ aparecen esas
    // cuentas — si no, el test no prueba nada». Medido ese día: 0 en lista, 11 en
    // grilla con TODO. El defecto que vigila no cambió; el fixture dependía de la
    // fecha. Se fija acá y deja de depender.
    activeDay = 'all';
    programaViewMode = 'grid';
    _renderProgramaContent && _renderProgramaContent();
    await w(1400);
    const esperados = () => (document.body.innerText.match(/\d+ obras/g) || []).length;
    const enEspanol = esperados();
    tap('selectLang', { code: 'en' });
    await w(1600);
    const vistos = [];
    for (const nav of ['mnav-cartelera', 'mnav-seleccion', 'mnav-planner', 'mnav-miplan']) {
      switchMainNav(nav);
      // la grilla también en inglés: es donde vivía el literal
      if (nav === 'mnav-cartelera') { activeDay = 'all'; programaViewMode = 'grid'; _renderProgramaContent && _renderProgramaContent(); }
      // showAgView() SOLO donde corresponde: llamarlo en cartelera saca de la
      // grilla y el test terminaba midiendo una pantalla que no era la del bug
      // (pasaba con el literal restituido — lo cacé mutando).
      if (nav === 'mnav-planner' || nav === 'mnav-miplan') { try { showAgView(); } catch (e) {} }
      await w(1200);
      const m = document.body.innerText
        .match(/\d+\s(obras?|actividades?|funciones?|d[ií]as?|vistas?)\b/g) || [];
      m.forEach(x => vistos.push(nav + ': ' + x));
    }
    return { enEspanol, vistos: [...new Set(vistos)] };
  });
  expect(r.enEspanol, 'en español SÍ aparecen esas cuentas — si no, el test no prueba nada')
    .toBeGreaterThan(0);
  expect(r.vistos, 'en inglés ninguna cuenta quedó con el sustantivo en español').toEqual([]);
});
