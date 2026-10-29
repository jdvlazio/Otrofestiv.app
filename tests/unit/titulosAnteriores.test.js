// titulosAnteriores — lo guardado bajo el título viejo de una obra renombrada
// pasa al vigente (7 oct 2026, decisión de Juan: sin aviso). Caso real: Villa
// del Cine renombró «Tránsito» → «Tránsitos» (PR #1021) y partió la ceremonia
// de apertura en dos; publicarCatalogo borraba lo guardado bajo el viejo.

const test = require('node:test');
const assert = require('node:assert');
const path = require('node:path');
const { pathToFileURL } = require('node:url');

const cargar = () => import(pathToFileURL(path.join(__dirname, '../../src/domain/titulos.js')).href);

const FILMS = [
  { title: 'Tránsitos', titulos_anteriores: ['Tránsito'] },
  { title: 'Ceremonia UNQUY de apertura', titulos_anteriores: ['Ceremonia UNQUY de apertura y Cine Concierto Caminos Sonoros'] },
  { title: 'Cine Concierto Caminos Sonoros — León Quintero', titulos_anteriores: ['Ceremonia UNQUY de apertura y Cine Concierto Caminos Sonoros'] },
  { title: 'Amor a primera vista' },
];

test('renamesDe: viejo → vigente; si se partió en dos gana la primera', async () => {
  const { renamesDe } = await cargar();
  const ren = renamesDe(FILMS);
  assert.strictEqual(ren.get('Tránsito'), 'Tránsitos');
  assert.strictEqual(ren.get('Ceremonia UNQUY de apertura y Cine Concierto Caminos Sonoros'), 'Ceremonia UNQUY de apertura');
  assert.strictEqual(ren.size, 2);
});

test('renamesDe: un título viejo que sigue vigente no se migra', async () => {
  const { renamesDe } = await cargar();
  const ren = renamesDe([{ title: 'A', titulos_anteriores: ['B'] }, { title: 'B' }]);
  assert.strictEqual(ren.size, 0);
});

test('migrarEstado: mueve Interés, vistas, prioridad, calificación, Plan y retrasos', async () => {
  const { renamesDe, migrarEstado } = await cargar();
  const u = migrarEstado({
    watchlist: new Set(['Tránsito', 'Amor a primera vista']),
    watched: new Set(['Tránsito']), notWatched: new Set(), prioritized: new Set(['Tránsito']),
    filmRatings: { 'Tránsito': 4 },
    filmDelays: { 'Tránsito|2026-10-15|16:00': 10 }, filmDelaysHistory: {},
    savedAgenda: { schedule: [{ _title: 'Tránsito', title: 'Tránsito', day: '2026-10-15', time: '16:00' }] },
    lastRemovedSlots: [],
  }, renamesDe(FILMS));
  assert.deepStrictEqual([...u.watchlist].sort(), ['Amor a primera vista', 'Tránsitos']);
  assert.deepStrictEqual([...u.watched], ['Tránsitos']);
  assert.deepStrictEqual([...u.prioritized], ['Tránsitos']);
  assert.deepStrictEqual(u.filmRatings, { 'Tránsitos': 4 });
  assert.deepStrictEqual(u.filmDelays, { 'Tránsitos|2026-10-15|16:00': 10 });
  assert.strictEqual(u.savedAgenda.schedule[0]._title, 'Tránsitos');
  assert.strictEqual(u.savedAgenda.schedule[0].title, 'Tránsitos');
  assert.ok(!('notWatched' in u) && !('lastRemovedSlots' in u), 'lo que no cambia no se toca');
});

test('migrarEstado: si ya hay algo bajo el título nuevo, manda el nuevo', async () => {
  const { renamesDe, migrarEstado } = await cargar();
  const u = migrarEstado({ filmRatings: { 'Tránsito': 2, 'Tránsitos': 5 } }, renamesDe(FILMS));
  assert.deepStrictEqual(u.filmRatings, { 'Tránsitos': 5 });
});

test('migrarEstado: idempotente y vacío cuando no hay nada que migrar', async () => {
  const { renamesDe, migrarEstado } = await cargar();
  const ren = renamesDe(FILMS);
  const st = { watchlist: new Set(['Tránsito']) };
  const u1 = migrarEstado(st, ren);
  const u2 = migrarEstado({ ...st, ...u1 }, ren);
  assert.deepStrictEqual(u2, {});
  assert.deepStrictEqual(migrarEstado({ watchlist: new Set(['Amor a primera vista']) }, ren), {});
});
