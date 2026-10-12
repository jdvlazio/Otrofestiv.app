# Catálogo único de obras — diseño y plan de acción

> Propuesta, 12 oct 2026. Pendiente de aprobación de Juan. Nada de esto está
> implementado todavía. Fuentes: `scratchpad/investigacion/catalogo-modelos.md`
> (estándares y casos) y `censo-obras.md` (medición del repo).

## 1. El problema, medido

| Dato | Valor |
|---|---|
| Registros de obra en 32 festivales | 4.490 |
| Obras distintas | ~2.500 |
| Obras en 2 o más festivales | 125 (CHAIKA y Decaer en 5) |
| … con datos contradictorios entre festivales | 111 (afiche 107, sinopsis 84, director 27, año 24, duración 9) |
| Obras sin ficha de TMDB (sin ningún identificador estable) | 1.651 (64 %) |
| Decisiones ya declaradas dos veces en sidecars de festivales distintos | 58 |
| Cobertura por obra única: tmdb_id / lbSlug | 36 % / 50 % |

Hoy, entre festivales viajan cuatro cosas: `tmdb_id`, afiche, sinopsis ES y
`lbSlug` (lib.obras_publicadas + reuso_publicada). **No viajan:** sinopsis EN,
año, duración, país, director canónico, ni ninguna decisión humana (los sidecars
`-correcciones`, `-sinopsis`, `-afiches` van atados al festival). Resultado:
*La paga* pasó por la hoja de contacto en FILCMAR y volvió a aparecer como duda en
MUBI Fest; *AtmoSphaira* tenía año, duración y país en CineAutopsia y en FICPA
hubo que declararlos a mano; cada festival corre las tres sondas de TMDB desde cero.

## 2. Qué dicen los que ya lo resolvieron

- **EN 15907 / FIAF / EIDR / ISAN** separan la **obra** (lo invariante: título
  original, autores, año, país) de la **versión** (cortes, idioma, duración) y de
  la **copia**. EN 15907 saca la duración del nivel obra *a propósito*.
- **El identificador es propio y opaco** (EIDR, ISAN). TMDB, IMDb, Wikidata son
  referencias cruzadas con regla *distinct values*: dos obras con el mismo
  `tmdb_id` es un bug detectable.
- **Matching con tres salidas** (EIDR, DAMA-DMBOK): coincide / no coincide /
  candidatos → revisión humana. Nunca se fusiona solo con candidatos.
- **Supervivencia por campo, no por fuente** (MDM): el festival manda en lo suyo
  (sección, horario, premiere), TMDB en lo bibliográfico, y la decisión humana
  registrada por encima de todo.
- **Procedencia por campo** guardada aparte de la vista (linkage model), y
  **decisiones humanas en tabla propia**, incluidas las negativas («no es la misma
  obra», «sin afiche oficial, no crear ficha»).
- **Los duplicados se redirigen, no se borran** (Letterboxd, Wikidata): un id que
  ya tuvo watchlist no puede morir.
- **Los agregadores de festivales** (Cinando, FilmFreeway) modelan *obra × evento*:
  premiere status, sección, Q&A e invitados son de la presentación, no de la obra.

Cinco errores documentados que evitamos de entrada: duración en la obra; título
como clave; auto-fusionar candidatos; borrar en vez de redirigir; supervivencia por
fuente sin registro de decisiones (la regeneración repite el match que ya
descartamos: es la cicatriz «arreglo aguas abajo se pierde»).

## 3. El modelo

Tres capas. La app no cambia: sigue leyendo el JSON plano de cada festival.

### 3.1 Obra (`catalogo/obras/<id>.json`)

Lo que no cambia entre festivales. Un archivo por obra, en el repo, revisable en
un diff.

```json
{
  "id": "w_01JA3F7K9QZ8",
  "titulo_original": "La paga",
  "idioma_original": "es",
  "anio": 1962,
  "paises": ["CO", "VE"],
  "directores": ["Ciro Durán"],
  "tipo": "largometraje",
  "aliases": [
    {"titulo": "The Payment", "idioma": "en", "tipo": "traduccion"}
  ],
  "sinopsis": {"es": "...", "en": "..."},
  "afiche": {"archivo": "catalogo/afiches/w_01JA3F7K9QZ8.jpg", "veredicto": "oficial"},
  "xref": {"tmdb": 1363770, "letterboxd": "la-paga", "imdb": null, "wikidata": null},
  "presentaciones": ["filcmar-2026", "mubibogota-2026"]
}
```

- `id` opaco (ULID). Nunca derivado del título. Se asigna una vez.
- **Sin duración**: va en la versión.
- `xref` con guardián *distinct values*: un `tmdb` no puede estar en dos obras.
- Las 1.651 obras sin TMDB viven igual, con `xref` vacío; cuando aparezca la
  ficha se agrega y nada cambia aguas abajo.

