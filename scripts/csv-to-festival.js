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
  const [, , inPath, outArg] = process.argv;
  if (!inPath) {
    console.error('Uso: node scripts/csv-to-festival.js <input.csv> [output.json]');
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
      has_qa: truthy(get(r, 'has_qa')),
      requires_registration: truthy(get(r, 'requires_registration')),
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
    if (base.has_qa) film.has_qa = true;
    if (base.requires_registration) film.requires_registration = true;
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

  // ── Salida ──
  const out = { venues, films };
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
  console.log(`\n→ Siguiente: geocode-venues.py · generate-config.js · validate-festivals.js\n`);
}

main();
