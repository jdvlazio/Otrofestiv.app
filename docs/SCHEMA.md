# Otrofestiv — Festival Data Schema

Documento normativo. Toda discrepancia entre este archivo y el código es un bug.
Última actualización: 2026-05-07 — commit 1f6f290

---

## Estructura raíz del JSON

```json
{
  "_status": "string — descripción del estado del archivo",
  "_source": "string — URL o descripción de la fuente",
  "_extracted": "string — fecha de extracción ISO",
  "_total": "number — total de films",
  "config": null,
  "transport": "string — 'transit' | 'driving' | 'walking'",
  "venues": { ... },
  "posters": { ... },
  "customPosters": { ... },
  "lbSlugs": { ... },
  "prioLimit": 5,
  "ticket_url": "string — URL https:// de entradas (opcional)",
  "ticketing_model": "string — 'paid' | 'mixed' (obligatorio si ticket_url existe)",
  "films": [ ... ]
}
```

**Nota formato:** Los festivales desde Jardín 2026 no incluyen `config{}` en el JSON — la configuración vive en `FESTIVAL_CONFIG` de `index.html`. Los festivales legacy (FICCI 65, Cinemancia 2025) sí incluyen `config{}`.

**Ticketing (campos opcionales del root):**
- `ticket_url` — URL `https://` de la página oficial de entradas. Si existe, el sheet de función muestra un bloque con link (oculto cuando `festivalEnded()`). Ausencia de `ticket_url` = festival gratuito (no muestra nada).
- `ticketing_model` — `"paid"` (todo pago, ej. Tribeca → link "Comprá tu entrada →") o `"mixed"` (pago + gratis, ej. Olhar → meta-banner "Funciones pagas y gratuitas"). **Obligatorio si `ticket_url` existe.**
- En festivales `"mixed"`, marcar funciones gratuitas con `is_free: true` por screening (ver Screenings). El card muestra badge "GRATIS"; el sheet oculta el bloque solo si **todas** las funciones del film son gratuitas.
- Ambos campos se absorben vía el whitelist `_cfgFields` en `loader.js` — un campo root nuevo que no esté ahí se descarta en silencio.

---

## Venues

```json
"venues": {
  "Nombre completo del venue": {
    "short": "Nombre corto para el card (≤ 20 chars)",
    "address": "Dirección completa",
    "lat": 0.0,
    "lng": 0.0
  }
}
```

**Reglas:**
- La clave ES el nombre completo — sin abreviaciones
- `short` es lo que ve el usuario en el card
- Coordenadas requeridas para la vista de mapa
- Los nombres de venue en `film.venue` y `film.screenings[].venue` deben ser claves exactas de este objeto

---

## Films

```json
{
  "title": "string — requerido",
  "slug": "string — requerido para Tribeca/festivales con URL propia",
  "section": "string — requerido",
  "type": "string — 'film' | 'event' | 'short'",
  "filmType": "string — descripción textual del tipo (de la fuente)",
  "director": "string",
  "duration": "number — minutos",
  "country": "string",
  "language": "string",
  "premiere": "string — 'World Premiere' | 'International Premiere' | ...",
  "synopsis": "string",
  "poster": "string — URL completa (https://...), path de assets (/assets/<id>/x.png) o path TMDB (/x.jpg). Prioridad, cobertura y reglas: docs/POSTERS.md",
  "posterPosition": "string — 'center' | 'top' | 'bottom' (default: 'center')",
  "genre": "string",
  "year": "number",
  "flags": "string — emojis de banderas de países",
  "day": "string — KEY del dayKeys del festival (REQUERIDO para filtrado)",
  "date": "string — ISO date '2026-06-03' (requerido si screenings[] existe)",
  "time": "string — '10:30 AM' formato 12h",
  "venue": "string — debe ser clave exacta de venues{}",
  "info": "boolean — opcional, SOLO type:event — evento informativo (ver abajo)",
  "screenings": [ ... ]
}
```

### Campo `info` — eventos informativos (no planificables)

`info: true` (solo en `type:'event'`) marca un evento **drop-in / sin hora fija**
cuya duración no es controlable: exposiciones, visitas guiadas, recorridos,
fiestas, conciertos, performances, presentaciones virtuales.

- **Aparece en el programa** como cualquier evento, pero **NO entra al plan ni a
  conflictos:** `screensConflict` lo ignora y `computeScenarios` lo excluye del
  plan generado (ambos en `domain/schedule.js`, guard aditivo por `f.info`).
- **El default es planificar.** La app es un **planificador**, no un tablón
  informativo — `info` es la **excepción mínima**. Un evento con hora fija
  (masterclass, conversatorio, panel, gala, bloque de cortos) NO lleva `info`:
  lleva `duration` (estimada si hace falta) y SÍ se planifica.
- Regla de clasificación al montar: *¿el asistente "reserva" ese horario?* Sí →
  `duration` (planificable). No (entra/sale cuando quiere) → `info: true`.
- `info` se propaga a los screenings exploded vía el `Object.assign` del loader.

### Campo `day` — regla crítica

