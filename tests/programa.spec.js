// @ts-check
// programa.spec.js — Tab Programa: lista, grid, filtros, posters, topbar.
const { test, expect } = require('@playwright/test');
const { LEVIZA_SIMTIME, enterFestival } = require('./helpers');

// T01 — Apóstrofe: corazón en lista agrega al watchlist
test('T01 — apóstrofe: corazón en lista agrega al watchlist', async ({ page }) => {
  await enterFestival(page, 'tribeca2026');
  await page.locator('.dtab[data-day="2026-06-06"]').click();
  await page.waitForSelector('.plist-item', { timeout: 8000 });
  const whoopi = page.locator('.plist-item[data-title*="Whoopi"]').first();
  await whoopi.scrollIntoViewIfNeeded();
  await whoopi.locator('.plist-heart').click();
  await page.waitForFunction(() => watchlist.size > 0, { timeout: 5000 });
  const inWL = await page.evaluate(() =>
    watchlist.has("Shorts: Whoopi's Wonderful World of Animation")
  );
  expect(inWL).toBe(true);
  expect(await page.locator('#pel-sheet.open').count()).toBe(0);
});

// T02 — Apóstrofe: tap en título abre sheet
test('T02 — apóstrofe: tap en título abre sheet', async ({ page }) => {
  await enterFestival(page, 'tribeca2026');
  await page.locator('.dtab[data-day="2026-06-06"]').click();
  await page.waitForSelector('.plist-item', { timeout: 8000 });
  const film = page.locator('.plist-item[data-title*="Here I"]').first();
  await film.scrollIntoViewIfNeeded();
  await film.locator('.plist-info').click();
  await page.waitForSelector('#pel-sheet.open', { timeout: 8000 });
  expect(await page.locator('#pel-sheet.open').count()).toBe(1);
});

// T05 — Corazón en lista NO abre sheet
test('T05 — corazón en lista no abre sheet', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.locator('.dtab[data-day="VIE 15"]').click();
  await page.waitForSelector('.plist-item', { timeout: 8000 });
  await page.locator('.plist-item').first().locator('.plist-heart').click();
  await page.waitForTimeout(300); // mínimo necesario: verificar ausencia de sheet
  expect(await page.locator('#pel-sheet.open').count()).toBe(0);
});

// T06 — Scroll se mantiene después de toggle corazón
test('T06 — scroll se mantiene después de toggle corazón', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.locator('.dtab[data-day="VIE 15"]').click();
  await page.waitForSelector('.plist-item', { timeout: 8000 });
  const items = page.locator('.plist-item');
  const count = await items.count();
  if (count > 2) {
    // Centrar el item objetivo en el viewport — lo deja despejado del header
    // sticky para que el click de Playwright no dispare auto-scroll de actionability.
    await page.evaluate(() => document.querySelectorAll('.plist-item')[2].scrollIntoView({ block: 'center' }));
    await page.waitForTimeout(300);
    const scrollBefore = await page.evaluate(() => window.scrollY);
    await items.nth(2).locator('.plist-heart').click();
    await page.waitForTimeout(400);
    const scrollAfter = await page.evaluate(() => window.scrollY);
    expect(Math.abs(scrollAfter - scrollBefore)).toBeLessThan(50); // scroll preservado tras toggle
  }
});

// T45 — Scroll-preservation: re-render por estado preserva scroll; cambio de día resetea
test('T45 — scroll: toggle preserva posición, cambio de día resetea al tope', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.locator('.dtab[data-day="VIE 15"]').click();
  await page.waitForSelector('.plist-item', { timeout: 8000 });

  // (A) Toggle de watchlist (re-render por estado) NO debe mover el scroll
  await page.evaluate(() => window.scrollTo(0, 250));
  await page.waitForTimeout(200);
  const before = await page.evaluate(() => window.scrollY);
  await page.locator('.plist-item').nth(2).locator('.plist-heart').click();
  await page.waitForFunction(() => watchlist.size > 0, { timeout: 5000 });
  await page.waitForTimeout(300);
  const afterToggle = await page.evaluate(() => window.scrollY);
  expect(Math.abs(afterToggle - before)).toBeLessThan(20); // scroll preservado

  // (B) Cambiar de día (navegación) SÍ resetea al tope
  const otherDay = await page.evaluate(() =>
    [...document.querySelectorAll('.dtab[data-day]')]
      .map(t => t.dataset.day)
      .find(d => d !== 'all' && d !== 'VIE 15') || null
  );
  expect(otherDay).toBeTruthy();
  await page.locator(`.dtab[data-day="${otherDay}"]`).click();
  await page.waitForTimeout(400);
  const afterDayChange = await page.evaluate(() => window.scrollY);
  expect(afterDayChange).toBe(0); // scroll reseteado en cambio de día
});

// T10 — Poster editorial sin truncar en carga inicial
test('T10 — poster editorial: sección completa sin truncar', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.waitForSelector('.poster-card, .plist-item', { timeout: 8000 });
  const content = await page.content();
  expect(content).not.toMatch(/>FICC\s*</);
});

// T12 — Día específico carga en vista lista por defecto
test('T12 — día específico carga en vista lista por defecto', async ({ page }) => {
  test.setTimeout(40000);
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  const activeDay = await page.evaluate(() => activeDay);
  if (activeDay === 'all') return;
  // Esperar a que .plist-item sea visible y .poster-card desaparezca del DOM visible
  await page.waitForSelector('.plist-item', { timeout: 8000 });
  await page.waitForFunction(() => {
    const cards = document.querySelectorAll('.poster-card');
    return Array.from(cards).every(c => getComputedStyle(c).display === 'none' || !c.offsetParent);
  }, { timeout: 8000 }).catch(() => {});
  const listItems = await page.locator('.plist-item:visible').count();
  const gridCards = await page.locator('.poster-card:visible').count();
  expect(listItems).toBeGreaterThan(0);
  expect(gridCards).toBe(0);
});

