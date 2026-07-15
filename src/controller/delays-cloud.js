// ── src/controller/delays-cloud.js ───────────────────────────────────────────
// Retraso colaborativo · Fase A (dual-write). RFC: docs/RFC-retraso-colaborativo.md
//
// `setDelay` ya escribe el retraso LOCAL (recálculo + avisos personales, sin cambios).
// Acá, además, reflejamos ese reporte en Supabase (`screening_reports`) para que
// alimente el consenso en la Fase B. Fase A = solo RECOLECTA: escribe y borra el
// reporte propio; no deriva estado ni pinta badge a terceros.
//
// Identidad = sesión de email del usuario (Camino A; ya no hay auth anónima). Sin
// sesión, los guards `!_sbUser` de report/clear son no-op → el retraso queda solo
// local. `reporter_id` lo completa el servidor con auth.uid() (default de la
// columna), y la RLS garantiza que solo se toca la fila propia. Fire-and-forget:
// nunca bloquea ni rompe el flujo local.
//
// _sb / _sbUser / _activeFestId son globals del STATE/VIEWSTATE BRIDGE.
//
// Fase B: además, nos SUSCRIBIMOS a los reportes del festival (Realtime), los
// cacheamos y exponemos getDelayConsensus() para que el badge derive el estado.

// cloudScreeningKey (constructor de clave, PURO) vive ahora en domain/delays.js.
// Se re-exporta acá para no romper a handlers.js, que lo importa desde este módulo.
import { deriveDelayConsensus, cloudScreeningKey } from '../domain/delays.js';
export { cloudScreeningKey };

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

// ── Fase B — suscripción Realtime + caché + consenso ──────────────────────────
// _reports: screening_key → Map(reporter_id → { delayMin, createdAtMs })
const _reports = new Map();
let _channel = null;
let _channelFest = null;   // festival al que está suscrito el canal actual
let _rerenderCb = null;    // callback de re-render (lo cablea main.js, evita import circular)

export function setDelaysRerender(cb){ _rerenderCb = cb; }
function _rerender(){ if(typeof _rerenderCb === 'function') { try{ _rerenderCb(); }catch(e){ /* noop */ } } }

function _applyRow(row, removed){
  if(!row || !row.screening_key) return;
  const k = row.screening_key;
  if(removed){
    const m = _reports.get(k);
    if(m){ m.delete(row.reporter_id); if(m.size === 0) _reports.delete(k); }
    return;
  }
  let m = _reports.get(k);
  if(!m){ m = new Map(); _reports.set(k, m); }
  m.set(row.reporter_id, { delayMin: row.delay_min, createdAtMs: Date.parse(row.created_at) || Date.now() });
}

// (Re)suscribe al festival activo. Idempotente por festival; tearing-down al cambiar.
// Lo llama loader.js tras cargar un festival (cuando _activeFestId ya es correcto).
export async function subscribeDelaysCloud(){
  if(!_sb || !_activeFestId) return;
  if(_channelFest === _activeFestId && _channel) return; // ya suscrito a este festival
  if(_channel){ try{ _sb.removeChannel(_channel); }catch(e){ /* noop */ } _channel = null; }
  _reports.clear();
  const fest = _activeFestId;
  _channelFest = fest;
  // Carga inicial — Realtime solo trae cambios futuros; los reportes ya existentes
  // se traen una vez. (Guard: si el festival cambió mientras esperábamos, descartar.)
  try{
    const { data } = await _sb.from('screening_reports')
      .select('screening_key,reporter_id,delay_min,created_at')
      .eq('festival_id', fest);
    if(_channelFest === fest){ (data || []).forEach(r => _applyRow(r, false)); _rerender(); }
  }catch(e){ console.warn('[delays-cloud] carga inicial:', e.message); }
  // CARRERA (cazada por T39 al iterar festivales rápido): si el festival cambió
  // durante el await de arriba, abortar — crear el canal igual dejaba un zombie
  // suscrito, y al volver a este festival _sb.channel() devolvía ese zombie →
  // "cannot add postgres_changes callbacks ... after subscribe()".
  if(_channelFest !== fest) return;
  // Cinturón: si quedó un canal vivo con este topic (carrera previa), removerlo
  // antes de re-crear — nunca hacer .on() sobre un canal ya suscrito.
  try{
    const _zombie = _sb.getChannels && _sb.getChannels().find(c => c.topic === 'realtime:sr-' + fest);
    if(_zombie) _sb.removeChannel(_zombie);
  }catch(e){ /* noop */ }
  // Suscripción a cambios de este festival.
  _channel = _sb.channel('sr-' + fest)
    .on('postgres_changes',
      { event: '*', schema: 'public', table: 'screening_reports', filter: 'festival_id=eq.' + fest },
      (payload) => {
        if(payload.eventType === 'DELETE') _applyRow(payload.old, true);
        else _applyRow(payload.new, false);
        _rerender();
      })
    .subscribe();
}

// Mapa de consenso por screening_key (lo consume el badge en renderAgenda, que lo
// pasa como parámetro a las funciones puras del view). Recalcula desde la caché
// con el reloj actual → el decaimiento se aplica en cada render (el tick de 60s y
// los cambios Realtime ambos repintan). nowMs inyectable (tests).
export function getConsensusMap(nowMs){
  const now = nowMs || Date.now();
  const out = {};
  _reports.forEach((m, key) => {
    const reports = [];
    m.forEach((v, reporterId) => reports.push({ reporterId, delayMin: v.delayMin, ageMin: (now - v.createdAtMs) / 60000 }));
    const c = deriveDelayConsensus(reports);
    if(c.state !== 'none') out[key] = c;
  });
  return out;
}
