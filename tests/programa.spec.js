// @ts-check
// programa.spec.js — Tab Programa: lista, grid, filtros, posters, topbar.
const { test, expect } = require('@playwright/test');
const { LEVIZA_SIMTIME, abrirHojaCiudad, enterFestival, goToPlanear, reentrar, esperarCalculo } = require('./helpers');

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
  // El reloj va DENTRO de cada festival y viaja por URL: la pregunta de ciudad
  // la decide el ARRANQUE, y un festival terminado ya no la hace (T177). Sin
  // reloj pre-arranque las dos afirmaciones de abajo pasarían por esa razón y
  // no por la que este test quiere medir.
  // mono-ciudad: el sheet NO existe
  await enterFestival(page, 'tercertiempo2026', '2026-07-15T10:00:00-05:00');
  await page.waitForTimeout(600);
  expect(await page.evaluate(() => document.getElementById('city-sheet')?.classList.contains('open'))).toBeFalsy();

  // multiciudad: aparece con una fila por ciudad + la salida
  await enterFestival(page, 'cinemancia2025', '2025-09-15T10:00:00-05:00');
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
  await enterFestival(page, 'cinemancia2025', '2025-09-15T10:00:00-05:00');
  await page.waitForTimeout(900);
  expect(await page.evaluate(() => document.getElementById('city-sheet').classList.contains('open'))).toBe(false);
  expect(await page.evaluate(() => activeVenue)).toBe('city:' + filas.nombre);
});

// La salida ("ver todas") también es una respuesta: no puede reabrir el sheet en
// bucle cada vez que el usuario entra.
test('T53 — "ver todas" se recuerda como respuesta, no como silencio', async ({ page }) => {
  // Reloj dentro del festival, por URL: lo que se mide es que la RESPUESTA se
  // recuerde en el arranque siguiente, y el arranque mira la hora (T177).
  await enterFestival(page, 'cinemancia2025', '2025-09-15T10:00:00-05:00');
  await page.waitForSelector('#city-sheet.open', { timeout: 5000 });
  await page.evaluate(() => document.querySelector('#city-sheet-list .lugar-opt.escape').click());
  await page.waitForTimeout(500);
  expect(await page.evaluate(() => activeVenue)).toBe('all');

  await enterFestival(page, 'cinemancia2025', '2025-09-15T10:00:00-05:00');
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
  // Elige una obra cuyas compañeras SOBREVIVEN a la regla de intersección
  // (30 ago): antes bastaba con estar en una función de 3+, pero desde que las
  // compañeras son las que acompañan en TODAS las funciones del título, una obra
  // que se repite en varias ciudades con distinto acompañamiento ya no arrastra
  // a nadie — y el toast, con razón, no dice «+N». El test mide que el toast sea
  // EL MISMO desde la ficha y desde la grilla; su dato tiene que ejercer ese caso.
  const anclada = await page.evaluate(() => {
    const titulos = [...new Set(FILMS.filter(f => f._slotKey).map(f => f.title))];
    for (const t of titulos) {
      const slots = [...new Set(FILMS.filter(f => f.title === t && f._slotKey).map(f => f._slotKey))];
      const porSlot = slots.map(k => new Set(FILMS.filter(f => f._slotKey === k && f.title !== t).map(f => f.title)));
      if (porSlot.length && [...porSlot[0]].filter(x => porSlot.every(s => s.has(x))).length >= 2) return t;
    }
    return null;
  });
  expect(anclada, 'hay una obra con compañeras estables en este festival').toBeTruthy();
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

  // La recarga borra _simTime: hay que re-elegir festival y re-congelar la fecha,
  // o el test queda a merced del día en que corra (ver `reentrar` en helpers).
  await page.reload();
  await reentrar(page, 'ficdeh2026', '2026-08-18T20:00');
  await page.waitForTimeout(1200);
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
  // El chip murió (18 ago): lo reemplaza la SECCIÓN Diario al final del tab —
  // banda canónica con icono, cuenta como badge y «Ver todo» hacia el overlay.
  const sec = await page.evaluate(() => {
    const w = document.querySelector('.diario-wrap');
    const b = w?.querySelector('.sec-hdr');
    return w && { txt: b.textContent.replace(/\s+/g, ' ').trim(),
      icono: !!b.querySelector('svg'),
      badge: !!b.querySelector('.count-badge'),
      bandaAbre: b.matches('[data-action="openDiary"]'),
      verTodoViejo: !!b.querySelector('button'),
      chipViejo: !!document.querySelector('.diary-chip') };
  });
  expect(sec, 'con obras vistas hay sección Diario').toBeTruthy();
  expect(sec.txt, 'la banda nombra su destino').toContain('Diario');
  expect(sec.icono, 'con icono, como toda banda').toBe(true);
  expect(sec.badge, 'y la cuenta como badge, no en palabras').toBe(true);
  expect(sec.bandaAbre, 'la banda ENTERA abre el Diario').toBe(true);
  expect(sec.verTodoViejo, 'sin «Ver todo»: la affordance no se duplica').toBe(false);
  expect(sec.chipViejo, 'el chip de la banda del Plan no existe más').toBe(false);

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

// Ronda 3 (FICDEH): con filtro de ciudad, Intereses mostraba las obras de OTRAS
// ciudades exactamente iguales que las demás. El planificador no las agenda
// (#594) y eso solo se sabía DESPUÉS de calcular, en la lista de excluidas —
// cuando el usuario ya se había hecho la expectativa. No se esconden (tus
// intereses son tuyos): se nombra la consecuencia, una vez y con el número.
test('T69 — Intereses avisa cuántas obras quedan fuera por la ciudad', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-13T09:00:00-05:00');
  const irAIntereses = async () => {
    await page.evaluate(async () => {
      document.getElementById('mnav-seleccion').click();
      await new Promise(r => setTimeout(r, 1200));
    });
    return page.evaluate(() => ({
      hint: (() => { const b = document.querySelector('.avisos-body');
        return b ? b.innerText.replace(/\s+/g, ' ').trim() : null; })(),
      filas: document.querySelectorAll('.int-item').length,
    }));
  };
  // Sembrar: 3 obras que SOLO existen fuera de Bogotá + 2 de Bogotá
  const caso = await page.evaluate(() => {
    const bog = f => (f.venue || '').includes('Bogotá');
    const fuera = [...new Set(FILMS.filter(f => f.venue && !bog(f)).map(f => f.title))]
      .filter(t => !FILMS.some(f => f.title === t && bog(f))).slice(0, 3);
    const dentro = [...new Set(FILMS.filter(bog).map(f => f.title))].slice(0, 2);
    state.set('watchlist', new Set([...fuera, ...dentro]));
    return { fuera: fuera.length, dentro: dentro.length };
  });
  expect(caso.fuera, 'FICDEH tiene obras exclusivas de otra ciudad').toBe(3);

  // Sin filtro de ciudad no hay nada que avisar
  const todas = await irAIntereses();
  expect(todas.hint, 'sin filtro, sin aviso').toBeNull();

  // Con Bogotá: avisa el número y NO esconde ninguna fila
  await page.evaluate(() => { activeVenue = 'city:Bogotá'; });
  const conCiudad = await irAIntereses();
  expect(conCiudad.hint, 'usa el diseño de AVISOS: píldora de contexto + consecuencia')
    .toBe('OTRA CIUDAD 3 intereses no entran en tu Plan');
  expect(conCiudad.filas, 'y no esconde ninguna obra').toBe(caso.fuera + caso.dentro);
});

// Ronda 3 (cierre): el chip del Diario y el titular del Recuerdo contaban lo
// mismo con reglas distintas — aquel incluía los eventos, este los descartaba.
// Medido con FICDEH (29 eventos en catálogo): 3 contra 2 con un taller marcado,
// dos números a dos centímetros. Ahora los dos leen _endedStats (dominio).
test('T70 — el Diario y el Recuerdo cuentan lo mismo, incluidos los talleres', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-17T20:00:00-05:00');
  await page.evaluate(() => document.querySelector('[data-action="citySheetAll"]')?.click());
  await page.waitForTimeout(400);
  const caso = await page.evaluate(async () => {
    const ev = FILMS.filter(f => f.type === 'event').slice(0, 1);
    const pel = FILMS.filter(f => f.type !== 'event').slice(0, 2);
    const marcar = [...pel.map(f => f.title), ...ev.map(f => f.title)];
    state.set('watched', new Set(marcar));
    state.set('savedAgenda', { scenarioIdx: 0, schedule: marcar.map(t => {
      const f = FILMS.find(x => x.title === t); return Object.assign({}, f, { _title: t }); }) });
    switchMainNav('mnav-miplan'); showAgView();
    await new Promise(r => setTimeout(r, 1200));
    const c = document.querySelector('.diario-wrap .count-badge');
    return { conEvento: marcar.length, eventos: ev.length,
      cuenta: c && c.textContent.trim() };
  });
  expect(caso.eventos, 'FICDEH tiene eventos en catálogo').toBe(1);
  expect(caso.cuenta, 'la banda del Diario cuenta las 3, taller incluido').toBe('3');

  const retro = await page.evaluate(async () => {
    _simTime = '2026-08-21T12:00:00-05:00'; showAgView();
    await new Promise(r => setTimeout(r, 1200));
    return (document.body.innerText.match(/Viste [^\n]*/) || [null])[0];
  });
  expect(retro, 'el Recuerdo dice el MISMO número, con el paraguas correcto')
    .toBe('Viste 3 actividades');
});

// 18 ago (vista asumida): la banda del Plan quedó solo con su cuenta y el día —
// el chip del Diario se mudó a su sección y «Sin confirmar» murió con la
// asunción. La banda sigue siendo canónica (a sangre, nombre + badge).
test('T71 — la banda del Plan: canónica, sin chip, y sin resucitar «Sin confirmar»', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-17T20:00:00-05:00');
  await page.evaluate(() => document.querySelector('[data-action="citySheetAll"]')?.click());
  await page.waitForTimeout(400);
  const g = await page.evaluate(async () => {
    const pas = FILMS.filter(f => f.day <= '2026-08-17' && f.time <= '18:00').slice(0, 3);
    const fut = FILMS.filter(f => f.day > '2026-08-17').slice(0, 2);
    state.set('watched', new Set(FILMS.slice(20, 24).map(f => f.title)));
    state.set('savedAgenda', { scenarioIdx: 0, schedule: [...pas, ...fut].map(f =>
      Object.assign({}, f, { _title: f.title })) });
    switchMainNav('mnav-miplan'); showAgView();
    await new Promise(r => setTimeout(r, 1400));
    const banda = [...document.querySelectorAll('#ag-view .sec-hdr')]
      .find(e => /Mi Plan|My Plan|Meu Plano/.test(e.textContent));
    const b = banda.getBoundingClientRect();
    return {
      x: Math.round(b.x), w: Math.round(b.width),
      txt: banda.textContent.replace(/\s+/g, ' ').trim(),
      chip: !!banda.querySelector('.diary-chip'),
      dia: !!banda.querySelector('.sec-hdr-opt'),
      checkin: !!document.querySelector('.checkin-wrap'),
    };
  });
  expect(g.x, 'la banda del Plan va a sangre').toBe(0);
  expect(g.txt, 'nombra la sección con su cuenta').toMatch(/Mi Plan\s*5/);
  expect(g.chip, 'el chip del Diario no vive más en la banda').toBe(false);
  expect(g.dia, 'el día cierra la banda como dato').toBe(true);
  expect(g.checkin, '«Sin confirmar» no resucita').toBe(false);
});

// Ronda 4 (auditor de fin de festival): «AHORA» en verde sobre una película que
// ya terminó. isNowShowing usa el fin EFECTIVO (con Q&A), correcto para el
// planificador —la función te ocupa hasta el final— pero no para el que lee: el
// fin de la película es DATO y el del Q&A es ESTIMACIÓN (FESTIVAL_QA_MIN, «la UI
// la declara, nunca la afirma»). Medido en FINCA, 16 de 30 obras con Q&A.
// Y Mi Plan estaba peor: el rótulo contaba con Q&A y la cuenta sin él, así que
// decía «Termina en 0 min» durante media hora.
// 18 ago: el badge de estado de la FILA («Q&A» ámbar) quedaba pegado al
// informativo «Q&A» de _metaBadges — la fila lo decía dos veces (traspaso de
// Onboarding, decisión de Juan). El punto verde .row-dot es ahora el marcador
// de «ahora» en las filas: el badge dice QUÉ, el punto dice CUÁNDO. La píldora
// sobrevive solo sobre el PÓSTER, donde un punto se pierde contra el afiche.
test('T72 — el punto dice cuándo, el badge dice qué (y el póster conserva su píldora)', async ({ page }) => {
  await enterFestival(page, 'finca2026', '2026-08-17T12:00:00-03:00');
  const leer = async (hora) => page.evaluate(async (hh) => {
    const f = FILMS.find(x => x.title.startsWith('¿Cuán profundo'));
    _simTime = `${f.day}T${hh}:00-03:00`;
    state.set('savedAgenda', { scenarioIdx: 0, schedule: [Object.assign({}, f, { _title: f.title })] });
    switchMainNav('mnav-cartelera');
    activeDay = f.day; programaViewMode = 'list'; _renderProgramaContent();
    await new Promise(r => setTimeout(r, 700));
    const fila = [...document.querySelectorAll('.plist-item')].find(e => e.textContent.includes('Cuán profundo'));
    const filaInfo = fila && {
      qas: [...fila.querySelectorAll('.meta-badge, .film-check-badge')].filter(e => /Q&A/.test(e.textContent)).length,
      pildoraEstado: !!fila.querySelector('.film-check-badge'),
      dots: fila.querySelectorAll('.row-dot').length,
      dotTras: fila.querySelector('.row-dot')?.previousElementSibling?.textContent.trim() || null,
      aria: fila.querySelector('.row-dot')?.getAttribute('aria-label') || null,
    };
    programaViewMode = 'grid'; setProgramaView ? setProgramaView('grid') : _renderProgramaContent();
    await new Promise(r => setTimeout(r, 700));
    const poster = document.querySelector('.poster-now');
    switchMainNav('mnav-miplan'); showAgView();
    await new Promise(r => setTimeout(r, 1000));
    const b = document.querySelector('.ctx-next-badge');
    return { fila: filaInfo,
      poster: poster && { txt: poster.textContent.trim(), qa: poster.classList.contains('qa-only') },
      plan: b && { txt: b.textContent.trim(), qa: b.classList.contains('qa-only') } };
  }, hora);

  // La obra: 19:00, película hasta 20:41, función (con Q&A) hasta 21:11
  const conPeli = await leer('20:00');
  expect(conPeli.fila.pildoraEstado, 'la fila ya no lleva píldora de estado').toBe(false);
  expect(conPeli.fila.dots, 'un punto').toBe(1);
  expect(conPeli.fila.dotTras, 'tras el TÍTULO cuando corre la película').toContain('Cuán profundo');
  expect(conPeli.fila.aria, 'el aria sostiene lo que el color no dice').toBeTruthy();
  expect(conPeli.plan.txt, 'Mi Plan cuenta lo que falta de película').toBe('Termina en 41 min');

  const enQa = await leer('20:50');
  expect(enQa.fila.qas, 'UN solo «Q&A» en la fila — el duplicado murió').toBe(1);
  expect(enQa.fila.dots, 'un punto').toBe(1);
  expect(enQa.fila.dotTras, 'tras el badge Q&A cuando corre la charla').toBe('Q&A');
  if (enQa.poster) {
    expect(enQa.poster.txt, 'el póster conserva su píldora').toBe('Q&A');
    expect(enQa.poster.qa, 'ámbar').toBe(true);
  }
  expect(enQa.plan.txt, 'Mi Plan sigue diciendo Q&A').toBe('Q&A');

  const despues = await leer('21:30');
  expect(despues.fila.dots, 'sin nada corriendo, sin punto').toBe(0);
});

// Ronda 4 (auditor): «te quedarían 0 min» explicaba una función EXCLUIDA con la
// rama de «sí llegás» — el mensaje contradecía a la lista donde aparecía. Causa:
// screensConflict exige hueco >= viaje + BUFFER y la cuenta sumaba solo el viaje,
// mientras la rama de misma sede sí nombraba el margen. Una regla, dos cuentas;
// 53 de los 275 choques de viaje de FICDEH se explicaban así. El margen pasó a ser
// un SUMANDO de la cadena (no una regla aparte): el total queda comparable con la
// hora de inicio y desaparece la frase de veredicto que podía contradecirla.
// Y el segundo tramo: cuando el choque existe SOLO por el Q&A —opcional y
// estimado— no es una imposibilidad sino una decisión, así que se nombra y la
// función se puede agendar marcándola _squeezed (verifyPlan la respeta).
test('T73 — la cuenta del veredicto usa la misma aritmética que la decisión', async ({ page }) => {
  await enterFestival(page, 'finca2026', '2026-08-13T09:00:00-05:00');
  const r = await page.evaluate(async () => {
    const S = await import('/src/domain/schedule.js');
    const H = await import('/src/view/helpers.js');
    const a = FILMS.find(f => f.title === 'Yintah');
    const b = FILMS.find(f => f.title.startsWith('El amor duerme'));
    const rr = S.screensConflictReason(a, b);
    const txt = H.conflictAccount(a, b, rr).replace(/<[^>]*>/g, '');
    // el plan con las dos, la segunda tomada a sabiendas
    const plan = [Object.assign({}, a, { _title: a.title }),
                  Object.assign({}, b, { _title: b.title, _squeezed: true })];
    const v = S.verifyPlan(plan, {});
    // y sin la marca deliberada, el mismo plan SÍ es una violación
    const planSinMarca = plan.map(s => { const c = Object.assign({}, s); delete c._squeezed; return c; });
    const v2 = S.verifyPlan(planSinMarca, {});
    return { kind: rr && rr.kind, qaOnly: rr && rr.qaOnly, txt,
      okConMarca: v.ok, okSinMarca: v2.ok };
  });

  expect(r.kind, 'el choque es por viaje').toBe('viaje');
  expect(r.qaOnly, 'y existe SOLO por el Q&A').toBe(true);
  // 1· el margen es un SUMANDO de la cadena, no una regla enunciada aparte: así
  //    el total se compara solo contra la hora de inicio (21:15 vs 21:00).
  // 18 ago: la SUMA se retiró (Juan) — «21:15 se entiende cuando la función
  // dice 21:00», y esa hora vive ahora arriba, en la línea de la función. La
  // cuenta conserva la CAUSA (Q&A, viaje) y el veredicto, con la tilde de
  // estimado mudada al total: sugerimos, no predecimos.
  expect(r.txt, 'nombra la causa: el Q&A y el viaje').toMatch(/Q&A y viaje/);
  expect(r.txt, 'y el veredicto es el total, marcado como estimado').toContain('~21:15');
  expect(r.txt, 'sin enumerar los sumandos').not.toMatch(/margen 15 min|\+ viaje/);
  // 2· la salida va en la MISMA moneda: la hora a la que llegarías sin el Q&A
  expect(r.txt, 'nombra la alternativa con su hora').toContain('sin el Q&A, ~20:45');
  // y ya no hace falta un veredicto en palabras
  expect(r.txt, 'sin frase de veredicto').not.toMatch(/no te daría el tiempo|te quedarían/);
  // 3· tomarla a sabiendas produce un plan VÁLIDO; sin la marca, no
  expect(r.okConMarca, 'con _squeezed el plan es válido').toBe(true);
  expect(r.okSinMarca, 'sin la marca sigue siendo una violación').toBe(false);
});

// Ronda 4 (auditor de fin de festival): «No incluidas» mezclaba dos poblaciones.
// Medido en FINCA (17 AGO 21:00, intereses mixtos): 9 excluidas — 7 cuyas
// funciones YA PASARON y solo 2 que compitieron de verdad —, y las 7 salían
// PRIMERO, enterrando las dos decisiones de la noche. Encima el banner general
// decía «se solapan con otros en tu Plan», falso para 7 de las 9.
// «No incluida» describe a la que compitió y perdió; a la que se llevó el
// festival, llamarla así es un reproche sin sujeto. Su lugar es el Diario y el
// Modo Recuerdo, y en Intereses ya aparece con «Ya pasó».
test('T74 — «No incluidas» solo lista lo que compitió', async ({ page }) => {
  await enterFestival(page, 'finca2026', '2026-08-17T21:00:00-03:00');
  const caso = await page.evaluate(() => {
    const muertas = [...new Set(FILMS.filter(f => screeningPassed(f)).map(f => f.title))]
      .filter(t => !FILMS.some(f => f.title === t && !screeningPassed(f)));
    const vivas = [...new Set(FILMS.filter(f => !screeningPassed(f)).map(f => f.title))];
    state.set('watchlist', new Set([...muertas.slice(0, 7), ...vivas.slice(0, 7)]));
    return { muertas: muertas.slice(0, 7).length };
  });
  expect(caso.muertas, 'el escenario tiene obras que ya pasaron').toBe(7);

  await goToPlanear(page);
  await page.evaluate(() => { document.querySelector('.av-calc-btn')?.click(); });
  await page.waitForTimeout(3500);

  const r = await page.evaluate(() => {
    const sc = cachedResult && cachedResult.scenarios[cachedResult.currentIdx || 0];
    const bloque = document.querySelector('.ag-excl-block');
    return {
      excluidasDominio: sc.excluded.length,
      filas: bloque ? bloque.querySelectorAll('.int-item-title').length : 0,
      badge: bloque?.querySelector('.count-badge')?.textContent,
      diceYaPaso: (bloque?.innerText || '').includes('Ya pasó'),
      banner: document.body.innerText.includes('se solapan con otros en tu Plan'),
    };
  });

  expect(r.excluidasDominio, 'el motor sigue reportando todas').toBe(9);
  expect(r.filas, 'pero la pantalla solo lista las que compitieron').toBe(2);
  expect(r.badge, 'y el badge cuenta lo accionable, no lo perdido').toBe('2');
  expect(r.diceYaPaso, 'ninguna lápida en Planear').toBe(false);
  expect(r.banner, 'sin el banner que generalizaba una causa falsa').toBe(false);
});

