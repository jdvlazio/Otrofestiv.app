#!/usr/bin/env node
/**
 * generate-config.js — Generador de entrada FESTIVAL_CONFIG
 *
 * Uso:
 *   node scripts/generate-config.js \
 *     --id        mujeres2026           \
 *     --name      "Mujeres Film Festival" \   (nombre común/marca — el display usa la 1ª palabra)
 *     --fullname  "Festival Internacional de Cine de Mujeres" \  (nombre OFICIAL completo, verificado en fuente)
 *     --short     MUJERES               \
 *     --city      Circasia              \
 *     --start     2026-08-05            \
 *     --days      5                     \
 *     --storage   mujeres2026_          \
 *     [--priolimit 5]                   \
 *     [--event    "EVENTO,"]            \
 *     [--tz       "-05:00"]             \
 *     [--endtime  "23:00:00"]           \
 *     [--test]                          (marca como grupo 'test')
 *
 * Restricciones del --id:
 *   - Solo letras minúsculas + dígitos, termina en 4 dígitos de año
 *   - Válido:   mujeres2026, bogoshorts2026, jardin2026
 *   - Inválido: Mujeres2026 (mayúscula), mujeres-2026 (guión), mujeres26 (año corto)
 *   El nombre del archivo JSON se deriva del id: mujeres2026 → festivals/mujeres-2026.json
 *
 * Salida: bloque JS listo para pegar en FESTIVAL_CONFIG en src/config.js.
 * Copia la salida entre los comentarios de inserción.
 */

const DAYS_ES      = ['DOM','LUN','MAR','MIÉ','JUE','VIE','SÁB'];
const DAYS_LONG    = ['Domingo','Lunes','Martes','Miércoles','Jueves','Viernes','Sábado'];
const DAYS_EN      = ['SUN','MON','TUE','WED','THU','FRI','SAT'];

const MONTH_ES = {
  '01':'ENE','02':'FEB','03':'MAR','04':'ABR','05':'MAY','06':'JUN',
  '07':'JUL','08':'AGO','09':'SEP','10':'OCT','11':'NOV','12':'DIC',
};

const MONTH_EN = {
  '01':'JAN','02':'FEB','03':'MAR','04':'APR','05':'MAY','06':'JUN',
  '07':'JUL','08':'AUG','09':'SEP','10':'OCT','11':'NOV','12':'DEC',
};

// ── Parse args ────────────────────────────────────────────────────────────────
function parseArgs() {
  const args = process.argv.slice(2);
  const opts = {
    id: null, name: null, fullname: null, short: null, city: null,
    country: 'CO', start: null, days: null, storage: null,
    priolimit: 5, event: 'EVENTO,', tz: '-05:00',
    endtime: '23:00:00', test: false,
  };
  for (let i = 0; i < args.length; i++) {
    const k = args[i].replace(/^--/, '');
    if (k === 'test') { opts.test = true; continue; }
    opts[k] = args[++i];
  }
  return opts;
}

// ── Validate ──────────────────────────────────────────────────────────────────
function validate(opts) {
  const required = ['id','name','fullname','short','city','start','days','storage'];
  const missing = required.filter(k => !opts[k]);
  if (missing.length) {
    console.error('❌  Faltan argumentos obligatorios: ' + missing.map(k => '--'+k).join(', '));
    console.error('\nUso:');
    console.error('  node scripts/generate-config.js \\');
    console.error('    --id mujeres2026 --name "Mujeres Film Festival" \\');
    console.error('    --fullname "Festival Internacional de Cine de Mujeres" --short MUJERES \\');
    console.error('    --city Circasia --start 2026-08-05 --days 5 --storage mujeres2026_');
    process.exit(1);
  }
  if (!/^\d{4}-\d{2}-\d{2}$/.test(opts.start)) {
    console.error('❌  --start debe tener formato YYYY-MM-DD. Ejemplo: 2026-08-05');
    process.exit(1);
  }
  if (isNaN(parseInt(opts.days)) || parseInt(opts.days) < 1) {
    console.error('❌  --days debe ser un número entero ≥ 1');
    process.exit(1);
  }
  if (!/^\w+_$/.test(opts.storage)) {
    console.error('❌  --storage debe terminar en guión bajo. Ejemplo: mujeres2026_');
    process.exit(1);
  }
  if (!/^[a-z][a-z0-9]+\d{4}$/.test(opts.id)) {
    console.error('❌  --id debe ser camelCase + año sin guiones. Ejemplo: mujeres2026');
    process.exit(1);
  }
}

