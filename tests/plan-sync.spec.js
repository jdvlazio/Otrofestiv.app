// @ts-check
// plan-sync.spec.js — el plan guardado se re-deriva del catálogo al hidratar.
//
// Bug real (captura de Juan, 31 jul 2026): plan de FINCA guardado ANTES del
// anclaje de función. Las entradas eran copias congeladas sin _slotDur y Mi Plan
// calculaba sobre ellas: "18:05" de fin para Mi casa es su casa y "Q&A · tenés
// ~115 min" — donde el catálogo vivo dice "19:51" y "~9 min". El planificador
// estaba bien; la persistencia servía datos de otro momento.
//
// La corrección es de puerta: loadFestival (tras sellar slots y avisos) y
// _applyCloudRow re-derivan cada entrada de su función viva vía
// syncScheduleWithCatalog. Este test escribe EL PLAN DE LA CAPTURA en
// localStorage y recarga por el camino real de producción.
const { test, expect } = require('@playwright/test');
const { enterFestival } = require('./helpers');

test('PS01 — el plan congelado pre-anclaje sale del hydrate con la verdad del catálogo', async ({ page }) => {
  await enterFestival(page, 'finca2026', '2026-08-13T10:00');
  const r = await page.evaluate(async () => {
    // El plan de la captura: copias congeladas de ANTES del anclaje (sin _slot*)
    const congelada = t => {
      const f = FILMS.find(fi => fi.title === t && fi.day === '2026-08-13');
      const c = { ...f, _title: f.title };
      delete c._slotKey; delete c._slotDur; delete c._slotMin;
      return c;
    };
    localStorage.setItem('finca2026_saved', JSON.stringify({ scenarioIdx: 0, schedule: [
      congelada('Propiedad privada prohibido pasar'),
      congelada('Mi casa es su casa'),
      congelada('Ziki'),
    ]}));
    // Recarga por el camino real: loadFestival → loadState (hydrate) → sync
    await loadFestival('finca2026');
    _simTime = '2026-08-13T10:00';
    const jueves = DAY_KEYS.indexOf('2026-08-13');
    activeMiPlanDay = jueves >= 0 ? jueves : 0;
    switchMainNav('mnav-miplan'); showAgView();
    return savedAgenda.schedule.map(s => ({ t: s._title.slice(0, 12), slotDur: s._slotDur || null }));
  });
  // el dato: las entradas hidratadas heredaron el anclaje vivo
  expect(r).toEqual([
    { t: 'Propiedad pr', slotDur: 111 },
    { t: 'Mi casa es s', slotDur: 111 },
    { t: 'Ziki', slotDur: 91 },
  ]);
  // la UI: fines de bloque correctos y el aviso de Q&A con el hueco REAL
  await page.waitForSelector('.mplan-row', { timeout: 8000 });
  const ui = await page.evaluate(() => ({
    // La línea dice «hasta HH:MM» (revisión de UX Writer, 16 ago): la fila
    // mostraba dos horas sin decir cuál era cuál. Se extrae la HORA, que es lo
    // que este test mide — que el fin sea el del BLOQUE, no el de la obra.
    fines: [...document.querySelectorAll('.mplan-row .mplan-t2')].map(e => (e.textContent.match(/\d{1,2}:\d{2}/) || [''])[0]),
    avisos: [...document.querySelectorAll('.mplan-warn-row')].map(w => w.textContent.trim()),
  }));
  expect(ui.fines).toEqual(['19:51', '19:51', '22:01']);
  expect(ui.avisos.join(' ')).toMatch(/~9 min/);
  expect(ui.avisos.join(' ')).not.toMatch(/115/);
});

// PS02 — la corrección de la nube: un plan viejo que llega por _applyCloudRow
// (boot con sesión / Realtime) también se re-deriva. Mismo contrato, otra puerta.
test('PS02 — el plan que llega de la nube también se normaliza contra el catálogo', async ({ page }) => {
  await enterFestival(page, 'finca2026', '2026-08-13T10:00');
  const r = await page.evaluate(() => {
    const f = FILMS.find(fi => fi.title === 'Ziki' && fi.day === '2026-08-13');
    const vieja = { ...f, _title: f.title, duration: '2 min' };
    delete vieja._slotKey; delete vieja._slotDur; delete vieja._slotMin;
    _applyCloudRow({ saved_agenda: { scenarioIdx: 0, schedule: [vieja] } }, { wholesale: true });
    const e = savedAgenda.schedule[0];
    return { dur: e.duration, slotDur: e._slotDur || null };
  });
  expect(r.dur).toBe('12 min');
  expect(r.slotDur).toBe(91);
});

