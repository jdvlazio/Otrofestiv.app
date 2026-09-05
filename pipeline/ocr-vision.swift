import Foundation
import Vision
import AppKit

let args = CommandLine.arguments.dropFirst()
for path in args {
    guard let img = NSImage(contentsOfFile: path),
          let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
        print("### \(path)\n[no se pudo abrir]"); continue
    }
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.recognitionLanguages = ["es-ES", "en-US"]
    req.usesLanguageCorrection = true
    let handler = VNImageRequestHandler(cgImage: cg, options: [:])
    do {
        try handler.perform([req])
        let obs = req.results ?? []
        // ordenar por posición: arriba→abajo, izquierda→derecha
        let sorted = obs.sorted { a, b in
            let ay = 1 - a.boundingBox.midY, by = 1 - b.boundingBox.midY
            if abs(ay - by) > 0.012 { return ay < by }
            return a.boundingBox.minX < b.boundingBox.minX
        }
        print("### \(path)")
        for o in sorted { if let t = o.topCandidates(1).first { print(t.string) } }
    } catch { print("### \(path)\n[error: \(error)]") }
}
