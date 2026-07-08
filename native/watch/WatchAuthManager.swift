// ── WatchAuthManager.swift — identidad del reloj (F1.0) ───────────────────────
// Plan: docs/PLAN-apple-watch-F1.md §2. FUENTE CANÓNICA: repo web, native/watch/.
//
// Flujo (el usuario JAMÁS firma en el reloj):
//  1. bootstrap(): si supabase-swift ya tiene sesión persistida (keychain DEL
//     reloj) → listo. El SDK refresca solo de ahí en adelante.
//  2. Sin sesión → pedir handoff al iPhone por WCSession.sendMessage
//     {type:"watch-auth-request"} y esperar {token_hash}.
//  3. Canjear: auth.verifyOTP(tokenHash:type:.email) → SESIÓN PROPIA del reloj
//     (cadena de refresh independiente — nunca la del teléfono; compartir sesión
//     dispara la detección de reuso de Supabase y revoca ambas).
//
// El pase (token_hash) es de un solo uso; lo emite el Edge Function watch-auth
// (valida el JWT del teléfono; el email jamás viaja como parámetro).

import Foundation
import Combine            // @Published / ObservableObject (sin esto no compila en watchOS)
import WatchConnectivity
import Supabase

@MainActor
final class WatchAuthManager: NSObject, ObservableObject {

    enum Status: Equatable {
        case checking            // arrancando / buscando sesión persistida
        case waitingForPhone     // pidiendo handoff al iPhone
        case authenticated(String) // email de la cuenta
        case failed(String)      // motivo (dev-only; UI real en F1.2)
    }

    @Published var status: Status = .checking

    // Mismo proyecto y publishable key que la web (index.html / auth.js).
    static let supabase = SupabaseClient(
        supabaseURL: URL(string: "https://eytxrvbnwzxuedbmnnqr.supabase.co")!,
        supabaseKey: "sb_publishable_-edEGNPRmpsRy7ThJMWtdw_bs6IVZSC"
    )

    private var authRequestContinuation: CheckedContinuation<String, Error>?

    // ── 1. Arranque ───────────────────────────────────────────────────────────
    func bootstrap() async {
        // ¿Sesión persistida en el keychain del reloj? (supabase-swift la maneja)
        if let session = try? await Self.supabase.auth.session {
            status = .authenticated(session.user.email ?? "?")
            return
        }
        await requestHandoffFromPhone()
    }

    // ── 2. Handoff desde el iPhone ────────────────────────────────────────────
    func requestHandoffFromPhone() async {
        status = .waitingForPhone
        guard WCSession.isSupported() else { status = .failed("WCSession no soportado"); return }
        let session = WCSession.default
        session.delegate = self
        if session.activationState != .activated { session.activate() }
        // Espera corta a que la sesión active (activate es async sin await nativo).
        for _ in 0..<20 where session.activationState != .activated {
            try? await Task.sleep(for: .milliseconds(100))
        }
        guard session.isReachable else {
            status = .failed("iPhone no alcanzable — abrí Otrofestiv en el teléfono")
            return
        }
        do {
            let tokenHash = try await withCheckedThrowingContinuation { (cont: CheckedContinuation<String, Error>) in
                authRequestContinuation = cont
                session.sendMessage(["type": "watch-auth-request"], replyHandler: { reply in
                    if let hash = reply["token_hash"] as? String {
                        cont.resume(returning: hash)
                    } else {
                        cont.resume(throwing: WatchAuthError.phone(reply["error"] as? String ?? "sin respuesta"))
                    }
                }, errorHandler: { err in
                    cont.resume(throwing: err)
                })
            }
            authRequestContinuation = nil
            try await redeem(tokenHash: tokenHash)
        } catch {
            authRequestContinuation = nil
            status = .failed(error.localizedDescription)
        }
    }

    // ── 3. Canje del pase → sesión PROPIA ────────────────────────────────────
    private func redeem(tokenHash: String) async throws {
        // type .email (magiclink está deprecado como tipo de verificación).
        try await Self.supabase.auth.verifyOTP(tokenHash: tokenHash, type: .email)
        let session = try await Self.supabase.auth.session
        status = .authenticated(session.user.email ?? "?")
    }
}

enum WatchAuthError: LocalizedError {
    case phone(String)
    var errorDescription: String? {
        switch self { case .phone(let m): return "iPhone: \(m)" }
    }
}

// WCSessionDelegate — mínimo para watchOS (sin los métodos iOS-only).
extension WatchAuthManager: WCSessionDelegate {
    nonisolated func session(_ session: WCSession,
                             activationDidCompleteWith activationState: WCSessionActivationState,
                             error: Error?) {}
}
