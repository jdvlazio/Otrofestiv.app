# POSTERS.md — regla única de pósters

> **Fuente única de verdad para todo lo de pósters.** Antes las reglas vivían
> dispersas y **contradictorias** entre `PIPELINE.md`, `FESTIVAL-CHECKLIST.md` y
> `SCHEMA.md` (ej. "festival primero" vs "TMDB primero"). Eso hacía que los
> pósters editoriales fueran el dolor de cabeza recurrente al montar festivales.
> Esos documentos ahora **apuntan acá**. Si algo de pósters no está claro, la
> respuesta está en este archivo — y solo acá se edita.
>
> Reglas operativas del runtime: `getFilmPoster` / `getCortoItemPoster`
> (`src/view/helpers.js`), generadores `_buildPosterV16` / `makeProgramPoster` /
> `makeEventPoster` / `makeSorpresaPoster` (`src/view/components.js`).

---

## 0. Principio rector

**Identidad primero, después aspecto.** Un póster malo no es solo feo: si es de
**otro film** (lección Tribeca: 134 pósters falsos por matching TMLB a ciegas) o
si rompe el render (XML malformado → `naturalWidth 0`), el daño es silencioso.
Por eso:

1. **La imagen debe ser del film correcto.** La fuente propia del festival
   (og:image / CDN oficial) tiene identidad **garantizada por construcción**.
   TMDB y Letterboxd **NO** se toman a ciegas: requieren **verificación visual
   humana** antes de escribirse.
2. **Entre imágenes de identidad correcta, se prefiere el formato portrait 2:3**
   (es el formato nativo del sistema). El landscape 16:9 no se descarta: se
   renderiza dentro del marco editorial (editorial-con-imagen).
3. **Ningún film/corto se queda sin imagen si existe una.** `poster: ""` es
   exclusivo de programas y es el último recurso real.

---

## 1. Modelo de datos

Dos formas de guardar el póster de un film. **La inline es la canónica** para
festivales nuevos.

| Modelo | Forma | Festivales |
|---|---|---|
| **Inline (canónico)** | campo `poster` en cada film | Leviza, Olhar, Tribeca, FICMontañas, Jardín+ |
| **Map (legacy, soportado)** | `posters{}` / `customPosters{}` a nivel raíz, **clave = título** | FICCI, AFF, Cinemancia |

- **`poster`** (inline): URL completa (`https://…`), path de assets propios
  (`/assets/<id>/slug.png`) o path TMDB (`/abc.jpg`). La resolución:
  `startsWith('http') || startsWith('/assets/')` → directo; si no → `TMDB_IMG + path`.
- **`posters{}` / `customPosters{}`** (map): la clave es el **título
  apóstrofe-normalizado** (`normKey` — solo unifica variantes de apóstrofe
  `‘’‚‛′ʼ` → `'`). `customPosters` gana sobre `posters`.

`normKey` es lo único que normaliza la clave — no hay lowercasing ni strip de
acentos. El título del film y la clave deben coincidir salvo por el apóstrofe.

---

## 2. Árbol de decisión de adquisición (qué imagen guardar)

Para **cada film individual** (incluidos los cortos dentro de `film_list`),
recorrer en orden y **parar en la primera que aplique**:

| # | Fuente | Formato | Condición | Resultado |
|---|---|---|---|---|
| 1 | **TMDB `poster_path`** | portrait 2:3 | **verificación visual** ✔ (es el film correcto) | `poster: "/path.jpg"` |
| 2 | **Letterboxd og:image** | portrait 2:3 | **verificación visual** ✔ (no el placeholder `empty-poster`) | `poster: "<url>"` |
| 3 | **Portrait oficial** del festival | portrait 2:3 | identidad garantizada; si viene dentro de un diseño → **§3 trim** | `poster: "/assets/<id>/slug.png"` |
| 4 | **Landscape oficial** (CDN cloudfront/supabase) | 16:9 | identidad garantizada | `poster: "<url>"` → editorial-con-imagen |
| 5 | **Editorial sin imagen** | generativo | **no existe imagen en ninguna fuente** | `poster: ""` *(solo programas, ver §6)* |

