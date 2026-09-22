// ── ProgramView.swift — Programa en el reloj: Hoy y Mañana (22 sep 2026) ─────
// FUENTE CANÓNICA: repo web, native/watch/. Segunda página de la raíz (bajo Mi
// Plan). Dos páginas horizontales: Hoy (desde la próxima función, con la gracia
// del teléfono) y Mañana (día completo). Solo lectura: agendar es del teléfono.
// Fila: póster (2:3, o editorial 16:9 ancho) + título + «hora ámbar · sala».
// «En tu Plan» = filete ámbar a la izquierda, el mismo idioma que la ficha del
// teléfono (.pel-sheet-screening.in-plan); el texto va solo a accesibilidad.
// Diseño: mockup v3 aprobado por Juan (barra de título nativa, hora del sistema).

import SwiftUI

struct ProgramView: View {
    @EnvironmentObject var catalog: CatalogStore
    @EnvironmentObject var plan: PlanStore

    var body: some View {
        Group {
            switch catalog.state {
            case .idle, .loading: ProgressView().tint(OT.amber)
            case .error(let e):   MessageView(title: L.loadFailed, detail: e)
            case .loaded:
                if let c = catalog.catalog { pages(c) }
                else { MessageView(title: L.loadFailed, detail: nil) }
            }
        }
    }

    @ViewBuilder private func pages(_ c: Catalog) -> some View {
        TimelineView(.everyMinute) { ctx in
            let days = PlanCompute.programDays(c.dayKeys, now: ctx.date)
            NavigationStack {
                TabView {
                    // Hoy: el día en curso, o el vacío «Empieza el…», o (terminado) el último día
                    if let today = days.today {
                        ProgramDayPage(catalog: c, day: today, now: ctx.date, title: L.today)
                    } else if let first = days.startsOn {
                        ProgramEmpty(title: L.startsOn(c.shortDay(first)), detail: L.swipeFirstDay)
                            .navigationTitle(L.today)
                    } else if let last = c.dayKeys.sorted().last {
                        ProgramDayPage(catalog: c, day: last, now: nil, title: PlanCompute.dayLabel(last))
                    }
                    if let tomorrow = days.tomorrow {
                        ProgramDayPage(catalog: c, day: tomorrow, now: nil, title: L.tomorrow)
                    }
                }
                .tabViewStyle(.page)
                .tint(OT.amber)
                .navigationDestination(for: ScheduleItem.self) { FilmDetail(item: $0) }
            }
        }
    }
}

// Un día del Programa: encabezado del día, tramos por hora, filas.
private struct ProgramDayPage: View {
    @EnvironmentObject var store: CatalogStore
    @EnvironmentObject var plan: PlanStore
    let catalog: Catalog
    let day: String
    let now: Date?        // Hoy → desde la próxima; nil → día completo
    let title: String

    private var items: [ScheduleItem] { PlanCompute.program(catalog.films, day: day, now: now) }
    private var planItems: [ScheduleItem] { plan.sections.flatMap { $0.items } }
    // «Programa de hace N h»: la caché envejeció y la red no la renovó.
    private var staleHours: Int? {
        guard let f = store.fetchedAt else { return nil }
        let h = Int(Date().timeIntervalSince(f) / 3600)
        return h >= Int(CatalogStore.maxAge / 3600) ? h : nil
    }

    var body: some View {
        List {
            Section {
                ForEach(PlanCompute.groupedByHour(items)) { hour in
                    Section {
                        ForEach(hour.items) { item in
                            NavigationLink(value: item) {
                                ProgramRow(item: item, inPlan: PlanCompute.inPlan(item, plan: planItems))
                            }
                            .listRowInsets(EdgeInsets(top: 4, leading: 8, bottom: 4, trailing: 8))
                        }
                    } header: {
                        Text(hour.id).font(.caption2).fontWeight(.semibold).tracking(1.2)
                            .foregroundStyle(OT.faint).monospacedDigit()
                    }
                }
                if items.isEmpty {
                    Text(L.noPlanDetail).font(.caption).foregroundStyle(OT.secondary)
                }
            } header: {
                Text(PlanCompute.dayLabel(day))
                    .font(.caption2).fontWeight(.semibold).tracking(1.2).foregroundStyle(OT.faint)
            } footer: {
                if let h = staleHours {
                    Text(L.scheduleFrom(hours: h)).font(.caption2).foregroundStyle(OT.faint)
                }
            }
        }
        .navigationTitle(title)
    }
}

private struct ProgramRow: View {
    let item: ScheduleItem
    let inPlan: Bool
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
                    if let s = item.sala ?? item.venue {
                        Text("·").font(.caption2).foregroundStyle(OT.faint)
                        Text(s).font(.caption).foregroundStyle(OT.secondary)
                            .lineLimit(1).truncationMode(.tail)
                    }
                }
            }
        }
        .frame(minHeight: 45)
        .padding(.leading, inPlan ? 6 : 0)
        .overlay(alignment: .leading) {
            if inPlan {
                Capsule().fill(OT.amber).frame(width: 2).padding(.vertical, 6)
            }
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel(inPlan ? "\(item.title). \(L.inPlan)" : item.title)
    }
}

private struct ProgramEmpty: View {
    let title: String; let detail: String
    var body: some View { MessageView(title: title, detail: detail) }
}
