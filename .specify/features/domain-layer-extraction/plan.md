# Plan técnico — Fase 1

## Restricciones de partida

### R1. Single-file en producción
`index.html` es la fuente única que se sirve. No se puede romper el invariante
en esta fase. Toda función nueva vive en `index.html`.

### R2. Web Worker serializa por `.toString()`
`_SCHED_PURE_FNS` lista las funciones que se inyectan al worker. Cualquier
función nueva que el worker necesite debe:
- Estar declarada con `function name(...)` (no arrow ni const) para que
  `.toString()` produzca código serializable y nombrable
- No capturar variables por closure — solo leer parámetros y globals que
  el worker también define
- Añadirse al array `_SCHED_PURE_FNS` (index.html:8234)

### R3. Globals como contrato implícito (decisión tomada)
`screensConflict` lee: `FESTIVAL_BUFFER`, `FESTIVAL_TRANSPORT`, venues activos.
`effectiveDuration` lee: `DEFAULT_DURATION_MIN` (vía parseDur).
Fase 1 NO cambia esto — documenta y cubre con tests que stubean.

## Cambios en index.html

### Inserciones nuevas

**1. `_resolveVenue` — nueva función, scope main**

Ubicación: justo antes de `venueTravelMins` (línea ~4499)
Comportamiento (replicado de la lógica más completa, que está en `vcfg`):
1. Si `venues[name]` existe → retornarlo
2. Ordenar keys por longitud desc, buscar la primera que:
   `name.startsWith(k) || name.includes(k) || nameLower.startsWith(kLower) || nameLower.includes(kLower)`
3. Si matchea → retornar `venues[k]`
4. Fallback → retornar `{ short: name }`

Nota: hoy `venueTravelMins.findCoords` solo hace exacto + prefix
case-sensitive. `vcfg` hace exacto + prefix/includes case-insensitive.
Unificamos al comportamiento más permisivo (el de vcfg) — verificar
manualmente que no produce matches incorrectos en festivales actuales.

**2. Bloques de comentario de contrato**

Encima de `effectiveDuration`, `screensConflict` y `_resolveVenue`:
- Qué globals lee
- Por qué es "pura" en el sentido del worker
- Qué se asume del entorno (timezone, buffer mínimo, transport mode)

**3. `_resolveVenue` añadida a `_SCHED_PURE_FNS`** (line 8234)

### Reemplazos

- `venueTravelMins` líneas 4505-4511: el bloque `const findCoords=v=>{...}; c1=findCoords(v1); c2=findCoords(v2);` → `const c1=_resolveVenue(v1, festVenues); const c2=_resolveVenue(v2, festVenues);`
  - El fallback `{short: v}` es distinto del fallback `null` que necesita aquí para `return 0`. Manejamos con guard: `if(!c1.lat||!c2.lat) return 0;`
- `vcfg` líneas 4523-4534: el cuerpo entero → `return _resolveVenue(v, festVenues);`
- `_workerFindCoords` líneas 8257-8263: el cuerpo entero → `return _resolveVenue(v, _venueCoords);`

### Sin cambios

- Firma de `screensConflict(a, b)`
- Firma de `effectiveDuration(f)`
- Ningún callsite de ninguna función
- Render functions
- Worker setup

## Tests — diseño

### Estructura

```
tests/
  lib/
    load-domain.js     ← extrae funciones de index.html, devuelve sandbox
  unit/
    effectiveDuration.test.js
    screensConflict.test.js
    resolveVenue.test.js
```

### `tests/lib/load-domain.js` — mecanismo

1. `fs.readFileSync('index.html', 'utf8')`
2. Concatenar todos los bloques `<script>...</script>` con regex
   (mismo patrón usado en el pre-push check del SCHEMA)
3. Para cada función pedida, extraer la declaración por nombre vía regex
   `function ${name}\s*\([^)]*\)\s*\{...\}` con balance de braces
4. Construir un módulo Node sintético:
   ```js
   module.exports = function load({globals = {}}) {
     const sandbox = {...globals};
     // eval functions en este scope
     return {effectiveDuration, screensConflict, _resolveVenue, parseDur, toMin, ...};
   };
   ```
5. Cada test invoca `load({globals: {FESTIVAL_BUFFER: 10, FESTIVAL_TRANSPORT: 'transit', ...}})` y testea contra esa instancia

Alternativa más robusta si la regex falla: usar `acorn` (cero deps si
está en stdlib? no — habría que añadirlo). Empezamos con regex y migramos
solo si el extractor se rompe.

### Casos cubiertos (mínimo)

`effectiveDuration`:
- `{duration: "90 min"}` → 90
- `{duration: "90 min", has_qa: true}` → 120
- `{duration: null}` → DEFAULT_DURATION_MIN
- `{duration: "~95 min"}` → 95
- `null` o `undefined` → DEFAULT_DURATION_MIN

`screensConflict`:
- a.day !== b.day → false
- mismo día, solapamiento directo → true
- gap > buffer y venues iguales → false
- gap < buffer → true
- gap > buffer pero < travel+buffer entre venues distantes → true
- a tiene has_qa, b empieza 20 min después → true (Q&A extiende)
- Orden invertido (b antes que a) → mismo resultado

`_resolveVenue`:
- Match exacto
- Match por prefix case-sensitive
- Match por substring case-insensitive
- venues con keys más largas precede a más cortas
- venues vacío → {short: name}
- name vacío → {short: ''}

## CI

`.github/workflows/bump-and-validate.yml` añade paso:

```yaml
- name: Unit tests dominio
  run: node --test tests/unit/*.test.js
```

Node 18+ tiene `node:test` y `node:assert` en stdlib — cero npm install.
Glob explícito (no `tests/unit/`): Node 22 trata el dir suelto como module path y falla con `MODULE_NOT_FOUND`. El glob lo expande bash antes de invocar a node, lo cual es portable entre Node 20 (CI) y Node 22 (local).

## Riesgos

| Riesgo | Mitigación |
|---|---|
| `_resolveVenue` con comportamiento más permisivo (de vcfg) produce match incorrecto que `venueTravelMins` no hacía antes | Inspeccionar manualmente venues de los 5 festivales en FESTIVAL_CONFIG, confirmar que no hay nombre de venue que matchee por substring case-insensitive un venue distinto. Si lo hay, mantener firmas separadas. |
| Loader regex de tests falla si el formateo del archivo cambia (one-liners, etc.) | Loader es código de tests, no de prod. Si rompe, los tests rompen ruidosamente. No es riesgo para usuarios. |
| Worker rompe porque `_resolveVenue` no se inyecta correctamente | Smoke test: abrir Planear y verificar que rendera el schedule. Paso explícito en el QA browser de spec.md. |
| Cambio de comportamiento sutil entre la copia inline de `venueTravelMins` (solo prefix) y la unificada (prefix + includes case-insensitive) afecta cálculo de travel time | Antes del commit final: comparar `travelMins` outputs en pares conocidos de venues (FICCI, Tribeca) con un snapshot manual. |

## Deuda futura

- Check en `validate.py` que detecte ambigüedad estática en `venues{}` por festival (una key matchea otra bajo prefix/includes case-insensitive). Auditoría manual de los 5 festivales actuales: clean. Útil como red de seguridad para festivales futuros con nombres de sala que se solapen.