// Ronda 4 (auditor): la última noche, con 12 obras en el plan y CERO funciones
// restantes en todo el catálogo, Planear mostraba el vacío de primer uso — «Tu
// Plan aparece aquí · Agregá lo que no querés perderte · Ir a Intereses». Tres
// promesas falsas. `pending` vacío tenía UNA pantalla; detrás hay tres
// situaciones. Y el vacío de combinaciones culpaba a la disponibilidad sin
// saber si había bloqueos, con un punto en medio por la costura de dos claves.
test('T75 — Planear distingue por qué no hay nada que planear', async ({ page }) => {
  await enterFestival(page, 'finca2026', '2026-08-17T12:00:00-03:00');

  // A.1 · no queda NADA en el festival → despedida, aunque el calendario siga
  const a1 = await page.evaluate(async () => {
    const tits = [...new Set(FILMS.map(f => f.title))].slice(0, 12);
    state.set('watchlist', new Set(tits));
    state.set('savedAgenda', { scenarioIdx: 0, schedule: tits.map(t => {
      const f = FILMS.find(x => x.title === t); return Object.assign({}, f, { _title: t }); }) });
    _simTime = '2026-08-19T23:00:00-03:00';
    // La espera va ANTES de entrar a Planear: el boot tiene un setTimeout que
    // salta solo a Mi Plan cuando hay agenda activa (main.js), y si cae después
    // del switch pisa la pantalla que este test mide.
    await new Promise(r => setTimeout(r, 1300));
    switchMainNav('mnav-planner'); showAgView();
    await new Promise(r => setTimeout(r, 400));
    return (document.getElementById('ag-view')?.innerText || '').replace(/\s+/g, ' ');
  });
  expect(a1, 'se despide en vez de invitar').toContain('ha terminado');
  expect(a1, 'y manda a lo vivido').toContain('Ver Mi Plan');
  expect(a1, 'sin la pantalla de primer uso').not.toContain('Primero, tus intereses');

  // A.2 · el festival sigue, tus intereses se agotaron → al Programa
  const a2 = await page.evaluate(async () => {
    const D = await import('/src/domain/film.js');
    _simTime = '2026-08-18T23:30:00-03:00';
    const pasadas = [...new Set(FILMS.filter(f => D.screeningPassed(f)).map(f => f.title))]
      .filter(t => !FILMS.some(f => f.title === t && !D.screeningPassed(f)));
    state.set('watchlist', new Set(pasadas.slice(0, 5)));
    state.set('savedAgenda', { scenarioIdx: 0, schedule: [] });
    await new Promise(r => setTimeout(r, 600));
    cachedResult = null;
    switchMainNav('mnav-planner'); showAgView();
    await new Promise(r => setTimeout(r, 400));
    return { quedan: FILMS.filter(f => !D.screeningPassed(f)).length,
      txt: (document.getElementById('ag-view')?.innerText || '').replace(/\s+/g, ' ') };
  });
  expect(a2.quedan, 'el festival aún tiene funciones').toBeGreaterThan(0);
  expect(a2.txt, 'nombra el hecho en siete palabras').toContain('Nada por planear');
  expect(a2.txt, 'y manda a donde queda material').toContain('Ir al Programa');
  expect(a2.txt, 'no a la lista agotada').not.toContain('Ir a Intereses');

  // A.3 · primer uso de verdad → la pantalla original
  const a3 = await page.evaluate(async () => {
    state.set('watchlist', new Set());
    cachedResult = null;
    switchMainNav('mnav-planner'); showAgView();
    await new Promise(r => setTimeout(r, 1000));
    return (document.getElementById('ag-view')?.innerText || '').replace(/\s+/g, ' ');
  });
  // El titular del primer uso cambió el 31 ago: «Tu Plan aparece aquí» era falso
  // acá (el Plan se arma en Planear y aparece en Mi Plan) y era además el mismo
  // de Mi Plan. El aserto se REAPUNTA a la frase nueva — si se dejara la vieja,
  // dejaría de identificar esta pantalla y el guardián quedaría ciego.
  expect(a3, 'el primer uso conserva su invitación').toContain('Primero, tus intereses');

  // Combos vacíos · sin bloqueos NO se culpa a la disponibilidad
  const combos = await page.evaluate(async () => {
    const V = await import('/src/view/agenda.js');
    const sinBloqueos = V.buildResultHTML([]).replace(/<[^>]*>/g, '');
    availability['2026-08-18'] = { blocks: [{ from: '10:00', to: '22:00' }] };
    const conBloqueos = V.buildResultHTML([]).replace(/<[^>]*>/g, '');
    delete availability['2026-08-18'];
    return { sinBloqueos, conBloqueos };
  });
  expect(combos.sinBloqueos, 'sin bloqueos: no culpa a la disponibilidad')
    .toBe('Sin combinaciones. Sumá más títulos.');
  expect(combos.conBloqueos, 'con bloqueos: la nombra')
    .toBe('Sin combinaciones. Liberá disponibilidad o sumá títulos.');
  expect(combos.sinBloqueos, 'sin punto en medio de frase').not.toMatch(/\.\s+[a-z]/);
});

// Ronda 4 (cierre): una prioridad cuyas funciones ya pasaron retenía su cupo —
// «Prioridades 2/4» con una muerta, y con 4/4 muertas el usuario chocaba contra
// la sheet del límite sin aviso. El cupo ahora se mide sobre las VIVAS
// (prioLiveCount, dominio); la muerta sigue en la lista, atenuada, pero no
// bloquea. Y el badge del tab MI PLAN queda atado por test a la banda «Sin
// confirmar»: cuentan lo mismo con el mismo predicado, y no pueden divergir.
test('T76 — el cupo de prioridades es de las vivas, y el badge de MI PLAN dice lo que la banda', async ({ page }) => {
  await enterFestival(page, 'finca2026', '2026-08-18T10:00:00-03:00');
  await page.evaluate(() => document.querySelector('[data-action="citySheetAll"]')?.click());
  await page.waitForTimeout(400);

  // ── 1 · cupo: 3 muertas + 1 viva = lleno según el tamaño, 1/4 según las vivas
  const cupo = await page.evaluate(async () => {
    const D = await import('/src/domain/film.js');
    const muertas = [...new Set(FILMS.filter(f => D.screeningPassed(f)).map(f => f.title))]
      .filter(t => !FILMS.some(f => f.title === t && !D.screeningPassed(f))).slice(0, 3);
    const viva = [...new Set(FILMS.filter(f => !D.screeningPassed(f)).map(f => f.title))][0];
    const otraViva = [...new Set(FILMS.filter(f => !D.screeningPassed(f)).map(f => f.title))][1];
    state.set('watchlist', new Set([...muertas, viva, otraViva]));
    state.set('prioritized', new Set([...muertas, viva]));
    switchMainNav('mnav-seleccion'); showAgView();
    await new Promise(r => setTimeout(r, 1000));
    const badge = [...document.querySelectorAll('.sec-hdr .count-badge')]
      .map(e => e.textContent.trim()).find(x => /\/\d/.test(x));
    // y priorizar otra VIVA no choca contra el límite pese a size=4
    togglePriority(otraViva);
    await new Promise(r => setTimeout(r, 600));
    return { size: prioritized.size, badge,
      sheetLimite: !!document.querySelector('#prio-limit-sheet.open, .prio-limit-sheet.open'),
      otraEntro: prioritized.has(otraViva) };
  });
  expect(cupo.badge, 'el badge cuenta las vivas, no el tamaño').toBe('1/4');
  expect(cupo.otraEntro, 'priorizar otra viva no choca contra el límite').toBe(true);
  expect(cupo.sheetLimite, 'sin sheet de límite').toBe(false);

  // ── 2 · la tarea de confirmar murió con la vista asumida (18 ago): ni badge
  //        en el tab ni bloque «Sin confirmar» — las pasadas van directo al Diario.
  const asumido = await page.evaluate(async () => {
    const pas = FILMS.filter(f => f.day <= '2026-08-17').slice(0, 3);
    state.set('watched', new Set());
    state.set('savedAgenda', { scenarioIdx: 0, schedule: pas.map(f =>
      Object.assign({}, f, { _title: f.title })) });
    switchMainNav('mnav-miplan'); showAgView();
    await new Promise(r => setTimeout(r, 1200));
    return {
      badge: !!document.getElementById('miplan-badge'),
      checkin: !!document.querySelector('.checkin-wrap'),
      diario: document.querySelector('.diario-wrap .count-badge')?.textContent,
    };
  });
  expect(asumido.badge, 'el badge del tab murió con su tarea').toBe(false);
  expect(asumido.checkin, 'el bloque de confirmación no existe').toBe(false);
  expect(Number(asumido.diario), 'las 3 pasadas están ASUMIDAS en el Diario').toBe(3);
});

// Falsa alarma que dejó un seguro: creí ver días vencidos en los chips de
// Intereses, pero la sonda del mockup usaba ?simTime= en la URL — el parámetro
// que NO existe (la app corría al reloj real y esos días eran futuros de
// verdad). El filtro de agenda.js siempre estuvo bien… y sin test: nada cazaba
// una regresión. Este lo cubre.
test('T77 — los chips de días en Intereses solo muestran días con función futura', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-18T20:00:00-05:00');
  await page.evaluate(() => document.querySelector('[data-action="citySheetAll"]')?.click());
  await page.waitForTimeout(400);
  const r = await page.evaluate(async () => {
    const D = await import('/src/domain/film.js');
    // mezcla: dos con función futura el 19, dos con todo pasado
    state.set('watchlist', new Set(['Semillas', 'Por una gota de leche', 'Madres de nacimiento', 'Sukua']));
    document.getElementById('mnav-seleccion').click();
    await new Promise(r => setTimeout(r, 1400));
    const filas = [...document.querySelectorAll('.int-item')].map(it => ({
      titulo: it.querySelector('.int-item-title')?.textContent.trim(),
      chips: [...it.querySelectorAll('.pelicula-day')].map(e => e.dataset.day),
    }));
    const futurasDe = t => new Set(FILMS.filter(f => f.title === t && !D.screeningPassed(f)).map(f => f.day));
    return filas.map(f => ({ ...f, fueraDeLugar: f.chips.filter(d => !futurasDe(f.titulo).has(d)) }));
  });
  const conChips = r.filter(f => f.chips.length);
  expect(conChips.length, 'hay filas con chips para medir').toBeGreaterThan(0);
  r.forEach(f => expect(f.fueraDeLugar, `«${f.titulo}» no muestra días sin función futura`).toEqual([]));
  const muertas = r.filter(f => !f.chips.length);
  expect(muertas.length, 'las agotadas no muestran ningún chip').toBeGreaterThan(0);
});

// Auditoría de Mi Plan, puntos 3–5 (18 ago): el eyebrow del hero era extranjero
// (10px, tracking propio), el hero estaba PEGADO a la banda del Plan (0px), y
// los botones Compartir/Calendario flotaban equidistantes (17/16) entre la
// grilla y la lista — el dueño del gap era el margin de .mplan-wrap, no el
// padding de los botones. Regla: entre secciones, UN token (sp-5).
test('T79 — Mi Plan: eyebrow pariente, hero que respira, botones anclados', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-18T15:00:00-05:00');
  await page.evaluate(() => [...document.querySelectorAll('#city-sheet [data-action]')]
    .find(x => x.textContent.includes('Bogotá'))?.click());
  await page.waitForTimeout(600);
  const r = await page.evaluate(async () => {
    const bog = f => (f.venue || '').includes('Bogotá');
    const hoy = FILMS.filter(f => bog(f) && f.day === '2026-08-18' && f.time > '16:00').slice(0, 2);
    state.set('savedAgenda', { scenarioIdx: 0, schedule: hoy.map(f =>
      Object.assign({}, f, { _title: f.title })) });
    switchMainNav('mnav-miplan'); showAgView();
    await new Promise(r => setTimeout(r, 1400));
    // La banda del PLAN se ubica por contenido, no por posición: desde que el
    // hero abre con su propia banda (T80), «la primera sec-hdr» ya no es esta.
    const bandaPlan = [...document.querySelectorAll('#ag-view .sec-hdr')]
      .find(e => /Mi Plan|My Plan|Meu Plano/.test(e.textContent));
    const g = (a, b) => { const A = typeof a === 'string' ? document.querySelector(a) : a,
      B = typeof b === 'string' ? document.querySelector(b) : b;
      return A && B ? Math.round(B.getBoundingClientRect().top - A.getBoundingClientRect().bottom) : null; };
    const ey = document.querySelector('#ag-view .ctx-aviso');
    // El aviso habla los tokens del sistema: t-sm y w-semi, sin caps ni tracking.
    const probe = document.createElement('span');
    probe.style.fontSize = 'var(--t-sm)'; document.body.appendChild(probe);
    const tSm = getComputedStyle(probe).fontSize; probe.remove();
    return { heroBanda: g('.ctx-header', bandaPlan),
      footDentro: !!document.querySelector('.mplan-wrap .mplan-foot'),
      eyebrowPx: ey && getComputedStyle(ey).fontSize,
      eyebrowCaps: ey && getComputedStyle(ey).textTransform, tSm };
  });
  expect(r.heroBanda, 'el hero respira sp-5 antes de la banda').toBe(24);
  expect(r.footDentro, 'las acciones son el footer DE la pieza, no flotan bajo ella').toBe(true);
  expect(r.eyebrowPx, 'el aviso habla el token t-sm del sistema').toBe(r.tSm);
  expect(r.eyebrowCaps, 'sin mayúsculas: es aviso, no separador').toBe('none');
});

// 18 ago, cazado por Juan en producción: al abrir Mi Plan se metía la barra de
// días de Programa. El fix del compositor de iOS (loader.js) re-ejecuta
// initProgramaModeBar ~830ms después de entrar al festival, y su
// remove('hidden') incondicional asumía correr solo en Programa — si para
// entonces estabas en Mi Plan (salto automático del boot, o un toque rápido),
// la barra se colaba. Ahora usa la MISMA condición que switchMainNav.
test('T81 — la barra de días no se cuela en Mi Plan (re-run diferido del iOS fix)', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-18T15:00:00-05:00');
  await page.evaluate(() => [...document.querySelectorAll('#city-sheet [data-action]')]
    .find(x => x.textContent.includes('Bogotá'))?.click());
  // entrar a Mi Plan INMEDIATAMENTE (dentro de la ventana de ~830ms del re-run)
  await page.click('#mnav-miplan');
  // esperar a que el re-run diferido dispare con Mi Plan activo
  await page.waitForTimeout(1400);
  const nav = await page.evaluate(() => {
    const n = document.getElementById('nav-row');
    return { hidden: n.classList.contains('hidden'),
      alto: Math.round(n.getBoundingClientRect().height) };
  });
  expect(nav.hidden, 'la barra de días queda oculta en Mi Plan').toBe(true);
  // y en Programa sigue visible — la condición no puede sobre-ocultar
  await page.click('#mnav-cartelera');
  await page.waitForTimeout(700);
  const nav2 = await page.evaluate(() => document.getElementById('nav-row').classList.contains('hidden'));
  expect(nav2, 'en Programa la barra vive').toBe(false);
});

// 18 ago, opción A de Juan: el hero habla UN solo aviso en sus cinco estados —
// texto con color semántico (ámbar próximo · verde ahora, punto solo si corre ·
// gris informativo), sin banda ni caps. El nocturno dice el día COMPLETO («tu
// martes», no «tu mar»), y el cierre vuelve al sistema con su propio aviso.
test('T80 — el aviso del hero: un solo vestuario en sus cinco estados', async ({ page }) => {
  test.setTimeout(60000);
  const medir = async (hora, watch) => {
    await page.evaluate(async ({ hh, watch }) => {
      _simTime = hh;
      const bog = f => (f.venue || '').includes('Bogotá');
      const pick = (day, pred, n) => FILMS.filter(f => bog(f) && f.day === day && pred(f)).slice(0, n);
      const sched = [...pick('2026-08-18', f => f.time < '14:00', 1), ...pick('2026-08-18', f => f.time >= '17:00', 2)];
      state.set('savedAgenda', { scenarioIdx: 0, schedule: sched.map(f =>
        Object.assign({}, f, { _title: f.title })) });
      state.set('watched', watch ? new Set(sched.map(x => x.title)) : new Set());
      switchMainNav('mnav-miplan'); showAgView();
      await new Promise(r => setTimeout(r, 1200));
    }, { hh: hora, watch: !!watch });
    return page.evaluate(() => {
      const a = document.querySelector('#ag-view .ctx-aviso');
      return { txt: a?.textContent.replace(/\s+/g, ' ').trim(),
        color: a && getComputedStyle(a).color,
        dot: !!a?.querySelector('.row-dot'),
        banda: !!document.querySelector('.ctx-eyebrow-band') };
    });
  };
  await enterFestival(page, 'ficdeh2026', '2026-08-18T15:00:00-05:00');
  await page.evaluate(() => [...document.querySelectorAll('#city-sheet [data-action]')]
    .find(x => x.textContent.includes('Bogotá'))?.click());
  await page.waitForTimeout(600);
  const AMBER = 'rgb(245, 158, 11)';

  const prox = await medir('2026-08-18T16:45:00-05:00');
  expect(prox.txt, 'el aviso nombra el estado').toBe('Próxima función');
  expect(prox.color, 'próximo = ámbar').toBe(AMBER);
  expect(prox.dot, 'sin punto: nada corre aún').toBe(false);
  expect(prox.banda, 'la banda del hero no existe más').toBe(false);

  const curso = await medir('2026-08-18T17:30:00-05:00');
  expect(curso.txt).toBe('En curso');
  expect(curso.color, 'ahora = verde').not.toBe(AMBER);
  expect(curso.dot, 'y el punto dice que corre').toBe(true);

  const libre = await medir('2026-08-18T14:30:00-05:00');
  expect(libre.txt, 'tiempo libre habla el mismo componente').toMatch(/Tiempo libre/);
  expect(libre.color, 'verde, sin punto').toBe(curso.color);
  expect(libre.dot).toBe(false);

  const noct = await medir('2026-08-18T22:45:00-05:00', true);
  expect(noct.txt, 'el día COMPLETO: «tu martes», no «tu mar»').toMatch(/martes/);
  expect(noct.dot).toBe(false);

  const fin = await medir('2026-08-20T11:00:00-05:00', true);
  expect(fin.txt, 'el cierre vuelve al sistema').toMatch(/Festival terminado/);
  expect(fin.color, 'informativo = gris, no ámbar').not.toBe(AMBER);
});

// 18 ago, auditoría de Mi Plan con Juan: el calendario es UNA pieza — grilla,
// día y lista comparten el perímetro bordeado, el día es caption (no banda),
// las acciones son footer con labels que dicen la acción, y la hora tocable
// lleva chevron en vez del hint que lo confesaba.
test('T82 — el calendario es una pieza: lista adentro, footer con nombre propio, chevron sin hint', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-18T15:00:00-05:00');
  await page.evaluate(() => [...document.querySelectorAll('#city-sheet [data-action]')]
    .find(x => x.textContent.includes('Bogotá'))?.click());
  await page.waitForTimeout(600);
  const r = await page.evaluate(async () => {
    const bog = f => (f.venue || '').includes('Bogotá');
    const pick = (day, pred, n) => FILMS.filter(f => bog(f) && f.day === day && pred(f)).slice(0, n);
    const sched = [...pick('2026-08-18', f => f.time < '14:00', 1), ...pick('2026-08-18', f => f.time > '16:00', 2)];
    state.set('savedAgenda', { scenarioIdx: 0, schedule: sched.map(f => Object.assign({}, f, { _title: f.title })) });
    switchMainNav('mnav-miplan'); showAgView();
    await new Promise(r => setTimeout(r, 1400));
    const wrap = document.querySelector('.mplan-wrap');
    const btns = [...document.querySelectorAll('.mplan-foot-btn')].map(b => b.textContent.trim());
    return {
      listaDentro: !!wrap?.querySelector('.mplan-list'),
      captionDentro: !!wrap?.querySelector('.mplan-list-hdr'),
      footAlFinal: wrap && wrap.lastElementChild?.classList.contains('mplan-foot'),
      labels: btns,
      // Un solo cuerpo para ambos botones, dictado por el label más largo
      // (pedido de Juan, 18 ago): mismas fuentes computadas y CERO desborde
      // en el peor idioma (PT trae el label más ancho).
      footSizes: [...document.querySelectorAll('.mplan-foot-btn')].map(b => getComputedStyle(b).fontSize),
      footOverflow: await (async () => {
        let worst = 0;
        for (const lang of ['es', 'pt']) {
          state.set('_lang', lang); switchMainNav('mnav-miplan'); showAgView();
          await new Promise(r => setTimeout(r, 700));
          const bs = [...document.querySelectorAll('.mplan-foot-btn')];
          bs.forEach(b => { worst = Math.max(worst, b.scrollWidth - b.clientWidth); });
          // y el 50/50 es real: ningún label le roba ancho al vecino
          worst = Math.max(worst, Math.abs(bs[0].clientWidth - bs[1].clientWidth) > 2 ? 99 : 0);
        }
        state.set('_lang', 'es'); switchMainNav('mnav-miplan'); showAgView();
        await new Promise(r => setTimeout(r, 700));
        return worst;
      })(),
      hint: !!document.querySelector('.mplan-change-hint'),
      chevronFuturas: [...document.querySelectorAll('.mplan-t1:not(.mp-past)')].every(e => !!e.querySelector('svg')),
      chevronPasadas: [...document.querySelectorAll('.mplan-t1.mp-past')].some(e => e.querySelector('svg')),
      nFuturas: document.querySelectorAll('.mplan-t1:not(.mp-past)').length,
      nPasadas: document.querySelectorAll('.mplan-t1.mp-past').length,
    };
  });
  expect(r.listaDentro, 'la lista vive dentro del perímetro de la pieza').toBe(true);
  expect(r.captionDentro, 'el día es caption dentro de la pieza').toBe(true);
  expect(r.footAlFinal, 'el footer cierra la pieza').toBe(true);
  expect(r.labels.join('|'), 'los labels dicen la acción, no el sustantivo').toMatch(/Compartir Plan|Share Plan/);
  // «Exportar» (Juan, 18 ago): dentro del calendario, «Pasar a tu calendario»
  // obligaba a preguntar cuál; y «Sincronizar» prometía un vínculo vivo que el
  // .ics no cumple. El verbo dice la acción; el icono carga el destino.
  expect(r.labels.join('|')).toMatch(/Exportar|Export/);
  expect(new Set(r.footSizes).size, 'un solo cuerpo tipográfico en el footer').toBe(1);
  expect(r.footOverflow, 'el label más largo cabe: cero desborde (ES y PT)').toBe(0);
  expect(r.hint, 'el hint murió: lo reemplaza la affordance').toBe(false);
  expect(r.nFuturas, 'la escena tiene horas futuras que medir').toBeGreaterThan(0);
  expect(r.chevronFuturas, 'toda hora tocable lleva chevron').toBe(true);
  expect(r.nPasadas).toBeGreaterThan(0);
  expect(r.chevronPasadas, 'una hora pasada no promete cambio').toBe(false);
});

