# La función — modelo, reglas y plan

> Especificación, 15 oct 2026. Viene de la auditoría del mismo día
> (`design-previews/auditoria-funcion.md`). Juan delegó las reglas
> («haz lo más conveniente, paso a paso con rigor»): las de la §4 son las
> recomendadas y quedan como **decisión delegada**, con fecha, revisables. Nada
> de esto está implementado todavía. Es el modelo hermano del catálogo de obras
> (`docs/CATALOGO-OBRAS.md`): allá la obra, acá la función.

La **función** es la unidad mínima de un festival: **qué** se presenta,
**cuándo**, **dónde** y **cómo se entra**. Es lo que el usuario planea.

---

## 1. El problema, medido (15 oct 2026, 34 festivales, 3.138 funciones)

| Dato | Valor |
|---|---|
| Funciones sin ninguna señal de entrada | 1.068 (34 %); 7 festivales al 100 % |
| Funciones con `sala` escrita, que la app no muestra | 1.586 (50 %) |
| Tablas de excepciones por festival sobre la función | más de 70, en 25 scripts |
| …que su verificador conoce | unas 15 |
| …sin fuente citada | más de 10 |
| Formas de corregir una hora / una duración | 8 / 6 |
| Festivales sin verificador | 5 |
| Funciones sin `_src` | 612 (19,5 %) |

Además:
- La boleta sin link se pierde (`lib.acceso_campos` solo guarda «libre» y el link).
- La app trata la entrada que falta como **paga**.
- Las decisiones de Juan existen solo como comentarios.
- `invitados` no tiene lector.
- `screenings[]` pierde `has_qa`, `premiere`, `ticket_url`, `requires_registration` y `duration`.
- La regla «programa → descripción» está escrita tres veces.

## 2. Qué dicen los que ya lo resolvieron

- **Wikidata:** cada dato es una *afirmación* con referencias y un *rango*. Varias afirmaciones conviven en una propiedad, y se lee la preferida.
- **Google Places:** el valor de cada atributo se elige por la confianza de la fuente *para ese atributo* (el dueño, en horario). Los conflictos van a revisión.
- **Datos maestros (MDM):** *reglas de supervivencia* por campo (fuente más confiable, más reciente o decisión manual), y procedencia por valor.

Lo común a los tres:
1. Las fuentes no se pisan, se suman.
2. Hay una regla por campo.
3. El valor publicado se calcula.
4. Los conflictos no se resuelven en silencio.
5. La procedencia viaja con el dato.

## 3. El modelo

### 3.1 Función base

Es la que da la **fuente principal** del festival: la que hoy produce el crudo (web, PDF, base de datos).
- Su **ancla** es `(sede, día, hora)` tal como la dio esa fuente.
- El ancla no cambia aunque una afirmación mueva la hora. Así las afirmaciones nunca persiguen a una función que se movió.

### 3.2 Afirmación (`festivals/staging/<fest>-afirmaciones.json`)

```json
{"ancla": {"sede": "Cinemateca de Bogotá", "dia": "2026-10-23", "hora": "19:00"},
 "casilla": "sala", "valor": "Sala 2",
 "fuente": {"tipo": "sala", "url": "https://…/node/peliculas/3620", "fecha": "2026-10-15"},
 "evidencia": "Cinemateca de Bogotá Centro / Octubre 23 7:00 PM / Sala 2"}
```

- **`casilla`:** una de la §4, con su nombre del contrato (`time`, `sala`, `entrada`…). Hay dos especiales:
  - `existe`: `true` agrega una función que la fuente principal no tiene. Su ancla es la nueva y la afirmación trae las casillas mínimas.
  - `existe`: `false` la quita, con `por_que`.
- **`fuente.tipo`:** `festival-web`, `festival-pdf`, `festival-ig`, `festival-mensaje`, `sala`, `prensa`, `juan`.
- **`fuente.url` y `fuente.fecha`** son obligatorias. Para `juan`, en vez de url va la frase en que lo dijo, con su fecha.
- **`evidencia`** es el texto literal de la fuente. El precio vive acá, nunca en una casilla publicada.

### 3.3 Decisión

Una afirmación con `tipo: juan`. Siempre gana en su casilla. Hoy esas decisiones están en comentarios; pasan a ser listables (`funcion.py decisiones <fest>`).

