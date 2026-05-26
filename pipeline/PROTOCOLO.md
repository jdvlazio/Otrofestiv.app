# Otrofestiv · Protocolo de producción de festivales

Este documento describe el proceso estándar para montar un festival en la app.
Siempre el mismo proceso — solo cambian los datos.

> ⚠️ **AUTORIDAD: para enrichment (TMDB / posters / synopsis_en / Letterboxd), `docs/PIPELINE.md` manda.**
> Es el proceso endurecido tras los incidentes de Tribeca 2026 (134 posters falsos, 107 synopsis_en
> de films distintos, slugs LB inferidos mal). Este PROTOCOLO describe el flujo general y los inputs;
> ante cualquier conflicto sobre qué se acepta de TMDB/LB, **PIPELINE.md prevalece**. Los scripts
> (`enrich-festival.py`, `tools/enricher.html`) **proponen** datos — no son verdad sin verificación humana.

---

## Lo que necesito de ti para comenzar

### Opción A — PDF del programa de mano
Súbelo directamente en el chat. Necesito que tenga texto seleccionable (no imagen escaneada). Puedo leer grillas de horarios, listas de películas, cualquier formato.

### Opción B — CSV del organizador
Pide al organizador que llene el archivo `/pipeline/csv-template.csv`. Si no es posible, con un Google Sheet o Excel funciona igual — lo pasan a CSV o me lo compartes.

### Información adicional que siempre necesito
- Nombre oficial del festival y año
- Fechas del festival (ej: 11–20 SEP 2025)
- Ciudad / región
- Modo de transporte predominante: `walking` (pueblo/campus) · `mixed` (ciudad con sedes concentradas) · `transit` (ciudad grande, Uber/Metro)
- ID corto para el JSON (ej: `cinemancia-2025`, `aff-2026`)

---

## Regla de arquitectura — Configuración de festival

La configuración de un festival (nombre, fechas, días, storageKey, etc.) vive en **un solo lugar**:

- **`FESTIVAL_CONFIG` en `src/config.js`** — generado por `generate-config.js`, pegado a mano.

**El JSON del festival NO lleva bloque `config{}` — nunca.** `validate-festivals.js` lo bloquea como
gate (config{} en el JSON = error). El engine ignora silenciosamente cualquier config dentro del JSON.
(Corrige una versión vieja de este doc que decía "config{} en el JSON, sincronizado" — eso ya no aplica.)

## El pipeline — siempre en este orden

> ⚠️ **Regla global: ningún festival llega a producción sin completar los 5 pasos.**
> El Paso 2 (Enrichment) es obligatorio sin excepción — no es opcional ni se pospone.

### Paso 1 · Parseo
**Yo produzco:** JSON de films con estructura canónica.
- Cada film único con sus metadatos
- Múltiples funciones en `screenings[]`
- Programas combinados con `is_programa: true`
- Eventos/talleres con `type: "event"`
- Q&A marcado con `has_qa: true`
- Inscripción previa con `requires_registration: true`

**Tú revisas:** que los títulos, directores, horarios y venues sean correctos.

### Paso 2 · Enrichment (TMDB + Letterboxd) — OBLIGATORIO

**Dos opciones equivalentes — usar la que sea más cómoda:**

**Opción A — Script (recomendado para festivales grandes):**
```bash
pip install requests
export TMDB_API_KEY=tu_key_de_tmdb
python3 scripts/enrich-festival.py festivals/<id>.json
```
El script **propone** datos de TMDB. Pero **no todo lo que propone es confiable** — regla de PIPELINE.md (Fase 3), tras los incidentes de Tribeca:

| Campo | Regla (PIPELINE.md manda) |
|---|---|
| `genre`, `year` | Aceptables de TMDB **solo si vacíos** y tras verificar que el `year` del scraping es correcto (el match usa `year`; un año corrupto asigna datos de OTRO film). |
| **`poster`** | ❌ **PROHIBIDO confiar en TMDB sin verificación visual humana.** 134 posters falsos en Tribeca. Fuente confiable: `og:image` del sitio oficial. El poster de TMDB que escriba el script **se verifica o se vacía**. |
| **`synopsis_en`** | ❌ **PROHIBIDO de TMDB sin verificar que describe el film correcto.** 107 synopsis_en de Tribeca eran de otra película. |
| `director`, `country`, `language` | Solo del scraping de primera fuente — **no** de TMDB. |

> **`lbSlug`** — el script lo resuelve vía `letterboxd.com/tmdb/{id}/`, pero **cada slug se verifica individualmente** (visitar la URL, comparar director+año) antes de aceptarlo. Inferir slugs apunta a films distintos (ver PIPELINE.md Fase 3b). `⚠️ LB PENDIENTE` = buscar y verificar a mano.