// 18 ago — Diario LUZ (elección de Juan sobre 3 propuestas premium): el muro de
// pósters LIMPIOS es el diario. La vista asumida no lleva NI UN pixel de estado;
// el estado solo aparece al desviarse: calificaste → estrellas FUERA del afiche
// (patrón Letterboxd); «no la vi» → póster apagado con el ojo tachado.
test('T83 — Diario Luz: muro limpio, estrellas afuera, y la negación se apaga', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-18T15:00:00-05:00');
  await page.evaluate(() => [...document.querySelectorAll('#city-sheet [data-action]')]
    .find(x => x.textContent.includes('Bogotá'))?.click());
  await page.waitForTimeout(600);
  const r = await page.evaluate(async () => {
    const bog = f => (f.venue || '').includes('Bogotá');
    const pick = (day, n) => FILMS.filter(f => bog(f) && f.day === day && f.poster && !f.is_cortos).slice(0, n);
    const [rated, assumed, negada] = [...pick('2026-08-15', 2), ...pick('2026-08-16', 1)];
    const sched = [rated, assumed, negada,
      ...FILMS.filter(f => bog(f) && f.day === '2026-08-18' && f.time > '16:00').slice(0, 1)];
    state.set('savedAgenda', { scenarioIdx: 0, schedule: sched.map(f => Object.assign({}, f, { _title: f.title })) });
    state.set('watched', new Set());
    state.set('notWatched', new Set([negada.title]));
    state.set('filmRatings', { [rated.title]: 4 });
    switchMainNav('mnav-miplan'); showAgView();
    await new Promise(r => setTimeout(r, 1400));
    // el muro vive detrás del tap (18 ago): la sección es una tira replegada
    document.querySelector('.dw-band')?.click();
    await new Promise(r => setTimeout(r, 900));
    const wrap = document.querySelector('.diary-sheet');
    const sug = document.querySelector('.suggestion-wrap');
    const seccion = document.querySelector('.diario-wrap');
    // el data-title vive en el AFICHE (su tap abre la ficha), no en la card
    const card = t => [...wrap.querySelectorAll('.dw-card')].find(c => c.querySelector(`[data-title="${CSS.escape(t)}"]`));
    const cR = card(rated.title), cA = card(assumed.title), cN = card(negada.title);
    return {
      alFinal: !!seccion && !!sug && seccion.getBoundingClientRect().top > sug.getBoundingClientRect().top,
      cuenta: wrap.querySelector('.count-badge')?.textContent,
      // calificada: estrellas FUERA del póster (la fila no es descendiente de .dw-poster)
      ratedStars: cR?.querySelectorAll('.dw-stars .dw-star.on').length,
      starsFuera: cR ? !cR.querySelector('.dw-poster .dw-stars') : null,
      // asumida: ni un pixel de estado sobre el afiche (su control es la
      // estrella opaca de la fila, no una marca encima del póster)
      assumedLimpia: cA ? !cA.querySelector('.dw-poster > :not(img)') && cA.querySelectorAll('.dw-star.on').length === 0 : null,
      // negada: apagada, con el ojo tachado en su FILA, y NO cuenta en la banda
      negadaOff: cN ? !!cN.querySelector('.dw-row .dw-ctrl[data-action="toggleWatched"]') && !!cN.querySelector('.dw-poster.dw-off') : null,
    };
  });
  expect(r.alFinal, 'el Diario cierra el tab, después de Sugerencias').toBe(true);
  expect(Number(r.cuenta), 'la banda cuenta 2: la calificada y la ASUMIDA — la negada no').toBe(2);
  expect(r.ratedStars, 'la calificada lleva sus 4 estrellas').toBe(4);
  expect(r.starsFuera, 'las estrellas viven FUERA del afiche (Letterboxd)').toBe(true);
  // (el detalle fino de la fila de control lo fija T86)
  expect(r.assumedLimpia, 'la asumida no lleva ni un pixel de estado').toBe(true);
  expect(r.negadaOff, 'la negada se apaga con el ojo tachado').toBe(true);
});

// 18 ago (Juan, tras ver Letterboxd): el Diario se parte en dos estados. En Mi
// Plan vive REPLEGADO —banda + tira solapada de alto FIJO, que no crece con lo
// visto para no comerle el scroll al calendario— y al tocarlo abre su TAPA:
// nuestro wordmark, el afiche del festival como objeto (completo, no recortado),
// nombre y fechas, la banda «Lo que viste» y el muro CONTINUO (los días, fuera:
// «limitan la visual y generan muchos espacios»).
test('T84 — el Diario: replegado de alto fijo en Mi Plan, tapa y muro continuo al abrir', async ({ page }) => {
  test.setTimeout(60000);
  await enterFestival(page, 'ficdeh2026', '2026-08-18T15:00:00-05:00');
  await page.evaluate(() => document.querySelector('[data-action="citySheetAll"]')?.click());
  await page.waitForTimeout(400);
  const medir = async (n) => page.evaluate(async (n) => {
    const pick = (day, k) => FILMS.filter(f => f.day === day && f.poster && !f.is_cortos).slice(0, k);
    const sched = [...pick('2026-08-13', 4), ...pick('2026-08-14', 4), ...pick('2026-08-15', 4)].slice(0, n);
    state.set('savedAgenda', { scenarioIdx: 0, schedule: sched.map(f => Object.assign({}, f, { _title: f.title })) });
    state.set('watched', new Set()); state.set('notWatched', new Set());
    state.set('filmRatings', { [sched[0].title]: 4 });
    switchMainNav('mnav-miplan'); showAgView();
    await new Promise(r => setTimeout(r, 1300));
    const wrap = document.querySelector('.diario-wrap');
    const strip = wrap?.querySelector('.dw-strip');
    return { alto: wrap ? Math.round(wrap.getBoundingClientRect().height) : 0,
      posters: strip ? strip.querySelectorAll('.dw-strip-p').length : 0,
      mas: strip?.querySelector('.dw-strip-mas')?.textContent || null,
      muroEnSeccion: !!wrap?.querySelector('.dw-grid'),
      abre: wrap?.querySelector('.sec-hdr')?.matches('[data-action="openDiary"]') };
  }, n);

  // ── replegado: el alto NO crece con lo visto ──
  const pocas = await medir(4);
  const muchas = await medir(12);
  expect(pocas.posters, 'con 4 obras, 4 pósters en la tira').toBe(4);
  expect(muchas.posters, 'con 12, la tira se acota a 6').toBe(6);
  expect(muchas.mas, 'y el resto se cuenta').toMatch(/\+\d+/);
  expect(Math.abs(muchas.alto - pocas.alto), 'el alto no crece con lo visto').toBeLessThanOrEqual(2);
  expect(muchas.muroEnSeccion, 'el muro NO vive en Mi Plan: está detrás del tap').toBe(false);
  expect(muchas.abre, 'la banda abre el Diario').toBe(true);

  // ── abierto: tapa + banda + muro continuo ──
  const abierto = await page.evaluate(async () => {
    document.querySelector('.dw-band').click();
    await new Promise(r => setTimeout(r, 900));
    const sheet = document.querySelector('.diary-sheet');
    const art = sheet.querySelector('.diary-keyart');
    const cs = art && getComputedStyle(art);
    return {
      wordmark: !!sheet.querySelector('.diary-wordmark'),
      afiche: !!art && !!art.getAttribute('src'),
      // el afiche es OBJETO: se ve completo (contain/cover en caja 2:3), no banda recortada
      afichePropor: art ? +(art.getBoundingClientRect().height / art.getBoundingClientRect().width).toFixed(2) : 0,
      titulo: sheet.querySelector('#diary-title')?.textContent.trim(),
      fechas: sheet.querySelector('#diary-dates')?.textContent.trim(),
      banda: sheet.querySelector('.diary-band')?.textContent.replace(/\s+/g, ' ').trim(),
      grids: sheet.querySelectorAll('.dw-grid').length,
      dias: sheet.querySelectorAll('.dw-day-lbl').length,
      estrellas: sheet.querySelectorAll('.dw-stars .dw-star.on').length,
      sheetIzq: Math.round(sheet.getBoundingClientRect().left),
      bandaIzq: Math.round(sheet.querySelector('.diary-band').getBoundingClientRect().left),
      ojoIzq: Math.round(sheet.querySelector('.diary-band svg').getBoundingClientRect().left),
      nombreCompleto: sheet.querySelector('#diary-full')?.textContent.trim(),
    };
  });
  expect(abierto.wordmark, 'la tapa lleva nuestro wordmark').toBe(true);
  expect(abierto.afiche, 'y el afiche del festival').toBe(true);
  expect(abierto.afichePropor, 'el afiche va completo en 2:3, no recortado a banda').toBeCloseTo(1.5, 1);
  expect(abierto.titulo, 'con el nombre del festival').toBe('FICDEH');
  expect(abierto.fechas, 'y sus fechas').toMatch(/AGO|AUG/);
  expect(abierto.banda, 'la banda separa la tapa del muro y lleva la cuenta').toMatch(/Lo que viste|What you saw/);
  // La banda no puede sangrar MÁS que la sheet: con el bleed de .sec-hdr
  // (pensado para un contenedor con padding) el icono caía en x=0, cortado
  // contra el borde (Juan, 18 ago).
  expect(abierto.bandaIzq, 'la banda arranca en el borde de la sheet, no antes').toBe(abierto.sheetIzq);
  expect(abierto.ojoIzq, 'y el ojo respeta su inset, entero').toBeGreaterThanOrEqual(12);
  expect(abierto.nombreCompleto, 'bajo la sigla, el nombre completo sin repetirla').toMatch(/Festival Internacional/);
  expect(abierto.grids, 'el muro es UNO solo, continuo').toBe(1);
  expect(abierto.dias, 'sin días partiendo la retícula').toBe(0);
  expect(abierto.estrellas, 'y las calificaciones se ven').toBeGreaterThan(0);
});

// 18 ago, regla de Juan: al ABRIR Programa, la barra de días muestra hoy Y
// mañana sin navegar — «el día siguiente no puede estar escondido». Medido
// antes del fix: AFF (10 días) mostraba hoy y cortaba mañana; Tribeca (12) no
// mostraba ninguno de los dos. La fórmula vieja vivía copiada en 3 sitios y
// solo corría al CARGAR el festival, no al volver desde otra pestaña.
test('T85 — al abrir Programa, hoy y mañana caben sin navegar', async ({ page }) => {
  test.setTimeout(90000);
  const casos = [
    ['aff2026', '2026-04-26T11:00:00-05:00'],
    ['tribeca2026', '2026-06-10T11:00:00-05:00'],
  ];
  for (const [fest, tm] of casos) {
    await enterFestival(page, fest, tm);
    await page.evaluate(() => document.querySelector('[data-action="citySheetAll"]')?.click());
    await page.waitForTimeout(500);
    // salir a otra pestaña y VOLVER — el caso que reportó Juan
    await page.evaluate(async () => {
      switchMainNav('mnav-miplan'); showAgView();
      await new Promise(r => setTimeout(r, 400));
      showDayView();
      await new Promise(r => setTimeout(r, 500));
    });
    const r = await page.evaluate(() => {
      const dt = document.getElementById('dtabs');
      const tabs = [...dt.querySelectorAll('.dtab')];
      const dr = dt.getBoundingClientRect();
      const on = dt.querySelector('.dtab.on');
      const next = tabs[tabs.indexOf(on) + 1] || null;
      const vis = t => { const b = t.getBoundingClientRect();
        return Math.round(b.left) >= Math.round(dr.left) - 1 && Math.round(b.right) <= Math.round(dr.right) + 1; };
      return { hoy: vis(on), manana: next ? vis(next) : null, dias: tabs.length };
    });
    expect(r.dias, `${fest} tiene barra con varios días`).toBeGreaterThan(6);
    expect(r.hoy, `${fest}: hoy a la vista al abrir Programa`).toBe(true);
    expect(r.manana, `${fest}: y mañana también, sin navegar`).toBe(true);
  }
});

// 18 ago (Juan, tras ver el ojo sobre el afiche): «el tap del póster abre la
// card — ese comportamiento no se cambia». Los controles salen del afiche a
// una fila centrada debajo: ojo tachado (devolver a vista) y estrella opaca
// (calificar), a la altura de las estrellas de las calificadas.
test('T86 — Diario: el afiche es solo afiche; los controles viven debajo', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-18T15:00:00-05:00');
  await page.evaluate(() => document.querySelector('[data-action="citySheetAll"]')?.click());
  await page.waitForTimeout(400);
  const r = await page.evaluate(async () => {
    const pick = (day, n) => FILMS.filter(f => f.day === day && f.poster && !f.is_cortos).slice(0, n);
    const s = pick('2026-08-13', 3);
    state.set('savedAgenda', { scenarioIdx: 0, schedule: s.map(f => Object.assign({}, f, { _title: f.title })) });
    state.set('watched', new Set()); state.set('notWatched', new Set([s[2].title]));
    state.set('filmRatings', { [s[0].title]: 4 });
    switchMainNav('mnav-miplan'); showAgView();
    await new Promise(r => setTimeout(r, 1400));
    // el muro vive detrás del tap (18 ago): la sección es una tira replegada
    document.querySelector('.dw-band')?.click();
    await new Promise(r => setTimeout(r, 900));
    const cards = [...document.querySelectorAll('.diary-sheet .dw-card')];
    const byTitle = t => cards.find(c => c.querySelector(`[data-title="${CSS.escape(t)}"]`));
    const cal = byTitle(s[0].title), sinCal = byTitle(s[1].title), negada = byTitle(s[2].title);
    const bajoElAfiche = c => { const p = c.querySelector('.dw-poster'), row = c.querySelector('.dw-row');
      return !!p && !!row && row.getBoundingClientRect().top >= p.getBoundingClientRect().bottom - 1; };
    const centrado = c => { const row = c.querySelector('.dw-row'), el = row.firstElementChild;
      const rr = row.getBoundingClientRect(), er = el.getBoundingClientRect();
      return Math.abs((er.left + er.right) / 2 - (rr.left + rr.right) / 2) <= 2; };
    return {
      nadaEncima: cards.every(c => !c.querySelector('.dw-poster > :not(img)')),
      posterAbreFicha: cards.every(c => c.querySelector('.dw-poster')?.classList.contains('js-open-pel')),
      // la negada ofrece el ojo; la no calificada, la estrella; la calificada, sus estrellas
      negadaOjo: !!negada?.querySelector('.dw-ctrl[data-action="toggleWatched"]'),
      sinCalEstrella: !!sinCal?.querySelector('.dw-ctrl-star[data-action="openRatingSheet"]'),
      calEstrellas: cal?.querySelectorAll('.dw-stars .dw-star.on').length,
      negadaSinEstrella: !negada?.querySelector('.dw-ctrl-star'),
      bajo: [cal, sinCal, negada].every(bajoElAfiche),
      centrados: [sinCal, negada].every(centrado),
      // la fila reserva su alto aunque el control sea el mismo → misma línea base
      mismaBase: new Set([cal, sinCal, negada].map(c => Math.round(c.querySelector('.dw-row').getBoundingClientRect().top))).size === 1,
    };
  });
  expect(r.nadaEncima, 'el afiche no lleva nada encima').toBe(true);
  expect(r.posterAbreFicha, 'y su tap abre la ficha, como en toda la app').toBe(true);
  expect(r.negadaOjo, 'la negada ofrece el ojo tachado para volver a vista').toBe(true);
  expect(r.sinCalEstrella, 'la no calificada ofrece la estrella opaca').toBe(true);
  expect(r.calEstrellas, 'la calificada muestra su calificación').toBe(4);
  expect(r.negadaSinEstrella, 'a la negada no se le pide calificar').toBe(true);
  expect(r.bajo, 'los controles viven DEBAJO del afiche').toBe(true);
  expect(r.centrados, 'y centrados en su fila').toBe(true);
  expect(r.mismaBase, 'la fila reserva su alto: los pósters no bailan').toBe(true);
});

// 18 ago (Juan): «al abrir la Card debe aparecer Vista, con el ojito; siempre
// primero la opción de Vista». Lo que había era una mentira de interfaz: el
// botón decía «Calificar» con estrella y su acción era toggleWatched — marcaba
// vista. Ahora el ojo y el label dicen lo que el botón hace, en los dos estados.
test('T87 — la card ofrece VISTA con el ojo, y calificar viene después', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-18T15:00:00-05:00');
  await page.evaluate(() => document.querySelector('[data-action="citySheetAll"]')?.click());
  await page.waitForTimeout(400);
  const r = await page.evaluate(async () => {
    const f = FILMS.find(x => !x.is_cortos && x.poster);
    openPelSheet(f.title);
    await new Promise(r => setTimeout(r, 700));
    const btn = document.getElementById('pel-vista-btn');
    const antes = { txt: btn?.textContent.trim(), accion: btn?.dataset.action,
      // el icono del ojo trae su círculo (pupila); la estrella, un polígono
      ojo: !!btn?.querySelector('circle'), estrella: !!btn?.querySelector('polygon') };
    // marcarla vista → la card pasa al estado ya-vista
    btn.click();
    await new Promise(r => setTimeout(r, 500));
    const modal = [...document.querySelectorAll('button')].find(b => /Sí|Marcar|Confirmar/i.test(b.textContent));
    if (modal) { modal.click(); await new Promise(r => setTimeout(r, 700)); }
    const vistos = [...document.querySelectorAll('.pel-sheet-ctas-watched .pel-sheet-action-btn')]
      .map(b => ({ txt: b.textContent.trim(), ojo: !!b.querySelector('circle'), estrella: !!b.querySelector('polygon') }));
    return { antes, vistos };
  });
  expect(r.antes.accion, 'el botón marca vista…').toBe('toggleWatched');
  expect(r.antes.txt, '…y lo dice: Vista, no Calificar').toMatch(/Vista|Seen|Watched/);
  expect(r.antes.ojo, 'con el ojo, el icono de watched').toBe(true);
  expect(r.antes.estrella, 'sin estrella: calificar es otra cosa').toBe(false);
  if (r.vistos.length) {
    expect(r.vistos[0].txt, 'ya vista: Vista sigue primero').toMatch(/Vista|Seen|Watched/);
    expect(r.vistos[0].ojo, 'y con el ojo, no con el check').toBe(true);
  }
});

// 18 ago (Juan): el vacío de Sugerencias gastaba 114px y una lupa de 20 para
// una frase de 31 caracteres — el vacío pesaba más que el contenido. Y la lupa
// decía «búsqueda fallida» cuando lo que pasa es que el catálogo se agotó.
test('T88 — el vacío de Sugerencias es una línea, no una pantalla', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-18T19:30:00-05:00');
  await page.evaluate(() => document.querySelector('[data-action="citySheetAll"]')?.click());
  await page.waitForTimeout(400);
  const r = await page.evaluate(async () => {
    const f = FILMS.filter(x => x.day === '2026-08-18' && x.time >= '19:00').slice(0, 3);
    state.set('savedAgenda', { scenarioIdx: 0, schedule: f.map(x => Object.assign({}, x, { _title: x.title })) });
    switchMainNav('mnav-miplan'); showAgView();
    await new Promise(r => setTimeout(r, 1400));
    const w = document.querySelector('.suggestion-wrap');
    const linea = w?.querySelector('.sug-vacio');
    return { hay: !!linea, alto: linea && Math.round(linea.getBoundingClientRect().height),
      pantallaVieja: !!w?.querySelector('.empty-state'),
      txt: linea?.textContent.trim() };
  });
  expect(r.hay, 'el vacío existe y nombra el día').toBe(true);
  expect(r.txt, 'con el día, no un «hoy» falso').toMatch(/MAR 18/);
  expect(r.alto, 'y cabe en una línea').toBeLessThanOrEqual(30);
  expect(r.pantallaVieja, 'sin la pantalla vacía con lupa').toBe(false);
});

// 18 ago (Juan, UX Writer): «no te daría» es una afirmación sobre tu futuro —
// nunca afirmamos, sugerimos. La línea del Q&A pasa a describir la aritmética
// de la estimación: cuánto queda, o cuánto se cruza. El sujeto es la charla y
// el reloj, no el usuario («si te quedás te quedarían» se fue con su redundancia).
test('T89 — la línea del Q&A cuenta el reloj, no predice tu suerte', async ({ page }) => {
  test.setTimeout(60000);
  await enterFestival(page, 'finca2026', '2026-08-18T09:00:00-03:00');
  await page.evaluate(() => document.querySelector('[data-action="citySheetAll"]')?.click());
  await page.waitForTimeout(400);
  const r = await page.evaluate(async () => {
    const dur = f => parseInt(String(f.duration).match(/\d+/)?.[0] || 90, 10);
    const mins = t => { const [h, m] = t.split(':').map(Number); return h * 60 + m; };
    const out = { cabe: null, cruza: null };
    for (const prev of FILMS.filter(f => f.has_qa)) {
      const fin = mins(prev.time) + dur(prev);
      for (const next of FILMS.filter(f => f.day === prev.day && f.venue === prev.venue && mins(f.time) > fin)) {
        const qaGap = mins(next.time) - fin - 30;
        const target = qaGap >= 0 && qaGap < 25 ? 'cabe' : (qaGap < 0 && qaGap > -40 ? 'cruza' : null);
        if (!target || out[target]) continue;
        _simTime = prev.day + 'T08:00:00-03:00';
        state.set('savedAgenda', { scenarioIdx: 0, schedule: [prev, next].map(f => Object.assign({}, f, { _title: f.title })) });
        switchMainNav('mnav-miplan'); showAgView();
        await new Promise(r => setTimeout(r, 900));
        const w = [...document.querySelectorAll('.mplan-warn-row')].find(e => /Q&A/.test(e.textContent));
        if (w) out[target] = w.textContent.replace(/\s+/g, ' ').trim();
      }
      if (out.cabe && out.cruza) break;
    }
    return out;
  });
  const todo = [r.cabe, r.cruza].filter(Boolean).join(' | ');
  expect(todo, 'la escena produjo al menos una línea de Q&A').toBeTruthy();
  expect(todo, 'sin veredicto sobre tu futuro').not.toMatch(/no te daría|wouldn.t make it/);
  expect(todo, 'y sin decirte qué harías').not.toMatch(/si te quedás|te quedarían/);
  if (r.cabe) expect(r.cabe, 'cuando cabe: cuánto queda hasta la siguiente').toMatch(/quedan ~\d+ min hasta la siguiente/);
  if (r.cruza) expect(r.cruza, 'cuando no: cuánto se cruza, con su número').toMatch(/se cruza ~\d+ min con la siguiente/);
});

