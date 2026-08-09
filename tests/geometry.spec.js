// @ts-check
// geometry.spec.js — GUARDIÁN de geometría entre tabs (decisión Juan, 17 jul 2026):
// "distancias diferentes entre el topbar y lo demás en cada tab" es la clase de
// inconsistencia que este spec entierra. Regla: el PRIMER contenido de cada tab
// arranca a la MISMA distancia del chrome superior (tolerancia ±4px por
// subpíxeles/bordes). Si un tab introduce un espaciador fantasma, esto lo caza
// con número y elemento culpable.
const { test, expect } = require('@playwright/test');

// MÓVIL explícito: el proyecto chromium hereda devices['Desktop Chrome'] (1280px)
// y ahí la nav vive EN FLUJO bajo el chrome — todo gap medido en desktop es de
// otro layout. La queja y la regla son del teléfono.
test.use({ viewport: { width: 390, height: 844 } });
const { enterFestival, LEVIZA_SIMTIME } = require('./helpers');

// Mide: bottom del chrome superior visible y top del primer elemento de
// contenido visible (>4px de alto) del view activo. Devuelve el gap y quién es.
async function measureGap(page) {
  return page.evaluate(() => {
    const vis = (e) => {
      if (!e) return false;
      const cs = getComputedStyle(e);
      if (cs.display === 'none' || cs.visibility === 'hidden') return false;
      const r = e.getBoundingClientRect();
      return r.height > 4 && r.width > 0;
    };
    // Chrome superior: topbar + barras sticky visibles que cuelgan de él
    const chrome = ['.topbar', '#programa-mode-bar', '#hdr-programa', '#hdr-ag', '.day-tabs']
      .flatMap(s => [...document.querySelectorAll(s)])
      .filter(vis);
    const chromeBottom = Math.max(...chrome.map(e => e.getBoundingClientRect().bottom), 0);
    // Primer contenido visible bajo el chrome (excluye style/script/overlays fijos)
    const roots = ['#ag-view', '#grid', '#programa-list', 'main', 'body'];
    let first = null;
    for (const rs of roots) {
      const root = document.querySelector(rs);
      if (!root || !vis(root)) continue;
      const walk = [...root.querySelectorAll('*')].filter(e => {
        if (!vis(e)) return false;
        const cs = getComputedStyle(e);
        if (cs.position === 'fixed') return false;
        const r = e.getBoundingClientRect();
        return r.top >= chromeBottom - 2 && r.top < chromeBottom + 400;
      });
      if (walk.length) { first = walk.sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top)[0]; break; }
    }
    if (!first) return { gap: null, el: null, chromeBottom };
    // Cadena de contribuciones: padding/margin top de first y sus ancestros
    const chain = [];
    let n = first;
    while (n && n !== document.body) {
      const cs = getComputedStyle(n);
      const mt = parseFloat(cs.marginTop) || 0, pt = parseFloat(cs.paddingTop) || 0;
      if (mt || pt) chain.push(`${n.id ? '#' + n.id : '.' + (n.className||'').toString().split(' ')[0]}:m${mt}/p${pt}`);
      n = n.parentElement;
    }
    return {
      gap: Math.round(first.getBoundingClientRect().top - chromeBottom),
      el: (first.id ? '#' + first.id : '') + '.' + (first.className || '').toString().split(' ').slice(0, 2).join('.'),
      chromeBottom: Math.round(chromeBottom),
      chain,
      between: [...document.querySelectorAll('body *')].filter(e => {
        const r = e.getBoundingClientRect(); const cs = getComputedStyle(e);
        return cs.position !== 'fixed' && r.height > 0 && r.top >= chromeBottom - 2 && r.bottom <= first.getBoundingClientRect().top + 2 && r.height >= 8;
      }).slice(0, 6).map(e => `${e.id ? '#' + e.id : '.' + (e.className||'').toString().split(' ')[0]}:h${Math.round(e.getBoundingClientRect().height)}`),
    };
  });
}

