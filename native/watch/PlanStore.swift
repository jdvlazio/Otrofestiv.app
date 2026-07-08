// ── PlanStore.swift — carga del plan en el reloj (F1.1) ───────────────────────
// FUENTE CANÓNICA: repo web, native/watch/. Usa la sesión propia del reloj (F1.0)
// para leer user_festival_state por PostgREST (la RLS own_select ya lo scope al
// usuario), decodifica saved_agenda y computa próxima función + agenda.
//
// Festival activo (spike): la fila MÁS RECIENTE por updated_at — el festival que el
// usuario editó último. Suficiente para el spike; el refinamiento (el teléfono empuja
// el festival activo por WCSession) queda para el hardening de F1.1.

import Foundation
import Combine
import Supabase

@MainActor
final class PlanStore: ObservableObject {
    enum State: Equatable { case idle, loading, loaded, empty, error(String) }

    @Published var state: State = .idle
    @Published var festival: String = ""
    @Published var items: [ScheduleItem] = []     // todo el plan, ordenado por hora
    @Published var next: ScheduleItem?             // próxima función (nil si el festival pasó)
    @Published var today: [ScheduleItem] = []      // funciones de hoy

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
                state = .empty; return
            }
            let now = Date()
            festival = row.festivalId
            items = PlanCompute.sortedByStart(schedule)
            next  = PlanCompute.next(schedule, now: now)
            today = PlanCompute.today(schedule, now: now)
            state = .loaded
        } catch {
            state = .error(error.localizedDescription)
        }
    }
}
