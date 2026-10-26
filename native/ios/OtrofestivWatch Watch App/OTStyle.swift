// ── OTStyle.swift — tokens de marca Otrofestiv en watchOS (F1.2) ──────────────
// La marca vive en el COLOR + la jerarquía, no en la fuente (SF Compact para todo
// el texto → legibilidad + Dynamic Type; ver docs/PLAN-apple-watch-F1-2.md).
// Ámbar = firma (hora + acción). Verde = "ahora". Warm-white = texto editorial.
// Fondo: true black (OLED) — la calidez va en el texto, no en la base.

import SwiftUI

enum OT {
    static let amber = Color(red: 0.961, green: 0.620, blue: 0.043)     // #F59E0B
    static let green = Color(red: 0.227, green: 0.667, blue: 0.431)     // #3AAA6E
    static let red   = Color(red: 0.878, green: 0.322, blue: 0.322)     // #E05252
    static let warm  = Color(red: 0.941, green: 0.929, blue: 0.910)     // #F0EDE8 (primario)

    static let secondary = warm.opacity(0.62)   // texto secundario (venue/meta)
    static let faint     = warm.opacity(0.45)    // eyebrows/labels tenues
}
