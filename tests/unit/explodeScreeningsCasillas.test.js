// explodeScreenings — toda casilla de la función (docs/FUNCION.md §4) viaja.
// Antes perdía has_qa, qa_type, premiere, ticket_url, requires_registration,
// duration e invitados: el dato estaba en el JSON y la app no lo veía.
const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');
const { explodeScreenings } = loadDomain({ functions: ['explodeScreenings'] });

const CASILLAS = {
  has_qa: true, qa_type: 'presencial', premiere: 'Estreno', ticket_url: 'https://x.co/f1',
  requires_registration: true, duration: '75 min', invitados: ['Ana'],
};

test('las casillas de la función viajan a la función explotada', () => {
  const [s] = explodeScreenings([{ title: 'O', duration: '90 min',
    screenings: [{ day: 'a', time: '19:00', venue: 'V', ...CASILLAS }] }]);
  for (const [k, v] of Object.entries(CASILLAS)) assert.deepStrictEqual(s[k], v, k);
});

test('sin la casilla, queda la de la obra', () => {
  const [s] = explodeScreenings([{ title: 'O', duration: '90 min', has_qa: true,
    screenings: [{ day: 'a', time: '19:00', venue: 'V' }] }]);
  assert.strictEqual(s.duration, '90 min');
  assert.strictEqual(s.has_qa, true);
});
