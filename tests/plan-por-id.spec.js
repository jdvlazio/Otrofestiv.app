// @ts-check
// plan-por-id.spec.js — el plan reconoce la función por su código estable
// (18 oct 2026, docs/FUNCION.md §11). Antes, si el festival movía la hora de una
// función que tenías en tu plan, la app no la encontraba: quedaba una entrada
// huérfana con la hora vieja. Con código, el plan se pone al día solo.
const { test, expect } = require('@playwright/test');
const { enterFestival } = require('./helpers');

test('PID1 — el festival mueve la hora: el plan guardado sigue la función por su código', async ({ page }) => {
  await enterFestival(page, 'fantasmagoria2026', '2026-10-14T10:00:00-05:00');
  const r = await page.evaluate(async () => {
    const S = await import('/src/domain/schedule.js');
    const f = FILMS.find(x => x.id && x.time);
    // Lo que el usuario guardó ANTES de que el festival moviera la función.
    const guardada = { ...f, _title: f.title, time: f.time === '09:00' ? '10:00' : '09:00' };
    const sinCodigo = { ...guardada }; delete sinCodigo.id;
    const conCodigo = S.syncScheduleWithCatalog([guardada], FILMS)[0];
    const viejo = S.syncScheduleWithCatalog([sinCodigo], FILMS)[0];
    return { vigente: f.time, conCodigo: conCodigo.time, viejo: viejo.time, guardadaTime: guardada.time, id: conCodigo.id === f.id };
  });
  expect(r.conCodigo, 'con código, el plan toma la hora nueva').toBe(r.vigente);
  expect(r.id, 'y conserva el código').toBe(true);
  expect(r.viejo, 'sin código (plan viejo) se reconoce como siempre: no la encuentra y la deja intacta').toBe(r.guardadaTime);
});

test('PID2 — el retraso y la boleta viajan con la función que el festival movió', async ({ page }) => {
  await enterFestival(page, 'fantasmagoria2026', '2026-10-14T10:00:00-05:00');
  const r = await page.evaluate(async () => {
    const P = await import('/src/controller/persistence.js');
    const f = FILMS.find(x => x.id && x.time);
    const viejaHora = f.time === '09:00' ? '10:00' : '09:00';
    const kv = `${f.title}|${f.day}|${viejaHora}`, kn = `${f.title}|${f.day}|${f.time}`;
    state.set('savedAgenda', { scenarioIdx: 0, schedule: [{ ...f, _title: f.title, time: viejaHora }] });
    state.set('filmDelays', { [kv]: 15 });
    state.set('ticketed', new Set([kv]));
    P.sincronizarPlan(FILMS);
    const fd = state.get('filmDelays'), tk = state.get('ticketed');
    return { plan: state.get('savedAgenda').schedule[0].time, hora: f.time,
             retrasoNuevo: fd[kn], retrasoViejo: fd[kv], boletaNueva: tk.has(kn), boletaVieja: tk.has(kv) };
  });
  expect(r.plan, 'el plan toma la hora nueva').toBe(r.hora);
  expect(r.retrasoNuevo, 'el retraso viaja').toBe(15);
  expect(r.retrasoViejo, 'y no queda colgado de la hora vieja').toBeUndefined();
  expect(r.boletaNueva, 'la boleta viaja').toBe(true);
  expect(r.boletaVieja).toBe(false);
});
