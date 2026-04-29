# OTROFESTIV — Documento de Arquitectura
> Referencia canónica para implementación. Leer antes de tocar código.
> Última actualización: ABR 2026 · `index.html` @ commit `567f216`

---

## 1. ESTRUCTURA DE ARCHIVOS

```
/
├── index.html              ← App completa (8 000+ líneas, single-file)
├── sw.js                   ← Service Worker (cacheo, versión con BUILD)
├── manifest.json           ← PWA manifest
├── festivals/
│   ├── aff-2026.json       ← Datos AFF 2026
│   └── ficci-65.json       ← Datos FICCI 65
└── fonts/                  ← Plus Jakarta Sans (400–800)
```

Los datos de cada festival viven en su propio JSON, **no** en `index.html`. Se cargan en `loadFestival(id)` la primera vez y se cachean en `FESTIVAL_CONFIG[id].films`.

---

## 2. DESIGN TOKENS

### Superficies (oscuro, siempre)
| Token | Valor | Uso |
|---|---|---|
| `--bg` | `#0A0A0A` | Fondo de página |
| `--surf` | `#141414` | Superficie principal (headers, navs) |
| `--surf-2` | `#1A1A1A` | Hover, estados activos |
| `--surf-3` | `#1F1F1F` | Placeholder de pósters |
| `--card-a` | `#1E1E1E` | Cards principales |
| `--card-b` | `#232323` | Cards secundarias |
| `--card-p` | `#141414` | Cards en panel |

### Bordes
| Token | Valor | Uso |
|---|---|---|
| `--bdr` | `#2A2A2A` | Chrome estructural (navs, headers) |
| `--bdr-l` | `#1E1E1E` | Separación de contenido (ítems de lista) |

### Color
| Token | Valor | Uso |
|---|---|---|
| `--amber` | `#F59E0B` | CTA primario, badges, acentos |
| `--amber-d` | `#D97706` | Hover de amber |
| `--amber-08…60` | rgba | Fondos tenues, bordes amber |
| `--green` | `#3AAA6E` | Confirmación, "en curso", nueva fecha |
| `--red` | `#E05252` | Error, conflicto |
| `--yellow` | `#E5A020` | Advertencia |
| `--white` | `#F0EDE8` | Texto principal |
| `--gray` | `#888888` | Texto secundario |
| `--gray2` | `#555555` | Texto terciario / deshabilitado |
| `--black` | `#000000` | Texto sobre fondo amber |

### Tipografía
| Token | Valor |
|---|---|
| `--font` | `'Plus Jakarta Sans', sans-serif` |
| `--t-badge` | `8px` |
| `--t-xs` | `9px` |
| `--t-label` | `10px` |
| `--t-sm` | `11px` |
| `--t-caption` | `12px` |
| `--t-base` | `13px` ← body estándar |
| `--t-md` | `16px` |
| `--t-lg` | `20px` |
| `--t-display` | `30px` |
| `--t-icon` | `15px` |

### Pesos
| Token | Valor | Uso |
|---|---|---|
| `--w-thin` | `400` | Raramente usado |
| `--w-regular` | `500` | Body normal |
| `--w-semi` | `600` | Énfasis suave |
| `--w-bold` | `700` | Títulos, labels |
| `--w-display` | `800` | Display, badges |

### Espaciado
| Token | px | Uso |
|---|---|---|
| `--sp-1` | `4px` | Micro-gaps |
| `--sp-2` | `8px` | Gaps entre elementos |
| `--sp-3` | `12px` | Padding componentes pequeños |
| `--sp-4` | `16px` | Padding componentes medianos |
| `--sp-5` | `24px` | Padding secciones |
| `--sp-6` | `32px` | Separación entre secciones |
| `--sp-btn` | `14px` | Padding vertical botones |

