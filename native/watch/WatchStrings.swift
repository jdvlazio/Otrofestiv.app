// ── WatchStrings.swift — i18n del reloj (F1.5) ────────────────────────────────
// MIEMBRO DE DOS TARGETS: "OtrofestivWatch Watch App" y "OtrofestivComplication".
// El reloj sigue el idioma del SISTEMA (watchOS locale) — nativo. es por defecto;
// en si el idioma del dispositivo es inglés. Las strings del festival (títulos,
// sedes) vienen de la data, no se traducen acá; esto es solo la UI del reloj.

import Foundation

enum Lang {
    case es, en
    // preferredLanguages, NO Locale.current: Locale.current se resuelve contra las
    // localizaciones DECLARADAS del bundle — y este target no declara es.lproj, así
    // que con el sistema en español devolvía "en" y TODO lo que pasa por L salía en
    // inglés ("Retry", "THU AUG 13") junto a strings hardcodeadas en español.
    // Evidencia: Store_Screenshots/reporte-strings (2 ago 2026).
    // preferredLanguages es la preferencia REAL del usuario, independiente del bundle.
    static var current: Lang {
        (Locale.preferredLanguages.first ?? "es").hasPrefix("en") ? .en : .es
    }
}

enum L {
    private static func t(_ es: String, _ en: String) -> String {
        Lang.current == .en ? en : es
    }

    static var opening: String        { t("abriendo…", "opening…") }
    static var connectingPhone: String { t("conectando con tu iPhone…", "connecting to your iPhone…") }
    static var loadFailed: String     { t("No se pudo cargar", "Couldn’t load") }
    static var noPlanTitle: String    { t("Sin plan", "No plan") }
    static var noPlanDetail: String   { t("Armá tu plan en el teléfono.", "Build your plan on your phone.") }
    static var now: String            { t("AHORA", "NOW") }
    static var retry: String          { t("Reintentar", "Retry") }
    // Errores del handoff con el iPhone (copy aprobado por Juan, 2 ago 2026).
    // Cortos a propósito: el largo anterior se truncaba hasta en Ultra 3.
    static var phoneUnreachable: String { t("Abrí Otrofestiv en tu iPhone", "Open Otrofestiv on your iPhone") }
    static var phoneNoSession: String  { t("Inicia sesión en Otrofestiv en tu iPhone", "Sign in to Otrofestiv on your iPhone") }
    static var next: String           { t("PRÓXIMA", "NEXT") }
    // Retraso v2 (aprobado por Juan, 25 sep 2026) — la misma frase que Mi Plan.
    static func startedLate(_ n: Int) -> String { t("Empezó \(n) min tarde", "Started \(n) min late") }
    // Progreso en vivo (21 sep 2026): UNA sola frase, la misma que Mi Plan usa en
    // el teléfono («Termina en»). Se retiró «faltan» en la revisión de copy.
    static func endsIn(_ min: Int) -> String { t("Termina en \(min) min", "Ends in \(min) min") }
    static var complicationLiveName: String { t("En curso", "Now playing") }
    // Programa en el reloj (22 sep 2026, copy aprobado con Juan en el mockup v3).
    static var miPlan: String         { t("Mi Plan", "My Plan") }
    static var program: String        { t("Programa", "Schedule") }
    static var today: String          { t("Hoy", "Today") }
    static var tomorrow: String       { t("Mañana", "Tomorrow") }
    static var inPlan: String         { t("En tu Plan", "In your Plan") }     // solo accesibilidad: el filete ámbar lo dice
    // «Programa de hace 3 h» — la caché envejeció y la red no la renovó.
    static func scheduleFrom(hours h: Int) -> String { t("Programa de hace \(h) h", "Schedule from \(h) h ago") }
    static var complicationName: String { t("Próxima función", "Next screening") }
    static var complicationDesc: String { t("Tu próxima película del festival.", "Your next festival film.") }
}
