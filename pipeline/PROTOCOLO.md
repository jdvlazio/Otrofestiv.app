# Otrofestiv · Protocolo de producción de festivales

**Este documento es EL proceso** — de la fuente al festival en producción.
La doctrina de enrichment (qué se acepta de TMDB/Letterboxd y por qué) y el
historial de errores viven en **`docs/PIPELINE.md`**, que manda en su tema:
ante cualquier conflicto sobre datos de terceros, PIPELINE prevalece.

Reescrito el 9 ago 2026 tras montar FICDEH (443 funciones, 11 ciudades) y
FICMA (90 funciones desde un PDF de imágenes). Todo lo que dice aquí se pagó.

---

## 1 · Qué pedir para empezar

Al festival u organizador, en el primer contacto:

1. **La programación completa en PDF** — idealmente el archivo original con
   texto seleccionable. Si es exportación en imagen (posts de Instagram a PDF,
   como FICMA) también sirve: el OCR del sistema lo lee — solo cuesta más.
2. **El Excel o la hoja con que la armaron**, si existe. Suele traer sinopsis,
   países y duraciones que el impreso no alcanza a mostrar. ⚠ Preguntar si
   algún FORMATO significa algo: en FICDEH las filas en rojo estaban dadas de
   baja y eso constaba SOLO en el color.
3. **El listado de sedes con dirección exacta** y el número de sala por función.
4. **Los afiches** (del festival y de las obras) en una carpeta de Drive.
5. **Los enlaces de inscripción o compra**, si los hay.
6. Y el acuerdo: **si algo cambia, nos avisan** — trabajamos sobre la versión
   que nos pasen y necesitamos saber cuál es la vigente.

Además: nombre oficial, fechas, ciudad(es), y el `id` corto (`ficma2026`).

**Jerarquía de fuentes** — se declara por festival y por escrito en el
ensamblador. La de FICDEH: guía PDF > Excel oficial > web > tiquetera. La web
corrige publicando de nuevo: el barrido se repite durante el festival.

---

## 2 · El proceso, paso a paso

### Paso 0 · Fuentes a su carpeta

Todo original va a **`fuentes/<fest-id>/`** (gitignored — decenas de MB, y el
repo sirve GitHub Pages). El escritorio es de TRÁNSITO: nada de trabajo vive
ahí, y macOS le pega a los archivos un `com.apple.macl` que puede impedir
abrirlos después (`xattr -c` lo limpia). Los scripts leen con ruta relativa al
repo (`f'{REPO}/fuentes/…'`), nunca rutas absolutas de una máquina.

### Paso 1 · Parser propio → formato intermedio

Cada fuente es única; **el parser es desechable** y no se generaliza. Lo que
no es negociable es su SALIDA: `festivals/staging/<id>-crudo.json` en el
formato intermedio (§4), con `_provenance.capturado` — `lib.provenance()` lo
pone solo. Lo derivado se versiona (un OCR completo cabe en staging); el
binario original no.

### Paso 2 · Enriquecer — un comando

```bash
TMDB_API_KEY=… python3 pipeline/enriquecer.py <id> --posters
```

TMDB **verificado** (director + año ±1 o duración ±3 min — `ficha_verifica()`),
`title_en` cuando difiere, `lbSlug` por el atajo `letterboxd.com/tmdb/<id>`,
sinopsis ES/EN, géneros, pósters a `assets/<id>/`. Lo que no verifica **no
entra**: los «sin ficha» se dan de alta en TMDB (PIPELINE.md Fase 3b) o quedan
sin ficha, jamás se adivina un homónimo.

**Y el encuadre de pósters, obligatorio** (docs/POSTERS.md §3):

```bash
python3 pipeline/encuadrar-posters.py <id> --aplicar
```

REGLA (Juan, 9 ago 2026): **todo póster cubre exactamente la proporción y el
tamaño del placeholder** — 780×1170, 2:3. Ni marco visible, ni hueco, ni recorte
del afiche. Es un cálculo, no un ajuste a ojo.

Dos pasos en uno, siempre desde el archivo ORIGINAL (re-descargarlo si hace
falta: encadenar recortes sobre recortes acumula deformación):

