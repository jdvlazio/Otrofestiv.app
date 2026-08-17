#!/usr/bin/env node
// Genera la sección «Films» de docs/SCHEMA.md desde pipeline/contrato.json.
//
// POR QUÉ EXISTE. Hasta el 17 ago 2026 el schema era prosa escrita a mano y se
// desincronizó sin que nada se pusiera rojo: documentaba 24 campos cuando había
// 60, y juraba que `duration` era un número cuando las 1.194 son el string
// «90 min». Quien creyera la doc, sumaba mal. Una doc que se escribe a mano al
// lado de un canon ejecutable es una SEGUNDA FUENTE, y dos fuentes divergen
// siempre; la única defensa es que no haya dos.
//
//   node scripts/generate-schema-md.js           # reescribe la sección
//   node scripts/generate-schema-md.js --check   # falla si está desactualizada (CI)
'use strict';
const fs = require('fs');
const path = require('path');

const RAIZ = path.join(__dirname, '..');
const C = JSON.parse(fs.readFileSync(path.join(RAIZ, 'pipeline', 'contrato.json'), 'utf8'));
const DOC = path.join(RAIZ, 'docs', 'SCHEMA.md');
const INI = '<!-- CONTRATO:INICIO — generado por scripts/generate-schema-md.js, no editar a mano -->';
const FIN = '<!-- CONTRATO:FIN -->';

// Las cuentas se MIDEN de los JSON reales: un campo documentado que ya no usa
// nadie es la otra mitad del problema.
const uso = {};
for (const f of fs.readdirSync(path.join(RAIZ, 'festivals')).filter(x => x.endsWith('.json'))) {
  const d = JSON.parse(fs.readFileSync(path.join(RAIZ, 'festivals', f), 'utf8'));
  for (const film of (d.films || [])) {
    for (const k of Object.keys(film)) {
      (uso[k] = uso[k] || { n: 0, fest: new Set() }).n++;
      uso[k].fest.add(f);
    }
  }
}

const esc = s => String(s).replace(/\|/g, '\\|');
const GRUPOS = [
  ['Obligatorios — sin esto no hay función', e => e[1].obligatorio],
  ['Cómo se entra — la casilla que no se deja en blanco', e => e[1].grupo === 'acceso'],
  ['Todo lo demás', () => true],
];

let out = [INI, '', '## Films — el contrato', '',
  'Esta sección se **genera** de `pipeline/contrato.json`. No se edita a mano: se',
  'edita el contrato y se corre `node scripts/generate-schema-md.js`. El contrato',
  'es lo que `validate-festivals.js` EXIGE, así que lo que leas aquí es lo que',
  'está pasando de verdad — no lo que alguien recordaba al escribirlo.', ''];

const vistos = new Set();
for (const [titulo, filtro] of GRUPOS) {
  const campos = Object.entries(C.campos).filter(e => !vistos.has(e[0]) && filtro(e));
  campos.forEach(e => vistos.add(e[0]));
  if (!campos.length) continue;
  out.push(`### ${titulo}`, '', '| campo | tipo | formato / valores | en uso | notas |', '|---|---|---|---|---|');
  for (const [k, s] of campos) {
    const u = uso[k];
    const forma = s.enum ? s.enum.map(v => `\`${v}\``).join(' · ') : (s.formato ? `\`${esc(s.formato)}\`` : '—');
    const notas = [];
    if (s.derivado_de) notas.push(`**derivado de \`${s.derivado_de}\`** — no viene de ninguna fuente`);
    if (s.lector) notas.push(`no lo lee la vista: ${s.lector}`);
    if (s.exige) notas.push(`exige \`${s.exige}\``);
    if (s.nota) notas.push(s.nota);
    out.push(`| \`${k}\` | ${s.tipo || '—'} | ${forma} | ${u ? `${u.n} · ${u.fest.size} fest` : '—'} | ${esc(notas.join(' ')) || ''} |`);
  }
  out.push('');
}

const pend = C._pendientes || {};
const filas = [];
for (const [campo, fests] of Object.entries(pend)) {
  if (campo === '_doc') continue;
  for (const [fest, info] of Object.entries(fests)) {
    filas.push(`| \`${campo}\` | ${fest} | ${info.incumple} | **${info.migrar_el}** | ${esc(info.motivo)} |`);
  }
}
if (filas.length) {
  out.push('### Excepciones con fecha de caducidad', '',
    'Festivales **vigentes** que aún no cumplen. A partir de la fecha, el validador',
    'deja de perdonar y se pone rojo: **una excepción sin fecha se vuelve permanente',
    'sola; ésta se vence sola.**', '',
    '| campo | festival | incumple | migra el | por qué espera |', '|---|---|---|---|---|',
    ...filas, '');
}

out.push('### Excepciones congeladas (festivales archivados)', '',
  'Su edición ya pasó y reescribir su historia es riesgo sin beneficio. **Esta',
  'lista solo puede encoger**: ningún festival nuevo entra aquí.', '');
for (const [campo, fests] of Object.entries(C._excepciones || {})) {
  if (campo === '_doc') continue;
  out.push(`- \`${campo}\` — ${Object.keys(fests).join(', ')}`);
}
out.push('', FIN);

const texto = out.join('\n');
const doc = fs.readFileSync(DOC, 'utf8');
const i = doc.indexOf(INI), j = doc.indexOf(FIN);
let nuevo;
if (i >= 0 && j > i) nuevo = doc.slice(0, i) + texto + doc.slice(j + FIN.length);
else {
  const anc = doc.indexOf('## Films');
  const fin = doc.indexOf('### Campo `info`');
  if (anc < 0 || fin < 0) { console.error('no encuentro dónde insertar la sección Films'); process.exit(1); }
  nuevo = doc.slice(0, anc) + texto + '\n\n' + doc.slice(fin);
}
if (process.argv.includes('--check')) {
  if (nuevo !== doc) { console.error('✗ docs/SCHEMA.md desactualizado — correr: node scripts/generate-schema-md.js'); process.exit(1); }
  console.log('✓ SCHEMA.md al día con el contrato'); process.exit(0);
}
fs.writeFileSync(DOC, nuevo);
console.log(`✓ docs/SCHEMA.md — ${Object.keys(C.campos).length} campos del contrato`);
