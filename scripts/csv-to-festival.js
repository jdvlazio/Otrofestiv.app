#!/usr/bin/env node
/**
 * csv-to-festival.js — Convierte el CSV del organizador (pipeline/csv-template.csv)
 * en JSON canónico de festival ({ venues, films }), compatible con el schema de
 * festivals/*.json y con validate-festivals.js.
 *
 * Uso:
 *   node scripts/csv-to-festival.js <input.csv> [output.json]
 *   (si se omite output, escribe <input-sin-ext>.json)
 *
 * Reglas:
 *   - Agrupa por título: múltiples filas con el mismo title = un film con screenings[].
 *     Una sola fila = film plano (day/time/venue en la raíz, sin screenings[]).
 *   - Deriva `day` desde `date` comparando contra el mapa date→day construido del
 *     propio CSV. Reporta conflictos (mismo date, distinto day). Nunca inventa.
 *   - Normaliza duración: int, "147", "147 min", "~90 min" → "147 min".
 *   - Normaliza comillas tipográficas en títulos (mismo set que normalize-festival-titles.py).
 *   - Tolerante: convierte lo que puede. Reporte de cobertura con warnings por campo
 *     vacío, día inválido, venue sin coords, duplicados, ALLCAPS.
 *   - NO escribe enrichment: poster, synopsis_en, lbSlug, genre. Eso es downstream.
 *   - NO escribe config{}: la config va a src/config.js vía generate-config.js.
 *
 * LÍMITE CONOCIDO — programas con film_list:
 *   El CSV es PLANO (una fila por función) y no puede anidar sub-películas. Por eso
 *   este convertidor maneja films (Tipo 1/1b) y eventos (Tipo 4), pero NO expresa
 *   programas de cortos (`is_cortos` + `film_list`) ni programas combinados
 *   (`is_programa`). Verificado contra cinemancia-2025: sus 19 programas de cortos y
 *   5 combinados saldrían como films planos SIN sus sub-películas.
 *   → Esos programas se autorían a mano en el JSON (Tipo 2/3 de festival-template.json)
 *     DESPUÉS de correr el convertidor. El convertidor cubre el caso común (films +
 *     eventos + multi-función); los programas anidados quedan fuera de su alcance.
 */

const fs = require('fs');
const path = require('path');

// ── Normalización de comillas (paridad con normalize-festival-titles.py) ──────
const QUOTE_MAP = {
  '‘': "'", '’': "'", 'ʼ': "'", 'ʹ': "'",
  '“': '"', '”': '"', '«': '"', '»': '"',
};
function normTitle(s) {
  return String(s == null ? '' : s).replace(/[‘’ʼʹ“”«»]/g, c => QUOTE_MAP[c] || c).trim();
}

// ── Parser CSV mínimo (RFC4180: comillas, comas y saltos dentro de campo) ─────
function parseCSV(text) {
  text = text.replace(/^﻿/, ''); // BOM
  const rows = [];
  let row = [], field = '', inQ = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQ) {
      if (c === '"') {
        if (text[i + 1] === '"') { field += '"'; i++; }
        else inQ = false;
      } else field += c;
    } else if (c === '"') inQ = true;
    else if (c === ',') { row.push(field); field = ''; }
    else if (c === '\r') { /* skip */ }
    else if (c === '\n') { row.push(field); rows.push(row); row = []; field = ''; }
    else field += c;
  }
  if (field.length || row.length) { row.push(field); rows.push(row); }
  // descartar filas totalmente vacías
  return rows.filter(r => r.some(x => x.trim() !== ''));
}

// ── Helpers de campo ──────────────────────────────────────────────────────────
const EMPTY = new Set(['', '—', '-', 'N/A', 'n/a']);
const clean = v => { const s = String(v == null ? '' : v).trim(); return EMPTY.has(s) ? '' : s; };
const truthy = v => /^(true|sí|si|yes|1|x)$/i.test(String(v == null ? '' : v).trim());

function normDuration(v) {
  const s = clean(v);
  if (!s) return { value: '', ok: false };
  const m = s.match(/(\d+)/); // primer número (ignora "~", "min", etc.)
  if (!m) return { value: s, ok: false };  // no se pudo parsear → conserva crudo
  return { value: `${parseInt(m[1], 10)} min`, ok: true };
}

function parseYear(v) {
  const s = clean(v);
  const m = s.match(/(\d{4})/);
  return m ? parseInt(m[1], 10) : null;
}

