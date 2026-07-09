// ── FilmDetail.swift — detalle del film en el reloj (F1.3) ────────────────────
// Se abre al tocar una fila de Mi Plan. Muestra SOLO lo que ya viaja al reloj en
// saved_agenda: poster grande + título completo + día/hora + sede + duración/tipo.
// Sinopsis/director quedan para una fase futura (ampliar el payload de sync).
// Marca: ámbar SOLO en el ícono de la hora (regla hora+acción); resto secundario.

import SwiftUI

struct FilmDetail: View {
    let item: ScheduleItem
    private var live: Bool { PlanCompute.isLive(item, now: Date()) }

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
        ScrollView {
            VStack(alignment: .leading, spacing: 10) {
                HStack { Spacer(); PosterLarge(path: item.poster); Spacer() }

                if live {
                    Text(L.now)
                        .font(.caption2).fontWeight(.bold).foregroundStyle(OT.green)
                }

                Text(item.title)
                    .font(.headline).foregroundStyle(OT.warm)
                    .fixedSize(horizontal: false, vertical: true)

                VStack(alignment: .leading, spacing: 7) {
                    MetaRow(icon: "clock", text: dayTimeLine, tint: OT.amber)
                    if let v = item.venue {
                        MetaRow(icon: "mappin.and.ellipse", text: v, tint: OT.secondary)
                    }
                    if let d = durationLine {
                        MetaRow(icon: "timer", text: d, tint: OT.secondary)
                    }
                }
                .padding(.top, 2)
            }
            .padding(.horizontal, 4)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .navigationTitle("")
    }
}

private struct PosterLarge: View {
    let path: String?
    private var editorial: Bool { PlanCompute.isEditorial(path) }
    private var url: URL? { PlanCompute.posterURL(path, tmdbSize: "w342") }

    var body: some View {
        artwork.clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
    }

    // Editorial → 16:9 completo a lo ancho. Póster normal → 2:3 fijo 88×132.
    @ViewBuilder private var artwork: some View {
        if editorial {
            image.aspectRatio(16.0 / 9.0, contentMode: .fit).frame(maxWidth: .infinity)
        } else {
            image.frame(width: 88, height: 132)
        }
    }

    @ViewBuilder private var image: some View {
        if let url {
            AsyncImage(url: url) { phase in
                if let img = phase.image { img.resizable().scaledToFill() } else { placeholder }
            }
        } else { placeholder }
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
