// ── FilmDetail.swift — detalle del film en el reloj (F1.3) ────────────────────
// Se abre al tocar una fila de Mi Plan. Muestra SOLO lo que ya viaja al reloj en
// saved_agenda: poster grande + título completo + día/hora + sede + duración/tipo.
// Sinopsis/director quedan para una fase futura (ampliar el payload de sync).
// Marca: ámbar SOLO en el ícono de la hora (regla hora+acción); resto secundario.

import SwiftUI
import WatchKit   // screenBounds: el tope de alto del póster es proporcional a la pantalla

struct FilmDetail: View {
    @EnvironmentObject var plan: PlanStore
    private let initial: ScheduleItem
    init(item: ScheduleItem) { initial = item }
    // La versión VIVA del plan: al marcar un retraso, la cuenta y la barra se corren
    // acá mismo (el valor de navegación es una copia de cuando se abrió).
    private var item: ScheduleItem { plan.item(id: initial.id) ?? initial }
    private var dayTimeLine: String {
        let day = item.dayStr.map { PlanCompute.dayLabel($0) } ?? ""
        let time = item.time ?? ""
        return [day, time].filter { !$0.isEmpty }.joined(separator: " · ")
    }
    private var durationLine: String? {
        guard let d = item.duration, !d.isEmpty else { return nil }
        return d
    }

