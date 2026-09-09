/**
 * visual-audit.spec.js — Screenshots de cada estado principal de la app,
 * CON CADA FESTIVAL del config.
 *
 * NO son tests de pixel-diff (frágiles entre OS). Son evidencia visual
 * automática: cada push genera screenshots que quedan como CI artifacts.
 * Juan puede revisarlos en GitHub Actions → Artifacts → visual-audit-screenshots.
 *
 * Cuándo falla: si un selector crítico no existe (la pantalla no cargó).
 * Cuándo NO falla: si algo se ve diferente visualmente — eso se audita manual.
 *
 * POR QUÉ DEJÓ DE SER SOLO LEVIZA (9 sep 2026, pedido de Juan)
 * Este archivo miraba un único festival hardcodeado desde mayo. Entretanto se
 * publicaron seis más y ninguno tuvo NUNCA una captura: los que traen las formas
 * nuevas —multiciudad, actividades abiertas, eventos con boleta— eran justo los
 * que nadie veía. El recorrido (recorrido-festival.spec.js) ya había aprendido
 * esta lección: deriva su lista de `festivalTestIds()` y un festival nuevo entra
 * a la cobertura al agregar su entrada de config + su JSON, sin editar specs.
 * Acá se hace lo mismo.
 *
 * EL RELOJ ES OBLIGATORIO, Y VA DENTRO DEL FESTIVAL
 * Sin ancla temporal la captura depende del día en que corra la suite: un
 * festival terminado muestra el modo recuerdo y uno futuro, listas vacías. Se
 * ancla a la mañana del PRIMER día, que es cuando la app tiene todo que mostrar.
 *
 * LA HOJA DE CIUDAD TAPA LA PANTALLA — Y ES EVIDENCIA
 * En los multiciudad (FICDEH 11, Cinemancia 6, SiembraFest 2) el arranque abre
 * «¿a cuál ciudad vas?», que cubre lo que se quiere retratar. Se cierra antes de
 * capturar los seis estados… y se retrata APARTE, porque esa pantalla tampoco
 * tenía ninguna captura y es de las que más cambian con el dato.
 */
const { test, expect } = require('@playwright/test');
const { enterFestival, festivalTestIds } = require('./helpers');

const FESTIVALES = festivalTestIds();

// esperarImagenes — una captura tomada antes de que carguen los pósters MIENTE.
// Medido el 9 sep 2026 en QAFF: al disparar el screenshot habían cargado 15 de 29
// imágenes y la grilla parecía media apagada; tres segundos después estaban las
// 29 y la opacidad era 1 en todas. La evidencia visual que hay que auditar a ojo
// es justo la que no puede tener ese ruido. Solo se esperan las imágenes VISIBLES
// (las de `loading="lazy"` fuera del viewport no cargan nunca) y con tope: si una
// está rota, el screenshot debe mostrarla rota, no colgar la suite.
async function esperarImagenes(page) {
  await page.waitForFunction(() => {
    const enPantalla = [...document.querySelectorAll('img')].filter((i) => {
      const r = i.getBoundingClientRect();
      return r.height > 0 && r.top < innerHeight && r.bottom > 0;
    });
    return enPantalla.every((i) => i.complete && i.naturalWidth > 0);
  }, null, { timeout: 6000 }).catch(() => {});
}

// Cerrar la hoja de ciudad si el arranque la abrió: se retrata aparte (07).
async function sinHojaDeCiudad(page) {
  const verTodas = page.getByText(/ver todas las ciudades|see all cities/i).first();
  if (await verTodas.isVisible().catch(() => false)) {
    await verTodas.click();
    await page.waitForTimeout(300);
  }
}

