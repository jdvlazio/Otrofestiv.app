# Pósters nuestros · «C2 sobre retícula»

> **ESTADO: PROPUESTA — 18 ago 2026.** Nada de esto está en producción ni en
> `docs/POSTERS.md`. La ley vigente sigue siendo `docs/POSTERS.md`; este archivo
> es el sistema que Juan y Claude construyeron en la sesión de Onboarding, para
> que no se pierda. Cuando se apruebe e implemente, las reglas se mudan a
> `docs/POSTERS.md` (fuente única) y este archivo queda como rationale.

Aplica **solo a los pósters nuestros** (editorial y generativo). El **póster
original nunca se toca** — sigue la regla de vocabulario de `docs/POSTERS.md`.

---

## 1. El problema, medido

En el grid de 4 columnas la tarjeta mide **84 × 125 px**. Ahí:

| | hoy | por qué |
|---|---|---|
| letra de la sección | **4,55 px** | `_BAND_FS = 0.0542` → 5,42% del ANCHO, una constante |
| alto de la banda | **36 px** (28,89%) | fijo, no depende del texto |
| aire lateral | 13% del ancho | `_BAND_PADX = 0.0667` a cada lado |

La banda es una losa de 36 px que contiene letra de 4,5 px: **nunca se llena**,
porque el tamaño está atado al ancho y no al espacio disponible. Ese es el
origen de «no estamos leyendo bien las secciones», y ocurre igual con nombres
cortos («FEATURED») que largos.

Y el problema no es de un festival: **fuera de CineAutopsia casi todos nuestros
pósters son de solo texto** — 24 funciones en FICDEH, 7 en FINCA (charlas,
ceremonias, programas). Ahí la tipografía no decora: es el póster entero.

---

## 2. La retícula

El póster es 2:3, así que la unidad cuadra sin residuo:

```
u = ancho / 8          →  el póster es 8u × 12u (módulos cuadrados)
línea base vertical    =  media unidad (24 líneas)
margen                 =  0,75u   →  caja de contenido = 6,5u
filete de sección      =  0,25u de alto, a sangre
```

### Regla del sistema

> **El módulo manda en X, la proporción de la imagen manda en Y.**

De ahí salen los únicos tamaños de imagen admitidos — los que, manteniendo la
proporción intacta, caen en línea de media unidad:

| módulo | anchos | alto resultante | comportamiento |
|---|---|---|---|
| **still 16:9** | 8u · 4u | 4,50u · 2,25u | **sangra** (es una ventana) |
| **póster 2:3** | 2u · 3u · 4u | 3u · 4,5u · 6u | **respeta el margen** (es un objeto) |

Anchos de 5u o 6u para un 16:9 dan 2,81u y 3,37u: se salen de la retícula. No
se usan.

Composiciones exactas dentro de la caja de 6,5u:
- dos pósters de 3u + calle de 0,5u
- tres pósters de 2u + dos calles de 0,25u

---

## 3. Los niveles (del referente de Adidas)

El nivel **no se configura: se deduce** de cuántas obras con imagen tiene la
función. Un largometraje entra siempre en calma; un programa de nueve cortos
entra siempre en ruido.

| nivel | cuándo | composición |
|---|---|---|
| **0 · solo tipo** | sin imagen | la sección ocupa 3,4u; el título manda abajo |
| **1 · calma** | 1 obra | un still de 8u en y=3,5 |
| **2 · equilibrio** | 2 obras | dos de 4u escalonados media unidad |
| **3 · potencia** | 3+ obras | tres de 4u en racimo |

Con pósters verticales (caso FINCA) los niveles 2 y 3 usan el módulo 2:3
dentro del margen, no el 16:9 a sangre.

---

## 4. Marca

Tomada del sistema de social media (`09_Marketing`, iCloud) para que la app y
los posts sean la misma marca:

```
fondo    #0A0A0A      (el negro de los slides, NO #141414 — ver el incidente
                       de color de los posts 10–27)
blanco   #F0EDE8
ámbar    #F59E0B
gris     #888888
fuente   Plus Jakarta Sans 800
luz      glow ámbar radial en la esquina inferior DERECHA
```

**Por qué la luz va a la derecha y no a la izquierda como en los slides:** en el
póster esa esquina la ocupa el título y la luz se lo comía.

El **color de arquetipo de la sección** deja de ser una losa y pasa a ser:
filete superior de 0,25u + el color de la propia tipografía de la sección. Se
conserva porque es la señal que se lee de un vistazo al hacer scroll.

---

## 5. El blur, con otro oficio

El blur **no se descarta** (decisión de Juan): cambia de trabajo.

- **Antes:** rellenaba el marco 2:3 por detrás del still. Era tapaagujeros.
- **Ahora:** es **la luz que la obra derrama** hacia el negro de marca, con
  máscara descendente, y **llena los módulos que el still no ocupa** en los
  niveles 2 y 3.

Sin eso, los huecos de la retícula se leen como imagen que falta. Con eso, el
racimo se lee como un campo compuesto y cada póster toma color de su propia
obra sin dejar de ser Otrofestiv.

---

## 6. Tipografía: ajuste al espacio, no constante

La sección y el título se ajustan al **mayor tamaño que cabe en su caja**, con
corte de línea **por ancho medido** (no por número de caracteres — eso partía
mal y dejaba títulos en una sola línea minúscula).

Medido en la tarjeta real de 84 px:

```
                        CineAutopsia   FICDEH    FINCA    Esfuerzo (43 car)
hoy      sección            4,5 px     4,5 px    4,5 px      4,5 px
C2       sección           11,4 px    15,0 px    8,5 px      9,2 px (3 líneas)
```

La prueba de esfuerzo es «Retrospectiva 10 Años del Acuerdo de Paz» (43
caracteres, FICDEH). Entra legible en tres líneas **sin tocar el nombre que puso
el festival** — la regla de que los nombres de sección no se tocan sigue intacta.

El corte de línea debe seguir usando `_bandWrap` (regla de Juan: ninguna línea,
salvo la última, termina en conjunción, preposición, artículo o separador).

---

## 7. Decisiones tomadas en el camino

- **Fuera el chevron `›`.** A 84 px se leía como una basurita, y competía con
  el glow por la misma esquina. La marca la carga la luz.
- **El pie lleva el dato** (`9 obras · 96 min`, `Charla · Bogotá`,
  `director · país · duración`). Es lo único que llena el vacío con
  información en vez de con decoración.

## 8. Abierto

1. El tercer still del nivel 3 va **centrado** (x=2), lo que rompe la
   alineación a la izquierda del resto. Alineado sería más disciplinado.
2. A tamaño real los stills del nivel 3 miden ~5 px de alto: **señalan** que es
   un programa, no **informan** de las obras. Si tienen que informar, el nivel 3
   baja a dos stills.
3. El nivel 0 no tiene luz de obra (no hay obra). Queda negro con el glow.
   ¿Tinte bajo del color de sección? Sería inventar color.
4. Falta regla de prioridad para el pie cuando no cabe (hoy se corta con `…`).

## 9. Implementación (cuando se apruebe)

Va dentro de los **dos dueños únicos** — `_buildPosterV16` (generativo) y
`editorialFrame` (con imagen), ambos en `src/view/`. **No** se crea una copia
bespoke en ninguna superficie nueva: esa deuda ya se pagó una vez (las 7 copias
divergidas, Fase C). Es cambio de app → sesión de **Main**, no de Onboarding.

El ajuste tipográfico en producción NO debe medir el DOM: se calcula en el
`viewBox` del SVG, que es determinista y no depende del layout.

Banco de pruebas de esta sesión (sin commitear, en la raíz del worktree):
`mockup-posters.html` · `-2` · `-3` · `-4`. Se levantan con el server local y
usan componentes y datos reales.
