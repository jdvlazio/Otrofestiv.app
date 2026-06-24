# RFC — Retraso colaborativo

> **Estado:** Aprobado · decisiones cerradas 23 jun 2026 · Fase A en arranque
> **Rol responsable:** Arquitecto de Software Principal — Sistemas distribuidos y tiempo real
> (coordina Trust & Safety + Realtime Backend)
> **Decisión de producto ya tomada:** la señal de retraso es **colaborativa** (no un canal de un operador). Confirmado: *"Solo informa"* — un retraso confirmado por la comunidad **nunca** modifica tu plan; solo muestra un badge.

---

## 1. Objetivo

Que cuando una función va atrasada, los asistentes lo sepan **en tiempo real**, con una señal **creíble** (confirmada por varios, no por uno) y que **caduca sola**. Sin servidor central que arbitre, sin forzar login, sin un punto único de falla. Es el primer feature multiusuario en vivo de la app.

## 2. Qué ya existe (auditoría del sistema actual)

El sistema **personal** de retraso ya está construido y es bueno — esta propuesta no lo reescribe, lo **extiende**.

- **UI de reporte:** Mi Plan → tira de "próxima función", **solo cuando la función está en curso** para vos ([agenda.js:546](../src/view/agenda.js)). Chips **+10 / +15 / +20 / +30** acumulativos bajo "¿Retraso?". Con retraso activo: "+X min", más chips, **deshacer** (pila `filmDelaysHistory`) y **quitar**.
- **Cálculo personal:** el contador "Termina en X" usa `inicio + duración + retraso`; y avisa si el retraso + `FESTIVAL_BUFFER` (15min) + `travelMins(sala→sala)` te hace perder tu próxima función (alerta roja `plan_delay_warn_critico` / ámbar `plan_delay_warn_ajustado`).
- **Modelo:** `filmDelays[título|día|hora]=min` + `filmDelaysHistory`. **100% local** — `saveDelays()` NO llama a `_cloudSave()`, no sincroniza ni a tus otros dispositivos. El **optimizador (`calc.js`) no usa el retraso** (el plan se arma pre-festival; el retraso es del día).
- **i18n:** vocabulario completo ES/EN/PT (`plan_retraso`, `plan_delay_warn_*`, `aria_reportar_retraso`, etc.).
- **Gate de confianza gratis:** el control solo aparece si la función está *en curso* **y** en *tu plan* → los reportes vienen de asistentes plausibles, no de cualquiera. Media defensa anti-Sybil que ya tenemos.

## 3. Conclusión arquitectónica: la capa colaborativa es aditiva

Todo lo *personal* (reportar, magnitud, undo, recálculo, avisos de viaje) queda intacto. Lo colaborativo se engancha en la capa de datos:

```
setDelay() (existente)
   ├─ escribe filmDelays local      → MI recálculo + avisos (HOY, sin cambios)
   └─ [NUEVO] upsert reporte a Supabase
                                     → fan-out Realtime a otros clientes
                                     → estado derivado de confianza (quórum)
                                     → [NUEVO] badge informativo (NO toca tu plan)
```

**"Solo informa" cae perfecto:** *mi* reporte sigue manejando *mi* matemática; el consenso solo pinta un badge.

## 4. Modelo de datos

Tabla nueva `screening_reports` (independiente de `user_festival_state`, que es privada por usuario):

| Columna | Tipo | Notas |
|---|---|---|
| `id` | uuid pk | `gen_random_uuid()` |
| `festival_id` | text | |
| `screening_key` | text | **`título\|día\|hora\|sede`** — ver §4.1 |
| `reporter_id` | uuid | identidad del dispositivo (§5) |
| `delay_min` | int | `check (0..240)` |
| `is_authed` | bool | reporte de usuario con email → peso de confianza |
| `created_at` | timestamptz | `default now()` |
| `updated_at` | timestamptz | |

`unique (festival_id, screening_key, reporter_id)` → **un reporte vigente por persona+función** (upsert). El estado "confirmado" **no se almacena**: es función pura de las filas no expiradas (§7) — sin flags que se desincronicen, convergente entre clientes (estilo CRDT).