### 3.2 Versión (`versiones[]` dentro de la obra, opcional)

Solo cuando una proyección difiere: `{duracion_min, idioma_audio, subtitulos,
corte, etiqueta}`. El 95 % de las obras tiene una versión por defecto. Resuelve
*Llueve sobre Babel* (111 / 113 / 120 min en cuatro festivales) sin elegir un
número «verdadero».

### 3.3 Presentación (lo que ya existe: la función en `festivals/<fid>.json`)

Cada función del festival gana un campo `work_id`. Lo que es del festival se
queda ahí, verbatim: sección, día/hora/sede, premiere status, Q&A, invitados,
`event_kind`, **título tal como lo imprimió el festival** (`title`, como hoy).
La obra aporta lo bibliográfico; la presentación, lo del evento.

### 3.4 Procedencia (`catalogo/procedencia/<id>.json`)

Por campo: `{valor, fuente, referencia, fecha, regla}`, con `fuente ∈ {tmdb,
wikidata, festival:<fid>, humano:juan, derivado}`. Vive aparte para que la obra se
lea limpia. Responde «¿de dónde salió este año?» sin adivinar.

### 3.5 Decisiones (`catalogo/decisiones.json`)

Una fila por decisión humana: `{work_id, campo, valor, motivo, fecha, reemplaza}`.
Prioridad máxima en la supervivencia: ninguna regeneración la pisa. Incluye las
**negativas**: «w_A NO es w_B» (no volver a proponer el match), «sin afiche
oficial: no crear ficha TMDB», «es videoclip: no va a TMDB». Aquí migran las 138
correcciones, 45 sinopsis y 183 afiches de los sidecars, deduplicados.

### 3.6 Fusiones (`catalogo/fusiones.json`)

`{id_absorbido, id_superviviente, fecha, motivo}`. Un id nunca se borra: se
redirige. `domain/titulos.js` ya hace esto para títulos renombrados; es la misma
idea a nivel de obra.

## 4. Reglas

### 4.1 Cómo se reconoce una obra (matching)

Clave de candidatura: `huella(título) + año ±1 + huella(apellido del primer
director)`. La huella es la de OpenRefine: minúsculas, sin tildes, sin puntuación,
sin artículos iniciales, tokens ordenados. Bloqueo por año y por director: con
2.500 obras la comparación corre en segundos, sin Splink.

| Salida | Cuándo | Qué pasa |
|---|---|---|
| **Coincide** | mismo `xref`, **o** huella del título igual + año ±1 + director coincide | se enlaza sola |
| **Candidato** | título parecido (≥ 0,85) + año ±1; **o** título igual y una fuente sin director; **o** mismo director y año con otro título (traducción/aka) | va a tu revisión, con los dos lados a la vista; nunca se enlaza sola |
| **No coincide** | director distinto y año distinto, aunque el título sea igual (homónimos, remakes) | obra nueva |

Los pares revisados se guardan (`catalogo/revisiones.json`) para recalibrar el
umbral con datos reales, no a ojo.

### 4.2 Qué fuente gana en cada campo (supervivencia)

| Campo | Gana | Después |
|---|---|---|
| Sección, día/hora/sede, premiere, título impreso, Q&A | **Festival** | — |
| Título original, año, director, país, idioma | **Decisión humana** > TMDB > Wikidata > festival | el festival puede *proponer* una corrección, que cae en candidatos |
| Duración | **Versión proyectada** (festival) > TMDB | si difieren > 5 min, aviso |
| Sinopsis ES / EN | **Oficial del festival** (verbatim) > traducción nuestra con contexto > TMDB | nunca una traducción como si fuera oficial |
| Afiche | **Oficial de la obra** > oficial del festival > compuesto nuestro | regla ya vigente (jerarquía del póster compuesto) |
| Emoji, arquetipo, EN de sección | Nuestra capa | nunca pisa el nombre verbatim |

Restricción dura: `titulo_original`, `directores` y `anio` no pueden quedar vacíos
en una obra publicada. Si falta, va a la cola de excepciones; no se publica en
silencio (es la regla de «sin ficha no se publica», llevada a la obra).

### 4.3 Guardianes (validate.py, fase 0: activos; con el catálogo vacío pasan, y la autoprueba demuestra que cada uno atrapa su cebo)

- `[xref-unico]`: un `tmdb`/`imdb` en una sola obra.
- `[obra-sin-duracion]`: la duración nunca en la obra.
- `[decision-pisada]`: ningún valor publicado contradice una decisión vigente.
- `[presentacion-con-obra]`: toda función con `type:film` lleva `work_id` válido
  (o está en `fusiones` como redirigida).
