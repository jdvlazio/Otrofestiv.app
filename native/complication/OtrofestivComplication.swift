// ── OtrofestivComplication.swift — próxima función en la cara (F1.4) ──────────
// Widget de accesorio (complication + Smart Stack). Lee la "próxima función" del
// App Group (SharedPlan) que escribe la app del reloj. Sin red ni sesión propia:
// solo pinta el snapshot. En la cara, el sistema tinta el accesorio → usamos
// jerarquía + .widgetAccentable() (la hora toma el acento) en vez de color crudo.
// El @main vive en OtrofestivComplicationBundle.swift (no tocar).

import WidgetKit
import SwiftUI

// ── Timeline ──────────────────────────────────────────────────────────────────
// Progreso en vivo (21 sep 2026): la app publica la función EN CURSO y la SIGUIENTE
// (PlanSnapshot). Mientras hay una en curso, una entrada POR MINUTO con el número
// exacto que faltan (el anillo circular no admite texto relativo del sistema); al
// terminar, la siguiente entra sola. Sin función en curso, una entrada y refresco
// al inicio de la próxima. Tope: 4 h de entradas (WidgetKit acepta cientos).
struct Provider: TimelineProvider {
    func placeholder(in context: Context) -> NextUpEntry {
        NextUpEntry(date: Date(), next: nil, live: nil)
    }
    func getSnapshot(in context: Context, completion: @escaping (NextUpEntry) -> Void) {
        completion(Self.entry(at: Date(), snap: SharedPlan.loadSnapshot()))
    }
    func getTimeline(in context: Context, completion: @escaping (Timeline<NextUpEntry>) -> Void) {
        let snap = SharedPlan.loadSnapshot()
        let now = Date()
        let entries = Self.timelineDates(from: now, snap: snap).map { Self.entry(at: $0, snap: snap) }
        completion(Timeline(entries: entries, policy: .after(Self.refreshDate(from: now, snap: snap))))
    }
    // Instantes de la línea de tiempo: ahora; si hay en curso, cada minuto en punto
    // hasta el fin (máx. 4 h) y uno justo después del fin.
    static func timelineDates(from now: Date, snap: PlanSnapshot?) -> [Date] {
        var dates = [now]
        if let cur = snap?.current, let end = cur.end, end > now {
            var t = now.addingTimeInterval(60 - now.timeIntervalSince1970.truncatingRemainder(dividingBy: 60))
            let cap = now.addingTimeInterval(4 * 3600)
            while t < end && t < cap { dates.append(t); t += 60 }
            dates.append(end.addingTimeInterval(1))
        }
        // Relevancia (25 sep 2026): una entrada 30 min antes de la próxima, para
        // que el Smart Stack la suba ANTES de que empiece.
        if let n = snap?.next {
            let pre = n.start.addingTimeInterval(-Self.preMinutes * 60)
            if pre > now && pre < now.addingTimeInterval(24 * 3600) { dates.append(pre) }
        }
        return dates.sorted()
    }
    static func refreshDate(from now: Date, snap: PlanSnapshot?) -> Date {
        if let cur = snap?.current, let end = cur.end, end > now { return end.addingTimeInterval(2) }
        if let n = snap?.next, n.start > now { return n.start }
        return now.addingTimeInterval(30 * 60)
    }
    // A esa hora: si la «en curso» sigue viva → ella con su progreso; si la siguiente
    // ya arrancó → ella; si no → la siguiente como «próxima».
    static func entry(at date: Date, snap: PlanSnapshot?) -> NextUpEntry {
        for n in [snap?.current, snap?.next].compactMap({ $0 }) where n.isLive(at: date) {
            return NextUpEntry(date: date, next: n,
                               live: LiveState(fraction: n.progress(at: date) ?? 0, minutesLeft: n.minutesLeft(at: date) ?? 0),
                               relevance: TimelineEntryRelevance(score: 100, duration: (n.end ?? date).timeIntervalSince(date)))
        }
        let nx = snap?.next ?? snap?.current
        // «Lo más parecido a Now Playing» sin serlo (Juan, 25 sep 2026): mientras
        // corre una función de tu Plan el Smart Stack sube esta tarjeta sola (100);
        // en los 30 min previos, también (60). Fuera de eso no compite (0).
        var rel = TimelineEntryRelevance(score: 0)
        if let n = nx, n.start > date, n.start.timeIntervalSince(date) <= Self.preMinutes * 60 {
            rel = TimelineEntryRelevance(score: 60, duration: n.start.timeIntervalSince(date))
        }
        return NextUpEntry(date: date, next: nx, live: nil, relevance: rel)
    }
    static let preMinutes: Double = 30
}

