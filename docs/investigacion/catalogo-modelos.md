# Catálogo único de obras: modelos de referencia y recomendación

Investigación web de solo lectura (12 oct 2026). Objetivo: una obra que aparece en 3 festivales se resuelve UNA vez (TMDB, afiche, sinopsis, traducción, decisiones editoriales) y cada festival solo aporta su *presentación*.

## 1. Lo que dicen los estándares

**EN 15907 (CEN, 2010)** — el estándar europeo de identificación de obras cinematográficas. Cuatro niveles: **Work** (la creación intelectual: título uniforme, año y lugar de producción, autores, descripción de contenido — lo que no cambia entre versiones; la *extensión/duración NO se registra aquí*), **Variant** (cambios menores de contenido: cortes, versiones dobladas; si el contenido cambia tanto que la descripción cambiaría, es otra obra), **Manifestation** (encarnación física o digital, incluido un archivo; una manifestación puede contener varias obras) e **Item** (copia concreta). Más entidades **Agent** y **Event** (producción, estreno, premio). Ejemplo trabajado con *I Vitelloni*: el catalogador crea Work + una Variant "por defecto" + Manifestation del estreno original + Item de la Cineteca; el título uniforme vive en el Work.
- https://filmstandards.org/fsc/index.php/EN_15907
- https://filmstandards.org/fsc/index.php/EN_15907_Cinematographic_Work
- https://filmstandards.org/fsc/index.php/EN_15907_Variant
- https://filmstandards.org/fsc/index.php/EN_15907_Manifestation
- https://filmstandards.org/fsc/index.php/Description_levels:_A_worked_example

**FIAF Moving Image Cataloguing Manual (2016)** — misma jerarquía (work / variant / manifestation / item), alineada con FRBR, EN 15907 y RDA. El Work es "el nodo que liga todas las variantes y manifestaciones a una creación"; la Manifestation puede describir lo que una versión *debería* contener aunque no haya copia. Apéndices de títulos y listas de valores.
- https://muse.jhu.edu/book/51968
- https://www.efgproject.eu/downloads/S1_FIAF_CataloguingRules.pdf

