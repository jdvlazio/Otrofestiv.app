# Pipeline de onboarding — festivales Otrofestiv

> **Regla de oro:** cada fase debe completarse y validarse antes de iniciar la siguiente.  
> Un push que falla `validate-festivals.js` se revierte sin excepciones.

---

## Fases en orden obligatorio

### Fase 1 · Extracción `[Data Engineer]`

**Objetivo:** JSON del festival con todos los campos poblados desde el origen.

**Entradas canónicas:**
- **Opción A1 — Scraping web server-rendered** (HTML fetch-able, página por film): `fetch` + parse `og:*` y DOM estático. Pasos 1–5 abajo + patrón `og:image`.
- **Opción A2 — SPA client-rendered** (Tribeca, Olhar, y la mayoría de sitios modernos): ver método abajo. **`fetch` devuelve un shell vacío** — solo el DOM renderizado tiene los datos.
- **Opción B — `pipeline/csv-template.csv`** (entrada estándar del organizador): una fila por **función**. El organizador llena solo los campos que conoce; el enrichment se hace downstream.

#### Método A2 — SPA client-rendered (reproducible sin contexto previo)

**Detección:** hacer `fetch()` de una página de film. Si el body vuelve vacío (shell de SPA, sin la sinopsis ni el `og:image` del film), es A2 → ir al loop por DOM renderizado. **No reintentar fetch.**

1. **Listado → IDs base.** Extraer del listado los identificadores por film (slug/uuid) + datos de tarjeta (título, título_en, director, país, año, sección). Guardar en `localStorage` como acumulador.
2. **Loop auto-avanzante.** Por cada `/{ruta}/{id}`: leer el DOM renderizado, guardar en `localStorage[done][id]`, y `location.href`-navegar al siguiente pendiente. Usar **flags por-campo** (`en_done`, `pt_full`, `info_done`) para soportar múltiples pasadas sin re-extraer.
3. **Sinopsis: del CUERPO, no de `og:description`.** El `og:description` viene **truncado** (~200 chars, corta a media palabra) y a veces es la descripción genérica del festival (el "último" og es ambiguo). Leer la sección de sinopsis del cuerpo (heading `SINOPSE`/`SYNOPSIS`) → texto completo del propio film. Stripear sufijos de UI (`TRAILER`).
4. **Multi-idioma = pasadas separadas** controladas por la key de idioma en `localStorage` (ej. `olhar-language`) + reload. El toggle del nav puede no responder a `.click()` sintético — ir por la key de storage. Festival bilingüe nativo (PT+EN en el sitio) → `synopsis` + `synopsis_en` **ambos de primera fuente**, sin traducción ni TMDB.
5. **Assert de readiness** antes de leer: confirmar que el DOM ya renderizó el film esperado (ej. `document.title`/heading == título esperado, o `og:image` contiene el id del film). Sin esto, una SPA lenta da el dato del film **anterior** (riesgo silencioso de A2).
6. **Verificación poster↔film por id.** Si el `og:image`/CDN embebe el id del film en el path (caso Olhar/Supabase), validar que `poster.includes(filmId)` para los N films — caza stale-render sin revisión visual. (Lo que a Tribeca le faltó: 134 posters falsos por matching TMDB.)
7. **Content filter en evals:** los `eval` del navegador pueden bloquear devolver URLs/UUIDs/JWTs → devolver escalares (counts/longitudes/booleanos) y stashear el detalle a `localStorage`; exfiltrar el dataset final por descarga byte-exacta (verificar con hash).

**Prioridad de poster (universal):** `og:image`/CDN de primera fuente del festival **primero** (es el póster oficial) → TMDB vertical **solo con verificación visual humana** → editorial generado. *(Corrige el orden viejo "TMDB→og:image": la fuente del festival manda sobre TMDB.)*

Columnas del CSV — **clase organizador** (lo que solo el festival sabe):

