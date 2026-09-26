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
    // La lógica de fechas vive en PlanSnapshot (SharedPlan.swift), probada.
    static func timelineDates(from now: Date, snap: PlanSnapshot?) -> [Date] {
        snap?.timelineDates(from: now, preMinutes: preMinutes) ?? [now]
    }
    static func refreshDate(from now: Date, snap: PlanSnapshot?) -> Date {
        snap?.refreshDate(from: now) ?? now.addingTimeInterval(30 * 60)
    }
    // A esa hora: si la «en curso» sigue viva → ella con su progreso; si la siguiente
    // ya arrancó → ella; si no → la siguiente como «próxima».
    static func entry(at date: Date, snap: PlanSnapshot?) -> NextUpEntry {
        for n in [snap?.current, snap?.next].compactMap({ $0 }) where n.isLive(at: date) {
            return NextUpEntry(date: date, next: n,
                               live: LiveState(fraction: n.progress(at: date) ?? 0, minutesLeft: n.minutesLeft(at: date) ?? 0,
                                               wait: n.waitFraction, delayMin: n.delayMin ?? 0),
                               relevance: TimelineEntryRelevance(score: 100, duration: (n.end ?? date).timeIntervalSince(date)))
        }
        let nx = snap?.upcoming(after: date) ?? snap?.next ?? snap?.current
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

struct LiveState: Equatable { let fraction: Double; let minutesLeft: Int; var wait: Double = 0; var delayMin: Int = 0 }

struct NextUpEntry: TimelineEntry {
    let date: Date
    let next: NextUp?
    let live: LiveState?    // nil = «próxima»; con valor = «en curso», con progreso
    var relevance: TimelineEntryRelevance? = nil   // cuánto sube en el Smart Stack
}

// ── Marca (aprobada por Juan, 26 sep 2026) ────────────────────────────────────
// El ícono de la app: la «F» de cuadritos (3×4, escalonada) dentro del anillo
// ámbar. Es una FORMA, así que sobrevive al teñido de la esfera; el color se lo
// da el sistema (.widgetAccentable) o el ámbar donde hay color (Smart Stack).
// OTStyle vive solo en el target de la app; la complication lleva sus dos colores.
enum BrandColor {
    static let amber = Color(red: 0.961, green: 0.620, blue: 0.043)   // #F59E0B
    static let warm  = Color(red: 0.941, green: 0.929, blue: 0.910)   // #F0EDE8
}
struct BrandF: Shape {
    func path(in r: CGRect) -> Path {
        var p = Path()
        let cols = [3, 3, 2, 1]            // cuadritos por fila, de arriba abajo
        let u = min(r.width / 3, r.height / 4), g = u * 0.22, s = u - g
        for (row, n) in cols.enumerated() {
            for c in 0..<n {
                p.addRoundedRect(in: CGRect(x: r.minX + CGFloat(c) * u, y: r.minY + CGFloat(row) * u, width: s, height: s),
                                 cornerSize: CGSize(width: s * 0.22, height: s * 0.22))
            }
        }
        return p
    }
}
struct BrandIcon: View {
    var size: CGFloat
    var body: some View {
        ZStack {
            Circle().stroke(lineWidth: max(1.5, size * 0.13))
            BrandF().frame(width: size * 0.32, height: size * 0.43)
        }
        .frame(width: size, height: size)
    }
}
// Barra de progreso con el tramo de espera al inicio.
struct WaitBar: View {
    let fraction: Double, wait: Double
    var body: some View {
        GeometryReader { g in
            ZStack(alignment: .leading) {
                Capsule().opacity(0.2)
                Capsule().foregroundStyle(BrandColor.amber).frame(width: max(3, g.size.width * fraction)).widgetAccentable()
                if wait > 0 { Capsule().foregroundStyle(BrandColor.amber.opacity(0.4)).frame(width: max(3, g.size.width * min(wait, fraction))) }
            }
        }.frame(height: 4)
    }
}

// ── Vista por familia ───────────────────────────────────────────────────────
struct OtrofestivComplicationEntryView: View {
    @Environment(\.widgetFamily) var family
    @Environment(\.widgetRenderingMode) var mode
    var entry: Provider.Entry

    var body: some View {
        switch family {
        case .accessoryInline:      inline
        case .accessoryCircular:    circular
        case .accessoryCorner:      corner
        default:                    rectangular
        }
    }

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

    // Redonda = el ícono: el anillo grueso ES el progreso (con la espera en ámbar)
    // y la «F» va sobre los minutos. Próxima: el ícono entero + la hora.
    private var circular: some View {
        ZStack {
            AccessoryWidgetBackground()
            if let l = entry.live {
                Circle().stroke(lineWidth: 5.5).opacity(0.2)
                Circle().trim(from: 0, to: l.fraction)
                    .stroke(style: StrokeStyle(lineWidth: 5.5, lineCap: .round)).rotationEffect(.degrees(-90))
                    .foregroundStyle(BrandColor.amber).widgetAccentable()
                if l.wait > 0 {
                    Circle().trim(from: 0, to: min(l.wait, l.fraction))
                        .stroke(style: StrokeStyle(lineWidth: 5.5, lineCap: .butt)).rotationEffect(.degrees(-90))
                        .foregroundStyle(BrandColor.amber.opacity(0.4))
                }
                VStack(spacing: 2) {
                    BrandF().frame(width: 7, height: 9.5).foregroundStyle(BrandColor.amber).widgetAccentable()
                    Text("\(l.minutesLeft)").font(.system(size: 17, weight: .bold)).monospacedDigit()
                }
                .accessibilityElement(children: .ignore)
                .accessibilityLabel(L.endsIn(l.minutesLeft))
            } else {
                VStack(spacing: 2) {
                    BrandIcon(size: 20).foregroundStyle(BrandColor.amber).widgetAccentable()
                    if let n = entry.next {
                        Text(n.time).font(.system(size: 13, weight: .semibold))
                    }
                }
            }
        }
    }

    private var corner: some View {
        BrandF().frame(width: 11, height: 15).foregroundStyle(BrandColor.amber).widgetAccentable()
            .widgetLabel {
                if let n = entry.next {
                    if let l = entry.live { Text(L.endsIn(l.minutesLeft)) }
                    else { Text("\(n.time)  \(n.title)") }
                } else { Text("Otrofestiv") }
            }
    }

    private func poster(_ n: NextUp) -> UIImage? {
        SharedPlan.loadPoster(n.poster).flatMap { UIImage(data: $0) }
    }

    // Rectangular. En la ESFERA (teñida): el ícono firma junto a «Termina en».
    // En el SMART STACK (a todo color): el póster ocupa la tarjeta y el texto va
    // encima, sobre un degradado — como la ficha del reloj.
    @ViewBuilder private var rectangular: some View {
        if mode == .fullColor, let n = entry.next, let ui = poster(n), !n.posterEditorial {
            ZStack(alignment: .bottomLeading) {
                Image(uiImage: ui).resizable().aspectRatio(contentMode: .fill)
                    .frame(maxWidth: .infinity, maxHeight: .infinity).clipped()
                LinearGradient(colors: [.black.opacity(0.1), .black.opacity(0.85)], startPoint: .top, endPoint: .bottom)
                BrandIcon(size: 14).foregroundStyle(BrandColor.amber)
                    .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topTrailing).padding(6)
                VStack(alignment: .leading, spacing: 2) {
                    Text(n.title).font(.headline).lineLimit(1)
                    if let l = entry.live {
                        HStack(spacing: 4) {
                            Text(L.endsIn(l.minutesLeft)).monospacedDigit()
                            if l.delayMin > 0 { Text("· " + L.minLate(l.delayMin)).foregroundStyle(BrandColor.amber) }
                        }.font(.caption2).lineLimit(1)
                        WaitBar(fraction: l.fraction, wait: l.wait)
                    } else {
                        Text("\(n.dayLabel) · \(n.time)").font(.caption2).lineLimit(1)
                    }
                }
                .foregroundStyle(BrandColor.warm).padding(6)
            }
            .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
        } else {
            HStack(alignment: .top, spacing: 8) {
                if let n = entry.next, let ui = poster(n) {
                    Image(uiImage: ui).resizable()
                        .aspectRatio(n.posterEditorial ? 16.0 / 9.0 : 2.0 / 3.0, contentMode: .fill)
                        .frame(width: n.posterEditorial ? 54 : 34, height: n.posterEditorial ? 30 : 51)
                        .clipShape(RoundedRectangle(cornerRadius: 5, style: .continuous))
                }
                VStack(alignment: .leading, spacing: 2) {
                    if let n = entry.next {
                        if let l = entry.live {
                            HStack(spacing: 4) {
                                BrandIcon(size: 12).foregroundStyle(BrandColor.amber).widgetAccentable()
                                Text(L.endsIn(l.minutesLeft)).font(.caption2).fontWeight(.semibold).monospacedDigit().lineLimit(1)
                            }
                            Text(n.title).font(.headline).lineLimit(1)
                            WaitBar(fraction: l.fraction, wait: l.wait)
                            if l.delayMin > 0 { Text(L.startedLate(l.delayMin)).font(.caption2).lineLimit(1).foregroundStyle(BrandColor.amber).widgetAccentable() }
                        } else {
                            HStack(spacing: 4) {
                                BrandIcon(size: 12).foregroundStyle(BrandColor.amber).widgetAccentable()
                                Text("\(n.dayLabel) · \(n.time)").font(.caption2).lineLimit(1)
                            }
                            Text(n.title).font(.headline).lineLimit(2)
                        }
                    } else {
                        HStack(spacing: 4) { BrandIcon(size: 12).foregroundStyle(BrandColor.amber).widgetAccentable(); Text(L.noPlanTitle).font(.headline) }
                        Text(L.noPlanDetail).font(.caption2).foregroundStyle(.secondary).lineLimit(2)
                    }
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
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
