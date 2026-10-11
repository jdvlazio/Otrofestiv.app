// @ts-check
// cuenta.spec.js — la invitación a la cuenta (una línea, solo sin sesión).
const { test, expect } = require('@playwright/test');
const { enterFestival } = require('./helpers');

test('IC1 — «Tu festival»: la línea sale sin cuenta, no con cuenta, y abre la hoja de cuenta', async ({ page }) => {
  await enterFestival(page, 'jardin2026', '2026-09-28T12:00:00-05:00');
  const r = await page.evaluate(async () => {
    const w = ms => new Promise(res => setTimeout(res, ms));
    const ts = ['La marcha del hambre', 'Romero'];
    state.set('watched', new Set(ts));
    state.set('savedAgenda', { scenarioIdx: 0, schedule: ts.map(t => Object.assign({}, FILMS.find(f => f.title === t), { _title: t })) });
    switchMainNav('mnav-miplan'); showAgView(); await w(800);
    const sin = document.querySelector('.saved-agenda .invitar-cuenta');
    const texto = sin && sin.textContent.trim(), alto = sin && Math.round(sin.getBoundingClientRect().height);
    sin && sin.click(); await w(600);
    const hoja = !!document.querySelector('#auth-sheet.open, .auth-sheet.open');
    globalThis._sbUser = { id: 'x', email: 'a@b.c' };
    showAgView(); await w(600);
    const con = !!document.querySelector('.saved-agenda .invitar-cuenta');
    globalThis._sbUser = null;
    return { texto, alto, hoja, con };
  });
  expect(r.texto).toBe('Guardá tu Diario con tu email →');
  expect(r.alto, '44pt de toque').toBeGreaterThanOrEqual(44);
  expect(r.hoja, 'abre la hoja de cuenta de siempre').toBe(true);
  expect(r.con, 'con cuenta no se invita').toBe(false);
});

test('IC2 — «¡Tu Plan está listo!»: la línea sale sin cuenta y se oculta con cuenta', async ({ page }) => {
  await enterFestival(page, 'fantasmagoria2026', '2026-10-13T10:00:00-05:00');
  const r = await page.evaluate(async () => {
    const S = await import('/src/controller/sheets-controller.js');
    const f = FILMS.find(x => x.type !== 'event' && x.day);
    const plan = [Object.assign({}, f, { _title: f.title })];
    globalThis._sbUser = null; S.openPlanConfirm(plan);
    const el = document.getElementById('plan-confirm-cuenta');
    const sin = { visible: el.style.display !== 'none', texto: el.textContent.trim() };
    S.closePlanConfirm(false);
    globalThis._sbUser = { id: 'x' }; S.openPlanConfirm(plan);
    const con = el.style.display !== 'none';
    globalThis._sbUser = null; S.closePlanConfirm(false);
    return { sin, con };
  });
  expect(r.sin).toEqual({ visible: true, texto: 'Guardalo con tu email →' });
  expect(r.con, 'con cuenta no se invita').toBe(false);
});
