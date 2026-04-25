#!/usr/bin/env node
// build.js — Otrofestiv build system
// Concatena src/*.js en el bloque <script> de index.html
// Uso: node build.js

const fs = require('fs');
const path = require('path');

const SRC = path.join(__dirname, 'src');
const INDEX = path.join(__dirname, 'index.html');

// Orden de concatenación — el orden importa
const BUILD_ORDER = [
  'config.js',
  // próximas fases:
  // 'utils.js',
  // 'state.js', 
  // 'algo.js',
  // 'renders.js',
  // 'main.js',
];

console.log('Building Otrofestiv...');

// Read current index.html
let html = fs.readFileSync(INDEX, 'utf8');

// Find the main script block
const scriptMatch = html.match(/<script>([\s\S]*?)<\/script>/g)
  ?.map((m, i) => ({i, m, len: m.length}))
  ?.sort((a, b) => b.len - a.len)[0];

if (!scriptMatch) {
  console.error('ERROR: No main script block found');
  process.exit(1);
}

// Read src files
const srcContent = BUILD_ORDER.map(file => {
  const p = path.join(SRC, file);
  if (!fs.existsSync(p)) {
    console.warn(`  WARN: ${file} not found — skipping`);
    return '';
  }
  const content = fs.readFileSync(p, 'utf8');
  console.log(`  ✓ ${file} (${content.length} chars)`);
  return `\n// ── ${file} ──────────────────────────────────────────────────\n` + content;
}).join('\n');

console.log(`\nBuild order: ${BUILD_ORDER.filter(f => fs.existsSync(path.join(SRC, f))).join(', ')}`);
console.log('Done. (This build system is a work in progress — Phase 1 only extracts config.js)');
console.log('\nNote: index.html is still the source of truth for Phases 1-4.');
console.log('The src/ files are the canonical source for config blocks.');
