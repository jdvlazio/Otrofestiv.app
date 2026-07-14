// ── src/telemetry.js ──────────────────────────────────────────────────────────
// report(err, ctx) — envía a Sentry un error CAPTURADO (try/catch). Sentry solo
// captura los NO-atrapados por sí mismo; los paths que hacen catch (carga de
// festival, sync de nube) los tragan → invisibles para el equipo en el dashboard.
// report() los hace visibles con un tag de contexto. No-op si Sentry no cargó, y
// filtrado por su beforeSend en localhost/headless (ver index.html). Nunca lanza.
export function report(err, ctx){
  try{ window.Sentry?.captureException?.(err, ctx?{tags:{ctx}}:undefined); }catch(e){/* noop */}
}
