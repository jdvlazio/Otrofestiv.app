// ci-camino.js — qué PR se saltea la regresión de la interfaz. La frontera:
// un cambio de CÓDIGO nunca puede ir por el camino de datos.
const test = require('node:test');
const assert = require('node:assert');
const { soloBump, clasificar } = require('../../scripts/ci-camino.js');

const BUMP = `--- a/sw.js\n+++ b/sw.js\n-const BUILD = '202610161211';\n+const BUILD = '202610172103';\n`;
const CODIGO = `--- a/sw.js\n+++ b/sw.js\n-const BUILD = '202610161211';\n+const BUILD = '202610172103';\n+self.skipWaiting();\n`;
const P = ['festivals/', 'pipeline/', 'docs/'];

test('el bump solo es bump', () => assert.strictEqual(soloBump(BUMP), true));
test('bump + una línea de código NO es bump', () => assert.strictEqual(soloBump(CODIGO), false));
test('cambiar un número que no es la versión NO es bump', () =>
  assert.strictEqual(soloBump(`-const T = 30;\n+const T = 90;\n`), false));

test('datos + bump → camino de datos', () =>
  assert.strictEqual(clasificar(['festivals/x.json', 'pipeline/y.py', 'sw.js'], P, () => BUMP).camino, 'datos'));
test('un archivo de la app con código → completo', () => {
  const r = clasificar(['festivals/x.json', 'sw.js'], P, () => CODIGO);
  assert.deepStrictEqual(r, { camino: 'completo', fuera: ['sw.js'] });
});
test('src/ que no es main.js → completo aunque el diff parezca bump', () =>
  assert.strictEqual(clasificar(['src/view/helpers.js'], P, () => BUMP).camino, 'completo'));
test('un spec de Playwright → completo', () =>
  assert.strictEqual(clasificar(['tests/festivals.spec.js'], P, () => '').camino, 'completo'));