### Radios
| Token | Valor | Uso |
|---|---|---|
| `--r-sm` | `4px` | Pósters, chips pequeños |
| `--r-md` | `8px` | Badges, botones |
| `--r` | `11px` | Cards |
| `--r-sheet` | `20px` | Bottom sheets |
| `--r-pill` | `999px` | Pills |

### Pósters (ratio 2:3)
| Token | Dimensiones | Uso |
|---|---|---|
| `--poster-xs` | `40×60px` | Lista Mi Plan, Planear, Sugerencias |
| `--poster-md` | `72×108px` | Prio strip |
| `--poster-lg` | `96×144px` | Cards de descubrimiento, sheet |

---

## 3. ESTRUCTURA DE DATOS

### Film object (en `films[]` del JSON de festival)
```json
{
  "title": "Belén",
  "title_en": "Belén",
  "country": "Argentina",
  "flags": "🇦🇷",
  "duration": "108 min",
  "day": "MAR 21",
  "date": 21,
  "time": "18:00",
  "venue": "MAMM",
  "section": "🏆 Competencia de Largometrajes",
  "day_order": 0,
  "is_cortos": false,
  "film_list": [],
  "director": "Dolores Fonzi",
  "year": 2025,
  "genre": "Drama",
  "synopsis": "..."
}
```
> `day_order`: índice del día (0 = primer día del festival). `is_cortos`: true si es programa de cortos. `type: 'event'`: talleres/industry days.

### Festival JSON (estructura completa)
```json
{
  "id": "aff2026",
  "name": "Alternativa Film Festival",
  "shortName": "AFF 2026",
  "city": "Medellín",
  "dates": "21–29 ABR",
  "storageKey": "aff2026_",
  "festivalEndStr": "2026-04-30T02:00:00",
  "festivalDates": { "MAR 21": "2026-04-21", ... },
  "days": [{ "k": "MAR 21", "lbl": "MAR", "d": 21 }, ...],
  "dayKeys": ["MAR 21", "MIÉ 22", ...],
  "dayShort": { "MAR 21": "MAR 21", ... },
  "dayLong": { "MAR 21": "Martes 21", ... },
  "prioLimit": 5,
  "festivalPosterUrl": "...",
  "films": [...],
  "posters": { "Título": "https://image.tmdb.org/..." },
  "customPosters": { "Título": "url-custom" },
  "lbSlugs": { "Título": "slug-en-letterboxd" }
}
```

### NOTICES (en `index.html`, editable directamente)
```js
const NOTICES = [
  { title: 'Un mundo frágil y maravilloso', festival: 'aff2026', type: 'cancelled' },
  // type: 'rescheduled' → añadir: newDay, newTime, newVenue
];
```

### Globals en runtime (swapeados por `loadFestival()`)
```
FILMS[]         ← array activo de funciones
POSTERS{}       ← title → URL de poster
LB_SLUGS{}      ← title → slug de Letterboxd
FESTIVAL_DATES  ← { "DÍA KEY": "YYYY-MM-DD" }
FESTIVAL_END    ← Date object
FESTIVAL_STORAGE_KEY ← prefijo para localStorage
DAY_KEYS[]      ← orden canónico de días
```

---

## 4. COMPONENTES CSS

### Badges (inline en texto o título)
| Clase | Descripción | Estilo |
|---|---|---|
| `.apertura-badge` | Evento especial / apertura | Fondo amber sólido, texto white, `--t-xs`, `--r-md` |
| `.past-badge` | Función pasada | Solo texto `--gray2` |
| `.notice-badge` | Cancelada / reprogramada | Fondo amber sólido, texto `#0A0A0A`, `--w-display` |
| `.poster-past-badge` | Sobre póster en grid | Overlay oscuro, texto gray |

> **Regla:** Todo badge nuevo → extender este sistema. Nunca estilos inline ad-hoc.

