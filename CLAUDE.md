# CLAUDE.md — Otrofestiv
> Generado automáticamente por `scripts/generate-claude-md.js`.
> No editar a mano — los cambios se sobreescriben en el próximo deploy.
> Para modificar secciones estáticas, editar el template en el script.
>
> Último commit: `740ae81 refactor(controller): 7a — 18 action handlers al pattern canónico + 2 dead removes (#10)`

---

## Qué es Otrofestiv

PWA mobile-first para planear asistencia a festivales de cine. Permite explorar el programa, armar una watchlist, detectar conflictos de horario y generar un plan optimizado. Vanilla JS/HTML, single-file (`index.html`), sin dependencias externas. Desplegado en GitHub Pages.

- **Repo:** `jdvlazio/Otrofestiv.app`
- **URL producción:** `https://otrofestiv.app`
- **Deploy:** drag-and-drop manual en GitHub web interface

---

## Bootstrap de sesión

```bash
git clone https://<GITHUB_TOKEN>@github.com/jdvlazio/Otrofestiv.app.git /home/claude/repo \
  && cd /home/claude/repo \
  && git config user.email "claude@anthropic.com" \
  && git config user.name "Claude"
```

Después del clone, leer en este orden:
1. Este archivo (`CLAUDE.md`)
2. `docs/ARQUITECTURA.md` — diseño, reglas, componentes, patrones
3. Si el trabajo involucra datos de festival: `docs/SCHEMA.md`
4. Si el trabajo involucra onboarding de un festival nuevo: `docs/PIPELINE.md`

---

## Protocolo de trabajo con Juan

Juan es Product Owner, diseñador y developer. Claude ejecuta; Juan audita y aprueba.

**Reglas inamovibles del proceso:**

1. **Arquitectura antes de ejecución.** Toda decisión no trivial requiere propuesta + aprobación antes de tocar código.
2. **Cambios quirúrgicos.** Solo se modifica lo pedido. Cero modificaciones no solicitadas.
3. **Copy es un artefacto de diseño.** Toda nueva string o corrección requiere discusión semántica con Juan como Content Designer + UX Writer. Sin excepciones.
4. **Validar antes de commitear.** Siempre correr `python3 validate.py` antes de proponer un commit.
5. **bump-version antes de deploy.** `node scripts/bump-version.js` justo antes de cada push.
6. **Sin regresiones.** Verificar qué cambió y por qué después de cada entrega.

---

## Estado del proyecto

### Festivales (desde `FESTIVAL_CONFIG` en `index.html`)

| ID | Nombre | Ciudad | Fechas | Estado |
|---|---|---|---|---|
| `ficci65` | FICCI 65 | Cartagena | 14–19 ABR | Archivado |
| `aff2026` | AFF 2026 | Medellín | 21–29 ABR | Recién terminado |
| `tribeca2026` | Tribeca Festival | New York | JUN 3–14 | **Próximo / activo** |
| `cinemancia2025` | Cinemancia 2025 | Valle de Aburrá | 11–20 SEP | Archivado |
| `leviza2026` | Leviza - Festival de Cine y Audiovisuales | Zapatoca | 14–17 MAY | Recién terminado |

### Features activas (desde `.specify/features/`)

- `controller-pattern-7a/` — fase actual: **tasks**
- `data-title-refactor/` — fase actual: **tasks**
- `domain-layer-extraction/` — fase actual: **tasks**
- `festival-phase-extraction/` — fase actual: **tasks**
- `grid-section-separators/` — fase actual: **tasks**
- `i18n-films-audit/` — fase actual: **tasks**
- `i18n-planner-audit/` — fase actual: **tasks**
- `lista-todo-sort/` — fase actual: **tasks**
- `normtitle/` — fase actual: **tasks**
- `schedule-planning/` — fase actual: **tasks**
- `splash-animation/` — fase actual: **tasks**
- `state-mirror/` — fase actual: **tasks**
- `storage-adapter/` — fase actual: **tasks**
- `sugerencias-watchlist/` — fase actual: **tasks**
- `temporal-subsystem/` — fase actual: **tasks**
- `title-truncation/` — fase actual: **tasks**
- `venue-warnings/` — fase actual: **tasks**
- `view-purity-6a/` — fase actual: **tasks**
- `view-purity-6b/` — fase actual: **tasks**
- `view-purity-6c/` — fase actual: **tasks**

---

## Documentación de referencia

| Archivo | Qué contiene |
|---|---|
| `docs/ARQUITECTURA.md` | Design system completo, reglas de diseño, mapa de funciones, patrones canónicos |
| `docs/PIPELINE.md` | Proceso de onboarding de festivales nuevos (fases, gates, roles) |
| `docs/SCHEMA.md` | Schema normativo del JSON de festival |
| `.specify/memory/constitution.md` | Rationale de decisiones de arquitectura clave |
| `.specify/features/` | Specs y planes de features en desarrollo |
| `validate.py` | Validador: JS syntax, divs críticos, CSS, patrones prohibidos |

---

## Reglas críticas (resumen — ver `docs/ARQUITECTURA.md` para detalle)

- **CTA primario:** fondo amber sólido, texto negro. Siempre.
- **Pósters:** solo vía `getFilmPoster(f)` o `getCortoItemPoster(item)`. Nunca directo.
- **Iconos:** solo Lucide. Flags de países y emojis de categoría son la única excepción.
- **Conflictos de horario:** siempre `screensConflict()`. Nunca comparaciones manuales.
- **Tokens:** todo valor de spacing, tipografía y radio usa `var(--)`. Cero valores raw.
- **Regex en index.html:** prohibido para transformaciones estructurales de >10 ocurrencias.
- **Timezone:** Colombia (UTC-5). Nunca `toISOString()` para lógica de fechas.
- **i18n:** toda string nueva va a `es.json` + `en.json` + `strings-reference.json`.

---

## APIs

- **TMDB:** `$TMDB_API_KEY` (variable de entorno — nunca hardcodeada)
- **GitHub token:** en el bootstrap command de arriba

---

## Android APK (Play Store)

- **Track:** Closed testing — Alpha
- **versionCode actual:** 3 (subido MAY 14, 2026)
- **Próximo versionCode:** **4** — nunca reutilizar un code ya publicado
- **server.url:** `https://otrofestiv.app` — la app carga desde producción, no desde bundle local
- **Para compilar:** Android Studio → Build → Generate Signed Bundle → versionCode en `android/app/build.gradle`
- **Para subir:** Play Console → Testing → Closed testing → Alpha → Create new release

---

## CI — GitHub Actions

- **bump-and-validate.yml:** solo corre `python3 validate.py`. El bump de versión es responsabilidad local — correr `node scripts/bump-version.js` antes de cada push.
- **playwright.yml:** tests de regresión T01–T10, viewport 390×844 (iPhone 14), simTime frozen para festivales activos.
- **promote-ios.yml:** workflow manual para promover `version.json.android → .ios` (staged rollout).

---

## Herramientas del pipeline

```bash
python3 validate.py                        # validar antes de commitear
node scripts/bump-version.js               # actualizar sw.js + version.json + CLAUDE.md antes de deploy
node scripts/generate-config.js --help     # generar entrada FESTIVAL_CONFIG
python3 scripts/enrich-festival.py --help  # enriquecer JSON con TMDB
python3 scripts/geocode-venues.py --help   # geocodificar venues
```
