#!/usr/bin/env node
// build.js — Otrofestiv build system
// Uso: node build.js → produce dist/index.html

const fs   = require('fs');
const path = require('path');

const ROOT  = __dirname;
const SRC   = path.join(ROOT, 'src');
const DIST  = path.join(ROOT, 'dist');
const INDEX = path.join(ROOT, 'index.html');
const SHELL = path.join(SRC, 'shell.html');

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

  let html = fs.readFileSync(SHELL, 'utf8'); // always from clean shell

  // 1. Inline CSS from src/styles.css
  const cssFile = path.join(SRC, 'styles.css');
  if (fs.existsSync(cssFile)) {
    const css = fs.readFileSync(cssFile, 'utf8');
    // Replace any <style>...</style> block (handles: two-block legacy, placeholder, or post-build single block)
    const replaced = html.replace('<style>/* __STYLES__ */</style>', '<style>\n' + css + '\n</style>');
    if (replaced === html) { console.error('  ✗ CSS: __STYLES__ placeholder missing'); process.exit(1); }
    html = replaced;
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

    // ── Incrustar datos de festivales en el bundle ──────────────────────────
    // GitHub Pages bloquea fetch() a subdirectorios sin index.html (HTTP 403).
    // Solución: leer los JSONs en build-time e inyectarlos como variables JS.
    // loadFestival() los consume de _FESTIVAL_DATA en lugar de fetchear.
    const FEST_DIR = path.join(ROOT, 'festivals');
    let festDataJs = '\n// ─── Festival data (build-time embedded) ────────────────────────────\n';
    festDataJs += 'const _FESTIVAL_DATA = {};\n';
    if (fs.existsSync(FEST_DIR)) {
      fs.readdirSync(FEST_DIR).filter(f => f.endsWith('.json')).forEach(fname => {
        const data = fs.readFileSync(path.join(FEST_DIR, fname), 'utf8');
        const id = JSON.parse(data).id || fname.replace('.json','');
        festDataJs += `_FESTIVAL_DATA[${JSON.stringify(id)}] = ${data};\n`;
        console.log(`  ✓ festivals/${fname} (${(data.length/1024).toFixed(0)}kb)`);
      });
    }

    const r2 = html.replace('<script>/* __SCRIPTS__ */</script>', `<script>\n${festDataJs}\n${js}\n</script>`);
    if (r2 === html) { console.error('  ✗ JS: __SCRIPTS__ placeholder missing'); process.exit(1); }
    html = r2;
    console.log(`\n  ✓ ${JS_ORDER.length} modules, ${declared.size} total symbols`);
  }

  fs.writeFileSync(path.join(DIST, 'index.html'), html);
  const kb = (fs.statSync(path.join(DIST, 'index.html')).size / 1024).toFixed(0);
  console.log(`\n✓ dist/index.html (${kb}kb) in ${Date.now() - start}ms`);
  
  // Auto-verify integrity
  try {
    require('./verify.js');
  } catch(e) {
    // verify.js calls process.exit(1) on failure — that's the intended behavior
  }
}

build();
