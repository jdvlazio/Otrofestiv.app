// QA de dominio del planeador — SMOKE con datos REALES de festivales.
//
// Las suites de invariantes usan fixtures sintéticas limpias. Los bugs de la
// semana de Ficmontañas fueron todos de FORMA de datos reales: duration como
// "120 min" string vs numérica, eventos sin duration, horas AM/PM vs 24h,
// bloques de cortos, venues con y sin coordenadas. Este smoke corre
// computeScenarios contra CADA festivals/*.json del repo con watchlists
// muestreadas determinísticamente, y valida los invariantes del planeador
// sobre esos datos. Corre automáticamente contra cada festival futuro que se
// monte en el pipeline — el onboarding de un festival con datos raros que
// rompan el planner se caza en CI, no en producción.
//
// simTime = 1 día antes del inicio del festival → ninguna función "pasada":
// el universo completo del festival es planificable.

const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const { loadDomain } = require('../lib/load-domain.js');

const ROOT = path.resolve(__dirname, '..', '..');
const FEST_DIR = path.join(ROOT, 'festivals');
const FESTIVALS = fs.readdirSync(FEST_DIR).filter(f => f.endsWith('.json'));

assert.ok(FESTIVALS.length > 0, 'no hay festivales en festivals/');

function loadFest(file) {
  const d = JSON.parse(fs.readFileSync(path.join(FEST_DIR, file), 'utf8'));
  // simTime: 1 día antes de la PRIMERA fecha del festival. Derivado de
  // festivalDates (presente en todos los JSON) — festivalStartStr NO existe en
  // los festivales viejos (vive en src/config.js para ellos).
  const firstDate = Object.values(d.festivalDates).sort()[0];
  const tz = d.timezoneOffset || '-05:00';
  const start = new Date(firstDate + 'T00:00:00' + tz);
  assert.ok(!isNaN(start), `${file}: festivalDates inválido (${firstDate})`);
  const simTime = new Date(start.getTime() - 24 * 3600 * 1000).toISOString();
  const endDate = Object.values(d.festivalDates).sort().slice(-1)[0];
  const api = loadDomain({
    globals: {
      FILMS: d.films,
      watched: new Set(),
      prioritized: new Set(),
      availability: {},
      savedAgenda: null,
      FESTIVAL_BUFFER: 15,
      FESTIVAL_TRANSPORT: d.transport || 'transit',
      FESTIVAL_CONFIG: { real: { venues: d.venues || {} } },
      _activeFestId: 'real',
      DEFAULT_DURATION_MIN: 90,
      _simTime: simTime,
      FESTIVAL_END: new Date(endDate + 'T23:59:00' + tz),
      FESTIVAL_DATES: d.festivalDates,
      TZ_OFFSET: d.timezoneOffset || '-05:00',
    },
  });
  return { d, api };
}

// Títulos planificables: con día+hora, no informativos.
function schedulable(d) {
  return [...new Set(d.films
    .filter(f => f.day && f.time && !f.info)
    .map(f => f.title))];
}

for (const file of FESTIVALS) {
  test(`datos reales · ${file}: invariantes del planeador sobre watchlists muestreadas`, () => {
    const { d, api } = loadFest(file);
    const pool = schedulable(d);
    assert.ok(pool.length >= 3, `${file}: menos de 3 títulos planificables`);

    // 6 watchlists deterministas por festival (LCG sembrado por el nombre).
    let seed = [...file].reduce((a, c) => (a * 31 + c.charCodeAt(0)) % 2147483648, 7);
    const rnd = () => (seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648;

    for (let s = 0; s < 6; s++) {
      const size = 3 + Math.floor(rnd() * 3); // 3–5 títulos (bajo el cap de nodos)
      const titles = [];
      const used = new Set();
      while (titles.length < Math.min(size, pool.length)) {
        const t = pool[Math.floor(rnd() * pool.length)];
        if (!used.has(t)) { used.add(t); titles.push(t); }
      }

      const scenarios = api.computeScenarios(titles);
      assert.ok(scenarios.length > 0,
        `${file} muestra ${s} (${titles.join(', ')}): sin escenarios`);

      for (const [i, sc] of scenarios.entries()) {
        const label = `${file} muestra ${s} esc#${i}`;
        // I1: sin conflictos internos (con travel time y Q&A reales)
        for (let a = 0; a < sc.schedule.length; a++)
          for (let b = a + 1; b < sc.schedule.length; b++)
            assert.ok(!api.screensConflict(sc.schedule[a], sc.schedule[b]),
              `${label}: conflicto interno entre "${sc.schedule[a]._title || sc.schedule[a].title}" y "${sc.schedule[b]._title || sc.schedule[b].title}"`);
        // I2: partición exacta incluidos/excluidos sobre la watchlist
        const inPlan = sc.schedule.map(p => p._title || p.title);
        assert.strictEqual(
          new Set([...inPlan, ...(sc.excluded || [])]).size, titles.length,
          `${label}: la partición no cubre la watchlist`);
        // I3: maximalidad — ningún excluido cabía sin conflicto.
        // CONTRATO is_recurring (aprendido de este mismo smoke con Leviza): un
        // título recurrente (taller multi-día) entra con TODAS sus sesiones o
        // ninguna (`allFit` en findMax) — su maximalidad se evalúa sobre el
        // conjunto completo, no por sesión individual.
        for (const ex of sc.excluded || []) {
          const screens = d.films.filter(f => f.title === ex && f.day && f.time && !f.info);
          if (!screens.length) continue;
          if (screens[0].is_recurring) {
            const allFit = screens.every(scr => !sc.schedule.some(p => api.screensConflict(p, scr)));
            assert.ok(!allFit,
              `${label}: recurrente "${ex}" cabía COMPLETO sin conflicto y quedó excluido`);
          } else {
            for (const scr of screens) {
              assert.ok(sc.schedule.some(p => api.screensConflict(p, scr)),
                `${label}: "${ex}" (${scr.day} ${scr.time}) cabía sin conflicto y quedó excluida`);
            }
          }
        }
      }
    }
  });
}
