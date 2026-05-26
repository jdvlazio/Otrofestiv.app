#!/usr/bin/env node
/**
 * validate-festivals.js
 * Valida la integridad de los JSONs de festival antes de commit.
 *
 * Uso: node scripts/validate-festivals.js [festival-id]
 * Ejemplo: node scripts/validate-festivals.js aff-2026
 *          node scripts/validate-festivals.js  (valida todos)
 *
 * Exit code 0 = OK | Exit code 1 = errores encontrados
 */

const fs = require('fs');
const path = require('path');

// ── Mapa de países → emoji bandera ───────────────────────────────────────────
const FLAGS_MAP = {
  'Colombia':'🇨🇴','UK':'🇬🇧','Chile':'🇨🇱','Brasil':'🇧🇷','Bolivia':'🇧🇴',
  'México':'🇲🇽','Guatemala':'🇬🇹','Francia':'🇫🇷','EEUU':'🇺🇸','Panamá':'🇵🇦',
  'Venezuela':'🇻🇪','Haití':'🇭🇹','España':'🇪🇸','Argentina':'🇦🇷','Uruguay':'🇺🇾',
  'Perú':'🇵🇪','Ecuador':'🇪🇨','Cuba':'🇨🇺','Paraguay':'🇵🇾','Costa Rica':'🇨🇷',
  'Alemania':'🇩🇪','Italia':'🇮🇹','Portugal':'🇵🇹','Suiza':'🇨🇭','Bélgica':'🇧🇪',
  'Países Bajos':'🇳🇱','Suecia':'🇸🇪','Noruega':'🇳🇴','Dinamarca':'🇩🇰',
  'Polonia':'🇵🇱','Austria':'🇦🇹','Grecia':'🇬🇷','Turquía':'🇹🇷','Israel':'🇮🇱',
  'Irán':'🇮🇷','Corea del Sur':'🇰🇷','Japón':'🇯🇵','China':'🇨🇳','Taiwán':'🇹🇼',
  'India':'🇮🇳','Australia':'🇦🇺','Senegal':'🇸🇳','Palestina':'🇵🇸',
  'Rep. Dominicana':'🇩🇴','Nicaragua':'🇳🇮','Canadá':'🇨🇦','Eslovaquia':'🇸🇰',
  'Estonia':'🇪🇪','Vietnam':'🇻🇳','Bolivia':'🇧🇴','Reino Unido':'🇬🇧',
  'Inglaterra':'🇬🇧','Rumania':'🇷🇴','Hungría':'🇭🇺','Finlandia':'🇫🇮',
  'Namibia':'🇳🇦','Nigeria':'🇳🇬','Marruecos':'🇲🇦','Sudáfrica':'🇿🇦',
  'Estados Unidos':'🇺🇸','Nueva Zelanda':'🇳🇿','USA':'🇺🇸','US':'🇺🇸',
  'Honduras':'🇭🇳','El Salvador':'🇸🇻','Puerto Rico':'🇵🇷','Jamaica':'🇯🇲',
};

// Emojis que NO son banderas de país — usados como sección, no como flags
const NON_FLAG_EMOJIS = new Set([
  '🎬','🎞️','🌐','🌍','🌎','🌊','🎨','⏳','📽️','🏆','⭐','📋','✨','🪶','✊',
  '🎭','🎖️','🏛️','🌙','🌿','💡','🌱','🌸','📖',
]);

// Categorías que legítimamente comparten emoji (subcategorías del mismo concepto)
const SHARED_EMOJI_ALLOWED = ['retrospectiva','retrospect','ciclo','cicl','muestra'];
const isSharedAllowed = (secName) =>
  SHARED_EMOJI_ALLOWED.some(w => secName.toLowerCase().includes(w));

// ── Helpers ──────────────────────────────────────────────────────────────────
function getFlagsFromList(filmList) {
  const seen = [];
  for (const film of filmList) {
    for (const country of (film.country || '').split('/')) {
      const c = country.trim();
      if (c && FLAGS_MAP[c] && !seen.includes(FLAGS_MAP[c])) seen.push(FLAGS_MAP[c]);
    }
  }
  return seen.join('');
}

function sectionEmoji(sec) {
  if (!sec) return '';
  const first = sec.split(' ')[0];
  // Only treat as emoji if it's actually an emoji character (not a word like "Spotlight" or "U.S.")
  const isEmoji = /^\p{Emoji}/u.test(first) && !/^[A-Za-z0-9.]/u.test(first);
  return isEmoji ? first : '';
}

