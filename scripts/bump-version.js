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

// ── index.html → ?v= en el <script src de main.js> ──────────────────────
// El sub-recurso /src/main.js debe versionarse: el fix de auto-update iOS (#85)
// recarga index.html con ?v=, pero sin ?v= en el <script src> WKWebView puede
// seguir sirviendo el main.js viejo desde caché HTTP. Debe coincidir con
// BUILD_VERSION en cada build.
const idxPath = path.join(ROOT, 'index.html');
let idx = fs.readFileSync(idxPath, 'utf8');
const idxBefore = idx;
idx = idx.replace(/(src="\/src\/main\.js\?v=)\d{12}(")/, `$1${build}$2`);
if (idx === idxBefore) {
  console.error('✗ index.html: src="/src/main.js?v=YYYYMMDDHHMM" no encontrado.');
  process.exit(1);
}
// Favicons: versionar el ?v= para bustear la caché de favicons de Safari (DB
// local que sobrevive al reload — no cede sin cambio de URL). href sin ?v= o con
// ?v= viejo → se estampa el build actual.
idx = idx.replace(/(href="\/favicon(?:-192)?\.png)(?:\?v=\d{12})?(")/g, `$1?v=${build}$2`);
fs.writeFileSync(idxPath, idx);

// ── version.json — android e ios al MISMO build ──────────────────────────
// Formato: { android: "BUILD", ios: "BUILD" }
// El wrapper nativo (WKWebView) no cambia entre deploys — solo el contenido web —,
// así que iOS se actualiza en la misma cadencia que Android. Sin staged rollout:
// el poll de version.json en el cliente recarga iOS en la próxima reapertura.
// (El SW no es confiable en WKWebView sin App-Bound Domains → version.json es el
//  canal de update de iOS, por eso ambos campos deben avanzar juntos.)
// NOTA: promote-ios.yml queda obsoleto con este cambio.
const vPath = path.join(ROOT, 'version.json');
// MERGE, no overwrite: version.json puede llevar flags de runtime además de los
// builds (ej. storeGate — kill-switch de la landing de tiendas). Reescribir el
// objeto completo destruiría esos flags en cada deploy.
let vPrev = {};
try { vPrev = JSON.parse(fs.readFileSync(vPath, 'utf8')); } catch (_) {}
const vData = { ...vPrev, android: build, ios: build };
fs.writeFileSync(vPath, JSON.stringify(vData, null, 2) + '\n');

console.log(`✅ Build: ${build}`);
console.log(`   sw.js        → CACHE_NAME + BUILD = ${build}`);
console.log(`   src/main.js  → BUILD_VERSION = ${build}`);
console.log(`   index.html   → main.js?v= = ${build}`);
console.log(`   version.json → android = ${build}, ios = ${vData.ios} (misma cadencia)`);

// Regenerar CLAUDE.md con estado actual del repo
try { require('./generate-claude-md'); } catch (_) {}
