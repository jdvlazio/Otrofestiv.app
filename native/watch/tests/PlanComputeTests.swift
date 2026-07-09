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
