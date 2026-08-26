// @ts-check
// «Verla otra vez» — la misma obra en DOS funciones del Plan.
//
// Rehecha el 26 ago 2026 tras el revert de #749. La versión anterior se retiró
// por un informe adversarial de 10 hallazgos; estos tests SON esa lista de
// aceptación, no una relectura de ella. Cada camino se ejerce por el MISMO
// `data-action` que dispara un tap real — nunca llamando la función interna.
//
// Datos reales de TIFF:
//   «2.6 Seconds: Death in the Outback» → 09-10 12:10 · 09-14 15:20 · 09-15 18:25
//   «Tenzing» → 09-16 08:15 (126 min) y 08:30, que SÍ chocan entre sí
const { test, expect } = require('@playwright/test');
const { enterFestival } = require('./helpers');

const OBRA = '2.6 Seconds: Death in the Outback';
// «Villeneuve» es el par exacto que midió el auditor (A13): 09-19 18:00 y 20:00,
// sedes distintas, y chocan. Ojo: el catálogo CARGADO no es el JSON crudo — las
// funciones de prensa están filtradas, y un par elegido leyendo el archivo puede
// no existir en la app. El par se buscó con el screensConflict de producción.
const CHOCA = 'Villeneuve: The Rise of a Legend';

/** dispara la acción como un tap real del usuario */
const TAP = `(action, ds) => {
  const b = document.createElement('button');
  b.setAttribute('data-action', action);
  Object.keys(ds).forEach(k => b.setAttribute('data-' + k, ds[k]));
  document.body.appendChild(b); b.click(); b.remove();
}`;

const PLAN = `() => ((savedAgenda && savedAgenda.schedule) || []).map(s => s._title + ' | ' + s.day + ' ' + s.time)`;

test('T110 — agendar una función que YA está no abre nada ni duplica (H6)', async ({ page }) => {
  await enterFestival(page, 'tiff2026', '2026-09-09T10:00');
  const r = await page.evaluate(([TITULO, tapSrc, planSrc]) => {
    const tap = eval(tapSrc), plan = eval(planSrc);
    tap('addSuggestion', { title: TITULO, day: '2026-09-14', time: '15:20' });
    tap('addSuggestion', { title: TITULO, day: '2026-09-15', time: '18:25', repetir: '1' });
    // el 2º entra por el modal; lo confirmamos con «Verla otra vez»
    const cmOk = document.getElementById('cm-ok'); if (cmOk) cmOk.click();
    const antes = plan();
    // ahora tocar «Agendar» sobre una que YA está
    tap('addSuggestion', { title: TITULO, day: '2026-09-15', time: '18:25' });
    return { antes, despues: plan(), modal: !!document.getElementById('conflict-modal') };
  }, [OBRA, TAP, PLAN]);
  expect(r.antes.length).toBe(2);
  expect(r.despues.length).toBe(2);          // no duplicó
  expect(r.modal).toBe(false);               // ni preguntó por algo que ya estaba
});

test('T111 — el modal trae TRES acciones y «Cambiar de función» de verdad cambia (H4)', async ({ page }) => {
  await enterFestival(page, 'tiff2026', '2026-09-09T10:00');
  const r = await page.evaluate(([TITULO, tapSrc, planSrc]) => {
    const tap = eval(tapSrc), plan = eval(planSrc);
    tap('addSuggestion', { title: TITULO, day: '2026-09-14', time: '15:20' });
    const antes = plan();
    tap('addSuggestion', { title: TITULO, day: '2026-09-15', time: '18:25' });
    const botones = [...document.querySelectorAll('#conflict-modal .conflict-modal-btn')]
      .map(b => ({ id: b.id, txt: b.textContent.trim() }));
    const alt = document.getElementById('cm-alt');
    if (alt) alt.click();                     // «Cambiar de función»
    return { antes, botones, despues: plan(), cerrado: !document.getElementById('conflict-modal') };
  }, [OBRA, TAP, PLAN]);
  expect(r.antes.length).toBe(1);
  expect(r.botones.map(b => b.id)).toEqual(['cm-ok', 'cm-alt', 'cm-c']);
  expect(r.cerrado).toBe(true);
  expect(r.despues.length).toBe(1);                        // sigue habiendo UNA
  expect(r.despues[0]).toContain('2026-09-15 18:25');      // y es la NUEVA, no la vieja
});