// ── Validar un festival ──────────────────────────────────────────────────────
function validateFestival(fname, data) {
  const errors = [];
  const warnings = [];

  const hasConfigBlock = !!data.config;
  const cfg = data.config || {};
  const films = data.films || [];
  const dayKeys = cfg.dayKeys || [];

  // CONFIG required fields
  // Festivales NUEVOS (desde Mujeres 2026): config en FESTIVAL_CONFIG de src/config.js, no en el JSON.
  // GATE: config{} en el JSON es un error bloqueante desde el pipeline v2.
  if (data.config && Object.keys(data.config).length > 0) {
    errors.push('GATE BLOQUEANTE: config{} presente en el JSON — mover a FESTIVAL_CONFIG en src/config.js y eliminar este bloque');
  }
  // Festivales LEGADOS (FICCI 65, Cinemancia 2025): config en el bloque config{} del JSON.
  if (!hasConfigBlock) {
    warnings.push('Sin bloque config{} — se asume que la configuración está en FESTIVAL_CONFIG en src/config.js (formato nuevo ✓)');
  } else {
    // Solo verificar campos si el JSON tiene bloque config (formato legado)
    const cfgRequired = ['name','shortName','city','dates','storageKey','festivalEndStr'];
    for (const k of cfgRequired) {
      if (!cfg[k]) errors.push(`config.${k} es requerido`);
    }
  }

  // dayKeys must match festivalDates (solo si el JSON define config)
  const festDates = cfg.festivalDates || {};
  for (const k of dayKeys) {
    if (!festDates[k]) errors.push(`dayKeys tiene '${k}' pero festivalDates no lo tiene`);
  }

  // days[].lbl must be in Spanish (MIÉ, JUE, VIE...) not English (WED, THU, FRI...)
  // Si está en inglés, el switch de idioma no puede traducir los días
  const EN_DAYS = ['MON','TUE','WED','THU','FRI','SAT','SUN'];
  const days = data.days || cfg.days || [];
  for (const day of days) {
    if (day.lbl && EN_DAYS.includes(day.lbl.toUpperCase())) {
      errors.push(`days[].lbl '${day.lbl}' está en inglés — debe ser español (LUN/MAR/MIÉ/JUE/VIE/SÁB/DOM). El switch de idioma no funcionará.`);
    }
  }

  // Track sections
  const emojiToSections = {}; // emoji → [section names]
  const sectionStrings = {};  // sec_name → Set of exact strings

  const _seenTitles = new Set();   // title-only: para detectar multi-función (informativo)
  const _seenSlots  = new Set();   // title+day+time: duplicado real (bloqueante)
  for (const film of films) {
    const title = film.title || '?';
    const sec = film.section || '';
    const isEvent = film.type === 'event';
    const isCortos = !!film.is_cortos;

    // ── RULE 1: day must exist in dayKeys ─────────────────────────────────
    if (film.day && dayKeys.length && !dayKeys.includes(film.day)) {
      errors.push(`"${title}": day='${film.day}' no existe en dayKeys`);
    }

    // ── RULE 2: is_cortos must have film_list ─────────────────────────────
    if (isCortos && (!film.film_list || film.film_list.length === 0)) {
      warnings.push(`"${title}": is_cortos:true pero film_list vacío`);
    }

    // ── RULE 3: is_cortos flags must be derived from film_list ────────────
    if (isCortos && film.film_list && film.film_list.length > 0) {
      const derived = getFlagsFromList(film.film_list);
      const current = film.flags || '';
      if (derived && (NON_FLAG_EMOJIS.has(current) || current === '' || current === 'Varios')) {
        warnings.push(`"${title}": flags='${current}' debería ser '${derived}' (derivado de film_list)`);
      }
    }

    // ── RULE 4: section emoji uniqueness ──────────────────────────────────
    if (sec) {
      const emoji = sectionEmoji(sec);
      const secName = sec.slice(emoji.length).trim();
      if (emoji) {
        // Solo advertir si el emoji de sección ES una bandera de país (regional indicators)
        // Los emojis decorativos (🌟, 📹, 🎬, etc.) son válidos como identificadores de sección
        const isFlagEmoji = /^\p{Regional_Indicator}\p{Regional_Indicator}/u.test(emoji);
        if (isFlagEmoji) {
          const secNameLower = secName.toLowerCase();
          const isCountrySection = ['muestra','comp.','casa','cortos','cine'].some(w => secNameLower.includes(w));
          if (!isCountrySection) {
            warnings.push(`"${title}": sección usa emoji de bandera como identificador: ${emoji}`);
          }
        }
      }
      if (emoji) {
        if (!emojiToSections[emoji]) emojiToSections[emoji] = new Set();
        emojiToSections[emoji].add(secName);
      }
      if (secName) {
        if (!sectionStrings[secName]) sectionStrings[secName] = new Set();
        sectionStrings[secName].add(sec);
      }
    }

    // ── RULE 5: required film fields ──────────────────────────────────────
    if (!film.day) errors.push(`"${title}": campo 'day' requerido`);
    if (!film.time) errors.push(`"${title}": campo 'time' requerido`);
    if (!film.venue) warnings.push(`"${title}": campo 'venue' vacío`);
    if (!film.section) warnings.push(`"${title}": campo 'section' vacío`);
    if (film.day_order === undefined) warnings.push(`"${title}": falta 'day_order'`);

    // ── RULE 5a: duplicado real (mismo título+día+hora) ──────────────────
    if (film.title) {
      _seenTitles.add(film.title);
      const _slot = `${film.title}|${film.day||''}|${film.time||''}`;
      if (_seenSlots.has(_slot)) errors.push(`GATE BLOQUEANTE: funcion duplicada (mismo título+día+hora) — '${film.title.slice(0,55)}'`);
      else _seenSlots.add(_slot);
    }
    // ── RULE 5b: titulo en ALLCAPS ───────────────────────────────────────
    if (film.title) {
      const _ws = film.title.split(' ');
      const _uw = _ws.filter(w => w.length > 2 && /^[A-ZÁÉÍÓÚÑÜ]+$/.test(w));
      if (_uw.length >= 3) {
        errors.push(`GATE BLOQUEANTE: titulo ALLCAPS — '${film.title.slice(0,55)}' — convertir a Title Case`);
      }
    }
    // ── RULE 6: event without type:event ──────────────────────────────────
    if (!isEvent && !isCortos && !film.director) {
      const secLower = (sec || '').toLowerCase();
      const isEventSec = ['industry','taller','panel','workshop','masterclass',
        'clausura','inaugurac','conferencia','ceremonia','academia'].some(w => secLower.includes(w));
      if (isEventSec) {
        warnings.push(`"${title}": parece un evento (sección=${sec}) pero no tiene type:'event'`);
      }
    }

    // ── RULE 7: flags con non-flag emojis ────────────────────────────────
    if (!isEvent && !isCortos && film.flags) {
      for (const char of [...film.flags]) {
        if (NON_FLAG_EMOJIS.has(char)) {
          warnings.push(`"${title}": flags='${film.flags}' contiene emoji no-bandera '${char}'`);
          break;
        }
      }
    }

    // ── RULE 8: screenings[] integridad ──────────────────────────────────
    // Aplica a festivales con múltiples funciones por film (formato Tribeca/Jardín)
    if (Array.isArray(film.screenings) && film.screenings.length) {
      const _venues = data.venues || {};
      const _hasVenues = Object.keys(_venues).length > 0;
      film.screenings.forEach((s, i) => {
        if (!s.day && !s.date) {
          errors.push(`"${title}": screenings[${i}] no tiene 'day' ni 'date' — mostraría UNDEFINED en UI`);
        }
        if (_hasVenues && s.venue && !_venues[s.venue]) {
          warnings.push(`"${title}": screenings[${i}].venue "${s.venue}" no está en venues{}`);
        }
      });
    }
  }
  // ════════ CHECKS DE CORRUPCIÓN (revisión crítica Olhar — detectan dato MALO, no solo ausente) ════════
  // [posters-duplicados] ERROR — dos films con TÍTULO DISTINTO y misma URL de poster.
  // (El mismo título repetido = misma película en formato 1-entrada-por-función, legítimo.
  //  La comparación de título es case-insensitive: difiere solo en mayúsculas = mismo film.)
  {
    const norm = t => (t || '?').trim().toLowerCase();
    const seen = new Map();
    for (const f of films) {
      const p = (f.poster || '').trim();
      if (!p) continue;
      if (seen.has(p) && seen.get(p).n !== norm(f.title)) errors.push(`[posters-duplicados] "${(f.title||'?').slice(0,40)}" comparte poster con "${seen.get(p).t.slice(0,40)}" (título distinto) — dato corrupto`);
      else if (!seen.has(p)) seen.set(p, { n: norm(f.title), t: f.title || '?' });
    }
  }
  // [sinopsis-duplicada] ERROR — dos films con TÍTULO DISTINTO y misma synopsis o synopsis_en.
  for (const fld of ['synopsis', 'synopsis_en']) {
    const norm = t => (t || '?').trim().toLowerCase();
    const seen = new Map();
    for (const f of films) {
      const s = (f[fld] || '').trim();
      if (!s) continue;
      if (seen.has(s) && seen.get(s).n !== norm(f.title)) errors.push(`[sinopsis-duplicada] "${(f.title||'?').slice(0,40)}" comparte ${fld} con "${seen.get(s).t.slice(0,40)}" (título distinto) — cross-contaminación`);
      else if (!seen.has(s)) seen.set(s, { n: norm(f.title), t: f.title || '?' });
    }
  }
  // [year-sospechoso] WARNING — year > festival_year+1 y el film no es clásico/retro declarado
  {
    const festYear = data.year || 0;
    for (const f of films) {
      if (typeof f.year === 'number' && festYear && f.year > festYear + 1) {
        const isClassic = /cl[aá]ssic|retro|classic/i.test(f.section || '');
        if (!isClassic) warnings.push(`[year-sospechoso] "${(f.title||'?').slice(0,40)}": year=${f.year} > ${festYear+1} y sección no es clásico/retro — posible outlier`);
      }
    }
  }
  // [slot-sin-agrupar] WARNING — ≥2 films distintos en el mismo (day,time,venue) sin is_cortos/is_programa
  {
    const slotMap = {};
    for (const f of films) {
      const isProg = !!(f.is_cortos || f.is_programa);
      const scr = (Array.isArray(f.screenings) && f.screenings.length)
        ? f.screenings : [{ day: f.day, time: f.time, venue: f.venue }];
      for (const s of scr) {
        const key = `${s.day||''}|${s.time||''}|${s.venue||''}`;
        if (key === '||') continue;
        (slotMap[key] = slotMap[key] || []).push({ t: f.title || '?', isProg });
      }
    }
    for (const [key, list] of Object.entries(slotMap)) {
      const uniq = [...new Set(list.map(x => x.t))];
      if (uniq.length >= 2 && !list.some(x => x.isProg)) {
        warnings.push(`[slot-sin-agrupar] ${uniq.length} films comparten slot (${key}) sin is_cortos/is_programa: ${uniq.slice(0,4).map(t=>t.slice(0,22)).join(', ')} — posible programa sin modelar`);
      }
    }
  }
  // [sinopsis-truncada] WARNING — exactamente 200 chars (huella de og:description truncada — trampa A2)
  for (const f of films) {
    for (const fld of ['synopsis', 'synopsis_en']) {
      if ((f[fld] || '').length === 200) warnings.push(`[sinopsis-truncada] "${(f.title||'?').slice(0,40)}": ${fld} tiene exactamente 200 chars — posible og:description truncada`);
    }
  }

  const venuesDef = data.venues || {};
  const venueKeys = Object.keys(venuesDef);
  for (const [vname, vdata] of Object.entries(venuesDef)) {
    const hasLat = vdata.lat !== null && vdata.lat !== undefined;
    const hasLng = vdata.lng !== null && vdata.lng !== undefined;
    if (hasLat && !hasLng) {
      errors.push(`venue "${vname}": tiene lat pero falta lng — geocoding incompleto. Correr scripts/geocode-venues.py`);
      totalErrors++;
    }
    if (!hasLat && hasLng) {
      errors.push(`venue "${vname}": tiene lng pero falta lat — geocoding incompleto`);
      totalErrors++;
    }
    if (!hasLat && !hasLng) {
      warnings.push(`venue "${vname}": sin coordenadas GPS — travelWarn usará tiempo por defecto`);
    }
  }

  // ── RULE 9: film.venue match en venues{} ─────────────────────────────────
  // Garantiza que el worker (exact match) y el main thread (prefix) coincidan
  const sortedKeys = [...venueKeys].sort((a,b) => b.length - a.length);
  function findVenueKey(v) {
    if (venuesDef[v]) return v;
    return sortedKeys.find(k => v.startsWith(k) || v.includes(k)) || null;
  }
  if (venueKeys.length > 0) {
    for (const film of data.films || []) {
      const v = film.venue;
      if (!v) continue;
      if (!venuesDef[v]) {
        // No exact match — check prefix
        const prefixMatch = findVenueKey(v);
        if (!prefixMatch) {
          errors.push(`"${(film.title||'?').slice(0,40)}": venue "${v}" no encontrado en venues{}`);
          totalErrors++;
        } else {
          warnings.push(`"${(film.title||'?').slice(0,40)}": venue "${v}" → prefix match a "${prefixMatch}" (worker usará prefix match)`);
        }
      }
    }
  }

  // ── RULE 9: i18n key parity ──────────────────────────────────────────────────
  // Los archivos es.json y en.json deben tener exactamente las mismas claves.
  // Una clave faltante produce strings en inglés cuando el usuario tiene ES.
  try {
    const repoRoot = path.join(__dirname, '..');
    const esPath = path.join(repoRoot, 'i18n', 'es.json');
    const enPath = path.join(repoRoot, 'i18n', 'en.json');
    if (fs.existsSync(esPath) && fs.existsSync(enPath)) {
      const esKeys = new Set(Object.keys(JSON.parse(fs.readFileSync(esPath, 'utf8'))));
      const enKeys = new Set(Object.keys(JSON.parse(fs.readFileSync(enPath, 'utf8'))));
      const missingInEs = [...enKeys].filter(k => !esKeys.has(k));
      const missingInEn = [...esKeys].filter(k => !enKeys.has(k));
      if (missingInEs.length) {
        errors.push(`i18n: ${missingInEs.length} claves en en.json faltan en es.json: ${missingInEs.slice(0,5).join(', ')}${missingInEs.length>5?'…':''}`);
      }
      if (missingInEn.length) {
        errors.push(`i18n: ${missingInEn.length} claves en es.json faltan en en.json: ${missingInEn.slice(0,5).join(', ')}${missingInEn.length>5?'…':''}`);
      }
    }
  } catch(e) { /* i18n files optional */ }

  // ── RULE 4 (cont): check emoji clashes ───────────────────────────────────
  for (const [emoji, secNames] of Object.entries(emojiToSections)) {
    if (secNames.size > 1) {
      const names = [...secNames];
      const allShared = names.every(isSharedAllowed);
      if (!allShared) {
        errors.push(`Emoji '${emoji}' compartido por secciones distintas: ${names.map(s=>`'${s}'`).join(', ')}`);
      }
      // Retrospectivas y ciclos pueden compartir emoji — solo warning
      else {
        warnings.push(`Emoji '${emoji}' compartido por subcategorías (permitido): ${names.map(s=>`'${s}'`).join(', ')}`);
      }
    }
  }

  // ── RULE 8: section string must be identical across all films ─────────────
  for (const [secName, strings] of Object.entries(sectionStrings)) {
    if (strings.size > 1) {
      errors.push(`Sección '${secName}' tiene strings distintos: ${[...strings].map(s=>`'${s}'`).join(' | ')}`);
    }
  }

  // ── [i18n-content-coverage] WARNING — cobertura de traducción de CONTENIDO ──
  // Detecta huecos de localización en el contenido del festival (no en strings de
  // UI). Solo WARNING, no bloquea. Reporta conteos por festival. No corrige nada.
  {
    const solos = (data.films || []).filter(f =>
      f.type !== 'event' && !f.is_cortos && !f.is_programa);
    const withSyn = solos.filter(f => f.synopsis);

    // (a) synopsis_es faltante cuando el origen no es español (synopsis_lang !== 'es')
    const needEs = withSyn.filter(f => (f.synopsis_lang || '') !== 'es');
    const missEs = needEs.filter(f => !f.synopsis_es);
    if (missEs.length) {
      const langs = [...new Set(needEs.map(f => f.synopsis_lang || '(no declarado)'))];
      const note = langs.length === 1 && langs[0] !== '(no declarado)'
        ? `origen ${langs[0]} — requiere traducción ES`
        : `synopsis_lang ${langs.join('/')} — verificar idioma de origen`;
      warnings.push(`[i18n-content-coverage] ${missEs.length}/${needEs.length} films sin synopsis_es (${note})`);
    } else if (needEs.length) {
      warnings.push(`[i18n-content-coverage] synopsis_es: 0/${needEs.length} films sin synopsis_es ✓`);
    }

    // (b) synopsis_en faltante cuando existe synopsis
    const missEn = withSyn.filter(f => !f.synopsis_en);
    if (missEn.length) {
      warnings.push(`[i18n-content-coverage] ${missEn.length}/${withSyn.length} films sin synopsis_en`);
    }

    // (c) title_en faltante cuando el festival usa title_en (tiene al menos uno)
    const festUsesTitleEn = solos.some(f => f.title_en);
    if (festUsesTitleEn) {
      const missTitleEn = solos.filter(f => !f.title_en);
      if (missTitleEn.length) {
        warnings.push(`[i18n-content-coverage] ${missTitleEn.length}/${solos.length} films sin title_en (el festival usa title_en)`);
      }
    }

    // (d) secciones sin section_en — informativo (no bloqueante todavía)
    const secs = [...new Set((data.films || [])
      .map(f => (f.section || '').replace(/^[\p{Emoji}️\s]+/u, '').trim())
      .filter(Boolean))];
    const secsSinEn = secs.filter(() => true); // ningún festival tiene section_en aún
    if (secsSinEn.length) {
      warnings.push(`[i18n-content-coverage] ${secsSinEn.length} secciones sin traducción (section_en) [info]: ${secsSinEn.join(' · ')}`);
    }
  }

  return { errors, warnings };
}

