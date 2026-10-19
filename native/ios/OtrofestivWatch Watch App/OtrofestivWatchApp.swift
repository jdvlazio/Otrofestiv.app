// ── OtrofestivWatchApp.swift — entry point del target watchOS ─────────────────
// F1.0: circuito de identidad (WatchAuthManager). F1.1: plan real (PlanStore).
// FUENTE CANÓNICA: repo web, native/watch/. watchOS 10+, SwiftUI. Dep: supabase-swift.

import SwiftUI

@main
struct OtrofestivWatchApp: App {
    @StateObject private var auth = WatchAuthManager()
    @StateObject private var plan = PlanStore()
    @StateObject private var catalog = CatalogStore()   // Programa + zona del festival (22 sep 2026)

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(auth)
                .environmentObject(plan)
                .environmentObject(catalog)
                .task { await auth.bootstrap() }
        }
    }
}
