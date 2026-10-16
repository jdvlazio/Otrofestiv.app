// ── OtrofestivLiveAttributes.swift — el dato de la Live Activity (fase 1, 28 sep 2026)
// COPIA IDÉNTICA en la app (Otrofestiv/OtrofestivLiveAttributes.swift): ActivityKit
// empareja por nombre de tipo y forma Codable. Si cambia uno, cambia el otro.
//
// Fase 1 = sin servidor: horas y sede fijas, y el reloj del sistema hace la cuenta
// y la barra. Desde el 14 oct 2026 cambia de fase sola sin push: el staleDate es el
// inicio real, e iOS la redibuja a esa hora («Empieza en» → «Termina en»).
import ActivityKit
import Foundation

struct OtrofestivLiveAttributes: ActivityAttributes {
    public struct ContentState: Codable, Hashable {
        var title: String
        var venue: String
        var start: Date          // inicio REAL (programado + retraso)
        var end: Date            // fin REAL
        var delayMin: Int        // «Empezó N min tarde» (0 = a tiempo)
        var posterFile: String?  // archivo en el App Group (la extensión no baja imágenes)
        var posterEditorial: Bool
        var kindLabel: String?   // «CHARLA», «TALLER»… si no hay póster
        var lang: String         // "es" | "en"
    }
    var festival: String
}
