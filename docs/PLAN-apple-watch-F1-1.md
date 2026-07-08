# PLAN — Apple Watch F1.1: el plan real en el reloj (capa de datos)

**Estado:** propuesta para aprobación de Juan. Depende de F1.0 verificado (✓ verde en Xcode).
**Precedente:** `docs/PLAN-apple-watch-F1.md` (F1.0 = puente de identidad, hecho).
**Alcance F1.1:** que el reloj **lea el plan real** del usuario y calcule "la próxima función". SIN UI de producto todavía (eso es F1.2) — F1.1 termina con datos crudos en pantalla de diagnóstico.

---

## 1. Qué produce F1.1

Con F1.0, el reloj ya tiene **su propia sesión Supabase**. F1.1 la usa para:
1. Saber **qué festival** mostrar (el activo en el teléfono).
2. Traer el **plan** del usuario para ese festival (`user_festival_state`).
3. Traer el **JSON del festival** (títulos, horarios, sedes) por HTTPS.
4. Cruzar plan + JSON + reloj actual → **"próxima función"** y **agenda de hoy**.

El reloj **no planea**: `saved_agenda.schedule` ya viene calculado por el teléfono. El reloj solo lo lee, lo cruza con el catálogo y lo ordena por hora.

## 2. Decisión abierta (necesita tu OK): ¿cómo sabe el reloj el festival activo?

El teléfono guarda el festival activo en `localStorage` (`otrofestiv_festival`); el reloj no lo ve. Dos opciones:

- **A (recomendada): el teléfono lo empuja.** Extendemos el plugin `WatchBridge` para mandar `{activeFestival, festivalMeta}` por `WCSession.updateApplicationContext` (último-valor, llega en background). El reloj siempre sabe la verdad, sin lógica de clasificación duplicada. ~15 líneas Swift + 5 JS.
- **B: el reloj lo infiere.** El reloj baja la lista de festivales y elige el "en curso" por fechas. Evita tocar el teléfono, pero **reimplementa en Swift la clasificación de festivales** (que hoy vive en JS) — justo lo que el RFC dice evitar.

→ **Propongo A.** Cero lógica duplicada; el teléfono es la fuente de verdad, consistente con todo F0/F1.

## 3. Fases

### F1.1.0 — Festival activo por WCSession (si elegís A)
- **Plugin iOS:** al cambiar de festival / al activar la sesión, `updateApplicationContext(["activeFestival": id])`.
- **Web:** llamar un método nuevo `WatchBridge.setActiveFestival(id)` desde `loadFestival` (loader.js) — no-op fuera de iOS.
- **Reloj:** `WCSession` recibe el context → guarda el festival activo.
- **Verificación:** log en el reloj mostrando el id recibido.

### F1.1.1 — Modelos + capa de datos (Swift)
- **Modelos** (`Codable`) espejo de la fila `user_festival_state` (`watchlist`, `watched`, `saved_agenda.schedule[]`, `ratings`, `updated_at`) y del JSON del festival (subset: `title`, `day`, `time`, `venue`, coords para caminata).
- **`PlanRepository`:**
  - `fetchPlan(festivalId)` → `supabase.from("user_festival_state").select().eq(...).single()` (misma RLS; ya autenticado por F1.0).
  - `fetchFestival(festivalId)` → `URLSession` GET a `https://otrofestiv.app/festivals/<slug>.json` (mismo archivo que la web; sin auth).
- **Verificación:** en el simulador, la pantalla de diagnóstico imprime "N funciones en tu agenda" con el conteo real de tu plan.

### F1.1.2 — Cómputo "próxima función" + "agenda de hoy" (Swift puro, testeable)
- Función pura `nextScreening(schedule, now, tz)` → la próxima función no pasada (timezone Colombia UTC−5, igual que la web).
- `todayAgenda(schedule, now)` → funciones de hoy ordenadas por hora.
- **Estas son puras → llevan tests Swift** (XCTest), espejando el rigor de los 233 tests JS. Casos: sin plan, todo pasado, borde de medianoche, multi-día.
- **Verificación:** tests verdes + diagnóstico mostrando título/hora de la próxima función real.

### F1.1.3 — Refresh
- Recalcular al abrir la app y al volver de background (`scenePhase`).
- (Realtime en vivo del plan en el reloj → se evalúa en F2, no acá; F1.1 refresca al mirar la muñeca, que es el caso de uso real.)

## 4. Lo que NO entra en F1.1
UI de producto (F1.2, con sesión de copy previa), complications (F1.3), push/retrasos (F2), check-in/calificar (F3).

## 5. Riesgos
| # | Riesgo | Mitigación |
|---|---|---|
| 1 | Firmas exactas de supabase-swift (verifyOTP/select) varían por versión | Confirmar contra el SDK que resuelva SPM (autocomplete de Xcode); el plan marca los puntos a validar |
| 2 | Decodificar `saved_agenda` (JSONB anidado) en Swift Codable | Modelar `schedule` como `[ScheduleItem]` con `CodingKeys`; test de decodificación con un row real |
| 3 | Timezone: la web usa UTC−5 fijo (nunca toISOString para lógica) | El cómputo Swift usa el mismo offset fijo; test de borde de medianoche |
| 4 | Duplicar lógica de dominio en Swift | Solo se duplica "próxima función" (trivial y testeada); el planner NO se toca (el reloj lee `saved_agenda` ya resuelto) |

## 6. Verificación end-to-end de F1.1
En el simulador (o tu reloj): la pantalla de diagnóstico muestra, de tu plan REAL de Ficmontañas, el **título + hora de la próxima función** y el **conteo de la agenda de hoy**. Eso prueba el circuito datos completo y habilita F1.2 (la UI linda).