### 3.4 Conflicto

Dos afirmaciones del **mismo rango** en la misma casilla, con valores distintos y la misma fecha. Ninguna gana. Va a la cola (`<fest>-conflictos`, generada) y **el push queda frenado** hasta que haya una decisión.

### 3.5 Procedencia publicada

El build lleva `_procedencia: {casilla: {tipo, url, fecha, regla, marca?}}`. Es interno: el publicador no lo escribe en el JSON público. El `_src` actual queda como resumen.

`marca` puede ser:
- `supuesto`: nadie lo dijo y se asumió por la regla.
- `estimado`: se calculó.

## 4. Las casillas y sus reglas (decisión delegada, 15 oct 2026)

**Rango** (de mayor a menor) por casilla. Dentro de un mismo rango gana lo **más reciente**; empate de fecha con valores distintos = conflicto.

| Casilla (contrato) | Tipo | Rango | Si nadie la dice |
|---|---|---|---|
| `day`, `time` | obligatoria | juan › festival (web/pdf/ig/mensaje, lo más reciente) › sala › prensa | no se publica |
| `venue` | obligatoria, con pin | juan › festival › sala | no se publica |
| `sala` | opcional | juan › **sala** › festival | vacía |
| `duration` | estimable | juan › festival › suma de las obras › obra › sala | estimada: hueco hasta la siguiente en la misma sede, tope 90, 60 si es la última (`marca: estimado`) |
| `entrada` → `is_free` / `ticket_url` / `requires_registration` / `by_invitation` / `online` | supuesto | juan › **sala** › festival › prensa | `libre` (`marca: supuesto`), salvo sede que siempre cobra o festival `paid`: entonces `boleta` |
| `ticket_url` | opcional | sala (link directo a la función) › festival | ninguno |
| `registration_url` | opcional | festival | ninguno |
| `has_qa` / `qa_type` | opcional | juan › festival › festival-ig › sala | no |
| `film_start` | opcional | juan › festival | no |
| `premiere` | opcional | festival; en un programa, el mayor de sus obras | no |
| `estado` (vigente / cancelada / reprogramada) | opcional | juan › lo más reciente de festival o sala | vigente |
| `title` | obligatoria | palabras del festival; caja según `pipeline/caja.py` | — |
| `film_list` | opcional | festival › festival-ig | programa sin lista |
| `type` / `event_kind` | obligatoria | festival | — |
| `invitados` | opcional | festival › festival-ig | — |

**`entrada`** es un enum: `libre`, `boleta`, `inscripcion`, `invitacion`, `en_linea`.
- Se traduce a los campos que la app ya lee, siempre explícitos. `boleta` publica `is_free: false`, para que la app deje de adivinar.
- El **precio no se publica**: queda en `evidencia`.
- «Sedes que siempre cobran» es una tabla única en `funcion.py`, con fuente por sede. Hoy tiene la Cinemateca de Bogotá («Adquiere tus entradas»; lo que es libre lo dice).

## 5. Cómo encaja con el pipeline de hoy

```
fuente principal → crudo (función base, sin tablas de excepciones)
                 → afirmaciones (todas las demás fuentes)
ensamblar → funcion.resolver(base, afirmaciones) → build con _procedencia
          → cola de conflictos (frena el push)
verificador → compara el build contra base + afirmaciones (el mismo resolver)
publicar → igual que hoy
```

- `pipeline/funcion.py` es **el único dueño**: modelo, reglas de la §4, resolución, cola, marcas.
- `ensamblar` lo llama. Los verificadores lo llaman también, nunca reimplementan.
- Los sidecars genéricos que ya existen sobre la función (`-duraciones`, y la parte de función de `-quitar`) se vuelven afirmaciones. `-titulos-anteriores`, `-correcciones` y `-sinopsis` siguen siendo de la obra.
- Las herramientas que leen fuentes secundarias (el vigía, la revisión de salas, `ig-programa.py`) **proponen afirmaciones**: un archivo de propuestas que Juan aprueba por lote. No escriben en `-afirmaciones.json` solas.

### 5.1 La cola de propuestas (`pipeline/propuestas.py`, 16 oct 2026)