function isAllcaps(title) {
  const uw = title.split(' ').filter(w => w.length > 2 && /^[A-ZÁÉÍÓÚÑÜ]+$/.test(w));
  return uw.length >= 3;
}

// ── Main ────────────────────────────────────────────────────────────────────
function main() {
  const argv = process.argv.slice(2);
  const flags = new Set(argv.filter(a => a.startsWith('--')));
  const pos = argv.filter(a => !a.startsWith('--'));
  const [inPath, outArg] = pos;
  if (!inPath) {
    console.error('Uso: node scripts/csv-to-festival.js <input.csv> [output.json] [--anclaje|--separadas]');
    console.error('  --anclaje    los slots compartidos son UNA función → sharedSlotIsOneScreening:true');
    console.error('  --separadas  los slots compartidos son funciones separadas (anotar en _SEPARATE de validate.py)');
    process.exit(2);
  }
  const outPath = outArg || inPath.replace(/\.csv$/i, '') + '.json';
  const raw = fs.readFileSync(inPath, 'utf8');
  const matrix = parseCSV(raw);
  if (matrix.length < 2) { console.error('CSV vacío o sin filas de datos.'); process.exit(2); }

  const header = matrix[0].map(h => h.trim());
  const idx = Object.fromEntries(header.map((h, i) => [h, i]));
  const get = (r, k) => (idx[k] === undefined ? '' : (r[idx[k]] || ''));
  const rows = matrix.slice(1).map(r => r);

  const report = { warnings: [], counts: {} };
  const warn = (m) => report.warnings.push(m);
  const bump = (k) => report.counts[k] = (report.counts[k] || 0) + 1;

  // ── Paso 1: mapa date→day desde el CSV + detección de conflictos ──
  const dateToDay = {};
  for (const r of rows) {
    const date = clean(get(r, 'date')), day = clean(get(r, 'day'));
    if (date && day) {
      if (dateToDay[date] && dateToDay[date] !== day) {
        warn(`Conflicto date→day: date='${date}' mapea a '${dateToDay[date]}' y a '${day}'`);
      } else dateToDay[date] = day;
    }
  }

  // ── Paso 2: filas → entradas (resolviendo day) ──
  const venuesSet = new Set();
  const entries = rows.map((r, n) => {
    const title = normTitle(get(r, 'title'));
    if (!title) { warn(`Fila ${n + 2}: sin 'title' — descartada`); bump('rows_sin_title'); return null; }
    let day = clean(get(r, 'day'));
    const date = clean(get(r, 'date'));
    if (!day && date && dateToDay[date]) { day = dateToDay[date]; bump('day_derivado'); }
    if (!day) warn(`"${title}": sin 'day' ni 'date' resoluble`);
    const time = clean(get(r, 'time'));
    if (!time) warn(`"${title}": sin 'time'`);
    const venue = clean(get(r, 'venue'));
    if (!venue) { warn(`"${title}": sin 'venue'`); bump('venue_vacio'); }
    else venuesSet.add(venue);
    if (isAllcaps(title)) { warn(`"${title}": título ALLCAPS — convertir a Title Case (gate de validate)`); bump('allcaps'); }
    return {
      title,
      title_es: normTitle(get(r, 'title_es')),
      type: clean(get(r, 'type')).toLowerCase(),
      director: clean(get(r, 'director')),
      country: clean(get(r, 'country')),
      language: clean(get(r, 'language')),
      year: parseYear(get(r, 'year')),
      duration: get(r, 'duration'),
      premiere: clean(get(r, 'premiere')),
      section: clean(get(r, 'section')),
      flags: clean(get(r, 'flags')),
      synopsis: clean(get(r, 'synopsis_source')),
      synopsis_lang: clean(get(r, 'synopsis_lang')).toLowerCase() || 'es',
      day, date: date ? parseInt(date, 10) : null, time, venue,
      sala: clean(get(r, 'sala')),
      has_qa: truthy(get(r, 'has_qa')),
      qa_type: clean(get(r, 'qa_type')).toLowerCase(),
      requires_registration: truthy(get(r, 'requires_registration')),
      is_free: truthy(get(r, 'is_free')),
      title_orig: normTitle(get(r, 'title_orig')),
      rating: clean(get(r, 'rating')),
      trailer: clean(get(r, 'trailer')),
      competencia: clean(get(r, 'competencia')),
    };
  }).filter(Boolean);

  // ── Paso 3: day_order desde días únicos ordenados ──
  const dayMinDate = {};
  for (const e of entries) if (e.day && e.date != null) dayMinDate[e.day] = Math.min(dayMinDate[e.day] ?? Infinity, e.date);
  const orderedDays = [...new Set(entries.map(e => e.day).filter(Boolean))]
    .sort((a, b) => (dayMinDate[a] ?? 0) - (dayMinDate[b] ?? 0) || String(a).localeCompare(String(b)));
  const dayOrder = Object.fromEntries(orderedDays.map((d, i) => [d, i]));

  // ── Paso 4: agrupar por título → films (+ screenings si multi-función) ──
  const groups = new Map();
  for (const e of entries) { if (!groups.has(e.title)) groups.set(e.title, []); groups.get(e.title).push(e); }

  const films = [];
  for (const [title, group] of groups) {
    // dedupe de slots idénticos (title|day|time)
    const seen = new Set(), fns = [];
    for (const e of group) {
      const slot = `${e.day}|${e.time}`;
      if (seen.has(slot)) { warn(`"${title}": función duplicada (${e.day} ${e.time}) — descartada`); bump('duplicados'); continue; }
      seen.add(slot); fns.push(e);
    }
    fns.sort((a, b) => (a.date ?? 0) - (b.date ?? 0) || String(a.time).localeCompare(String(b.time)));
    const base = fns[0];
    const film = { title };
    if (base.title_es && base.title_es !== title) film.title_es = base.title_es;
    if (base.type && base.type !== 'film') film.type = base.type; // 'film' implícito → se omite
    if (base.director) film.director = base.director; else bump('director_vacio');
    if (base.country) film.country = base.country;
    if (base.language) film.language = base.language;
    if (base.year != null) film.year = base.year;
    const dur = normDuration(base.duration);
    if (dur.value) film.duration = dur.value;
    if (!dur.ok && clean(base.duration)) warn(`"${title}": duración '${base.duration}' no parseable — conservada cruda`);
    if (base.premiere) film.premiere = base.premiere;
    if (base.section) film.section = base.section; else { warn(`"${title}": sin 'section'`); bump('section_vacio'); }
    if (base.flags) film.flags = base.flags;
    if (base.synopsis) film.synopsis = base.synopsis; else bump('synopsis_vacio');
    if (base.synopsis_lang && base.synopsis_lang !== 'es') film.synopsis_lang = base.synopsis_lang;
    // scheduling
    film.day = base.day;
    if (base.date != null) film.date = base.date;
    film.time = base.time;
    if (base.venue) film.venue = base.venue;
    film.day_order = dayOrder[base.day] ?? 0;
    if (base.has_qa) { film.has_qa = true; if (base.qa_type) film.qa_type = base.qa_type; }
    if (base.requires_registration) film.requires_registration = true;
    if (base.is_free) film.is_free = true;
    if (base.title_orig && base.title_orig !== title) film.title_orig = base.title_orig;
    if (base.rating) film.rating = base.rating;
    if (base.trailer) film.trailer = base.trailer;
    if (base.competencia) film.competencia = base.competencia;
    if (base.sala) film.sala = base.sala;
    if (fns.length > 1) {
      film.screenings = fns.map(e => {
        const s = { day: e.day, time: e.time };
        if (e.date != null) s.date = e.date;
        if (e.venue) s.venue = e.venue;
        return s;
      });
    }
    films.push(film);
  }

  // ── Paso 5: venues skeleton (sin coords — geocode-venues.py las llena) ──
  const venues = {};
  for (const v of [...venuesSet].sort()) venues[v] = { short: v };
  if (venuesSet.size) { warn(`${venuesSet.size} venues sin coordenadas — correr scripts/geocode-venues.py`); report.counts.venues = venuesSet.size; }

  // ── GATE DURO: proyecciones conjuntas (doctrina SCHEMA.md, 30 jul 2026) ──────
  // Dos+ obras en el mismo día+hora+sede+sala = decisión OBLIGATORIA contra el
  // programa oficial. Sin decisión NO se emite el JSON: el limbo de Cinemancia
  // (corto+largo tratados como rivales) no se repite. No se auto-deriva — en
  // multisala misma hora+sede puede ser otra sala = otra función.
  const slotMap = new Map();
  for (const e of entries) {
    if (!e.day || !e.time || !e.venue) continue;
    const k = `${e.day}|${e.time}|${e.venue}|${e.sala || ''}`;
    if (!slotMap.has(k)) slotMap.set(k, new Set());
    slotMap.get(k).add(e.title);
  }
  const sharedSlots = [...slotMap.entries()].filter(([, t]) => t.size > 1);
  if (sharedSlots.length && !flags.has('--anclaje') && !flags.has('--separadas')) {
    console.error(`\n⛔ ${sharedSlots.length} slot(s) compartidos SIN modelo decidido — no se emite el JSON.`);
    for (const [k, t] of sharedSlots) console.error(`   · ${k} → ${[...t].join(' + ')}`);
    console.error(`\n  Decidí contra el programa oficial (SCHEMA.md § Proyecciones conjuntas):`);
    console.error(`   1. ¿El festival le puso NOMBRE al conjunto? → modelalo como PROGRAMA (fila is_cortos + film_list), no como filas sueltas.`);
    console.error(`   2. ¿Obras independientes en UNA función? → re-corré con --anclaje (activa sharedSlotIsOneScreening).`);
    console.error(`   3. ¿Funciones de verdad separadas (multisala/paralelas)? → re-corré con --separadas y anotá el slot en _SEPARATE de validate.py.`);
    process.exit(1);
  }

  // ── Salida ──
  const out = { venues, films };
  if (sharedSlots.length && flags.has('--anclaje')) out.sharedSlotIsOneScreening = true;
  fs.writeFileSync(outPath, JSON.stringify(out, null, 2) + '\n', 'utf8');

  // ── Reporte de cobertura ──
  console.log(`\n📋 csv-to-festival — ${path.basename(inPath)} → ${path.basename(outPath)}`);
  console.log(`   films: ${films.length} (de ${entries.length} filas) · venues: ${venuesSet.size}`);
  const c = report.counts;
  console.log(`   cobertura: director ${films.length - (c.director_vacio || 0)}/${films.length} · ` +
              `synopsis ${films.length - (c.synopsis_vacio || 0)}/${films.length} · ` +
              `section ${films.length - (c.section_vacio || 0)}/${films.length}`);
  if (c.day_derivado) console.log(`   days derivados desde date: ${c.day_derivado}`);
  if (c.duplicados) console.log(`   funciones duplicadas descartadas: ${c.duplicados}`);
  if (c.allcaps) console.log(`   ⚠ títulos ALLCAPS (rompen validate): ${c.allcaps}`);
  console.log(`   enrichment NO escrito (downstream): poster, synopsis_en, lbSlug, genre`);
  if (report.warnings.length) {
    console.log(`\n⚠ ${report.warnings.length} warnings:`);
    for (const w of report.warnings) console.log('   · ' + w);
  } else console.log('\n✓ sin warnings');
  if (sharedSlots.length && flags.has('--anclaje'))
    console.log(`   ⚓ anclaje: ${sharedSlots.length} slot(s) compartidos → sharedSlotIsOneScreening:true`);
  if (sharedSlots.length && flags.has('--separadas'))
    console.log(`   ⚠ ${sharedSlots.length} slot(s) compartidos declarados SEPARADOS — anotalos en _SEPARATE de validate.py o [slots-sin-decidir] va a fallar`);

  // ── generate-config.js: comando listo, derivado del propio dato ──
  // Un flujo, no dos pasos sueltos que hay que recordar. Lo derivable va lleno;
  // lo que el CSV no sabe (nombre oficial, ciudad, tz) queda como <placeholder>.
  const _id = path.basename(outPath).replace(/\.json$/i, '').replace(/-/g, '');
  const _isoDays = orderedDays.filter(d => /^\d{4}-\d{2}-\d{2}$/.test(d)).sort();
  const _start = _isoDays[0] || '<YYYY-MM-DD>';
  console.log(`\n→ Siguiente paso (config bootstrap — completar los <placeholders>):`);
  console.log(`   node scripts/generate-config.js --id ${_id} --name "<Nombre>" --fullname "<Nombre oficial completo>" \\`);
  console.log(`     --short <CORTO> --city <Ciudad> --start ${_start} --days ${orderedDays.length} --storage ${_id}_ --tz <±HH:MM del país del festival>`);
  console.log(`\n→ Después: geocode-venues.py · enrich-festival.py (PIPELINE.md manda) · validate-festivals.js · python3 validate.py\n`);
}

main();
