// ── PlanModels.swift — modelos del plan para el reloj (F1.2) ──────────────────
// FUENTE CANÓNICA: repo web, native/watch/. Espejo de user_festival_state.saved_agenda.
// El schedule trae title/time/venue/day/poster/duration → suficiente para Mi Plan por día.

import Foundation

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

struct ScheduleItem: Decodable, Identifiable {
    let title: String
    let day: String?
    let date: String?
    let time: String?
    let venue: String?
    let type: String?
    let duration: String?   // "124 min" → estado en vivo
    let poster: String?     // "/assets/ficmontanas/un-poeta.png" (puede faltar en eventos)

    var dayStr: String? { day ?? date }
    var id: String { (dayStr ?? "") + (time ?? "") + title }
}

// Un día del plan (una página en el reloj).
struct DaySection: Identifiable {
    let id: String       // dayStr "2026-07-03"
    let label: String    // "VIE 3 JUL"
    let items: [ScheduleItem]
}
