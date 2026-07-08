// ── src/controller/watch-bridge.js — respuesta al handoff del Apple Watch (F1.0)
// Plan: docs/PLAN-apple-watch-F1.md §2. Contraparte web del plugin nativo
// WatchBridge (native/ios-plugin/WatchBridgePlugin.swift).
//
// Flujo: el reloj pide auth → el plugin emite "watchAuthRequest" → acá llamamos
// al Edge Function watch-auth con NUESTRO JWT (functions.invoke lo adjunta solo)
// → devolvemos el token_hash (pase de un solo uso) al plugin → WCSession → reloj.
//
// No-op total fuera del contexto correcto: web sin Capacitor, Android, o builds
// iOS sin el plugin. _sb vía STATE BRIDGE (como el resto de controller/).

export function initWatchBridge(){
  const cap=window.Capacitor;
  if(!cap?.isNativePlatform?.()) return;               // solo app nativa
  const plugin=cap.Plugins?.WatchBridge;
  if(!plugin?.addListener) return;                     // build sin el plugin → no-op
  plugin.addListener('watchAuthRequest', async (ev)=>{
    const requestId=ev?.requestId;
    if(!requestId) return;
    try{
      if(!_sb||!_sbUser||_sbUser.is_anonymous||!_sbUser.email) throw new Error('sin sesión de email en el teléfono');
      const {data,error}=await _sb.functions.invoke('watch-auth');
      if(error||!data?.token_hash) throw (error||new Error('sin token'));
      await plugin.respondAuth({requestId, tokenHash:data.token_hash});
    }catch(e){
      // Responder SIEMPRE — el reloj muestra el motivo y ofrece reintentar.
      try{ await plugin.respondAuth({requestId, error:String(e?.message||e)}); }catch(_e){ /* noop */ }
    }
  });
}
