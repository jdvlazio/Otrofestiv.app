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
              let body = message.body as? [String: Any] else { return }
        // Festival activo (multiplexado por el mismo canal): guardarlo como el
        // último estado que el reloj lee al abrir (F1.6).
        if (body["type"] as? String) == "festival", let fid = body["id"] as? String, !fid.isEmpty {
            try? WCSession.default.updateApplicationContext(["activeFestival": fid])
            return
        }
        // El plan cambió en la web (21 sep 2026): avisar al reloj para que relea la
        // nube. Alcanzable → sendMessage (inmediato); si no, o si falla, transferUserInfo
        // (cola: llega cuando el reloj vuelva). No lleva el plan: el reloj lo lee él.
        if (body["type"] as? String) == "plan", let fid = body["id"] as? String, !fid.isEmpty {
            let s = WCSession.default
            let info: [String: Any] = ["planChanged": fid, "at": Date().timeIntervalSince1970]
            if s.isReachable {
                s.sendMessage(info, replyHandler: nil, errorHandler: { _ in s.transferUserInfo(info) })
            } else {
                s.transferUserInfo(info)
            }
            return
        }
        guard let requestId = body["requestId"] as? String else { return }
        var reply: (([String: Any]) -> Void)?
        q.sync { reply = pending.removeValue(forKey: requestId) }
        guard let reply = reply else { return } // ya expiró / desconocido
        if let hash = body["token_hash"] as? String {
            reply(["token_hash": hash])
        } else {
            reply(["error": body["error"] as? String ?? "unknown"])
        }
    }

    // ── Reloj → teléfono: retraso marcado en el reloj (14 oct 2026) ─────────────
    // Llega por sendMessage (sin respuesta) o transferUserInfo (cola). Dos destinos:
    //  · la Live Activity, NATIVO: corre inicio y fin aunque la web esté dormida;
    //  · la web (Mi Plan), si está viva: guarda el retraso como si lo marcaras ahí.
    // Si la web no estaba viva, al abrir la app lee tus reportes de la nube.
    func session(_ session: WCSession, didReceiveMessage message: [String: Any]) { applyDelay(message) }
    func session(_ session: WCSession, didReceiveUserInfo userInfo: [String: Any] = [:]) { applyDelay(userInfo) }
    private func applyDelay(_ m: [String: Any]) {
        guard (m["type"] as? String) == "delay",
              let title = m["title"] as? String, let day = m["day"] as? String,
              let time = m["time"] as? String, let mins = (m["minutes"] as? NSNumber)?.intValue else { return }
        Task { await LiveActivityBridge.applyDelay(key: "\(title)|\(day)|\(time)", minutes: mins) }
        guard let data = try? JSONSerialization.data(withJSONObject: [
            "festival": m["festival"] as? String ?? "", "key": m["key"] as? String ?? "", "minutes": mins]),
              let json = String(data: data, encoding: .utf8) else { return }
        DispatchQueue.main.async { [weak self] in
            self?.webView?.evaluateJavaScript("window.__otfWatchDelay && window.__otfWatchDelay(\(json))",
                                              completionHandler: nil)
        }
    }

    // WCSessionDelegate — stubs requeridos en iOS.
    func session(_ s: WCSession, activationDidCompleteWith st: WCSessionActivationState, error: Error?) {}
    func sessionDidBecomeInactive(_ s: WCSession) {}
    func sessionDidDeactivate(_ s: WCSession) { s.activate() }
}
