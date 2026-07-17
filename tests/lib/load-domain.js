// Domain function loader for unit tests.
//
// Pure functions live in index.html — no module boundary. To unit test them
// without rebuilding the app, this loader:
//   1. Reads index.html
//   2. Concatenates the contents of all <script> blocks
//   3. Extracts named function declarations by walking braces (skips strings
//      and comments — does not parse regex literals)
//   4. Wraps them in an IIFE that exposes injected globals as `let` bindings,
//      so the extracted functions resolve free variables (FESTIVAL_BUFFER,
//      FESTIVAL_TRANSPORT, FESTIVAL_CONFIG, _activeFestId, DEFAULT_DURATION_MIN)
//      against the test-controlled sandbox.
//
// Hoisting handles cross-function references inside the wrapper, so the
// declaration order does not matter. The production code stays single-file.
//
// The worker-template copies of venueTravelMins/travelMins live inside backtick
// strings further down in the file; the extractor walks matches in document
// order and returns the first one, which is always the main-thread version.

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const INDEX = path.join(ROOT, 'index.html');
const MAIN = path.join(ROOT, 'src', 'main.js');
const STORAGE = path.join(ROOT, 'src', 'storage', 'storage.js');
const DOMAIN = ['time', 'film', 'schedule', 'festival']
  .map(m => path.join(ROOT, 'src', 'domain', `${m}.js`));
// QA de dominio del planeador (5 jul 2026): getSuggestions vive en
// src/view/agenda.js. Se concatena para poder extraerla y testearla con deps
// inyectadas (savedAgenda/watchlist/FILMS/etc. van como globals en cada test).
const AGENDA = path.join(ROOT, 'src', 'view', 'agenda.js');

// p8 Step 0: el código de la app se movió de los <script> inline de index.html
// a src/main.js (módulo). readScripts concatena los scripts inline restantes
// (Sentry, splash) + main.js (raw) para que extractFunction encuentre las fns.
// p8 Step 3: el adapter `storage` se movió a src/storage/storage.js. Se concatena
// también — extractObject('storage') matchea `const storage={` dentro de
// `export const storage={` (el match arranca en `const`, sin el `export`).
// p8 Step 5: las 24 fns puras + venueTravelMins/travelMins se movieron a
// src/domain/*.js. Se concatenan — extractFunction matchea `function NAME(`
// dentro de `export function NAME(`. Los imports ESM se ignoran (extractFunction
// solo extrae bodies por nombre; los deps se inyectan como globals en cada test).
function readScripts() {
  const html = fs.readFileSync(INDEX, 'utf8');
  const inline = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)]
    .map(m => m[1])
    .join('\n');
  const main = fs.existsSync(MAIN) ? fs.readFileSync(MAIN, 'utf8') : '';
  const storageSrc = fs.existsSync(STORAGE) ? fs.readFileSync(STORAGE, 'utf8') : '';
  const domainSrc = DOMAIN.filter(fs.existsSync).map(f => fs.readFileSync(f, 'utf8')).join('\n');
  const agendaSrc = fs.existsSync(AGENDA) ? fs.readFileSync(AGENDA, 'utf8') : '';
  // domainSrc ANTES de main: las fns de dominio (main-thread, src/domain/) deben
  // matchearse antes que las COPIAS worker-local (en backtick strings dentro de
  // main.js, ej. `function simNow(){return SIM_TIME...}`). extractFunction
  // devuelve el primer match en orden de documento → la versión main-thread.
  // agendaSrc al FINAL: solo se piden de ahí fns que no existen en otros archivos
  // (getSuggestions) — sin riesgo de shadowing.
  return inline + '\n' + domainSrc + '\n' + main + '\n' + storageSrc + '\n' + agendaSrc;
}

// Returns the source of `function NAME(...) { ... }` from `source`, or null.
// Walks braces while skipping strings ("", '', ``) and comments (// /**/).
// Does NOT detect regex literals; callers should not ask for functions whose
// body contains regex literals with unbalanced braces.
function extractFunction(source, name) {
  const re = new RegExp(`\\bfunction\\s+${name}\\s*\\(`, 'g');
  let m;
  while ((m = re.exec(source)) !== null) {
    const start = m.index;
    // Skip the param list
    let i = source.indexOf('(', start);
    let parens = 1;
    i++;
    while (i < source.length && parens > 0) {
      const c = source[i];
      if (c === '(') parens++;
      else if (c === ')') parens--;
      i++;
    }
    // Find the body `{`
    while (i < source.length && source[i] !== '{') i++;
    if (i >= source.length) continue;
    let depth = 0;
    while (i < source.length) {
      const c = source[i], n = source[i + 1];
      if (c === '/' && n === '*') {
        i += 2;
        while (i < source.length - 1 && !(source[i] === '*' && source[i + 1] === '/')) i++;
        i += 2;
        continue;
      }
      if (c === '/' && n === '/') {
        while (i < source.length && source[i] !== '\n') i++;
        continue;
      }
      if (c === '"' || c === "'" || c === '`') {
        const q = c;
        i++;
        while (i < source.length) {
          if (source[i] === '\\') { i += 2; continue; }
          if (source[i] === q) { i++; break; }
          i++;
        }
        continue;
      }
      if (c === '{') depth++;
      else if (c === '}') {
        depth--;
        if (depth === 0) return source.slice(start, i + 1);
      }
      i++;
    }
  }
  return null;
}

