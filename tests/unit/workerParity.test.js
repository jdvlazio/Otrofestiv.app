// QA de dominio del planeador — PARIDAD worker ↔ main-thread.
//
// runCalc (src/controller/calc.js) NO ejecuta computeScenarios directamente:
// serializa las 16 fns de _SCHED_PURE_FNS con .toString(), las concatena con
// globals worker-local (_workerGlobals) y copias worker-local de simNow/
// festivalEnded/venueTravelMins (_venueFns), y evalúa TODO dentro de un Web
// Worker. Ese mecanismo es el gotcha recurrente documentado en CLAUDE.md:
// cambiar la firma/deps de una fn de dominio puede romper el worker con
// validate.py verde (el guard estático no ejecuta nada).
//
// Este test cierra el hueco EJECUTANDO el ensamblaje real:
//   1. Lee _SCHED_PURE_FNS del propio calc.js (si la lista cambia, el test
//      la sigue solo) y extrae los bloques _workerGlobals/_venueFns/tal cual.
//   2. Extrae las fns reales de src/domain/* (mismas fuentes que producción).
//   3. Ensambla el "worker" como string y lo evalúa en un scope aislado de
//      Node (equivalente al Worker scope: sin acceso al exterior).
//   4. Corre computeScenarios dentro Y fuera con el mismo input y asserta
//      IGUALDAD EXACTA de escenarios (el RNG va sembrado por watchlist →
//      ambos lados son deterministas y comparables).
//
// Si una fn de dominio adquiere una dependencia que el worker no recibe, el
// ensamblado lanza ReferenceError o los resultados divergen → CI rojo.

const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const { loadDomain, extractFunction } = require('../lib/load-domain.js');

const ROOT = path.resolve(__dirname, '..', '..');
const CALC = fs.readFileSync(path.join(ROOT, 'src', 'controller', 'calc.js'), 'utf8');
const DOMAIN_SRC = ['time', 'film', 'schedule', 'festival']
  .map(m => fs.readFileSync(path.join(ROOT, 'src', 'domain', `${m}.js`), 'utf8'))
  .join('\n');

// 1 — la lista real de fns del worker, parseada de calc.js (auto-tracking).
function schedPureFns() {
  const m = CALC.match(/_SCHED_PURE_FNS\s*=\s*\[([\s\S]*?)\]/);
  assert.ok(m, '_SCHED_PURE_FNS no encontrada en calc.js');
  return [...m[1].matchAll(/'([^']+)'/g)].map(x => x[1]);
}

// Extrae un bloque template-literal `const NAME=\`...\`;` de calc.js.
function calcBlock(name) {
  const re = new RegExp('const ' + name + '=`([\\s\\S]*?)`;');
  const m = CALC.match(re);
  assert.ok(m, name + ' no encontrado en calc.js');
  return m[1];
}

// 3 — ensambla y evalúa el worker en scope aislado; devuelve compute(input).
function buildWorker() {
  const pure = schedPureFns().map(n => {
    const fn = extractFunction(DOMAIN_SRC, n);
    assert.ok(fn, `fn del worker no extraíble de src/domain: ${n}`);
    return fn;
  }).join('\n');
  const src = calcBlock('_workerGlobals') + calcBlock('_venueFns') + pure + `
return function compute(d){
  FILMS=d.films;
  watched=new Set(d.watched);
  prioritized=new Set(d.prioritized);
  availability=d.availability;
  FESTIVAL_DATES=d.festivalDates;
  TZ_OFFSET=d.tzOffset||'-05:00';
  FESTIVAL_END_TS=d.festivalEndTs;
  SIM_TIME=d.simTime;
  _venueCoords=d.venueCoords||{};
  _transport=d.transport||'transit';
  return computeScenarios(d.titles);
};`;
  // Scope aislado: sin closure sobre el test (paridad con Worker scope).
  // eslint-disable-next-line no-new-func
  return new Function(src)();
}