test('G01 — el primer contenido de cada tab arranca a la misma distancia del chrome', async ({ page }) => {
  await enterFestival(page, 'leviza2026', LEVIZA_SIMTIME); // festival EN CURSO → Planear poblado (pending>0)
  // Estado POBLADO (el de la queja real): watchlist + plan guardado — los tabs
  // vacíos centran un hero y no miden lo mismo que la vida real.
  await page.evaluate(() => {
    const wl = FILMS.filter(f => !f.info && f.time).slice(0, 6);
    watchlist.clear(); wl.forEach(f => watchlist.add(f.title));
    const sched = wl.slice(0, 4).map(f => ({ _title: f.title, title: f.title, day: f.day, time: f.time, venue: f.venue, duration: f.duration, day_order: f.day_order }));
    state.set('savedAgenda', { schedule: sched });
  });
  const tabs = ['mnav-cartelera', 'mnav-seleccion', 'mnav-planner', 'mnav-miplan'];
  const gaps = {};
  for (const tab of tabs) {
    await page.evaluate((t) => { switchMainNav(t); (t === 'mnav-cartelera' ? showDayView : showAgView)(); }, tab);
    await page.waitForTimeout(500);
    gaps[tab] = await measureGap(page);
    // anti-flake: un re-intento si el primer render aún no asentó
    if (gaps[tab].gap === null || gaps[tab].gap > 2) { await page.waitForTimeout(500); gaps[tab] = await measureGap(page); }
  }
  // Sub-vista TODO del Programa (camino de render grid — lección Tribeca 18 jul):
  // la regla FLUSH cubre TODO camino de render, no solo la puerta de cada tab.
  await page.evaluate(() => {
    switchMainNav('mnav-cartelera'); showDayView();
    const chip = [...document.querySelectorAll('[data-day]')].find(e => e.dataset.day === 'all');
    if (chip) chip.click();
  });
  await page.waitForTimeout(500);
  gaps['cartelera-todo'] = await measureGap(page);
  if (gaps['cartelera-todo'].gap === null || gaps['cartelera-todo'].gap > 2) { await page.waitForTimeout(500); gaps['cartelera-todo'] = await measureGap(page); }
  // La banda de sección del grid debe ser FULL-BLEED simétrica (borde a borde),
  // como toda banda sec-hdr: el padding del grid y los márgenes de la banda cancelan.
  const sepBleed = await page.evaluate(() => {
    const sep = document.querySelector('.poster-grid-sep');
    if (!sep) return null;
    const r = sep.getBoundingClientRect();
    return { left: Math.round(r.left), rightInset: Math.round(window.innerWidth - r.right) };
  });
  expect(sepBleed, 'la vista TODO no renderizó ninguna banda de sección').not.toBeNull();
  expect(Math.abs(sepBleed.left), `banda de sección con aire a la izquierda: ${JSON.stringify(sepBleed)}`).toBeLessThanOrEqual(2);
  expect(Math.abs(sepBleed.rightInset), `banda de sección con aire a la derecha: ${JSON.stringify(sepBleed)}`).toBeLessThanOrEqual(2);
  console.log('G01 gaps:', JSON.stringify(gaps));
  const values = Object.values(gaps).map(g => g.gap).filter(g => g !== null);
  expect(values.length).toBe(5);
  const min = Math.min(...values), max = Math.max(...values);
  // FLUSH (regla Juan 17 jul): cada tab arranca PEGADO al chrome — sin espacio.
  expect(max, `algún tab no arranca pegado al chrome: ${JSON.stringify(gaps)}`).toBeLessThanOrEqual(2);
  expect(max - min, `gaps desiguales entre tabs: ${JSON.stringify(gaps)}`).toBeLessThanOrEqual(2);
});

