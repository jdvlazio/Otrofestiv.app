// _sortFestivals — el orden del riel del splash y del selector.
//
// Tiers: en curso → próximos → pasados. Dentro del tier manda la fecha… salvo que
// haya una PRIORIDAD EDITORIAL declarada.
//
// De dónde sale: FINCA y FICDEH 2026 comparten fechas exactas (12–19 AGO) y quién
// salía primero lo decidía un accidente —30 minutos de diferencia en
// festivalEndStr—. Con una alianza oficial (FINCA) y otra parcial (FICDEH), esa
// decisión es editorial: tiene que estar declarada, no emerger del ruido de los
// datos.
const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

const orden = entries => loadDomain({
  functions: ['_sortFestivals', '_classifyFestival'],
  globals: { SIM_TIME: null },
})._sortFestivals(entries, null).map(([id]) => id);

// Mismas fechas, como FINCA y FICDEH. RELATIVAS A HOY, no fijas: con fechas
// escritas a mano el test caducaba solo. Las de FINCA/FICDEH (12–19 AGO 2026)
// eran «en curso» cuando se escribió el test y pasaron a «pasado» el 20 de
// agosto: los dos primeros casos empezaron a fallar sin que nadie tocara nada,
// porque en el tier `past` el orden es el inverso (más reciente primero) y la
// prioridad editorial desempata. El test comprobaba la regla; la fecha fija lo
// convirtió en una bomba de tiempo.
const _dia = n => new Date(Date.now() + n * 864e5).toISOString().slice(0, 10);
const fechas = { festivalStartStr: `${_dia(-1)}T00:00:00`, festivalEndStr: `${_dia(6)}T23:00:00` };
const fin30  = { festivalStartStr: `${_dia(-1)}T00:00:00`, festivalEndStr: `${_dia(6)}T23:30:00` };

test('sin prioridad: manda la fecha (comportamiento de siempre)', () => {
  // el que termina 30 min antes va primero — el accidente que motivó el cambio
  const r = orden([['ficdeh', { name: 'FICDEH', ...fechas }], ['finca', { name: 'FINCA', ...fin30 }]]);
  assert.deepStrictEqual(r, ['ficdeh', 'finca']);
});

test('con prioridad: la alianza oficial va primero pese a la fecha', () => {
  const r = orden([['ficdeh', { name: 'FICDEH', ...fechas }], ['finca', { name: 'FINCA', ...fin30, priority: 1 }]]);
  assert.deepStrictEqual(r, ['finca', 'ficdeh']);
});

test('la prioridad NO salta de tier: un pasado no se cuela entre los vigentes', () => {
  // El tier manda siempre: un festival terminado no vuelve arriba por prioridad.
  const pasado = { name: 'Viejo', priority: 1, festivalStartStr: '2020-01-01T00:00:00', festivalEndStr: '2020-01-05T23:00:00' };
  const r = orden([['viejo', pasado], ['finca', { name: 'FINCA', ...fin30 }]]);
  assert.deepStrictEqual(r, ['finca', 'viejo']);
});

test('entre dos prioridades, gana el número menor', () => {
  const r = orden([['b', { name: 'B', ...fechas, priority: 2 }], ['a', { name: 'A', ...fechas, priority: 1 }]]);
  assert.deepStrictEqual(r, ['a', 'b']);
});
