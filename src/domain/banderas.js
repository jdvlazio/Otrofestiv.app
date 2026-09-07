// País(es) → banderas. UN solo motor, sobre UNA sola tabla.
//
// Antes vivía en sheets-controller.js con su propia tabla escrita a mano, y
// pipeline/lib.py tenía otra. Divergieron en todo lo que podían divergir: la
// tabla (a la del app le faltaban 23 países de festivales EN CURSO), la
// normalización (el pipeline comparaba sin tildes y el app exacto, así que
// «Países bajos» daba 🇳🇱 en el dato y 🌍 en pantalla) y hasta el modo de partir
// («Antigua y Barbuda» se partía en dos mitades que no eran ningún país).
//
// Ahora la tabla se GENERA (scripts/generate-paises.js, de ICU es+en) y este
// módulo es el único que la lee del lado del app. El gemelo en Python es
// lib.banderas(), con el mismo algoritmo y la misma tabla en JSON.
import { PAISES, SIN_BANDERA } from './paises.js';

// La MISMA clave que usan el generador y lib.norm(): minúsculas, sin tildes,
// solo alfanumérico. Tres copias de una regla son tres reglas.
const _k = x => (x || '').normalize('NFD').replace(/[̀-ͯ]/g, '')
  .toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();

export function countryToFlags(countryStr) {
  if (!countryStr) return '🌍';
  const out = [];
  // Coma, barra y paréntesis son separadores INEQUÍVOCOS: «España (Austria)» es
  // una coproducción de dos países y quedarse con uno pierde el otro.
  for (const parte of String(countryStr).split(/[,/()]/)) {
    const k = _k(parte);
    if (!k || SIN_BANDERA.has(k)) continue;
    const f = PAISES[k];
    if (f) { out.push(f); continue; }
    // Por « y » y por guion se parte SOLO si el token entero no resolvió:
    // «Antigua y Barbuda» y «Guinea-Bissau» son un país; «Colombia y México» no.
    for (const sub of parte.split(/\s+y\s+|[-–—]/)) {
      const g = PAISES[_k(sub)];
      if (g) out.push(g);
    }
  }
  const flags = [...new Set(out)];
  return flags.length ? flags.join('') : '🌍';
}
