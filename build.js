#!/usr/bin/env node
// build.js — Otrofestiv build system
// Uso: node build.js
// Produce dist/index.html desde src/ + index.html

const fs   = require('fs');
const path = require('path');

const ROOT  = __dirname;
const SRC   = path.join(ROOT, 'src');
const DIST  = path.join(ROOT, 'dist');
const INDEX = path.join(ROOT, 'index.html');

// Fases completadas:
// Fase 1: src/config.js  — UI, ICONS, FESTIVAL_CONFIG, VENUES
// Fase 2: src/styles.css — todo el CSS
// Fases 3-5: pendientes

const JS_FILES = [
  'config.js',
  // 'utils.js',   // Fase 3
  // 'state.js',   // Fase 3
  // 'algo.js',    // Fase 3
  // 'renders.js', // Fase 4
  // 'main.js',    // Fase 5
];

function build() {
  console.log('Building Otrofestiv...\n');
  if (!fs.existsSync(DIST)) fs.mkdirSync(DIST);

  let html = fs.readFileSync(INDEX, 'utf8');

  // Fase 2: inline CSS from src/styles.css
  const cssFile = path.join(SRC, 'styles.css');
  if (fs.existsSync(cssFile)) {
    const css = fs.readFileSync(cssFile, 'utf8');
    html = html.replace(
      /<style>[\s\S]*?<\/style>\s*<style>[\s\S]*?<\/style>/,
      '<style>\n' + css + '\n</style>'
    );
    console.log('  ✓ styles.css inlined (' + css.length + ' chars)');
  }

  fs.writeFileSync(path.join(DIST, 'index.html'), html);
  console.log('\n✓ dist/index.html (' + html.length + ' chars)');
}

build();