### Banner global (descartable)
```
.notice-banner          ← contenedor flex, surf-2, bdr-l bottom
.notice-banner-dot      ← círculo 6px amber
.notice-banner-body     ← flex:1
.notice-banner-label    ← "AVISO DEL FESTIVAL" en amber, t-xs, w-display
.notice-banner-text     ← t-sm, white; <span> para texto gris
.notice-banner-close    ← botón ✕ gray2
```

### Cards de lista (plist — vista Hoy/Mañana y Explorar)
```
.plist-item             ← flex, gap sp-3, padding sp-3, bdr-l bottom
.plist-poster           ← 32×48px, r-sm, surf-3 como placeholder
.plist-info             ← flex:1, min-width:0
.plist-title            ← t-base, w-bold, white — contiene badges inline
.plist-meta             ← t-sm, gray — venue · sala · duración
.plist-sec              ← t-label, gray2 — sección
.plist-heart            ← ícono corazón amber (watchlist toggle)
.plist-event            ← variante para eventos/industry days
```

### Bottom Sheet
```
.sheet-overlay          ← overlay oscuro (overlay-60)
.sheet / .av-sheet      ← panel blanco desde abajo, r-sheet arriba
.sheet-handle           ← handle drag (r-handle)
```
Abierta con `openXxxSheet()`, cerrada con `closeXxxSheet()`. El overlay llama al close si se toca fuera.

### Toast
```js
showToast(msg, type='info', duration=2800)  // type: info | warn | error
showActionToast(msg, label, fn, duration)   // con botón de acción
```

### Modales de confirmación
```js
showDestructiveModal(title, body, label, cb)  // acción destructiva (rojo)
showActionModal(title, body, label, cb, cancelLabel)  // acción neutra
showConflictModal(conflicts, onConfirm)  // conflicto de horario
```

---

## 5. MAPA DE FUNCIONES DE RENDER

### Mi Plan (tab)
| Función | Qué hace |
|---|---|
| `renderAgenda()` | Orquestador principal — llama a los sub-renders |
| `renderContextualHeader()` | Panel de fase (próxima función, entre funciones, etc.) |
| `renderNextStrip(schedule)` | Tira de próxima función con countdown |
| `renderUnconfirmed(schedule)` | Check-ins pendientes de funciones pasadas |
| `renderSavedAgendaHTML()` | Agenda guardada completa |
| `_renderSavedAgendaHTML()` | Implementación interna |
| `renderMiPlanList(schedule)` | Vista lista compacta |
| `renderMiPlanCalendar()` | Vista calendario |

### Selección (tab)
| Función | Qué hace |
|---|---|
| `renderFilmListHTML()` | Grid de watchlist |
| `renderPrioStrip()` | Strip de películas priorizadas |
| `renderFlowProgress(tab)` | Stepper ① INTERESES → ② PLANEAR → ③ MI PLAN |

### Programa / Cartelera (tab)
| Función | Qué hace |
|---|---|
| `_renderProgramaContent()` | Orquestador — decide qué sub-render usar |
| `renderProgramaList()` | Lista cronológica Hoy/Mañana |
| `_renderExploreLista()` | Lista catálogo completo (Explorar) |
| `renderPeliculaView()` | Grid por película |
| `render()` | Grid por horario |
| `renderVbar()` | Filtro de venue |
| `renderSbar()` | Filtro de sección |
| `renderProgramaChips()` | Chips de categoría (Explorar) |
| `renderNoticesBanner()` | Banner de avisos (cancelaciones) |

### Planear (tab)
| Función | Qué hace |
|---|---|
| `renderSimPanel()` | Panel de escenarios calculados |
| `renderGapOptions()` | Sugerencias para huecos en el plan |
| `renderFilmAlternatives()` | Alternativas para una función específica |

---

## 6. FLUJO DE DATOS

```
PDF del festival
      ↓
Enriquecimiento manual (director, año, país, Letterboxd slug, TMDB poster)
      ↓
festivals/[id].json  (films[], posters{}, lbSlugs{})
      ↓
loadFestival(id)  →  swapea globals FILMS, POSTERS, LB_SLUGS, etc.
      ↓
render functions  →  DOM
```

