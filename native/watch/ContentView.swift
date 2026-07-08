// ── ContentView.swift — UI de DIAGNÓSTICO de F1.0 (dev-only) ──────────────────
// NO es la UI del producto. Muestra el estado del circuito de identidad para
// verificar F1.0 en el simulador/reloj. La UI real ("Lo que sigue" + Agenda de
// hoy) llega en F1.2 con sesión de copy previa con Juan (regla 3 del protocolo)
// — por eso acá no hay strings de producto, solo estado técnico.

import SwiftUI

struct ContentView: View {
    @EnvironmentObject var auth: WatchAuthManager

    var body: some View {
        VStack(spacing: 8) {
            switch auth.status {
            case .checking:
                ProgressView()
                Text("checking session…").font(.footnote).foregroundStyle(.secondary)
            case .waitingForPhone:
                ProgressView()
                Text("waiting for iPhone…").font(.footnote).foregroundStyle(.secondary)
            case .authenticated(let email):
                Image(systemName: "checkmark.circle.fill").foregroundStyle(.green).font(.title2)
                Text(email).font(.footnote).lineLimit(1).truncationMode(.middle)
                Text("session OK — F1.0 ✓").font(.caption2).foregroundStyle(.secondary)
            case .failed(let reason):
                Image(systemName: "xmark.circle.fill").foregroundStyle(.red).font(.title2)
                Text(reason).font(.caption2).multilineTextAlignment(.center)
                Button("Retry") { Task { await auth.requestHandoffFromPhone() } }
                    .font(.footnote)
            }
        }
        .padding()
    }
}
