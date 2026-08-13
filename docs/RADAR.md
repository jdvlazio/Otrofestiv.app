# RADAR — descubrimiento y vigilancia de festivales

> Dueño: el chat de **Onboarding** (es dato de festival, no código de la app).
> Registro: issues `label:radar` en este repo. Tarea programada: `radar-festivales`.

## Por qué existe

La fuente de consulta de Juan era visitar a mano la sección «Eventos en Colombia» de
Proimágenes cada tanto. Eso dependía de que él se acordara, y falla justo con los
festivales que se anuncian **sobre la fecha**: FICMA apareció así. El radar no
reemplaza el criterio de Juan —él decide qué se onboardea—; reemplaza el *acordarse*.

**La prioridad la declaró Juan (11 ago 2026):** lo valioso no es descubrir nombres
nuevos —para eso basta dos veces por semana— sino **vigilar cada festival ya conocido
que viene en camino**, para llegar al pre-onboarding con tiempo.

## La fuente

`https://proimagenescolombia.com/secciones/eventos/eventos.php?tipo=1`

Medido el 11 ago 2026: **HTML estático** (sin JavaScript), pestaña «En Colombia»
(`tipo=1`) separada de las internacionales, paginación `?pagina=N&tipo=1`, ~8 eventos
por página ordenados de futuro a pasado. El detalle (`evento_interna.php?ntd=N`) trae
**web oficial e Instagram**, que es lo que hace barato el pre-onboarding.

**Proimágenes descubre y detecta cambios; NO corrige datos del festival.** Es la
autoridad sobre *qué festivales existen* y sobre *que algo se movió* — nada más.
Cuando su ficha discrepa de un dato que salió del propio festival, gana el
festival. Caso real (11 ago 2026): Proimágenes lista QAFF como 14–18 SEP y
nuestra rama tiene 14–20, porque el calendario oficial del festival programa 17
funciones en Bogotá los días 19 y 20 que Proimágenes no recoge. Un listado de
terceros no borra el calendario de la casa. Lo que sí hace ese desajuste es
disparar una VERIFICACIÓN, que es exactamente para lo que sirve el radar.

### La web NO es la única fuente del festival

**Regla (Juan, 12 ago 2026): nunca decidir sobre un festival mirando solo su web.
Hay que consultar también sus redes.** Muchos festivales pequeños dejan la web
congelada en la edición anterior y anuncian TODO por Instagram.

Caso que la originó, el mismo día: **CineAutopsia**.

| fuente | qué decía |
|---|---|
| web oficial | edición **2025** — congelada |
| Proimágenes | 21–29 AGO 2026 |
| **Instagram (bio)** | **«21 - 28 Agosto 2026»** + publicaciones hasta el 11 de agosto |

Con la web sola, el veredicto habría sido «web abandonada → descartado», y
habríamos perdido un festival que abre en 9 días. La bio de Instagram —una línea—
lo resolvió.

Corolarios que valen para cualquier festival:

- **Una web vieja no prueba que no haya edición.** Prueba que la web está vieja.
  Solo el silencio en TODOS los canales es evidencia de que no hay edición.
- **Las fechas de la bio ganan a las de un tercero** (ver la regla de autoridad
  arriba): IG dice 21–28, Proimágenes 21–29. Gana el festival — y la discrepancia
  dispara verificación, no corrección automática.
- **Un canal vivo es señal por sí mismo.** Publicaciones recientes dicen que el
  equipo está activo aunque no hayan publicado programación.

Lo que el bot SÍ puede hacer: leer la bio y los textos públicos del perfil. Lo que
NO: dar por bueno un silencio de Instagram —a menudo es bloqueo, no ausencia—.
Si el fetch de la red no devuelve nada legible, **eso no es «no hay nada»**: es un
vistazo manual pendiente, y así debe reportarse (misma familia que la regla de
ceguera).

> ⚠ El dominio viejo `proimagenes.com.co` **no resuelve**. Si alguien lo ve escrito en
> notas antiguas, es la razón por la que un fetch «no anda».

## El registro: issues, no archivos