// Returns the source of `const NAME = { ... };` from `source`, or null.
// Walks braces from the opening `{` after `=` while skipping strings and
// comments. Captures the trailing `;` if present.
// Same caveats as extractFunction: does NOT detect regex literals; callers
// should not ask for objects whose body contains regex with unbalanced braces.
function extractObject(source, name) {
  const re = new RegExp(`\\bconst\\s+${name}\\s*=\\s*\\{`);
  const m = source.match(re);
  if (!m) return null;
  const start = m.index;
  let i = start + m[0].length - 1; // points to '{'
  let depth = 0;
  while (i < source.length) {
    const c = source[i], n = source[i + 1];
    if (c === '/' && n === '*') {
      i += 2;
      while (i < source.length - 1 && !(source[i] === '*' && source[i + 1] === '/')) i++;
      i += 2;
      continue;
    }
    if (c === '/' && n === '/') {
      while (i < source.length && source[i] !== '\n') i++;
      continue;
    }
    if (c === '"' || c === "'" || c === '`') {
      const q = c;
      i++;
      while (i < source.length) {
        if (source[i] === '\\') { i += 2; continue; }
        if (source[i] === q) { i++; break; }
        i++;
      }
      continue;
    }
    if (c === '{') depth++;
    else if (c === '}') {
      depth--;
      if (depth === 0) {
        let end = i + 1;
        // Capture optional trailing `;`
        while (end < source.length && /\s/.test(source[end])) end++;
        if (source[end] === ';') end++;
        return source.slice(start, end);
      }
    }
    i++;
  }
  return null;
}

const DEFAULT_FNS = [
  'toMin', 'minToStr', 'parseDur', 'effectiveDuration',
  'screeningEndMin', 'screeningEnded', 'screeningNow',
  '_resolveVenue', 'venueTravelMins', 'travelMins',
  'screensConflict',
  // Fase 2 — festival phase helpers
  '_endedStats', '_classifyTodayScreenings', '_gapSuggestion', '_getFestivalPhase',
  // Fase 3 — temporal subsystem
  '_festDate', 'simNow', '_tzOffsetMin', '_festNow', '_festNowMin', 'simTodayStr', 'festivalEnded', 'screeningPassed', 'dayFullyPassed',
  // Fase 4 — schedule planning
  'isScreeningBlocked', '_djb2', '_titleSeed', '_mulberry32',
  'shuffle', 'scoreFilm', 'sortScreensByStrategy', 'computeScenarios',
];

function loadDomain(opts = {}) {
  const globals = opts.globals || {};
  const fns = opts.functions || DEFAULT_FNS;
  const objects = opts.objects || [];
  const source = readScripts();

  // Functions whose names appear in `globals` are OVERRIDDEN by the global —
  // skip the function declaration to avoid `Identifier already declared`.
  // The let binding from globalDecls wins; functions referencing the name
  // resolve to the stub via closure.
  const fnsToDeclare = fns.filter(name => !(name in globals));

  const fnDeclarations = fnsToDeclare.map(name => {
    const fn = extractFunction(source, name);
    if (!fn) throw new Error(`Function not found in index.html: ${name}`);
    return fn;
  }).join('\n\n');

  const objDeclarations = objects.map(name => {
    const obj = extractObject(source, name);
    if (!obj) throw new Error(`Object not found in index.html: ${name}`);
    return obj;
  }).join('\n\n');

  const declarations = fnDeclarations + (objDeclarations ? '\n\n' + objDeclarations : '');

  const globalDecls = Object.keys(globals)
    .map(k => `let ${k} = __g[${JSON.stringify(k)}];`)
    .join('\n');

  const returnNames = [...fns, ...objects];
  const returnObj = '{' + returnNames.join(', ') + '}';
  const src = `(function (__g) {\n${globalDecls}\n${declarations}\nreturn ${returnObj};\n})`;

  // eslint-disable-next-line no-eval
  const factory = eval(src);
  return factory(globals);
}

module.exports = { loadDomain, extractFunction, extractObject };
