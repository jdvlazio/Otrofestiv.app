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

// ── T109 — «Actualizar» sobre un TALLER no puede dejar el plan en «1 de 2» ────
// Bug medido en main (26 ago 2026), vivo y sin relación con «verla otra vez»:
// _planFixNotice mandaba TODO título reprogramado a addSuggestion, que resuelve
// el swap de función con filter(_title!==title) + insertar UNA. Sobre un taller
// de 2 sesiones eso borraba la hermana intacta: 2 → 1, sin toast, y sin pasar
// por _dropFromPlan, así que la sesión perdida NO quedaba restaurable. El propio
// verifyPlan la marcaba `bloque-incompleto` — el estado que addRecurringBlock
// declara prohibido («un plan con 1 de 2 no es medio taller, es un plan que
// miente sobre un compromiso que nadie tomó», regla de Juan del 8 ago).
//
// Se ejerce por el MISMO data-action que dispara un tap real, no por el bridge.
const TALLER_FICDEH = 'Los frutos que dan vida: Siembra autosostenible casera';

test('T109 — un taller con una sesión reprogramada se re-toma ENTERO', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-14T10:00');
  const r = await page.evaluate((TITULO) => {
    const tap = (action, title) => {
      const b = document.createElement('button');
      b.setAttribute('data-action', action);
      b.setAttribute('data-title', title);
      document.body.appendChild(b); b.click(); b.remove();
    };
    const delTaller = () => ((savedAgenda && savedAgenda.schedule) || [])
      .filter(s => s._title === TITULO).map(s => s.day + ' ' + s.time);

    tap('addRecurringBlock', TITULO);
    const antes = delTaller();

    // el festival mueve UNA de las dos sesiones
    const ses = FILMS.filter(f => f.title === TITULO);
    if (ses[1]) { ses[1]._movedFrom = { day: ses[1].day, time: ses[1].time }; ses[1].time = '15:00'; }

    tap('planFixNotice', TITULO);   // el usuario toca «Actualizar» en Mi Plan
    const despues = delTaller();
    const v = verifyPlan((savedAgenda && savedAgenda.schedule) || [], { catalog: FILMS });
    return { antes, despues, ok: !!(v && v.ok), violaciones: (v && v.violations) || [] };
  }, TALLER_FICDEH);

  expect(r.antes.length).toBe(2);                 // el taller entró entero
  expect(r.despues.length).toBe(2);               // y sigue entero tras «Actualizar»
  expect(r.despues).toContain('2026-08-16 13:00'); // la sesión intacta sobrevive
  expect(r.despues).toContain('2026-08-17 15:00'); // la reprogramada, en su hora nueva
  expect(r.violaciones.map(x => x.kind)).not.toContain('bloque-incompleto');
  expect(r.ok).toBe(true);
});

// ── PC10 — el titular del Plan nombra la ciudad que lo restringió ────────────
// Auditoría 4 sep 2026. El planificador NO cruza ciudades, así que el filtro de
// Lugar decide qué obras compitieron. Medido en FICDEH con la MISMA lista de
// intereses y el mismo reloj, cambiando solo el filtro: «7 obras · 4 días»
// (Bogotá), «7 obras · 2 días» (Ibagué), «7 obras · 5 días» (todas). Tres planes
// sin nada en común, el mismo titular, y la barra de Lugar vive en Programa: en
// Planear no había dónde leer con qué ciudad se calculó.
//
// El código ya usaba la ciudad para no inflar «quedaron fuera» —o sea que era un
// insumo del resultado que el resultado no decía—.
//
// Se afirma: (1) con una ciudad puesta, el titular la nombra; (2) con «todas» NO
// nombra ninguna —el control: nombrarla siempre sería inventar un filtro que el
// usuario no puso—; (3) el titular sigue diciendo lo que decía.
test('PC10 — el titular nombra la ciudad cuando el filtro la restringe', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });

  const titular = async (filtro) => {
    await enterFestival(page, 'ficdeh2026', '2026-08-15T11:00');
    return page.evaluate(async (filtro) => {
      const b = document.createElement('button'); b.setAttribute('data-action', 'closeCitySheet');
      document.body.appendChild(b); b.click(); b.remove();
      await new Promise(r => setTimeout(r, 400));
      activeVenue = filtro;
      const t = [...new Set(FILMS.filter(f => !f._cancelled && f.day >= '2026-08-16').map(f => f.title))].slice(0, 8);
      state.set('watchlist', new Set(t));
      state.set('savedAgenda', null);
      cachedResult = null;
      switchMainNav('mnav-planner'); showAgView();
      await new Promise(r => setTimeout(r, 2500));
      const d = document.querySelector('.dato-resultado');
      return { filtro, texto: d ? d.textContent.replace(/\s+/g, ' ').trim() : null };
    }, filtro);
  };

  // 1 · con ciudad: el titular la nombra
  const bogota = await titular('city:Bogotá');
  expect(bogota.texto, 'Planear muestra su resultado').toBeTruthy();
  expect(bogota.texto, `el titular nombra la ciudad (dice: ${bogota.texto})`).toContain('Bogotá');
  expect(bogota.texto, 'y sigue diciendo cuántos días').toMatch(/d[íi]as?/i);

  // 2 · control: sin filtro NO nombra ninguna. Nombrarla siempre sería inventar
  // un filtro que el usuario no puso.
  const todas = await titular('all');
  expect(todas.texto, 'con «todas» el resultado sigue estando').toBeTruthy();
  expect(todas.texto, `y no nombra ninguna ciudad (dice: ${todas.texto})`)
    .not.toMatch(/Bogot|Ibagu|Medell|Armenia|Cartagena|Quibd/i);

  // 3 · otra ciudad, otro nombre: no está cableado a una sola
  const ibague = await titular('city:Ibagué');
  expect(ibague.texto, `el titular nombra Ibagué (dice: ${ibague.texto})`).toContain('Ibagué');

  // 4 · una SEDE elegida no restringe el plan —la ciudad es contexto, la sede es
  // un filtro momentáneo (isCitySel/keepCityOnly)—, así que el titular NO la
  // nombra. Sin este caso, quitar keepCityOnly pasaba limpio y el titular
  // atribuiría el resultado a un filtro que no lo produjo.
  const unaSede = await page.evaluate(() => {
    const vs = Object.keys((FESTIVAL_CONFIG[_activeFestId] || {}).venues || {});
    return vs.find(v => !v.startsWith('city:')) || null;
  });
  expect(unaSede, 'FICDEH tiene sedes con clave propia').toBeTruthy();
  const sede = await titular(unaSede);
  expect(sede.texto, 'con una sede elegida el resultado sigue estando').toBeTruthy();
  expect(sede.texto, `una sede no restringe el plan: el titular no la nombra (dice: ${sede.texto})`)
    .not.toMatch(/·\s*(en|in|em)\s+\S/);
});
