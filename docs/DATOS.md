# Datos aparte del código

> 18 oct 2026, decisión de Juan: «separar los datos de lo demás es una obligación».
> Migración 0009 · `pipeline/publicar-datos.py` · `src/controller/datos-fuente.js`.

## Por qué

Hasta el 18 oct un horario corregido viajaba como una versión de la app: PR →
bump → CI de la app (mediana 44 min en octubre) → merge → deploy de Pages. Los
datos de un festival cambian a otra velocidad que el código, y para un festival
en curso esa espera es inaceptable.

## Cómo funciona

```
festivals/<id>.json ─ publicar-datos.py ─▶ guardianes (≈2 min) ─▶ rama `datos` ─▶ función `publicar-datos`
                                                                                   │
                     almacén `datos` (Supabase Storage, público para leer)  ◀──────┘
                       festivales/<id>/<huella12>.json   versiones inmutables
                       indice.json                       la vigente de cada festival
                                   │
                     la app (datos-fuente.js) ◀─ al cargar y en el refresco en caliente
```

- **Autorización sin claves:** la función solo acepta el commit que está en la
  punta de la rama `datos`; solo quien puede empujar al repo publica.
- **Guardianes:** los mismos de un PR de datos. Si uno falla, no se publica.
- **Respaldo:** si el festival no está en el índice, si el almacén falla o si el
  índice trae `apagado: true`, la app lee la copia de la web de siempre.
- **Main sigue siendo la historia:** el PR de datos se hace después. Al entrar a
  main, el job «Datos al almacén» republica ese festival **si ya está en el
  almacén**, así el almacén nunca queda atrás de main.
- **Un festival entra al almacén a propósito, de a uno** (Juan, 18 oct): la
  primera vez con `publicar-datos.py`. Un PR que toca muchos JSON no mueve a
  nadie al almacén.
- **Registro:** cada publicación queda en `publicaciones_datos` (quién, cuándo,
  qué versión).

## Recetas

| Quiero… | Comando |
|---|---|
| corregir un festival ya | editar (o re-armar con el pipeline) y `python3 pipeline/publicar-datos.py <id>` |
| ver si pasaría | `python3 pipeline/publicar-datos.py <id> --probar` |
| volver atrás | dejar el archivo como estaba (`git checkout <commit> -- festivals/<id>.json`) y publicar |
| cambiar el afiche de portada, las fechas, el nombre o el estado de un festival | editar su entrada en `FESTIVAL_CONFIG` (src/config.js; afiche nuevo = archivo NUEVO en assets/keyart/) y `python3 pipeline/publicar-datos.py <id>` |
| sumar un festival nuevo a la portada | su entrada en `FESTIVAL_CONFIG` + su JSON, y `publicar-datos.py <id>` |
| apagar el almacén para todos | `python3 pipeline/publicar-datos.py --apagar` (y `--encender`): la app vuelve a la web en ≤1 min |

## La ficha del festival (Etapa 2·B1, 19 oct 2026)

La **ficha** es lo que la portada necesita antes de bajar ningún festival:
nombre, lema, ciudad, fechas, zona horaria, afiche de portada, estado. Los
campos son `CAMPOS_FICHA` en `src/fichas.js` (nunca `storageKey`: es la llave de
lo que cada usuario guardó).

- **Se escribe** donde siempre, en `FESTIVAL_CONFIG` (src/config.js): ahí la
  vigilan sus guardianes (nombre oficial, afiche 2:3, fechas del afiche, zona…).
- **Se publica** con `publicar-datos.py`: viaja en el mismo commit que el JSON
  (`fichas/<id>.json`, extraída con `scripts/ficha-de.mjs`, el mismo módulo que
  usa la app) junto con la imagen del afiche. La función la pone en el índice y
  guarda el afiche en `datos/keyart/<huella>.<ext>`: el nombre es su contenido,
  así que un afiche nuevo nunca queda tapado por el viejo en los teléfonos.
- **La app** la aplica encima de la copia que trae adentro: al arrancar con la
  última copia guardada (la portada sale al instante y sin conexión) y, al bajar
  el índice, re-dibuja la portada si algo cambió. Un festival que la app no
  conoce aparece si su ficha trae lo mínimo.
- **Guardián:** `[fichas-campos]` — la lista de campos es la misma en la app y
  en la función.
- El PR con el cambio de config.js va después, para la historia, como con los datos.

## Afiches de obras y actividades (19 oct 2026)

Siguen en `assets/` y los sirve la web (B2, moverlos al almacén, se descartó por
costo). Dos reglas que ahora frenan solas:

- **El afiche va primero:** `publicar-datos.py` frena si el JSON nombra un
  `/assets/…` que no está en el repo o que la web todavía no sirve (o sirve con
  otro tamaño). Orden: PR de los afiches → merge → se publica la web → recién ahí
  `publicar-datos.py`. Desde main, el job espera hasta 10 min al deploy.
- **Afiche nuevo = archivo nuevo:** `[asset-write-once]` en validate.py frena
  cualquier imagen de `assets/` que cambie de contenido con el mismo nombre (el
  SW la guarda para siempre; quien vio la vieja no vería la nueva). Usar `-v2`.

## Fuentes vivas (20 oct 2026)

Lo que el festival re-publica mientras corre (página de programación, API, PDF)
se declara en `fuentes_vivas` del plan y se baja con
`python3 pipeline/correr.py <id> --bajar`. Con el festival vigente, una fuente de
más de 24 h frena a `correr.py` y a `publicar-datos.py`. `[fuentes-vivas-declaradas]`
avisa qué festival vigente todavía no las declara. Detalle: pipeline/PROTOCOLO.md
Paso 0 y pipeline/fuentes_vivas.py.

## Lo que NO pasa por acá

El código de la app (src/, index.html, sw.js…): PR + CI completo + deploy, como
siempre.