Un issue por festival, `label:radar` + un label de estado:

| estado | significa |
|---|---|
| `radar:nuevo` | sin triage — Juan decide vigilando o descartado |
| `radar:vigilando` | en seguimiento pre-onboarding |
| `radar:en-onboarding` | rama activa |
| `radar:publicado` | en producción |
| `radar:descartado` | fuera de alcance (mercados de industria, temporadas de circulación) |
| `radar:alerta` | el radar no pudo leer una fuente |

**No hay archivo de estado ni commits automáticos.** Los issues SON la memoria: el
cuerpo lleva el `ntd=` de Proimágenes (la clave de matcheo), web, IG y fecha de
detección; los comentarios `ESTADO WEB:` llevan la historia. Un segundo registro
derivado sería una fuente de verdad que se desincroniza — la deuda que ya pagamos
con el roster duplicado en `[state-mirror]`.

## El semáforo

El color lo pone la FECHA; la acción, lo que el festival haya publicado.

| | Faltan | Sonda | Qué significa |
|---|---|---|---|
| 🟢 VERDE | >45 días | lunes | Solo existe en el radar |
| 🟡 AMARILLO | 45–15 días | lunes y jueves | **Ventana de pre-onboarding** |
| 🔴 ROJO | ≤14 días | diaria | Publicable o publicado |
| ⚫ EN CURSO | ya arrancó | diaria | Cambios y cancelaciones |

**La alarma que importa: ROJO sin programación.** Un festival a 10 días sin
programa publicado no es «sin novedades» — es el aviso de que hay que escribirle
al festival, y va como PRIMERA línea del resumen. En FICMA y en Cinemancia lo
que frenó el onboarding nunca fue nuestro trabajo: fue esperar el dato.

**El AMARILLO es el disparador del pre-onboarding**, y es también cuando conviene
abrir una tarea dedicada a ese festival —bajar programación, contar obras, mirar
el formato del catálogo—, que se borra al onboardearlo. Serían 1–2 vivas a la vez.
El radar liviano no hace profundidad; avisa de cuándo hace falta.

## La regla de ceguera

Si la fuente no responde o el parseo da **cero** eventos, el radar **no** reporta
«sin novedades»: abre/comenta el issue `RADAR CIEGO`. Un radar que calla cuando está
roto es peor que no tener radar — es la misma familia que la card genérica «EVENTO»
o el guardián con parser flojo: un resultado plausible que no avisa que no es fiable.

## Instagram queda fuera del bot

Scraping frágil y territorio del chat de Social Media. Cuando un festival está a ≤42
días y su web no dice nada, el resumen **sugiere el vistazo manual** con el enlace a
la mano. La automatización llega hasta donde es confiable, y ahí lo dice.

## Nuestro lado se mide, no se lee

El cuerpo del issue es una **foto del día en que se escribió**, no el estado. El 13 ago
2026 el radar reportó que la rama de QAFF tenía las fechas mal cuando ya estaban
corregidas hacía dos días, y citó «faltan 53 fichas» de Cinemancia cuando la
programación ya estaba montada: las dos salieron de leer el issue en vez del repo.

Por eso el radar ahora **mide** antes de informar: rama (fecha, behind/ahead), `_etapa`
del JSON, cuántas entradas de `films` tienen `day`, cuántas sin póster o sinopsis, y si
`src/config.js` ya menciona el festival. Es `git`/`gh`, no cuesta WebFetch. La regla es
la misma que aplicamos al dato: **si no lo mediste, no lo afirmes** — «no medido» es una
respuesta válida en el informe; inventar el estado de una rama no lo es.

`_etapa` es la pieza que hace esto verificable, y hoy **solo FICDEH la declara**. Cuando
un JSON no la tiene, el informe lo dice en vez de adivinar.

## El informe: tres bloques

El informe se ordena por **quién tiene la pelota**, no por color: el color es del
calendario, la decisión no. El formato viejo mezclaba en un mismo párrafo lo que publicó
el festival, lo que teníamos nosotros y lo que había que hacer, ordenado por semáforo —
y enterraba la única línea accionable entre datos de contexto.

