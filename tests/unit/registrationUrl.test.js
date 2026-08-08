// registration_url — el formulario de inscripción viaja POR FUNCIÓN.
//
// FICDEH 2026 trae actividades con inscripción obligatoria y cupo limitado (15
// por taller). Sabíamos DECIR que hace falta inscribirse —badge INSCRIPCIÓN y
// aviso «Reservá tu lugar»— pero no DÓNDE, que con 15 cupos es el dato que
// importa.
//
// Es por función y no del festival porque el formulario es específico: el de la
// Master Class de FICDEH se titula «Filmar un país en guerra | 13° FICDEH».
//
// Y no se reusó `ticket_url` a propósito (regla de Juan: «ticket es solo para
// comprar»): un formulario gratuito ahí haría que la ficha dijera «Comprá tu
// entrada» en una actividad de entrada libre.
const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

const explotar = films => loadDomain({ functions: ['explodeScreenings'] }).explodeScreenings(films);

test('sobrevive a la explosión de screenings, función por función', () => {
  const r = explotar([{ title: 'Master Class', screenings: [
    { day: '2026-08-18', time: '2:00 PM', venue: 'Colombo', registration_url: 'https://forms.gle/abc' },
    { day: '2026-08-19', time: '4:00 PM', venue: 'Colombo' },
  ] }]);
  assert.strictEqual(r.length, 2);
  assert.strictEqual(r[0].registration_url, 'https://forms.gle/abc');
  assert.strictEqual(r[1].registration_url, undefined,
    'la otra función no hereda un formulario que no es suyo');
});

test('sin el campo, nada se inventa', () => {
  const r = explotar([{ title: 'Taller', screenings: [{ day: '2026-08-18', time: '2:00 PM', venue: 'X' }] }]);
  assert.strictEqual(r[0].registration_url, undefined);
});

test('el formato plano (sin screenings[]) pasa intacto', () => {
  // Los festivales viejos traen day/time/venue en el film — no deben romperse.
  const r = explotar([{ title: 'Charla', day: '2026-08-18', time: '2:00 PM', venue: 'X',
                        registration_url: 'https://forms.gle/xyz' }]);
  assert.strictEqual(r[0].registration_url, 'https://forms.gle/xyz');
});
