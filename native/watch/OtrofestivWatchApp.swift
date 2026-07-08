// ── OtrofestivWatchApp.swift — entry point del target watchOS (F1.0) ──────────
// Plan: docs/PLAN-apple-watch-F1.md. FUENTE CANÓNICA: repo web, native/watch/.
// Target: watchOS 10+, SwiftUI puro. Dependencia: supabase-swift (SPM,
// https://github.com/supabase/supabase-swift — productos Auth y PostgREST).
//
// F1.0: SOLO el circuito de identidad (handoff iPhone → sesión propia del reloj).
// La UI de esta fase es de diagnóstico (dev-only) — la UI real y todo copy visible
// llegan en F1.2 con sesión de copy previa (regla 3 del protocolo).

import SwiftUI

@main
struct OtrofestivWatchApp: App {
    @StateObject private var auth = WatchAuthManager()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(auth)
                .task { await auth.bootstrap() }
        }
    }
}
