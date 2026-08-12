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

── 1. SONDA PROIMÁGENES (solo lunes y jueves; los demás días saltá esta sección) ──
Fuente: https://proimagenescolombia.com/secciones/eventos/eventos.php?tipo=1 (pestaña «En Colombia»; paginación ?pagina=N&tipo=1). Leé las páginas 1 y 2 (los eventos van de futuro a pasado; con 2 páginas cubrís todo lo vigente — si TODOS los de la página 2 aún no pasaron, leé también la 3).
Por cada evento extraé: nombre, fechas, ciudad, ntd=NÚMERO del enlace de detalle.
Compará contra los issues `label:radar` existentes (matcheá por el ntd= en el cuerpo, y si no está, por nombre aproximado):
- Evento SIN issue → leé su ficha de detalle (evento_interna.php?ntd=N) para sacar web oficial e Instagram, y creá el issue: título `RADAR: <nombre> — <ciudad>, <fechas>`, labels `radar` + `radar:nuevo`, cuerpo con fuente/ntd/fecha de detección/web/IG.
- Evento CON issue cuyas fechas cambiaron → comentá el issue con las fechas viejas y nuevas. Si el issue es de FICMA (aplazado), esto es LA señal de fechas nuevas: además marcalo claramente en el comentario («FICMA anunció fechas nuevas en Proimágenes») porque dispara la reversión del estado aplazado en la app.

── 2. VIGILANCIA POR FESTIVAL (todos los días) ──
Listá los issues `label:radar` con estado radar:vigilando o radar:en-onboarding. Para cada uno, parseá sus fechas del título y calculá días restantes (hoy en zona America/Bogota). Cadencia:
- Más de 60 días → revisalo solo los lunes.
- 21–60 días → revisalo lunes y jueves.
- 20 días o menos → revisalo TODOS los días.
«Revisar» = WebFetch de su web oficial (URL en el cuerpo del issue) preguntando: ¿hay fechas de la edición actual? ¿hay programación/cartelera publicada (enlaces a programación, PDF, «ya está disponible»)? ¿hay venta de boletas o acreditación abierta? Compará contra el último comentario tuyo en el issue que empiece con «ESTADO WEB:». Si algo CAMBIÓ (apareció programación, cambiaron fechas, abrió boletería), comentá el issue con «ESTADO WEB: <fecha de hoy>» + qué cambió. Si nada cambió, NO comentes (cero ruido). Instagram NO se revisa por bot: si el festival está a ≤42 días y su web no dice nada, agregá UNA línea al resumen sugiriendo un vistazo manual a su IG (el enlace está en la ficha).

── 3. REGLA DE CEGUERA (siempre) ──
Si Proimágenes no responde, o el parse de la página da CERO eventos, o la web de un festival vigilado no carga en dos intentos: NO lo reportes como «sin novedades». Buscá el issue abierto con label radar:alerta titulado «RADAR CIEGO» (si no existe, crealo con labels radar + radar:alerta) y comentá qué fuente falló y desde cuándo. Un radar que calla cuando está roto es peor que no tener radar. Cuando la fuente vuelva a leer bien, comentá que se restableció y cerrá el issue de alerta.

── 4. RESUMEN (siempre, al final) ──
Terminá con un resumen de MÁXIMO 6 líneas: qué se revisó hoy, hallazgos (issues nuevos/comentados con sus números), alertas, y qué festivales entran en ventana pronto. Si no hubo absolutamente nada nuevo y ninguna alerta, el resumen es una sola línea: «Radar <fecha>: sin novedades (N festivales vigilados, próxima sonda Proimágenes <día>).»

Límites de recursos: máximo ~10 WebFetch por corrida. Si la vigilancia del día excede eso, priorizá por cercanía de fechas y anotá en el resumen cuáles quedaron sin revisar.
```