// ── Main ─────────────────────────────────────────────────────────────────────
const festivalsDir = path.join(__dirname, '..', 'festivals');
const targetId = process.argv[2]; // optional: validate single festival

const files = fs.readdirSync(festivalsDir)
  .filter(f => f.endsWith('.json') && !f.startsWith('_'))
  .filter(f => !targetId || f === targetId + '.json' || f === targetId);

if (files.length === 0) {
  console.error(`No se encontró festival: ${targetId}`);
  process.exit(1);
}

let totalErrors = 0;
let totalWarnings = 0;
const results = [];

for (const fname of files) {
  const fpath = path.join(festivalsDir, fname);
  let data;
  try {
    data = JSON.parse(fs.readFileSync(fpath, 'utf8'));
  } catch (e) {
    console.error(`✗ ${fname}: JSON inválido — ${e.message}`);
    totalErrors++;
    continue;
  }

  const { errors, warnings } = validateFestival(fname, data);

  // ── Poster coverage check ─────────────────────────────────────────────────
  // Un festival sin posters reales sale con todos los placeholders generativos.
  // Esto no es un error (generativo es el fallback válido) pero sí es un warning.
  const filmableFilms = (data.films || []).filter(f =>
    f.type !== 'event' && !f.is_cortos
  );
  const filmsWithPoster = filmableFilms.filter(f => f.poster && f.poster !== '');
  const legacyPosters   = Object.keys(data.posters || {}).length;
  const totalPosters    = filmsWithPoster.length + legacyPosters;
  if (filmableFilms.length > 0) {
    const _pPct = Math.round(totalPosters / filmableFilms.length * 100);
    if (totalPosters === 0) {
      errors.push(`GATE BLOQUEANTE: cobertura de poster 0% — ${filmableFilms.length} films sin imagen. Ejecutar scraping og:image + TMDB estricto.`);
    } else if (_pPct < 95) {
      warnings.push(`Cobertura de poster: ${_pPct}% (${totalPosters}/${filmableFilms.length}) — recomendado ≥95%. Revisar films sin imagen.`);
    }
  }

  // ── Genre coverage ≥ 80% ─────────────────────────────────────────────────
  const _auditFilms = (data.films || []).filter(f => f.type !== 'event' && !f.is_cortos && !f.title?.startsWith('Shorts:'));
  const _withGenre  = _auditFilms.filter(f => f.genre && f.genre.trim());
  if (_auditFilms.length > 0) {
    const _gPct = Math.round(_withGenre.length / _auditFilms.length * 100);
    if (_gPct < 80) warnings.push(`Cobertura de género: ${_gPct}% (${_withGenre.length}/${_auditFilms.length}) — recomendado ≥80%. Ejecutar enriquecimiento TMDB estricto.`);
  }
  // ── Duration anomalies ────────────────────────────────────────────────────
  for (const f of (data.films || [])) {
    if (!f.duration && f.duration !== 0) continue;
    const _d = parseInt(String(f.duration).replace(/[^0-9]/g,''));
    if (!isNaN(_d) && (_d <= 0 || _d > 400)) warnings.push(`Duración anómala: '${(f.title||'').slice(0,40)}' — ${f.duration}`);
  }
  totalErrors += errors.length;
  totalWarnings += warnings.length;
  results.push({ fname, errors, warnings });
}