// PS03 — el calendario exportado dice la verdad del bloque
// exportICS calculaba DTEND con parseInt(duration)||90: una obra anclada de
// 5 min exportaba "18:00→18:05" al calendario del teléfono — la mentira de la
// captura del 31 jul, fugada al ICS. Ahora DTEND sale de blockDuration (19:51).
test('PS03 — el ICS exporta el fin del BLOQUE para una obra anclada', async ({ page }) => {
  await enterFestival(page, 'finca2026', '2026-08-13T10:00');
  const ics = await page.evaluate(async () => {
    const f = FILMS.find(fi => fi.title === 'Mi casa es su casa' && fi.day === '2026-08-13');
    state.set('savedAgenda', { scenarioIdx: 0, schedule: [{ ...f, _title: f.title }] });
    // capturar el blob del download (camino web) sin descargar nada
    let captured = null;
    const orig = URL.createObjectURL.bind(URL);
    URL.createObjectURL = b => { captured = b; return orig(b); };
    await exportICS();
    URL.createObjectURL = orig;
    return captured ? await captured.text() : null;
  });
  expect(ics).toContain('BEGIN:VEVENT');
  // 18:00 -03:00 = 21:00Z; fin del bloque 19:51 -03:00 = 22:51Z (obra suelta diría 21:05Z)
  expect(ics).toContain('DTSTART:20260813T210000Z');
  expect(ics).toContain('DTEND:20260813T225100Z');
});

// PS05 — el calendario dice los minutos que reserva, y Avisos por qué
// Auditoría 4 sep 2026: una actividad sin duración publicada exportaba un evento
// de 90 minutos —el relleno de DEFAULT_DURATION_MIN— con la duración EN BLANCO:
// la descripción terminaba colgando en « - » mientras bloqueaba 90 minutos reales.
// El DTEND no cambia (un evento necesita un fin): cambia que lo diga, con la `~`
// de siempre. El POR QUÉ vive en Avisos, en la ficha, que es donde se decide
// (decisión de Juan, 4 sep) — eso lo mide T171.
test('PS05 — el ICS dice los minutos que reserva cuando la duración no está publicada', async ({ page }) => {
  await enterFestival(page, 'cinemancia2026', '2026-09-09T15:00');
  const r = await page.evaluate(async () => {
    const capturar = async (f) => {
      state.set('savedAgenda', { scenarioIdx: 0, schedule: [{ ...f, _title: f.title }] });
      let cap = null;
      const orig = URL.createObjectURL.bind(URL);
      URL.createObjectURL = b => { cap = b; return orig(b); };
      await exportICS();
      URL.createObjectURL = orig;
      return cap ? await cap.text() : null;
    };
    const sin = FILMS.find(x => !x._cancelled && x.day && x.time && !x.duration);
    const con = FILMS.find(x => !x._cancelled && x.day && x.time && x.duration);
    return { sinDur: sin ? { obra: sin.title.slice(0, 30), ics: await capturar(sin) } : null,
             conDur: con ? { obra: con.title.slice(0, 30), dur: con.duration, ics: await capturar(con) } : null };
  });

  expect(r.sinDur, 'Cinemancia tiene la actividad sin duración del censo').not.toBeNull();
  const desc = (r.sinDur.ics.match(/^DESCRIPTION:.*$/m) || [''])[0];
  expect(desc, `dice los minutos que bloquea (dice: ${desc})`).toContain('90 min');
  expect(desc, 'marcados como estimados con la `~` de siempre').toContain('~90');
  expect(desc.trim(), 'y ya no termina colgando en « - »').not.toMatch(/-\s*$/);

  // control: con duración publicada, ni tilde ni invento — sale el dato tal cual
  expect(r.conDur, 'y hay obras con duración').not.toBeNull();
  const desc2 = (r.conDur.ics.match(/^DESCRIPTION:.*$/m) || [''])[0];
  expect(desc2, `«${r.conDur.obra}» sale con su duración real (dice: ${desc2})`).toContain(r.conDur.dur);
  expect(desc2, 'sin marca de estimación').not.toContain('~');
});

