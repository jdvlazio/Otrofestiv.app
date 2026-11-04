# Mesa de luz — el póster de los programas

> **APROBADA** por Juan (31 oct 2026). El diseño lo aprobó Juan sobre prototipo
> (`design-previews/mesa-de-luz/`, fuera del repo). Este documento propone la
> doctrina que reemplaza a la **Forma C (la Escalera)** de `docs/POSTERS.md`.
> Pendiente: implementación.

## Por qué cambia

- **La Escalera no deja reconocer las obras.** Desde 3 obras, cada afiche tapa
  casi la mitad del anterior y solo el de adelante se ve entero.
- **Con 9 obras o más cae al generativo.** En FICIDI, 4 de los 7 programas no
  muestran ningún afiche teniendo los 12 guardados.
- **Los programas mixtos pierden obras.** De 385 programas sin afiche propio en
  el catálogo, 95 tienen afiche solo en una parte de sus obras: hoy esas obras
  no aparecen.

## Qué se revoca, dicho explícitamente

§6.0 dice «**Nunca varias imágenes** (Juan, 18 ago 2026). Mosaicos, escalonados
y tiras de índice quedan descartados: a 84 px son ruido». La Mesa de luz es un
mosaico, así que esta regla se revoca para los programas. La razón de 18 ago se
midió en el chip: en la Mesa de luz el chip se dibuja sin filo y sin grano, y se
lee como «varios afiches», que es el dato que tiene que dar.

También se revoca «la Escalera existe solo de 2 a 8 obras». La Mesa de luz no
tiene tope.

## Lo que NO cambia

- **La jerarquía (26 ago 2026).** Primero el afiche oficial del programa, si el
  festival mandó uno. Después la Mesa de luz. El generativo queda solo para los
  programas en que ninguna obra tiene afiche ni fotograma.
- **El pie dice la verdad del programa:** «N obras · X min», con la duración del
  bloque.
- **Sin título del programa dentro del póster.** El título vive al lado.
- **Un solo dueño del modelo** (`programParts` / `slotPosterParts`) y **un solo
  dibujante**, que reemplaza a `makeSharedSlotSVG`.

## La forma

**La mesa.** El fondo es gris cálido `#221F1B`, entre `--surf-2` y `--surf-3`, y
no el negro: sobre el negro las sombras no se ven. Lleva grano fino en toda la
mesa, el filete de sección a sangre arriba y la luz de sección abajo a la
izquierda.

**Las obras.** Van en orden de catálogo, en una rejilla suelta:

- **Columnas:** `ceil(√N)`.
- **Reparto:** las filas se reparten parejo y las más llenas van al medio
  (7 → 2-3-2), así ningún afiche queda solo abajo.
- **Giro:** ±5°, y ±9° con 4 obras o menos. Sale de una semilla del título del
  programa, así que el mismo programa siempre se ve igual.
- **Desplazamiento:** un desorden mínimo.
- **2 obras:** dos afiches grandes cruzados, uno arriba a la izquierda y el otro
  abajo a la derecha.

**El papel.**

- **Filo:** hueso `#E9E1D0`, del 2,5 % del ancho.
- **Radio:** 13 % del ancho, el token de pósters. La imagen interior lleva un
  radio concéntrico.
- **Borde de luz:** una línea de 1 px más clara del lado de la luz y otra más
  oscura del lado opuesto.

**La profundidad.** La sombra tiene cuatro capas: una de contacto y tres
difusas. Caen hacia arriba a la derecha, lejos de la luz. Cada obra flota a una
**altura distinta**: el factor de elevación va de 0,45 a 1,35 en orden de
apilado, así que las de arriba proyectan una sombra más larga.

## Qué representa a cada obra

| La obra tiene | Se dibuja como |
|---|---|
| afiche (oficial, TMDB o propio) | el afiche, con filo hueso |
| solo un fotograma (`posterSource: editorial`) | **boleta con la foto arriba** |
| nada | **boleta** |

**La boleta** es la entrada de la función, un objeto del cine:

- **Papel:** hueso con grano suave.
- **Texto:** **solo el título de la obra**, en Plus Jakarta Bold, negro cálido.
  Sin rótulo, director ni país: lo que se ve en un póster es el título.
- **Troquel:** una línea punteada con muescas a los lados.
- **Talón:** mitad ámbar `#F59E0B` y mitad negro `#0B0A08`.
- **Con fotograma:** la foto 16:9 va arriba, dentro de la boleta. Un fotograma
  suelto sobre la mesa se probó y se descartó («no se ve bien»).
- **Siempre encima** de los afiches que pisa, para que su texto se lea.

**El tamaño del título es UNO solo** (31 oct 2026, ver «Pósters sin afiche»).

## El chip de 56 px

Es la misma composición, pero sin filo hueso, sin grano y sin borde de luz. La
boleta conserva el talón y deja de mostrar el título, que ahí no se leería.

## Pósters sin afiche (aprobado por Juan, 31 oct 2026)

Fuera de la mesa, lo que no tiene afiche se dibuja sobre **negro con la luz de
sección** abajo a la derecha, la identidad de hoy. Se descartó el papel gris
(«perdimos identidad»).

**Tipografía de un solo tamaño en todos los pósters:**

- **Rótulo:** 9 px.
- **Título:** 11 px.
- **Duración:** 8 px.

El título nunca crece ni se encoge. No se corta con guion. Se recorta con «…»
a partir de la línea 6, y solo baja de tamaño cuando una sola palabra no cabe
en el ancho (mínimo 9 px). El título no repite el rótulo: «Panel: Memoria…»
bajo PANEL queda «Memoria…».

**La forma según lo que es:**

| Es | Forma | Título |
|---|---|---|
| Evento (charla, panel, taller, encuentro) | **Escarapela**: banda sólida de color con el rótulo en negro y el agujero del cordón | abajo |
| Obra sin afiche ni fotograma | **Boleta** negra: troquel con muescas y talón delgado de color | arriba |
| Obra con solo fotograma | **Boleta con el fotograma enmarcado** (16:9, radio 4) y la luz de la foto derramada sobre el negro (desenfoque, opacidad 0,26) | debajo del fotograma |

Regla: con banda, el título va abajo; sin banda, arriba. Se agregan un grano
muy suave y un brillo de 1 px en el borde de arriba.

**Paleta de secciones «Sala».** Son los mismos tonos de `ARCHETYPE_COLORS`, en
`oklch(0.66 0.075 h)`: apagados y terrosos. El ámbar de marca `#F59E0B` queda
como el único color vivo.

## Por resolver al implementar

- **El grano** en SVG sale de `feTurbulence`, con un id por póster (lección del
  §ids únicos). Hay que medir cuánto cuesta dibujar 40 pósters en una grilla.
- **La fuente** dentro de un SVG inline: hoy el generativo dibuja en el
  `viewBox`; con la boleta, el título necesita Plus Jakarta cargada.
- **Los tests:** se re-apuntan los de la Escalera (`poster.test.js`) y se agregan
  guardianes para el programa mixto, para más de 8 obras y para «el afiche
  oficial gana sobre la mesa».
