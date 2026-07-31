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
  const api = loadDomain({
    globals: {
      FILMS: films,
      watched: new Set(), prioritized: new Set(), availability: {}, savedAgenda: null,
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
  return { films, api };
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