// ── PS06 — el calendario conserva las comas del título ───────────────────────
// Auditoría 4 sep 2026: `clean()` reemplazaba por un espacio la coma, el punto y
// coma, el salto de línea y la barra invertida. «Ni un minuto de silencio, toda
// una vida de búsqueda» llegaba al calendario del teléfono como «Ni un minuto de
// silencio  toda una vida de búsqueda», partido y con doble espacio. Medido: 39
// obras en 12 festivales llevan alguno de esos caracteres.
//
// El RFC 5545 §3.3.11 pide ESCAPARLOS (`\,`), no borrarlos: el valor sigue siendo
// uno solo y el título llega entero.
//
// Se afirma: (1) el título con coma sobrevive al viaje —se desescapa al que era—;
// (2) la coma va escapada, no cruda, que es lo que haría que un parser partiera
// el valor; (3) control: un título SIN coma no gana barras de la nada.
test('PS06 — el ICS escapa la coma en vez de borrarla', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-15T10:00');
  const r = await page.evaluate(async () => {
    const capturar = async (f) => {
      state.set('savedAgenda', { scenarioIdx: 0, schedule: [{ ...f, _title: f.title }] });
      let cap = null;
      const orig = URL.createObjectURL.bind(URL);
      URL.createObjectURL = b => { cap = b; return orig(b); };
      await exportICS();
      URL.createObjectURL = orig;
      return cap ? await cap.text() : null;
    };
    const conComa = FILMS.find(x => !x._cancelled && x.day && x.time && /,/.test(x.title));
    const sinComa = FILMS.find(x => !x._cancelled && x.day && x.time && !/[,;\\]/.test(x.title));
    return { conComa: conComa ? { titulo: conComa.title, ics: await capturar(conComa) } : null,
             sinComa: sinComa ? { titulo: sinComa.title, ics: await capturar(sinComa) } : null };
  });

  expect(r.conComa, 'FICDEH tiene títulos con coma — 5 de los 39 del censo').not.toBeNull();
  const linea = (r.conComa.ics.match(/^SUMMARY:.*$/m) || [''])[0];

  // 1 · el título vuelve a ser el que era al desescapar
  const desescapado = linea.replace(/^SUMMARY:/, '')
    .replace(/\\n/g, '\n').replace(/\\([,;])/g, '$1').replace(/\\\\/g, '\\');
  expect(desescapado, `«${r.conComa.titulo}» llega entero (línea: ${linea})`).toBe(r.conComa.titulo);

  // 2 · y la coma viaja ESCAPADA: cruda, un parser partiría el valor en dos
  expect(linea, 'la coma va escapada').toContain('\\,');
  expect(linea.replace(/\\,/g, ''), 'y no queda ninguna coma cruda suelta').not.toContain(',');

  // 3 · control: sin coma no aparecen barras de la nada
  expect(r.sinComa, 'y hay títulos sin coma').not.toBeNull();
  const linea2 = (r.sinComa.ics.match(/^SUMMARY:.*$/m) || [''])[0];
  expect(linea2, `«${r.sinComa.titulo}» sale tal cual`).toBe('SUMMARY:' + r.sinComa.titulo);

  // 4 · el punto y coma y la barra invertida. NINGÚN título del catálogo los trae
  // (medido: 0 de 2.246), así que el caso se construye — sin él, escapar solo la
  // coma pasaba el test y el día que un festival publique un título con `;` se
  // partiría el evento en silencio.
  const raro = await page.evaluate(async () => {
    const f = FILMS.find(x => !x._cancelled && x.day && x.time);
    const titulo = 'Uno; dos, tres \\ cuatro';
    state.set('savedAgenda', { scenarioIdx: 0, schedule: [{ ...f, _title: titulo, title: titulo }] });
    let cap = null;
    const orig = URL.createObjectURL.bind(URL);
    URL.createObjectURL = b => { cap = b; return orig(b); };
    await exportICS();
    URL.createObjectURL = orig;
    return { titulo, ics: cap ? await cap.text() : null };
  });
  const l3 = (raro.ics.match(/^SUMMARY:.*$/m) || [''])[0];
  const vuelta = l3.replace(/^SUMMARY:/, '')
    .replace(/\\n/g, '\n').replace(/\\([,;])/g, '$1').replace(/\\\\/g, '\\');
  expect(vuelta, `«${raro.titulo}» vuelve entero (línea: ${l3})`).toBe(raro.titulo);
  expect(l3, 'el punto y coma va escapado').toContain('\\;');
  expect(l3, 'y la barra invertida también').toContain('\\\\');
});

