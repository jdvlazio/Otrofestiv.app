// ── ContentView.swift — UI del reloj (F1.1: plan real) ────────────────────────
// Muestra el plan REAL del usuario (leído de user_festival_state). Los strings
// visibles ("Próxima", "Tu plan"…) son PLACEHOLDER de F1.1 — la UI y el copy
// definitivos llegan en F1.2 con sesión de copy previa con Juan (regla 3).

import SwiftUI

struct ContentView: View {
    @EnvironmentObject var auth: WatchAuthManager
    @EnvironmentObject var plan: PlanStore

    var body: some View {
        switch auth.status {
        case .authenticated:
            PlanView()
        case .checking, .waitingForPhone:
            VStack(spacing: 8) {
                ProgressView()
                Text("conectando…").font(.footnote).foregroundStyle(.secondary)
            }.padding()
        case .failed(let reason):
            VStack(spacing: 8) {
                Image(systemName: "xmark.circle.fill").foregroundStyle(.red).font(.title2)
                Text(reason).font(.caption2).multilineTextAlignment(.center)
                Button("Retry") { Task { await auth.requestHandoffFromPhone() } }.font(.footnote)
            }.padding()
        }
    }
}

private struct PlanView: View {
    @EnvironmentObject var plan: PlanStore

    var body: some View {
        Group {
            switch plan.state {
            case .idle, .loading:
                ProgressView()
            case .empty:
                Text("Sin plan").font(.footnote).foregroundStyle(.secondary)
            case .error(let e):
                VStack(spacing: 6) {
                    Text("Error").font(.footnote)
                    Text(e).font(.caption2).foregroundStyle(.secondary).multilineTextAlignment(.center)
                }.padding()
            case .loaded:
                List {
                    if let n = plan.next {
                        Section("Próxima") { row(n) }
                    }
                    Section("Tu plan (\(plan.items.count))") {
                        ForEach(plan.items) { row($0) }
                    }
                }
            }
        }
        .task { if case .idle = plan.state { await plan.load() } }
    }

    @ViewBuilder private func row(_ i: ScheduleItem) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(i.title).font(.footnote).lineLimit(2)
            Text([i.dayStr, i.time, i.venue].compactMap { $0 }.joined(separator: " · "))
                .font(.caption2).foregroundStyle(.secondary)
        }
    }
}
