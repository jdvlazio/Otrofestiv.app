// sameEntry — el dueño único de «esta entrada del Plan es aquella».
//
// EL BUG QUE LO MOTIVA (medido en main, 25 ago 2026): la identidad del Plan era
// título+día+hora, sin SEDE. FICDEH programa la misma obra el mismo día y hora
// en ciudades distintas — 13 casos reales. Agendar «La independencia» en Bogotá
// hacía que la app marcara la función de IBAGUÉ como «en tu plan»: a alguien de
// Ibagué le decía que ya tenía una función que nunca agendó, y la que sí quería
// aparecía tomada.
const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

const { sameEntry } = loadDomain({ functions: ['sameEntry'], globals: {} });

// El caso real de FICDEH, con sus dos sedes.
const BOGOTA = { title: 'La independencia', day: '2026-08-13', time: '14:00',
                 venue: 'Biblioteca Pública La Victoria - Bogotá' };
const IBAGUE = { title: 'La independencia', day: '2026-08-13', time: '14:00',
                 venue: 'Centro Cultural Panóptico de Ibagué - Ibagué' };

test('la SEDE separa: misma obra, mismo día y hora, ciudades distintas', () => {
  assert.equal(sameEntry(BOGOTA, IBAGUE), false,
    'sin esto, agendar en Bogotá marcaba la función de Ibagué como planeada');
  assert.equal(sameEntry(BOGOTA, { ...BOGOTA }), true);
});

test('la entrada del Plan usa _title; la del catálogo, title', () => {
  const entrada = { _title: BOGOTA.title, day: BOGOTA.day, time: BOGOTA.time, venue: BOGOTA.venue };
  assert.equal(sameEntry(entrada, BOGOTA), true, 'la entrada guardada y su función viva son la misma');
});

test('TOLERANCIA: si un lado no declara sede, no se exige que coincida', () => {
  // Los planes guardados antes de que la sede viajara en la entrada no la
  // tienen. Endurecer acá los desconectaría del catálogo — la pérdida de datos
  // que este predicado existe para evitar.
  const vieja = { _title: BOGOTA.title, day: BOGOTA.day, time: BOGOTA.time };  // sin venue
  assert.equal(sameEntry(vieja, BOGOTA), true, 'un plan viejo sigue reconociendo su función');
  assert.equal(sameEntry(vieja, IBAGUE), true, 'y no se puede desambiguar: es el precio de no romperlo');
});

test('FALLA CERRADO: sin día u hora no matchea NADA', () => {
  // La versión previa (revertida) matcheaba TODO con los campos ausentes: un
  // llamador que se olvidaba de pasarlos no daba error, borraba en masa.
  const sinDia = { _title: BOGOTA.title, time: BOGOTA.time, venue: BOGOTA.venue };
  const sinHora = { _title: BOGOTA.title, day: BOGOTA.day, venue: BOGOTA.venue };
  assert.equal(sameEntry(sinDia, BOGOTA), false, 'el olvido es un no-op, no una pérdida');
  assert.equal(sameEntry(sinHora, BOGOTA), false);
  assert.equal(sameEntry(null, BOGOTA), false);
  assert.equal(sameEntry(BOGOTA, undefined), false);
});

test('obras distintas nunca son la misma entrada, coincidan día y sede', () => {
  assert.equal(sameEntry(BOGOTA, { ...BOGOTA, title: 'Semillas' }), false);
});