    var body: some View {
        // Progreso en vivo (21 sep 2026): TimelineView → «Termina en N min» avanza solo.
        TimelineView(.everyMinute) { ctx in
            ScrollView {
                VStack(alignment: .leading, spacing: 8) {
                    // El póster manda: a sangre arriba, el texto sube sobre un degradado.
                    ZStack(alignment: .bottomLeading) {
                        PosterLarge(item: item)
                        LinearGradient(colors: [.clear, .black.opacity(0.85), .black],
                                       startPoint: .center, endPoint: .bottom)
                            .allowsHitTesting(false)
                        VStack(alignment: .leading, spacing: 3) {
                            if PlanCompute.isLive(item, now: ctx.date) {
                                Text(L.now).font(.system(size: 9, weight: .bold)).tracking(0.6)
                                    .foregroundStyle(OT.green)
                            }
                            Text(item.title)
                                .font(.headline).foregroundStyle(OT.warm)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                        .padding(.horizontal, 8).padding(.bottom, 2)
                    }

                    if let f = PlanCompute.progress(item, now: ctx.date),
                       let m = PlanCompute.minutesLeft(item, now: ctx.date) {
                        VStack(alignment: .leading, spacing: 5) {
                            LiveBar(fraction: f, height: 6, wait: PlanCompute.waitFraction(item))
                            HStack {
                                Text(L.endsIn(m)).font(.footnote).fontWeight(.semibold).monospacedDigit()
                                    .foregroundStyle(OT.warm)
                                Spacer()
                                if let end = PlanCompute.endTimeLabel(item) {
                                    Text(end).font(.footnote).monospacedDigit().foregroundStyle(OT.secondary)
                                }
                            }
                            if PlanCompute.delay(item) > 0 {
                                Text(L.startedLate(PlanCompute.delay(item)))
                                    .font(.footnote).fontWeight(.semibold).foregroundStyle(OT.amber)
                            }
                        }
                        .padding(.horizontal, 8)
                        .accessibilityElement(children: .combine)
                    }

                    if PlanCompute.canMarkDelay(item, now: ctx.date) {
                        DelayControl(item: item).padding(.horizontal, 8)
                    }

                    VStack(alignment: .leading, spacing: 7) {
                        MetaRow(icon: "clock", text: dayTimeLine, tint: OT.amber)
                        if let v = item.venue {
                            MetaRow(icon: "mappin.and.ellipse", text: v, tint: OT.secondary)
                        }
                        if let d = durationLine {
                            MetaRow(icon: "timer", text: d, tint: OT.secondary)
                        }
                    }
                    .padding(.horizontal, 8).padding(.top, 2)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }
        }
        .navigationTitle("")
    }
}

private struct PosterLarge: View {
    let item: ScheduleItem
    private var editorial: Bool { PlanCompute.isEditorial(item) }
    private var url: URL? { PlanCompute.posterURL(item.poster, tmdbSize: "w342") }

    var body: some View {
        artwork.clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
    }

    // Editorial → 16:9 a lo ancho. Póster → 2:3, pero con TOPE DE ALTO: a todo el
    // ancho un 2:3 mide 1,5 pantallas de ancho, más alto que la pantalla entera del
    // Ultra, y el detalle arrancaba con una imagen que no cabía y un scroll larguísimo
    // (23 sep 2026). El mockup aprobado lo mostraba ocupando el tercio de arriba: el
    // tope lo devuelve a eso. Sin recortar, la regla de siempre.
    @ViewBuilder private var artwork: some View {
        if editorial {
            image.aspectRatio(16.0 / 9.0, contentMode: .fit).frame(maxWidth: .infinity)
        } else {
            image.aspectRatio(2.0 / 3.0, contentMode: .fit)
                .frame(maxWidth: .infinity, maxHeight: PosterLarge.maxAlto)
        }
    }
    // 40 % del alto de la pantalla: el póster encabeza, no tapa.
    static var maxAlto: CGFloat { WKInterfaceDevice.current().screenBounds.height * 0.4 }

    // RemoteImage comparte la NSCache con la fila → si el thumb ya cargó, el
    // detalle aparece al instante (y viceversa); reemplaza AsyncImage (flaky).
    private var image: some View {
        RemoteImage(url: url) { placeholder }
    }

    private var placeholder: some View {
        Rectangle().fill(OT.warm.opacity(0.08))
            .overlay(Image(systemName: "film").font(.title3).foregroundStyle(OT.faint))
    }
}

private struct MetaRow: View {
    let icon: String; let text: String; let tint: Color
    var body: some View {
        HStack(alignment: .firstTextBaseline, spacing: 6) {
            Image(systemName: icon).font(.caption2).foregroundStyle(tint).frame(width: 16)
            Text(text).font(.footnote).foregroundStyle(OT.warm)
                .fixedSize(horizontal: false, vertical: true)
        }
    }
}

// ── Marcar el retraso desde el reloj (14 oct 2026, aprobado por Juan) ─────────
// El mismo control de Mi Plan en el teléfono: pregunta + − / + de a 5 min, y la
// corona (tocar el número le da el foco). Sin botón de confirmar: se guarda solo.
private struct DelayControl: View {
    @EnvironmentObject var plan: PlanStore
    let item: ScheduleItem
    @State private var crown: Double = 0
    @FocusState private var focused: Bool
    private var mins: Int { PlanCompute.delay(item) }
    private func set(_ m: Int) {
        guard m != mins, m >= 0 else { return }
        WKInterfaceDevice.current().play(.click)
        plan.setDelay(item, minutes: m)
    }
    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            VStack(alignment: .leading, spacing: 1) {
                Text(mins > 0 ? L.delayState : L.delayAsk)
                    .font(.footnote).fontWeight(.semibold)
                    .foregroundStyle(mins > 0 ? OT.amber : OT.warm)
                Text(mins > 0 ? L.delayScheduled(item.time ?? "") : L.delayHelp)
                    .font(.caption2).foregroundStyle(OT.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
            HStack {
                Button { set(mins - 5) } label: { Image(systemName: "minus").font(.body.weight(.bold)) }
                    .frame(width: 44, height: 44).disabled(mins == 0)
                    .accessibilityLabel(L.minus5)
                Spacer()
                Text(L.delayMins(mins)).font(.title3).fontWeight(.heavy).monospacedDigit()
                    .foregroundStyle(mins > 0 ? OT.amber : OT.warm)
                    .focusable().focused($focused)
                    .digitalCrownRotation($crown, from: 0, through: 240, by: 5, sensitivity: .low,
                                          isContinuous: false, isHapticFeedbackEnabled: true)
                    .onChange(of: crown) { _, v in set(Int((v / 5).rounded()) * 5) }
                Spacer()
                Button { set(mins + 5) } label: { Image(systemName: "plus").font(.body.weight(.bold)) }
                    .frame(width: 44, height: 44)
                    .accessibilityLabel(L.plus5)
            }
            .buttonStyle(.bordered)
        }
        .onAppear { crown = Double(mins) }
        .onChange(of: mins) { _, m in if Int(crown) != m { crown = Double(m) } }
    }
}