| Columna | Qué es |
|---|---|
| `title` | título original (idioma de origen) |
| `title_es` | título en español si difiere del original (vacío si coinciden) |
| `type` | `film` · `event` · `short` |
| `director` | director(es) |
| `country` | país de producción (ej. `Argentina`, `Colombia`) |
| `language` | idioma original del film (ej. `Español`, `Portugués`) |
| `year` | año |
| `duration` | duración (ej. `147 min`) |
| `premiere` | estreno si aplica (`World Premiere` / `International Premiere` / `Estreno Nacional`); vacío si no lo es |
| `section` | sección curatorial |
| `flags` | bandera(s) del país (emoji) |
| `synopsis_source` | sinopsis en su idioma de origen (entrecomillar si tiene comas) |
| `synopsis_lang` | idioma de `synopsis_source` — default `es`; `pt`/`en` para festivales en otro idioma |
| `day` | clave de día (debe coincidir con `dayKeys`) |
| `date` | número de día del mes |
| `time` | hora 24h (ej. `17:00`) |
| `venue` | nombre exacto de la sede (clave de `venues{}`) |
| `has_qa` | `TRUE`/`FALSE` |
| `requires_registration` | `TRUE`/`FALSE` |

> Misma película con dos horarios = **dos filas** con igual `title`, distinto `day`/`time`/`venue`.
> Campos de **enrichment** (`poster`, `synopsis_en`, `lbSlug`, `genre`, `year` verificado) **NO** van en el CSV — se rellenan downstream (`enrich-festival.py` + verificación humana). El CSV captura solo lo del organizador.

1. Scraping de la web oficial del festival  
   - Campos obligatorios: `title`, `slug`, `section`, `type`, `director`, `country`, `year`, `synopsis`, `screenings`, `language`, `premiere`  
   - Campos deseables: `filmType`, `genre`, `duration`

2. **`poster` (og:image) — capturar desde el día 1**  
   URL patrón: `{festival-url}/films/{slug}` → leer `<meta property="og:image">`  
   Este campo nunca debe llegar vacío si la página del film existe.

3. Day keys en formato ISO `YYYY-MM-DD` — único formato aceptado desde Tribeca 2026 en adelante.

4. Secciones con emoji — cada sección recibe un emoji único antes del commit.

5. **Orden editorial de secciones** — el orden en que las secciones aparecen por primera vez en `films[]` define el orden de display en el Grid. Organizar el array con intención curatorial: secciones principales primero, eventos y shorts al final. Primera aparición = posición en el Grid.

**Gates de salida (bloqueantes):**
- [ ] Cero films sin `slug`
- [ ] Cero títulos en ALLCAPS (3+ palabras consecutivas en mayúsculas)
- [ ] `poster` ≥ 90% de films auditables
- [ ] `node scripts/validate-festivals.js` pasa con 0 errores antes de cada push — **sin excepciones**
- [ ] Cero funciones duplicadas (mismo título+día+hora). Múltiples funciones del mismo título en días distintos son **datos correctos, no duplicados**

---

### Fase 2 · Configuración en FESTIVAL_CONFIG `[Senior Dev + PM]`

**Objetivo:** El festival existe en la app con su configuración completa.

1. Crear entrada en `FESTIVAL_CONFIG` dentro de `index.html`:
   ```js
   'festival-id': {
     id: 'festival-id',
     name: 'Nombre completo',
     name_short: 'Nombre corto',
     city: 'Ciudad',
     country: 'XX',           // ISO-2, usado por flagFmt() para supresión de banderas
     storageKey: 'otrofestiv_festival_id',
     festivalEndStr: 'YYYY-MM-DDTHH:MM:SS',
     festivalDates: { 'YYYY-MM-DD': 'YYYY-MM-DD', ... },
     dayKeys: ['YYYY-MM-DD', ...],
     dayShort: { 'YYYY-MM-DD': 'MON D', ... },
     dayShort_en: { 'YYYY-MM-DD': 'MON D', ... },
     dayLong: { 'YYYY-MM-DD': 'Day, Month D', ... },
   }
   ```

2. El JSON del festival **no lleva bloque `config{}`** — nunca.

3. Emojis de sección aprobados por PM + Content Designer.

**Gates de salida (bloqueantes):**
- [ ] JSON sin `config{}`
- [ ] `storageKey` único (verificar contra todos los festivales)
- [ ] `festivalEndStr` presente y correcto
- [ ] `country` presente (necesario para `flagFmt`)

---

### Fase 3 · Enriquecimiento TMDB `[Data Engineer — algoritmo aprobado por Senior Dev]`

