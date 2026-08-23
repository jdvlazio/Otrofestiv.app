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
const { enterFestival } = require('./helpers');

const FEST = 'finca2026';

// applyNotices — inyecta avisos y fuerza la recarga por el camino de producción.
async function applyNotices(page, notices) {
  return page.evaluate(async ({ id, notices }) => {
    NOTICES.length = 0;
    notices.forEach(n => NOTICES.push(Object.assign({ festival: id }, n)));
    FESTIVAL_CONFIG[id].films = null;   // sin esto, el caché de sesión salta el sellado
    await loadFestival(id);
  }, { id: FEST, notices });
}

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
  await enterFestival(page, FEST, '2026-08-12T10:00');
  const title = await page.evaluate(() =>
    (FILMS.filter(f => !f.info).map(f => f.title)
      .find((t, i, a) => a.indexOf(t) !== i)) || null);
  if (!title) { test.skip(true, 'AV02: sin título con dos funciones, skip'); return; }
  const day = await page.evaluate(t => FILMS.find(f => f.title === t).day, title);
  await applyNotices(page, [{ title, type: 'cancelled', date: day }]);
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
