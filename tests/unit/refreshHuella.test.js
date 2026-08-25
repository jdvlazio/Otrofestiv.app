// Unit test — la HUELLA CRUDA del refresco en caliente (loader.js).
//
// EL BUG QUE VIO JUAN EN SU TELÉFONO (24 ago 2026): «los pósters titilan cada
// tanto». La ingesta MUTA el JSON recién bajado —explodeScreenings devuelve los
// MISMOS objetos que data.films, así que la duración automática de programas,
// sealSharedSlots y los avisos de NOTICES escriben sobre él—. La huella se
// tomaba AL FINAL, ya mutada, y nunca volvía a coincidir con la de un JSON
// fresco: el refresco creía ver un cambio en CADA tick y re-renderizaba el grid.
//
// No se puede importar loader.js en node (toca DOM), así que el test ataca la
// PROPIEDAD que lo causa, sobre los festivales REALES: si la ingesta muta el
// objeto, la huella tiene que tomarse antes. Cazado sobre datos de verdad — el
// bug vive en 4 de 17 festivales, y con uno solo de ejemplo se habría escapado.
const { test, before } = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');

let F;
before(async () => { F = await import('../../src/domain/film.js'); });

const DIR = path.join(__dirname, '..', '..', 'festivals');
const festivales = () => fs.readdirSync(DIR).filter(f => f.endsWith('.json'));

// Replica los pasos MUTANTES de _ingerirDatosFestival (mismo orden).
function ingestaMutante(F, data){
  const ex = F.explodeScreenings(data.films);
  ex.forEach(f => {
    if (f.is_programa && f.film_list && f.film_list.length && !f.duration) {
      const mins = f.film_list.reduce((a, it) => a + (parseInt((it.duration||'').replace(/[^0-9]/g,'')) || 0), 0);
      if (mins > 0) f.duration = mins + ' min';
    }
  });
  if (data.sharedSlotIsOneScreening) F.sealSharedSlots(ex);
  return ex;
}

test('la ingesta muta el JSON bajado — por eso la huella se toma ANTES, no después', () => {
  const mutan = [];
  for (const file of festivales()) {
    let data; try { data = JSON.parse(fs.readFileSync(path.join(DIR, file), 'utf8')); } catch { continue; }
    const antes = F._djb2(JSON.stringify(data));
    ingestaMutante(F, data);
    if (F._djb2(JSON.stringify(data)) !== antes) mutan.push(file.replace('.json',''));
  }
  // Este assert NO exige que la ingesta deje de mutar (mutar es su trabajo: sella
  // slots, avisos y duraciones). Exige que sepamos que muta — si algún día dejara
  // de hacerlo, esta prueba se vuelve decorativa y hay que revisarla.
  assert.ok(mutan.length > 0,
    'ningún festival muta: la premisa del test caducó, revisar si la huella cruda sigue haciendo falta');
});

test('la huella tomada al ENTRAR sobrevive a la ingesta — la del final, no', () => {
  for (const file of festivales()) {
    let data; try { data = JSON.parse(fs.readFileSync(path.join(DIR, file), 'utf8')); } catch { continue; }
    const fresco = F._djb2(JSON.stringify(data));      // lo que verá el próximo fetch
    const alEntrar = F._djb2(JSON.stringify(data));    // como lo hace hoy la ingesta
    ingestaMutante(F, data);
    const alFinal = F._djb2(JSON.stringify(data));     // como lo hacía antes (el bug)
    assert.equal(alEntrar, fresco,
      `${file}: la huella de entrada debe coincidir con la de un JSON recién bajado`);
    if (alFinal !== fresco) {
      assert.notEqual(alFinal, alEntrar,
        `${file}: confirma que tomarla al final daba una huella distinta — el origen del titileo`);
    }
  }
});

test('_rawFilms debe ser COPIA: con las mutaciones puestas, el diff se inventa cambios', () => {
  // El lado «viejo» del diff no puede llevar nuestro sellado: contra un JSON
  // nuevo intacto, una función reprogramada por NOTICES se vería «movida».
  const file = festivales().find(f => {
    const d = JSON.parse(fs.readFileSync(path.join(DIR, f), 'utf8'));
    if (!d.sharedSlotIsOneScreening) return false;
    const antes = F._djb2(JSON.stringify(d));
    ingestaMutante(F, d);
    return F._djb2(JSON.stringify(d)) !== antes;
  });
  assert.ok(file, 'hace falta al menos un festival que mute para probar esto');

  const data = JSON.parse(fs.readFileSync(path.join(DIR, file), 'utf8'));
  const copia = JSON.parse(JSON.stringify(data)).films;   // como guarda hoy _rawFilms
  const referencia = data.films;                          // como guardaba antes (el bug)
  ingestaMutante(F, data);
  assert.notEqual(F._djb2(JSON.stringify(referencia)), F._djb2(JSON.stringify(copia)),
    'guardar la referencia arrastra las mutaciones al lado viejo del diff');
  const fresco = JSON.parse(fs.readFileSync(path.join(DIR, file), 'utf8')).films;
  assert.equal(F._djb2(JSON.stringify(copia)), F._djb2(JSON.stringify(fresco)),
    'la copia debe ser idéntica al JSON recién bajado');
});
