# Spec — File Split / ES Modules nativos (Fase 8)

## Problema

`index.html` tiene ~12,266 líneas con toda la app en 4 bloques `<script>` (el
grande: L2754–11697, ~9000 líneas). Mantenibilidad limitada: navegar, revisar,
y razonar sobre fronteras de responsabilidad cuesta. El refactor 5.5→7d dejó la
arquitectura limpia (MVC, event delegation, render pipeline) PERO sigue en un
archivo.

Fase 8 separa el código en módulos ES nativos (`src/*.js`), rompiendo
deliberadamente el invariante single-file. Es **relocación + import/export**, NO
cambio de comportamiento.

## Prerequisitos (TODOS resueltos)

- ✅ **Decisiones D-INFRA-1 a 5** cerradas (`docs/FASE8-INFRA.md §8`)
- ✅ **DAG verificado acíclico** (`docs/FASE8-INFRA.md §12`)
- ✅ **Orden topológico** definido (§12)

## Decisiones de infraestructura (de FASE8-INFRA.md, ya cerradas)

| # | Decisión | Aplicación en Fase 8 |
|---|---|---|
| D-INFRA-1=B | SW network-first para `/src/` | `sw.js` sirve `/src/*.js` con `no-store` + fallback offline |
| D-INFRA-2=Camino 1 | ESM nativo multi-file | Sin bundler. Deploy = copiar `src/` + index.html |
| D-INFRA-3 | QA device obligatorio | iOS + Android antes de promover nativo |
| D-INFRA-4 | Eliminar mirror de globals | state container fuente única; se eliminan `let` globals + `_MIRROR_*` |
| D-INFRA-5 | Tests por import directo | módulos `export`; `load-domain.js` + sandbox `extractStateBlock` reemplazados por `import` |

## Solución — extracción incremental en orden topológico

8 waves, cada una extrae una capa cuando sus dependencias ya son módulos. Tras
cada wave: `validate.py` + unit tests + Playwright verde antes de la siguiente.

```
Wave 1: config     → (leaf)
Wave 2: domain     → config
Wave 3: state      → config            [elimina mirror D-INFRA-4]
Wave 4: storage    → state, config
Wave 5: i18n       → state, config
Wave 6: view       → domain, state, i18n, config
Wave 7: controller → view, state, domain, storage, i18n
Wave 8: main       → todo (bootstrap)
```

### Estructura objetivo (de FASE8-INFRA.md §6)

```
index.html               # shell + <script type="module" src="/src/main.js">
sw.js                    # + regla network-first /src/
src/
├── main.js              # entry/bootstrap
├── config.js            # FESTIVAL_CONFIG, constants, BUILD_VERSION
├── state/state.js       # container (subscribe, subscribeRender, transaction)
├── storage/storage.js   # localStorage adapter
├── domain/{schedule,time,film,festival}.js   # funciones puras
├── i18n/i18n.js         # t(), _applyI18nDOM
├── view/{programa,agenda,miplan,sheets,components}.js
└── controller/{registry,pipeline,handlers}.js   # + renderActiveView, runCalc
```

### Mecanismo de cada wave
1. Crear el/los archivo(s) `src/<capa>/*.js`.
2. **Mover** (cut) las funciones/consts de esa capa desde index.html → módulo.
3. Añadir `export` a lo que otras capas consumen.
4. Añadir `import` de las dependencias (ya extraídas en waves previas).
5. En index.html, el código restante referencia la capa extraída vía import
   (o, hasta Wave 8, vía un puente temporal — ver "Coexistencia" abajo).
6. Validar + tests + Playwright.

### Coexistencia durante el split (el reto de las waves intermedias)

Entre waves, parte del código vive en módulos y parte en index.html inline. El
código inline de index.html debe poder REFERENCIAR los módulos ya extraídos.
Dos enfoques:

**Opción A — Bridge global temporal**: cada módulo extraído expone sus exports
en `window` (`window.computeScenarios = computeScenarios`) para que el inline
legacy los siga viendo como globals. Se eliminan los bridges en Wave 8 cuando
todo es módulo. Pragmático, permite waves verdaderamente incrementales.

