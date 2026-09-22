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

struct ScheduleItem: Decodable, Identifiable, Hashable {
    let title: String
    let day: String?
    let date: String?
    let time: String?
    let venue: String?
    let type: String?
    let duration: String?   // "124 min" → estado en vivo
    let poster: String?     // "/assets/ficmontanas/un-poeta.png" (puede faltar en eventos)
    // Del CATÁLOGO (festivals/*.json, Programa en el reloj — 22 sep 2026). En
    // saved_agenda pueden faltar: opcionales con default, el decode no cambia.
    var sala: String? = nil      // "TLB 4" — en la muñeca no cabe la sede completa
    var section: String? = nil   // "📺 Primetime" (verbatim del festival)

    var dayStr: String? { day ?? date }
    var id: String { (dayStr ?? "") + (time ?? "") + title }
}

// ── Catálogo del festival (Programa) ─────────────────────────────────────────
// El reloj es el SEGUNDO lector de festivals/*.json (docs/SCHEMA.md). Decodifica
// solo lo que usa; el resto del JSON se ignora. timezoneOffset ("-04:00") es la
// zona del festival: desde acá se fija PlanCompute.tz (antes Bogotá fijo).
struct Catalog: Decodable {
    let timezoneOffset: String?
    let dayKeys: [String]
    let dayShort: [String: String]?
    let films: [ScheduleItem]
}

// Un tramo de hora del Programa (encabezado "17:00" + sus funciones).
struct HourSection: Identifiable {
    let id: String       // "17:00"
    let items: [ScheduleItem]
}

// Qué día es Hoy y Mañana para el Programa, en la zona del festival.
struct ProgramDays: Equatable {
    let today: String?     // dayKey de hoy si el festival está en curso
    let tomorrow: String?  // dayKey siguiente (o el primero, si aún no empezó)
    let startsOn: String?  // primer dayKey cuando el festival no empezó
    var ended: Bool { today == nil && tomorrow == nil }
}

// Un día del plan (una página en el reloj).
struct DaySection: Identifiable {
    let id: String       // dayStr "2026-07-03"
    let label: String    // "VIE 3 JUL"
    let items: [ScheduleItem]
}