- `festivals/staging/<fid>-propuestas.json`: cada propuesta es `{id, estado: pendiente|aceptada|rechazada, por, fecha, afirmacion, decision?: {fecha, frase}, rechazada_antes?}`.
- El **id** es el de *un dato de una fuente* (qué + quién + cuándo). La misma fuente con la misma fecha no se repite; una fuente más nueva con el mismo valor entra otra vez, y si ese valor ya se rechazó lo muestra con la frase de Juan.
- Nadie propone en nombre de Juan (`tipo: juan` no entra por la cola). Solo un festival del modelo tiene cola.
- **Aceptar** corre el armado real (`ensamblar.py <fid> --ver`) antes y después: si aparece un fallo nuevo, se deshace todo. La afirmación aceptada lleva `propuesta: <id>` (clave declarada; `validar` la ignora).
- Comandos: `python3 pipeline/propuestas.py` (pendientes) · `proponer <fid> <a.json> --por <quién>` · `aceptar|rechazar <fid> <ids…|todas> --frase "…"`.

### 5.2 El actualizador (`pipeline/actualizar.py`, 17 oct 2026)

El vigía AVISA; el actualizador ACTÚA, dentro de una frontera estrecha (senior dev + tech lead, 17 oct):
- **Qué fuente:** solo la estructurada del propio festival (la base de Fantasmagoría, el JSON de FICICA), lo que declara `pipeline/actualizador.json` por festival (`antes`: el comando que la baja; `pasos`: los del plan que re-corre). Lo de una sala o de Instagram va a la cola de propuestas.
- **Qué cambio:** solo día, hora o sala de funciones que ya existen. Una función nueva o que sale, cualquier otro campo, o la raíz del festival → frena y avisa.
- **Tope:** más de 5 funciones cambiadas en una corrida → frena (suele ser una fuente rota).
- **Interruptor:** `activo: false` lo apaga sin tocar código.
- **Sin cambios no publica:** cada deploy hace recargar a los teléfonos.
- **Corre cada hora** desde una tarea programada, en su propia copia: si hay cambios publicables, validadores → **abre el PR y avisa a Juan; NO fusiona solo** (decisión de Juan, 18 oct). Lo fusiona Juan, o Claude cuando él lo pida. Si en un par de festivales no propone nada equivocado, gana el merge automático con el tope de 5. Empieza solo con Fantasmagoría.
- **Tope de tiempo** por comando (300 s: una fuente colgada no cuelga la tarea) y, al fallar o frenar, **deshace también lo nuevo** (`git clean` además del `checkout`), para que la corrida siguiente no aborte por copia sucia.

## 6. Guardianes (validate.py) — a implementar en la fase 1

Todavía no existen; se escriben sin corchetes para no confundirlos con los activos. Al implementarse, cada uno toma su nombre entre corchetes.

| Guardián | Qué vigila |
|---|---|
| `[funcion-tests]` (activo) | Los tests de `tests/pipeline/test_funcion.py`: una regla por caso, probados por mutación (11/11). |
| `[funcion-autoprueba]` (activo) | Cada regla de la §4 atrapa su cebo (rango, más reciente, conflicto, supuesto, estimado). |
| `[afirmaciones-validas]` (activo; reúne fuente, formato y rango) | Toda afirmación tiene tipo, url o frase, y fecha. Sin fuente no entra. |
| `afirmacion-con-ancla` | Toda afirmación encuentra su función base. Si no, aborta (nunca se ignora en silencio). |
| `[conflicto-abierto]` (activo) | No hay conflictos sin decisión. |
| `[excepcion-en-crudo]` (activo, deuda en `pipeline/funcion-deuda.json`) | Ningún crudo tiene tablas de corrección de función. Lista de deuda que solo baja, como `[dato-que-no-viaja]`. |
| `[entrada-explicita]` (activo, deuda por festival; 0 si está en el modelo) | Toda función publicada dice su entrada, aunque sea un supuesto marcado. |
| `[propuestas-validas]` (activo) | La cola `festivals/staging/<fid>-propuestas.json` (`pipeline/propuestas.py`): estado conocido, id que corresponde a su afirmación, decisión con frase y fecha, y toda aceptada presente en `-afirmaciones.json`. |
| `[entrada-mixta]` (activo) | En un festival `mixed`, toda función dice si se paga (`is_free` explícito, salvo invitación). La regla `funcion.paga_supuesta` escribe `is_free: false` con marca `supuesto` donde nadie dijo nada; antes la app lo deducía de la falta del dato. Bisturí para festivales que no se re-arman: `pipeline/entrada-paga-supuesta.py`. Festivales sin `ticketing_model`: todo libre, supuesto declarado aquí y no por función (16 oct 2026). |
| `casilla-obligatoria` | Día, hora, sede, título y tipo en toda función. |

