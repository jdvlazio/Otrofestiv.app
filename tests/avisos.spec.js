// @ts-check
// avisos.spec.js — el camino REAL de un aviso de festival, de punta a punta.
//
// Un aviso (cancelación / reprogramación) entra por NOTICES (src/config.js) y lo
// sella el LOADER sobre los datos ya explotados: pone `_cancelled`, o mueve
// day/time/venue y guarda `_movedFrom` recalculando `day_order` contra dayKeys.
// Todo lo que ve el usuario cuelga de ese sellado.
//
// Hasta ahora esa cadena se verificaba a mano: los tests de Mi Plan (T52/T53)
// simulan el sellado poniendo `_cancelled`/`_movedFrom` a mano sobre FILMS, así
// que probaban la REACCIÓN pero no el sellado. Estos tests entran por NOTICES.
//
// Detalle no obvio: el loader sella dentro de `if(!cfg.films)` — una vez cargado,
// el festival queda cacheado en sesión. Para ejercer el camino real hay que
// limpiar `FESTIVAL_CONFIG[id].films` ANTES de volver a llamar loadFestival.
const { test, expect } = require('@playwright/test');
const { enterFestival, soloWeb } = require('./helpers');

const FEST = 'finca2026';

// applyNotices — inyecta avisos por el camino de PRODUCCIÓN: el campo `avisos`
// del JSON del festival (desde el 19 oct viven ahí, no en NOTICES de config.js)
// y fuerza la recarga. Re-apuntado al vaciarse NOTICES (pedido de Onboarding):
// el test depende de SU aviso, no de que config.js todavía traiga alguno.
// `fest` por parámetro: estaba cableado a FEST, así que un test que entrara a
// OTRO festival recargaba FINCA encima y se quedaba sin sus obras (me pasó con
// AV02 el 5 sep 2026: `total` daba 0 y parecía dato roto, era el fixture pisado).
const _avisosDe = new WeakMap();   // page → { archivo: avisos }
const archivoDe = id => id.replace(/(\d+)$/, '-$1');
async function jsonCon(page, fest, cambiar) {
  await page.route(`**/festivals/${archivoDe(fest)}.json*`, async route => {
    // Sin las cabeceras condicionales: al recargar, el navegador pide con
    // If-None-Match, el servidor contesta 304 SIN cuerpo y no hay JSON que tocar.
    const h = { ...route.request().headers() };
    delete h['if-none-match']; delete h['if-modified-since'];
    const res = await route.fetch({ headers: h });
    const d = await res.json();
    cambiar(d);
    await route.fulfill({ response: res, json: d });
  });
}
async function applyNotices(page, notices, fest = FEST) {
  let m = _avisosDe.get(page);
  if (!m) { m = {}; _avisosDe.set(page, m); }
  if (!(fest in m)) await jsonCon(page, fest, d => { d.avisos = m[fest]; });
  m[fest] = notices;
  return page.evaluate(async (id) => {
    FESTIVAL_CONFIG[id].films = null;   // sin esto, el caché de sesión salta el sellado
    await loadFestival(id);
  }, fest);
}

// El service worker responde festivals/ desde su caché y page.route no lo ve:
// la intercepción no se entera (medido: 0 aciertos). Este archivo va sin SW.
test.use({ serviceWorkers: 'block' });