for (const festId of FESTIVALES) {
  test.describe(`Visual audit — ${festId}`, () => {
    test.beforeEach(async ({ page }) => {
      // Dos entradas, igual que el recorrido: la primera para leer el config,
      // la segunda ya con el reloj puesto (viaja por URL, lo ve el arranque).
      await enterFestival(page, festId);
      const simTime = await page.evaluate((id) => {
        const cfg = FESTIVAL_CONFIG[id] || {};
        if (!cfg.festivalStartStr) return null;
        const d = cfg.festivalStartStr.slice(0, 10);
        return `${d}T10:00:00${cfg.timezoneOffset || '-05:00'}`;
      }, festId);
      if (!simTime) { test.skip(true, `${festId}: sin festivalStartStr`); return; }
      await enterFestival(page, festId, simTime);
      await sinHojaDeCiudad(page);
    });

    test('01 — Programa, día con más funciones (lista)', async ({ page }) => {
      // El primer día puede estar flojo; se retrata el día que más tiene, que es
      // donde la lista se ve de verdad (y donde antes se veía el día fijo de Leviza).
      await page.evaluate(() => {
        const porDia = {};
        (FILMS || []).filter(f => f.day).forEach(f => { porDia[f.day] = (porDia[f.day] || 0) + 1; });
        const top = Object.entries(porDia).sort((a, b) => b[1] - a[1])[0];
        if (top) activeDay = top[0];
        programaViewMode = 'list';
        _renderProgramaContent();
      });
      await page.waitForSelector('.plist-item', { timeout: 8000 });
      await esperarImagenes(page);
      await page.screenshot({ path: `test-results/visual/${festId}-programa-lista.png`, fullPage: false });
      expect(await page.locator('.plist-item').count()).toBeGreaterThan(0);
    });

    test('02 — Programa TODO (grid)', async ({ page }) => {
      await page.locator('.dtab[data-day="all"]').click();
      await page.waitForSelector('.poster-card', { timeout: 8000 });
      await esperarImagenes(page);
      await page.screenshot({ path: `test-results/visual/${festId}-programa-todo.png`, fullPage: false });
      expect(await page.locator('.poster-card').count()).toBeGreaterThan(0);
    });

    // 03–05: la captura tiene que ser de la pantalla que dice su nombre. Sin el
    // aserto de la pestaña no probaban nada: con un id inexistente el screenshot
    // salía igual, y «intereses» y «planear» eran BYTE A BYTE la misma imagen,
    // las dos de Programa (medido, 4 sep 2026).
    for (const [n, nombre, tab] of [['03', 'intereses', 'mnav-seleccion'],
                                    ['04', 'planear', 'mnav-planner'],
                                    ['05', 'miplan', 'mnav-miplan']]) {
      test(`${n} — ${nombre}`, async ({ page }) => {
        await page.evaluate((t) => switchMainNav(t), tab);
        await page.waitForTimeout(800);
        await expect(page.locator(`#${tab}`)).toHaveClass(/\bon\b/, { timeout: 3000 });
        await esperarImagenes(page);
        await page.screenshot({ path: `test-results/visual/${festId}-${nombre}.png`, fullPage: false });
      });
    }

    test('06 — Topbar selector', async ({ page }) => {
      await page.waitForSelector('.hdr-fest-dates', { timeout: 5000 });
      const bar = page.locator('.hdr-fest-bar');
      await esperarImagenes(page);
      await bar.screenshot({ path: `test-results/visual/${festId}-topbar.png` });
      await expect(bar).toBeVisible();
    });

    test('07 — Hoja de ciudad (solo multiciudad)', async ({ page }) => {
      const ciudades = await page.evaluate(async () => {
        const H = await import('/src/view/helpers.js');
        return Object.keys(H.festivalCities(FILMS) || {}).length;
      });
      test.skip(ciudades < 2, `${festId}: una sola ciudad, no hay hoja que retratar`);
      const { abrirHojaCiudad } = require('./helpers');
      await abrirHojaCiudad(page);
      await esperarImagenes(page);
      await page.screenshot({ path: `test-results/visual/${festId}-hoja-ciudad.png`, fullPage: false });
    });
  });
}
