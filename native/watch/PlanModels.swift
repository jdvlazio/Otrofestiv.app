// ── PlanModels.swift — modelos del plan para el reloj (F1.1) ──────────────────
// FUENTE CANÓNICA: repo web, native/watch/. Espejo de user_festival_state.saved_agenda.
// El schedule ya viene con title/time/venue/day → el reloj NO necesita el JSON del
// festival para "próxima función" + "agenda de hoy". Campos extra del item se ignoran.

import Foundation

// Fila de user_festival_state (solo lo que el reloj usa).
struct UserFestivalRow: Decodable {
    let festivalId: String
    let savedAgenda: SavedAgenda?
    enum CodingKeys: String, CodingKey {
        case festivalId = "festival_id"
        case savedAgenda = "saved_agenda"
    }
}

struct SavedAgenda: Decodable {
    let schedule: [ScheduleItem]
}

// Un ítem del plan. day="2026-07-02", time="20:00" (24h). Lenient: campos opcionales
// para que un ítem raro no rompa la decodificación del arreglo entero.
struct ScheduleItem: Decodable, Identifiable {
    let title: String
    let day: String?
    let date: String?
    let time: String?
    let venue: String?
    let type: String?

    var dayStr: String? { day ?? date }
    var id: String { (dayStr ?? "") + (time ?? "") + title }
}