// ── PS07 — los afiches del export se cargan, aunque la pantalla ya los mostró ─
// Reporte de Juan (4 sep 2026, FICCI desde iPhone): exportó su festival y los
// pósters no salieron. Reproducido: el canvas EXIGE permiso cruzado —dibujar sin
// él lo contamina y `toBlob` tira excepción, medido—, pero la grilla ya cargó ese
// mismo afiche SIN pedirlo, y la copia guardada no sirve para una petición que sí
// lo pide. Con un póster real de FICCI (TMDB w185): con permiso cruzado falla,
// sin él carga, y con permiso cruzado más una dirección distinta carga. El
// servidor autoriza (manda `access-control-allow-origin: *`); lo que falla es
// reusar la copia vieja.
//
// Se afirma sobre el ARCHIVO producido, no sobre el flujo: cada celda del muro
// tiene la variedad de color de una foto. El mosaico de reemplazo —el que se
// dibuja cuando el afiche no carga— es plano y se distingue por eso.
test('PS07 — el export dibuja los afiches, no sus reemplazos', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await enterFestival(page, 'ficci65');
  const r = await page.evaluate(async () => {
    const b = document.createElement('button'); b.setAttribute('data-action', 'closeCitySheet');
    document.body.appendChild(b); b.click(); b.remove();
    await new Promise(r => setTimeout(r, 500));
    // obras con afiche de OTRO ORIGEN: es el caso reportado y el que fallaba.
    // Anotado y fuera de este arreglo: los 7 afiches incrustados (`data:`) de
    // FICCI tampoco se dibujan, pero por otra razón —cargan perfecto con y sin
    // permiso cruzado, medido 180x270; lo que no los entrega es `getFilmPoster`,
    // el dueño único de qué afiche va—. Ensanchar acá sería tocar ese dueño a
    // ciegas.
    const el = [];
    const vis = new Set();
    for (const f of FILMS) {
      if (f._cancelled || !f.title || vis.has(f.title)) continue;
      if (!/^https?:/i.test(f.poster || '')) continue;
      vis.add(f.title); el.push(f);
      if (el.length === 3) break;
    }
    if (el.length < 3) return { pocas: el.length };
    state.set('watchlist', new Set(el.map(f => f.title)));
    state.set('watched', new Set(el.map(f => f.title)));
    // 1 · la pantalla los pinta PRIMERO, sin permiso cruzado: así queda la copia
    //     que rompía el export. Sin este paso el defecto no se reproduce.
    switchMainNav('mnav-seleccion');
    if (typeof renderAgenda === 'function') renderAgenda();
    await new Promise(r => setTimeout(r, 2500));
    const pintados = [...document.querySelectorAll('img')].filter(i => i.naturalWidth > 0).length;

    let blob = null;
    const origTB = HTMLCanvasElement.prototype.toBlob;
    HTMLCanvasElement.prototype.toBlob = function (cb, ...a) {
      return origTB.call(this, x => { if (!blob) blob = x; cb(x); }, ...a);
    };
    const bt = document.createElement('button'); bt.setAttribute('data-action', 'shareDiary');
    document.body.appendChild(bt); bt.click(); bt.remove();
    await new Promise(r => setTimeout(r, 6000));
    HTMLCanvasElement.prototype.toBlob = origTB;
    if (!blob) return { pintados, sinBlob: true, toast: document.getElementById('prio-toast')?.textContent };

    const bmp = await createImageBitmap(blob);
    const cv = document.createElement('canvas'); cv.width = bmp.width; cv.height = bmp.height;
    const cx = cv.getContext('2d'); cx.drawImage(bmp, 0, 0);
    const COLS = 3, PAD = 64, HDR = 240, GAP = 24;
    const cw = Math.floor((bmp.width - PAD * 2 - GAP * (COLS - 1)) / COLS), ch = Math.round(cw * 1.5);
    const celdas = [];
    for (let i = 0; i < 3; i++) {
      const col = i % COLS, row = Math.floor(i / COLS);
      const d = cx.getImageData(PAD + col * (cw + GAP) + 4, HDR + row * (ch + GAP) + 4, cw - 8, ch - 8).data;
      const s = new Set();
      for (let p = 0; p < d.length; p += 4 * 97) s.add(`${d[p]},${d[p + 1]},${d[p + 2]}`);
      celdas.push(s.size);
    }
    return { pintados, dim: [bmp.width, bmp.height], colores: celdas };
  });

  expect(r.pocas, 'FICCI tiene obras con afiche de otro origen').toBeUndefined();
  expect(r.sinBlob, `el export produce su imagen (toast: ${r.toast})`).toBeUndefined();
  expect(r.pintados, 'la pantalla pintó los afiches ANTES — sin eso el defecto no se reproduce')
    .toBeGreaterThan(0);
  // el reemplazo es un degradado plano: mide decenas de colores, no cientos
  for (const [i, n] of r.colores.entries()) {
    expect(n, `la celda ${i} trae un afiche, no su reemplazo (${r.colores.join(', ')} colores)`)
      .toBeGreaterThan(200);
  }
});

