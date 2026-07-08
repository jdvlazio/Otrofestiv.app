// ── PlanCompute.swift — cómputo puro del plan (F1.1) ──────────────────────────
// FUENTE CANÓNICA: repo web, native/watch/. Funciones PURAS (testables sin red):
// próxima función + agenda de hoy. Zona horaria Colombia (UTC−5), igual que el web
// (que nunca usa toISOString para lógica de fechas — ver CLAUDE.md).

import Foundation

enum PlanCompute {
    // America/Bogota es UTC−5 todo el año (sin DST) → coincide con el offset fijo del web.
    static let tz = TimeZone(identifier: "America/Bogota") ?? TimeZone(secondsFromGMT: -5 * 3600)!

    /// day "2026-07-02" + time "20:00" → Date en zona Colombia. nil si el ítem es inválido.
    static func startDate(_ item: ScheduleItem) -> Date? {
        guard let dayStr = item.dayStr, let timeStr = item.time else { return nil }
        let d = dayStr.split(separator: "-")
        let t = timeStr.split(separator: ":")
        guard d.count == 3, t.count >= 2,
              let y = Int(d[0]), let mo = Int(d[1]), let da = Int(d[2]),
              let h = Int(t[0]), let mi = Int(t[1]) else { return nil }
        var c = DateComponents()
        c.year = y; c.month = mo; c.day = da; c.hour = h; c.minute = mi; c.timeZone = tz
        return Calendar(identifier: .gregorian).date(from: c)
    }

    /// Todos los ítems con fecha válida, ordenados por hora de inicio.
    static func sortedByStart(_ items: [ScheduleItem]) -> [ScheduleItem] {
        items.compactMap { i in startDate(i).map { ($0, i) } }
            .sorted { $0.0 < $1.0 }
            .map { $0.1 }
    }

    /// La próxima función que aún no empezó (start >= now). nil si el festival ya pasó.
    static func next(_ items: [ScheduleItem], now: Date) -> ScheduleItem? {
        items.compactMap { i in startDate(i).map { ($0, i) } }
            .filter { $0.0 >= now }
            .min { $0.0 < $1.0 }?.1
    }

    /// Ítems de HOY (mismo día en zona Colombia), ordenados por hora.
    static func today(_ items: [ScheduleItem], now: Date) -> [ScheduleItem] {
        var cal = Calendar(identifier: .gregorian); cal.timeZone = tz
        return sortedByStart(items).filter { i in
            guard let s = startDate(i) else { return false }
            return cal.isDate(s, inSameDayAs: now)
        }
    }

    // ── Estado en vivo (verde "AHORA") ────────────────────────────────────────
    static func durationMinutes(_ item: ScheduleItem) -> Int? {
        guard let d = item.duration else { return nil }
        let n = d.filter { $0.isNumber }
        return Int(n)
    }

    static func endDate(_ item: ScheduleItem) -> Date? {
        guard let s = startDate(item) else { return nil }
        let mins = durationMinutes(item) ?? 120
        return s.addingTimeInterval(TimeInterval(mins * 60))
    }

    static func isLive(_ item: ScheduleItem, now: Date) -> Bool {
        guard let s = startDate(item), let e = endDate(item) else { return false }
        return s <= now && now < e
    }

    /// Lo que sigue: la función en curso si hay, si no la próxima que aún no empezó.
    static func currentOrNext(_ items: [ScheduleItem], now: Date) -> ScheduleItem? {
        if let live = sortedByStart(items).first(where: { isLive($0, now: now) }) { return live }
        return next(items, now: now)
    }

    /// "en 25 min" / "en 2 h 10 min" / "ahora". nil si ya pasó.
    static func relative(to start: Date, now: Date) -> String? {
        let mins = Int((start.timeIntervalSince(now) / 60).rounded())
        if mins < 0 { return nil }
        if mins == 0 { return "ahora" }
        if mins < 60 { return "en \(mins) min" }
        let h = mins / 60, m = mins % 60
        return m == 0 ? "en \(h) h" : "en \(h) h \(m) min"
    }
}
