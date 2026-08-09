// ORÁCULO DEL PLANEADOR — optimalidad demostrada sobre datos reales.
//
// plannerInvariants prueba que el plan es VÁLIDO; plannerRealData que no
// EXPLOTA con datos reales. Lo que ninguno probaba: que no existe un plan
// MEJOR ("Ziki quedó afuera pudiendo entrar" — el bug del 30 jul). Este test
// compara computeScenarios contra un solver exacto de referencia
// (tests/lib/exact-planner) sobre CADA festivals/*.json con watchlists
// sembradas, y certifica cada escenario con verifyPlan.
//
// PARIDAD CON PRODUCCIÓN: el catálogo pasa por explodeScreenings +
// sealSharedSlots — los MISMOS dueños de dominio que corre el loader (por eso
// se extrajeron de loadFestival). Sin eso el oráculo probaría otro universo:
// Tribeca tiene 203 screenings[] sin explotar y FINCA necesita el anclaje.
//
// Cota de nodos: MAX_NODES_PER_CALL=80000 limita a computeScenarios. Con
// watchlists de 3–8 títulos no se alcanza; si una discrepancia aparece junto a
// un cap-hit, la causa es el tope, no el algoritmo (documentado, no observado).

const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const { loadDomain } = require('../lib/load-domain.js');
const { exactMaxEntries } = require('../lib/exact-planner.js');

const ROOT = path.resolve(__dirname, '..', '..');
const FEST_DIR = path.join(ROOT, 'festivals');
const FESTIVALS = fs.readdirSync(FEST_DIR).filter(f => f.endsWith('.json'));

// Fase 1: los dueños de preparación de catálogo (los mismos del loader).
const prep = loadDomain({
  functions: ['parseDur', 'explodeScreenings', 'sealSharedSlots'],
  globals: { DEFAULT_DURATION_MIN: 90 },
});

function loadFest(file) {
  const d = JSON.parse(fs.readFileSync(path.join(FEST_DIR, file), 'utf8'));
  let films = prep.explodeScreenings(d.films);
  if (d.sharedSlotIsOneScreening) prep.sealSharedSlots(films);

  const firstDate = Object.values(d.festivalDates).sort()[0];
  const tz = d.timezoneOffset || '-05:00';
  const simTime = new Date(new Date(firstDate + 'T00:00:00' + tz).getTime() - 24 * 3600 * 1000).toISOString();
  const endDate = Object.values(d.festivalDates).sort().slice(-1)[0];
  // Estado del usuario POR REFERENCIA: loadDomain enlaza los globals con
  // `let x = __g['x']`, así que el dominio y el test comparten el mismo objeto.
  // Mutarlo (add/clear/delete) cambia lo que ve isScreeningBlocked y
  // computeScenarios sin recargar el dominio — 96 recargas evitadas.
  const state = { watched: new Set(), prioritized: new Set(), availability: {} };
  const api = loadDomain({
    globals: {
      FILMS: films,
      watched: state.watched, prioritized: state.prioritized,
      availability: state.availability, savedAgenda: null,
      FESTIVAL_BUFFER: 15,
      FESTIVAL_TRANSPORT: d.transport || 'transit',
      FESTIVAL_CONFIG: { real: { venues: d.venues || {} } },
      _activeFestId: 'real', DEFAULT_DURATION_MIN: 90,
      _simTime: simTime,
      FESTIVAL_END: new Date(endDate + 'T23:59:00' + tz),
      FESTIVAL_DATES: d.festivalDates,
      TZ_OFFSET: tz,
    },
  });
  return { films, api, state, dates: d.festivalDates };
}

const schedulable = films => [...new Set(films.filter(f => f.day && f.time && !f.info && !f._cancelled).map(f => f.title))];