- **HOY DECIDE** — la pelota es nuestra: falta un paso de nuestro lado o hay que
  escribirle al festival. Imperativo, con días que faltan y acción exacta. Primera de
  todas, la alarma de ROJO sin programación. Si no hay nada: «HOY DECIDE: nada».
- **ESPERANDO AL FESTIVAL** — la pelota es del festival: qué dato exacto falta y desde
  cuándo se espera. Sin acciones nuestras.
- **SIN MOVIMIENTO** — una sola línea agregada, más los cambios de color de los próximos
  7 días y la próxima sonda.

Cada afirmación sobre nuestro estado cita el número medido (obras, cuántas con día,
behind/ahead) en vez de adjetivos como «lista» o «a medias».

## Prompt de la tarea (copiable)

Para recrearla desde el chat de Onboarding (así sus resúmenes llegan a quien hace el
trabajo), crear una tarea programada `radar-festivales`, diaria, con este prompt:

> ⚠ El `taskId` de una tarea programada es ÚNICO y GLOBAL: el almacén
> (`~/.claude/scheduled-tasks/`) es compartido entre sesiones, así que dos chats
> NO pueden tener a la vez una `radar-festivales`. El traspaso entre sesiones es
> **borrar y recrear**, no «crear y después borrar». Antes de borrar, comparar el
> `SKILL.md` existente contra el bloque de aquí abajo: si son idénticos no se
> pierde nada, y el que recrea es quien recibe los resúmenes. Hecho así el 11 ago
> 2026 al pasar el radar de Main a Onboarding, sin corridas perdidas.

