// Unit test — la MINI (desde 31 oct 2026 la obra sin ordinal es la boleta vacía:
// las figuras geométricas se eliminaron). Antes: la MINI de la Forma A (mejora 1, auditoría Apple Music 24-25 ago).
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

test('mini — la serie muestra su ordinal, grande y legible', () => {
  const svg = dec(C._buildPosterMini({ accent:'#D85A30', title:'Competencia Nuevas Voces Programa 2', esPrograma:true }));
  assert.ok(/<text[^>]*font-size="75"[^>]*>2</.test(svg), 'el ordinal a 5u (75 en viewBox)');
  assert.ok(!/circle|path d=/.test(svg), 'serie → ordinal, no marca');
});

test('mini — la obra sin ordinal es la BOLETA vacía, sin figuras (Juan, 31 oct 2026)', () => {
  const mini = C._buildPosterMini({ accent:'#7F77DD', title:'Carta Blanca Luciana Decker' });
  assert.equal(mini, C._posterForma({ forma:'boleta', accent:'#7F77DD', title:'', dato:'' }));
  assert.ok(!/<text/.test(dec(mini)), 'sin texto: el título vive al lado, en la fila');
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
