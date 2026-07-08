// ── ContentView.swift — UI del reloj (F1.2) ───────────────────────────────────
// Estructura: TabView vertical paginado (corona) — Página 1 "Lo que sigue" (hero),
// Página 2 "Hoy / Tu plan" (List nativa). Marca por color + jerarquía (OTStyle),
// SF Compact para todo el texto (Dynamic Type). Fondo true black.
// Diseño: docs/PLAN-apple-watch-F1-2.md. Copy es artefacto de diseño (aprobado con Juan).

import SwiftUI

struct ContentView: View {
    @EnvironmentObject var auth: WatchAuthManager
    @EnvironmentObject var plan: PlanStore

    var body: some View {
        switch auth.status {
        case .authenticated:      RootTabs()
        case .checking:           StatusScreen(icon: nil, text: "abriendo…")
        case .waitingForPhone:    StatusScreen(icon: nil, text: "conectando con tu iPhone…")
        case .failed(let reason): FailScreen(reason: reason) { Task { await auth.requestHandoffFromPhone() } }
        }
    }
}

// ── Contenedor de las dos páginas ─────────────────────────────────────────────
private struct RootTabs: View {
    @EnvironmentObject var plan: PlanStore
    var body: some View {
        TabView {
            NavigationStack { NextPage() }
            NavigationStack { TodayPage() }
        }
        .tabViewStyle(.verticalPage)
        .tint(OT.amber)
        .task { if case .idle = plan.state { await plan.load() } }
    }
}

// ── Página 1 · Lo que sigue (hero) ────────────────────────────────────────────
private struct NextPage: View {
    @EnvironmentObject var plan: PlanStore
    var body: some View {
        content
            .containerBackground(OT.amber.opacity(0.12).gradient, for: .navigation)
    }
    @ViewBuilder private var content: some View {
        switch plan.state {
        case .idle, .loading: ProgressView().tint(OT.amber)
        case .error(let e):   MessageView(title: "No se pudo cargar", detail: e)
        case .empty:          MessageView(title: "Sin plan", detail: "Armá tu plan en el teléfono.")
        case .loaded:
            if let item = plan.hero {
                Hero(item: item)
            } else {
                MessageView(title: "El festival terminó", detail: "Este fue tu plan.")
            }
        }
    }
}

private struct Hero: View {
    let item: ScheduleItem
    private var live: Bool { PlanCompute.isLive(item, now: Date()) }
    private var relative: String? {
        guard let s = PlanCompute.startDate(item) else { return nil }
        return PlanCompute.relative(to: s, now: Date())
    }
    var body: some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(live ? "AHORA" : "PRÓXIMA")
                .font(.caption2).fontWeight(.semibold).tracking(1.3)
                .foregroundStyle(live ? OT.green : OT.faint)
            Text(item.time ?? "—")
                .font(.system(.largeTitle, design: .rounded)).fontWeight(.bold)
                .monospacedDigit().foregroundStyle(OT.amber)
            if !live, let rel = relative {
                Text(rel).font(.caption).foregroundStyle(OT.secondary)
            }
            Text(item.title)
                .font(.title3).fontWeight(.semibold)
                .foregroundStyle(OT.warm).lineLimit(3).padding(.top, 3)
            if let venue = item.venue {
                Label(venue, systemImage: "mappin.and.ellipse")
                    .font(.caption).foregroundStyle(OT.secondary).lineLimit(2)
                    .padding(.top, 1)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .leading)
    }
}

// ── Página 2 · Hoy / Tu plan (lista) ──────────────────────────────────────────
private struct TodayPage: View {
    @EnvironmentObject var plan: PlanStore
    var body: some View {
        switch plan.state {
        case .loaded:
            if !plan.today.isEmpty {
                PlanList(header: "HOY", items: plan.today)
            } else if !plan.items.isEmpty {
                PlanList(header: "TU PLAN", items: plan.items)   // festival sin funciones hoy → recap
            } else {
                MessageView(title: "Día libre", detail: "Hoy no tenés funciones.")
            }
        case .idle, .loading: ProgressView().tint(OT.amber)
        default: MessageView(title: "Sin plan", detail: nil)
        }
    }
}

private struct PlanList: View {
    let header: String
    let items: [ScheduleItem]
    var body: some View {
        List {
            Section {
                ForEach(items) { PlanRow(item: $0) }
            } header: {
                Text(header).font(.caption2).fontWeight(.semibold).tracking(1.3)
                    .foregroundStyle(OT.faint)
            }
        }
    }
}

private struct PlanRow: View {
    let item: ScheduleItem
    private var live: Bool { PlanCompute.isLive(item, now: Date()) }
    var body: some View {
        HStack(alignment: .top, spacing: 9) {
            if live {
                Capsule().fill(OT.green).frame(width: 3)
            }
            Text(item.time ?? "—")
                .font(.headline).monospacedDigit().foregroundStyle(OT.amber)
            VStack(alignment: .leading, spacing: 2) {
                Text(item.title).font(.headline).foregroundStyle(OT.warm).lineLimit(2)
                if let v = item.venue {
                    Text(v).font(.caption).foregroundStyle(OT.secondary).lineLimit(1)
                }
                if live {
                    Text("AHORA").font(.caption2).fontWeight(.bold).foregroundStyle(OT.green)
                }
            }
        }
        .padding(.vertical, 2)
    }
}

// ── Estados auxiliares ────────────────────────────────────────────────────────
private struct MessageView: View {
    let title: String
    let detail: String?
    var body: some View {
        VStack(spacing: 6) {
            Text(title).font(.headline).foregroundStyle(OT.warm).multilineTextAlignment(.center)
            if let d = detail {
                Text(d).font(.caption).foregroundStyle(OT.secondary).multilineTextAlignment(.center)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding()
    }
}

private struct StatusScreen: View {
    let icon: String?
    let text: String
    var body: some View {
        VStack(spacing: 8) {
            ProgressView().tint(OT.amber)
            Text(text).font(.footnote).foregroundStyle(OT.secondary).multilineTextAlignment(.center)
        }.padding()
    }
}

private struct FailScreen: View {
    let reason: String
    let retry: () -> Void
    var body: some View {
        VStack(spacing: 8) {
            Image(systemName: "exclamationmark.triangle.fill").foregroundStyle(OT.amber).font(.title3)
            Text(reason).font(.caption2).foregroundStyle(OT.secondary).multilineTextAlignment(.center)
            Button("Reintentar", action: retry).font(.footnote).tint(OT.amber)
        }.padding()
    }
}