// 18 ago, discusión de Planear (Juan: «mantener la simplicidad pero comunicar
// mejor»): la pantalla pedía calcular sin decir qué iba a procesar. Ahora dice
// el INSUMO («8 obras · 3 con prioridad»), el SUPUESTO (la banda de
// Disponibilidad muestra su valor, no «opcional») y el PRE-DIAGNÓSTICO (los
// cruces sin salida, en ámbar, con oráculo independiente en este test).
test('T90 — Planear dice qué va a procesar antes de que lo pidas', async ({ page }) => {
  test.setTimeout(60000);
  await enterFestival(page, 'ficdeh2026', '2026-08-18T08:21:00-05:00');
  // con filtro de CIUDAD: en un festival multiciudad casi todo choque es de
  // ciudad, y el pre-diagnóstico solo afirma solapes de reloj.
  await page.evaluate(() => [...document.querySelectorAll('#city-sheet [data-action]')]
    .find(x => x.textContent.includes('Bogotá'))?.click());
  await page.waitForTimeout(400);
  const r = await page.evaluate(async () => {
    const D = await import('/src/domain/film.js');
    const S = await import('/src/domain/schedule.js');
    // La selección INCLUYE obras con ≥2 funciones: ahí un predicado débil
    // (some en vez de every) infla la cuenta — el cruce con salida no es cruce.
    const porT = {};
    FILMS.forEach(f => { if (!D.screeningPassed(f)) (porT[f.title] = porT[f.title] || []).push(f); });
    // la selección INCLUYE pares que se pisan de verdad, y obras con ≥2
    // funciones (ahí un predicado débil inflaría la cuenta: el cruce con salida
    // no es cruce).
    const pisanTodo = (a, b) => porT[a].every(x => porT[b].every(y => {
      const r = S.screensConflictReason(x, y); return !!r && r.kind === 'solape'; }));
    const ts0 = Object.keys(porT);
    const conSolape = new Set();
    for (let i = 0; i < ts0.length && conSolape.size < 6; i++)
      for (let j = i + 1; j < ts0.length && conSolape.size < 6; j++)
        if (pisanTodo(ts0[i], ts0[j])) { conSolape.add(ts0[i]); conSolape.add(ts0[j]); }
    const multi = ts0.filter(t => porT[t].length >= 2 && !conSolape.has(t));
    const sel = [...conSolape, ...multi.slice(0, 3)];
    state.set('watchlist', new Set(sel));
    state.set('prioritized', new Set(sel.slice(0, 3)));
    const base = FILMS.find(f => f.day === '2026-08-19' && !sel.includes(f.title));
    state.set('savedAgenda', { scenarioIdx: 0, schedule: [Object.assign({}, base, { _title: base.title })] });
    cachedResult = null;
    switchMainNav('mnav-planner'); showAgView();
    await new Promise(r => setTimeout(r, 1500));
    // oráculo independiente: parejas cuyas funciones chocan en TODAS las combinaciones
    const por = {};
    FILMS.forEach(f => { if (sel.includes(f.title) && !D.screeningPassed(f)) (por[f.title] = por[f.title] || []).push(f); });
    const ts = Object.keys(por); let esperados = 0, debiles = 0;
    for (let i = 0; i < ts.length; i++) for (let j = i + 1; j < ts.length; j++) {
      const pisan = (x, y) => { const r = S.screensConflictReason(x, y); return !!r && r.kind === 'solape'; };
      if (por[ts[i]].every(x => por[ts[j]].every(y => pisan(x, y)))) esperados++;
      if (por[ts[i]].some(x => por[ts[j]].some(y => pisan(x, y)))) debiles++;
    }
    // materializar ANTES del re-render (los nodos quedan huérfanos después)
    // El conteo se acota a Planear (2 sep 2026): contaba .dato-linea en TODO el
    // documento y eso solo funcionaba mientras ninguna otra pantalla usara el
    // canon. La hoja «¡Tu Plan está listo!» lo adoptó y el test cayó sin que
    // Planear hubiera cambiado — medía la app entera creyendo medir una vista.
    const _plan = document.getElementById('ag-view');
    const linea = _plan.querySelector('.dato-linea');
    const _insumo = linea?.textContent.replace(/\s+/g, ' ').trim();
    const _cr = linea?.querySelector('.dato-alerta');
    const _crTxt = _cr?.textContent.trim() || null;
    const _crColor = _cr && getComputedStyle(_cr).color;
    const _fs = linea && getComputedStyle(linea).fontSize;
    // ritmo 1:2 — el hueco al CTA no puede ser el de «entre secciones»
    const _cta = document.querySelector('.av-calc-btn');
    const _gapCta = (_cta && linea) ? Math.round(_cta.getBoundingClientRect().top - linea.getBoundingClientRect().bottom) : null;
    const _filas = _plan.querySelectorAll('.dato-linea').length;
    const fila = document.querySelector('.av-fila');
    const _filaTxt = fila?.textContent.replace(/\s+/g, ' ').trim();
    const _editar = fila?.querySelector('.av-editar')?.textContent.trim() || null;
    // con una restricción configurada, el bloque se VE (no hay acordeón)
    const av = { ...state.snapshot().availability };
    av[Object.keys(av)[6]] = { blocks: [{ from: '09:00', to: '14:00' }] };
    state.set('availability', av);
    switchMainNav('mnav-planner'); showAgView();
    await new Promise(r => setTimeout(r, 900));
    const bloqueVisible = (() => { const b = document.getElementById('av-blocks-list');
      return !!b && b.children.length > 0 && b.offsetParent !== null; })();
    return {
      esperados, debiles, pendientes: ts.length,
      insumo: _insumo, cruces: _crTxt, crucesColor: _crColor, fs: _fs, gapCta: _gapCta, filas: _filas,
      filaTxt: _filaTxt, editar: _editar,
      acordeon: !!document.querySelector('.ag-av-details'),
      bloqueVisible,
    };
  });
  // UNA sola línea con la fórmula «texto · texto»: insumo y aviso conviven
  expect(r.filas, 'una sola línea, no dos').toBe(1);
  // El insumo dice ahora de qué conjunto habla («N obras POR PLANEAR»): la cifra
  // de arriba y la del resultado usaban la misma clave a 113px una de otra. El
  // aserto se REAPUNTA —su intención es que el insumo abra la línea, no el
  // literal— porque dejarlo pasaría a medir una frase que ya no existe.
  expect(r.insumo, 'el insumo abre la línea').toMatch(new RegExp(`^${r.pendientes} obras por planear · \\d+ con prioridad`));
  expect(r.fs, 'con el cuerpo del canon (t-base), no t-sm').toBe('13px');
  expect(r.gapCta, 'y el salto al CTA es sp-4, no «entre secciones»').toBeLessThanOrEqual(20);
  expect(r.esperados, 'la escena tiene cruces que diagnosticar').toBeGreaterThan(0);
  expect(r.debiles, 'y distingue el predicado: un cruce con salida no es cruce').toBeGreaterThan(r.esperados);
  // solapes puros: dato del programa, afirmable. Los cruces por viaje son
  // estimación nuestra y no se anuncian como hecho antes de calcular.
  expect(r.cruces, 'el pre-diagnóstico dice el número del oráculo de SOLAPES')
    .toBe(r.esperados === 1 ? '1 cruce de horario' : `${r.esperados} cruces de horario`);
  expect(r.crucesColor, 'en ámbar: aviso, no veredicto').toBe('rgb(245, 158, 11)');
  // La fila de Disponibilidad: sin acordeón, sin valor verbal (Juan: confundía)
  // — el estado lo dicen los BLOQUES visibles. «Editar» hereda el objeto.
  expect(r.acordeon, 'el acordeón murió').toBe(false);
  expect(r.editar, 'la fila ofrece Editar — el verbo hereda el objeto').toMatch(/^Editar$|^Edit$/);
  expect(r.filaTxt, 'sin «opcional» ni valor verbal').not.toMatch(/opcional|restriccion/i);
  expect(r.bloqueVisible, 'con restricción configurada, el bloque SE VE').toBe(true);
});

// 18 ago (Juan): «quiero que se vean siempre claros los botones inferiores,
// sin navegar la card». Medido antes: con 352 caracteres de sinopsis la ficha
// topaba en 88dvh y los CTAs caían 96px BAJO el borde visible. El alto ya era
// responsive (411px en un evento sin sinopsis); lo que faltaba era anclar el pie.
test('T91 — la ficha: alto según su contenido y los CTAs siempre a la vista', async ({ page }) => {
  test.setTimeout(60000);
  await enterFestival(page, 'ficdeh2026', '2026-08-18T09:00:00-05:00');
  await page.evaluate(() => document.querySelector('[data-action="citySheetAll"]')?.click());
  await page.waitForTimeout(400);
  const r = await page.evaluate(async () => {
    const largo = f => (f.synopsis || '').length + (f.film_list?.length || 0) * 200;
    const orden = [...FILMS].sort((a, b) => largo(b) - largo(a));
    const casos = [orden[orden.length - 1], orden[0]]; // la más corta y la más larga
    const out = [];
    for (const f of casos) {
      openPelSheet(f.title);
      await new Promise(r => setTimeout(r, 700));
      const sh = document.getElementById('pel-sheet');
      const cta = sh.querySelector('.pel-sheet-ctas, .pel-sheet-ctas-watched');
      const shr = sh.getBoundingClientRect(), ctr = cta.getBoundingClientRect();
      out.push({
        alto: Math.round(shr.height),
        scrollea: sh.scrollHeight > sh.clientHeight + 2,
        // el CTA cabe DENTRO del rectángulo visible de la sheet
        dentro: Math.round(ctr.bottom) <= Math.round(shr.bottom) + 1 && Math.round(ctr.top) >= Math.round(shr.top),
        piePegado: getComputedStyle(sh.querySelector('.pel-sheet-foot')).position,
      });
      closePelSheet(); await new Promise(r => setTimeout(r, 300));
    }
    return { corta: out[0], larga: out[1], vp: innerHeight };
  });
  // alto según contenido: la corta NO llega al tope y no scrollea
  expect(r.corta.scrollea, 'la ficha corta cabe entera').toBe(false);
  expect(r.corta.alto, 'y mide bastante menos que el tope').toBeLessThan(r.vp * 0.7);
  expect(r.larga.scrollea, 'la larga sí scrollea su cuerpo').toBe(true);
  // y en AMBAS los botones están a la vista sin navegar
  expect(r.corta.dentro, 'CTAs a la vista en la corta').toBe(true);
  expect(r.larga.dentro, 'CTAs a la vista en la larga, sin scrollear').toBe(true);
  expect(r.larga.piePegado, 'el pie va anclado').toBe('sticky');
});

// 18 ago (Juan): «el separador dice Opción y tiene badge, se entiende como el
// número de Opción». Un badge junto a un sustantivo CONTABLE se lee como su
// índice — y el 5 eran las obras. Ya pasamos por «Plan Óptimo»: el problema no
// era la palabra, era el badge. Muere la banda; el resumen usa la línea de dato
// («6 obras · 2 días») y los días adoptan la banda ámbar del separador de horas
// de Programa, con su conteo.
test('T92 — el resultado: sin banda «Opción», resumen en línea y días como Programa', async ({ page }) => {
  test.setTimeout(90000);
  await enterFestival(page, 'ficdeh2026', '2026-08-18T08:00:00-05:00');
  await page.evaluate(() => [...document.querySelectorAll('#city-sheet [data-action]')]
    .find(x => x.textContent.includes('Bogotá'))?.click());
  await page.waitForTimeout(500);
  const r = await page.evaluate(async () => {
    const D = await import('/src/domain/film.js');
    const bog = f => (f.venue || '').includes('Bogotá');
    const fut = [...new Set(FILMS.filter(f => bog(f) && !D.screeningPassed(f)).map(f => f.title))];
    state.set('watchlist', new Set(fut.slice(0, 10)));
    cachedResult = null; savedAgenda = null;
    switchMainNav('mnav-planner'); showAgView();
    await new Promise(r => setTimeout(r, 800));
    document.querySelector('.av-calc-btn').click();
    for (let i = 0; i < 40 && !document.querySelector('.ag-day-band'); i++) await new Promise(r => setTimeout(r, 250));
    const sum = document.querySelector('.ag-summary');
    const bandas = [...document.querySelectorAll('.ag-day-band')];
    const b0 = bandas[0];
    return {
      bandaOpcion: !!sum?.querySelector('.sec-hdr'),
      resumen: sum?.querySelector('.dato-resultado')?.textContent.trim(),
      // el resumen NO lleva badge: un número en píldora se leía como índice
      resumenBadge: !!sum?.querySelector('.count-badge'),
      nBandas: bandas.length,
      // los días heredan la anatomía del separador de horas de Programa
      color: b0 && getComputedStyle(b0).color,
      caps: b0 && getComputedStyle(b0).letterSpacing,
      conteoDia: !!b0?.querySelector('.count-badge'),
      txt: b0?.textContent.replace(/\s+/g, ' ').trim(),
      // y el conteo del día coincide con las filas que lo siguen
      dias: new Set((cachedResult.scenarios[cachedResult.currentIdx || 0].schedule || []).map(s => s.day)).size,
    };
  });
  expect(r.bandaOpcion, 'la banda «Opción» murió').toBe(false);
  // El sustantivo lo elige el contenido (T153): con un taller o una charla en el
  // Plan la línea dice «actividades». Lo que este test afirma es la FORMA
  // —«N sustantivo · N días»—, no cuál de los dos sustantivos toca.
  expect(r.resumen, 'el resumen es una línea de dato: N cosas · N días')
    .toMatch(/\d+ (?:obras?|actividades?) · \d+ días?/);
  expect(r.resumenBadge, 'sin badge — el número no puede leerse como índice').toBe(false);
  expect(r.nBandas, 'hay una banda por día del plan').toBe(r.dias);
  expect(r.color, 'los días van en ámbar, como las horas de Programa').toBe('rgb(245, 158, 11)');
  expect(parseFloat(r.caps), 'con el tracking del separador de horas').toBeGreaterThan(0.5);
  expect(r.conteoDia, 'y conservan su conteo').toBe(true);
  expect(r.txt, 'el día va en mayúsculas').toMatch(/^[A-ZÁÉÍÓÚÑ]/);
});

test('T93 — el resultado se distingue del insumo, y «sin cupo» no se inventa el número', async ({ page }) => {
  test.setTimeout(90000);
  await enterFestival(page, 'ficdeh2026', '2026-08-18T08:00:00-05:00');
  await page.evaluate(() => [...document.querySelectorAll('#city-sheet [data-action]')]
    .find(x => x.textContent.includes('Bogotá'))?.click());
  await page.waitForTimeout(500);
  const r = await page.evaluate(async () => {
    const D = await import('/src/domain/film.js');
    const bog = f => (f.venue || '').includes('Bogotá');
    const fut = [...new Set(FILMS.filter(f => bog(f) && !D.screeningPassed(f)).map(f => f.title))];
    // 14 obras para forzar que alguna se quede fuera y exista el matiz, MÁS
    // obras que el festival ya se llevó: sin ellas sc.excluded y _excVivas dan
    // el mismo número y el oráculo no distingue nada (la mutación pasaba).
    // «ya se la llevó el festival» = TODAS sus funciones pasaron. Con «alguna»
    // entran obras que aún tienen función futura y el motor sí puede planear.
    const porT = {};
    FILMS.filter(bog).forEach(f => (porT[f.title] = porT[f.title] || []).push(f));
    const idas = Object.keys(porT).filter(t => porT[t].every(f => D.screeningPassed(f))).slice(0, 3);
    state.set('watchlist', new Set([...fut.slice(0, 14), ...idas]));
    cachedResult = null; savedAgenda = null;
    switchMainNav('mnav-planner'); showAgView();
    await new Promise(r => setTimeout(r, 1500));
    // el insumo vive ARRIBA del botón; se mide antes de calcular
    const insumo = document.querySelector('.pre-resumen .dato-linea');
    // se leen los NÚMEROS ya: getComputedStyle devuelve un objeto vivo y el
    // cálculo re-renderiza — guardar la referencia daba '' (y NaN al medir).
    const insumoPx = insumo ? parseFloat(getComputedStyle(insumo).fontSize) : null;
    const insumoPeso = insumo ? parseInt(getComputedStyle(insumo).fontWeight) : null;
    document.querySelector('.av-calc-btn').click();
    for (let i = 0; i < 40 && !document.querySelector('.ag-day-band'); i++) await new Promise(r => setTimeout(r, 250));
    const res = document.querySelector('.dato-resultado');
    const cs = res && getComputedStyle(res);
    const cupo = res?.querySelector('.dato-linea');
    const band = document.querySelector('.ag-day-band');
    return {
      insumoPx, insumoPeso,
      resPx: cs && parseFloat(cs.fontSize),
      resPeso: cs && parseInt(cs.fontWeight),
      resColor: cs && cs.color,
      // el matiz sigue siendo gris y más chico que la afirmación que acompaña
      cupoTxt: cupo?.textContent.trim() || '',
      cupoPx: cupo && parseFloat(getComputedStyle(cupo).fontSize),
      cupoColor: cupo && getComputedStyle(cupo).color,
      // el N de «sin cupo» tiene que ser el de la lista que se ve, no otro
      nFilas: document.querySelectorAll('.ag-excl-block .int-item').length,
      // control de que el oráculo NO es vacuo: si estos dos números fueran
      // iguales, «sin cupo» podría salir de cualquiera de los dos conteos.
      nExcluidasCrudas: (cachedResult.scenarios[cachedResult.currentIdx || 0].excluded || []).length,
      // y la línea pertenece a la banda de abajo, no al botón de arriba
      huecoAbajo: band && res ? Math.round(band.getBoundingClientRect().top - res.getBoundingClientRect().bottom) : null,
    };
  });
  expect(r.resPx, 'el resultado es más grande que el insumo').toBeGreaterThan(r.insumoPx);
  expect(r.resPeso, 'y más pesado').toBeGreaterThan(r.insumoPeso);
  expect(r.resColor, 'el resultado va en blanco — es la respuesta').toBe('rgb(240, 237, 232)');
  if (r.nFilas > 0) {
    expect(r.nExcluidasCrudas, 'el escenario distingue: hay excluidas que el festival ya se llevó')
      .toBeGreaterThan(r.nFilas);
    expect(r.cupoTxt, 'con obras fuera, el resultado dice cuántas').toMatch(/\d+/);
    expect(parseInt(r.cupoTxt.match(/\d+/)[0]), 'y ese número es el de la lista que se ve')
      .toBe(r.nFilas);
    expect(r.cupoPx, 'el matiz es más chico que la afirmación').toBeLessThan(r.resPx);
    expect(r.cupoColor, 'y sigue siendo gris').toBe('rgb(136, 136, 136)');
  }
  expect(r.huecoAbajo, 'el resultado queda pegado a la banda que describe').toBeLessThanOrEqual(16);
});

test('T94 — lo que nunca compitió no cuenta como costo del Plan, y no se pierde', async ({ page }) => {
  test.setTimeout(90000);
  await enterFestival(page, 'ficdeh2026', '2026-08-18T08:00:00-05:00');
  await page.evaluate(() => [...document.querySelectorAll('#city-sheet [data-action]')]
    .find(x => x.textContent.includes('Bogotá'))?.click());
  await page.waitForTimeout(500);
  const r = await page.evaluate(async () => {
    const D = await import('/src/domain/film.js');
    const bog = f => (f.venue || '').includes('Bogotá');
    const fut = [...new Set(FILMS.filter(f => bog(f) && !D.screeningPassed(f)).map(f => f.title))];
    state.set('watchlist', new Set(fut.slice(0, 14)));
    cachedResult = null; savedAgenda = null;
    switchMainNav('mnav-planner'); showAgView();
    for (let i = 0; i < 40 && !document.querySelector('.ag-day-band'); i++) await new Promise(r => setTimeout(r, 250));
    await new Promise(r => setTimeout(r, 400));
    const sc = cachedResult.scenarios[cachedResult.currentIdx || 0];
    const city = document.querySelector('.ag-excl-city');
    const filasCiudad = [...document.querySelectorAll('.ag-excl-city .int-item')];
    return {
      titular: document.querySelector('.dato-resultado')?.textContent.replace(/\s+/g, ' ').trim(),
      nCompiten: document.querySelectorAll('.ag-excl-block .int-item').length,
      nCiudad: filasCiudad.length,
      // oráculo independiente: el total de excluidas VIVAS del escenario
      nVivas: (sc.excluded || []).filter(t => FILMS.some(f => f.title === t && !D.screeningPassed(f))).length,
      abierta: !!city?.open,
      // en «otra ciudad» no se repite la razón ni se ofrece lo que el motor rechaza
      razones: filasCiudad.filter(x => x.querySelector('.excl-reason')).length,
      botones: filasCiudad.filter(x => x.querySelector('.excl-include-btn')).length,
      // la explicación se dice UNA vez, con la ciudad del Plan
      sub: document.querySelector('.excl-city-sub')?.textContent.trim() || '',
      // y cada fila aporta la suya
      ciudadEnFila: filasCiudad.every(x => /·/.test(x.querySelector('.int-item-when')?.textContent || '')),
    };
  });
  expect(r.nCiudad, 'el escenario tiene obras de otra ciudad (si no, el test no prueba nada)').toBeGreaterThan(0);
  expect(r.nCompiten + r.nCiudad, 'ninguna excluida se pierde entre las dos secciones').toBe(r.nVivas);
  expect(r.titular, 'el titular cuenta SOLO las que compitieron').toContain(String(r.nCompiten));
  expect(r.nCompiten, 'y el escenario distingue: no todas compitieron').toBeLessThan(r.nVivas);
  expect(r.abierta, 'la sección sin acciones arranca replegada').toBe(false);
  expect(r.razones, 'la razón no se repite fila por fila').toBe(0);
  expect(r.botones, 'no se ofrece un botón que el motor va a rechazar').toBe(0);
  expect(r.sub, 'la explicación se dice una vez, con la ciudad del Plan').toMatch(/Bogotá/);
  expect(r.ciudadEnFila, 'cada fila aporta su ciudad').toBe(true);
});

test('T95 — la alerta de cruces es un pre-diagnóstico: no sobrevive al resultado', async ({ page }) => {
  test.setTimeout(90000);
  await enterFestival(page, 'ficdeh2026', '2026-08-18T08:00:00-05:00');
  await page.evaluate(() => [...document.querySelectorAll('#city-sheet [data-action]')]
    .find(x => x.textContent.includes('Bogotá'))?.click());
  await page.waitForTimeout(500);
  const r = await page.evaluate(async () => {
    const D = await import('/src/domain/film.js');
    const bog = f => (f.venue || '').includes('Bogotá');
    const fut = [...new Set(FILMS.filter(f => bog(f) && !D.screeningPassed(f)).map(f => f.title))];
    state.set('watchlist', new Set(fut.slice(0, 14)));
    state.set('prioritized', new Set(fut.slice(0, 2)));
    // showAgView() calcula solo si no hay Plan guardado (pipeline.js): para ver
    // el estado PREVIO se le da uno, así el pre-diagnóstico queda a la vista.
    const base = FILMS.find(f => bog(f) && !D.screeningPassed(f));
    state.set('savedAgenda', { scenarioIdx: 0, schedule: [Object.assign({}, base, { _title: base.title })] });
    cachedResult = null;
    switchMainNav('mnav-planner'); showAgView();
    await new Promise(r => setTimeout(r, 1500));
    const antes = {
      alerta: !!document.querySelector('.pre-resumen .dato-alerta'),
      linea: document.querySelector('.pre-resumen .dato-linea')?.textContent.replace(/\s+/g, ' ').trim(),
    };
    document.querySelector('.av-calc-btn').click();
    for (let i = 0; i < 40 && !document.querySelector('.ag-day-band'); i++) await new Promise(r => setTimeout(r, 250));
    await new Promise(r => setTimeout(r, 400));
    const banner = document.querySelector('.meta-banner-text');
    return {
      antes,
      despuesAlerta: !!document.querySelector('.pre-resumen .dato-alerta'),
      despuesLinea: document.querySelector('.pre-resumen .dato-linea')?.textContent.replace(/\s+/g, ' ').trim(),
      banner: banner ? banner.textContent.replace(/\s+/g, ' ').trim() : null,
    };
  });
  expect(r.antes.alerta, 'antes de calcular la alerta SÍ está (si no, el test no prueba nada)').toBe(true);
  expect(r.despuesAlerta, 'con el resultado en pantalla la alerta se retira').toBe(false);
    // Sustantivo agnóstico por la misma razón que T92: acá se afirma que el dato
    // SIGUE, no con qué palabra se nombra (eso lo vigila T153).
  expect(r.despuesLinea, 'el insumo SIGUE en pantalla tras calcular — si desaparece, se fue el dato con la alerta')
    .toBeTruthy();
  expect(r.despuesLinea, 'el insumo se conserva: se va la alerta, no el dato')
    .toMatch(/\d+ (?:obras?|actividades?)/);
  if (r.banner) {
    expect(r.banner, 'punto seguido de raya no es puntuación española').not.toMatch(/\.\s*—/);
    expect(r.banner, 'la segunda oración arranca en mayúscula').toMatch(/\.\s+[A-ZÁÉÍÓÚÑ]/);
  }
});

