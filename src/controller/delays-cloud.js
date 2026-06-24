// ── src/controller/delays-cloud.js ───────────────────────────────────────────
// Retraso colaborativo · Fase A (dual-write). RFC: docs/RFC-retraso-colaborativo.md
//
// `setDelay` ya escribe el retraso LOCAL (recálculo + avisos personales, sin cambios).
// Acá, además, reflejamos ese reporte en Supabase (`screening_reports`) para que
// alimente el consenso en la Fase B. Fase A = solo RECOLECTA: escribe y borra el
// reporte propio; no deriva estado ni pinta badge a terceros.
//
// Identidad = sesión anónima del dispositivo (auth.js). `reporter_id` lo completa
// el servidor con auth.uid() (default de la columna), y la RLS garantiza que solo
// se toca la fila propia. Fire-and-forget: nunca bloquea ni rompe el flujo local.
//
// _sb / _sbUser / _activeFestId son globals del STATE/VIEWSTATE BRIDGE.

// screening_key compartida = título|día|hora|sede (la sede desambigua funciones
// repetidas; el _delayKey local es solo título|día|hora).
export function cloudScreeningKey(title, day, time, venue){
  return (title||'') + '|' + (day||'') + '|' + (time||'') + '|' + (venue||'');
}

// Upsert del reporte propio con el total de minutos vigente para esa función.
export function cloudReportDelay(screeningKey, delayMin){
  if(!_sb || !_sbUser || !screeningKey) return;
  _sb.from('screening_reports').upsert(
    { festival_id: _activeFestId, screening_key: screeningKey, delay_min: delayMin },
    { onConflict: 'festival_id,screening_key,reporter_id' }
  ).then(({ error }) => { if(error) console.warn('[delays-cloud] report:', error.message); });
}

// Borra el reporte propio (clear / retraso vuelto a 0). La RLS (reporter_id =
// auth.uid()) asegura que solo se borra el de uno aunque el filtro no lo incluya.
export function cloudClearDelay(screeningKey){
  if(!_sb || !_sbUser || !screeningKey) return;
  _sb.from('screening_reports').delete()
    .eq('festival_id', _activeFestId)
    .eq('screening_key', screeningKey)
    .then(({ error }) => { if(error) console.warn('[delays-cloud] clear:', error.message); });
}