## 7. Plan

| Fase | Qué | Hecho cuando |
|---|---|---|
| 1 | `funcion.py` + tests primero (cada regla con su caso, más mutación) + guardianes con autoprueba. Ningún festival migrado. | tests verdes; autoprueba atrapa cada cebo |
| 2 | App: mostrar `sala`; entrada sin adivinar (leer explícito; ausente = guardián rojo, no «paga»); `screenings[]` copia todas las casillas de la §4; invitados. Copy de la sala, con Juan. | tests de UI; Juan aprueba el copy |
| 3 | Migrar los festivales vivos, uno por uno: BHFF (salas, links, clausura gratis desde la Cinemateca), MIDBO, FICICA, Ficcali, Fantasmagoría. Cada re-armado contra producción: cero cambios salvo los aprobados. | diff contra producción revisado |
| 4 | Migrar el resto de las 70+ tablas, festival por festival. | `excepcion-en-crudo` en cero |
| 5 | Vigía y revisión de salas proponen afirmaciones. | primera propuesta aprobada |

## 8. Riesgos

- **Ancla que cambia en la fuente principal.** Si el festival mueve una función en su propia web, el ancla vieja ya no está. El guardián aborta y alguien re-ancla. Es ruidoso a propósito.
- **Migración que cambia datos sin querer.** Cada festival se compara contra producción antes de publicar (memoria «arreglo aguas abajo se pierde»).
- **Dos rutas a la vez durante la migración.** Mientras quede un crudo con tablas, conviven. `excepcion-en-crudo` mide la deuda y solo puede bajar.

## 9. Auditoría del 16 oct 2026 (senior dev + tech lead) y correcciones

Dos auditorías independientes sobre la fase 3 (BHFF). Ninguna afecta a BHFF
(sin anclas repetidas ni duraciones estimadas; su resultado se comparó campo
por campo), pero el modelo **no está listo para migrar más festivales**. Nada
se migra hasta cerrar C1–C6.

| # | Hallazgo | Severidad | Corrección |
|---|---|---|---|
| C1 | El ancla `(sede, día, hora)` choca con dos salas a la misma hora (22 de 34 festivales; FICDEH 175, TIFF 134): el resolver revienta o pierde una función | bloqueante | **id estable por función** (`func_id`), registro `<fest>-funciones-ids.json` y redirecciones, como `work_id` del catálogo. Las afirmaciones apuntan al id |
| C2 | La duración estimada se calcula antes de reponer lo publicado (`_conservar_publicado`) y de `-duraciones`: puede pisar un dato real (la cicatriz de Ficcali) | bloqueante | la estimación sale del resolver y va como último paso, solo donde siga vacía |
| C3 | Se cae con una fuente sin rango para la casilla, al correr dos veces sobre su salida, sin `_ancla`; un conflicto entre funciones nuevas se pierde; `libre` deja el link de compra; horas comparadas como texto | crítica | correcciones puntuales, cada una con su test |
| C4 | `validar` deja pasar formatos que la app no usa (`7pm`, `75`, `None` en obligatorias, fechas imposibles o futuras, url sin https) | alta | tabla de formato por casilla |
| C5 | Las decisiones de Juan no caducan | alta | cada decisión guarda `contra` (el valor que pisó); si ese valor cambia, vuelve a revisión (como `catalogo.decision_pisada`) |
| C6 | Fechas no comparables (publicación contra captura) | alta | `fuente.publicado` y `fuente.capturado`; la regla usa `publicado` |
| C7 | `ticketing_model_de` lee el config como texto | media | leer `FESTIVAL_CONFIG` como dato (node) |
| C8 | Inscripción implica «gratis» | media | `requires_registration` deja de ser un valor de `entrada`: casilla propia, combinable con `boleta` |
| C9 | Sin cola de conflictos ni de propuestas, sin informe de decisiones, 4 guardianes de §6 sin implementar, sin herramienta para migrar las tablas | media | `<fest>-conflictos.json`, `<fest>-propuestas.json` con estado, `funcion.py informe`, los guardianes, y un migrador tabla → afirmaciones |
| C10 | Casillas de la función y de la obra mezcladas (`title`, `duration`, `film_list`, `premiere`) | media | `nivel: funcion|obra` por casilla; las de obra van a las decisiones del catálogo |

