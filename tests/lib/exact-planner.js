// exact-planner — solver EXACTO de referencia del planeador. SOLO TESTS.
//
// El problema es Job Interval Selection (elegir ≤1 función por título,
// maximizar títulos; NP-hard en general, trivial a nuestra escala). Este solver
// NO conoce la heurística de producción: hace DFS exhaustivo con poda de cota
// (chosen + restantes ≤ best → poda). Su única dependencia compartida con
// producción es `screensConflict` — a propósito: la FACTIBILIDAD tiene un solo
// dueño; lo que este solver aporta de forma independiente es la OPTIMALIDAD.
//
// Regla del dominio (la cazó el oráculo en su primera corrida, Leviza):
// un título `is_recurring` (taller de varios días) entra con TODAS sus
// sesiones o con ninguna — así lo planifica computeScenarios (rama is_recurring
// del backtracking) y así cuenta: cada sesión suma al tamaño del plan.
//
// Orden MRV (menos funciones primero) solo por velocidad — no afecta el
// resultado: el DFS agota el espacio salvo poda por cota, que es exacta.

function exactMaxEntries(titles, groupByTitle, screensConflict) {
  const groups = titles
    .map(t => groupByTitle(t))
    .filter(g => g && g.screens.length > 0)
    .sort((a, b) => a.screens.length - b.screens.length);
  // cota optimista por título: lo que aportaría si entrara completo
  const gain = g => g.recurring ? g.screens.length : 1;
  const suffixGain = new Array(groups.length + 1).fill(0);
  for (let i = groups.length - 1; i >= 0; i--) suffixGain[i] = suffixGain[i + 1] + gain(groups[i]);
  let best = 0;
  const chosen = [];
  (function dfs(idx) {
    if (chosen.length + suffixGain[idx] <= best) return; // cota exacta
    if (idx === groups.length) { best = Math.max(best, chosen.length); return; }
    const g = groups[idx];
    if (g.recurring) {
      // todo-o-nada: entran todas las sesiones o ninguna
      if (g.screens.every(s => chosen.every(c => !screensConflict(c, s)))) {
        g.screens.forEach(s => chosen.push(s));
        dfs(idx + 1);
        g.screens.forEach(() => chosen.pop());
      }
    } else {
      for (const s of g.screens) {
        if (chosen.every(c => !screensConflict(c, s))) {
          chosen.push(s); dfs(idx + 1); chosen.pop();
        }
      }
    }
    dfs(idx + 1); // rama "este título queda afuera"
  })(0);
  return best;
}

module.exports = { exactMaxEntries };
