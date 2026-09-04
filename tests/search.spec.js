// @ts-check
// search.spec.js — Búsqueda global: abrir, tipear, resultados, cerrar.
const { test, expect } = require('@playwright/test');
const { LEVIZA_SIMTIME, enterFestival } = require('./helpers');

// S01 — Icono de búsqueda abre el overlay
test('S01 — icono búsqueda abre overlay', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.locator('#hdr-search-icon').click();
  await page.waitForSelector('#search-overlay', { state: 'visible', timeout: 5000 });
  expect(await page.locator('#search-overlay').count()).toBe(1);
});

// S02 — Input de búsqueda recibe foco al abrir
test('S02 — search input recibe foco', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => searchOpen());
  await page.waitForSelector('#search-overlay', { state: 'visible', timeout: 5000 });
  const input = page.locator('#search-input');
  await expect(input).toBeVisible({ timeout: 3000 });
});

// S03 — Buscar término con resultados muestra items
test('S03 — búsqueda con resultados muestra items', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => searchOpen());
  await page.waitForSelector('#search-overlay', { state: 'visible', timeout: 5000 });
  await page.locator('#search-input').fill('La');
  await page.waitForSelector('.search-item', { timeout: 5000 });
  const items = await page.locator('.search-item').count();
  expect(items).toBeGreaterThan(0);
});

// S04 — Búsqueda sin resultados muestra empty state
test('S04 — búsqueda sin resultados muestra empty state', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => searchOpen());
  await page.waitForSelector('#search-overlay', { state: 'visible', timeout: 5000 });
  await page.locator('#search-input').fill('xyzxyzxyz123456');
  await page.waitForSelector('.search-empty', { timeout: 5000 });
  expect(await page.locator('.search-empty').count()).toBeGreaterThan(0);
});

// S05 — Click en resultado de búsqueda abre sheet de película
test('S05 — resultado búsqueda abre sheet de película', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => searchOpen());
  await page.waitForSelector('#search-overlay', { state: 'visible', timeout: 5000 });
  await page.locator('#search-input').fill('Suprema');
  await page.waitForSelector('.search-item', { timeout: 5000 });
  await page.locator('.search-item').first().click();
  await page.waitForSelector('#pel-sheet.open', { timeout: 5000 });
  expect(await page.locator('#pel-sheet.open').count()).toBe(1);
});

// S06 — Búsqueda funciona en Tribeca
test('S06 — búsqueda funciona en Tribeca', async ({ page }) => {
  await enterFestival(page, 'tribeca2026');
  await page.evaluate(() => searchOpen());
  await page.waitForSelector('#search-overlay', { state: 'visible', timeout: 5000 });
  await page.locator('#search-input').fill('New');
  await page.waitForSelector('.search-item, .search-empty', { timeout: 5000 });
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.waitForTimeout(200);
  expect(errors).toHaveLength(0);
});

// ── S07 — la búsqueda no acepta letras desparramadas ─────────────────────────
// «techo» devolvía 6 resultados y solo el primero tenía que ver: fuzzyMatch
// aceptaba cualquier SUBSECUENCIA, así que T-h-e C-h-ildren's H-o-ur contiene
// t·e·c·h·o en orden, igual que un título de 57 caracteres. Ahora la
// subsecuencia vale solo si es compacta (ventana ≤ 2× lo escrito). El umbral
// salió de medir el catálogo: una errata real (una letra caída) se pasa de la
// consulta por 1 en 29 de 35 casos, y el ruido empieza en 9.
//
// Los DOS asertos van juntos a propósito: el primero solo puede aprobarse
// borrando la tolerancia a erratas, y el segundo lo impide.
test('S07 — «techo» no trae títulos con las letras sueltas', async ({ page }) => {
  await enterFestival(page, 'cinemancia2026');
  const r = await page.evaluate(async () => {
    const O = await import('/src/controller/overlays.js');
    const res = O._searchAll('techo').map(x => x.title);
    // tolerancia a erratas: a cada título se le cae una letra de una palabra suya
    const titulos = [...new Set(FILMS.map(f => f.title))].filter(t => t.length > 7 && !t.includes(' + '));
    let ok = 0, total = 0;
    titulos.slice(0, 60).forEach(t => {
      const w = O.normalize(t).split(' ').find(x => x.length >= 6);
      if (!w) return;
      total++;
      const q = w.slice(0, 3) + w.slice(4, 7);
      if (O._searchAll(q).some(x => x.title === t)) ok++;
    });
    return {
      res,
      sueltos: res.filter(t => !O.normalize(t).includes('techo')),
      erratasOk: ok, erratasTotal: total
    };
  });
  expect(r.res.length, 'la obra buscada sigue apareciendo').toBeGreaterThan(0);
  expect(r.sueltos, 'ningún resultado con las letras desparramadas').toEqual([]);
  expect(r.erratasTotal, 'la muestra de erratas no está vacía').toBeGreaterThan(20);
  expect(r.erratasOk, 'y una letra caída se sigue perdonando').toBe(r.erratasTotal);
});