Pendiente de Juan: ¿las actividades (eventos, actividad abierta) también van
«libre» por supuesto, como las proyecciones? Hoy sí (regla «sin aviso de pago
es gratis»).

**Estado (16 oct 2026):**
- **Corregidos, con tests escritos antes y probados por mutación (15 de 16; el que sobrevive es un mutante equivalente, una guarda redundante): C1 (id estable y registro; el ancla usa el venue publicado, con su ciudad — «Cinema Local» existe en Bogotá y en Cali), C2, C3, C4, C5, C6, C7, C8.** Los 34 festivales publicados pasan por `asignar_ids` + `resolver` sin pérdidas ni caídas; BHFF re-armado sobre el modelo corregido da exactamente lo mismo.
- **C9 hechos:** los guardianes `[excepcion-en-crudo]` (72 tablas de deuda), `[entrada-explicita]` (836 funciones de deuda; 0 para un festival en el modelo), `[afirmaciones-validas]` y `[conflicto-abierto]`, probados por mutación sobre datos reales; `python3 pipeline/funcion.py informe <fest>` (qué se decidió, de dónde y contra qué); y `publicar.py` rechaza un build de una corrida fallida (el sello guarda el paso que falló).
- **C10 hecho:** toda casilla es de la función (`NIVEL`); lo de la obra no es una casilla y va por el catálogo.
- **Pendientes de C9:** la cola de propuestas (`-propuestas.json` con estado y aceptación) y el migrador de tablas → afirmaciones. Son las herramientas de la fase 4; hasta tenerlas, no se migra otro festival.

### 9.1 Revisión previa al merge (16 oct 2026)

Antes de abrir el PR de C1–C10, una revisión independiente encontró 10 hallazgos más. Todos tienen su reproducción como test (`tests/pipeline/test_funcion_revision.py`) y se probaron por mutación (10 de 10, después de reforzar los dos tests que la primera vuelta dejó pasar):

| # | Hallazgo | Corrección |
|---|---|---|
| R1 | una duración ESTIMADA volvía en el montaje siguiente como «conservada de lo publicado» (deshacía C2) | en un festival del modelo, `_conservar_publicado` no repone `duration` |
| R2 | `ensamblar --ver` escribía el registro de ids y los conflictos | toda escritura del modelo depende de `escribir` |
| R3 | una función ausente prestaba su id a otra función con el mismo título | las ausentes quedan marcadas y solo vuelven por su clave exacta, con aviso |
| R4 | una hora mala en la base tumbaba el montaje; `99:99` pasaba | rango de hora; un día u hora fuera de formato en la base es un conflicto `formato-base`, no una caída |
| R5 | el detector de tablas no veía asignaciones anotadas, `dict(...)`, tablas dentro de un `if` o de `main()`, ni los nombres `CORRECCION`, `SEDE_…`, `TITULO…`, `QUITAR` | cubiertos; la deuda pasó de 72 a 98 por la definición, no por tablas nuevas. Límite declarado: un nombre que no se parezca, o una mutación (`X['k'] = v`), no se ve |
| R6–R10 | node ausente, ruido diario del registro, idempotencia al borrar una decisión, fallo limpiado por otro paso con el mismo número, fecha de la máquina | corregidos |

**Límite conocido:** cinco festivales viejos, sin pipeline, publican el día y la hora en otro formato (`'MAR 21'`, `'Miércoles'`, `'8:00 PM'`: AFF, Cinemancia 2025, FICCI 65, Leviza, Tribeca). La app los entiende, pero el modelo los marca como `formato-base`. Como no tienen pipeline no pasan por el modelo; para migrar alguno, primero hay que normalizar su formato.

**Otros dos límites, aceptados:**
- Si una función desaparece de la fuente y vuelve **movida** (otra sede, día u hora), no recupera su id: recibe uno nuevo y sus afirmaciones fallan con `AnclaPerdida`, en voz alta. Arreglo: re-apuntar el `ancla` de la afirmación a la función nueva.
- El registro de ids no se poda: las ausentes se quedan, marcadas. Son inofensivas (no prestan su id) y el archivo crece unas decenas de líneas por festival.

