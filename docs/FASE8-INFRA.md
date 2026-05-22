# Fase 8 — Análisis de Infraestructura (File Split / ES Modules nativos)

> **Estado**: análisis completo. Las 5 decisiones D-INFRA están **cerradas**
> (§8). NO se ha tocado código de la app.
> **Objetivo**: dejar lista la transición de infraestructura para ejecutar
> Fase 8 (split de `index.html` en módulos ES nativos) inmediatamente
> post-Tribeca, sin sorpresas.
> **Fecha**: post-7d. Fase 8 NO se ejecuta antes de Tribeca (cambia el deploy
> — riesgo operativo).
> **Único bloqueante restante**: mapa de dependencias (DAG) — §11.
>
> **Decisiones cerradas**: D-INFRA-1=B (SW network-first /src/) ·
> D-INFRA-2=Camino 1 (ESM nativo, sin bundler) · D-INFRA-3=QA device obligatorio ·
> D-INFRA-4=eliminar mirror de globals · D-INFRA-5=tests por import directo.

---

## 0. Por qué Fase 8 rompe el invariante single-file (a propósito)

Todas las fases 5.5 → 7d mantuvieron `index.html` como archivo único. Fase 8
lo rompe deliberadamente: separa las ~12,266 líneas en módulos. El beneficio
(maintainability, módulos testeables, ownership claro por dominio) es real,
pero **cambia el deploy** — de drag-and-drop de un archivo a servir/empaquetar
múltiples. Este documento mapea cada pieza de infraestructura afectada.

### Estado actual (baseline)

| Pieza | Estado |
|---|---|
| `index.html` | 12,266 líneas, 4 bloques `<script>` (el grande: L2754–11697, ~9000 líneas) |
| Deploy web | Drag-and-drop manual de `index.html` al repo (GitHub web UI) |
| Deploy nativo | `bundle.yml` → `www/` → `bundle.zip` → Capgo live-update |
| GitHub Pages | Sirve repo root directo. `.nojekyll` presente (sin transformación). `CNAME` = otrofestiv.app |
| Service Worker | `sw.js` — HTML network-first (no-store), i18n cache-first, festivals network, assets cache-first |
| Capacitor | `server.url = https://otrofestiv.app` (carga producción) + Capgo bundle para updates OTA |
| CI validate | `bump-and-validate.yml`: `validate.py` + `node --test tests/unit/*.test.js` |
| CI Playwright | `playwright.yml`: paths filter en `index.html`. Server: `python3 -m http.server 3000` |
| CI bundle | `bundle.yml`: estampa `BUILD_VERSION` con sed, copia archivos a `www/`, zip, release |
| Tests unit | `tests/lib/load-domain.js` extrae funciones de los `<script>` de `index.html` |
| version cache-bust | `BUILD_VERSION` en index.html + `CACHE_NAME` en sw.js, bumpeados por `bump-version.js` |

---

## 1. EL RETO CENTRAL — Service Worker + cache-bust de módulos JS

Este es el problema más difícil de Fase 8 y debe resolverse ANTES de tocar
nada.

### El invariante actual que se rompe

El SW (`sw.js`) está diseñado así:
- **HTML → siempre desde red** (`cache: 'no-store'`). Garantiza que un deploy
  toma efecto inmediatamente: el nuevo HTML se sirve al instante.
- **Assets estáticos → cache-first** (catch-all final del `fetch` handler).

Hoy todo el JS vive INLINE en `index.html` → viaja con el HTML → se actualiza
inmediatamente en cada deploy.

**Con módulos ES nativos**, el HTML hace:
```html
<script type="module" src="/src/main.js"></script>
```
Y `main.js` importa `state.js`, `view.js`, etc. Estos `.js` tienen
`request.destination === 'script'` → caen en el catch-all **cache-first** del
SW → **JS stale tras un deploy**. El nuevo HTML carga, pero jala los módulos
viejos del caché. Se rompe el invariante "deploy toma efecto inmediato".

### Opciones de cache-bust (decisión D-INFRA-1)

**Opción A — Filenames con content-hash** (`state.a3f9.js`)
- Cada build genera nombres nuevos según hash del contenido. El HTML referencia
  los nombres nuevos. Los viejos quedan huérfanos (se limpian al borrar caché).
