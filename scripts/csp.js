#!/usr/bin/env node
// csp.js — DUEÑO ÚNICO del script-src de la CSP de index.html (26 oct 2026).
//
// La CSP va en un <meta> (GitHub Pages no manda headers, no hay nonces). Para no
// necesitar 'unsafe-inline', cada <script> inline ejecutable se autoriza por su
// HASH sha256. El hash cambia si cambia UN byte del script — y bump-version.js
// reescribe el src="/src/main.js?v=…" del gate en cada deploy —, así que el hash
// se calcula ACÁ, siempre: bump-version.js llama a aplicar() después de estampar,
// y validate.py [csp-hashes] corre `--comprobar` (un hash viejo dejaría la app
// en blanco: el navegador no ejecuta el gate).
//
//   node scripts/csp.js              reescribe index.html
//   node scripts/csp.js --comprobar  sale 1 si index.html no está al día
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const IDX = path.join(__dirname, '..', 'index.html');
// Orígenes de scripts externos permitidos (cada <script src> lleva además
// versión fija + integrity: [script-externo-fijo]).
// POR RUTA, no el CDN entero (auditoría senior, 26 oct): con `cdn.jsdelivr.net` a
// secas, un HTML inyectado podía cargar CUALQUIER paquete de npm (incluidas
// librerías viejas que sirven para saltarse la CSP). Al subir supabase-js se
// cambian la versión de acá, la del <script> y su integrity.
const EXTERNOS = [
  'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.118.0/',
  'https://js.sentry-cdn.com/f9a3edecb09ba965c5426d617e1cf7de.min.js',
  'https://browser.sentry-cdn.com',   // solo sirve bundles de Sentry (el loader los pide)
];

function hashes(html) {
  const out = [];
  // fuera los comentarios HTML: el de la CSP dice «<script>» en texto y el
  // scanner arrancaba ahí — hasheaba comentario+meta, no el script real
  const sinComent = html.replace(/<!--[\s\S]*?-->/g, '');
  const re = /<script(?![^>]*\bsrc=)([^>]*)>([\s\S]*?)<\/script>/g;
  let m;
  while ((m = re.exec(sinComent))) {
    if (/type="application\/ld\+json"/.test(m[1])) continue;   // dato, no se ejecuta
    // un «<!--» DENTRO de un script rompería el borrado de comentarios de arriba
    if (m[2].includes('<!--')) throw new Error('un <script> inline contiene «<!--»: csp.js no puede hashearlo con seguridad');
    // el parser HTML convierte \r\n y \r en \n ANTES de que el navegador hashee
    const texto = m[2].replace(/\r\n?/g, '\n');
    out.push(`'sha256-${crypto.createHash('sha256').update(texto, 'utf8').digest('base64')}'`);
  }
  return out;
}

function aplicar(html) {
  // Capacitor Android inyecta su bridge justo después del literal «<head>»: con
  // atributos lo pondría DESPUÉS de la CSP y lo bloquearía. Y el charset va en los
  // primeros 1024 bytes, o el navegador puede decodificar distinto y el hash no da.
  if (!/<head>\s*<meta charset="UTF-8">/.test(html)) throw new Error('index.html: «<head>» literal seguido de <meta charset="UTF-8">');
  if (Buffer.byteLength(html.slice(0, html.indexOf('<meta charset')), 'utf8') > 1000) throw new Error('index.html: <meta charset> fuera de los primeros 1024 bytes');
  const src = ["'self'", ...hashes(html), ...EXTERNOS].join(' ');
  const re = /(<meta http-equiv="Content-Security-Policy" content="[^"]*?script-src )[^;"]*/;
  if (!re.test(html)) throw new Error('index.html: no encuentro script-src en el <meta> de la CSP');
  return html.replace(re, `$1${src}`);
}

module.exports = { aplicar, hashes };

if (require.main === module) {
  const html = fs.readFileSync(IDX, 'utf8');
  const nuevo = aplicar(html);
  if (process.argv.includes('--comprobar')) {
    if (nuevo !== html) { console.error('✗ la CSP de index.html no coincide con sus scripts inline: node scripts/csp.js'); process.exit(1); }
    console.log('✓ CSP al día'); process.exit(0);
  }
  if (nuevo !== html) fs.writeFileSync(IDX, nuevo);
  console.log(`✓ CSP: script-src con ${hashes(html).length} hash(es), sin unsafe-inline ni unsafe-eval`);
}