**Por qué este orden (y cómo resuelve la vieja contradicción):** TMDB/LB están
arriba **solo porque son portrait** (mejor aspecto), pero están **condicionados a
verificación visual** — ese es el candado de la lección Tribeca. La fuente del
festival está más abajo en aspecto pero su **identidad nunca necesita
verificarse**: por eso es el respaldo seguro. El viejo "la fuente del festival
manda sobre TMDB" exageraba; lo que realmente quería decir es **"nunca tomes
TMDB/LB a ciegas por encima de la imagen conocida-correcta del festival"**. Esta
tabla captura ambas lecciones en un solo orden.

- **`poster_path`, nunca `backdrop_path`.** En TMDB `poster_path` es siempre
  portrait 2:3 (lo que el sistema espera); `backdrop_path` es landscape — **jamás
  usarlo**.
- **Búsqueda TMDB con título original Y `title_en`** antes de descartar.
- El landscape (#4) **no se vacía** a editorial-sin-imagen: eso pierde la imagen.
  Va en `poster` y se renderiza dentro del marco editorial (§5 / §7).

---

## 3. Paso obligatorio — recorte a 2:3 limpio (bar-trim)

Los afiches del sitio oficial suelen venir **dentro del diseño del festival**
(márgenes blancos, branding, barras negras de centrado). Esos **no se suben tal
cual**. Antes de hospedarlos:

1. **Trim de relleno**: recortar **blanco Y negro** del borde (un trim que solo
   quita blanco deja barras negras — caso Chiribiquete FICMontañas).
2. **Crop a 2:3 limpio**: encuadrar el afiche real. *No importa si se recorta a
   los lados* — el objetivo es que se vea **como el póster original**, sin el
   diseño del festival alrededor.
3. **Hospedar** en `assets/<id>/slug.png` y apuntar `poster: "/assets/<id>/slug.png"`.

> Regla de Juan: **"no subas pósters con el diseño del festival, sino recortados,
> como si fuera el original."** Verificación visual obligatoria tras el trim.

---

## 4. Resolución en runtime (`getFilmPoster`)

Cómo el dato guardado se convierte en imagen (orden real, `helpers.js`). Útil
para entender por qué un film cae a generativo:

1. `customPosters[normKey(title)]` — siempre primero.
2. **Evento** (`type:'event'`) → `f.poster` o `makeEventPoster` (ámbar generativo).
3. **Sorpresa** (título contiene "sorpresa") → `makeSorpresaPoster`.
4. **Cortos** (`is_cortos`) → `f.poster` → `getPosterSrc` → `makeProgramPoster`.
5. **Programa** (`is_programa` + `film_list`) → `film_list[0].poster` → … → `makeProgramPoster`.
6. **`posters[normKey(title)]`** (map TMDB) — **prioridad sobre el editorial inline**.
7. **`f.poster` directo** — editorial-con-imagen (landscape) o assets propios.
8. **Generativo** `_buildPosterV16` — fallback final.

> Nota: el map `posters{}` (#6) se resuelve **antes** que `f.poster` (#7). Si un
> film tiene ambos, gana el map. En festivales inline modernos no hay map → manda
> `f.poster`.

---

## 5. Detección de editorial-con-imagen (HÍBRIDA + fail-safe)

Un `poster` landscape se renderiza **dentro** del marco editorial (banda de
sección + imagen) en vez de como póster completo. La detección vive en **un solo
lugar**, `_isEditorialPoster(f)` (`helpers.js`), y es **híbrida** con default
seguro:

1. **`posterSource` explícito gana** — `'editorial'` → sí; `'tmdb'`/`'custom'` → no.
   Es la forma robusta y recomendada para festivales nuevos.
2. **Si hay póster TMDB validado** (clave en el map `posters{}`) → no (es portrait,
   no 16:9).
3. **Si no, auto por host CDN** — `_isEditorialImageUrl(url)` contra
   **`EDITORIAL_CDN_HOSTS`** (`['cloudfront.net','supabase.co']` — Tribeca, Olhar+).
   **Añadir un CDN nuevo = una línea** en esa constante.

**Default fail-safe:** lo que no tiene señal (ni `posterSource` ni host conocido)
cae a **NO-editorial** → `posterModel` lo trata como `image`. Nunca se asume
editorial por adivinanza, así que jamás se mete a la fuerza un 16:9 en un marco
que no le toca. El precio: un landscape en un CDN desconocido sin `posterSource`
se renderiza como portrait recortado — el fix correcto es declarar
`posterSource:'editorial'` (contrato §1) o añadir el host.

---

## 5b. Render: modelo único + builder único

Un solo camino para pintar cualquier póster — los call sites NO re-derivan flags:

- **`posterModel(f)`** (`helpers.js`) → unión discriminada `{kind, …}` con
  `kind ∈ {image, editorial, generative, empty}`. Es el **único** lugar que
  clasifica (usa `getFilmPoster` + `_isEditorialPoster`). `generative` se detecta
  por el prefijo data-URI; el default es `image` (fail-safe, §5).
- **`editorialFrame({header, body, src, title, loading})`** (`helpers.js`) → el
  **único** builder del marco editorial-con-imagen. Devuelve los **hijos**
  (`.ed-hdr` + `.ed-img` + `.ed-body`); el **contenedor** aporta tamaño y color
  vía la clase **`poster-ed`** + `style="--ed-accent:…"`. `body`: `undefined`
  omite la zona (thumb/sheet), `''` reserva zona vacía (ended-poster), con texto
  pone el título (grid).
- **CSS `.poster-ed`** (`index.html`) — **un** componente; el alto de la banda es
  `var(--ed-hdr-ratio)` (una fuente, antes `28.89%` hardcodeado en CSS y JS).
- **`onerror` unificado** — los marcos editoriales usan **`_edPosterErr`**
  (`poster-err.js`): si la imagen falla, reemplaza **toda** la pieza por un póster
  generativo (no deja la banda con hueco).

Sustituye las **7 copias bespoke** del marco que habían divergido (grid · sheet ×3
· lista · thumb · agenda). Antes: 2 modelos de datos + el marco reescrito a mano
en cada superficie + `28.89%` en 4 sitios + escape XML local frágil.

---

## 6. Pósters editoriales generativos (`_buildPosterV16` y derivados)

Cuando no hay imagen, el sistema genera un póster tipográfico (SVG data-URI).
Dos zonas: **header** = sección (color de acento) y **body** = texto.

### 6.1 Escape XML — fuente única `escXML`

Todo texto de usuario que entra a un `<text>` SVG **debe** pasar por
**`escXML`** (`components.js`) — la **única** función de escape. Escapa `& < > "`
(el `&` primero, para no re-escapar). Un `&`/`<`/`>` crudo produce XML malformado
→ el navegador descarta la imagen (`naturalWidth 0`) → póster roto **silencioso**
(regresión real: "Opening & Galas", "Recorrido en Bicicleta").

- Guardarraíl: `tests/unit/poster.test.js` corre los 4 generadores con entradas
  adversarias (`&`, `<`, `>`, `"`, emoji, vacío) y exige XML bien formado.
- **No** crear helpers de escape locales (`const esc=t=>t.replace(...)`) — eran la
  causa de la fragilidad. Reusar `escXML` (lo hace `_edHdrSVG` en `helpers.js`).

### 6.2 Body de pósters de programas — REGLA INAMOVIBLE

`is_cortos` / `is_programa` sin póster propio → `makeProgramPoster`:

1. **El body es el identificador único del programa, nunca el descriptor de
   sección suelto.**
   - **Numerados** (`PGM 01`, `Prog. 4`…): body = el **código** (`PGM 05`),
     extraído del **título** (`f.title`), no de la sección.
   - **Con nombre propio** (retrospectivas, sesiones especiales, combinados):
     body = el **nombre propio**, tal cual el título original.
2. **El texto sale del título original (`f.title`)**, nunca de la traducción de UI
   (`f.section` solo aporta el color). Así no se mezclan idiomas.
3. **Todo programa produce un póster único** — lo blinda el check
   `[poster-editorial-unique]` (corre el `makeProgramPoster` real sobre cada
   programa y falla si dos coinciden). **ERROR, sin falsos positivos.**

---

## 7. `poster: ""` — exclusivo de programas

`poster: ""` (editorial **sin imagen**) es **exclusivo de programas**
(`is_cortos` / `is_programa`) sin póster propio, y solo cuando **no existe ninguna
imagen en ninguna fuente**. Último recurso, nunca el segundo.

- **NUNCA** en films individuales ni cortometrajes sueltos: si tienen cualquier
  imagen (aunque sea landscape) va en `poster` (editorial-con-imagen, §2.4).
- Lo blinda el check **`[poster-empty-film]`** (`validate-festivals.js`): un film
  no-programa/no-cortos con `poster: ""` y sin clave en `posters{}`/`customPosters{}`
  es **ERROR**. La intención correcta es imagen real o **omitir el campo** — nunca
  string vacío.

---

## 8. Gates de validación (pre-commit)

`node scripts/validate-festivals.js <id>` → **0 errores**. Checks de pósters:

- **Cobertura ≥ 95 %** — un film cuenta como cubierto si `f.poster` no vacío **o**
  su título (normKey) está en `posters{}`/`customPosters{}`. (El cálculo viejo
  ignoraba `customPosters{}` → FICCI reportaba 63 % siendo 100 %.)
- **`[poster-source]`** (ERROR) — un poster inline **sin `posterSource`**. Obliga a
  correr el clasificador por aspecto (abajo) — así ningún landscape se cuela como
  portrait recortado. La detección editorial deja de depender del host (§5.3);
  `posterSource` explícito manda (§5.1).
- **`[poster-host]`** (WARNING) — poster http fuera de la whitelist
  (`image.tmdb.org` · `d13jj08vfqimqg.cloudfront.net` · `*.supabase.co`). Fuentes
  frágiles (hotlink bloqueado, links muertos) → **descargar y re-hostear en
  `/assets/<id>/`**. Regla de hosting: **2 fuentes** — TMDB (portrait, se
  referencia) + `/assets/` (todo lo demás, incluidas stills 16:9 re-hosteadas).
- **`[poster-empty-film]`** — §7.
- **`[poster-editorial-unique]`** — §6.2.

> **Clasificador de aspecto — `scripts/classify-posters.py`** (paso de onboarding):
> descarga cada poster, mide el aspecto real y escribe `posterSource` en cada
> film/corto (`editorial` si landscape ≥ 1.2, si no `tmdb`/`custom`). Caza rotos
> (403/404) al montar, no en producción. `--apply` escribe; sin flag = dry-run.
> Reemplaza la detección frágil por-host: el runtime ya honra `posterSource`
> primero. **Correrlo en cada festival nuevo** — el gate `[poster-source]` lo exige.
- **Binding por id** — si el CDN/og:image embebe el id del film en el path,
  confirmar `poster.includes(filmId)` (caza stale-render — lección Tribeca).
- **Verificación visual** (galería Chrome) — obligatoria antes de escribir TMDB/LB.

---

## 9. Resumen de un vistazo

- Identidad antes que aspecto. TMDB/LB **solo verificados**; festival = identidad segura.
- Portrait 2:3 preferido; landscape oficial → editorial-con-imagen (no se vacía).
- Afiches con diseño del festival → **trim blanco+negro → 2:3 → `/assets/<id>/`**.
- `poster: ""` solo programas, último recurso.
- Editorial generativo: **todo** texto por `escXML`; body de programa = identificador único.
- Render: **`posterModel(f)`** clasifica (un lugar) → **`editorialFrame()`** + clase
  **`.poster-ed`** pintan el marco (un builder, un CSS, `--ed-hdr-ratio`); `onerror`
  editorial = `_edPosterErr` (cae a generativo). Detección híbrida (`posterSource`→host) con fail-safe.
- Gates: cobertura ≥95 %, `[poster-empty-film]`, `[poster-editorial-unique]`, binding por id, visual.