// ── Build day objects ─────────────────────────────────────────────────────────
function buildDays(startStr, numDays) {
  const days = [];
  const [y, m, d] = startStr.split('-').map(Number);
  for (let i = 0; i < numDays; i++) {
    const date = new Date(y, m - 1, d + i);
    const dow  = date.getDay(); // 0=DOM … 6=SÁB
    const num  = date.getDate();
    const lbl  = DAYS_ES[dow];
    const long = DAYS_LONG[dow];
    const key  = `${lbl} ${num}`;
    const iso  = `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;
    const lblEn  = DAYS_EN[dow];
    days.push({ key, iso, lbl, num, long, lblEn });
  }
  return days;
}

// ── Format output ─────────────────────────────────────────────────────────────
function formatConfig(opts, days) {
  const d0   = days[0];
  const dn   = days[days.length - 1];
  const mm0  = d0.iso.slice(5, 7);
  const mmN  = dn.iso.slice(5, 7);
  const mon0 = MONTH_ES[mm0] || mm0;
  const monN = MONTH_ES[mmN] || mmN;
  // Formato consistente con festivales existentes (FICCI: '14\u201319 ABR', AFF: '21\u201329 ABR'):
  // - Mismo mes:    '5\u20139 AGO'
  // - Cruza de mes: '28 SEP\u20132 OCT'
  const datesStr = mm0 === mmN
    ? `${d0.num}\u2013${dn.num} ${mon0}`
    : `${d0.num} ${mon0}\u2013${dn.num} ${monN}`;
  // EN format: APR 21–29 (month before day, EN abbreviation)
  const mon0EN = MONTH_EN[mm0] || mm0;
  const monNEN = MONTH_EN[mmN] || mmN;
  const datesStrEN = mm0 === mmN
    ? `${mon0EN} ${d0.num}\u2013${dn.num}`
    : `${mon0EN} ${d0.num}\u2013${monNEN} ${dn.num}`;
  const year     = parseInt(opts.start.slice(0, 4));
  const endDate  = days[days.length - 1].iso;
  const endStr   = `${endDate}T${opts.endtime}`;

  // eventPosterLabel: "EVENTO," → ['EVENTO','']
  const epParts  = opts.event.split(',');
  const ep0      = (epParts[0] || 'EVENTO').trim();
  const ep1      = (epParts[1] !== undefined ? epParts[1] : '').trim();

  // Day keys ISO (YYYY-MM-DD) — único formato desde Tribeca 2026 (docs/PIPELINE.md
  // "Reglas inmutables"). El formato legacy 'LUN 13' se emitía hasta jul 2026 —
  // descubierto desalineado en el test del pipeline v2 (Tercer Tiempo).
  const MONTH_LONG = {'01':'enero','02':'febrero','03':'marzo','04':'abril','05':'mayo','06':'junio',
    '07':'julio','08':'agosto','09':'septiembre','10':'octubre','11':'noviembre','12':'diciembre'};
  const fd  = days.map(d => `'${d.iso}':'${d.iso}'`).join(',');
  const da  = days.map(d => `{k:'${d.iso}',d:${d.num},lbl:'${d.lbl}'}`).join(',');
  const dk  = days.map(d => `'${d.iso}'`).join(',');
  const ds    = days.map(d => `'${d.iso}':'${d.lbl} ${d.num}'`).join(',');
  const dsen  = days.map(d => `'${d.iso}':'${d.lblEn} ${d.num}'`).join(',');
  const dlong = days.map(d => `'${d.iso}':'${d.long} ${d.num} de ${MONTH_LONG[d.iso.slice(5,7)]}'`).join(',');
  const startStr = `${days[0].iso}T00:00:00`;

  const group = opts.test ? "\n  group:'test'," : '';

  return [
    `'${opts.id}': {`,
    `  name:'${opts.name}',fullName:'${opts.fullname}',shortName:'${opts.short}',`,
    `  city:'${opts.city}',country:'${opts.country}',`,
    `  dates:'${datesStr}',dates_en:'${datesStrEN}',year:${year},timezoneOffset:'${opts.tz}',`,
    `  storageKey:'${opts.storage}',festivalStartStr:'${startStr}',festivalEndStr:'${endStr}',${group}`,
    `  festivalDates:{${fd}},`,
    `  days:[${da}],`,
    `  dayKeys:[${dk}],`,
    `  dayShort:{${ds}},`,
    `  dayShort_en:{${dsen}},`,
    `  dayLong:{${dlong}},`,
    `  prioLimit:${parseInt(opts.priolimit)||5},eventPosterLabel:['${ep0}','${ep1}'],`,
    `  films:null,posters:null,lbSlugs:{}`,
    `},`,
  ].join('\n');
}

// ── Main ──────────────────────────────────────────────────────────────────────
const opts = parseArgs();
validate(opts);
const days   = buildDays(opts.start, parseInt(opts.days));
const output = formatConfig(opts, days);

console.log('\n// ── Pegar en FESTIVAL_CONFIG en src/config.js (antes del cierre }; ) ──────────\n');
console.log(output);
console.log('\n// ─────────────────────────────────────────────────────────────────────────────');
console.log(`\n✅  ${opts.id} generado — ${days.length} días (${days[0].key} → ${days[days.length-1].key})`);
console.log(`   Próximos pasos:`);
console.log(`   1. Pegar el bloque en FESTIVAL_CONFIG en src/config.js`);
console.log(`   2. Crear festivals/${opts.id.replace(/([a-z]+)(\d+)/, '$1-$2')}.json`);
console.log(`   3. node scripts/validate-festivals.js ${opts.id.replace(/([a-z]+)(\d+)/, '$1-$2')}`);
console.log(`   4. QA visual P1-P7\n`);