// T13 — Topbar fecha en una sola línea
test('T13 — topbar fecha en una sola línea', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.waitForSelector('.hdr-fest-dates', { timeout: 5000 });
  const lineCount = await page.evaluate(() => {
    const el = document.querySelector('.hdr-fest-dates');
    if (!el) return -1;
    const style = getComputedStyle(el);
    const lineHeight = parseFloat(style.lineHeight) || parseFloat(style.fontSize) * 1.2;
    return Math.round(el.scrollHeight / lineHeight);
  });
  expect(lineCount).toBe(1);
});

// T20 — TODO muestra vista grid
test('T20 — TODO muestra vista grid', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => { activeDay='all'; programaViewMode='grid'; _renderProgramaContent(); });
  await page.waitForSelector('.poster-card', { timeout: 8000 });
  const cards = await page.locator('.poster-card').count();
  expect(cards).toBeGreaterThan(0);
});

// T21 — Día específico muestra vista lista
test('T21 — día específico muestra vista lista', async ({ page }) => {
  test.setTimeout(40000);
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.waitForSelector('.plist-item', { timeout: 8000 });
  await page.waitForFunction(() => {
    const cards = document.querySelectorAll('.poster-card');
    return Array.from(cards).every(c => getComputedStyle(c).display === 'none' || !c.offsetParent);
  }, { timeout: 8000 }).catch(() => {});
  const grid = await page.locator('.poster-card:visible').count();
  const list = await page.locator('.plist-item:visible').count();
  expect(list).toBeGreaterThan(0);
  expect(grid).toBe(0);
});

// T22 — Toggle de vista grid/lista funciona
test('T22 — toggle grid/lista cambia el modo de vista', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => { activeDay='all'; programaViewMode='grid'; _renderProgramaContent(); });
  await page.waitForSelector('.poster-card', { timeout: 5000 });
  await page.evaluate(() => setProgramaView('list'));
  await page.waitForSelector('.plist-item', { timeout: 5000 });
  const afterToggle = await page.evaluate(() => programaViewMode);
  expect(afterToggle).toBe('list');
});

// T23 — Filtro por día muestra solo films de ese día
test('T23 — filtro por día muestra films del día correcto', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => { activeDay='VIE 15'; programaViewMode='list'; _renderProgramaContent(); });
  await page.waitForSelector('.plist-item', { timeout: 5000 });
  const wrongDay = await page.evaluate(() => {
    return Array.from(document.querySelectorAll('.plist-item')).some(el => {
      const meta = el.querySelector('.plist-meta')?.textContent || '';
      return meta.includes('JUE') || meta.includes('SÁB') || meta.includes('DOM');
    });
  });
  expect(wrongDay).toBe(false);
});

// T41 — Sección del poster no truncada en grid
test('T41 — sección del poster no truncada en grid', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME);
  await page.evaluate(() => { activeDay='all'; programaViewMode='grid'; _renderProgramaContent(); });
  await page.waitForSelector('.poster-card', { timeout: 8000 });
  const content = await page.content();
  expect(content).not.toMatch(/>FICC\s*</);
  expect(content).not.toMatch(/>COMP\s*</);
});

// ── T46/T47 — filtro de lugar con NIVEL DE CIUDAD (5 ago 2026) ────────────────
// FICDEH 2026: 11 ciudades, 131 sedes, 416 funciones — la lista plana eran 12,5
// pantallas de scroll y el usuario de Tunja tenía que recorrer las de Bogotá.
// Anatomía aprobada por Juan: nivel 1 = ciudades (caben sin scroll), nivel 2 =
// "‹ Ciudades" + la ciudad (filtra entera) + sus sedes. SOLO en multiciudad:
// con una sola ciudad el filtro queda EXACTO como siempre (T47 lo congela).
test('T46 — multiciudad: el filtro abre por ciudad y se puede filtrar la ciudad entera', async ({ page }) => {
  await enterFestival(page, 'cinemancia2025');
  await page.evaluate(() => switchMainNav('mnav-cartelera'));
  await page.waitForTimeout(300);
  await page.evaluate(() => document.getElementById('lugar-btn').click());
  await page.waitForSelector('#lugar-drop', { timeout: 5000 });

  const n1 = await page.evaluate(() => [...document.querySelectorAll('#lugar-drop .lugar-opt')].map(o => o.dataset.v));
  expect(n1[0]).toBe('all');
  expect(n1.filter(v => v.startsWith('drill:')).length).toBeGreaterThanOrEqual(2); // ciudades, no sedes
  expect(n1.some(v => v === 'Colombo Americano')).toBe(false);                     // las sedes NO están en el nivel 1

  // entrar a una ciudad → "‹ Ciudades" + la ciudad + sus sedes
  await page.evaluate(() => document.querySelector('#lugar-drop [data-v="drill:Medellín"]').click());
  await page.waitForTimeout(200);
  const n2 = await page.evaluate(() => [...document.querySelectorAll('#lugar-drop .lugar-opt')].map(o => o.dataset.v));
  expect(n2[0]).toBe('back');
  expect(n2[1]).toBe('city:Medellín');
  expect(n2.length).toBeGreaterThan(2);
  // el drill NO cierra el dropdown (regresión: el repintado dejaba huérfano el
  // e.target y lugarOutside lo cerraba — por eso stopPropagation)
  expect(await page.evaluate(() => !!document.getElementById('lugar-drop'))).toBe(true);

  // volver
  await page.evaluate(() => document.querySelector('#lugar-drop [data-v="back"]').click());
  await page.waitForTimeout(200);
  expect(await page.evaluate(() => document.querySelector('#lugar-drop .lugar-opt').dataset.v)).toBe('all');

  // filtrar la ciudad entera
  await page.evaluate(() => document.querySelector('#lugar-drop [data-v="drill:Medellín"]').click());
  await page.waitForTimeout(200);
  await page.evaluate(() => document.querySelector('#lugar-drop [data-v="city:Medellín"]').click());
  await page.waitForTimeout(700);
  const tras = await page.evaluate(() => ({
    sel: activeVenue,
    pill: document.querySelector('.paf-pill')?.innerText.replace(/\s+/g, ' ').trim(),
    items: document.querySelectorAll('.poster-card, .plist-item').length,
  }));
  expect(tras.sel).toBe('city:Medellín');
  expect(tras.pill).toContain('Medellín');
  expect(tras.pill).not.toContain('city:');   // el centinela no se filtra a la UI
  expect(tras.items).toBeGreaterThan(0);
});