const VENUES = {
  'Sala A': { short: 'A', lat: 6.25, lng: -75.57 },
  'Sala B': { short: 'B', lat: 6.28, lng: -75.60 },
};
const DATES = { 'MAR 21': '2026-06-05', 'MAR 22': '2026-06-06' };
const SIM = '2026-06-05T08:00:00Z';
const END_TS = new Date('2099-01-01').getTime();

function mainThread(films, opts = {}) {
  return loadDomain({
    globals: {
      FILMS: films,
      watched: opts.watched || new Set(),
      prioritized: opts.prioritized || new Set(),
      availability: opts.availability || {},
      savedAgenda: null,
      FESTIVAL_BUFFER: 15,
      FESTIVAL_TRANSPORT: 'transit',
      FESTIVAL_CONFIG: { test: { venues: VENUES } },
      _activeFestId: 'test',
      DEFAULT_DURATION_MIN: 90,
      _simTime: SIM,
      FESTIVAL_END: new Date(END_TS),
      FESTIVAL_DATES: DATES,
      TZ_OFFSET: '-05:00',
    },
  });
}

function workerInput(films, titles, opts = {}) {
  return {
    films, titles,
    watched: [...(opts.watched || [])],
    prioritized: [...(opts.prioritized || [])],
    availability: opts.availability || {},
    festivalDates: DATES,
    tzOffset: '-05:00',
    festivalEndTs: END_TS,
    simTime: SIM,
    venueCoords: VENUES,
    transport: 'transit',
  };
}

const F = (title, day, time, opts) => Object.assign(
  { title, day, time, duration: '90 min', venue: 'Sala A', section: 'S' }, opts);

test('el ensamblaje del worker evalúa sin ReferenceError (guard de deps)', () => {
  assert.doesNotThrow(buildWorker);
});

test('PARIDAD: worker y main-thread producen escenarios idénticos', () => {
  const films = [
    F('F1', 'MAR 21', '10:00 AM'),
    F('F2', 'MAR 21', '10:30 AM', { venue: 'Sala B' }),
    F('F3', 'MAR 21', '4:00 PM'),
    F('F4', 'MAR 22', '11:00 AM', { has_qa: true }),
  ];
  const titles = ['F1', 'F2', 'F3', 'F4'];
  const compute = buildWorker();
  const w = compute(workerInput(films, titles));
  const m = mainThread(films).computeScenarios(titles);
  assert.deepStrictEqual(JSON.parse(JSON.stringify(w)), JSON.parse(JSON.stringify(m)),
    'worker y main-thread divergen para el mismo input');
});

test('PARIDAD bajo estrés: 15 configuraciones aleatorias deterministas', () => {
  let seed = 99;
  const rnd = () => (seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648;
  const compute = buildWorker();
  for (let c = 0; c < 15; c++) {
    const n = 3 + Math.floor(rnd() * 3);
    const films = [];
    for (let i = 0; i < n; i++) {
      const day = rnd() > 0.4 ? 'MAR 21' : 'MAR 22';
      const hour = 9 + Math.floor(rnd() * 10);
      const h12 = hour > 12 ? hour - 12 : hour;
      films.push(F('T' + i, day, `${h12}:${rnd() > 0.5 ? '00' : '30'} ${hour >= 12 ? 'PM' : 'AM'}`,
        { venue: rnd() > 0.5 ? 'Sala A' : 'Sala B', duration: `${60 + Math.floor(rnd() * 60)} min` }));
    }
    const titles = films.map(f => f.title);
    const prioritized = new Set(rnd() > 0.5 ? [titles[0]] : []);
    const w = compute(workerInput(films, titles, { prioritized }));
    const m = mainThread(films, { prioritized }).computeScenarios(titles);
    assert.deepStrictEqual(JSON.parse(JSON.stringify(w)), JSON.parse(JSON.stringify(m)),
      `config ${c}: divergencia worker/main`);
  }
});
