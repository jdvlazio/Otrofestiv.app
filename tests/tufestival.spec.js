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

// TF3 — el aviso del día después (10:00 del día siguiente al cierre, abre Mi
// Plan) y la etiqueta de Instagram tras compartir la historia. Se simula el
// puente de avisos del iPhone para leer exactamente lo que se programa.
test('TF3 — aviso «Tu festival» al día siguiente y etiqueta del festival al compartir', async ({ page }) => {
  await enterFestival(page, 'biff2026', '2026-10-12T10:00:00-05:00');
  const r = await page.evaluate(async () => {
    const w = ms => new Promise(r => setTimeout(r, ms));
    const lotes = [];
    window.webkit = { messageHandlers: { notifications: { postMessage: m => lotes.push(m) } } };
    const f = FILMS.find(x => !x.info && x.day === '2026-10-13' && x.time && x.type !== 'event');
    commitPlan(() => ({ schedule: [{ ...f, _title: f.title }] })); saveSavedAgenda(); await w(300);
    const conPlan = (lotes.pop() || { avisos: [] }).avisos.find(a => a.id === '99') || null;
    state.set('notWatched', new Set([f.title])); saveSavedAgenda(); await w(300);
    const negado = (lotes.pop() || { avisos: [] }).avisos.find(a => a.id === '99') || null;
    return { conPlan, negado, esperado: new Date('2026-10-15T10:00:00-05:00').getTime() };
  });
  expect(r.conPlan, 'con algo para contar, se programa el aviso').not.toBeNull();
  expect(r.conPlan.at, 'al día siguiente del cierre, 10:00 hora del festival').toBe(r.esperado);
  expect(r.conPlan.abrir, 'y abre Mi Plan').toBe('miplan');
  expect(r.conPlan.title).toBe('Tu festival está listo.');
  expect(r.conPlan.body).toContain('BIFF');
  expect(r.negado, 'si negaste todo, no hay festival que contar: no hay aviso').toBeNull();

  await enterFestival(page, 'biff2026', '2026-10-16T10:00:00-05:00');
  const toast = await page.evaluate(async () => {
    const w = ms => new Promise(r => setTimeout(r, ms));
    const f = FILMS.find(x => !x.info && x.day && x.time && x.type !== 'event');
    commitPlan(() => ({ schedule: [{ ...f, _title: f.title }] }));
    navigator.canShare = () => true; navigator.share = async () => {};
    const m = await import('/src/controller/story.js'); await m.shareStory(); await w(900);
    return (document.getElementById('prio-toast') || {}).textContent || '';
  });
  expect(toast, 'tras compartir, sugiere etiquetar al festival').toContain('@biffcol');
});

// TF4 — «Mi plan» como historia (#1064). La hoja ofrece Historia / Calendario;
// planRecap cuenta OBRAS (un programa son sus cortos), las prioridades van
// primero en el mosaico y la historia de «Tu festival» habla en primera persona.
test('TF4 — Mi plan: hoja Historia/Calendario, prioridades primero y voz en primera persona', async ({ page }) => {
  await enterFestival(page, 'biff2026', '2026-10-07T09:00:00-05:00');
  const r = await page.evaluate(async () => {
    const w = ms => new Promise(r => setTimeout(r, ms));
    const pr = ['Fjord', 'Cobarde'];
    // Un programa de cortos: cuenta por sus cortos, no como 1.
    const prog = FILMS.find(f => f.is_cortos && f.film_list && f.film_list.length > 1);
    const otras = [prog.title, ...new Set(FILMS.filter(f => f.type !== 'event' && !f.is_cortos && !pr.includes(f.title)).map(f => f.title))].slice(0, 6);
    watchlist.clear(); prioritized.clear(); watched.clear();
    [...otras, ...pr].forEach(x => watchlist.add(x)); pr.forEach(x => prioritized.add(x));
    const D = await import('/src/domain/schedule.js');
    const sch = D.computeScenarios([...watchlist])[0].schedule;
    state.set('savedAgenda', { scenarioIdx: 0, schedule: sch });
    const F = await import('/src/domain/festival.js');
    const film = await import('/src/domain/film.js');
    const p = F.planRecap();
    const esperadas = [...new Set(sch.map(s => s._title))].reduce((n, t) => n + film.obrasDe(FILMS.find(f => f.title === t)).length, 0);
    // Solo lo que falta: una obra marcada como vista sale de la cuenta.
    const suelta = sch.find(s => !s.is_cortos && !pr.includes(s._title))._title;
    watched.add(suelta); const sinVista = F.planRecap().n; watched.delete(suelta);
    const S = await import('/src/controller/story.js');
    S.abrirCompartirPlan(); await w(400);
    const titulo = (document.querySelector('.conflict-modal-hdr, .action-modal-title, [class*="modal"] [class*="hdr"], [class*="modal"] [class*="title"]') || {}).textContent?.trim();
    const botones = [...document.querySelectorAll('button')].filter(b => b.offsetParent).map(b => b.textContent.trim());
    const R = await import('/src/view/recap.js');
    const rec = { peliculas: 4, eventos: 0 };
    return { n: p.n, sinVista, esperadas, conProg: sch.some(s => s._title === prog.title), primeras: p.obras.slice(0, p.prios.length).map(o => o.prio),
      resto: p.obras.slice(p.prios.length).some(o => o.prio), prios: p.prios.map(x => x.title).sort(),
      titulo, botones, yo: R.recapTitular(rec, true).verbo, tu: R.recapTitular(rec).verbo };
  });
  expect(r.conProg, 'el programa de cortos entró al Plan').toBe(true);
  expect(r.n, 'cuenta obras con obrasDe, una vez por título').toBe(r.esperadas);
  expect(r.sinVista, '«Voy a ver» cuenta solo lo que falta').toBe(r.n - 1);
  expect(r.prios, 'No me las pierdo = las prioridades del Plan').toEqual(['Cobarde', 'Fjord']);
  expect(r.primeras.every(Boolean), 'las prioridades abren el mosaico').toBe(true);
  expect(r.resto, 'y no se repiten después').toBe(false);
  expect(r.botones).toEqual(expect.arrayContaining(['Historia', 'Calendario']));
  expect(r.titulo, 'la hoja dice qué hace').toBe('Compartir Plan');
  expect(r.yo, 'la historia habla el asistente').toBe('Vi');
  expect(r.tu, 'la pantalla le habla a él').toBe('Viste');
});
