#!/usr/bin/env node
// ci-camino.js — ¿este PR va por el CAMINO DE DATOS o por el COMPLETO?
// (17 oct 2026, senior dev + tech lead; docs/ARQUITECTURA.md «Dos caminos de CI»)
//
// Datos = todo archivo cambiado está bajo un prefijo de .github/camino-datos.txt,
// o es un archivo de la app cuyo ÚNICO cambio es el número de versión que pone
// scripts/bump-version.js (12 dígitos: index.html, src/main.js, sw.js). Sin esa
// excepción ningún PR calificaría: el bump es obligatorio en cada push.
//
//   node scripts/ci-camino.js <base-ref>   → imprime «datos» o «completo» + el porqué
const { execSync } = require('child_process');
const fs = require('fs');

const BUMP = ['index.html', 'src/main.js', 'sw.js'];

function soloBump(diff) {
  // líneas -/+ del diff, sin cabeceras; con el número de versión tapado deben
  // quedar iguales de los dos lados
  const L = diff.split('\n').filter(l => /^[-+]/.test(l) && !/^(---|\+\+\+)/.test(l));
  const tapa = l => l.slice(1).replace(/\d{12}/g, 'V');
  const menos = L.filter(l => l[0] === '-').map(tapa).sort();
  const mas = L.filter(l => l[0] === '+').map(tapa).sort();
  return menos.length === mas.length && menos.every((x, i) => x === mas[i]);
}

function clasificar(archivos, prefijos, diffDe) {
  const fuera = archivos.filter(f => !prefijos.some(p => f.startsWith(p)) &&
    !(BUMP.includes(f) && soloBump(diffDe(f))));
  return fuera.length ? { camino: 'completo', fuera } : { camino: 'datos', fuera: [] };
}

module.exports = { soloBump, clasificar };

if (require.main === module) {
  const base = process.argv[2] || 'main';
  const prefijos = fs.readFileSync('.github/camino-datos.txt', 'utf8').split('\n')
    .map(l => l.trim()).filter(l => l && !l.startsWith('#'));
  const archivos = execSync(`git diff --name-only origin/${base}...HEAD`).toString().split('\n').filter(Boolean);
  const r = clasificar(archivos, prefijos, f => execSync(`git diff -U0 origin/${base}...HEAD -- ${f}`).toString());
  console.log(r.camino);
  if (r.fuera.length) console.error('camino COMPLETO por: ' + r.fuera.slice(0, 20).join(', '));
  else console.error(`camino de DATOS: ${archivos.length} archivo(s), todos de datos o solo el bump`);
}