**Objetivo:** Poblar `genre` y `year` con datos verificados. **No poster. No synopsis_en.**

> ⚠️ **Lección aprendida (Tribeca 2026):** El algoritmo de matching usa `year` como criterio de validación. Si `year` viene corrupto del scraping (como ocurrió con 37 films de Tribeca), la validación falla silenciosamente y TMDB asigna datos de un film completamente distinto. `synopsis_en` de 64/107 films describía otra película. Ningún campo de TMDB puede considerarse verificado sin revisión humana previa.

**Algoritmo de matching estricto — los 4 criterios deben cumplirse simultáneamente:**

| Criterio | Regla |
|----------|-------|
| Título | Similitud > 0.6 con título TMDB o título original |
| Año | Diferencia ≤ 1 año (si ambos disponibles) |
| Director | Al menos un apellido coincide con crew[job=Director] |
| País | Al menos un país coincide con `production_countries` |

- Si algún criterio falla → el film queda **sin TMDB** (no se asigna ningún dato)
- Los rechazos se loguean para revisión manual
- Se consultan hasta 3 resultados de búsqueda por film antes de descartar
- Se prueban `movie` y `tv` en ese orden

**Campos aceptados de TMDB (solo si vacíos en el JSON):**
- `genre` → campo en el objeto film (si vacío) — error tolerable, no visible como dato crítico
- `year` → campo en el objeto film (si vacío) — solo si el año del scraping fue verificado primero

**Campos PROHIBIDOS desde TMDB sin verificación humana:**
- ❌ `poster` / `posters{}` → **NUNCA desde TMDB sin verificación visual manual**
- ❌ `synopsis_en` → **NUNCA desde TMDB sin verificación que describe el film correcto**
- ❌ `director`, `country`, `language` → solo desde el scraping de primera fuente

**Nota sobre match rate:**
- Match rate > 60% → sospechoso, el algoritmo puede ser demasiado permisivo
- Match rate < 20% → revisar algoritmo de búsqueda o datos de entrada

**Prerequisito obligatorio antes de correr TMDB:**
- Verificar que el campo `year` del scraping es correcto para una muestra de 10+ films
- Si hay World Premieres con year < año_del_festival - 1 → el scraping está corrupto, no correr TMDB

#### Posters TMDB — lecciones de Olhar de Cinema 2026

> Contexto: 11/14 clásicos matchearon al primer intento; 2 más (Wajda) se
> recuperaron buscando por título original; 1 (Salhab) se incluyó por override
> de transliteración. 13–14 de 14 con poster portrait verificado visualmente.

1. **Orden de búsqueda TMDB: original primero, luego EN.**
   Buscar por **título original** y *después* por `title_en`. **No descartar un
   film hasta haber intentado ambos.** El search en inglés rankea mal los títulos
   no-ingleses: para `Dyrygent` (Wajda) y `Ziemia obiecana` (Wajda), la búsqueda
   por "The Conductor"/"The Promised Land" devolvía films distintos (remake danés
   2024, film 2023); la búsqueda por el título polaco directo trajo el correcto.

2. **Override por transliteración.**
   Si el ÚNICO criterio que falla es el de **título**, y la causa es
   transliteración / caracteres no-latinos (árabe, cirílico, etc.), y los **otros
   3 criterios pasan** (año ±1, apellido director, país) **+ la verificación
   visual confirma el film correcto** → **override explícito permitido**.
   Documentarlo en el PR como `override: transliteración`. Ejemplo: *Ashbah
   Beyrouth* (Salhab) — título "Ashbah Beyrouth" vs TMDB "Beirut Phantom"/أشباح بيروت
   (sim 0.5), pero año/director/país exactos + poster confirma "un film de Ghassan
   Salhab". **No es un falso match** — es el film correcto con métrica de string
   inaplicable. (Sigue siendo override; nunca aplicar sin verificación visual.)

3. **Verificación visual — método Chrome tab (gate, no opcional).**
   Antes de escribir cualquier poster TMDB al JSON: crear un `gallery.html`
   temporal con los `poster_path` candidatos (`https://image.tmdb.org/t/p/w342{path}`)
   + título + director + año; servirlo con `python3 -m http.server <port>` desde
   `/tmp`; abrirlo en el Chrome tab; **confirmar visualmente que cada poster
   corresponde al film correcto y es portrait**; cerrar el server (`pkill -f
   "http.server <port>"`). Es el mismo nivel de gate que el snippet de Letterboxd.

