// ── SharedPlan.swift — puente app-del-reloj ↔ complication (F1.4) ──────────────
// MIEMBRO DE DOS TARGETS: "OtrofestivWatch Watch App" (escribe) y
// "OtrofestivComplication" (lee). La complication corre en su propio proceso, así
// que el dato viaja por un App Group (UserDefaults compartido). El reloj guarda la
// "próxima función"; el widget la pinta en la cara. Al guardar, refresca timelines.

import Foundation
import WidgetKit

// Resumen mínimo que necesita la cara del reloj.
struct NextUp: Codable {
    let title: String
    let time: String        // "10:00"
    let venue: String?
    let dayLabel: String     // "SÁB 4 JUL"
    let startEpoch: Double    // inicio (segundos desde 1970) — validez del timeline
}

enum SharedPlan {
    static let suite = "group.app.otrofestiv.watch"
    static let key = "nextUp"

    static func save(_ n: NextUp?) {
        guard let d = UserDefaults(suiteName: suite) else { return }
        if let n, let data = try? JSONEncoder().encode(n) {
            d.set(data, forKey: key)
        } else {
            d.removeObject(forKey: key)
        }
        WidgetCenter.shared.reloadAllTimelines()
    }

    static func load() -> NextUp? {
        guard let d = UserDefaults(suiteName: suite),
              let data = d.data(forKey: key),
              let n = try? JSONDecoder().decode(NextUp.self, from: data) else { return nil }
        return n
    }
}
