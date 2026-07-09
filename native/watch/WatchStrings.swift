// ── WatchStrings.swift — i18n del reloj (F1.5) ────────────────────────────────
// MIEMBRO DE DOS TARGETS: "OtrofestivWatch Watch App" y "OtrofestivComplication".
// El reloj sigue el idioma del SISTEMA (watchOS locale) — nativo. es por defecto;
// en si el idioma del dispositivo es inglés. Las strings del festival (títulos,
// sedes) vienen de la data, no se traducen acá; esto es solo la UI del reloj.

import Foundation

enum Lang {
    case es, en
    static var current: Lang {
        (Locale.current.language.languageCode?.identifier == "en") ? .en : .es
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
    static var next: String           { t("PRÓXIMA", "NEXT") }
    static var complicationName: String { t("Próxima función", "Next screening") }
    static var complicationDesc: String { t("Tu próxima película del festival.", "Your next festival film.") }
}
