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
    // Progreso en vivo (21 sep 2026). Opcionales: un snapshot viejo decodifica igual.
    var endEpoch: Double? = nil   // fin de la obra → barra/anillo y «Termina en N min»
    var poster: String? = nil     // path del póster (el widget lo pinta del caché en disco)
    var posterEditorial: Bool = false  // still 16:9: el widget NO lo mete en un 2:3 (23 sep 2026)

    var start: Date { Date(timeIntervalSince1970: startEpoch) }
    var end: Date? { endEpoch.map { Date(timeIntervalSince1970: $0) } }
    func isLive(at now: Date) -> Bool { guard let e = end else { return false }; return start <= now && now < e }
    func progress(at now: Date) -> Double? {
        guard isLive(at: now), let e = end else { return nil }
        return min(1, max(0, now.timeIntervalSince(start) / e.timeIntervalSince(start)))
    }
    func minutesLeft(at now: Date) -> Int? {
        guard isLive(at: now), let e = end else { return nil }
        return Int(ceil(e.timeIntervalSince(now) / 60))
    }
}

// Lo que la app publica para la complication: la función EN CURSO (si hay) y la
// SIGUIENTE. Con las dos, la esfera pasa sola de una a otra sin que la app corra.
struct PlanSnapshot: Codable {
    let current: NextUp?
    let next: NextUp?
}

enum SharedPlan {
    static let suite = "group.app.otrofestiv.watch"
    static let key = "nextUp"          // legado: solo la próxima (widgets viejos)
    static let snapshotKey = "planSnapshot"

    static func save(_ n: NextUp?) { saveSnapshot(PlanSnapshot(current: nil, next: n)) }

    // Nombre distinto a propósito: con dos save(_:) que aceptan nil el compilador
    // no sabe cuál elegir («ambiguous use of 'save'», cazado en el archive 21 sep).
    static func saveSnapshot(_ snap: PlanSnapshot?) {
        guard let d = UserDefaults(suiteName: suite) else { return }
        if let snap, let data = try? JSONEncoder().encode(snap) {
            d.set(data, forKey: snapshotKey)
            // Compat: la clave vieja sigue con «lo que viene» (en curso, si no la siguiente)
            if let n = snap.current ?? snap.next, let nd = try? JSONEncoder().encode(n) { d.set(nd, forKey: key) }
            else { d.removeObject(forKey: key) }
        } else {
            d.removeObject(forKey: snapshotKey); d.removeObject(forKey: key)
        }
        WidgetCenter.shared.reloadAllTimelines()
    }

    static func load() -> NextUp? { loadSnapshot().flatMap { $0.current ?? $0.next } }

    static func loadSnapshot() -> PlanSnapshot? {
        guard let d = UserDefaults(suiteName: suite) else { return nil }
        if let data = d.data(forKey: snapshotKey), let s = try? JSONDecoder().decode(PlanSnapshot.self, from: data) { return s }
        if let data = d.data(forKey: key), let n = try? JSONDecoder().decode(NextUp.self, from: data) { return PlanSnapshot(current: nil, next: n) }
        return nil
    }

    // ── Póster para el widget ─────────────────────────────────────────────────
    // El widget no puede bajar imágenes: la app guarda el JPEG chico en el App
    // Group y el widget lo lee por path. Un archivo por póster (nombre = hash).
    static func posterFileURL(_ path: String) -> URL? {
        guard let dir = FileManager.default.containerURL(forSecurityApplicationGroupIdentifier: suite) else { return nil }
        let name = "poster-" + String(path.hashValue.magnitude) + ".img"
        return dir.appendingPathComponent(name)
    }
    static func savePoster(_ path: String, data: Data) {
        guard let u = posterFileURL(path) else { return }
        try? data.write(to: u, options: .atomic)
    }
    static func loadPoster(_ path: String?) -> Data? {
        guard let p = path, let u = posterFileURL(p) else { return nil }
        return try? Data(contentsOf: u)
    }
}
