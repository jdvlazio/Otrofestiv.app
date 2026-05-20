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

function readScripts() {
  const html = fs.readFileSync(INDEX, 'utf8');
  return [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)]
    .map(m => m[1])
    .join('\n');
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

const DEFAULT_FNS = [
  'toMin', 'parseDur', 'effectiveDuration',
  '_resolveVenue', 'venueTravelMins', 'travelMins',
  'screensConflict',
  // Fase 2 — festival phase helpers
  '_endedStats', '_classifyTodayScreenings', '_gapSuggestion', '_getFestivalPhase',
  // Fase 3 — temporal subsystem
  '_festDate', 'simNow', 'simTodayStr', 'festivalEnded', 'screeningPassed', 'dayFullyPassed',
];

function loadDomain(opts = {}) {
  const globals = opts.globals || {};
  const fns = opts.functions || DEFAULT_FNS;
  const source = readScripts();

  // Functions whose names appear in `globals` are OVERRIDDEN by the global —
  // skip the function declaration to avoid `Identifier already declared`.
  // The let binding from globalDecls wins; functions referencing the name
  // resolve to the stub via closure.
  const fnsToDeclare = fns.filter(name => !(name in globals));

  const declarations = fnsToDeclare.map(name => {
    const fn = extractFunction(source, name);
    if (!fn) throw new Error(`Function not found in index.html: ${name}`);
    return fn;
  }).join('\n\n');

  const globalDecls = Object.keys(globals)
    .map(k => `let ${k} = __g[${JSON.stringify(k)}];`)
    .join('\n');

  const returnObj = '{' + fns.join(', ') + '}';
  const src = `(function (__g) {\n${globalDecls}\n${declarations}\nreturn ${returnObj};\n})`;

  // eslint-disable-next-line no-eval
  const factory = eval(src);
  return factory(globals);
}

module.exports = { loadDomain, extractFunction };
