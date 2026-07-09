// ── ContentView.swift — UI del reloj (F1.2) ───────────────────────────────────
// Mi Plan = objetivo principal. Navegación PAGINADA POR DÍA (swipe/corona = "flechas").
// Cada fila: poster chico (marca) + título (hasta 3 líneas, se lee completo) + línea
// meta "hora ámbar · sede". Función en curso → "AHORA" verde. Filas centradas y de
// altura pareja (patrón Apple Music / Calendar). Vistas auxiliares → WatchViews.swift.
// Diseño: docs/PLAN-apple-watch-F1-2.md. Copy aprobado con Juan.

import SwiftUI

struct ContentView: View {
    @EnvironmentObject var auth: WatchAuthManager
    @EnvironmentObject var plan: PlanStore

    var body: some View {
        switch auth.status {
        case .authenticated:      MiPlan()
        case .checking:           StatusScreen(text: L.opening)
        case .waitingForPhone:    StatusScreen(text: L.connectingPhone)
        case .failed(let reason): FailScreen(reason: reason) { Task { await auth.requestHandoffFromPhone() } }
        }
    }
}

// ── Mi Plan · paginado por día ────────────────────────────────────────────────
private struct MiPlan: View {
    @EnvironmentObject var plan: PlanStore
    @State private var day = 0

    var body: some View {
        Group {
            switch plan.state {
            case .idle, .loading: ProgressView().tint(OT.amber)
            case .error(let e):   MessageView(title: L.loadFailed, detail: e)
            case .empty:          MessageView(title: L.noPlanTitle, detail: L.noPlanDetail)
            case .loaded:
                if plan.sections.isEmpty {
                    MessageView(title: L.noPlanTitle, detail: L.noPlanDetail)
                } else {
                    NavigationStack {
                        TabView(selection: $day) {
                            ForEach(Array(plan.sections.enumerated()), id: \.element.id) { idx, section in
                                DayPage(section: section).tag(idx)
                            }
                        }
                        .tabViewStyle(.page)
                        .tint(OT.amber)
                        .navigationDestination(for: ScheduleItem.self) { FilmDetail(item: $0) }
                    }
                }
            }
        }
        .task { if case .idle = plan.state { await plan.load() } }
        .onChange(of: plan.defaultDay) { _, new in day = new }
    }
}

private struct DayPage: View {
    let section: DaySection
    var body: some View {
        List {
            Section {
                ForEach(section.items) { item in
                    NavigationLink(value: item) { PlanRow(item: item) }
                        .listRowInsets(EdgeInsets(top: 6, leading: 8, bottom: 6, trailing: 8))
                }
            } header: {
                Text(section.label)
                    .font(.caption2).fontWeight(.semibold).tracking(1.2)
                    .foregroundStyle(OT.faint)
            }
        }
    }
}

private struct PlanRow: View {
    let item: ScheduleItem
    private var live: Bool { PlanCompute.isLive(item, now: Date()) }
    var body: some View {
        HStack(alignment: .center, spacing: 8) {
            PosterThumb(path: item.poster)
            VStack(alignment: .leading, spacing: 3) {
                Text(item.title)
                    .font(.subheadline).fontWeight(.medium).foregroundStyle(OT.warm)
                    .lineLimit(3).truncationMode(.tail)
                    .fixedSize(horizontal: false, vertical: true)
                HStack(spacing: 5) {
                    Text(item.time ?? "—")
                        .font(.caption).monospacedDigit().fontWeight(.semibold)
                        .foregroundStyle(OT.amber)
                    if live {
                        Text(L.now).font(.caption2).fontWeight(.bold).foregroundStyle(OT.green)
                    }
                    if let v = item.venue {
                        Text("·").font(.caption2).foregroundStyle(OT.faint)
                        Text(v).font(.caption).foregroundStyle(OT.secondary)
                            .lineLimit(1).truncationMode(.tail)
                    }
                }
            }
        }
        .frame(minHeight: 45)
    }
}
