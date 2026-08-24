# Doctrina de enrichment y historial de errores — festivales Otrofestiv

> **Alcance (9 ago 2026):** este documento es LA AUTORIDAD sobre qué se acepta
> de TMDB / Letterboxd / fuentes de terceros y por qué — el proceso endurecido
> tras Tribeca 2026 (134 posters falsos, 107 synopsis_en de films distintos).
> **El PROCESO de montar un festival vive en `pipeline/PROTOCOLO.md`**; este
> doc manda únicamente en su tema. Las reglas de verificación ya son código:
> `lib.ficha_verifica()` y `pipeline/enriquecer.py` las aplican solas — este
> doc explica el porqué y guarda el historial para no repetirlo.

## 0 · Secuencia de herramientas (referencia rápida)

Orden canónico para montar un festival. Cada paso mapea a una fase de abajo.

| # | Paso | Hace | Fase |
|---|---|---|---|
| 1 | `node scripts/csv-to-festival.js <in.csv> festivals/<id>.json [--anclaje\|--separadas]` | CSV del organizador → JSON base `{venues, films}`. **BLOQUEA** si hay proyecciones conjuntas sin modelo decidido (gate duro), y al terminar emite el comando de `generate-config.js` ya derivado | 1 |
| 2 | `TMDB_API_KEY=… python3 scripts/enrich-festival.py festivals/<id>.json` | llena **solo `genre`/`year`** (gate de 4 criterios; rechaza en miss) | 3 |
| 3 | **`synopsis_es` → traducción inline de Claude** (lee PT/EN → ES) + **pase de Content Design** | localización de contenido | 3b / 5 |
| 4 | `python3 scripts/geocode-venues.py …` | lat/lng de venues (Nominatim) | 2 |
| 5 | `node scripts/generate-config.js …` → pegar en `src/config.js` | entrada de `FESTIVAL_CONFIG` | 2 |
| 6 | **Secciones nuevas → `src/config.js`**: emoji único + entrada `SECTION_EN` + arquetipo en `SECTION_ARCHETYPES` (uno de los 9) | display EN + color de banda (sin arquetipo = ERROR `[seccion-sin-arquetipo]`) | 2 |
| 7 | `python3 scripts/classify-posters.py <id> --apply` | mide el aspecto real de cada póster y escribe **`posterSource`** (`editorial`/`tmdb`/`custom`) — lo exige el gate `[poster-source]`; caza rotos al montar | 3 |
| 7b | `python3 scripts/optimize-posters.py assets/<id>/` | pósters al peso de la app: redimensiona a **500px** de ancho (= mínimo TMDB → el mismo archivo sirve a la app Y a las altas); solo reemplaza si pesa menos; `--dry-run` para reporte. **Commitear antes el sidecar de URLs fuente** (`<id>-posters-src.json`) para poder re-bajar originales | 3 |
| 8 | `python3 validate.py` + `node scripts/validate-festivals.js <id>` | gates bloqueantes (0 errores) | 4 |
| 9 | **`tools/audit.html?fest=<id>`** (servir el repo + abrir en Chrome) | dashboard de auditoría: UNA pasada visual cubre póster·metadata·sinopsis·procedencia·LB; filtro "Solo problemas" | 5 |
| 10 | `node scripts/bump-version.js` | stamp de build antes de deploy | 6 |

> **`scripts/translate-synopsis.py` está DEPRECADO** — la traducción de sinopsis se hace inline (Claude) + pase humano de Content Design, no por script.
>
> **TMDB jamás llena `poster`/`synopsis_en` (lección Brujo/Tribeca 2026):** esos campos salen de la fuente oficial del festival con **verificación humana film-por-film** (ver Fase 3 y `docs/FESTIVAL-CHECKLIST.md`).

### Roles — *Claude ejecuta · Juan audita y aprueba*

| Tarea | Ejecuta | Aprueba |
|---|---|---|
| Extracción · enrich · geocode · config · validación | **Claude** | Juan en los gates |
| `synopsis_*` / copy / strings de UI | Claude propone | **Juan (Content Design)** |
| Pósters (verificación visual) | Claude propone | **Juan** |
| Merge · arquitectura · borrar ramas | Claude propone/ejecuta | **Juan (OK explícito)** |

---

## Fases en orden obligatorio

### Fase 0 · El `robots.txt` va PRIMERO — retro TIFF 2026 (13 ago 2026)

**Antes de escribir una línea de extractor, leer el `robots.txt` de la fuente.**
No al final, no cuando algo falla: antes de la primera petición.

Salió de TIFF y costó 262 páginas ya descargadas. Al ir a leer *tiffr* —un
planificador de terceros— apareció esto, y lo mismo en Letterboxd:

```
User-agent: ClaudeBot
Disallow: /
Content-Signal: ai-train=no, use=reference
```

Las tres fuentes de aquel onboarding resultaron ser tres casos distintos, y la
diferencia importa:

| Fuente | Qué dice | Qué hacemos |
|---|---|---|
| **tiff.net** | no publica `robots.txt` (404) | sin restricción declarada → es la fuente |
| **Letterboxd** | prohíbe ClaudeBot | decisión de Juan caso por caso; en TIFF quedó el uso mínimo del `lbSlug`, que además les devuelve tráfico |
| **tiffr** | prohíbe ClaudeBot, y es un producto PAR | no se toca. Y no hacía falta: sus 244 obras eran las mismas 244 de TIFF |

**Dos reglas que se llevan de aquí:**

- **La web del propio festival es la fuente legítima por defecto.** Un tercero
  que refleja al festival no aporta dato nuevo — se comprobó contando: tiffr y
  tiff.net daban el mismo número exacto de obras.
- **Un `robots.txt` que no existe (404) no es lo mismo que uno que calla sobre
  nosotros, y ninguno de los dos es lo mismo que uno que nos nombra y nos
  prohíbe.** Solo el tercero es un no.

### Fase 0·bis · Qué obras PUEDEN tener `lbSlug` — retro TIFF (17 ago 2026)

Una cobertura de Letterboxd que parece un hueco y no lo es. TIFF tenía «62
funciones sin `lbSlug`», y al desglosarlas quedó así:

| | | |
|---|---|---|
| programas de cortos | 20 funciones | **Letterboxd no tiene página de programa.** Sus cortos sí, uno por uno, y ahí es donde va el slug |
| charlas y conversatorios | 5 | no son obras |
| **series de TV** (Primetime) | 22 | **Letterboxd es SOLO cine.** Una serie no existe ahí, y buscarla es perder la noche |
| obras que sí podrían tenerlo | 15 | estrenos 2026 aún sin ficha en TMDB |

**El hueco real eran 5 títulos, no 62.** Antes de salir a buscar slugs, hay que
restar lo que por definición no puede tenerlos: si el festival programa series,
el 100% de cobertura es imposible y perseguirlo es trabajo inventado.

**Y el `lbSlug` se saca por el atajo `letterboxd.com/tmdb/<id>`**, que necesita
`tmdb_id`: sin ficha en TMDB no hay slug, y la ruta entonces es darla de alta
(Fase 3b), no rastrear Letterboxd — que además nos prohíbe por `robots.txt`
(Fase 0). Para estrenos del año en curso suele bastar con repetir el pase de
TMDB unas semanas antes del festival: las fichas aparecen solas.

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

**Prioridad de poster:** ver **`docs/POSTERS.md`** — fuente única. (Regla en una línea: identidad primero — TMDB/LB solo con verificación visual; entre correctos, portrait 2:3 sobre landscape oficial; el landscape no se vacía.)

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

#### Gate de Fase 1 — proyecciones conjuntas (obligatorio desde FINCA 2026)

Al cerrar el JSON, buscar **slots compartidos** (2+ obras con mismo
día+hora+sede+sala). Cada uno exige una decisión contra el programa oficial —
nunca por deducción:

1. **¿El festival lo curó con nombre?** → modelo **Programa**: una entrada
   `is_cortos` + `film_list`.
2. **¿Obras independientes en una misma función?** (corto antes del largo, dos
   mediometrajes) → modelo **Anclaje**: `sharedSlotIsOneScreening: true` en la
   raíz. Verificar caso por caso: en sedes multisala, misma hora+sede puede ser
   otra sala = otra función.
3. **¿Son de verdad funciones separadas?** (actividades paralelas en espacios
   distintos) → anotarlo en `_SEPARATE` del guardián.

El guardián `[slots-sin-decidir]` (validate.py) falla si un festival activo
tiene slots compartidos sin decisión — Cinemancia 2025 quedó en ese limbo y la
app trató corto+largo de una misma función como rivales. Doctrina completa y
tabla de decisión: `docs/SCHEMA.md` § Proyecciones conjuntas.

#### Reglas de Fase 1 probadas en Tercer Tiempo 2026 (fuente = PDF + fichas web)