### 4.1 La clave necesita la sede
`_delayKey` actual es `título|día|hora` ([agenda.js:1409](../src/view/agenda.js)) — te sirve porque en *tu* plan hay una sola instancia. El dato global puede tener dos funciones de la misma peli el mismo día; el retraso es de una **sala** puntual. La `screening_key` compartida agrega `sede`. (El cliente mapea su `_delayKey` local → `screening_key` global al emitir.)

## 5. Identidad y anti-abuso (Trust & Safety)

Tensión real: el anti-abuso necesita identidad, pero el login es **opcional** a propósito (fue el rechazo de Google).

**Recomendación: Supabase Anonymous Auth.** Cada dispositivo obtiene una sesión anónima en el primer arranque → un `auth.uid()` **confiable por el servidor**, sin email, sin fricción. Con eso:
- **RLS real:** `insert/update` solo si `reporter_id = auth.uid()`; el `unique` garantiza 1 reporte por identidad por función. El quórum cuenta identidades distintas de verdad.
- **Login con email = mejora opcional** que setea `is_authed=true` → mayor peso de confianza, sin ser requisito.
- **Rate-limit:** trigger/función SQL (máx N reportes por `reporter_id` por hora) + detección de anomalías (ráfagas, clusters). 
- **SELECT** abierto (lectura pública de reportes no expirados del festival) — necesario para que todos computen el estado.

## 6. Cliente: enganche

1. Arranque: asegurar sesión anónima Supabase (identidad de reporte).
2. `setDelay` existente: **dual-write** — local (igual que hoy) + upsert a `screening_reports`.
3. Suscripción Realtime a reportes de las funciones **de mi plan en la ventana del día** (no todo el festival).
4. Estado de confianza derivado por función → **badge informativo nuevo**. Por "Solo informa", el badge **no escribe** en `filmDelays` (no altera mi recálculo/avisos).
5. `undoDelay`/`clearDelay` también retiran/ajustan mi fila remota.

## 7. Máquina de estados de confianza

```
sin reportes → tentativo (≥1, sin confirmar) → confirmado (umbral) → decayendo → expirado
```

- **Tentativo se muestra** (etiquetado "sin confirmar · 1 reporte") → da valor incluso con baja densidad, con incertidumbre honesta. (Si se muestra a *otros* o solo al reportero en la Fase B → §11 pregunta abierta.)
- **Confirmado:** umbral alcanzado (§8).
- **Decayendo / Expirado:** §9.

## 8. Quórum adaptativo

El umbral no es un número fijo; es relativo a la **audiencia planificada** (cuánta gente tiene esa función en su `savedAgenda` — dato que sí sincroniza). *Ojo:* el check-in (`checkinLaVi`) marca **watched** retrospectivo, **no** es presencia en vivo; por eso el denominador es audiencia *planificada*, no *presente*.

Marco (los valores exactos se **calibran con datos reales** de la Fase A):
- Piso duro: `≥ 2` identidades distintas. Nunca confirmamos con 1.
- Señal de fuerza: `reporters / audiencia_planificada` → se muestra como "N de ~M" en el badge.
- Peso por confianza: reportes `is_authed` o con historial de aciertos pesan más; mitiga "una persona con 2 teléfonos".
- **Magnitud confirmada = mediana** de los `delay_min` vigentes (robusta ante un valor disparatado).

## 9. Decaimiento

Un reporte está vigente hasta `min(fin_programado_función + 60min, created_at + 120min)`. Pasada la función, la señal expira sola. El cliente nunca muestra retrasos de funciones fuera de `[-30min, +3h]` de ahora.

## 10. Realtime, escala, costo, fallback

- Supabase Realtime (`postgres_changes`) filtrado por `festival_id`; cliente cachea reportes de funciones relevantes y recomputa el estado derivado en cada cambio. **Parchea la UI, no recarga** — mismo modelo que el contador de minutos.
- **Fallback** (el socket se cae / cold start): recomputar también en el tick de 60s y en `visibilitychange` — patrones que la app ya usa.
- **Escala:** cientos de funciones, decenas–cientos de usuarios → holgado en el plan actual de Supabase.

## 11. Observabilidad ("quién audita esto en producción")

El rol posee la verificación en vivo, no solo el diseño:
- **Métricas** (vista SQL / panel simple): reportes por función, identidades distintas, tasa de confirmación, tiempo-a-confirmar, sospechas de abuso.
- En la **Fase A** miramos la tabla llenarse en Ficmontañas para **calibrar** §8/§9 con números reales, no inventados.
- Cliente: dot de sync + log de push/subscribe + errores a la vista.