`day` debe ser una clave exacta de `FESTIVAL_CONFIG[id].dayKeys`.

- **Formato legacy** (FICCI, AFF): `day` = key legible, e.g. `"MAR 21"`, `"VIE 24"`
- **Formato ISO** (Tribeca, Jardín): `day` = ISO date, e.g. `"2026-06-03"`

Cuando el film tiene `screenings[]`, el campo `day` del film raíz se toma del primer screening.

**El validator falla si `day` no está en `dayKeys`.**

---

## Screenings (array por función)

Usado cuando un film tiene múltiples funciones en días/horarios/venues distintos.

```json
"screenings": [
  {
    "date": "string — ISO date '2026-06-03' (requerido)",
    "day": "string — KEY del dayKeys (opcional, se deriva de date si falta)",
    "time": "string — '10:30 AM'",
    "venue": "string — clave exacta de venues{}",
    "is_free": "boolean — opcional, solo festivales 'mixed': marca función gratuita"
  }
]
```

`is_free` se absorbe en la explosión de screenings (whitelist en `loader.js`). Solo aplica a festivales con `ticketing_model: "mixed"`.

**Regla de explosión:** el sistema convierte `screenings[]` en objetos film planos usando:
```javascript
day: s.day || s.date   // ← CRÍTICO: siempre usar ambos por compatibilidad
date: s.date || s.day
```

**Si solo existe `date` (sin `day`), el sistema lo normaliza automáticamente.**
El validator debe advertir si ninguno de los dos existe.

---

## FESTIVAL_CONFIG en index.html

Campos requeridos por festival:

```javascript
{
  name: 'Nombre completo',
  shortName: 'ABREVIACIÓN',
  city: 'Ciudad',
  dates: 'FEB 3–14',        // ES
  dates_en: 'FEB 3–14',     // EN
  year: 2026,
  timezoneOffset: '-05:00',
  storageKey: 'id_',
  festivalEndStr: '2026-02-14T23:59:00',
  festivalDates: { dayKey: isoDate },
  days: [{ k: dayKey, d: dayNumber, lbl: 'LUN' }],
  dayKeys: ['key1', 'key2', ...],
  dayShort: { dayKey: 'LUN 3' },
  dayShort_en: { dayKey: 'MON 3' },
  dayLong: { dayKey: 'Lunes 3 de febrero' },
  eventPosterLabel: ['LABEL1', 'LABEL2'],
  films: null,
  posters: null,
  lbSlugs: {}
}
```

**`dayKeys` deben coincidir exactamente con los valores de `film.day` en el JSON.**

---

## i18n — Reglas

- Toda string visible al usuario debe usar `t('key')`
- **Prohibido:** strings hardcodeadas en ES o EN dentro de templates HTML en `index.html`
- Excepción: nombres propios, nombres de festival, títulos de film
- Toda clave nueva debe añadirse a AMBOS archivos (`es.json` y `en.json`) en el mismo commit
- El validator compara keys de `en.json` vs `es.json` — deben ser idénticas

---

## Pre-push checklist (obligatorio para cambios en index.html)

```
[ ] node scripts/validate-festivals.js → 0 errores
[ ] VERIFICACIÓN DE SINTAXIS JS (obligatorio, <1 segundo):
    node -e "const h=require('fs').readFileSync('index.html','utf8');[...h.matchAll(/<script>([\s\S]*?)<\/script>/g)].forEach((m,i)=>{try{new Function(m[1]);console.log('Script',i,'OK')}catch(e){console.error('Script',i,'ERROR:',e.message);process.exit(1)}})"
[ ] Diff review completo — no solo el fragmento modificado
[ ] Smoke test en browser:
    [ ] Splash carga con festival correcto como default
    [ ] Grilla Programa muestra films y posters
    [ ] Sheet de un film: día visible (no UNDEFINED), venue, hora
    [ ] Tab Intereses: carga sin error de consola
    [ ] Consola: 0 errores nuevos
[ ] str_replace verificado: leer las líneas modificadas con sed antes de commitear
```

---

## Regla de onboarding de festival nuevo

**Esta regla es la más importante del documento.**

Cuando se monta un festival nuevo, el trabajo es:

1. Copiar la estructura de datos del festival más reciente
2. Replicar exactamente el mismo pipeline: extracción → enrichment → FESTIVAL_CONFIG
3. No modificar ningún componente visual existente
4. No proponer mejoras visuales durante el onboarding
5. Si el festival nuevo tiene algo que los anteriores no tienen (ej: imagen editorial 16:9), se para, se hace un mockup, se presenta, se espera aprobación explícita antes de tocar código

**Lo que no es aceptable:**
- Modificar `makeFilmPlaceholder`, `makeEventPoster`, `makeProgramPoster`, `_buildPosterV16` durante el onboarding de un festival
- Añadir componentes visuales (badges, overlays, nuevos tipos de card) sin aprobación
- Cambiar proporciones, colores o tipografía de componentes existentes
- "Mejorar" algo que no se pidió mejorar

**La pregunta antes de cada cambio:**
¿Me pidieron esto explícitamente? Si la respuesta no es "sí", no se hace.