// ── Cross-festival checks ────────────────────────────────────────────────────
let hasIssues = false;
// storageKey debe ser único entre todos los festivales — colisión = datos mezclados.
// NOTA: festivales nuevos (sin config{} en JSON) tienen storageKey en FESTIVAL_CONFIG.
// Esta check solo cubre festivales legados con config{} en el JSON.
const storageKeyMap = {}; // storageKey → [fnames that use it]
for (const { fname } of results) {
  const fpath = path.join(festivalsDir, fname);
  try {
    const data = JSON.parse(fs.readFileSync(fpath, 'utf8'));
    const sk = (data.config || {}).storageKey;
    if (sk) {
      if (!storageKeyMap[sk]) storageKeyMap[sk] = [];
      storageKeyMap[sk].push(fname);
    }
  } catch (e) { /* JSON parse errors already reported above */ }
}
const skErrors = [];
for (const [sk, fnames] of Object.entries(storageKeyMap)) {
  if (fnames.length > 1) {
    skErrors.push(`storageKey '${sk}' compartida por: ${fnames.join(', ')}`);
    totalErrors++;
  }
}
if (skErrors.length) {
  hasIssues = true;
  console.log('\n── Cross-festival ──');
  for (const e of skErrors) console.log(`  ✗ ERROR:   ${e}`);
}

