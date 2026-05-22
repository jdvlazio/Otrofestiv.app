#!/usr/bin/env node
/**
 * bump-version.js — Actualiza BUILD_VERSION en index.html, sw.js y version.json.
 *
 * Uso: node scripts/bump-version.js
 * Correr ANTES de cada git push a producción.
 * En CI (validate.yml) corre automáticamente en cada push que toca index.html o sw.js.
 *
 * Qué actualiza:
 *   - index.html → BUILD_VERSION='YYYYMMDDHHMMM' (reload inmediato al cambiar HTML)
 *   - sw.js      → CACHE_NAME + BUILD (fuerza detección de nuevo SW)
 *   - version.json → android: BUILD (ios se mantiene hasta "Promover a iOS")
 *
 * Formato: YYYYMMDDHHmm (ej: 202609101430)
 */

const fs   = require('fs');
const path = require('path');
const ROOT = path.join(__dirname, '..');

const now   = new Date();
const build = [
  now.getFullYear(),
  String(now.getMonth() + 1).padStart(2, '0'),
  String(now.getDate()).padStart(2, '0'),
  String(now.getHours()).padStart(2, '0'),
  String(now.getMinutes()).padStart(2, '0'),
].join('');

// ── sw.js ─────────────────────────────────────────────────────────────────
const swPath = path.join(ROOT, 'sw.js');
let sw = fs.readFileSync(swPath, 'utf8');
const swBefore = sw;
sw = sw.replace(/otrofestiv-v\d{12}/, `otrofestiv-v${build}`);
sw = sw.replace(/BUILD = '\d{12}'/, `BUILD = '${build}'`);
if (sw === swBefore) {
  console.error('✗ sw.js: patrones CACHE_NAME/BUILD no encontrados. Verificar formato.');
  process.exit(1);
}
fs.writeFileSync(swPath, sw);

// ── BUILD_VERSION ──────────────────────────────────────────────────────────
// p8 Step 0: BUILD_VERSION se movió de index.html a src/main.js (módulo).
const bvPath = path.join(ROOT, 'src', 'main.js');
let bvFile = fs.readFileSync(bvPath, 'utf8');
const bvBefore = bvFile;
bvFile = bvFile.replace(/BUILD_VERSION='\d{12}'/, `BUILD_VERSION='${build}'`);
if (bvFile === bvBefore) {
  console.error('✗ src/main.js: BUILD_VERSION=\'YYYYMMDDHHMMM\' no encontrado.');
  process.exit(1);
}
fs.writeFileSync(bvPath, bvFile);

// ── version.json — android bump, ios se preserva ─────────────────────────
// Formato: { android: "BUILD", ios: "BUILD" }
// iOS solo se actualiza via "Promover a iOS" en GitHub Actions.
const vPath = path.join(ROOT, 'version.json');
let vData = { android: build, ios: build }; // default si no existe
if (fs.existsSync(vPath)) {
  try {
    const existing = JSON.parse(fs.readFileSync(vPath, 'utf8'));
    // Preservar ios tal como está — solo bumpeamos android
    vData = { android: build, ios: existing.ios || build };
  } catch (_) {
    // JSON corrupto → resetear ambos
  }
}
fs.writeFileSync(vPath, JSON.stringify(vData, null, 2) + '\n');

console.log(`✅ Build: ${build}`);
console.log(`   sw.js        → CACHE_NAME + BUILD = ${build}`);
console.log(`   src/main.js  → BUILD_VERSION = ${build}`);
console.log(`   version.json → android = ${build}, ios = ${vData.ios} (preservado)`);

// Regenerar CLAUDE.md con estado actual del repo
try { require('./generate-claude-md'); } catch (_) {}
