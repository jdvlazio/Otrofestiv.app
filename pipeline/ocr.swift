// ocr.swift — el texto PINTADO de una imagen, con el OCR del sistema (Vision).
//
// Se usa desde pipeline/ocr.py. Recibe rutas y devuelve una línea JSON por
// imagen: {"ruta": …, "lineas": [...]}. Acepta VARIAS rutas en una sola
// invocación a propósito: `swift ocr.swift` compila en cada llamada, y compilar
// una vez por imagen costaba más que leerla.
import Foundation
import Vision
import AppKit

for ruta in CommandLine.arguments.dropFirst() {
    var lineas: [String] = []
    if let img = NSImage(contentsOfFile: ruta),
       let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) {
        let req = VNRecognizeTextRequest()
        req.recognitionLevel = .accurate
        req.recognitionLanguages = ["es-ES", "en-US", "pt-BR"]
        req.usesLanguageCorrection = true
        try? VNImageRequestHandler(cgImage: cg, options: [:]).perform([req])
        for o in (req.results ?? []) {
            if let c = o.topCandidates(1).first { lineas.append(c.string) }
        }
    }
    let obj: [String: Any] = ["ruta": ruta, "lineas": lineas]
    if let d = try? JSONSerialization.data(withJSONObject: obj),
       let s = String(data: d, encoding: .utf8) { print(s) }
}