1. **Caja de contenido** — se descarta el borde uniforme. Solo cuenta como marco
   lo que aparece en los DOS lados opuestos: un marco rodea. Un borde claro de
   un solo lado es arte —el cielo de «The Dig»— y recortarlo mutila el afiche.
2. **Escala al lienzo con zoom mínimo** — la caja se lleva a 780×1170 estirando
   el eje que falte, con un 4% de overscan que se recorta al centro. Ese zoom se
   traga las 1–2 filas de transición que deja el antialias del borde, a cambio
   de un 2% por lado que no se percibe. Afinar más el detector para ahorrarse
   ese 2% arriesga comerse arte, que es peor.

**Qué cuenta como marco, calibrado con píxeles reales:** una línea PLANA (poca
varianza a lo ancho), sea blanca, negra o gris. En «El juego de la vida» el
marco son dos filas —255 y 178— y exigir «casi blanco» dejaba fuera la segunda,
que es justo la línea gris que se veía. El arte tiene varianza alta desde la
primera fila (117 ahí mismo).

El script **verifica su propio resultado**: al terminar mide de nuevo y reporta
cuántos quedan con borde y cuántos fuera de lienzo. Objetivo 0 y 0; lo que
quede es arte de un solo lado.

Un `posterSource:editorial` (still 16:9) se respeta: su marco lo encuadra a 16/9.

Correcciones en `festivals/staging/<id>-correcciones.json`:
`titulo_oficial` (el OCR/programa escriben mal → se corrige contra el afiche)
vs `alias` (el festival rebautizó → se busca por el nombre de distribución,
se conserva el del festival).

### Paso 3 · Sedes

**Primero la tabla canónica, a mano.** La fuente nombra el mismo lugar de
varias maneras y cada variante parte o duplica funciones — la lección más cara
de FICDEH. La sala va FUERA del nombre (campo `sala` de la función); la tabla
es explícita, nunca heurística sobre el guion.

```bash
python3 pipeline/geocodificar.py <id> --centro LAT,LNG   # verificado por tipo
python3 pipeline/sedes-html.py   <id> --centro LAT,LNG   # las pendientes, a mano
```

Lo verificado a mano lleva `_prec:"manual"` y es **intocable**. Dos sedes
reales en el mismo predio se declaran con `_nota` (el guardián
`[sedes-apiladas]` pregunta por todo par a <60 m).

### Paso 4 · Decisiones de contenido — con Juan

- **Secciones**: nombre VERBATIM del festival; nuestra capa es emoji + inglés
  + arquetipo (los 9 canónicos de `ARCHETYPE_COLORS` — un gate lo exige).
- **Proyecciones conjuntas**: ¿el festival le puso NOMBRE al conjunto? →
  Programa (`is_cortos` + `film_list`). ¿Obras independientes en una función?
  → anclaje (`sharedSlotIsOneScreening`). La duda se resuelve contra el
  programa oficial, nunca por deducción.
- **Talleres multi-día**: UN bloque — `is_recurring` en cada sesión; la app
  ofrece «Añadir las N sesiones».
- **Acceso — CASILLA OBLIGATORIA, no se deja en blanco.** `is_free` /
  `ticket_url` (solo compra) / `requires_registration` + `registration_url`
  (van en la FUNCIÓN — cada actividad tiene su formulario). La traducción de la
  palabra del festival a esos campos la hace `lib.acceso_campos()`, una sola
  vez, con las frases reales de FICDEH, FICMA, FINCA y la Cinemateca.
  **Si el festival aún no lo publicó se escribe `lib.DESCONOCIDO`**: no saber es
  legítimo y se declara; no mirar, no. Un festival vigente cuyas funciones
  callan queda ROJO (`[boleteria-muda]`), y `lib.cargar_crudo()` ya no acepta un
  crudo mudo — falla en el paso 1, meses antes de que se vea en la app.
- **Copy**: toda string nueva pasa por Juan. El tagline del splash expande la
  sigla; el lema del año vive en el afiche.

### Paso 5 · El camino genérico — un ensamblador, un publicador

**Desde el 17 ago 2026 el festival NO escribe su ensamblador.** Escribe su
`pipeline/<id>.plan.json` —identidad, tabla de sedes, mapa de secciones— y
corre:

```bash
python3 pipeline/ensamblar.py <id>    # crudo + plan → staging/<id>-build.json
python3 pipeline/publicar.py <id>     # build → festivals/<id>.json, validando
```

Lo que pone el genérico, igual para todos: `day_order`, banderas desde el país,
«N min», «Sede - Ciudad», la casilla de acceso vía `lib.acceso_campos()`, los
cortos como `is_cortos` + `film_list`, el país de un programa derivado de sus
obras, y el enriquecimiento por obra —también dentro de un bloque de cortos—.

**Si un festival necesita una regla nueva, se añade AL GENÉRICO.** Escribir un
ensamblador aparte es cómo se perdieron los 6 enlaces de TuBoleta de
CineAutopsia y las 415 banderas de FICDEH: no eran doce errores distintos, era
el mismo error doce veces. Lo vigila `[pipeline-generico]`.

**`publicar.py` se niega a borrar lo que ya está en producción.** Compara la
cobertura campo a campo con el JSON publicado y **aborta** si el build trae
menos: es exactamente lo que pasó con FICDEH, cuyo build estaba atrasado y
habría borrado 415 banderas y 13 salas en silencio. Con `--forzar` se publica
igual, pero hay que escribirlo a mano.

**Plantilla del plan:** `pipeline/festival.plan.example.json`.

### Paso 5·bis · El ensamblador propio (legado)

El ensamblador del festival junta crudo + enriquecido + geo y escribe el JSON
final. La jerarquía de fuentes va COMENTADA en su cabecera, y toda excepción
(duración corregida, título del afiche, cambio anunciado después del PDF) en
**tabla explícita con fecha**, nunca editando el crudo.

#### La palabra la pone el festival — no se traduce en la salida

**Si la fuente ya trae la palabra, se PASA.** El error no es capturar mal un
dato: es capturarlo bien y traducirlo en la línea que lo escribe.

```python
e['event_kind'] = 'ponencia' if f['tipo'] == 'charla' else 'masterclass'   # ✗
e['event_kind'] = f['tipo']                                                # ✓
```

Esa línea real de FICDEH traducía **las dos** palabras. El festival dice
`charla` y `taller`; la app imprimía **PONENCIA** en 18 actividades y
**MASTERCLASS** en 11 —«Producción y Animación 2D», «Actuación para cine»—,
ninguna de las cuales lo era. FICMA tenía la misma línea con `charla`. Estuvo
en producción hasta el 10 ago 2026 y no lo cazó ningún guardián: el dato era
válido, solo que era **nuestra palabra**.

Cómo se reconoce, en dos formas:

- `X if fuente == 'A' else 'B'` con `B` literal en la línea de salida.
- un mapa cuyos VALORES no aparecen en ningún sidecar.

Y una prueba rápida: buscar la palabra de salida en `festivals/staging/`. Si no
está en ninguna fuente, la pusimos nosotros.

Ojo con el falso positivo: renombrar **no** siempre es traducir. FICDEH titula
su sección «🛠️ Formación» aunque el `tipo` sea `taller`, y es correcto — sus
propios pósters se llaman `formacion-actuacion-para-cine.jpg`. QAFF renombra
sus 15 categorías porque el widget de calendario las publica en mayúsculas y
con erratas («PRISMA FEMININO») mientras su web las escribe bien.

**Cuando el festival se nombra de dos formas, se elige una y se DECLARA en el
código**: qué superficie manda y por qué. Sin esa nota, el siguiente que pase
lee el renombre como el bug de arriba y lo «arregla» al revés.

La config va en `FESTIVAL_CONFIG` de **`src/config.js`** (registrarla ahí es
parte legítima de un PR de datos). `node scripts/generate-config.js --help`
genera el bloque; `lib.dias_config()` los objetos de días. **El JSON del
festival NUNCA lleva bloque `config{}`** — `validate-festivals.js` lo bloquea.

### Paso 6 · El plan del festival + runner

Los pasos 1–5 se declaran en `pipeline/<id>.plan.json` y se corren con:

```bash
python3 pipeline/correr.py <id>          # en orden, aborta al primer fallo
python3 pipeline/correr.py <id> --lista  # ver pasos e inventario con edades
```