## 11. El identificador estable de la función — PROPUESTA (18 oct 2026, sin implementar)

Pedido de Juan vía la sesión Main: hoy la app reconoce una función por título + día + hora (+ sede). Si el festival cambia la hora o el título, la trata como otra: se rompen planes, retrasos, boleta y avisos, y `titulos_anteriores` es un parche. **El modelo ya tiene la mitad**: `asignar_ids` (C1) da un `_fid` y lo guarda en `<fid>-funciones-ids.json` (BHFF, Fantasmagoría, Ficcali). Esto lo completa.

### 11.1 La forma
- **`id`** en cada función publicada (schema.org: `ScreeningEvent.identifier`), opaco: `f_` + 10 hex. Se calcula UNA vez, al nacer la función, y **nunca se recalcula**: el registro es la fuente, no la fórmula. Sobrevive a cambios de hora, sala, sede y título.
- Único **dentro del festival**; global = `<festival>/<id>`.
- Alineación schema.org: función = `ScreeningEvent` (`identifier`, `startDate`, `location`), obra = `Movie` (`work_id` del catálogo, `workPresented`), sede = `Place` (`venue`), festival = `superEvent`. Solo nombres; el JSON no cambia de forma.

### 11.2 Quién lo asigna
- El **pipeline**, en `ensamblar` (`funcion.asignar_ids`), para TODO festival con plan, no solo los del modelo. El registro `<fid>-funciones-ids.json` se versiona y es la fuente.
- Festivales sin pipeline (legado): un script de una pasada les asigna ids y congela su registro.
- `publicar.py` deja pasar `id` (hoy descarta todo lo que empieza con `_`).

### 11.3 Cómo se casa una función nueva con una vieja al re-armar
En orden, como hoy, más lo que falta:
1. **clave exacta** (sede, día, hora, sala, título) → mismo id;
2. **una sola candidata** libre que coincida en (sede, título) → *movida*; o en (sede, día, hora, sala) → *renombrada*;
3. **NUEVO — un solo cambio de sede**: (título, día, hora) iguales en otra sede → *trasladada* (el sismo de FICMA, la sala de BHFF);
4. **NUEVO — cambio doble** (título Y hora, o sede Y hora): no se adivina. Va a una **decisión registrada** en `<fid>-funciones-decisiones.json` — `{"viejo": id, "nuevo": clave | "es_otra", "por_que", "quien", "fecha"}` —, como las decisiones de identidad del catálogo. Sin decisión: id nuevo y el armado AVISA (no frena: una función que de verdad es otra no debe bloquear).
5. Más de una candidata → ambigua → decisión, nunca en silencio (como hoy).

### 11.4 Partir y fusionar
- **Se parte** (un programa pasa a ser dos funciones): el id viejo queda en el registro con `partida_en: [id1, id2]`; las hijas nacen con id nuevo. La app migra lo guardado a la primera hija y avisa.
- **Se fusionan** (dos funciones pasan a ser una): la nueva conserva el id de la más antigua; la otra queda `fusionada_en: id`.
- **Se cancela / sale**: el id queda `ausente` (como hoy) y nunca se reusa.
- Todo eso viaja publicado en `ids_anteriores` de la función destino (el hermano de `titulos_anteriores`), para que la app migre sin leer el registro.

### 11.5 Guardián `[id-funcion-estable]`
Contra `main`: (a) todo `id` publicado antes sigue publicado, o figura `ausente` / `partida_en` / `fusionada_en` en el registro; (b) ningún `id` cambia de función salvo por una regla de §11.3 registrada; (c) un `id` nuevo solo para una función nueva. Con autoprueba (un cebo por regla) y mutación.

### 11.6 Plan (PRs chicas)
1. Esta propuesta → Juan.
2. `id` publicado + `ids_anteriores` + guardián, en los 3 festivales que ya tienen registro (BHFF, Fantasmagoría, Ficcali). La app no lo lee todavía.
3. Reglas nuevas (trasladada, decisión registrada, partir/fusionar), con tests primero.
4. Todo festival con plan; luego los de legado con su registro congelado.
5. (Main) la app: plan, retrasos, boleta y avisos apuntan al `id`.
