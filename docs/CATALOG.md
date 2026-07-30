# RFC — Catálogo madre de películas (Master Data, forward-only)

> **Estado:** Propuesta · pendiente de aprobación de Juan
> **Rol responsable:** Data Architect — Master Data Management (MDM) & Data Governance
> **Criterio de producto (Juan):** *"Pensar a futuro, no arreglar lo viejo."* El sistema previene inconsistencias **en onboardings nuevos**; los 7 festivales actuales se dejan como están. **La app NO cambia** — el catálogo actúa en *write-time* (onboarding), nunca en runtime.

---

## 1. Objetivo

Que una película que pasa por **varios festivales** tenga **una sola verdad** (año, duración, director, sinopsis, póster, ids), reutilizable y consistente — sin re-investigar cada vez y sin que dos festivales muestren datos distintos de la misma peli. Es el primer sistema de **datos maestros** del proyecto.

## 2. El problema, medido (no asumido)

De **807 títulos únicos** en los 7 festivales, **13 se repiten** en ≥2 festivales (~1.6%). Poco, pero la **divergencia es real y de cara al usuario**:

| Película | Festivales | Divergencia |
|---|---|---|
| **Piedras preciosas** | AFF / FICCI | año **2026 vs 2019** (la verdad es 2026: estrenó en FICCI y vino a AFF) |
| **Cartas a mis padres muertos** | Cinemancia / Olhar | duración **106 vs 124 min** |
| **An Incomplete Calendar** | FICCI / Olhar | 77 vs 70 min; Olhar con póster+sinopsis, FICCI sin |
| **Crocodile · Mu-Ki-Ra · Refracción** | varios | uno tiene póster/sinopsis, el otro está flaco → **reuso desperdiciado** |

**Dos trampas que el diseño DEBE respetar** (vistas en los datos):
- **Identidad ≠ título.** "Madres de nacimiento" en FICCI es **8 min** (sin póster/sinopsis); en Ficmontañas es un **documental**. Probablemente **dos películas distintas con el mismo título** → fusionarlas por título sería un error de datos (la misma lección que el match-por-título trajo malas sinopsis, *"Brujo"*, ver `docs/PIPELINE.md`).
- **La memoria humana falla.** Se creía que "Chicas Tristes" estuvo en Tribeca + FICCI; en los datos está **solo en FICCI** (duplicada dos veces *dentro* de FICCI). Las decisiones de match se toman contra **datos**, no recuerdos.

## 3. Principio rector: forward-only, write-time, aditivo

```
Onboarding de festival NUEVO
   ├─ resolver cada film contra catalog/films.json (por TMDB id)
   │     ├─ match  → pre-llenar datos agnósticos desde el catálogo
   │     │           + GUARD: si el festival contradice al catálogo → falla, Juan arbitra
   │     └─ no-match → candidato a registro NUEVO del catálogo
   └─ el JSON del festival queda self-contained (snapshot) → la app NO cambia
```

- **No se migra el pasado.** Los 7 festivales actuales quedan intactos (4 archivados, 2 recién terminados). Su data, con o sin errores, es **deuda aceptada**: nadie planifica sobre ellos.
- **No hay base de datos en runtime.** El planner sigue leyendo JSONs self-contained → **cero riesgo** al sistema que ya funciona. El catálogo vive y actúa **solo en el pipeline de onboarding**.
- **Aditivo:** el catálogo *alimenta* el JSON del festival; no lo reemplaza.

## 4. Modelo de datos — `catalog/films.json`

Objeto keyeado por **id canónico** (no por título):

```jsonc
{
  "tmdb:1670058": {
    "canonical_title": "Herencia: Los Cantos de la Tierra",
    "original_title":  "Herencia: Los Cantos de la Tierra",
    "director": "Iván Acosta Rojas",
    "country":  "Colombia",
    "year":     2026,
    "runtime_min": 82,
    "synopsis":    "…",          // origen ES
    "synopsis_en": "…",
    "poster": "/assets/…/herencia.png",
    "ids": { "tmdb": 1670058, "letterboxd": "herencia-los-cantos-de-la-tierra", "imdb": null },
    "appears_in": ["aff-2026", "olhar-2026"],     // procedencia: qué festivales la referencian
    "provenance": { "year": "TMDB+LB", "poster": "olhar-2026" }  // de dónde salió cada dato (auditoría)
  },
  "slug:cuando-la-palabra-se-hace-busqueda": {     // sin TMDB → id canónico verificado a mano
    "canonical_title": "Cuando la palabra se hace búsqueda", "director": "Frank Benítez Peña", "...": "..."
  }
}
```

- **Solo campos agnósticos al festival.** Lo festival-específico (sección, día/hora/sede, premiere, framing editorial) **nunca** entra al catálogo: vive en el JSON del festival (`docs/SCHEMA.md`).
- `provenance` documenta el origen de cada dato → cuando hay conflicto, se ve quién tenía razón.
- `appears_in` da trazabilidad inversa sin que la app lo lea.

## 5. Identidad y resolución de matches (el nudo)

| Caso | Llave | Cómo se resuelve |
|---|---|---|
| Con TMDB id | `tmdb:<id>` | **automático y confiable** — `enrich-festival.py` ya trae el TMDB id |
| Sin TMDB (muchos cortos) | `slug:<título-normalizado>` | **match propuesto, confirmado por humano** — nunca auto-fusión |

