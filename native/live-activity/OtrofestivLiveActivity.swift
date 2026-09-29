// ── OtrofestivLiveActivity.swift — la tarjeta en vivo (fase 1, aprobada 28 sep 2026)
// Pantalla bloqueada, Dynamic Island y, desde watchOS 11, el Smart Stack del reloj.
// Identidad (mockup v2): fondo #0B0A08 con filo ámbar, Plus Jakarta Sans, póster con
// el radio proporcional de la app, el ícono (anillo ámbar + F de cuadritos).
// Información: SOLO lo que es cierto en todo momento — horas y sede fijas — y el
// reloj del sistema para la cuenta y la barra (corren solos, sin la app).
import ActivityKit
import WidgetKit
import SwiftUI
import UIKit

private enum Brand {
    static let amber = Color(red: 0.961, green: 0.620, blue: 0.043)   // #F59E0B
    static let warm  = Color(red: 0.941, green: 0.929, blue: 0.910)   // #F0EDE8
    static let bg    = Color(red: 0.043, green: 0.039, blue: 0.031)   // #0B0A08
    static let sec   = Color(red: 0.941, green: 0.929, blue: 0.910).opacity(0.62)
    static func font(_ size: CGFloat, _ w: Int) -> Font {
        .custom(w >= 800 ? "PlusJakartaSans-ExtraBold" : w >= 700 ? "PlusJakartaSans-Bold" : "PlusJakartaSans-SemiBold", size: size)
    }
    static let group = "group.app.otrofestiv.watch"
}

// El ícono de la app: la F de cuadritos (3×4 escalonada) dentro del anillo ámbar.
private struct BrandF: Shape {
    func path(in r: CGRect) -> Path {
        var p = Path(); let cols = [3, 3, 2, 1]
        let u = min(r.width / 3, r.height / 4), g = u * 0.22, s = u - g
        for (row, n) in cols.enumerated() { for c in 0..<n {
            p.addRoundedRect(in: CGRect(x: r.minX + CGFloat(c) * u, y: r.minY + CGFloat(row) * u, width: s, height: s),
                             cornerSize: CGSize(width: s * 0.22, height: s * 0.22)) } }
        return p
    }
}
private struct BrandIcon: View {
    var size: CGFloat
    var body: some View {
        ZStack {
            Circle().stroke(Brand.amber, lineWidth: max(1.6, size * 0.13))
            BrandF().fill(Brand.amber).frame(width: size * 0.32, height: size * 0.43)
        }.frame(width: size, height: size)
    }
}

private func hhmm(_ d: Date) -> String {
    var c = Calendar(identifier: .gregorian); c.timeZone = .current
    let x = c.dateComponents([.hour, .minute], from: d)
    return String(format: "%02d:%02d", x.hour ?? 0, x.minute ?? 0)
}
private func lateText(_ st: OtrofestivLiveAttributes.ContentState) -> String {
    st.lang == "en" ? "Started \(st.delayMin) min late" : "Empezó \(st.delayMin) min tarde"
}

// Póster: del App Group (la app lo dejó ahí). Radio proporcional 13% como en la app.
// Still 16:9 va horizontal, sin recortar. Evento sin póster: el afiche de la app.
private struct Poster: View {
    let st: OtrofestivLiveAttributes.ContentState
    var height: CGFloat
    var body: some View {
        let w = st.posterEditorial ? height * 16 / 9 : height * 2 / 3
        Group {
            if let f = st.posterFile,
               let url = FileManager.default.containerURL(forSecurityApplicationGroupIdentifier: Brand.group)?
                   .appendingPathComponent("live/\(f)"),
               let ui = UIImage(contentsOfFile: url.path) {
                Image(uiImage: ui).resizable().aspectRatio(contentMode: .fill)
            } else {
                ZStack(alignment: .topLeading) {
                    Brand.bg
                    Text(st.kindLabel ?? "OTROFESTIV").font(Brand.font(height * 0.14, 800))
                        .foregroundStyle(Brand.amber).padding(height * 0.06)
                        .minimumScaleFactor(0.5).lineLimit(1)
                }
            }
        }
        .frame(width: w, height: height)
        .clipShape(RoundedRectangle(cornerRadius: w * 0.13, style: .continuous))
    }
}

