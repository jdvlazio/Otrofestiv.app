// screeningEndDate — el fin canónico como instante absoluto, dueño único del
// filtro "esta entrada del plan ya terminó". renderUnconfirmed y
// _updateMiPlanBadge lo reconstruían por separado, y "terminó hace X min" medía
// desde OTRO fin (blockDuration) en la misma frase que el filtro (effective).
const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

function load(){
  return loadDomain({
    functions: ['toMin', 'parseDur', '_festDate', 'blockDuration', 'effectiveDuration', 'screeningEndDate'],
    globals: {
      DEFAULT_DURATION_MIN: 90,
      FESTIVAL_DATES: { D1: '2026-08-13' },
      TZ_OFFSET: '-03:00',
    },
  });
}

test('el fin incluye el Q&A (fin canónico, doctrina del par)', () => {
  const { screeningEndDate } = load();
  const end = screeningEndDate({ day: 'D1', time: '18:00', duration: '80 min', has_qa: true });
  // 18:00 + 80 + 30 = 19:50 en -03:00
  assert.strictEqual(end.toISOString(), new Date('2026-08-13T19:50:00-03:00').toISOString());
});

test('con anclaje usa el fin del slot (_slotMin), no la obra suelta', () => {
  const { screeningEndDate } = load();
  const end = screeningEndDate({ day: 'D1', time: '18:00', duration: '5 min', _slotDur: 111, _slotMin: 141 });
  assert.strictEqual(end.toISOString(), new Date('2026-08-13T20:21:00-03:00').toISOString());
});

test('día desconocido → null (el consumidor filtra)', () => {
  const { screeningEndDate } = load();
  assert.strictEqual(screeningEndDate({ day: 'DX', time: '18:00', duration: '90 min' }), null);
});