```
Sos el RADAR de festivales de Otrofestiv. Corrés a diario, pero cada corrida decide QUÉ toca hoy según estas reglas. Objetivo: que ningún festival colombiano se acerque sin que lo estemos mirando, gastando lo mínimo. Todo por lecturas de texto (WebFetch) y gh CLI — NUNCA abras navegador.

REGISTRO ÚNICO: los issues con label `radar` del repo jdvlazio/Otrofestiv.app (usá `gh -R jdvlazio/Otrofestiv.app`). Cada festival tiene UN issue con su ficha (fechas, ciudad, web, IG, `ntd=` de Proimágenes). Estados por label: radar:nuevo / radar:vigilando / radar:en-onboarding / radar:publicado / radar:descartado. NO crees archivos de estado ni commits: los issues SON la memoria.

REGLA DE AUTORIDAD: Proimágenes DESCUBRE festivales y detecta que algo se movió. NO corrige datos que salieron del propio festival. Si su ficha discrepa de lo nuestro, eso dispara una VERIFICACIÓN y se reporta — nunca una corrección automática.

── 1. SONDA PROIMÁGENES (solo lunes y jueves; los demás días saltá esta sección) ──
Fuente: https://proimagenescolombia.com/secciones/eventos/eventos.php?tipo=1 (pestaña «En Colombia»; paginación ?pagina=N&tipo=1). Leé las páginas 1 y 2 (los eventos van de futuro a pasado; con 2 páginas cubrís todo lo vigente — si TODOS los de la página 2 aún no pasaron, leé también la 3).
Por cada evento extraé: nombre, fechas, ciudad, ntd=NÚMERO del enlace de detalle.
Compará contra los issues `label:radar` existentes (matcheá por el ntd= en el cuerpo, y si no está, por nombre aproximado):
- Evento SIN issue → leé su ficha de detalle (evento_interna.php?ntd=N) para sacar web oficial e Instagram, y creá el issue: título `RADAR: <nombre> — <ciudad>, <fechas>`, labels `radar` + `radar:nuevo`, cuerpo con fuente/ntd/fecha de detección/web/IG.
- Evento CON issue cuyas fechas cambiaron → comentá el issue con las fechas viejas y nuevas. Si el issue es de FICMA (aplazado), esto es LA señal de fechas nuevas: además marcalo claramente en el comentario («FICMA anunció fechas nuevas en Proimágenes») porque dispara la reversión del estado aplazado en la app.
- NO todo lo que lista Proimágenes es un festival. Las franjas de exhibición itinerante que corren meses (ej. Temporada de Cine Colombiano, 3 meses) no se pueden planear como festival: van a `radar:descartado` y se cierran, con el motivo escrito. El issue cerrado queda como registro para no re-abrirlo en la próxima edición.

── 2. SEMÁFORO: qué se revisa hoy (todos los días) ──
Listá los issues `label:radar` con estado radar:vigilando o radar:en-onboarding. Para cada uno, parseá sus fechas del título y calculá los días que faltan para que ARRANQUE (hoy en zona America/Bogota). El color lo pone la fecha:

  VERDE    (más de 45 días)  → revisalo solo los LUNES
  AMARILLO (45 a 15 días)    → revisalo LUNES y JUEVES. Es la ventana de pre-onboarding.
  ROJO     (14 días o menos) → revisalo TODOS LOS DÍAS
  EN CURSO (ya arrancó)      → revisalo TODOS LOS DÍAS, buscando cambios y cancelaciones

«Revisar» = WebFetch de su web oficial Y de su Instagram (las dos URLs están en el cuerpo del issue), preguntando: ¿hay fechas de la edición actual? ¿hay programación/cartelera publicada? ¿hay boletería o acreditación abierta? En Instagram, leé además la BIO del perfil: muchos festivales pequeños dejan la web congelada en la edición anterior y anuncian las fechas ahí (CineAutopsia, 12 ago 2026: web en 2025, bio con «21 - 28 Agosto 2026»). NUNCA concluyas «no hay edición» mirando solo la web.
Compará contra el último comentario tuyo en el issue que empiece con «ESTADO: ». Si algo CAMBIÓ (aparecieron fechas, programación, boletería), comentá «ESTADO: <fecha> · <fuente: web|IG>» + qué cambió. Si nada cambió, NO comentes (cero ruido).
Si el fetch de la red social no devuelve contenido legible, eso NO es «no hay nada» —suele ser bloqueo, no ausencia—: anotalo como vistazo manual pendiente en el informe, nunca como evidencia de que no hay edición. Discrepancia entre fuentes → gana el festival (bio/web oficial) sobre el tercero (Proimágenes), y se dispara verificación, nunca corrección automática.

── 3. NUESTRO LADO: se MIDE en el repo, no se lee del issue ──
El cuerpo del issue es una FOTO del día en que se escribió, no el estado. Tu memoria, tampoco. Antes de escribir una sola línea del informe, medí nuestro lado con git/gh — es gratis, no gasta WebFetch.
Regla dura: **si no lo mediste, no lo afirmes.** «No medido» es una respuesta válida en el informe; inventar el estado de una rama no lo es. (13 ago 2026: el radar reportó que la rama de QAFF tenía las fechas mal cuando ya estaban corregidas hacía dos días, y citó «faltan 53 fichas» de Cinemancia cuando la programación ya estaba montada. Las dos salieron de leer el issue en vez del repo.)

Para cada festival en `radar:en-onboarding` (y cualquiera con rama), desde el repo local:

    git fetch --prune
    git for-each-ref --format='%(refname:short) | %(committerdate:short) | %(contents:subject)' refs/remotes/origin | grep -i <festival>
    git rev-list --left-right --count origin/main...origin/<rama>   # behind / ahead

Y del JSON del festival en esa rama (`festivals/<fest>.json` o `festivals/staging/<fest>.json`), con `git show "origin/<rama>:<archivo>" | python3 …` — ojo en zsh: SIEMPRE `origin/${b}:ruta` con llaves, si no da «bad substitution»:
- **`_etapa`** — el estado declarado por el propio pipeline. Es la fuente de verdad de en qué punto está. Si el JSON NO tiene el campo, decilo en el informe: es un festival cuyo estado no es legible por máquina (a 13 ago 2026 solo FICDEH lo declara).
- **`films`**: cuántas entradas, y cuántas tienen `day`. Cero con día = catálogo sin programación (esperando al festival). Todas con día = programación ya montada. Cada entrada de `films` es una función, no una obra única.
- cuántas sin `poster` y cuántas sin `synopsis`.
- si `src/config.js` de la rama ya menciona el festival → la entrada en `FESTIVAL_CONFIG` está hecha o pendiente.

── 4. LA ALARMA QUE IMPORTA: ROJO SIN PROGRAMACIÓN ──
El color lo pone la fecha, pero la ACCIÓN la pone lo que el festival haya publicado. Si un festival está en ROJO (≤14 días) y NINGUNA de sus fuentes publica programación, eso NO es «sin novedades»: es el aviso de que hay que escribirle al festival. Va en el bloque HOY DECIDE, primero de todo, con el nombre, los días que faltan y qué falta exactamente. Lo mismo si está en ROJO y le faltan las fechas de la edición.
Razón: en FICMA y en Cinemancia lo que frenó el onboarding nunca fue nuestro trabajo, fue esperar el dato del festival. Cuanto antes se pida, mejor.

── 5. REGLA DE CEGUERA (siempre) ──
Si Proimágenes no responde, o el parse de la página da CERO eventos, o la web de un festival vigilado no carga en dos intentos: NO lo reportes como «sin novedades». Buscá el issue abierto con label radar:alerta titulado «RADAR CIEGO» (si no existe, crealo con labels radar + radar:alerta) y comentá qué fuente falló y desde cuándo. Un radar que calla cuando está roto es peor que no tener radar. Cuando la fuente vuelva a leer bien, comentá que se restableció y cerrá el issue de alerta.

── 6. INFORME: TRES BLOQUES, SIEMPRE EN ESTE ORDEN ──
El informe se ordena por QUIÉN TIENE LA PELOTA, no por color. El color es del calendario; la decisión no. Nunca mezcles en una misma línea lo que publicó el festival con lo que tenemos nosotros — esa mezcla es lo que volvía el informe ilegible.

**HOY DECIDE** — solo aquello donde la pelota es NUESTRA: falta un paso de nuestro lado, o hay que escribirle al festival. Una línea por asunto, en imperativo, con el festival, los días que faltan y la acción exacta. Si no hay nada accionable, escribí «HOY DECIDE: nada». Aquí va, primera, la alarma de ROJO sin programación (§4).

**ESPERANDO AL FESTIVAL** — una línea por festival cuya pelota es del festival: qué dato exacto falta (programación con días/sedes/horarios, fechas, boletería) y desde cuándo se espera. Nada de acciones nuestras acá.

**SIN MOVIMIENTO** — UNA sola línea agregada con los que se revisaron y no cambiaron, con nombre y color. Al final de esta línea, dos datos de contexto: qué festivales CAMBIAN DE COLOR en los próximos 7 días (sobre todo los que entran en AMARILLO, que es cuando arranca el pre-onboarding) y cuándo es la próxima sonda Proimágenes.

Reglas del informe:
- Cada afirmación sobre NUESTRO estado tiene que venir de §3, medida hoy. Citá el número (obras, cuántas con día, behind/ahead) en vez de adjetivos como «lista» o «a medias».
- Números de issue en todo hallazgo, como enlace.
- Alertas de ceguera y vistazos manuales pendientes: dentro de HOY DECIDE si hay que mirar algo a mano; si no, al final de SIN MOVIMIENTO.
- Si te equivocaste en una corrida anterior y ya lo comentaste en el issue, decilo en HOY DECIDE — una corrección no anunciada deja el registro sucio.
- Si no hubo absolutamente nada nuevo y ninguna alerta, el informe entero es una sola línea: «Radar <fecha>: sin novedades (N vigilados — R rojo, A amarillo, V verde; próxima sonda Proimágenes <día>).»

Límites de recursos: máximo ~10 WebFetch por corrida. git/gh NO cuentan (son locales, medí sin miedo). Si la vigilancia del día excede el tope, priorizá por color (ROJO primero, después AMARILLO) y anotá en SIN MOVIMIENTO cuáles quedaron sin revisar.
```