### Arquitectura

**ARCH-R1 — Una función, una definición en el scope del main thread.**
Las funciones duplicadas en `index.html` son del Web Worker (scope separado, legítimo). No eliminar.

**ARCH-R2 — Detección de poster editorial.**
Usar `_isEditorialPoster(f)` en todo el código. Esta función lee `f.posterSource` primero.
Nuevos festivales **deberían** incluir `posterSource: 'editorial'` cuando la imagen es editorial.
Estado real y deuda (hoy la detección operativa es por host vía `_isEditorialImageUrl`; `posterSource` está sin adoptar): ver `docs/POSTERS.md §5`.

**ARCH-R3 — Constantes de módulo, no locales.**
`SECTION_COLORS`, `SECTION_ORDER_LIST`, `_sectionColor()`, `_secLabel()`, `_isEditorialPoster()` viven al nivel de módulo, antes de `_buildPosterV16`. No redefinir dentro de funciones.

**ARCH-R4 — Cero `console.log` en producción.**
Usar `if(DEBUG)console.log(...)` o eliminarlo. El flag `DEBUG` se activa solo en desarrollo.

---

### Componentes

**COMP-R1 — Sheet compacto con 3+ funciones.**
`openPelSheet` añade clase `.compact` cuando `totalFn >= 3`. El CSS reduce el poster de 96→72px.
Regla: el CTA primario debe ser visible sin scroll en el primer viewport.

**COMP-R2 — `_secLabel(sec)` en todos los contextos.**
Nunca usar `.replace(/^\S+ /, '')` ni `.replace(/^[^ ]+ /, '')` para limpiar nombres de sección.
Usar `_secLabel(sec)` — solo elimina prefijo emoji, preserva palabras como "U.S.", "Free", "Escape".

**COMP-R3 — Scroll en sheets.**
Toda función que abre el sheet hace `document.getElementById('pel-sheet').scrollTop = 0`.
Toda función que abre el sheet añade `-webkit-overflow-scrolling: touch` al contenedor.

---

### Visual

**VIS-R1 — Tres tipos de card, tratamiento visual distinto:**
1. TMDB: imagen pura 2:3, sin intervención, sin sólido de sección.
2. Editorial (cloudfront): sólido de sección 52px + imagen 16:9 + título anclado abajo.
3. Generativo (sin imagen): sólido de sección 52px + caja oscura + título. Sin texto "NO POSTER".

**VIS-R2 — `makeFilmPlaceholder` siempre recibe `section`.**
Firma: `makeFilmPlaceholder(title, director, year, section)`.
El header usa `_sectionColor(section)`. Si no hay `section`, color fallback `#2C2C2A`.

**VIS-R3 — Grilla con affordance de scroll.**
`poster-grid` tiene `padding-right: 20px` para que la cuarta columna asome.

---

### Copy e i18n

**COPY-R1 — El campo `synopsis` en el JSON no contiene metadatos de proceso.**
Nunca guardar `⚠️ INGLÉS —` u otros prefijos en el dato. El dato es el dato.

**COPY-R2 — Toda string visible al usuario pasa por `t()`.**
Sin excepciones en templates. Incluye: Q&A labels, registro, premieres, empty states.

**COPY-R3 — `premiere` se muestra tal cual, sin `.toUpperCase()`.**
El valor en el JSON ya viene en el case correcto desde la fuente.

**COPY-R4 — Paridad ES/EN obligatoria.**
Toda key nueva se añade a `es.json` Y `en.json` en el mismo commit.
El validator (RULE 9) bloquea el push si hay desalineación.

---

### Mobile

**MOB-R1 — `-webkit-overflow-scrolling: touch` en todo scroll container.**
`.pel-sheet`, `.prio-strip-row`, `.hscroll-strip`, `.mplan-wk-outer`, `.ag-excl-strip`.

**MOB-R2 — Tap targets mínimo 44px.**
Botones de acción: `min-height: 44px`. Si el visual es más pequeño, usar `padding` para expandir el área táctil sin cambiar el tamaño visual.

---

### Deuda técnica registrada (no bloqueante)

- 13 inline onclick handlers con >40 chars — deben migrar a funciones nombradas
- FICCI/AFF/Cinemancia tienen `config{}` en el JSON (formato legacy) — no afecta runtime
- Cinemancia2025 en FESTIVAL_CONFIG falta `dayShort`/`dayShort_en`/`dayLong`
- Detección por URL en `_isEditorialPoster` como fallback — migrar a `posterSource` en todos los festivales



| Error | Causa | Fix |
|---|---|---|
| `SyntaxError: Unexpected token '?'` | `str_replace` eliminó código adyacente | Verificar diff post-reemplazo |
| `renderSbar is not defined` | Función eliminada en refactor, llamada no eliminada | Inventario de funciones antes de borrar |
| `UNDEFINED` en día del sheet | `s.day` undefined en screenings con formato ISO | `s.day \|\| s.date` en la explosión |
| Strings hardcodeadas ES en festival EN | Templates con strings literales en vez de `t()` | Toda string de UI pasa por `t()` |