test('T96 — el botón admite que ya calculó, y no compite con el que confirma', async ({ page }) => {
  test.setTimeout(90000);
  await enterFestival(page, 'ficdeh2026', '2026-08-18T08:00:00-05:00');
  await page.evaluate(() => [...document.querySelectorAll('#city-sheet [data-action]')]
    .find(x => x.textContent.includes('Bogotá'))?.click());
  await page.waitForTimeout(500);
  const r = await page.evaluate(async () => {
    const D = await import('/src/domain/film.js');
    const bog = f => (f.venue || '').includes('Bogotá');
    const fut = [...new Set(FILMS.filter(f => bog(f) && !D.screeningPassed(f)).map(f => f.title))];
    state.set('watchlist', new Set(fut.slice(0, 12)));
    // con Plan guardado NO hay auto-cálculo (pipeline.js): se ve el estado previo
    const base = FILMS.find(f => bog(f) && !D.screeningPassed(f));
    state.set('savedAgenda', { scenarioIdx: 0, schedule: [Object.assign({}, base, { _title: base.title })] });
    cachedResult = null;
    switchMainNav('mnav-planner'); showAgView();
    await new Promise(r => setTimeout(r, 1500));
    // ámbar del canon primario: el primer stop del degradado
    const AMBAR = '251, 191, 36';
    const primarios = () => [...document.querySelectorAll('button')]
      .filter(b => b.offsetParent !== null)
      .filter(b => (getComputedStyle(b).backgroundImage || '').includes(AMBAR))
      .map(b => b.textContent.replace(/\s+/g, ' ').trim());
    const btn = () => document.querySelector('.av-calc-btn');
    const esAmbar = el => (getComputedStyle(el).backgroundImage || '').includes(AMBAR);
    const antes = { txt: btn().textContent.trim(), recalc: btn().classList.contains('recalc'), ambar: esAmbar(btn()) };
    btn().click();
    for (let i = 0; i < 40 && !document.querySelector('.ag-day-band'); i++) await new Promise(r => setTimeout(r, 250));
    await new Promise(r => setTimeout(r, 400));
    return { antes, despues: { txt: btn().textContent.trim(), recalc: btn().classList.contains('recalc'),
      ambar: esAmbar(btn()), primarios: primarios() } };
  });
  // El rótulo pasó a «Ver opciones» (31 ago): la clave siempre se llamó
  // av_ver_opciones y su valor había derivado a «Calcular Mi Plan», que con un
  // Plan ya guardado prometía crear lo que el usuario tiene. El aserto se
  // REAPUNTA al rótulo nuevo — dejarlo en /Calcular/ lo volvería ciego.
  expect(r.antes.txt, 'sin resultado, el botón ofrece ver las opciones').toMatch(/Ver opciones/);
  expect(r.antes.recalc, 'y es el primario').toBe(false);
  expect(r.antes.ambar, 'sin resultado, calcular ES el CTA ámbar').toBe(true);
  expect(r.despues.txt, 'con resultado, nombra lo que de verdad haría').toMatch(/Recalcular/);
  expect(r.despues.recalc, 'y baja a secundario').toBe(true);
  expect(r.despues.ambar, 'y deja de vestirse de CTA primario').toBe(false);
  // El paso siguiente pasa a ser confirmar: «Usar este Plan» queda como el único
  // ámbar de PÁGINA. (Las acciones de fila del bloque de conflictos también son
  // ámbar por el canon; se cuentan aparte y no son parte de este cambio.)
  expect(r.despues.primarios.some(txt => /Plan/.test(txt)), 'el CTA que confirma sigue en ámbar').toBe(true);
  expect(r.despues.primarios.some(txt => /Ver opciones|Recalcular/.test(txt)), 'y el de calcular ya no compite').toBe(false);
});

test('T97 — el Plan que estás mirando no cambia solo: se marca y vos recalculás', async ({ page }) => {
  test.setTimeout(120000);
  await enterFestival(page, 'ficdeh2026', '2026-08-18T08:00:00-05:00');
  await page.evaluate(() => [...document.querySelectorAll('#city-sheet [data-action]')]
    .find(x => x.textContent.includes('Bogotá'))?.click());
  await page.waitForTimeout(500);
  const r = await page.evaluate(async () => {
    const D = await import('/src/domain/film.js');
    const bog = f => (f.venue || '').includes('Bogotá');
    const fut = [...new Set(FILMS.filter(f => bog(f) && !D.screeningPassed(f)).map(f => f.title))];
    state.set('watchlist', new Set(fut.slice(0, 12)));
    cachedResult = null; savedAgenda = null;
    switchMainNav('mnav-planner'); showAgView();
    for (let i = 0; i < 40 && !document.querySelector('.ag-day-band'); i++) await new Promise(r => setTimeout(r, 250));
    await new Promise(r => setTimeout(r, 300));
    const firma = () => cachedResult && cachedResult._inputSnapshot;
    const foto = () => ({
      titulos: [...document.querySelectorAll('#ag-result .saved-item')].length,
      stale: !!document.querySelector('.prio-stale'),
      confirmar: !!document.querySelector('.ag-save-btn'),
      confirmarOff: !!document.querySelector('.ag-save-btn[disabled]'),
      confirmarOpacidad: (() => { const b = document.querySelector('.ag-save-btn');
        return b ? parseFloat(getComputedStyle(b).opacity) : 1; })(),
      firma: firma(),
    });
    const inicial = foto();
    // gesto 1 — CORAZÓN: antes destruía el resultado y recalculaba en silencio
    const enPlan = [...document.querySelectorAll('#ag-result .saved-item')][0]?.dataset.title;
    const fuera = fut.slice(12, 13)[0];
    toggleWL(fuera);
    await new Promise(r => setTimeout(r, 600));
    const trasCorazon = foto();
    // gesto 2 — MARCADOR: el que ya conservaba (misma ley ahora)
    togglePriority(enPlan || fut[0]);
    await new Promise(r => setTimeout(r, 600));
    const trasMarcador = foto();
    // recalcular: el usuario decide cuándo
    document.querySelector('.av-calc-btn').click();
    for (let i = 0; i < 60 && document.querySelector('.prio-stale'); i++) await new Promise(r => setTimeout(r, 250));
    await new Promise(r => setTimeout(r, 300));
    return { inicial, trasCorazon, trasMarcador, tras: foto() };
  });
  expect(r.inicial.titulos, 'hay un Plan en pantalla').toBeGreaterThan(0);
  expect(r.inicial.stale, 'y arranca al día').toBe(false);
  expect(r.inicial.confirmarOff, 'con el Plan al día se puede confirmar').toBe(false);
  // el corazón ya no destruye ni recalcula: conserva y avisa
  expect(r.trasCorazon.titulos, 'el Plan sigue en pantalla tras tocar un interés').toBe(r.inicial.titulos);
  expect(r.trasCorazon.firma, 'y sigue siendo el MISMO cálculo (no recalculó solo)').toBe(r.inicial.firma);
  expect(r.trasCorazon.stale, 'pero queda marcado como desactualizado').toBe(true);
  expect(r.trasCorazon.confirmarOff, 'y no se puede confirmar un Plan que ya no corresponde').toBe(true);
  expect(r.trasCorazon.confirmarOpacidad, 'y se NOTA que no se puede (un botón muerto no puede verse vivo)')
    .toBeLessThan(0.5);
  // el marcador se comporta IGUAL que el corazón: una sola ley
  expect(r.trasMarcador.stale, 'la prioridad sigue la misma ley').toBe(true);
  expect(r.trasMarcador.firma, 'tampoco recalcula sola').toBe(r.inicial.firma);
  // y al pedirlo, se pone al día
  expect(r.tras.stale, 'al recalcular se va la marca').toBe(false);
  expect(r.tras.firma, 'y el cálculo es otro').not.toBe(r.inicial.firma);
  expect(r.tras.confirmarOff, 'y vuelve a poder confirmarse').toBe(false);
});

test('T98 — ningún texto del póster cruza la línea de margen de la retícula', async ({ page }) => {
  test.setTimeout(90000);
  await enterFestival(page, 'ficdeh2026', '2026-08-18T08:00:00-05:00');
  const r = await page.evaluate(async () => {
    const C = await import('/src/view/components.js');
    // Retícula §6.0: u = ancho/8 = 15, margen 0,75u = 11,25. Las «reglas» son
    // x ≤ 108,75 y y ≤ 168,75 — Juan las pidió tras ver textos tocando el borde.
    const M = 11.25, DER = 120 - M, ABAJO = 180 - M;
    const casos = [
      ['Retrospectiva 10 Años del Acuerdo de Paz', 'Con la paz entre las manos'],
      ['Competencia Nacional de Cortometrajes', 'Una obra con título bastante largo de prueba'],
      ['Charla', 'El arte de moldear la IA'],
      ['Muestra', 'Ñandú y el poema gigante que baja'],
      ['Retrospectiva', 'Wwwwwwwwwwww Mmmmmmmmmm'],   // extremo sintético: palabra sin dónde partir
      ['Cortos', 'A'],
    ];
    return casos.map(([sec, tit]) => {
      const svg = decodeURIComponent(C._buildPosterV16({ accent:'#F59E0B', headerLabel:sec, title:tit, num:null, dato:'Charla · Bogotá' })
        .replace('data:image/svg+xml,', ''));
      const div = document.createElement('div'); div.innerHTML = svg;
      const el = div.querySelector('svg');
      el.style.cssText = 'position:absolute;width:120px'; document.body.appendChild(el);
      let der = 0, abajo = 0, n = 0;
      el.querySelectorAll('text').forEach(t => { const b = t.getBBox();
        der = Math.max(der, b.x + b.width); abajo = Math.max(abajo, b.y + b.height); n++; });
      el.remove();
      return { sec, der:+der.toFixed(1), abajo:+abajo.toFixed(1), n, DER, ABAJO };
    });
  });
  for (const c of r) {
    expect(c.n, `«${c.sec}» dibuja texto (si no, el test no probaría nada)`).toBeGreaterThan(1);
    expect(c.der, `«${c.sec}» no cruza el margen derecho`).toBeLessThanOrEqual(c.DER + 0.1);
    expect(c.abajo, `«${c.sec}» no cruza el margen inferior`).toBeLessThanOrEqual(c.ABAJO + 0.1);
  }
});