test('T47 — festival de una ciudad: el filtro sigue plano, sin nivel de ciudad', async ({ page }) => {
  await enterFestival(page, 'finca2026', '2026-08-13T10:00');
  await page.evaluate(() => switchMainNav('mnav-cartelera'));
  await page.waitForTimeout(300);
  await page.evaluate(() => document.getElementById('lugar-btn').click());
  await page.waitForSelector('#lugar-drop', { timeout: 5000 });
  const v = await page.evaluate(() => [...document.querySelectorAll('#lugar-drop .lugar-opt')].map(o => o.dataset.v));
  expect(v[0]).toBe('all');
  expect(v.some(x => x.startsWith('drill:'))).toBe(false);
  expect(v.some(x => x.startsWith('city:'))).toBe(false);
  expect(v.length).toBeGreaterThan(1);        // y sigue listando sus sedes
});

// ── T48 — los paneles de filtro nunca se salen del viewport ───────────────────
// Bug real (FICDEH, 6 ago 2026): el panel se anclaba al borde derecho de su
// botón sin tope. Con el botón "Sección" terminando en x=274 de 375 y el panel
// en su ancho máximo (300px), el borde izquierdo caía en -26px: se leía "odo el
// programa" sin la T y los emojis de sección salían partidos. No lo introdujo
// FICDEH — le pasa a cualquier festival cuyo panel llegue a 300px.
test('T48 — los paneles de Sección y Lugar caben en pantalla (375px, el peor caso)', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 844 });
  await enterFestival(page, 'tribeca2026');
  await page.evaluate(() => switchMainNav('mnav-cartelera'));
  await page.waitForTimeout(300);
  for (const [btn, drop] of [['seccion-btn', 'seccion-drop'], ['lugar-btn', 'lugar-drop']]) {
    await page.evaluate(id => document.getElementById(id).click(), btn);
    await page.waitForSelector(`#${drop}`, { timeout: 5000 });
    const box = await page.evaluate(id => {
      const r = document.getElementById(id).getBoundingClientRect();
      return { left: Math.round(r.left), right: Math.round(r.right), w: Math.round(r.width) };
    }, drop);
    expect(box.left, `${drop} se sale por la izquierda`).toBeGreaterThanOrEqual(0);
    expect(box.right, `${drop} se sale por la derecha`).toBeLessThanOrEqual(375);
    await page.evaluate(id => document.getElementById(id)?.remove(), drop);
  }
});

// ── T49/T50 — la CIUDAD como contexto (FICDEH, 6 ago 2026) ───────────────────
// FICDEH: 11 ciudades, 387 funciones. Dos problemas que resolvió este bloque:
//   · el modo por días mezclaba las 11 sin decir cuál era cuál — había que abrir
//     cada ficha para saber si la función era alcanzable;
//   · el filtro de ciudad se perdía al cambiar de día y al cerrar la app.
// Doctrina: la ciudad filtra lo que DESCUBRÍS (Programa/Días), nunca lo que YA
// ELEGISTE (Mi Plan). Y es contexto: se recuerda; la sede no.
test('T49 — multiciudad: cada card del modo por días dice su ciudad', async ({ page }) => {
  await enterFestival(page, 'cinemancia2025');
  // El día con MÁS funciones — un DAY_KEYS fijo puede caer en un día vacío y el
  // test pasaría sin ejercer nada (pasó: skip silencioso, cazado por mutación).
  await page.evaluate(() => {
    switchMainNav('mnav-cartelera');
    const cnt = {}; FILMS.forEach(f => { if (f.day) cnt[f.day] = (cnt[f.day] || 0) + 1; });
    activeDay = Object.keys(cnt).sort((a, b) => cnt[b] - cnt[a])[0];
    programaViewMode = 'list';   // el modo POR DÍAS es la lista (el grid son pósters)
    _renderProgramaContent();
  });
  await page.waitForTimeout(500);
  const r = await page.evaluate(() => {
    const items = [...document.querySelectorAll('.plist-item')];
    return { items: items.length, conCiudad: items.filter(i => i.querySelector('.plist-city')).length };
  });
  expect(r.items, 'el día elegido tiene que tener funciones o el test no prueba nada').toBeGreaterThan(0);
  expect(r.conCiudad).toBe(r.items);   // TODAS, no algunas
});

test('T50 — la ciudad se recuerda entre sesiones; la sede no', async ({ page }) => {
  await enterFestival(page, 'cinemancia2025');
  await page.evaluate(() => { switchMainNav('mnav-cartelera'); });
  await page.waitForTimeout(300);
  // elegir una ciudad por la UI real
  await page.evaluate(() => document.getElementById('lugar-btn').click());
  await page.waitForSelector('#lugar-drop', { timeout: 5000 });
  const ciudad = await page.evaluate(() => {
    const d = [...document.querySelectorAll('#lugar-drop .lugar-opt')].find(o => o.dataset.v.startsWith('drill:'));
    d.click(); return d.dataset.v.slice(6);
  });
  await page.waitForTimeout(200);
  await page.evaluate(c => document.querySelector(`#lugar-drop [data-v="city:${c}"]`).click(), ciudad);
  await page.waitForTimeout(600);

  const guardado = await page.evaluate(() => localStorage.getItem('cinemancia2025_city'));
  expect(guardado).toBe('city:' + ciudad);

  // cambiar de DÍA no la pierde (antes sí: activeVenue se reseteaba a 'all')
  await page.evaluate(() => { const t = [...document.querySelectorAll('.dtab')].find(x => x.dataset.day && x.dataset.day !== 'all' && x.dataset.day !== activeDay); t && t.click(); });
  await page.waitForTimeout(600);
  expect(await page.evaluate(() => activeVenue)).toBe('city:' + ciudad);

  // reabrir la app: sigue en su ciudad
  await enterFestival(page, 'cinemancia2025');
  expect(await page.evaluate(() => activeVenue)).toBe('city:' + ciudad);

  // y se puede SALIR: quitar el chip la olvida
  await page.evaluate(() => { switchMainNav('mnav-cartelera'); });
  await page.waitForTimeout(300);
  await page.evaluate(() => document.querySelector('.paf-pill[data-action="pafClearVenue"]')?.click());
  await page.waitForTimeout(500);
  expect(await page.evaluate(() => activeVenue)).toBe('all');
  expect(await page.evaluate(() => localStorage.getItem('cinemancia2025_city'))).toBeFalsy();
});

