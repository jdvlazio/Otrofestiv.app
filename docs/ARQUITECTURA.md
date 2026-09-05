# OTROFESTIV — Documento de Arquitectura
> Referencia canónica para implementación. Leer antes de tocar código.
> Última actualización: JUL 2026 · app modular ESM en `src/` (Fase 8 completada) · `index.html` = shell
> · MVC migrado; invariantes de capas y estado protegidos por fitness functions (§15.4)

---

## 1. ESTRUCTURA DE ARCHIVOS

```
/
├── index.html                  ← Shell HTML: <head> + skeleton + carga `src/main.js` como módulo ESM
├── sw.js                       ← Service Worker (CACHE_NAME/BUILD stampeado por bump-version.js)
├── manifest.json               ← PWA manifest
├── version.json                ← Build timestamp (android+ios) — sincronizado por bump-version.js
│   Los 4 canales que lo leen (cold start, visibilitychange, online, poll de
│   10 min con toast) viven en src/main.js FUERA del guard de service worker:
│   el wrapper iOS (WKWebView sin WKAppBoundDomains) no tiene esa API, y con
│   los canales presos del guard quedaba sin ningún mecanismo de update
│   (bug del 24 ago 2026). Guardián: [update-canales-sin-sw] + test T102.
│   CAPA 2 — datos en caliente (live-refresh.js): en los mismos ticks, el
│   catálogo del festival activo se re-fetchea y aplica SIN recargar, por
│   tres reglas (aprobadas con respaldo — web.dev CLS, NN/g, pill de X):
│   valores → en silencio; estructura visible → se OFRECE (pill), calendario
│   siempre; cambios de TU plan → aviso con el hecho (T97). Dueños únicos
│   compartidos con loadFestival: _ingerirDatosFestival + publicarCatalogo;
│   el árbitro es domain/refresh-diff.js (puro). Tests: T103/T104 + unit.
│   La HUELLA del refresco (_rawHash) y la copia cruda (_rawFilms) se toman AL
│   ENTRAR a la ingesta: explodeScreenings devuelve los MISMOS objetos que
│   data.films, así que duraciones, sealSharedSlots y NOTICES mutan el JSON
│   bajado — tomarla al final la dejaba distinta de la de un fetch fresco y el
│   refresco veía un cambio en cada tick (los pósters titilaban; 4 de 17
│   festivales). Guardián: [refresco-huella-cruda] + tests/unit/refreshHuella.
├── src/                        ← App modular ESM (Fase 8). Mapa detallado de módulos en §16.2
│   ├── main.js                 ← Bootstrap + STATE/VIEWSTATE bridge + ACTION_REGISTRY; importa el resto
│   ├── config.js               ← FESTIVAL_CONFIG · VENUES · NOTICES · taxonomía/colores de sección + mergeFestivalSections()
│   ├── telemetry.js            ← report(err, ctx) → Sentry (captura no bloqueante)
│   ├── lru.js                  ← lruTouch() — decisión PURA del LRU del cache de festivales (§8.3)
│   ├── i18n/i18n.js            ← Bloque _I18N (es/en/pt) — FUENTE DE VERDAD de strings (la lee t())
│   ├── domain/                 ← Funciones puras: time · film · schedule · festival · conflict · venues · delays
│   ├── controller/             ← Handlers, pipeline, persistence, festival, sheets, calc, loader, delays-cloud
│   ├── view/                   ← Render puro: agenda · programa · components · helpers
│   ├── state/                  ← state container + viewstate (bridge) + festival-context (§8.1)
│   └── storage/                ← adapter de localStorage
├── festivals/                  ← Un JSON por festival (films[] con poster/lbSlug inline)
│   ├── ficci-65 · aff-2026 · cinemancia-2025      ← archivados / test
│   └── leviza-2026 · olhar-2026 · tribeca-2026    ← recientes (Tribeca activo)
├── scripts/                    ← Pipeline CLI — secuencia canónica en docs/PIPELINE.md §0
│   ├── csv-to-festival.js · enrich-festival.py · translate-synopsis.py
│   ├── generate-config.js · validate-festivals.js · geocode-venues.py
│   └── bump-version.js · generate-claude-md.js · normalize-festival-titles.py
├── tests/                      ← Playwright (*.spec.js) + unit (node:test sobre domain/) + helpers
├── docs/                       ← ARQUITECTURA · PIPELINE · SCHEMA · FESTIVAL-CHECKLIST · DESIGN
├── pipeline/                   ← PROTOCOLO.md + templates (festival-template.json, csv-template.csv)
├── tools/                      ← enricher.html · smoke-test.html · audit.sh
└── assets/                     ← proyeccion-sorpresa.svg + assets por festival
```

Los datos de cada festival viven en su propio JSON, **no** en `index.html`. Se cargan en `loadFestival(id)` la primera vez y se cachean en `FESTIVAL_CONFIG[id].films`.

> **i18n — fuente de verdad:** `src/i18n/i18n.js` (bloque `_I18N`, es+en+pt) — es lo que lee `t()` y lo que valida `validate.py`. Los `i18n/*.json` legacy de la raíz fueron **eliminados** (17 jul 2026).
>
> **Nota:** las secciones 1–15 documentan el código actual (modular ESM); la §16 documenta el modelo MVC y su roadmap (Fases 1–8, ya completadas).

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

### Transiciones
| Token | Valor | Uso |
|---|---|---|
| `--tr-fast` | `100ms ease` | Feedback inmediato: hover color |
| `--tr-base` | `150ms ease` | Micro-interacción: botones, badges |
| `--tr-smooth` | `200ms ease` | Overlays, opacidades, estados |
| `--tr-enter` | `300ms ease-out` | Entradas al DOM: paneles, drawers |

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

> **Formato nuevo (desde Jardín 2026):** `poster` y `lbSlug` van dentro de cada objeto film.
> No crear `posters{}` ni `lbSlugs{}` al nivel raíz — eso es formato legado (FICCI, Cinemancia).

```json
{
  "config": { ... },
  "venues": { "Sala - Ciudad": { "short": "...", "lat": 0, "lng": 0, "city": "..." } },
  "customPosters": { "Título": "url-override" },
  "films": [...],
  "transport": "transit"
}
```

La configuración del festival tiene **un solo dueño por tipo de dato** (17 jul 2026, loader.js):
- **Identidad** (`name/shortName/city/dates/dates_en/year/timezoneOffset/festivalDates`): dueño = `FESTIVAL_CONFIG` (src/config.js). El JSON solo rellena huecos legacy, **nunca pisa** un valor de config. Gate: `validate.py [festival-name-parity]`.
- **Contenido** (films, days, sections, venues, ticketing…): dueño = el JSON del festival.
- `FESTIVAL_CONFIG` en `src/config.js` — para carga inicial antes del fetch del JSON
- `config{}` dentro del JSON del festival — generado por `generate-config.js`

Ambas fuentes deben estar sincronizadas. Usar `generate-config.js` para producir la entrada de `FESTIVAL_CONFIG`. **No editar ninguna de las dos a mano.**

### NOTICES (en `index.html`, editable directamente)
```js
const NOTICES = [
  { title: 'Un mundo frágil y maravilloso', festival: 'aff2026', type: 'cancelled' },
  // type: 'rescheduled' → añadir: newDay, newTime, newVenue
];
```

### Globals en runtime (swapeados por `loadFestival()`)
```
FILMS[]              ← array activo de funciones
POSTERS{}            ← title → URL de poster (formato legado)
LB_SLUGS{}           ← title → slug de Letterboxd
FESTIVAL_DATES       ← { "DÍA KEY": "YYYY-MM-DD" }
FESTIVAL_END         ← Date object
FESTIVAL_STORAGE_KEY ← prefijo para localStorage
DAY_KEYS[]           ← orden canónico de días (ej: ["MAR 21", "MIÉ 22"])
DAY_SHORT{}          ← { "MAR 21": "MAR 21" } — label corto para chips de día
DAY_LONG{}           ← { "MAR 21": "Martes 21" } — label largo para headers
TZ_OFFSET            ← offset de timezone del festival (ej: "-05:00", "-04:00")
FESTIVAL_TRANSPORT   ← modo de transporte: "walking" | "transit" | "mixed"
```

---

## 4. SISTEMA i18n

La app soporta español (ES) e inglés (EN). El idioma activo se persiste en `localStorage('otrofestiv_lang')`.

### Funciones principales
```js
t('key')           // devuelve el string en el idioma activo; fallback a ES si no existe EN
setLang('en')      // cambia idioma in-place — muta _lang, actualiza DOM, re-renderiza vista activa
_applyI18nDOM()    // parchea elementos del DOM estático (nav labels, filtros, etc.)
```

### Archivos de strings
```
src/i18n/i18n.js  ← FUENTE ÚNICA: bloque _I18N (es+en) — lo que lee t() y valida
                    validate.py [i18n-complete]/[i18n-parity]
```
> Los `i18n/*.json` legacy (es/en/strings-reference) fueron ELIMINADOS (17 jul
> 2026): llevaban meses desincronizados y no se consumían en runtime — solo
> invitaban a editar el archivo equivocado.

### Cómo conectar un string nuevo
1. Verificar que la key existe en `es.json` y `en.json`
2. Si es en un **template JS** (backtick): reemplazar con `t('key')`
3. Si es en **HTML estático con ID**: añadir a los `ids{}` en `_applyI18nDOM()`
4. Si es en **HTML estático sin ID**: añadir `data-i18n="key"` al elemento
5. **Nunca** añadir `data-i18n` a elementos `<script>` o `<style>` — `_applyI18nDOM` tiene guard, pero la regla es no hacerlo en primer lugar

### Regla de proceso — inamovible
**Toda decisión de traducción** (nueva key, corrección, ajuste de copy EN o ES) requiere discusión semántica y sintáctica con **Content Designer y UX Writer** antes de entrar al código. Sin excepción.

---

## 5. COMPONENTES CSS

