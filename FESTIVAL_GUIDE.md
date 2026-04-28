# FESTIVAL_GUIDE.md
## Manual para crear un festival en Otrofestiv

Última actualización: abril 2026  
Basado en: AFF 2026 y FICCI 65

---

## Índice

1. [Estructura del JSON](#1-estructura-del-json)
2. [Sección `config`](#2-sección-config)
3. [Sección `films`](#3-sección-films)
4. [Tipos de entrada en `films`](#4-tipos-de-entrada-en-films)
5. [Secciones auxiliares](#5-secciones-auxiliares)
6. [Alimentar sinopsis](#6-alimentar-sinopsis)
7. [Registrar el festival en la app](#7-registrar-el-festival-en-la-app)
8. [Decisiones de diseño](#8-decisiones-de-diseño)
9. [Checklist de lanzamiento](#9-checklist-de-lanzamiento)

---

## 1. Estructura del JSON

Cada festival es un archivo en `festivals/nombre-año.json` con esta estructura raíz:

```json
{
  "config": { ... },
  "films": [ ... ],
  "posters": { },
  "customPosters": { },
  "lbSlugs": { },
  "venues": { },
  "transport": "transit",
  "notices": [ ]
}
```

El archivo se carga de forma asíncrona cuando el usuario selecciona el festival. El campo `config` reemplaza la configuración hardcodeada en el HTML — ningún festival nuevo requiere tocar el código.

---

## 2. Sección `config`

Controla el comportamiento del motor del festival.

```json
"config": {
  "name": "Festival de Cine de Jardín",
  "shortName": "JARDÍN",
  "city": "Jardín",
  "dates": "12–15 SEP",
  "storageKey": "jardin2026_",
  "festivalEndStr": "2026-09-15T23:00:00",
  "festivalDates": {
    "JUE 12": "2026-09-12",
    "VIE 13": "2026-09-13",
    "SÁB 14": "2026-09-14",
    "DOM 15": "2026-09-15"
  },
  "days": [
    { "k": "JUE 12", "d": 12, "lbl": "JUE" },
    { "k": "VIE 13", "d": 13, "lbl": "VIE" },
    { "k": "SÁB 14", "d": 14, "lbl": "SÁB" },
    { "k": "DOM 15", "d": 15, "lbl": "DOM" }
  ],
  "dayKeys": ["JUE 12", "VIE 13", "SÁB 14", "DOM 15"],
  "dayShort": {
    "JUE 12": "JUE 12",
    "VIE 13": "VIE 13",
    "SÁB 14": "SÁB 14",
    "DOM 15": "DOM 15"
  },
  "dayLong": {
    "JUE 12": "Jueves 12",
    "VIE 13": "Viernes 13",
    "SÁB 14": "Sábado 14",
    "DOM 15": "Domingo 15"
  },
  "lbSlugs": {
    "Título en la app": "slug-en-letterboxd"
  }
}
```

### Campos de `config`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `name` | string | Nombre completo del festival |
| `shortName` | string | Nombre corto para la UI |
| `city` | string | Ciudad sede |
| `dates` | string | Rango de fechas para mostrar (ej. `"12–15 SEP"`) |
| `storageKey` | string | Prefijo único para localStorage. **Nunca reutilizar.** |
| `festivalEndStr` | string | ISO datetime del fin del festival. Controla el modo "festival terminado" |
| `festivalDates` | object | Mapa `"DIA DD"` → `"YYYY-MM-DD"`. Usado para cálculo de conflictos |
| `days` | array | Lista de días en orden. `k` = key, `d` = número, `lbl` = abreviación 3 letras |
| `dayKeys` | array | Lista de keys en orden cronológico |
| `dayShort` | object | Mapa `key` → texto en UI (ej. `"JUE 12"`). **Siempre incluir el número.** |
| `dayLong` | object | Mapa `key` → texto largo (ej. `"Jueves 12"`) |
| `lbSlugs` | object | Mapa `título en app` → slug en Letterboxd para enlazar reviews |

---

## 3. Sección `films`

Array de todas las entradas del programa. Cada entrada es una función — si una película tiene 3 funciones, aparece 3 veces con diferente `day`/`time`/`venue`.

### Campos de una película

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
  "section": "🏆 Competencia Largometrajes",
  "day_order": 0,
  "is_cortos": false,
  "film_list": [],
  "director": "Dolores Fonzi",
  "year": 2025,
  "genre": "Drama",
  "synopsis": "Una joven falsamente acusada de infanticidio y la abogada que la defiende detonan un movimiento por la justicia y los derechos de las mujeres.",
  "festival_slug": "belen"
}
```

### Referencia de campos

| Campo | Obligatorio | Descripción |
|-------|-------------|-------------|
| `title` | ✅ | **Título principal tal como aparece en el programa del festival.** No traducir. |
| `title_en` | — | Título en inglés si el festival lo publica. Útil para match con TMDB/web. |
| `country` | ✅ | País(es) de producción |
| `flags` | ✅ | Emojis de bandera. Usar `countryToFlags()` o añadir manualmente |
| `duration` | ✅ | Duración en formato `"90 min"` o `"~90 min"` para programas de cortos |
| `day` | ✅ | Key del día, debe existir en `config.dayKeys` |
| `date` | ✅ | Número del día del mes (entero) |
| `time` | ✅ | Hora en formato `"HH:MM"` (24h) |
| `venue` | ✅ | Nombre del venue. Debe existir en `venues` o ser reconocido por `vcfg()` |
| `section` | ✅ | Sección del festival con emoji al inicio (ej. `"🏆 Competencia Largometrajes"`) |
| `day_order` | ✅ | Índice numérico del día (0 = primer día). Controla el orden cronológico |
| `is_cortos` | ✅ | `true` si es un programa de cortometrajes. `false` para todo lo demás |
| `film_list` | ✅ | Array de cortos individuales. Vacío `[]` para películas normales |
| `director` | — | Nombre del director |
| `year` | — | Año de producción |
| `genre` | — | Género cinematográfico |
| `synopsis` | — | Sinopsis curatorial. **Máximo 250 caracteres. Siempre en español.** |
| `festival_slug` | — | Slug en el sitio web oficial del festival. Necesario para scraping de sinopsis |
| `type` | — | Solo para eventos/talleres: `"event"` |

---

## 4. Tipos de entrada en `films`

### Tipo A — Película normal

Todos los campos estándar. `is_cortos: false`, `film_list: []`, sin `type`.

### Tipo B — Programa de cortometrajes

```json
{
  "title": "Cortos: Territorio",
  "title_en": "Short Films: Territory",
  "is_cortos": true,
  "film_list": [
    {
      "title": "Corteza",
      "title_en": "Bark",
      "country": "Colombia/UK",
      "duration": "14 min",
      "director": "Simon Acosta",
      "genre": "Documental",
      "synopsis": "En el corazón rural de Colombia, Astrid defiende una reserva natural."
    }
  ],
  "duration": "84 min",
  "synopsis": "Selección de cortometrajes que..."
}
```

`title` debe seguir el formato `"Cortos: NombreSección"` para que la app lo parsee correctamente.
La duración total se puede calcular automáticamente sumando las duraciones de `film_list`.

### Tipo C — Evento / Taller / Conferencia

```json
{
  "title": "BAM × Alternativa: Coproducción",
  "type": "event",
  "is_cortos": false,
  "film_list": [],
  "flags": "🏛️",
  "section": "📋 Industry Days",
  "synopsis": "Panel de coproducción internacional."
}
```

Sin `country` ni campos de película. `type: "event"` es obligatorio para el tratamiento visual correcto (poster azul, sin Letterboxd).

---

## 5. Secciones auxiliares

### `posters`
Mapa `"Título"` → URL de imagen. Para películas cuyo poster no está en TMDB.

```json
"posters": {
  "Belén": "https://ejemplo.com/belen-poster.jpg"
}
```

### `customPosters`
Igual que `posters` pero con mayor prioridad. Para overrides manuales.

### `lbSlugs`
Mapa de títulos en la app → slugs en Letterboxd. Solo para películas que existen en Letterboxd con título diferente al usado en la app.

```json
"lbSlugs": {
  "Un mundo frágil y maravilloso": "a-sad-and-beautiful-world"
}
```

### `venues`
Mapa de nombre de venue → configuración de visualización:

```json
"venues": {
  "Teatro Municipal": {
    "short": "T. Municipal",
    "lat": 5.5985,
    "lng": -75.8192
  }
}
```

### `transport`
String. Modo de transporte para calcular tiempo de traslado entre sedes. Valores: `"transit"`, `"walking"`, `"driving"`.

### `notices`
Array de avisos de reprogramación o cancelación:

```json
"notices": [
  {
    "title": "Nombre de la película",
    "festival": "jardin2026",
    "type": "rescheduled",
    "newDay": "SÁB 14",
    "newTime": "16:00",
    "newVenue": "Teatro Municipal"
  }
]
```

---

## 6. Alimentar sinopsis

### Por qué 250 caracteres

La sinopsis se muestra en un sheet de móvil. 250 chars equivalen a 2-3 oraciones — suficiente para que el usuario decida si le interesa la película. Las sinopsis curatoriales completas de los festivales suelen tener 800-1500 chars incluyendo contexto y bio del director — ese texto pertenece al sitio del festival, no a la app.

### Proceso con Chrome Extension (método probado con FICCI 65)

**Prerrequisito:** Tener Claude Chrome Extension instalada y activa.

**Paso 1 — Abrir el índice de proyecciones del festival en Chrome.**

**Paso 2 — Desde el chat con Claude, ejecutar el scraper de índice:**
El agente extrae automáticamente todos los slugs y títulos del índice usando JavaScript en el contexto de la página.

**Paso 3 — El agente visita cada página individual y extrae la sinopsis.**
Se ejecuta en background usando `fetch()` en el contexto del browser — sin SSL issues.

**Paso 4 — El agente genera el JSON resultante y actualiza el archivo del festival directamente.**

### El problema de títulos en idiomas no latinos

Cuando el JSON usa el título original (serbio, coreano, georgiano, persa, etc.) y el sitio del festival lo publica en español o inglés, el match automático falla. 

**Solución:** añadir `festival_slug` al campo de la película:

```json
{
  "title": "Vetre, pričaj sa mnom",
  "festival_slug": "wind-talk-me"
}
```

El agente usa `festival_slug` para construir la URL directamente, sin necesidad de hacer match por título.

**Regla:** Cuando el título en el JSON difiere del título en el sitio del festival, siempre añadir `festival_slug`. Hacerlo desde el inicio del JSON evita el proceso manual de mapeo posterior.

### Estándar de calidad de sinopsis

- ✅ En español
- ✅ Máximo 250 caracteres
- ✅ Terminar en oración completa (no cortar a mitad de frase)
- ✅ Fuente: sitio oficial del festival (texto curatorial)
- ❌ No incluir premios ganados, bio del director, ni contexto de distribución
- ❌ No usar TMDB como fuente principal (idioma variable, calidad inconsistente)

---

## 7. Registrar el festival en la app

Una vez creado el JSON, añadir el festival al selector en `index.html`. Son dos lugares:

**1. Splash screen (selector inicial):**
```html
<button class="splash-drop-item" data-fest="jardin2026"
  onclick="selectSplashFest('Festival de Jardín','Jardín · 12–15 SEP 2026','jardin2026')">
  <div>
    <div class="splash-drop-item-name">Festival de Jardín</div>
    <div class="splash-drop-item-meta">Jardín · 12–15 SEP 2026</div>
  </div>
</button>
```

**2. Festival switcher (dentro de la app):**
```html
<div class="fs-festival-row" data-fest="jardin2026"
  onclick="loadFestival('jardin2026')">
  ...
</div>
```

**3. Nombre del archivo JSON:**  
El nombre del archivo debe coincidir con el `id` del festival. El mapeo está en `loadFestival()`:
```js
const festFile = id === 'ficci65' ? 'ficci-65' : id === 'aff2026' ? 'aff-2026' : id;
```
Para festivales nuevos el nombre del archivo puede ser el mismo que el id (ej. `jardin2026.json`).

---

## 8. Decisiones de diseño

### `title` es el título del programa del festival, no una traducción
El festival decide cómo llamar a la película. La app respeta esa decisión. Si FICCI publica "Wind, Talk to Me" para una película serbia, ese es el título en la app. No se traduce ni se normaliza.

### `dayShort` siempre incluye el número
`"JUE 12"` no `"JUE"`. El número permite distinguir días del mismo nombre de semana si el festival dura más de 7 días, y da orientación temporal al usuario sin necesidad de context adicional.

### Una entrada por función, no por película
Si "Belén" se proyecta martes y viernes, hay dos entradas en `films` con el mismo `title` pero diferente `day`/`time`/`venue`. El motor agrupa por título al renderizar.

### `day_order` es el índice del día, no la fecha
`day_order: 0` = primer día del festival, `day_order: 1` = segundo día, etc. No es el número del día del mes. Esto permite ordenar correctamente independientemente de las fechas del festival.

### La sinopsis de programa de cortos describe la selección, no los cortos individuales
El texto curatorial del bloque (qué une a esos cortos temáticamente) va en `synopsis` del programa. Cada corto individual en `film_list` puede tener su propia `synopsis`.

---

## 9. Checklist de lanzamiento

```
[ ] JSON creado en festivals/nombre-año.json
[ ] config completo con todos los días y dayShort con números
[ ] Todas las películas con title, day, time, venue, section, day_order
[ ] festival_slug añadido para películas con título en idioma no latino
[ ] Sinopsis en español, máximo 250 chars, para todas las películas
[ ] Programas de cortos con film_list completo
[ ] Eventos con type: "event"
[ ] venues configurado para cálculo de traslados
[ ] lbSlugs para películas en Letterboxd con título diferente
[ ] Festival registrado en splash screen y festival switcher del HTML
[ ] Verificar en la app: Programa, Intereses, Planear, Mi Plan
[ ] Verificar dayShort muestra número en tabs de días
```