// ── T51 — el badge de precio marca la MINORÍA ────────────────────────────────
// FICDEH 2026 (81% de entrada libre) invirtió la premisa de la app: el badge
// GRATIS pintaba 313 de 384 funciones y escondía las 71 accionables. La regla
// pasó a ser "marcá la minoría" y la decide ticketBadgeTarget() una vez por
// festival. Este test congela el OTRO lado: en los festivales donde lo gratuito
// sigue siendo la excepción, nada cambió — el badge GRATIS sigue exactamente
// donde estaba. (El lado invertido lo cubre tests/unit/ticketBadgeTarget.test.js
// con las proporciones reales de ambos festivales.)
test('T51 — donde gratis es la excepción, el badge GRATIS sigue igual', async ({ page }) => {
  await enterFestival(page, 'tercertiempo2026');
  await page.evaluate(() => { switchMainNav('mnav-cartelera'); activeDay = 'all'; programaViewMode = 'list'; _renderProgramaContent(); });
  await page.waitForTimeout(500);

  const r = await page.evaluate(() => {
    const items = [...document.querySelectorAll('.plist-item')];
    const badges = items.flatMap(i => [...i.querySelectorAll('.meta-badge')].map(b => b.textContent));
    const reales = FILMS.filter(f => !f.info && f.day && f.time);
    return {
      target: ticketBadgeTarget(),
      libres: reales.filter(f => f.is_free === true).length,
      total: reales.length,
      gratis: badges.filter(b => /GRATIS|FREE/i.test(b)).length,
      boleta: badges.filter(b => /BOLETA|TICKETED/i.test(b)).length,
    };
  });
  expect(r.libres * 2).toBeLessThan(r.total);      // premisa del escenario
  expect(r.target).toBe('free');
  expect(r.gratis).toBeGreaterThan(0);             // sigue marcando las gratuitas
  expect(r.boleta).toBe(0);                        // y NO invade con CON BOLETA
});

// ── T52 — el sheet de ciudad: se pregunta UNA vez, y solo si hay que preguntar ─
// FICDEH 2026 abre en 11 ciudades: entrar al programa y ver las 11 mezcladas no
// es un catálogo, es ruido. El sheet pregunta al entrar, guarda la respuesta y
// no vuelve a preguntar. En un festival de una ciudad no existe.
test('T52 — sheet de ciudad: solo multiciudad, y no reaparece', async ({ page }) => {
  // mono-ciudad: el sheet NO existe
  await enterFestival(page, 'tercertiempo2026');
  await page.waitForTimeout(600);
  expect(await page.evaluate(() => document.getElementById('city-sheet')?.classList.contains('open'))).toBeFalsy();

  // multiciudad: aparece con una fila por ciudad + la salida
  await enterFestival(page, 'cinemancia2025');
  await page.waitForSelector('#city-sheet.open', { timeout: 5000 });
  const filas = await page.evaluate(() => ({
    ciudades: document.querySelectorAll('#city-sheet-list .lugar-opt.city').length,
    salida: !!document.querySelector('#city-sheet-list .lugar-opt.escape'),
    nombre: document.querySelector('#city-sheet-list .lugar-opt.city span').textContent.trim(),
  }));
  expect(filas.ciudades).toBeGreaterThan(1);
  expect(filas.salida).toBe(true);

  // elegir ciudad: filtra, cierra y queda recordada
  await page.evaluate(() => document.querySelector('#city-sheet-list .lugar-opt.city').click());
  await page.waitForTimeout(600);
  expect(await page.evaluate(() => activeVenue)).toBe('city:' + filas.nombre);
  expect(await page.evaluate(() => document.getElementById('city-sheet').classList.contains('open'))).toBe(false);

  // reabrir: ya respondió, no se vuelve a preguntar
  await enterFestival(page, 'cinemancia2025');
  await page.waitForTimeout(900);
  expect(await page.evaluate(() => document.getElementById('city-sheet').classList.contains('open'))).toBe(false);
  expect(await page.evaluate(() => activeVenue)).toBe('city:' + filas.nombre);
});

// La salida ("ver todas") también es una respuesta: no puede reabrir el sheet en
// bucle cada vez que el usuario entra.
test('T53 — "ver todas" se recuerda como respuesta, no como silencio', async ({ page }) => {
  await enterFestival(page, 'cinemancia2025');
  await page.waitForSelector('#city-sheet.open', { timeout: 5000 });
  await page.evaluate(() => document.querySelector('#city-sheet-list .lugar-opt.escape').click());
  await page.waitForTimeout(500);
  expect(await page.evaluate(() => activeVenue)).toBe('all');

  await enterFestival(page, 'cinemancia2025');
  await page.waitForTimeout(900);
  expect(await page.evaluate(() => document.getElementById('city-sheet').classList.contains('open'))).toBe(false);
});