test('T99 — el texto del póster no se monta sobre la imagen, y la sección tiene color', async ({ page }) => {
  test.setTimeout(90000);
  await enterFestival(page, 'cineautopsia2026', '2026-08-25T10:00:00-05:00');
  await page.waitForTimeout(1000);
  // TODO explícito. Antes el test no lo pedía y funcionaba igual — pero solo
  // porque la detección de HOY estaba rota y la app caía siempre en TODO. Al
  // arreglarla, entra por el día 25 (una LISTA, no la grilla) y el test se
  // quedaba sin tarjetas que mirar: su propio guard lo cazó. Lo que T99 quiere
  // examinar es la grilla de pósters, así que la pide en voz alta.
  await page.click('.dtab[data-day="all"]');
  await page.waitForTimeout(600);
  await page.evaluate(() => { try { setProgramaView('grid'); } catch (e) {} });
  await page.waitForTimeout(800);
  const r = await page.evaluate(() => {
    return [...document.querySelectorAll('.poster-ed')].filter(e => e.offsetParent).map(ed => {
      const R = ed.getBoundingClientRect();
      const img = ed.querySelector('.ed-img')?.getBoundingClientRect();
      const ttl = ed.querySelector('.ed-title')?.getBoundingClientRect();
      const txt = ed.querySelector('.ed-hdr svg text');
      return {
        titulo: (ed.querySelector('.ed-title')?.textContent || '').slice(0, 24),
        // «montado sobre la imagen» = el título empieza ANTES de que el campo termine
        invade: !!(img && ttl && ttl.top < img.bottom - 0.5),
        // el pie tampoco puede desbordar la tarjeta por abajo
        seSale: !!(ttl && ttl.bottom > R.bottom + 0.5),
        fill: txt ? txt.getAttribute('fill') : null,
      };
    });
  });
  expect(r.length, 'hay tarjetas con marco editorial (si no, el test no prueba nada)').toBeGreaterThan(0);
  for (const c of r) {
    expect(c.invade, `«${c.titulo}» no se monta sobre la imagen`).toBe(false);
    expect(c.seSale, `«${c.titulo}» no se sale de la tarjeta`).toBe(false);
    if (c.fill !== null) {
      // fill="undefined" pintaba la sección de NEGRO sobre fondo oscuro: invisible
      expect(c.fill, 'la sección se pinta con un color de verdad').toMatch(/^(#[0-9A-Fa-f]{3,8}|var\(--[a-z-]+\))$/);
    }
  }
});

test('T100 — un día hueco del festival no manda «Hoy» a un día que ya pasó', async ({ page }) => {
  test.setTimeout(90000);
  // CineAutopsia va del 21 al 29 de agosto y NO programa el 24: un hueco EN MEDIO
  // del festival. Ese día `DAY_KEYS.findIndex(hoy)` da -1, y los fallbacks viejos
  // mandaban a los extremos del array — «Hoy» al primer día (ya pasado) y «Mañana»
  // al último. Cazado en producción el 24 ago 2026, con el festival en curso.
  await enterFestival(page, 'cineautopsia2026', '2026-08-24T10:00:00-05:00');
  await page.waitForTimeout(1200);

  const leer = async (rotulo) => {
    await page.evaluate((r) => {
      const p = [...document.querySelectorAll('.pmode-tab')]
        .find(x => new RegExp(r, 'i').test(x.textContent));
      if (p) p.click();
    }, rotulo);
    await page.waitForTimeout(900);
    return page.evaluate(() => ({
      dia: typeof activeDay !== 'undefined' ? activeDay : null,
      pasado: !!document.querySelector('.dtab.on')?.classList.contains('past'),
      // La grilla de TODO sigue en el DOM oculta; lo que importa es la superficie
      // VISIBLE del día. Medirlo con .poster-card contaba cards de otra vista.
      vacio: document.querySelectorAll('.plist-item').length === 0,
      motivo: (document.querySelector('#programa-list .empty-state, #programa-list .empty-state-hero')
        ?.textContent || '').replace(/\s+/g, ' ').trim(),
    }));
  };

  // El 24 EXISTE en el calendario aunque no tenga funciones (regla de Juan,
  // 24 ago 2026): un día vacío se declara, no se omite. Así «Hoy» significa hoy.
  const hoy = await leer('Hoy|Today');
  expect(hoy.pasado, '«Hoy» no puede abrir un día que ya pasó').toBe(false);
  expect(hoy.dia, '«Hoy» es HOY, aunque hoy no tenga funciones').toBe('2026-08-24');
  expect(hoy.vacio, 'el día vacío se muestra vacío, no se salta').toBe(true);
  // Y dice la verdad: sin filtros puestos, el vacío es del FESTIVAL, no del filtro.
  expect(hoy.motivo, 'el vacío no culpa a un filtro que nadie puso')
    .not.toMatch(/filtro|filter/i);
  // Ni ancla el mensaje a HOY: el vacío se pinta para el día que MIRÁS, y
  // Tercer Tiempo tiene dos días vacíos que no son hoy (14 y 19 jul). Decir
  // «hoy» ahí sería la misma afirmación sin comprobar (Juan, 24 ago 2026).
  expect(hoy.motivo, 'el vacío no dice «hoy»: vale para cualquier día')
    .not.toMatch(/\bhoy\b|\btoday\b|\bhoje\b/i);

  const manana = await leer('Mañana|Tomorrow');
  expect(manana.pasado, '«Mañana» tampoco abre un día pasado').toBe(false);
  expect(manana.dia, '«Mañana» es el día siguiente, no el final del festival').toBe('2026-08-25');
});

test.describe('T101 — canal #4 (sin SW: page.route no ve los fetches que pasan por el service worker)', () => {
  test.use({ serviceWorkers: 'block' });
test('T101 — la app abierta se entera del build nuevo, y no se recarga sola', async ({ page }) => {
  test.setTimeout(90000);
  // El canal #4 (poll en primer plano) existe para quien deja la app ABIERTA:
  // sin él, un cambio de sede u horario no llega hasta soltar el teléfono.
  // Doctrina T97 aplicada a la app entera: lo que estás mirando no cambia solo.
  // `?updPoll=400` acorta el ciclo (precedente: simTime).
  let servirNuevo = false;
  await page.route('**/version.json*', async (route) => {
    if (!servirNuevo) return route.continue();
    await route.fulfill({ contentType: 'application/json',
      body: JSON.stringify({ android: '299901010000', ios: '299901010000', storeGate: false }) });
  });
  await enterFestival(page, 'cineautopsia2026', '2026-08-25T10:00:00-05:00', { query: 'updPoll=400' });
  await page.waitForTimeout(1000);
  const urlAntes = page.url();

  // Aparece el build nuevo en el servidor…
  servirNuevo = true;
  await page.waitForTimeout(1600); // ≥2 ciclos de poll

  // …la app lo OFRECE (toast con acción) y NO navegó sola.
  const t1 = await page.evaluate(() => ({
    toast: document.getElementById('prio-toast')?.textContent.replace(/\s+/g, ' ').trim() || '',
    accion: !!document.querySelector('#prio-toast .toast-action-btn'),
  }));
  expect(page.url(), 'la app NO se recarga bajo los dedos del usuario').toBe(urlAntes);
  expect(t1.accion, 'ofrece la actualización con el toast de acción').toBe(true);
  expect(t1.toast.length, 'el toast dice algo').toBeGreaterThan(0);

  // Al aceptar, recarga con el cache-busting del build nuevo.
  await page.click('#prio-toast .toast-action-btn');
  await page.waitForURL(/v=299901010000/, { timeout: 8000 });
  expect(page.url()).toContain('v=299901010000');
});
});

test.describe('T102 — el wrapper iOS: SIN navigator.serviceWorker, los canales existen igual', () => {
test('T102 — sin API de service worker, el poll igual ofrece el build nuevo', async ({ page }) => {
  test.setTimeout(90000);
  // EL BUG QUE VIVIÓ JUAN (24 ago 2026): los 4 canales de version.json vivían
  // dentro de if('serviceWorker' in navigator). El wrapper iOS es WKWebView sin
  // WKAppBoundDomains → navigator.serviceWorker NO EXISTE → el bloque entero
  // nunca corría: iOS sin NINGÚN mecanismo de actualización (el palmarés de
  // FINCA no llegaba con la app en la mano). T101 no lo cazaba: el `block` de
  // Playwright bloquea el registro pero deja la API presente — el guard pasaba.
  // Acá se borra la API de verdad, como en el wrapper.
  await page.addInitScript(() => { delete Navigator.prototype.serviceWorker; });
  let servirNuevo = false;
  await page.route('**/version.json*', async (route) => {
    if (!servirNuevo) return route.continue();
    await route.fulfill({ contentType: 'application/json',
      body: JSON.stringify({ android: '299901010000', ios: '299901010000', storeGate: false }) });
  });
  await enterFestival(page, 'cineautopsia2026', '2026-08-25T10:00:00-05:00', { query: 'updPoll=400' });

  // Sanidad del harness: el entorno ES el del wrapper (sin la API).
  const sinSW = await page.evaluate(() => !('serviceWorker' in navigator));
  expect(sinSW, 'el harness debe simular el wrapper: sin navigator.serviceWorker').toBe(true);

  await page.waitForTimeout(1000);
  const urlAntes = page.url();
  servirNuevo = true;
  await page.waitForTimeout(1600); // ≥2 ciclos de poll

  const t1 = await page.evaluate(() => ({
    toast: document.getElementById('prio-toast')?.textContent.replace(/\s+/g, ' ').trim() || '',
    accion: !!document.querySelector('#prio-toast .toast-action-btn'),
  }));
  expect(page.url(), 'doctrina T97: tampoco acá se recarga sola').toBe(urlAntes);
  expect(t1.accion, 'sin SW, el canal #4 igual ofrece la actualización').toBe(true);
});
});

test.describe('T103/T104 — capa 2: los datos se refrescan en caliente (sin SW: page.route no ve fetches vía SW)', () => {
  test.use({ serviceWorkers: 'block' });

test('T103 — un cambio de sede aterriza EN SILENCIO, en su casilla, sin scroll ni toast', async ({ page }) => {
  test.setTimeout(90000);
  // Regla 1 de la capa 2 (aprobada con respaldo: marcadores deportivos /
  // tableros de aeropuerto): un VALOR que cambia dentro de su casilla se aplica
  // solo — el usuario espera ese dato vivo. Ni pill, ni recarga, ni salto.
  let mutar = false;
  await page.route('**/festivals/cineautopsia-2026.json*', async (route) => {
    if (!mutar) return route.continue();
    const res = await route.fetch();
    const j = await res.json();
    // A la OTRA sede real del día: la lista muestra nombres cortos («ASAB»,
    // «U. Nacional»), así que el cambio es visible y el venue existe en el mapa.
    j.films.forEach(f => { if (f.title === 'Mediometrajes Destacados del Mundo Entero 1') f.venue = 'Universidad Nacional - Bogotá'; });
    await route.fulfill({ contentType: 'application/json', body: JSON.stringify(j) });
  });
  await enterFestival(page, 'cineautopsia2026', '2026-08-25T10:00:00-05:00', { query: 'updPoll=400' });
  await expect(page.locator('#programa-list')).toContainText('ASAB', { timeout: 8000 });
  const urlAntes = page.url();
  const scrollAntes = await page.evaluate(() => window.scrollY);

  mutar = true;
  // La casilla de Mediometrajes 1 pasa de «ASAB» a «U. Nacional» — sola.
  await expect(page.locator('#programa-list')).not.toContainText('ASAB', { timeout: 8000 });
  await expect(page.locator('#programa-list')).toContainText('Mediometrajes Destacados del Mundo Entero 1');
  expect(page.url(), 'sin recarga: el documento es el mismo').toBe(urlAntes);
  expect(await page.evaluate(() => window.scrollY), 'sin salto de scroll').toBe(scrollAntes);
  const toast = await page.evaluate(() => document.getElementById('prio-toast')?.classList.contains('show') || false);
  expect(toast, 'regla 1 es silenciosa: un valor fresco no es una noticia').toBe(false);
  await page.unrouteAll({ behavior: 'ignoreErrors' });
});

test('T104 — una función nueva NO se inyecta bajo los dedos: se ofrece, y el tap la aplica', async ({ page }) => {
  test.setTimeout(90000);
  // Regla 2 (CLS / patrón «N posts nuevos»): estructura en pantalla visible se
  // OFRECE. La lista queda intacta hasta el tap.
  let mutar = false;
  await page.route('**/festivals/cineautopsia-2026.json*', async (route) => {
    if (!mutar) return route.continue();
    const res = await route.fetch();
    const j = await res.json();
    j.films.push({ title: 'Función Sorpresa de Medianoche', type: 'film', section: '🛰️ Apertura',
      duration: '80 min', day: '2026-08-25', time: '23:00',
      day_order: 4, venue: 'Universidad Nacional - Bogotá' });
    await route.fulfill({ contentType: 'application/json', body: JSON.stringify(j) });
  });
  await enterFestival(page, 'cineautopsia2026', '2026-08-25T10:00:00-05:00', { query: 'updPoll=400' });
  await expect(page.locator('#programa-list')).toContainText('Mediometrajes', { timeout: 8000 });

  mutar = true;
  // Aparece el pill…
  await expect(page.locator('#prio-toast .toast-action-btn')).toBeVisible({ timeout: 8000 });
  // …y la lista sigue INTACTA (nada se inyectó bajo los dedos).
  await expect(page.locator('#programa-list')).not.toContainText('Función Sorpresa');
  // El tap aplica: ahora sí, la función nueva existe en la lista.
  // Testigo de no-recarga: una recarga lo borraría del window.
  await page.evaluate(() => { window.__vivoT104 = 1; });
  await page.click('#prio-toast .toast-action-btn');
  await expect(page.locator('#programa-list')).toContainText('Función Sorpresa', { timeout: 8000 });
  expect(await page.evaluate(() => window.__vivoT104),
    'aplicar estructura no recarga el documento (el testigo sobrevive)').toBe(1);
  await page.unrouteAll({ behavior: 'ignoreErrors' });
});
});

test('T105 — la Forma B es de la misma familia que la A: negro de marca y luz de sección', async ({ page }) => {
  test.setTimeout(60000);
  // Juan, 24 ago 2026, sobre «Ver y escuchar» (Cinemancia): «tiene un estilo
  // diferente al que aprobamos para los stills 16:9». Eran DOS bugs, los dos de
  // la misma familia —la Forma B no recibió lo que la A sí—, y los dos solo se
  // ven EN PANTALLA (el dato y el markup estaban perfectos):
  //  1. SUELO: .poster-ed{background:var(--bg)} lo pisaba .bg-surf-2, que la card
  //     del grid también trae y que está definida ~1950 líneas más abajo con la
  //     MISMA especificidad. La Forma B se pintaba sobre #1B1917 mientras sus
  //     hermanas generativas usan #0B0A08 → al lado se veía más clara y plana.
  //     La Forma A nunca lo sufrió: su <img> SVG tapa el fondo del contenedor.
  //  2. LUZ: seguía ámbar fija aunque la Forma A ya hereda el acento de sección
  //     (24 ago) — una pared con las dos formas mezclaba ámbar entre colores.
  // Por eso este test MIDE estilos computados en vez de leer el CSS: un guardián
  // estático habría dado verde con el bug puesto, porque la regla correcta SÍ
  // existía — solo perdía la cascada.
  await enterFestival(page, 'cineautopsia2026', '2026-08-25T10:00:00-05:00');
  await page.evaluate(() => { activeDay = 'all'; programaViewMode = 'grid'; _renderProgramaContent(); });
  const ed = page.locator('.poster-ed').first();
  await expect(ed, 'CineAutopsia trae un póster editorial con still').toBeVisible({ timeout: 8000 });

  const med = await page.evaluate(() => {
    const n = document.querySelector('.poster-ed');
    const cs = getComputedStyle(n), af = getComputedStyle(n, '::after');
    const hex2rgb = h => { const v = h.trim().replace('#',''); return `rgb(${parseInt(v.slice(0,2),16)}, ${parseInt(v.slice(2,4),16)}, ${parseInt(v.slice(4,6),16)})`; };
    return {
      fondo: cs.backgroundColor,
      negroMarca: hex2rgb(getComputedStyle(document.documentElement).getPropertyValue('--bg')),
      surf2: hex2rgb(getComputedStyle(document.documentElement).getPropertyValue('--surf-2')),
      acento: hex2rgb(n.style.getPropertyValue('--ed-accent') || '#000000'),
      luz: af.backgroundImage || '',
    };
  });
  expect(med.fondo, 'el marco editorial pinta su propio suelo: negro de marca, no la superficie gris').toBe(med.negroMarca);
  expect(med.fondo, 'si sale surf-2, una clase utilitaria le ganó la cascada al builder').not.toBe(med.surf2);
  expect(med.luz, 'la luz hereda el acento de la sección, no un color fijo').toContain(med.acento);
});

test('T106 — la LISTA sirve la mini: una voz por chip, y el grid queda intacto', async ({ page }) => {
  test.setTimeout(60000);
  // Mejora 1 (auditoría Apple Music, aprobada 25 ago): en el chip de 56px el
  // póster entero era ruido de 3px que repetía la fila. La mini responde con UNA
  // voz — ordinal de serie o la marca de la obra. El GRID no cambia (Juan: la
  // marca en grande era «demasiado ruidosa»).
  await enterFestival(page, 'cineautopsia2026', '2026-08-25T10:00:00-05:00');
  // Lista de un día: los chips generativos NO llevan rótulo de sección
  await page.evaluate(() => { activeDay = DAY_KEYS[0]; programaViewMode = 'list'; _renderProgramaContent(); });
  const lista = await page.evaluate(() => {
    const out = [];
    document.querySelectorAll('.plist-item').forEach(li => {
      const img = li.querySelector('.plist-poster img');
      if (!img || !img.src.startsWith('data:image/svg')) return;
      const svg = decodeURIComponent(img.src.split(',')[1] || '');
      out.push({ t: li.dataset.title, textos: (svg.match(/<text/g) || []).length,
        conMarca: /circle|<path d=/.test(svg) });
    });
    return out;
  });
  expect(lista.length, 'el día 1 de CineAutopsia tiene chips generativos').toBeGreaterThan(0);
  for (const c of lista) {
    expect(c.textos, `${c.t}: la mini lleva a lo sumo UNA voz (ordinal) — el póster entero eran 4+`)
      .toBeLessThanOrEqual(1);
    expect(c.textos === 1 || c.conMarca, `${c.t}: sin ordinal, la marca es el diferenciador`).toBe(true);
  }
  // El GRID conserva el póster entero (rótulo de sección presente)
  await page.evaluate(() => { activeDay = 'all'; programaViewMode = 'grid'; _renderProgramaContent(); });
  const grid = await page.evaluate(() => {
    const img = [].slice.call(document.querySelectorAll('.poster-card img'))
      .find(i => i.src.startsWith('data:image/svg'));
    return img ? decodeURIComponent(img.src.split(',')[1] || '') : '';
  });
  expect((grid.match(/<text/g) || []).length, 'el grid queda tipográfico: sus voces intactas').toBeGreaterThanOrEqual(2);
});

test('T107 — la ciudad no se pega a la sede en la lista', async ({ page }) => {
  test.setTimeout(60000);
  // Juan, 25 ago, sobre Cinemancia: «¿por qué la ciudad está pegada totalmente
  // del venue?» — «Centro Colombo AmericanoMedellín». La ciudad pasó a vivir
  // DENTRO de la frase de sede el 18 ago (antes era display:block, línea propia
  // sin separador), y de los tres emisores solo dos recibieron el « · ». El de
  // la lista quedó pegando ciudad y sede en TODOS los festivales multiciudad.
  // Se mide en PANTALLA (textContent real), no en el markup: es donde se ve.
  await enterFestival(page, 'ficdeh2026', '2026-08-14T10:00:00-05:00');
  await page.evaluate(() => { activeDay = DAY_KEYS[0]; programaViewMode = 'list'; _renderProgramaContent(); });
  // Se lee el NODO DE TEXTO anterior al span, no la cadena entera: buscar la
  // ciudad con indexOf la encuentra dentro del propio nombre de la sede
  // («Centro Cultural Panóptico de Ibagué» · Ibagué) y el test acusaba en falso.
  const metas = await page.evaluate(() => [].slice.call(document.querySelectorAll('.plist-meta'))
    .filter(n => n.querySelector('.plist-city'))
    .map(n => {
      const span = n.querySelector('.plist-city');
      const prev = span.previousSibling;
      return {
        txt: n.textContent.replace(/\s+/g, ' '),
        antes: prev ? prev.textContent.trimEnd() : '',
      };
    }));
  expect(metas.length, 'FICDEH es multiciudad: sus filas muestran ciudad').toBeGreaterThan(0);
  for (const m of metas) {
    expect(m.antes.endsWith('·'),
      `«${m.txt}»: la ciudad debe ir separada de la sede por « · », no pegada`).toBe(true);
  }
});

test('T108 — la SEDE es parte de la identidad: agendar en una ciudad no marca la otra', async ({ page }) => {
  test.setTimeout(60000);
  // Bug MEDIDO EN PRODUCCIÓN (25 ago 2026, sin ninguna feature nueva): la
  // identidad de una entrada del Plan era título+día+hora, sin sede. FICDEH
  // programa la misma obra el mismo día y hora en ciudades distintas — 13 casos.
  // Agendar «La independencia» en Bogotá hacía que la app diera por planeada
  // la función de IBAGUÉ: a alguien de Ibagué le decía que ya tenía algo que
  // nunca agendó, y la que sí quería aparecía tomada.
  await enterFestival(page, 'ficdeh2026', '2026-08-12T09:00:00-05:00');
  const r = await page.evaluate(() => {
    // buscar en el catálogo REAL una colisión título+día+hora en dos sedes
    const porClave = {};
    FILMS.filter(f => f.day && f.time).forEach(f => {
      const k = f.title + '|' + f.day + '|' + f.time;
      (porClave[k] = porClave[k] || []).push(f);
    });
    const par = Object.values(porClave).find(v => new Set(v.map(x => x.venue)).size > 1);
    if (!par) return null;
    const [a, b] = par;
    addSuggestion(a.title, a.day, a.time);            // agendo SOLO la primera sede
    const sch = (state.get('savedAgenda') || {}).schedule || [];
    return {
      enPlan: sch.length,
      sedeGuardada: (sch[0] || {}).venue,
      sedeA: a.venue, sedeB: b.venue,
      // ¿la app cree que la de la OTRA sede también está planeada?
      otraMarcada: sch.some(s => sameEntry(s, b)),
    };
  });
  expect(r, 'FICDEH trae la misma obra el mismo día y hora en dos ciudades').not.toBeNull();
  expect(r.enPlan, 'se agendó una sola función').toBe(1);
  expect(r.sedeGuardada, 'y es la de la sede que se eligió').toBe(r.sedeA);
  expect(r.otraMarcada,
    `agendar en «${r.sedeA}» no puede marcar la función de «${r.sedeB}»`).toBe(false);
});

// ── T117 — el filtro de Prensa se lee como filtro, no como un botón mudo ─────
// Una usuaria pidió el filtro de Prensa e Industria para TIFF y no lo encontró
// (Juan, 26 ago 2026). Estaba al lado de Sección y Lugar pero era otro
// componente: un cuadrado de 26px con fondo y solo un icono, mientras sus dos
// hermanos son texto+icono sin fondo. La razón escrita era que «la barra a
// 390px no admite una cuarta etiqueta» — se midió y era falsa: con Hoy+Mañana
// visibles y todos los filtros, el espaciador deja 45px libres en español y 28
// en inglés a 390px, y 30/13 a 375px. La palabra cuesta 18-25px.
// El test mide la BARRA, no el CSS: que quepa es la mitad del requisito.
test('T117 — Prensa tiene etiqueta, anatomía de filtro, y la barra sigue cabiendo', async ({ page }) => {
  await enterFestival(page, 'tiff2026', '2026-09-12T14:00');
  for (const lang of ['es', 'en']) {
    const r = await page.evaluate((L) => {
      const tap = (a, ds) => { const b = document.createElement('button'); b.setAttribute('data-action', a);
        Object.keys(ds || {}).forEach(k => b.setAttribute('data-' + k, ds[k]));
        document.body.appendChild(b); b.click(); b.remove(); };
      tap('selectLang', { code: L });
      switchMainNav('mnav-cartelera');
      // el caso PEOR: los dos tabs de modo visibles a la vez
      const hoy = document.getElementById('pmode-hoy'), man = document.getElementById('pmode-manana');
      hoy.style.display = ''; man.style.display = '';
      const pb = document.getElementById('prensa-btn');
      const lbl = document.getElementById('prensa-lbl');
      const sec = document.getElementById('seccion-btn');
      const cs = pb && getComputedStyle(pb), cse = sec && getComputedStyle(sec);
      const sp = document.querySelector('.pmode-spacer');
      return {
        etiqueta: lbl && lbl.textContent.trim(),
        libre: sp ? Math.round(sp.getBoundingClientRect().width) : -1,
        // misma anatomía que su hermano Sección
        fondo: cs && cs.backgroundColor, borde: cs && cs.borderTopWidth,
        fuente: cs && cs.fontSize, fuenteHermano: cse && cse.fontSize,
        icono: pb && (() => { const s = pb.querySelector('svg'); return s ? s.getAttribute('width') : null; })(),
        iconoHermano: sec && (() => { const s = sec.querySelector('svg'); return s ? s.getAttribute('width') : null; })()
      };
    }, lang);
    expect(r.etiqueta, `hay etiqueta en ${lang}`).toBeTruthy();
    expect(r.etiqueta.length, `la etiqueta es corta en ${lang}`).toBeLessThanOrEqual(9);
    expect(r.libre, `la barra sigue cabiendo en ${lang}`).toBeGreaterThan(0);
    expect(r.fondo, `sin fondo propio en ${lang}`).toBe('rgba(0, 0, 0, 0)');
    expect(parseFloat(r.borde), `sin borde en ${lang}`).toBe(0);
    expect(r.fuente, `misma tipografía que Sección en ${lang}`).toBe(r.fuenteHermano);
    expect(Math.abs(+r.icono - +r.iconoHermano), `icono a la par de Sección en ${lang}`).toBeLessThanOrEqual(1);
  }
});

// ── T126 — el corazón de la LISTA tiene área de toque, como su hermano ───────
// El botón mide 26×26 y errarle abría la ficha: a ±14 px del centro
// elementFromPoint ya devolvía la fila. El expansor (::after con inset -14px)
// lo lleva a 54×54, sobre el mínimo de 44.
//
// Se sondea con elementFromPoint —la MISMA magnitud del diagnóstico—, no las
// propiedades CSS del ::after: un expansor puede existir en el estilo y no
// capturar nada (ancestro sin position, z-index, un sheet encima). La versión
// anterior de este test medía en la vista GRID —clickeaba el toggle, que sale
// de la lista— y leía estilos de un elemento oculto.
//
// El aserto de BORDE es la otra mitad: a ±30 px debe responder la ficha. Sin él,
// «arreglarlo» haciendo que toda la fila sea corazón pasaría el test y rompería
// el toque de abrir la obra.
test('T126 — el corazón de la lista llega al área de toque de sus hermanos', async ({ page }) => {
  await enterFestival(page, 'cinemancia2026', '2026-09-05T11:00:00-05:00');
  const r = await page.evaluate(async () => {
    const w = ms => new Promise(r => setTimeout(r, ms));
    const tap = a => { const b = document.createElement('button'); b.setAttribute('data-action', a);
      document.body.appendChild(b); b.click(); b.remove(); };
    // Cinemancia es multiciudad: el sheet de ciudad nace encima y se come las
    // sondas (es fixed, así que offsetParent no lo delata).
    tap('closeCitySheet');
    await w(600);
    switchMainNav('mnav-cartelera');
    await w(1400);
    const h = [...document.querySelectorAll('.plist-heart')].filter(e => e.getBoundingClientRect().width > 0)[0];
    if (!h) return { sinCorazon: true };
    const b = h.getBoundingClientRect();
    const cx = Math.round(b.left + b.width / 2), cy = Math.round(b.top + b.height / 2);
    const sonda = (dx, dy) => {
      const e = document.elementFromPoint(cx + dx, cy + dy);
      if (!e) return 'nada';
      if (e.closest('[data-action="toggleWLFromList"],.plist-heart')) return 'CORAZON';
      return e.closest('.js-open-pel') ? 'FICHA' : 'OTRO';
    };
    return {
      caja: Math.round(b.width),
      dentro: [sonda(-14, 0), sonda(14, 0), sonda(0, -14), sonda(0, 14)],
      borde: [sonda(-30, 0), sonda(0, -30)]
    };
  });
  if (r.sinCorazon) return;
  expect(r.caja, 'el botón sigue siendo el chico de 26 px').toBeLessThan(44);
  expect(r.dentro, 'a 14 px del centro responde el corazón, no la fila')
    .toEqual(['CORAZON', 'CORAZON', 'CORAZON', 'CORAZON']);
  expect(r.borde, 'y a 30 px ya es la fila: el expansor está acotado')
    .toEqual(['FICHA', 'FICHA']);
});

// ── T131 — el vacío de un día con SOLO la ciudad puesta no culpa a los filtros ──
// La ciudad es CONTEXTO (sobrevive al cambio de día por keepCityOnly), no un
// filtro que el usuario fue a buscar. En FICDEH, Medellín + MIÉ 12 no tiene
// programación y el vacío decía «Ajustá los filtros de sección o sede»: dos
// controles que el usuario nunca tocó y que no arreglan nada. Se mide el TEXTO
// pintado —la misma magnitud del diagnóstico—, no la rama que lo eligió.
test('T131 — el día vacío por ciudad nombra la ciudad, no filtros ajenos', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-12T10:00');
  const r = await page.evaluate(async () => {
    const w = ms => new Promise(r => setTimeout(r, ms));
    const tap = (a, ds) => { const b = document.createElement('button'); b.setAttribute('data-action', a);
      Object.keys(ds || {}).forEach(k => b.setAttribute('data-' + k, ds[k]));
      document.body.appendChild(b); b.click(); b.remove(); };
    tap('citySheetPick', { city: 'Medell\u00edn' });
    await w(700);
    switchMainNav('mnav-cartelera');
    await w(700);
    const out = { venue: String(activeVenue), sec: String(activeSec), txt: null };
    for (let i = 0; i < DAY_KEYS.length; i++) {
      globalThis.selectedIdx = i;
      if (typeof render === 'function') render();
      await w(240);
      const es = document.querySelector('.empty-state');
      if (es) { out.txt = es.innerText.replace(/\s+/g, ' ').trim(); break; }
    }
    return out;
  });
  expect(r.venue, 'la ciudad quedó puesta como selección de lugar').toContain('city:');
  expect(r.sec, 'y ninguna sección está filtrando').toBe('all');
  expect(r.txt, 'algún día de FICDEH queda vacío en esa ciudad').not.toBe(null);
  expect(r.txt, 'el vacío nombra la ciudad').toContain('Medell\u00edn');
  expect(r.txt, 'y NO manda a ajustar sección o sede').not.toMatch(/secci\u00f3n o sede/);
});

// ── T133 — el número de un filtro promete lo que vas a ver ───────────────────
// Contrato de Juan (7 ago, citado en sheets.js): «en el filtro el número dice
// vas a ver N si filtrás por esto — es la consecuencia de la acción». Los dos
// menús lo incumplían con unidades distintas: Sección deduplicaba por título
// (día 15 de FICDEH: decía 6, pintaba 8) y la fila de CIUDAD sumaba las de sus
// sedes, contando dos veces la obra proyectada en dos salas (decía 136 en modo
// «todas», pintaba 79). Se asserta número contra FILAS PINTADAS, que es la
// magnitud del contrato — no contra el dato del que sale el número.
test('T133 — el número del filtro de sección es el de las filas que pinta', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-15T09:00:00-05:00');
  const r = await page.evaluate(async () => {
    const w = ms => new Promise(r => setTimeout(r, ms));
    switchMainNav('mnav-cartelera');
    await w(1200);
    const vis = () => [...document.querySelectorAll('.plist-item,.poster-card')]
      .filter(e => e.offsetParent !== null).length;
    const b = document.getElementById('seccion-btn');
    if (!b) return { sinBoton: true };
    b.click(); await w(800);
    const ops = [...document.querySelectorAll('.filter-drop .lugar-opt')]
      .filter(o => o.querySelector('.lugar-cnt') && o.dataset.s && o.dataset.s !== 'all');
    if (!ops.length) return { sinOpciones: true };
    const dice = parseInt(ops[0].querySelector('.lugar-cnt').innerText, 10);
    ops[0].click(); await w(1300);
    const dd = FILMS.filter(f => f.day === activeDay && f.section === activeSec);
    return { dice, pinta: vis(), funciones: dd.length, obras: new Set(dd.map(f => f.title)).size };
  });
  if (r.sinBoton || r.sinOpciones) return;
  expect(r.funciones, 'la sección elegida repite algún título ese día — si no, el caso no distingue')
    .toBeGreaterThan(r.obras);
  expect(r.dice, 'el número dice lo que se va a pintar').toBe(r.pinta);
});

test('T133b — la fila de ciudad no cuenta dos veces la obra que va a dos salas', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-15T09:00:00-05:00');
  const r = await page.evaluate(async () => {
    const w = ms => new Promise(r => setTimeout(r, ms));
    switchMainNav('mnav-cartelera');
    await w(1200);
    const chipAll = document.querySelector('.dtab[data-day="all"]');
    if (chipAll) chipAll.click();
    await w(1400);
    const vis = () => [...document.querySelectorAll('.plist-item,.poster-card')]
      .filter(e => e.offsetParent !== null).length;
    const b = document.getElementById('lugar-btn');
    if (!b) return { sinBoton: true };
    b.click(); await w(800);
    const dr = [...document.querySelectorAll('.filter-drop .lugar-opt')]
      .find(o => (o.dataset.v || '').startsWith('drill:'));
    if (!dr) return { sinCiudades: true };          // festival de una sola ciudad
    const diceNivel1 = parseInt(dr.querySelector('.lugar-cnt').innerText, 10);
    dr.click(); await w(700);
    const cityRow = [...document.querySelectorAll('.filter-drop .lugar-opt')]
      .find(o => (o.dataset.v || '').startsWith('city:'));
    const diceNivel2 = parseInt(cityRow.querySelector('.lugar-cnt').innerText, 10);
    cityRow.click(); await w(1500);
    return { diceNivel1, diceNivel2, pinta: vis(), total: new Set(FILMS.map(f => f.title)).size };
  });
  if (r.sinBoton || r.sinCiudades) return;
  expect(r.diceNivel1, 'los dos niveles dicen lo mismo de la misma ciudad').toBe(r.diceNivel2);
  expect(r.diceNivel1, 'y ese número es el de las tarjetas que pinta').toBe(r.pinta);
  expect(r.pinta, 'la ciudad no puede tener más obras que el festival entero')
    .toBeLessThanOrEqual(r.total);
});

