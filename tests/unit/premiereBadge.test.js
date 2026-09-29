// premiereBadge.test.js — el distintivo de UNA palabra que resume `premiere`.
// Casos reales de los festivales publicados. El de Mamut 11 («Inauguración») no
// casaba con /inaugural/ y la inaugural salía sin píldora: lo cazó
// [premiere-sin-badge] el 28 sep 2026, cuando se le arregló un bug que lo
// tenía mudo.
const { test } = require('node:test');
const assert = require('node:assert');

let F;
test.before(async () => { F = await import('../../src/domain/film.js'); });

const casos = [
  ['Inauguración', 'badge_apertura'],          // Mamut 11
  ['Proyección inaugural', 'badge_apertura'],  // Girardota 9
  ['Película de Apertura', 'badge_apertura'],
  ['Opening Night', 'badge_apertura'],
  ['Clausura', 'badge_clausura'],
  ['Estreno nacional', 'badge_estreno'],       // Mamut 11
  ['World Premiere', 'badge_estreno'],
  ['Selección oficial', null],                 // no es un distintivo de estreno
];
for (const [valor, clave] of casos) {
  test(`premiere «${valor}» → ${clave}`, () => {
    assert.strictEqual(F.premiereBadgeKey({ premiere: valor }), clave);
  });
}
test('sin premiere → sin distintivo', () => {
  assert.strictEqual(F.premiereBadgeKey({}), null);
});