test('T112 — «Verla otra vez» deja las dos funciones y el plan certifica ok', async ({ page }) => {
  await enterFestival(page, 'tiff2026', '2026-09-09T10:00');
  const r = await page.evaluate(([TITULO, tapSrc, planSrc]) => {
    const tap = eval(tapSrc), plan = eval(planSrc);
    tap('addSuggestion', { title: TITULO, day: '2026-09-14', time: '15:20' });
    tap('addSuggestion', { title: TITULO, day: '2026-09-15', time: '18:25' });
    const cuerpo = (document.querySelector('#conflict-modal .conflict-modal-body') || {}).textContent || '';
    document.getElementById('cm-ok').click();              // «Verla otra vez»
    const v = verifyPlan((savedAgenda && savedAgenda.schedule) || [], { catalog: FILMS });
    return { plan: plan(), cuerpo: cuerpo.replace(/\s+/g, ' ').trim(), ok: !!(v && v.ok), viol: (v && v.violations) || [] };
  }, [OBRA, TAP, PLAN]);
  expect(r.plan.length).toBe(2);
  expect(r.ok).toBe(true);
  expect(r.viol.map(x => x.kind)).not.toContain('duplicado');
  expect(r.cuerpo).toContain('15:20');   // el cuerpo nombra la que YA tenía
});

test('T113 — repetir un par que choca consigo mismo abre el conflicto y NO toca el plan (H7)', async ({ page }) => {
  await enterFestival(page, 'tiff2026', '2026-09-09T10:00');
  const r = await page.evaluate(([TITULO, tapSrc, planSrc]) => {
    const tap = eval(tapSrc), plan = eval(planSrc);
    tap('addSuggestion', { title: TITULO, day: '2026-09-19', time: '18:00' });
    const antes = plan();
    tap('addSuggestion', { title: TITULO, day: '2026-09-19', time: '20:00' });
    const hubo = !!document.getElementById('cm-ok');
    if (hubo) document.getElementById('cm-ok').click();     // «Verla otra vez»
    const sheet = document.getElementById('conflict-sheet');
    return { antes, despues: plan(), hubo, abierto: !!sheet && sheet.classList.contains('open') };
  }, [CHOCA, TAP, PLAN]);
  expect(r.antes.length).toBe(1);
  expect(r.hubo).toBe(true);          // se preguntó, porque el título ya estaba
  expect(r.despues.length).toBe(1);   // el imposible físico NO se agendó
  expect(r.abierto).toBe(true);       // y se le avisó con el sheet de conflicto
});

test('T114 — DESHACER no pregunta: restaura la entrada sin tocar la gemela (H4, 2ª mitad)', async ({ page }) => {
  await enterFestival(page, 'tiff2026', '2026-09-09T10:00');
  const r = await page.evaluate(([TITULO, tapSrc, planSrc]) => {
    const tap = eval(tapSrc), plan = eval(planSrc);
    tap('addSuggestion', { title: TITULO, day: '2026-09-14', time: '15:20' });
    const antes = plan();
    // el botón de deshacer es ESTE MISMO data-action y solo cambia de etiqueta:
    // sin declarar intención abriría el modal, que a quien deshace no le sirve.
    tap('addSuggestion', { title: TITULO, day: '2026-09-15', time: '18:25', restaurar: '1' });
    return { antes, plan: plan(), modal: !!document.getElementById('conflict-modal') };
  }, [OBRA, TAP, PLAN]);
  expect(r.antes.length).toBe(1);
  expect(r.modal).toBe(false);        // deshacer no inventa una pregunta…
  expect(r.plan.length).toBe(2);      // …y la entrada vuelve sin tocar la gemela
  // (la contraprueba —que el camino SIN la marca sí pregunta— la da T111)
});
