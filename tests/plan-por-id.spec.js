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