- **Requiere build step** (bundler/hasher). Rompe el "no build, drag-and-drop".
- Estándar de la industria. SW cache-first funciona perfecto (filename nuevo =
  cache miss = red).

**Opción B — SW network-first para `/src/`** (Recommended para ESM nativo)
- Cambiar el SW: módulos bajo `/src/` se sirven network-first (igual que HTML),
  con fallback a caché offline.
- **Sin build step.** Coherente con la filosofía existente ("HTML network-first
  porque la frescura importa más que el offline para el código"). El comentario
  del SW v15 ya muestra que priorizan frescura.
- Costo: una request de red por módulo en cada load (mitigable con
  stale-while-revalidate: servir caché + revalidar en background, pero eso
  reintroduce staleness de 1 ciclo).
- Con HTTP/2 (GitHub Pages lo soporta) las N requests se multiplexan — costo
  aceptable para ~10-15 módulos.

**Opción C — Query-string cache-bust** (`main.js?v=BUILD`)
- El HTML estampa `?v=${BUILD}` en el entry. SW cachea por URL completa (incl.
  query) → query nueva = cache miss.
- **Problema**: los `import` estáticos de ESM no pueden usar query dinámica
  fácilmente (`import './state.js'` es estático). Habría que usar un **import
  map** que remapee `state.js` → `state.js?v=BUILD`, estampado en el HTML.
  Funciona pero el import map debe cubrir TODOS los módulos.

### Recomendación D-INFRA-1: **Opción B** (SW network-first para `/src/`)

Razones:
1. Preserva el "no build step / drag-and-drop" — el deploy sigue siendo copiar
   archivos.
2. Coherente con la filosofía del SW actual (frescura > offline para código).
3. Sin la complejidad del import map versionado (Opción C) ni el build (A).
4. El `BUILD_VERSION` + `CACHE_NAME` existentes siguen sirviendo para el bump
   del SW; los módulos se revalidan por red.

Cambio concreto en `sw.js` (a implementar en Fase 8, no ahora):
```js
// Módulos de la app → network-first (igual que HTML): el deploy debe propagar
if (url.pathname.startsWith('/src/')) {
  event.respondWith(
    fetch(new Request(request, { cache: 'no-store' }))
      .catch(() => caches.match(request))   // fallback offline
  );
  return;
}
```

**Alternativa si se prioriza offline/perf**: Opción A (build con hash). Esto
convertiría Fase 8 en "split source + bundle artifact" — ver §6.

---

## 2. Bundling strategy

### La pregunta estratégica: ¿el deploy ships multi-file o bundle?

El GOAL de Fase 8 (split para mantenibilidad) NO obliga a que el ARTEFACTO de
deploy sea multi-file. Hay dos caminos:

**Camino 1 — ESM nativo multi-file en producción** (lo que pidió el equipo)
- Source split en `src/*.js`, servidos tal cual. Browser carga ESM nativo.
- Sin bundler. Deploy = copiar `src/` + index.html.
- Requiere resolver el SW (D-INFRA-1 = B) + reescribir test/validate infra (§4).

**Camino 2 — Split source + bundle a artefacto único**
- Source split en `src/*.js` (dev). Un build step (esbuild) los bundlea de
  vuelta a un `index.html` inline (o `bundle.js`).
- El deploy/SW/tests quedan CASI sin cambios (artefacto sigue siendo ~1 archivo).
- "Single-file invariant" se vuelve "single-file ARTIFACT, multi-file source".

| Dimensión | Camino 1 (ESM nativo) | Camino 2 (bundle) |
|---|---|---|
| Build step | No | Sí (esbuild ~50ms) |
| Deploy | Copiar src/ + index.html | Build → drag dist/index.html |
| SW changes | Sí (D-INFRA-1) | Mínimos |
| Test/validate infra | Reescribir (§4) | Casi sin cambios (apuntar a src/) |
| Dev experience | Editar módulo, refresh | Editar módulo, rebuild, refresh |
| Debug en prod | Módulos legibles en DevTools | Necesita sourcemaps |
| Riesgo | Alto (toca todo) | Medio (build step nuevo) |

### Recomendación D-INFRA-2

El equipo pidió **ESM nativo** (Camino 1). Lo respeto, pero el doc debe
registrar honestamente: **Camino 2 de-riesga significativamente** (deploy + SW +
tests casi intactos). Si el apetito de riesgo post-Tribeca es bajo, Camino 2 con
esbuild es defendible.

Si se confirma Camino 1 (ESM nativo): NO se introduce bundler. Para optimización
futura (si el waterfall de imports importa), se puede añadir `<link
rel="modulepreload">` para los módulos críticos — sin bundler, solo hints.

**Decisión a tomar con Juan antes de Fase 8**: ¿Camino 1 o 2? El resto de este
doc asume **Camino 1** (ESM nativo) por el framing del equipo, marcando dónde
Camino 2 simplificaría.

---

## 3. GitHub Pages multi-file

GitHub Pages sirve el repo root estáticamente. Implicaciones para multi-file:

### Lo que ya funciona
- **`.nojekyll`** presente → GH Pages NO corre Jekyll → sirve `src/*.js` tal
  cual, sin transformación. ✓
- **MIME types**: GH Pages sirve `.js` como `application/javascript` (o
  `text/javascript`) — correcto para `<script type="module">`. ✓ (ESM exige
  MIME JS válido; un MIME incorrecto bloquea el módulo.)
- **HTTP/2**: GH Pages lo soporta → requests de módulos multiplexadas. ✓
- **HTTPS + same-origin**: módulos servidos desde `otrofestiv.app` → mismo
  origen → sin problemas de CORS para `import`. ✓

### Lo que hay que vigilar
- **Cache headers de GH Pages**: GH Pages aplica `Cache-Control: max-age=600`
  (10 min) a los assets. Esto interactúa con el SW: aunque el SW haga
  network-first, el browser puede servir el `.js` desde su HTTP cache (10 min)
  antes de llegar al SW. Mitigación: el SW usa `cache: 'no-store'` en el fetch
  (D-INFRA-1 opción B ya lo incluye) → bypassa el HTTP cache del browser.
- **Paths absolutos vs relativos**: usar paths absolutos desde root
  (`/src/state.js`) o relativos (`./state.js`). Con custom domain (CNAME) y
  servido desde root, ambos funcionan. Recomendación: **paths relativos entre
  módulos** (`./domain/schedule.js`) para portabilidad; el entry en index.html
  usa absoluto (`/src/main.js`).
- **404 handling**: GH Pages no tiene fallback SPA, pero la app es single-page
  servida desde `/` — no aplica routing server-side. ✓

### Sin cambios necesarios en GH Pages config
No hay `_config.yml` ni settings especiales. `.nojekyll` + CNAME es todo. El
split multi-file "just works" en GH Pages siempre que los MIME sean correctos
(lo son).

---

## 4. CI con ES modules — EL SEGUNDO RETO GRANDE

El split rompe la suposición single-file de TODA la infra de test/validate.

### 4.1 `tests/lib/load-domain.js` — reescritura obligatoria

Hoy: lee los `<script>` de `index.html`, concatena, extrae funciones por
nombre. Con las funciones en `src/*.js`:
- **Opción A**: `load-domain.js` lee y concatena los `src/*.js` (en vez de los
  `<script>` de index.html). Mantiene la estrategia de extracción.
- **Opción B** (mejor, si los módulos exportan): los módulos ES `export` sus
  funciones puras → los tests hacen `import` directo. Elimina la extracción por
  string-walking (frágil). Requiere que `src/domain/*.js` use `export`.

Recomendación: **B** — el split a ESM es la oportunidad de que los tests hagan
`import` real en vez del hack de extracción. Más robusto, menos mantenimiento.
Pero los tests de Node necesitan `"type":"module"` o `.mjs`, o usar `import()`
dinámico. Decisión de tooling.

### 4.2 `tests/unit/state.test.js` — el sandbox extractStateBlock

Hoy: extrae el bloque entre `// ── STATE MIRROR START/END` de index.html y lo
`eval` en un sandbox con los 19 globals pre-declarados. Con el state container
en `src/state.js`:
- Si `src/state.js` exporta el `state` container → el test hace `import` directo
  (mucho más limpio que el eval-sandbox).
- Los 19 globals "mirror" son el detalle más espinoso: el state container hace
  late-binding contra `let` globals del módulo. Al separar, esos globals deben
  vivir en algún módulo (¿`src/state.js` los declara y exporta?). El mirror
  pattern (p5.5) fue diseñado para coexistir con globals legacy — Fase 8 podría
  ELIMINAR el mirror si los globals desaparecen (todo pasa por state). Eso es
  scope de Fase 8, no de este doc, pero hay que decidirlo.

### 4.3 `validate.py` — múltiples checks parsean index.html

Checks que asumen single-file y deben adaptarse a multi-file:
- `[state-mirror]`, `[controller-pattern]`, `[event-delegation]`,
  `[view-purity]`, `[storage-encapsulation]`, `[js-syntax]`,
  `[js-open-pel-coverage]`, etc.
- Hoy hacen `open('index.html').read()` y regex/markers sobre el texto único.
- Adaptación: cada check debe leer el conjunto `src/*.js` (glob) en vez de
  index.html. La mayoría son regex sobre texto → cambiar la fuente de
  `_html = open('index.html').read()` a `_src = concat(glob('src/**/*.js'))`.
- `[js-syntax]`: hoy extrae `<script>` y hace `node --check`. Con módulos →
  `node --check src/*.js` archivo por archivo (más limpio).
- Los markers de sección (`// ── STATE MIRROR START`) ya no son necesarios si
  cada sección ES un archivo — los checks apuntan al archivo directamente.

### 4.4 `playwright.yml` paths filter

Hoy: `paths: ['index.html', ...]`. Con multi-file: **añadir `src/**`** al filter,
o CI no corre en cambios solo-de-módulos. Crítico — un cambio en
`src/domain/schedule.js` sin tocar index.html NO dispararía Playwright hoy.

### 4.5 `playwright.config.js` webServer

`python3 -m http.server 3000` sirve el repo root. Python ≥3.7 sirve `.js` con
MIME `text/javascript` (válido para ESM). ✓ Sin cambios. (Verificar versión de
Python en el runner CI — Node 20 image suele traer Python 3.10+.)

### 4.6 `bundle.yml` (Capgo)

Hoy copia `index.html`, `sw.js`, etc. a `www/`. Debe **añadir `cp -r src/.
www/src/`** para que el bundle Capgo incluya los módulos. Si falta, la app
nativa carga HTML que importa módulos inexistentes → pantalla blanca.

### 4.7 `bump-version.js`

Hoy estampa `BUILD_VERSION` en index.html + `CACHE_NAME` en sw.js. Sin cambios
si D-INFRA-1=B (los módulos se revalidan por red, no por filename-hash). Si
D-INFRA-1=A (content-hash), bump-version se reemplaza por el build step.

---

## 5. Capacitor module loading

### Soporte de ESM en WebViews
- **iOS WKWebView**: soporta `<script type="module">` desde iOS 11+ (Safari 11).
  Todos los targets actuales OK.
- **Android WebView**: soporta ESM desde Chrome 61+ (System WebView moderno).
  El minSdk del proyecto debe garantizar WebView reciente — verificar
  `build.gradle` (no en este repo; está en el proyecto Android separado).

### server.url = producción
- La app nativa carga desde `https://otrofestiv.app` (no bundle local). Los
  módulos se sirven por HTTPS desde GH Pages → same-origin → ESM imports OK.
- **Riesgo conocido (del comentario de sw.js v15)**: "controllerchange en iOS
  WKWebView es flaky". El SW hace `client.navigate()` en cada activación para
  forzar reload. Con módulos network-first (D-INFRA-1=B), el reload jala los
  módulos nuevos. Verificar en QA real en device iOS que el reload + re-import
  de módulos funciona (no hay caché de módulo ES persistente en WKWebView que
  sobreviva al navigate).

### Capgo OTA bundle
- El bundle (`www/`) debe incluir `src/`. Capgo sirve el bundle localmente en el
  device. Los `import` relativos (`./domain/x.js`) resuelven dentro del bundle
  servido por Capgo (origin local `capacitor://` o `https://localhost`).
- **Verificar**: el origin del WebView con Capgo bundle local soporta ESM
  imports. Capacitor sirve el bundle vía un servidor local → ESM same-origin OK.
  Pero el `url.origin !== location.origin` guard del SW podría comportarse
  distinto bajo `capacitor://`. QA en device necesario.

### Decisión D-INFRA-3: QA en device obligatorio
Antes de promover Fase 8 a producción nativa, QA manual en device iOS + Android:
- App carga (módulos importan sin error)
- Deploy OTA propaga cambios de módulo (Capgo) + producción (server.url)
- SW reload tras deploy jala módulos nuevos (no stale)

---

## 6. Estructura de carpetas objetivo

Mapeo de las secciones actuales de `index.html` a módulos. El bloque grande
(L2754–11697) contiene la mayoría.

```
/
├── index.html              # shell: <head>, divs críticos, <script type="module" src="/src/main.js">
├── sw.js                   # + regla network-first para /src/ (D-INFRA-1=B)
├── src/
│   ├── main.js             # entry: imports + bootstrap (DOMContentLoaded, loadFestival inicial)
│   ├── state/
│   │   └── state.js        # STATE MIRROR (subscribe, subscribeRender, transaction) — exporta `state`
│   ├── storage/
│   │   └── storage.js      # storage adapter (localStorage I/O encapsulado)
│   ├── domain/             # funciones PURAS (las 21 PURE_FNS + sched + helpers) — testeables vía import
│   │   ├── schedule.js     # computeScenarios, screensConflict, sortScreensByStrategy, ...
│   │   ├── time.js         # festDate, simNow, parseDur, getFestivalPhase, ...
│   │   ├── film.js         # scoreFilm, effectiveDuration, screeningPassed, ...
│   │   └── festival.js     # resolveVenue, classifyFestival, ...
│   ├── controller/
│   │   ├── registry.js     # ACTION_REGISTRY (97 entries) + delegated listener + renderActiveView
│   │   ├── pipeline.js     # RENDER PIPELINE (subscribeRender registrations)
│   │   └── handlers.js     # toggleWL, togglePriority, ... (los controllers 7a/7c)
│   ├── view/
│   │   ├── programa.js     # renderPrograma*, _renderProgramaContent, grid
│   │   ├── agenda.js       # renderAgenda (seleccion/miplan/planner branches)
│   │   ├── miplan.js       # renderMiPlanCalendar, ...
│   │   ├── sheets.js       # pel-sheet, corto-sheet, av-sheet, auth-sheet renders
│   │   └── components.js   # emptyState, _posterThumb, toast, ICONS
│   ├── i18n/
│   │   └── i18n.js         # t(), _applyI18nDOM, setLang
│   └── config.js           # FESTIVAL_CONFIG, constants, BUILD_VERSION
├── i18n/                   # (sin cambio) es.json, en.json
├── festivals/              # (sin cambio) *.json
└── assets/                 # (sin cambio)
```

### Principios del split
1. **Domain primero, sin DOM**: `src/domain/*.js` son funciones puras, cero
   `document`. Testeables por `import` directo (resuelve §4.1).
2. **State como módulo central**: `src/state/state.js` exporta el container.
   Todos importan de ahí. **Decisión Fase 8**: ¿eliminar el mirror de globals
   (p5.5) ahora que no hay legacy global scope? Probablemente sí — el mirror
   existía para coexistir con globals; con módulos, el state ES la fuente.
3. **Dependencias acíclicas**: domain ← state ← controller ← view ← main. Los
   `import` deben formar un DAG. El render pipeline (controller) importa view;
   view importa domain + state. Cuidado con ciclos view↔controller (el
   ACTION_REGISTRY referencia handlers que referencian renders).
4. **El orden de los 7c/7d ayuda**: ACTION_REGISTRY (7c) y el subscribe→render
   pipeline (7d) ya desacoplaron handlers de renders vía el registry y el
   pipeline. Eso da fronteras de módulo limpias — el split sigue esas fronteras.

### Riesgo de dependencias circulares (el más sutil del split)
- `controller/registry.js` (ACTION_REGISTRY) referencia handlers
  (`handlers.js`) que mutan state y disparan render (vía pipeline).
- `view/*.js` referencian `domain` + `state`.
- `controller/pipeline.js` (subscribeRender) referencia `renderActiveView`
  (controller) que llama `view/*`.
- Posible ciclo: pipeline → view → (¿controller?). Mapear el DAG ANTES de
  splittear. Si hay ciclos, romperlos con late-binding (import dinámico) o
  reordenar. **Tarea de análisis previo de Fase 8**, no de este doc.

---

## 7. Orden de ejecución propuesto para Fase 8 (post-Tribeca)

Secuencia de menor a mayor riesgo, cada paso verificable:

1. **Mapa de dependencias (DAG)** — analizar imports/referencias entre las
   secciones futuras. Detectar ciclos. (Análisis previo, sin código.)
2. **Decidir Camino 1 vs 2** (D-INFRA-2) y D-INFRA-1 (cache-bust).
3. **Reescribir test/validate infra PRIMERO** — `load-domain.js` + `state.test.js`
   + `validate.py` para leer `src/` (con un `src/` placeholder o feature flag).
   Esto da la red de seguridad ANTES de mover código.
4. **Split incremental por capa**: domain → state → controller → view → main.
   Cada capa: mover a módulo, añadir `export`/`import`, validar, Playwright.
5. **SW network-first para /src/** (D-INFRA-1=B).
6. **bundle.yml + playwright.yml paths** — añadir `src/`.
7. **QA device iOS + Android** (D-INFRA-3) antes de promover nativo.
8. **Deploy**: el primer deploy multi-file requiere subir `src/` completo +
   index.html nuevo. Coordinar (no es el drag-and-drop de 1 archivo habitual).

---

## 8. Decisiones cerradas

Las 5 decisiones de infraestructura están **cerradas** (aprobadas por Juan
post-7d):

| # | Decisión | Resolución | Implicación |
|---|---|---|---|
| **D-INFRA-1** | Cache-bust de módulos JS | ✅ **B — SW network-first para `/src/`** | Sin build step. El SW sirve `/src/*.js` con `cache: 'no-store'` + fallback offline. `BUILD_VERSION`/`CACHE_NAME` siguen bumpeando el SW. |
| **D-INFRA-2** | Artefacto de deploy | ✅ **Camino 1 — ESM nativo multi-file** | No se introduce bundler. Deploy = copiar `src/` + index.html. `modulepreload` hints opcionales para módulos críticos (sin bundler). |
| **D-INFRA-3** | QA device | ✅ **Obligatorio pre-prod nativo** | QA manual iOS + Android antes de promover: app carga, OTA propaga, SW reload jala módulos nuevos. |
| **D-INFRA-4** | Mirror de globals (p5.5) | ✅ **Eliminar en el split** | El state container es la fuente única. Se eliminan los `let` globals + `_MIRROR_TARGETS`/`_MIRROR_READERS`. `state.js` exporta el container; todos importan de ahí. |
| **D-INFRA-5** | Tests: extracción vs import | ✅ **`import` directo** | Los módulos `export` sus funciones. `load-domain.js` (string-walking) y el sandbox `extractStateBlock` se reemplazan por `import` real. Tests Node con ESM (`.mjs` o `"type":"module"`). |

### Consecuencias acopladas de las decisiones cerradas

- **D-INFRA-1=B + D-INFRA-2=Camino 1** se refuerzan: ambas evitan el build step.
  El SW network-first es lo que hace viable el ESM nativo sin hash de filenames.
- **D-INFRA-4 (eliminar mirror) + D-INFRA-5 (import directo)** se acoplan: al
  eliminar los globals legacy, `state.test.js` ya no necesita el sandbox de 19
  globals — hace `import { state } from '../../src/state/state.js'` directo. El
  mirror existía SOLO para coexistir con globals; sin ellos, desaparece.
- **D-INFRA-4 es el cambio de comportamiento más profundo de Fase 8**: a
  diferencia del resto (relocación pura), eliminar el mirror toca CÓMO se leen
  los globals en todo el código. Requiere que cada lectura de `watchlist`,
  `FILMS`, etc. pase por `state.get()` o por el import del módulo que los posee.
  Esto debe verificarse en el mapa de dependencias (DAG) — ver §11.

---

## 9. Lo que NO cambia en Fase 8

- `festivals/*.json`, `i18n/*.json`, `assets/` — sin cambios.
- `version.json`, `manifest.json`, `CNAME`, `.nojekyll` — sin cambios.
- La lógica de la app (ya refactorizada en 5.5–7d) — solo se MUEVE, no se
  reescribe. Fase 8 es relocación + import/export, no cambio de comportamiento.
- El deploy nativo vía Capgo OTA — el mecanismo sigue; solo el contenido del
  bundle incluye `src/`.

---

## 10. Riesgo neto y recomendación de timing

Fase 8 toca: SW, deploy, CI (4 workflows), test infra (3 archivos), y mueve
~12k líneas. Es el cambio de mayor superficie del roadmap. Confirma la decisión
de **hacerlo post-Tribeca** — el riesgo operativo (deploy nuevo, SW nuevo) no es
apropiado a 13 días de un festival en vivo.

Las 5 decisiones de infraestructura (D-INFRA-1 a 5) están **cerradas** (§8). El
único pre-requisito restante es el mapa de dependencias (DAG) — §11.

---

## 11. ⚠ PREREQUISITO BLOQUEANTE — Mapa de dependencias (DAG)

**Fase 8 NO arranca hasta que este mapa esté completo y libre de ciclos.** Es
el único bloqueante restante (las 5 decisiones D-INFRA ya están cerradas).

### Qué entregar
Un análisis previo (sin código) que mapee, para cada módulo objetivo de §6, sus
`import` hacia otros módulos, y verifique que el grafo resultante es **acíclico**
(DAG). Orden esperado: `domain ← state ← controller ← view ← main`.

### Ciclos a descartar explícitamente
1. **view ↔ controller**: `controller/registry.js` (ACTION_REGISTRY) referencia
   handlers → handlers mutan state → pipeline dispara `renderActiveView`
   (controller) → llama `view/*`. Si `view/*` importa de `controller`, hay ciclo.
2. **pipeline → view → ¿?**: `controller/pipeline.js` (subscribeRender)
   referencia `renderActiveView`, que llama renders de `view/*`. Verificar que
   `view/*` no reimporte `controller`.
3. **handlers ↔ view**: los handlers (toggleWL, etc.) ya NO llaman renders
   directos (7d los movió al pipeline) — esto ROMPE el ciclo handler→view que
   existiría pre-7d. Confirmar que se mantiene.

### Técnicas de ruptura si aparecen ciclos
- **Late-binding por import dinámico**: `const { renderActiveView } = await
  import('./registry.js')` dentro del callback, no al top.
- **Inversión de dependencia**: el pipeline recibe `renderActiveView` como
  parámetro inyectado en `main.js` en vez de importarlo.
- **Reubicación**: mover `renderActiveView` a un módulo neutro que ambos importen.

### Por qué 7c/7d facilitan esto
ACTION_REGISTRY (7c) y el subscribe→render pipeline (7d) ya desacoplaron
handlers de renders. El registry es un mapa de strings→fns; el pipeline es
suscripción por key. Ninguno crea acoplamiento estático directo handler→view.
Eso da fronteras de módulo limpias — pero el DAG debe **confirmarlo**, no
asumirlo.

### Gate
Con el DAG verificado sin ciclos (o con las rupturas planeadas), Fase 8 se
ejecuta con el mismo patrón de fases acotadas + verificables que llevó
5.5 → 7d a cero regresiones. Sin el DAG, no se escribe una línea de Fase 8.

---

## 12. DAG RESUELTO — verificado acíclico ✅

El prerequisito bloqueante (§11) está **resuelto**. Análisis empírico sobre
`index.html` confirma: **cero ciclos**. Fase 8 puede arrancar.

### Grafo de capas (aristas verificadas)

```
                  config  (leaf — constants, FESTIVAL_CONFIG, BUILD_VERSION)
                   ▲  ▲  ▲
        ┌──────────┘  │  └──────────┐
     domain         state         i18n / storage
   (puras)        (container)
        ▲             ▲  ▲
        │      ┌──────┘  │
        │   storage    i18n          storage → state ; i18n → state (t() lee _lang)
        │             ▲
        └────┐    ┌───┘
           view ─┘                   view → domain, state, i18n, config
        (render*)                    ⚠ NO view → controller (clave)
            ▲
        controller                   controller → view, state, domain, storage, i18n
       (handlers, registry,
        renderActiveView,
        runCalc, pipeline)
            ▲
          main                       main → todo (bootstrap)
```

### Cero ciclos — los 3 riesgos de §11 son unidireccionales

| Riesgo §11 | Verificación | Resultado |
|---|---|---|
| view ↔ controller | `renderAgenda`/`_renderProgramaContent` no llaman handlers/runCalc/renderActiveView; ningún render llama renderActiveView | Solo controller→view |
| pipeline → view → controller | pipeline → renderActiveView (controller) → render* (view); view no regresa | No ciclo |
| handlers ↔ view | handlers → surgical patches (view) + renders vía pipeline; renders no llaman handlers | Solo controller→view |
| toast closures | `showActionToast(..., () => handler())` solo en toggleWL/_checkRecalcOpportunity/togglePelWL (todos controller) | No filtra a view |

### Por qué quedó acíclico (payoff de 7c/7d/7c-4)

- **7c** (event delegation): renders emiten `data-action="X"` (string), no
  `onclick="X()"` (ref JS). El edge view→controller vía onclick desapareció.
- **7d** (subscribe→render): handlers ya no llaman renders; el pipeline
  (controller) dispara renderActiveView. Edge handler→view centralizado.
- **7c-4** (emptyStateHero/_posterThumb): emiten `data-action` strings / usan
  js-open-pel en vez de handler calls. Otro edge view→controller eliminado.

Sin estas fases, el split tendría ciclos view↔controller intratables. El
roadmap dejó la app en el único estado donde Fase 8 es acíclica.

### Orden topológico de extracción (CORRIGE §7)

§7 proponía `domain → state → controller → view → main`. **Invertido**:
`controller` depende de `view`, así que view se extrae ANTES. Orden correcto
(leaves primero — cada módulo se extrae cuando sus deps ya existen):

```
1. config       (leaf)
2. domain       → config                        [22 unit-tested + 15 sched, ya puras]
3. state        → config                         [elimina mirror — D-INFRA-4]
4. storage      → state, config
5. i18n         → state, config
6. view         → domain, state, i18n, config    [render*, sheets, components]
7. controller   → view, state, domain, storage   [handlers, registry, pipeline, renderActiveView, runCalc]
8. main         → todo                            [bootstrap]
```

Sub-DAG dentro de controller (acíclico): `pipeline → registry → handlers`,
`renderActiveView → view`. Todo hacia abajo.

### Clasificaciones resueltas

| Función / grupo | Capa | Razón |
|---|---|---|
| `renderActiveView`, `runCalc` | **controller** | Orquestación compute+dispatch; llaman renders (view) → controller→view limpio |
| `updateCardState`, `updateAgTab`, `_reRenderIntereses`, `updateHorarioPrioBtn`, `updateRatingStars` | **view** | Surgical DOM patches; leaves de view, llamados por controller |
| Sheets (`openPelSheet`, `closePelSheet`, `openAvSheet`, …) | **view/sheets.js** | DOM show/hide; despachados por registry (controller→view) |
| `setLang` | **controller** | ACTION_REGISTRY entry (acción) |
| `t()`, `_applyI18nDOM` | **i18n** | Lectura de `_lang` (state); sin llamadas a render |
| `emptyStateHero`, `_posterThumb`, `showToast`, `ICONS` | **view/components.js** | Componentes puros (post-7c-4 emiten data-action strings) |
| Composite helpers (`_toggleWLAndClose`, `_closePelAndRate`, …) | **controller** | Encapsulan multi-statement de handlers |

### Veredicto

**Prerequisito bloqueante resuelto.** Fase 8 ejecutable con extracción
incremental en el orden topológico, cada capa validada + Playwright antes de la
siguiente.