### Posters — cadena de prioridad
```js
getFilmPoster(f)       // para cualquier film completo
getCortoItemPoster(item) // para cortos individuales en film_list
```
Nunca llamar `getPosterSrc()`, `makeProgramPoster()` o `makeEventPoster()` directamente en templates.

Prioridad interna:
1. `CUSTOM_POSTERS[title]` (override manual)
2. `POSTERS[title]` (TMDB o URL directa)
3. Poster generativo (solo si `is_cortos` o `type === 'event'`)
4. `null` → no render (nunca fondo negro, usar `--surf-2`)

### Letterboxd URL
```js
`https://letterboxd.com/film/${LB_SLUGS[title]}/`
```

---

## 7. STATE & STORAGE

### Claves de localStorage (prefijadas por festival)
```
{key}_wl        ← watchlist (Set de títulos)
{key}_watched   ← películas vistas
{key}_av3       ← bloques de no-disponibilidad por día
{key}_saved     ← agenda guardada { schedule: [...] }
{key}_prio      ← set de priorizadas
{key}_lastslot  ← array de últimos slots removidos (hasta 5)
```
El prefijo `{key}` viene de `FESTIVAL_STORAGE_KEY` (e.g. `aff2026_`).

### Funciones de estado
```js
loadState()   // carga desde localStorage al iniciar / cambiar festival
saveState()   // escribe a localStorage (con debounce interno)
```

---

## 8. CONFLICTOS DE HORARIO

Siempre usar `screensConflict(a, b)` — incluye buffer de ±10 min.  
**Nunca** ad-hoc con comparaciones de minutos directas.

---

## 9. REGLAS DE DISEÑO (no negociables)

1. **CTA primario**: fondo amber sólido (`--amber`), texto negro (`#0A0A0A` o `--black`).
2. **Badges**: clases existentes. Nunca inline ad-hoc.
3. **Nuevo componente**: reutilizar tokens y clases antes de crear nuevos.
4. **Tipografía**: verificar escala de tokens antes de aplicar `font-size`.
5. **Iconografía**: solo Lucide pack para íconos de venue/tiempo. Flags de países y emojis de categoría son la única excepción permitida.
6. **Conflictos**: siempre `screensConflict()`.
7. **Pósters**: siempre `getFilmPoster()` o `getCortoItemPoster()`. Nunca `onerror` con fondo negro — usar `this.remove()` o placeholder `--surf-2`.
8. **Cards** — 4 tipos canónicos:
   - Película: poster + flags + título + dur + sección, funciones + dir + sinopsis + Letterboxd, CTAs
   - Programa de cortos: igual + lista de cortos, sin Letterboxd
   - Corto individual (`openCortoSheet`): igual, solo Intereses + Calificar
   - Evento/taller: sin flags, horario + descripción, sin Letterboxd

---

## 10. AGREGAR UN FESTIVAL NUEVO

1. Crear `festivals/[id].json` con la estructura completa
2. Agregar entrada en `FESTIVAL_CONFIG` en `index.html`
3. Agregar opción en el splash dropdown y en `fs-sheet`
4. `loadFestival('[id]')` ya maneja el resto

Para avisos de ese festival: agregar entrada en `NOTICES[]` con `festival: '[id]'`.

---

## 11. TIPOS DE FUNCIÓN — REFERENCIA CANÓNICA

Cinco tipos de objeto en `films[]`. El render los detecta automáticamente.

### 1. Largometraje individual
```json
{
  "title": "Eureka",
  "director": "Lisandro Alonso",
  "duration": "147 min",
  "day": "VIE 12", "date": 12, "time": "17:00",
  "venue": "Biblioteca Juan Carlos Montoya - Sabaneta",
  "section": "Proyecciones especiales",
  "flags": "🇦🇷", "year": 2023
}
```