**Opción B — Enricher web:**
Abrir `otrofestiv.app/tools/enricher.html`, cargar los films, correr TMDB, resolver slugs LB desde el browser. **Mismas reglas de verificación** — poster/synopsis_en no se confían sin revisión humana.

**Tú produces:** JSON con `director`, `genre`, `year`, `synopsis` enriquecidos y **`poster`/`lbSlug` verificados** (los campos van en cada objeto film: `film.poster`, `film.lbSlug` — no en mapas `posters{}`/`lbSlugs{}` al nivel raíz).

> Sin este paso: las cards de películas quedan sin director, año ni sinopsis. No deploy.

### Paso 3 · Venues — OBLIGATORIO si el festival tiene más de una sede

**Yo produzco:** bloque `venues{}` con coordenadas via Nominatim para cada sede.
- Formato de nombre: `"Nombre Sede - Ciudad"` (canónico, siempre igual)
- Coordenadas exactas de la dirección física, no del centro de la ciudad

**Tú revisas:** que los nombres de las sedes coincidan exactamente con los del JSON de films.

> Sin `venues{}`, el algoritmo de planificación calcula tiempo de traslado = 0 entre todas las sedes. Para festivales con sede única (o sedes en el mismo predio) esto es correcto. Para festivales con sedes en distintos barrios o ciudades, es imprescindible.

> ⚠️ **Regla GPS — BLOQUEANTE:** cada venue debe tener `lat` **y** `lng`. Un venue con solo uno de los dos campos es equivalente a no tener coordenadas (el app usa el tiempo por defecto) y bloquea el CI. Verificar siempre con `node scripts/validate-festivals.js` antes de commit.

### Paso 3.5 · Generar entrada FESTIVAL_CONFIG

```bash
node scripts/generate-config.js \
  --id        mujeres2026             \
  --name      "Mujeres Film Festival" \
  --short     MUJERES                 \
  --city      Circasia                \
  --start     2026-08-05              \
  --days      5                       \
  --storage   mujeres2026_
```

Salida: bloque JS completo con los 5 objetos de días calculados — listo para pegar en `FESTIVAL_CONFIG` en `index.html`. Sin errores manuales.

### Paso 4 · Validación — OBLIGATORIO antes de deploy

```bash
node scripts/validate-festivals.js <id>
# Ejemplo: node scripts/validate-festivals.js mujeres-2026
```

Verifica: campos requeridos, consistencia de días, secciones sin duplicados de emoji, `film_list` en programas de cortos. Exit 0 = listo. Exit 1 = corregir antes de continuar.

### Paso 5 · Ensamblaje

**Yo produzco dos artefactos:**

**A. `festivals/<id>.json`** — datos de películas completos y enriquecidos, listo para subir al repo.

**B. Bloque FESTIVAL_CONFIG** — generado con el script en el Paso 3.5, listo para pegar en `index.html`.

**Tú haces:**
1. Subir `festivals/<id>.json` al repo (drag & drop en GitHub o push)
2. Pegar el bloque en `FESTIVAL_CONFIG` en `index.html` (buscar el cierre `};` y pegar antes)

### Paso 6 · QA Visual — OBLIGATORIO antes de deploy

Abrir la app en mobile (390px) con el festival nuevo activo y verificar las 7 pantallas en orden. **Sin excepción — si alguna falla, no se hace deploy.**

#### P1 · Splash y selector
- [ ] Festival aparece en el dropdown del splash con nombre, ciudad y fechas correctas
- [ ] Badge correcto: vacío si está activo, `PASADO` si terminó, `TEST` si `group:'test'`
- [ ] Festival aparece en el selector interno (topbar → chevron)

#### P2 · Explorar — grid de posters
- [ ] Posters reales visibles (no todos generativos)
- [ ] Ningún poster negro ni roto — fallback generativo si no hay poster real
- [ ] Filtros Sección y Lugar funcionan y muestran las secciones del festival
- [ ] Tab de días muestra todos los días del festival
- [ ] **Cada tab de día muestra films de ese día** — tocar cada día y confirmar que el grid no queda vacío (valida que `film.day` coincide con `dayKeys` en FESTIVAL_CONFIG)

#### P3 · Pel-sheet
- [ ] Header: flags · duración en una línea
- [ ] Metaline: director · género · año
- [ ] Sección tappable en ámbar
- [ ] FUNCIÓN: día y hora en ámbar, venue correcto (sin ciudad si el festival tiene `city` definido)
- [ ] SINOPSIS visible
- [ ] Letterboxd solo aparece si hay slug — sin enlace roto
- [ ] CTAs: Intereses (ámbar), Priorizar (secundario), Vista (terciario)

#### P4 · Planear — disponibilidad y algoritmo
- [ ] Bloques de disponibilidad se pueden crear y guardar
- [ ] "Ver opciones" genera escenarios (sin freeze — Web Worker activo)
- [ ] Escenarios muestran películas del festival actual (no de otro festival)

