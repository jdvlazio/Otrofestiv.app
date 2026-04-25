#!/usr/bin/env node
// verify.js — post-build integrity check
// Run: node verify.js
// Exits 1 if any check fails.

const fs   = require('fs');
const path = require('path');

const built = fs.readFileSync(path.join(__dirname, 'dist/index.html'), 'utf8');

let pass = 0, fail = 0;
const ok  = (msg) => { console.log(`  ✓ ${msg}`); pass++; };
const err = (msg) => { console.error(`  ✗ ${msg}`); fail++; };

// ── 1. Style block ────────────────────────────────────────────
const styles = built.match(/<style>([\s\S]*?)<\/style>/);
if (!styles) { err('No <style> block found'); process.exit(1); }
const css = styles[1];

const requiredCSS = [
  'ag-excl-strip','ag-excl-poster',
  'ag-warn','ctx-header','mplan-wk-block',
  'ctx-eyebrow','notice-banner','wl-heart',
  'prog-suffix','badge-live',
];
console.log('\nCSS checks:');
for (const cls of requiredCSS) {
  css.includes(cls) ? ok(`.${cls}`) : err(`.${cls} MISSING`);
}

// ── 2. JS block ───────────────────────────────────────────────
const scripts = [...built.matchAll(/<script>([\s\S]*?)<\/script>/g)];
const js = scripts.reduce((a,b) => b[0].length > a[0].length ? b : a)[1];

// Syntax check
try {
  new Function(js);
  ok('JS syntax valid');
} catch(e) {
  err(`JS syntax error: ${e.message}`);
}

// Required functions
const requiredFns = [
  'toMin','parseDur','screensConflict','travelMins','travelWarn',
  '_effectiveVenue','isScreeningBlocked',
  'computeScenarios','getSuggestions','squeezeExcluded','greedyFloor',
  'scoreFilm','sortScreensByStrategy',
  'buildResultHTML','runCalc','saveCurrentScenario','renderAgenda',
  'togglePriority','jumpToScenario','renderPrioStrip',
  'loadState','saveSavedAgenda','showToast','showActionModal',
  'renderAvBlocks','openAvSheet','renderNoticesBanner',
];
console.log('\nFunction checks:');
for (const fn of requiredFns) {
  const count = (js.match(new RegExp(`function ${fn}\\b`, 'g')) || []).length;
  if (count === 0) err(`${fn}() MISSING`);
  else if (count > 1) err(`${fn}() DUPLICATE x${count}`);
  else ok(`${fn}()`);
}

// ── 3. Summary ────────────────────────────────────────────────
console.log(`\n${pass + fail} checks: ${pass} passed, ${fail} failed`);
if (fail > 0) { console.error('\n✗ Build verification FAILED'); process.exit(1); }
else { console.log('\n✓ Build OK'); }
