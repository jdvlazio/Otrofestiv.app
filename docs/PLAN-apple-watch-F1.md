# PLAN — Apple Watch F1: "Lo que sigue" (spike Swift)

**Estado:** propuesta para aprobación de Juan. Nada implementado.
**Precedente:** `docs/RFC-apple-watch.md` (7 jul 2026). Este plan **ejecuta** la F1 de ese RFC con la arquitectura de autenticación ya verificada contra documentación oficial.
**Fecha:** 7 jul 2026.

---

## 0. Qué cambió desde el RFC (decisiones cerradas)

| Decisión | Valor | Quién / cuándo |
|---|---|---|
| F0 (plan → Supabase) | ✅ **HECHO y verificado en prod** — sync en vivo por Realtime autenticado (PRs #267–#274) | 7 jul 2026 |
| Modelo del reloj | **Extensión del iPhone** (companion): el usuario firma SOLO en el teléfono; el reloj hereda identidad vía handoff. Cero login en el reloj. | Juan, 7 jul 2026 |
| Target mínimo | **watchOS 10+** | Juan, 7 jul 2026 |
| El reloj, ¿planea? | **No.** Solo consume el plan ya calculado (decisión del RFC, sin cambios). | RFC §2 |

### Corrección documentada (errata de la discusión previa)

En la conversación del 7 jul se mencionó "pasar el token por keychain/App Group compartido". **Eso es incorrecto**: desde watchOS 2 el reloj es un dispositivo físicamente separado — **ni el keychain ni los App Groups se comparten** entre iPhone y Watch ([Apple Forums 79866](https://developer.apple.com/forums/thread/79866), [9918](https://developer.apple.com/forums/thread/9918)). El mecanismo sancionado para pasar datos es **WatchConnectivity (`WCSession`)** ([docs](https://developer.apple.com/documentation/watchconnectivity/wcsession), [WWDC21 10003](https://developer.apple.com/videos/play/wwdc2021/10003/)); el reloj luego guarda su sesión en **su propio** keychain.

---

## 1. La restricción que define la arquitectura de auth

**No se puede compartir la sesión de Supabase del teléfono con el reloj.** Los refresh tokens de Supabase son de un solo uso (rotación con gracia de ~10 s). Dos clientes refrescando la MISMA sesión disparan la detección de reuso y **Supabase revoca la familia entera de tokens: se cierra la sesión en ambos dispositivos** ([Supabase — User sessions](https://supabase.com/docs/guides/auth/sessions)).

**Conclusión verificada:** el reloj necesita **su propia sesión** (su propia cadena de refresh), pero creada **sin que el usuario firme en el reloj**.

## 2. Arquitectura del handoff (verificada, con fuentes)

Patrón estándar de "sesión derivada": el teléfono, ya autenticado, le pide al servidor un **pase de un solo uso** para el mismo usuario; el reloj lo canjea por su propia sesión.

```
 ┌─────────── iPhone (Capacitor WebView) ────────────┐
 │ supabase-js con sesión de email (ya existe)        │
 │                                                    │
 │ [4] llama Edge Function watch-auth con su JWT ─────┼──▶ Supabase Edge Function (service-role,
 │ [5] recibe token_hash (pase de un solo uso)  ◀─────┼──   SOLO server-side):
 │                                                    │     · verifica el JWT del caller
 │ Plugin Capacitor "WatchBridge" (Swift, nuevo)      │     · admin.generateLink(magiclink, email
 │ [3] la capa web le entrega el pedido               │       del PROPIO caller)
 │ [6] responde al reloj vía WCSession ───────┐       │     · devuelve properties.hashed_token
 └────────────────────────────────────────────┼───────┘
                                              │ WatchConnectivity (cifrado Apple device-to-device)
 ┌─────────── Apple Watch (SwiftUI) ──────────┼───────┐
 │ [1] abre app; sin sesión en SU keychain    │       │
 │ [2] WCSession.sendMessage("necesito auth") ┘       │
 │ [7] supabase-swift: verifyOTP(tokenHash:) ─────────┼──▶ Supabase Auth
 │ [8] recibe SU PROPIA sesión (cadena propia) ◀──────┼──
 │ [9] persiste en el keychain del reloj; desde acá   │
 │     refresca solo y lee user_festival_state (RLS)  │
 └────────────────────────────────────────────────────┘
```

**Por qué es el diseño correcto (cada pieza con fuente):**
- `admin.generateLink` existe, devuelve `hashed_token`, y exige service-role key **solo en servidor** → Edge Function ([docs](https://supabase.com/docs/reference/javascript/auth-admin-generatelink)).
- `verifyOTP(tokenHash:)` existe en **supabase-swift** y entrega una sesión independiente ([docs Swift](https://supabase.com/docs/reference/swift/auth-verifyotp)); patrón documentado en [Passwordless email logins](https://supabase.com/docs/guides/auth/auth-email-passwordless).
- El token_hash es de un solo uso y expira según `otp_expiry` del proyecto (verificar en dashboard; recomendado ≤ 1 h).
- supabase-swift soporta **watchOS 9+** con Auth, PostgREST y Realtime ([Package.swift](https://github.com/supabase/supabase-swift/blob/main/Package.swift)) — nuestro target 10+ sobra.
- `@capacitor/watch` oficial es **experimental y dormido** (CapacitorLABS, sin soporte) → **no se usa**. En su lugar: plugin Capacitor propio mínimo (una clase Swift) + target watchOS normal en el proyecto Xcode de Capacitor — patrón comunitario estándar.
- UX resultante: el usuario firma una vez en el teléfono; el reloj se conecta **solo**, invisible. Exactamente el modelo "el reloj es extensión del iPhone".

**Seguridad:** service-role key jamás sale del Edge Function; el Edge Function solo genera pases para el email del **propio** caller autenticado (jamás acepta un email por parámetro); el token_hash viaja por WCSession (cifrado Apple) y muere al primer uso.

## 3. Fases de F1 (cada una con entregable y verificación propia)

### F1.0 — Puente de identidad (la fundación)
**Qué:** Edge Function `watch-auth` (Deno/TS, repo web `supabase/functions/`) + plugin Capacitor `WatchBridge` (Swift) + llamada JS en la capa web + esqueleto WCSession del lado reloj.
**Entregables:** código de las 4 piezas + deploy del Edge Function (vía MCP, con aprobación) + test del Edge Function con `curl` (JWT real → token_hash válido; JWT inválido → 401).
**Verificación:** el Edge Function respondiendo en prod es verificable por mí; el circuito WCSession completo se verifica en tu Xcode (checklist).
**Quién:** yo escribo todo; vos compilás el target iOS con el plugin.

### F1.1 — Target watchOS + capa de datos
**Qué:** target watchOS 10 SwiftUI en el proyecto Xcode de Capacitor; paquete supabase-swift; modelos Swift (`UserFestivalState`, `Screening`); auth store (canje del token_hash + persistencia en keychain del reloj + refresh autónomo); fetch del plan (`user_festival_state`) + JSON del festival (HTTPS a otrofestiv.app).
**Entregables:** código Swift completo + instrucciones Xcode paso a paso (estilo checklist APK).
**Verificación:** en simulador — el reloj muestra datos crudos del plan real de tu cuenta.

### F1.2 — UI "Lo que sigue" + Agenda de hoy
**Qué:** las dos pantallas del RFC: próxima función (título, hora, sala, minutos de caminata) y lista mínima del día. SwiftUI puro, watchOS 10.
**Nota de proceso:** todo string visible del reloj es **copy nuevo → decisión de Juan** antes de codear esa parte (regla 3 del protocolo).
**Verificación:** simulador + tu Apple Watch real por TestFlight/build directo.

### F1.3 — Complication (cierre del spike, opcional)
**Qué:** WidgetKit timeline con la próxima función en la esfera. Se decide **después** de evaluar F1.2 en la muñeca.

**Qué NO entra en F1** (sin cambios vs RFC): push/APNs (F2), reportar retrasos (F2), check-in/calificar (F3), planner en el reloj (nunca).

## 4. Dónde vive el código (restricción del repo nativo)

El repo nativo (`~/Otrofestiv.app`) **no admite commits** (comparte remote con producción web — constitución). Por eso:
- **Fuente canónica de TODO el Swift** (plugin + app watch): este repo web, bajo `native/` (`native/ios-plugin/`, `native/watch/`).
- Al proyecto Xcode se **copian** (mismo flujo que `www/` para el APK). El checklist de build documenta la copia.
- Edge Function: `supabase/functions/watch-auth/` en este repo, deploy vía MCP.

## 5. Riesgos de este plan

| # | Riesgo | Mitigación |
|---|---|---|
| 1 | Yo no puedo compilar Swift/Xcode — el loop de verificación pasa por vos | Fases chicas con checklist de compilación cada una; F1.0 tiene partes verificables por mí (Edge Function) |
| 2 | Primer plugin Capacitor propio del proyecto | Es mínimo (1 método, ~40 líneas Swift); patrón documentado |
| 3 | WCSession requiere ambas apps instaladas y emparejadas; timing de reachability | `sendMessage` con reply para el pedido (reloj en foreground) + reintento; `updateApplicationContext` como fallback |
| 4 | Deriva de copy/diseño en el reloj | F1.2 arranca con sesión de copy con Juan; nada de strings inventados |
| 5 | `otp_expiry` del proyecto puede estar alto | Verificarlo en dashboard al inicio de F1.0; recomendado ≤ 1 h |

## 6. Fuentes

- [WCSession — Apple](https://developer.apple.com/documentation/watchconnectivity/wcsession) · [WWDC21 — Data transfer on Apple Watch](https://developer.apple.com/videos/play/wwdc2021/10003/) · [Apple Forums 79866 (no keychain cross-device)](https://developer.apple.com/forums/thread/79866)
- [Supabase — User sessions / refresh token rotation](https://supabase.com/docs/guides/auth/sessions) · [auth.admin.generateLink](https://supabase.com/docs/reference/javascript/auth-admin-generatelink) · [verifyOTP (Swift)](https://supabase.com/docs/reference/swift/auth-verifyotp) · [Passwordless email logins](https://supabase.com/docs/guides/auth/auth-email-passwordless)
- [supabase-swift Package.swift (watchOS 9+)](https://github.com/supabase/supabase-swift/blob/main/Package.swift) · [CapacitorWatch (experimental — descartado)](https://github.com/ionic-team/CapacitorWatch)
- [Authenticating users on Apple Watch — Apple](https://developer.apple.com/documentation/watchos-apps/authenticating-users-on-apple-watch) · [WWDC19 208 — Independent Watch Apps](https://developer.apple.com/videos/play/wwdc2019/208/)
