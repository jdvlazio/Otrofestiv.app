import SwiftUI
import WebKit
import EventKit
import UserNotifications

// WKWebView wrapper con cachePolicy = .reloadIgnoringLocalAndRemoteCacheData
// en cada launch. Garantiza que el HTML de https://otrofestiv.app se fetchea
// fresco del servidor en cada cold start, evitando el problema de WKWebView
// sirviendo HTML cacheado después de un deploy.
//
// Recursos sub-document (JS/CSS/JSON) siguen usando caché normal del WebView
// — están versionados por BUILD_VERSION en el código web, así que el SW
// (otrofestiv-v{timestamp}) los invalida cuando hay deploy.
//
// Data store es persistente (default) — cookies, localStorage y el propio
// Service Worker registry sobreviven entre launches. Solo el HTTP cache del
// document request se bypassa.
//
// Puente EventKit: el Coordinator registra el messageHandler 'calendar'. El
// lado web (share.js → exportICS) postea {events:[{title,start,end,location,
// notes}]} con start/end en epoch ms (instante absoluto). Swift pide permiso
// una vez y agrega un EKEvent por función al calendario por defecto, sin hoja
// de compartir. Devuelve el resultado a JS vía window.__otfCalResult(res).
//
// WKUIDelegate: createWebViewWith abre target="_blank" en Safari del sistema.
// isInspectable: habilita Web Inspector en builds debug (iOS 16.4+).
struct WebViewContainer: UIViewRepresentable {
    func makeCoordinator() -> Coordinator { Coordinator() }

    // Fondo del chrome nativo = --bg del web (#0A0A0A). Debe coincidir con el
    // launch screen y el <html>/body del HTML para una transición sin flash.
    static let bg = UIColor(red: 0.039, green: 0.039, blue: 0.039, alpha: 1)

