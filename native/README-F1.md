# native/ — Apple Watch F1: integración en Xcode (checklist para Juan)

> **Fuente canónica del Swift = este directorio del repo web.** El repo nativo
> (`~/Otrofestiv.app`) NO admite commits (constitución) — los archivos se COPIAN
> al proyecto Xcode, igual que el flujo `www/` del APK.
> Plan y arquitectura: `docs/PLAN-apple-watch-F1.md`.

## Estado del server-side (ya hecho, verificable sin Xcode)

- ✅ Edge Function **`watch-auth`** desplegado (v1, `verify_jwt` on). Rechazos verificados:
  sin JWT → 401 de plataforma; JWT no-usuario → `{"error":"invalid token"}` 401.
- ✅ Capa web: `src/controller/watch-bridge.js` responde al evento del plugin
  llamando `functions.invoke('watch-auth')` (no-op fuera de la app iOS).

## Checklist Xcode — F1.0 (puente de identidad)

### A. Plugin en el target iOS existente
1. Abrir `~/Otrofestiv.app/ios/App/App.xcworkspace` en Xcode.
2. Arrastrar `native/ios-plugin/WatchBridgePlugin.swift` al grupo `App/App`
   (✓ "Copy items if needed", target **App**).
3. **Registrar el plugin (Capacitor 6):** si no existe ya un ViewController custom,
   crear `MyViewController.swift` en `App/App`:
   ```swift
   import UIKit
   import Capacitor

   class MyViewController: CAPBridgeViewController {
       override open func capacitorDidLoad() {
           bridge?.registerPluginInstance(WatchBridgePlugin())
       }
   }
   ```
   y en `App/App/Base.lproj/Main.storyboard`, seleccionar el ViewController y en
   Identity Inspector cambiar la clase `CAPBridgeViewController` → `MyViewController`
   (Module: App).
4. Build del target **App** (⌘B) — debe compilar sin errores.

### B. Target watchOS nuevo
1. File → New → Target… → **watchOS → App**.
   - Product Name: `OtrofestivWatch` · Interface: SwiftUI · "Watch App for Existing iOS App" (companion de **App**).
   - Minimum Deployment: **watchOS 10.0**.
2. Reemplazar los archivos generados por los canónicos de `native/watch/`:
   `OtrofestivWatchApp.swift`, `WatchAuthManager.swift`, `ContentView.swift`.
3. **Agregar supabase-swift al target del reloj:** File → Add Package Dependencies…
   → `https://github.com/supabase/supabase-swift` → Add. En "Add to Target",
   producto **Supabase** → target `OtrofestivWatch`.
4. Build del target `OtrofestivWatch` (⌘B).

### C. Prueba del circuito completo (simuladores emparejados)
1. Scheme `App` → correr en un simulador de iPhone. **Firmarse con tu email** en la app.
2. Scheme `OtrofestivWatch` → correr en el Apple Watch emparejado a ese iPhone
   (Xcode crea el par; verificar en Devices que estén emparejados).
3. En el reloj: debe pasar `waiting for iPhone…` → **✓ verde con tu email** ("session OK — F1.0 ✓").
4. Si falla con "iPhone no alcanzable": asegurarse de que la app del iPhone esté
   **abierta y en primer plano**, y Retry en el reloj.

### Qué reportar de vuelta
- Captura del reloj con el ✓ verde (o el error exacto si falla).
- Con eso cerramos F1.0 y arranca F1.1 (datos del plan en el reloj).

## Notas de seguridad (por qué es así)

- El reloj **jamás** recibe la sesión del teléfono: recibe un **pase de un solo uso**
  (`token_hash`) y lo canjea por SU propia sesión (cadena de refresh independiente).
  Compartir una sesión entre dos dispositivos dispararía la detección de reuso de
  refresh tokens de Supabase y **cerraría la sesión en ambos**.
- La service-role key vive SOLO en el Edge Function (server-side).
- El Edge Function solo emite pases para el email del **propio** caller autenticado.