4. **`poster_path` vs `backdrop_path` — usar SIEMPRE `poster_path`.**
   En TMDB, **`poster_path` es siempre portrait (2:3)** — el formato que el sistema
   espera. **`backdrop_path` es landscape (16:9). NUNCA usar `backdrop_path`.**
   Usar `poster_path` garantiza el aspecto correcto sin medir píxeles.

---

### Fase 3b · Letterboxd slugs `[Data Engineer — Chrome tab obligatorio]`

**Objetivo:** Poblar `lbSlugs{}` en el JSON del festival para que cada film muestre enlace a Letterboxd.

> ⚠️ **Regla absoluta:** Los slugs de Letterboxd NUNCA se infieren desde el título. El slug se extrae directamente del DOM de Letterboxd y se verifica individualmente. Inferir slugs produce errores silenciosos — un slug plausible puede apuntar a un film completamente distinto.

#### Paso 1 — Extraer slugs desde listas de Letterboxd

Buscar listas compiladas del festival (buscar en Google: `letterboxd list [nombre festival] [año]`).

Abrir cada lista en el Chrome tab y ejecutar este JS en cada página:

```js
// Extraer slug + título de todos los films en la página
Array.from(document.querySelectorAll('a[href*="/film/"]'))
  .map(a => {
    const m = a.href.match(/letterboxd\.com\/film\/([^/?#]+)/);
    const img = a.querySelector('img') || a.closest('li,div,article')?.querySelector('img');
    return m ? m[1] + '|||' + (img?.alt?.replace('Poster for ','') || '') : null;
  })
  .filter(Boolean)
  .join('\n')
```

Repetir para cada página de la lista (`/page/2/`, `/page/3/`, etc.).

#### Paso 2 — Verificar cada slug individualmente

**Este paso es obligatorio. Sin excepción.**

Para cada slug extraído, navegar a `https://letterboxd.com/film/SLUG/` y verificar:
```js
document.title
// Debe contener: "Título (año) directed by Director"
```

Comparar director y año contra los datos del JSON del festival. Si no coinciden → el slug es incorrecto, buscar el correcto.

**Casos frecuentes de error:**
- Films con títulos genéricos (`Cotton Fever`, `Harvest`, `Funk`) tienen múltiples páginas en LB con sufijos (`-1`, `-2026`, etc.)
- Films de retrospectiva usan el slug del año original, no el año del festival
- El título en LB a veces difiere del título en el programa (ej: `Billy Joel - The Last Play at Shea` vs `The Last Play at Shea`)
- Films que son World Premieres pueden no tener página en LB todavía — dejar sin slug

#### Paso 3 — Insertar en el JSON

```python
with open('festivals/festival-id.json') as f:
    d = json.load(f)

d['lbSlugs'] = {
    "Título exacto del film": "slug-verificado",
    # ...
}

with open('festivals/festival-id.json', 'w') as f:
    json.dump(d, f, ensure_ascii=False, indent=2)
```

La clave del dict es el `title` exacto del film en el JSON (case-sensitive, apóstrofes incluidos).

**Gates de salida:**
- [ ] Cada slug fue visitado y verificado (director + año)
- [ ] Competencias principales: cobertura 100%
- [ ] 0 slugs inferidos sin verificación

---

### Fase 4 · Validación automática `[automatizado — validate-festivals.js]`

```bash
node scripts/validate-festivals.js [festival-id]
```

**Gates bloqueantes (exit code 1 = no se hace push):**
- `config{}` presente en el JSON
- Título con 3+ palabras en ALLCAPS
- Cobertura de poster = 0%

**Warnings (no bloquean pero requieren revisión antes del deploy):**
- Cobertura de poster < 95%
- Cobertura de género < 80%
- Duración ≤ 0 o > 400 min
- Venue vacío
- `is_cortos: true` sin `film_list`
- Emoji de sección duplicado (salvo retrospectivas)

---

### Fase 5 · Revisión de roles `[Content Designer · UX Designer · PM]`