// ── [poster-editorial-unique] + Output (async: importa makeProgramPoster ESM) ──
(async () => {
  // [poster-editorial-unique] ERROR — dos programas (is_cortos/is_programa) del
  // MISMO festival que renderizan un poster editorial generativo IDÉNTICO.
  // Usa la función REAL makeProgramPoster (no una réplica) → cero falsos positivos:
  // si dos programas se ven iguales, es un error real. Solo aplica a programas SIN
  // poster propio (los que efectivamente rinden el editorial generativo).
  let makeProgramPoster = null;
  try {
    const _cu = require('url').pathToFileURL(path.join(__dirname, '..', 'src', 'view', 'components.js')).href;
    ({ makeProgramPoster } = await import(_cu));
  } catch (e) {
    console.error(`⚠ [poster-editorial-unique] no se pudo importar makeProgramPoster: ${e.message}`);
  }
  if (makeProgramPoster) {
    const _mockState = { snapshot: () => ({ FILMS: [] }) };
    for (const r of results) {
      let data;
      try { data = JSON.parse(fs.readFileSync(path.join(festivalsDir, r.fname), 'utf8')); } catch (e) { continue; }
      const progs = (data.films || []).filter(f => (f.is_cortos || f.is_programa) && !f.poster);
      const seen = {}; // svg → Set(títulos)
      for (const p of progs) {
        const svg = makeProgramPoster(_mockState, p.title, p.duration || '', p.section || '');
        (seen[svg] = seen[svg] || new Set()).add(p.title);
      }
      for (const titles of Object.values(seen)) {
        if (titles.size > 1) {
          r.errors.push(`[poster-editorial-unique] ${titles.size} programas con poster editorial idéntico: ${[...titles].join(' | ')}`);
          totalErrors++;
        }
      }
    }
  }

  // ── Output ───────────────────────────────────────────────────────────────────
  for (const { fname, errors, warnings } of results) {
    if (errors.length === 0 && warnings.length === 0) {
      console.log(`✓ ${fname}`);
      continue;
    }
    hasIssues = true;
    console.log(`\n── ${fname} ──`);
    for (const e of errors)   console.log(`  ✗ ERROR:   ${e}`);
    for (const w of warnings) console.log(`  ⚠ WARNING: ${w}`);
  }

  console.log(`\n${'─'.repeat(50)}`);
  console.log(`Festivales: ${files.length} | Errores: ${totalErrors} | Warnings: ${totalWarnings}`);

  if (totalErrors > 0) {
    console.log('\n✗ Validación fallida — corregir errores antes de commit\n');
    process.exit(1);
  } else if (totalWarnings > 0) {
    console.log('\n⚠ Validación OK con warnings — revisar antes de publicar\n');
    process.exit(0);
  } else {
    console.log('\n✓ Validación completa — todos los festivales OK\n');
    process.exit(0);
  }
})();