// ── T140 — la etiqueta de metadato no parte el título en dos ─────────────────
// «CON BOLETA» quedaba pegada a la PRIMERA línea de un título de dos, y se leía
// «El viento sabe que vuelvo [CON BOLETA] / a casa»: un título mal cortado antes
// que una etiqueta. No estaba dentro del texto —es hermana FLEX del bloque del
// título—, pero el align-items:flex-start del contenedor la anclaba arriba.
// Bajándola a la última línea termina la frase en vez de interrumpirla.
//
// Se mide la POSICIÓN de la etiqueta contra las líneas del título, que es la
// magnitud del hallazgo; el CSS puede decir align-self y aun así no aplicar
// (contenedor sin flex, especificidad, otro selector ganando).
test('T140 — con el título en dos líneas, la etiqueta va en la última', async ({ page }) => {
  await enterFestival(page, 'cinemancia2026', '2026-09-05T11:00:00-05:00');
  const r = await page.evaluate(async () => {
    const w = ms => new Promise(r => setTimeout(r, ms));
    const tap = a => { const b = document.createElement('button'); b.setAttribute('data-action', a);
      document.body.appendChild(b); b.click(); b.remove(); };
    tap('closeCitySheet');
    await w(600);
    switchMainNav('mnav-cartelera');
    await w(1500);
    const casos = [];
    document.querySelectorAll('.plist-title').forEach(fila => {
      const txt = fila.querySelector('.plist-title-txt');
      const badge = fila.querySelector('.meta-badge');
      if (!txt || !badge) return;
      const tb = txt.getBoundingClientRect(), bb = badge.getBoundingClientRect();
      const lh = parseFloat(getComputedStyle(txt).lineHeight) || 16;
      const lineas = Math.round(tb.height / lh);
      if (lineas < 2) return;                       // con una línea no hay dónde partirse
      casos.push({
        txt: txt.innerText.slice(0, 30), etiqueta: badge.innerText,
        lineas,
        // distancia del PIE de la etiqueta al pie del título: 0 = última línea
        alPie: Math.round(tb.bottom - bb.bottom),
        // distancia de su TECHO al techo del título: 0 = primera línea (el bug)
        alTecho: Math.round(bb.top - tb.top)
      });
    });
    return { casos };
  });
  if (!r.casos.length) return;                      // ningún título de 2 líneas con etiqueta
  for (const c of r.casos) {
    expect(c.alPie, `«${c.etiqueta}» en ${c.txt}: va con la última línea`).toBeLessThanOrEqual(4);
    expect(c.alTecho, `«${c.etiqueta}» en ${c.txt}: y NO junto a la primera`).toBeGreaterThan(4);
  }
});

// ── T141 — la fila que filtra la ciudad entera está en la columna, no fuera ──
// En el nivel 2 del filtro de Lugar («‹ Ciudades / Medellín 60 / 📍 sede / …»)
// la fila de la CIUDAD es la única sin icono: el pin es de las SEDES, y esa
// regla se queda. Pero sin nada en su lugar, su texto arrancaba 21px a la
// izquierda de todas las demás (63 contra 84) y colgaba fuera de la columna, así
// que se leía como el TÍTULO de la lista y no como la opción que es — y es la
// única forma de pedir «todo Medellín», el caso más común en un festival de área
// metropolitana.
//
// El reporte lo atribuía al color («las sedes llevan color más claro»): medido,
// las tres filas son el MISMO rgb(136,136,136). Era la sangría.
//
// Se comparan las posiciones ENTRE FILAS, no contra un número fijo: lo que no
// puede volver a pasar es que la ciudad quede desalineada de sus hermanas.
test('T141 — el rótulo de la ciudad se alinea con el de sus sedes', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-14T09:00:00-05:00');
  const r = await page.evaluate(async () => {
    const w = ms => new Promise(r => setTimeout(r, ms));
    const tap = a => { const b = document.createElement('button'); b.setAttribute('data-action', a);
      document.body.appendChild(b); b.click(); b.remove(); };
    tap('closeCitySheet');
    await w(600);
    switchMainNav('mnav-cartelera');
    await w(1300);
    const btn = document.querySelector('.lugar-btn');
    if (!btn) return { sinBoton: true };
    btn.click();
    await w(900);
    const dr = [...document.querySelectorAll('.filter-drop .lugar-opt')]
      .find(o => (o.dataset.v || '').startsWith('drill:'));
    if (!dr) return { sinDrill: true };            // festival de una sola ciudad
    dr.click();
    await w(700);
    // El rótulo es el primer span CON texto: el hueco es un span vacío y el
    // conteo va después (medirlo mal fue mi primer error acá).
    const rotulo = o => {
      const sp = [...o.querySelectorAll('span')]
        .find(x => x.textContent.trim() && !x.classList.contains('lugar-cnt'));
      return sp ? Math.round(sp.getBoundingClientRect().left) : null;
    };
    const filas = [...document.querySelectorAll('.filter-drop .lugar-opt')];
    const ciudad = filas.find(o => (o.dataset.v || '').startsWith('city:'));
    const sedes = filas.filter(o => (o.dataset.v || '').startsWith('sede:'));
    if (!ciudad || !sedes.length) return { sinNivel2: true };
    return {
      xCiudad: rotulo(ciudad),
      xSedes: [...new Set(sedes.map(rotulo))],
      colorCiudad: getComputedStyle(ciudad).color,
      colorSede: getComputedStyle(sedes[0]).color,
      pinCiudad: ciudad.querySelectorAll('svg').length,
      pinSede: sedes[0].querySelectorAll('svg').length
    };
  });
  if (r.sinBoton || r.sinDrill || r.sinNivel2) return;
  expect(r.xSedes.length, 'las sedes comparten una sola columna').toBe(1);
  expect(Math.abs(r.xCiudad - r.xSedes[0]), 'la ciudad está en esa misma columna')
    .toBeLessThanOrEqual(2);
  // Las dos mitades de la regla que se conserva: la ciudad NO lleva pin (es de
  // las sedes) y tampoco está más apagada — si alguien "arregla" la alineación
  // dándole un pin, esto lo caza.
  expect(r.pinSede, 'la sede sí lleva pin').toBeGreaterThan(0);
  expect(r.pinCiudad, 'y la ciudad no — el pin es de las sedes').toBe(0);
  expect(r.colorCiudad, 'ni está más apagada que ellas').toBe(r.colorSede);
});

// ── T142 — al encender Prensa te lleva a donde se ven los pases añadidos ─────
// El recorrido reportó que en la grilla el interruptor «no cambia nada»: 243
// cards antes y 243 después. Es cierto que no puede cambiarlas —la grilla es un
// catálogo de OBRAS, una tarjeta por obra, y ninguna obra existe SOLO en prensa
// (medido en TIFF: 247 funciones de prensa, 0 obras exclusivas)— así que un
// interruptor que se enciende sobre una pantalla quieta parece roto.
//
// La regla del 24 ago lo resolvió navegando: al ENCENDER desde una vista que no
// puede mostrarlos, salta a Lista y al primer día CON pases. Esa regla no tenía
// guardián: T117 cubre la anatomía del botón y T123 su papel como insumo del
// Plan, pero nadie vigilaba la navegación — quitarla devuelve el síntoma del
// reporte en silencio.
//
// La segunda mitad es igual de deliberada: al APAGAR no se mueve a nadie,
// porque un segundo salto sorprende más que quedarse. Sin ese aserto, «arreglar»
// esto navegando siempre pasaría el test.
test('T142 — Prensa ON salta a donde se ven los pases; OFF no mueve a nadie', async ({ page }) => {
  await enterFestival(page, 'tiff2026', '2026-09-09T10:00:00-04:00');
  const r = await page.evaluate(async () => {
    const w = ms => new Promise(r => setTimeout(r, ms));
    const tap = a => { const b = document.createElement('button'); b.setAttribute('data-action', a);
      document.body.appendChild(b); b.click(); b.remove(); };
    tap('closeCitySheet');
    await w(500);
    switchMainNav('mnav-cartelera');
    await w(1400);
    const chipAll = document.querySelector('.dtab[data-day="all"]');
    if (chipAll) chipAll.click();
    await w(1400);
    const snap = () => ({
      dia: String(activeDay),
      modo: typeof programaViewMode !== 'undefined' ? programaViewMode : '?',
      prensa: typeof showPress !== 'undefined' ? showPress : '?',
      filas: [...document.querySelectorAll('.plist-item')].filter(e => e.offsetParent !== null).length
    });
    const enGrilla = snap();
    const btn = document.querySelector('.prensa-btn');
    if (!btn) return { sinBoton: true };
    btn.click();
    await w(2000);
    const conPrensa = snap();
    // ¿el día al que saltó tiene pases de prensa de verdad?
    const diaTienePases = FILMS.some(f => f.audience === 'press' && f.day === activeDay);
    btn.click();
    await w(2000);
    const trasApagar = snap();
    return { enGrilla, conPrensa, trasApagar, diaTienePases };
  });
  if (r.sinBoton) return;                       // festival sin pases de prensa
  expect(r.enGrilla.modo, 'se parte de la grilla de todas').toBe('grid');
  expect(r.enGrilla.dia, 'y de «todos los días»').toBe('all');
  // ENCENDER: lleva a donde lo añadido se ve
  expect(r.conPrensa.prensa, 'el interruptor quedó encendido').toBe(true);
  expect(r.conPrensa.modo, 'y la vista pasa a Lista, donde la unidad es la función').toBe('list');
  expect(r.conPrensa.dia, 'sobre un día concreto, no «todas»').not.toBe('all');
  expect(r.diaTienePases, 'y ese día TIENE pases de prensa').toBe(true);
  expect(r.conPrensa.filas, 'con funciones en pantalla').toBeGreaterThan(0);
  // APAGAR: no mueve a nadie
  expect(r.trasApagar.prensa, 'el interruptor quedó apagado').toBe(false);
  expect(r.trasApagar.dia, 'apagar NO devuelve a nadie a otro día').toBe(r.conPrensa.dia);
  expect(r.trasApagar.modo, 'ni a otra vista').toBe(r.conPrensa.modo);
});

// ── T145 — los rótulos de la barra se leen sobre pósters claros ──────────────
// La barra es vidrio: rgba(14,13,12,.55) + blur(28px). Deja pasar LUZ, no texto
// —el blur impide leer nada detrás—, pero con pósters claros el fondo efectivo
// sube y el rótulo inactivo #888 caía a 3,65:1, bajo el 4,5:1 que WCAG AA pide
// para 11px. En Cinemancia (pósters oscuros) el mismo gris daba 5,52:1: el
// defecto dependía del festival.
//
// La salida NO fue opacar el vidrio —lo prohíbe [chrome-glass], alpha ≤0,6,
// decisión del 18 jul— sino aclarar el RÓTULO a --white-60, ya en la paleta.
//
// EL FONDO ES UNA CONSTANTE MEDIDA, y hay que decirlo: rgb(52,49,44) es el
// píxel real de la barra en TIFF con scrollTop 1800, el más claro que encontré
// barriendo dos festivales × cuatro posiciones. No se puede leer en vivo desde
// la página —lo que compone backdrop-filter no es accesible al DOM— y el peor
// teórico (un póster blanco puro bajo el velo, rgb(122,122,121)) no ocurre:
// el blur de 28px promedia un área grande. El test vigila lo que cambiamos —el
// color del RÓTULO— contra ese suelo, y que el velo siga siendo vidrio.
const _FONDO_MAS_CLARO_MEDIDO = [52, 49, 44];   // TIFF · scrollTop 1800 · 1 sep 2026

test('T145 — el rótulo inactivo de la barra cumple AA sobre pósters claros', async ({ page }) => {
  await enterFestival(page, 'tiff2026', '2026-09-09T10:00:00-04:00');
  const r = await page.evaluate(async (fondo) => {
    const w = ms => new Promise(r => setTimeout(r, ms));
    const tap = a => { const b = document.createElement('button'); b.setAttribute('data-action', a);
      document.body.appendChild(b); b.click(); b.remove(); };
    tap('closeCitySheet');
    await w(600);
    switchMainNav('mnav-cartelera');
    await w(1200);
    const nav = document.querySelector('.main-nav');
    const tab = [...document.querySelectorAll('.main-nav-tab')].find(t => !t.classList.contains('on'));
    if (!nav || !tab) return { sinBarra: true };
    const nums = s => (s.match(/[\d.]+/g) || []).map(Number);
    const csN = getComputedStyle(nav), csT = getComputedStyle(tab);
    const nN = nums(csN.backgroundColor), nT = nums(csT.color);
    const alfaVelo = nN.length > 3 ? nN[3] : 1;
    const aT = nT.length > 3 ? nT[3] : 1;
    const txtEf = nT.slice(0, 3).map((c, i) => Math.round(aT * c + (1 - aT) * fondo[i]));
    const lin = c => { c /= 255; return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
    const L = ([a, b, c]) => 0.2126 * lin(a) + 0.7152 * lin(b) + 0.0722 * lin(c);
    const l1 = L(txtEf), l2 = L(fondo);
    return { contraste: +(((Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05)).toFixed(2)),
      alfaVelo, blur: csN.backdropFilter || csN.webkitBackdropFilter,
      colorTexto: csT.color, fs: parseFloat(csT.fontSize) };
  }, _FONDO_MAS_CLARO_MEDIDO);
  if (r.sinBarra) return;
  expect(r.alfaVelo, 'la barra sigue siendo vidrio, no muro ([chrome-glass])').toBeLessThanOrEqual(0.6);
  expect(r.blur, 'y conserva su desenfoque').toMatch(/blur/);
  expect(r.fs, 'el rótulo es texto pequeño: le aplica el 4,5:1').toBeLessThan(18);
  expect(r.contraste,
    `sobre el fondo más claro medido (${_FONDO_MAS_CLARO_MEDIDO}) el rótulo ${r.colorTexto} cumple AA`)
    .toBeGreaterThanOrEqual(4.5);
});

// ── T146 — el dropdown avisa que hay más, sin comerse la última opción ───────
// El panel se corta donde llega su max-height y eso caía a MEDIA LETRA: medido
// en Sección (max-height 464,2 · scrollHeight 660), la fila 11 quedaba con 23 de
// sus 44px — 53% — y se leía como error de render.
//
// La máscara NO puede ser fija: al final de la lista se come la última opción
// («Función de clausura» quedaba a 1px de la base, dentro del degradado), que es
// peor que el corte. Por eso la clase se enciende SOLO mientras queda algo abajo.
//
// Las dos mitades van juntas a propósito: la primera sola se «arregla» con una
// máscara fija, y la segunda lo impide.
//
// FIXTURE — se mide sobre ficci65 y NO sobre un festival vivo. El test estaba
// apuntado a cinemancia2026 y se volvió mudo sin avisar: su lista de Sección
// bajó a 8 opciones (352px) y dejó de tocar el tope de 464,2 — sin desborde no
// hay máscara que medir, así que salía verde probando nada (medido 4 sep 2026).
// ficci65 está archivado (su dato ya no cambia) y desborda con margen amplio:
// 22 opciones, 968px contra los mismos 464,2. Y si aun así dejara de desbordar,
// abajo se cae en vez de callarse.
test('T146 — el pie del dropdown se desvanece solo mientras queda lista', async ({ page }) => {
  await enterFestival(page, 'ficci65');
  const r = await page.evaluate(async () => {
    const w = ms => new Promise(r => setTimeout(r, ms));
    const tap = a => { const b = document.createElement('button'); b.setAttribute('data-action', a);
      document.body.appendChild(b); b.click(); b.remove(); };
    tap('closeCitySheet');
    await w(600);
    switchMainNav('mnav-cartelera');
    await w(1400);
    const btn = document.getElementById('seccion-btn');
    if (!btn) return { sinBoton: true };
    btn.click();
    await w(800);
    const d = document.querySelector('.filter-drop');
    if (!d || d.scrollHeight <= d.clientHeight + 4) return { noScrollea: true };
    const arriba = { clase: d.classList.contains('hay-mas'), mask: getComputedStyle(d).maskImage || getComputedStyle(d).webkitMaskImage };
    d.scrollTop = d.scrollHeight;
    d.dispatchEvent(new Event('scroll'));
    await w(400);
    const abajo = { clase: d.classList.contains('hay-mas'), mask: getComputedStyle(d).maskImage || getComputedStyle(d).webkitMaskImage };
    // ¿la última opción queda dentro de la zona de desvanecido?
    const ult = [...d.querySelectorAll('.lugar-opt')].pop();
    const db = d.getBoundingClientRect(), ub = ult.getBoundingClientRect();
    return { arriba, abajo, pieUltimaALaBase: Math.round(db.bottom - ub.bottom) };
  });
  // Estas dos NO son escapes: son la premisa del test. Cuando no se cumplen no
  // hay nada que medir, y eso tiene que sonar — antes eran un `return` mudo.
  expect(r.sinBoton, 'el filtro de Sección existe en este festival').toBeUndefined();
  expect(r.noScrollea, 'y su lista desborda el panel: sin desborde no hay máscara que probar').toBeUndefined();
  expect(r.arriba.clase, 'con lista por debajo, el pie se desvanece').toBe(true);
  expect(r.arriba.mask, 'y la máscara aplica de verdad, no solo la clase').toMatch(/gradient/);
  expect(r.abajo.clase, 'al final de la lista la clase se retira').toBe(false);
  // Y la MÁSCARA con ella: comprobar solo la clase deja pasar una regla fija
  // sobre .filter-drop, que es exactamente el modo de fallo documentado arriba
  // (lo cacé mutando: con la máscara sin condicionar, el test pasaba).
  expect(r.abajo.mask, 'y con ella el degradado — si no, la última opción se desvanece').toBe('none');
  expect(r.pieUltimaALaBase, 'porque la última opción está pegada a la base — con máscara sería ilegible')
    .toBeLessThan(24);
});

// ── T149 — la pregunta de apertura marca la ciudad cuya programación cayó ────
// FICDEH tras el sismo: de once ciudades, CUATRO tienen el 100% de sus funciones
// caídas (Pereira 0/29, Manizales 0/26, Cali 0/17, Quibdó 0/16) y se ofrecían
// con la misma clase, el mismo color y la misma opacidad que las siete vivas.
// El destino sí avisa —el banner explica con las palabras del festival—, pero
// el aviso llegaba DESPUÉS de elegir.
//
// El test mide las DOS superficies en la misma corrida a propósito: la hoja de
// apertura y el nivel de ciudades del filtro de Lugar leen el mismo dueño
// (festivalCities). Marcar una sola las pondría a decir cosas distintas de la
// misma ciudad, que es peor que no marcar ninguna.
test('T149 — la ciudad sin programación viva se marca en las dos superficies', async ({ page }) => {
  // El reloj va DENTRO del festival y la hoja se abre después: es la fase en la
  // que esta pregunta existe. Un festival terminado ya no la hace (T177).
  await enterFestival(page, 'ficdeh2026', '2026-08-16T10:00:00-05:00');
  await abrirHojaCiudad(page);
  await page.waitForTimeout(1200);
  const r = await page.evaluate(async () => {
    const w = ms => new Promise(r => setTimeout(r, ms));
    const H = await import('/src/view/helpers.js');
    // oráculo independiente: la ciudad cae si NINGUNA de sus funciones sobrevive
    const viva = {};
    FILMS.forEach(f => {
      const c = H.venueCity(f.venue); if (!c || !f.day) return;
      viva[c] = viva[c] || 0; if (!f._cancelled) viva[c]++;
    });
    const caidasReales = Object.keys(viva).filter(c => viva[c] === 0).sort();
    const vivasReales = Object.keys(viva).filter(c => viva[c] > 0).sort();

    const filas = [...document.querySelectorAll('#city-sheet-list .lugar-opt.city')];
    const hoja = { marcadas: [], sinMarca: [], texto: null, cortado: false };
    filas.forEach(e => {
      const m = e.querySelector('.lugar-canc');
      const n = e.querySelector('span:not(.lugar-canc)');
      if (m) { hoja.marcadas.push(e.dataset.city); hoja.texto = m.innerText.trim(); }
      else hoja.sinMarca.push(e.dataset.city);
      if (n && n.scrollWidth > n.clientWidth + 1) hoja.cortado = true;
    });
    hoja.marcadas.sort(); hoja.sinMarca.sort();

    // ── el filtro de Lugar, la otra cara del mismo dueño ──
    const tap = a => { const b = document.createElement('button'); b.setAttribute('data-action', a);
      document.body.appendChild(b); b.click(); b.remove(); };
    tap('closeCitySheet'); await w(700);
    const lb = document.getElementById('lugar-btn');
    if (!lb) return { hoja, caidasReales, vivasReales, sinFiltro: true };
    lb.click(); await w(800);
    const d = document.querySelector('.filter-drop');
    const filtro = { marcadas: [], sinMarca: [] };
    [...d.querySelectorAll('.lugar-opt')].forEach(e => {
      const v = e.dataset.v || '';
      if (!v.startsWith('drill:')) return;
      const c = v.slice(6);
      (e.querySelector('.lugar-canc') ? filtro.marcadas : filtro.sinMarca).push(c);
    });
    filtro.marcadas.sort(); filtro.sinMarca.sort();
    return { hoja, filtro, caidasReales, vivasReales };
  });

  // 1 · la hoja marca EXACTAMENTE las caídas, y ninguna viva
  expect(r.caidasReales.length, 'el fixture tiene que traer ciudades caídas o el test no mide nada')
    .toBeGreaterThan(0);
  expect(r.hoja.marcadas, 'la hoja marca las ciudades sin una sola función viva')
    .toEqual(r.caidasReales);
  expect(r.hoja.sinMarca, 'y no marca ninguna de las vivas').toEqual(r.vivasReales);

  // 2 · con la MISMA palabra que el banner del destino — sin copy nuevo
  expect(r.hoja.texto, 'la marca dice lo mismo que el rótulo del banner al que lleva')
    .toBe('CANCELADA');

  // 3 · el nombre de la ciudad sigue entero: la marca no se lo come
  expect(r.hoja.cortado, 'la marca no recorta el nombre de la ciudad').toBe(false);

  // 4 · y el filtro de Lugar dice LO MISMO — dos superficies, un dueño
  // La otra mitad no se salta en silencio: si el filtro de Lugar no está, las
  // dos superficies dejan de compararse y el test se queda a medias sin decirlo.
  expect(r.sinFiltro, 'el filtro de Lugar existe: es la otra superficie que este test compara').toBeUndefined();
  {
    expect(r.filtro.marcadas, 'el filtro de Lugar marca las mismas que la hoja de apertura')
      .toEqual(r.hoja.marcadas);
    expect(r.filtro.sinMarca, 'y deja sin marcar las mismas').toEqual(r.hoja.sinMarca);
  }
});

// ── T153 — con un taller en la cuenta, Planear no dice «obras» ──────────────
// «actividad» es el PARAGUAS y un taller no es una obra (regla de vocabulario).
// El titular de Mi Plan ya elegía el sustantivo por el contenido y T132b lo
// vigilaba, pero las dos líneas de Planear se habían quedado afuera: medido en
// FICDEH con «Los frutos que dan vida» —taller de dos sesiones— más una
// película, decían «2 obras» sobre 1 película y 1 taller. El NÚMERO estaba bien
// (2 obras, 3 citas); el sustantivo no.
//
// La segunda mitad es la que impide arreglar de más: sin taller las dos líneas
// tienen que seguir diciendo «obras», que es más específico y sigue siendo
// verdad. Un cambio a «actividades» siempre pasaría la primera mitad sola.
test('T153 — el sustantivo de Planear sigue al contenido, no a la pantalla', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-12T09:00:00-05:00');
  const leer = async (conTaller) => {
    await page.evaluate(async (ev) => {
      const w = ms => new Promise(r => setTimeout(r, ms));
      const b = document.createElement('button');
      b.setAttribute('data-action', 'closeCitySheet');
      document.body.appendChild(b); b.click(); b.remove();
      await w(400);
      watchlist.clear(); prioritized.clear();
      savedAgenda = null; cachedResult = null;
      const pelis = FILMS.filter(f => f.type !== 'event' && !f._cancelled && f.day && f.time);
      if (ev) {
        const t = FILMS.find(f => f.is_recurring);
        watchlist.add(t.title); watchlist.add(pelis[0].title);
      } else {
        watchlist.add(pelis[0].title); watchlist.add(pelis[1].title);
      }
      if (typeof saveState === 'function') saveState('wl', 'watched');
    }, conTaller);
    await goToPlanear(page);
    await esperarCalculo(page);
    await page.waitForTimeout(1000);
    return page.evaluate(() => {
      const vis = e => { const b = e.getBoundingClientRect(); return b.width > 0 && b.height > 0; };
      const uno = sel => [...document.querySelectorAll(sel)].filter(vis)
        .map(e => e.innerText.replace(/\s+/g, ' ').trim())[0] || '';
      return { insumo: uno('#ag-view .dato-linea'), resultado: uno('#ag-view .dato-resultado') };
    });
  };

  // 1 · con un taller adentro, ninguna de las dos líneas puede decir «obra»
  const conT = await leer(true);
  expect(conT.insumo, 'la línea de insumo se pintó').toBeTruthy();
  expect(conT.resultado, 'la línea de resultado se pintó').toBeTruthy();
  expect(conT.insumo, 'con un taller en la cuenta, el insumo no lo llama obra')
    .not.toMatch(/\bobras?\b/i);
  expect(conT.insumo, 'usa el paraguas').toMatch(/\bactividad(es)?\b/i);
  expect(conT.resultado, 'y el resultado tampoco lo llama obra').not.toMatch(/\bobras?\b/i);
  expect(conT.resultado, 'usa el paraguas').toMatch(/\bactividad(es)?\b/i);
  // el número no cambia: son 2 cosas, aunque el taller traiga 2 sesiones
  expect(conT.insumo, 'y sigue contando 2 — el taller de dos sesiones es UNA').toMatch(/\b2\b/);

  // 2 · sin taller, «obras» sobrevive: es más específico y sigue siendo verdad
  const sinT = await leer(false);
  expect(sinT.insumo, 'sin taller el insumo vuelve a la palabra específica')
    .toMatch(/\bobras?\b/i);
  expect(sinT.resultado, 'y el resultado también').toMatch(/\bobras?\b/i);
});

