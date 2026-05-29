# Otrofestiv — Constitution
> El *por qué* de las decisiones de arquitectura. El *qué* y el *cómo* viven en `docs/ARQUITECTURA.md`.
> Actualizar cada vez que se tome una decisión de arquitectura significativa.

---

## Principios fundacionales

### Single-file architecture
`index.html` contiene CSS + JS + HTML de la app. No hay build step, no hay bundler, no hay dependencias externas. Esto es una decisión consciente: el costo de mantenimiento de un toolchain supera el beneficio para un proyecto de un solo desarrollador con deployment manual. La restricción genera disciplina de diseño (tokens, componentes reutilizables) en lugar de depender de librerías.

### Vanilla JS sin frameworks
Sin React, Vue, ni Svelte. La app no tiene suficiente complejidad de estado para justificar un framework completo. El DOM es la fuente de verdad de la UI; el estado vive en `localStorage` y en variables globales swapeadas por `loadFestival()`.

### Festival data como JSON externo
Los datos de cada festival no viven en `index.html` — viven en `festivals/<id>.json` cargados async. Esto permite actualizar datos de un festival sin redeploy del app shell, y mantiene `index.html` ligero.

### Mobile-first, PWA
El 100% de los usuarios accede desde móvil. Desktop es nice-to-have, no requisito. La app es instalable como PWA (Service Worker + manifest), lo que mejora la experiencia offline y el acceso rápido.

---

## Decisiones de diseño

### Sistema de tokens (CSS custom properties)
Todo valor de spacing, tipografía y color usa `var(--)`. Esto no es preferencia estética — es la única forma de mantener consistencia a escala en un archivo de ~10k líneas sin un preprocessor. La regla se audita con `tools/audit.sh`.