// ── T54 — el aviso parcial nombra la CIUDAD cuando la obra recorre varias ────
// FICDEH 2026 estrenó un mecanismo que ningún festival había ejercido: un rasgo
// (precio, Q&A, inscripción) presente en ALGUNAS funciones y no en todas, con
// esas funciones repartidas en ciudades distintas — 43 obras.
// «One in a million» es gratis en Medellín y con boleta en Bogotá; el aviso
// desambiguaba por fecha y hora, y había que cruzar «sáb 15 · 19:00» a mano
// contra la lista de funciones para descubrir que hablaba de OTRA ciudad.
// La ciudad se agrega solo si la obra recorre ≥2: si todas sus funciones están
// en la misma, nombrarla no distingue nada y sería ruido en cada línea.
test('T54 — el aviso dice la ciudad solo cuando la obra recorre varias', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-12T09:00:00-05:00');
  const avisos = async (titulo) => {
    await page.evaluate(() => { try { closePelSheet(); } catch (e) {} });
    await page.waitForTimeout(500);
    await page.evaluate(t => openPelSheet(t), titulo);
    await page.waitForTimeout(800);
    return page.evaluate(() => [...document.querySelectorAll('[class*="aviso"]')]
      .map(e => e.textContent.replace(/\s+/g, ' ').trim()).find(x => /entrada/.test(x)) || '');
  };
  // recorre 2 ciudades → la ciudad es lo que separa las funciones
  const varias = await avisos('One in a million');
  expect(varias, 'el aviso debe nombrar la ciudad').toContain('Bogotá');
  expect(varias).toMatch(/sáb 15/);

  // 3 funciones, todas en Bogotá → la ciudad no distingue: no se dice
  const una = await avisos('Los pliegues de la falda');
  expect(una, 'aviso parcial presente').toMatch(/lun 17/);
  expect(una, 'con una sola ciudad, nombrarla es ruido').not.toContain('Bogotá');
});

// ── T55 — la ficha hereda el contexto de ciudad ──────────────────────────────
// Con Medellín elegido, «One in a million» mostraba sus 2 funciones y un aviso de
// boletería que era de Bogotá: información de una ciudad a la que no vas y encima
// engañosa, porque en Medellín esa función es gratis.
// La excepción NO es negociable: una función que ya está en tu plan se muestra
// siempre, aunque sea de otra ciudad — si no, la app te ofrecería «Agregar» algo
// que ya tenés. Es la doctrina de #504: la ciudad filtra lo que descubrís, nunca
// lo que ya elegiste.
test('T55 — la ficha filtra por ciudad, pero nunca esconde lo que ya elegiste', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-12T09:00:00-05:00');
  await page.waitForTimeout(500);
  await page.evaluate(() => {
    const f = [...document.querySelectorAll('#city-sheet-list .lugar-opt.city')].find(x => /Medell/.test(x.textContent));
    if (f) f.click();
  });
  await page.waitForTimeout(600);

  const ficha = async () => {
    await page.evaluate(() => { try { closePelSheet(); } catch (e) {} });
    await page.waitForTimeout(400);
    await page.evaluate(() => openPelSheet('One in a million'));
    await page.waitForTimeout(900);
    return page.evaluate(() => ({
      funciones: document.querySelectorAll('#pel-sheet .pel-sheet-screening').length,
      ciudadBanner: document.querySelector('#pel-sheet .fn-ciudad')?.textContent || '',
      ciudadEnFilas: document.querySelectorAll('#pel-sheet .venue-municipio').length,
      nota: document.querySelector('#pel-sheet .fn-otra-ciudad')?.textContent || '',
      avisos: !!document.querySelector('#pel-sheet .avisos-body'),
    }));
  };

  const a = await ficha();
  expect(a.funciones, 'solo la función de Medellín').toBe(1);
  expect(a.ciudadBanner).toBe('Medellín');
  expect(a.ciudadEnFilas, 'la ciudad se dice UNA vez, en el banner').toBe(0);
  expect(a.nota).toMatch(/otra ciudad/);
  expect(a.avisos, 'en Medellín es gratis: la banda AVISOS no debe quedar vacía').toBe(false);

  // la función de Bogotá entra al plan → deja de ser "descubrimiento"
  await page.evaluate(() => {
    const b = FILMS.find(f => f.title === 'One in a million' && /Cinemateca/.test(f.venue || ''));
    state.set('savedAgenda', { schedule: [{ _title: b.title, title: b.title, day: b.day,
      time: b.time, venue: b.venue, duration: b.duration, day_order: b.day_order }] });
  });
  const b = await ficha();
  expect(b.funciones, 'lo que ya elegiste se muestra aunque sea de otra ciudad').toBe(2);
  expect(b.nota, 'ya no queda nada fuera').toBe('');
});

// T60 — el corazón dice lo MISMO desde la ficha que desde la grilla
// Re-corrida del QA de ojos frescos (16 ago 2026): agregar desde la ficha una
// obra anclada sumaba 12 obras y anunciaba solo «En Intereses», mientras la
// grilla decía «+11 cortos del mismo programa». La causa no era la mutación
// —togglePelWL delega en toggleWL— sino que el envoltorio tiraba su PROPIO toast
// DESPUÉS y pisaba el verdadero. El dueño del mensaje es toggleWL.
test('T60 — el toast del corazón es el mismo desde la ficha y desde la grilla', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-16T10:00');
  const anclada = await page.evaluate(() => {
    const conSlot = FILMS.filter(f => f._slotKey);
    const cuenta = {};
    conSlot.forEach(f => { cuenta[f._slotKey] = (cuenta[f._slotKey] || 0) + 1; });
    const k = Object.keys(cuenta).find(x => cuenta[x] >= 3);
    return conSlot.find(f => f._slotKey === k).title;
  });
  const leerToast = () => page.evaluate(() => {
    const el = document.querySelector('.toast, [class*=toast]');
    return el ? el.innerText.replace(/\n/g, ' ').trim() : '';
  });

  // desde la GRILLA
  await page.evaluate((t) => { watchlist.clear(); toggleWL(t); }, anclada);
  await page.waitForTimeout(500);
  const grilla = await leerToast();

  // desde la FICHA
  await page.evaluate((t) => { watchlist.clear(); openPelSheet(t); }, anclada);
  await page.waitForSelector('#pel-wl-btn', { timeout: 8000 });
  await page.evaluate(() => document.getElementById('pel-wl-btn').click());
  await page.waitForTimeout(700);
  const ficha = await leerToast();

  expect(grilla, 'la grilla nombra cuántas obras arrastró').toMatch(/\+\d+/);
  expect(ficha, 'la ficha dice lo mismo que la grilla').toBe(grilla);
});