// ── PS08 — ninguna línea del .ics pasa de 75 octetos ─────────────────────────
// Auditoría 4 sep 2026: 10 de 53 líneas de un .ics de FICDEH pasaban el límite
// del RFC 5545 §3.1 —hasta 138 octetos el UID de una actividad de nombre largo, y
// 98 un SUMMARY—. Ningún calendario nos lo rechazó (Google y Apple son
// tolerantes), así que es deuda de formato, no un fallo visto; se paga porque el
// estándar es el contrato con un programa que no controlamos.
//
// Se afirma: (1) ninguna línea pasa de 75 octetos; (2) el contenido sobrevive al
// plegado —desplegando se recupera lo que había—; (3) control: el archivo sigue
// teniendo sus propiedades y sus finales de línea CRLF.
test('PS08 — el ICS pliega sus líneas largas sin perder contenido', async ({ page }) => {
  await enterFestival(page, 'ficdeh2026', '2026-08-15T10:00');
  const ics = await page.evaluate(async () => {
    // se eligen las obras de TÍTULO más largo: son las que producen líneas largas
    const vis = new Set(); const todas = [];
    for (const f of FILMS) { if (!f._cancelled && f.day && f.time && !vis.has(f.title)) { vis.add(f.title); todas.push(f); } }
    const el = todas.sort((a, b) => b.title.length - a.title.length).slice(0, 5);
    state.set('savedAgenda', { scenarioIdx: 0, schedule: el.map(f => ({ ...f, _title: f.title })) });
    let cap = null;
    const orig = URL.createObjectURL.bind(URL);
    URL.createObjectURL = b => { cap = b; return orig(b); };
    await exportICS();
    URL.createObjectURL = orig;
    return cap ? await cap.text() : null;
  });
  expect(ics, 'el export produce su archivo').toBeTruthy();

  const oct = s => new TextEncoder().encode(s).length;
  const lineas = ics.split('\r\n');
  const largas = lineas.filter(l => oct(l) > 75).map(l => `${oct(l)} octetos: ${l.slice(0, 30)}…`);
  expect(largas, `ninguna línea pasa de 75 octetos — ${largas.slice(0, 3).join(' · ')}`).toHaveLength(0);

  // el contenido sobrevive: al desplegar (quitar CRLF+espacio) vuelve a estar entero
  const desplegado = ics.replace(/\r\n /g, '');
  expect(desplegado, 'el calendario conserva su estructura').toContain('BEGIN:VEVENT');
  const sums = desplegado.split('\r\n').filter(l => l.startsWith('SUMMARY:'));
  expect(sums.length, 'con un evento por obra del plan').toBe(5);
  const titulos = await page.evaluate(() => savedAgenda.schedule.map(s => s._title));
  for (const t of titulos) {
    const esperado = t.replace(/\\/g, '\\\\').replace(/([,;])/g, '\\$1');
    expect(desplegado, `«${t.slice(0, 28)}» llega entero`).toContain('SUMMARY:' + esperado);
  }

  // control: no queda ningún salto de línea SUELTO — el RFC pide CRLF, y el
  // plegado es justamente quien podría introducir uno. (La última línea no lleva
  // salto: por eso se busca el `\n` sin `\r` delante, no que todas terminen en CRLF.)
  expect(/[^\r]\n/.test(ics), 'no hay saltos de línea sueltos: todo va en CRLF').toBe(false);
});