// ── G02 — el grupo de sesiones: mismo ritmo, mismo eje, sin robarle la sede ────
// El bloque multi-día se dibuja como GRUPO (corchete + eslabón + un solo control,
// 9 ago 2026). Tres medidas lo sostienen, y las tres se pierden en silencio si
// alguien toca el CSS sin medir:
//
//  1. La fila del grupo mide LO MISMO que una fila suelta. Agrupar no es motivo
//     para cambiar el ritmo vertical de la lista.
//  2. Corchete, eslabón y botón comparten EJE. Es lo que hace leer «estas N
//     alimentan una sola acción»; con el eje corrido, el corchete parece decorado.
//  3. La columna de sede no encoge de más. El primer borrador la dejaba en 129px
//     contra 151px de una fila normal: 22px que parten «Colombo Americano · Sala 2»
//     en dos líneas — el mismo bug que causó el badge «✓ En tu Plan» (20 jul).
test('G02 — el grupo de sesiones comparte eje y no le roba ancho a la sede', async ({ page }) => {
  await enterFestival(page, 'leviza2026', '2026-05-13T09:00:00-05:00');
  const m = await page.evaluate(() => {
    activeVenue = 'all';
    const taller = FILMS.find(f => f.is_recurring);
    openPelSheet(taller.title, taller);
    const g = document.querySelector('.blq');
    if (!g) return { err: 'no se dibujó el grupo' };
    const ctr = el => { const r = el.getBoundingClientRect(); return +(r.top + r.height / 2).toFixed(1); };
    const out = {
      filas: [...document.querySelectorAll('.blq .pel-sheet-screening')].map(e => +e.getBoundingClientRect().height.toFixed(1)),
      corchete: +document.querySelector('.blq-corchete').getBoundingClientRect().height.toFixed(1),
      ejeGrupo: ctr(g),
      ejeLink: ctr(document.querySelector('.blq-link')),
      ejeBtn: ctr(document.querySelector('.blk-add, .blk-quitar')),
      sedeGrupo: +document.querySelector('.blq .pelicula-venue').getBoundingClientRect().width.toFixed(1),
      // El RITMO se mide en padding, no en alto: el alto depende del contenido
      // (una sede con municipio ocupa dos líneas) y compararlo entre filas
      // distintas mide el texto, no el diseño. Primer borrador de este test:
      // falló contra una fila de referencia de 39px por esa razón.
      padGrupo: getComputedStyle(document.querySelector('.blq .pel-sheet-screening')).paddingTop,
    };
    // Referencia: una función suelta CON su botón «Agregar» — el mismo caso de uso.
    const suelta = FILMS.find(f => !f.is_recurring && f.day && f.time && f.venue && !f.info);
    openPelSheet(suelta.title, suelta);
    const fila = document.querySelector('.pel-sheet-screening');
    out.padNormal = getComputedStyle(fila).paddingTop;
    out.sedeNormal = +fila.querySelector('.pelicula-venue').getBoundingClientRect().width.toFixed(1);
    out.normalTieneBoton = !!fila.querySelector('.suggestion-add');
    return out;
  });
  expect(m.err).toBeUndefined();
  console.log('G02:', JSON.stringify(m));
  expect(m.normalTieneBoton, 'la referencia tiene que ser una fila CON botón').toBe(true);

  // 1. mismo ritmo vertical que una fila suelta
  expect(m.padGrupo, `la fila del grupo cambió su padding (${m.padGrupo}) frente a una suelta (${m.padNormal})`).toBe(m.padNormal);
  // el corchete abarca exactamente las filas
  expect(Math.abs(m.corchete - m.filas.reduce((a, b) => a + b, 0)),
    `el corchete (${m.corchete}) no abarca las filas`).toBeLessThanOrEqual(1);
  // 2. eje compartido
  expect(Math.abs(m.ejeLink - m.ejeGrupo), 'el eslabón no está centrado en el grupo').toBeLessThanOrEqual(1);
  expect(Math.abs(m.ejeBtn - m.ejeGrupo), 'el botón no comparte eje con el grupo').toBeLessThanOrEqual(1);
  // 3. la sede no encoge de más
  expect(m.sedeNormal - m.sedeGrupo,
    `el grupo le roba ${(m.sedeNormal - m.sedeGrupo).toFixed(1)}px a la sede (tope 8)`).toBeLessThanOrEqual(8);
});