### Encabezados de sección y cejas (consolidación jul 2026)
Dos componentes canónicos reemplazan las ~20 clases ad-hoc de encabezados
(`int-section-hdr`, `pel-sheet-section-lbl`, `fs-section-lbl`, `diary-prog-lbl`,
`archive-out-lbl`, `pv/conflict/prio-limit/ag-excl-eyebrow` — todas retiradas):

| Clase | Rol | Anatomía |
|---|---|---|
| `.sec-hdr` | **Encabezado de sección** — abre una lista de ítems | **Estilo C (17 jul 2026)**: BANDA sólida full-bleed (surf-2 sobre página; card-b dentro de sheets/cards) + icono Lucide ámbar + label + badge opcional. Variante `.sm`: uppercase `--t-xs`. Slot `.hdr-end` (margin-left:auto) para controles. Los DÍAS y HORAS (saved-day-lbl, bandas de horario) van sin banda de sec-hdr: jerarquía posicional propia. |
| `.ctx-eyebrow` | **Ceja** — corona un bloque/sheet con contexto | Icono pequeño + label uppercase, sin barra. Color por contexto vía scope del padre (`.pv-header`, `.conflict-hdr`, `.prio-limit-hdr`). |

**Regla de uso:** ¿abre una lista? → `sec-hdr`. ¿Corona un bloque/sheet? → `ctx-eyebrow`.

**El contrato de `sec-hdr` con su contenedor (24 ago 2026).** El full-bleed no es
magia: se consigue con `margin-left/right: calc(-1*var(--sp-4))` para romper el
padding del contenedor, repuesto como `padding: var(--sp-2) var(--sp-4)` propio.
De ahí sale un requisito que hay que cumplir al usarlo:

> **El contenedor de un `sec-hdr` DEBE aportar `var(--sp-4)` de padding lateral**
> —él mismo o un ancestro—. Sin eso los márgenes negativos no compensan nada:
> solo empujan la banda fuera del viewport.

Y su corolario: si el contenedor da ese padding, **la tira o lista hermana NO
debe repetirlo** (`padding: var(--sp-2) 0 var(--sp-1)`), o queda a 32px y se
desalinea del icono de la banda.

Lo pagó el palmarés: nació el 23 ago con un punto de inserción nuevo
—`#palmares-slot`, un div sin una sola regla de CSS colgado del `body`— y su
banda medía **422px en un viewport de 390**, con el icono cortado contra el
borde. Los otros 23 `sec-hdr` de la app nunca lo notaron porque heredaron
contextos que ya cumplían (`.poster-grid`, sheets, `.ag-summary`): cumplían la
regla por copiar un sitio que funcionaba, no por conocerla.

Al crear un contenedor NUEVO para un `sec-hdr`, medir. La comprobación son tres
números en el navegador a 390px: la banda ocupa exactamente el ancho del
viewport, el icono queda a 16px del borde, y `scrollWidth` no crece.

**Cero divisores sueltos (decisión Juan, jul 2026):** la separación de secciones
la hace la BANDA del `sec-hdr` (estilo C — reemplazó a la línea del estilo A ese
mismo día, prototipo A/B/C con datos reales). Prohibidos los divisores huérfanos
(`hr-bdr`, `fs-divider`, `pel-sheet-divider` — retirados). Excepción: divisores
CON palabra (`.splash-rail-div` "ANTERIORES", `.conflict-vs-line` "VS").

### Badges (inline en texto o título)
| Clase | Descripción | Estilo |
|---|---|---|
| `.apertura-badge` | Evento especial / apertura | Fondo amber sólido, texto white, `--t-xs`, `--r-md` |
| `.past-badge` | Función pasada | Solo texto `--gray2` |
| `.notice-badge` | Cancelada / reprogramada | Fondo amber sólido, texto `#0A0A0A`, `--w-display` |
| `.poster-past-badge` | Sobre póster en grid | Overlay oscuro, texto gray |

> **Regla:** Todo badge nuevo → extender este sistema. Nunca estilos inline ad-hoc.

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
showDestructiveModal(title, body, label, cb)
showActionModal(title, body, label, cb, cancelLabel)
showConflictModal(conflicts, onConfirm)
```

---

## 6. MAPA DE FUNCIONES DE RENDER

### Mi Plan (tab)
| Función | Qué hace |
|---|---|
| `renderAgenda()` | Orquestador principal |
| `renderContextualHeader()` | Panel de fase (próxima función, etc.) |
| `renderNextStrip(schedule)` | Tira de próxima función con countdown |
| `renderUnconfirmed(schedule)` | Check-ins pendientes |
| `renderMiPlanList(schedule)` | Vista lista compacta |
| `renderMiPlanCalendar()` | Vista calendario |

### Programa / Cartelera (tab)
| Función | Qué hace |
|---|---|
| `_renderProgramaContent()` | Orquestador |
| `renderProgramaList()` | Lista cronológica Hoy/Mañana |
| `_renderExploreLista()` | Lista catálogo completo |
| `renderPeliculaView()` | Grid por película |
| `render()` | Grid por horario |
| `renderProgramaChips()` | Chips de categoría |
| `renderNoticesBanner()` | Banner de avisos |

### Planear (tab)
| Función | Qué hace |
|---|---|
| `renderSimPanel()` | Panel de escenarios calculados |
| `renderGapOptions()` | Sugerencias para huecos |
| `renderFilmAlternatives()` | Alternativas para una función |

---

## 7. FLUJO DE DATOS

```
PDF del festival
      ↓
Enrichment via script (director, año, género, sinopsis, poster TMDB, lbSlug Letterboxd)
      ↓
festivals/[id].json  (films[] con poster y lbSlug inline)
      ↓
loadFestival(id)  →  swapea globals FILMS, POSTERS, LB_SLUGS, DAY_KEYS, DAY_SHORT, etc.
      ↓
