// ── CatalogStore.swift — el Programa del festival en el reloj (22 sep 2026) ──
// FUENTE CANÓNICA: repo web, native/watch/. Baja festivals/<id>.json de producción
// con la sesión de red del reloj (sin pasar por el teléfono), lo guarda en disco y
// lo reusa. Además es quien FIJA la zona horaria del festival (PlanCompute.tz) a
// partir de timezoneOffset del JSON — y la recuerda por festival para que Mi Plan
// calcule bien «AHORA» aun antes de que el catálogo llegue.
//
// Política de refresco: caché fresca (< 6 h) → no toca la red. Si no, GET
// condicional con If-None-Match (Pages manda ETag): 304 → sigue la caché; 200 →
// reemplaza. Sin red y con caché → la caché, y la vista dice de cuándo es.

import Foundation
import Combine

@MainActor
final class CatalogStore: ObservableObject {
    enum State: Equatable { case idle, loading, loaded, error(String) }

    @Published var state: State = .idle
    @Published var festival: String = ""
    @Published var catalog: Catalog?
    @Published var fetchedAt: Date?
    // Cambia cuando la zona horaria del festival cambió al cargar → Mi Plan recalcula.
    @Published var tzVersion: Int = 0

    static let maxAge: TimeInterval = 6 * 3600
    static let tzKeyPrefix = "otf.tz."          // UserDefaults: zona recordada por festival
    static let etagKeyPrefix = "otf.catalog.etag."
    static let fetchedKeyPrefix = "otf.catalog.fetchedAt."

    // Antes de cualquier red: aplicar la zona recordada del festival (o Bogotá).
    static func applyRememberedTimeZone(festival: String) -> Bool {
        let off = UserDefaults.standard.string(forKey: tzKeyPrefix + festival)
        if PlanCompute.setTimeZone(offset: off) { return true }
        PlanCompute.tz = PlanCompute.defaultTz; return false
    }

    func load(festival fid: String, force: Bool = false) async {
        guard !fid.isEmpty else { return }
        festival = fid
        let d = UserDefaults.standard
        let fetched = d.object(forKey: Self.fetchedKeyPrefix + fid) as? Date
        // 1. Caché en disco
        if catalog == nil || festival != fid, let data = try? Data(contentsOf: Self.cacheURL(fid)),
           let c = try? JSONDecoder().decode(Catalog.self, from: data) {
            apply(c, fid: fid, at: fetched)
        }
        // 2. ¿Hace falta ir a la red?
        let fresh = fetched.map { Date().timeIntervalSince($0) < Self.maxAge } ?? false
        if catalog != nil && fresh && !force { return }
        if catalog == nil { state = .loading }
        // 3. GET condicional
        var req = URLRequest(url: PlanCompute.catalogURL(for: fid))
        if let etag = d.string(forKey: Self.etagKeyPrefix + fid) { req.setValue(etag, forHTTPHeaderField: "If-None-Match") }
        do {
            let (data, resp) = try await URLSession.shared.data(for: req)
            let http = resp as? HTTPURLResponse
            if http?.statusCode == 304, catalog != nil {
                d.set(Date(), forKey: Self.fetchedKeyPrefix + fid); fetchedAt = Date(); state = .loaded; return
            }
            guard http?.statusCode == 200 else { throw URLError(.badServerResponse) }
            let c = try JSONDecoder().decode(Catalog.self, from: data)
            try? data.write(to: Self.cacheURL(fid), options: .atomic)
            if let etag = http?.value(forHTTPHeaderField: "ETag") { d.set(etag, forKey: Self.etagKeyPrefix + fid) }
            d.set(Date(), forKey: Self.fetchedKeyPrefix + fid)
            apply(c, fid: fid, at: Date())
        } catch {
            // Sin red: si hay caché queda .loaded (la vista dice de cuándo es); si no, error.
            if catalog == nil { state = .error(error.localizedDescription) }
        }
    }

    // Refresco al volver al primer plano: solo si la caché envejeció o cambió el día.
    func refreshIfStale() async {
        guard !festival.isEmpty else { return }
        let fetched = UserDefaults.standard.object(forKey: Self.fetchedKeyPrefix + festival) as? Date
        let stale = fetched.map { Date().timeIntervalSince($0) >= Self.maxAge || PlanCompute.dayKey($0) != PlanCompute.dayKey(Date()) } ?? true
        if stale { await load(festival: festival, force: true) }
    }

    private func apply(_ c: Catalog, fid: String, at: Date?) {
        catalog = c; fetchedAt = at; state = .loaded
        // Zona del festival: fijarla, recordarla, y avisar si cambió.
        let before = PlanCompute.tz
        if PlanCompute.setTimeZone(offset: c.timezoneOffset) {
            UserDefaults.standard.set(c.timezoneOffset, forKey: Self.tzKeyPrefix + fid)
            if PlanCompute.tz != before { tzVersion += 1 }
        }
    }

    static func cacheURL(_ fid: String) -> URL {
        let dir = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        return dir.appendingPathComponent("catalog-\(fid).json")
    }
}
