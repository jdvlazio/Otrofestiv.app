// countryToFlags — de país a bandera, el motor del lado del app.
//
// Los casos de aquí no son inventados: cada uno se rompió de verdad. «Países
// bajos» con b minúscula mostró un globo en Cinemancia con el festival en curso
// (Juan, 4 sep 2026); «Antigua y Barbuda» se partía por la « y » en dos mitades
// que no son ningún país; a Burkina Faso el primer generador le dio 🇭🇻 porque
// recorría también los códigos difuntos. Un fallo de banderas no rompe nada —
// por eso hace falta el test: la app sigue andando, solo miente en pantalla.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const mod = () => import(path.join(ROOT, 'src', 'domain', 'banderas.js'));

test('el país escrito de cualquier forma da su bandera', async () => {
  const { countryToFlags } = await mod();
  const casos = [
    ['Países Bajos', '🇳🇱'], ['Países bajos', '🇳🇱'], ['países bajos', '🇳🇱'],
    ['Netherlands', '🇳🇱'], ['Holanda', '🇳🇱'], ['NL', '🇳🇱'],
    ['Colombia', '🇨🇴'], ['Estados Unidos', '🇺🇸'], ['EEUU', '🇺🇸'],
    ['United States', '🇺🇸'], ['Rep. Dominicana', '🇩🇴'],
    ['Burkina Faso', '🇧🇫'], ['Benín', '🇧🇯'], ['Myanmar', '🇲🇲'],
    ['Hong Kong', '🇭🇰'], ['Palestina', '🇵🇸'], ['Kosovo', '🇽🇰'],
  ];
  for (const [entra, sale] of casos) {
    assert.strictEqual(countryToFlags(entra), sale, `«${entra}»`);
  }
});

test('un país con « y » o guion en el nombre NO se parte', async () => {
  const { countryToFlags } = await mod();
  for (const [entra, sale] of [
    ['Antigua y Barbuda', '🇦🇬'], ['Bosnia y Herzegovina', '🇧🇦'],
    ['Trinidad y Tobago', '🇹🇹'], ['San Vicente y las Granadinas', '🇻🇨'],
    ['Guinea-Bissau', '🇬🇼'], ['Timor-Leste', '🇹🇱'],
  ]) assert.strictEqual(countryToFlags(entra), sale, `«${entra}»`);
});

test('la coproducción se parte por coma, barra, paréntesis, « y » y guion', async () => {
  const { countryToFlags } = await mod();
  for (const [entra, sale] of [
    ['Francia, Colombia', '🇫🇷🇨🇴'],
    ['Francia/Colombia/Canadá/Portugal', '🇫🇷🇨🇴🇨🇦🇵🇹'],
    ['España (Austria)', '🇪🇸🇦🇹'],
    ['Egipto (Catar, Túnez, Alemania)', '🇪🇬🇶🇦🇹🇳🇩🇪'],
    ['Colombia y México', '🇨🇴🇲🇽'],
    ['Ecuador-Chile-Alemania', '🇪🇨🇨🇱🇩🇪'],
  ]) assert.strictEqual(countryToFlags(entra), sale, `«${entra}»`);
});

test('no se repite la bandera de un país nombrado dos veces', async () => {
  const { countryToFlags } = await mod();
  assert.strictEqual(countryToFlags('Colombia, Colombia, Francia'), '🇨🇴🇫🇷');
});

test('vacío y Estados que ya no existen: globo, nunca una bandera falsa', async () => {
  const { countryToFlags } = await mod();
  for (const x of ['', null, undefined, 'URSS', 'Yugoslavia', 'Varios', 'Marte'])
    assert.strictEqual(countryToFlags(x), '🌍', `«${x}»`);
});

test('la tabla del app y la del pipeline son la MISMA', async () => {
  const { PAISES, SIN_BANDERA } = await import(path.join(ROOT, 'src', 'domain', 'paises.js'));
  const py = JSON.parse(fs.readFileSync(path.join(ROOT, 'pipeline', 'paises.json'), 'utf8'));
  assert.deepStrictEqual(PAISES, py.paises, 'la tabla del app difiere de la del pipeline');
  assert.deepStrictEqual([...SIN_BANDERA].sort(), [...py.sin_bandera].sort());
});

test('todo país de los festivales publicados produce bandera', async () => {
  const { countryToFlags } = await mod();
  const { SIN_BANDERA } = await import(path.join(ROOT, 'src', 'domain', 'paises.js'));
  const dir = path.join(ROOT, 'festivals');
  const mudos = [];
  for (const f of fs.readdirSync(dir).filter(x => x.endsWith('.json'))) {
    const d = JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8'));
    const visto = new Set();
    const walk = o => {
      if (Array.isArray(o)) return o.forEach(walk);
      if (!o || typeof o !== 'object') return;
      // Los bloques de procedencia guardan de DÓNDE salió el campo, no su valor.
      for (const [k, v] of Object.entries(o)) {
        if (k.startsWith('_')) continue;
        if (k === 'country' && typeof v === 'string' && v.trim() && o.title) {
          if (!visto.has(v) && countryToFlags(v) === '🌍') { visto.add(v); mudos.push(`${f}: «${v}»`); }
        } else walk(v);
      }
    };
    walk(d);
  }
  const esperados = mudos.filter(m => {
    const t = m.slice(m.indexOf('«') + 1, -1).normalize('NFD')
      .replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
    return !SIN_BANDERA.has(t);
  });
  assert.deepStrictEqual(esperados, [], 'países que saldrían con globo en pantalla');
});
