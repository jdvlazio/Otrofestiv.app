// ── src/domain/delays.js ──────────────────────────────────────────────────────
// Retraso colaborativo · Fase B — derivación PURA del consenso desde los reportes.
// Sin I/O ni deps → testeable directo. RFC: docs/RFC-retraso-colaborativo.md §7–§8.
//
// El estado "confirmado" NO se almacena: se deriva acá del conjunto de reportes
// vigentes (estilo CRDT convergente — cada cliente computa lo mismo).

// cloudScreeningKey(title,day,time,venue) → clave compartida de una función:
// título|día|hora|sede. La sede desambigua funciones repetidas (el _delayKey local
// es solo título|día|hora). PURA — antes vivía en controller/delays-cloud.js, pero la
// consume tanto el view (agenda) como el controller (handlers); su lugar es el dominio.
export function cloudScreeningKey(title, day, time, venue){
  return (title||'') + '|' + (day||'') + '|' + (time||'') + '|' + (venue||'');
}

// reports: [{ reporterId, delayMin, ageMin }]
//   ageMin = minutos desde que se creó/actualizó el reporte (decaimiento).
// Reglas:
//   - Ignora reportes expirados (ageMin > maxAgeMin, default 120) y los de 0 min
//     (retraso limpiado → no cuenta).
//   - Un reporte vigente por reporter (el más reciente) → el quórum cuenta
//     IDENTIDADES distintas, no reportes (anti "una persona, varios reportes").
//   - Estado: none (0) · tentative (1, "sin confirmar") · confirmed (≥2).
//   - delayMin = mediana de los minutos vigentes (robusta ante un valor outlier).
export function deriveDelayConsensus(reports, maxAgeMin = 120) {
  const byReporter = new Map();
  for (const r of (reports || [])) {
    if (!r || typeof r.delayMin !== 'number' || r.delayMin <= 0) continue;
    if (typeof r.ageMin === 'number' && r.ageMin > maxAgeMin) continue;
    const prev = byReporter.get(r.reporterId);
    if (!prev || (r.ageMin ?? 0) < (prev.ageMin ?? 0)) byReporter.set(r.reporterId, r);
  }
  const vals = [...byReporter.values()].map(r => r.delayMin).sort((a, b) => a - b);
  const n = vals.length;
  if (n === 0) return { state: 'none', delayMin: 0, reporters: 0 };
  const median = n % 2
    ? vals[(n - 1) / 2]
    : Math.round((vals[n / 2 - 1] + vals[n / 2]) / 2);
  return { state: n >= 2 ? 'confirmed' : 'tentative', delayMin: median, reporters: n };
}
