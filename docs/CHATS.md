# Los dos chats — quién hace qué, y quién decide

> Rige igual en **Otrofestiv - Main** y en **Otrofestiv - Onboarding**.
> Escrito el 12 ago 2026, después de dos días en que un sismo obligó a los dos
> chats a trabajar sobre lo mismo al mismo tiempo.

## La frontera

| | Onboarding | Main |
|---|---|---|
| **Dominio** | el DATO del festival | la APP |
| Archivos | `festivals/`, `pipeline/`, la entrada del festival en `FESTIVAL_CONFIG`, entradas de `NOTICES` | `src/`, `index.html`, `tests/`, `validate.py`, `docs/ARQUITECTURA.md` |
| Fuentes | Proimágenes, el radar, la web y las redes del festival | el código y la pantalla |
| Cambia | *qué dice* la app de un festival | *cómo se comporta* la app para cualquier festival |

La línea está bien puesta y hay prueba: el estado APLAZADO lo construyó Main y el
`status` de FICMA lo puso Onboarding; el mecanismo de `cities` lo hizo Main y el
aviso del sismo lo metió Onboarding. Nadie pisó a nadie.

**Regla vieja que sigue viva:** «código de la app acá, datos del festival allá».
Main no commitea datos de festival; Onboarding no cambia el comportamiento de la app.

## Juan no es el cable

Los dos chats **se hablan directo** (`send_message`). El 11 y 12 de agosto se
cruzaron ~15 mensajes sin intermediario. Cuando Juan estuvo fuera hizo de relay
porque no había otra opción — no porque haga falta.

**Juan entra solo cuando la decisión es suya**, y son cuatro:

1. **Copy** — palabras nuevas o cambiadas. Sin excepción.
2. **Diseño** — qué se ve, dónde, y qué se marca.
3. **Alcance** — qué festival entra, cuál se descarta, qué se aplaza.
4. **Publicar** — mergear a producción cuando hay 1, 2 o 3 de por medio.

Todo lo demás —diagnóstico, implementación, tests, verificación, coordinación—
se resuelve entre chats. A Juan le llega el resultado, no el proceso.

## Tres reglas, cada una con su cicatriz

### 1 · Un PR, un dueño

El chat dueño del archivo abre **y** mergea su PR. Nunca dos manos en la misma rama.

> **Cicatriz (12 ago):** Main hizo `--amend` + `push -f` sobre la rama de #585
> mientras Onboarding la mergeaba. El merge se llevó solo el primer commit y dos
> arreglos ya escritos —el filtro del aviso y el sticky— **desaparecieron sin que
> nadie lo notara**. Juan los reportó como «falta esto» y Main habría jurado que
> estaba. Si hay que sumar algo a un PR abierto: commit nuevo encima, o PR aparte.

### 2 · Autorización permanente para lo que no decide nada

Cada chat mergea lo suyo con CI verde **sin preguntar**, siempre que no haya
palabras nuevas ni cambio visual. Si las hay, para y pregunta.

Esto saca a Juan de la cadena sin sacarlo del control: sigue decidiendo lo que
importa, deja de aprobar lo mecánico.

> **Corolario (11 ago):** cuando un chat rompe el *medio* que el otro propuso
> para conservar el *fin*, actúa y lo explica después. Onboarding tuvo que
> borrar la tarea del radar de Main —el `taskId` es único y global, así que
> «creá la tuya y después borro la mía» era imposible— y lo hizo tras comparar
> los dos `SKILL.md` byte a byte. Fue correcto. **El medio es negociable; el fin no.**

### 3 · Onboarding mide el dato, Main mira la pantalla

Es el hallazgo más útil de estos dos días. Los tres bugs serios salieron de
**mirar la pantalla**, no el JSON:

- **«CANCELADA» junto a «CON BOLETA»** — la app ofrecía comprar entrada para una
  función suspendida por un sismo.
- **La fecha impresa DENTRO del afiche** — ningún `grep` encuentra píxeles.
- **El aviso al 97% del documento** — existía, se contaba, y no se veía.

En los tres, la verificación contra el dato daba **correcto**. La simulación de
Onboarding contó 88 funciones selladas y las 88 estaban bien; lo que no ve desde
ahí es qué *otra cosa* dice la card al lado.

Por eso el reparto de verificación: **Onboarding valida contra el JSON servido;
Main abre la app en producción con la UA del WebView y mira.**

## Cuando algo urge y el otro chat no responde

Decilo con las dos opciones y un plazo, como se hizo el 12 de agosto:

> «A) ya estás en ello → decime cuánto. B) no podés → lo hago yo.
> Si no hay respuesta en un rato, asumo B y te lo cuento después.»

Es mejor que esperar en silencio o que duplicar trabajo. La única condición es
avisar antes de arrancar y contar después lo que se hizo.
