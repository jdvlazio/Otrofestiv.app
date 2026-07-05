// QA de dominio del planeador — getSuggestions (src/view/agenda.js).
//
// Contexto (5 jul 2026, decisión de Juan): Planear/Mi Plan son el factor
// diferencial de la app y deben generar confianza total. El bug del último día
// de Ficmontañas ("Día libre" + agenda llena + CERO sugerencias, fix en PR #242)
// motivó esta suite: convertir esa clase de bug en algo que el CI caza solo.
//
// INVARIANTE CENTRAL:
//   Si existe al menos una función futura, visible (no passed / no blocked /
//   no watched / no en agenda) y sin conflicto con el plan activo,
//   getSuggestions NUNCA devuelve vacío.
//
// Contrato de bloques (del código):
//   Bloque 0 (Restaurar): lastRemovedSlots con slot original libre — primero.
//   Bloque 1 (Descubrimiento): films del festival que quepan en huecos;
//     EXCLUYE watchlist (ya las conocés), watched, agenda, passed, blocked,
//     y funciones de <20 min de ventana.
//   Bloque 2 (Recuperación): watchlist no en agenda que quepa sin conflicto.
//   Orden dentro del día: Restaurar > watchlist > cronológico.
//   Sin plan confirmado (savedAgenda null/vacío) → {} (Mi Plan muestra su
//   empty state; no hay plan contra el cual sugerir).

const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

// Overlap simple por intervalos [start, end) del mismo día — stub determinista
// de screensConflict (que tiene su propia suite). Duración default 90.
function mkConflict() {
  const dur = s => { const m = String(s.duration || '').match(/(\d+)/); return m ? +m[1] : 90; };
  const toMin = t => { const [h, m] = String(t).split(':').map(Number); return h * 60 + m; };
  return (a, b) => {
    if (a.day !== b.day) return false;
    const aS = toMin(a.time), aE = aS + dur(a);
    const bS = toMin(b.time), bE = bS + dur(b);
    return aS < bE && bS < aE;
  };
}

function load(opts = {}) {
  const passed = opts.passed || new Set();
  return loadDomain({
    functions: ['getSuggestions', 'toMin', 'parseDur'],
    globals: {
      DEFAULT_DURATION_MIN: 90,
      FESTIVAL_BUFFER: opts.buffer != null ? opts.buffer : 10,
      DAY_KEYS: opts.DAY_KEYS || ['D1', 'D2'],
      FILMS: opts.FILMS || [],
      savedAgenda: 'savedAgenda' in opts ? opts.savedAgenda : { schedule: [] },
      watchlist: opts.watchlist || new Set(),
      watched: opts.watched || new Set(),
      lastRemovedSlots: opts.lastRemovedSlots || [],
      screeningPassed: s => passed.has(s._title || s.title),
      screensConflict: opts.screensConflict || mkConflict(),
      isScreeningBlocked: opts.isScreeningBlocked || (() => false),
      t: k => k,
    },
  });
}

const film = (title, day, time, duration, extra) =>
  Object.assign({ title, day, time, duration, venue: 'V' }, extra);
const sched = (title, day, time, duration) =>
  ({ _title: title, title, day, time, duration, venue: 'V' });

// ── INVARIANTE CENTRAL ────────────────────────────────────────────────────────

test('INVARIANTE: función futura visible y sin conflicto → nunca vacío', () => {
  const { getSuggestions } = load({
    FILMS: [film('Premiación', 'D2', '19:00', '120 min')],
    savedAgenda: { schedule: [sched('Vieja', 'D1', '10:00', '90 min')] },
    passed: new Set(['Vieja']),
  });
  const by = getSuggestions();
  assert.ok(Object.values(by).flat().length > 0, 'no puede estar vacío');
  assert.strictEqual(by.D2[0].title, 'Premiación');
});

