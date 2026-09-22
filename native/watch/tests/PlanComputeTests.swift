// ── PlanComputeTests.swift — tests del cómputo puro del reloj (F1.6) ──────────
// PlanCompute/PlanModels/WatchStrings son Foundation-only → se compilan y corren
// en el Mac con swiftc (sin target de Xcode). Testea los archivos REALES del repo.
//
//   cd native/watch && swiftc PlanModels.swift WatchStrings.swift PlanCompute.swift \
//       tests/PlanComputeTests.swift -o /tmp/otf-tests && /tmp/otf-tests
//
// (ver native/watch/tests/run.sh)

import Foundation

@main
enum PlanComputeTests {
    static func main() {
        var passed = 0, failed = 0
        func check(_ name: String, _ cond: Bool) {
            if cond { passed += 1 } else { failed += 1; print("  ✗ FAIL: \(name)") }
        }
        func item(_ title: String, _ day: String?, _ time: String?,
                  venue: String? = nil, duration: String? = nil, poster: String? = nil) -> ScheduleItem {
            ScheduleItem(title: title, day: day, date: nil, time: time,
                         venue: venue, type: nil, duration: duration, poster: poster)
        }

        // ── startDate (zona Colombia) ─────────────────────────────────────────
        let d = PlanCompute.startDate(item("X", "2026-07-04", "10:00"))!
        var cal = Calendar(identifier: .gregorian); cal.timeZone = PlanCompute.tz
        let c = cal.dateComponents([.year, .month, .day, .hour, .minute], from: d)
        check("startDate parsea zona Bogotá",
              c.year == 2026 && c.month == 7 && c.day == 4 && c.hour == 10 && c.minute == 0)
        check("startDate nil sin hora", PlanCompute.startDate(item("X", "2026-07-04", nil)) == nil)

        // ── durationMinutes ───────────────────────────────────────────────────
        check("durationMinutes 124", PlanCompute.durationMinutes(item("X", nil, nil, duration: "124 min")) == 124)
        check("durationMinutes nil", PlanCompute.durationMinutes(item("X", nil, nil)) == nil)

        // ── Progreso en vivo (21 sep 2026) ────────────────────────────────────
        // Bedford Park: 14:30, 121 min → termina 16:31. A las 16:08 faltan 23.
        let bp = item("Bedford Park", "2026-09-12", "14:30", duration: "121 min")
        let bpStart = PlanCompute.startDate(bp)!
        let t1608 = bpStart.addingTimeInterval(98 * 60)
        check("minutesLeft 16:08 → 23", PlanCompute.minutesLeft(bp, now: t1608) == 23)
        check("progress 16:08 → 98/121", abs((PlanCompute.progress(bp, now: t1608) ?? -1) - 98.0 / 121.0) < 0.001)
        check("endTimeLabel 16:31", PlanCompute.endTimeLabel(bp) == "16:31")
        // redondeo hacia arriba: a 16:30:20 todavía falta 1 min, no 0
        check("minutesLeft 16:30:20 → 1", PlanCompute.minutesLeft(bp, now: bpStart.addingTimeInterval(120 * 60 + 20)) == 1)
        check("minutesLeft en el primer segundo → 121", PlanCompute.minutesLeft(bp, now: bpStart) == 121)
        check("progress arranca en 0", PlanCompute.progress(bp, now: bpStart) == 0)
        // fuera de la función: nil (antes y después), no 0 ni 1
        check("minutesLeft antes → nil", PlanCompute.minutesLeft(bp, now: bpStart.addingTimeInterval(-60)) == nil)
        check("progress después → nil", PlanCompute.progress(bp, now: bpStart.addingTimeInterval(121 * 60)) == nil)
        check("progress sin hora → nil", PlanCompute.progress(item("X", "2026-09-12", nil), now: t1608) == nil)
        // current: la en curso, no la siguiente; y sin en curso → nil
        let later = item("I Play Rocky", "2026-09-12", "18:00", duration: "90 min")
        check("current = la en curso", PlanCompute.current([later, bp], now: t1608)?.title == "Bedford Park")
        check("current sin en curso → nil", PlanCompute.current([later, bp], now: bpStart.addingTimeInterval(125 * 60)) == nil)
        check("nextUpcoming sigue prefiriendo la en curso", PlanCompute.nextUpcoming([later, bp], now: t1608)?.title == "Bedford Park")

        // ── isLive ────────────────────────────────────────────────────────────
        let live = item("L", "2026-07-04", "10:00", duration: "124 min")   // 10:00–12:04
        let start = PlanCompute.startDate(live)!
        check("isLive dentro",  PlanCompute.isLive(live, now: start.addingTimeInterval(60 * 60)))
        check("isLive antes",  !PlanCompute.isLive(live, now: start.addingTimeInterval(-60)))
        check("isLive después", !PlanCompute.isLive(live, now: start.addingTimeInterval(200 * 60)))

        // ── sortedByStart ─────────────────────────────────────────────────────
        let s = PlanCompute.sortedByStart([item("A", "2026-07-04", "18:00"), item("B", "2026-07-04", "10:00")])
        check("sortedByStart asc", s.first?.title == "B" && s.last?.title == "A")

        // ── groupedByDay ──────────────────────────────────────────────────────
        let secs = PlanCompute.groupedByDay([
            item("A", "2026-07-05", "10:00"),
            item("B", "2026-07-04", "18:00"),
            item("C", "2026-07-04", "10:00"),
        ])
        check("grouped 2 días", secs.count == 2)
        check("grouped orden cronológico", secs[0].id == "2026-07-04" && secs[1].id == "2026-07-05")
        check("grouped ordena dentro del día", secs[0].items.map { $0.title } == ["C", "B"])

        // ── dayLabel es/en ────────────────────────────────────────────────────
        check("dayLabel es orden d-MMM", PlanCompute.dayLabel("2026-07-04", lang: .es).contains("4 JUL"))
        check("dayLabel en orden MMM-d", PlanCompute.dayLabel("2026-07-04", lang: .en).contains("JUL 4"))
        check("dayLabel sin puntos",    !PlanCompute.dayLabel("2026-07-04", lang: .es).contains("."))

        // ── Lang.current respeta el idioma del USUARIO (B2, 2 ago 2026) ───────
        // Bug real: Locale.current se resuelve contra las localizaciones del
        // bundle (sin es.lproj → siempre "en") y el plan salía "THU AUG 13" con
        // el sistema en español. Lang.current pasó a preferredLanguages. El
        // harness corre el binario con -AppleLanguages forzado (ver run.sh) y
        // acá se asserta la cadena completa: idioma → dayLabel del encabezado.
        if let forced = UserDefaults.standard.stringArray(forKey: "AppleLanguages")?.first {
            if forced.hasPrefix("es") {
                check("Lang.current=es con AppleLanguages es", Lang.current == .es)
                check("encabezado ES localizado (JUE 13 AGO)", PlanCompute.dayLabel("2026-08-13", lang: Lang.current) == "JUE 13 AGO")
            } else if forced.hasPrefix("en") {
                check("Lang.current=en con AppleLanguages en", Lang.current == .en)
                check("encabezado EN (THU AUG 13)", PlanCompute.dayLabel("2026-08-13", lang: Lang.current) == "THU AUG 13")
            }
        }

        // ── nextUpcoming ──────────────────────────────────────────────────────
        let now = PlanCompute.startDate(item("_", "2026-07-04", "12:00"))!
        let past = item("past", "2026-07-04", "09:00")
        let future = item("future", "2026-07-04", "18:00")
        let future2 = item("future2", "2026-07-05", "10:00")
        check("nextUpcoming primera futura",
              PlanCompute.nextUpcoming([past, future2, future], now: now)?.title == "future")
        let liveNow = item("live", "2026-07-04", "11:30", duration: "120 min")   // 11:30–13:30
        check("nextUpcoming prefiere en curso",
              PlanCompute.nextUpcoming([past, liveNow, future], now: now)?.title == "live")
        check("nextUpcoming nil si todo pasó",
              PlanCompute.nextUpcoming([past], now: now.addingTimeInterval(100 * 3600)) == nil)

        // ── isEditorial ───────────────────────────────────────────────────────
        check("editorial cloudfront", PlanCompute.isEditorial("https://d13jj08vfqimqg.cloudfront.net/x.jpg"))
        check("editorial supabase",   PlanCompute.isEditorial("https://xyz.supabase.co/x.jpg"))
        check("no editorial assets", !PlanCompute.isEditorial("/assets/f/h.jpg"))
        check("no editorial tmdb",   !PlanCompute.isEditorial("/abc.jpg"))
        check("no editorial nil",    !PlanCompute.isEditorial(nil))
        check("no editorial tmdb host", !PlanCompute.isEditorial("https://image.tmdb.org/t/p/w185/x.jpg"))

        // ── posterURL ─────────────────────────────────────────────────────────
        check("posterURL http tal cual",
              PlanCompute.posterURL("https://x.com/a.jpg")?.absoluteString == "https://x.com/a.jpg")
        check("posterURL assets → prod",
              PlanCompute.posterURL("/assets/f/h.jpg")?.absoluteString == "https://otrofestiv.app/assets/f/h.jpg")
        check("posterURL tmdb w185",
              PlanCompute.posterURL("/abc.jpg")?.absoluteString == "https://image.tmdb.org/t/p/w185/abc.jpg")
        check("posterURL tmdb w342",
              PlanCompute.posterURL("/abc.jpg", tmdbSize: "w342")?.absoluteString == "https://image.tmdb.org/t/p/w342/abc.jpg")
        check("posterURL nil", PlanCompute.posterURL(nil) == nil)
        check("posterURL vacío", PlanCompute.posterURL("") == nil)

        // ── defaultDayIndex ───────────────────────────────────────────────────
        let secs2 = PlanCompute.groupedByDay([item("A", "2026-07-04", "10:00"), item("B", "2026-07-05", "10:00")])
        check("defaultDayIndex hoy",
              PlanCompute.defaultDayIndex(secs2, now: PlanCompute.startDate(item("_", "2026-07-05", "08:00"))!) == 1)
        check("defaultDayIndex primera futura",
              PlanCompute.defaultDayIndex(secs2, now: PlanCompute.startDate(item("_", "2026-07-01", "08:00"))!) == 0)
        check("defaultDayIndex recap (último)",
              PlanCompute.defaultDayIndex(secs2, now: PlanCompute.startDate(item("_", "2026-07-10", "08:00"))!) == 1)

        print("\nPlanCompute: \(passed) passed, \(failed) failed")
        exit(failed == 0 ? 0 : 1)
    }
}