// AV01 — el loader sella la cancelación y la reprogramación desde NOTICES
test('AV01 — el aviso llega al dato: cancelada marcada, reprogramada movida', async ({ page }) => {
  await enterFestival(page, FEST, '2026-08-12T10:00');
  await applyNotices(page, [
    { title: 'Yurlu', type: 'cancelled', date: '2026-08-13' },
    { title: 'Ziki', type: 'rescheduled', date: '2026-08-13',
      newDay: '2026-08-16', newTime: '17:00', newVenue: 'Cine York' },
  ]);
  const r = await page.evaluate(() => {
    const c = FILMS.find(f => f.title === 'Yurlu');
    const m = FILMS.find(f => f.title === 'Ziki');
    return {
      cancelada: !!(c && c._cancelled),
      // la cancelada NO se mueve: sigue en su día y hora (solo queda marcada)
      canceladaDia: c && c.day,
      dia: m && m.day, hora: m && m.time, sede: m && m.venue,
      orden: m && m.day_order, ordenReal: DAY_KEYS.indexOf('2026-08-16'),
      antesDia: m && m._movedFrom && m._movedFrom.day,
      antesHora: m && m._movedFrom && m._movedFrom.time,
    };
  });
  expect(r.cancelada).toBe(true);
  expect(r.canceladaDia).toBe('2026-08-13');
  expect(r.dia).toBe('2026-08-16');
  expect(r.hora).toBe('17:00');
  expect(r.sede).toBe('Cine York');
  // day_order recalculado: si se queda con el viejo, la función aparece en el día equivocado
  expect(r.orden).toBe(r.ordenReal);
  expect(r.antesDia).toBe('2026-08-13');
  expect(r.antesHora).toBeTruthy();
});

// AV02 — el aviso sin fecha no se aplica a la función equivocada
// El matcher es (title, date opcional): con `date`, solo esa función. Sin esta
// guarda, un festival con dos funciones del mismo título perdería las dos.
test('AV02 — el aviso con fecha toca UNA función, no todas las del título', async ({ page }) => {
  // FIXTURE — FICDEH, no FINCA. Este test necesita un título con DOS funciones
  // EN DÍAS DISTINTOS, y FINCA no tiene ni un título repetido: se saltaba
  // siempre, así que nunca corrió (medido 5 sep 2026 sobre los 18 festivales).
  // FICDEH está terminado —su dato ya no cambia—, usa días ISO y trae 82
  // títulos repetidos. Descartado FICCI 65 pese a tener 66: sus días son
  // nombres («Martes»), no fechas, así que un aviso con `date` no puede casar —
  // lo probé y marcaba cero.
  await enterFestival(page, 'ficdeh2026', '2026-08-15T10:00:00-05:00');
  // La condición se pide COMPLETA: dos funciones en días distintos. Con las dos
  // el mismo día, el aviso con fecha marcaría las dos y el test mediría al revés.
  const caso = await page.evaluate(() => {
    const por = {};
    FILMS.filter(f => !f.info && f.day).forEach(f => (por[f.title] ||= new Set()).add(f.day));
    const t = Object.keys(por).find(t => por[t].size > 1);
    return t ? { title: t, day: [...por[t]].sort()[0] } : null;
  });
  expect(caso, 'el fixture trae un título con funciones en dos días: es el caso que mide')
    .not.toBe(null);
  const title = caso.title;
  const day = caso.day;
  await applyNotices(page, [{ title, type: 'cancelled', date: day }], 'ficdeh2026');
  const r = await page.evaluate(t => {
    const fs = FILMS.filter(f => f.title === t);
    return { total: fs.length, marcadas: fs.filter(f => f._cancelled).length };
  }, title);
  expect(r.total).toBeGreaterThan(1);
  expect(r.marcadas).toBe(1);
});

// AV03 — la ficha muestra el aviso rojo y la función cancelada pierde su salida
// Ofrecer "Añadir" sobre una sala cerrada sería el peor de los errores posibles.
test('AV03 — la ficha marca la función cancelada y le quita el botón de añadir', async ({ page }) => {
  await enterFestival(page, FEST, '2026-08-12T10:00');
  await applyNotices(page, [{ title: 'Yurlu', type: 'cancelled', date: '2026-08-13' }]);
  await page.evaluate(() => openPelSheet('Yurlu'));
  await page.waitForSelector('#pel-sheet.open', { timeout: 8000 });
  const r = await page.evaluate(() => ({
    void: document.querySelectorAll('#pel-sheet-inner .pel-sheet-screening.scr-void').length,
    addEnVoid: document.querySelectorAll('#pel-sheet-inner .scr-void .suggestion-add').length,
    pills: [...document.querySelectorAll('#pel-sheet-inner .aviso-pill')].map(e => e.textContent.trim()),
    rojas: document.querySelectorAll('#pel-sheet-inner .aviso-pill.sev-red').length,
  }));
  expect(r.void).toBe(1);
  expect(r.addEnVoid).toBe(0);
  expect(r.rojas).toBeGreaterThan(0);
  expect(r.pills.join(' ')).toMatch(/cancel/i);
});