// ── T157 — las salidas «Cancelar» se alcanzan con el teclado ────────────────
// `.auth-cancel` eran los ÚNICOS `<span data-action>` de todo el index: cinco
// salidas «Cancelar» —los tres pasos de la hoja de cuenta, la de reseña y la
// del nombre al compartir— que ningún teclado podía alcanzar.
//
// Y estaban en la MISMA regla CSS que `.conflict-btn-cancel` y
// `.prio-limit-cancel`, que es un reset de botón (background:none, border:none,
// cursor:pointer) y cuyas otras dos clases ya eran `<button>`. La etiqueta era
// lo único que faltaba; el anillo de foco ya existía
// (`:focus-visible{outline:2px solid var(--amber)}`).
//
// Se afirman las tres cosas que hacen falta para poder usarla sin mouse:
// alcanzable, con foco VISIBLE, y que Enter la opere. Una de las tres sola no
// sirve de nada.
test('T157 — Cancelar es alcanzable, se ve enfocada y responde a Enter', async ({ page }) => {
  await enterFestival(page, 'cinemancia2026', '2026-09-04T10:00:00-05:00');
  await page.evaluate(() => {
    const b = document.createElement('button');
    b.setAttribute('data-action', 'closeCitySheet');
    document.body.appendChild(b); b.click(); b.remove();
  });
  await page.waitForTimeout(700);
  await page.evaluate(() => {
    const b = document.createElement('button');
    b.setAttribute('data-action', 'openAuthSheet');
    document.body.appendChild(b); b.click(); b.remove();
  });
  await page.waitForTimeout(1200);

  // 1 · TODAS las salidas de la app son alcanzables, incluidas las de los pasos
  //     que ahora mismo están ocultos
  const todas = await page.evaluate(() => {
    const out = [...document.querySelectorAll('.auth-cancel')].map(e => ({
      tag: e.tagName, tab: e.tabIndex
    }));
    return { n: out.length, inalcanzables: out.filter(o => !(o.tab >= 0)),
      spansConAccion: document.querySelectorAll('span[data-action]').length };
  });
  expect(todas.n, 'la hoja de cuenta trae sus salidas').toBeGreaterThan(0);
  expect(todas.inalcanzables,
    'ninguna salida «Cancelar» puede quedar fuera del recorrido del teclado').toEqual([]);
  expect(todas.spansConAccion,
    'y no queda ningún <span> haciendo de botón, que es como empezó esto').toBe(0);

  // 2 · llegar con Tab de verdad: :focus-visible solo se arma con el teclado
  await page.evaluate(() => { const i = document.getElementById('auth-email-inp'); if (i) i.focus(); });
  await page.keyboard.press('Tab');
  await page.keyboard.press('Tab');
  await page.waitForTimeout(300);
  const foco = await page.evaluate(() => {
    const a = document.activeElement;
    return { esCancelar: a.classList.contains('auth-cancel'),
      visible: (() => { try { return a.matches(':focus-visible'); } catch (e) { return null; } })() };
  });
  expect(foco.esCancelar, 'tabulando desde el campo se llega a Cancelar').toBe(true);
  expect(foco.visible, 'y el foco se VE — un foco invisible no sirve de nada').toBe(true);

  // 3 · y Enter la opera
  await page.keyboard.press('Enter');
  await page.waitForTimeout(900);
  const cerrada = await page.evaluate(() => {
    const sh = document.getElementById('auth-sheet');
    return !sh || !sh.classList.contains('open');
  });
  expect(cerrada, 'Enter cierra la hoja: es un botón de verdad, no un span con onclick').toBe(true);
});

// ── T158 — un corto dentro de una charla no sigue «En curso» cuando la charla terminó ──
// FICDEH, 17 AGO, Cinemateca Sala 2 a las 16:00: dos cortos (18 y 14 min) y una
// charla de 180 que los proyecta adentro. El bloque sumaba 212 y los cortos
// quedaban «En curso» hasta las 19:32, tres horas y media después de terminar,
// mientras el bloque real terminó a las 19:00 (auditoría B-2, 2 sep 2026).
//
// Se afirma sobre lo PINTADO —el punto verde y su aria— en dos instantes: a las
// 18:50 sigue en curso (la charla no terminó: el anclaje es correcto), a las
// 19:30 ya no. Con la suma vieja el segundo instante falla; sin anclaje el
// primero — las dos mitades se sostienen mutuamente.
// El reloj del navegador se CONGELA (page.clock): «en curso» lee la hora del
// navegador, y con solo _simTime esta medición no reproducía.
test('T158 — el punto verde de un corto se apaga cuando termina la charla que lo contiene', async ({ page }) => {
  const leer = async (iso) => {
    try { await page.clock.setFixedTime(new Date(iso)); } catch (e) {}
    await page.evaluate(t => { _simTime = t; activeDay = '2026-08-17'; programaViewMode = 'list';
      _renderProgramaContent && _renderProgramaContent(); }, iso);
    await page.waitForTimeout(1200);
    return page.evaluate(() => {
      const vis = e => { const b = e.getBoundingClientRect(); return b.width > 0 && b.height > 0; };
      const fila = [...document.querySelectorAll('.plist-item')].filter(vis).find(e => e.innerText.includes('Los pliegues de la falda'));
      if (!fila) return null;
      const dot = fila.querySelector('.live-dot,.row-dot');
      return { enCurso: !!dot, aria: dot ? dot.getAttribute('aria-label') : null, opacity: getComputedStyle(fila).opacity };
    });
  };
  await enterFestival(page, 'ficdeh2026', '2026-08-17T18:50:00-05:00');
  await page.evaluate(() => { const f = [...document.querySelectorAll('#city-sheet-list .lugar-opt')].find(e => e.dataset.city === 'Bogotá'); if (f) f.click(); });
  await page.waitForTimeout(1400);

  const antes = await leer('2026-08-17T18:50:00-05:00');
  expect(antes, 'la fila del corto se pintó').not.toBeNull();
  expect(antes.enCurso, 'a las 18:50 la charla que lo contiene sigue: el corto está EN CURSO — es el anclaje, y es correcto')
    .toBe(true);

  const despues = await leer('2026-08-17T19:30:00-05:00');
  expect(despues, 'la fila del corto se pintó').not.toBeNull();
  expect(despues.enCurso, 'a las 19:30 la charla terminó (16:00 + 180): el punto verde se apaga')
    .toBe(false);
  expect(parseFloat(despues.opacity), 'y la fila pasa a atenuada, como toda función pasada')
    .toBeLessThan(0.9);
});

// ── T160 — el día de hoy no se atenúa mientras su última función sigue ───────
// Auditoría B-4 (2 sep 2026): 17 AGO 19:30, Bogotá. «El juego de la vida»
// (19:00, 95 min) corre hasta las 20:35 y la cabecera dice «En curso · Termina
// en 1 h 05» — pero la pestaña LUN 17 salía `past` a opacity .35 (2,04:1),
// porque dayFullyPassed tomaba el último INICIO más 10 minutos.
//
// Dos instantes, y el segundo impide arreglar de más: a las 19:30 el día está
// vivo; a las 21:00 (la última terminó 20:35) ya pasó y se atenúa. El reloj del
// navegador se congela (page.clock): esta medición no reproducía con _simTime
// solo, y así fue como la primera verificación la dio por falsa.
test('T160 — LUN 17 sigue encendido a las 19:30 con su última función en curso, y pasado a las 21:00', async ({ page }) => {
  // Cada instante ENTRA a la app de nuevo: la clase `past` de las pestañas se
  // decide al construirlas (pipeline/loader), no en cada render, así que mover
  // el reloj con la app abierta no la recalcula — y eso es lo que hace un
  // usuario que abre la app a esa hora. La primera versión de este test movía
  // _simTime en caliente y fallaba con el dominio SANO: medía el arnés.
  const tab = async (iso) => {
    await enterFestival(page, 'ficdeh2026', iso);
    try { await page.clock.setFixedTime(new Date(iso)); } catch (e) {}
    await page.evaluate(() => { const f = [...document.querySelectorAll('#city-sheet-list .lugar-opt')].find(e => e.dataset.city === 'Bogotá'); if (f) f.click(); });
    await page.waitForTimeout(1400);
    return page.evaluate(() => {
      const t = [...document.querySelectorAll('.dtab')].find(e => (e.dataset.day || e.getAttribute('data-day')) === '2026-08-17');
      if (!t) return null;
      const bog = FILMS.filter(f => f.day === '2026-08-17' && f.time && !f._cancelled && /Bogot/.test(f.venue || ''));
      const u = bog.sort((a, b) => a.time.localeCompare(b.time)).pop();
      return { past: t.classList.contains('past'), opacity: parseFloat(getComputedStyle(t).opacity), ultima: u ? u.time + ' · ' + u.duration : null };
    });
  };
  const vivo = await tab('2026-08-17T19:30:00-05:00');
  expect(vivo, 'la pestaña del 17 se pintó').not.toBeNull();
  expect(vivo.ultima, 'el fixture: la última de Bogotá empieza a las 19:00 y dura 95 — el caso medido').toBe('19:00 · 95 min');
  expect(vivo.past, 'a las 19:30 la última función sigue: el día NO es pasado').toBe(false);
  expect(vivo.opacity, 'y no se atenúa — es el día que estás viviendo').toBeGreaterThan(0.9);

  const pasado = await tab('2026-08-17T21:00:00-05:00');
  expect(pasado.past, 'a las 21:00 la última terminó (19:00 + 95 = 20:35): el día pasó').toBe(true);
  expect(pasado.opacity, 'y se atenúa como todo día pasado').toBeLessThan(0.5);
});
// ── T164 — el panel de filtro no deja aire sin usar mientras corta nombres ──
// Auditoría A-6 (2 sep 2026): en Sección con TODO el panel quedaba de x=8 a
// x=308 en un viewport de 390 —82px sin usar— y 4 de 15 secciones salían
// cortadas, la peor perdiendo el 45% de su nombre («🌷 La primavera llega para
// los que esperan…», 453px de texto en 251 de caja).
//
// La causa no era el tope sino CUÁNDO se mide: _dropRight se llamaba antes de
// que el panel tuviera contenido, así que espejaba el máximo (300) y posicionaba
// por el peor caso. Con el ancho real, el panel ancho usa la pantalla y el
// angosto queda pegado a su botón.
//
// Las dos mitades: si algo se corta, no puede sobrar espacio; si nada se corta,
// el panel sigue anclado a su botón. Una sola de las dos se «arregla» sola.
test('T164 — el panel usa el ancho que necesita, y no más', async ({ page }) => {
  const abrir = async (todo) => {
    await page.evaluate(t => {
      const b = document.createElement('button'); b.setAttribute('data-action', 'closeCitySheet');
      document.body.appendChild(b); b.click(); b.remove();
      if (t) { activeDay = 'all'; programaViewMode = 'grid'; _renderProgramaContent && _renderProgramaContent(); }
    }, todo);
    await page.waitForTimeout(1200);
    return page.evaluate(async () => {
      document.querySelector('.filter-drop')?.remove();
      document.getElementById('seccion-btn').click();
      await new Promise(r => setTimeout(r, 800));
      const d = document.querySelector('.filter-drop'); if (!d) return null;
      const dr = d.getBoundingClientRect();
      const btn = document.getElementById('seccion-btn').getBoundingClientRect();
      const spans = [...d.querySelectorAll('.lugar-opt span')];
      return { left: Math.round(dr.left), right: Math.round(dr.right), width: Math.round(dr.width),
        vp: innerWidth, btnRight: Math.round(btn.right),
        filas: spans.length, cortadas: spans.filter(s => s.scrollWidth > s.clientWidth + 1).length };
    });
  };
  await page.setViewportSize({ width: 390, height: 844 });
  await enterFestival(page, 'cinemancia2026', '2026-09-04T10:00:00-05:00');

  // 1 · catálogo entero: hay nombres largos, así que el panel tiene que usar todo
  const todo = await abrir(true);
  expect(todo, 'el panel de Sección abre').not.toBeNull();
  expect(todo.filas, 'con TODO hay muchas secciones — si no, el test no mide nada').toBeGreaterThan(5);
  expect(todo.left, 'no se sale por la izquierda').toBeGreaterThanOrEqual(0);
  expect(todo.right, 'ni por la derecha').toBeLessThanOrEqual(todo.vp);
  if (todo.cortadas > 0) {
    const sobra = todo.vp - todo.width;
    expect(sobra,
      `${todo.cortadas} nombres cortados y ${sobra}px de pantalla sin usar: si algo se corta, el panel usa todo lo que hay`)
      .toBeLessThanOrEqual(20);
  }

  // 2 · y con pocas secciones (el día de hoy) NO se estira: queda anclado al botón
  const hoy = await abrir(false);
  if (hoy && hoy.cortadas === 0 && hoy.width < todo.vp - 40) {
    expect(Math.abs(hoy.right - hoy.btnRight),
      `sin nada que cortar, el panel se ancla al borde del botón (panel ${hoy.right}, botón ${hoy.btnRight})`)
      .toBeLessThanOrEqual(2);
  }
});

// ── T166 — las dos salidas de texto gris se leen (contraste PINTADO) ─────────
// Auditorías A-7 y A-3 (2 sep 2026), medido a 390x844 con el color COMPUESTO
// (color × opacidades heredadas sobre el fondo real), no con el declarado:
//   «Ver todas las ciudades» (hoja de ciudad) → #555555 sobre #1D1B18 = 2,30
//   «Letterboxd» (ficha)                     → #555555 al .55 = pintado #3B3A39 = 1,54
// Los dos son texto de 11px, así que les aplica el 4,5:1 de AA normal.
//
// Por qué PINTADO y no declarado: el enlace de Letterboxd hereda el opacity:.55
// de `.c-lb`, y ningún guardián estático lo ve. Cambiarle solo el color a
// --gray daba 2,39 —seguía fallando— y un grep habría cantado victoria.
// Con --white bajo la misma opacidad pinta #908E8A y da 5,34.
const _AA_NORMAL = 4.5;

test('T166 — las dos salidas de texto gris cumplen AA pintadas', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const sonda = () => {
    const lin = c => { c /= 255; return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
    const L = ([a, b, c]) => 0.2126 * lin(a) + 0.7152 * lin(b) + 0.0722 * lin(c);
    const nums = s => (s.match(/[\d.]+/g) || []).map(Number);
    // fondo: el primer ancestro con un relleno realmente opaco
    const fondo = el => { let n = el;
      while (n && n !== document.documentElement) {
        const p = nums(getComputedStyle(n).backgroundColor);
        if (p.length >= 3 && (p[3] === undefined || p[3] > 0.9)) return p.slice(0, 3);
        n = n.parentElement; }
      return nums(getComputedStyle(document.body).backgroundColor).slice(0, 3); };
    // alfa compuesto: el propio y el de TODOS sus ancestros
    const alfa = el => { let a = 1, n = el;
      while (n && n !== document.documentElement) { a *= parseFloat(getComputedStyle(n).opacity) || 1; n = n.parentElement; }
      return a; };
    window.__sonda = sel => {
      const el = document.querySelector(sel); if (!el) return null;
      const r = el.getBoundingClientRect(); if (!r.width || !r.height) return null;
      const cs = getComputedStyle(el), c = nums(cs.color);
      const aTxt = c.length > 3 ? c[3] : 1;
      const a = alfa(el) * aTxt, bg = fondo(el);
      const pintado = c.slice(0, 3).map((v, i) => Math.round(v * a + bg[i] * (1 - a)));
      const l1 = L(pintado), l2 = L(bg);
      return { txt: el.textContent.trim().slice(0, 26), px: parseFloat(cs.fontSize),
        peso: cs.fontWeight, declarado: cs.color, alfa: Math.round(a * 100) / 100,
        pintado: '#' + pintado.map(v => v.toString(16).padStart(2, '0')).join(''), bg,
        contraste: +(((Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05)).toFixed(2)) }; };
  };

  // 1 · A-7 · el escape de la hoja de ciudad (festival multiciudad: la hoja abre sola)
  await enterFestival(page, 'ficdeh2026', '2026-08-15T10:00');
  await page.evaluate(sonda);
  const esc = await page.evaluate(() => window.__sonda('.lugar-opt.escape'));
  expect(esc, 'la hoja de ciudad muestra su escape').not.toBeNull();
  expect(esc.px, 'es texto pequeño: le aplica el 4,5:1').toBeLessThan(18);
  expect(esc.contraste,
    `«${esc.txt}»: ${esc.declarado} pintado ${esc.pintado} sobre ${esc.bg} da ${esc.contraste}`)
    .toBeGreaterThanOrEqual(_AA_NORMAL);

  // 2 · A-3 · el enlace de Letterboxd de la ficha
  await enterFestival(page, 'cinemancia2026', '2026-09-04T10:00');
  const abierta = await page.evaluate(async () => {
    const b = document.createElement('button'); b.setAttribute('data-action', 'closeCitySheet');
    document.body.appendChild(b); b.click(); b.remove();
    await new Promise(r => setTimeout(r, 500));
    for (const f of FILMS.filter(x => !x._cancelled && x.type !== 'event')) {
      openPelSheet(f.title);
      await new Promise(r => setTimeout(r, 800));
      if (document.querySelector('.c-lb-text')) return f.title;
      closePelSheet && closePelSheet();
      await new Promise(r => setTimeout(r, 200));
    }
    return null;
  });
  expect(abierta, 'alguna obra del catálogo trae enlace de Letterboxd').toBeTruthy();
  await page.evaluate(sonda);
  const lb = await page.evaluate(() => window.__sonda('.c-lb-text'));
  expect(lb, 'el enlace se dibuja').not.toBeNull();
  expect(lb.px, 'también es texto pequeño').toBeLessThan(18);
  expect(lb.alfa, 'y sigue atenuado — el arreglo NO fue subirle la opacidad').toBeLessThan(0.7);
  expect(lb.contraste,
    `«${lb.txt}»: ${lb.declarado} al ${lb.alfa} pinta ${lb.pintado} sobre ${lb.bg} y da ${lb.contraste}`)
    .toBeGreaterThanOrEqual(_AA_NORMAL);
});

// ── T177 — un festival terminado no pregunta ciudad, pero deja elegirla ──────
// «¿A cuál ciudad vas?» está en futuro. En un festival pasado era lo primero y
// ÚNICO que se veía al entrar: medido en FICDEH, la hoja ocupa 390x844 —el
// viewport entero— con z-index 9999, así que también se comía el toque a las
// pestañas. Once ciudades preguntadas a alguien que viene a RECORDAR.
//
// Las dos mitades van juntas a propósito, y es la decisión de Juan (4 sep 2026):
// lo que se retira es la PREGUNTA, no la posibilidad. Sin la segunda mitad, este
// test se «arregla» borrando la elección de ciudad por completo —que es
// exactamente lo que no se quiere—: el filtro de Lugar tiene que seguir
// ofreciendo las mismas ciudades para releer el programa de una.
test('T177 — el festival terminado no pregunta ciudad, y el filtro sigue ofreciéndolas', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-25T10:00:00-05:00');
  const r = await page.evaluate(async () => {
    const w = ms => new Promise(r => setTimeout(r, ms));
    const H = await import('/src/view/helpers.js');
    const T = await import('/src/domain/time.js');
    await w(1400);
    // 1 · la pregunta no aparece
    const sh = document.getElementById('city-sheet');
    const hoja = { abierta: !!sh && sh.classList.contains('open'),
                   display: sh ? getComputedStyle(sh).display : null };
    // 2 · pero las ciudades siguen estando, y el filtro las ofrece
    switchMainNav('mnav-cartelera');
    await w(1400);
    const lb = document.getElementById('lugar-btn');
    if (!lb) return { hoja, sinFiltro: true };
    lb.click();
    await w(800);
    const drop = document.querySelector('#lugar-drop, .filter-drop');
    const opciones = drop ? [...drop.querySelectorAll('[data-v]')].map(e => e.dataset.v) : [];
    return { hoja,
      terminado: T.festivalEnded(),
      ciudadesDelDato: H.festivalCities(FILMS).length,
      ciudadesEnFiltro: opciones.filter(v => v.startsWith('drill:')).length };
  });
  // Premisas: sin ellas no hay nada que medir, y tienen que sonar ([test-salida-muda])
  expect(r.sinFiltro, 'el filtro de Lugar existe').toBeUndefined();
  expect(r.terminado, 'el fixture es un festival TERMINADO').toBe(true);
  expect(r.ciudadesDelDato, 'y multiciudad — con una sola no habría pregunta que retirar')
    .toBeGreaterThanOrEqual(2);
  // 1 · no se pregunta
  expect(r.hoja.abierta, 'la hoja que pregunta la ciudad no se abre').toBe(false);
  expect(r.hoja.display, 'y no queda tapando la pantalla').not.toBe('flex');
  // 2 · pero se puede elegir igual — la mitad que impide «arreglarlo» borrando todo
  expect(r.ciudadesEnFiltro, 'el filtro de Lugar sigue ofreciendo las mismas ciudades')
    .toBe(r.ciudadesDelDato);
});