// ── G03 — ningún icono se estruja ─────────────────────────────────────────────
// Un <svg> dentro de un contenedor flex es un item más. Sin `flex-shrink:0`, el
// navegador reparte el ahogo entre el icono y el texto, y el SVG —que no tiene
// ancho intrínseco— cede primero: el texto envuelve, el icono no puede, así que
// pierde ancho conservando el alto. No se ve más chico: se ve DEFORMADO.
//
// Reportado por Juan el 9 ago 2026 sobre el pin de sede. Medido en FICMA:
// «Secretaría de la Mujer y Equidad de Género» dejaba el pin en 7,5×13 —42% de
// ancho— y ya «Teatro los Fundadores» perdía un 8%. Afectaba SEIS superficies.
//
// El criterio es la PROPORCIÓN, no el tamaño: un icono que rinde más chico en
// ambas dimensiones lo está achicando el CSS a propósito y se ve bien. Esa
// distinción es la que hace útil al guardián — con «más angosto que su ancho
// declarado» daba 5 culpables y 4 eran falsos positivos.
const _detectorIconos = () => {
  const rotos = [];
  document.querySelectorAll('svg[width][height]').forEach(svg => {
    const w = parseFloat(svg.getAttribute('width')), h = parseFloat(svg.getAttribute('height'));
    if (!w || !h) return;
    const r = svg.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) return;            // oculto: no se juzga
    const propDecl = w / h, propReal = r.width / r.height;
    if (Math.abs(propReal - propDecl) / propDecl < 0.02) return;
    const p = svg.parentElement;
    rotos.push(`${p ? '.' + (p.className || '').toString().split(' ')[0] : '?'}: `
      + `${w}×${h} declarado → ${r.width.toFixed(1)}×${r.height.toFixed(1)} `
      + `(texto: "${(p ? p.textContent : '').replace(/\s+/g, ' ').trim().slice(0, 30)}")`);
  });
  return [...new Set(rotos)];
};

test('G03 — ningún icono pierde su proporción por el flex del contenedor', async ({ page }) => {
  // FICMA a propósito: tiene las sedes más largas del catálogo, que es lo que
  // aprieta. Con nombres cortos el defecto no aparece y el test pasaría en vano.
  await enterFestival(page, 'ficma2026', '2026-08-09T08:00:00-05:00');
  const rotos = [];
  // DOS muestras, y solo cuenta lo que aparece en las dos. Los sheets entran con
  // animación y una medición a mitad de camino inventa proporciones que no existen
  // un frame después: así salió flaky en su primera corrida. Un defecto real de
  // layout no se arregla solo en 250ms, así que la intersección no pierde nada.
  const barrer = async (pantalla) => {
    const a = await page.evaluate(_detectorIconos);
    await page.waitForTimeout(250);
    const b = await page.evaluate(_detectorIconos);
    a.filter(x => b.includes(x)).forEach(x => rotos.push(`[${pantalla}] ${x}`));
  };

  await page.evaluate(() => {
    activeVenue = 'all';
    const largo = FILMS.filter(f => f.venue && f.day && f.time)
      .sort((a, b) => (b.venue || '').length - (a.venue || '').length)[0];
    openPelSheet(largo.title, largo);
  });
  await page.waitForTimeout(700);
  await barrer('ficha');

  await page.evaluate(() => { closePelSheet(); switchMainNav('mnav-cartelera'); showDayView(); });
  await page.waitForTimeout(600);
  await barrer('programa');

  await page.evaluate(() => {
    const fs = FILMS.filter(f => f.day && f.time && f.venue && !f.info).slice(0, 5);
    state.set('savedAgenda', { schedule: fs.map(f => ({ ...f, _title: f.title })) });
    fs.forEach(f => watchlist.add(f.title));
    switchMainNav('mnav-miplan'); showAgView();
  });
  await page.waitForTimeout(800);
  await barrer('mi plan');

  await page.evaluate(() => { switchMainNav('mnav-seleccion'); showAgView(); });
  await page.waitForTimeout(700);
  await barrer('intereses');

  expect(rotos, `icono(s) deformado(s):\n  ${rotos.join('\n  ')}`).toEqual([]);
});
