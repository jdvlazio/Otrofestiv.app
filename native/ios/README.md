# native/ios — la app iOS de Otrofestiv (Xcode)

Proyecto SwiftUI de producción (`app.otrofestiv.mobile`): envoltorio WKWebView
+ Live Activity + app del Apple Watch + complicación. Desde el 19 oct 2026 vive
acá, versionado; antes estaba en iCloud (`10_iOS`), fuera de git.

- Abrir: `native/ios/Otrofestiv.xcodeproj`. Las carpetas de cada target son
  carpetas sincronizadas: un archivo que se agrega a la carpeta entra al target.
- Compilar sin firmar: `xcodebuild -project native/ios/Otrofestiv.xcodeproj
  -scheme Otrofestiv -destination 'generic/platform=iOS' CODE_SIGNING_ALLOWED=NO build`.
  El bundle es `app.otrofestiv.mobile` también en el simulador (16 nov 2026): antes
  era `app.otrofestiv.Otrofestiv` y el empaquetado con el reloj fallaba.
- Tests del reloj (sin Xcode): `native/ios/tests/watch/run.sh`.
