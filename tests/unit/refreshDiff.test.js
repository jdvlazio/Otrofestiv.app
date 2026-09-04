// Unit test — clasificarRefresco (domain/refresh-diff.js), el árbitro de la
// capa 2 (refresco de datos en caliente, 24 ago 2026).
//
// POR QUÉ EXISTE: este clasificador decide si un cambio del festival se aplica
// EN SILENCIO (valores), se OFRECE (estructura visible / calendario) o AVISA
// (tu plan). Equivocarse hacia un lado inyecta contenido bajo los dedos del
// usuario (CLS — tocar el botón equivocado); hacia el otro, esconde un cambio
// de sede de una función que el usuario va a caminar 40 minutos para ver.
const { test, before } = require('node:test');
const assert = require('node:assert');

let D;
before(async () => { D = await import('../../src/domain/refresh-diff.js'); });

const F = (title, day, time, venue, extra={}) => ({ title, day, time, venue, ...extra });
const DIAS = ['d1','d2'];
const base = () => [F('Alfa','d1','10:00','Sala 1'), F('Beta','d1','14:00','Sala 2'), F('Alfa','d2','18:00','Sala 1')];
const C = (oldFns, newFns, plan=[], oldDays=DIAS, newDays=DIAS) =>
  D.clasificarRefresco({ oldFns, newFns, oldDays, newDays, plan });

test('sin cambios → nada que hacer', () => {
  const r = C(base(), base());
  assert.equal(r.hay, false);
  assert.equal(r.estructural, false);
  assert.equal(r.valores.length, 0);
  assert.equal(r.plan.length, 0);
});

test('cambio de sede = VALOR (regla 1), nunca estructura', () => {
  const n = base(); n[1] = F('Beta','d1','14:00','Sala 9');
  const r = C(base(), n);
  assert.equal(r.estructural, false, 'una sede nueva no mueve el layout: no es estructura');
  assert.deepEqual(r.valores, [{ title:'Beta', day:'d1', time:'14:00', campo:'venue' }]);
});

test('función que entra o sale = ESTRUCTURA (regla 2)', () => {
  const conAlta = [...base(), F('Gamma','d2','20:00','Sala 3')];
  assert.equal(C(base(), conAlta).estructural, true, 'un alta mueve el layout');
  assert.equal(C(conAlta, base()).estructural, true, 'una baja también');
});

test('cambio de hora = alta+baja para el layout, pero el PLAN lo entiende como horario', () => {
  const n = base(); n[0] = F('Alfa','d1','11:30','Sala 1');
  const r = C(base(), n, [{ title:'Alfa', day:'d1', time:'10:00' }]);
  assert.equal(r.estructural, true, 'para el layout la identidad 10:00 murió');
  assert.deepEqual(r.plan, [{ title:'Alfa', tipo:'horario' }],
    'para el usuario no «se fue»: cambió el horario — decir «retirada» sería falso');
});

test('el calendario cambiado es SIEMPRE estructural, aunque las funciones coincidan', () => {
  const r = C(base(), base(), [], DIAS, ['d1','d2','d3']);
  assert.equal(r.calendario, true);
  assert.equal(r.estructural, true, 'reconstruir la tira de días jamás pasa en silencio');
});

test('el plan distingue sus cuatro hechos: sede, horario, día, retirada', () => {
  const plan = [
    { title:'Alfa', day:'d1', time:'10:00' },
    { title:'Beta', day:'d1', time:'14:00' },
    { title:'Alfa', day:'d2', time:'18:00' },
  ];
  // Alfa d1 se muda de día; Beta cambia de sede; Alfa d2 desaparece del festival…
  // pero Alfa sigue existiendo (d1) → su hecho es «día», no «retirada».
  const n = [F('Alfa','d3','10:00','Sala 1'), F('Beta','d1','14:00','Sala 5')];
  const r = C(base(), n, plan, DIAS, ['d1','d3']);
  const porTitulo = Object.fromEntries(r.plan.map(c => [c.title + '|' + c.tipo, true]));
  assert.ok(porTitulo['Alfa|dia'], 'Alfa d1 → cambió de día');
  assert.ok(porTitulo['Beta|sede'], 'Beta → cambió la sede');
  assert.equal(r.plan.length, 3, 'las tres elecciones del plan reportan su hecho');
});

test('obra que sale entera del festival → «retirada» para quien la tenía en el plan', () => {
  const n = base().filter(f => f.title !== 'Beta');
  const r = C(base(), n, [{ title:'Beta', day:'d1', time:'14:00' }]);
  assert.deepEqual(r.plan, [{ title:'Beta', tipo:'retirada' }]);
});

test('un cambio ajeno al plan NO fabrica avisos de plan', () => {
  const n = base(); n[1] = F('Beta','d1','14:00','Sala 9');
  const r = C(base(), n, [{ title:'Alfa', day:'d1', time:'10:00' }]);
  assert.equal(r.plan.length, 0, 'la sede de Beta no es asunto del plan de Alfa');
});
