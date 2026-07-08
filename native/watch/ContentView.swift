// ── ContentView.swift — UI del reloj (F1.2) ───────────────────────────────────
// Mi Plan = objetivo principal. Navegación PAGINADA POR DÍA (swipe/corona = "flechas").
// Cada fila: poster chico (color/marca, como Mi Plan del teléfono) + hora ámbar + título
// + sede. Función en curso → "AHORA" verde. Marca por color+jerarquía (OTStyle), SF
// Compact (Dynamic Type), fondo true black. La "próxima función" (glance) vive en la
// complication (F1.3). Diseño: docs/PLAN-apple-watch-F1-2.md. Copy aprobado con Juan.

import SwiftUI

struct ContentView: View {
    @EnvironmentObject var auth: WatchAuthManager
    @EnvironmentObject var plan: PlanStore

    var body: some View {
        switch auth.status {
        case .authenticated:      MiPlan()
        case .checking:           StatusScreen(text: "abriendo…")
        case .waitingForPhone:    StatusScreen(text: "conectando con tu iPhone…")
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
            case .idle, .loading:
                ProgressView().tint(OT.amber)
            case .error(let e):
                MessageView(title: "No se pudo cargar", detail: e)
            case .empty:
                MessageView(title: "Sin plan", detail: "Armá tu plan en el teléfono.")
            case .loaded:
                if plan.sections.isEmpty {
                    MessageView(title: "Sin plan", detail: "Armá tu plan en el teléfono.")
                } else {
                    TabView(selection: $day) {
                        ForEach(Array(plan.sections.enumerated()), id: \.element.id) { idx, section in
                            DayPage(section: section).tag(idx)
                        }
                    }
                    .tabViewStyle(.page)
                    .tint(OT.amber)
                }
            }
        }
        .task {
            if case .idle = plan.state { await plan.load() }
        }
        .onChange(of: plan.defaultDay) { _, new in day = new }
    }
}

private struct DayPage: View {
    let section: DaySection
    var body: some View {
        List {
            Section {
                ForEach(section.items) { PlanRow(item: $0) }
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
        HStack(alignment: .top, spacing: 8) {
            PosterThumb(path: item.poster)
            VStack(alignment: .leading, spacing: 2) {
                HStack(spacing: 6) {
                    Text(item.time ?? "—").font(.headline).monospacedDigit().foregroundStyle(OT.amber)
                    if live { Text("AHORA").font(.caption2).fontWeight(.bold).foregroundStyle(OT.green) }
                }
                Text(item.title).font(.subheadline).foregroundStyle(OT.warm).lineLimit(2)
                if let v = item.venue {
                    Text(v).font(.caption2).foregroundStyle(OT.secondary).lineLimit(1)
                }
            }
        }
        .padding(.vertical, 2)
    }
}

// Poster chico (2:3) — color/marca, como Mi Plan del teléfono. Placeholder para eventos.
private struct PosterThumb: View {
    let path: String?
    private var url: URL? {
        guard let p = path, !p.isEmpty else { return nil }
        return URL(string: "https://otrofestiv.app" + p)
    }
    var body: some View {
        Group {
            if let url {
                AsyncImage(url: url) { phase in
                    if let img = phase.image {
                        img.resizable().scaledToFill()
                    } else {
                        placeholder
                    }
                }
            } else {
                placeholder
            }
        }
        .frame(width: 30, height: 45)
        .clipShape(RoundedRectangle(cornerRadius: 4, style: .continuous))
    }
    private var placeholder: some View {
        Rectangle().fill(OT.warm.opacity(0.08))
            .overlay(Image(systemName: "film").font(.caption2).foregroundStyle(OT.faint))
    }
}

// ── Estados auxiliares ────────────────────────────────────────────────────────
private struct MessageView: View {
    let title: String; let detail: String?
    var body: some View {
        VStack(spacing: 6) {
            Text(title).font(.headline).foregroundStyle(OT.warm).multilineTextAlignment(.center)
            if let d = detail {
                Text(d).font(.caption).foregroundStyle(OT.secondary).multilineTextAlignment(.center)
            }
        }.frame(maxWidth: .infinity, maxHeight: .infinity).padding()
    }
}

private struct StatusScreen: View {
    let text: String
    var body: some View {
        VStack(spacing: 8) {
            ProgressView().tint(OT.amber)
            Text(text).font(.footnote).foregroundStyle(OT.secondary).multilineTextAlignment(.center)
        }.padding()
    }
}

private struct FailScreen: View {
    let reason: String; let retry: () -> Void
    var body: some View {
        VStack(spacing: 8) {
            Image(systemName: "exclamationmark.triangle.fill").foregroundStyle(OT.amber).font(.title3)
            Text(reason).font(.caption2).foregroundStyle(OT.secondary).multilineTextAlignment(.center)
            Button("Reintentar", action: retry).font(.footnote).tint(OT.amber)
        }.padding()
    }
}