// T63 — la píldora Hoy/Mañana ESPEJA a su chip de día (ronda 3 + Juan, 16 ago)
// La píldora es doble: botón (atajo al día) e indicador. La mitad de indicador
// mentía: pintada desde programaSubMode quedaba subrayada mostrando MAR 18, y
// nunca se atenuaba con su día agotado. Ahora deriva de activeDay (subrayado)
// y dayFullyPassed (opacidad) — los mismos dueños del chip.
test('T63 — la píldora Hoy espeja al día: se apaga en otro día, vuelve en hoy, se atenúa agotada', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-16T10:00');
  const claves = await page.evaluate(() => {
    const hoy = DAY_KEYS.find(d => FESTIVAL_DATES[d] === simTodayStr());
    const i = DAY_KEYS.indexOf(hoy);
    // ni hoy ni MAÑANA: si tomás hoy+1, «Mañana» encendida es lo CORRECTO y el
    // test se acusa solo (pasó en la primera corrida).
    const otro = DAY_KEYS[i + 2];
    return { hoy, otro };
  });
  const leer = () => page.evaluate(() => ({
    hoyOn: document.getElementById('pmode-hoy')?.classList.contains('on'),
    hoyPast: document.getElementById('pmode-hoy')?.classList.contains('past'),
    mananaOn: document.getElementById('pmode-manana')?.classList.contains('on'),
  }));

  // Se opera por los BOTONES reales (dispatcher incluido): la píldora y los chips.
  // (a) el atajo enciende su píldora
  await page.evaluate(() => document.getElementById('pmode-hoy').click());
  await page.waitForTimeout(300);
  expect((await leer()).hoyOn, 'atajo Hoy → píldora encendida').toBe(true);

  // (b) chip de OTRO día → ambas píldoras apagadas (el caso del agente)
  await page.evaluate((c) => document.querySelector(`.dtab[data-day="${c.otro}"]`).click(), claves);
  await page.waitForTimeout(300);
  const b = await leer();
  expect(b.hoyOn, 'viendo otro día, Hoy se apaga').toBe(false);
  expect(b.mananaOn, 'y Mañana también').toBe(false);

  // (c) chip del día de HOY → la píldora Hoy vuelve, aunque no viniste por el atajo
  await page.evaluate((c) => document.querySelector(`.dtab[data-day="${c.hoy}"]`).click(), claves);
  await page.waitForTimeout(300);
  expect((await leer()).hoyOn, 'chip de hoy → Hoy encendida').toBe(true);

  // (d) con el día de hoy AGOTADO, la píldora se atenúa igual que su chip
  // (la mitad que vio Juan). Se llega por el camino real: mover el reloj y
  // tocar un chip — el mismo gesto que dispara el espejo en producción.
  await page.evaluate((c) => { _simTime = '2026-08-16T23:50:00-05:00';
    document.querySelector(`.dtab[data-day="${c.otro}"]`).click(); }, claves);
  await page.waitForTimeout(400);
  const d = await leer();
  expect(d.hoyPast, 'hoy agotado → píldora opaca').toBe(true);
  expect(d.hoyOn, 'y sigue sin estar activa (estás en otro día)').toBe(false);
  const chipPast = await page.evaluate((c) =>
    document.querySelector(`.dtab[data-day="${c.hoy}"]`).classList.contains('past'), claves);
  expect(chipPast, 'el chip de hoy también está opaco: píldora y chip coinciden').toBe(true);
});

// T64 — el aviso de función compartida nombra el vínculo, y el número solo si es cierto
// Ronda 3 (FINCA): «Programa · Verás las otras obras» describía la SALA, no la
// consecuencia de marcar, y el usuario se sorprendió al ver dos obras marcadas.
// Ahora nombra el vínculo. El NÚMERO solo si todas las funciones VISIBLES
// coinciden: «Madres de nacimiento» tiene funciones con 4, 5, 6 y 0 compañeras
// —la unión da 11 y ninguna función tiene 11—, y afirmarlo sería falso.
test('T64 — «Va con otras N obras» solo cuando todas sus funciones coinciden', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-16T09:00');
  const caso = await page.evaluate(() => {
    const bog = f => (f.venue || '').includes('Bogotá');
    // Ambos casos se buscan sobre las funciones VISIBLES (futuras + ciudad),
    // que son exactamente las que mira la ficha. Buscar el caso variable sobre
    // TODAS las funciones elegía una obra que en Bogotá sí es uniforme, y el
    // test sobrevivía a la mutación.
    const vis = {};
    FILMS.filter(f => f._slotKey && f.day >= '2026-08-17' && bog(f))
      .forEach(f => (vis[f.title] = vis[f.title] || []).push(f));
    const cuentas = (scr, t) => { const c = new Set(scr.map(sc =>
      new Set(FILMS.filter(o => o._slotKey === sc._slotKey && o.title !== t).map(o => o.title)).size));
      c.delete(0); return c; };
    let uniforme = null, n = 0, variable = null;
    for (const [t, scr] of Object.entries(vis)) { const c = cuentas(scr, t);
      if (c.size === 1 && [...c][0] > 1) { uniforme = t; n = [...c][0]; break; } }
    for (const [t, scr] of Object.entries(vis)) { if (cuentas(scr, t).size > 1) { variable = t; break; } }
    return { uniforme, n, variable };
  });
  expect(caso.uniforme, 'FICDEH tiene un caso uniforme').not.toBeNull();

  // La ciudad se elige por la UI (el camino real): setear activeVenue a mano
  // deja el sheet de ciudad abierto y la ficha no hereda el contexto igual.
  await page.evaluate(() => {
    const r = [...document.querySelectorAll('#city-sheet [data-action]')]
      .find(x => x.textContent.includes('Bogotá'));
    if (r) r.click();
  });
  await page.waitForTimeout(600);

  const avisoDe = async (titulo) => {
    await page.evaluate((t) => openPelSheet(t), titulo);
    await page.waitForSelector('#pel-sheet.open', { timeout: 8000 });
    await page.waitForTimeout(400);
    return page.evaluate(() => [...document.querySelectorAll(
      '#pel-sheet .meta-banner-text, #pel-sheet [class*=aviso] *')]
      .map(e => e.textContent.replace(/\s+/g, ' ').trim())
      .find(x => /(obras|cortos)/i.test(x) && x.length < 120) || '');
  };

  const conNumero = await avisoDe(caso.uniforme);
  expect(conNumero, 'coinciden → dice el número').toContain(`otras ${caso.n} obras`);
  expect(conNumero, 'y nombra el vínculo, no la sala').toContain('en la misma función');
  expect(conNumero, 'ya no describe lo que verás').not.toMatch(/Verás/);

  expect(caso.variable, 'FICDEH tiene un caso variable').not.toBeNull();
  const sinNumero = await avisoDe(caso.variable);
  expect(sinNumero, 'si varían, nombra el vínculo igual').toContain('en la misma función');
  expect(sinNumero, 'si varían, NO inventa un número').not.toMatch(/otras \d+ obras/);
});

