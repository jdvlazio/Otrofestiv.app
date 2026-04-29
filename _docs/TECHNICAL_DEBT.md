# Deuda Técnica — Otrofestiv

## 1. Sistema de Posters — Arquitectura Incompleta

**Fecha:** 26 Abr 2026  
**Prioridad:** Alta  

### Estado actual
Los posters de películas se obtienen de `posters{}` en el JSON del festival — un mapa de título → URL de TMDB hardcodeada manualmente. Cada vez que se agrega una película nueva, alguien debe:
1. Buscar el TMDB ID
2. Encontrar el poster path en TMDB
3. Hardcodearlo en `festivals/aff-2026.json`

### El problema
- Proceso manual → propenso a errores (demostrado con Homebound y A Sad and Beautiful World el 26 Abr 2026)
- Múltiples fuentes de poster pueden coexistir y contradecirse (`posters{}`, `tmdb_id` en film, `CUSTOM_POSTERS`, `SHORT_IMGS`)
- Viola Single Source of Truth

### La arquitectura correcta
```
build.js
  → lee festivals/*.json
  → para cada film con tmdb_id, hace fetch a TMDB API en build-time
  → embebe las URLs de poster en el bundle
  → sin requests en runtime, sin race conditions, sin pasos manuales
```

Cada film solo necesita:
```json
{ "title": "Homebound", "tmdb_id": 1227739 }
```

### Por qué no está implementado
El servidor de build de Claude tiene un allowlist de dominios que no incluye `api.themoviedb.org`. El build-time fetch requiere correr `build.js` localmente o en GitHub Actions donde TMDB sí es accesible.

### Próximos pasos
1. Mover el build a GitHub Actions con acceso a TMDB
2. En `build.js`: para cada film con `tmdb_id`, fetchear el poster path y embeber la URL
3. Eliminar `posters{}` del JSON — reemplazar por `tmdb_id` en cada film
4. Eliminar `SHORT_IMGS`, `CUSTOM_POSTERS` del código — consolidar en un solo lookup
5. Films sin TMDB (cortos, eventos, talleres) → poster generativo, sin campo `tmdb_id`

### Impacto si no se resuelve
Cada festival nuevo requiere búsqueda manual de poster paths. Error humano garantizado a medida que crece el número de festivales y películas.

---

## 2. Build desde Servidor de Claude — Limitaciones de Red

**Fecha:** 26 Abr 2026  
**Prioridad:** Media  

El build corre en el servidor de Claude con allowlist restringida:
- ✓ github.com, npmjs.org, pypi.org (build/deploy)
- ✗ api.themoviedb.org (posters)
- ✗ api.anthropic.com solo para Claude

Mover el build a GitHub Actions daría acceso completo a red y resolvería la deuda #1.

---

## 3. Film Object — No hay Single Source of Truth

**Fecha:** 26 Abr 2026  
**Prioridad:** Alta  

### Estado actual
La información de una película está dispersa en múltiples lugares:
- `films[]` → metadatos (título, horario, director, sinopsis)
- `posters{}` → URL del poster, keyed por título (separado)
- `lbSlugs{}` en FESTIVAL_CONFIG → slug de Letterboxd (separado y duplicado)
- `film.tmdb_id` → a veces en el objeto, a veces no
- `film.lb_slug` → a veces en el objeto, a veces no

### El problema
Agregar una película nueva requiere tocar 3-4 lugares distintos. Error humano garantizado. Demostrado el 26 Abr 2026 con Homebound y A Sad and Beautiful World.

### La arquitectura correcta — template único
```json
{
  "title": "Un mundo frágil y maravilloso",
  "title_en": "A Sad and Beautiful World",
  "director": "Cyril Aris",
  "country": "Líbano, Alemania",
  "flags": "🇱🇧🇩🇪",
  "duration": "110 min",
  "year": 2025,
  "genre": "Drama romántico",
  "synopsis": "...",
  "day": "DOM 26",
  "time": "13:30",
  "venue": "Cineprox Las Américas",
  "section": "✨ Impact Hits",
  "day_order": 5,
  "tmdb_id": 1376838,
  "lb_slug": "a-sad-and-beautiful-world"
}
```

