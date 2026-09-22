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

        // ── Zona del festival (22 sep 2026) ───────────────────────────────────
        check("offsetSeconds -04:00", PlanCompute.offsetSeconds("-04:00") == -4 * 3600)
        check("offsetSeconds +05:30", PlanCompute.offsetSeconds("+05:30") == 5 * 3600 + 30 * 60)
        check("offsetSeconds basura → nil", PlanCompute.offsetSeconds("Toronto") == nil && PlanCompute.offsetSeconds(nil) == nil && PlanCompute.offsetSeconds("-4:00") == nil)
        let tzBefore = PlanCompute.tz
        check("setTimeZone fija Toronto", PlanCompute.setTimeZone(offset: "-04:00") && PlanCompute.tz.secondsFromGMT() == -4 * 3600)
        // Bedford Park 14:30 en Toronto = 13:30 Bogotá: con la zona bien, a las 15:31 Toronto YA terminó
        let bpTor = item("Bedford Park", "2026-09-12", "14:30", duration: "61 min")
        var utc = Calendar(identifier: .gregorian); utc.timeZone = TimeZone(identifier: "UTC")!
        let t1531Toronto = utc.date(from: DateComponents(year: 2026, month: 9, day: 12, hour: 19, minute: 31))!  // 15:31 -04:00
        check("con zona Toronto, 15:31 ya no está en curso", !PlanCompute.isLive(bpTor, now: t1531Toronto))
        check("setTimeZone inválido no toca la zona", !PlanCompute.setTimeZone(offset: "??") && PlanCompute.tz.secondsFromGMT() == -4 * 3600)
        PlanCompute.tz = tzBefore
        check("con Bogotá (fallback), a esa misma hora sigue en curso", PlanCompute.isLive(bpTor, now: t1531Toronto))

        // ── Programa: archivo, Hoy/Mañana, desde ahora, por hora, en tu Plan ──
        check("catalogFile tiff2026 → tiff-2026.json", PlanCompute.catalogFile(for: "tiff2026") == "tiff-2026.json")
        check("catalogFile ficci65 → ficci-65.json", PlanCompute.catalogFile(for: "ficci65") == "ficci-65.json")
        let keys = ["2026-09-10", "2026-09-11", "2026-09-12", "2026-09-13"]
        let sat = PlanCompute.startDate(item("X", "2026-09-12", "16:08"))!
        // En curso: hoy y el siguiente; «Hoy» y «Mañana» son ciertos.
        let pd = PlanCompute.programDays(keys, now: sat)
        check("en curso: sáb y dom", pd.days == ["2026-09-12", "2026-09-13"])
        check("en curso: hoy es sáb y mañana es dom", pd.todayKey == "2026-09-12" && pd.tomorrowKey == "2026-09-13")
        // Último día: solo él, sin segunda página.
        let last = PlanCompute.programDays(keys, now: PlanCompute.startDate(item("X", "2026-09-13", "10:00"))!)
        check("último día: una sola página", last.days == ["2026-09-13"] && last.todayKey == "2026-09-13")
        // ANTES del festival (el caso que rompía: el 22 sep, con Jardín el 24, el
        // título decía «Today»). Dos días adelante → NINGUNO es hoy ni mañana.
        let dosAntes = PlanCompute.programDays(keys, now: PlanCompute.startDate(item("X", "2026-09-08", "10:00"))!)
        check("no empezó: los dos primeros días", dosAntes.days == ["2026-09-10", "2026-09-11"])
        check("no empezó: hoy no es día de festival", dosAntes.todayKey == nil)
        check("no empezó a dos días: el primero NO es mañana", dosAntes.days.first != dosAntes.tomorrowKey)
        // Empieza MAÑANA → ahí sí, el primer día es «Mañana».
        let vispera = PlanCompute.programDays(keys, now: PlanCompute.startDate(item("X", "2026-09-09", "10:00"))!)
        check("víspera: el primer día ES mañana", vispera.days.first == vispera.tomorrowKey && vispera.todayKey == nil)
        // Terminado: el último día, y no se dice «Hoy».
        let after = PlanCompute.programDays(keys, now: PlanCompute.startDate(item("X", "2026-09-21", "10:00"))!)
        check("terminado: el último día", after.days == ["2026-09-13"] && after.todayKey == nil)
        check("catálogo sin días: nada que mostrar", PlanCompute.programDays([], now: sat).days.isEmpty)
        check("programDays desordenados no importan", PlanCompute.programDays(keys.reversed(), now: sat) == pd)
        let cat = [item("A", "2026-09-12", "11:30", duration: "90 min"), item("B", "2026-09-12", "16:00", duration: "70 min"),
                   item("C", "2026-09-12", "16:15", duration: "70 min"), item("D", "2026-09-12", "17:15"), item("E", "2026-09-13", "08:15")]
        let hoy = PlanCompute.program(cat, day: "2026-09-12", now: sat).map { $0.title }
        check("Hoy desde la próxima: B (16:00, gracia 10 min) sigue; A no", hoy == ["B", "C", "D"])
        let hoyTarde = PlanCompute.program(cat, day: "2026-09-12", now: sat.addingTimeInterval(3 * 60)).map { $0.title }
        check("a las 16:11, B ya pasó su gracia", hoyTarde == ["C", "D"])
        check("otro día: completo, sin filtro", PlanCompute.program(cat, day: "2026-09-13", now: nil).map { $0.title } == ["E"])
        let hours = PlanCompute.groupedByHour(PlanCompute.program(cat, day: "2026-09-12", now: nil))
        check("por hora: 11:00, 16:00 (B,C), 17:00", hours.map { $0.id } == ["11:00", "16:00", "17:00"] && hours[1].items.map { $0.title } == ["B", "C"])
        let plan = [item("C", "2026-09-12", "16:15"), item("D", "2026-09-13", "17:15")]
        check("inPlan: C sí", PlanCompute.inPlan(cat[2], plan: plan))
        check("inPlan: D no — misma obra, otro día", !PlanCompute.inPlan(cat[3], plan: plan))
        check("dayKey en la zona", PlanCompute.dayKey(sat) == "2026-09-12")

        // ── Programa: copy y día corto (22 sep 2026) ──────────────────────────
        let en = Lang.current == .en
        check("scheduleFrom", L.scheduleFrom(hours: 3) == (en ? "Schedule from 3 h ago" : "Programa de hace 3 h"))
        check("today/tomorrow", L.today == (en ? "Today" : "Hoy") && L.tomorrow == (en ? "Tomorrow" : "Mañana"))
        let catJSON = #"{"timezoneOffset":"-04:00","dayKeys":["2026-09-12"],"dayShort":{"2026-09-12":"SÁB 12"},"dayShort_en":{"2026-09-12":"SAT 12"},"films":[]}"#
        let catObj = try! JSONDecoder().decode(Catalog.self, from: catJSON.data(using: .utf8)!)
        check("Catalog decodifica dayShort_en", catObj.dayShortEn?["2026-09-12"] == "SAT 12")
        check("shortDay en el idioma del reloj", catObj.shortDay("2026-09-12") == (en ? "SAT 12" : "SÁB 12"))
        let catSin = try! JSONDecoder().decode(Catalog.self, from: #"{"dayKeys":["2026-09-12"],"films":[]}"#.data(using: .utf8)!)
        check("shortDay sin dayShort → dayLabel", catSin.shortDay("2026-09-12") == PlanCompute.dayLabel("2026-09-12"))
        check("Catalog sin timezoneOffset decodifica (nil)", catSin.timezoneOffset == nil)

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
