// OCR local con Vision (el mismo motor de Live Text). Lee imágenes y escribe
// JSON: por cada línea reconocida, su texto y su caja (x,y,w,h normalizadas).
// La caja importa: la plantilla de FICMA es fija, así que la POSICIÓN dice qué
// campo es cada línea — sin eso, «Brasil» y «86 min» son solo dos strings.
import Foundation
import Vision
import AppKit

struct Linea: Codable { let t: String; let x: Double; let y: Double; let w: Double; let h: Double; let c: Double }

var salida: [String: [Linea]] = [:]

for ruta in CommandLine.arguments.dropFirst() {
    guard let img = NSImage(contentsOfFile: ruta),
          let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
        FileHandle.standardError.write("no se pudo abrir: \(ruta)\n".data(using: .utf8)!)
        continue
    }
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    // es primero: el documento es en español y «PAÍS»/«DIRECCIÓN» se degradan
    // a «PAIS»/«DIRECCION» si el motor asume inglés.
    req.recognitionLanguages = ["es-ES", "en-US", "pt-BR"]
    req.usesLanguageCorrection = true
    try? VNImageRequestHandler(cgImage: cg, options: [:]).perform([req])

    var lineas: [Linea] = []
    for obs in (req.results ?? []) {
        guard let top = obs.topCandidates(1).first else { continue }
        let b = obs.boundingBox   // origen abajo-izquierda, normalizado
        lineas.append(Linea(t: top.string,
                            x: Double(b.minX),
                            y: Double(1 - b.maxY),   // a origen arriba-izquierda
                            w: Double(b.width),
                            h: Double(b.height),
                            c: Double(top.confidence)))
    }
    salida[(ruta as NSString).lastPathComponent] = lineas.sorted { $0.y < $1.y }
}

let data = try JSONEncoder().encode(salida)
FileHandle.standardOutput.write(data)
