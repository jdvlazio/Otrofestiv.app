// Unit test — la MINI de la Forma A (mejora 1, auditoría Apple Music 24-25 ago).
//
// POR QUÉ EXISTE: en el chip de 56px el póster entero escalado dejaba la sección
// en 3,3px (ruido que repite la fila). La mini responde con UNA voz — ordinal de
// serie o la MARCA de la obra. El requisito que tumbó la primera versión (Juan:
// «no hay diferenciador, no sirve») es LEY acá: dos obras de la misma sección
// deben distinguirse entre sí.
const { test, before } = require('node:test');
const assert = require('node:assert');

let C, H;
before(async () => {
  globalThis._lang = 'es';
  C = await import('../../src/view/components.js');
  H = await import('../../src/view/helpers.js');
});

const dec = uri => decodeURIComponent(String(uri).split(',')[1] || '');

test('mini — determinista: la misma obra dibuja SIEMPRE la misma marca', () => {
  const a = C._buildPosterMini({ accent:'#7F77DD', title:'Carta Blanca Luciana Decker' });
  const b = C._buildPosterMini({ accent:'#7F77DD', title:'Carta Blanca Luciana Decker' });
  assert.equal(a, b);
});

test('mini — EL DIFERENCIADOR: obras de la misma sección no comparten marca', () => {
  // El requisito de Juan. Mismo accent (misma sección) — solo el título siembra.
  const titulos = ['Carta Blanca Luciana Decker', 'Pere Portabella: legado inmarcesible',
    'Sobre cosas que me han pasado + Verano', '¿Qué historia es ésta y cuál es su final?'];
  const minis = titulos.map(t => C._buildPosterMini({ accent:'#7F77DD', title:t }));
  assert.equal(new Set(minis).size, titulos.length,
    'dos obras vecinas con la misma mini = el bug que tumbó la v1');
});

test('mini — la serie muestra su ordinal, grande y legible', () => {
  const svg = dec(C._buildPosterMini({ accent:'#D85A30', title:'Competencia Nuevas Voces Programa 2', esPrograma:true }));
  assert.ok(/<text[^>]*font-size="75"[^>]*>2</.test(svg), 'el ordinal a 5u (75 en viewBox)');
  assert.ok(!/circle|path d=/.test(svg), 'serie → ordinal, no marca');
});

test('mini — la obra lleva marca (2-3 formas), nunca texto', () => {
  const svg = dec(C._buildPosterMini({ accent:'#7F77DD', title:'Carta Blanca Luciana Decker' }));
  assert.ok(!/<text/.test(svg), 'sin texto: el título vive al lado, en la fila');
  const formas = (svg.match(/<(circle|rect|path)[^>]*fill="#7F77DD"/g) || [])
    .filter(x => !x.includes('height="3.75"'));           // el filete no cuenta
  assert.ok(formas.length >= 2 && formas.length <= 3, `2-3 formas, hay ${formas.length}`);
});

test('mini — conserva la anatomía §6.0: negro de marca, filete, luz de sección', () => {
  const svg = dec(C._buildPosterMini({ accent:'#1D9E75', title:'X' }));
  assert.ok(svg.includes('fill="#0B0A08"'), 'negro de marca');
  assert.ok(/height="3\.75" fill="#1D9E75"/.test(svg), 'filete 0,25u en color de sección');
  assert.ok(svg.includes('stop-opacity=".28"') && svg.includes('#1D9E75'), 'luz de sección');
});

test('getFilmPosterMini — solo sustituye el generativo; lo demás pasa intacto', () => {
  // Póster real (TMDB/asset) → tal cual
  const conPoster = { title:'X', poster:'/assets/x.jpg', section:'💡 Iluminaciones' };
  assert.equal(H.getFilmPosterMini(conPoster), H.getFilmPoster(conPoster));
  // Sorpresa → conserva su «?» (es marca, no eco)
  const sorpresa = { title:'Función sorpresa', section:'💡 Iluminaciones' };
  assert.equal(H.getFilmPosterMini(sorpresa), H.getFilmPoster(sorpresa));
  // Generativo → mini (sin las voces del póster entero)
  const gen = { title:'Obra sin póster', section:'💡 Iluminaciones' };
  const mini = H.getFilmPosterMini(gen);
  assert.notEqual(mini, H.getFilmPoster(gen));
  assert.ok(!dec(mini).includes('ILUMINACIONES'), 'la mini no lleva el rótulo de sección');
});
