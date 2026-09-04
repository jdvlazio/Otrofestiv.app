#!/usr/bin/env node
/**
 * generate-paises.js — LA fuente de países y banderas, para la app y el pipeline.
 *
 * Había DOS tablas escritas a mano: `_COUNTRY_FLAGS` en la app y `BANDERAS` en
 * pipeline/lib.py. Divergieron, como divergen siempre dos copias: el pipeline
 * normalizaba y la app comparaba exacto, así que «Países bajos» con b minúscula
 * daba 🇳🇱 en el dato y 🌍 en la pantalla. Y ninguna estaba completa: al destapar
 * el guardián aparecieron 23 países mostrando globo en festivales EN CURSO.
 *
 * Ahora las dos se GENERAN de aquí, y un guardián comprueba que no se hayan
 * tocado a mano. Los nombres salen de ICU (Intl.DisplayNames) en español e
 * inglés — no de una lista que alguien mantiene— y la bandera del propio código
 * ISO, que es un cálculo, no un dato que se pueda escribir mal.
 *
 *   node scripts/generate-paises.js          # escribe los dos archivos
 *   node scripts/generate-paises.js --check  # falla si están desincronizados
 */
const fs = require('fs');

// Grafías REALES de nuestros festivales que ICU no reconoce. Cada una sale de
// mirar los datos (175 tokens distintos, 23 sin resolver), no de imaginar.
const ALIAS = {
  'EEUU': 'US', 'EE.UU.': 'US', 'EE UU': 'US', 'USA': 'US', 'Estados Unidos de América': 'US',
  'Inglaterra': 'GB', 'UK': 'GB', 'Gran Bretaña': 'GB',
  'Palestina': 'PS', 'Palestine': 'PS',
  'República Checa': 'CZ', 'Czech Republic': 'CZ', 'Chequia': 'CZ',
  'Arabia Saudita': 'SA',
  'Rep. Dominicana': 'DO', 'República Dominicana': 'DO',
  'Federación Rusa': 'RU', 'Rusia': 'RU',
  'RD Congo': 'CD', 'República Democrática del Congo': 'CD',
  'Democratic Republic of Congo': 'CD', 'Congo-Kinshasa': 'CD',
  'Republic of Korea': 'KR', 'Corea del Sur': 'KR', 'South Korea': 'KR',
  'Hong Kong': 'HK', 'Holanda': 'NL', 'Países bajos': 'NL',
  'Guinea Bissau': 'GW', 'Costa de Marfil': 'CI', 'Bielorrusia': 'BY',
  'Birmania': 'MM', 'Burma': 'MM', 'Timor Oriental': 'TL', 'Cabo Verde': 'CV',
};

// NO llevan bandera, y es deliberado: Estados que dejaron de existir —Unicode no
// tiene glifo para ellos y poner la del sucesor falsearía la procedencia de la
// obra— y etiquetas que no son un país. Se declaran para que el guardián no las
// persiga y para que nadie las «arregle» mañana.
const SIN_BANDERA = [
  'URSS', 'Yugoslavia', 'Checoslovaquia',
  'Varios', 'Iberoamérica', 'Internacional', 'Coproducción',
];

// LA MISMA regla que lib.norm() en Python y que _k() en la app. Que fueran
// distintas es lo que rompió «Rep. Dominicana»: el generador guardaba la clave
// con el punto y el pipeline la buscaba sin él. Tres copias de una regla son
// tres reglas.
const norm = s => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '')
  .toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
const flag = c => String.fromCodePoint(...[...c].map(x => 0x1F1E6 + x.charCodeAt(0) - 65));

// Códigos que ICU nombra pero que NO son un país: la región desconocida y
// macrorregiones. Kosovo (XK) SÍ entra: su bandera no está en el juego
// «recomendado» de Unicode, pero está en los datos desde hace meses y coproduce
// obras reales — dejarlo fuera no lo dibuja mejor, lo borra del crédito.
const NO_PAIS = new Set(['ZZ', 'QO', 'EZ', 'UN']);

// Lo que este generador debe producir, pase lo que pase. Un generador que
// entrega mal en silencio es el mismo fallo que la tabla que sustituye: la
// primera versión daba 🇭🇻 a Burkina Faso porque recorría también los códigos
// difuntos —Alto Volta, Dahomey— cuyo nombre ICU es el del país de hoy.
const DEBE = [
  ['Burkina Faso', '🇧🇫'], ['Benín', '🇧🇯'], ['Curazao', '🇨🇼'], ['Serbia', '🇷🇸'],
  ['Alemania', '🇩🇪'], ['Rusia', '🇷🇺'], ['Reino Unido', '🇬🇧'], ['Zimbabue', '🇿🇼'],
  ['Países bajos', '🇳🇱'], ['Países Bajos', '🇳🇱'], ['Netherlands', '🇳🇱'], ['NL', '🇳🇱'],
  ['EEUU', '🇺🇸'], ['Estados Unidos', '🇺🇸'], ['United States', '🇺🇸'],
  ['Guinea-Bissau', '🇬🇼'], ['Palestina', '🇵🇸'], ['Arabia Saudita', '🇸🇦'],
  ['República Democrática del Congo', '🇨🇩'], ['Corea del Sur', '🇰🇷'],
  ['Rep. Dominicana', '🇩🇴'], ['Kosovo', '🇽🇰'], ['EE.UU.', '🇺🇸'], ['Myanmar', '🇲🇲'], ['Birmania', '🇲🇲'], ['Hong Kong', '🇭🇰'], ['Macao', '🇲🇴'],
  ['China', '🇨🇳'], ['Taiwán', '🇹🇼'], ['Irán', '🇮🇷'], ['Costa de Marfil', '🇨🇮'],
];

