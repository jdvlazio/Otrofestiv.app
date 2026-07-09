// ── PlanStore.swift — carga del plan en el reloj (F1.2) ───────────────────────
// FUENTE CANÓNICA: repo web, native/watch/. Usa la sesión propia del reloj (F1.0)
// para leer user_festival_state por PostgREST (RLS own_select), decodifica
// saved_agenda y lo agrupa por día para la navegación paginada.
//
// Festival activo (spike): la fila MÁS RECIENTE por updated_at. El refinamiento
// (el teléfono empuja el festival activo por WCSession) queda para el hardening.

import Foundation
import Combine
import Supabase

@MainActor
final class PlanStore: ObservableObject {
    enum State: Equatable { case idle, loading, loaded, empty, error(String) }

    @Published var state: State = .idle
    @Published var festival: String = ""
    @Published var sections: [DaySection] = []   // el plan agrupado por día
    @Published var defaultDay: Int = 0            // página inicial (hoy / recap)

    func load() async {
        state = .loading
        do {
            let rows: [UserFestivalRow] = try await WatchAuthManager.supabase
                .from("user_festival_state")
                .select("festival_id, saved_agenda")
                .order("updated_at", ascending: false)
                .limit(1)
                .execute()
                .value
            guard let row = rows.first,
                  let schedule = row.savedAgenda?.schedule, !schedule.isEmpty else {
                SharedPlan.save(nil)
                state = .empty; return
            }
            festival = row.festivalId
            sections = PlanCompute.groupedByDay(schedule)
            defaultDay = PlanCompute.defaultDayIndex(sections, now: Date())
            publishNextUp()
            state = .loaded
        } catch {
            state = .error(error.localizedDescription)
        }
    }

    // Escribe la próxima función al App Group para que la lea la complication.
    private func publishNextUp() {
        let flat = sections.flatMap { $0.items }
        guard let n = PlanCompute.nextUpcoming(flat, now: Date()),
              let start = PlanCompute.startDate(n) else {
            SharedPlan.save(nil); return
        }
        SharedPlan.save(NextUp(
            title: n.title,
            time: n.time ?? "",
            venue: n.venue,
            dayLabel: n.dayStr.map { PlanCompute.dayLabel($0) } ?? "",
            startEpoch: start.timeIntervalSince1970
        ))
    }
}
