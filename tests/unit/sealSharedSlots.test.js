// sealSharedSlots — un EVENTO en el bloque es el contenedor, no una obra más.
//
// La suma es la doctrina para OBRAS que comparten función (FINCA: cortos uno
// detrás de otro). Pero FICDEH 2026 tiene cinco «Charlas que Unen» de 180 min
// que proyectan cortos ADENTRO, y la suma le agregaba a la charla lo que ya
// tiene dentro: «Los pliegues de la falda» (18 min, 16:00) quedaba «En curso»
// hasta las 19:32 con un bloque que termina 19:00, y el planificador bloqueaba
// esa media hora de más (auditoría B-2, 2 sep 2026).
//
// Se prueba sobre los JSON reales, no sobre fixtures: son los cinco bloques de
// FICDEH, el de FICMA que NO debe cambiar (taller de 120 + largo de 178 en una
// feria sin sala: el evento no contiene nada, se conserva la suma) y un bloque
// de cortos de FINCA, que es la doctrina original intacta.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const { loadDomain } = require('../lib/load-domain.js');

const ROOT = path.resolve(__dirname, '..', '..');
const prep = loadDomain({ functions: ['parseDur', 'explodeScreenings', 'sealSharedSlots'], globals: { DEFAULT_DURATION_MIN: 90 } });
const cargar = f => {
  const d = JSON.parse(fs.readFileSync(path.join(ROOT, 'festivals', f), 'utf8'));
  const films = prep.explodeScreenings(d.films);
  if (d.sharedSlotIsOneScreening) prep.sealSharedSlots(films);
  return films;
};
const bloque = (films, day, time, venueRx) => films.filter(f => f.day === day && f.time === time && venueRx.test(f.venue || ''));

test('FICDEH: una charla de 180 que proyecta cortos ocupa 180, no 180 + los cortos', () => {
  const films = cargar('ficdeh-2026.json');
  const g = bloque(films, '2026-08-17', '16:00', /Cinemateca de Bogotá/);
  assert.strictEqual(g.length, 3, 'el bloque real tiene dos cortos y una charla');
  assert.ok(g.some(f => f.type === 'event'), 'con un evento adentro');
  for (const f of g) {
    assert.strictEqual(f._slotDur, 180, `${f.title.slice(0, 24)}: el bloque dura lo que dura la charla`);
    assert.strictEqual(f._slotMin, 180, 'sin Q&A: igual');
  }
});

test('FICDEH: los cinco bloques mixtos, todos a la duración de su charla', () => {
  const films = cargar('ficdeh-2026.json');
  const grupos = {};
  films.forEach(f => { if (f._slotKey) (grupos[f._slotKey] ||= []).push(f); });
  const mixtos = Object.values(grupos).filter(g => g.some(f => f.type === 'event') && g.some(f => f.type !== 'event'));
  assert.strictEqual(mixtos.length, 5, 'FICDEH tiene cinco bloques charla + obras');
  for (const g of mixtos) {
    const ev = Math.max(...g.filter(f => f.type === 'event').map(f => prep.parseDur(f.duration)));
    const suma = g.reduce((a, f) => a + prep.parseDur(f.duration), 0);
    assert.strictEqual(g[0]._slotDur, ev, 'el bloque es la charla');
    assert.ok(g[0]._slotDur < suma, 'y es menor que la suma que se calculaba antes');
  }
});

test('FICMA: un taller de 120 junto a un largo de 178 NO es contenedor — se conserva la suma', () => {
  const films = cargar('ficma-2026.json');
  const g = bloque(films, '2026-08-15', '17:00', /Expoferias/);
  assert.strictEqual(g.length, 2);
  for (const f of g) assert.strictEqual(f._slotDur, 298, 'el evento es más corto que la obra: no contiene, se suma como siempre');
});

test('FINCA: un bloque de solo obras sigue siendo la suma (doctrina original intacta)', () => {
  const films = cargar('finca-2026.json');
  const g = Object.values(films.reduce((m, f) => { if (f._slotKey) (m[f._slotKey] ||= []).push(f); return m; }, {}))
    .find(g => g.every(f => f.type !== 'event'));
  assert.ok(g && g.length >= 2, 'hay un bloque de cortos');
  const suma = g.reduce((a, f) => a + prep.parseDur(f.duration), 0);
  for (const f of g) assert.strictEqual(f._slotDur, suma);
});