**Opción B — index.html como módulo desde Wave 1**: convertir el `<script>`
grande en `<script type="module">` desde el inicio, e ir moviendo + importando.
Más limpio pero el bloque inline grande como módulo único puede tener problemas
de orden (hoisting de function declarations en módulos funciona, pero el orden
de ejecución top-level cambia).

**Decisión D8-1 (pendiente)**: A (bridge) vs B (módulo desde wave 1). Ver
"Decisiones pendientes".

## Infraestructura tocada (de FASE8-INFRA.md §4)

| Archivo | Cambio |
|---|---|
| `sw.js` | + regla network-first `/src/` (Wave final o cuando aparezca el primer módulo) |
| `tests/lib/load-domain.js` | Reemplazar string-walking por re-export desde módulos (D-INFRA-5) |
| `tests/unit/state.test.js` | `import` directo del container (elimina sandbox de 19 globals) |
| `tests/unit/*.test.js` (22 domain) | `import` desde `src/domain/*.js` |
| `validate.py` | Checks leen `src/**/*.js` (glob) en vez de index.html single-file |
| `playwright.yml` | paths filter + `src/**` |
| `bundle.yml` | + `cp -r src/. www/src/` |
| `bump-version.js` | Sin cambio (D-INFRA-1=B no usa hash) |

## R2' (functional equivalence)

Fase 8 NO cambia comportamiento — mueve código. Verificación por wave:
1. **Functional equivalence**: la app se comporta idéntico tras cada wave.
2. **validate.py**: adaptado a multi-file, sigue 26/26 (o el count post-adaptación).
3. **Unit tests**: 141 (migrados a import directo), siguen verde.
4. **Playwright T01-T10 + T32**: verde tras cada wave.
5. **QA Boot Path**: 0 errors.
6. **QA device** (D-INFRA-3): iOS + Android antes de promover nativo.

## Lo que NO cambia

- `festivals/*.json`, `i18n/*.json`, `assets/`, `version.json`, `manifest.json`,
  `CNAME`, `.nojekyll`.
- La LÓGICA de la app — solo se mueve.
- Capgo OTA — el bundle ahora incluye `src/`.

## Riesgo

Mayor superficie del roadmap. Ejecutar **post-Tribeca** (decisión confirmada).
Mitigación: waves incrementales + validación por capa + el DAG acíclico
garantiza que cada import resuelve sin ciclos.

## Definition of Done

- [ ] 8 waves completas: config, domain, state, storage, i18n, view, controller, main
- [ ] `index.html` reducido a shell (head, divs críticos, `<script type="module">`)
- [ ] Mirror de globals eliminado (D-INFRA-4); state container fuente única
- [ ] `sw.js` con regla network-first `/src/`
- [ ] Test infra migrada a import directo (D-INFRA-5): 141 tests verde
- [ ] `validate.py` adaptado a multi-file; checks pasan
- [ ] `playwright.yml` + `bundle.yml` actualizados con `src/`
- [ ] Playwright T01-T10 + T32 verde
- [ ] QA Boot Path 0 errors
- [ ] QA device iOS + Android (D-INFRA-3) antes de promover nativo
- [ ] Cero cambios de comportamiento (functional equivalence por wave)

## Decisiones cerradas (aprobadas pre-código)

| # | Decisión | Resolución |
|---|---|---|
| **D8-1** | Coexistencia en waves intermedias | ✅ **A — Bridge global temporal** (`Object.defineProperty` / `window.*`). Única forma de waves verdaderamente incrementales sin big-bang. Limpieza en Wave 8. |
| **D8-2** | Migración de test infra | ✅ **Por wave** — cada wave migra sus propios tests al extraer (domain wave → 22 domain tests, etc.). Coherente con el patrón de fases acotadas. |
| **D8-3** | Granularidad view/controller | ✅ **Sub-split, evaluar al llegar** — no especular tamaño ahora; decidir el sub-split en Wave 6/7 según tamaño real. |
| **Worker (R3)** | Acceso del worker a domain | ✅ **Decidir en Wave 2** — module worker si el entorno lo soporta, copia worker-local si no. No bloquea el spec. |

**Estado**: todas las decisiones cerradas. Fase 8 ejecutable post-Tribeca.
NO se arranca ejecución hasta post-festival.
