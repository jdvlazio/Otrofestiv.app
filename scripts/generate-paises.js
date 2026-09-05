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
  'United States of America': 'US',    // la grafía larga que usa TIFF
  'Turkey': 'TR', 'Turquía': 'TR',     // ICU dice «Türkiye»; los catálogos, no
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
  // Errata de imprenta del programa de QAFF Bogotá (SEP 2026): el país es ese.
  // Vivía en la tabla a mano de pipeline/lib.py; al fusionar con esta rama —que
  // hace de esta la fuente ÚNICA— se habría perdido en silencio, y «Estados
  // Unido» habría vuelto a salir sin bandera. Medido antes de fusionar.
  'Estados Unido': 'US',
};

// NO llevan bandera, y es deliberado: Estados que dejaron de existir —Unicode no
// tiene glifo para ellos y poner la del sucesor falsearía la procedencia de la
// obra— y etiquetas que no son un país. Se declaran para que el guardián no las
// persiga y para que nadie las «arregle» mañana.
const SIN_BANDERA = [
  'URSS', 'USSR', 'Yugoslavia', 'Checoslovaquia',
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

// ICU NO es igual en todas las versiones de Node: la 22 trae CLDR 47 y la 20 otra
// más vieja, con nombres distintos. Exigir que el archivo salga byte a byte igual
// ata el repo a la máquina de quien lo generó — CI (Node 20) rechazó una tabla
// perfectamente buena hecha en Node 22.
//
// Así que la tabla solo CRECE: al escribirla se une lo que ya había con lo que
// diga el ICU de turno. Una grafía que una versión conocía no se pierde porque
// otra la haya dejado de nombrar, y reconocer más formas nunca es peor. Lo que no
// se tolera es un CONFLICTO —la misma clave apuntando a dos banderas—, que es lo
// que de verdad significaría un error o una edición a mano.
function unir(stored, fresh) {
  const out = {...stored};
  const choques = [];
  for (const [k, v] of Object.entries(fresh)) {
    if (out[k] && out[k] !== v) { choques.push(`${k}: ${out[k]} (guardado) vs ${v} (ICU ${process.versions.cldr})`); continue; }
    out[k] = v;
  }
  return {out, choques};
}

function leerGuardado() {
  try {
    return JSON.parse(fs.readFileSync('pipeline/paises.json', 'utf8')).paises || {};
  } catch { return {}; }
}

const { mapa: fresco, iso } = construir();
const guardado = leerGuardado();
const { out: mapa, choques: enConflicto } = unir(guardado, fresco);
if (enConflicto.length) {
  console.error('✗ la tabla guardada y el ICU de este Node no coinciden en una clave:');
  for (const x of enConflicto) console.error('   ' + x);
  console.error('  Una de las dos está mal. NO se resuelve solo.');
  process.exit(1);
}



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
  // Se comprueba lo que NO depende de la versión de Node:
  //   · que los dos archivos digan lo mismo (si uno se editó a mano, se ve aquí)
  //   · que no falte nada de lo que este ICU sí sabe
  //   · que las aserciones de DEBE, los alias y los «sin bandera» sigan en pie
  // Que el archivo tenga ADEMÁS grafías que este Node no nombra es normal y
  // correcto: las puso otra versión, y reconocer más formas no es un defecto.
  const errs = [];
  const py = JSON.parse(fs.readFileSync('pipeline/paises.json', 'utf8'));
  const js = fs.readFileSync('src/domain/paises.js', 'utf8');
  const mJs = /export const PAISES = (\{.*?\});/s.exec(js);
  const jsTab = mJs ? JSON.parse(mJs[1]) : null;
  if (!jsTab) errs.push('src/domain/paises.js no expone una tabla legible');
  else if (JSON.stringify(jsTab) !== JSON.stringify(py.paises))
    errs.push('src/domain/paises.js y pipeline/paises.json ya no dicen lo mismo');
  // Faltantes: hay que distinguir DERIVA de BORRADO. Que un ICU más nuevo nombre
  // un país de otra forma y el archivo no la tenga es deriva — se avisa, no se
  // bloquea, o el guardián rompe CI cada vez que GitHub sube el Node. Que falten
  // MUCHAS, o que falte un código ISO (que no depende de ICU: se calcula), es
  // otra cosa: alguien editó el archivo a mano.
  const falta = Object.entries(fresco).filter(([k, v]) => py.paises[k] !== v);
  const isoFalta = falta.filter(([k]) => /^[a-z]{2}$/.test(k));
  const DERIVA_MAX = 15;
  if (isoFalta.length || falta.length > DERIVA_MAX)
    errs.push(`${falta.length} clave(s) ausentes${isoFalta.length ? ` (${isoFalta.length} son códigos ISO, que no dependen de ICU)` : ''}: `
      + falta.slice(0, 5).map(([k, v]) => `${k}→${v}`).join(', ')
      + ' — correr: node scripts/generate-paises.js');
  else if (falta.length)
    console.log(`  · ${falta.length} grafía(s) que este ICU (CLDR ${process.versions.cldr}) nombra `
      + `distinto y la tabla no trae — deriva de versión, no error: `
      + falta.slice(0, 4).map(([k]) => k).join(', '));
  for (const [nombre, esperada] of DEBE)
    if (py.paises[norm(nombre)] !== esperada)
      errs.push(`«${nombre}» debería dar ${esperada} y da ${py.paises[norm(nombre)] || '(nada)'}`);
  for (const s2 of SIN_BANDERA.map(norm))
    if (!py.sin_bandera.includes(s2)) errs.push(`«${s2}» dejó de estar declarado sin bandera`);
  if (errs.length) { for (const e of errs) console.error('✗ ' + e); process.exit(1); }
  console.log(`✓ países en orden · ${claves.length} claves · ${Object.keys(iso).length} regiones `
    + `(ICU CLDR ${process.versions.cldr})`);
} else {
  for (const [p, c] of destinos) fs.writeFileSync(p, c);
  console.log(`✓ ${claves.length} claves (es+en+ISO+alias) · ${Object.keys(iso).length} regiones → ${destinos.map(d => d[0]).join(' · ')}`);
}