### 2. Largometraje con múltiples funciones (formato nuevo — recomendado)
`loadFestival()` explota `screenings[]` en objetos planos. Sin duplicar metadatos.
```json
{
  "title": "Eureka",
  "director": "Lisandro Alonso",
  "duration": "147 min",
  "section": "Proyecciones especiales",
  "flags": "🇦🇷", "year": 2023,
  "screenings": [
    {"day": "VIE 12", "date": 12, "time": "17:00", "venue": "Biblioteca Juan Carlos Montoya - Sabaneta"},
    {"day": "SÁB 13", "date": 13, "time": "19:00", "venue": "Teatro Baggenuff II - Copacabana"},
    {"day": "MAR 16", "date": 16, "time": "19:00", "venue": "Teatro Caribe - Itagüí"}
  ]
}
```

### 3. Programa de cortos
```json
{
  "title": "Competencia de Cortometrajes · Programa 1",
  "is_cortos": true,
  "duration": "82 min",
  "day": "SÁB 13", "date": 13, "time": "17:00",
  "venue": "La Capilla del Claustro Comfama - Medellín",
  "film_list": [
    {"title": "Jirapo", "director": "María Rojas Arias", "duration": "20 min", "country": "Colombia"},
    {"title": "Kilómetro 126", "director": "Felipe López Gómez", "duration": "17 min", "country": "Colombia"}
  ]
}
```

### 4. Programa combinado de largometrajes
Dos o más largos en un solo slot. Bloque indivisible. Poster: stack offset del primer y segundo film.
`duration` se calcula automáticamente si no viene explícita.
```json
{
  "title": "Portales + Las muchas muertes de Antônio Parreiras",
  "is_programa": true,
  "day": "VIE 12", "date": 12, "time": "18:30",
  "venue": "Cine MAMM - Medellín",
  "section": "Competencia central",
  "film_list": [
    {"title": "Portales", "duration": "16 min"},
    {"title": "As Muitas Mortes de Antônio Parreiras", "duration": "65 min"}
  ]
}
```

### 5. Evento / taller / conversatorio
```json
{
  "title": "Laboratorio internacional de sonido cinematográfico",
  "type": "event",
  "duration": "120 min",
  "day": "LUN 15", "date": 15, "time": "09:00",
  "venue": "Estudio Archipiélago Sonoro - Medellín",
  "section": "Programación académica"
}
```

### Venue — formato para festivales multi-sede
`"[Nombre sala] - [Municipio]"` → funciona con el filtro de Lugar existente sin cambios.
Ejemplo: `"Teatro Otraparte - Envigado"`, `"Cinemas Procinal Las Américas - Medellín"`

---

## 12. METADATA ESPECIAL DE FUNCIONES

Campos opcionales que modifican comportamiento y UI. Aplican a cualquier tipo de función.

### `has_qa: true` — Equipo presente / Q&A
```json
{
  "title": "Andariega",
  "has_qa": true,
  ...
}
```
**Comportamiento:**
- El algoritmo de conflictos suma +30 min a `duration` al calcular solapamientos
- Badge ámbar en card de lista (igual al sistema de notices)
- Banner en sheet de detalle: "EQUIPO PRESENTE · +30 min estimados"
- En Mi Plan: aviso junto a la función agendada

**Lógica de duración efectiva:**
```js
function effectiveDuration(f) {
  const base = parseInt(f.duration) || 90;
  return f.has_qa ? base + 30 : base;
}
```
Usar `effectiveDuration(f)` en `screensConflict` en lugar de `f.duration` directamente.

### `requires_registration: true` — Inscripción previa
```json
{
  "title": "Foro de la crítica · Sesión 1",
  "type": "event",
  "requires_registration": true,
  ...
}
```
**Comportamiento:**
- Badge informativo en card de lista
- Banner en sheet de detalle: "INSCRIPCIÓN PREVIA"
- No bloquea agendar — el usuario decide
- No afecta el algoritmo de conflictos

