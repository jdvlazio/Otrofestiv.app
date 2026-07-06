# RFC — Modo Recuerdo (post-festival)

**Estado:** propuesta para auditoría de Juan (Product Owner + Content Designer). Nada implementado.
**Origen:** 6 jul 2026 — feedback de usuarios reales (amigos de Juan, Ficmontañas): el recap de vistas+calificaciones "les gustaba mucho", pero el post-festival actual es tacaño — con 0 vistas borra el plan de la vista, e Intereses es un callejón.
**Principio rector:** cuando el festival termina, la app no se apaga — **cambia de tiempo verbal**. De "qué vas a ver" a "qué viviste". Todo lo planificador se retira; todo lo vivido se celebra.

---

## 1. Diagnóstico del post-festival actual

| Tab | Hoy (festival terminado) | Problema |
|---|---|---|
| Programa | Programa completo navegable, cards con `opacity` reducida | ✅ Aceptable (archivo consultable) |
| Intereses | Empty: "ha terminado → Ver Mi Plan" | Callejón sin salida; tu lista de deseos desaparece |
| Planear | Empty: "ha terminado" (runCalc bloqueado — correcto) | Correcto que no calcule, pero el empty es frío |
| Mi Plan | **Con vistas:** recap (pósters + estrellas) ✅ · **Sin vistas:** empty "No marcaste ninguna" | El recap existente es EL feature; el caso 0-vistas descarta el plan vivido |

## 2. Propuesta por tab

### Mi Plan → **"Tu festival"** (el corazón del modo)
1. **Hero recap** (existente, se conserva): "Viste N películas" + grid de pósters con estrellas, orden: calificación desc → luego sin calificar.
2. **NUEVO — con 0 vistas (o pocas):** el plan confirmado NO desaparece. Se muestra el calendario vivido (read-only) con CTA por ítem: **"¿La viste?"** → marca Vista + pide calificación (flujo de rating existente). Copy hero propuesto: *"Tu plan de {festival}"* / sub: *"Marcá lo que llegaste a ver y calificalo."*
3. **NUEVO — bloque compartir:** botón "Compartir mi festival" reutilizando el share nativo existente (imagen del grid recap). Es el momento de mayor orgullo del usuario = mayor viralidad orgánica de la app.

### Intereses → **"Lo que te llamó"**
- Deja de ser redirect. Muestra la watchlist final, partida en dos: **Vistas** (con estrellas, arriba) y **Te quedaste con ganas** (abajo, atenuadas).
- CTA por ítem no visto: "¿La viste?" (misma marca retroactiva).
- Empty real (watchlist vacía): el actual, sin cambios.

### Planear → se retira con gracia
- Empty state actual pero con copy de cierre (propuesta): *"{festival} ha terminado"* / sub: *"El planeador descansa hasta el próximo festival."* + CTA "Ver mi festival" → Mi Plan.
- `runCalc` sigue bloqueado (sin cambios de lógica).

### Programa → archivo (casi sin cambios)
- Se conserva navegable. Único ajuste: si hay palmarés cargado (campo `award`, pendiente de fuente oficial), badge 🏆 en las cards premiadas — conecta con la decisión abierta del palmarés (opción B: chip dorado en ficha).

## 3. Estados (matriz de verdad)

| Estado | Mi Plan | Intereses |
|---|---|---|
| Vistas > 0 | Recap + plan vivido debajo | Vistas arriba + ganas abajo |
| Vistas = 0, plan > 0 | Plan vivido + "¿La viste?" | Solo "te quedaste con ganas" |
| Vistas = 0, plan = 0, WL > 0 | Empty → CTA a Intereses | Lista con "¿La viste?" |
| Todo vacío | Empty actual | Empty actual |

## 4. Alcance técnico (estimación)

- **F1 (core):** plan vivido en Mi Plan 0-vistas + "¿La viste?" retroactivo + Intereses partido. Reutiliza: `renderContextualHeader`, `ended-poster`, flujo de rating, `_endedStats`. Sin schema nuevo. ~1 sesión.
- **F2 (brillo):** compartir recap como imagen + badge palmarés (depende del campo `award` y fuente oficial). ~1 sesión.
- Guards: los gates son `festivalEnded()` (ya testeado); tests nuevos para la matriz de estados (mismo patrón del QA de dominio).

## 5. Copy — auditado (UX Writer, 6 jul; delegado por Juan)

Principios aplicados: voseo de la casa ("Marcá", "Escaneá") · no repetir info visible · reusar vocabulario ya aprendido por los usuarios antes que inventar.

| Contexto | ES (final) | EN (final) | Nota UX |
|---|---|---|---|
| Hero Mi Plan (0 vistas) | **"Tu festival"** / sub: "Marcá lo que llegaste a ver y calificalo." | "Your festival" / "Mark what you got to see and rate it." | El nombre del festival ya está en el header — no se repite (regla de no-redundancia) |
| Marca retroactiva | **Se reutiliza el par existente "Vista" / "Luego"** | "Seen" / "Later" | Vocabulario ya aprendido en "Funciones sin confirmar"; cero strings nuevas; se descarta "¿La viste?" (introducía una segunda forma para el mismo acto) |
| Sección Intereses (no vistas) | **"Te quedaste con ganas"** | "The ones that got away" | Cálido, voz de marca |
| Sección Intereses (vistas) | **"Vistas"** | "Seen" | Reuso |
| Planear post-festival | **"El planeador descansa hasta el próximo festival."** | "The planner rests until the next festival." | Cierre con la voz del splash ("More than you think possible") |
| Compartir | **"Compartir mi festival"** | "Share my festival" | — |
| Tabs | **Sin cambios de nombre por fase** | — | Los tabs son anclas de navegación; solo cambia su contenido ("Lo que te llamó" descartado como título) |

Todas las strings nuevas → `_I18N` (es+en), validadas por `[i18n-complete]`.

## 6. Decisiones (Product Manager, 6 jul; delegado por Juan)

1. **Sin período de gracia.** El modo entra con `festivalEnded()` — el propio modo permite marcar Vista y calificar, así que no hay nada que "esperar". Menos estados, menos bugs.
2. **La marca retroactiva no expira.** Es memoria del usuario; los festivales archivados siguen consultables y el costo es cero.
3. **Compartir = F2, ya** — independiente del RFC de retraso colaborativo (no comparten backend; el share reutiliza el flujo nativo existente).
4. **Nombre interno: "Modo Recuerdo"** (solo docs, nunca UI).

**Estado: RFC cerrado — listo para implementar F1.** El visual final de cada pantalla lo audita Juan sobre la implementación (como la landing).
