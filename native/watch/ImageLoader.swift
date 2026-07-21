// ── ImageLoader.swift — carga de imágenes robusta para el reloj (F1.7) ────────
// AsyncImage en listas de watchOS es flaky: no cachea y se cancela al paginar →
// los thumbnails cargan inconsistente (algunos solo al entrar al detalle). Este
// loader cachea en memoria (NSCache) + deja que URLSession use su caché HTTP: una
// vez que una imagen carga (aunque sea en el detalle), reaparece AL INSTANTE en la
// lista y no parpadea entre días. Reemplazo directo del closure de AsyncImage.

import SwiftUI
import UIKit

enum ImageMemoryCache {
    static let cache: NSCache<NSURL, UIImage> = {
        let c = NSCache<NSURL, UIImage>()
        c.countLimit = 150
        return c
    }()
}

struct RemoteImage<Placeholder: View>: View {
    let url: URL?
    @ViewBuilder var placeholder: () -> Placeholder

    @State private var image: UIImage?

    var body: some View {
        Group {
            if let image {
                Image(uiImage: image).resizable().scaledToFill()
            } else {
                placeholder()
            }
        }
        .task(id: url) { await load() }
    }

    private func load() async {
        guard let url else { image = nil; return }
        if let cached = ImageMemoryCache.cache.object(forKey: url as NSURL) {
            image = cached; return
        }
        do {
            let (data, _) = try await URLSession.shared.data(from: url)
            guard let ui = UIImage(data: data), !Task.isCancelled else { return }
            ImageMemoryCache.cache.setObject(ui, forKey: url as NSURL)
            image = ui
        } catch { /* mantener placeholder */ }
    }
}
