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

**Un film = un `poster` inline. Fuente única, sin excepciones.** El modelo dual
`posters{}` / `customPosters{}` a nivel raíz **murió** (Fase A.1): los 7
festivales se migraron a inline (`scripts/migrate-posters-inline.py`) y el gate
**`[poster-map-legacy]`** bloquea cualquier map que reaparezca.

- **`poster`** (inline): URL completa (`https://…`), path de assets propios
  (`/assets/<id>/slug.png`) o path TMDB (`/abc.jpg`). La resolución:
  `startsWith('http') || startsWith('/assets/')` → directo; si no → `TMDB_IMG + path`.
- **`posterSource`** (inline, junto al `poster`): `'editorial'` | `'tmdb'` |
  `'custom'`. Es la **señal explícita** que decide el render (§5); lo escribe el
  clasificador por aspecto (`scripts/classify-posters.py`) y lo exige el gate
  `[poster-source]`. Un poster inline sin `posterSource` es ERROR.

> Legacy: `getFilmPoster` conserva el paso del map (§4 #6) por compatibilidad,
> pero **ningún festival tiene map** — ese paso es código muerto defensivo.

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
   Es la forma robusta y recomendada, y hoy la de **todos** los festivales (el
   clasificador lo escribió en cada film; el gate `[poster-source]` lo exige).
2. **Si no, auto por host CDN** — `_isEditorialImageUrl(url)` contra
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
- **`editorialFrame({header, body, src, title, loading, accent, dato, firma})`**
  (`helpers.js`) → el **único** builder del marco editorial-con-imagen (Forma B
  §6.0 = Forma A + un campo 16:9 constante). Devuelve los **hijos**; el
  **contenedor** aporta tamaño y color vía la clase **`poster-ed`** +
  `style="--ed-accent:…"`.
- **Anatomía §6.0 del marco** — respeta el **16:9 completo** (el cover-crop
  decapitaba composiciones con gente a los lados). La geometría vive en el CSS
  de `.poster-ed`, en %:
  - `.ed-fil` — el filete de sección de 0,25u a sangre (color de sección).
  - `.ed-hdr` — la sección tipografiada (`_edHdrSVG`, mismo motor de ajuste).
  - `.ed-halo` — la propia obra desenfocada llenando el vacío bajo el campo,
    contenida y con máscara (no es el blur a sangre que mató §6.0). En la
    miniatura va bajo el campo centrado; en el póster grande ancla al borde del
    campo (66,67%, `.ed-halo-full` — 24 ago 2026: la línea negra bajo el still
    «genera distancia y ruido»).
  - `.ed-img` + `.ed-still` — el still **16:9 sin recortar**; `.ed-img-mid`
    centra el campo en la miniatura (corto dentro de programa, sin sección ni
    título). El still lleva `data-title` y `onerror` → `_edPosterErr`.
  - `.ed-foot` — el pie: `.ed-title` (solo cuando `body` trae texto — grid;
    thumb/sheet muestran el título aparte), `.ed-firma` (curatorial, itálica,
    solo junto al título) y `.ed-dato` (gris, 5%).
  - Muertos y enterrados: `.ed-blur` (blur a sangre), `.ed-scrim` (degradado
    con título encima del still) y `.ed-body`. Si aparecen en código nuevo, es
    regresión.
- **CSS `.poster-ed`** (`index.html`) — **un** componente; el alto de la banda es
  `var(--ed-hdr-ratio)` (una fuente, antes `28.89%` hardcodeado en CSS y JS).
- **La Forma B es de la MISMA FAMILIA que la A** (24 ago 2026): mismo **suelo**
  (negro de marca `--bg`) y misma **luz** de sección. Dos trampas, las dos
  visibles solo EN PANTALLA:
  1. El marco **pinta su propio suelo** —es el póster, no un contenedor de
     `<img>`—, pero la card del grid llega con `bg-surf-2 … poster-ed` y
     `.bg-surf-2` **gana la cascada** (misma especificidad, ~1950 líneas más
     abajo). Por eso la regla del suelo va con la clase repetida
     (`.poster-ed.poster-ed`). La Forma A nunca lo sufrió: su `<img>` SVG tapa
     el fondo del contenedor.
  2. La luz **hereda `--ed-accent`** (que el contenedor ya trae). Estuvo ámbar
     fija mientras la Forma A ya heredaba el acento → una pared con las dos
     formas mezclaba ámbar entre colores de sección.
  Guardián: **T105**, que MIDE estilos computados. Un check estático del CSS
  habría dado verde con el bug puesto: la regla correcta existía, solo perdía.
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

### 6.0 Anatomía del póster nuestro — APROBADA (18 ago 2026, Juan)

> Aprobadas **las dos formas**: solo texto, y **una sola imagen 16:9**.
> Rationale y descartes en `.specify/design-system/posters-c2-reticula.md`.

**Solo hay dos formas. La regla que decide es una:**

```
¿la función tiene UNA imagen 16:9 propia?
   sí  → forma B (una imagen)
   no  → forma A (solo texto)
```

**«Propia» significa de la obra misma.** Un programa de cortos **no** toma
prestada la imagen de una de sus obras: elegir un fotograma de las nueve para
representar a las nueve es curaduría nuestra sobre curaduría ajena. Un programa
sin still propio es **forma A**.

**Nunca varias imágenes** (decisión de Juan, 18 ago 2026). Mosaicos, escalonados
y tiras de índice quedan descartados: a 84 px son ruido, no información.

**Nunca una imagen que no sea 16:9.** Un póster vertical 2:3 de una obra no se
mete en el campo — eso sería recortarlo. Esa función es **forma A**.

**El problema que corrige.** El tamaño de la sección estaba atado a una
constante del ancho (`_BAND_FS = 0.0542`) y la banda a un alto fijo (28,89%).
En la tarjeta real de 84 px eso da **una losa de 36 px con letra de 4,55 px**:
la banda nunca se llena, y da igual que el nombre sea corto o largo. Fuera de
los festivales con stills, *casi todos* nuestros pósters son de solo texto —
24 funciones en FICDEH, 7 en FINCA— así que ahí la tipografía no decora: es el
póster entero.

**Retícula.** El póster es 2:3, así que la unidad cuadra sin residuo:

```
u = ancho / 8        →  el póster es 8u × 12u (módulos cuadrados)
línea base           =  media unidad (24 líneas)
margen               =  0,75u  →  caja de contenido 6,5u
filete de sección    =  0,25u de alto, a sangre, en color de arquetipo
```

**Anatomía.** Sobre fondo `#0A0A0A` (el negro de la marca — el mismo de los
slides de social media, **no** `#141414`):

| elemento | posición | tamaño |
|---|---|---|
| filete de sección | `y = 0` | `0,25u`, a sangre |
| sección | `y = 1u` | la mayor que quepa en `6,5u × 3,4u`, máx. 3 líneas |
| título | anclado abajo, sobre `11,25u` | la mayor que quepa en `6,5u × 2,4u`, máx. 4 líneas |
| dato | bajo el título | `5% del ancho`, gris `#888` |
| luz | esquina inferior **derecha** | glow radial ámbar `#F59E0B` |

**La regla que lo hace funcionar: la tipografía se ajusta al ESPACIO, no a una
constante.** El corte de línea se decide por **ancho medido**, nunca por número
de caracteres (partir por caracteres dejaba el título en una sola línea
minúscula). En producción el ajuste se calcula en el `viewBox` del SVG —
determinista, sin medir el DOM.

Resultado medido en la tarjeta de 84 px:

```
                   hoy       aprobado
CineAutopsia      4,5 px     11,4 px
FICDEH            4,5 px     15,0 px
FINCA             4,5 px      8,5 px
esfuerzo (43 car) 4,5 px      9,2 px  ← «Retrospectiva 10 Años del Acuerdo de Paz»
```

La prueba de esfuerzo entra legible en tres líneas **sin tocar el nombre que
puso el festival**: la regla de que las secciones no se renombran (§ vocabulario)
queda intacta.

**El color de sección deja de ser una losa** y pasa a ser el filete superior más
el color de la propia tipografía de la sección. Se conserva porque es la señal
que se lee de un vistazo al hacer scroll.

**La luz va abajo a la derecha**, no abajo a la izquierda como en los slides de
Instagram: en el póster esa esquina la ocupa el título.

**Sin chevron.** A 84 px se leía como suciedad y competía con la luz por la
misma esquina.

El corte de línea sigue siendo `_bandWrap` (ninguna línea, salvo la última,
termina en conjunción, preposición, artículo o separador).

#### La MINIATURA es su propia forma (19 ago 2026, Juan)

Un corto dentro de un programa se dibuja con el marco editorial pero **sin
sección ni título** — los dice la fila de al lado. Con la anatomía de arriba tal
cual, esa miniatura queda hueca: el hueco que en el póster grande llenan título
y dato, acá no lo llena nadie. Reglas propias, y solo para ella:

- **El campo se centra** (`y = 3,75u` en vez de `3,5u`): el vacío se reparte.
- **Halo en el pie**: la propia obra desenfocada bajo el campo (`blur 10px`,
  `opacity .55`), apagada con máscara antes del borde. Se lee como calor, no
  como imagen. El primer valor probado —`.38`— se veía en el mockup y **no en
  la app**: a 56×84 el pie seguía leyéndose negro. Se mide en la superficie
  real, no en el banco de pruebas.
- **El filete va en ámbar de marca**, no en color de sección: los cortos de un
  programa comparten sección, así que ese color no informa nada — y sin
  arquetipo caía al gris `#2C2C2A`, que fue lo que se veía: una barra gris
  repetida siete veces.

**Esto NO revive el blur que §6.0 mató.** Aquel iba *detrás* del still, a
sangre, y ensuciaba el negro de marca compitiendo con la imagen. Este está
contenido bajo el campo, con máscara, y solo donde hay vacío: en la tapa
—con sección y título— no se emite. La diferencia está fijada por test.

Costo medido: **un `<img>` extra por miniatura, con el MISMO src** — el
navegador lo reusa de su cache, así que son 7 elementos más en la ficha de un
programa de 7 cortos y **cero descargas nuevas**.

#### Lo que cambió al implementar (19 ago 2026) — la spec se corrige con lo medido

La anatomía se implementó tal cual, con cuatro ajustes que salieron de MEDIR el
texto ya renderizado (`getBBox`) en la tarjeta real. Se documentan acá porque
esta sección es la fuente única y las cifras de arriba salían de un mockup:

- **El negro es `#0B0A08`, no `#0A0A0A`.** El guardián `[warm-neutrals]` marca
  `#0A0A0A` como paleta fría vieja: la app migró a negros cálidos. A la vista son
  el mismo negro; la regla del design system manda.
- **La sección admite 4 líneas, no 3** (decisión de Juan). Con 3 líneas, el caso
  de esfuerzo daba **6,4 px**; con 4 da **7,7 px**, un 20% más.
- **Los 9,2 px del caso de esfuerzo NO son alcanzables.** «Retrospectiva 10 Años
  del Acuerdo de Paz» son 39 caracteres; para dar 9,2 px en una tarjeta de 84 px
  cada línea podría tener 12 caracteres y 3×12 = 36 < 39. El techo aritmético con
  el margen de 0,75u es 7,7 px. Ensanchar la caja a 7,5u tampoco alcanza (7,5 px)
  y además desbordaba. El número del mockup no medía el texto renderizado.
- **Tope de 15 px para la sección** (decisión de Juan). «La mayor que quepa» sin
  techo llevaba «CHARLA» a 17,9 px — más grande que el título de la obra.

**Las dos reglas de margen son duras y están verificadas** (T98): ningún texto
cruza `x = 108,75` ni `y = 168,75` del viewBox (0,75u). Dos hallazgos:

- El dato apoyaba su línea base EN el margen y las colas de «g»/«p» se salían:
  la base sube 0,30 em.
- «Competencia Nacional de Cortometrajes» no tiene arreglo por tamaño: la regla
  de corte prohíbe dejar «de» al final de línea, así que «DE CORTOMETRAJES»
  viaja pegado y son 16 caracteres donde caben 14. Se resuelve con `textLength` +
  `lengthAdjust="spacingAndGlyphs"`, que condensa ESA línea unos puntos hasta el
  ancho exacto. Solo se activa cuando el corte no puede evitar el desborde.

**El estimador de ancho se calibra con `getBBox`, no con `canvas.measureText`**:
ahí el bold sintetizado mide de menos y el primer intento subestimaba hasta un
19% («CHARLA» real da 0,739 em/carácter). Se usa 0,66 de promedio con factor de
seguridad 1,12 — el error del estimador no es simétrico: pasarse se VE.

#### Forma C — FUNCIÓN COMPARTIDA: la Escalera (21 ago 2026, Juan)

Una **función compartida** (Tipo 2 del template: obras independientes que
comparten día·hora·sede, ancladas por `_slotKey`) no tenía póster propio en
ninguna superficie: la grilla y la lista muestran cada obra con su card, y la
única representación de la función como unidad es el bloque de texto del
calendario semanal. La Escalera le da forma: **los afiches de las obras,
apilados en diagonal dentro del póster nuestro**.

**Geometría — RIMA 2:3** (viewBox 120×180, `u=15`; revisada 25 ago 2026, Juan).
El desplazamiento entre módulos es **paralelo a la diagonal del marco**:

> **dy = 1,5 · dx**

y con eso el rectángulo que envuelve a la pila mide exactamente 2:3 — la misma
proporción del marco y la de cada afiche, tres 2:3 anidados. La demostración es
de una línea, y vale para cualquier N:

> alto = 1,5w + (N−1)·1,5dx = 1,5·(w + (N−1)dx) = 1,5 × ancho

Una sola perilla, `k = dx / ancho del envolvente`:

| | 2 obras | 3 obras |
|---|---|---|
| k | 0,30 | 0,235 |
| envolvente | de `y=1,5u` a `y=VH−M−1,6·datoFS`, centrado en x | ídem |
| módulo | ≈ 4,25u de ancho | ≈ 3,6u |

Con más solape el de atrás se lee como sombra del de adelante y se pierde la
pluralidad; con menos, sobra campo. **El ÚLTIMO módulo va al frente** y su
sombra (dura, 0,19u) cae sobre el anterior: con el primero al frente la sombra
cae en campo vacío y la pieza se aplana.

Afiches 2:3 **completos**, nunca recortados, con el radio del token (13% del
ancho del módulo) y un **passe-partout** cálido de 0,5 — sin él un afiche
oscuro se disuelve en el negro de marca y la tarjeta parece rota.

**La luz va abajo a la IZQUIERDA**, que es el triángulo que deja libre la
diagonal. En su posición canónica (abajo-derecha, §6.0) queda tapada por el
módulo delantero y no ilumina nada. Es una excepción deliberada de esta forma;
no se "corrige" de vuelta.

Sustituye a la geometría de pasos fijos del 21 ago, que reservaba 3u arriba
para el rótulo de sección.

**SIN TÍTULO interno** (decisión de Juan): *«en una película con póster nunca
vemos títulos»*. Se auditaron las cinco superficies antes de quitarlo: en lista,
ficha, Intereses, Mi Plan y buscador el título ya vive **al lado** del póster —
era duplicado; y en grilla y Diario **ninguna obra se nombra**, así que la
identidad queda a un tap, igual que para cualquier película. Se conserva **el dato al pie** («2 obras · 92 min»): es la **única declaración
de pluralidad** dentro del póster, y lo único que las imágenes no pueden decir.

**El RÓTULO de sección salió también** (25 ago 2026, Juan). Competía con los
afiches y les robaba 3u de alto —el mismo argumento que mató el título—, y la
sección sigue dicha por **el filete**, que es de su color y va a sangre arriba.
Queda anotado el costo, para que se sepa que se aceptó y no que se pasó por
alto: el separador de sección de la grilla solo existe en la vista «todos los
días», así que en la vista por día el filete es la única señal de sección.

**DÓNDE ALCANZA (ampliado 25 ago 2026).** La forma nació para la función
compartida y su modelo se llamaba `legacyProgramParts`, con el gate puesto en
`is_programa`. Pero la pregunta que responde —«¿esta función agrupa 2-3 obras
y tenemos el afiche REAL de todas?»— no depende de cómo esté modelada la
función. Los **programas de cortos** (`is_cortos`), que es como se modelan hoy,
quedaban fuera: **31 funciones del catálogo** caían al generativo teniendo los
dos o tres afiches guardados. Y en la grilla los programas legacy mostraban
`poster-card-stack` — dos mitades a 50/50 que recortan cada afiche a una tira
y le parten la tipografía impresa, justo lo que la Escalera existe para evitar.

El modelo pasó a llamarse `programParts` y mira `is_programa || is_cortos`. La
grilla lo pregunta ANTES que nada, porque es la decisión de más alto rango para
una función que agrupa obras y su modelo ya sabe decir que no.

> **El SVG va INLINE, nunca como `src` de un `<img>`.** Sus módulos son
> `<image href>` remotos y un SVG dentro de `<img>` no carga recursos externos:
> saldría en negro. Es el mismo camino que ya usaba el Diario (`.dw-svg`).

**Por qué la sección se queda, aunque la grilla tenga banda.** Se propuso
quitarla (25 ago) con el argumento de que el separador de sección está unos
pixeles más arriba. **Es cierto solo en la vista «todos los días»**: en la
vista por día ese separador no existe, y la tarjeta se quedaría sin ninguna
señal de que es una función curada. La medición que sostenía la propuesta se
había hecho únicamente en modo TODO.

**LAS FRONTERAS, y de dónde salió cada una.** Las tres primeras las encontró
Juan mirando render real, no razonando en abstracto:

- **Solo Tipo 2, jamás PROGRAMAS (Tipo 3).** Las obras dentro de un programa
  suelen tener *stills*, no afiches: Tribeca 68, Cinemancia 29, FantasoFest 18;
  Ficmontañas y Vartex, ninguna imagen. Un still se dibuja **dentro del marco
  editorial**, que ya es un póster propio — meterlo como módulo sería un póster
  propio dentro de otro. Los programas conservan su afiche oficial o la forma A,
  donde el título ES el identificador único (§6.2, con guardián propio).
- **Solo con afiche real.** El módulo se decide con `_isEditorialPoster` (dueño
  único del predicado): un `posterSource:'editorial'` nunca es módulo.
- **Solo COMPLETA.** Se probó un «módulo mudo» para las funciones donde falta un
  afiche: se leía como una sombra sucia y la tarjeta terminaba haciéndose pasar
  por la única obra visible — con el agravante de que la obra invisible podía ser
  la primera de la función. Falta un afiche → **sin tarjeta**, como hoy: cada
  obra conserva su card y nada finge.
- **2 o 3 obras.** Con 4+ habría que mostrar 3 de 6, y elegir cuáles es
  curaduría nuestra sobre curaduría ajena — la misma objeción que mató al
  mosaico.

Cobertura medida con la regla dura: **FICDEH 18 de 63** funciones compartidas
reciben tarjeta; las otras 45 no pierden nada (hoy tampoco la tienen).

**Dueños.** La DECISIÓN vive en `slotPosterParts` (helpers.js) — clasifica los
miembros y devuelve `null` cuando no corresponde; el DIBUJO en
`makeSharedSlotSVG` (components.js), que solo recibe módulos ya validados.
Devuelve **markup SVG inline**, no data-uri: lleva `<image>`, y un SVG dentro de
`<img>` tiene prohibido cargar recursos externos — los afiches saldrían rotos.

**Estado: la forma existe y está probada, sin consumidor.** Dónde vive —el
bloque del calendario semanal, el Diario— es una decisión aparte. Y ojo con una
regla del template al considerarlo: las obras de una función compartida se
muestran en **cards independientes, jamás fusionadas**; fusionarlas en la grilla
sería cambiar esa regla, no aplicar esta forma.

#### Forma B — una sola imagen 16:9

Idéntica a la forma A **más un campo de imagen**, y nada más:

| elemento | posición | tamaño |
|---|---|---|
| campo de imagen | `y = 3,5u`, a sangre | `8u × 4,5u` — el 16:9 exacto |

**El campo es constante**: siempre el mismo rectángulo, en la misma posición.
Es lo que hace que las tarjetas se sientan familia al hacer scroll; cuando el
bloque de imagen cambiaba de alto según el caso, la silueta saltaba.

`8u` de ancho da `4,50u` de alto, que cae **en línea de media unidad**: el 16:9
entra entero, sin recorte, sin sobrante y sin salirse de la retícula. Es el
único ancho a sangre que lo consigue (`5u` → 2,81u y `6u` → 3,37u se salen).

**Sin blur.** El relleno borroso bajo el still queda **descartado**: ensuciaba
el negro de marca y competía con la imagen. Bajo el campo va el fondo limpio,
igual que en la forma A.

La sección baja a un máximo de 2 líneas (en forma A son 3): con imagen, la
imagen es la que carga el peso.


### 6.1 Escape XML — fuente única `escXML`

Todo texto de usuario que entra a un `<text>` SVG **debe** pasar por
**`escXML`** (`components.js`) — la **única** función de escape. Escapa `& < > "`
(el `&` primero, para no re-escapar). Un `&`/`<`/`>` crudo produce XML malformado
→ el navegador descarta la imagen (`naturalWidth 0`) → póster roto **silencioso**
(regresión real: "Opening & Galas", "Recorrido en Bicicleta").

- Guardarraíl: `tests/unit/poster.test.js` corre los 4 generadores con entradas
  adversarias (`&`, `<`, `>`, `"`, emoji, vacío) y exige XML bien formado.
- **No** crear helpers de escape locales (`const esc=t=>t.replace(...)`) — eran la
  causa de la fragilidad. Reusar `escXML` (lo hace `_bandTextSVG`).

### 6.1b Banda de sección — builder único `_bandTextSVG`

La banda (etiqueta de sección) es **una sola implementación** (`_bandTextSVG` en
`components.js`), compartida por el editorial (`_edHdrSVG`, `vw=100`) y el
generativo (`_buildPosterV16`, `vw=120`). Antes eran **dos** builders casi
idénticos que divergían (padding 2 vs 8, wrap 14 vs 15, spacing 0.5 vs 0.7, case)
— esa duplicación **era** la inconsistencia. Métricas ratio de `vw` calibradas
para que a `vw=120` dé exacto lo del generativo. Toda banda va en **MAYÚSCULA** y
con **auto-contraste** (`_contrastText`: negro/blanco por máximo contraste real,
no umbral) sobre el color de arquetipo (§8b).

**Regla de lecturabilidad del corte de línea** (`_bandWrap`, restricción dura):
cada línea debe tener sentido por sí sola y **ninguna línea (salvo la última)
termina en palabra débil** — conjunción, preposición, artículo ni guión suelto;
esas bajan a la línea siguiente con el sustantivo que introducen.

- `"Competencia De Cortometrajes"` → `[Competencia / De Cortometrajes]`.
- `"¿Qué es la ficción?"` → `[¿Qué es / la ficción?]`.
- Guardarraíl: `tests/unit/poster.test.js` (ejemplos canónicos + invariante
  "sin palabra débil al final" sobre las secciones reales).

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
4. **La serie se ve como serie** — regla de las portadas de playlists dinámicas
   de Apple («easily identified as being part of a series», auditoría 24 ago
   2026): los programas numerados de una misma sección cuyo título solo difiere
   en el ordinal renderizan la MISMA composición. Lo blinda
   `[poster-serie-consistente]` (el inverso del anterior: idénticos-salvo-el-
   ordinal dentro de la serie; enmascara ordinales y coordenadas para comparar
   solo estructura, colores y voces). 21 series reales en 8 festivales.

### 6.2b El título no repite la sección — por delante Y por detrás

Si la sección ya lo dijo, el título no lo repite. Dos formas del mismo eco:

1. **Prefijo**: título que ARRANCA con el rótulo («Competencia de cortometrajes
   Programa 1» bajo COMPETENCIA DE CORTOMETRAJES) → queda «Programa 1».
2. **Identificador de programa al final** (24 ago 2026, cazado por Juan en
   Cinemancia): sección «Programa 1. El espesor de las formas» con título «Fuera
   de competencia programa 1» → «Programa 1» **dos veces** en el mismo póster.
   Queda «Fuera de competencia»: el número lo dice la sección, arriba y grande.

**Dos frenos, los dos con test:**
- Solo si la sección nombra **ESE MISMO número**. «programa 2» bajo «Programa 1»
  se conserva — ahí el número informa, no repite.
- Solo el eco **FINAL** (regla anclada). «…programa 1 (restaurada)» va entero:
  lo que viene después del número no es eco, y recortar ahí se lo comería.

Comparación sin acentos ni case; si el recorte dejara el título vacío, se
conserva el original.

---

### 6.2c La MINI — el generativo en superficies de 56px

Regla de Apple que la motiva («legible en TODO el rango de tamaños», Curator
Best Practices) + medición propia: en el chip de la lista el póster entero
escalado dejaba la sección en **3,3px** y el dato en 2,8px — ruido que además
REPITE lo que la fila dice al lado (anti-repetición).

La mini responde con **UNA voz** (dueño: `_buildPosterMini`, servida por
`getFilmPosterMini` que espeja las decisiones de `getFilmPoster` y solo
sustituye los caminos generativos — custom/evento/sorpresa/TMDB/editorial pasan
intactos):
- **Serie** («Programa N»): el **ordinal a 5u** — legible de verdad.
- **Obra o programa con nombre**: **SU MARCA** — 2-3 formas geométricas sobre
  retícula de 2u, sembradas por `_djb2(título)` → `_mulberry32`. Determinista:
  la misma obra dibuja siempre la misma marca, se reconoce sin leer, como una
  portada de disco. (La v1 sin marca murió en revisión: «no hay diferenciador,
  no sirve» — el color es de la SECCIÓN y dos vecinas quedaban idénticas.)

**El GRID no cambia** (Juan, 25 ago): la marca en el póster grande era
«demasiado ruidosa, minimalismo cero» — el grid queda tipográfico puro.
Superficies de la mini: chip de la lista (`_plistPosterHtml`), thumb de corto
(`itemPosterParts` sin header) y el fallback del stack (`_programaStack`).
Guardián: T106 (lista → mini, grid → intacto) + unit posterMini (5 mutantes).

---

### 6.3 La pila de obras — un compuesto se apila, no se escribe como frase

Un título compuesto (`«A + B»`, `«A + B + C»`) **no es una frase**: es una lista
de obras. Escrito corrido, el motor lo partía donde cayera —línea rota a mitad de
un nombre, el « + » colgando al final del renglón, elipsis al cierre—. Un cartel
de programa doble nunca tipografía así.

**Retícula** (medida sobre grid y rulers, `_buildPosterV16`):

1. **Un bloque tipográfico por obra**, todos al **mismo cuerpo** — el menor de
   los ajustes individuales, tope **16**. Una obra corta no puede gritar más que
   su vecina.
2. **1u exacto** entre bloques. El « + » vive **en ese gap**, a **0,6u**, al
   margen izquierdo como todo el sistema, en el **color de la sección**, y
   ópticamente centrado en el aire (no apoyado en su borde). Subió de 0,5u a
   0,6u (Juan, 24 ago): a 0,5u quedaba casi un punto y leía como suciedad antes
   que como el signo que une dos obras.
3. La pila **crece hacia arriba** desde la misma base que cualquier título
   (§6.0): su última línea se apoya donde se apoyaba el título de una sola obra.
4. **Frontera 2–3 obras** — la misma de la forma C / Escalera. Con **4 o más** se
   conserva la forma de siempre: el cuerpo caería a ilegible y el pie ya dice
   «4 obras» (`_datoCompuesto`).

**El presupuesto se reparte por USO REAL, no en partes iguales.** Darle a cada
obra un tercio exacto del alto castigaba a las tres por culpa de una: con dos
nombres de una línea y uno de dos sobraban ~3,7u de aire muerto y la pila igual
salía pequeña (10,8 donde cabía 14). El alto **no acota** el ajuste individual:
las líneas de cada obra las decide su **ancho**, que es lo único que de verdad la
limita, y el presupuesto —base del título − fondo del rótulo **ya ajustado** −
0,5u de aire— se cobra **una sola vez**, sobre el alto que la pila realmente
ocupa: si no cabe, el cuerpo baja de a 0,25 hasta que quepa (suelo 9).

Ojo con el orden: la primera versión repartía el presupuesto como caja de cada
obra y llevaba además un lazo correctivo. Ese lazo era **código muerto**
—`_fitLines` lo adelantaba siempre— y un guardián que nunca dispara no es de
fiar. Con el reparto por uso real el lazo **sí vive**, y es lo único que impide
que un cartel real de Cinemancia invada la sección.

Lo blindan 7 tests en `tests/unit/poster.test.js` (11 mutantes, todos mueren).
Ojo con los inputs: dos mutantes sobrevivieron a la primera versión porque los
casos de prueba caían al suelo **por ancho** antes de que el techo mandara. El
input que prueba el techo salió de una búsqueda por fuerza bruta sobre el espacio
de compuestos — **tres nombres medianos bajo un rótulo de 2 líneas**.

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

- **Cobertura ≥ 95 %** — un film cuenta como cubierto si `f.poster` no está vacío.
- **`[poster-map-legacy]`** (ERROR) — `posters{}` o `customPosters{}` presente a
  nivel raíz. El modelo dual murió (§1, Fase A.1); un map que reaparezca significa
  que el pipeline regresó al modelo viejo. Inline el poster en cada film
  (`scripts/migrate-posters-inline.py`) y elimina el map.
- **`[seccion-sin-arquetipo]`** (ERROR) — una `section` (film o corto anidado) sin
  entrada en `SECTION_ARCHETYPES` (§8b). Sin arquetipo, `_sectionColor` cae a gris
  ilegible `#2C2C2A`. Caza las secciones nuevas de un festival recién montado
  **antes** de publicar — asignales uno de los 9 arquetipos en `src/config.js`.
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

## 8b. Color de sección — paleta por arquetipo (unificada)

El color de la banda editorial **significa**: las 78 secciones de los 7 festivales
colapsan en **9 arquetipos** (Gala, Competencia, Clausura, Especiales, Retrospectiva,
Muestra/País, Perspectivas, Cortos, Charlas), cada uno con **un** color de marca
reusado en todos los festivales (misma Competencia = mismo naranja en cualquier lado).

- **`ARCHETYPE_COLORS`** (9) + **`SECTION_ARCHETYPES`** (sección→arquetipo) en `config.js`.
- **`_sectionColor(sec)`** resuelve vía arquetipo (gana), luego `SECTION_COLORS` legacy,
  luego gris `#2C2C2A` (que el gate debería impedir).
- **`_contrastText(hex)`** (`components.js`): el texto de la banda elige negro/blanco por
  **máximo contraste real** (WCAG), no por umbral. Usado en `_edHdrSVG` (editorial) y
  `_buildPosterV16` (generativo) → banda legible sobre cualquier color. Antes: 51 secciones
  caían al gris con texto negro (contraste 2.49, ilegible).
- Sección nueva sin arquetipo → cae a gris → **debería** cazarla un gate (pendiente).

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