Todo en un objeto. El poster se resuelve de `tmdb_id` en build-time. El link de Letterboxd de `lb_slug`. Sin `posters{}`. Sin `lbSlugs{}` en config.

### Próximos pasos
1. Migrar todos los films: mover poster URL → `tmdb_id`, mover lb_slug → `lb_slug` en film
2. Eliminar `posters{}` del JSON
3. Eliminar `lbSlugs` de FESTIVAL_CONFIG en config.js
4. Actualizar `lbUrl()` y `getFilmPoster()` para leer solo del film object
5. Documentar el template canónico de film para futuros festivales

---

## 4. Sistema de Build Modular — Regresión de Render

**Fecha:** 26 Abr 2026  
**Prioridad:** Crítica  

### Qué pasó
El 25 Abr se refactorizó el monolito `index.html` en archivos modulares (`src/`). El sistema de build concatena esos archivos en `dist/index.html`. Esta refactorización introdujo un problema de render en iOS/WebKit: las acciones (Añadir, Quitar, Intereses, Vista) ejecutaban su lógica correctamente pero el DOM no se repintaba visualmente hasta que el usuario cambiaba de tab o contexto.

### Causa identificada
El `index.html` monolítico original (Apr 24) funcionaba porque el JS se ejecutaba en un contexto de página completa donde los reflows eran síncronos. La refactorización no introdujo diferencias en la lógica, pero sí en algún aspecto del entorno de ejecución que aún no fue identificado con precisión.

### Solución temporal
Se restauró el `index.html` de Apr 24 (commit `211ec2a`) como base, editándolo directamente. Los datos del festival se inyectan manualmente via script.

### Riesgo activo
Editar `index.html` directamente no es sostenible. Cualquier feature nueva toca el monolito sin el sistema de build. No hay validación automática (`verify.js`), no hay separación de responsabilidades.

### Próximos pasos
1. Comparar el output del build modular con el Apr 24 monolito línea por línea — encontrar la diferencia exacta que causa el problema de render
2. Corregir el build system
3. Volver al flujo `src/` → `node build.js` → push

---

## 5. Cambiar Función — Caso No Cubierto

**Fecha:** 27 Abr 2026  
**Prioridad:** Baja (no aplica en AFF, aplica en festivales con reposiciones)

### El caso
Un usuario tiene una película en su plan. El mismo film tiene otra función en un día/hora distinto. El usuario quiere cambiar a esa función. Hoy debe: quitar del plan → esperar sugerencia del algoritmo → añadir. El algoritmo puede sugerir la misma función que el usuario quería cambiar.

### La solución propuesta
En la ficha de una película que ya está en el plan, mostrar todas las funciones disponibles del mismo film y permitir cambiar directamente. El sistema valida conflictos antes de confirmar el cambio.

### Cuándo implementar
Antes de FICCI 66 o cualquier festival con reposiciones frecuentes. No urgente para AFF ni festivales pequeños.

---

## 6. Señal Visual — Films Pasados en Intereses

**Fecha:** 27 Abr 2026  
**Prioridad:** Baja  

### El caso
Intereses funciona como watchlist persistente del festival. Las películas pasadas permanecen en la lista pero `screeningPassed()` las excluye del algoritmo correctamente. Sin embargo no hay distinción visual entre films pendientes y films ya pasados en la vista de Intereses.

### La solución propuesta
Mostrar los films pasados con opacidad reducida o un badge "Pasó" en la vista de Intereses, igual que en la cartelera. No cambiar la lógica — solo la señal visual.

### Cuándo implementar
Cualquier momento — es un cambio de CSS/template, sin riesgo lógico.
