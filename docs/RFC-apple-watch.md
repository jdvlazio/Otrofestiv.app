# RFC — Otrofestiv para Apple Watch (y el camino a Swift nativo)

**Estado:** ideación / plan de acción para auditoría de Juan. Nada implementado.
**Alcance de ESTE RFC:** solo Apple Watch. La migración de iOS a Swift nativo se menciona como *contexto de dirección*, no se diseña aquí.
**Fecha:** 7 jul 2026. Documentación consultada: watchOS 26, Supabase Swift SDK v2.46.0, WidgetKit complications, WatchConnectivity (fuentes al pie).

---

## 0. La verdad arquitectónica (define todo lo demás)

El modelo actual —Capacitor cargando `otrofestiv.app` en un WebView— **no existe en watchOS**. El reloj no tiene WebView utilizable: las apps son **SwiftUI nativo, obligatorio**. Consecuencias:

1. Un watch NO es "extender la web". Es una **app nueva en Swift** — codebase, lenguaje y herramientas (Xcode) aparte del vanilla-JS de hoy.
2. La **lógica de dominio en JS** (planner, `computeScenarios`, conflictos, huecos — lo que blindamos con 218 tests) **no se puede importar** a Swift. Dos caminos: reimplementarla (costoso + doble mantenimiento + doble superficie de bugs) o **que el reloj NO planee** y solo consuma un plan ya calculado. → **Decidido abajo: el reloj consume, no planea.**
3. Requisitos de entorno nuevos: **Mac + Xcode**, cuenta **Apple Developer** (ya la tenemos — la app iOS existe), y build/signing de un target watchOS (proceso Xcode, no CLI — igual que el APK).

## 1. El prerrequisito DURO: el estado del usuario en la nube

Hoy el plan/watchlist/ratings del usuario viven en **localStorage** dentro del WebView del teléfono. Un reloj —app independiente— **no puede leer eso**. Sin resolver esto, no hay Apple Watch posible.

**Buena noticia:** media base ya está puesta en Supabase — `user_festival_state` y `screening_reports` (los retrasos colaborativos). El prerrequisito es **completar el cloud-sync del plan** (savedAgenda + watchlist + watched + ratings) a `user_festival_state`, con Anonymous Auth (ya en uso).

**Este paso vale por sí solo, hoy, sin watch:** da sync real entre iPhone/iPad/web del mismo usuario — algo que la app promete a medias. Es el paso #1 lo hagamos o no el reloj.

## 2. Arquitectura propuesta: **app independiente que lee la nube**

```
                    Supabase (ya existe)
                   ┌───────────────────────┐
   iPhone (web) ──▶│ user_festival_state   │◀── Apple Watch (SwiftUI nativo)
   planea, marca   │ screening_reports     │    lee plan + retrasos
                   └───────────────────────┘    NO planea
   festivals/*.json (GitHub Pages, HTTPS) ◀───── Watch lee el JSON del festival
```

- **App watchOS INDEPENDIENTE** (no companion-dependiente): instala/corre sola, lee Supabase (SDK Swift oficial, soporta watchOS) + el JSON del festival por HTTPS. Ventaja: no depende del Capacitor iOS (que es un WebView difícil de puentear a WatchConnectivity).
- **Fuente de verdad del plan = Supabase.** El watch nunca calcula; muestra lo que el teléfono ya decidió.
- **SwiftUI puro** (no WatchKit) — requisito para que las complications actualicen de forma confiable.

## 3. Restricciones de la plataforma (y cómo se respetan)

| Restricción watchOS | Implicación | Mitigación |
|---|---|---|
| Complications actualizan ~4×/hora (presupuesto) | No sirve para "cuenta regresiva al minuto" por polling | La complication muestra la **próxima función** (cambia pocas veces/día); WidgetKit timeline con entradas pre-calculadas para las transiciones |
| Tocar la complication fuerza refresh **sin costo** | El usuario que mira su muñeca ya la refresca | Suficiente para el caso de uso real |
| Background refresh acotado | No podés pollear retrasos en vivo | **Los retrasos llegan por PUSH (APNs)** — no por polling |
| Push inmediato actualiza complication | El delay en vivo SÍ es viable | Requiere backend de push → ver Riesgo R3 |

## 4. Feature set — el reloj es "el día del festival, en la muñeca"

Principio: **el teléfono planea, el reloj ejecuta.** Glanceable, segundos de atención, sin teclado.

### F0 — Prerrequisito (web, sin Swift): plan → Supabase
Cloud-sync completo de `user_festival_state`. Vale solo. Desbloquea todo lo demás.

### F1 — MVP del reloj (SwiftUI): "Lo que sigue"
- **Pantalla "Ahora / Lo que sigue":** próxima función — título, hora, sala, minutos de caminata (venue coords ya en los datos).
- **Agenda de hoy:** lista mínima scrolleable del plan del día.
- **Complication en la esfera:** "AHORA: [film]" o cuenta regresiva a la próxima. La razón #1 para levantar la muñeca.