**EIDR** — registro DOI (`10.5240/xxxx-...`) con árbol: **Abstraction** (la obra en su forma más general) → **Edit** (versión única: theatrical, director's cut, versión TV) → **Manifestation** (técnica: subtítulos y doblajes son manifestaciones, no edits) + **Collection**. El ID no revela el nivel; el Abstraction se deriva subiendo el árbol. Dedup: 15 años de reglas, desde abr 2026 ML (Tamr) + revisión experta; la API Match devuelve **Match / No Match / Candidates Found / Error** y con "candidates" exige decisión humana o de negocio, nunca auto-registro. Práctica: *Match → Evaluate → Register*, metadatos ricos, estrategia de títulos consistente, normalizar entrada.
- https://www.eidr.org/documents/Best%20Practices%20and%20Use%20Cases%20for%20Edits.pdf
- https://eidrdotorg.atlassian.net/wiki/spaces/ERL/pages/2328395805/Match+and+De-duplication+Strategy
- https://www.eidr.org/blog/eidr-modernizes-deduplication-efforts-2

**ISAN** — 96 bits en tres segmentos: **root** (obra), **episode** (parte), **version** (edición por territorio, audio, subtítulos). Sin semántica: todo lo descriptivo va en metadatos enlazados.
- https://support.isan.org/hc/en-us/articles/115003941311-What-is-the-structure-of-ISAN
- https://www.rfc-editor.org/rfc/rfc4246

**Lectura para ~1.500 obras:** los cuatro niveles son excesivos. Lo que sirve es la separación *obra (invariante)* vs *versión proyectada (duración, idioma, subtítulos)*, y la idea EIDR/ISAN de que el **identificador es nuestro y opaco**; los de TMDB/IMDb/ISAN son referencias cruzadas, no la clave.

## 2. Plataformas grandes

- **TMDB**: una entrada por obra; *no* acepta versiones alternativas (extended, director's cut, 3D) salvo excepciones "muy, muy raras"; rodajes simultáneos en dos idiomas = una entrada, el original fija `original_title` y `original_language`. Títulos: `original_title` + `translations` (oficiales por idioma) + `alternative_titles` por país con `type` (working title, DVD title…); nunca inventar traducciones. `release_dates` por país con tipo (premiere, theatrical, digital…) — el estreno en festival es un release tipo *Premiere* con país.
  - https://www.themoviedb.org/bible/new_content
  - https://themoviedb.org/bible/tv/59f73eb49251416e71000020
- **Letterboxd**: "film data comes from TMDB — submit changes there first"; conserva duplicados ya borrados en TMDB porque hay diarios logueados sobre ellos (lección: un ID que ya tiene actividad de usuario no se borra, se redirige).
  - https://letterboxd.com/contact/
- **IMDb**: `originalTitle` (título en país de primer estreno), `akas` (lista con país + idioma + atributo) y `titleDisplay` (subconjunto curado por país/idioma para mostrar). Tres capas: original / todas / la que se enseña.
  - https://developer.imdb.com/documentation/bulk-data-documentation/data-dictionary/titles
- **Wikidata**: P1476 título (monolingüe, en idioma original), P364 idioma original, P57 director, P495 país, P2047 duración, P577 fecha con P291 lugar como calificador, P144 *based on*. Versiones dobladas/traducidas = **ítem aparte** ligado con P629 (edition or translation of) + P407 idioma; versiones multilingües rodadas a la vez = P1889 *different from* con criterio Q2518205. IDs externos: P345 IMDb, P4947 TMDB, con restricciones *single value* y *distinct values* → dos ítems que comparten un P345 son sospecha automática de duplicado. Duplicados se **fusionan con redirect**, nunca se borran.
  - https://www.wikidata.org/wiki/Wikidata:WikiProject_Movies/Properties
  - https://www.wikidata.org/wiki/Property:P4947
  - https://codethecity.org/2023/09/ (merge práctico)

## 3. Agregadores de festivales

No publican esquema. Lo que se ve desde fuera: Cinando modela **film × festival event** (dataset de investigación: 77.398 films, 38.367 eventos, 183.865 pares) — la obra es fija y cada programación es un par con sección. Festival Scope ata su ventana al *premiere* del festival. En FilmFreeway el **premiere status** es un campo del formulario de cada festival (tiers World / International / Nacional / Regional / Ciudad) definido por *cada festival* y que cambia en el tiempo: la misma obra es "Colombian premiere" en uno y nada en otro. Conclusión: premiere status, sección, Q&A, invitados y versión proyectada son atributos de la **presentación**, no de la obra.
- https://figshare.com/articles/dataset/Cinando_film_festival_programming_dataset/22682794
- https://www.edfilmfest.org/wp-content/uploads/2025/12/EIFF-2026-Submissions-FAQs.docx.pdf
- https://2025.fantasiafestival.com/en/submissions/submissions-faq

## 4. Ingeniería de datos

- **MDM / golden record (DAMA-DMBOK, área Reference & Master Data)**: el golden record no es copia de ninguna fuente; se mantiene aparte una *linkage model/crosswalk* con IDs de origen, timestamps y procedencia. **Survivorship por atributo, no por fuente** (el festival manda en sección/horario; TMDB en año/director; Juan en sinopsis). Criterios habituales: jerarquía de confianza, recencia, completitud, frecuencia; restricciones duras (un campo no puede quedar vacío) mandan a cola de excepción. Matching con **tres salidas**: auto-match, auto-no-match, revisión manual. Modo "simulación" que muestra qué regla eligió cada campo antes de activarla.
  - https://profisee.com/blog/mdm-survivorship/
  - https://www.gravitee.io/corpus/gen-2469/master-data-management/golden-record-management-for-enterprise-master-data.html
- **Entity resolution**: Splink implementa Fellegi-Sunter — pesos parciales por comparación (coincidencia exacta, fuzzy, cercana), el peso refleja cuán informativo es el campo (alta cardinalidad = más peso), el umbral es específico del dataset y se elige en el "valle" del histograma, no en la ladera. dedupe.io: *active learning* (los ejemplos a etiquetar son los que más enseñan, no los representativos) y estimación de precisión/recall por umbral. OpenRefine: *key collision* con *fingerprint* (trim, lower, sin puntuación, sin acentos, tokens ordenados y únicos) como método más conservador; Levenshtein para cadenas cortas, n-gram para largas.
  - https://dataingovernment.blog.gov.uk/2022/09/23/splink-fast-accurate-and-scalable-record-linkage/
  - https://dedupe.readthedocs.io/en/latest/how-it-works/Choosing-a-good-threshold.html
  - https://docs.openrefine.org/technical-reference/clustering-in-depth

## 5. Casos documentados

- **BFI CID**: implementa "una parte significativa" de EN 15907 en un componente de filmografía sobre Adlib/Axiell, alimentado por transformación de bases legadas.
  - https://filmstandards.org/fsc/index.php/CEN_TC_372_Workshop_Series
  - https://help.collections.axiell.com/en/Topics/Moving%20image%20catalogue.htm
- **European Film Gateway / Europeana**: modelo común FRBR + EN 15907 (aplicado solo parcialmente); objetivo explícito "identificación inequívoca de obras catalogadas bajo distintos títulos de distribución"; consolidación de autoridades de obra y persona fue tarea de última fase; los restauradores objetaron que el cine mudo no tiene "original" único → propuesta de hacer el *evento de producción* entidad primaria.
  - https://euscreen.eu/2011/06/cen-standards-for-metadata-about-cinematographic-works/
  - https://www.efgproject.eu/downloads/cen-cws-synop-2009-06.pdf
- **Filmoteca Española**: "Inventario de cine español conservado", 5.863 títulos / 30.643 materiales, catálogo compartido entre archivos sobre AbsysNet (Baratz).
  - https://anabad.org/wp-content/uploads/2020/11/El-cat%C3%A1logo-%C2%ABInventario-de-cine-espa%C3%B1ol-conservado%C2%BB-re%C3%BAne-los-t%C3%ADtulos-que-custodian-los-archivos-f%C3%ADlmicos-de-Espa%C3%B1a-1.pdf
- **Ciné-Ressources**: catálogo colectivo de 4 cinematecas francesas desde 2007.
  - https://en.wikipedia.org/wiki/Cin%C3%A9-Ressources
- Open source genérico: AtoM (ICA) y CollectiveAccess son de descripción archivística, no de obra fílmica; ninguno modela presentación en festival.

---

## (a) Modelo de entidades recomendado

Tres capas, en vez de cuatro:

1. **Obra** (`work`) — invariante. `id` propio opaco (p. ej. `w_<ulid>`), `title_original`, `original_language`, `year`, `countries[]`, `directors[]`, `kind` (largo/corto/serie/instalación), `based_on`, `synopsis{es,en}`, `poster` (el oficial o el nuestro, con origen), `xref{tmdb,imdb,wikidata,letterboxd,isan}`, `aliases[]` (títulos por país/idioma con `type`, como IMDb akas + TMDB alternative titles). **Sin duración** (EN 15907 la saca del Work a propósito).
2. **Versión** (`version`) — opcional, solo cuando difiere: `work_id`, `runtime`, `audio_language`, `subtitles[]`, `cut` (theatrical/director's/restaurada), `label`. Para el 95 % de las obras basta una versión por defecto (lo que hace el ejemplo de EN 15907 con la "default variant").
3. **Presentación** (`screening_entry`, ya existe en cada festival) — `festival_id`, `work_id`, `version_id?`, sección verbatim, `premiere_status` (tier declarado por *ese* festival), Q&A/invitados, `event_kind`, `title_as_printed` (lo que imprimió el festival, para no perder la fuente), horarios/sedes.

Más una tabla **`merge_log`** (id absorbido → id superviviente, fecha, motivo) para que ningún ID que ya tuvo watchlist muera (lección Letterboxd/Wikidata: redirigir, no borrar).

## (b) Identificar una obra sin TMDB

- **Clave natural de candidatura** = `fingerprint(title_original) + year ± 1 + fingerprint(apellido del primer director)`. Fingerprint OpenRefine: minúsculas, sin acentos, sin puntuación, sin artículos iniciales (el/la/the/o/a), tokens ordenados. Para cortos sin año fiable, director + título.
- **Clave de identidad** = ID propio opaco, asignado una vez y nunca derivado del título (EIDR/ISAN). TMDB, IMDb, Wikidata, ISAN son `xref` con regla *distinct values*: dos obras con el mismo TMDB id es un bug detectable por guardián.
- Las obras sin ficha en ninguna base (muchos cortos colombianos) viven igual con ID propio y `xref` vacío; cuando aparezca la ficha, se añade — nada cambia aguas abajo.

## (c) Reglas de matching y supervivencia

**Matching (tres salidas, estilo EIDR/DAMA):**
- *Auto-match*: mismo `xref` (tmdb/imdb) **o** fingerprint de título igual + año ±1 + director coincide.
- *Candidato → revisión humana*: título fuzzy (Levenshtein normalizado ≥ 0,85 o Jaro-Winkler en títulos cortos) + año ±1, **o** título igual y director desconocido en una fuente, **o** mismo director + año y título distinto (puede ser traducción/aka). Nunca auto-registrar con candidatos.
- *Auto-no-match*: director distinto y año distinto, aunque el título coincida (remakes y homónimos).
- Bloqueo (blocking) por año ±1 y por primer token del director: con 1.500 obras no hace falta Splink; una comparación cuadrática por bloque corre en segundos. Umbral: mirar el histograma y ponerlo en el valle; registrar los pares revisados para recalibrar.

**Survivorship por campo (jerarquía de confianza):**

| Campo | Gana | Luego |
|---|---|---|
| Sección, horario, sede, premiere status, título impreso | Festival (fuente oficial del evento) | — |
| Título original, año, director, país, idioma original | Decisión humana registrada > TMDB > Wikidata > festival | Festival puede *proponer* corrección |
| Duración | Versión proyectada (festival) > TMDB | Se contrastan y se avisa si difieren > 5 min |
| Sinopsis ES/EN | Oficial del festival (verbatim) > decisión editorial > TMDB `translations` | Nunca traducción inventada como "oficial" (regla TMDB) |
| Afiche | Oficial de la obra > oficial del festival > nuestro compuesto | Regla propia existente (jerarquía del póster compuesto) |
| Emoji/arquetipo/EN de sección | Nuestra capa | Nunca pisa el nombre verbatim |

Restricción dura: `title_original`, `directors`, `year` no pueden quedar vacíos en una obra publicada → cola de excepción, no publicación silenciosa.

## (d) Procedencia y decisiones

- Cada campo de la obra lleva `{value, source, source_ref, fetched_at, rule}` donde `source ∈ {tmdb, wikidata, festival:<id>, human:<quien>, derived}`. Es el "linkage model" de MDM, guardado aparte del golden record para que la vista de la app siga siendo plana.
- **Decisiones humanas** van en una tabla propia `decisions` (`work_id`, `field`, `value`, `reason`, `date`, `supersedes?`) con prioridad máxima en survivorship: una regeneración automática nunca las pisa (es exactamente la cicatriz "arreglo aguas abajo se pierde"). Incluye decisiones negativas: "NO es la misma obra que w_X" (evita re-proponer el mismo match) y "sin afiche oficial, no crear ficha TMDB".
- `merge_log` con redirect; `match_review_log` con pares aceptados/rechazados (sirve de verdad para recalibrar umbrales).
- Modo simulación antes de activar una regla: diff "qué valor elegiría cada campo" contra lo publicado (ya es práctica en el pipeline: regenerar y diffear).

## (e) Cinco errores típicos documentados

1. **Poner la duración en la obra.** EN 15907 la excluye del Work porque cambia por versión; TMDB tiene un solo runtime y por eso choca con la versión proyectada.
2. **Usar el título como clave.** EFG nació precisamente para identificar obras "catalogadas bajo distintos títulos de distribución"; IMDb necesita tres capas de título. Clave = ID opaco; título = atributo con aliases.
3. **Auto-fusionar candidatos.** EIDR: con "Candidates Found" nunca se registra solo; con 15 años de reglas aún necesitan revisión experta. Homónimos y remakes comparten título y a veces año.
4. **Borrar duplicados en vez de redirigir.** Letterboxd conserva duplicados borrados en TMDB porque hay diarios sobre ellos; Wikidata fusiona con redirect. Una watchlist apunta a un ID.
5. **Survivorship por fuente en lugar de por campo** y sin registro de decisiones: "TMDB siempre gana" pisa la sinopsis oficial; "el festival siempre gana" mete el año mal tecleado del programa; y sin tabla de decisiones la regeneración repite el mismo match descartado (MDM: lineage por atributo + cola de stewardship).

Nota de fiabilidad: Cinando/Festival Scope/FilmFreeway no publican esquema; lo dicho sobre ellos es inferido de datasets y formularios públicos. El PDF "Introduction to the EIDR Data Model" devolvió 404 el 12 oct; la descripción de EIDR sale del Best Practices for Edits y de la wiki de desarrolladores.
