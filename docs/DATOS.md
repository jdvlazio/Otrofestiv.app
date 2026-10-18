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
  main, el job «Datos al almacén» republica ese festival, así el almacén nunca
  queda atrás de main.
- **Registro:** cada publicación queda en `publicaciones_datos` (quién, cuándo,
  qué versión).

## Recetas

| Quiero… | Comando |
|---|---|
| corregir un festival ya | editar (o re-armar con el pipeline) y `python3 pipeline/publicar-datos.py <id>` |
| ver si pasaría | `python3 pipeline/publicar-datos.py <id> --probar` |
| volver atrás | dejar el archivo como estaba (`git checkout <commit> -- festivals/<id>.json`) y publicar |
| apagar el almacén para todos | `python3 pipeline/publicar-datos.py --apagar` (y `--encender`): la app vuelve a la web en ≤1 min |

## Lo que NO pasa por acá

El código de la app (src/, index.html, sw.js…): PR + CI completo + deploy, como
siempre.
