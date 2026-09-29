// ── OtrofestivLiveAttributes.swift — el dato de la Live Activity (fase 1, 28 sep 2026)
// COPIA IDÉNTICA en la app (Otrofestiv/OtrofestivLiveAttributes.swift): ActivityKit
// empareja por nombre de tipo y forma Codable. Si cambia uno, cambia el otro.
//
// Fase 1 = sin servidor: la tarjeta solo muestra lo que es cierto en TODO momento
// (horas y sede fijas) y deja que el reloj del sistema haga la cuenta y la barra.
// Nunca dice «Próxima» ni «En curso»: sin push no puede cambiar de fase sola.
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