// AV04 — desde NOTICES hasta Mi Plan: la entrada afectada tiene marca y salida
// T52 prueba el botón partiendo de un sellado simulado; acá el sellado lo hace
// el loader, así que se cubre el tramo que faltaba (NOTICES → dato → UI → acción).
test('AV04 — Mi Plan marca la función reprogramada y Actualizar la muda', async ({ page }) => {
  // el día activo tiene que ser el de la entrada: Mi Plan dibuja UN día
  await enterFestival(page, FEST, '2026-08-13T10:00');
  await applyNotices(page, [{ title: 'Ziki', type: 'rescheduled', date: '2026-08-13',
    newDay: '2026-08-16', newTime: '17:00', newVenue: 'Cine York' }]);
  await page.evaluate(() => {
    const f = FILMS.find(fi => fi.title === 'Ziki');
    state.set('savedAgenda', { scenarioIdx: 0, schedule: [Object.assign({}, f, {
      _title: f.title, day: f._movedFrom.day, time: f._movedFrom.time, venue: f._movedFrom.venue })] });
    switchMainNav('mnav-miplan'); showAgView();
  });
  const btn = page.locator('.mplan-fix').first();
  await expect(btn).toBeVisible({ timeout: 8000 });
  await expect(page.locator('.mp-void-t').first()).toBeVisible();
  await btn.click();
  await page.waitForTimeout(700);
  const e = await page.evaluate(() => savedAgenda.schedule.find(s => s._title === 'Ziki') || {});
  expect(e.day).toBe('2026-08-16');
  expect(e.time).toBe('17:00');
});

// ── Etapa 2·A (19 oct 2026): avisos y palmarés viven en el JSON del festival ──
// Regla de transición, en el loader y una sola vez: si el JSON trae el campo
// —aunque vacío— manda el JSON; si no lo trae, las constantes de config.js.
// Los AV01–AV04 cubren el lado «sin campo» (entran por NOTICES); estos, el otro.

async function conCampos(page, campos) {
  await soloWeb(page);   // el almacén va cortado
  await jsonCon(page, FEST, d => Object.assign(d, campos));
}

// AV05 — el aviso del JSON se sella, y uno de NOTICES para el mismo festival ya no
test('AV05 — con `avisos` en el JSON manda el JSON, no NOTICES', async ({ page }) => {
  // Sin `date`: el banner se apaga al día siguiente de la función según el reloj
  // REAL (no el simulado), así que con fecha de agosto no se vería nunca.
  await conCampos(page, { avisos: [{ title: 'Yurlu', type: 'cancelled' }] });
  await enterFestival(page, FEST, '2026-08-12T10:00:00-05:00');
  const r = await page.evaluate(async (id) => {
    NOTICES.length = 0;
    NOTICES.push({ festival: id, title: 'Ziki', type: 'cancelled', date: '2026-08-13' });
    FESTIVAL_CONFIG[id].films = null;
    await loadFestival(id);
    const { getActiveNotices } = await import('/src/view/programa.js');
    return {
      yurlu: !!FILMS.find(f => f.title === 'Yurlu' && f._cancelled),
      ziki: !!FILMS.find(f => f.title === 'Ziki' && f._cancelled),
      banner: getActiveNotices().map(n => n.title),
    };
  }, FEST);
  expect(r.yurlu).toBe(true);
  expect(r.ziki).toBe(false);
  expect(r.banner).toEqual(['Yurlu']);
});

