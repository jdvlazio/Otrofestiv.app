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
    @EnvironmentObject var auth: WatchAuthManager
    @EnvironmentObject var catalog: CatalogStore
    @Environment(\.scenePhase) private var scenePhase
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
                        .navigationTitle(L.miPlan)   // barra nativa, hermana de «Hoy»/«Mañana»
                        // Programa: BOTÓN en la barra, no una página vertical (22 sep 2026).
                        // El pager vertical no llegaba nunca: la lista de días es un TabView
                        // paginado y watchOS le da a ESE la corona y el gesto; el de afuera
                        // no recibía su turno (verificado en device, build 1.12 (1)).
                        .toolbar {
                            ToolbarItem(placement: .topBarLeading) {
                                NavigationLink { ProgramView() } label: {
                                    Image(systemName: "calendar")
                                        .foregroundStyle(OT.amber)
                                        .accessibilityLabel(L.program)
                                }
                            }
                        }
                        .navigationDestination(for: ScheduleItem.self) { FilmDetail(item: $0) }
                    }
                }
            }
        }
        .task {
            // Zona del festival ANTES de calcular el plan (22 sep 2026): la recordada
            // por festival; si nunca llegó, Bogotá. Luego el catálogo la confirma.
            if let fid = auth.activeFestival ?? UserDefaults.standard.string(forKey: WatchAuthManager.activeFestivalKey), !fid.isEmpty {
                _ = CatalogStore.applyRememberedTimeZone(festival: fid)
                Task { await catalog.load(festival: fid) }
            }
            if case .idle = plan.state { await plan.load() }
        }
        // El catálogo trajo otra zona horaria → el plan se recalcula en silencio.
        .onChange(of: catalog.tzVersion) { _, _ in
            if case .loaded = plan.state { Task { await plan.load(silent: true) } }
        }
        .onChange(of: plan.defaultDay) { _, new in day = new }
        // Live-reload: el teléfono cambió el festival en curso → recargar el plan.
        .onChange(of: auth.activeFestival) { _, new in
            guard let new, !new.isEmpty, new != plan.festival else { return }
            _ = CatalogStore.applyRememberedTimeZone(festival: new)
            Task { await catalog.load(festival: new) }
            Task { await plan.load() }
        }
        // Refresco (21 sep 2026): el plan se leía UNA vez por proceso. Ahora se relee
        // en silencio al volver al primer plano (mirás el reloj → está al día) y cuando
        // el teléfono avisa que cambió (con la app abierta → inmediato).
        .onChange(of: scenePhase) { _, phase in
            guard phase == .active, case .loaded = plan.state else { return }
            Task { await plan.load(silent: true) }
            Task { await catalog.refreshIfStale() }
        }
        .onChange(of: auth.planChangedAt) { _, _ in
            if case .loading = plan.state { return }
            if case .idle = plan.state { return }
            Task { await plan.load(silent: true) }
        }
    }
}

private struct DayPage: View {
    let section: DaySection
    var body: some View {
        // TimelineView: la fila en curso avanza sola una vez por minuto (también en
        // pantalla siempre activa). Sin esto «Termina en N min» se congelaba al abrir.
        TimelineView(.everyMinute) { ctx in
            List {
                Section {
                    ForEach(section.items) { item in
                        NavigationLink(value: item) {
                            if PlanCompute.isLive(item, now: ctx.date) { LiveRow(item: item, now: ctx.date) }
                            else { PlanRow(item: item) }
                        }
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
}

// La fila EN CURSO (21 sep 2026): tarjeta propia, póster más grande, barra y la
// frase del teléfono. Las demás filas quedan como estaban (PlanRow).
private struct LiveRow: View {
    let item: ScheduleItem
    let now: Date
    var body: some View {
        HStack(alignment: .top, spacing: 9) {
            PosterThumb(path: item.poster, width: 46)
            VStack(alignment: .leading, spacing: 2) {
                Text(L.now).font(.system(size: 9, weight: .bold)).foregroundStyle(OT.green)
                Text(item.title)
                    .font(.subheadline).fontWeight(.semibold).foregroundStyle(OT.warm)
                    .lineLimit(2).truncationMode(.tail)
                    .fixedSize(horizontal: false, vertical: true)
                if let v = item.venue {
                    Text(v).font(.caption2).foregroundStyle(OT.secondary).lineLimit(1)
                }
                Spacer(minLength: 4)
                LiveBar(fraction: PlanCompute.progress(item, now: now) ?? 0)
                if let m = PlanCompute.minutesLeft(item, now: now) {
                    Text(L.endsIn(m)).font(.caption2).fontWeight(.medium).monospacedDigit()
                        .foregroundStyle(OT.warm)
                }
            }
        }
        .padding(8)
        .background(RoundedRectangle(cornerRadius: 12, style: .continuous).fill(OT.warm.opacity(0.06)))
        .accessibilityElement(children: .combine)
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
