// sala() y venueLabel() — la sala dentro del edificio.
//
// El modelo multisala (una sala = una sede con clave propia, mismo `short`, mismas
// coordenadas) ya resuelve lo importante: dos funciones simultáneas en salas
// distintas son funciones distintas y chocan, encadenarlas no cuesta viaje, y el
// filtro las agrupa por edificio. Lo que faltaba era DECIRLE al asistente a qué
// sala entrar — y eso se adivinaba con un regex que solo entiende números.
const test = require('node:test');
const assert = require('node:assert');
const { loadDomain } = require('../lib/load-domain.js');

const VENUES = {
  // Lo ya montado: la sala vive incrustada en el nombre (FICCI 65, Cinemancia…)
  'Plaza Bocagrande ‒ Sala 3': { short: 'Plaza Bocagrande' },
  'Salón 1 ‒ Miguel Sebastián Guerrero, unibac': { short: 'UNIBAC' },
  // El caso que se perdía: sala con NOMBRE, no número (Cinemateca de Bogotá)
  'Cinemateca Sala Capital': { short: 'Cinemateca de Bogotá' },
  'Cinemateca Sala Capital declarada': { short: 'Cinemateca de Bogotá', room: 'Sala Capital' },
  // Lo declarado gana sobre lo deducido
  'Colombo Sala 2': { short: 'Colombo Americano', room: 'Sala Tulio Ospina' },
  // Sede de una sola sala: no hay nada que decir
  'Teatro Adolfo Mejía': { short: 'Teatro Adolfo Mejía' },
};
const cargar = () => loadDomain({
  functions: ['sala', 'venueLabel', 'vcfg', '_resolveVenue'],
  globals: { FESTIVAL_CONFIG: { f: { venues: VENUES } }, _activeFestId: 'f' },
});

test('sin declarar: se deduce del nombre (los festivales ya montados)', () => {
  const { sala } = cargar();
  assert.strictEqual(sala('Plaza Bocagrande ‒ Sala 3'), 'Sala 3');
  assert.strictEqual(sala('Salón 1 ‒ Miguel Sebastián Guerrero, unibac'), 'Sala 1');
});

test('sala con NOMBRE: el regex no la ve — por eso se puede declarar', () => {
  const { sala } = cargar();
  assert.strictEqual(sala('Cinemateca Sala Capital'), '',
    'sin declarar, una sala no numerada se pierde: el caso real de Tercer Tiempo y FantasoFest');
  assert.strictEqual(sala('Cinemateca Sala Capital declarada'), 'Sala Capital');
});

test('lo declarado manda sobre lo deducido', () => {
  // El nombre dice "Sala 2" pero el festival declara cómo se llama de verdad.
  assert.strictEqual(cargar().sala('Colombo Sala 2'), 'Sala Tulio Ospina');
});

test('sede de una sola sala → vacío, nunca "undefined"', () => {
  const { sala } = cargar();
  assert.strictEqual(sala('Teatro Adolfo Mejía'), '');
  assert.strictEqual(sala('Sede que no existe'), '');
  assert.strictEqual(sala(''), '');
  assert.strictEqual(sala(null), '');
});

// venueLabel — el texto que se lleva al calendario del teléfono. Existe porque el
// ICS y el puente nativo de iOS mandaban cosas distintas: uno la clave cruda (con
// sala), el otro solo el edificio (sin sala). A qué sala entrar no puede depender
// del teléfono.
test('venueLabel: edificio · sala, legible', () => {
  const { venueLabel } = cargar();
  assert.strictEqual(venueLabel('Plaza Bocagrande ‒ Sala 3'), 'Plaza Bocagrande · Sala 3');
  assert.strictEqual(venueLabel('Salón 1 ‒ Miguel Sebastián Guerrero, unibac'), 'UNIBAC · Sala 1',
    'legible, no la clave cruda del JSON');
  assert.strictEqual(venueLabel('Cinemateca Sala Capital declarada'), 'Cinemateca de Bogotá · Sala Capital');
});

test('venueLabel: sin sala, solo el edificio (sin separador colgando)', () => {
  const { venueLabel } = cargar();
  assert.strictEqual(venueLabel('Teatro Adolfo Mejía'), 'Teatro Adolfo Mejía');
  assert.strictEqual(venueLabel('Sede que no existe'), 'Sede que no existe',
    'una sede fuera del mapa se dice tal cual: mejor eso que vacío');
  assert.strictEqual(venueLabel(''), '');
});