struct LiveState: Equatable { let fraction: Double; let minutesLeft: Int }

struct NextUpEntry: TimelineEntry {
    let date: Date
    let next: NextUp?
    let live: LiveState?    // nil = «próxima»; con valor = «en curso», con progreso
    var relevance: TimelineEntryRelevance? = nil   // cuánto sube en el Smart Stack
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

    // Una línea: "🎬 10:00 Título" / en curso: "🎬 Termina en 23 min · Título"
    private var inline: some View {
        Group {
            if let n = entry.next {
                if let l = entry.live { Label("\(L.endsIn(l.minutesLeft))  \(n.title)", image: "otmark") }
                else { Label("\(n.time)  \(n.title)", image: "otmark") }
            } else {
                Text("Otrofestiv")
            }
        }
    }

    // Círculo: próxima → ícono + hora. En curso → ANILLO que se vacía + minutos.
    // Sin póster: la cara tiñe el accesorio de un solo color. Jerarquía, no color.
    private var circular: some View {
        ZStack {
            AccessoryWidgetBackground()
            if let l = entry.live {
                Gauge(value: 1 - l.fraction) { EmptyView() }
                    .gaugeStyle(.accessoryCircularCapacity)
                    .widgetAccentable()
                Text("\(l.minutesLeft)").font(.system(size: 17, weight: .semibold)).monospacedDigit()
                    .accessibilityLabel(L.endsIn(l.minutesLeft))
            } else {
                VStack(spacing: 1) {
                    Image("otmark").resizable().scaledToFit().frame(height: 13)
                    if let n = entry.next {
                        Text(n.time).font(.system(size: 13, weight: .semibold)).widgetAccentable()
                    }
                }
            }
        }
    }

    // Esquina: ícono + etiqueta curva (en curso: los minutos)
    private var corner: some View {
        Image("otmark").resizable().scaledToFit().frame(width: 15, height: 15)
            .widgetLabel {
                if let n = entry.next {
                    if let l = entry.live { Text(L.endsIn(l.minutesLeft)) }
                    else { Text("\(n.time)  \(n.title)") }
                } else { Text("Otrofestiv") }
            }
    }

    // Rectangular (rico, también Smart Stack): a color → entra el póster.
    private var rectangular: some View {
        HStack(alignment: .top, spacing: 8) {
            if let n = entry.next, let data = SharedPlan.loadPoster(n.poster), let ui = UIImage(data: data) {
                Image(uiImage: ui).resizable()
                    .aspectRatio(n.posterEditorial ? 16.0 / 9.0 : 2.0 / 3.0, contentMode: .fill)
                    .frame(width: n.posterEditorial ? 54 : 34, height: n.posterEditorial ? 30 : 51)
                    .clipShape(RoundedRectangle(cornerRadius: 5, style: .continuous))
            }
            VStack(alignment: .leading, spacing: 2) {
                if let n = entry.next {
                    Text(n.title).font(.headline).lineLimit(2)
                    if let l = entry.live {
                        Spacer(minLength: 2)
                        ProgressView(value: l.fraction).progressViewStyle(.linear).tint(.primary)
                        Text(L.endsIn(l.minutesLeft)).font(.caption2).monospacedDigit().lineLimit(1)
                    } else {
                        Text("\(n.dayLabel) · \(n.time)")
                            .font(.caption2).lineLimit(1).widgetAccentable()
                    }
                } else {
                    Text(L.noPlanTitle).font(.headline)
                    Text(L.noPlanDetail)
                        .font(.caption2).foregroundStyle(.secondary).lineLimit(2)
                }
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
        .configurationDisplayName(L.complicationName)
        .description(L.complicationDesc)
        .supportedFamilies([.accessoryInline, .accessoryCircular, .accessoryCorner, .accessoryRectangular])
    }
}

// ── Preview (canvas de Xcode — datos de muestra) ──────────────────────────────
private let _sample = NextUp(
    title: "Herencia: los cantos de la tierra",
    time: "10:00", venue: "Carpa Cinemateca",
    dayLabel: "SÁB 4 JUL", startEpoch: 0)

#Preview("Rectangular", as: .accessoryRectangular) {
    OtrofestivComplication()
} timeline: {
    NextUpEntry(date: .now, next: _sample, live: nil)
    NextUpEntry(date: .now, next: _sample, live: LiveState(fraction: 0.66, minutesLeft: 23))
    NextUpEntry(date: .now, next: nil, live: nil)
}

#Preview("Circular", as: .accessoryCircular) {
    OtrofestivComplication()
} timeline: {
    NextUpEntry(date: .now, next: _sample, live: nil)
    NextUpEntry(date: .now, next: _sample, live: LiveState(fraction: 0.66, minutesLeft: 23))
}