    func makeUIView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.userContentController.add(context.coordinator, name: "calendar")
        config.userContentController.add(context.coordinator, name: "notifications")   // ← avisos del Plan
        config.userContentController.add(context.coordinator.live, name: "liveActivity") // ← Live Activity
        UNUserNotificationCenter.current().delegate = context.coordinator
        config.userContentController.add(context.coordinator.watchAuth, name: "watchAuth")   // ← reloj
        let webView = WKWebView(frame: .zero, configuration: config)
        context.coordinator.webView = webView
        context.coordinator.watchAuth.webView = webView   // ← reloj
        context.coordinator.watchAuth.activate()          // ← reloj
        webView.uiDelegate = context.coordinator
        // ── Fix del flash blanco (capa 2: el WKWebView nace OPACO y BLANCO) ──
        // isOpaque=false + bg #0A0A0A hacen que la ventana del WebView sea oscura
        // (no blanca) mientras otrofestiv.app carga — tras el launch screen, antes
        // del primer paint del HTML. El contenido (incluida la animación de entrada
        // del splash) se pinta directamente sobre este fondo oscuro, SIN esperar a
        // didFinish → la animación se ve siempre, sin importar la velocidad de red.
        webView.isOpaque = false
        webView.backgroundColor = Self.bg
        webView.scrollView.backgroundColor = Self.bg
        if #available(iOS 16.4, *) {
            webView.isInspectable = true
        }
        var request = URLRequest(url: URL(string: "https://otrofestiv.app")!)
        request.cachePolicy = .reloadIgnoringLocalAndRemoteCacheData
        webView.load(request)
        return webView
    }

    func updateUIView(_ webView: WKWebView, context: Context) {
        // Load solo en makeUIView; updates no recargan para no perder estado
        // del WebView (scroll, navegación interna, JS state, autenticación).
    }

    final class Coordinator: NSObject, WKScriptMessageHandler, WKUIDelegate, UNUserNotificationCenterDelegate {
        weak var webView: WKWebView?
        let store = EKEventStore()
        let watchAuth = WatchAuthBridge()   // ← puente del reloj
        let live = LiveActivityBridge()     // ← Live Activity (fase 1)

        override init() {
            super.init()
            // Tocar la Live Activity abre la app EN MI PLAN (otrofestiv://plan).
            NotificationCenter.default.addObserver(forName: .otfOpenPlan, object: nil, queue: .main) { [weak self] _ in
                self?.webView?.evaluateJavaScript("try{switchMainNav('mnav-miplan');showAgView();}catch(e){}", completionHandler: nil)
            }
        }

        // Abre links target="_blank" en Safari del sistema
        func webView(_ webView: WKWebView,
                     createWebViewWith configuration: WKWebViewConfiguration,
                     for navigationAction: WKNavigationAction,
                     windowFeatures: WKWindowFeatures) -> WKWebView? {
            if navigationAction.targetFrame == nil,
               let url = navigationAction.request.url {
                UIApplication.shared.open(url)
            }
            return nil
        }

        // ── Avisos del Plan (27 sep 2026, copy aprobado por Juan) ──────────────
        // La web (persistence.js → _planAvisos) manda la lista ENTERA del festival
        // cada vez que cambia el Plan: {festival, avisos:[{id,title,body,at(ms)}]}.
        // Se reemplazan los pendientes de ESE festival (prefijo), sin tocar otro
        // simultáneo. Notificaciones LOCALES: sin servidor; el reloj las recibe solo.
        private func scheduleAvisos(_ body: [String: Any]) {
            guard let fest = body["festival"] as? String,
                  let avisos = body["avisos"] as? [[String: Any]] else { return }
            let center = UNUserNotificationCenter.current()
            let prefix = "otf.\(fest)."
            center.getPendingNotificationRequests { reqs in
                center.removePendingNotificationRequests(
                    withIdentifiers: reqs.map(\.identifier).filter { $0.hasPrefix(prefix) })
                guard !avisos.isEmpty else { return }
                center.requestAuthorization(options: [.alert, .sound]) { granted, _ in
                    guard granted else { return }
                    let now = Date().timeIntervalSince1970
                    // iOS guarda hasta 64 pendientes por app: los más próximos primero.
                    // «abrir»: destino al tocar el aviso (el del día después → Mi Plan, #1055).
                    let prox = avisos.compactMap { a -> (String, String, String, Double, String?)? in
                        guard let id = a["id"] as? String, let t = a["title"] as? String,
                              let b = a["body"] as? String,
                              let at = (a["at"] as? NSNumber)?.doubleValue else { return nil }
                        return (id, t, b, at / 1000, a["abrir"] as? String)
                    }.filter { $0.3 > now + 1 }.sorted { $0.3 < $1.3 }.prefix(60)
                    for (id, t, b, at, abrir) in prox {
                        let c = UNMutableNotificationContent()
                        c.title = t; c.body = b; c.sound = .default
                        if let abrir = abrir { c.userInfo = ["abrir": abrir] }
                        let trig = UNTimeIntervalNotificationTrigger(timeInterval: at - now, repeats: false)
                        center.add(UNNotificationRequest(identifier: prefix + id, content: c, trigger: trig))
                    }
                }
            }
        }
        // Con la app abierta también se muestra (si no, iOS lo callaría).
        func userNotificationCenter(_ center: UNUserNotificationCenter, willPresent notification: UNNotification,
                                    withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void) {
            completionHandler([.banner, .sound, .list])
        }
        // Tocar un aviso con destino: «Tu festival» abre Mi Plan (mismo camino que
        // la Live Activity, otfOpenPlan). Sin destino, la app abre donde estaba.
        func userNotificationCenter(_ center: UNUserNotificationCenter, didReceive response: UNNotificationResponse,
                                    withCompletionHandler completionHandler: @escaping () -> Void) {
            if (response.notification.request.content.userInfo["abrir"] as? String) == "miplan" {
                NotificationCenter.default.post(name: .otfOpenPlan, object: nil)
            }
            completionHandler()
        }

        func userContentController(_ uc: WKUserContentController,
                                   didReceive message: WKScriptMessage) {
            if message.name == "notifications", let body = message.body as? [String: Any] {
                scheduleAvisos(body); return
            }
            guard message.name == "calendar",
                  let body = message.body as? [String: Any],
                  let events = body["events"] as? [[String: Any]], !events.isEmpty
            else { return }
            requestAccess { [weak self] granted in
                guard let self = self else { return }
                guard granted else { self.sendResult(["status": "denied"]); return }
                let count = self.addEvents(events)
                self.sendResult(count > 0 ? ["status": "added", "count": count]
                                          : ["status": "error"])
            }
        }

        private func requestAccess(_ completion: @escaping (Bool) -> Void) {
            if #available(iOS 17.0, *) {
                store.requestWriteOnlyAccessToEvents { granted, _ in completion(granted) }
            } else {
                store.requestAccess(to: .event) { granted, _ in completion(granted) }
            }
        }

        private func addEvents(_ events: [[String: Any]]) -> Int {
            let cal = store.defaultCalendarForNewEvents
                   ?? store.calendars(for: .event).first { $0.allowsContentModifications }
            guard let calendar = cal else { return 0 }
            var added = 0
            for e in events {
                guard let title = e["title"] as? String,
                      let startMs = (e["start"] as? NSNumber)?.doubleValue,
                      let endMs   = (e["end"]   as? NSNumber)?.doubleValue
                else { continue }
                let ev = EKEvent(eventStore: store)
                ev.title     = title
                ev.startDate = Date(timeIntervalSince1970: startMs / 1000.0)
                ev.endDate   = Date(timeIntervalSince1970: endMs / 1000.0)
                ev.location  = e["location"] as? String
                ev.notes     = e["notes"] as? String
                ev.calendar  = calendar
                do { try store.save(ev, span: .thisEvent, commit: false); added += 1 }
                catch { }
            }
            try? store.commit()
            return added
        }

        private func sendResult(_ dict: [String: Any]) {
            guard let data = try? JSONSerialization.data(withJSONObject: dict),
                  let json = String(data: data, encoding: .utf8) else { return }
            DispatchQueue.main.async { [weak self] in
                self?.webView?.evaluateJavaScript(
                    "window.__otfCalResult && window.__otfCalResult(\(json))",
                    completionHandler: nil)
            }
        }
    }
}

struct ContentView: View {
    var body: some View {
        ZStack {
            // Capa oscura (#0A0A0A) detrás del WebView — defensiva: con
            // isOpaque=false, cualquier pixel sin contenido del WebView deja ver
            // esta capa en vez del blanco por default de SwiftUI.
            Color(red: 0.039, green: 0.039, blue: 0.039).ignoresSafeArea()
            WebViewContainer()
                .ignoresSafeArea(.container, edges: .bottom)
        }
    }
}