1. **Sección = NOMBRE OFICIAL, jamás inventado.** Si el festival nombra sus
   sesiones/secciones ("Juego Mental", "Refugio en la Cancha"), esos nombres SON
   las secciones de la app. Agrupar bajo etiquetas genéricas propias ("Selección
   Oficial") viola la doctrina de fuentes — costó un re-seccionado completo en TT
   (PR #295, cazado por Juan).
2. **Inventariar TODAS las imágenes de cada ficha, no solo el texto.** Cada ficha
   de la Cinemateca publica el **afiche oficial de la sesión** (título + stills):
   ese afiche es la fuente canónica del póster de bloque (`is_cortos`). Un
   extractor que solo lee texto se los pierde (pasó en TT; 12 afiches recuperados
   en pase posterior, PR #297). Gate: por cada ficha leída, listar sus
   `<img>`/`og:image` y clasificarlas (afiche de sesión / still / logo) antes de
   cerrar la Fase 1.
3. **Funciones provisionales → `_pendiente`.** Cuando la fuente operativa
   (fichas/boletas) no confirma algo que otra fuente anuncia (ej. PDF dice "ambas
   CEFEs", fichas solo publican una), se modela SOLO lo confirmado y el resto se
   marca `_pendiente: "<qué falta y contra qué fuente se resuelve>"` — visible en
   tools/audit.html, re-sondeable durante el festival.
4. **Ticketing por función.** Si el material oficial trae link de compra por
   sesión (ej. URIs en anotaciones del PDF, mapeadas por página), poblar
   `ticket_url` POR FILM — pisa al global en el CTA del sheet.

#### Reglas de Fase 1 probadas en FantasoFest 2026 (CMS WordPress + PDF de prensa)

1. **Cazar contenido RECICLADO de ediciones pasadas (CMS que reusa páginas).**
   La web de FantasoFest mostraba 10 largos; 5 eran **fantasmas de la edición
   2022** dejados en el WordPress. Cómo se cazó — y el gate que queda:
   - **Cruzar SIEMPRE contra la fuente oficial de convocatoria** (PDF/comunicado
     de prensa). El PDF decía "5 largos, 9 funciones"; la web tenía 10. El PDF
     manda para el CANON de qué está en el programa.
   - **Validar el par día-de-semana ↔ fecha contra el AÑO del festival.** Las
     funciones fantasma decían "Martes 19 de julio", "Sábado 23 de julio" — y
     esos weekdays cuadran con **2022**, no 2026. Un weekday que no matchea el
     calendario del año = dato de otra edición.
   - **Fecha fuera de la ventana oficial = bandera roja.** Funciones el 20–27 jul
     cuando el festival es 13–19 → no modelar sin confirmar.
   - La fuente a veces se autodelata: el bloque fantasma estaba rotulado
     "Proyecciones en FantasoFest **2022**:". Leerlo, no ignorarlo.
2. **El póster pertenece a ESTE film (director con varias obras).** La Virgen de
   la Tosquera (Casabé, 2025) NO usa `AFICHE-Lqv` — ése es "Los Que Vuelven"
   (Casabé, 2019, otra película). El correcto (`LaVirgenDeLaTosquera_Web_Cartel`)
   se halló **buscando el título en los uploads**, no por cercanía/orden en la
   grilla. Regla: cuando un director tiene >1 film, verificar que el asset de
   póster corresponde a ESE título (buscar por título), nunca por proximidad.
3. **Stills de cortos sin etiqueta → mapear con una CLAVE, nunca adivinar.** La
   página oficial (popups Popup Maker) tenía 9 stills limpios 16:9 pero SIN
   etiqueta (9 para 10 cortos; el orden DOM no corresponde a la lista). Instagram
   sí mapeaba (título pegado en cada slide) pero tras login wall. Se usó IG como
   **clave de mapeo, confirmada por el PO** (P#→título). Mis hipótesis visuales
   previas estaban casi todas mal → **confirmar con el PO, no adivinar**. Un still
   16:9 LOCAL va con `poster` + `posterSource:'editorial'` (recibe la banda; el
   sheet ya lo honra, no solo por CDN-URL). Sin mapeo certero → generativo, jamás
   un still equivocado.

**Gates de salida (bloqueantes):**
- [ ] Cero films sin `slug`
- [ ] Cero títulos en ALLCAPS (3+ palabras consecutivas en mayúsculas)
- [ ] `poster` ≥ 90% de films auditables
- [ ] `node scripts/validate-festivals.js` pasa con 0 errores antes de cada push — **sin excepciones**
- [ ] Cero funciones duplicadas (mismo título+día+hora). Múltiples funciones del mismo título en días distintos son **datos correctos, no duplicados**

---

### Fase 1.5 · Validación de CONTENIDO `[Data Engineer]` — retro FICDEH (26 jul 2026)

Los gates de forma (Fase 4) no ven contenido corrupto: en FICDEH TODOS los
errores (duraciones falsas por números partidos en el HTML, 92 sinopsis con
metadata pegada, títulos bilingües que rompían TMDB, países con basura) los
cazó un ojo humano notando que "algo huele raro". Esta fase mecaniza ese olfato
y es OBLIGATORIA antes de dar la extracción por buena:

**1. Doble lectura (regla dura).** Todo campo se extrae de DOS representaciones
independientes de la fuente (HTML renderizado vs `og:description` vs API) y se
DIFEAN: donde discrepan hay un bug — del parseo o de la fuente — y se resuelve
ANTES de escribir el JSON. En FICDEH el diff contra `og:description` cazó 4
duraciones falsas (un "largometraje de 1 min" era 102) y 2 directores perdidos
(`Directoras:` en plural). El diff no es opcional ni a posteriori: es el
detector de bugs del parseo.

**2. Linter de contenido (ejecutable).**
```bash
python3 scripts/lint-catalog.py festivals/staging/<id>.json   # en pre-onboarding
python3 scripts/lint-catalog.py --root                        # publicados (con pHash)
```
Gates: `[duracion-vs-seccion]` (largo <40 min = imposible) · `[sinopsis-pura]`
(sin "Director:/Ubicación:/Hora:" dentro del texto) · `[titulo-bilingue]`
("Silenciada (Silenced)" pegado) · `[pais-sano]` (segmentable en países
conocidos) · `[director-persona]` · `[poster-phash-dup]` (pósters duplicados
POR PÍXELES aunque el archivo difiera — el gate por URL no los ve; cazó un
duplicado real en TT ya publicado). En CI corre como `[contenido-sano]` dentro
de `validate.py` (solo texto; el pHash es del checklist de onboarding).

**3. Auditar los rechazos del enrich (no solo leerlos).** El log de
`enrich-festival.py` lista los rechazos con su similitud. Los de **título ≥0.85
se auditan UNO A UNO** contra TMDB antes de aceptar "no existe": en FICDEH la
mitad de los "52 sin ficha" eran títulos bilingües mal parseados (mi bug) y la
otra mitad homónimos reales (Amalgama=Cuarón/México, Clemencia=1935) donde el
gate acertó al rechazar. Un número de cobertura que "huele raro" (Juan lo olió)
ES una señal — verificarla, no racionalizarla. Ojo: existen **fichas cascarón**
en TMDB (sin fecha/director/sinopsis) — sin criterio corroborante NO se atan.

---

### Fase 1.6 · Guardianes de la LÓGICA DEL CRUCE — retro TIFF 2026 (13 ago 2026)

Hasta TIFF, todos nuestros guardianes revisaban la **forma** del dato: que el
campo exista, que el sidecar tenga fecha, que la sede no esté apilada. Ninguno
sabía preguntar si el **cruce** que produjo ese dato era correcto.

Montando TIFF se colaron cinco defectos de cruce y **ningún guardián cazó uno
solo**: los cinco se cazaron mirando la salida a mano. De ahí salen estos
cuatro, uno por clase de error. Son genéricos — no saben de qué festival
hablan, solo de cómo se comporta un cruce sano.

| Guardián | Qué exige | El error que lo parió |
|---|---|---|
| `[cruce-inyectivo]` | Un `lbSlug` o `tmdb_id` no puede quedar asignado a dos obras distintas. Se compara por OBRA, no por fila: una obra con doce funciones repite su slug doce veces y eso es sano. | «The Age of Goodbyes» le prestó su slug a otras cuatro obras cuyos títulos («月宫», «咒语») se normalizaban a cadena VACÍA, y la vacía casaba con cualquier cosa. Y los dos cortos llamados «The End» —Pelechian 1992 y Lindroth von Bahr 2026— colapsaron en uno al indexar por título. |
| `[cuentas-cuadran]` | Si un sidecar declara `_cuentas`, sus números cierran: `entradas == publicadas + suma de descartadas`. | El ensamblador se quedaba con la PRIMERA sección de cada obra y tiraba la segunda sin decir nada: 18 obras perdieron una etiqueta y el JSON se veía perfecto. |
| `[sidecar-vacio]` | Un conteo `_algo: N > 0` tiene que estar respaldado por su lista: ni vacía ni toda nula. | El script de TMDB se pasó una hora reintentando un error de certificado SSL y terminó sin escribir nada, porque trataba un fallo de transporte como un tropiezo pasajero de la API. |
| `[discrepancia-falsa]` | En una lista `_discrep*` o `_ambigu*`, ningún elemento puede tener dos valores iguales al normalizar. | La auditoría de directores reportó 22 discrepancias y las 22 eran falsas: comparaba «Sue Kim» con «Sue Kim» y «濱口竜介» con su nombre latino. Una lista de discrepancias con idénticos no es auditoría, es ruido que esconde las de verdad. |

**Séptimo, hermano del anterior y del mismo día: `[valor-inventado]`.**
`[campo-contrato]` caza el NOMBRE mal escrito; éste caza el VALOR inventado.

Escribí `ticketing_model:'ticketed'` para TIFF. La app solo ramifica sobre
`'paid'` y `'mixed'`; con cualquier otra cosa cae al `return ''`. **637 fichas
con su enlace de Ticketmaster guardado y sin botón de compra.** El error de
fondo no fue teclear mal: fue ver `'mixed'` en otro festival y **deducir** que
existiría un valor para «todo de pago», en vez de leer qué acepta el código.

Los valores manejados se leen **del código**, no de una lista escrita a mano:
una lista aquí envejecería igual que el bug que persigue.

**La regla de trabajo que se lleva de aquí, y que vale más que el guardián: un
valor de enum no se deduce por analogía. Se lee en el código que lo consume,
antes de escribirlo.**

**Sexto guardián, el que tapa el hueco de verdad: `[campo-contrato]`.** Todos
los demás revisan el dato POR DENTRO —que el campo exista, que sea booleano,
que las cuentas cierren—. Ninguno miraba la **junta** entre el dato y la app.
Un JSON impecable y una vista impecable pueden no encontrarse nunca, y nada se
pone rojo.

Pasó con TIFF: emití `ticketUrl` y `sheets-controller` lee `ticket_url`. Los 638
enlaces de boletería estaban en el JSON y no llegaban a ninguna ficha. **No lo
cazó ningún test —ni los del pipeline ni los de la app—: lo cazó Juan abriendo
la app y preguntando dónde estaba el enlace.** Esa es la definición del hueco.

La regla es estrecha a propósito, para no dar falsos positivos: si un campo NO
lo lee la app pero SÍ existe su variante en el otro estilo de nombre
(camelCase ↔ snake_case) y esa sí se lee, es un error seguro — es la misma cosa
escrita de dos formas. Los campos que nadie lee y no tienen gemela salen como
aviso, no como error: son dato muerto, no un fallo.

**En su primera ejecución encontró un bug que llevaba meses en producción y no
era de TIFF:** `aff-2026.json` emitía `lb_slug` en dos películas y la app lee
`lbSlug`. Dos botones de Letterboxd que nunca aparecieron.

**Quinto guardián, añadido el 13 ago 2026:** `[flag-booleano]`. La app compara
los flags de servicio con `=== true`, no por truthy, y eso es deliberado —un
badge de precio no se pinta por un valor accidental—. El precio de esa decisión
es que un `"true"` como **string** no rompe nada: el badge simplemente no
aparece nunca, y nadie se entera. Lo levantó Main al implementar el badge
PREMIUM de TIFF, y vale para todos los flags (`is_free`,
`requires_registration`, `has_qa`, `is_cortos`, `premium`), en el film y dentro
de `film_list`. Basta con que un ensamblador lea un CSV o un Excel para que un
booleano llegue como texto.

**El guion bajo no es un escondite (17 ago 2026).** Un campo `_` es una NOTA
para nosotros —de dónde salió el dato, qué falta, qué se heredó—, no un dato de
la app con disfraz. `_tmdbId` vivió en 16 funciones de FINCA a salvo de
`[campo-huerfano]` **solo por llamarse con guion bajo**, mientras el resto del
repo usaba `tmdb_id`. Ahora, si al quitarle el guion el nombre coincide con un
campo real, el guardián lo llama por su nombre: contrabando.

**Decimoquinto: `[cosecha-tmdb]` — tener la ficha y volver con las manos
vacías.** Los catorce anteriores miran la FORMA del dato: el tipo, el enum, el
campo que nadie lee, el camino por el que llegó. Ninguno preguntaba lo obvio:
si fuimos hasta TMDB y anotamos el `tmdb_id`, ¿por qué la obra no tiene
sinopsis? En CineAutopsia 32 obras tenían ficha y ni una línea de texto. Dos
fallos encadenados, los dos invisibles:

1. La consulta pedía `es-CO`. TMDB **no cae a `es-ES`**: devuelve vacío. El
   enriquecedor genérico (`pipeline/enriquecer.py`) siempre pidió `es-ES` +
   `en-US`; el que se equivocó fue un script a la medida del festival, escrito
   por fuera del pipeline. Cuarta reincidencia del mismo pecado.
2. `ensamblar.py` construía cada obra de `film_list` con una lista de campos
   **escrita a mano** (título, director, país, año, duración). Todo lo demás
   que el crudo trajera sobre la obra —póster, `tmdb_id`, sinopsis— se caía en
   silencio. Ahora la lista la manda el contrato: lo que la fuente trae, viaja.

Regla: **si hay `tmdb_id` y no hay `synopsis`, el guardián se pone rojo.** Un
identificador de ficha es la prueba de que estuvimos ahí; volver sin el texto
no es un dato que falta, es una cosecha que no hicimos.

**Decimocuarto, y el que cierra el círculo: `[pipeline-generico]`.** Los trece
anteriores vigilan que el dato salga bien de un camino que cada festival
reescribía. Éste vigila que **el camino sea uno**: `pipeline/ensamblar.py` y
`pipeline/publicar.py`, con lo propio del festival declarado en su `plan.json`.

Por qué: los 6 enlaces de TuBoleta de CineAutopsia, las 415 banderas de FICDEH y
el `is_free:false` escrito a mano en una función que era libre no fueron tres
errores distintos — fueron **el mismo error tres veces**, porque las reglas
vivían en la cabeza de quien escribía el ensamblador de turno.

Y el publicador **se niega a borrar lo que ya está en producción**: compara la
cobertura campo a campo con el JSON publicado y aborta si el build trae menos.
Es literalmente el accidente de FICDEH del 17 ago, convertido en una guarda.

**La prueba de que el genérico sirve fue reproducir CineAutopsia entero con él**
—7 programas, 45 obras, 4 días— contra el JSON que había hecho el ensamblador a
mano: mismas funciones, mismas obras, **mismos 23 pósters y 27 slugs de
Letterboxd**. Las diferencias que quedaron fueron todas mejoras del genérico, y
una fue un bug MÍO que la comparación cazó: deduplicaba banderas por carácter y
partía los emoji en dos («🇺🇸🇪🇸🇵🇱» salía «🇺🇸🇪🇵🇱»), porque una bandera son dos
puntos de código.

**Y de paso se midió la tabla de países entera**: `banderas()` se escribía a
mano y a demanda, así que le faltaba lo que ningún festival anterior había
traído. «Hungría» apareció con CineAutopsia y se quedó sin bandera. Medido
contra los 13 festivales: **de 191 apariciones sin bandera a 27**, y las 27 que
quedan no son países («Varios», «Iberoamérica»).

**Decimotercero: `[lib-unica]` — una función, un dueño.** `pipeline/lib.py`
existe para escribir la lógica común una sola vez. El 17 ago 2026 se midió
cuánto de eso era verdad: **7 de sus 17 funciones tenían copias sueltas**,
`norm()` estaba reescrita en SEIS scripts, y solo 5 de 28 scripts importaban
lib.

Al comparar comportamiento con entradas reales apareció algo peor que un
duplicado: **el mismo nombre significaba cosas distintas.** `norm()` devuelve un
string en lib, un `set` en ficma-repesca y una `list` en ficma-tmdb. `slug()`
quita acentos en lib y los conserva en ficma —«rebelion» contra «rebelión»—.
`hora24()` devuelve la hora en lib y «» en ficma-parse cuando ya venía en 24h.
`sede_sala()` y `director_coincide()` ni siquiera tenían la misma firma. Leer un
script y suponer la semántica del otro era un bug esperando fecha.

La regla tiene dos ramas: **si la copia hace lo mismo, se borra y se importa**
(6 casos, verificados idénticos con entradas reales de los 12 festivales); **si
hace otra cosa, se renombra para que lo diga** (8 casos, cada uno con su razón
escrita sobre el `def`). Lo que no se permite es que dos cosas distintas
compartan nombre.

**El método importa tanto como el resultado**: la paridad se MIDIÓ ejecutando
las dos versiones sobre 525 títulos, 523 horas y 440 países reales. Sustituir
por una versión «equivalente» que no lo sea habría sido peor que el duplicado.

**Duodécimo, y el que cambia el modelo: `[contrato-vivo]`.** Los once anteriores
vigilan errores concretos que ya cometimos, uno por uno. Éste vigila que exista
**un canon ejecutable**: `pipeline/contrato.json` declara los 49 campos de una
función —tipo, formato, obligatoriedad, enum— y `validate-festivals.js` lo
EXIGE. La sección Films de `docs/SCHEMA.md` ya no se escribe: se **genera** del
contrato (`node scripts/generate-schema-md.js`).

Por qué importa: una doc escrita a mano al lado de un canon ejecutable es una
SEGUNDA FUENTE, y dos fuentes divergen siempre. Divergieron — el schema
documentaba 24 campos de 60 y juraba que `duration` era un número cuando las
1.194 son el string «90 min». La única defensa no es revisar la doc: es que no
haya dos.

Vigila tres cosas: que la doc esté regenerada, que **ningún campo viva en los
datos sin estar declarado** (así el contrato no envejece callando, que es como
envejeció la doc), y que **ninguna excepción con fecha se venza sin que nadie
mire**.

**Y uno para los tests: `[reload-sin-reloj]`.** Dos de las tres bombas del 20 de
agosto eran tests que hacían `page.reload()`. La recarga borra `_simTime` —vive
en memoria—, así que la app vuelve a la fecha real y el test queda a merced del
día en que corra. El síntoma engaña: T65 parecía un fallo del marcado «Ya pasó»
y lo que estaba roto era su premisa.

Después de recargar hay tres formas correctas: `reentrar()` (helpers, re-elige y
re-congela), `page.clock.install()` (congela el reloj del navegador y sobrevive),
o derivar el festival del dato en tiempo de ejecución en vez de clavarlo.

El check mira **dos cosas juntas**: recarga *y* premisa clavada. Recargar no es el
problema; recargar con `enterFestival(page, 'ficdeh2026')` escrito a mano, sí. Si
solo mirara el reload obligaría a reescribir tests que ya son correctos — y un
guardián que crea trabajo inútil se termina ignorando.

**Decimotercero, el único ÁMBAR del repo: `[contrato-por-vencer]`.** El 20 de
agosto de 2026 `main` amaneció rojo sin que nadie tocara nada: la excepción de
`venue@finca-2026` vencía ese día. No hubo aviso porque **no existía la franja
intermedia** — todo era verde o rojo, así que lo que caducaba no avisaba: explotaba.

Lo irónico: el preaviso ya estaba escrito. `_exentoDe()` devolvía
`{ exento:true, aviso }` mientras la excepción seguía viva… y **nadie leía ese
`aviso`**. Ahora se lee: a 14 días o menos, `validate.py` y `validate-festivals.js`
avisan **sin bloquear**; el día D siguen siendo error.

- **La fecha se calcula en la zona del proyecto (UTC-5), no en UTC.** Con
  `toISOString()` crudo, entre las 7pm y medianoche de Colombia «hoy» ya era
  mañana: la excepción vencía cinco horas antes y la máquina local discrepaba de
  CI. Es la regla que `CLAUDE.md` fija para toda lógica de fechas.
- **La ventana avisa, no perdona.** Si la fecha llega, es error igual.

Lección de la fecha que estalló: `migrar_el` era el **20 de agosto** y FINCA
cerraba el **19**. Nunca hubo ventana que perder — al fijar la fecha de una
excepción, dejar margen real después del cierre del festival.

**Y las excepciones llevan fecha.** Los archivados quedan congelados —reescribir
su historia es riesgo sin beneficio— pero un festival VIGENTE que aún no cumple
entra en `_pendientes` con el día en que deja de perdonársele. Una excepción sin
fecha se vuelve permanente sola; ésta se vence sola. La primera fue FINCA: sus
30 sedes sin ciudad esperan al 20 AGO porque el festival cierra el 19 y renombrar
una sede toca `_slotKey`, que es la ancla de los planes YA GUARDADOS de usuarios
reales.

**Decimoséptimo: `[config-esm]` — `node --check` da un verde falso.**
`src/config.js` es un **módulo ES**, y `node --check` lo analiza como *script*.
Un archivo donde la entrada de un festival se quedó sin cerrar pasa ese chequeo
y revienta en el navegador. Pasó el 20 ago 2026 al resolver un merge en el que
las dos ramas agregaban su festival en el mismo punto del archivo: la entrada de
Cinemancia perdió su `},`, CineAutopsia quedó **anidado dentro de ella**, y la
app no arrancaba — splash vacío y `Uncaught SyntaxError` en consola.

Nada lo vio. `validate.py` parsea el config con expresiones regulares y nunca lo
ejecuta; `node --check` lo lee con la gramática equivocada; los unit tests no lo
tocan; y Playwright habría fallado, pero esa rama no lo corría. El error viajó
dentro de un commit que decía «108/117 checks passed».

Regla: **el guardián IMPORTA el config de verdad** —`import()` sobre el archivo—
y comprueba dos cosas que solo se ven al cargarlo: que no haya un festival
anidado dentro de otro, y que el número de festivales no se desplome. Es la
única forma de saber que el archivo que carga el navegador es el que creemos.

**Decimosexto: `[poster-mirado]` — alguien tiene que ABRIR el archivo.**

*«¿Cómo es posible crear un póster sin pasar por un guardián?»* preguntó Juan al
ver en pantalla un póster que era la franja gris del encabezado del PDF con dos
stills ajenos debajo. La respuesta incómoda: **todos los guardianes de póster
miran el CAMPO y ninguno el ARCHIVO.** `[poster-single-owner]` vigila quién lo
escribe, `[posters-duplicados]` que dos obras no compartan URL,
`[paridad-derivados]` que `posterSource` acompañe a `poster`. Un JPG con un
tercio de banda plana los pasa todos, porque ninguno lo abre.

Éste lo abre y mide tres cosas sin opinar: que el archivo EXISTA, que tenga
resolución de póster y no de miniatura, y que no arrastre una BANDA PLANA en un
borde —el recorte que se comió el encabezado—.

**Calibrarlo costó dos vueltas, y las dos por falsos positivos:** el mínimo iba
por el ancho y marcaba 52 pósters verticales legítimos (300×427 es un póster,
no una miniatura) → ahora va por el lado corto; y perseguía bandas planas en
afiches ajenos, donde una franja de color sólido es una decisión de diseño →
ahora solo en los EDITORIALES, que son los que recortamos nosotros.

**Decimoquinto: `[arquetipo-existe]` — el color que no existe se pinta gris.**
`[seccion-sin-arquetipo]` comprueba que la sección ESTÉ en `SECTION_ARCHETYPES`.
Nadie comprobaba que el arquetipo asignado sea uno de los NUEVE que tienen
color. Con CineAutopsia escribí «Apertura» e «Industria / Formación» —que suenan
bien y no existen: son «Apertura / Gala» y «Charlas / Industria»— y las dos
secciones cayeron al gris por defecto, con el texto encima ilegible.

Los dos validadores en verde y la pantalla rota. Lo vio Juan mirando la app, que
es donde se ven estas cosas: *«el gris está bien pero la letra no se lee
absolutamente nada»*.

**Y una regla de la misma tanda, sin guardián porque es de criterio:** el póster
de un PROGRAMA no puede ser un recorte de la página donde están los stills de
sus obras. Eso no es «la imagen del programa», son dos obras suyas pegadas —y
encima con la franja del encabezado—. Solo vale recortar la página cuando ésta
NO lleva stills de obras: el Encuentro, cuya página es un mosaico de retratos de
los artistas, sí es la imagen del evento.

**Y la deuda quedó en CERO el mismo día.** Los nueve huérfanos salieron:
`trailer`, `tematica` y `qa_detail` primero; después `original_title` (con
`title_orig` ya unificado dentro), `filmType` y `cycle`; `_tmdbId` se fusionó en
`tmdb_id`. `cycle` merece una nota: las franjas de FICMA —«Cine al barrio»,
«Cine bajo la niebla»— **sí eran palabra del festival e información que
`section` no da**. Salió igual, porque no se iba a pintar, y sigue viva en el
crudo: si algún día se muestra, no hay que volver a extraerla. **Borrar del JSON
final no es perder el dato** — el crudo es el archivo, el JSON es la vitrina.

**Y el epílogo (17 ago 2026).** Hubo un guardián —`titulo-original-util`, sin
corchetes porque ya no existe— que exigía que `original_title` dijera algo que
el `title` no dijera. Duró unas horas: al preguntarnos si íbamos a pintarlo alguna
vez, la respuesta fue no, y entonces el campo entero salió del repo —dato,
productores y plantillas—. **Un campo limpio que nadie lee sigue siendo peso
muerto**, y un guardián que cuida un campo que ya no existe es peso muerto al
cuadrado. El `titulo_original` de los sidecars SÍ se queda: `enriquecer.py` lo
usa para decidir el `title_en`, que eso sí se ve.

**Noveno, el del silencio: `[boleteria-muda]`.** Los guardianes de boletería
que ya teníamos vigilan la COHERENCIA de lo que se emite —que el badge lo
decida `ticketBadgeTarget()`, que `ticketing_model` use el vocabulario real,
que no se escriba `ticketUrl` en camelCase—. Ninguno vigilaba la AUSENCIA: un
festival vigente podía salir sin **una sola** función que dijera cómo se entra,
y todo quedaba verde.

Lo destapó CineAutopsia el 17 ago 2026. La agenda de la Cinemateca publicaba el
enlace de TuBoleta de los seis programas de pago y decía «Entrada libre» en la
clausura; mi ensamblador no miró el campo y encima escribió `is_free: false` en
los siete, también en el libre. El dato estaba en la misma página de la que
saqué todo lo demás. Lo cazó Juan preguntando —igual que los 638 enlaces de
TIFF y las 415 banderas de FICDEH—.

La regla: **gratis se declara, no se deja en blanco.** Un festival vigente cuyas
funciones no dicen nada —ni `ticket_url`, ni `is_free`, ni
`registration_url`— está mudo, y el silencio no es un dato, es una omisión.
Solo aplica a los vigentes: reescribir el pasado de un festival archivado no le
sirve a nadie.

**Octavo, y el que explica por qué lo de FICDEH costó meses:
`[paridad-derivados]`.**

`flags` es un campo **derivado**: no existe en ninguna fuente. Ningún PDF,
ningún Excel, ninguna web de festival trae banderas — las calculamos del país.
Y ahí está la trampa: **una ausencia que nunca fue presencia no se nota.** Si
falta un título salta a la vista, porque la fuente lo tenía y lo perdimos. Si
falta `flags`, no hay nada río arriba de donde se haya caído.

FICDEH corrió su festival entero con 415 films mostrando país y ninguna
bandera. Su ensamblador era a medida —PDF, Excel, web y tuboleta— y nunca
escribió el campo; los otros doce lo emiten porque salieron de la plantilla.

**La regla: para cada par (fuente → derivado), un film con la fuente tiene que
tener el derivado.** Los pares se declaran en el guardián y se **midieron
antes de entrar**: `day→day_order`, `day→time`, `poster→posterSource` y
`synopsis→synopsis_lang` se cumplen hoy en los 12 festivales publicados, 1.209
films sin una sola excepción. No es una aspiración: es un invariante que ya se
sostenía y que ahora no se puede romper en silencio. `country→flags` va aparte
y solo cuenta como hueco si la bandera **se podía** derivar — un país fuera de
tabla («Varios», o un idioma colado en el campo) es otro problema, y de ese se
ocupa `[country-flags]`.

**Ojo con la regla ingenua «campo presente en N−1 festivales»:** daría falsos
positivos con `is_cortos` y `film_list`, que faltan legítimamente donde el
festival no tiene programas de cortos. **Lo que distingue un hueco de una
ausencia legítima es la dependencia, no la frecuencia.**

**Regla nueva para todo ensamblador:** emitir `_cuentas` con `entradas`,
`publicadas` y `descartadas` desglosadas por motivo. Declarar los descartes
obliga a mirarlos; que sumen impide inventarlos.

**Y la lección de método:** un guardián que nunca ha fallado no es de fiar.
Los cuatro se probaron contra un sidecar roto a propósito antes de darlos por
buenos, y ahí se cayó uno: `[sidecar-vacio]` usaba
`_listas.get(a) or _listas.get(b)`, y **una lista vacía es falsa en Python**,
así que el guardián de las listas vacías se dejaba vencer justo por una lista
vacía. Se pregunta por PRESENCIA, no por verdad.

### Fase 2 · Configuración en FESTIVAL_CONFIG `[Senior Dev + PM]`

**Objetivo:** El festival existe en la app con su configuración completa.

> **La Fase 2 no se difiere — retro QAFF (23 ago 2026).** QAFF se montó el 2 ago
> con datos al 100% y pasó tres semanas de fases posteriores SIN entrada en
> `FESTIVAL_CONFIG`. Consecuencia: los guardianes de festival vigente no lo
> veían, y el día de publicar destaparon 4 errores de golpe (banderas, keyArt,
> paridad de nombre) más 96 commits de guardianes nuevos que nunca habían
> corrido contra él. La entrada en config no publica nada —la rama no llega a
> producción hasta el merge—: lo único que hace es poner el festival bajo
> vigilancia desde el día 1, para comerse los errores de a uno y no en bloque.

1. Crear entrada en `FESTIVAL_CONFIG` dentro de **`src/config.js`** (post-Fase 8; el bloque salió de `index.html`). `generate-config.js` genera el bloque listo para pegar:
   ```js
   'festival-id': {
     id: 'festival-id',
     name: 'Nombre común/marca',     // el display (selector + header) usa la 1ª palabra
     fullName: 'Nombre OFICIAL completo',  // OBLIGATORIO — verificado en fuente; se muestra al expandir el selector
     shortName: 'ABREV',             // deprecado para display; histórico
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

   > **Regla de nombres (obligatoria).** Cada festival lleva **tres** identidades:
   > - `name` — nombre **común/marca**. El display en TODA la app (selector del splash, selector in-app, header) deriva de aquí: `festivalLabel()` = 1ª palabra de `name` + ` · ` + `year`. Ej.: `'Ficmontañas'` → "Ficmontañas · 2026".
   > - `fullName` — nombre **oficial completo**, **verificado en la fuente oficial del festival** (sitio propio, no Wikipedia ni terceros). Se muestra **al expandir** el item en el selector. Ej.: `'Festival Internacional de Cine en las Montañas'`. **No fabricar** — si la fuente no lo da con claridad, parar y consultar.
   > - `shortName` — **deprecado para display** (era una sigla en MAYÚS). Se conserva por compatibilidad; no usar en render.
   >
   > `generate-config.js` exige `--fullname` como argumento obligatorio. Onboarding sin `fullName` no pasa.

2. El JSON del festival **no lleva bloque `config{}`** — nunca.

3. Emojis de sección aprobados por PM + Content Designer.

3b. **Secciones nuevas — TRES registros en `src/config.js` (obligatorio):**
   - **Emoji único** líder en el string de sección (el string CON emoji es la clave en todos los mapas).
   - **`SECTION_EN`** — display en inglés (warning `[i18n-content-coverage]` si falta).
   - **`SECTION_ARCHETYPES`** — asignar uno de los **9 arquetipos** (Gala, Competencia, Clausura, Especiales, Retrospectiva, Muestra/País, Perspectivas/Miradas, Industria/Formación, Cortos). Sin arquetipo, `_sectionColor` cae a gris ilegible `#2C2C2A` → **ERROR bloqueante `[seccion-sin-arquetipo]`**. La paleta y el auto-contraste viven en `docs/POSTERS.md` §8b.

4. **Ticketing (obligatorio evaluar en cada festival).** En el root del JSON:
   - `ticket_url` (`https://`) + `ticketing_model` (`"paid"` o `"mixed"`) si el festival cobra entrada o es mixto.
   - Festival 100% gratuito → omitir ambos campos.
   - Festival `"mixed"` → marcar `is_free: true` en cada screening gratuito (verificar contra el sitio oficial de entradas).
   - Recordar: `ticket_url`/`ticketing_model` ya están en el whitelist `_cfgFields` de `loader.js`. `is_free` ya pasa por la explosión de screenings.

5. **keyArt — el afiche del splash se ESTIRA a 2:3 (regla permanente).**

   > **REGLA (Juan, 6 ago 2026):** el afiche se **estira en un eje** hasta
   > 400×600. **No se recorta, no se rellena con bandas, no se difumina.**

   La card del riel es 2:3 exacto con `object-fit:cover`, así que recorta todo
   afiche que no lo sea — y los afiches de festival casi nunca son 2:3 (suelen
   ser 3:4 o serie A). Medido en ago 2026: 7 de 10 se recortaban, hasta +19,5%
   (Tercer Tiempo perdía casi un quinto del afiche, patrocinadores incluidos).

   Se evaluaron tres caminos con afiches reales a tamaño de card: banda de color
   plano (deja línea dura), blur del propio afiche detrás (mejor, pero sigue
   siendo un marco alrededor de un afiche chico) y **estirado** — que llena la
   card, deja leer el afiche entero y **no se percibe**. Compresiones reales:
   5,7% / 5,9% / 7,4% / 16,3%; aprobado incluso en el peor caso. **Sin umbral ni
   excepciones**: se estira siempre, para que ningún onboarding tenga que decidir.

   ```bash
   python3 scripts/compose-keyart.py assets/keyart/<fest>.jpg
   ```
   **Write-once**: escribe a `-v2` y NUNCA sobreescribe — el SW cachea
   `/assets/` cache-first para siempre, y sobreescribir dejaría a los usuarios
   recurrentes viendo el afiche viejo. Actualizar el path en `config.js`.
   Con el afiche completo, `keyArtPos` deja de tener sentido: quitarlo.
   Verifica el guardián **`[keyart-2-3]`** (falla sobre 2% de desvío).
   `--check` diagnostica sin escribir; `--all` procesa todos.

**Gates de salida (bloqueantes):**
- [ ] JSON sin `config{}`
- [ ] `storageKey` único (verificar contra todos los festivales)
- [ ] `festivalEndStr` presente y correcto
- [ ] `country` presente (necesario para `flagFmt`)
- [ ] Ticketing evaluado: `ticket_url` + `ticketing_model` presentes (o ambos ausentes si es gratuito); `is_free` marcado en funciones gratuitas si es `"mixed"`
- [ ] `keyArt` en 2:3 (`[keyart-2-3]` en verde) — estirado con `compose-keyart.py` si el afiche original no lo era

---

### Fase 3 · Enriquecimiento TMDB `[Data Engineer — algoritmo aprobado por Senior Dev]`

**Objetivo:** Poblar `genre` y `year` con datos verificados. **No poster. No synopsis_en.**

> ⚠️ **Lección aprendida (Tribeca 2026):** El algoritmo de matching usa `year` como criterio de validación. Si `year` viene corrupto del scraping (como ocurrió con 37 films de Tribeca), la validación falla silenciosamente y TMDB asigna datos de un film completamente distinto. `synopsis_en` de 64/107 films describía otra película. Ningún campo de TMDB puede considerarse verificado sin revisión humana previa.

**Algoritmo de matching estricto — gate v2 (afinado con los 32 casos reales de Tercer Tiempo 2026, PR #301):**

| Criterio | Regla v2 |
|----------|-------|
| Título | Similitud > 0.6 con título TMDB o título original (obligatorio siempre) |
| Año | Diferencia ≤ 1; hasta ≤ 2 **solo si** el director corrobora (año de festival vs año de estreno difieren con frecuencia) |
| Director | Intersección de **tokens de nombres completos** exigiendo apellido exacto de un lado como token del otro — `Guareño` matchea `Guareño Genesta` (apellidos compuestos), `Costa` NO matchea `Originario` |
| País | Match laxo por substring **tras normalizar ES→EN** (`CTY_ES2EN`: nuestro JSON guarda 'España', TMDB en-US responde 'Spain' — sin el mapa, jamás coincidían) |

- Corroboración mínima: **≥2 de {año, director, país}** evaluables y aprobados — el título solo **nunca** alcanza (caso Brujo). Excepción única: **registro TMDB escaso** (cine nicho sin año/país cargados) se acepta con 1 corroborante SOLO si es el director Y título ≥0.9 (director+título casi exacto no es el caso Brujo).
- Si un criterio evaluable falla → el film queda **sin TMDB** (no se asigna ningún dato); los rechazos se loguean.
- Búsqueda con variantes cuando la query literal da 0 candidatos: sin comillas tipográficas, sin subtítulo tras `: . —`.
- Se consultan hasta 3 resultados por (media × query); `movie` y `tv` en ese orden.
- **Implementado y testeado:** `enrich-festival.py` (función pura `match_ok`). `python3 scripts/enrich-festival.py --selftest` corre 14 fixtures — incluidos los 4 falsos rechazos de TT que deben pasar y los 4 homónimos genuinos que deben seguir fallando. El script escribe **solo `genre`, `year` y `lbSlug`**.

**Doctrina de rechazos (lección TT 2026 — dos veces + FantasoFest):**
1. **Un rechazo del gate NO es evidencia de ausencia en TMDB/LB.** Antes de concluir "no existe", auditar los rechazos cuyo candidato tiene título ~1.0: en TT, 10 de esos "rechazos" eran la película correcta con el gate viejo defectuoso.
2. **Rechazo por director ⇒ verificar el crédito de la FUENTE contra el registro canónico** (TMDB/LB + prensa). En TT, la ficha de la Cinemateca acreditaba al guionista como director (*El documental del 10*): el gate rechazaba "correctamente" un dato equivocado. El fix es corregir el dato, no aflojar el gate.
3. **Confirmar la AUSENCIA con búsqueda directa en LB — y rechazar homónimos.** Si tras auditar el rechazo el film sigue sin match, buscarlo **directo en `letterboxd.com/search/films/<título>/`** para confirmar que genuinamente no está (no solo confiar en que el enricher no lo halló). En FantasoFest, *Peephole* (Sarmiento Bazzani, 2020) y *Mutante* (Tabares/Martínez, 2022) tienen MUCHOS homónimos en LB (Peephole 1993/2004/2015/2018/2025…) pero NINGUNO es el nuestro → **quedan sin `lbSlug`, y eso es correcto**. Adjuntar un homónimo (`peephole-2018`) sería el error. Ausencia real verificada = sin link es el estado honesto; la UI oculta el botón.

**Campos aceptados de TMDB (solo si vacíos en el JSON):**
- `genre` → campo en el objeto film (si vacío) — error tolerable, no visible como dato crítico
- `year` → campo en el objeto film (si vacío) — solo si el año del scraping fue verificado primero

**Campos PROHIBIDOS desde TMDB sin verificación humana:**
- ❌ `poster` → **NUNCA desde TMDB sin verificación visual manual**
- ❌ `synopsis_en` → **NUNCA desde TMDB sin verificación que describe el film correcto**
- ❌ `director`, `country`, `language` → solo desde el scraping de primera fuente

#### Sinopsis (`synopsis` / `synopsis_en`) — gate film-por-film (gate, no opcional)

> ⚠️ **Lección Brujo / Tribeca 2026.** La sinopsis es el campo de **mayor riesgo de match equivocado**: un corto extranjero con título corto ("Brujo") suele estar ausente de TMDB → el match por título traía la sinopsis de **otra película**. La auditoría retroactiva halló **9 casos además de Brujo** (PR #181: *Summer War*, *Unidentified*, *I Spy With My Little Eye*, *Memorizu*, *Seven O'Clock Breakfast Club*, *Found&Lost*, *The Barbershop*, *32 B*, *Odessa*). Mismo nivel de gate que pósters y slugs — **no es opcional**.

1. **Fuente: la página oficial del film en el sitio del festival, verbatim.**
   La sinopsis sale de **primera fuente** (igual que el póster: la fuente del festival manda sobre TMDB). Festival bilingüe nativo → `synopsis` + `synopsis_en` **ambos de primera fuente**. Festival en un solo idioma → `synopsis_en` por **traducción manual con pase de Content Design**. **TMDB jamás** llena `synopsis_en` (`enrich-festival.py` ya no lo escribe).

2. **Verificación por anclas — director · país · duración (gate).**
   Para **cada** film, confirmar que la sinopsis describe la película de **ese** director, **ese** país y **esa** duración. Si la premisa no encaja con las tres anclas → es match equivocado, **rechazar**. *(Así se cazaron* Summer War *—directora chilena con sinopsis de un documental finlandés de la 2ªGM— y* Unidentified *—directora saudí con sinopsis de sci-fi en Nevada.)*

3. **Prioridad de escrutinio — el "perfil-Brujo" primero.**
   Cortos de origen **no-anglo** + título de una o dos palabras + presencia débil en TMDB son los de mayor riesgo de colisión. Verificarlos primero. Para festivales ya onboardeados con el método sin afinar, correr la auditoría retroactiva sobre esta clase (rankear → traer verbatim oficial → comparar contra anclas → veredicto).

#### `title_en` vs `synopsis_en` — buscar el oficial vs traducir (regla FantasoFest 2026)

Asimetría clave, misma doctrina "leer, no inventar":

- **`title_en` = título internacional OFICIAL, buscado y verificado. NUNCA
  máquina-traducción.** Un título es una decisión creativa del realizador/
  distribuidor, no un texto traducible: "La Virgen de la Tosquera" → el oficial
  es **"The Virgin of the Quarry Lake"** (Sundance/Sitges), no "…of the Gravel
  Pit"; "El Ritual del Nahual" → **"Tekenchu: The Rite of the Nahuales"**, no
  "The Ritual of the Nahual". Se busca en Letterboxd / circuito de festivales /
  IMDb y se verifica (200 + director/año). **Si el film no tiene título en inglés
  registrado, se deja el español tal cual (sin `title_en`)** — nunca inventar uno.
- **`synopsis_en` = traducción SOLO cuando no existe una oficial.** Festival
  bilingüe nativo → ambas de primera fuente. Festival hispano sin sinopsis EN
  oficial → se produce por traducción fiel con pase de Content Design (no hay
  artefacto oficial que buscar). Por eso las `synopsis_en` son traducción propia
  y los `title_en` no.

Regla mnemónica: **si el dato oficial existe (título de circuito), se busca;
si no existe (sinopsis EN de festival hispano), se produce con cuidado.**

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

**Jerarquía de poster + póster editorial de programas → `docs/POSTERS.md`** (fuente
única). Resumen: la adquisición sigue las 5 fuentes (TMDB/LB portrait verificados
→ portrait oficial → landscape oficial editorial-con-imagen → editorial sin
imagen), el landscape no se vacía, `poster: ""` es exclusivo de programas, y el
body del póster de programa es el identificador único (código `PGM 05` o nombre
propio) sacado del título original. Gates: `[poster-editorial-unique]` y
`[poster-empty-film]` en `validate-festivals.js`.

---

### Fase 3b · Letterboxd slugs `[Data Engineer]`

**Objetivo:** Poblar `lbSlug` por film para que cada film muestre enlace a Letterboxd.

> ⚠️ **Regla absoluta:** Los slugs de Letterboxd NUNCA se infieren desde el título. El slug se resuelve desde un identificador verificado (TMDB id que pasó el gate) o se extrae del DOM de Letterboxd y se verifica individualmente. Inferir slugs produce errores silenciosos — un slug plausible puede apuntar a un film completamente distinto.

#### Método PRIMARIO — vía enricher (automático, desde TT 2026)

`enrich-festival.py` Fase 2 resuelve el slug canónico vía `letterboxd.com/tmdb/{id}/`
(redirect → og:url) **solo para matches que pasaron el gate v2** — la verificación
identidad-película ya la hizo el gate. Comportamiento:
- Sin match → el campo `lbSlug` queda **AUSENTE** (la UI oculta el link). El
  marcador `⚠️ LB PENDIENTE` **ya no se escribe al JSON** (viajó a prod en TT y
  habría producido hrefs rotos); los pendientes salen solo en el log del run.
- **Verificación final obligatoria:** por cada slug nuevo, GET a
  `letterboxd.com/film/{slug}/` → 200 + director de la página coincide con el
  nuestro (en TT: 12/12 verificados así antes del merge).

#### Método de RESCATE — Chrome tab / manual (para sin-match que se encuentren a mano)

Cuando alguien encuentra en LB un film que el enricher no resolvió: primero
auditar POR QUÉ (¿falso rechazo del gate? ¿crédito equivocado en la fuente? —
ver doctrina de rechazos en Fase 3); corregir la causa raíz y re-correr. Solo si
el film genuinamente no está en TMDB, insertar el slug a mano con la
verificación individual de abajo.

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

#### Método de CREACIÓN — dar de alta la película en TMDB (probado con Chist · Leviza 2026)

Para films que **genuinamente no existen** en TMDB (el residuo tras enrich).
Doctrina: la app aporta a la base de la cinefilia, no solo la consume — así cada
obra tiene su página de Letterboxd. **Solo se dan de alta films con póster real
de ≥500px de ancho** (regla de Juan + mínimo de TMDB): el alta es exclusivamente
para que en LB se vea bien, no para sembrar fichas vacías ni huérfanas sin imagen.

> 🚦 **GATE PRIMERO — correr `python3 scripts/tmdb-gaps.py <festival.json>` ANTES de
> abrir cualquier alta.** El script mide cada póster y separa las obras en **APTAS**
> y **BLOQUEADAS**, con dos criterios que el uploader de TMDB aplica por separado:
> **ancho ≥500px** y **proporción entre 0.66 y 0.71** (w/h). **No se abre el alta de
> una obra bloqueada** — primero se arregla su póster. Cuando el festival tiene
> sidecar `<id>-posters-src.json`, el gate juzga el **original de la fuente** (que es
> lo que se sube, no el asset optimizado de la app) e imprime su URL en `Subir:`.
>
> Las dos lecciones que lo construyeron, ambas pagadas con fichas rebotadas:
> - **Resolución** — ensayo «Al son que me toquen bailo» (21 jul 2026): el asset era
>   298px → TMDB lo rechazó y quedó una ficha huérfana. Casi todos nuestros pósters
>   de films son ~300–500px (optimizados para la app) → hay que bajar el original.
> - **Proporción** — tanda FICDEH (25 jul 2026): el original de *Amalgama* medía
>   1857×2560 (**0.725**) y TMDB lo rechazó por *aspect ratio* **después** de crear la
>   ficha; entró tras un recorte centrado a 1792×2560 (0.700). Los 700×1000 de la
>   fuente (0.700) pasaron los seis. El gate ya sugiere el recorte exacto.

> ⚠️ **Límite de plataforma:** la API de TMDB **no crea películas ni sube imágenes** —
> ambas son solo por web y **requieren login**. Claude nunca escribe contraseñas:
> **el login SIEMPRE lo hace Juan**. El alta la conduce Claude por navegador
> (Chrome extension) una vez la sesión está autenticada.

**Antes de crear — descartar que ya exista (2 formas):**
1. Buscar en TMDB por título original **y** `title_en`. Si aparece → no crear;
   resolver el slug con el método PRIMARIO/RESCATE.
2. **Buscar también como SERIE.** Si existe pero como **serie**, Letterboxd **no
   la mostrará** (LB es solo películas) → **saltar** (no forzar un alta de film).
   Caso real: «Sin la Luz Perpetua» estaba como serie → se dejó sin `lbSlug`.

**Alta (formulario `themoviedb.org/movie/new`):**
- **País de origen:** el formulario **precarga «España»** (locale es-ES) → cambiarlo
  al país real (Colombia, etc.). Trampa fácil de pasar por alto.
- **Fecha de estreno:** si solo se tiene el año → `AAAA-01-01`.
- **Duración, sinopsis (original):** de la ficha del festival.
- **Póster:** subida **también web-only**, y la extensión solo sube **archivos que
  el usuario ADJUNTA al chat** — NO toma rutas del disco. Probado y descartado (21
  jul): `assets/` con directory-grant, scratchpad y Desktop → **todas rechazadas**.
  La barrera es *quién* introdujo el archivo (solo lo adjuntado por el usuario), no
  *dónde* está; es una red anti-exfiltración, no un límite tonto. → **Juan adjunta
  el póster al chat** (para un lote, un arrastre masivo de todos). Requisitos TMDB:
  **≥500px de ancho** y **ratio 0.66–0.71** (rechaza fuera de rango → ver el GATE).
  Nuestros assets están optimizados para la app → **no sirven**; hay que conseguir el
  **original de prensa** en alta (press kit del festival / canal oficial).
  **Vía que funcionó (25 jul 2026), cuando el adjunto al chat no llega al disco:**
  usar el **Browser integrado** (`preview_start` con la URL de TMDB) — Juan se loguea
  ahí una vez y Claude conduce todo (⊕ «Añadir cartel», idioma, siguiente ficha)
  **salvo el diálogo de archivos**, que es una ventana de la app de Claude y por eso
  es lo único que Claude no puede tocar jamás → **un doble clic de Juan por póster**.
  Tras subir, poner **Idioma = Español; Castellano (es-ES)** en el cartel (si el
  cartel tiene texto): el desplegable acumula lo tecleado si se repite el intento —
  escribir el filtro UNA vez y clicar la opción; verificar con
  `GET /movie/<id>/images?include_image_language=es,xx,null` que `iso_639_1` sea `es`.
- **Equipo → Director:** en «Añadir nuevo miembro del equipo» buscar la persona.
  Si hay **homónimos** (TMDB suele mostrar varios), **no atar a un perfil existente
  sin certeza** — meter la persona equivocada ensucia una base pública. Regla de
  Juan: si no hay certeza → **«Créalo»** (persona nueva con el nombre). TMDB fusiona
  duplicados después; una atribución errada es peor. Solo atar a existente si la
  comparación (créditos, festival hermano) lo confirma sin duda.

**Tras el alta — resolver el slug:**
- Letterboxd importa el **texto al instante** (la página `letterboxd.com/film/<slug>/`
  ya existe), pero el **póster tarda** en propagar — normal, no reintentar.
- Resolver el slug canónico vía el redirect `letterboxd.com/tmdb/<nuevo-id>/` y
  escribirlo como `lbSlug` en el JSON (para ítems de `film_list`, dentro del ítem).
- Verificación final igual que el método PRIMARIO (GET a `/film/<slug>/` → 200 +
  director coincide).

**Qué es 100% automático y qué no (para dimensionar un lote grande):**
- **Ya existe en TMDB** (el grueso) → 100% automático vía `enrich-festival.py`. Sin
  navegador, sin póster, sin intervención.
- **Hay que crear** (el residuo) → alta por navegador. El póster lo sube Claude
  **si `assets/` está conectada a la sesión**; si no, es el único arrastre de Juan.
  Las **ambigüedades de persona** son lo único que pide criterio humano.

---

### Fase 4 · Validación automática `[automatizado — validate-festivals.js]`

```bash
node scripts/validate-festivals.js [festival-id]
```

**Gates bloqueantes (exit code 1 = no se hace push):**
- `config{}` presente en el JSON
- Título con 3+ palabras en ALLCAPS
- Cobertura de poster = 0%
- `ticket_url` presente sin `ticketing_model` válido (`"paid"`/`"mixed"`)
- `ticket_url` que no empieza con `https://`
- `ticketing_model` presente sin `ticket_url`
- `is_cortos: true` con `film_list` vacío (cáscara — invisibiliza cortos reales)
- **`[poster-map-legacy]`** — `posters{}`/`customPosters{}` a nivel raíz (el modelo map murió en jul 2026; un film = un `poster` inline)
- **`[poster-source]`** — póster inline sin `posterSource` (correr `classify-posters.py --apply`)
- **`[seccion-sin-arquetipo]`** — sección usada sin entrada en `SECTION_ARCHETYPES` (caería a gris ilegible)
- `[poster-editorial-unique]` / `[poster-empty-film]` / `[posters-duplicados]` / `[sinopsis-duplicada]` — ver `docs/POSTERS.md` §8 y `FESTIVAL-CHECKLIST.md`

**Warnings (no bloquean pero requieren revisión antes del deploy):**
- Cobertura de poster < 95%
- Cobertura de género < 80%
- Duración ≤ 0 o > 400 min
- Venue vacío
- Sinopsis > 600 chars (condensar)
- Emoji de sección duplicado (salvo retrospectivas)

> **Cortos sin horario:** NO se pausan fuera del JSON. Se montan como **catálogo
> vivo** (`is_cortos` + `unscheduled` + `film_list`, sin `day`/`time`) — buscables
> en el acto; la jornada se asigna cuando el festival la publique. Ver `docs/SCHEMA.md`.

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

- **La rama de un festival trae `main` cada semana.** El coste de la fusión es
  lineal si es semanal y cuadrático si se acumula: QAFF cruzó 132 commits de
  una vez (23 ago) y absorbió 96 cambios de guardianes el día que quería
  publicar; TIFF publicó desde una rama cuyo `validate.py` viejo daba verde
  sobre un `config.js` roto. Una rama congelada no está «estable»: está
  acumulando deuda de guardianes que va a pagar entera el día del merge.

| Regla | Detalle |
|-------|---------|
| `config{}` prohibido en JSON | La configuración vive en `FESTIVAL_CONFIG` en `src/config.js` siempre |
| Matching TMDB estricto | Los 4 criterios simultáneos — pero solo válido si los datos de entrada fueron verificados primero |
| TMDB para poster: prohibido | `poster` (inline; el modelo map murió) solo desde verificación visual humana — nunca automatizado |
| TMDB para synopsis_en: prohibido | synopsis_en solo desde traducción manual o fuente verificada — 64/107 de Tribeca eran de films distintos |
| `og:image` en fase 1 | Se captura en extracción, no como parche posterior |
| Day keys ISO | `YYYY-MM-DD` desde Tribeca 2026. Los festivales legacy mantienen su formato pero no se replica |
| Validate antes de push | `validate-festivals.js` no es opcional. Un push que falla se revierte |
| Arquitectura antes de ejecución | El algoritmo de matching, la prioridad de posters y el schema de datos se aprueban antes de implementar |
| Cero decisiones de arquitectura en ejecución | El Data Engineer no decide el criterio de matching — lo aprueba el Senior Dev antes de correr el script |
| Eventos: planificable vs informativo | `type:event` con horario que el asistente "reserva" (masterclass, conversatorio, panel, gala, bloque de cortos) → `duration` (estimada si no se publica). Drop-in / sin hora fija (exposición, visita guiada, recorrido, fiesta, concierto, performance) → `info:true`: no entra al plan ni a conflictos. **El default es planificar** — somos planificadores, `info` es la excepción mínima. Ver `docs/SCHEMA.md` (campo `info`). |

---

## Doctrina de fuentes — leer, no inventar (probada en FICMontañas 2026)

La regla madre del onboarding: **cada dato sale de una fuente oficial leída
página a página; lo que la fuente no da, NO se fabrica** — se para y se
consulta a Juan. De esa regla derivan estos mecanismos, todos probados en
producción durante FICMontañas 2026:

1. **Jerarquía de verdad: el último post/PDF oficial DETALLADO manda.**
   Cuando el festival publica el cronograma definitivo (post de IG, PDF de
   programación), ese documento es la fuente de verdad. **Lo provisional que
   difiera, cambió** — no se promedia ni se conserva "por si acaso". Cada día
   publicado se reconcilia EXACTO al oficial (hora, sede, orden).

2. **`_parked` — provisionales guardados, no borrados.** Un evento del research
   que NO aparece en el post oficial del día se mueve al array top-level
   `d._parked`: invisible para la app (que lee `films`) y exento del validador,
   pero recuperable si reaparece en el post de otro día. Nunca borrar datos de
   research; nunca mostrarlos sin confirmación oficial.

3. **`unscheduled` — catálogo vivo, no pausa.** Films/cortos confirmados en el
   programa pero sin horario publicado NO se dejan fuera del JSON: se montan
   como catálogo (`is_cortos` + `film_list` + `unscheduled:true`, sin
   `day`/`time`) — buscables desde el día 1; la jornada se asigna cuando el
   festival la publique. Ver `docs/SCHEMA.md`.

4. **Sinopsis: VERBATIM verificado contra el DOM.** La sinopsis se extrae de la
   página oficial y se verifica contra el DOM real (fetch/Chrome) — **nunca de
   la memoria del modelo**, aunque "conozca" el film. Después el pase de
   Content Design condensa/traduce (aprobación de Juan). Caso testigo: El
   Huaquero (film inédito — la única fuente en el mundo era la página del
   festival).

5. **Instagram se lee por PÍXELES, no por metadata.** El CDN de IG no permite
   descarga directa (URLs firmadas) y el alt-text OCR no es confiable →
   navegar el post con Chrome MCP, avanzar slide por slide (flecha, no
   deep-links `?img_index=`), screenshot y leer píxeles. Extraer TODOS los
   slides antes de modelar.

6. **Nombres oficiales exactos.** Secciones, títulos y sedes usan la taxonomía
   del sitio/afiche oficial verbatim (con sus tildes y mayúsculas). Si el
   afiche y el sitio difieren, gana el más reciente y se anota el conflicto.
   `fullName` del festival: verificado en la fuente oficial — **no fabricar;
   si no está claro, parar y consultar**.

7. **Assert antes de leer, binding después de escribir.** En SPAs: confirmar
   que el DOM renderizó el film esperado antes de extraer (título/og:image
   coincide). En pósters: si el CDN embebe el id del film, verificar
   `poster.includes(filmId)`. La lectura sin assert produce el dato del film
   anterior — el error más silencioso del método.

8. **Procedencia obligatoria — la doctrina hecha verificable (pipeline v2).**
   Todo festival nuevo declara **`_provenance: true`** en el root del JSON, y
   **cada film top-level lleva `_src: {url, date}`** — la URL de la fuente
   oficial de la que salieron sus datos y la fecha de extracción (los cortos de
   `film_list` heredan el `_src` del bloque salvo `_src` propio). El gate
   **`[sin-procedencia]`** (ERROR) bloquea films sin fuente declarada: dato sin
   fuente = dato no confiable. Así la auditoría deja de "verificar el mundo" y
   pasa a **muestrear contra la fuente declarada** — y el dashboard
   (`tools/audit.html`) enlaza cada film a su fuente con un clic. La app ignora
   `_src` (prefijo `_`, no se renderiza).

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
| Secciones inventadas (TT 2026) | "Selección Oficial" agrupaba sesiones que el festival nombra una a una — re-seccionado completo (PR #295) | Regla Fase 1: sección = nombre oficial de sesión, jamás etiqueta propia |
| Extractor solo-texto ignoró afiches de sesión (TT 2026) | 12 pósters de bloque oficiales no vistos; se recuperaron en pase posterior (PR #297) | Gate Fase 1: inventariar y clasificar TODAS las imágenes de cada ficha |
| Gate TMDB con falsos rechazos estructurales (TT 2026) | 10 películas con match título-1.00 rechazadas (país ES vs EN, apellidos compuestos, registro escaso, año festival vs estreno) → concluimos "no existen en LB" y era falso (lo cazó Juan) | Gate v2 (PR #301) + fixtures reales en `--selftest` + doctrina: rechazo ≠ ausencia, auditar rechazos con título ~1.0 |
| Marcador `⚠️ LB PENDIENTE` escrito al JSON (TT 2026) | Viajó a prod; habría producido hrefs rotos a Letterboxd | El enricher ya no escribe marcadores (pendientes solo en log) + guard en `lbUrlForFilm` |
| Crédito de la fuente equivocado (TT 2026) | Ficha Cinemateca acreditaba al guionista como director (*El documental del 10*) → el gate rechazaba "bien" un dato malo | Doctrina: rechazo por director ⇒ verificar crédito contra registro canónico (TMDB/LB + prensa) y corregir el DATO, no aflojar el gate (PR #302) |
| Contenido reciclado de edición pasada en el CMS (FantasoFest 2026) | La web mostraba 10 largos; 5 eran fantasmas de 2022 (fechas 20–27 jul con weekday de 2022, bloque rotulado "…2022") — modelar la web sola habría metido 5 films inexistentes | Cruzar contra el PDF/comunicado oficial (canon de qué está en el programa) + validar weekday↔fecha contra el año + fecha fuera de ventana = bandera roja (regla Fase 1 FantasoFest) |
| Póster de otra película del mismo director (FantasoFest 2026) | `AFICHE-Lqv` era "Los Que Vuelven" (Casabé 2019), NO "La Virgen de la Tosquera" (Casabé 2025) | Buscar el asset por TÍTULO en los uploads, no por proximidad/orden en la grilla; verificar que el póster corresponde a ESE film |
| `title_en` traducido a mano en vez del oficial (riesgo, evitado) | Traducir "La Virgen de la Tosquera" daría "…Gravel Pit"; el oficial es "The Virgin of the Quarry Lake" | Regla: `title_en` = título internacional OFICIAL buscado+verificado (LB/circuito/IMDb), nunca máquina-traducción; sin oficial → sin `title_en` |
| Still local 16:9 no recibía la banda editorial (FantasoFest 2026) | El sheet del corto detectaba editorial solo por CDN-URL, ignorando `posterSource` → still local caía a `<img>` recortado 2:3 | `_isEd3`/`_isEd4` honran `posterSource:'editorial'` (PR #305); still local de festival va con `poster`+`posterSource:'editorial'` |


### `[calendario-entero]` — un día que se dibuja tiene que existir para el reloj

La tira de días se arma con `dayKeys`; el reloj (`dayFullyPassed`,
`screeningPassed`, la detección de HOY) lee `festivalDates`. Son **el mismo
calendario**, y hasta el 23 ago 2026 tenían dueños distintos: `dayKeys` lo pisaba
el JSON del festival, pero `festivalDates` estaba clasificado como *identidad* y
el JSON solo podía rellenarlo si config lo tenía vacío.

CineAutopsia dibujaba 8 días y el reloj conocía 4. Los cuatro huérfanos no se
atenuaban nunca (`dayFullyPassed` corta con `if(!dateStr) return false`), sus
funciones no contaban como pasadas, y el 25/26/27 habrían roto la detección de
HOY con el festival en curso.

El guardián exige tres cosas:
1. Todo día de `dayKeys` tiene fecha en `festivalDates` — en config y en el JSON.
2. El calendario de config **coincide** con el de su JSON. Esta es la que caza el
   bug real: dentro de cada fuente todo cuadraba; lo que no cuadraba era una
   contra la otra, y ahí no miraba nadie.
3. `festivalDates` sigue siendo **contenido** en el loader, no identidad.


### `[calendario-sin-huecos]` — el día existe aunque esté vacío

**Regla (Juan, 24 ago 2026):** el calendario de un festival declara **todos** los
días entre el primero y el último, **incluidos los que no tienen programación**.
Un día vacío se declara; no se omite.

**Por qué.** CineAutopsia corre del 21 al 29 de agosto y no declaraba el 24. Con
el festival **en curso**, «Hoy» abría el VIE 21 —ya pasado— y «Mañana» el SÁB 29:
`findIndex` del día de hoy daba −1 y los fallbacks caían a los extremos del
array. Un día vacío **declarado** se atenúa solo y no rompe nada
(`dayFullyPassed` ya tiene su caso explícito); un día **ausente** deja un agujero
por el que se cuela la aritmética de índices.

**La convención ya existía y nadie la había escrito:** Tercer Tiempo declara
**siete** días con **dos vacíos** (14 y 19 jul) y cero huecos. FICDEH tampoco
tiene huecos. CineAutopsia fue la excepción.

**Al montar un festival:** si la programación salta un día, ese día va igual en
`dayKeys`, `days`, `dayShort`, `dayShort_en`, `dayLong` y `festivalDates`. El
guardián ignora los festivales legacy con rótulos en vez de fechas ISO (Leviza).


### `[genero-unico]` — una obra, un género, y de los comunes

**Regla (Juan, 24 ago 2026):** cada obra declara **un solo género**: el
**primero de la fuente que sea un género de verdad**. El orden de la fuente
manda; lo que no es un género se salta. Si no hay ninguno, el campo queda
**vacío** — inventarle un género a una obra es peor que no decir nada.

**Por qué.** TIFF traía **859 de 878 obras (97%)** con varios, y no eran
subgéneros: eran **etiquetas de programación del festival** mezcladas con el
género en el mismo campo.

```
Asian Cultures, Drama, Directed by Women, Coming of Age
Documentary, Aboriginal + Indigenous, Crime, Biography + History
```

Tomar «el primero» a secas habría publicado **«Asian Cultures» donde va
«Drama»**, en 271 fichas. No era solo TIFF: Tribeca 56, Olhar 19, FICDEH 29.

**El vocabulario no se inventa ni se copia.** Es `_GENRE_EN`
(`src/controller/sheets-controller.js`), la tabla que la app ya usa para
traducir géneros, con los nombres canónicos de TMDB. El validador la **lee** de
ahí: duplicar la lista crearía una segunda verdad que envejece sola.

**Dos formas de escribir que hay que reconocer al extraer**, encontradas
midiendo — el género es la **cabeza** del compuesto:

| fuente | género |
|---|---|
| `Experimental + Avant-Garde` (TIFF compone con `+`) | **Experimental** |
| `Comedia dramática` (el español compone con adjetivo) | **Comedia** |
| `Action + Adventure` | **Action** |

Sin reconocerlas, 28 obras se quedaban sin género **teniendo uno**.

**El gate:** varios géneros → **error bloqueante**. Un género fuera del
vocabulario → **warning**, porque puede ser una etiqueta colada… o un género
legítimo que falte en `_GENRE_EN`, y esa decisión es de quien monta.

