// ── src/controller/watch-bridge.js — handoff de identidad al Apple Watch (F1.0)
// Plan: docs/PLAN-apple-watch-F1.md §2. Lado TELÉFONO, para el envoltorio iOS real
// (la app SwiftUI "Otrofestiv" — WKWebView nativo, NO Capacitor). Calcado del patrón
// del puente de calendario que ya existe en su ContentView.swift.
//
// Flujo:
//   1. El reloj le pide auth al teléfono por WCSession.
//   2. El envoltorio nativo (WatchAuthBridge.swift) nos LLAMA acá vía
//      evaluateJavaScript → window.__otfWatchAuthRequest(requestId).
//   3. Nosotros (que tenemos la sesión de email) pedimos al Edge Function watch-auth
//      un pase de un solo uso y se lo devolvemos al native por
//      webkit.messageHandlers.watchAuth.postMessage → WCSession → reloj.
//
// Dormido en web/Android: nadie llama __otfWatchAuthRequest ahí. _sb/_sbUser vía
// STATE BRIDGE (se leen al momento de la invocación, ya inicializados).

import { storage } from '../storage/storage.js';

export function initWatchBridge(){
  // Definir SIEMPRE el handler global — es inerte hasta que el envoltorio nativo lo llame.
  window.__otfWatchAuthRequest = async (requestId) => {
    const reply = (msg) => {
      try{ window.webkit?.messageHandlers?.watchAuth?.postMessage(msg); }catch(e){ /* no-op */ }
    };
    try{
      if(!_sb || !_sbUser || _sbUser.is_anonymous || !_sbUser.email){
        throw new Error('sin sesión de email en el teléfono');
      }
      const { data, error } = await _sb.functions.invoke('watch-auth'); // adjunta el JWT solo
      if(error || !data?.token_hash) throw (error || new Error('sin token'));
      reply({ requestId, token_hash: data.token_hash });
    }catch(e){
      reply({ requestId, error: String(e?.message || e) }); // el reloj muestra el motivo y reintenta
    }
  };

  // Empujar el festival EN CURSO al reloj (mismo canal watchAuth, multiplexado por
  // type). El wrapper lo guarda con updateApplicationContext; el reloj consulta ESE
  // festival en vez de adivinar por la fila más reciente. Se llama al boot y cada
  // vez que se cambia de festival (loader.switchFestival). Inerte en web/Android.
  window.__otfPushWatchFestival = () => {
    try{
      const fid = storage.getActiveFestId();
      if(fid) window.webkit?.messageHandlers?.watchAuth?.postMessage({ type:'festival', id: fid });
    }catch(e){ /* no-op */ }
  };
  window.__otfPushWatchFestival();
}
