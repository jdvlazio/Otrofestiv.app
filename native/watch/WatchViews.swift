// ── WatchViews.swift — vistas auxiliares del reloj (F1.2) ─────────────────────
// Poster de fila + estados (mensaje / carga / fallo). Separadas de ContentView
// para mantener cada archivo chico y el pegado a Xcode seguro. Marca: OTStyle.

import SwiftUI

// Poster chico (2:3) — color/marca, como Mi Plan del teléfono. Placeholder para eventos.
struct PosterThumb: View {
    let item: ScheduleItem    // el item entero: la forma la decide posterSource, no la ruta
    var width: CGFloat = 30   // la fila en curso lo pide más grande (héroe, 21 sep 2026)
    private var url: URL? { PlanCompute.posterURL(item.poster) }
    var body: some View {
        // RemoteImage (NSCache + caché HTTP) en vez de AsyncImage: en listas
        // paginadas de watchOS AsyncImage cancela al deslizar y no cachea → los
        // thumbnails cargaban solo en el día abierto (o al entrar al detalle).
        // Editorial (still 16:9 de un CDN oficial) → ancho, sin recortar; póster → 2:3.
        // Radio proporcional (13 % del ancho del 2:3), como las 17 superficies del web.
        let editorial = PlanCompute.isEditorial(item)
        let w = editorial ? width * 1.6 : width
        let h = editorial ? width * 0.9 : width * 1.5
        RemoteImage(url: url) { placeholder }
            .frame(width: w, height: h)
            .clipShape(RoundedRectangle(cornerRadius: width * 0.13, style: .continuous))
    }
    private var placeholder: some View {
        Rectangle().fill(OT.warm.opacity(0.08))
            .overlay(Image(systemName: "film").font(.caption2).foregroundStyle(OT.faint))
    }
}

// ── Estados auxiliares ────────────────────────────────────────────────────────
struct MessageView: View {
    let title: String; let detail: String?
    var body: some View {
        VStack(spacing: 6) {
            Text(title).font(.headline).foregroundStyle(OT.warm).multilineTextAlignment(.center)
            if let d = detail {
                Text(d).font(.caption).foregroundStyle(OT.secondary).multilineTextAlignment(.center)
            }
        }.frame(maxWidth: .infinity, maxHeight: .infinity).padding()
    }
}

struct StatusScreen: View {
    let text: String
    var body: some View {
        VStack(spacing: 8) {
            ProgressView().tint(OT.amber)
            Text(text).font(.footnote).foregroundStyle(OT.secondary).multilineTextAlignment(.center)
        }.padding()
    }
}

struct FailScreen: View {
    let reason: String; let retry: () -> Void
    var body: some View {
        VStack(spacing: 8) {
            Image(systemName: "exclamationmark.triangle.fill").foregroundStyle(OT.amber).font(.title3)
            Text(reason).font(.caption2).foregroundStyle(OT.secondary).multilineTextAlignment(.center)
            Button(L.retry, action: retry).font(.footnote).tint(OT.amber)
        }.padding()
    }
}

// ── Barra de progreso en vivo (21 sep 2026) ───────────────────────────────────
// Blanco cálido, no ámbar: el ámbar es hora + acción; el progreso es estado.
struct LiveBar: View {
    let fraction: Double
    var height: CGFloat = 4
    var wait: Double = 0      // tramo de ESPERA al inicio (retraso), en ámbar
    var body: some View {
        GeometryReader { g in
            ZStack(alignment: .leading) {
                Capsule().fill(OT.warm.opacity(0.16))
                Capsule().fill(OT.warm).frame(width: max(height, g.size.width * fraction))
                if wait > 0 {
                    Capsule().fill(OT.amber.opacity(0.7)).frame(width: max(height, g.size.width * min(wait, fraction)))
                }
            }
        }
        .frame(height: height)
        .accessibilityHidden(true)
    }
}