### Identidad visual de badges especiales
Ambos siguen el mismo sistema que `.notice-badge`:
- Fondo ámbar sólido (`var(--amber)`)
- Texto negro (`#0A0A0A`)
- `font-size: var(--t-xs)`, `font-weight: var(--w-display)`
- `border-radius: var(--r-md)`
- Misma posición en card: inline antes del título

### Ejemplo completo con ambos campos
```json
{
  "title": "Cartas a mis padres muertos",
  "director": "Ignacio Agüero",
  "duration": "106 min",
  "has_qa": true,
  "section": "Proyecciones especiales",
  "screenings": [
    {"day": "MIÉ 17", "date": 17, "time": "17:00", "venue": "La Capilla del Claustro Comfama - Medellín"}
  ]
}
```

---

## 13. SISTEMA GLOBAL DE SEDES (VENUES)

Las sedes de cada festival se definen en `festivals/*.json` bajo la clave `venues{}`.
El código las carga en `_FEST_VENUES` al iniciar el festival y las usa para:
- Mostrar el nombre corto de la sede en cards y Mi Plan
- Calcular tiempos de viaje entre sedes para `travelWarn()`
- Detectar conflictos de desplazamiento en `screensConflict()`

### Estructura en el JSON del festival
```json
{
  "venues": {
    "MAMM": {
      "short": "MAMM",
      "lat": 6.2338,
      "lon": -75.5733,
      "city": "Medellín",
      "address": "Carrera 44 #19A-100, Ciudad del Río"
    },
    "Cineprox Las Américas": {
      "short": "Cineprox",
      "lat": 6.2504,
      "lon": -75.5800,
      "city": "Medellín",
      "address": "Diagonal 75B #2A-120"
    }
  }
}
```

### Resolución de venue (_resolveVenue)
1. Búsqueda exacta en `_FEST_VENUES` (JSON del festival)
2. Búsqueda parcial en `_FEST_VENUES` (por si el string incluye sala: "MAMM · Sala 1")
3. Fallback estático en `VENUES` (cubre FICCI 65 sin JSON de venues)
4. Si nada coincide: `{short: primer segmento del string de venue}`

### Escala de tiempos de viaje (venueTravelMins)
| Distancia | Tiempo estimado | Contexto |
|---|---|---|
| < 150 m | 0 min | Misma sede / sala contigua |
| < 400 m | 8 min | A pie |
| < 1 km | 12 min | A pie rápido o transporte corto |
| < 2.5 km | 18 min | Uber / Metro |
| < 5 km | 25 min | Uber con tráfico |
| ≥ 5 km | 35 min | Trayecto largo |

### Modo de transporte — campo `transport`
Define el modo de movilización predominante del festival.
Vive en el JSON del festival. El código no requiere cambio para nuevos festivales.

```json
{ "transport": "walking" }   // Festival compacto — Jardín, campus, pueblo
{ "transport": "transit" }   // Festival en ciudad — Medellín, Cartagena (default)
```

| Distancia | walking | transit |
|---|---|---|
| < 100 m | 0 min | 0 min |
| < 350 m | 5 min | 8 min |
| < 800 m | 10 min | 12 min |
| < 1.5 km | 20 min | 18 min |
| < 3 km | 35 min | 25 min |
| ≥ 3 km | 50 min | 35 min |

El aviso en Mi Plan dice "a pie" o "en carro" según el modo.

### Para agregar un festival nuevo
Solo definir `venues{}` y `transport` en el JSON.
El código no requiere ningún cambio.

### Cambios de sede (notices)
Cuando un film tiene `notice.type === 'rescheduled'` con `newVenue`,
`_effectiveVenue()` devuelve la nueva sede para el cálculo de distancias.
El sistema refleja automáticamente el cambio en `travelWarn()`.
