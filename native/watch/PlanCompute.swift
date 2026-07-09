// ── PlanCompute.swift — cómputo puro del plan (F1.2) ──────────────────────────
// FUENTE CANÓNICA: repo web, native/watch/. Puro/testable. Zona Colombia (UTC−5),
// igual que el web. Agrupa el plan por día para la navegación paginada del reloj.

import Foundation

enum PlanCompute {
    static let tz = TimeZone(identifier: "America/Bogota") ?? TimeZone(secondsFromGMT: -5 * 3600)!

    // ── URL del poster ────────────────────────────────────────────────────────
    // Espeja la resolución del web (getFilmPoster): URL completa → tal cual;
    // "/assets/…" → dominio de producción; cualquier otro path ("/xxx.jpg") es
    // TMDB → base de imágenes de TMDB. tmdbSize: w185 (fila) / w342 (detalle).
    static func posterURL(_ path: String?, tmdbSize: String = "w185") -> URL? {
        guard let p = path, !p.isEmpty else { return nil }
        if p.hasPrefix("http") { return URL(string: p) }
        if p.hasPrefix("/assets/") { return URL(string: "https://otrofestiv.app" + p) }
        return URL(string: "https://image.tmdb.org/t/p/\(tmdbSize)" + p)
    }

    // Editorial = still landscape 16:9 de un CDN oficial (espeja EDITORIAL_CDN_HOSTS
    // del web). Se renderiza sin recortar; el resto es póster 2:3.
    static let editorialHosts = ["cloudfront.net", "supabase.co"]
    static func isEditorial(_ path: String?) -> Bool {
        guard let p = path, let host = URL(string: p)?.host else { return false }
        return editorialHosts.contains { host.hasSuffix($0) }
    }

    static func startDate(_ item: ScheduleItem) -> Date? {
        guard let dayStr = item.dayStr, let timeStr = item.time else { return nil }
        let d = dayStr.split(separator: "-"); let t = timeStr.split(separator: ":")
        guard d.count == 3, t.count >= 2,
              let y = Int(d[0]), let mo = Int(d[1]), let da = Int(d[2]),
              let h = Int(t[0]), let mi = Int(t[1]) else { return nil }
        var c = DateComponents()
        c.year = y; c.month = mo; c.day = da; c.hour = h; c.minute = mi; c.timeZone = tz
        return Calendar(identifier: .gregorian).date(from: c)
    }

    static func sortedByStart(_ items: [ScheduleItem]) -> [ScheduleItem] {
        items.compactMap { i in startDate(i).map { ($0, i) } }.sorted { $0.0 < $1.0 }.map { $0.1 }
    }

    // ── Estado en vivo (verde "AHORA") ────────────────────────────────────────
    static func durationMinutes(_ item: ScheduleItem) -> Int? {
        guard let d = item.duration else { return nil }
        return Int(d.filter { $0.isNumber })
    }
    static func endDate(_ item: ScheduleItem) -> Date? {
        guard let s = startDate(item) else { return nil }
        return s.addingTimeInterval(TimeInterval((durationMinutes(item) ?? 120) * 60))
    }
    static func isLive(_ item: ScheduleItem, now: Date) -> Bool {
        guard let s = startDate(item), let e = endDate(item) else { return false }
        return s <= now && now < e
    }

    // ── Agrupación por día (páginas de Mi Plan) ───────────────────────────────
    static func groupedByDay(_ items: [ScheduleItem]) -> [DaySection] {
        var order: [String] = []
        var map: [String: [ScheduleItem]] = [:]
        for i in sortedByStart(items) {
            guard let d = i.dayStr else { continue }
            if map[d] == nil { order.append(d); map[d] = [] }
            map[d]?.append(i)
        }
        return order.map { DaySection(id: $0, label: dayLabel($0), items: map[$0] ?? []) }
    }

    /// "2026-07-03" → "VIE 3 JUL" (es) / "FRI JUL 3" (en). ALLCAPS, según idioma.
    static func dayLabel(_ dayStr: String, lang: Lang = Lang.current) -> String {
        let en = lang == .en
        let loc = Locale(identifier: en ? "en_US" : "es_CO")
        let parse = DateFormatter()
        parse.locale = loc; parse.timeZone = tz
        parse.dateFormat = "yyyy-MM-dd"
        guard let date = parse.date(from: dayStr) else { return dayStr }
        let out = DateFormatter()
        out.locale = loc; out.timeZone = tz
        out.dateFormat = en ? "EEE MMM d" : "EEE d MMM"
        return out.string(from: date).uppercased().replacingOccurrences(of: ".", with: "")
    }

    /// Página inicial: hoy si el plan lo tiene; si no, el primer día futuro; si el festival
    /// ya pasó, el último día (recap).
    // Próxima función del plan: la que está en curso, o la primera futura.
    static func nextUpcoming(_ items: [ScheduleItem], now: Date) -> ScheduleItem? {
        let sorted = sortedByStart(items)
        if let live = sorted.first(where: { isLive($0, now: now) }) { return live }
        return sorted.first(where: { (startDate($0) ?? .distantPast) >= now })
    }

    static func defaultDayIndex(_ sections: [DaySection], now: Date) -> Int {
        var cal = Calendar(identifier: .gregorian); cal.timeZone = tz
        if let i = sections.firstIndex(where: { s in
            guard let f = s.items.first, let d = startDate(f) else { return false }
            return cal.isDate(d, inSameDayAs: now)
        }) { return i }
        if let i = sections.firstIndex(where: { s in
            guard let f = s.items.first, let d = startDate(f) else { return false }
            return d >= cal.startOfDay(for: now)
        }) { return i }
        return max(0, sections.count - 1)
    }
}