## 12. Privacidad
`reporter_id` es un uuid anónimo, sin PII. Guardamos festival, `screening_key`, `delay_min`, timestamps. Sin ubicación. El email (si hay login) no se guarda en esta tabla. Purga de reportes tras el festival (§ pregunta abierta).

## 13. Plan de fases

**Fase A — recolección, riesgo CERO de cara al usuario (IMPLEMENTADA 23 jun 2026):**
Anon auth + tabla + RLS + grants + **dual-write** en `setDelay`/`undoDelay`/`clearDelay` → `screening_reports` (con `sede` en la clave). **Sin quórum, sin badge, sin suscripción Realtime** (sería código muerto sin badge que actualizar). Corre en **Ficmontañas (JUL 1–5)** como banco de pruebas real para **recolectar reportes y calibrar** los umbrales de la Fase B; un reporte equivocado solo te afecta a vos, igual que hoy. Auditor repetible: `scripts/verify-delays-cloud.mjs`. *(Nota: la sesión anónima da un `uid` por dispositivo — NO sincroniza tus reportes entre tus dispositivos; eso es exclusivo del login con email.)*

**Fase B — consenso + tiempo real (IMPLEMENTADA 23 jun 2026, defaults seguros para Ficmontañas):**
- **Función pura** `deriveDelayConsensus` (`src/domain/delays.js`): none/tentativo/confirmado + mediana + decaimiento 120 min + quórum por identidades distintas. 8 unit tests.
- **Suscripción Realtime** + caché + `getConsensusMap` (`delays-cloud.js`); `loader.js` (re)suscribe por festival; `main.js` repinta Mi Plan al llegar cambios.
- **Badge** en la tira de Mi Plan ("Va atrasada · ~{min} min" confirmado ámbar; "Posible retraso · sin confirmar" tentativo punteado; disclaimer "reportado por asistentes · no oficial"). i18n es+en+pt. Pasado como **parámetro** a las funciones puras del view (no rompe `[view-purity]`). "Solo informa": no toca el plan.
- Verificado e2e en vivo: 2 sesiones anónimas → confirmado, mediana 25, 2 reporters.

**Defaults conservadores (no "calibrados" aún):** quórum fijo ≥2, decaimiento 120 min. Ficmontañas (JUL 1–5) es el banco de pruebas real; con sus datos se afinan los umbrales y se suma el **quórum adaptativo + peso por confianza + anomalías** (refinación post-festival). El estado tentativo etiquetado da valor aún a baja densidad sin mentir.

## 14. Copy / i18n
Todo string nuevo es **artefacto de Content Design** → va a `src/i18n/i18n.js` (es+en+pt) con paridad COPY‑R4.

**Copy ES aprobado (23 jun 2026, Content Designer + UX Writer):**
- Badge confirmado: **«Va atrasada · ~{min} min»** (ámbar sólido).
- Badge tentativo (1 reporte, sin confirmar): **«Posible retraso · sin confirmar»** (tenue + punteado).
- Disclaimer bajo el badge: **«reportado por asistentes · no oficial»**.

EN/PT se traducen manteniendo el tono conciso existente, en el pase de i18n de la Fase B.

## 15. Riesgos
| Riesgo | Mitigación |
|---|---|
| Confirmación falsa en vivo | Fases A→B + calibración + etiqueta "no oficial" + piso ≥2 + decaimiento |
| Abuso / Sybil | Anon auth + RLS + `unique` + rate-limit + peso por confianza + gate "en curso & en mi plan" |
| Caída de Realtime | Fallback tick 60s + `visibilitychange` |
| Baja densidad → nunca confirma | Estado tentativo visible + quórum por ratio, no conteo fijo |
| Scope creep | Fase A deliberadamente mínima |

## 16. Decisiones (cerradas 23 jun 2026)
1. **Tentativo a terceros:** ✅ **se muestra etiquetado** ("sin confirmar"), distinto del confirmado — maximiza valor a baja densidad con honestidad.
2. **Retención:** ✅ **purgar reportes tras el festival** (job/política de borrado N días después del fin). Detalle de N en la implementación de la Fase B.
3. **Copy:** ✅ cerrado — ver §14.