### Amber como color de acción
`--amber` (#F59E0B) es el único CTA primario. Verde (`--green`) es confirmación/estado activo. Rojo (`--red`) es error/conflicto. Ningún otro color tiene semántica de acción. Esta restricción previene proliferación de colores de acción que degradan la jerarquía visual.

### Lucide como sistema de iconos
Un solo pack, inline SVG, sin dependencias. Los emojis de país (flags) y emojis de categoría de sección son la única excepción — no hay equivalente de alta calidad en Lucide para iconografía cultural/geográfica.

### Pósters: cadena de prioridad unificada
La función `getFilmPoster(f)` encapsula toda la lógica de resolución de poster (custom override → inline → legado → generativo → null). Llamar directamente a `getPosterSrc()` o `makeProgramPoster()` desde templates está prohibido porque rompe la cadena y crea inconsistencias silenciosas.

### Opacidad: feedback y estado, no jerarquía
Un control interactivo en reposo expresa jerarquía secundaria mediante token de color sólido, nunca mediante `opacity`. La opacidad se reserva para: (a) feedback `:active`, (b) `:disabled` real, (c) des-énfasis de estado de contenido (past/watched/conflict), (d) transiciones de overlay, (e) placeholders decorativos. Distinción clave: un indicador de affordance (chevron, ×, flecha) dentro de un target mayor que ya lee como interactivo puede ir tenue; la regla solo aplica cuando el elemento atenuado ES el control. Referencia canónica: `.int-prio-btn` (estrella de Prioridades) — `#555` apagado, `--amber` encendido, `opacity:1`; `.6`+`scale` solo en `:active`.

---

## Decisiones de proceso

### Copy como artefacto de diseño
Las strings de la UI no son "texto que se puede cambiar después". Cada string es una micro-decisión de UX que afecta la percepción del producto. Las decisiones de copy se toman con el mismo rigor que las decisiones de diseño visual — siempre con Juan actuando como Content Designer + UX Writer.

### i18n desde el principio
La app soporta ES + EN. Esto no es una feature opcional — es parte del modelo de producto (festivales internacionales como Tribeca requieren interfaz en inglés). Toda string nueva entra simultáneamente en `es.json` y `en.json`.

### validate.py como gate obligatorio

⚠️ **NUNCA** usar `python3 validate.py | tail -N` — el pipe hace que el exit code sea el de `tail` (siempre 0), no el de validate.py. Así el `&&` chain continúa aunque haya errores. Siempre correr sin pipe para verificar, o usar `python3 validate.py; echo "exit: $?"`.

### validate.py como gate obligatorio
El validador chequea JS syntax, divs críticos, CSS corruption y patrones prohibidos. Es la única forma de detectar regresiones en un archivo de ~10k líneas sin test suite formal. Correr antes de cada commit no es opcional.

### Atomicidad de tasks
`tasks.md` se actualiza al terminar la implementación de cada tarea — en el mismo commit que el código, no al final de la sesión. Un commit de feature sin su `tasks.md` correspondiente es un commit incompleto. Esta regla existe porque el contexto entre sesiones se pierde: el tasks.md es la única memoria persistente del estado real de cada feature. `validate.py` advierte si algún `tasks.md` tiene cero tareas completadas — señal de desincronización entre código y documentación.

### CI = solo validar (bump es local)
El workflow `bump-and-validate.yml` en GitHub Actions solo corre `python3 validate.py`. El bump de versión (`node scripts/bump-version.js`) es responsabilidad del developer local, justo antes de cada push. El auto-bump en CI fue eliminado porque `bump-version.js` fallaba con exit code 1 en el runner de GitHub Actions (causa exacta nunca identificada). El nombre del workflow es histórico — el comportamiento actual es validar-only.

### iOS non-scrollable page bug (patrón conocido)
Cuando el contenido total de la página es menor que el alto del viewport (página sin scroll), iOS calcula `position:fixed;bottom:0` relativo al fondo del documento en lugar del fondo del viewport. El nav principal aparece flotando en el centro de la pantalla. Se corrige con el primer tap del usuario.

**Causa exacta:** Leviza con modo "Hoy" (día específico) muestra 5 items en una pantalla de 844px — el contenido total (~570px) no supera el viewport.

**Fix implementado:** `_fixStickyOffset()` calcula `--min-content-h = window.innerHeight - topbarHeight + 1px` y lo aplica como `min-height` en `#grid`. Esto garantiza que la página siempre tenga al menos 1px de scroll disponible, forzando a iOS a usar el path correcto para `position:fixed`.

**Para debug futuro:** si el nav aparece en posición incorrecta solo en ciertos festivales o días con pocos items, verificar que `--min-content-h` esté siendo calculado correctamente por `_fixStickyOffset()`.

### hdr-fest-bar — Opción A (nombre truncado, fecha fija derecha)
El selector de festival en el topbar usa `text-overflow:ellipsis` en `.hdr-fest-name` con `flex:1;min-width:0;overflow:hidden;white-space:nowrap`. La fecha (`.hdr-fest-dates`) tiene `flex-shrink:0;white-space:nowrap` — nunca wrappea, siempre aparece a la derecha. Si el nombre es muy largo, se trunca con `…`. Esto garantiza 1 sola línea en todos los festivales independientemente del largo del nombre. Opciones B y C (name+date fluyen juntos, o fecha abajo) fueron descartadas por inconsistencia visual.

### Timezone Colombia (UTC-5)
Los festivales colombianos operan en hora local. `toISOString()` devuelve UTC, lo que produce diferencias de fecha silenciosas en lógica de "hoy". Toda comparación de fechas usa offset `-05:00` explícito.

---

## Decisiones pendientes

| Decisión | Opciones | Bloqueante para |
|---|---|---|
| Festival selector en nav | Center tap (wordmark) vs. fila explícita | Nav redesign |
| Desktop layout | Tabs en fila propia vs. en topbar | Desktop layout |
| Separadores de sección en Grid | Detalle visual sutil entre grupos de sección — sin headers de texto, sin filtros. Dirección aprobada: sutil. Diseño pendiente. | Grid legibilidad |

---

## Reglas de proceso — inamovibles

1. **`node scripts/validate-festivals.js` antes de cada push de datos de festival.** Sin excepciones. El CI es el último gate, no el primero.
2. **Múltiples funciones del mismo título en días distintos son datos correctos.** Un duplicado real es mismo título + mismo día + misma hora. Esta distinción debe respetarse en todo script de limpieza, dedup o validación.
3. **Ningún script de limpieza de datos puede correr sin auditoría previa** del resultado: comparar total antes/después y verificar que la diferencia corresponde a duplicados reales, no a funciones adicionales.

## Log de decisiones

| Fecha | Decisión | Rationale |
|---|---|---|
| May 2026 | Eliminar `--orange` como alias de `--amber` | Un solo token para el color primario evita ambigüedad |
| May 2026 | `poster` y `lbSlug` inline en cada film (no en raíz del JSON) | Formato Jardín 2026 en adelante — la fuente de verdad es el objeto film, no lookup tables separadas |
| May 2026 | `config{}` del festival NO va en el JSON | La config vive en `FESTIVAL_CONFIG` de `index.html` — generada por `generate-config.js`, no editada a mano |
| May 2026 | Supabase para auth + cloud sync | Permite sincronización de watchlist entre dispositivos sin backend propio |
| May 2026 | `day` en formato ISO (`YYYY-MM-DD`) desde Tribeca 2026 | Elimina ambigüedad de formato localizado; el validator lo enforcea |
| May 2026 | Grid/TODO ordena por sección (cronológico dentro de cada sección) | Grid es modo de descubrimiento, no de planificación. Ordenar por sección crea clusters visuales coherentes con la identidad editorial del festival. Cronológico ya está cubierto por Lista. |
| May 2026 | Orden de secciones en Grid = orden de primera aparición en `films[]` | El JSON se construye con orden editorial intencional desde Fase 1 del pipeline. Primera aparición = posición en el Grid. Sin configuración extra; el orden vive donde viven los datos. |
