// @ts-check
// boleta.spec.js — Boleta, nivel 1 (#1077): «N sin boleta», marcar en Mi Plan y
// el aviso de la víspera. Solo funciones pagas (funcionPaga, el criterio de CON BOLETA).
const { test, expect } = require('@playwright/test');
const { enterFestival } = require('./helpers');

test('BL1 — cuenta solo pagas, marcar baja la cuenta, el filtro deja las que faltan', async ({ page }) => {
  await enterFestival(page, 'fantasmagoria2026', '2026-10-14T10:00:00-05:00');
  const r = await page.evaluate(async () => {
    const w = ms => new Promise(res => setTimeout(res, ms));
    const H = await import('/src/view/helpers.js');
    const C = await import('/src/controller/handlers.js');
    const pagas = FILMS.filter(f => f.day && f.time && H.funcionPaga(f));
    const dia = pagas[0].day;
    const gratis = FILMS.find(f => f.day === dia && f.time && f.is_free === true);
    const sel = [...pagas.filter(f => f.day === dia).slice(0, 2), gratis];
    state.set('savedAgenda', { scenarioIdx: 0, schedule: sel.map(f => Object.assign({}, f, { _title: f.title })) });
    state.set('ticketed', new Set());
    switchMainNav('mnav-miplan'); showAgView(); await w(600);
    C.selectMiPlanDay(DAY_KEYS.indexOf(dia)); await w(400);
    const antes = document.querySelector('.boleta-falta')?.textContent.trim();
    const filas = document.querySelectorAll('.mplan-boleta').length;
    C.toggleBoleta(H.claveBoleta(Object.assign({}, sel[0], { _title: sel[0].title }))); await w(400);
    const despues = document.querySelector('.boleta-falta')?.textContent.trim();
    const guardado = JSON.parse(localStorage.getItem(FESTIVAL_STORAGE_KEY + 'tickets') || '[]');
    C.toggleSoloSinBoleta(); await w(400);
    const filtradas = [...document.querySelectorAll('.mplan-row')].length;
    C.toggleSoloSinBoleta(); await w(300);
    C.toggleBoleta(H.claveBoleta(Object.assign({}, sel[1], { _title: sel[1].title }))); await w(400);
    const ninguna = !!document.querySelector('.boleta-falta');
    return { antes, filas, despues, guardado: guardado.length, filtradas, ninguna, gratisPaga: H.funcionPaga(gratis) };
  });
  expect(r.gratisPaga, 'una función gratis no es paga').toBe(false);
  expect(r.antes).toBe('2 sin boleta');
  expect(r.filas, 'solo las pagas llevan la fila de boleta').toBe(2);
  expect(r.despues, 'marcar una baja la cuenta').toBe('1 sin boleta');
  expect(r.guardado, 'se guarda en el teléfono').toBe(1);
  expect(r.filtradas, 'el filtro deja solo la que falta').toBe(1);
  expect(r.ninguna, 'sin faltantes, la banda desaparece').toBe(false);
});

