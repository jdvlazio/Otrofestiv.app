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
            // Retraso v2: mis reportes de esta función («Empezó N min tarde») viven
            // en screening_reports —la misma fila que escribe el teléfono—. Si la
            // lectura falla, el plan se muestra igual, sin retrasos.
            let delays = await Self.myDelays(festival: row.festivalId)
            sections = PlanCompute.groupedByDay(PlanCompute.applyDelays(schedule, delays))
            defaultDay = PlanCompute.defaultDayIndex(sections, now: Date())
            publishNextUp()
            state = .loaded
        } catch {
            if !silent { state = .error(error.localizedDescription) }
        }
    }

    // ── Marcar el retraso desde el reloj (14 oct 2026) ────────────────────────
    // Total de minutos (no un delta), como el teléfono. Se aplica al instante en
    // pantalla y en la complication; la nube y el teléfono, 1,2 s después del último
    // toque (el control va de a 5 min y la tabla limita 30 reportes por hora).
    func item(id: String) -> ScheduleItem? { sections.lazy.flatMap { $0.items }.first { $0.id == id } }
    private var delayTasks: [String: Task<Void, Never>] = [:]
    func setDelay(_ item: ScheduleItem, minutes: Int) {
        let mins = max(0, min(240, minutes))
        let key = PlanCompute.delayKey(item)
        sections = sections.map { sec in
            DaySection(id: sec.id, label: sec.label, items: sec.items.map { i in
                guard PlanCompute.delayKey(i) == key else { return i }
                var c = i; c.delayMin = mins > 0 ? mins : nil; return c
            })
        }
        publishNextUp()
        let fest = festival
        delayTasks[key]?.cancel()
        delayTasks[key] = Task { [weak self] in
            try? await Task.sleep(nanoseconds: 1_200_000_000)
            guard !Task.isCancelled else { return }
            await Self.saveDelay(festival: fest, key: key, minutes: mins)
            WatchAuthManager.sendDelayToPhone(festival: fest, key: key, title: item.title,
                                              day: item.dayStr ?? "", time: item.time ?? "", minutes: mins)
            self?.delayTasks[key] = nil
        }
    }
    private struct DelayUpsert: Encodable {
        let festival_id: String; let screening_key: String; let delay_min: Int
    }
    // La misma fila que escribe el teléfono (cloudReportDelay / cloudClearDelay):
    // reporter_id lo pone el servidor (auth.uid()) y la RLS solo deja tocar la propia.
    private static func saveDelay(festival: String, key: String, minutes: Int) async {
        let db = WatchAuthManager.supabase.from("screening_reports")
        if minutes > 0 {
            _ = try? await db.upsert(DelayUpsert(festival_id: festival, screening_key: key, delay_min: minutes),
                                     onConflict: "festival_id,screening_key,reporter_id").execute()
        } else {
            _ = try? await db.delete().eq("festival_id", value: festival).eq("screening_key", value: key).execute()
        }
    }

    private struct DelayRow: Decodable {
        let screeningKey: String; let delayMin: Int
        enum CodingKeys: String, CodingKey { case screeningKey = "screening_key", delayMin = "delay_min" }
    }
    private static func myDelays(festival: String) async -> [String: Int] {
        guard let uid = try? await WatchAuthManager.supabase.auth.session.user.id else { return [:] }
        let rows: [DelayRow]? = try? await WatchAuthManager.supabase
            .from("screening_reports")
            .select("screening_key, delay_min")
            .eq("festival_id", value: festival)
            .eq("reporter_id", value: uid.uuidString.lowercased())
            .execute().value
        var out: [String: Int] = [:]
        for r in rows ?? [] where r.delayMin > 0 { out[r.screeningKey] = r.delayMin }
        return out
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
                          poster: n.poster, posterEditorial: PlanCompute.isEditorial(n),
                          delayMin: PlanCompute.delay(n) > 0 ? PlanCompute.delay(n) : nil)
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