// Ronda 3 (FINCA): «Sin actividades disponibles» hablaba del INVENTARIO —sonaba
// a que el festival nunca programó la obra— cuando el hecho era temporal. Medido
// en los 3 festivales activos (564 entradas): CERO obras sin función, así que esa
// frase SOLO se leía sobre obras cuyas funciones ya pasaron.
test('T65 — una obra cuyas funciones pasaron dice «Ya pasó», no que no exista', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-18T20:00');
  await page.evaluate(() => document.querySelector('[data-action="citySheetAll"]')?.click());
  await page.waitForTimeout(500);

  // Sembrar intereses con una obra cuyas funciones quedaron TODAS atrás.
  // Se siembran VARIAS: no toda entrada del catálogo tiene fila propia en
  // Intereses (un corto vive dentro de su programa), y con una sola el test
  // dependía de cuál saliera primero.
  const pasadas = await page.evaluate(() => {
    const ts = [...new Set(FILMS.map(f => f.title))]
      .filter(ti => FILMS.every(f => f.title !== ti || screeningPassed(f))).slice(0, 6);
    const k = localStorage.getItem('otrofestiv_festival') + '_';
    localStorage.setItem(k + 'wl', JSON.stringify(ts));
    localStorage.setItem(k + 'prio', JSON.stringify(ts.slice(0, 1)));
    return ts;
  });
  expect(pasadas.length, 'FICDEH tiene obras con todas sus funciones pasadas').toBeGreaterThan(0);

  await page.reload();
  await page.waitForSelector('.splash-card');
  await page.click('#splash-enter-btn');
  await page.waitForTimeout(2500);
  await page.evaluate(() => document.querySelector('[data-action="citySheetAll"]')?.click());
  await page.waitForTimeout(400);
  await page.click('#mnav-seleccion');
  await page.waitForTimeout(1200);

  const etiquetas = await page.evaluate(() =>
    [...document.querySelectorAll('.int-item-gone, .prio-chip-past-lbl')].map(e => e.textContent.trim()));
  expect(etiquetas.length, 'la obra pasada se marca').toBeGreaterThan(0);
  expect(etiquetas.join(' | '), 'dice el hecho temporal').toContain('Ya pasó');
  expect(etiquetas.join(' | '), 'y ya no habla del inventario')
    .not.toContain('Sin actividades disponibles');
});

// Ronda 3 (FINCA): Mi Plan mostraba «Día cubierto · No hay más actividades que
// quepan hoy» en días que YA PASARON (medido: los cinco días previos), y la caja
// «Día libre → mirá abajo» mandaba a un Sugerencias vacío. Dos raíces: el copy
// hablaba de «hoy» aunque la sección se calcula sobre el día SELECCIONADO, y la
// promesa no se verificaba antes de hacerse.
test('T66 — Sugerencias habla del día que mirás, y no promete lo que no tiene', async ({ page }) => {
  const sembrar = async (simTime, diaPlan) => {
    await enterFestival(page, 'ficdeh2026', simTime);
    await page.evaluate(() => document.querySelector('[data-action="citySheetAll"]')?.click());
    await page.waitForTimeout(400);
    await page.evaluate((d) => {
      const fut = FILMS.filter(f => f.day >= d);
      state.set('watchlist', new Set([...new Set(fut.map(f => f.title))].slice(0, 12)));
      const f = FILMS.find(x => x.day === d);
      state.set('savedAgenda', { scenarioIdx: 0, schedule: [Object.assign({}, f, { _title: f.title })] });
      switchMainNav('mnav-miplan'); showAgView();
    }, diaPlan);
    await page.waitForTimeout(1200);
  };
  const mirarDia = async (dia) => {
    await page.evaluate((d) => {
      const i = DAY_KEYS.indexOf(d);
      [...document.querySelectorAll('[data-action="selectMiPlanDay"]')]
        .filter(x => x.dataset.index === String(i))[0]?.click();
    }, dia);
    await page.waitForTimeout(700);
    return page.evaluate(() => ({
      bloqueSugs: !!document.querySelector('.suggestion-wrap'),
      sugs: document.querySelectorAll('.suggestion-item').length,
      ctaConDestino: !!document.querySelector('[data-action="scrollToSuggestions"]'),
      txt: document.body.innerText.replace(/\s+/g, ' '),
    }));
  };

  // El instante lleva offset explícito (-05:00, Colombia): sin él, `new Date()`
  // lo lee en la zona del navegador y en CI (UTC) las 22:30 del caso 3 eran las
  // 17:30 locales — todavía con funciones por delante.
  // 1· Un día que ya pasó no tiene nada que sugerir: la sección no se dibuja.
  await sembrar('2026-08-17T09:00:00-05:00', '2026-08-17');
  const pasado = await mirarDia('2026-08-14');
  expect(pasado.bloqueSugs, 'día pasado: sin bloque de Sugerencias').toBe(false);
  expect(pasado.txt, 'y sin «hoy» sobre un día que no es hoy').not.toContain('quepan hoy');
  expect(pasado.txt, 'ni «cubierto» sobre un día vacío').not.toContain('Día cubierto');

  // 2· Un día futuro CON sugerencias sigue ofreciendo el atajo.
  const conSugs = await mirarDia('2026-08-19');
  expect(conSugs.sugs, 'el 19 tiene sugerencias').toBeGreaterThan(0);
  expect(conSugs.ctaConDestino, 'con material, la caja sí lleva abajo').toBe(true);

  // 2b· Un día futuro CON bloque pero SIN material (Tunja no programa el 19):
  //     el vacío de la sección nombra el día en vez de decir «hoy».
  await page.evaluate(() => { activeVenue = 'city:Tunja'; showAgView(); });
  await page.waitForTimeout(900);
  const seco19 = await mirarDia('2026-08-19');
  expect(seco19.bloqueSugs, 'el 19 no pasó: la sección sigue ahí').toBe(true);
  expect(seco19.sugs, 'pero Tunja no programa ese día').toBe(0);
  expect(await page.evaluate(() => document.querySelector('.suggestion-wrap')?.innerText || ''),
    'el vacío de la sección nombra el día').toContain('Sin más opciones para el MIÉ 19');

  // 3· El día en curso ya sin nada: nombra el día y NO ofrece destino.
  await sembrar('2026-08-19T22:30:00-05:00', '2026-08-17');
  const seco = await mirarDia('2026-08-19');
  expect(seco.sugs, 'a las 22:30 del último día no queda nada').toBe(0);
  expect(seco.ctaConDestino, 'sin material, no manda a ningún lado').toBe(false);
  expect(seco.txt, 'y nombra el día en vez de decir «hoy»').toContain('Sin más opciones para el MIÉ 19');
});

