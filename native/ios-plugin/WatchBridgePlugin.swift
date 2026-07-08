// ── WatchBridgePlugin.swift — puente iPhone ↔ Apple Watch (F1.0) ───────────────
// Plan: docs/PLAN-apple-watch-F1.md §2-3. FUENTE CANÓNICA: repo web, native/ios-plugin/.
// Se COPIA al proyecto Xcode de Capacitor (ios/App/App/) — el repo nativo no admite
// commits (constitución). Capacitor 6: registrar en MyViewController.capacitorDidLoad
// con bridge?.registerPluginInstance(WatchBridgePlugin()) — ver native/README-F1.md.
//
// Responsabilidad (lado teléfono):
//  1. Activa WCSession y escucha mensajes del reloj.
//  2. Al recibir {type:"watch-auth-request"} → emite el evento "watchAuthRequest"
//     a la capa web (JS) con un requestId, y RETIENE el replyHandler.
//  3. La capa web llama al Edge Function watch-auth con su JWT y responde vía
//     respondAuth({requestId, tokenHash}) → se contesta al reloj por WCSession.
//  4. Si JS no responde en 15 s → reply con error (el reloj reintenta).
//
// El token_hash es un pase de UN SOLO USO (no una sesión) — viaja una vez por el
// canal cifrado de WatchConnectivity y muere al canjearse en el reloj.

import Foundation
import Capacitor
import WatchConnectivity

@objc(WatchBridgePlugin)
public class WatchBridgePlugin: CAPPlugin, CAPBridgedPlugin {
    public let identifier = "WatchBridgePlugin"
    public let jsName = "WatchBridge"
    public let pluginMethods: [CAPPluginMethod] = [
        CAPPluginMethod(name: "respondAuth", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "isWatchReachable", returnType: CAPPluginReturnPromise),
    ]

    // requestId → replyHandler pendiente del reloj (sendMessage espera respuesta).
    private var pendingReplies: [String: ([String: Any]) -> Void] = [:]
    private let repliesQueue = DispatchQueue(label: "app.otrofestiv.watchbridge")

    public override func load() {
        guard WCSession.isSupported() else { return }
        WCSession.default.delegate = WatchSessionDelegate.shared
        WatchSessionDelegate.shared.plugin = self
        WCSession.default.activate()
    }

    // ── API expuesta a JS ────────────────────────────────────────────────────

    /// JS responde un pedido de auth del reloj: {requestId, tokenHash} o {requestId, error}.
    @objc func respondAuth(_ call: CAPPluginCall) {
        guard let requestId = call.getString("requestId") else {
            call.reject("requestId requerido"); return
        }
        repliesQueue.async { [weak self] in
            guard let self, let reply = self.pendingReplies.removeValue(forKey: requestId) else {
                call.reject("request desconocido o expirado"); return
            }
            if let tokenHash = call.getString("tokenHash") {
                reply(["token_hash": tokenHash])
            } else {
                reply(["error": call.getString("error") ?? "unknown"])
            }
            call.resolve()
        }
    }

    @objc func isWatchReachable(_ call: CAPPluginCall) {
        call.resolve(["reachable": WCSession.isSupported() && WCSession.default.isReachable])
    }

    // ── Entrada desde el reloj (via WatchSessionDelegate) ────────────────────

    func handleWatchMessage(_ message: [String: Any], replyHandler: @escaping ([String: Any]) -> Void) {
        guard (message["type"] as? String) == "watch-auth-request" else {
            replyHandler(["error": "unknown message type"]); return
        }
        let requestId = UUID().uuidString
        repliesQueue.async { [weak self] in
            guard let self else { return }
            self.pendingReplies[requestId] = replyHandler
            // Timeout: si la capa web no responde (WebView dormido, sin red), liberar.
            self.repliesQueue.asyncAfter(deadline: .now() + 15) {
                if let orphan = self.pendingReplies.removeValue(forKey: requestId) {
                    orphan(["error": "timeout"])
                }
            }
        }
        notifyListeners("watchAuthRequest", data: ["requestId": requestId])
    }
}

// WCSessionDelegate separado: el delegate debe sobrevivir y WCSession exige NSObject.
final class WatchSessionDelegate: NSObject, WCSessionDelegate {
    static let shared = WatchSessionDelegate()
    weak var plugin: WatchBridgePlugin?

    func session(_ session: WCSession, activationDidCompleteWith state: WCSessionActivationState, error: Error?) {}
    func sessionDidBecomeInactive(_ session: WCSession) {}
    func sessionDidDeactivate(_ session: WCSession) { session.activate() }

    // Pedido interactivo del reloj (reloj en foreground esperando respuesta).
    func session(_ session: WCSession, didReceiveMessage message: [String: Any],
                 replyHandler: @escaping ([String: Any]) -> Void) {
        DispatchQueue.main.async { [weak self] in
            guard let plugin = self?.plugin else { replyHandler(["error": "plugin not loaded"]); return }
            plugin.handleWatchMessage(message, replyHandler: replyHandler)
        }
    }
}
