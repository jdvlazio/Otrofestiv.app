// ── LiveActivityBridge.swift — web → Live Activity (fase 1, 28 sep 2026)
// La web (persistence.js → _planLiveActivity) manda la función que corresponde AHORA
// —la que está en curso o la próxima dentro de 1 h (Juan, 14 oct), del festival activo— cada vez que
// cambia el Plan o un retraso, y al volver a la app:
//   {festival, lang, item: {title, venue, start(ms), end(ms), delayMin, poster(url)?,
//    posterEditorial, kindLabel?} | null}
// Con item: crea la tarjeta o la actualiza (misma función = mismo título+inicio
// programado). Sin item: cierra las que queden. Sin servidor: iOS lleva solo la
// cuenta y la barra; el resto se corrige la próxima vez que se abre la app.
import ActivityKit
import Foundation
import WebKit
import UIKit

final class LiveActivityBridge: NSObject, WKScriptMessageHandler {
    private let group = "group.app.otrofestiv.watch"

    func userContentController(_ uc: WKUserContentController, didReceive message: WKScriptMessage) {
        guard let body = message.body as? [String: Any] else { return }
        Task { await self.apply(body) }
    }

    private func apply(_ body: [String: Any]) async {
        guard ActivityAuthorizationInfo().areActivitiesEnabled else { return }
        let fest = body["festival"] as? String ?? ""
        guard let item = body["item"] as? [String: Any],
              let title = item["title"] as? String,
              let s = (item["start"] as? NSNumber)?.doubleValue,
              let e = (item["end"] as? NSNumber)?.doubleValue, e > s else {
            for a in Activity<OtrofestivLiveAttributes>.activities {
                await a.end(nil, dismissalPolicy: .immediate)
            }
            return
        }
        let start = Date(timeIntervalSince1970: s / 1000), end = Date(timeIntervalSince1970: e / 1000)
        let key = (item["key"] as? String) ?? title
        var posterFile: String? = nil
        if let url = (item["poster"] as? String).flatMap(URL.init(string:)) {
            posterFile = await cachePoster(url, name: key)
        }
        let state = OtrofestivLiveAttributes.ContentState(
            title: title, venue: item["venue"] as? String ?? "",
            start: start, end: end, delayMin: (item["delayMin"] as? NSNumber)?.intValue ?? 0,
            posterFile: posterFile, posterEditorial: item["posterEditorial"] as? Bool ?? false,
            kindLabel: item["kindLabel"] as? String, lang: body["lang"] as? String ?? "es")
        // staleDate = el INICIO real (14 oct 2026): a esa hora iOS redibuja la tarjeta
        // con isStale = true y pasa sola de «Empieza en» a «Termina en», sin la app.
        let content = ActivityContent(state: state, staleDate: start, relevanceScore: 100)

        // La misma función se ACTUALIZA (p. ej. un retraso); otra distinta reemplaza.
        var kept = false
        for a in Activity<OtrofestivLiveAttributes>.activities {
            if a.attributes.festival == fest && key == UserDefaults.standard.string(forKey: "otf.live.\(a.id)") {
                await a.update(content); kept = true
                Self.register(a, state)
            } else {
                await a.end(nil, dismissalPolicy: .immediate)
            }
        }
        guard !kept else { return }
        // pushType .token (14 oct 2026): el token de la tarjeta va al servidor con su
        // hora de fin, y el servidor la cierra a esa hora (edge function live-end).
        // Si no hay push (sin permiso, simulador), se crea igual sin token.
        let attrs = OtrofestivLiveAttributes(festival: fest)
        if let a = (try? Activity.request(attributes: attrs, content: content, pushType: .token))
                ?? (try? Activity.request(attributes: attrs, content: content, pushType: nil)) {
            UserDefaults.standard.set(key, forKey: "otf.live.\(a.id)")
            Task {
                for await data in a.pushTokenUpdates {
                    UserDefaults.standard.set(data.map { String(format: "%02x", $0) }.joined(), forKey: "otf.live.tok.\(a.id)")
                    Self.register(a, a.content.state)
                }
            }
        }
    }

    // Retraso marcado en el RELOJ (14 oct 2026): corre la tarjeta sin pasar por la
    // web, que puede estar dormida. Inicio y fin = programados + el retraso nuevo.
    // El staleDate se mueve con el inicio: es lo que cambia «Empieza en» por
    // «Termina en» a la hora real.
    static func applyDelay(key: String, minutes: Int) async {
        for a in Activity<OtrofestivLiveAttributes>.activities
        where UserDefaults.standard.string(forKey: "otf.live.\(a.id)") == key {
            var st = a.content.state
            let shift = TimeInterval((minutes - st.delayMin) * 60)
            guard shift != 0 else { continue }
            st.start = st.start.addingTimeInterval(shift)
            st.end = st.end.addingTimeInterval(shift)
            st.delayMin = minutes
            await a.update(ActivityContent(state: st, staleDate: st.start, relevanceScore: 100))
            register(a, st)
        }
    }

    // ── Cierre a la hora de fin (14 oct 2026, migración 0008) ─────────────────
    // Manda al servidor el token de la tarjeta, su fin REAL y el estado a mostrar
    // al cerrar. Se repite en cada actualización (un retraso corre el fin). Sin
    // token todavía (llega async por pushTokenUpdates) no hace nada: cuando llega,
    // se registra desde ahí.
    private static let liveEndURL = URL(string: "https://eytxrvbnwzxuedbmnnqr.supabase.co/functions/v1/live-end")!
    static func register(_ a: Activity<OtrofestivLiveAttributes>, _ st: OtrofestivLiveAttributes.ContentState) {
        guard let tok = UserDefaults.standard.string(forKey: "otf.live.tok.\(a.id)"),
              let stData = try? JSONEncoder().encode(st),   // mismo encoder que ActivityKit: fechas = segundos desde 2001
              let stObj = try? JSONSerialization.jsonObject(with: stData) else { return }
        #if DEBUG
        let env = "sandbox"
        #else
        let env = "production"
        #endif
        let body: [String: Any] = ["token": tok, "end_at": st.end.timeIntervalSince1970 * 1000, "env": env, "state": stObj]
        guard let data = try? JSONSerialization.data(withJSONObject: body) else { return }
        var req = URLRequest(url: liveEndURL); req.httpMethod = "POST"; req.httpBody = data
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        URLSession.shared.dataTask(with: req).resume()
    }

    // La extensión no baja imágenes: el póster queda en el App Group, chico.
    private func cachePoster(_ url: URL, name: String) async -> String? {
        guard let dir = FileManager.default.containerURL(forSecurityApplicationGroupIdentifier: group)?
            .appendingPathComponent("live", isDirectory: true) else { return nil }
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        let file = String(name.unicodeScalars.filter { CharacterSet.alphanumerics.contains($0) }.prefix(60)) + ".jpg"
        let dest = dir.appendingPathComponent(file)
        if FileManager.default.fileExists(atPath: dest.path) { return file }
        // Chico: una Live Activity con una imagen grande no se pinta (límite de memoria).
        guard let (data, _) = try? await URLSession.shared.data(from: url), let img = UIImage(data: data) else { return nil }
        let k = min(1, 240 / max(img.size.width, img.size.height))
        let size = CGSize(width: img.size.width * k, height: img.size.height * k)
        let small = UIGraphicsImageRenderer(size: size).image { _ in img.draw(in: CGRect(origin: .zero, size: size)) }
        guard let jpg = small.jpegData(compressionQuality: 0.8) else { return nil }
        try? jpg.write(to: dest)
        return file
    }
}
