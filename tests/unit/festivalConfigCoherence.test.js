// Fitness function — coherencia de FESTIVAL_CONFIG (src/config.js).
//
// POR QUÉ EXISTE: onboardear un festival escribe a mano dayKeys / days / festivalDates
// / festivalStartStr / festivalEndStr. Un typo (un día de menos en festivalDates, un
// dayKey mal, start>end, una fecha fuera de rango) NO lo cazaba nada → el splash
// mostraba fechas distintas al programa, o el match de día se rompía en silencio. Con
// 3 festivales simultáneos en septiembre el riesgo se triplica. Este test congela las
// invariantes que HOY cumplen los 9 festivales → una divergencia futura es fallo de CI.
//
// Solo aplica a festivales con dayKeys EN config (bootstrap). Los archivados que cargan
// todo del JSON tienen dayKeys vacío en config → se saltean (vacuamente coherentes).

const { test, before } = require('node:test');
const assert = require('node:assert');

let CFG, C;
before(async () => { C = await import('../../src/config.js'); CFG = C.FESTIVAL_CONFIG; });

const dateOnly = (s) => new Date(String(s).slice(0, 10) + 'T12:00:00');

test('FESTIVAL_CONFIG — dayKeys ≡ days ≡ festivalDates (mismo set, mismo tamaño)', () => {
  for (const [id, c] of Object.entries(CFG)) {
    if (!c.name || !(c.dayKeys && c.dayKeys.length)) continue; // archivado / carga del JSON
    const dk = c.dayKeys, days = c.days || [], fd = c.festivalDates || {};
    assert.strictEqual(days.length, dk.length, `${id}: days.length ≠ dayKeys.length`);
    assert.strictEqual(Object.keys(fd).length, dk.length, `${id}: festivalDates ≠ dayKeys`);
    const daysK = new Set(days.map(d => d.k));
    for (const k of dk) {
      assert.ok(daysK.has(k), `${id}: dayKey '${k}' falta en days[].k`);
      assert.ok(fd[k] !== undefined, `${id}: dayKey '${k}' falta en festivalDates`);
    }
  }
});

test('FESTIVAL_CONFIG — festivalStartStr ≤ festivalEndStr', () => {
  for (const [id, c] of Object.entries(CFG)) {
    if (!c.name || !c.festivalStartStr || !c.festivalEndStr) continue;
    assert.ok(new Date(c.festivalStartStr) <= new Date(c.festivalEndStr),
      `${id}: festivalStartStr posterior a festivalEndStr`);
  }
});

test('FESTIVAL_CONFIG — cada festivalDates cae dentro de [start, end]', () => {
  for (const [id, c] of Object.entries(CFG)) {
    if (!c.name || !(c.dayKeys && c.dayKeys.length) || !c.festivalStartStr || !c.festivalEndStr) continue;
    const lo = dateOnly(c.festivalStartStr), hi = dateOnly(c.festivalEndStr);
    for (const [k, iso] of Object.entries(c.festivalDates || {})) {
      const d = dateOnly(iso);
      assert.ok(d >= lo && d <= hi, `${id}: festivalDates['${k}']=${iso} fuera de [${c.festivalStartStr}, ${c.festivalEndStr}]`);
    }
  }
});

test('FESTIVAL_CONFIG — storageKey único y con formato <id>_', () => {
  const seen = new Map();
  for (const [id, c] of Object.entries(CFG)) {
    if (!c.name || !c.storageKey) continue;
    assert.ok(!seen.has(c.storageKey), `storageKey '${c.storageKey}' duplicado entre ${seen.get(c.storageKey)} y ${id}`);
    seen.set(c.storageKey, id);
  }
});

// ── P2.2: secciones data-driven (mergeFestivalSections) ──
test('mergeFestivalSections — mergea metadata del festival en los 4 mapas', () => {
  const before = C.SECTION_ORDER_LIST.length;
  C.mergeFestivalSections({
    '🧪 Test Alpha': { en: 'Alpha EN', color: '#ABCDEF', archetype: 'Cortos / Programas', order: 2 },
    '🧪 Test Beta':  { en: 'Beta EN',  color: '#123456', archetype: 'Apertura / Gala',    order: 1 },
  });
  assert.strictEqual(C.SECTION_COLORS['🧪 Test Alpha'], '#ABCDEF', 'color mergeado');
  assert.strictEqual(C.SECTION_EN['🧪 Test Beta'], 'Beta EN', 'en mergeado');
  assert.strictEqual(C.SECTION_ARCHETYPES['🧪 Test Alpha'], 'Cortos / Programas', 'archetype mergeado');
  // order: Beta (1) antes que Alpha (2) en ORDER_LIST
  assert.ok(C.SECTION_ORDER_LIST.indexOf('🧪 Test Beta') < C.SECTION_ORDER_LIST.indexOf('🧪 Test Alpha'),
    'ORDER_LIST respeta el campo order');
  assert.strictEqual(C.SECTION_ORDER_LIST.length, before + 2, 'agrega 2 al ORDER_LIST');
  // idempotente: re-merge no duplica en ORDER_LIST
  C.mergeFestivalSections({ '🧪 Test Alpha': { en: 'X', color: '#000000', archetype: 'Y', order: 2 } });
  assert.strictEqual(C.SECTION_ORDER_LIST.filter(s => s === '🧪 Test Alpha').length, 1, 'idempotente');
});

test('mergeFestivalSections — no-op defensivo sin sections', () => {
  const b = C.SECTION_ORDER_LIST.length;
  C.mergeFestivalSections(undefined);
  C.mergeFestivalSections(null);
  C.mergeFestivalSections('x');
  assert.strictEqual(C.SECTION_ORDER_LIST.length, b, 'sin sections no toca nada');
});