// Cuenta regresiva del sistema: antes de empezar muestra la duración completa quieta;
// desde el inicio corre sola hasta el fin. Nunca afirma una fase que no sabe.
private struct Countdown: View {
    let st: OtrofestivLiveAttributes.ContentState
    var size: CGFloat = 20
    var body: some View {
        Text(timerInterval: st.start...st.end, countsDown: true)
            .font(Brand.font(size, 800)).monospacedDigit().foregroundStyle(Brand.warm)
    }
}
private struct Bar: View {
    let st: OtrofestivLiveAttributes.ContentState
    var body: some View {
        ProgressView(timerInterval: st.start...st.end, countsDown: false) { EmptyView() } currentValueLabel: { EmptyView() }
            .progressViewStyle(.linear).tint(Brand.amber)
    }
}

struct OtrofestivLiveActivity: Widget {
    var body: some WidgetConfiguration {
        ActivityConfiguration(for: OtrofestivLiveAttributes.self) { ctx in
            LockView(st: ctx.state)
                .widgetURL(URL(string: "otrofestiv://plan"))
                .activityBackgroundTint(Brand.bg)
                .activitySystemActionForegroundColor(Brand.amber)
        } dynamicIsland: { ctx in
            DynamicIsland {
                DynamicIslandExpandedRegion(.leading) { Poster(st: ctx.state, height: 58).padding(.leading, 4) }
                DynamicIslandExpandedRegion(.trailing) { BrandIcon(size: 18).padding(.trailing, 4) }
                DynamicIslandExpandedRegion(.center) {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(ctx.state.title).font(Brand.font(15, 800)).foregroundStyle(Brand.warm).lineLimit(1)
                        Text("\(hhmm(ctx.state.start)) – \(hhmm(ctx.state.end)) · \(ctx.state.venue)")
                            .font(Brand.font(11, 600)).foregroundStyle(Brand.sec).lineLimit(1)
                    }.frame(maxWidth: .infinity, alignment: .leading)
                }
                DynamicIslandExpandedRegion(.bottom) {
                    VStack(alignment: .leading, spacing: 4) {
                        HStack { Countdown(st: ctx.state, size: 18); Spacer()
                            if ctx.state.delayMin > 0 { Text(lateText(ctx.state)).font(Brand.font(11, 700)).foregroundStyle(Brand.amber) } }
                        Bar(st: ctx.state)
                    }
                }
            } compactLeading: {
                Poster(st: ctx.state, height: 22)
            } compactTrailing: {
                Text(timerInterval: ctx.state.start...ctx.state.end, countsDown: true)
                    .font(Brand.font(13, 700)).monospacedDigit().foregroundStyle(Brand.amber)
                    .frame(maxWidth: 52)
            } minimal: {
                BrandIcon(size: 18)
            }
            .keylineTint(Brand.amber)
            .widgetURL(URL(string: "otrofestiv://plan"))
        }
        .supplementalActivityFamilies([.small])
    }
}

// Pantalla bloqueada (y el reloj, en su tamaño chico).
private struct LockView: View {
    let st: OtrofestivLiveAttributes.ContentState
    @Environment(\.activityFamily) var family
    var body: some View {
        if family == .small {
            VStack(alignment: .leading, spacing: 3) {
                HStack(spacing: 5) { BrandIcon(size: 12)
                    Text(st.title).font(Brand.font(13, 800)).foregroundStyle(Brand.warm).lineLimit(1) }
                Countdown(st: st, size: 15)
                Bar(st: st)
            }.padding(8)
        } else {
            HStack(alignment: .top, spacing: 11) {
                Poster(st: st, height: 69)
                VStack(alignment: .leading, spacing: 3) {
                    HStack(alignment: .top) {
                        Text(st.title).font(Brand.font(15, 800)).foregroundStyle(Brand.warm).lineLimit(2)
                        Spacer(minLength: 6)
                        BrandIcon(size: 16)
                    }
                    Text("\(hhmm(st.start)) – \(hhmm(st.end)) · \(st.venue)")
                        .font(Brand.font(11.5, 600)).foregroundStyle(Brand.sec).lineLimit(1)
                    Spacer(minLength: 2)
                    Countdown(st: st)
                    Bar(st: st)
                    if st.delayMin > 0 {
                        Text(lateText(st)).font(Brand.font(11, 700)).foregroundStyle(Brand.amber)
                    }
                }
            }
            .padding(12)
            .overlay(RoundedRectangle(cornerRadius: 22, style: .continuous).stroke(Brand.amber.opacity(0.14), lineWidth: 1))
        }
    }
}
