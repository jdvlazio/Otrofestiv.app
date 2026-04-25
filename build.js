#!/usr/bin/env node
// build.js — Otrofestiv build system
// Uso: node build.js → produce dist/index.html

const fs   = require('fs');
const path = require('path');

const ROOT  = __dirname;
const SRC   = path.join(ROOT, 'src');
const DIST  = path.join(ROOT, 'dist');
const INDEX = path.join(ROOT, 'index.html');

const JS_ORDER = [
  'config.js',
  'posters.js',
  'auth.js',
  'utils.js',
  'state.js',
  'actions.js',
  'algo.js',
  'renders/helpers.js',
  'renders/mi-lista.js',
  'renders/mi-plan.js',
  'renders/planear.js',
  'renders/cartelera.js',
  'renders/sheets.js',
  'renders/programa.js',
  'renders/init.js',
];

// Remove top-level const/let declarations that are already declared
function dedup(code, alreadyDeclared) {
  const lines = code.split('\n');
  const result = [];
  let skipDepth = 0;
  let skipName = null;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trimStart();

    // Detect top-level duplicate declaration
    if (skipDepth === 0) {
      const m = trimmed.match(/^(const|let|var)\s+(\w+)\s*=/);
      if (m && alreadyDeclared.has(m[2]) && !line.startsWith(' ') && !line.startsWith('\t')) {
        skipName = m[2];
        skipDepth = 1;
        // Count braces in this line
        skipDepth += (line.match(/\{/g)||[]).length - (line.match(/\}/g)||[]).length;
        // Single-line declaration ends with ;
        if (skipDepth <= 1 && trimmed.endsWith(';')) skipDepth = 0;
        continue;
      }
    }

    if (skipDepth > 0) {
      skipDepth += (line.match(/\{/g)||[]).length - (line.match(/\}/g)||[]).length;
      if (skipDepth <= 0) { skipDepth = 0; skipName = null; }
      continue;
    }

    result.push(line);

    // Track new declarations for subsequent files
    const m = trimmed.match(/^(const|let|var)\s+(\w+)/);
    if (m && !line.startsWith(' ') && !line.startsWith('\t')) {
      alreadyDeclared.add(m[2]);
    }
  }

  return result.join('\n');
}

function build() {
  const start = Date.now();
  console.log('Building Otrofestiv...\n');
  if (!fs.existsSync(DIST)) fs.mkdirSync(DIST);

  let html = fs.readFileSync(INDEX, 'utf8');

  // 1. Inline CSS from src/styles.css
  const cssFile = path.join(SRC, 'styles.css');
  if (fs.existsSync(cssFile)) {
    const css = fs.readFileSync(cssFile, 'utf8');
    // Try two-block pattern first (legacy index.html with separate font-face block)
    // Then fall back to single placeholder pattern (shell.html)
    const twoBlock = /<style>[\s\S]*?<\/style>\s*<style>[\s\S]*?<\/style>/;
    const placeholder = /<style>\/\* __STYLES__ \*\/<\/style>/;
    if (twoBlock.test(html)) {
      html = html.replace(twoBlock, '<style>\n' + css + '\n</style>');
    } else {
      html = html.replace(placeholder, '<style>\n' + css + '\n</style>');
    }
    console.log(`  ✓ styles.css (${(css.length/1024).toFixed(0)}kb)`);
  }

  // 2. Concatenate JS with dedup
  const missing = JS_ORDER.filter(f => !fs.existsSync(path.join(SRC, f)));
  if (missing.length) {
    console.log(`  ⚠ Missing: ${missing.join(', ')} — keeping inline JS`);
  } else {
    const declared = new Set();
    const parts = [];

    for (const f of JS_ORDER) {
      let code = fs.readFileSync(path.join(SRC, f), 'utf8');
      const before = declared.size;
      code = dedup(code, declared);
      parts.push(`\n// ─── ${f} ${'─'.repeat(Math.max(0,48-f.length))}\n${code}`);
      console.log(`  ✓ ${f.padEnd(28)} (${(code.length/1024).toFixed(0)}kb, +${declared.size-before} symbols)`);
    }

    const js = parts.join('\n');
    const scriptBlocks = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)];
    const mainBlock = scriptBlocks.reduce((a, b) => b[0].length > a[0].length ? b : a);
    html = html.replace(mainBlock[0], `<script>\n${js}\n</script>`);
    console.log(`\n  ✓ ${JS_ORDER.length} modules, ${declared.size} total symbols`);
  }

  fs.writeFileSync(path.join(DIST, 'index.html'), html);
  const kb = (fs.statSync(path.join(DIST, 'index.html')).size / 1024).toFixed(0);
  console.log(`\n✓ dist/index.html (${kb}kb) in ${Date.now() - start}ms`);
}

build();