### F2 — Retrasos en vivo (push)
- Notificación **"Tu función empieza en 20 min"** y **alertas de retraso** del consenso colaborativo (`screening_reports` ya existe). El delay en la muñeca es EL caso de uso arquetípico del watch.
- **Reportar retraso con un tap** desde la sede — alimenta el consenso. Reportar en el momento, sin sacar el teléfono.

### F3 — Check-in + calificar
- "La vi" con un tap + **estrellas con la Digital Crown** (gesto nativo hermoso de watchOS). Escribe a `user_festival_state` → se refleja en el teléfono (recap de Modo Recuerdo).

**Fuera del reloj (se quedan en el teléfono):** Programa completo, Planear (cómputo pesado + pantalla), búsqueda, selección de festival, onboarding.

## 5. Costos reales (honestos)

- **Skillset nuevo:** Swift/SwiftUI/Xcode. Es un lenguaje y un stack distinto del vanilla-JS. Curva de aprendizaje real.
- **Doble codebase:** web (7 festivales, planner, QA de 218 tests) + Swift (watch). Cada feature de datos nuevo hay que pensarlo en dos lados. Mitigado porque el watch es **read-mostly** y acotado.
- **Infra de push (F2):** APNs necesita backend — Supabase Edge Function + certificados APNs. Complejidad y mantenimiento nuevos.
- **Build/release:** target watchOS en Xcode, signing manual (como el APK), review de App Store para el watch app.
- **Tiempo:** F0 ≈ 1–2 sesiones (web). F1 ≈ varias semanas (primer Swift, MVP). F2/F3 ≈ semanas adicionales.

## 6. Riesgos y mitigaciones

| # | Riesgo | Prob. | Mitigación |
|---|---|---|---|
| R1 | Curva de Swift ralentiza todo; el reloj no es un PR, es un producto | Alta | Empezar por F0 (web, cero Swift, valor inmediato) mientras se aprende Swift en paralelo con un spike acotado (solo F1 "Lo que sigue", read-only) |
| R2 | Doble mantenimiento diverge (web y watch muestran datos distintos) | Media | Supabase como **única fuente de verdad**; el watch nunca deriva lógica, solo lee estado ya calculado |
| R3 | Push/APNs es infra nueva y frágil | Media | F2 es opcional y posterior; F1 no necesita push (funciona con refresh al tocar) |
| R4 | El planner en Swift sería una reimplementación con bugs nuevos | Alta si se intentara | **No se reimplementa** — el reloj no planea (decisión de arquitectura) |
| R5 | Esfuerzo grande, adopción incierta del watch entre tu audiencia | Media | F0 vale sin el watch; F1 es un spike medible antes de comprometerse a F2/F3 |

## 7. Relación con la migración futura de iOS (solo contexto)

La app iOS es hoy un Capacitor thin-client. Una migración a SwiftUI nativo sería un proyecto **mucho mayor** (reimplementar TODA la lógica que hoy vive en JS + los 218 tests de dominio). **El watch es el experimento barato para aprender Swift** sin arriesgar la app iOS que ya funciona: si F1 sale bien, tenemos base y criterio para evaluar el iOS nativo con datos reales, no con corazonadas. Si el watch enseña que el costo Swift es mayor al esperado, lo supimos con un spike acotado, no rehaciendo la app entera. **No se decide iOS aquí.**

## 8. Recomendación

1. **Hacer F0 ya** (plan → Supabase). Cero Swift, valor inmediato (sync multi-dispositivo), desbloquea el reloj. Encaja con el backlog actual.
2. **Spike de F1** ("Lo que sigue" read-only) como primer contacto con Swift — acotado, medible, sin push.
3. **Decidir F2/F3 y el iOS nativo DESPUÉS**, con la experiencia real del spike en la mano.

## 9. Preguntas abiertas para Juan

1. ¿Arrancamos por F0 (Supabase sync) esta semana, independiente del reloj?
2. ¿El spike de F1 lo hago yo escribiendo Swift, o preferís sumar a alguien con experiencia watchOS para el primer target?
3. ¿Target mínimo de watchOS? (watchOS 10 da el diseño nuevo; bajar a 9 amplía dispositivos viejos.)
4. Nombre del proyecto watch: ¿"Otrofestiv" a secas en la esfera, o algo más corto para la complication?

---

### Fuentes
- [Creating independent watchOS apps — Apple Developer](https://developer.apple.com/documentation/watchos-apps/creating-independent-watchos-apps)
- [Creating a watchOS app — SwiftUI Tutorials](https://developer.apple.com/tutorials/swiftui/creating-a-watchos-app)
- [Supabase Swift SDK — Swift Package Index (v2.46.0, watchOS)](https://swiftpackageindex.com/supabase/supabase-swift)
- [Keeping a widget up to date — Apple Developer (WidgetKit timelines)](https://developer.apple.com/documentation/widgetkit/keeping-a-widget-up-to-date)
