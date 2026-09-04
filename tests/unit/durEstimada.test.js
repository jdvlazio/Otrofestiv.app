// durEstimada — «¿sabemos cuánto dura?», el compañero honesto de parseDur.
//
// parseDur rellena con DEFAULT_DURATION_MIN (90) cuando el texto no trae número,
// y hasta ahora nada distinguía un 90 real de uno inventado. Sobre ese número la
// app afirmaba la hora de salida, reservaba 90 minutos en el calendario y
// descartaba obras del plan. Medido en el catálogo: 28 registros en 7 festivales
// sin duración (FICMontañas 16, Leviza 4, Vartex 3, y uno suelto en Cinemancia,
// CineAutopsia, FantasoFest y QAFF).
const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

test('durEstimada distingue el 90 inventado del 90 real', () => {
  const { parseDur, durEstimada } = loadDomain({ globals: { DEFAULT_DURATION_MIN: 90 } });

  // lo que NO sabemos: sin texto, vacío, o texto sin un solo dígito
  for (const d of [undefined, null, '', '   ', 'min', 'a confirmar', 'Duración por confirmar']) {
    assert.equal(durEstimada(d), true, `«${d}» no trae duración: es estimada`);
    assert.equal(parseDur(d), 90, `y cae en el relleno de 90`);
  }

  // lo que SÍ sabemos, incluido un 90 de verdad — que no debe confundirse
  for (const [d, min] of [['90 min', 90], ['90', 90], ['105 min', 105], ['8 min', 8], ['~120 min', 120]]) {
    assert.equal(durEstimada(d), false, `«${d}» trae duración`);
    assert.equal(parseDur(d), min);
  }

  // el caso que da nombre al arreglo: un 90 real y un 90 inventado dan el MISMO
  // número y tienen que poder distinguirse, que es justo lo que faltaba
  assert.equal(parseDur('90 min'), parseDur(undefined));
  assert.notEqual(durEstimada('90 min'), durEstimada(undefined));
});
