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

// TF2 — Mi Plan terminado: tarjeta de recorrido arriba, compartir debajo con la
// hoja Historia/Grilla, y la historia sale en 1080×1920. Plan armado en el test
// (BIFF terminado), sin depender de que haya un festival vigente.
test('TF2 — recorrido en Mi Plan terminado y la historia en 1080×1920', async ({ page }) => {
  await enterFestival(page, 'biff2026', '2026-10-16T10:00:00-05:00');
  const r = await page.evaluate(async () => {
    const w = ms => new Promise(r => setTimeout(r, ms));
    const pelis = FILMS.filter(f => !f.info && f.day && f.time && f.type !== 'event' && f.duration);
    const elegidas = [], vistos = new Set();
    for (const f of pelis) { if (vistos.has(f.title)) continue; vistos.add(f.title); elegidas.push(f); if (elegidas.length === 6) break; }
    commitPlan(() => ({ schedule: elegidas.map(f => ({ ...f, _title: f.title })) }));
    state.set('filmRatings', { [elegidas[0].title]: 5, [elegidas[1].title]: 4 });
    switchMainNav('mnav-miplan'); showAgView(); await w(1500);
    const linea = (document.querySelector('.recap-recorrido') || {}).textContent || '';
    const mejores = document.querySelectorAll('.recap-top-item').length;
    const btn = document.querySelector('[data-action="abrirCompartirFestival"]');
    const diario = [...document.querySelectorAll('.sec-hdr')].find(h => /Diario/.test(h.textContent));
    const antes = btn && diario ? !!(btn.compareDocumentPosition(diario) & Node.DOCUMENT_POSITION_FOLLOWING) : false;
    btn.click(); await w(400);
    const hoja = [...document.querySelectorAll('#conflict-modal button')].map(b => b.textContent.trim());
    document.getElementById('conflict-modal')?.remove();
    let cap = null; const o = HTMLAnchorElement.prototype.click;
    HTMLAnchorElement.prototype.click = function () { if (this.download) { cap = this.href; return; } return o.call(this); };
    navigator.canShare = () => false;
    const m = await import('/src/controller/story.js'); await m.shareStory(); await w(300);
    const dim = await new Promise(res => { const im = new Image(); im.onload = () => res([im.naturalWidth, im.naturalHeight]); im.onerror = () => res(null); im.src = cap; });
    return { linea, mejores, antes, hoja, dim };
  });
  expect(r.linea, 'el recorrido dice días y sedes').toMatch(/\d+\s*días?.*\d+\s*sedes?/);
  expect(r.mejores, 'Tus mejores: solo las calificadas').toBe(2);
  expect(r.antes, 'compartir va ANTES del Diario').toBe(true);
  expect(r.hoja.join('|'), 'la hoja ofrece Historia y Grilla').toMatch(/Historia.*Grilla/);
  expect(r.dim, 'la historia mide 1080×1920').toEqual([1080, 1920]);
});