El runner muestra la EDAD de cada sidecar (`capturado`): un sidecar viejo
junto a uno recién escrito es la señal de circuito roto que faltó el 8 ago.

### Paso 7 · Validar, QA visual, publicar

```bash
python3 validate.py                      # guardianes — incluye los del pipeline
node scripts/validate-festivals.js <id>
node --test tests/unit/*.test.js
```

**QA visual en móvil (390px), sin excepción**: splash (afiche entero, orden
por fecha), grid por día (ningún día vacío, pósters sin romper), ficha
(metaline, sinopsis, Letterboxd solo si hay slug, CTAs canon), planear (el
worker genera escenarios), Mi Plan, cambio de festival limpia estado. Mirar la
app encuentra lo que ninguna validación ve: el póster roto, el filtro
desbordado y el badge invertido salieron los tres en pantalla.

Publicar: `node scripts/bump-version.js` → commit (los 5 archivos del bump
JUNTOS) → push → PR **de datos** (la frontera código/datos es un guardián de
CI; mezcla deliberada = etiqueta `frontera-ok`) → CI verde → merge (el dueño
de la rama la lleva hasta el final) → **verificar el deploy de Pages y el JSON
en producción con curl**, no asumirlo.

---

## 2·bis · Cuando al festival le pasa algo

Terremotos, paros, clima, duelo. Pasó dos veces en 24 horas —FICMA aplazado y
FICDEH cancelando cuatro ciudades, ambos por el sismo del 10 ago 2026— así que
esto es doctrina, no anécdota.

**Lo primero, y decide todo lo demás: qué declaró el festival.** No se traduce
ni se interpreta. Si dicen «aplazado» no escribimos «cancelado», y al revés. Es
la misma regla del Paso 5 aplicada a la peor semana del festival.

| El festival dice | Mecanismo | Precedente |
|---|---|---|
| «se aplaza todo» | `status:{kind:'postponed', since, note, note_en, url}` en FESTIVAL_CONFIG | FICMA 17 |
| «cancelamos en estas ciudades» | `NOTICES` con alcance `cities:[…]` | FICDEH 2026 |
| «esta función cambia o se cae» | `NOTICES` por `title` + `date` | ya existía |

**Un solo elemento ruidoso: el banner, y descartable.** Todo lo demás es estado
en su sitio — la card atenuada con su badge, el planificador que la esquiva, el
«Buscar reemplazo» que solo ve quien la tenía en Mi Plan. La regla de Juan del
29 jul 2026 sigue mandando: *el aviso es una NOTA al margen, no una tarjeta*.

**Reglas que costaron caro:**

- **Las palabras son del festival, con enlace al comunicado.** `note` verbatim;
  `note_en` es traducción nuestra y se consulta antes — un comunicado de
  tragedia no suele tener versión en inglés.
- **No prometer lo que no se sabe.** «Pendiente nueva fecha» es de una función
  REPROGRAMADA. En una cancelación no hay fecha pendiente, y prometerla es peor
  que callar.
- **El dato del festival NO se toca.** Aplazar o cancelar es una capa; las
  funciones, sedes y secciones se quedan. Revertir = fechas nuevas y borrar la
  capa, sin re-onboarding.
- **Un festival que canceló parte NO terminó**, y uno aplazado tampoco. Modo
  Recuerdo no puede inventar recuerdos de funciones que no ocurrieron.
- **Ocultar es el último recurso.** `group:'test'` saca el festival del riel sin
  explicar nada: sirve como parche de minutos mientras se monta el estado, no
  como solución. Se usó así el 10 ago y se declaró parche en el propio código.
- **Verificar en producción**, no asumirlo: el JSON servido y el config, con curl.

**Y lo que dispara todo:** el comunicado suele salir primero en Instagram, no en
la web. El [radar](../docs/RADAR.md) vigila la web y la ficha de Proimágenes;
para el aviso urgente, la fuente sigue siendo el ojo humano.

---

## 3 · Checklist de publicación