- `[candidato-sin-resolver]`: un onboarding no publica con candidatos abiertos.
- `[catalogo-ids]`: todo id con la forma `w_` + 12 caracteres Crockford, y cada archivo se llama como su id.
- `[catalogo-autoprueba]`: cada uno de los anteriores tiene que atrapar un cebo en memoria; si alguno queda ciego, el push se bloquea.

## 5. Cómo encaja con el pipeline de hoy

- **El enriquecido consulta el catálogo antes que TMDB.** `cascada_tmdb` pasa a
  ser `cascada_obra`: 1) decisión humana, 2) catálogo (por xref o por huella),
  3) TMDB con el candado, 4) Proimágenes, 5) cinecorto. Si el catálogo ya tiene la
  obra, **no se sondea ni se re-revisa**: hereda ficha, afiche, sinopsis, EN,
  Letterboxd, año, país.
- **Lo nuevo escribe de vuelta al catálogo** al final del onboarding (hoy nada
  vuelve al festival viejo). La hoja de contacto solo muestra obras nuevas o con
  candidatos.
- **`publicar.py` materializa la vista plana**: para cada función, obra + versión
  + presentación → el JSON que la app ya lee. El contrato de `SCHEMA.md` no cambia;
  se le suma `work_id`.
- **Los sidecars por festival desaparecen** para lo que es de la obra
  (`-correcciones.fichas`, `-sinopsis`, `-afiches`). Se quedan los que son del
  festival (`sin_afiche` por programa, alias de sedes, títulos anteriores).
- **Los festivales archivados no se reescriben** (excepciones congeladas). Entran
  al catálogo como fuente de datos, no como destino.

## 6. Plan de acción

| Fase | Qué | Entregable | Tiempo |
|---|---|---|---|
| **0. Diseño** | Este documento + esquema JSON del catálogo + los 5 guardianes escritos como tests que fallan | PR de docs, sin datos | 1 sesión |
| **1. Censo → catálogo inicial** | Script `catalogo/construir.py` que lee los 32 festivales + sidecars, agrupa por xref/huella, asigna ids, escribe procedencia. Salida en **modo simulación**: lista de coincidencias, candidatos y contradicciones, sin publicar nada | `catalogo/` con ~2.500 obras + hoja de **candidatos** (estimo 100–200 pares) y de **contradicciones** (111 obras) para tu revisión | 1–2 sesiones + tu revisión |
| **2. Resolver contradicciones** | Tú decides sobre la hoja (una vez por obra, no por festival): grafía del director, año, afiche que manda. Cada respuesta entra a `decisiones.json` | catálogo coherente; 58 decisiones duplicadas → 1 cada una | tu tiempo, por lotes |
| **3. Cablear el pipeline** | `cascada_obra`, escritura de vuelta, `work_id` en la vista, guardianes activos. Modo simulación: regenerar los 32 festivales y diffear contra producción, **cero cambios no explicados** | PR de pipeline | 1–2 sesiones |
| **4. Probar con dos festivales** | MUBI Fest (8 obras ya en catálogo de 12) y FICICA (31 de 81) | onboarding sin volver a sondear lo conocido; hoja de contacto solo con lo nuevo | 1 sesión |
| **5. Altas TMDB desde el catálogo** | La cola de altas sale del catálogo (obras sin xref, con afiche oficial ≥ 500 px, director y año) y se marca una vez | lotes de altas sin re-filtrar por festival | continuo |

Orden de dependencias: 0 → 1 → 2 → 3 → 4 → 5. La fase 2 es la única que te
pide tiempo activo; se puede hacer por lotes de 30 mientras avanzo la 3.

## 7. Lo que decides tú ahora

1. **Aprobar el modelo** (3 capas, id propio, sin duración en la obra).
2. **Dónde vive el catálogo**: en el repo, como JSON por obra (propuesta: diffs
   legibles, mismo flujo de PR y guardianes). La alternativa, Supabase, da
   consultas pero saca el dato del flujo de revisión; no la recomiendo para esto.
3. **Umbral de revisión**: propongo que en la fase 1 *todo* candidato pase por ti
   (son pocos cientos, una vez). Después del primer lote se calibra.
4. **Los archivados**: fuente sí, destino no (no se reescriben). ¿De acuerdo?

## 8. Riesgos

- **El censo cuenta 127 títulos que caen en dos claves** (tmdb en un festival,
  título en otro). Son los candidatos duros; la fase 1 los pone en tu hoja, no los
  resuelve sola.
- **Una obra «partida» hoy en dos ids** (p. ej. *Soñé su nombre*) se fusiona con
  redirect; las watchlists que apunten a cualquiera de los dos siguen vivas.
- **Regenerar 32 festivales** puede mover datos que nadie pidió. Por eso la fase 3
  corre primero en simulación con diff contra producción y exige cero cambios no
  explicados antes de tocar `main`.