// ── S08 — el build que muestra el buscador es el que corre ───────────────────
// El número estaba TIPEADO en index.html y nadie lo actualizaba: mostró el build
// del 10 de mayo durante cuatro meses. Ahora lo pone main.js con BUILD_VERSION.
// [dbg-ver-sin-literal] (validate.py) impide que vuelva a nacer escrito; este
// test cubre la otra mitad —que el código de verdad lo escriba—, porque un nodo
// que nace vacío y nunca se llena pasa ese guardián sin decir nada.
test('S08 — el número de build del buscador sale del código que corre', async ({ page }) => {
  await enterFestival(page, 'cinemancia2026');
  const r = await page.evaluate(async () => {
    const w = ms => new Promise(r => setTimeout(r, ms));
    const tap = a => { const b = document.createElement('button'); b.setAttribute('data-action', a);
      document.body.appendChild(b); b.click(); b.remove(); };
    tap('closeCitySheet');
    await w(500);
    tap('searchOpen');
    await w(800);
    const el = document.getElementById('dbg-ver');
    const vj = await (await fetch('/version.json?cb=' + Math.random())).json();
    return { enPantalla: el ? el.textContent.trim() : null, deploy: String(vj.android) };
  });
  expect(r.enPantalla, 'el buscador muestra un build').toBeTruthy();
  expect(r.enPantalla, 'y es el del deploy, no uno escrito a mano').toBe(r.deploy);
});

// ── S10 — el buscador encuentra por el título que dice el AFICHE ─────────────
// Auditoría A-8 (2 sep 2026): «Dry Leaf» (Cinemancia) se muestra con nuestro
// póster de TMDB, que trae el arte de distribución en español y dice «Hoja
// seca» en letras grandes. El título de la ficha es correcto por doctrina —así
// la publica el festival en su PDF—, pero la única pista que el usuario tiene
// delante es el afiche. Medido por la interfaz: buscar «hoja» daba «Sin
// resultados», con el nombre a la vista en la grilla.
//
// El buscador ya miraba `title_en`; ahora mira cualquier título alterno. Este
// test inyecta el campo en el dato (el dato real viaja en su propio PR: la
// frontera código/datos no se cruza) y afirma que el buscador lo usa.
test('S10 — el buscador encuentra una obra por su título alterno', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await enterFestival(page, 'cinemancia2026', '2026-09-04T10:00');
  await page.evaluate(async () => {
    const b = document.createElement('button'); b.setAttribute('data-action', 'closeCitySheet');
    document.body.appendChild(b); b.click(); b.remove();
    await new Promise(r => setTimeout(r, 400));
  });

  const buscar = async (q) => {
    await page.evaluate(() => { searchClose(); });
    await page.waitForTimeout(200);
    await page.evaluate(() => searchOpen());
    await page.waitForSelector('#search-overlay', { state: 'visible', timeout: 5000 });
    await page.locator('#search-input').fill(q);
    await page.waitForTimeout(600);
    return page.evaluate(() => [...document.querySelectorAll('.search-item')]
      .map(e => e.textContent.trim().slice(0, 30)));
  };

  const obra = await page.evaluate(() => {
    const f = FILMS.find(x => x.title === 'Dry Leaf');
    return f ? { title: f.title, tenia: 'title_es' in f } : null;
  });
  expect(obra, 'Cinemancia tiene la obra del hallazgo').not.toBeNull();

  // 1 · control: sin título alterno en español, «hoja» no la encuentra.
  // Es el estado que midió la auditoría, y lo que hace que el resto pruebe algo.
  expect(obra.tenia, 'el fixture parte SIN el campo — si el dato ya lo trae, este control no vale')
    .toBe(false);
  const antes = await buscar('hoja');
  expect(antes.join(' | '), '«hoja» no encuentra «Dry Leaf»: ese es el defecto')
    .not.toContain('Dry Leaf');

  // 2 · con el título del afiche en el dato, aparece
  await page.evaluate(() => {
    const f = FILMS.find(x => x.title === 'Dry Leaf');
    f.title_es = 'Hoja seca';
  });
  const conAlt = await buscar('hoja');
  expect(conAlt.join(' | '), '«hoja» encuentra la obra por el título de su afiche')
    .toContain('Dry Leaf');
  const completo = await buscar('hoja seca');
  expect(completo.join(' | '), 'y el título entero también').toContain('Dry Leaf');

  // 2b · ORDEN. El alterno no solo tiene que hacerla aparecer: tiene que pesar
  // en el puntaje. Con el catálogo tal cual, «hoja seca» devuelve UN resultado,
  // así que «sale primera» es cierto haga lo que haga la fórmula y no prueba
  // nada. La competencia se construye: una segunda obra con un alterno que casa
  // de refilón. La que lo dice exacto va primera.
  const rival = await page.evaluate(() => {
    const f = FILMS.find(x => x.title !== 'Dry Leaf' && !x.title_es && x.title);
    if (!f) return null;
    f.title_es = 'Hojas secas';                   // casa de refilón, no exacto
    return f.title;
  });
  expect(rival, 'hace falta una segunda obra para que haya orden que medir').not.toBeNull();
  const conRival = await buscar('hoja seca');
  expect(conRival.length, 'las dos compiten por la misma consulta').toBeGreaterThan(1);
  expect(conRival[0], `la que dice «Hoja seca» exacto va primera (salió: ${conRival.join(' | ')})`)
    .toContain('Dry Leaf');

  // 3 · sin romper lo que ya andaba: el título oficial sigue encontrándola
  const oficial = await buscar('dry leaf');
  expect(oficial.join(' | '), 'el título del festival la sigue encontrando').toContain('Dry Leaf');

  // 4 · y el alterno no se traga el buscador: una consulta ajena no la trae
  const ajena = await buscar('zzzqx');
  expect(ajena.join(' | '), 'una consulta que no casa con nada no la devuelve')
    .not.toContain('Dry Leaf');
});