#### P5 · Mi Plan
- [ ] Plan guardado muestra películas en orden cronológico
- [ ] Días correctos del festival
- [ ] CTA "Ver Mi Plan" / "Ir al Programa" según si hay plan

#### P6 · Intereses — lista
- [ ] Films agregados aparecen con poster, director, siguiente función
- [ ] Films sin funciones futuras aparecen con `opacity:.35`
- [ ] Botones Priorizar y Vista funcionan

#### P7 · Cambio de festival
- [ ] Cambiar a otro festival desde el selector limpia el estado correctamente
- [ ] Volver al festival nuevo mantiene los datos

**Si algo falla:** documentar en el chat antes de continuar. No hacer deploy parcial.

### Paso 7 · Deploy
```bash
node scripts/bump-version.js   # sincroniza sw.js y version.json — obligatorio antes de push
```
**Yo hago:** push directo al repo `jdvlazio/Otrofestiv.app` via GitHub API.
**Resultado:** festival disponible en `otrofestiv.app` en ~2 minutos.

---

## Convenciones que nunca cambian

### Objeto film — formato canónico (desde Jardín 2026)

Poster y Letterboxd van **en el objeto film**, no en mapas separados:

```json
{ "title": "...", "poster": "/path.jpg", "lbSlug": "titulo-2026", ... }
```

El script `scripts/enrich-festival.py` produce este formato automáticamente.
**No crear `posters{}` ni `lbSlugs{}` en festivales nuevos.**



Para agregar un festival nuevo, el único lugar que se edita es `FESTIVAL_CONFIG` en `index.html`. **Nunca** hardcodear IDs de festival en otro lugar del código.

```js
// index.html — FESTIVAL_CONFIG
'jardin2026': {
  name: 'Festival de Jardín',
  city: 'Jardín',
  dates: '10–14 SEP 2026',
  // ...
}
```

El festival queda disponible automáticamente en el selector y en `_DEFAULT_FEST_ID`.

> **Seguridad:** La TMDB API key NO debe incluirse en el bundle de producción (`index.html`).
> Solo pertenece en herramientas de enriquecimiento offline (`tools/enricher.html`, `scripts/enrich-festival.py`).
> La key en producción debe ser `''` (string vacío) — los fallbacks la manejan silenciosamente.


Siempre: `"Nombre de la Sede - Ciudad"`
```
"Cine MAMM - Medellín"
"Teatro Caribe - Itagüí"
"Teatro Otraparte - Envigado"
"Plaza Bocagrande - Cartagena"
```

### Días
Para festivales en español: `"VIE 12"`, `"SÁB 13"`, `"DOM 14"` (abreviatura en español + número).
Para festivales en inglés (ej: Tribeca): `"TUE 3"`, `"WED 4"` — usar abreviaturas EN desde el inicio.
`generate-config.js` produce los objetos `dayShort` y `dayLong` según el idioma configurado.

### Horarios
Siempre 24h con dos dígitos: `"17:00"`, `"09:30"`, `"21:00"`

### Duración
Siempre con `min`: `"147 min"`, `"90 min"`

### Flags
Siempre emoji de banderas: `"🇨🇴"`, `"🇦🇷🇫🇷"`

---

## Festivales en producción

| Festival | ID | Archivo | Estado |
|---|---|---|---|
| FICCI 65 | `ficci65` | `festivals/ficci-65.json` | ✓ Archivado |
| AFF 2026 | `aff2026` | `festivals/aff-2026.json` | ✓ Archivado |
| Cinemancia 2025 | `cinemancia2025` | `festivals/cinemancia-2025.json` | 🧪 Test |
| Tribeca 2026 | `tribeca2026` | `festivals/tribeca-2026.json` | 📋 Draft |

## Agregar un festival nuevo — checklist

1. Crear `festivals/<id>.json` con `films[]` (Paso 1 del pipeline)
2. Correr enrichment: `python3 scripts/enrich-festival.py festivals/<id>.json` (Paso 2)
3. Generar config: `node scripts/generate-config.js --id <id> ...` (Paso 3.5)
4. Pegar el bloque generado en `FESTIVAL_CONFIG` en `index.html` — **solo esto, nada más**
5. Validar: `node scripts/validate-festivals.js <id>` (Paso 4)
6. QA visual P1-P7 (Paso 6)
7. Push → deploy automático en ~2 minutos

---

## Archivos de referencia en este repositorio

```
/pipeline/
  PROTOCOLO.md          ← este archivo
  festival-template.json ← molde JSON vacío con comentarios
  csv-template.csv       ← template para organizadores

/festivals/
  aff-2026.json          ← AFF 2026 (producción)
  ficci-65.json          ← FICCI 65 (archivado)

/docs/ARQUITECTURA.md         ← documentación técnica completa del sistema
tools/enricher.html            ← enricher de películas (TMDB + Letterboxd)
```
