// ── WatchViews.swift — vistas auxiliares del reloj (F1.2) ─────────────────────
// Poster de fila + estados (mensaje / carga / fallo). Separadas de ContentView
// para mantener cada archivo chico y el pegado a Xcode seguro. Marca: OTStyle.

import SwiftUI

// Poster chico (2:3) — color/marca, como Mi Plan del teléfono. Placeholder para eventos.
struct PosterThumb: View {
    let path: String?
    private var url: URL? { PlanCompute.posterURL(path) }
    var body: some View {
        // RemoteImage (NSCache + caché HTTP) en vez de AsyncImage: en listas
        // paginadas de watchOS AsyncImage cancela al deslizar y no cachea → los
        // thumbnails cargaban solo en el día abierto (o al entrar al detalle).
        RemoteImage(url: url) { placeholder }
            .frame(width: 30, height: 45)
            .clipShape(RoundedRectangle(cornerRadius: 5, style: .continuous))
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