**Content Designer:**
- [ ] Títulos en formato correcto (sin ALLCAPS, sin errores tipográficos)
- [ ] Sinopsis en ES revisadas (longitud, tono, coherencia)
- [ ] Géneros en español y consistentes con el catálogo
- [ ] Emojis de sección aprobados

**UX Designer:**
- [ ] Posters correctos en el contexto real de la UI (editorial vs portrait vs generativo)
- [ ] Secciones con sección-color coherente
- [ ] Ningún film con layout roto

**PM:**
- [ ] Informe de cobertura aprobado (poster %, género %, sinopsis %)
- [ ] Sign-off explícito antes del primer deploy público

---

### Fase 6 · Deploy `[Senior Dev]`

1. Push a `main` con commit semántico que incluya métricas de cobertura:
   ```
   feat(festival): festival-id — N films, poster X%, género X%, sinopsis X%
   ```
2. Bump de versión SW para forzar cache refresh en todos los clientes
3. Verificación en dispositivo iOS real (Safari) antes de anunciar

---

## Reglas inmutables

| Regla | Detalle |
|-------|---------|
| `config{}` prohibido en JSON | La configuración vive en `FESTIVAL_CONFIG` en `index.html` siempre |
| Matching TMDB estricto | Los 4 criterios simultáneos — pero solo válido si los datos de entrada fueron verificados primero |
| TMDB para poster: prohibido | `posters{}` solo desde verificación visual humana — nunca automatizado |
| TMDB para synopsis_en: prohibido | synopsis_en solo desde traducción manual o fuente verificada — 64/107 de Tribeca eran de films distintos |
| `og:image` en fase 1 | Se captura en extracción, no como parche posterior |
| Day keys ISO | `YYYY-MM-DD` desde Tribeca 2026. Los festivales legacy mantienen su formato pero no se replica |
| Validate antes de push | `validate-festivals.js` no es opcional. Un push que falla se revierte |
| Arquitectura antes de ejecución | El algoritmo de matching, la prioridad de posters y el schema de datos se aprueban antes de implementar |
| Cero decisiones de arquitectura en ejecución | El Data Engineer no decide el criterio de matching — lo aprueba el Senior Dev antes de correr el script |

---

## Deuda técnica por festival

| Festival | Género | Poster | Sinopsis ES | Pendiente |
|----------|--------|--------|-------------|-----------|
| FICCI 65 | 37% | 74% | 75% | Verificar year del scraping antes de TMDB |
| Cinemancia 2025 | 93% | 95% | 100% | — |
| AFF 2026 | 100% | 100% | 100% | — |
| Tribeca 2026 | 93% | 44%* | 90% | *poster: solo cloudfront verificado. TMDB requiere verificación visual |

*Tribeca: 134 cloudfront (tribecafilm.com primera fuente) + 87 poster editorial. TMDB vaciado hasta verificación humana.

---

## Historial de errores — para no repetir

| Error | Impacto | Fix aplicado |
|-------|---------|-------------|
| TMDB sin validación (round 1) | 134 posters falsos ("The Leader" → "The Leader and the Band") | Algoritmo estricto con 4 criterios |
| TMDB con año corrupto (round 2) | 107 synopsis_en de films distintos (64 confirmados). Año corrupto en 37 films dejó el validador ciego | TMDB prohibido para poster y synopsis_en. Verificación de year del scraping como prerequisito |
| Scraping incompleto de imágenes | 29 films sin poster a pesar de tener og:image en la web | og:image en fase 1 obligatorio |
| `config{}` en JSON | Configuración ignorada silenciosamente por el engine | Gate bloqueante en validator |
| Títulos en ALLCAPS | ALEJANDRO SANZ, MOUTH FULL OF GOLDS visibles en producción | Gate bloqueante en validator |
| `synopsis_en` de TMDB sin validar | Sinopsis de films incorrectos aparecen en la UI | Misma validación estricta que posters |
| lbSlugs inferidos desde título | Slugs plausibles apuntando a films distintos (ej: `cotton-fever-1` existía pero era otro film; `ascension-2026` no existía; `against-the-flow` era un film diferente al de Tribeca) | Método Chrome tab obligatorio: extraer del DOM de listas LB + verificar cada URL individualmente |