// AV06 — palmarés: el del JSON reemplaza al de config.js, y `[]` también manda
test('AV06 — con `palmares` en el JSON manda el JSON, incluso vacío', async ({ page }) => {
  await conCampos(page, { palmares: [
    { categoria: 'Competencia Prueba', nivel: 'ganadora', titulo: 'Yurlu', obra: 'Yurlu' },
  ] });
  await enterFestival(page, FEST, '2026-08-25T10:00:00-05:00');
  const uno = await page.evaluate(async (id) => {
    const { palmaresDe } = await import('/src/view/programa.js');
    return (palmaresDe(id) || []).map(c => c.categoria + ':' + c.ganadoras.length);
  }, FEST);
  expect(uno).toEqual(['Competencia Prueba:1']);

  await page.unrouteAll({ behavior: 'ignoreErrors' });
  await conCampos(page, { palmares: [] });
  const vacio = await page.evaluate(async (id) => {
    FESTIVAL_CONFIG[id].films = null;
    await loadFestival(id);
    const { palmaresDe } = await import('/src/view/programa.js');
    return palmaresDe(id);
  }, FEST);
  expect(vacio).toBeNull();
});

// AV07 — sin `palmares` en el JSON, la app usa los de config.js (transición).
// Construye su PREMISA (pedido de Onboarding, 19 oct): le saca el campo al JSON
// e inyecta su propia fila en PALMARES. Antes exigía que config.js trajera filas
// reales de FINCA, y al vaciarse PALMARES se ponía rojo sin que la regla fallara.
test('AV07 — sin `palmares` en el JSON se usa PALMARES de config.js', async ({ page }) => {
  await soloWeb(page);
  await jsonCon(page, FEST, d => { delete d.palmares; });
  await enterFestival(page, FEST, '2026-08-25T10:00:00-05:00');
  const r = await page.evaluate(async (id) => {
    const { PALMARES } = await import('/src/config.js');
    const { palmaresDe } = await import('/src/view/programa.js');
    PALMARES.push({ fest: id, categoria: 'Categoría de prueba', nivel: 'ganadora', titulo: 'Yurlu', obra: 'Yurlu' });
    FESTIVAL_CONFIG[id].films = null;
    await loadFestival(id);
    return (palmaresDe(id) || []).map(c => c.categoria + ':' + c.ganadoras.map(g => g.titulo).join('|'));
  }, FEST);
  expect(r).toContain('Categoría de prueba:Yurlu');
});

// AV08 — con la app ABIERTA: un aviso que aparece en el JSON llega por el
// refresco de datos (live-refresh), sin recargar ni subir versión. Es el motivo
// de toda la Etapa 2·A: antes un aviso era código y exigía un deploy.
test('AV08 — un aviso nuevo en el JSON llega con la app abierta', async ({ page }) => {
  let campos = {};
  await soloWeb(page);
  await page.route('**/festivals/finca-2026.json*', async route => {
    const h = { ...route.request().headers() };
    delete h['if-none-match']; delete h['if-modified-since'];
    const res = await route.fetch({ headers: h });
    const d = await res.json();
    Object.assign(d, campos);
    await route.fulfill({ response: res, json: d });
  });
  await enterFestival(page, FEST, '2026-08-12T10:00:00-05:00');
  const antes = await page.evaluate(() => !!FILMS.find(f => f.title === 'Yurlu' && f._cancelled));
  campos = { avisos: [{ title: 'Yurlu', type: 'cancelled' }] };
  const despues = await page.evaluate(async () => {
    const { refrescarDatosFestival } = await import('/src/controller/live-refresh.js');
    const { getActiveNotices } = await import('/src/view/programa.js');
    const hubo = await refrescarDatosFestival();
    return { hubo, sellada: !!FILMS.find(f => f.title === 'Yurlu' && f._cancelled),
      banner: getActiveNotices().map(n => n.title) };
  });
  expect(antes).toBe(false);
  expect(despues.hubo).toBe(true);
  expect(despues.sellada).toBe(true);
  expect(despues.banner).toEqual(['Yurlu']);
});
