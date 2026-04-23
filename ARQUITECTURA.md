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
