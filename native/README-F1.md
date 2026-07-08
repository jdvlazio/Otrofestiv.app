# native/ — Apple Watch F1: integración en Xcode (checklist para Juan)

> **Proyecto correcto (confirmado 8 jul 2026):** el iOS de producción es la app SwiftUI
> **"Otrofestiv"** (`app.otrofestiv.mobile` para iOS), un envoltorio WKWebView. NO es
> Capacitor (ese quedó en v1.2, solo para Android). Todo el trabajo del reloj va acá.
> Plan y arquitectura: `docs/PLAN-apple-watch-F1.md`.
>
> **Fuente canónica del Swift = este repo web.** Se COPIA/AGREGA al proyecto Otrofestiv.

## Estado server-side (hecho, sin Xcode)

- ✅ Edge Function **`watch-auth`** desplegado (verify_jwt on). Rechazos verificados
  (sin JWT → 401; sin sesión de usuario → 401).
- ✅ Web: `src/controller/watch-bridge.js` define `window.__otfWatchAuthRequest` →
  llama `functions.invoke('watch-auth')` → responde por `webkit.messageHandlers.watchAuth`.
  Inerte en web/Android. **Desplegado en otrofestiv.app.**

## A. Puente nativo en el envoltorio (target iOS "Otrofestiv")

1. Abrí el proyecto **Otrofestiv** (el SwiftUI real).
2. Arrastrá `native/ios-wrapper/WatchAuthBridge.swift` al grupo del proyecto
   (junto a `ContentView.swift`) — ✓ "Copy files to destination", Target: **Otrofestiv**.
3. **Editar `ContentView.swift`** — 4 líneas, calcadas del puente de calendario:

   En la clase `Coordinator`, agregá una propiedad:
   ```swift
   let watchAuth = WatchAuthBridge()   // ← NUEVO
   ```

   En `makeUIView(context:)`, junto a `add(context.coordinator, name: "calendar")`:
   ```swift
   config.userContentController.add(context.coordinator.watchAuth, name: "watchAuth")  // ← NUEVO
   ```

   Y después de `context.coordinator.webView = webView`:
   ```swift
   context.coordinator.watchAuth.webView = webView   // ← NUEVO
   context.coordinator.watchAuth.activate()          // ← NUEVO
   ```
4. Build del target **Otrofestiv** (⌘B) → debe compilar.

## B. Target watchOS

1. En el navegador, seleccioná el **proyecto azul "Otrofestiv"** (arriba de todo) para
   que el nuevo target se cree en ESTE proyecto.
2. File → New → Target… → **watchOS → App** → Next.
   - Product Name: `OtrofestivWatch` · Interface: SwiftUI · watchOS 10.0 mínimo.
   - **"Watch App for Existing iOS App"** → en el desplegable elegí **`Otrofestiv`**
     (ahora sí aparece, porque el target creador es el correcto).
   - ✅ Señal de OK: el Bundle Identifier cuelga de `app.otrofestiv.mobile`.
3. Reemplazá los archivos generados por los de `native/watch/`:
   `OtrofestivWatchApp.swift`, `WatchAuthManager.swift`, `ContentView.swift`.
   *(Ojo: el reloj tiene su propio `ContentView.swift` — no confundir con el del iPhone.)*
4. Agregar **supabase-swift** al target del reloj: File → Add Package Dependencies… →
   `https://github.com/supabase/supabase-swift` → producto **Supabase** → target
   `OtrofestivWatch`.
5. Build del target `OtrofestivWatch` (⌘B).

## C. Prueba del circuito (simuladores emparejados)

1. Scheme `Otrofestiv` → simulador de iPhone. **Firmá con tu email** en la app.
2. Scheme `OtrofestivWatch` → Apple Watch emparejado a ese iPhone.
3. En el reloj: `waiting for iPhone…` → **✓ verde con tu email** ("session OK — F1.0 ✓").
4. Si "iPhone no alcanzable": la app del iPhone tiene que estar **abierta en primer
   plano**; Retry en el reloj.

**Reportá:** captura del reloj con el ✓ verde (o el error). Con eso cerramos F1.0.

## Notas

- El reloj recibe un **pase de un solo uso**, no la sesión del teléfono → obtiene SU
  propia sesión (cadena de refresh propia). Compartir la sesión revocaría ambas.
- Cabo abierto a revisar: bundle iOS = `app.otrofestiv.mobile` (correcto); Mac/visionOS
  usan `app.otrofestiv.Otrofestiv`. El reloj cuelga del iOS → `.mobile`.