// ICU nombra a cuatro con un paréntesis o un prefijo administrativo: «Myanmar
// (Birmania)», «RAE de Hong Kong (China)». Nadie escribe eso en un catálogo. Se
// registra también la forma corta. Lo de DENTRO del paréntesis NO se registra:
// «China» reclamaría la bandera de Hong Kong.
function variantes(n) {
  if (!n) return [];
  const out = [n];
  const sinPar = n.replace(/\s*\([^)]*\)/g, ' ').replace(/\s+/g, ' ').trim();
  if (sinPar && sinPar !== n) out.push(sinPar);
  const m = /^RAE de (.+)$/.exec(sinPar);
  if (m) out.push(m[1]);
  return out;
}

function construir() {
  const es = new Intl.DisplayNames(['es'], { type: 'region' });
  const en = new Intl.DisplayNames(['en'], { type: 'region' });
  const mapa = {};          // clave normalizada → bandera
  const iso = {};           // ISO2 → {es, en, flag}
  const choques = [];
  for (let a = 65; a <= 90; a++) {
    for (let b = 65; b <= 90; b++) {
      const c = String.fromCharCode(a) + String.fromCharCode(b);
      if (NO_PAIS.has(c)) continue;
      // Un código DIFUNTO se canonicaliza a otro: und-HV → BF. ICU le pone el
      // nombre del país de hoy, así que si se deja pisa al código bueno.
      let canon; try { canon = new Intl.Locale('und-' + c).region; } catch { continue; }
      if (canon !== c) continue;
      let ne, ni;
      try { ne = es.of(c); ni = en.of(c); } catch { continue; }
      if (!ne || ne === c) continue;          // sin nombre: no es una región nombrada
      const f = flag(c);
      iso[c] = { es: ne, en: ni, flag: f };
      for (const k of [c, ...variantes(ne), ...variantes(ni)]) {
        if (!k) continue;
        const kk = norm(k);
        // Dos códigos que reclaman el mismo nombre no se resuelven a escondidas.
        if (mapa[kk] && mapa[kk] !== f) { choques.push(`${k}: ${mapa[kk]} vs ${f} (${c})`); continue; }
        mapa[kk] = f;
      }
    }
  }
  for (const [k, c] of Object.entries(ALIAS)) {
    if (!iso[c]) { choques.push(`alias ${k} apunta a ${c}, que no existe`); continue; }
    mapa[norm(k)] = iso[c].flag;
  }
  for (const [nombre, esperada] of DEBE) {
    const dio = mapa[norm(nombre)];
    if (dio !== esperada) choques.push(`«${nombre}» dio ${dio || '(nada)'}, se esperaba ${esperada}`);
  }
  if (choques.length) {
    console.error('✗ el generador no produce lo que debe:');
    for (const x of choques) console.error('   ' + x);
    process.exit(1);
  }
  return { mapa, iso };
}

const { mapa, iso } = construir();
const claves = Object.keys(mapa).sort();

const JS = `// GENERADO por scripts/generate-paises.js — NO editar a mano.
// Nombres de ICU (Intl.DisplayNames) en español e inglés; la bandera sale del
// código ISO, que es un cálculo. El guardián [paises-generados] comprueba que
// este archivo siga siendo el que produce el generador.
//
// La clave va NORMALIZADA (minúsculas, sin tildes): «Países bajos» con b
// minúscula costó un globo en Cinemancia con el festival en curso.
export const PAISES = ${JSON.stringify(mapa)};

// Sin bandera A PROPÓSITO: Estados que ya no existen y etiquetas que no son un
// país. Ver el porqué en scripts/generate-paises.js.
export const SIN_BANDERA = new Set(${JSON.stringify(SIN_BANDERA.map(norm))});
`;

const JSON_PY = JSON.stringify({
  _generado_por: 'scripts/generate-paises.js — no editar a mano',
  _nombres: 'ICU (Intl.DisplayNames) es+en; la bandera se calcula del código ISO',
  paises: mapa, sin_bandera: SIN_BANDERA.map(norm), iso,
}, null, 1);

const destinos = [['src/domain/paises.js', JS], ['pipeline/paises.json', JSON_PY]];
if (process.argv.includes('--check')) {
  let mal = 0;
  for (const [p, c] of destinos) {
    const actual = fs.existsSync(p) ? fs.readFileSync(p, 'utf8') : '';
    if (actual !== c) { console.error(`✗ ${p} no coincide con el generador`); mal++; }
  }
  if (mal) { console.error('  correr: node scripts/generate-paises.js'); process.exit(1); }
  console.log(`✓ países sincronizados · ${claves.length} claves · ${Object.keys(iso).length} regiones`);
} else {
  for (const [p, c] of destinos) fs.writeFileSync(p, c);
  console.log(`✓ ${claves.length} claves (es+en+ISO+alias) · ${Object.keys(iso).length} regiones → ${destinos.map(d => d[0]).join(' · ')}`);
}