// Ronda 3 (FINCA): el Diario tenía UNA puerta —el chip del progreso— y no decía
// a dónde iba: «14 obras vistas ✓ ›» describe un contador. La palabra «Diario»
// solo existía DENTRO del Diario y en la imagen que se comparte, o sea después
// de llegar. Misma regla que los toasts: un control nombra su destino.
test('T67 — el chip nombra el Diario, y el Recuerdo lo presenta', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-17T20:00:00-05:00');
  await page.evaluate(() => document.querySelector('[data-action="citySheetAll"]')?.click());
  await page.waitForTimeout(400);
  const pintar = async () => {
    await page.evaluate(() => {
      const tits = [...new Set(FILMS.filter(f => f.day <= '2026-08-17').map(f => f.title))];
      state.set('watched', new Set(tits.slice(0, 14)));
      const f = FILMS.find(x => x.day === '2026-08-17');
      state.set('savedAgenda', { scenarioIdx: 0, schedule: [Object.assign({}, f, { _title: f.title })] });
      switchMainNav('mnav-miplan'); showAgView();
    });
    await page.waitForTimeout(900);
  };
  await pintar();
  const chip = await page.evaluate(() => {
    const c = document.querySelector('.diary-chip');
    return c && { txt: c.innerText.replace(/\s+/g, ' ').trim(),
      ancho: Math.round(c.getBoundingClientRect().width),
      icono: !!c.querySelector('svg'),
      badge: !!c.querySelector('.count-badge'),
      desborda: c.getBoundingClientRect().right > 390 };
  });
  expect(chip, 'con obras vistas hay chip').toBeTruthy();
  expect(chip.txt, 'el chip nombra su destino').toContain('Diario');
  expect(chip.icono, 'con icono, como todo encabezado').toBe(true);
  expect(chip.badge, 'y la cuenta como badge, no en palabras').toBe(true);
  expect(chip.txt, 'la cuenta no se repite en palabras').not.toMatch(/obras? vistas?/);
  expect(chip.desborda, 'sin desbordar los 390 px').toBe(false);

  // Y después del festival, el bloque del Recuerdo se presenta con su nombre.
  await page.evaluate(() => { _simTime = '2026-08-21T12:00:00-05:00'; showAgView(); });
  await page.waitForTimeout(1000);
  const retro = await page.evaluate(() =>
    [...document.querySelectorAll('.sec-hdr')].map(e => e.textContent.trim()));
  expect(retro.join(' | '), 'el Diario retro lleva encabezado').toContain('Diario');
});

// Ronda 3 (FICDEH): «Cambiar de actividad» ofrecía las HERMANAS del mismo bloque
// —misma sala, misma hora, la misma función— así que el cambio no cambiaba nada
// real, pero el plan sí lo registraba y después Sugerencias ofrecía «Restaurar»
// lo recién sacado. Medido con «Sukua»: 5 alternativas, 4 eran compañeras.
test('T68 — el panel de alternativas no ofrece compañeras de la misma función', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-13T09:00:00-05:00');
  await page.evaluate(() => document.querySelector('[data-action="citySheetAll"]')?.click());
  await page.waitForTimeout(400);
  const r = await page.evaluate(async () => {
    const V = await import('/src/view/agenda.js');
    // una obra anclada con el bloque más poblado, para que el caso sea el peor
    const porSlot = {};
    FILMS.forEach(f => { if (f._slotKey) (porSlot[f._slotKey] = porSlot[f._slotKey] || []).push(f); });
    const [k, g] = Object.entries(porSlot).sort((a, b) => b[1].length - a[1].length)[0];
    const f = g[0];
    const div = document.createElement('div');
    div.innerHTML = V.renderFilmAlternatives(state, f.title, f.day, f.time);
    const ofrecidas = [...div.querySelectorAll('.checkin-opt-add')].map(e => e.dataset.newtitle);
    const hermanas = new Set(FILMS.filter(x => x._slotKey === k && x.title !== f.title).map(x => x.title));
    return { obra: f.title, hermanas: hermanas.size, ofrecidas: ofrecidas.length,
      hermanasOfrecidas: ofrecidas.filter(t => hermanas.has(t)).length };
  });
  expect(r.hermanas, 'el caso tiene compañeras de bloque').toBeGreaterThan(1);
  expect(r.hermanasOfrecidas, 'ninguna compañera se ofrece como alternativa').toBe(0);
});