render functions  →  DOM
```

### Posters — cadena de prioridad
```js
getFilmPoster(f)          // para cualquier film completo
getCortoItemPoster(item)  // para cortos individuales en film_list
```
Nunca llamar `getPosterSrc()`, `makeProgramPoster()` o `makeEventPoster()` directamente.

Prioridad interna real de `getFilmPoster` (caso film normal; ver `docs/POSTERS.md §4`
para el árbol completo con ramas event/sorpresa/cortos/programa):
1. `customPosters[normKey(title)]`
2. `posters[normKey(title)]` (map legado / TMDB) — **antes** que `f.poster`
3. `f.poster` (formato inline) — editorial-con-imagen o assets propios
4. Poster generativo `_buildPosterV16`

> Detalle que se documentaba al revés: el map `posters{}` gana sobre `f.poster`
> inline (helpers.js: "TMDB — prioridad sobre editorial cloudfront"). **Prioridad,
> cobertura, trim y reglas editoriales: `docs/POSTERS.md` (fuente única).**

---

## 8. STATE & STORAGE

### Claves de localStorage (prefijadas por festival)
```
{key}_wl        ← watchlist
{key}_watched   ← películas vistas
{key}_av3       ← bloques de no-disponibilidad
{key}_saved     ← agenda guardada { schedule: [...] }
{key}_prio      ← set de priorizadas
{key}_lastslot  ← últimos slots removidos (hasta 5)
```

### Claves de localStorage (globales)
```
otrofestiv_festival   ← ID del festival activo
otrofestiv_lang       ← idioma activo: 'es' | 'en'
otrofestiv_build      ← build version (para invalidación de cache)
```

### 8.1 FestivalContext — fuente única del estado por-festival

`src/state/festival-context.js` declara **qué estado es por-festival** en UNA tabla (`FESTIVAL_STATE`, 9 entradas). Antes esa definición vivía IMPLÍCITA en 4 listas paralelas mantenidas a mano (el clear al cambiar de festival, el hidrate desde storage, los campos que suben a la nube, las ramas al aplicar la nube). Agregar un estado por-festival exigía tocar ~9 sitios; olvidar UNO producía sangrado silencioso entre festivales (el bug de `availability`).

Cada entrada declara: `key` (nombre en el roster de state) · `empty(cfg)` (valor fresco al cambiar de festival) · `hydrate()` (valor desde storage) · `storage` (sufijo get/set) · `cloud` (columna en Supabase, o `null`) · `toCloud`/`fromCloud` (serialización). Los 4 consumidores se **DERIVAN** de la tabla: `deriveClear` · `deriveHydrate` · `deriveCloudSave` · `deriveCloudApply`. **Agregar estado por-festival = 1 entrada** (+ 1 columna Supabase si se sincroniza). La fitness function `festivalContext.test.js` afirma completitud vs. el roster y storage (§15.4).

### 8.2 Sync a la nube (Supabase `user_festival_state`)

- **Token de generación** (`loadFestival`): cada carga captura un `_loadGen`; tras cada `await` se re-verifica → una carga más nueva aborta la vieja (evita que el plan del festival A se escriba bajo las claves del B en redes lentas).
- **`_flushCloudSave`** al tope de `loadFestival`: sube la edición del festival saliente a SU fila antes de swapear el estado.
- **Merge POR CAMPO antes de subir** (`deriveCloudMerge`): el upsert de la fila entera es last-write-wins. Antes de subir se relee la fila remota; un campo que ESTE dispositivo editó (`_dirtyFields`) sube su valor local, un campo no tocado conserva el remoto → dos dispositivos editando campos distintos no se pisan. Merge a nivel de **campo**, no de elemento (no resucita borrados). `_cloudSave()` **sin** argumento = "el plan local es la verdad" = todos los campos dirty (re-push al boot: `_dirtyFields` está vacío tras un reload). Residual conocido: mismo campo + misma ventana de debounce sigue siendo last-write-wins (necesitaría timestamps por-campo).
- **Realtime** (`subscribePlanCloud`): aplica cambios entrantes con `wholesale=true` (autoritativo), guardado por festival activo + `_shouldApplyRealtimeRow` (no pisa ediciones locales dirty).

### 8.3 Cache de festivales en memoria (LRU)

`FESTIVAL_CONFIG[id].films/posters/…` se cachean tras la primera carga. `src/lru.js` (`lruTouch`, puro) mantiene hasta `_FEST_CACHE_CAP=8` festivales cacheados y evicta el menos-usado; el festival activo nunca se evicta. Quita el techo de capacidad simultánea sin acumular memoria sin cota.

---

## 9. CONFLICTOS DE HORARIO

Siempre usar `screensConflict(a, b)`. Nunca comparaciones de minutos directas.

---

## 10. REGLAS DE DISEÑO (no negociables)

1. **CTA primario**: fondo amber sólido (`--amber`), texto negro.
2. **Imágenes**: toda `<img>` lleva `loading="lazy"` y `onerror="this.remove()"`.
3. **Inline styles**: prohibidos en templates nuevos. Crear token antes de usar valor raw.
4. **Badges**: clases existentes. Nunca inline ad-hoc.
5. **Nuevo componente**: reutilizar tokens y clases antes de crear nuevos.
6. **Tipografía**: verificar escala de tokens antes de aplicar `font-size`.
7. **Iconografía**: solo Lucide pack. Flags de países y emojis de categoría son la única excepción.
8. **Conflictos**: siempre `screensConflict()`.
9. **Pósters**: siempre `getFilmPoster()` o `getCortoItemPoster()`. `onerror` → `this.remove()`.
10. **Tap targets iOS**: todo elemento interactivo ≥ 44×44pt. Para elementos pequeños usar:
    ```css
    .elemento { position: relative; }
    .elemento::after { content: ''; position: absolute; inset: -Xpx; }
    /* X = (44 - tamaño_visual) / 2   |   Ejemplo: emoji 22px → inset: -11px */
    ```
11. **Vista por modo de navegación** — regla global inamovible:
    - `activeDay === 'all'` (Explorar/TODO) → `programaViewMode = 'grid'`
    - `activeDay !== 'all'` (día específico) → `programaViewMode = 'list'`
    - Se aplica en `loadFestival()`, `filterByVenue()` y `filterBySection()`. El usuario puede cambiar manualmente después; esta regla aplica solo al estado inicial/reset.
12. **Cards** — 4 tipos canónicos (no agregar campos sin pasar por arquitectura):
    - Película: poster + flags + título + dur + sección, funciones + dir + sinopsis + Letterboxd, CTAs
    - Programa de cortos: igual + lista de cortos, sin Letterboxd
    - Corto individual (`openCortoSheet`): igual, solo Intereses + Calificar
    - Evento/taller: sin flags, horario + descripción, sin Letterboxd

---

## 11. AGREGAR UN FESTIVAL NUEVO

Ver protocolo completo en `pipeline/PROTOCOLO.md`.

1. Crear `festivals/[id].json`
2. Correr enrichment: `python3 scripts/enrich-festival.py festivals/[id].json`
3. Generar config: `node scripts/generate-config.js --id [id] ...`
4. Pegar bloque generado en `FESTIVAL_CONFIG` en `index.html`
5. Validar: `node scripts/validate-festivals.js [id]`
6. QA visual P1–P7
7. `node scripts/bump-version.js` → push

---

## 12. TIPOS DE FUNCIÓN — REFERENCIA CANÓNICA

Ver sección completa arriba. Cinco tipos: largometraje individual, largometraje multi-función (recomendado), programa de cortos, programa combinado, evento/taller.

---

## 13. METADATA ESPECIAL DE FUNCIONES

### `has_qa: true`
- Algoritmo suma +30 min para conflictos
- Usar `effectiveDuration(f)` en `screensConflict`, nunca `f.duration` directamente

### `requires_registration: true`
- Badge informativo. No afecta algoritmo.

---

## 14. SISTEMA GLOBAL DE SEDES (VENUES)

Formato de nombre: `"[Nombre sala] - [Ciudad]"` — siempre igual.

### Modo de transporte
```json
{ "transport": "walking" }   // Festival compacto
{ "transport": "transit" }   // Festival en ciudad (default)
```

### Resolución de venue (_resolveVenue)
1. Búsqueda exacta → 2. Búsqueda parcial → 3. Fallback estático → 4. Primer segmento del string

---

## 15. REGLAS TÉCNICAS

### Columnas tiempo/día en listas
Todo label de día/hora que ancle una columna flex debe tener `width` o `min-width` fijo. Validar con `MIÉ` (el día más ancho en Plus Jakarta Sans).

### Transformaciones masivas de código
Nunca regex sobre index.html completo para patrones estructurales. Usar parser para transformaciones de >10 ocurrencias que toquen atributos HTML.

### iOS Safari — propiedades críticas
Verificar en dispositivo físico antes de commitear cambios con: `overflow`, `position:sticky`, `touch-action`, `overscroll-behavior`, `-webkit-*`.

| Propiedad | Comportamiento en iOS Safari |
|---|---|
| `overscroll-behavior:contain` sin height | consume scroll events |
| `position:sticky` dentro de `overflow:auto` sin height | no stickea |
| `AbortSignal.timeout()` | no disponible en Safari < 16 |
| `100vh` | incluye chrome del browser en < 15 (usar `100dvh`) |
| Modificar `aria-label` en `role="dialog"` activo | puede triggear reposicionamiento de foco |
| `data-i18n` en `<script>` o `<style>` | nunca — `_applyI18nDOM` tiene guard pero la regla es no hacerlo |

### 15.4 Fitness functions — invariantes de arquitectura verificadas en CI

Las invariantes de arquitectura **no se documentan y confía**: se verifican. `validate.py` (37+ checks) y los unit tests (`node --test tests/unit/*.test.js`) corren en el CI (`bump-and-validate.yml`); ambos deben pasar. Los que protegen la modularidad:

| Check / test | Qué congela |
|---|---|
| `[layer-direction]` (validate.py) | Las dependencias apuntan hacia adentro: `domain/` no importa de controller/view; `state`/`storage` tampoco; `view/` no importa de controller salvo una **allowlist** (`getConsensusMap` — lectura de estado derivado). Antes era medición manual. |
| `[module-size]` (validate.py) | Techo de 800 líneas para módulos nuevos; los grandes actuales grandfathered a su tamaño (allowlist) → solo pueden encoger. Crecerlos exige subir el techo en el código (decisión revisada). |
| `[section-map-dupes]` | Claves duplicadas en los mapas de sección (una pisa a la otra en silencio). |
| `[test-salida-muda]` (validate.py) | Un `return;` suelto en el cuerpo de un test lo apaga sin dejar rastro: el informe lo cuenta como verde. Línea base por archivo (34 al 4 sep 2026, grandfathered) que solo puede bajar; una salida temprana nueva tiene que ser `expect(cond, '…').toBeUndefined()` o `test.skip(cond, 'razón')`, que sí se ven. Nació de T146, que dejó de medir cuando su festival de prueba encogió. |
| `[pipeline-huerfano]` (validate.py) | Un `pipeline/<festival>-*.py` está vivo solo si algún `.plan.json` lo nombra en un `cmd` — literalmente lo que `correr.py` ejecuta. Lo demás se archiva en `pipeline/_historico/` (se archiva, no se borra). Nació de medir 42 scripts con 32 huérfanos (5 sep 2026). |
| `festivalContext.test.js` | Completitud de `FESTIVAL_STATE` (§8.1) vs. el roster de state + pares get/set de storage → imposible olvidar registrar un estado por-festival. Congela también el merge por-campo (`deriveCloudMerge`) y wholesale-vs-parcial. |
| `festivalConfigCoherence.test.js` | Coherencia de `FESTIVAL_CONFIG` + `mergeFestivalSections` (secciones data-driven desde el JSON del festival). |
| `lruCache.test.js` | La decisión pura del LRU (§8.3): mueve a MRU, evicta el menos-usado, nunca el activo. |

> Regla: al cambiar la firma/deps de una función de dominio (ej. un `import` interno nuevo) suele haber que actualizar `tests/lib/load-domain.js` (`DEFAULT_FNS`) además del test.

### 15.4b Operaciones de git — las barreras y por qué existen

En una semana de agosto de 2026 se perdió trabajo tres veces, y **ninguna fue un
error de lógica**: las tres fueron manipulación del repositorio.

| qué pasó | qué se perdió |
|---|---|
| `git checkout --theirs index.html` al resolver un merge | el markup del sheet de ciudad (8 referencias) y `ticketBadgeTarget` del TEST BRIDGE (3) |
| lo mismo, dos días después | el CSS de `.fn-ciudad` / `.fn-otra-ciudad` |
| `git add -A` | versionó `fuentes/` (68 MB); al cambiar de rama, git borró del disco los PDF originales |

Las tres estaban descritas en la documentación de git. `git-checkout(1)`: `--ours`
y `--theirs` sacan «stage #2 o #3 **for unmerged paths**» — el **archivo entero**,
no el hunk. Y al cambiar de rama, los archivos versionados en una y no en la otra
se borran del working tree.

**Dos reglas duras:**

1. **Nunca `--ours`/`--theirs` sobre un archivo con código.** En este repo la
   trampa es concreta: `bump-version.js` toca cuatro archivos —`index.html`,
   `src/main.js`, `sw.js`, `version.json`— y tres **también llevan código**. Un
   conflicto ahí parece trivial y no lo es. Desde el driver `bump` (15.4c) casi
   nunca hay que resolverlo a mano; cuando lo haya, usar
   **`./scripts/traer-main.sh`**, que resuelve el bump re-ejecutándolo y al final
   verifica que ninguna línea propia haya desaparecido.
2. **Para mirar otra rama, worktree, nunca `checkout`.** Un `git worktree add`
   deja el directorio principal intacto: ni arrastra untracked ni borra nada.
3. **Nada de `git stash` en este repo.** Los worktrees aíslan el árbol y el índice;
   la **pila de stash es una sola para todo el repositorio**. Con dos chats en
   worktrees distintos, un `pop` saca la entrada de arriba — que puede ser del otro.
   Pasó el 9 ago 2026: un `pop` en el worktree de app trajo `ficmontanas-hold-5` del
   worktree de onboarding y dejó `CLAUDE.md`, `src/config.js` y
   `validate-festivals.js` con marcadores de conflicto sin resolver, en medio de una
   verificación que no tenía nada que ver con festivales.
   **En vez de stash: commiteá el WIP en tu rama.** Un commit lleva tu nombre de rama
   y nadie lo saca por accidente. Si aun así hay que aplicar uno, `git stash apply
   stash@{N}` por referencia exacta, nunca `pop`.
   No hay hook de git para stash (`pre-stash` no existe), así que la barrera vigila
   el ESTADO: `[stash-compartido]` avisa cuando hay entradas vivas con más de un
   worktree, y dice de qué rama vienen.

**Barreras mecánicas** (`.githooks/`, activadas con `git config core.hooksPath .githooks`):

| hook | qué corta |
|---|---|
| `pre-commit` | marcadores de conflicto sin resolver · documentos ofimáticos · archivos > 3 MB |
| `pre-push` | `validate.py` en rojo — el fallo se ve en 20 s acá, no en 5 min de CI |

Ambos aceptan `--no-verify`. Que el escape exista no lo vuelve rutina.

Y lo que un hook no puede cortar, lo vigila `validate.py`:

| guardián | qué vigila |
|---|---|
| `[hooks-activos]` | los hooks enchufados en este clon (`core.hooksPath`) |
| `[merge-driver]` | el driver `bump` registrado (§15.4c) |
| `[sin-symlinks]` | ningún enlace simbólico versionado — tumban el deploy de Pages |
| `[peso-repo]` | material de trabajo versionado (ofimáticos, > 3 MB) |
| `[stash-compartido]` | stash vivo con varios worktrees — la pila es del repo, no del worktree |
| `[plannable-dueno-unico]` | que nadie reimplemente «qué funciones son planificables» fuera de `plannableScreens` (exención explícita: `// plannable-ok:`) |
| `[plan-concepto]` | que «Plan» vaya en mayúscula en las 3 locales y en el fallback estático — es el nombre de un concepto, y la regla se eligió por ser verificable |
| `[close-bg-registrado]` | que toda hoja con `data-close-bg="X"` tenga su `closeX` en ACTION_REGISTRY — sin él el toque en el fondo no hace NADA, y en silencio (la hoja de ciudad fue así desde siempre) |
| `[doc-cadena]` | que esta documentación y los guardianes se citen mutuamente |

#### La identidad nunca sale de una etiqueta

`short` es cómo se **muestra** una sede; la identidad es la sede. Confundirlos costó
un bug en producción: el filtro agrupaba por `short`, que no es único entre ciudades
(FICDEH tiene dos «Cinema Local» y dos «Alianza Francesa»), así que elegir una traía
las funciones de la otra y la segunda desaparecía de su lista. La clave correcta es
**(ciudad, short)**: la ciudad separa, el short agrupa — dentro de una ciudad el
short repetido son las salas de un edificio y agruparlas es lo que se quiere.

Tres guardianes sostienen la regla, y cada uno cubre lo que el otro no ve:

| | |
|---|---|
| `[short-ambiguo]` | **el dato**: avisa si un short se repite entre ciudades (validate-festivals) |
| `venueMatches.test.js` | **la unidad**: el predicado no cruza ciudades y sí agrupa salas |
| `P08` | **el invariante**: filtrar por una sede nunca devuelve otra ciudad, en CADA festival |
| `[ciudad-separada]` | **la pantalla**: la ciudad va DENTRO de la frase de sede (auditoría 18 ago) y necesita su « · ». Se lo pusieron a 2 de los 3 emisores; el tercero pegó «Centro Colombo AmericanoMedellín» en todos los multiciudad hasta el 25 ago |

P08 es el que más vale: no sabe nada de centinelas ni de `short`, así que sigue
cazando la clase aunque cambiemos por completo la implementación. Juzga el
resultado, no el camino — mismo patrón que el oráculo del planeador (§15.6).

> **La familia del bug.** El 9 ago aparecieron tres del mismo tipo: `day_order` que
> no era el índice del día, `COUNTRY_NAMES` sin `AR` (que devolvía `''`), y el short
> como clave. Ninguno lanzó un error: los tres devolvieron algo **plausible** —un
> orden, una línea más corta, un conteo— y por eso sobrevivieron meses. La regla que
> dejan: **una derivación que puede fallar tiene que fallar fuerte o no fallar
> nunca**; devolver un valor creíble es la peor de las tres opciones.

#### La sala que parte un programa — `[sala-mixta]`

El anclaje de función (`sealSharedSlots`) agrupa por `día|hora|sede|sala`. Si en

#### Los guardianes se pudren: la auditoría del 25 ago 2026

Un guardián es código, y como todo código se desactualiza cuando la app se
mueve. La **Fase 8** partió el JS de `index.html` en 37 módulos bajo `src/` y
anotó en el shim de `validate.py`: *«los checks no requieren cambios»*. Esa
frase fue la enfermedad — el shim inyectaba **solo `main.js`**, así que todos
los checks que leen `content` se quedaron mirando 2 de 37 módulos.

Se auditaron con **mutación** los 30 guardianes más antiguos (los anteriores a
la Fase 8, la población de mayor riesgo). Resultado: **19 vivos · 8 ciegos ·
3 decorativos**.

**Lo que se arregló:**
- **`js-syntax` era un ✓ incondicional**: `node --check` sobre un `.js` con
  `import` lo trata como CommonJS y aprueba *cualquier cosa* — incluso
  `const a = ;`. Ahora compila cada módulo como `.mjs` (parseo real) y el inline
  de index.html como script clásico. Importa porque un error de sintaxis en
  cualquier módulo mata la app entera al boot (ver [boot-esm-torn]).
- **El shim inyecta TODOS los módulos**: `event-delegation` pasó de ver 39
  `data-action` a **101** (y sus «63 muertos» eran falsos: 7).

**LOS DUEÑOS NO SON TERRITORIO.** Al ver todo el código, cuatro guardianes se
acusaron a sí mismos: el diccionario (`i18n.js`) veía sus 425 valores como
«strings hardcodeados», el adaptador (`storage.js`) veía sus propios
`localStorage`, y los bridges veían sus declaraciones como shadowing. Un
archivo que ES la referencia de un check no puede estar en su pajar:
`_SRC_NO_INYECTAR`.

**Un guardián puede tener razón y estar mal escrito.** Dos regex daban falsos:
uno cruzaba la coma de un array literal (`const _visDays=new Set([DAY_KEYS[vs],
DAY_KEYS[ve]])` parecía declarar `DAY_KEYS`); otro ignoraba que
`t('k').replace('{n}',…)` sí sustituye el placeholder.

**Y uno se BORRÓ, con medición:** `shadow-t` (retirado) vigilaba 1 de 467 llamadas a
`t()`, y con el territorio completo hay **42 sombreados de `t` y cero
peligrosos**. La alternativa correcta (ESLint `no-restricted-syntax`, parser de
verdad) marca los 42 inofensivos: 50 avisos por un bug que no ocurre. Menos
guardianes y mejores: **155 → 154**.

> **La regla que queda.** «Un guardián que nunca falló no es de fiar» se venía
> aplicando **al crearlo**. Hay que aplicarla también **al conjunto**, cada
> tanto: un guardián verde puede estar mirando el lugar equivocado desde hace
> meses. Lo único que lo demuestra es plantar el bug real donde hoy ocurriría.

---

#### `sameEntry` — la identidad de una entrada del Plan incluye la SEDE

`sameEntry(a,b)` (`src/domain/schedule.js`) es el **dueño único** de «esta
entrada del Plan es aquella»: **título + día + hora + sede**. Misma forma que
`screensConflict` para «estas dos chocan» y `venueMatches` para el filtro: el
predicado vive en el dominio y todos preguntan, nadie reimplementa.

**Por qué la sede.** FICDEH programa la misma obra el mismo día y a la misma
hora en ciudades distintas — **13 casos medidos**. Sin sede en la identidad,
agendar «La independencia» en Bogotá marcaba la función de **Ibagué** como «en
tu plan»: la app le decía a alguien de Ibagué que ya tenía algo que nunca
agendó, y la que sí quería aparecía tomada. Bug real en producción, encontrado
por el modelador de dominio el 25 ago 2026, sin relación con ninguna feature.

**Dos decisiones del predicado, y las dos importan:**
- **Falla CERRADO**: sin día u hora no matchea nada. Un predicado anterior
  (revertido con #749) matcheaba TODO con los campos ausentes, así que un
  llamador olvidadizo no daba error — borraba en masa. Ahora el olvido es un
  no-op.
- **Tolera la sede ausente**: si un lado no la declara, no se exige que
  coincida. Los planes guardados antes de que la sede viajara en la entrada no
  la tienen, y endurecerlo los desconectaría del catálogo — justo la pérdida de
  datos que el predicado existe para evitar.

**Sutileza del refresco en caliente**: la CLAVE del diff (`refresh-diff.js`) NO
lleva sede a propósito — un cambio de sede es un cambio de VALOR (regla 1, se
aplica en silencio) y meterla ahí lo volvería estructural, disparando el pill
por una mudanza de sala. Solo el emparejamiento del PLAN usa `sameEntry`.

**`verifyPlan` pregunta lo mismo (26 ago 2026).** La violación `duplicado` era
por TÍTULO: repetir el título bastaba, e `is_recurring` era el permiso que
salvaba a los talleres. Esa regla dejó de distinguir. Un plan legítimo con la
misma obra en **dos funciones** —lo que el usuario puede pedir a propósito—
salía marcado igual que un plan con la **misma función dos veces**, que sí es
corrupción; y como el chokepoint reporta a Sentry en cada escritura, gritaba en
cada toque sin señalar nada. Ahora `duplicado` = `sameEntry(a,b)`, y el permiso
de `is_recurring` sobra: las sesiones de un taller ya tienen día distinto. Dos
consecuencias que valen la pena: misma obra, mismo día y hora, **sedes
distintas** ya no es `duplicado` sino `conflicto` —que es lo que de verdad es—,
y dos entradas idénticas dejan de reportarse **también** como conflicto consigo
mismas, un eco que enmascaraba el hallazgo real.

Blindaje: `tests/unit/sameEntry.test.js` (datos reales de FICDEH) + **T108**
(mide el bug en pantalla) + `verifyPlan.test.js` y `bloqueRecurrente.test.js`
para la doctrina de `duplicado`. Cuatro mutantes mueren: quitarle la sede
reproduce el bug de producción; quitarle el fallo-cerrado reproduce el de #746;
volver `duplicado` a por-título tumba 4 tests; y quitar el `continue` devuelve
el eco de conflicto.
un programa de cortos una entrada trae `sala` y las demás no, esa obra **queda
fuera del bloque**: la duración se cuenta de menos, no cuenta como conflicto con
sus compañeras, el planificador puede agendar dos obras de la misma función, y el
aviso de la ficha dice «va con otras N obras» con N corta.

Cazado el 17 ago 2026 en FICDEH (17 AGO 17:30, Cinemateca de Bogotá): cinco cortos
que suman **86 min**, «La independencia» con `sala: "Sala Capital"` y las otras
cuatro sin sala → el bloque valía **66**.

`[sala-mixta]` (validate-festivals) mira **solo el subconjunto de formato corto**
(≤45 min) de cada `día|hora|sede`: si entre esos unos traen sala y otros no, falla.
Exigir que TODA la función fuera corta dejaba escapar el caso original, porque a esa
hora y en esa sede había además un taller de 180 min en otra sala — eso es legítimo
y por eso no se marca cuando hay largos o eventos en la mezcla. Las cuatro funciones
de FICDEH que ya estaban mal al escribir la regla quedan en `DEUDA_SALA` como
WARNING (el dato es del festival y arreglarlo exige la guía oficial); cualquier caso
nuevo falla en duro.

#### El paraguas no promete formato — `[vocab-obra]`

«No siempre son películas. Esto es regla» (Juan, 17 ago 2026). El catálogo lleva
talleres, charlas y eventos; llamarlos «película» en un texto que los abarca a
todos promete un formato que la app no controla. El vocabulario tiene dos
paraguas y ninguno es un formato: **ACTIVIDAD** para lo que ocurre (incluye
talleres y eventos), **OBRA** para lo que se programa. *Función* sigue siendo solo
la proyección.

El hallazgo que lo destapó: el encabezado del Recuerdo decía «Viste 4 películas»
mientras el chip contiguo decía «obras vistas» — dos vocabularios para lo mismo,
en pantallas vecinas. Se barrieron 13 strings ES (más sus pares EN/PT); en inglés
el paraguas es **title**, que es de uso corriente en festivales y no promete
formato.

`[vocab-obra]` (validate.py) mira el VALOR de cada clave de `src/i18n/i18n.js` —
lo que el usuario lee— y no el nombre de la clave: hay claves históricas
(`misc_pelicula`, `plan_pelicula_hoy`) cuyo texto ya dice «obra», y renombrarlas
sería un cambio sin lector. Quedan EXENTOS los nombres de FORMATO
(`label_cortometraje`, `label_cortos`), donde «cortometraje» es el dato correcto y
no un paraguas.

#### La cuenta no lleva el sustantivo escrito — `[i18n-sustantivo-pegado]`

Las cards de programa compuesto decían «2 obras · 93 min» **en inglés**: el
sustantivo estaba pegado al template en dos sitios —`_datoCompuesto`
(components.js) y `slotPosterParts` (helpers.js)— en vez de salir de `t()`. Once
ocurrencias en la grilla.

Ningún guardián podía verlo. `[i18n-complete]` comprueba que las **claves**
existan en los dos idiomas, y un literal no es una clave; `literal-template.spec`
vigila `${` roto, otra cosa. Y un test de DOM solo alcanza lo que se **renderiza**:
medido, `_datoCompuesto` no se pinta en ninguno de los tres festivales grandes,
así que su regresión sería invisible desde el navegador.

Por eso hay **dos** capas: `[i18n-sustantivo-pegado]` (validate.py) mira el
CÓDIGO —una interpolación seguida de nuestro vocabulario en español, `${n} obras`,
es cromo sin traducir— e **I07** (i18n.spec.js) mira el DOM en inglés buscando
«N obras» y hermanos. El contenido del festival no se traduce por diseño, así que
el número delante es lo que distingue cromo de título.

#### El build que se ve es el que corre — `[dbg-ver-sin-literal]`

El buscador muestra el número de build en su esquina (`#dbg-ver`). Estaba
**tipeado a mano** en `index.html`, y nadie lo actualizaba —`bump-version.js` ni
sabía que existía—, así que enseñó el build del **10 de mayo durante cuatro
meses** a todo el que abriera el buscador. Un número de build existe justo para
lo contrario: saber qué código corre de verdad, que es la cicatriz del bundle
congelado del v6/v7 en Play Store. Uno viejo miente sobre lo único que tenía que
decir, y encima parece confiable.

Ahora lo llena `main.js` con `BUILD_VERSION` —el del código que se está
ejecutando, mantenido por `bump-version.js`— y el nodo **nace vacío**: si el JS
no llega, mejor sin número que con uno falso. `[dbg-ver-sin-literal]`
(validate.py) bloquea el push si vuelve a nacer escrito.

#### El nombre de la actividad — `[event-kind-conocido]`

`event_kind` es la palabra que la card le pone encima a una actividad: TALLER,
CHARLA, MASTERCLASS. `makeEventPoster` la traduce con dos mapas (`_kindMapES` y
`_kindMapEN` en `src/view/components.js`) y, si la clave no está, **cae al genérico
«EVENTO»**. No falla, no avisa: produce una card correcta que no dice nada.

Dos formas de romperse, cazadas el 10 ago 2026 con FICMA ya abierto:

1. **La palabra que pusimos nosotros.** FICDEH («💬 Charlas que Unen», 18) y FICMA
   («💬 Charlas», 6) mostraban PONENCIA — una palabra que no aparece en ninguna
   fuente de ninguno de los dos; la Franja Académica de FICMA dice TALLERES y
   CHARLAS. Ver también [nombre oficial / secciones tal cual]: **el vocabulario es
   del festival, no nuestro**, y eso vale para el kind igual que para la sección.
2. **La clave que nunca existió.** Los 8 talleres de FICMA traían `'taller'`, que
   jamás estuvo en el mapa: llevaban meses mostrando «EVENTO» y nadie lo vio, porque
   una card genérica no se distingue de una card correcta si no sabés qué esperabas.

`[event-kind-conocido]` (validate-festivals) exige que todo `event_kind` del dato
exista en **los dos** mapas — leídos por separado, porque una clave solo en ES
sobrevive hasta que alguien abre la app en inglés. Si el parser no logra leer los
mapas se declara **CIEGO y bloquea**, en vez de aprobar por no haber encontrado nada.

Y una regla de orden que no se puede invertir: **primero el mapa, después el dato.**
`event_kind` solo alimenta `makeEventPoster`, y `agenda.js` (×2) y `programa.js` lo
llaman sin la sección — así que migrar el dato antes que el código no deja el
nombre viejo: deja «EVENTO», que es peor.

#### Festival aplazado — `status` y `[festival-aplazado]`

El terremoto de Manizales (10 ago 2026) encontró a la app diciendo «FICMA EN
CURSO» —punto verde, 90 funciones, chips AHORA— mientras el festival publicaba
que no habría festival. El parche de urgencia (`group:'test'`) lo hizo
desaparecer sin explicar; el estado de verdad es **`status:{kind:'postponed',
since, note, url}`** en `FESTIVAL_CONFIG`:

- `_classifyFestival` devuelve `'postponed'` **antes** de la aritmética de fechas
  — un solo dueño, y de él caen en cascada la preselección del splash, el punto
  verde, el orden del riel y la rehidratación del plan.
- El festival **se ve** (card con distintivo APLAZADO, última de los vigentes,
  fuera de «Próximos» — un aplazado no tiene fecha) pero **no invita a ir**: sin
  AHORA (`isNowShowing` gana el estado), sin abrir en «hoy» (loader), y la banda
  persistente del header dice las palabras del **propio festival**: `note`
  verbatim, y `note_en` como traducción nuestra aprobada por Juan (opcional; sin
  ella el EN muestra el ES intacto — nunca se traduce en runtime). Etiqueta y
  enlace pasan por `t()`.
- Reversión: fechas nuevas + borrar `status`. Los datos no se tocan.

**Un aplazado tampoco TERMINÓ.** `festivalEnded()` era pura aritmética contra
`FESTIVAL_END`, y las fechas viejas se cruzan igual: FICMA habría entrado en Modo
Recuerdo el 18 ago —«Tu festival», «Marcá lo que viste y calificálo»— por ocho días
que no ocurrieron, sin que nadie desplegara nada. El estado viaja por el bridge
(`FESTIVAL_POSTPONED`, junto a `FESTIVAL_END`) y `festivalEnded()` lo respeta: 27
call sites corregidos en un punto. En Mi Plan el plan guardado sigue rindiendo, y
el aviso NO se repite: la banda del header ya está visible en esa pestaña.

`[festival-aplazado]` (validate.py) exige el status COMPLETO: `note` (sin él la
banda sale vacía), `url` (el comunicado), `since`, y `kind` exactamente
`'postponed'` — un typo haría que `_classifyFestival` lo ignorara en silencio y
el festival volvería a salir «en curso», que es el bug que este estado evita.

#### Cuándo la suite dice la verdad — `scripts/test.sh`

Medido el 10 ago 2026, sin reintentos: con la máquina **libre**, la suite da 0
fallos a 5 workers, dos corridas seguidas. Con **carga externa** —otra sesión de
Claude corriendo sus tests en la misma máquina— la MISMA suite falló 11 veces, y
5, y 6, con tests distintos cada vez. El puerto por corrida aisló el servidor;
no aísla la CPU.

Dos correcciones, ninguna de ellas «arreglar tests»:

- **`test.sh` avisa antes de correr** cuando la carga supera el 70% de los núcleos
  o hay otra corrida de Playwright viva. No bloquea: un rojo bajo carga no es un
  rojo de la app, y decirlo vale más que esconderlo.
- **`retries: 2` → `1`.** Con dos reintentos la suite reportaba «13 flaky, 0
  fallos» y eso se leía como verde; sin reintentos, esa misma suite fallaba 11.
  Los reintentos no distinguían «la máquina estaba ocupada» de «la app falla una
  de cada tres veces». Y los flaky ahora se **nombran** al final de la corrida:
  un flaky no es un test que pasa, es un test que no sabe si pasa.

> Tres trampas de shell, las tres cazadas probando y no leyendo: `set -o pipefail`
> mataba el script cuando `pgrep` no encontraba nada (cero salida, exit 1);
> `${otras:+…}` se expandía con `otras=0` porque «0» no es cadena vacía; y el
> `grep '^ *N flaky'` nunca casaba porque el reporter escribe secuencias de escape
> del terminal antes del texto.

#### La doc de contexto no puede envejecer — `[claude-md-fresco]`

`CLAUDE.md` se genera leyendo el repo, pero el generador **se corre a mano** y
nadie lo verificaba. El archivo que un ayudante lee PRIMERO envejecía en silencio.

> **La cicatriz (15 ago 2026).** Decía «Android: Closed testing — Alpha» meses
> después de que las dos apps estuvieran publicadas y verificadas. De ahí salió el
> diagnóstico de que «nadie pudo instalar la app» durante FICMA, FICDEH y FINCA
> —falso— y la petición a Juan de confirmar algo que el repo debía saber. **Un
> dato caduco en la doc de contexto no produce una duda: produce una conclusión
> falsa, con seguridad.** Es peor que un hueco: un hueco se pregunta.

Dos correcciones, y la segunda es la que dura:

- **El estado que el archivo no puede saber, sale del archivo.** El estado de las
  tiendas vive en App Store Connect y Play Console; en `CLAUDE.md` quedan el
  enlace y el procedimiento. Misma regla que el radar («si no lo mediste, no lo
  afirmes») y que los guardianes que se declaran ciegos en vez de aprobar.
- **El estado que sí deriva del repo, se verifica.** `[claude-md-fresco]`
  regenera el archivo en un temporal y compara las secciones DERIVADAS —la tabla
  de festivales y las features—; si difieren, bloquea y dice el comando. La línea
  del último commit se excluye a propósito: cambia con cada commit y compararla
  haría fallar el check siempre. El check restaura el archivo: no deja huella.

#### La cadena doc ↔ guardián

Una regla escrita que nadie ejecuta es una opinión; un guardián que nadie documenta
es una trampa. `[doc-cadena]` cierra el circuito en **las dos direcciones**:

- **doc → código.** Una etiqueta citada en la documentación sin ejecutor real es una
  promesa vacía. Hoy son **cero** y es un error bloqueante que dejen de serlo.
- **código → doc.** Un guardián sin una línea acá es deuda: se cumple, pero nadie
  puede leer la doc y saber que existe, así que se re-descubre a golpes o se duplica.
  Techo que solo BAJA (mismo patrón que `module-size`): los 46 que ya estaban quedan
  con número, y **uno nuevo nace documentado o no entra**.

> Medido el 9 ago 2026, a partir de «hemos escrito muchas cosas pero no todas se
> cumplen en cadena» (Juan). El resultado corrigió la intuición: de 61 etiquetas
> documentadas, **las 61 tenían ejecutor**. El hueco estaba al revés — de 100
> guardianes reales, **46 no se mencionaban en ningún documento**.
>
> Dos advertencias que costaron dos iteraciones, y que valen para cualquier check
> que lea código con regex: el extractor tiene que conocer **cómo declara sus
> etiquetas cada archivo** (`check = 'x'` en validate.py, `'[x]'` en el mensaje de
> validate-festivals.js, `err('x', …)` en lint-catalog.py) o inventa huérfanos —
> primero dio 54 falsos, después 5 «promesas rotas» que sí existían. Un check con
> parser flojo no avisa de menos: **avisa mal**, que es peor.

> Por qué barreras y no propósitos: un agente encadena comandos de git en un
> segundo, sin la fricción que tiene una persona al ver el diff en pantalla. La
> velocidad que ayuda escribiendo código es peligrosa moviendo archivos.

---

### 15.4c El conflicto que no debía existir — el driver `bump`

Al medir los conflictos de esa misma semana apareció que **los cinco fueron el
mismo timestamp de 12 dígitos**, y ninguno fue contenido. La causa no era falta de
coordinación entre ramas: era estructural. `bump-version.js` estampa el mismo
renglón en cada rama antes de cada push, así que con dos ramas vivas el conflicto
no es probable — **es seguro, uno por PR**. Y como tres de esos archivos también
llevan código, el conflicto barato es justo el que se lleva trabajo por delante.

Tres cambios, en orden de cuánto quitan del camino:

1. **`.gitattributes` + `scripts/merge-bump.sh`.** Los cuatro archivos del bump
   (`index.html`, `src/main.js`, `sw.js`, `version.json`) se mergean con un driver
   propio: normaliza el build a un marcador, deja que git mergee de verdad, y
   estampa de vuelta el build **más alto** de los dos lados. El conflicto que era
   solo el número desaparece; el de contenido real sigue saliendo con marcadores.
   Probado con las dos mitades antes de adoptarlo — que un conflicto real siga
   siendo un conflicto es la mitad que importa.
2. **`CLAUDE.md` fuera del bump.** Era el quinto archivo, y su línea de «último
   commit» cambiaba en toda rama sin aportar nada que `git log` no diga mejor.
   Ahora se regenera a mano: `node scripts/generate-claude-md.js`.
3. **`[sin-symlinks]` en `validate.py`.** Un symlink `fuentes` → ruta absoluta del
   Mac entró dentro de un PR de festival y tumbó el deploy de Pages: en el runner
   esa ruta no existe, el empaquetador la sigue y muere con exit 1 sin decir la
   palabra «symlink» en ningún lado. FICMA quedó en `main` sin llegar a producción.
   Un symlink no sobrevive a salir de la máquina que lo creó: la regla es absoluta.

> El driver se declara en el repo pero se registra **local** (`merge.bump.driver`):
> git no ejecuta comandos que vengan del repositorio, y eso es una defensa suya,
> no un descuido. `sh scripts/install-hooks.sh` lo enchufa —junto con los hooks— y
> `[merge-driver]` avisa si falta. `traer-main.sh` queda como red para el clon que
> no lo corrió.

### 15.4d La frontera código/datos

El trabajo está partido en dos chats con worktrees separados, y la regla es
**«código de la app acá, datos del festival allá»**. `frontera.yml` la vuelve
ejecutable: un PR que toca a la vez app (`src/`, `index.html`, `sw.js`,
`validate.py`, `tests/`, `scripts/`) y festival (`festivals/`, `assets/`) falla.

Dos decisiones deliberadas: **`src/config.js` no cuenta como código**, porque
registrar un festival en `FESTIVAL_CONFIG` es parte legítima de un PR de datos; y
la etiqueta **`frontera-ok`** deja pasar la mezcla, dejando rastro de que fue una
decisión y no un descuido.

Cuando un cambio necesita los dos lados —un campo nuevo en el dato más su soporte
en la app— van **dos PR, primero el de app**: así el dato nunca llega a producción
antes que el código que sabe leerlo.

**Dueño de la rama = quien la lleva hasta el final, push _y_ merge.** El trabajo no
se parte a la mitad entre dos chats; de ahí nacía la pregunta «¿y ahora quién
mergea?», que costó más tiempo que los conflictos.

---

### 15.5 Cómo se corre la suite — un puerto por corrida

**Correr siempre `./scripts/test.sh`**, nunca `npx playwright test` a secas:

```bash
./scripts/test.sh                       # toda la suite
./scripts/test.sh tests/programa.spec.js
./scripts/test.sh -g "T51"
```

**Por qué** (6 ago 2026 — el flaky que costó meses): Playwright **mata el
servidor que él levantó** al terminar. Con `reuseExistingServer` (local), una
segunda corrida reusa ese servidor en vez de levantar el suyo; si la primera
termina antes, la segunda se queda sin servidor a mitad de camino →
`net::ERR_CONNECTION_REFUSED` y una cascada de timeouts de 30s en specs sin
relación entre sí. Como el daño depende de qué corrida termine antes, **fallaba
distinto cada vez** y parecía aleatorio.

Medido: la misma suite da **21/21 sola y 1/21** con otra corrida solapada. Dos
suites completas solapadas daban **22 y 14 fallos**; con puerto propio, **0 y 0**.

Pasaba a diario sin que se notara: dos sesiones de Claude Code en la misma
carpeta, o dos corridas encimadas en la misma sesión. En CI el workflow invoca
Playwright cinco veces seguidas y cada paso levantaba y mataba el servidor en el
mismo puerto — misma clase de bug, por eso los pasos también usan el script.

`scripts/test.sh` toma el primer puerto libre (3000–3099) y aísla también los
artefactos: el JSON de resultados y el informe HTML son archivos únicos que dos
corridas se sobreescribían. Lo congela `[tests-puerto-propio]`, que además
prohíbe hardcodear `localhost:3000` en un spec.

> `retries: 2` sigue puesto. Ahora que la causa dominante está cerrada, la
> pregunta abierta es si todavía hacen falta o están tapando algo distinto.
> Sospechosos anotados, no demostrados: el SW recarga la página en cada
> activación (`sw.js` — `client.navigate`, ya identificado como causa de los
> falsos positivos #133–#137 del monitor, que por eso bloquea el SW) y el
> repintado alineado al minuto exacto del reloj (`main.js` — `_msToNextMin`).

---

### 15.6 QA de festival nuevo — dos capas y un gate

`docs/QA-FULL.md` definió en mayo de 2026 un protocolo de 92 checks manuales y dejó
tres bloques escritos pero **sin ejecutar**: E (Intereses), F (Planear), G (Mi Plan).
Corrió una vez. Pasaron cinco festivales sin volver a correr. Que un protocolo
manual se ejecute una vez en tres meses no es descuido — es el dato de diseño: lo
manual no se sostiene, así que lo que importa se automatiza y lo manual se recorta
hasta que quepa en una sesión.

**Capa 1 — el motor es óptimo** (`tests/unit/plannerOracle.test.js`, sin navegador).
Recorre `festivals/*.json` y compara `computeScenarios` contra un solver exacto
(`tests/lib/exact-planner.js`), certificando cada plan con `verifyPlan`. Desde ago
2026 siembra además las tres restricciones que el usuario sí usa —prioridades,
ya-vistas, disponibilidad— y juzga **los dos máximos** que la app reporta:
`trueMax` (sin exigir prioridades) y `maxWithPriorities` (exigiéndolas), este
último contra `exactMaxEntries(..., {required})`.

> Lección de método: sembrar 96 watchlists con prioridades **no** cazó una mutación
> que hacía `maxWithPriorities = trueMax`. En las 96 las prioridades nunca costaron
> nada, así que ambos máximos coincidían y la mentira era indistinguible de la
> verdad. Una restricción que no aprieta no prueba nada. Lo cerró un caso
> **dirigido**: dos obras de una sola función que chocan entre sí — exigir ambas es
> imposible por definición y los máximos se separan (1 y 0). Cuando el muestreo no
> caza, no hay que muestrear más: hay que construir la tensión.

**Capa 2 — la app conecta ese motor** (`tests/recorrido-festival.spec.js`). Un
recorrido por festival: intereses → prioridades → ya-vistas → disponibilidad →
Planear (click real) → auditar → Mi Plan → sugerencias. El DOM se usa para
**ejercer**, no para juzgar: el veredicto lo da `verifyPlan` sobre el plan que la UI
acaba de mostrar y sobre el que `commitPlan` guardó (con `__PLAN_STRICT__`, que en
tests **tira** en vez de reportar). Un aserto sobre texto renderizado se rompe con
cada cambio de copy y no dice nada sobre si el plan es correcto.

Ambas capas son **cross-festival por construcción**: la primera por el glob de
`festivals/`, la segunda por `festivalTestIds()`. Un festival nuevo entra a la
cobertura al agregar su config + su JSON, sin editar specs.

**El gate** vive en `docs/FESTIVAL-CHECKLIST.md`: un festival no se publica sin
las dos capas en verde **con su JSON ya montado**. Es lo que convierte esto en algo
que corre siempre, en vez de un documento que se relee.

**Qué encontró el primer día.** El recorrido cazó un bug real en Leviza: al vetar un
día entero, el planeador proponía **2 de las 3 sesiones** de un taller multi-día —
la rama todo-o-nada del backtracking mete el grupo completo, pero el grupo ya venía
filtrado por disponibilidad. Un plan con 2 de 3 no es medio taller: es un plan que
miente, y FICDEH —que arrancaba tres días después— tiene taller multi-día. El fix
creó `plannableScreens` como **dueño único** de «qué funciones son planificables
para vos» (cancelada · pasada · franja vetada · taller entero-o-nada), consumido por
el planeador, el oráculo y el recorrido.

**La segunda vuelta del dueño único** (16 ago 2026, re-corrida del QA). El predicado
POR FUNCIÓN se extrajo como `screeningPlannable(s)` (cancelada · pasada · franja
vetada · ciudad): el panel de alternativas reimplementaba 2 de los 4 chequeos y
ofrecía funciones de otras ciudades (436 de 836 con filtro Bogotá) y canceladas
por el sismo (118), y la Recuperación de Sugerencias se saltaba `_cancelled`.
Tres lecciones quedaron con guardián o test de mutación:
- `[plannable-dueno-unico]` captura ahora el cuerpo del filtro por **balance de
  paréntesis**, no por ventana de caracteres — la versión anterior leía 240 y el
  filtro del panel medía 337: un guardián que depende del largo no vigila,
  muestrea.
- El SET de ciudad (`planCityVenues`, view/helpers) se **publica en cada sitio de
  uso**, no solo al Calcular: quien armaba el plan a mano tenía el predicado sin
  restricción — lo destapó un test de mutación que al principio pasaba en vacío.
- `_pickScreen` (handlers): resolver (título, día, hora) **prefiere la función
  elegible** — la otra cabeza del bug del sync (#612): aquel protegía el plan
  guardado, esta protege la puerta de entrada.

**Y un dueño único solo lo es si nadie más lo reimplementa** (16 ago 2026). Con la
restricción de plan por ciudad recién puesta, el plan **volvió a cruzar ciudades**: no
por la regla —`plannableScreens` filtraba bien— sino porque `squeezeExcluded`
(`controller/handlers.js`) tenía su propia copia del predicado y reinsertaba las
excluidas **al guardar**, después del motor, y exenta del chequeo de conflicto por
`_squeezed`. La misma copia estaba en `forceInclude` («+ Incluir»). El fix tiene tres
capas, porque una sola habría vuelto a fallar: los consumidores usan el dueño;
`verifyPlan` gana la violación `ciudad-fuera` —la red que caza a **cualquiera** que
inserte, no solo al camino feliz—; y `[plannable-dueno-unico]` en `validate.py` impide
que la copia vuelva. Las preguntas sobre el **catálogo** (qué días existe una obra, por
qué quedó fuera) son legítimamente otras y necesitan ver lo que el dueño ya filtró: se
declaran con `// plannable-ok: <razón>`, que el guardián respeta. Declararlas, no
asumirlas, es lo que separa una excepción de una fuga.

> Y al extraerlo apareció la trampa que este mismo documento advierte: el worker del
> planeador se arma con `.toString()` sobre `_SCHED_PURE_FNS` (`controller/calc.js`).
> Una función nueva que no esté en esa lista existe en el main thread y **no** en el
> worker: el cálculo moría adentro y el plan no volvía nunca. Lo cazó
> `workerParity.test.js`, que lee la lista del propio `calc.js`.

---

## 16. ARQUITECTURA OBJETIVO — MVC vanilla JS

> **MIGRACIÓN COMPLETADA (JUL 2026).** El roadmap MVC (Fases 1–8) ya está en producción: las capas están separadas (`domain/` = Model puro, `view/` = render puro, `controller/` = orquestación, `state`+`storage` = estado) y su dirección de dependencia la protege una fitness function (§15.4). Esta sección se conserva como registro del diseño objetivo y su rationale.
>
> **Diferencias de nombre vs. lo real:** el destino abajo dice `model/`; la implementación usa `domain/` (funciones puras) + `state/` + `storage/`. La estructura viva es §1.
>
> **Deuda residual conocida:** el STATE/VIEWSTATE **bridge** (estado expuesto como globals bare para que los módulos lo lean sin importarlo) sigue vigente — contenido (6 puntos de `globalThis`, centralizados) y protegido por `[layer-direction]`. Migrarlo a imports explícitos es trabajo grande de bajo retorno; diferido a cuando duela.

### 16.1 Principios

- **MVC clásico**, sin frameworks, sin build step
- **ES modules nativos** cargados directamente por el browser (HTTP/2 multiplexing absorbe el costo)
- **Estado centralizado**: un único contenedor de estado, mutado solo desde Controllers
- **Funciones puras** en Model: dependencias por parámetro, cero globals, cero DOM
- **Views puras**: `(state, deps) → HTML string` — sin mutación de estado, sin side effects
- **Controllers**: único lugar donde conviven `addEventListener`, `state.update()` y `rerender()`
- **Worker boundary explícita**: archivo standalone que importa los módulos Model que necesita

### 16.2 Estructura de archivos destino

```
/
├── index.html                    ← Shell: <head>, body skeleton, <script type="module" src="controller/boot.js">
├── sw.js                         ← Service Worker — cachea model/, view/, controller/, styles/, JSONs
├── manifest.json                 ← PWA (sin cambios)
├── version.json                  ← Build (sin cambios)
│
├── model/
│   ├── time.js                   ← simNow, simTodayStr, festivalEnded, screeningPassed, dayFullyPassed, _festDate
│   ├── venues.js                 ← _resolveVenue, venueTravelMins, travelMins, vcfg
│   ├── conflict.js               ← screensConflict, effectiveDuration, parseDur, toMin
│   ├── phase.js                  ← _getFestivalPhase + _endedStats + _classifyTodayScreenings + _gapSuggestion
│   ├── schedule.js               ← computeScenarios, scoreFilm, sortScreensByStrategy, isScreeningBlocked, RNG
│   ├── film.js                   ← normTitle, getFilmPoster, getCortoItemPoster, _isEditorialPoster
│   ├── festival.js               ← FESTIVAL_CONFIG, loadFestival, switching activo
│   ├── state.js                  ← single state container — subscribe(), update(), get()
│   ├── storage.js                ← localStorage adapter (watchlist, watched, savedAgenda, etc.)
│   └── i18n.js                   ← t(), setLang, _applyI18nDOM
│
├── view/
│   ├── miplan/
│   │   ├── agenda.js             ← renderAgenda (orquestador)
│   │   ├── header.js             ← renderContextualHeader
│   │   ├── strip.js              ← renderNextStrip
│   │   ├── unconfirmed.js        ← renderUnconfirmed
│   │   ├── list.js               ← renderMiPlanList
│   │   └── calendar.js           ← renderMiPlanCalendar
│   ├── programa/
│   │   ├── content.js            ← _renderProgramaContent
│   │   ├── list.js               ← renderProgramaList
│   │   ├── grid.js               ← render (timetable grid)
│   │   ├── film.js               ← renderPeliculaView
│   │   ├── chips.js              ← renderProgramaChips
│   │   └── notices.js            ← renderNoticesBanner
│   ├── planear/
│   │   ├── sim-panel.js          ← renderSimPanel
│   │   ├── gap-options.js        ← renderGapOptions
│   │   └── alternatives.js       ← renderFilmAlternatives
│   └── components/
│       ├── sheet.js              ← openPelSheet, openCortoSheet, openAvSheet
│       ├── modal.js              ← showDestructiveModal, showActionModal, showConflictModal
│       ├── toast.js              ← showToast, showActionToast
│       ├── badges.js             ← templates de badges (apertura, past, notice, poster-past)
│       └── poster.js             ← makeFilmPlaceholder, _buildPosterV16, makeEventPoster
│
├── controller/
│   ├── boot.js                   ← bootstrap inicial, lee storage, escoge festival activo, monta listeners
│   ├── tabs.js                   ← switching entre Mi Plan / Programa / Planear
│   ├── watchlist.js              ← togglePelWL, togglePelPrio, toggleWatched, addSuggestion
│   ├── plan.js                   ← Calcular plan, aplicar escenario, slot management
│   ├── filters.js                ← filterByVenue, filterBySection, filterByDay
│   ├── lang.js                   ← setLang trigger
│   ├── sim-time.js               ← applySimTime
│   └── availability.js           ← bloques de no-disponibilidad (av-sheet)
│
├── worker/
│   ├── calc-worker.js            ← Worker entry — recibe state slice, retorna escenarios
│   └── boundary.js               ← serialización del state slice main → worker
│
├── styles/
│   ├── tokens.css                ← design tokens (--bg, --amber, --sp-*, etc.)
│   ├── base.css                  ← reset, body, tipografía
│   ├── components/               ← un .css por componente reutilizable (sheet, modal, badge, card, poster)
│   └── views/                    ← un .css por vista (miplan, programa, planear)
│
├── tests/
│   ├── unit/                     ← node:test sobre Model (import directo, sin parseo de index.html)
│   ├── integration/              ← Playwright sobre Controller + interacciones UI
│   └── fixtures/                 ← festival JSONs reducidos para tests
│
├── festivals/                    (sin cambios — datos JSON por festival)
├── i18n/                         (sin cambios — strings ES/EN)
├── assets/                       (sin cambios)
├── docs/                         (sin cambios)
└── scripts/                      (sin cambios — bump-version, generate-config, enrich, geocode)
```

### 16.3 Responsabilidades por capa

#### Model
- **Funciones puras**: input → output determinístico
- Lee state **como parámetro**, NO como global
- No referencia DOM
- Único lugar donde existe estado mutable es `state.js`; el resto del Model lee state como parámetro
- Testeable directamente con `node:test` sin DOM (`import` directo, no más extracción de `index.html`)
- Worker importa los módulos Model que necesita (sin `.toString()` serialización)

#### View
- Funciones de forma `(state, deps) → HTML string` o componentes que reciben un container y appenden DOM (sheets, modales)
- No mutan state
- No hacen fetch ni llamadas a API
- Pueden llamar a funciones Model para derivar data (pure reads), nunca para actualizar
- Reciben el slice de state que necesitan, no el state completo

#### Controller
- **Único lugar** con `addEventListener`
- Cada handler: 1) llama Model para actualizar state, 2) dispara re-render de View afectada
- Cero `onclick=""` inline en HTML
- Conecta `storage.js` con `state.js`: load on boot, save on change
- Conecta el Worker: dispara cálculos en background, recibe resultados, actualiza state

### 16.4 Trade-offs respecto al estado actual

| Concern | Estado actual | Destino | Comentario |
|---|---|---|---|
| Single-file `index.html` | ~10.150 líneas, todo mezclado | Shell de ~50 líneas + `<script type="module">` | **Se rompe el invariant single-file.** El deploy sigue siendo drag-and-drop, pero con varios archivos. |
| Build step | Ninguno | Ninguno (ES modules nativos) | HTTP/2 multiplexing absorbe el costo. Sin npm install — zero-dep mantenido. |
| Service Worker cache | Lista corta hardcodeada | Lista generada por `bump-version.js` | Crece para incluir todos los `.js`/`.css`. |
| Worker | `.toString()` + concat en string + `eval` | Archivo standalone con `import` directo | Elimina duplicación de funciones y la fragilidad del template literal. |
| Globals mutables | ~12 globals swapeados por `loadFestival` | `state.js` con `update()` / `subscribe()` | Estado explícito. Mutación trazable. |
| Android shell | Carga desde producción URL | Sin cambios | El shell no sabe ni le importa la estructura interna. |
| Deploy manual | Drag-and-drop de `index.html` (+ sw.js, etc.) | Drag-and-drop de carpeta completa | Igual de simple, ligero ajuste de proceso. |

### 16.5 Roadmap — fases concretas

| Fase | Alcance | Capa | Estado |
|---|---|---|:---:|
| **1** | `_resolveVenue` extraído + contratos en `screensConflict`/`effectiveDuration` + 18 tests | Model | ✅ merged |
| **2** | `_getFestivalPhase` descompuesto en 3 helpers + 19 tests | Model | ✅ merged |
| **3** | Subsistema temporal: `simNow`, `simTodayStr`, `festivalEnded`, `screeningPassed`, `dayFullyPassed`, `_festDate` + contratos + 21 tests | Model | ✅ merged |
| **4** | Schedule planning: `computeScenarios`, `scoreFilm`, `sortScreensByStrategy`, `isScreeningBlocked`, RNG helpers + contratos + 26 tests (property-based para `computeScenarios`) | Model | ✅ merged |
| **5** | Storage adapter: encapsular I/O de `localStorage` en namespace `storage` (24 métodos, 9 user-state + 3 global). Validate check `[storage-encapsulation]` enforza zero `localStorage.*` inline. 19 tests | Model | ✅ merged |
| **5.5** | State container mirror: 19 globals espejados via namespace `state` con `set/update/batchUpdate/subscribe/snapshot` + lazy fallback. **Solo canaliza escrituras** — readers siguen yendo al global. `loadFestival` en 3 batches atómicos. Validate check `[state-mirror]`. 28 tests | Model | ✅ merged |
| ~~5.6~~ | ~~Migrar readers a `state.get(k)`~~ | — | ❌ skip (los readers se migran bundled con Fase 6/7 cuando se necesita el shape `function(state){...}`; el mirror invariante permite que el doble-truth coexista hasta entonces) |
| **6** | View extraction: convertir cada `renderXxx` en función pura `(state, deps) → HTML string`. Readers de los Views migran de globals a `state.snapshot()` destructure al inicio. Mover componentes (sheet, modal, toast, badges, poster) a `view/components/` lógicamente (split físico es Fase 8) | View | propuesta — siguiente |
| **7** | Controller layer: migrar inline `onclick` a `addEventListener` en `controller/*.js`. Cada handler = Model update + View rerender. Readers de handlers (toggleWL, togglePriority, etc.) migran a `state.get(k)`. `subscribe()` se conecta al rerender pipeline | Controller | propuesta |
| **8** | File split: mover Model/View/Controller a archivos físicos `.js`. `index.html` queda como shell. Worker en archivo standalone. CSS modularizado. CI cachea estructura nueva en sw.js. **Mirror global eliminado** — state queda como single source of truth | Build/Deploy | propuesta |

### 16.6 Dependencias entre fases

```
Fase 1 ── Fase 2 ── Fase 3 ── Fase 4 ── Fase 5 ── Fase 5.5 ──┐
                                                             ├── Fase 6 ── Fase 7 ── Fase 8
                                                             │
                                          (State container es prereq de Views puras)
```

- Fases 1–4 completan la **capa Model** (extracción + contratos + tests, todavía en index.html)
- Fase 5 encapsula **I/O de storage** (sin tocar runtime state)
- Fase 5.5 introduce **state container con mirror** — escrituras canalizadas, readers no migrados (intencional)
- ~~Fase 5.6~~ skip: la migración masiva de readers no aporta valor sin Views puras. Se hace per-feature en Fase 6/7
- Fase 6 hace los **Views puros** — readers de Views migran a snapshot destructure como parte del cambio de shape
- Fase 7 hace los **Controllers explícitos** — readers de handlers migran a `state.get`, `subscribe` se conecta
- Fase 8 hace el **split físico** y **elimina el mirror** (state como única fuente de verdad)

### 16.7 Lo que NO cambia en el destino

- Festival JSON schema (`docs/SCHEMA.md`)
- i18n: bloque `_I18N` en `src/i18n/i18n.js` (los JSON legacy ya no existen)
- Design tokens (las mismas `--*` CSS vars, solo extraídas a `styles/tokens.css`)
- TMDB / Lucide / Plus Jakarta Sans (siguen vía CDN)
- Manifest / PWA / Android shell
- Deploy manual via GitHub web interface
- `validate.py` (sigue corriendo en CI; cobertura se extiende a los nuevos archivos)
- El protocolo de trabajo con Juan (arquitectura antes de ejecución, cambios quirúrgicos, validar antes de commitear)

### 16.8 Riesgos del destino y cuándo abortar

| Riesgo | Mitigación | Trigger para abortar |
|---|---|---|
| ES modules en Safari iOS < 11 | Confirmar versión mínima soportada (la app es mobile-first iOS) | Soporte Safari ≥ 11 cubre el mercado real |
| Latencia inicial del Service Worker con muchos archivos | sw.js pre-cache all en `install` event | Si TTI mobile sube > 200 ms, considerar bundling minimal |
| Worker importa modules dinámicamente (no toString) | Test exhaustivo del worker post-split | Si Planear se degrada, mantener serialización vía toString hasta resolver |
| Fase 5 (state container) implica tocar muchos callsites | Hacer un PR por subsistema (time, venues, conflict, phase, schedule, festival) | Si el blast radius por PR > 200 líneas tocadas, dividir más |
| Fase 8 cambia el modelo de deploy de Juan | Documentar el nuevo flujo en CLAUDE.md antes de mergear Fase 8 | Si el deploy nuevo no es drag-and-drop friendly, mantener single-file build como fallback |
