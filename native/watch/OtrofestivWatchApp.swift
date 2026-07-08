// ── OtrofestivWatchApp.swift — entry point del target watchOS ─────────────────
// F1.0: circuito de identidad (WatchAuthManager). F1.1: plan real (PlanStore).
// FUENTE CANÓNICA: repo web, native/watch/. watchOS 10+, SwiftUI. Dep: supabase-swift.

import SwiftUI

@main
struct OtrofestivWatchApp: App {
    @StateObject private var auth = WatchAuthManager()
    @StateObject private var plan = PlanStore()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(auth)
                .environmentObject(plan)
                .task { await auth.bootstrap() }
        }
    }
}