test('BL2 — aviso de la víspera a las 20:00, solo si falta alguna, y se retira al marcar', async ({ page }) => {
  await enterFestival(page, 'fantasmagoria2026', '2026-10-14T10:00:00-05:00');
  const r = await page.evaluate(async () => {
    const w = ms => new Promise(res => setTimeout(res, ms));
    const H = await import('/src/view/helpers.js');
    const P = await import('/src/controller/persistence.js');
    // el puente de avisos del iPhone: lo que se programa, tal cual
    const lotes = [];
    window.webkit = { messageHandlers: { notifications: { postMessage: m => lotes.push(m) } } };
    const pagas = FILMS.filter(f => f.day && f.time && H.funcionPaga(f) && f.day >= '2026-10-16');
    const dia = pagas[0].day;
    const sel = pagas.filter(f => f.day === dia).slice(0, 2).map(f => Object.assign({}, f, { _title: f.title }));
    state.set('ticketed', new Set());
    commitPlan(() => ({ schedule: sel })); saveSavedAgenda(); await w(300);
    const lee = () => ((lotes.pop() || { avisos: [] }).avisos).filter(a => /boleta/i.test(a.title));
    const a1 = lee();
    state.set('ticketed', new Set(sel.map(H.claveBoleta))); P.saveTicketed(); await w(300);
    // marcar TIENE que reprogramar: sin un lote nuevo, «no hay aviso» no prueba nada
    const reprogramo = lotes.length > 0;
    const a2 = lee();
    return { a1: a1.map(a => ({ title: a.title, body: a.body, at: new Date(a.at).toISOString(), abrir: a.abrir, filtro: a.filtro, adia: a.dia })), a2: a2.length, reprogramo, dia };
  });
  expect(r.a1.length, 'un aviso para ese día').toBe(1);
  expect(r.a1[0].title).toBe('2 funciones de mañana sin boleta');
  // 20:00 en Medellín (UTC-5) del día anterior = 01:00Z del día de la función
  expect(r.a1[0].at).toBe(`${r.dia}T01:00:00.000Z`);
  expect(r.a1[0].abrir).toBe('miplan');
  expect(r.a1[0].filtro, 'el aviso lleva el filtro').toBe('sinboleta');
  expect(r.a1[0].adia, 'y el día al que se refiere').toBe(r.dia);
  expect(r.a1[0].body).toMatch(/ y .+\.$/);
  expect(r.reprogramo, 'marcar reprograma los avisos').toBe(true);
  expect(r.a2, 'con todas marcadas no hay aviso').toBe(0);
});

// ── BL3 — tocar el aviso abre Mi Plan en ESE día con «sin boleta» (15 oct 2026)
// Juan: el aviso pide una acción, la lista filtrada es esa acción. Mismo camino
// en iPhone (__otfAbrirAviso) y Android (extra del aviso → abrirAviso).
test('BL3 — tocar el aviso: Mi Plan en ese día, filtrado; sin faltantes, sin filtro', async ({ page }) => {
  await enterFestival(page, 'fantasmagoria2026', '2026-10-14T10:00:00-05:00');
  const r = await page.evaluate(async () => {
    const w = ms => new Promise(res => setTimeout(res, ms));
    const H = await import('/src/view/helpers.js');
    const A = await import('/src/view/agenda.js');
    const pagas = FILMS.filter(f => f.day && f.time && H.funcionPaga(f));
    const dias = [...new Set(pagas.map(f => f.day))].sort();
    const d1 = dias[0], d2 = dias[1];
    const sel = [pagas.find(f => f.day === d1), ...pagas.filter(f => f.day === d2).slice(0, 2)].map(f => Object.assign({}, f, { _title: f.title }));
    state.set('savedAgenda', { scenarioIdx: 0, schedule: sel }); state.set('ticketed', new Set());
    switchMainNav('mnav-cartelera'); await w(300);
    const ok = window.__otfAbrirAviso({ abrir: 'miplan', filtro: 'sinboleta', dia: d2 }); await w(500);
    const enMiPlan = !!document.querySelector('.boleta-falta, .mplan-row');
    const filtro = A.soloSinBoleta();
    const dia = DAY_KEYS[activeMiPlanDay];
    const filas = [...document.querySelectorAll('.mplan-row')].length;
    state.set('ticketed', new Set(sel.map(H.claveBoleta)));
    window.__otfAbrirAviso({ abrir: 'miplan', filtro: 'sinboleta', dia: d2 }); await w(400);
    return { ok, enMiPlan, filtro, dia, d2, filas, filtroSinFaltantes: A.soloSinBoleta() };
  });
  expect(r.ok, 'la web atiende el aviso').toBe(true);
  expect(r.enMiPlan, 'abre Mi Plan').toBe(true);
  expect(r.filtro, 'con «sin boleta» prendido').toBe(true);
  expect(r.dia, 'en el día del aviso').toBe(r.d2);
  expect(r.filas, 'las dos de ese día').toBe(2);
  expect(r.filtroSinFaltantes, 'ya marcadas: sin filtro, no una lista vacía').toBe(false);
});
