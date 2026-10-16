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

## 6. Guardianes (validate.py) — a implementar en la fase 1

Todavía no existen; se escriben sin corchetes para no confundirlos con los activos. Al implementarse, cada uno toma su nombre entre corchetes.

| Guardián | Qué vigila |
|---|---|
| `funcion-autoprueba` | Cada regla de la §4 atrapa su cebo (rango, más reciente, conflicto, supuesto, estimado). |
| `afirmacion-con-fuente` | Toda afirmación tiene tipo, url o frase, y fecha. Sin fuente no entra. |
| `afirmacion-con-ancla` | Toda afirmación encuentra su función base. Si no, aborta (nunca se ignora en silencio). |
| `conflicto-abierto` | No hay conflictos sin decisión. |
| `excepcion-en-crudo` | Ningún crudo tiene tablas de corrección de función. Lista de deuda que solo baja, como `[dato-que-no-viaja]`. |
| `entrada-explicita` | Toda función publicada dice su entrada, aunque sea un supuesto marcado. |
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
