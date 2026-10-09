// @ts-check
// tufestival.spec.js — «Tu festival» (#1055). F1: la función en que se vio cada
// obra queda guardada (watchedMeta) y persiste; desde la ficha solo se infiere
// cuando la obra tiene UNA función (no se adivina).
const { test, expect } = require('@playwright/test');
const { enterFestival } = require('./helpers');

test('TF1 — marcar vista guarda en qué función fue; con varias funciones no se adivina', async ({ page }) => {
  await enterFestival(page, 'villadelcine2026', '2026-10-15T23:00:00-05:00');
  const r = await page.evaluate(async () => {
    const w = ms => new Promise(r => setTimeout(r, ms));
    const una = FILMS.find(f => !f.info && f.day && f.time && FILMS.filter(x => x.title === f.title && x.day).length === 1 && f.type !== 'event');
    const varias = FILMS.find(f => !f.info && f.day && FILMS.filter(x => x.title === f.title && x.day).length > 1);
    // 1) botón del Plan: trae la función
    const b = document.createElement('button');
    b.setAttribute('data-action', 'markWatchedFromPlan'); b.dataset.title = una.title; b.dataset.day = una.day;
    b.dataset.time = una.time; b.dataset.venue = una.venue; b.dataset.dur = una.duration || '';
    document.body.appendChild(b); b.click(); b.remove(); await w(400);
    document.querySelectorAll('.modal-overlay,.conflict-modal,#pv-rating-sheet.open').forEach(e => e.classList.remove('open'));
    const desdePlan = watchedMeta[una.title];
    // 2) desde la ficha, obra con VARIAS funciones: se marca pero sin meta
    let sinMeta = 'n/a';
    if (varias) {
      const t = document.createElement('button');
      t.setAttribute('data-action', 'toggleWatched'); t.dataset.title = varias.title;
      document.body.appendChild(t); t.click(); t.remove(); await w(300);
      const ok = document.querySelector('#conflict-modal .conflict-modal-btn.confirm');
      if (ok) ok.click();
      await w(400);
      sinMeta = { vista: watched.has(varias.title), meta: watchedMeta[varias.title] || null };
    }
    const guardado = JSON.parse(localStorage.getItem(FESTIVAL_STORAGE_KEY + 'wmeta') || '{}');
    return { una: { day: una.day, time: una.time, venue: una.venue }, desdePlan, sinMeta, guardado: guardado[una.title] };
  });
  expect(r.desdePlan, 'el botón del Plan deja día, hora y sede').toEqual(r.una);
  expect(r.guardado, 'y queda guardado en el teléfono').toEqual(r.una);
  if (r.sinMeta !== 'n/a') {
    expect(r.sinMeta.vista, 'desde la ficha se marca vista').toBe(true);
    expect(r.sinMeta.meta, 'pero con varias funciones no se inventa cuál').toBeNull();
  }
});
