// Unit test — deriveDelayConsensus (src/domain/delays.js), Fase B del retraso
// colaborativo. Contrato: a partir de los reportes vigentes, derivar
// none/tentative/confirmed + mediana de minutos + nº de reporters distintos.
//
// Carga: import() dinámico del módulo ESM (fn pura, sin deps) — patrón de
// poster.test.js, sin el harness load-domain.

const { test, before } = require('node:test');
const assert = require('node:assert');

let D;
before(async () => { D = await import('../../src/domain/delays.js'); });

test('sin reportes → none', () => {
  assert.deepStrictEqual(D.deriveDelayConsensus([]), { state: 'none', delayMin: 0, reporters: 0 });
  assert.deepStrictEqual(D.deriveDelayConsensus(null), { state: 'none', delayMin: 0, reporters: 0 });
});

test('cloudScreeningKey — título|día|hora|sede, tolerante a faltantes', () => {
  assert.strictEqual(D.cloudScreeningKey('Film', 'Mar', '18:00', 'Teatro'), 'Film|Mar|18:00|Teatro');
  assert.strictEqual(D.cloudScreeningKey('Film', 'Mar', '18:00'), 'Film|Mar|18:00|', 'sede faltante → vacía');
  assert.strictEqual(D.cloudScreeningKey(), '|||', 'todo faltante → separadores intactos');
  // la sede desambigua misma peli/día/hora en salas distintas
  assert.notStrictEqual(
    D.cloudScreeningKey('F', 'L', '20:00', 'Sala A'),
    D.cloudScreeningKey('F', 'L', '20:00', 'Sala B'));
});

test('1 reporte → tentative (sin confirmar)', () => {
  const r = D.deriveDelayConsensus([{ reporterId: 'a', delayMin: 20, ageMin: 5 }]);
  assert.equal(r.state, 'tentative');
  assert.equal(r.delayMin, 20);
  assert.equal(r.reporters, 1);
});

test('2 reporters distintos → confirmed, mediana', () => {
  const r = D.deriveDelayConsensus([
    { reporterId: 'a', delayMin: 20, ageMin: 5 },
    { reporterId: 'b', delayMin: 30, ageMin: 5 },
  ]);
  assert.equal(r.state, 'confirmed');
  assert.equal(r.delayMin, 25);
  assert.equal(r.reporters, 2);
});

test('mismo reporter NO infla el quórum (toma el más reciente)', () => {
  const r = D.deriveDelayConsensus([
    { reporterId: 'a', delayMin: 20, ageMin: 9 },
    { reporterId: 'a', delayMin: 30, ageMin: 2 },
  ]);
  assert.equal(r.state, 'tentative');
  assert.equal(r.reporters, 1);
  assert.equal(r.delayMin, 30);
});

test('reporte expirado (ageMin > maxAge) se ignora', () => {
  const r = D.deriveDelayConsensus([
    { reporterId: 'a', delayMin: 20, ageMin: 5 },
    { reporterId: 'b', delayMin: 30, ageMin: 999 },
  ]);
  assert.equal(r.state, 'tentative');
  assert.equal(r.reporters, 1);
});

test('delay 0 (limpiado) no cuenta', () => {
  const r = D.deriveDelayConsensus([{ reporterId: 'a', delayMin: 0, ageMin: 1 }]);
  assert.equal(r.state, 'none');
  assert.equal(r.reporters, 0);
});

test('mediana de 3 reporters', () => {
  const r = D.deriveDelayConsensus([
    { reporterId: 'a', delayMin: 10, ageMin: 1 },
    { reporterId: 'b', delayMin: 20, ageMin: 1 },
    { reporterId: 'c', delayMin: 60, ageMin: 1 },
  ]);
  assert.equal(r.state, 'confirmed');
  assert.equal(r.delayMin, 20);
  assert.equal(r.reporters, 3);
});

test('maxAgeMin configurable', () => {
  const reports = [{ reporterId: 'a', delayMin: 15, ageMin: 90 }];
  assert.equal(D.deriveDelayConsensus(reports, 60).state, 'none');   // 90 > 60 → expira
  assert.equal(D.deriveDelayConsensus(reports, 120).state, 'tentative'); // 90 ≤ 120 → vigente
});
