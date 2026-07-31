// @ts-check
// plan-sync.spec.js — el plan guardado se re-deriva del catálogo al hidratar.
//
// Bug real (captura de Juan, 31 jul 2026): plan de FINCA guardado ANTES del
// anclaje de función. Las entradas eran copias congeladas sin _slotDur y Mi Plan
// calculaba sobre ellas: "18:05" de fin para Mi casa es su casa y "Q&A · tenés
// ~115 min" — donde el catálogo vivo dice "19:51" y "~9 min". El planificador
// estaba bien; la persistencia servía datos de otro momento.
//
// La corrección es de puerta: loadFestival (tras sellar slots y avisos) y
// _applyCloudRow re-derivan cada entrada de su función viva vía
// syncScheduleWithCatalog. Este test escribe EL PLAN DE LA CAPTURA en
// localStorage y recarga por el camino real de producción.
const { test, expect } = require('@playwright/test');
const { enterFestival } = require('./helpers');

test('PS01 — el plan congelado pre-anclaje sale del hydrate con la verdad del catálogo', async ({ page }) => {
  await enterFestival(page, 'finca2026', '2026-08-13T10:00');
  const r = await page.evaluate(async () => {
    // El plan de la captura: copias congeladas de ANTES del anclaje (sin _slot*)
    const congelada = t => {
      const f = FILMS.find(fi => fi.title === t && fi.day === '2026-08-13');
      const c = { ...f, _title: f.title };
      delete c._slotKey; delete c._slotDur; delete c._slotMin;
      return c;
    };
    localStorage.setItem('finca2026_saved', JSON.stringify({ scenarioIdx: 0, schedule: [
      congelada('Propiedad privada prohibido pasar'),
      congelada('Mi casa es su casa'),
      congelada('Ziki'),
    ]}));
    // Recarga por el camino real: loadFestival → loadState (hydrate) → sync
    await loadFestival('finca2026');
    _simTime = '2026-08-13T10:00';
    const jueves = DAY_KEYS.indexOf('2026-08-13');
    activeMiPlanDay = jueves >= 0 ? jueves : 0;
    switchMainNav('mnav-miplan'); showAgView();
    return savedAgenda.schedule.map(s => ({ t: s._title.slice(0, 12), slotDur: s._slotDur || null }));
  });
  // el dato: las entradas hidratadas heredaron el anclaje vivo
  expect(r).toEqual([
    { t: 'Propiedad pr', slotDur: 111 },
    { t: 'Mi casa es s', slotDur: 111 },
    { t: 'Ziki', slotDur: 91 },
  ]);
  // la UI: fines de bloque correctos y el aviso de Q&A con el hueco REAL
  await page.waitForSelector('.mplan-row', { timeout: 8000 });
  const ui = await page.evaluate(() => ({
    fines: [...document.querySelectorAll('.mplan-row .mplan-t2')].map(e => e.textContent.trim().slice(0, 5)),
    avisos: [...document.querySelectorAll('.mplan-warn-row')].map(w => w.textContent.trim()),
  }));
  expect(ui.fines).toEqual(['19:51', '19:51', '22:01']);
  expect(ui.avisos.join(' ')).toMatch(/~9 min/);
  expect(ui.avisos.join(' ')).not.toMatch(/115/);
});

// PS02 — la corrección de la nube: un plan viejo que llega por _applyCloudRow
// (boot con sesión / Realtime) también se re-deriva. Mismo contrato, otra puerta.
test('PS02 — el plan que llega de la nube también se normaliza contra el catálogo', async ({ page }) => {
  await enterFestival(page, 'finca2026', '2026-08-13T10:00');
  const r = await page.evaluate(() => {
    const f = FILMS.find(fi => fi.title === 'Ziki' && fi.day === '2026-08-13');
    const vieja = { ...f, _title: f.title, duration: '2 min' };
    delete vieja._slotKey; delete vieja._slotDur; delete vieja._slotMin;
    _applyCloudRow({ saved_agenda: { scenarioIdx: 0, schedule: [vieja] } }, { wholesale: true });
    const e = savedAgenda.schedule[0];
    return { dur: e.duration, slotDur: e._slotDur || null };
  });
  expect(r.dur).toBe('12 min');
  expect(r.slotDur).toBe(91);
});

// PS03 — el calendario exportado dice la verdad del bloque
// exportICS calculaba DTEND con parseInt(duration)||90: una obra anclada de
// 5 min exportaba "18:00→18:05" al calendario del teléfono — la mentira de la
// captura del 31 jul, fugada al ICS. Ahora DTEND sale de blockDuration (19:51).
test('PS03 — el ICS exporta el fin del BLOQUE para una obra anclada', async ({ page }) => {
  await enterFestival(page, 'finca2026', '2026-08-13T10:00');
  const ics = await page.evaluate(async () => {
    const f = FILMS.find(fi => fi.title === 'Mi casa es su casa' && fi.day === '2026-08-13');
    state.set('savedAgenda', { scenarioIdx: 0, schedule: [{ ...f, _title: f.title }] });
    // capturar el blob del download (camino web) sin descargar nada
    let captured = null;
    const orig = URL.createObjectURL.bind(URL);
    URL.createObjectURL = b => { captured = b; return orig(b); };
    await exportICS();
    URL.createObjectURL = orig;
    return captured ? await captured.text() : null;
  });
  expect(ics).toContain('BEGIN:VEVENT');
  // 18:00 -03:00 = 21:00Z; fin del bloque 19:51 -03:00 = 22:51Z (obra suelta diría 21:05Z)
  expect(ics).toContain('DTSTART:20260813T210000Z');
  expect(ics).toContain('DTEND:20260813T225100Z');
});