- [ ] Fuentes en `fuentes/<id>/` · derivados en staging con `capturado`
- [ ] Tabla de sedes canónica hecha · 0 salas dentro de nombres de sede
- [ ] Slots compartidos DECIDIDOS (programa vs anclaje vs separadas)
- [ ] **Acceso declarado en TODAS las funciones** (gratis / boletería /
      inscripción / `desconocido` explícito) — nunca en blanco
- [ ] Secciones verbatim + arquetipo de los 9 + inglés
- [ ] Enriquecimiento verificado · sin-ficha resueltos o declarados
- [ ] Sedes: verificadas o `_prec:"manual"`; pendientes DECLARADAS
- [ ] `_etapa` dice la verdad (se actualiza al publicar)
- [ ] validate.py + validate-festivals + tests + QA visual
- [ ] Gate humano de Juan: revisión film-por-film (`tools/audit.html?fest=<id>`)

---

## 4 · El formato intermedio — un shape, N lectores, M herramientas

Los PARSERS son desechables; las HERRAMIENTAS son permanentes. Lo que las une
es UN formato. Todo parser, venga de donde venga, escribe:

```json
{ "_provenance": { "fuente": "…", "capturado": "AAAA-MM-DD" },
  "funciones": [ { "titulo": "…", "dia": "AAAA-MM-DD", "hora": "HH:MM",
                   "sede": "…", "sala": "", "ciudad": "",
                   "director": "…", "pais": "…", "anio": 2026,
                   "duracion_min": 90, "has_qa": false,
                   "acceso": "Entrada libre | Boletería en … | desconocido",
                   "ticket_url": "", "en_app": true } ] }
```

y las herramientas genéricas leen eso, nunca el JSON propio de un festival.
`capturado` es obligatorio: sin fecha no se sabe si un sidecar está viejo —
así se escondió el bug de las 48 salas de FICDEH. **`acceso` también**: el campo
existía desde el principio, FICDEH lo capturaba y FICMA lo declaraba en prosa, y
aun así ningún ensamblador lo convertía en los campos que la app lee. Los 6
enlaces de TuBoleta de CineAutopsia estaban en la fuente y no llegaron al JSON
(17 ago 2026). Un campo que nadie exige es un campo que algún día no se llena.

Las funciones comunes viven en **`pipeline/lib.py`** (antes reescritas por
triplicado): `norm`, `hora24`, `rango_horario`, `curl_get`, `tmdb_get`,
`director_coincide`, `ficha_verifica`, `sede_sala`, `dias_config`, `banderas`,
`provenance`, `cargar_crudo`. `python3 pipeline/lib.py` corre su selftest —
los casos reales que cada una resolvió, incluidos los que costaron un bug.

Guardianes del pipeline en `validate.py`: `[staging-provenance]` (sidecar
nuevo sin fecha = error), `[pipeline-circuito]` (escrito-sin-lector junto a su
gemelo leído-sin-escritor = error), `[sedes-apiladas]` y `[sala-en-sede]`
(warnings sobre festivales activos).

Los pipelines de FICDEH y FICMA (pre-formato) no se migran: son históricos.
Primer festival montado enteramente con esto: SiembraFest.

---

## 5 · Convenciones que nunca cambian

- **La palabra la pone el festival.** Si la fuente la trae, se pasa; no se
  traduce en la línea de salida (Paso 5). `event_kind` lo vigila
  `[event-kind-conocido]` en `scripts/validate-festivals.js`.
- **Venue**: `"Nombre de la Sede - Ciudad"`, siempre. La sala aparte.
- **Horas**: 24h con dos dígitos (`"09:30"`). **Duración**: `"90 min"`.
- **Días**: `dayShort` ES (`"VIE 12"`) + `dayShort_en` (`"FRI 12"`).
- **Flags**: emoji de bandera (`"🇨🇴🇨🇦"`) — `lib.banderas()`.
- **Objeto film canónico**: `poster` y `lbSlug` EN el film, no en mapas raíz.
- **`poster: ""` prohibido**: imagen real o ausencia del campo.
- **TMDB_API_KEY** jamás en el bundle: `''` en producción, env en scripts.
- **keyArt** del splash: 2:3 por estirado (`scripts/compose-keyart.py`),
  write-once (el SW cachea), huella registrada (`scripts/keyart-huellas.py`).
