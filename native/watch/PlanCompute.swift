// ── PlanCompute.swift — cómputo puro del plan (F1.2) ──────────────────────────
// FUENTE CANÓNICA: repo web, native/watch/. Puro/testable. Zona Colombia (UTC−5),
// igual que el web. Agrupa el plan por día para la navegación paginada del reloj.

import Foundation

enum PlanCompute {
    // Zona del FESTIVAL (22 sep 2026): antes Bogotá fijo, y para TIFF (Toronto)
    // «AHORA» iba una hora corrido. La fija CatalogStore desde timezoneOffset
    // del JSON («-04:00»); Bogotá queda como fallback hasta que llegue.
    static let defaultTz = TimeZone(identifier: "America/Bogota") ?? TimeZone(secondsFromGMT: -5 * 3600)!
    static var tz: TimeZone = defaultTz
    // "-04:00" / "+05:30" → segundos desde GMT. nil si no parsea.
    static func offsetSeconds(_ s: String?) -> Int? {
        guard let s = s, s.count == 6, let sign = s.first, sign == "+" || sign == "-",
              let h = Int(s.dropFirst().prefix(2)), let m = Int(s.suffix(2)), h <= 14, m < 60 else { return nil }
        return (sign == "-" ? -1 : 1) * (h * 3600 + m * 60)
    }
    @discardableResult static func setTimeZone(offset: String?) -> Bool {
        guard let secs = offsetSeconds(offset), let z = TimeZone(secondsFromGMT: secs) else { return false }
        tz = z; return true
    }

    // ── Programa (Hoy / Mañana) ───────────────────────────────────────────────
    // Archivo del catálogo: espeja loader.js → 'tiff2026' → 'tiff-2026.json'.
    static func catalogFile(for festivalId: String) -> String {
        let re = try! NSRegularExpression(pattern: "([a-zA-Z]+)(\\d+)$")
        let r = NSRange(festivalId.startIndex..., in: festivalId)
        return re.stringByReplacingMatches(in: festivalId, range: r, withTemplate: "$1-$2") + ".json"
    }
    static func catalogURL(for festivalId: String) -> URL {
        URL(string: "https://otrofestiv.app/festivals/" + catalogFile(for: festivalId))!
    }
    // "2026-09-12" — hoy en la zona del festival.
    static func dayKey(_ date: Date) -> String {
        var cal = Calendar(identifier: .gregorian); cal.timeZone = tz
        let c = cal.dateComponents([.year, .month, .day], from: date)
        return String(format: "%04d-%02d-%02d", c.year ?? 0, c.month ?? 0, c.day ?? 0)
    }
    // Hoy y Mañana contra los dayKeys del festival (ordenados). Antes del festival:
    // Hoy vacío («Empieza el jue 10») y Mañana = primer día. Último día: sin Mañana.
    // Terminado: nada.
    static func programDays(_ dayKeys: [String], now: Date) -> ProgramDays {
        let keys = dayKeys.sorted(); let today = dayKey(now)
        guard let first = keys.first, let last = keys.last else { return ProgramDays(today: nil, tomorrow: nil, startsOn: nil) }
        if today < first { return ProgramDays(today: nil, tomorrow: first, startsOn: first) }
        if today > last { return ProgramDays(today: nil, tomorrow: nil, startsOn: nil) }
        let idx = keys.firstIndex(of: today)
        let tomorrow = idx.flatMap { $0 + 1 < keys.count ? keys[$0 + 1] : nil } ?? keys.first { $0 > today }
        return ProgramDays(today: idx != nil ? today : nil, tomorrow: tomorrow, startsOn: nil)
    }
    // Las funciones de un día. Hoy: desde la próxima (misma gracia que el teléfono:
    // 10 min tras el arranque todavía se ofrece). Otro día: completo.
    static let graceMinutes = 10
    static func program(_ items: [ScheduleItem], day: String, now: Date?) -> [ScheduleItem] {
        let ofDay = sortedByStart(items.filter { $0.dayStr == day })
        guard let now = now else { return ofDay }
        let cutoff = now.addingTimeInterval(-Double(graceMinutes) * 60)
        return ofDay.filter { (startDate($0) ?? .distantPast) >= cutoff }
    }
    // Tramos por hora, en orden: "16:00" → [16:15], "17:00" → [17:15, 17:30, …]
    static func groupedByHour(_ items: [ScheduleItem]) -> [HourSection] {
        var order: [String] = []; var buckets: [String: [ScheduleItem]] = [:]
        for it in sortedByStart(items) {
            guard let t = it.time, let h = t.split(separator: ":").first else { continue }
            let key = String(format: "%02d:00", Int(h) ?? 0)
            if buckets[key] == nil { order.append(key); buckets[key] = [] }
            buckets[key]!.append(it)
        }
        return order.map { HourSection(id: $0, items: buckets[$0]!) }
    }
    // «En tu Plan»: misma función (título + día + hora), como sameEntry en el web.
    static func inPlan(_ item: ScheduleItem, plan: [ScheduleItem]) -> Bool {
        plan.contains { $0.title == item.title && $0.dayStr == item.dayStr && $0.time == item.time }
    }

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

    // ── Progreso en vivo (21 sep 2026) — dueño único del «cuánto falta» ───────
    // Mismo fin que el teléfono: inicio + duración de la obra, sin Q&A y (por
    // ahora) sin retrasos reportados. Fracción en [0,1]; nil si no está en curso.
    static func progress(_ item: ScheduleItem, now: Date) -> Double? {
        guard isLive(item, now: now), let s = startDate(item), let e = endDate(item) else { return nil }
        let total = e.timeIntervalSince(s); guard total > 0 else { return nil }
        return min(1, max(0, now.timeIntervalSince(s) / total))
    }
    // Minutos que faltan, redondeados hacia ARRIBA: a las 16:30:20 de una función
    // que termina 16:31 todavía «falta 1 min», no 0. nil si no está en curso.
    static func minutesLeft(_ item: ScheduleItem, now: Date) -> Int? {
        guard isLive(item, now: now), let e = endDate(item) else { return nil }
        return Int(ceil(e.timeIntervalSince(now) / 60))
    }
    // «16:31» — la hora de salida en la zona del festival, mismo formato que item.time.
    static func endTimeLabel(_ item: ScheduleItem) -> String? {
        guard let e = endDate(item) else { return nil }
        var cal = Calendar(identifier: .gregorian); cal.timeZone = tz
        let c = cal.dateComponents([.hour, .minute], from: e)
        guard let h = c.hour, let m = c.minute else { return nil }
        return String(format: "%02d:%02d", h, m)
    }
    // La función en curso a esta hora (o nil). Distinta de nextUpcoming: no cae a
    // la siguiente. La complication necesita las dos por separado.
    static func current(_ items: [ScheduleItem], now: Date) -> ScheduleItem? {
        sortedByStart(items).first { isLive($0, now: now) }
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
