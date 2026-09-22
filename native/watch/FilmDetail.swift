// ── FilmDetail.swift — detalle del film en el reloj (F1.3) ────────────────────
// Se abre al tocar una fila de Mi Plan. Muestra SOLO lo que ya viaja al reloj en
// saved_agenda: poster grande + título completo + día/hora + sede + duración/tipo.
// Sinopsis/director quedan para una fase futura (ampliar el payload de sync).
// Marca: ámbar SOLO en el ícono de la hora (regla hora+acción); resto secundario.

import SwiftUI

struct FilmDetail: View {
    let item: ScheduleItem
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
                        PosterLarge(path: item.poster)
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
                        .padding(.horizontal, 4).padding(.bottom, 2)
                    }

                    if let f = PlanCompute.progress(item, now: ctx.date),
                       let m = PlanCompute.minutesLeft(item, now: ctx.date) {
                        VStack(alignment: .leading, spacing: 5) {
                            LiveBar(fraction: f, height: 6)
                            HStack {
                                Text(L.endsIn(m)).font(.footnote).fontWeight(.semibold).monospacedDigit()
                                    .foregroundStyle(OT.warm)
                                Spacer()
                                if let end = PlanCompute.endTimeLabel(item) {
                                    Text(end).font(.footnote).monospacedDigit().foregroundStyle(OT.secondary)
                                }
                            }
                        }
                        .padding(.horizontal, 4)
                        .accessibilityElement(children: .combine)
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
                    .padding(.horizontal, 4).padding(.top, 2)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            .ignoresSafeArea(edges: .top)
        }
        .navigationTitle("")
    }
}

private struct PosterLarge: View {
    let path: String?
    private var editorial: Bool { PlanCompute.isEditorial(path) }
    private var url: URL? { PlanCompute.posterURL(path, tmdbSize: "w342") }

    var body: some View {
        artwork.clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
    }

    // Editorial → 16:9 completo a lo ancho. Póster → 2:3 completo a lo ancho
    // (protagonista, 21 sep 2026): sin recortar, la regla de siempre.
    @ViewBuilder private var artwork: some View {
        if editorial {
            image.aspectRatio(16.0 / 9.0, contentMode: .fit).frame(maxWidth: .infinity)
        } else {
            image.aspectRatio(2.0 / 3.0, contentMode: .fit).frame(maxWidth: .infinity)
        }
    }

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
