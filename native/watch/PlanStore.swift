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
import WidgetKit

@MainActor
final class PlanStore: ObservableObject {
    enum State: Equatable { case idle, loading, loaded, empty, error(String) }

    @Published var state: State = .idle
    @Published var festival: String = ""
    @Published var sections: [DaySection] = []   // el plan agrupado por día
    @Published var defaultDay: Int = 0            // página inicial (hoy / recap)

    // silent: refresco con datos ya en pantalla (volver al primer plano, aviso del
    // teléfono). No pasa por .loading —la lista no parpadea— y si la red falla se
    // conserva lo que había. La carga inicial y el cambio de festival siguen siendo
    // visibles (load() a secas).
    func load(silent: Bool = false) async {
        if !silent || state != .loaded { state = .loading }
        do {
            // Festival en curso que empujó el teléfono (F1.6). Si aún no llegó,
            // fallback a la fila más reciente por updated_at.
            let fid = UserDefaults.standard.string(forKey: WatchAuthManager.activeFestivalKey)
            let base = WatchAuthManager.supabase
                .from("user_festival_state")
                .select("festival_id, saved_agenda")
            let filtered = (fid?.isEmpty == false) ? base.eq("festival_id", value: fid!) : base
            let rows: [UserFestivalRow] = try await filtered
                .order("updated_at", ascending: false)
                .limit(1)
                .execute()
                .value
            guard let row = rows.first,
                  let schedule = row.savedAgenda?.schedule, !schedule.isEmpty else {
                SharedPlan.saveSnapshot(nil)
                state = .empty; return
            }
            festival = row.festivalId
            sections = PlanCompute.groupedByDay(schedule)
            defaultDay = PlanCompute.defaultDayIndex(sections, now: Date())
            publishNextUp()
            state = .loaded
        } catch {
            if !silent { state = .error(error.localizedDescription) }
        }
    }

    // Escribe la función EN CURSO y la SIGUIENTE al App Group para la complication
    // (progreso en vivo, 21 sep 2026). Con las dos, la esfera pasa sola de una a otra.
    private func publishNextUp() {
        let flat = sections.flatMap { $0.items }
        let now = Date()
        let cur = PlanCompute.current(flat, now: now)
        let nxt = PlanCompute.sortedByStart(flat).first { (PlanCompute.startDate($0) ?? .distantPast) >= now && $0.id != cur?.id }
        func pack(_ n: ScheduleItem?) -> NextUp? {
            guard let n, let start = PlanCompute.startDate(n) else { return nil }
            return NextUp(title: n.title, time: n.time ?? "", venue: n.venue,
                          dayLabel: n.dayStr.map { PlanCompute.dayLabel($0) } ?? "",
                          startEpoch: start.timeIntervalSince1970,
                          endEpoch: PlanCompute.endDate(n)?.timeIntervalSince1970,
                          poster: n.poster)
        }
        let snap = PlanSnapshot(current: pack(cur), next: pack(nxt))
        guard snap.current != nil || snap.next != nil else { SharedPlan.saveSnapshot(nil); return }
        SharedPlan.saveSnapshot(snap)
        // Pósters chicos al App Group (el widget no baja imágenes). Al llegar, se
        // vuelve a publicar para que el widget los pinte.
        for path in [cur?.poster, nxt?.poster].compactMap({ $0 }) { cachePoster(path) }
    }
    private func cachePoster(_ path: String) {
        guard SharedPlan.loadPoster(path) == nil, let url = PlanCompute.posterURL(path) else { return }
        Task.detached(priority: .utility) {
            guard let (data, _) = try? await URLSession.shared.data(from: url), data.count < 400_000 else { return }
            SharedPlan.savePoster(path, data: data)
            await MainActor.run { WidgetCenter.shared.reloadAllTimelines() }
        }
    }
}