- **TMDB id es la única identidad fuerte.** El slug es candidato, no veredicto: el resolver propone, Juan confirma (un click "sí/no es la misma"). Esto evita el merge "Madres 8min ↔ Madres doc".
- Señales de apoyo para des-ambiguar un match propuesto: director + duración (±2 min) + país. Si discrepan → se trata como **películas distintas**, no como conflicto a fusionar.
- Sin TMDB y sin confirmación → entra como registro propio (no se fuerza el match). Falso-distinto es barato; **falso-igual corrompe dos pelis** → el default es no-fusionar.

## 6. Split catálogo ↔ festival (modelo de override)

| Campo | Dueño | Override del festival |
|---|---|---|
| año, duración, director, país, sinopsis, póster, ids | **catálogo** | permitido pero **flaggeado** por el guard (ej. corte restaurado con otra duración) |
| sección, día, hora, sede, premiere, orden, editorial | **festival** | siempre del festival; el catálogo no los toca |

En el onboarding, el festival hereda del catálogo lo agnóstico que no especifique. Si el festival **sí** especifica y **difiere**, el guard lo marca: o es un error (gana el catálogo) o es legítimo (corte distinto → override explícito + se anota en `provenance`).

## 7. Flujo de onboarding (dónde se engancha)

Extiende `docs/PIPELINE.md` (no lo reescribe):

1. **Fase 1 (extracción)** — igual que hoy.
2. **Fase 2 (enriquecimiento)** — `enrich-festival.py` trae TMDB id → **nuevo paso: resolver contra el catálogo.** Match → pre-llena; no-match → marca candidato nuevo.
3. **Fase 4 (validación)** — el **guard de consistencia** (§8) corre aquí: conflictos catálogo↔festival fallan el gate.
4. **Post-merge** — los registros nuevos/actualizados se promueven al catálogo (con `provenance`).

## 8. Guard de consistencia (automatiza al Data Steward)

`scripts/audit-catalog.py <festival-id>` — read-only, corre en onboarding + CI:

- **CONFLICTO (error):** el festival matchea una entrada del catálogo pero difiere en año / duración / director sin override explícito. → Juan arbitra; el catálogo es el árbitro.
- **REUSO (warning):** el catálogo tiene póster o sinopsis que el festival no trae → sugerencia de heredar.
- **NUEVO (info):** film sin entrada en el catálogo → candidato a promover.
- **DRIFT (warning):** dos festivales (vía el catálogo) con datos incompatibles → lo que hoy te preocupa, ahora **imposible de introducir en silencio**.

## 9. Siembra (seeding) — oportunista, no limpieza

El catálogo arranca casi vacío y **crece con cada onboarding**. Para que el próximo festival se beneficie ya:

- **Cosecha** los registros ricos que existen (Olhar/Tribeca/Ficmontañas tienen data buena) hacia el catálogo, **eligiendo el valor correcto cuando hay conflicto** (Piedras = 2026, criterio de Juan).
- Esto **NO toca los JSON viejos** — solo extrae lo bueno hacia el catálogo. Es harvest, no migración.
- Alcance de la siembra inicial: los **13 cruces** + los films de los festivales **activos/próximos** (Ficmontañas) — no los 807.

## 10. Fases

| Fase | Entregable | Riesgo |
|---|---|---|
| **0** | Este RFC + aprobación | — |
| **1** | Esquema `catalog/films.json` + resolver (TMDB id) + `audit-catalog.py` (read-only) | bajo (no toca app ni JSONs) |
| **2** | Wire al pipeline (`enrich` consulta, guard en Fase 4); siembra de los 13 cruces + Ficmontañas | medio (proceso de onboarding) |
| **3** *(opcional, futuro)* | Backfill puntual de un festival activo si Juan lo pide | acotado — **fuera de alcance ahora** |

## 11. Riesgos y mitigaciones

- **Falso merge (entidad)** → TMDB id primario; slugs confirmados a mano; default no-fusionar; señales de apoyo (dir+dur+país). El guard surfacea, no auto-resuelve.
- **Drift del catálogo** → el guard de consistencia + `provenance`.
- **Scope creep** → forward-only + fases; la siembra se acota a 13 cruces + activos, no a los 807.
- **Sobre-ingeniería** → a este scale, **un archivo JSON + un resolver + un guard**, sin DB ni runtime. Se re-evalúa si los cruces escalan a decenas (más festivales).

## 12. No-objetivos (explícitos)

- ❌ Reescribir/limpiar los 7 festivales existentes.
- ❌ Base de datos o join en runtime; cambiar la app o el planner.
- ❌ Auto-fusión por título.
- ❌ Resolver la deuda histórica de datos. Esto es **prevención forward**, no remediación.

## 13. Decisiones que necesito de Juan

1. **Films sin TMDB** (muchos cortos): ¿entran al catálogo con `slug:` confirmado a mano, o el catálogo cubre **solo** películas con TMDB id (y los cortos sin TMDB se quedan self-contained por festival)?
2. **Override legítimo** (corte restaurado, otra duración): ¿se permite override por-festival flaggeado, o el catálogo **siempre** gana?
3. **Siembra inicial:** ¿cosechamos ya los 13 cruces + Ficmontañas, o arranca vacío y solo crece con onboardings nuevos?
4. **Ubicación:** `catalog/films.json` único (suficiente a este scale) — confirmar.

---

> Aprobado esto, Fase 1 es el esquema + resolver + guard read-only: cero riesgo, valor inmediato (el guard ya te lista divergencias), y siembra el catálogo madre. Construir = Data Engineer (Claude); el guard reemplaza el 90% del trabajo manual de Data Steward.
