// @ts-check
// ─────────────────────────────────────────────────────────────────────────────
// responsive.spec.js — Invariantes de layout CROSS-ENGINE (Paso 2 del plan de
// robustez responsive; ver memoria responsive-robustness-plan).
//
// Corre SOLO bajo los proyectos cross-engine de playwright.config.js
// (ios-mobile = WebKit@390, motor de iOS · android-small = Blink@360, clase
// Redmi 8). La suite de comportamiento lo IGNORA (testIgnore) y sigue en
// chromium@390. Aquí medimos GEOMETRÍA determinista (scrollWidth, bounding-rects)
// — NO screenshots: sin umbrales visuales frágiles, un fallo señala un elemento
// concreto que se sale del viewport.
//
// Regresión que cubre R1/R4: bajo WebKit@390 los expansores de tap-target
// (::after{position:absolute;inset:-6px}) de los botones pegados al borde derecho
// sangraban 6px; WebKit los contaba en scrollWidth (Blink los recortaba) → 6px de
// overflow horizontal sólo en iOS, invisible en el CI que sólo corría chromium.
// Arreglado con overflow-x:clip en html+body.
// ─────────────────────────────────────────────────────────────────────────────
const { test, expect } = require('@playwright/test');
const { LEVIZA_SIMTIME, enterFestival } = require('./helpers');

// SW bloqueado: el listener `controllerchange` de main.js recarga la página
// cuando el service worker reclama el control (sw.js → clients.claim()). Bajo
// WebKit (arranque más lento) ese reload caía a MITAD del test → "Execution
// context was destroyed, most likely because of a navigation" (flaky). El SW no
// afecta el layout, así que bloquearlo es un estabilizador determinista, no un
// enmascarador de fallos reales.
test.use({ serviceWorkers: 'block' });

// Settle determinista antes de medir rects (sin waitForTimeout fijo): networkidle
// (requests resueltos) + fonts.ready (métricas del webfont finales — la fuente
// real es más alta que el fallback y desplazaba el wordmark si se medía antes del
// swap) + doble rAF (layout flusheado). Esto es lo que hacía que R2/R3 pasaran
// SÓLO en retry: se medían bounding-rects a mitad de render/font-swap.
async function settleLayout(page) {
  await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
  await page.evaluate(async () => {
    if (document.fonts && document.fonts.ready) { try { await document.fonts.ready; } catch (_) {} }
    await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
  });
}

function horizontalOverflow(page) {
  return page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
}

function rectOf(page, selector) {
  return page.evaluate((sel) => {
    const el = document.querySelector(sel);
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return { top: r.top, left: r.left, right: r.right, bottom: r.bottom, width: r.width, height: r.height };
  }, selector);
}

test.describe('Responsive — invariantes de layout cross-engine', () => {
  test.beforeEach(async ({ page }) => {
    await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
    await settleLayout(page);
  });

  // R1 — La cartelera NUNCA debe ser scrolleable en horizontal. +1px de
  // tolerancia subpíxel; el bug original eran 6px, así que el guard lo caza.
  test('R1 — cartelera sin overflow horizontal', async ({ page }) => {
    expect(await horizontalOverflow(page)).toBeLessThanOrEqual(1);
  });

  // R2 — El wordmark "Otrofestiv" del header está visible y no recortado por
  // arriba (top >= -1). Defiende contra el header sticky que se "entrecorta" al
  // asentar la vista.
  test('R2 — wordmark visible y no recortado', async ({ page }) => {
    const wm = page.locator('.hdr-wordmark').first();
    await expect(wm).toBeVisible();
    const r = await rectOf(page, '.hdr-wordmark');
    expect(r).not.toBeNull();
    expect(r.height).toBeGreaterThan(0);
    expect(r.width).toBeGreaterThan(0);
    expect(r.top).toBeGreaterThanOrEqual(-1);
  });

  // R3 — La barra de navegación principal (fixed bottom en móvil) cabe dentro del
  // viewport: no se sale por los lados.
  test('R3 — main-nav dentro del viewport', async ({ page }) => {
    const nav = page.locator('.main-nav').first();
    await expect(nav).toBeVisible();
    const r = await rectOf(page, '.main-nav');
    const vp = page.viewportSize();
    const vw = vp ? vp.width : 0;
    expect(r).not.toBeNull();
    expect(r.left).toBeGreaterThanOrEqual(-1);
    expect(r.right).toBeLessThanOrEqual(vw + 1);
  });

  // R4 — Mi Plan (la otra vista densa: listas + pósters apilados) tampoco debe
  // tener overflow horizontal.
  test('R4 — Mi Plan sin overflow horizontal', async ({ page }) => {
    await page.evaluate(() => { switchMainNav('mnav-miplan'); showAgView(); });
    await page.waitForSelector('#ag-view', { state: 'visible', timeout: 8000 });
    await settleLayout(page);
    expect(await horizontalOverflow(page)).toBeLessThanOrEqual(1);
  });

  // R5 — Contrato dual del bottom-sheet (regla ≥768px de index.html): en móvil
  // (<768) el sheet ocupa TODO el ancho; en tablet (≥768) se centra a max-width
  // 560px en vez de estirarse de borde a borde. Un solo test protege ambos
  // comportamientos según el viewport del proyecto (390/360 vs tablet@768).
  test('R5 — pel-sheet: full-width en móvil, centrado ≤560px en tablet', async ({ page }) => {
    await page.evaluate(() => {
      const f = FILMS.find(x => x.type !== 'event') || FILMS[0];
      openPelSheet(f.title);
    });
    await page.waitForSelector('#pel-sheet.open', { state: 'attached', timeout: 8000 });
    await settleLayout(page);
    const r = await rectOf(page, '#pel-sheet');
    const vp = page.viewportSize();
    expect(r).not.toBeNull();
    if (vp.width >= 768) {
      expect(r.width).toBeLessThanOrEqual(562);                                 // max-width 560 (+2 subpíxel)
      expect(Math.abs(r.left - (vp.width - r.right))).toBeLessThanOrEqual(2);   // centrado
    } else {
      expect(r.width).toBeGreaterThanOrEqual(vp.width - 2);                     // full-width intacto
    }
  });
});