for (const file of FESTIVALS) {
  test(`oráculo · ${file}: computeScenarios alcanza el máximo exacto`, () => {
    const { films, api } = loadFest(file);
    const pool = schedulable(films);
    if (pool.length < 3) { console.log(`${file}: <3 títulos, skip`); return; }

    // 8 watchlists sembradas por festival (LCG determinista — cero flakiness).
    let seed = [...file].reduce((a, c) => (a * 31 + c.charCodeAt(0)) % 2147483648, 13);
    const rnd = () => (seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648;

    const groupByTitle = t => {
      const screens = films.filter(f => f.title === t && f.day && f.time && !f.info && !f._cancelled);
      return { screens, recurring: screens.some(f => f.is_recurring) };
    };

    for (let w = 0; w < 8; w++) {
      const size = Math.min(pool.length, 3 + Math.floor(rnd() * 6)); // 3–8 títulos
      const titles = [], used = new Set();
      while (titles.length < size) {
        const t = pool[Math.floor(rnd() * pool.length)];
        if (!used.has(t)) { used.add(t); titles.push(t); }
      }

      const exact = exactMaxEntries(titles, groupByTitle, api.screensConflict);
      const scenarios = api.computeScenarios(titles);

      if (exact === 0) { assert.deepStrictEqual(scenarios, [], `${file} w${w}: exact=0 pero hay escenarios`); continue; }
      assert.ok(scenarios.length > 0, `${file} w${w}: exact=${exact} pero cero escenarios [${titles.join(' | ')}]`);

      scenarios.forEach((sc, i) => {
        // certificado de validez — verifyPlan, el mismo del futuro chokepoint
        const cert = api.verifyPlan(sc.schedule, { checkPassed: true });
        assert.ok(cert.ok, `${file} w${w} sc${i}: plan inválido: ${JSON.stringify(cert.violations)}`);
        // OPTIMALIDAD: cada escenario propone el máximo alcanzable
        assert.strictEqual(sc.schedule.length, exact,
          `${file} w${w} sc${i}: el heurístico dejó afuera pudiendo no hacerlo — propuso ${sc.schedule.length}, el exacto ${exact} [${titles.join(' | ')}]`);
      });
      // y el trueMax que reporta la UI no miente
      assert.strictEqual(scenarios[0].trueMax, exact,
        `${file} w${w}: trueMax=${scenarios[0].trueMax} ≠ exacto=${exact}`);
    }
  });
}

// ── ORÁCULO CON RESTRICCIONES ─────────────────────────────────────────────────
// El oráculo de arriba prueba el plan de un usuario que no dijo nada: watchlist y
// nada más. El usuario real dice tres cosas más, y son justo las que el planeador
// promete respetar:
//
//   · ya vistas    → el título no entra al plan (computeScenarios filtra `pending`)
//   · prioridades  → el título entra SÍ O SÍ, y el plan encoge si hace falta
//   · disponibilidad → una franja del día queda vetada (isScreeningBlocked)
//
// De las tres, la de prioridades no tenía oráculo: `maxWithPriorities` se creía.
// Acá se compara contra el solver exacto con `required`, que es la definición
// formal de la promesa. Y el contrato completo que se certifica es:
//
//   trueMax           === máximo exacto SIN exigir prioridades
//   maxWithPriorities === máximo exacto exigiéndolas (0 si son incompatibles)
//   cada escenario    === maxWithPriorities y contiene TODAS las prioridades
//                        (o trueMax, si resultaron incompatibles → fallback)
//
// Se separa del test de arriba a propósito: si algo se rompe, el nombre del test
// dice si el régimen roto es el libre o el restringido.
//
// Test añadido el 9 ago 2026, cerrando el bloque E de docs/QA-FULL.md — escrito
// en mayo, nunca ejecutado.
for (const file of FESTIVALS) {
  test(`oráculo con restricciones · ${file}: prioridades, ya vistas y disponibilidad`, () => {
    const { films, api, state, dates } = loadFest(file);
    const pool = schedulable(films);
    if (pool.length < 4) { console.log(`${file}: <4 títulos, skip`); return; }

    const days = Object.values(dates || {}).sort();
    let seed = [...file].reduce((a, c) => (a * 31 + c.charCodeAt(0)) % 2147483648, 71);
    const rnd = () => (seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648;

    for (let w = 0; w < 8; w++) {
      // ── sembrar la watchlist ──
      const size = Math.min(pool.length, 4 + Math.floor(rnd() * 5)); // 4–8 títulos
      const titles = [], used = new Set();
      while (titles.length < size) {
        const t = pool[Math.floor(rnd() * pool.length)];
        if (!used.has(t)) { used.add(t); titles.push(t); }
      }

      // ── sembrar el estado del usuario (mutación por referencia) ──
      state.watched.clear();
      state.prioritized.clear();
      Object.keys(state.availability).forEach(k => delete state.availability[k]);

      // ya vistas: 0–1 título de la watchlist
      if (rnd() < 0.5) state.watched.add(titles[Math.floor(rnd() * titles.length)]);
      // prioridades: 0–2 títulos, nunca uno ya visto (sería contradictorio)
      const candidatas = titles.filter(t => !state.watched.has(t));
      const nPrio = Math.floor(rnd() * 3);
      for (let i = 0; i < nPrio && i < candidatas.length; i++) {
        state.prioritized.add(candidatas[Math.floor(rnd() * candidatas.length)]);
      }
      // disponibilidad: una franja vetada en un día del festival
      if (days.length && rnd() < 0.6) {
        const d = days[Math.floor(rnd() * days.length)];
        const desde = 9 + Math.floor(rnd() * 8); // 09:00–16:00
        state.availability[d] = { blocks: [{ from: `${String(desde).padStart(2, '0')}:00`, to: `${String(desde + 4).padStart(2, '0')}:00` }] };
      }

      // ── el mismo universo que ve producción ──
      // `pending` de computeScenarios: sin ya-vistas y sin eventos informativos.
      const pending = titles.filter(t => !state.watched.has(t) && !films.some(f => f.title === t && f.info));
      // groupByTitle replica el filtrado de baseGroups. isScreeningBlocked es el
      // DUEÑO de disponibilidad y se llama, no se reimplementa: si el test
      // recalculara la regla sería una segunda opinión, no un oráculo.
      // plannableScreens es el DUEÑO de «qué funciones son planificables para vos»
      // —cancelada, pasada, franja vetada, taller entero-o-nada—. Se llama, no se
      // reimplementa: si el test recalculara la regla mediría un universo distinto
      // al de la app y su veredicto no valdría nada.
      const groupByTitle = t => {
        const screens = api.plannableScreens(t).filter(f => f.day && f.time && !f.info);
        return { screens, recurring: screens.some(f => f.is_recurring) };
      };

      const conFunciones = new Set(pending.filter(t => groupByTitle(t).screens.length > 0));
      // Una prioridad SIN funciones utilizables no entra a baseGroups → no se exige.
      const required = new Set([...state.prioritized].filter(t => conFunciones.has(t)));

      const exact = exactMaxEntries(pending, groupByTitle, api.screensConflict);
      const exactPrio = required.size
        ? exactMaxEntries(pending, groupByTitle, api.screensConflict, { required })
        : exact;

      const scenarios = api.computeScenarios(titles);
      const ctx = `${file} w${w} [prio:${[...required].length} vistas:${state.watched.size} franja:${Object.keys(state.availability).length}]`;

      if (exact === 0) { assert.deepStrictEqual(scenarios, [], `${ctx}: exact=0 pero hay escenarios`); continue; }
      assert.ok(scenarios.length > 0, `${ctx}: exact=${exact} y cero escenarios`);

      // Los dos máximos que la UI reporta, contra el solver exacto.
      assert.strictEqual(scenarios[0].trueMax, exact, `${ctx}: trueMax=${scenarios[0].trueMax} ≠ exacto=${exact}`);
      if (required.size) {
        assert.strictEqual(scenarios[0].maxWithPriorities, exactPrio,
          `${ctx}: maxWithPriorities=${scenarios[0].maxWithPriorities} ≠ exacto con prioridades=${exactPrio}`);
      }

      // Prioridades incompatibles: producción lo declara y cae a trueMax. Que el
      // fallback exista no lo exime de ser óptimo.
      const objetivo = (required.size && exactPrio > 0) ? exactPrio : exact;

      scenarios.forEach((sc, i) => {
        const cert = api.verifyPlan(sc.schedule, { checkPassed: true, catalog: films });
        assert.ok(cert.ok, `${ctx} sc${i}: plan inválido: ${JSON.stringify(cert.violations)}`);
        assert.strictEqual(sc.schedule.length, objetivo,
          `${ctx} sc${i}: propuso ${sc.schedule.length}, el exacto ${objetivo} [${titles.join(' | ')}]`);

        const enPlan = new Set(sc.schedule.map(s => s._title || s.title));
        // YA VISTAS — la promesa más simple y la más fácil de romper en silencio.
        state.watched.forEach(t => assert.ok(!enPlan.has(t),
          `${ctx} sc${i}: «${t}» está marcada como ya vista y el plan la incluye`));
        // DISPONIBILIDAD — ninguna función del plan cae en una franja vetada.
        sc.schedule.forEach(s => assert.ok(!api.isScreeningBlocked(s),
          `${ctx} sc${i}: «${s._title || s.title}» (${s.day} ${s.time}) cae en una franja no disponible`));
        // PRIORIDADES — si son satisfacibles, están TODAS.
        if (required.size && exactPrio > 0) {
          required.forEach(t => assert.ok(enPlan.has(t),
            `${ctx} sc${i}: la prioridad «${t}» quedó afuera de un plan que podía incluirla`));
        }
      });
    }
  });
}

// ── PRIORIDADES INCOMPATIBLES (dirigido, no muestreado) ───────────────────────
// El test de arriba sembró 96 watchlists con prioridades y NO cazó una mutación
// que hacía `maxWithPriorities = trueMax` — es decir, un planeador que dice
// «respeté tus prioridades» sin haberlas exigido. La razón no fue el aserto sino
// el muestreo: en las 96, las prioridades nunca costaron nada, así que ambos
// máximos coincidían y la mentira era indistinguible de la verdad.
//
// Más muestreo no arregla eso: hay que CONSTRUIR la tensión. Se busca en cada
// festival un par de obras con una sola función que chocan entre sí; exigir las
// dos es imposible por definición, y ahí los dos máximos se separan:
//   trueMax = 1  ·  maxWithPriorities = 0  ·  incompatiblePriorities = true
//
// Es también la única rama del contrato que el muestreo no visitó ni una vez
// (exactPrio === 0), y la que la UI usa para decirle al usuario QUÉ dos obras
// se pelean. Escrito el 9 ago 2026.
for (const file of FESTIVALS) {
  test(`prioridades incompatibles · ${file}: los dos máximos se separan`, () => {
    const { films, api, state } = loadFest(file);
    const porTitulo = {};
    films.filter(f => f.day && f.time && !f.info && !f._cancelled)
         .forEach(f => { (porTitulo[f.title] = porTitulo[f.title] || []).push(f); });
    // Una sola función y no recurrente: cero flexibilidad, el choque es forzoso.
    const unicas = Object.keys(porTitulo).filter(t => porTitulo[t].length === 1 && !porTitulo[t][0].is_recurring);

    let par = null;
    for (let i = 0; i < unicas.length && !par; i++) {
      for (let j = i + 1; j < unicas.length; j++) {
        if (api.screensConflict(porTitulo[unicas[i]][0], porTitulo[unicas[j]][0])) { par = [unicas[i], unicas[j]]; break; }
      }
    }
    if (!par) { console.log(`${file}: sin par de obras inflexibles en conflicto, skip`); return; }

    const [a, b] = par;
    // LAS DOS como prioridad — sin esto `hasPriorities` es false y el planeador
    // nunca entra a la rama que se quiere juzgar.
    state.prioritized.add(a); state.prioritized.add(b);

    const groupByTitle = t => {
      const screens = films.filter(f => f.title === t && f.day && f.time && !f.info && !f._cancelled);
      return { screens, recurring: screens.some(f => f.is_recurring) };
    };
    const exact = exactMaxEntries([a, b], groupByTitle, api.screensConflict);
    const exactPrio = exactMaxEntries([a, b], groupByTitle, api.screensConflict, { required: new Set([a, b]) });

    assert.strictEqual(exact, 1, `${file}: el par elegido debería dar máximo 1 [${a} | ${b}]`);
    assert.strictEqual(exactPrio, 0, `${file}: exigir ambas debería ser imposible [${a} | ${b}]`);

    const scenarios = api.computeScenarios([a, b]);
    assert.ok(scenarios.length > 0, `${file}: cero escenarios para el par`);
    // LA PROMESA: los dos máximos NO son el mismo número.
    assert.strictEqual(scenarios[0].trueMax, exact, `${file}: trueMax=${scenarios[0].trueMax} ≠ ${exact}`);
    assert.strictEqual(scenarios[0].maxWithPriorities, exactPrio,
      `${file}: maxWithPriorities=${scenarios[0].maxWithPriorities} ≠ exacto con prioridades=${exactPrio} — el planeador dice respetar prioridades que no exigió [${a} | ${b}]`);
    assert.ok(scenarios[0].incompatiblePriorities,
      `${file}: prioridades imposibles sin declarar incompatibilidad [${a} | ${b}]`);
    // Y la UI tiene que poder NOMBRAR el par que se pelea.
    const pares = scenarios[0].conflictingPriorityPairs.map(p => [...p].sort().join('|'));
    assert.ok(pares.includes([a, b].sort().join('|')),
      `${file}: el par en conflicto no se reporta a la UI [${a} | ${b}] — reportados: ${JSON.stringify(pares)}`);
  });
}

// ── Canario del ANCLAJE (dirigido, no muestreado) ─────────────────────────────
// M3 de la verificación por mutación: quitar el sellado del test no caía por
// sampling — heurístico y exacto consumen el mismo array y quedan consistentes
// entre sí aunque AMBOS estén mal. La paridad con producción la garantiza la
// extracción (loader y oráculo llaman los MISMOS dueños de dominio); este
// canario le pone un diente conductual: el trío real de la captura del 30 jul
// (dos obras ancladas 18:00 + Ziki 20:30, mismo Cine York) DEBE dar 3.
// Sin sellado, las dos de las 18:00 rivalizan y el máximo cae a 2.
test('canario anclaje · finca-2026: el trío de la captura planifica completo', () => {
  const { films, api } = loadFest('finca-2026.json');
  const titles = ['Propiedad privada prohibido pasar', 'Mi casa es su casa', 'Ziki'];
  titles.forEach(t => assert.ok(films.some(f => f.title === t), `falta ${t} en el catálogo`));
  const scenarios = api.computeScenarios(titles);
  assert.ok(scenarios.length > 0, 'cero escenarios para el trío anclado');
  assert.strictEqual(scenarios[0].trueMax, 3, 'el anclaje no está sellado: el trío real cayó a ' + scenarios[0].trueMax);
});
