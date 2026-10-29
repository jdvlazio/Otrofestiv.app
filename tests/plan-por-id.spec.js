// @ts-check
// plan-por-id.spec.js — el plan reconoce la función por su código estable
// (18 oct 2026, docs/FUNCION.md §11). Antes, si el festival movía la hora de una
// función que tenías en tu plan, la app no la encontraba: quedaba una entrada
// huérfana con la hora vieja. Con código, el plan se pone al día solo.
const { test, expect } = require('@playwright/test');
const { enterFestival } = require('./helpers');

test('PID1 — el festival renombra la función: el plan la sigue por su código; si la MUEVE, no (avisa)', async ({ page }) => {
  await enterFestival(page, 'fantasmagoria2026', '2026-10-14T10:00:00-05:00');
  const r = await page.evaluate(async () => {
    const S = await import('/src/domain/schedule.js');
    const f = FILMS.find(x => x.id && x.time);
    // Lo que el usuario guardó ANTES de que el festival moviera la función.
    // Renombrada: el plan la sigue por el código.
    const renombrada = { ...f, _title: 'Título viejo', title: 'Título viejo' };
    const r1 = S.syncScheduleWithCatalog([renombrada], FILMS)[0];
    // Movida de hora: el plan NO la sigue en silencio (queda para el aviso REPROGRAMADA).
    const movida = { ...f, _title: f.title, time: f.time === '09:00' ? '10:00' : '09:00' };
    const r2 = S.syncScheduleWithCatalog([movida], FILMS)[0];
    return { sigue: r1._title === f.title && r1.time === f.time, movidaTime: r2.time, guardadaTime: movida.time };
  });
  expect(r.sigue, 'renombrada: el plan toma el título nuevo').toBe(true);
  expect(r.movidaTime, 'movida de hora: el plan queda en la vieja para avisar').toBe(r.guardadaTime);
});
test('PID2 — el retraso y la boleta viajan con la función que el festival renombró', async ({ page }) => {
  await enterFestival(page, 'fantasmagoria2026', '2026-10-14T10:00:00-05:00');
  const r = await page.evaluate(async () => {
    const P = await import('/src/controller/persistence.js');
    const f = FILMS.find(x => x.id && x.time);
    const viejo = 'Título viejo';
    const kv = `${viejo}|${f.day}|${f.time}`, kn = `${f.title}|${f.day}|${f.time}`;
    state.set('savedAgenda', { scenarioIdx: 0, schedule: [{ ...f, _title: viejo, title: viejo }] });
    state.set('filmDelays', { [kv]: 15 });
    state.set('ticketed', new Set([kv]));
    P.sincronizarPlan(FILMS);
    const fd = state.get('filmDelays'), tk = state.get('ticketed');
    return { plan: state.get('savedAgenda').schedule[0]._title, hora: f.title,
             retrasoNuevo: fd[kn], retrasoViejo: fd[kv], boletaNueva: tk.has(kn), boletaVieja: tk.has(kv) };
  });
  expect(r.plan, 'el plan toma el título nuevo').toBe(r.hora);
  expect(r.retrasoNuevo, 'el retraso viaja').toBe(15);
  expect(r.retrasoViejo, 'y no queda colgado de la hora vieja').toBeUndefined();
  expect(r.boletaNueva, 'la boleta viaja').toBe(true);
  expect(r.boletaVieja).toBe(false);
});