test('INVARIANTE bajo estrés: 30 configuraciones aleatorias deterministas', () => {
  // Generador determinista (LCG) — sin Math.random: reproducible en CI.
  let seed = 42;
  const rnd = () => (seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648;
  for (let i = 0; i < 30; i++) {
    const hour = 8 + Math.floor(rnd() * 12);
    const target = film('Objetivo' + i, 'D2', `${String(hour).padStart(2, '0')}:00`, `${60 + Math.floor(rnd() * 60)} min`);
    const planItems = [];
    if (rnd() > 0.5) planItems.push(sched('PasadaA', 'D1', '10:00', '90 min'));
    if (rnd() > 0.5) planItems.push(sched('PasadaB', 'D1', '15:00', '60 min'));
    if (!planItems.length) planItems.push(sched('PasadaC', 'D1', '12:00', '90 min'));
    const { getSuggestions } = load({
      FILMS: [target],
      savedAgenda: { schedule: planItems },
      passed: new Set(planItems.map(s => s._title)),
    });
    const total = Object.values(getSuggestions()).flat();
    assert.ok(total.some(f => f.title === target.title),
      `config ${i}: el objetivo futuro visible no fue sugerido`);
  }
});

// ── Regresión PR #242 (el bug del último día) ────────────────────────────────

test('REGRESIÓN #242: plan 100% pasado NO silencia sugerencias', () => {
  const { getSuggestions } = load({
    FILMS: [
      film('Premiación', 'D2', '19:00', '120 min'),
      film('Concierto', 'D2', '20:30', null),
    ],
    savedAgenda: { schedule: [
      sched('Ayer1', 'D1', '12:00', '86 min'),
      sched('Ayer2', 'D1', '18:00', '96 min'),
    ] },
    passed: new Set(['Ayer1', 'Ayer2']),
  });
  const d2 = getSuggestions().D2 || [];
  assert.deepStrictEqual(d2.map(f => f.title), ['Premiación', 'Concierto']);
});

test('día completamente libre → sugiere todo el día en orden cronológico', () => {
  const { getSuggestions } = load({
    FILMS: [
      film('Tarde', 'D2', '16:00', '60 min'),
      film('Mañana', 'D2', '09:00', '60 min'),
      film('Noche', 'D2', '20:00', '60 min'),
    ],
    savedAgenda: { schedule: [sched('Otra', 'D1', '10:00', '60 min')] },
  });
  assert.deepStrictEqual((getSuggestions().D2 || []).map(f => f.title),
    ['Mañana', 'Tarde', 'Noche']);
});

// ── Exclusiones correctas (cada filtro, aislado) ─────────────────────────────

test('función pasada → excluida', () => {
  const { getSuggestions } = load({
    FILMS: [film('Pasada', 'D2', '10:00', '60 min'), film('Futura', 'D2', '19:00', '60 min')],
    savedAgenda: { schedule: [sched('X', 'D1', '10:00', '60 min')] },
    passed: new Set(['Pasada']),
  });
  assert.deepStrictEqual((getSuggestions().D2 || []).map(f => f.title), ['Futura']);
});

test('ya en agenda → excluida (aunque haya otra función de lo mismo)', () => {
  const { getSuggestions } = load({
    FILMS: [film('EnPlan', 'D2', '19:00', '60 min')],
    savedAgenda: { schedule: [sched('EnPlan', 'D2', '10:00', '60 min')] },
  });
  assert.strictEqual((getSuggestions().D2 || []).length, 0);
});

test('marcada como vista → excluida de todos los bloques', () => {
  const { getSuggestions } = load({
    FILMS: [film('Vista', 'D2', '19:00', '60 min')],
    savedAgenda: { schedule: [sched('X', 'D1', '10:00', '60 min')] },
    watched: new Set(['Vista']),
    watchlist: new Set(['Vista']),
  });
  assert.strictEqual((getSuggestions().D2 || []).length, 0);
});

test('bloqueada (isScreeningBlocked) → excluida', () => {
  const { getSuggestions } = load({
    FILMS: [film('Bloqueada', 'D2', '19:00', '60 min'), film('Libre', 'D2', '21:00', '60 min')],
    savedAgenda: { schedule: [sched('X', 'D1', '10:00', '60 min')] },
    isScreeningBlocked: f => f.title === 'Bloqueada',
  });
  assert.deepStrictEqual((getSuggestions().D2 || []).map(f => f.title), ['Libre']);
});

test('conflicto con el plan activo → excluida', () => {
  const { getSuggestions } = load({
    FILMS: [film('Choca', 'D2', '19:30', '60 min'), film('NoChoca', 'D2', '21:30', '60 min')],
    savedAgenda: { schedule: [sched('EnPlan', 'D2', '19:00', '90 min')] },
  });
  const titles = (getSuggestions().D2 || []).map(f => f.title);
  assert.ok(!titles.includes('Choca'), 'la que se solapa no puede sugerirse');
  assert.ok(titles.includes('NoChoca'));
});

// ── Datos imperfectos (la realidad de los festivales) ────────────────────────

test('evento SIN duration → default 90, se sugiere igual (nunca invisible)', () => {
  const { getSuggestions } = load({
    FILMS: [film('Concierto', 'D2', '20:30', null), film('SinDur2', 'D2', '18:00', undefined)],
    savedAgenda: { schedule: [sched('X', 'D1', '10:00', '60 min')] },
  });
  assert.deepStrictEqual((getSuggestions().D2 || []).map(f => f.title),
    ['SinDur2', 'Concierto']);
});

// ── Watchlist: descubrimiento vs recuperación ────────────────────────────────

test('watchlist: excluida de Descubrimiento pero presente vía Recuperación', () => {
  const { getSuggestions } = load({
    FILMS: [film('Corazón', 'D2', '19:00', '60 min')],
    savedAgenda: { schedule: [sched('X', 'D1', '10:00', '60 min')] },
    watchlist: new Set(['Corazón']),
  });
  const d2 = getSuggestions().D2 || [];
  assert.strictEqual(d2.length, 1, 'debe aparecer una sola vez (Bloque 2, no dup)');
  assert.strictEqual(d2[0].title, 'Corazón');
  assert.strictEqual(d2[0]._isFromWL, true, 'marcada como recuperación de watchlist');
});

test('orden dentro del día: watchlist antes que descubrimiento, luego cronológico', () => {
  const { getSuggestions } = load({
    FILMS: [
      film('Descubre9', 'D2', '09:00', '60 min'),
      film('WL20', 'D2', '20:00', '60 min'),
      film('Descubre15', 'D2', '15:00', '60 min'),
    ],
    savedAgenda: { schedule: [sched('X', 'D1', '10:00', '60 min')] },
    watchlist: new Set(['WL20']),
  });
  assert.deepStrictEqual((getSuggestions().D2 || []).map(f => f.title),
    ['WL20', 'Descubre9', 'Descubre15']);
});

// ── Restaurar (lastRemovedSlots) ─────────────────────────────────────────────

test('quitada recientemente con slot libre → "Restaurar" primero', () => {
  const { getSuggestions } = load({
    FILMS: [film('Otra', 'D2', '09:00', '60 min')],
    savedAgenda: { schedule: [sched('X', 'D1', '10:00', '60 min')] },
    lastRemovedSlots: [sched('Quitada', 'D2', '19:00', '60 min')],
  });
  const d2 = getSuggestions().D2 || [];
  assert.strictEqual(d2[0].title, 'Quitada');
  assert.strictEqual(d2[0]._isRestored, true);
  assert.strictEqual(d2[1].title, 'Otra');
});

test('quitada con slot AHORA ocupado → no ofrece Restaurar en ese slot', () => {
  const { getSuggestions } = load({
    FILMS: [],
    savedAgenda: { schedule: [sched('Nueva', 'D2', '19:00', '90 min')] },
    lastRemovedSlots: [sched('Quitada', 'D2', '19:30', '60 min')],
  });
  const d2 = getSuggestions().D2 || [];
  assert.ok(!d2.some(f => f._isRestored), 'slot ocupado: no Restaurar');
});

// ── Huecos entre funciones (respeta FESTIVAL_BUFFER) ─────────────────────────

test('hueco entre funciones: sugiere lo que cabe, excluye lo que lo excede', () => {
  // Plan D2: 10:00–11:00 y 15:00–16:00. Hueco real con buffer 10: 11:10–14:50.
  const { getSuggestions } = load({
    FILMS: [
      film('Cabe', 'D2', '12:00', '90 min'),      // 12:00–13:30 ✓
      film('SeSale', 'D2', '14:00', '120 min'),   // 14:00–16:00 ✗ (excede 14:50)
    ],
    savedAgenda: { schedule: [
      sched('A', 'D2', '10:00', '60 min'),
      sched('B', 'D2', '15:00', '60 min'),
    ] },
  });
  assert.deepStrictEqual((getSuggestions().D2 || []).map(f => f.title), ['Cabe']);
});

// ── Contrato del gate de entrada ─────────────────────────────────────────────

test('sin plan confirmado (null o schedule vacío) → {} (contrato con Mi Plan)', () => {
  const a = load({ FILMS: [film('F', 'D2', '19:00', '60 min')], savedAgenda: null });
  assert.deepStrictEqual(a.getSuggestions(), {});
  const b = load({ FILMS: [film('F', 'D2', '19:00', '60 min')], savedAgenda: { schedule: [] } });
  assert.deepStrictEqual(b.getSuggestions(), {});
});
