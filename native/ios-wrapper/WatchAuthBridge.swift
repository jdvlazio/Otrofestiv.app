// ── WatchAuthBridge.swift — puente de identidad iPhone → Apple Watch (F1.0) ────
// FUENTE CANÓNICA: repo web (native/ios-wrapper/). Se AGREGA al proyecto SwiftUI
// "Otrofestiv" (el envoltorio iOS real, `app.otrofestiv.mobile`). Calcado del patrón
// del Coordinator del calendario que ya existe en ContentView.swift.
// Plan: docs/PLAN-apple-watch-F1.md §2. Integración: native/README-F1.md.
//
// Doble sentido con la capa web (que tiene la sesión de email):
//   · Reloj → WCSession(sendMessage) → acá → evaluateJavaScript(__otfWatchAuthRequest)
//   · Web → webkit.messageHandlers.watchAuth.postMessage → acá → replyHandler al reloj
// El pase (token_hash) es de UN SOLO USO; nunca se comparte la sesión del teléfono
// (la rotación de refresh tokens de Supabase revocaría ambas).

import Foundation
import WebKit
import WatchConnectivity

final class WatchAuthBridge: NSObject, WCSessionDelegate, WKScriptMessageHandler {
    weak var webView: WKWebView?
    private var pending: [String: ([String: Any]) -> Void] = [:]
    private let q = DispatchQueue(label: "app.otrofestiv.watchauth")

    /// Llamar una vez desde ContentView.makeUIView (después de setear webView).
    func activate() {
        guard WCSession.isSupported() else { return }
        WCSession.default.delegate = self
        WCSession.default.activate()
    }

    // ── Reloj → teléfono: pide auth ───────────────────────────────────────────
    func session(_ session: WCSession, didReceiveMessage message: [String: Any],
                 replyHandler: @escaping ([String: Any]) -> Void) {
        guard (message["type"] as? String) == "watch-auth-request" else {
            replyHandler(["error": "unknown message type"]); return
        }
        let requestId = UUID().uuidString
        q.sync { pending[requestId] = replyHandler }
        // Timeout: si la web no responde (WebView dormido / sin red), liberar el reloj.
        q.asyncAfter(deadline: .now() + 15) { [weak self] in
            var orphan: (([String: Any]) -> Void)?
            self?.q.sync { orphan = self?.pending.removeValue(forKey: requestId) }
            orphan?(["error": "timeout"])
        }
        // Pedirle a la capa web el pase de un solo uso.
        DispatchQueue.main.async { [weak self] in
            self?.webView?.evaluateJavaScript(
                "window.__otfWatchAuthRequest && window.__otfWatchAuthRequest('\(requestId)')",
                completionHandler: nil)
        }
    }

    // ── Web → teléfono: devuelve el pase (o error) ────────────────────────────
    func userContentController(_ uc: WKUserContentController,
                               didReceive message: WKScriptMessage) {
        guard message.name == "watchAuth",
              let body = message.body as? [String: Any],
              let requestId = body["requestId"] as? String else { return }
        var reply: (([String: Any]) -> Void)?
        q.sync { reply = pending.removeValue(forKey: requestId) }
        guard let reply = reply else { return } // ya expiró / desconocido
        if let hash = body["token_hash"] as? String {
            reply(["token_hash": hash])
        } else {
            reply(["error": body["error"] as? String ?? "unknown"])
        }
    }

    // WCSessionDelegate — stubs requeridos en iOS.
    func session(_ s: WCSession, activationDidCompleteWith st: WCSessionActivationState, error: Error?) {}
    func sessionDidBecomeInactive(_ s: WCSession) {}
    func sessionDidDeactivate(_ s: WCSession) { s.activate() }
}
