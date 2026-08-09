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

// PRIORIDADES (opts.required) — la segunda pregunta que sabe responder este solver.
// computeScenarios reporta DOS máximos: `trueMax` (sin restricción) y
// `maxWithPriorities` (todas las prioridades adentro). El segundo no tenía oráculo:
// se creía. Con `required`, la rama «este título queda afuera» se prohíbe para los
// exigidos, y el resultado es el máximo alcanzable respetándolos — o 0 si son
// mutuamente imposibles, que es exactamente lo que reporta findMax(mustIncludeAll).
//
// Solo se exigen títulos que SOBREVIVEN al filtrado (tienen ≥1 función utilizable):
// una prioridad sin funciones no entra a baseGroups en producción y, por tanto,
// tampoco se exige acá. Exigirla haría fallar al oráculo por una regla que el
// código de producción nunca prometió.
function exactMaxEntries(titles, groupByTitle, screensConflict, opts) {
  const required = (opts && opts.required) || new Set();
  const groups = titles
    .map(t => ({ title: t, ...groupByTitle(t) }))
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
    // Rama "este título queda afuera" — prohibida para los exigidos. Si un
    // exigido no cabe en ninguna de sus funciones, el camino muere acá y ese
    // subárbol no aporta ningún máximo: es la definición de prioridades
    // incompatibles.
    if (!required.has(g.title)) dfs(idx + 1);
  })(0);
  return best;
}

module.exports = { exactMaxEntries };
