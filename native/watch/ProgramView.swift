// ── ProgramView.swift — Programa en el reloj: Hoy y Mañana (22 sep 2026) ─────
// FUENTE CANÓNICA: repo web, native/watch/. Se abre desde el botón de calendario
// de Mi Plan y vive DENTRO de su pila de navegación (volver = flecha o gesto).
// Dos páginas laterales con los días que correspondan. Solo lectura: agendar es
// del teléfono. Fila: póster (2:3, o editorial 16:9 ancho) + título + «hora ámbar
// · sala». «En tu Plan» = filete ámbar a la izquierda, el mismo idioma que la
// ficha del teléfono; el texto va solo a accesibilidad.
//
// Dos correcciones verificadas en device (build 1.12 (2), fotos de Juan):
//  1. El título NO puede ir en cada página: en un TabView watchOS se queda con el
//     de la primera y decía «Today» sobre el jueves 24. Va en el TabView, atado a
//     la página seleccionada.
//  2. «Hoy» y «Mañana» solo cuando SON hoy y mañana. Con el festival sin empezar
//     el título es el día con su fecha, y la página de «Empieza el…» desaparece:
//     ver la programación del primer día es más útil que un aviso.

import SwiftUI

struct ProgramView: View {
    @EnvironmentObject var catalog: CatalogStore
    @EnvironmentObject var plan: PlanStore
    @State private var page = 0

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
            if days.days.isEmpty {
                MessageView(title: L.noPlanTitle, detail: nil)
            } else {
                TabView(selection: $page) {
                    ForEach(Array(days.days.enumerated()), id: \.element) { idx, day in
                        ProgramDayPage(catalog: c, day: day,
                                       now: day == days.todayKey ? ctx.date : nil)
                            .tag(idx)
                    }
                }
                .tabViewStyle(.page)
                .tint(OT.amber)
                // El título vive acá, no en cada página (ver cabecera).
                .navigationTitle(title(days, c))
            }
        }
    }

    // «Hoy» / «Mañana» solo cuando es cierto; si no, el día con su fecha.
    private func title(_ days: ProgramDays, _ c: Catalog) -> String {
        guard let day = days.days.indices.contains(page) ? days.days[page] : days.days.first else { return L.program }
        if day == days.todayKey { return L.today }
        if day == days.tomorrowKey { return L.tomorrow }
        return c.shortDay(day)
    }
}

// Un día del Programa: tramos por hora y sus funciones.
private struct ProgramDayPage: View {
    @EnvironmentObject var store: CatalogStore
    @EnvironmentObject var plan: PlanStore
    let catalog: Catalog
    let day: String
    let now: Date?        // Hoy → desde la próxima; nil → día completo

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
            // Secciones por hora, SIN anidar (anidadas, watchOS pintaba la hora
            // como una tarjeta vacía — device, 22 sep 2026).
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
                Text(catalog.shortDay(day)).font(.caption).foregroundStyle(OT.secondary)
            }
            if let h = staleHours {
                Text(L.scheduleFrom(hours: h)).font(.caption2).foregroundStyle(OT.faint)
            }
        }
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
