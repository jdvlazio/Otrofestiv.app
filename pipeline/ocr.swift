// ocr.swift — el texto PINTADO de una imagen, con el OCR del sistema (Vision).
//
// Se usa desde pipeline/ocr.py. Recibe rutas y devuelve una línea JSON por
// imagen: {"ruta": …, "lineas": [...]}. Acepta VARIAS rutas en una sola
// invocación a propósito: `swift ocr.swift` compila en cada llamada, y compilar
// una vez por imagen costaba más que leerla.
//
// PALANCAS (22 sep 2026). Sin ninguna se comporta EXACTAMENTE como antes; están
// para que una segunda lectura sea de verdad otro camino y no la misma dos
// veces —la trampa en la que caí con Jardín, donde «las dos lecturas coinciden»
// no probaba nada porque compartían motor Y parser—:
//
//   --sin-correccion   apaga `usesLanguageCorrection`. NO es un matiz: con el
//                      corrector encendido Vision REESCRIBE lo que le parece
//                      improbable contra su modelo de idioma, que es justo lo
//                      que pasa con nombres propios, siglas y títulos raros.
//                      Las dos lecturas juntas delatan qué «arregló».
//   --escala N         lee la lámina a N× (Lanczos lo hace Python; acá se
//                      recibe ya escalada). Caza lo que se pierde por tamaño:
//                      el «(SO2E6)» de «Cien años de soledad» se leía a 1× y
//                      no a 2×.
//   --candidatos N     además del texto, las N alternativas que Vision barajó
//                      con su confianza. Donde duda, hay que mirar la imagen.
//   --cajas            cada línea con su caja normalizada (x, y, w, h, conf.).
//                      Sin geometría no se puede recortar la franja de logos
//                      del pie, y ahí el OCR nunca coincide consigo mismo:
//                      son logotipos. En Itagüí esa franja era el 100% de las
//                      175 discrepancias de la primera corrida.
import Foundation
import Vision
import AppKit

var rutas: [String] = []
var correccion = true
var conCajas = false
var nCand = 1
var args = Array(CommandLine.arguments.dropFirst())
var i = 0
while i < args.count {
    switch args[i] {
    case "--sin-correccion": correccion = false
    case "--cajas": conCajas = true
    case "--candidatos":
        i += 1
        if i < args.count { nCand = max(1, Int(args[i]) ?? 1) }
    default: rutas.append(args[i])
    }
    i += 1
}

for ruta in rutas {
    var lineas: [String] = []
    var cajas: [[String: Any]] = []
    var alternativas: [[String: Any]] = []
    if let img = NSImage(contentsOfFile: ruta),
       let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) {
        let req = VNRecognizeTextRequest()
        req.recognitionLevel = .accurate
        req.recognitionLanguages = ["es-ES", "en-US", "pt-BR"]
        req.usesLanguageCorrection = correccion
        try? VNImageRequestHandler(cgImage: cg, options: [:]).perform([req])
        for o in (req.results ?? []) {
            let cands = o.topCandidates(nCand)
            if let c = cands.first {
                lineas.append(c.string)
                if conCajas {
                    let b = o.boundingBox
                    cajas.append(["t": c.string, "x": b.minX,
                                  "y": 1 - b.maxY, "w": b.width, "h": b.height,
                                  "c": c.confidence])
                }
            }
            if nCand > 1 && cands.count > 1 {
                alternativas.append([
                    "texto": cands.first?.string ?? "",
                    "otras": cands.dropFirst().map { ["t": $0.string, "c": $0.confidence] },
                ])
            }
        }
    }
    var obj: [String: Any] = ["ruta": ruta, "lineas": lineas]
    if conCajas { obj["cajas"] = cajas }
    if !alternativas.isEmpty { obj["alternativas"] = alternativas }
    if let d = try? JSONSerialization.data(withJSONObject: obj),
       let s = String(data: d, encoding: .utf8) { print(s) }
}
