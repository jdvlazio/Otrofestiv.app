# native/ios — la app iOS de Otrofestiv (Xcode)

Proyecto SwiftUI de producción (`app.otrofestiv.mobile`): envoltorio WKWebView
+ Live Activity + app del Apple Watch + complicación. Desde el 19 oct 2026 vive
acá, versionado; antes estaba en iCloud (`10_iOS`), fuera de git.

- Abrir: `native/ios/Otrofestiv.xcodeproj`. Las carpetas de cada target son
  carpetas sincronizadas: un archivo que se agrega a la carpeta entra al target.
- Compilar sin firmar: `xcodebuild -project native/ios/Otrofestiv.xcodeproj
  -scheme Otrofestiv -destination 'generic/platform=iOS' CODE_SIGNING_ALLOWED=NO build`.
  En el simulador el bundle es `app.otrofestiv.Otrofestiv` (solo dispositivo
  usa `.mobile`) y el empaquetado con el reloj falla; es así de origen.
- Tests del reloj (sin Xcode): `native/ios/tests/watch/run.sh`.
