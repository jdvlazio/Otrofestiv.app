// @ts-check
// reportes.spec.js — retraso colaborativo SIN sesión de email (migración 0006).
// Sin cuenta: el reporte va a la edge function `reportar` con el identificador del
// dispositivo, y el consenso se lee con consenso_festival() — nunca la tabla.
const { test, expect } = require('@playwright/test');
const { enterFestival } = require('./helpers');

test('RP1 — sin cuenta se reporta por la función y se lee el consenso por la consulta pública', async ({ page }) => {
  await enterFestival(page, 'biff2026', '2026-10-12T20:10:00-05:00');
  const r = await page.evaluate(async () => {
    const DC = await import('/src/controller/delays-cloud.js');
    const llamadas = { invoke: [], rpc: [], from: 0 };
    globalThis._sbUser = null;
    globalThis._sb = {
      functions: { invoke: async (n, o) => { llamadas.invoke.push([n, o.body]); return { error: null }; } },
      rpc: async (n, a) => { llamadas.rpc.push([n, a]);
        return { data: [
          { id: 'a1', screening_key: 'Fjord|2026-10-12|20:00|X', delay_min: 10, is_authed: false, created_at: new Date().toISOString() },
          { id: 'b2', screening_key: 'Fjord|2026-10-12|20:00|X', delay_min: 20, is_authed: true, created_at: new Date().toISOString() },
        ], error: null }; },
      from: () => { llamadas.from++; return { upsert: () => ({ then() {} }), delete: () => ({ eq: () => ({ eq: () => ({ then() {} }) }) }), select: () => ({ eq: async () => ({ data: [] }) }) }; },
      channel: () => { throw new Error('sin cuenta no hay canal'); },
      removeChannel: () => {},
    };
    // Leer ANTES de reportar: quien no reporta también tiene que ver el aviso.
    await DC.subscribeDelaysCloud();
    await new Promise(res => setTimeout(res, 300));
    const c = DC.getConsensusMap()['Fjord|2026-10-12|20:00|X'];
    DC.cloudReportDelay('Fjord|2026-10-12|20:00|X', 15);
    DC.cloudClearDelay('Fjord|2026-10-12|20:00|X');
    await new Promise(res => setTimeout(res, 300));
    return { ...llamadas, c, token: localStorage.getItem('otrofestiv_dispositivo') };
  });
  expect(r.from, 'sin cuenta la tabla no se toca').toBe(0);
  expect(r.invoke.map(x => x[0])).toEqual(['reportar', 'reportar']);
  expect(r.invoke[0][1]).toMatchObject({ festival_id: 'biff2026', screening_key: 'Fjord|2026-10-12|20:00|X', delay_min: 15 });
  expect(r.invoke[1][1].delay_min, 'limpiar = 0').toBe(0);
  expect(r.invoke[0][1].token, 'el mismo identificador del dispositivo').toBe(r.token);
  expect(r.token).toMatch(/^[0-9a-f-]{36}$/);
  expect(r.rpc[0]).toEqual(['consenso_festival', { p_festival: 'biff2026' }]);
  expect(r.c, 'dos personas = confirmado, mediana 15').toMatchObject({ state: 'confirmed', delayMin: 15, reporters: 2 });
});
