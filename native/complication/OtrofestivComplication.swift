// ── OtrofestivComplication.swift — próxima función en la cara (F1.4) ──────────
// Widget de accesorio (complication + Smart Stack). Lee la "próxima función" del
// App Group (SharedPlan) que escribe la app del reloj. Sin red ni sesión propia:
// solo pinta el snapshot. En la cara, el sistema tinta el accesorio → usamos
// jerarquía + .widgetAccentable() (la hora toma el acento) en vez de color crudo.
// El @main vive en OtrofestivComplicationBundle.swift (no tocar).

import WidgetKit
import SwiftUI

// ── Timeline ──────────────────────────────────────────────────────────────────
struct Provider: TimelineProvider {
    func placeholder(in context: Context) -> NextUpEntry {
        NextUpEntry(date: Date(), next: nil)
    }
    func getSnapshot(in context: Context, completion: @escaping (NextUpEntry) -> Void) {
        completion(NextUpEntry(date: Date(), next: SharedPlan.load()))
    }
    func getTimeline(in context: Context, completion: @escaping (Timeline<NextUpEntry>) -> Void) {
        let next = SharedPlan.load()
        let entry = NextUpEntry(date: Date(), next: next)
        // Al empezar la función, refrescar para que "pase" a la siguiente.
        var refresh = Date().addingTimeInterval(30 * 60)
        if let n = next {
            let start = Date(timeIntervalSince1970: n.startEpoch)
            if start > Date() { refresh = start }
        }
        completion(Timeline(entries: [entry], policy: .after(refresh)))
    }
}

struct NextUpEntry: TimelineEntry {
    let date: Date
    let next: NextUp?
}

// ── Vista por familia ───────────────────────────────────────────────────────
struct OtrofestivComplicationEntryView: View {
    @Environment(\.widgetFamily) var family
    var entry: Provider.Entry

    var body: some View {
        switch family {
        case .accessoryInline:      inline
        case .accessoryCircular:    circular
        case .accessoryCorner:      corner
        default:                    rectangular
        }
    }

    // Una línea: "🎬 10:00 Título"
    private var inline: some View {
        Group {
            if let n = entry.next {
                Label("\(n.time)  \(n.title)", systemImage: "film")
            } else {
                Text("Otrofestiv")
            }
        }
    }

    // Círculo: ícono + hora
    private var circular: some View {
        ZStack {
            AccessoryWidgetBackground()
            VStack(spacing: 1) {
                Image(systemName: "film.fill").font(.system(size: 10))
                if let n = entry.next {
                    Text(n.time).font(.system(size: 13, weight: .semibold)).widgetAccentable()
                }
            }
        }
    }

    // Esquina: ícono + etiqueta curva
    private var corner: some View {
        Image(systemName: "film.fill")
            .widgetLabel {
                Text(entry.next.map { "\($0.time)  \($0.title)" } ?? "Otrofestiv")
            }
    }

    // Rectangular (rico, también Smart Stack)
    private var rectangular: some View {
        VStack(alignment: .leading, spacing: 2) {
            if let n = entry.next {
                Text(n.title).font(.headline).lineLimit(2)
                Text("\(n.dayLabel) · \(n.time)")
                    .font(.caption2).lineLimit(1).widgetAccentable()
            } else {
                Text("Sin plan").font(.headline)
                Text("Armá tu plan en el teléfono.")
                    .font(.caption2).foregroundStyle(.secondary).lineLimit(2)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

// ── Widget ────────────────────────────────────────────────────────────────────
struct OtrofestivComplication: Widget {
    let kind = "OtrofestivComplication"
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: Provider()) { entry in
            OtrofestivComplicationEntryView(entry: entry)
                .containerBackground(for: .widget) { Color.clear }
        }
        .configurationDisplayName("Próxima función")
        .description("Tu próxima película del festival.")
        .supportedFamilies([.accessoryInline, .accessoryCircular, .accessoryCorner, .accessoryRectangular])
    }
}

// ── Preview (canvas de Xcode — datos de muestra) ──────────────────────────────
#Preview(as: .accessoryRectangular) {
    OtrofestivComplication()
} timeline: {
    NextUpEntry(date: .now, next: NextUp(
        title: "Herencia: los cantos de la tierra",
        time: "10:00", venue: "Carpa Cinemateca",
        dayLabel: "SÁB 4 JUL", startEpoch: 0))
    NextUpEntry(date: .now, next: nil)
}
